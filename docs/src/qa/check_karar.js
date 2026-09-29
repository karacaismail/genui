// Behavior checks for the decision book (docs/karar-kitabi.html).
// Usage: node check_karar.js <html-file-or-url>   (CHROME_PATH=/path/to/chromium, otherwise the installed Chrome channel)
// Prints one JSON line per check; exits 1 if any check fails, 2 on a bad argument.
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

function toUrl(arg) {
  if (!arg) { console.error('usage: node check_karar.js <html-file-or-url>'); process.exit(2); }
  if (/^(https?|file):\/\//i.test(arg)) return arg;
  const abs = path.resolve(arg);
  if (!fs.existsSync(abs)) { console.error('file not found: ' + abs); process.exit(2); }
  return pathToFileURL(abs).href;
}
const url = toUrl(process.argv[2]);
const results = [];
const rec = (check, ok, detail) => results.push({ check, status: ok ? 'pass' : 'fail', detail });

(async () => {
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH, args: ['--no-sandbox'] } : { channel: 'chrome' });
  const ctx = await browser.newContext({ viewport: { width: 1280, height: 900 }, acceptDownloads: true });
  const page = await ctx.newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message));
  await page.goto(url); await page.waitForTimeout(300);

  const bank = await page.evaluate(() => JSON.parse(document.getElementById('kitap-veri').textContent));
  const total = bank.sorular.length;
  const cards = await page.locator('article.q').count();
  rec('every question renders a card', cards === total, `cards=${cards} questions=${total}`);
  const everyExample = await page.evaluate(() => [].every.call(document.querySelectorAll('.opt'), o => o.querySelector('.ex') && o.querySelector('.eff')));
  rec('every option shows a real-world example and its effect', everyExample, '');

  // conditional question: U07 (accounting AI) appears only when U03 includes "muhasebe"
  const hiddenBefore = await page.locator('#U07').isHidden();
  await page.locator('#U03 input[value="muhasebe"]').check();
  const shownAfter = await page.locator('#U07').isVisible();
  rec('conditional question appears when its condition is chosen', hiddenBefore && shownAfter, `before hidden=${hiddenBefore} after visible=${shownAfter}`);

  // select, defer, recommended
  await page.locator('#C01 input[value="kayit"]').check();
  await page.locator('#C02 [data-role="defer"]').click();
  await page.locator('#C03 .q-actions .btn').first().click();
  const states = await page.evaluate(() => ['C01', 'C02', 'C03'].map(id => document.getElementById(id).dataset.state));
  rec('select, defer and "Önerileni seç" set the card state', states.join() === 'answered,deferred,answered', states.join());

  // persistence
  await page.waitForTimeout(400);
  await page.reload(); await page.waitForTimeout(300);
  const persisted = await page.evaluate(() => document.querySelector('#C01 input[value="kayit"]').checked && document.getElementById('C02').dataset.state === 'deferred');
  rec('answers survive a reload (browser storage)', persisted, '');

  // P1 filter
  await page.locator('#filtre button[data-f="p1"]').click();
  const p1ok = await page.evaluate(() => [].every.call(document.querySelectorAll('article.q'), c => c.getBoundingClientRect().height === 0 || c.querySelector('.chip.p1')));
  await page.locator('#filtre button[data-f="all"]').click();
  rec('P1 filter shows only P1 questions', p1ok, '');

  // bulk fill with two-step confirmation
  const bulk = page.locator('#bulk');
  await bulk.click(); const armedTxt = await bulk.textContent(); await bulk.click();
  await page.waitForTimeout(300);
  const leftWithRec = await page.evaluate(() => {
    const bank = JSON.parse(document.getElementById('kitap-veri').textContent);
    return bank.sorular.filter(q => q.oneri.length && document.getElementById(q.id).dataset.state === 'empty').map(q => q.id);
  });
  rec('bulk fill needs confirmation and fills every empty question that has a recommendation', /Onayla/.test(armedTxt) && leftWithRec.length === 0, `armed="${armedTxt.trim()}" left=${leftWithRec.join(',')}`);
  const c02still = await page.evaluate(() => document.getElementById('C02').dataset.state);
  rec('bulk fill keeps deferred questions deferred', c02still === 'deferred', c02still);

  // export
  const [dl] = await Promise.all([page.waitForEvent('download'), page.locator('.bar [data-act="export"]').click()]);
  const file = await dl.path();
  const data = JSON.parse(fs.readFileSync(file, 'utf8'));
  const a = Object.fromEntries(data.answers.map(x => [x.id, x]));
  const shapeOk = data.kind === 'genui-karar-kitabi-yanitlari' && data.schemaVersion === 1 && data.answers.length === total
    && a.C01.status === 'answered' && a.C01.selected[0] === 'kayit' && a.C01.source === 'user' && a.C01.matchesRecommendation === true
    && a.C02.status === 'deferred' && a.U07.status !== 'not_applicable'
    && a.C09.status === 'not_applicable'
    && data.answers.every(x => typeof x.question === 'string' && Array.isArray(x.affects) && Array.isArray(x.sources));
  rec('export produces a self-describing JSON with statuses, labels and sources', shapeOk, `file=${dl.suggestedFilename()} answered=${data.summary.answered} deferred=${data.summary.deferred} na=${data.summary.notApplicable}`);
  const sum = data.summary;
  const sumOk = sum.total + sum.notApplicable === total && sum.answered + sum.deferred + sum.unanswered === sum.total;
  rec('export summary counts add up', sumOk, JSON.stringify(sum).slice(0, 160));

  // reset then import the exported file
  const reset = page.locator('#reset'); await reset.click(); await reset.click(); await page.waitForTimeout(300);
  const afterReset = await page.evaluate(() => document.querySelectorAll('article.q[data-state="answered"]').length);
  await page.locator('#import-file').setInputFiles(file); await page.waitForTimeout(500);
  const restored = await page.evaluate(() => ({ answered: document.querySelectorAll('article.q[data-state="answered"]').length, c01: document.querySelector('#C01 input[value="kayit"]').checked }));
  rec('reset clears answers and import restores them', afterReset === 0 && restored.answered === sum.answered && restored.c01, `afterReset=${afterReset} restored=${restored.answered}/${sum.answered}`);

  // glossary dialog
  await page.locator('[data-act="gloss"]').first().click();
  const open = await page.evaluate(() => document.getElementById('sozluk').open);
  await page.locator('#sozluk-kapat').click();
  rec('glossary dialog opens and closes', open === true, '');

  // keyboard focus ring on an option card
  await page.locator('#C04 input').first().focus(); await page.keyboard.press('Tab'); await page.keyboard.press('Shift+Tab');
  const ring = await page.evaluate(() => { const l = document.activeElement.closest('.opt'); return l ? getComputedStyle(l).boxShadow : 'none'; });
  rec('keyboard focus shows a ring on the option card', /rgb/.test(ring), ring.slice(0, 80));

  rec('no uncaught JS errors', errs.length === 0, errs.join(' | ').slice(0, 200));
  await ctx.close();

  // narrow screens: no horizontal page overflow
  for (const w of [320, 390]) {
    const p = await browser.newPage({ viewport: { width: w, height: 800 } });
    await p.goto(url); await p.waitForTimeout(200);
    const ov = await p.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    rec(`${w}px: no horizontal page overflow`, ov <= 0, `overflow=${ov}px`);
    await p.close();
  }
  // dark theme renders without errors and with a dark background
  const dctx = await browser.newContext({ colorScheme: 'dark' });
  const dp = await dctx.newPage(); await dp.goto(url);
  const bg = await dp.evaluate(() => getComputedStyle(document.body).backgroundColor);
  rec('dark theme applies', bg === 'rgb(13, 17, 23)', bg);
  await dctx.close();

  await browser.close();
  for (const r of results) console.log(JSON.stringify(r));
  if (results.some(r => r.status === 'fail')) process.exitCode = 1;
})().catch(e => { console.error(e); process.exit(1); });

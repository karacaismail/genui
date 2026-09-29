// Behavior checks for the requirements page (document UI only; not the product's tests or the identity integration tests).
// Usage: node check.js <file-or-url>
// Browser: CHROME_PATH=/path/to/chromium, otherwise the locally installed Chrome channel is used.
// Prints one JSON line per check: {check, status: pass|fail|not_run, detail}; exits 1 if any check fails.
const { chromium } = require('playwright-core');
const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');

// http(s) and file URLs are used as given; any other argument is a file path, resolved against the
// current directory and converted with pathToFileURL (handles relative paths, spaces and non-ASCII).
function toUrl(arg) {
  if (!arg) {
    console.error('usage: node check.js <html-file-or-url>');
    process.exit(2);
  }
  if (/^(https?|file):\/\//i.test(arg)) return arg;
  const abs = path.resolve(arg);
  if (!fs.existsSync(abs)) {
    console.error('file not found: ' + abs);
    process.exit(2);
  }
  return pathToFileURL(abs).href;
}
const url = toUrl(process.argv[2]);
const results = [];
const rec = (check, ok, detail) => results.push({ check, status: ok === null ? 'not_run' : ok ? 'pass' : 'fail', detail });

(async () => {
  const browser = await chromium.launch(process.env.CHROME_PATH ? { executablePath: process.env.CHROME_PATH, args: ['--no-sandbox'] } : { channel: 'chrome' });

  // 1. keyboard: open AI label panel, press "Geri al" with Enter, focus must not fall to BODY
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    const chip = page.locator('#demo-chip');
    if (await chip.count()) {
      await chip.focus(); await page.keyboard.press('Enter');
      await page.locator('#demo-undo').focus(); await page.keyboard.press('Enter');
      const active = await page.evaluate(() => document.activeElement && (document.activeElement.id || document.activeElement.tagName));
      rec('demo: focus after "Geri al" via keyboard', active !== 'BODY', 'activeElement=' + active);
      const msg = await page.locator('#demo-status').textContent();
      rec('demo: status text says it is a simulation', /Demo/i.test(msg || ''), (msg || '').slice(0, 90));
      await page.locator('#demo-chip').count();
      await page.evaluate(() => { const r = document.getElementById('demo-revert'); r && r.click(); });
      const fb = page.locator('#demo-fb');
      await page.locator('#demo-chip').click();
      await fb.click();
      const msg2 = await page.locator('#demo-status').textContent();
      rec('demo: "Uygunsuz bildir" does not claim a real save', /gönderilmedi|simülasyon|Demo/i.test(msg2 || ''), (msg2 || '').slice(0, 90));
    } else rec('demo present', false, 'no #demo-chip');
    await page.close();
  }

  // 2. filter SHOULD then open a hash pointing at a MUST row: row must become visible
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    await page.locator('#flt-level button[data-level="SHOULD"]').click();
    const shown = await page.locator('#flt-count').textContent();
    await page.evaluate(() => { location.hash = '#B1'; });
    await page.waitForTimeout(300);
    const st = await page.evaluate(() => { const r = document.getElementById('B1'); const b = r.getBoundingClientRect(); return { hidden: r.hidden, h: Math.round(b.height) }; });
    rec('filter: deep link to a filtered-out row reveals it', !st.hidden && st.h > 0, 'count before=' + shown + ' hidden=' + st.hidden + ' height=' + st.h);
    await page.close();
  }

  // 3. no native <select> in the page UI
  {
    const page = await browser.newPage();
    await page.goto(url);
    const n = await page.locator('select').count();
    rec('controls: no native <select> used', n === 0, 'select count=' + n);
    await page.close();
  }

  // 4. 320 px: no root horizontal overflow; figure labels readable (>= 11 CSS px) or a text alternative visible
  {
    const page = await browser.newPage({ viewport: { width: 320, height: 568 } });
    await page.goto(url);
    const ov = await page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth);
    rec('320px: no root horizontal overflow', ov <= 0, 'overflow=' + ov + 'px');
    const fig = await page.evaluate(() => {
      const svg = document.querySelector('.fig svg');
      if (!svg) return null;
      const vb = svg.viewBox.baseVal; const w = svg.getBoundingClientRect().width;
      const scale = w / vb.width;
      const alt = document.querySelector('.fig .fig-steps');
      const altVisible = !!alt && getComputedStyle(alt).display !== 'none';
      return { scale: +scale.toFixed(3), smallest: +(11 * scale).toFixed(2), altVisible };
    });
    if (fig) rec('320px: diagram labels legible or text alternative shown', fig.smallest >= 11 || fig.altVisible, JSON.stringify(fig));
    else rec('320px: diagram present', null, 'no svg');
    // requirement rows readable as cards (no table scroll)
    const tbl = await page.evaluate(() => { const w = document.querySelector('.req-table').closest('.tbl-wrap'); return w.scrollWidth - w.clientWidth; });
    rec('320px: requirement table does not scroll sideways', tbl <= 1, 'inner overflow=' + tbl + 'px');
    await page.close();
  }

  // 5. reduced motion: back-to-top must not use smooth scrolling
  {
    const ctx = await browser.newContext({ reducedMotion: 'reduce', viewport: { width: 1280, height: 900 } });
    const page = await ctx.newPage();
    await page.addInitScript(() => {
      const orig = window.scrollTo.bind(window);
      window.__scrollCalls = [];
      window.scrollTo = function (a, b) { window.__scrollCalls.push(typeof a === 'object' ? a.behavior || 'auto' : 'auto'); return orig(a, b); };
    });
    await page.goto(url);
    await page.evaluate(() => window.scrollTo(0, 3000));
    await page.waitForTimeout(200);
    await page.evaluate(() => { const t = document.getElementById('totop'); t && t.click(); });
    const calls = await page.evaluate(() => window.__scrollCalls);
    const last = calls[calls.length - 1];
    rec('reduced-motion: back-to-top scroll behavior', last !== 'smooth', 'last behavior=' + last);
    await ctx.close();
  }

  // 6. focus ring: single token, visible on a filter button
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    await page.locator('#flt-level button').first().focus();
    await page.keyboard.press('Tab'); await page.keyboard.press('Shift+Tab');
    const s = await page.evaluate(() => { const e = document.activeElement; const c = getComputedStyle(e); return { tag: e.tagName, shadow: c.boxShadow, outline: c.outlineStyle }; });
    rec('focus: visible ring from the single focus token', /rgb/.test(s.shadow) && s.outline === 'none', JSON.stringify(s));
    await page.close();
  }

  // 7. JS errors on load
  {
    const page = await browser.newPage();
    const errs = []; page.on('pageerror', e => errs.push(e.message));
    await page.goto(url); await page.waitForTimeout(300);
    rec('no uncaught JS errors on load', errs.length === 0, errs.join(' | ').slice(0, 200));
    await page.close();
  }

  // 8. slice (dilim) filter: one button per slice that rows carry; each slice shows exactly the rows delivered in it
  //    (a row with sub-scopes in several slices shows under each); "Tümü" restores all
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    const info = await page.evaluate(() => {
      // the universe is every requirement row, not only rows that already carry a slice attribute
      const rows = [].slice.call(document.querySelectorAll('.req-table tbody tr'));
      const missing = rows.filter(r => !/^[1-4]$/.test(r.getAttribute('data-dilim') || '') || !/^[1-4]( [1-4])*$/.test(r.getAttribute('data-dilimler') || '')).map(r => r.id);
      if (missing.length) return { total: rows.length, slices: ['missing:' + missing.join(',')], btns: [] };
      const slices = Array.from(new Set([].concat.apply([], rows.map(r => r.getAttribute('data-dilimler').split(' '))))).sort();
      const btns = [].slice.call(document.querySelectorAll('#flt-phase button')).map(b => b.getAttribute('data-dilim')).filter(p => p !== 'ALL').sort();
      return { total: rows.length, slices, btns };
    });
    rec('slice filter: a button for every slice present', JSON.stringify(info.slices) === JSON.stringify(info.btns), 'rows=' + info.slices.join(',') + ' buttons=' + info.btns.join(','));
    if (info.slices.some(p => p.startsWith('missing:'))) {
      rec('slice filter: each slice shows exactly its rows, "Tümü" restores all', false, 'requirement rows without a valid slice: ' + info.slices.join(','));
      await page.close();
    } else {
      const visible = () => page.evaluate(() => [].slice.call(document.querySelectorAll('.req-table tbody tr')).filter(r => !r.hidden && r.getBoundingClientRect().height > 0).map(r => r.id));
      let ok = true; const detail = [];
      for (const sl of info.slices) {
        await page.locator('#flt-phase button[data-dilim="' + sl + '"]').click();
        const ids = await visible();
        const expected = await page.evaluate(p => [].slice.call(document.querySelectorAll('.req-table tbody tr[data-dilimler~="' + p + '"]')).map(r => r.id), sl);
        const same = JSON.stringify(ids) === JSON.stringify(expected);
        ok = ok && same; detail.push(sl + ':' + ids.length + (same ? '' : '!=' + expected.length));
      }
      await page.locator('#flt-phase button[data-dilim="ALL"]').click();
      const all = (await visible()).length;
      ok = ok && all === info.total;
      rec('slice filter: each slice shows exactly its rows, "Tümü" restores all', ok, detail.join(' ') + ' all=' + all + '/' + info.total);
      await page.close();
    }
  }

  // 9. traceability: decisions changed by a later source show their effective state on their own row
  {
    const page = await browser.newPage();
    await page.goto(url);
    const st = await page.evaluate(() => {
      const out = {};
      [].slice.call(document.querySelectorAll('#izlenebilirlik table.trace tr')).forEach(tr => {
        const c = tr.querySelectorAll('td'); if (c.length > 8) out[c[0].textContent] = c[8].textContent;
      });
      return { auth: out['auth'], gateway: out['gateway'], tenancy: out['tenancy'], migration: out['migration'], css: out['css'], devices: out['devices'] };
    });
    rec('trace: effective state shown for superseded, closed and extended decisions',
      st.auth === 'yerine geçti' && st.gateway === 'koşullu' && st.tenancy === 'kapandı' && st.migration === 'yerine geçti' && st.css === 'yerine geçti' && st.devices === 'genişletildi', JSON.stringify(st));
    await page.close();
  }

  // 10. decision book: one row per answer; a link to a row inside a closed appendix opens it
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    const n = await page.locator('#kitap-sonuc tr[id^="kk-"]').count();
    await page.evaluate(() => { location.hash = '#kk-U07'; });
    await page.waitForTimeout(300);
    const vis = await page.evaluate(() => { const r = document.getElementById('kk-U07'); const d = r && r.closest('details'); return { open: !!(d && d.open), h: r ? Math.round(r.getBoundingClientRect().height) : 0 }; });
    rec('decision book: every answer has a row and deep links open its appendix', n === 104 && vis.open && vis.h > 0, 'rows=' + n + ' ' + JSON.stringify(vis));
    await page.close();
  }

  // 11. glossary: first use of a term links to its entry, which opens and is visible
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    const href = await page.evaluate(() => { const a = document.querySelector('#karar ~ section a.terim, #karar a.terim'); return a ? a.getAttribute('href') : null; });
    let ok = false, detail = 'no term link';
    if (href) {
      await page.evaluate(h => { location.hash = h; }, href);
      await page.waitForTimeout(300);
      const r = await page.evaluate(h => { const dt = document.querySelector(h); const d = dt && dt.closest('details'); return { open: !!(d && d.open), h: dt ? Math.round(dt.getBoundingClientRect().height) : 0, title: document.querySelector('a.terim').getAttribute('title') || '' }; }, href);
      ok = r.open && r.h > 0 && r.title.length > 10; detail = href + ' ' + JSON.stringify(r).slice(0, 120);
    }
    rec('glossary: term link opens the glossary entry and carries a short definition', ok, detail);
    await page.close();
  }

  // 12. every MUST row shows its test link; summary reading mode hides it
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    const r = await page.evaluate(() => {
      const rows = [].slice.call(document.querySelectorAll('.req-table tbody tr')).filter(tr => tr.querySelector('.chip.must'));
      return { must: rows.length, missing: rows.filter(tr => !tr.querySelector('.tst a')).map(tr => tr.id) };
    });
    await page.locator('#flt-mode button[data-mode="ozet"]').click();
    const hidden = await page.evaluate(() => { const t = document.querySelector('.req-table .tst'); return t ? getComputedStyle(t).display : 'none'; });
    rec('tests: every MUST row links to a test; summary mode hides test lines', r.missing.length === 0 && r.must > 0 && hidden === 'none', 'must=' + r.must + ' missing=' + r.missing.join(',') + ' ozet display=' + hidden);
    await page.close();
  }

  // 13. narrow screens with every appendix open (glossary, decision tables, test matrix): no root overflow.
  // The glossary is opened with the keyboard first (focus its summary, press Enter), the rest are opened in script.
  for (const w of [320, 360, 390]) {
    const page = await browser.newPage({ viewport: { width: w, height: 740 } });
    await page.goto(url);
    await page.locator('#sozluk-kutu > summary').focus();
    await page.keyboard.press('Enter');
    const kb = await page.evaluate(() => document.getElementById('sozluk-kutu').open);
    const r = await page.evaluate(() => {
      const ds = [].slice.call(document.querySelectorAll('details'));
      ds.forEach(d => { d.open = true; });
      const de = document.documentElement;
      // elements inside a container that scrolls or clips sideways (tables, code, the contents rail) cannot widen the page
      const inScroller = e => { for (let a = e.parentElement; a && a !== document.body; a = a.parentElement) { if (getComputedStyle(a).overflowX !== 'visible') return true; } return false; };
      const wide = [].slice.call(document.querySelectorAll('body *'))
        .filter(e => e.getBoundingClientRect().right > de.clientWidth + 1 && !inScroller(e))
        .slice(0, 5).map(e => e.tagName + '.' + (e.className || '').toString().split(' ')[0] + ' ' + Math.round(e.getBoundingClientRect().right));
      return { details: ds.length, ov: de.scrollWidth - de.clientWidth, wide };
    });
    rec(w + 'px: glossary opens with the keyboard; no root overflow with every appendix open',
      kb && r.ov <= 0 && r.wide.length === 0, 'keyboard open=' + kb + ' details=' + r.details + ' overflow=' + r.ov + 'px ' + r.wide.join(', '));
    await page.close();
  }

  // 14. multi-slice rows: a requirement delivered over several slices appears under each of them
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    const multi = await page.evaluate(() => [].slice.call(document.querySelectorAll('.req-table tbody tr[data-dilimler]'))
      .filter(r => r.getAttribute('data-dilimler').split(' ').length > 1).map(r => ({ id: r.id, s: r.getAttribute('data-dilimler').split(' ') })));
    let ok = multi.length > 0; const detail = [];
    for (const sl of ['1', '2', '3', '4']) {
      const btn = page.locator('#flt-phase button[data-dilim="' + sl + '"]');
      if (!(await btn.count())) continue;
      await btn.click();
      const visIds = await page.evaluate(() => [].slice.call(document.querySelectorAll('.req-table tbody tr')).filter(r => !r.hidden).map(r => r.id));
      const want = multi.filter(m => m.s.includes(sl)).map(m => m.id);
      const miss = want.filter(id => !visIds.includes(id));
      if (miss.length) { ok = false; detail.push(sl + ' missing ' + miss.join(',')); } else detail.push(sl + ':' + want.length);
    }
    rec('slice filter: rows delivered over several slices show under each slice', ok, 'multi-slice rows=' + multi.length + ' ' + detail.join(' '));
    await page.close();
  }

  await browser.close();
  for (const r of results) console.log(JSON.stringify(r));
  if (results.some(r => r.status === 'fail')) process.exitCode = 1;
})().catch(e => { console.error(e); process.exit(1); });

// Behavior checks for the requirements page (document UI only; not the identity integration tests AT-18–AT-25).
// Usage: node check.js <file-or-url>
// Browser: CHROME_PATH=/path/to/chromium, otherwise the locally installed Chrome channel is used.
// Prints one JSON line per check: {check, status: pass|fail|not_run, detail}; exits 1 if any check fails.
const { chromium } = require('playwright-core');

const target = process.argv[2];
const url = /^https?:/.test(target) ? target : 'file://' + target;
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

  // 8. phase filter: one button per phase that rows carry; each phase shows exactly its rows; "Tümü" restores all
  {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await page.goto(url);
    const info = await page.evaluate(() => {
      const rows = [].slice.call(document.querySelectorAll('tr[data-phase]'));
      const phases = Array.from(new Set(rows.map(r => r.getAttribute('data-phase')))).sort();
      const btns = [].slice.call(document.querySelectorAll('#flt-phase button')).map(b => b.getAttribute('data-phase')).filter(p => p !== 'ALL').sort();
      return { total: rows.length, phases, btns };
    });
    rec('phase filter: a button for every phase present', JSON.stringify(info.phases) === JSON.stringify(info.btns), 'rows=' + info.phases.join(',') + ' buttons=' + info.btns.join(','));
    const visible = () => page.evaluate(() => [].slice.call(document.querySelectorAll('tr[data-phase]')).filter(r => !r.hidden && r.getBoundingClientRect().height > 0).map(r => r.id));
    let ok = true; const detail = [];
    for (const ph of info.phases) {
      await page.locator('#flt-phase button[data-phase="' + ph + '"]').click();
      const ids = await visible();
      const expected = await page.evaluate(p => [].slice.call(document.querySelectorAll('tr[data-phase="' + p + '"]')).map(r => r.id), ph);
      const same = JSON.stringify(ids) === JSON.stringify(expected);
      ok = ok && same; detail.push(ph + ':' + ids.length + (same ? '' : '!=' + expected.length));
    }
    await page.locator('#flt-phase button[data-phase="ALL"]').click();
    const all = (await visible()).length;
    ok = ok && all === info.total;
    rec('phase filter: each phase shows exactly its rows, "Tümü" restores all', ok, detail.join(' ') + ' all=' + all + '/' + info.total);
    await page.close();
  }

  // 9. traceability: superseded and reopened record decisions are visible on their own row
  {
    const page = await browser.newPage();
    await page.goto(url);
    const st = await page.evaluate(() => {
      const out = {};
      [].slice.call(document.querySelectorAll('#izlenebilirlik table.trace tr')).forEach(tr => {
        const c = tr.querySelectorAll('td'); if (c.length > 8) out[c[0].textContent] = c[8].textContent;
      });
      return { auth: out['auth'], gateway: out['gateway'], tenancy: out['tenancy'], 'tenant-isolation': out['tenant-isolation'] };
    });
    rec('trace: effective state shown for superseded and reopened decisions',
      st.auth === 'yerine geçti' && st.gateway === 'koşullu' && st.tenancy === 'yeniden açıldı' && st['tenant-isolation'] === 'yeniden açıldı', JSON.stringify(st));
    await page.close();
  }

  await browser.close();
  for (const r of results) console.log(JSON.stringify(r));
  if (results.some(r => r.status === 'fail')) process.exitCode = 1;
})().catch(e => { console.error(e); process.exit(1); });

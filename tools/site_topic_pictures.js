/* The pictures of the topics on the home page of the site (site/img-topics/NAME-LANG-THEME.png → webp), taken from the
   Atlas of the built site (the owner, 2026-11-14, the design review §10). Run:
     python3 tools/build_atlas_site.py --out /tmp/site && (cd /tmp/site && python3 -m http.server 8791) &
     node tools/site_topic_pictures.js /tmp/shots
   then each PNG to 720 px wide WebP (quality 80) in site/img-topics. PICK: [page of the topic, its key, which of its
   pictures wider than 250 × 180 px]; fixed parts of the page and its buttons are hidden for the picture. */
const { chromium } = require('playwright');
const OUT = process.argv[2];
const PICK = [['pes', 'pes', 0], ['diatomics', 'mo', 0], ['symmetry', 'sym', 0], ['bo', 'bo', 0], ['vibrations', 'nm', 0],
              ['aim', 'aim', 0]];
const ONLY = process.argv.slice(3);  // keys to take again (all when none)
(async () => { const b = await chromium.launch();
for (const lang of ['ru', 'en', 'zh']) for (const theme of ['light', 'dark']) {
  const c = await b.newContext({viewport:{width:1200,height:900}, deviceScaleFactor:2});
  await c.addInitScript(t => { try { localStorage.setItem('qc-theme', t) } catch (e) {} }, theme);
  const p = await c.newPage();
  for (const [page, key, n] of PICK.filter(x => !ONLY.length || ONLY.includes(x[1]))) {
    await p.goto('http://localhost:8791/atlas/' + lang + '/' + page + '.html', {waitUntil:'load'}); await p.waitForTimeout(4000);
    const els = await p.$$('main svg, main canvas');
    let el = null, k = -1;
    for (const e of els) { const r = await e.boundingBox(); if (r && r.width > 250 && r.height > 180) { k++; if (k === n) { el = e; break; } } }
    await el.scrollIntoViewIfNeeded(); await p.waitForTimeout(600);
    await p.evaluate(() => { for (const e of document.querySelectorAll('body *')) { const s = getComputedStyle(e); if (s.position === 'fixed') e.style.visibility = 'hidden'; } document.querySelectorAll('button').forEach(x => x.style.visibility = 'hidden'); });
    await p.waitForTimeout(300);
    await el.screenshot({path: `${OUT}/${key}-${lang}-${theme}.png`});
    console.log(lang, theme, key);
  }
  await c.close();
}
await b.close(); })();

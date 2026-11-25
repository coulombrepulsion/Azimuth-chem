/* What every topic of the Atlas asks its Python for when it is opened — written to site/initial-requests.json, from
   which tools/build_atlas_site.py counts the answers kept on the site (atlas/assets/initial/<topic>.json), so that a
   topic opened shows its first plots without Python being loaded.

   Run after the pages or their scripts changed (needs Node and Playwright with Chromium; not needed to build the
   site): build the site, serve it, and
       node tools/site_initial_requests.js http://localhost:8791/ <folder of the built site>
   Every page of every language is opened alone, on a wide screen and on a phone (some topics ask for a plot of the
   size of the screen), until it has asked nothing new for 4 s (at most 90 s). The list of a topic is what its pages
   asked in the three languages on both screens, each request once: [name, parameters as qcstatic.js writes them].
   A request made at one opening only (its parameters are drawn at random) is left out. A request missing from the
   list is simply counted in the browser as before. */
const {chromium} = require('playwright');
const fs = require('fs');
const path = require('path');
(async () => {
  const [root, folder] = process.argv.slice(2);
  if (!root || !folder) { console.error('usage: node site_initial_requests.js <address of the site> <folder of the built site>'); process.exit(2); }
  const jobs = [];
  for (const screen of ['wide', 'phone'])
    for (const lang of ['ru', 'en', 'zh'])
      for (const file of fs.readdirSync(path.join(folder, 'atlas', lang)).filter(f => f.endsWith('.html')).sort())
        jobs.push([lang, file.slice(0, -5), screen]);
  const SCREENS = {wide: {viewport: {width: 1300, height: 900}}, phone: {viewport: {width: 390, height: 780}, isMobile: true, hasTouch: true, deviceScaleFactor: 2}};
  const found = {};
  const browser = await chromium.launch();
  const one = async () => {
    const pages = {};
    for (const screen of Object.keys(SCREENS)) {
      const context = await browser.newContext(Object.assign({serviceWorkers: 'block'}, SCREENS[screen]));
      await context.route('**/assets/initial/*.json', route => route.fulfill({status: 404, body: ''}));  // record what Python is asked without them
      pages[screen] = await context.newPage();
    }
    while (jobs.length) {
      const [lang, topic, screen] = jobs.shift();
      const page = pages[screen];
      let asked = [];
      try {
        await page.goto(new URL(`atlas/${lang}/${topic}.html`, root).href, {waitUntil: 'load', timeout: 60000});
        let same = 0;
        for (let t = 0; t < 90 && same < 4; t++) {
          await page.waitForTimeout(1000);
          const state = await page.evaluate(() => { const s = window.QCStatic && window.QCStatic.state; return s ? {asked: s.asked, busy: (window.QC && window.QC.pending) ? window.QC.pending() : 0} : null; });
          if (!state) { same++; continue; }
          same = state.asked.length === asked.length && !state.busy ? same + 1 : 0;
          asked = state.asked;
        }
      } catch (error) { console.error(lang, topic, String(error).split('\n')[0]); }
      /* a request is kept when at least two openings of the topic made it: what a page asks with a number drawn at
         random (the cloud of points of an orbital, a question of its quiz) is new at every opening and cannot be
         counted ahead */
      const list = found[topic] = found[topic] || [];
      const once = new Set();
      for (const [name, key] of asked) {
        if (key === null || name === 'health' || once.has(name + '|' + key)) continue;
        once.add(name + '|' + key);
        const entry = list.find(x => x[0] === name && x[1] === key);
        if (entry) entry[2]++; else list.push([name, key, 1]);
      }
      console.log(screen, lang, topic, asked.length);
    }
  };
  await Promise.all([one(), one()]);
  await browser.close();
  const sorted = {};
  Object.keys(found).sort().forEach(k => { const kept = found[k].filter(x => x[2] >= 2).map(x => [x[0], x[1]]); if (kept.length) sorted[k] = kept; });
  const out = path.join(__dirname, '..', 'site', 'initial-requests.json');
  const topics = Object.keys(sorted);  // a request a line, so that a change of the list reads as a change of lines
  const lines = ['{'];
  topics.forEach((t, i) => {
    lines.push(JSON.stringify(t) + ': [');
    sorted[t].forEach((x, j) => lines.push(' ' + JSON.stringify(x) + (j < sorted[t].length - 1 ? ',' : '')));
    lines.push(']' + (i < topics.length - 1 ? ',' : ''));
  });
  lines.push('}');
  fs.writeFileSync(out, lines.join('\n') + '\n');
  console.log('written', out, Object.keys(sorted).length, 'topics,', Object.values(sorted).reduce((a, b) => a + b.length, 0), 'requests');
})();

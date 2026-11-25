/* Azimuth site: the side panel of the program (hub/window.py _build_sidebar) for the pages of the site — the home
   page and the Atlas. A rail of icons 68 px wide; it stays narrow and the name of an icon stands beside it under the
   pointer or the keyboard focus; the glyph of the program at the top leads to the home page; below — the pages; at the
   bottom — the languages and the theme, for the whole site: the theme is kept in localStorage «qc-theme» and the
   language in «qc-hub-lang», the keys of the Atlas, so both pages show the same. On a phone the panel is a bar at the
   bottom. <script src="rail.js" data-root="./" data-here="home|atlas|lost">; window.SiteRail = {lang(), setLang(v),
   theme(), setTheme(v)}; the event «rail-lang» ({detail: lang}) on document tells a page to change its texts. In the
   Atlas the panel talks to its page as the program does, through window.QuASAtlas. */
(function () {
  'use strict';
  const me = document.currentScript;
  const ROOT = me.dataset.root || './', HERE = me.dataset.here || 'home';
  /* the home page has an address of its own in every language (a search engine reads one language an
     address): / — Russian, /en/, /zh/ (tools/build_atlas_site.py, HOME_PATHS); data-lang names the language of the
     page it stands on, the root has none and keeps choosing by the visitor */
  const PAGE_LANG = HERE === 'home' ? (me.dataset.lang || '') : '';
  const HOMES = {ru: '', en: 'en/', zh: 'zh/'};
  const homeOf = l => ROOT + (HOMES[l] || '');
  const R = document.documentElement;
  const LANGS = [['ru', 'RU'], ['en', 'EN'], ['zh', '中文']];
  const T = {
    ru: {home: 'Главная', atlas: 'Атлас', program: 'Программа', download: 'Скачать', author: 'Автор', dark: 'Тёмная тема', light: 'Светлая тема', brand: 'Азимут — на главную', lang: 'Язык', save: 'Сохранить Атлас для работы без сети', saving: 'Сохраняется…', saved: 'Атлас сохранён: работает без сети', saveFail: 'Не всё сохранилось — повторите при хорошей связи'},
    en: {home: 'Home', atlas: 'Atlas', program: 'Program', download: 'Download', author: 'Author', dark: 'Dark theme', light: 'Light theme', brand: 'Azimuth — home page', lang: 'Language', save: 'Keep the Atlas for reading offline', saving: 'Saving…', saved: 'The Atlas is kept: it works offline', saveFail: 'Not everything was kept — try again on a good connection'},
    zh: {home: '首页', atlas: '图谱', program: '程序', download: '下载', author: '作者', dark: '深色主题', light: '浅色主题', brand: '方位 — 返回首页', lang: '语言', save: '保存图谱以便离线使用', saving: '正在保存…', saved: '图谱已保存：可离线使用', saveFail: '未能全部保存——请在网络良好时重试'}
  };
  const S = 'fill="none" stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round"';
  const ICON = {
    home: `<svg viewBox="0 0 24 24" ${S}><path d="M3.5 11.2 12 4l8.5 7.2"/><path d="M6 9.6V20h12V9.6"/><path class="rb" d="M10 20v-5.6h4V20"/></svg>`,
    atlas: `<svg viewBox="0 0 24 24" ${S}><path d="M12 5C8 2 4 3 2 4v15c3-2 7-2 10 0 3-2 7-2 10 0V4c-3-1-6-1-10 1Zm0 0v14"/><path class="rb" d="M5 7l4 1M5 11l4 1M15 8l4-1M15 12l4-1"/></svg>`,
    program: `<svg viewBox="0 0 24 24" ${S}><rect x="3" y="4.5" width="18" height="12.5" rx="2"/><path d="M8.5 20.5h7M12 17v3.5"/><path class="rb" d="M7 13l3-3.5 2.5 2 4-4.5"/></svg>`,
    download: `<svg viewBox="0 0 24 24" ${S}><path d="M4 16.5V19a1.5 1.5 0 0 0 1.5 1.5h13A1.5 1.5 0 0 0 20 19v-2.5"/><path class="rb" d="M12 3.5v12M7.5 11 12 15.5 16.5 11"/></svg>`,
    author: `<svg viewBox="0 0 24 24" ${S}><circle cx="12" cy="12" r="9"/><path d="M12 11v6"/><circle class="rb" cx="12" cy="7.6" r="1.1" fill="currentColor"/></svg>`,
    save: `<svg viewBox="0 0 24 24" ${S}><path d="M7 18.5h10.2a4.3 4.3 0 0 0 .6-8.56A6 6 0 0 0 6.2 9.2 4.7 4.7 0 0 0 7 18.5Z"/><path class="rb" d="M12 9.5v5.5M9.6 12.8 12 15.2l2.400-2.400"/></svg>`,
    ok: `<svg viewBox="0 0 24 24" ${S}><path d="M7 18.5h10.2a4.3 4.3 0 0 0 .6-8.56A6 6 0 0 0 6.2 9.2 4.7 4.7 0 0 0 7 18.5Z"/><path class="rb" d="M9.3 12.7l2 2 3.6-3.900"/></svg>`,
    moon: `<svg viewBox="0 0 24 24" ${S}><path d="M20.5 14.2A8.5 8.5 0 0 1 9.8 3.5a8.5 8.5 0 1 0 10.7 10.7z"/></svg>`,
    sun: `<svg viewBox="0 0 24 24" ${S}><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.6M12 18.9v2.6M2.5 12h2.6M18.9 12h2.6M5.3 5.3l1.8 1.8M16.9 16.9l1.8 1.8M5.3 18.7l1.8-1.8M16.9 7.1l1.8-1.8"/></svg>`
  };
  const CSS = `
:root{--rail-w:68px;--rail-bg:linear-gradient(180deg,#f4f6fa,#e6ebf2);--rail-edge:#cfd7e2;--rail-ink:#1b2230;--rail-muted:#5b6474;--rail-hover:rgba(27,34,48,.07);--rail-on:rgba(42,98,184,.14);--rail-accent:#2a62b8;--rail-brown:#b8893f;--rail-rule:rgba(27,34,48,.12);--rail-tip:#fff}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--rail-bg:linear-gradient(180deg,#22304a,#172133);--rail-edge:#33435f;--rail-ink:#e7eaf0;--rail-muted:#9aa3b2;--rail-hover:rgba(255,255,255,.12);--rail-on:rgba(110,162,240,.22);--rail-accent:#6ea2f0;--rail-brown:#d6a95c;--rail-rule:rgba(255,255,255,.14);--rail-tip:#11151c}}
:root[data-theme="dark"]{--rail-bg:linear-gradient(180deg,#22304a,#172133);--rail-edge:#33435f;--rail-ink:#e7eaf0;--rail-muted:#9aa3b2;--rail-hover:rgba(255,255,255,.12);--rail-on:rgba(110,162,240,.22);--rail-accent:#6ea2f0;--rail-brown:#d6a95c;--rail-rule:rgba(255,255,255,.14);--rail-tip:#11151c}
body.hasRail{padding-left:var(--rail-w);box-sizing:border-box}
#siteRail{position:fixed;left:0;top:0;bottom:0;width:var(--rail-w);z-index:50;background:var(--rail-bg);border-right:1px solid var(--rail-edge);color:var(--rail-ink);display:flex;flex-direction:column;gap:6px;padding:16px 10px 14px;box-sizing:border-box;overflow:visible;transition:box-shadow .22s;font:500 13.5px/1.2 "Golos Text","PingFang SC","Microsoft YaHei","Segoe UI",system-ui,sans-serif;letter-spacing:.3px}
#siteRail a,#siteRail button{color:inherit;text-decoration:none;font:inherit;border:0;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:12px;height:44px;padding:0;border-radius:9px;white-space:nowrap;flex:none;width:46px;box-sizing:border-box;text-align:left;position:relative}
#siteRail a:hover,#siteRail button:hover{background:var(--rail-hover)}
#siteRail a,#siteRail button{-webkit-tap-highlight-color:transparent}
#siteRail a svg,#siteRail button svg{transition:transform .12s}
#siteRail a:active,#siteRail button:active{background:var(--rail-on)}  /* the press is seen */
#siteRail a:active svg,#siteRail button:active svg{transform:scale(.86)}
#siteRail a:focus-visible,#siteRail button:focus-visible{outline:2px solid var(--rail-accent);outline-offset:-2px}
#siteRail svg{width:22px;height:22px;flex:none}
/* the names are for a screen reader; for the eye — the note beside the icon (data-tip, set with the texts) */
#siteRail a span,#siteRail .rTheme span,#siteRail .rSave span{position:absolute;width:1px;height:1px;overflow:hidden;clip-path:inset(50%)}
@media (hover:hover) and (min-width:701px){
  #siteRail [data-tip]:hover::after,#siteRail [data-tip]:focus-visible::after{content:attr(data-tip);position:absolute;left:calc(100% + 12px);top:50%;transform:translateY(-50%);z-index:60;
    padding:6px 10px;border-radius:7px;background:var(--rail-ink);color:var(--rail-tip,#fff);font:500 13px/1.2 "Golos Text",system-ui,sans-serif;letter-spacing:0;text-transform:none;white-space:nowrap;pointer-events:none;box-shadow:0 4px 14px rgba(0,0,0,.22)}
}
#siteRail .rb{stroke:var(--rail-brown);color:var(--rail-brown)}
#siteRail a[aria-current="page"]{background:var(--rail-on);color:var(--rail-accent)}
#siteRail .rBrand{height:46px;padding:0 1px;gap:10px;font:600 15px/1 "Golos Text",system-ui,sans-serif;letter-spacing:.16em;text-transform:uppercase}
#siteRail .rBrand img{width:44px;height:44px;flex:none}
#siteRail .rBrand .dk{display:none}
:root[data-theme="dark"] #siteRail .rBrand .lt{display:none}
:root[data-theme="dark"] #siteRail .rBrand .dk{display:block}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) #siteRail .rBrand .lt{display:none}:root:not([data-theme="light"]) #siteRail .rBrand .dk{display:block}}
#siteRail .rRule{height:1px;background:var(--rail-rule);margin:6px 0 10px;flex:none}
#siteRail .rGap{flex:1}
#siteRail .rLang{display:flex;flex-direction:column;gap:2px}
#siteRail .rLang button{height:30px;font-size:12.5px;color:var(--rail-muted);padding:0;width:46px;justify-content:center;letter-spacing:.04em}
#siteRail .rLang button[aria-pressed="true"]{background:var(--rail-on);color:var(--rail-accent);font-weight:600}
#siteRail .rSave[hidden]{display:none}
#siteRail .rSave[data-state="busy"]{background:linear-gradient(90deg,var(--rail-on) calc(var(--p,0)*100%),transparent 0);cursor:progress}
#siteRail .rSave[data-state="done"]{color:var(--rail-accent)}
#siteRail .rSave span{white-space:normal;line-height:1.15;font-size:12px}
#siteRail .rCycle{display:none}
/* molecules and cells of crystals in thin lines behind the
   icons, under the line of the name — the background of the panel of the program (hub/chrome.py, MoleculeArt) */
#siteRail .rArt{position:absolute;left:0;width:var(--rail-w);height:auto;bottom:0;z-index:-1;pointer-events:none;overflow:hidden;color:var(--rail-accent);opacity:.22}
:root[data-theme="dark"] #siteRail .rArt{opacity:.19}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) #siteRail .rArt{opacity:.19}}
#siteRail .rArt *{fill:none;stroke:currentColor;stroke-width:1;vector-effect:non-scaling-stroke}
@media (max-width:700px){
  body.hasRail{padding-left:0;padding-bottom:54px}
  #siteRail .rArt{display:none}
  #siteRail{top:auto;right:0;width:auto;height:54px;flex-direction:row;align-items:center;gap:0;padding:0 6px;border-right:0;border-top:1px solid var(--rail-edge);box-shadow:none;justify-content:space-between}
  #siteRail a,#siteRail button{width:44px;height:44px;padding:0;justify-content:center}
  #siteRail button span,#siteRail .rRule,#siteRail .rGap,#siteRail .rLang{display:none}
  /* the design review §3 the pages of the bar with their names under the icons, each as wide
     as the bar allows (the switches of language and theme stay icons) */
  #siteRail a[data-nav]{flex:1 1 0;min-width:0;width:auto;height:50px;flex-direction:column;gap:3px;border-radius:10px}
  #siteRail a[data-nav] svg{width:21px;height:21px}
  #siteRail a[data-nav] span{position:static;width:auto;height:auto;clip-path:none;overflow:hidden;text-overflow:ellipsis;max-width:100%;
    font-size:9.5px;line-height:1.1;letter-spacing:-.1px;font-weight:500}
  #siteRail a[data-nav] span{display:none}  /* the name only under the page shown */
  #siteRail a[data-nav][aria-current="page"] span{display:block;font-weight:600}
  #siteRail .rCycle,#siteRail .rTheme,#siteRail .rSave{width:34px;flex:none}
  #siteRail{padding:0 4px}
  #siteRail .rBrand{display:none}
  /* the Atlas on a phone (a student, the search ran over the edge of the screen — the header was wider
     than the screen; Quill's fact came up over the text): the name smaller, the fact not shown */
  body.hasRail header .top{gap:8px}
  body.hasRail .qbrandH{zoom:.68}
  body.hasRail .qpart{display:none}
  body.hasRail .qtip{display:none!important}
  #siteRail .rCycle{display:flex;font-size:12.5px;font-weight:600;color:var(--rail-accent)}
}
@media (prefers-reduced-motion: reduce){#siteRail{transition:none}#siteRail a:active svg,#siteRail button:active svg{transform:none}}
@media print{#siteRail{display:none}body.hasRail{padding:0}}
/* the Atlas: its menu of topics slides out from under the panel; its own switches are hidden (QuASAtlas) */
body.hasRail .drawer{left:var(--rail-w)}
@media (max-width:700px){body.hasRail .drawer{left:0;bottom:54px}}
/* the design review §2 «больше область нажатия у стрелок пред./след. тема» — 26 px were
   hard to hit; 38 px, 44 on a touch screen (the arrow itself a little larger) */
body.hasRail .pgB{width:38px;height:38px;border-radius:8px}
body.hasRail .pgB svg{width:18px;height:18px}
@media (pointer:coarse){body.hasRail .pgB{width:44px;height:44px}}
/* a tip on the left
   stands beside the panel; on a phone, where the panel is a row at the bottom, above it */
body.hasRail .qtip.qtipL{left:calc(var(--rail-w) + 18px)}
@media (max-width:700px){body.hasRail .qtip.qtipL{left:12px}body.hasRail .qtip{bottom:calc(54px + 12px + env(safe-area-inset-bottom,0px))}}
/* the overview of the Atlas: «Продолжить» and «С чего начать» (the design review §11) */
.siteStart{display:flex;flex-wrap:wrap;align-items:center;gap:10px 14px;margin:0 0 18px}
.siteStart button{font:inherit;cursor:pointer}
.siteCont{flex-basis:100%;display:flex;align-items:center;gap:8px;text-align:left;padding:12px 16px;border-radius:12px;border:1px solid var(--accent,#2a62b8);background:var(--panel,#fff);color:var(--ink,#1b2230);font-size:15px}
.siteCont b{color:var(--accent,#2a62b8)}
.siteCont span{margin-left:auto;color:var(--accent,#2a62b8);font-size:18px}
.siteCont:hover{box-shadow:0 4px 14px rgba(0,0,0,.08)}
.siteStartH{font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:var(--accent,#2a62b8)}
.siteStartL{display:flex;flex-wrap:wrap;gap:8px}
.siteStartL button{display:inline-flex;align-items:center;gap:8px;padding:7px 14px 7px 8px;border-radius:99px;border:1px solid var(--line,#d8dce3);background:var(--panel,#fff);color:var(--ink,#1b2230);font-size:14px}
.siteStartL button:hover{border-color:var(--accent,#2a62b8);color:var(--accent,#2a62b8)}
.siteStartL i{font-style:normal;font-size:12px;font-weight:700;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;background:var(--accent,#2a62b8);color:#fff}
@media (max-width:700px){.siteStartH{flex-basis:100%}}
/* a phone: the name of the section took the row and the topic open was cut to «Постулат» — the section gives way */
@media (max-width:700px){body.hasRail .secT{max-width:38vw;overflow:hidden;text-overflow:ellipsis;font-size:14px;padding-right:10px}}
`;
  const store = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) {} return null; };
  const atlasApi = () => (HERE === 'atlas' && window.QuASAtlas) || null;

  function firstLang() {
    const q = new URLSearchParams(location.search).get('lang');
    if (T[q]) return q;
    if (T[PAGE_LANG]) return PAGE_LANG;
    const a = atlasApi();
    if (a && T[a.language()]) return a.language();
    const s = store('qc-hub-lang') || store('azimuth-site-lang');
    if (T[s]) return s;
    const n = (navigator.language || 'ru').slice(0, 2).toLowerCase();
    return T[n] ? n : 'en';
  }
  let lang = firstLang();
  const sys = matchMedia('(prefers-color-scheme: dark)');
  const isDark = () => { const t = R.getAttribute('data-theme'); return t === 'dark' || (t !== 'light' && sys.matches); };

  const style = document.createElement('style');
  style.textContent = CSS;
  document.head.appendChild(style);
  const rail = document.createElement('nav');
  rail.id = 'siteRail';
  const home = HERE === 'home' ? homeOf(PAGE_LANG || 'ru') : homeOf(lang), atlas = ROOT + 'atlas/';
  const items = [['home', home], ['atlas', HERE === 'home' ? home + '#atlas' : atlas], ['program', home + '#program'], ['download', home + '#download'], ['author', home + '#author']];
  rail.innerHTML =
    `<a class="rBrand" href="${home}"><img class="lt" src="${ROOT}img/glyph-light.svg" alt=""><img class="dk" src="${ROOT}img/glyph-dark.svg" alt=""><span data-k="brandName"></span></a><div class="rRule"></div>` +
    items.map(([k, href]) => `<a href="${href}" data-nav="${k}">${ICON[k]}<span data-k="${k}"></span></a>`).join('') +
    '<div class="rGap"></div><div class="rLang" role="group">' + LANGS.map(([k, l]) => `<button type="button" data-lang="${k}">${l}</button>`).join('') + '</div>' +
    '<button type="button" class="rSave" hidden></button><button type="button" class="rCycle"></button><button type="button" class="rTheme"></button>';
  document.body.insertBefore(rail, document.body.firstChild);
  document.body.classList.add('hasRail');

  /* The background of the panel: the drawings and their places are those of the program (hub/chrome.py, MoleculeArt —
     its column of the narrow rail): a row every ART.row px from the line under the name to the bottom, each moved,
     turned and scaled by a fixed scatter (the same numbers as in the program — the picture never changes). */
  const ART = {row: 104, edge: 26, reach: 30, jy: 22, jx: 9, cellTurn: 28, order: [0, 5, 12, 8, 2, 10, 6, 3, 14, 9, 1, 7, 11, 4, 13]};
  const artDrawings = (function () {
    const f = v => Math.round(v * 100) / 100;
    const L = (a, b, dash) => `<path d="M${f(a[0])} ${f(a[1])}L${f(b[0])} ${f(b[1])}"${dash ? ` stroke-dasharray="${dash}"` : ''}/>`;
    const C = (c, r) => `<circle cx="${f(c[0])}" cy="${f(c[1])}" r="${r}"/>`;
    const P = pts => `<path d="M${pts.map(p => f(p[0]) + ' ' + f(p[1])).join('L')}Z"/>`;
    const add = (a, b) => [a[0] + b[0], a[1] + b[1]], mul = (a, k) => [a[0] * k, a[1] * k];
    const unit = a => mul(a, 1 / Math.hypot(a[0], a[1])), rad = d => d * Math.PI / 180;
    const ring = (c, r, n) => Array.from({length: n}, (_, k) => [c[0] + r * Math.cos(rad(90 + 360 / n * k)), c[1] - r * Math.sin(rad(90 + 360 / n * k))]);
    const bonded = (c, r, ends, small) => C(c, r) + ends.map(e => { const d = unit(e); return L(add(c, mul(d, r)), add(add(c, e), mul(d, -small))) + C(add(c, e), small); }).join('');
    function cell(a, shift) {
      const front = [[-a / 2, -a / 2 + 4], [a / 2, -a / 2 + 4], [a / 2, a / 2 + 4], [-a / 2, a / 2 + 4]], back = front.map(p => add(p, shift));
      let out = P(front);
      for (let k = 0; k < 4; k++) {
        const hidden = k === 3;
        out += L(front[k], back[k], hidden && '3 2') + L(back[k], back[(k + 1) % 4], (hidden || (k + 1) % 4 === 3) && '3 2');
      }
      return {front, back, svg: out + front.concat(back).map(p => C(p, 2.4)).join('')};
    }
    return [
      function benzene() { const pts = ring([0, 0], 17, 6); return P(pts) + C([0, 0], 9.86) + pts.map(p => L(p, add(p, mul(unit(p), 7)))).join(''); },
      function water() { const o = [0, -6]; return C(o, 6) + [-1, 1].map(s => { const a = rad(90 + s * 52.25), d = [Math.cos(a), Math.sin(a)], h = add(o, mul(d, 21)); return L(add(o, mul(d, 6)), add(h, mul(d, -4))) + C(h, 4); }).join(''); },
      function chain() { const pts = [0, 1, 2, 3].map(k => [-21 + 14 * k, k % 2 ? -6 : 6]); return pts.slice(1).map((q, k) => L(pts[k], q)).join('') + pts.map(p => C(p, 2.2)).join('') + L(add(pts[1], [0, -2.2]), add(pts[1], [0, -14])) + C(add(pts[1], [0, -17]), 3); },
      function methane() { return C([0, 0], 5) + [[0, -20], [-18, 9], [15, 12], [15, -7]].map((e, k) => { const d = unit(e); return L(mul(d, 5), e, k === 3 && '3 2') + C(add(e, mul(d, 3)), 3); }).join(''); },
      function ammonia() { return bonded([0, -5], 5.5, [[-17, 13], [0, 20], [17, 13]], 3); },
      function carbonDioxide() { return C([0, 0], 4) + [-1, 1].map(s => C([s * 21, 0], 5.5) + [-2, 2].map(dy => L([s * 4.5, dy], [s * 15, dy])).join('')).join(''); },
      function ethene() { return [-2, 2].map(dy => L([-9, dy], [9, dy])).join('') + [-1, 1].map(s => [-13, 13].map(dy => L([s * 9, 0], [s * 20, dy]) + C([s * 22, dy + dy / 6.5], 2.6)).join('')).join(''); },
      function naphthalene() { const h = 13 * Math.cos(rad(30)); return [-1, 1].map(s => P(ring([s * h, 0], 13, 6)) + C([s * h, 0], 7.15)).join(''); },
      function pyridine() { const pts = ring([0, 0], 16, 6); return pts.map((p, k) => { const q = pts[(k + 1) % 6], d = unit([q[0] - p[0], q[1] - p[1]]); return L(add(p, mul(d, k === 0 ? 5 : 0)), add(q, mul(d, k === 5 ? -5 : 0))); }).join('') + C(pts[0], 5) + C([0, 0], 8.8); },
      function ethanol() { const pts = [[-20, 6], [-6, -6], [8, 6]]; return L(pts[0], pts[1]) + L(pts[1], pts[2]) + C(pts[0], 2.2) + C(pts[1], 2.2) + C([12, 9], 5) + L([16.5, 6.5], [26, -1]) + C([28.5, -3], 2.8); },
      function cyclopentane() { const pts = ring([0, 0], 15, 5); return P(pts) + pts.map(p => C(p, 2.2)).join(''); },
      function formaldehyde() { return C([0, -17], 5.5) + [-2, 2].map(dx => L([dx, 4], [dx, -11.5])).join('') + [-1, 1].map(s => L([0, 4], [s * 14, 15]) + C([s * 16, 16.6], 2.8)).join(''); },
      function cubicCell() { const c = cell(26, [11, -9]); return c.svg + c.front.map((p, k) => C(mul(add(p, c.front[(k + 1) % 4]), 0.5), 1.5)).join(''); },
      function centredCell() { const c = cell(26, [11, -9]), m = mul(add(c.front[0], c.back[2]), 0.5); return c.svg + C(m, 4) + L(m, c.front[3], '1 2') + L(m, c.back[1], '1 2'); },
      function hexagonalCell() {
        const hex = cy => Array.from({length: 6}, (_, k) => [17 * Math.cos(rad(60 * k)), cy - 7 * Math.sin(rad(60 * k))]), top = hex(-11), bottom = hex(13);
        return P(top) + top.map((p, k) => L(bottom[k], bottom[(k + 1) % 6], k < 3 && '3 2') + L(p, bottom[k], (k === 1 || k === 2) && '3 2')).join('') + top.concat(bottom).map(p => C(p, 2.2)).join('');
      }
    ];
  })();
  function artScatter(row, column, salt) {  // hub/chrome.py MoleculeArt._scatter, the same 32-bit numbers
    let n = (Math.imul(row, 374761393) + Math.imul(column, 668265263) + Math.imul(salt, 2246822519 | 0) + 3266489917) >>> 0;
    n = Math.imul(n ^ (n >>> 13), 1274126177) >>> 0;
    return ((n ^ (n >>> 16)) & 0xFFFF) / 0xFFFF;
  }
  function artPlaces(height) {  // [[drawing, x, y, turn °, scale]] under the line (y = 0) down to `height`
    const found = [], cells = artDrawings.length - 3;
    for (let row = 0; ; row++) {
      const base = ART.reach + 8 + row * ART.row;
      if (base > height - ART.edge) break;
      const r = [0, 1, 2, 3].map(salt => artScatter(row, 0, salt)), index = ART.order[row % ART.order.length];
      const y = Math.min(Math.max(base + (2 * r[0] - 1) * ART.jy, ART.reach), height - ART.edge);
      found.push([index, 34 + (2 * r[1] - 1) * ART.jx, y, (2 * r[2] - 1) * (index >= cells ? ART.cellTurn : 180), 0.74 + 0.30 * r[3]]);
    }
    return found;
  }
  const art = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  art.setAttribute('class', 'rArt');
  art.setAttribute('aria-hidden', 'true');
  rail.appendChild(art);
  function drawArt() {
    const rule = rail.querySelector('.rRule'), top = rule.offsetTop + rule.offsetHeight + 1, height = rail.clientHeight - top;
    if (!rule.offsetHeight || height < 60) { art.innerHTML = ''; return; }  // the bar of a phone: no background
    if (art.dataset.h === String(height)) return;
    art.dataset.h = String(height);
    art.style.top = top + 'px';
    art.style.height = height + 'px';  // «#siteRail svg» gives an icon its 22 px
    art.setAttribute('viewBox', `0 0 68 ${height}`);
    art.innerHTML = artPlaces(height).map(([k, x, y, turn, scale]) =>
      `<g transform="translate(${x.toFixed(1)} ${y.toFixed(1)}) rotate(${turn.toFixed(1)}) scale(${scale.toFixed(3)})">${artDrawings[k]()}</g>`).join('');
  }
  drawArt();
  addEventListener('resize', drawArt);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(drawArt);

  /* the parts of the home page the panel leads to; on the home page «Атлас» too goes to its part
     the Atlas itself is opened by the button «Открыть Атлас» */
  const PARTS = ['atlas', 'program', 'download', 'author'];
  let spied = null;
  function current() {
    if (HERE === 'atlas') return HERE;
    if (HERE === 'lost') return '';
    if (spied) return spied;
    const h = location.hash.slice(1);
    return PARTS.includes(h) ? h : 'home';
  }
  function texts() {
    const u = T[lang];
    rail.setAttribute('aria-label', lang === 'zh' ? '方位' : lang === 'en' ? 'Azimuth' : 'Азимут');
    rail.querySelectorAll('[data-k]').forEach(e => { e.textContent = e.dataset.k === 'brandName' ? (lang === 'zh' ? '方位' : lang === 'en' ? 'Azimuth' : 'Азимут') : u[e.dataset.k]; });
    rail.querySelector('.rBrand').title = u.brand;
    rail.querySelectorAll('[data-nav]').forEach(a => { a.title = u[a.dataset.nav]; if (a.dataset.nav === current()) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current'); });
    rail.querySelectorAll('[data-lang]').forEach(b => b.setAttribute('aria-pressed', String(b.dataset.lang === lang)));
    rail.querySelector('.rLang').setAttribute('aria-label', u.lang);
    const cycle = rail.querySelector('.rCycle');
    cycle.textContent = LANGS.find(x => x[0] === lang)[1]; cycle.title = u.lang;
    const sv = rail.querySelector('.rSave'), word = save.state === 'busy' ? u.saving + (save.total ? ' ' + Math.round(100 * save.done / save.total) + '%' : '') : save.state === 'done' ? u.saved : save.state === 'fail' ? u.saveFail : u.save;
    sv.innerHTML = (save.state === 'done' ? ICON.ok : ICON.save) + `<span>${word}</span>`; sv.title = word; sv.setAttribute('aria-label', word); sv.disabled = save.state === 'busy';
    sv.style.setProperty('--p', save.total ? save.done / save.total : 0); sv.dataset.state = save.state;
    const th = rail.querySelector('.rTheme'), name = isDark() ? u.light : u.dark;
    th.innerHTML = (isDark() ? ICON.sun : ICON.moon) + `<span>${name}</span>`; th.title = name; th.setAttribute('aria-label', name);
    if (HERE !== 'home') {  // away from the home page its links carry the language chosen
      rail.querySelectorAll('[data-nav]').forEach(a => {
        const k = a.dataset.nav;
        if (k === 'atlas' && HERE === 'atlas') return;
        const to = k === 'atlas' ? a.getAttribute('href') : homeOf(lang) + (k === 'home' ? '' : '#' + k);  // the home page of the language
        const u2 = new URL(to.split('?')[0], location.href); a.href = u2.pathname + '?lang=' + lang + u2.hash;
      });
      rail.querySelector('.rBrand').href = homeOf(lang) + '?lang=' + lang;
    }
    /* the name of every icon: beside it under the pointer (data-tip) and for a screen reader — not the slow note of the browser */
    rail.querySelectorAll('a, button').forEach(e => { if (e.title) { e.dataset.tip = e.title; e.setAttribute('aria-label', e.title); e.removeAttribute('title'); } });
  }
  /* without a network: sw.js keeps what was read; the button keeps the whole Atlas of the language shown */
  const save = {state: 'idle', done: 0, total: 0};
  function savedBefore() { return store('qc-site-saved') || ''; }
  if ('serviceWorker' in navigator && /^https?:$/.test(location.protocol)) {
    navigator.serviceWorker.register(ROOT + 'sw.js').then(() => {
      rail.querySelector('.rSave').hidden = false;
      fetch(ROOT + 'site-files.json', {cache: 'no-cache'}).then(r => r.json()).then(f => { save.version = f.version; if (savedBefore() === f.version + '|' + lang) { save.state = 'done'; texts(); } }).catch(() => {});
    }).catch(() => {});
    navigator.serviceWorker.addEventListener('message', e => {
      const d = e.data || {};
      if (d.type !== 'saved') return;
      save.done = d.done; save.total = d.total;
      if (d.total && d.done >= d.total || !d.total) { save.state = d.failed || !d.total ? 'fail' : 'done'; if (save.state === 'done' && save.version) store('qc-site-saved', save.version + '|' + d.lang); }
      texts();
    });
    rail.querySelector('.rSave').addEventListener('click', () => {
      navigator.serviceWorker.ready.then(reg => { save.state = 'busy'; save.done = 0; save.total = 0; texts(); reg.active.postMessage({type: 'save', lang}); });
    });
  }
  /* the address says the language shown (a student: after RU was chosen the address still said ?lang=en) */
  function address() {
    if (PAGE_LANG) return;  // /en/, /zh/: the address itself says the language
    try { const u = new URL(location.href); if (u.searchParams.get('lang') !== lang) { u.searchParams.set('lang', lang); history.replaceState(history.state, '', u); } } catch (e) {}
  }
  function setLang(v) {
    if (!T[v]) return false;
    if (HERE === 'home') {  // the home page of that language is another address: go there, to the same part
      const target = new URL(homeOf(v), location.href);
      if (target.pathname !== location.pathname) { store('qc-hub-lang', v); location.href = target.pathname + location.hash; return true; }
    }
    lang = v; store('qc-hub-lang', v);
    if (save.state !== 'busy') save.state = savedBefore() === save.version + '|' + v ? 'done' : 'idle';
    const a = atlasApi(); if (a) a.setLanguage(v);
    texts(); address();
    document.dispatchEvent(new CustomEvent('rail-lang', {detail: v}));
    return true;
  }
  function setTheme(v) {
    if (v !== 'light' && v !== 'dark') return false;
    const a = atlasApi();
    if (a) a.setTheme(v); else { R.setAttribute('data-theme', v); store('qc-theme', v); }
    texts();
    return true;
  }
  rail.querySelectorAll('[data-lang]').forEach(b => b.addEventListener('click', () => setLang(b.dataset.lang)));
  rail.querySelector('.rCycle').addEventListener('click', () => { const k = LANGS.findIndex(x => x[0] === lang); setLang(LANGS[(k + 1) % LANGS.length][0]); });
  rail.querySelector('.rTheme').addEventListener('click', () => setTheme(isDark() ? 'light' : 'dark'));
  sys.addEventListener('change', texts);
  new MutationObserver(texts).observe(R, {attributes: true, attributeFilter: ['data-theme']});
  addEventListener('hashchange', texts);

  /* the home page a part of the page is gone to without
     loading the page again (the address had ?lang=, the link had not — another address), the address keeps its
     language and gets the part; the icon lit is that of the part read now, as the page is scrolled */
  if (HERE === 'home') {
    /* while the page
       glides to the part pressed, every part it passes lit up in turn; now the part pressed stays lit until the
       glide ends (no scroll for 160 ms, «scrollend», at most 2 s) or the reader scrolls himself (wheel, touch, keys) */
    let going = null, quiet = 0, giveUp = 0;
    const arrive = () => { going = null; clearTimeout(quiet); clearTimeout(giveUp); };
    const goTo = k => { going = k; clearTimeout(giveUp); giveUp = setTimeout(arrive, 2000); };
    ['wheel', 'touchstart', 'keydown', 'mousedown'].forEach(t => addEventListener(t, e => {
      if (going && !(t === 'mousedown' && rail.contains(e.target))) arrive();
    }, {passive: true}));
    addEventListener('scrollend', () => { if (going) arrive(); });  // the part pressed stays lit where the glide stopped
    PARTS.forEach(k => rail.querySelector(`[data-nav="${k}"]`).addEventListener('click', e => {
      const part = document.getElementById(k);
      if (!part) return;
      e.preventDefault();
      goTo(k);
      part.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
      try { const u = new URL(location.href); u.hash = k; history.replaceState(history.state, '', u); } catch (err) {}
      spied = k; texts();
    }));
    rail.querySelector('[data-nav="home"]').addEventListener('click', e => {
      e.preventDefault();
      goTo('home');
      scrollTo({top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
      try { const u = new URL(location.href); u.hash = ''; history.replaceState(history.state, '', u); } catch (err) {}
      spied = 'home'; texts();
    });
    const spy = () => {
      if (going) {  // the glide to the part pressed: that part stays lit; its end is when the scroll stops
        clearTimeout(quiet); quiet = setTimeout(arrive, 160);
        if (spied !== going) { spied = going; texts(); }
        return;
      }
      const line = innerHeight * 0.35;  // the part whose top has passed a third of the window is the one read
      let now = 'home';
      PARTS.forEach(k => { const el = document.getElementById(k); if (el && el.getBoundingClientRect().top <= line) now = k; });
      if (innerHeight + scrollY >= document.documentElement.scrollHeight - 2) {  // the end of the page: the last part
        const last = PARTS.filter(k => document.getElementById(k)).pop(); if (last) now = last;
      }
      if (now !== spied) { spied = now; texts(); }
    };
    let ticking = false;
    addEventListener('scroll', () => { if (!ticking) { ticking = true; requestAnimationFrame(() => { ticking = false; spy(); }); } }, {passive: true});
    addEventListener('load', spy);
  }

  /* in the Atlas the panel's script stands right
     after the header (tools/build_atlas_site.py), before the long script of the page — the panel is drawn with the
     header; what talks to the page (window.QuASAtlas, the overview) is wired when the page has been read */
  function wireAtlas() {
    const a = atlasApi();
    if (a) { a.setThemeControl(false); if (a.setLanguageControl) a.setLanguageControl(false); }
    /* «Открыть в Компасе» of the topics opens the installed program by a link azimuth:// — on a computer only
       (the program is for macOS and Windows; a phone has nothing to open it with) */
    if (a && a.setControl && matchMedia('(pointer:fine)').matches) a.setControl('compass', 'link');
    // «Азимут» in the header of the Atlas leads to the home page of the site; «Атлас» of the panel — to its overview.
    // The word «Атлас» of the header and its book lead to the overview of the Atlas too (the link's own #home)
    const brand = document.getElementById('homeLink');
    if (brand) {
      brand.addEventListener('click', e => {
        if (e.target.closest && e.target.closest('.qpart, .qIco')) return;  // the Atlas: the page's own way to its overview
        e.preventDefault(); e.stopImmediatePropagation(); location.href = homeOf(lang) + '?lang=' + lang;
      }, true);
    }
    rail.querySelector('[data-nav="atlas"]').addEventListener('click', e => { e.preventDefault(); location.hash = '#home'; });
    /* a student: «чем дольше сидишь на сайте, тем дольше грузятся открываемые темы» — the page keeps every topic opened
       as a frame, each with its scripts and pictures. Here only the topic shown and the KEEP last ones stay; an older
       one is opened anew when asked for. (`frames` is the table of the page: {topic|language: iframe}.) */
    const KEEP = 3, seen = [];
    const prune = () => {
      let table; try { table = frames; } catch (e) { return; }
      if (!table || table === window || typeof table !== 'object') return;
      const shown = Object.keys(table).find(k => !table[k].hidden);
      if (shown) { const i = seen.indexOf(shown); if (i >= 0) seen.splice(i, 1); seen.push(shown); }
      const keep = new Set(seen.slice(-(KEEP + 1)));
      Object.keys(table).forEach(k => { if (!keep.has(k) && table[k].hidden) { table[k].remove(); delete table[k]; } });
      while (seen.length > KEEP + 1) seen.shift();
    };
    addEventListener('hashchange', () => setTimeout(prune, 50));
    /* the design review §11 on the overview of the Atlas «С чего начать» — a few first topics
       — and «Продолжить: <the topic read last>». The topics are pressed through the overview's own buttons
       (#grid .item[data-p]), their names are those the overview shows in the language chosen. */
    const START = ['post', 'hat', 'scf', 'lad'];  // the keys of the topics (data-p)
    const WORDS = {ru: ['С чего начать', 'Продолжить'], en: ['Where to start', 'Continue'], zh: ['从哪里开始', '继续']};
    const item = key => document.querySelector(`#grid .item[data-p="${key}"]`);
    const remember = () => { const k = location.hash.slice(1); if (item(k)) store('qc-site-last', k); };
    // the Atlas changes its address by history.replaceState/pushState (no «hashchange»): the address is looked at
    let seenHash = null;
    setInterval(() => { if (location.hash !== seenHash) { seenHash = location.hash; remember(); drawStart(); } }, 600);
    const startBox = document.createElement('div');  // drawn again only when its words change (it is in #home, watched)
    startBox.className = 'siteStart';
    const drawStart = () => {
      const grid = document.getElementById('grid');
      if (!grid || !grid.querySelector('.item')) return;
      if (startBox.parentNode !== grid.parentNode) grid.parentNode.insertBefore(startBox, grid);
      const w = WORDS[lang] || WORDS.ru, last = store('qc-site-last');
      const name = k => (item(k) && item(k).querySelector('b') ? item(k).querySelector('b').textContent : k);
      const html = (last && item(last) ? `<button type="button" class="siteCont" data-go="${last}">${w[1]}: <b>${name(last)}</b> <span aria-hidden="true">→</span></button>` : '') +
        `<div class="siteStartH">${w[0]}</div><div class="siteStartL">` +
        START.filter(item).map((k, i) => `<button type="button" data-go="${k}"><i>${i + 1}</i>${name(k)}</button>`).join('') + '</div>';
      if (startBox.dataset.drawn !== html) { startBox.dataset.drawn = html; startBox.innerHTML = html; }
    };
    startBox.addEventListener('click', e => { const b = e.target.closest('[data-go]'); if (b && item(b.dataset.go)) item(b.dataset.go).click(); });
    new MutationObserver(drawStart).observe(document.getElementById('home') || document.body, {childList: true, subtree: true, characterData: true});
    document.addEventListener('rail-lang', () => setTimeout(drawStart, 50));
    drawStart();
    setInterval(prune, 2000);
    setInterval(() => { const now = a && a.language(); if (now && T[now] && now !== lang) { lang = now; texts(); address(); } }, 500);  // changed inside the page
    texts();
  }
  if (HERE === 'atlas') {
    if (atlasApi() || document.readyState !== 'loading') wireAtlas();
    else document.addEventListener('DOMContentLoaded', wireAtlas);
  }
  texts();
  window.SiteRail = {lang: () => lang, setLang, theme: () => (isDark() ? 'dark' : 'light'), setTheme};
})();

/* Cross-page links (a[data-goto]).
   Inside the Atlas shell (index.html) the page asks the shell to switch the
   tab, so the shell keeps its header, history and language.  Opened on its
   own, the page simply follows the relative href: every language lives in its
   own folder with identical file names, so no file-name rewriting is needed. */
document.addEventListener('click', e => {
  const a = e.target.closest && e.target.closest('a[data-goto]');
  if (!a) return;
  if (window.parent !== window) {
    e.preventDefault();
    try { parent.postMessage({goto: a.dataset.goto}, location.origin === 'null' ? '*' : location.origin); } catch (err) {}
  }
});

/* Quail's pose overlapping «Что нужно понять» (assets/css/qpose.css): the box gets a
   float spacer exactly as tall as the part of the picture that hangs over it. */
(() => {
  const img = document.querySelector('.qPoseH > .qPose');
  const keys = img && document.querySelector('.qPoseH ~ .keys');
  if (!img || !keys) return;
  const fit = () => {
    /* a hidden page (the hub keeps other topics in hidden frames) has no layout: keep the last
       values, otherwise the box reflowed under the picture when the topic was shown again */
    if (!keys.getBoundingClientRect().width) return;
    keys.style.setProperty('--qpo', '0px');
    const r = img.getBoundingClientRect(), k = keys.getBoundingClientRect();
    const shown = getComputedStyle(img).display !== 'none' && r.height > 0;
    const over = shown ? Math.ceil(r.bottom - k.top) : 0;
    keys.style.setProperty('--qpo', Math.max(0, over) + 'px');
    keys.style.setProperty('--qpw', shown ? Math.ceil(r.width - 8) + 'px' : '0px');
    shape(r, k, Math.max(0, over), shown ? Math.ceil(r.width - 8) : 0);
  };
  /* the text of the box flows around Quill herself, not around the whole rectangle of the picture (its
     transparent margins kept the text away from the empty corner too). The outline is read from the alpha of the
     picture, row by row, and given to the spacer as shape-outside; on any error the spacer stays a rectangle. */
  let alpha = null;
  const outline = () => {
    if (alpha !== null) return alpha;
    alpha = false;
    try {
      const w = img.naturalWidth, h = img.naturalHeight;
      if (!w || !h) { alpha = null; return false; }
      const c = document.createElement('canvas'); c.width = w; c.height = h;
      const g = c.getContext('2d', {willReadFrequently: true}); g.drawImage(img, 0, 0);
      const d = g.getImageData(0, 0, w, h).data, left = new Float32Array(h);
      for (let y = 0; y < h; y++) {
        let x = 0; while (x < w && d[(y * w + x) * 4 + 3] < 40) x++;
        left[y] = x / w;  // share of the width that is empty on the left of this row (1: an empty row)
      }
      alpha = {left, w, h};
    } catch (err) { alpha = false; }  // a picture from file:// cannot be read: keep the rectangle
    return alpha;
  };
  const shape = (r, k, over, width) => {
    const a = over > 0 && width > 0 && outline();
    if (!a) { keys.style.removeProperty('--qps'); return; }
    // the drawn picture: object-fit contain, object-position right top inside the box r
    const s = Math.min(r.width / a.w, r.height / a.h), dw = a.w * s, x0 = r.right - dw, y0 = r.top;
    // the spacer: floats right with margins -10px (top) and -16px (right) in the content box of keys
    const cs = getComputedStyle(keys), top = k.top + parseFloat(cs.borderTopWidth) + parseFloat(cs.paddingTop) - 10;
    const right = k.right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight) + 16, sx = right - width;
    const pts = [[width, 0]], step = 6;
    for (let y = 0; y < over; y += step) {
      let m = 1;
      for (let yy = y; yy < Math.min(over, y + step); yy++) {
        const row = Math.floor((top + yy - y0) / s);
        if (row >= 0 && row < a.h) m = Math.min(m, a.left[row]);
      }
      const x = m >= 1 ? width : Math.max(0, Math.min(width, x0 + m * dw - sx - 10));
      pts.push([x, y], [x, Math.min(over, y + step)]);
    }
    pts.push([width, over]);
    keys.style.setProperty('--qps', 'polygon(' + pts.map(([x, y]) => x.toFixed(1) + 'px ' + y.toFixed(1) + 'px').join(',') + ') border-box');
  };
  if (img.complete) fit(); else img.addEventListener('load', fit);
  addEventListener('resize', fit);
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
  if (window.ResizeObserver) new ResizeObserver(fit).observe(img.parentElement);
})();

/* «Открыть в Компасе»: a page names its molecules in <meta name="qc-molecules" content="water,…">;
   inside Azimuth (the hub sends {hub:1, compass:true}) a row of buttons appears under the lead, and a click asks
   the program to open the molecule from the library of Compass ("Azimuth:compass <key>" in the console, read by
   modules/atlas/browser.py). In a plain browser nothing is shown — except on the site, whose shell sends
   {compass:'link'}: there a click opens the address azimuth://compass/<key>, which the system gives to the installed
   program (azimuth/links.py); the address is opened in a hidden frame, so that a browser without the program
   leaves the page as it is, and a line under the buttons says what the buttons need. */
(() => {
  const meta = document.querySelector('meta[name="qc-molecules"]');
  if (!meta) return;
  const keys = meta.content.split(',').map(k => k.trim()).filter(k => /^[a-z0-9]+$/.test(k));
  const F = {water: 'H₂O', ammonia: 'NH₃', methane: 'CH₄', co2: 'CO₂', bf3: 'BF₃', benzene: 'C₆H₆', ethene: 'C₂H₄',
    hf: 'HF', n2: 'N₂', butadiene: 'C₄H₆', naphthalene: 'C₁₀H₈', pyridine: 'C₅H₅N', pyrrole: 'C₄H₄NH', furan: 'C₄H₄O',
    formaldehyde: 'H₂CO', phenol: 'C₆H₅OH', so3: 'SO₃', h2o2: 'H₂O₂', ethane: 'C₂H₆', cyclohexane: 'C₆H₁₂',
    butane: 'C₄H₁₀', acetic: 'CH₃COOH', methanol: 'CH₃OH', acetone: '(CH₃)₂CO', hcl: 'HCl', ethanol: 'C₂H₅OH'};
  const T = {ru: 'Открыть в Компасе', en: 'Open in Compass', zh: '在罗盘中打开'};
  const N = {ru: 'Нужна установленная программа «Азимут».', en: 'The installed program Azimuth is needed.',
    zh: '需要已安装的“方位”程序。'};
  const lang = (document.documentElement.lang || 'ru').slice(0, 2);
  const viaLink = k => {
    const f = document.createElement('iframe');
    f.style.display = 'none'; f.setAttribute('aria-hidden', 'true');
    f.src = 'azimuth://compass/' + k;
    document.body.appendChild(f);
    setTimeout(() => f.remove(), 3000);
  };
  let row = null;
  addEventListener('message', e => {
    if (row || e.source !== parent || !e.data || !e.data.hub || !e.data.compass) return;
    row = document.createElement('div');
    row.className = 'toCompass';
    const lab = document.createElement('span');
    lab.className = 'tcL';
    lab.innerHTML = '<svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true"><circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" stroke-width="1.8"/><path d="M15.5 8.5l-2 5-5 2 2-5z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"/></svg>' + (T[lang] || T.ru);
    row.appendChild(lab);
    keys.filter(k => F[k]).forEach(k => {
      const b = document.createElement('button');
      b.type = 'button'; b.className = 'tcB'; b.textContent = F[k];
      b.title = (T[lang] || T.ru) + ': ' + F[k];
      b.onclick = () => e.data.compass === 'link' ? viaLink(k) : console.log('Azimuth:compass ' + k);
      row.appendChild(b);
    });
    if (e.data.compass === 'link') {
      const note = document.createElement('span');
      note.className = 'tcL'; note.textContent = N[lang] || N.ru;
      row.appendChild(note);
    }
    const head = document.querySelector('main > header') || document.querySelector('header');
    if (head) head.appendChild(row);
  });
})();

/* 2.15.0: the arrow keys inside a topic shown in the Atlas — ← → ask the shell for the previous / next topic (the
   arrows ‹ › of the row of topics); ↑ ↓ scroll the page (the browser does it; the shell sends {qcScroll} when the
   focus is in the shell itself). Left alone: fields, sliders, the demonstration (body.demoOn), the projector mode
   (html.proj — its own ← → go through the sections), keys with modifiers, and keys a widget took (defaultPrevented). */
(() => {
  if (window.parent === window) return;
  const busy = e => {
    const t = e.target || {};
    return e.defaultPrevented || e.altKey || e.ctrlKey || e.metaKey || e.shiftKey || /INPUT|TEXTAREA|SELECT/.test(t.tagName || '')
      || t.isContentEditable || document.documentElement.classList.contains('proj')
      || (document.body && document.body.classList.contains('demoOn'));
  };
  addEventListener('keydown', e => {
    if ((e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') || busy(e)) return;
    e.preventDefault();
    try { parent.postMessage({qcFlip: e.key === 'ArrowRight' ? 1 : -1}, '*'); } catch (err) {}
  });
  addEventListener('message', e => {
    if (e.source !== parent || !e.data || (e.data.qcScroll !== 1 && e.data.qcScroll !== -1)) return;
    window.scrollBy({top: e.data.qcScroll * 80, behavior: 'smooth'});
  });
})();

/* the blocks of a topic are numbered everywhere, as in the topics that had numbers in their titles. The number
   is drawn by CSS (data-n), the text of the heading stays as it is (the search of the hub finds a heading by its text);
   a topic whose headings are already numbered is left alone. */
(() => {
  const heads = [...document.querySelectorAll('main section.panel > h2, main section.desc > h2')]
    .filter(h => !h.closest('.keys, .try, .nextQ, .limits, .selfBox'));
  if (heads.length < 2 || heads.some(h => /^\d+\.\s/.test(h.textContent.trim()))) return;
  heads.forEach((h, i) => { h.dataset.n = i + 1; });
  const s = document.createElement('style');
  s.textContent = 'main h2[data-n]::before{content:attr(data-n) ". "}';
  document.head.appendChild(s);
})();

/* a round button «up» at the bottom right — the page scrolls back to its top; shown once the page has been
   scrolled down by more than a screen (above the theme button when that one is shown) */
(() => {
  const T = {ru: 'Наверх', en: 'Back to top', zh: '回到顶部'};
  const lang = (document.documentElement.lang || 'ru').slice(0, 2);
  const b = document.createElement('button');
  b.type = 'button';
  b.className = 'toTop';
  b.title = T[lang] || T.ru;
  b.setAttribute('aria-label', b.title);
  b.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path d="M12 19V5M5.5 11.5L12 5l6.5 6.5" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>';
  b.onclick = () => scrollTo({top: 0, behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'});
  const s = document.createElement('style');
  s.textContent = '.toTop{position:fixed;right:14px;bottom:106px;z-index:40;width:38px;height:38px;border-radius:50%;border:1px solid var(--line);background:var(--panel);color:var(--accent);cursor:pointer;box-shadow:0 2px 10px rgba(0,0,0,.15);display:flex;align-items:center;justify-content:center;padding:0;opacity:0;pointer-events:none;transform:translateY(8px);transition:opacity .2s ease,transform .2s ease,background-color .15s ease}'
    + '.toTop.on{opacity:1;pointer-events:auto;transform:none}.toTop:hover{background:color-mix(in srgb,var(--accent) 12%,var(--panel))}.toTop:active{transform:scale(.92);background:var(--accent);color:var(--accent-ink,#fff)}'
    + '.inHub .toTop{bottom:14px}@media print{.toTop{display:none}}';
  document.head.appendChild(s);
  document.body.appendChild(b);
  const sync = () => b.classList.toggle('on', scrollY > innerHeight);
  addEventListener('scroll', sync, {passive: true});
  sync();
})();

/* the names of the rows of controls (.crow > .l) are as wide as the longest name of their block, not 170 px
   everywhere — a short name no longer stands far from its buttons; the rows of one block stay aligned */
(() => {
  const fit = () => {
    const groups = new Map();
    document.querySelectorAll('main .crow > .l').forEach(l => {
      const block = l.closest('section, .controls, details, main');
      if (!groups.has(block)) groups.set(block, []);
      groups.get(block).push(l);
    });
    groups.forEach(labels => {
    labels.forEach(l => { l.style.minWidth = '0'; });
    const widest = Math.max(...labels.map(l => l.getBoundingClientRect().width));
    if (widest > 0) labels.forEach(l => { l.style.minWidth = Math.ceil(widest + 6) + 'px'; });
    });
  };
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit); else fit();
  addEventListener('load', fit);
})();

/* when a table or a list of results is redrawn after a
   slider or a button, the cells whose value changed light up for a moment */
(() => {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches) return;
  const s = document.createElement('style');
  s.textContent = '@keyframes qcChg{from{background:color-mix(in srgb,var(--warn,#d9822b) 30%,transparent)}to{background:transparent}}'
    + '.qcChg{animation:qcChg 1.2s ease-out}';
  document.head.appendChild(s);
  const cells = box => [...box.querySelectorAll(box.tagName === 'TABLE' || box.querySelector('table') ? 'td' : ':scope > b, :scope > span:nth-child(even)')];
  const snap = box => cells(box).map(c => c.textContent.trim());
  const watch = box => {
    if (box._qcWatch) return;
    box._qcWatch = true;
    box._qcSnap = snap(box);
    new MutationObserver(() => {
      const now = cells(box), before = box._qcSnap || [];
      if (before.length && now.length === before.length) {
        now.forEach((c, i) => { if (c.textContent.trim() !== before[i]) { c.classList.remove('qcChg'); void c.offsetWidth; c.classList.add('qcChg'); } });
      }
      box._qcSnap = now.map(c => c.textContent.trim());
    }).observe(box, {childList: true, subtree: true, characterData: true});
  };
  // the box of a table that is written anew by innerHTML is its parent: that one stays
  const scan = () => document.querySelectorAll('main table, main .kvt').forEach(b => { if (b.closest('.try')) return; const host = b.tagName === 'TABLE' && b.parentElement && !/^(SECTION|MAIN)$/.test(b.parentElement.tagName) && b.parentElement.children.length === 1 ? b.parentElement : b; watch(host); });
  scan();
  new MutationObserver(scan).observe(document.querySelector('main') || document.body, {childList: true, subtree: true});
})();

/* a fraction written with a slash in the text of a topic — E/RT, ħ²/(2mr²), 1/r, (d/h) — is typeset as a fraction
   (the .fr of assets/css/formula.css), also in the texts the page writes later. Units (кДж/моль, г/см³, eV/Å…), names
   of methods and bases (HF/6-31G*, TZ/QZ) and words stay as they are. */
(() => {
  const ATOM = String.raw`(?:\([^()\s][^()]{0,28}\)|[A-Za-zα-ωΑ-Ωħε√∞πΔΣ0-9₀-₉⁰-⁹²³⁺⁻′'‡·]{1,9})`;
  const RE = new RegExp(String.raw`(^|[\s(=≈~−+×·,:;[{])(${ATOM})\s?/\s?(${ATOM})(?=$|[\s)=≈,.;:!?\]}+−×·²³⁰-⁹])`, 'g');
  const UNIT = /^(?:моль|mol|K|К|с|s|Å|бор|bohr|см|cm|м|m|нм|nm|пм|pm|ГГц|МГц|Гц|Hz|MHz|GHz|л|L|ч|h₀|сек|мин|min|г|g|кг|kg|ккал|kcal|кДж|kJ|Дж|J|эВ|eV|атом|atom|ат|at)(?:[⁻⁰-⁹²³·()]|$)/;
  const SKIP = /[а-яё]|^\d+-\d|^(?:HF|DFT|LDA|GGA|MP\d|CCSD\S*|CISD\S*|CI|CAS\S*|TZ|QZ|DZ|SZ|5Z|6Z|cc-\S*|aug-\S*|def2\S*|STO\S*|B3LYP|PBE\S*|xtb|GFN\S*|RHF|UHF|ROHF|SCF|KS)$/i;
  const strip = s => (s[0] === '(' && s[s.length - 1] === ')' ? s.slice(1, -1) : s);
  const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
  const LABEL = /^[A-Z][a-z]?\d*$/, WORD = /^[A-Za-z]{4,}$/;
  function convert(text, tailSub) {
    let changed = false;
    const out = text.replace(RE, (m, pre, a, b, at) => {
      if (SKIP.test(a) || SKIP.test(b) || UNIT.test(b) || /^\d+$/.test(a) && /^\d{3,}$/.test(b)) return m;
      if (LABEL.test(a) && LABEL.test(b) && /[a-z\d]/.test(a + b) || WORD.test(a) && WORD.test(b) || /^[A-Z]{2,}\d*$/.test(a) && /^[A-Z]{2,}\d*$/.test(b)) return m;  // C1/C3, He/H, words
      const start = at + pre.length, end = at + m.length;
      if (/[\d][,.]?$/.test(text.slice(0, start)) && pre === ',' || /^[,.]\d/.test(text.slice(end))) return m;  // 0,2677/0,2692
      if (end === text.length && tailSub) return m;  // r/r<sub>e</sub>: the subscript belongs to the denominator
      changed = true;
      return pre + '\u0000' + strip(a) + '\u0001' + strip(b) + '\u0002';
    });
    return changed ? out : null;
  }
  function walk(root) {
    const w = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {acceptNode: n =>
      !n.data.includes('/') || n.parentElement.closest('svg,script,style,code,pre,textarea,input,select,button,h1,h2,h3,.t,.fr,.demoBar,a[href],.noFrac')
        ? NodeFilter.FILTER_REJECT : NodeFilter.FILTER_ACCEPT});
    const nodes = [];
    while (w.nextNode()) nodes.push(w.currentNode);
    nodes.forEach(n => {
      if (/^(SUB|SUP)$/.test(n.parentElement.nodeName)) return;  // inside an index: E_corr^FCI/n is not a fraction of the index
      const prev = n.previousSibling;
      if (prev && /^(SUB|SUP)$/.test(prev.nodeName) && /^\s?\//.test(n.data)) return;  // E<sub>x</sub>/n: the numerator is longer
      const next = n.nextSibling, out = convert(n.data, !!(next && /^(SUB|SUP)$/.test(next.nodeName)));
      if (out === null) return;
      const span = document.createElement('span');
      span.innerHTML = esc(out).replace(/\u0000/g, '<span class="fr" data-auto="1"><span>').replace(/\u0001/g, '</span><span>').replace(/\u0002/g, '</span></span>');
      n.replaceWith(...span.childNodes);
    });
  }
  const main = document.querySelector('main');
  if (!main) return;
  walk(main);
  let queued = false;
  new MutationObserver(() => { if (!queued) { queued = true; requestAnimationFrame(() => { queued = false; walk(main); }); } })
    .observe(main, {childList: true, subtree: true, characterData: true});
})();

/* the buttons «▶ Пуск», «❚❚ Пауза», «■ Стоп» of the topics
   show only their icon; the words go to the tooltip. The page changes the text of such a button while it plays — the
   icon follows. */
(() => {
  const ICON = {
    '▶': '<path d="M8 5.5v13l10.5-6.5z" fill="currentColor"/>',
    '❚❚': '<path d="M7.5 5.5h3v13h-3zM13.5 5.5h3v13h-3z" fill="currentColor"/>',
    '■': '<path d="M7 7h10v10H7z" fill="currentColor"/>',
  };
  const RE = /^\s*(▶|❚❚|■)︎?\s+(.+?)\s*$/;
  const iconize = b => {
    if (b.closest('.demoBar') || b.classList.contains('demoBtn')) return;
    const m = RE.exec(b.textContent || '');
    if (!m || b.querySelector('svg.icoS')) return;
    b._iconizing = true;
    b.title = m[2];
    b.setAttribute('aria-label', m[2]);
    b.classList.add('icoB');
    b.innerHTML = '<svg class="icoS" viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' + ICON[m[1]] + '</svg>';
    b._iconizing = false;
  };
  const s = document.createElement('style');
  s.textContent = 'button.icoB{display:inline-flex;align-items:center;justify-content:center;min-width:38px;padding-left:8px!important;padding-right:8px!important}';
  document.head.appendChild(s);
  const all = () => document.querySelectorAll('main button').forEach(iconize);
  all();
  new MutationObserver(ms => { for (const m of ms) { const b = m.target.closest && m.target.closest('button'); if (b && !b._iconizing) iconize(b); else if (m.addedNodes.length) all(); } })
    .observe(document.querySelector('main') || document.body, {childList: true, subtree: true, characterData: true});
})();
/* the list of a <select> opens in the style of the Atlas (rounded card with a shadow, smooth), not as the square
   list of the system. The <select> itself stays: its value, its «change» event and the keyboard (arrows on the closed
   field) work as before; a click or Enter/Space/Alt+↓ opens the list. */
(function () {
  const css = document.createElement('style');
  css.textContent = '.qcList{position:fixed;z-index:60;min-width:120px;max-height:320px;overflow:auto;padding:4px;margin:0;list-style:none;'
    + 'background:var(--panel,#fff);color:var(--ink,#1b2230);border:1px solid var(--line,#d8dce3);border-radius:10px;'
    + 'box-shadow:0 10px 28px rgba(15,25,45,.18);font:inherit;font-size:14px;opacity:0;transform:translateY(-4px);'
    + 'transition:opacity .14s ease,transform .14s ease}.qcList.on{opacity:1;transform:none}'
    + '.qcList li{padding:6px 12px;border-radius:7px;cursor:pointer;white-space:nowrap}'
    + '.qcList li.cur{background:var(--acc-bg,#e3ecfa)}.qcList li.sel{font-weight:600;color:var(--accent,#2a62b8)}'
    + '.qcList li[aria-disabled="true"]{opacity:.45;cursor:default}'
    + '@media (prefers-reduced-motion:reduce){.qcList{transition:none}}';
  document.head.appendChild(css);
  let list = null, owner = null;
  function close(focus) {
    if (!list) return;
    const l = list; list = null; l.classList.remove('on'); setTimeout(() => l.remove(), 150);
    if (focus && owner) owner.focus();
    owner = null;
    removeEventListener('scroll', onScroll, true);
  }
  function place() {
    if (!list || !owner) return;
    const r = owner.getBoundingClientRect(), h = list.offsetHeight, below = innerHeight - r.bottom - 8;
    if (r.bottom < 0 || r.top > innerHeight) { close(false); return; }
    list.style.left = Math.max(8, Math.min(r.left, innerWidth - list.offsetWidth - 8)) + 'px';
    list.style.top = (below >= h || below >= r.top ? r.bottom + 4 : Math.max(8, r.top - h - 4)) + 'px';
  }
  function onScroll(e) { if (list && !list.contains(e.target)) place(); }  // the page scrolls: the list follows its field
  function pick(sel, i) {
    if (i < 0 || sel.options[i].disabled) return;
    if (sel.selectedIndex !== i) {
      sel.selectedIndex = i;
      sel.dispatchEvent(new Event('input', {bubbles: true}));
      sel.dispatchEvent(new Event('change', {bubbles: true}));
    }
    close(true);
  }
  function open(sel) {
    close(false);
    owner = sel;
    const r = sel.getBoundingClientRect();
    const ul = list = document.createElement('ul');
    ul.className = 'qcList'; ul.setAttribute('role', 'listbox');
    [...sel.options].forEach((o, i) => {
      const li = document.createElement('li');
      li.textContent = o.textContent; li.setAttribute('role', 'option');
      if (o.disabled) li.setAttribute('aria-disabled', 'true');
      if (i === sel.selectedIndex) li.className = 'sel cur';
      li.addEventListener('mousedown', e => e.preventDefault());
      li.addEventListener('click', () => pick(sel, i));
      li.addEventListener('mousemove', () => { ul.querySelectorAll('.cur').forEach(x => x.classList.remove('cur')); li.classList.add('cur'); });
      ul.appendChild(li);
    });
    document.body.appendChild(ul);
    ul.style.minWidth = r.width + 'px';
    place();
    const cur = ul.querySelector('.cur'); if (cur) cur.scrollIntoView({block: 'nearest'});
    requestAnimationFrame(() => ul.classList.add('on'));
    addEventListener('scroll', onScroll, true);
  }
  const usable = s => s && s.tagName === 'SELECT' && !s.multiple && !(s.size > 1) && !s.disabled;
  document.addEventListener('mousedown', e => {
    const s = e.target.closest && e.target.closest('select');
    if (usable(s)) { e.preventDefault(); s.focus({preventScroll: true}); list && owner === s ? close(false) : open(s); return; }
    if (list && !list.contains(e.target)) close(false);
  }, true);
  document.addEventListener('keydown', e => {
    if (list && owner) {
      const items = [...list.children];
      let i = items.findIndex(x => x.classList.contains('cur'));
      const move = d => { do { i = Math.max(0, Math.min(items.length - 1, i + d)); } while (owner.options[i].disabled && i > 0 && i < items.length - 1);
        items.forEach(x => x.classList.remove('cur')); items[i].classList.add('cur'); items[i].scrollIntoView({block: 'nearest'}); };
      if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
      else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
      else if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); pick(owner, i); }
      else if (e.key === 'Escape' || e.key === 'Tab') { if (e.key === 'Escape') e.preventDefault(); close(e.key === 'Escape'); }
      return;
    }
    const s = e.target;
    if (usable(s) && (e.key === 'Enter' || e.key === ' ' || (e.altKey && e.key === 'ArrowDown'))) { e.preventDefault(); open(s); }
  }, true);
  addEventListener('blur', () => close(false));
  addEventListener('resize', () => close(false));
})();

/* Topic pages of the Atlas on the site (see atlas-page.css): the numbers of the axes on a phone, tables that can be
   moved, «Перейти к модели». Put into every topic page by tools/build_atlas_site.py. */
(function () {
  'use strict';
  var lang = (document.documentElement.lang || 'ru').slice(0, 2);
  var narrow = function () { return window.innerWidth <= 640; };

  /* The labels of a plot are written in the units of its drawing (font-size="12" of a drawing 560 wide), and a phone
     shows the drawing at half its size: the numbers of the axes came out 7 px high. All the labels of a drawing are
     enlarged by one factor — the largest of FACTORS at which no label runs into another or over the edge of the
     drawing that did not do so at its own size (the number of a tick stands right above the name of its axis); a
     label is not made larger than MIN px on the screen. The factor of a drawing is found once and kept until the
     drawing changes its size or the number of its labels: plots are drawn anew many times a second. */
  var MIN = 10.5, FACTORS = [1.55, 1.4, 1.25, 1.12];
  function apply(texts, scale, factor) {
    for (var i = 0; i < texts.length; i++) {
      var t = texts[i], own = parseFloat(t.getAttribute('font-size'));
      if (!own) continue;
      var wanted = factor > 1 && own * scale < MIN ? Math.min(own * factor, MIN / scale) : 0;
      if (wanted) { t.style.fontSize = wanted.toFixed(2) + 'px'; t.dataset.siteSize = '1'; }
      else if (t.dataset.siteSize) { t.style.fontSize = ''; delete t.dataset.siteSize; }
    }
  }
  /* the box of a label is taller than its letters (room for accents and tails): the middle of it is compared */
  function trouble(svg, texts, box) {  // labels that touch one another or leave the drawing
    var boxes = [], count = 0, i, j;
    for (i = 0; i < texts.length; i++) {
      var r = null;
      try { var b = texts[i].getBBox(), m = texts[i].getCTM(), s = svg.getCTM(); if (b.width && m && s) { var k = m.a / s.a; r = {x: (m.e - s.e) / s.a + b.x * k + box.x, y: (m.f - s.f) / s.d + b.y * (m.d / s.d) + box.y, w: b.width * k, h: b.height * (m.d / s.d)}; } } catch (e) {}
      if (!r) continue;
      if (r.x < box.x - 1 || r.x + r.w > box.x + box.width + 1) count++;
      boxes.push(r);
    }
    for (i = 0; i < boxes.length; i++) for (j = i + 1; j < boxes.length; j++) {
      var p = boxes[i], q = boxes[j], pad = 0.5;
      if (p.x + pad < q.x + q.w && q.x + pad < p.x + p.w && p.y + p.h * 0.2 < q.y + q.h * 0.85 && q.y + q.h * 0.2 < p.y + p.h * 0.85) count++;
    }
    return count;
  }
  var kept = new WeakMap();
  function labels(svg) {
    var box = svg.viewBox && svg.viewBox.baseVal, width = svg.getBoundingClientRect().width;
    if (!box || !box.width || !width) return;
    var texts = svg.querySelectorAll('text[font-size]');
    if (!texts.length) return;
    var scale = width / box.width;
    if (!narrow() || scale >= 0.86) { apply(texts, scale, 1); kept.delete(svg); return; }
    var sign = texts.length + '|' + Math.round(width) + '|' + box.width, was = kept.get(svg);
    if (was && was.sign === sign) { apply(texts, scale, was.factor); return; }
    apply(texts, scale, 1);
    var allowed = trouble(svg, texts, box), factor = 1;
    if (texts.length <= 400) for (var f = 0; f < FACTORS.length; f++) {
      apply(texts, scale, FACTORS[f]);
      if (trouble(svg, texts, box) <= allowed) { factor = FACTORS[f]; break; }
    }
    apply(texts, scale, factor);
    kept.set(svg, {sign: sign, factor: factor});
  }
  var dirty = new Set(), queued = false, tabled = false;
  function sweep() { queued = false; dirty.forEach(function (svg) { if (svg.isConnected) labels(svg); }); dirty.clear(); }
  function mark(svg) { if (!svg) return; dirty.add(svg); if (!queued) { queued = true; requestAnimationFrame(sweep); } }
  function all() { var list = document.querySelectorAll('svg[viewBox]'); for (var i = 0; i < list.length; i++) mark(list[i]); }
  new MutationObserver(function (records) {
    for (var i = 0; i < records.length; i++) {
      var node = records[i].target;
      var svg = node.nodeType === 1 ? (node.closest ? node.closest('svg[viewBox]') : null) : null;
      if (svg) mark(svg);
      else if (node.nodeType === 1 && records[i].addedNodes.length && node.querySelector && node.querySelector('svg[viewBox]')) all();
      if (node.nodeType === 1 && node.closest && !tabled && (node.closest('table, .tablewrap') || (records[i].addedNodes.length && node.querySelector && node.querySelector('table')))) { tabled = true; setTimeout(function () { tabled = false; tables(); }, 150); }
    }
  }).observe(document.documentElement, {childList: true, subtree: true});
  addEventListener('resize', all);

  /* Every table can be moved sideways when it is wider than the screen; the edge is shaded while there is more. */
  function tables() {
    var list = document.querySelectorAll('main table');
    for (var i = 0; i < list.length; i++) {
      var table = list[i];
      if (!table.closest('.tablewrap')) {
        var wrap = document.createElement('div');
        wrap.className = 'tablewrap';
        table.parentNode.insertBefore(wrap, table);
        wrap.appendChild(table);
      }
    }
    var cells = document.querySelectorAll('main table td, main table th');
    for (var k = 0; k < cells.length; k++) cells[k].classList.toggle('siteLong', cells[k].textContent.trim().length > LONG);
    shade();
  }
  var LONG = 26;
  function shade() {
    var list = document.querySelectorAll('.tablewrap');
    for (var i = 0; i < list.length; i++) {
      var w = list[i];
      w.classList.toggle('more', w.scrollWidth - w.clientWidth - w.scrollLeft > 4);
      if (!w.dataset.siteWatched) { w.dataset.siteWatched = '1'; w.addEventListener('scroll', shade, {passive: true}); }
    }
  }
  addEventListener('resize', shade);

  /* «Перейти к модели»: on a phone the first control of a topic lies several screens below its introduction. The
     link stands under the lead and leads to the panel of the first control; the text of the topic is not moved. */
  var WORDS = {ru: 'Перейти к модели', en: 'Go to the model', zh: '前往模型'};
  function toModel() {
    var header = document.querySelector('main > header');
    if (!header || header.querySelector('.toModel')) return;
    var first = document.querySelector('main > section input[type=range], main > section select, main > section .seg button, main > section button.btn');
    if (!first) return;
    var panel = first.closest('main > section') || first;
    if (panel.getBoundingClientRect().top + scrollY < innerHeight * 1.5) return;
    var link = document.createElement('button');
    link.type = 'button'; link.className = 'toModel';
    link.textContent = (WORDS[lang] || WORDS.ru) + ' ↓';
    link.addEventListener('click', function () { panel.scrollIntoView({behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start'}); });
    header.appendChild(link);
  }

  /* F4 of the mobile audit: a wide plot (viewBox WIDE units and more, at least twice as wide as high) shown on a
     phone at less than SHRINK of its size keeps the width of SHRINK of it and is moved sideways in its own frame —
     its labels were 5 px high. The plot itself, its script and its events are not touched. */
  var WIDE = 700, SHRINK = 0.6;
  function widen() {
    var list = document.querySelectorAll('main svg[viewBox]');
    for (var i = 0; i < list.length; i++) {
      var svg = list[i], box = svg.viewBox.baseVal;
      if (!box || box.width < WIDE || box.width < 2 * box.height || svg.closest('.siteWide, .tablewrap')) continue;
      var shown = svg.getBoundingClientRect().width;
      if (!narrow() || !shown || shown >= box.width * SHRINK) continue;
      var frame = document.createElement('div');
      frame.className = 'siteWide';
      svg.parentNode.insertBefore(frame, svg);
      frame.appendChild(svg);
      svg.style.minWidth = Math.round(box.width * SHRINK) + 'px';
      frame.addEventListener('scroll', edges, {passive: true});
      mark(svg);
    }
    edges();
  }
  function edges() {
    var list = document.querySelectorAll('.siteWide');
    for (var i = 0; i < list.length; i++) list[i].classList.toggle('more', list[i].scrollWidth - list[i].clientWidth - list[i].scrollLeft > 4);
  }

  /* F5: the wavelengths under the lines of a spectrum (.specw .lb, the atom of hydrogen) that would run into one
     another stand on a second and a third row. */
  function stagger() {
    var bands = document.querySelectorAll('.specw');
    for (var i = 0; i < bands.length; i++) {
      var labels = Array.prototype.slice.call(bands[i].querySelectorAll('.lb'));
      labels.forEach(function (l) { l.style.marginTop = ''; });
      labels.sort(function (a, b) { return a.getBoundingClientRect().left - b.getBoundingClientRect().left; });
      var ends = [], rows = 0;
      labels.forEach(function (l) {
        var r = l.getBoundingClientRect(), row = 0;
        while (ends[row] !== undefined && r.left < ends[row] + 4) row++;
        ends[row] = r.right; rows = Math.max(rows, row);
        if (row) l.style.marginTop = (row * 1.25) + 'em';
      });
      bands[i].style.marginBottom = rows ? (rows * 1.25) + 'em' : '';
    }
  }
  var later = false;
  function soon() { if (!later) { later = true; setTimeout(function () { later = false; widen(); stagger(); }, 120); } }
  new MutationObserver(function (records) {
    for (var i = 0; i < records.length; i++) if (records[i].addedNodes.length) { soon(); return; }
  }).observe(document.documentElement, {childList: true, subtree: true});
  addEventListener('resize', soon);

  /* «Сообщить о проблеме» at the end of every topic a link that opens a draft of a letter
     in the mail program of the visitor — the name of the topic and its address are filled in, the rest is for the
     visitor to write; nothing is sent by the page, and nothing about the visitor or the model is put in. */
  var MAIL = ['contact', 'azimuth-chem.com'].join(String.fromCharCode(64));  // not written whole: robots look for «@»
  var REPORT = {
    ru: {link: 'Сообщить о проблеме или непонятном месте', note: 'Откроется черновик письма автору — отправляете вы сами.',
         subject: 'Атлас: ', body: 'Страница: {url}\n\nЧто я делал(а): \nЧто ожидал(а) увидеть: \nЧто произошло (или что непонятно): \nУстройство и браузер: \n'},
    en: {link: 'Report a problem or an unclear place', note: 'A draft of a letter to the author opens — you send it yourself.',
         subject: 'Atlas: ', body: 'Page: {url}\n\nWhat I did: \nWhat I expected to see: \nWhat happened (or what is unclear): \nDevice and browser: \n'},
    zh: {link: '报告问题或不清楚之处', note: '将打开一封写给作者的邮件草稿——由您自己发送。',
         subject: '图谱：', body: '页面：{url}\n\n我做了什么：\n我期望看到什么：\n发生了什么（或哪里不清楚）：\n设备和浏览器：\n'}
  };
  function report() {
    var main = document.querySelector('main');
    if (!main || main.querySelector('.siteReport')) return;
    var words = REPORT[lang] || REPORT.ru, h1 = document.querySelector('main h1, h1');
    var title = h1 ? h1.textContent.replace(/\s+/g, ' ').trim() : document.title;
    var address = location.href;
    try { if (window.top !== window && window.top.location.origin === location.origin) address = window.top.location.href; } catch (e) {}
    var box = document.createElement('p'), a = document.createElement('a'), note = document.createElement('span');
    box.className = 'siteReport';
    a.textContent = words.link;
    a.href = 'mailto:' + MAIL + '?subject=' + encodeURIComponent(words.subject + title) + '&body=' + encodeURIComponent(words.body.replace('{url}', address));
    a.addEventListener('click', function () {  // the address of the moment of the click: the topic may have changed its #
      var now = location.href;
      try { if (window.top !== window && window.top.location.origin === location.origin) now = window.top.location.href; } catch (e) {}
      a.href = 'mailto:' + MAIL + '?subject=' + encodeURIComponent(words.subject + title) + '&body=' + encodeURIComponent(words.body.replace('{url}', now));
    });
    note.textContent = ' ' + words.note;
    box.appendChild(a); box.appendChild(note);
    main.appendChild(box);
  }

  /* the design review §6 «на широком экране параметры модели рядом с графиком, чтобы двигать
     ползунок и сразу видеть результат». A part of a topic whose controls (sliders, buttons, choices) stand above its
     result (.work or .two: the plots, the table) gets them side by side on a wide screen: the controls on the left,
     the result and what follows it on the right. The two groups are wrapped (.siteCtl, .siteRes) as they stand, in
     their order, so a fold and its button stay neighbours; the wrappers are display:contents — no box at all — but on
     a wide screen (atlas-page.css), so a phone sees the page as it was. Left as they are: a part whose controls are a
     line or two (nothing to gain), or have a plot or a table among them. */
  var SIDE_MIN = 90;  // px of controls at least
  function side() {
    var parts = document.querySelectorAll('main section.panel');
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i];
      if (part.classList.contains('siteSide')) continue;
      var kids = Array.prototype.filter.call(part.children, function (e) { return e.tagName !== 'SCRIPT' && e.tagName !== 'STYLE'; });
      var w = -1;
      for (var j = 0; j < kids.length; j++) if (kids[j].matches('.work, .two')) { w = j; break; }
      if (w < 1) continue;
      var head = /^H[2-4]$/.test(kids[0].tagName) ? 1 : 0, controls = kids.slice(head, w);
      if (!controls.length) continue;
      var active = controls.filter(function (e) { return e.matches('input,select,button:not(.foldB)') || e.querySelector('input,select,button:not(.foldB)'); });
      var tall = active.reduce(function (h, e) { return h + e.getBoundingClientRect().height; }, 0);
      var busy = controls.some(function (e) { return e.querySelector('table,canvas,.work,.two') || Array.prototype.some.call(e.querySelectorAll('svg'), function (g) { return !g.closest('button'); }); });
      if (tall < SIDE_MIN || busy) continue;
      var ctl = document.createElement('div'), res = document.createElement('div');
      ctl.className = 'siteCtl'; res.className = 'siteRes';
      part.insertBefore(ctl, controls[0]);
      controls.forEach(function (e) { ctl.appendChild(e); });
      part.insertBefore(res, kids[w]);
      kids.slice(w).forEach(function (e) { res.appendChild(e); });
      part.classList.add('siteSide');
    }
  }
  /* a drawing
     turned with the mouse is not a text to select: a selection begun on a drawing is not begun (Safari began it,
     the CSS user-select alone did not stop it there). */
  document.addEventListener('selectstart', function (e) {
    var t = e.target && e.target.nodeType === 1 ? e.target : e.target && e.target.parentElement;
    if (t && t.closest && t.closest('svg,canvas')) e.preventDefault();
  });
  /* the turning compass of the program before every line
     of a topic that says it is calculating — «Считаю волновую функцию…», «Строю карту…», «Computing…», «正在计算…» —
     a button or a line of text alone (not a text drawn on a canvas); it goes with the words when they are replaced.
     The compass and its style come from tools/build_atlas_site.py (COMPASS_SVG, COMPASS_PAGE_CSS). */
  var COMPASS = '__COMPASS__';
  var WAITING = /^(Считаю|Считается|Строю|Вычисляю|Интегрирую|Загружаю|Calculating|Computing|Building|Drawing|Integrating|Loading|正在)[\s\S]*…\s*$/;
  function waiting() {
    if (!document.getElementById('qcCompassCss')) {
      var st = document.createElement('style'); st.id = 'qcCompassCss';
      st.textContent = __COMPASS_CSS__ + '.qcCompass.qcInline{display:inline-block;width:1.15em;height:1.15em;vertical-align:-.22em;margin-right:.4em}';
      document.head.appendChild(st);
    }
    var all = document.body ? document.body.querySelectorAll('span,p,div,button,td,b,em,small,li,label') : [];
    for (var i = 0; i < all.length; i++) {
      var el = all[i], own = el.querySelector(':scope > .qcInline');
      var words = 0;
      for (var k = 0; k < el.children.length; k++) if (!el.children[k].classList.contains('qcInline')) words++;
      var says = !words && WAITING.test(el.textContent.trim());
      if (says && !own) el.insertAdjacentHTML('afterbegin', COMPASS.replace('class="qcCompass"', 'class="qcCompass qcInline"'));
      else if (!says && own) own.remove();
    }
  }
  var looking = false;
  function look() { if (!looking) { looking = true; requestAnimationFrame(function () { looking = false; waiting(); }); } }
  new MutationObserver(look).observe(document.documentElement, {childList: true, subtree: true, characterData: true});

  function start() { tables(); all(); toModel(); report(); side(); waiting(); setTimeout(function () { shade(); all(); side(); }, 1200); }
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', start); else start();
  addEventListener('load', function () { shade(); all(); toModel(); side(); });
})();

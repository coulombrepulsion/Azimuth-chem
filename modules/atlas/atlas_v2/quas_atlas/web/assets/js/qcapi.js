/* Azimuth Atlas v2: client of the local Python calculation server.

   QC.api(name, params)  -> Promise of the endpoint result (JSON).
                            Identical requests are answered from a small cache;
                            every caller gets its own copy (results may be modified).
   QC.live(name)         -> function(params) returning a Promise that resolves
                            only for the newest call; older calls reject with
                            QC.STALE (ignored globally), so a dragged slider
                            never paints an outdated result over a newer one.
   QC.ready              -> Promise resolved once /api/health answered.
   QC.pending()          -> number of requests in flight.
   QC.idle()             -> Promise resolved when nothing is in flight.

   When the server is not running (page opened as a file, or the console
   window was closed) a banner explains how to start it, in the page language. */
(function () {
  'use strict';
  const QC = window.QC = window.QC || {};
  const STALE = QC.STALE = {stale: true};
  const cache = new Map(), MAXC = 400;
  const lang = (document.documentElement.lang || 'ru').slice(0, 2);
  const MSG = {
    ru: {t: 'Расчёты не запущены.', d: 'Числа на этой странице считает программа на Python. Запустите атлас: дважды щёлкните <b>run_atlas.bat</b> (Windows) или выполните <code>./run_atlas.sh</code> (Linux, macOS) в папке проекта и откройте страницу по адресу, который он покажет (обычно <code>http://127.0.0.1:8765</code>). Окно программы держите открытым.', e: 'Ошибка расчёта: '},
    en: {t: 'Calculations are not running.', d: 'The numbers on this page are computed by a Python program. Start the Atlas: double-click <b>run_atlas.bat</b> (Windows) or run <code>./run_atlas.sh</code> (Linux, macOS) in the project folder, then open the address it prints (usually <code>http://127.0.0.1:8765</code>). Keep its window open.', e: 'Calculation error: '},
    zh: {t: '计算程序未运行。', d: '本页的数值由 Python 程序计算。请启动图谱：在项目文件夹中双击 <b>run_atlas.bat</b>（Windows）或运行 <code>./run_atlas.sh</code>（Linux、macOS），然后打开它显示的地址（通常为 <code>http://127.0.0.1:8765</code>）。请保持程序窗口打开。', e: '计算错误：'}
  }[lang] || null;
  /* inside Azimuth the server is started by the program — no .bat to run; the page says what
     to do there, offers to try again, and tells when the connection is back. Long calculations show a small note with
     the time; a request with no answer for TIMEOUT s ends with a message instead of an empty plot. */
  const EMB = (() => { try { return window.parent !== window || /QtWebEngine/.test(navigator.userAgent); } catch (e) { return true; } })();
  const W = {
    ru: {off: 'Нет связи с расчётами Атласа.', offD: 'Сервер, который считает числа на этой странице, не отвечает. Нажмите «Повторить»; если не поможет — закройте и снова откройте Азимут.',
      retry: 'Повторить', back: 'Связь восстановлена.', reload: 'Обновить страницу', busy: 'Считаю…', sec: 'с',
      slow: 'Расчёт не ответил за ' , slowD: ' с. Попробуйте ещё раз или выберите вариант попроще.', plot: 'Нет связи с расчётом', checking: 'Проверяю…'},
    en: {off: 'No connection to the Atlas calculations.', offD: 'The server that computes the numbers on this page does not answer. Press “Try again”; if that does not help, close and reopen Azimuth.',
      retry: 'Try again', back: 'The connection is back.', reload: 'Reload the page', busy: 'Calculating…', sec: 's',
      slow: 'The calculation gave no answer in ', slowD: ' s. Try again or choose a simpler case.', plot: 'No connection to the calculation', checking: 'Checking…'},
    zh: {off: '与图谱计算程序的连接中断。', offD: '计算本页数值的服务器没有响应。请点击“重试”；如果无效，请关闭并重新打开 Azimuth。',
      retry: '重试', back: '连接已恢复。', reload: '刷新页面', busy: '正在计算…', sec: '秒',
      slow: '计算在 ', slowD: ' 秒内没有响应。请重试或选择更简单的情况。', plot: '与计算程序的连接中断', checking: '正在检查…'}
  }[lang] || null;
  const TIMEOUT = 90;  // s: the longest calculation of a page takes about 15 s (AIM, 6-31G**)
  /* the server's checks of the parameters come in English («al: value out of range (20..160)»); say them in the
     language of the page */
  const RANGE = {ru: (p, r) => 'значение «' + p + '» вне допустимого диапазона' + (r ? ' (' + r.replace('..', '…') + ')' : '') + '.',
    en: (p, r) => 'the value of “' + p + '” is out of range' + (r ? ' (' + r.replace('..', '…') + ')' : '') + '.',
    zh: (p, r) => '“' + p + '” 的值超出允许范围' + (r ? '（' + r.replace('..', '…') + '）' : '') + '。'}[lang];
  const say = m => { const x = /^(\w+): value out of range \((.*)\)$/.exec(m); if (!x || !RANGE) return m;
    return RANGE(x[1], /^see endpoint/.test(x[2]) ? '' : x[2]); };
  const M = MSG || {t: 'Calculations are not running.', d: 'Start the Atlas with run_atlas.bat or ./run_atlas.sh.', e: 'Calculation error: '};

  const css = '.qcBanner{position:fixed;left:12px;right:12px;top:12px;z-index:1000;background:#fff4e5;color:#5a3200;border:1px solid #f0b46a;border-radius:10px;padding:12px 16px;font:15px/1.45 var(--f-body,system-ui,sans-serif);box-shadow:0 6px 24px rgba(0,0,0,.18)}' +
    '.qcBanner b{font-weight:700}.qcBanner code{font-family:var(--f-mono,monospace);font-size:.92em;background:rgba(0,0,0,.06);padding:0 .25em;border-radius:3px}' +
    '.qcBanner .x{float:right;border:0;background:none;font-size:20px;line-height:1;cursor:pointer;color:inherit;margin:-4px -6px 0 8px}' +
    '.qcErr{background:#fdecea;color:#611a15;border-color:#f5a39b}' +
    'html.qc-busy body{cursor:progress}' +
    '.qcBanner .qcAct{margin-top:8px;display:flex;gap:8px}.qcBanner .qcAct button{font:inherit;font-size:14px;padding:5px 12px;border-radius:7px;border:1px solid currentColor;background:transparent;color:inherit;cursor:pointer}' +
    '.qcBanner.qcOk{background:#e5f2ea;color:#1d4d31;border-color:#9fd0b2}' +
    '.qcBusy{position:fixed;left:50%;bottom:16px;transform:translate(-50%,8px);z-index:900;display:flex;align-items:center;gap:8px;padding:6px 14px 6px 10px;border-radius:999px;' +
    'background:var(--panel,#fff);color:var(--ink,#1b2230);border:1px solid var(--line,#d8dce3);box-shadow:0 6px 18px rgba(0,0,0,.14);font:13.5px/1.2 var(--f-body,system-ui,sans-serif);opacity:0;pointer-events:none;transition:opacity .2s,transform .2s}' +
    '.qcBusy.on{opacity:1;transform:translate(-50%,0)}.qcBusy i{width:14px;height:14px;border-radius:50%;border:2px solid var(--line,#d8dce3);border-top-color:var(--accent,#2a62b8);animation:qcSpin .8s linear infinite}' +
    '@keyframes qcSpin{to{transform:rotate(360deg)}}@media (prefers-reduced-motion:reduce){.qcBusy i{animation:none}}';
  function addCss() { const s = document.createElement('style'); s.textContent = css; document.head.appendChild(s); }
  let bannerShown = false;
  function banner(html, err) {
    if (bannerShown && !err) return;
    const go = () => {
      if (!document.getElementById('qcCss')) { addCss(); document.head.lastChild.id = 'qcCss'; }
      const old = document.querySelector('.qcBanner' + (err ? '.qcErr' : ':not(.qcErr)')); if (old) old.remove();
      const d = document.createElement('div'); d.className = 'qcBanner' + (err ? ' qcErr' : ''); d.setAttribute('role', 'alert');
      d.innerHTML = '<button class="x" type="button" aria-label="close">×</button>' + html;
      d.querySelector('.x').onclick = () => d.remove();
      document.body.appendChild(d);
    };
    if (!err) bannerShown = true;
    if (document.body) go(); else addEventListener('DOMContentLoaded', go);
  }
  let watching = null;
  function watch() {  // after a lost connection: /api/health every 3 s; when it answers, say so and offer to reload
    if (watching || !base) return;
    watching = setInterval(() => {
      fetch(base + 'health', {cache: 'no-store'}).then(r => r.ok ? r.json() : null).then(j => {
        if (!j) return;
        clearInterval(watching); watching = null; bannerShown = false;
        const old = document.querySelector('.qcBanner:not(.qcErr)'); if (old) old.remove();
        if (!W) return;
        banner('<b>' + W.back + '</b><div class="qcAct"><button type="button" data-qc="reload">' + W.reload + '</button></div>', false);
        const b = document.querySelector('.qcBanner:not(.qcErr)'); if (b) b.classList.add('qcOk');
      }).catch(() => {});
    }, 3000);
  }
  QC.offline = () => {
    if (EMB && W && base) {
      banner('<b>' + W.off + '</b> ' + W.offD + '<div class="qcAct"><button type="button" data-qc="retry">' + W.retry + '</button></div>', false);
      watch();
    } else banner('<b>' + M.t + '</b> ' + M.d, false);
    emptyPlots();
  };
  document.addEventListener('click', e => {
    const b = e.target.closest && e.target.closest('.qcBanner [data-qc]');
    if (!b) return;
    if (b.dataset.qc === 'reload') location.reload();
    else if (b.dataset.qc === 'retry') {
      b.textContent = W ? W.checking : '…';
      fetch(base + 'health', {cache: 'no-store'}).then(r => { if (r.ok) location.reload(); else throw 0; })
        .catch(() => { b.textContent = W ? W.retry : 'Retry'; });
    }
  });
  function emptyPlots() {  // the plots left empty say why (they stood blank)
    const go = () => {
      if (!W) return;
      document.querySelectorAll('main svg').forEach(svg => {
        if (svg.querySelector('path,line,circle,rect,polyline,polygon,text,image,ellipse')) return;
        const r = svg.getBoundingClientRect(); if (r.width < 80 || r.height < 60) return;
        const vb = svg.viewBox && svg.viewBox.baseVal, w = vb && vb.width ? vb.width : r.width, h = vb && vb.height ? vb.height : r.height;
        const t = document.createElementNS('http://www.w3.org/2000/svg', 'text');
        t.setAttribute('x', (vb ? vb.x : 0) + w / 2); t.setAttribute('y', (vb ? vb.y : 0) + h / 2);
        t.setAttribute('text-anchor', 'middle'); t.setAttribute('font-size', 14); t.setAttribute('fill', 'var(--muted, #5b6474)');
        t.setAttribute('data-no-axis', ''); t.textContent = W.plot; svg.appendChild(t);
      });
    };
    if (document.readyState === 'loading') addEventListener('DOMContentLoaded', () => setTimeout(go, 300)); else setTimeout(go, 300);
  }

  let pending = 0, busyT = null, note = null, noteT = null, tick = null, since = 0;
  function busy(d) {
    pending += d;
    if (pending > 0 && !busyT) {
      busyT = setTimeout(() => document.documentElement.classList.add('qc-busy'), 150);
      since = Date.now();
      noteT = setTimeout(showNote, 600);  // a calculation longer than 0,6 s gets a note: a short one stays silent
    }
    if (pending === 0) {
      clearTimeout(busyT); busyT = null; document.documentElement.classList.remove('qc-busy');
      clearTimeout(noteT); noteT = null; clearInterval(tick); tick = null; if (note) note.classList.remove('on');
    }
  }
  function showNote() {
    if (!W || !document.body) return;
    if (!document.getElementById('qcCss')) { addCss(); document.head.lastChild.id = 'qcCss'; }
    if (!note) { note = document.createElement('div'); note.className = 'qcBusy'; note.setAttribute('role', 'status'); note.innerHTML = '<i></i><span></span>'; document.body.appendChild(note); }
    const text = () => { const s = Math.round((Date.now() - since) / 1000); note.lastChild.textContent = W.busy + (s >= 2 ? ' ' + s + ' ' + W.sec : ''); };
    text(); note.classList.add('on'); tick = setInterval(text, 1000);
  }

  const base = location.protocol === 'file:' ? null : '/api/';
  QC.api = function (name, params) {
    const key = name + '|' + JSON.stringify(params || {});
    const copy = v => (v && typeof v === 'object' ? structuredClone(v) : v);
    if (cache.has(key)) { const v = cache.get(key); cache.delete(key); cache.set(key, v); return v.then(copy); }
    if (!base) { QC.offline(); return Promise.reject(new Error('no server')); }
    busy(1);
    const ctl = typeof AbortController === 'function' ? new AbortController() : null;
    const limit = ctl ? setTimeout(() => ctl.abort(), TIMEOUT * 1000) : null;
    const pr = fetch(base + name, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(params || {}), signal: ctl ? ctl.signal : undefined})
      .then(r => r.json().then(j => {
        if (!r.ok) { const e = new Error(j && j.error || ('HTTP ' + r.status)); e.status = r.status; throw e; }
        return j;
      }), e => {
        if (e && e.name === 'AbortError') {  // no answer in TIMEOUT s — said, not left as an empty plot
          const x = new Error((W ? W.slow : 'No answer in ') + TIMEOUT + (W ? W.slowD : ' s')); x.status = 504; throw x;
        }
        QC.offline(); throw e;
      })
      .finally(() => { clearTimeout(limit); busy(-1); });
    pr.catch(e => { cache.delete(key); if (e.status) banner('<b>' + M.e + '</b>' + say(String(e.message)).replace(/[&<>]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;'}[c])), true); });
    cache.set(key, pr);
    if (cache.size > MAXC) cache.delete(cache.keys().next().value);
    return pr.then(copy);
  };
  QC.pending = () => pending;  /* number of requests in flight (tests wait for 0) */
  /* resolves once no request is in flight (checked on macrotask boundaries, so the
     drawing done in the responses' continuations has happened); the shared page
     helpers (folding of long hints, glossary) start then, i.e. on the drawn page */
  QC.idle = () => new Promise(res => { const chk = () => (pending === 0 ? res() : setTimeout(chk, 30)); setTimeout(chk, 0); });
  QC.live = function (name) {
    let seq = 0;
    return function (params) {
      const my = ++seq;
      return QC.api(name, params).then(v => { if (my !== seq) throw STALE; return v; });
    };
  };
  addEventListener('unhandledrejection', e => { if (e.reason === STALE || (e.reason && e.reason.message === 'no server')) e.preventDefault(); });
  QC.ready = base ? fetch(base + 'health').then(r => r.json()).catch(() => { QC.offline(); return null; }) : Promise.resolve(null).then(() => { QC.offline(); return null; });
})();

/* 2.16.0: the animations of a topic run only while the topic is on screen. The Atlas keeps the topics it has opened
   (hidden iframes); the shell tells every one {qcActive: shown?} when the topic changes, and a hidden program window
   hides the document. While inactive, requestAnimationFrame callbacks wait and setInterval ticks are skipped; the
   clock of the page (performance.now and the rAF time) stands still, so an animation goes on from where it stopped
   instead of jumping over the paused time. */
(function () {
  'use strict';
  const raf = window.requestAnimationFrame.bind(window), caf = window.cancelAnimationFrame.bind(window);
  const every = window.setInterval.bind(window), realNow = performance.now.bind(performance);
  let shown = true, paused = 0, since = null, ids = 0;
  const waiting = new Map(), running = new Map();
  const active = () => shown && !document.hidden;
  function fire(id, cb) {
    running.set(id, raf(t => { running.delete(id); if (!active()) { waiting.set(id, cb); return; } cb(t - paused); }));
  }
  function update() {
    if (!active()) { if (since === null) since = realNow(); return; }
    if (since !== null) { paused += realNow() - since; since = null; }
    const list = [...waiting]; waiting.clear(); list.forEach(([id, cb]) => fire(id, cb));
  }
  window.requestAnimationFrame = cb => { const id = ++ids; if (active()) fire(id, cb); else waiting.set(id, cb); return id; };
  window.cancelAnimationFrame = id => { waiting.delete(id); if (running.has(id)) { caf(running.get(id)); running.delete(id); } };
  window.setInterval = (f, ms, ...rest) => every(typeof f === 'function' ? (...a) => { if (active()) f(...a); } : f, ms, ...rest);
  try { performance.now = () => (since === null ? realNow() : since) - paused; } catch (e) { /* read-only: the time jumps */ }
  window.QC = window.QC || {};
  window.QC.active = active;
  addEventListener('message', e => { if (e.data && typeof e.data.qcActive === 'boolean') { shown = e.data.qcActive; update(); } });
  document.addEventListener('visibilitychange', update);
})();

/* 2.16.0: the titles of the axes in every plot of a topic are bold, in the ink colour and 13 px, and the title of
   the horizontal axis stands under the middle of the axis (it stood at its right end). A title is a <text> of an
   <svg> with a unit or a short symbol («R, Å», «x / L», «T, K», «n (…)», «… (логарифмическая шкала)»), not a
   number, that stands at the bottom edge of the picture (≤ 9 units from it), is turned by 90° or stands in the
   top left corner. The axis is the widest horizontal line or frame of the picture; a title moves only when it stood
   at the right end of it. The plots are redrawn often:
   the new <text> are found after every change of the page (a MutationObserver, once per task). */
(function () {
  'use strict';
  const UNIT = /,\s|\s\/\s|шкала|scale|标度|对数|^\S{1,3}(\s\(.*\))?$/i, NUMBER = /^[−\-+]?[\d\s.,·×⁰¹²³⁴⁵⁶⁷⁸⁹⁻]+\s?%?$/;  // «100 %» is a number of the scale too
  const style = document.createElement('style');
  style.textContent = 'svg text.qcAx{font-weight:700;font-size:13px;fill:var(--ink,currentColor)}';
  (document.head || document.documentElement).appendChild(style);
  function box(svg) {
    const vb = svg.viewBox && svg.viewBox.baseVal;
    if (vb && vb.width && vb.height) return [vb.x, vb.y, vb.width, vb.height];
    const w = parseFloat(svg.getAttribute('width')), h = parseFloat(svg.getAttribute('height'));
    return w && h ? [0, 0, w, h] : null;
  }
  /* the frame of a plot — a rect without fill, or one that covers most of the picture (the field of a map:
     «Оптимизация», «Паули» — filled with the colour of the card) */
  function frame(svg, r) {
    const fill = (r.getAttribute('fill') || '').trim();
    if (fill === 'none' || fill === 'transparent') return true;
    const vb = svg.viewBox && svg.viewBox.baseVal, w = +r.getAttribute('width') || 0, h = +r.getAttribute('height') || 0;
    return !!(vb && vb.width && w >= vb.width * 0.5 && h >= vb.height * 0.4);
  }
  function span(svg, width) {
    let best = null;
    const keep = (a, b) => { const lo = Math.min(a, b), hi = Math.max(a, b); if (hi - lo < width - 1 && (!best || hi - lo > best[1] - best[0])) best = [lo, hi]; };
    svg.querySelectorAll('line').forEach(l => { const y1 = +l.getAttribute('y1'), y2 = +l.getAttribute('y2'); if (Math.abs(y1 - y2) < 0.5) keep(+l.getAttribute('x1'), +l.getAttribute('x2')); });
    svg.querySelectorAll('rect').forEach(r => { const x = +r.getAttribute('x') || 0, w = +r.getAttribute('width') || 0; if (frame(svg, r)) keep(x, x + w); });
    return best;
  }
  function axes(svg) {
    const b = box(svg);
    if (!b) return;
    const [x0, y0, width, height] = b;
    let axis;
    svg.querySelectorAll('text.qcAx').forEach(t => {  // a page that moves its title itself (it sets x, y or the
      if (t.dataset.qcSig === undefined || t.dataset.qcSig === sig(t)) return;  // transform again: «Скорость реакции» at 650 K)
      ['qcAx', 'qcUp', 'qcTr', 'qcShift', 'qcSig'].forEach(k => delete t.dataset[k]);  // gets it placed anew
      t.classList.remove('qcAx');
    });
    svg.querySelectorAll('text').forEach(t => {
      if (t.dataset.qcAx || t.closest('[data-no-axis]')) return;
      const s = (t.textContent || '').trim();
      if (!s || NUMBER.test(s)) return;
      const x = parseFloat(t.getAttribute('x')), y = parseFloat(t.getAttribute('y'));
      const turned = /rotate\(\s*-?90/.test(t.getAttribute('transform') || '');
      // the corner is the top left of the picture (a title of the vertical axis need not have a unit: «r²φ²·4π»)
      const corner = !turned && x <= x0 + Math.max(24, width * 0.15) && y <= y0 + 30 && s.length <= 24;
      if (!corner && !UNIT.test(s)) return;
      const bottom = !turned && y >= y0 + height - 9;
      if (!(bottom || turned || corner)) return;
      t.dataset.qcAx = '1';
      t.classList.add('qcAx');
      if (bottom) {  // every title of the horizontal axis under its middle (it was only those at the right end)
        if (axis === undefined) axis = span(svg, width);
        if (axis && x >= axis[0] - 14 && x <= axis[1] + 14) { t.setAttribute('x', ((axis[0] + axis[1]) / 2).toFixed(1)); t.setAttribute('text-anchor', 'middle'); }
      }
      // one turned title per picture — a second text in the corner is a legend
      if (corner && ![...svg.querySelectorAll('text')].some(n => n !== t && /rotate\(\s*-90/.test(n.getAttribute('transform') || ''))) upright(svg, t, x0);
    });
    clear(svg);
    svg.querySelectorAll('text.qcAx').forEach(t => { t.dataset.qcSig = sig(t); });
  }
  const sig = t => ['x', 'y', 'transform'].map(k => t.getAttribute(k) || '').join('|');
  /* a turned title of the vertical axis keeps at least 7 px from the numbers of the scale (it touched them when
     the numbers were long or the letters had descenders): it is moved left, at most 12 px out of the picture */
  const GAP = 7;
  function clear(svg) {
    const ctm = svg.getScreenCTM && svg.getScreenCTM();
    if (!ctm || !ctm.a) return;
    const edge = svg.getBoundingClientRect().left + 1;
    const nums = [...svg.querySelectorAll('text')].filter(n => NUMBER.test((n.textContent || '').trim())).map(n => n.getBoundingClientRect());
    svg.querySelectorAll('text').forEach(t => {
      const tr = t.getAttribute('transform') || '';
      if (!/rotate\(\s*-?90/.test(tr) || t.closest('[data-no-axis]')) return;
      const a = t.getBoundingClientRect();
      if (!a.width || !a.height) return;
      let need = 0;
      nums.forEach(n => { if (n.bottom < a.top || n.top > a.bottom || n.right < a.left) return; if (n.left >= a.left - 1) need = Math.max(need, GAP - (n.left - a.right)); });
      if (need <= 0.5) return;
      const room = a.left - edge;  // no room on the left: the title may stand up to 12 px out of the picture, over the padding
      if (need > room) { need = Math.min(need, Math.max(0, room) + 12); svg.style.overflow = 'visible'; }  // of the card (the viewBox is kept: clicks on maps count in it)
      if (need <= 0.5) return;
      const ours = t.dataset.qcTr !== undefined && tr === `translate(${(-t.dataset.qcShift).toFixed(2)} 0) ${t.dataset.qcTr}`;  // else the page set a new transform
      const prev = ours ? +t.dataset.qcShift : 0, base = ours ? t.dataset.qcTr : tr, d = prev + need / ctm.a;
      t.dataset.qcTr = base;
      t.dataset.qcShift = d.toFixed(2);
      t.setAttribute('transform', `translate(${(-d).toFixed(2)} 0) ${base}`);
    });
  }
  /* the title of the vertical axis, written in the top left corner, is turned by 90° and stands at the middle
     of the axis, left of the numbers of its scale; when there is no room on the left it stays where it was */
  function vspan(svg) {
    let best = null;
    const all = [];  // of the long vertical lines the leftmost is the axis (a marker line inside the plot — «H₂O» in «Кристаллическом поле» — was taken for it)
    const keep = (a, b, x) => { all.push([Math.min(a, b), Math.max(a, b), x]); };
    svg.querySelectorAll('line').forEach(l => { const x1 = +l.getAttribute('x1'), x2 = +l.getAttribute('x2'); if (Math.abs(x1 - x2) < 0.5) keep(+l.getAttribute('y1'), +l.getAttribute('y2'), x1); });
    svg.querySelectorAll('rect').forEach(r => { if (!frame(svg, r)) return; const y = +r.getAttribute('y') || 0, h = +r.getAttribute('height') || 0, x = +r.getAttribute('x') || 0; keep(y, y + h, x); });
    const longest = Math.max(0, ...all.map(v => v[1] - v[0]));
    all.forEach(v => { if (v[1] - v[0] >= longest * 0.8 && (!best || v[2] < best[2])) best = v; });
    if (!best || best[1] - best[0] < 60) {  // no vertical axis line (only grid lines across, «Атомные единицы», 2): the grid gives the span
      let lo = Infinity, hi = -Infinity, x = Infinity;
      svg.querySelectorAll('line').forEach(l => { const y1 = +l.getAttribute('y1'), y2 = +l.getAttribute('y2'), x1 = +l.getAttribute('x1'), x2 = +l.getAttribute('x2');
        if (Math.abs(y1 - y2) < 0.5 && Math.abs(x2 - x1) > 60) { lo = Math.min(lo, y1); hi = Math.max(hi, y1); x = Math.min(x, x1, x2); } });
      if (hi - lo >= 60) best = [lo, hi, x];
    }
    if (!best || best[1] - best[0] < 60) {  // one grid line or none («Скорость реакции» at some T): the numbers of the scale on the left give the span
      const vb = svg.viewBox && svg.viewBox.baseVal, w = vb && vb.width ? vb.width : 0;
      const nums = [...svg.querySelectorAll('text')].filter(n => NUMBER.test((n.textContent || '').trim()) && n.getAttribute('text-anchor') === 'end' && parseFloat(n.getAttribute('x')) <= (vb ? vb.x : 0) + w * 0.2);  // the scale on the left is written against its axis
      const ys = nums.map(n => parseFloat(n.getAttribute('y'))).filter(Number.isFinite);
      if (ys.length >= 2 && Math.max(...ys) - Math.min(...ys) >= 40) best = [Math.min(...ys) - 4, Math.max(...ys), Math.max(...nums.map(n => parseFloat(n.getAttribute('x')) || 0)) + 6];
    }
    return best;
  }
  function upright(svg, t, x0) {
    const v = vspan(svg);
    if (!v || v[1] - v[0] < 40) return;
    if (parseFloat(t.getAttribute('y')) > v[0] + 16) return;
    const fill = (t.getAttribute('fill') || '').toLowerCase();  // a coloured text is a mark on the plot («1 ккал/моль»), not a title
    if (fill && !/^(var\(--(muted|ink)\)|#5b6474|#1b2230|#9aa3b2|#e7eaf0|currentcolor)$/.test(fill)) return;  // a title stands above the plot; a text beside the rows (bar names, legends) is not one
    if (/[↑↓←→]/.test(t.textContent || '')) return;
    if (/\s=\s/.test(t.textContent || '')) return;  // a caption with a value («H₂O · ν₁ = 3657 см⁻¹» over the molecule of «Колебаний»), not the name of an axis — it was turned and put along the arrow of an atom
    if (/^[A-Z][a-z]?[₀-₉]*[⁺⁻⁰-⁹]*$/.test((t.textContent || '').trim())) return;  // a species next to its point («H⁺» in DFT), not a title  // «энергия ↑» of a level diagram already shows its direction
    let left = v[2];
    svg.querySelectorAll('text').forEach(n => {
      if (n === t || !NUMBER.test((n.textContent || '').trim())) return;
      try { const b = n.getBBox(); if (b.x + b.width <= v[2] + 2 && b.y + b.height >= v[0] - 4 && b.y <= v[1] + 4) left = Math.min(left, b.x); } catch (e) { /* not rendered */ }
    });
    let lx = left - 10;  // was 6 — the letters below the line touched the numbers
    if (lx < x0 + 2) return;  // no room at all left of the numbers («Паули», the maps): it stays upright in its corner
    if (lx - 14 < x0) lx = x0 + 14;  // long numbers of the scale (α = 1,738 in «Вариационном методе»): it is turned all the same, at the left edge — clear() moves it further out if it touches them (it stayed upright at the top)
    const ly = (v[0] + v[1]) / 2;
    t.setAttribute('x', lx.toFixed(1));
    t.setAttribute('y', ly.toFixed(1));
    t.setAttribute('text-anchor', 'middle');
    t.setAttribute('transform', `rotate(-90 ${lx.toFixed(1)} ${ly.toFixed(1)})`);
    t.dataset.qcUp = '1';
  }
  let queued = false;
  function run() { queued = false; document.querySelectorAll('svg').forEach(axes); }
  function later() { if (!queued) { queued = true; setTimeout(run, 0); } }
  /* a redrawn plot is fixed before it is painted (a mutation observer runs before the next frame): with the
     timer the titles of the axes flashed in their old places while a slider moved */
  new MutationObserver(list => {
    const svgs = new Set();
    for (const m of list) {
      const t = m.target;
      if (m.type === 'attributes' && t.dataset && t.dataset.qcSig === sig(t)) continue;  // our own change
      const own = t.closest ? t.closest('svg') : null;
      if (own) svgs.add(own);
      else m.addedNodes.forEach(n => { if (n.nodeType !== 1) return; if (n.tagName.toLowerCase() === 'svg') svgs.add(n); else n.querySelectorAll && n.querySelectorAll('svg').forEach(x => svgs.add(x)); });
    }
    svgs.forEach(svg => { if (svg.isConnected) axes(svg); });
  }).observe(document.documentElement, {childList: true, subtree: true, attributes: true, attributeFilter: ['x', 'y', 'transform']});
  later();
  addEventListener('resize', later);  // a page shown again (a hidden frame of the hub) is measured anew
})();
/* smooth change of plotted curves. QC.snap(svg) remembers the paths before a redraw, QC.tween(svg, snap) makes the
   new paths grow out of the old ones (same number of points: every coordinate is interpolated). */
(function () {
  const QC = window.QC = window.QC || {};
  const NUM = /-?\d*\.?\d+(?:e[-+]?\d+)?/gi;
  const keyed = svg => { const c = {}; return [...svg.querySelectorAll('path')].map(p => { const k = (p.getAttribute('stroke') || '') + '|' + (p.getAttribute('stroke-dasharray') || ''); c[k] = (c[k] || 0) + 1; return [k + '#' + c[k], p]; }); };
  QC.snap = svg => { const m = {}; if (svg) keyed(svg).forEach(([k, p]) => m[k] = p.getAttribute('d') || ''); return m; };
  QC.tween = (svg, old, ms) => {
    if (!svg || !old || matchMedia('(prefers-reduced-motion: reduce)').matches) return;
    const id = svg.__tw = (svg.__tw || 0) + 1, T = ms || 260, t0 = performance.now(), jobs = [];
    keyed(svg).forEach(([key, p]) => {
      const a = old[key], b = p.getAttribute('d') || ''; if (!a || a === b) return;
      const na = a.match(NUM) || [], nb = b.match(NUM) || [];
      if (na.length !== nb.length || a.replace(NUM, '#') !== b.replace(NUM, '#')) return;
      const parts = b.split(NUM); jobs.push({p, parts, na: na.map(Number), nb: nb.map(Number)});
    });
    if (!jobs.length) return;
    const step = () => {
      if (svg.__tw !== id) return;
      const t = Math.min(1, (performance.now() - t0) / T), e = 1 - Math.pow(1 - t, 3);
      jobs.forEach(j => { let s = j.parts[0]; for (let k = 0; k < j.nb.length; k++) s += (j.na[k] + (j.nb[k] - j.na[k]) * e).toFixed(2) + j.parts[k + 1]; j.p.setAttribute('d', s); });
      if (t < 1) requestAnimationFrame(step);
    };
    step();
  };
})();

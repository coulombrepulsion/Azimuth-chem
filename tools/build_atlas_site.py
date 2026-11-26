"""The Atlas as a static web site.

In the program the pages of the Atlas ask a local Python server for every number (POST /api/<name>,
quas_atlas/server.py). A site has no such server. Here the same Python package runs in the browser of the reader
(Pyodide — CPython compiled to WebAssembly — with numpy), so the site is only files: any static hosting serves it, and
the calculations are the very same code as in the program.

What is built into --out:
    the pages of quas_atlas/web as they are, each with one more script before qcapi.js:
    assets/js/qcstatic.js answers the requests of the pages to /api/… from a Web Worker instead of the network
                            (fetch is wrapped for those addresses only; qcapi.js itself is not changed). The topics are
                            frames of the index page: they all use the one worker of the top window.
    assets/js/qcworker.js the worker: loads Pyodide and numpy, unpacks assets/py/quas_atlas.zip, imports the
                            endpoints (quas_atlas.pages) and answers {id, name, body} with {id, status, body}.
    assets/py/quas_atlas.zip the package without its server, command line and web pages, plus atlas_site_entry.py —
                            handle(name, body) -> (status, json text), the same answers as the server gives.

Pyodide is served by the site itself (atlas/assets/pyodide-<version>/): the runtime of the version pinned below and the
numpy wheel, kept in site/.pyodide/<version>/ (not in git; fetched once — the core archive from the GitHub release of
Pyodide, checked by its sha256 written here, and numpy from jsDelivr, checked by the sha256 its pyodide-lock.json
names). A foreign CDN is not needed to read the Atlas (it is unreliable in China and was the one thing the site could
not work without); --pyodide URL loads Pyodide from that address instead.

Offline: sw.js at the root of the site (a service worker) keeps what was read — the pages network-first (a new build
is seen at once, the kept copy answers without a network), the runtime, fonts and pictures cache-first — and, asked by
the side panel («Сохранить для работы без сети»), keeps the whole Atlas of one language: site-files.json lists the
files.

    python3 tools/build_atlas_site.py --out ~/atlas-site
    cd ~/atlas-site && python3 -m http.server 8080 # then http://localhost:8080/ in a browser

The first calculation of a visit waits for Pyodide (about 10 MB, kept by the browser afterwards).
"""

import argparse
import io
import json
import re
import shutil
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import site_scales  # noqa: E402 — the scales of the background as SVG

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'modules' / 'atlas' / 'atlas_v2' / 'quas_atlas'
PYODIDE = 'local'  # served by the site itself; an address (ending with /) loads it from there instead
PYODIDE_VERSION = '0.26.4'
PYODIDE_CORE = (f'https://github.com/pyodide/pyodide/releases/download/{PYODIDE_VERSION}/pyodide-core-{PYODIDE_VERSION}.tar.bz2',
                '70dba93432f3653155998cc9001f9c200182343c2f95165a2f9e9e4673fa35e8')  # the archive and its sha256
PYODIDE_WHEELS = f'https://cdn.jsdelivr.net/pyodide/v{PYODIDE_VERSION}/full/'  # numpy; its sha256 is in pyodide-lock.json
RUNTIME = ('pyodide.js', 'pyodide.asm.js', 'pyodide.asm.wasm', 'python_stdlib.zip', 'pyodide-lock.json')
RUNTIME_DIR = ROOT / 'site' / '.pyodide' / PYODIDE_VERSION
LEFT_OUT = ('server.py', 'cli.py', 'sitecheck.py')  # the local server, its command line, the check of the pages

ENTRY = '''"""The answers of the Atlas server without the server (made by tools/build_atlas_site.py)."""
import json

from quas_atlas import __version__, api
from quas_atlas import pages as _pages  # noqa: F401  (registers the endpoints)


def _text(obj):
    return json.dumps(api.to_json(obj), ensure_ascii=False, allow_nan=False)


def handle(name, body):
    """(status, JSON text) for POST /api/<name> with the JSON text body — as quas_atlas.server.Handler.do_POST."""
    try:
        raw = json.loads(body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return 400, _text({"error": "body is not valid JSON"})
    try:
        return 200, _text(api.call(name, raw))
    except api.ApiError as e:
        return e.status, _text({"error": e.message})
    except Exception as e:  # a bug of a model: reported, the page keeps working
        return 500, _text({"error": f"internal error: {type(e).__name__}: {e}"})


def health():
    return _text({"ok": True, "version": __version__, "static": True})


def endpoints():
    return _text({k: v.doc for k, v in sorted(api.REGISTRY.items())})
'''

WORKER = r'''/* Azimuth Atlas as a static site: the Python of the Atlas in a Web Worker (made by tools/build_atlas_site.py). */
'use strict';
const PYODIDE = __PYODIDE__;
let ready = null;
function start() {
  if (ready) return ready;
  ready = (async () => {
    importScripts(PYODIDE + 'pyodide.js');
    // The server may give pyodide.asm.wasm without «Content-Type: application/wasm» (seen on the site, 2026-11-12:
    // no type at all) — the compilation from the stream then refuses it and nothing is calculated on any page.
    // The bytes are the same whatever the header says: compile from the bytes.
    WebAssembly.compileStreaming = async source => WebAssembly.compile(await (await source).arrayBuffer());
    WebAssembly.instantiateStreaming = async (source, imports) => WebAssembly.instantiate(await (await source).arrayBuffer(), imports);
    const py = await loadPyodide({indexURL: PYODIDE});
    await py.loadPackage('numpy');
    const zip = await (await fetch(new URL('../py/quas_atlas.zip', self.location.href))).arrayBuffer();
    py.unpackArchive(zip, 'zip', {extractDir: '/atlas'});
    py.runPython('import sys\nsys.path.insert(0, "/atlas")\nimport atlas_site_entry');
    return py.globals.get('atlas_site_entry');
  })();
  ready.catch(() => { ready = null; });  // a failed start (no network) may be tried again
  return ready;
}
self.onmessage = async (event) => {
  const {id, name, body} = event.data;
  try {
    const entry = await start();
    if (name === 'health') { self.postMessage({id, status: 200, body: entry.health()}); return; }
    if (name === 'endpoints') { self.postMessage({id, status: 200, body: entry.endpoints()}); return; }
    const answer = entry.handle(name, body || '{}');
    const pair = answer.toJs();
    answer.destroy();
    self.postMessage({id, status: pair[0], body: pair[1]});
  } catch (error) {
    self.postMessage({id, status: 503, body: JSON.stringify({error: 'the calculations did not start: ' + (error && error.message || error)})});
  }
};
'''

STATIC = r'''/* Azimuth Atlas as a static site (made by tools/build_atlas_site.py): the requests of the pages to /api/… are
   answered by the Python of the Atlas running in this browser (assets/js/qcworker.js), not by a server. fetch is
   wrapped for those addresses only. The topics are frames of the index page: every frame uses the worker of the top
   window, so Python is loaded once for the whole visit. */
(function () {
  'use strict';
  if (window.QCStatic) return;
  let host = null;
  try { if (window.top !== window && window.top.QCStatic) host = window.top.QCStatic; } catch (e) { host = null; }
  const here = document.currentScript && document.currentScript.src || location.href;
  const canon = body => { try { const o = JSON.parse(body || '{}'), s = {}; Object.keys(o).sort().forEach(k => { s[k] = o[k]; }); return JSON.stringify(s); } catch (e) { return null; } };
  let call, state;
  if (host) {
    call = host.call; state = host.state;
  } else {
    state = {failed: false, started: false, asked: []};  // asked: what went to Python — [name, parameters], for tools/site_initial_requests.js
    let worker = null, seq = 0;
    const waiting = new Map();
    /* The first answer of Python waits for it to load (seconds; once a visit): said on the page while a request
       waits — not while Python is loaded ahead of need (warm, below). */
    let up = false, noting = null;
    const note = document.createElement('div'), lang = (document.documentElement.lang || 'ru').slice(0, 2);
    /* 2026-11-15: with the compass of the program (COMPASS_SVG of tools/build_atlas_site.py) */
    note.innerHTML = '__COMPASS__<span></span>';
    note.lastChild.textContent = {ru: 'Загружаются расчёты… (один раз за визит)', en: 'Loading the calculations… (once a visit)', zh: '正在加载计算模块…（每次访问一次）'}[lang] || 'Loading the calculations…';
    if (!document.getElementById('qcCompassCss')) { const st = document.createElement('style'); st.id = 'qcCompassCss'; st.textContent = __COMPASS_CSS__; document.head.appendChild(st); }
    note.setAttribute('role', 'status');
    note.style.cssText = 'display:flex;align-items:center;gap:8px;--accent:#6ea2f0;--ink:#e7eaf0;--panel:#1b2230;--qcArc:#e6d2ad;--qcTail:#3a4a66;pointer-events:none;position:fixed;left:50%;bottom:' + (innerWidth <= 700 ? 66 : 22) + 'px;white-space:nowrap;max-width:calc(100vw - 24px);overflow:hidden;text-overflow:ellipsis;transform:translateX(-50%);z-index:2147483001;padding:9px 16px;border-radius:999px;background:#1b2230;color:#fff;font:500 13.5px/1.3 "Golos Text",system-ui,sans-serif;box-shadow:0 6px 24px rgba(0,0,0,.25);pointer-events:none';
    /* pointer-events:none — the note lies where a topic keeps the bar of its demonstration: it must not take the clicks */
    const loaded = () => { up = true; clearTimeout(noting); noting = null; note.remove(); };
    const boot = () => {
      if (worker) return worker;
      worker = new Worker(new URL('qcworker.js', here));
      state.started = true; up = false;
      worker.onmessage = e => { loaded(); state.failed = e.data.status === 503; const w = waiting.get(e.data.id); if (w) { waiting.delete(e.data.id); w(e.data); } };
      worker.onerror = e => {
        const text = JSON.stringify({error: 'the calculations did not start: ' + (e && e.message || 'worker error')});
        loaded(); up = false; state.failed = true; waiting.forEach(w => w({status: 503, body: text})); waiting.clear(); worker = null;
      };
      return worker;
    };
    const ask = (name, body) => new Promise(resolve => {
      const id = ++seq; waiting.set(id, resolve); boot().postMessage({id, name, body});
      if (!up && !noting) noting = setTimeout(() => { if (!up && document.body) document.body.appendChild(note); }, 600);
    });
    /* Python ahead of need: a topic opened shows what was counted for it when the site was built, and Python is
       wanted only at the first change — which would then wait for all of it (24 MB the first time). So it is
       started quietly a few seconds after the page: always when the browser already keeps its files (no traffic),
       otherwise on a computer with an ordinary connection only — not on a phone, not with «save data», not on 2G/3G. */
    const warm = async () => {
      if (worker || state.failed) return;
      let kept = false;
      try { kept = !!(await caches.match(new URL('../__RUNTIME__/pyodide.asm.wasm', here).href)); } catch (e) {}
      const c = navigator.connection || {};
      if (kept || (matchMedia('(pointer:fine)').matches && !c.saveData && !/2g|3g/.test(c.effectiveType || ''))) {
        const id = ++seq; waiting.set(id, () => {}); boot().postMessage({id, name: 'health', body: ''});
      }
    };
    addEventListener('load', () => setTimeout(warm, 4000));
    /* The longest calculations of the Atlas (the topic «Атомы в молекулах»: benzene took 45 s here) are counted when
       the site is built, by the same Python: ../answers-index.json names the file of the answer to a request
       «name|{its parameters, keys sorted}». Such a request is answered by the file; any other, and one whose file
       does not come, by the worker as before. */
    const folder = new URL('../answers/', here);
    let index = null;
    const answers = () => index || (index = fetch(new URL('../answers-index.json', here), {cache: 'no-cache'}).then(r => r.ok ? r.json() : {}).catch(() => ({})));
    call = async (name, body) => {
      const key = canon(body), file = key === null ? null : (await answers())[name + '|' + key];
      if (file) {
        try { const r = await fetch(new URL(file, folder)); if (r.ok) return {status: 200, body: await r.text()}; } catch (e) {}
      }
      if (state.asked.length < 2000) state.asked.push([name, key]);
      return ask(name, body);
    };
  }
  window.QCStatic = {call, state};
  /* What a topic asks for when it is opened is counted when the site is built (by the same Python) and lies in one
     file a topic, ../initial/<topic>.json {«name|parameters»: the text of the answer}: a page opened shows its
     first plots without Python being loaded at all — the 26 MB of it come with the first request that is not there
     (a slider moved, another molecule). /api/health is answered here («the page can ask for calculations») until
     Python has failed to start; after that it goes to Python, so «Повторить» of the page really tries again. */
  const HEALTH = __HEALTH__;
  const topic = (/\/(?:ru|en|zh)\/([\w-]+?)(?:\.html)?$/.exec(location.pathname) || [])[1];
  let first = null;
  const initial = () => first || (first = !topic ? Promise.resolve({}) :
    window.fetch(new URL('../initial/' + topic + '.json', here)).then(r => r.ok ? r.json() : {}).catch(() => ({})));
  const answer = async (name, body) => {
    if (name === 'health' && !state.failed) return {status: 200, body: HEALTH};
    const key = canon(body);
    if (key !== null && name !== 'health') { const kept = (await initial())[name + '|' + key]; if (typeof kept === 'string') return {status: 200, body: kept}; }
    return call(name, body);
  };
  /* The faint scales of the program's background (the dial top right, the book bottom left): in the program its
     window gives them to the index page (qcScales); on the site they are given here, in the colour of the theme. */
  if (!host) {
    const SCALES = __SCALES__;
    const url = (svg, colour) => 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg.split('currentColor').join(colour));
    const dark = () => { const t = document.documentElement.getAttribute('data-theme'); return t ? t === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; };
    const put = () => {
      if (typeof window.qcScales !== 'function') return;
      const z = SCALES.size, colour = dark() ? '#6ea2f0' : '#2a62b8';
      if (innerWidth < 700) { window.qcScales(null); return; }  // a phone: no room for them
      window.qcScales({dial: url(SCALES.dial, colour), book: url(SCALES.book, colour), size: z,
                       dx: innerWidth - z, dy: 0, bx: document.getElementById('siteRail') ? 68 : 0, by: innerHeight - z,
                       spin: url(SCALES.spin, colour), spinBox: SCALES.spinBox});
    };
    /* 2026-11-17: at once, not on «load» — «load» waits for the first topic, and the dial turns while it loads */
    put();
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', put, {once: true});
    addEventListener('load', put);
    addEventListener('resize', put);
    new MutationObserver(put).observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
    matchMedia('(prefers-color-scheme: dark)').addEventListener('change', put);
  }
  const real = window.fetch.bind(window);
  const api = url => { try { const u = new URL(url, location.href); const k = u.pathname.indexOf('/api/'); return u.origin === location.origin && k >= 0 ? u.pathname.slice(k + 5) : null; } catch (e) { return null; } };
  window.fetch = function (input, init) {
    const name = api(typeof input === 'string' ? input : (input && input.url) || '');
    if (name === null) return real(input, init);
    const body = init && typeof init.body === 'string' ? init.body : '';
    const signal = init && init.signal;
    return new Promise((resolve, reject) => {
      if (signal) {
        if (signal.aborted) { reject(new DOMException('Aborted', 'AbortError')); return; }
        signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')), {once: true});
      }
      answer(name, body).then(a => resolve(new Response(a.body, {status: a.status, headers: {'Content-Type': 'application/json; charset=utf-8'}})));
    });
  };
})();
'''

API_SCRIPT = re.compile(r'<script\s+src="((?:\.\./)?assets/js/)qcapi\.js"')
FIRST_SCRIPT = re.compile(r'<script\b')


def package_zip(package=PACKAGE):
    """The bytes of the zip: quas_atlas (its Python and data, no web pages, no server) and atlas_site_entry.py.
    The same files give the same bytes — every entry with one fixed time and mode, not the time of the
    build (writestr) or of the file (write), so an unchanged Atlas is not uploaded again and the copies kept offline
    stay valid (site-files.json)."""
    def entry(name):
        info = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        return info

    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(package.rglob('*')):
            relative = path.relative_to(package)
            if (not path.is_file() or relative.parts[0] == 'web' or '__pycache__' in relative.parts
                    or path.suffix == '.pyc' or (len(relative.parts) == 1 and path.name in LEFT_OUT)):
                continue
            archive.writestr(entry((Path('quas_atlas') / relative).as_posix()), path.read_bytes())
        archive.writestr(entry('atlas_site_entry.py'), ENTRY)
    return data.getvalue()


def with_static(html):
    """The page with qcstatic.js: before qcapi.js where the page has it, else (the index page, which only hosts the
    worker for its frames) before its first script. A page with no script is left as it is."""
    found = API_SCRIPT.search(html)
    if found:
        # with it, what the pages need on the site only (site/atlas-page.css, .js); the styles go to the end of the
        # head — qcapi.js stands before the styles of the page, and a sheet put there was overruled by them
        own = f'<script defer src="{found.group(1)}site-page.js"></script>\n'
        html = html[:found.start()] + own + f'<script src="{found.group(1)}qcstatic.js"></script>\n' + html[found.start():]
        if html.count('</head>') != 1:
            raise ValueError('a topic page without one </head>: the styles of the site have no place')
        if html.count(EARLY_TAG) != 1:
            raise ValueError('a topic page without theme-early.js: the dark ground has no place')
        html = fonts_aside(html.replace(EARLY_TAG, EARLY_TAG + TOPIC_EARLY))
        styles = re.sub(r'js/$', 'css/', found.group(1))  # ../assets/js/ → ../assets/css/
        return html.replace('</head>', f'<link rel="stylesheet" href="{styles}site-page.css">\n</head>'), True
    return html, False


LANDING = ROOT / 'site' / 'index.html'  # the home page of the site: the program and the way to the Atlas
LANDING_PICTURE = ROOT / 'assets' / 'quill' / 'quill-home-desk.webp'
# Quill of the parts of the home page (docs/art/QUAIL_ART_SITE.md): the part of the Atlas only — the four cards of the
# parts of the program are without her
SECTION_PICTURES = (ROOT / 'assets' / 'quill' / 'site' / 'quill-site-atlas.webp',)
APP_ICON = ROOT / 'assets' / 'app-icon'  # the icon of the program — the icon of the site too
ATLAS_ICONS = {'d4fffdebdad3.png': 32, '9b516a1bad91.png': 64, 'f8ff4c87ca71.png': 256}  # the icon files of the pages
# atlas/assets/img/ is kept by browsers for good (IMMUTABLE, sw.js), so a picture written under an old name is not
# read again: a new picture is a new name, and the pages are led to these.
ATLAS_ICON_NAME = 'azimuth-icon-{size}.png'
REDIRECTS = """# Cloudflare Pages: the Atlas lived at the root of the site before the home page (2026-11-10): its old pages
# /LANG/PAGE.html go to /atlas/LANG/; 2026-11-14: /en/ and /zh/ themselves are the home page in that language (a
# placeholder is one part of an address - the folder itself is not caught)
/ru/:page /atlas/ru/:page 301
/en/:page /atlas/en/:page 301
/zh/:page /atlas/zh/:page 301
"""

# the home page in every language at an address of its own — a search engine reads one language an address
# (the other two were put in by the script only); the root stays Russian and still follows the visitor's language
HOME_PATHS = {'ru': '', 'en': 'en/', 'zh': 'zh/'}
LOCALES = {'ru': 'ru_RU', 'en': 'en_US', 'zh': 'zh_CN'}
# Safari hides the part of a title it takes for the name of the site («Азимут — квантовая химия» shown as «квантовая
# химия»): the titles part their words with « · », and no page names the site in og:site_name; and still «Азимут ·
# квантовая химия» was «квантовая химия» (the third screenshot: Safari matches «Азимут» with the address
# azimuth-chem.com) — the tab of the home page has the name alone («Азимут»; texts.json title), the preview of a link
# the whole (ogTitle)
TITLE_SEPARATOR = ' · '


def _sha256(path):
    import hashlib

    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def numpy_wheel(folder=RUNTIME_DIR):
    """(file name, sha256) of numpy as pyodide-lock.json of the runtime names it."""
    entry = json.loads((Path(folder) / 'pyodide-lock.json').read_text(encoding='utf-8'))['packages']['numpy']
    return entry['file_name'], entry['sha256']


def runtime_files(folder=RUNTIME_DIR, fetch=True, opener=None):
    """The files of Pyodide the site serves, in folder: RUNTIME and the numpy wheel. Missing ones are fetched when
    fetch (the core archive, checked by PYODIDE_CORE's sha256; numpy, checked by the sha256 of the lock file); a file
    that does not match is not kept. ValueError when they are not there and cannot be fetched. Returns their paths."""
    import tarfile
    import urllib.request

    folder = Path(folder)
    opener = opener or (lambda url: urllib.request.urlopen(url, timeout=120).read())
    if not all((folder / name).is_file() for name in RUNTIME):
        if not fetch:
            raise ValueError(f'No Pyodide runtime in {folder}')
        url, digest = PYODIDE_CORE
        folder.mkdir(parents=True, exist_ok=True)
        archive = folder / 'core.tar.bz2'
        try:
            archive.write_bytes(opener(url))
        except OSError as exc:
            raise ValueError(f'Pyodide could not be fetched ({url}): {exc}') from exc
        if _sha256(archive) != digest:
            archive.unlink()
            raise ValueError(f'{url}: the archive is not the one expected (sha256)')
        with tarfile.open(archive) as tar:
            for name in RUNTIME:
                (folder / name).write_bytes(tar.extractfile(f'pyodide/{name}').read())
        archive.unlink()
    wheel, digest = numpy_wheel(folder)
    if not (folder / wheel).is_file():
        if not fetch:
            raise ValueError(f'No {wheel} in {folder}')
        try:
            data = opener(PYODIDE_WHEELS + wheel)
        except OSError as exc:
            raise ValueError(f'numpy for Pyodide could not be fetched ({PYODIDE_WHEELS + wheel}): {exc}') from exc
        (folder / wheel).write_bytes(data)
    if _sha256(folder / wheel) != digest:
        (folder / wheel).unlink()
        raise ValueError(f'{wheel}: not the file pyodide-lock.json names (sha256)')
    return [folder / name for name in RUNTIME] + [folder / wheel]


RUNTIME_LICENSES = f"""The files of this folder are not a part of Azimuth; they are served unchanged.

Pyodide {PYODIDE_VERSION} (pyodide.js, pyodide.asm.js, pyodide.asm.wasm, pyodide-lock.json) — Mozilla Public License 2.0,
https://github.com/pyodide/pyodide ; it contains CPython (python_stdlib.zip) — Python Software Foundation License.
numpy 1.26.4 (the .whl file) — BSD 3-Clause License, https://numpy.org .
"""

# The calculations counted when the site is built the molecules and bases of that topic whose five stages take 12 s or
# more of ordinary Python with numpy — three times that in a browser (measured 2026-11-11, s: C6F6/STO-3G 66,
# C3H6/6-31G* 30, C6H6/STO-3G 30, F2CO/6-31G* 22, F2CO/6-31G** 22, C3H6/6-31G 20, C2H4/6-31G** 17, C2H4/6-31G* 14; the
# rest are under 12). Every answer is about 3 MB (the grids of the density), so not every combination is kept: all 43
# would be 156 MB.
ANSWERED = (('C6H6', 'STO-3G'), ('C6F6', 'STO-3G'), ('C3H6', '6-31G'), ('C3H6', '6-31G*'), ('F2CO', '6-31G*'),
            ('F2CO', '6-31G**'), ('C2H4', '6-31G*'), ('C2H4', '6-31G**'))
ANSWERS_DIR = ROOT / 'site' / '.answers'  # counted once and kept (not in git); a change of the model counts anew


def request_key(name, params):
    """«name|{parameters}» as qcstatic.js writes it: the keys sorted, no spaces (strings and whole numbers only)."""
    for value in params.values():
        if not isinstance(value, (str, int)) or isinstance(value, bool):
            raise ValueError(f'{name}: a kept answer takes strings and whole numbers only, got {value!r}')
    return name + '|' + json.dumps(params, sort_keys=True, separators=(',', ':'), ensure_ascii=False)


def model_stamp(package=PACKAGE):
    """sha256 of the Python and the data of the models (core/, pages/, api.py): the kept answers belong to it."""
    import hashlib

    stamp = hashlib.sha256()
    for path in sorted(p for folder in ('core', 'pages') for p in (package / folder).rglob('*') if p.is_file()
                       and '__pycache__' not in p.parts and p.suffix != '.pyc'):
        stamp.update(path.relative_to(package).as_posix().encode() + b'\0' + path.read_bytes())
    stamp.update((package / 'api.py').read_bytes())
    return stamp.hexdigest()


def aim_requests(k, b, scf):
    """The requests of the topic for one molecule and basis: its five stages and the profile along every bond — the
    pairs of nuclei as the page asks for them (web/ru/js/aim.js prof(): the bond critical points of the SCF answer,
    each pair once, the heavier nucleus first)."""
    from quas_atlas.core import aim

    requests = [('aim.stage', {'k': k, 'b': b, 'stage': stage}) for stage in aim.STAGES]
    seen = set()
    for point in scf.get('cps') or ():
        atoms = point.get('atoms')
        if point.get('type') != 'b' or not atoms or any(i < 0 for i in atoms):
            continue
        pair = tuple(sorted(atoms))
        if pair in seen:
            continue
        seen.add(pair)
        ia, ib = atoms
        if scf['atoms'][ia]['Z'] < scf['atoms'][ib]['Z']:
            ia, ib = ib, ia
        requests.append(('aim.prof', {'k': k, 'b': b, 'ia': ia, 'ib': ib}))
    return requests


def answers(out_folder, package=PACKAGE, wanted=ANSWERED, kept=ANSWERS_DIR, log=None):
    """The kept answers in out_folder (atlas/assets/answers): one file a request, and next to the folder
    answers-index.json {request_key: file} (outside it: the files never change under their names, the index does).
    An answer is the text the worker would give (status 200), counted here by the package itself and kept in `kept`
    under the sha256 of the model and the request, so the next build takes it from there. Returns the index."""
    import hashlib
    import importlib

    out_folder = Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)
    kept = Path(kept)
    kept.mkdir(parents=True, exist_ok=True)
    stamp = model_stamp(package)
    index = {}
    api = None
    if str(package.parent) not in sys.path:  # aim_requests reads the stages of the package even when all is kept
        sys.path.insert(0, str(package.parent))

    def answer(name, params):
        nonlocal api
        key = request_key(name, params)
        file = hashlib.sha256((stamp + key).encode()).hexdigest()[:24] + '.json'
        if not (kept / file).is_file():
            if api is None:  # the package is imported only when something is to be counted
                api = importlib.import_module('quas_atlas.api')
                importlib.import_module('quas_atlas.pages')
            if log:
                log(key)
            text = json.dumps(api.to_json(api.call(name, dict(params))), ensure_ascii=False, allow_nan=False)
            (kept / (file + '.tmp')).write_text(text, encoding='utf-8')
            (kept / (file + '.tmp')).replace(kept / file)
        shutil.copy2(kept / file, out_folder / file)
        index[key] = file
        return kept / file

    for k, b in wanted:
        scf = json.loads(answer('aim.stage', {'k': k, 'b': b, 'stage': 'scf'}).read_text(encoding='utf-8'))
        for name, params in aim_requests(k, b, scf)[1:]:
            answer(name, params)
    (out_folder.parent / 'answers-index.json').write_text(json.dumps(index, ensure_ascii=False, sort_keys=True),
                                                          encoding='utf-8')
    return index


# No white field before a dark page.
# Seen here on a slow connection: the index page of the Atlas stood in the light theme, with its note «Страница не
# запустилась», until its scripts had come — the theme chosen was applied by the last of them, and the note is
# taken away by it. On the site the theme is set by a script at the very top, and the note waits NOJS_WAIT seconds.
DARK = '#11151c'  # --bg of the dark theme of the Atlas pages and of its index page
NOJS_WAIT = 8
# the program opens the Atlas with ?theme=light|dark (azimuth/site.py) — kept as the switch would keep it, and gone
# from the address; without it the theme kept by the browser, then that of the system.
THEME_EARLY = (
    "(function(){try{var t,m=/[?&]theme=(light|dark)(?:&|$)/.exec(location.search);"
    "if(m){t=m[1];try{localStorage.setItem('qc-theme',t)}catch(e){}"
    "try{var u=new URL(location.href);u.searchParams.delete('theme');history.replaceState(history.state,'',u)}catch(e){}}"
    "else t=localStorage.getItem('qc-theme');"
    "if(t==='light'||t==='dark')document.documentElement.setAttribute('data-theme',t)}catch(e){}})()")
# the compass of the program's sign of waiting (azimuth/controls.py, draw_compass and azimuth_arc) — the ring, the
# needle (blue point, grey tail, the pivot) turning, the golden arc of the azimuth growing from the north behind the
# needle on one turn and shrinking to the north on the next (two turns, with inertia: COMPASS_TURN, COMPASS_PAUSE,
# COMPASS_EASE); where the site waits: a topic of the Atlas not come yet (the middle of its place, SHELL_EARLY),
# «Загружаются расчёты…» (qcstatic.js) and «Считаю…» (qcapi.js) the motion of azimuth/controls.swing — a turn of
# COMPASS_TURN s eased by COMPASS_EASE, a rest of COMPASS_PAUSE s at the north; the arc follows the needle in the same
# eased segments (one timing function a segment of the keyframes)
COMPASS_TURN, COMPASS_PAUSE = 1.3, 0.3  # s — azimuth/controls.py TURN, PAUSE
COMPASS_EASE = (0.6, 0.0, 0.3, 1.0)  # azimuth/controls.py EASE
COMPASS_CYCLE = 2 * (COMPASS_TURN + COMPASS_PAUSE)
def _glyph():
    """azimuth/compass_glyph.py — the lines of the icon of the program (loaded as a file: no package of the program)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location('compass_glyph', ROOT / 'azimuth' / 'compass_glyph.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


GLYPH = _glyph()


def compass_svg(name='small'):
    """The compass as HTML (classes of compass_css), drawn from the lines of the icon of the program (the same
    divisions, needle and arc, without the star; azimuth.compass_glyph: 'small' — glyph-small.svg, below 40 px; 'full' —
    glyph.svg): the dial — the ring, the divisions, the dotted meridian —, the arc of the azimuth as two halves
    (compass_halves) and the needle with its axis. Every moving part is a picture of its own turned as a whole,
    the arc too: the needle and the halves of the arc are turned by one set of keyframes (_compass_keys), so they move
    together."""
    return ('<span class="qcCompass" aria-hidden="true">' + compass_dial(name) + compass_halves(name)
            + compass_needle(name) + '</span>')


_BOX = 'viewBox="-380 -380 760 760"'


def compass_dial(name):
    """The still part: the ring, the divisions, the meridian (the arc is compass_halves)."""
    import math

    shape = GLYPH.VARIANTS[name]
    parts = [f'<circle class="r" r="{GLYPH.RING_RADIUS:g}" stroke-width="{shape["ring"]:g}"/>']
    for degrees, r0, r1, width, opacity in GLYPH.divisions(name):
        a = math.radians(degrees)
        parts.append(f'<path class="d" d="M{math.sin(a) * r0:.1f} {-math.cos(a) * r0:.1f}L{math.sin(a) * r1:.1f} '
                     f'{-math.cos(a) * r1:.1f}" stroke-width="{width:g}" stroke-opacity="{opacity:g}"/>')
    if shape['meridian']:
        length, width, opacity, dash, gap = shape['meridian']
        parts.append(f'<path class="d" d="M0 0V{-length:g}" stroke-width="{width:g}" stroke-opacity="{opacity:g}" '
                     f'stroke-dasharray="{dash:g} {gap:g}"/>')
    return f'<svg class="qcD" {_BOX}>' + ''.join(parts) + '</svg>'


def compass_halves(name):
    """The arc of the azimuth as two half rings, each turned in a window of half the compass (the right one, x > 0,
    and the left one): a half ring over the left half of the dial (from the south through the west to the north), turned
    by R in the right window, shows the arc from the north to R; turned by L in the left one, from the south to 180 + L.
    _compass_keys turns them so that the arc runs from the north to the needle on its first turn and from the needle to
    the north on its second (azimuth.controls.azimuth_arc)."""
    radius, width = GLYPH.VARIANTS[name]['arc']
    half = f'<svg {_BOX}><path class="a" d="M0 {-radius:g}A{radius:g} {radius:g} 0 0 0 0 {radius:g}" stroke-width="{width:g}"/></svg>'
    return f'<span class="qcH qcR">{half}</span><span class="qcH qcL">{half}</span>'


def compass_needle(name):
    point, half, tail = GLYPH.VARIANTS[name]['needle']
    axis, eye = GLYPH.VARIANTS[name]['axis']
    return (f'<svg class="qcN" {_BOX}><path class="p" d="M0 {-point:g}L{half:g} 0H{-half:g}Z"/>'
            f'<path class="t" d="M0 {tail:g}L{half:g} 0H{-half:g}Z"/><circle class="h" r="{axis:g}"/>'
            f'<circle class="e" r="{eye:g}"/></svg>')


COMPASS_SVG = compass_svg('small')  # the small compass of the notes (18 px): glyph-small.svg


def _bezier(x, x1, y1, x2, y2):
    """y of the CSS cubic-bezier(x1, y1, x2, y2) at x (bisection on the curve's parameter)."""
    def at(t, a, b):
        return 3 * a * t * (1 - t) ** 2 + 3 * b * t * t * (1 - t) + t ** 3

    lo, hi = 0.0, 1.0
    for _ in range(60):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if at(mid, x1, x2) < x else (lo, mid)
    return at((lo + hi) / 2, y1, y2)


COMPASS_STEPS = 36  # keyframes a turn: the eased turn sampled, linear between — the same samples for all three parts


def compass_turns(angle):
    """(needle, right half, left half) in degrees for the needle at angle 0–720 (compass_halves): the arc grows from
    the north behind the needle on the first turn and shrinks to the north before it on the second."""
    if angle <= 360:
        return angle, min(angle, 180.0), max(angle, 180.0) - 360.0
    a = angle - 360.0
    return angle, 180.0 + min(a, 180.0), max(a, 180.0) - 180.0


def _compass_keys():
    """qcCmpN (the needle), qcCmpR, qcCmpL (the halves of the arc): one cycle — a turn of COMPASS_TURN s eased by
    COMPASS_EASE, a rest of COMPASS_PAUSE s at the north, the second turn, the rest — sampled at the same moments."""
    turn = 100 * COMPASS_TURN / COMPASS_CYCLE
    keys = {'N': [], 'R': [], 'L': []}
    moments = []
    for start, base in ((0.0, 0.0), (50.0, 360.0)):
        for k in range(COMPASS_STEPS + 1):
            x = k / COMPASS_STEPS
            moments.append((start + turn * x, base + 360.0 * _bezier(x, *COMPASS_EASE)))
    moments.append((100.0, 720.0))
    for at, angle in moments:
        for part, value in zip('NRL', compass_turns(angle)):
            keys[part].append(f'{at:.3f}%{{transform:rotate({value:.2f}deg)}}')
    return ''.join(f'@keyframes qcCmp{part}{{' + ''.join(frames) + '}' for part, frames in keys.items())


COMPASS_KEYS = _compass_keys()


def compass_css(colours=None, layout=True, scope='.qcCompass'):
    """The style of COMPASS_SVG — the colours (the widths are the icon's, in the SVG), the windows of the halves of the
    arc and the motion: colours — the keys of azimuth.compass_glyph.COLOURS, or None for those of the page (--accent,
    --ink, --panel, --qcArc, --qcTail); scope — the selector of the compass (the big one of the place of a topic has
    its own colours, before the styles of the page have come)."""
    c = colours or {'ring': 'var(--accent,#2a62b8)', 'ink': 'var(--ink,#1b2230)', 'arc': 'var(--qcArc,#b8893f)',
                    'point': 'var(--accent,#2a62b8)', 'tail': 'var(--qcTail,#9aa6b8)', 'axis': 'var(--ink,#1b2230)',
                    'eye': 'var(--panel,#fff)'}
    q = scope
    turn = f'{COMPASS_CYCLE:g}s linear infinite'
    return ((f'{q}{{display:inline-block;position:relative;width:18px;height:18px;flex:none}}'
             f'{q} svg{{position:absolute;left:0;top:0;width:100%;height:100%;overflow:visible}}'
             f'{q} .qcH{{position:absolute;top:0;width:50%;height:100%;overflow:hidden}}'
             f'{q} .qcR{{left:50%}}{q} .qcL{{left:0}}'
             f'{q} .qcH svg{{width:200%;transform-origin:50% 50%;will-change:transform}}{q} .qcR svg{{left:-100%}}'
             f'{q} .qcR svg{{animation:qcCmpR {turn}}}{q} .qcL svg{{animation:qcCmpL {turn}}}'
             f'{q} .qcN{{transform-origin:50% 50%;will-change:transform;animation:qcCmpN {turn}}}' if layout else '')
            + f'{q} .r{{fill:none;stroke:{c["ring"]};stroke-opacity:{GLYPH.RING_OPACITY:g}}}'
            f'{q} .d{{fill:none;stroke:{c["ink"]};stroke-linecap:round}}'
            f'{q} .a{{fill:none;stroke:{c["arc"]};stroke-linecap:butt}}'
            f'{q} .p{{fill:{c["point"]}}}{q} .t{{fill:{c["tail"]}}}{q} .h{{fill:{c["axis"]}}}'
            f'{q} .e{{fill:{c["eye"]}}}'
            + ((COMPASS_KEYS + f'@media (prefers-reduced-motion:reduce){{{q} .qcH svg,{q} .qcN{{animation-duration:8s}}}}')
               if layout else ''))


COMPASS_COLOURS = {'light': GLYPH.COLOURS[False], 'dark': GLYPH.COLOURS[True]}
_LIGHT, _DARK = COMPASS_COLOURS['light'], COMPASS_COLOURS['dark']
COMPASS_PAGE_CSS = (f':root{{--qcArc:{_LIGHT["arc"]};--qcTail:{_LIGHT["tail"]}}}'
                    f':root[data-theme="dark"]{{--qcArc:{_DARK["arc"]};--qcTail:{_DARK["tail"]}}}'
                    '@media (prefers-color-scheme: dark){:root:not([data-theme="light"])'
                    f'{{--qcArc:{_DARK["arc"]};--qcTail:{_DARK["tail"]}}}}}' + compass_css())


# the frame of a topic opened
# for the first time stays unseen until its page has come (the index page marks it data-ld on «load») — or FRAME_WAIT
# seconds at most — so the ground of the Atlas is seen instead of the white of a frame not drawn yet
FRAME_WAIT = 1.5
SHELL_EARLY = (
    "<script>" + THEME_EARLY + "</script>\n"
    "<style>#nojs{animation:nojsLate 0s linear " + str(NOJS_WAIT) + "s both}"
    "@keyframes nojsLate{from{visibility:hidden}to{visibility:visible}}"
    "#stage iframe:not([data-ld]){animation:qcFrameLate 0s linear " + str(FRAME_WAIT) + "s both}"
    "@keyframes qcFrameLate{from{visibility:hidden}to{visibility:visible}}"
    # on the site the language and the theme are those of the side panel (rail.js hides the Atlas's own when it has
    # come) — they are not shown at all, not even as empty buttons before the panel
    "#langG,#themeB{display:none!important}"
    "</style>\n")

# every page says at once that it has both themes — a browser that follows a dark system (Safari above
# all) gives the page a dark ground from its first line, before any style or script; the pages without the line were
# shown on white until their styles came
COLOR_SCHEME = '<meta name="color-scheme" content="light dark">'
CHARSET = re.compile(r'<meta charset="utf-8">', re.IGNORECASE)


def color_scheme(out):
    """COLOR_SCHEME right after the charset of every page of the site that has none; the number of pages given it."""
    count = 0
    for page in Path(out).rglob('*.html'):
        text = page.read_text(encoding='utf-8')
        if 'name="color-scheme"' in text:
            continue
        found = CHARSET.search(text[:2000])
        if found is None:
            continue
        page.write_text(text[:found.end()] + COLOR_SCHEME + text[found.end():], encoding='utf-8')
        count += 1
    return count


# the compass in the middle of the place of a topic while it comes (after 0,25 s: a quick one shows none); after the
# room of the side panel (RAIL_EARLY).
# the compass of the notes (COMPASS_SVG of glyph.svg) in the page itself (STAGE_COMPASS_HTML, put into #stage) — its
# needle and its arc turned by the page's clock (the arc was the animation of a picture of its own: its clock started
# when the picture came, before the needle); its own colours of both themes (the styles of the page are not there yet)
STAGE_LIVE = '#stage:has(>iframe:not([data-ld]):not([hidden]))>.qcStage'
STAGE_COMPASS_HTML = compass_svg('full').replace('class="qcCompass"', 'class="qcCompass qcStage"', 1)
STAGE_COMPASS = (
    "<style>"
    + compass_css(COMPASS_COLOURS['light'], scope='.qcStage')
    + ".qcCompass.qcStage{display:none;position:absolute;left:50%;top:42%;width:56px;height:56px;margin:-28px 0 0 -28px;"
    "pointer-events:none;z-index:2}"
    + STAGE_LIVE + "{display:inline-block;animation:qcCmpIn .2s .25s both}"
    # where the dial of the corner turns (index.html, html.qcDialTurning), no
    # compass in the middle — it stays where there is no dial (a phone)
    + "html.qcDialTurning .qcStage{display:none!important}"
    + ":root[data-theme=\"dark\"] " + compass_css(COMPASS_COLOURS['dark'], layout=False, scope='.qcStage').replace('}.qcStage', '}:root[data-theme="dark"] .qcStage')
    + "@media (prefers-color-scheme: dark){:root:not([data-theme=\"light\"]) "
    + compass_css(COMPASS_COLOURS['dark'], layout=False, scope='.qcStage').replace('}.qcStage', '}:root:not([data-theme="light"]) .qcStage') + "}"
    + "@keyframes qcCmpIn{from{opacity:0}to{opacity:1}}</style>\n")


# A topic page takes its colours from style sheets that are still on their way when the page is first shown: until
# they come it is given the dark ground itself (theme-early.js has set the theme by then), and gives it back to the
# sheets when they are there.
TOPIC_EARLY = (
    "<script>(function(){var R=document.documentElement,t=R.getAttribute('data-theme');"
    "if(t==='dark'||(!t&&window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches)){"
    "R.style.backgroundColor='" + DARK + "';R.style.colorScheme='dark';"
    "document.addEventListener('DOMContentLoaded',function(){R.style.backgroundColor='';R.style.colorScheme=''})}"
    # the room under the glass header of the index page (--qcHead) was given to the frame only on its «load» — a slow
    # topic was shown first under the header, then moved down; the page takes it from the index page from its first line
    "try{if(parent!==window){var h=parent.document.documentElement.style.getPropertyValue('--qcHead');"
    "if(h){R.style.setProperty('--qcHead',h);var s=document.createElement('style');s.id='qcHeadEarly';"
    "s.textContent='html{padding-top:var(--qcHead,0px);scroll-padding-top:calc(var(--qcHead,0px) + 8px)}"
    "html .work>.stage{top:calc(10px + var(--qcHead,0px))}html .qcBanner{top:calc(12px + var(--qcHead,0px))}';"
    "document.head.appendChild(s)}}}catch(e){}})()</script>")
EARLY_TAG = '<script src="../assets/js/theme-early.js"></script>'
# The side panel (site/rail.js) is made by a script at the end of the page; until it ran, the page stood without it and
# then moved right by its width. The room of the panel is kept from the first picture — the same padding rail.js gives,
# and an empty strip of its colours where it will stand (on a phone: the row at the bottom); the strip goes when the
# panel has come (body.hasRail). The colours are those of --rail-bg and --rail-edge of rail.js.
RAIL_EARLY = (
    '<style>body{padding-left:68px;box-sizing:border-box}'
    'body:not(.hasRail)::before{content:"";position:fixed;left:0;top:0;bottom:0;width:68px;z-index:50;'
    'box-sizing:border-box;background:linear-gradient(180deg,#f4f6fa,#e6ebf2);border-right:1px solid #cfd7e2}'
    '.qtip.qtipL{left:86px}.drawer{left:68px}'  # the Atlas: Quill's tip and the menu beside the room of the panel
    '@media (prefers-color-scheme: dark){:root:not([data-theme="light"]) body:not(.hasRail)::before{'
    'background:linear-gradient(180deg,#22304a,#172133);border-color:#33435f}}'
    ':root[data-theme="dark"] body:not(.hasRail)::before{background:linear-gradient(180deg,#22304a,#172133);'
    'border-color:#33435f}'
    '@media (max-width:700px){body{padding-left:0;padding-bottom:54px}body:not(.hasRail)::before{top:auto;right:0;'
    'width:auto;height:54px;border-right:0;border-top:1px solid #cfd7e2}.qtip.qtipL{left:12px}.drawer{left:0}'
    # the header of the Atlas on a phone as site/rail.js makes it — from the first picture, not when the panel came
    'header .top{gap:8px}.qbrandH{zoom:.68}.qpart{display:none}.qtip{display:none!important}'
    '.secT{max-width:38vw;overflow:hidden;text-overflow:ellipsis;font-size:14px;padding-right:10px}}'
    '@media print{body{padding:0}body::before{display:none}}</style>\n')
FONTS_LINK = re.compile(r'<link rel="stylesheet" href="((?:\.\./)?assets/fonts/fonts\.css)">')


# the home page and the index page of the Atlas carry the faces of the fonts in the page itself — the browser knows them
# from the first picture and takes the files from its cache at once — and the wordmark of the name is in the page as it
# was built, not put there by the script at its end
FONT_FACE_URL = re.compile(r'url\((?![\'"]?(?:data:|https?:|/))([\'"]?)([^)\'"]+)\1\)')


HOME_FONTS = re.compile(r'<link rel="stylesheet" href="(atlas/assets/fonts/fonts\.css)" media="print" '
                        r'onload="this\.media=\'all\'">\n<noscript><link rel="stylesheet" href="atlas/assets/fonts/fonts\.css">'
                        r'</noscript>')


def font_faces(css, base):
    """The @font-face rules of fonts.css in one line, their files at base (ending with /)."""
    faces = FONT_FACE_URL.sub(lambda m: f'url({base}{m.group(2)})', re.sub(r'/\*.*?\*/', '', css, flags=re.S))
    return re.sub(r'\s*\n\s*', '', faces).strip()


def fonts_inline(html, css, link=FONTS_LINK, prefix=''):
    """The one link to fonts.css of a page (link: FONTS_LINK, or HOME_FONTS of the home page with its copy for a browser
    without scripts) made a <style> with its @font-face rules, the files where the link pointed (prefix before it:
    '../' for the home page of a folder). One link a page, or ValueError."""
    if len(link.findall(html)) != 1:
        raise ValueError('a page without one link to fonts.css')
    found = link.search(html)
    style = '<style>' + font_faces(css, prefix + found.group(1).rsplit('/', 1)[0] + '/') + '</style>'
    html = html[:found.start()] + html[found.end():]
    if '</head>' in html:  # after the theme set at the top (nothing is drawn before it) — the end of the head
        return html.replace('</head>', style + '\n</head>', 1)
    return html[:found.start()] + style + html[found.start():]  # the index page of the Atlas has no </head>


WORD_ITEM = re.compile(r"(ru|en|zh):'((?:[^'\\]|\\.)*)'")


def wordmarks(web):
    """{'ru', 'en', 'zh': the SVG of the name} — the WORD of the index page of the Atlas (wordmark_script)."""
    found = dict(WORD_ITEM.findall(wordmark_script(web)))
    if set(found) != {'ru', 'en', 'zh'} or any('\\' in v for v in found.values()):
        raise ValueError('const WORD of the index page of the Atlas changed: the wordmarks cannot be read')
    return found


def fonts_aside(html):
    """The sheet of the fonts does not hold the first picture of a page back: it is asked for as a sheet «for print»
    and made a sheet for the screen when it has come; the text stands in the font of the system until then (the
    font files themselves were already shown that way, font-display: swap). One link a page, or ValueError."""
    if len(FONTS_LINK.findall(html)) != 1:
        raise ValueError('a page of the Atlas without one link to fonts.css')
    return FONTS_LINK.sub(lambda m: f'<link rel="stylesheet" href="{m.group(1)}" media="print" onload="this.media=\'all\'">'
                                    f'<noscript><link rel="stylesheet" href="{m.group(1)}"></noscript>', html)


INITIAL_REQUESTS = ROOT / 'site' / 'initial-requests.json'  # written by tools/site_initial_requests.js


def initial_answers(out_folder, package=PACKAGE, requests=INITIAL_REQUESTS, kept=ANSWERS_DIR, log=None):
    """What every topic asks for when it is opened, counted here: out_folder/<topic>.json {«name|parameters»: the text
    of the answer} (atlas/assets/initial), read by qcstatic.js before Python is asked. requests — {topic: [[name,
    parameters as the page wrote them], …]}; the parameters are kept as written, so the key is the page's own.
    Counted by the package, the texts kept in `kept` under the sha256 of the model and the request (as answers()).
    A request the package refuses (its parameters are no longer taken) is left out: the browser asks Python as before.
    Returns {topic: number of answers}."""
    import hashlib
    import importlib

    out_folder = Path(out_folder)
    out_folder.mkdir(parents=True, exist_ok=True)
    kept = Path(kept)
    kept.mkdir(parents=True, exist_ok=True)
    stamp = model_stamp(package)
    if str(package.parent) not in sys.path:
        sys.path.insert(0, str(package.parent))
    api = None
    made = {}
    for topic, asked in sorted(json.loads(Path(requests).read_text(encoding='utf-8')).items()):
        if not re.fullmatch(r'[\w-]+', topic):
            raise ValueError(f'{requests}: not a name of a topic: {topic!r}')
        bundle = {}
        for name, params in asked:
            key = name + '|' + params
            file = kept / (hashlib.sha256((stamp + key).encode()).hexdigest()[:24] + '.initial.json')
            if not file.is_file():
                if api is None:
                    api = importlib.import_module('quas_atlas.api')
                    importlib.import_module('quas_atlas.pages')
                if log:
                    log(key if len(key) < 100 else key[:100] + '…')
                try:
                    text = json.dumps(api.to_json(api.call(name, json.loads(params))), ensure_ascii=False, allow_nan=False)
                except api.ApiError:
                    text = ''  # refused: not kept, and not asked again at every build
                file.with_suffix('.tmp').write_text(text, encoding='utf-8')
                file.with_suffix('.tmp').replace(file)
            text = file.read_text(encoding='utf-8')
            if text:
                bundle[key] = text
        if bundle:
            (out_folder / f'{topic}.json').write_text(json.dumps(bundle, ensure_ascii=False), encoding='utf-8')
            made[topic] = len(bundle)
    return made


BUSY_MARK = "note.innerHTML = '<i></i><span></span>'"  # qcapi.js: the note «Считаю…» (the compass in place of <i>)
BUSY_CSS = "'@keyframes qcSpin{to{transform:rotate(360deg)}}@media (prefers-reduced-motion:reduce){.qcBusy i{animation:none}}';"
LIVE_OLD = '''  QC.live = function (name) {
    let seq = 0;
    return function (params) {
      const my = ++seq;
      return QC.api(name, params).then(v => { if (my !== seq) throw STALE; return v; });
    };
  };
'''
# A slider dragged asks for a result at every step; each of them was counted in turn by the one Python of the browser
# (a second and more each), and the last position waited for all the positions passed. On the site one consumer
# (one QC.live) has one request being counted and at most one waiting — the newest: a request overtaken before it was
# sent is not sent at all and ends as QC.STALE, as an overtaken result always did. In the program the answers come
# in milliseconds and qcapi.js is left as it is.
LIVE_NEW = '''  QC.live = function (name) {
    let seq = 0, busy = false, next = null;
    const pump = () => {
      if (busy || !next) return;
      const job = next; next = null; busy = true;
      QC.api(name, job.params).then(
        v => { busy = false; if (job.my === seq) job.resolve(v); else job.reject(STALE); pump(); },
        e => { busy = false; job.reject(e); pump(); });
    };
    return function (params) {
      return new Promise((resolve, reject) => {
        if (next) next.reject(STALE);
        next = {params, resolve, reject, my: ++seq};
        pump();
      });
    };
  };
'''

SEARCH_LOADER = (
    "/*SIDX*/const SIDX={},SIDXP={},SIDXF={};"
    "function sidxLoad(l,done){if(SIDX[l])return;"
    "if(!SIDXP[l])SIDXP[l]=fetch('assets/search-'+l+'.json').then(r=>{if(!r.ok)throw 0;return r.json()})"
    ".then(j=>{SIDX[l]=j;SIDXF[l]=false;return true}).catch(()=>{delete SIDXP[l];SIDXF[l]=true;return false});"
    "SIDXP[l].then(ok=>done&&done(ok,l))}/*SIDX_END*/")
SEARCH_OFF = {'ru': 'Поиск по тексту тем сейчас недоступен: нет сети. Найдены только названия тем.',
              'en': 'The search in the text of the topics is not available now: no network. Only the names of the topics were searched.',
              'zh': '目前无法搜索主题正文：没有网络。只搜索了主题名称。'}


def split_search(shell_text):
    """The index page of the Atlas without its search index, and the index by languages.

    web/index.html carries what the search looks through in all three languages (/*SIDX*/const SIDX={ru, en, zh};
    /*SIDX_END*/) — 0.55 of its 0.69 MB, read by everyone who opens the Atlas, in three languages, searching or not.
    On the site the index of a language is a file (atlas/assets/search-<lang>.json), read when the search is opened or
    typed in — once, also after the language is changed; until it comes, and when it does not come, the names of the
    topics are searched as before, and a line says that the text was not. Returns (text, {lang: list})."""
    start, end = shell_text.index('/*SIDX*/const SIDX='), shell_text.index('/*SIDX_END*/')
    index = json.loads(shell_text[start + len('/*SIDX*/const SIDX='):end].rstrip().rstrip(';'))
    text = shell_text[:start] + SEARCH_LOADER + shell_text[end + len('/*SIDX_END*/'):]
    changes = (
        # typing: the index of the language of the page is asked for; drawn again when it has come
        (" function draw(){const q=I.value.trim();res=find(q);sel=0;",
         " function draw(){const q=I.value.trim();if(q)sidxLoad(lang,(ok,l)=>{if(l===lang&&!P.hidden)draw()});res=find(q);sel=0;"),
        # the search opened: the index starts to come before the first letter
        (" function open(){W.classList.add('open');", " function open(){sidxLoad(lang);W.classList.add('open');"),
        # nothing more to wait for and the index did not come: said under the results
        ("   R.querySelectorAll('a').forEach(a=>a.onclick=()=>pick(+a.dataset.i))}",
         "   if(q&&SIDXF[lang])R.insertAdjacentHTML('beforeend','<div class=\"none\" style=\"font-size:.86em\">'+("
         + json.dumps(SEARCH_OFF, ensure_ascii=False) + ")[lang]+'</div>');"
         "   R.querySelectorAll('a').forEach(a=>a.onclick=()=>pick(+a.dataset.i))}"),
    )
    for old, new in changes:
        if text.count(old) != 1:
            raise ValueError('the search of the Atlas index page changed: «' + old[:50] + '…» is there ' + str(text.count(old)) + ' times')
        text = text.replace(old, new)
    return text, index


# The runtime of Python lies in a folder named by its version: another version is another address, and the copy a
# browser keeps of this one never has to change (it lay in assets/pyodide/, a name that would have outlived its
# content). RUNTIME_FOLDER is under atlas/assets/.
RUNTIME_FOLDER = f'pyodide-{PYODIDE_VERSION}'
# Kept cache-first by sw.js — what never changes under its name: the runtime (its version in the address), the kept
# answers (the hash of the model and the request), the pictures of the topics (a date or a hash in the name) and the
# font files (*.woff2; fonts.css beside them may change and is read from the network). The pictures of the home page
# (img/: og.jpg, the glyphs) may change under their names and are not here.
IMMUTABLE = (f'atlas/assets/{RUNTIME_FOLDER}/', 'atlas/assets/img/', 'atlas/assets/answers/')
IMMUTABLE_PATTERN = r'^atlas/assets/fonts/[^/]+\.woff2$'


# The scripts and styles of the site itself, named the same from build to build: a page asks for them with ?v=<the
# start of their sha256>: a browser keeps a script (the mirror gives it a day, Safari keeps what it is not told
# about), so a new content gets a new address, read at once.
VERSIONED = ('rail.js', 'atlas/assets/js/site-page.js', 'atlas/assets/css/site-page.css')


def versioned(out):
    """Every reference to a file of VERSIONED in the pages of out (…/name" → …/name?v=hash") — the number of the
    references changed."""
    import hashlib

    out = Path(out)
    marks = {}
    for name in VERSIONED:
        if (out / name).is_file():
            marks[Path(name).name] = hashlib.sha256((out / name).read_bytes()).hexdigest()[:10]
    if not marks:
        return 0
    pattern = re.compile(r'((?:src|href)="[^"?]*/?(' + '|'.join(re.escape(n) for n in marks) + r'))"')
    changed = 0
    for page in out.rglob('*.html'):
        text = page.read_text(encoding='utf-8')
        new, count = pattern.subn(lambda m: f'{m.group(1)}?v={marks[m.group(2)]}"', text)
        if count:
            page.write_text(new, encoding='utf-8')
            changed += count
    return changed


def site_files(out):
    """site-files.json: what «Сохранить для работы без сети» keeps — {version, common, ru, en, zh}: the paths of the
    files from the root of the site; a language folder of the Atlas goes to its language, the rest is common. version
    is the sha256 of the names and sizes: a new build is a new version (sw.js drops the copies of the old one)."""
    import hashlib

    out = Path(out)
    lists = {'common': [], 'ru': [], 'en': [], 'zh': []}
    stamp = hashlib.sha256()
    for path in sorted(p for p in out.rglob('*') if p.is_file()):
        name = path.relative_to(out).as_posix()
        if name in ('site-files.json', 'sw.js', '_redirects', '_headers', '.nojekyll', 'sitemap.xml') or name.endswith(('.txt', '.md')):
            continue
        if name.startswith('atlas/assets/answers/'):
            continue  # the kept answers (3 MB each) are read when asked for; without them the worker counts
        parts = name.split('/')
        key = parts[1] if len(parts) > 2 and parts[0] == 'atlas' and parts[1] in ('ru', 'en', 'zh') else 'common'
        lists[key].append(name)
        stamp.update(f'{name}:{path.stat().st_size}:'.encode() + hashlib.sha256(path.read_bytes()).digest())
    return {'version': stamp.hexdigest()[:16], **lists}


SERVICE_WORKER = r'''/* Azimuth site: what was read is kept for reading without a network (made by tools/build_atlas_site.py).
   Pages, scripts and the Python of the Atlas: the network first (a new build is seen at once), the kept copy when the
   network does not answer. The runtime of Python, fonts and pictures never change under one name: the kept copy first.
   {type: 'save', lang} from a page keeps the whole Atlas of that language (site-files.json) and reports
   {type: 'saved', done, total, failed} to it. */
'use strict';
const VERSION = __VERSION__;
const CACHE = 'azimuth-site-' + VERSION;
const IMMUTABLE = __IMMUTABLE__, PATTERN = new RegExp(__PATTERN__);
const fixed = path => IMMUTABLE.some(p => path.startsWith(p)) || PATTERN.test(path);  // never changes under its name
const WAIT = 4000;  // ms the network is waited for when a copy of the page is kept
const SLOW = 60000;
let slowUntil = 0;
const ROOT = new URL('./', self.location.href);
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil((async () => {
  const names = await caches.keys();
  const old = names.filter(n => n.startsWith('azimuth-site-') && n !== CACHE);
  if (old.length) {  // the files that never change move to the new version; the rest are read anew
    const now = await caches.open(CACHE);
    for (const name of old) {
      const was = await caches.open(name);
      for (const request of await was.keys()) {
        const path = new URL(request.url).pathname.slice(ROOT.pathname.length);
        if (fixed(path) && !(await now.match(request))) { const r = await was.match(request); if (r) await now.put(request, r); }
      }
      await caches.delete(name);
    }
  }
  await self.clients.claim();
})()));
const key = url => { const u = new URL(url); u.search = ''; u.hash = ''; return u.href; };  // ?lang=… is one page
/* The copy is written beside the answer, not before it: cache.put ends when the whole body has come, and waiting
   for it held back every first reading of a file (the 10 MB of the runtime most of all). A copy that cannot be
   written (no room) is no reason to fail a reading that succeeded. */
function keep(event, request, response) {
  if (response && response.ok && response.type === 'basic') {
    const copy = response.clone();
    event.waitUntil(caches.open(CACHE).then(cache => cache.put(key(request.url), copy)).catch(() => {}));
  }
  return response;
}
self.addEventListener('fetch', event => {
  const request = event.request, url = new URL(request.url);
  if (request.method !== 'GET' || url.origin !== ROOT.origin || !url.pathname.startsWith(ROOT.pathname)) return;
  const path = url.pathname.slice(ROOT.pathname.length);
  if (path === 'sw.js') return;
  event.respondWith((async () => {
    const cache = await caches.open(CACHE);
    if (fixed(path)) {
      const kept = await cache.match(key(request.url));
      return kept || keep(event, request, await fetch(request));
    }
    /* A page or a script: the network first, so that a new build is seen at once — but when a copy is kept, the
       network is waited for WAIT ms only (a slow connection that does answer made a topic read before wait as long
       as the first time). The answer that comes later still renews the copy. */
    const copy = await cache.match(key(request.url));
    const fresh = fetch(request, {cache: 'no-cache'}).then(response => keep(event, request, response));
    if (copy) {
      /* once the network was found slow or absent, the copies are given at once for a while (SLOW ms): a topic is
         a chain of readings (the page, its scripts, the frame, its scripts), and waiting WAIT at each made it 20 s */
      if (Date.now() < slowUntil) { event.waitUntil(fresh.catch(() => {})); return copy; }
      const late = new Promise(resolve => setTimeout(() => resolve(null), WAIT));
      const first = await Promise.race([fresh.catch(() => null), late]);
      if (first && (first.ok || first.status === 404)) return first;
      slowUntil = Date.now() + SLOW;
      event.waitUntil(fresh.catch(() => {}));
      return copy;
    }
    try {
      return await fresh;
    } catch (error) {
      const kept = await cache.match(key(request.url)) || (request.mode === 'navigate' && await cache.match(key(new URL(path.endsWith('/') || !path ? path + 'index.html' : path, ROOT).href)));
      if (kept) return kept;
      throw error;
    }
  })());
});
self.addEventListener('message', event => {
  const data = event.data || {};
  if (data.type !== 'save') return;
  event.waitUntil((async () => {
    const tell = m => event.source && event.source.postMessage(m);
    try {
      const lists = await (await fetch(new URL('site-files.json', ROOT), {cache: 'no-cache'})).json();
      const names = lists.common.concat(lists[data.lang] || []);
      const cache = await caches.open(CACHE);
      let done = 0, failed = 0, next = 0;
      const one = async () => {
        while (next < names.length) {
          const name = names[next++], url = new URL(name, ROOT).href;
          try {
            if (!(fixed(name) && await cache.match(url))) { const r = await fetch(url, {cache: 'no-cache'}); if (!r.ok) throw new Error(r.status); await cache.put(url, r); }
            if (name.endsWith('/index.html')) { const r = await cache.match(url); await cache.put(url.slice(0, -10), r.clone()); }  // the folder address too
          } catch (error) { failed++; }
          done++;
          if (done % 10 === 0 || done === names.length) tell({type: 'saved', done, total: names.length, failed, lang: data.lang});
        }
      };
      await Promise.all([one(), one(), one(), one()]);
      if (!names.length) tell({type: 'saved', done: 0, total: 0, failed: 0, lang: data.lang});
    } catch (error) { tell({type: 'saved', done: 0, total: 0, failed: 1, lang: data.lang, error: String(error)}); }
  })());
});
'''


# Cloudflare Pages: the types of the files of the runtime of Python said aloud (the site gave them without a type on
# 2026-11-12). The worker no longer depends on it (WORKER); this keeps the answers of the server right as well.
HEADERS = f"""/atlas/assets/{RUNTIME_FOLDER}/*.wasm
  Content-Type: application/wasm
/atlas/assets/{RUNTIME_FOLDER}/*.whl
  Content-Type: application/zip
"""

SITE_URL = 'https://www.azimuth-chem.com/'  # the address of the site: the previews of a link need whole addresses
# the address of the author is not written in the HTML (the robots that gather addresses for spam read it):
# {mail} becomes an empty link that the script of the page fills (site/index.html, ADDRESS)
MAIL = '<a class="mail" href="#author"></a>'


def home_page(template, texts, url=SITE_URL, title='title', lead='lead', path='', lang='ru'):
    """The home page from its template (site/index.html) and its texts (site/texts.json: {ru, en, zh: {key: text}}).

    The texts were put in by the script of the page only: the HTML itself was empty, so a search engine and the preview
    of a link in a messenger (they read the HTML, not the page drawn) saw no text and no picture. Now the Russian text
    stands in the HTML — every element data-t="key" holds texts['ru'][key], the picture its alt — and the head has the
    description and the Open Graph marks (title, description, picture og.jpg by its whole address). The script still
    changes the language from the same texts (/*TEXTS*/), so there is one source.

    Title and lead name its texts, path — the page's place under the address of the site (the page «О программе»,
    program/, was made the same way). Lang: the language
    whose texts stand in the HTML; the head names the pages of the other languages (hreflang)."""
    import html as _html

    ru = texts[lang]

    def fill(match):
        key = match.group(2)
        if key not in ru:
            raise ValueError(f'the home page asks for the text «{key}», site/texts.json has none')
        return match.group(1) + ru[key].replace('{mail}', MAIL) + match.group(3)

    page, count = re.subn(r'(<[a-z0-9]+\b[^>]*\bdata-t="([A-Za-z0-9]+)"[^>]*>)(</)', fill, template)
    if count != template.count('data-t="'):
        raise ValueError('the home page: an element data-t is not empty or is not closed at once')
    page = re.sub(r'alt="" data-alt="([A-Za-z0-9]+)"', lambda m: f'alt="{_html.escape(ru[m.group(1)], quote=True)}" data-alt="{m.group(1)}"', page)
    lead = _html.escape(re.sub(r'<[^>]+>', '', ru[lead]), quote=True)
    tab = _html.escape(ru[title], quote=True)
    title = _html.escape(ru.get('ogTitle', ru[title]), quote=True)  # the preview of a link: the name and what it is
    # the title of the tab in the language of the page (it was the Russian one until the script ran) — the
    # name alone (TITLE_SEPARATOR)
    if len(re.findall(r'<title>[^<]*</title>', page)) != 1:
        raise ValueError('the home page has not one <title>')
    page = re.sub(r'<title>[^<]*</title>', f'<title>{tab}</title>', page)
    head = '\n'.join((
        f'<meta name="description" content="{lead}">',
        f'<link rel="canonical" href="{url}{path}">',
        '<meta property="og:type" content="website">',
        f'<meta property="og:url" content="{url}{path}">',
        # no og:site_name: Safari takes the name of the site from it and hides it in the tab title
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:description" content="{lead}">',
        f'<meta property="og:image" content="{url}img/og.jpg">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        f'<meta property="og:locale" content="{LOCALES[lang]}">',
        *(f'<meta property="og:locale:alternate" content="{LOCALES[other]}">' for other in LOCALES if other != lang),
        '<meta name="twitter:card" content="summary_large_image">',
        *(f'<link rel="alternate" hreflang="{"zh-Hans" if other == "zh" else other}" href="{url}{HOME_PATHS[other]}">'
          for other in HOME_PATHS),
        f'<link rel="alternate" hreflang="x-default" href="{url}">',
    ))
    if lang != 'ru':
        page = page.replace('<html lang="ru">', f'<html lang="{"zh-CN" if lang == "zh" else lang}">', 1)
    for mark in ('<!--HEAD-->', '/*TEXTS*/'):
        if mark not in page:
            raise ValueError(f'the home page has no {mark}')
    return page.replace('<!--HEAD-->', head).replace('/*TEXTS*/', json.dumps(texts, ensure_ascii=False))


def in_folder(page, lang):
    """The home page made for its folder (en/, zh/): the addresses of the site in it one folder up — those of the
    attributes and the strings of its script that begin with its folders — the parts of the page (#program) its own,
    and the side panel told the language of the page (data-lang, site/rail.js). A reference left pointing into the
    root is a ValueError."""
    page = re.sub(r'\b(src|href)="(?!#|https?:|mailto:|data:|/|\.\./|\./")([^"]*)"', r'\1="../\2"', page)
    page = re.sub(r"""(['`])(img/|atlas/|rail\.js)""", r'\1../\2', page)
    if page.count('data-root="./"') != 1:
        raise ValueError('the home page: the side panel (rail.js, data-root) was not found once')
    page = page.replace('data-root="./"', f'data-root="../" data-lang="{lang}"')
    stray = re.findall(r'\b(?:src|href)="((?:img|atlas)/[^"]*)"', page)
    if stray:
        raise ValueError(f'the home page of {lang}: addresses left in the root: {stray[:5]}')
    return page


def sitemap(out, url):
    """sitemap.xml: the home page in its three languages (each naming the others) and the pages of the Atlas."""
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    alternates = ''.join(f'<xhtml:link rel="alternate" hreflang="{"zh-Hans" if lang == "zh" else lang}" href="{url}{path}"/>'
                         for lang, path in HOME_PATHS.items())
    for path in HOME_PATHS.values():
        lines.append(f'<url><loc>{url}{path}</loc>{alternates}</url>')
    for page in sorted((Path(out) / 'atlas').glob('*/*.html')):
        if page.parent.name in HOME_PATHS:
            lines.append(f'<url><loc>{url}atlas/{page.parent.name}/{page.name}</loc></url>')
    lines.append('</urlset>')
    return '\n'.join(lines) + '\n'


ART = re.compile(r'<!--ART ([a-z]+)-->')
ICON = re.compile(r'<!--ICON ([a-z]+)-->')
NAV = re.compile(r'<!--NAV ([a-z]+)-->')
CARD_STRENGTH = 1.6  # the faintness of the pictures on the cards and on the panel of a section
MIRRORED = {'book', 'compass', 'sextant', 'spectrum'}  # drawn for the lower left corner of the window; a card has them
# lower right (the spectrum too — it is cut by the corner now, as the others)


def card_pictures(html):
    """<!--ART name--> — the picture of a section of the program (tools/site_scales: book, compass, sextant, spectrum)
    faint in the corner of a card; <!--ICON name--> — a small line picture (site_scales.ICONS). An unknown name is
    ValueError."""
    def art(match):
        name = match.group(1)
        if name not in ('book', 'compass', 'sextant', 'spectrum'):
            raise ValueError(f'no picture of a section «{name}»')
        cls = 'cardArt mirror' if name in MIRRORED else 'cardArt'
        # the strengths of the window (0.07–0.22 over 1000 px of a window) are too faint on a card a fifth of its size
        drawing = re.sub(r'(stroke|fill)-opacity="([0-9.]+)"',
                         lambda m: f'{m.group(1)}-opacity="{min(0.6, float(m.group(2)) * CARD_STRENGTH):.2f}"',
                         getattr(site_scales, name)())
        return f'<div class="{cls}" aria-hidden="true">' + drawing + '</div>'

    def icon(match):
        if match.group(1) not in site_scales.ICONS:
            raise ValueError(f'no icon «{match.group(1)}»')
        return site_scales.icon(match.group(1))

    def nav(match):
        # the icon of the section in the program (assets/navigation, its brown accent — --gold of the page)
        name = match.group(1)
        if name not in ('atlas', 'compass', 'sextant', 'spectrum'):
            raise ValueError(f'no icon of a section «{name}»')
        svg = (ROOT / 'assets' / 'navigation' / f'{name}.svg').read_text(encoding='utf-8').strip()
        svg = svg.replace(' width="22" height="22"', '').replace('<svg ', '<svg class="navIcon" ', 1)
        return svg.replace('stroke="currentBrown"', 'style="stroke:var(--gold)"')

    return NAV.sub(nav, ICON.sub(icon, ART.sub(art, html)))


SHOT = re.compile(r'<!--SHOT ([a-z-]+) ([A-Za-z0-9]+)-->')
SHOT_SIZE = (1600, 1000)  # of site/img-program/*.webp, made from the windows of the program (tools/site_screenshots.py)


SHOT_LANGS = ('en', 'zh')  # name-LANG-THEME.webp beside the Russian name-THEME.webp; a language without its pictures
# shows the Russian


def shot_languages(source):
    """{name: [lang, …]} — the languages of SHOT_LANGS in which site/img-program has the pictures of a section (both
    themes)."""
    there = {p.name for p in (source / 'img-program').glob('*.webp')}
    found = {}
    for file in sorted(there):
        m = re.fullmatch(r'(.+)-(' + '|'.join(SHOT_LANGS) + r')-light\.webp', file)
        if m and f'{m.group(1)}-{m.group(2)}-dark.webp' in there:
            found.setdefault(m.group(1), []).append(m.group(2))
    return found


def shot_figures(template, folder, langs=None):
    """<!--SHOT name key--> → a figure with both pictures name-light.webp and name-dark.webp of folder (the one of the
    theme of the page is shown by its CSS) and the caption key — in the panels of the sections of the home page.
    Langs ({name: [lang, …]}, shot_languages): the languages it has its own pictures in (data-langs), the script of the
    page and shot_language take them."""
    width, height = SHOT_SIZE
    langs = langs or {}

    def figure(match):
        name, key = match.groups()
        own = ' '.join(langs.get(name, ()))
        pictures = ''.join(
            f'<img class="{cls}" src="{folder}{name}-{theme}.webp" width="{width}" height="{height}" loading="lazy" '
            f'alt="" data-alt="{key}">' for cls, theme in (('lt', 'light'), ('dk', 'dark')))
        return (f'<figure class="shot"><a href="{folder}{name}-light.webp" data-shot="{name}" data-langs="{own}" '
                f'target="_blank" rel="noopener">{pictures}</a><figcaption data-t="{key}"></figcaption></figure>')

    return SHOT.sub(figure, template)


def shot_language(page, lang):
    """The pictures of the sections in the page of lang (en/, zh/) — its own where the figure has them (data-langs),
    so the page shows them before its script runs."""
    def figure(match):
        block, name, own = match.group(0), match.group(1), match.group(2).split()
        if lang not in own:
            return block
        return re.sub(rf'(img/program/{re.escape(name)})-(light|dark)\.webp', rf'\1-{lang}-\2.webp', block)

    return re.sub(r'<figure class="shot"><a href="[^"]*" data-shot="([^"]+)" data-langs="([^"]*)".*?</figure>', figure, page)


PROGRAM_GONE = """<!doctype html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="robots" content="noindex">
<link rel="canonical" href="{url}">
<meta http-equiv="refresh" content="0; url=../#program">
<title>Азимут</title>
<script>location.replace('../' + location.search + '#program')</script>
</head><body><p><a href="../#program">Азимут — программа</a></p></body></html>
"""


TOPIC_PICTURE = re.compile(r"\['([a-z0-9]+)', 'ex\d+'\]")  # the pool of the home page: const EXAMPLES = [['pes', 'ex1'], …]


def topic_pictures(source, out, home):
    """The pictures of the topics shown on the home page (site/img-topics/NAME-LANG-THEME.webp, taken from the Atlas of
    the site in each language and theme) to out/img/topics/. Every
    topic of the pool of the page (EXAMPLES, three of it shown at random) has its six, every picture there is of a
    topic of the pool — else ValueError."""
    named = TOPIC_PICTURE.findall(home)
    there = {p.name for p in (source / 'img-topics').glob('*.webp')}
    wanted = {f'{name}-{lang}-{theme}.webp' for name in named for lang in ('ru', 'en', 'zh') for theme in ('light', 'dark')}
    if not named or there != wanted:
        raise ValueError(f'site/index.html and site/img-topics differ: {sorted(there ^ wanted)}')
    (out / 'img' / 'topics').mkdir(parents=True, exist_ok=True)
    for name in sorted(there):
        shutil.copy2(source / 'img-topics' / name, out / 'img' / 'topics' / name)


def program_pictures(source, out, home):
    """The pictures of the sections (site/img-program/NAME-THEME.webp, tools/site_screenshots.py) to out/img/program/.

    The panels of the parts on the home page tell all the page «О программе» (program/) told. Every picture there is
    named in the home page, every one named is there — else ValueError: the page and the folder go together. The address
    program/ stays as a page that leads to the part «Программа» of the home page (links and bookmarks to it, the index
    of a search engine)."""
    named = [m.group(1) for m in SHOT.finditer(home)]
    there = {p.name for p in (source / 'img-program').glob('*.webp')}
    wanted = {f'{name}-{theme}.webp' for name in named for theme in ('light', 'dark')}
    # and the pictures in the other languages (shot_languages) — of a section named, in both themes
    wanted |= {f'{name}-{lang}-{theme}.webp' for name, langs in shot_languages(source).items() if name in named
               for lang in langs for theme in ('light', 'dark')}
    if there != wanted:
        raise ValueError(f'site/index.html and site/img-program differ: {sorted(there ^ wanted)}')
    (out / 'img' / 'program').mkdir(parents=True, exist_ok=True)
    for name in sorted(there):
        shutil.copy2(source / 'img-program' / name, out / 'img' / 'program' / name)


def wordmark_script(web):
    """const WORD={ru,en,zh} — the wordmarks of the Atlas header (web/index.html), for the home page."""
    text = (web / 'index.html').read_text(encoding='utf-8')
    start = text.index('const WORD=')
    return text[start:text.index('};', start) + 2]


def build(out, package=PACKAGE, pyodide=PYODIDE, landing=LANDING, answered=True, log=None, url=SITE_URL):
    """The site in the folder out (made anew): the home page at its root, the Atlas in atlas/.
    answered: the kept answers of the long calculations (ANSWERED) are counted or taken from site/.answers.
    Returns {'pages': n with calculations, 'zip': bytes, 'files': n, 'answers': n}."""
    out = Path(out)
    web = package / 'web'
    atlas = out / 'atlas'
    if out.exists():
        ours = (atlas / 'assets' / 'js' / 'qcstatic.js').is_file() or (out / 'assets' / 'js' / 'qcstatic.js').is_file()
        if not ours and any(out.iterdir()):
            raise ValueError(f'{out} is not empty and is not a site built by this tool — choose another folder')
        for old in out.iterdir():  # the folder itself stays: a server started in it goes on serving the new site
            shutil.rmtree(old) if old.is_dir() and not old.is_symlink() else old.unlink()
    out.mkdir(parents=True, exist_ok=True)
    shutil.copytree(web, atlas)
    pages = 0
    for page in sorted(atlas.rglob('*.html')):
        text = page.read_text(encoding='utf-8')
        changed, calculating = with_static(text)
        if not calculating and page.parent == atlas and FIRST_SCRIPT.search(text):  # index.html: the host of the worker
            first = FIRST_SCRIPT.search(text)
            # defer — the script of the page writes the header and the overview at once;
            # the worker it hosts is wanted by the frames only, asked for after the page has been read
            changed = text[:first.start()] + '<script defer src="assets/js/qcstatic.js"></script>\n' + text[first.start():]
        pages += calculating
        if changed != text:
            page.write_text(changed, encoding='utf-8')
    scripts = atlas / 'assets' / 'js'
    scales = {'size': site_scales.ZONE, 'dial': site_scales.dial(), 'book': site_scales.book(),
              'spin': site_scales.spin_dial(), 'spinBox': list(site_scales.spin_box())}  # turned while a topic loads
    shutil.copyfile(ROOT / 'site' / 'atlas-page.css', atlas / 'assets' / 'css' / 'site-page.css')
    page_js = (ROOT / 'site' / 'atlas-page.js').read_text(encoding='utf-8')  # with the compass
    if '__COMPASS__' not in page_js or '__COMPASS_CSS__' not in page_js:
        raise ValueError('site/atlas-page.js has no place for the compass')
    (scripts / 'site-page.js').write_text(page_js.replace('__COMPASS_CSS__', json.dumps(COMPASS_PAGE_CSS))
                                          .replace('__COMPASS__', COMPASS_SVG), encoding='utf-8')
    version = re.search(r'__version__\s*=\s*"([^"]+)"', (package / '__init__.py').read_text(encoding='utf-8')).group(1)
    health = json.dumps({'ok': True, 'version': version, 'static': True}, ensure_ascii=False)  # as ENTRY health()
    (scripts / 'qcstatic.js').write_text(
        STATIC.replace('__SCALES__', json.dumps(scales)).replace('__HEALTH__', json.dumps(health)).replace('__RUNTIME__', RUNTIME_FOLDER)
        .replace('__COMPASS_CSS__', json.dumps(COMPASS_PAGE_CSS)).replace('__COMPASS__', COMPASS_SVG), encoding='utf-8')
    for name, size in ATLAS_ICONS.items():  # the icon of the program in the tab of every page of the Atlas
        (atlas / 'assets' / 'img' / name).unlink(missing_ok=True)
        shutil.copy2(APP_ICON / f'azimuth-{size}.png', atlas / 'assets' / 'img' / ATLAS_ICON_NAME.format(size=size))
    if pyodide == 'local':  # the runtime is a part of the site: no foreign CDN to read the Atlas
        (atlas / 'assets' / RUNTIME_FOLDER).mkdir(parents=True, exist_ok=True)
        for file in runtime_files():
            shutil.copy2(file, atlas / 'assets' / RUNTIME_FOLDER / file.name)
        (atlas / 'assets' / RUNTIME_FOLDER / 'LICENSES.txt').write_text(RUNTIME_LICENSES, encoding='utf-8')
        address = f"new URL('../{RUNTIME_FOLDER}/', self.location.href).href"
    else:
        address = json.dumps(pyodide if pyodide.endswith('/') else pyodide + '/')
    (scripts / 'qcworker.js').write_text(WORKER.replace('__PYODIDE__', address), encoding='utf-8')
    (atlas / 'assets' / 'py').mkdir(parents=True, exist_ok=True)
    packed = package_zip(package)
    (atlas / 'assets' / 'py' / 'quas_atlas.zip').write_bytes(packed)
    if landing is not None:
        home = landing.read_text(encoding='utf-8')
        if '/*WORD*/' not in home:
            raise ValueError(f'{landing}: no /*WORD*/ place for the wordmarks')
        if '<!--DIAL-->' not in home:
            raise ValueError(f'{landing}: no <!--DIAL--> place for the scale of the background')
        # the sextant of the lower left corner is no longer on the home page; the four parts
        # of the program carry the pictures of their sections in their cards (card_pictures)
        home = card_pictures(home.replace('<!--DIAL-->', site_scales.dial(turning=True)).replace('<!--CORNER-->', site_scales.sextant()))
        # a click on the title of a section slides out its panel on the right, with the pictures of the section
        program_pictures(landing.parent, out, home)
        topic_pictures(landing.parent, out, home)
        home = shot_figures(home, 'img/program/', shot_languages(landing.parent))
        texts = json.loads((landing.parent / 'texts.json').read_text(encoding='utf-8'))
        # the mirror for Russia (ru.azimuth-chem.com, Yandex Object Storage) — the main site points to it,
        # the mirror names the main address
        if 'ru.azimuth-chem.com' in url:
            for words in texts.values():
                if 'mirrorHere' in words:
                    words['mirror'] = words['mirrorHere']
        fonts_css = (web / 'assets' / 'fonts' / 'fonts.css').read_text(encoding='utf-8')
        for lang, path in HOME_PATHS.items():
            page = shot_language(home_page(home, texts, url, path=path, lang=lang), lang)
            page = page.replace('download/Azimuth-manual-ru.pdf', f'download/Azimuth-manual-{lang}.pdf')  # its own book
            page = page.replace('</head>', RAIL_EARLY + '</head>', 1).replace('/*WORD*/', wordmark_script(web))
            brand = '<a class="brand" href="./" id="brand" aria-label="Азимут"></a>'
            if page.count(brand) != 1:
                raise ValueError('the home page: the place of the name (#brand) was not found once')
            label = {'ru': 'Азимут', 'en': 'Azimuth', 'zh': '方位'}[lang]
            page = page.replace(brand, f'<a class="brand" href="./" id="brand" aria-label="{label}">{wordmarks(web)[lang]}</a>')
            page = fonts_inline(page, fonts_css, HOME_FONTS, '../' if path else '')
            if path:
                page = in_folder(page, lang)
                (out / path).mkdir(exist_ok=True)
            (out / path / 'index.html').write_text(page, encoding='utf-8')
        (out / 'sitemap.xml').write_text(sitemap(out, url), encoding='utf-8')
        (out / 'img').mkdir(exist_ok=True)
        shutil.copy2(landing.parent / 'og.jpg', out / 'img' / 'og.jpg')  # the picture of a link's preview, 1200 × 630
        (out / 'program').mkdir(exist_ok=True)
        (out / 'program' / 'index.html').write_text(PROGRAM_GONE.replace('{url}', url), encoding='utf-8')
        # the side panel of the program for the whole site (site/rail.js): on the home page and in the Atlas
        shutil.copy2(landing.parent / 'rail.js', out / 'rail.js')
        # an address that is not a page of the site: with 404.html the hosting answers «not found» with this page
        # (without it Cloudflare Pages gave the home page for any address — a student)
        lost = (landing.parent / '404.html').read_text(encoding='utf-8')
        (out / '404.html').write_text(lost.replace('</head>', RAIL_EARLY + '</head>', 1), encoding='utf-8')
        # the bucket of the mirror (Yandex Object Storage, the objects not listed publicly) answers 403 for
        # a file it lacks, and a robot reads a 403 of robots.txt as «all is closed» — so the rules are written
        (out / 'robots.txt').write_text(f'User-agent: *\nAllow: /\nSitemap: {url}sitemap.xml\n', encoding='ascii')
        shutil.copy2(APP_ICON / 'glyph.svg', out / 'img' / 'glyph-light.svg')
        shutil.copy2(APP_ICON / 'dark' / 'glyph.svg', out / 'img' / 'glyph-dark.svg')
        shell = atlas / 'index.html'
        text = shell.read_text(encoding='utf-8')
        if 'window.QuASAtlas=' not in text:
            raise ValueError('the index page of the Atlas has no QuASAtlas for the side panel')
        # after the last script of the page (it ends without </body>): QuASAtlas is there by then. The panel's script is
        # in the page itself (it waited for its own request) — the panel is drawn with the page; the home page keeps it
        # as a file
        panel = (out / 'rail.js').read_text(encoding='utf-8')
        if '</script' in panel.lower():
            raise ValueError('site/rail.js has «</script»: it cannot stand inside the index page of the Atlas')
        # right after the header, before them — the panel is drawn
        # with the header; it wires itself to the page (QuASAtlas) when the page has been read (rail.js wireAtlas)
        if text.count('</header>') != 1:
            raise ValueError('the index page of the Atlas has no single </header> for the side panel')
        shell.write_text(text.replace('</header>', '</header>\n<script data-root="../" data-here="atlas">' + panel
                                      + '</script>', 1), encoding='utf-8')
        # the icon of the program (assets/app-icon), as in the Dock and the taskbar, under a new name (a browser keeps
        # the icon of an address), and /favicon.ico, which a browser asks for by itself
        for size in (32, 64, 256):
            shutil.copy2(APP_ICON / f'azimuth-{size}.png', out / 'img' / ATLAS_ICON_NAME.format(size=size))
        shutil.copy2(APP_ICON / 'Azimuth.ico', out / 'favicon.ico')
        # Safari asks for these by
        # itself, at the root, whatever the page names — the icon of the program there too
        for name in ('apple-touch-icon.png', 'apple-touch-icon-precomposed.png'):
            shutil.copy2(APP_ICON / 'azimuth-256.png', out / name)
        # Safari asks for /apple-touch-icon.png by
        # itself (it was «not found») — the icon of the program there too
        shutil.copy2(APP_ICON / 'azimuth-256.png', out / 'apple-touch-icon.png')
        shutil.copy2(APP_ICON / 'azimuth-256.png', out / 'apple-touch-icon-precomposed.png')
        shutil.copy2(LANDING_PICTURE, out / 'img' / LANDING_PICTURE.name)
        for picture in SECTION_PICTURES:
            shutil.copy2(picture, out / 'img' / picture.name)
        (out / '_redirects').write_text(REDIRECTS, encoding='ascii')
        (out / '_headers').write_text(HEADERS, encoding='ascii')
    (out / '.nojekyll').write_text('', encoding='ascii')  # GitHub Pages: serve the folders as they are
    if answered:
        made_answers = answers(atlas / 'assets' / 'answers', package, log=log)
        if INITIAL_REQUESTS.is_file():
            initial_answers(atlas / 'assets' / 'initial', package, log=log)
    client = atlas / 'assets' / 'js' / 'qcapi.js'  # one request at a time for a slider (LIVE_NEW)
    text = client.read_text(encoding='utf-8')
    if text.count(LIVE_OLD) != 1:
        raise ValueError('QC.live of assets/js/qcapi.js changed: the site cannot put its own in its place')
    text = text.replace(LIVE_OLD, LIVE_NEW)
    # «Считаю…» with the compass of the program instead of a turning ring (COMPASS_SVG)
    for was, now in ((BUSY_MARK, BUSY_MARK.replace("'<i></i>", "'" + COMPASS_SVG)),
                     (BUSY_CSS, BUSY_CSS[:-1] + ' + ' + json.dumps(COMPASS_PAGE_CSS) + ';')):
        if text.count(was) != 1:
            raise ValueError('the note «Считаю…» of assets/js/qcapi.js changed: the site cannot give it the compass')
        text = text.replace(was, now)
    client.write_text(text, encoding='utf-8')
    shell = atlas / 'index.html'  # the search index: a file a language, read when searched (split_search)
    text, index = split_search(shell.read_text(encoding='utf-8'))
    title = text.index('</title>') + len('</title>')  # the index page has no <head> tag: after its title
    if text.count('id="nojs"') != 1:
        raise ValueError('the index page of the Atlas has no note #nojs any more')
    # the faces of the fonts and the name in the page itself (fonts_inline, wordmarks)
    # the row of the topics of a section (▾ … ‹ ›) stands hidden until the page knows what it shows (the
    # overview has none; the script of the page shows it for a topic) — it stood empty over the loading overview
    row = '<div class="secrow" id="secrow">'
    if text.count(row) != 1:
        raise ValueError('the index page of the Atlas has no row of the topics #secrow any more')
    text = text.replace(row, '<div class="secrow" id="secrow" hidden>')
    main = '<main id="stage">'
    if text.count(main) != 1:
        raise ValueError('the index page of the Atlas has no place of the topics <main id="stage"> any more')
    text = text.replace(main, main + STAGE_COMPASS_HTML)  # the waiting compass of a topic (STAGE_COMPASS)
    text = fonts_inline(text[:title] + '\n' + SHELL_EARLY + RAIL_EARLY + STAGE_COMPASS + text[title:],
                        (web / 'assets' / 'fonts' / 'fonts.css').read_text(encoding='utf-8'))
    brand = '<span class="q1 qBrand">Азимут</span>'
    if text.count(brand) < 1:
        raise ValueError('the index page of the Atlas: the name (.qBrand) was not found')
    text = text.replace(brand, '<span class="q1 qBrand">' + wordmarks(web)['ru'] + '</span>')
    shell.write_text(text, encoding='utf-8')
    for language, entries in index.items():
        (atlas / 'assets' / f'search-{language}.json').write_text(
            json.dumps(entries, ensure_ascii=False, separators=(',', ':')), encoding='utf-8')
    for page in atlas.rglob('*.html'):  # the pages ask for the icon by its new name (ATLAS_ICON_NAME)
        text = page.read_text(encoding='utf-8')
        named = text
        for name, size in ATLAS_ICONS.items():
            named = named.replace('assets/img/' + name, 'assets/img/' + ATLAS_ICON_NAME.format(size=size))
        if named != text:
            page.write_text(named, encoding='utf-8')
    color_scheme(out)  # no white ground before a dark page
    versioned(out)
    listed = site_files(out)
    (out / 'site-files.json').write_text(json.dumps(listed, ensure_ascii=False), encoding='utf-8')
    (out / 'sw.js').write_text(SERVICE_WORKER.replace('__VERSION__', json.dumps(listed['version']))
                               .replace('__IMMUTABLE__', json.dumps(list(IMMUTABLE)))
                               .replace('__PATTERN__', json.dumps(IMMUTABLE_PATTERN)), encoding='utf-8')
    return {'pages': pages, 'zip': len(packed), 'files': sum(1 for p in out.rglob('*') if p.is_file()),
            'answers': len(made_answers) if answered else 0}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--out', required=True, help='the folder of the site (made anew)')
    parser.add_argument('--pyodide', default=PYODIDE, help='«local» (by default): Pyodide is a part of the site; or the address of a folder with it (ending with /)')
    parser.add_argument('--url', default=SITE_URL, help='the address of this copy of the site (the previews of a link): the mirror for Russia — https://ru.azimuth-chem.com/ (tools/upload_site_yandex.py)')
    parser.add_argument('--no-answers', action='store_true', help='do not count the kept answers of the long calculations')
    args = parser.parse_args(argv)
    try:
        made = build(Path(args.out).expanduser(), pyodide=args.pyodide, answered=not args.no_answers, url=args.url,
                     log=lambda key: print('считается:', key, flush=True))
    except (ValueError, OSError) as exc:
        print(exc)
        return 1
    print(f'Сайт собран: {Path(args.out).expanduser()} — файлов {made["files"]}, страниц с расчётами {made["pages"]}, '
          f'пакет Python {made["zip"] / 1e6:.1f} МБ.')
    print('Проверить: cd в эту папку, python3 -m http.server 8080, открыть http://localhost:8080/ (Атлас — /atlas/)')
    return 0


if __name__ == '__main__':
    sys.exit(main())

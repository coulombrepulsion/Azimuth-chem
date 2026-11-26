"""The Atlas as a static site (tools/build_atlas_site.py): what is packed answers as the server does."""

import importlib
import json
import re
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

import build_atlas_site as site  # noqa: E402


def _built(tmp_path, pyodide='https://example.org/pyodide'):
    out = tmp_path / 'site'
    made = site.build(out, pyodide=pyodide, answered=False)  # the kept answers have their own test (minutes otherwise)
    return out, made


def test_the_site_has_the_pages_and_every_calculating_page_gets_the_static_script(tmp_path):
    out, made = _built(tmp_path)
    assert made['pages'] > 100
    for page in (out / 'atlas').rglob('*.html'):
        text = page.read_text(encoding='utf-8')
        if 'qcapi.js' in text:
            assert text.index('qcstatic.js') < text.index('qcapi.js'), page
            assert text.count('qcstatic.js') == 1, page
    assert 'assets/js/qcstatic.js' in (out / 'atlas' / 'index.html').read_text(encoding='utf-8')  # the one worker
    home = (out / 'index.html').read_text(encoding='utf-8')
    assert 'qcstatic' not in home and '/*WORD*/' not in home and 'const WORD={ru:' in home
    assert (out / 'img' / 'quill-home-desk.webp').is_file() and '/ru/:page /atlas/ru/:page 301' in (out / '_redirects').read_text()
    # Quill of the part of the Atlas — the picture the home page names is in the built site
    assert 'img/quill-site-atlas.webp' in home and (out / 'img' / 'quill-site-atlas.webp').is_file()
    # Quill over each of the four cards of the parts of the program — Теория, Молекула, Расчёт, Результат
    for part, name in (('atlas', 'theory'), ('compass', 'molecule'), ('sextant', 'calculation'), ('spectrum', 'result')):
        start = home.index(f'<div class="card part" data-part="{part}">')
        card = home[start:home.index('class="what"', start)]  # the card up to its label: the picture is there
        assert f'<img class="cardQuill" src="img/quill-site-{name}.webp" width="96" height="96"' in card, part
        assert (out / 'img' / f'quill-site-{name}.webp').is_file(), name
    # two of the four pictures turned, to face different sides
    # Quill in the upper right corner, the text around her; Молекула and Расчёт turned
    assert '.card.part[data-part="compass"] .cardQuill,.card.part[data-part="sextant"] .cardQuill{transform:scaleX(-1)}' in home
    assert '.cardQuill{float:right;' in home
    worker = (out / 'atlas' / 'assets' / 'js' / 'qcworker.js').read_text(encoding='utf-8')
    assert '"https://example.org/pyodide/"' in worker and '__PYODIDE__' not in worker


def test_the_packed_package_has_no_server_and_answers_as_the_server_does(tmp_path, monkeypatch):
    out, _made = _built(tmp_path)
    unpacked = tmp_path / 'unpacked'
    with zipfile.ZipFile(out / 'atlas' / 'assets' / 'py' / 'quas_atlas.zip') as archive:
        names = archive.namelist()
        archive.extractall(unpacked)
    assert 'quas_atlas/server.py' not in names and not any(n.startswith('quas_atlas/web/') for n in names)
    assert any(n.startswith('quas_atlas/core/data/') and n.endswith('.json') for n in names)
    for name in [m for m in sys.modules if m == 'quas_atlas' or m.startswith('quas_atlas.')]:
        monkeypatch.delitem(sys.modules, name)
    monkeypatch.syspath_prepend(str(unpacked))
    entry = importlib.import_module('atlas_site_entry')
    try:
        assert Path(sys.modules['quas_atlas'].__file__).is_relative_to(unpacked)
        assert json.loads(entry.health())['ok'] is True
        endpoints = json.loads(entry.endpoints())
        assert len(endpoints) > 100
        failed = [name for name in endpoints if entry.handle(name, '{}')[0] >= 500]
        assert failed == []
        status, body = entry.handle('no.such', '{}')
        assert status == 404 and 'error' in json.loads(body)
        assert entry.handle(next(iter(endpoints)), '{not json')[0] == 400
    finally:
        for name in [m for m in sys.modules if m == 'atlas_site_entry' or m == 'quas_atlas' or m.startswith('quas_atlas.')]:
            sys.modules.pop(name, None)


def test_a_foreign_folder_is_not_overwritten(tmp_path):
    out = tmp_path / 'mine'
    out.mkdir()
    (out / 'thesis.txt').write_text('x', encoding='utf-8')
    try:
        site.build(out)
    except ValueError:
        pass
    else:
        raise AssertionError('a folder with foreign files was replaced')
    assert (out / 'thesis.txt').is_file()


def test_exp_np_gives_ldexp_a_c_int_exponent(monkeypatch):
    """In a browser (Pyodide) the C long has 32 bits and numpy refuses a 64-bit exponent: the topic «Атомы в
    молекулах» answered «ufunc 'ldexp' not supported» on the site."""
    import numpy as np

    sys.path.insert(0, str(ROOT / 'modules' / 'atlas' / 'atlas_v2'))
    from quas_atlas.core import jsmath_np

    real, seen = np.ldexp, []

    def watched(y, k):
        seen.append(np.asarray(k).dtype)
        return real(y, k)

    monkeypatch.setattr(np, 'ldexp', watched)
    x = np.array([-800.0, -745.0, -1.0, 0.3, 1.0, 700.0, 800.0])
    with np.errstate(all='ignore'):
        got = jsmath_np.exp_np(x)
    assert seen and all(kind == np.dtype(np.intc) for kind in seen)
    assert got[0] == 0.0 and got[-1] == np.inf and abs(got[4] - 2.718281828459045) < 1e-15


def test_the_dial_of_the_corner_turns_while_a_topic_loads():
    # a whole ring (marks every 5°, the cardinal lines) of the
    # dial's radius, turned about its own centre while the frame of the topic has not come; the compass of the stage
    # is not shown then
    import re

    import site_scales

    spin = site_scales.spin_dial()
    x, y, side = site_scales.spin_box()
    assert side == 2 * (site_scales.DIAL_R + site_scales.SPIN_PAD)
    assert (x + side / 2, y + side / 2) == (site_scales.DIAL_CX, site_scales.DIAL_CY)
    f = site_scales._f
    assert f'viewBox="{f(x)} {f(y)} {f(side)} {f(side)}"' in spin
    assert len(re.findall(r'M[-0-9.]+ [-0-9.]+L', spin)) >= 360 // 5
    build = (ROOT / 'tools' / 'build_atlas_site.py').read_text(encoding='utf-8')
    assert "'spin': site_scales.spin_dial()" in build and 'spinBox: SCALES.spinBox' in build
    assert 'html.qcDialTurning .qcStage{display:none!important}' in build
    index = (ROOT / 'modules' / 'atlas' / 'atlas_v2' / 'quas_atlas' / 'web' / 'index.html').read_text(encoding='utf-8')
    assert 'qcDialSpin' in index and '@keyframes qcDialTurn' in index
    assert "lf.dataset.ld!=='1'" in index and 'qcDialTurning' in index


def test_the_site_has_the_icon_of_the_program_and_the_scales_of_its_background(tmp_path):
    # the icon of the site is the icon of the program; the background pictures of the program
    # (hub/chrome.py Ornament: the dial, the sextant, the book) on the pages of the site
    import re

    import site_scales

    out, _ = _built(tmp_path)
    icons = ROOT / 'assets' / 'app-icon'
    # the home page too under the new name (img/icon-*.png was the winking Quill), and /favicon.ico
    for size in (32, 64, 256):
        assert (out / 'img' / f'azimuth-icon-{size}.png').read_bytes() == (icons / f'azimuth-{size}.png').read_bytes()
        assert not (out / 'img' / f'icon-{size}.png').exists()
    assert (out / 'favicon.ico').read_bytes() == (icons / 'Azimuth.ico').read_bytes()
    for name in ('apple-touch-icon.png', 'apple-touch-icon-precomposed.png'):  # asked for by Safari itself
        assert (out / name).read_bytes() == (icons / 'azimuth-256.png').read_bytes()
    # on the home page the panel's script follows the header
    home_text = (out / 'index.html').read_text(encoding='utf-8')
    assert home_text.index('</header>') < home_text.index('<script src="rail.js') < home_text.index('id="atlas"')
    home = (out / 'index.html').read_text(encoding='utf-8')
    assert 'href="img/azimuth-icon-32.png"' in home and 'atlas/assets/img/d4fffdebdad3.png' not in home
    for page in [out / '404.html', out / 'en' / 'index.html', out / 'zh' / 'index.html']:
        assert 'icon-32.png' in page.read_text(encoding='utf-8') and 'img/icon-' not in page.read_text(encoding='utf-8')
    pages = list((out / 'atlas').rglob('*.html'))
    assert len(pages) > 100
    for name, size in site.ATLAS_ICONS.items():  # a browser keeps an old icon under its name, so
        # the icon of the program goes under a new name, and no page asks for the old one
        # the icon of the program goes under a new name, and no page asks for the old one
        new = site.ATLAS_ICON_NAME.format(size=size)
        assert (out / 'atlas' / 'assets' / 'img' / new).read_bytes() == (icons / f'azimuth-{size}.png').read_bytes()
        assert not (out / 'atlas' / 'assets' / 'img' / name).exists()
        assert not any(name in p.read_text(encoding='utf-8') for p in pages)
    topic = (out / 'atlas' / 'ru' / 'symmetry.html').read_text(encoding='utf-8')
    assert 'href="../assets/img/azimuth-icon-32.png"' in topic
    assert '<!--DIAL-->' not in home and '<!--CORNER-->' not in home and home.count('<svg xmlns') >= 2
    static = (out / 'atlas' / 'assets' / 'js' / 'qcstatic.js').read_text(encoding='utf-8')
    assert '__SCALES__' not in static and 'qcScales' in static
    # the geometry of Ornament, counted independently: the dial — 37 marks (90…270° every 5°), 7 of them long
    # (every 30°), two circles, two dashed lines; the sextant — 31 marks (270…360° every 3°), 7 long (every 15°)
    dial, sextant = site_scales.dial(), site_scales.sextant()
    assert dial.count('<path') == 37 + 2 and dial.count('stroke-width="1.6"') == 7 and dial.count('<circle') == 2
    assert sextant.count('stroke-width="1.4"') == 7 and sextant.count('stroke-width="0.9"') == 24
    assert all(f'viewBox="0 0 {site_scales.ZONE} {site_scales.ZONE}"' in s for s in (dial, sextant, site_scales.book()))
    assert 'currentColor' not in site_scales.ink(dial, '#2a62b8')
    centre = re.search(r'<circle cx="([\d.]+)" cy="([\d.]+)" r="330"', dial)  # 70 px from the top right corner
    assert centre and (float(centre.group(1)), float(centre.group(2))) == (site_scales.ZONE - 70, 70)


def test_the_site_has_the_side_panel_of_the_program_on_the_home_page_and_in_the_atlas(tmp_path):
    # a side panel as in the program, with the languages and the theme; «Азимут» leads home; the
    # home page had no theme switch and the Atlas did not take the theme of the home page
    out, _ = _built(tmp_path)
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    home = (out / 'index.html').read_text(encoding='utf-8')
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    assert re.search(r'<script src="rail\.js\?v=[0-9a-f]{10}" data-root="\./" data-here="home">', home)
    # the panel's script in the page itself, right after the header and before the script of the page (the
    # owner: «Левая панель пустая всё равно при загрузке»); it wires itself to QuASAtlas when the page has been read
    panel = shell.index('<script data-root="../" data-here="atlas">' + rail[:200])
    assert shell.index('</header>') < panel < shell.index('window.QuASAtlas=') and shell.count(rail[:200]) == 1
    assert "document.addEventListener('DOMContentLoaded', wireAtlas)" in rail
    for name in ('glyph-light.svg', 'glyph-dark.svg'):
        assert (out / 'img' / name).is_file() and f'img/{name}' in rail
    # one theme and one language for the whole site: the keys of the Atlas page itself
    source = (site.PACKAGE / 'web' / 'index.html').read_text(encoding='utf-8')
    for key in ('qc-theme', 'qc-hub-lang'):
        assert f"'{key}'" in rail and f"'{key}'" in source
    assert "localStorage.getItem('qc-theme')" in home  # applied before the page is drawn
    assert 'azimuth-site-lang' not in home and 'class="langs"' not in home  # the switches moved to the panel
    for call in ('setThemeControl(false)', 'setLanguageControl(false)', 'setTheme(v)', 'setLanguage(v)'):
        assert call in rail


def test_what_is_kept_for_reading_offline_is_listed_and_the_service_worker_knows_its_version(tmp_path):
    # the Atlas of the site is read without a network
    out, _ = _built(tmp_path)
    listed = json.loads((out / 'site-files.json').read_text(encoding='utf-8'))
    on_disk = {p.relative_to(out).as_posix() for p in out.rglob('*') if p.is_file()}
    names = listed['common'] + listed['ru'] + listed['en'] + listed['zh']
    assert len(names) == len(set(names)) and set(names) <= on_disk
    assert on_disk - set(names) <= {'site-files.json', 'sw.js', '_redirects', '_headers', '.nojekyll', 'sitemap.xml'} | {
        n for n in on_disk if n.endswith(('.txt', '.md'))}  # everything a page may ask for is listed
    assert 'index.html' in listed['common'] and 'rail.js' in listed['common'] and 'atlas/index.html' in listed['common']
    assert 'atlas/assets/py/quas_atlas.zip' in listed['common'] and 'atlas/ru/h2.html' in listed['ru']
    assert all(n.startswith('atlas/en/') for n in listed['en']) and not any('/en/' in n for n in listed['ru'])
    worker = (out / 'sw.js').read_text(encoding='utf-8')
    assert json.dumps(listed['version']) in worker and '__VERSION__' not in worker and '__IMMUTABLE__' not in worker
    # a changed page is a new version (the copies of the old one are dropped); the same files — the same version
    assert site.site_files(out)['version'] == listed['version']
    (out / 'atlas' / 'ru' / 'h2.html').write_text('changed', encoding='utf-8')
    assert site.site_files(out)['version'] != listed['version']
    assert "register(ROOT + 'sw.js')" in (out / 'rail.js').read_text(encoding='utf-8')


def test_the_runtime_of_python_is_fetched_once_and_checked(tmp_path, monkeypatch):
    # Pyodide is a part of the site (no foreign CDN): the archive is checked by the sha256 written in the tool, numpy
    # by the sha256 its lock file names; a wrong file is refused and not kept
    import hashlib
    import io
    import tarfile

    import pytest

    wheel = b'a numpy wheel'
    lock = json.dumps({'packages': {'numpy': {'file_name': 'numpy-x.whl', 'sha256': hashlib.sha256(wheel).hexdigest()}}})
    packed = io.BytesIO()
    with tarfile.open(fileobj=packed, mode='w:bz2') as tar:
        for name in site.RUNTIME:
            data = lock.encode() if name == 'pyodide-lock.json' else name.encode()
            info = tarfile.TarInfo('pyodide/' + name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    archive = packed.getvalue()
    asked = []

    def opener(url):
        asked.append(url)
        return archive if url.endswith('.tar.bz2') else wheel

    monkeypatch.setattr(site, 'PYODIDE_CORE', ('https://example.org/core.tar.bz2', hashlib.sha256(archive).hexdigest()))
    folder = tmp_path / 'runtime'
    files = site.runtime_files(folder, opener=opener)
    assert [f.name for f in files] == list(site.RUNTIME) + ['numpy-x.whl'] and len(asked) == 2
    assert site.runtime_files(folder, opener=opener) == files and len(asked) == 2  # there already: nothing is fetched
    (folder / 'numpy-x.whl').write_bytes(b'something else')
    with pytest.raises(ValueError, match='sha256'):
        site.runtime_files(folder, opener=opener)
    assert not (folder / 'numpy-x.whl').exists()
    monkeypatch.setattr(site, 'PYODIDE_CORE', ('https://example.org/core.tar.bz2', '0' * 64))
    with pytest.raises(ValueError, match='sha256'):
        site.runtime_files(tmp_path / 'other', opener=opener)
    assert not (tmp_path / 'other' / 'pyodide.js').exists()
    with pytest.raises(ValueError):
        site.runtime_files(tmp_path / 'none', fetch=False)


def test_the_site_serves_the_runtime_itself(tmp_path):
    import pytest

    if not all((site.RUNTIME_DIR / name).is_file() for name in site.RUNTIME):
        pytest.skip('the Pyodide runtime is not fetched here (site/.pyodide)')
    out, _ = _built(tmp_path, pyodide='local')
    served = out / 'atlas' / 'assets' / f'pyodide-{site.PYODIDE_VERSION}'  # the version in the address
    wheel, digest = site.numpy_wheel()
    assert {p.name for p in served.iterdir()} == set(site.RUNTIME) | {wheel, 'LICENSES.txt'}
    assert site._sha256(served / wheel) == digest
    worker = (out / 'atlas' / 'assets' / 'js' / 'qcworker.js').read_text(encoding='utf-8')
    assert f"new URL('../pyodide-{site.PYODIDE_VERSION}/', self.location.href)" in worker
    assert 'cdn.jsdelivr.net' not in worker


def test_what_a_student_found_on_the_site_stays_fixed(tmp_path):
    # a student, any address was a page (the home page came, empty); the address kept another language
    # than the page; the longer one read, the slower the topics opened; on a phone the search ran over the edge and
    # Quill's fact covered the text
    out, _ = _built(tmp_path)
    lost = (out / '404.html').read_text(encoding='utf-8')
    assert 'data-here="lost"' in lost and 'href="/atlas/"' in lost and 'location.pathname' in lost
    assert 'src="/rail.js?v=' in lost and 'noindex' in lost  # absolute addresses: it is shown at any depth
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert "u.searchParams.set('lang', lang)" in rail and 'history.replaceState' in rail
    assert 'const KEEP = 3' in rail and 'table[k].remove(); delete table[k]' in rail
    assert 'body.hasRail .qtip{display:none!important}' in rail and 'body.hasRail .qbrandH{zoom:' in rail
    # the table of the open topics the panel prunes is the one of the page
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    assert 'frames={}' in shell and "frames[key]=f" in shell


def test_the_home_page_has_its_text_and_the_marks_of_a_preview_in_the_html(tmp_path):
    # a search engine and the preview of a link read the HTML, so it must not be empty
    import re

    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    texts = json.loads((ROOT / 'site' / 'texts.json').read_text(encoding='utf-8'))
    assert set(texts) == {'ru', 'en', 'zh'} and set(texts['ru']) == set(texts['en']) == set(texts['zh'])
    assert f'<h1 data-t="h1">{texts["ru"]["h1"]}</h1>' in home
    assert not re.search(r'data-t="[A-Za-z0-9]+"[^>]*></', home)  # no element left empty
    # {mail} is put in as a link the script fills; the address itself is nowhere whole (robots of spam)
    assert '<a class="mail" href="#author"></a>' in home.split('</aside>')[0]  # in the page, before its scripts
    assert 'contact@azimuth-chem.com' not in home  # the address of the site
    # the buttons «Скачать» lead to the releases of GitHub (the owner, 2026-11-26: «Ссылки на GitHub можно»)
    assert f'alt="{texts["ru"]["heroAlt"]}"' in home
    head = home[:home.index('<style>')]
    for mark in ('og:title', 'og:description', 'og:image', 'og:url', 'twitter:card', 'name="description"'):
        assert mark in head
    assert f'content="{site.SITE_URL}img/og.jpg"' in head and (out / 'img' / 'og.jpg').stat().st_size > 20000
    assert (out / 'img' / 'og.jpg').read_bytes()[:3] == b'\xff\xd8\xff'  # a JPEG: every messenger shows it
    assert '/*TEXTS*/' not in home and json.dumps(texts['zh']['h1'], ensure_ascii=False) in home  # one source
    with pytest.raises(ValueError, match='nothing'):
        site.home_page('<p data-t="nothing"></p><!--HEAD-->/*TEXTS*/', texts)


def test_the_long_calculations_are_answered_by_kept_files(tmp_path):
    # (benzene took 45 s in a browser)
    sys.path.insert(0, str(site.PACKAGE.parent))
    from quas_atlas import api
    from quas_atlas import pages as _pages  # noqa: F401

    assert site.request_key('aim.stage', {'k': 'H2', 'stage': 'scf', 'b': 'STO-3G'}) == \
        'aim.stage|{"b":"STO-3G","k":"H2","stage":"scf"}'  # as JSON.stringify of the keys sorted
    with pytest.raises(ValueError):
        site.request_key('h2.scan', {'R': 1.4})  # a fraction is written differently by Python and JavaScript
    # the pairs of the profiles, as the page takes them: bond points only, a pair once, the heavier nucleus first
    scf = {'atoms': [{'Z': 1}, {'Z': 8}, {'Z': 1}],
           'cps': [{'type': 'b', 'atoms': [0, 1]}, {'type': 'b', 'atoms': [1, 0]}, {'type': 'r', 'atoms': [0, 2]},
                   {'type': 'b', 'atoms': [1, 2]}, {'type': 'b', 'atoms': [-1, 2]}]}
    asked = site.aim_requests('H2O', 'STO-3G', scf)
    assert [p['stage'] for n, p in asked if n == 'aim.stage'] == ['scf', 'map', 'vol', 'esp', 'bader']
    assert [(p['ia'], p['ib']) for n, p in asked if n == 'aim.prof'] == [(1, 0), (1, 2)]
    counted = []
    folder, kept = tmp_path / 'atlas' / 'assets' / 'answers', tmp_path / 'kept'
    index = site.answers(folder, wanted=(('H2', 'STO-3G'),), kept=kept, log=counted.append)
    assert len(index) == 6 and len(counted) == 6  # five stages and the one bond
    assert json.loads((folder.parent / 'answers-index.json').read_text(encoding='utf-8')) == index
    key = next(k for k in index if k.startswith('aim.prof|'))
    params = json.loads(key.split('|', 1)[1])
    assert {params['ia'], params['ib']} == {0, 1}
    direct = json.dumps(api.to_json(api.call('aim.prof', params)),
                        ensure_ascii=False, allow_nan=False)
    assert (folder / index[key]).read_text(encoding='utf-8') == direct  # the very answer of the worker
    again = []
    assert site.answers(tmp_path / 'second', wanted=(('H2', 'STO-3G'),), kept=kept, log=again.append) == index
    assert again == []  # kept: nothing is counted twice
    listed = site.site_files(tmp_path)
    assert not any('/answers/' in n for n in listed['common']) and 'atlas/assets/answers-index.json' in listed['common']


def test_the_topics_of_the_site_open_their_molecules_in_the_installed_program(tmp_path):
    """«Открыть в Компасе» on the site — the panel of the site asks the shell for the buttons as links, the
    page opens azimuth://compass/<key>, and every key the pages name is one the program understands."""
    import re

    from azimuth import links

    out, _ = _built(tmp_path)
    assert "setControl('compass', 'link')" in (out / 'rail.js').read_text(encoding='utf-8')
    assert "v==='link'?'link':!!v" in (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    nav = (out / 'atlas' / 'assets' / 'js' / 'nav.js').read_text(encoding='utf-8')
    assert "'azimuth://compass/' + k" in nav
    shown = set(re.findall(r"(\w+): '", nav[nav.index('const F = {'):nav.index('};', nav.index('const F = {'))]))
    assert shown == set(links.MOLECULES)  # a button for every molecule of the table, and no other
    named = set()
    for page in (out / 'atlas').glob('*/*.html'):
        for content in re.findall(r'<meta name="qc-molecules" content="([^"]*)"', page.read_text(encoding='utf-8')):
            named |= {k.strip() for k in content.split(',')}
    assert len(named) >= 15 and named <= set(links.MOLECULES)
    for key in named:
        assert links.parse('azimuth://compass/' + key) is not None


def test_the_runtime_starts_whatever_type_the_server_gives_its_file(tmp_path):
    """The site gave pyodide.asm.wasm without a type, the browser refused to compile it from the stream
    («Incorrect response MIME type») and no page calculated anything. The worker compiles from the bytes, before
    the runtime is started; the types are also said to the hosting."""
    out, _ = _built(tmp_path)
    worker = (out / 'atlas' / 'assets' / 'js' / 'qcworker.js').read_text(encoding='utf-8')
    assert worker.index('WebAssembly.compileStreaming =') < worker.index('loadPyodide(')
    assert worker.index('WebAssembly.instantiateStreaming =') < worker.index('loadPyodide(')
    assert 'arrayBuffer()' in worker
    headers = (out / '_headers').read_text(encoding='ascii')
    assert f'/atlas/assets/pyodide-{site.PYODIDE_VERSION}/*.wasm\n  Content-Type: application/wasm\n' in headers
    import json

    lists = json.loads((out / 'site-files.json').read_text(encoding='utf-8'))
    assert not any('_headers' in name for names in lists.values() if isinstance(names, list) for name in names)


def test_the_search_index_is_a_file_a_language_read_when_searched(tmp_path):
    """The index page of the Atlas carried what the search looks through in three
    languages — four fifths of it. On the site it is a file a language; what was in the page is in the files, whole."""
    import json

    source = (site.PACKAGE / 'web' / 'index.html').read_text(encoding='utf-8')
    start = source.index('/*SIDX*/const SIDX=') + len('/*SIDX*/const SIDX=')
    was = json.loads(source[start:source.index('/*SIDX_END*/')].rstrip().rstrip(';'))
    out, _ = _built(tmp_path)
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    panel = len((out / 'rail.js').read_bytes())  # the side panel's script stands in the page; not the index
    assert len(shell.encode()) - panel < 0.3 * len(source.encode())
    assert 'const SIDX={}' in shell and "fetch('assets/search-'+l+'.json')" in shell
    assert set(was) == {'ru', 'en', 'zh'}
    for language, entries in was.items():
        assert len(entries) > 500
        assert json.loads((out / 'atlas' / 'assets' / f'search-{language}.json').read_text(encoding='utf-8')) == entries
        assert entries[5][2] not in shell  # the texts are not in the page any more
    listed = json.loads((out / 'site-files.json').read_text(encoding='utf-8'))
    assert {f'atlas/assets/search-{language}.json' for language in was} <= set(listed['common'])  # kept offline
    # a page whose search was rewritten is refused, not built wrong
    import pytest

    with pytest.raises(ValueError):
        site.split_search(source.replace(' function open(){W.classList.add', ' function open2(){W.classList.add'))


def test_what_a_topic_asks_when_opened_is_counted_at_the_build(tmp_path):
    """The answers kept for the opening of a topic are the texts Python itself gives — counted by the package from
    the requests recorded in a browser (site/initial-requests.json), under the keys the page writes."""
    import json

    recorded = json.loads(site.INITIAL_REQUESTS.read_text(encoding='utf-8'))
    assert len(recorded) >= 40 and all(recorded.values())
    pages = {p.stem for p in (site.PACKAGE / 'web' / 'ru').glob('*.html')}
    assert set(recorded) <= pages
    for topic, asked in recorded.items():
        for name, params in asked:
            # the parameters are kept as the page wrote them (JavaScript writes numbers its own way): only read here
            assert isinstance(json.loads(params), dict) and name != 'health'
    # two cheap topics counted here, the oracle is the package asked directly
    topic = 'huckel'
    few = tmp_path / 'requests.json'
    few.write_text(json.dumps({topic: recorded[topic][:2], 'no-such-endpoint': [['nothing.here', '{}']]}), encoding='utf-8')
    made = site.initial_answers(tmp_path / 'initial', requests=few, kept=tmp_path / 'kept')
    assert made == {topic: 2}  # what the package refuses is left out, not written as an answer
    bundle = json.loads((tmp_path / 'initial' / f'{topic}.json').read_text(encoding='utf-8'))
    import sys

    sys.path.insert(0, str(site.PACKAGE.parent))
    from quas_atlas import api
    from quas_atlas import pages as _pages  # noqa: F401

    for name, params in recorded[topic][:2]:
        direct = json.dumps(api.to_json(api.call(name, json.loads(params))), ensure_ascii=False, allow_nan=False)
        assert bundle[name + '|' + params] == direct
    again = site.initial_answers(tmp_path / 'initial2', requests=few, kept=tmp_path / 'kept', log=lambda key: 1 / 0)
    assert again == made  # the second time nothing is counted
    import pytest

    bad = tmp_path / 'bad.json'
    bad.write_text(json.dumps({'../x': [['a', '{}']]}), encoding='utf-8')
    with pytest.raises(ValueError):  # a name of a topic becomes a name of a file
        site.initial_answers(tmp_path / 'initial3', requests=bad, kept=tmp_path / 'kept')


def test_a_topic_opens_without_python_and_the_service_worker_does_not_hold_answers_back(tmp_path):
    out, _ = _built(tmp_path)
    static = (out / 'atlas' / 'assets' / 'js' / 'qcstatic.js').read_text(encoding='utf-8')
    # health is answered by the page until Python failed; the kept answers are asked before Python
    assert "if (name === 'health' && !state.failed) return {status: 200, body: HEALTH};" in static
    assert '\\"static\\": true' in static and '__HEALTH__' not in static and '__RUNTIME__' not in static
    assert static.index('(await initial())[name + ') < static.index('return call(name, body);')
    assert "'../initial/' + topic + '.json'" in static
    # Python ahead of need: not on a phone, not with «save data»
    assert "matchMedia('(pointer:fine)').matches && !c.saveData" in static
    worker = (out / 'sw.js').read_text(encoding='utf-8')
    assert 'await cache.put(key(request.url), response.clone())' not in worker  # the answer waited for its copy
    assert 'event.waitUntil(caches.open(CACHE).then(cache => cache.put(key(request.url), copy))' in worker
    assert 'const WAIT = 4000;' in worker and 'Promise.race([fresh.catch(() => null), late])' in worker
    # what is kept for ever has its version or hash in the address; the pictures of the home page are not among it
    assert f'"atlas/assets/pyodide-{site.PYODIDE_VERSION}/"' in worker and '"img/"' not in worker
    assert 'woff2$' in worker and '"atlas/assets/fonts/"' not in worker
    # a slider: one request counted, the newest waiting
    client = (out / 'atlas' / 'assets' / 'js' / 'qcapi.js').read_text(encoding='utf-8')
    assert 'if (next) next.reject(STALE);' in client
    assert 'let seq = 0, busy = false, next = null;' in client
    program = (site.PACKAGE / 'web' / 'assets' / 'js' / 'qcapi.js').read_text(encoding='utf-8')
    assert 'busy = false, next = null' not in program  # the program's own file is left as it is


def test_the_topic_pages_get_what_a_phone_and_a_wide_screen_need(tmp_path):
    """On a phone the title keeps its lines, the table of results its right column, the numbers of the axes are
    readable and the section name does not hide the name of the topic; on a wide screen an explanation is not too
    wide. The styles and the
    script of the site are put into every topic page — after the page's own styles — and the Atlas of the program is
    left as it is."""
    out, _ = _built(tmp_path)
    style = (out / 'atlas' / 'assets' / 'css' / 'site-page.css').read_text(encoding='utf-8')
    script = (out / 'atlas' / 'assets' / 'js' / 'site-page.js').read_text(encoding='utf-8')
    for language in ('ru', 'en', 'zh'):
        pages = sorted((out / 'atlas' / language).glob('*.html'))
        assert len(pages) == 56
        for page in pages:
            text = page.read_text(encoding='utf-8')
            head = text[:text.index('</head>')]
            assert re.search(r'<link rel="stylesheet" href="\.\./assets/css/site-page\.css\?v=[0-9a-f]{10}">$', head.rstrip()), page.name
            assert head.count('site-page.css') == 1 and text.count('site-page.js') == 1
            assert text.index('qpose.css') < text.index('site-page.css')  # the later sheet is the one obeyed
    phone = style[style.index('@media (max-width:640px){'):]
    # Quill on the right of the title, not above it; the page's own display:flex is overruled
    assert '.qPoseH{padding-right:0;display:grid !important' in phone and '.qPose{position:static;grid-column:2' in phone
    assert '.tablewrap{overflow-x:auto' in phone and '.siteLong{white-space:normal' in phone
    assert 'main{max-width:1080px !important' in style  # one column in the middle (was: text at 86ch)
    assert "querySelectorAll('text[font-size]')" in script and 'FACTORS = [1.55, 1.4, 1.25, 1.12]' in script
    for language, words in (('ru', 'Перейти к модели'), ('en', 'Go to the model'), ('zh', '前往模型')):
        assert words in script
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert 'body.hasRail .secT{max-width:38vw' in rail
    source = site.PACKAGE / 'web'
    assert not any('site-page' in p.read_text(encoding='utf-8') for p in (source / 'ru').glob('*.html'))
    listed = json.loads((out / 'site-files.json').read_text(encoding='utf-8'))
    assert {'atlas/assets/css/site-page.css', 'atlas/assets/js/site-page.js'} <= set(listed['common'])  # kept offline


def test_the_atlas_shows_no_empty_controls_while_it_loads(tmp_path):
    """The language and the theme of the Atlas's header are never shown on the site (the side panel has them), and the
    row of the topics stands hidden until the page shows a topic."""
    out, _ = _built(tmp_path)
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    rule = '#langG,#themeB{display:none!important}'
    assert rule in shell and shell.index(rule) < shell.index('id="langG"')
    assert '<div class="secrow" id="secrow" hidden>' in shell


def test_no_light_page_before_a_dark_one(tmp_path):
    """In the dark theme no white page flashes while a slow connection loads the scripts. The theme is set before
    anything is drawn, the note waits, a topic page is dark before its sheets come,
    and no page waits for the sheet of the fonts."""
    out, _ = _built(tmp_path)
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    early = shell.index("localStorage.getItem('qc-theme')")
    assert early < shell.index('<style>') and early < shell.index('@font-face')  # before anything drawn
    assert early < shell.index('qcstatic.js')  # and before the scripts that are waited for
    # the theme of the program in the address (azimuth/site.py) comes first, then the one kept
    assert early > shell.index('[?&]theme=(light|dark)') > shell.index('</title>')
    home = (out / 'index.html').read_text(encoding='utf-8')
    assert home.index('[?&]theme=(light|dark)') < home.index("localStorage.getItem('qc-theme')") < home.index('<style>')
    assert f'#nojs{{animation:nojsLate 0s linear {site.NOJS_WAIT}s both}}' in shell and 'id="nojs"' in shell
    source = (site.PACKAGE / 'web' / 'index.html').read_text(encoding='utf-8')
    assert site.DARK in source  # the ground given early is the dark ground of the Atlas itself
    for page in list((out / 'atlas' / 'ru').glob('*.html')) + [out / '404.html']:
        text = page.read_text(encoding='utf-8')
        assert 'fonts.css" media="print" onload="this.media=\'all\'"' in text, page.name
        assert text.count('fonts.css') == 2  # the link and its copy for a browser without scripts
    for page in (out / 'atlas' / 'index.html', out / 'index.html'):  # the faces in the page (fonts_inline)
        assert 'fonts.css' not in page.read_text(encoding='utf-8') and '@font-face' in page.read_text(encoding='utf-8')
    topic = (out / 'atlas' / 'ru' / 'postulates.html').read_text(encoding='utf-8')
    tag = '<script src="../assets/js/theme-early.js"></script>'
    after = topic[topic.index(tag) + len(tag):]
    assert after.startswith("<script>(function(){var R=document.documentElement") and site.DARK in after[:400]
    assert "R.style.backgroundColor=''" in after[:600]  # given back to the sheets when they are there
    import pytest

    with pytest.raises(ValueError):
        site.fonts_aside('<p>no link</p>')


def test_the_side_panel_stays_narrow(tmp_path):
    """The left panel stays narrow under the pointer. The names of its icons stand beside them instead, and are said to a screen reader."""
    out, _ = _built(tmp_path)
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert '196px' not in rail and 'width:176px' not in rail
    assert '--rail-w:68px' in rail and '#siteRail:hover{' not in rail and '#siteRail:hover,' not in rail
    assert 'content:attr(data-tip)' in rail and "e.dataset.tip = e.title; e.setAttribute('aria-label', e.title); e.removeAttribute('title')" in rail
    assert 'pointer-events:none' in rail[rail.index('content:attr(data-tip)'):rail.index('content:attr(data-tip)') + 500]


def test_the_page_about_the_program_is_gone(tmp_path):
    """(program/) told of every section with pictures of the program in
    both themes; the panels of the parts on the home page tell the same, so the page goes. The
    panels hold all the page held of the sections; the address program/ leads to the part «Программа» of the home
    page; the side panel and the buttons lead there; no picture is unused, none named is missing."""
    import json
    import re

    out, _ = _built(tmp_path)
    assert not (site.ROOT / 'site' / 'program.html').exists()
    gone = (out / 'program' / 'index.html').read_text(encoding='utf-8')
    assert 'content="noindex"' in gone and "location.replace('../' + location.search + '#program')" in gone
    assert 'url=../#program' in gone and '<link rel="canonical" href="https://www.azimuth-chem.com/">' in gone
    home = (out / 'index.html').read_text(encoding='utf-8')
    texts = json.loads((site.ROOT / 'site' / 'texts.json').read_text(encoding='utf-8'))
    for key in ('gC1a', 'gC2d', 'gSs1', 'gPd', 'gShots'):
        assert texts['ru'][key] in home  # the text stands in the HTML, not only in the script
    keys = {k for k in texts['ru'] if k.startswith('g')}
    assert len(keys) > 30 and all(keys <= set(texts[lang]) for lang in ('en', 'zh'))  # nothing left untranslated
    shown = set(re.findall(r'src="img/program/([a-z-]+)-(light|dark)\.webp"', home))
    names = {name for name, _ in shown}
    # 13 pictures (scan, hydrogen bonds, Hirshfeld, fingerprint, powder, crystal in Sextant added) — the
    # number is the one of the marks <!--SHOT …--> of site/index.html
    marked = set(re.findall(r'<!--SHOT ([a-z-]+) ', (site.ROOT / 'site' / 'index.html').read_text(encoding='utf-8')))
    assert len(names) == len(marked) >= 7 and names == marked
    assert shown == {(name, theme) for name in names for theme in ('light', 'dark')}
    # no picture unused: the Russian ones of the page and those of the other languages it names (data-langs)
    own = {(name, lang) for name, langs in re.findall(r'data-shot="([a-z-]+)" data-langs="([a-z ]*)"', home)
           for lang in langs.split()}
    assert {p.name for p in (out / 'img' / 'program').iterdir()} == (
        {f'{n}-{t}.webp' for n, t in shown} | {f'{n}-{l}-{t}.webp' for n, l in own for t in ('light', 'dark')})
    for name, theme in shown:
        assert (out / 'img' / 'program' / f'{name}-{theme}.webp').stat().st_size > 10_000
    assert ':root[data-theme="dark"] .shot .lt{display:none}' in home
    assert 'id="aboutProgram" href="#program"' in home and 'moreProgram' not in home and 'program/?lang' not in home
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert "['program', home + '#program']" in rail and "'program/" not in rail
    assert "const PARTS = ['atlas', 'program', 'download', 'author']" in rail and 'PARTS.includes(h)' in rail
    import pytest

    lost = tmp_path / 'lost'
    (lost / 'img-program').mkdir(parents=True)
    with pytest.raises(ValueError):  # a picture named and not there
        site.program_pictures(lost, tmp_path / 'o', '<!--SHOT compass gC1s1-->')


def test_the_mobile_audit_of_2026_11_13(tmp_path):
    """The audit of the Atlas at 390 px (all 43 topics): «1,362 бор» a character a line (.kvt of the helium and of
    CASSCF), the names of «Проверка расчётов» 28 px wide, plots of 900–1100 units drawn 328 px wide with 5 px labels,
    the wavelengths of the hydrogen spectrum running together, the last tick of the Jahn–Teller plot cut. Measured in a
    browser after the fix: labels 9–12 px, the tallest cell 74 px (was 499). Here — that the means are in place."""
    out, _ = _built(tmp_path)
    style = (out / 'atlas' / 'assets' / 'css' / 'site-page.css').read_text(encoding='utf-8')
    phone = style[style.index('@media (max-width:640px){'):]
    for rule in ('main .kvt{grid-template-columns:minmax(0,1fr) !important', '.tablewrap td.l{min-width:9em}',
                 '#jtSvg{overflow:visible}', '.siteWide{overflow-x:auto'):
        assert rule in phone, rule
    script = (out / 'atlas' / 'assets' / 'js' / 'site-page.js').read_text(encoding='utf-8')
    assert 'var WIDE = 700, SHRINK = 0.6;' in script and "frame.className = 'siteWide'" in script
    assert "bands[i].querySelectorAll('.lb')" in script  # the wavelengths of .specw on rows


def test_the_cards_the_dial_and_the_letters(tmp_path):
    """The parts of the program on the home page carry the pictures of their sections from the
    background of the program; the sextant of the lower left corner is gone from the home page; the other cards have
    small line pictures; the dial goes up with the page, as in the program; «Запросить программу», «Сообщить о
    проблеме» (drafts of letters, nothing sent by a page) and «Проверено эталонами» → «Проверка расчётов»."""
    import re

    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    assert 'class="scale corner"' not in home and '.scale.dial{position:absolute;top:0;right:0}' in home
    arts = re.findall(r'<div class="(cardArt[^"]*)" aria-hidden="true"><svg', home)
    # the icon of the section from the program before each title, on the cards and on the panel
    for part in ('atlas', 'compass', 'sextant', 'spectrum'):
        nav = (ROOT / 'assets' / 'navigation' / f'{part}.svg').read_text(encoding='utf-8')
        path = re.search(r'<path d="([^"]+)"', nav).group(1)
        assert home.count(path) >= 2, part
    assert '<!--NAV' not in home and 'currentBrown' not in home and 'style="stroke:var(--gold)"' in home
    assert len(arts) == 4 and arts.count('cardArt mirror') == 4  # the spectrum too, cut by its corner now
    # the strengths of the window times CARD_STRENGTH 1.6; the strongest mark 0.32
    assert site.CARD_STRENGTH == 1.6 and 'stroke-opacity="0.32"' in home and 'stroke-opacity="0.50"' not in home
    assert home.count('class="cardIcon"') == 6 and '<!--ICON' not in home and '<!--ART' not in home  # 6: and Linux
    assert 'id="toValidation" href="atlas/#val"' in home and "'#val'" in home
    # the letter is made by the script only — the HTML holds no address (robots of spam)
    assert 'id="askProgram" href="#download"' in home and "'mailto:' + ADDRESS" in home
    assert 'encodeURIComponent(u.reqBody)' in home
    script = (out / 'atlas' / 'assets' / 'js' / 'site-page.js').read_text(encoding='utf-8')
    assert "a.href = 'mailto:' + MAIL" in script and 'function report()' in script and 'report();' in script
    for words in ('Сообщить о проблеме', 'Report a problem', '报告问题'):
        assert words in script
    import pytest

    with pytest.raises(ValueError):
        site.card_pictures('<!--ART castle-->')


def test_the_panels_of_the_parts(tmp_path):
    """The title of each of the four parts is a button, the panel holds a part for each with its
    pictures; the panel's names do not meet the Atlas's own .drawer (rail.js moves that one), so the panel is not
    pulled to the left."""
    import re

    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    buttons = re.findall(r'<div class="card part" data-part="([a-z]+)">.*?<button class="partBtn"', home)
    assert buttons == ['atlas', 'compass', 'sextant', 'spectrum']
    parts = re.findall(r'<div class="dpart" data-part="([a-z]+)" hidden>', home)
    assert parts == ['atlas', 'compass', 'sextant', 'spectrum']
    for part in parts[1:]:  # every section of the program has its pictures
        block = home[home.index(f'<div class="dpart" data-part="{part}"'):]
        assert '<figure class="shot">' in block[:block.index('</div>\n    <div class="dpart"') if part != 'spectrum' else None]
    assert '<!--SHOT' not in home and 'class="drawer' not in home and 'id="secPanel"' in home
    assert 'history.pushState' in home and 'class="secNote" data-t="gShots"' in home
    # the pictures are in the
    # language of the page — the note says only how to open one
    words = json.loads((site.ROOT / 'site' / 'texts.json').read_text(encoding='utf-8'))
    assert not any(w in words[lang]['gShots'] for lang in ('ru', 'en', 'zh') for w in ('русск', 'Russian', '俄'))


def test_the_wishes_of_2026_11_13_evening(tmp_path):
    """Under «МОЛЕКУЛА»), the card of
    Compass «Молекула / Кристалл»; the side panel goes to a part of the home page without loading it again, below the
    header, and lights the part read; the text of a part as wide as its cards; Quill's greeting of the program on
    the home page; in the Atlas larger arrows of the topics, a tip of Quill beside the side panel, «С чего начать» and
    «Продолжить» on the overview, the controls of a model beside its result on a wide screen."""
    import json

    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    texts = json.loads((site.ROOT / 'site' / 'texts.json').read_text(encoding='utf-8'))
    assert 'gC1T' not in texts['ru'] and texts['ru']['p2w'] == 'Молекула / Кристалл'
    assert '<h2 id="dh-compass"><svg class="navIcon"' in home and '<span data-t="p2T">' in home and '<h3 class="sub" data-t="gC2w">' in home
    assert 'section{scroll-margin-top:72px}' in home and 'max-width:44em' not in home
    assert 'class="hello"' in home and texts['ru']['qHello2'][:30] in home
    # then (the same evening) in the place of the lead of the first screen, told for the site; «lead» stays the
    # description of the page for the search engines
    hero = home[home.index('<div class="hero">'):home.index('<section id="atlas">')]
    assert 'class="hello"' in hero and 'data-t="lead"' not in home and texts['ru']['qHello2'].startswith('Это «Азимут»')  # «ни слова про Азимут» — now its first words
    assert f'<meta name="description" content="{texts["ru"]["lead"][:20]}' in home
    for lang in ('ru', 'en', 'zh'):
        assert '<b class="qa">QuAIL</b>' in texts[lang]['qHello1']
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert "scrollIntoView" in rail and 'const spy = () =>' in rail
    assert 'body.hasRail .pgB{width:38px;height:38px' in rail and 'body.hasRail .qtip.qtipL{left:calc(var(--rail-w) + 18px)}' in rail
    assert "const START = ['post', 'hat', 'scf', 'lad']" in rail and "store('qc-site-last', k)" in rail
    style = (out / 'atlas' / 'assets' / 'css' / 'site-page.css').read_text(encoding='utf-8')
    script = (out / 'atlas' / 'assets' / 'js' / 'site-page.js').read_text(encoding='utf-8')
    assert '.siteCtl,.siteRes{display:contents}' in style and 'main section.panel.siteSide{display:grid' in style
    assert 'function side()' in script and 'side();' in script and 'main [id]{scroll-margin-top:14px}' in style


def test_three_topics_on_the_home_page(tmp_path):
    """The design review §10 three real topics of the Atlas on the home page — a picture of
    each in every language and theme, the link to the topic; the build refuses a picture missing or left over."""
    import json

    import pytest

    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    assert len(re.findall(r'<a class="example" data-topic="([a-z0-9]+)" href="atlas/#\1">', home)) == 3
    # three of a pool, at random
    pool = re.findall(r"\['([a-z0-9]+)', '(ex\d+)'\]", home)
    assert [k for k, _ in pool] == ['pes', 'mo', 'sym', 'bo', 'nm', 'aim'] and 'Math.random()' in home
    index = (site.ROOT / 'modules' / 'atlas' / 'atlas_v2' / 'quas_atlas' / 'web' / 'index.html').read_text(encoding='utf-8')
    topics = set(re.findall(r"\{id:'([\w-]+)'", index))
    texts = json.loads((site.ROOT / 'site' / 'texts.json').read_text(encoding='utf-8'))
    for key, n in pool:
        assert key in topics and texts['ru'][n]
        for lang in ('ru', 'en', 'zh'):
            assert texts[lang][n] and texts[lang][n + 't']
            for theme in ('light', 'dark'):
                assert (out / 'img' / 'topics' / f'{key}-{lang}-{theme}.webp').stat().st_size > 5000
    assert "a.href = 'atlas/?lang=' + lang + '#' + a.dataset.topic" in home
    with pytest.raises(ValueError):
        site.topic_pictures(tmp_path / 'nothing', tmp_path / 'o', home)


def test_the_room_of_the_side_panel_is_kept_from_the_first_picture(tmp_path):
    """The pages with the panel keep its room (the padding rail.js gives) and a strip of its colours from their
    head, before rail.js has run; the strip goes when the panel has come."""
    out, _ = _built(tmp_path)
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert 'body.hasRail{padding-left:var(--rail-w)' in rail and '--rail-w:68px' in rail
    for name in ('index.html', '404.html', 'atlas/index.html'):
        page = (out / name).read_text(encoding='utf-8')
        head = page[:page.index('</title>') + 2000] if name == 'atlas/index.html' else page[:page.index('</head>')]
        assert site.RAIL_EARLY in head, name
        assert page.index(site.RAIL_EARLY) < re.search(r'<script src="[^"]*rail\.js', page).start(), name
    assert 'body{padding-left:68px' in site.RAIL_EARLY and 'padding-bottom:54px' in site.RAIL_EARLY
    assert 'body:not(.hasRail)::before' in site.RAIL_EARLY


def test_the_header_of_the_home_page_and_the_names_of_the_phone_bar(tmp_path):
    """The wordmark, the name of the place, «Открыть Атлас»; on a phone the name under the icon of the page shown only.
    No links to the parts in the header: the panel leads there, «Атлас» of the panel too goes to its part of the home
    page."""
    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    header = home[home.index('<header class="top">'):home.index('</header>')]
    assert 'class="tag" data-t="tag">Квантовая химия<' in header and 'id="openAtlas4"' in header
    assert '<a href="#' not in header and 'nav.links' not in home
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert "['atlas', HERE === 'home' ? home + '#atlas' : atlas]" in rail
    assert '#siteRail a[data-nav] span{display:none}' in rail
    assert '#siteRail a[data-nav][aria-current="page"] span{display:block' in rail


def test_the_press_of_a_button_is_seen(tmp_path):
    """On the home page and in the panel a
    button held sinks a little (the pages of the Atlas have it of their own, formula.css); no grey flash of a phone."""
    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    for rule in ('.btn:active{transform:scale(.96)', '.example:active{transform:scale(.98)', '.card.part:active{', '.langs button:active{'):
        assert rule in home
    assert '-webkit-tap-highlight-color:transparent' in home
    rail = (out / 'rail.js').read_text(encoding='utf-8')
    assert '#siteRail a:active svg,#siteRail button:active svg{transform:scale(.86)}' in rail
    assert '#siteRail a:active svg,#siteRail button:active svg{transform:none}' in rail  # not with fewer motions asked


def test_a_drawing_turned_is_not_selected_like_a_text(tmp_path):
    """Turning a molecule of the topic of symmetry does not select the picture as text."""
    out, _ = _built(tmp_path)
    css = (out / 'atlas' / 'assets' / 'css' / 'site-page.css').read_text(encoding='utf-8')
    assert 'svg,canvas{-webkit-user-select:none;user-select:none;-webkit-touch-callout:none}' in css
    js = (out / 'atlas' / 'assets' / 'js' / 'site-page.js').read_text(encoding='utf-8')
    assert "addEventListener('selectstart'" in js and "closest('svg,canvas')" in js
    topic = (out / 'atlas' / 'ru' / 'symmetry.html').read_text(encoding='utf-8')
    assert 'site-page.css' in topic and 'site-page.js' in topic


def test_the_home_page_has_an_address_in_every_language(tmp_path):
    # a search engine reads one language an address — the English and the Chinese home pages were made by
    # the script only; now / (ru), /en/ and /zh/ hold their own texts, name each other and stand in sitemap.xml
    import re

    out, _ = _built(tmp_path)
    texts = json.loads((ROOT / 'site' / 'texts.json').read_text(encoding='utf-8'))
    for lang, path, mark in (('ru', '', 'ru'), ('en', 'en/', 'en'), ('zh', 'zh/', 'zh-CN')):
        page = (out / path / 'index.html').read_text(encoding='utf-8')
        assert f'<html lang="{mark}">' in page and f'<h1 data-t="h1">{texts[lang]["h1"]}</h1>' in page
        assert f'<link rel="canonical" href="{site.SITE_URL}{path}">' in page
        for other in ('', 'en/', 'zh/'):
            assert f'href="{site.SITE_URL}{other}"' in page  # hreflang of all three
        if path:  # one folder down: every address of the site goes up, the side panel knows the language
            assert f'data-root="../" data-lang="{lang}"' in page and 'src="../img/quill-home-desk.webp"' in page
            assert not re.findall(r'(?:src|href)="(?:img|atlas)/', page) and "'../img/topics/'" in page
    sitemap = (out / 'sitemap.xml').read_text(encoding='utf-8')
    assert sitemap.count('<url>') > 100 and f'<loc>{site.SITE_URL}zh/</loc>' in sitemap
    assert f'<loc>{site.SITE_URL}atlas/en/h2.html</loc>' in sitemap
    assert f'Sitemap: {site.SITE_URL}sitemap.xml' in (out / 'robots.txt').read_text()
    rules = (out / '_redirects').read_text()
    assert '/en/:page /atlas/en/:page 301' in rules and '/en/*' not in rules  # /en/ itself is not sent to the Atlas


def test_the_download_part_names_linux(tmp_path):
    """Three cards — macOS, Windows, Linux (its icon a
    terminal), the text of Linux in the three languages, the letter of the request names it among the systems; each card
    has its button to the latest release of GitHub."""
    import json

    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    part = home[home.index('<section id="download">'):home.index('</section>', home.index('<section id="download">'))]
    assert [os for os in ('macOS', 'Windows', 'Linux') if f'<div class="os">{os}</div>' in part] == ['macOS', 'Windows', 'Linux']
    assert part.count('class="card"') == 3 and '<path d="M7 12l3 2.5L7 17"/>' in part and 'data-t="lin"' in part
    assert '.dl{display:grid;grid-template-columns:repeat(3,1fr)' in home
    texts = json.loads((Path(__file__).resolve().parents[2] / 'site' / 'texts.json').read_text(encoding='utf-8'))
    for lang in ('ru', 'en', 'zh'):
        assert 'Linux x86_64' in texts[lang]['lin'] and 'Ubuntu 22.04' in texts[lang]['lin']
        assert 'Linux x86_64' in texts[lang]['reqBody']
    # the files of the latest release under the names without the version, the same names the builds give them
    latest = 'https://github.com/coulombrepulsion/Azimuth-chem/releases/latest'
    assert f'href="{latest}/download/Azimuth-macOS-arm64.dmg"' in part and f'href="{latest}/download/Azimuth-Setup-Windows-x64.exe"' in part
    assert f'href="{latest}"' in part and 'class="soon"' not in part
    root = Path(__file__).resolve().parents[2] / '.github' / 'workflows'
    assert 'Azimuth-macOS-arm64.dmg' in (root / 'build-macos.yml').read_text(encoding='utf-8')
    assert 'Azimuth-Setup-Windows-x64.exe' in (root / 'build-windows.yml').read_text(encoding='utf-8')


def test_every_page_says_it_has_both_themes_at_its_first_line(tmp_path):
    """<meta name="color-scheme" content="light dark"> right after the charset of every page — the home
    page in its languages, the Atlas, its topics, the page «не найдено» — once."""
    out, _ = _built(tmp_path)
    pages = list(out.rglob('*.html'))
    assert len(pages) > 100
    for page in pages:
        text = page.read_text(encoding='utf-8')
        assert text.count('name="color-scheme"') == 1, page
        assert text.index(site.COLOR_SCHEME) < 400 and text.index(site.COLOR_SCHEME) > text.lower().index('<meta charset="utf-8">'), page
    assert site.color_scheme(out) == 0  # given once


def test_a_topic_opened_first_is_unseen_until_its_page_came(tmp_path):
    """A frame of a topic
    without data-ld (the index page sets it on «load») is hidden, FRAME_WAIT seconds at most."""
    out, _ = _built(tmp_path)
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    rule = '#stage iframe:not([data-ld]){animation:qcFrameLate 0s linear 1.5s both}'
    assert rule in shell and '@keyframes qcFrameLate{from{visibility:hidden}to{visibility:visible}}' in shell
    assert shell.index(rule) < shell.index('<main id="stage"')
    # the
    assert "f.addEventListener('load',()=>{try{if(f.contentWindow.location.href==='about:blank')return}catch(e){}f.dataset.ld='1'" in shell
    # mark the rule waits for the page of the topic is asked for when the index page has been read (after rail.js at its
    # end), the panel's script from the head
    assert "if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',go,{once:true});else go();" in shell
    assert shell.index('<header') < shell.index('<script data-root="../" data-here="atlas">') and 'src="../rail.js' not in shell
    # the scripts the page waited for come after it (defer), the empty quote is not shown
    assert '<script defer src="assets/js/qcstatic.js">' in shell and '<script defer src="assets/js/tips.js">' in shell
    assert '.qtag:empty,#qTag:empty{display:none!important}' in shell


def test_the_name_and_the_fonts_are_in_the_first_picture(tmp_path):
    """the home pages and the index page of the Atlas carry the @font-face rules of fonts.css (the files where the sheet
    has them) and the wordmark of the name as built; on a phone the header of the Atlas is small from the first picture
    (RAIL_EARLY, not when site/rail.js came)."""
    import re

    out, _ = _built(tmp_path)
    words = site.wordmarks(site.PACKAGE / 'web')
    faces = (site.PACKAGE / 'web' / 'assets' / 'fonts' / 'fonts.css').read_text(encoding='utf-8').count('@font-face')
    for path, lang, base in (('index.html', 'ru', 'atlas/assets/fonts/'), ('en/index.html', 'en', '../atlas/assets/fonts/'),
                             ('zh/index.html', 'zh', '../atlas/assets/fonts/'), ('atlas/index.html', 'ru', 'assets/fonts/')):
        page = (out / path).read_text(encoding='utf-8')
        head = page[:page.index('</head>')] if '</head>' in page else page[:page.index('<header')]
        assert head.count('@font-face') == faces and 'fonts.css' not in page, path
        files = [f for f in re.findall(r'url\(([^)]+)\)', head) if f.endswith('.woff2')]  # not the compass (data:)
        assert files and all(f.startswith(base) and (out / path).parent.joinpath(f).resolve().is_file() for f in files), path
        assert words[lang] in page, path
    home = (out / 'en' / 'index.html').read_text(encoding='utf-8')
    assert f'id="brand" aria-label="Azimuth">{words["en"]}</a>' in home
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    assert '<span class="q1 qBrand">Азимут</span>' not in shell and shell.count('<span class="q1 qBrand"><svg') >= 1
    phone = site.RAIL_EARLY[site.RAIL_EARLY.index('@media (max-width:700px)'):]
    assert '.qbrandH{zoom:.68}' in phone and '.qpart{display:none}' in phone and shell.index(site.RAIL_EARLY) < shell.index('<header')


def test_quill_of_the_atlas_stands_to_the_left_of_its_heading(tmp_path):
    """In the part «Атлас» of the home page her picture comes before the heading, in a column of 220 px on the left."""
    out, _ = _built(tmp_path)
    home = (out / 'index.html').read_text(encoding='utf-8')
    part = home[home.index('<section id="atlas">'):]
    head = part[part.index('<div class="partHead">'):part.index('<div class="atlas">')]
    assert head.index('class="partQuill"') < head.index('data-t="atlasT"')
    assert '.partHead{display:grid;grid-template-columns:220px 1fr;' in home


def test_the_titles_of_the_tabs_keep_the_name(tmp_path):
    """Safari hides what it takes for the site's name before a dash, a pipe or a colon; the titles part their words with
    « · », and each home page has the title of its own language in its HTML."""
    import json
    import re

    out, _ = _built(tmp_path)
    texts = json.loads((Path(__file__).resolve().parents[2] / 'site' / 'texts.json').read_text(encoding='utf-8'))
    names = {'ru': 'Азимут', 'en': 'Azimuth', 'zh': '方位'}
    for path, lang in (('index.html', 'ru'), ('en/index.html', 'en'), ('zh/index.html', 'zh')):
        page = (out / path).read_text(encoding='utf-8')
        # the third screenshot: «Азимут · квантовая химия» too was cut — the tab has the name alone
        assert re.findall(r'<title>([^<]*)</title>', page) == [names[lang]] == [texts[lang]['title']], path
        assert f'<meta property="og:title" content="{texts[lang]["ogTitle"]}">' in page and site.TITLE_SEPARATOR in texts[lang]['ogTitle']
    for name in ('apple-touch-icon.png', 'apple-touch-icon-precomposed.png'):  # Safari asks for them by itself
        assert (out / name).read_bytes() == (site.APP_ICON / 'azimuth-256.png').read_bytes()
    titles = [t for page in (out / 'index.html', out / 'en' / 'index.html', out / '404.html', out / 'atlas' / 'index.html')
              for t in re.findall(r"<title>([^<]*)</title>|title: ?'([^']*)'", page.read_text(encoding='utf-8')) for t in t if t]
    titles += [texts[lang]['ogTitle'] for lang in texts]
    named = [t for t in titles if any(n in t for n in ('Азимут', 'Azimuth', '方位'))]
    assert len(named) >= 9 and all(site.TITLE_SEPARATOR in t or t in names.values() for t in named), named
    assert not any(sep in t for t in named for sep in (' — ', ' – ', ' - ', ' | ', ': ')), named
    # the second screenshot: with og:site_name Safari hid «Азимут · » as well — no page names the site there
    assert not [p for p in out.rglob('*.html') if 'og:site_name' in p.read_text(encoding='utf-8')]


def test_the_site_waits_with_the_compass_of_the_program(tmp_path):
    """The compass of azimuth/controls.py — the needle turning, the golden arc filling over one turn and emptying over
    the next — in the place of a topic while it comes, in «Загружаются расчёты…» and in «Считаю…»."""
    out, _ = _built(tmp_path)
    shell = (out / 'atlas' / 'index.html').read_text(encoding='utf-8')
    # the big compass of the place of a topic is in the page itself — not two pictures, the arc in the one with a clock
    # of its own — and shown while the topic comes; its colours of both themes are its own (the page's are not there
    # yet)
    import re

    assert shell.count(site.STAGE_COMPASS_HTML) == 1 and '<main id="stage">' + site.STAGE_COMPASS_HTML in shell
    assert site.STAGE_LIVE + '{display:inline-block' in shell and 'data:image/svg+xml' not in site.STAGE_COMPASS
    for theme in ('light', 'dark'):
        assert site.COMPASS_COLOURS[theme]['arc'] in site.STAGE_COMPASS
    assert ':root[data-theme="dark"] .qcStage .a{' in site.STAGE_COMPASS
    assert '<svg class="qcN"' in site.COMPASS_SVG and '<svg class="qcD"' in site.COMPASS_SVG
    static = (out / 'atlas' / 'assets' / 'js' / 'qcstatic.js').read_text(encoding='utf-8')
    assert "note.innerHTML = '" + site.COMPASS_SVG + "<span></span>'" in static and '__COMPASS' not in static
    client = (out / 'atlas' / 'assets' / 'js' / 'qcapi.js').read_text(encoding='utf-8')
    assert "note.innerHTML = '" + site.COMPASS_SVG + "<span></span>'" in client and "'<i></i>" not in client
    assert '.qcCompass .qcN{' in site.COMPASS_PAGE_CSS
    # 2026-11-16 «таким же, как на иконке»: the lines of the icon (azimuth.compass_glyph) — glyph-small.svg for the
    # small compass (the four divisions of the cardinal points), glyph.svg for the big one (72, the dotted meridian)
    assert site.COMPASS_SVG.count('class="d"') == 4 and 'stroke-width="28"' in site.COMPASS_SVG  # the ring of the small
    full = site.compass_svg('full')
    assert full.count('class="d"') == 73 and 'stroke-dasharray="4 22"' in full and 'stroke-width="12"' in full
    assert 'A215 215 0 0 0 0 215" stroke-width="22"' in full and 'A200 200 0 0 0 0 200" stroke-width="44"' in site.COMPASS_SVG
    assert 'M0 -300L58 0H-58Z' in site.COMPASS_SVG and 'M0 -300L36 0H-36Z' in site.compass_needle('full')  # the needles
    assert '#c9962e' not in full and 'star' not in site.COMPASS_SVG  # no star
    # every moving part is turned (a transform: the compositor turns it while the page is busy), the two halves of the
    # arc and the needle by keyframes at the same moments of the cycle — the arc cannot run ahead of the needle
    assert full.count('class="qcH') == 2 and 'stroke-dasharray:' not in site.COMPASS_PAGE_CSS
    frames = {part: re.findall(r'([\d.]+)%\{transform:rotate\((-?[\d.]+)deg\)\}',
                               re.search(r'@keyframes qcCmp' + part + r'\{(.*?\})\}', site.COMPASS_KEYS).group(1))
              for part in 'NRL'}
    assert [m for m, _ in frames['N']] == [m for m, _ in frames['R']] == [m for m, _ in frames['L']]
    for (_, n), (_, r), (_, left) in zip(frames['N'], frames['R'], frames['L']):
        a = float(n)
        # the arc that the halves show (compass_halves): from the north to R in the right window, from the south to
        # 180 + L in the left one — on the first turn it is [0, needle], on the second [needle − 360, 360]
        shown = (max(0.0, float(r) - 180), min(180.0, float(r))), (max(180.0, float(left) + 180), min(360.0, float(left) + 360))
        start, stop = (0.0, a) if a <= 360 else (a - 360, 360.0)
        covered = [(lo, hi) for lo, hi in shown if hi - lo > 0.01]
        assert abs(sum(hi - lo for lo, hi in covered) - (stop - start)) < 0.05, (a, shown)
        assert not covered or (abs(covered[0][0] - start) < 0.05 and abs(covered[-1][1] - stop) < 0.05), (a, shown)
    # 2026-11-15 «с инерцией»: the motion of the program's compass — the same turn, rest and easing
    from azimuth import controls

    assert (site.COMPASS_TURN, site.COMPASS_PAUSE, site.COMPASS_EASE) == (controls.TURN, controls.PAUSE, controls.EASE)
    stop = f'{100 * controls.TURN / (2 * (controls.TURN + controls.PAUSE)):.3f}%'
    assert f'{stop}{{transform:rotate(360.00deg)}}' in site.COMPASS_KEYS and 'rotate(720.00deg)' in site.COMPASS_KEYS
    eased = [float(v) for _, v in frames['N'][:site.COMPASS_STEPS + 1]]
    assert eased[1] < 1 and eased[site.COMPASS_STEPS // 2] == pytest.approx(360 * site._bezier(0.5, *controls.EASE), abs=0.01)


def test_every_line_that_calculates_gets_the_compass(tmp_path):
    """The big compass with half as thick
    lines; site-page.js of every topic puts the compass before a line that says it is calculating («Считаю…», «Строю
    карту…», «Computing…», «正在计算…») and takes it away with the words."""
    import re

    out, _ = _built(tmp_path)
    page = (out / 'atlas' / 'assets' / 'js' / 'site-page.js').read_text(encoding='utf-8')
    assert "var COMPASS = '" + site.COMPASS_SVG + "'" in page and '__COMPASS' not in page
    waiting = re.compile(re.search(r"var WAITING = /(.*)/;", page).group(1).replace('\\s\\S', '\\s\\S'))
    for text in ('Считаю волновую функцию…', 'Строю карту и траектории…', 'Считаю H₂O, STO-3G (MP2, диполь, заряды)…',
                 'Computing vibrations…', 'Calculating…', '正在计算振动…', '正在绘制图和轨迹…'):
        assert waiting.search(text), text
    for text in ('Считаю', 'Это просто подсказка.', '…', 'Готово: 3 частоты.'):
        assert not waiting.search(text), text


def test_a_topic_is_one_column_in_the_middle_of_a_wide_screen(tmp_path):
    """On a wide screen the topic is one column 1080 px wide (the width of the home page) in the middle;
    its text has no narrower measure of its own, so the text, the fields and the notes share the edges."""
    out, _ = _built(tmp_path)
    css = (out / 'atlas' / 'assets' / 'css' / 'site-page.css').read_text(encoding='utf-8')
    wide = css[css.index('@media (min-width:1100px){'):]
    wide = wide[:wide.index('\n}') + 2]
    assert 'main{max-width:1080px !important;margin-left:auto !important;margin-right:auto !important}' in wide
    assert 'max-width:none' in wide and 'max-width:86ch' not in css and 'max-width:46em' not in css
    home = (out / 'index.html').read_text(encoding='utf-8')
    assert '.wrap{max-width:1080px;' in home  # the same width as the home page


def test_the_controls_take_the_theme_chosen_on_the_site():
    """With a theme chosen the
    controls of the browser take it, not the system's."""
    css = (Path(__file__).resolve().parents[2] / 'site' / 'atlas-page.css').read_text(encoding='utf-8')
    assert ':root[data-theme="light"]{color-scheme:light}' in css and ':root[data-theme="dark"]{color-scheme:dark}' in css


def test_the_package_zip_is_the_same_for_the_same_files():
    """Quas_atlas.zip was new at every build (the
    time of the build in it) and so sent to the mirror each time; the same files now give the same bytes."""
    import io
    import time

    first = site.package_zip()
    time.sleep(2.1)  # the time of a zip entry is counted in two seconds
    assert site.package_zip() == first
    with zipfile.ZipFile(io.BytesIO(first)) as archive:
        names = archive.namelist()
        assert 'atlas_site_entry.py' in names and any(n.startswith('quas_atlas/') for n in names)
        assert archive.testzip() is None


def test_the_pictures_of_the_sections_in_each_language(tmp_path):
    # name-LANG-THEME.webp beside the Russian name-THEME.webp;
    # a section without them shows the Russian ones in every language
    import pytest

    folder = tmp_path / 'img-program'
    folder.mkdir()
    for name in ('compass-light', 'compass-dark', 'spectrum-light', 'spectrum-dark',
                 'compass-en-light', 'compass-en-dark', 'compass-zh-light', 'compass-zh-dark'):
        (folder / f'{name}.webp').write_bytes(b'x')
    langs = site.shot_languages(tmp_path)
    assert langs == {'compass': ['en', 'zh']}
    home = '<p><!--SHOT compass cap1--></p><p><!--SHOT spectrum cap2--></p>'
    page = site.shot_figures(home, 'img/program/', langs)
    assert 'data-shot="compass" data-langs="en zh"' in page and 'data-shot="spectrum" data-langs=""' in page
    assert site.shot_language(page, 'ru') == page
    en = site.shot_language(page, 'en')
    assert 'src="img/program/compass-en-light.webp"' in en and 'src="img/program/compass-en-dark.webp"' in en
    assert 'src="img/program/spectrum-light.webp"' in en and 'spectrum-en' not in en  # none of its own: the Russian
    out = tmp_path / 'out'
    site.program_pictures(tmp_path, out, home)
    assert sorted(p.name for p in (out / 'img' / 'program').iterdir()) == sorted(p.name for p in folder.iterdir())
    (folder / 'spectrum-zh-light.webp').write_bytes(b'x')  # one theme only: the folder and the page differ
    with pytest.raises(ValueError):
        site.program_pictures(tmp_path, out, home)
    # the page changes them with the language, and opens the one shown
    template = (ROOT / 'site' / 'index.html').read_text(encoding='utf-8')
    assert "(a.dataset.langs || '').split(' ').includes(lang)" in template
    assert "a.href = seen(a).getAttribute('src')" in template


def test_the_pictures_of_the_program_are_taken_in_a_language():
    # tools/site_screenshots.py --lang en|zh — the program in that language, the pictures NAME-LANG-THEME
    # (those shot_languages takes); Russian keeps NAME-THEME. The window itself is made only on the Mac (in the VM
    # HubWindow fails on its menus), so the words of the script are checked here.
    text = (ROOT / 'tools' / 'site_screenshots.py').read_text(encoding='utf-8')
    assert "parser.add_argument('--lang', choices=['ru', 'en', 'zh'], default='ru'" in text
    assert "suffix = '' if args.lang == 'ru' else '-' + args.lang" in text
    assert "f'{name}{suffix}-{theme}.webp'" in text and "f'{name}{suffix}-{theme}.png'" in text
    assert "preferences.setValue('hub_language', args.lang)" in text and 'hub.set_language(args.lang)' in text
    assert site.SHOT_LANGS == ('en', 'zh')


def test_a_picture_of_a_section_opens_on_the_page(tmp_path):
    # the picture in full size over the page (#shotView) — closed by ×, Esc, a press beside it or «назад», the arrows
    # through the pictures of the section; with Ctrl/⌘/Shift/the middle button it is still a link to a new tab. Checked
    # in a browser too (the scratch harness of the session: open, →, Esc, back, back — no new tab).
    import json

    out, _ = _built(tmp_path)
    for page in (out / 'index.html', out / 'en' / 'index.html', out / 'zh' / 'index.html'):
        home = page.read_text(encoding='utf-8')
        for part in ('id="shotView" role="dialog" aria-modal="true"', 'id="shotClose"', 'id="shotPrev"', 'id="shotNext"',
                     'id="shotImg"', 'id="shotCap"', '.shotView.open{', 'history.pushState({drawer: shown, shot: a.dataset.shot}',
                     "if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey || e.button !== 0) return;",
                     "e.key === 'ArrowLeft'", "e.key === 'Escape'",
                     # the flight from the small picture and back (FLIP), to the one shown last, the panel scrolled to it
                     'big.animate(frames', "prefers-reduced-motion: reduce", 'if (last && last !== from)',
                     'body.scrollTop += ', 'figure.shot a.flying img{visibility:hidden}'):
            assert part in home, (page, part)
    texts = json.loads((ROOT / 'site' / 'texts.json').read_text(encoding='utf-8'))
    for lang in ('ru', 'en', 'zh'):
        assert texts[lang]['dPrev'] and texts[lang]['dNext'] and texts[lang]['dPrev'] != texts[lang]['dNext']

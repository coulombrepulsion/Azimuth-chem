"""The local server of the Atlas package (quas_atlas/server.py); no Qt, no display.

Modules/atlas/service.py, which started it for the window of the program, went with the Atlas of the window
(the Atlas is on the site); the server of the package stays — the author's local run of the Atlas and the
models answer here as they do in the browser of the site (Pyodide).

Oracles: the bundled files on disk (served page = file), the version string written in
the bundled package, the Bohr formula with the reduced mass E_n = -R_M hc Z^2 / n^2,
R_M = R_inf / (1 + m_e/M) from CODATA 2018 (Atlas 2.10.0).
"""

import json
import re
import urllib.request

import pytest

from modules.atlas.paths import ATLAS_ENTRY, ATLAS_HOME

# local requests must not go through a system proxy
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def get(url):
    with OPENER.open(url, timeout=60) as r:
        return r.status, r.headers.get('Content-Type', ''), r.read()


def post(url, payload):
    request = urllib.request.Request(url, json.dumps(payload).encode(), {'Content-Type': 'application/json'})
    with OPENER.open(request, timeout=60) as r:
        return json.loads(r.read())


@pytest.fixture
def base():
    import sys
    import threading

    if str(ATLAS_HOME) not in sys.path:
        sys.path.insert(0, str(ATLAS_HOME))
    from quas_atlas.server import make_server

    server = make_server('127.0.0.1', 0, preload=False)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f'http://127.0.0.1:{server.server_address[1]}/'
    server.shutdown()
    server.server_close()


def test_hub_page_is_the_bundled_file(base):
    status, ctype, body = get(base)
    assert status == 200 and ctype.startswith('text/html')
    assert body == ATLAS_ENTRY.read_bytes()


def test_health_reports_bundled_version(base):
    text = (ATLAS_HOME / 'quas_atlas' / '__init__.py').read_text(encoding='utf-8')
    expected = re.search(r'__version__\s*=\s*"([^"]+)"', text).group(1)
    status, _, body = get(base + 'api/health')
    assert status == 200 and json.loads(body) == {'ok': True, 'version': expected}


R_INF_CM = 109737.31568160  # cm^-1, CODATA 2018
EV_PER_CM = 1.239841984e-4
NUCLEUS_ME = {1: 1836.15267343, 2: 7294.29954142, 3: 12786.393}  # p, 4He, 7Li nuclei / m_e


@pytest.mark.parametrize('Z', [1, 2, 3])
def test_calculation_matches_bohr_levels(base, Z):
    levels = post(base + 'api/h.levels', {'Z': Z, 'series': 1})['lev']
    assert len(levels) >= 5
    ry = R_INF_CM / (1 + 1 / NUCLEUS_ME[Z]) * EV_PER_CM
    for n, energy in enumerate(levels, start=1):
        assert energy == pytest.approx(-ry * Z * Z / n**2, rel=1e-7)


def test_a_port_in_use_is_never_shared(base):
    # on Windows SO_REUSEADDR let a second server bind the port of the first (the open window of Azimuth and
    # the tests: a request was reset); the second one takes the next port, on every system
    from urllib.parse import urlsplit

    from quas_atlas.server import make_server

    used = urlsplit(base).port
    other = make_server('127.0.0.1', used, 5)
    try:
        assert other.server_address[1] != used
    finally:
        other.server_close()


def test_the_server_is_made_without_waiting_for_the_endpoints():
    # 0.109.2/0.109.3: the window of Azimuth starts the server while it builds itself; importing the server and binding
    # its port do not import the endpoints (numpy and the models, ~0.25 s; with preload=False not even in a thread); the
    # first request imports them. A fresh interpreter: in this one
    # the endpoints may be imported already.
    import subprocess
    import sys

    probe = (
        'import sys, threading, json, urllib.request\n'
        f'sys.path.insert(0, {str(ATLAS_HOME)!r})\n'
        'from quas_atlas import server\n'
        'before = "quas_atlas.pages" in sys.modules\n'
        'srv = server.make_server("127.0.0.1", 0, preload=False)\n'
        'made = "quas_atlas.pages" in sys.modules\n'
        'threading.Thread(target=srv.serve_forever, daemon=True).start()\n'
        'opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))\n'
        'url = "http://127.0.0.1:%d/api/au.constants" % srv.server_address[1]\n'
        'answer = opener.open(urllib.request.Request(url, b"{}", {"Content-Type": "application/json"}), timeout=60)\n'
        'print(json.dumps([before, made, answer.status, "quas_atlas.pages" in sys.modules]))\n'
        'srv.shutdown()\n'
    )
    run = subprocess.run([sys.executable, '-c', probe], capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-2000:]
    assert json.loads(run.stdout.strip().splitlines()[-1]) == [False, False, 200, True]

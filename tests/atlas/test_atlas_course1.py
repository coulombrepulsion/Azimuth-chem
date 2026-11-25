"""Atlas additions for the first course: SALCs (core.salc), Koopmans' theorem (core.koopmans), Walsh
diagrams (core.walsh), conceptual-DFT indices and Fukui functions (core.reactivity), semi-empirical integral counts
(core.semiemp); no Qt, no browser.

Oracles: textbook decompositions of ligand σ orbitals (Cotton, «Chemical Applications of Group Theory»); the
orthogonality of the character tables; Szabo–Ostlund, H₂/STO-3G at R = 1.4 bohr: ε₁ = −0.578 E_h, E(RHF) = −1.1167,
E(full CI) = −1.1373; Brillouin's theorem; BeH₂ linear and H₂O bent (experiment); χ(F) = (I + A)/2 with NIST I, A;
Σf = 1; Hückel f± equal to the frontier densities; the integral count M(M + 1)/2, M = N(N + 1)/2.
"""

import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import koopmans, reactivity, salc, semiemp, walsh  # noqa: E402


@pytest.mark.parametrize('key, expected', [
    ('h2o', {'A₁': 1, 'B₂': 1}), ('nh3', {'A₁': 1, 'E': 1}), ('bf3', {'A₁′': 1, 'E′': 1}), ('ch4', {'A₁': 1, 'T₂': 1}),
    ('ptcl4', {'A₁g': 1, 'B₁g': 1, 'Eu': 1}), ('sf6', {'A₁g': 1, 'Eg': 1, 'T₁u': 1})])
def test_salc_decompositions_and_orthonormal_combinations(key, expected):
    r = salc.salc(key)
    assert {x['irrep']: x['n'] for x in r['reduce'] if x['n']} == expected
    assert sum(c['g'] for c in r['classes']) == r['h'] and r['h'] == {4: 4, 6: 6, 12: 12, 24: 24, 16: 16, 48: 48}[r['h']]
    g = [c['g'] for c in r['classes']]
    for i, (_, _, a) in enumerate(r['table']):  # Σ g χ_i χ_j = h δ_ij
        for j, (_, _, b) in enumerate(r['table']):
            assert sum(w * x * y for w, x, y in zip(g, a, b)) == (r['h'] if i == j else 0)
    vecs = [s['c'] for s in r['salc']]
    assert len(vecs) == r['ligands']
    for i, u in enumerate(vecs):
        for j, v in enumerate(vecs):
            assert sum(a * b for a, b in zip(u, v)) == pytest.approx(1.0 if i == j else 0.0, abs=1e-12)


def test_koopmans_h2_and_heh():
    h = koopmans.koopmans('H2', 1.4, 1.24, 1.24)
    assert h['eps'][0] == pytest.approx(-0.578, abs=5e-4) and h['E_rhf'] == pytest.approx(-1.1167, abs=1e-4)
    assert h['E_fci'] == pytest.approx(-1.1373, abs=1e-4) and h['brillouin'] == pytest.approx(0.0, abs=1e-9)
    assert h['ip_dscf'] == pytest.approx(h['ip_koop'], abs=1e-9) and h['ip_fci'] > h['ip_koop']  # symmetry: no relaxation
    x = koopmans.koopmans('HeH', 1.4632, 2.0925, 1.24)
    assert x['relax'] > 0.03 and x['corr'] > 0.01 and x['ip_dscf'] < x['ip_fci'] < x['ip_koop']


def test_walsh_shapes():
    assert walsh.diagram(4)['best'] == pytest.approx(180, abs=1)
    assert 125 < walsh.diagram(5)['best'] < 140 and 95 < walsh.diagram(8)['best'] < 110
    d = walsh.diagram(8)['orbitals']
    assert d['2a1'][0] < d['2a1'][-1] and d['1b2'][0] > d['1b2'][-1]  # 2a1 drops, 1b2 rises on bending
    assert max(d['1b1']) - min(d['1b1']) < 1e-9 and d['2a1'][-1] == pytest.approx(d['1b1'][-1], abs=1e-9)


def test_reactivity_indices_and_fukui():
    f = reactivity.global_(17.423, 3.401)
    assert f['chi'] == pytest.approx(10.412) and f['eta'] == pytest.approx(7.011) and f['omega'] == pytest.approx(10.412**2 / 14.022)
    r = reactivity.fukui(['C', 'C', 'C', 'C'], [[0, 1], [1, 2], [2, 3]])
    assert sum(r['fplus']) == pytest.approx(1) and sum(r['fminus']) == pytest.approx(1)
    assert r['fplus'] == pytest.approx(r['fL']) and r['fminus'] == pytest.approx(r['fH']) and r['fminus'][0] > r['fminus'][1]
    a = reactivity.fukui(['C', 'C', 'C', 'O1'], [[0, 1], [1, 2], [2, 3]])
    assert max(range(4), key=lambda k: a['fplus'][k]) == 0  # acrolein: the β carbon
    with pytest.raises(ValueError):
        reactivity.global_(3.0, 5.0)


def test_semiempirical_counts():
    c = semiemp.count(6, 6)
    N = 36
    M = N * (N + 1) // 2
    assert c['N_sto3g'] == N and c['ab_sto3g'] == M * (M + 1) // 2 and c['N_val'] == 30
    assert c['cndo'] == 78 and c['nddo'] < c['ab_sto3g'] / 50
    # the example «a protein, 1000 heavy atoms» of «Hückel» asked 1000 and the server refused it
    assert api.call('semi.count', {'n': 1000, 'm': 1000})['N_val'] > c['N_val']
    with pytest.raises(api.ApiError):
        api.call('semi.count', {'n': 6000, 'm': 0})


def test_course1_endpoints():
    assert api.call('sym.salc', {'key': 'ch4'})['group'] == 'Td'
    assert api.call('walsh.diagram', {'ne': 4})['best'] == pytest.approx(180, abs=1)
    assert api.call('scf.koopmans', {'mol': 'H2', 'R': 1.4, 'za': 1.24, 'zb': 1.24})['ip_koop'] == pytest.approx(0.578, abs=5e-4)
    with pytest.raises(api.ApiError):
        api.call('sym.salc', {'key': 'xx'})
    with pytest.raises(api.ApiError):
        api.call('walsh.diagram', {'ne': 9})


def test_server_keeps_a_deep_queue_of_connections():
    # a topic page asks for 20-30 files at once; with socketserver's queue of 5 macOS refused some of them
    # («QC is not defined», page without styles and Quill's picture)
    import concurrent.futures
    import urllib.request

    from quas_atlas import server

    assert server.Server.request_queue_size >= 64
    srv, base = server.start_background(0)
    try:
        files = ['/ru/symmetry.html', '/assets/js/qcapi.js', '/assets/css/formula.css', '/assets/css/qpose.css',
                 '/assets/img/quill-20261023-sym-g.webp', '/ru/js/symmetry.js'] * 10
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

        def get(path):
            with opener.open(base + path, timeout=20) as answer:
                return answer.status, len(answer.read())

        with concurrent.futures.ThreadPoolExecutor(60) as pool:
            results = list(pool.map(get, files))
        assert all(status == 200 and size > 0 for status, size in results)
    finally:
        srv.shutdown()
        srv.server_close()


def test_slow_endpoints_answer_from_memory():
    # a slow deterministic endpoint is computed once; the copy given out can be changed without harm
    assert api.REGISTRY['h2.scan'].memo and not api.REGISTRY['sym.salc'].memo
    first = api.call('h2.scan', {})
    first['spoiled'] = True
    again = api.call('h2.scan', {})
    assert 'spoiled' not in again and again == {k: v for k, v in first.items() if k != 'spoiled'}

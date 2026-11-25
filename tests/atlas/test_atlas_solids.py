"""The Atlas topics on the Bloch theorem and k-points (bloch.html), on bands and the density of states (bands.html) and on
the properties of crystals (solidprops.html): the model quas_atlas.core.solids and its endpoints; no Qt, no browser.

Oracles: the vectors of the smooth and of the dense grid Quantum ESPRESSO 7.6 printed for the Si cell of
tests/data/qe/si_bands.in (5985 at 4·30 = 120 Ry, 16889 at 240 Ry, si_bands_pw76.out) and its cell volume 270.2564 bohr³;
the exact band energy of a half-filled chain −4|β|/π; graphene ±3|β| at Γ, ±|β| at M, 0 at K; the gap of a two-atom chain
2·sqrt(Δ²/4 + (β1 − β2)²); first-order perturbation theory of nearly free electrons (gap → 2|V|); the irreducible points
of the 4 × 4 mesh of a square counted by hand (3 shifted, 6 with Γ); the Birch–Murnaghan energy is a cubic in V^(−2/3),
so exact points give back V0, B0, B0′; the band edges of a two-atom chain sqrt(2C/m) and sqrt(2C(1/m1 + 1/m2)); the limits
of the Debye model (Dulong–Petit, (4π⁴/5)(T/θ)³) and of the Einstein model.
"""

import math
import re
import sys
from pathlib import Path

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import solids  # noqa: E402

QE = Path(__file__).parents[1] / 'data' / 'qe'


def test_plane_waves_of_silicon_are_those_of_quantum_espresso():
    text = (QE / 'si_bands_pw76.out').read_text(encoding='utf-8')
    smooth = int(re.search(r'Smooth grid:\s+(\d+) G-vectors', text).group(1))
    dense = int(re.search(r'Dense  grid:\s+(\d+) G-vectors', text).group(1))
    volume = float(re.search(r'unit-cell volume\s+=\s+([\d.]+)', text).group(1))
    rows = re.search(r'CELL_PARAMETERS angstrom\n(.*?)\nATOMIC', (QE / 'si_bands.in').read_text(), re.S).group(1)
    cell = [[float(x) for x in line.split()] for line in rows.splitlines()]
    assert cell == solids.CELLS['si']
    p = solids.plane_waves(cell, 30)
    assert p['V'] == pytest.approx(volume, abs=1e-3)
    assert (p['N_rho4'], p['N_rho8']) == (smooth, dense) == (5985, 16889)
    assert p['N'] == 749 and p['N_est'] == pytest.approx(p['N'], rel=0.01)  # the sphere counted and estimated agree
    assert solids.plane_waves(cell, 60)['N'] / p['N'] == pytest.approx(2 ** 1.5, rel=0.02)  # N ~ E_cut^(3/2)


def test_the_bloch_wave_is_the_same_on_the_sites():
    w = solids.wave(0.3, 1)
    assert w['E'] == pytest.approx(-2 * math.cos(0.3 * math.pi))
    x = w['x']
    for s in w['sites']:
        i = x.index(s['x'])
        assert w['re'][i] == pytest.approx(w['re_g'][i], abs=1e-9)  # k and k + 2π/a agree on the atoms
    between = [i for i, v in enumerate(x) if abs(v - round(v)) > 0.2]
    assert max(abs(w['re'][i] - w['re_g'][i]) for i in between) > 0.5  # and differ between them
    assert solids.wave(1, 0)['E'] == pytest.approx(2.0)  # the top of the band at π/a: −2β = 2|β|
    with pytest.raises(ValueError):
        solids.wave(1.5)


def test_k_meshes_of_a_metal_and_an_insulator():
    metal = solids.mesh('metal', 40)
    assert metal['exact'] == pytest.approx(-4 / math.pi)
    insulator = solids.mesh('insulator', 40, delta=1.0)
    err = [abs(r['err']) for r in insulator['rows']]
    assert err[11] < 1e-4 and all(b < a for a, b in zip(err, err[1:]))  # monotone, exponential
    assert abs(metal['rows'][39]['err']) < 5e-3 and abs(metal['rows'][11]['err']) > 1e-2  # a metal is slow
    ratio = err[20] / err[10]
    assert ratio < 1e-2


def test_the_symmetry_of_a_square_mesh():
    shifted = solids.mesh2d(4, True)
    assert [(p['k'], p['w']) for p in shifted['irreducible']] == [([0.125, 0.125], 4), ([0.375, 0.125], 8),
                                                                   ([0.375, 0.375], 4)]
    gamma = solids.mesh2d(4, False)
    assert len(gamma['irreducible']) == 6 and sum(p['w'] for p in gamma['irreducible']) == 16
    assert all(sum(p['w'] for p in solids.mesh2d(n, s)['irreducible']) == n * n for n in range(1, 9) for s in (0, 1))


def test_the_two_atom_chain():
    metal = solids.pair(0.0, -1, -1, electrons=2)
    assert metal['gap'] == pytest.approx(0, abs=1e-9) and metal['metal']
    insulator = solids.pair(1.0, -1, -1, electrons=2)
    assert insulator['gap'] == pytest.approx(1.0) and not insulator['metal'] and insulator['ef'] == pytest.approx(0)
    peierls = solids.pair(0.0, -1.2, -0.8, electrons=2)
    assert peierls['gap'] == pytest.approx(2 * 0.4) and not peierls['metal']
    assert solids.pair(1.0, electrons=1)['metal'] and not solids.pair(1.0, electrons=4)['metal']
    step = metal['E'][1] - metal['E'][0]
    assert sum(metal['dos']) * step == pytest.approx(2, abs=1e-3)  # two bands per cell
    step = insulator['E'][1] - insulator['E'][0]  # its own energy grid
    assert sum(insulator['pdos_a']) * step == pytest.approx(1, abs=1e-3)  # one orbital of A
    # the upper band lies on A (on-site +Δ/2): its PDOS above the gap outweighs that of B
    up = [i for i, e in enumerate(insulator['E']) if e > insulator['cbm']]
    assert sum(insulator['pdos_a'][i] for i in up) > 2 * sum(insulator['pdos_b'][i] for i in up)


def test_graphene_at_the_special_points():
    g = solids.graphene(0.0, -2.8)
    at = lambda x: min(range(len(g['x'])), key=lambda i: abs(g['x'][i] - x))
    gamma, m, k = at(0), at(g['ticks'][1]), at(g['ticks'][2])
    assert g['upper'][gamma] == pytest.approx(8.4) and g['upper'][m] == pytest.approx(2.8)
    assert g['upper'][k] == pytest.approx(0, abs=1e-9) and g['gap'] == 0
    hbn = solids.graphene(4.0, -2.8)
    assert hbn['upper'][k] == pytest.approx(2.0) and hbn['gap'] == pytest.approx(4.0)
    step = g['E'][1] - g['E'][0]
    assert sum(g['dos']) * step == pytest.approx(2, abs=1e-3)


def test_nearly_free_electrons():
    weak = solids.nfe(0.05, 4)
    first = next(x for x in weak['gaps'] if x['between'] == [1, 2])
    assert first['k'] == 1.0 and first['gap'] == pytest.approx(0.1, rel=1e-3)  # 2|V|
    assert all(x['gap'] == pytest.approx(0, abs=1e-12) for x in solids.nfe(0.0, 3)['gaps'])
    assert solids.nfe(0.3, 0)['gaps'] == []  # one plane wave: no gaps
    converged = solids.nfe(1.0, 6)['bands'][0]
    assert solids.nfe(1.0, 4)['bands'][0] == pytest.approx(converged, abs=1e-6)  # the basis has converged


def test_the_endpoints():
    assert api.call('sol.pw', {'cell': 'si', 'ecut': 30})['N'] == 749
    assert len(api.call('sol.mesh', {'kind': 'metal', 'n': 10, 'delta': 1})['rows']) == 10
    assert api.call('sol.pair', {'delta': 1, 'b1': -1, 'b2': -1, 'e': 2, 'sigma': 0.08})['gap'] == pytest.approx(1)
    assert set(api.call('sol.graphene', {'delta': 0, 'sigma': 0.15})) >= {'x', 'upper', 'dos'}
    assert len(api.call('sol.mesh2d', {'n': 4, 'shift': True})['irreducible']) == 3
    with pytest.raises(Exception):
        api.call('sol.pw', {'cell': 'gold', 'ecut': 30})
    for name in ('sol.wave', 'sol.mesh', 'sol.mesh2d', 'sol.pw', 'sol.pair', 'sol.graphene', 'sol.nfe', 'sol.eos', 'sol.phonons', 'sol.cv'):
        assert name in api.REGISTRY


def test_the_pages_name_what_their_scripts_draw():
    web = ATLAS_HOME / 'quas_atlas' / 'web'
    for lang in ('ru', 'en', 'zh'):
        for topic in ('bloch', 'bands', 'solidprops'):
            page = (web / lang / f'{topic}.html').read_text(encoding='utf-8')
            script = (web / lang / 'js' / f'{topic}.js').read_text(encoding='utf-8')
            for ident in set(re.findall(r"\$\('([A-Za-z]\w*)'\)", script)):
                assert f'id="{ident}"' in page, f'{lang}/{topic}: #{ident}'
            assert page.count('data-ok="1"') == 4 and f'window.QC_GL_SELF="{topic}"' in page


# ---- the properties of crystals ----
@pytest.mark.parametrize('kind', sorted(solids.EOS_PRESETS))
def test_exact_points_give_back_the_equation_of_state(kind):
    fit, ref = solids.eos(kind, 6, 7, 0)['fit'], solids.EOS_PRESETS[kind]
    assert fit['V0'] == pytest.approx(ref['V0'], rel=1e-7)
    assert fit['B0'] == pytest.approx(ref['B0'], rel=1e-6)
    assert fit['Bp'] == pytest.approx(ref['Bp'], rel=1e-5)
    assert solids.eos(kind, 0.5, 4, 0)['fit']['B0'] == pytest.approx(ref['B0'], rel=1e-4)  # narrow but sound


def test_the_bulk_modulus_is_the_curvature():
    V0, B0, Bp = 20.0, 100.0, 4.0
    h = 1e-3
    E = lambda v: solids.birch_murnaghan(v, V0, B0, Bp)
    curv = (E(V0 + h) - 2 * E(V0) + E(V0 - h)) / h ** 2
    assert V0 * curv * solids.EV_A3_GPA == pytest.approx(B0, rel=1e-5)
    assert E(V0) == 0 and E(V0 * 1.05) > 0 and E(V0 * 0.95) > 0


def test_noise_over_a_narrow_range_spoils_the_fit():
    narrow, wide = solids.eos('si', 1, 7, 5)['fit'], solids.eos('si', 10, 11, 5)['fit']
    assert narrow['V0'] == pytest.approx(20.02, rel=0.01)  # the minimum still shows
    assert narrow['B0'] > 500  # the curvature does not
    assert wide['B0'] == pytest.approx(98.8, rel=0.05) and wide['Bp'] == pytest.approx(4.2, rel=0.15)
    assert solids.eos('si', 1, 7, 5) == solids.eos('si', 1, 7, 5)  # the noise is fixed
    with pytest.raises(ValueError):
        solids.eos('si', 40, 7, 0)


def test_the_phonon_branches_and_the_gap():
    p = solids.phonons(40, 10, 50)
    to_cm = 1 / (2 * math.pi * solids.C_CM)
    assert p['acoustic_top'] == pytest.approx(math.sqrt(2 * 50 / (40 * solids.AMU)) * to_cm)
    assert p['optical_bottom'] == pytest.approx(2 * p['acoustic_top'])  # the masses differ fourfold
    mid = len(p['k']) // 2
    assert p['k'][mid] == 0 and p['acoustic'][mid] == pytest.approx(0, abs=1e-6)
    assert p['optical'][mid] == pytest.approx(p['optical_top'])
    assert max(p['acoustic']) == pytest.approx(p['acoustic_top'], rel=1e-9)
    assert min(p['optical']) == pytest.approx(p['optical_bottom'], rel=1e-9)
    assert solids.phonons(28, 28, 50)['gap'] == pytest.approx(0, abs=1e-9)
    with pytest.raises(ValueError):
        solids.phonons(0.5, 10, 50)


def test_the_heat_capacity_limits():
    assert solids.debye_cv(3000, 343) == pytest.approx(1, abs=1e-3)  # Dulong–Petit
    for T in (2, 5, 10):
        assert solids.debye_cv(T, 343) == pytest.approx(4 * math.pi ** 4 / 5 * (T / 343) ** 3, rel=1e-3)
    assert solids.debye_cv(0.5, 2230) == pytest.approx(4 * math.pi ** 4 / 5 * (0.5 / 2230) ** 3, rel=1e-9)  # the T³ branch
    assert solids.einstein_cv(3000, 300) == pytest.approx(1, abs=1e-3)
    assert solids.einstein_cv(10, 300) < 1e-9 < solids.debye_cv(10, 300)  # Einstein falls exponentially
    h = solids.heat_capacity('diamond', 300)
    assert h['at']['debye'] == pytest.approx(0.17, abs=0.01)
    assert solids.heat_capacity('cu', 300)['at']['debye'] == pytest.approx(0.94, abs=0.01)
    assert all(a <= b + 1e-12 for a, b in zip(h['debye'], h['debye'][1:]))


def test_the_properties_endpoints():
    assert api.call('sol.eos', {'kind': 'mgo', 'span': 6, 'n': 7, 'noise': 0})['fit']['B0'] == pytest.approx(160)
    assert api.call('sol.phonons', {'m1': 24.3, 'm2': 16.0, 'C': 60})['gap'] == pytest.approx(67.3, abs=0.1)
    assert api.call('sol.cv', {'kind': 'cu', 'T': 300})['theta'] == 343
    with pytest.raises(Exception):
        api.call('sol.cv', {'kind': 'gold', 'T': 300})
    with pytest.raises(Exception):
        api.call('sol.eos', {'kind': 'si', 'span': 6, 'n': 3, 'noise': 0})

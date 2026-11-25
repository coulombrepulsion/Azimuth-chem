"""The Atlas topics on defects and surfaces (defects.html) and on adsorption and magnetism (adsorption.html): the models
quas_atlas.core.defects and core.adsorption and their endpoints; no Qt, no browser.

Oracles — the numbers of lecture 15 of the course «Квантово-химические методы» (its derivations): c(3.6 eV, 1687 K)
= e^{−24.8} ≈ 2·10⁻¹¹; ε(+/0) = 0.5 and ε(0/−) = 0.9 eV for 2.9, 3.4, 4.3 eV; the Makov–Payne term 0.16 eV for Si,
q = 1, 64 atoms, 0.11 eV for 216, about 1.5 eV for q = 2, ε = 5; γ(111) = 1.36, γ(100) = 2.36 J/m² by the bonds; the
error Nδ/(2A); the 2 × 2 roots of the adsorbate and a metal level; the Stoner criterion I·N(E_F) > 1 (Pd ≈ 0.8);
the Hubbard dimer −2t for U = 0 and −4t²/U for U ≫ t; DFT+U: U/8 at n = ½, ∓U/2.
"""

import math
import re
import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import adsorption, defects  # noqa: E402


def test_the_vacancy_of_silicon_at_its_melting_point():
    v = defects.vacancy(3.6, 1687)
    assert v['x'] == pytest.approx(24.76, abs=0.01)
    assert v['c'] == pytest.approx(1.76e-11, rel=0.01)
    assert v['factor'] == pytest.approx(math.exp(0.3 / (defects.K_B * 1687)))
    assert defects.vacancy(3.6, 300)['x'] == pytest.approx(139.3, abs=0.1)  # e^{−139}: none at room temperature


def test_the_transition_levels():
    c = defects.charged(2.9, 3.4, 4.3, 1.17)
    assert [l['label'] for l in c['levels']] == ['+/0', '0/−']
    assert [round(l['at'], 9) for l in c['levels']] == [0.5, 0.9]
    assert [s['q'] for s in c['stable']] == ['+', '0', '−']
    neg = defects.charged(2.9, 3.6, 4.0, 1.17)  # ε(+/0) = 0.7 > ε(0/−) = 0.4: «negative U»
    assert [l['label'] for l in neg['levels']] == ['+/−'] and neg['levels'][0]['at'] == pytest.approx(0.55)
    assert defects.charged(2.0, 4.0, 9.0, 1.17)['levels'] == []  # always positive within the gap
    for i, x in enumerate(c['ef']):  # the lowest line is the lowest of the three
        assert c['lowest'][i] == pytest.approx(min(c['lines'][k][i] for k in ('+', '0', '−')))


def test_the_makov_payne_term():
    rows = defects.supercell(1, 11.7)['rows']
    assert [r['atoms'] for r in rows] == [64, 216, 512, 1000, 1728]
    assert rows[0]['dE'] == pytest.approx(0.16, abs=0.005) and rows[1]['dE'] == pytest.approx(0.11, abs=0.005)
    assert rows[0]['dE'] * rows[0]['L'] == pytest.approx(rows[-1]['dE'] * rows[-1]['L'])  # 1/L
    assert defects.supercell(2, 5)['rows'][0]['dE'] == pytest.approx(1.5, abs=0.05)


def test_the_surface_energy_by_the_bonds_and_the_error_of_the_bulk_energy():
    assert defects.slab('111', 0, 0)['gamma'] == pytest.approx(1.36, abs=0.005)
    assert defects.slab('100', 0, 0)['gamma'] == pytest.approx(2.36, abs=0.005)
    assert defects.slab('100r', 0, 0)['gamma'] == 1.44
    s = defects.slab('111', 10, 0)
    for n, ext, err in zip(s['N'], s['ext'], s['err_formula']):  # γ from elsewhere is off by Nδ/(2A)
        assert ext - s['gamma'] == pytest.approx(err, abs=1e-9)
    assert all(f == pytest.approx(s['gamma'], abs=1e-9) for f in s['fit'] if f is not None)  # the line: exact
    noisy = defects.slab('111', 10, 2)
    assert abs(noisy['fit'][-1] - noisy['gamma']) < abs(noisy['ext'][-1] - noisy['gamma'])
    with pytest.raises(ValueError):
        defects.slab('110', 0, 0)


def test_the_two_level_problem_and_the_band():
    c = adsorption.chemisorption(-2.0, -2.25, 6.5, 2.0)
    half, root = (-2.0 - 2.25) / 2, math.sqrt(0.125 ** 2 + 4)
    assert c['two']['lower'] == pytest.approx(half - root) and c['two']['upper'] == pytest.approx(half + root)
    assert sum(s['w'] for s in c['states']) == pytest.approx(1.0, abs=1e-9)  # the adsorbate is shared out whole
    levels = adsorption._band_levels(-2.25, 6.5, 80)
    for s in c['states']:  # every state solves the secular equation
        rest = s['E'] + 2.0 - sum(4.0 / 80 / (s['E'] - e) for e in levels)
        assert abs(rest) < 1e-6
    free = adsorption.chemisorption(-2.0, -2.25, 6.5, 0.0)
    assert free['hyb'] == pytest.approx(0, abs=1e-9) and free['pauli'] == 0


def test_the_d_band_rule():
    rows = {m['name']: m['dE'] for m in adsorption.trend()['metals']}
    assert rows['Ni'] < rows['Pd'] < rows['Pt'] < 0 < rows['Cu']  # the higher the d band, the stronger the bond
    assert rows['Au'] > 0 and rows['Ag'] > 0  # noble: the antibonding states are filled


def test_the_stoner_criterion():
    for name, (n, W, I) in adsorption.STONER.items():
        s = adsorption.stoner(n, W, I)
        assert (s['moment'] > 0.01) == (s['product'] > 1), name
    assert adsorption.stoner(*adsorption.STONER['Fe'])['moment'] > 2
    assert 0.4 < adsorption.stoner(*adsorption.STONER['Ni'])['moment'] < 0.8
    s = adsorption.stoner(7.0, 5.0, 0.5)
    small = s['m'][1]  # E ≈ (m²/4)(1/N − I) for a small moment
    assert s['E'][1] == pytest.approx(small ** 2 / 4 * (1 / s['N_EF'] - 0.5), rel=1e-3)


def test_the_hubbard_dimer_and_dft_plus_u():
    assert adsorption.hubbard(0)['at']['E_S'] == pytest.approx(-2.0)
    big = adsorption.hubbard(20)['at']
    assert big['J'] == pytest.approx(0.198, abs=0.001) and big['J_large_U'] == pytest.approx(0.2)
    assert adsorption.hubbard(0)['at']['ionic'] == pytest.approx(0.5)
    p = adsorption.plus_u(5.0)
    assert p['E_U'][50] == pytest.approx(5 / 8) and p['E_U'][0] == 0 and p['E_U'][-1] == 0
    assert (p['shift_filled'], p['shift_empty']) == (-2.5, 2.5) and p['V'][0] == 2.5 and p['V'][-1] == -2.5


def test_the_endpoints():
    assert api.call('def.vacancy', {'ef': 3.6, 'T': 1687})['c'] == pytest.approx(1.76e-11, rel=0.01)
    r = api.call('def.charged', {'ep': 2.9, 'e0': 3.4, 'em': 4.3, 'gap': 1.17, 'q': 1, 'eps': 11.7})
    assert len(r['levels']) == 2 and r['supercell'][0]['atoms'] == 64
    assert api.call('def.slab', {'face': '100', 'delta': 0, 'noise': 0})['gamma'] == pytest.approx(2.357, abs=0.001)
    assert api.call('ads.chem', {'ea': -2, 'ed': -1.29, 'W': 4, 'V': 2})['dE'] < 0
    assert api.call('ads.stoner', {'n': 9.5, 'W': 4.6, 'I': 0.7})['moment'] == 0
    assert api.call('ads.hubbard', {'U': 4, 'Ueff': 5})['plus_u']['half'] == pytest.approx(0.625)
    with pytest.raises(Exception):
        api.call('def.slab', {'face': '110', 'delta': 0, 'noise': 0})
    for name in ('def.vacancy', 'def.charged', 'def.slab', 'ads.chem', 'ads.stoner', 'ads.hubbard'):
        assert name in api.REGISTRY


def test_the_pages_name_what_their_scripts_draw():
    web = ATLAS_HOME / 'quas_atlas' / 'web'
    for lang in ('ru', 'en', 'zh'):
        for topic in ('defects', 'adsorption'):
            page = (web / lang / f'{topic}.html').read_text(encoding='utf-8')
            script = (web / lang / 'js' / f'{topic}.js').read_text(encoding='utf-8')
            for ident in set(re.findall(r"\$\('([A-Za-z]\w*)'\)", script)):
                assert f'id="{ident}"' in page, f'{lang}/{topic}: #{ident}'
            assert page.count('data-ok="1"') == 4 and f'window.QC_GL_SELF="{topic}"' in page

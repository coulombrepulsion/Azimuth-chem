"""The Atlas topics added on their models
(quas_atlas.core.nmr, conformers, relativity, crystals) and endpoints; no Qt, no browser.

Oracles: γ(¹H)/2π = 42.577478 MHz/T (CODATA 2018); binomial multiplets; the ethane symmetry (three equal
minima); the Dirac 1s energy of hydrogen −1/2 − α²/8 to first order; def2 ECP core sizes from the basis set
exchange (28 for Rb–Xe, 46 for Cs–La, 60 for Hf–Rn); NaCl, Cu, Si cells from crystallographic tables
(ρ(NaCl) = 2.1635 g/cm³ from a = 5.6402 Å, Z = 4 — the measured density is 2.165; Cu (111) at 2θ = 43.3° with Cu Kα1);
the packing fraction π/(3√2).
"""

import math
import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import conformers, crystals, nmr, relativity  # noqa: E402


def test_nmr_larmor_shift_and_multiplets():
    assert nmr.larmor(9.3947)['nu']['1H'] == pytest.approx(400.0, abs=0.01)
    assert nmr.larmor(14.1)['nu']['13C'] == pytest.approx(151.0, abs=0.1) and nmr.larmor(1)['nu']['15N'] < 0
    assert nmr.shifts([31.88, 30.66], 31.88)['delta'] == pytest.approx([0.0, 1.22])
    assert nmr.shifts([24.6], 31.9, slope=-1.0, intercept=31.9)['delta'][0] == pytest.approx(7.3)
    t = nmr.multiplet(2, 7.0, 300, 1.0)
    assert [w for _, w in t['lines']] == [0.25, 0.5, 0.25] and t['width_hz'] == 14
    assert t['width_ppm'] == pytest.approx(14 / 300) and nmr.multiplet(2, 7.0, 600, 1.0)['width_ppm'] == pytest.approx(t['width_ppm'] / 2)
    s = nmr.spectrum([{'delta': 1.22, 'count': 3, 'n': 2, 'J': 7.0}, {'delta': 3.69, 'count': 2, 'n': 3, 'J': 7.0}], 400, 1.2, 0, 5, 2000)
    assert max(s['y']) == pytest.approx(1.0) and len(s['lines']) == 7
    with pytest.raises(ValueError):
        nmr.multiplet(13, 7.0, 300)


def test_conformers_ethane_butane_and_the_grid():
    e = conformers.profile(*conformers.PRESETS['ethane'])
    assert len(e['minima']) == 3 and all(m['p'] == pytest.approx(1 / 3) for m in e['minima'])
    assert all(m['E'] == pytest.approx(12.0) for m in e['maxima'])
    b = conformers.profile(*conformers.PRESETS['butane'], T=298.15)
    anti = min(b['minima'], key=lambda m: m['E'])
    gauche = [m for m in b['minima'] if m is not anti]
    assert abs(abs(anti['phi']) - 180) < 1e-6 and len(gauche) == 2
    assert 3.5 < gauche[0]['E'] < 3.8 and gauche[0]['E'] == pytest.approx(gauche[1]['E'])
    assert 0.66 < anti['p'] < 0.70 and sum(m['p'] for m in b['minima']) == pytest.approx(1.0)
    hot = conformers.profile(*conformers.PRESETS['butane'], T=1000)
    assert min(hot['minima'], key=lambda m: m['E'])['p'] < anti['p']  # heating spreads the molecules
    assert conformers.profile(0, 0, 0)['flat'] and conformers.grid_cost(10, 3, 1.0)['starts'] == 59049
    assert conformers.grid_cost(10, 3, 1.0)['days'] == pytest.approx(41.0, abs=0.01)


def test_relativity_hydrogen_gold_and_ecp():
    alpha = 1 / relativity.C
    h = relativity.hydrogenic(1)
    assert h['E_dirac'] == pytest.approx(-0.5 - alpha**2 / 8, abs=1e-9) and h['E_ratio'] > 1
    au = relativity.hydrogenic(79)
    assert au['v'] == pytest.approx(0.5765, abs=1e-4) and au['r_ratio'] == pytest.approx(0.817, abs=1e-3)
    assert au['gamma'] == pytest.approx(1 / au['r_ratio']) and 1.09 < au['E_ratio'] < 1.11
    assert [relativity.ecp(z)['core'] for z in (35, 37, 53, 55, 57, 72, 79, 86)] == [0, 28, 28, 46, 46, 60, 60, 60]
    assert relativity.ecp(79)['valence'] == 19 and relativity.ecp(60)['core'] is None
    assert len(relativity.curve()) == 118
    with pytest.raises(ValueError):
        relativity.hydrogenic(138)


def test_crystals_density_bragg_and_packing():
    P = crystals.PRESETS

    def cell(k):
        v = P[k]
        return crystals.cell(v['a'], v['b'], v['c'], v['al'], v['be'], v['ga'], v['Z'], v['M'])

    def lines(k):
        v = P[k]
        return crystals.pattern(v['a'], v['b'], v['c'], v['al'], v['be'], v['ga'], v['cent'])['lines']

    assert cell('nacl')['rho'] == pytest.approx(2.1635, abs=0.0005) and cell('cu')['rho'] == pytest.approx(8.94, abs=0.01)
    assert cell('si')['rho'] == pytest.approx(2.329, abs=0.002)
    ice = P['ice']
    assert cell('ice')['V'] == pytest.approx(ice['a'] ** 2 * ice['c'] * math.sqrt(3) / 2)
    cu = lines('cu')
    assert cu[0]['hkl'] == [1, 1, 1] and cu[0]['tt'] == pytest.approx(43.3, abs=0.05) and cu[0]['mult'] == 8
    assert [l['hkl'] for l in lines('si')[:3]] == [[1, 1, 1], [2, 2, 0], [3, 1, 1]]  # (200) is extinct in diamond
    assert lines('fe')[0]['hkl'] == [1, 1, 0]
    first = [tuple(l['hkl']) for l in lines('ice')[:3]]
    assert (0, 0, 1) not in first and len(first) == 3
    assert crystals.packing('fcc')['pf'] == pytest.approx(math.pi / (3 * math.sqrt(2))) and crystals.packing('bcc')['cn'] == 8


def test_new_endpoints_validate_their_parameters():
    assert api.call('rel.atom', {'Z': 79})['ecp']['core'] == 60
    assert api.call('cr.pattern', {'a': 3.6149, 'b': 3.6149, 'c': 3.6149, 'al': 90, 'be': 90, 'ga': 90, 'cent': 'F',
                                   'lam': 1.540593, 'n': 3})['lines'][0]['hkl'] == [1, 1, 1]
    assert api.call('nmr.shifts', {'sigmas': [30.66], 'ref': 31.88, 'slope': -1.0})['delta'][0] == pytest.approx(1.22)
    with pytest.raises(api.ApiError):
        api.call('conf.cost', {'n': 0, 'k': 3, 'minutes': 1})
    with pytest.raises(api.ApiError):
        api.call('nmr.shifts', {'sigmas': ['x'], 'ref': 31.9, 'slope': -1.0})

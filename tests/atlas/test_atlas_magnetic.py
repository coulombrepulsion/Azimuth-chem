"""The EPR and NICS panels of the Atlas NMR page (nmr.html): the model quas_atlas.core.magnetic and its endpoints; no
Qt, no browser.

Oracles — lecture 5 of the course «Квантово-химические методы»: A_iso of the hydrogen 1s ≈ 1423 MHz (experiment
1420.4, the 21 cm line); the density at the nucleus relative to the exact 0.24 (one Gaussian), 0.65 (STO-3G), 0.88
(STO-6G) (derivation 6); a diatropic ring current: NICS < 0 inside and above the ring, the ring protons deshielded;
paratropic — the reverse (derivation 9).
"""

import sys

import pytest

from modules.atlas.paths import ATLAS_HOME

if str(ATLAS_HOME) not in sys.path:
    sys.path.insert(0, str(ATLAS_HOME))

from quas_atlas import api, pages  # noqa: E402,F401  (pages registers the endpoints)
from quas_atlas.core import magnetic  # noqa: E402


def test_the_fermi_contact_of_hydrogen():
    f = magnetic.fermi('sto3g')
    assert round(f['a_exact']) == 1423 and abs(f['a_exact'] - f['exp']) < 5
    assert [round(magnetic.fermi(b)['ratio'], 2) for b in ('g1', 'sto3g', 'sto6g')] == [0.24, 0.65, 0.88]
    assert magnetic.fermi('g1')['energy'] == pytest.approx(-4 / (3 * 3.141592653589793), abs=1e-9)  # −0.4244
    assert -0.5 < magnetic.fermi('sto6g')['energy'] < -0.499
    assert f['exact'][0] == pytest.approx(1 / 3.141592653589793 ** 0.5)


def test_the_ring_current():
    b = magnetic.ring(-10, 1.39)
    assert b['axis'][0] == pytest.approx(-10) and b['plane'][0] == pytest.approx(-10, abs=1e-6)
    assert b['nics1'] == pytest.approx(-10 * 1.39 ** 3 / (1.39 ** 2 + 1) ** 1.5)
    assert 0.5 < b['proton']['dshift'] < 3  # benzene protons deshielded by the current
    outside = [v for r, v in zip(b['rho'], b['plane']) if v is not None and r > 1.6]
    assert all(v > 0 for v in outside)  # the induced field adds to B outside the ring
    c = magnetic.ring(27, 1.0)
    assert c['nics1'] > 0 and c['proton']['dshift'] < 0  # paratropic: the reverse
    with pytest.raises(ValueError):
        magnetic.ring(50, 1.0)


def test_the_endpoints():
    assert round(api.call('nmr.fermi', {'basis': 'sto6g'})['ratio'], 2) == 0.88
    assert api.call('nmr.ring', {'nics0': 0, 'R': 1.4})['nics1'] == 0
    with pytest.raises(Exception):
        api.call('nmr.fermi', {'basis': 'cc-pvdz'})
    for name in ('nmr.fermi', 'nmr.ring'):
        assert name in api.REGISTRY

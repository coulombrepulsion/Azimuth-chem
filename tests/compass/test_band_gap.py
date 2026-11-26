"""The band gap of a band structure (modules/compass/chemistry/band_gap.py).

Oracles: the eigenvalues of the real run of pw.x 7.6 for silicon (tests/data/qe/si_bands_pw76.out, PBE, 297 points,
8 bands) copied by hand from its lines — Γ: «-5.7594 6.2016 6.2016 6.2016 8.7644 …» (the top of the valence band
6.2016 eV, the direct gap at Γ 8.7644 − 6.2016 = 2.5628 eV); the lowest fifth band of the file, 6.7757 eV, at its
40th point — on Γ–X, at 85 % of the way (the textbook place of the minimum of the conduction band of silicon,
0.85 of Γ–X); the gap of the summary line the panel of Quantum ESPRESSO has shown since 0.93, 0.574 eV (another code
path: the levels around E₀ of the scf run). Model bands written here for the direct gap, the metal and the refusals.
"""

from pathlib import Path

import pytest

from modules.compass.chemistry import band_gap
from modules.sextant import qe_paths
from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'


def silicon_bands():
    from modules.compass.chemistry import crystal as cr
    from tests.sextant.test_qe_inputs import silicon

    text = (DATA / 'si_bands_pw76.out').read_text(encoding='utf-8')
    si = silicon()
    path = qe_paths.path(si, cr.primitive_basis(si))
    return text, qe.bands(text), path


def test_silicon_has_an_indirect_gap_on_the_way_to_x():
    text, bands, path = silicon_bands()
    assert band_gap.occupied_bands(text) == 4  # «number of electrons = 8.00»
    found = band_gap.gap(bands.energies, 4, path.x, path.ticks)
    assert found.kind == 'indirect' and found.occupied == 4
    assert (found.vbm.energy, found.vbm.index, found.vbm.where) == (6.2016, 0, 'Γ')
    assert (found.cbm.energy, found.cbm.index) == (6.7757, 39) and found.cbm.where == 'между Γ и X, 85 % пути'
    assert found.gap == pytest.approx(0.5741, abs=1e-4) and found.gap == pytest.approx(0.574, abs=1e-3)
    assert found.direct == pytest.approx(2.5628, abs=1e-4) and found.direct_where == 'Γ'
    line = band_gap.text(found)
    assert 'Щель непрямая: 0.57 эВ' in line and 'в точке Γ' in line and '85 %' in line and '2.56 эВ' in line


def test_a_direct_gap_a_metal_and_what_cannot_be_told():
    x, ticks = [0.0, 0.5, 1.0, 1.5, 2.0], [(0.0, 'Γ'), (1.0, 'X'), (2.0, 'M')]
    direct = [[-1.0, 2.5], [-0.2, 1.8], [0.0, 1.5], [-0.3, 2.0], [-0.9, 2.6]]  # both edges at X
    found = band_gap.gap(direct, 1, x, ticks)
    assert found.kind == 'direct' and found.gap == pytest.approx(1.5) and found.vbm.where == found.cbm.where == 'X'
    assert band_gap.text(found).startswith('Щель прямая: 1.50 эВ в точке X.')
    metal = [[-1.0, 0.4], [0.5, 1.5], [0.2, 0.9]]  # the first band at the second point is above the second at the first
    found = band_gap.gap(metal, 1, [0.0, 0.5, 1.0], [(0.0, 'Γ'), (1.0, 'X')])
    assert found.kind == 'metal' and found.gap == 0.0 and 'металл' in band_gap.text(found)
    assert band_gap.gap(direct, 2) is None  # no empty band computed
    assert band_gap.gap([], 1) is None and band_gap.gap(direct, None) is None and band_gap.text(None) == ''
    assert band_gap.gap(direct, 1).vbm.where == ''  # without a path the place is not named


def test_the_number_of_occupied_bands():
    assert band_gap.occupied_bands('     number of electrons       =        16.00\n') == 8
    assert band_gap.occupied_bands('     number of electrons       =         7.00\n') is None  # an odd number: a metal
    assert band_gap.occupied_bands('number of electrons = 8.00\n ------ SPIN UP ------------\n') is None
    assert band_gap.occupied_bands('') is None


def test_the_place_of_a_point_of_the_path():
    x, ticks = [0.0, 0.25, 1.0, 1.0, 1.4], [(0.0, 'Γ'), (1.0, 'K|U'), (1.4, 'X')]
    assert band_gap.where(0, x, ticks) == 'Γ' and band_gap.where(2, x, ticks) == 'K|U'
    assert band_gap.where(1, x, ticks) == 'между Γ и K, 25 % пути'  # the first letter of a jump is where the run ends
    assert band_gap.where(9, x, ticks) == '' and band_gap.where(0) == ''


def test_the_dots_of_the_edges_on_the_plot():
    text, bands, path = silicon_bands()
    found = band_gap.gap(bands.energies, 4, path.x, path.ticks)
    marks = band_gap.marks(found, path.x, 6.2016)
    assert marks[0] == (0.0, 0.0, 'v') and marks[1][2] == 'c'
    assert marks[1][0] == pytest.approx(0.85 * path.ticks[1][0], rel=0.02) and marks[1][1] == pytest.approx(0.5741, abs=1e-4)
    assert band_gap.marks(None, path.x, 0.0) == []

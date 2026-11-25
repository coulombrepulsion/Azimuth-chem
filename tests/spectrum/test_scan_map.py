"""Two-dimensional relaxed scans: orca_scan of two coordinates, analysis/scan_map.py, the input of Sextant.

Oracles: the ORCA 6.0.1 run of the user (tests/data/scan2d/h2o_scan2d_orca.out — the two O–H bonds of water, 0.85…1.25
Å, 5 × 5, B3LYP/def2-SVP): the order of the points (for every value of the first coordinate all of the second, as the
«Calculated Surface» table of ORCA lists them), the symmetry E(r₁, r₂) = E(r₂, r₁) of the molecule, the minimum at
0.95 Å (B3LYP/def2-SVP gives 0.96–0.97 Å); bilinear refinement reproducing the nodes; marching squares on a plane.
xtb 6.7.1 (h2o2_scan2d_xtb.xtbscan.log) made 7 + 5 = 12 points of two scans one after the other — no grid.
"""

from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import scan_map as sm
from modules.spectrum.readers.orca_scan import read_scan

DATA = Path(__file__).parents[1] / 'data' / 'scan2d'


def water():
    return read_scan((DATA / 'h2o_scan2d_orca.out').read_text(encoding='utf-8'))


def test_grid_of_the_water_scan():
    scan = water()
    assert scan.kind == 'relaxed' and len(scan.coordinates) == 2 and len(scan.points) == 25
    assert [p.values for p in scan.points[:6]] == [(0.85, 0.85), (0.85, 0.95), (0.85, 1.05), (0.85, 1.15), (0.85, 1.25),
                                                   (0.95, 0.85)]
    g = sm.grid(scan)
    assert list(g.xs) == pytest.approx([0.85, 0.95, 1.05, 1.15, 1.25]) and g.labels == ('r(2–1), Å', 'r(3–1), Å')
    assert g.energy[0, 0] == pytest.approx(-76.28791549) and g.energy[4, 4] == pytest.approx(-76.24053674)
    assert np.allclose(g.energy, g.energy.T, atol=1e-6)  # the two O–H bonds are alike
    x, y, index = sm.minimum(g)
    assert (x, y) == (0.95, 0.95) and scan.points[index].values == (0.95, 0.95)
    assert [v[1] for v in sm.valley(g)] == [0.95] * 5  # the other bond stays near its minimum
    assert all(scan.points[i].geometry is not None for i in g.index.ravel())


def test_refinement_levels_and_isolines():
    g = sm.grid(water())
    fx, fy, fz = sm.fine(g.xs, g.ys, g.energy, 4)
    assert fz.shape == (17, 17) and np.allclose(fz[::4, ::4], g.energy)
    assert sm.levels(0.0, 1.0, 10) == pytest.approx([0.1 * k for k in range(1, 10)])
    assert sm.levels(-76.33, -76.24, 10)[0] > -76.33 and len(sm.levels(1.0, 1.0)) == 0
    xs = ys = np.array([0.0, 1.0, 2.0])
    plane = np.add.outer(ys, xs)  # z = x + y
    for (x1, y1), (x2, y2) in sm.isolines(xs, ys, plane, 1.5):
        assert x1 + y1 == pytest.approx(1.5) and x2 + y2 == pytest.approx(1.5)
    assert sm.nearest(g, 0.96, 1.24) == int(g.index[4, 1])


def test_one_coordinate_is_not_a_map():
    one = read_scan((DATA / 'h2o2_scan1d_orca.out').read_text(encoding='utf-8'))
    assert len(one.coordinates) == 1 and sm.grid(one) is None


def test_sextant_writes_a_two_dimensional_scan_for_orca_only():
    from azimuth.core import SCAN_TASK, Calculation, orca_input, read_xyz
    from modules.sextant import inputs

    w = read_xyz('3\nwater\nO 0 0 0.1173\nH 0 0.7572 -0.4692\nH 0 -0.7572 -0.4692')
    bonds = (('B', (0, 1)), ('B', (0, 2)))
    calc = Calculation(task=SCAN_TASK, scan_index=0, scan_end=1.25, scan_steps=5, scan2_index=1, scan2_end=1.25,
                       scan2_steps=5)
    text = orca_input(w, calc, bonds)
    assert '  Scan\n    B 0 1 = 0.9578, 1.2500, 5\n    B 0 2 = 0.9578, 1.2500, 5\n  end\n' in text
    assert 'Constraints' not in text  # both bonds are scanned, nothing else is held
    for bad, words in ((Calculation(task=SCAN_TASK, scan_end=1.25, scan2_index=0, scan2_end=1.25), 'совпадает с первой'),
                       (Calculation(task=SCAN_TASK, scan_end=1.25, scan2_index=1, scan2_end=20.0), 'от 0.3 до 10')):
        with pytest.raises(ValueError, match=words):
            orca_input(w, bad, bonds)
    with pytest.raises(ValueError, match='только для ORCA'):
        inputs.gaussian_input(w, calc, bonds)
    with pytest.raises(ValueError, match='по очереди'):
        inputs.xtb_control(w, calc, bonds)
    assert 'scan2_index' in inputs.task_options('orca', SCAN_TASK) and 'scan2_index' not in inputs.task_options(
        'xtb', SCAN_TASK)
    xtb = (DATA / 'h2o2_scan2d_xtb.xtbscan.log').read_text(encoding='utf-8')
    assert xtb.count('energy:') == 12  # xtb: 7 + 5, one scan after the other

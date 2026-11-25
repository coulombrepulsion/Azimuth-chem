"""Scans and IRC paths in ORCA outputs (modules/spectrum/readers/orca_scan.py).

Oracles, independent of the parser:
  * the energies of the table «The Calculated Surface using the 'Actual Energy'» copied by hand;
  * geometry: the dihedral angle 10-9-4-3 (0-based 9, 8, 3, 2) computed here from the coordinates of
    every point equals the scanned value. Tolerance 0.01 deg: the coordinates are printed to 1e-6 A,
    which moves a dihedral of ~1.4 A bonds by ~1e-4 deg; the relaxed scan keeps the constraint exactly;
  * the 12 points are 0, 32.7, ..., 360 deg = 360/11 deg apart (ORCA: range 0..360, 12 steps);
  * IRC: a summary table written after the ORCA 6.0 tutorial (synthetic: no real IRC output was
    available, see the ASSUMPTION in the module).
"""

from math import atan2, degrees
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.readers.orca import read_output
from modules.spectrum.readers.orca_scan import read_scan, with_trajectory

DATA = Path(__file__).parents[1] / 'data' / 'orca_cclib'


def dihedral(geometry, a, b, c, d):
    p = [np.array(geometry.atoms[k].position) for k in (a, b, c, d)]
    b0, b1, b2 = p[0] - p[1], p[2] - p[1], p[3] - p[2]
    b1 = b1 / np.linalg.norm(b1)
    v, w = b0 - (b0 @ b1) * b1, b2 - (b2 @ b1) * b1
    return degrees(atan2(np.cross(b1, v) @ w, v @ w))


@pytest.mark.parametrize(
    'name, kind, first, last',
    [
        ('dvb_scan_relaxed_orca6.0.out', 'relaxed', -382.05511575, -382.05511606),
        ('dvb_scan_unrelaxed_orca5.0.out', 'unrelaxed', -378.12338325, -378.12338339),
    ],
)
def test_scan_points(name, kind, first, last):
    scan = read_scan((DATA / name).read_text(encoding='utf-8'))
    assert scan.kind == kind and len(scan.points) == 12
    assert scan.points[0].energy == first and scan.points[-1].energy == last
    for k, point in enumerate(scan.points):
        assert point.number == k + 1
        assert point.values[0] == pytest.approx(k * 360 / 11, abs=1e-7)
        angle = dihedral(point.geometry, 9, 8, 3, 2)
        assert (angle - point.values[0] + 180) % 360 - 180 == pytest.approx(0, abs=0.01)


def test_relaxed_scan_coordinate_and_convergence():
    scan = read_scan((DATA / 'dvb_scan_relaxed_orca6.0.out').read_text(encoding='utf-8'))
    (coordinate,) = scan.coordinates
    assert coordinate.kind == 'dihedral' and coordinate.atoms == (9, 8, 3, 2)
    assert coordinate.label == 'φ(10–9–4–3)' and coordinate.unit == '°'
    assert all(p.converged for p in scan.points)
    energies = [p.energy for p in scan.points]
    assert scan.reference == energies.index(min(energies))
    # the rotation of a vinyl group: the barrier near 90 and 270 deg, minima at 0/180/360 (planar)
    assert max(energies[2:4]) - min(energies) > 0.005  # hartree


def test_unrelaxed_scan_names_its_zmatrix_parameter():
    scan = read_scan((DATA / 'dvb_scan_unrelaxed_orca5.0.out').read_text(encoding='utf-8'))
    (coordinate,) = scan.coordinates
    assert coordinate.kind == 'parameter' and coordinate.label == 'D7' and coordinate.unit == ''
    assert all(p.converged is None for p in scan.points)


def test_other_outputs_are_not_scans():
    for name in ('water_mp2_orca5.0.out', 'dvb_gopt_orca6.0.out', 'dvb_sp_un_dft_orca6.0.out'):
        assert read_scan((DATA / name).read_text(encoding='utf-8')) is None
    assert read_output((DATA / 'dvb_gopt_orca6.0.out').read_text(encoding='utf-8')).scan is None
    assert read_output((DATA / 'dvb_scan_relaxed_orca6.0.out').read_text(encoding='utf-8')).scan.kind == 'relaxed'


IRC = """
                          -----------------
                          IRC PATH SUMMARY
                          -----------------

All gradients are in Eh/Bohr.

Step        E(Eh)      dE(kcal/mol)  max(|G|)   RMS(G)
   1    -76.401000   -12.550000    0.004829  0.001679
   2    -76.390000    -5.647500    0.003100  0.001000
   3    -76.381000     0.000000    0.000149  0.000056 <= TS
   4    -76.392000    -6.902600    0.002900  0.000900
   5    -76.405000   -15.060000    0.004500  0.001500

Timings for individual modules:
"""


def test_irc_summary_and_its_trajectory():
    scan = read_scan(IRC)
    assert scan.kind == 'irc' and [p.number for p in scan.points] == [1, 2, 3, 4, 5]
    assert scan.reference == 2 and scan.points[2].ts and not scan.points[0].ts
    assert scan.points[0].energy == -76.401
    # dE as printed equals (E - E_TS) * 627.509474 kcal/mol per hartree, within the printed decimals
    for p, de in zip(scan.points, (-12.55, -5.6475, 0.0, -6.9026, -15.06)):
        assert (p.energy - scan.points[2].energy) * 627.509474 == pytest.approx(de, abs=0.01)
    frames = ''.join(f'3\nframe {k}\nO 0 0 {0.01 * k}\nH 0.96 0 0\nH -0.24 0.93 0\n' for k in range(5))
    joined = with_trajectory(scan, frames)
    assert all(p.geometry is not None for p in joined.points)
    with pytest.raises(ValueError):
        with_trajectory(scan, frames.split('3\nframe 4')[0])


def test_relaxed_point_is_the_optimized_geometry():
    # Oracle: ORCA prints «FINAL SINGLE POINT ENERGY» after each geometry of a constrained optimization;
    # the energy printed after the geometry chosen for a point must be the energy of that point in its
    # final table (the first geometry of a point has the scanned angle too, but a higher energy).
    import re

    text = (DATA / 'dvb_scan_relaxed_orca6.0.out').read_text(encoding='utf-8')
    scan = read_scan(text)
    heads = [m.start() for m in re.finditer(r'RELAXED SURFACE SCAN STEP', text)] + [len(text)]
    for k, point in enumerate(scan.points):
        part = text[heads[k] : heads[k + 1]]
        first_row = point.geometry.atoms[0]
        found = None
        for m in re.finditer(r'CARTESIAN COORDINATES \(ANGSTROEM\)\n-+\n\s*(\S+)\s+(\S+)\s+(\S+)\s+(\S+)', part):
            if m[1] == first_row.symbol and tuple(float(v) for v in m.groups()[1:]) == first_row.position:
                found = m.end()
        assert found is not None
        energy = float(re.search(r'FINAL SINGLE POINT ENERGY\s+(\S+)', part[found:])[1])
        assert energy == pytest.approx(point.energy, abs=1e-8)

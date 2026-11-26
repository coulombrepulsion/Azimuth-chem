"""Convergence series of a plane-wave calculation (modules/compass/chemistry/convergence.py).

Oracles: the values of a series and its table written out by hand; the definition of «converged from» applied by hand
to a model series; the real series of pw.x 7.6 for silicon (tests/data/qe/si_cutoff_pw76.out, si_kgrid_pw76.out) —
the «! total energy» lines copied from the outputs, the energy falling with the cutoff (the plane-wave basis is
variational) and the pressures pw.x printed.
"""

import re
from pathlib import Path

import pytest

from modules.compass.chemistry import convergence as cv
from modules.sextant import qe_inputs
from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'
RY = 13.605693122994
# copied by hand from the «! total energy» and «P=» lines of the two outputs (Ry, kbar)
CUTOFF_ENERGIES = [-22.83771743, -22.83949545, -22.83961527, -22.83970914, -22.83972917, -22.83974056]
CUTOFF_PRESSURES = [18.17, 19.58, 19.65, 19.67, 19.71, 19.71]
KGRID_ENERGIES = [-22.82579088, -22.83892144, -22.83949545, -22.83959373, -22.83961497, -22.83961745]
# by hand from them, per atom (two atoms): 40 Ry is 0.85 meV above 70 Ry (30 Ry — 1.67 meV); the grid 9 × 9 × 9 of the
# primitive cell is 0.83 meV above 18 × 18 × 18 (7 × 7 × 7 — 4.73 meV)
CUTOFF_CONVERGED, KGRID_CONVERGED = 2, 2


def test_the_values_of_the_series():
    assert cv.cutoffs(30.0, 8.0) == [(20.0, 160.0), (30.0, 240.0), (40.0, 320.0), (50.0, 400.0), (60.0, 480.0), (70.0, 560.0)]
    assert [w for w, _ in cv.cutoffs(47.0, 4.0)] == [30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0]  # around 50, the nearest ten
    assert cv.cutoffs(47.0, 4.0)[0] == (30.0, 120.0)
    assert cv.cutoffs(12.0)[0][0] == 20.0  # never below 20 Ry
    assert cv.grids((5, 5, 5)) == [(2, 2, 2), (4, 4, 4), (5, 5, 5), (6, 6, 6), (8, 8, 8), (10, 10, 10)]
    assert cv.grids((12, 12, 1)) == [(6, 6, 1), (9, 9, 1), (12, 12, 1), (15, 15, 1), (18, 18, 1), (24, 24, 1)]  # a slab
    assert cv.grids((2, 2, 2)) == [(1, 1, 1), (2, 2, 2), (3, 3, 3), (4, 4, 4)]  # repeats left out
    for wrong in ((0, 2, 2), (2, 2), None):
        with pytest.raises(ValueError):
            cv.grids(wrong)
    with pytest.raises(ValueError):
        cv.cutoffs(0.0)


def test_the_table_and_where_it_converges():
    # two atoms; energies per cell: the last is the reference
    energies = [-10.0, -10.1, -10.19, -10.1996, -10.2004, -10.2]
    pressures = [30.0, 12.0, 4.0, 2.2, 0.6, 0.0]
    points = [cv.Point(f'{20 + 10 * k} Ry', e, 2, p) for k, (e, p) in enumerate(zip(energies, pressures))]
    table = cv.rows(points)
    assert [round(r.delta, 3) for r in table] == [100.0, 50.0, 5.0, 0.2, -0.2, 0.0]  # meV per atom
    assert table[0].energy_per_atom == -5.0
    assert cv.converged(table) == 3  # 0.2 and −0.2 meV are inside 1 meV, 5 meV is not
    assert cv.converged(table, 'pressure', cv.TOLERANCE_KBAR) == 4  # the pressure — one value later
    lines = cv.summary(table)
    assert '50 Ry' in lines[0] and 'медленнее' in lines[1] and '60 Ry' in lines[1]
    # a point inside the tolerance followed by one outside does not count: converged means to the end
    jumpy = cv.rows([cv.Point(str(k), e, 1) for k, e in enumerate([-1.0, -1.0500, -1.0496, -1.0300, -1.0499, -1.05])])
    assert cv.converged(jumpy) == 4
    short = cv.rows([cv.Point(str(k), e, 1) for k, e in enumerate([-1.0, -1.02, -1.05])])
    assert cv.converged(short) is None and 'не сошлась' in cv.summary(short)[0]
    with pytest.raises(ValueError, match='трёх'):
        cv.rows(points[:2])
    assert cv.converged(cv.rows([cv.Point('a', -1.0, 1), cv.Point('b', -1.0, 1), cv.Point('c', -1.0, 1)]), 'pressure') is None


def _silicon():
    from tests.sextant.test_qe_inputs import silicon

    return silicon()


def test_the_inputs_of_the_two_series():
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    cut = qe_inputs.steps(_silicon(), qe_inputs.CUTOFF_TASK, pseudo, '/p')
    assert [name for name, _, _ in cut] == [f'cut{n}.in' for n in range(1, 7)]
    assert [re.search(r'ecutwfc = (\S+)', t).group(1) for _, _, t in cut] == ['20', '30', '40', '50', '60', '70']
    assert [re.search(r'ecutrho = (\S+)', t).group(1) for _, _, t in cut] == ['160', '240', '320', '400', '480', '560']
    assert {t.split('K_POINTS automatic')[1].strip() for _, _, t in cut} == {'5 5 5 0 0 0'}  # one grid for all
    grid = qe_inputs.steps(_silicon(), qe_inputs.KGRID_TASK, pseudo, '/p')
    assert [t.split('K_POINTS automatic')[1].split()[:3] for _, _, t in grid] == [
        ['2'] * 3, ['4'] * 3, ['5'] * 3, ['6'] * 3, ['8'] * 3, ['10'] * 3]
    assert {re.search(r'ecutwfc = (\S+)', t).group(1) for _, _, t in grid} == {'30'}
    assert all("calculation = 'scf'" in t for _, _, t in cut + grid)
    assert {qe_inputs.CUTOFF_TASK, qe_inputs.KGRID_TASK} <= set(qe_inputs.ALL_TASKS)
    own = qe_inputs.steps(_silicon(), qe_inputs.CUTOFF_TASK, pseudo, '/p', options=qe_inputs.Options(ecutwfc=45.0, ecutrho=360.0))
    assert [re.search(r'ecutwfc = (\S+)', t).group(1) for _, _, t in own][:2] == ['30', '40']  # around the setting, 50
    assert re.search(r'ecutrho = (\S+)', own[0][2]).group(1) == '240'  # the ratio of the setting, 8


def _points(name, labels):
    runs = qe.runs((DATA / name).read_text(encoding='utf-8'))
    assert len(runs) == len(labels)
    found = []
    for label, run in zip(labels, runs):
        r = qe.read(run)
        found.append(cv.Point(label, r.energy * RY, r.nat, r.pressures[-1] if r.pressures else None,
                              r.lowest - r.highest if r.lowest is not None and r.highest is not None else None))
    return found


def test_the_real_series_of_silicon():
    text = (DATA / 'si_cutoff_pw76.out').read_text(encoding='utf-8')
    printed = [float(e) for e in re.findall(r'^!\s+total energy\s+=\s+(-?[\d.]+) Ry', text, re.M)]
    assert printed == CUTOFF_ENERGIES and all(a > b for a, b in zip(printed, printed[1:]))  # variational: only down
    table = cv.rows(_points('si_cutoff_pw76.out', [f'{w} Ry' for w in (20, 30, 40, 50, 60, 70)]))
    assert [r.delta for r in table] == pytest.approx([1000 * (e - printed[-1]) * RY / 2 for e in printed], abs=1e-6)
    assert cv.converged(table) == CUTOFF_CONVERGED
    assert [r.pressure for r in table] == CUTOFF_PRESSURES
    grid = cv.rows(_points('si_kgrid_pw76.out', ['4 × 4 × 4', '7 × 7 × 7', '9 × 9 × 9', '11 × 11 × 11', '14 × 14 × 14', '18 × 18 × 18']))
    kprinted = [float(e) for e in re.findall(r'^!\s+total energy\s+=\s+(-?[\d.]+) Ry',
                                              (DATA / 'si_kgrid_pw76.out').read_text(encoding='utf-8'), re.M)]
    assert kprinted == KGRID_ENERGIES
    assert cv.converged(grid) == KGRID_CONVERGED and abs(grid[0].delta) > 20  # 4 × 4 × 4 is far off
    assert grid[KGRID_CONVERGED].label == '9 × 9 × 9'

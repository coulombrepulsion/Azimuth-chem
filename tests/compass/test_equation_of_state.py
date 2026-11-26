"""The Birch–Murnaghan equation of state (modules/compass/chemistry/equation_of_state.py).

Oracles: energies computed here from the Birch–Murnaghan formula typed in independently (Birch 1947, as in every
textbook) for parameters like silicon's — the fit must give the parameters back; the pressure of the fit against the
numerical derivative −dE/dV; a harmonic solid E = E₀ + ½ B (V − V₀)²/V₀ near V₀ — B₀ by hand; 1 eV/Å³ =
160.21766208 GPa (CODATA: e × 10³⁰ Pa); the volume of a scaled cubic cell.
"""

from dataclasses import dataclass

import numpy as np
import pytest

from modules.compass.chemistry import equation_of_state as eos

GPA = 160.21766208


def birch(v, e0, v0, b0_gpa, bp):
    b = b0_gpa / GPA
    eta = (v0 / v) ** (2 / 3)
    return e0 + 9 * v0 * b / 16 * ((eta - 1) ** 3 * bp + (eta - 1) ** 2 * (6 - 4 * eta))


def test_the_fit_gives_back_the_parameters():
    e0, v0, b0, bp = -215.6934, 40.89, 88.6, 4.31  # two atoms of silicon, PBE-like
    volumes = [v0 * f for f in eos.series()]
    found = eos.fit(volumes, [birch(v, e0, v0, b0, bp) for v in volumes])
    assert found.e0 == pytest.approx(e0, abs=1e-9) and found.v0 == pytest.approx(v0, rel=1e-9)
    assert found.b0 == pytest.approx(b0, rel=1e-7) and found.b0_prime == pytest.approx(bp, rel=1e-6)
    assert found.rms < 1e-10
    # a series off its centre, in any order, with a repeated point
    volumes = [44.0, 38.5, 41.0, 39.7, 42.6, 43.3, 40.2, 41.0]
    found = eos.fit(volumes, [birch(v, e0, v0, b0, bp) for v in volumes])
    assert (found.v0, found.b0, found.b0_prime) == pytest.approx((v0, b0, bp), rel=1e-6)
    assert len(found.volumes) == 7


def test_the_energy_and_the_pressure_of_the_fit():
    found = eos.Fit(-10.0, 20.0, 100.0, 4.0, 0.0, (), ())
    assert eos.energy(found, 20.0) == -10.0 and eos.pressure(found, 20.0) == 0.0
    for v in (18.5, 19.4, 21.0):
        h = 1e-4
        numerical = -(eos.energy(found, v + h) - eos.energy(found, v - h)) / (2 * h) * GPA
        assert eos.pressure(found, v) == pytest.approx(numerical, rel=1e-6)
        assert eos.energy(found, v) == pytest.approx(birch(v, -10.0, 20.0, 100.0, 4.0), abs=1e-12)
    assert eos.pressure(found, 19.0) > 0 > eos.pressure(found, 21.0)  # squeezed — a positive pressure


def test_a_harmonic_solid_by_hand():
    # E = E₀ + ½ k (V − V₀)², B₀ = V₀ k: k = 0.01 eV/Å⁶, V₀ = 30 Å³ → B₀ = 0.3 eV/Å³ = 48.07 GPa
    volumes = [30.0 * f for f in eos.series(9, 0.01)]
    found = eos.fit(volumes, [-5.0 + 0.5 * 0.01 * (v - 30.0) ** 2 for v in volumes])
    assert found.v0 == pytest.approx(30.0, rel=1e-6) and found.b0 == pytest.approx(0.3 * GPA, rel=2e-3)
    assert 0.3 * GPA == pytest.approx(48.065, abs=1e-3)


def test_noise_of_the_energies_moves_the_modulus_little():
    e0, v0, b0, bp = -215.6934, 40.89, 88.6, 4.31
    volumes = [v0 * f for f in eos.series()]
    noise = np.random.default_rng(7).normal(0.0, 1e-5, len(volumes))  # 1e-5 eV: a converged scf
    found = eos.fit(volumes, [birch(v, e0, v0, b0, bp) + n for v, n in zip(volumes, noise)])
    assert found.v0 == pytest.approx(v0, rel=1e-4) and found.b0 == pytest.approx(b0, rel=0.01)
    assert found.b0_prime == pytest.approx(bp, abs=0.3) and found.rms < 5e-5


def test_what_is_refused():
    e0, v0, b0, bp = -215.6934, 40.89, 88.6, 4.31
    with pytest.raises(ValueError, match='пяти'):
        eos.fit([39.0, 40.0, 41.0, 42.0], [1.0, 0.9, 0.95, 1.1])
    one_side = [v0 * f for f in (1.05, 1.07, 1.09, 1.11, 1.13)]  # all on the stretched side: the minimum is outside
    with pytest.raises(ValueError, match='вне'):
        eos.fit(one_side, [birch(v, e0, v0, b0, bp) for v in one_side])
    with pytest.raises(ValueError):
        eos.fit([38.0, 39.0, 40.0, 41.0, 42.0], [0.0, 1.0, 1.5, 1.0, 0.0])  # a maximum
    with pytest.raises(ValueError):
        eos.series(3)
    with pytest.raises(ValueError):
        eos.fit([38.0, 39.0, 40.0, 41.0, float('nan')], [0.0] * 5)


def test_the_series_and_the_scaled_crystal():
    assert eos.series() == pytest.approx((0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06))

    @dataclass(frozen=True)
    class Cell:
        a: float
        b: float
        c: float
        alpha: float = 90.0

    @dataclass(frozen=True)
    class Crystal:
        cell: Cell
        atoms: tuple = ()

    cube = Crystal(Cell(5.0, 5.0, 5.0), (('Si', (0.0, 0.0, 0.0)),))
    bigger = eos.scaled(cube, 1.06)
    assert bigger.cell.a * bigger.cell.b * bigger.cell.c == pytest.approx(125.0 * 1.06, rel=1e-12)
    assert bigger.cell.a == bigger.cell.c and bigger.cell.alpha == 90.0 and bigger.atoms == cube.atoms


def test_the_points_of_the_runs():
    @dataclass
    class Run:
        energy: float | None
        cell: tuple | None

    runs = [Run(-15.85, ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 2.5))), Run(None, ((1.0, 0, 0), (0, 1.0, 0), (0, 0, 1.0))),
            Run(-15.9, None), None]
    points = eos.points_of_runs(runs)
    assert points == [(pytest.approx(10.0), pytest.approx(-15.85 * 13.605693122994))]


def test_the_series_of_inputs_of_quantum_espresso():
    # «Уравнение состояния (ряд объёмов)»: seven inputs of pw.x; the volume of each by the determinant of its
    # CELL_PARAMETERS (computed here), the same atoms in fractions, one grid of k-points for all
    import re

    from modules.sextant import qe_inputs
    from tests.sextant.test_qe_inputs import silicon

    steps = qe_inputs.steps(silicon(), qe_inputs.EOS_TASK, {'Si': ('Si.upf', 30.0, 240.0)}, '/p')
    assert [(name, tool) for name, tool, _ in steps] == [(f'eos{n}.in', 'pw.x') for n in range(1, 8)]
    assert qe_inputs.EOS_TASK in qe_inputs.ALL_TASKS

    def volume(text):
        rows = re.search(r'CELL_PARAMETERS angstrom\n((?:.*\n){3})', text).group(1).splitlines()
        return abs(np.linalg.det(np.array([[float(x) for x in row.split()] for row in rows])))

    volumes = [volume(text) for _, _, text in steps]
    assert volumes[3] == pytest.approx(5.431 ** 3, rel=1e-7)
    assert [v / volumes[3] for v in volumes] == pytest.approx([0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06], rel=1e-7)
    positions = {text.split('ATOMIC_POSITIONS crystal')[1].split('K_POINTS')[0] for _, _, text in steps}
    grids = {text.split('K_POINTS automatic')[1].strip() for _, _, text in steps}
    assert len(positions) == 1 and grids == {'5 5 5 0 0 0'}
    assert all("calculation = 'relax'" in text for _, _, text in steps)
    hybrid = qe_inputs.steps(silicon(), qe_inputs.EOS_TASK, {'Si': ('Si.upf', 30.0, 240.0)}, '/p',
                             options=qe_inputs.Options(functional='hse'))
    assert all("calculation = 'scf'" in text for _, _, text in hybrid)  # no forces of a hybrid here
    # a cell so small that the grid by the spacing would change along the series keeps one grid
    from dataclasses import replace

    small = replace(silicon(), cell=replace(silicon().cell, a=5.03, b=5.03, c=5.03))
    grids = {text.split('K_POINTS automatic')[1].strip() for _, _, text in
             qe_inputs.steps(small, qe_inputs.EOS_TASK, {'Si': ('Si.upf', 30.0, 240.0)}, '/p')}
    assert len(grids) == 1


def test_a_real_run_of_pw_gives_a_point():
    # pw.x 7.6, silicon (tests/data/qe/si_scf_pw76.out): «! total energy» and the cell of the run
    from pathlib import Path

    from modules.spectrum.readers import qe

    text = (Path(__file__).resolve().parents[1] / 'data' / 'qe' / 'si_scf_pw76.out').read_text(encoding='utf-8')
    result = qe.read(text)
    (volume, energy), = eos.points_of_runs([result])
    assert energy == pytest.approx(result.energy * 13.605693122994, rel=1e-12)
    assert volume == pytest.approx(eos.volume_of(result.cell)) and 150.0 < volume < 170.0  # the cubic cell, 5.43–5.47 Å


def test_the_real_series_of_silicon():
    # pw.x 7.6, seven volumes (tests/data/qe/si_eos_pw76.out). Oracles: the «! total energy» lines and the «unit-cell
    # volume» lines of the output copied by hand (a.u.³ × 0.529177210903³ = Å³ — not the determinant the module takes);
    # the pressure pw.x prints changes its sign between the fifth and the sixth volume, so V₀ lies between them; the
    # PBE values of the literature for silicon, a₀ = 5.469 Å and B₀ = 88–89 GPa
    from pathlib import Path

    from modules.spectrum.readers import qe

    text = (Path(__file__).resolve().parents[1] / 'data' / 'qe' / 'si_eos_pw76.out').read_text(encoding='utf-8')
    points = eos.points_of_runs([qe.read(run) for run in qe.runs(text)])
    energies = [-22.83372303, -22.83649793, -22.83839394, -22.83949545, -22.83987597, -22.83961627, -22.83877497]
    volumes = [254.0410, 259.4462, 264.8513, 270.2564, 275.6615, 281.0667, 286.4718]
    assert [e for _, e in points] == pytest.approx([e * 13.605693122994 for e in energies], abs=1e-7)
    assert [v for v, _ in points] == pytest.approx([v * 0.529177210903 ** 3 for v in volumes], rel=5e-5)
    found = eos.fit([v for v, _ in points], [e for _, e in points])
    assert points[4][0] < found.v0 < points[5][0]
    assert (4 * found.v0) ** (1 / 3) == pytest.approx(5.469, abs=0.003)  # four primitive cells in the cubic one
    assert found.b0 == pytest.approx(88.8, abs=0.3) and 88.0 < found.b0 < 89.5
    assert found.b0_prime == pytest.approx(4.34, abs=0.05) and found.rms < 5e-5
    # the pressure of the fit against the pressures pw.x printed (kbar → GPa), within the noise of its stress
    printed = [87.85, 62.70, 40.05, 19.58, 1.06, -15.55, -30.53]
    for (volume, _), kbar in zip(points, printed):
        assert eos.pressure(found, volume) == pytest.approx(kbar / 10, abs=0.25)

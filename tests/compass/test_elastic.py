"""The elastic constants of a cubic crystal (modules/compass/chemistry/elastic.py; the task of qe_inputs and its
table in modules/compass/actions/qe_results.py).

Oracles. A model energy written here from the definition, E = E₀ + (V₀/2) Σ C_ij ε_i ε_j with C₁₁ = 300, C₁₂ = 100,
C₄₄ = 150 GPa (Voigt: ε₄ = 2ε_yz …) — the fit must give the three numbers back; by hand B = (300 + 200)/3 = 166.67,
A = 2·150/200 = 1.5. A strained cell by hand: the cube of 4 Å stretched by 1 % along x is 4.04 × 4 × 4 Å with right
angles; sheared by ε₆ = 0.02 its angle γ is 90° − 0.02 rad (to first order: cos γ = 2ε_xy / (1 + ε_xy²)).
"""

from math import acos, degrees

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr, elastic as el
from modules.sextant import qe_inputs


def model(eps, c11=300.0, c12=100.0, c44=150.0, volume=18.7, e0=-10.0):
    c = np.full((3, 3), c12 / el.GPA)
    np.fill_diagonal(c, c11 / el.GPA)
    voigt = np.array([eps[0, 0], eps[1, 1], eps[2, 2]])
    shear = np.array([2 * eps[1, 2], 2 * eps[0, 2], 2 * eps[0, 1]])
    return e0 + volume / 2 * (voigt @ c @ voigt + c44 / el.GPA * shear @ shear)


def cube(a=4.0):
    return cr.Crystal('cube', cr.Cell(a, a, a), (cr.Site('X1', 'Al', 0.0, 0.0, 0.0), cr.Site('X2', 'Al', 0.5, 0.5, 0.5)),
                      (cr.operation('x, y, z'),), 'P 1')


def test_the_constants_of_a_model_energy():
    assert el.plan()[0] == (None, 0.0) and len(el.plan()) == 19
    assert [k for k, _ in el.plan()[1:]] == ['c11'] * 6 + ['cp'] * 6 + ['c44'] * 6
    points = {kind: [(0.0, model(np.zeros((3, 3))))] for kind in el.KINDS}
    for kind, e in el.plan()[1:]:
        points[kind].append((e, model(el.matrix(kind, e))))
    found = el.fit(points, 18.7)
    assert (found.c11, found.c12, found.c44) == pytest.approx((300.0, 100.0, 150.0), abs=1e-6)
    assert found.bulk == pytest.approx(500.0 / 3) and found.anisotropy == pytest.approx(1.5) and el.stable(found)
    assert el.curve(found, 'c44', 0.01) == pytest.approx(0.5 * 150.0 / el.GPA * 1e-4)  # ½ C₄₄ e², eV/Å³
    text = ' '.join(el.lines(found))
    assert '300.0' in text and '166.7' in text and '1.50' in text and '-50.0' in text  # Cauchy: C₁₂ − C₄₄
    # an energy with a cubic term too (a stretch is not symmetric): the curvature at zero is still the constant
    skewed = {**points, 'c11': [(e, energy - 40.0 * e ** 3) for e, energy in points['c11']]}
    assert el.fit(skewed, 18.7).c11 == pytest.approx(300.0, abs=1e-6)
    unstable = {kind: [(e, model(el.matrix(kind, e) if e else np.zeros((3, 3)), c44=-20.0)) for e, _ in points[kind]]
                for kind in el.KINDS}
    broken = el.fit(unstable, 18.7)
    assert broken.c44 == pytest.approx(-20.0, abs=1e-6) and not el.stable(broken) and 'устойчивости' in ' '.join(el.lines(broken))
    with pytest.raises(ValueError, match='меньше пяти'):
        el.fit({**points, 'cp': points['cp'][:4]}, 18.7)
    with pytest.raises(ValueError, match='меньше пяти'):
        el.fit({**points, 'cp': points['cp'][1:]}, 18.7)  # without the unstrained cell
    with pytest.raises(ValueError, match='объём'):
        el.fit(points, 0.0)
    with pytest.raises(ValueError):
        el.matrix('c12', 0.01)


def test_a_strained_cell():
    rows = np.array(cube().cell.vectors(), dtype=float)
    stretched = el.deformed(cube(), rows, el.matrix('c11', 0.01))
    cell = stretched.cell
    assert (cell.a, cell.b, cell.c) == pytest.approx((4.04, 4.0, 4.0)) and (cell.alpha, cell.beta, cell.gamma) == pytest.approx((90, 90, 90))
    assert [a[1:4] for a in cr.unit_cell(stretched)] == [(0.0, 0.0, 0.0), (0.5, 0.5, 0.5)]  # the fractions are kept
    both = el.deformed(cube(), rows, el.matrix('cp', 0.01)).cell
    assert (both.a, both.b, both.c) == pytest.approx((4.04, 3.96, 4.0)) and both.volume() == pytest.approx(64 * (1 - 1e-4))
    sheared = el.deformed(cube(), rows, el.matrix('c44', 0.02)).cell
    assert sheared.gamma == pytest.approx(degrees(acos(2 * 0.01 / (1 + 0.01 ** 2)))) and sheared.gamma == pytest.approx(90 - degrees(0.02), abs=1e-3)
    assert sheared.a == pytest.approx(4.0 * (1 + 0.01 ** 2) ** 0.5) and (sheared.alpha, sheared.beta) == pytest.approx((90, 90))


def test_the_inputs_of_the_task():
    from tests.compass.test_layer import graphene
    from tests.sextant.test_qe_inputs import silicon

    pseudo = {'Si': ('Si.upf', 30.0, 240.0), 'C': ('C.upf', 45.0, 360.0)}
    conventional = silicon()
    primitive, basis = cr.primitive(conventional), cr.primitive_basis(conventional)
    found = qe_inputs.steps(primitive, qe_inputs.ELASTIC_TASK, pseudo, '/p', basis=basis, conventional=conventional)
    assert [name for name, _, _ in found] == [f'ela{n}.in' for n in range(1, 20)]
    assert all("calculation = 'relax'" in text for _, _, text in found)  # the atoms of silicon move under a shear
    assert len({text.split('K_POINTS automatic')[1].strip() for _, _, text in found}) == 1  # one grid for all

    def volume(text):
        rows = np.array([[float(v) for v in line.split()] for line in text.split('CELL_PARAMETERS angstrom')[1].splitlines()[1:4]])
        return abs(np.linalg.det(rows))

    v0 = volume(found[0][2])
    assert v0 == pytest.approx(5.431 ** 3 / 4)
    # ε₁ = e changes the volume by e; ε₁ = e, ε₂ = −e by −e²; a shear by −e²/4 (the strains act in the cubic frame)
    for (kind, e), (_, _, text) in zip(el.plan()[1:], found[1:]):
        change = volume(text) / v0 - 1
        assert change == pytest.approx({'c11': e, 'cp': -e * e, 'c44': -e * e / 4}[kind], abs=1e-7)  # the cell is written to 1e-8 Å
    with pytest.raises(ValueError, match='кубического'):
        qe_inputs.steps(graphene(), qe_inputs.ELASTIC_TASK, pseudo, '/p')
    assert qe_inputs.ELASTIC_TASK in qe_inputs.ALL_TASKS


def test_the_real_constants_of_magnesium_oxide(tmp_path):
    # MgO at the cell PBE gives (a = 4.2486 Å), pw.x 7.6 through the inputs of the task (tests/data/qe/README.md).
    # PBE in the literature: C₁₁ about 270–280, C₁₂ about 90, C₄₄ about 140–145 GPa; measured 297, 96 and 156 GPa
    from pathlib import Path
    from types import SimpleNamespace

    from modules.compass.actions import qe_results

    data = Path(__file__).resolve().parents[1] / 'data' / 'qe'
    (tmp_path / 'pw.out').write_text((data / 'mgo_elastic_pw76.out').read_text(encoding='utf-8'), encoding='utf-8')
    assert qe_results.elastic_data(SimpleNamespace(folder=tmp_path)) is None  # no plan beside the output
    (tmp_path / 'elastic.json').write_text((data / 'mgo_elastic.json').read_text(encoding='utf-8'), encoding='utf-8')
    panel = SimpleNamespace(folder=tmp_path)
    found, points = qe_results.elastic_data(panel)
    assert [len(points[kind]) for kind in el.KINDS] == [7, 7, 7] and found.volume == pytest.approx(4.2486 ** 3 / 4)
    assert (found.c11, found.c12, found.c44) == pytest.approx((276.3, 92.1, 143.2), abs=0.1)
    assert found.bulk == pytest.approx(153.5, abs=0.1) and found.anisotropy == pytest.approx(1.55, abs=0.01) and el.stable(found)
    assert found.c12 - found.c44 == pytest.approx(-51.1, abs=0.2)  # the Cauchy relation does not hold: non-central forces
    assert all(rms < 1e-6 for _, rms in found.curves.values())  # the cubic fits the seven points to 1e-6 eV/Å³
    # a stretch costs more than the same squeeze gains nothing: every strained cell is above the unstrained one
    zero = points['c11'][0][1]
    assert all(energy > zero for kind in el.KINDS for e, energy in points[kind] if e)
    lines = qe_results.elastic_lines(panel, (found, points))
    assert '276.3' in lines[0] and '153.5' in lines[1]
    (tmp_path / 'elastic.json').write_text('{"plan": [[null, 0.0]], "volume": 19.17}', encoding='utf-8')
    broken = qe_results.elastic_data(panel)
    assert broken[0] is None and 'меньше пяти' in qe_results.elastic_lines(panel, broken)[0]

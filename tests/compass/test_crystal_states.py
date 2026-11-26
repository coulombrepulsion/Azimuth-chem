"""The series of magnetic orders and of U of a crystal (qe_inputs.MAGNETIC_TASK, HUBBARD_TASK; the table of
modules/compass/actions/qe_results.py; the magnetization read by modules/spectrum/readers/qe.py).

Oracles: the numbers pw.x 7.6 printed for NiO (tests/data/qe/README.md), copied here by hand from the outputs — the
energies «!», the lines «total magnetization», «absolute magnetization», the table «Magnetic moment per site» and
«highest occupied, lowest unoccupied level»; the differences of the energies computed here (1 Ry = 13.605693 eV).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.sextant import hubbard, qe_inputs
from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'
RY = 13.605693122994
# no spin, ferromagnetic, antiferromagnetic (AFM-II): Ry per cell of two formula units
MAGNETIC = [-769.73287092, -769.74215935, -769.78059614]


def _nickel_oxide(tmp_path):
    from tests.sextant.test_hubbard import nickel_oxide

    (tmp_path / 'Ni.upf').write_text('<PP_HEADER z_valence="18.0" />', encoding='utf-8')
    (tmp_path / 'O.upf').write_text('<PP_HEADER z_valence="6.0" />', encoding='utf-8')
    return nickel_oxide(), {'Ni': ('Ni.upf', 45.0, 360.0), 'O': ('O.upf', 50.0, 400.0)}


def test_the_inputs_of_the_series_of_u(tmp_path):
    crystal, pseudo = _nickel_oxide(tmp_path)
    with pytest.raises(ValueError, match='DFT\\+U'):
        qe_inputs.steps(crystal, qe_inputs.HUBBARD_TASK, pseudo, tmp_path)
    found = qe_inputs.steps(crystal, qe_inputs.HUBBARD_TASK, pseudo, tmp_path,
                            options=qe_inputs.Options(hubbard=hubbard.parse('Ni 6')))
    assert [(name, tool) for name, tool, _ in found] == [(f'hub{n}.in', 'pw.x') for n in range(1, 6)]
    assert 'HUBBARD' not in found[0][2]  # U = 0 is the plain functional
    assert [text.split('HUBBARD (ortho-atomic)')[1].split()[:3] for _, _, text in found[1:]] == [
        ['U', 'Ni-3d', u] for u in ('2', '4', '6', '8')]
    # 4 Ni × 18 + 4 O × 6 = 96 electrons: 48 occupied bands and ⅛ more (6) empty ones for the gap
    assert all('nbnd = 54' in text and "calculation = 'scf'" in text for _, _, text in found)


def test_the_inputs_of_the_magnetic_orders(tmp_path):
    crystal, pseudo = _nickel_oxide(tmp_path)
    with pytest.raises(ValueError, match='антиферромагнитный'):
        qe_inputs.steps(crystal, qe_inputs.MAGNETIC_TASK, pseudo, tmp_path)
    signs = (1, 1, -1, -1, 0, 0, 0, 0)  # two Ni up, two down (layers along c), the oxygens none
    plain, ferro, anti = (text for _, _, text in qe_inputs.steps(
        crystal, qe_inputs.MAGNETIC_TASK, pseudo, tmp_path, options=qe_inputs.Options(magnetic=signs)))
    assert 'nspin' not in plain and 'starting_magnetization' not in plain
    assert 'nspin = 2' in ferro and 'Ni1' not in ferro and 'tot_magnetization' not in ferro
    assert 'nspin = 2' in anti and 'Ni1' in anti and 'Ni2' in anti and 'tot_magnetization = 0' in anti
    assert {qe_inputs.MAGNETIC_TASK, qe_inputs.HUBBARD_TASK} <= set(qe_inputs.ALL_TASKS)


def test_the_magnetization_pw_prints():
    plain, ferro, anti = (qe.read(run) for run in qe.runs((DATA / 'nio_magnetic_pw76.out').read_text(encoding='utf-8')))
    assert [r.energy for r in (plain, ferro, anti)] == MAGNETIC
    assert plain.magnetization is None and plain.moments == ()
    assert (ferro.magnetization, ferro.absolute_magnetization) == (2.91, 2.94)
    assert ferro.moments == ((1, 1.2025), (2, 1.2025), (3, 0.2144), (4, 0.2144))
    assert (anti.magnetization, anti.absolute_magnetization) == (0.0, 2.96)
    assert anti.moments == ((1, 1.3348), (2, -1.3348), (3, 0.0), (4, 0.0))
    assert (anti.highest, anti.lowest) == (13.8053, 14.6176)


def _folder(tmp_path, kind, output, count):
    for n in range(1, count + 1):
        (tmp_path / f'{kind}{n}.in').write_text((DATA / f'nio_{output}_{kind}{n}.in').read_text(encoding='utf-8'),
                                                encoding='utf-8')
    (tmp_path / 'pw.out').write_text((DATA / f'nio_{output}_pw76.out').read_text(encoding='utf-8'), encoding='utf-8')
    return SimpleNamespace(folder=tmp_path)


def test_the_table_of_the_magnetic_orders(tmp_path):
    from modules.compass.actions import qe_results

    kind, rows = qe_results.states_data(_folder(tmp_path, 'mag', 'magnetic', 3))
    assert kind == 'mag' and [row[0] for row in rows] == list(qe_inputs.MAGNETIC_STATES)
    assert [row[1] for row in rows] == pytest.approx([e * RY for e in MAGNETIC], abs=1e-9)
    # the antiferromagnetic state is the lowest: 0.523 eV under the ferromagnetic one, 0.649 eV under the one without spin
    assert rows[1][1] - rows[2][1] == pytest.approx((MAGNETIC[1] - MAGNETIC[2]) * RY) == pytest.approx(0.5230, abs=5e-4)
    assert rows[0][1] - rows[2][1] == pytest.approx(0.6493, abs=5e-4)
    assert rows[0][2] < 0 and rows[0][3] is None  # without spin the bands overlap: a metal
    assert rows[1][2] is None and rows[1][3] == 1.2025 and rows[1][4] == 2.94  # smearing: no levels of the edges
    assert rows[2][2] == pytest.approx(14.6176 - 13.8053) and rows[2][3] == 1.3348 and rows[2][4] == 2.96
    html = qe_results.states_table(None, (kind, rows))
    assert html.count('<tr>') == 4 and '>&nbsp;0.0&nbsp;<' in html and '523.' in html and '649.' in html
    assert 'металл' in html and '0.81' in html and '1.33' in html
    assert qe_results.states_data(SimpleNamespace(folder=tmp_path / 'none')) is None


def test_the_lines_of_the_summary():
    from modules.compass.actions import qe_results

    runs = qe.runs((DATA / 'nio_magnetic_pw76.out').read_text(encoding='utf-8'))
    assert qe_results.magnetic_lines(qe.read(runs[0])) == []
    lines = qe_results.magnetic_lines(qe.read(runs[2]))
    assert '0.00' in lines[0] and '2.96' in lines[0]
    assert '1 +1.33' in lines[1] and '2 -1.33' in lines[1] and '3 ' not in lines[1].split(':')[1]  # oxygen has none


# U = 0, 2, 4, 6, 8 eV on Ni 3d, the antiferromagnetic cell: what pw.x printed
HUBBARD_GAPS = [14.6176 - 13.8053, 15.1039 - 13.2691, 15.6634 - 13.0104, 16.0052 - 12.8918, 16.0365 - 12.8435]
HUBBARD_MOMENTS = [1.3348, 1.5115, 1.6070, 1.6751, 1.7278]
HUBBARD_ABSOLUTE = [2.96, 3.32, 3.50, 3.62, 3.71]


def test_the_table_of_the_series_of_u(tmp_path):
    from modules.compass.actions import qe_results

    kind, rows = qe_results.states_data(_folder(tmp_path, 'hub', 'hubbard', 5))
    assert kind == 'hub' and [row[0].split(' эВ')[0] for row in rows] == ['U = 0', 'U = 2', 'U = 4', 'U = 6', 'U = 8']
    assert [row[2] for row in rows] == pytest.approx(HUBBARD_GAPS, abs=1e-9)
    assert [row[3] for row in rows] == HUBBARD_MOMENTS and [row[4] for row in rows] == HUBBARD_ABSOLUTE
    # U opens the gap and localizes the moment: both grow along the series
    assert all(a < b for a, b in zip(HUBBARD_GAPS, HUBBARD_GAPS[1:])) and HUBBARD_GAPS[3] == pytest.approx(3.1134)
    html = qe_results.states_table(None, (kind, rows))
    assert html.count('<tr>') == 6 and 'ΔE' not in html and '3.11' in html and '1.68' in html and 'не сравнивают' in html
    # U = 0 of this series is the antiferromagnetic state of the other one: the same energy to 1e-8 Ry
    first = qe.read(qe.runs((DATA / 'nio_hubbard_pw76.out').read_text(encoding='utf-8'))[0])
    assert first.energy == MAGNETIC[2]

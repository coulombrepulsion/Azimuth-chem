"""The frequencies at Γ of Quantum ESPRESSO (task «Частоты (точка Γ)»: pw.x, ph.x, dynmat.x) — the inputs
(modules/sextant/qe_inputs.py), the reading (modules/spectrum/readers/qe.py: phonons) and the modes on the model of a
crystal (modules/compass/actions/crystal_dynamics.py).

Oracles — real runs of QE 7.6 (tests/data/qe/README.md): silicon — the optical triplet at 514.0 cm⁻¹ with no IR
activity (a non-polar crystal; experiment 520 cm⁻¹), ε∞ 13.557; rock salt — the TO triplet at 165.37 cm⁻¹, IR activity
1.9996 (D/Å)²/amu, ε∞ 2.511, Z*(Na) = −Z*(Cl) = 1.0994 after the sum rule. The factor of the IR activity, N_A/(12 ε₀ c²)
(D/Å)²/amu → km/mol, from CODATA 2018 by hand: 42.2561.
"""

from pathlib import Path
import shutil
from types import SimpleNamespace

import pytest

from modules.compass.chemistry import crystal as cr
from modules.sextant import qe_inputs
from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'


def run_folder(tmp_path, name):
    shutil.copy(DATA / f'{name}_phonon_gamma.mold', tmp_path / qe_inputs.PHONON_FILE)
    shutil.copy(DATA / f'{name}_phonon_gamma_pw76.out', tmp_path / 'pw.out')
    shutil.copy(DATA / f'{name}_phonon_gamma_scf.in', tmp_path / 'scf.in')
    return tmp_path


def test_the_steps_of_the_phonons():
    from tests.sextant.test_qe_inputs import silicon

    prim = cr.primitive(silicon())
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    steps = qe_inputs.steps(prim, qe_inputs.PHONON_TASK, pseudo, '.')
    assert [s[:2] for s in steps] == [('scf.in', 'pw.x'), ('ph.in', 'ph.x'), ('dynmat.in', 'dynmat.x')]
    assert 'epsil = .true.' in steps[1][2] and steps[1][2].rstrip().endswith('0.0 0.0 0.0')  # an insulator: ε, Z*
    assert f"filmol = '{qe_inputs.PHONON_FILE}'" in steps[2][2] and "asr = 'crystal'" in steps[2][2]
    assert qe_inputs.PHONON_TASK in qe_inputs.ALL_TASKS and 'ph.x' in qe_inputs.PARALLEL
    metal = qe_inputs.steps(prim, qe_inputs.PHONON_TASK, pseudo, '.', options=qe_inputs.Options(occupations='smearing'))
    assert 'epsil = .false.' in metal[1][2]  # ph.x stops on a metal asked for ε
    for options in (qe_inputs.Options(functional='hse'), qe_inputs.Options(vdw='d3bj')):
        with pytest.raises(ValueError):
            qe_inputs.steps(prim, qe_inputs.PHONON_TASK, pseudo, '.', options=options)
    assert qe_inputs.steps(prim, qe_inputs.PHONON_TASK, pseudo, '.', options=qe_inputs.Options(vdw='d2'))


def test_the_phonons_of_silicon_and_rock_salt(tmp_path):
    assert qe.IR_KM_MOL == pytest.approx(42.2561, abs=1e-4)
    (tmp_path / 'si').mkdir()
    si = qe.phonons(run_folder(tmp_path / 'si', 'si'))
    assert [round(m.frequency, 2) for m in si.modes] == [0.0, 0.0, 0.0, 513.96, 513.96, 514.03]
    assert all(m.intensity == 0 for m in si.modes) and si.epsilon[0][0] == pytest.approx(13.556780951)
    assert [s for s, _ in si.atoms] == ['Si', 'Si'] and si.atoms[1][1] == pytest.approx((1.92015, 1.10860, 0.78390), abs=1e-4)
    (tmp_path / 'nacl').mkdir()
    nacl = qe.phonons(run_folder(tmp_path / 'nacl', 'nacl'))
    to = [m for m in nacl.modes if m.frequency > 100]
    assert len(to) == 3 and all(m.frequency == pytest.approx(165.37) for m in to)
    assert to[0].intensity == pytest.approx(1.9996 * 42.2561, rel=1e-4)  # 84.50 km/mol
    assert nacl.born == [(1, 'Na', pytest.approx(1.0994)), (2, 'Cl', pytest.approx(-1.0994))]
    assert qe.input_cell(tmp_path / 'nacl')[1] == pytest.approx((1.99405, 3.45379591, 0.0))
    assert qe.phonons(tmp_path) is None  # no file of dynmat.x


def test_the_modes_of_a_qe_run_go_to_the_model(tmp_path):
    from modules.compass.actions import crystal_dynamics

    run = SimpleNamespace(program='qe', folder=run_folder(tmp_path, 'nacl'))
    atoms, modes, rows = crystal_dynamics.read_modes(run)
    assert len(atoms) == 2 and len(modes) == 6 and rows.shape == (3, 3)


def test_the_summary_of_the_phonons(tmp_path):
    from modules.compass.actions.qe_common import phonon_lines

    lines = phonon_lines(qe.phonons(run_folder(tmp_path, 'nacl')))
    assert lines[0] == 'Частоты в точке Γ: 3 оптических мод, от 165.4 до 165.4 см⁻¹'
    assert lines[1].startswith('ИК-активных мод: 3; самая сильная — 165.4 см⁻¹, 84.5 км/моль')
    assert lines[2].endswith('2.511') and not any('Мнимых' in x for x in lines)


def test_ph_x_runs_in_parallel_on_a_server():
    from modules.sextant import cluster

    body = '\n'.join(cluster.qe_lines(4, (('scf.in', 'pw.x'), ('ph.in', 'ph.x'), ('dynmat.in', 'dynmat.x'))))
    ph = next(line for line in body.splitlines() if 'ph.in' in line)
    dyn = next(line for line in body.splitlines() if 'dynmat.in' in line)
    assert '$RUN' in ph and '$RUN' not in dyn


def test_the_steps_of_the_phonon_branches():
    from tests.sextant.test_qe_inputs import silicon

    conventional = silicon()
    prim = cr.primitive(conventional)
    pseudo = {'Si': ('Si.upf', 30.0, 240.0)}
    steps = qe_inputs.steps(prim, qe_inputs.DISPERSION_TASK, pseudo, '.', basis=cr.primitive_basis(conventional),
                            conventional=conventional)
    assert [s[:2] for s in steps] == [('scf.in', 'pw.x'), ('ph.in', 'ph.x'), ('q2r.in', 'q2r.x'),
                                      ('matdyn.in', 'matdyn.x'), ('phdos.in', 'matdyn.x')]
    # ph.x stopped on the operations with fractional translations of Fd-3m on a grid of q (QE 7.6, the owner's Mac)
    assert 'force_symmorphic = .true.' in steps[0][2]
    ph = steps[1][2]
    assert 'ldisp = .true.' in ph and 'nq1 = 4' in ph and 'epsil = .true.' in ph
    assert all(2 <= n <= qe_inputs.Q_MAX for n in qe_inputs.qgrid(prim.cell))
    path = steps[3][2].splitlines()
    count = int(path[path.index('/') + 1])
    assert count == len(path) - path.index('/') - 2 > 100 and 'q_in_cryst_coord = .true.' in steps[3][2]
    assert f"fldos = '{qe_inputs.PHDOS_FILE}'" in steps[4][2] and 'dos = .true.' in steps[4][2]
    assert qe_inputs.DISPERSION_TASK in qe_inputs.ALL_TASKS


def test_the_branches_and_the_density_of_states_of_rock_salt(tmp_path):
    import json

    from modules.compass.actions.qe_window import QePanel

    branches = qe.read_branches((DATA / 'nacl_dispersion.freq').read_text(encoding='utf-8'))
    path = json.loads((DATA / 'nacl_dispersion_path.json').read_text(encoding='utf-8'))
    assert len(branches) == len(path['x']) == 289 and all(len(row) == 6 for row in branches)
    assert branches[0][3:] == [165.4046, 165.411, 255.4121]  # Γ: TO, TO, LO (the LO–TO splitting)
    assert max(max(row) for row in branches) == pytest.approx(255.41, abs=0.01)
    assert [round(v, 4) for v in branches[1][:3]] == [3.2382, 3.2725, 6.8487]  # the acoustic ones rise from Γ
    nu, g = qe.read_phdos((DATA / 'nacl_dispersion.phdos').read_text(encoding='utf-8'))
    assert len(nu) == len(g) == 257 and nu[1] == pytest.approx(1.0, abs=1e-4) and max(g) > 0
    assert qe.read_branches('no header') == []
    for name, target in (('nacl_dispersion.freq', qe_inputs.FREQ_FILE), ('nacl_dispersion.phdos', qe_inputs.PHDOS_FILE),
                         ('nacl_dispersion_path.json', 'path.json')):
        shutil.copy(DATA / name, tmp_path / target)
    found = QePanel.phonon_data(SimpleNamespace(folder=tmp_path))
    assert found is not None and len(found[0]) == 289 and len(found[2][0]) == 257


def test_the_branches_of_silicon_with_the_operations_of_fractional_translations_dropped():
    import json

    assert 'force_symmorphic = .true.' in (DATA / 'si_dispersion_q222_scf.in').read_text(encoding='utf-8')
    branches = qe.read_branches((DATA / 'si_dispersion_q222.freq').read_text(encoding='utf-8'))
    path = json.loads((DATA / 'si_dispersion_q222_path.json').read_text(encoding='utf-8'))

    def at(label):
        x = next(x for x, name in path['ticks'] if name == label)
        return branches[min(range(len(path['x'])), key=lambda k: abs(path['x'][k] - x))]

    assert at('Γ')[3:] == pytest.approx([514.41] * 3, abs=0.01)
    assert at('X') == pytest.approx([141.63, 141.65, 410.08, 410.09, 461.79, 461.80], abs=0.01)
    assert min(min(row) for row in branches) > -1  # no imaginary branch

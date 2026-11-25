"""The scenarios T01–T04 of docs/architecture/PROJECT_RUNTIME_GUIDE.md §13 through the window — as the user
does them (the same rules at the level of the session: tests/runtime/test_runtime_session.py).

Oracles: the rules of the guide §1 — a file opened is one new project named after the file, its molecules in the
order of the file with ids kept from opening to opening; files added to the tab extend its project, its molecules and
their history stay, no new tab; the first molecule drawn survives the exit as a draft in the projects folder (the
owner, «черновик при выходе», «с пометкой «черновик»»); an edit not saved is what the calculation and the
export get, the molecules of another project never.
"""

from pathlib import Path

import pytest
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QMessageBox

from azimuth import projects
from azimuth.core import Calculation, Molecule, read_xyz
from tests.projects.test_projects import app, window  # noqa: F401 — isolated Qt fixtures

COUNT = 44
EDITED_X = 1.25


def empty(window):
    window.load_molecule(Molecule('', (), ()), record=False)
    window.dirty = False


def h2_record(name, d=0.74):
    return (f'{name}\n  Azimuth\n\n  2  1  0  0  0  0  0  0  0  0999 V2000\n'
            '    0.0000    0.0000    0.0000 H   0  0  0  0  0  0  0  0  0  0  0  0\n'
            f'    0.0000    0.0000    {d:.4f} H   0  0  0  0  0  0  0  0  0  0  0  0\n'
            '  1  2  1  0  0  0  0\nM  END\n$$$$\n')


def sdf(path, names):
    path.write_text(''.join(h2_record(n, 0.70 + 0.001 * k) for k, n in enumerate(names)), encoding='utf-8')
    return path


def xyz_set(path, names):
    """Frames of different molecules (H2 and HF in turn) — a set of structures, not a trajectory."""
    frames = [f'2\n{n}\nH 0 0 0\n{"H" if k % 2 == 0 else "F"} 0 0 {0.74 if k % 2 == 0 else 0.92}\n'
              for k, n in enumerate(names)]
    path.write_text(''.join(frames), encoding='utf-8')
    return path


def names_of(path):
    return [e['name'] for e in projects.Project.load(path).molecules]


def ids_of(path):
    return [e['id'] for e in projects.Project.load(path).molecules]


@pytest.mark.parametrize('kind', ['sdf', 'xyz'])
def test_t01_one_file_of_44_structures_opens_as_one_project_with_its_name_order_and_ids(window, tmp_path, kind):
    empty(window)
    names = [f'ligand {k:02d}' for k in range(1, COUNT + 1)]
    source = (sdf if kind == 'sdf' else xyz_set)(tmp_path / f'Cs_full.{kind}', names)
    before = len(window.project_sessions)
    # Act
    window.opening_tool.open_path(source)
    # Assert: one new project, the name of the file, the order of the file, its own ids
    path = window.research_path()
    assert len(window.project_sessions) == before + 1
    assert projects.Project.load(path).data['name'] == 'Cs_full'
    assert names_of(path) == names
    ids = ids_of(path)
    assert len(ids) == len(set(ids)) == COUNT
    assert window.project_molecules.rowCount() == COUNT
    # Act: the project saved (a file only looked at leaves no project), the tab closed, the project opened
    # again (as after a restart)
    window.save_project_tab(name='Cs_full')
    window.file_tool.close_current_tab()
    window.open_project_path(str(path))
    # Assert: the same ids in the same order
    assert window.research_path() == path and ids_of(path) == ids and names_of(path) == names


def test_t01_a_trajectory_stays_the_steps_of_the_drawer(window, tmp_path):
    # frames of one molecule (an optimization, a dynamics) are not a set of structures
    trajectory = tmp_path / 'steps.xyz'
    trajectory.write_text(''.join(f'2\nstep {k}\nH 0 0 0\nH 0 0 {0.70 + 0.01 * k}\n' for k in range(5)), encoding='utf-8')
    assert not window.opening_tool.opens_as_project(str(trajectory))
    assert window.opening_tool.opens_as_project(str(xyz_set(tmp_path / 'set.xyz', ['a', 'b'])))


def test_t02_files_added_to_the_tab_keep_its_molecules_and_their_history(window, tmp_path):
    empty(window)
    window.opening_tool.open_path(sdf(tmp_path / 'pair.sdf', ['a', 'b']))
    path = window.research_path()
    first = ids_of(path)
    with projects.edit(path) as project:  # a calculation of «a» is in its history
        molecule, calc = project.read_structure(project.molecules[0]['structure'])
        project.record(first[0], 'attempt-1', molecule, calc, 'orca', 'running')
    tabs = len(window.project_sessions)
    added = [tmp_path / 'c.xyz', tmp_path / 'd.xyz']
    for item, symbol in zip(added, ('F', 'Cl')):
        item.write_text(f'2\n{item.stem}\nH 0 0 0\n{symbol} 0 0 1.0\n', encoding='utf-8')
    # Act: dropped onto the window (the same as «Добавить молекулы…»)
    window.view_tool.drop_paths(added)
    # Assert: the same tab and project, the molecules before first and kept with their attempt, the name kept
    assert len(window.project_sessions) == tabs and window.research_path() == path
    ids = ids_of(path)
    assert ids[:2] == first and len(ids) == 4 and names_of(path) == ['a', 'b', 'c', 'd']
    entry = projects.Project.load(path).entry(first[0])
    assert [a['id'] for a in entry['attempts']] == ['attempt-1']
    assert projects.Project.load(path).data['name'] == 'pair'


def test_t03_the_first_molecule_drawn_survives_the_exit_as_a_draft(window, tmp_path, monkeypatch):
    from azimuth.app import Studio

    empty(window)
    assert window.research_path() is None  # the first empty tab: no project, no folder
    drawn = read_xyz(f'3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 {EDITED_X} 0\n')
    window.load_molecule(drawn)
    window.dirty = True
    asked = []

    def answer(parent, title, text, *rest, **kw):
        asked.append(text)
        return QMessageBox.StandardButton.Discard
    monkeypatch.setattr(QMessageBox, 'question', answer)
    # Act: the program closed, «Не сохранять»
    event = QCloseEvent()
    window.closeEvent(event)
    # Assert: the exit said so; a draft in the projects folder with the molecule as drawn; it is the recent file
    assert event.isAccepted()
    assert asked and 'останется черновиком' in asked[0]
    path = Path(window.recent('molecule'))
    assert path.name == projects.MANIFEST and Path(window.projects_root()).resolve() in path.resolve().parents
    project = projects.Project.load(path)
    assert project.data['draft'] and len(project.molecules) == 1
    molecule, _ = project.read_structure(project.molecules[0]['structure'])
    assert molecule.formula == drawn.formula and molecule.atoms[2].y == pytest.approx(EDITED_X)
    assert projects.display_name(path).endswith('· черновик')
    # Act: the program started again — the draft opens with its molecule
    again = Studio(example=False, probe_machine=False)
    try:
        again.unfinished.timer.stop()
        again.open_project_path(str(path))
        assert again.research_path() == path.resolve() or again.research_path() == path
        assert again.own_molecule().atoms[2].y == pytest.approx(EDITED_X)
    finally:
        again.dirty = False
        for document in again.all_documents():
            document.dirty = False
        again.close()
        again.deleteLater()


def test_t03_a_molecule_saved_to_a_file_or_unchanged_is_not_a_draft(window):
    empty(window)
    window.load_molecule(read_xyz('1\nHe\nHe 0 0 0\n'))
    window.dirty = False  # opened, not edited: nothing to keep
    assert window.loose_drawn_documents() == []
    window.dirty = True
    window.project_path = Path('/tmp/own.qcc')  # a file of its own
    assert window.loose_drawn_documents() == []
    window.project_path = None
    assert window.loose_drawn_documents() == [window.document()]
    window.dirty = False


def test_t03_the_exit_of_a_window_browsing_steps_asks_nothing(window, monkeypatch):
    # finding the drawn molecules does not leave a trajectory being browsed (that put its own structure back on the
    # model — an edit — and the exit asked «Несохранённый проект» of a window with nothing changed)
    empty(window)
    window.load_molecule(read_xyz('1\nHe\nHe 0 0 0\n'))
    window.trajectory_tool.enter_trajectory()
    window.trajectory_tool.show_molecule(read_xyz('1\nNe\nNe 0 0 0\n'))
    window.dirty = False
    for document in window.all_documents():
        document.dirty = False
    asked = []
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: asked.append(a) or QMessageBox.StandardButton.Cancel)
    event = QCloseEvent()
    window.closeEvent(event)
    assert event.isAccepted() and not asked


def test_t04_an_edit_not_saved_is_what_the_calculation_gets_and_another_project_is_not(window, tmp_path, monkeypatch):
    from modules.sextant import batch_retry

    empty(window)
    window.opening_tool.open_path(sdf(tmp_path / 'a.sdf', ['a1', 'a2']))
    a = window.research_path()
    window.opening_tool.open_path(sdf(tmp_path / 'b.sdf', ['b1']))
    b = window.research_path()
    assert a != b
    window.activate_project_tab(window.project_sessions.index(a))
    assert window.research_path() == a
    window.open_project_molecule(ids_of(a)[0], stay=True)
    # Act: the coordinates changed in the table, nothing saved
    window.table.item(0, 1).setText(str(EDITED_X))
    # Assert: a single calculation is written for the edited structure
    assert window.calculation_molecule().atoms[0].x == pytest.approx(EDITED_X)
    # Act: the calculations of the project prepared at once
    seen = []

    class Dialog:
        def setWindowTitle(self, title):
            pass

        def show(self):
            pass

    def capture(owner, parent, indices):
        seen.append(parent)
        return Dialog()
    monkeypatch.setattr(batch_retry, 'retry_dialog', capture)
    window.prepare_project_calculations(ids_of(a))
    # Assert: the edit, and only the molecules of this project
    (parent,) = seen
    assert [item.name for item in parent.items] == ['a1', 'a2']
    assert parent.items[0].molecule.atoms[0].x == pytest.approx(EDITED_X)
    assert not any(item.name == 'b1' for item in parent.items)
    assert len(ids_of(b)) == 1 and names_of(b) == ['b']  # one record: named after its file (§1)

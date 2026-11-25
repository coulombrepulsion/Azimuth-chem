"""Project-scoped export and tab commands, including edits not yet saved to project.qcc."""
import pytest

from azimuth import projects
from azimuth.core import Molecule, read_xyz
from modules.compass.chemistry import formats
from tests.projects.test_projects import app, window  # noqa: F401 — isolated Qt fixtures

HELIUM, NEON = 'He', 'Ne'
EDITED_X = 1.25
ONE_PROJECT = 1


def files(tmp_path):
    paths = []
    for symbol in (HELIUM, NEON):
        path = tmp_path / f'{symbol}.xyz'
        path.write_text(f'1\n{symbol}\n{symbol} 0 0 0\n', encoding='utf-8')
        paths.append(path)
    return paths


def empty(window):
    window.load_molecule(Molecule('', (), ()), record=False)
    window.dirty = False


@pytest.mark.parametrize('close_other', [False, True])
def test_exports_only_active_project_when_another_project_was_open(window, tmp_path, close_other):
    # Arrange
    empty(window)
    first, second = files(tmp_path)
    window.opening_tool.open_path(first)
    window.opening_tool.open_path(second)
    if close_other:
        window.close_project_tab(0)
    target = tmp_path / 'export.xyz'
    # Act
    window.file_tool.save_batch('xyz-one', path=target)
    # Assert
    exported = formats.read_xyz_frames(target.read_text())
    assert [m.formula for m in exported] == [NEON]


@pytest.mark.parametrize('switch_molecule', [False, True])
@pytest.mark.parametrize('kind', ['xyz-one', 'sdf-one'])
def test_exports_latest_coordinates_when_project_has_unsaved_edits(window, tmp_path, switch_molecule, kind):
    # Arrange
    empty(window)
    window.open_files_project(files(tmp_path))
    path = window.research_path()
    before = path.read_bytes()
    window.table.item(0, 1).setText(str(EDITED_X))
    if switch_molecule:
        ident = projects.Project.load(path).molecules[1]['id']
        window.open_project_molecule(ident, stay=True)
    target = tmp_path / ('export.xyz' if kind == 'xyz-one' else 'export.sdf')
    # Act
    window.file_tool.save_batch(kind, path=target)
    # Assert
    read = formats.read_xyz_frames if kind == 'xyz-one' else formats.read_sdf_records
    exported = read(target.read_text())
    assert [m.formula for m in exported] == [HELIUM, NEON]
    assert exported[0].atoms[0].x == pytest.approx(EDITED_X)
    assert path.read_bytes() == before  # export does not silently save the project


def test_closes_project_and_preserves_edits_when_close_tab_command_runs(window, tmp_path):
    # Arrange
    empty(window)
    window.open_files_project(files(tmp_path))
    path = window.research_path()
    window.table.item(0, 1).setText(str(EDITED_X))
    # Act
    closed = window.file_tool.close_current_tab()
    # Assert
    assert closed
    assert window.research_path() is None
    assert not window.molecule.atoms
    assert window.file_tool.batch_structures() == []
    saved = projects.Project.load(path)
    molecule, _ = saved.read_structure(saved.molecules[0]['structure'])
    assert molecule.atoms[0].x == pytest.approx(EDITED_X)
    assert not window.project_sessions


def test_keeps_active_project_when_close_other_tabs_command_runs(window, tmp_path):
    # Arrange
    empty(window)
    first, second = files(tmp_path)
    window.opening_tool.open_path(first)
    other = window.research_path()
    window.opening_tool.open_path(second)
    keep = window.research_path()
    window.table.item(0, 1).setText(str(EDITED_X))
    # Act
    closed = window.file_tool.close_other_tabs()
    # Assert
    assert closed == ONE_PROJECT
    assert window.project_tabs.count() == ONE_PROJECT
    assert window.research_path() == keep
    assert window.coordinate_tool.table_molecule().formula == NEON
    assert window.coordinate_tool.table_molecule().atoms[0].x == pytest.approx(EDITED_X)
    assert not other.parent.exists()  # the other file was only looked at — its project leaves no folder


def test_keeps_selection_when_inactive_project_is_closed(window, tmp_path):
    # Arrange
    empty(window)
    first, second = files(tmp_path)
    window.opening_tool.open_path(first)
    keep = window.research_path()
    window.opening_tool.open_path(second)
    window.activate_project_tab(0)
    # Act
    window.close_project_tab(1)
    # Assert
    assert window.research_path() == keep
    assert window.coordinate_tool.table_molecule().formula == HELIUM


def test_exports_nothing_when_active_project_is_empty(window, tmp_path):
    # Arrange
    empty(window)
    window.opening_tool.open_path(files(tmp_path)[0])
    window.new_project_tab()
    # Act
    found = window.file_tool.batch_structures()
    # Assert
    assert found == []


def test_exports_drawn_molecule_when_new_project_has_not_been_saved(window, tmp_path):
    # Arrange
    empty(window)
    window.new_project_tab()
    window.load_molecule(read_xyz(f'1\n{HELIUM}\n{HELIUM} 0 0 0\n'))
    target = tmp_path / 'drawn.xyz'
    # Act
    window.file_tool.save_batch('xyz-one', path=target)
    # Assert
    assert read_xyz(target.read_text()).formula == HELIUM


def test_preserves_drawn_molecule_when_new_project_is_closed(window):
    # Arrange
    empty(window)
    path = window.new_project_tab()
    window.load_molecule(read_xyz(f'1\n{HELIUM}\n{HELIUM} {EDITED_X} 0 0\n'))
    # Act
    window.file_tool.close_current_tab()
    # Assert
    saved = projects.Project.load(path)
    molecule, _ = saved.read_structure(saved.molecules[0]['structure'])
    assert molecule.formula == HELIUM
    assert molecule.atoms[0].x == pytest.approx(EDITED_X)

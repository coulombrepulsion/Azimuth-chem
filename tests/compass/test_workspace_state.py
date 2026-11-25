"""The view of a tab of Compass is a record of its own (azimuth/runtime/workspace_state.WorkspaceState).

Oracles: the rules of workspace_state §2 — the fields of the view live in document.view and are read and written under
their old names; each tab keeps its own view when the tabs are switched; the data of the tab is not in the view."""

from dataclasses import fields

from azimuth.core import read_xyz
from azimuth.runtime.workspace_state import VIEW_FIELDS, WorkspaceState
from modules.compass.panels.documents import Document
from tests.projects.test_projects import app, window  # noqa: F401 — isolated Qt fixtures

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')


def test_the_view_is_its_own_record_under_the_old_names():
    d = Document()
    assert isinstance(d.view, WorkspaceState)
    data = {f.name for f in fields(Document)}
    assert not data & set(VIEW_FIELDS)  # no field of the view among the fields of the document
    d.drawer_open, d.drawer_page, d.current = True, 'conformers', 3
    d.undo.append(WATER)
    assert d.view.drawer_open and d.view.drawer_page == 'conformers' and d.view.current == 3 and d.view.undo == [WATER]
    other = Document()
    assert other.view is not d.view and other.undo == [] and not other.drawer_open


def test_each_tab_keeps_its_own_view(window):
    window.load_molecule(WATER)
    first = window.document()
    window.new_document('Helium', read_xyz('1\nHe\nHe 0 0 0'))
    second = window.document()
    window.switch_document(window.documents.index(first))
    assert window.document() is first and first.undo is first.view.undo
    assert second.view is not first.view
    window.switch_document(window.documents.index(second))
    assert window.own_molecule().formula == 'He'

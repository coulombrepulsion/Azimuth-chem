"""What a tab shows, apart from what it holds (PROJECT_RUNTIME_GUIDE.md §3–4 and RUNTIME_CONTRACTS.md §1:
«Камера, раскрытые панели, прокрутка — WorkspaceState: только представление, не источник научных данных»).

§1 PURPOSE
    A tab of Compass (modules/compass/panels/documents.Document) kept in one flat record the data of its molecule (the
    structure, the constraints, the settings of Sextant, the project ids) and how it is looked at (the Undo history,
    the measurements pinned on the model, the vectors and planes, the drawer open and its page, the step and the
    conformer chosen). Nothing told the two apart, so nothing kept a view from becoming data. Here the view is a record
    of its own; the document keeps it as .view and gives its fields under their old names (properties), so the code
    of the window reads and writes them as before.
§2 RULES
    1. WorkspaceState holds only the view: VIEW_FIELDS. It is never written into a project, a recovery copy or an
       input file and is never read to make one (tests/core/test_architecture_boundaries: the storage and the runtime
       layers name none of VIEW_FIELDS, nor .view).
    2. Each tab has its own WorkspaceState (switching tabs keeps each one's view).
    3. Undo is a view: going back in it changes the structure of the tab (an edit, written as any edit), but the list of
       states itself is not data of the molecule.
§3 INTERFACE WorkspaceState(undo, redo, pinned, guides, current, drawer_open, drawer_page, conformer_current);
    VIEW_FIELDS; view_property(name) — a property of a document delegating to its .view.
"""

from __future__ import annotations

from dataclasses import dataclass, field, fields


@dataclass(eq=False)
class WorkspaceState:
    undo: list = field(default_factory=list)  # the structures before (Ctrl+Z)
    redo: list = field(default_factory=list)
    pinned: list = field(default_factory=list)  # the measurements pinned on the model
    guides: list = field(default_factory=list)  # the vectors and planes drawn on the model
    current: int = -1  # the step of the result chosen in the drawer
    drawer_open: bool = False
    drawer_page: str = 'steps'  # the page of the drawer of the result
    conformer_current: int = -1  # the conformer chosen on the page «Конформеры»


VIEW_FIELDS = tuple(f.name for f in fields(WorkspaceState))


def view_property(name):
    """A property of a document that reads and writes the field name of its WorkspaceState (.view)."""
    def get(self):
        return getattr(self.view, name)

    def put(self, value):
        setattr(self.view, name, value)

    return property(get, put, doc=f'{name} of the view of the tab (WorkspaceState)')

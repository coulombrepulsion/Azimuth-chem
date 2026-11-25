"""Compass, Sextant and Spectrum: document tabs — several structures, their calculations and results side by side
(one row of tabs for the three sections).

§1 PURPOSE
    A result of a calculation (optimization steps, a scan, an IRC or NEB path, frames of an XYZ file) opens in
    its own tab of Compass, and the molecule that was there stays in its tab: closing and opening the steps
    drawer, or going to Sextant and back, never takes the result away. A crystal from a CIF file gets a tab too.
§2 ALGORITHM
    «Компас · Молекула» and «Компас · Кристалл» have separate rows of tabs (Document.kind): changing the
    subsection stores the shown tabs and brings back the other subsection's tabs (show_document_kind); a result
    always opens among the molecule tabs, a CIF among the crystal tabs.
    One viewer, one table and one drawer show the current Document; switching stores the state of the shown
    tab (structure, undo and redo, the «unsaved» mark, the project file, optimization constraints, pinned
    measurements, the steps of the drawer with the chosen step and whether the drawer was open, the crystal
    and its cell) and puts back the state of the other one. A result goes (result_document):
      1. into the tab its calculation was started from, when that tab is still open (a job of Sextant);
      2. else into the current tab when it is empty (no atoms, no steps);
      3. else into a new tab named «formula · file».
    The structure of a result tab is the last geometry of the result (open_result_steps), so the drawer
    closed shows the result; in the tab of rule 1 it is one undoable change. A result without steps
    (a single point, UV-Vis …) goes to Spectrum only and leaves the tabs as they are. Closing a tab with unsaved
    changes asks first; closing the last tab leaves one empty tab.
    A tab is the whole work on one structure — its structure (Compass), the settings
    of its calculation (Sextant: Document.calculation, .program) and its result (Spectrum: Document.output = (output,
    text, source, path), the properties on the model: Document.properties). Sextant and Spectrum show the same
    molecule tabs above their pages, and a tab chosen in any section is chosen in all three (the rows of
    the tabs are gone — a visible tab is a project, azimuth/project_navigation.py). Sextant and Spectrum always work on
    the molecule tabs: going there from
    «Компас · Кристалл» brings the molecules back (azimuth/app.py navigate). Every result now gets a tab
    (route_result): a result with steps as before (open_result_steps); a result without steps goes by the same
    rules 1–3 and its tab takes its geometry; its properties are on the model of that tab at once, without opening
    Spectrum first. Where the result is shown is decided by spectral(): frequencies, UV-Vis or NMR → Spectrum,
    otherwise Compass (modules/sextant/workspace.py finish_job, modules/compass/workspace.py open_example_path).
§3 APPLICATIONS modules/compass/panels/layout.py (the tab row above the model), modules/spectrum/workspace.py
    (display_output), modules/compass/workspace.py (open_path), modules/compass/actions/crystal_actions.py (CIF),
    modules/sextant/workspace.py (the tab a job was started from).
§4 SPECIFICATION
    Document (fields above); document() -> Document shown; documents, current_document; new_document(title='',
    molecule=None) -> Document (shown); switch_document(index); close_document(index) -> bool;
    result_document(title, target=None) -> Document; open_result_steps(output, source) -> Document | None;
    own_molecule() -> the structure of the tab (not the step shown in the drawer); any_dirty() -> bool.
§5 PROCEDURES - below.
§6 NOTES
    Before 0.59.0 Sextant (charge, multiplicity, method …) and Spectrum were shared by all tabs. A new tab takes
    the settings of Sextant as they are (Document.calculation None until it is left once).
§7 TESTS
    tests/test_gui.py::test_document_tabs_keep_results.
§8' ROBUSTNESS
    Switching while a step is shown in the drawer first leaves the drawer (the step is not adopted); a tab that
    was closed is never the target of a finished job.
"""

from dataclasses import dataclass, field, replace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout

from azimuth.core import Molecule
from azimuth.i18n import tr
from azimuth.runtime.workspace_state import VIEW_FIELDS, WorkspaceState, view_property


@dataclass(eq=False)
class Document:
    title: str = ''
    molecule: object = None
    # the view of the tab (Undo, pinned measurements, vectors and planes, the drawer and what is chosen in it)
    # is a record of its own — azimuth/runtime/workspace_state.WorkspaceState; its fields are properties below
    view: object = field(default_factory=WorkspaceState)
    dirty: bool = False
    project_path: object = None
    constraints: list = field(default_factory=list)
    steps: tuple = ()
    source: str = ''
    scan: object = None
    initial: object = None
    conformers: tuple = ()  # the page «Конформеры» of the drawer
    conformer_source: str = ''
    research_project_id: str = ''
    research_molecule_id: str = ''
    research_project_path: str = ''
    file_formal: tuple = ()  # the formal charges per atom of the molfile opened in the tab (embed3d)
    structure_flat: tuple = ()  # the structures told flat (2D) when their file was opened — «Сделать 3D» takes them
    crystal: object = None
    slab: object = None
    slab_n: tuple = (1, 1, 1)
    cell_lines: object = None
    symmetry_items: object = None
    lattice_points: object = None
    ellipsoids: object = None
    polyhedra: object = None
    atom_tints: object = None
    ring_marks: object = None
    result: bool = False
    iupac: object = None  # the name asked with «Назвать»
    symmetry_asked: object = None  # the geometry the point group was asked for
    named: bool = False  # the title was given (a result, a file), not taken from the structure
    kind: str = 'molecule'  # the tabs of «Компас · Молекула» ('molecule') and «Компас · Кристалл» ('crystal')
    # the tab is shared by Compass, Sextant and Spectrum
    calculation: object = None  # core.Calculation of Sextant (None: the form as it is)
    program: str = ''  # the program chosen in Sextant
    state_formula: object = None  # the formula the charge and multiplicity of Sextant were set for
    input_edit: object = None  # (text, the generated text it was edited from) — the input edited by hand
    output: object = None  # (output, text, source, path) shown in Spectrum
    properties: object = None  # (Properties, source) on the model
    labels: dict = field(default_factory=dict)  # own labels of atoms {index: text}
    bond_marks: dict = field(default_factory=dict)  # the type and the colour of single bonds (viewer)
    file_path: object = None  # the file the tab was opened from («Файл → Перечитать файл»)
    # the turn, the zoom and the shift of the model of this tab (the field is one for all the tabs)
    camera: object = None
    shown_attempt: object = None  # the id of a calculation of the molecule looked at instead of the current


for _name in VIEW_FIELDS:  # d.undo, d.drawer_open … read and write d.view
    setattr(Document, _name, view_property(_name))


def empty_molecule():
    return Molecule(tr('Новая молекула'), (), ())


class DocumentActions:
    """Mixin of CompassWorkspace."""

    def build_view_row(self, leading=()):
        """The row over the field (called by the layout before the model is built): the steps button and the
        «Молекула | Координаты» tabs. The row of the molecule tabs that followed them (hidden since
        0.104.0 — a tab is a project now, its molecules are in the list of the project) is gone; the tabs of Compass
        stay as documents switched by switch_document."""
        self.documents = [Document(molecule=self.molecule)]
        self.current_document = 0
        # «Компас · Молекула» and «Компас · Кристалл» have their own tabs; the tabs of the subsection not
        # shown wait here as (documents, current index), and show_document_kind swaps them in
        self.document_kind = 'molecule'
        self.shelved_documents = {}
        if not hasattr(self, 'compass_mode'):
            self.compass_mode = 'molecule'  # known from the start, not only after the first change of subsection
        self._switching = False
        self.result_target = None
        from PySide6.QtWidgets import QFrame

        row = QFrame()
        row.setObjectName('documentRow')
        layout = QHBoxLayout(row)
        # the row stands right on the top edge of the field (no gap below it) and starts after its rounded
        # corner (radius 10 px of QTabWidget::pane), where the straight line begins; everything sits on that line
        layout.setContentsMargins(12, 0, 2, 0)
        layout.setSpacing(2)
        for widget in leading:
            layout.addWidget(widget, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addStretch(1)
        return row

    # -- state -------------------------------------------------------------------------------------
    def document(self):
        return self.documents[self.current_document]

    def own_molecule(self):
        """The structure of the tab: while a step is shown in the drawer, the one under it."""
        if getattr(self, 'browsing', False) and getattr(self, '_own', None):
            return self._own[0]
        return self.molecule

    def store_document(self):
        d = self.document()
        d.drawer_open = self.trajectory_button.isChecked()
        d.drawer_page = self.drawer.page()
        d.current = self.drawer.current
        if self.browsing or self.drawer.isVisible():
            self.trajectory_tool.set_trajectory_open(False)  # back to the tab's own structure
        d.molecule = self.molecule
        d.camera = self.viewer_camera()  # each tab keeps its own view of the model
        d.undo, d.redo = self.undo_history, self.redo_history
        d.dirty, d.project_path = self.dirty, self.project_path
        d.constraints = list(getattr(self, 'constraints', []) or [])
        d.pinned = list(getattr(self.viewer, 'pinned', []) or [])
        d.labels = dict(getattr(self.viewer, 'custom_labels', {}) or {})
        d.bond_marks = dict(getattr(self.viewer, 'bond_marks', {}) or {})
        d.guides = list(getattr(self.viewer, 'guides', []) or [])
        d.steps, d.source, d.scan = self.drawer.steps, self.drawer.source, self.drawer.scan
        d.conformers, d.conformer_source = self.drawer.conformers, self.drawer.conformer_source
        d.conformer_current = self.drawer.conformer_current
        d.initial = self.trajectory_initial
        d.crystal, d.slab = getattr(self, 'crystal', None), getattr(self, 'slab', None)
        d.slab_n = getattr(self, 'slab_n', (1, 1, 1))
        d.cell_lines = self.viewer.cell_lines
        d.symmetry_items = getattr(self.viewer, 'symmetry_items', None)
        d.lattice_points = getattr(self.viewer, 'lattice_points', None)
        d.ellipsoids = getattr(self.viewer, 'ellipsoids', None)
        d.polyhedra = getattr(self.viewer, 'polyhedra', None)
        d.atom_tints = getattr(self.viewer, 'atom_tints', None)
        d.ring_marks = getattr(self.viewer, 'ring_marks', None)
        d.iupac, d.symmetry_asked = getattr(self, '_iupac', None), getattr(self, '_symmetry_asked', None)
        if hasattr(self, 'calculation') and hasattr(self, 'program'):  # Sextant of this tab
            d.calculation, d.program = self.calculation(), self.program_kind()
            d.state_formula = getattr(self, '_state_formula', None)
            if hasattr(self, 'input_tool'):
                d.input_edit = self.input_tool.stored_input_edit()
        if hasattr(self, 'result_properties'):
            d.properties = (self.result_properties, getattr(self, 'result_source', ''))
        return d

    CAMERA = ('yaw', 'pitch', 'roll', 'zoom', 'basis')

    def viewer_camera(self):
        """The view of the model — its turn (yaw, pitch, roll, basis), zoom and shift (pan)."""
        viewer = self.viewer
        return {**{k: getattr(viewer, k, None) for k in self.CAMERA}, 'pan': (viewer.pan.x(), viewer.pan.y())}

    def set_viewer_camera(self, camera):
        """The view kept by a tab; a tab without one (new) — the view of a model just opened."""
        from PySide6.QtCore import QPointF

        viewer = self.viewer
        if not camera:
            viewer.reset_view()
            return
        for key in self.CAMERA:
            if key in camera:
                setattr(viewer, key, camera[key])
        x, y = camera.get('pan', (viewer.pan.x(), viewer.pan.y()))
        viewer.pan = QPointF(x, y)
        viewer.locked_camera = None
        viewer.update()

    def restore_document(self, d):
        self._switching = True
        try:
            self.undo_history, self.redo_history = d.undo, d.redo
            self._iupac, self._symmetry_asked = d.iupac, d.symmetry_asked
            self.constraints = list(d.constraints)
            self.viewer.constraints = list(d.constraints)
            self.viewer.pinned = []
            self.molecule = d.molecule  # the same atoms: load_molecule keeps the constraints
            self.viewer.custom_labels = {}
            self.viewer.bond_marks = {}
            self.load_molecule(d.molecule, record=False)
            self.set_viewer_camera(getattr(d, 'camera', None))
            self.viewer.custom_labels = dict(d.labels)
            self.viewer.bond_marks = dict(getattr(d, 'bond_marks', {}) or {})
            self.viewer.pinned = list(d.pinned)
            self.viewer.guides = list(d.guides)
            self.crystal, self.slab, self.slab_n = d.crystal, d.slab, d.slab_n
            self.viewer.cell_lines = d.cell_lines
            self.viewer.symmetry_items = getattr(d, 'symmetry_items', None)
            self.viewer.lattice_points = getattr(d, 'lattice_points', None)
            self.viewer.ellipsoids = getattr(d, 'ellipsoids', None)
            self.viewer.polyhedra = getattr(d, 'polyhedra', None)
            self.viewer.atom_tints = getattr(d, 'atom_tints', None)
            self.viewer.ring_marks = getattr(d, 'ring_marks', None)
            self.trajectory_initial = d.initial
            self.drawer.load(d.steps, d.source, d.scan)
            if d.steps and 0 <= d.current < len(d.steps):
                self.drawer.select(d.current)
            self.drawer.load_conformers(d.conformers, d.conformer_source)
            if 0 <= d.conformer_current < len(d.conformers):
                self.drawer.select_conformer(d.conformer_current)
            if hasattr(self, 'trajectory_tool'):  # ☰ only with something to show
                self.trajectory_tool.update_result_button()
            # Sextant and Spectrum of this tab
            if d.calculation is not None and hasattr(self, 'program') and hasattr(self, 'apply_calculation'):
                self.apply_calculation(d.calculation, d.program, d.state_formula)
            if hasattr(self, 'input_tool'):  # the edit of this tab, or none
                self.input_tool.restore_input_edit(d.input_edit)
            if hasattr(self, 'result_properties'):
                props, source = d.properties or (None, '')
                self.result_properties, self.result_source = props, source
                self._overlay_cache = (None, None, None)
            if hasattr(self, 'result_tabs') and hasattr(self, 'show_result'):
                if d.output is not None:
                    self.show_result(d.output)
                elif hasattr(self, 'clear_result'):
                    self.clear_result()
            self.dirty, self.project_path = d.dirty, d.project_path
            self.update_history_buttons()
            self.update_pin_button()
            self.viewer.update()
        finally:
            self._switching = False
        if d.drawer_open:
            self.trajectory_tool.set_trajectory_open(True, d.drawer_page)

    def any_dirty(self):
        """Unsaved changes in some tab of Compass. A tab without atoms has nothing to save — an empty tab of
        «Молекула» or «Кристалл» that was only visited (its settings touched, the table reloaded) no longer asks to
        save when the program closes (the same rule as the dot on the tab and closing a tab)."""
        here = self.document()
        shelved = [d for docs, _ in self.shelved_documents.values() for d in docs]
        own = self.own_molecule()
        if self.dirty and own is not None and own.atoms:
            return True
        return any(d.dirty and d.molecule is not None and d.molecule.atoms for d in self.documents + shelved if d is not here)

    def all_documents(self):
        """The tabs of both subsections of Compass: the shown ones first."""
        return list(self.documents) + [d for docs, _ in self.shelved_documents.values() for d in docs]

    def show_document_kind(self, kind):
        """Show the tabs of «Компас · Молекула» ('molecule') or «Компас · Кристалл» ('crystal') — 0.52.0. The tabs
        shown are stored as they are (structure, undo, drawer …) and wait; the other subsection gets back its own
        tabs and the tab that was current there, or one empty tab the first time."""
        kind = 'crystal' if kind == 'crystal' else 'molecule'
        if kind == self.document_kind or not hasattr(self, 'documents'):
            self.document_kind = kind
            return False
        self.store_document()
        self.shelved_documents[self.document_kind] = (self.documents, self.current_document)
        docs, index = self.shelved_documents.pop(kind, ([], 0))
        if not docs:
            docs, index = [Document(molecule=empty_molecule(), kind=kind)], 0
        self.documents, self.current_document = docs, min(max(0, index), len(docs) - 1)
        self.document_kind = kind
        self.restore_document(self.document())
        return True

    # -- tabs ----------------------------------------------------------------------------------------
    def switch_document(self, index):
        if self._switching or index == self.current_document or not 0 <= index < len(self.documents):
            return
        from azimuth.tasks import held

        if held():  # a work goes on in this document (azimuth.tasks.run_waiting)
            return 
        self.store_document()
        tool = getattr(self, 'crystal_tool', None)
        if tool is not None:  # the panel beside the model is of this tab
            tool.close_side()
        self.current_document = index
        self.restore_document(self.documents[index])

    def new_document(self, title='', molecule=None):
        d = Document(title=title, molecule=molecule or empty_molecule(), named=bool(title), kind=self.document_kind)
        self.documents.append(d)
        self.switch_document(len(self.documents) - 1)  # stores the shown tab, shows this one
        return d

    def close_document(self, index):
        from PySide6.QtWidgets import QMessageBox

        from azimuth.tasks import held

        if held():  # a work goes on in this document (azimuth.tasks.run_waiting)
            return False
        if not 0 <= index < len(self.documents):
            return False
        d = self.documents[index]
        dirty = self.dirty if index == self.current_document else d.dirty
        if dirty and d.molecule is not None and (self.own_molecule() if index == self.current_document else d.molecule).atoms:
            from azimuth import quill

            answer = quill.question(  # Quill over the waste basket
                self,
                tr('Закрыть вкладку?'),
                tr(f'Во вкладке «{self.document_title(index)}» есть несохранённые изменения. Закрыть её?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
                'delete',
            )
            if answer != QMessageBox.StandardButton.Yes:
                return False
        if index == self.current_document and (self.browsing or self.drawer.isVisible()):
            self.trajectory_tool.set_trajectory_open(False)
        if len(self.documents) == 1:  # the last tab: an empty one in its place
            fresh = Document(molecule=empty_molecule(), kind=self.document_kind)
            self.documents[0] = fresh
            self.restore_document(fresh)
            if hasattr(self, 'recovery'):
                self.recovery.capture()
            return True
        shown = index == self.current_document
        del self.documents[index]
        if shown:  # as the tab bar did: the tab to the right takes its place, or the one before the last
            self.current_document = min(index, len(self.documents) - 1)
            self.restore_document(self.document())
        elif index < self.current_document:
            self.current_document -= 1
        if hasattr(self, 'recovery'):
            self.recovery.capture()
        return True

    def document_title(self, index):
        d = self.documents[index]
        molecule = self.own_molecule() if index == self.current_document else d.molecule
        if d.named and d.title:
            return d.title
        if molecule is None or not molecule.atoms:
            return tr('Новая вкладка')
        # the titles of the examples of the program in the language of the program («Этан — учебная начальная
        # геометрия» stayed Russian in English); a title of the user's file is not in the tables and stays as it is
        return tr(molecule.title) if molecule.title else molecule.formula

    # -- the molecule tabs for Sextant and Spectrum ---------------------------------------------------------
    def molecule_documents(self):
        """(the molecule tabs, the index of the current one) — shown or waiting on the shelf."""
        if self.document_kind == 'molecule':
            return self.documents, self.current_document
        return self.shelved_documents.get('molecule', ([], 0))

    def ensure_molecule_tabs(self):
        """Sextant and Spectrum work on the molecule tabs: from «Компас · Кристалл» they come back."""
        if self.document_kind != 'molecule':
            if hasattr(self, 'crystal_tool'):
                self.crystal_tool.set_compass_mode('molecule')
            else:
                self.show_document_kind('molecule')

    # -- results ---------------------------------------------------------------------------------------
    def tab_is_empty(self):
        return not self.own_molecule().atoms and not self.drawer.steps

    def result_document(self, title, target=None):
        """The tab a result opens in (§2): the tab of its calculation, the current empty one or a new one.
        A result belongs to «Компас · Молекула» — from «Компас · Кристалл» Compass goes there first."""
        if self.document_kind != 'molecule' and hasattr(self, 'crystal_tool'):
            self.crystal_tool.set_compass_mode('molecule')
        index = next((i for i, d in enumerate(self.documents) if d is target), None) if target is not None else None
        if index is not None:
            if index != self.current_document:
                self.switch_document(index)
            d = self.document()
        elif self.tab_is_empty():
            d = self.document()
            d.title, d.named = title, True
        else:
            d = self.new_document(title)
        d.result = True
        return d

    @staticmethod
    def spectral(output):
        """Whether a result has something to look at in Spectrum (vibrations, UV-Vis, NMR); otherwise it is
        looked at in Compass (the structure, the steps, the properties on the model)."""
        return bool(getattr(output, 'frequencies', ()) or getattr(output, 'absorption', ()) or getattr(output, 'shieldings', ()))

    def route_result(self, record):
        """The tab of a result (output, text, source, path): steps as open_result_steps, otherwise by the
        same rules 1–3 with the geometry of the result; the record and the properties belong to that tab."""
        output, text, source, path = record
        d = self.open_result_steps(output, source)
        if d is None:
            target, self.result_target = self.result_target, None
            final = output.vibration_geometry or output.geometry
            title = f'{final.formula} · {source}' if final is not None and source else (source or tr('Результат'))
            d = self.result_document(title, target)
            if self.browsing or self.drawer.isVisible():
                self.trajectory_tool.set_trajectory_open(False)
            if final is not None and final.atoms:
                keep = target is not None and d is target
                own = self.molecule
                same = [a.symbol for a in own.atoms] == [a.symbol for a in final.atoms]
                moved = not same or any(a.position != b.position for a, b in zip(own.atoms, final.atoms))
                if moved:
                    molecule = replace(final, title=own.title if keep else '', bonds=own.bonds if same else None)
                    self.load_molecule(molecule, record=keep and bool(own.atoms))
                    if not keep:
                        self.undo_history, self.redo_history = [], []
                        self.update_history_buttons()
                        self.dirty = False
        d.output = record
        if hasattr(self, 'property_tool'):
            self.property_tool.set_result_properties(output.properties, source, announce=True)
            d.properties = (output.properties, source)
        return d

    def result_orbitals_note(self):
        """A hint where the orbitals of the result of this tab are on the model (after show_result)."""
        if self.result_orbitals() is not None and hasattr(self, 'notify'):  # also an ORCA .gbw
            self.notify(tr('В результате есть орбитали: кнопка ☰ слева над моделью — вкладки «Орбитали» и «QTAIM».'), 12000)

    def open_result_steps(self, output, source=''):
        """Optimization steps, a scan or a path of output in its tab; None when there are no steps."""
        steps = tuple(getattr(output, 'steps', ()) or ())
        scan = getattr(output, 'scan', None)
        if not steps and not (scan is not None and scan.points):
            return None
        target, self.result_target = self.result_target, None
        geometries = [s.geometry for s in steps if s.geometry is not None]
        if not geometries and scan is not None:
            geometries = [p.geometry for p in scan.points if p.geometry is not None]
        final = geometries[-1] if geometries else None
        title = f'{final.formula} · {source}' if final is not None and source else (source or tr('Результат'))
        d = self.result_document(title, target)
        if self.browsing or self.drawer.isVisible():
            self.trajectory_tool.set_trajectory_open(False)
        self.trajectory_tool.load_trajectory(output, source)
        if final is not None:
            keep = target is not None and d is target
            own = self.molecule
            same = [a.symbol for a in own.atoms] == [a.symbol for a in final.atoms]
            molecule = replace(final, title=own.title if keep else '', bonds=own.bonds if same else None)
            self.load_molecule(molecule, record=keep and bool(own.atoms))
            if not keep:
                self.undo_history, self.redo_history = [], []
                self.update_history_buttons()
                self.dirty = False
        return d

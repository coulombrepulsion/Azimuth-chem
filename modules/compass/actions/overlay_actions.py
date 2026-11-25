"""Compass: overlay of another structure for comparison, atoms in any order.

The button «Сравнить» above the model (and «Файл → Наложить структуру для сравнения…») opens a
structure file; modules/compass/chemistry/overlay.py pairs its atoms with those of the model (same element, one
to one, whatever the numbering) and superimposes it. The compared structure is drawn over the model in
one colour (rings, dashed bonds, dotted lines from each atom to its partner); the caption gives the
file, RMSD (all atoms and without H), the largest deviation and whether the numbering differs. The
structure is aligned onto the model again after each change of the model (a moment after the last
change, so dragging stays smooth). Actions: allow a mirror image; renumber the model as in the file;
save the compared structure in the numbering of the model; remove the comparison.

§1 THEORY the superposition and pairing: modules/compass/chemistry/overlay.py §1.
§2 ALGORITHM read the file (structure_from_path: the final geometry of outputs, trajectories and
               Molden files; the structure of the other formats); superimpose onto the model; keep the
               result for the atoms it was computed for and compute again when they change (at once
               up to RECOMPUTE_NOW_ATOMS atoms, else RECOMPUTE_MS after the last change).
§3 APPLICATIONS the «Сравнить» button and «Файл → Наложить структуру для сравнения…» of Compass.
§4 SPECIFICATION compare_path(path) -> bool; set_compare(structure, name, note) -> bool;
               compare_overlay(molecule) -> (aligned Molecule or None, caption lines) for the viewer;
               renumber_as_compared(); save_compared_renumbered(); clear_compare().
§5 PROCEDURES below.
§6 NOTES the overlay is not drawn while optimization steps are browsed (their own start is shown).
§7 TESTS tests/test_gui.py::test_overlay_of_another_structure_with_shuffled_atoms.
§8' ROBUSTNESS unreadable files and a different composition give a message, the model is unchanged;
               renumbering is one undoable step, constraints and pinned measurements follow the atoms.
"""

from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QFileDialog, QMenu

from modules.compass.chemistry import overlay
from azimuth.i18n import tr
from azimuth.ui import smooth

RECOMPUTE_MS = 180  # wait after the last change of the model before aligning again
RECOMPUTE_NOW_ATOMS = 60  # up to this size the structure is aligned at once (about 50 ms)


def structure_from_path(path):
    """(Molecule, note) of a structure file: the final geometry of outputs and trajectories."""
    from modules.compass.chemistry import formats
    from modules.compass.actions.opening_actions import OpeningTool
    from azimuth.core import read_xyz

    kind = OpeningTool.file_kind(path)
    text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
    if kind == 'project':
        from azimuth.core import read_project

        return read_project(text)[0], ''
    if kind in ('output', 'gaussian_log'):
        from modules.spectrum.readers.outputs import read_any

        out = read_any(text, path)
        if out.geometry is None:
            raise ValueError(tr('В результате нет геометрии.'))
        return out.geometry, tr('последняя геометрия результата')
    if kind == 'cif':  # the content of one unit cell
        from modules.compass.chemistry import crystal

        return crystal.build(crystal.parse_cif(text), (1, 1, 1), False), tr('одна элементарная ячейка')
    if kind == 'fchk':
        from modules.spectrum.readers.orbital_files import read_fchk

        return read_fchk(text).molecule, ''
    if kind in ('molden', 'xyz_frames'):
        traj = (formats.read_molden if kind == 'molden' else formats.xyz_trajectory)(text)
        return traj.geometry, (tr('последний кадр') if traj.steps else '')
    if kind in ('gaussian_input', 'orca_input'):
        return (formats.read_gaussian_input if kind == 'gaussian_input' else formats.read_orca_input)(text)[0], ''
    if kind in ('mol', 'mol2', 'pdb'):
        return {'mol': formats.read_mol, 'mol2': formats.read_mol2, 'pdb': formats.read_pdb}[kind](text), ''
    return read_xyz(text), ''


class OverlayTool:
    """Was the mixin OverlayActions of the window; a part of its own — it reaches the window only through the names
    of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'OPEN_FILTER',
        'browsing',
        'compare_error',
        'compare_menu',
        'compare_name',
        'compare_result',
        'compare_structure',
        'constraints',
        'constraints_changed',
        'error',
        'load_molecule',
        'molecule',
        'notify',
        'save_text',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def build_overlay_actions(self):
        self.w.compare_structure = None  # the other structure as read (its own numbering)
        self.w.compare_name = ''
        self.compare_note = ''
        self.compare_mirror = False
        self.w.compare_result = None  # overlay.Overlay for the atoms self._compare_for
        self._compare_molecule = None
        self.w.compare_error = ''
        self._compare_for = None
        self._compare_timer = QTimer(self.w.widget)
        self._compare_timer.setSingleShot(True)
        self._compare_timer.timeout.connect(self._compare_now)
        self.w.compare_menu = smooth(QMenu(tr('Сравнение структур'), self.w.widget))
        self.w.compare_menu.aboutToShow.connect(lambda: self.fill_compare_menu(self.w.compare_menu))
        self.w.viewer.compare_source = self.compare_overlay

    # -- data ---------------------------------------------------------------------------------------
    def open_compare(self):
        path, _ = QFileDialog.getOpenFileName(
            self.w.widget, tr('Наложить структуру для сравнения'), str(Path.home()), tr(self.w.OPEN_FILTER)
        )
        if path:
            self.compare_path(path)

    def compare_path(self, path):
        try:
            structure, note = structure_from_path(path)
        except (OSError, ValueError, UnicodeError, IndexError, KeyError) as exc:
            self.w.error(exc)
            return False
        return self.set_compare(structure, Path(path).name, note)

    def set_compare(self, structure, name, note=''):
        """Compare the model with structure; False (and a message) if they cannot be superimposed."""
        if structure is None or not structure.atoms:
            self.w.error(ValueError(tr('В файле нет атомов.')))
            return False
        self.w.compare_structure, self.w.compare_name, self.compare_note = structure, name, note
        self._compare_for = None
        self._compare_now()
        if self.w.compare_error:
            self.w.notify(self.w.compare_error, 12000)
        else:
            self.w.notify(self.compare_text()[0], 12000)
        self.w.viewer.update()
        return not self.w.compare_error

    def clear_compare(self):
        self.w.compare_structure = None
        self.w.compare_result = None
        self.w.compare_error = ''
        self._compare_for = None
        self._compare_timer.stop()
        self.w.viewer.update()

    def set_compare_mirror(self, allowed):
        self.compare_mirror = bool(allowed)
        self._compare_for = None
        self._compare_now()
        self.w.viewer.update()

    def _compare_now(self, molecule=None):
        molecule = molecule or self.w.viewer.molecule or self.w.molecule
        self._compare_for = molecule.atoms if molecule is not None else None  # compared by value
        self._compare_molecule = molecule
        self.w.compare_result, self.w.compare_error = None, ''
        if self.w.compare_structure is None:
            return
        try:
            self.w.compare_result = overlay.superimpose(molecule, self.w.compare_structure, self.compare_mirror)
        except ValueError as exc:
            self.w.compare_error = str(exc)
        self.w.viewer.update()

    def compare_overlay(self, molecule):
        """For the viewer: (aligned structure or None, caption lines)."""
        if self.w.compare_structure is None or getattr(self.w, 'browsing', False):
            return None, []
        if molecule.atoms != self._compare_for:
            if len(molecule.atoms) <= RECOMPUTE_NOW_ATOMS:  # small: at once (a few ms, see overlay.py §6)
                self._compare_now(molecule)
            else:  # large: a moment after the last change, so dragging stays smooth
                self._compare_timer.start(RECOMPUTE_MS)
                return None, [tr('Сравнение: выравнивание…')]
        if self.w.compare_error:
            return None, [tr('Сравнение с ') + self.w.compare_name, self.w.compare_error]
        return (self.w.compare_result.aligned if self.w.compare_result else None), self.compare_text()

    def compare_text(self):
        r = self.w.compare_result
        if r is None:
            return [tr('Сравнение с ') + self.w.compare_name] + ([self.w.compare_error] if self.w.compare_error else [])
        k = max(range(len(r.deviations)), key=r.deviations.__getitem__)
        model = self._compare_molecule
        atom = model.atoms[k].symbol + str(k + 1)
        head = tr('Сравнение с ') + self.w.compare_name + (f' ({self.compare_note})' if self.compare_note else '')
        line = tr(f'RMSD {r.rmsd:.3f} Å')
        if r.rmsd_heavy is not None and any(a.symbol == 'H' for a in model.atoms):
            line += tr(f' · без H {r.rmsd_heavy:.3f} Å')
        line += tr(f' · наибольшее отклонение {r.deviations[k]:.3f} Å ({atom})')
        extra = []
        if not r.same_order:
            extra.append(tr('нумерация атомов в файле другая — сопоставлено по положению'))
        if r.mirrored:
            extra.append(tr('совмещено с зеркальным отражением'))
        return [head, line] + ([' · '.join(extra)] if extra else [])

    # -- actions ------------------------------------------------------------------------------------
    def renumber_as_compared(self):
        """Renumber the model as the compared file: model atom paired with file atom j gets number j."""
        r = self.w.compare_result
        if r is None or r.same_order:
            return
        inverse = [0] * len(r.order)
        for i, j in enumerate(r.order):
            inverse[j] = i
        new_index = {old: new for new, old in enumerate(inverse)}
        # constraints and pinned measurements follow their atoms (load_molecule would drop them)
        constraints = [(kind, tuple(new_index[i] for i in atoms)) for kind, atoms in getattr(self.w, 'constraints', [])]
        pinned = [tuple(new_index[i] for i in m) for m in self.w.viewer.pinned]
        if getattr(self.w, 'constraints', None):
            self.w.constraints.clear()
        self.w.viewer.pinned = []
        self.w.load_molecule(overlay.renumber(self.w.molecule, inverse), preserve_view=True)
        if self.w.has('constraints'):
            self.w.constraints[:] = constraints
            self.w.constraints_changed()
        self.w.viewer.pinned = pinned
        self.w.notify(tr('Атомы модели перенумерованы как в ') + self.w.compare_name + tr(' (отменяется).'), 10000)

    def save_compared_renumbered(self):
        r = self.w.compare_result
        if r is None:
            return
        stem = Path(self.w.compare_name).stem or 'structure'
        try:
            self.w.save_text(
                tr('Сохранить сравниваемую структуру в нумерации модели'),
                'XYZ (*.xyz)',
                r.renumbered.xyz(),
                f'{stem}-renumbered.xyz',
            )
        except (ValueError, OSError) as exc:
            self.w.error(exc)

    def fill_compare_menu(self, menu):
        menu.clear()
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        menu.addAction(tr('Наложить структуру из файла…')).triggered.connect(self.open_compare)
        if self.w.compare_structure is None:
            item = menu.addAction(
                tr('Конформер, другая программа, другой порядок атомов — атомы сопоставляются по положению')
            )
            item.setEnabled(False)
            return
        menu.addSeparator()
        for line in self.compare_text():
            menu.addAction(line).setEnabled(False)
        mirror = menu.addAction(tr('Разрешить зеркальное отражение'))
        mirror.setCheckable(True)
        mirror.setChecked(self.compare_mirror)
        mirror.toggled.connect(self.set_compare_mirror)
        menu.addSeparator()
        r = self.w.compare_result
        item = menu.addAction(tr('Перенумеровать модель как в файле'))
        item.setEnabled(r is not None and not r.same_order)
        item.triggered.connect(self.renumber_as_compared)
        item = menu.addAction(tr('Сохранить структуру из файла в нумерации модели (XYZ)…'))
        item.setEnabled(r is not None)
        item.triggered.connect(self.save_compared_renumbered)
        menu.addSeparator()
        menu.addAction(tr('Убрать сравнение')).triggered.connect(self.clear_compare)

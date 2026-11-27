"""OpeningTool (window.opening_tool, a part of the window; was the mixin OpeningActions of CompassWorkspace,
split from it on 2026-11-08): opening structures in Compass — files of every format (open_path, file_kind,
read_structures), a file of many structures as a project, the examples and the library, SMILES, hydrogens and 3D on
opening, the demo optimization, saving XYZ."""

from pathlib import Path

from PySide6.QtWidgets import QFileDialog

from azimuth.core import read_xyz
from azimuth.i18n import combo_key, set_combo_key, tr
from azimuth.paths import ROOT
from modules.compass.chemistry import library

UNNAMED = ('', 'Молфайл', 'MOL2', 'MOL', 'untitled', 'Untitled')  # the titles the readers give a nameless record


def structure_name(title):
    """The name of a record of a file of structures, or '' when it has none (a placeholder of a reader, a number
    or an «energy: …» comment of a program)."""
    title = (title or '').strip()
    if title in UNNAMED or title == tr('Молфайл'):
        return ''
    try:
        float(title.split()[0])
        return ''  # a bare number (xtb, CREST write the energy there)
    except (ValueError, IndexError):
        pass
    return '' if title.lower().startswith(('energy', 'e=', 'scf done')) else title


class OpeningTool:
    """Was the mixin OpeningActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'EXAMPLE_FILTER',
        'HYDROGENS_ON_OPEN',
        'OPEN_FILTER',
        'STRUCTURE_KINDS',
        'batch_tool',
        'browsing',
        'charge',
        'compass_mode',
        'confirm_replace',
        'structure_as_new_molecule',
        'coordinate_tool',
        'crystal_results',  # Spectrum of a crystal project: an output of pw.x opened on its run
        'crystal_tool',
        'display_output',
        'document',
        'error',
        'examples',
        'file_tool',
        'fragment_tool',
        'load_molecule',
        'make_project_3d',
        'model_menu_tool',
        'navigate',
        'notify',
        'open_files_project',
        'open_orbitals_text',
        'open_output_in_its_project',
        'open_output_path',
        'open_project_path',
        'open_result_steps',
        'output',
        'preferences',
        'project_path',
        'projects_root',  # an output of pw.x opened — a crystal project of its own
        'refresh_project_navigation',  # an output of CRYSTAL — its method and energy in the list
        'remember_recent',
        'research_document_path',
        'research_path',
        'save_text',
        'spectral',
        'spin',
        'stack',
        'structure_tabs',
        'trajectory_tool',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def load_example_menu(self, name):
        self.w.crystal_tool.clear_crystal()
        set_combo_key(self.w.examples, name)
        self.example()

    def example(self):
        if self.w.confirm_replace():
            self.w.project_path = None
            self.w.load_molecule(library.molecule(combo_key(self.w.examples)))
            self.w.charge.setValue(0)
            self.w.spin.setValue(1)

    def open_xyz(self):
        path, _ = QFileDialog.getOpenFileName(self.w.widget, tr('Открыть XYZ'), str(Path.home()), 'XYZ (*.xyz)')
        if path:
            self.open_path(path)  # a project, as every file of structures

    def open_any(self):
        """Файл → Открыть… (more formats): the kind of file decides what happens."""
        # several files at once — a set of structures (one project)
        paths, _ = QFileDialog.getOpenFileNames(self.w.widget, tr('Открыть'), str(Path.home()), tr(self.w.OPEN_FILTER))
        if len(paths) > 1:
            self.open_paths_as_set(paths)
        elif paths:
            self.open_path(paths[0])

    def read_structures(self, path):
        """[(Molecule, name)] of a file of structures (XYZ with several frames: each frame; SDF: each record)."""
        from modules.compass.chemistry import formats

        kind = self.file_kind(path)
        if kind not in self.w.STRUCTURE_KINDS:
            raise ValueError(tr(f'{Path(path).name}: это не файл структуры.'))
        text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
        stem = Path(path).stem
        if kind in ('xyz', 'xyz_frames'):
            frames = formats.read_xyz_frames(text)
        elif kind == 'mol':
            frames = formats.read_sdf_records(text) if Path(path).suffix.lower() in ('.sdf', '.sd') else [formats.read_mol(text)]
            formal = formats.sdf_charges(text) if Path(path).suffix.lower() in ('.sdf', '.sd') else [formats.mol_charges(text)]
            if len(formal) == len(frames) and any(any(q) for q in formal):  # (Molecule, name, formal charges)
                names = [stem] if len(frames) == 1 else [structure_name(m.title) for m in frames]
                return [(m, n, q) for m, n, q in zip(frames, names, formal)]
        elif kind == 'mol2':
            frames = [formats.read_mol2(text)]
        elif kind == 'cdxml':  # ChemDraw (its formal charges as those of a molfile)
            charges = formats.cdxml_charges(text)
            molecule = formats.read_cdxml(text)
            if any(charges):
                return [(molecule, stem, charges)]
            frames = [molecule]
        elif kind == 'pdb':
            frames = [formats.read_pdb(text)]
        else:
            frames = [(formats.read_gaussian_input if kind == 'gaussian_input' else formats.read_orca_input)(text)[0]]
        if len(frames) == 1:
            return [(frames[0], stem)]
        # a record without a name of its own gets '' — the import of the project names it by its formula (was
        # «Молфайл» for every record of a database)
        return [(m, structure_name(m.title)) for m in frames]

    def hydrogens_on_open(self):
        return str(self.w.preferences.value(self.w.HYDROGENS_ON_OPEN, 'true')).lower() in ('true', '1')

    def opened_with_hydrogens(self, molecule, formal=()):
        """(molecule, added): a file of the heavy atoms only gets its hydrogens when the switch is on; not on
        the atoms with a formal charge of the file (formal — [int] per atom, formats.mol_charges)."""
        from modules.compass.chemistry.editing import skeleton_hydrogens

        charged = tuple(k for k, q in enumerate(formal or ()) if q)
        return skeleton_hydrogens(molecule, charged=charged) if self.hydrogens_on_open() else (molecule, 0)

    def state_of_file(self, molecule, formal):
        """(charge, multiplicity) of a structure whose file gives formal charges (their sum; the parity of the
        electrons), None without them."""
        if not formal or not any(formal) or len(formal) > len(molecule.atoms):
            return None
        charge = sum(formal)
        return charge, 1 if molecule.electrons(charge) % 2 == 0 else 2

    def offer_3d(self, flat, total):
        """Quill offers to make the flat (2D) structures of the file three-dimensional (make_3d), in a window
        with Quill. Returns make_3d's count or 0."""
        from PySide6.QtWidgets import QMessageBox

        from azimuth import quill

        what = (tr('Структура из файла плоская (2D-рисунок)') if total == 1 else
                tr(f'Плоских (2D) структур в файле: {flat} из {total}'))
        answer = quill.question(
            self.w.widget, tr('Плоская структура'),
            what + tr(': у атомов, которые в молекуле не лежат в одной плоскости, все координаты z одинаковы. Для расчёта '
                      'нужна объёмная геометрия — сделать её сейчас (RDKit: ETKDG + MMFF94)? Названия и заряды останутся; '
                      'позже — «Геометрия → Сделать 3D (RDKit)…».'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes, 'empty-model',
            labels={QMessageBox.StandardButton.Yes: tr('Сделать объёмными'), QMessageBox.StandardButton.No: tr('Не сейчас')})
        if answer != QMessageBox.StandardButton.Yes:
            return 0
        return self.make_3d()

    def make_3d(self, *args):
        """«Геометрия → Сделать 3D (RDKit)…» — the molecules of the project (make_project_3d) or the structure of the
        tab, three-dimensional by RDKit (embed3d.py: ETKDG + MMFF94, the lowest of 20); the atoms, their order, the
        names and the charges for a queue stay. A Python with RDKit is found on the computer or chosen once. Returns how
        many were made 3D."""

        from azimuth.tasks import run_waiting
        from modules.compass.chemistry import embed3d

        if self.w.has('research_document_path') and self.w.research_document_path():
            return self.w.make_project_3d()  # the molecules of the project (the only set there is)
        if self.w.browsing:
            return 0
        python = self.rdkit_python()
        if python is None:
            return 0
        document = self.w.document()
        try:
            molecule = self.w.coordinate_tool.table_molecule()
        except ValueError as exc:
            self.w.error(exc)
            return 0
        if len(molecule.atoms) < 2:
            return 0
        molecules = [molecule]
        formal = [document.file_formal if len(document.file_formal) == len(molecule.atoms) else ()]
        try:
            made = run_waiting(self.w.widget, tr(f'RDKit: объёмные структуры ({len(molecules)})…'),
                               lambda step: embed3d.run(python, molecules, formal, step=step), len(molecules))
        except InterruptedError:
            return 0
        except ValueError as exc:
            self.w.error(exc)
            return 0
        good = sum(ok for _, ok, _ in made)
        failed = [f'{molecules[0].title or k + 1}: {note}' for k, (_, ok, note) in enumerate(made) if not ok]
        if good:
            self.w.model_menu_tool.edit_structure(made[0][0], tr('Объёмная структура от RDKit (ETKDG + силовое поле) — это начальная '
                                               'геометрия, а не оптимизированная.'))
        self.w.notify(tr(f'RDKit: объёмных структур {good} из {len(made)}.') + (
            ' ' + tr('Не вышло: ') + '; '.join(failed[:3]) + ('…' if len(failed) > 3 else '') if failed else '')
            + ' ' + tr('Для гибких молекул (макроциклы) дальше — «Поиск конформеров».'), 15000)
        return good

    def rdkit_python(self):
        """The Python with RDKit (embed3d.find_python, kept in the settings), or one chosen; None."""
        from PySide6.QtWidgets import QFileDialog, QMessageBox

        from azimuth import quill
        from azimuth.tasks import run_waiting
        from modules.compass.chemistry import embed3d

        settings = getattr(self.w, 'preferences', None)
        try:
            found = run_waiting(self.w.widget, tr('Ищу Python с RDKit…'), lambda step: embed3d.find_python(settings))
        except InterruptedError:
            return None
        if found is not None:
            return found
        answer = quill.question(
            self.w.widget, tr('Нужен RDKit'),
            tr('Объёмные структуры строит RDKit — его нет ни в Python Азимута, ни в conda на этом компьютере. '
               'Установите его в Терминале: conda install -c conda-forge rdkit — и повторите. Или укажите Python, где '
               'он уже есть. Указать сейчас?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No, 'error')
        if answer != QMessageBox.StandardButton.Yes:
            return None
        path, _ = QFileDialog.getOpenFileName(self.w.widget, tr('Python с RDKit'), str(Path.home()))
        if not path:
            return None
        if not embed3d.has_rdkit(path):
            self.w.error(tr('В этом Python нет RDKit (import rdkit не прошёл).'))
            return None
        if settings is not None:
            settings.setValue(embed3d.KEY, path)
        return Path(path)

    def opens_as_project(self, path):
        """A file of structures opens as a project (the only way — the old ways into the tab and onto
        «Структуры» of the drawer are gone) — but a trajectory stays the steps of the drawer: an XYZ of
        several frames and a PDB of several MODEL (the steps of an optimization, a dynamics), as before 0.104."""
        from modules.compass.chemistry import formats

        kind = self.file_kind(path)
        if kind == 'xyz_frames':
            # T01 (PROJECT_RUNTIME_GUIDE.md §13: a file of many structures is one project): frames of different
            # molecules (another set of atoms) are a set of structures, not a trajectory
            try:
                frames = formats.read_xyz_frames(formats.read_text(path))
            except (OSError, ValueError):
                return False
            first = [a.symbol for a in frames[0].atoms] if frames else []
            return any([a.symbol for a in frame.atoms] != first for frame in frames[1:])
        if kind not in self.w.STRUCTURE_KINDS:
            return False
        if kind == 'pdb':
            try:
                return formats.pdb_model_count(formats.read_text(path)) <= 1
            except (OSError, ValueError):
                return True
        return True

    def open_paths_as_set(self, paths):
        """The structures of several files listed together; a file that is not a structure is reported."""
        path = self.w.open_files_project(paths)  # a project, the only way
        if not path:
            return 0
        from azimuth.projects import Project

        return len(Project.view(path).molecules)

    @staticmethod
    def structure_properties(path, count):
        """The data items of the structures of a file ({} each when it has none, or not as many records)."""
        from modules.compass.chemistry import formats

        if Path(path).suffix.lower() in ('.sdf', '.sd'):
            try:
                found = formats.sdf_properties(Path(path).read_text(encoding='utf-8-sig', errors='replace'))
            except OSError:
                found = []
            if len(found) == count:
                return found
        return [{} for _ in range(count)]

    CRYSTAL_EXAMPLES = (('CsCl.cif', 'CsCl — хлорид цезия (Pm-3m)'), ('NaCl_rock_salt.cif', 'NaCl — каменная соль (Fm-3m)'),
                        ('graphite_P1.cif', 'Графит (P1)'),
                        # silicon: vc-relax works on the primitive cell, which differs from the cell of the file
                        ('Si_diamond.cif', 'Si — кремний, решётка алмаза (Fd-3m)'),
                        ('benzoic_acid.cif', 'Бензойная кислота — молекулярный кристалл'))

    def open_example(self, at=None):
        """Файл → Открыть пример…: the dialog starts in the examples folder (examples/README.md).
        in «Компас · Кристалл» — a menu of the crystals of examples/10-crystals; «Другой файл…» — the dialog there,
        CIF and outputs of CRYSTAL. Returns the menu (shown) or None."""
        if getattr(self.w, 'compass_mode', 'molecule') == 'crystal':
            from PySide6.QtGui import QCursor
            from PySide6.QtWidgets import QMenu

            folder = ROOT / 'examples' / '10-crystals'
            menu = QMenu(self.w.widget)
            for name, title in self.CRYSTAL_EXAMPLES:
                if (folder / name).is_file():
                    menu.addAction(tr(title), lambda p=str(folder / name): self.open_example_path(p))
            menu.addSeparator()

            def other():
                path, _ = QFileDialog.getOpenFileName(self.w.widget, tr('Открыть пример'), str(folder),
                                                      tr('Кристаллы (*.cif *.out *.outp);;Все файлы (*)'))
                if path:
                    self.open_example_path(path)

            menu.addAction(tr('Другой файл…'), other)
            from PySide6.QtCore import QPoint

            menu.popup(at if isinstance(at, QPoint) else QCursor.pos())  # «triggered» of a menu item hands a bool
            self._examples_menu = menu
            return menu
        path, _ = QFileDialog.getOpenFileName(
            self.w.widget, tr('Открыть пример'), str(ROOT / 'examples'), tr(self.w.EXAMPLE_FILTER)
        )
        if path:
            self.open_example_path(path)

    def open_example_path(self, path, go=True, done=None):
        """A result gets its tab (the same in Compass, Sextant and Spectrum) and is shown where there is
        something to look at: vibrations, UV-Vis or NMR in Spectrum, otherwise Compass (optimizations and scans
        with the steps drawer); a fragments file goes to «Мои фрагменты», everything else as «Файл → Открыть…».
        Go=False (the end of a calculation of Sextant) — the result gets its tab and nothing else: the section
        shown stays."""
        if Path(path).name == 'batch.json':
            return self.w.batch_tool.show_saved_batches(Path(path).parent)
        if Path(path).suffix.lower() == '.json':
            return self.w.fragment_tool.import_user_fragments(path)
        if self.file_kind(path) in ('output', 'gaussian_log'):
            def then():  # after the result is shown (a big one is read in the background)
                if done is not None:
                    done()
                if not go:
                    return
                output = getattr(self.w, 'output', None)
                if output is not None and self.w.spectral(output):
                    self.w.navigate(2)
                elif output is not None and (output.steps or getattr(output, 'scan', None) is not None):
                    self.show_trajectory_drawer()
                else:
                    self.w.navigate(0)

            self.w.open_output_path(path, show=False, done=then)
            return None
        return self.open_path(path)

    def open_path(self, path):
        """A structure → Compass; .qcc → the project; ORCA output, Gaussian log, Molden with geometries,
        XYZ with several frames → the optimization drawer of Compass."""
        from modules.compass.chemistry import formats

        from azimuth.tasks import held

        if held():  # a work goes on in this document (azimuth.tasks.run_waiting)
            return None
        if Path(path).name == 'batch.json':
            return self.w.batch_tool.show_saved_batches(Path(path).parent)
        if self.w.has('open_output_in_its_project') and self.w.open_output_in_its_project(path):
            return None  # an output of a calculation of a project — that project, not a tab of its own
        if self.opens_as_project(path):  # 0.104.0; the only way a file of structures opens
            return self.w.open_files_project([path])
        if Path(path).is_file() and self.w.has('file_tool'):  # «Файл → Недавние файлы»
            self.w.file_tool.note_recent(path)
        kind = self.file_kind(path)
        if kind == 'crystal_output':  # an output of CRYSTAL or of TOPOND — the crystal, its steps, its tables
            from modules.compass.actions import crystal_code_window

            try:
                crystal_code_window.open_output(self.w, path, formats.read_text(path))
            except (OSError, ValueError, UnicodeError) as exc:
                self.w.error(exc)
            return
        if kind == 'qe_output':  # Quantum ESPRESSO — the crystal and its results (crystal_code_window.open_qe_output)
            from modules.compass.actions import crystal_code_window

            try:
                crystal_code_window.open_qe_output(self.w, path, formats.read_text(path))
            except (OSError, ValueError, UnicodeError) as exc:
                self.w.error(exc)
            return
        if kind == 'cdx':  # the binary ChemDraw file — its XML twin is read
            self.w.error(ValueError(tr('Двоичный файл ChemDraw (.cdx) не читается — сохраните его в ChemDraw как '
                                       '«ChemDraw XML (.cdxml)» и откройте тот.')))
            return
        if kind == 'cif':  # a crystal — the «Кристалл» window builds it
            try:
                self.w.crystal_tool.open_crystal_text(Path(path).read_text(encoding='utf-8-sig', errors='replace'), Path(path).name)
            except OSError as exc:
                self.w.error(exc)
            return
        if getattr(self.w, 'compass_mode', 'molecule') == 'crystal':
            self.w.crystal_tool.set_compass_mode('molecule')  # molecules and results open among the molecule tabs
        if kind not in ('output', 'gaussian_log', 'xyz_frames'):  # a result goes to its own tab
            self.w.crystal_tool.clear_crystal()
        if kind == 'project':
            self.w.open_project_path(path)
            return
        if kind in ('output', 'gaussian_log'):  # Gaussian logs are read in full (Spectrum)
            self.w.open_output_path(path, show=False, done=self.show_trajectory_drawer)
            return
        if kind == 'fchk':  # a Gaussian formatted checkpoint — the structure and the orbital window
            from modules.spectrum.readers.orbital_files import read_fchk

            try:
                text = Path(path).read_text(encoding='utf-8', errors='replace')
                orbital_set = read_fchk(text)
            except (OSError, ValueError) as exc:
                self.w.error(exc)
                return
            if self.w.confirm_replace():
                self.w.load_molecule(orbital_set.molecule)
                self.w.remember_recent('molecule', path)
            self.w.open_orbitals_text(text, Path(path).name)
            return
        try:
            text = formats.read_text(path)  # UTF-8 or cp1251
            if kind in ('gaussian_log', 'molden', 'xyz_frames'):
                reader = {
                    'gaussian_log': formats.read_gaussian_log,
                    'molden': formats.read_molden,
                    'xyz_frames': formats.xyz_trajectory,
                }[kind]
                traj = reader(text)
                orbitals = kind == 'molden' and self.has_orbitals(text)
                if not traj.steps:  # a Molden file with one geometry
                    if self.w.confirm_replace():
                        self.w.load_molecule(traj.geometry)
                        self.w.remember_recent('molecule', path)
                    if orbitals:  # [GTO] and [MO] — the orbital window too
                        self.w.open_orbitals_text(text, Path(path).name)
                    return
                self.w.open_result_steps(traj, Path(path).name)  # its own tab
                self.show_trajectory_drawer()
                if orbitals:
                    self.w.open_orbitals_text(text, Path(path).name)
                return
            if kind == 'pdb' and formats.pdb_model_count(text) > 1:  # MODEL frames — the steps drawer
                self.w.open_result_steps(formats.pdb_trajectory(text), Path(path).name)
                self.show_trajectory_drawer()
                return
        except (ValueError, OSError, UnicodeError, IndexError, KeyError, TypeError, ZeroDivisionError) as exc:
            self.w.error(exc)

    def show_trajectory_drawer(self):
        if self.w.stack.currentIndex() != 0:
            self.w.navigate(0)
        self.w.structure_tabs.setCurrentIndex(0)
        self.w.trajectory_tool.set_trajectory_open(True, 'steps')

    @staticmethod
    def file_kind(path):
        suffix = Path(path).suffix.lower()
        simple = {
            '.inp': 'orca_input',
            '.qcc': 'project',
            '.mol': 'mol',
            '.sdf': 'mol',
            '.sd': 'mol',
            '.mol2': 'mol2',
            '.cdxml': 'cdxml',  # ChemDraw (XML; the binary .cdx is said to be saved as .cdxml)
            '.cdx': 'cdx',
            '.pdb': 'pdb',
            '.ent': 'pdb',
            '.gjf': 'gaussian_input',
            '.com': 'gaussian_input',
            '.gjc': 'gaussian_input',
            '.molden': 'molden',
            '.molf': 'molden',
            '.fchk': 'fchk',
            '.fch': 'fchk',
            '.cif': 'cif',
            '.nwout': 'output',  # NWChem, Q-Chem, GAMESS outputs (modules/spectrum/readers/outputs.py)
            '.qcout': 'output',
            '.gamout': 'output',
        }
        if suffix in simple:
            return simple[suffix]
        try:
            text = Path(path).read_text(encoding='utf-8', errors='replace')
        except OSError:
            return 'xyz'
        head = text[:20000]
        if head.lstrip().lower().startswith('[molden format]'):  # also orca_2mkl's <name>.molden.input
            return 'molden'
        if suffix in ('.out', '.outp', '.log', '.txt') or not suffix:  # CRYSTAL and TOPOND
            from modules.spectrum.readers import crystal_out, qe

            if qe.is_qe(head):  # pw.x — not an output of a molecule (0.249.1: it was read as ORCA)
                return 'qe_output'

            if crystal_out.is_crystal(text) or crystal_out.is_topond(text):
                return 'crystal_output'
        if suffix in ('.out', '.log') or not suffix or suffix == '.txt':
            if 'Entering Gaussian System' in head or 'Gaussian, Inc.' in head:
                return 'gaussian_log'
            from modules.spectrum.readers.outputs import program

            if suffix in ('.out', '.log') or 'ORCA' in head or 'GEOMETRY OPTIMIZATION CYCLE' in head or program(head) != 'ORCA':
                return 'output'
            if '[Molden Format]' in head:
                return 'molden'
        if suffix == '.xyz' or not suffix or suffix == '.txt':
            from modules.compass.chemistry.formats import xyz_frame_count

            return 'xyz_frames' if xyz_frame_count(text) > 1 else 'xyz'
        return 'xyz'

    @staticmethod
    def has_orbitals(text):
        lowered = text.lower()
        return '[gto]' in lowered and '[mo]' in lowered

    def molecule_from_smiles(self):
        """Файл → Молекула по SMILES… — a 3D starting structure (formats.from_smiles). A small window of its own — under
        the field, while the text has Cyrillic letters, a hint and the text as typed on the Latin layout, one click
        away."""
        text = smiles_dialog(self.w.widget)
        if text:
            self.load_smiles(text)

    def load_smiles(self, text):
        from modules.compass.chemistry.formats import from_smiles

        try:
            mol = from_smiles(text)
            # a new molecule of the project shown
            if self.w.structure_as_new_molecule(mol, '') is None:
                return
            self.w.notify(tr('Структура построена по SMILES — это начальная геометрия, а не оптимизированная.'), 10000)
        except ValueError as exc:
            self.w.error(exc)

    def demo_optimization(self):
        """The synthetic teaching optimization, shown in Compass (before: Spectrum)."""
        try:
            self.w.display_output(
                (ROOT / 'examples' / 'optimization-demo.out').read_text(encoding='utf-8'),
                'optimization-demo.out',
                show=False,
            )
        except (ValueError, OSError) as exc:
            self.w.error(exc)
            return
        if self.w.stack.currentIndex() != 0:
            self.w.navigate(0)
        self.w.structure_tabs.setCurrentIndex(0)
        self.w.trajectory_tool.set_trajectory_open(True, 'steps')

    def export_xyz(self):
        try:
            self.w.save_text(
                tr('Сохранить XYZ'), 'XYZ (*.xyz)', read_xyz(self.w.coordinate_tool.table_molecule().xyz()).xyz(), 'molecule.xyz'
            )
        except (ValueError, OSError) as exc:
            self.w.error(exc)


# the keys of the Russian layout (ЙЦУКЕН) and what they type on the Latin one (QWERTY) — a SMILES typed
# with the wrong layout («ССЩ» for «CCO»)
_RU = 'йцукенгшщзхъфывапролджэячсмитьбюЙЦУКЕНГШЩЗХЪФЫВАПРОЛДЖЭЯЧСМИТЬБЮёЁ№'
_EN = "qwertyuiop[]asdfghjkl;'zxcvbnm,.QWERTYUIOP{}ASDFGHJKL:\"ZXCVBNM<>`~#"
LAYOUT = str.maketrans(_RU, _EN)


def has_cyrillic(text):
    return any('а' <= ch.lower() <= 'я' or ch in 'ёЁ' for ch in text)


def latin_layout(text):
    """The text as the same keys type it on the Latin layout."""
    return text.translate(LAYOUT)


def smiles_dialog(parent):
    """The SMILES typed (stripped), or '' when cancelled."""
    from PySide6.QtWidgets import QDialog, QDialogButtonBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout

    dialog = QDialog(parent)
    dialog.setWindowTitle(tr('Молекула по SMILES'))
    column = QVBoxLayout(dialog)
    column.addWidget(QLabel(tr('SMILES (например, CCO, c1ccccc1, CC(=O)O):')))
    field = QLineEdit()
    field.setMinimumWidth(360)
    column.addWidget(field)
    hint_row = QHBoxLayout()
    hint = QLabel()
    hint.setObjectName('subtitle')
    hint.setWordWrap(True)
    fix = QPushButton()
    hint_row.addWidget(hint, 1)
    hint_row.addWidget(fix)
    column.addLayout(hint_row)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    column.addWidget(buttons)

    def follow(text):
        wrong = has_cyrillic(text)
        hint.setVisible(wrong)
        fix.setVisible(wrong)
        if wrong:
            hint.setText(tr('Похоже, включена русская раскладка: SMILES пишется латиницей.'))
            fix.setText(tr('Заменить на «{}»').format(latin_layout(text)))

    fix.clicked.connect(lambda: field.setText(latin_layout(field.text())))
    field.textChanged.connect(follow)
    follow('')
    dialog.smiles_field, dialog.smiles_hint, dialog.smiles_fix = field, hint, fix
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return ''
    return field.text().strip()

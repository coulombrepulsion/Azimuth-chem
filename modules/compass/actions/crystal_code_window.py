"""«Расчёт → Входной файл CRYSTAL…» of «Компас · Кристалл» and the outputs of CRYSTAL opened in Compass.
§1 PURPOSE
    CRYSTAL (Dovesi et al.) is not run by the program (a licence of its own, usually on a cluster): its input is made
    here for the crystal shown — the task, the functional, the basis set of its library, a pressure — seen as text,
    corrected by hand if needed and saved as .d12; the input of TOPOND (.d3) beside it. Its output (.out) opens as a
    crystal: the last structure in its cell and group, the steps of an optimization in the drawer of steps, a line of
    what it gave (the energy, the gap, the pressure), the elastic constants in a table; an output of TOPOND (.outp) —
    the table of the critical points of ρ (modules/spectrum/readers/crystal_out).
§4 SPECIFICATION
    show(studio) -> CrystalInputWindow | None; CrystalInputWindow(parent, crystal, studio): text() — the input as the
    choices make it (ValueError shown under it); save() / save_topond() -> path | None. open_output(studio, path, text)
    -> True when it was an output of CRYSTAL or of TOPOND; summary(result) -> the line of what the run gave;
    elastic_rows(result), topond_rows(points) -> rows of the tables. open_qe_output(studio, path, text) — an output of
    pw.x (Quantum ESPRESSO) by «Файл → Открыть…» or dropped on the window (0.249.1; the feedback of 2026-11-18: it was
    taken for ORCA and nothing opened): in the folder of a run of a crystal project — that project, Spectrum on that
    run; elsewhere — the crystal of the output in a new project, the run copied into it (without out/, the wave
    functions), Spectrum on it.
§7 TESTS tests/gui/test_gui_files.py::test_crystal_input_window, ::test_a_crystal_output_opens_with_its_steps."""

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QPlainTextEdit, QSpinBox, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.sextant import crystal_inputs as ci

WINDOWS = {}  # 'input', 'elastic', 'topond' -> the window shown last (kept alive here)


def _parent(studio):
    """The window as the parent of a dialog — the studio itself or the window behind a tool's port."""
    widget = getattr(studio, 'widget', studio)
    return widget if isinstance(widget, QWidget) else None


def _shown(studio):
    shown = getattr(studio, 'crystal', None)
    return shown[0] if isinstance(shown, tuple) and shown else shown


def show(studio):
    crystal = _shown(studio)
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    window = CrystalInputWindow(_parent(studio), crystal, studio)
    WINDOWS['input'] = window
    window.show()
    return window


class CrystalInputWindow(QDialog):
    def __init__(self, parent, crystal, studio=None):
        super().__init__(parent)
        self.crystal, self.studio = crystal, studio
        self.setWindowTitle(tr('Входной файл CRYSTAL · ') + (crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.task = QComboBox()
        for name in ci.TASKS:
            self.task.addItem(tr(name), name)
        self.task.setCurrentIndex(list(ci.TASKS).index('Оптимизация с ячейкой'))
        self.functional = QComboBox()
        for key, name in ci.FUNCTIONALS.items():
            self.functional.addItem(tr(name), key)
        self.basis = QComboBox()
        for key, name in ci.BASES.items():
            self.basis.addItem(tr(name), key)
        self.pressure = QDoubleSpinBox()
        self.pressure.setRange(0.0, 500.0)
        self.pressure.setDecimals(2)
        self.pressure.setSuffix(tr(' ГПа'))
        self.shrink = QSpinBox()
        self.shrink.setRange(0, 24)
        self.shrink.setSpecialValueText(tr('по ячейке'))
        form.addRow(tr('Задача'), self.task)
        form.addRow(tr('Функционал'), self.functional)
        form.addRow(tr('Базис'), self.basis)
        form.addRow(tr('Давление'), self.pressure)
        form.addRow(tr('Сетка k (SHRINK)'), self.shrink)
        layout.addLayout(form)
        self.preview = QPlainTextEdit()
        self.preview.setObjectName('code')
        layout.addWidget(self.preview, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        self.note.setObjectName('subtitle')
        layout.addWidget(self.note)
        bottom = QHBoxLayout()
        bottom.addWidget(action_button(tr('Сохранить .d12…'), self.save, 'file-save'))
        bottom.addWidget(action_button(tr('Сохранить .d3 для TOPOND…'), self.save_topond, 'save-topond'))
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        for box in (self.task, self.functional, self.basis):
            box.currentIndexChanged.connect(self.refresh)
        self.pressure.valueChanged.connect(self.refresh)
        self.shrink.valueChanged.connect(self.refresh)
        self.resize(720, 640)
        self.refresh()

    def options(self):
        return ci.Options(functional=self.functional.currentData(), basis=self.basis.currentData(),
                          pressure=self.pressure.value(), shrink=self.shrink.value())

    def text(self):
        return ci.crystal_input(self.crystal, self.task.currentData(), self.options())

    def refresh(self):
        cell_task = self.task.currentData() == 'Оптимизация с ячейкой'
        self.pressure.setEnabled(cell_task)
        if not cell_task and self.pressure.value():
            self.pressure.blockSignals(True)
            self.pressure.setValue(0.0)
            self.pressure.blockSignals(False)
        try:
            text = self.text()
        except ValueError as exc:
            self.preview.setPlainText('')
            self.note.setText(str(exc))
            return
        self.preview.setPlainText(text)
        number = ci.geometry(self.crystal)[0]
        lines = [tr('Группа № {} в установке, которую CRYSTAL берёт по номеру; атомы — независимая часть.').format(number)
                 if number > 1 else tr('Вся ячейка в P 1: установку группы для CRYSTAL найти не удалось (расчёт '
                                       'верный, но без выигрыша от симметрии).'),
                 tr('Базис — из библиотеки CRYSTAL (BASISSET, CRYSTAL17 и новее); текст можно поправить перед '
                    'сохранением. Давление — EXTPRESS, 1 Хартри/Бор³ = 29421 ГПа.')]
        self.note.setText(' '.join(lines))

    def _save(self, text, suffix, caption):
        name = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in (self.crystal.title or 'crystal'))
        path, _ = QFileDialog.getSaveFileName(self, caption, str(Path.home() / (name + suffix)),
                                              f'CRYSTAL (*{suffix})')
        if not path:
            return None
        from azimuth.files import atomic_write

        try:
            atomic_write(path, text)
        except OSError as exc:
            self.note.setText(str(exc))
            return None
        if self.studio is not None and hasattr(self.studio, 'notify'):
            self.studio.notify(tr('Сохранено: ') + path, 8000)
        return path

    def save(self):
        text = self.preview.toPlainText()
        if not text.strip():
            return None
        return self._save(text, '.d12', tr('Входной файл CRYSTAL'))

    def save_topond(self):
        return self._save(ci.topond_input(), '.d3', tr('Входной файл TOPOND'))


# -- outputs ------------------------------------------------------------------------------------------------------------
def basis_text(result, name=''):
    """The basis set of an output of CRYSTAL — its name after BASISSET;
    a basis written by hand has no name in the output: the one in the name of the file, said as such, or «свой базис»
    with its number of atomic orbitals."""
    from modules.spectrum.readers import crystal_out as co

    if result.basis:
        return result.basis
    guessed = co.basis_from_name(Path(name).name) if name else ''
    size = tr(', {} АО').format(result.basis_ao) if result.basis_ao else ''
    if guessed:
        return tr('{} (по имени файла{})').format(guessed, size)
    return tr('свой базис{}').format(size)


def summary(result, name=''):
    """The line of what a run of CRYSTAL gave."""
    parts = [result.version.strip() or 'CRYSTAL']
    if result.method:
        parts.append(result.method + ' / ' + basis_text(result, name))
    if result.energy is not None:
        parts.append(tr('E = {} Хартри').format(f'{result.energy:.8f}'))
    if result.optimization:
        parts.append(tr('оптимизация сошлась за {} шагов').format(result.steps) if result.converged else
                     tr('оптимизация не сошлась ({} шагов)').format(result.steps))
    if result.external:
        parts.append(tr('давление {} ГПа').format(f'{result.external:.2f}'))
    if result.gap is not None:
        parts.append(tr('щель {} эВ ({})').format(f'{result.gap:.3f}', tr('прямая') if result.gap_kind == 'direct'
                                                   else tr('непрямая')))
    elif result.conducting:
        parts.append(tr('похоже на металл'))
    if result.moduli.get('K_H') is not None:
        parts.append(tr('K = {} ГПа (Хилл)').format(f"{result.moduli['K_H']:.1f}"))
    if result.error:
        parts.append(tr('ошибка: ') + result.error)
    elif not result.done:
        parts.append(tr('расчёт не закончен'))
    return ' · '.join(parts) + '.'


def elastic_rows(result):
    rows = [[f'C{i + 1}j'] + [f'{v:.2f}' for v in row] for i, row in enumerate(result.elastic or ())]
    names = {'K_V': tr('K Фойгт'), 'K_R': tr('K Ройсс'), 'K_H': tr('K Хилл'), 'G_V': tr('G Фойгт'),
             'G_R': tr('G Ройсс'), 'G_H': tr('G Хилл'), 'E_H': tr('E Хилл'), 'v_H': tr('ν Хилл')}
    lines = ', '.join(f'{names[k]} {v:g}' for k, v in result.moduli.items() if k in names)
    return rows, lines


KINDS = {'(3,-3)': 'ядро', '(3,-1)': 'связь', '(3,+1)': 'кольцо', '(3,+3)': 'клетка'}


def topond_rows(points):
    rows = []
    for p in points:
        near = ', '.join(f'{s}{n} {d:.3f}' for n, s, d in p.neighbours[:2])
        rows.append((str(p.number), tr(KINDS.get(p.kind, p.kind)), near, f'{p.rho:.5f}', f'{p.laplacian:.5f}',
                     '' if p.g is None else f'{p.g:.5f}', '' if p.v is None else f'{p.v:.5f}',
                     '' if p.h is None else f'{p.h:.5f}', '' if p.ratio is None else f'{p.ratio:.3f}',
                     '' if p.ellipticity is None else f'{p.ellipticity:.3f}'))
    return rows


def _run_of_project(folder):
    """(manifest, index of the run) when folder is a run of a crystal project (<project>/calculations/<run>), else
    None."""
    from azimuth import crystal_projects, projects
    from modules.compass.chemistry import crystal_results

    manifest = folder.parent.parent / projects.MANIFEST
    if folder.parent.name != 'calculations' or not manifest.is_file():
        return None
    try:
        if not crystal_projects.is_crystal(manifest):
            return None
        found = [k for k, run in enumerate(crystal_results.runs(manifest)) if run.folder.resolve() == folder.resolve()]
    except (OSError, ValueError, KeyError):
        return None
    return (manifest, found[-1]) if found else None


def _show_run(studio, index=None):
    """Spectrum on the results of the crystal project shown: the run index (the last one when None)."""
    if hasattr(studio, 'navigate'):
        studio.navigate(2)
    view = getattr(studio, 'crystal_results', None)
    if view is not None and index is not None and 0 <= index < len(getattr(view, 'run_list', [])):
        view.runs.setCurrentIndex(index)
        view.choose(index)
    return view


def open_qe_output(studio, path, text):
    """§4: an output of pw.x opened as the crystal it computed, with its results in Spectrum."""
    import shutil
    from datetime import datetime

    from azimuth import crystal_projects
    from modules.compass.chemistry.surface import write_cif
    from modules.spectrum.readers import qe

    path = Path(path)
    folder = path.parent
    known = _run_of_project(folder)
    if known is not None:  # a run of a project: the project, Spectrum on this run
        manifest, index = known
        studio.open_project_path(str(manifest))
        return _show_run(studio, index)
    crystal = qe.crystal_of(text, folder.name if path.stem == 'pw' else path.stem)
    if crystal is None:
        raise ValueError(tr('В выводе Quantum ESPRESSO нет ячейки и атомов — кристалл не построить.'))
    text_cif, name = write_cif(crystal), crystal.title
    made = None
    if hasattr(studio, 'projects_root'):  # a project of its own — not one more crystal of the project shown
        made = crystal_projects.create(studio.projects_root('crystal'), name, text_cif)
    studio.crystal_tool.open_crystal_text(text_cif, name + '.out', project=made)
    project = studio.research_path() if hasattr(studio, 'research_path') else None
    if not project or not crystal_projects.is_crystal(project):
        return None
    target = Path(project).parent / 'calculations' / folder.name
    if not target.exists():  # the run beside the project, its wave functions left where they are (gigabytes)
        shutil.copytree(folder, target, ignore=shutil.ignore_patterns('out', '*.save', '*.wfc*', '*.hdf5'))
    result = qe.read(text)
    stamp = datetime.fromtimestamp(path.stat().st_mtime).isoformat(timespec='seconds')
    crystal_projects.record_run(project, {'folder': f'calculations/{folder.name}', 'task': result.calculation or 'scf',
                                          'time': stamp, 'energy_ry': result.energy, 'place': 'local', 'program': 'qe'})
    if hasattr(studio, 'refresh_project_navigation'):
        studio.refresh_project_navigation()
    return _show_run(studio)


def open_output(studio, path, text):
    """An output of CRYSTAL or of TOPOND opened in Compass; False when the text is neither."""
    from modules.spectrum.readers import crystal_out as co

    name = Path(path).name
    if co.is_topond(text):
        from modules.compass.actions.qe_results import TableWindow

        points = co.topond(text)
        if not points:
            studio.notify(tr('В выводе TOPOND нет критических точек.'), 8000)
            return True
        heads = ['№', tr('Тип'), tr('Ближайшие атомы, Å'), 'ρ', '∇²ρ', 'G', 'V', 'H = G + V', '|V|/G', 'ε']
        lines = [tr('Критические точки электронной плотности, найденные TOPOND (атомные единицы). Расстояния — от '
                    'точки до ближайших атомов. H < 0 и |V|/G > 1 — обобществлённое или промежуточное взаимодействие, '
                    'H > 0 и |V|/G < 1 — замкнутые оболочки (Espinosa и др., 2002).')]
        window = TableWindow(_parent(studio), tr('TOPOND · ') + name, heads, topond_rows(points), lines)
        WINDOWS['topond'] = window
        window.show()
        return True
    if not co.is_crystal(text):
        return False
    result = co.read(text)
    crystal = co.final_crystal(result, result.title or Path(path).stem)
    if crystal is None:
        studio.notify(tr('В выводе CRYSTAL нет геометрии кристалла.'), 8000)
        return True
    from modules.compass.chemistry.surface import write_cif

    studio.crystal_tool.open_crystal_text(write_cif(crystal), name)
    # what the output gave — into the list of its project
    project = studio.research_path() if hasattr(studio, 'research_path') else None
    if project and result.energy is not None:
        from azimuth import crystal_projects

        try:
            if crystal_projects.is_crystal(project):
                method = result.method + ' / ' + basis_text(result, name) if result.method else ''
                crystal_projects.set_result(project, ' · '.join(p for p in (result.version.strip(), method) if p),
                                            result.energy, pressure=result.external or result.pressure)
                # studio is the port of the opening tool —
                # research_path was not in it, hasattr said no and nothing was written
                if hasattr(studio, 'refresh_project_navigation'):
                    studio.refresh_project_navigation()
        except (OSError, ValueError, KeyError):
            pass
    raw = co.steps(text)
    if len(raw) > 1:
        from modules.compass.chemistry import crystal_steps

        studio.trajectory_tool.load_crystal_steps(crystal_steps.make_steps(raw, crystal.title),
                                                  tr('оптимизация CRYSTAL · {}').format(name), Path(path).parent)
    if result.elastic is not None:
        from modules.compass.actions.qe_results import TableWindow

        rows, moduli = elastic_rows(result)
        window = TableWindow(_parent(studio), tr('Упругие константы · ') + name,
                             ['', '1', '2', '3', '4', '5', '6'], rows,
                             [tr('Упругие постоянные Cij, ГПа (нотация Фойгта), — ELASTCON CRYSTAL.'),
                              tr('Модули, ГПа: ') + moduli if moduli else ''])
        WINDOWS['elastic'] = window
        window.show()
    studio.notify(summary(result, name), 20000)
    return True

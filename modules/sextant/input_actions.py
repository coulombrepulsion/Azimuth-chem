"""InputTool (window.input_tool, a part of the window; was the mixin InputActions of SextantWorkspace, split
from it on 2026-11-08): the input file of Sextant — the preview made from the settings, its own edit and the
check of it (input_check), saving it and the inputs of a set, opening an input file."""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QDesktopServices, QTextCursor, QTextFormat
from PySide6.QtWidgets import QFileDialog, QMessageBox, QTextEdit

from azimuth import quill
from azimuth.core import NEB_TASK, TASKS, auto_title, file_base, orca_input
from azimuth.i18n import combo_key, set_combo_key, tr
from modules.sextant import advice, input_check, inputs, runner
from modules.sextant.inputs import NAMES

CONSTRAINT_PLACE = {'orca': 'блок %geom', 'gaussian': 'Opt=ModRedundant', 'psi4': 'set optking', 'xtb': 'файл xcontrol',
                    'mopac': 'флаги оптимизации атомов', 'gamess': '—', 'nwchem': '—'}
SAVE = {'orca': ('ORCA (*.inp)', 'calculation.inp'), 'gaussian': ('Gaussian (*.gjf *.com)', 'calculation.gjf'),
        'psi4': ('Psi4 (*.dat *.in)', 'input.dat'), 'xtb': ('XYZ (*.xyz)', 'molecule.xyz'),
        'mopac': ('MOPAC (*.mop)', 'calculation.mop'), 'gamess': ('GAMESS (*.inp)', 'calculation.inp'),
        'nwchem': ('NWChem (*.nw)', 'calculation.nw')}


class InputTool:
    """Was the mixin InputActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        '_edit_base',
        '_filling_preview',
        '_generated',
        'basis',
        'batch_tool',
        'calc_title',
        'calculation',
        'calculation_constraints',
        'calculation_molecule',
        'charge',
        'confirm_replace',
        'cores',
        'couplings',
        'dispersion',
        'error',
        'export_button',
        'follow_molecule_state',
        'found_program',
        'input_edited',
        'input_edited_note',
        'input_edited_row',
        'input_error',
        'install_job',
        'load_molecule',
        'method',
        'method_picker',
        'mpi_button',
        'navigate',
        'neb_end',
        'neb_images',
        'notify',
        'preview',
        'program',
        'program_kind',
        'run_button',
        'run_tool',
        'save_text',
        'set_inputs_button',
        'spin',
        'state_info',
        'state_note',
        'task',
        'time_estimate',
        'update_advice',
        'update_calc_card',
        'update_scan_list',
        'where',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def refresh_input(self):
        kind = self.w.program_kind() if self.w.has('program') else 'orca'
        if self.w.has('set_inputs_button'):  # only when the tab has a set of structures
            count = len(self.structure_set())
            self.w.set_inputs_button.setVisible(count > 1)
            self.w.set_inputs_button.setToolTip(tr(f'Входные файлы для всего набора структур ({count}) — одни настройки, свои координаты'))
        self.w.batch_tool.update_batch_buttons()
        self.w.update_scan_list()
        try:
            mol = self.w.calculation_molecule()  # without the dummy atoms X
            if self.w.has('state_note'):
                self.w.follow_molecule_state(mol)
            calc = self.w.calculation()
            fixed = self.w.calculation_constraints()
            if kind == 'xtb':
                calc = replace(calc, dispersion='')  # the switch is off for xtb; D4 is part of GFN2-xTB
            text = inputs.preview(kind, mol, calc, fixed, self.neb_settings())
            self.w._generated = text
            if self.w.has('calc_title'):  # the automatic name as the placeholder of «Название»
                self.w.calc_title.setPlaceholderText(auto_title(mol, calc, kind))
            if not getattr(self.w, 'input_edited', False):
                self.fill_preview(text)
            self.show_input_edited()
            self.w.input_error.hide()
            self.w.export_button.setEnabled(True)
            if kind == 'xtb':
                info = tr(
                    f'Электронов: {mol.electrons(calc.charge)}\nНеспаренных электронов (--uhf): {calc.multiplicity - 1}'
                )
            else:
                info = tr(
                    f'Электронов: {mol.electrons(calc.charge)}\nМультиплетность: {calc.multiplicity}'
                )
            info = tr(f'Заряд: {calc.charge:+d}' if calc.charge else 'Заряд: 0') + '\n' + info
            # the charge, the electrons and the multiplicity on one line: five lines and the time were taller than the
            # model beside them, and the card of a window of 1133 × 730 cut them (0.222.0)
            info = ' · '.join(line.strip() for line in info.split('\n') if line.strip())
            if kind == 'mopac':  # no basis set — no basis functions, the method alone
                atoms = sum(1 for a in mol.atoms if a.symbol != 'X')
                info += '\n' + tr(f'Атомов: {atoms}')
                info += '\n' + f'{calc.method} · ' + tr(combo_key(self.w.task))
            elif kind != 'xtb':  # the card had empty room — what the calculation is and how big
                from modules.sextant import estimate

                atoms = sum(1 for a in mol.atoms if a.symbol != 'X')
                functions = estimate.basis_functions(mol, calc.basis)
                info += '\n' + tr(f'Атомов: {atoms} · базисных функций: ≈{functions:.0f}')
                info += '\n' + f'{calc.method}/{calc.basis} · ' + tr(combo_key(self.w.task))
            if fixed:
                info += '\n' + (
                    tr(f'Ограничений оптимизации: {len(fixed)} ({tr(CONSTRAINT_PLACE[kind])}).')
                    if 'Opt' in TASKS[calc.task]
                    else tr('Ограничения заданы, но задача — не оптимизация: в файл они не входят.')
                )
            neb = self.neb_settings()
            if calc.task == NEB_TASK and neb:
                info += '\n' + tr(f'Путь реакции: конец — «{neb[0].title}», промежуточных структур {neb[1]}.')
            self.w.state_info.setText(info)
            from modules.sextant import estimate

            spent = estimate.text(estimate.seconds(mol, calc, kind))
            self.w.time_estimate.setText(tr(f'Примерное время расчёта: {spent}') if spent else '')
            self.w.time_estimate.setVisible(bool(spent))
            self.w.update_calc_card()
            valid = True
        except ValueError as exc:
            self.w._generated = None
            if not getattr(self.w, 'input_edited', False):
                self.fill_preview('')
            self.show_input_edited()
            self.w.input_error.setText(str(exc))
            self.w.input_error.show()
            self.w.export_button.setEnabled(False)
            # the reason itself — the line under the input file is hidden while the calculation is shown
            self.w.state_info.setText(tr('Входной файл не собран:') + ' ' + str(exc))
            if self.w.has('time_estimate'):
                self.w.time_estimate.hide()
            try:
                self.w.update_calc_card()
            except ValueError:
                pass
            valid = False
        if self.w.has('run_button'):
            # the button follows the place chosen: a calculation on this computer does not keep it from a server
            self.w.run_button.setEnabled(valid and not self.w.run_tool.run_blocked(getattr(self.w, 'where', 'local')))
        if self.w.has('mpi_button'):  # ORCA on several processes without mpirun
            needs = kind == 'orca' and self.w.cores.value() > 1 and getattr(self.w, 'found_program', None) is not None
            self.w.mpi_button.setVisible(needs and getattr(self.w, 'where', 'local') == 'local'
                                       and runner.find_mpirun(self.w.found_program) is None and self.w.install_job is None)
        if self.w.has('method_picker'):
            self.w.update_advice()

    def open_msmpi_page(self):
        """The page of Microsoft MPI (msmpisetup.exe); after installing, the program is restarted (PATH)."""
        QDesktopServices.openUrl(QUrl(runner.MSMPI_PAGE))
        self.w.notify(tr('Скачайте и установите msmpisetup.exe, затем перезапустите «Азимут» — ORCA сможет считать на '
                       'нескольких процессах.'), 15000)

    def export_program_input(self):
        """«Сохранить входной файл выбранной программы…»: .inp, .gjf, input.dat or, for xtb, the XYZ."""
        kind = self.w.program_kind()
        try:
            calc = self.w.calculation()
            if kind == 'xtb':
                calc = replace(calc, dispersion='')
            files = inputs.input_files(kind, self.w.calculation_molecule(), calc, self.w.calculation_constraints(), self.neb_settings())
            pattern, _ = SAVE[kind]
            name = next(iter(files))  # named after the calculation
            if 'end.xyz' in files:  # ORCA reads the product from end.xyz next to the input
                self.w.notify(tr('Для пути реакции рядом с входным файлом нужен end.xyz — сохраните его тоже.'), 10000)
            edited = self.edited_input()  # the file as edited
            self.w.save_text(tr('Сохранить входной файл'), pattern, edited if edited is not None else files[next(iter(files))], name)
        except (ValueError, OSError) as exc:
            self.w.error(exc)

    def export_input(self):
        try:
            self.w.save_text(
                tr('Сохранить входной файл'),
                'ORCA (*.inp)',
                orca_input(self.w.calculation_molecule(), self.w.calculation(), self.w.calculation_constraints(), *(self.neb_settings() or (None, 8))),
                file_base(self.w.calculation_molecule(), self.w.calculation()) + '.inp',
            )
        except (ValueError, OSError) as exc:
            self.w.error(exc)

    def neb_settings(self):
        """(end structure, images) of the reaction path set in Compass, or None."""
        end = getattr(self.w, 'neb_end', None)
        return (end, getattr(self.w, 'neb_images', 8)) if end is not None else None

    # an input file of ORCA or Gaussian opened in Sextant --------------------------------------------------
    def open_input_file(self, path=None):
        """The molecule, charge and multiplicity of the file into the tab, the program, method, basis, task and
        dispersion that are read back (inputs.read_settings), and the file itself as the edited input — it is run as it
        is. Returns the program or None."""
        from modules.compass.chemistry import formats

        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self.w.widget, tr('Открыть входной файл'), str(self.w.run_tool.jobs_root() if self.w.run_tool.jobs_root().exists() else Path.home()),
                tr('Входные файлы ORCA и Gaussian (*.inp *.gjf *.com *.gjc);;Все файлы (*)'))
        if not path:
            return None
        try:
            text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
            kind = inputs.input_kind(path, text)
            reader = formats.read_gaussian_input if kind == 'gaussian' else formats.read_orca_input
            molecule, charge, multiplicity = reader(text)
        except (OSError, ValueError, IndexError) as exc:
            self.w.error(exc)
            return None
        if self.w.has('confirm_replace') and not self.w.confirm_replace():
            return None
        self.w.load_molecule(replace(molecule, title=molecule.title or Path(path).stem))
        self.w.program.setCurrentIndex(max(0, self.w.program.findData(kind)))
        found = inputs.read_settings(kind, text)
        for combo, key in ((self.w.method, 'method'), (self.w.basis, 'basis')):
            index = combo.findData(found.get(key))
            if index >= 0:
                combo.setCurrentIndex(index)
        set_combo_key(self.w.task, found['task'])
        if self.w.has('couplings'):
            self.w.couplings.setChecked(bool(found.get('couplings')))
        self.w.dispersion.setCurrentIndex(max(0, self.w.dispersion.findData(found.get('dispersion', ''))))
        self.w.charge.setValue(charge)
        self.w.spin.setValue(multiplicity)
        if self.w.has('navigate'):
            self.w.navigate(1)
        self.refresh_input()
        self.restore_input_edit((text.rstrip('\n') + '\n', getattr(self.w, '_generated', None) or ''))
        self.w.notify(tr(f'Открыт {Path(path).name}: будет запущен этот файл; «Собрать файл заново по настройкам» — '
                       'собранный из настроек.'), 9000)
        return kind

    def structure_set(self):
        """The molecules of the project of the tab (the set of «Структуры» of the drawer is gone)."""
        return tuple(self.w.batch_tool.structure_rows()) if self.w.has('batch_tool') else ()

    def export_set_inputs(self, folder=None):
        """An input file for every structure of the set (the settings of Sextant, the charge and multiplicity
        of each structure from its bonds), written into a folder; returns the paths written."""
        structures = self.structure_set()
        if not structures:
            self.w.notify(tr('Набора структур нет: откройте в Компасе несколько файлов или базу SDF («Файл → Открыть…»).'), 9000)
            return []
        kind = self.w.program_kind()
        if folder is None:
            start = self.w.run_tool.jobs_root()
            folder = QFileDialog.getExistingDirectory(self.w.widget, tr('Папка для входных файлов набора'),
                                                      str(start if start.exists() else Path.home()))
        if not folder:
            return []
        try:
            calc = self.w.calculation()
        except ValueError as exc:
            self.w.error(exc)
            return []

        def state(molecule):
            charge, multiplicity, _ = advice.guess_state(molecule)
            return charge, multiplicity

        files, failed = inputs.set_input_files(kind, structures, calc, state)
        written = []
        try:
            for name, text in files.items():
                path = Path(folder) / name
                path.write_text(text, encoding='utf-8')
                written.append(path)
        except OSError as exc:
            self.w.error(exc)
            return written
        note = tr(f'Входных файлов {NAMES[kind]}: {len(written)} — в папке {folder}.')
        if failed:
            note += ' ' + tr(f'Не записаны ({len(failed)}): ') + '; '.join(f'{n}: {why}' for n, why in failed[:2])
        self.w.notify(note, 12000)
        return written

    # the input file edited by hand, the output file followed --------------------------------------------
    def fill_preview(self, text):
        self.w._filling_preview = True
        try:
            if self.w.preview.toPlainText() != text:
                bar = self.w.preview.verticalScrollBar().value()
                self.w.preview.setPlainText(text)
                self.w.preview.verticalScrollBar().setValue(bar)
            self.w.preview.setExtraSelections([])
        finally:
            self.w._filling_preview = False

    def input_text_changed(self):
        if self.w._filling_preview or self.w.preview.isReadOnly():
            return
        # a «change» that leaves the generated text as it was (the colours of the highlighter) is no edit
        if not self.w.input_edited and self.w.preview.toPlainText() == (getattr(self.w, '_generated', None) or ''):
            return
        if not self.w.input_edited:
            self.w.input_edited = True
            self.w._edit_base = getattr(self.w, '_generated', None) or ''
        self.w.preview.setExtraSelections([])
        self.show_input_edited()

    def show_input_edited(self):
        if not self.w.has('input_edited_row'):
            return
        if not self.w.input_edited:
            self.w.input_edited_row.hide()
            return
        stale = getattr(self.w, '_generated', None) != self.w._edit_base
        self.w.input_edited_note.setText(
            tr('Настройки или молекула изменились после правки — файл не пересобран.') if stale
            else tr('Файл изменён вручную: будет запущен он, а не собранный по настройкам.')
        )
        self.w.input_edited_row.show()

    def stored_input_edit(self):
        return (self.w.preview.toPlainText(), self.w._edit_base) if getattr(self.w, 'input_edited', False) else None

    def restore_input_edit(self, edit):
        if edit is None:
            if self.w.input_edited:
                self.w.input_edited = False
                self.refresh_input()
            return
        self.w.input_edited = False
        self.refresh_input()
        self.fill_preview(edit[0])
        self.w.input_edited, self.w._edit_base = True, edit[1]
        self.show_input_edited()

    def insert_block(self, title, block, keyword=''):
        """«Правка → Вставить блок»: the block at its place in the file (input_blocks), one step of undo; the
        file becomes «правлен вручную» as by typing."""
        from PySide6.QtGui import QTextCursor

        from modules.sextant import input_blocks

        edit = self.w.preview
        if edit.isReadOnly():
            return None
        new = input_blocks.inserted(edit.toPlainText(), self.w.program_kind(), block, keyword)
        cursor = edit.textCursor()
        cursor.beginEditBlock()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.insertText(new)
        cursor.endEditBlock()
        moved = edit.textCursor()
        moved.setPosition(max(0, new.find(block)))
        edit.setTextCursor(moved)
        edit.centerCursor()
        self.w.notify(tr('Вставлен блок: {}. «Собрать файл заново по настройкам» вернёт файл к настройкам.').format(tr(title)),
                      8000)
        return new

    def check_input_now(self):
        """«Правка → Проверить входной файл»: the checks made before a run (input_check), now; the lines
        with a problem tinted. Returns the problems."""
        problems = input_check.check(self.w.program_kind(), self.w.preview.toPlainText())
        if problems:
            self.mark_input_problems(problems)
            first = problems[0]
            self.w.notify(tr('Во входном файле замечаний: {}.').format(len(problems)) + ' '
                          + (tr(f'строка {first.line}: ') if first.line else '') + first.text, 12000)
        else:
            self.w.preview.setExtraSelections([])
            self.w.notify(tr('Входной файл проверен: замечаний нет.'), 6000)
        return problems

    def reset_input(self):
        self.w.input_edited = False
        self.refresh_input()
        return self.w.preview.toPlainText()

    def edited_input(self):
        """The text to run instead of the generated one, or None (not edited, or xtb)."""
        if not getattr(self.w, 'input_edited', False) or self.w.program_kind() == 'xtb':
            return None
        return self.w.preview.toPlainText().split('\n# end.xyz\n', 1)[0]  # NEB: end.xyz is written by the program

    def check_edited_input(self, kind, text):
        """input_check on the edited file; True — run it (no problems, or the user runs it anyway)."""
        problems = input_check.check(kind, text)
        if getattr(self.w, '_generated', None) != self.w._edit_base:
            problems.append(input_check.Problem(0, tr('Настройки или молекула изменились после вашей правки: в файле — прежние.')))
        if not problems:
            return True
        self.mark_input_problems(problems)
        return self.confirm_input_problems(problems)

    def mark_input_problems(self, problems):
        """The lines with a problem are tinted in the file, the first one is scrolled into view."""
        selections = []
        document = self.w.preview.document()
        for problem in problems:
            block = document.findBlockByNumber(problem.line - 1) if problem.line else None
            if block is None or not block.isValid():
                continue
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor(208, 74, 60, 60))
            selection.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
            selection.cursor = QTextCursor(block)
            selections.append(selection)
        self.w.preview.setExtraSelections(selections)
        if selections:
            self.w.preview.setTextCursor(selections[0].cursor)
            self.w.preview.centerCursor()
        return len(selections)

    def confirm_input_problems(self, problems):
        lines = [(tr(f'строка {p.line}: ') if p.line else '') + p.text for p in problems[:8]]
        if len(problems) > 8:
            lines.append(tr(f'… и ещё {len(problems) - 8}'))
        box = QMessageBox(self.w.widget)
        quill.set_icon(box, 'input-check', QMessageBox.Icon.Warning)  # Quill with the red pencil
        box.setWindowTitle(tr('Проверка входного файла'))
        box.setText(tr('Во входном файле, похоже, есть ошибки — программа может сразу остановиться.'))
        box.setInformativeText('\n'.join(lines))
        fix = box.addButton(tr('Исправить'), QMessageBox.ButtonRole.RejectRole)
        box.addButton(tr('Запустить как есть'), QMessageBox.ButtonRole.AcceptRole)
        box.setDefaultButton(fix)
        box.exec()
        return box.clickedButton() is not fix

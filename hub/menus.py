"""HubMenus: the menus of the header of the hub — the menus of each section (Compass, Sextant, Spectrum) built
from the actions of Studio, and the label of the theme button; «Проект» of Compass, «Сервер» of Sextant and
«Справка» of every section. A mixin of HubWindow (hub/window.py)."""

from PySide6.QtGui import QAction, QActionGroup
from PySide6.QtWidgets import QMenu

from azimuth.i18n import to_source, tr
from azimuth.ui import smooth
from hub.branding import glyph_icon
from hub.texts import TEXT
from hub import menus_sections as _sections


class HubMenus:
    """Mixin of HubWindow (hub/window.py)."""

    # -- menus of the sections ------------------------------------------------------
    def _studio_actions(self):
        found, menus = [], [m for m in self.studio.menuBar().findChildren(QMenu)]
        for menu in menus:
            found.extend(a for a in menu.actions() if not a.isSeparator() and a.menu() is None)
        return found

    def studio_action(self, source):
        """The Studio menu action created with the Russian text source."""
        for each in self._studio_actions():
            if to_source(each.text()) == source:
                return each
        raise KeyError(source)

    def _studio_menu(self, source):
        for menu in self.studio.menuBar().findChildren(QMenu):
            if to_source(menu.title()) == source:
                return menu
        raise KeyError(source)

    def _section_menus(self, ident):
        """Fresh menus for Compass, Sextant or Spectrum; each shows only what the section can do."""
        for menu in self._header_menus:
            menu.deleteLater()
        self._header_menus = []
        studio = self.studio

        def menu(title, *parts):
            box = smooth(QMenu(tr(title), self))
            box.setToolTipsVisible(True)
            for part in parts:
                if part is None:
                    box.addSeparator()
                elif isinstance(part, QMenu):
                    box.addMenu(part)
                elif isinstance(part, QAction):
                    box.addAction(part)
                else:
                    box.addAction(self.studio_action(part))
            self._header_menus.append(box)
            return box

        def own(title, callback, checkable=False):
            item = QAction(tr(title), self._header_menus[-1] if self._header_menus else self)
            # «triggered» passes the checked state (False): only a checkable item gets it, others are called with no
            # arguments (otherwise verify_installation would read it as show=False)
            if checkable:
                item.triggered.connect(callback)
            else:
                item.triggered.connect(lambda checked=False, run=callback: run())
            item.setCheckable(checkable)
            return item

        def print3d_window():  # the window of a model for 3D printing, imported when asked
            from modules.compass.actions import print3d_window as module

            return module

        quit_ = studio.exit_action

        def help_menu():
            # «Справка» in every section: «О программе», the manual, the journal and the folder of the logs
            from hub.about import ChangelogDialog, open_manual

            def manual():
                self.manual_dialog = open_manual(self, self.language)

            def journal():
                self.journal_dialog = ChangelogDialog(self, self.language)
                self.journal_dialog.open()

            def handbook(tab):  # units, solvents, scaling factors, measured data (azimuth/handbook.py)
                from azimuth.handbook_window import open_handbook

                molecule = getattr(studio, 'molecule', None)
                formula = molecule.formula if molecule is not None and molecule.atoms else ''
                open_handbook(self, tab, formula=formula)

            def elements_table():  # the periodic table and the table of isotopes
                from azimuth.element_window import ElementsDialog

                self.elements_dialog = ElementsDialog(self)
                self.elements_dialog.show()

            box = menu(
                'Справка',
                own('Руководство', manual),
                own('Что нового', journal),
                own('Таблица Менделеева', elements_table),
                menu('Справочник',
                     own('Единицы и константы', lambda: handbook('units')),
                     own('Растворители', lambda: handbook('solvents')),
                     own('Множители частот', lambda: handbook('factors')),
                     own('Опытные данные', lambda: handbook('experiment'))),
                None,
                own('Проверить установку…', lambda: self.verify_installation()),  # a lambda: «triggered» must not reach
                # «show»
                own('Папка журналов программы', self.open_log_folder),
                'Отчёт об ошибке…',
                None,
                own('О программе', self.show_about),
            )
            # a search field on top, as in the Help menu of macOS
            from hub import menu_search

            menu_search.install(box, self)
            return box

        def picture_menu(gif='GIF: вращение молекулы'):
            """«Сохранить рисунок» of Compass, shared by the molecule and the crystal pages."""
            from azimuth import defaults

            box = menu('Сохранить рисунок',
                       own('Снимок PNG', lambda: studio.picture_tool.save_screenshot(1)),
                       large := own('Снимок высокого разрешения',  # ×N of «Настройки → Снимки»
                                    lambda: studio.picture_tool.save_screenshot(defaults.get('picture_scale'))),
                       own('Рисунок SVG (подписи — векторами)', lambda: studio.view_tool.save_document('.svg')),
                       own('Рисунок PDF (подписи — векторами)', lambda: studio.view_tool.save_document('.pdf')),
                       own(gif, studio.picture_tool.save_rotation_gif))
            clear = own('Прозрачный фон', studio.picture_tool.set_transparent_pictures, checkable=True)
            box.addSeparator()
            box.addAction(clear)

            def shown():
                clear.blockSignals(True)
                clear.setChecked(studio.viewer.transparent)
                clear.blockSignals(False)
                large.setText(tr('Снимок высокого разрешения') + f' (×{defaults.get("picture_scale")})')

            box.aboutToShow.connect(shown)
            return box

        def compare_menu():
            """«Сравнение структур»: the structure from a file and its settings, then «Сравнить с вкладкой»."""
            box = studio.compare_menu
            tabs = studio.chem_menus['compare_tabs']

            def shown():  # after the menu is filled (overlay_actions.fill_compare_menu clears it)
                if tabs not in [a.menu() for a in box.actions()]:
                    box.addSeparator()
                    box.addMenu(tabs)

            if not box.property('hubTabs'):
                box.setProperty('hubTabs', True)
                box.aboutToShow.connect(shown)
            return box

        if ident == 'compass':
            return _sections.compass_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window)
        if ident == 'crystal':
            return _sections.crystal_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window)
        if ident == 'sextant':
            return _sections.sextant_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window)
        if ident == 'spectrum':
            return _sections.spectrum_menus(self, studio, menu, own, help_menu, picture_menu, compare_menu, quit_, print3d_window)
        return []

    def _unit_converter(self):
        from azimuth.handbook_window import open_handbook

        return open_handbook(self, 'units')

    def _measured_data(self):
        """The databases of measured data with the formula of the result shown in Spectrum (of the molecule of
        Compass when no result is open)."""
        from azimuth.handbook_window import open_handbook

        studio = self.studio
        formula = getattr(studio.vibrations, 'source_formula', '') or ''
        if not formula and getattr(studio, 'molecule', None) is not None and studio.molecule.atoms:
            formula = studio.molecule.formula
        return open_handbook(self, 'experiment', formula=formula)

    # -- «Проект» of Compass, «Сервер» of Sextant, «Справка» ------------------------------------------------------
    def _project_menu(self, menu, own):
        """«Проект» of Compass: what the panel of the molecules of a project and its menu do, in one place; the items
        that need an open project are off without one."""
        studio = self.studio
        add = own('Добавить молекулы…', studio.add_project_files_dialog)
        panel = own('Список молекул проекта', studio.toggle_project_molecules, checkable=True)
        single = own('Одиночный режим', lambda: studio.set_project_batch_mode(False), checkable=True)
        batch = own('Пакетный режим', lambda: studio.set_project_batch_mode(True), checkable=True)
        modes = QActionGroup(self)
        for item in (single, batch):
            modes.addAction(item)
        remove = own('Удалить из проекта…', lambda: studio.remove_project_molecules())
        back = own('Вернуть удалённые', lambda: studio.restore_project_molecules())
        history = own('История и файлы проекта…', studio.show_research_project)
        # the reaction of the project — the roles are given in the menu of the list (right click)
        gibbs = own('ΔG реакции…', lambda: studio.project_reaction())
        box = menu(
            'Проект',
            # creating and opening projects is in «Файл»; here only the molecules of the project
            panel,
            add,
            remove,
            back,
            None,
            single,
            batch,
            None,
            gibbs,
            history,
            # «Сохранить» and «Сохранить как» are in «Файл» only
        )

        def shown():
            opened = studio.research_path() is not None
            for item in (add, remove, single, batch, history, gibbs):
                item.setEnabled(opened)
            kept = getattr(studio, '_project_removed', None)
            back.setEnabled(opened and kept is not None and kept[0] == studio.research_path())
            for item, value in ((panel, studio.project_menu_button.isChecked()),
                                (batch, opened and studio.project_batch_mode()),
                                (single, opened and not studio.project_batch_mode())):
                item.blockSignals(True)
                item.setChecked(bool(value))
                item.blockSignals(False)

        box.aboutToShow.connect(shown)
        return box

    def _sextant_view_menu(self, menu, own):
        """«Вид» of Sextant — the input file and the window of the calculation, the result of the last one in
        Compass or Spectrum (the buttons of that window, enabled when they are there)."""
        studio = self.studio
        expand = own('Развернуть входной файл', lambda: studio.expand_input_button.click(), checkable=True)
        compass = own('Результат в Компасе', lambda: studio.run_tool.go_to_result('compass'))
        spectrum = own('Результат в Спектре', lambda: studio.run_tool.go_to_result('spectrum'))
        box = menu(
            'Вид',
            own('Входной файл', studio.show_input_card),
            expand,
            own('Окно расчёта', studio.show_job_window),
            None,
            compass,
            spectrum,
        )

        def shown():
            expand.blockSignals(True)
            expand.setChecked(studio.expand_input_button.isChecked())
            expand.blockSignals(False)
            window = studio.job_window
            compass.setEnabled(not window.compass_button.isHidden() and window.compass_button.isEnabled())
            spectrum.setEnabled(not window.spectrum_button.isHidden() and window.spectrum_button.isEnabled())

        box.aboutToShow.connect(shown)
        return box

    def _server_menu(self, menu, own):
        """«Сервер» of Sextant: where to calculate and the server — the buttons of the row of the program, shown only
        while «Сервер» is chosen, are found here always."""
        studio = self.studio
        here = own('Считать на этом компьютере', lambda: studio.where_buttons['local'].click(), checkable=True)
        there = own('Считать на сервере', lambda: studio.where_buttons['server'].click(), checkable=True)
        places = QActionGroup(self)
        for item in (here, there):
            places.addAction(item)
        box = menu(
            'Сервер',
            here,
            there,
            None,
            own('Профиль сервера…', studio.run_tool.edit_server),
            own('Проверить подключение к серверу', studio.run_tool.check_server),
            own('Файлы на сервере', studio.run_tool.open_server_files),
            own('Очередь кластера…', lambda: studio.server_watch_tool.open_cluster_queue()),  # squeue, scancel
        )

        def shown():
            for item, key in ((here, 'local'), (there, 'server')):
                item.blockSignals(True)
                item.setChecked(studio.where == key)
                item.blockSignals(False)

        box.aboutToShow.connect(shown)
        return box

    def open_log_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from azimuth import crash_report

        folder = crash_report.log_dir()
        folder.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        return folder

    def verify_installation(self, show=True):
        """«Справка → Проверить установку…»: verify_install.py of the program folder in a process of its own (the
        libraries, the bundled files, the symmetry engine, a VTK surface), its lines in a window.
        Returns (passed, text)."""
        import subprocess
        import sys
        from pathlib import Path

        from PySide6.QtWidgets import QMessageBox

        from azimuth.tasks import run_waiting

        script = Path(__file__).resolve().parents[1] / 'verify_install.py'
        if getattr(sys, 'frozen', False) or not script.is_file():
            passed, text = False, tr('В этой сборке программы проверка установки не входит: она делается при установке.')
        else:
            def work(step):
                return subprocess.run([sys.executable, str(script)], capture_output=True, text=True, timeout=900,
                                      encoding='utf-8', errors='replace', cwd=str(script.parent))

            try:
                # waited on the pill of the section (the Studio tells; the hub has no pill of its own)
                done = run_waiting(getattr(self, 'studio', None) or self, tr('Проверка установки…'), work, alone=False)
                passed, text = done.returncode == 0, (done.stdout + done.stderr).strip()
            except (OSError, subprocess.SubprocessError) as exc:
                passed, text = False, str(exc)
        if show:
            # the checks are listed once, in the language of the program (no «Show details…» of Qt), with Quill;
            # a window, not a sheet
            from PySide6.QtCore import Qt

            from azimuth import quill

            lines, done, total = verify_lines(text)
            head = tr('Установка в порядке') if passed else tr('Проверка нашла неполадки')
            box = QMessageBox(self)
            quill.headline(box, tr('Проверка установки'), '\n'.join(lines))
            box.setText(f'<b>{head}</b>')
            box.setStandardButtons(QMessageBox.StandardButton.Ok)
            quill.set_icon(box, 'install' if passed else 'error',
                           QMessageBox.Icon.Information if passed else QMessageBox.Icon.Warning)
            box.setWindowModality(Qt.WindowModality.ApplicationModal)
            box.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            box.show()
            box.raise_()
            box.activateWindow()
            self.verify_box = box
            studio = getattr(self, 'studio', None)
            if studio is not None:
                studio.notify(head + (tr(': пройдено {} из {}').format(done, total) if total else '') + '.', 8000)
        return passed, text

    def _label_theme_button(self):
        if not hasattr(self, 'theme_button'):
            return
        text = TEXT[getattr(self, 'language', 'ru')]
        title = text['light'] if self.dark else text['dark']
        self.theme_button.setIcon(glyph_icon('sun' if self.dark else 'moon'))
        self.theme_button.setText('' if getattr(self, 'collapsed', False) else title)
        self.theme_button.setToolTip(title)


# the lines of verify_install.py («[OK] Name: detail», «n/m checks passed») in the language of the program
_VERIFY_NAMES = {'Python': 'Python', 'Dependencies': 'Зависимости', 'Assets': 'Файлы программы',
                 'Symmetry': 'Симметрия', 'Surface': 'Поверхности'}
_VERIFY_DETAILS = (
    (r'pinned versions and runtime imports', 'версии библиотек и их загрузка'),
    (r'(\d+) bundled files verified', 'проверено файлов: {}'),
    (r'point group of water: (\S+)', 'точечная группа воды: {}'),
    (r'VTK contour generation \(no window\)', 'построение изоповерхности VTK'),
)


def verify_lines(text):
    """([lines in the language of the program], passed, total) of the output of verify_install.py: «✓ Name — detail»
    (a known detail translated, an unknown one — a failure, a version — as written), the count of the last line."""
    import re

    lines, done, total = [], 0, 0
    for raw in (text or '').splitlines():
        raw = raw.strip()
        found = re.match(r'\[(OK|FAIL)\]\s*([^:]+):\s*(.*)$', raw)
        if found:
            ok, name, detail = found.group(1) == 'OK', found.group(2).strip(), found.group(3).strip()
            for pattern, words in _VERIFY_DETAILS:
                hit = re.fullmatch(pattern, detail)
                if hit:
                    detail = tr(words).format(*hit.groups())
                    break
            lines.append(('✓ ' if ok else '✗ ') + tr(_VERIFY_NAMES.get(name, name)) + ' — ' + detail)
            continue
        count = re.match(r'(\d+)/(\d+) checks passed', raw)
        if count:
            done, total = int(count.group(1)), int(count.group(2))
        elif raw:
            lines.append(raw)
    return lines, done, total

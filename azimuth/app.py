"""The main window of «Азимут» (Studio): the left panel, the File menus, the pages of the modules and the settings."""


from PySide6.QtCore import Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFrame,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QMessageBox,
    QStackedWidget,
)
from .core import Molecule, read_xyz, EXAMPLES
from .icons import iconify
from .controls import HoldButton

from . import quill
from .paths import ROOT
from .ui import label, button
from modules.compass.workspace import CompassWorkspace
from modules.sextant.workspace import SextantWorkspace
from modules.spectrum.workspace import SpectrumWorkspace
from azimuth.project_actions import ProjectActions
from azimuth.i18n import tr

from azimuth.app_style import DARK_STYLE, STYLE, theme_extra, theme_style_sheet  # noqa: F401 — named here by hub/launch.py and the tests
from azimuth.files import atomic_write  # noqa: F401 — also imported from here by tests and tools
from azimuth import app_menus as _menus
from azimuth import app_theme as _theme
from azimuth.app_theme import system_prefers_dark
from azimuth import app_files as _files


def app_icon(dark=False):
    """Application icon (assets/app-icon): the compact drawing for small sizes, the full one above 64 px;
    dark=True: the dark variant (assets/app-icon/dark) for the dark theme."""
    folder = ROOT / 'assets' / 'app-icon' / ('dark' if dark else '')
    result = QIcon()
    for size in (16, 32, 48, 64, 128, 256, 512, 1024):
        result.addFile(str(folder / f'azimuth-{size}.png'))
    return result


def use_fusion(app):
    """The style Fusion for the application — once. With a style sheet set, app.style() is Qt's wrapper of it
    (QStyleSheetStyle), whose name is empty: the check «is it Fusion already?» was always false, and every window
    set the style again — Qt then polished every widget of the application anew (2 of the 3.5 s of a
    window in the tests, growing with the windows left; at the start of the program the style was set twice). The
    application keeps a mark instead."""
    if app is None or app.property('azimuth_fusion'):
        return False
    # the font of the system (Segoe UI on Windows, Helvetica Neue on macOS — the style sheet names them): the typeface
    # carried by the program (azimuth/fonts.py) was drawn too sharp on Windows (the owner, 2026-11-27) and is not set
    app.setStyle(_quiet_wheel_style())
    app.setProperty('azimuth_fusion', True)
    return True


def _quiet_wheel_style():
    """Fusion in which the wheel does not turn a combo box: Qt asks the style
    (SH_ComboBox_AllowWheelScrolling); told no, the combo box passes the wheel on, and the window under it scrolls.
    The list itself, once opened, scrolls as before."""
    from PySide6.QtWidgets import QProxyStyle, QStyle

    class QuietWheel(QProxyStyle):
        def styleHint(self, hint, option=None, widget=None, data=None):
            if hint == QStyle.StyleHint.SH_ComboBox_AllowWheelScrolling:
                return 0
            return super().styleHint(hint, option, widget, data)

    style = QuietWheel('Fusion')
    style.setObjectName('fusion')
    return style


def _windows():
    """The top-level widgets of the application by the address of their C++ object."""
    import shiboken6

    return {shiboken6.getCppPointer(w)[0]: w for w in QApplication.topLevelWidgets()}


class Studio(ProjectActions, CompassWorkspace, SextantWorkspace, SpectrumWorkspace, QMainWindow):
    def __init__(self, example=False, probe_machine=True):
        super().__init__()
        self.probe_machine = probe_machine  # False keeps 2 processes and 1000 MB (the tests)
        from azimuth.activities import Board

        self.activities = Board()  # the long work put away — one sign in the left panel (hub/job_indicator.py)
        self.setWindowTitle(tr('Азимут'))
        self.resize(1280, 850)
        self.setMinimumSize(1050, 730)
        # Compass starts empty; example=True — with the water of the examples (the tests use it)
        self.molecule = read_xyz(next(iter(EXAMPLES.values()))) if example else Molecule(tr('Новая молекула'), (), ())
        self.output = None
        self.cube_dialog = None
        self.undo_history = []
        self.redo_history = []
        self._loading = False
        self.dirty = False
        self.project_path = None
        from azimuth.settings import open_settings

        self.preferences = open_settings()  # an INI file in the tests
        from azimuth import defaults

        defaults.load(self.preferences)  # bonds, steps, pictures, spectra of «Настройки» — before the panels
        from azimuth import file_dialogs

        # «Открыть…» starts in the folder of the last file opened; first — the folder of the projects
        file_dialogs.install(self.preferences, root=lambda: self.projects_root())
        use_fusion(QApplication.instance())
        before = _windows()
        self.build()
        self.adopt_loose_controls(before)
        self.setAcceptDrops(True)  # files dropped on the window
        from azimuth.drop_overlay import DropOverlay

        self.drop_overlay = DropOverlay(self)  # the grey veil with what can be dropped here
        # the first start follows the system theme; afterwards the theme the user chose is kept — unless
        # «Как в системе» was chosen (THEME_FOLLOWS_SYSTEM): then the system's, and its changes while the program runs
        saved = self.preferences.value('theme', '')
        follow = self.follows_system_theme()
        self.theme.setCurrentIndex(
            1 if (system_prefers_dark() if follow or saved not in ('light', 'dark') else saved == 'dark') else 0
        )
        self.apply_theme()
        try:
            QApplication.instance().styleHints().colorSchemeChanged.connect(lambda *_: self.system_theme_changed())
        except (AttributeError, RuntimeError):  # Qt before 6.5: no signal — the theme is read at the start only
            pass
        if hasattr(self, 'scheme_tool'):
            self.scheme_tool.apply_start_scheme()  # «Настройки → Вид модели → Схема при запуске»
        self.load_molecule(self.molecule, record=False)
        self.dirty = False
        # The status bar shows only short messages (saved, snapshot, ...) and is hidden between them.
        bar = self.statusBar()
        bar.hide()

        def told(text):
            # a message of the status
            # line goes to the pill of the page shown (Compass: over its model), the line itself stays hidden
            if text:
                bar.clearMessage()
                self.notify(text, 9000)

        bar.messageChanged.connect(told)
        from azimuth.recovery_ui import Recovery

        self.recovery = Recovery(self)
        from azimuth.ui import DialogCentre

        DialogCentre.install()  # the dialogs in the middle of the window
        from modules.sextant.unfinished import UnfinishedCheck

        # a queue or a server calculation left unfinished — asked by the launcher after the window is shown
        # (hub/launch.py), never by a window made in the tests
        self.unfinished = UnfinishedCheck(self, start=False)

    def adopt_loose_controls(self, before):
        """The controls that build() made but put in no layout (the state of older panels kept for the menus
        and the toolbar: «Связать», the display mode, «Сохранить входной файл .inp»…, 20 of them) were windows of their
        own, hidden — nobody deleted them with the window, and a show() of one would open it as an empty window. They
        become children of a hidden holder; a control placed in a layout later moves there as before. Popups, tool
        windows and dialogs (their own window type, or a title) stay as they are."""
        import shiboken6
        from PySide6.QtWidgets import QAbstractButton, QAbstractSpinBox, QLabel

        holder = QWidget(self)
        holder.setObjectName('looseControls')
        holder.hide()
        for key, widget in _windows().items():
            if key in before or widget is self or not shiboken6.createdByPython(widget):
                continue
            # a parentless widget is a plain window (Qt.Window); only controls, no window of the program
            if (widget.windowType() == Qt.WindowType.Window and not widget.windowTitle()
                    and isinstance(widget, (QAbstractButton, QComboBox, QAbstractSpinBox, QLabel, QFrame))):
                widget.setParent(holder)
        self.loose_controls = holder

    def build(self):
        root = QWidget()
        root.setObjectName('workspace')
        self.setCentralWidget(root)
        base = QHBoxLayout(root)
        base.setContentsMargins(0, 0, 0, 0)
        base.setSpacing(0)
        self.sidebar = sidebar = QFrame()
        sidebar.hide()
        sidebar.setObjectName('sidebar')
        sidebar.setFixedWidth(180)
        left = QVBoxLayout(sidebar)
        left.setContentsMargins(14, 18, 14, 18)
        left.setSpacing(12)
        left.addWidget(label(tr('Азимут'), 'brand'))
        left.addWidget(label(tr('Квантовая химия\nтеория и расчёт')))
        self.setWindowIcon(app_icon())
        left.addWidget(label(tr('Квантовая химия\nОт модели к расчёту')))
        left.addSpacing(4)
        self.navigation = []
        for i, title in enumerate([tr('01   Структура'), tr('02   Расчёт'), tr('03   Результаты')]):
            nav = button(title, lambda checked=False, index=i: self.navigate(index))
            nav.setObjectName('nav')
            nav.setCheckable(True)
            self.navigation.append(nav)
            left.addWidget(nav)
        left.addStretch()
        self.theme = QComboBox()
        self.theme.addItems([tr('Светлая тема'), tr('Тёмная тема')])
        self.theme.setAccessibleName(tr('Тема оформления'))
        self.theme.currentIndexChanged.connect(self.apply_theme)
        left.addWidget(self.theme)
        left.addWidget(label(tr('Выберите модель.\nСформулируйте ожидание.\nПроверьте результат.')))
        left.addSpacing(10)

        from azimuth import __version__  # the version of the program, not one written here (it said 0.91.45)

        left.addWidget(label(tr(f'Самостоятельный проект\nВерсия {__version__} · ORCA, Gaussian, Psi4, xtb, CREST')))
        base.addWidget(sidebar)
        body = QVBoxLayout()
        body.setContentsMargins(14, 12, 14, 12)
        body.setSpacing(10)
        base.addLayout(body, 1)
        self.workspace_controls = QWidget()
        top = QHBoxLayout(self.workspace_controls)
        top.setContentsMargins(0, 0, 0, 0)
        self.panel_toggle = iconify(
            button('', lambda: self.sidebar.setVisible(self.panel_toggle.isChecked())),
            'menu',
            tr('Показать / скрыть левую панель'),
        )
        self.panel_toggle.setCheckable(True)
        top.addWidget(self.panel_toggle)
        top.addStretch(1)
        self.theme_toggle = button(
            tr('Тёмная тема'), lambda: self.theme.setCurrentIndex(0 if self.theme.currentIndex() else 1)
        )
        iconify(self.theme_toggle, 'moon', tr('Тёмная тема'))
        top.addWidget(self.theme_toggle)

        body.addWidget(self.workspace_controls)
        self.stack = QStackedWidget()
        body.addWidget(self.stack, 1)
        self.structure_page()
        self.calculation_page()
        self.results_page()
        self.install_project_navigation(body)
        self.build_menus()
        if hasattr(self, 'custom_bar'):  # the user's own buttons, now that the menus are there
            self.custom_bar.start()
        self.update_history_buttons()
        self.model_selection_changed([])
        self.navigate(0)

    def save_error_report(self):
        """«Файл → Отчёт об ошибке…» (azimuth/crash_report.py)."""
        from azimuth import crash_report

        return crash_report.save_report_dialog(self, self.preferences)

    def apply_default(self, key):
        """A value of «Настройки» (azimuth/defaults.py) changed — what is open follows it at once."""
        from dataclasses import replace

        from azimuth import defaults

        value = defaults.get(key)
        viewer = getattr(self, 'viewer', None)
        if key == 'bond_factor' and viewer is not None and viewer.molecule is not None and viewer.molecule.bonds is None:
            viewer.set_molecule(replace(viewer.molecule))  # the bonds by distance found again (a structure without its own)
        elif key == 'common_orientation' and getattr(self, 'browsing', False) and self.drawer.page() == 'steps':
            self.trajectory_tool.show_trajectory_step(self.drawer.current)
        elif key == 'picture_transparent' and viewer is not None:
            viewer.transparent = value
        elif key == 'ir_style' and hasattr(self, 'vibrations'):
            self.vibrations.ir_style.setCurrentIndex(1 if value == 'gauss' else 0)
        elif key == 'ir_width' and hasattr(self, 'vibrations'):
            self.vibrations.ir_width.setValue(value)
        elif key == 'uv_fwhm' and hasattr(self, 'uv_panel'):
            self.uv_panel.fwhm.setValue(value)
        elif key == 'coordinate_unit' and hasattr(self, 'coord_units') and self.coord_units.isEnabled():
            self.coord_units.setCurrentIndex(int(value == 'bohr'))
        elif key == 'energy_unit' and hasattr(self, 'drawer'):
            self.drawer.relabel_energies()  # the reaction diagram: its own choice, this is its default
        elif key == 'quick_atoms' and viewer is not None:
            viewer._model_image = None
            viewer.update()
        return value

    def show_settings(self, focus=None):
        """«Файл → Настройки…» — one window for the preferences of the whole program (azimuth/settings_dialog);
        focus: the section to show ('tables' from «Таблицы CSV…»)."""
        from azimuth.settings_dialog import SettingsDialog

        old = getattr(self, 'settings_dialog', None)
        if old is not None:
            try:
                old.close()
            except RuntimeError:
                pass
        top = self.window()
        hub = top if top is not self and hasattr(top, 'set_language') else None
        self.settings_dialog = dialog = SettingsDialog(self, hub, focus)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        if focus:
            dialog.show_section(focus)
        return dialog

    build_menus = _menus.build_menus
    install_combo_theme = _theme.install_combo_theme
    style_new_combos = _theme.style_new_combos
    style_combo = _theme.style_combo

    theme_extra = staticmethod(theme_extra)  # azimuth/app_style.py

    THEME_FOLLOWS_SYSTEM = 'theme_follows_system'  # «Настройки → Тема → Как в системе»

    follows_system_theme = _theme.follows_system_theme
    set_theme_follows_system = _theme.set_theme_follows_system
    system_theme_changed = _theme.system_theme_changed
    apply_theme = _theme.apply_theme
    _apply_theme = _theme._apply_theme

    def set_language(self, code):
        """Language of Compass, Sextant and Spectrum (ru, en, zh): static texts are re-translated,
        texts made later come from tr() in the new language (azimuth/i18n.py, locale/*.json)."""
        # a change of the language changes nothing of the work: the lists translated anew (the method, the
        # solvent…) told «the settings changed», and the project asked to be saved (the owner, 2026-11-28: «я ничего
        # не меняю в проекте, но он предлагает его сохранить после просто переключений языка»)
        was_dirty = getattr(self, 'dirty', False)
        documents = [(d, d.dirty) for d in self.all_documents()] if hasattr(self, 'all_documents') else []
        try:
            self._set_language(code)
        finally:
            self.dirty = was_dirty
            for document, dirty in documents:
                document.dirty = dirty

    def _set_language(self, code):
        from azimuth import i18n, qt_language

        i18n.set_language(code)
        qt_language.install(code)  # Qt's standard buttons (Yes, No, Save, Cancel...) in this language too
        i18n.retranslate(self)
        for dialog in (getattr(self, 'cube_dialog', None), getattr(self, 'periodic_dialog', None)):
            if dialog is not None:
                i18n.retranslate(dialog)
        try:
            self.input_tool.refresh_input()
        except Exception:
            pass
        if self.geometry_error.isHidden():
            self.molecule_info.setText(self.molecule_summary(self.molecule))  # names follow the language
        if self.geometry_error.isHidden():
            self.symmetry_tool.update_symmetry()
        self.crystal_tool.update_panel(getattr(self, 'compass_mode', 'molecule'))  # the arrow's text by the mode
        self.update_choice_label()
        if getattr(self, 'browsing', False) and hasattr(self, 'trajectory_tool'):
            # the line of the step and the shift from
            # the start are made again — a label of two texts was not re-translated as a whole
            drawer = getattr(self, 'drawer', None)
            if drawer is not None and hasattr(drawer, 'show_step'):
                drawer.show_step(drawer.current)
            self.trajectory_tool.show_trajectory_step(getattr(drawer, 'current', -1))
        self.sync_view_tabs()  # «Молекула | Координаты» shown in the row of the tabs

    def navigate(self, index):
        if index == 2 and self.crystal_project_shown():
            # Spectrum of molecules left the project of a crystal for a «Новый проект»; Spectrum of a crystal — the
            # results of the runs of its project
            from azimuth import crystal_projects

            if getattr(self, 'browsing', False):
                self.trajectory_tool.set_trajectory_open(False)
            path = self.research_path()
            title = crystal_projects.title(path) if crystal_projects.is_crystal(path) else ''
            self.stack.setCurrentIndex(2)
            self.show_crystal_results(path, title)
            self.style_new_combos(self.stack.currentWidget())
            for i, nav in enumerate(self.navigation):
                nav.setChecked(i == 2)
            return True
        if index == 2 and hasattr(self, 'results_stack'):
            self.results_stack.setCurrentIndex(0)  # the results of a molecule
        if index != 0 and getattr(self, 'browsing', False):
            self.trajectory_tool.set_trajectory_open(False)  # the steps belong to Compass
        # 0.133.0; Sextant of a crystal tab is the calculation of the crystal (crystal_mode.py) — the crystal
        # tabs stay; Sextant of a molecule tab and Spectrum work on the molecule tabs
        follow = index == 1 and hasattr(self, 'calc_stack')
        crystal_tab = (self.document() if follow and getattr(self, 'compass_mode', 'molecule') == 'crystal'
                       and getattr(self, 'crystal', None) is not None else None)
        if index in (1, 2) and crystal_tab is None and hasattr(self, 'ensure_molecule_tabs'):
            self.ensure_molecule_tabs()  # Sextant and Spectrum work on the molecule tabs
        self.stack.setCurrentIndex(index)
        if follow:
            self.crystal_mode_tool.follow(crystal_tab)
            self.crystal_mode_tool.sync_programs()  # a project of no kind yet — the programs of both kinds
        self.style_new_combos(self.stack.currentWidget())  # the combo boxes made since the theme was set
        for i, nav in enumerate(self.navigation):
            nav.setChecked(i == index)
        if hasattr(self, 'preview'):
            self.input_tool.refresh_input()
        self.project_section_changed(index)

    def crystal_project_shown(self):
        """The project of the tab shown is one of a crystal (or a new one waiting for its CIF in «Кристалл»)."""
        if getattr(self, 'compass_mode', 'molecule') != 'crystal' or not hasattr(self, 'research_path'):
            return False
        from azimuth import crystal_projects

        path = self.research_path()
        return bool(path) and (crystal_projects.is_crystal(path) or self.project_kind(path) == '')

    def confirm_replace(self):
        if not self.dirty:
            return True
        return (
            quill.question(
                self,
                tr('Заменить структуру?'),
                tr('Есть несохранённые изменения. Заменить текущий проект?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
                'save',
            )
            == QMessageBox.StandardButton.Yes
        )

    def error(self, exc):
        """With Quill (azimuth.quill.warning): the tangled ball of «Не удалось выполнить действие», the tin-can
        telephone when the server does not answer (ssh.SshError of kind 'connection' or 'timeout'), or the picture the
        raiser put on the exception as exc.quill ('nothing-found', 'file-unreadable')."""
        for item in self.findChildren(HoldButton):
            item.finish(False)
        picture = getattr(exc, 'quill', None)
        if picture is None:
            picture = 'offline' if getattr(exc, 'kind', None) in ('connection', 'timeout') else 'error'
        quill.warning(self, tr('Не удалось выполнить действие'), str(exc), picture)

    save_text = _files.save_text
    save_project = _files.save_project
    save_project_as = _files.save_project_as
    remember_recent = _files.remember_recent
    recent = _files.recent
    recent_list = _files.recent_list
    open_molecule_path = _files.open_molecule_path
    open_project = _files.open_project
    open_project_path = _files.open_project_path

    @staticmethod
    def _carried_molecules(event):
        """Molecules of the list of a project carried (MoleculeTable.carrying) — a drop anywhere in the
        window puts them back (no picture sliding back), they fly from there to the list."""
        return bool(getattr(event.source(), 'carrying', False))

    def dragEnterEvent(self, event):  # a file dropped on the window opens
        if self._carried_molecules(event):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        if event.mimeData().hasUrls() and any(u.isLocalFile() for u in event.mimeData().urls()):
            event.acceptProposedAction()
            section = self.stack.currentIndex() if hasattr(self, 'stack') else None
            self.drop_overlay.show_for(section if section in (0, 1, 2) else None)

    def dragMoveEvent(self, event):
        if self._carried_molecules(event):
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        self.drop_overlay.hide()

    def dropEvent(self, event):
        """The drop is answered at once and the files are opened on the next turn of the event loop. Opened
        inside the drop (Quill's «Сделать объёмными?», RDKit), the drag of Finder was not over for macOS all that time —
        and the gestures of the system waited for it."""
        from PySide6.QtCore import QTimer

        self.drop_overlay.hide()
        if self._carried_molecules(event):  # put back: the list lays them out again (MoleculeTable.lay_back)
            event.setDropAction(Qt.DropAction.MoveAction)
            event.accept()
            return
        paths = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        if not paths:
            return
        event.acceptProposedAction()
        QTimer.singleShot(0, lambda: self.view_tool.drop_paths(paths))

    def save_all_before_exit(self):
        """«Сохранить» before the exit saves every changed molecule tab into its project (until then only the tab shown
        — the others were lost). A tab of «Кристалл» is not a project: its cell would be lost in a .qcc, so it is not
        saved here — changed ones are named and the exit asks once more. A cancelled save — False, the tab and the
        subsection shown before come back."""
        self.store_document()
        kind = getattr(self, 'document_kind', 'molecule')
        shown = self.document()
        docs = [d for d in self.all_documents() if d.dirty and d.molecule is not None and d.molecule.atoms]

        def back():
            if getattr(self, 'document_kind', 'molecule') != kind:
                self.crystal_tool.set_compass_mode(kind)
            if shown in self.documents:
                self.switch_document(self.documents.index(shown))

        for doc in (d for d in docs if d.kind == 'molecule'):
            if getattr(self, 'document_kind', 'molecule') != 'molecule':
                self.crystal_tool.set_compass_mode('molecule')
            self.switch_document(self.documents.index(doc))
            if not self.save_project():
                back()
                return False
            self.store_document()
        crystals = [d for d in docs if d.kind == 'crystal']
        if crystals:
            back()
            answer = quill.question(
                self, tr('Несохранённый кристалл'),
                tr(f'Вкладки «Кристалл» с изменениями: {len(crystals)}. Ячейку кристалла проект не хранит — сохраните её '
                   'кнопкой «Сохранить CIF…» на панели кристалла. Выйти без них?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel, 'save')
            if answer != QMessageBox.StandardButton.Yes:
                return False
        return True

    def closeEvent(self, event):
        # a calculation of each place (this computer, a server) may go on
        jobs = self.running_jobs() if hasattr(self, 'running_jobs') else []
        local_jobs = [j for j in jobs if not getattr(j, 'remote_dir', None)]
        remote_job = next((j.remote_dir for j in jobs if getattr(j, 'remote_dir', None)), None)  # on a server
        left = self.batch_tool.server_queue_left() if hasattr(self, 'batch_tool') and not local_jobs else None
        if left is not None:
            # a queue on a server — what is not sent yet goes there now and runs without the program
            waiting = sum(1 for item in left.items if item.state == 'waiting')
            answer = quill.question(
                self, tr('Очередь на сервере'),
                tr(f'В очереди на сервере ещё не отправлены расчёты: {waiting}. Отправить их сейчас? Они пойдут на '
                   'сервере один за другим и без программы; при следующем запуске Секстант подхватит очередь и покажет '
                   'её ход. «Выйти без них» — они подождут следующего запуска.'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes, 'stop-running',
                labels={QMessageBox.StandardButton.Yes: tr('Отправить и выйти'),
                        QMessageBox.StandardButton.No: tr('Выйти без них')})
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Yes:
                with self.at_place('server'):
                    self.batch_tool.send_rest_before_exit(left)
        elif remote_job and not local_jobs:
            # it goes on on the server: closing does not stop it; its folder there is named for the user
            answer = quill.question(
                self,
                tr('Идёт расчёт на сервере'),
                tr(f'Расчёт продолжится на сервере и без программы; результат останется там, в папке {remote_job}. '
                   'Выйти?') + (' ' + tr('При следующем открытии проекта программа сама подключится к серверу и покажет, '
                                        'как идёт расчёт.') if any(getattr(j, '_research_link', None) for j in jobs) else ''),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
                'stop-running',
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        elif local_jobs:  # a calculation of Sextant on this computer
            answer = quill.question(  # Quill instead of the system icon
                self,
                tr('Идёт расчёт'),
                tr('Расчёт ещё не закончен. Остановить его и выйти?'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
                'stop-running',
            )
            if answer != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            for job in local_jobs:
                job.stop()
        # T03 a molecule drawn in no project is kept as a draft whatever
        # the answer below — Save (to a file) takes it out of this list
        loose = self.loose_drawn_documents() if hasattr(self, 'loose_drawn_documents') else []
        if self.any_dirty():  # any tab of Compass
            answer = quill.question(
                self,
                tr('Несохранённый проект'),
                tr('Сохранить изменения перед выходом?') + (
                    ' ' + tr('Нарисованная молекула без проекта останется черновиком в папке «Проекты».') if loose else ''),
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Save,
                'save',
            )
            if answer == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if answer == QMessageBox.StandardButton.Save and not self.save_all_before_exit():
                event.ignore()
                return
        if loose:
            try:
                self.keep_drawn_as_drafts(loose)
            except Exception as exc:  # noqa: BLE001 — the exit is never stopped by a draft; kept in errors.log
                from azimuth.runtime.provenance import note

                note('project', f'a drawn molecule was not kept as a draft at the exit ({exc})')
        if hasattr(self, 'discard_untouched_projects'):
            try:  # the projects of files opened only to look at leave no folder in «Проекты»
                self.discard_untouched_projects()
            except Exception as exc:  # noqa: BLE001 — the exit is never stopped by it; kept in errors.log
                from azimuth.runtime.provenance import note

                note('project', f'a project only looked at was not removed at the exit ({exc})')
        self.vibrations.set_playing(False)
        if self.cube_dialog is not None:
            self.cube_dialog.close()
        self.recovery.finish()
        event.accept()

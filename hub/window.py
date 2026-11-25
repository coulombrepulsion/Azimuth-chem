"""Azimuth hub window: own sidebar, sections in one content area, smooth switching.

§1 PURPOSE
    One window for the sections Compass, Sextant and Spectrum. Each section also runs alone (python -m
    modules.<id>); the hub only arranges them. The Atlas lives on the site — its item of the panel and its
    card on the home page open it in the browser (azimuth/site.py); it is no part of the window any more.
§2 ALGORITHM
    Left: the hub sidebar (hub/registry.py order, SVG icons, theme switch; a
    rail of icons with tooltips, the drawer is off: PANEL_EXPANDABLE). The
    application icon opens the home page HOME (HomePage: Quill's greeting, the
    program, the section blocks). Right: a stacked area with the home page and the shared Studio window, whose pages
    0..2 are Compass, Sextant and Spectrum (one molecule and undo history for all three).
    Switching grabs the current picture, changes the section and fades the
    picture out over the new one (FADE_MS).
§3 SCENARIOS
    Theory in the Atlas (the site) -> build in Compass -> prepare in Sextant -> results in Spectrum; Ctrl+1 opens the
    Atlas on the site, Ctrl+2..5 switch sections; the program opens on the home page unless --module names one.
§4 CONTRACT
    HubWindow(initial: str | None, preferences=None): preferences a QSettings for hub_section (tests pass their own).
    Sections:
    hub/modules.json (docs/MODULES.md §4). show_section(id | HOME, animate=True) -> None; 'atlas' opens the Atlas
    of the site in the browser and the window stays where it is; unknown id -> ValueError. self.ready is True once
    the window is made (gui_launcher.py --check).
§5 PROCEDURES -- below.
§6 IMPLEMENTATION The hub theme is the Studio theme (QSettings 'theme'). Studio keeps its own menus; its standalone
    sidebar and header stay hidden. Parts of the window live next to it: texts.py, branding.py, about.py, header.py,
    home.py, chrome.py; their names are imported here.
§7 TESTS
    tests/hub/test_hub_registry.py (registry contract, no display), tests/hub/test_hub.py
    (offscreen window: sections, titles, Studio pages, theme, fade, shortcuts).
§8' ROBUSTNESS
    A fade in progress is finished before the next one starts. Closing
    asks Studio's save/discard/cancel question once.
"""


import sys

from PySide6.QtCore import QEasingCurve, QEvent, QPoint, QVariantAnimation, Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsOpacityEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from azimuth.app import Studio, app_icon
from azimuth.i18n import tr
from hub import registry
from azimuth.paths import ROOT  # noqa: F401  (hub.window.ROOT is used by tests)
from hub.texts import TEXT
from hub.menus import HubMenus  # split off
from hub.texts import HEADER_HEIGHT  # noqa: F401  (hub.window.HEADER_HEIGHT is used by tests)
from hub.branding import glyph_logo, wordmark_cuts, wordmark_pixmap, zh_wordmark_pixmap
from hub.about import AboutDialog
from hub.header import SectionHeader
from hub.home import HomePage
from hub.chrome import Ornament, Scrim
from hub import window_sidebar as _sidebar
from hub.window_sidebar import LANGUAGES, NARROW, WIDE  # noqa: F401 — also named from here
from hub import window_sections as _sections
from hub.window_sections import HOME

# the panel stays a rail of icons (names in tooltips); the drawer can be switched back on here
PANEL_EXPANDABLE = False


class HubWindow(HubMenus, QMainWindow):
    def __init__(self, initial=None, preferences=None):
        super().__init__()
        self.sections = {item['id']: item for item in registry.load()}
        if initial is not None and initial not in self.sections:
            raise ValueError(f'Unknown section {initial!r}')
        self.setWindowTitle('Азимут')
        self.resize(1440, 900)
        self.setMinimumSize(1050, 700)
        from azimuth.settings import open_settings

        self.preferences = preferences if preferences is not None else open_settings()
        self.ready = False  # True at the end of __init__ (gui_launcher.py --check)
        self.current = None
        language = self.preferences.value('hub_language', 'ru')
        self.language = language if language in LANGUAGES else 'ru'
        self._animation = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        # The sidebar floats over the page: a narrow rail keeps its place in the layout; a click on the
        # panel slides it open over the page, a click on the page slides it back.
        self.rail = QWidget()
        self.rail.setFixedWidth(NARROW)
        layout.addWidget(self.rail)
        self._composition_anchor(self.rail)  # no black flash when the VTK view of Compass is shown the first time
        # The panel is laid out once at full width inside a clipping frame (self.sidebar); the slide
        # only changes the frame's width, so the icons, names and wordmark never reflow or shake.
        self.sidebar = QWidget(root)
        self.sidebar.setObjectName('sidebarClip')
        self.panel = self._build_sidebar()
        self.panel.setParent(self.sidebar)
        self.panel.move(0, 0)
        # a 1 px edge on the right of the panel (in the dark theme it merged with the page)
        self.edge = QFrame(self.sidebar)
        self.edge.setObjectName('sidebarEdge')
        self._progress = 0.0
        self.slide = QVariantAnimation(self)
        self.slide.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.slide.valueChanged.connect(self._apply_progress)
        self.slide.finished.connect(self._slide_done)
        self.sidebar.show()
        self.sidebar.installEventFilter(self)  # a click on the empty panel opens it
        self.panel.installEventFilter(self)
        root.installEventFilter(self)  # keeps the panel as tall as the window

        self.content = QWidget()
        area = QVBoxLayout(self.content)
        area.setContentsMargins(0, 0, 0, 0)
        area.setSpacing(0)
        self.header = SectionHeader()
        self.header.hide()
        area.addWidget(self.header)
        self.stack = QStackedWidget()
        area.addWidget(self.stack)
        layout.addWidget(self.content, 1)

        # one theme switch and one language switch for all sections: the sidebar
        from azimuth import qt_language

        qt_language.install(self.language)  # Qt's standard buttons in the language of the program
        self.studio = Studio()
        self.studio.recovery.restored.connect(lambda: self.show_section('compass', animate=False))
        self.studio.unfinished.shown.connect(lambda section: self.show_section(section, animate=False))
        self.studio.setParent(self.stack, Qt.WindowType.Widget)
        self.studio.setMinimumSize(0, 0)
        self.studio.menuBar().setNativeMenuBar(False)
        self.studio.menuBar().hide()  # the menus live in the section header
        for each in self._studio_actions():
            if not each.shortcut().isEmpty():
                self.studio.addAction(each)
        self._header_menus = []
        self.studio.exit_action.triggered.disconnect()
        self.studio.exit_action.triggered.connect(self.close)
        for part in (
            self.studio.sidebar,
            self.studio.panel_toggle,
            self.studio.theme_toggle,
            self.studio.workspace_controls,
        ):
            part.hide()
        self.studio.stack.currentChanged.connect(self._studio_page_changed)
        self.studio.theme.currentIndexChanged.connect(self._theme_changed)
        self.compass = self.studio  # name used by gui_launcher.py and older callers
        self.studio.compass_mode_listener = self._compass_mode_changed  # a CIF opens «Компас · Кристалл»
        self.studio.job_listener = self.job_indicator.set_state  # the hourglass of a calculation
        self.job_indicator.board()  # the sign follows all the long work of the Studio (azimuth/activities.py)
        if hasattr(self.studio, 'job_windows'):  # shown only while the window of the calculation is hidden
            for window in self.studio.job_windows():  # this computer and the server
                window.on_parked = self.job_indicator.set_parked
        if self.language != 'ru':
            self.studio.set_language(self.language)
        self.home = HomePage(self.sections, self.show_section, self)
        self.stack.addWidget(self.home)
        self.stack.addWidget(self.studio)
        # the status line of the hub
        # is never shown; a message written into it goes to the pill of the section (Studio.notify)
        self.statusBar().hide()
        self.statusBar().messageChanged.connect(self._told)
        self.setWindowIcon(self.studio.windowIcon())
        self.logo.setIcon(glyph_logo(self.dark))  # the glyph without the tile; dark on the light panel
        self.logo.setProperty('variant', 'glyph')

        # A still of the previous section fades out above the new one.
        self.fader = QLabel(self.content)
        self.fader.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.fader.setScaledContents(True)
        self.fader_effect = QGraphicsOpacityEffect(self.fader)
        self.fader.setGraphicsEffect(self.fader_effect)
        self.fader.hide()
        self.ornament = Ornament(self.content)  # the azimuth dial top right; the section's picture lower left
        self.content.installEventFilter(self)
        self.history, self.history_pos, self._history_nav = [], -1, False

        self.shortcuts = []
        for key, step in ((QKeySequence.StandardKey.Back, -1), (QKeySequence.StandardKey.Forward, 1)):
            shortcut = QShortcut(QKeySequence(key), self)
            shortcut.activated.connect(lambda step=step: self.go_history(step))
            self.history_shortcuts = getattr(self, 'history_shortcuts', []) + [shortcut]
        for number, ident in enumerate(self.sections, start=1):
            shortcut = QShortcut(QKeySequence(f'Ctrl+{number}'), self)
            shortcut.activated.connect(lambda ident=ident: self.show_section(ident))
            self.shortcuts.append(shortcut)
        # ⌘? (Ctrl+? elsewhere) — «Справка» with its field of the search open, as the Help menu of macOS
        from hub import menu_search

        self.help_search_shortcut = QShortcut(QKeySequence('Ctrl+?'), self)
        self.help_search_shortcut.activated.connect(lambda: menu_search.open_help(self.header))

        self._theme_changed()
        # While the panel is open a light veil lies over the page; a click on it closes the panel.
        self.scrim = Scrim(root, lambda: self.set_collapsed(True))
        self.scrim.hide()
        self.collapsed = True
        self.set_collapsed(True, animate=False)
        # the program always opens on the home page (its «continue» cards lead to the sections); the
        # Atlas is no section of the window — asked for at the start, it is the home page
        self.show_section(initial if initial not in (None, 'atlas') else HOME, animate=False)
        self.ready = True

    @staticmethod
    def _composition_anchor(parent):
        """Qt composes a window through the graphics card only after the first widget that needs it (the web
        view of the Atlas then, the VTK view of Compass) is shown, and the switch repaints the whole window black for a
        moment. A 1 × 1 transparent Qt Quick widget, shown from the start under the panel, makes the window composed
        that way from its first frame (Qt Quick follows the graphics interface the program chose, opengl_setup.py)."""
        from PySide6.QtGui import QGuiApplication

        if QGuiApplication.platformName() in ('offscreen', 'minimal'):
            return None
        try:
            from PySide6.QtQuickWidgets import QQuickWidget
        except ImportError:
            return None
        anchor = QQuickWidget(parent)
        anchor.setObjectName('compositionAnchor')
        anchor.setFixedSize(1, 1)
        anchor.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        anchor.setAttribute(Qt.WidgetAttribute.WA_AlwaysStackOnTop)
        anchor.setClearColor(Qt.GlobalColor.transparent)
        anchor.move(0, 0)
        anchor.show()
        return anchor

    _build_sidebar = _sidebar._build_sidebar
    set_collapsed = _sidebar.set_collapsed
    _apply_progress = _sidebar._apply_progress
    _slide_done = _sidebar._slide_done
    _place_sidebar = _sidebar._place_sidebar

    # -- the Atlas of the site, its links -------------------------------------------------------
    def open_atlas_molecule(self, name):
        """«Открыть в Компасе» of an Atlas topic — the molecule from the library in a tab of Compass
        (the current one when it is empty, else a new one)."""
        from modules.compass.chemistry import library

        studio = self.studio
        try:
            molecule = library.molecule(name)
        except (KeyError, ValueError) as exc:
            studio.error(exc)
            return None
        title = tr(name.split(' · ')[0])
        if hasattr(studio, 'tab_is_empty') and not studio.tab_is_empty():
            studio.new_document(title)
        elif hasattr(studio, 'document'):
            d = studio.document()
            d.title, d.named = title, True
        studio.load_molecule(molecule)
        self.show_section('compass')
        return molecule

    def open_link(self, address):
        """An address azimuth:// from the system (azimuth/links.py): its molecule in Compass, the window to
        the front. Anything else is written to the log and nothing is done."""
        from azimuth import links

        link = links.parse(address)
        if link is None:
            print('Azimuth: a link not understood, nothing done: '
                  + str(address)[:200].encode('ascii', 'backslashreplace').decode('ascii'), file=sys.stderr)
            return None
        molecule = self.open_atlas_molecule(link.name)
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        return molecule

    def open_file(self, path):
        """        a file given by the system — a double click or «Открыть с помощью» in Finder (QEvent.FileOpen,
        azimuth/link_channel.py), a path on the command line — opened as by «Файл → Открыть…»: a project, a structure
        or a crystal in Compass, a result of a calculation in Spectrum; the window to the front. Returns the path or
        None (no such file)."""
        from pathlib import Path

        file = Path(str(path))
        if not file.is_file():
            print('Azimuth: no such file, nothing opened: '
                  + str(path)[:200].encode('ascii', 'backslashreplace').decode('ascii'), file=sys.stderr)
            return None
        studio = self.studio
        kind = studio.opening_tool.file_kind(str(file)) if hasattr(studio, 'opening_tool') else ''
        self.show_section('spectrum' if kind in ('output', 'gaussian_log') else 'compass', animate=False)
        studio.opening_tool.open_path(str(file))
        if self.isMinimized():
            self.showNormal()
        self.show()
        self.raise_()
        self.activateWindow()
        return str(file)

    def open_site_atlas(self, topic=None):
        """The Atlas of the site in the browser, in the language of the program (azimuth/site.py)."""
        from azimuth import site

        return site.open_atlas(self.language, topic, 'dark' if self.dark else 'light')  # and its theme

    def continue_with(self, kind, path=None):
        """'molecule': the last XYZ or project in Compass; 'output': the last ORCA result in Spectrum (the
        last topic of the Atlas is no more — the site remembers it itself, «Продолжить» of its overview);
        path — one of the last ones chosen by the arrow of the card."""
        if not path and kind in ('molecule', 'crystal') and hasattr(self.studio, 'recent_list'):
            listed = self.studio.recent_list(kind)  # as the card shows it (no drafts only looked at)
            path = listed[0] if listed else None
        path = path or self.studio.recent(kind)
        if not path:
            return
        self.show_section('spectrum' if kind == 'output' else 'compass', animate=False)
        # 'crystal' — the project of the crystal, opened as from «Недавние файлы»
        (self.studio.open_output_path if kind == 'output' else self.studio.open_molecule_path)(path)

    def _logo_clicked(self):
        """The application icon opens the home page; with the drawer enabled it toggles the panel."""
        if PANEL_EXPANDABLE:
            self.set_collapsed(not self.collapsed)
        else:
            self.show_section(HOME)

    def _nav_clicked(self, ident):
        self.show_section(ident)
        if not self.collapsed:  # a section chosen in the open panel: the panel slides back
            self.set_collapsed(True)

    def _mark_buttons(self, ident):
        for key, button in self.buttons.items():
            button.setChecked(key == ident)

    def _place_job_indicator(self):
        """The hourglass over the bottom of the background, just above the row of languages."""
        indicator, row = getattr(self, 'job_indicator', None), getattr(self, 'language_row', None)
        if indicator is None or row is None or row.parentWidget() is None:
            return
        bar = indicator.parentWidget()
        height = max(indicator.sizeHint().height(), 34)
        left = row.geometry().left()
        width = bar.width() - 2 * left if bar.width() > 2 * left else row.width()
        top = row.geometry().top()
        indicator.setGeometry(left, top - self._indicator_gap - height, width, height)
        indicator.raise_()

    def eventFilter(self, watched, event):
        # Only a few objects are watched (the panel, the central widget, the languages, the hourglass): no
        # application-wide filter.
        kind = event.type()
        if watched in (getattr(self, 'language_row', None), getattr(self, 'job_indicator', None)) and kind in (
            QEvent.Type.Move, QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.Hide,
        ):
            if not (watched is self.job_indicator and kind != QEvent.Type.Show):
                self._place_job_indicator()
            return False
        if kind == QEvent.Type.Resize and watched is getattr(self, 'content', None) and hasattr(self, 'ornament'):
            self.ornament.setGeometry(self.content.rect())
            self.ornament.raise_()
        if kind == QEvent.Type.Resize and watched is self.centralWidget():
            self._place_sidebar()
        elif (
            kind == QEvent.Type.MouseButtonPress
            and watched in (self.sidebar, self.panel)
            and self.collapsed
            and PANEL_EXPANDABLE
        ):
            self.set_collapsed(False)
            return True
        return False

    def show_about(self):
        """About window (the Atlas no longer gives its texts — it is on the site)."""
        self.about_dialog = AboutDialog(self, self.language, self.dark)
        self.about_dialog.open()

    # -- language ----------------------------------------------------------------------------
    def name(self, ident):
        if ident == HOME:
            return TEXT[self.language]['home']
        item = self.sections[ident]
        return item['title'] if self.language == 'ru' else item[self.language]

    def set_language(self, code):
        """Language of the sidebar and the Studio sections (ru, en, zh); the Atlas of the site opens in it."""
        if code not in LANGUAGES:
            raise ValueError(f'Unknown language {code!r}')
        self.language = code
        self.preferences.setValue('hub_language', code)
        self.studio.set_language(code)  # Compass, Sextant, Spectrum
        self._relabel()

    def _language_clicked(self, code):
        if self.collapsed and code == self.language:  # one button in the narrow panel: it cycles
            code = LANGUAGES[(LANGUAGES.index(code) + 1) % len(LANGUAGES)]
        self.set_language(code)

    def _relabel(self):
        text = TEXT[self.language]
        if self.language == 'zh':
            self.brand.setPixmap(
                *zh_wordmark_pixmap(
                    19, self.devicePixelRatioF(), '#ffffff', '#6ea2f0', getattr(self, 'family', ''), with_cuts=True
                )
            )
        else:
            self.brand.setPixmap(
                wordmark_pixmap(self.language, 17, self.devicePixelRatioF()), wordmark_cuts(self.language)
            )
        self.brand.setAccessibleName(text['brand'])
        self.logo.setAccessibleName(text['brand'])
        self.logo.setToolTip(
            text['home'] if not PANEL_EXPANDABLE else (text['expand'] if self.collapsed else text['collapse'])
        )
        for number, (ident, button) in enumerate(self.buttons.items(), start=1):
            button.setText('' if self.collapsed else self.name(ident))
            where = f" · {text['on_site']}" if ident == 'atlas' else ''  # it opens the site
            button.setToolTip(f'{self.name(ident)}{where} · Ctrl+{number}')
            button.setAccessibleName(self.name(ident))
        for code, button in self.language_buttons.items():
            button.setChecked(code == self.language)
            button.setVisible(not self.collapsed or code == self.language)
            button.setToolTip(text['language'])
        self.about_button.setText('' if self.collapsed else text['about'])
        self.settings_button.setText('' if self.collapsed else text['settings'])
        self.settings_button.setToolTip(text['settings'])
        self.settings_button.setAccessibleName(text['settings'])
        if hasattr(self, 'job_indicator'):
            self.job_indicator.set_collapsed(self.collapsed)
        self.about_button.setToolTip(text['about'])
        self.back_button.setToolTip(text['back'])
        self.forward_button.setToolTip(text['forward'])
        self._label_theme_button()
        if self.current is not None:
            self.setWindowTitle(TEXT[self.language]['brand'] + ' · ' + self.name(self.current))
        self._update_header()

    show_section = _sections.show_section
    _switch = _sections._switch
    _switch_now = _sections._switch_now
    _job_follow = _sections._job_follow
    _remember = _sections._remember
    _history_buttons = _sections._history_buttons
    go_history = _sections.go_history
    _told = _sections._told
    _studio_page_changed = _sections._studio_page_changed
    _compass_mode_changed = _sections._compass_mode_changed
    _transition = _sections._transition
    _transition_done = _sections._transition_done

    # -- theme -------------------------------------------------------------------------------
    @property
    def dark(self):
        return self.studio.theme.currentIndex() == 1

    def toggle_theme(self):
        """To the dark theme the darkness spreads from the theme button over the window, back to the light one
        it gathers into the button (hub/theme_wipe.py); the slow restyling happens under a still picture."""
        if hasattr(self.studio, 'set_theme_follows_system'):  # a theme chosen by hand — no longer the system's
            self.studio.set_theme_follows_system(False)
        from hub.theme_wipe import ThemeWipe, wipe_enabled

        target = 0 if self.dark else 1
        old = getattr(self, '_theme_wipe', None)
        if old is not None:
            try:
                old.animation.stop()
                old.deleteLater()
            except RuntimeError:  # already gone
                pass
            self._theme_wipe = None
        if not (self.isVisible() and wipe_enabled()):
            self.studio.theme.setCurrentIndex(target)
            return None
        still = self.grab()
        # the icon of the button, not the middle of it: the icon stands left (padding 12 px), the button is wide when
        # the panel is open
        button = self.theme_button
        icon_x = min(button.rect().center().x(), 12 + button.iconSize().width() // 2)
        centre = button.mapTo(self, QPoint(icon_x, button.rect().center().y()))
        wipe = ThemeWipe(self, still, centre, spreading=target == 1)
        wipe.show()
        wipe.raise_()
        wipe.repaint()  # the old picture is on screen before the restyling starts
        self.studio.theme.setCurrentIndex(target)
        wipe.raise_()
        self._theme_wipe = wipe
        wipe.start(lambda: setattr(self, '_theme_wipe', None))
        return wipe

    def _theme_changed(self, *args):
        # Studio.apply_theme has already styled the application, including this sidebar.
        # the Dock and window icon follows the theme of the program, like the side panel
        # (it followed the appearance of the system); the tiles have the panel colours
        self._system_icon()
        if hasattr(self, 'ornament'):
            self.ornament.set_color('#6ea2f0' if self.dark else '#2a62b8')
        self._style_sidebar()
        self._label_theme_button()
        self._update_header()

    _style_sidebar = _sidebar._style_sidebar

    def system_dark(self):
        """The appearance of the system (macOS: light or dark), not the theme of the program."""
        from PySide6.QtGui import QGuiApplication

        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark

    def _system_icon(self, *args):
        """The window and Dock icon: the light or the dark tile; Azimuth.app gets the same tile (hub/dock_icon.py), so
        the Dock keeps it after the program closes. 0.55.0 followed the theme of the program; 0.64.7 (by the user's
        wish): the appearance of the system again — the Dock is part of the system, the program may be dark in a light
        system; a change of the system appearance changes the icon at once (colorSchemeChanged)."""
        from hub import dock_icon

        if not getattr(self, '_scheme_watched', False):
            from PySide6.QtGui import QGuiApplication

            QGuiApplication.styleHints().colorSchemeChanged.connect(self._system_icon)
            self._scheme_watched = True
        dark = self.system_dark()
        icon = app_icon(dark)
        self.setWindowIcon(icon)
        QApplication.instance().setWindowIcon(icon)
        self.setProperty('dock_variant', 'dark' if dark else 'light')
        dock_icon.sync(dark, self.preferences)

    def _update_header(self):
        """Compass, Sextant and Spectrum get the hub header (the home page has none)."""
        if not hasattr(self, 'header') or self.current is None:
            return
        if self.current == HOME:
            self.header.hide()
            if hasattr(self, 'home'):
                self.home.show_texts(self.language, self.dark, getattr(self, 'family', ''), self.windowIcon())
            return
        item = self.sections[self.current]
        self.header.show()
        self.header.show_section(item, self.name(self.current), self.language, self.dark, getattr(self, 'family', ''))
        menus = self._section_menus(self.current)
        self.header.set_menus(menus)
        # the right click and the drag onto the panels of Compass were watched on the menus of Studio only — the header
        # shows menus of its own, made anew for each section
        bar = getattr(self.studio, 'custom_bar', None)
        if bar is not None:
            # the items the header makes itself have keys too; the menus of another section are not those
            # of Compass (and the old ones are deleted) — none then
            bar.set_header_menus(menus if self.current in ('compass', 'crystal') else [])

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fader.isVisible():
            self.fader.setGeometry(self.content.rect())
        wipe = getattr(self, '_theme_wipe', None)
        if wipe is not None:
            try:
                wipe.setGeometry(self.rect())
            except RuntimeError:
                self._theme_wipe = None

    def closeEvent(self, event):
        # Reuse Studio's save/discard/cancel decision before closing the shell.
        decision = QCloseEvent()
        self.studio.closeEvent(decision)
        if not decision.isAccepted():
            event.ignore()
            return
        event.accept()


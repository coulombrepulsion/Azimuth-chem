"""The sidebar of the hub: its buttons of the sections, the logo, the languages and the theme, folding to icons or
opening over the page, its look in the light and the dark theme. Methods of HubWindow (self is the window), kept here
to make window.py shorter.

Split off hub/window.py (0.222.30).
"""

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QVBoxLayout, QWidget
from hub import registry
from hub.branding import SvgIconEngine, glyph_logo, sidebar_family
from hub.chrome import BrandMark, MoleculeArt, NavGroup, SiteArrow


SLIDE_MS = 320  # the sidebar slides over the page (full travel; a partial one takes its share)


WIDE, NARROW = 196, 68


LANGUAGES = ('ru', 'en', 'zh')  # was modules.atlas.panel.LANGUAGES


LANGUAGE_LABELS = {'ru': 'RU', 'en': 'EN', 'zh': '中文'}


LANGUAGE_STYLE = (
    'QPushButton#lang {background: transparent; color: #bfd1db; border: 1px solid #34486b; '
    'border-radius: 6px; padding: 5px 0; font-weight: 500; min-width: 44px; max-width: 44px;} '
    'QPushButton#lang:hover {border-color: #6ea2f0;} '
    'QPushButton#lang:checked {background: #2a62b8; color: white; border-color: #2a62b8;}'
)


LANGUAGE_STYLE_LIGHT = (  # the light panel
    'QPushButton#lang {background: transparent; color: #4b5a6e; border: 1px solid #c3cdd9; '
    'border-radius: 6px; padding: 5px 0; font-weight: 500; min-width: 44px; max-width: 44px;} '
    'QPushButton#lang:hover {border-color: #2a62b8;} '
    'QPushButton#lang:checked {background: #2a62b8; color: white; border-color: #2a62b8;}'
)


BACK_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M14.5 5.5 8 12l6.5 6.5" '
    'fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)


FORWARD_SVG = BACK_SVG.replace('M14.5 5.5 8 12l6.5 6.5', 'M9.5 5.5 16 12l-6.5 6.5')


INFO_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linecap="round"><circle cx="12" cy="12" r="9"/><path d="M12 11v6"/></g>'
    '<circle cx="12" cy="7.6" r="1.1" fill="currentColor"/></svg>'
)


# «Настройки» of the panel — the same window as «Файл → Настройки…» (a gear)
SETTINGS_SVG = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><g fill="none" stroke="currentColor" '
    'stroke-width="1.7" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M12 2.8l1.6 2.5 2.9-.8.8 '
    '2.9 2.5 1.6-1.3 2.7 1.3 2.7-2.5 1.6-.8 2.9-2.9-.8L12 21.2l-1.6-2.5-2.9.8-.8-2.9-2.5-1.6 1.3-2.7-1.3-2.7 '
    '2.5-1.6.8-2.9 2.9.8z"/></g></svg>'
)


# -- sidebar -----------------------------------------------------------------------------
def _build_sidebar(self):
    bar = QFrame()
    bar.setObjectName('sidebar')
    family = self.family = sidebar_family()
    if family:  # sections and buttons of the panel in the typeface of the Atlas and the site, slightly tracked
        bar.setStyleSheet(f"QPushButton#nav {{font-family: '{family}'; font-size: 13.5px; letter-spacing: 0.3px;}}")
    column = QVBoxLayout(bar)
    column.setContentsMargins(10, 16, 10, 14)
    column.setSpacing(6)
    header = QHBoxLayout()
    header.setContentsMargins(4, 0, 0, 0)
    header.setSpacing(8)
    self.logo = QPushButton()  # the application icon; a click opens or closes the panel
    self.logo.setFixedSize(46, 46)
    self.logo.setIconSize(QSize(42, 42))
    self.logo.setFlat(True)
    self.logo.setCursor(Qt.CursorShape.PointingHandCursor)
    self.logo.setStyleSheet(
        'QPushButton {border: none; background: transparent; padding: 0;}'
        'QPushButton:hover {background: rgba(255, 255, 255, 0.12); border-radius: 9px;}'
    )
    self.logo.clicked.connect(self._logo_clicked)
    header.addWidget(self.logo)
    self.brand = BrandMark()
    self.brand.setObjectName('wordmark')
    header.addWidget(self.brand)
    header.addStretch(1)
    column.addLayout(header)
    history = QHBoxLayout()  # back / forward through the sections shown
    history.setContentsMargins(4, 4, 0, 0)
    history.setSpacing(0)
    self.back_button, self.forward_button = QPushButton(), QPushButton()
    for button, svg, step in ((self.back_button, BACK_SVG, -1), (self.forward_button, FORWARD_SVG, 1)):
        button.setObjectName('hist')
        button.setFixedSize(20, 26)
        button.setIcon(QIcon(SvgIconEngine(svg)))
        button.setIconSize(QSize(18, 18))
        button.setFlat(True)
        button.setEnabled(False)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setStyleSheet(
            'QPushButton {border: none; background: transparent; padding: 0;}'
            'QPushButton:hover:enabled {background: rgba(255, 255, 255, 0.12); border-radius: 6px;}'
        )
        button.clicked.connect(lambda checked=False, step=step: self.go_history(step))
        history.addWidget(button)
    history.addStretch(1)
    column.addLayout(history)
    column.addSpacing(6)
    self.brand_rule = QFrame()  # thin line under the name
    self.brand_rule.setObjectName('brandRule')
    self.brand_rule.setFixedHeight(1)
    self.brand_rule.setStyleSheet('QFrame#brandRule {background: rgba(255, 255, 255, 0.14); border: none;}')
    column.addWidget(self.brand_rule)
    column.addSpacing(12)
    self.buttons = {}
    for number, item in enumerate(self.sections.values(), start=1):
        button = QPushButton(item['title'])
        button.setObjectName('nav')
        button.setCheckable(True)
        button.setIcon(QIcon(SvgIconEngine(registry.icon_svg(item))))
        button.setIconSize(QSize(22, 22))
        button.setToolTip(f'{item["title"]} · Ctrl+{number}')
        button.setAccessibleName(item['title'])
        button.clicked.connect(lambda checked=False, ident=item['id']: self._nav_clicked(ident))
        if item['id'] == 'atlas':  # a link to the site, not a section that stays chosen
            button.setCheckable(False)
            self.site_arrow = SiteArrow(button)  # «↗» — it opens outside the window
        self.buttons[item['id']] = button
        if item['page'] == 0 and 'crystal' in self.sections:  # both Compasses joined by a line
            if not hasattr(self, 'compass_group'):
                self.compass_group = NavGroup(column.spacing())
                column.addWidget(self.compass_group)
            self.compass_group.add(button)
        else:
            column.addWidget(button)
        if item['id'] == 'atlas':  # the Atlas (the site) apart from the sections of the program
            column.addSpacing(4)
            self.atlas_rule = QFrame()
            self.atlas_rule.setObjectName('atlasRule')
            self.atlas_rule.setFixedHeight(1)
            self.atlas_rule.setStyleSheet('QFrame#atlasRule {background: rgba(255, 255, 255, 0.14); border: none;}')
            column.addWidget(self.atlas_rule)
            column.addSpacing(4)
    # molecules in thin lines, like the scales on the pages; under the whole panel (its child
    # that follows its size), not only in the free height of the column
    self.panel_art = MoleculeArt(bar)
    self.panel_art.top = lambda: self.brand_rule.geometry().bottom()  # nothing above the line under the name
    column.addStretch(1)
    from hub.job_indicator import JobIndicator

    # a calculation running (or just finished) — the hourglass; a click shows its window. At the
    # bottom, over the languages, and only while the window of the calculation is hidden with «Скрыть»
    # the hourglass lies over the molecules of the background (not in the layout): they neither move nor
    # disappear when it comes; it stands just above the languages (_place_job_indicator)
    self.job_indicator = JobIndicator(lambda: getattr(self, 'studio', None), bar)
    self.job_indicator.hide()
    self._indicator_gap = column.spacing()
    self.language_row = QWidget()
    self.language_row.installEventFilter(self)  # the hourglass follows it
    self.job_indicator.installEventFilter(self)
    self.language_row.setStyleSheet(LANGUAGE_STYLE)
    row = QHBoxLayout(self.language_row)
    row.setContentsMargins(2, 0, 2, 4)
    row.setSpacing(4)
    self.language_buttons = {}
    self.language_group = QButtonGroup(self)
    self.language_group.setExclusive(True)
    for code in LANGUAGES:
        button = QPushButton(LANGUAGE_LABELS[code])
        button.setObjectName('lang')
        button.setCheckable(True)
        button.setAccessibleName(LANGUAGE_LABELS[code])
        button.clicked.connect(lambda checked=False, code=code: self._language_clicked(code))
        self.language_group.addButton(button)
        self.language_buttons[code] = button
        row.addWidget(button)
    row.addStretch(1)  # fixed 44 px buttons from the left: the current one stays in the rail
    column.addWidget(self.language_row)
    self.theme_button = QPushButton()
    self.theme_button.setObjectName('nav')
    self.theme_button.setIconSize(QSize(22, 22))
    self.theme_button.clicked.connect(self.toggle_theme)
    column.addWidget(self.theme_button)
    self.settings_button = QPushButton()
    self.settings_button.setObjectName('nav')
    self.settings_button.setIconSize(QSize(22, 22))
    self.settings_button.setIcon(QIcon(SvgIconEngine(SETTINGS_SVG)))
    self.settings_button.clicked.connect(lambda: self.studio.show_settings())
    column.addWidget(self.settings_button)
    self.about_button = QPushButton()
    self.about_button.setObjectName('nav')
    self.about_button.setIconSize(QSize(22, 22))
    self.about_button.setIcon(QIcon(SvgIconEngine(INFO_SVG)))
    self.about_button.clicked.connect(self.show_about)
    column.addWidget(self.about_button)
    return bar


def set_collapsed(self, collapsed, animate=True):
    """Icons only (NARROW, the rail) or opened over the page with names (WIDE). Starts closed.
    Opening: names are set first and uncovered by the slide, the wordmark appears letter by letter.
    Closing: names stay until the panel is narrow again."""
    self.collapsed = bool(collapsed)
    if not self.collapsed:
        self.brand.show()
        self._relabel()
        if not self.sidebar.isHidden():
            self.scrim.show()
    target = 0.0 if self.collapsed else 1.0
    self.slide.stop()
    if animate and self.isVisible() and self._progress != target:
        self.slide.setDuration(max(60, round(SLIDE_MS * abs(target - self._progress))))
        self.slide.setStartValue(self._progress)
        self.slide.setEndValue(target)
        self.slide.start()
    else:
        self._apply_progress(target)
        self._slide_done()


def _apply_progress(self, value):
    self._progress = float(value)
    self._place_sidebar()
    if hasattr(self, 'site_arrow'):  # the arrow of the Atlas where the panel shows it (rail or open)
        button = self.site_arrow.parentWidget()
        self.site_arrow.place(self.sidebar.width() - button.mapTo(self.sidebar, button.rect().topLeft()).x())
    self.brand.set_progress(self._progress)
    self.scrim.set_level(self._progress)


def _slide_done(self):
    if self.collapsed:
        self.brand.hide()
        self.scrim.hide()
        self._relabel()


def _place_sidebar(self, animate=False):
    root = self.centralWidget()
    width = round(NARROW + (WIDE - NARROW) * self._progress)
    self.sidebar.setGeometry(0, 0, width, root.height())
    self.panel.setGeometry(0, 0, WIDE, root.height())
    self.edge.setGeometry(width - 1, 0, 1, root.height())
    self.edge.raise_()
    self.scrim.setGeometry(QRect(NARROW, 0, max(0, root.width() - NARROW), root.height()))
    self.scrim.raise_()
    self.sidebar.raise_()


def _style_sidebar(self):
    """Light theme — a grey panel with a little blue, dark ink and the dark glyph; dark theme — navy."""
    from hub.branding import set_sidebar_theme

    dark = self.dark
    set_sidebar_theme(dark)
    hover = 'rgba(255, 255, 255, 0.12)' if dark else 'rgba(27, 34, 48, 0.07)'
    self.logo.setIcon(glyph_logo(dark))
    self.logo.setStyleSheet(
        f'QPushButton {{border: none; background: transparent; padding: 0;}}QPushButton:hover {{background: {hover}; border-radius: 9px;}}'
    )
    for button in (self.back_button, self.forward_button):
        button.setStyleSheet(
            f'QPushButton {{border: none; background: transparent; padding: 0;}}'
            f'QPushButton:hover:enabled {{background: {hover}; border-radius: 6px;}}'
        )
    self.brand_rule.setStyleSheet(
        'QFrame#brandRule {background: %s; border: none;}' % ('rgba(255, 255, 255, 0.14)' if dark else 'rgba(27, 34, 48, 0.12)')
    )
    if hasattr(self, 'atlas_rule'):  # as the line under the name
        self.atlas_rule.setStyleSheet(
            'QFrame#atlasRule {background: %s; border: none;}' % ('rgba(255, 255, 255, 0.14)' if dark else 'rgba(27, 34, 48, 0.12)')
        )
    if hasattr(self, 'site_arrow'):
        self.site_arrow.set_color('#6ea2f0' if dark else '#2a62b8')
    self.edge.setStyleSheet('QFrame#sidebarEdge {background: %s; border: none;}' % ('#33435f' if dark else '#cfd7e2'))
    self.language_row.setStyleSheet(LANGUAGE_STYLE if dark else LANGUAGE_STYLE_LIGHT)
    self.panel_art.set_color('#6ea2f0' if dark else '#2a62b8', dark)
    if hasattr(self, 'compass_group'):
        self.compass_group.set_color('#6ea2f0' if dark else '#2a62b8')
    for widget in [self.logo, self.back_button, self.forward_button, self.theme_button, self.about_button,
                   self.settings_button, *self.buttons.values()]:
        widget.update()

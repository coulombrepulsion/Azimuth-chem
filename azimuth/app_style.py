"""The style sheets of Azimuth: STYLE (light) and DARK_STYLE (dark), with the paths of the pictures of the arrows,
the check mark and the closing cross put in. theme_extra(dark) — the part made at run time;
theme_style_sheet() — both themes in one sheet (azimuth/theme_sheet.py).

Split off azimuth/app.py (0.222.30); azimuth.app.STYLE and DARK_STYLE still name them.
"""

from azimuth.paths import ROOT
from azimuth.ui import menu_font_family


STYLE = '''
QWidget {font-family: 'Segoe UI', 'Helvetica Neue', sans-serif; font-size: 13px; color: #1b2230;}
QMainWindow, QWidget#workspace {background: #f5f6f8;}
QFrame#sidebar {background: #e6ebf2;}
QFrame#sidebar QLabel {color: #3f4d61; background: transparent;}
QLabel#brand {color: white; font-size: 25px; font-weight: 700;}
QLabel#heading {font-size: 22px; font-weight: 700; color: #1b2230;}
QLabel#subtitle {color: #5b6474; font-size: 13px;}
QLabel#eyebrow {color: #2a62b8; font-size: 11px; font-weight: 700;}
QLabel#cardtitle {font-size: 17px; font-weight: 600;}
QFrame#card {background: white; border: 1px solid #d8dce3; border-radius: 12px;}
/* 2026-11-19 (the owner, «Свой вид»: «пусть заголовки хоть как-то выделяются от другого текста»; «хочу чуть больше
   элементов золотого цвета»): the heading of a group — semibold, a little larger, a short gold line under it; the
   group a rounded frame of the cards (the square native one went with the heading drawn by the style sheet) */
QGroupBox {border: 1px solid #d8dce3; border-radius: 9px; margin-top: 26px; padding: 12px 8px 8px 8px; font-weight: 600;}
QGroupBox::title {subcontrol-origin: margin; subcontrol-position: top left; left: 2px; top: 0px; padding: 0 2px 3px 2px; color: #1b2230; border-bottom: 2px solid #e2bf78;}
/* 2026-11-19 (the owner: «заголовки с подчёркиванием золотым пусть будут полужирными»): the font of the title is the
   font of the group (::title takes no font) — semibold there, and the rows inside back to the usual weight */
QGroupBox > QWidget {font-weight: 400;}
QGroupBox > QPushButton {font-weight: 500;}
QTreeWidget#surfacesTree {background: #fbfcfd; border: 1px solid #d8dce3; border-radius: 10px; padding: 6px 4px;}
QTreeWidget#surfacesTree::item {padding: 3px 2px; border: 1px solid transparent; border-radius: 6px;}
QTreeWidget#surfacesTree::item:hover {border-color: #9db8e0; background: rgba(42, 98, 184, 12);}  /* 2026-11-18: the row under the mouse */
QFrame#densityDrawer {background: white; border: 1px solid #d8dce3; border-radius: 12px;}
QFrame#trajectoryDrawer {background: white; border: none; border-right: 1px solid #d8dce3; border-radius: 0px;}
QFrame#projectPane {background: white; border: 1px solid #d8dce3; border-radius: 12px;}
QWidget#resultCard {background: white; border: 1px solid #d8dce3; border-radius: 12px;}
QFrame#resultGroup {background: #eef2f7; border: 1px solid #e1e6ed; border-radius: 14px;}
QFrame#drawerRule {background: #e1e6ed; border: none;}
QLabel#toast {background: rgba(27, 34, 48, 226); color: #f4f6f9; border-radius: 10px; padding: 0; font-size: 13px;}  /* 2026-11-18: the air round the words — contents margins (ui.fit_pill: SIDE, TOP) */
QFrame#statusPill {background: rgba(27, 34, 48, 226); border-radius: 10px;}  /* 2026-11-17: the status of Spectrum */
QFrame#statusPill QLabel {color: #f4f6f9; background: transparent;}
QFrame#statusPill QLabel#statusMessage {border-top: 1px solid rgba(244, 246, 249, 70); margin-top: 5px; padding-top: 5px;}
/* 2026-11-18: the room of the sign of waiting — a contents margin of the pill (azimuth.ui.fit_pill), not a padding */
QFrame#trajectoryDrawer QTableWidget, QFrame#densityDrawer QTableWidget, QFrame#projectPane QTableWidget {background: transparent; border: none; alternate-background-color: #f8fafc;}
QFrame#trajectoryDrawer QHeaderView::section, QFrame#densityDrawer QHeaderView::section, QFrame#projectPane QHeaderView::section {background: transparent; border: none; border-bottom: 1px solid #e1e6ed; padding: 4px; color: #5b6474; font-weight: 600;}
QLabel#choicePill {background: transparent; border: 1px solid #c3cbd6; border-radius: 7px; padding: 6px 9px; color: #1b2230;}
QFrame#toolRule, QFrame#panelRule {background: #dde2e8; border: none;}
QFrame#panelRule {margin: 0 14px;}
QPushButton {background: white; border: 1px solid #d8dce3; border-radius: 7px; padding: 9px 13px; font-weight: 500;}
QPushButton:hover {background: #eef0f4; border-color: #6ea2f0;}
QPushButton:pressed {background: #e4e9f0; border-color: #2a62b8; padding-top: 10px; padding-bottom: 8px;}
/* 2026-11-18 (the owner, «Цвет элемента C», «Цвет связи»: «окна упорядочить, чтобы всё было ровно и аккуратно
   расположено внутри»): the picker of colours of Qt — its buttons and fields compact and of one height; the tall
   ones made the right half high and left an empty band in the left one */
QColorDialog QPushButton, QColorDialog QPushButton:pressed {padding: 4px 12px; min-height: 22px;}
QColorDialog QSpinBox {padding: 2px 26px 2px 6px; min-height: 22px; min-width: 44px;}
QColorDialog QLineEdit {padding: 2px 6px; min-height: 22px;}
/* 2026-11-17, the rule of the buttons (the owner: «почему в некоторых местах кнопка синяя, а где-то белая? надо общее
   правило», agreed): a blue fill — the one main action of a card or a window (#primary); the rest white, «Закрыть» too;
   a switch that is on — a light blue ground with a blue frame, not the fill; the gold of the icons, sparingly — a gold
   frame round the next step (#primary[next="true"]) and the gold star of a recommendation */
QPushButton:checked, QPushButton[on="true"] {background: #e4ecf8; color: #1d4f9c; border-color: #6ea2f0;}
QPushButton:checked:hover, QPushButton[on="true"]:hover {background: #d8e4f6; color: #1d4f9c; border-color: #2a62b8;}
QPushButton:checked:pressed {background: #cddcf3; color: #1d4f9c;}
QPushButton:disabled {color: #95a4ae; background: #edf1f4;}
QPushButton#primary {background: #2a62b8; color: white; border: 1px solid #2a62b8;}
QPushButton#primary:hover {background: #204e94; border-color: #e2bf78;}
QPushButton#primary:pressed {background: #1a3f78; padding-top: 10px; padding-bottom: 8px;}
QPushButton#primary:disabled {background: #dde2e8; color: #95a4ae; border-color: #dde2e8;}
QPushButton#primary[next="true"] {border: 2px solid #e2bf78;}
QPushButton#primary[next="true"]:hover {border-color: #f2d595;}
QPushButton#nav {text-align: left; background: transparent; color: #3f4d61; border: none; padding: 14px 12px;}
QPushButton#nav:checked {background: rgba(42, 98, 184, 36); color: #1b2230; border-left: 3px solid #2a62b8;}
QPushButton#nav:hover:!checked {background: rgba(42, 98, 184, 20);}
QComboBox, QSpinBox, QDoubleSpinBox {background: white; border: 1px solid #d8dce3; border-radius: 8px; padding: 6px 10px; min-height: 20px;}
QComboBox {padding-right: 30px;}
QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover {border-color: #9db8e0;}
QComboBox:on, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {border-color: #2a62b8;}
QComboBox::drop-down {subcontrol-origin: padding; subcontrol-position: center right; width: 28px; border: none; background: transparent;}
QComboBox::down-arrow {image: url(CHEVRON); width: 11px; height: 7px;}
QComboBox::down-arrow:on {top: 1px;}
QComboBoxPrivateContainer {background: transparent; border: none;}
QComboBox {combobox-popup: 0;}
QSpinBox, QDoubleSpinBox {padding-right: 28px;}
QSpinBox::up-button, QDoubleSpinBox::up-button, QSpinBox::down-button, QDoubleSpinBox::down-button {subcontrol-origin: border; width: 22px; border: none; border-left: 1px solid #e1e6ed; background: transparent; margin-right: 1px;}
QSpinBox::up-button, QDoubleSpinBox::up-button {subcontrol-position: top right; margin-top: 1px; border-top-right-radius: 7px;}
QSpinBox::down-button, QDoubleSpinBox::down-button {subcontrol-position: bottom right; margin-bottom: 1px; border-bottom-right-radius: 7px;}
QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover, QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {background: #eef2f7;}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed, QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {background: #e4e9f0;}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {image: url(ARROWUP); width: 9px; height: 6px;}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {image: url(CHEVRON); width: 9px; height: 6px;}
QSpinBox::up-arrow:off, QDoubleSpinBox::up-arrow:off, QSpinBox::down-arrow:off, QDoubleSpinBox::down-arrow:off, QSpinBox::up-arrow:disabled, QDoubleSpinBox::up-arrow:disabled, QSpinBox::down-arrow:disabled, QDoubleSpinBox::down-arrow:disabled {image: none;}
QProgressBar#jobBar {background: #e1e6ed; border: none; border-radius: 3px;}
QProgressBar#jobBar::chunk {background: #2a62b8; border-radius: 3px;}
QToolButton#helpButton {border: 1px solid #c3cbd6; border-radius: 11px; color: #2a62b8; font-weight: 700; font-size: 13px; background: transparent;}
QToolButton#helpButton:hover {background: #e4ecf8;}
QLabel#jobStages {color: #1b2230; line-height: 140%;}
QLineEdit {background: white; border: 1px solid #d8dce3; border-radius: 8px; padding: 5px 9px; min-height: 20px;}
QLineEdit:hover {border-color: #9db8e0;}
QLineEdit:focus {border-color: #2a62b8;}
QLineEdit:disabled {background: #edf1f4; color: #95a4ae;}
/* 2026-11-19 (the owner: «поле „Молекул“ не серое, оно просто не нажимается»): a number field switched off is grey as
   a text field switched off */
QAbstractSpinBox:disabled {background: #edf1f4; color: #95a4ae;}
QAbstractSpinBox QLineEdit, QComboBox QLineEdit {background: transparent; border: none; padding: 0; min-height: 0; border-radius: 0;}
QAbstractItemView QLineEdit {padding: 0 4px; min-height: 0; border-radius: 4px; border: 1px solid #2a62b8;}
QCheckBox, QRadioButton {spacing: 8px;}
QCheckBox::indicator, QAbstractItemView::indicator {width: 15px; height: 15px; border: 1px solid #a9b4c2; border-radius: 4px; background: white;}
QRadioButton::indicator {width: 15px; height: 15px; border: 1px solid #a9b4c2; border-radius: 8px; background: white;}
QCheckBox::indicator:hover, QRadioButton::indicator:hover, QAbstractItemView::indicator:hover {border-color: #2a62b8;}
QCheckBox::indicator:checked, QAbstractItemView::indicator:checked {background: #2a62b8; border-color: #2a62b8; image: url(CHECKMARK);}
QRadioButton::indicator:checked {background: white; border: 5px solid #2a62b8;}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {background: #edf1f4; border-color: #c3cbd6;}
QCheckBox::indicator:checked:disabled {background: #c3cbd6; border-color: #c3cbd6;}
QCheckBox:disabled, QRadioButton:disabled {color: #95a4ae;}
QLineEdit#measure {font-size: 11px; padding: 1px 6px; border: 1px solid #d8dce3; border-radius: 6px;}
QPushButton[iconic="true"] {background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 0;}
QPushButton[iconic="true"]:hover {background: #eef2f7; border-color: #e1e6ed;}
QPushButton[iconic="true"]:pressed {background: #e4e9f0;}
QPushButton[iconic="true"]:checked {background: #e4ecf8; border-color: #c6d6ef;}
QPushButton[iconic="true"]:disabled {background: transparent; border-color: transparent;}
QPlainTextEdit, QTableWidget {background: #fbfcfd; border: 1px solid #d8dce3; border-radius: 6px; selection-background-color: #dbe8fb; selection-color: #1b2230;}
QPlainTextEdit#code {font-family: 'Menlo', 'Consolas', monospace; font-size: 13px;}
QHeaderView::section {background: #edf2f5; border: none; padding: 7px; color: #5b7180;}
QLabel#notice {background: #eef0f4; border: 1px solid #d8dce3; border-radius: 8px; padding: 14px; color: #2a62b8;}
QLabel#error {color: #a13d3d; background: #fff2ee; border-radius: 5px; padding: 9px;}
QTabWidget::pane {border: 1px solid #d8dce3; background: white; border-radius: 10px; top: -1px;}
QTabBar::tab {background: #eaf0f3; color: #526d7c; padding: 9px 22px; margin-right: 4px; border: 1px solid transparent; border-bottom: none; border-top-left-radius: 9px; border-top-right-radius: 9px; font-weight: 500;}
QTabBar::tab:hover:!selected {background: #e1e8ee; color: #1b2230;}
QTabBar::tab:selected {background: #2a62b8; color: white;}
QTabBar#documents {background: transparent;}
/* 0.248.7 (the owner: «пусть каждая вкладка проекта имеет вид тонкого стекла, практически полностью прозрачного»): each tab a thin pane of glass — almost clear, a light edge above, a darker one below */
QTabBar#documents::tab {height: 26px; min-width: 112px; padding: 0 12px 0 14px; margin: 0; background: rgba(255, 255, 255, 0.22); color: #5b6474; border: 1px solid rgba(255, 255, 255, 0.75); border-bottom-color: rgba(27, 34, 48, 0.12); border-right-color: rgba(27, 34, 48, 0.08); border-top-left-radius: 8px; border-top-right-radius: 8px; border-bottom-left-radius: 0; border-bottom-right-radius: 0; font-size: 12px; font-weight: 500;}
QTabBar#documents::tab:selected {color: #1b2230; background: rgba(255, 255, 255, 0.42); border-bottom: 2px solid #2a62b8;}
QTabBar#documents::tab:hover:!selected {color: #1b2230; background: rgba(255, 255, 255, 0.34);}
QTabBar#documents::close-button {image: url(TABCLOSE); subcontrol-position: right; width: 22px; height: 12px; margin-left: 0; margin-right: 10px; border-radius: 3px;}  /* 12 px of the cross and 10 px clear after it (0.248.13) */
QTabBar#documents::close-button:hover {background: #e1e6ed;}
QFrame#documentRow {border: none; background: transparent;}
QLabel#calcFormula {color: #1b2230; font-size: 18px; font-weight: 600;}
QFrame#queueBanner {background: #e4ecf8; border: 1px solid #c6d6ef; border-radius: 8px;}
QFrame#queueBanner QLabel {color: #2a62b8; background: transparent;}
QTabBar#viewTabs::tab {padding: 6px 16px; margin-right: 3px;}
QTabWidget#structureTabs::pane {top: 0px;}
QTabBar#drawerTabs::tab {padding: 5px 10px; margin-right: 2px; font-size: 12.5px; border-radius: 7px;}
QTabBar#drawerTabs::tab:disabled {color: #c3cbd6; background: transparent;}
QTabBar#drawerSubTabs::tab {padding: 3px 10px; margin-right: 2px; font-size: 12px; background: transparent; color: #5b6474; border: none; border-bottom: 2px solid transparent; border-radius: 0;}
QTabBar#drawerSubTabs::tab:selected {color: #1b2230; background: transparent; border-bottom: 2px solid #2a62b8;}
QFrame#trajectoryDrawer QTabWidget::pane {border: none; background: transparent; top: 0px;}
QStatusBar {background: white; color: #657b89;}
'''


DARK_STYLE = STYLE
for old, new in {
    '#1b2230': '#e7eaf0',
    '#f5f6f8': '#11151c',
    '#5b6474': '#9aa3b2',
    '#2a62b8': '#6ea2f0',
    'background: white': 'background: #191f28',
    '#d8dce3': '#2b333f',
    '#eef0f4': '#212833',
    '#95a4ae': '#80909d',
    '#edf1f4': '#212833',
    '#f8fafc': '#11151c',
    '#fbfcfd': '#11151c',
    '#edf2f5': '#212833',
    '#5b7180': '#c2d2dc',
    '#a13d3d': '#ffb9a9',
    '#fff2ee': '#492e30',
    '#eaf0f3': '#212833',
    '#526d7c': '#c0d2df',
    '#657b89': '#9aa3b2',
    '#9db8e0': '#3d5a86',
    '#eef2f7': '#232b36',
    '#e1e6ed': '#2b333f',
    '#e4e9f0': '#2a3340',
    '#e4ecf8': '#26364f',
    '#c3cbd6': '#46505e',
    '#a9b4c2': '#56627a',  # the border of a check box
    '#dde2e8': '#2a313b',
    '#c6d6ef': '#3d5a86',
    '#e1e8ee': '#2a323d',
    # the side panel — grey with a little blue in the light theme, deep navy in the dark theme
    '#e6ebf2': '#172133',  # lighter than the page (#11151c), was #0e1521
    '#3f4d61': '#bfd1db',
    # the chosen section and the one under the mouse — a see-through tint of the accent, as
    # --rail-on of the side panel of the site (site/rail.js), the picture of the panel shows through
    'rgba(42, 98, 184, 36)': 'rgba(110, 162, 240, 56)',
    'rgba(42, 98, 184, 20)': 'rgba(110, 162, 240, 30)',
}.items():
    DARK_STYLE = DARK_STYLE.replace(old, new)
STYLE = STYLE.replace('ARROWUP', (ROOT / 'assets' / 'ui' / 'chevron-up.svg').as_posix())  # spin boxes
STYLE = STYLE.replace('CHEVRON', (ROOT / 'assets' / 'ui' / 'chevron-down.svg').as_posix())
STYLE = STYLE.replace('TABCLOSE', (ROOT / 'assets' / 'ui' / 'tab-close.svg').as_posix())
STYLE = STYLE.replace('CHECKMARK', (ROOT / 'assets' / 'ui' / 'check.svg').as_posix())  # check boxes
DARK_STYLE = DARK_STYLE.replace('CHECKMARK', (ROOT / 'assets' / 'ui' / 'check-dark.svg').as_posix())
DARK_STYLE = DARK_STYLE.replace('TABCLOSE', (ROOT / 'assets' / 'ui' / 'tab-close-dark.svg').as_posix())
DARK_STYLE = DARK_STYLE.replace('ARROWUP', (ROOT / 'assets' / 'ui' / 'chevron-up-dark.svg').as_posix())
DARK_STYLE = DARK_STYLE.replace('CHEVRON', (ROOT / 'assets' / 'ui' / 'chevron-down-dark.svg').as_posix())
# a dark pill with a light frame
DARK_STYLE += ('\nQTabBar#documents::tab {background: rgba(255, 255, 255, 0.04); border: 1px solid rgba(255, 255, 255, 0.14);'
               ' border-bottom-color: rgba(0, 0, 0, 0.35); border-right-color: rgba(0, 0, 0, 0.25);}'
               '\nQTabBar#documents::tab:selected {background: rgba(255, 255, 255, 0.09); border-bottom: 2px solid #6ea2f0;}'
               '\nQTabBar#documents::tab:hover:!selected {background: rgba(255, 255, 255, 0.07);}')  # glass tabs (0.248.7)
DARK_STYLE += '\nQLabel#toast {background: rgba(46, 54, 68, 240); color: #e7eaf0; border: 1px solid #4a5568;}'
DARK_STYLE += ('\nQFrame#statusPill {background: rgba(46, 54, 68, 240); border: 1px solid #4a5568;}'
               '\nQFrame#statusPill QLabel {color: #e7eaf0;}'
               '\nQFrame#statusPill QLabel#statusMessage {border-top-color: rgba(231, 234, 240, 60);}'
               # as the toast
               '\nQTreeWidget#surfacesTree::item:hover {border-color: #4f6f9f; background: rgba(110, 162, 240, 22);}')
# the filled buttons, the tab chosen and the checked boxes in the blue of the languages and of the light theme (#2a62b8)
# — the replacement above made them the light #6ea2f0 under white text
DARK_STYLE += ('\nQPushButton:checked, QPushButton[on="true"] {background: rgba(110, 162, 240, 46); color: #cfe0fa; border-color: #6ea2f0;}'
               '\nQPushButton:checked:hover, QPushButton[on="true"]:hover {background: rgba(110, 162, 240, 70); color: #e4eefc; border-color: #9cc0f5;}'
               '\nQPushButton:checked:pressed {background: rgba(110, 162, 240, 90); color: #e4eefc;}'
               '\nQPushButton#primary[next="true"] {border: 2px solid #f2d595;}'
               '\nQPushButton#primary {background: #2a62b8; color: white; border: 1px solid #2a62b8;}'
               # a blue button under the mouse
               # — a thin gold frame (the frame of the next step stays 2 px, always)
               '\nQPushButton#primary:hover {border-color: #f2d595;}'
               '\nQGroupBox::title {border-bottom-color: #f2d595;}'  # the gold of the dark theme
               '\nQTabBar::tab:selected {background: #2a62b8; color: white;}'
               '\nQCheckBox::indicator:checked, QAbstractItemView::indicator:checked {background: #2a62b8; border-color: #2a62b8;}'
               '\nQProgressBar#jobBar::chunk {background: #2a62b8;}')
DARK_STYLE += '\nQDialog {background: #191f28;} QComboBox QAbstractItemView {background: #191f28; color: #e7eaf0; selection-background-color: #2a62b8;} QToolTip {background: #212833; color: white;}'


def theme_extra(dark):
    """The part of the sheet of a theme made at run time (the colours of the tables, menus, fields, scroll bars)."""
    background = '#11151c' if dark else '#fbfcfd'
    foreground = '#e7eaf0' if dark else '#1b2230'
    border = '#2b333f' if dark else '#d8dce3'
    field = '#191f28' if dark else 'white'  # the line edits as the combo boxes and spin boxes
    return f"""
QAbstractScrollArea, QAbstractScrollArea > QWidget, QAbstractScrollArea > QWidget > QWidget {{background: {background}; color: {foreground};}}
QTableWidget {{gridline-color: {border};}}
QTableWidget::item {{background: {background}; color: {foreground};}}
QTableWidget::item:selected {{background: {'#26364f' if dark else '#e4ecf8'}; color: {foreground};}}
QMenuBar, QMenu {{background: {background}; color: {foreground};}}
QMenu::item:selected {{background: {'#26364f' if dark else '#e4ecf8'}; color: {foreground};}}
QMenu {{border: 1px solid {border}; border-radius: 9px; padding: 5px; font-family: '{menu_font_family()}'; font-size: 13px;}}
QMenu::item {{padding: 5px 24px 5px 26px; border-radius: 6px;}}
QMenu::item:disabled, QMenu::item:disabled:selected {{color: {'#5f6a7a' if dark else '#a3adbb'}; background: transparent;}}
QMenu::separator {{height: 1px; background: {border}; margin: 4px 8px;}}
QMenu::indicator {{width: 12px; height: 12px; left: 8px;}}
QTableCornerButton::section, QHeaderView, QHeaderView::section {{background: {background}; color: {foreground}; border: none;}}
QHeaderView::section {{border-right: 1px solid {border}; border-bottom: 1px solid {border}; padding: 6px 8px;}}
QHeaderView::section:last {{border-right: none;}}
QHeaderView::section:vertical {{border-right: 1px solid {border}; border-bottom: 1px solid {border}; padding: 0 6px;}}
QTableWidget {{border-radius: 0;}}
QTableWidget::item {{padding: 0 8px;}}
QLineEdit {{background: {field}; color: {foreground}; selection-background-color: #2a62b8; selection-color: white;}}
QAbstractSpinBox QLineEdit, QComboBox QLineEdit {{background: transparent;}}
QScrollBar:vertical {{background: {background}; width: 12px; margin: 0;}}
QScrollBar:horizontal {{background: {background}; height: 12px; margin: 0;}}
QScrollBar::handle {{background: {border}; border-radius: 4px; min-width: 20px; min-height: 20px;}}
QScrollBar::add-page, QScrollBar::sub-page {{background: {background};}}
QScrollBar::add-line, QScrollBar::sub-line {{width: 0; height: 0; background: {background};}}
"""


def theme_style_sheet():
    """The one style sheet of both themes (azimuth/theme_sheet.py); set on the application before the windows are
    made (hub/launch.py), it costs nothing at the start, and _apply_theme finds it in place."""
    from azimuth import theme_sheet

    return theme_sheet.both(STYLE + theme_extra(False), DARK_STYLE + theme_extra(True))

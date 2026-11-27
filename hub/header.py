"""Section header above Compass, Sextant and Spectrum (moved from window.py)."""

from PySide6.QtCore import (
    QEvent,
    QObject,
    Qt,
)
from PySide6.QtGui import (
    QFont,
)
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from azimuth.ui import smooth
from hub import registry
from hub.texts import HEADER_HEIGHT, HEADER_SCALE, TEXT, TITLE_PX

ICON_PX = 26  # the section icon next to the name
from hub.branding import svg_pixmap, wordmark_pixmap, zh_wordmark_pixmap


class MenuToggle(QObject):
    """A click on the name of an open menu closes it. The click outside the menu first closes it, and on
    Windows the same press then reached the button, which opened the menu again; a press on the button within
    REOPEN_MS after its menu closed is swallowed."""

    REOPEN_MS = 300
    _filter = None

    def __init__(self):
        super().__init__()
        self.closed = {}  # id(button) -> the time its menu closed

    @classmethod
    def watch(cls, button, menu):
        if cls._filter is None:
            cls._filter = cls()
        cls._filter._watch(button, menu)

    def _watch(self, button, menu):
        import time

        key = id(button)
        menu.aboutToHide.connect(lambda: self.closed.__setitem__(key, time.monotonic()))
        button.destroyed.connect(lambda *_: self.closed.pop(key, None))
        button.installEventFilter(self)

    def just_closed(self, button, now=None):
        import time

        when = self.closed.get(id(button))
        now = time.monotonic() if now is None else now
        return when is not None and (now - when) * 1000 < self.REOPEN_MS

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonDblClick) and self.just_closed(watched):
            self.closed.pop(id(watched), None)
            return True  # this press only closed the menu
        return False

class SectionHeader(QFrame):
    """Header above Compass, Sextant and Spectrum: section icon, wordmark, thin rule, section name
    (the same layout as the Atlas header)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('sectionHeader')
        # Pixel copy of the Atlas header (measured in the page): padding 8/16, a 30 px row, a 1 px line
        # below; icon 30, gap 10, wordmark 20 high, 18 to the rule (1 x 1.2em), 12 to the name (TITLE_PX).
        # Since 2026-10-23 the row and everything in it are HEADER_SCALE (1.2) times larger -> 45 px.
        self.setFixedHeight(HEADER_HEIGHT)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(0)
        bar = QWidget()
        bar.setObjectName('sectionBar')
        row = QHBoxLayout(bar)
        row.setContentsMargins(16, 8, 16, 0)
        row.setSpacing(0)
        S = HEADER_SCALE
        row_px = round(30 * S)
        self.icon = QLabel()  # right of the section name (in «Компас · …» between the two words)
        self.icon.setFixedSize(ICON_PX, row_px)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon.setContentsMargins(0, 0, 0, 2)
        self.mark = QLabel()
        self.mark.setFixedHeight(row_px)
        self.mark.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.rule = QFrame()
        self.rule.setFixedSize(1, round(TITLE_PX * 1.2))
        self.title = QLabel()
        self.title.setFixedHeight(row_px)
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.tail = QLabel()  # «МОЛЕКУЛА» / «КРИСТАЛЛ» after the icon; hidden for the other sections
        self.tail.setFixedHeight(row_px)
        self.tail.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.menu_rule = QFrame()  # a second rule, then the menus of the section
        self.menu_rule.setFixedSize(1, round(TITLE_PX * 1.2))
        self.menu_bar = QWidget()
        self.menu_bar.setObjectName('sectionMenus')
        self.menu_row = QHBoxLayout(self.menu_bar)
        self.menu_row.setContentsMargins(0, 0, 0, 0)
        self.menu_row.setSpacing(2)
        self.menu_buttons = []
        # the wordmark first (next to the logo of the panel), then the name and its icon
        for widget, space in (
            (self.mark, round(18 * S)),
            (self.rule, round(12 * S)),
            (self.title, 6),
            (self.icon, 6),
            (self.tail, round(10 * S)),
            (self.menu_rule, round(8 * S)),
            (self.menu_bar, 0),
        ):
            row.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
            row.addSpacing(space)
        row.addStretch(1)
        self.colors = ('#1b2230', '#5b6474', '#2a62b8', '#d8dce3', '#ffffff')
        self.family = ''
        self.line = QFrame()  # the 1 px line under the header, full width as in the Atlas
        self.line.setFixedHeight(1)
        column.addWidget(bar, 1)
        column.addWidget(self.line)

    def show_section(self, item, name, language, dark, family):
        ratio = self.devicePixelRatioF()
        ink, muted, accent, line, back = (
            ('#e7eaf0', '#9aa3b2', '#6ea2f0', '#2b333f', '#191f28')
            if dark
            else ('#1b2230', '#5b6474', '#2a62b8', '#d8dce3', '#ffffff')
        )
        # glass (0.248.6): the Ornament draws the background of the page under the header as through the panels. Its own
        # ground is the colour 55 % white over the page would give — opaque (0.248.12: a translucent ground blinked
        # while the sections changed); set only when it changes (setStyleSheet repolishes every button of the header)
        glass = '#151b23' if dark else '#fafbfc'
        sheet = f'QFrame#sectionHeader {{background: {glass}; border: none;}}QWidget#sectionBar {{background: transparent;}}'
        if self.styleSheet() != sheet:
            self.setStyleSheet(sheet)
        self.rule.setStyleSheet(f'background: {line}; border: none;')
        self.menu_rule.setStyleSheet(f'background: {line}; border: none;')
        self.colors, self.dark, self.family = (ink, muted, accent, line, back), dark, family
        self.line.setStyleSheet(f'background: {line}; border: none;')
        # The Atlas book glyph fills about 21 of its 30 px box; the section icons fill the whole box,
        # so they are drawn at 24 px, 1 px above the centre, to look the same size and clear the line.
        S = HEADER_SCALE
        self.icon.setPixmap(svg_pixmap(registry.icon_svg(item), accent, ICON_PX - 4, ratio))
        if language == 'zh':
            self.mark.setPixmap(zh_wordmark_pixmap(round(27 * S), ratio, ink, accent, family))  # Atlas: 27 px x S
        else:
            self.mark.setPixmap(wordmark_pixmap(language, round(20 * S), ratio, dark))
        self.mark.setAccessibleName(TEXT[language]['brand'])
        font = QFont(family) if family else QFont(self.title.font())
        font.setPixelSize(TITLE_PX)
        font.setWeight(QFont.Weight.Medium)
        font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, TITLE_PX * 0.14)
        head, _, tail = name.upper().partition(' · ')  # «КОМПАС · МОЛЕКУЛА»: the icon instead of the dot
        self.title.setText(head)
        self.tail.setText(tail)
        self.tail.setVisible(bool(tail))
        # The application style sheet sets a QLabel font size, which beats setFont(): size, weight and
        # family go through the style sheet, the tracking (not a style-sheet property) through the font.
        face = f"font-family: '{family}'; " if family else ''
        for label in (self.title, self.tail):
            label.setStyleSheet(f'QLabel {{{face}font-size: {TITLE_PX}px; font-weight: 500; color: {muted};}}')
            label.setFont(font)

    def full_title(self):
        """The section name as shown: «КОМПАС · МОЛЕКУЛА» (the dot is the icon on screen)."""
        return self.title.text() + (' · ' + self.tail.text() if self.tail.text() else '')

    def menu_style(self):
        ink, muted, accent, line, back = self.colors
        dark = getattr(self, 'dark', False)
        pick = '#26364f' if dark else '#e4ecf8'
        from azimuth.ui import menu_font_family

        face = f"font-family: '{menu_font_family()}';"  # the system font, not the typeface of the panel
        return (
            f'QMenu {{background: {back}; color: {ink}; border: 1px solid {line}; border-radius: 9px; '
            f'padding: 4px; {face} font-size: 13px;}}'
            f'QMenu::item {{padding: 4px 22px 4px 24px; border-radius: 5px; background: transparent;}}'
            f'QMenu::item:selected {{background: {pick}; color: {ink};}}'
            f'QMenu::item:disabled, QMenu::item:disabled:selected {{color: {muted}; background: transparent;}}'
            f'QMenu::separator {{height: 1px; background: {line}; margin: 4px 8px;}}'
            f'QMenu::indicator {{width: 12px; height: 12px; left: 8px;}}'
            f'QMenu::right-arrow {{right: 8px;}}'
        )

    def set_menus(self, menus):
        """menus: [(title, QMenu)]; flat text buttons that open the menus (an empty list hides the row)."""
        for button in self.menu_buttons:
            self.menu_row.removeWidget(button)
            button.hide()  # at once: deleteLater() alone would paint it over the new one
            button.deleteLater()
        self.menu_buttons = []
        ink, muted, accent, line, back = self.colors
        hover = '#232b36' if getattr(self, 'dark', False) else '#eef2f7'
        face = f"font-family: '{self.family}';" if self.family else ''
        style = (  # smaller menu names
            f'QToolButton {{background: transparent; border: none; border-radius: 6px; padding: 3px 9px; '
            f'color: {muted}; {face} font-size: 13px;}}'
            f'QToolButton:hover, QToolButton:open {{background: {hover}; color: {ink};}}'
            f'QToolButton::menu-indicator {{image: none; width: 0;}}'
        )
        sheet = self.menu_style()
        for title, menu in menus:
            button = QToolButton(self.menu_bar)
            button.setText(title)
            button.setAccessibleName(title)
            button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setFixedHeight(26)
            button.setStyleSheet(style)
            found, todo = [], [menu]  # every level of submenus
            while todo:
                each = todo.pop()
                if each in found:
                    continue
                found.append(each)
                todo += [a.menu() for a in each.actions() if a.menu()] + each.findChildren(QMenu)
            for each in found:
                each.setStyleSheet(sheet)
                each.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
                each.setWindowFlags(each.windowFlags() | Qt.WindowType.FramelessWindowHint)
                smooth(each)
            button.setMenu(menu)
            MenuToggle.watch(button, menu)  # a second click on the name closes the menu
            self.menu_row.addWidget(button)
            self.menu_buttons.append(button)
        self.menu_rule.setVisible(bool(menus))
        self.menu_bar.setVisible(bool(menus))

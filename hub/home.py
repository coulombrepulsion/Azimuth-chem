"""Hub home page: the name and the motto, what the program is, «continue where you left off», four section cards
(moved from window.py).

Since 0.35.0 Quill's tips live on the Atlas home page (web/assets/js/tips.js); the Atlas, its tips with it, is
on the site — its card opens it in the browser (HubWindow.show_section('atlas')). No Quill and no greeting on the home
page — what is used every day («Продолжить», the
sections) stands at the top; Quill stays in the dialogs, the hints of Compass and on the site."""

import functools

from PySide6.QtCore import (
    QObject,
    QSize,
    Qt,
)
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontDatabase,
    QIcon,
    QPainter,
)
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from hub import registry
from hub.texts import TEXT
from hub.branding import FONTS, glyph_pixmap, svg_pixmap, wordmark_pixmap, zh_wordmark_pixmap
from hub.about import MOTTO, PROGRAM

_CHEVRON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><path d="M6 9.5l6 6 6-6" fill="none" '
            'stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>')


# MOTTO comes from hub.about (the About window shows it too)


@functools.lru_cache(maxsize=1)
def motto_family():
    """Golos Text SemiBold, the face the wordmark is drawn from (strict, sharp strokes)."""
    families = QFontDatabase.applicationFontFamilies(
        QFontDatabase.addApplicationFont(str(FONTS / 'GolosText-SemiBold.ttf'))
    )
    return families[0] if families else ''


class SectionCard(QFrame):
    """A block on the home page: section icon, name and what it is for; a click opens the section."""

    def __init__(self, ident, on_open, parent=None):
        super().__init__(parent)
        self.ident = ident
        self.on_open = on_open
        self.setObjectName('card')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        row = QHBoxLayout(self)
        row.setContentsMargins(18, 16, 18, 16)
        row.setSpacing(16)
        self.icon = QLabel()
        self.icon.setFixedSize(40, 40)
        self.icon.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignHCenter)
        row.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignTop)
        texts = QVBoxLayout()
        texts.setSpacing(6)
        self.title = QLabel()
        self.text = QLabel()
        self.text.setWordWrap(True)
        texts.addWidget(self.title)
        texts.addWidget(self.text)
        texts.addStretch(1)
        row.addLayout(texts, 1)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_open(self.ident)
        event.accept()


class CompassCard(QFrame):
    """The card of Compass on the home page (0.248.0, the owner: «объедини компас в одну панель, и внизу панели раздели
    на 2 части линией, слева молекула, справа кристалл»): the compass and its name over a line; under it two halves
    divided by a line — the molecule and the crystal, each with its own picture; a click on a half opens its part,
    on the head — the molecule."""

    def __init__(self, on_open, parent=None):
        super().__init__(parent)
        self.ident = 'compass'
        self.on_open = on_open
        self.setObjectName('card')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        column = QVBoxLayout(self)
        column.setContentsMargins(18, 16, 18, 10)
        column.setSpacing(10)
        head = QHBoxLayout()
        head.setSpacing(16)
        self.icon = QLabel()
        self.icon.setFixedSize(40, 40)
        head.addWidget(self.icon, 0, Qt.AlignmentFlag.AlignVCenter)
        self.title = QLabel()
        column.addLayout(head)
        texts = QVBoxLayout()
        texts.setSpacing(4)
        texts.addWidget(self.title)
        self.text = QLabel()  # one line about the section, as on the other cards
        texts.addWidget(self.text)
        head.addLayout(texts, 1)
        self.rule = QFrame()
        self.rule.setObjectName('compassRule')
        self.rule.setFixedHeight(1)
        column.addWidget(self.rule)
        halves = QHBoxLayout()
        halves.setSpacing(0)
        self.parts = {}
        for kind in ('compass', 'crystal'):
            if kind == 'crystal':
                self.divider = QFrame()
                self.divider.setObjectName('compassRule')
                self.divider.setFixedWidth(1)
                halves.addWidget(self.divider)
            part = SectionCard(kind, on_open)
            part.setObjectName('compassPart')
            part.layout().setContentsMargins(6, 4, 6, 4)
            part.icon.setFixedSize(30, 30)
            part.text.hide()
            halves.addWidget(part, 1)
            self.parts[kind] = part
        column.addLayout(halves)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.on_open('compass')
        event.accept()


# the pictures of the halves of the card of Compass: the molecule and the crystal of the icons of the two parts
# (assets/navigation/compass.svg, crystal.svg), without the compass
PART_SVG = {
    'compass': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="10.4 1.2 13.4 13.4" fill="none" stroke="currentColor" '
               'stroke-width="0.85" stroke-linecap="round" stroke-linejoin="round"><circle cx="17.6" cy="7" r="2.5"/>'
               '<circle cx="12.6" cy="3.4" r="1.5"/><circle cx="21.6" cy="11.2" r="1.5"/>'
               '<path d="M15.6 5.6 13.9 4.3M19.3 8.8 20.6 10"/></svg>',
    'crystal': '<svg xmlns="http://www.w3.org/2000/svg" viewBox="12.4 3.2 11.4 11.4" fill="none" stroke="currentColor" '
               'stroke-width="0.75" stroke-linecap="round" stroke-linejoin="round">'
               '<path d="M13.6 7.4h6.2v6.2h-6.2zM13.6 7.4l2.8-3h6.2l-2.8 3M22.6 4.4v6.2l-2.8 3"/></svg>',
}
# the compass alone, for the head of the card
COMPASS_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1.8 5.8 20 20" fill="none" stroke="currentColor" '
               'stroke-width="1.15" stroke-linecap="round" stroke-linejoin="round"><circle cx="8.2" cy="15.8" r="6"/>'
               '<path d="M11.6 12.4 9.4 17 4.8 19.2 7 14.6Z"/></svg>')
PART_NAMES = {'ru': ('Компас', 'Молекула', 'Кристалл'), 'en': ('Compass', 'Molecule', 'Crystal'), 'zh': ('罗盘', '分子', '晶体')}
def thin(svg):
    """The icon of a section in thinner lines on the cards of the home page (0.248.0; the panel keeps its own)."""
    return svg.replace('stroke-width="1.7"', 'stroke-width="1.15"')


# one line about each section on its card (0.248.0, the owner: «добавь какое-нибудь краткое описание каждого раздела»)
BRIEF = {
    'ru': {'atlas': 'Теория в интерактивных темах – на сайте', 'compass': 'Построить молекулу или кристалл',
           'sextant': 'Подготовить и запустить расчёт', 'spectrum': 'Разобрать результат расчёта'},
    'en': {'atlas': 'Theory in interactive topics – on the site', 'compass': 'Build a molecule or a crystal',
           'sextant': 'Prepare and run a calculation', 'spectrum': 'Read the result of a calculation'},
    'zh': {'atlas': '交互式主题中的理论——在网站上', 'compass': '构建分子或晶体',
           'sextant': '准备并运行计算', 'spectrum': '解读计算结果'},
}


HOME_TEXT = {  # + the cards of the molecule and of the crystal (the two parts of Compass)
    'ru': {'continue': 'Продолжить', 'molecule': 'Компас · Молекула', 'crystal': 'Компас · Кристалл'},
    'en': {'continue': 'Continue', 'molecule': 'Compass · Molecule', 'crystal': 'Compass · Crystal'},
    'zh': {'continue': '继续', 'molecule': '罗盘 · 分子', 'crystal': '罗盘 · 晶体'},
}


class _ArrowLeave(QObject):
    """The arrow lit by hand (property hot — while the panel of the recent ones holds the mouse) goes dark
    when the pointer leaves it."""

    def __init__(self, arrow):
        super().__init__(arrow)
        arrow.installEventFilter(self)

    def eventFilter(self, obj, event):
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.Type.Leave and obj.property('hot'):
            from PySide6.QtGui import QCursor

            if obj.rect().contains(obj.mapFromGlobal(QCursor.pos())):
                return False  # the panel took the mouse; the pointer is still over the arrow
            obj.setProperty('hot', False)
            obj.style().unpolish(obj)
            obj.style().polish(obj)
        return False


class RecentStack(QFrame):
    """The cards of the recent
    projects slide out from under the card of «Продолжить» one after another, each from under the ones before it, to
    their places in UNFOLD_MS, and slide back under it (the last first) before the panel closes."""

    UNFOLD_MS = 520  # each card eases in and out (smoothstep of its own share), one after another
    GAP = 6  # px between the cards
    TOP = 6  # px between the card of «Продолжить» and the first one

    def __init__(self, card, accent, back, line):
        super().__init__(card, Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        from PySide6.QtCore import QVariantAnimation

        self.arrow = getattr(card, 'more', None)  # it turns up while open, lit under the mouse as before
        self.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)  # a click on the arrow folds it, it does not open again
        self.setMouseTracking(True)

        self.setObjectName('recentPopup')
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(
            'QFrame#recentPopup {background: transparent;}'
            f'QFrame#recentRow {{background: {back}; border: 1px solid {line}; border-radius: 12px;}}'
            f'QFrame#recentRow:hover {{border-color: {accent};}}'
            'QLabel {background: transparent; border: none;}')
        self.rows = []
        self.shown = 0.0  # 0 — the stack, 1 — unfolded
        self._closing = False
        self.motion = QVariantAnimation(self)
        self.motion.valueChanged.connect(self._step)
        self.motion.finished.connect(self._moved)

    def _places(self):
        width = self.width()
        heights = [max(row.sizeHint().height(), 54) for row in self.rows]
        tops, y = [], self.TOP
        for h in heights:
            tops.append(y)
            y += h + self.GAP
        return width, heights, tops

    def _arrow(self, open_, hot=None):
        arrow = self.arrow
        if arrow is None:
            return
        try:
            arrow.setProperty('open', bool(open_))
            if hot is not None:
                arrow.setProperty('hot', bool(hot))
            arrow.style().unpolish(arrow)
            arrow.style().polish(arrow)
            turn = getattr(arrow, 'turn', None)
            if turn is not None:
                turn(bool(open_))
        except RuntimeError:
            pass

    def _over_arrow(self, global_pos):
        arrow = self.arrow
        # not hidden by the page (isVisible is False while the window itself is not shown, and the arrow would
        # never light)
        return arrow is not None and not arrow.isHidden() and arrow.rect().contains(arrow.mapFromGlobal(global_pos))

    def _follow_pointer(self):
        """The arrow lit while the pointer is over it, the panel open (also when the pointer was put there
        before it opened, or the system told nothing of it — the frames of the unfolding look again)."""
        arrow = self.arrow
        if arrow is None or self._closing:
            return
        from PySide6.QtGui import QCursor

        try:
            hot = self._over_arrow(QCursor.pos())
            if bool(arrow.property('hot')) != hot:
                self._arrow(True, hot)
        except RuntimeError:
            pass

    def mouseMoveEvent(self, event):
        # the pointer itself, not the position of the event: a move made by the system (a pointer put somewhere) came
        # with a position of the panel's own window that lit the arrow wrong
        if self._closing:
            self._arrow(False)
        else:
            self._follow_pointer()
        super().mouseMoveEvent(event)

    def open_under(self, card):
        from PySide6.QtCore import QEasingCurve

        self._arrow(True)
        width = max(card.width(), 280)
        self.setFixedWidth(width)
        _, heights, tops = self._places()
        self.setFixedHeight(tops[-1] + heights[-1] + 2)
        for row in reversed(self.rows):  # the first on top of the stack
            row.raise_()
        self.move(card.mapToGlobal(card.rect().bottomLeft()))  # its top edge — the lower edge of the card
        self._step(0.0)
        self.show()
        # the panel takes the mouse, the arrow is left — it stays lit while the pointer is over it
        from PySide6.QtGui import QCursor

        self._arrow(True, self._over_arrow(QCursor.pos()))
        self.motion.stop()
        self.motion.setDuration(self.UNFOLD_MS)
        self.motion.setEasingCurve(QEasingCurve.Type.Linear)
        self.motion.setStartValue(0.0)
        self.motion.setEndValue(1.0)
        self.motion.start()

    LAG = 0.6  # the next card starts when the one before has done this share of its way (0.35 until 2026-11-18)

    def _step(self, value):
        """The first card slides out from under the
        card of «Продолжить» (from above the edge of the panel, which stands at the lower edge of that card); every next
        one from under the one before it — it starts where that one is now, hidden behind it (that one is over it), and
        moves down by the distance between their places; they start one after another (LAG); folding is the same
        backwards — the last one goes back under the one before it first. Each share eased by itself (smoothstep)."""
        self.shown = float(value)
        self._follow_pointer()
        width, heights, tops = self._places()
        n = len(self.rows)
        span = 1 + self.LAG * (n - 1)
        above = None  # the place of the card before, now
        for k, (row, h, top) in enumerate(zip(self.rows, heights, tops)):
            share = min(1.0, max(0.0, self.shown * span - self.LAG * k)) if n > 1 else self.shown
            share = share * share * (3 - 2 * share)
            if above is None:
                y = -h + (top + h) * share  # out from under the card of «Продолжить»
            else:
                y = above + (top - tops[k - 1]) * share  # out from under the card before it
            above = y
            inset = (1 - share) * 8  # in the stack — a little narrower
            row.setGeometry(round(inset), round(y), round(width - 2 * inset), h)
            row.setVisible(y + h > 0)

    def _moved(self):
        if self._closing:
            self.close_now()

    def close_now(self):
        from PySide6.QtGui import QCursor

        self._closing = True
        self._arrow(False, self._over_arrow(QCursor.pos()))  # lit until the pointer leaves it (_ArrowLeave)
        self.motion.stop()
        super().close()
        self.deleteLater()

    def closeEvent(self, event):
        """A click beside it (the Popup closes itself) — the cards go back into the stack first."""
        if self._closing or self.shown <= 0.0:
            self._closing = True
            event.accept()
            return
        from PySide6.QtCore import QEasingCurve

        event.ignore()
        self._closing = True
        self._arrow(False)
        self.motion.stop()
        self.motion.setDuration(round(self.UNFOLD_MS * 0.8))
        self.motion.setEasingCurve(QEasingCurve.Type.Linear)
        self.motion.setStartValue(self.shown)
        self.motion.setEndValue(0.0)
        self.motion.start()


class HomeBackdrop(QWidget):
    """Background of the home page (the page colour; the scales come from the hub's Ornament)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.page = QColor('#f5f6f8')
        self.ink = QColor('#2a62b8')

    def set_colors(self, page, ink):
        self.page, self.ink = QColor(page), QColor(ink)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), self.page)  # the scales are drawn by the hub's Ornament
        painter.end()


class HomePage(QScrollArea):
    """Start page of the program: name and motto, what the program is, 'continue where you left off', four section
    blocks (no greeting of Quill)."""

    def __init__(self, sections, on_open, hub=None, parent=None):
        super().__init__(parent)
        self.setObjectName('home')
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.sections = sections
        self.on_open = on_open
        self.hub = hub
        self.language = 'ru'
        inner = HomeBackdrop()
        inner.setObjectName('homeInner')
        self.backdrop = inner
        self.setWidget(inner)
        outer = QHBoxLayout(inner)
        outer.setContentsMargins(32, 28, 32, 32)
        outer.addStretch(1)
        column = QWidget()
        column.setMaximumWidth(1000)
        column.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        outer.addWidget(column, 8)
        outer.addStretch(1)
        lay = QVBoxLayout(column)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(22)
        head = QHBoxLayout()
        head.setSpacing(16)
        self.app_icon = QLabel()
        head.addWidget(self.app_icon, 0, Qt.AlignmentFlag.AlignVCenter)
        names = QVBoxLayout()
        names.setSpacing(4)
        self.mark = QLabel()
        self.motto = QLabel()  # the motto as the program's tagline, under its name
        self.motto.setWordWrap(True)
        names.addWidget(self.mark)
        names.addSpacing(2)
        names.addWidget(self.motto)
        head.addLayout(names, 1)
        lay.addLayout(head)
        self.intro = QLabel()  # what the program is — under its name, where the greeting of Quill was
        self.intro.setWordWrap(True)
        lay.addWidget(self.intro)
        self.continue_title = QLabel()
        lay.addWidget(self.continue_title)
        self.continue_row = QHBoxLayout()
        self.continue_row.setSpacing(14)
        self.continue_cards = {}
        # no Atlas (the site keeps it); + crystal; no Spectrum; an arrow on the card — the last projects
        from PySide6.QtWidgets import QToolButton

        for kind in ('molecule', 'crystal'):
            card = SectionCard(kind, self._continue)
            card.setVisible(False)
            card.more = QToolButton(card)
            card.more.setObjectName('homeMore')
            card.more.setCursor(Qt.CursorShape.PointingHandCursor)
            card.more.setAutoRaise(True)
            # larger; up while the stack is open; lit under the mouse in both states
            card.more.setIconSize(QSize(26, 26))
            card.more.setFixedSize(40, 40)
            card.more.turn = lambda up, c=card: self._paint_arrow(c, up)
            card.more.leave = _ArrowLeave(card.more)
            card.more.clicked.connect(lambda checked=False, k=kind: self._choose_recent(k))
            card.layout().addWidget(card.more, 0, Qt.AlignmentFlag.AlignVCenter)
            self.continue_row.addWidget(card, 1)
            self.continue_cards[kind] = card
        self.continue_row.addStretch(0)
        lay.addLayout(self.continue_row)
        self.sections_title = QLabel()
        lay.addWidget(self.sections_title)
        grid = QGridLayout()
        grid.setSpacing(14)
        self.cards = {}
        # one card of Compass for its two parts (0.248.0); the other sections — their icon and name only
        # 0.248.2 (the owner chose: Compass the whole width on top, the other three in one row under it — cards of one
        # height): Compass alone in the first row over every column, the rest one to a column in the second
        shown = [ident for ident in sections if not (ident == 'crystal' and 'compass' in sections)]
        rest = [ident for ident in shown if ident != 'compass']
        columns = max(1, len(rest))
        for ident in shown:
            card = CompassCard(on_open) if ident == 'compass' and 'crystal' in sections else SectionCard(ident, on_open)
            card.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)  # the text never widens a
            # column
            if ident == 'compass':
                grid.addWidget(card, 0, 0, 1, columns)
            else:
                grid.addWidget(card, 1, rest.index(ident))
            self.cards[ident] = card
            if isinstance(card, CompassCard):
                self.cards['crystal'] = card.parts['crystal']
        for column in range(columns):  # columns of one width
            grid.setColumnStretch(column, 1)
        lay.addLayout(grid)
        self.note = QLabel()
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        lay.addStretch(1)
        self._colors = ('#1b2230', '#5b6474', '#2a62b8')
        self._face = ''

    # -- continue where you left off --------------------------------------------------------------
    def _continue(self, kind):
        if self.hub is not None:
            self.hub.continue_with(kind)

    def _paint_arrow(self, card, up):
        _, muted, _ = self._colors
        svg = _CHEVRON.replace('M6 9.5l6 6 6-6', 'M6 14.5l6-6 6 6') if up else _CHEVRON
        card.more.setIcon(QIcon(svg_pixmap(svg, muted, 26, self.devicePixelRatioF())))

    def recent_paths(self, kind):
        studio = getattr(self.hub, 'studio', None) if self.hub is not None else None
        return studio.recent_list(kind) if studio is not None and hasattr(studio, 'recent_list') else []

    def _choose_recent(self, kind):
        """The arrow of a card of «Продолжить» — the last projects of its part of Compass; each one a card as the card
        itself — the icon of the section, the date muted above, the name in bold; the cards come out of a stack under
        the card and go back into it (RecentStack)."""
        import datetime
        from pathlib import Path

        from azimuth.projects import display_name

        card = self.continue_cards[kind]
        ink, muted, accent = self._colors
        back, line = getattr(self, '_card', ('#ffffff', '#d8dce3'))
        ratio = self.devicePixelRatioF()
        popup = RecentStack(card, accent, back, line)
        ident = 'compass' if kind == 'molecule' else kind
        item = self.sections.get(ident) or self.sections.get('compass')
        icon = svg_pixmap(registry.icon_svg(item), accent, 22, ratio) if item is not None else None
        for path in self.recent_paths(kind):
            row = SectionCard(path, lambda p, k=kind: (popup.close_now(), self.hub.continue_with(k, p)), popup)
            row.setObjectName('recentRow')
            row.layout().setContentsMargins(12, 9, 12, 9)
            row.layout().setSpacing(12)
            row.icon.setFixedSize(26, 26)
            if icon is not None:
                row.icon.setPixmap(icon)
            try:
                stamp = datetime.datetime.fromtimestamp(Path(path).stat().st_mtime).strftime('%d.%m.%Y %H:%M')
            except OSError:
                stamp = ''
            row.title.setText(stamp)
            row.title.setStyleSheet(f'color: {muted}; font-size: 12px; font-weight: 500; {self._face}')
            row.text.setText(display_name(path))
            row.text.setStyleSheet(f'color: {ink}; font-size: 15px; font-weight: 600; {self._face}')
            row.setToolTip(path)
            popup.rows.append(row)
        self.recent_menu = popup
        if popup.rows:
            popup.open_under(card)
        return popup

    def _show_continue(self, ratio):
        ink, muted, accent = self._colors
        words = HOME_TEXT[self.language]
        hub = self.hub
        items = {}
        if hub is not None:
            # the card of the crystal with the icon of «Компас · Кристалл» (as its list of recent projects), not of the
            # molecule (the owner, 2026-11-23: «у компас кристалл в продолжить не та иконка»)
            for kind, ident in (('molecule', 'compass'), ('crystal', 'crystal' if 'crystal' in self.sections else 'compass')):
                # the newest of the list — not a draft of a file only looked at (recent_list)
                listed = hub.studio.recent_list(kind) if hasattr(hub.studio, 'recent_list') else []
                path = listed[0] if listed else None
                if path:
                    from azimuth.projects import display_name  # a project by its name, not project.qcc

                    title = words.get(kind) or hub.name(ident)  # «Компас · Молекула», «Компас · Кристалл»
                    items[kind] = (self.sections[ident], title, display_name(path))
        self.continue_title.setVisible(bool(items))
        self.continue_title.setText(words['continue'].upper())
        self.continue_title.setStyleSheet(
            f'color: {muted}; font-size: 13px; font-weight: 500; letter-spacing: 2px; {self._face}'
        )
        for kind, card in self.continue_cards.items():
            card.setVisible(kind in items)
            if kind not in items:
                continue
            item, title, detail = items[kind]
            card.icon.setPixmap(svg_pixmap(registry.icon_svg(item), accent, 28, ratio))
            card.title.setText(title)
            card.title.setStyleSheet(f'color: {muted}; font-size: 13px; font-weight: 500; {self._face}')
            card.text.setText(detail)
            card.text.setStyleSheet(f'color: {ink}; font-size: 16px; font-weight: 600; {self._face}')
            card.setToolTip(title + ': ' + detail)
            more = len(self.recent_paths(kind)) > 1  # the arrow when there is more than the last one
            card.more.setVisible(more)
            if more:
                self._paint_arrow(card, bool(card.more.property('open')))
                card.more.setToolTip({'ru': 'Другие недавние', 'en': 'Other recent ones', 'zh': '其他最近项目'}.get(
                    self.language, 'Другие недавние'))

    def show_texts(self, language, dark, family, icon):
        self.language = language
        ratio = self.devicePixelRatioF()
        ink, muted, accent, line, back = (
            ('#e7eaf0', '#9aa3b2', '#6ea2f0', '#2b333f', '#191f28')
            if dark
            else ('#1b2230', '#5b6474', '#2a62b8', '#d8dce3', '#ffffff')
        )
        page = '#11151c' if dark else '#f5f6f8'
        face = f"font-family: '{family}';" if family else ''
        self._colors, self._face = (ink, muted, accent), face
        self._card = (back, line)  # the list of the recent ones drawn as the cards
        self.backdrop.set_colors(page, accent)
        self.setStyleSheet(
            f'QScrollArea#home {{background: {page};}}'
            f'QFrame#card {{background: {back}; border: 1px solid {line}; border-radius: 12px;}}'
            f'QFrame#card:hover {{border-color: {accent};}}'
            f'QLabel {{color: {ink}; background: transparent; border: none;}}'
            f'QToolButton#homeMore {{background: transparent; border: none; border-radius: 10px;}}'
            f'QToolButton#homeMore:hover, QToolButton#homeMore[hot="true"] {{background: {line};}}'
        )
        words, text = PROGRAM[language], TEXT[language]
        # the glyph without the tile background (assets/app-icon[/dark]/glyph.svg): dark strokes
        # on the light page, light strokes on the dark one
        art = glyph_pixmap(dark, 64, ratio)
        self.app_icon.setPixmap(art if not art.isNull() else icon.pixmap(QSize(64, 64)))
        self.app_icon.setProperty('variant', 'dark' if dark else 'light')
        if language == 'zh':
            self.mark.setPixmap(zh_wordmark_pixmap(40, ratio, ink, accent, family))
        else:
            self.mark.setPixmap(wordmark_pixmap(language, 30, ratio, dark))
        self.mark.setAccessibleName(text['brand'])
        # tagline in the wordmark's face: Golos Text SemiBold, capitals, tracked like the name
        strict = motto_family() or family
        self.motto.setText(MOTTO[language].upper() if language != 'zh' else MOTTO[language])
        self.motto.setStyleSheet(f"color: {muted}; font-family: '{strict}'; font-size: 14px; font-weight: 600;")
        mfont = QFont(self.motto.font())
        mfont.setLetterSpacing(QFont.SpacingType.PercentageSpacing, 114)
        self.motto.setFont(mfont)
        self._show_continue(ratio)
        self.intro.setText(words['intro'])
        self.intro.setStyleSheet(f'font-size: 15px; {face}')
        self.sections_title.setText(words['sections_title'].upper())
        self.sections_title.setStyleSheet(
            f'color: {muted}; font-size: 13px; font-weight: 500; letter-spacing: 2px; {face}'
        )
        names = dict(zip(self.sections, (name for name, _ in words['sections'])))
        compass, molecule, crystal = PART_NAMES.get(language, PART_NAMES['ru'])
        for ident, card in self.cards.items():
            if ident == 'crystal' and isinstance(self.cards.get('compass'), CompassCard):
                continue  # a half of the card of Compass
            item = self.sections[ident]
            if isinstance(card, CompassCard):  # the compass and its name; the molecule and the crystal under the line
                card.icon.setPixmap(svg_pixmap(COMPASS_SVG, accent, 36, ratio))
                card.title.setText(compass)
                card.title.setStyleSheet(f'font-size: 18px; font-weight: 600; {face}')
                card.text.setText(BRIEF.get(language, BRIEF['ru'])['compass'])
                card.text.setStyleSheet(f'color: {muted}; font-size: 14px; {face}')
                card.setStyleSheet(f'QFrame#compassRule {{background: {line}; border: none;}}'
                                   f'QFrame#compassPart {{background: transparent; border: none; border-radius: 8px;}}'
                                   f'QFrame#compassPart:hover {{background: {line};}}')
                for kind, title in (('compass', molecule), ('crystal', crystal)):
                    part = card.parts[kind]
                    part.icon.setPixmap(svg_pixmap(PART_SVG[kind], accent, 26, ratio))
                    part.title.setText(title)
                    part.title.setStyleSheet(f'font-size: 15px; font-weight: 500; {face}')
                    part.setToolTip(names.get(kind, title))
                    part.setAccessibleName(names.get(kind, title))
                card.setToolTip(compass)
                card.setAccessibleName(compass)
                continue
            name = names.get(ident, '')
            card.icon.setPixmap(svg_pixmap(thin(registry.icon_svg(item)), accent, 36, ratio))
            card.title.setText(name)
            card.title.setStyleSheet(f'font-size: 18px; font-weight: 600; {face}')
            # 0.248.0: one line instead of the list of the functions (the owner: «убери подробную опись»; «добавь
            # какое-нибудь краткое описание каждого раздела»)
            card.text.setText(BRIEF.get(language, BRIEF['ru']).get(ident, ''))
            card.text.setStyleSheet(f'color: {muted}; font-size: 14px; {face}')
            card.layout().setAlignment(card.icon, Qt.AlignmentFlag.AlignVCenter)
            if not getattr(card, 'centred', False):  # the name and its line in the middle of the card, by the icon
                card.layout().itemAt(1).layout().insertStretch(0, 1)
                card.centred = True
            card.setToolTip(name)
            card.setAccessibleName(name)
        # the note on the calculation programs moved to Sextant, the author and the e-mail are in About
        self.note.setText('')
        self.note.hide()

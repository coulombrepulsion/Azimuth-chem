"""The long work of the program in the left panel of the hub: the turning compass while it runs, a mark when it ends.

HEADER
    a calculation of Sextant had an hourglass here while its window was hidden with «Скрыть». 2026-11-17
    one sign for all the
    long work put away (azimuth/activities.py — the calculation, the search of conformers): the compass of the program
    with its needle swinging (azimuth.controls.swing) and, when the share done is known, a ring of the progress around
    it; at the end a green tick, a red cross or a grey bar by it. Several at once — their number on the sign, a click
    gives the list. A click opens the window of the work without leaving the section; an end is forgotten once opened.
    Wilkinson convention, sections 1-8.
§2 ALGORITHM
    The board of the Studio (studio.activities, azimuth.activities.Board) tells the button after every change (sync):
    it is shown while the board has work put away; the timer (FRAME_MS) runs while any work runs. Sextant still calls
    job_listener(state, spent) — set_state — and its windows on_parked — set_parked: they are the activity
    «calculation» of the board.
§4 SPECIFICATION
    JobIndicator(studio: callable returning the Studio): .state (of the calculation), .parked; set_state(state,
    spent=''); set_parked(bool); board(); sync(board=None); text() -> the tooltip; label() -> the text of the button
    in the opened panel; open_window() (the calculation — its section shown); paint_icon(size, ratio)
    -> QPixmap (a calculation of Sextant alone
    — draw_sextant, the arm sweeping its scale (sight); other work — the compass; a calculation started
    in Compass — «Быстрый расчёт xtb», job.section 'compass' — the compass too).
    A work ended well and not yet opened — a thin gold ring round the disc (the next step, NEXT_GOLD).
§7 TEST CASES tests/hub/test_hub.py::test_calculation_indicator_in_the_panel, ::test_work_put_away_in_the_panel."""

from __future__ import annotations

from azimuth.ui import rounded  # menus with rounded corners
import time

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import QMenu, QPushButton

from azimuth.i18n import tr

FRAME_MS = 50
COLOURS = {'done': '#2e9e5b', 'failed': '#d04a3c', 'stopped': '#8a96a3'}
CALCULATION = 'calculation'  # the key of the calculation of Sextant on the board
# a little larger than the icons of the
# sections, on a disc of the accent that breathes, with a comet running round it (or the ring of the share done)
SIZE = 40  # was 28
PAD = 12 - (SIZE - 22) // 2  # the left padding: the centre of the icon as of the 22 px icons at 12 px
INNER = 0.68  # the compass or the sextant on its disc, a share of SIZE (was 0.64)
BREATH = 1.6  # s: the disc grows lighter and darker once
COMET = 1.1  # s: a turn of the comet when the share is not known
# a calculation of Sextant is a sextant whose index arm sweeps the scale, as one takes the height of a star; the star
# flashes when the arm comes to it
SIGHT = 2.6  # s: the arm there and back


def sight(seconds):
    """The share of the scale the index arm is at (0 — the near end, 1 — the far one), eased there and back, and how
    bright the star is (1 when the arm has come to its end, fading away)."""
    import math

    phase = (seconds % SIGHT) / SIGHT
    share = 0.5 - 0.5 * math.cos(2 * math.pi * phase)
    flash = max(0.0, 1.0 - abs(phase - 0.5) / 0.18)
    return share, flash


def draw_sextant(p, side, seconds, dark, running=True):
    """A sextant in a square of side px (the icon of the section, assets/navigation/sextant.svg, drawn by hand): the
    frame from the pivot, the arc of the scale with its marks, the index arm (moving while running) and the star."""
    import math

    from hub.branding import BROWN

    unit = side / 24.0
    ink = QColor('#c9d3e0' if dark else '#344354')
    brown = QColor(BROWN[1] if dark else BROWN[0])
    accent = QColor('#6ea2f0' if dark else '#2a62b8')
    cx, cy, radius = 7.0, 4.0, 16.0
    low, high = 30.0, 100.0  # the arc: degrees from the right, clockwise on the screen

    def at(angle, r=radius):
        a = math.radians(angle)
        return QPointF((cx + r * math.cos(a)) * unit, (cy + r * math.sin(a)) * unit)

    width = max(1.0, 1.5 * unit)
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.setPen(QPen(ink, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    arc = QPainterPath(at(low))
    for k in range(1, 21):
        arc.lineTo(at(low + (high - low) * k / 20))
    p.drawPath(arc)
    p.drawLine(QPointF(cx * unit, cy * unit), at(low))
    p.drawLine(QPointF(cx * unit, cy * unit), at(high))
    p.setPen(QPen(brown, max(0.8, 1.1 * unit), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for k in range(1, 7):  # the marks of the scale
        angle = low + (high - low) * k / 7
        p.drawLine(at(angle, radius - 2.4), at(angle, radius - 0.6))
    share, flash = sight(seconds) if running else (0.35, 0.0)
    arm = high - (high - low) * (0.12 + 0.76 * share)  # from near the lower end up towards the star
    p.setPen(QPen(accent, max(1.2, 1.9 * unit), Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    p.drawLine(QPointF(cx * unit, cy * unit), at(arm, radius + 1.2))
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(accent)
    p.drawEllipse(QPointF(cx * unit, cy * unit), 1.8 * unit, 1.8 * unit)
    # the star sighted: up to the right of the frame, brighter as the arm comes to it
    star = QColor(BROWN[1] if dark else '#d9a441')
    star.setAlphaF(0.45 + 0.55 * flash)
    sx, sy, r1 = 20.0 * unit, 4.0 * unit, (2.6 + 1.6 * flash) * unit
    r2 = r1 * 0.32
    shape = QPainterPath()
    for k in range(8):
        r = r1 if k % 2 == 0 else r2
        a = math.radians(45 * k)
        point = QPointF(sx + r * math.sin(a), sy - r * math.cos(a))
        shape.moveTo(point) if k == 0 else shape.lineTo(point)
    shape.closeSubpath()
    p.setBrush(star)
    p.drawPath(shape)


class JobIndicator(QPushButton):
    def __init__(self, studio, parent=None):
        super().__init__(parent)
        self.studio = studio
        self.state = None
        self.spent = ''
        self.collapsed = True
        self.parked = False  # the window of the calculation is hidden with «Скрыть»
        self._own = None  # a board of its own when the Studio has none
        self._told = 0.0  # when the tooltip got its time last
        self.setObjectName('nav')
        self.setIconSize(QSize(SIZE, SIZE))
        # the icon of SIZE px, wider than the
        # 22 px of the other buttons of the panel (padding 12 px) — its padding less by half the difference, the
        # centres in one column
        self.setStyleSheet(f'QPushButton#nav {{padding-left: {PAD}px;}}')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.timer = QTimer(self)
        self.timer.setInterval(FRAME_MS)
        self.timer.timeout.connect(self.tick)
        self.clicked.connect(self.open_window)
        self.hide()

    # -- the board ----------------------------------------------------------------------------------------------
    def board(self):
        studio = self.studio()
        board = getattr(studio, 'activities', None) if studio is not None else None
        if board is None:
            if self._own is None:
                from azimuth.activities import Board

                self._own = Board()
            board = self._own
        if self.sync not in board.listeners:
            board.listen(self.sync)
        return board

    def shown(self):
        return self.board().shown()

    def sync(self, board=None):
        board = board or self.board()
        if board.running():
            if not self.timer.isActive():
                self.timer.start()
        else:
            self.timer.stop()
        self.setVisible(bool(board.shown()))
        self.refresh()

    # -- the calculation of Sextant (job_listener, on_parked) ---------------------------------------------------
    def _open_job(self):
        """The section of the calculation is shown — Sextant (its card of the calculation in the place of the input
        file), or Compass for its quick xtb — not a window over another one."""
        studio = self.studio()
        if studio is None:
            return
        section = 'compass' if getattr(getattr(studio, 'job', None), 'section', '') == 'compass' else 'sextant'
        hub = self.window()
        if hasattr(hub, 'show_section'):
            hub.show_section(section)
        if section == 'sextant' and hasattr(studio, 'show_job_window'):
            studio.show_job_window()

    def set_state(self, state, spent=''):
        self.state = state
        self.spent = spent
        board = self.board()
        if state is None:
            board.remove(CALCULATION)
        elif state == 'running':
            board.start(CALCULATION, tr('Расчёт'), self._open_job, parked=self.parked)
        else:
            if board.get(CALCULATION) is None:
                board.start(CALCULATION, tr('Расчёт'), self._open_job, parked=self.parked)
            board.finish(CALCULATION, state, spent)
        self.sync(board)

    def set_parked(self, parked):
        self.parked = bool(parked)
        board = self.board()
        board.park(CALCULATION, self.parked)
        self.sync(board)

    # -- words --------------------------------------------------------------------------------------------------
    def elapsed(self, item=None):
        if item is not None and item.key != CALCULATION:
            return time.monotonic() - item.started
        studio = self.studio()
        job = getattr(studio, 'job', None) if studio is not None else None
        try:
            return job.elapsed() if job is not None else time.monotonic() - (item.started if item else time.monotonic())
        except Exception:  # noqa: BLE001 — the time of the board itself
            return time.monotonic() - (item.started if item else time.monotonic())

    def _one_text(self, item):
        from modules.sextant.runner import duration

        if item.key == CALCULATION:
            if item.state == 'running':
                return tr('Идёт расчёт · ') + duration(self.elapsed(item)) + tr(' · нажмите — к расчёту')
            if item.state == 'done':
                return tr('Расчёт окончен') + (f' · {item.spent}' if item.spent else '') + tr(' · нажмите — к расчёту')
            if item.state == 'failed':
                return tr('Расчёт завершился с ошибкой · нажмите — к расчёту')
            return tr('Расчёт остановлен · нажмите — к расчёту')
        share = f' · {item.done}/{item.total}' if item.total and item.done is not None else ''
        if item.state == 'running':
            return item.title + share + ' · ' + duration(self.elapsed(item)) + tr(' · нажмите — открыть')
        ends = {'done': tr('окончен'), 'failed': tr('ошибка'), 'stopped': tr('остановлен')}
        return item.title + ' · ' + ends.get(item.state, '') + (f' · {item.note}' if item.note else '') + tr(
            ' · нажмите — открыть')

    def text(self):
        shown = self.shown()
        if not shown:
            return ''
        if len(shown) == 1:
            return self._one_text(shown[0])
        return '\n'.join(self._one_text(item) for item in shown)

    def label(self):
        shown = self.shown()
        if not shown:
            return ''
        if len(shown) > 1:
            return tr('Фоновых работ: {}').format(len(shown))
        item = shown[0]
        if item.key == CALCULATION:
            return {'running': tr('Идёт расчёт'), 'done': tr('Расчёт окончен'), 'failed': tr('Ошибка расчёта'),
                    'stopped': tr('Расчёт остановлен')}.get(item.state, '')
        if item.state == 'running' and item.total and item.done is not None:
            return f'{item.title} {item.done}/{item.total}'
        return item.title

    def set_collapsed(self, collapsed):
        self.collapsed = bool(collapsed)
        self.refresh()

    def refresh(self):
        self.setToolTip(self.text())
        self.setAccessibleName(self.label())
        self.setText('' if self.collapsed else self.label())
        self.setIcon(QIcon(self.paint_icon(SIZE, self.devicePixelRatioF())))

    def tick(self):
        if not self.isVisible():
            return
        self.setIcon(QIcon(self.paint_icon(SIZE, self.devicePixelRatioF())))
        now = time.monotonic()
        if now - self._told >= 1.0:  # the time in the tooltip, once a second
            self._told = now
            self.setToolTip(self.text())
            if not self.collapsed:
                self.setText(self.label())

    def _open(self, item):
        board = self.board()
        if item.open is not None:
            item.open()
        elif item.section:  # a work of run_waiting — back to the section it goes on in
            hub = self.window()
            if hasattr(hub, 'show_section'):
                hub.show_section(item.section)
        if item.state != 'running':
            board.seen(item.key)  # seen: the mark goes away
            if item.key == CALCULATION:
                self.state = None
        self.sync(board)

    def open_window(self):
        shown = self.shown()
        if len(shown) == 1:
            return self._open(shown[0])
        if len(shown) > 1:  # several at once: the list
            menu = rounded(QMenu(self))  # rounded corners
            for item in shown:
                action = menu.addAction(self.label_of(item))
                action.triggered.connect(lambda checked=False, item=item: self._open(item))
            self.menu = menu
            menu.popup(self.mapToGlobal(self.rect().topRight()))
        return None

    def label_of(self, item):
        share = f' {item.done}/{item.total}' if item.total and item.done is not None and item.state == 'running' else ''
        mark = {'done': ' ✓', 'failed': ' ✕', 'stopped': ' —'}.get(item.state, '')
        return item.title + share + mark

    # -- drawing ------------------------------------------------------------------------------------------------
    def paint_icon(self, size=22, ratio=1.0):
        """The compass of the program (its needle swinging while work runs), the ring of the share done around it,
        the mark of an end; with several works their number."""
        from azimuth.controls import draw_compass, swing

        shown = self.shown() if self.studio is not None else []
        item = shown[0] if len(shown) == 1 else None
        running = any(i.state == 'running' for i in shown)
        state = item.state if item is not None else ('running' if running else (shown[0].state if shown else None))
        self.state_drawn = state
        pixmap = QPixmap(round(size * ratio), round(size * ratio))
        pixmap.setDevicePixelRatio(ratio)
        pixmap.fill(Qt.GlobalColor.transparent)
        p = QPainter(pixmap)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        import math

        dark = self.palette().buttonText().color().lightness() > 128  # light words: a dark panel
        now = time.monotonic()
        started = min((i.started for i in shown), default=now)
        angle = swing(now - started) if running else 0.0
        accent = QColor('#6ea2f0' if dark else '#2a62b8')
        # the disc of the accent behind the compass — it breathes while work runs, stays when it waits to be seen
        breath = 0.5 - 0.5 * math.cos(2 * math.pi * ((now - started) % BREATH) / BREATH) if running else 1.0
        disc = QColor(accent)
        disc.setAlpha(round(40 + 50 * breath))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(disc)
        ring = size * 0.075  # the width of the ring of the share done and of the comet
        edge = ring / 2 + 0.6  # the ring inside the picture (a wider one was cut at its edge)
        p.drawEllipse(QRectF(edge + ring, edge + ring, size - 2 * (edge + ring), size - 2 * (edge + ring)))
        inner = size * INNER
        p.save()
        p.translate((size - inner) / 2, (size - inner) / 2)
        studio = self.studio() if self.studio is not None else None
        from_compass = getattr(getattr(studio, 'job', None), 'section', '') == 'compass'  # quick xtb
        self.sextant_drawn = bool(shown) and all(i.key == CALCULATION for i in shown) and not from_compass
        # a work of another section (run_waiting) — the sign of its section
        own = item.section if item is not None and item.key != CALCULATION else ''
        self.section_drawn = own or ('sextant' if self.sextant_drawn else 'compass')
        if self.sextant_drawn or own == 'sextant':  # Sextant — the sextant taking the height of its star
            draw_sextant(p, inner, now - started, dark, running)
        elif own == 'spectrum':
            from modules.spectrum.views.spectrum_pulse import draw_pulse

            axis = QColor(self.palette().buttonText().color())
            axis.setAlpha(120)
            draw_pulse(p, QRectF(0, inner * 0.18, inner, inner * 0.64), now - started, dark, axis)
        else:
            draw_compass(p, inner, inner, angle, dark)
        p.restore()
        share = item.fraction() if item is not None else None
        rect = QRectF(edge, edge, size - 2 * edge, size - 2 * edge)
        p.setBrush(Qt.BrushStyle.NoBrush)
        if share is not None:  # the ring of the share done
            faint = QColor(accent)
            faint.setAlpha(70)
            p.setPen(QPen(faint, size * 0.065))
            p.drawEllipse(rect)
            p.setPen(QPen(accent, ring, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawArc(rect, 90 * 16, -round(360 * 16 * share))
        elif running:  # the share not known: a comet runs round the disc
            head = 90.0 - 360.0 * ((now - started) % COMET) / COMET
            for k in range(6):  # a tail fading behind the head
                tail = QColor(accent)
                tail.setAlpha(round(255 * (1 - k / 6)))
                p.setPen(QPen(tail, ring, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
                p.drawArc(rect, round((head + 14 * k) * 16), round(14 * 16))
        elif state == 'done':
            # a work ended well
            # waits to be opened — the next step: the gold ring of the icons round the disc
            from hub.branding import NEXT_GOLD

            p.setPen(QPen(QColor(NEXT_GOLD['dark' if dark else 'light']), ring * 0.6))  # thinner, lighter
            p.drawEllipse(rect)
        if len(shown) > 1:  # the number of the works
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#2a62b8'))
            r = size * 0.24
            centre = QPointF(size * 0.76, size * 0.24)
            p.drawEllipse(centre, r, r)
            font = QFont(self.font())
            font.setPixelSize(max(7, round(size * 0.32)))
            font.setBold(True)
            p.setFont(font)
            p.setPen(QColor('#ffffff'))
            p.drawText(QRectF(centre.x() - r, centre.y() - r, 2 * r, 2 * r), Qt.AlignmentFlag.AlignCenter, str(len(shown)))
        colour = COLOURS.get(state) if len(shown) <= 1 else None
        if colour is not None:  # the mark of the end next to the glass
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(colour))
            # a smaller mark in the corner
            r = size * 0.17
            centre = QPointF(size * 0.80, size * 0.78)
            p.drawEllipse(centre, r, r)
            p.setPen(QPen(QColor('#ffffff'), 1.3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
            if state == 'done':
                tick = QPainterPath()
                tick.moveTo(centre.x() - r * 0.5, centre.y())
                tick.lineTo(centre.x() - r * 0.1, centre.y() + r * 0.4)
                tick.lineTo(centre.x() + r * 0.55, centre.y() - r * 0.4)
                p.drawPath(tick)
            elif state == 'failed':
                d = r * 0.42
                p.drawLine(QPointF(centre.x() - d, centre.y() - d), QPointF(centre.x() + d, centre.y() + d))
                p.drawLine(QPointF(centre.x() - d, centre.y() + d), QPointF(centre.x() + d, centre.y() - d))
            else:
                p.drawLine(QPointF(centre.x() - r * 0.45, centre.y()), QPointF(centre.x() + r * 0.45, centre.y()))
        p.end()
        return pixmap

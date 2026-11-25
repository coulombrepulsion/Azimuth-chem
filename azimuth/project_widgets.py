"""The pieces of the project list and its tabs (azimuth/project_navigation.py builds them into the window): the row of
the project tabs and their «+», the table of the molecules with its columns, the sliding of the panel and its log.

§1 PURPOSE
    The widgets and the helpers that hold no state of the window, apart from the mixins of ProjectNavigation, so that a
    section (Compass slides its panels the same way) imports them without the whole navigation.
§2 RULES
    1. Nothing here reads or changes a project: the window passes what a widget shows.
    2. AZIMUTH_SLIDE_LOG=<file> writes every step of a sliding panel there (slide_log_step, slide_profile_*).
§7 TESTS tests/projects/test_project_navigation.py.
"""

from azimuth.i18n import tr


SUBSCRIPT = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


# px between the card of the list and the page beside it; no margin above and below —
# the card is as tall as the page, the row of the project tabs lies on its top edge as on that of the page
GAP = 12



NEW_ROW = '+new'  # the row of «Новая молекула» of a project (no id of a molecule)

SLIDE_LOG = 'AZIMUTH_SLIDE_LOG'  # a file — every step of a sliding panel written there (its width, its time)


def slide_log_start():
    import os
    from time import perf_counter

    return perf_counter() if os.environ.get(SLIDE_LOG) else None


def slide_log_step(started, width):
    """To find what makes a sliding panel shake with the
    environment variable AZIMUTH_SLIDE_LOG=<file> every step adds «time since the last step, its work, the width»."""
    if started is None:
        return
    import os
    from time import perf_counter

    now = perf_counter()
    last = getattr(slide_log_step, 'last', None)
    gap = (started - last) * 1000 if last is not None and started - last < 1 else 0.0
    slide_log_step.last = now
    try:
        with open(os.environ[SLIDE_LOG], 'a', encoding='utf-8') as out:
            out.write(f'{gap:7.1f} ms  {1000 * (now - started):6.1f} ms  {width}\n')
    except OSError:
        pass


def _slide_note(text):
    import os

    try:
        with open(os.environ[SLIDE_LOG], 'a', encoding='utf-8') as out:
            out.write(text if text.endswith('\n') else text + '\n')
    except (OSError, KeyError):
        pass


def slide_profile_begin():
    """With AZIMUTH_SLIDE_LOG, the widgets painted during a slide (their paint events counted by class) and,
    when it can be had, the Python time of it (cProfile) — written to the log by slide_profile_end."""
    import os

    if not os.environ.get(SLIDE_LOG):
        return None
    try:
        from collections import Counter

        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QApplication

        class Painted(QObject):
            def __init__(self):
                super().__init__()
                self.count = Counter()

            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Paint:
                    self.count[type(obj).__name__ + ('#' + obj.objectName() if obj.objectName() else '')] += 1
                return False

        painted = Painted()
        QApplication.instance().installEventFilter(painted)
        profile = None
        try:
            import cProfile

            profile = cProfile.Profile()
            profile.enable()
        except Exception as exc:  # noqa: BLE001 — another profiler on: the paint events only
            _slide_note(f'(no Python profile: {exc!r})')
            profile = None
        return profile, painted
    except Exception as exc:  # noqa: BLE001
        _slide_note(f'(no profile: {exc!r})')
        return None


def slide_profile_end(handle, label):
    if handle is None:
        return
    try:
        import io
        import pstats

        from PySide6.QtWidgets import QApplication

        profile, painted = handle
        if profile is not None:
            profile.disable()
        QApplication.instance().removeEventFilter(painted)
        out = [f'=== {label}: paint events']
        out += [f'{count:6d}  {name}' for name, count in painted.count.most_common(30)]
        if profile is not None:
            text = io.StringIO()
            pstats.Stats(profile, stream=text).sort_stats('tottime').print_stats(25)
            lines = [ln for ln in text.getvalue().splitlines() if ln.strip()]
            out += [f'=== {label}: Python time'] + lines[:45]
        _slide_note('\n'.join(out))
    except Exception as exc:  # noqa: BLE001
        _slide_note(f'(profile not written: {exc!r})')


def even_step(value):
    """The width of a sliding panel in even pixels — what stands in the middle of the field beside it moves by half the
    step, and an odd step was rounded now down, now up (a pixel, none, a pixel…); with even steps it moves by whole
    pixels."""
    return int(round(float(value) / 2.0)) * 2


def slide_box(child):
    """A box whose width goes from 0 to that of child — the child keeps
    its width and stands at the right edge of the box, so it comes out from the left edge of the window as the drawer
    of Compass does, and the field beside it gives way at the same pace (no squeezed table while it moves)."""
    from PySide6.QtWidgets import QWidget

    class SlideBox(QWidget):
        def resizeEvent(self, event):
            super().resizeEvent(event)
            child.setGeometry(self.width() - child.width() - GAP, 0, child.width(), self.height())

    box = SlideBox()
    child.setParent(box)
    box.setFixedWidth(0)
    box.hide()
    return box


class PlusDrops:
    """«+» of the projects takes the rows of the list of molecules dropped on it (made — a new project of
    them; ⌥ / Alt — copied). An event filter of the button: lit while they are over it."""

    def __new__(cls, plus, table, made):
        from PySide6.QtCore import QEvent, QObject, Qt, QTimer

        class Filter(QObject):
            def light(self, on):
                # a frame of the
                # accent, as round the tab that takes them (ProjectTabBar)
                dark = plus.palette().window().color().lightness() < 128
                accent = '#6ea2f0' if dark else '#2a62b8'
                plus.setStyleSheet(f'QPushButton {{border: 2px solid {accent}; border-radius: 6px;}}' if on else '')
                plus.setProperty('dropLit', bool(on))

            def eventFilter(self, watched, event):
                kind = event.type()
                if kind in (QEvent.Type.DragEnter, QEvent.Type.DragMove):
                    if event.source() is table():
                        event.setDropAction(Qt.DropAction.MoveAction if getattr(table(), 'carrying', False)
                                            else Qt.DropAction.IgnoreAction)
                        event.accept()
                        self.light(True)
                        return True
                    return False
                if kind == QEvent.Type.DragLeave:
                    self.light(False)
                    return False
                if kind == QEvent.Type.Drop:
                    self.light(False)
                    if event.source() is not table():
                        return False
                    copy = bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)
                    # the list itself removes nothing (see MoleculeTable.carrying)
                    event.setDropAction(Qt.DropAction.MoveAction if getattr(table(), 'carrying', False)
                                        else Qt.DropAction.IgnoreAction)
                    event.accept()
                    QTimer.singleShot(0, lambda: made(copy))
                    return True
                return False

        return Filter(plus)


def project_tab_bar():
    """The tabs of the projects
    take the rows of the list of molecules dragged onto a tab — on_molecules_dropped(index of the tab, copy) (copy: ⌥ /
    Alt held, else they move); the tab under the cursor framed while they are carried, and only a tab that may take them
    (accepts(index))."""
    from PySide6.QtCore import QRect, Qt
    from PySide6.QtGui import QColor, QPainter, QPen
    from PySide6.QtWidgets import QTabBar

    class ProjectTabBar(QTabBar):
        on_molecules_dropped = None
        accepts = None
        source = None  # the list of the molecules: only its rows are taken

        def __init__(self):
            super().__init__()
            self.setAcceptDrops(True)
            self.drop_target = -1

        def _target(self, event):
            if self.source is None or event.source() is not self.source:
                return -1
            index = self.tabAt(event.position().toPoint())
            if index < 0 or (self.accepts is not None and not self.accepts(index)):
                return -1
            return index

        def _copy(self, event):
            return bool(event.modifiers() & Qt.KeyboardModifier.AltModifier)

        def dragEnterEvent(self, event):
            if self.source is not None and event.source() is self.source:
                event.acceptProposedAction()
                return
            super().dragEnterEvent(event)

        def dragMoveEvent(self, event):
            index = self._target(event)
            if index != self.drop_target:
                self.drop_target = index
                self.update()
            if index >= 0:
                # the list offers only a move (InternalMove): the copy is told by ⌥ / Alt at the drop, not by the action
                event.setDropAction(Qt.DropAction.MoveAction)
                event.accept()
            else:
                event.ignore()

        def dragLeaveEvent(self, event):
            self.drop_target = -1
            self.update()
            super().dragLeaveEvent(event)

        def dropEvent(self, event):
            from PySide6.QtCore import QTimer

            index = self._target(event)
            self.drop_target = -1
            self.update()
            if index < 0:
                event.ignore()
                return
            copy = self._copy(event)
            # the list itself removes nothing: the window moves the molecules between the projects (a drag of several
            # rows takes the drop — see MoleculeTable.carrying)
            event.setDropAction(Qt.DropAction.MoveAction if getattr(self.source, 'carrying', False)
                                else Qt.DropAction.IgnoreAction)
            event.accept()
            dropped = self.on_molecules_dropped
            if dropped is not None:
                QTimer.singleShot(0, lambda: dropped(index, copy))

        def paintEvent(self, event):
            super().paintEvent(event)
            if 0 <= self.drop_target < self.count():
                p = QPainter(self)
                p.setRenderHint(QPainter.RenderHint.Antialiasing)
                accent = QColor('#6ea2f0' if self.palette().window().color().lightness() < 128 else '#2a62b8')
                p.setPen(QPen(accent, 2))
                rect = QRect(self.tabRect(self.drop_target)).adjusted(1, 1, -1, -1)
                p.drawRoundedRect(rect, 6, 6)
                p.end()

    return ProjectTabBar()


def flight(host, items, duration, easing=None):
    """Pictures carried over the window in one layer of its own — items [(picture,
    start, end)], points of host; the first picture on top, the others under it in their order. One widget paints them
    all and asks only the places they leave and take to be drawn again (a label for each made the window repaint them
    one by one). Returns (the layer, the animation of 0 → 1); the layer goes when the animation ends."""
    from PySide6.QtCore import QEasingCurve, QPointF, QRect, Qt, QVariantAnimation
    from PySide6.QtGui import QPainter
    from PySide6.QtWidgets import QWidget

    class Layer(QWidget):
        def __init__(self):
            super().__init__(host)
            self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            self.setGeometry(host.rect())
            self.items = items
            self.share = 0.0
            self.shown = self.places(0.0)

        def places(self, share):
            rects = []
            for picture, start, end in self.items:
                end = end() if callable(end) else end  # a point that moves (the cursor)
                x = start.x() + (end.x() - start.x()) * share
                y = start.y() + (end.y() - start.y()) * share
                size = picture.size() / picture.devicePixelRatio()
                rects.append(QRect(round(x), round(y), size.width(), size.height()))
            return rects

        def step(self, share):
            self.share = float(share)
            now = self.places(self.share)
            dirty = QRect()
            for rect in self.shown + now:
                dirty = dirty.united(rect)
            self.shown = now
            self.update(dirty.adjusted(-2, -2, 2, 2))

        def paintEvent(self, event):
            p = QPainter(self)
            for (picture, _, _), rect in reversed(list(zip(self.items, self.shown))):  # the first one drawn last: on top
                p.drawPixmap(QPointF(rect.topLeft()), picture)
            p.end()

    layer = Layer()
    motion = QVariantAnimation(layer)
    motion.setDuration(duration)
    motion.setStartValue(0.0)
    motion.setEndValue(1.0)
    motion.setEasingCurve(easing if easing is not None else QEasingCurve.Type.InOutCubic)
    motion.valueChanged.connect(layer.step)
    motion.finished.connect(layer.deleteLater)
    layer.show()
    layer.raise_()
    return layer, motion


# the columns of the list of the molecules of a project — (key, head, shown at first); «№» and «Название»
# are always shown, the others are chosen in the menu of the head (kept in the preference COLUMNS_KEY)
COLUMNS = (
    ('number', '№', True),
    ('name', 'Название', True),
    ('formula', 'Формула', True),
    ('method', 'Метод', True),
    ('energy', 'Энергия, Eh', False),
    ('atoms', 'Атомов', False),
    ('charge', 'Заряд, мульт.', False),
    ('attempts', 'Расчётов', False),
    ('state', 'Последний расчёт', False),
)
FIXED_COLUMNS = ('number', 'name')
COLUMNS_KEY = 'project_list_columns'
COLUMN_TIPS = {
    'method': 'Метод текущего расчёта молекулы (того, чей результат показан)',
    'energy': 'Энергия текущего расчёта, в хартри',
    'charge': 'Заряд и мультиплетность молекулы',
    'attempts': 'Сколько раз молекулу считали',
    'state': 'Состояние последнего расчёта молекулы',
}


def column_cells(project, entry, molecule, calc):
    """The texts of the columns after «Формула» (COLUMNS[3:]) for a molecule of a project."""
    from azimuth.project_view import method_of
    from modules.sextant.batch import STATE_NAMES

    attempts = entry.get('attempts', [])
    current = project.current(entry)
    method = ''
    energy = ''
    if current is not None:
        kind = str(current.get('kind', '')).upper()
        method = method_of(current) if kind in ('XTB', 'MOPAC') else kind + ' · ' + method_of(current)
        value = current.get('energy')
        if isinstance(value, (int, float)):
            energy = f'{value:.6f}'
    last = attempts[-1] if attempts else None
    state = tr(STATE_NAMES.get(last.get('state'), last.get('state') or '')) if last else ''
    charge = f'{calc.charge:+d}'.replace('+0', '0') + f', {calc.multiplicity}' if molecule.atoms else ''
    return (method, energy, str(len(molecule.atoms)) if molecule.atoms else '', charge,
            str(len(attempts)) if attempts else '', state)


EMPTY_CELLS = ('',) * (len(COLUMNS) - 3)


def molecule_table():
    """The list of the molecules of the project drawn as the page «Структуры» of the drawer of Compass was —
    №, Структура, Формула (subscripts), no frame and no grid, alternating rows; several rows can be chosen."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QAbstractItemView, QFrame, QHeaderView, QTableWidget

    class MoleculeTable(QTableWidget):
        on_rows_moved = None  # (rows dragged, the row they go before) — the window reorders the project

        def viewportEvent(self, event):
            """The whole text of a cell cut to «…»; a
            cell that fits shows its own tooltip only (the ≠ of a result of other data)."""
            from PySide6.QtCore import QEvent
            from PySide6.QtWidgets import QToolTip

            if event.type() != QEvent.Type.ToolTip:
                return super().viewportEvent(event)
            point = event.pos()
            item = self.itemAt(point)
            if item is None:
                QToolTip.hideText()
                event.ignore()
                return True
            text = item.text().strip()
            room = self.columnWidth(item.column()) - 18  # the padding of a cell (8 px each side, app.py)
            cut = bool(text) and self.fontMetrics().horizontalAdvance(item.text()) > room
            tip = '\n'.join(t for t in ((text if cut else ''), item.toolTip()) if t)
            if tip:
                QToolTip.showText(event.globalPos(), tip, self.viewport(), self.visualItemRect(item))
            else:
                QToolTip.hideText()
                event.ignore()
            return True

        def count(self):  # the interface of the QListWidget it replaced
            return self.rowCount()

        def setCurrentRow(self, row):
            self.setCurrentCell(row, 0)

        # several rows carried — their pictures fly from their places to the cursor and fade, and the
        # cursor carries a pile of them with their number
        GATHER_MS = 220
        PILE = 3  # rows drawn in the pile

        carrying = False  # a drag of several rows of startDrag runs — its drop is taken (MoveAction)

        def ground(self):
            """An opaque colour under the rows: the list is drawn on the ground of its panel (transparent itself)."""
            from PySide6.QtGui import QColor

            colour = QColor(self.window().palette().window().color())
            colour.setAlpha(255)
            return colour

        def row_picture(self, row):
            """The row as it is drawn, on an opaque ground."""
            from PySide6.QtGui import QPainter, QPixmap

            rect = self.visualRect(self.model().index(row, 0))
            right = self.visualRect(self.model().index(row, self.columnCount() - 1))
            rect = rect.united(right)
            grabbed = self.viewport().grab(rect)
            picture = QPixmap(grabbed.size())
            picture.setDevicePixelRatio(grabbed.devicePixelRatio())
            picture.fill(self.ground())
            p = QPainter(picture)
            p.drawPixmap(0, 0, grabbed)
            p.end()
            return picture, rect

        def pile_picture(self, pictures, count):
            from PySide6.QtCore import QRectF
            from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPixmap

            shown = pictures[:self.PILE]
            width = max(round(p.width() / p.devicePixelRatio()) for p in shown)  # logical pixels (Retina: halves)
            height = max(round(p.height() / p.devicePixelRatio()) for p in shown)
            step = 5
            ratio = self.devicePixelRatioF()
            side = (width + step * (len(shown) - 1) + 14, height + step * (len(shown) - 1) + 14)
            pile = QPixmap(round(side[0] * ratio), round(side[1] * ratio))
            pile.setDevicePixelRatio(ratio)
            pile.fill(Qt.GlobalColor.transparent)
            p = QPainter(pile)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            dark = self.ground().lightness() < 128
            for k in reversed(range(len(shown))):  # the last one at the bottom, the first on top
                x, y = step * k, step * k
                card = QRectF(x + 0.5, y + 0.5, width, height)
                p.setPen(QPen(QColor('#3a4452' if dark else '#d8dce3'), 1))
                p.setBrush(self.ground())  # opaque (the base of the list is transparent)
                p.drawRoundedRect(card, 6, 6)
                if k == 0:
                    p.drawPixmap(int(x), int(y), shown[0])
            if count > 1:  # the number of the molecules carried
                r = 10
                centre = (side[0] - r - 1, r + 1)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor('#2a62b8'))
                p.drawEllipse(QRectF(centre[0] - r, centre[1] - r, 2 * r, 2 * r))
                font = QFont(self.font())
                font.setPixelSize(11)
                font.setBold(True)
                p.setFont(font)
                p.setPen(QColor('#ffffff'))
                p.drawText(QRectF(centre[0] - r, centre[1] - r, 2 * r, 2 * r), Qt.AlignmentFlag.AlignCenter, str(count))
            p.end()
            return pile

        def _heights(self, group, rows, grow):
            """The rows close to nothing (they left for the pile) or open again (laid back), with the flight."""
            from PySide6.QtCore import QVariantAnimation

            header = self.verticalHeader()
            full = header.defaultSectionSize()
            motion = QVariantAnimation(group)
            motion.setDuration(self.GATHER_MS)
            motion.setStartValue(0 if grow else full)
            motion.setEndValue(full if grow else 0)

            def step(value):
                for row in rows:
                    if 0 <= row < self.rowCount():
                        header.resizeSection(row, int(value))

            motion.valueChanged.connect(step)
            step(0 if grow else full)
            group.addAnimation(motion)

        def gather(self, pictures, cursor, rows=(), follow=False):
            """The pictures of the rows (with their places in the viewport) fly, opaque, in one
            layer (flight) to the cursor (a global point) while their rows close."""
            from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint

            host = self.window()
            group = QParallelAnimationGroup(host)
            end = host.mapFromGlobal(cursor) + QPoint(12, 10)
            if follow:  # to the cursor where it is now, not where it was
                from PySide6.QtGui import QCursor

                end = lambda: host.mapFromGlobal(QCursor.pos()) + QPoint(12, 10)  # noqa: E731
            items = [(picture, self.viewport().mapTo(host, rect.topLeft()), end) for picture, rect in pictures[:8]]
            _, motion = flight(host, items, self.GATHER_MS, QEasingCurve.Type.OutCubic)
            group.addAnimation(motion)
            self._heights(group, list(rows), grow=False)
            group.finished.connect(group.deleteLater)
            group.start()
            self.gathering = group
            return group

        def lay_back(self, pictures, cursor, ids, pile=None):
            """After the drop: the pile flies from cursor (a global point) to the rows of the molecules ids still in the
            list (where the drop put them, or their old places), then falls apart — the first stays on top, the others
            come out from under it to their rows, which open. The others
            (gone to another project) are not laid anywhere."""
            from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QSequentialAnimationGroup

            host = self.window()
            whole = QSequentialAnimationGroup(host)
            start = host.mapFromGlobal(cursor) + QPoint(12, 10)
            rows = {}
            for row in range(self.rowCount()):
                item = self.item(row, 0)
                if item is not None:
                    rows[item.data(Qt.ItemDataRole.UserRole)] = row
            landed = [rows[i] for i in ids if i in rows]
            if landed:  # chosen again
                from PySide6.QtCore import QItemSelectionModel

                chosen = self.selectionModel()
                flags = QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
                chosen.clearSelection()
                for row in landed:
                    chosen.select(self.model().index(row, 0), flags)
            header = self.verticalHeader()
            places = []
            for (picture, _), ident in zip(pictures[:8], ids):
                if ident in rows:
                    y = header.sectionViewportPosition(rows[ident])
                    places.append((picture, self.viewport().mapTo(host, QPoint(0, y))))
            first = places[0][1] if places else start
            spread_layer = None
            if pile is not None and places:  # the pile comes to the list whole
                distance = (first - start).manhattanLength()
                carrier, way = flight(host, [(pile, start, first)], max(120, min(420, distance)))
                whole.addAnimation(way)
            spread = QParallelAnimationGroup(whole)
            self._heights(spread, landed, grow=True)
            if places:
                spread_layer, apart = flight(host, [(picture, first, place) for picture, place in places],
                                             self.GATHER_MS, QEasingCurve.Type.OutCubic)
                spread.addAnimation(apart)
                if pile is not None:  # shown when the pile has come
                    spread_layer.hide()
                    whole.animationAt(0).finished.connect(lambda: (spread_layer.show(), spread_layer.raise_()))
            whole.addAnimation(spread)
            whole.finished.connect(whole.deleteLater)
            whole.start()
            self.laying = whole
            return whole

        # several rows are carried by the program itself, not by a drag of the system — the
        # pile follows the cursor in the window (opaque, smooth), what is under it is lit, the release decides:
        # hover_at(point) / drop_at(point, rows, copy) of the window (a tab of a project, «+», a row of the list);
        # anywhere else they are put back. One row — the drag of before (its order in the list).
        hover_at = None
        drop_at = None
        carried = None  # (rows, ids, pictures, pile label, pile picture) while carried

        def startDrag(self, actions):
            from PySide6.QtCore import QPoint
            from PySide6.QtGui import QCursor
            from PySide6.QtWidgets import QLabel

            rows = sorted({index.row() for index in self.selectedIndexes()})
            if len(rows) < 2 or self.carried is not None:
                return super().startDrag(actions) if len(rows) < 2 else None
            ids = [self.item(row, 0).data(Qt.ItemDataRole.UserRole) if self.item(row, 0) else None for row in rows]
            pictures = [self.row_picture(row) for row in rows]
            pile = self.pile_picture([p for p, _ in pictures], len(rows))
            host = self.window()
            label = QLabel(host)
            label.setPixmap(pile)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            label.adjustSize()
            label.move(host.mapFromGlobal(QCursor.pos()) + QPoint(12, 10))
            label.hide()
            self.carried = (rows, ids, pictures, label, pile)
            self.carrying = True
            group = self.gather(pictures, QCursor.pos(), rows, follow=True)
            group.finished.connect(lambda: (label.show(), label.raise_()) if self.carried is not None else None)
            return None

        def mouseMoveEvent(self, event):
            if self.carried is None:
                return super().mouseMoveEvent(event)
            from PySide6.QtCore import QPoint

            label = self.carried[3]
            point = event.globalPosition().toPoint()
            label.move(label.parentWidget().mapFromGlobal(point) + QPoint(12, 10))
            label.raise_()
            if self.hover_at is not None:
                self.hover_at(point)
            event.accept()
            return None

        def mouseReleaseEvent(self, event):
            if self.carried is None:
                return super().mouseReleaseEvent(event)
            from PySide6.QtCore import QTimer
            from PySide6.QtWidgets import QApplication

            rows, ids, pictures, label, pile = self.carried
            self.carried = None
            self.carrying = False
            label.hide()
            label.deleteLater()
            gathering = getattr(self, 'gathering', None)
            try:
                if gathering is not None:
                    gathering.setCurrentTime(gathering.duration())
            except RuntimeError:
                pass
            point = event.globalPosition().toPoint()
            copy = bool(QApplication.keyboardModifiers() & Qt.KeyboardModifier.AltModifier)
            if self.hover_at is not None:
                self.hover_at(None)  # the light goes
            if self.drop_at is not None:
                self.drop_at(point, rows, copy)
            QTimer.singleShot(0, lambda: self.lay_back(pictures, point, ids, pile))
            event.accept()
            return None

        def target_row(self, point):
            """The row the rows go before for a point of the viewport (after a row, below its middle)."""
            index = self.indexAt(point)
            return self.rowCount() if not index.isValid() else index.row() + (
                1 if point.y() > self.visualRect(index).center().y() else 0)

        def dropEvent(self, event):
            """The rows dragged go before the row under the cursor (after it, below its middle); the project is
            reordered and the list made anew — the table itself moves nothing (IgnoreAction: no row removed at the end
            of the drag)."""
            from PySide6.QtCore import QTimer

            if event.source() is not self:
                event.ignore()
                return
            rows = sorted({index.row() for index in self.selectedIndexes()})
            point = event.position().toPoint()
            index = self.indexAt(point)
            target = self.rowCount() if not index.isValid() else index.row() + (
                1 if point.y() > self.visualRect(index).center().y() else 0)
            # IgnoreAction: no row removed at the end of a drag of the table's own; a drag of several rows (carrying)
            # takes the drop — an ignored one makes macOS slide the picture back first (the rows came back late)
            event.setDropAction(Qt.DropAction.MoveAction if self.carrying else Qt.DropAction.IgnoreAction)
            event.accept()
            moved = self.on_rows_moved
            if moved is not None and rows:
                QTimer.singleShot(0, lambda: moved(rows, target))

    table = MoleculeTable(0, len(COLUMNS))
    table.setObjectName('projectMolecules')
    # «Название» (it was «Структура»), the columns of COLUMNS, each as wide
    # as dragged (kept), those not wanted hidden (the menu of the head)
    table.setHorizontalHeaderLabels([tr(title) for _, title, _ in COLUMNS])
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(False)
    header.setMinimumSectionSize(36)
    header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
    table.verticalHeader().hide()
    table.verticalHeader().setMinimumSectionSize(0)  # the rows of conformers grow from nothing and shrink to it
    table.setShowGrid(False)
    table.setFrameShape(QFrame.Shape.NoFrame)
    table.setAlternatingRowColors(True)
    table.setWordWrap(False)
    # a number is never cut to «…» (its column is as wide as the widest, fit_number_column); a
    # column narrowed by the user ends its text with «…»
    table.setTextElideMode(Qt.TextElideMode.ElideRight)
    table.setDragEnabled(True)  # the molecules dragged one after another (dropEvent)
    table.setAcceptDrops(True)
    table.viewport().setAcceptDrops(True)
    table.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
    table.setDefaultDropAction(Qt.DropAction.MoveAction)
    table.setDragDropOverwriteMode(False)
    table.setDropIndicatorShown(True)
    return table


def _FoldClicks(table, toggle):
    """A click on ▸ / ▾ before the name of a molecule with conformers — toggle(id): its group unfolds or
    folds (a click elsewhere on the row chooses the molecule as before)."""
    from PySide6.QtCore import QEvent, QObject, Qt

    class Filter(QObject):
        def eventFilter(self, watched, event):
            if event.type() != QEvent.Type.MouseButtonPress or event.button() != Qt.MouseButton.LeftButton:
                return False
            try:
                return self._press(event)
            except RuntimeError:  # the list being deleted
                return False

        def _press(self, event):
            index = table.indexAt(event.position().toPoint())
            if not index.isValid() or index.column() != 1:
                return False
            item, first = table.item(index.row(), 1), table.item(index.row(), 0)
            if (item is None or first is None or item.text()[:1] not in '▸▾'
                    or event.position().x() - table.visualRect(index).left() >= 22):
                return False
            toggle(first.data(Qt.ItemDataRole.UserRole))
            return True

    found = Filter(table)
    table.viewport().installEventFilter(found)
    return found


def fit_number_column(table, count, ticks, labels=()):
    """The column «№» as wide as its widest number and, in the batch mode, the tick before it —
    ResizeToContents left out the width of the check box drawn by the style sheet (15 px), so from 10 on the two digits
    did not fit and were cut away. Returns the width set."""
    from PySide6.QtWidgets import QHeaderView

    metrics = table.fontMetrics()
    digits = max([len(str(max(1, count)))] + [len(str(label)) for label in labels])  # «2.10» of a conformer
    text = max(metrics.horizontalAdvance('8' * digits), metrics.horizontalAdvance(tr('№')))
    width = text + 18 + (15 + 10 if ticks else 0)  # the padding of the cell; the check box and its spacing
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
    table.setColumnWidth(0, width)
    return width


def _list_keys(owner):
    """Delete, ⌫ and Ctrl+Z (⌘Z) of the list of the molecules of a project, before the shortcuts of the
    window take them (ShortcutOverride accepted — the key comes to the list). Ctrl+Z is taken only while there is a
    removal to put back; otherwise it stays «Отменить» of the model."""
    from PySide6.QtCore import QEvent, QObject, Qt
    from PySide6.QtGui import QKeySequence

    class Keys(QObject):
        def eventFilter(self, watched, event):
            kind = event.type()
            if kind not in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress):
                return False
            plain = not event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
            remove = plain and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
            undo = event.matches(QKeySequence.StandardKey.Undo) and owner._project_removed is not None
            if not (remove or undo):
                return False
            if kind == QEvent.Type.ShortcutOverride:
                event.accept()
                return True
            if remove:
                owner.remove_project_molecules()
            else:
                owner.restore_project_molecules()
            return True

    return Keys(owner)

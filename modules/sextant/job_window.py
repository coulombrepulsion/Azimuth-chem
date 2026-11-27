"""Sextant: the window of a running calculation and the dialog of additional settings.

§1 PURPOSE The page of Sextant keeps the main choices (program, task, method, basis, charge, multiplicity); the rarer
    ones (processes and memory, solvent, dispersion, SCF, optimization, properties — in groups that fold) are in a
    dialog opened by «Дополнительные настройки…». A started calculation is shown in its own window: what runs, the time,
    the optimization cycles and the last energy, «Вывод программы», «Остановить», «Папка расчёта»; it can be minimized,
    and is minimized and restored together with the main window. The end of the output is not copied into the window —
    «Вывод программы» opens the output file itself (OutputWindow), which follows the file as the program writes it; the
    formula in the title has its subscripts (H₂O). In Sextant the calculation is a card in the place of the input file
    (dock), not a window; «Входной файл» on it brings the file back; in the other sections the hourglass of the hub
    opens the same widget as a window (undock) that can be hidden, and coming back to Sextant puts it in its place again
    (Sextant.job_follow).
§2 ALGORITHM
    dock(host) — the widget becomes a child of host (added to its layout) without margins of its own, its card
    stays (it stands for the card of the input file), «Входной файл» instead of «Скрыть»; undock() — a window owned
    by the main window again, «Скрыть».
    JobWindow(owner) is a top-level window owned by the main window (Qt.Window; WA_QuitOnClose off, so it
    never keeps the program open). An event filter on the main window: minimized → the job window is
    minimized too (when it was shown), restored → shown again; the main window hidden (closed) → hidden.
    begin(title, details) clears the stages and starts the busy bar; finish() stops it. Closing the window
    only hides it — the calculation goes on, «Окно расчёта» in the card or the «Расчёт» menu shows it again;
    hidden by the user («Скрыть» or the close button of the window) it calls on_parked(True) — the
    hourglass of the hub appears — and on_parked(False) when it is shown again.
    OutputWindow: once a second while visible, the bytes added to the file are appended (a file that became
    shorter is read again); the view stays at the end while «Следить за концом» is on and the user has not scrolled
    up; a file bigger than SHOWN_BYTES is shown from its last SHOWN_BYTES. program_badge(kind) — the mark of a
    program next to its name in Sextant: a coloured square with its letters (Azimuth's own, not the logos).
    OptionsDialog(owner) is not modal: its controls are the owner's solvent, dispersion and memory, so the
    preview follows every change at once.
§3 APPLICATIONS
    modules/sextant/workspace.py (run_card, calculation_page).
§4 SPECIFICATION JobWindow(owner): status (QLabel), bar (QProgressBar), picture (QLabel, Quill when the calculation is
    over — show_picture(name) -> bool, picture_name; while it runs the animation — begin() starts
    show_animation('calc-running') -> bool, paused while the window is hidden and after finish(); movie_running()),
    output_button, stop_button, folder_button, compass_button, spectrum_button, close_button, stages (QLabel),
    stage_keys, begin(title, details), add_stage(key, text, when), show_results(compass, spectrum), finish(),
    show_window(), park(), dock(host), undock(), docked (bool), input_button (owner.show_input_card), picture_size,
    on_parked (callable(bool) or None), parked, followed (True while it was minimized with the main window).
    OutputWindow(owner): watch(paths) — the first of the paths that exists is shown; view (QPlainTextEdit), follow
    (QCheckBox), find (QLineEdit), info (QLabel), refresh() -> bool (something new). program_badge(kind, size=22,
    ratio=1.0) -> QPixmap; subscript(formula) -> 'H₂O'. OptionsDialog(owner, rows): rows = [(title, widget)].
§5 PROCEDURES - below.
§6 NOTES
    Minimizing the window does not slow the calculation: it is a separate process.
§7 TESTS
    tests/test_gui.py::test_sextant_job_window_and_options, test_sextant_output_window_follows_the_file.
§8' ROBUSTNESS
    The filter only reads the state of the main window; a window that was never shown is not shown by it.
"""


from PySide6.QtCore import QEvent, QObject, QRectF, Qt, QTimer
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QScrollArea,
    QSizePolicy,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QVBoxLayout,
    QWidget,
)

from azimuth.i18n import tr
from azimuth.ui import button, card, icon_button, label
from modules.sextant.job_dialogs import OutputWindow, OptionsDialog, FamilyPicker, gold_star  # noqa: F401 — also named from here

PICTURE = 130  # Quill in the window of the calculation, logical pixels
DOCKED_PICTURE = 220  # in Sextant the panel has room for a bigger Quill
BADGES = {  # the mark of each program in Sextant — letters on a colour, not the logos of the programs
    'orca': ('Or', '#2f6db5'), 'gaussian': ('G', '#7a4fb5'), 'psi4': ('Ψ4', '#2a8f84'), 'xtb': ('xtb', '#c27a22'),
    'crest': ('cr', '#8a6a3a'), 'mopac': ('MP', '#5a7d2a'),
    'gamess': ('Ga', '#9a4a3a'), 'nwchem': ('NW', '#3a6a9a'),
}
SUBSCRIPTS = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def subscript(formula):
    """H2O -> H₂O (the window title cannot have HTML)."""
    return str(formula).translate(SUBSCRIPTS)


def program_badge(kind, size=22, ratio=1.0):
    text, colour = BADGES.get(kind, (kind[:2], '#8a96a3'))
    pixmap = QPixmap(round(size * ratio), round(size * ratio))
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(colour))
    p.drawRoundedRect(QRectF(0.5, 0.5, size - 1, size - 1), size * 0.24, size * 0.24)
    font = QFont()
    font.setBold(True)
    font.setPixelSize(round(size * (0.5 if len(text) <= 2 else 0.4)))
    p.setFont(font)
    p.setPen(QColor('#ffffff'))
    p.drawText(QRectF(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, text)
    p.end()
    return pixmap


class _Follower(QObject):
    """Event filter on the main window: the job window follows its minimizing and closing."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window

    def eventFilter(self, watched, event):
        w = self.window
        kind = event.type()
        if kind == QEvent.Type.WindowStateChange:
            if watched.isMinimized():
                if w.isVisible() and not w.isMinimized():
                    w.followed = True
                    w.showMinimized()
            elif w.followed:
                w.followed = False
                w.showNormal()
        elif kind == QEvent.Type.Hide and not watched.isMinimized() and not event.spontaneous():
            w.followed = False
            w.hide()
        return False


class JobWindow(QWidget):
    """In the style of the program — a card on the background of the sections: the title, the task and the
    method, a thin progress bar, the stages passed («✓ Самосогласованное поле сошлось · 0:04»), the status, the end
    of the output; «Остановить», «Папка расчёта», and when it is over «Перейти в Компас» / «Перейти в Спектр»; only
    «Скрыть» (no «Свернуть»: the window is minimized with the program)."""

    def __init__(self, owner):
        super().__init__(owner, Qt.WindowType.Window)
        self.owner = owner
        self.followed = False
        self.docked = False  # a panel inside Sextant (dock) or a window (undock)
        self.picture_size = PICTURE
        self.parked = False  # hidden by the user — the hourglass of the hub is shown
        self.on_parked = None
        self._watched = None
        self._follower = _Follower(self)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName('workspace')  # the background of the sections
        self.setWindowTitle(tr('Расчёт'))
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        frame, layout = card('')
        self.frame = frame
        self.heading = layout.itemAt(0).widget()
        layout.setSpacing(10)
        outer.addWidget(frame, 1)
        self.details = label('', 'subtitle')
        layout.addWidget(self.details)
        self.bar = QProgressBar()
        self.bar.setObjectName('jobBar')
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(6)
        layout.addWidget(self.bar)
        body = QHBoxLayout()  # the status and the stages on the left, Quill on the right when it is over
        body.setSpacing(12)
        column = QVBoxLayout()
        column.setSpacing(10)
        # the status, the stages, the problem and the remedy scroll in their own area when the card is lower than they
        # are
        self.info = QWidget()
        self.info.setObjectName('jobInfo')
        top, column = column, QVBoxLayout(self.info)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(10)
        self.info_scroll = QScrollArea()
        self.info_scroll.setObjectName('jobInfoScroll')
        self.info_scroll.setWidgetResizable(True)
        self.info_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.info_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.info_scroll.setStyleSheet('QScrollArea#jobInfoScroll, QScrollArea#jobInfoScroll > QWidget > QWidget, '
                                       'QWidget#jobInfo {background: transparent;}')
        self.info_scroll.setWidget(self.info)
        top.addWidget(self.info_scroll, 1)
        self.status = label('', 'subtitle')
        column.addWidget(self.status)
        # «Ход расчёта» — the stages under their own heading; a failure — what it is and what it may come from
        self.stages_title = label(tr('Ход расчёта'), 'eyebrow')
        self.stages_title.hide()
        column.addWidget(self.stages_title)
        self.stages = QLabel()  # one line per stage passed
        self.stages.setObjectName('jobStages')
        self.stages.setTextFormat(Qt.TextFormat.RichText)
        self.stages.hide()
        column.addWidget(self.stages)
        self.problem = label('', 'error')
        self.problem.setTextFormat(Qt.TextFormat.RichText)
        self.problem.hide()
        column.addWidget(self.problem)
        # the doctor of the calculation — the repeat with the remedy for the problem above, at one click
        self._remedy = None
        self.remedy_button = button('', self._for_place(self._remedy_pressed), True)
        self.remedy_button.hide()
        remedy_row = QHBoxLayout()
        remedy_row.addWidget(self.remedy_button)
        remedy_row.addStretch(1)
        column.addLayout(remedy_row)
        column.addStretch(1)
        column = top  # the queue below takes the height that is left
        # a queue of calculations — its list (batch_actions.py)
        self.queue_title = label(tr('Очередь'), 'eyebrow')
        self.queue_title.hide()
        column.addWidget(self.queue_title)
        self.queue = QLabel()
        self.queue.setObjectName('jobQueue')
        self.queue.setTextFormat(Qt.TextFormat.RichText)
        self.queue.setWordWrap(True)
        self.queue.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        # the list scrolls inside QUEUE_HEIGHT px (44 structures made the window taller than the screen) and follows the
        # one that runs
        self.queue_scroll = QScrollArea()
        self.queue_scroll.setObjectName('jobQueueScroll')
        self.queue_scroll.setWidgetResizable(True)
        self.queue_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.queue_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.queue_scroll.setStyleSheet('QScrollArea#jobQueueScroll, QScrollArea#jobQueueScroll > QWidget > QWidget '
                                        '{background: transparent;}')
        self.queue_scroll.setWidget(self.queue)
        self.queue_scroll.hide()
        self._queue_running = None
        # the list takes the height that is left in the panel (it was held at up to QUEUE_HEIGHT px, more than the panel
        # had under the stages — its bottom went below the card); at least QUEUE_MIN_LINES lines, the rest scrolls
        column.addWidget(self.queue_scroll, 1000)
        # no stretch under them: it took half of the free height from the stages (stretch 1 each), and «Ход расчёта»
        # scrolled with room left below (the owner, 2026-11-24). No copy of the output here — «Вывод программы» opens it
        body.addLayout(column, 1)
        self.picture = QLabel()
        self.picture.setObjectName('jobQuill')
        self.picture.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignBottom)
        self.picture.hide()
        self.picture_name = None
        body.addWidget(self.picture, 0, Qt.AlignmentFlag.AlignBottom)
        layout.addLayout(body, 1)
        self.stage_keys = []
        self._stage_lines = []
        self.compact = False  # a queue runs — one line each, the list below keeps its place
        self._wrap_policy = {item: item.sizePolicy() for item in (self.heading, self.details, self.status)}
        row = QHBoxLayout()
        row.setSpacing(8)
        # icons that unfold into their text on hover
        self.stop_button = icon_button(tr('Остановить'), self._for_place(owner.run_tool.stop_calculation), 'stop')
        self.stop_button.setEnabled(False)
        # in a queue — the current calculation is stopped, the next one starts
        # the handlers are the window's own, named here — no stand-in that does
        # nothing when a name is missing (three buttons did nothing); found when pressed (a test may replace one)
        self.skip_button = icon_button(tr('Пропустить'), self._for_place(lambda: owner.batch_tool.skip_batch_item()), 'next')
        self.skip_button.hide()
        self.output_button = icon_button(tr('Вывод программы'), self._for_place(owner.run_tool.open_output), 'output')
        self.folder_button = icon_button(tr('Папка расчёта'), self._for_place(owner.run_tool.open_job_folder), 'folder')
        self.compass_button = button(tr('Открыть в Компасе'), self._for_place(lambda: owner.run_tool.go_to_result('compass')), True)
        self.spectrum_button = button(tr('Открыть в Спектре'), self._for_place(lambda: owner.run_tool.go_to_result('spectrum')), True)
        # after a queue — the critical points of every calculation of it (batch_actions.batch_qtaim)
        self.qtaim_button = button(tr('QTAIM для всех'), lambda: owner.batch_tool.batch_qtaim(), False)
        self.qtaim_button.setToolTip(tr('Критические точки плотности всех расчётов очереди (Multiwfn) и таблицы '
                                        'взаимодействий в «Анализ» папки очереди'))
        self.qtaim_button.hide()
        # only «Расчёт → Дескрипторы и logK
        # очереди…» now
        self.close_button = icon_button(tr('Скрыть'), self.park, 'hide')
        # in Sextant the panel stands in the place of the input file — this brings the file back
        self.input_button = icon_button(tr('Входной файл'), lambda: owner.show_input_card(), 'back')
        self.input_button.hide()
        for item in (self.stop_button, self.skip_button, self.output_button, self.folder_button):
            row.addWidget(item)
        row.addStretch(1)
        for item in (self.qtaim_button, self.compass_button, self.spectrum_button,
                     self.input_button, self.close_button):
            row.addWidget(item)
        self.compass_button.hide()
        self.spectrum_button.hide()
        outer.addLayout(row)
        self.resize(560, 340)

    place = None  # 'local' or 'server' — whose calculation this window shows (Sextant sets it)

    def _for_place(self, action):
        """A button of this window acts on the calculation of its place, whatever place is chosen in Sextant now."""
        def run(*args):
            at = getattr(self.owner, 'at_place', None)
            if at is None or self.place is None:
                return action()
            with at(self.place):
                return action()
        return run

    def set_compact(self, on):
        """While a queue runs the title, the settings and the status are one line each (cut at
        the width of the window; the whole text in the tip of the title), the stages are their last line in a line
        kept even when empty, the problems are not shown (✗ and the reason are in the list) — what is above the list
        keeps one height from one calculation to the next. A single calculation and a queue that is over: in full."""
        on = bool(on)
        if on == self.compact:
            return False
        self.compact = on
        for item in (self.heading, self.details, self.status):
            item.setWordWrap(not on)
            if on:
                item.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            else:
                item.setSizePolicy(self._wrap_policy[item])
        line = self.stages.fontMetrics().lineSpacing()
        if on:
            self.stages.setWordWrap(False)
            self.stages.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            self.stages.setFixedHeight(line)
            self.stages_title.hide()
            self.problem.hide()
            self.remedy_button.hide()
        else:
            self.stages.setMinimumHeight(0)
            self.stages.setMaximumHeight(16777215)
            self.stages.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
            self.stages.setVisible(bool(self._stage_lines))
            self.stages_title.setVisible(bool(self._stage_lines))
            self.problem.setVisible(bool(self.problem.text()))
            self.remedy_button.setVisible(self._remedy is not None)
        self._show_stages()
        return True

    def _show_stages(self):
        if self.compact:
            self.stages.setText(self._stage_lines[-1] if self._stage_lines else '')
            self.stages.show()
        else:
            self.stages.setText('<br>'.join(self._stage_lines))

    def begin(self, title, details=''):
        self.used = True  # the window shows something (a calculation, an installation) — not «Расчёта ещё не было»
        self.heading.setText(title)
        self.heading.setToolTip(title)
        self.setWindowTitle(title)
        self._set_parked(False)
        self.details.setText(details)
        self.details.setVisible(bool(details))
        self.status.setText('')
        self.stage_keys = []
        self._stage_lines = []
        self.stages.clear()
        self.stages.hide()
        self.stages_title.hide()
        self.problem.clear()
        self.problem.hide()
        self.show_remedy('')
        self.show_batch(None)  # a job of a queue shows its list again right after
        self.qtaim_button.hide()
        self.compass_button.hide()
        self.spectrum_button.hide()
        self.show_picture(None)
        self.show_animation('calc-running', self.picture_size)  # Quill counts while it runs
        self.bar.setRange(0, 0)  # busy
        self.bar.show()

    def show_idle(self):
        """The window opened before any calculation («Расчёт → Окно расчёта» with nothing run): a dash for the
        title and a line what to do — it was an empty card in the place of the input file."""
        self.heading.setText('—')
        self.setWindowTitle(tr('Расчёт'))
        self.details.clear()
        self.details.hide()
        self.status.setText(tr('Расчёта ещё не было. Постройте молекулу в Компасе и нажмите «Запустить расчёт»; '
                               '«Входной файл» вернёт файл на место.'))
        self.status.setWordWrap(True)
        for item in (self.stages, self.problem):
            item.clear()
            item.hide()
        self.stages_title.hide()
        self.show_batch(None)
        self.compass_button.hide()
        self.spectrum_button.hide()
        self.show_picture(None)
        self.bar.hide()
        for item in (self.stop_button, self.output_button, self.folder_button):
            item.setEnabled(False)
        return True

    def add_stage(self, key, text, when=''):
        """A stage of the calculation is passed (once per key)."""
        if key in self.stage_keys:
            return False
        self.stage_keys.append(key)
        tail = f' <span style="color: #8a94a3;">· {when}</span>' if when else ''
        self._stage_lines.append(f'<span style="color: #3a9a5b;">✓</span>&nbsp; {text}{tail}')
        self._show_stages()
        self.stages.show()
        self.stages_title.setVisible(not self.compact)
        return True

    def show_remedy(self, text, action=None):
        """The button of the doctor — «Повторить с …» under the problem; '' or no action hides it."""
        self._remedy = action if text else None
        self.remedy_button.setText(text or '')
        self.remedy_button.setToolTip(tr('Секстант поставит эти настройки и запустит расчёт снова; прежний расчёт и его '
                                         'файлы останутся.') if text else '')
        self.remedy_button.setVisible(bool(text) and action is not None and not self.compact)
        return self.remedy_button.isVisibleTo(self) if text else False

    def _remedy_pressed(self):
        action, self._remedy = self._remedy, None
        self.remedy_button.hide()  # one press — one repeat
        return action() if action is not None else None

    def show_problems(self, problems):
        """[(what, why)] of runner.diagnose under the stages, in the colour of an error; [] hides it."""
        from html import escape

        if not problems:
            self.problem.clear()
            self.problem.hide()
            return False
        self.problem.setText('<br><br>'.join(f'<b>{escape(what)}</b><br>{escape(why)}' for what, why in problems))
        self.problem.setVisible(not self.compact)
        return True

    QUEUE_HEIGHT = 240  # px — about ten lines of the list of a queue; more scroll
    QUEUE_MIN_LINES = 3  # the list is never lower than this, it grows into the height left in the panel
    MARKS = {'waiting': ('·', '#8a94a3'), 'running': ('▶', '#2f6fd6'), 'done': ('✓', '#3a9a5b'),
             'failed': ('✗', '#c0392b'), 'stopped': ('■', '#8a94a3'), 'skipped': ('–', '#8a94a3'),
             'sent': ('⇡', '#2f6fd6'),  # sent to the server before the exit, waits there
             'searching': ('◌', '#2f6fd6')}  # its best conformer is searched first

    def show_batch(self, queue):
        """The list of a queue (batch.Batch) under the stages; None hides it."""
        from html import escape

        if queue is None:
            for item in (self.queue_scroll, self.queue_title, self.skip_button):
                item.hide()
            self._queue_running = None
            self._queue_follow = False
            self.set_compact(False)
            return False
        self.set_compact(not queue.done())
        lines = []
        for k, item in enumerate(queue.items, 1):
            mark, colour = self.MARKS.get(item.state, ('·', '#8a94a3'))
            energy = '' if item.energy is None else f' <span style="color: #8a94a3;">· {item.energy:.6f} Eh</span>'
            if getattr(item, 'note', '') and item.state == 'failed':  # why it failed
                energy += f' <span style="color: #8a94a3;">· {escape(item.note[:160])}</span>'
            text = escape(f'{k}. {item.name}')
            if item.state == 'searching':
                energy += f' <span style="color: #8a94a3;">· {escape(tr("поиск конформера…"))}</span>'
            lines.append(f'<p style="margin: 0;"><span style="color: {colour};">{mark}</span>&nbsp; '
                         + (f'<b>{text}</b>' if item.state in ('running', 'searching') else text) + energy + '</p>')
        counts = queue.counts()
        left = sum(counts.get(state, 0) for state in ('waiting', 'running', 'sent', 'searching'))
        title = tr(f'Очередь · готово {counts["done"]} из {len(queue.items)}')
        if left:
            title += tr(f' · осталось {left}')
        if counts.get('failed'):
            title += tr(f' · ошибок {counts["failed"]}')
        self.queue_title.setText(title)
        self.queue.setText(''.join(lines))
        self.queue.show()
        line = self.queue.fontMetrics().lineSpacing()
        self.queue_scroll.setMinimumHeight(min(self.QUEUE_MIN_LINES * line + 4, self.queue.sizeHint().height() + 4))
        self.queue_scroll.show()
        self.queue_title.show()
        running = next((k for k, item in enumerate(queue.items) if item.state in ('running', 'searching')), None)
        if running is not None and running != self._queue_running:  # a new one started: it is brought into sight
            self._queue_running = running
            self._queue_follow = True
            QTimer.singleShot(0, self, self.follow_running)
        running = not queue.done()
        self.skip_button.setVisible(running)
        self.skip_button.setEnabled(running)
        self.stop_button.setToolTip(tr('Остановить очередь') if running else tr('Остановить'))
        return True

    def follow_running(self):
        """The running line of the queue into sight — once the list is laid out (before, at the width of a
        list not shown, the line was counted far too low and the scroll stopped at the top); again after the window
        changed its size while the queue runs."""
        number = self._queue_running
        if number is None or self.queue_scroll.isHidden():
            return False
        line = self.queue.fontMetrics().lineSpacing()
        self.queue_scroll.ensureVisible(0, self.queue_line_middle(number), 0, 2 * line)
        return True

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if getattr(self, '_queue_follow', False):
            from PySide6.QtCore import QTimer

            QTimer.singleShot(0, self, self.follow_running)

    def queue_line_middle(self, number):
        """The height (px from the top of the list) of the middle of line number — a long name or the reason
        of a failure wraps onto two lines, so «number × the height of a line» missed the running one lower down."""
        from PySide6.QtGui import QTextDocument

        document = QTextDocument()
        document.setDefaultFont(self.queue.font())
        document.setDocumentMargin(0)
        document.setHtml(self.queue.text())
        document.setTextWidth(max(1, self.queue.width() - 2 * self.queue.margin()))
        block = document.findBlockByNumber(number)
        if not block.isValid():
            return 0
        rect = document.documentLayout().blockBoundingRect(block)
        return int(rect.top() + rect.height() / 2)

    def show_results(self, compass=False, spectrum=False):
        """One of them blue — Spectrum when the result has spectra, else Compass —
        in the gold frame of the next step; the other white. The
        frame 2 px of the lighter gold (hub.branding.NEXT_GOLD), no star."""
        self.compass_button.setVisible(compass)
        self.spectrum_button.setVisible(spectrum)
        main = self.spectrum_button if spectrum else self.compass_button
        for item in (self.compass_button, self.spectrum_button):
            item.setObjectName('primary' if item is main else '')
            item.setProperty('next', item is main)
            item.style().unpolish(item)
            item.style().polish(item)
        self.name_result_buttons()

    # the section shown — its button «Открыть», the other
    # «Открыть в …»; in Sextant (and elsewhere) both «Открыть в …»
    RESULT_WORDS = {0: ('Открыть', 'Открыть в Спектре'), 2: ('Открыть в Компасе', 'Открыть')}
    ELSEWHERE = ('Открыть в Компасе', 'Открыть в Спектре')

    def section_shown(self):
        stack = getattr(self.owner, 'stack', None)
        try:
            return stack.currentIndex() if stack is not None else None
        except RuntimeError:
            return None

    def name_result_buttons(self, *args):
        stack = getattr(self.owner, 'stack', None)
        if stack is not None and not getattr(self, '_follows_sections', False):
            stack.currentChanged.connect(self.name_result_buttons)
            self._follows_sections = True
        compass, spectrum = self.RESULT_WORDS.get(self.section_shown(), self.ELSEWHERE)
        self.compass_button.setText(tr(compass))
        self.spectrum_button.setText(tr(spectrum))

    def show_animation(self, name='calc-running', size=PICTURE):
        """The picture of a running calculation while it runs (0.247.0: the picture of the state in thin lines, not the
        animation of Quill); False when there is none."""
        return self.show_picture(name, size)

    def _stop_movie(self):
        movie = getattr(self, '_movie', None)
        if movie is not None:
            movie.stop()
            movie.deleteLater()
            self._movie = None

    def movie_running(self):
        from PySide6.QtGui import QMovie

        movie = getattr(self, '_movie', None)
        return movie is not None and movie.state() == QMovie.MovieState.Running

    def show_picture(self, name, size=None):
        """Quill of the state (assets/quill/quill-<name>.webp); None or a missing file — no picture."""
        from azimuth import quill

        self._stop_movie()  # the animation of the running calculation gives way
        size = size or self.picture_size
        picture = quill.pixmap(name, size) if name else None
        self.picture_name = name if picture is not None and not picture.isNull() else None
        if self.picture_name is None:
            self.picture.clear()
            self.picture.hide()
            return False
        self.picture.setFixedSize(size, size)
        self.picture.setPixmap(picture)
        self.picture.show()
        return True

    def set_picture_size(self, size):
        """Quill of another size (the panel in Sextant — bigger, the window — PICTURE); what she shows stays."""
        from PySide6.QtGui import QMovie

        if size == self.picture_size:
            return False
        self.picture_size = size
        name = self.picture_name
        if name is None:
            return True
        movie = getattr(self, '_movie', None)
        if movie is not None:
            paused = movie.state() == QMovie.MovieState.Paused and self.isVisible()  # over: it stopped counting
            self.show_animation(name, size)
            if paused and getattr(self, '_movie', None) is not None:
                self._movie.setPaused(True)
        else:
            self.show_picture(name, size)
        return True

    def finish(self):
        self.bar.setRange(0, 1)
        self.bar.setValue(1)
        if getattr(self, '_movie', None) is not None:  # over — Quill stops counting (a picture of the end follows)
            self._movie.setPaused(True)

    def showEvent(self, event):
        super().showEvent(event)
        movie = getattr(self, '_movie', None)
        if movie is not None and self.bar.maximum() == 0:  # plays only while it is seen and the job runs
            movie.setPaused(False)

    def hideEvent(self, event):
        movie = getattr(self, '_movie', None)
        if movie is not None:
            movie.setPaused(True)
        super().hideEvent(event)

    # a card in Sextant or a window ---------------------------------------------------------------------
    def dock(self, host):
        """Into Sextant, in the place of the input file: a child of host, «Входной файл» instead of «Скрыть»."""
        if self.docked and self.parentWidget() is host:
            return self
        if self.isWindow():
            self.followed = False
            self.hide()
        self.docked = True
        self.setParent(host, Qt.WindowType.Widget)
        host.layout().addWidget(self)
        self.layout().setContentsMargins(0, 0, 0, 0)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self.setObjectName('jobPanel')
        self.close_button.hide()
        self.input_button.show()
        self.set_picture_size(DOCKED_PICTURE)
        return self

    def undock(self):
        """A window of its own again (the other sections: the hourglass of the hub opens it)."""
        if not self.docked:
            return self
        host = self.parentWidget()
        if host is not None and host.layout() is not None:
            host.layout().removeWidget(self)
        self.docked = False
        self.setParent(self.owner, Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName('workspace')
        self.layout().setContentsMargins(16, 16, 16, 16)
        self.input_button.hide()
        self.close_button.show()
        self.set_picture_size(PICTURE)
        self.resize(560, 340)
        return self

    def show_window(self):
        self.name_result_buttons()
        if self.docked:  # in Sextant the panel is the window
            self.show()
            self._set_parked(False)
            return self
        top = self.owner.window()
        if self._watched is not top:
            if self._watched is not None:
                self._watched.removeEventFilter(self._follower)
            top.installEventFilter(self._follower)
            self._watched = top
        self.followed = False
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self._set_parked(False)
        return self

    def park(self):
        """«Скрыть»: the calculation goes on, the hourglass of the hub stands for the window."""
        self.hide()
        self._set_parked(True)

    def closeEvent(self, event):  # the close button of the window is «Скрыть» too
        super().closeEvent(event)
        if event.isAccepted():
            self._set_parked(True)

    def _set_parked(self, parked):
        self.parked = parked
        if self.on_parked is not None:
            self.on_parked(parked)



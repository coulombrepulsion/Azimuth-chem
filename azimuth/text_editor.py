"""The text editor of the program.
§1 PURPOSE
    One editor for the input files of Sextant and the text files of «Файлы на сервере»: what a plain text editor such
    as AkelPad gives — the line numbers, the line of the cursor, the pairs of brackets, find and replace with a bar
    under the text (case, whole word, regular expression, within the selection), go to a line, the case of the
    selection, a line duplicated, moved or deleted, indent and outdent of a block, comment and uncomment (the comment
    sign of the program: ORCA «#», Gaussian and Quantum ESPRESSO «!»), the date inserted, overwrite, word wrap, the
    spaces and tabs shown, the zoom — with the keys of AkelPad, all in the context menu with their keys; the status line
    (line, column, selection, lines, INS/OVR, wrap).
§2 KEYS (AkelPad, the defaults of its menus)
    Ctrl+F find · F3 / Shift+F3 next / previous · Ctrl+F3 / Ctrl+Shift+F3 the selected word down / up · Ctrl+R
    (and Ctrl+H) replace · Ctrl+G go to line · Ctrl+U word wrap · Insert overwrite · F5 date and time · Ctrl+D the line
    duplicated · Ctrl+Shift+K the line deleted · Alt+Up / Alt+Down the line moved · Tab / Shift+Tab the block indented /
    outdented · Ctrl+/ comment · Ctrl+Shift+U upper case · Ctrl+Shift+L lower case · Ctrl+Alt+U capitals · Ctrl+Up /
    Ctrl+Down the text scrolled · Ctrl+= / Ctrl+- / Ctrl+0 zoom (and Ctrl+wheel) · Ctrl+S save, Ctrl+O open (when the
    owner gives them) · F1 the list of the keys · Esc closes the bar.
§4 SPECIFICATION CodeEdit(QPlainTextEdit): comment, line_numbers, find(text, back=False, case=False, word=False,
    regex=False) -> bool, replace_all(text, new, …) -> int, go_to_line(n), duplicate_line(), delete_line(),
    move_line(step), indent(step), toggle_comment(), change_case(kind), insert_date(), set_wrap(on), set_whitespace(on),
    zoom(step), status() -> str. Set_language(kind) — the colours of an input: 'orca', 'gaussian', 'qe', 'cp2k', 'psi4',
    'nwchem', 'gamess', 'mopac', 'xtb' or None (plain text); guess_language(name, text) -> kind | None (Highlighter: the
    keywords, the blocks, the coordinates, the numbers and the comments of the program, in both themes).
    EditorPane(edit=None, save=None, open_=None): the editor, its find bar (.bar: .find_edit, .replace_edit, .case,
    .word, .regex, .within) and its status line (.status); .edit is the CodeEdit.
§7 TESTS
    tests/gui/test_text_editor.py."""

import re
import sys
from datetime import datetime

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QKeySequence,
    QPainter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
    QTextFormat,
    QTextOption,
)
from PySide6.QtWidgets import (QCheckBox, QFrame, QHBoxLayout, QInputDialog, QLabel, QLineEdit, QPlainTextEdit,
                               QPushButton, QTextEdit, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.text_highlight import guess_language, Highlighter, _Numbers, LANGUAGES  # noqa: F401 — also named from here

PAIRS = {'(': ')', '[': ']', '{': '}'}
CLOSING = {v: k for k, v in PAIRS.items()}

# (key of the action, its title, its keys) — the context menu and the list of F1 are made of it
KEYS = (
    ('find', 'Найти…', 'Ctrl+F'),
    ('next', 'Найти далее', 'F3'),
    ('previous', 'Найти назад', 'Shift+F3'),
    ('word_next', 'Найти выделенное вниз', 'Ctrl+F3'),
    ('word_previous', 'Найти выделенное вверх', 'Ctrl+Shift+F3'),
    ('replace', 'Заменить…', 'Ctrl+R'),
    ('go_to', 'Перейти к строке…', 'Ctrl+G'),
    (None, None, None),
    ('duplicate', 'Дублировать строку', 'Ctrl+D'),
    ('delete_line', 'Удалить строку', 'Ctrl+Shift+K'),
    ('line_up', 'Строку вверх', 'Alt+Up'),
    ('line_down', 'Строку вниз', 'Alt+Down'),
    ('comment', 'Закомментировать / раскомментировать', 'Ctrl+/'),
    ('upper', 'ВЕРХНИЙ РЕГИСТР', 'Ctrl+Shift+U'),
    ('lower', 'нижний регистр', 'Ctrl+Shift+L'),
    ('title', 'Каждое Слово С Заглавной', 'Ctrl+Alt+U'),
    ('date', 'Вставить дату и время', 'F5'),
    (None, None, None),
    ('wrap', 'Перенос по словам', 'Ctrl+U'),
    ('whitespace', 'Показывать пробелы и табуляции', ''),
    ('overwrite', 'Режим замены (ЗАМ)', 'Insert'),
    ('zoom_in', 'Крупнее', 'Ctrl+='),
    ('zoom_out', 'Мельче', 'Ctrl+-'),
    ('zoom_reset', 'Обычный размер', 'Ctrl+0'),
    (None, None, None),
    ('keys', 'Горячие клавиши…', 'F1'),
)
# the groups of the menu of the right button (the list of KEYS was too long for one menu)
MENU_GROUPS = (
    ('Поиск и переход', ('find', 'next', 'previous', 'word_next', 'word_previous', 'replace', 'go_to')),
    ('Строки', ('duplicate', 'delete_line', 'line_up', 'line_down', 'comment')),
    ('Регистр', ('upper', 'lower', 'title')),
    ('Вид', ('wrap', 'whitespace', 'overwrite', 'zoom_in', 'zoom_out', 'zoom_reset')),
)
OTHER_KEYS = (('Tab / Shift+Tab', 'Сдвинуть выделенные строки вправо / влево'),
              ('Ctrl+Up / Ctrl+Down', 'Прокрутить текст на строку'),
              ('Ctrl+колесо мыши', 'Крупнее / мельче'),
              ('Ctrl+Z / Ctrl+Y', 'Отменить / повторить'),
              ('Ctrl+S / Ctrl+O', 'Сохранить / открыть файл (где они есть)'),
              ('Esc', 'Закрыть панель поиска'))


class CodeEdit(QPlainTextEdit):
    """A QPlainTextEdit with what AkelPad gives (§1); everything else of QPlainTextEdit as it is."""

    statusChanged = Signal()

    def __init__(self, text='', parent=None, comment='#'):
        super().__init__(parent)
        self.setObjectName('code')
        self.comment = comment
        self.base_px = self.size_px = 0  # the size of the font before Ctrl+= / Ctrl+- and now (px)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.numbers = _Numbers(self)
        self.line_numbers = True
        self.blockCountChanged.connect(self._margins)
        self.updateRequest.connect(self._scrolled)
        self.cursorPositionChanged.connect(self._marks)
        self.cursorPositionChanged.connect(self.statusChanged.emit)
        self.selectionChanged.connect(self.statusChanged.emit)
        self.textChanged.connect(self.statusChanged.emit)
        self.found = []  # the selections of the last search (shown in yellow)
        self.outside = []  # the extra selections set by the owner (setExtraSelections)
        self.highlighter = None  # set_language: the colours of an input
        if text:
            self.setPlainText(text)
        self._margins()
        self._marks()

    def set_language(self, language):
        """The colours of the input of a program (LANGUAGES), None — plain text; the sign of Ctrl+/ follows."""
        if language in LANGUAGES:
            self.comment = LANGUAGES[language]['comment'] or self.comment
        # 2026-11-21 (the full run: the input file of Sextant came out empty, «изменён вручную» by itself): the
        # highlighter colours the text through the document, which tells textChanged as an edit would — a new
        # language is no change of the text, so the signals of the editor are quiet meanwhile
        quiet = self.blockSignals(True)
        try:
            if self.highlighter is None:
                if language not in LANGUAGES:
                    return None
                self.highlighter = Highlighter(self, language)
            else:
                self.highlighter.set_language(language)
        finally:
            self.blockSignals(quiet)
        return self.highlighter.language

    def language(self):
        return self.highlighter.language if self.highlighter is not None else None

    # -- the line numbers ---------------------------------------------------------------------------------------------
    def numbers_width(self):
        if not self.line_numbers:
            return 0
        digits = len(str(max(1, self.blockCount())))
        return 14 + self.fontMetrics().horizontalAdvance('9') * max(2, digits)

    def _margins(self, *args):
        self.setViewportMargins(self.numbers_width(), 0, 0, 0)

    def _scrolled(self, rect, dy):
        if dy:
            self.numbers.scroll(0, dy)
        else:
            self.numbers.update(0, rect.y(), self.numbers.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._margins()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        area = self.contentsRect()
        self.numbers.setGeometry(QRect(area.left(), area.top(), self.numbers_width(), area.height()))

    def paint_numbers(self, widget, event):
        painter = QPainter(widget)
        palette = self.palette()
        base = palette.base().color()
        painter.fillRect(event.rect(), base.darker(104) if base.lightness() > 128 else base.lighter(118))
        dim = QColor(palette.text().color())
        dim.setAlpha(110)
        bright = palette.text().color()
        block = self.firstVisibleBlock()
        number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        height = self.fontMetrics().height()
        painter.setFont(self.font())
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(bright if number == current else dim)
                painter.drawText(0, top, widget.width() - 6, height, Qt.AlignmentFlag.AlignRight, str(number + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            number += 1

    # -- the line of the cursor, the brackets, what was found ----------------------------------------------------------
    @staticmethod
    def _mark(cursor, colour, full=False):
        """An extra selection (its format and cursor made first: PySide gives copies of the fields of the struct)."""
        mark = QTextEdit.ExtraSelection()
        style = QTextCharFormat()
        style.setBackground(colour)
        if full:
            style.setProperty(QTextFormat.Property.FullWidthSelection, True)
        mark.format = style
        mark.cursor = cursor
        return mark

    def _marks(self):
        here = QTextCursor(self.textCursor())
        here.clearSelection()
        marks = [self._mark(here, QColor(42, 98, 184, 22), True)]
        for start in self.bracket_pair():
            cursor = QTextCursor(self.document())
            cursor.setPosition(start)
            cursor.setPosition(start + 1, QTextCursor.MoveMode.KeepAnchor)
            marks.append(self._mark(cursor, QColor(46, 158, 91, 70)))
        marks += [self._mark(cursor, QColor(255, 214, 10, 110)) for cursor in self.found]
        super().setExtraSelections(marks + list(self.outside))
        self.numbers.update()

    def setExtraSelections(self, selections):
        """The marks of the owner (the lines with problems of the input of Sextant) kept under those of the editor."""
        self.outside = list(selections)
        self._marks()

    def bracket_pair(self):
        """The positions of the bracket at the cursor (or before it) and of its pair, or ()."""
        doc = self.document()
        at = self.textCursor().position()
        for k in (at, at - 1):
            ch = doc.characterAt(k) if 0 <= k < doc.characterCount() else ''
            if ch and (ch in PAIRS or ch in CLOSING):
                text = self.toPlainText()
                step, mine, other = (1, ch, PAIRS[ch]) if ch in PAIRS else (-1, ch, CLOSING[ch])
                depth, j = 0, k
                while 0 <= j < len(text):
                    if text[j] == mine:
                        depth += 1
                    elif text[j] == other:
                        depth -= 1
                        if depth == 0:
                            return (k, j)
                    j += step
                return ()
        return ()

    # -- find and replace ------------------------------------------------------------------------------------------------
    def _flags(self, back, case, word):
        flags = QTextDocument.FindFlag(0)
        if back:
            flags |= QTextDocument.FindFlag.FindBackward
        if case:
            flags |= QTextDocument.FindFlag.FindCaseSensitively
        if word:
            flags |= QTextDocument.FindFlag.FindWholeWords
        return flags

    def _pattern(self, text, case, word, regex):
        from PySide6.QtCore import QRegularExpression

        body = text if regex else re.escape(text)
        if word:
            body = r'\b' + body + r'\b'
        expression = QRegularExpression(body)
        if not case:
            expression.setPatternOptions(QRegularExpression.PatternOption.CaseInsensitiveOption)
        return expression

    def find(self, text, back=False, case=False, word=False, regex=False, wrap=True):
        """The next (previous) match selected; from the other end when none is left (wrap). False — none at all."""
        if not text:
            return False
        what = self._pattern(text, case, word, regex) if regex else text
        flags = self._flags(back, case, word and not regex)
        doc = self.document()
        cursor = doc.find(what, self.textCursor(), flags)
        if cursor.isNull() and wrap:
            start = QTextCursor(doc)
            start.movePosition(QTextCursor.MoveOperation.End if back else QTextCursor.MoveOperation.Start)
            cursor = doc.find(what, start, flags)
        if cursor.isNull() or not cursor.hasSelection():
            return False
        self.setTextCursor(cursor)
        self.found = self.all_found(text, case, word, regex)
        self._marks()
        return True

    def all_found(self, text, case=False, word=False, regex=False, within=None, limit=2000):
        doc = self.document()
        what = self._pattern(text, case, word, regex) if regex else text
        flags = self._flags(False, case, word and not regex)
        found, cursor = [], QTextCursor(doc)
        if within is not None:
            cursor.setPosition(within[0])
        while len(found) < limit:
            cursor = doc.find(what, cursor, flags)
            if cursor.isNull() or not cursor.hasSelection():
                break
            if within is not None and cursor.selectionEnd() > within[1]:
                break
            found.append(QTextCursor(cursor))
        return found

    def replace_current(self, text, new, case=False, word=False, regex=False):
        """The selection replaced when it is a match, then the next one found."""
        cursor = self.textCursor()
        if cursor.hasSelection() and self._matches(cursor.selectedText(), text, case, word, regex):
            cursor.insertText(self._substitute(cursor.selectedText(), text, new, case, regex))
        return self.find(text, False, case, word, regex)

    @staticmethod
    def _matches(chosen, text, case, word, regex):
        if regex:
            try:
                return re.fullmatch(text, chosen, 0 if case else re.IGNORECASE) is not None
            except re.error:
                return False
        return chosen == text if case else chosen.lower() == text.lower()

    @staticmethod
    def _substitute(chosen, text, new, case, regex):
        if not regex:
            return new
        return re.sub(text, re.sub(r'\$(\d)', r'\\\1', new), chosen, count=1, flags=0 if case else re.IGNORECASE)

    def replace_all(self, text, new, case=False, word=False, regex=False, selection_only=False):
        """Every match (in the selection only) replaced as one step of undo; their number."""
        cursor = self.textCursor()
        within = (cursor.selectionStart(), cursor.selectionEnd()) if selection_only and cursor.hasSelection() else None
        found = self.all_found(text, case, word, regex, within, limit=1_000_000)
        if not found:
            return 0
        edit = QTextCursor(self.document())
        edit.beginEditBlock()
        for match in reversed(found):
            chosen = match.selectedText()
            match.insertText(self._substitute(chosen, text, new, case, regex))
        edit.endEditBlock()
        self.found = []
        self._marks()
        return len(found)

    def clear_found(self):
        self.found = []
        self._marks()

    # -- lines ------------------------------------------------------------------------------------------------------------
    def go_to_line(self, number):
        block = self.document().findBlockByNumber(max(0, min(int(number) - 1, self.blockCount() - 1)))
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.centerCursor()
        return block.blockNumber() + 1

    def _lines(self):
        """(first block, last block) of the selection (the line of the cursor without one)."""
        cursor = self.textCursor()
        doc = self.document()
        first = doc.findBlock(cursor.selectionStart())
        last = doc.findBlock(cursor.selectionEnd())
        if cursor.hasSelection() and last.position() == cursor.selectionEnd() and last != first:
            last = last.previous()
        return first, last

    def _select_lines(self, first, last):
        cursor = QTextCursor(self.document())
        cursor.setPosition(first.position())
        cursor.setPosition(last.position() + len(last.text()), QTextCursor.MoveMode.KeepAnchor)
        return cursor

    def duplicate_line(self):
        first, last = self._lines()
        chosen = self._select_lines(first, last)
        text = chosen.selectedText().replace('\u2029', '\n')
        cursor = QTextCursor(self.document())
        cursor.setPosition(last.position() + len(last.text()))
        cursor.insertText('\n' + text)
        moved = self.textCursor()
        moved.setPosition(self.textCursor().position() + len(text) + 1)
        self.setTextCursor(moved)

    def delete_line(self):
        first, last = self._lines()
        cursor = self._select_lines(first, last)
        cursor.beginEditBlock()
        if last.next().isValid():
            cursor.movePosition(QTextCursor.MoveOperation.NextCharacter, QTextCursor.MoveMode.KeepAnchor)
        elif first.previous().isValid():
            start = cursor.selectionEnd()
            cursor.setPosition(first.position() - 1)
            cursor.setPosition(start, QTextCursor.MoveMode.KeepAnchor)
        cursor.removeSelectedText()
        cursor.endEditBlock()
        self.setTextCursor(cursor)

    def move_line(self, step):
        """The lines of the selection one line up (step -1) or down (+1), still selected."""
        first, last = self._lines()
        other = first.previous() if step < 0 else last.next()
        if not other.isValid():
            return False
        lines = self._select_lines(first, last)
        text = lines.selectedText().replace('\u2029', '\n')
        column = self.textCursor().positionInBlock()
        count = last.blockNumber() - first.blockNumber()
        # the places taken before the edit: the blocks replaced by it are no longer valid after it
        first_at, last_end = first.position(), last.position() + len(last.text())
        other_at, other_text = other.position(), other.text()
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        if step < 0:
            cursor.setPosition(other_at)
            cursor.setPosition(last_end, QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(text + '\n' + other_text)
            start = other_at
        else:
            cursor.setPosition(first_at)
            cursor.setPosition(other_at + len(other_text), QTextCursor.MoveMode.KeepAnchor)
            cursor.insertText(other_text + '\n' + text)
            start = first_at + len(other_text) + 1
        cursor.endEditBlock()
        doc = self.document()
        top = doc.findBlock(start)
        end = doc.findBlockByNumber(top.blockNumber() + count)
        chosen = QTextCursor(doc)
        if count:
            chosen.setPosition(top.position())
            chosen.setPosition(end.position() + len(end.text()), QTextCursor.MoveMode.KeepAnchor)
        else:
            chosen.setPosition(top.position() + min(column, len(top.text())))
        self.setTextCursor(chosen)
        return True

    def indent(self, step):
        """Tab / Shift+Tab with lines selected: each of them shifted by four spaces (a tab taken away too)."""
        first, last = self._lines()
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        block = first
        while block.isValid():
            line = QTextCursor(block)
            if step > 0:
                line.insertText('    ')
            else:
                text = block.text()
                cut = 1 if text.startswith('\t') else min(4, len(text) - len(text.lstrip(' ')))
                if cut:
                    line.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, cut)
                    line.removeSelectedText()
            if block == last:
                break
            block = block.next()
        cursor.endEditBlock()
        self.setTextCursor(self._select_lines(first, last))

    def toggle_comment(self):
        """The lines commented with the sign of the program, or uncommented when every one of them is."""
        sign = self.comment or '#'
        first, last = self._lines()
        blocks = []
        block = first
        while block.isValid():
            blocks.append(block)
            if block == last:
                break
            block = block.next()
        filled = [b for b in blocks if b.text().strip()]
        undo = all(b.text().lstrip().startswith(sign) for b in filled) and filled
        cursor = QTextCursor(self.document())
        cursor.beginEditBlock()
        for b in blocks:
            text = b.text()
            if not text.strip():
                continue
            line = QTextCursor(b)
            if undo:
                at = len(text) - len(text.lstrip())
                take = len(sign) + (1 if text[at + len(sign):at + len(sign) + 1] == ' ' else 0)
                line.setPosition(b.position() + at)
                line.setPosition(b.position() + at + take, QTextCursor.MoveMode.KeepAnchor)
                line.removeSelectedText()
            else:
                line.insertText(sign + ' ')
        cursor.endEditBlock()
        self.setTextCursor(self._select_lines(first, last))
        return not undo

    def change_case(self, kind):
        cursor = self.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        text = cursor.selectedText()
        new = text.upper() if kind == 'upper' else text.lower() if kind == 'lower' else text.title()
        start = cursor.selectionStart()
        cursor.insertText(new)
        cursor.setPosition(start)
        cursor.setPosition(start + len(new), QTextCursor.MoveMode.KeepAnchor)
        self.setTextCursor(cursor)

    def insert_date(self):
        self.insertPlainText(datetime.now().strftime('%H:%M %d.%m.%Y'))

    # -- the view ---------------------------------------------------------------------------------------------------------
    def set_wrap(self, on):
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth if on else QPlainTextEdit.LineWrapMode.NoWrap)
        self.statusChanged.emit()

    def wrapped(self):
        return self.lineWrapMode() != QPlainTextEdit.LineWrapMode.NoWrap

    def set_whitespace(self, on):
        option = self.document().defaultTextOption()
        flags = option.flags()
        if on:
            flags |= QTextOption.Flag.ShowTabsAndSpaces
        else:
            flags &= ~QTextOption.Flag.ShowTabsAndSpaces
        option.setFlags(flags)
        self.document().setDefaultTextOption(option)

    def whitespace(self):
        return bool(self.document().defaultTextOption().flags() & QTextOption.Flag.ShowTabsAndSpaces)

    def zoom(self, step):
        """Ctrl+= / Ctrl+- one pixel bigger or smaller; 0 — the size it had. The size goes into the style sheet of the
        editor itself: the sheet of the program («QPlainTextEdit#code {font-size: 13px}») would win over setFont."""
        font = self.font()
        current = self.size_px or (font.pixelSize() if font.pixelSize() > 0 else
                                   round(font.pointSizeF() * 96 / 72) if font.pointSizeF() > 0 else 13)
        if not self.base_px:
            self.base_px = current
        px = self.base_px if step == 0 else max(9, min(48, current + step))
        self.size_px = px
        self.setStyleSheet(f'font-size: {px}px;')
        self._margins()
        return px

    def toggle_overwrite(self):
        self.setOverwriteMode(not self.overwriteMode())
        self.statusChanged.emit()

    def status(self):
        cursor = self.textCursor()
        parts = [tr('Стр {}, Кол {}').format(cursor.blockNumber() + 1, cursor.positionInBlock() + 1)]
        if cursor.hasSelection():
            parts.append(tr('выделено {}').format(len(cursor.selectedText())))
        parts.append(tr('строк {}').format(self.blockCount()))
        parts.append(tr('ЗАМ') if self.overwriteMode() else tr('ВСТ'))
        if self.wrapped():
            parts.append(tr('перенос'))
        return ' · '.join(parts)

    # -- keys -------------------------------------------------------------------------------------------------------------
    def keyPressEvent(self, event):
        key, mods = event.key(), event.modifiers()
        ctrl = Qt.KeyboardModifier.ControlModifier
        if key == Qt.Key.Key_Insert and not mods:
            self.toggle_overwrite()
            return
        if key in (Qt.Key.Key_Tab, Qt.Key.Key_Backtab) and not self.isReadOnly():
            many = self.textCursor().hasSelection() and '\u2029' in self.textCursor().selectedText()
            if key == Qt.Key.Key_Backtab or mods & Qt.KeyboardModifier.ShiftModifier:
                self.indent(-1)
                return
            if many:
                self.indent(1)
                return
        if key in (Qt.Key.Key_Up, Qt.Key.Key_Down) and mods == ctrl and sys.platform != 'darwin':  # ⌘↑ of the Mac stays
            bar = self.verticalScrollBar()
            bar.setValue(bar.value() + (-1 if key == Qt.Key.Key_Up else 1))
            return
        super().keyPressEvent(event)

    def changeEvent(self, event):
        from PySide6.QtCore import QEvent

        super().changeEvent(event)
        if event.type() == QEvent.Type.PaletteChange and self.highlighter is not None and self.highlighter.language:
            self.highlighter.set_language(self.highlighter.language)  # the other theme: its colours

    def wheelEvent(self, event):
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom(1 if event.angleDelta().y() > 0 else -1)
            return
        super().wheelEvent(event)


class FindBar(QFrame):
    """Find and replace under the text (as the window of AkelPad, but a bar: the text stays in sight)."""

    def __init__(self, pane):
        super().__init__(pane)
        self.pane = pane
        self.setObjectName('findBar')
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 6, 0, 0)
        column.setSpacing(6)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.find_edit = QLineEdit()
        self.find_edit.setPlaceholderText(tr('Найти'))
        self.find_edit.setClearButtonEnabled(True)
        row.addWidget(self.find_edit, 1)
        self.back_button = self._button('↑', tr('Найти назад · Shift+F3'), lambda: pane.find_next(True))
        self.next_button = self._button('↓', tr('Найти далее · F3'), lambda: pane.find_next(False))
        row.addWidget(self.back_button)
        row.addWidget(self.next_button)
        self.case = QCheckBox(tr('Регистр'))
        self.word = QCheckBox(tr('Слово'))
        self.regex = QCheckBox(tr('Рег. выражение'))
        self.regex.setToolTip(tr('Регулярное выражение Python; в замене $1 или \\1 — первая группа'))
        for box in (self.case, self.word, self.regex):
            box.toggled.connect(lambda *_: pane.search_changed())
            row.addWidget(box)
        self.count = QLabel('')
        self.count.setObjectName('subtitle')
        row.addWidget(self.count)
        self.close_button = self._button('×', tr('Закрыть · Esc'), pane.close_bar)
        row.addWidget(self.close_button)
        column.addLayout(row)
        self.replace_row = QWidget()
        replace = QHBoxLayout(self.replace_row)
        replace.setContentsMargins(0, 0, 0, 0)
        replace.setSpacing(6)
        self.replace_edit = QLineEdit()
        self.replace_edit.setPlaceholderText(tr('Заменить на'))
        replace.addWidget(self.replace_edit, 1)
        self.replace_button = QPushButton(tr('Заменить'))
        self.replace_button.clicked.connect(pane.replace_one)
        self.all_button = QPushButton(tr('Заменить всё'))
        self.all_button.clicked.connect(pane.replace_everything)
        self.within = QCheckBox(tr('В выделенном'))
        replace.addWidget(self.replace_button)
        replace.addWidget(self.all_button)
        replace.addWidget(self.within)
        column.addWidget(self.replace_row)
        self.find_edit.textChanged.connect(lambda *_: pane.search_changed())
        self.find_edit.returnPressed.connect(lambda: pane.find_next(False))
        self.replace_edit.returnPressed.connect(pane.replace_one)

    @staticmethod
    def _button(text, tip, slot):
        item = QPushButton(text)
        item.setToolTip(tip)
        item.setFixedWidth(30)
        item.clicked.connect(slot)
        return item


class EditorPane(QWidget):
    """The editor with its find bar and its status line; save / open_ — what Ctrl+S / Ctrl+O do (None: nothing)."""

    def __init__(self, edit=None, save=None, open_=None, parent=None):  # noqa: C901 — the table of the actions
        super().__init__(parent)
        self.edit = edit if edit is not None else CodeEdit()
        self.save, self.open_ = save, open_
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(4)
        column.addWidget(self.edit, 1)
        self.bar = FindBar(self)
        self.bar.hide()
        column.addWidget(self.bar)
        self.status = QLabel('')
        self.status.setObjectName('subtitle')
        self.status.setToolTip(tr('Горячие клавиши — F1 или правая кнопка мыши по тексту'))
        column.addWidget(self.status)
        self.edit.statusChanged.connect(self.show_status)
        self.edit.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.edit.customContextMenuRequested.connect(self.context_menu)
        self.actions = {
            'find': lambda: self.open_bar(False), 'replace': lambda: self.open_bar(True),
            'next': lambda: self.find_next(False), 'previous': lambda: self.find_next(True),
            'word_next': lambda: self.find_selected(False), 'word_previous': lambda: self.find_selected(True),
            'go_to': self.ask_line, 'duplicate': self._edit(self.edit.duplicate_line),
            'delete_line': self._edit(self.edit.delete_line), 'line_up': self._edit(lambda: self.edit.move_line(-1)),
            'line_down': self._edit(lambda: self.edit.move_line(1)), 'comment': self._edit(self.edit.toggle_comment),
            'upper': self._edit(lambda: self.edit.change_case('upper')),
            'lower': self._edit(lambda: self.edit.change_case('lower')),
            'title': self._edit(lambda: self.edit.change_case('title')), 'date': self._edit(self.edit.insert_date),
            'wrap': lambda: self.edit.set_wrap(not self.edit.wrapped()),
            'whitespace': lambda: self.edit.set_whitespace(not self.edit.whitespace()),
            'overwrite': self.edit.toggle_overwrite, 'zoom_in': lambda: self.edit.zoom(1),
            'zoom_out': lambda: self.edit.zoom(-1), 'zoom_reset': lambda: self.edit.zoom(0), 'keys': self.show_keys,
        }
        # the keys (KEYS) taken by the editor and its bar before the shortcuts of the window (ShortcutOverride): F3, F5,
        # Ctrl+R, Ctrl+S… of the menus of Sextant act on the text while it has the focus
        self.keymap = {}
        for key, _title, keys in KEYS:
            if key and keys:
                self.keymap[QKeySequence(keys).toString()] = self.actions[key]
        for keys, slot in (('Ctrl+H', self.actions['replace']), ('Ctrl+Shift+=', self.actions['zoom_in']),
                           ('Ctrl++', self.actions['zoom_in']), ('Ctrl+S', self._saved if save else None),
                           ('Ctrl+O', self._opened if open_ else None)):
            if slot is not None:  # without a file to save or open the keys stay those of the window
                self.keymap[QKeySequence(keys).toString()] = slot
        for widget in (self.edit, self.bar.find_edit, self.bar.replace_edit):
            widget.installEventFilter(self)
        self.show_status()

    @staticmethod
    def sequence(event):
        """The keys of a key event as QKeySequence prints them (the keypad mark dropped), '' for a modifier alone."""
        from PySide6.QtCore import QKeyCombination

        key = event.key()
        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta, 0) or key > 0x01FFFFFF:
            return ''
        mods = event.modifiers() & ~Qt.KeyboardModifier.KeypadModifier
        if key == Qt.Key.Key_Backtab:  # Shift+Tab arrives as Backtab
            return ''
        return QKeySequence(QKeyCombination(mods, Qt.Key(key))).toString()

    def handler(self, event, watched=None):
        """What these keys do here, or None (Esc only while the bar is open; Insert and Tab are the editor's own)."""
        keys = self.sequence(event)
        if keys == QKeySequence('Esc').toString():
            return self.close_bar if not self.bar.isHidden() else None
        slot = self.keymap.get(keys)
        if slot is None:
            return None
        if watched is not self.edit and keys in (QKeySequence('Insert').toString(), QKeySequence('Ctrl+D').toString(),
                                                 QKeySequence('Ctrl+Shift+K').toString(),
                                                 QKeySequence('Alt+Up').toString(),
                                                 QKeySequence('Alt+Down').toString()):
            return None  # the fields of the bar keep these
        return slot

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent

        if event.type() == QEvent.Type.ShortcutOverride and self.handler(event, watched) is not None:
            event.accept()
            return True
        if event.type() == QEvent.Type.KeyPress:
            slot = self.handler(event, watched)
            if slot is not None:
                slot()
                return True
        return False

    def press(self, keys):
        """The keys pressed in the editor (the tests): True when they did something of KEYS."""
        slot = self.keymap.get(QKeySequence(keys).toString())
        if slot is None:
            return False
        slot()
        return True

    def _opened(self):
        if self.open_:
            self.open_()

    def _edit(self, work):
        return lambda: None if self.edit.isReadOnly() else work()

    def _saved(self):
        if self.save:
            self.save()

    def show_status(self):
        self.status.setText(self.edit.status())

    # -- find ---------------------------------------------------------------------------------------------------------------
    def options(self):
        return {'case': self.bar.case.isChecked(), 'word': self.bar.word.isChecked(),
                'regex': self.bar.regex.isChecked()}

    def open_bar(self, replace=False):
        chosen = self.edit.textCursor().selectedText()
        if chosen and '\u2029' not in chosen:
            self.bar.find_edit.setText(chosen)
        self.bar.replace_row.setVisible(bool(replace) and not self.edit.isReadOnly())
        self.bar.show()
        self.bar.find_edit.setFocus()
        self.bar.find_edit.selectAll()
        self.search_changed()

    def close_bar(self):
        if not self.bar.isHidden():  # isVisible() is False also for a bar of a pane not shown yet
            self.bar.hide()
            self.edit.clear_found()
            self.edit.setFocus()

    def search_changed(self):
        text = self.bar.find_edit.text()
        try:
            found = len(self.edit.all_found(text, **self.options())) if text else 0
        except re.error:
            found = 0
        self.bar.count.setText(tr('найдено: {}').format(found) if text else '')
        if text:
            self.edit.found = self.edit.all_found(text, **self.options())
        else:
            self.edit.found = []
        self.edit._marks()

    def find_next(self, back=False):
        text = self.bar.find_edit.text()
        if not text:
            self.open_bar(False)
            return False
        found = self.edit.find(text, back, **self.options())
        if not found:
            self.bar.count.setText(tr('не найдено'))
        return found

    def find_selected(self, back=False):
        cursor = self.edit.textCursor()
        if not cursor.hasSelection():
            cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        text = cursor.selectedText()
        if not text:
            return False
        self.bar.find_edit.setText(text)
        if back:
            here = self.edit.textCursor()
            here.setPosition(cursor.selectionStart())
            self.edit.setTextCursor(here)
        else:
            self.edit.setTextCursor(cursor)
        return self.edit.find(text, back, **self.options())

    def replace_one(self):
        if self.edit.isReadOnly():
            return False
        try:
            return self.edit.replace_current(self.bar.find_edit.text(), self.bar.replace_edit.text(), **self.options())
        except re.error as exc:
            self.bar.count.setText(tr('ошибка в выражении: ') + str(exc))
            return False

    def replace_everything(self):
        if self.edit.isReadOnly():
            return 0
        try:
            count = self.edit.replace_all(self.bar.find_edit.text(), self.bar.replace_edit.text(),
                                          selection_only=self.bar.within.isChecked(), **self.options())
        except re.error as exc:
            self.bar.count.setText(tr('ошибка в выражении: ') + str(exc))
            return 0
        self.bar.count.setText(tr('заменено: {}').format(count))
        return count

    def ask_line(self, number=None):
        if number is None:
            number, ok = QInputDialog.getInt(self, tr('Перейти к строке'), tr('Строка (1–{}):').format(
                self.edit.blockCount()), self.edit.textCursor().blockNumber() + 1, 1, self.edit.blockCount())
            if not ok:
                return None
        return self.edit.go_to_line(number)

    # -- the menu and the keys ----------------------------------------------------------------------------------------------
    def context_menu(self, point, show=True):
        """The menu of the right button: the standard items of the text, then the actions of the editor in groups
        (MENU_GROUPS), the date and the list of the keys. Returns the menu."""
        from PySide6.QtWidgets import QMenu

        from azimuth.ui import rounded

        menu = self.edit.createStandardContextMenu()
        menu.addSeparator()
        known = {key: (title, keys) for key, title, keys in KEYS if key}
        checks = {'wrap': self.edit.wrapped(), 'whitespace': self.edit.whitespace(),
                  'overwrite': self.edit.overwriteMode()}
        editing = ('duplicate', 'delete_line', 'line_up', 'line_down', 'comment', 'upper', 'lower', 'title', 'date',
                   'replace')

        def put(box, key):
            title, keys = known[key]
            item = box.addAction(tr(title))
            if keys:
                item.setShortcut(QKeySequence(keys))
                item.setShortcutVisibleInContextMenu(True)
            if key in checks:
                item.setCheckable(True)
                item.setChecked(checks[key])
            item.setEnabled(not (self.edit.isReadOnly() and key in editing))
            item.triggered.connect(lambda checked=False, k=key: self.actions[k]())
            return item

        for group, keys in MENU_GROUPS:
            sub = QMenu(tr(group), menu)
            for key in keys:
                put(sub, key)
            rounded(sub)
            menu.addMenu(sub)
        put(menu, 'date')
        menu.addSeparator()
        put(menu, 'keys')
        rounded(menu)
        if show:
            menu.exec(self.edit.mapToGlobal(point))
        return menu

    def keys_text(self):
        lines = [f'{keys}\t{tr(title)}' for key, title, keys in KEYS if key and keys]
        lines += [f'{keys}\t{tr(title)}' for keys, title in OTHER_KEYS]
        return '\n'.join(lines)

    def show_keys(self):
        """F1: the keys of the editor in a small window of the program (not modal: the text stays at hand)."""
        from PySide6.QtWidgets import QDialog, QHeaderView, QTableWidget, QTableWidgetItem

        from azimuth.ui import button

        rows = [line.split('\t') for line in self.keys_text().splitlines()]
        box = QDialog(self)
        box.setWindowTitle(tr('Горячие клавиши редактора'))
        column = QVBoxLayout(box)
        column.setContentsMargins(18, 16, 18, 16)
        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels([tr('Клавиши'), tr('Действие')])
        table.verticalHeader().hide()
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for i, (keys, title) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(QKeySequence(keys).toString(QKeySequence.SequenceFormat.NativeText)
                                                 if '/' not in keys and ' ' not in keys else keys))
            table.setItem(i, 1, QTableWidgetItem(title))
        column.addWidget(table, 1)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(button(tr('Закрыть'), box.accept))
        column.addLayout(row)
        box.resize(520, 560)
        box.show()
        self.keys_window = box
        return box

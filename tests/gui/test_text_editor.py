"""Azimuth/text_editor.py: find and replace, go to a line, the lines duplicated, moved,
deleted, commented, the case, the indent, the date, wrap, overwrite, zoom; the keys taken before those of the window."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QTextCursor

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers

TEXT = '! B3LYP def2-SVP\n%pal nprocs 4 end\n* xyz 0 1\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n*\n'


def _pane(text=TEXT, **kw):
    from azimuth.text_editor import CodeEdit, EditorPane

    return EditorPane(CodeEdit(text), **kw)


def _line(edit, n):
    return edit.document().findBlockByNumber(n).text()


def test_find_and_replace_as_akelpad(app):
    pane = _pane()
    edit = pane.edit
    pane.open_bar(True)
    assert not pane.bar.isHidden() and not pane.bar.replace_row.isHidden()
    pane.bar.find_edit.setText('h ')
    assert pane.bar.count.text() == 'найдено: 2'  # case ignored: the two H atoms
    assert pane.find_next() and edit.textCursor().blockNumber() == 4
    assert pane.find_next() and edit.textCursor().blockNumber() == 5
    assert pane.find_next() and edit.textCursor().blockNumber() == 4  # from the top again
    assert pane.find_next(True) and edit.textCursor().blockNumber() == 5  # Shift+F3
    pane.bar.case.setChecked(True)
    assert pane.bar.count.text() == 'найдено: 0'  # «h » in lower case: none
    pane.bar.find_edit.setText('H ')
    assert pane.bar.count.text() == 'найдено: 2'
    pane.bar.case.setChecked(False)
    pane.bar.regex.setChecked(True)
    pane.bar.find_edit.setText(r'nprocs (\d+)')
    pane.bar.replace_edit.setText(r'nprocs 8 # was $1')
    assert pane.replace_everything() == 1 and _line(edit, 1) == '%pal nprocs 8 # was 4 end'
    edit.undo()  # one step of undo
    assert _line(edit, 1) == '%pal nprocs 4 end'
    pane.bar.regex.setChecked(False)
    pane.bar.find_edit.setText('SV')
    assert pane.bar.count.text() == 'найдено: 1'
    pane.bar.word.setChecked(True)
    assert pane.bar.count.text() == 'найдено: 0'  # a whole word: «SV» of «SVP» is not one
    pane.close_bar()
    assert pane.bar.isHidden() and edit.found == []


def test_the_lines_as_akelpad(app):
    pane = _pane()
    edit = pane.edit
    assert pane.ask_line(4) == 4 and edit.textCursor().blockNumber() == 3
    pane.press('Ctrl+D')
    assert _line(edit, 3) == _line(edit, 4) == 'O 0 0 0' and edit.blockCount() == 9
    pane.press('Ctrl+Shift+K')
    assert edit.blockCount() == 8 and _line(edit, 4) == 'H 0.96 0 0'
    pane.press('Alt+Down')
    assert _line(edit, 4) == 'H -0.24 0.93 0' and _line(edit, 5) == 'H 0.96 0 0' and edit.textCursor().blockNumber() == 5
    pane.press('Alt+Up')
    assert _line(edit, 4) == 'H 0.96 0 0' and edit.textCursor().blockNumber() == 4
    cursor = edit.textCursor()  # the three atoms selected
    cursor.setPosition(edit.document().findBlockByNumber(3).position())
    cursor.setPosition(edit.document().findBlockByNumber(5).position() + 3, QTextCursor.MoveMode.KeepAnchor)
    edit.setTextCursor(cursor)
    pane.press('Ctrl+/')
    assert [_line(edit, k) for k in (3, 4, 5)] == ['# O 0 0 0', '# H 0.96 0 0', '# H -0.24 0.93 0']
    pane.press('Ctrl+/')
    assert _line(edit, 3) == 'O 0 0 0'
    edit.indent(1)
    assert _line(edit, 4) == '    H 0.96 0 0'
    edit.indent(-1)
    assert _line(edit, 4) == 'H 0.96 0 0'
    edit.go_to_line(1)
    cursor = edit.textCursor()
    cursor.setPosition(2)
    cursor.setPosition(7, QTextCursor.MoveMode.KeepAnchor)
    edit.setTextCursor(cursor)
    pane.press('Ctrl+Shift+L')
    assert _line(edit, 0) == '! b3lyp def2-SVP'
    pane.press('Ctrl+Shift+U')
    assert _line(edit, 0) == '! B3LYP def2-SVP'


def test_the_view_the_status_and_the_keys(app):
    pane = _pane()
    edit = pane.edit
    assert pane.status.text().startswith('Стр 1, Кол 1') and 'строк 8' in pane.status.text() and 'ВСТ' in pane.status.text()
    pane.press('Ctrl+U')
    assert edit.wrapped() and 'перенос' in pane.status.text()
    edit.toggle_overwrite()
    assert edit.overwriteMode() and 'ЗАМ' in pane.status.text()
    pane.press('Ctrl+=')
    assert edit.size_px == edit.base_px + 1 and f'{edit.size_px}px' in edit.styleSheet()
    pane.press('Ctrl+-')
    pane.press('Ctrl+-')
    assert edit.size_px == edit.base_px - 1
    pane.press('Ctrl+0')
    assert edit.size_px == edit.base_px
    edit.go_to_line(2)
    cursor = edit.textCursor()
    cursor.movePosition(QTextCursor.MoveOperation.EndOfBlock)
    edit.setTextCursor(cursor)
    assert edit.bracket_pair() == ()
    edit.setPlainText('f(a[1], b)')
    cursor = edit.textCursor()
    cursor.setPosition(1)
    edit.setTextCursor(cursor)
    assert edit.bracket_pair() == (1, 9)
    # the keys of the editor come before the shortcuts of the window (F3, Ctrl+R… of the menus)
    press = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_F3, Qt.KeyboardModifier.NoModifier)
    assert pane.eventFilter(edit, press) and press.isAccepted()
    other = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_F9, Qt.KeyboardModifier.NoModifier)
    assert not pane.eventFilter(edit, other)
    save = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier)
    assert not pane.eventFilter(edit, save)  # no file to save: Ctrl+S stays that of the window
    saved = []
    with_save = _pane(save=lambda: saved.append(True))
    assert with_save.press('Ctrl+S') and saved == [True]
    menu = pane.context_menu(edit.rect().center(), show=False)  # the actions in groups
    groups = [a.menu().title() for a in menu.actions() if a.menu() is not None]
    assert groups == ['Поиск и переход', 'Строки', 'Регистр', 'Вид']
    assert len([a for a in menu.actions() if a.menu() is None and not a.isSeparator()]) <= 12
    box = pane.show_keys()
    assert box.findChildren(__import__('PySide6.QtWidgets', fromlist=['QTableWidget']).QTableWidget)[0].rowCount() > 20
    box.close()
    edit.setReadOnly(True)
    edit.setPlainText('a\nb\n')
    pane.press('Ctrl+D')
    assert edit.toPlainText() == 'a\nb\n'  # read only: nothing changed


def test_the_input_of_sextant_is_edited_in_it(window):
    from azimuth.text_editor import CodeEdit, EditorPane

    assert isinstance(window.preview, CodeEdit) and isinstance(window.preview_pane, EditorPane)
    assert window.preview_pane.save is not None and window.preview_pane.open_ is not None
    assert window.preview.comment in ('#', '!', '*')
    # the colours of another program are no edit of the file
    assert window.preview.toPlainText() and not window.input_edited
    changed = []
    window.preview.textChanged.connect(lambda: changed.append(1))
    for kind in ('gaussian', 'orca', 'psi4', 'orca'):
        window.preview.set_language(kind)
    assert changed == [] and not window.input_edited
    window.program.setCurrentIndex(window.program.findData('gaussian'))
    window.program.setCurrentIndex(window.program.findData('orca'))
    assert 'def2-SVP' in window.preview.toPlainText() and not window.input_edited


def test_the_colours_of_an_input(app):
    from azimuth.text_editor import CodeEdit, guess_language

    edit = CodeEdit('! B3LYP def2-SVP Opt\n%pal nprocs 4 end\n# a comment\n* xyz 0 1\nO 0 0 0\n*\n')
    assert edit.language() is None and edit.document().findBlockByNumber(0).layout().formats() == []
    assert edit.set_language('orca') == 'orca' and edit.comment == '#'
    keywords = edit.document().findBlockByNumber(0).layout().formats()
    assert keywords and any(f.format.font().bold() for f in keywords)  # the line of the keywords, bold
    comment = edit.document().findBlockByNumber(2).layout().formats()
    assert any(f.format.fontItalic() for f in comment)
    assert edit.set_language('gaussian') == 'gaussian' and edit.comment == '!'
    assert edit.set_language(None) is None
    assert guess_language('w.gjf', '') == 'gaussian' and guess_language('pw.in', '&CONTROL\n/') == 'qe'
    assert guess_language('notes.txt', 'hello') is None


def test_the_edit_menu_of_sextant_puts_a_block_and_checks(window):
    # «Правка → Вставить блок» and «Проверить входной файл» of Sextant
    from modules.sextant import input_blocks

    window.program.setCurrentIndex(window.program.findData('orca'))
    window.input_tool.reset_input()
    assert window.preview.language() == 'orca'
    title, text, keyword = input_blocks.BLOCKS['orca'][0]
    new = window.input_tool.insert_block(title, text, keyword)
    assert new is not None and '%pal' in window.preview.toPlainText() and window.input_edited
    content = window.preview.toPlainText()
    assert content.index('%pal') < content.lower().index('* xyz')
    window.preview.undo()  # one step
    assert '%pal\n  nprocs 4' not in window.preview.toPlainText()
    assert isinstance(window.input_tool.check_input_now(), list)
    window.input_tool.reset_input()
    assert not window.input_edited

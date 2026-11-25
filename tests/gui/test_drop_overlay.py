"""The grey veil while files are dragged onto the window (azimuth/drop_overlay.py): an icon and a caption that
depend on the section."""

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def drag(kind, window, paths):
    from PySide6.QtCore import QMimeData, QPoint, QPointF, Qt, QUrl
    from PySide6.QtGui import QDragEnterEvent, QDragLeaveEvent, QDropEvent

    data = QMimeData()
    data.setUrls([QUrl.fromLocalFile(str(p)) for p in paths])
    if kind == 'enter':
        event = QDragEnterEvent(QPoint(50, 50), Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton,
                                Qt.KeyboardModifier.NoModifier)
        window.dragEnterEvent(event)
    elif kind == 'leave':
        window.dragLeaveEvent(QDragLeaveEvent())
    else:
        event = QDropEvent(QPointF(50, 50), Qt.DropAction.CopyAction, data, Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier)
        window.dropEvent(event)
    return data


def test_veil_says_what_the_section_takes(window, app, tmp_path, monkeypatch):
    path = tmp_path / 'water.xyz'
    path.write_text('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n', encoding='utf-8')
    monkeypatch.setattr(window, 'confirm_replace', lambda *a, **k: True)
    texts = {}
    for section in (0, 1, 2):
        window.navigate(section)
        drag('enter', window, [path])
        assert not window.drop_overlay.isHidden() and window.drop_overlay.geometry() == window.rect()  # offscreen: the window is not shown
        window.drop_overlay.grab()
        texts[section] = (window.drop_overlay.title, window.drop_overlay.extensions)
        drag('leave', window, [path])
        assert window.drop_overlay.isHidden()
    assert texts[0][0] == 'Перенесите сюда файлы структуры' and 'PDB' in texts[0][1]
    assert texts[1][0].startswith('Перенесите сюда входные') and '.inp' in texts[1][1]
    assert texts[2][0] == 'Перенесите сюда расчётные файлы' and '.log' in texts[2][1]
    window.navigate(0)
    drag('enter', window, [path])
    drag('drop', window, [path])
    app.processEvents()  # the file is opened on the next turn of the event loop, after the drop is answered
    assert window.drop_overlay.isHidden() and len(window.molecule.atoms) == 3

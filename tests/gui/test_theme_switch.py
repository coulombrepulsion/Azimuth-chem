"""The theme switched by the property of the windows looks as the sheet of that theme alone.

Oracles: the picture of the window under the old way — QApplication.setStyleSheet with the dark sheet alone
(DARK_STYLE + the part made at run time) — taken in the same window; the new way must give the same pixels; and the
switch must not set the sheet of the application again.
"""

from tests.gui_support import *  # noqa: F401,F403


def settled(window, app, tries=60):
    """The picture of the window once it has stopped changing: a window just shown lays itself out over several
    passes of the events (the bar of the tabs was still narrow, with its scroll buttons, and the cards 10 px lower
    after one pass: two pictures of one theme differ by the place of things, not by their colours). Two equal pictures
    in a row, 20 ms apart."""
    import time

    before = None
    for _ in range(tries):
        app.processEvents()
        picture = window.grab().toImage()
        if before is not None and picture == before:
            return picture
        before = picture
        time.sleep(0.02)
    return before


def test_dark_theme_by_property_is_the_dark_sheet(window, app):
    from azimuth import app as appmod
    from azimuth import theme_sheet

    window.resize(1200, 800)
    window.show()
    window.theme.setCurrentIndex(0)
    app.processEvents()
    sheet = app.styleSheet()
    assert sheet == appmod.theme_style_sheet()
    window.theme.setCurrentIndex(1)
    app.processEvents()
    assert app.styleSheet() is not None and app.styleSheet() == sheet  # no new sheet: only the property
    assert window.window().property(theme_sheet.PROPERTY) is True
    new = settled(window, app)
    try:
        app.setStyleSheet(appmod.DARK_STYLE + appmod.Studio.theme_extra(True))
        app.processEvents()
        old = settled(window, app)
    finally:
        app.setStyleSheet(sheet)
        window.theme.setCurrentIndex(0)
        app.processEvents()
    assert new.size() == old.size()
    differ = sum(1 for y in range(0, new.height(), 4) for x in range(0, new.width(), 4) if new.pixel(x, y) != old.pixel(x, y))
    assert differ == 0


def test_the_bars_of_tabs_count_their_tabs_again_after_the_switch(window, app):
    # every bar of tabs of the window is told that the style changed, and none is
    # left narrower than its tabs
    from PySide6.QtCore import QEvent, QObject
    from PySide6.QtWidgets import QTabBar

    class Heard(QObject):
        def __init__(self):
            super().__init__()
            self.bars = set()

        def eventFilter(self, watched, event):
            if event.type() == QEvent.Type.StyleChange:
                self.bars.add(watched)
            return False

    window.resize(1200, 800)
    window.show()
    window.theme.setCurrentIndex(0)
    settled(window, app)
    bars = [bar for bar in window.findChildren(QTabBar)]
    assert len(bars) >= 2
    heard = Heard()
    for bar in bars:
        bar.installEventFilter(heard)
    try:
        for index in (1, 0):
            heard.bars.clear()
            window.theme.setCurrentIndex(index)
            settled(window, app)
            assert heard.bars == set(bars)
            for bar in bars:
                if bar.isVisible() and bar.count():
                    assert bar.width() >= bar.sizeHint().width(), bar.objectName()
    finally:
        for bar in bars:
            bar.removeEventFilter(heard)
        window.theme.setCurrentIndex(0)
        app.processEvents()


def test_a_window_put_into_another_follows_the_theme(window, app):
    # the window of the sections, marked dark while it was a window of its
    # own, is put into the hub (as HubWindow does); back in the light theme it must look as before the dark one
    from PySide6.QtWidgets import QVBoxLayout, QWidget

    from azimuth import theme_sheet

    window.theme.setCurrentIndex(0)
    window.resize(1200, 800)
    host = QWidget()
    try:
        window.theme.setCurrentIndex(1)  # dark while on its own
        app.processEvents()
        assert window.property(theme_sheet.PROPERTY) is True
        QVBoxLayout(host).addWidget(window)
        host.resize(1200, 800)
        host.show()
        app.processEvents()
        window.theme.setCurrentIndex(0)
        app.processEvents()
        assert not window.property(theme_sheet.PROPERTY) and not host.property(theme_sheet.PROPERTY)
        light = window.grab().toImage()
        # the backgrounds of the dark theme (the page, the cards, the buttons) are nowhere in the light picture
        dark = {0xff11151c, 0xff191f28, 0xff212833}
        found = sum(1 for y in range(0, light.height(), 4) for x in range(0, light.width(), 4) if light.pixel(x, y) in dark)
        assert found == 0
    finally:
        window.setParent(None)
        host.deleteLater()

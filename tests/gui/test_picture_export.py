"""One way to save a picture in every window (azimuth/picture_export.py, 0.249.2): PNG twice the size or SVG, on white
with dark ink whatever the theme; the palette of the widget given back."""

from pathlib import Path

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_a_dark_widget_is_saved_on_white(app, tmp_path):
    from PySide6.QtGui import QColor, QImage, QPainter, QPalette
    from PySide6.QtWidgets import QWidget

    from azimuth import picture_export
    from modules.spectrum.views.spectrum_common import _export_widget

    class Drawing(QWidget):  # as the plots of the program: the ground and the ink from the palette
        def paintEvent(self, event):
            p = QPainter(self)
            p.fillRect(self.rect(), self.palette().base())
            p.fillRect(10, 10, 20, 20, self.palette().text().color())
            p.end()

    drawing = Drawing()
    drawing.resize(120, 80)
    dark = QPalette(drawing.palette())
    dark.setColor(QPalette.ColorRole.Base, QColor('#151b23'))
    dark.setColor(QPalette.ColorRole.Text, QColor('#e6e9ef'))
    drawing.setPalette(dark)
    path = picture_export.save(drawing, str(tmp_path / 'plot.png'))
    image = QImage(path)
    assert image.width() == 240 and image.pixelColor(100, 100) == QColor('#ffffff')  # white ground, twice the size
    assert image.pixelColor(40, 40) == QColor(picture_export.INK)  # dark ink
    assert drawing.palette().color(QPalette.ColorRole.Base) == QColor('#151b23')  # the theme of the window kept
    with picture_export.on_white(drawing):
        assert drawing.palette().color(QPalette.ColorRole.Base) == QColor('#ffffff')
    assert drawing.palette().color(QPalette.ColorRole.Text) == QColor('#e6e9ef')
    svg = tmp_path / 'plot.svg'
    _export_widget(drawing, svg, 'Azimuth · test', [(1, 2)], ['x', 'y'])  # the «Экспорт…» of Spectrum the same way
    assert '#ffffff' in svg.read_text(encoding='utf-8').lower() and '#e6e9ef' not in svg.read_text(encoding='utf-8')
    try:
        picture_export.save(drawing, str(tmp_path / 'plot.jpg'))
    except ValueError as exc:
        assert 'PNG' in str(exc)
    else:
        raise AssertionError('a JPEG is not offered')


def test_the_buttons_say_the_same():
    # «Сохранить рисунок…» with the picture of a picture in every window that saves only a picture
    import re

    root = Path(__file__).resolve().parents[2]
    for name in ('modules/compass/actions/morphology_window.py', 'modules/compass/actions/brillouin_window.py',
                 'modules/sextant/descriptor_view.py', 'modules/compass/actions/qe_plots.py'):
        text = (root / name).read_text(encoding='utf-8')
        assert "tr('Сохранить рисунок…')" in text and 'Сохранить картинку' not in text, name
    for folder in ('modules', 'azimuth', 'hub'):
        for path in (root / folder).rglob('*.py'):
            text = path.read_text(encoding='utf-8')
            assert not re.search(r"tr\('Сохранить (картинку|изображение)", text), path

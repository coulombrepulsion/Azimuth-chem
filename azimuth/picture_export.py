"""The picture of a plot or a drawing for a report: one way in every window of the program.

§1 PURPOSE
    0.249.2 (the owner, 2026-11-27: «Пройдись по предыдущим пунктам, где стиль нужно одинаковый везде сделать»): the
    windows saved their pictures each in its own way — «Сохранить картинку», «рисунок», «изображение», PNG alone or PNG
    and SVG, the dark ground of the dark theme or white. Now: «Сохранить рисунок…» (a picture only) or «Экспорт…» (a
    picture or a table), PNG twice the size on the screen or SVG, always on white with dark ink whatever the theme — a
    report is printed on white.
§2 ALGORITHM
    The widget is drawn with a light palette (white Window and Base, dark Text and WindowText): the plots of the
    program take their colours from their palette (a dark palette — light lines), so they draw themselves for white; the
    palette of the widget is given back afterwards. PNG — a QImage PICTURE_SCALE times the widget, filled white; SVG —
    QSvgGenerator of the size of the widget, a white rectangle under the drawing.
§3 INTERFACE
    LABEL, TITLE, FILTER, FILTER_TABLE; on_white(widget) — a context: the widget drawn for white inside it;
    save(widget, path, title='') -> path (ValueError for another suffix, OSError
    when the file is not written); ask(parent, name, table=False, title=None) -> path | None (the dialog of the system;
    a name without a suffix gets .png).
§7 TESTS tests/gui/test_qe_phonon_plot.py::test_a_plot_is_saved_as_a_white_picture_for_a_report,
    tests/gui/test_picture_export.py.
"""

from contextlib import contextmanager
from pathlib import Path

LABEL = 'Сохранить рисунок…'
TITLE = 'Сохранить рисунок'
FILTER = 'PNG (*.png);;SVG (*.svg)'
FILTER_TABLE = 'PNG (*.png);;SVG (*.svg);;CSV (*.csv)'
PICTURE_SCALE = 2  # a PNG twice its size on the screen: sharp in a report
WHITE, INK = '#ffffff', '#1b2230'


@contextmanager
def on_white(widget):
    """The widget drawn for white while inside: a light palette, its own given back afterwards (for the windows that
    draw their pictures themselves — the diagram of a reaction, the maps of a field)."""
    from PySide6.QtGui import QColor, QPalette

    old = QPalette(widget.palette())  # a copy: the palette of the widget is changed below
    light = QPalette(old)
    for role, color in ((QPalette.ColorRole.Window, WHITE), (QPalette.ColorRole.Base, WHITE),
                        (QPalette.ColorRole.Text, INK), (QPalette.ColorRole.WindowText, INK)):
        light.setColor(role, QColor(color))
    widget.setPalette(light)
    try:
        yield widget
    finally:
        widget.setPalette(old)


def save(widget, path, title=''):
    """The widget into a PNG or SVG file on white, whatever the theme; -> path."""
    from PySide6.QtCore import QPoint, QSize
    from PySide6.QtGui import QColor, QImage, QPainter

    from azimuth.i18n import tr

    suffix = Path(path).suffix.lower()
    if suffix not in ('.png', '.svg'):
        raise ValueError(tr('Поддерживаются PNG и SVG.'))
    with on_white(widget):
        if suffix == '.svg':
            from PySide6.QtSvg import QSvgGenerator

            device = QSvgGenerator()
            device.setFileName(str(path))
            device.setSize(QSize(widget.width(), widget.height()))
            device.setViewBox(widget.rect())
            device.setTitle(title)
            painter = QPainter(device)
            if not painter.isActive():
                raise OSError(tr('Не удалось создать SVG.'))
            painter.fillRect(widget.rect(), QColor(WHITE))
            widget.render(painter, QPoint(0, 0))
            painter.end()
        else:
            image = QImage(widget.width() * PICTURE_SCALE, widget.height() * PICTURE_SCALE, QImage.Format.Format_ARGB32)
            image.fill(QColor(WHITE))
            painter = QPainter(image)
            painter.scale(PICTURE_SCALE, PICTURE_SCALE)
            widget.render(painter, QPoint(0, 0))
            painter.end()
            if not image.save(str(path)):
                raise OSError(tr('Не удалось сохранить PNG.'))
    return path


def ask(parent, name, table=False, title=None):
    """Where to put the picture (or, table, the picture or the table); -> path or None."""
    from PySide6.QtWidgets import QFileDialog

    from azimuth.i18n import tr

    path, _ = QFileDialog.getSaveFileName(parent, tr(title or TITLE), str(name), FILTER_TABLE if table else FILTER)
    if not path:
        return None
    if not Path(path).suffix:
        path += '.png'
    return path

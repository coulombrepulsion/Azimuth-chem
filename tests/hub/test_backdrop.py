"""hub/backdrop.py and its place in the window: light, shadows, isolines, the gyroscope, the glass (0.245.0)."""

import math

import numpy as np
import pytest
from PySide6.QtCore import QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QRegion
from PySide6.QtWidgets import QApplication

from hub import backdrop


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def _image(width, height):
    image = QImage(width, height, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(0)
    return image


def test_the_molecule_of_the_home_page_is_nitrobenzene():
    atoms = backdrop.nitrobenzene()
    weights = sorted(w for _, _, w in atoms)
    assert weights == [1.0] * 5 + [6.0] * 6 + [7.0] + [8.0] * 2  # C6H5NO2
    px = backdrop.SCALE
    (nx, ny, _), oxygens = atoms[11], atoms[12:]
    for ox, oy, _ in oxygens:
        assert math.hypot(ox - nx, oy - ny) == pytest.approx(1.22 * px)
    a = [math.atan2(oy - ny, ox - nx) for ox, oy, _ in oxygens]
    assert abs(math.degrees(a[0] - a[1])) == pytest.approx(125.0)
    # the nitro group is on the page (x > 0, y < 0 from the bottom edge), the ring mostly below and left of it
    assert nx > 0 and ny < 0 and all(ox > 0 and oy < 0 for ox, oy, _ in oxygens)
    ring_x, ring_y = backdrop.ANCHOR
    assert ring_x < 0 and ring_y > 0


def test_marching_squares_find_a_circle():
    xs = ys = np.arange(-50.0, 51.0, 1.0)
    x, y = np.meshgrid(xs, ys)
    field = np.exp(-np.hypot(x, y) / 10.0)
    pieces = backdrop.segments(field, xs, ys, math.exp(-3.0))  # the circle r = 30
    assert len(pieces) > 100
    r = np.hypot(pieces[:, 0], pieces[:, 1])
    assert np.all(np.abs(r - 30.0) < 0.6)
    assert backdrop.segments(field, xs, ys, 2.0).shape == (0, 4)  # above everything: no line


def test_the_isolines_are_few_and_kept(app):
    lines = backdrop.isolines()
    assert len(lines) == len(backdrop.LEVELS) == 10 and backdrop.isolines() is lines  # computed once
    assert all(not path.isEmpty() for path, _, _ in lines)
    assert all(0 < alpha < 0.3 and 0 < width <= 1.1 for _, alpha, width in lines)
    image = _image(1200, 760)
    painter = QPainter(image)
    backdrop.draw_isolines(painter, 760, QColor('#2a62b8'))
    painter.end()
    lower_left = sum(image.pixelColor(x, y).alpha() for x in range(0, 500, 4) for y in range(400, 760, 4))
    upper_right = sum(image.pixelColor(x, y).alpha() for x in range(880, 1200, 4) for y in range(0, 300, 4))
    assert lower_left > 0 and upper_right == 0  # the lines keep away from the azimuth in the upper right corner


def test_the_gyroscope_starts_turns_and_comes_to_rest_flat():
    gyro = backdrop.Gyro()
    assert gyro.mode == 'rest' and not gyro.moving and gyro.angles == [0.0, 0.0, 0.0]
    gyro.leave()
    assert gyro.mode == 'rest'  # nothing to stop
    gyro.start()
    assert gyro.moving
    gyro.advance(0.05)
    first = list(gyro.angles)
    assert 0 < first[0] < gyro.SPEED[0] * 0.05  # it rises from zero
    for _ in range(80):
        gyro.advance(0.05)
    assert gyro.angles[0] > first[0] and gyro.angles[1] > first[1] and gyro.angles[2] < first[2]
    gyro.leave()
    assert gyro.mode == 'settle'
    for _ in range(round(gyro.SETTLE / 0.05) + 2):
        gyro.advance(0.05)
    assert gyro.mode == 'rest'
    for angle, turn in zip(gyro.angles, gyro.FLAT):  # flat; the inner ring a whole turn — the needle to the north
        assert angle % turn == pytest.approx(0.0, abs=1e-9) or angle % turn == pytest.approx(turn)
    # back to the home page: the second start is quicker than the first
    gyro.start()
    assert gyro.rise == gyro.RISE < gyro.RISE_FIRST
    gyro.advance(0.6)
    assert gyro.moving and gyro.angles != [0.0, 0.0, 0.0]


def test_the_lines_of_the_gyroscope_are_of_one_width_and_of_even_strength_when_flat(app):
    gyro = backdrop.Gyro()
    for _, frame, _ in gyro.lines():
        assert frame in (0, 1, 2)
    picture = gyro.picture(QColor('#2a62b8'))
    assert picture.width() == picture.height() == gyro.size() == round(gyro.SIDE * gyro.GROW)
    image = picture.toImage()
    half = gyro.size() // 2
    r = round(gyro.OUTER * gyro.GROW)  # 0.248.0: 1.5 times larger
    # flat: the outer ring is equally strong on the left and on the right (there was a jump of the light)
    left = max(image.pixelColor(x, half + 20).alpha() for x in range(half - r - 5, half - r + 5))
    right = max(image.pixelColor(x, half + 20).alpha() for x in range(half + r - 5, half + r + 5))
    assert left > 0 and abs(left - right) <= 8
    # turned: the near half of a ring is stronger than the far one, but the strength changes smoothly
    gyro.angles = [60.0, 0.0, 0.0]
    x, y, z = gyro.project(gyro.placed(np.array([[150.0, 0, 0], [-150.0, 0, 0]]), 0))
    assert z[0] < 0 < z[1]  # turned about the vertical axis
    assert x[1] < half < x[0] or x[0] < half < x[1]


def test_light_and_shadows_darken_only_round_the_panels(app):
    image = _image(400, 300)
    painter = QPainter(image)
    backdrop.shade(painter, QRectF(0, 0, 400, 300))
    painter.end()
    assert image.pixelColor(5, 5).alpha() == 0 and image.pixelColor(395, 295).alpha() > 0  # the light from the upper left
    image = _image(400, 300)
    painter = QPainter(image)
    panel = QRect(100, 100, 200, 100)
    painter.setClipRegion(QRegion(image.rect()).subtracted(QRegion(panel)))
    backdrop.shadows(painter, [panel])
    painter.end()
    assert image.pixelColor(200, 150).alpha() == 0  # never on the panel
    below, above = image.pixelColor(200, 100 + 100 + 3).alpha(), image.pixelColor(200, 100 - 3).alpha()
    assert below > above > 0  # moved down
    assert image.pixelColor(200, 290).alpha() == 0


def test_the_glass_shows_the_background_moved(app):
    drawn = []

    def draw(painter):
        drawn.append(painter.transform().m11())
        painter.fillRect(QRectF(0, 0, 60, 60), QColor('#2a62b8'))

    picture = backdrop.glass_picture(draw, 600, 300, 120)
    assert picture.width() == math.ceil(720 / backdrop.GLASS) and drawn == [pytest.approx(1 / backdrop.GLASS)]
    image = _image(600, 300)
    painter = QPainter(image)
    backdrop.draw_glass(painter, picture, 120)
    painter.end()
    assert image.pixelColor(30, 30).alpha() > 0
    assert image.pixelColor(3, 3).alpha() < image.pixelColor(30, 30).alpha()  # moved: nothing at the very corner


def test_the_window_turns_the_gyroscope_on_the_home_page_only(app, tmp_path):
    from PySide6.QtCore import QSettings

    from hub.chrome import Ornament, PanelGlass
    from hub.window import HubWindow
    import hub.window_sections as sections

    window = HubWindow(preferences=QSettings(str(tmp_path / 'h.ini'), QSettings.Format.IniFormat))
    try:
        window.resize(1200, 800)
        window.show()
        window.show_section(sections.HOME, animate=False)
        app.processEvents()
        ornament = window.ornament
        assert isinstance(ornament, Ornament) and ornament.gyro.mode == 'run' and ornament.timer.isActive()
        assert ornament.timer.interval() == ornament.TICK
        ornament._tick()
        place = ornament.gyro_rect()  # its centre where the centre of the flat dial was (0.248.0)
        assert place.center().x() == pytest.approx(ornament.width() - 70, abs=2) and place.center().y() == pytest.approx(70, abs=2)
        window.show_section('sextant', animate=False)
        app.processEvents()
        assert ornament.gyro.mode == 'settle'
        for _ in range(200):
            ornament.gyro.advance(0.05)
        ornament.intro = None  # the needle of Sextant has settled too (0.246.0)
        ornament._tick()
        assert ornament.gyro.mode == 'rest' and not ornament.timer.isActive()  # no timer while it stands
        assert isinstance(window.panel_art, PanelGlass) and window.panel_art.source() is ornament
        window.panel_art.grab()  # draws the background through the side panel
        surfaces = ornament.surface_region()
        assert all(surfaces.contains(p.center()) for p in ornament.panels)
        window.show_section(sections.HOME, animate=False)
        assert ornament.gyro.mode == 'run' and ornament.gyro.rise == ornament.gyro.RISE
        window.hide()
        assert not ornament.timer.isActive()  # a hidden window does not turn it
    finally:
        window.studio.dirty = False
        for document in window.studio.all_documents():
            document.dirty = False
        window.close()
        window.deleteLater()


def test_the_picture_of_a_section_moves_when_the_section_opens(app):
    # 0.246.0: the needle of Compass swings and settles, the index arm of Sextant too, the bands of Spectrum rise
    from hub.chrome import Ornament

    ornament = Ornament()
    ornament.resize(900, 700)

    def ink():
        image = _image(900, 700)
        painter = QPainter(image)
        ornament._art(painter)
        painter.end()
        return image

    for section in ('compass', 'sextant', 'spectrum'):
        ornament.set_section('home')
        ornament.set_section(section)
        assert ornament.intro == 0.0 and ornament.corner_rect().bottom() == 699
        opening = ink()
        ornament.intro = None
        rest = ink()
        assert opening != rest, section  # the picture at the start differs from the one at rest
    ornament.set_section('spectrum')
    assert ornament.intro is None  # the same section again: no motion
    # at rest after INTRO: the motion has died away
    assert abs(Ornament.swing(Ornament.INTRO, 34.0, 1.0, 4.4)) < 3.0
    ornament.set_section('compass')
    ornament.gyro.mode = 'rest'  # only the picture of the section moves
    ornament.show()
    assert ornament.timer.isActive()
    ornament._clock -= 0.0
    for _ in range(80):
        ornament._clock -= 0.05
        ornament._tick()
        if ornament.intro is None:
            break
    assert ornament.intro is None and not ornament.timer.isActive()  # no timer once it has settled
    ornament.hide()


def test_the_isolines_are_whole_smooth_lines():
    # 0.248.0 (the owner: «изолинии какие-то пиксельные слишком»): the pieces of the squares joined into lines
    xs = ys = np.arange(-50.0, 51.0, 1.0)
    x, y = np.meshgrid(xs, ys)
    field = np.exp(-np.hypot(x, y) / 10.0)
    lines = backdrop.chains(backdrop.segments(field, xs, ys, math.exp(-3.0)))
    longest = max(lines, key=len)
    assert len(longest) > 200 and longest[0] == longest[-1]  # the circle, closed
    assert sum(len(line) for line in lines) - len(lines) == len(backdrop.segments(field, xs, ys, math.exp(-3.0)))


def test_round_corners_of_a_card_are_page(app):
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame, QWidget

    from hub.chrome import Ornament

    host = QWidget()
    host.resize(400, 300)
    card = QFrame(host)
    card.setObjectName('card')
    card.setGeometry(100, 100, 200, 100)
    ornament = Ornament(host)
    ornament.setGeometry(host.rect())
    host.show()
    region = ornament.surface_region()
    assert region.contains(QPoint(200, 150)) and not region.contains(QPoint(101, 101))  # the corner is not the card
    assert region.contains(QPoint(112, 101))
    host.close()

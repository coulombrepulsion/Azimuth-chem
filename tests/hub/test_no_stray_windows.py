"""No widget of the window shows itself as a window of its own (2026-11-28, Windows: «на секунду появляется какое-то
маленькое окно» as the panel of the density opened and as Compass went from Crystal back to Molecule). A widget made
without a parent and shown (setVisible(True)) before it is put into a layout is a top-level window for that moment —
on a Mac it is not painted in time, on Windows it flickers with its frame."""

import time
from pathlib import Path

from PySide6.QtCore import QEvent, QObject
from PySide6.QtWidgets import QApplication, QWidget

from tests.hub.test_hub import app, hub  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]
WINDOWS = ('OrbitalsDialog',)  # the windows a step opens on purpose


class Watch(QObject):
    def __init__(self, main):
        super().__init__()
        self.main, self.seen, self.stage = main, [], ''

    def eventFilter(self, obj, event):
        if (event.type() == QEvent.Type.Show and isinstance(obj, QWidget) and obj.isWindow() and obj is not self.main
                and type(obj).__name__ not in WINDOWS):
            self.seen.append(f'{self.stage}: {type(obj).__name__} {obj.size().toTuple()}')
        return False


def wait(app, seconds):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()
        time.sleep(0.01)


def test_the_panel_of_the_density_shows_no_window_of_its_own(hub, app):
    hub.resize(1300, 800)
    hub.show()
    hub.show_section('compass', animate=False)
    wait(app, 0.3)
    studio = hub.studio
    watch = Watch(hub)
    QApplication.instance().installEventFilter(watch)
    try:
        text = (ROOT / 'tests' / 'data' / 'orbitals' / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8')
        dialog = studio.open_orbitals_text(text, 'water.molden')
        homo, _ = dialog.orbital_set.frontier()
        dialog.select(homo)
        watch.stage = 'the orbital to Compass'
        dialog.show_orbital()
        wait(app, 0.6)
        for mode in ('crystal', 'molecule'):
            watch.stage = f'Compass · {mode}'
            studio.crystal_tool.set_compass_mode(mode)
            wait(app, 0.6)
    finally:
        QApplication.instance().removeEventFilter(watch)
    assert watch.seen == []


def test_crystal_and_back_keep_the_model_in_place_and_the_surface_lit(hub, app):
    # 0.249.19, the owner: going «Кристалл → Молекула» with the panel of the result open, the molecule «продолжает
    # сдвигать каждый раз вправо», and «сбрасывается выделение, какая функция построена». The shift of a tab is kept
    # without the half of the drawer (it was added again at every opening); the surface on the model stays lit
    hub.resize(1300, 800)
    hub.show()
    hub.show_section('compass', animate=False)
    wait(app, 0.3)
    studio = hub.studio
    text = (ROOT / 'tests' / 'data' / 'orbitals' / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8')
    dialog = studio.open_orbitals_text(text, 'water.molden')
    homo, _ = dialog.orbital_set.frontier()
    dialog.select(homo)
    dialog.show_orbital()
    wait(app, 0.8)
    drawer = studio.density_drawer
    assert studio.viewer.inset > 0
    # a surface of the list as if built and on the model
    item = drawer.surface_items()[1]
    key = drawer.current_choice(item)
    drawer.surfaces_list.setCurrentItem(item)
    source = {'kind': 'choice', 'title': item.text(0), 'orbitals': drawer.orbital_set}
    studio.surface_source = source
    drawer.shown, drawer.shown_source = ('choice', key), source
    drawer.refresh_lights()
    assert item.font(0).bold()
    before = studio.viewer.pan.x()
    for _ in range(3):
        studio.crystal_tool.set_compass_mode('crystal')
        wait(app, 0.5)
        studio.crystal_tool.set_compass_mode('molecule')
        wait(app, 0.8)
        assert abs(studio.viewer.pan.x() - before) < 1.0, (before, studio.viewer.pan.x())
    if studio.surface_source is source:  # still on the model: still lit and chosen
        lit = next(i for i in drawer.surface_items() if drawer.current_choice(i) == key)
        assert drawer.shown == ('choice', key) and lit.font(0).bold() and drawer.current_choice() == key

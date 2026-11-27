"""Shared fixtures and helpers of the window tests (tests/gui/test_gui_*.py; split from test_gui.py on 2026-11-08):
the application, a Studio window with the water of the examples, the model shown, fake Multiwfn. The test modules
take them with «from tests.gui_support import *» — the fixtures app and window, show_model, leaf_actions, csv_rows,
fake_multiwfn and the names imported here."""

import os
import re

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
if os.name == 'nt':  # offscreen on Windows knows no fonts of the system: the widgets got another font, other widths
    os.environ.setdefault('QT_QPA_FONTDIR', os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts'))
os.environ['AZIMUTH_MULTIWFN_SEARCH'] = '0'  # only the fake Multiwfn a test gives — never the installed one
from pathlib import Path
import pytest
from dataclasses import replace
from PySide6.QtWidgets import QApplication
from azimuth.app import Studio, STYLE, atomic_write
from tests.fake_programs import fake_program, q


@pytest.fixture(scope='module')
def app():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)  # the font of the system, as the program
    yield app


def leaf_actions(menu):
    """The items of a menu and of its submenus (the values at the atoms are grouped in submenus)."""
    found = []
    for action in menu.actions():
        found.append(action)
        if action.menu() is not None:
            found.extend(leaf_actions(action.menu()))
    return found


# the settings of the look of the model, kept by every window in the settings file the tests of a run share. A test that
# changed one and left it (test_hide_hydrogens_in_every_display_mode left «spacefill») changed every window opened
# after it: a test that counted the drawn bonds found none, and failed only in some orders of the tests (2026-11-23)
VIEW_KEYS = re.compile(r'^(display_mode|background|grid|palette|element_colors|multiple_bonds|show_bonds|show_lengths|'
                       r'show_hbonds|start_scheme|display_schemes|atom_labels|atom_scale|axes_|bond_|label_|measure_|'
                       r'guide_|hbond_)')


def fresh_view():
    """The settings of the look left by the tests before removed: a window starts with the defaults of the program."""
    from azimuth.settings import open_settings

    store = open_settings()
    for key in store.allKeys():
        if VIEW_KEYS.match(key):
            store.remove(key)
    store.sync()


@pytest.fixture
def window(app):
    fresh_view()
    window = Studio(example=True, probe_machine=False)  # start from the water; 2 processes, 1000 MB
    # the built-in renderer whatever the program remembers, without touching that preference
    window.viewer.engine = 'raster'
    window.viewer.set_native(False)
    window.viewer._model_image = None
    if hasattr(window, 'engine_action'):
        window.engine_action.blockSignals(True)
        window.engine_action.setChecked(False)
        window.engine_action.blockSignals(False)
    yield window
    window.dirty = False
    for d in window.all_documents():  # the tabs of both subsections of Compass
        d.dirty = False
    window.close()
    window.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent

    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


# five tests stood here and were collected again in each of the 8 modules that
# take «import *» (40 runs of 5 scenarios); their own places are test_gui_sextant.py and test_gui_settings.py. Here
# only fixtures and helpers — a function test_* here would run once per module again.


from PySide6.QtCore import Qt, QPoint, QEvent
from PySide6.QtTest import QTest
from azimuth.core import Molecule, Atom, read_project, project_text, read_xyz, EXAMPLES
from modules.compass.chemistry.builder import connections


def show_model(window, app):
    window.show()
    window.navigate(0)
    window.structure_tabs.setCurrentIndex(0)
    app.processEvents()


def csv_rows(path):
    """The rows of a table of the analysis, the decimal comma read as a point."""
    from modules.spectrum.wavefunction import field_tables

    header, rows = field_tables.read_csv(path)
    return [header] + [[c.replace(',', '.') for c in row] for row in rows]


def fake_multiwfn(tmp_path):
    """A Multiwfn that answers the topology (2 …) and the surface analysis (12 …) with the files recorded by
    Multiwfn 2026.7.15 for the water of examples/6-orbitals/water_mp2_gaussian16.fchk."""
    data = Path(__file__).parent / 'data' / 'multiwfn'
    fake = fake_program(tmp_path, f'''
if answer(0) == '2':
    cp({q(data / "water_fchk_CPprop_2026.7.15.txt")}, 'CPprop.txt')
    cat({q(data / "water_fchk_topology_2026.7.15.txt")})
if answer(0) == '12':
    gunzip({q(data / "water_fchk_esp_vtx.txt.gz")}, 'vtx.txt')
    gunzip({q(data / "water_fchk_esp_surf.cub.gz")}, 'surf.cub')
    cat({q(data / "water_fchk_esp_2026.7.15.txt")})
''')
    return fake

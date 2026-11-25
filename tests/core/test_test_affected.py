"""tools/test_affected.py — the tests a change touches.

Oracles: the imports of the code themselves (test_convergence.py imports modules/spectrum/analysis/convergence.py;
test_iupac.py reaches it only through the main window, which is not followed) and the rules of §2 (a document chooses
nothing; the conftest of the tests — everything; a data set — the tests that name it; the translations — their tests).
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(ROOT / 'tools'))

import test_affected as ta  # noqa: E402


def test_a_reader_chooses_its_tests_and_the_window_of_its_section():
    files, reasons, notes = ta.select(['modules/spectrum/analysis/convergence.py'])
    assert 'tests/spectrum/test_convergence.py' in files and 'tests/gui/test_gui_spectrum.py' in files
    assert 'tests/compass/test_iupac.py' not in files  # only through the main window
    assert 'tests/gui/test_gui_compass.py' not in files and 'tests/gui/test_gui_sextant.py' not in files
    assert reasons['tests/gui/test_gui_spectrum.py'].startswith('окно раздела') and not notes


def test_what_is_not_code_and_what_is_under_everything():
    files, _, notes = ta.select(['docs/manual/ru.md'])
    assert files == [] and 'не код программы' in notes[0]
    everything, _, _ = ta.select(['tests/conftest.py'])
    assert len(everything) == len(ta._tests())


def test_data_translations_and_a_test_itself():
    files, _, _ = ta.select(['tests/data/spherical/README.md'])
    assert 'tests/spectrum/test_spherical_order.py' in files and 'tests/spectrum/test_xtb.py' not in files
    assert set(ta.select(['azimuth/locale/en.json'])[0]) == set(ta.TRANSLATIONS)
    assert ta.select(['tests/spectrum/test_xtb.py'])[0] == ['tests/spectrum/test_xtb.py']


def test_a_shared_module_of_the_window_runs_every_scenario():
    files, _, _ = ta.select(['azimuth/ui.py'])
    assert {'tests/gui/test_gui_compass.py', 'tests/gui/test_gui_sextant.py', 'tests/hub/test_hub.py'} <= set(files)


def test_relative_imports_are_followed():
    assert ta.module_name('modules/spectrum/readers/__init__.py') == 'modules.spectrum.readers'
    assert 'modules.spectrum.readers.results' in ta.graph()['modules.spectrum.readers.orca']

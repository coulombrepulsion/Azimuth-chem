# ruff: noqa: F811 — the fixtures app and hub are imported from test_hub
"""The real menu items and buttons reach their handlers.
1. Every item of the menus of every section (with the submenus) that is not a submenu itself has a receiver of
   triggered / toggled: an item left unconnected (its handler lost in a move) is found by name.
2. The buttons of the calculation window that 0.108.28 left doing nothing — «Пропустить», «QTAIM для всех»,
   «Дескрипторы и logK…» — and «Входной файл» are clicked; the method of the window's part must be called.
The oracle is Qt's own count of receivers and a record of the calls, not the code of the handlers."""

import pytest

pytest.importorskip('PySide6')

from PySide6.QtCore import SIGNAL  # noqa: E402

from azimuth.i18n import to_source  # noqa: E402
from tests.hub.test_hub import app, hub  # noqa: E402,F401 — the shared fixtures


def leaves(menu):
    for action in menu.actions():
        if action.isSeparator():
            continue
        if action.menu() is not None:
            yield from leaves(action.menu())
        else:
            yield action


def connected(action):
    return (action.receivers(SIGNAL('triggered()')) + action.receivers(SIGNAL('triggered(bool)'))
            + action.receivers(SIGNAL('toggled(bool)')))


@pytest.mark.parametrize('section', ['compass', 'crystal', 'sextant', 'spectrum'])
def test_every_menu_item_of_a_section_is_connected(hub, app, section):
    hub.show_section(section, animate=False)
    app.processEvents()
    loose = []
    for menu_button in hub.header.menu_buttons:
        if menu_button.menu() is None:
            continue
        for action in leaves(menu_button.menu()):
            if action.isEnabled() and not connected(action):
                loose.append(f'{to_source(menu_button.text())} → {to_source(action.text())}')
    assert not loose, 'menu items with no handler: ' + '; '.join(loose)


def test_the_buttons_of_the_calculation_window_reach_the_parts(hub, monkeypatch):
    studio = hub.studio
    calls = []
    for name in ('skip_batch_item', 'batch_qtaim'):
        monkeypatch.setattr(studio.batch_tool, name, lambda *a, name=name: calls.append(name))
    monkeypatch.setattr(studio, 'show_input_card', lambda *a: calls.append('show_input_card'))
    window = studio.job_window  # made with the window, one for each place (SextantWorkspace)
    for button in (window.skip_button, window.qtaim_button, window.input_button):
        button.setEnabled(True)
        button.click()
    assert calls == ['skip_batch_item', 'batch_qtaim', 'show_input_card']
    # «Дескрипторы и logK…» only in the menu «Расчёт»
    assert not hasattr(window, 'descriptors_button')

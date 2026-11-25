"""The button «Орбитали» belongs to the wave function only."""

import numpy as np

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_the_legend_of_the_dos_is_on_a_plate_in_the_emptier_corner_and_nothing_goes_under_the_axis(app):
    from modules.spectrum.views.dos_view import DosPlot

    x = np.linspace(-20, 8, 600)
    peaks = lambda centres: sum(np.exp(-((x - c) / 0.3) ** 2) for c in centres)  # noqa: E731
    for centres, right in (((-18, -10, -5), True), ((2, 4, 6, 7), False)):
        total = peaks(centres)
        negative = 0.3 * total - 0.6 * peaks(centres[-1:])  # a share below zero (an empty orbital)
        plot = DosPlot()
        plot.resize(900, 360)
        plot.set_data({'x': x, 'total': total, 'parts': [('C', 0.7 * total), ('H', negative)], 'levels': [],
                       'homo': None})
        plot.grab()
        box = plot.legend_box
        assert (box.left() > plot.width() / 2) == right  # the corner where the curves are lower
        image = plot.grab().toImage()
        base = plot.height() - plot.BOTTOM
        # under the axis only its ticks and its numbers: no curve drawn there (the share below zero is taken in)
        coloured = [image.pixelColor(xx, yy) for xx in range(plot.LEFT + 2, plot.width() - plot.RIGHT, 3)
                    for yy in range(base + 14, base + 20)]
        assert not any(c.red() > 180 and c.green() < 120 for c in coloured)


def test_qtaim_the_batch_button_beside_the_search_and_the_explanation_in_a_question_mark(window):
    panel = window.topology_panel
    row = panel.aim_row
    widgets = [row.itemAt(k).widget() for k in range(row.count()) if row.itemAt(k).widget() is not None]
    assert widgets.index(panel.find_button) < widgets.index(window.project_qtaim_button)
    assert 'Найти критические точки' in window.project_qtaim_button.toolTip()
    assert panel.aim_help is not None and panel.aim_help.help.startswith('Критические точки плотности')
    assert widgets.index(panel.folder_button) + 1 == widgets.index(panel.aim_help)  # «?» right of the folder
    # no long text over the table any more
    from PySide6.QtWidgets import QLabel

    assert not any(label.text().startswith('Критические точки плотности') for label in panel.findChildren(QLabel))


def test_the_tools_of_the_result_are_in_the_top_row_by_group(window, app):
    tabs = window.result_tabs
    top = tabs.tools
    holders = [top.itemAt(k).widget() for k in range(top.count())]
    assert window.wave_tools in holders and window.energy_tools in holders
    # the folder at the
    # right of the row of the tabs of the result; the row over the page only when it has something
    assert window.result_folder_button not in holders
    assert window.result_folder_button.parentWidget() is window.result_top_row
    tabs.setCurrentIndex(0)  # «Результат»: the reaction diagram, not the orbitals
    assert not window.energy_tools.isHidden() and window.wave_tools.isHidden()
    tabs.setTabVisible(window.field_tab, True)
    tabs.setCurrentIndex(window.field_tab)  # «Волновая функция»: the orbitals and the way to Compass
    assert window.energy_tools.isHidden() and not window.wave_tools.isHidden()
    assert window.orbitals_button.parentWidget() is window.wave_tools
    assert window.reaction_button.parentWidget() is window.energy_tools


def test_the_row_over_the_page_goes_when_it_is_empty(window, app):
    # «Колебания и ИК» — no list of pages, no tool: no row (it held the folder alone)
    tabs = window.result_tabs
    window.reaction_button.setVisible(False)
    tabs.setTabVisible(window.vibrations_tab, True)
    tabs.setCurrentIndex(window.vibrations_tab)
    window.refresh_result_tools()
    if tabs.chooser.isHidden():
        assert tabs.bar.isHidden()
    window.reaction_button.setVisible(True)
    tabs.setCurrentIndex(0)
    window.refresh_result_tools()
    assert not tabs.bar.isHidden()

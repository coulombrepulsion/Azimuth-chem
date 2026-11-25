"""«Справка → Справочник» (azimuth/handbook_window.py): the tabs, the search, the factor put into the IR spectrum of
Spectrum, «?» at the solvent of Sextant."""

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_the_tabs_the_search_and_the_conversion(app):
    from azimuth.handbook_window import TABS, HandbookDialog

    dialog = HandbookDialog(None, 'units')
    assert [dialog.tabs.tabText(i) for i in range(dialog.tabs.count())] == [
        'Единицы и константы', 'Растворители', 'Множители частот', 'Опытные данные']
    dialog.value.setText('1')
    rows = {dialog.converted.item(r, 0).text(): dialog.converted.item(r, 1).text()
            for r in range(dialog.converted.rowCount())}
    assert rows['эВ'] == '27,21138625' and rows['нм'] == '45,56335253'  # 1 Eh, the decimal comma
    dialog.value.setText('abc')
    assert dialog.converted.rowCount() == 0  # nothing to convert, nothing shown
    dialog.show_tab('solvents')
    dialog.search.setText('вода')
    shown = [r for r in range(dialog.solvents.rowCount()) if not dialog.solvents.isRowHidden(r)]
    assert [dialog.solvents.item(r, 0).text() for r in shown] == ['Вода']
    dialog.search.clear()
    assert not any(dialog.solvents.isRowHidden(r) for r in range(dialog.solvents.rowCount()))
    assert len(TABS) == 4
    dialog.close()


def test_a_factor_chosen_in_the_handbook_goes_into_the_spectrum(window, app):
    chosen = []
    from azimuth.handbook_window import HandbookDialog

    dialog = HandbookDialog(None, 'factors', apply_factor=chosen.append, level=('B3LYP', '6-31G*'))
    assert dialog.apply_button.isVisibleTo(dialog)
    assert dialog.apply_chosen() == 0.960 and chosen == [0.960]
    dialog.close()
    vibrations = window.vibrations
    opened = vibrations.open_factor_table()
    assert opened is window.handbook_dialog and opened.tabs.currentIndex() == 2
    opened.choose_level('HF', 'cc-pVDZ')
    opened.apply_chosen()
    assert abs(vibrations.ir_scale.value() - 0.908) < 1e-9 and vibrations.ir_scale_on.isChecked()
    opened.close()
    without = HandbookDialog(None, 'factors')
    assert not without.apply_button.isVisibleTo(without) and without.apply_chosen() is None  # from the menu: no target
    without.close()


def test_the_solvent_of_sextant_and_the_measured_data(window, app):
    window.navigate(1)
    window.solvent_help.click()
    assert window.handbook_dialog.tabs.currentIndex() == 1  # the solvents
    window.handbook_dialog.close()
    from azimuth.handbook_window import open_handbook

    dialog = open_handbook(window, 'experiment', formula='CH2O')
    assert dialog.formula_url('NIST Chemistry WebBook').endswith('Formula=CH2O&NoIon=on&Units=SI')
    dialog.close()

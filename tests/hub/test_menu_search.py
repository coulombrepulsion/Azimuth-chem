# ruff: noqa: F811 — the fixtures app and hub are imported from test_hub
"""Hub/menu_search.py and hub/sidebar_search.py — the search of the side panel, its results, the item shown."""

from PySide6.QtCore import Qt

from tests.hub.test_hub import app, hub  # noqa: F401 — the fixtures


def _search(hub):
    """The search of the side panel (0.248.0; the magnifier of the row of the menus until then)."""
    from azimuth.i18n import to_source

    helps = next(b.menu() for b in hub.header.menu_buttons if to_source(b.text()) == 'Справка')
    assert not hasattr(helps, 'search_field') and not hasattr(hub.header, 'search_button')
    return hub.search


def test_the_search_of_the_help_finds_a_menu_item_and_shows_it(hub):
    from hub import menu_search

    hub.show_section('crystal', animate=False)
    found = menu_search.find(menu_search.entries(hub.header, hub.studio), 'хиршфельд')
    labels = [e.label() for e in found]
    assert any(label.endswith('Межмолекулярные взаимодействия ▸ Поверхность Хиршфельда…') for label in labels)
    assert menu_search.find(menu_search.entries(hub.header), 'КОНТАКТЫ водородные')  # case ignored, the words in any order
    assert menu_search.find(menu_search.entries(hub.header), '') == []
    search = _search(hub)
    search.open(animate=False)
    field = search.field
    field.setText('vc-relax')  # the words of the tooltips and of the paths count too
    field.setText('поверхность хиршфельда')
    assert search.results.count() and 'Поверхность Хиршфельда' in search.results.item(0).text()
    entry = next(e for e in found if e.title.startswith('Поверхность Хиршфельда'))
    last = menu_search.reveal(hub.header, entry, step=0)
    assert last is not None and entry.action in last.actions()
    for _ in range(20):
        from PySide6.QtWidgets import QApplication

        QApplication.processEvents()
    assert last.activeAction() is entry.action or last.isVisible()
    for button in hub.header.menu_buttons:
        button.menu().close()
    field.setText('такого пункта нет нигде')
    assert [search.results.item(k).text() for k in range(search.results.count())] == ['Ничего не найдено']
    field.clear()
    assert search.results.isHidden()
    search.close(animate=False)

def test_the_search_finds_the_buttons_of_the_window(hub):
    from hub import menu_search

    hub.show_section('crystal', animate=False)
    hub.studio.show()
    found = menu_search.find(menu_search.entries(hub.header, hub.studio), 'Результаты расчётов')
    assert any(e.widget is hub.studio.crystal_results_button or e.action is not None for e in found)


def test_the_magnifier_stands_in_the_side_panel_over_the_languages(hub, app):
    # the owner, 2026-11-27: «Лупа пусть будет расположена в левой панели над языком, в виде иконки внутри квадратика со
    # скругленными краями, и при нажатии поле выдвигается из квадратика»
    from hub.sidebar_search import WIDTH

    hub.show_section('compass', animate=False)
    hub.show()
    app.processEvents()
    search = hub.search
    button = search.button
    assert button.isVisible() and button.toolTip() == 'Поиск по меню и кнопкам'
    # a button of the panel as the others: the same name of the style and the same width (0.248.3)
    assert button.objectName() == 'nav' and button.width() == hub.theme_button.width() and not button.icon().isNull()
    languages = hub.language_row
    assert button.mapTo(hub, button.rect().bottomLeft()).y() < languages.mapTo(hub, languages.rect().topLeft()).y()
    assert button.window() is hub and hub.sidebar.isAncestorOf(button)
    search.open(animate=False)  # the field out of the square, to the right
    assert search.is_open() and search.panel.width() == WIDTH and search.panel.x() == button.mapTo(hub, button.rect().topLeft()).x()
    assert search.field.isVisible()
    search.field.setText('хиршфельд')
    assert search.results.isVisible() and search.results.geometry().bottom() < search.panel.geometry().top()  # over it
    search.close(animate=False)
    assert search.panel.isHidden() and search.field.text() == '' and search.results.isHidden()
    # a click elsewhere on the panel puts it away (0.248.3)
    from PySide6.QtCore import QPoint
    from PySide6.QtTest import QTest

    search.open(animate=False)
    QTest.mouseClick(hub.sidebar, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(30, 140))
    app.processEvents()
    assert not search._opening
    search.close(animate=False)
    hub.help_search_shortcut.activated.emit()  # Ctrl+Shift+/
    app.processEvents()
    assert search.panel.isVisible()
    search.close(animate=False)
    for section in ('sextant', 'spectrum', 'crystal', 'home'):  # the same square in every section
        hub.show_section(section, animate=False)
        app.processEvents()
        assert button.isVisible(), section

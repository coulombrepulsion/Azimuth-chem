# ruff: noqa: F811 — the fixtures app and hub are imported from test_hub
"""Hub/menu_search.py — the field of «Справка», its results, the item shown where it is."""

from tests.hub.test_hub import app, hub  # noqa: F401 — the fixtures


def _help(hub):
    """The menu of the magnifier at the right end of the row of the menus (in «Справка» until 0.244.0)."""
    from azimuth.i18n import to_source

    helps = next(b.menu() for b in hub.header.menu_buttons if to_source(b.text()) == 'Справка')
    assert not hasattr(helps, 'search_field') and 'Поиск по меню' not in [to_source(a.text()) for a in helps.actions()]
    assert hub.header.search_button.menu() is hub.header.search_menu
    assert hub.header.search_button.property('quail_icon') in (None, 'search') and not hub.header.search_button.icon().isNull()
    assert hub.header.search_button not in hub.header.menu_buttons  # the search does not list itself
    return hub.header.search_menu


def test_the_search_of_the_help_finds_a_menu_item_and_shows_it(hub):
    from hub import menu_search

    hub.show_section('crystal', animate=False)
    found = menu_search.find(menu_search.entries(hub.header, hub.studio), 'хиршфельд')
    labels = [e.label() for e in found]
    assert any(label.endswith('Межмолекулярные взаимодействия ▸ Поверхность Хиршфельда…') for label in labels)
    assert menu_search.find(menu_search.entries(hub.header), 'КОНТАКТЫ водородные')  # case ignored, the words in any order
    assert menu_search.find(menu_search.entries(hub.header), '') == []
    helps = _help(hub)
    field = helps.search_field
    field.setText('vc-relax')  # the words of the tooltips and of the paths count too
    field.setText('поверхность хиршфельда')
    results = helps.search_results()
    assert results and 'Поверхность Хиршфельда' in results[0].text()
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
    assert [a.text() for a in helps.search_results()] == ['Ничего не найдено']
    field.clear()
    assert helps.search_results() == []


def test_the_search_finds_the_buttons_of_the_window(hub):
    from hub import menu_search

    hub.show_section('crystal', animate=False)
    hub.studio.show()
    found = menu_search.find(menu_search.entries(hub.header, hub.studio), 'Результаты расчётов')
    assert any(e.widget is hub.studio.crystal_results_button or e.action is not None for e in found)


def test_the_magnifier_stands_at_the_end_of_the_row_of_the_menus(hub, app):
    # the owner, 2026-11-27: the search out of «Справка», a magnifier at the right on the level of the menus
    from hub import menu_search

    hub.show_section('compass', animate=False)
    hub.show()
    app.processEvents()
    header = hub.header
    button = header.search_button
    assert button.isVisible() and button.toolTip() == 'Поиск по меню и кнопкам'
    last = header.menu_buttons[-1]
    assert button.mapTo(header, button.rect().topLeft()).x() > last.mapTo(header, last.rect().topRight()).x()
    assert abs(button.mapTo(header, button.rect().center()).y() - last.mapTo(header, last.rect().center()).y()) <= 3
    assert header.width() - button.mapTo(header, button.rect().topRight()).x() <= 24  # at the right end of the row
    menu = menu_search.open_help(header)  # Ctrl+Shift+/
    assert menu is header.search_menu
    app.processEvents()
    menu.close()
    for section in ('sextant', 'spectrum', 'crystal'):  # the same magnifier in every section with menus
        hub.show_section(section, animate=False)
        app.processEvents()
        assert header.search_button.isVisible() and header.search_menu is menu, section

# ruff: noqa: F811 — the fixtures app and hub are imported from test_hub
"""Hub/menu_search.py — the field of «Справка», its results, the item shown where it is."""

from tests.hub.test_hub import app, hub  # noqa: F401 — the fixtures


def _help(hub):
    from azimuth.i18n import to_source

    return next(b.menu() for b in hub.header.menu_buttons if to_source(b.text()) == 'Справка')


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

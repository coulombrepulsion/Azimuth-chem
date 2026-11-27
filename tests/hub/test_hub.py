"""Azimuth hub window offscreen (hub/window.py §7): sections, Studio pages, theme, sidebar,
fade, shortcuts; the Atlas is on the site — its item and card open it in the browser.

Oracles: hub/modules.json (section order, titles, Studio page numbers) read independently
of the window; the addresses of azimuth/site.py.
"""

import json
import os
import time

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QSettings
from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from azimuth.app import STYLE
from azimuth.paths import ROOT
import hub.window as hub_window
import hub.window_sections as hub_window_sections
from hub.window import HubWindow, NARROW, WIDE

SECTIONS = json.loads((ROOT / 'hub' / 'modules.json').read_text(encoding='utf-8'))


def wait_for(app, condition, seconds=40):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.02)
    return False


@pytest.fixture(scope='module')
def app():
    app = QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)
    yield app


@pytest.fixture(autouse=True)
def site_opened(monkeypatch):
    """The Atlas of the site is never opened in a browser by the tests — the addresses asked are kept."""
    from azimuth import site

    class Asked(list):
        pass

    asked = Asked()
    # the window gives its theme too — kept apart, the addresses asked stay those of the language and the topic
    asked.themes = []
    monkeypatch.setattr(site, 'open_atlas', lambda language='ru', topic=None, theme=None: asked.themes.append(theme)
                        or asked.append(site.atlas(language, topic)) or True)
    return asked


@pytest.fixture
def hub(app, tmp_path):
    preferences = QSettings(str(tmp_path / 'hub.ini'), QSettings.Format.IniFormat)
    window = HubWindow(preferences=preferences)
    window.started_collapsed = window.collapsed
    window.set_collapsed(False, animate=False)  # tests read the names in the open panel
    theme = window.studio.theme.currentIndex()
    yield window
    window.studio.theme.setCurrentIndex(theme)
    window.studio.dirty = False
    for d in window.studio.all_documents():  # the tabs of both subsections
        d.dirty = False
    window.close()
    window.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_sidebar_follows_registry(hub):
    assert list(hub.buttons) == [item['id'] for item in SECTIONS]
    for item in SECTIONS:
        assert hub.buttons[item['id']].text() == item['title']


def test_atlas_stands_apart_with_an_arrow(hub, app):
    # a line under the Atlas, «↗» on its button — in the open panel and on the narrow rail
    from hub.chrome import SiteArrow

    atlas = hub.buttons['atlas']
    others = [b for ident, b in hub.buttons.items() if ident != 'atlas']
    assert isinstance(hub.site_arrow, SiteArrow) and hub.site_arrow.parentWidget() is atlas
    assert not any(b.findChildren(SiteArrow) for b in others)  # only the Atlas leaves the window
    assert atlas.accessibleName() == 'Атлас' and 'azimuth-chem.com' in atlas.toolTip()  # the name stays the name
    hub.show()
    for collapsed in (False, True):
        hub.set_collapsed(collapsed, animate=False)
        app.processEvents()
        rule = hub.atlas_rule.mapTo(hub.sidebar, hub.atlas_rule.rect().topLeft()).y()
        below = atlas.mapTo(hub.sidebar, atlas.rect().bottomLeft()).y()
        above = min(b.mapTo(hub.sidebar, b.rect().topLeft()).y() for b in others)
        assert below < rule < above and hub.atlas_rule.height() == 1 and hub.atlas_rule.isVisible()
        arrow = hub.site_arrow.geometry()
        assert atlas.rect().contains(arrow) and hub.site_arrow.isVisible()
        # seen: inside the part of the button the panel shows (on the rail the buttons are cut, not narrowed)
        assert atlas.mapTo(hub.sidebar, arrow.topRight()).x() < hub.sidebar.width() - 4
        assert (arrow.width() == 11) == collapsed  # the small one in the corner of the icon on the rail
    before = hub.dark
    for _ in range(2):  # in the colour of the panel's accent, seen on the light panel too (not white)
        hub.toggle_theme()
        app.processEvents()
        hub._style_sidebar()
        assert hub.site_arrow.color.name() == ('#6ea2f0' if hub.dark else '#2a62b8')
        # the line under the Atlas is the line under the name
        assert hub.atlas_rule.styleSheet().replace('atlasRule', 'brandRule') == hub.brand_rule.styleSheet()
    assert hub.dark is before
    hub.set_collapsed(True, animate=False)


def test_sections_switch_hosts_pages_and_title(hub, site_opened):
    for item in SECTIONS:
        if item['id'] == 'atlas':  # the site in the browser; the window stays where it was
            before = hub.current
            hub.show_section('atlas', animate=False)
            assert hub.current == before and site_opened[-1] == 'https://ru.azimuth-chem.com/atlas/?lang=ru'
            assert not hub.buttons['atlas'].isCheckable() and not hub.buttons['atlas'].isChecked()
            continue
        hub.show_section(item['id'], animate=False)
        assert hub.current == item['id']
        assert hub.windowTitle() == 'Азимут · ' + item['title']
        assert [b.isChecked() for b in hub.buttons.values()] == [i['id'] == item['id'] for i in SECTIONS]
        assert hub.stack.currentWidget() is hub.studio
        assert hub.studio.stack.currentIndex() == item['page']
    assert hub.preferences.value('hub_section') == SECTIONS[-1]['id']
    assert not hasattr(hub, 'atlas') and hub.ready  # no Atlas in the window


def test_studio_navigation_moves_hub_selection(hub):
    hub.show_section('compass', animate=False)
    target = next(i for i in SECTIONS if i['page'] == 1)
    hub.studio.navigate(1)
    assert hub.current == target['id'] and hub.buttons[target['id']].isChecked()


def test_shared_molecule_between_studio_sections(hub):
    hub.show_section('compass', animate=False)
    molecule = hub.studio.molecule
    hub.show_section('spectrum', animate=False)
    hub.show_section('compass', animate=False)
    assert hub.studio.molecule is molecule


def test_unknown_section_rejected(hub, app):
    with pytest.raises(ValueError):
        hub.show_section('unknown')
    with pytest.raises(ValueError):
        HubWindow('unknown')


def test_theme_button_switches_studio(hub):
    before = hub.dark
    hub.theme_button.click()
    assert hub.dark is (not before)
    assert hub.studio.theme.currentIndex() == int(not before)
    hub.theme_button.click()
    assert hub.dark is before


def test_collapse_keeps_tooltips(hub):
    assert hub.started_collapsed  # starts closed
    hub.set_collapsed(True)
    assert hub.sidebar.width() == NARROW and hub.rail.width() == NARROW
    assert all(b.text() == '' and b.toolTip() for b in hub.buttons.values())
    assert hub.brand.isHidden() and not hub.logo.isHidden() and not hub.logo.icon().isNull()
    hub.set_collapsed(False)
    assert hub.sidebar.width() == WIDE and hub.rail.width() == NARROW and not hub.brand.isHidden()
    assert [b.text() for b in hub.buttons.values()] == [i['title'] for i in SECTIONS]


def test_fade_runs_and_finishes(hub, app, monkeypatch):
    monkeypatch.setattr(hub_window_sections, 'FADE_MS', 80)  # the switch of the sections is there (0.222.30)
    hub.show()
    app.processEvents()
    hub.show_section('compass')
    assert hub.fader.isVisible() and hub.current == 'compass'
    hub.show_section('sextant')  # a second switch during the fade
    assert hub.current == 'sextant'
    assert wait_for(app, lambda: not hub.fader.isVisible(), 3)


def test_shortcuts_follow_registry_order(hub, site_opened):
    assert len(hub.shortcuts) == len(SECTIONS)
    hub.shortcuts[2].activated.emit()
    assert hub.current == SECTIONS[2]['id']
    hub.shortcuts[0].activated.emit()  # Ctrl+1: the Atlas of the site
    assert hub.current == SECTIONS[2]['id'] and len(site_opened) == 1


def test_the_atlas_opens_on_the_site(hub, app, site_opened):
    # the Atlas left the window for the site — its item of the panel and its card on
    # the home page open it in the browser, in the language of the program; Compass, Sextant and Spectrum need nothing
    # of it (azimuth/symmetry_engine)
    hub.show_section('compass', animate=False)
    hub.buttons['atlas'].click()
    assert hub.current == 'compass' and hub.buttons['compass'].isChecked() and not hub.buttons['atlas'].isChecked()
    hub.set_language('zh')
    hub.show_section(hub_window.HOME, animate=False)
    QTest.mouseClick(hub.home.cards['atlas'], Qt.MouseButton.LeftButton)
    assert hub.current == hub_window.HOME
    hub.set_language('ru')
    assert site_opened == ['https://ru.azimuth-chem.com/atlas/?lang=ru', 'https://www.azimuth-chem.com/atlas/?lang=zh']
    assert site_opened.themes == ['dark' if hub.dark else 'light'] * 2  # in the theme of the program
    assert 'azimuth-chem.com' in hub.buttons['atlas'].toolTip()
    assert not hasattr(hub_window, 'AtlasPanel') and not hasattr(hub, 'atlas')


def test_language_switch_relabels_sidebar(hub, app):
    hub.show_section('compass', animate=False)
    hub.set_language('en')
    assert [b.text() for b in hub.buttons.values()] == [i['en'] for i in SECTIONS]
    assert hub.windowTitle() == 'Azimuth · ' + SECTIONS[1]['en'] and hub.brand.accessibleName() == 'Azimuth'
    assert not hub.brand.pixmap().isNull()  # the wordmark
    assert hub.preferences.value('hub_language') == 'en' and hub.language_buttons['en'].isChecked()
    with pytest.raises(ValueError):
        hub.set_language('de')
    hub.set_collapsed(True)  # narrow panel: one button that cycles
    assert [c for c, b in hub.language_buttons.items() if not b.isHidden()] == ['en']
    hub.language_buttons['en'].click()
    assert hub.language == 'zh' and hub.windowTitle() == '方位 · ' + SECTIONS[1]['zh']
    hub.set_collapsed(False)
    hub.set_language('ru')
    assert hub.windowTitle() == 'Азимут · ' + SECTIONS[1]['title']


def test_logo_click_opens_home_and_panel_stays_a_rail(hub, app):
    # the drawer is switched off; the application icon opens the home page
    hub.set_collapsed(True, animate=False)
    hub.show_section('compass', animate=False)
    hub.logo.click()
    assert hub.current == hub_window.HOME and hub.stack.currentWidget() is hub.home
    assert hub.collapsed and hub.sidebar.width() == NARROW and hub.header.isHidden()
    assert not any(b.isChecked() for b in hub.buttons.values())
    assert hub.windowTitle() == 'Азимут · Главная' and hub.logo.toolTip() == 'Главная'
    QTest.mouseClick(
        hub.sidebar,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(NARROW // 2, hub.sidebar.height() // 2 + 40),
    )
    assert hub.collapsed  # a click on the rail does not open it
    assert all(b.toolTip() for b in hub.buttons.values())  # names are in the tooltips
    assert hub.theme_button.toolTip() and hub.about_button.toolTip()


def test_home_page_blocks_open_sections(hub, app):
    hub.show_section(hub_window.HOME, animate=False)
    assert list(hub.home.cards) == [item['id'] for item in SECTIONS]
    # no Quill and no greeting; what the program is
    # stands under its name, above «Продолжить» and the sections
    assert not any(hasattr(hub.home, name) for name in ('quill', 'bubble', 'hello', 'hello2'))
    assert hub.home.intro.text().startswith('«Азимут» — учебная программа')
    column = hub.home.intro.parentWidget().layout()
    assert column.indexOf(hub.home.intro) < column.indexOf(hub.home.continue_title) < column.indexOf(hub.home.sections_title)
    assert not hub.home.mark.pixmap().isNull()
    assert hub.home.motto.text() == 'ПРОЛОЖИТЕ КУРС К РЕЗУЛЬТАТУ'  # the tagline under the name (0.248.0)
    before = hub.dark
    hub.toggle_theme()  # the icon follows the theme
    assert hub.home.app_icon.property('variant') == ('dark' if hub.dark else 'light')
    hub.toggle_theme()
    assert hub.dark is before and hub.home.app_icon.property('variant') == ('dark' if before else 'light')
    # 0.248.0: the name only, no list of functions; one card of Compass — the molecule and the crystal its halves
    from hub.home import CompassCard

    compass = hub.home.cards['compass']
    assert isinstance(compass, CompassCard) and compass.title.text() == 'Компас'
    assert hub.home.cards['crystal'] is compass.parts['crystal'] and compass.parts['compass'].title.text() == 'Молекула'
    assert compass.parts['crystal'].title.text() == 'Кристалл'
    # Compass the whole width on top, the other three in one row of cards of one height (0.248.2)
    row = [hub.home.cards[i] for i in ('atlas', 'sextant', 'spectrum')]
    hub.resize(1300, 860)
    hub.show()
    QApplication.processEvents()
    assert len({card.height() for card in row}) == 1 and len({card.y() for card in row}) == 1
    assert compass.y() < row[0].y() and compass.width() > 2 * row[0].width()
    assert compass.x() == row[0].x() and compass.geometry().right() == row[-1].geometry().right()
    for item in SECTIONS:
        card = hub.home.cards[item['id']]
        assert card.title.text()
        # a sentence about the section (0.249.3); Compass — under its name and under each of its halves
        assert card.text.text() and len(card.text.text()) < 160 and not card.text.isHidden()
        if item['id'] not in ('compass', 'crystal'):
            assert card.title.text() == item['title']
        QTest.mouseClick(card if item['id'] != 'compass' else compass.parts['compass'], Qt.MouseButton.LeftButton)
        assert hub.current == (hub_window.HOME if item['id'] == 'atlas' else item['id'])  # the site
        hub.show_section(hub_window.HOME, animate=False)
    assert compass.text.text().startswith('Здесь строится') and compass.parts['compass'].text.text() == 'Построить и изменить молекулу'
    hub.set_language('en')
    assert hub.home.intro.text().startswith('Azimuth is') and hub.home.cards['atlas'].title.text() == 'Atlas'
    hub.set_language('ru')


def test_starts_on_home_then_last_section(app, tmp_path):
    # the program always starts on the home page, also after a section was open last time
    preferences = QSettings(str(tmp_path / 'fresh.ini'), QSettings.Format.IniFormat)
    for expected, then in ((hub_window.HOME, 'sextant'), (hub_window.HOME, None)):
        window = HubWindow(preferences=preferences)
        try:
            assert window.current == expected
            if then:
                window.show_section(then, animate=False)
        finally:
            window.studio.dirty = False
            window.close()
            window.deleteLater()
            QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def test_panel_opens_on_click_and_closes_on_page_click(hub, app, monkeypatch):
    monkeypatch.setattr(hub_window, 'PANEL_EXPANDABLE', True)  # the drawer, when switched back on
    hub.show()
    app.processEvents()
    hub.set_collapsed(True, animate=False)
    QTest.mouseClick(
        hub.sidebar,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
        QPoint(NARROW // 2, hub.sidebar.height() // 2 + 40),
    )
    assert not hub.collapsed and wait_for(app, lambda: hub.sidebar.width() == WIDE, 3)
    # the width reaches WIDE (rounded) a frame before the slide ends: wait for the last frame
    assert wait_for(app, lambda: hub.brand.progress == 1.0, 3)
    assert len(hub.brand._cuts) == 8  # А З И М У Т + star, all shown
    assert hub.panel.width() == WIDE  # laid out once, clipped by the frame
    assert hub.sidebar.geometry().right() > hub.content.geometry().left()  # over the page, not pushing it
    assert hub.scrim.isVisible()  # a veil over the page
    QTest.mouseClick(hub.scrim, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(600, 300))
    assert hub.collapsed and wait_for(app, lambda: hub.sidebar.width() == NARROW, 3)
    assert wait_for(app, lambda: not hub.scrim.isVisible(), 2) and hub.brand.isHidden()
    hub.set_collapsed(False, animate=False)
    hub.buttons['sextant'].click()  # choosing a section closes the panel
    assert hub.current == 'sextant' and hub.collapsed


def test_section_header_for_studio_sections(hub):
    hub.show_section(hub_window.HOME, animate=False)
    assert hub.header.isHidden()  # the home page has none
    for item in SECTIONS[1:]:
        hub.show_section(item['id'], animate=False)
        assert not hub.header.isHidden() and hub.header.full_title() == item['title'].upper()
        # the wordmark first, the icon right of the name (in «Компас · …» in place of the dot)
        row = hub.header.title.parentWidget().layout()
        assert row.indexOf(hub.header.mark) < row.indexOf(hub.header.title) < row.indexOf(hub.header.icon) < row.indexOf(hub.header.tail)
        assert (not hub.header.tail.isHidden()) == (' · ' in item['title'])
        assert not hub.header.icon.pixmap().isNull() and not hub.header.mark.pixmap().isNull()
        # 1.2 times larger, as the Atlas header row (zoom 1.2): 8 + 36 + 1
        assert hub.header.height() == hub_window.HEADER_HEIGHT == 45 and hub.header.line.height() == 1  # as the Atlas
        assert hub.header.icon.height() == 36 and hub.header.mark.height() == 36 and hub.header.icon.width() == 26
        hub.header.title.ensurePolished()
        font = hub.header.title.font()  # 19 px tracked 2.66 px (was 24 px)
        assert font.pixelSize() == 19 and abs(font.letterSpacing() - 2.66) < 0.01
    hub.set_language('zh')
    assert hub.header.title.text() == SECTIONS[-1]['zh'] and hub.header.mark.accessibleName() == '方位'
    assert not hub.header.mark.pixmap().isNull() and not hub.brand.pixmap().isNull()  # 方位 with the star
    hub.set_language('ru')


def test_changelog_window_from_about(hub, app, monkeypatch):
    hub.show_about()
    assert wait_for(app, lambda: getattr(hub, 'about_dialog', None) is not None, 10)
    hub.about_dialog.changelog_link.click()
    log = hub.about_dialog.changelog
    # the program tab is Quail's journal (docs/journal), not CHANGELOG.md; no editor's notes anywhere
    program, atlas = log.tabs.widget(0).toPlainText(), log.tabs.widget(1).toPlainText()
    # one tab per section — the program, the Atlas, Compass, Sextant, Spectrum
    assert log.tabs.count() == 5 and '0.35.0' in program
    # no line about CHANGELOG.md and no «Общее» headings; Quill with her notes and the title above the tabs;
    # the text justified
    assert 'Подробный технический журнал' not in program and '\nОбщее\n' not in '\n' + program + '\n'
    assert log.title.text() == 'Что нового — заметки Квил' and not log.picture.pixmap().isNull()
    assert not log.quill.pixmap().isNull() and not log.pen.pixmap().isNull()  # Quill and her pen (0.248.14)
    from PySide6.QtCore import Qt as _Qt

    block = log.tabs.widget(0).document().begin()
    assert block.blockFormat().alignment() & _Qt.AlignmentFlag.AlignJustify
    assert [log.tabs.tabText(i) for i in range(5)] == ['Программа', 'Атлас', 'Компас', 'Секстант', 'Спектр']
    assert 'Правки внесла' not in program and 'Правки внесла' not in atlas
    assert 'Уолша' in atlas and 'Уолша' not in program  # the Atlas entries live in the Atlas tab
    import modules.compass

    compass = log.tabs.widget(2).toPlainText()
    assert 'VTK' in compass and modules.compass.__version__ in compass
    log.close()
    # «Руководство»: the book (PDF) in the reader of the system; the dialog when the system opens nothing
    from PySide6.QtGui import QDesktopServices

    from pathlib import Path

    from hub import about

    opened = []
    monkeypatch.setattr(QDesktopServices, 'openUrl', staticmethod(lambda url: opened.append(url.toLocalFile()) or True))
    hub.about_dialog.manual_link.click()
    assert [Path(p) for p in opened] == [about.MANUAL / 'Azimuth-manual-ru.pdf'] and hub.about_dialog.manual is None
    monkeypatch.setattr(QDesktopServices, 'openUrl', staticmethod(lambda url: False))
    hub.about_dialog.manual_link.click()
    manual = hub.about_dialog.manual.body.toPlainText()
    assert 'Компас' in manual and 'Спектр' in manual and 'Секстант' in manual and 'Атлас' in manual
    # one tab per chapter of the book, the pictures left out
    tabs = hub.about_dialog.manual.tabs
    titles = [tabs.tabText(i) for i in range(tabs.count())]
    assert titles[:9] == ['Введение', 'Установка и первый запуск', 'Быстрый старт: от теории до результата',
                          'Интерфейс и настройки', 'Атлас', 'Компас · Молекула', 'Компас · Кристалл', 'Секстант', 'Спектр']
    assert 'Подготовка расчёта' in hub.about_dialog.manual.pages[7].toPlainText()
    assert all('img/' not in page.toMarkdown() for page in hub.about_dialog.manual.pages)
    hub.about_dialog.manual.close()
    hub.about_dialog.close()


def test_about_window_without_the_atlas(hub, app):
    # the Atlas gave the About window its version and its citation when it was in the window; now the
    # versions of the program and its sections, no «Атлас ещё загружается», no button for a citation
    hub.show_about()
    dialog = hub.about_dialog
    import modules.compass, modules.sextant, modules.spectrum, azimuth  # noqa: E401

    line = dialog.versions.text()
    for version in (azimuth.__version__, modules.compass.__version__, modules.sextant.__version__,
                    modules.spectrum.__version__):
        assert version in line
    assert 'Секстант' in line and 'Спектр' in line and 'загружается' not in line
    assert dialog.motto.text() == 'ПРОЛОЖИТЕ КУРС К РЕЗУЛЬТАТУ'  # as on the home page
    assert '* Расчётные программы' in dialog.body.toPlainText() and 'azimuth-chem.com' in dialog.body.toPlainText()
    assert 'href="https://www.azimuth-chem.com/"' in dialog.body.toHtml()  # the site a link (0.248.11)
    assert not hasattr(dialog, 'copy_button') and dialog.bug_button.isEnabled()
    dialog.close()


def test_close_without_changes_is_accepted(hub):
    hub.studio.dirty = False
    assert hub.close()


def test_tips_live_on_the_site(hub, app):
    # Quill's tips left the home page for the Atlas home page (web/assets/js/tips.js); with the Atlas
    # on the site; the greeting went too
    hub.show_section(hub_window.HOME, animate=False)
    assert not hasattr(hub.home, 'tips') and not hasattr(hub.home, 'tip') and not hasattr(hub.home, 'hello')
    assert 'на сайте' in hub.home.cards['atlas'].text.text()  # 0.249.3: the line of the Atlas says it
    # no note and no e-mail on the home page
    assert hub.home.note.isHidden() and '@' not in hub.home.note.text()


def test_home_continue_where_you_left_off(hub, app, tmp_path, monkeypatch):
    xyz = tmp_path / 'water.xyz'
    xyz.write_text('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n', encoding='utf-8')
    recent = {'molecule': None, 'crystal': None, 'output': None}
    monkeypatch.setattr(hub.studio, 'recent', lambda kind: recent.get(kind))
    monkeypatch.setattr(hub.studio, 'remember_recent', lambda kind, path: None)  # keep the user's settings
    # the cards read recent_list (0.216.x) — «Недавние файлы» of the profile and of the earlier tests of the
    # run are in it too; the list of this test only
    monkeypatch.setattr(hub.studio, 'recent_list', lambda kind, limit=5: [recent[kind]] if recent.get(kind) else [])
    # the window starts on the home page, so it is left and shown again — else the page kept what
    # the earlier tests of the run had opened (the test passed or failed by their order)
    hub.show_section('compass', animate=False)
    hub.show_section(hub_window.HOME, animate=False)
    assert hub.home.continue_title.isHidden()  # a fresh profile: nothing to continue
    recent['molecule'] = str(xyz)  # a molecule was opened in Compass
    hub.show_section('compass', animate=False)
    hub.show_section(hub_window.HOME, animate=False)
    cards = hub.home.continue_cards
    assert not hub.home.continue_title.isHidden()
    # no card of the Atlas — the site keeps its last topic
    # no card of Spectrum
    assert 'atlas' not in cards and not cards['molecule'].isHidden() and 'output' not in cards
    assert cards['molecule'].text.text() == 'water.xyz' and cards['crystal'].isHidden()
    # only the names, without «молекула», «результат ORCA»; the two parts of Compass by their names, a card of the
    # crystal project
    from hub.home import HOME_TEXT

    assert cards['molecule'].title.text() == HOME_TEXT[hub.language]['molecule']
    from azimuth import crystal_projects
    from modules.compass.chemistry import surface
    from tests.sextant.test_qe_inputs import silicon

    recent['crystal'] = str(crystal_projects.create(tmp_path / 'projects', 'Si', surface.write_cif(silicon())))
    hub.show_section('compass', animate=False)
    hub.show_section(hub_window.HOME, animate=False)
    assert not cards['crystal'].isHidden() and cards['crystal'].title.text() == HOME_TEXT[hub.language]['crystal']
    assert cards['crystal'].text.text() == 'Si'
    # each card with the icon of its part of Compass: the crystal one is not the molecule one (2026-11-23)
    crystal_icon, molecule_icon = cards['crystal'].icon.pixmap().toImage(), cards['molecule'].icon.pixmap().toImage()
    assert not crystal_icon.isNull() and crystal_icon != molecule_icon
    hub.studio.dirty = False
    hub.continue_with('molecule')
    assert hub.current == 'compass' and len(hub.studio.coordinate_tool.table_molecule().atoms) == 3
    other = tmp_path / 'ammonia.xyz'
    other.write_text('4\nammonia\nN 0 0 0\nH 0.94 0 0.3\nH -0.47 0.81 0.3\nH -0.47 -0.81 0.3\n', encoding='utf-8')
    monkeypatch.setattr(hub.studio, 'recent_list', lambda kind: [str(xyz), str(other)] if kind == 'molecule' else [])
    hub.show_section(hub_window.HOME, animate=False)
    assert not cards['molecule'].more.isHidden() and cards['crystal'].more.isHidden()
    from PySide6.QtGui import QCursor

    arrow = cards['molecule'].more
    QCursor.setPos(arrow.mapToGlobal(arrow.rect().center()))  # the pointer on the arrow when it opens
    popup = hub.home._choose_recent('molecule')
    # rows as the card
    assert [row.text.text() for row in popup.rows] == ['water.xyz', 'ammonia.xyz'] and popup.isVisible()
    assert all(row.title.text() for row in popup.rows) and not popup.rows[0].icon.pixmap().isNull()
    # out of a stack — first one over the other, then
    # each at its place, one under another
    from PySide6.QtTest import QTest

    # out from under the card of «Продолжить»: at first above the edge of the panel (the lower edge of the card)
    assert all(row.y() + row.height() <= 0 or row.isHidden() for row in popup.rows)
    QTest.qWait(popup.UNFOLD_MS + 150)
    end = time.monotonic() + 3  # a busy computer runs the animation late (Windows check 2026-11-25: 0.78 after the wait)
    while popup.shown < 1.0 and time.monotonic() < end:
        QTest.qWait(20)
    assert popup.shown == 1.0 and popup.rows[1].y() >= popup.rows[0].geometry().bottom()
    # larger, turned up while it is open
    assert arrow.width() >= 40 and arrow.property('open')
    # still lit under the pointer — where the system lets
    # a test move the pointer (macOS may not)
    if arrow.rect().contains(arrow.mapFromGlobal(QCursor.pos())):
        assert arrow.property('hot')
    hub.studio.dirty = False
    popup.rows[1].on_open(popup.rows[1].ident)
    assert not arrow.property('open')
    assert hub.current == 'compass' and len(hub.studio.coordinate_tool.table_molecule().atoms) == 4


def test_back_and_forward_through_sections(hub, app):
    hub.show_section('compass', animate=False)
    hub.show_section('sextant', animate=False)
    hub.show_section('atlas', animate=False)  # the site — no step of the history
    hub.show_section('spectrum', animate=False)
    assert hub.back_button.isEnabled() and not hub.forward_button.isEnabled()
    # the tooltips say they go between sections and name ⌘Z / ⌘⇧Z
    assert hub.back_button.toolTip().startswith('Назад к предыдущему разделу') and '⌘Z' in hub.back_button.toolTip()
    assert hub.forward_button.toolTip().startswith('Вперёд к следующему разделу') and '⌘⇧Z' in hub.forward_button.toolTip()
    hub.back_button.click()
    assert hub.current == 'sextant'
    hub.go_history(-1)
    assert hub.current == 'compass'
    assert hub.forward_button.isEnabled()
    hub.forward_button.click()
    assert hub.current == 'sextant'
    hub.show_section('crystal', animate=False)  # a new step cuts the forward branch
    assert not hub.forward_button.isEnabled()
    hub.go_history(-1)
    assert hub.current == 'sextant'
    assert all(entry[0] != 'atlas' for entry in hub.history)


def test_ornament_in_every_section(hub, app):
    hub.show()
    app.processEvents()
    for ident in [hub_window.HOME] + [i['id'] for i in SECTIONS if i['id'] != 'atlas']:
        hub.show_section(ident, animate=False)
        app.processEvents()
        assert hub.ornament.isVisible() and hub.ornament.size() == hub.content.size()
        assert hub.ornament.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def test_ornament_is_fainter_over_surfaces(hub, app):
    # the scales lie on the background; filled surfaces leave THROUGH of them, the header none
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QImage, QPainter, QRegion
    from PySide6.QtWidgets import QComboBox, QFrame, QPushButton

    hub.resize(1200, 800)
    hub.show()
    hub.show_section('compass', animate=False)
    app.processEvents()
    ornament, content = hub.ornament, hub.content
    region = ornament.surface_region()

    def centre(widget):
        return ornament.mapFrom(content, widget.mapTo(content, widget.rect().center()))

    shown = [w for w in content.findChildren(QFrame) if w.objectName() == 'card' and w.isVisible()]
    combos = [w for w in content.findChildren(QComboBox) if w.isVisible()]
    assert shown and all(region.contains(centre(w)) for w in shown + combos)
    header_point = ornament.mapFrom(content, hub.header.mapTo(content, QPoint(hub.header.width() // 2, 4)))
    assert hub.header.isVisible() and region.contains(header_point)  # the header is glass too (0.248.6)
    icons = [b for b in content.findChildren(QPushButton) if b.property('iconic') and not b.isChecked()]
    assert icons and not any(ornament.is_surface(b) for b in icons)  # transparent icon buttons are not surfaces

    def ink(surfaces):
        image = QImage(ornament.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        ornament.paint_layers(painter, surfaces)
        painter.end()
        return sum(
            image.pixelColor(x, y).alpha() for x in range(0, image.width(), 2) for y in range(0, image.height(), 2)
        )

    free, covered = ink(QRegion()), ink(QRegion(ornament.rect()))
    assert free > 0 and abs(covered / free - ornament.THROUGH) < 0.1


def test_application_icon_follows_theme(hub, app):
    before = hub.dark
    for _ in range(2):
        hub.toggle_theme()
        assert not hub.logo.icon().isNull()
        assert not app.windowIcon().isNull()
    assert hub.dark is before
    assert hub.logo.iconSize().width() == 42
    # the sidebar logo is the transparent glyph whatever the theme (the panel is navy in both)
    assert hub.logo.property('variant') == 'glyph'
    # the Dock icon follows the appearance of the system, not the theme of the program (0.55.0–0.64.6)
    system = 'dark' if hub.system_dark() else 'light'
    for _ in range(2):
        hub.toggle_theme()
        assert hub.property('dock_variant') == system
    assert hub.dark is before


def test_dock_icon_is_quiet_in_tests():
    from hub import dock_icon

    assert dock_icon.available() is False  # offscreen tests never touch Azimuth.app
    assert dock_icon.sync(True) is False
    for dark in (False, True):
        assert dock_icon.icon_file(dark).is_file()


def test_qt_standard_buttons_follow_the_language(app):
    # «Сохранить изменения?» offers «Сохранить / Не сохранять / Отмена», not Save / Discard / Cancel
    from PySide6.QtCore import QCoreApplication
    from PySide6.QtWidgets import QMessageBox
    from azimuth import qt_language

    previous = qt_language.current() or 'ru'
    try:
        qt_language.install('ru')
        box = QMessageBox()
        box.setStandardButtons(
            QMessageBox.StandardButton.Save | QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel
        )
        texts = [box.button(b).text().replace('&', '') for b in (
            QMessageBox.StandardButton.Save, QMessageBox.StandardButton.Discard, QMessageBox.StandardButton.Cancel)]
        assert texts[0] == 'Сохранить' and texts[2] == 'Отмена' and texts[1] not in ('Discard', "Don't Save", '')
        # a text no translator knows stays as it is (not empty)
        assert QCoreApplication.translate('QPlatformTheme', 'No such text 0.55') == 'No such text 0.55'
        qt_language.install('zh')
        assert QCoreApplication.translate('QPlatformTheme', 'Cancel') == '取消'
        qt_language.install('en')
        assert QCoreApplication.translate('QPlatformTheme', 'Cancel') == 'Cancel'
        assert qt_language.install('en') is False  # the same language again changes nothing
    finally:
        qt_language.install(previous)


def test_first_theme_follows_the_system():
    from azimuth import app as studio_app

    assert studio_app.system_prefers_dark() in (True, False)


def test_sections_follow_the_language(hub, app):
    # Compass, Sextant and Spectrum are translated (azimuth/locale), also at run time
    from PySide6.QtWidgets import QLabel
    from azimuth import i18n

    def texts():
        return {w.text() for w in hub.studio.findChildren(QLabel)}

    assert 'Входной файл ORCA' in texts()
    task_key = i18n.combo_key(hub.studio.task)
    hub.set_language('en')
    assert 'ORCA input file' in texts() and 'Входной файл ORCA' not in texts()
    assert hub.studio.task.currentText() == i18n.tr(task_key, 'en')  # shown translated ...
    assert i18n.combo_key(hub.studio.task) == task_key  # ... the key stays Russian
    assert hub.studio.calculation().task == task_key
    hub.set_language('zh')
    assert 'ORCA 输入文件' in texts()
    hub.set_language('ru')
    assert 'Входной файл ORCA' in texts() and i18n.LANG == 'ru'


def test_every_translation_keeps_placeholders():
    import json
    from pathlib import Path

    folder = Path(hub_window.ROOT) / 'azimuth' / 'locale'
    en, zh = (json.loads((folder / f'{c}.json').read_text(encoding='utf-8')) for c in ('en', 'zh'))
    assert set(en) == set(zh) and len(en) > 400
    for key in en:
        for table in (en, zh):
            assert table[key].count('{}') == key.count('{}'), key
            assert table[key].count('\n') == key.count('\n'), key


def test_section_menus_live_in_the_header(hub, app):
    # File / Edit / View in the section header, a different set in every section; no «Пособие»
    from azimuth.i18n import to_source

    assert not hub.studio.menuBar().isVisible()
    from PySide6.QtWidgets import QMenu

    assert 'Пособие' not in {to_source(m.title()) for m in hub.studio.menuBar().findChildren(QMenu)}

    def flat(menu):  # the items of the submenus too (a submenu also counts by its own title)
        out = []
        for a in menu.actions():
            if a.isSeparator():
                continue
            out.append(to_source(a.text()))
            if a.menu() is not None:
                out += flat(a.menu())
        return out

    def menus(ident):
        hub.show_section(ident, animate=False)
        app.processEvents()
        return {to_source(b.text()): flat(b.menu()) for b in hub.header.menu_buttons}

    compass = menus('compass')
    # the menus of Chemcraft
    assert list(compass) == ['Файл', 'Правка', 'Вид', 'Отображение', 'Инструменты', 'Расчёт', 'Проект', 'Справка']
    assert {'Удалить из проекта…', 'Вернуть удалённые', 'Пакетный режим', 'Добавить молекулы…'} <= set(compass['Проект'])
    assert not {'Сохранить', 'Сохранить как…', 'Новый проект с расчётами…', 'Открыть проект…',
                'Молекулы и расчёты проекта…'} & set(compass['Проект'])  # they are in «Файл» only
    assert compass['Справка'] == ['Руководство', 'Что нового', 'Таблица Менделеева', 'Справочник',
                                  'Единицы и константы', 'Растворители', 'Множители частот', 'Опытные данные',
                                  'Проверить обновления…', 'Проверить установку…', 'Папка журналов программы',
                                  'Отчёт об ошибке…', 'О программе']
    assert 'Поиск конформеров…' in compass['Расчёт'] and 'Свойства из расчёта' not in compass['Вид']
    assert 'Новая молекула' in compass['Файл'] and 'Создать связь' in compass['Правка']
    assert 'Отображение связей' in compass['Отображение'] and 'Снимок PNG' in compass['Файл']
    assert 'Скрыть атомы H' in compass['Отображение']
    assert {'Расширить выделение на шаг', 'Выделить по номерам…', 'Найти связи заново', 'Оси по трём выделенным атомам',
            'Повернуть к главным осям инерции'} <= set(compass['Правка'])
    assert {'Перспектива', 'Оси X, Y, Z', 'Копировать положение камеры', 'Все валентные углы', 'Копировать рисунок'} <= set(compass['Вид'])
    assert {'Моменты инерции и вращательные постоянные…', 'Масса молекулы…', 'Фрагменты структуры'} <= set(compass['Инструменты'])
    assert compass['Инструменты'][:3] == ['Определить точечную группу', 'Симметризовать',
                                          'Симметризовать и повернуть в стандартную ориентацию']
    assert 'Кристалл…' not in compass['Вид'] and 'Новая вкладка' in compass['Файл']
    # no item twice, the comparison of structures reachable
    assert 'Симметризовать' not in compass['Правка'] and 'Наложить структуру для сравнения…' not in compass['Инструменты']
    assert 'Сравнение структур' in compass['Инструменты']
    hub.studio.compare_menu.aboutToShow.emit()  # filled when it opens
    assert {'Наложить структуру из файла…', 'Сравнить с вкладкой'} <= {to_source(a.text()) for a in hub.studio.compare_menu.actions()}
    assert {'Шаги расчёта', 'Открыть шаги расчёта…', 'Сохранить шаги одним XYZ…'} <= set(compass['Расчёт'])
    crystal = menus('crystal')  # «Компас · Кристалл» — the same page, the crystal menus and tools
    assert list(crystal) == ['Файл', 'Правка', 'Вид', 'Отображение', 'Кристалл', 'Расчёт', 'Справка']
    assert 'Открыть CIF…' in crystal['Файл']
    # «Кристалл» — the tools of the buttons of the panel; «Расчёт» — the calculation and what it gave
    assert {'Блок ячеек', 'Блок 2 × 2 × 2', 'Вид кристалла', 'Контакты и водородные связи…',
            'Порошковая дифрактограмма…'} <= set(crystal['Кристалл'])
    assert crystal['Кристалл'][0].startswith('Не проверено')  # outside the beta (AGENTS.md §0): marked on top
    # one item for one thing; what a molecule has and a crystal needs
    assert not {'Сведения о кристалле…', 'Сохранить кристалл в CIF…', 'Другой блок, поверхность (hkl), сеть связей…',
                'Выделенные молекулы — в новую вкладку молекулы'} & set(crystal['Кристалл'])
    assert {'Выделить молекулу целиком', 'Расширить выделение на шаг', 'Выделить по номерам…',
            'Выделенные молекулы — в новую вкладку молекулы'} <= set(crystal['Правка'])
    assert {'Перспектива', 'Центровать', 'Оси X, Y, Z', 'Подписи атомов', 'Все валентные углы', 'Скрыть выделенные атомы',
            'Сферы Ван-дер-Ваальса', 'Копировать рисунок'} <= set(crystal['Вид'])
    assert {'Отображение связей', 'Скрыть атомы H'} <= set(crystal['Отображение'])
    assert {'Перечитать файл', 'Показать файл в папке', 'GIF: вращение кристалла'} <= set(crystal['Файл'])
    assert {'Посчитать кристалл в Секстанте…', 'Шаги последней оптимизации', 'Заряды атомов в Multiwfn…',
            'Связи по AIM (Multiwfn)…', 'Спектр кристалла'} <= set(crystal['Расчёт'])
    # the items of «Кристалл» and «Расчёт» in groups
    assert {'Межмолекулярные взаимодействия', 'Структура и упаковка', 'Ячейка и решётка'} <= set(crystal['Кристалл'])
    assert {'Заряды атомов', 'Связи и критические точки (AIM)', 'Поля на модели'} <= set(crystal['Расчёт'])
    # the projects are opened from «Компас · Кристалл» too
    assert {'Открыть проект…', 'Новый проект с расчётами…', 'Недавние файлы'} <= set(crystal['Файл'])
    # from «Правка»
    assert 'Сохранить кристалл в CIF…' in crystal['Файл'] and 'Перестроить кристалл (ячейки, поверхность)…' in crystal['Файл']
    assert not any('Кристалл' in t for t in crystal['Правка'])
    assert 'Показывать ячейку' in crystal['Вид'] and 'Создать связь' not in crystal['Правка']
    assert hub.studio.stack.currentIndex() == 0 and hub.studio.compass_mode == 'crystal'
    assert hub.studio.cell_button.isVisibleTo(hub.studio) and not hub.studio.cell_button.text()  # by the axes
    sextant = menus('sextant')
    assert list(sextant) == ['Файл', 'Правка', 'Вид', 'Расчёт', 'Сервер', 'Справка']
    assert sextant['Вид'] == ['Входной файл', 'Развернуть входной файл', 'Окно расчёта', 'Результат в Компасе',
                              'Результат в Спектре']
    assert sextant['Сервер'] == ['Считать на этом компьютере', 'Считать на сервере', 'Профиль сервера…',
                                 'Проверить подключение к серверу', 'Файлы на сервере', 'Очередь кластера…']
    assert sextant['Расчёт'] == ['Запустить расчёт', 'Остановить расчёт', 'Окно расчёта', 'Другие расчёты на сервере',
                                 'Дополнительные настройки…',
                                 'Цепочка расчётов', 'Оптимизация + частоты → УФ-спектр (TD-DFT)',
                                 'Оптимизация + частоты → ЯМР', 'Оптимизация + частоты → энергия в большем базисе',
                                 # the history; QTAIM of a queue; descriptors
                                 'Оптимизация + частоты → УФ-спектр → ЯМР', 'Указать программу…', 'Установить программы для расчёта…', 'Папка расчёта', 'История расчётов…', 'Методика расчёта…', 'Пакеты расчётов…', 'QTAIM для очереди…', 'Дескрипторы и logK очереди…']
    assert 'Сохранить входной файл ORCA…' in sextant['Файл'] and 'Открыть XYZ…' not in sextant['Файл']
    # «Правка» of Sextant — the editor of the input, the blocks of the program, the check
    assert {'Найти…', 'Заменить…', 'Перейти к строке…', 'Закомментировать / раскомментировать', 'Вставить блок',
            'Проверить входной файл', 'Собрать файл заново по настройкам', 'Скопировать входной файл'} <= set(sextant['Правка'])
    server = next(b.menu() for b in hub.header.menu_buttons if to_source(b.text()) == 'Сервер')
    items = {to_source(a.text()): a for a in server.actions() if not a.isSeparator()}
    items['Считать на сервере'].trigger()  # the same as the button «Сервер» of the row of the program
    assert hub.studio.where == 'server' and hub.studio.where_buttons['server'].isChecked()
    items['Считать на этом компьютере'].trigger()
    assert hub.studio.where == 'local' and hub.studio.where_buttons['local'].isChecked()
    spectrum = menus('spectrum')
    assert 'Открыть результат расчёта…' in spectrum['Файл'] and 'Новая молекула' not in spectrum['Файл']
    assert spectrum['Вид'] == [
        to_source(hub.studio.result_tabs.tabText(i)) for i in range(hub.studio.result_tabs.count())
    ]
    assert 'Изотопный пик молекулярного иона…' in spectrum['Инструменты']  # the tools of results
    assert {'Множители частот…', 'Опытные данные для молекулы…', 'Пересчёт единиц…'} <= set(spectrum['Инструменты'])
    hub.set_language('en')
    try:  # back to Russian even when it fails — the next tests of the hub read Russian tooltips
        assert [b.text() for b in hub.header.menu_buttons] == ['File', 'Edit', 'View', 'Tools', 'Help']
    finally:
        hub.set_language('ru')
    hub.show_section(hub_window.HOME, animate=False)  # the home page has no header (the Atlas is on the site)
    assert not hub.header.isVisible() or not hub.header.menu_buttons
    assert any(a.shortcut().toString() for a in hub.studio.actions())  # Cmd+N/O/S still reach Studio



def test_crystal_section_follows_the_compass_page(hub, app, tmp_path):
    # «Компас · Молекула» and «Компас · Кристалл» are one Studio page in two modes; opening a CIF in the
    # molecule section moves the hub to the crystal section; Sextant → back to Compass keeps the mode
    hub.show_section('compass', animate=False)
    assert hub.studio.compass_mode == 'molecule' and not hub.studio.cell_button.isVisibleTo(hub.studio)
    cif = tmp_path / 'po.cif'
    cif.write_text(
        'data_Po\n_cell_length_a 3.35\n_cell_length_b 3.35\n_cell_length_c 3.35\n_cell_angle_alpha 90\n'
        '_cell_angle_beta 90\n_cell_angle_gamma 90\nloop_\n_atom_site_label\n_atom_site_fract_x\n'
        '_atom_site_fract_y\n_atom_site_fract_z\nPo1 0 0 0\n',
        encoding='utf-8',
    )
    hub.studio.opening_tool.open_path(str(cif))
    assert hub.current == 'crystal' and hub.buttons['crystal'].isChecked() and not hub.buttons['compass'].isChecked()
    hub.studio.crystal_window.reject()
    hub.studio.navigate(1)
    # Sextant of a crystal tab is the calculation of that crystal — the crystal tabs stay (till then, 0.59.0,
    # Sextant always went to the molecule tabs)
    assert hub.current == 'sextant' and hub.studio.document_kind == 'crystal'
    hub.studio.navigate(0)  # back from it: to the crystal
    assert hub.current == 'crystal' and hub.studio.stack.currentIndex() == 0 and hub.studio.compass_mode == 'crystal'
    hub.show_section('compass', animate=False)  # the molecule tabs wait and come back
    assert hub.studio.compass_mode == 'molecule' and hub.current == 'compass'
    hub.studio.navigate(1)
    assert hub.current == 'sextant' and hub.studio.document_kind == 'molecule'  # Sextant of a molecule: the molecules
    hub.studio.to_compass_button.click()  # the arrow next to the input file: back to that molecule
    assert hub.current == 'compass' and hub.studio.stack.currentIndex() == 0
    hub.show_section('crystal', animate=False)  # the crystal tabs wait and come back
    assert hub.studio.compass_mode == 'crystal' and hub.studio.document_kind == 'crystal'
    hub.show_section('compass', animate=False)
    assert hub.studio.compass_mode == 'molecule' and hub.current == 'compass'


def test_ornament_picture_follows_the_section(hub, app):
    # every section draws its own picture lower left (sextant, the compass card in both Compasses, a spectrum); the
    # home page — the isolines of a nitro group (0.245.0, hub/backdrop.py); the side panel shows the same background
    # as glass (PanelGlass, 0.245.0: the molecules in thin lines went)
    from PySide6.QtGui import QImage, QPainter, QRegion

    hub.resize(1200, 800)
    hub.show()
    app.processEvents()
    ornament = hub.ornament
    assert ornament.width() > 600 and ornament.height() > 400

    def ink(ident):
        ornament.set_section(ident)
        image = QImage(ornament.size(), QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(0)
        painter = QPainter(image)
        ornament.paint_layers(painter, QRegion())
        painter.end()
        w, h = image.width(), image.height()
        return sum(image.pixelColor(x, y).alpha() for x in range(0, w // 2, 3) for y in range(h // 2, h, 3))

    home = ink(hub_window.HOME)
    pictures = {ident: ink(ident) for ident in ('compass', 'crystal', 'sextant', 'spectrum')}
    assert home > 0 and all(v > 0 for v in pictures.values()) and home not in pictures.values()
    assert pictures['crystal'] == pictures['compass'] and len(set(pictures.values())) == 3  # both Compasses: the compass
    assert ink('atlas') == 0  # the book of the Atlas went with it (the Atlas is no section of the window)
    hub.show_section('crystal', animate=False)
    assert ornament.section == 'crystal'
    from hub.chrome import PanelGlass

    assert isinstance(hub.panel_art, PanelGlass) and hub.panel_art.source() is ornament and hub.panel_art.offset() is not None
    assert hub.panel_art.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)


def test_a_molecule_of_the_atlas_opens_in_compass(hub, app):
    # «Открыть в Компасе» — 0.131.0 by a link azimuth:// from the site (the keys: azimuth/links.py,
    # checked against the pages in tests/runtime/test_links.py and tests/atlas/test_site_build.py)
    hub.studio.dirty = False
    molecule = hub.open_atlas_molecule('Бензол · C₆H₆')
    assert molecule is not None and hub.current == 'compass' and len(hub.studio.coordinate_tool.table_molecule().atoms) == 12


def test_a_link_of_the_site_opens_its_molecule_in_compass(hub, app, capsys):
    # azimuth://compass/<key> given by the system (azimuth/links.py) — the molecule in Compass; an address
    # not understood does nothing and is written to the log
    hub.studio.dirty = False
    hub.show_section('spectrum', animate=False)
    molecule = hub.open_link('azimuth://compass/water')
    assert molecule is not None and hub.current == 'compass'
    assert sorted(a.symbol for a in hub.studio.coordinate_tool.table_molecule().atoms) == ['H', 'H', 'O']
    tabs = len(hub.studio.all_documents())
    hub.show_section('spectrum', animate=False)
    for bad in ('azimuth://compass/unobtainium', 'azimuth://compass/../x', 'file:///etc/passwd', ''):
        assert hub.open_link(bad) is None
    assert hub.current == 'spectrum' and len(hub.studio.all_documents()) == tabs
    assert sorted(a.symbol for a in hub.studio.coordinate_tool.table_molecule().atoms) == ['H', 'H', 'O']
    assert 'not understood' in capsys.readouterr().err
    hub.studio.dirty = False


def test_calculation_indicator_in_the_panel(hub, app, monkeypatch):
    # an hourglass while a calculation runs (it turns, the tooltip has the time), a tick when it is done; a
    # click opens the window of the calculation without leaving the section and takes the mark away. At the
    # bottom of the panel, over the languages, and only while the window of the calculation is hidden with «Скрыть»
    indicator = hub.job_indicator
    assert indicator.isHidden()
    column = indicator.parentWidget().layout()
    # over the background, not in the layout — the molecules neither move nor disappear when it comes
    assert column.indexOf(indicator) == -1 and indicator.parentWidget() is hub.panel_art.parentWidget()
    hub.show_section('spectrum', animate=False)
    column.activate()
    art = hub.panel_art
    height = art.height()
    hub.studio.run_tool.tell_job('running')
    assert indicator.isHidden() and indicator.timer.isActive()  # the window of the calculation says it all
    hub.studio.job_window.close_button.click()  # «Скрыть»
    assert not indicator.isHidden() and 'Идёт расчёт' in indicator.toolTip()
    column.activate()
    hub._place_job_indicator()
    assert art.height() == height and art.reserve() == 0
    assert indicator.geometry().bottom() < hub.language_row.geometry().top()
    assert not indicator.paint_icon(22, 2.0).isNull()
    assert indicator.sextant_drawn  # a calculation of Sextant — the sextant, not the compass
    # 2026-11-18 started in Compass — the compass
    from types import SimpleNamespace

    job_before = getattr(hub.studio, 'job', None)
    hub.studio.job = SimpleNamespace(section='compass', elapsed=lambda: 1.0)
    indicator.paint_icon(22, 2.0)
    assert not indicator.sextant_drawn
    hub.studio.job = job_before
    assert not hasattr(hub, 'zoom_button')  # no zoom of the Atlas in the panel
    hub.show_section('compass', animate=False)
    assert indicator.geometry().bottom() < hub.language_row.geometry().top()
    hub.show_section('spectrum', animate=False)
    hub.studio.run_tool.tell_job('done', '2 мин 05 с')
    assert not indicator.timer.isActive() and 'Расчёт окончен · 2 мин 05 с' in indicator.toolTip()
    # ended well, not yet opened — the gold ring of the next step round the disc
    from hub.branding import NEXT_GOLD
    from PySide6.QtGui import QColor

    picture = indicator.paint_icon(80, 1.0).toImage()  # large: the thin ring has whole pixels of its colour
    golds = {QColor(NEXT_GOLD[k]).rgb() & 0xFFFFFF for k in NEXT_GOLD}
    assert any(picture.pixelColor(x, y).rgb() & 0xFFFFFF in golds and picture.pixelColor(x, y).alpha() == 255
               for x in range(80) for y in range(80))
    shown = []
    monkeypatch.setattr(hub.studio, 'show_job_window', lambda: shown.append(True))
    indicator.click()
    # the section of the calculation, its card
    assert shown and indicator.isHidden() and hub.current == 'sextant'
    hub.show_section('spectrum', animate=False)
    hub.studio.run_tool.tell_job('failed', '1 с')
    assert 'ошибкой' in indicator.toolTip() and not indicator.isHidden()
    indicator.set_state(None)
    hub.studio.job_window._set_parked(False)
    assert indicator.isHidden()


def test_a_work_of_another_section_is_its_sign_in_the_panel(hub, app):
    from azimuth import tasks

    indicator = hub.job_indicator
    board = hub.studio.activities
    hub.show_section('compass', animate=False)
    board.start(tasks.WAITING, 'Индексы делокализации…', None, parked=True)
    board.get(tasks.WAITING).section = 'spectrum'
    indicator.sync(board)
    assert not indicator.isHidden() and not indicator.paint_icon(40, 2.0).isNull()
    assert indicator.section_drawn == 'spectrum' and 'Индексы делокализации' in indicator.toolTip()
    indicator.click()
    assert hub.current == 'spectrum'
    # ended while away: the sign stays done — the gold ring and the tick — until it is opened
    hub.show_section('compass', animate=False)
    board.finish(tasks.WAITING, 'done')
    indicator.sync(board)
    assert not indicator.isHidden() and indicator.paint_icon(40, 2.0) is not None and indicator.state_drawn == 'done'
    indicator.click()
    assert hub.current == 'spectrum' and board.get(tasks.WAITING) is None and indicator.isHidden()
    hub.show_section('compass', animate=False)


def test_work_put_away_in_the_panel(hub, app):
    # one sign for the long work put away —
    # the compass of the program with the ring of the share done; several — their number, a click gives the list
    indicator, board = hub.job_indicator, hub.studio.activities
    opened = []
    board.start('conformers', 'Поиск конформеров', lambda: opened.append('conformers'), total=8)
    assert indicator.isHidden() and indicator.timer.isActive()  # its window is open: nothing in the panel
    board.park('conformers')
    board.progress('conformers', done=3)
    assert not indicator.isHidden() and 'Поиск конформеров · 3/8' in indicator.toolTip()
    assert not indicator.paint_icon(22, 2.0).isNull()
    assert not indicator.sextant_drawn  # the search of conformers keeps the compass
    indicator.set_collapsed(False)
    assert indicator.text() and indicator.label() == 'Поиск конформеров 3/8'
    indicator.set_collapsed(True)
    board.start('other', 'Multiwfn', lambda: opened.append('other'), parked=True)
    assert indicator.label() == 'Фоновых работ: 2' and not indicator.paint_icon(22, 1.0).isNull()
    indicator.open_window()  # several: a list of them
    assert [a.text() for a in indicator.menu.actions()] == ['Поиск конформеров 3/8', 'Multiwfn']
    indicator.menu.close()
    board.remove('other')
    board.finish('conformers', 'done')
    assert not indicator.timer.isActive() and 'окончен' in indicator.toolTip()
    indicator.click()  # opened: the end is seen, the sign goes
    assert opened == ['conformers'] and indicator.isHidden() and board.get('conformers') is None


def test_theme_wipe_circle(app):
    # to the dark theme the circle grows from the button to the farthest corner, back to the light one it
    # shrinks into the button; the still picture is painted outside (growing) or inside (shrinking) the circle
    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QPixmap
    from PySide6.QtWidgets import QWidget

    from hub import theme_wipe

    host = QWidget()
    host.resize(400, 300)
    still = QPixmap(400, 300)
    still.fill(QColor('#f5f6f8'))
    grow = theme_wipe.ThemeWipe(host, still, QPointF(20, 280), spreading=True)
    shrink = theme_wipe.ThemeWipe(host, still, QPointF(20, 280), spreading=False)
    far = grow.far()
    corner = ((380 ** 2 + 280 ** 2) ** 0.5) + 4
    waves = sum(a for _, a, _, _ in theme_wipe.WAVES)
    assert abs(far - corner / (1 - waves)) < 1e-6
    import math

    grow.progress = 1.0  # the edge is wavy, and at the end even its troughs are past the farthest corner
    radii = [grow.edge_radius(2 * math.pi * i / 360) for i in range(360)]
    assert min(radii) >= corner - 1e-6 and max(radii) - min(radii) > 0.1 * far
    grow.progress = 0.3
    assert all(abs(grow.edge_radius(x) / grow.radius() - 1) <= waves + 1e-9 for x in (0.0, 1.0, 2.5, 4.0))
    assert grow.edge().elementCount() >= theme_wipe.POINTS
    for t, small, large in ((0.0, 0.0, far), (0.5, far / 2, far / 2), (1.0, far, 0.0)):
        grow.progress = shrink.progress = t
        assert abs(grow.radius() - small) < 1e-9 and abs(shrink.radius() - large) < 1e-9
    grow.progress = 0.5
    image = grow.grab().toImage()
    assert image.pixelColor(390, 10) == QColor('#f5f6f8')  # far from the button: still the old picture
    assert theme_wipe.wipe_enabled() is False  # the tests run offscreen: the theme changes at once
    # a little slower, with an ease out (the ink moves from the first frame)
    assert theme_wipe.WIPE_MS == 950
    # the two ways mirror each other — out of the button slowly (to dark), into it slowly (to light)
    assert grow.animation.easingCurve().type() == theme_wipe.QEasingCurve.Type.InCubic
    assert shrink.animation.easingCurve().type() == theme_wipe.QEasingCurve.Type.OutCubic
    # always inside the window (the separate window over the web view of the Atlas went with it)
    assert not grow.isWindow() and grow.geometry() == host.rect()
    host.deleteLater()


def test_menus_and_buttons_are_translated_and_not_cut(hub, app):
    # in English and Chinese no menu item, submenu or tooltip of Compass, Sextant and
    # Spectrum is left in Russian, and no visible button of Compass cuts its text (its width is below what the text
    # needs)
    import re

    from PySide6.QtWidgets import QAbstractButton

    cyrillic = re.compile('[А-Яа-яЁё]')

    def texts(menu, path=''):
        out = []
        for a in menu.actions():
            if a.isSeparator():
                continue
            where = f'{path} → {a.text()}'
            out.append((where, a.text()))
            if a.toolTip() and a.toolTip() != a.text():
                out.append((where + ' (подсказка)', a.toolTip()))
            if a.menu() is not None:
                out += texts(a.menu(), where)
        return out

    try:
        for code in ('en', 'zh'):
            hub.set_language(code)
            for ident in ('compass', 'sextant', 'spectrum'):
                hub.show_section(ident, animate=False)
                app.processEvents()
                left = [(f'{code} {ident}: {b.text()}{where}', text) for b in hub.header.menu_buttons
                        for where, text in [('', b.text())] + texts(b.menu())]
                russian = [where for where, text in left if cyrillic.search(text)]
                assert not russian, russian
            hub.show_section('compass', animate=False)
            hub.resize(1280, 800)
            app.processEvents()
            cut = []
            for button in hub.studio.findChildren(QAbstractButton):
                if button.isVisible() and button.text().strip() and button.width() + 2 < button.sizeHint().width():
                    cut.append(f'{code}: «{button.text()}» {button.width()} < {button.sizeHint().width()}')
            assert not cut, cut
    finally:
        hub.set_language('ru')


def test_header_menus_close_on_a_second_click_and_animate_once(hub, app):
    # the system animation of menus is off (ours alone — before, the menu showed twice); a press on
    # the name of a menu that has just closed is swallowed, so the second click closes it instead of opening it again
    import time

    from PySide6.QtCore import QEvent, QPointF, Qt
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication

    from hub.header import MenuToggle

    hub.show_section('compass', animate=False)
    app.processEvents()
    assert not QApplication.isEffectEnabled(Qt.UIEffect.UI_AnimateMenu)
    assert not QApplication.isEffectEnabled(Qt.UIEffect.UI_FadeMenu)
    button = hub.header.menu_buttons[0]
    toggle = MenuToggle._filter
    press = QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(5, 5), QPointF(5, 5), Qt.MouseButton.LeftButton,
                        Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert toggle.eventFilter(button, press) is False  # no menu closed: the press opens it as usual
    button.menu().aboutToHide.emit()
    assert toggle.just_closed(button) and toggle.eventFilter(button, press) is True
    assert toggle.eventFilter(button, press) is False  # only that one press
    button.menu().aboutToHide.emit()
    assert not toggle.just_closed(button, now=time.monotonic() + 1)


def test_settings_of_the_panel(hub):
    # «Настройки» of the panel (a gear between the theme and «О программе») and «Файл → Настройки…» of the
    # sections open the same window; its language is the language of the hub
    assert hub.settings_button.toolTip() == 'Настройки'
    hub.settings_button.click()
    dialog = hub.studio.settings_dialog
    assert dialog.isVisible() and dialog.hub is hub and dialog.language.isEnabled()
    dialog.language.setCurrentIndex(dialog.language.findData('en'))
    assert hub.language == 'en' and hub.preferences.value('hub_language') == 'en'
    assert hub.settings_button.toolTip() == 'Settings'
    hub.set_language('ru')
    dialog.close()
    hub.show_section('sextant', animate=False)
    files = next(m for t, m in hub._section_menus('sextant') if t == 'Файл')
    assert 'Настройки…' in [a.text() for a in files.actions()]


def test_the_blue_side_of_a_card_leaves_no_line_inside(app):
    # the blue side of Quill's greeting (quill.paint_edge) cut by intersecting paths left a seam along the cut
    # — on Windows a thin blue line inside the card, 20 px from its side; with clipping
    # the card is its own colour right after the band, at the scales of Windows too
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QColor, QImage, QPainter

    from azimuth import quill

    navy = QColor('#1c2a42')
    for scale in (1.0, 1.25, 1.5, 2.0):
        image = QImage(round(240 * scale), round(140 * scale), QImage.Format.Format_ARGB32)
        image.fill(navy)
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.scale(scale, scale)
        body = QRectF(14.5, 0.5, 200, 120)
        quill.paint_edge(painter, body, 18, 'left', navy)
        painter.end()
        y = round(60 * scale)
        assert QColor(image.pixel(round((body.left() + 1) * scale), y)) != navy  # the band is there
        for x in range(round((body.left() + quill.EDGE + 2) * scale), round((body.left() + 60) * scale)):
            assert QColor(image.pixel(x, y)) == navy, (scale, x)


def test_ornament_survives_widgets_with_a_size_and_a_window_of_their_own(hub, app):
    # 0.91.52–0.91.53 (the user's reports from Windows): a widget with an attribute «size» (the list of the map size)
    # or «window» (the render window of the VTK view) broke the painting of the ornament at every frame — the screen
    # went black at a change of section; the methods of QWidget are now called as QWidget.size(w)
    from PySide6.QtWidgets import QComboBox, QLabel

    class Odd(QLabel):
        def __init__(self, parent):
            super().__init__('x', parent)
            self.size = QComboBox()
            self.window = object()

    hub.show()
    odd = Odd(hub.content)
    odd.setObjectName('notice')  # a surface: it is measured
    odd.show()
    app.processEvents()
    try:
        hub.ornament.surface_region()
        hub.ornament.opaque_region()
        assert not hub.ornament.grab().isNull()
        assert not hub.content.grab().isNull()  # the still of a change of section
    finally:
        odd.deleteLater()


def test_map_and_profile_side_by_side(app):
    # «Карты и профили» — the map and the profile next to each other, both seen
    from modules.spectrum.views.field_view import FieldPanel

    panel = FieldPanel()
    panel.resize(900, 500)
    panel.show()
    app.processEvents()
    try:
        assert panel.map_view.isVisible() and panel.line_view.isVisible()
        from PySide6.QtCore import QPoint

        left, right = (v.mapTo(panel, QPoint(0, 0)) for v in (panel.map_view, panel.line_view))
        assert left.x() < right.x() and left.y() == right.y()
        assert panel.views.currentWidget() is panel.map_view
        # each picture its own row over it — the plane over the map, the line over the profile,
        # with a floppy disk that saves that picture; the log scale an icon; the explanation in «?»
        for button, view in ((panel.map_save, panel.map_view), (panel.line_save, panel.line_view)):
            assert button.mapTo(panel, QPoint(0, 0)).y() < view.mapTo(panel, QPoint(0, 0)).y()
            assert abs(button.mapTo(panel, QPoint(0, 0)).x() + button.width()
                       - view.mapTo(panel, QPoint(view.width(), 0)).x()) <= 2  # at the right edge of its picture
        assert panel.map_button.mapTo(panel, QPoint(0, 0)).x() < right.x() <= panel.line_button.mapTo(panel, QPoint(0, 0)).x()
        assert panel.log.isCheckable() and panel.log.isChecked() and panel.log.text() == ''
        assert panel.field_help.help.startswith('Функция волновой функции')
        panel.views.setCurrentWidget(panel.line_view)
        assert panel.views.currentWidget() is panel.line_view
    finally:
        panel.close()


def test_the_molecules_of_the_panel_background(app):
    # the background of the whole panel — its child under the buttons, two staggered columns from
    # under the name to the bottom, fifteen drawings (three of them cells), the same picture at every start
    from PySide6.QtCore import QPointF, Qt
    from PySide6.QtGui import QColor, QImage, QPainter, QPen
    from PySide6.QtWidgets import QFrame, QPushButton, QVBoxLayout

    from hub.chrome import MoleculeArt

    bar = QFrame()
    column = QVBoxLayout(bar)
    button = QPushButton('Компас')
    column.addWidget(button)
    art = MoleculeArt(bar)
    column.addStretch(1)
    bar.resize(196, 860)
    bar.show()
    app.processEvents()
    assert art.geometry() == bar.rect() and column.indexOf(art) == -1  # follows the panel, takes no place in it
    assert bar.children().index(art) < bar.children().index(button)  # under the buttons
    assert art.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    places = art.places()
    # fewer, scattered, and nothing
    # above the line under the name (top(), set by the window)
    assert places == art.places(860) and 10 <= len(places) <= 16
    ys, xs = [p[2] for p in places], [p[1] for p in places]
    assert min(ys) >= art.top() + art.REACH and max(ys) > 860 - 110  # from the line to the bottom
    assert min(xs) < 68 < max(xs)  # the rail (the narrow panel) and the wide part
    rail = sorted(y for _k, x, y, _t, _s in places if x < 68)
    gaps = [b - a for a, b in zip(rail, rail[1:])]
    assert max(gaps) - min(gaps) > 12 and len({round(x) for x in xs}) > len(xs) // 2  # no grid
    assert len({round(p[3] / 20) for p in places}) >= 6  # turned every way
    kinds = [p[0] for p in places]
    cells = [k for k in kinds if k >= 12]
    assert len(set(kinds)) >= 10 and 1 <= len(cells) <= 3  # mixed; «пару ячеек»
    assert all(abs(t) <= art.CELL_TURN for k, _x, _y, t, _s in places if k >= 12)  # a cell stays a cell
    assert len(art.places(400)) < len(places) and all(y <= 400 - art.EDGE for _k, _x, y, _t, _s in art.places(400))
    art.top = lambda: 300  # a lower line: everything under it
    assert min(p[2] for p in art.places()) >= 300 + art.REACH
    art.top = lambda: art.TOP
    for order in art.ORDER:
        assert sorted(order) == list(range(len(art.drawings())))
        assert all(a != b for a, b in zip(order, order[1:]))
    for draw in art.drawings():  # every drawing leaves ink
        image = QImage(80, 80, QImage.Format.Format_ARGB32_Premultiplied)
        image.fill(Qt.GlobalColor.transparent)
        painter = QPainter(image)
        painter.setPen(QPen(QColor('#2a62b8'), 1.0))
        painter.translate(40, 40)
        draw(painter, QPointF(0, 0))
        painter.end()
        assert any(image.pixelColor(x, y).alpha() for x in range(80) for y in range(80)), draw.__name__
    image = QImage(196, 860, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    from PySide6.QtCore import QPoint
    from PySide6.QtGui import QRegion

    art.render(image, QPoint(0, 0), QRegion(), art.RenderFlag.DrawChildren)
    assert not any(image.pixelColor(x, y).alpha() for x in range(196) for y in range(0, art.TOP + 2))  # clear above the line
    strongest = max(image.pixelColor(x, y).alpha() for x in range(0, 196, 2) for y in range(100, 860, 2))
    assert 0 < strongest <= 128  # faint: also where the lines cross, never stronger than a half
    bar.close()


def test_the_panel_of_the_site_has_the_background_of_the_program(app):
    # molecules and cells in thin lines behind the icons
    # of the panel, under the line of the name — the drawings, their order and the scatter of the narrow rail of the
    # program (hub/chrome.py, MoleculeArt); not on the bar of a phone
    import re
    from pathlib import Path

    from hub.chrome import MoleculeArt

    rail = (Path(__file__).resolve().parents[2] / 'site' / 'rail.js').read_text(encoding='utf-8')
    art = re.search(r'const ART = \{row: (\d+), edge: (\d+), reach: (\d+), jy: (\d+), jx: (\d+), cellTurn: (\d+), order: \[([\d, ]+)\]\}', rail)
    assert art, 'the constants of the background'
    numbers = tuple(int(v) for v in art.groups()[:6])
    assert numbers == (MoleculeArt.ROW, MoleculeArt.EDGE, MoleculeArt.REACH, MoleculeArt.JITTER_Y, MoleculeArt.RAIL, MoleculeArt.CELL_TURN)
    assert tuple(int(v) for v in art.group(7).split(',')) == MoleculeArt.ORDER[0]
    for constant in ('374761393', '668265263', '2246822519', '3266489917', '1274126177'):  # the same scatter
        assert constant in rail
    drawings = re.findall(r'^      function (\w+)\(\)', rail, re.M)
    assert len(drawings) == len(MoleculeArt().drawings()) == 15 and drawings[-3:] == ['cubicCell', 'centredCell', 'hexagonalCell']
    assert "34 + (2 * r[1] - 1) * ART.jx" in rail and '0.74 + 0.30 * r[3]' in rail
    assert '#siteRail .rArt{position:absolute' in rail and 'pointer-events:none' in rail and 'z-index:-1' in rail
    assert "art.setAttribute('aria-hidden', 'true')" in rail
    assert rail.index('#siteRail .rArt{position:absolute') < rail.index('  #siteRail .rArt{display:none}')  # a phone: none
    assert "art.style.height = height + 'px'" in rail  # «#siteRail svg» would make it an icon of 22 px


def test_the_entries_of_the_journal_do_not_creep_to_the_right():
    # an entry «- ### title» is shown as a heading, its text a paragraph under it — no list nested in the one before
    from hub.about import journal_page

    text = '## 0.2 — 17\n\n- ### 0.2 — b\n\nB.\n\n## 0.1 — 17\n\n- ### 0.1 — a\n\nA.\n'
    shown = journal_page(text)
    assert '- ###' not in shown and '### 0.2 — b\n\nB.' in shown and '### 0.1 — a' in shown


def test_the_versions_of_the_journal_stand_under_one_heading_a_minor(app):
    from hub.about import journal_page, journal_span

    text = ('# Журнал\n\n## 0.3.0 — 2 ноября 2026\n\n- ### 0.3.0 — c\n\nC.\n\n'
            '## 0.2.1 — 1 ноября 2026\n\n- Без заголовка.\n\n## 0.2.0 — 30 октября 2026\n\n- ### 0.2.0 — a\n\nA.\n\n'
            '## Раньше\n\nСтарое.\n')
    shown = journal_page(text)
    heads = [line for line in shown.splitlines() if line.startswith('## ')]
    assert heads == ['## 0.3 — 2 ноября 2026', '## 0.2 — 30 октября – 1 ноября 2026', '## Раньше']
    assert '### 0.2.1\n\n- Без заголовка.' in shown and '### 0.2.0 — a\n\nA.' in shown and '### 0.2.0\n' not in shown
    assert journal_span(['17 November 2026', '15 November 2026']) == '15–17 November 2026'
    assert journal_span(['2026 年 11 月 17 日', '2026 年 11 月 16 日']) == '2026 年 11 月 16–17 日'
    assert journal_span(['вчера']) == 'вчера'


def test_a_message_of_spectrum_in_the_hub_is_a_pill(hub):
    # the Studio is a widget of the hub, a StatusEcho tells the Studio (not the window of the hub), and a message
    # written into the status line of the hub goes to the pill of the section too
    from azimuth.ui import StatusEcho

    hub.show_section('spectrum', animate=False)
    studio = hub.studio
    echo = StatusEcho(studio.stack.currentWidget())
    echo.setText('Таблицы в папке расчёта: a.csv')
    assert studio._page_toast.text() == 'Таблицы в папке расчёта: a.csv' and not studio._page_toast.isHidden()
    assert hub.statusBar().isHidden() and not hub.statusBar().currentMessage() and echo.isHidden()
    hub.statusBar().showMessage('Ещё одно', 3000)
    assert studio._page_toast.text() == 'Ещё одно' and hub.statusBar().isHidden()


def test_the_sign_of_waiting_is_the_sign_of_the_section(hub, app):
    # on the pill of Sextant the
    # sextant, of Spectrum the recorded spectrum (wider: the padding of the pill «wide»)
    import time

    from PySide6.QtCore import QTimer

    from azimuth.tasks import run_waiting
    from azimuth.ui import Spinner

    for section, kind, busy in (('sextant', 'sextant', True), ('spectrum', 'spectrum', 'wide')):
        hub.show_section(section, animate=False)
        seen = []

        def look():
            # the line of the work on a pill of its own (busy_status)
            toast = hub.studio.busy_pill()
            seen.append(([s.kind for s in toast.findChildren(Spinner)], toast.property('busy')))

        QTimer.singleShot(600, look)
        run_waiting(hub.studio, 'Считаю', lambda step: time.sleep(1.2))
        assert seen and seen[0][0] == [kind] and seen[0][1] == busy
        assert hub.studio.busy_pill() is None


def test_about_has_one_icon_and_the_journal_no_strip(hub):
    import inspect

    import hub.about as about
    from azimuth.button_icons import TEXT_ICONS

    assert TEXT_ICONS['О программе'] == 'info'
    assert 'border-left' not in inspect.getsource(about)


def test_a_menu_item_calls_without_the_flag_of_triggered(hub, monkeypatch):
    # «triggered» gave False to verify_installation as
    # its «show» — the result was never shown
    from azimuth.i18n import to_source

    calls = []
    monkeypatch.setattr(hub, 'verify_installation', lambda *args, **kw: calls.append((args, kw)))
    hub.show_section('compass', animate=False)
    helps = next(b.menu() for b in hub.header.menu_buttons if to_source(b.text()) == 'Справка')
    item = next(a for a in helps.actions() if to_source(a.text()) == 'Проверить установку…')
    item.trigger()
    assert calls == [((), {})]


def test_a_message_pill_is_measured_by_its_text(hub):
    studio = hub.studio
    hub.show_section('compass', animate=False)
    studio.notify('Проверка установки… · 0:01 · Esc — отменить', 3000)
    one = studio.notice.fontMetrics().height()
    assert studio.notice.width() < 420 and studio.notice.height() < 2 * one + 20
    studio.hide_notice()


def test_the_check_of_the_installation_speaks_the_language_of_the_program():
    from hub.menus import verify_lines

    out = ('[OK] Python: 3.13.3\n[OK] Dependencies: pinned versions and runtime imports\n'
           '[OK] Assets: 818 bundled files verified\n[OK] Symmetry: point group of water: C2v\n'
           '[FAIL] Surface: RuntimeError: no VTK\n4/5 checks passed')
    lines, done, total = verify_lines(out)
    assert (done, total) == (4, 5) and len(lines) == 5
    assert lines[2] == '✓ Файлы программы — проверено файлов: 818' and lines[4].startswith('✗ Поверхности — RuntimeError')


def test_the_menus_of_the_header_put_items_on_the_panels_of_compass(hub, app, monkeypatch):
    # the header shows menus of its own — they are watched too: a right
    # click on an item offers it for the panels, an item pressed and moved is dragged onto them
    from PySide6.QtCore import QEvent, QPointF
    from PySide6.QtGui import QMouseEvent

    from modules.compass.actions import custom_bar as cb

    monkeypatch.setattr(cb.CustomBar, 'CARRY_IN_MENU', False)  # the drag of the system (on macOS the menu carries it)
    hub.show_section('compass', animate=False)
    app.processEvents()
    bar = hub.studio.custom_bar
    view = next(m for m in hub._header_menus if m.title() == 'Вид')
    assert view.property('azimuthBarWatched')
    action = next(a for a in view.actions() if not a.isSeparator() and a.menu() is None and a.isEnabled()
                  and bar.key_of(a) is not None and bar.already(bar.key_of(a), a) is None)
    key = bar.key_of(action)
    view.ensurePolished()
    view.adjustSize()
    centre = QPointF(view.actionGeometry(action).center())
    offered, dragged = [], []
    monkeypatch.setattr(bar, 'offer', lambda k, at: offered.append(k))
    monkeypatch.setattr(bar, 'drag_item', lambda k, a, sub: dragged.append((k, a)))

    def mouse(kind, point, button, buttons):
        return QMouseEvent(kind, point, view.mapToGlobal(point), button, buttons, Qt.KeyboardModifier.NoModifier)

    right = Qt.MouseButton.RightButton
    assert bar.clicks.eventFilter(view, mouse(QEvent.Type.MouseButtonRelease, centre, right, Qt.MouseButton.NoButton))
    assert offered == [key]
    left = Qt.MouseButton.LeftButton
    bar.clicks.eventFilter(view, mouse(QEvent.Type.MouseButtonPress, centre, left, left))
    assert not dragged  # a press alone is a click of the menu
    away = centre + QPointF(40, 0)
    assert bar.clicks.eventFilter(view, mouse(QEvent.Type.MouseMove, away, Qt.MouseButton.NoButton, left))
    assert dragged == [(key, action)]
    # the menus made anew for another section are watched as well (marked on the menu, not by its id)
    hub.show_section('sextant', animate=False)
    hub.show_section('compass', animate=False)
    assert all(m.property('azimuthBarWatched') for m in hub._header_menus if m.title() == 'Вид')



def test_the_items_the_header_makes_itself_go_on_the_panels_too(hub, app):
    # the header makes items of its own («К параметрам расчёта», «Определить точечную группу», the submenu «Шаги
    # расчёта»…) — they had no key, so no right click and no drag; their buttons come back with the new menus of each
    # visit to Compass
    from modules.compass.actions import custom_bar as cb

    hub.show_section('compass', animate=False)
    app.processEvents()
    bar = hub.studio.custom_bar
    calc = next(m for m in hub._header_menus if m.title() == 'Расчёт')
    own = next(a for a in calc.actions() if a.text() == 'К параметрам расчёта')
    key = bar.key_of(own)
    assert key == 'Расчёт/К параметрам расчёта'
    steps = next(a for a in calc.actions() if a.menu() is not None and a.text() == 'Шаги расчёта')
    assert bar.key_of(steps) == 'Расчёт/Шаги расчёта'
    try:
        bar.add(key, cb.TOP)
        assert key in bar.buttons
        hub.show_section('sextant', animate=False)
        hub.show_section('compass', animate=False)
        app.processEvents()
        assert key in bar.buttons  # made again with the action of the new menu
        again = next(a for a in next(m for m in hub._header_menus if m.title() == 'Расчёт').actions()
                     if a.text() == 'К параметрам расчёта')
        assert bar.find(key)[0] is again
    finally:
        bar.reset()


def test_an_item_carried_in_over_the_field_can_still_be_dropped_on_a_panel(hub, app):
    # Windows, 2026-11-27: «Заряд и мультиплетность» and «Поиск конформеров…» stand low in the menu «Расчёт» — when the
    # menu closed, the item was over the field, where no button goes; the card ignored that DragEnter, Qt sent it no
    # DragMove after it, and the sign «not here» stayed wherever the item was carried
    from PySide6.QtCore import QEvent, QMimeData, QPoint, QPointF, Qt
    from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent

    from modules.compass.actions import custom_bar as cb

    hub.show_section('compass', animate=False)
    app.processEvents()
    bar = hub.studio.custom_bar
    card = bar.card
    data = QMimeData()
    data.setData(cb.MIME, 'Расчёт/К параметрам расчёта'.encode('utf-8'))
    middle = QPoint(card.width() // 2, card.height() // 2)
    assert bar.slot(middle) is None  # the field itself: no place for a button
    enter = QDragEnterEvent(middle, Qt.DropAction.MoveAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    enter.ignore()
    assert bar.drags.eventFilter(card, enter) and enter.isAccepted()  # taken in, to be asked again at every move
    there = QDragMoveEvent(middle, Qt.DropAction.MoveAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert bar.drags.eventFilter(card, there) and not there.isAccepted()  # over the field: «not here»
    row = next(QPoint(x, y) for y in range(2, card.height(), 6) for x in range(2, card.width(), 12)
               if bar.slot(QPoint(x, y)) is not None)  # a point at the row above the field (or at the column)
    near = QDragMoveEvent(row, Qt.DropAction.MoveAction, data, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    near.ignore()
    assert bar.drags.eventFilter(card, near) and near.isAccepted()  # at the row above the field: it can be dropped
    foreign = QMimeData()
    foreign.setText('not a button')
    other = QDragEnterEvent(middle, Qt.DropAction.MoveAction, foreign, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
    assert bar.drags.eventFilter(card, other) and not other.isAccepted()  # not ours: as before
    bar.show_slot(None, at_once=True)


def test_the_glass_follows_a_panel_that_moved(hub, app):
    # 0.249.4 (the owner, Sextant: «При открытии панели структуры» the glass stayed in strips where the panels had
    # stood): the frames of the gyroscope reuse the regions of the last painting — a widget of the window moved or
    # resized drops them, and the whole background is painted again where the panels are now
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import QFrame

    hub.show()
    hub.show_section(hub_window.HOME, animate=False)  # the bare page under the cards
    app.processEvents()
    ornament = hub.ornament
    panel = QFrame(hub.content)
    panel.setObjectName('card')  # a surface: its glass is drawn under it
    panel.setGeometry(300, 700, 120, 60)
    panel.show()
    app.processEvents()
    ornament.repaint()
    surfaces, _ = ornament._regions
    assert surfaces.contains(QPoint(360, 730)) and not surfaces.contains(QPoint(760, 730))
    panel.move(700, 700)  # the drawer slides: a move alone
    assert ornament._layout_pending  # one painting after all the widgets that move at once
    app.processEvents()
    ornament._frame = True  # a frame of the gyroscope uses what the painting after the move found
    ornament.repaint()
    ornament._frame = False
    surfaces, _ = ornament._regions
    assert surfaces.contains(QPoint(760, 730)) and not surfaces.contains(QPoint(360, 730))
    panel.deleteLater()
    app.processEvents()


def test_the_card_of_the_molecule_keeps_its_lines_whole_beside_the_panel_of_structures(hub, app):
    # 0.249.7, the owner: «В секстанте при разворачивании списка структур текст криво сворачивается» — on a window of
    # about 1130 px the lines of the molecule were wrapped into a column of 100 px beside the model and ran under
    # «Примерное время расчёта». A narrow card shows them without the model; the note under the input file goes
    st = hub.studio
    st.opening_tool.load_smiles('O')
    hub.resize(1132, 700)
    hub.show()
    hub.show_section('sextant', animate=False)
    QTest.qWait(400)
    try:
        st.project_menu_button.setChecked(True)
        st.toggle_project_molecules()
        QTest.qWait(1000)
        assert st.calc_card.width() < 480 and not st.calc_picture.isVisible()
        assert st.state_info.geometry().bottom() < st.time_estimate.geometry().top()
        assert st.state_info.width() > 180  # the room of the model given to the lines
        assert st.preview_card.geometry().top() > st.calc_card.geometry().bottom()
        st.project_menu_button.setChecked(False)
        st.toggle_project_molecules()
        hub.resize(1600, 900)
        QTest.qWait(1000)
        assert st.calc_card.width() >= 480 and st.calc_picture.isVisible()
    finally:
        st.project_menu_button.setChecked(False)
        st.slide_project_pane(False, animate=False)

"""The icons of the text buttons (azimuth/button_icons.py)."""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

from azimuth import button_icons, i18n

ICONS = Path(__file__).parents[2] / 'azimuth' / 'icons.py'


def test_every_button_has_a_drawn_glyph():
    toolbar = set(re.findall(r"^    '([a-z0-9-]+)': '", ICONS.read_text(encoding='utf-8'), re.M))
    names = set(button_icons.TEXT_ICONS.values()) | {name for _, name in button_icons.RULES}
    assert names <= toolbar | set(button_icons.BUTTON_GLYPHS)
    assert not set(button_icons.BUTTON_GLYPHS) & toolbar  # a new glyph never hides one of the toolbars
    source = (Path(__file__).parents[2] / 'azimuth' / 'button_icons.py').read_text(encoding='utf-8')
    glyphs = source[source.index('BUTTON_GLYPHS = {'):source.index('\n}\n', source.index('BUTTON_GLYPHS = {'))]
    drawn = re.findall(r"^    '([a-z0-9-]+)': '", glyphs, re.M)
    assert len(drawn) == len(set(drawn)), sorted({n for n in drawn if drawn.count(n) > 1})  # a second «units» hid the first
    for name, glyph in button_icons.BUTTON_GLYPHS.items():
        ET.fromstring(f'<svg xmlns="http://www.w3.org/2000/svg">{glyph}</svg>')  # well formed


def test_the_icon_follows_the_language():
    for lang in i18n.LANGUAGES:
        assert button_icons.icon_name(i18n.tr('Сохранить рисунок…', lang), lang) == 'image'
        assert button_icons.icon_name(i18n.tr('Построить карту', lang), lang) == 'map'
        assert button_icons.icon_name(i18n.tr('Закрыть', lang), lang) == 'close'
    assert button_icons.icon_name('Сохранить отчёт как…') == 'save'  # by the first word
    assert button_icons.icon_name('&Готово') == 'check'
    assert button_icons.icon_name('Квил') is None and button_icons.icon_name('') is None


def test_the_buttons_of_the_code_are_covered():
    # the texts of QPushButton(tr('…')) in the program: almost all have an icon (a few are deliberately left)
    root = Path(__file__).parents[2]
    texts = set()
    for path in list((root / 'modules').rglob('*.py')) + list((root / 'azimuth').rglob('*.py')) + list((root / 'hub').rglob('*.py')):
        if 'atlas_v2' in path.parts:
            continue
        texts |= set(re.findall(r"QPushButton\(tr\('([^']{2,60})'\)", path.read_text(encoding='utf-8')))
    without = sorted(t for t in texts if button_icons.icon_name(t, 'ru') is None)
    assert len(without) <= 3, without


def test_every_glyph_named_in_the_code_exists():
    # the button «Связи по AIM (Multiwfn)» of Sextant had the glyph 'chart', which there is not — an empty
    # icon (test_toolbar_icons_transparent_and_named); every action_button(…, 'name') and iconify(…, 'name') is checked
    import ast
    from pathlib import Path

    from azimuth.icons import GLYPHS

    drawn = {'label-custom'}  # drawn by GlyphEngine itself (a tag), not from GLYPHS
    root = Path(__file__).resolve().parents[2]
    missing = []
    for path in list((root / 'azimuth').rglob('*.py')) + list((root / 'modules').rglob('*.py')) + list(
            (root / 'hub').rglob('*.py')):
        try:
            tree = ast.parse(path.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            name = getattr(node.func, 'id', None) or getattr(node.func, 'attr', None)
            if name in ('action_button', 'iconify') and len(node.args) >= 3:
                glyph = node.args[2] if name == 'action_button' else node.args[1]
                if isinstance(glyph, ast.Constant) and isinstance(glyph.value, str) and glyph.value not in GLYPHS \
                        and glyph.value not in drawn:
                    missing.append(f'{path.relative_to(root)}:{node.lineno} {glyph.value}')
    assert not missing, missing


def test_no_two_glyphs_are_drawn_alike():
    # «Прозрачный фон» had the eraser of «Очистить модель», «Новый проект с расчётами…» the folder of
    # «Новая вкладка» — two names, one picture; every glyph of the toolbars and of the buttons is now its own drawing
    toolbar = dict(re.findall(r"^    '([a-z0-9-]+)': '(.*?)',", ICONS.read_text(encoding='utf-8'), re.M))
    seen = {}
    for name, glyph in list(toolbar.items()) + list(button_icons.BUTTON_GLYPHS.items()):
        drawing = ' '.join(glyph.split())
        assert drawing not in seen, (name, seen.get(drawing))
        seen[drawing] = name

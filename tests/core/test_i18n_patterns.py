"""The patterns of the translation tables (texts with «{}», azimuth/i18n.py) are matched by their fixed start
and end first and compiled only when used; oracle — a regular expression made from the pattern by hand."""

import re

from azimuth import i18n


def _by_hand(template, text):
    rx = '^' + '(.*?)'.join(re.escape(part) for part in template.split('{}')) + '$'
    return re.match(rx, text, re.S)


def test_a_pattern_matches_as_its_regular_expression():
    pattern = i18n._Pattern('атомов: {}, связей: {}', 'atoms: {}, bonds: {}')
    for text in ('атомов: 3, связей: 2', 'атомов: , связей: ', 'атомов: 3', 'x атомов: 3, связей: 2', ''):
        mine, oracle = pattern.match(text), _by_hand(pattern.template, text)
        assert (mine and mine.groups()) == (oracle and oracle.groups())


def test_patterns_are_compiled_only_when_a_text_fits_them():
    i18n._load()
    assert all(p._rx is None or p._rx.pattern.startswith('^') for p in i18n._PATTERNS['en'])
    fresh = i18n._Pattern('Энергия {} Eh', 'Energy {} Eh')
    assert fresh.match('Частота 5') is None and fresh._rx is None  # another start: no regular expression made
    assert fresh.match('Энергия -76.4 Eh').groups() == ('-76.4',) and fresh._rx is not None


def test_texts_built_at_run_time_are_translated_and_found_back():
    i18n._load()
    template = next(k for k in i18n._TABLES['en'] if k.count('{}') == 1 and i18n._TABLES['en'][k].count('{}') == 1)
    text = template.replace('{}', '42')
    shown = i18n.tr(text, 'en')
    assert shown == i18n._TABLES['en'][template].replace('{}', '42')
    assert i18n.to_source(shown) == text


def test_a_text_joined_of_known_parts_is_retranslated():
    # part by part, and back
    from azimuth import i18n

    try:
        i18n.set_language('en')
        english = i18n.retranslate_text('Настройки задачи · Оптимизация + частоты')
        assert english == i18n.tr('Настройки задачи') + ' · ' + i18n.tr('Оптимизация + частоты') != ''
        assert 'Настройки' not in english
        i18n.set_language('zh')
        chinese = i18n.retranslate_text(english)
        assert chinese == i18n.tr('Настройки задачи', 'zh') + ' · ' + i18n.tr('Оптимизация + частоты', 'zh')
        i18n.set_language('ru')
        assert i18n.retranslate_text(chinese) == 'Настройки задачи · Оптимизация + частоты'
    finally:
        i18n.set_language('ru')

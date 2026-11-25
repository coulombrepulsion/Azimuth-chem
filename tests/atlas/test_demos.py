"""The demonstrations of the Atlas topics (window.DEMO of <topic>.demo.js or of the page itself): what their steps
click must exist. Oracles: the pages and their scripts as text — an id a step names is in the page or is made by
its script; the languages show the same steps. (The steps themselves were run in a browser on 2026-11-11, all 43
topics in three languages; that run is not part of the tests — it needs a browser.)"""

import re
from pathlib import Path

import pytest

WEB = Path(__file__).parents[2] / 'modules' / 'atlas' / 'atlas_v2' / 'quas_atlas' / 'web'
LANGUAGES = ('ru', 'en', 'zh')
ACTION = re.compile(r"\['(click|on|set|scroll)','([^']+)'")


def demo_text(language, topic):
    """The text of window.DEMO of a topic, or None when the topic has no demonstration in this language."""
    separate = WEB / language / 'js' / f'{topic}.demo.js'
    if separate.is_file():
        return separate.read_text(encoding='utf-8')
    page = (WEB / language / f'{topic}.html').read_text(encoding='utf-8')
    found = re.search(r'window\.DEMO=\[.*?\];', page, re.S)
    return found.group(0) if found else None


def topics():
    return sorted(p.name[:-len('.demo.js')] for p in (WEB / 'ru' / 'js').glob('*.demo.js'))


def test_there_are_demonstrations():
    assert len(topics()) == 56


@pytest.mark.parametrize('topic', topics())
def test_every_language_shows_the_same_steps(topic):
    steps = {}
    for language in LANGUAGES:
        text = demo_text(language, topic)
        assert text is not None, f'{language}: no demonstration of {topic}'
        # every action with all it is given (the element, its number, the value), and where the steps begin
        steps[language] = re.findall(r"\{t:|\['(?:click|on|set|scroll|wait)',[^\]]*\]", text)
    assert steps['ru'].count('{t:') >= 2 and steps['en'] == steps['ru'] and steps['zh'] == steps['ru']


@pytest.mark.parametrize('topic', topics())
def test_the_ids_the_steps_name_exist(topic):
    for language in LANGUAGES:
        page = (WEB / language / f'{topic}.html').read_text(encoding='utf-8')
        scripts = ''.join((WEB / language / src).read_text(encoding='utf-8')
                          for src in re.findall(r'<script src="(js/[^"]+)"', page) if not src.endswith('.demo.js'))
        for _, selector in ACTION.findall(demo_text(language, topic)):
            for ident in re.findall(r'#([A-Za-z][\w-]*)', selector):
                in_page = re.search(r'id=["\']?' + re.escape(ident) + r'["\'\s>]', page) is not None
                in_script = re.search(r'''["'`]''' + re.escape(ident) + r'''["'`]''', scripts) is not None \
                    or f'id="{ident}"' in scripts or f"id='{ident}'" in scripts or f'id={ident}' in scripts
                assert in_page or in_script, f'{language}/{topic}: #{ident} of «{selector}» is nowhere'


def test_degenerate_vibrations_choose_a_degenerate_mode_first():
    # the last step asked for the second component of a mode while the mode chosen (ν1, A1g of SF6) has one: the row
    # of the components stayed hidden and the step did nothing (seen in a browser)
    for language in LANGUAGES:
        text = demo_text(language, 'vibrations')
        last = text[text.rindex('{t:'):]
        assert last.index("'#modeTab tr.pick',2]") < last.index("'#cmpG button',1]")

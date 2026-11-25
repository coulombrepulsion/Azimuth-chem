"""The Atlas on the site (azimuth/site.py) — the addresses the program opens."""

import pytest

from azimuth import site


def test_the_addresses():
    # in Russian — the mirror for Russia (ru.azimuth-chem.com), in English and Chinese — the main address
    assert site.atlas() == 'https://ru.azimuth-chem.com/atlas/?lang=ru'
    assert site.atlas('zh') == 'https://www.azimuth-chem.com/atlas/?lang=zh'
    assert site.atlas('de') == 'https://ru.azimuth-chem.com/atlas/?lang=ru'  # not a language of the site
    assert site.atlas('en', 'sym') == 'https://www.azimuth-chem.com/atlas/?lang=en#sym'
    # the site opens in the theme of the program
    assert site.atlas('en', 'sym', 'dark') == 'https://www.azimuth-chem.com/atlas/?lang=en&theme=dark#sym'
    assert site.atlas('ru', None, 'light') == 'https://ru.azimuth-chem.com/atlas/?lang=ru&theme=light'
    assert site.atlas('ru', 'sym') == 'https://ru.azimuth-chem.com/atlas/?lang=ru#sym'
    assert site.atlas('ru', None, 'blue') == site.atlas('ru', None, '<x>') == site.atlas()
    for bad in ('', 'Sym', 'a b', '../x', 'sym#x', 5, 'x' * 13):
        with pytest.raises(ValueError):
            site.atlas('ru', bad)


def test_the_links_of_the_manual_lead_to_topics_of_the_atlas():
    """    every link of the manual to a topic names a topic the Atlas has, in the language of that manual."""
    import re

    from azimuth.paths import ROOT

    index = ROOT / 'modules' / 'atlas' / 'atlas_v2' / 'quas_atlas' / 'web' / 'index.html'
    topics = set(re.findall(r"\{id:'([\w-]+)'", index.read_text(encoding='utf-8')))
    assert len(topics) >= 43  # the topics and the ids of the sections of the overview
    for language in site.LANGUAGES:
        text = (ROOT / 'docs' / 'manual' / f'{language}.md').read_text(encoding='utf-8')
        # the Russian manual leads to the mirror for Russia, as the program does
        host = re.escape(site.home(language).split('//')[1])
        found = re.findall(r'https://' + host + r'atlas/\?lang=(\w+)(?:#(\w+))?\)', text)
        assert language != 'ru' or 'www.azimuth-chem.com/atlas' not in text
        assert len(found) >= 13, language
        for lang, topic in found:
            assert lang == language
            if topic:
                assert topic in topics and site.atlas(lang, topic)

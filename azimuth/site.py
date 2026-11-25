"""The site of Azimuth: the Atlas lives there, the program opens it in the browser.

§1 PURPOSE The Atlas left the window of the program for the site the item «Атлас» of the side panel, its card on the
    home page and the links of the manual open the Atlas of the site in the browser of the system, in the language of
    the program.
§2 RULES SITE is the main address (Cloudflare Pages); the mirror for Russia (MIRROR, ru.azimuth-chem.com, Yandex Object
    Storage) has the same pages. The Atlas in Russian is opened on the mirror, in English and Chinese — on SITE.
    atlas(language, topic=None, theme=None) — the overview of the Atlas or one topic (its key, as data-p of the
    overview: 'post', 'hat', 'sym', …); the language is one of ru, en, zh (anything else — ru). Only the program's own
    words make an address: no text from outside goes into it. Theme 'light' or 'dark' — the site opens in the theme of
    the program (?theme=, kept by the site as its own switch would keep it); anything else — none.
§3 INTERFACE
    SITE; MIRROR; LANGUAGES; THEMES; home(language) -> str; atlas(language='ru', topic=None, theme=None) -> str;
    open_atlas(language='ru', topic=None, theme=None) -> bool (Qt's
    QDesktopServices; True when the system took the address).
§4 TESTS
    tests/core/test_site_links.py."""

import re

SITE = 'https://www.azimuth-chem.com/'
MIRROR = 'https://ru.azimuth-chem.com/'
LANGUAGES = ('ru', 'en', 'zh')
THEMES = ('light', 'dark')
_TOPIC = re.compile(r'[a-z0-9]{1,12}', re.ASCII)


def home(language='ru'):
    """The site for the language: the mirror for Russia in Russian, the main address in the others."""
    return MIRROR if language == 'ru' else SITE


def atlas(language='ru', topic=None, theme=None):
    """The address of the Atlas on the site (the overview, or the topic of that key)."""
    language = language if language in LANGUAGES else 'ru'
    address = f'{home(language)}atlas/?lang={language}'
    if theme in THEMES:
        address += '&theme=' + theme
    if topic is not None:
        if not isinstance(topic, str) or not _TOPIC.fullmatch(topic):
            raise ValueError(f'Not a topic of the Atlas: {topic!r}')
        address += '#' + topic
    return address


def open_atlas(language='ru', topic=None, theme=None):
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    return bool(QDesktopServices.openUrl(QUrl(atlas(language, topic, theme))))

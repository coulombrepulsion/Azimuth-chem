"""Section registry of the Azimuth hub (contract: docs/MODULES.md §4).

hub/modules.json lists the sections in sidebar order. Each entry:
    id one of SECTIONS; unique
    title Russian name (sidebar, window title); en, zh: names for later localisation
    page index of the section page in the shared Studio window (Compass 0, Sextant 1,
           Spectrum 2) or null for the Atlas, which is no page (a link to the site); «crystal» (Компас ·
           Кристалл) shares page 0 with «compass» (Компас · Молекула) — the same page with other menus and tools
    icon file stem in assets/navigation/*.svg (24x24 stroke icon drawn with currentColor)
load() validates the file and raises ValueError with the reason; no Qt here, so the
contract is tested without a display (tests/hub/test_hub_registry.py).
"""

import json
from azimuth.paths import ROOT

SECTIONS = ('atlas', 'compass', 'crystal', 'sextant', 'spectrum')  # «Компас · Кристалл»
NAVIGATION = ROOT / 'assets' / 'navigation'


def load(path=ROOT / 'hub' / 'modules.json'):
    items = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(items, list) or not items:
        raise ValueError('modules.json: expected a non-empty list')
    seen, pages = set(), set()
    for item in items:
        if not isinstance(item, dict):
            raise ValueError('modules.json: every entry must be an object')
        ident = item.get('id')
        if ident not in SECTIONS or ident in seen:
            raise ValueError(f'modules.json: unknown or repeated id {ident!r}')
        seen.add(ident)
        for key in ('title', 'en', 'zh', 'icon'):
            if not isinstance(item.get(key), str) or not item[key].strip():
                raise ValueError(f'modules.json: {ident}.{key} must be a non-empty string')
        page = item.get('page', 'missing')
        if ident == 'atlas':
            if page is not None:
                raise ValueError('modules.json: atlas.page must be null (a link to the site)')
        elif ident == 'crystal':
            if type(page) is not int or page != 0:
                raise ValueError('modules.json: crystal.page must be 0 (the Compass page)')
        elif type(page) is not int or not 0 <= page <= 2 or page in pages:
            raise ValueError(f'modules.json: {ident}.page must be a distinct Studio page 0..2')
        else:
            pages.add(page)
        if not (NAVIGATION / (item['icon'] + '.svg')).is_file():
            raise ValueError(f'modules.json: icon {item["icon"]}.svg not found')
    return items


def icon_svg(item):
    return (NAVIGATION / (item['icon'] + '.svg')).read_text(encoding='utf-8')

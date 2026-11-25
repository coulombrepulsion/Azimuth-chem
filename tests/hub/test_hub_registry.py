"""Section registry of the hub (hub/registry.py, docs/MODULES.md §4); no display needed."""

import json

import pytest

from hub import registry

GOOD = [
    {"id": "atlas", "title": "Атлас", "en": "Atlas", "zh": "图谱", "page": None, "icon": "atlas"},
    {"id": "compass", "title": "Компас · Молекула", "en": "Compass · Molecule", "zh": "罗盘 · 分子", "page": 0, "icon": "compass"},
    {"id": "crystal", "title": "Компас · Кристалл", "en": "Compass · Crystal", "zh": "罗盘 · 晶体", "page": 0, "icon": "crystal"},
    {"id": "sextant", "title": "Секстант", "en": "Sextant", "zh": "六分仪", "page": 1, "icon": "sextant"},
    {"id": "spectrum", "title": "Спектр", "en": "Spectrum", "zh": "光谱", "page": 2, "icon": "spectrum"},
]


def write(tmp_path, items):
    path = tmp_path / 'modules.json'
    path.write_text(json.dumps(items, ensure_ascii=False), encoding='utf-8')
    return path


def test_bundled_registry_is_valid_and_ordered():
    items = registry.load()
    assert [item['id'] for item in items] == ['atlas', 'compass', 'crystal', 'sextant', 'spectrum']
    for item in items:
        assert '<svg' in registry.icon_svg(item) and 'currentColor' in registry.icon_svg(item)


def test_good_registry(tmp_path):
    assert registry.load(write(tmp_path, GOOD)) == GOOD


@pytest.mark.parametrize(
    'change',
    [
        lambda items: items.append(dict(items[1])),  # repeated id
        lambda items: items[1].update(id='unknown'),
        lambda items: items[0].update(page=0),  # the Atlas is a link to the site
        lambda items: items[3].update(page=0),  # Studio page used twice
        lambda items: items[2].update(page=1),  # the crystal section is the Compass page
        lambda items: items[4].update(page=3),
        lambda items: items[4].update(page=True),
        lambda items: items[1].update(title=' '),
        lambda items: items[1].update(icon='missing-icon'),
        lambda items: items[1].pop('page'),
        lambda items: items.clear(),
    ],
)
def test_bad_registry_rejected(tmp_path, change):
    items = json.loads(json.dumps(GOOD))
    change(items)
    with pytest.raises(ValueError):
        registry.load(write(tmp_path, items))

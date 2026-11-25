"""Ready molecules and fragments of the Compass menus.

§1 PURPOSE
    The menus «Молекула», «Фрагмент» and «Файл → Примеры молекул» offer, besides the hand-written
    teaching examples (azimuth.core.EXAMPLES) and the first five fragments (builder), a library
    sorted into groups: inorganic molecules, alkanes, alkenes and alkynes, aromatics, alcohols and
    ethers, carbonyl compounds, N/S/halogen compounds; hydrocarbon, oxygen, N/S and halogen groups.
§2 SOURCE
    library.json, made by tools/build_compass_library.py from SMILES with the Compass's own builder
    and symmetrised to the expected point group (the method and its checks are documented there).
    Starting geometries for a calculation, not optimised structures.
§3 APPLICATIONS
    modules/compass/workspace.py (menus, placing a molecule), azimuth/app.py (File menu),
    modules/compass/chemistry/builder.py (FRAGMENTS, FRAGMENT_BONDS, FRAGMENT_GROUPS).
§4 CONTRACT
    MOLECULE_GROUPS: {group (ru): [key, ...]} in menu order; key = 'Name · formula' (ru).
    molecule(key) -> Molecule with bonds (orders); a key of EXAMPLES gives that example (bonds by
        distance, as before); an unknown key -> KeyError.
    FRAGMENTS: {key: ((symbol, x, y, z), ...)}, FRAGMENT_BONDS: {key: ((i, j, order), ...)},
        FRAGMENT_GROUPS: {group (ru): [key, ...]}; atom 0 is the attachment atom, the open bond
        points to -X (the convention of builder.place_fragment).
    GROUP_NAMES: {group (ru): (en, zh)}; NAMES: {key: (ru, en, zh)} - the translations.
§5 PROCEDURES - below.
§6 NOTES
    Read once at import; about 70 kB. No Qt.
§7 TESTS
    tests/compass/test_compass_library.py.
§8' ROBUSTNESS
    A missing or damaged library.json raises at import: the program is incomplete then, and
    verify_install.py reports the file through assets-manifest.json.
"""

import json
from pathlib import Path

from azimuth.core import EXAMPLES, Molecule, read_xyz

_DATA = json.loads((Path(__file__).with_name('library.json')).read_text(encoding='utf-8'))
if _DATA.get('version') != 1:
    raise ValueError('modules/compass/chemistry/library.json: unknown version')

GROUP_NAMES = {k: tuple(v) for k, v in _DATA['groups'].items()}
MOLECULE_GROUPS, _MOLECULES, NAMES = {}, {}, {}
for _entry in _DATA['molecules']:
    MOLECULE_GROUPS.setdefault(_entry['group'], []).append(_entry['key'])
    _MOLECULES[_entry['key']] = _entry
    NAMES[_entry['key']] = tuple(_entry['names'])

FRAGMENTS, FRAGMENT_BONDS, FRAGMENT_GROUPS = {}, {}, {}
for _entry in _DATA['fragments']:
    FRAGMENTS[_entry['key']] = tuple((a[0], a[1], a[2], a[3]) for a in _entry['atoms'])
    FRAGMENT_BONDS[_entry['key']] = tuple((b[0], b[1], b[2]) for b in _entry['bonds'])
    FRAGMENT_GROUPS.setdefault(_entry['group'], []).append(_entry['key'])


def keys():
    """All molecule keys: the teaching examples first, then the library in menu order."""
    return list(EXAMPLES) + [k for group in MOLECULE_GROUPS.values() for k in group]


def molecule(key):
    from modules.compass.chemistry import user_molecules  # «Мои молекулы» — by name, as the library

    if key in user_molecules.USER:
        return user_molecules.USER[key]
    if key in EXAMPLES:
        return read_xyz(EXAMPLES[key])
    entry = _MOLECULES[key]
    m = read_xyz(entry['xyz'])
    return Molecule(m.title, m.atoms, tuple(tuple(b) for b in entry['bonds']))


def titles():
    """Titles (comment lines) of all ready molecules: a structure still called so is unchanged."""
    return {read_xyz(text).title for text in EXAMPLES.values()} | {
        e['xyz'].split('\n', 2)[1] for e in _MOLECULES.values()
    }

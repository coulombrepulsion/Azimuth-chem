"""«Мои молекулы»: the user's own molecules kept by the program — as «Мои фрагменты» (user_fragments.py).

§1 PURPOSE
    As a fragment can be saved, so can a molecule. A molecule (the whole structure, the atoms chosen, or the molecule of
    an atom) is kept under a name
    and taken again from «Файл → Примеры молекул → Мои молекулы» (into the tab) or from «Молекула» of the building
    (one more molecule put where the field is clicked).
§2 ALGORITHM
    A molecule is its XYZ text (Molecule.xyz) and its bonds with their orders, kept as JSON in the settings of the
    program (fragment_actions.MOLECULES_KEY); USER {name: Molecule} — what library.molecule finds by name, before the
    library itself. The names of the library are not taken (the menus would mix them).
§4 SPECIFICATION GROUP; USER; check_name(name, taken=()) -> name (stripped) | ValueError; cut(molecule, indices) ->
    Molecule (the atoms in their order, the bonds between them renumbered); parse(text) -> {name: Molecule} |
    ValueError; dump(mapping) -> text; register(mapping).
§7 TESTS
    tests/compass/test_user_molecules.py.
"""

import json

from azimuth.core import Molecule, SYMBOLS, read_xyz
from azimuth.i18n import tr

GROUP = 'Мои молекулы'
MAX_ATOMS = 2000
MAX_NAME = 60
USER = {}


def check_name(name, taken=()):
    from modules.compass.chemistry import library

    name = ' '.join(str(name or '').split())
    if not name:
        raise ValueError(tr('Дайте молекуле название.'))
    if len(name) > MAX_NAME:
        raise ValueError(tr('Название длиннее {} знаков.').format(MAX_NAME))
    if name in library.keys() or name == GROUP:
        raise ValueError(tr('Так называется молекула библиотеки — выберите другое название.'))
    if name in taken:
        raise ValueError(tr('Молекула «{}» уже есть в «Моих молекулах».').format(name))
    return name


def cut(molecule, indices):
    """The atoms indices of molecule (in their order) with the bonds between them."""
    from modules.compass.chemistry.builder import connections

    chosen = sorted(set(int(i) for i in indices))
    if not chosen or not all(0 <= i < len(molecule.atoms) for i in chosen):
        raise ValueError(tr('Нет атомов, чтобы сохранить молекулу.'))
    if len(chosen) > MAX_ATOMS:
        raise ValueError(tr('Больше {} атомов — сохраните структуру файлом.').format(MAX_ATOMS))
    where = {old: new for new, old in enumerate(chosen)}
    bonds = tuple((where[a], where[b], o) for a, b, o in connections(molecule) if a in where and b in where)
    return Molecule(molecule.title, tuple(molecule.atoms[i] for i in chosen), bonds)


def _entry(name, molecule):
    return {'name': name, 'xyz': molecule.xyz(), 'bonds': [list(b) for b in (molecule.bonds or ())]}


def parse(text):
    try:
        data = json.loads(text)
    except ValueError as exc:
        raise ValueError(tr('Файл «Моих молекул» повреждён: ') + str(exc)) from exc
    if not isinstance(data, dict) or data.get('format') != 'azimuth-molecules':
        raise ValueError(tr('Это не файл «Моих молекул» «Азимута».'))
    found = {}
    for item in data.get('molecules', []):
        name = str(item.get('name', ''))
        try:
            m = read_xyz(str(item['xyz']))
            n = len(m.atoms)
            bonds = tuple((int(a), int(b), int(o)) for a, b, o in item.get('bonds', []))
            if not m.atoms or any(a.symbol not in SYMBOLS and a.symbol != 'X' for a in m.atoms):
                raise ValueError('atoms')
            if any(not (0 <= a < n and 0 <= b < n and a != b and 0 < o <= 3) for a, b, o in bonds):
                raise ValueError('bonds')
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(tr('Молекула «{}» в файле повреждена.').format(name)) from exc
        found[name] = Molecule(m.title or name, m.atoms, bonds)
    return found


def dump(mapping):
    return json.dumps({'format': 'azimuth-molecules', 'version': 1,
                       'molecules': [_entry(name, m) for name, m in mapping.items()]}, ensure_ascii=False, indent=1)


def register(mapping):
    USER.clear()
    USER.update(mapping)

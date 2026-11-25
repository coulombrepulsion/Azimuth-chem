"""User fragments of Compass: a group cut from a model, kept and reused like the built-in ones.

§1 THEORY
    A fragment is a rigid group of atoms with one attachment atom and one open bond. The built-in
    ones (modules/compass/chemistry/builder.py) are stored in a frame with the attachment atom at the origin and
    the open bond pointing to -X: place_fragment and substitute turn +X onto the direction away from
    the atom the fragment is bonded to. A user fragment is brought into the same frame by a proper
    rigid motion (a shift and a rotation, no reflection, so a chiral group keeps its handedness):
    the attachment atom goes to the origin and the open bond to -X.
§2 ALGORITHM
    1. The chosen atoms (at least one, at most MAX_ATOMS) of the model. The open bond: if exactly one
       chosen atom has a bond to an atom that is not chosen, that atom is the attachment atom and
       the bond is the open bond (a methyl of toluene: its carbon and the bond to the ring). With no
       such bond, the attachment atom is the first chosen atom and the open bond points to the
       freest direction around it (builder.outgoing). With two or more, the choice is refused: the
       group would have several open bonds.
    2. d = unit(outside - attachment) (or the free direction); the frame ex = -d, ey = a unit vector
       normal to d (reference z, or y when d is nearly along z), ez = ex x ey; template coordinates
       ((p - a).ex, (p - a).ey, (p - a).ez). Atom order: the attachment atom first, then the others
       in the order of the model. Bonds: those of the model between chosen atoms, renumbered.
    3. Storage: JSON {"version": 1, "fragments": [{"key", "atoms": [[symbol, x, y, z]], "bonds":
       [[i, j, order]]}]}; every entry is validated when read (dump(parse(text)) is a fixed point).
§3 APPLICATIONS
    modules/compass/actions/fragment_actions.py (menus, saving in the settings of the program, export and
    import); the fragments take part in the «Фрагмент» menu and in placing and substituting.
§4 SPECIFICATION
    cut(molecule, indices) -> (atoms ((symbol, x, y, z), ...), bonds ((i, j, order), ...));
    parse(text) -> {key: (atoms, bonds)} in file order; dump({key: (atoms, bonds)}) -> text;
    check_name(name, taken) -> stripped name; register(fragments) puts them into builder.FRAGMENTS,
    builder.FRAGMENT_BONDS and the group USER_GROUP of builder.FRAGMENT_GROUPS (and removes the user
    fragments that are no longer in fragments). ValueError for every refused input.
§5 PROCEDURES - below.
§6 NOTES
    Coordinates are rounded to ROUND = 6 decimals (1e-6 A) when stored: far below any chemical
    meaning, and the stored text stays short. The built-in names cannot be reused.
§7 TESTS
    tests/compass/test_user_fragments.py.
§8' ROBUSTNESS / ERRORS
    A proper rotation preserves all distances to rounding (1e-12 A here); after storing, to ROUND.
    Damaged entries of a file are refused with the entry named; nothing is registered then.
"""

from math import isfinite, sqrt

from modules.compass.chemistry.builder import connections
from azimuth.core import SYMBOLS
from azimuth.i18n import tr

USER_GROUP = 'Мои фрагменты'
MAX_ATOMS = 200
MAX_NAME = 60
ROUND = 6


def _sub(a, b):
    return tuple(a[k] - b[k] for k in range(3))


def _dot(a, b):
    return sum(a[k] * b[k] for k in range(3))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = sqrt(_dot(a, a))
    if n < 1e-9:
        raise ValueError(tr('Атомы фрагмента совпадают по положению.'))
    return tuple(x / n for x in a)


def cut(molecule, indices):
    """The chosen atoms as a fragment in the frame of builder.FRAGMENTS (see §2)."""
    from modules.compass.chemistry.builder import outgoing

    chosen = list(dict.fromkeys(indices))
    n = len(molecule.atoms)
    if not chosen:
        raise ValueError(tr('Выделите атомы фрагмента.'))
    if any(not 0 <= i < n for i in chosen):
        raise ValueError(tr('Выберите существующий атом.'))
    if len(chosen) > MAX_ATOMS:
        raise ValueError(tr(f'Во фрагменте не больше {MAX_ATOMS} атомов.'))
    inside = set(chosen)
    bonds = connections(molecule)
    open_bonds = [(i, j) if i in inside else (j, i) for i, j, _ in bonds if (i in inside) != (j in inside)]
    if len(open_bonds) > 1:
        raise ValueError(
            tr('У выделенной группы несколько связей с остальной молекулой — выделите группу с одной такой связью.')
        )
    if open_bonds:
        attach, outside = open_bonds[0]
        d = _unit(_sub(molecule.atoms[outside].position, molecule.atoms[attach].position))
    else:
        attach = chosen[0]
        from azimuth.core import Molecule

        own = Molecule('', tuple(molecule.atoms[i] for i in chosen), None)
        d = tuple(outgoing(own, 0))
    a = molecule.atoms[attach].position
    ex = tuple(-x for x in d)
    reference = (0.0, 0.0, 1.0) if abs(d[2]) < 0.9 else (0.0, 1.0, 0.0)
    ey = _unit(_cross(reference, ex))
    ez = _cross(ex, ey)
    order = [attach] + [i for i in chosen if i != attach]
    where = {old: new for new, old in enumerate(order)}
    atoms = []
    for i in order:
        atom = molecule.atoms[i]
        r = _sub(atom.position, a)
        atoms.append((atom.symbol, _dot(r, ex), _dot(r, ey), _dot(r, ez)))
    inner = tuple(
        sorted((min(where[i], where[j]), max(where[i], where[j]), o) for i, j, o in bonds if i in inside and j in inside)
    )
    return tuple(atoms), inner


def check_name(name, taken=()):
    """The name of a new fragment: not empty, not too long, not a built-in or other taken name."""
    from modules.compass.chemistry.builder import FRAGMENTS

    name = ' '.join(str(name).split())
    if not name:
        raise ValueError(tr('Введите название фрагмента.'))
    if len(name) > MAX_NAME:
        raise ValueError(tr(f'Название фрагмента — не длиннее {MAX_NAME} знаков.'))
    builtin = set(FRAGMENTS) - set(USER)
    if name in builtin or tr(name) in {tr(k) for k in builtin}:
        raise ValueError(tr('Так называется встроенный фрагмент — выберите другое название.'))
    if name in taken:
        raise ValueError(tr('Фрагмент с таким названием уже есть.'))
    return name


def _entry(item, number):
    where = tr(f'фрагмент {number}')
    if not isinstance(item, dict):
        raise ValueError(where)
    key = item.get('key')
    atoms, bonds = item.get('atoms'), item.get('bonds', [])
    if not isinstance(key, str) or not key.strip() or len(key) > MAX_NAME:
        raise ValueError(where + tr(': название'))
    if not isinstance(atoms, list) or not 1 <= len(atoms) <= MAX_ATOMS:
        raise ValueError(where + tr(': атомы'))
    parsed = []
    for a in atoms:
        if not isinstance(a, list) or len(a) != 4 or a[0] not in SYMBOLS:
            raise ValueError(where + tr(': атомы'))
        xyz = []
        for v in a[1:]:
            if isinstance(v, bool) or not isinstance(v, (int, float)) or not isfinite(v) or abs(v) > 1e4:
                raise ValueError(where + tr(': координаты'))
            xyz.append(float(v))
        parsed.append((a[0], *xyz))
    if any(abs(v) > 1e-6 for v in parsed[0][1:]):
        raise ValueError(where + tr(': атом присоединения не в начале координат'))
    out_bonds, seen = [], set()
    if not isinstance(bonds, list):
        raise ValueError(where + tr(': связи'))
    for b in bonds:
        if (
            not isinstance(b, list)
            or len(b) != 3
            or not all(isinstance(v, int) and not isinstance(v, bool) for v in b)
            or not (0 <= b[0] < len(parsed) and 0 <= b[1] < len(parsed))
            or b[0] == b[1]
            or b[2] not in (1, 2, 3)
        ):
            raise ValueError(where + tr(': связи'))
        pair = (min(b[0], b[1]), max(b[0], b[1]))
        if pair in seen:
            raise ValueError(where + tr(': связи'))
        seen.add(pair)
        out_bonds.append((*pair, b[2]))
    return ' '.join(key.split()), (tuple(parsed), tuple(sorted(out_bonds)))


def parse(text):
    """{key: (atoms, bonds)} of a fragments file; ValueError naming the first damaged entry."""
    import json

    try:
        data = json.loads(text)
    except (ValueError, TypeError) as exc:
        raise ValueError(tr('Файл фрагментов повреждён.')) from exc
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('fragments'), list):
        raise ValueError(tr('Это не файл фрагментов «Азимута».'))
    out = {}
    for number, item in enumerate(data['fragments'], 1):
        key, value = _entry(item, number)
        if key in out:
            raise ValueError(tr(f'фрагмент {number}') + tr(': название повторяется'))
        out[key] = value
    return out


def dump(fragments):
    import json

    items = [
        {
            'key': key,
            'atoms': [[s, round(x, ROUND), round(y, ROUND), round(z, ROUND)] for s, x, y, z in atoms],
            'bonds': [list(b) for b in bonds],
        }
        for key, (atoms, bonds) in fragments.items()
    ]
    return json.dumps({'version': 1, 'fragments': items}, ensure_ascii=False, indent=1)


USER = {}  # the registered user fragments {key: (atoms, bonds)}


def register(fragments):
    """Make exactly these user fragments available to the menus and the builder."""
    from modules.compass.chemistry import builder

    for key in list(USER):
        if key not in fragments:
            builder.FRAGMENTS.pop(key, None)
            builder.FRAGMENT_BONDS.pop(key, None)
            USER.pop(key)
    for key, (atoms, bonds) in fragments.items():
        if key in builder.FRAGMENTS and key not in USER:
            raise ValueError(tr('Так называется встроенный фрагмент — выберите другое название.'))
        builder.FRAGMENTS[key] = tuple(atoms)
        builder.FRAGMENT_BONDS[key] = tuple(bonds)
        USER[key] = (tuple(atoms), tuple(bonds))
    if USER:
        builder.FRAGMENT_GROUPS[USER_GROUP] = list(USER)
    else:
        builder.FRAGMENT_GROUPS.pop(USER_GROUP, None)

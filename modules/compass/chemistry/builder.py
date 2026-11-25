"""Independent coordinate-based builder. Templates are starting geometries, not optimized structures."""

from dataclasses import replace
from math import cos, sin, pi, sqrt, dist
from azimuth.core import MAX_ATOMS, Atom, Molecule, Z, near_pairs, read_xyz
from azimuth.i18n import tr

RADII = {'H': 0.31, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57, 'Cl': 1.02, 'Br': 1.20, 'I': 1.39, 'S': 1.05, 'P': 1.07}


def add(a, b):
    return tuple(x + y for x, y in zip(a, b))


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def mul(a, s):
    return tuple(x * s for x in a)


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    norm = sqrt(dot(a, a))
    if norm < 1e-9:
        raise ValueError(tr('Направление не определено.'))
    return mul(a, 1 / norm)


_RECENT = []  # [(molecule, bonds)] of the last few structures without explicit bonds


def connections(molecule):
    """Explicit bonds, or bonds by distance (1.22 x the sum of covalent radii — the factor of «Настройки»,
    azimuth.defaults 'bond_factor'), order 1.

    The distance search is O(n^2) and the model asked for it several times per frame; the answer for
    the last four structures is kept. Molecule is a frozen dataclass of tuples, so the same object
    always has the same bonds (looked up by identity, not equality: no hashing of all atoms)."""
    if molecule.bonds is not None:
        return molecule.bonds
    cacheable = isinstance(molecule.atoms, tuple)  # a list could still change in place
    from azimuth import defaults

    factor = defaults.get('bond_factor')
    for known, used, bonds in _RECENT if cacheable else ():
        if known is molecule and used == factor:
            return bonds
    atoms = molecule.atoms
    # candidate pairs by cells of the longest possible bond (was every pair: 1 s at 2000 atoms)
    longest = factor * 2 * max([RADII.get(a.symbol, 0.8) for a in atoms] or [0.8])
    bonds = tuple(
        (j, i, 1)
        for j, i in near_pairs([a.position for a in atoms], longest)
        if atoms[i].symbol != 'X' and atoms[j].symbol != 'X'  # a dummy atom has no bonds
        and dist(atoms[i].position, atoms[j].position)
        <= factor * (RADII.get(atoms[i].symbol, 0.8) + RADII.get(atoms[j].symbol, 0.8))
    )
    if cacheable:
        _RECENT.insert(0, (molecule, factor, bonds))
        del _RECENT[4:]
    return bonds


def checked(molecule):
    if molecule.atoms:
        read_xyz(molecule.xyz())
    if len(molecule.atoms) > MAX_ATOMS:
        raise ValueError(tr(f'Не больше {MAX_ATOMS} атомов в этой версии.'))
    return molecule


def outgoing(molecule, anchor):
    """Choose a free direction, maximizing separation from nearby neighbours."""
    center = molecule.atoms[anchor].position
    neighbours = [
        unit(sub(a.position, center))
        for i, a in enumerate(molecule.atoms)
        if i != anchor and dist(a.position, center) < 2.5
    ]
    candidates = [
        (1, 0, 0),
        (-1 / 3, sqrt(8 / 9), 0),
        (-1 / 3, -sqrt(2 / 9), sqrt(2 / 3)),
        (-1 / 3, -sqrt(2 / 9), -sqrt(2 / 3)),
    ]
    if not neighbours:
        return candidates[0]
    for i in range(100):
        z = 1 - 2 * (i + 0.5) / 100
        radius = sqrt(1 - z * z)
        angle = pi * (3 - sqrt(5)) * i
        candidates.append((radius * cos(angle), radius * sin(angle), z))
    return min(candidates, key=lambda v: max(dot(v, n) for n in neighbours))


# Single bonds that the sum of covalent radii describes badly (lone pairs on both atoms), in angstrom
# : H2O2 O-O 1.474 (gas; verified 2026-10-23 via webqc.org, «Hydrogen Peroxide»), H2SO4
# S-OH 1.574 (verified 2026-10-23 via webqc.org, «Sulfuric acid»). Multiple bonds keep the radii model.
SINGLE_BONDS = {frozenset(('O',)): 1.474, frozenset(('O', 'S')): 1.574}


def covalent_single(a, b):
    """The single-bond length from the covalent radii (the base of the multiple-bond lengths)."""
    return max(0.5, RADII.get(a, 0.8) + RADII.get(b, 0.8))


def bond_length(a, b, order=1):
    if order == 1 and frozenset((a, b)) in SINGLE_BONDS:
        return SINGLE_BONDS[frozenset((a, b))]
    return max(0.5, covalent_single(a, b) * {1: 1.0, 2: 0.9, 3: 0.84}[order])


def aimed(molecule, anchor, direction):
    """The direction of a new bond on anchor — the one aimed (a unit vector), else the freest one (outgoing)."""
    if direction is not None:
        size = sqrt(dot(direction, direction))
        if size > 1e-9:
            return tuple(c / size for c in direction)
    return outgoing(molecule, anchor)


def place_atom(molecule, symbol, position, anchor=None, order=1, length=0, direction=None):
    if symbol not in Z:
        raise ValueError(tr('Неизвестный элемент.'))
    if order not in (1, 2, 3):
        raise ValueError(tr('Порядок связи: 1, 2 или 3.'))
    edges = connections(molecule)
    if anchor is not None:
        if not 0 <= anchor < len(molecule.atoms):
            raise ValueError(tr('Выберите существующий атом.'))
        start = molecule.atoms[anchor]
        direction = aimed(molecule, anchor, direction)
        position = add(start.position, mul(direction, length or bond_length(start.symbol, symbol, order)))
        edges = edges + ((anchor, len(molecule.atoms), order),)
    return checked(Molecule(molecule.title, molecule.atoms + (Atom(symbol, *position),), edges))


# All coordinates are hand-authored approximate starting geometries in angstroms.
# Attachment atom is index 0, open attachment direction is -X.
FRAGMENTS = {
    'Метил · —CH₃': (('C', 0, 0, 0), ('H', 0.363, 1.027, 0), ('H', 0.363, -0.514, 0.889), ('H', 0.363, -0.514, -0.889)),
    'Гидроксил · —OH': (('O', 0, 0, 0), ('H', 0.25, 0.93, 0)),
    'Амино · —NH₂': (('N', 0, 0, 0), ('H', 0.337, 0.952, 0), ('H', 0.337, -0.476, 0.825)),
    'Карбонил · >C=O': (('C', 0, 0, 0), ('O', 0, 1.22, 0)),
    'Фенил · —C₆H₅': (
        ('C', 0, 0, 0),
        ('C', 0.7, 1.2124, 0),
        ('C', 2.1, 1.2124, 0),
        ('C', 2.8, 0, 0),
        ('C', 2.1, -1.2124, 0),
        ('C', 0.7, -1.2124, 0),
        ('H', 0.16, 2.1477, 0),
        ('H', 2.64, 2.1477, 0),
        ('H', 3.88, 0, 0),
        ('H', 2.64, -2.1477, 0),
        ('H', 0.16, -2.1477, 0),
    ),
}
FRAGMENT_BONDS = {
    'Метил · —CH₃': ((0, 1, 1), (0, 2, 1), (0, 3, 1)),
    'Гидроксил · —OH': ((0, 1, 1),),
    'Амино · —NH₂': ((0, 1, 1), (0, 2, 1)),
    'Карбонил · >C=O': ((0, 1, 2),),
    'Фенил · —C₆H₅': (
        (0, 1, 2),
        (1, 2, 1),
        (2, 3, 2),
        (3, 4, 1),
        (4, 5, 2),
        (0, 5, 1),
        (1, 6, 1),
        (2, 7, 1),
        (3, 8, 1),
        (4, 9, 1),
        (5, 10, 1),
    ),
}


# the five fragments above stay first in the menus; the library adds grouped ones
BASIC_FRAGMENTS = tuple(FRAGMENTS)
from modules.compass.chemistry import library as _library  # noqa: E402  (json only; no import cycle)

FRAGMENTS.update(_library.FRAGMENTS)
FRAGMENT_BONDS.update(_library.FRAGMENT_BONDS)
FRAGMENT_GROUPS = _library.FRAGMENT_GROUPS


def place_fragment(molecule, name, position, anchor=None, order=1, length=0, direction=None):
    if name not in FRAGMENTS:
        raise ValueError(tr('Неизвестный фрагмент.'))
    template = FRAGMENTS[name]
    toward, direction = direction, (1, 0, 0)
    edges = list(connections(molecule))
    offset = len(molecule.atoms)
    if anchor is not None:
        if not 0 <= anchor < offset:
            raise ValueError(tr('Выберите существующий атом.'))
        direction = aimed(molecule, anchor, toward)
        atom = molecule.atoms[anchor]
        position = add(atom.position, mul(direction, length or bond_length(atom.symbol, template[0][0], order)))
        edges.append((anchor, offset, order))
    # Orthonormal frame maps template +X to the chosen outgoing direction.
    reference = (0, 0, 1) if abs(direction[2]) < 0.9 else (0, 1, 0)
    ey = unit(cross(reference, direction))
    ez = cross(direction, ey)
    atoms = tuple(
        Atom(symbol, *add(position, add(mul(direction, x), add(mul(ey, y), mul(ez, z)))))
        for symbol, x, y, z in template
    )
    edges.extend((a + offset, b + offset, o) for a, b, o in FRAGMENT_BONDS[name])
    return checked(Molecule(molecule.title, molecule.atoms + atoms, tuple(edges)))


def move_atom(molecule, index, position):
    atoms = list(molecule.atoms)
    atoms[index] = Atom(atoms[index].symbol, *position)
    return checked(Molecule(molecule.title, tuple(atoms), connections(molecule)))


def delete_atoms(molecule, indices):
    indices = set(indices)
    mapping = {old: new for new, old in enumerate(i for i in range(len(molecule.atoms)) if i not in indices)}
    atoms = tuple(a for i, a in enumerate(molecule.atoms) if i not in indices)
    edges = tuple(
        (mapping[a], mapping[b], o) for a, b, o in connections(molecule) if a not in indices and b not in indices
    )
    return Molecule(molecule.title, atoms, edges)


def place_molecule(molecule, piece, position):
    """Add the molecule piece with its centre at position; no bond to the existing atoms."""
    if not piece.atoms:
        raise ValueError(tr('Пустая молекула.'))
    centre = tuple(sum(a.position[k] for a in piece.atoms) / len(piece.atoms) for k in range(3))
    shift = sub(position, centre)
    offset = len(molecule.atoms)
    atoms = tuple(Atom(a.symbol, *add(a.position, shift)) for a in piece.atoms)
    edges = tuple(connections(molecule)) + tuple((i + offset, j + offset, o) for i, j, o in connections(piece))
    title = molecule.title if molecule.atoms else piece.title
    return checked(Molecule(title, molecule.atoms + atoms, edges))


# a structure drawn in the field has the origin at its centre (the mean of the atoms: the first atom
# itself, the middle of the bond for two); the editor keeps it so (workspace.load_edit) while the structure was centred
CENTRE_TOLERANCE = 1e-3  # Å


def centre_of(molecule):
    atoms = molecule.atoms
    return tuple(sum(a.position[k] for a in atoms) / len(atoms) for k in range(3)) if atoms else (0.0, 0.0, 0.0)


def is_centred(molecule):
    return max(abs(c) for c in centre_of(molecule)) < CENTRE_TOLERANCE


def centred(molecule):
    """The molecule moved so that its centre is the origin, and the shift taken away from every atom."""
    shift = centre_of(molecule)
    atoms = tuple(Atom(a.symbol, *sub(a.position, shift)) for a in molecule.atoms)
    return replace(molecule, atoms=atoms), shift


def set_bond(molecule, a, b, order):
    if a == b or not all(0 <= i < len(molecule.atoms) for i in (a, b)):
        raise ValueError(tr('Выберите два разных атома.'))
    if order not in (0, 1, 2, 3):
        raise ValueError(tr('Недопустимый порядок связи.'))
    a, b = sorted((a, b))
    edges = tuple((i, j, o) for i, j, o in connections(molecule) if {i, j} != {a, b})
    if order:
        edges += ((a, b, order),)
    return replace(molecule, bonds=edges)

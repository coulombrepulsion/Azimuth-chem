"""Compass: the same molecule? — a key of a structure by its atoms and bonds, not its coordinates.

HEADER Adding a molecule the project already has asks first. Two structures are the same molecule when their formulas
    and their graphs of bonds are the same, whatever the order of the atoms or the orders of the bonds. The same
    molecule again is the same structure with the same shape — a conformer (another shape of the same graph) is not
    asked about. Wilkinson convention, sections 1-8.
§2 ALGORITHM
    The bonds: the stored ones, else by distance (builder.connections). Weisfeiler–Lehman: every atom starts with its
    element; four times it takes its element and the sorted labels of its neighbours (a short hash). The key is the
    formula and the sorted labels. The shape: for every pair of elements, the sorted distances between their atoms
    — the same, within SHAPE_TOLERANCE Å each, for two copies of one geometry however turned, moved or numbered;
    a turn about a bond changes the distances across it. Mirror images have the same distances (one shape here).
§4 SPECIFICATION
    structure_key(molecule) -> tuple; same_structure(a, b) -> bool; same_shape(a, b) -> bool (of the same structure);
    find_same(molecule, candidates, shape=True) -> index | None, candidates [(name, molecule)].
§7 TESTS
    tests/compass/test_identity.py."""

import hashlib

ROUNDS = 4
SHAPE_TOLERANCE = 0.1  # Å: a copy written to a file and read back, a structure tidied a little — the same shape


def _short(text):
    return hashlib.blake2b(text.encode('utf-8'), digest_size=6).hexdigest()


def structure_key(molecule):
    from modules.compass.chemistry.builder import connections

    atoms = [a for a in molecule.atoms]
    count = len(atoms)
    neighbours = [[] for _ in range(count)]
    for bond in connections(molecule):
        i, j = bond[0], bond[1]
        if 0 <= i < count and 0 <= j < count and i != j:
            neighbours[i].append(j)
            neighbours[j].append(i)
    labels = [a.symbol for a in atoms]
    for _ in range(ROUNDS):
        labels = [_short(labels[i] + '(' + ','.join(sorted(labels[k] for k in neighbours[i])) + ')')
                  for i in range(count)]
    return molecule.formula, tuple(sorted(labels))


def same_structure(a, b):
    if a.formula != b.formula or len(a.atoms) != len(b.atoms):
        return False
    return structure_key(a) == structure_key(b)


def _distances(molecule):
    from math import dist

    atoms = molecule.atoms
    table = {}
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            pair = tuple(sorted((atoms[i].symbol, atoms[j].symbol)))
            table.setdefault(pair, []).append(dist(atoms[i].position, atoms[j].position))
    return {pair: sorted(values) for pair, values in table.items()}


def same_shape(a, b, tolerance=SHAPE_TOLERANCE):
    """Two structures of the same graph with the same geometry (not two conformers)."""
    one, other = _distances(a), _distances(b)
    if one.keys() != other.keys():
        return False
    return all(len(one[k]) == len(other[k]) and all(abs(x - y) <= tolerance for x, y in zip(one[k], other[k]))
               for k in one)


def find_same(molecule, candidates, shape=True):
    """The index of the first of candidates [(name, molecule)] that is the same molecule, or None; shape — and of
    the same geometry (a conformer is another one)."""
    key = None
    for index, (_, other) in enumerate(candidates):
        if other is None or other.formula != molecule.formula or len(other.atoms) != len(molecule.atoms):
            continue
        key = key or structure_key(molecule)
        if structure_key(other) == key and (not shape or same_shape(molecule, other)):
            return index
    return None

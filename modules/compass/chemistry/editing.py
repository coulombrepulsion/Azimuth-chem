"""Quick structure edits of Compass: hydrogens by valence, H → group, element change.

Hydrogens. The bond orders are the stored ones (set with the right click on a bond), or, for a
structure whose bonds were found by distance, estimated from the length relative to the single
bond of the two atoms (builder.bond_length): below 0.82 → triple, below 0.90 → double, below
0.95 → aromatic (1.5), else single (C≡C 0.79, C=O 0.85, C=C 1.34 Å / 1.52 = 0.88, benzene 0.91).
A structure whose bonds were found by distance keeps them so (the new hydrogens too). The number
of missing hydrogens is the usual valence (C 4, N 3, O 2, S 2, P 3, B 3, Si 4, halogens 1) minus the
sum of the orders. They are placed by the VSEPR shape of the atom (shape below) at the X–H bond
length of builder.bond_length. A starting structure for an optimization, not an optimized one.

Shape. The steric number of an atom is its number of neighbours n plus its lone pairs
L = floor((V − Σ orders) / 2), V the valence electrons (B 3, C 4, N 5, O 6, …; aromatic bonds count
1.5): 2 → linear, 3 → trigonal, 4 or more → tetrahedral (lone pairs take the free positions). So
CO₂, HCN and allene are linear, SO₂ bent (n 2 + L 1), SO₃ trigonal, H₂SO₄ tetrahedral and DMSO
pyramidal, while C, N and O in ordinary organic molecules keep their former shapes. Elements without
a V in the table keep the former rule: linear with a triple bond or two double bonds, trigonal with a
double or aromatic bond, tetrahedral otherwise. (Before, two double bonds always meant linear: SO₂
came out linear and the oxygens of SO₃ and H₂SO₄ fell onto each other.)

Substitution. A click with a fragment on a terminal atom (usually H) replaces it: the fragment is
bonded to the neighbour along the old bond. An element change keeps the atom and its bonds; a
terminal atom is moved along its bond to the new bond length.
"""

from math import cos, pi, radians, sin, sqrt, dist

from azimuth.core import Atom, Molecule
from modules.compass.chemistry.builder import (
    FRAGMENTS,
    FRAGMENT_BONDS,
    bond_length,
    covalent_single,
    checked,
    connections,
    delete_atoms,
    add,
    sub,
    mul,
    dot,
    cross,
    unit,
)
from azimuth.i18n import tr

VALENCE = {
    'C': 4,
    'Si': 4,
    'Ge': 4,
    'N': 3,
    'P': 3,
    'As': 3,
    'B': 3,
    'O': 2,
    'S': 2,
    'Se': 2,
    'F': 1,
    'Cl': 1,
    'Br': 1,
    'I': 1,
}
LONE_PAIRS = {'N', 'P', 'As', 'O', 'S', 'Se'}
TETRAHEDRAL = radians(109.4712206)


def bonds_with_orders(molecule):
    """Bonds (i, j, order); orders estimated from lengths when the bonds were found by distance."""
    if molecule.bonds is not None:
        return tuple(molecule.bonds)
    result = []
    for i, j, _ in connections(molecule):
        a, b = molecule.atoms[i], molecule.atoms[j]
        ratio = dist(a.position, b.position) / covalent_single(a.symbol, b.symbol)  # thresholds: radii model
        order = 1
        if 'H' not in (a.symbol, b.symbol) and a.symbol in VALENCE and b.symbol in VALENCE:
            order = 3 if ratio < 0.82 else 2 if ratio < 0.90 else 1.5 if ratio < 0.95 else 1
        result.append((i, j, order))
    return tuple(result)


def perceived_orders(molecule):
    """Bond orders from valences, for a structure with hydrogens (robust to rough geometry).

    Every bond starts single; atoms with free valence (usual valence − number of neighbours) are
    paired along their bonds, the relatively shortest bonds first, until none is left; six-membered
    rings of alternating single and double bonds become aromatic (1.5). A structure without any
    hydrogen is read from the bond lengths instead (bonds_with_orders): its free valences are the
    missing hydrogens, not multiple bonds."""
    if molecule.bonds is not None:
        return tuple(molecule.bonds)
    atoms = molecule.atoms
    if not any(a.symbol == 'H' for a in atoms):
        return bonds_with_orders(molecule)
    edges = [[i, j, 1] for i, j, _ in connections(molecule)]
    degree = [0] * len(atoms)
    for i, j, _ in edges:
        degree[i] += 1
        degree[j] += 1
    free = [max(0, VALENCE.get(a.symbol, 0) - degree[k]) if a.symbol in VALENCE else 0 for k, a in enumerate(atoms)]
    ratio = lambda e: (
        dist(atoms[e[0]].position, atoms[e[1]].position) / covalent_single(atoms[e[0]].symbol, atoms[e[1]].symbol)
    )
    changed = True
    while changed:
        changed = False
        for e in sorted(edges, key=ratio):
            i, j = e[0], e[1]
            if free[i] > 0 and free[j] > 0 and e[2] < 3:
                e[2] += 1
                free[i] -= 1
                free[j] -= 1
                changed = True
                break
    return aromatize(len(atoms), [(i, j, o) for i, j, o in edges])


def aromatize(count, bonds):
    """Six-membered rings of alternating single and double bonds get order 1.5; repeated until nothing
    changes, so that the second ring of naphthalene follows the first."""
    order = {(min(i, j), max(i, j)): o for i, j, o in bonds}
    neighbours = [[] for _ in range(count)]
    for i, j, _ in bonds:
        neighbours[i].append(j)
        neighbours[j].append(i)
    rings = _rings6(neighbours)
    before = None
    while before != order:
        before = dict(order)
        _aromatize_pass(rings, order)
    return tuple((i, j, order[(min(i, j), max(i, j))]) for i, j, _ in bonds)


def _aromatize_pass(rings, order):
    for ring in rings:
        pairs = [(min(ring[k], ring[(k + 1) % 6]), max(ring[k], ring[(k + 1) % 6])) for k in range(6)]
        values = [order[p] for p in pairs]
        if (
            all(v in (1, 2, 1.5) for v in values)
            and sum(1 for v in values if v in (2, 1.5)) >= 3
            and all(not (values[k] == 1 and values[(k + 1) % 6] == 1) for k in range(6))
        ):
            for p in pairs:
                order[p] = 1.5


def _rings6(neighbours):
    found = set()
    for start in range(len(neighbours)):
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            if len(path) == 6:
                if start in neighbours[node]:
                    found.add(tuple(sorted(path)) + (tuple(path),))
                continue
            for nxt in neighbours[node]:
                if nxt > start and nxt not in path:
                    stack.append((nxt, path + [nxt]))
    seen, rings = set(), []
    for key in found:
        if key[:6] not in seen:
            seen.add(key[:6])
            rings.append(list(key[6]))
    return rings


def _perpendicular(v):
    ref = (0, 0, 1) if abs(v[2]) < 0.9 else (1, 0, 0)
    return unit(cross(v, ref))


VALENCE_ELECTRONS = {
    'H': 1,
    'B': 3,
    'C': 4,
    'Si': 4,
    'N': 5,
    'P': 5,
    'As': 5,
    'O': 6,
    'S': 6,
    'Se': 6,
    'F': 7,
    'Cl': 7,
    'Br': 7,
    'I': 7,
}


def shape(symbol, orders):
    """'linear', 'trigonal' or 'tetrahedral' for an atom with bonds of these orders (all of them)."""
    valence = VALENCE_ELECTRONS.get(symbol)
    if valence is None:  # the former rule
        if any(o >= 3 for o in orders) or sum(1 for o in orders if o == 2) >= 2:
            return 'linear'
        return 'trigonal' if any(o in (2, 1.5) for o in orders) else 'tetrahedral'
    lone = max(0, int((valence - sum(orders)) // 2))
    steric = len(orders) + lone
    return 'linear' if steric <= 2 else ('trigonal' if steric == 3 else 'tetrahedral')


def _directions(molecule, i, bonds, missing, orders=None):
    """Unit vectors for `missing` new bonds of atom i, by its shape (orders: of all its bonds, if
    some of them are not in `bonds` yet; otherwise the new bonds are single)."""
    centre = molecule.atoms[i].position
    neighbours = [j if k == i else k for k, j, _ in bonds if i in (k, j)]
    vectors = [unit(sub(molecule.atoms[j].position, centre)) for j in neighbours]
    orders = [o for k, j, o in bonds if i in (k, j)] + [1] * missing if orders is None else orders
    form = shape(molecule.atoms[i].symbol, orders)
    triple, trigonal = form == 'linear', form == 'trigonal'
    if triple:
        if vectors:
            return [mul(vectors[0], -1)][:missing]
        return [(1, 0, 0), (-1, 0, 0)][:missing]
    if trigonal:
        if not vectors:
            return [(1, 0, 0), (-0.5, sqrt(3) / 2, 0), (-0.5, -sqrt(3) / 2, 0)][:missing]
        if len(vectors) >= 2:
            return [_away(vectors[:2])][:missing]
        a = vectors[0]
        # keep the plane of the double-bond partner's substituents (ethylene stays planar)
        partner = neighbours[0]
        others = [
            unit(sub(molecule.atoms[j].position, molecule.atoms[partner].position))
            for k, j, _ in bonds
            for j in ((j if k == partner else k),)
            if partner in (k, j) and j != i
        ]
        p = None
        for v in others:
            w = sub(v, mul(a, dot(v, a)))
            if dot(w, w) > 1e-6:
                p = unit(w)
                break
        p = p or _perpendicular(a)
        c, s = cos(radians(120)), sin(radians(120))
        return [unit(add(mul(a, c), mul(p, s))), unit(add(mul(a, c), mul(p, -s)))][:missing]
    # tetrahedral
    if not vectors:
        base = [(1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1)]
        return [unit(v) for v in base][:missing]
    if len(vectors) == 1:
        a = vectors[0]
        # stagger against the substituents of the neighbour, as in ethane
        partner = neighbours[0]
        others = [
            unit(sub(molecule.atoms[j].position, molecule.atoms[partner].position))
            for k, j, _ in bonds
            for j in ((j if k == partner else k),)
            if partner in (k, j) and j != i
        ]
        p = None
        for v in others:
            w = sub(v, mul(a, dot(v, a)))
            if dot(w, w) > 1e-6:
                p = unit(mul(w, -1))
                break
        p = p or _perpendicular(a)
        q = cross(a, p)
        ca, sa = cos(TETRAHEDRAL), sin(TETRAHEDRAL)
        return [
            unit(add(mul(a, ca), mul(add(mul(p, cos(t)), mul(q, sin(t))), sa))) for t in (0, 2 * pi / 3, 4 * pi / 3)
        ][:missing]
    if len(vectors) == 2:
        a, b = vectors
        m = _away(vectors)
        try:
            n = unit(cross(a, b))
        except ValueError:  # a and b along one line: 0.106.15 — a straight chain of a drawing (opposite): the other
            n = cross(a, m)  # perpendicular; the same way (atoms on top of each other): any, as before
            n = unit(n) if dot(n, n) > 1e-12 else _perpendicular(a)
        half = TETRAHEDRAL / 2
        return [unit(add(mul(m, cos(half)), mul(n, sin(half)))), unit(add(mul(m, cos(half)), mul(n, -sin(half))))][
            :missing
        ]
    flat = _flat_normal(vectors[:3])
    if flat is not None:  # three bonds in one plane with the atom (a flat drawing) — the H out of it (a wedge)
        return [flat][:missing]
    return [_away(vectors[:3])][:missing]


def _flat_normal(vectors):
    """An sp³ atom whose three bonds lie in one plane with it — the two CH of a ring fusion got their H in that plane,
    towards each other, 0.07 Å apart, and the structure was left without any hydrogens. The normal of the plane (+, the
    same side for all — neighbours' H stay 1.5 Å apart) when the bonds are within ~3° of a plane; None otherwise."""
    if len(vectors) < 3:
        return None
    normal = cross(vectors[0], vectors[1])
    if dot(normal, normal) < 1e-6:
        normal = cross(vectors[0], vectors[2])
    if dot(normal, normal) < 1e-6:
        return None
    normal = unit(normal)
    if abs(dot(vectors[2], normal)) > 0.05 or abs(dot(vectors[1], normal)) > 0.05:
        return None
    return normal if normal[2] >= 0 else mul(normal, -1)


def _away(vectors):
    """The direction away from the
    bonds — minus their sum; when they cancel (a CH₂ in a straight chain, a CH with three bonds at 120° — as a flat
    drawing has them), the sum is zero and «Направление не определено» left the whole structure without its hydrogens:
    then the normal of their plane (out of the drawing), or any perpendicular for a straight line."""
    total = vectors[0]
    for v in vectors[1:]:
        total = add(total, v)
    if dot(total, total) > 1e-18:  # as unit() before: any sum that is not zero keeps its direction
        return unit(mul(total, -1))
    if len(vectors) >= 2:
        normal = cross(vectors[0], vectors[1])
        if dot(normal, normal) > 1e-6:
            return unit(normal)
    return _perpendicular(vectors[0])


def missing_hydrogens(molecule, i, bonds=None):
    symbol = molecule.atoms[i].symbol
    if symbol not in VALENCE:
        return 0
    bonds = bonds_with_orders(molecule) if bonds is None else bonds
    used = sum(o for k, j, o in bonds if i in (k, j))
    return max(0, VALENCE[symbol] - int(used + 0.5))


def add_hydrogens(molecule, indices=None):
    """Fill the valences of the given atoms (all heavy atoms if None) with hydrogens."""
    bonds = list(bonds_with_orders(molecule))
    atoms = list(molecule.atoms)
    targets = range(len(atoms)) if indices is None else indices
    added = 0
    for i in list(targets):
        if atoms[i].symbol == 'H':
            continue
        current = Molecule(molecule.title, tuple(atoms), tuple(bonds))
        count = missing_hydrogens(current, i, bonds)
        if not count:
            continue
        length = bond_length(atoms[i].symbol, 'H', 1)
        for d in _directions(current, i, bonds, count):
            atoms.append(Atom('H', *add(atoms[i].position, mul(d, length))))
            bonds.append((i, len(atoms) - 1, 1))
            added += 1
    if molecule.bonds is None:  # bonds by distance: the orders stay readable from the lengths
        return checked(Molecule(molecule.title, tuple(atoms), None)), added
    return checked(Molecule(molecule.title, tuple(atoms), tuple((i, j, int(o)) for i, j, o in bonds))), added


SKELETON_LIMIT = 3000  # atoms; a bigger file (a protein) is opened as it is — too slow and rarely wanted


def skeleton_hydrogens(molecule, limit=SKELETON_LIMIT, charged=()):
    """0.91.10 («Достраивать водороды у файлов без H»): (the molecule with the hydrogens up to the valence, how many
    were added) when the file has the heavy atoms only — not one hydrogen, and some atom of VALENCE short of its
    valence; otherwise (the molecule, 0). A structure with some hydrogens is never touched: they were written on
    purpose (a radical, an ion, a part of a structure). Without bonds in the file, only with two bonded
    carbons (an organic skeleton)."""
    atoms = molecule.atoms if molecule is not None else ()
    if not atoms or len(atoms) > limit or any(a.symbol in ('H', 'D') for a in atoms):
        return molecule, 0
    if not any(a.symbol in VALENCE for a in atoms):
        return molecule, 0
    # a file with its bonds (MOL, SDF, MOL2: a database without H — methanol is C–O there) or, without bonds
    # (XYZ, PDB: the orders guessed from the lengths), an organic skeleton — two carbons bonded (≤ 1.75 Å); CO, NO₂,
    # O₃ … in an XYZ are real molecules without hydrogens (CO from a file became HCO)
    carbons = [a for a in atoms if a.symbol == 'C']
    if not molecule.bonds and not any((p.x - q.x) ** 2 + (p.y - q.y) ** 2 + (p.z - q.z) ** 2 <= 1.75 ** 2
                                      for k, p in enumerate(carbons) for q in carbons[k + 1:]):
        return molecule, 0
    try:  # an atom with a formal charge in the file (O⁻ of nitrate, Cl⁻) gets none — it is the ion
        if charged:
            return add_hydrogens(molecule, [k for k in range(len(atoms)) if k not in set(charged)])
        return add_hydrogens(molecule)
    except ValueError:  # a structure the builder refuses (overlapping atoms…): as it is
        return molecule, 0


def make_room(molecule, index, order=1, toward=None):
    """0.55.0 («Достраивать водороды при построении»): before a new bond of this order on atom index, remove
    the terminal hydrogens that would make it over-valent (the last ones in the file first; with toward,
    the direction aimed by a drag — those nearest to it). Returns (molecule, the new index of the atom)."""
    symbol = molecule.atoms[index].symbol
    if symbol not in VALENCE:
        return molecule, index
    bonds = bonds_with_orders(molecule)
    used = sum(o for k, j, o in bonds if index in (k, j))
    extra = int(used + order + 0.5) - VALENCE[symbol]
    if extra <= 0:
        return molecule, index
    degree = {}
    for k, j, _ in bonds:
        degree[k] = degree.get(k, 0) + 1
        degree[j] = degree.get(j, 0) + 1
    hydrogens = [
        j if k == index else k
        for k, j, _ in bonds
        if index in (k, j) and molecule.atoms[j if k == index else k].symbol == 'H' and degree[j if k == index else k] == 1
    ]
    if toward is not None:
        centre = molecule.atoms[index].position

        def along(h):
            v = tuple(molecule.atoms[h].position[k] - centre[k] for k in range(3))
            size = sqrt(sum(c * c for c in v)) or 1.0
            return sum(v[k] * toward[k] for k in range(3)) / size

        hydrogens = sorted(hydrogens, key=along)  # the nearest to the aim last
    else:
        hydrogens = sorted(hydrogens)
    gone = hydrogens[-extra:] if extra < len(hydrogens) else hydrogens
    if not gone:
        return molecule, index
    from modules.compass.chemistry.builder import delete_atoms

    return delete_atoms(molecule, gone), index - sum(1 for g in gone if g < index)


def hydrogens_for(molecule, indices):
    """The valences of these atoms (the heavy ones) filled with hydrogens, extra hydrogens removed."""
    from modules.compass.chemistry.builder import delete_atoms

    bonds = bonds_with_orders(molecule)
    degree = {}
    for k, j, _ in bonds:
        degree[k] = degree.get(k, 0) + 1
        degree[j] = degree.get(j, 0) + 1
    gone = set()
    for i in indices:
        symbol = molecule.atoms[i].symbol
        if symbol == 'H' or symbol not in VALENCE:
            continue
        used = sum(o for k, j, o in bonds if i in (k, j))
        extra = int(used + 0.5) - VALENCE[symbol]
        hs = sorted(
            (j if k == i else k)
            for k, j, _ in bonds
            if i in (k, j) and molecule.atoms[j if k == i else k].symbol == 'H' and degree[j if k == i else k] == 1
        )
        if extra > 0:
            gone.update(hs[-extra:])
    keep = [i for i in indices if i not in gone]
    if gone:
        keep = [i - sum(1 for g in gone if g < i) for i in keep]
        molecule = delete_atoms(molecule, gone)
    return add_hydrogens(molecule, keep)[0]


def substitute(molecule, index, fragment):
    """Replace the terminal atom index (usually H) by the fragment (a FRAGMENTS key) bonded along the old bond."""
    if fragment not in FRAGMENTS:
        raise ValueError(tr('Неизвестный фрагмент.'))
    bonds = connections(molecule)
    neighbours = [j if k == index else k for k, j, _ in bonds if index in (k, j)]
    if len(neighbours) != 1:
        raise ValueError(tr('Заменить фрагментом можно только концевой атом с одной связью.'))
    anchor = neighbours[0]
    direction = unit(sub(molecule.atoms[index].position, molecule.atoms[anchor].position))
    stripped = delete_atoms(molecule, [index])
    anchor -= 1 if anchor > index else 0
    template = FRAGMENTS[fragment]
    start = stripped.atoms[anchor]
    position = add(start.position, mul(direction, bond_length(start.symbol, template[0][0], 1)))
    ref = (0, 0, 1) if abs(direction[2]) < 0.9 else (0, 1, 0)
    ey = unit(cross(ref, direction))
    ez = cross(direction, ey)
    offset = len(stripped.atoms)
    new = tuple(Atom(s, *add(position, add(mul(direction, x), add(mul(ey, y), mul(ez, z))))) for s, x, y, z in template)
    edges = (
        list(connections(stripped))
        + [(anchor, offset, 1)]
        + [(a + offset, b + offset, o) for a, b, o in FRAGMENT_BONDS[fragment]]
    )
    return checked(Molecule(molecule.title, stripped.atoms + new, tuple(edges)))


def change_element(molecule, index, symbol):
    """The atom index becomes symbol; a terminal atom is moved to the new bond length."""
    bonds = connections(molecule)
    atoms = list(molecule.atoms)
    atom = atoms[index]
    neighbours = [(j if k == index else k, o) for k, j, o in bonds if index in (k, j)]
    position = atom.position
    if len(neighbours) == 1:
        j, order = neighbours[0]
        d = unit(sub(atom.position, atoms[j].position))
        position = add(
            atoms[j].position, mul(d, bond_length(atoms[j].symbol, symbol, order if order in (1, 2, 3) else 1))
        )
    atoms[index] = Atom(symbol, *position)
    return checked(Molecule(molecule.title, tuple(atoms), tuple(bonds)))



def bond_by_replacing(molecule, anchor, target, symbol, order=1, length=0):
    """The atom target becomes symbol and is bonded to anchor with this order; its other bonds stay. A target of another
    molecule (not connected to anchor) brings its molecule along, unturned: the target at the bond length from anchor
    along the line anchor → target. A target of the same molecule closes a ring where it is. The bonds are the ones
    before the move (explicit ones), so the distance does not make or break any."""
    from modules.compass.chemistry.builder import set_bond

    count = len(molecule.atoms)
    if anchor == target or not (0 <= anchor < count and 0 <= target < count):
        raise ValueError(tr('Выберите два разных атома.'))
    bonds = tuple(connections(molecule))
    atoms = list(molecule.atoms)
    start = atoms[anchor]
    if target not in connected(molecule, anchor):
        line = sub(atoms[target].position, start.position)
        direction = unit(line) if dot(line, line) > 1e-12 else (1.0, 0.0, 0.0)
        place = add(start.position, mul(direction, length or bond_length(start.symbol, symbol, order)))
        shift = sub(place, atoms[target].position)
        for i in connected(molecule, target):
            atoms[i] = Atom(atoms[i].symbol, *add(atoms[i].position, shift))
    atoms[target] = Atom(symbol, *atoms[target].position)
    return checked(set_bond(Molecule(molecule.title, tuple(atoms), bonds), anchor, target, order))

# -- selection tools -----------------------------------------------------------------------
def connected(molecule, index):
    """All atoms connected to index through bonds (its molecule or fragment)."""
    neighbours = [[] for _ in molecule.atoms]
    for i, j, _ in connections(molecule):
        neighbours[i].append(j)
        neighbours[j].append(i)
    seen, stack = {index}, [index]
    while stack:
        for j in neighbours[stack.pop()]:
            if j not in seen:
                seen.add(j)
                stack.append(j)
    return sorted(seen)


def chain(molecule, index):
    """The unbranched piece of a chain with index («Цепочка» of the move tools, as in Chemcraft).

    Heavy atoms (not H) with at most two heavy neighbours and outside rings are chain atoms; the piece is
    the chain atoms connected to index through chain atoms, up to the nearest branch or ring atom (that
    one is not taken), with the hydrogens of the taken atoms. A hydrogen stands for its heavy atom; a
    branch or ring atom pressed itself: that atom with its hydrogens. A molecule of hydrogens only:
    connected()."""
    count = len(molecule.atoms)
    neighbours = [set() for _ in range(count)]
    for i, j, _ in connections(molecule):
        neighbours[i].add(j)
        neighbours[j].add(i)
    heavy = [a.symbol != 'H' for a in molecule.atoms]
    if not heavy[index]:
        parents = [j for j in neighbours[index] if heavy[j]]
        if not parents:
            return connected(molecule, index)
        index = parents[0]

    def reach(i, j):  # j from i without the bond i–j: the bond is in a ring
        stack = [k for k in neighbours[i] if k != j]
        seen = {i, *stack}
        while stack:
            for k in neighbours[stack.pop()]:
                if k == j:
                    return True
                if k not in seen:
                    seen.add(k)
                    stack.append(k)
        return False

    ring = [any(reach(i, j) for j in neighbours[i]) for i in range(count)]

    def is_chain(i):
        return heavy[i] and not ring[i] and sum(heavy[j] for j in neighbours[i]) <= 2

    taken, stack = {index}, [index] if is_chain(index) else []
    while stack:
        for j in neighbours[stack.pop()]:
            if j not in taken and is_chain(j):
                taken.add(j)
                stack.append(j)
    taken |= {j for i in list(taken) for j in neighbours[i] if not heavy[j]}
    return sorted(taken)


def mirror(molecule, indices, axis):
    """Reflect the atoms (all if indices is empty) through the plane through their centre normal to
    axis 'x', 'y' or 'z' (YZ, XZ or XY plane). A whole molecule becomes its mirror image."""
    k = 'xyz'.index(axis)
    chosen = set(indices) if indices else set(range(len(molecule.atoms)))
    centre = sum(molecule.atoms[i].position[k] for i in chosen) / len(chosen)
    atoms = []
    for i, a in enumerate(molecule.atoms):
        p = list(a.position)
        if i in chosen:
            p[k] = 2 * centre - p[k]
        atoms.append(Atom(a.symbol, *p))
    return checked(Molecule(molecule.title, tuple(atoms), connections(molecule)))


def paste(molecule, piece):
    """Add the atoms of piece; moved aside (along x) if they would overlap the structure."""
    if not piece.atoms:
        raise ValueError(tr('В буфере обмена нет атомов.'))
    shift = (0.0, 0.0, 0.0)
    if molecule.atoms and min(dist(a.position, b.position) for a in molecule.atoms for b in piece.atoms) < 1.0:
        top = max(a.x for a in molecule.atoms)
        low = min(b.x for b in piece.atoms)
        shift = (top - low + 3.0, 0.0, 0.0)
    offset = len(molecule.atoms)
    atoms = tuple(Atom(a.symbol, *add(a.position, shift)) for a in piece.atoms)
    edges = tuple(connections(molecule)) + tuple((i + offset, j + offset, o) for i, j, o in connections(piece))
    return checked(Molecule(molecule.title, molecule.atoms + atoms, edges)), list(range(offset, offset + len(atoms)))


def piece_from_text(text):
    """Atoms from the clipboard: an XYZ block, or lines 'symbol x y z'."""
    from azimuth.core import read_xyz

    text = text.strip()
    try:
        return read_xyz(text)
    except ValueError:
        rows = [l.split() for l in text.splitlines() if l.strip()]
        try:
            return read_xyz(f'{len(rows)}\n\n' + '\n'.join(' '.join(r[:4]) for r in rows))
        except (ValueError, IndexError):
            raise ValueError(tr('В буфере обмена нет координат: нужен XYZ или строки «элемент x y z».')) from None


def selection_xyz(molecule, indices):
    chosen = sorted(indices) if indices else range(len(molecule.atoms))
    rows = [molecule.atoms[i] for i in chosen]
    return f'{len(rows)}\n{molecule.title}\n' + ''.join(
        f'{a.symbol:<2} {a.x: .8f} {a.y: .8f} {a.z: .8f}\n' for a in rows
    )

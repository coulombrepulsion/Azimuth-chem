"""Compass: the structure tools of the menus «Правка» and «Инструменты», as in Chemcraft.

§1 PURPOSE
    The user asked for the menus of Compass to hold everything Chemcraft has there, except what lives in other parts of
    Azimuth (input files — Sextant, spectra and results — Spectrum). These are the operations Compass did not have:
    selection by steps, by numbers and by a box of coordinates; moving the frame of coordinates (origin at an atom,
    axes on three atoms, two atoms along an axis, inversion, a small random displacement); removing overlapping atoms;
    bonds found again or removed around the selection; a dummy atom at the centre of the selection; and the data of the
    structure — principal axes and moments of inertia, rotational constants, counts of atoms and bonds, the separate
    fragments, the exact (monoisotopic) and average masses.
§2 ALGORITHM
    Pure functions of a Molecule (azimuth.core); nothing here touches Qt. Bonds are the stored ones or found by distance
    (builder.connections). Rotations are orthonormal 3 × 3 matrices applied to every atom. The inertia tensor is
    diagonalised by Jacobi rotations (3 × 3, symmetric; converged to 1e-12), principal moments in ascending order
    (I_A ≤ I_B ≤ I_C), the frame right-handed. Rotational constants: B = h / (8π² c I) = 16.857629 / I cm⁻¹ and
    505379.0 / I MHz for I in amu·Å².
§3 APPLICATIONS
    modules/compass/actions/structure_actions.py (the Qt actions of the menus), hub/window.py (the menus of the
    section).
§4 SPECIFICATION expand(molecule, indices) -> sorted indices with their bonded neighbours; parse_numbers(text, count,
    symbols=None) -> indices (0-based) from «1-5, 8 10» or «C1–C5, O8»; numbers_text(indices) -> «1–5, 8, 10»;
    in_box(molecule, lo, hi) -> indices with lo[k] ≤ x_k ≤ hi[k] (None: no limit); origin_at(molecule, i);
    axes_on(molecule, i, j, k); along(molecule, i, j, axis 'x'|'y'|'z'); inverted(molecule); shaken(molecule,
    amplitude=0.01, seed=None); overlapping(molecule, limit=0.5) -> indices to remove; rebonded(molecule);
    without_bonds_of(molecule, indices); with_element(molecule, indices, symbol); with_dummy_at_centre(molecule,
    indices) -> (molecule, new index); inertia(molecule) -> {'moments', 'axes', 'centre', 'B_cm', 'B_mhz', 'kind'};
    principal_frame(molecule); statistics(molecule) -> {'atoms': {symbol: n}, 'bonds': {'C–H': n, …}, 'count',
    'bond_count'}; fragments(molecule) -> [sorted indices of each connected part], largest first; masses(molecule) ->
    {'formula', 'exact', 'average', 'missing'}; bond_angles(molecule, indices=None) -> [(i, j, k)]; pairs(indices) ->
    [(i, j)]. Whole(molecule, indices); selected_first(molecule, indices) -> (molecule, order);
    hydrogens_after(molecule) -> (molecule, order); without_bonds(molecule); transformed(molecule, indices, shift=(dx,
    dy, dz), angle=°, axis='x'|'y'|'z', through=(i, j)|None); plane(molecule, indices) -> {'centre', 'normal',
    'deviations', 'rms', 'largest'}; planes(molecule, first, second) -> {'first', 'second', 'angle', 'centres',
    'b_from_a', 'a_from_b', 'offset'}.
§5 PROCEDURES — below.
§6 NOTES
    Dummy atoms X have no mass and are left out of inertia and masses; they stay in the coordinate operations.
    A function that cannot act (too few atoms, atoms on one line) raises ValueError with a message for the user.
§7 TESTS
    tests/compass/test_structure_tools.py (water, benzene, two waters, numbers, boxes, frames).
§8' ROBUSTNESS
    Exact arithmetic is not needed: coordinates are printed to 8 decimals; the tests use tolerances of 1e-6 Å.
"""

from math import sqrt
import random

from azimuth.core import DUMMY, Atom, Molecule
from azimuth.i18n import tr
from modules.compass.chemistry.builder import connections

# monoisotopic masses of the most abundant isotopes (as modules/spectrum/analysis/thermo.MASSES, kept here so Compass does not
# need Spectrum) and standard atomic weights (IUPAC, abridged), amu
from modules.spectrum.analysis.thermo import MASSES as EXACT

AVERAGE = {
    'H': 1.008, 'He': 4.0026, 'Li': 6.94, 'Be': 9.0122, 'B': 10.81, 'C': 12.011, 'N': 14.007, 'O': 15.999,
    'F': 18.998, 'Ne': 20.180, 'Na': 22.990, 'Mg': 24.305, 'Al': 26.982, 'Si': 28.085, 'P': 30.974, 'S': 32.06,
    'Cl': 35.45, 'Ar': 39.95, 'K': 39.098, 'Ca': 40.078, 'Sc': 44.956, 'Ti': 47.867, 'V': 50.942, 'Cr': 51.996,
    'Mn': 54.938, 'Fe': 55.845, 'Co': 58.933, 'Ni': 58.693, 'Cu': 63.546, 'Zn': 65.38, 'Ga': 69.723, 'Ge': 72.630,
    'As': 74.922, 'Se': 78.971, 'Br': 79.904, 'Kr': 83.798, 'Rb': 85.468, 'Sr': 87.62, 'Y': 88.906, 'Zr': 91.224,
    'Nb': 92.906, 'Mo': 95.95, 'Ru': 101.07, 'Rh': 102.91, 'Pd': 106.42, 'Ag': 107.87, 'Cd': 112.41, 'In': 114.82,
    'Sn': 118.71, 'Sb': 121.76, 'Te': 127.60, 'I': 126.90, 'Xe': 131.29, 'Cs': 132.91, 'Ba': 137.33, 'La': 138.91,
    'Hf': 178.49, 'Ta': 180.95, 'W': 183.84, 'Re': 186.21, 'Os': 190.23, 'Ir': 192.22, 'Pt': 195.08, 'Au': 196.97,
    'Hg': 200.59, 'Tl': 204.38, 'Pb': 207.2, 'Bi': 208.98,
}
B_CM = 16.857629  # h / (8π² c) in cm⁻¹ · amu · Å²
B_MHZ = 505379.0  # the same in MHz · amu · Å²


# -- selection ---------------------------------------------------------------------------------------------------
def _neighbours(molecule):
    near = [[] for _ in molecule.atoms]
    for i, j, _ in connections(molecule):
        near[i].append(j)
        near[j].append(i)
    return near


def expand(molecule, indices):
    """The selection with every atom bonded to it (one step, as «Expand selection» of Chemcraft)."""
    near = _neighbours(molecule)
    chosen = set(indices)
    for i in list(chosen):
        if 0 <= i < len(near):
            chosen.update(near[i])
    return sorted(chosen)


def parse_numbers(text, count, symbols=None):
    """Atom numbers typed by the user (1-based: «1-5, 8 10», «3–7»; «C1–C5, O8», «H» with symbols) as 0-based
    indices; ValueError for a bad part."""
    from azimuth import atom_labels

    return [n - 1 for n in atom_labels.parse(text, count, symbols)]


def numbers_text(indices, symbols=None):
    """0-based indices as 1-based numbers with ranges: [0, 1, 2, 4] -> «1–3, 5» («C1–C3, O5» with symbols)."""
    from azimuth import atom_labels

    return atom_labels.text([i + 1 for i in indices], symbols)


def in_box(molecule, lo, hi):
    """Atoms with lo[k] ≤ coordinate k ≤ hi[k] for x, y, z (Å); a None limit is open."""
    found = []
    for i, atom in enumerate(molecule.atoms):
        p = atom.position
        if all((lo[k] is None or p[k] >= lo[k]) and (hi[k] is None or p[k] <= hi[k]) for k in range(3)):
            found.append(i)
    return found


def pairs(indices):
    """Every pair of the indices (for «all interatomic distances» of a selection)."""
    s = sorted(set(indices))
    return [(s[a], s[b]) for a in range(len(s)) for b in range(a + 1, len(s))]


def bond_angles(molecule, indices=None):
    """Every bond angle i–j–k (j the vertex) of the molecule, or of the selected atoms only."""
    near = _neighbours(molecule)
    keep = None if indices is None else set(indices)
    result = []
    for j, around in enumerate(near):
        around = sorted(around)
        for a in range(len(around)):
            for b in range(a + 1, len(around)):
                triple = (around[a], j, around[b])
                if keep is None or all(t in keep for t in triple):
                    result.append(triple)
    return result


# -- frames of coordinates --------------------------------------------------------------------------------------
def _moved(molecule, function):
    atoms = tuple(Atom(a.symbol, *function(a.position)) for a in molecule.atoms)
    return Molecule(molecule.title, atoms, molecule.bonds)


def _sub(a, b):
    return tuple(a[k] - b[k] for k in range(3))


def _dot(a, b):
    return sum(a[k] * b[k] for k in range(3))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(v):
    n = sqrt(_dot(v, v))
    if n < 1e-9:
        raise ValueError(tr('Атомы совпадают или лежат на одной прямой — направление не определено.'))
    return tuple(c / n for c in v)


def _frame(molecule, origin, rows):
    """Coordinates in the frame with this origin and these axes (rows of an orthonormal matrix)."""
    return _moved(molecule, lambda p: tuple(_dot(r, _sub(p, origin)) for r in rows))


def origin_at(molecule, i):
    """The origin of coordinates moved to atom i (the orientation kept)."""
    o = molecule.atoms[i].position
    return _moved(molecule, lambda p: _sub(p, o))


def axes_on(molecule, i, j, k):
    """Origin at atom i, X towards atom j, atom k in the XY plane (Y > 0), as a Z-matrix frame."""
    o = molecule.atoms[i].position
    x = _unit(_sub(molecule.atoms[j].position, o))
    v = _sub(molecule.atoms[k].position, o)
    z = _unit(_cross(x, v))
    y = _cross(z, x)
    return _frame(molecule, o, (x, y, z))


def along(molecule, i, j, axis):
    """Atom i at the origin and atom j on the positive half of the axis 'x', 'y' or 'z' (the smallest turn)."""
    o = molecule.atoms[i].position
    d = _unit(_sub(molecule.atoms[j].position, o))
    target = {'x': (1.0, 0.0, 0.0), 'y': (0.0, 1.0, 0.0), 'z': (0.0, 0.0, 1.0)}[axis]
    rotation = _turn(d, target)
    return _moved(molecule, lambda p: _apply(rotation, _sub(p, o)))


def _turn(a, b):
    """The rotation matrix taking unit vector a to unit vector b (Rodrigues; the half turn for opposite vectors)."""
    c = _dot(a, b)
    axis = _cross(a, b)
    s = sqrt(_dot(axis, axis))
    if s < 1e-12:
        if c > 0:
            return ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        helper = (1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0)
        axis, c, s = _unit(_cross(a, helper)), -1.0, 0.0
    else:
        axis = tuple(v / s for v in axis)
    x, y, z = axis
    t = 1 - c
    return ((t * x * x + c, t * x * y - s * z, t * x * z + s * y),
            (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
            (t * x * z - s * y, t * y * z + s * x, t * z * z + c))


def _apply(m, p):
    return tuple(_dot(row, p) for row in m)


def inverted(molecule):
    """Every coordinate with its sign changed (inversion through the origin)."""
    return _moved(molecule, lambda p: (-p[0], -p[1], -p[2]))


def shaken(molecule, amplitude=0.01, seed=None):
    """Every atom moved at random by up to `amplitude` Å along each axis (to leave a symmetric saddle point)."""
    rng = random.Random(seed)
    return _moved(molecule, lambda p: tuple(c + rng.uniform(-amplitude, amplitude) for c in p))


# -- atoms and bonds ------------------------------------------------------------------------------------------------
def overlapping(molecule, limit=0.5):
    """Atoms closer than `limit` Å to an earlier atom (the later one of each pair is to be removed)."""
    from azimuth.core import near_pairs  # by cells, not over all pairs

    return sorted({i for j, i in near_pairs([a.position for a in molecule.atoms], limit, strict=True)})


def without(molecule, indices):
    """The molecule without these atoms (stored bonds renumbered)."""
    drop = set(indices)
    keep = [k for k in range(len(molecule.atoms)) if k not in drop]
    new = {old: n for n, old in enumerate(keep)}
    bonds = None
    if molecule.bonds is not None:
        bonds = tuple((new[i], new[j], o) for i, j, o in molecule.bonds if i in new and j in new)
    return Molecule(molecule.title, tuple(molecule.atoms[k] for k in keep), bonds)


def rebonded(molecule):
    """The bonds found again from the distances (stored bonds and orders forgotten)."""
    return Molecule(molecule.title, molecule.atoms, None)


def without_bonds_of(molecule, indices):
    """Every bond that touches a selected atom removed (the others kept, with their orders)."""
    chosen = set(indices)
    bonds = tuple((i, j, o) for i, j, o in connections(molecule) if i not in chosen and j not in chosen)
    return Molecule(molecule.title, molecule.atoms, bonds)


def with_element(molecule, indices, symbol):
    """The selected atoms made atoms of `symbol` (positions and bonds kept)."""
    chosen = set(indices)
    atoms = tuple(Atom(symbol, *a.position) if k in chosen else a for k, a in enumerate(molecule.atoms))
    return Molecule(molecule.title, atoms, molecule.bonds)


def with_dummy_at_centre(molecule, indices):
    """A dummy atom X at the geometric centre of the selected atoms (for a Z-matrix, a ring centre); its index."""
    chosen = [molecule.atoms[i] for i in indices]
    if not chosen:
        raise ValueError(tr('Выделите атомы, в центр которых поставить точку X.'))
    centre = tuple(sum(a.position[k] for a in chosen) / len(chosen) for k in range(3))
    bonds = None if molecule.bonds is None else tuple(molecule.bonds)
    return Molecule(molecule.title, tuple(molecule.atoms) + (Atom(DUMMY, *centre),), bonds), len(molecule.atoms)


# -- data of the structure ------------------------------------------------------------------------------------------
def _jacobi(a):
    """Eigenvalues and eigenvectors (columns) of a symmetric 3 × 3 matrix."""
    a = [list(row) for row in a]
    v = [[1.0 if i == j else 0.0 for j in range(3)] for i in range(3)]
    for _ in range(100):
        off = max((abs(a[p][q]), p, q) for p in range(3) for q in range(p + 1, 3))
        if off[0] < 1e-12:
            break
        _, p, q = off
        theta = 0.5 * (a[q][q] - a[p][p]) / a[p][q]
        t = (1.0 if theta >= 0 else -1.0) / (abs(theta) + sqrt(theta * theta + 1.0))
        c = 1.0 / sqrt(t * t + 1.0)
        s = t * c
        for k in range(3):
            akp, akq = a[k][p], a[k][q]
            a[k][p], a[k][q] = c * akp - s * akq, s * akp + c * akq
        for k in range(3):
            apk, aqk = a[p][k], a[q][k]
            a[p][k], a[q][k] = c * apk - s * aqk, s * apk + c * aqk
        for k in range(3):
            vkp, vkq = v[k][p], v[k][q]
            v[k][p], v[k][q] = c * vkp - s * vkq, s * vkp + c * vkq
    return [a[i][i] for i in range(3)], v


def inertia(molecule):
    """Principal moments of inertia (amu·Å², ascending), their axes (unit vectors), the centre of mass, rotational
    constants (cm⁻¹ and MHz; None for a zero moment) and the kind of top."""
    atoms = [a for a in molecule.atoms if a.symbol != DUMMY]
    if not atoms:
        raise ValueError(tr('В структуре нет атомов.'))
    mass = [EXACT.get(a.symbol, AVERAGE.get(a.symbol, 0.0)) for a in atoms]
    total = sum(mass)
    centre = tuple(sum(m * a.position[k] for m, a in zip(mass, atoms)) / total for k in range(3))
    tensor = [[0.0] * 3 for _ in range(3)]
    for m, a in zip(mass, atoms):
        r = _sub(a.position, centre)
        r2 = _dot(r, r)
        for i in range(3):
            for j in range(3):
                tensor[i][j] += m * ((r2 if i == j else 0.0) - r[i] * r[j])
    values, vectors = _jacobi(tensor)
    order = sorted(range(3), key=lambda k: values[k])
    moments = [max(0.0, values[k]) for k in order]
    axes = [tuple(vectors[r][k] for r in range(3)) for k in order]
    if _dot(_cross(axes[0], axes[1]), axes[2]) < 0:  # right-handed
        axes[2] = tuple(-c for c in axes[2])
    b_cm = [B_CM / m if m > 1e-8 else None for m in moments]
    b_mhz = [B_MHZ / m if m > 1e-8 else None for m in moments]
    a_, b_, c_ = moments
    big = max(moments) or 1.0
    near = lambda x, y: abs(x - y) <= 1e-3 * big
    if len(atoms) == 1:
        kind = 'atom'
    elif a_ <= 1e-3 * big:
        kind = 'linear'
    elif near(a_, b_) and near(b_, c_):
        kind = 'spherical'
    elif near(a_, b_) or near(b_, c_):
        kind = 'symmetric'
    else:
        kind = 'asymmetric'
    return {'moments': moments, 'axes': axes, 'centre': centre, 'B_cm': b_cm, 'B_mhz': b_mhz, 'kind': kind}


def principal_frame(molecule):
    """The molecule with the origin at its centre of mass and X, Y, Z along the principal axes A, B, C."""
    data = inertia(molecule)
    return _frame(molecule, data['centre'], data['axes'])


def statistics(molecule):
    """Counts of atoms by element and of bonds by the pair of elements («C–H», «C=O» for orders 2, «C≡N» for 3)."""
    atoms = {}
    for a in molecule.atoms:
        atoms[a.symbol] = atoms.get(a.symbol, 0) + 1
    bonds = {}
    sign = {1: '–', 1.5: '…', 2: '=', 3: '≡'}
    for i, j, order in connections(molecule):
        x, y = sorted((molecule.atoms[i].symbol, molecule.atoms[j].symbol), key=lambda s: (s != 'C', s == 'H', s))
        key = f'{x}{sign.get(order, "–")}{y}'
        bonds[key] = bonds.get(key, 0) + 1
    return {'atoms': dict(sorted(atoms.items(), key=lambda kv: (-kv[1], kv[0]))),
            'bonds': dict(sorted(bonds.items(), key=lambda kv: (-kv[1], kv[0]))),
            'count': len(molecule.atoms), 'bond_count': sum(bonds.values())}


def fragments(molecule):
    """The connected parts of the structure (molecules of a cluster, ions of a salt), the largest first."""
    near = _neighbours(molecule)
    seen, parts = set(), []
    for start in range(len(molecule.atoms)):
        if start in seen:
            continue
        part, stack = {start}, [start]
        while stack:
            for j in near[stack.pop()]:
                if j not in part:
                    part.add(j)
                    stack.append(j)
        seen |= part
        parts.append(sorted(part))
    return sorted(parts, key=lambda p: (-len(p), p[0]))


def masses(molecule):
    """The formula, the exact (monoisotopic: most abundant isotopes) and the average molecular mass, amu; elements
    without data in `missing`."""
    exact = average = 0.0
    missing = set()
    for a in molecule.atoms:
        if a.symbol == DUMMY:
            continue
        if a.symbol in EXACT and a.symbol in AVERAGE:
            exact += EXACT[a.symbol]
            average += AVERAGE[a.symbol]
        else:
            missing.add(a.symbol)
    return {'formula': molecule.formula, 'exact': exact, 'average': average, 'missing': sorted(missing)}


# -- «Правка» — the whole molecule, the order of the atoms, all bonds off, shift and turn, planes -------------
def whole(molecule, indices):
    """The selection grown to the whole of each molecule it touches («Expand selection as much…» of Chemcraft)."""
    chosen = set(indices)
    return sorted(i for part in fragments(molecule) if chosen & set(part) for i in part)


def _renumbered(molecule, order):
    """Atom k of the result is atom order[k]; the stored bonds follow (bonds by distance are found again anyway)."""
    if sorted(order) != list(range(len(molecule.atoms))):
        raise ValueError('order must be a permutation of the atoms')
    where = {old: new for new, old in enumerate(order)}
    bonds = None if molecule.bonds is None else tuple(
        (min(where[i], where[j]), max(where[i], where[j]), o) for i, j, o in molecule.bonds)
    return Molecule(molecule.title, tuple(molecule.atoms[j] for j in order), bonds)


def selected_first(molecule, indices):
    """The selected atoms become 1, 2, 3… in the order they were selected (clicked); the others follow in their
    order — for the fragment of CDA, the first atoms of a Z-matrix, the same numbering in two files. → (molecule,
    order)."""
    first = [i for i in dict.fromkeys(indices) if 0 <= i < len(molecule.atoms)]
    if not first:
        raise ValueError(tr('Выделите атомы в том порядке, в каком им дать номера 1, 2, 3…'))
    order = first + [i for i in range(len(molecule.atoms)) if i not in set(first)]
    return _renumbered(molecule, order), order


def hydrogens_after(molecule):
    """Every hydrogen right after the heavy atom it is bonded to (C1 H2 H3 C4 H5…), the heavy atoms in their order;
    a hydrogen bonded to nothing heavy stays at the end. → (molecule, order)."""
    near = _neighbours(molecule)
    heavy = [i for i, a in enumerate(molecule.atoms) if a.symbol != 'H']
    order, placed = [], set()
    for i in heavy:
        order.append(i)
        for j in sorted(near[i]):
            if molecule.atoms[j].symbol == 'H' and j not in placed:
                order.append(j)
                placed.add(j)
    order += [i for i, a in enumerate(molecule.atoms) if a.symbol == 'H' and i not in placed]
    return _renumbered(molecule, order), order


def without_bonds(molecule):
    """«Удалить все связи»: none stored (an empty tuple — not None, which means «by distance»)."""
    return Molecule(molecule.title, molecule.atoms, ())


def _rotation(axis, angle_deg):
    """The rotation matrix by angle (degrees, counter-clockwise looking against the axis) about a unit axis (Rodrigues)."""
    from math import cos, radians, sin

    x, y, z = axis
    c, s = cos(radians(angle_deg)), sin(radians(angle_deg))
    t = 1 - c
    return ((t * x * x + c, t * x * y - s * z, t * x * z + s * y),
            (t * x * y + s * z, t * y * y + c, t * y * z - s * x),
            (t * x * z - s * y, t * y * z + s * x, t * z * z + c))


def transformed(molecule, indices, shift=(0.0, 0.0, 0.0), angle=0.0, axis='z', through=None):
    """«Сдвинуть и повернуть…»: the atoms of indices (all when empty) turned by angle (°) about an axis — 'x', 'y', 'z'
    through their centre, or the line through two atoms through=(i, j) — and then moved by shift (Å)."""
    n = len(molecule.atoms)
    chosen = sorted(set(indices)) or list(range(n))
    if through is not None:
        i, j = through
        point = molecule.atoms[i].position
        direction = _unit(_sub(molecule.atoms[j].position, point))
    else:
        points = [molecule.atoms[k].position for k in chosen]
        point = tuple(sum(p[k] for p in points) / len(points) for k in range(3))
        direction = {'x': (1.0, 0.0, 0.0), 'y': (0.0, 1.0, 0.0), 'z': (0.0, 0.0, 1.0)}[axis]
    turn = _rotation(direction, angle)
    keep = set(chosen)
    atoms = []
    for k, a in enumerate(molecule.atoms):
        if k in keep:
            r = _sub(a.position, point)
            p = tuple(point[m] + _dot(turn[m], r) + shift[m] for m in range(3))
            atoms.append(Atom(a.symbol, *p))
        else:
            atoms.append(a)
    return Molecule(molecule.title, tuple(atoms), molecule.bonds)


def plane(molecule, indices):
    """The best plane through the atoms (least squares: the normal is the direction of the smallest spread of the
    centred coordinates) → {'centre', 'normal', 'deviations' (signed, Å, per atom), 'rms', 'largest' (index)}."""
    import numpy as np

    chosen = list(dict.fromkeys(indices))
    if len(chosen) < 3:
        raise ValueError(tr('Для плоскости нужны хотя бы три атома.'))
    xyz = np.array([molecule.atoms[i].position for i in chosen], float)
    centre = xyz.mean(axis=0)
    _, values, vt = np.linalg.svd(xyz - centre)
    if len(values) > 1 and values[1] < 1e-6:
        raise ValueError(tr('Атомы лежат на одной прямой — плоскость не определена.'))
    normal = vt[2]
    deviations = (xyz - centre) @ normal
    k = int(np.argmax(np.abs(deviations)))
    return {'centre': tuple(map(float, centre)), 'normal': tuple(map(float, normal)),
            'deviations': [(i, float(d)) for i, d in zip(chosen, deviations)],
            'rms': float(np.sqrt(np.mean(deviations ** 2))), 'largest': chosen[k]}


def planes(molecule, first, second):
    """Two planes and how they stand: the angle between them (0–90°), the distance between the centres, the distance
    of each centre from the other plane and the shift of the centres along the plane (offset, as for π-stacking)."""
    from math import acos, degrees

    a, b = plane(molecule, first), plane(molecule, second)
    cosine = min(1.0, abs(_dot(a['normal'], b['normal'])))
    between = _sub(b['centre'], a['centre'])
    distance = sqrt(_dot(between, between))
    b_from_a = abs(_dot(between, a['normal']))
    return {'first': a, 'second': b, 'angle': degrees(acos(cosine)), 'centres': distance,
            'b_from_a': b_from_a, 'a_from_b': abs(_dot(between, b['normal'])),
            'offset': sqrt(max(0.0, distance ** 2 - b_from_a ** 2))}


# -- «Инструменты → Таблица внутренних координат…» ---------------------------------------------------------
def internal_coordinates(molecule):
    """Every bond length (Å), every valence angle (°, i–j–k with j the vertex) and every dihedral (°, i–j–k–l over the
    bond j–k, −180…180) of the bonded structure (Enumerate internal coordinates of Chemcraft). Dummy atoms X left
    out. → {'bonds': [(i, j, d)], 'angles': [(i, j, k, a)], 'dihedrals': [(i, j, k, l, φ)]}, 0-based, sorted."""
    from modules.compass.chemistry.geometry_tools import measurement

    atoms = molecule.atoms
    near = _neighbours(molecule)
    real = [a.symbol != 'X' for a in atoms]
    bonds = sorted((min(i, j), max(i, j)) for i, j, _ in connections(molecule) if real[i] and real[j])

    def value(*indices):
        found = measurement([atoms[i].position for i in indices])
        return float(found[1] if isinstance(found, tuple) else found)

    out = {'bonds': [(i, j, value(i, j)) for i, j in bonds], 'angles': [], 'dihedrals': []}
    for j in range(len(atoms)):
        mates = sorted(k for k in near[j] if real[k] and real[j])
        for x in range(len(mates)):
            for y in range(x + 1, len(mates)):
                out['angles'].append((mates[x], j, mates[y], value(mates[x], j, mates[y])))
    for j, k in bonds:
        for i in sorted(near[j]):
            for m in sorted(near[k]):
                if i in (j, k) or m in (j, k) or i == m or not (real[i] and real[m]):
                    continue
                try:
                    out['dihedrals'].append((i, j, k, m, value(i, j, k, m)))
                except (ValueError, ZeroDivisionError, TypeError):
                    continue  # three atoms on a line: no dihedral
    return out

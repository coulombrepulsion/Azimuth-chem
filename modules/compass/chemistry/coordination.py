"""Coordination centres from a template: «Правка → Геометрия → Координационный центр…».

§1 PURPOSE
    A metal and its ligands in an ideal polyhedron — the usual start of a calculation of a complex, which otherwise is
    built atom by atom: [Fe(H2O)6]2+, [PtCl4]2−, [Ni(CO)4], [Co(NH3)5Cl]2+, Fe(CO)5.
§2 RULES
    1. GEOMETRIES — the directions of the donors as unit vectors, the metal at the origin; their order is the order of
       the positions: linear (±z), trigonal planar (120° in xy), tetrahedral (109.47°), square planar (±x, ±y),
       trigonal bipyramidal (2 axial ±z first, then 3 equatorial), square pyramidal (apical +z first, then 4 basal
       ±x, ±y — the ideal 90°, real complexes lift the basal donors to about 100°), octahedral (±x, ±y, ±z),
       pentagonal bipyramidal (2 axial first, then 5 equatorial at 72°).
    2. LIGANDS — every ligand is a rigid group: its donor at the origin, the rest towards +z (away from the metal),
       with its charge: H2O (H–O–H 104.5°, M–O–H 127.75°), NH3, PH3 (M–X–H 109.47°), OH (M–O–H 109.47°), CO and CN
       (linear, bound by C), the halides F, Cl, Br, I and the hydride H. Names are read without regard to case.
    3. M–L = r(M) + r(donor), the covalent radii of Cordero et al. (Dalton Trans. 2008, 2832; for Mn, Fe, Co the
       low-spin values) — an estimate within about 0.1 Å, to be optimized. An element without a radius is refused.
    4. Every ligand is turned about its M–L axis (12 steps of 30°, ligand after ligand) to the angle with the largest
       distance to the atoms placed before it; the distances between atoms of different ligands shorter than
       0.7 of the sum of their van der Waals radii (contacts.VDW: Bondi, Mantina) are returned as clashes — the
       polyhedron is too crowded for these ligands: said, not hidden. (Measured: [Fe(H2O)6] 0.92, [Co(NH3)6] 0.86,
       [FeCl7] 0.79, seven NH3 on Cu 0.56, seven PH3 on Ni 0.54.)
    5. The charge of the complex = the oxidation state of the metal + the charges of the ligands.
    6. Bonds: metal–donor single; inside the ligands as their formulas (C≡O, C≡N triple).
§3 INTERFACE
    GEOMETRIES = {key: (title, directions)}; LIGANDS = {name: (charge, ((symbol, x, y, z), …), bonds)};
    build(metal, geometry, ligands, oxidation=0) -> Built(molecule, charge, clashes); ligands — one name for every
    position or a list of the length of the geometry; ValueError for an unknown metal, geometry or ligand and for a
    wrong number of ligands.
    parse_ligands(text, count) -> list of names — «H2O» or «Cl, Cl, NH3, NH3» or «4 Cl, 2 NH3».
§4 TESTS
    tests/compass/test_coordination.py — the angles between the donors measured back (90, 109.47, 120, 180, 72), the
    M–L distances against the sums of radii, the ligands keep their own bond lengths and angles, the charges of
    [Fe(H2O)6]2+, [PtCl4]2−, [Ni(CO)4], [Fe(CN)6]3−, the clashes of seven NH3 on a small metal reported.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from azimuth.core import Atom, Molecule
from azimuth.i18n import tr

# Cordero 2008, the transition metals missing from contacts.COVALENT and descriptors.EXTRA_RADII
MORE_RADII = {'Nb': 1.64, 'Tc': 1.47, 'Ru': 1.46, 'Rh': 1.42, 'Ta': 1.70, 'W': 1.62, 'Re': 1.51, 'Os': 1.44,
              'Ir': 1.41}
CLASH = 0.7  # × (vdW_i + vdW_j), §2.4
TURNS = 12


def _unit(*v):
    v = np.array(v, dtype=float)
    return tuple(v / np.linalg.norm(v))


def _ring(n, z=0.0):
    return tuple(_unit(math.cos(2 * math.pi * k / n), math.sin(2 * math.pi * k / n), z) for k in range(n))


GEOMETRIES = {
    'linear': ('линейная', ((0, 0, 1.0), (0, 0, -1.0))),
    'trigonal': ('треугольная плоская', _ring(3)),
    'tetrahedral': ('тетраэдр', (_unit(1, 1, 1), _unit(1, -1, -1), _unit(-1, 1, -1), _unit(-1, -1, 1))),
    'square': ('плоский квадрат', _ring(4)),
    'bipyramid': ('тригональная бипирамида', ((0, 0, 1.0), (0, 0, -1.0)) + _ring(3)),
    'pyramid': ('квадратная пирамида', ((0, 0, 1.0),) + _ring(4)),
    'octahedral': ('октаэдр', ((0, 0, 1.0), (0, 0, -1.0)) + _ring(4)),
    'pentagonal': ('пентагональная бипирамида', ((0, 0, 1.0), (0, 0, -1.0)) + _ring(5)),
}


def _tilted(length, angle_from_z, count, start=0.0):
    """count atoms H at length from the donor, angle_from_z from +z, spread evenly about z."""
    a = math.radians(angle_from_z)
    return tuple(('H', length * math.sin(a) * math.cos(start + 2 * math.pi * k / count),
                  length * math.sin(a) * math.sin(start + 2 * math.pi * k / count), length * math.cos(a))
                 for k in range(count))


TETRAHEDRAL = 180.0 - 109.4712  # the angle from +z of an H with M–X–H tetrahedral
LIGANDS = {
    'H2O': (0, (('O', 0, 0, 0),) + _tilted(0.958, 52.25, 2), ((0, 1, 1), (0, 2, 1))),
    'NH3': (0, (('N', 0, 0, 0),) + _tilted(1.012, TETRAHEDRAL, 3), ((0, 1, 1), (0, 2, 1), (0, 3, 1))),
    'PH3': (0, (('P', 0, 0, 0),) + _tilted(1.420, TETRAHEDRAL, 3), ((0, 1, 1), (0, 2, 1), (0, 3, 1))),
    'OH': (-1, (('O', 0, 0, 0),) + _tilted(0.960, TETRAHEDRAL, 1), ((0, 1, 1),)),
    'CO': (0, (('C', 0, 0, 0), ('O', 0, 0, 1.128)), ((0, 1, 3),)),
    'CN': (-1, (('C', 0, 0, 0), ('N', 0, 0, 1.160)), ((0, 1, 3),)),
    'F': (-1, (('F', 0, 0, 0),), ()),
    'Cl': (-1, (('Cl', 0, 0, 0),), ()),
    'Br': (-1, (('Br', 0, 0, 0),), ()),
    'I': (-1, (('I', 0, 0, 0),), ()),
    'H': (-1, (('H', 0, 0, 0),), ()),
}
_NAMES = {name.lower(): name for name in LIGANDS}


@dataclass(frozen=True)
class Built:
    molecule: Molecule
    charge: int
    clashes: tuple  # ((atom i, atom j, distance), …), 0-based


def radius(symbol):
    from modules.spectrum.analysis.contacts import COVALENT
    from modules.spectrum.analysis.descriptors import EXTRA_RADII

    found = COVALENT.get(symbol, EXTRA_RADII.get(symbol, MORE_RADII.get(symbol)))
    if found is None:
        raise ValueError(tr('Для элемента {} нет ковалентного радиуса.').format(symbol))
    return found


def parse_ligands(text, count):
    """§3: one name for all, a list by commas, or «4 Cl, 2 NH3»."""
    names = []
    for part in (p.strip() for p in str(text).replace(';', ',').split(',')):
        if not part:
            continue
        words = part.split()
        times = 1
        if len(words) == 2 and words[0].isdigit():
            times, part = int(words[0]), words[1]
        elif len(words) != 1:
            raise ValueError(tr('Не понял лиганд «{}».').format(part))
        name = _NAMES.get(part.lower())
        if name is None:
            raise ValueError(tr('Неизвестный лиганд «{}». Есть: {}.').format(part, ', '.join(LIGANDS)))
        names += [name] * times
    if len(names) == 1:
        names *= count
    if len(names) != count:
        raise ValueError(tr('Нужно {} лигандов, указано {}.').format(count, len(names)))
    return names


def _rotation(direction):
    """The matrix turning +z to direction (a fixed choice of the turn about it)."""
    d = np.asarray(direction, dtype=float)
    z = np.array([0.0, 0.0, 1.0])
    c = float(d @ z)
    if c > 1 - 1e-12:
        return np.eye(3)
    if c < -1 + 1e-12:
        return np.diag([1.0, -1.0, -1.0])
    v = np.cross(z, d)
    s = np.linalg.norm(v)
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k * ((1 - c) / s ** 2)


def _spin(angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


def build(metal, geometry, ligands, oxidation=0):
    metal = str(metal).strip()
    metal = metal[:1].upper() + metal[1:].lower()
    if geometry not in GEOMETRIES:
        raise ValueError(tr('Неизвестная геометрия «{}».').format(geometry))
    title, directions = GEOMETRIES[geometry]
    names = parse_ligands(ligands, len(directions)) if isinstance(ligands, str) else list(ligands)
    if len(names) != len(directions):
        raise ValueError(tr('Нужно {} лигандов, указано {}.').format(len(directions), len(names)))
    names = [_NAMES.get(str(n).lower()) or n for n in names]
    for name in names:
        if name not in LIGANDS:
            raise ValueError(tr('Неизвестный лиганд «{}». Есть: {}.').format(name, ', '.join(LIGANDS)))
    r_metal = radius(metal)
    symbols, points, bonds, owner = [metal], [np.zeros(3)], [], [-1]
    for k, (name, direction) in enumerate(zip(names, directions)):
        charge, group, inner = LIGANDS[name]
        local = np.array([p[1:] for p in group], dtype=float)
        d = np.asarray(direction, dtype=float)
        shift = d * (r_metal + radius(group[0][0]))
        turn = _rotation(d)
        placed = np.array(points)
        best, best_gap = None, -1.0
        for step in range(TURNS if len(group) > 2 or (len(group) == 2 and local[1, :2].any()) else 1):
            xyz = (turn @ _spin(2 * math.pi * step / TURNS) @ local.T).T + shift
            gap = float(np.min(np.linalg.norm(xyz[1:, None, :] - placed[None, 1:, :], axis=2))) \
                if len(group) > 1 and len(placed) > 1 else 0.0
            if gap > best_gap + 1e-9:
                best, best_gap = xyz, gap
        start = len(symbols)
        bonds.append((0, start, 1))
        bonds += [(start + i, start + j, order) for i, j, order in inner]
        symbols += [p[0] for p in group]
        points += list(best)
        owner += [k] * len(group)
    xyz = np.array(points)
    from modules.spectrum.analysis.contacts import VDW

    radii = np.array([VDW.get(s, 2.0) for s in symbols])
    clashes = []
    for i in range(1, len(symbols)):
        for j in range(i + 1, len(symbols)):
            if owner[i] != owner[j]:
                distance = float(np.linalg.norm(xyz[i] - xyz[j]))
                if distance < CLASH * (radii[i] + radii[j]):
                    clashes.append((i, j, round(distance, 3)))
    counts = {}
    for name in names:
        counts[name] = counts.get(name, 0) + 1
    label = '[' + metal + ''.join((f'({n})' if len(n) > 1 and len(LIGANDS[n][1]) > 1 else n) + (str(c) if c > 1 else '')
                                  for n, c in counts.items()) + ']'
    charge = int(oxidation) + sum(LIGANDS[n][0] for n in names)
    atoms = tuple(Atom(s, float(p[0]), float(p[1]), float(p[2])) for s, p in zip(symbols, xyz))
    return Built(Molecule(label, atoms, tuple(bonds)), charge, tuple(clashes))

"""A model of balls and sticks for 3D printing: STL and VRML (as Mercury's «Print 3D» / «Save as VRML»).

§1 PURPOSE
    The roadmap, «Кристаллы: очередь дальше», 6: a molecule, a block of cells or a molecular shell printed as a
    plastic model for teaching — the balls and sticks of the Compass model at a printable size, the edges of the cell
    as thin rods.
§2 ALGORITHM
    Every atom — an icosphere (an icosahedron whose faces are split SUBDIVISIONS times, the new points pushed onto the
    sphere), every bond — a closed cylinder of SIDES faces from centre to centre, every edge of the cell — a closed
    cylinder too. The parts overlap and are not merged into one surface: slicers of 3D printers join overlapping closed
    bodies (as the models of Mercury). Sizes in millimetres: scale mm per Å; the radii of the balls in Å
    (balls: H smaller), the rods never thinner than min_rod mm across — a thinner one breaks when printed.
    STL: binary (an 80-byte header, the count, 50 bytes a triangle: its normal, three corners, 2 bytes 0) — one colour.
    VRML 2.0: one Shape a part with its diffuse colour (the colour of the element on the model) — for colour printers.
    Every triangle is wound so that its normal points out of its body.
§3 APPLICATIONS
    modules/compass/actions/print3d_window.py: «Файл → Модель для 3D-печати…» of Compass (molecule and crystal).
§4 SPECIFICATION
    Part(name, color '#rrggbb', triangles (n, 3, 3) mm).
    icosphere(centre, radius, subdivisions=SUBDIVISIONS) -> (n, 3, 3); cylinder(a, b, radius, sides=SIDES) ->
    (n, 3, 3) (closed: the side and two caps).
    parts(molecule, scale=SCALE, atom=ATOM, hydrogen=HYDROGEN, rod=ROD, min_rod=MIN_ROD, bonds=None, edges=(),
    colors=None, hidden=()) -> [Part]: the balls (one Part an element), the bonds (one Part, grey, or both halves in
    the colours of their atoms when colors is given), the edges (one Part).
    write_stl(parts, path) -> path; write_vrml(parts, path) -> path; volume(triangles) -> mm³ (the signed volume,
    positive for a closed body wound outward); size(parts) -> (dx, dy, dz) mm.
§7 TESTS
    tests/compass/test_print3d.py.
§8' ROBUSTNESS / ERRORS
    ValueError — no atoms.
"""

from dataclasses import dataclass
from math import pi
import struct

import numpy as np

SCALE = 10.0  # mm per Å: water about 2.5 cm across
ATOM, HYDROGEN = 0.35, 0.25  # Å: the radii of the balls (a little larger than on the screen — stronger)
ROD = 0.12  # Å: the radius of a bond
MIN_ROD = 1.6  # mm: the thinnest rod across
SUBDIVISIONS, SIDES = 2, 20
BOND_COLOR, EDGE_COLOR = '#9aa3ad', '#555b63'


@dataclass
class Part:
    name: str
    color: str
    triangles: np.ndarray


def _icosahedron():
    t = (1 + 5 ** 0.5) / 2
    points = np.array([(-1, t, 0), (1, t, 0), (-1, -t, 0), (1, -t, 0), (0, -1, t), (0, 1, t), (0, -1, -t), (0, 1, -t),
                       (t, 0, -1), (t, 0, 1), (-t, 0, -1), (-t, 0, 1)], float)
    faces = [(0, 11, 5), (0, 5, 1), (0, 1, 7), (0, 7, 10), (0, 10, 11), (1, 5, 9), (5, 11, 4), (11, 10, 2), (10, 7, 6),
             (7, 1, 8), (3, 9, 4), (3, 4, 2), (3, 2, 6), (3, 6, 8), (3, 8, 9), (4, 9, 5), (2, 4, 11), (6, 2, 10),
             (8, 6, 7), (9, 8, 1)]
    return points / np.linalg.norm(points, axis=1)[:, None], faces


_UNIT = {}


def _unit_sphere(subdivisions):
    if subdivisions not in _UNIT:
        points, faces = _icosahedron()
        tris = points[np.array(faces)]
        for _ in range(subdivisions):
            a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
            ab, bc, ca = (a + b) / 2, (b + c) / 2, (c + a) / 2
            tris = np.concatenate([np.stack(x, 1) for x in ((a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca))])
            tris /= np.linalg.norm(tris, axis=2)[:, :, None]
        _UNIT[subdivisions] = _outward(tris, np.zeros(3))
    return _UNIT[subdivisions]


def _outward(tris, centre):
    """The triangles wound so that their normals point away from centre (a convex body)."""
    normal = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    flip = np.einsum('ij,ij->i', normal, tris.mean(1) - centre) < 0
    tris = tris.copy()
    tris[flip] = tris[flip][:, ::-1]
    return tris


def icosphere(centre, radius, subdivisions=SUBDIVISIONS):
    return np.asarray(centre, float) + radius * _unit_sphere(subdivisions)


def cylinder(a, b, radius, sides=SIDES):
    a, b = np.asarray(a, float), np.asarray(b, float)
    axis = b - a
    length = np.linalg.norm(axis)
    if length < 1e-9:
        return np.zeros((0, 3, 3))
    axis /= length
    helper = np.array([1.0, 0, 0]) if abs(axis[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(axis, helper)
    u /= np.linalg.norm(u)
    v = np.cross(axis, u)
    angles = np.linspace(0, 2 * pi, sides, endpoint=False)
    ring = radius * (np.cos(angles)[:, None] * u + np.sin(angles)[:, None] * v)
    low, high = a + ring, b + ring
    nxt = np.roll(np.arange(sides), -1)
    side = np.concatenate([np.stack([low, high, high[nxt]], 1), np.stack([low, high[nxt], low[nxt]], 1)])
    # the side outward from the axis, the caps outward along it
    normal = np.cross(side[:, 1] - side[:, 0], side[:, 2] - side[:, 0])
    centroid = side.mean(1)
    radial = centroid - (a + np.outer((centroid - a) @ axis, axis))
    flip = np.einsum('ij,ij->i', normal, radial) < 0
    side[flip] = side[flip][:, ::-1]
    caps = []
    for end, rim, sign in ((a, low, -1), (b, high, 1)):
        cap = np.stack([np.repeat(end[None], sides, 0), rim, rim[nxt]], 1)
        normal = np.cross(cap[:, 1] - cap[:, 0], cap[:, 2] - cap[:, 0])
        flip = (normal @ axis) * sign < 0
        cap[flip] = cap[flip][:, ::-1]
        caps.append(cap)
    return np.concatenate([side] + caps)


def parts(molecule, scale=SCALE, atom=ATOM, hydrogen=HYDROGEN, rod=ROD, min_rod=MIN_ROD, bonds=None, edges=(),
          colors=None, hidden=()):
    if molecule is None or not molecule.atoms:
        from azimuth.i18n import tr

        raise ValueError(tr('Нет атомов — печатать нечего.'))
    if bonds is None:
        from modules.compass.chemistry.builder import connections

        bonds = connections(molecule)
    hidden = set(hidden)
    xyz = np.array([(a.x, a.y, a.z) for a in molecule.atoms], float) * scale
    rod_mm = max(rod * scale, min_rod / 2)
    balls = {}
    for k, a in enumerate(molecule.atoms):
        if k in hidden:
            continue
        radius = (hydrogen if a.symbol in ('H', 'D') else atom) * scale
        balls.setdefault(a.symbol, []).append(icosphere(xyz[k], max(radius, rod_mm * 1.3)))
    out = [Part(symbol, (colors or {}).get(symbol, BOND_COLOR), np.concatenate(tris)) for symbol, tris in balls.items()]
    sticks = {}
    for bond in bonds:
        i, j = bond[0], bond[1]
        if i in hidden or j in hidden:
            continue
        if colors:  # two halves, each in the colour of its atom
            middle = (xyz[i] + xyz[j]) / 2
            for k, end in ((i, middle), (j, middle)):
                sticks.setdefault(colors.get(molecule.atoms[k].symbol, BOND_COLOR), []).append(cylinder(xyz[k], end, rod_mm))
        else:
            sticks.setdefault(BOND_COLOR, []).append(cylinder(xyz[i], xyz[j], rod_mm))
    for color, tris in sticks.items():
        out.append(Part('bonds', color, np.concatenate(tris)))
    rods = [cylinder(np.asarray(a, float) * scale, np.asarray(b, float) * scale, min_rod / 2) for a, b in edges or ()]
    rods = [r for r in rods if len(r)]
    if rods:
        out.append(Part('cell', EDGE_COLOR, np.concatenate(rods)))
    return out


def volume(triangles):
    t = np.asarray(triangles, float)
    return float(np.einsum('ij,ij->i', t[:, 0], np.cross(t[:, 1], t[:, 2])).sum() / 6)


def size(model):
    points = np.concatenate([p.triangles.reshape(-1, 3) for p in model])
    return tuple(float(x) for x in points.max(0) - points.min(0))


def write_stl(model, path):
    tris = np.concatenate([p.triangles for p in model]).astype(np.float32)
    normals = np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0])
    normals /= np.maximum(np.linalg.norm(normals, axis=1), 1e-12)[:, None]
    record = np.zeros(len(tris), dtype=[('n', '<f4', 3), ('v', '<f4', (3, 3)), ('a', '<u2')])
    record['n'], record['v'] = normals, tris
    with open(path, 'wb') as out:
        out.write(b'Azimuth: a model for 3D printing, millimetres'.ljust(80, b' '))
        out.write(struct.pack('<I', len(tris)))
        out.write(record.tobytes())
    return path


def _rgb(color):
    color = color.lstrip('#')
    return tuple(int(color[k:k + 2], 16) / 255 for k in (0, 2, 4))


def write_vrml(model, path):
    lines = ['#VRML V2.0 utf8', '# Azimuth: a model for 3D printing, millimetres', '']
    for part in model:
        points, index = np.unique(part.triangles.reshape(-1, 3).round(5), axis=0, return_inverse=True)
        index = index.reshape(-1, 3)
        r, g, b = _rgb(part.color)
        lines.append(f'Shape {{ # {part.name}')
        lines.append(f'  appearance Appearance {{ material Material {{ diffuseColor {r:.3f} {g:.3f} {b:.3f} }} }}')
        lines.append('  geometry IndexedFaceSet { solid TRUE')
        lines.append('    coord Coordinate { point [')
        lines.extend(f'      {x:.4f} {y:.4f} {z:.4f},' for x, y, z in points)
        lines.append('    ] }')
        lines.append('    coordIndex [')
        lines.extend(f'      {a}, {b_}, {c}, -1,' for a, b_, c in index)
        lines.append('    ]')
        lines.append('  }')
        lines.append('}')
    with open(path, 'w', encoding='utf-8', newline='\n') as out:
        out.write('\n'.join(lines) + '\n')
    return path

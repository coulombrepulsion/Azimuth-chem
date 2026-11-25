"""Rotation about a bond: the dihedral angle, a turn of one side, a conformer scan.

§1 THEORY
    A single bond b-c that is not in a ring splits the molecule into two sides; turning one side
    rigidly about the axis b->c changes only the dihedral angles about that bond (every length, bond
    angle and the other dihedrals stay). The dihedral a-b-c-d (a bonded to b, d to c) measures the
    turn; any choice of a and d differs from another one by a constant, so one pair is enough to set
    and to report the turn. A scan turns the side in equal steps through a full turn and records each
    conformer (Chemcraft's «rotate around a bond» / a rigid torsion scan, no relaxation).
§2 ALGORITHM
    side(m, b, c, moving): transforms.bond_side (the atoms reached from the moving end without the
    bond; refused for a ring bond). reference(m, b, c): a = the neighbour of b other than c, d = the
    neighbour of c other than b, preferring heavy atoms, then the lower number (None if an end has no
    other neighbour: the dihedral is then undefined, a turn is still possible). turn(m, b, c, moving,
    degrees): rotate_atoms of the moving side about the bond axis through the fixed end, the positive
    sense right-handed about fixed->moving. set_dihedral(m, a, b, c, d, moving, target): the turn
    by the difference folded to [-180, 180) (a right-handed turn of either side raises the IUPAC
    dihedral by the same angle; the result is checked). scan(m, b, c, moving,
    step): frames k = 0 .. n-1 with n = round(360 / step) (step must divide 360 to 1e-9), frame k
    turned by k*step from the given geometry, each with its dihedral (if defined) and its closest
    contact: the smallest distance between an atom of the moving side and one of the fixed side that
    are not bonded and do not share a bonded neighbour (1-2 and 1-3 pairs are left out).
§3 APPLICATIONS
    modules/compass/actions/torsion_actions.py (the «Вращение вокруг связи» window, the drag, the scan).
§4 SPECIFICATION
    side -> sorted indices; reference -> (a or None, d or None); turn -> Molecule;
    set_dihedral -> Molecule; dihedral(m, a, b, c, d) -> degrees in (-180, 180];
    contact(m, moving_side) -> (distance, i, j) or None; scan -> [(angle_turned, dihedral or None,
    contact or None, Molecule)]. ValueError: atoms not bonded, a ring bond, a bad step, an undefined
    dihedral for set_dihedral.
§5 PROCEDURES - below.
§6 NOTES
    The rotation acts on the given coordinates (not cumulative): the window always turns its starting
    geometry, so many small drags do not accumulate rounding. Bonds are kept explicitly (a turn could
    otherwise change bonds found by distance).
§7 TESTS
    tests/compass/test_torsion.py.
§8' ROBUSTNESS / ERRORS
    A rotation keeps distances to ~1e-14 A relative; the dihedral is reached to 1e-9 deg (checked
    after the turn, ValueError if not). MAX_FRAMES = 360 frames at most.
"""

from math import atan2, degrees, dist, isfinite, radians, sqrt

from modules.compass.chemistry.transforms import bond_side, rotate_atoms
from modules.compass.chemistry.builder import connections
from azimuth.i18n import tr

MAX_FRAMES = 360


def _neighbours(molecule):
    out = [set() for _ in molecule.atoms]
    for i, j, _ in connections(molecule):
        out[i].add(j)
        out[j].add(i)
    return out


def _bonded(molecule, b, c):
    if not (0 <= b < len(molecule.atoms) and 0 <= c < len(molecule.atoms)) or b == c:
        raise ValueError(tr('Выберите два связанных атома.'))
    if c not in _neighbours(molecule)[b]:
        raise ValueError(tr('Выберите два связанных атома.'))


def side(molecule, b, c, moving):
    """Atoms that turn: the side of moving (b or c) of the bond b-c."""
    _bonded(molecule, b, c)
    if moving not in (b, c):
        raise ValueError(tr('Вращаемая сторона — один из концов связи.'))
    fixed = c if moving == b else b
    return bond_side(molecule, fixed, moving)


def reference(molecule, b, c):
    """(a, d): default dihedral atoms a-b-c-d (heavy neighbours first, then the lower number)."""
    _bonded(molecule, b, c)
    nb = _neighbours(molecule)

    def pick(end, other):
        choices = sorted(nb[end] - {other}, key=lambda i: (molecule.atoms[i].symbol == 'H', i))
        return choices[0] if choices else None

    return pick(b, c), pick(c, b)


def dihedral(molecule, a, b, c, d):
    """The dihedral angle a-b-c-d in degrees (-180, 180] (IUPAC sign convention)."""
    p = [molecule.atoms[i].position for i in (a, b, c, d)]
    b1 = [p[1][k] - p[0][k] for k in range(3)]
    b2 = [p[2][k] - p[1][k] for k in range(3)]
    b3 = [p[3][k] - p[2][k] for k in range(3)]

    def cross(u, v):
        return [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]

    # atan2(|b2| b1.(b2 x b3), (b1 x b2).(b2 x b3)): positive clockwise looking along b -> c (IUPAC)
    n1, n2 = cross(b1, b2), cross(b2, b3)
    norm2 = sqrt(sum(x * x for x in b2))
    x = sum(n1[k] * n2[k] for k in range(3))
    y = norm2 * sum(b1[k] * n2[k] for k in range(3))
    if abs(x) < 1e-12 and abs(y) < 1e-12:
        raise ValueError(tr('Двугранный угол не определён: три атома на одной прямой.'))
    angle = degrees(atan2(y, x))
    return 180.0 if angle <= -180.0 else angle


def turn(molecule, b, c, moving, angle):
    """The side of moving turned by angle degrees about the bond (right-handed about fixed -> moving)."""
    if not isfinite(angle):
        raise ValueError(tr('Введите конечное числовое значение.'))
    group = side(molecule, b, c, moving)
    fixed = c if moving == b else b
    pivot = molecule.atoms[fixed].position
    axis = tuple(molecule.atoms[moving].position[k] - pivot[k] for k in range(3))
    return rotate_atoms(molecule, group, pivot, axis, radians(angle))


def set_dihedral(molecule, a, b, c, d, moving, target):
    """Turn the side of moving so that the dihedral a-b-c-d becomes target degrees."""
    if not isfinite(target):
        raise ValueError(tr('Введите конечное числовое значение.'))
    current = dihedral(molecule, a, b, c, d)
    delta = (target - current + 180.0) % 360.0 - 180.0
    # a right-handed turn of either side about fixed -> moving raises the dihedral a-b-c-d by the same
    # angle (a relative turn of the two sides); the result is checked, not assumed
    result = turn(molecule, b, c, moving, delta)
    reached = dihedral(result, a, b, c, d)
    if abs((reached - target + 180.0) % 360.0 - 180.0) > 1e-9:
        raise ValueError(tr('Не удалось задать двугранный угол.'))
    return result


def contact(molecule, moving_side):
    """(distance, i, j): the closest atoms of the two sides beyond 1-2 and 1-3 pairs, or None."""
    inside = set(moving_side)
    nb = _neighbours(molecule)
    best = None
    for i in inside:
        near = nb[i] | {k for j in nb[i] for k in nb[j]}
        for j in range(len(molecule.atoms)):
            if j in inside or j in near:
                continue
            r = dist(molecule.atoms[i].position, molecule.atoms[j].position)
            if best is None or r < best[0]:
                best = (r, i, j)
    return best


def scan(molecule, b, c, moving, step, a=None, d=None):
    """Conformers turned by 0, step, 2 step, ... below 360 degrees (see §2)."""
    if not isfinite(step) or step <= 0:
        raise ValueError(tr('Шаг перебора должен быть положительным.'))
    n = round(360.0 / step)
    if n < 2 or abs(n * step - 360.0) > 1e-9:
        raise ValueError(tr('Шаг перебора должен делить 360° нацело (например, 10, 15, 30, 60, 120).'))
    if n > MAX_FRAMES:
        raise ValueError(tr(f'Не больше {MAX_FRAMES} кадров.'))
    group = side(molecule, b, c, moving)
    if a is None or d is None:
        a, d = reference(molecule, b, c)
    frames = []
    for k in range(n):
        m = turn(molecule, b, c, moving, k * step) if k else molecule
        try:
            value = dihedral(m, a, b, c, d) if a is not None and d is not None else None
        except ValueError:
            value = None
        frames.append((k * step, value, contact(m, group), m))
    return frames


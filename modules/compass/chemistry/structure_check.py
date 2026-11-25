"""«Проверить структуру», явная сольватация и протоны.

§1 PURPOSE
    1) A check of the structure before a calculation:
    what ORCA would refuse or what is likely a slip of drawing; 2) explicit solvation: molecules of a solvent put round
    the structure without overlaps (microsolvation, a first shell); 3) protons: one put on an atom (+1), one taken off
    (−1), one carried to another atom (a tautomer, the charge unchanged).
§2 ALGORITHM
    check(molecule, charge, multiplicity) -> [Problem]: the number of electrons against the multiplicity (an even count
    takes 1, 3, …; an odd one 2, 4, …); atoms nearer than 0.6 × the sum of their covalent radii (or 0.5 Å); an atom
    with more neighbours than it usually has; a C, N or O whose valence is not filled (by editing.perceived_orders — a
    missing hydrogen or an unpaired electron) when the molecule is neutral and a singlet, otherwise said as a note;
    a neutral N with four bonds (N⁺?) and an O with three; parts of the structure not bonded to each other (a complex
    or a dimer — said as a note).
    solvate(molecule, solvent, count, seed): the first shell first (shell) — a molecule of the solvent on every free
    lone pair of the structure (two on an O, _lone_pairs) by its donor H and on every polar H by its acceptor, H···A
    1.9 Å, the line bent up to 36° and the molecule turned about it until nothing is in the way; then (around) copies
    of the solvent, each turned at random, centred at a random point 2.4–4.2 Å beyond a random atom of the structure
    itself (heteroatoms twice as likely); a molecule is kept when no atom of it is nearer than 2.0 Å to an atom already
    there (2.4 Å heavy to heavy, 1.8 Å H to H); -> (molecule, placed). Repeatable for one seed.
    protonate(molecule, index) — an H on the free side of the atom (builder.outgoing) at the length of the X–H bond;
    deprotonate(molecule, index) — the H itself or the last terminal H of the atom taken away; move_proton(molecule,
    hydrogen, target) — the H taken from its atom and put on target.
§4 CONTRACT
    Problem(level 'error' | 'warning' | 'note', text, atoms (0-based)); the functions return new Molecules (bonds:
    explicit when the structure had them, else by distance) and raise ValueError with a sentence for the user.
§7 TESTS tests/compass/test_structure_check.py.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from math import cos, dist, pi, sin, sqrt

from azimuth.core import Atom, Molecule, near_pairs
from azimuth.i18n import tr
from modules.compass.chemistry.builder import RADII, bond_length, connections, delete_atoms, outgoing

LEVELS = ('error', 'warning', 'note')
NEIGHBOURS = {'H': 1, 'F': 1, 'Cl': 1, 'Br': 1, 'I': 1, 'O': 2, 'S': 6, 'Se': 6, 'N': 4, 'P': 5, 'As': 5, 'B': 4,
              'C': 4, 'Si': 4, 'Ge': 4}
SOLVENTS = (  # the key of the library, the name shown
    ('Вода · H₂O', 'Вода'),
    ('Метанол · CH₄O', 'Метанол'),
    ('Этанол · C₂H₆O', 'Этанол'),
    ('Аммиак · NH₃', 'Аммиак'),
    ('Диметилсульфоксид · C₂H₆OS', 'ДМСО'),
    ('Дихлорметан · CH₂Cl₂', 'Дихлорметан'),
    ('Трихлорметан (хлороформ) · CHCl₃', 'Хлороформ'),
    ('Оксолан (тетрагидрофуран) · C₄H₈O', 'ТГФ'),
    ('Бензол · C₆H₆', 'Бензол'),
)


@dataclass(frozen=True)
class Problem:
    level: str
    text: str
    atoms: tuple = ()


def _name(molecule, index):
    return f'{molecule.atoms[index].symbol}{index + 1}'


def check(molecule, charge=0, multiplicity=1):
    """The problems of the structure, errors first."""
    atoms = molecule.atoms
    found = []
    if not atoms:
        return found
    try:
        electrons = molecule.electrons(int(charge))
    except KeyError as exc:
        return [Problem('error', tr('Неизвестный элемент: {}').format(exc.args[0] if exc.args else ''))]
    if electrons <= 0:
        found.append(Problem('error', tr('Заряд {} не оставляет молекуле электронов.').format(charge)))
    elif (electrons + int(multiplicity) - 1) % 2:
        found.append(Problem('error', tr('Электронов {} при заряде {} — мультиплетность должна быть {}, а не {}.').format(
            electrons, charge, tr('нечётной (1, 3, …)') if electrons % 2 == 0 else tr('чётной (2, 4, …)'), multiplicity)))
    positions = [a.position for a in atoms]
    biggest = 2 * max(RADII.get(a.symbol, 0.8) for a in atoms)
    for j, i in near_pairs(positions, 0.6 * biggest):
        if 'X' in (atoms[i].symbol, atoms[j].symbol):
            continue
        d = dist(positions[i], positions[j])
        if d < max(0.5, 0.6 * (RADII.get(atoms[i].symbol, 0.8) + RADII.get(atoms[j].symbol, 0.8))):
            found.append(Problem('error', tr('Атомы {} и {} слишком близко: {:.2f} Å.').format(
                _name(molecule, j), _name(molecule, i), d), (j, i)))
    bonds = connections(molecule)
    neighbours = [[] for _ in atoms]
    for i, j, _ in bonds:
        neighbours[i].append(j)
        neighbours[j].append(i)
    plain = int(charge) == 0 and int(multiplicity) == 1
    for k, atom in enumerate(atoms):
        count = len(neighbours[k])
        limit = NEIGHBOURS.get(atom.symbol)
        if limit is not None and count > limit:
            found.append(Problem('warning', tr('У атома {} соседей: {} — больше, чем обычно ({}).').format(
                _name(molecule, k), count, limit), (k,)))
        elif atom.symbol == 'N' and count == 4 and int(charge) == 0:
            found.append(Problem('warning', tr('У атома {} четыре связи, а заряд молекулы 0 — это N⁺?').format(
                _name(molecule, k)), (k,)))
        elif atom.symbol == 'O' and count == 3 and int(charge) == 0:
            found.append(Problem('warning', tr('У атома {} три связи, а заряд молекулы 0 — это O⁺?').format(
                _name(molecule, k)), (k,)))
    if any(a.symbol == 'H' for a in atoms):  # without hydrogens the free valences are the missing H of a skeleton
        from modules.compass.chemistry.editing import VALENCE, perceived_orders

        used = [0.0] * len(atoms)
        for i, j, order in perceived_orders(molecule):
            used[i] += order
            used[j] += order
        for k, atom in enumerate(atoms):
            if atom.symbol in ('C', 'N', 'O') and neighbours[k] and used[k] + 0.25 < VALENCE[atom.symbol]:
                found.append(Problem('warning' if plain else 'note', tr(
                    'У атома {} не заполнена валентность — не хватает водорода, или это радикал или ион?').format(
                    _name(molecule, k)), (k,)))
    parts = _parts(len(atoms), neighbours)
    if len(parts) > 1:
        small = sorted(parts, key=len)[:-1]
        found.append(Problem('note', tr('Структура из {} несвязанных частей — так и задумано (комплекс, димер, '
                                        'растворитель)?').format(len(parts)), tuple(k for p in small for k in p)))
    return sorted(found, key=lambda p: LEVELS.index(p.level))


def _parts(count, neighbours):
    seen, parts = set(), []
    for start in range(count):
        if start in seen:
            continue
        part, todo = [], [start]
        seen.add(start)
        while todo:
            k = todo.pop()
            part.append(k)
            for n in neighbours[k]:
                if n not in seen:
                    seen.add(n)
                    todo.append(n)
        parts.append(sorted(part))
    return parts


# -- explicit solvation -------------------------------------------------------------------------------------------------
def _rotation(rng):
    """A uniformly random rotation (a random unit quaternion)."""
    u1, u2, u3 = rng.random(), rng.random(), rng.random()
    a, b = sqrt(1 - u1), sqrt(u1)
    w, x, y, z = a * sin(2 * pi * u2), a * cos(2 * pi * u2), b * sin(2 * pi * u3), b * cos(2 * pi * u3)
    return ((1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)),
            (2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)),
            (2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)))


def _turned(matrix, v):
    return tuple(sum(matrix[r][c] * v[c] for c in range(3)) for r in range(3))


def _unit(rng):
    z = 2 * rng.random() - 1
    angle = 2 * pi * rng.random()
    r = sqrt(max(0.0, 1 - z * z))
    return r * cos(angle), r * sin(angle), z


def _clear(new, placed, contact=None):
    """No atom of new nearer than 2.0 Å to one placed (2.4 Å heavy to heavy) — but the pair contact (its index in new,
    its index in placed: the hydrogen bond being made) at its own distance."""
    for k, a in enumerate(new):
        for m, b in enumerate(placed):
            if contact is not None and (k, m) == contact:
                continue
            # heavy–heavy 2.4 Å; with a hydrogen 2.0 Å, H···H 1.8 Å (two hydrogens of neighbours in a real shell)
            limit = 2.4 if a.symbol != 'H' and b.symbol != 'H' else 1.8 if a.symbol == b.symbol == 'H' else 2.0
            if dist(a.position, b.position) < limit:
                return False
    return True


HBOND = 1.9  # Å, H···acceptor of the first shell


def _norm(v):
    length = sqrt(sum(c * c for c in v)) or 1.0
    return tuple(c / length for c in v)


def _aligning(a, b):
    """The rotation matrix turning the unit vector a onto the unit vector b (Rodrigues)."""
    a, b = _norm(a), _norm(b)
    v = (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])
    c = sum(x * y for x, y in zip(a, b))
    if c < -0.999999:  # opposite: half a turn about any perpendicular
        axis = _norm((1.0, 0.0, 0.0) if abs(a[0]) < 0.9 else (0.0, 1.0, 0.0))
        axis = _norm((a[1] * axis[2] - a[2] * axis[1], a[2] * axis[0] - a[0] * axis[2], a[0] * axis[1] - a[1] * axis[0]))
        return _about(axis, pi)
    k = 1 / (1 + c)
    return ((v[0] * v[0] * k + c, v[0] * v[1] * k - v[2], v[0] * v[2] * k + v[1]),
            (v[1] * v[0] * k + v[2], v[1] * v[1] * k + c, v[1] * v[2] * k - v[0]),
            (v[2] * v[0] * k - v[1], v[2] * v[1] * k + v[0], v[2] * v[2] * k + c))


def _about(axis, angle):
    x, y, z = _norm(axis)
    c, s_, t = cos(angle), sin(angle), 1 - cos(angle)
    return ((t * x * x + c, t * x * y - s_ * z, t * x * z + s_ * y),
            (t * x * y + s_ * z, t * y * y + c, t * y * z - s_ * x),
            (t * x * z - s_ * y, t * y * z + s_ * x, t * z * z + c))


def _times(m, n):
    return tuple(tuple(sum(m[r][k] * n[k][c] for k in range(3)) for c in range(3)) for r in range(3))


def _pyramidal(molecule, k, neighbours):
    """The sum of the three angles at atom k below 345° (an sp³ centre; flat — 360°)."""
    from math import acos, degrees

    centre = molecule.atoms[k].position
    vectors = [_norm(tuple(molecule.atoms[n].position[c] - centre[c] for c in range(3))) for n in neighbours]
    total = 0.0
    for a in range(3):
        for b in range(a + 1, 3):
            total += degrees(acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(vectors[a], vectors[b]))))))
    return total < 345


def _lone_pairs(molecule, k, near):
    """The directions of the lone pairs of an acceptor that take a hydrogen bond — an O with one neighbour (C=O, O⁻ of a
    carboxylate): two, in the plane of the group, 120° from the bond; an O with two (an alcohol, an ether, water): two,
    tetrahedral; an N with one (a nitrile): one along the bond; with two (pyridine, an imine): one on the bisector; with
    three, pyramidal (an amine): one opposite the bonds; an F: one. [unit vectors]."""
    from math import radians

    centre = molecule.atoms[k].position
    bonds = [_norm(tuple(molecule.atoms[n].position[c] - centre[c] for c in range(3))) for n in near[k]]
    symbol = molecule.atoms[k].symbol
    if not bonds:
        return []
    if symbol == 'O' and len(bonds) == 1:
        u = tuple(-c for c in bonds[0])
        neighbour = near[k][0]
        others = [n for n in near[neighbour] if n != k]
        side = None
        if others:
            r = tuple(molecule.atoms[others[0]].position[c] - molecule.atoms[neighbour].position[c] for c in range(3))
            along = sum(r[c] * u[c] for c in range(3))
            side = tuple(r[c] - along * u[c] for c in range(3))
            if sum(c * c for c in side) < 1e-6:
                side = None
        if side is None:
            side = (1.0, 0.0, 0.0) if abs(u[0]) < 0.9 else (0.0, 1.0, 0.0)
            along = sum(side[c] * u[c] for c in range(3))
            side = tuple(side[c] - along * u[c] for c in range(3))
        p = _norm(side)
        return [_norm(tuple(0.5 * u[c] + sign * 0.8660254 * p[c] for c in range(3))) for sign in (1, -1)]
    if symbol == 'O' and len(bonds) == 2:
        a, b = bonds
        bisector = _norm(tuple(-(a[c] + b[c]) for c in range(3)))
        normal = _norm((a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]))
        half = radians(54.75)
        return [_norm(tuple(bisector[c] * cos(half) + sign * normal[c] * sin(half) for c in range(3)))
                for sign in (1, -1)]
    if symbol in ('N', 'F') and len(bonds) <= 3:
        return [_norm(tuple(-sum(v[c] for v in bonds) for c in range(3)))]
    return []


def _sites(molecule):
    """(acceptors: the lone pairs that take a hydrogen bond — [(atom, direction)], two on an O (_lone_pairs), one on an
    N with ≤ 2 neighbours or a pyramidal one with 3, on an F; donors: hydrogens that give one — on O, N, or on a carbon
    with two or more Cl (chloroform, dichloromethane) — [(hydrogen, its atom)])."""
    bonds = connections(molecule)
    near = [[] for _ in molecule.atoms]
    for i, j, _ in bonds:
        near[i].append(j)
        near[j].append(i)
    acceptors, donors = [], []
    for k, atom in enumerate(molecule.atoms):
        # an N with three neighbours is an acceptor only
        # when pyramidal (an amine); flat (an amide, a ring N–R, an aniline) its lone pair is in the π system
        if atom.symbol in ('O', 'F') or (atom.symbol == 'N' and (len(near[k]) <= 2 or (
                len(near[k]) == 3 and _pyramidal(molecule, k, near[k])))):
            acceptors += [(k, direction) for direction in _lone_pairs(molecule, k, near)]
        if atom.symbol == 'H' and len(near[k]) == 1:
            owner = near[k][0]
            symbol = molecule.atoms[owner].symbol
            chlorines = sum(1 for n in near[owner] if molecule.atoms[n].symbol == 'Cl')
            if symbol in ('O', 'N') or (symbol == 'C' and chlorines >= 2):
                donors.append((k, owner))
    return acceptors, donors


def _solvent_formulas():
    from modules.compass.chemistry import library

    found = set()
    for key, _ in SOLVENTS:
        try:
            found.add(library.molecule(key).formula)
        except KeyError:
            continue
    return found


def _solute(parts):
    """The part that is the structure itself: the one of the first atom — the solvent is always put after the
    structure (methanol in water or in methanol, ammonia in benzene stays the structure)."""
    return next(n for n, part in enumerate(parts) if 0 in part)


def solute_atoms(molecule):
    """The atoms of the structure itself — not of the molecules of a solvent round it (the rule of solute_sites)."""
    near = [[] for _ in molecule.atoms]
    for i, j, _ in connections(molecule):
        near[i].append(j)
        near[j].append(i)
    parts = _parts(len(molecule.atoms), near)
    solvents = _solvent_formulas()
    first = _solute(parts)
    return {k for n, part in enumerate(parts)
            if n == first or Molecule('', tuple(molecule.atoms[i] for i in part), None).formula not in solvents
            for k in part}


def solute_sites(molecule):
    """The sites of the first shell of the structure itself — not of the molecules of a solvent put round it before (its
    parts of the formula of a solvent of SOLVENTS, when something else is there) — and not those taken already (a
    hydrogen of another part within 2.3 Å of an acceptor, an O, N, F, S of another part within 2.3 Å of a donor H). ->
    (acceptors, donors, taken)."""
    bonds = connections(molecule)
    near = [[] for _ in molecule.atoms]
    for i, j, _ in bonds:
        near[i].append(j)
        near[j].append(i)
    parts = _parts(len(molecule.atoms), near)
    part_of = {k: n for n, part in enumerate(parts) for k in part}
    solvents = _solvent_formulas()

    def formula(part):
        return Molecule('', tuple(molecule.atoms[k] for k in part), None).formula

    kept = {n for n, part in enumerate(parts) if formula(part) not in solvents} | {_solute(parts)}
    acceptors, donors = _sites(molecule)
    acceptors = [(k, d) for k, d in acceptors if part_of[k] in kept]
    donors = [(k, owner) for k, owner in donors if part_of[k] in kept]

    def partner(k, symbols, direction=None):
        here = molecule.atoms[k].position
        # 2.6 Å: a hydrogen bond of a structure opened after an optimization may be longer than the 1.9 Å it was put at;
        # a lone pair is taken by a hydrogen on its side (within ~50°), the other pair of the O stays free
        for m, a in enumerate(molecule.atoms):
            if part_of[m] == part_of[k] or a.symbol not in symbols:
                continue
            r = dist(a.position, here)
            if r >= 2.6:
                continue
            if direction is None or sum((a.position[c] - here[c]) * direction[c] for c in range(3)) > 0.64 * r:
                return True
        return False

    free_acceptors = [(k, d) for k, d in acceptors if not partner(k, ('H',), d)]
    free_donors = [(k, owner) for k, owner in donors if not partner(k, ('O', 'N', 'F', 'S'))]
    taken = len(acceptors) - len(free_acceptors) + len(donors) - len(free_donors)
    return free_acceptors, free_donors, taken


def without_solvent(molecule):
    """The structure without the molecules of a solvent
    put round it — its parts of the formula of a solvent of SOLVENTS, when something else is there (as solute_sites).
    -> (the structure, how many molecules were taken away)."""
    near = [[] for _ in molecule.atoms]
    for i, j, _ in connections(molecule):
        near[i].append(j)
        near[j].append(i)
    parts = _parts(len(molecule.atoms), near)
    solvents = _solvent_formulas()
    solute = _solute(parts)
    gone = [part for n, part in enumerate(parts) if n != solute
            and Molecule('', tuple(molecule.atoms[k] for k in part), None).formula in solvents]
    if not gone:
        return molecule, 0
    result = delete_atoms(molecule, [k for part in gone for k in part])
    if molecule.bonds is None:
        result = Molecule(result.title, result.atoms, None)
    return result, len(gone)


def _cone(axis, rng, tilts=(0, 12, 24, 36), around=8):
    """The directions round axis: itself first, then tilted by tilts (degrees) at around azimuths."""
    from math import radians

    axis = _norm(axis)
    side = (1.0, 0.0, 0.0) if abs(axis[0]) < 0.9 else (0.0, 1.0, 0.0)
    first = _norm((axis[1] * side[2] - axis[2] * side[1], axis[2] * side[0] - axis[0] * side[2],
                   axis[0] * side[1] - axis[1] * side[0]))
    second = (axis[1] * first[2] - axis[2] * first[1], axis[2] * first[0] - axis[0] * first[2],
              axis[0] * first[1] - axis[1] * first[0])
    yield axis
    for tilt in tilts[1:]:
        start = rng.random() * 2 * pi
        for k in range(around):
            phi = start + 2 * pi * k / around
            t = radians(tilt)
            yield _norm(tuple(axis[c] * cos(t) + sin(t) * (first[c] * cos(phi) + second[c] * sin(phi))
                              for c in range(3)))


def _shell_pieces(molecule, solvent, local, count, rng, placed_atoms):
    """The first shell: one molecule of the solvent on each acceptor of the structure (its donor H toward the free side
    of the acceptor, D–H···A in a line, H···A = HBOND) and on each donor H of the structure (its acceptor at HBOND on
    the line X–H, its free side toward the H). -> [[Atom]] placed (placed_atoms grows)."""
    acceptors, donors, _ = solute_sites(molecule)
    s_acceptors, s_donors = _sites(solvent)
    pieces = []
    jobs = []
    if s_donors:
        jobs += [('acceptor', site) for site in acceptors]
    if s_acceptors:
        jobs += [('donor', k) for k in donors]
    for kind, site in jobs:
        if len(pieces) >= count:
            break
        if kind == 'acceptor':
            site, ideal = site  # the atom and the direction of its lone pair
            hydrogen, owner = s_donors[0]
            h, d = local[hydrogen][1], local[owner][1]
            pin, contact_atom = hydrogen, site
        else:
            k, owner = site
            ideal = _norm(tuple(molecule.atoms[k].position[c] - molecule.atoms[owner].position[c] for c in range(3)))
            acceptor, lone = s_acceptors[0]  # a lone pair of the solvent's acceptor looks back to the H
            pin, contact_atom = acceptor, k
        target = molecule.atoms[contact_atom].position
        # a hydrogen bond bends — the line is tried as it should be,
        # then tilted up to 40° round it, and the molecule turned about the line, until nothing is in the way
        done = False
        for out in _cone(ideal, rng):
            if kind == 'acceptor':
                base = _aligning(tuple(d[c] - h[c] for c in range(3)), out)  # D–H···A in a line along out
            else:
                base = _aligning(lone, tuple(-c for c in out))
            anchor = tuple(target[c] + out[c] * HBOND for c in range(3))
            for attempt in range(12):
                turn = _times(_about(out, 2 * pi * attempt / 12 + rng.random() * 0.3), base)
                pinned = _turned(turn, local[pin][1])
                new = [Atom(symbol, *(anchor[c] - pinned[c] + _turned(turn, p)[c] for c in range(3)))
                       for symbol, p in local]
                if _clear(new, placed_atoms, (pin, contact_atom)):
                    placed_atoms += new
                    pieces.append(new)
                    done = True
                    break
            if done:
                break
    return pieces


def shell_places(molecule, solvent):
    """How many molecules of solvent the first shell of the structure takes — its acceptors when the solvent
    has a donor H, its O–H and N–H when the solvent has an acceptor; the free ones of the structure itself
    (solute_sites)."""
    acceptors, donors, _ = solute_sites(molecule)
    s_acceptors, s_donors = _sites(solvent)
    return (len(acceptors) if s_donors else 0) + (len(donors) if s_acceptors else 0)


def solvate(molecule, solvent, count, seed=1, tries=600, shell=True, report=None, around=True):
    """(the structure with up to count copies of solvent round it, the number placed). Shell — the first shell first, by
    hydrogen bonds to the polar centres (_shell_pieces), the rest round the structure at random. report — a dict filled
    with 'shell' (put in the first shell) and 'places' (shell_places)."""
    if not molecule.atoms:
        raise ValueError(tr('Сначала нужна структура.'))
    if not solvent.atoms or count < 1:
        if report is not None:  # the first shell full already: said as well (Компас says how many are taken)
            report.update(shell=0, places=shell_places(molecule, solvent) if shell and solvent.atoms else 0,
                          taken=solute_sites(molecule)[2] if shell else 0)
        return molecule, 0
    rng = random.Random(seed)
    centre = [sum(a.position[k] for a in solvent.atoms) / len(solvent.atoms) for k in range(3)]
    local = [(a.symbol, (a.x - centre[0], a.y - centre[1], a.z - centre[2])) for a in solvent.atoms]
    size = max(sqrt(sum(c * c for c in p)) for _, p in local)
    # the new molecules go round the structure itself, never round the solvent there before
    own = solute_atoms(molecule)
    anchors = [k for k, a in enumerate(molecule.atoms) if a.symbol != 'X' and k in own]
    weights = [2.0 if molecule.atoms[k].symbol in ('N', 'O', 'F', 'S', 'Cl') else 1.0 for k in anchors]
    placed_atoms = list(molecule.atoms)
    pieces = []
    if shell:
        relative = Molecule(solvent.title, tuple(Atom(sym, *p) for sym, p in local), solvent.bonds)
        pieces += _shell_pieces(molecule, relative, local, count, rng, placed_atoms)
    if report is not None:
        report['shell'] = len(pieces)
        report['places'] = shell_places(molecule, solvent) if shell else 0
        report['taken'] = solute_sites(molecule)[2] if shell else 0
    for _ in range(count * tries if around else 0):  # around=False: the first shell alone
        if len(pieces) >= count:
            break
        anchor = molecule.atoms[rng.choices(anchors, weights)[0]].position
        reach = 2.4 + size + 1.8 * rng.random()
        direction = _unit(rng)
        middle = tuple(anchor[k] + direction[k] * reach for k in range(3))
        turn = _rotation(rng)
        new = [Atom(symbol, *(middle[k] + _turned(turn, p)[k] for k in range(3))) for symbol, p in local]
        if _clear(new, placed_atoms):
            placed_atoms += new
            pieces.append(new)
    edges = None
    if molecule.bonds is not None or solvent.bonds is not None:
        edges = list(connections(molecule))
        offset = len(molecule.atoms)
        own = list(connections(solvent))
        for _ in pieces:
            edges += [(i + offset, j + offset, o) for i, j, o in own]
            offset += len(solvent.atoms)
        edges = tuple(edges)
    return Molecule(molecule.title, tuple(placed_atoms), edges), len(pieces)


# -- protons ------------------------------------------------------------------------------------------------------------
def protonate(molecule, index):
    """(the structure with an H on atom index, the index of that H)."""
    atom = molecule.atoms[index]
    if atom.symbol in ('H', 'X'):
        raise ValueError(tr('Протон ставится на тяжёлый атом — выделите его, а не водород.'))
    direction = outgoing(molecule, index)
    length = bond_length(atom.symbol, 'H', 1)
    hydrogen = Atom('H', *(atom.position[k] + direction[k] * length for k in range(3)))
    edges = None
    if molecule.bonds is not None:
        edges = tuple(connections(molecule)) + ((index, len(molecule.atoms), 1),)
    return Molecule(molecule.title, molecule.atoms + (hydrogen,), edges), len(molecule.atoms)


def _hydrogens_of(molecule, index):
    return [j if i == index else i for i, j, _ in connections(molecule)
            if index in (i, j) and molecule.atoms[j if i == index else i].symbol == 'H']


def deprotonate(molecule, index):
    """(the structure without one H — the atom itself when it is an H, else its last H; the index of its atom after)."""
    if molecule.atoms[index].symbol == 'H':
        hydrogen = index
        owner = next((j if i == index else i for i, j, _ in connections(molecule) if index in (i, j)), None)
    else:
        found = _hydrogens_of(molecule, index)
        if not found:
            raise ValueError(tr('У атома {} нет водорода, который можно снять.').format(_name(molecule, index)))
        hydrogen, owner = max(found), index
    result = delete_atoms(molecule, [hydrogen])
    if molecule.bonds is None:
        result = Molecule(result.title, result.atoms, None)
    if owner is not None and owner > hydrogen:
        owner -= 1
    return result, owner


def move_proton(molecule, hydrogen, target):
    """(the structure with the H hydrogen carried from its atom to target, the new index of that H) — a tautomer."""
    if molecule.atoms[hydrogen].symbol != 'H':
        hydrogen, target = target, hydrogen
    if molecule.atoms[hydrogen].symbol != 'H' or molecule.atoms[target].symbol in ('H', 'X'):
        raise ValueError(tr('Выделите водород и атом, к которому его перенести.'))
    if target in _hydrogens_of_owner(molecule, hydrogen):
        raise ValueError(tr('Этот водород уже у выделенного атома.'))
    without, _ = deprotonate(molecule, hydrogen)
    return protonate(without, target - (1 if target > hydrogen else 0))


def _hydrogens_of_owner(molecule, hydrogen):
    return [j if i == hydrogen else i for i, j, _ in connections(molecule) if hydrogen in (i, j)]

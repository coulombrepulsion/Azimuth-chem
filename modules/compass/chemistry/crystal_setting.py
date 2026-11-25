"""Another setting of the cell of a crystal: the axes changed by a matrix, the reduced cell, the name of
the setting — as «Unit cell transformation» and «Reduced cell» of Mercury.

§1 THEORY
    The same crystal is described by many cells: the axes renamed (P 21/c with a and c swapped is P 21/a), the
    monoclinic cell choices (P 21/c, P 21/n, P 21/a — the same group 14), a centred cell or a primitive one. New axes
    A' = M A (rows; M — rational, its rows the new edges in fractions of the old). A point r = f A = f' A' keeps its
    place: f' = f M⁻¹ (rows), as columns f' = Q f with Q = M⁻ᵀ. An operation x → R x + t becomes Q R Q⁻¹ x + Q t;
    when the new cell is larger (det M = n > 1) the old lattice vectors inside it, Q·(whole vectors) mod 1, are added
    as translations; when it is smaller (a primitive cell of a centred lattice) the centring translations become
    whole and the operations that differ by them are one. The reduced cell (Buerger, Niggli): the three shortest
    lattice vectors of the primitive lattice that span it, all their angles acute or all not acute, right-handed —
    one cell for one lattice, whatever the file chose: two files of one crystal agree in it.
    The name of a setting: the table of the 530 settings (space_groups) — the one whose operations (R, t mod 1) are
    those of the crystal; a setting with a shifted origin is not named.
§2 ALGORITHM
    transform(crystal, M) — exact in fractions (Fraction); identify(operations) — a dictionary of the 530 sets of
    operations, built once; reduced_matrix(crystal) — the lattice vectors n·P·A (P — the primitive cell in fractions of
    the cell, |n_i| ≤ 2) by length, the shortest three with det n = ±1, the signs for one kind of angles and a right
    hand; settings(crystal) — the cell transformed by the 24 rotations of the axes, each times the monoclinic cell
    choices (I, C₁→C₂, C₁→C₃ for each axis as the unique one), named; for each name the cell with its angles nearest
    to 90° and the simplest matrix.
§4 SPECIFICATION
    transform(crystal, M) -> Crystal; identify(operations) -> entry | None (space_groups); reduced_matrix(crystal) ->
    3 × 3 Fractions; settings(crystal) -> [(entry, M, cell)], the setting of the file first; matrix_text(M).
§7 TESTS tests/compass/test_crystal_setting.py — benzoic acid P 21/c → P 21/n and back, the atoms in the same
    places; the reduced cell of rock salt (a/√2, 60°); the cell of the file named; the powder pattern unchanged.
"""

from dataclasses import replace
from fractions import Fraction
from functools import lru_cache
from itertools import permutations, product
from math import acos, degrees

import numpy as np


def _matrix(m):
    return [[Fraction(x).limit_denominator(48) for x in row] for row in m]


def _mul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


def _vec(a, v):
    return [sum(a[i][k] * v[k] for k in range(3)) for i in range(3)]


def _det(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def _inverse(m):
    d = _det(m)
    if d == 0:
        raise ValueError('a matrix of a cell needs det ≠ 0')
    c = [[(m[(j + 1) % 3][(i + 1) % 3] * m[(j + 2) % 3][(i + 2) % 3]
           - m[(j + 1) % 3][(i + 2) % 3] * m[(j + 2) % 3][(i + 1) % 3]) for j in range(3)] for i in range(3)]
    return [[c[i][j] / d for j in range(3)] for i in range(3)]


def _transpose(m):
    return [[m[j][i] for j in range(3)] for i in range(3)]


def _op_key(rows, t):
    return tuple(tuple(int(x) for x in r) for r in rows), tuple(Fraction(x) % 1 for x in t)


def _new_operations(operations, m):
    q = _transpose(_inverse(m))
    qi = _inverse(q)
    det = abs(_det(m))
    extra = {(Fraction(0),) * 3}
    if det > 1:
        n = int(det) + 1
        for v in product(range(-n, n + 1), repeat=3):
            extra.add(tuple(x % 1 for x in _vec(q, [Fraction(x) for x in v])))
    out = {}
    for rows, t in operations:
        r = _mul(_mul(q, [[Fraction(x) for x in row] for row in rows]), qi)
        if any(x.denominator != 1 for row in r for x in row):
            raise ValueError('the matrix does not map the lattice onto itself')
        tt = _vec(q, [Fraction(x) for x in t])
        for e in extra:
            k = _op_key(r, [tt[i] + e[i] for i in range(3)])
            out.setdefault(k, (tuple(tuple(int(x) for x in row) for row in r), k[1]))
    return tuple(out[k] for k in sorted(out))


def _cell_of(rows):
    from modules.compass.chemistry import crystal as cr

    a, b, c = (float(np.linalg.norm(v)) for v in rows)

    def angle(u, v):
        return degrees(acos(max(-1.0, min(1.0, float(np.dot(u, v)) / (np.linalg.norm(u) * np.linalg.norm(v))))))

    return cr.Cell(a, b, c, angle(rows[1], rows[2]), angle(rows[0], rows[2]), angle(rows[0], rows[1]))


def transform(crystal, m):
    """The crystal in the cell with the edges M A (M — rows of the new edges in fractions of the old ones)."""

    m = _matrix(m)
    if _det(m) <= 0:
        raise ValueError('the new axes must stay right-handed (det M > 0)')
    rows = np.array(crystal.cell.vectors(), dtype=float)
    new_rows = np.array([[float(x) for x in row] for row in m]) @ rows
    q = _transpose(_inverse(m))
    sites = []
    for s in crystal.sites:
        f = _vec(q, [Fraction(s.x).limit_denominator(10 ** 6), Fraction(s.y).limit_denominator(10 ** 6),
                     Fraction(s.z).limit_denominator(10 ** 6)])
        f = [float(x) % 1.0 for x in f]
        sites.append(replace(s, x=f[0], y=f[1], z=f[2], u=()))  # the anisotropic U are in the old axes: dropped
    operations = _new_operations(crystal.operations, m)
    entry = identify(operations)
    name = entry_name(entry)
    note = 'Ячейка в другой установке: ' + matrix_text(m)
    return replace(crystal, cell=_cell_of(new_rows).validate(), sites=tuple(sites), operations=operations,
                   space_group=name, number=entry['number'] if entry else crystal.number,
                   notes=tuple(crystal.notes) + (note,),
                   formula_z=crystal.formula_z * float(abs(_det(m))) if crystal.formula_z else 0)


@lru_cache(maxsize=1)
def _settings_table():
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import space_groups

    found = {}
    for entry in space_groups._table()[0]:
        keys = frozenset(_op_key(*cr.operation(text)) for text in space_groups.operations(entry))
        found.setdefault(keys, entry)
    return found


def identify(operations):
    return _settings_table().get(frozenset(_op_key(r, t) for r, t in operations))


def entry_name(entry):
    return entry['full'].replace('_', '') if entry else ''


def matrix_text(m):
    names = 'abc'
    out = []
    for row in _matrix(m):
        terms = ''
        for x, n in zip(row, names):
            if x == 0:
                continue
            sign = '−' if x < 0 else ('+' if terms else '')
            size = abs(x)
            terms += sign + ('' if size == 1 else (str(size) if size.denominator == 1 else f'({size})')) + n
        out.append(terms or '0')
    return 'a′ = {}, b′ = {}, c′ = {}'.format(*out)


def reduced_matrix(crystal):
    from modules.compass.chemistry import crystal as cr

    rows = np.array(crystal.cell.vectors(), dtype=float)
    basis = cr.primitive_basis(crystal)
    p = _matrix(np.eye(3) if basis is None else basis)
    prim = np.array([[float(x) for x in row] for row in p]) @ rows
    vectors = []
    for n in product(range(-2, 3), repeat=3):
        if n != (0, 0, 0):
            v = np.array(n, dtype=float) @ prim
            vectors.append((float(np.linalg.norm(v)), n, v))
    vectors.sort(key=lambda x: (round(x[0], 6), x[1]))
    chosen = []
    for _, n, v in vectors:
        if len(chosen) == 0:
            chosen.append((n, v))
        elif len(chosen) == 1:
            if np.linalg.norm(np.cross(chosen[0][1], v)) > 1e-6 * np.linalg.norm(v) ** 2:
                chosen.append((n, v))
        else:
            det = round(float(np.linalg.det(np.array([chosen[0][0], chosen[1][0], n], dtype=float))))
            if abs(det) == 1:
                chosen.append((n, v))
                break
    ns = [list(c[0]) for c in chosen]
    vs = [c[1] for c in chosen]
    # one kind of angles: the products b·c, a·c, a·b all > 0 or all ≤ 0 (Niggli type I or II)
    products = [np.dot(vs[1], vs[2]), np.dot(vs[0], vs[2]), np.dot(vs[0], vs[1])]
    positive = sum(1 for x in products if x > 1e-9)
    want = positive >= 2
    for _ in range(3):
        products = [np.dot(vs[1], vs[2]), np.dot(vs[0], vs[2]), np.dot(vs[0], vs[1])]
        wrong = [k for k, x in enumerate(products) if (x > 1e-9) != want and abs(x) > 1e-9]
        if not wrong:
            break
        k = wrong[0]  # the product of the pair without axis k: flip one of that pair
        flip = (k + 1) % 3
        vs[flip] = -vs[flip]
        ns[flip] = [-x for x in ns[flip]]
    if np.linalg.det(np.array(vs)) < 0:
        vs = [-v for v in vs]
        ns = [[-x for x in n] for n in ns]
    return _mul([[Fraction(x) for x in n] for n in ns], p)


def _choices():
    """The 24 rotations of the axes, each with the monoclinic cell choices for each axis as the unique one."""
    rotations = []
    for perm in permutations(range(3)):
        for signs in product((1, -1), repeat=3):
            m = [[Fraction(signs[i]) if j == perm[i] else Fraction(0) for j in range(3)] for i in range(3)]
            if _det(m) == 1:
                rotations.append(m)
    shears = [[[Fraction(int(i == j)) for j in range(3)] for i in range(3)]]
    for unique in range(3):
        a, c = [k for k in range(3) if k != unique]
        for rows in (((a, (0, 0, 1)), (c, (-1, 0, -1))), ((a, (-1, 0, -1)), (c, (1, 0, 0)))):
            m = [[Fraction(int(i == j)) for j in range(3)] for i in range(3)]
            for axis, (x, _, z) in rows:
                m[axis] = [Fraction(0)] * 3
                m[axis][a], m[axis][c] = Fraction(x), Fraction(z)
            if _det(m) == 1:
                shears.append(m)
    return [_mul(s, r) for r in rotations for s in shears]


def settings(crystal):
    """[(entry, M, cell)] — the named settings of the crystal reached by the axes renamed and the monoclinic cell
    choices; the setting of the file first (M = 1)."""
    rows = np.array(crystal.cell.vectors(), dtype=float)
    best = {}
    own = identify(crystal.operations)
    choices = _choices()
    if len(crystal.operations) > 32:  # cubic, hexagonal, most tetragonal: the axes renamed give the same name
        choices = choices[:1]
    for m in choices:
        try:
            ops = _new_operations(crystal.operations, m)
        except ValueError:
            continue
        entry = identify(ops)
        if entry is None:
            continue
        cell = _cell_of(np.array([[float(x) for x in row] for row in m]) @ rows)
        score = (round(sum(abs(x - 90) for x in (cell.alpha, cell.beta, cell.gamma)), 3),
                 sum(1 for row in m for x in row if x != 0), [[-float(x) for x in row] for row in m])
        if entry['hall'] not in best or score < best[entry['hall']][0]:
            best[entry['hall']] = (score, entry, m, cell)
    items = sorted(best.values(), key=lambda x: (x[1] is not own, x[1]['hall']))
    if own is not None and own['hall'] in best:
        identity = [[Fraction(int(i == j)) for j in range(3)] for i in range(3)]
        items = [(None, own, identity, crystal.cell)] + [x for x in items if x[1] is not own]
    return [(entry, m, cell) for _, entry, m, cell in items]

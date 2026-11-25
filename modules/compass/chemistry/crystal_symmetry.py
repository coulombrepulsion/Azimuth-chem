"""The symmetry of a crystal from its operations; whole molecules across the cell faces.

§1 THEORY
    A space-group operation x -> W x + w (fractional coordinates; W an integer matrix, w translations)
    has, by the International Tables (ITA, vol. A, sect. 1.2.2), a type fixed by det W and tr W:
        det +1: tr 3 -> 1, tr -1 -> 2, tr 0 -> 3, tr 1 -> 4, tr 2 -> 6;
        det -1: tr -3 -> -1, tr 1 -> m (= -2), tr 0 -> -3, tr -1 -> -4, tr -2 -> -6.
    With k the order of W and Y(W) = W^(k-1) + ... + W + I, the intrinsic (screw or glide) part of the
    translation is w_g = Y(W) w / k (zero for the rotoinversions -1, -3, -4, -6); the location of the
    element is the set of fixed points of x -> W x + (w - w_g): the solutions of (W - I) x = -(w - w_g).
    The axis of a rotation is the direction Y(W) maps onto (for m and the rotoinversions: of -W); a screw
    n_p has w_g = (p / n) u for the shortest lattice vector u along the axis, p counted in the sense of
    the rotation; a glide is a, b or c (w_g = half a cell edge), n (half a face diagonal), d (a quarter of
    one), and g otherwise. The pure translations (W = I) are the centring of the lattice: none P, A, B,
    C, I, F, R (obverse: 2/3 1/3 1/3). The rotation parts W of all operations form the point group; the
    numbers of its elements of each type single out one of the 32 crystallographic point groups (checked
    for all 32 by the tests), and the point group the crystal system and the range of the space-group
    numbers in ITA (1; 2; 3-5; 6-9; 10-15; 16-24; 25-46; 47-74; 75-80; 81-82; 83-88; 89-98; 99-110;
    111-122; 123-142; 143-146; 147-148; 149-155; 156-161; 162-167; 168-173; 174; 175-176; 177-182;
    183-186; 187-190; 191-194; 195-199; 200-206; 207-214; 215-220; 221-230).
    Z, the formula units in the cell: the cell content (each site times its number of copies and its
    occupancy) divided by _chemical_formula_sum, or _cell_formula_units_Z, or the greatest common divisor
    of the counts; Z' = Z / (number of operations). The density rho = M_cell / (N_A V).
§2 ALGORITHM
    describe(op): the type, the order, Y(W), w_g, the axis or the plane normal (the primitive integer
    vector), the fixed points by Gaussian elimination in fractions (none: the element is located
    nowhere, which happens only for a translation), a symbol (2_1, 4_2, c, n, -4 ...) and a Russian text.
    analyse(crystal): closure of the operations modulo the lattice (a missing product is a note), the
    centring, the point group and system, the number of the file checked against the range of the point
    group, Z, Z', rho.
    molecules(crystal, factor): the atoms of the cell (crystal.unit_cell) bonded when d <= factor (r1 + r2)
    (covalent radii, coordination.radius, 0.8 A when unknown) to any of the 27 images of each other; a
    walk over the bonds gives each atom the cell shift of its image; a component that meets itself with
    another shift is infinite (its periodic directions give a chain, a layer or a framework), the others
    are molecules, moved by a lattice vector so that their centroid lies in the cell [0, 1)^3.
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py (the «Кристалл» window: the group, Z, the operations, «Целые
    молекулы»).
§4 SPECIFICATION
    describe(op) -> dict(kind, order, symbol, axis, glide (w_g as Fractions), point (a fixed point or
    None), text); analyse(crystal) -> Symmetry; molecules(crystal, factor=None) -> Packing;
    whole_molecules(crystal, n=(1, 1, 1), factor=None) -> Molecule (the molecules of n1 x n2 x n3 cells).
§5 PROCEDURES - below.
§6 NOTES
    Infinite components (salts, metals, frameworks) are not cut: their atoms stay as in the cell. Atoms
    of partial occupancy are kept (as crystal.build). The symbol is the one of the operation as given;
    an element that is a glide in one setting and a mirror after adding a centring vector is listed as
    both (ITA lists them so as well).
§7 TESTS
    tests/compass/test_crystal_symmetry.py.
§8' ROBUSTNESS / ERRORS
    W with |det| != 1 is refused (crystal.operation already refuses empty rows); a cell above MAX_ATOMS
    atoms: ValueError (crystal.build).
"""

from dataclasses import dataclass, field
from fractions import Fraction
from math import floor, gcd

from azimuth.i18n import tr

AVOGADRO = 6.02214076e23

# -- matrices of integers and fractions ------------------------------------------------------------------
I3 = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


def _mul(a, b):
    return tuple(tuple(sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)) for i in range(3))


def _apply(m, v):
    return tuple(sum(m[i][k] * v[k] for k in range(3)) for i in range(3))


def _det(m):
    return (m[0][0] * (m[1][1] * m[2][2] - m[1][2] * m[2][1]) - m[0][1] * (m[1][0] * m[2][2] - m[1][2] * m[2][0])
            + m[0][2] * (m[1][0] * m[2][1] - m[1][1] * m[2][0]))


def _neg(m):
    return tuple(tuple(-x for x in row) for row in m)


def _add(a, b):
    return tuple(tuple(a[i][j] + b[i][j] for j in range(3)) for i in range(3))


def _frac(v):
    """A fraction in [0, 1)."""
    v = Fraction(v)
    return v - floor(v)


def _sym(v):
    """A fraction in (-1/2, 1/2]."""
    v = _frac(v)
    return v - 1 if v > Fraction(1, 2) else v


# -- one operation ---------------------------------------------------------------------------------------
TYPES = {(1, 3): '1', (1, -1): '2', (1, 0): '3', (1, 1): '4', (1, 2): '6',
         (-1, -3): '-1', (-1, 1): 'm', (-1, 0): '-3', (-1, -1): '-4', (-1, -2): '-6'}
ORDER = {'1': 1, '2': 2, '3': 3, '4': 4, '6': 6, '-1': 2, 'm': 2, '-3': 6, '-4': 4, '-6': 6}
SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
AXES = 'xyz'


def kind(rows):
    d = _det(rows)
    if d not in (1, -1):
        raise ValueError(tr('Операция симметрии с определителем, не равным ±1.'))
    found = TYPES.get((d, rows[0][0] + rows[1][1] + rows[2][2]))
    if found is None:
        raise ValueError(tr('Операция симметрии не кристаллографическая.'))
    return found


def _y(rows, k):
    total, power = I3, I3
    for _ in range(k - 1):
        power = _mul(power, rows)
        total = _add(total, power)
    return total


def _primitive(v):
    v = [Fraction(x) for x in v]
    if not any(v):
        return None
    den = 1
    for x in v:
        den = den * x.denominator // gcd(den, x.denominator)
    ints = [int(x * den) for x in v]
    g = 0
    for x in ints:
        g = gcd(g, abs(x))
    ints = [x // g for x in ints]
    first = next(x for x in ints if x)
    return tuple(-x for x in ints) if first < 0 else tuple(ints)


def _axis(rows, t):
    """The direction of the axis the primitive integer vector Y maps onto."""
    proper = rows if _det(rows) == 1 else _neg(rows)
    k = ORDER[kind(proper)]
    y = _y(proper, k)
    for j in range(3):
        col = _primitive((y[0][j], y[1][j], y[2][j]))
        if col is not None:
            return col
    return None


def _solve(a, b):
    """A solution of a x = b (3 x 3, fractions) or None; free unknowns are set to 0."""
    m = [[Fraction(a[i][j]) for j in range(3)] + [Fraction(b[i])] for i in range(3)]
    pivots, row = [], 0
    for col in range(3):
        p = next((r for r in range(row, 3) if m[r][col] != 0), None)
        if p is None:
            continue
        m[row], m[p] = m[p], m[row]
        div = m[row][col]
        m[row] = [x / div for x in m[row]]
        for r in range(3):
            if r != row and m[r][col] != 0:
                f = m[r][col]
                m[r] = [m[r][c] - f * m[row][c] for c in range(4)]
        pivots.append(col)
        row += 1
    if any(m[r][3] != 0 and not any(m[r][:3]) for r in range(3)):
        return None
    x = [Fraction(0)] * 3
    for r, col in enumerate(pivots):
        x[col] = m[r][3]
    return tuple(x)


def _num(v):
    v = Fraction(v)
    if v.denominator == 1:
        return str(v.numerator)
    return f'{"-" if v < 0 else ""}{abs(v.numerator)}/{v.denominator}'


def _direction(u):
    return '[' + ''.join(str(x) if x >= 0 else '-' + str(-x) for x in u) + ']'


def _glide_letter(w):
    w = [_sym(x) for x in w]
    nonzero = [i for i in range(3) if w[i] != 0]
    half, quarter = Fraction(1, 2), Fraction(1, 4)
    if len(nonzero) == 1 and abs(w[nonzero[0]]) == half:
        return 'abc'[nonzero[0]]
    if len(nonzero) >= 2 and all(abs(w[i]) == half for i in nonzero):
        return 'n'
    if len(nonzero) >= 2 and all(abs(w[i]) == quarter for i in nonzero):
        return 'd'
    return 'g'


def _sense(rows, u):
    """+1 or -1: the sense of the rotation about u (det of u, v, W v for a v off the axis)."""
    for v in ((1, 0, 0), (0, 1, 0), (0, 0, 1)):
        wv = _apply(rows, v)
        d = _det((tuple(u), v, wv))
        if d:
            return 1 if d > 0 else -1
    return 1


def describe(op):
    rows, shifts = op
    t = tuple(Fraction(x) for x in shifts)
    name = kind(rows)
    order = ORDER[name]
    info = {'kind': name, 'order': order, 'axis': None, 'glide': (Fraction(0),) * 3, 'point': None}
    if name == '1':
        tr_ = tuple(_sym(x) for x in t)
        if any(tr_):
            info.update(symbol='t', text=tr('Трансляция (центрировка) на ({})').format(', '.join(_num(x) for x in tr_)))
        else:
            info.update(symbol='1', text=tr('Тождественная операция'))
        return info
    if name in ('2', '3', '4', '6', 'm'):
        y = _y(rows, order)
        wg = tuple(Fraction(x) / order for x in _apply(y, t))
    else:
        wg = (Fraction(0),) * 3
    info['glide'] = wg
    rest = tuple(t[i] - wg[i] for i in range(3))
    point = _solve(_add(rows, _neg(I3)), tuple(-x for x in rest))
    if point is not None:
        point = tuple(_frac(x) for x in point)
    info['point'] = point
    if name == '-1':
        info.update(symbol='-1', text=tr('Центр инверсии в точке {}').format(_where(point)))
        return info
    u = _axis(rows, t)
    info['axis'] = u
    if name == 'm':
        letter = 'm' if not any(_sym(x) for x in wg) else _glide_letter(wg)
        title = tr('Зеркальная плоскость') if letter == 'm' else tr('Плоскость скользящего отражения {}').format(letter)
        info.update(symbol=letter, text=f'{title} ⊥ {_direction(u)}, {_plane(u, point)}')
        return info
    if name in ('-3', '-4', '-6'):
        info.update(symbol=name, text=tr('Инверсионная ось {} ∥ {}, точка инверсии {}').format(
            name.replace('-', '−'), _direction(u), _where(point)))
        return info
    p = 0
    if any(wg):
        ratio = next(wg[i] / u[i] for i in range(3) if u[i])
        p = int(ratio * order) % order
        if p and _sense(rows, u) < 0:
            p = order - p
    symbol = name + (str(p).translate(SUB) if p else '')
    title = (tr('Винтовая ось {}') if p else tr('Поворотная ось {}')).format(symbol)
    info.update(symbol=symbol, text=f'{title} ∥ {_direction(u)}, {_line(u, point)}')
    return info


def _where(point):
    return '(' + ', '.join(_num(x) for x in point) + ')' if point is not None else '—'


def _line(u, point):
    if point is None:
        return ''
    fixed = [f'{AXES[i]} = {_num(point[i])}' for i in range(3) if u[i] == 0]
    if len(fixed) == 2:
        return tr('проходит через {}').format(', '.join(fixed))
    return tr('проходит через точку {}').format(_where(point))


def _plane(n, point):
    if point is None:
        return ''
    value = sum(Fraction(n[i]) * point[i] for i in range(3))
    terms = []
    for i in range(3):
        if n[i] == 0:
            continue
        c = n[i]
        sign = '−' if c < 0 else ('+' if terms else '')
        mag = '' if abs(c) == 1 else str(abs(c))
        terms.append(f'{sign} {mag}{AXES[i]}'.strip() if terms else f'{"−" if c < 0 else ""}{mag}{AXES[i]}')
    return ' '.join(terms) + ' = ' + _num(value)


# -- the 32 point groups ---------------------------------------------------------------------------------
def _closure(generators):
    found = {I3}
    frontier = [I3]
    while frontier:
        new = []
        for a in frontier:
            for g in generators:
                p = _mul(a, g)
                if p not in found:
                    found.add(p)
                    new.append(p)
        frontier = new
    return found


_INV = _neg(I3)
_C = {'4z': ((0, -1, 0), (1, 0, 0), (0, 0, 1)), '2z': ((-1, 0, 0), (0, -1, 0), (0, 0, 1)),
      '2y': ((-1, 0, 0), (0, 1, 0), (0, 0, -1)), '2x': ((1, 0, 0), (0, -1, 0), (0, 0, -1)),
      'mx': ((-1, 0, 0), (0, 1, 0), (0, 0, 1)), 'mz': ((1, 0, 0), (0, 1, 0), (0, 0, -1)),
      '3d': ((0, 0, 1), (1, 0, 0), (0, 1, 0)), '-4z': ((0, 1, 0), (-1, 0, 0), (0, 0, -1)), '-1': _INV}
_H6 = ((1, -1, 0), (1, 0, 0), (0, 0, 1))
_H3 = _mul(_H6, _H6)
_H2 = ((1, -1, 0), (0, -1, 0), (0, 0, -1))  # 2 along a in the hexagonal basis
POINT_GROUPS = (  # (Hermann-Mauguin, system, the first and the last space-group number, generators)
    ('1', 'triclinic', 1, 1, ()), ('-1', 'triclinic', 2, 2, (_INV,)),
    ('2', 'monoclinic', 3, 5, (_C['2z'],)), ('m', 'monoclinic', 6, 9, (_C['mz'],)),
    ('2/m', 'monoclinic', 10, 15, (_C['2z'], _INV)),
    ('222', 'orthorhombic', 16, 24, (_C['2z'], _C['2y'])), ('mm2', 'orthorhombic', 25, 46, (_C['2z'], _C['mx'])),
    ('mmm', 'orthorhombic', 47, 74, (_C['2z'], _C['2y'], _INV)),
    ('4', 'tetragonal', 75, 80, (_C['4z'],)), ('-4', 'tetragonal', 81, 82, (_C['-4z'],)),
    ('4/m', 'tetragonal', 83, 88, (_C['4z'], _INV)), ('422', 'tetragonal', 89, 98, (_C['4z'], _C['2x'])),
    ('4mm', 'tetragonal', 99, 110, (_C['4z'], _C['mx'])), ('-42m', 'tetragonal', 111, 122, (_C['-4z'], _C['2x'])),
    ('4/mmm', 'tetragonal', 123, 142, (_C['4z'], _C['2x'], _INV)),
    ('3', 'trigonal', 143, 146, (_H3,)), ('-3', 'trigonal', 147, 148, (_H3, _INV)),
    ('32', 'trigonal', 149, 155, (_H3, _H2)), ('3m', 'trigonal', 156, 161, (_H3, _neg(_H2))),
    ('-3m', 'trigonal', 162, 167, (_H3, _H2, _INV)),
    ('6', 'hexagonal', 168, 173, (_H6,)), ('-6', 'hexagonal', 174, 174, (_neg(_H6),)),
    ('6/m', 'hexagonal', 175, 176, (_H6, _INV)), ('622', 'hexagonal', 177, 182, (_H6, _H2)),
    ('6mm', 'hexagonal', 183, 186, (_H6, _neg(_H2))), ('-6m2', 'hexagonal', 187, 190, (_neg(_H6), _H2)),
    ('6/mmm', 'hexagonal', 191, 194, (_H6, _H2, _INV)),
    ('23', 'cubic', 195, 199, (_C['2z'], _C['3d'])), ('m-3', 'cubic', 200, 206, (_C['2z'], _C['3d'], _INV)),
    ('432', 'cubic', 207, 214, (_C['4z'], _C['3d'])), ('-43m', 'cubic', 215, 220, (_C['-4z'], _C['3d'])),
    ('m-3m', 'cubic', 221, 230, (_C['4z'], _C['3d'], _INV)),
)
SCHOENFLIES = {  # the crystal classes in the notation of Schoenflies (ITA vol. A, table 3.2.3.2)
    '1': 'C1', '-1': 'Ci', '2': 'C2', 'm': 'Cs', '2/m': 'C2h', '222': 'D2', 'mm2': 'C2v', 'mmm': 'D2h', '4': 'C4',
    '-4': 'S4', '4/m': 'C4h', '422': 'D4', '4mm': 'C4v', '-42m': 'D2d', '4/mmm': 'D4h', '3': 'C3', '-3': 'C3i',
    '32': 'D3', '3m': 'C3v', '-3m': 'D3d', '6': 'C6', '-6': 'C3h', '6/m': 'C6h', '622': 'D6', '6mm': 'C6v',
    '-6m2': 'D3h', '6/mmm': 'D6h', '23': 'T', 'm-3': 'Th', '432': 'O', '-43m': 'Td', 'm-3m': 'Oh',
}
SYSTEMS = {'triclinic': 'триклинная', 'monoclinic': 'моноклинная', 'orthorhombic': 'ромбическая',
           'tetragonal': 'тетрагональная', 'trigonal': 'тригональная', 'hexagonal': 'гексагональная',
           'cubic': 'кубическая'}


def signature(rotations):
    counts = {}
    for w in rotations:
        k = kind(w)
        counts[k] = counts.get(k, 0) + 1
    return tuple(sorted(counts.items()))


_SIGNATURES = {signature(_closure(g)): (name, system, lo, hi) for name, system, lo, hi, g in POINT_GROUPS}


def point_group(rotations):
    """(Hermann-Mauguin symbol, crystal system, first and last space-group number) or None."""
    return _SIGNATURES.get(signature(set(rotations)))


# -- the whole crystal -----------------------------------------------------------------------------------
CENTRINGS = {
    frozenset(): 'P',
    frozenset({(0, Fraction(1, 2), Fraction(1, 2))}): 'A',
    frozenset({(Fraction(1, 2), 0, Fraction(1, 2))}): 'B',
    frozenset({(Fraction(1, 2), Fraction(1, 2), 0)}): 'C',
    frozenset({(Fraction(1, 2),) * 3}): 'I',
    frozenset({(0, Fraction(1, 2), Fraction(1, 2)), (Fraction(1, 2), 0, Fraction(1, 2)),
               (Fraction(1, 2), Fraction(1, 2), 0)}): 'F',
    frozenset({(Fraction(2, 3), Fraction(1, 3), Fraction(1, 3)), (Fraction(1, 3), Fraction(2, 3), Fraction(2, 3))}): 'R',
}


@dataclass(frozen=True)
class Symmetry:
    operations: tuple  # describe() of each operation, in the order of the file
    centring: str  # P, A, B, C, I, F, R or '?'
    point_group: str  # '' when the rotations form no crystallographic point group
    system: str  # Russian
    number: int  # from the file, 0 if absent
    numbers: tuple  # (first, last) of the point group
    formula: str
    z: object  # Fraction or int
    z_prime: object
    density: float  # g/cm3, 0 if unknown
    notes: tuple = field(default_factory=tuple)


def _key(op):
    rows, shifts = op
    return rows, tuple(_frac(x) for x in shifts)


def _compose(a, b):
    """a after b."""
    (ra, ta), (rb, tb) = a, b
    return _mul(ra, rb), tuple(_frac(x) for x in tuple(Fraction(_apply(ra, tb)[i]) + Fraction(ta[i]) for i in range(3)))


def _missing_products(ops, keys):
    """How many products a·b of the operations are not among them (the group closed: 0). N² products
    (36 864 for F m -3 m) were worked out in Fractions — 35 s for the 530 settings of the tests, a part of every
    file opened; with integer rotations (every setting of the tables) the shifts are taken as whole numbers of
    1/D (D — their common denominator) and the same products are found in integers modulo D, exactly the same set.
    A rotation with a fraction in it (a file of an odd setting) — the products in Fractions, as before."""
    if any(not isinstance(x, int) for rows, _ in ops for row in rows for x in row):
        return sum(1 for a in ops for b in ops if _compose(a, b) not in keys)
    from math import lcm

    den = 1
    for _, shifts in ops:
        for x in shifts:
            den = lcm(den, Fraction(x).denominator)
    whole = [(rows, tuple(int(Fraction(x) * den) % den for x in shifts)) for rows, shifts in ops]
    known = set(whole)
    missing = 0
    for ra, ta in whole:
        for rb, tb in whole:
            rows = _mul(ra, rb)
            shifts = tuple((ra[i][0] * tb[0] + ra[i][1] * tb[1] + ra[i][2] * tb[2] + ta[i]) % den for i in range(3))
            if (rows, shifts) not in known:
                missing += 1
    return missing


def _formula_text(counts):
    from azimuth.core import Atom, Molecule

    atoms = []
    for symbol, n in counts.items():
        atoms += [Atom(symbol, 0, 0, 0)] * int(n)
    return Molecule('', tuple(atoms)).formula


def cell_counts(crystal):
    """Element -> atoms in the cell (each site times its copies and its occupancy)."""
    from modules.compass.chemistry import crystal as cr

    counts = {}
    for site in crystal.sites:
        mine = []
        for op in crystal.operations:
            f = cr._wrap(cr._apply(op, (site.x, site.y, site.z)))
            if all(cr._separation(crystal.cell, f, g) > cr.MERGE for g in mine):
                mine.append(f)
        counts[site.symbol] = counts.get(site.symbol, 0.0) + len(mine) * site.occupancy
    return counts


def _parse_formula(text):
    import re

    found = {}
    for symbol, count in re.findall(r'([A-Z][a-z]?)\s*([0-9.]*)', text or ''):
        found[symbol] = found.get(symbol, 0.0) + (float(count) if count else 1.0)
    return found


def analyse(crystal):
    from modules.compass.chemistry.structure_tools import AVERAGE

    notes = []
    ops = [_key(op) for op in crystal.operations]
    keys = set(ops)
    missing = _missing_products(ops, keys)
    if missing:
        notes.append(tr('Операции файла не замкнуты: не хватает произведений — группа неполная.'))
    translations = set()
    for rows, t in ops:
        if rows == I3 and any(t):
            translations.add(tuple(t))
    centring = CENTRINGS.get(frozenset(translations), '?')
    found = point_group({rows for rows, _ in ops})
    name, system, lo, hi = found if found else ('', '', 0, 0)
    if not found:
        notes.append(tr('Повороты операций не образуют кристаллографическую точечную группу.'))
    number = int(getattr(crystal, 'number', 0) or 0)
    if number and found and not lo <= number <= hi:
        notes.append(tr('Номер группы в файле ({}) не подходит к точечной группе {} ({}–{}).').format(number, name, lo, hi))
    counts = {s: n for s, n in cell_counts(crystal).items() if n > 1e-6}
    given = _parse_formula(getattr(crystal, 'formula_sum', ''))
    z = None
    if given and set(given) == set(counts):
        ratios = [counts[s] / given[s] for s in given]
        if max(ratios) - min(ratios) < 0.02 * max(ratios):
            z = round(sum(ratios) / len(ratios), 3)
    if z is None and getattr(crystal, 'formula_z', 0):
        z = crystal.formula_z
    if z is None:
        z = _molecular_z(crystal, counts)  # a molecular crystal — Z counts its molecules
    if z is None:
        whole = [round(n) for n in counts.values()]
        if all(abs(n - w) < 1e-3 for n, w in zip(counts.values(), whole)) and whole:
            g = 0
            for w in whole:
                g = gcd(g, w)
            z = g or 1
        else:
            z = 1
    unit = {s: n / z for s, n in counts.items()}
    formula = _formula_text({s: round(n) for s, n in unit.items()}) if all(
        abs(n - round(n)) < 1e-3 for n in unit.values()) else ' '.join(f'{s}{n:g}' for s, n in sorted(unit.items()))
    mass = sum(AVERAGE.get(s, 0.0) * n for s, n in counts.items())
    density = mass / AVOGADRO / (crystal.cell.volume() * 1e-24) if mass else 0.0
    general = len(keys)
    z_prime = Fraction(z).limit_denominator(48) / general if general else 0
    return Symmetry(tuple(describe(op) for op in crystal.operations), centring, name,
                    SYSTEMS.get(system, ''), number, (lo, hi), formula, z, z_prime, density, tuple(notes))


# -- molecules across the faces of the cell ----------------------------------------------------------------
@dataclass(frozen=True)
class Packing:
    molecules: tuple  # each: ((symbol, (fx, fy, fz)), ...), unwrapped, centroid in [0, 1)^3
    frameworks: tuple  # each: (dimension 1-3, ((symbol, (fx, fy, fz)), ...)) as in the cell
    text: str


def _radius(symbol):
    from modules.compass.chemistry.coordination import radius

    try:
        return radius(symbol)
    except (ValueError, KeyError):
        return 0.8


def _rank(vectors):
    rows = [list(map(Fraction, v)) for v in vectors]
    rank = 0
    for col in range(3):
        p = next((r for r in range(rank, len(rows)) if rows[r][col] != 0), None)
        if p is None:
            continue
        rows[rank], rows[p] = rows[p], rows[rank]
        for r in range(len(rows)):
            if r != rank and rows[r][col] != 0:
                f = rows[r][col] / rows[rank][col]
                rows[r] = [rows[r][c] - f * rows[rank][c] for c in range(3)]
        rank += 1
    return rank


@dataclass(frozen=True)
class Walk:
    """The cell under periodic bonds (shared by molecules and crystal_contacts)."""
    atoms: tuple  # crystal.unit_cell: (symbol, fx, fy, fz, label)
    frac: object  # n x 3 array, in [0, 1)
    vectors: object  # 3 x 3 array, rows a, b, c (A)
    edges: tuple  # per atom: ((j, (sx, sy, sz)), ...): atom j of the cell shifted by s is bonded to it
    component: tuple  # per atom: the index of its component
    shift: tuple  # per atom: its cell shift in the component (a molecule: the unwrapped copy)
    periods: dict  # component -> dimension of its periodicity (0 for a molecule)
    move: dict  # component (a molecule) -> the lattice vector that puts its centroid into the cell


def walk(crystal, factor=None):
    import numpy as np

    from modules.compass.chemistry import crystal as cr

    if factor is None:
        from azimuth import defaults

        factor = defaults.get('bond_factor')
    atoms = cr.unit_cell(crystal)
    n = len(atoms)
    frac = np.array([a[1:4] for a in atoms], dtype=float).reshape(n, 3)
    vectors = np.array(crystal.cell.vectors(), dtype=float)
    radii = np.array([_radius(a[0]) if a[0] != 'X' else 0.0 for a in atoms])
    limit = factor * (radii[:, None] + radii[None, :])
    edges = [[] for _ in range(n)]
    cart = frac @ vectors
    for s in ((i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)):
        moved = cart + np.array(s, dtype=float) @ vectors
        d = np.linalg.norm(moved[None, :, :] - cart[:, None, :], axis=2)  # d[i, j]: atom i to image of j
        hit = (d <= limit) & (d > 0.1) & (radii[:, None] > 0) & (radii[None, :] > 0)
        for i, j in zip(*np.nonzero(hit)):
            edges[int(i)].append((int(j), s))
    shift_of = [None] * n
    component = [None] * n
    periods, move = {}, {}
    for start in range(n):
        if shift_of[start] is not None:
            continue
        shift_of[start], component[start] = (0, 0, 0), start
        members, found, stack = [start], [], [start]
        while stack:
            i = stack.pop()
            for j, s in edges[i]:
                want = tuple(shift_of[i][k] + s[k] for k in range(3))
                if shift_of[j] is None:
                    shift_of[j], component[j] = want, start
                    members.append(j)
                    stack.append(j)
                elif shift_of[j] != want:
                    found.append(tuple(want[k] - shift_of[j][k] for k in range(3)))
        periods[start] = _rank(found) if found else 0
        if not found:
            points = np.array([frac[i] + np.array(shift_of[i]) for i in members])
            move[start] = tuple(int(x) for x in np.floor(points.mean(axis=0) + 1e-6))
    return Walk(tuple(atoms), frac, vectors, tuple(tuple(e) for e in edges), tuple(component), tuple(shift_of),
                periods, move)


def _molecular_z(crystal, counts):
    """The molecules of the cell, when all of it is molecules (no chain, layer or
    framework) — Z is the greatest common divisor of the numbers of each kind (C6Cl6 × 2 → 2; a salt of two kinds of
    ions, 4 + 8 → 4), so that the formula unit is a whole molecule (or a whole set of ions); None otherwise."""
    from math import gcd

    try:
        w = walk(crystal)
    except (ValueError, IndexError, MemoryError):
        return None
    groups = {}
    for i, c in enumerate(w.component):
        groups.setdefault(c, []).append(i)
    if not groups or any(w.periods[c] for c in groups):
        return None
    kinds = {}
    for members in groups.values():
        key = _formula_text(_count(w.atoms[i][0] for i in members))
        kinds[key] = kinds.get(key, 0) + 1
    z = 0
    for n in kinds.values():
        z = gcd(z, n)
    total = sum(len(m) for m in groups.values())
    if not z or abs(total - sum(counts.values())) > 1e-3:
        return None
    return z


def molecules(crystal, factor=None):
    w = walk(crystal, factor)
    groups = {}
    for i, c in enumerate(w.component):
        groups.setdefault(c, []).append(i)
    found, frames = [], []
    for c, members in groups.items():
        if w.periods[c]:
            frames.append((w.periods[c], tuple((w.atoms[i][0], tuple(float(x) for x in w.frac[i])) for i in members)))
            continue
        m = w.move[c]
        found.append(tuple((w.atoms[i][0], tuple(float(w.frac[i][k] + w.shift[i][k] - m[k]) for k in range(3)))
                           for i in members))
    words = []
    if found:
        kinds = {}
        for m in found:
            f = _formula_text(_count(s for s, _ in m))
            kinds[f] = kinds.get(f, 0) + 1
        words.append(tr('Молекул в ячейке: {}').format(', '.join(f'{k} × {v}' if v > 1 else k for k, v in kinds.items())))
    names = {1: tr('цепь (1D)'), 2: tr('слой (2D)'), 3: tr('каркас (3D)')}
    for dim, part in frames:
        f = _formula_text(_count(s for s, _ in part))
        words.append(tr('Бесконечная структура — {}, в ячейке {}: показана как в ячейке').format(names[dim], f))
    return Packing(tuple(found), tuple(frames), '; '.join(words))


def _count(symbols):
    out = {}
    for s in symbols:
        out[s] = out.get(s, 0) + 1
    return out


def whole_molecules(crystal, n=(1, 1, 1), factor=None):
    """The molecules (and the infinite parts as in the cell) of n1 x n2 x n3 cells as one Molecule."""
    from azimuth.core import MAX_ATOMS, Atom, Molecule

    if len(n) != 3 or any(not isinstance(k, int) or not 1 <= k <= 10 for k in n):
        raise ValueError(tr('Число ячеек по каждой оси — от 1 до 10.'))
    packing = molecules(crystal, factor)
    parts = list(packing.molecules) + [part for _, part in packing.frameworks]
    total = sum(len(p) for p in parts) * n[0] * n[1] * n[2]
    if total > MAX_ATOMS:
        raise ValueError(tr('Получится {} атомов — больше {}. Уменьшите число ячеек.').format(total, MAX_ATOMS))
    atoms = []
    for i in range(n[0]):
        for j in range(n[1]):
            for k in range(n[2]):
                for part in parts:
                    for symbol, f in part:
                        atoms.append(Atom(symbol, *crystal.cell.cartesian((f[0] + i, f[1] + j, f[2] + k))))
    formula = _formula_text(_count(a.symbol for a in atoms[: sum(len(p) for p in parts)]))
    title = f'{crystal.title or "crystal"} {formula} {n[0]}x{n[1]}x{n[2]}'
    return Molecule(title, tuple(atoms), None), packing


# -- the symmetry elements inside the cell ------------------------------------------------------
ELEMENT_LIMIT = 400  # more than this many elements in one cell are not drawn (a cubic F group has thousands)


def _clip_line(x0, u):
    """The part of the line x0 + s u inside the cell [0, 1]^3 (fractional): (start, end) or None."""
    lo, hi = -1e18, 1e18
    for k in range(3):
        if u[k] == 0:
            if not -1e-9 <= x0[k] <= 1 + 1e-9:
                return None
            continue
        a, b = (0 - x0[k]) / u[k], (1 - x0[k]) / u[k]
        lo, hi = max(lo, min(a, b)), min(hi, max(a, b))
    if hi - lo < 1e-9:
        return None
    return tuple(x0[k] + lo * u[k] for k in range(3)), tuple(x0[k] + hi * u[k] for k in range(3))


CUBE_EDGES = tuple(
    (tuple(c), tuple(c[:k] + (1,) + c[k + 1:]))
    for c in ((i, j, m) for i in (0, 1) for j in (0, 1) for m in (0, 1))
    for k in range(3) if c[k] == 0
)


def _clip_plane(normal, value):
    """The polygon where the plane normal . x = value cuts the cell [0, 1]^3 (fractional), in order, or None."""
    from math import atan2

    points = []
    for a, b in CUBE_EDGES:
        fa = sum(normal[k] * a[k] for k in range(3)) - value
        fb = sum(normal[k] * b[k] for k in range(3)) - value
        if abs(fa) < 1e-9 and abs(fb) < 1e-9:
            points += [a, b]
        elif abs(fa) < 1e-9:
            points.append(a)
        elif abs(fb) < 1e-9:
            points.append(b)
        elif fa * fb < 0:
            s = fa / (fa - fb)
            points.append(tuple(a[k] + s * (b[k] - a[k]) for k in range(3)))
    unique = []
    for p in points:
        if all(max(abs(p[k] - q[k]) for k in range(3)) > 1e-7 for q in unique):
            unique.append(p)
    if len(unique) < 3:
        return None
    c = [sum(p[k] for p in unique) / len(unique) for k in range(3)]
    n = [float(x) for x in normal]
    # two directions in the plane to order the corners by angle
    helper = (1.0, 0.0, 0.0) if abs(n[0]) < 0.9 * max(abs(x) for x in n) else (0.0, 1.0, 0.0)
    e1 = [n[1] * helper[2] - n[2] * helper[1], n[2] * helper[0] - n[0] * helper[2], n[0] * helper[1] - n[1] * helper[0]]
    e2 = [n[1] * e1[2] - n[2] * e1[1], n[2] * e1[0] - n[0] * e1[2], n[0] * e1[1] - n[1] * e1[0]]
    key = lambda p: atan2(sum((p[k] - c[k]) * e2[k] for k in range(3)), sum((p[k] - c[k]) * e1[k] for k in range(3)))  # noqa: E731
    return tuple(sorted(unique, key=key))


def elements(crystal):
    """The symmetry elements inside one cell: [{'kind', 'symbol', 'frac': point | (start, end) | polygon}].
    Each operation is taken with the lattice translations t in {-1, 0, 1, 2}^3 (W x + w + t): they move the element
    (a 2_1 axis at x = 0 has a twin at x = 1/2); copies that coincide are one element."""
    found, seen = [], set()
    span = (-1, 0, 1, 2)  # fixed points t/2 reach the far faces of the cell (x = 1) too
    for rows, shifts in crystal.operations:
        for t in ((i, j, k) for i in span for j in span for k in span):
            op = (rows, tuple(Fraction(shifts[q]) + t[q] for q in range(3)))
            d = describe(op)
            if d['kind'] == '1' or d['point'] is None:
                continue
            x0 = tuple(float(x) for x in _raw_point(op, d))
            if d['kind'] in ('-1', '-3', '-4', '-6'):
                if not all(-1e-9 <= x <= 1 + 1e-9 for x in x0):
                    continue
                geometry, key = x0, ('p', tuple(round(x, 6) for x in x0))
            elif d['kind'] == 'm':
                n = d['axis']
                value = sum(n[k] * x0[k] for k in range(3))
                geometry = _clip_plane(n, value)
                if geometry is None:
                    continue
                key = ('m', n, round(value, 6))
            else:
                geometry = _clip_line(x0, d['axis'])
                if geometry is None:
                    continue
                key = ('l', d['axis'], tuple(tuple(round(x, 6) for x in end) for end in sorted(geometry)))
            key = (d['symbol'],) + key
            if key in seen:
                continue
            seen.add(key)
            found.append({'kind': d['kind'], 'symbol': d['symbol'], 'frac': geometry})
    return found


def _raw_point(op, d):
    """A fixed point of the reduced operation without wrapping it into the cell (describe wraps it)."""
    rows, shifts = op
    t = tuple(Fraction(x) for x in shifts)
    rest = tuple(t[i] - d['glide'][i] for i in range(3))
    return _solve(_add(rows, _neg(I3)), tuple(-x for x in rest))


# -- the packing coefficient --------------------------------------------------------------------
def packing_coefficient(crystal, grid=40):
    """The part of the cell inside the van der Waals spheres of the atoms (Bondi radii as in
    modules/spectrum/analysis/contacts.VDW): Kitaigorodsky's packing coefficient of a molecular crystal (about 0.65-0.77)
    — counted on a grid of grid^3 points at the centres of its cells; the spheres of the atoms of the 27 neighbouring
    cells reach in. The error of the grid is below 0.01 at 40 (simple cubic and face-centred packings of touching
    spheres: pi/6 and pi/(3 sqrt 2), tests/compass/test_crystal_symmetry.py)."""
    import numpy as np

    from modules.compass.chemistry import crystal as cr
    from modules.spectrum.analysis.contacts import VDW

    atoms = cr.unit_cell(crystal)
    if not atoms:
        return 0.0
    rows = np.array(crystal.cell.vectors(), dtype=float)
    frac = np.array([a[1:4] for a in atoms], dtype=float)
    radii = np.array([VDW.get(a[0], 1.8) for a in atoms])
    shifts = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)], dtype=float)
    centres = (frac[None, :, :] + shifts[:, None, :]).reshape(-1, 3) @ rows
    r2 = np.tile(radii, len(shifts)) ** 2
    lengths = np.linalg.norm(rows, axis=1)
    # only the spheres that can reach the cell
    f_all = (frac[None, :, :] + shifts[:, None, :]).reshape(-1, 3)
    reach = np.tile(radii, len(shifts))[:, None] / lengths[None, :]
    near = np.all((f_all > -reach - 1e-9) & (f_all < 1 + reach + 1e-9), axis=1)
    centres, r2 = centres[near], r2[near]
    axis = (np.arange(grid) + 0.5) / grid
    points = np.stack(np.meshgrid(axis, axis, axis, indexing='ij'), axis=-1).reshape(-1, 3) @ rows
    inside = 0
    rmax = float(np.sqrt(r2.max())) if len(r2) else 0.0
    for start in range(0, len(points), 4096):
        chunk = points[start:start + 4096]
        lo, hi = chunk.min(axis=0) - rmax, chunk.max(axis=0) + rmax  # only the spheres near this part of the grid
        keep = np.all((centres >= lo) & (centres <= hi), axis=1)
        if not keep.any():
            continue
        d2 = ((chunk[:, None, :] - centres[keep][None, :, :]) ** 2).sum(axis=2)
        inside += int(np.any(d2 < r2[keep][None, :], axis=1).sum())
    return inside / len(points)


# -- coordination polyhedra ---------------------------------------------------------------------
NONMETALS = {'H', 'He', 'B', 'C', 'N', 'O', 'F', 'Ne', 'Si', 'P', 'S', 'Cl', 'Ar', 'As', 'Se', 'Br', 'Kr', 'Te', 'I',
             'Xe', 'At', 'Rn', 'X'}


def is_metal(symbols):
    """A metal for the occupations of a calculation — every element a metal (Cu, an alloy). A compound
    with a nonmetal (CsCl, NaCl, an oxide, a molecular crystal) is an insulator: a salt was taken for a metal because
    of its metal element, and CP2K smeared the electrons of CsCl and blew its cell up by 28 % at the Γ point."""
    symbols = set(symbols)
    return bool(symbols) and not symbols & NONMETALS


def hull_faces(points, eps=1e-6):
    """The faces of the convex hull of 4-12 points (A): [polygon of points in order], each plane once; [] when the points
    lie in a plane. By trial of all triples: a plane through three points with all the others on one side is a face."""
    import numpy as np

    p = np.array(points, dtype=float)
    n = len(p)
    if n < 4:
        return []
    centre = p.mean(axis=0)
    planes = []
    for i in range(n):
        for j in range(i + 1, n):
            for k in range(j + 1, n):
                normal = np.cross(p[j] - p[i], p[k] - p[i])
                size = np.linalg.norm(normal)
                if size < eps:
                    continue
                normal /= size
                side = (p - p[i]) @ normal
                if np.all(side <= eps) or np.all(side >= -eps):
                    if np.dot(centre - p[i], normal) > 0:
                        normal = -normal
                    offset = float(np.dot(normal, p[i]))
                    if not any(np.allclose(normal, q, atol=1e-5) and abs(offset - d) < 1e-5 for q, d in planes):
                        planes.append((normal, offset))
    faces = []
    for normal, offset in planes:
        on = [m for m in range(n) if abs(float(np.dot(normal, p[m])) - offset) < 1e-5]
        if len(on) < 3:
            continue
        c = p[on].mean(axis=0)
        e1 = p[on[0]] - c
        e1 /= np.linalg.norm(e1)
        e2 = np.cross(normal, e1)
        on.sort(key=lambda m: float(np.arctan2(np.dot(p[m] - c, e2), np.dot(p[m] - c, e1))))
        faces.append([tuple(float(x) for x in p[m]) for m in on])
    volume = sum(abs(float(np.dot(np.array(f[0]) - centre, np.cross(np.array(f[a]) - centre, np.array(f[a + 1]) - centre))))
                 for f in faces for a in range(1, len(f) - 1)) / 6
    return faces if volume > 1e-6 else []


SHELL = 1.12  # the first coordination shell: up to 1.12 x the nearest distance (CsCl: 8 Cl at a sqrt3/2, the 6 Cs at a are 1.155 x)


def polyhedra(molecule, centres=None, shell=SHELL):
    """The coordination polyhedra of the model: [(centre atom index, symbol, faces)] for every atom of centres (default:
    the metals) whose first shell — the atoms up to shell x its nearest distance (ionic crystals have no drawn bonds:
    Na–Cl 2.82 A is longer than the bonds Compass draws) — has 4 to 12 atoms and a solid hull; of each element only the
    atoms with the full shell (the most neighbours of that element in the model) — not the cut ones on the edges."""
    import numpy as np

    if not molecule.atoms:
        return []
    xyz = np.array([a.position for a in molecule.atoms], dtype=float)
    shells = []
    for k, atom in enumerate(molecule.atoms):
        wanted = atom.symbol not in NONMETALS if centres is None else atom.symbol in centres
        if not wanted:
            continue
        d = np.linalg.norm(xyz - xyz[k], axis=1)
        d[k] = np.inf
        nearest = float(d.min()) if len(d) > 1 else np.inf
        if not np.isfinite(nearest) or nearest < 0.5:
            continue
        shell_atoms = [int(m) for m in np.nonzero(d <= shell * nearest)[0]]
        if 4 <= len(shell_atoms) <= 12:
            shells.append((k, atom.symbol, shell_atoms))
    # an atom on the edge of the block misses neighbours: only the full shells (the largest of each element) are drawn
    full = {}
    for _, symbol, members in shells:
        full[symbol] = max(full.get(symbol, 0), len(members))
    found = []
    for k, symbol, members in shells:
        if len(members) == full[symbol]:
            faces = hull_faces([tuple(xyz[m]) for m in members])
            if faces:
                found.append((k, symbol, faces))
    return found


# 2026-11-13 (the card of Sextant showed «ClCs₈» for CsCl — the atoms of the block on the screen): the formula of the
# crystal itself — its cell divided by the greatest common divisor; Hill order with carbon (C, H, then by alphabet),
# else by Pauling electronegativity, the electropositive first (CsCl, NaCl, SiO₂, Fe₂O₃), as chemists write salts
PAULING = {
    'H': 2.20, 'Li': 0.98, 'Be': 1.57, 'B': 2.04, 'C': 2.55, 'N': 3.04, 'O': 3.44, 'F': 3.98, 'Na': 0.93, 'Mg': 1.31,
    'Al': 1.61, 'Si': 1.90, 'P': 2.19, 'S': 2.58, 'Cl': 3.16, 'K': 0.82, 'Ca': 1.00, 'Sc': 1.36, 'Ti': 1.54, 'V': 1.63,
    'Cr': 1.66, 'Mn': 1.55, 'Fe': 1.83, 'Co': 1.88, 'Ni': 1.91, 'Cu': 1.90, 'Zn': 1.65, 'Ga': 1.81, 'Ge': 2.01,
    'As': 2.18, 'Se': 2.55, 'Br': 2.96, 'Kr': 3.00, 'Rb': 0.82, 'Sr': 0.95, 'Y': 1.22, 'Zr': 1.33, 'Nb': 1.6, 'Mo': 2.16,
    'Tc': 1.9, 'Ru': 2.2, 'Rh': 2.28, 'Pd': 2.20, 'Ag': 1.93, 'Cd': 1.69, 'In': 1.78, 'Sn': 1.96, 'Sb': 2.05, 'Te': 2.1,
    'I': 2.66, 'Xe': 2.6, 'Cs': 0.79, 'Ba': 0.89, 'La': 1.10, 'Ce': 1.12, 'Pr': 1.13, 'Nd': 1.14, 'Sm': 1.17, 'Gd': 1.20,
    'Hf': 1.3, 'Ta': 1.5, 'W': 2.36, 'Re': 1.9, 'Os': 2.2, 'Ir': 2.20, 'Pt': 2.28, 'Au': 2.54, 'Hg': 2.00, 'Tl': 1.62,
    'Pb': 2.33, 'Bi': 2.02, 'Po': 2.0, 'At': 2.2, 'U': 1.38}


def empirical_formula(crystal):
    """The formula of the crystal (CsCl, not the atoms of a block): its cell reduced; '' without atoms."""
    from math import gcd

    counts = {s: c for s, c in cell_counts(crystal).items() if s != 'X' and c > 1e-6}
    if not counts:
        return ''
    whole = all(abs(c - round(c)) < 1e-3 for c in counts.values())
    if whole:
        # a crystal of molecules — its molecule (C6Cl6)
        molecular = _molecular_z(crystal, counts) if not getattr(crystal, 'formula_sum', '') else None
        divisor = molecular or 0
        if not divisor:
            for c in counts.values():
                divisor = gcd(divisor, int(round(c)))
        counts = {s: round(c) // max(1, divisor) for s, c in counts.items()}
    if 'C' in counts:
        order = ['C'] + (['H'] if 'H' in counts else []) + sorted(s for s in counts if s not in ('C', 'H'))
    else:
        order = sorted(counts, key=lambda s: (PAULING.get(s, 2.5), s))

    def number(c):
        if whole:
            return '' if c == 1 else str(int(c))
        return f'{c:.3g}'

    return ''.join(s + number(counts[s]) for s in order)

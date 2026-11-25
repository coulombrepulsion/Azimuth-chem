"""Crystals for Compass: CIF files, the unit cell, supercells.

§1 THEORY
    A crystal is a lattice of unit cells with edges a, b, c and angles alpha (b^c), beta (a^c), gamma
    (a^b), and the atoms of the asymmetric unit, which the symmetry operations of the space group
    (x, y, z) -> R (x, y, z) + t (fractional coordinates) copy over the cell. Cartesian coordinates
    r = f1 a + f2 b + f3 c with the usual orientation: a along x, b in the xy plane,
        a = (a, 0, 0), b = (b cos g, b sin g, 0),
        c = (c cos b, c (cos a - cos b cos g) / sin g, c sqrt(1 - cos^2 b - ((cos a - cos b cos g) / sin g)^2)),
    the cell volume V = abc sqrt(1 - cos^2 a - cos^2 b - cos^2 g + 2 cos a cos b cos g) (the standard
    formulas; the tests check them against the dot products and the determinant of the vectors).
§2 ALGORITHM
    parse_cif(text): the first data block; tags and values (quoted '...' and "...", ;-delimited text
    fields, # comments), loops; numbers with a standard uncertainty in parentheses (1.234(5)) give the
    value. Cell: _cell_length_a/b/c, _cell_angle_alpha/beta/gamma (90 if missing). Atoms: the loop with
    _atom_site_fract_x/y/z; the element from _atom_site_type_symbol, else from _atom_site_label (the
    leading letters, matched to the periodic table, two letters first); occupancy from
    _atom_site_occupancy (1 if missing). Operations: _space_group_symop_operation_xyz or
    _symmetry_equiv_pos_as_xyz; if none, those of the group named by the Hall symbol, the Hermann–Mauguin symbol or
    the number (space_groups.py, 0.118.0; said in the notes); the identity if none of these (P1, said so).
    operation(text) parses 'x', '-y', '1/2+z', 'x-y', '0.25-x' ... into R (integers) and t (fractions).
    unit_cell(crystal): every operation applied to every site, fractional coordinates wrapped into [0, 1);
    copies closer than MERGE (A, minimum image) to an earlier atom are the same atom (a special position).
    build(crystal, n=(1, 1, 1), faces=False): the cell content translated by i, j, k (0 <= i < n1, ...);
    with faces also the atoms on the far faces, edges and corners of the block (fractional coordinate
    within FACE of 0 is repeated at n); refused beyond MAX_ATOMS atoms.
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py (opening a CIF, the «Кристалл» window, the cell in the viewer).
§4 SPECIFICATION
    Cell(a, b, c, alpha, beta, gamma): vectors() -> 3 rows (A), volume(); Site(label, symbol, x, y, z,
    occupancy); Crystal(title, cell, sites, operations, space_group, notes); parse_cif(text) -> Crystal;
    operation(text) -> (R, t); unit_cell(crystal) -> [(symbol, fx, fy, fz, label)]; build(...) ->
    Molecule (title: formula of the cell, the repetitions); cell_edges(cell, n) -> 12 segments (A).
    ValueError for every refused input.
§5 PROCEDURES - below.
§6 NOTES
    Partial occupancies are kept as atoms (disorder is shown as all its sites; the window says how many
    sites are partial). Bonds are found by distance as for other structures. Only the first data block
    is read. Hydrogen positions are those of the file (often missing in X-ray structures).
§7 TESTS
    tests/compass/test_crystal.py.
§8' ROBUSTNESS / ERRORS
    Cell lengths 0.1-1000 A, angles 1-179 deg, a valid metric (the root above real and positive);
    coordinates are refused if not finite. MERGE = 0.05 A: printed CIF coordinates have 4-5 decimals
    (1e-4 of a 20 A cell = 2e-3 A), so copies of one special position fall far within it, and distinct
    atoms are never that close.
"""

from dataclasses import dataclass, field
from fractions import Fraction
from functools import lru_cache
from math import cos, isfinite, radians, sin, sqrt
import re

from azimuth.core import SYMBOLS, Atom, Molecule
from azimuth.i18n import tr

MERGE = 0.05
FACE = 1e-4
from azimuth.core import MAX_ATOMS  # the atoms of one structure (was 500 here)


@lru_cache(maxsize=1024)
def _cell_vectors(a, b, c, alpha, beta, gamma):
    ca, cb, cg = (cos(radians(x)) for x in (alpha, beta, gamma))
    sg = sin(radians(gamma))
    cy = (ca - cb * cg) / sg
    cz = sqrt(max(0.0, 1 - cb * cb - cy * cy))
    return (
        (a, 0.0, 0.0),
        (b * cg, b * sg, 0.0),
        (c * cb, c * cy, c * cz),
    )


@dataclass(frozen=True)
class Cell:
    a: float
    b: float
    c: float
    alpha: float = 90.0
    beta: float = 90.0
    gamma: float = 90.0

    def validate(self):
        for v in (self.a, self.b, self.c):
            if not isfinite(v) or not 0.1 <= v <= 1000:
                raise ValueError(tr('Длины ячейки — от 0,1 до 1000 Å.'))
        for v in (self.alpha, self.beta, self.gamma):
            if not isfinite(v) or not 1 <= v <= 179:
                raise ValueError(tr('Углы ячейки — от 1 до 179°.'))
        ca, cb, cg = (cos(radians(x)) for x in (self.alpha, self.beta, self.gamma))
        if 1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg <= 1e-10:
            raise ValueError(tr('Углы ячейки несовместимы (объём ячейки не положителен).'))
        return self

    def vectors(self):
        # the cell is frozen — its vectors are worked out once
        return _cell_vectors(self.a, self.b, self.c, self.alpha, self.beta, self.gamma)

    def volume(self):
        ca, cb, cg = (cos(radians(x)) for x in (self.alpha, self.beta, self.gamma))
        return self.a * self.b * self.c * sqrt(1 - ca * ca - cb * cb - cg * cg + 2 * ca * cb * cg)

    def cartesian(self, f):
        v = self.vectors()
        return tuple(f[0] * v[0][k] + f[1] * v[1][k] + f[2] * v[2][k] for k in range(3))


@dataclass(frozen=True)
class Site:
    label: str
    symbol: str
    x: float
    y: float
    z: float
    occupancy: float = 1.0
    disorder: str = ''  # _atom_site_disorder_group ('' for none)
    u: tuple = ()  # (U11, U22, U33, U12, U13, U23), A^2, of _atom_site_aniso_U_* (or B/8pi^2); () if none
    u_iso: float = 0.0  # _atom_site_U_iso_or_equiv (or B_iso/8pi^2), A^2; 0 if none


@dataclass(frozen=True)
class Crystal:
    title: str
    cell: Cell
    sites: tuple
    operations: tuple
    space_group: str = ''
    notes: tuple = field(default_factory=tuple)
    number: int = 0  # _space_group_IT_number (0 if absent)
    formula_sum: str = ''  # _chemical_formula_sum
    formula_z: float = 0  # _cell_formula_units_Z (0 if absent)


# -- CIF syntax ----------------------------------------------------------------------------------------
def _tokens(text):
    """Tokens of a CIF text: tags, values, loop_, data_; text fields as one value."""
    out = []
    lines = text.replace('\r\n', '\n').replace('\r', '\n').split('\n')
    k = 0
    while k < len(lines):
        line = lines[k]
        if line.startswith(';'):
            block = [line[1:]]
            k += 1
            while k < len(lines) and not lines[k].startswith(';'):
                block.append(lines[k])
                k += 1
            out.append(('value', '\n'.join(block).strip()))
            k += 1
            continue
        for m in re.finditer(r"""'([^']*)'(?=\s|$)|"([^"]*)"(?=\s|$)|(#.*$)|(\S+)""", line):
            if m.group(3) is not None:
                break
            if m.group(1) is not None or m.group(2) is not None:
                out.append(('value', m.group(1) if m.group(1) is not None else m.group(2)))
                continue
            word = m.group(4)
            low = word.lower()
            if low.startswith('data_'):
                out.append(('data', word[5:]))
            elif low == 'loop_':
                out.append(('loop', ''))
            elif word.startswith('_'):
                out.append(('tag', low))
            else:
                out.append(('value', word))
        k += 1
    return out


def _blocks(text):
    """The first data block: (title, {tag: value}, [ {tag: [values]} for each loop ])."""
    tokens = _tokens(text)
    title, items, loops = '', {}, []
    i = 0
    started = False
    while i < len(tokens):
        kind, value = tokens[i]
        if kind == 'data':
            if started:
                break
            started, title = True, value
            i += 1
        elif kind == 'loop':
            i += 1
            tags = []
            while i < len(tokens) and tokens[i][0] == 'tag':
                tags.append(tokens[i][1])
                i += 1
            values = []
            while i < len(tokens) and tokens[i][0] == 'value':
                values.append(tokens[i][1])
                i += 1
            if tags:
                if len(values) % len(tags):
                    raise ValueError(tr('CIF: в цикле число значений не кратно числу полей.'))
                loops.append({t: values[j :: len(tags)] for j, t in enumerate(tags)})
        elif kind == 'tag':
            if i + 1 < len(tokens) and tokens[i + 1][0] == 'value':
                items[value] = tokens[i + 1][1]
                i += 2
            else:
                i += 1
        else:
            i += 1
    if not started:
        raise ValueError(tr('Это не файл CIF: нет блока data_.'))
    return title, items, loops


def number(text):
    """A CIF number: '1.234(5)' -> 1.234; '.' and '?' are missing values (None)."""
    t = str(text).strip()
    if t in ('.', '?', ''):
        return None
    t = re.sub(r'\(\d+\)$', '', t)
    try:
        value = float(t)
    except ValueError as exc:
        raise ValueError(tr('CIF: не число: ') + str(text)) from exc
    if not isfinite(value):
        raise ValueError(tr('CIF: не число: ') + str(text))
    return value


def element(label, type_symbol=None):
    """The element of an atom site: from the type symbol ('O2-', 'Fe3+'), else from the label ('C12a')."""
    for source in (type_symbol, label):
        if not source or source in ('.', '?'):
            continue
        m = re.match(r'([A-Za-z]{1,2})', source)
        if not m:
            continue
        letters = m.group(1)
        for candidate in (letters[:2], letters[:1]):
            s = candidate[0].upper() + candidate[1:].lower()
            if s in SYMBOLS:
                return s
    raise ValueError(tr('CIF: не удалось определить элемент атома ') + str(label))


def operation(text):
    """'x, -y+1/2, z' -> (R rows of ints, t of Fractions)."""
    parts = [p.strip().lower().replace(' ', '') for p in str(text).split(',')]
    if len(parts) != 3:
        raise ValueError(tr('CIF: неверная операция симметрии: ') + str(text))
    rows, shifts = [], []
    for part in parts:
        row, shift = [0, 0, 0], Fraction(0)
        for sign, term in re.findall(r'([+-]?)([^+-]+)', part):
            s = -1 if sign == '-' else 1
            if term in ('x', 'y', 'z'):
                row['xyz'.index(term)] += s
                continue
            m = re.fullmatch(r'(\d+(?:\.\d+)?)(?:/(\d+))?\*?([xyz])?', term)
            if not m:
                raise ValueError(tr('CIF: неверная операция симметрии: ') + str(text))
            value = Fraction(m.group(1)) / (int(m.group(2)) if m.group(2) else 1)
            if m.group(3):
                if value != int(value):
                    raise ValueError(tr('CIF: неверная операция симметрии: ') + str(text))
                row['xyz'.index(m.group(3))] += s * int(value)
            else:
                shift += s * value
        rows.append(tuple(row))
        shifts.append(shift)
    if not any(rows[0]) or not any(rows[1]) or not any(rows[2]):
        raise ValueError(tr('CIF: неверная операция симметрии: ') + str(text))
    return tuple(rows), tuple(shifts)


def parse_cif(text):
    title, items, loops = _blocks(text)

    def get(tag, default=None):
        value = items.get(tag)
        if value is None:
            return default
        v = number(value)
        return default if v is None else v

    a, b, c = (get(f'_cell_length_{x}') for x in 'abc')
    if None in (a, b, c):
        raise ValueError(tr('CIF: нет длин ячейки (_cell_length_a, b, c).'))
    cell = Cell(a, b, c, get('_cell_angle_alpha', 90.0), get('_cell_angle_beta', 90.0), get('_cell_angle_gamma', 90.0)).validate()
    notes = []
    atoms = next((lp for lp in loops if '_atom_site_fract_x' in lp), None)
    if atoms is None:
        raise ValueError(tr('CIF: нет координат атомов (_atom_site_fract_x, y, z).'))
    labels = atoms.get('_atom_site_label', [''] * len(atoms['_atom_site_fract_x']))
    types = atoms.get('_atom_site_type_symbol', [None] * len(labels))
    occupancies = atoms.get('_atom_site_occupancy', ['1'] * len(labels))
    groups = atoms.get('_atom_site_disorder_group', ['.'] * len(labels))
    from math import pi

    isos = atoms.get('_atom_site_u_iso_or_equiv') or [None] * len(labels)
    b_isos = atoms.get('_atom_site_b_iso_or_equiv') or [None] * len(labels)
    aniso = {}  # label -> the six U_ij
    loop = next((lp for lp in loops if '_atom_site_aniso_label' in lp), None)
    if loop is not None:
        names = ('11', '22', '33', '12', '13', '23')
        kind = 'u' if '_atom_site_aniso_u_11' in loop else ('b' if '_atom_site_aniso_b_11' in loop else None)
        if kind:
            for k, label in enumerate(loop['_atom_site_aniso_label']):
                values = [number(loop.get(f'_atom_site_aniso_{kind}_{n}', [None] * (k + 1))[k] or '') for n in names]
                if None not in values:
                    aniso[label] = tuple(v / (8 * pi * pi) if kind == 'b' else v for v in values)
    sites = []
    for k, label in enumerate(labels):
        xyz = [number(atoms[f'_atom_site_fract_{w}'][k]) for w in 'xyz']
        if None in xyz:
            raise ValueError(tr('CIF: у атома нет координат: ') + label)
        occ = number(occupancies[k])
        group = str(groups[k]).strip()
        u_iso = number(isos[k] or '') if isos[k] is not None else None
        if u_iso is None and b_isos[k] is not None:
            b = number(b_isos[k] or '')
            u_iso = b / (8 * pi * pi) if b is not None else None
        sites.append(Site(label, element(label, types[k]), *xyz, 1.0 if occ is None else occ,
                          '' if group in ('.', '?') else group, aniso.get(label, ()), u_iso or 0.0))
    if not sites:
        raise ValueError(tr('CIF: нет атомов.'))
    ops_loop = next(
        (lp for lp in loops if '_space_group_symop_operation_xyz' in lp or '_symmetry_equiv_pos_as_xyz' in lp), None
    )
    texts = []
    if ops_loop is not None:
        texts = ops_loop.get('_space_group_symop_operation_xyz') or ops_loop.get('_symmetry_equiv_pos_as_xyz')
    else:
        single = items.get('_space_group_symop_operation_xyz') or items.get('_symmetry_equiv_pos_as_xyz')
        texts = [single] if single else []
    group = items.get('_space_group_name_h-m_alt') or items.get('_symmetry_space_group_name_h-m') or ''
    it_number = get('_space_group_it_number') or get('_symmetry_int_tables_number') or 0
    if not texts:
        # the operations of the group named by the symbol (Hall, then Hermann–Mauguin) or the number
        from modules.compass.chemistry import space_groups

        hall = items.get('_space_group_name_hall') or items.get('_symmetry_space_group_name_hall') or ''
        number_only = int(it_number) if it_number and float(it_number).is_integer() else 0
        entry = space_groups.find(str(group), str(hall), number_only)
        if entry is not None:
            texts = list(space_groups.operations(entry))
            named = str(hall).strip() or str(group).strip()
            if named:
                notes.append(tr('В файле нет операций симметрии: взяты операции группы {} по символу «{}».').format(
                    space_groups.describe(entry), named))
            else:
                notes.append(tr('В файле нет операций симметрии: взяты операции группы {} по её номеру.').format(
                    space_groups.describe(entry)))
            if not str(group).strip():
                group = entry['full'].replace('_', '')
    if not texts:
        texts = ['x, y, z']
        notes.append(tr('В файле нет операций симметрии: считается, что все атомы ячейки перечислены (P1).'))
    operations = tuple(operation(t) for t in texts)
    partial = sum(1 for s in sites if s.occupancy < 0.999)
    if partial:
        notes.append(tr(f'Неполная заселённость у {partial} позиций: показаны все позиции.'))
    z = get('_cell_formula_units_z') or 0
    formula_sum = str(items.get('_chemical_formula_sum') or '').strip()
    return Crystal(title, cell, tuple(sites), operations, str(group).strip(), tuple(notes),
                   int(it_number) if it_number and float(it_number).is_integer() else 0, formula_sum, float(z))


# -- the cell and supercells ---------------------------------------------------------------------------
def _apply(op, f):
    rows, shifts = op
    return tuple(sum(rows[i][j] * f[j] for j in range(3)) + float(shifts[i]) for i in range(3))


def _wrap(f):
    out = []
    for v in f:
        w = v - int(v // 1)
        if w >= 1.0 - 1e-9:
            w = 0.0
        out.append(0.0 if abs(w) < 1e-12 else w)
    return tuple(out)


def _separation(cell, f, g):
    """The shortest Cartesian distance between fractional points f and g of the lattice (minimum image)."""
    d = [f[k] - g[k] for k in range(3)]
    d = [x - round(x) for x in d]
    best = None
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                r = cell.cartesian((d[0] + i, d[1] + j, d[2] + k))
                s = sqrt(sum(x * x for x in r))
                best = s if best is None or s < best else best
    return best


def disorder_groups(crystal):
    """The disorder groups of the sites, sorted ('1', '2' …; a negative group — a disorder about a special
    position — counts as its absolute value)."""
    found = {s.disorder.lstrip('-') for s in crystal.sites if s.disorder}
    return tuple(sorted(found, key=lambda g: (len(g), g)))


def main_part(crystal, keep=None):
    """The crystal with the sites of one disorder group only (keep; by default the first one) and the
    ordered sites; a crystal without disorder groups is returned as it is."""
    groups = disorder_groups(crystal)
    told = tr('Разупорядочение: показана часть {} из {}.').split('{}')[0]
    if not groups or (len(groups) == 1 and any(n.startswith(told) for n in crystal.notes)):
        return crystal  # nothing to choose, or the part was chosen already
    keep = keep or groups[0]
    sites = tuple(s for s in crystal.sites if not s.disorder or s.disorder.lstrip('-') == keep)
    from dataclasses import replace

    note = tr('Разупорядочение: показана часть {} из {}.').format(keep, ', '.join(groups))
    notes = tuple(crystal.notes) + (() if note in crystal.notes else (note,))
    return replace(crystal, sites=sites, notes=notes)


def unit_cell(crystal):
    """All atoms of one cell: [(symbol, fx, fy, fz, label)], fractional coordinates in [0, 1)."""
    found = []
    for site in crystal.sites:
        mine = []
        for op in crystal.operations:
            f = _wrap(_apply(op, (site.x, site.y, site.z)))
            if all(_separation(crystal.cell, f, g) > MERGE for g in mine):
                mine.append(f)
        for f in mine:
            clash = next((x for x in found if _separation(crystal.cell, f, x[1:4]) <= MERGE), None)
            if clash is not None and clash[0] != site.symbol:
                raise ValueError(tr('CIF: разные атомы в одной точке ячейки: ') + clash[4] + ', ' + site.label)
            if clash is None:
                found.append((site.symbol, *f, site.label))
    return found


def model_sites(crystal, molecule):
    """The site of the file each atom of the model is a copy of — [(label, fractional position)] per atom,
    label None for an atom added by hand (no atom of the cell of its element within MERGE, the minimum image). The
    model is Cartesian, the cell at the origin. For block_crystal and for the table of the independent atoms of the
    «Координаты» tab (a row chosen there selects its copies on the model)."""
    import numpy as np

    rows = np.array(crystal.cell.vectors(), dtype=float)
    inverse = np.linalg.inv(rows)
    cell_atoms = unit_cell(crystal)
    known = np.array([a[1:4] for a in cell_atoms], dtype=float).reshape(-1, 3)
    out = []
    for atom in molecule.atoms:
        f = np.array(atom.position, dtype=float) @ inverse
        label = None
        if len(known):
            d = known - (f - np.floor(f))
            d -= np.round(d)
            dist = np.linalg.norm(d @ rows, axis=1)
            best = int(np.argmin(dist))
            if dist[best] <= MERGE and cell_atoms[best][0] == atom.symbol:
                label = cell_atoms[best][4] or None
        out.append((label, f))
    return out


def block_crystal(crystal, molecule):
    """The atoms of the model (a block of cells, whole molecules, a slab — Cartesian, the cell at the origin) as a
    crystal of space group P 1 in the same cell: fractional coordinates as they are (2.25 in the third cell), the label
    and the occupancy of the site of the file each atom is a copy of (model_sites), else the symbol and the number of
    the atom (an atom added by hand). Labels repeated by the copies get a suffix: C1, C1_2, C1_3… — for the «Координаты»
    tab of «Компас · Кристалл» and for saving the block as a CIF."""
    sites = {s.label: s for s in crystal.sites}
    seen = {}
    out = []
    for k, (atom, (found, f)) in enumerate(zip(molecule.atoms, model_sites(crystal, molecule))):
        label = found or f'{atom.symbol}{k + 1}'
        site = sites.get(found) if found else None
        occupancy = site.occupancy if site is not None else 1.0
        seen[label] = seen.get(label, 0) + 1
        name = label if seen[label] == 1 else f'{label}_{seen[label]}'
        out.append(Site(name, atom.symbol, *(float(round(x, 6)) + 0.0 for x in f), occupancy))
    return Crystal(f'{crystal.title or "crystal"} block', crystal.cell, tuple(out), (operation('x, y, z'),), 'P 1', (), 1)


def centring_vectors(crystal):
    """The pure translations of the operations (identity rotation, translation not a lattice vector), as
    fractions in [0, 1) — those of a centred lattice (½ ½ 0 … of F, ½ ½ ½ of I, ⅔ ⅓ ⅓ … of R on hexagonal axes)."""
    identity = ((1, 0, 0), (0, 1, 0), (0, 0, 1))
    found = set()
    for rows, t in crystal.operations:
        if tuple(tuple(r) for r in rows) == identity:
            v = tuple(Fraction(x) % 1 for x in t)
            if any(v):
                found.add(v)
    return sorted(found)


def supercell(crystal, n):
    """The crystal in a supercell n1 × n2 × n3 of its cell (group P 1): the edges a·n1, b·n2, c·n3, the same
    angles, the atoms of the cell repeated — for a calculation of Quantum ESPRESSO (a defect, a magnetic order, a
    larger cell); n = (1, 1, 1) gives the crystal itself."""
    n = tuple(int(k) for k in n)
    if len(n) != 3 or any(k < 1 or k > 10 for k in n):
        raise ValueError(tr('Число ячеек по каждой оси — от 1 до 10.'))
    if n == (1, 1, 1):
        return crystal
    c = crystal.cell
    cell = Cell(c.a * n[0], c.b * n[1], c.c * n[2], c.alpha, c.beta, c.gamma)
    sites = []
    for symbol, fx, fy, fz, label in unit_cell(crystal):
        for i in range(n[0]):
            for j in range(n[1]):
                for k in range(n[2]):
                    sites.append(Site(label, symbol, (fx + i) / n[0], (fy + j) / n[1], (fz + k) / n[2]))
    total = n[0] * n[1] * n[2]
    return Crystal(f'{crystal.title or "crystal"} {n[0]}×{n[1]}×{n[2]}', cell, tuple(sites), (operation('x, y, z'),), 'P 1',
                   (), 1, crystal.formula_sum, crystal.formula_z * total if crystal.formula_z else 0)


def primitive_basis(crystal):
    """The rows of the primitive cell of primitive(crystal) in fractions of the cell of the crystal (a 3 × 3
    numpy array), or None when the lattice is not centred — for the k-points of a band path (qe_paths)."""
    return _primitive_basis(crystal)[0]


def _primitive_basis(crystal):
    import numpy as np
    from itertools import combinations

    centres = centring_vectors(crystal)
    if not centres:
        return None, 1
    m = len(centres) + 1
    rows = np.array(crystal.cell.vectors(), dtype=float)
    candidates = []
    for t in [(0, 0, 0)] + [tuple(float(x) for x in c) for c in centres]:
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for k in (-1, 0, 1):
                    f = np.array(t) + np.array((i, j, k), dtype=float)
                    if np.linalg.norm(f) > 1e-9:
                        candidates.append(f)
    candidates.sort(key=lambda f: (round(float(np.linalg.norm(f @ rows)), 6), tuple(-f)))
    valid = []
    for trio in combinations(range(min(len(candidates), 40)), 3):
        p = np.array([candidates[n] for n in trio])  # rows: the new vectors in fractions of the old cell
        if abs(np.linalg.det(p) - 1.0 / m) < 1e-6:  # right-handed (the opposite vectors are candidates too)
            valid.append(p)
    if not valid:
        return None, m
    shortest = min(sum(float(np.linalg.norm(v @ rows)) for v in p) for p in valid)
    valid = [p for p in valid if sum(float(np.linalg.norm(v @ rows)) for v in p) < shortest + 1e-6]

    def kind(p):  # as a Niggli cell: all angles acute first, then all not acute (the 60° of fcc, the 109.47° of bcc)
        v = p @ rows
        dots = [float(v[0] @ v[1]), float(v[0] @ v[2]), float(v[1] @ v[2])]
        return 0 if all(d > 1e-9 for d in dots) else 1 if all(d <= 1e-9 for d in dots) else 2

    return min(valid, key=kind).copy(), m


def primitive(crystal):
    """The crystal in a primitive cell when its lattice is centred (else the crystal itself): the three shortest lattice
    vectors (of the centring vectors and the cell edges, ±1 cell) that span a cell 1/m of the volume (m — the number of
    lattice points in the cell: 4 for F, 2 for I, A, B, C, 3 for R), among them those with all angles acute, else all
    not acute (as the reduced cell of Niggli: 60° for fcc, 109.47° for bcc), right-handed; the atoms of the cell taken
    into it (wrapped, the copies merged, as unit_cell). Group P 1, the operations of the primitive cell not kept — for a
    calculation (Quantum ESPRESSO: 4 times fewer atoms for rock salt and silicon)."""
    import numpy as np

    basis, m = _primitive_basis(crystal)
    if basis is None:
        return crystal
    rows = np.array(crystal.cell.vectors(), dtype=float)
    vectors = basis @ rows
    lengths = [float(np.linalg.norm(v)) for v in vectors]

    def angle(u, v):
        return float(np.degrees(np.arccos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)), -1.0, 1.0))))

    cell = Cell(*lengths, angle(vectors[1], vectors[2]), angle(vectors[0], vectors[2]), angle(vectors[0], vectors[1]))
    inverse = np.linalg.inv(basis)
    sites = []
    labels = {s.label: s for s in crystal.sites}
    placed = []
    for symbol, fx, fy, fz, label in unit_cell(crystal):
        f = _wrap(tuple(float(x) for x in np.array((fx, fy, fz)) @ inverse))
        if any(_separation(cell, f, g) <= MERGE for g in placed):
            continue
        placed.append(f)
        site = labels.get(label)
        sites.append(Site(label, symbol, *f, site.occupancy if site else 1.0, site.disorder if site else '',
                          (), site.u_iso if site else 0.0))
    return Crystal(f'{crystal.title or "crystal"} primitive', cell, tuple(sites), (operation('x, y, z'),), 'P 1',
                   (), 1, crystal.formula_sum, crystal.formula_z / m if crystal.formula_z else 0)


def build(crystal, n=(1, 1, 1), faces=False):
    """The block of n1 x n2 x n3 cells as a Molecule (see §2)."""
    if len(n) != 3 or any(not isinstance(k, int) or not 1 <= k <= 10 for k in n):
        raise ValueError(tr('Число ячеек по каждой оси — от 1 до 10.'))
    content = unit_cell(crystal)
    points = []
    for symbol, fx, fy, fz, _ in content:
        base = (fx, fy, fz)
        shifts = [[0] for _ in range(3)]
        if faces:
            for axis in range(3):
                if abs(base[axis]) < FACE:
                    shifts[axis] = [0, n[axis]]
        for i in range(n[0]):
            for j in range(n[1]):
                for k in range(n[2]):
                    for si in shifts[0]:
                        for sj in shifts[1]:
                            for sk in shifts[2]:
                                f = (fx + i + si, fy + j + sj, fz + k + sk)
                                if f[0] > n[0] + FACE or f[1] > n[1] + FACE or f[2] > n[2] + FACE:
                                    continue
                                points.append((symbol, f))
    unique = {}
    for symbol, f in points:
        key = tuple(round(x, 6) for x in f)
        unique.setdefault(key, (symbol, f))
    if len(unique) > MAX_ATOMS:
        raise ValueError(tr(f'Получится {len(unique)} атомов — больше {MAX_ATOMS}. Уменьшите число ячеек.'))
    atoms = tuple(Atom(s, *crystal.cell.cartesian(f)) for s, f in unique.values())
    formula = Molecule('', tuple(Atom(s, 0, 0, 0) for s, *_ in content)).formula
    title = f'{crystal.title or "crystal"} {formula} {n[0]}x{n[1]}x{n[2]}'
    return Molecule(title, atoms, None)


def cell_edges(cell, n=(1, 1, 1)):
    """The 12 edges of the block of n1 x n2 x n3 cells: [(start, end)] in A; the first three start at
    the origin along a, b, c."""
    corners = {}
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                corners[(i, j, k)] = cell.cartesian((i * n[0], j * n[1], k * n[2]))
    edges = []
    for (i, j, k), p in corners.items():
        for axis in range(3):
            step = [i, j, k]
            if step[axis] == 0:
                step[axis] = 1
                edges.append((p, corners[tuple(step)]))
    return edges

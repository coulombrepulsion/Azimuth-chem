"""Short contacts and hydrogen bonds of a crystal; the molecules they join.

§1 THEORY
    The kinds and their criteria are those of modules/spectrum/analysis/contacts.py §1 (IUPAC): a hydrogen bond
    D–H···A with D more electronegative than H, A a lone pair or a π system, the angle D–H···A at least HB_ANGLE;
    halogen, chalcogen, pnictogen and tetrel bonds R–E···Y along the extension of R–E (angle at least HOLE_ANGLE);
    anything else nearer than the sum of the van der Waals radii plus TOLERANCE — a van der Waals contact. In a
    crystal the partner is an atom of the cell shifted by a lattice vector: a contact is (atom i of the cell, atom j
    of the cell, the shift L of j), and (j, i, −L) is the same contact.
§2 ALGORITHM
    crystal_symmetry.walk gives the atoms of the cell, their bonds to shifted atoms and the molecules. For every
    atom i of the cell, the atoms within three bonds of it (with their shifts) are not contacts (as in the molecule
    module). Candidates: d(i, j + L) <= Rvdw_i + Rvdw_j + TOLERANCE over the 27 shifts L in {−1, 0, 1}^3 (cells longer
    than the longest contact, 3.8 + 0.2 A x 2, need no farther shift) — numpy; each pair once (i < j, or i = j and
    L after 0 in the order of the tuples). The kind: both directions tried (electrophilic site → nucleophile) in the
    order of contacts.ORDER; the donor or R is a bonded neighbour (with its shift) of the site; the first kind whose
    angle holds names the contact, the larger angle wins within a kind.
    A contact of two halogens R1–X1···X2–R2 gets both angles θ1 = R1–X1···X2 ≥ θ2 = X1···X2–R2 and its
    geometry (Desiraju & Parthasarathy 1989; Cavallo et al., Chem. Rev. 116 (2016) 2478): type I (θ1 ≈ θ2,
    |θ1 − θ2| < 15°) — the atoms meet side by side, no σ-hole points at the belt of the other: not a halogen bond,
    a van der Waals contact even when θ1 ≥ 150°; type II (|θ1 − θ2| ≥ 30°, θ1 ≈ 180°, θ2 ≈ 90°) — the σ-hole of X1
    at the belt of X2, a halogen bond; between them — «I/II». grouped(contacts): the contacts that the
    symmetry repeats (the same labels of the two sites, the same kind, d within 1e-3 A) are one row with a count.
    network(crystal, kinds): the molecules of the cell and every copy of a molecule (shifted by a lattice vector)
    that one of the contacts of these kinds joins to them — each contact in both directions (a molecule that gives
    a hydrogen bond to the next one along a also takes one from the previous).
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py: «Контакты…» of the «Кристалл» window (the table, «Показать сеть»).
§4 SPECIFICATION
    contacts(crystal, factor=None, tolerance=TOLERANCE) -> tuple of CrystalContact(kind, i, j, shift, site, acceptor,
        donor (each (atom, shift) or None), distance, vdw_sum, angle or None, angle2 (θ2 of X···X) or None,
        geometry 'I' | 'II' | 'I/II' | ''), sorted: the kinds in contacts.ORDER, then van der Waals contacts, each by
        d − vdw_sum. ratio(contact) = d / Σ r(вдВ) — the normalised contact.
    representatives(found, atoms) -> [CrystalContact] — the first contact of each row of grouped, in its order.
    grouped(contacts, atoms) -> [(kind, text 'O1–H1···O2', distance, vdw_sum, angle, count)].
    network(crystal, kinds=('hydrogen'), factor=None, layers=1, chosen=None, **criteria) -> (Molecule, number of
        molecules added); layers — the network grown so many times, chosen — only these contacts;
        row_contacts(found, atoms) -> [[CrystalContact]] — all the copies of each row of grouped.
    Contacts(..., hb_angle=None, hole_angle=None) — the least angles (the window's criteria, as «Define
        Contacts» of Mercury); hydrogen_bonds(crystal, found) -> [HydrogenBond(donor, hydrogen, acceptor, code,
        d_dh, d_ha, d_da, angle, count)] — the table of a paper, code the symmetry code of the acceptor with the donor
        in the asymmetric unit ('' for x, y, z, '?' if not found); symmetry_code(crystal, walk, donor, acceptor);
        code_text(R, τ) -> '-x+1, y+1/2, -z+1/2'; marks(bonds) -> {code: 'i' …}; hydrogen_table(bonds, decimal)
        -> the text with tabs and the codes under it.
    cut(molecule, indices) -> Molecule: the molecules (bonded fragments) of the model that hold the atoms indices
        (a molecule with its neighbours taken out of the crystal for a calculation).
§5 PROCEDURES - below.
§6 NOTES
    The constants are those of the molecule module (TOLERANCE 0.2 A, HB_ANGLE 120°, HOLE_ANGLE 150°); positions of
    hydrogen atoms in X-ray structures are short (C–H about 0.95 A instead of 1.09): H···A distances are then too long
    by about 0.1 A — the window of the contacts moves them to the neutron lengths first
    (crystal_hydrogens.normalized, as Mercury; a check box), contacts() takes the crystal it is given. Infinite parts (a
    salt) have no molecules: their
    contacts are listed (often none: Na and Cl are bonded by the covalent radii) and network adds nothing.
§7 TESTS
    tests/compass/test_crystal_contacts.py.
§8' ROBUSTNESS / ERRORS
    A cell with no atoms raises in crystal.unit_cell; a cell edge shorter than the longest contact is still right
    for contacts with the nearest images (only the 27 neighbours are looked at).
"""

from dataclasses import dataclass
from math import acos, degrees

from azimuth.i18n import tr
from modules.compass.chemistry import crystal_symmetry as cs
from modules.spectrum.analysis import contacts as mc

TOLERANCE = mc.TOLERANCE
SHIFTS = tuple((i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1))


@dataclass(frozen=True)
class CrystalContact:
    kind: str
    i: int
    j: int
    shift: tuple
    site: tuple | None  # (atom, shift) of the H or the σ-hole atom
    acceptor: tuple | None
    donor: tuple | None
    distance: float
    vdw_sum: float
    angle: float | None
    angle2: float | None = None  # θ2 of a contact X···X of two halogens
    geometry: str = ''  # 'I', 'II' or 'I/II' for X···X


HALOGENS = {'F', 'Cl', 'Br', 'I', 'At'}
TYPE_I = 15.0  # |θ1 − θ2| below: type I
TYPE_II = 30.0  # |θ1 − θ2| from: type II


def ratio(contact):
    """D / Σ r(вдВ) — below 1 the atoms are nearer than their van der Waals radii allow."""
    return contact.distance / contact.vdw_sum if contact.vdw_sum else None


def _halogen_pair(w, a, b):
    """(θ1, θ2, geometry) of R1–X1···X2–R2 (a, b: (atom, shift)), θ1 ≥ θ2; None without a bonded R on both sides."""
    pa, pb = _xyz(w, a), _xyz(w, b)
    ta = max((_angle(_xyz(w, r), pa, pb) for r in _neighbours(w, a)), default=None)
    tb = max((_angle(pa, pb, _xyz(w, r)) for r in _neighbours(w, b)), default=None)
    if ta is None or tb is None:
        return None
    t1, t2 = max(ta, tb), min(ta, tb)
    gap = t1 - t2
    return t1, t2, 'I' if gap < TYPE_I else ('II' if gap >= TYPE_II else 'I/II')


def _add(s, t):
    return tuple(s[k] + t[k] for k in range(3))


def _near(w, start, limit=3):
    """{(atom, shift)} within limit bonds of (start, 0)."""
    seen = {(start, (0, 0, 0)): 0}
    frontier = [(start, (0, 0, 0))]
    for depth in range(limit):
        nxt = []
        for k, s in frontier:
            for m, t in w.edges[k]:
                node = (m, _add(s, t))
                if node not in seen:
                    seen[node] = depth + 1
                    nxt.append(node)
        frontier = nxt
    return set(seen)


def _xyz(w, node):
    k, s = node
    f = w.frac[k] + s
    return tuple(float(x) for x in f @ w.vectors)


def _angle(a, b, c):
    u = [a[k] - b[k] for k in range(3)]
    v = [c[k] - b[k] for k in range(3)]
    nu, nv = sum(x * x for x in u) ** 0.5, sum(x * x for x in v) ** 0.5
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    return degrees(acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(u, v)) / (nu * nv)))))


def _neighbours(w, node):
    k, s = node
    return [(m, _add(s, t)) for m, t in w.edges[k]]


def _kind(w, e, n, hb_angle=None, hole_angle=None):
    """(kind, donor, angle) for the site e pointing at the nucleophile n (both (atom, shift)), or None; the
    least angles D–H···A and R–E···Y may be given (the criteria of the window), else those of the molecule module."""
    hb_angle = mc.HB_ANGLE if hb_angle is None else hb_angle
    hole_angle = mc.HOLE_ANGLE if hole_angle is None else hole_angle
    symbol = w.atoms[e[0]][0]
    other = w.atoms[n[0]][0]
    if not (other in mc.NUCLEOPHILES or (other == 'C' and len(w.edges[n[0]]) < 4)):
        return None
    pe, pn = _xyz(w, e), _xyz(w, n)
    if symbol == 'H':
        donors = [d for d in _neighbours(w, e) if w.atoms[d[0]][0] in mc.ELECTRONEGATIVE]
        best = max(((_angle(_xyz(w, d), pe, pn), d) for d in donors), default=None)
        if best is not None and best[0] >= hb_angle:
            return 'hydrogen', best[1], best[0]
        return None
    for kind, elements in mc.HOLES:
        if symbol in elements:
            best = max(((_angle(_xyz(w, r), pe, pn), r) for r in _neighbours(w, e) if r != n), default=None)
            if best is not None and best[0] >= hole_angle:
                return kind, best[1], best[0]
    return None


def contacts(crystal, factor=None, tolerance=TOLERANCE, hb_angle=None, hole_angle=None):
    import numpy as np

    w = cs.walk(crystal, factor)
    n = len(w.atoms)
    symbols = [a[0] for a in w.atoms]
    vdw = np.array([mc.VDW.get(s, 1.8) for s in symbols])
    reach = vdw[:, None] + vdw[None, :] + tolerance
    cart = w.frac @ w.vectors
    near = [_near(w, i) for i in range(n)]
    found = []
    for s in SHIFTS:
        moved = cart + np.array(s, dtype=float) @ w.vectors
        d = np.linalg.norm(moved[None, :, :] - cart[:, None, :], axis=2)
        for i, j in zip(*np.nonzero((d <= reach) & (d > 0.1))):
            i, j = int(i), int(j)
            if i > j or (i == j and s <= (0, 0, 0)):
                continue
            if (j, s) in near[i] or symbols[i] == 'X' or symbols[j] == 'X':
                continue
            a, b = (i, (0, 0, 0)), (j, s)
            options = [(e, m, _kind(w, e, m, hb_angle, hole_angle)) for e, m in ((a, b), (b, a))]
            options = [(mc.ORDER.index(k[0]), -k[2], e, m, k) for e, m, k in options if k is not None]
            dist, total = float(d[i, j]), float(vdw[i] + vdw[j])
            pair = _halogen_pair(w, a, b) if symbols[i] in HALOGENS and symbols[j] in HALOGENS else None
            if options:
                _, _, e, m, (kind, donor, angle) = min(options)
                if pair is not None and pair[2] == 'I' and kind == 'halogen':
                    kind = 'vdw'  # side by side — not a σ-hole at the belt of the other
                found.append(CrystalContact(kind, i, j, s, e, m, donor, dist, total, angle,
                                            pair[1] if pair else None, pair[2] if pair else ''))
            elif pair is not None:
                found.append(CrystalContact('vdw', i, j, s, None, None, None, dist, total, pair[0], pair[1], pair[2]))
            else:
                found.append(CrystalContact('vdw', i, j, s, None, None, None, dist, total, None))
    rank = {k: r for r, k in enumerate(mc.ORDER + ('vdw',))}
    return tuple(sorted(found, key=lambda c: (rank[c.kind], c.distance - c.vdw_sum)))


def _label(atoms, node):
    k = node[0]
    return atoms[k][4] or f'{atoms[k][0]}{k + 1}'


def text(contact, atoms):
    """'O1–H1···O2' (D–H···A) or 'C3···C7'."""
    if contact.site is None:
        return f'{_label(atoms, (contact.i,))}···{_label(atoms, (contact.j,))}'
    return f'{_label(atoms, contact.donor)}–{_label(atoms, contact.site)}···{_label(atoms, contact.acceptor)}'


def _rows(found, atoms):
    rows = []
    for c in found:
        t = text(c, atoms)
        for row in rows:
            if row[0] == c.kind and row[1] == t and abs(row[2] - c.distance) < 1e-3:
                row[5] += 1
                break
        else:
            rows.append([c.kind, t, c.distance, c.vdw_sum, c.angle, 1, c])
    return rows


def grouped(found, atoms):
    return [tuple(r[:6]) for r in _rows(found, atoms)]


def row_contacts(found, atoms):
    """All the contacts of each row of grouped (the symmetry copies), in the same order."""
    rows = []
    for c in found:
        t = text(c, atoms)
        for row in rows:
            if row[0] == c.kind and row[1] == t and abs(row[2] - c.distance) < 1e-3:
                row[3].append(c)
                break
        else:
            rows.append([c.kind, t, c.distance, [c]])
    return [row[3] for row in rows]


def representatives(found, atoms):
    """The first contact of each row of grouped (its θ2 and geometry), in the same order."""
    return [r[6] for r in _rows(found, atoms)]


def name(kind):
    return tr(mc.NAMES[kind]) if kind in mc.NAMES else tr('ван-дер-ваальсов контакт')


# the table of hydrogen bonds of a paper (as Mercury, PLATON, SHELXL's HTAB): D–H, H···A, D···A, the angle and
# the symmetry code of the acceptor — the operation that takes its site of the file to where it stands, with the donor
# in the asymmetric unit of the file (x, y, z).

@dataclass(frozen=True)
class HydrogenBond:
    donor: str  # the labels of the file
    hydrogen: str
    acceptor: str
    code: str  # '-x+1, y+1/2, -z+1/2'; '' — the acceptor of the same asymmetric unit (x, y, z)
    d_dh: float
    d_ha: float
    d_da: float
    angle: float
    count: int = 1  # the copies of it in the cell


def _sites(crystal):
    return {site.label: site for site in crystal.sites}


def _placement(crystal, site, f):
    """(R, τ) — an operation of the crystal plus a lattice translation with R·site + τ = f (fractional), or None."""
    from fractions import Fraction

    for rows, shifts in crystal.operations:
        moved = [sum(rows[i][j] * (site.x, site.y, site.z)[j] for j in range(3)) + float(shifts[i]) for i in range(3)]
        t = [round(f[i] - moved[i]) for i in range(3)]
        if all(abs(f[i] - moved[i] - t[i]) < 2e-3 for i in range(3)):
            return rows, tuple(Fraction(shifts[i]) + t[i] for i in range(3))
    return None


def _inverse(rows):
    import numpy as np

    return tuple(tuple(int(round(v)) for v in row) for row in np.linalg.inv(np.array(rows, dtype=float)))


def code_text(rows, tau):
    """(R, τ) -> '-x+1, y+1/2, -z+1/2' (the style of a CIF); 'x, y, z' for the identity."""
    out = []
    for i in range(3):
        part = ''
        for j, name in enumerate('xyz'):
            r = rows[i][j]
            if r:
                part += ('-' if r < 0 else ('+' if part else '')) + ('' if abs(r) == 1 else str(abs(r))) + name
        t = tau[i]
        if t:
            part += ('-' if t < 0 else '+') + str(abs(t))
        out.append(part)
    return ', '.join(out)


def symmetry_code(crystal, w, donor, acceptor):
    """The code of the acceptor node (atom, shift) seen from the donor node put in the asymmetric unit: the operation
    g with g(site of the acceptor) = g_D⁻¹(position of the acceptor), g_D the placement of the donor. '' for x, y, z;
    None when an atom is not placed by the operations of the crystal (a file without them)."""
    from fractions import Fraction

    sites = _sites(crystal)
    (kd, sd), (ka, sa) = donor, acceptor
    site_d, site_a = sites.get(w.atoms[kd][4]), sites.get(w.atoms[ka][4])
    if site_d is None or site_a is None:
        return None
    fd = [float(w.frac[kd][i]) + sd[i] for i in range(3)]
    fa = [float(w.frac[ka][i]) + sa[i] for i in range(3)]
    gd = _placement(crystal, site_d, fd)
    if gd is None:
        return None
    inv = _inverse(gd[0])
    q = [sum(inv[i][j] * (fa[j] - float(gd[1][j])) for j in range(3)) for i in range(3)]
    ga = _placement(crystal, site_a, q)
    if ga is None:
        return None
    rows, tau = ga
    if rows == ((1, 0, 0), (0, 1, 0), (0, 0, 1)) and all(t == Fraction(0) for t in tau):
        return ''
    return code_text(rows, tau)


def hydrogen_bonds(crystal, found, factor=None):
    """[HydrogenBond] of the contacts found of the kind 'hydrogen': one row for the copies that the symmetry repeats
    (the same labels and code), in the order found."""
    w = cs.walk(crystal, factor)
    rows = {}
    for c in found:
        if c.kind != 'hydrogen' or c.donor is None:
            continue
        d, h, a = c.donor, c.site, c.acceptor
        pd, ph, pa = _xyz(w, d), _xyz(w, h), _xyz(w, a)

        def far(p, q):
            return sum((p[k] - q[k]) ** 2 for k in range(3)) ** 0.5

        code = symmetry_code(crystal, w, d, a)
        key = (w.atoms[d[0]][4], w.atoms[h[0]][4], w.atoms[a[0]][4], code, round(c.distance, 3))
        if key in rows:
            rows[key] = HydrogenBond(*key[:4], rows[key].d_dh, rows[key].d_ha, rows[key].d_da, rows[key].angle,
                                     rows[key].count + 1)
            continue
        rows[key] = HydrogenBond(key[0], key[1], key[2], code if code is not None else '?', far(pd, ph), c.distance,
                                 far(pd, pa), c.angle)
    return list(rows.values())


ROMAN = ('i', 'ii', 'iii', 'iv', 'v', 'vi', 'vii', 'viii', 'ix', 'x', 'xi', 'xii', 'xiii', 'xiv', 'xv', 'xvi', 'xvii',
         'xviii', 'xix', 'xx')


def marks(bonds):
    """{code: 'i' | 'ii' …} — the marks of the codes in the order of the bonds (not for '' or '?')."""
    out = {}
    for b in bonds:
        if b.code and b.code != '?' and b.code not in out:
            out[b.code] = ROMAN[len(out)] if len(out) < len(ROMAN) else str(len(out) + 1)
    return out


def hydrogen_table(bonds, decimal='.'):
    """The table of a paper as text with tabs (to paste into a word processor or a spreadsheet): D–H···A, D–H, H···A,
    D···A, D–H···A, then the symmetry codes under it."""
    mark = marks(bonds)

    def num(v, n):
        return f'{v:.{n}f}'.replace('.', decimal)

    lines = ['D–H···A\tD–H, Å\tH···A, Å\tD···A, Å\tD–H···A, °']
    for b in bonds:
        acceptor = b.acceptor + (f'^{mark[b.code]}' if b.code in mark else '')
        lines.append(f'{b.donor}–{b.hydrogen}···{acceptor}\t{num(b.d_dh, 2)}\t{num(b.d_ha, 2)}\t{num(b.d_da, 3)}\t'
                     f'{num(b.angle, 0)}')
    if mark:
        lines.append('')
        lines.append(tr('Коды симметрии: ') + '; '.join(f'({m}) {c}' for c, m in mark.items()))
    return '\n'.join(lines) + '\n'


PI_KINDS = ('pi', 'ch_pi')  # the π–π stacks and the C–H···π of crystal_rings in network()


def _pi_pairs(crystal, w, kinds, factor):
    """The pairs of (atom, cell shift) that the π–π stacks and the C–H···π join (an atom of each ring stands
    for its molecule)."""
    from modules.compass.chemistry import crystal_rings as rg

    def at(k, s=(0, 0, 0)):  # the atom k of the unwrapped copy of crystal_rings, moved by s
        return k, tuple(w.shift[k][x] + s[x] for x in range(3))

    pairs = []
    if 'pi' in kinds:
        found, stacks = rg.stacking(crystal, factor)
        pairs += [(at(found[x.first].atoms[0]), at(found[x.second].atoms[0], x.shift)) for x in stacks]
    if 'ch_pi' in kinds:
        found, near = rg.ch_pi(crystal, factor)
        pairs += [(at(x.hydrogen), at(found[x.ring].atoms[0], x.shift)) for x in near]
    return pairs


def network(crystal, kinds=('hydrogen',), factor=None, layers=1, chosen=None, **criteria):
    """The molecules of the cell and the copies of molecules joined to them by the contacts of these kinds;
    criteria — tolerance, hb_angle, hole_angle of contacts() (those of the window); kinds may hold 'pi'
    (π–π stacks) and 'ch_pi' (C–H···π) of crystal_rings. 0.170.0 (Mercury's «expand contacts»): layers — how many
    times the network grows from the molecules added (1: the neighbours of the cell); chosen — only these contacts
    (the rows picked in the window) instead of all of the kinds."""
    from azimuth.core import MAX_ATOMS, Atom, Molecule

    w = cs.walk(crystal, factor)
    if chosen is not None:
        pairs = [((c.i, (0, 0, 0)), (c.j, c.shift)) for c in chosen]
    else:
        contact_kinds = [k for k in kinds if k not in PI_KINDS]
        found = [c for c in contacts(crystal, factor, **criteria) if c.kind in contact_kinds] if contact_kinds else []
        pairs = [((c.i, (0, 0, 0)), (c.j, c.shift)) for c in found] + _pi_pairs(crystal, w, kinds, factor)
    groups = {}
    for i, c in enumerate(w.component):
        groups.setdefault(c, []).append(i)

    def copy_of(atom, s):
        """(component, translation of the copy from the one in the cell) of the atom at shift s, or None."""
        c = w.component[atom]
        if w.periods[c]:
            return None
        m = w.move[c]
        return c, tuple(s[k] - (w.shift[atom][k] - m[k]) for k in range(3))

    relations = set()  # (component, component joined, the lattice vector between their copies)
    for p, q in pairs:
        for a, b in ((p, q), (q, p)):
            first, second = copy_of(*a), copy_of(*b)
            if first is not None and second is not None:
                relations.add((first[0], second[0], tuple(second[1][k] - first[1][k] for k in range(3))))
    copies = {(c, (0, 0, 0)) for c in groups if not w.periods[c]}
    base = set(copies)
    frontier = set(copies)
    for _ in range(max(1, int(layers))):
        grown = set()
        for c, t in frontier:
            for one, two, delta in relations:
                if one == c:
                    new = (two, tuple(t[k] + delta[k] for k in range(3)))
                    if new not in copies:
                        grown.add(new)
        copies |= grown
        frontier = grown
        if not grown:
            break
    atoms = []
    for c, t in sorted(copies, key=lambda x: (x[1] != (0, 0, 0), x)):
        m = w.move[c]
        for i in groups[c]:
            f = [float(w.frac[i][k] + w.shift[i][k] - m[k] + t[k]) for k in range(3)]
            atoms.append(Atom(w.atoms[i][0], *crystal.cell.cartesian(f)))
    if len(atoms) > MAX_ATOMS:
        raise ValueError(tr('Получится {} атомов — больше {}. Уменьшите число ячеек.').format(len(atoms), MAX_ATOMS))
    title = f'{crystal.title or "crystal"} ' + tr('сеть контактов')
    return Molecule(title, tuple(atoms), None), len(copies) - len(base)


def model_contacts(molecule, crystal, found, kinds=None, within=0.003, factor=None):
    """[(i, j, kind)] — the pairs of atoms of the model (Cartesian: a block, a network,
    a shell) that are the contacts found by contacts(crystal): the same two elements at the same distance (within
    «within» Å), of the kinds given (None — all but van der Waals). For a hydrogen bond these are its H and its
    acceptor."""
    import numpy as np

    wanted = [c for c in found if (c.kind in kinds if kinds is not None else c.kind != 'vdw')]
    if not wanted or not molecule.atoms:
        return []
    cell = cs.walk(crystal, factor).atoms
    keys = sorted({(c.kind, round(c.distance, 4), frozenset((cell[c.i][0], cell[c.j][0]))) for c in wanted},
                  key=lambda k: k[1])
    xyz = np.array([a.position for a in molecule.atoms], dtype=float)
    symbols = [a.symbol for a in molecule.atoms]
    reach = keys[-1][1] + within + 0.01
    d = np.linalg.norm(xyz[:, None, :] - xyz[None, :, :], axis=2)
    from dataclasses import replace as _replace

    from modules.compass.chemistry.builder import connections

    owner = list(range(len(symbols)))  # the molecules of the model: a contact joins two of them, never one

    def root(k):
        while owner[k] != k:
            owner[k] = owner[owner[k]]
            k = owner[k]
        return k

    for a, b, *_ in connections(_replace(molecule, bonds=None)):
        owner[root(a)] = root(b)
    out = []
    for i, j in zip(*np.nonzero(np.triu(d <= reach, 1))):
        i, j = int(i), int(j)
        if root(i) == root(j):
            continue
        pair = frozenset((symbols[i], symbols[j]))
        for kind, distance, elements in keys:
            if elements == pair and abs(d[i, j] - distance) <= within:
                out.append((i, j, kind))
                break
    return out


def cut(molecule, indices):
    """The whole fragments (by the bonds Compass draws) that hold the atoms indices, as a new Molecule."""
    from azimuth.core import Molecule
    from modules.compass.chemistry.builder import connections

    n = len(molecule.atoms)
    neighbours = [[] for _ in range(n)]
    for i, j, _ in connections(molecule):
        neighbours[i].append(j)
        neighbours[j].append(i)
    keep, stack = set(), [i for i in indices if 0 <= i < n]
    while stack:
        k = stack.pop()
        if k in keep:
            continue
        keep.add(k)
        stack += neighbours[k]
    return Molecule(molecule.title, tuple(molecule.atoms[k] for k in sorted(keep)), None)

"""Weak interactions told apart by NCI: the regions of low RDG split into domains, each named and measured.

HEADER The NCI surface (modules/spectrum/wavefunction/multiwfn.py, run_nci) shows where the weak interactions are; this
    module says which ones they are. The low-RDG region of the grids is cut into its connected pieces (domains); each
    domain gets the atoms it lies between, the value of sign(λ₂)ρ where RDG is lowest (the spike of the plot), its
    volume and the density integrated over it, and a kind: the IUPAC kinds of the QTAIM contacts (contacts.py) and those
    that QTAIM misses — π–π stacking, C–H···π, steric repulsion and the repulsion inside a ring. Wilkinson convention,
    sections 1-8.

§1 THEORY NCI (Johnson et al., J. Am. Chem. Soc. 2010, 132, 6498): s = |∇ρ| / (2 (3π²)^(1/3) ρ^(4/3)) falls towards zero
    where the density is flat between atoms; every weak interaction makes a low-s basin, the sign of the second
    eigenvalue λ₂ of the Hessian of ρ tells attraction (λ₂ < 0) from repulsion (λ₂ > 0), and ρ there its strength. The
    value of sign(λ₂)ρ at the lowest s of a basin is nearly ρ at its bond critical point when there is one (s = 0 at a
    critical point). A basin may dip on both sides of zero (C–H···π, stacking): its spike is taken on the side that
    holds more of the density of the basin, attraction or repulsion. Contreras-García et al. (J. Chem. Theory Comput.
    2011, 7, 625, NCIPLOT) read these basins one by one; Boto et al. (J. Chem. Theory Comput. 2020, 16, 4150, NCIPLOT 4)
    integrate ρ over the volume of each one: these integrals follow the interaction energies within a family of
    complexes. The ranges of sign(λ₂)ρ used to grade the spike (a.u.): below −0.035 a strong attraction (strong hydrogen
    bonds, charged ones), −0.035 … −0.010 an attraction (ordinary hydrogen, halogen and other σ-hole bonds), −0.010 …
    +0.010 weak, van der Waals like (dispersion, stacking), above +0.010 repulsion (steric clashes, the centres of
    rings) — the ranges of the colour scales of these papers. A hydrogen bond also gets the energy of contacts.energy
    (Emamian et al. 2019) from |sign(λ₂)ρ| of its spike in place of ρ_BCP.
§2 ALGORITHM
    1. The domain nodes: RDG (or IRI) below the level of the surface (δg_inter of IGMH above it — its spike is
       the node of the highest δg_inter) and |sign(λ₂)ρ| < RHO_CUT (Multiwfn sets RDG to 100
       where ρ > 0.05 already). Connected pieces with 26 neighbours (a label propagation with pointer jumping over the
       edges of the masked nodes); fewer than MIN_NODES nodes — noise of the grid, dropped.
    2. The atoms: every node belongs to the atom with the smallest d / r_vdW (Bondi radii) and faces the atom with the
       smallest d / r_vdW among those more than two bonds away from the first one (or in another molecule); the pair of
       the node is weighted by ρ. The main pair of a domain is the heaviest; the pairs of at least SHARE of the weight
       make its two sides (each atom put on the side of the main atom it is nearer to). Domains with the same main pair
       (or whose main atoms are in the same two different rings) and the same sign of the spike are one interaction cut
       by the grid: they are joined.
    3. The kind, in this order: a repulsive spike (> STERIC) inside a ring of the molecule (the centre of the domain
    within
       RING_OFFSET Å of the centroid of a planar ring of 5–7 atoms, crystal_rings.cycles) — 'ring'; any other repulsive
       spike — 'steric'; the main atoms in two different rings whose planes are within 30° — 'stacking' (its sides
       are the two rings); a
       hydrogen of one side bonded to C (N, O) facing at least two ring or unsaturated atoms whose centroid makes
       C–H···Cg ≥ contacts.HB_ANGLE — 'ch-pi' ('hydrogen' with π); the main pair by contacts (hydrogen, halogen,
       chalcogen, pnictogen, tetrel); else 'vdw'.
    4. The numbers: the spike, the range of sign(λ₂)ρ, the volume (nodes × the volume of a cell), ∫ρ dV over the
       attractive (λ₂ < 0) and the repulsive nodes (electrons), the ρ-weighted centre; the BCP of the main pair (or the
       nearest one within 1.5 grid steps of a node) when a QTAIM topology is given.
§3 APPLICATIONS
    modules/compass/view/nci_plot.py: the table of the tab «NCI» of Spectrum, the labels of the spikes on the plot, the
    CSV «<stem>_nci_domains.csv» in «Анализ»; modules/compass/actions/surface_actions.py computes them after run_nci.
§4 SPECIFICATION
    find(sign, field, level=None, kind='nci' | 'iri' | 'igmh', molecule=None, topology=None, charge=0) -> tuple of
    Domain sorted by
        the spike (the strongest attraction first); sign, field: cubes of modules/spectrum/readers/cube.py on one grid;
        molecule: by default that of the field cube. ValueError: the grids differ.
    Domain(kind, atoms (i, j) sorted, donor, site, acceptor, angle ° | None, peak, low, high (a.u.), volume Å³,
        attractive, repulsive (e), centre (Å), nodes (flat indices of the grid), sides ((atoms), (atoms)), strength
        'strong' | 'medium' | 'weak' | 'repulsive', energy kcal/mol | None, grade (contacts.STRENGTHS key) | None,
        point CriticalPoint | None, intra bool, distance Å, dg (IGMH, a.u.) | None); for 'stacking' the sides are the
        atoms of the two rings, for
        'ring' (the atoms of the ring, ()).
    attach(domains, igmh pairs [(i, j, value, …)], molecule) -> the domains with dg.
    label(domain, symbols) -> 'водородная O1–H3···O4'; chain(domain, symbols) -> 'O1–H3···O4'; detail(domain, symbols)
    -> the numbers in words (a tooltip); table(domains, symbols) -> (header, rows); NAMES, STRENGTHS.
§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES RHO_CUT = 0.05 a.u. (Multiwfn), MIN_NODES = 3, SHARE = 0.15, STERIC = 0.005 a.u., RING_OFFSET =
    0.7 Å, STACK_COS = cos 30°. The coarse grid of Multiwfn (about 0.07–0.25 Å) may cut a thin basin; joining by the
    main pair repairs most of it. The kind is geometric, as in contacts.py; NCI adds the sign and the size. The energy
    is an estimate (±15 % of the fit and the difference between the spike and ρ_BCP).
§7 TEST CASES (tests/spectrum/test_nci_domains.py)
    The S22 water dimer from the grids recorded with Multiwfn 2026.7.15 (wavefunction and promolecular): one hydrogen
    bond O1–H3···O4, spike −0.021 and −0.030; promolecular grids of tests/promolecule.py: CF3Br···NH3 halogen, the
    benzene dimer stacking, benzene···methane C–H···π, benzene the ring, the methane dimer van der Waals.
§8 ERROR ANALYSIS Near the cutoffs the grade changes with the method and the grid; a promolecular density overestimates
    ρ at the spikes (water dimer: −0.030 against −0.021 of B3LYP); the sides depend on the radii for contacts of very
    different atoms.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import dist

import numpy as np

from azimuth.i18n import tr
from modules.compass.chemistry.crystal_rings import cycles
from modules.compass.chemistry.geometry_tools import BOHR
from modules.spectrum.analysis import contacts

RHO_CUT = 0.05
LEVELS = {'nci': 0.5, 'iri': 1.0, 'igmh': 0.005}
ATTACH = 3.0  # Å: an IGMH atom pair belongs to the domain whose centre is nearest its midpoint, within this
MIN_NODES = 3
SHARE = 0.15
STRONG, MEDIUM, WEAK = -0.035, -0.010, 0.010
STERIC = 0.005
RING_OFFSET = 0.7
STACK_COS = 0.866  # the planes of the rings within 30°
PLANAR = 0.1
OFFSETS = np.array([(a, b, c) for a in (-1, 0, 1) for b in (-1, 0, 1) for c in (-1, 0, 1) if (a, b, c) > (0, 0, 0)])
NAMES = {**contacts.NAMES, 'ch-pi': 'C–H···π', 'stacking': 'π-стэкинг', 'steric': 'стерическое отталкивание',
         'ring': 'отталкивание в кольце'}
STRENGTHS = {'strong': 'сильное притяжение', 'medium': 'притяжение', 'weak': 'слабое (ван-дер-ваальсово)',
             'repulsive': 'отталкивание'}


@dataclass(frozen=True, eq=False)
class Domain:
    kind: str
    atoms: tuple
    donor: int | None
    site: int | None
    acceptor: int | None
    angle: float | None
    peak: float
    low: float
    high: float
    volume: float
    attractive: float
    repulsive: float
    centre: tuple
    nodes: np.ndarray
    sides: tuple
    strength: str
    energy: float | None = None
    grade: str | None = None
    point: object = None
    intra: bool = False
    distance: float = 0.0
    dg: float | None = None


def _pieces(mask):
    """(flat indices of the masked nodes, the label of each: the smallest node index of its piece, 26 neighbours)."""
    flat = np.flatnonzero(mask)
    m = len(flat)
    if not m:
        return flat, np.zeros(0, np.int64)
    shape = np.array(mask.shape)
    where = np.full(mask.size, -1, np.int64)
    where[flat] = np.arange(m)
    coords = np.array(np.unravel_index(flat, mask.shape)).T
    us, vs = [], []
    for off in OFFSETS:
        c = coords + off
        ok = np.all((c >= 0) & (c < shape), axis=1)
        other = np.full(m, -1, np.int64)
        other[ok] = where[np.ravel_multi_index(c[ok].T, mask.shape)]
        good = other >= 0
        us.append(np.flatnonzero(good))
        vs.append(other[good])
    u, v = np.concatenate(us), np.concatenate(vs)
    label = np.arange(m)
    while True:
        low = np.minimum(label[u], label[v])
        new = label.copy()
        np.minimum.at(new, u, low)
        np.minimum.at(new, v, low)
        while True:
            jumped = new[new]
            if np.array_equal(jumped, new):
                break
            new = jumped
        if np.array_equal(new, label):
            return flat, label
        label = new


def _rings(symbols, xyz, neighbours):
    """[(atoms, centroid, normal)] of the planar rings of 5–7 atoms."""
    out = []
    for path in cycles(lambda k: set(neighbours[k]), symbols, range(len(symbols))):
        points = xyz[list(path)]
        centre = points.mean(axis=0)
        _, _, vt = np.linalg.svd(points - centre)
        if float(np.abs((points - centre) @ vt[-1]).max()) <= PLANAR:
            out.append((tuple(path), centre, vt[-1]))
    return out


class _Molecule:
    def __init__(self, molecule):
        atoms = list(molecule.atoms)
        self.symbols = [a.symbol for a in atoms]
        self.xyz = np.array([tuple(float(c) for c in a.position) for a in atoms], float).reshape(-1, 3)
        rows = [tuple(p) for p in self.xyz]
        self.neighbours = contacts._bonds(self.symbols, rows)
        self.group = contacts._components(self.neighbours)
        n = len(atoms)
        self.near = np.zeros((n, n), bool)
        for k in range(n):
            for m, steps in contacts._separation(self.neighbours, k, 2).items():
                self.near[k, m] = True
        self.radius = np.array([contacts.VDW.get(s, 1.8) for s in self.symbols])
        self.rings = _rings(self.symbols, self.xyz, self.neighbours)
        self.ring_atoms = {k for path, *_ in self.rings for k in path}

    def pairs(self, points, weights, chunk=4000):
        """{(i, j): weight} of the nodes at points (in chunks: a large domain of a large molecule stays small in memory)."""
        out = {}
        for start in range(0, len(points), chunk):
            part = points[start:start + chunk]
            ratio = np.linalg.norm(part[:, None, :] - self.xyz[None, :, :], axis=2) / self.radius[None, :]
            first = np.argmin(ratio, axis=1)
            other = np.where(self.near[first], np.inf, ratio)
            second = np.argmin(other, axis=1)
            valid = np.isfinite(other[np.arange(len(part)), second])
            for a, b, w in zip(first[valid], second[valid], weights[start:start + chunk][valid]):
                key = (int(min(a, b)), int(max(a, b)))
                out[key] = out.get(key, 0.0) + float(w)
        return out

    def key(self, main):
        """The main pair, or the two rings when both atoms are in rings of different molecules or rings apart: the pieces
        of one stacking that the grid cut join by it."""
        i, j = main
        ri = frozenset(path for path, *_ in self.rings if i in path)
        rj = frozenset(path for path, *_ in self.rings if j in path)
        if ri and rj and not (ri & rj):
            return tuple(sorted((ri, rj), key=lambda r: min(min(p) for p in r)))
        return main

    def pi(self, k):
        s = self.symbols[k]
        return k in self.ring_atoms or (s == 'C' and len(self.neighbours[k]) < 4) or (
            s in ('N', 'O', 'S') and len(self.neighbours[k]) < (3 if s == 'N' else 2))


def _sides(mol, main, pairs, total):
    i, j = main
    a, b = {i}, {j}
    for (p, q), w in pairs.items():
        if w < SHARE * total:
            continue
        xp, xq = mol.xyz[p], mol.xyz[q]
        if dist(xp, mol.xyz[i]) + dist(xq, mol.xyz[j]) <= dist(xp, mol.xyz[j]) + dist(xq, mol.xyz[i]):
            a.add(p)
            b.add(q)
        else:
            a.add(q)
            b.add(p)
    return tuple(sorted(a)), tuple(sorted(b))


def _hydrogen_to_pi(mol, sides):
    """(kind, donor, site, acceptor, angle) of an X–H on one side facing a π system on the other, or None."""
    for one, other in (sides, sides[::-1]):
        pis = [k for k in other if mol.pi(k)]
        if len(pis) < 2:
            continue
        cg = mol.xyz[pis].mean(axis=0)
        for h in one:
            if mol.symbols[h] != 'H':
                continue
            for d in mol.neighbours[h]:
                if mol.symbols[d] not in contacts.ELECTRONEGATIVE:
                    continue
                angle = contacts._angle(tuple(mol.xyz[d]), tuple(mol.xyz[h]), tuple(cg))
                if angle >= contacts.HB_ANGLE:
                    acceptor = min(pis, key=lambda k: dist(mol.xyz[k], mol.xyz[h]))
                    return ('ch-pi' if mol.symbols[d] == 'C' else 'hydrogen'), d, h, acceptor, angle
    return None


def _kind(mol, main, sides, peak, centre):
    """(kind, donor, site, acceptor, angle)."""
    if peak > STERIC:
        involved = set(sides[0]) | set(sides[1])
        for path, cg, _ in mol.rings:
            if float(np.linalg.norm(cg - centre)) <= RING_OFFSET and involved <= set(path) | {
                    m for k in path for m in mol.neighbours[k]}:
                return 'ring', None, None, None, None
        return 'steric', None, None, None, None
    key = mol.key(main)
    if key != main:
        normal = {path: n for path, _, n in mol.rings}
        if any(abs(float(normal[a] @ normal[b])) >= STACK_COS for a in key[0] for b in key[1]):
            return 'stacking', None, None, None, None
    to_pi = _hydrogen_to_pi(mol, sides)
    if to_pi is not None:
        return to_pi
    i, j = main
    options = []
    for e, n in ((i, j), (j, i)):
        found = contacts._kind(e, n, mol.symbols, [tuple(p) for p in mol.xyz], mol.neighbours)
        if found is not None:
            options.append((contacts.ORDER.index(found[0]), -found[2], e, n, found))
    if options:
        _, _, e, n, (kind, donor, angle) = min(options)
        return kind, donor, e, n, angle
    return 'vdw', None, None, None, None


def _spike(values, rdg):
    """sign(λ₂)ρ where RDG is lowest among the nodes of the side that holds more density (attraction or repulsion):
    a basin of a C–H···π contact dips on both sides of zero, and its deeper dip may be the weaker side."""
    rho = np.abs(values)
    attractive = values < 0
    side = attractive if rho[attractive].sum() >= rho[~attractive].sum() else ~attractive
    if not side.any():
        side = np.ones(len(values), bool)
    k = np.flatnonzero(side)[np.argmin(rdg[side])]
    return float(values[k])


def _grade(peak):
    return 'strong' if peak <= STRONG else 'medium' if peak <= MEDIUM else 'weak' if peak <= WEAK else 'repulsive'


def _point(topology, main, points, step):
    if topology is None:
        return None
    bonds = [p for p in getattr(topology, 'points', ()) if p.kind == 'bond' and len(p.atoms) == 2]
    for p in bonds:
        if tuple(sorted(p.atoms)) == main:
            return p
    best, where = None, 1.5 * step
    for p in bonds:
        d = float(np.min(np.linalg.norm(points - np.asarray(p.position, float), axis=1)))
        if d <= where:
            best, where = p, d
    return best


def find(sign, field, level=None, kind='nci', molecule=None, topology=None, charge=0):
    s = np.asarray(sign.values)[..., 0]
    f = np.asarray(field.values)[..., 0]
    if s.shape != f.shape or not np.allclose(sign.origin, field.origin, atol=1e-4) or not np.allclose(
            sign.axes, field.axes, atol=1e-6):
        raise ValueError(tr('NCI: сетки sign(λ₂)ρ и RDG не совпадают.'))
    molecule = molecule if molecule is not None else field.molecule
    if molecule is None or not molecule.atoms:
        return ()
    level = LEVELS.get(kind, 0.5) if level is None else level
    if kind == 'igmh':  # δg_inter is high where fragments interact — the lowest «RDG» is the highest δg_inter
        flat, label = _pieces((f > level) & (np.abs(s) < RHO_CUT))
        f = -f
    else:
        flat, label = _pieces((f < level) & (np.abs(s) < RHO_CUT))
    if not len(flat):
        return ()
    mol = _Molecule(molecule)
    axes = np.asarray(field.axes, float)
    cell = abs(float(np.linalg.det(axes)))
    step = float(np.max(np.linalg.norm(axes, axis=1)))
    coords = np.array(np.unravel_index(flat, f.shape)).T
    points = np.asarray(field.origin, float) + coords @ axes
    values = s.reshape(-1)[flat]
    rdg = f.reshape(-1)[flat]
    rho = np.abs(values)
    groups = {}
    for root in np.unique(label):
        idx = np.flatnonzero(label == root)
        if len(idx) < MIN_NODES:
            continue
        pairs = mol.pairs(points[idx], rho[idx])
        if not pairs:
            continue
        main = max(pairs, key=pairs.get)
        peak = _spike(values[idx], rdg[idx])
        groups.setdefault((mol.key(main), peak > STERIC), []).append(idx)
    found = []
    for (main, _), parts in groups.items():
        idx = np.concatenate(parts)
        pairs = mol.pairs(points[idx], rho[idx])
        total = sum(pairs.values())
        main = max(pairs, key=pairs.get)
        v = values[idx]
        peak = _spike(v, rdg[idx])
        weight = rho[idx]
        centre = (points[idx] * weight[:, None]).sum(axis=0) / max(float(weight.sum()), 1e-30)
        sides = _sides(mol, main, pairs, total)
        name, donor, site, acceptor, angle = _kind(mol, main, sides, peak, centre)
        if name == 'stacking':  # the sides are the two rings
            key = mol.key(main)
            sides = tuple(tuple(sorted({k for path in r for k in path})) for r in key)
        elif name == 'ring':  # the ring itself, the other side empty
            path = min(mol.rings, key=lambda r: float(np.linalg.norm(r[1] - centre)))[0]
            sides = (tuple(sorted(path)), ())
        energy = grade = None
        charged = bool(round(charge))
        if name == 'hydrogen' and peak < 0:
            energy = contacts.energy(-peak, charged)
            grade = contacts.strength(energy, charged)
        bohr3 = cell / BOHR ** 3
        found.append(Domain(name, main, donor, site, acceptor, angle, peak, float(v.min()), float(v.max()),
                            len(idx) * cell, float(weight[v < 0].sum() * bohr3), float(weight[v > 0].sum() * bohr3),
                            tuple(float(c) for c in centre), flat[idx], sides, _grade(peak), energy, grade,
                            _point(topology, main, points[idx], step), mol.group[main[0]] == mol.group[main[1]],
                            dist(mol.xyz[main[0]], mol.xyz[main[1]])))
    return tuple(sorted(found, key=lambda d: d.peak))


def attach(domains, pairs, molecule):
    """The domains with dg — the sum of the IGMH atom-pair δG indices [(i, j, value, …)] whose midpoints are
    nearest their centres (within ATTACH Å); pairs left over belong to none."""
    from dataclasses import replace

    if not domains or not pairs:
        return tuple(domains)
    xyz = np.array([tuple(float(c) for c in a.position) for a in molecule.atoms], float)
    centres = np.array([d.centre for d in domains], float)
    sums = [None] * len(domains)
    for i, j, value, *_ in pairs:
        if not (0 <= i < len(xyz) and 0 <= j < len(xyz)):
            continue
        gap = np.linalg.norm(centres - (xyz[i] + xyz[j]) / 2, axis=1)
        k = int(np.argmin(gap))
        if gap[k] <= ATTACH:
            sums[k] = (sums[k] or 0.0) + float(value)
    return tuple(replace(d, dg=v) for d, v in zip(domains, sums))


def _name(k, symbols):
    return contacts._name(k, symbols)


def _ring(atoms, symbols):
    return f'Cg({_name(atoms[0], symbols)}–{_name(atoms[-1], symbols)})'


def chain(domain, symbols):
    """'O1–H3···O4' (D–H···A), 'Cg(C1–C6)···Cg(C13–C18)' (stacking: the first and the last atom of each ring), 'Cg(C1–C6)'
    (a ring), 'C1···C4' (the main pair)."""
    if domain.site is not None and domain.donor is not None:
        return f'{_name(domain.donor, symbols)}–{_name(domain.site, symbols)}···{_name(domain.acceptor, symbols)}'
    if domain.kind == 'stacking':
        return f'{_ring(domain.sides[0], symbols)}···{_ring(domain.sides[1], symbols)}'
    if domain.kind == 'ring':
        return _ring(domain.sides[0], symbols)
    i, j = domain.atoms
    return f'{_name(i, symbols)}···{_name(j, symbols)}'


def label(domain, symbols):
    text = tr(NAMES[domain.kind])
    if domain.kind in contacts.ORDER or domain.kind == 'ch-pi':
        text += ' ' + chain(domain, symbols)
        if domain.kind == 'hydrogen' and domain.acceptor is not None and symbols[domain.acceptor] == 'C':
            text += ' (π)'
    return text


def detail(domain, symbols):
    lines = [chain(domain, symbols) + ': ' + tr(NAMES[domain.kind])]
    lines.append(tr(f'sign(λ₂)ρ в минимуме RDG {domain.peak:+.4f} а. е. — {tr(STRENGTHS[domain.strength])}').replace('-', '−'))
    lines.append(tr(f'объём {domain.volume:.2f} Å³; ∫ρ dV: притяжение {domain.attractive:.4f} e, '
                    f'отталкивание {domain.repulsive:.4f} e'))
    lines.append(tr(f'd = {domain.distance:.3f} Å'))
    if domain.angle is not None:
        lines.append(tr(f'угол {chain(domain, symbols)} {domain.angle:.1f}°'))
    if domain.point is not None:
        lines.append(tr(f'есть критическая точка связи (QTAIM), ρ = {domain.point.rho:.4f} а. е.'))
    if domain.energy is not None:
        lines.append(tr(f'E ≈ {domain.energy:.1f} ккал/моль ({tr(contacts.STRENGTHS[domain.grade])}; по ρ в минимуме '
                        f'RDG, Emamian 2019, точность ±15 %)'))
    if domain.dg is not None:
        lines.append(tr(f'IGMH: сумма δG пар атомов {domain.dg:.4f} а. е.'))
    if domain.kind == 'stacking':
        lines.append(tr(f'атомов в кольцах: {len(domain.sides[0])} и {len(domain.sides[1])}'))
    return '\n'.join(lines)


def table(domains, symbols):
    header = [tr('Тип'), tr('Атомы'), tr('sign(λ₂)ρ, а. е.'), tr('Сила'), tr('Объём, Å³'), tr('∫ρ притяж., e'),
              tr('∫ρ отталк., e'), 'd, Å', tr('Угол, °'), 'BCP', tr('E ≈, ккал/моль')]
    igmh = any(d.dg is not None for d in domains)
    if igmh:
        header.append(tr('δG пар, а. е.'))
    rows = []
    for d in domains:
        rows.append([tr(NAMES[d.kind]), chain(d, symbols), f'{d.peak:.4f}', tr(STRENGTHS[d.strength]),
                     f'{d.volume:.2f}', f'{d.attractive:.4f}', f'{d.repulsive:.4f}', f'{d.distance:.3f}',
                     '' if d.angle is None else f'{d.angle:.1f}', tr('да') if d.point is not None else tr('нет'),
                     '' if d.energy is None else f'{d.energy:.2f}'] + (['' if d.dg is None else f'{d.dg:.4f}'] if igmh else []))
    return header, rows

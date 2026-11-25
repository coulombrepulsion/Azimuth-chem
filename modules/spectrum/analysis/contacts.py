"""Weak (noncovalent) interactions named after a QTAIM search: hydrogen, halogen, chalcogen, pnictogen, tetrel bonds
and van der Waals contacts.

HEADER
    A bond critical point between two atoms says that the density has a saddle there, not what kind of interaction
    it is, and its absence does not rule one out (Lane et al., J. Phys. Chem. Lett. 2013, 4, 4107: the intramolecular
    O–H···O of ethane-1,2-diol has no BCP; Popelier, J. Mol. Model. 2022, 28, 276, §2.11). The kind is therefore given
    by the IUPAC definitions — an electrophilic site of one atom pointing at a nucleophile of another — from the
    geometry, and the BCP, when there is one, adds its numbers: the region of |V|/G (Espinosa et al., J. Chem. Phys.
    2002, 117, 5529) and, for a hydrogen bond only, an estimate of its energy from ρ_BCP (Emamian et al., J. Comput.
    Chem. 2019, 40, 2868). Wilkinson convention, sections 1-8.

§1 THEORY
    Hydrogen bond (IUPAC 2011): D–H···A, D more electronegative than H (Pauling χ > 2.20: C, N, O, F, S, Se, Cl, Br, I),
    A a lone pair or a π system. Halogen bond (IUPAC 2013): R–X···Y, X = Cl, Br, I, At, the σ-hole of X on the
    extension of R–X. Chalcogen (2019: S, Se, Te, Po), pnictogen (2023: P, As, Sb, Bi), tetrel (Si, Ge, Sn, Pb) bonds:
    the σ-hole opposite one of the bonds R–E of the atom. A hydrogen bond is also named at an angle under HB_ANGLE
    (down to HB_ANGLE_BCP) when a BCP joins H and the acceptor and its ρ and ∇²ρ are in the ranges of hydrogen bonds of
    Koch and Popelier (J. Phys. Chem. 1995, 99, 9747: ρ 0.002–0.034 au, ∇²ρ 0.024–0.139 au) — the bond path is the
    evidence the angle cannot give for an intramolecular bond closing a small ring (the methyl C–H···O=C of caffeine:
    2.25 Å, 107°). The nucleophile: N, O, F, P, S, Cl, As, Se, Br, Sb, Te, I, or
    an unsaturated carbon (fewer than four neighbours: a π system). Everything else close enough — a van der Waals
    contact (H···H, C···C of stacked rings …). Two atoms bonded covalently are a chemical bond.
    |V|/G at the BCP (Espinosa 2002): < 1 pure closed shell (H > 0), 1–2 the transit region (H < 0, ∇²ρ > 0),
    > 2 shared shell (covalent).
    Hydrogen-bond energy (Emamian 2019, CCSD(T) binding energies of 42 complexes, ρ at B3LYP-D3(BJ)/ma-TZVPP):
        neutral BE = −223.08 ρ_BCP + 0.7423 kcal/mol (MAPE 14.7 %),
        charged BE = −332.34 ρ_BCP − 1.0661 kcal/mol (MAPE 10.0 %);
    the classes: neutral — very weak |BE| < 2.5, weak to medium 2.5–14.0; charged — medium up to 15.0, strong > 15.0.
    BE ≈ V_BCP/2 (Espinosa 1998) is not used: its error is ~100 % on the same set (Emamian 2019). For halogen and other
    σ-hole bonds there is no general relation (Kuznetsov, Int. J. Quantum Chem. 2019, 119, e25869: only per pair of
    atoms, method and basis): no energy is given.
§2 ALGORITHM
    Covalent bonds: d ≤ BOND_FACTOR (Rcov_i + Rcov_j) (Cordero 2008 radii). The pairs looked at: every BCP with its two
    atoms, and every pair not bonded and more than three bonds apart (or in different molecules) with
    d ≤ Rvdw_i + Rvdw_j + TOLERANCE (Bondi; Mantina 2009 for the elements Bondi has not). A pair is tried in both
    directions (electrophilic site → nucleophile) for every kind, in the order hydrogen, halogen, chalcogen,
    pnictogen, tetrel; the first kind whose angle condition holds (D–H···A ≥ HB_ANGLE, R–E···Y ≥ HOLE_ANGLE for the
    neighbour R giving the largest angle) names it; for one kind the direction with the larger angle wins (a type II
    Br···Br contact is the halogen bond of the bromine whose C–Br points at the other).
§3 APPLICATIONS modules/spectrum/views/density_view.py: the column «Взаимодействие» of the detailed table of the points,
    the contacts without a BCP under it, the CSV table «<stem>_qtaim_contacts.csv» in «Анализ».
§4 SPECIFICATION
    classify(molecule, topology=None, charge=0) -> tuple of Contact, the BCP contacts first in the order of the
        topology, then those without a BCP by distance.
    Contact(kind 'covalent' | 'hydrogen' | 'halogen' | 'chalcogen' | 'pnictogen' | 'tetrel' | 'vdw', atoms (i, j)
        sorted, donor (R or D) | None, site (the H or the σ-hole atom) | None, acceptor | None, distance Å,
        vdw_sum Å, angle ° | None, point CriticalPoint | None, region 'closed' | 'transit' | 'shared' | None,
        energy kcal/mol | None, strength 'very weak' | 'weak-medium' | 'medium' | 'strong' | None, intra bool,
        by_bcp bool — a hydrogen bond named at an angle under HB_ANGLE for its BCP).
    by_point(contacts) -> {id(point): Contact}. label(contact, symbols) -> 'водородная O1–H3···O4' (translated).
    detail(contact, symbols) -> the criteria in words (a tooltip). table(contacts, symbols) -> (header, rows).
§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    BOND_FACTOR = 1.22 (as Compass draws bonds), TOLERANCE = 0.2 Å, HB_ANGLE = 120°, HOLE_ANGLE = 150° — the usual
    values of the literature, not of a definition (IUPAC gives no numbers); HB_ANGLE_BCP = 90° is ours: below it the H
    is beside its D–H bond rather than pointing at A. The sign of the electrostatic potential
    on the σ-hole is not checked here. The total charge decides the formula of the energy; a neutral pair inside an
    ion gets the charged one. The formula was fitted on intermolecular bonds: for an intramolecular one it is noted.
§7 TEST CASES (tests/spectrum/test_contacts.py)
    water dimer (S22): O–H···O, 174°, with a BCP of ρ 0.024 the energy −223.08·0.024 + 0.7423; the same contact found
    without a BCP; CF3Br···NH3 halogen; a type II Br···Br; (CH3)2S···O chalcogen; PF3···NH3 pnictogen; SiF4···NH3
    tetrel; CH4 dimer van der Waals; a bent C–Br···N (120°) is van der Waals; the BCP of a covalent O–H; a C–H···O at
    107° (as the methyl of caffeine) a hydrogen bond with a BCP in the ranges — not without one, nor with ρ or ∇²ρ out
    of them, nor at 85°.
§8 ERROR ANALYSIS
    The energy carries the MAPE of the fit (14.7 % neutral, 10 % charged) and grows for ρ from a poorer level than
    B3LYP-D3(BJ)/ma-TZVPP; the kind depends on the cutoffs above near their edges."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from math import acos, degrees, dist

from azimuth.i18n import tr
from modules.compass.chemistry.molecular_size import BONDI

BOND_FACTOR = 1.22
TOLERANCE = 0.2
HB_ANGLE = 120.0
HB_ANGLE_BCP = 90.0  # with a BCP of the ranges of Koch and Popelier (KP_RHO, KP_LAPLACIAN)
KP_RHO = (0.002, 0.034)  # au, Koch & Popelier, J. Phys. Chem. 1995, 99, 9747
KP_LAPLACIAN = (0.024, 0.139)
HOLE_ANGLE = 150.0
COVALENT = {'H': 0.31, 'Li': 1.28, 'Be': 0.96, 'B': 0.84, 'C': 0.76, 'N': 0.71, 'O': 0.66, 'F': 0.57, 'Na': 1.66,
            'Mg': 1.41, 'Al': 1.21, 'Si': 1.11, 'P': 1.07, 'S': 1.05, 'Cl': 1.02, 'K': 2.03, 'Ca': 1.76, 'Fe': 1.32,
            'Co': 1.26, 'Ni': 1.24, 'Cu': 1.32, 'Zn': 1.22, 'Ga': 1.22, 'Ge': 1.20, 'As': 1.19, 'Se': 1.20, 'Br': 1.20,
            'Pd': 1.39, 'Ag': 1.45, 'Cd': 1.44, 'In': 1.42, 'Sn': 1.39, 'Sb': 1.39, 'Te': 1.38, 'I': 1.39, 'Xe': 1.40,
            'Pt': 1.36, 'Au': 1.36, 'Hg': 1.32, 'Tl': 1.45, 'Pb': 1.46, 'Bi': 1.48, 'Po': 1.40, 'At': 1.50}  # Cordero 2008
VDW = {**BONDI, 'B': 1.92, 'Al': 1.84, 'Ge': 2.11, 'Sb': 2.06, 'Bi': 2.07, 'Po': 1.97, 'At': 2.02}  # + Mantina 2009
ELECTRONEGATIVE = {'C', 'N', 'O', 'F', 'S', 'Se', 'Cl', 'Br', 'I'}  # Pauling χ > 2.20 (H)
NUCLEOPHILES = {'N', 'O', 'F', 'P', 'S', 'Cl', 'As', 'Se', 'Br', 'Sb', 'Te', 'I'}
HOLES = (('halogen', {'Cl', 'Br', 'I', 'At'}), ('chalcogen', {'S', 'Se', 'Te', 'Po'}),
         ('pnictogen', {'P', 'As', 'Sb', 'Bi'}), ('tetrel', {'Si', 'Ge', 'Sn', 'Pb'}))
ORDER = ('hydrogen', 'halogen', 'chalcogen', 'pnictogen', 'tetrel')
NEUTRAL = (-223.08, 0.7423)  # Emamian 2019: BE = a ρ + b, kcal/mol
CHARGED = (-332.34, -1.0661)
# «ковалентная связь», not «химическая»
NAMES = {'covalent': 'ковалентная связь', 'hydrogen': 'водородная', 'halogen': 'галогенная', 'chalcogen': 'халькогенная',
         'pnictogen': 'пниктогенная', 'tetrel': 'тетрельная', 'vdw': 'ван-дер-ваальсов контакт'}
REGIONS = {'closed': 'замкнутые оболочки (|V|/G < 1)', 'transit': 'переходная область (1 < |V|/G < 2)',
           'shared': 'общая оболочка (|V|/G > 2)'}
STRENGTHS = {'very weak': 'очень слабая', 'weak-medium': 'слабая–средняя', 'medium': 'средняя', 'strong': 'сильная'}


@dataclass(frozen=True)
class Contact:
    kind: str
    atoms: tuple
    donor: int | None
    site: int | None
    acceptor: int | None
    distance: float
    vdw_sum: float
    angle: float | None
    point: object = None
    region: str | None = None
    energy: float | None = None
    strength: str | None = None
    intra: bool = False
    by_bcp: bool = False  # a hydrogen bond at an angle under HB_ANGLE, named for its BCP


def _angle(a, b, c):
    """The angle a–b–c, degrees."""
    u = [a[k] - b[k] for k in range(3)]
    v = [c[k] - b[k] for k in range(3)]
    nu, nv = sum(x * x for x in u) ** 0.5, sum(x * x for x in v) ** 0.5
    if nu < 1e-9 or nv < 1e-9:
        return 0.0
    return degrees(acos(max(-1.0, min(1.0, sum(x * y for x, y in zip(u, v)) / (nu * nv)))))


def _bonds(symbols, xyz):
    n = len(symbols)
    neighbours = [[] for _ in range(n)]
    for i in range(n):
        for j in range(i + 1, n):
            if dist(xyz[i], xyz[j]) <= BOND_FACTOR * (COVALENT.get(symbols[i], 1.5) + COVALENT.get(symbols[j], 1.5)):
                neighbours[i].append(j)
                neighbours[j].append(i)
    return neighbours


def _separation(neighbours, start, limit=4):
    """{atom: number of bonds from start} up to limit."""
    seen = {start: 0}
    queue = deque([start])
    while queue:
        k = queue.popleft()
        if seen[k] >= limit:
            continue
        for m in neighbours[k]:
            if m not in seen:
                seen[m] = seen[k] + 1
                queue.append(m)
    return seen


def _components(neighbours):
    group = [-1] * len(neighbours)
    for start in range(len(neighbours)):
        if group[start] < 0:
            group[start] = start
            stack = [start]
            while stack:
                k = stack.pop()
                for m in neighbours[k]:
                    if group[m] < 0:
                        group[m] = start
                        stack.append(m)
    return group


def _nucleophile(k, symbols, neighbours):
    return symbols[k] in NUCLEOPHILES or (symbols[k] == 'C' and len(neighbours[k]) < 4)


def _koch_popelier(point):
    """ρ and ∇²ρ of the BCP in the ranges of hydrogen bonds (Koch & Popelier 1995)."""
    return (point is not None and KP_RHO[0] <= point.rho <= KP_RHO[1]
            and KP_LAPLACIAN[0] <= point.laplacian <= KP_LAPLACIAN[1])


def _kind(e, n, symbols, xyz, neighbours, point=None):
    """(kind, donor, angle) of the electrophilic site e pointing at the nucleophile n, or None; point — the BCP of
    the pair (with it a hydrogen bond down to HB_ANGLE_BCP)."""
    if not _nucleophile(n, symbols, neighbours):
        return None
    if symbols[e] == 'H':
        donors = [d for d in neighbours[e] if symbols[d] in ELECTRONEGATIVE]
        best = max(((_angle(xyz[d], xyz[e], xyz[n]), d) for d in donors), default=None)
        if best is not None and (best[0] >= HB_ANGLE or best[0] >= HB_ANGLE_BCP and _koch_popelier(point)):
            return 'hydrogen', best[1], best[0]
        return None
    for kind, elements in HOLES:
        if symbols[e] in elements:
            best = max(((_angle(xyz[r], xyz[e], xyz[n]), r) for r in neighbours[e] if r != n), default=None)
            if best is not None and best[0] >= HOLE_ANGLE:
                return kind, best[1], best[0]
    return None


def _region(point):
    if point is None or not point.kinetic or point.kinetic <= 1e-12:
        return None
    ratio = abs(point.potential) / point.kinetic
    return 'closed' if ratio < 1 else 'transit' if ratio < 2 else 'shared'


def energy(rho, charged=False):
    """Emamian 2019: the binding energy of a hydrogen bond, kcal/mol, from ρ_BCP (au)."""
    a, b = CHARGED if charged else NEUTRAL
    return a * rho + b


def strength(value, charged=False):
    size = abs(value)
    if charged:
        return 'medium' if size <= 15.0 else 'strong'
    return 'very weak' if size < 2.5 else 'weak-medium'


def classify(molecule, topology=None, charge=0):
    atoms = [a for a in molecule.atoms]
    symbols = [a.symbol for a in atoms]
    xyz = [tuple(float(c) for c in a.position) for a in atoms]
    neighbours = _bonds(symbols, xyz)
    group = _components(neighbours)
    charged = bool(round(charge))
    pairs = []  # (i, j, point)
    seen = set()
    for point in getattr(topology, 'points', ()) if topology is not None else ():
        if point.kind == 'bond' and len(point.atoms) == 2:
            i, j = sorted(point.atoms)
            if 0 <= i < len(atoms) and 0 <= j < len(atoms) and (i, j) not in seen:
                seen.add((i, j))
                pairs.append((i, j, point))
    extra = []
    for i in range(len(atoms)):
        near = _separation(neighbours, i, 3)
        for j in range(i + 1, len(atoms)):
            if (i, j) in seen or j in near:
                continue
            d = dist(xyz[i], xyz[j])
            if d <= VDW.get(symbols[i], 1.8) + VDW.get(symbols[j], 1.8) + TOLERANCE:
                extra.append((d, i, j))
    pairs += [(i, j, None) for _, i, j in sorted(extra)]
    found = []
    for i, j, point in pairs:
        d = dist(xyz[i], xyz[j])
        vdw = VDW.get(symbols[i], 1.8) + VDW.get(symbols[j], 1.8)
        intra = group[i] == group[j]
        region = _region(point)
        if j in neighbours[i]:
            found.append(Contact('covalent', (i, j), None, None, None, d, vdw, None, point, region, intra=True))
            continue
        options = [(e, n, _kind(e, n, symbols, xyz, neighbours, point)) for e, n in ((i, j), (j, i))]
        options = [(ORDER.index(k[0]), -k[2], e, n, k) for e, n, k in options if k is not None]
        if not options:
            found.append(Contact('vdw', (i, j), None, None, None, d, vdw, None, point, region, intra=intra))
            continue
        _, _, e, n, (kind, donor, angle) = min(options)
        value = grade = None
        if kind == 'hydrogen' and point is not None:
            value = energy(point.rho, charged)
            grade = strength(value, charged)
        found.append(Contact(kind, (i, j), donor, e, n, d, vdw, angle, point, region, value, grade, intra,
                             kind == 'hydrogen' and angle < HB_ANGLE))
    return tuple(found)


def by_point(contacts):
    return {id(c.point): c for c in contacts if c.point is not None}


def _name(k, symbols):
    return f'{symbols[k]}{k + 1}' if k is not None and 0 <= k < len(symbols) else ''


def chain(contact, symbols):
    """'O1–H3···O4' (D–H···A, R–X···Y) or 'H5···H9'."""
    if contact.site is None:
        i, j = contact.atoms
        joint = '–' if contact.kind == 'covalent' else '···'
        return _name(i, symbols) + joint + _name(j, symbols)
    return f'{_name(contact.donor, symbols)}–{_name(contact.site, symbols)}···{_name(contact.acceptor, symbols)}'


def label(contact, symbols):
    text = tr(NAMES[contact.kind])
    if contact.kind in ORDER:
        text += ' ' + chain(contact, symbols)
        if contact.acceptor is not None and symbols[contact.acceptor] == 'C':
            text += ' (π)'
    return text


def detail(contact, symbols):
    lines = [chain(contact, symbols) + ': ' + tr(NAMES[contact.kind])]
    lines.append(tr(f'd = {contact.distance:.3f} Å, сумма ван-дер-ваальсовых радиусов {contact.vdw_sum:.2f} Å'))
    if contact.angle is not None:
        lines.append(tr(f'угол {chain(contact, symbols)} {contact.angle:.1f}°'))
    if contact.by_bcp:
        lines.append(tr('Угол меньше {}°: водородная связь по критической точке — ρ и ∇²ρ в пределах водородных связей '
                        '(Koch, Popelier 1995).').format(f'{HB_ANGLE:.0f}'))
    if contact.region is not None:
        lines.append(tr(REGIONS[contact.region]))
    if contact.point is None and contact.kind != 'covalent':
        lines.append(tr('Критической точки связи нет: по геометрии (её отсутствие не исключает взаимодействия).'))
    if contact.energy is not None:
        lines.append(tr(f'E ≈ {contact.energy:.1f} ккал/моль ({tr(STRENGTHS[contact.strength])}; по ρ, Emamian 2019, '
                        f'точность ±15 %)'))
        if contact.intra:
            lines.append(tr('Формула получена для межмолекулярных связей.'))
    if contact.kind in ('halogen', 'chalcogen', 'pnictogen', 'tetrel'):
        lines.append(tr('σ-дырка по геометрии; знак потенциала на ней не проверялся. Энергию по ρ для таких связей '
                        'надёжно не оценить.'))
    return '\n'.join(lines)


def table(contacts, symbols):
    header = [tr('Тип'), tr('Атомы'), 'd, Å', tr('Σ r(вдВ), Å'), tr('Угол, °'), 'BCP', 'ρ', '|V|/G',
              tr('E ≈, ккал/моль')]
    rows = []
    for c in contacts:
        if c.kind == 'covalent':
            continue
        p = c.point
        ratio = abs(p.potential) / p.kinetic if p is not None and p.kinetic and p.kinetic > 1e-12 else None
        rows.append([tr(NAMES[c.kind]), chain(c, symbols), f'{c.distance:.3f}', f'{c.vdw_sum:.2f}',
                     '' if c.angle is None else f'{c.angle:.1f}', tr('да') if p is not None else tr('нет'),
                     '' if p is None else f'{p.rho:.5f}', '' if ratio is None else f'{ratio:.3f}',
                     '' if c.energy is None else f'{c.energy:.2f}'])
    return header, rows

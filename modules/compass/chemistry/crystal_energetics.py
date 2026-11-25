"""The ionic picture of a crystal: oxidation states, the Madelung energy, bond valence sums, Shannon radii
and Pauling's rules, the packing of the ions, the cell computed against the cell of the file.

§1 THEORY
    An ionic crystal is taken as point charges q_i e (the formal oxidation states, or the charges of a calculation).
    The electrostatic energy of a cell E = ½ Σ_i q_i φ_i, φ_i = k_e Σ'_{j,n} q_j / |r_i − r_j − n| (n — the lattice
    vectors, k_e = e²/(4πε₀) = 14.399645 eV·Å); the sum converges only conditionally and is taken by Ewald's method:
        φ_i = Σ'_{j,n} q_j erfc(η r)/r + (4π/V) Σ_{k≠0} exp(−k²/4η²)/k² Σ_j q_j cos(k·r_ij) − 2η q_i/√π,
    exact for any η (the tests check that two η give one sum). For a binary salt AₘXₙ the Madelung constant
    M = −E_fu r₀ / (k_e |z₊ z₋|) (r₀ — the shortest cation–anion distance, E_fu — per formula unit); CsCl 1.762675,
    NaCl 1.747565 (Kittel, Introduction to Solid State Physics, ch. 3), CaF2 2.51939.
    Bond valence (Brown & Altermatt, Acta Cryst. B41, 244, 1985): s = exp((R₀ − R)/b), the sum over the counter-ions of
    an ion V = Σ s should be its |oxidation state|; R₀, b — the IUCr table bvparm2020 (I. D. Brown). The global
    instability index GII = √(mean (V − |q|)²) over the atoms of the cell: below 0.1 v.u. — an unstrained structure,
    above 0.2 — a strained or wrong one (Salinas-Sanchez et al., J. Solid State Chem. 100, 201, 1992).
    Shannon's effective ionic radii (Acta Cryst. A32, 751, 1976) depend on the charge and the coordination number.
    Pauling's first rule: the radius ratio r₊/r₋ sets the coordination of the cation — < 2, < 3,
    < 4, < 6, < 1: 8, ≥ 1: 12; the second (electrostatic valence): Σ z₊/CN₊ of the cations around an
    anion equals |z₋|. Goldschmidt's tolerance factor of a perovskite ABX₃ t = (r_A + r_X) / (√2 (r_B + r_X)):
    0.9–1 cubic (to 1.02: SrTiO₃ 1.00), 0.71–0.9 distorted (orthorhombic, rhombohedral), > 1 the ion A too large
    (hexagonal polytypes, or the ion B off centre — ferroelectric BaTiO₃ 1.06). The ionic packing fraction —
    Σ 4/3 π r³ of the ions over the cell volume (the spheres are taken as not overlapping).
§2 ALGORITHM oxidation_states(crystal): one state per element from the tables (data/oxidation_states.json: the common
    states first, then those of the ICSD, four per element), the cell neutral, every anion more electronegative
    (Pauling) than every cation; the smallest sum of the places in the lists wins. A molecular crystal (C and H) is
    refused. neighbours(crystal, cutoff): the atoms of the cell (crystal.unit_cell) and their images in the cells around
    within cutoff. madelung(crystal, charges): Ewald with η = √π (N/V²)^(1/6), the real sum to erfc(ηr) < 1e-12, the
    reciprocal to exp(−k²/4η²) < 1e-12. bond_valences(crystal, states): for each atom the counter-ions within R₀ + b ln
    100 (s ≥ 0.01). radii(crystal, states): the coordination of a cation — anions within 1.2 × its shortest such
    distance, of an anion — the cations that count it so; Shannon's radius at that number (the nearest number of the
    table if it is missing, said so; high spin first). compare(file, computed): the cells and the density.
§4 SPECIFICATION
    oxidation_states(crystal) -> {symbol: int} (ValueError when none is neutral); madelung(crystal, charges=None) ->
    Madelung; bond_valences(crystal, states=None) -> BondValences; radii(crystal, states=None) -> Radii;
    packing(crystal, states=None) -> Packing; compare(file, computed) -> [(name, file, computed, difference, unit)].
§6 NOTES
    Partial occupancies: the first disorder part (crystal.main_part); the atoms are taken as wholly there.
§7 TESTS
    tests/compass/test_crystal_energetics.py — CsCl, NaCl, CaF2 against the textbook constants, η-independence,
    BVS of NaCl and BaTiO3, Pauling's rule, the tolerance factor of SrTiO3 and BaTiO3.
"""

from dataclasses import dataclass
from functools import lru_cache
from itertools import product
import json
from math import erfc, exp, log, pi, sqrt
from pathlib import Path

from azimuth.i18n import tr

K_E = 14.399645  # eV·Å, e²/(4πε₀)
EV_KJ = 96.485332  # kJ/mol per eV
DATA = Path(__file__).with_name('data')
SHELL = 1.2  # the coordination shell: counter-ions within 1.2 × the shortest distance
CHOICES = 4  # states tried per element


@lru_cache(maxsize=None)
def _table(name):
    return json.loads((DATA / name).read_text(encoding='utf-8'))


def _atoms(crystal):
    from modules.compass.chemistry import crystal as cr

    return cr.unit_cell(cr.main_part(crystal))


def _counts(crystal):
    counts = {}
    for atom in _atoms(crystal):
        counts[atom[0]] = counts.get(atom[0], 0) + 1
    return counts


def ionic_problem(crystal):
    """Why the ionic model (oxidation states, Madelung with formal charges, bond valences, Pauling) does not apply to
    the crystal — a text — or None. The menus grey out
    what it needs by this, before a click. A crystal with C and H has molecules or organic ions (calcium formate: the
    formate ion) — formal charges of its atoms mean nothing."""
    counts = _counts(crystal)
    if not counts:
        return tr('В ячейке нет атомов.')
    if len(counts) == 1:
        return tr('Простое вещество: ионов нет, ионная модель (степени окисления, Маделунг, валентности '
                  'связей) к нему не применима.')
    if 'C' in counts and 'H' in counts:
        return tr('В кристалле органические молекулы или ионы (есть C и H): ионная модель (степени окисления, '
                  'Маделунг, валентности связей) к нему не применима.')
    from modules.compass.chemistry.crystal_symmetry import NONMETALS

    if all(s in NONMETALS for s in counts):  # e.g. C6Cl6: no H, yet molecular
        return tr('В кристалле нет металлов — он молекулярный или ковалентный: ионная модель (степени окисления, '
                  'Маделунг, валентности связей) к нему не применима.')
    return None


def oxidation_states(crystal):
    """{symbol: formal oxidation state} that make the cell neutral."""
    from modules.compass.chemistry.crystal_symmetry import PAULING

    counts = _counts(crystal)
    problem = ionic_problem(crystal)
    if problem:
        raise ValueError(problem)
    states = _table('oxidation_states.json')['states']
    options = {}
    for symbol in counts:
        known = states.get(symbol) or {}
        listed = list(known.get('common') or []) + [q for q in known.get('icsd') or [] if q not in (known.get('common') or [])]
        listed = [q for q in listed if q != 0][:CHOICES]
        if not listed:
            raise ValueError(tr('Нет степеней окисления для {}.').format(symbol))
        options[symbol] = listed
    symbols = list(counts)
    best = None
    for combo in product(*(range(len(options[s])) for s in symbols)):
        q = {s: options[s][i] for s, i in zip(symbols, combo)}
        if sum(counts[s] * q[s] for s in symbols) != 0:
            continue
        cations = [PAULING.get(s, 2.0) for s in symbols if q[s] > 0]
        anions = [PAULING.get(s, 2.0) for s in symbols if q[s] < 0]
        if not cations or not anions or max(cations) >= min(anions):
            continue
        score = sum(combo)
        if best is None or score < best[0]:
            best = (score, q)
    if best is None:
        raise ValueError(tr('Не удалось подобрать степени окисления, при которых ячейка нейтральна (смешанная '
                            'валентность, интерметаллид или металл).'))
    return best[1]


def ion_name(symbol, q):
    sign = '+' if q > 0 else '−'
    return f'{symbol}{abs(q) if abs(q) != 1 else ""}{sign}'


def _rows(crystal):
    import numpy as np

    return np.array(crystal.cell.vectors(), dtype=float)


def neighbours(crystal, cutoff):
    """[(i, j, distance)] over the atoms of the cell, j counted with its images (i ≠ j or another image)."""
    import numpy as np

    atoms = _atoms(crystal)
    rows = _rows(crystal)
    frac = np.array([a[1:4] for a in atoms], dtype=float)
    lengths = np.linalg.norm(rows, axis=1)
    volume = abs(np.linalg.det(rows))
    heights = [volume / np.linalg.norm(np.cross(rows[(k + 1) % 3], rows[(k + 2) % 3])) for k in range(3)]
    reach = [int(np.ceil(cutoff / h)) + 1 for h in heights]
    shifts = np.array([(i, j, k) for i in range(-reach[0], reach[0] + 1) for j in range(-reach[1], reach[1] + 1)
                       for k in range(-reach[2], reach[2] + 1)], dtype=float)
    found = []
    cart = frac @ rows
    images = (frac[None, :, :] + shifts[:, None, :]).reshape(-1, 3) @ rows
    n = len(atoms)
    for i in range(n):
        d = np.linalg.norm(images - cart[i], axis=1)
        for m in np.nonzero((d > 1e-6) & (d <= cutoff))[0]:
            found.append((i, int(m % n), float(d[m])))
    del lengths
    return atoms, found


# -- the Madelung energy ---------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Madelung:
    energy_cell: float  # eV
    energy_unit: float  # eV per formula unit
    units: int  # formula units in the cell
    formula: str
    constant: float | None  # binary salts: M = −E_fu r₀ / (k_e |z₊ z₋|)
    shortest: float  # r₀, Å
    sites: tuple  # (label, symbol, charge, potential V), one per site of the asymmetric unit
    charges: str  # how the charges were taken


def ewald(crystal, charges, eta=None):
    """(energy of the cell eV, potentials V at the atoms) for charges — one per atom of crystal.unit_cell."""
    import numpy as np

    atoms = _atoms(crystal)
    q = np.array(charges, dtype=float)
    if len(q) != len(atoms):
        raise ValueError('one charge per atom of the cell')
    if abs(q.sum()) > 1e-6 * max(1.0, np.abs(q).sum()):
        raise ValueError(tr('Сумма зарядов ячейки не ноль ({}): энергия Маделунга заряженной ячейки не определена.')
                         .format(f'{q.sum():+.3f}'))
    rows = _rows(crystal)
    volume = abs(np.linalg.det(rows))
    n = len(atoms)
    eta = float(eta or sqrt(pi) * (n / volume ** 2) ** (1 / 6))
    accuracy = sqrt(-log(1e-12))  # erfc(x) ~ exp(-x²)
    r_cut = accuracy / eta
    k_cut = 2 * eta * accuracy
    frac = np.array([a[1:4] for a in atoms], dtype=float)
    cart = frac @ rows
    heights = [volume / np.linalg.norm(np.cross(rows[(k + 1) % 3], rows[(k + 2) % 3])) for k in range(3)]
    reach = [int(np.ceil(r_cut / h)) + 1 for h in heights]
    shifts = np.array([(i, j, k) for i in range(-reach[0], reach[0] + 1) for j in range(-reach[1], reach[1] + 1)
                       for k in range(-reach[2], reach[2] + 1)], dtype=float) @ rows
    verfc = np.vectorize(erfc)
    phi = np.zeros(n)
    for i in range(n):
        d = (cart[None, :, :] + shifts[:, None, :] - cart[i]).reshape(-1, 3)
        r = np.linalg.norm(d, axis=1)
        qj = np.tile(q, len(shifts))
        keep = (r > 1e-8) & (r < r_cut)
        phi[i] += float((qj[keep] * verfc(eta * r[keep]) / r[keep]).sum())
    recip = 2 * pi * np.linalg.inv(rows).T  # rows of the reciprocal lattice (with 2π)
    kreach = [int(np.ceil(k_cut / np.linalg.norm(recip[k]))) for k in range(3)]
    ks = np.array([(i, j, k) for i in range(-kreach[0], kreach[0] + 1) for j in range(-kreach[1], kreach[1] + 1)
                   for k in range(-kreach[2], kreach[2] + 1) if (i, j, k) != (0, 0, 0)], dtype=float) @ recip
    k2 = (ks ** 2).sum(axis=1)
    ks, k2 = ks[k2 < k_cut ** 2], k2[k2 < k_cut ** 2]
    weight = np.exp(-k2 / (4 * eta * eta)) / k2
    phase = ks @ cart.T  # (k, atom)
    s_cos = np.cos(phase) @ q
    s_sin = np.sin(phase) @ q
    phi += (4 * pi / volume) * ((np.cos(phase) * (weight * s_cos)[:, None]).sum(axis=0)
                                + (np.sin(phase) * (weight * s_sin)[:, None]).sum(axis=0))
    phi -= 2 * eta * q / sqrt(pi)
    phi *= K_E
    return 0.5 * float((q * phi).sum()), phi


def _formula_units(crystal):
    from math import gcd

    counts = _counts(crystal)
    g = 0
    for c in counts.values():
        g = gcd(g, c)
    return max(1, g)


def madelung(crystal, charges=None, how=''):
    """charges: {symbol: q} or one per atom of the cell; None — the formal oxidation states."""
    from modules.compass.chemistry.crystal_symmetry import empirical_formula

    atoms = _atoms(crystal)
    if charges is None:
        states = oxidation_states(crystal)
        charges = states
        how = how or tr('формальные степени окисления')
    per_atom = [charges[a[0]] for a in atoms] if isinstance(charges, dict) else list(charges)
    energy, phi = ewald(crystal, per_atom)
    units = _formula_units(crystal)
    _, pairs = neighbours(crystal, 6.0)
    opposite = [d for i, j, d in pairs if per_atom[i] * per_atom[j] < 0]
    shortest = min(opposite) if opposite else 0.0
    constant = None
    if isinstance(charges, dict) and len(charges) == 2 and shortest:
        zp, zm = max(charges.values()), min(charges.values())
        constant = -energy / units * shortest / (K_E * abs(zp * zm))
    sites, seen = [], set()
    for k, atom in enumerate(atoms):
        if atom[4] in seen:
            continue
        seen.add(atom[4])
        sites.append((atom[4], atom[0], float(per_atom[k]), float(phi[k])))
    return Madelung(energy, energy / units, units, empirical_formula(crystal), constant, shortest, tuple(sites), how)


# -- bond valence sums -----------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class BondValences:
    sites: tuple  # (label, ion, |q|, V, bonds: ((ion, R Å, s), …)) per site of the asymmetric unit
    gii: float
    missing: tuple  # the pairs without parameters ('Cs+1|Cl-1', …)


def _key(a, qa, b, qb):
    return f'{a}{qa:+d}|{b}{qb:+d}'


def bond_valences(crystal, states=None):
    states = states or oxidation_states(crystal)
    pairs = _table('bond_valence.json')['pairs']
    atoms, found = neighbours(crystal, 4.5)
    table = {}
    missing = set()
    for i, j, d in found:
        a, b = atoms[i][0], atoms[j][0]
        qa, qb = states[a], states[b]
        if qa * qb >= 0:
            continue
        key = _key(a, qa, b, qb) if qa > 0 else _key(b, qb, a, qa)
        if key not in pairs:
            missing.add(key)
            continue
        r0, b_, _ = pairs[key]
        if d > r0 + b_ * log(100):
            continue
        table.setdefault(i, []).append((ion_name(b, qb), d, exp((r0 - d) / b_)))
    sums = [sum(s for *_, s in table.get(i, [])) for i in range(len(atoms))]
    deviations = [(sums[i] - abs(states[a[0]])) ** 2 for i, a in enumerate(atoms)]
    gii = sqrt(sum(deviations) / len(deviations)) if deviations else 0.0
    sites, seen = [], set()
    for i, atom in enumerate(atoms):
        if atom[4] in seen:
            continue
        seen.add(atom[4])
        bonds = tuple(sorted(table.get(i, []), key=lambda x: x[1]))
        sites.append((atom[4], ion_name(atom[0], states[atom[0]]), abs(states[atom[0]]), sums[i], bonds))
    return BondValences(tuple(sites), gii, tuple(sorted(missing)))


# -- Shannon radii and Pauling's rules -------------------------------------------------------------------------------
PAULING_RATIOS = ((0.155, 2), (0.225, 3), (0.414, 4), (0.732, 6), (1.0, 8))


def predicted_cn(ratio):
    for limit, cn in PAULING_RATIOS:
        if ratio < limit:
            return cn
    return 12


def shannon(symbol, q, cn):
    """(radius Å, the coordination number of the table used) or None; high spin first."""
    radii = (_table('shannon_radii.json')['radii'].get(symbol) or {}).get(str(q))
    if not radii:
        return None
    numbers = {}
    for key, r in radii.items():
        digits = ''.join(ch for ch in key if ch.isdigit())
        if not digits:
            continue
        number = int(digits)
        rank = 0 if key == digits else 1 if 'hs' in key and 'sq' not in key else 2
        if number not in numbers or rank < numbers[number][0]:
            numbers[number] = (rank, r)
    if not numbers:
        return None
    near = min(numbers, key=lambda n: (abs(n - cn), -n))
    return numbers[near][1], near


@dataclass(frozen=True)
class Radii:
    ions: tuple  # (ion, CN observed, r Å, CN of the table) per element
    pairs: tuple  # (cation, anion, r₊/r₋, CN predicted, CN observed, r₊ + r₋, the shortest distance)
    electrostatic: tuple  # (anion label, Σ z₊/CN₊, |z₋|)
    tolerance: float | None  # Goldschmidt t for ABX₃
    tolerance_text: str


def _coordination(crystal, states):
    """{atom: [(counter-ion, distance)]}: a cation — the anions within SHELL × its shortest cation–anion distance; an
    anion — the cations that have it in their shells (the O of a perovskite: 2 Ti and 4 Ba, though Ba is farther)."""
    atoms, found = neighbours(crystal, 5.0)
    near = {}
    for i, j, d in found:
        if states[atoms[i][0]] > 0 > states[atoms[j][0]]:
            near.setdefault(i, []).append((j, d))
    shells = {}
    for i, pairs in near.items():
        r_min = min(d for _, d in pairs)
        shells[i] = [(j, d) for j, d in pairs if d <= SHELL * r_min]
        for j, d in shells[i]:
            shells.setdefault(j, []).append((i, d))
    return atoms, shells


def radii(crystal, states=None):
    states = states or oxidation_states(crystal)
    atoms, shells = _coordination(crystal, states)
    by_element = {}
    for i, atom in enumerate(atoms):
        by_element.setdefault(atom[0], []).append(len(shells.get(i, [])))
    ions = []
    radius = {}
    for symbol, numbers in by_element.items():
        cn = max(set(numbers), key=numbers.count)
        found = shannon(symbol, states[symbol], cn)
        radius[symbol] = found[0] if found else None
        ions.append((ion_name(symbol, states[symbol]), cn, found[0] if found else None, found[1] if found else None))
    pairs = []
    cations = [s for s in by_element if states[s] > 0]
    anions = [s for s in by_element if states[s] < 0]
    for c in cations:
        for a in anions:
            distances = [d for i, near in shells.items() if atoms[i][0] == c for j, d in near if atoms[j][0] == a]
            if not distances or not radius.get(c) or not radius.get(a):
                continue
            ratio = radius[c] / radius[a]
            observed = max(set(by_element[c]), key=by_element[c].count)
            pairs.append((ion_name(c, states[c]), ion_name(a, states[a]), ratio, predicted_cn(ratio), observed,
                          radius[c] + radius[a], min(distances)))
    electrostatic, seen = [], set()
    for i, atom in enumerate(atoms):
        if states[atom[0]] >= 0 or atom[4] in seen:
            continue
        seen.add(atom[4])
        total = 0.0
        for j, _ in shells.get(i, []):
            cn = len(shells.get(j, [])) or 1
            total += states[atoms[j][0]] / cn
        electrostatic.append((atom[4], total, abs(states[atom[0]])))
    tolerance, text = _tolerance(crystal, states)
    return Radii(tuple(ions), tuple(pairs), tuple(electrostatic), tolerance, text)


def _tolerance(crystal, states):
    counts = _counts(crystal)
    g = _formula_units(crystal)
    unit = {s: n // g for s, n in counts.items()}
    anions = [s for s in unit if states[s] < 0]
    cations = [s for s in unit if states[s] > 0]
    if len(unit) != 3 or len(anions) != 1 or unit[anions[0]] != 3 or len(cations) != 2 or any(unit[s] != 1 for s in cations):
        return None, tr('Фактор толерантности Гольдшмидта — для перовскитов ABX₃; у этого кристалла другой состав.')
    x = anions[0]
    a, b = sorted(cations, key=lambda s: -(shannon(s, states[s], 12) or (0,))[0])
    ra, rb, rx = shannon(a, states[a], 12), shannon(b, states[b], 6), shannon(x, states[x], 6)
    if not (ra and rb and rx):
        return None, tr('Нет радиусов Шеннона для этих ионов.')
    t = (ra[0] + rx[0]) / (sqrt(2) * (rb[0] + rx[0]))
    if t > 1.02:
        kind = tr('больше 1 — ион A велик: гексагональные политипы (BaNiO₃) или смещение иона B (сегнетоэлектрик BaTiO₃)')
    elif t >= 0.9:
        kind = tr('0,9–1 — кубический перовскит')
    elif t >= 0.71:
        kind = tr('0,71–0,9 — искажённый перовскит (ромбический, ромбоэдрический)')
    else:
        kind = tr('меньше 0,71 — перовскит неустойчив (ильменит и другие структуры)')
    text = tr('A = {}, B = {}, X = {}: t = ({} + {}) / (√2 · ({} + {})) = {} — {}').format(
        ion_name(a, states[a]), ion_name(b, states[b]), ion_name(x, states[x]), f'{ra[0]:.3f}', f'{rx[0]:.3f}',
        f'{rb[0]:.3f}', f'{rx[0]:.3f}', f'{t:.3f}', kind)
    return t, text


# -- packing ---------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Packing:
    density: float  # g/cm³
    volume: float  # Å³ of the cell
    volume_unit: float  # Å³ per formula unit
    ionic: float | None  # the ionic packing fraction
    vdw: float  # Kitaigorodsky's coefficient (van der Waals spheres)


def packing(crystal, states=None):
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_symmetry as cs

    part = cr.main_part(crystal)
    volume = part.cell.volume()
    density = cs.analyse(part).density
    ionic = None
    try:
        states = states or oxidation_states(part)
        atoms, shells = _coordination(part, states)
        total = 0.0
        for i, atom in enumerate(atoms):
            r = shannon(atom[0], states[atom[0]], len(shells.get(i, [])) or 6)
            if r is None:
                total = None
                break
            total += 4 / 3 * pi * r[0] ** 3
        ionic = total / volume if total is not None else None
    except ValueError:
        pass
    return Packing(density, volume, volume / _formula_units(part), ionic, cs.packing_coefficient(part))


# -- the cell computed against the cell of the file ------------------------------------------------------------------
def compare(file, computed):
    """[(name, file, computed, difference, unit)]; the volume and the density per formula unit when the cells differ."""
    from modules.compass.chemistry import crystal_symmetry as cs

    rows = []
    one, two = file.cell, computed.cell
    units_one, units_two = _formula_units(file), _formula_units(computed)
    if units_one == units_two:
        for name, x, y in (('a', one.a, two.a), ('b', one.b, two.b), ('c', one.c, two.c)):
            rows.append((name, x, y, 100 * (y / x - 1), 'Å'))
        for name, x, y in (('α', one.alpha, two.alpha), ('β', one.beta, two.beta), ('γ', one.gamma, two.gamma)):
            rows.append((name, x, y, y - x, '°'))
    v1, v2 = one.volume() / units_one, two.volume() / units_two
    rows.append((tr('V на формульную единицу'), v1, v2, 100 * (v2 / v1 - 1), 'Å³'))
    d1, d2 = cs.analyse(file).density, cs.analyse(computed).density
    if d1 and d2:
        rows.append((tr('плотность'), d1, d2, 100 * (d2 / d1 - 1), 'г/см³'))
    return rows


# -- labels on the model --------------------------------------------------------------------------------
# «Подписи на модели» of a crystal: what the structure itself gives: the oxidation states, the
# bond valence sums, the fractional coordinates, the site (its label in the file, its multiplicity, its symmetry).
LABELS = ('oxidation', 'bvs', 'fractional', 'site')


def site_symmetry(crystal):
    """{site label: (multiplicity in the cell, the point group of the site)}: the operations that keep the site (mod the
    lattice; a centring translation does not), their rotations — crystal_symmetry.point_group."""
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_symmetry as cs

    found = {}
    for site in crystal.sites:
        f = (site.x, site.y, site.z)
        keep = set()
        images = []
        for op in crystal.operations:
            g = cr._apply(op, f)
            if cr._separation(crystal.cell, cr._wrap(g), cr._wrap(f)) <= cr.MERGE:
                keep.add(op[0])
            w = cr._wrap(g)
            if all(cr._separation(crystal.cell, w, h) > cr.MERGE for h in images):
                images.append(w)
        group = cs.point_group(keep)
        found[site.label] = (len(images), group[0] if group else '?')
    return found


def _ion_text(q):
    return f'{q:+d}'.replace('-', '−') if q else '0'


def _fraction_text(x):
    x = 0.0 if abs(x) < 5e-4 else x
    text = f'{x:.3f}'.rstrip('0').rstrip('.')
    return text.replace('-', '−') or '0'


def model_labels(crystal, positions, key):
    """One label per point of the model (Cartesian, the cell at the origin) — str or float; None for a point that is no
    atom of the cell. ValueError when the ionic model does not apply (oxidation, bvs)."""
    import numpy as np

    from modules.compass.chemistry import crystal as cr

    part = cr.main_part(crystal)
    atoms = _atoms(part)
    rows = _rows(part)
    inverse = np.linalg.inv(rows)
    cell = np.array([a[1:4] for a in atoms], dtype=float)
    per_label = {}
    if key == 'oxidation':
        states = oxidation_states(part)
        per_label = {a[4]: _ion_text(states[a[0]]) for a in atoms}
    elif key == 'bvs':
        per_label = {label: round(total, 2) for label, _, _, total, _ in bond_valences(part).sites}
    elif key == 'site':
        symmetry = site_symmetry(part)
        per_label = {label: f'{label} · {n} · {group}' for label, (n, group) in symmetry.items()}
    out = []
    for symbol, position in positions:
        f = np.array(position, dtype=float) @ inverse
        d = cell - (f - np.floor(f + 1e-9))
        d -= np.round(d)
        dist = np.linalg.norm(d @ rows, axis=1)
        k = int(np.argmin(dist)) if len(dist) else -1
        if k < 0 or dist[k] > cr.MERGE or atoms[k][0] != symbol:
            out.append(None)
        elif key == 'fractional':
            out.append(' '.join(_fraction_text(x) for x in f))
        else:
            out.append(per_label.get(atoms[k][4]))
    return out

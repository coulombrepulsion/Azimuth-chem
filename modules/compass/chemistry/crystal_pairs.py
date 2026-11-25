"""The interaction energies of a molecule with its neighbours in a crystal, the lattice energy and the energy
framework (as CrystalExplorer's «interaction energies» and «energy frameworks», here with GFN2-xTB).

§1 THEORY
    A molecular crystal is held together by the interactions of its molecules. The pair energy of the molecule A and
    a neighbour B, E_int = E(AB) − E(A) − E(B), at the geometry of the crystal (no relaxation); the lattice energy is
    then approximately half the sum over the neighbours of one molecule (each pair belongs to two molecules):
        E_latt ≈ ½ Σ_B E_int(A, B) (Gavezzotti; Thomas, Spackman et al., J. Phys. Chem. Lett. 9, 2018: with the
    neighbours within 3.8 Å, the atom–atom distance CrystalExplorer uses). Its negative is the sublimation enthalpy at
    0 K without the vibrations: for benzoic acid about −90 kJ/mol (ΔH_sub ≈ 90 kJ/mol). GFN2-xTB (Bannwarth, Ehlert &
    Grimme 2019) has electrostatics, exchange and the D4 dispersion: fast and good for the order and the pattern of the
    pair energies, about 10–20 % on their size. The energy framework: a cylinder between the centroids of A and B with
    the thickness growing with |E_int| — the topology of the strong pairs (columns, layers, a 3-D frame) seen at once.
§2 ALGORITHM
    The shell (crystal_shell.shell, the distance radius 3.8 Å) gives the neighbours with their codes; the centroid of
    each is taken from its atoms. A monomer energy for each component of the cell met (the copies of one molecule by
    symmetry have one energy), a dimer energy for each pair of a different kind: the pairs of the same components at
    the same centroid distance and the same shortest contact (within 0.001 Å) are one (the symmetry repeats them), the
    energy computed once and given to all. The energies come from energy(molecule) -> hartree — xtb in the window
    (run_xtb), a model function in the tests. E in kJ/mol = ΔE (hartree) × 2625.4996.
§3 APPLICATIONS
    modules/compass/actions/pairs_window.py: «Кристалл → Энергии пар и каркас (xtb)…».
§4 SPECIFICATION
    plan(crystal, centre=None, radius=RADIUS, factor=None) -> Plan(shell, monomers {component: Molecule},
        dimers [(key, Molecule)], of [key of each neighbour], centroids (centre, [of each neighbour])).
    compute(plan, energy, progress=None) -> Result(pairs [Pair(neighbour, distance (centroids, Å), energy kJ/mol)],
        lattice kJ/mol, calculations (the number of energies asked)); progress(done, total) is called after each.
    frame(result, centre_point, neighbour_points) -> [(a, b, width 0–1, attractive)] — the cylinders of the framework.
    run_xtb(program, molecule, folder, timeout=600, charge=0, terms=False) -> hartree (subprocess: xtb mol.xyz
        --gfn 2 --sp --chrg q [--uhf 1 for an odd number of electrons]), with terms=True a dict of the terms of
        GFN2 (terms_of); ValueError when xtb gives no energy.
    energy_of(output text) -> hartree | None ('TOTAL ENERGY … Eh' of xtb).
    Terms_of(output text) -> {'total', 'es', 'xc', 'disp', 'rep'} (hartree) | None — the SUMMARY of xtb:
        isotropic + anisotropic ES, anisotropic XC, dispersion, repulsion energy.
        Pair.terms {'es', 'disp', 'rep', 'rest'} kJ/mol (the energy of each the difference AB − A − B; rest = E_int −
        the three: the rest of the SCC energy — polarisation, exchange, charge transfer, the XC of GFN2) | None.
        guess_charges(crystal, factor=None) -> Charges(by_formula {formula: q}, counts {formula: n in the cell},
        components {component: formula}, known {formula: bool}, balanced: bool).
        plan(…, charges=None) — charges {formula: q} (None: guess_charges); compute calls energy(molecule) for a
        neutral molecule and energy(molecule, charge) for a charged one.
§5 PROCEDURES - below.
§6 NOTES
    0.181.0 — the decomposition. CrystalExplorer splits E_int (CE-B3LYP; Mackenzie et al., IUCrJ 4, 575, 2017) into
    electrostatic, polarisation, dispersion and repulsion from wavefunctions; here the same spirit with the terms that
    GFN2-xTB prints in its SUMMARY, each taken as AB − A − B: electrostatics (isotropic + anisotropic ES), dispersion
    (D4), repulsion (the repulsion of the atoms) and the rest (everything else of the SCC energy — polarisation,
    exchange, charge transfer). These are the terms of a semi-empirical method, not those of CE-B3LYP: their sum is
    the E_int of GFN2, the split shows the character of a pair (an H-bond — electrostatic, a stack — dispersion).
    0.181.0 — salts. The charges of the components cannot be read from a CIF; guess_charges takes them from the
    formula: one-atom ions (Na⁺, Ca²⁺, Cl⁻ …) and common polyatomic ions (NH₄⁺, NO₃⁻, ClO₄⁻, SO₄²⁻, PO₄³⁻, BF₄⁻,
    PF₆⁻, acetate, oxalate …, ION_FORMULAS); then, if the cell is not neutral and exactly one kind of component is
    left unknown, it takes the charge that makes the cell neutral (pyridinium chloride: Cl⁻ known — the organic cation
    +1). The window shows the charges and lets the user change them. Truncated at the shell: the long-range
    electrostatics beyond 3.8 Å is left out — for ions far more than for neutral molecules: the lattice energy of a
    salt from the shell is only a rough value (the window says so).
§7 TESTS
    tests/compass/test_crystal_pairs.py — a model energy that is a sum over atom pairs: E_int is the sum over the
    pairs between the molecules exactly, the lattice energy of argon in a cubic cell ½ · 6 · u(a); one dimer for six
    equivalent neighbours; the reading of the xtb output.
§8' ROBUSTNESS / ERRORS
    A failed energy (ValueError, OSError) — the pair gets None and is left out of the sum (the window says how many).
"""

from dataclasses import dataclass
import re
import subprocess

from azimuth.i18n import tr

RADIUS = 3.8
HARTREE_KJ = 2625.4996
ENERGY = re.compile(r'TOTAL ENERGY\s+(-?\d+\.\d+)\s+Eh')


@dataclass(frozen=True)
class Plan:
    shell: object
    monomers: dict
    dimers: list
    of: list
    centroids: tuple
    charges: dict = None  # {component: charge}


@dataclass(frozen=True)
class Pair:
    neighbour: object
    distance: float
    energy: float | None
    key: tuple
    terms: dict | None = None  # {'es', 'disp', 'rep', 'rest'} kJ/mol


ION_ATOMS = {**{s: 1 for s in ('Li', 'Na', 'K', 'Rb', 'Cs', 'Ag', 'Tl')},
             **{s: 2 for s in ('Be', 'Mg', 'Ca', 'Sr', 'Ba')}, 'Al': 3,
             **{s: -1 for s in ('F', 'Cl', 'Br', 'I')}}
# the formulas as azimuth.core.Molecule.formula writes them (C, H first when there is C, else alphabetical)
ION_FORMULAS = {'H4N': 1, 'H3O': 1, 'NO3': -1, 'NO2': -1, 'ClO4': -1, 'O4S': -2, 'HO4S': -1, 'O4P': -3, 'HO4P': -2,
                'H2O4P': -1, 'CO3': -2, 'CHO3': -1, 'BF4': -1, 'F6P': -1, 'F6Sb': -1, 'C2H3O2': -1, 'HO': -1,
                'CN': -1, 'CNS': -1, 'N3': -1, 'C2O4': -2, 'CF3O3S': -1, 'I3': -1, 'BrO3': -1, 'ClO3': -1, 'IO3': -1,
                'O4Re': -1, 'MnO4': -1, 'CrO4': -2, 'Cr2O7': -2}


@dataclass(frozen=True)
class Charges:
    by_formula: dict
    counts: dict
    components: dict
    known: dict
    balanced: bool


def guess_charges(crystal, factor=None):
    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry import crystal_symmetry as cs

    w = cs.walk(crystal, factor)
    members = {}
    for i, c in enumerate(w.component):
        members.setdefault(c, []).append(w.atoms[i][0])
    components = {c: Molecule('', tuple(Atom(s, 0, 0, 0) for s in symbols)).formula for c, symbols in members.items()}
    counts = {}
    for formula in components.values():
        counts[formula] = counts.get(formula, 0) + 1
    by_formula, known = {}, {}
    for formula in counts:
        symbols = [s for c, f in components.items() if f == formula for s in members[c]]
        if len(symbols) == 1 and symbols[0] in ION_ATOMS:
            by_formula[formula], known[formula] = ION_ATOMS[symbols[0]], True
        elif formula in ION_FORMULAS:
            by_formula[formula], known[formula] = ION_FORMULAS[formula], True
        else:
            by_formula[formula], known[formula] = 0, False
    total = sum(by_formula[f] * n for f, n in counts.items())
    unknown = [f for f in counts if not known[f]]
    if total and len(unknown) == 1 and total % counts[unknown[0]] == 0:
        by_formula[unknown[0]] = -total // counts[unknown[0]]
        total = 0
    return Charges(by_formula, counts, components, known, total == 0)


@dataclass(frozen=True)
class Result:
    pairs: list
    lattice: float
    calculations: int
    failed: int


def _centroid(atoms):
    n = len(atoms)
    return tuple(sum(getattr(a, k) for a in atoms) / n for k in 'xyz')


def plan(crystal, centre=None, radius=RADIUS, factor=None, charges=None):
    from azimuth.core import Molecule
    from modules.compass.chemistry import crystal_shell

    from modules.compass.chemistry import crystal_symmetry as cs

    found = crystal_shell.shell(crystal, centre, radius, False, factor)
    w = cs.walk(crystal, factor)
    if len(found.centres) != 1:
        raise ValueError(tr('Энергии пар считаются для одной молекулы — выделите атом одной молекулы.'))
    atoms = found.molecule.atoms
    centre_atoms = atoms[:found.centre_atoms]
    size = {}
    start = found.centre_atoms
    pieces = []
    c0 = found.centres[0][0]
    size[c0] = found.centre_atoms
    for n in found.neighbours:  # the atoms of each neighbour follow in the order of the neighbours
        count = size.get(n.component)
        if count is None:
            count = size[n.component] = sum(1 for c in w.component if c == n.component)
        pieces.append(atoms[start:start + count])
        start += count
    monomers = {c0: Molecule('A', tuple(centre_atoms), None)}
    for n, piece in zip(found.neighbours, pieces):
        monomers.setdefault(n.component, Molecule('B', tuple(piece), None))
    a = _centroid(centre_atoms)
    centroids = [_centroid(piece) for piece in pieces]
    dimers, of, seen = [], [], set()
    for n, piece, b in zip(found.neighbours, pieces, centroids):
        r = sum((a[k] - b[k]) ** 2 for k in range(3)) ** 0.5
        key = (c0, n.component, round(r, 3), round(n.distance, 3))
        of.append(key)
        if key not in seen:
            seen.add(key)
            dimers.append((key, Molecule('AB', tuple(centre_atoms) + tuple(piece), None)))
    guessed = guess_charges(crystal, factor)
    by_formula = dict(guessed.by_formula)
    by_formula.update(charges or {})
    charge = {c: int(by_formula.get(guessed.components.get(c, ''), 0)) for c in monomers}
    return Plan(found, monomers, dimers, of, (a, centroids), charge)


def _ask(energy, molecule, charge):
    return energy(molecule) if not charge else energy(molecule, charge)


def _split(value):
    """(total, terms or None) of what energy() gave: a number or a dict of terms_of."""
    if isinstance(value, dict):
        return value.get('total'), value
    return value, None


def compute(p, energy, progress=None):
    total = len(p.monomers) + len(p.dimers)
    done = 0
    charge = dict(p.charges or {})
    monomer = {}
    for c, molecule in p.monomers.items():
        try:
            monomer[c] = _split(_ask(energy, molecule, charge.get(c, 0)))
        except (ValueError, OSError):
            monomer[c] = (None, None)
        done += 1
        if progress:
            progress(done, total)
    dimer = {}
    for key, molecule in p.dimers:
        try:
            dimer[key] = _split(_ask(energy, molecule, charge.get(key[0], 0) + charge.get(key[1], 0)))
        except (ValueError, OSError):
            dimer[key] = (None, None)
        done += 1
        if progress:
            progress(done, total)
    pairs, failed = [], 0
    a = p.centroids[0]
    c0 = next(iter(p.monomers))
    for n, key, b in zip(p.shell.neighbours, p.of, p.centroids[1]):
        r = sum((a[k] - b[k]) ** 2 for k in range(3)) ** 0.5
        parts = (dimer.get(key, (None, None)), monomer.get(c0, (None, None)), monomer.get(n.component, (None, None)))
        e = None if any(x[0] is None for x in parts) else (parts[0][0] - parts[1][0] - parts[2][0]) * HARTREE_KJ
        terms = None
        if e is not None and all(x[1] for x in parts):  # the terms of GFN2, each AB − A − B
            def delta(name):
                return (parts[0][1][name] - parts[1][1][name] - parts[2][1][name]) * HARTREE_KJ

            terms = {'es': delta('es'), 'disp': delta('disp'), 'rep': delta('rep')}
            terms['rest'] = e - terms['es'] - terms['disp'] - terms['rep']
        failed += e is None
        pairs.append(Pair(n, r, e, key, terms))
    lattice = 0.5 * sum(x.energy for x in pairs if x.energy is not None)
    return Result(pairs, lattice, total, failed)


def frame(result, centre_point, neighbour_points):
    """The cylinders of the energy framework: (centroid A, centroid B, width 0–1 by |E| / the largest |E|, E < 0)."""
    known = [x.energy for x in result.pairs if x.energy is not None]
    top = max((abs(e) for e in known), default=0.0) or 1.0
    out = []
    for pair, point in zip(result.pairs, neighbour_points):
        if pair.energy is None or abs(pair.energy) < 0.05 * top:  # the weak pairs left out, as CrystalExplorer's cut-off
            continue
        out.append((tuple(centre_point), tuple(point), abs(pair.energy) / top, pair.energy < 0))
    return out


def energy_of(text):
    found = ENERGY.findall(text or '')
    return float(found[-1]) if found else None


TERMS = {'iso': re.compile(r'->\s*isotropic ES\s+(-?\d+\.\d+)\s+Eh'),
         'aniso': re.compile(r'->\s*anisotropic ES\s+(-?\d+\.\d+)\s+Eh'),
         'xc': re.compile(r'->\s*anisotropic XC\s+(-?\d+\.\d+)\s+Eh'),
         'disp': re.compile(r'->\s*dispersion\s+(-?\d+\.\d+)\s+Eh'),
         'rep': re.compile(r'::\s*repulsion energy\s+(-?\d+\.\d+)\s+Eh')}


def terms_of(text):
    total = energy_of(text)
    found = {k: pattern.findall(text or '') for k, pattern in TERMS.items()}
    if total is None or not all(found.values()):
        return None
    last = {k: float(v[-1]) for k, v in found.items()}
    return {'total': total, 'es': last['iso'] + last['aniso'], 'xc': last['xc'], 'disp': last['disp'], 'rep': last['rep']}


def run_xtb(program, molecule, folder, timeout=600, charge=0, terms=False):
    from pathlib import Path

    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    lines = [str(len(molecule.atoms)), 'pair']
    lines += [f'{a.symbol} {a.x:.6f} {a.y:.6f} {a.z:.6f}' for a in molecule.atoms]
    (folder / 'mol.xyz').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    command = [str(program), 'mol.xyz', '--gfn', '2', '--sp', '--chrg', str(int(charge))]
    from azimuth.core import Z

    if (sum(Z.get('H' if a.symbol == 'D' else a.symbol, 0) for a in molecule.atoms) - int(charge)) % 2:
        command += ['--uhf', '1']
    done = subprocess.run(command, cwd=folder, capture_output=True, text=True, encoding='utf-8', errors='replace',
                          timeout=timeout)
    (folder / 'xtb.out').write_text(done.stdout + done.stderr, encoding='utf-8')
    value = energy_of(done.stdout)
    if value is None:
        raise ValueError(tr('xtb не дал энергии — вывод в {}').format(str(folder / 'xtb.out')))
    if terms:
        return terms_of(done.stdout) or value
    return value

"""Conformer search: turns about the rotatable bonds, steric filter, duplicates, Boltzmann weights.

§1 THEORY
    Conformers differ by turns about single bonds that are not in a ring. A systematic search turns every
    rotatable bond through 360° in equal steps (120° gives the staggered positions of sp³–sp³ bonds:
    anti, gauche±) and keeps the combinations without atoms running into each other; equal structures
    (the same after superposition) are counted once. Their energies need a calculation (here GFN2-xTB
    optimizations, modules/sextant/runner.py); the share of a conformer at temperature T is the
    Boltzmann weight p_k = exp(−ΔE_k / RT) / Σ_j exp(−ΔE_j / RT) (electronic energies; free energies
    would add the vibrational part).
§2 ALGORITHM rotors(m): bonds of order 1 (editing.perceived_orders) that are not in a ring (transforms.bond_side refuses
    ring bonds), both ends with another neighbour, the moving side = the smaller side; a side that is only hydrogens on
    a carbon (CH3, CH2 of a terminal carbon …) is not a rotor (its turns give the same structure), O–H, N–H and S–H are
    (they decide hydrogen bonds); amide C(=O)–N bonds are left out (partial double bond). candidates(m, step, limit,
    seed): all combinations k·step for every rotor (applied one after another on the current coordinates with
    torsion.turn), or `limit` random combinations (numpy Generator(seed), the identity first) when there are more; a
    combination is refused when two atoms that are not 1–2 or 1–3 neighbours come closer than CLASH × (r_i + r_j) (van
    der Waals radii); the rest sorted by the steric score Σ max(0, 0.9 (r_i + r_j) − d)² of the same pairs; duplicates:
    RMSD of the heavy atoms and of the H on N, O, S after a proper Kabsch fit below SAME Å. ranked(results, T): relative
    energies (kcal/mol) and the weights after the sorting of CREST (cregen, energy window 6 kcal/mol, duplicates ΔE <
    0.05 kcal/mol and RMSD < 0.125 Å, rotamers ΔE < 0.05 kcal/mol with rotational constants within 1 %, weights with the
    number of rotamers). read_ensemble reads an ensemble written by CREST (crest_conformers.xyz).
§3 APPLICATIONS
    modules/compass/actions/conformer_actions.py («Правка → Поиск конформеров…»).
§4 SPECIFICATION
    rotors(m) -> [(b, c, moving)] (moving ∈ {b, c}); candidates(m, step=120, limit=500, seed=1) ->
    [(Molecule, score)] distinct, the lowest score first (the given structure is always one of them when
    it passes the filter); rmsd_heavy(a, b) -> Å; ranked([(Molecule, energy hartree)], T=298.15) ->
    [(Molecule, energy, ΔE kcal/mol, weight)] lowest first. above_window(results, ewin) -> (how many structures lie
    above the window, ΔE kcal/mol of the nearest of them or None) — 0.91.1, said in the status of the search so that
    a conformer left out by the window is not taken for one never found. ValueError: step not dividing 360, limit
    outside 1–5000, no atoms.
§5 PROCEDURES - below.
§6 NOTES
    CLASH = 0.65 and SAME = 0.3 Å are design choices: 0.65 of the van der Waals sum lets eclipsed H…H
    (≈ 2.3 Å) and 1–4 contacts pass and stops atoms inside each other; 0.3 Å RMSD is far below the
    difference of two staggered positions (≈ 1 Å for the moved atoms).
§7 TESTS
    tests/compass/test_conformers.py.
§8' ROBUSTNESS
    A turn that fails (atoms closer than 0.1 Å) drops that combination.
"""

from itertools import product
from math import exp

import numpy as np

from azimuth.i18n import tr

CLASH = 0.65
SAME = 0.3
RADII = {'H': 1.20, 'C': 1.70, 'N': 1.55, 'O': 1.52, 'F': 1.47, 'P': 1.80, 'S': 1.80, 'Cl': 1.75, 'Br': 1.85, 'I': 1.98,
         'Si': 2.10, 'B': 1.92}
R_KCAL = 0.0019872043  # kcal/(mol K)
HARTREE_KCAL = 627.5094740631


def _neighbours(molecule):
    from modules.compass.chemistry.builder import connections

    out = [set() for _ in molecule.atoms]
    for i, j, _ in connections(molecule):
        out[i].add(j)
        out[j].add(i)
    return out


def rotors(molecule):
    from modules.compass.chemistry.editing import perceived_orders
    from modules.compass.chemistry.transforms import bond_side

    nb = _neighbours(molecule)
    atoms = molecule.atoms
    found = []
    for i, j, order in perceived_orders(molecule):
        if order != 1 or len(nb[i]) < 2 or len(nb[j]) < 2:
            continue
        try:
            side_j = bond_side(molecule, i, j)
        except ValueError:
            continue  # a ring bond
        side_i = sorted(set(range(len(atoms))) - set(side_j))
        moving, side = (j, side_j) if len(side_j) <= len(side_i) else (i, side_i)
        fixed = i if moving == j else j
        rest = [k for k in side if k != moving]
        if all(atoms[k].symbol == 'H' for k in rest) and atoms[moving].symbol not in ('O', 'N', 'S'):
            continue  # CH3 and the like: every turn gives the same structure
        if _amide(molecule, nb, fixed, moving) or _amide(molecule, nb, moving, fixed):
            continue
        found.append((fixed, moving, moving))
    return found


def _amide(molecule, nb, c, n):
    atoms = molecule.atoms
    if atoms[c].symbol != 'C' or atoms[n].symbol != 'N':
        return False
    return any(atoms[k].symbol in ('O', 'S') and len(nb[k]) == 1 for k in nb[c])


def _pairs(molecule):
    """Index arrays of the atom pairs that are not 1–2 or 1–3 neighbours, and their radius sums."""
    nb = _neighbours(molecule)
    n = len(molecule.atoms)
    near = [set(nb[i]) | {k for j in nb[i] for k in nb[j]} | {i} for i in range(n)]
    ii, jj = [], []
    for i in range(n):
        for j in range(i + 1, n):
            if j not in near[i]:
                ii.append(i)
                jj.append(j)
    radius = np.array([RADII.get(a.symbol, 1.8) for a in molecule.atoms])
    ii, jj = np.array(ii, int), np.array(jj, int)
    return ii, jj, radius[ii] + radius[jj]


def _score(x, pairs):
    ii, jj, sums = pairs
    if len(ii) == 0:
        return 0.0, True
    d = np.linalg.norm(x[ii] - x[jj], axis=1)
    if np.any(d < CLASH * sums):
        return float('inf'), False
    over = np.maximum(0.0, 0.9 * sums - d)
    return float(np.sum(over * over)), True


def _heavy(molecule):
    """Heavy atoms and the hydrogens on N, O, S (their turns are conformers too)."""
    nb = _neighbours(molecule)
    atoms = molecule.atoms
    keep = [i for i, a in enumerate(atoms)
            if a.symbol != 'H' or any(atoms[j].symbol in ('N', 'O', 'S') for j in nb[i])]
    return np.array([atoms[i].position for i in keep] or [a.position for a in atoms], float)


def rmsd_heavy(a, b):
    x, y = _heavy(a), _heavy(b)
    xc, yc = x - x.mean(0), y - y.mean(0)
    if len(x) == 1:
        return 0.0
    u, _, vt = np.linalg.svd(xc.T @ yc)
    d = np.eye(3)
    d[2, 2] = 1.0 if np.linalg.det(u @ vt) >= 0 else -1.0
    return float(np.sqrt(np.mean(np.sum((xc @ (u @ d @ vt) - yc) ** 2, axis=1))))


def candidates(molecule, step=120, limit=500, seed=1):
    from modules.compass.chemistry import torsion

    if not molecule.atoms:
        raise ValueError(tr('Нет атомов.'))
    if not (0 < step <= 360) or abs(360 / step - round(360 / step)) > 1e-9:
        raise ValueError(tr('Шаг поворота должен делить 360° нацело.'))
    if not isinstance(limit, int) or not 1 <= limit <= 5000:
        raise ValueError(tr('Конформеров для перебора — от 1 до 5000.'))
    found_rotors = rotors(molecule)
    positions = round(360 / step)
    total = positions ** len(found_rotors)
    if total <= limit:
        combos = list(product(range(positions), repeat=len(found_rotors)))
    else:
        rng = np.random.default_rng(seed)
        combos = [tuple([0] * len(found_rotors))]
        seen = {combos[0]}
        while len(combos) < limit:
            c = tuple(int(v) for v in rng.integers(0, positions, len(found_rotors)))
            if c not in seen:
                seen.add(c)
                combos.append(c)
    pairs = _pairs(molecule)
    kept = []
    for combo in combos:
        m = molecule
        try:
            for (fixed, moving, _), k in zip(found_rotors, combo):
                if k:
                    m = torsion.turn(m, fixed, moving, moving, k * step)
        except ValueError:
            continue
        score, fine = _score(np.array([a.position for a in m.atoms], float), pairs)
        if fine:
            kept.append((m, score))
    kept.sort(key=lambda item: item[1])
    distinct = []
    for m, score in kept:
        if all(rmsd_heavy(m, other) >= SAME for other, _ in distinct):
            distinct.append((m, score))
    return distinct


# CREGEN of CREST (Pracht, Bohle, Grimme, Phys. Chem. Chem. Phys. 22, 7169 (2020); the defaults of
# `crest --help`): energy window, RMSD, energy and rotational-constant thresholds
EWIN, RTHR, ETHR, BTHR = 6.0, 0.125, 0.05, 0.01


def rotational_constants(molecule):
    """A >= B >= C in MHz from the principal moments (masses of the most abundant isotopes)."""
    from modules.spectrum.analysis.thermo import AMU, MASSES

    masses = np.array([MASSES.get(a.symbol, 1.0) for a in molecule.atoms]) * AMU
    x = np.array([a.position for a in molecule.atoms], float) * 1e-10
    r = x - (masses[:, None] * x).sum(0) / masses.sum()
    inertia = sum(m * (np.dot(v, v) * np.eye(3) - np.outer(v, v)) for m, v in zip(masses, r))
    moments = np.sort(np.linalg.eigvalsh(inertia))
    h = 6.62607015e-34
    return tuple(float(h / (8 * np.pi ** 2 * max(i, 1e-60)) / 1e6) for i in moments)


def rmsd_all(a, b):
    x = np.array([p.position for p in a.atoms], float)
    y = np.array([p.position for p in b.atoms], float)
    xc, yc = x - x.mean(0), y - y.mean(0)
    u, _, vt = np.linalg.svd(xc.T @ yc)
    d = np.eye(3)
    d[2, 2] = 1.0 if np.linalg.det(u @ vt) >= 0 else -1.0
    return float(np.sqrt(np.mean(np.sum((xc @ (u @ d @ vt) - yc) ** 2, axis=1))))


def _same_rotors(a, b, bthr):
    ra, rb = rotational_constants(a), rotational_constants(b)
    # a linear or flat limit: compare the finite constants only
    pairs = [(x, y) for x, y in zip(ra, rb) if x < 1e12 and y < 1e12]
    return all(abs(x - y) / max(abs(x), abs(y), 1e-30) < bthr for x, y in pairs)


def cregen(results, temperature=298.15, ewin=EWIN, rthr=RTHR, ethr=ETHR, bthr=BTHR):
    """CREST's sorting of an ensemble [(Molecule, energy hartree)] (§2 of the CREST paper): the
    lowest first; above ewin (kcal/mol) left out; a structure with ΔE < ethr and RMSD < rthr to a kept
    one is a duplicate (dropped); with ΔE < ethr, RMSD >= rthr and rotational constants within bthr it is
    a rotamer of that conformer (its degeneracy grows); the rest are new conformers. Boltzmann weights
    p_k ∝ g_k exp(−ΔE_k / RT) with the degeneracy g_k.
    Returns [(Molecule, energy, ΔE kcal/mol, weight, degeneracy)]."""
    results = sorted(((m, e) for m, e in results if e is not None), key=lambda item: item[1])
    if not results:
        return []
    low = results[0][1]
    kept = []  # [molecule, energy, degeneracy, members: [(molecule, energy)] of the conformer and its rotamers]
    for m, e in results:
        if (e - low) * HARTREE_KCAL > ewin:
            break
        near = [(item, other) for item in kept for other, eo in item[3] if abs(e - eo) * HARTREE_KCAL < ethr]
        if any(rmsd_all(m, other) < rthr for _, other in near):
            continue  # a duplicate of a structure already kept (a conformer or one of its rotamers)
        owner = next((item for item, other in near if _same_rotors(m, other, bthr)), None)
        if owner is not None:
            owner[2] += 1
            owner[3].append((m, e))
        else:
            kept.append([m, e, 1, [(m, e)]])
    rel = [(item[1] - low) * HARTREE_KCAL for item in kept]
    factors = [item[2] * exp(-r / (R_KCAL * temperature)) for item, r in zip(kept, rel)]
    total = sum(factors)
    return [(item[0], item[1], r, f / total, item[2]) for item, r, f in zip(kept, rel, factors)]


def above_window(results, ewin=EWIN):
    """(count, nearest ΔE kcal/mol) of the structures of [(Molecule, energy hartree)] above ewin of the lowest."""
    energies = sorted(e for _, e in results if e is not None)
    if not energies:
        return 0, None
    above = [(e - energies[0]) * HARTREE_KCAL for e in energies if (e - energies[0]) * HARTREE_KCAL > ewin]
    return len(above), (above[0] if above else None)


def read_ensemble(text):
    """[(Molecule, energy | None)] of a multi-frame XYZ such as crest_conformers.xyz (the energy: the
    first number of the comment line, hartree)."""
    import re

    from modules.compass.chemistry.formats import read_xyz_frames

    frames = read_xyz_frames(text)
    comments = []
    lines = text.splitlines()
    k = 0
    while k < len(lines):
        if not lines[k].strip():
            k += 1
            continue
        n = int(lines[k].split()[0])
        comments.append(lines[k + 1] if k + 1 < len(lines) else '')
        k += n + 2
    energies = []
    for c in comments:
        m = re.search(r'[-+]?\d+\.\d+(?:[eEdD][-+]?\d+)?', c)
        energies.append(float(m.group(0)) if m else None)
    return list(zip(frames, energies + [None] * (len(frames) - len(energies))))


def ranked(results, temperature=298.15):
    """The ensemble sorted as CREGEN does (cregen), as (Molecule, energy, ΔE, weight)."""
    return [(m, e, r, w) for m, e, r, w, _ in cregen(results, temperature)]

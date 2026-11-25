"""Conformer search by an Artificial Bee Colony (ABC) over the torsions of the rotatable bonds.

§1 THEORY
    The method of SmartChemDesign/abc (M. Yablonskiy et al., github.com/SmartChemDesign/abc, MIT licence; the bee colony
    of Karaboga & Basturk, J. Glob. Optim. 39, 459 (2007)), written again here without RDKit, OpenBabel, ASE and PySCF:
    a «food source» is a vector of turns of the rotatable bonds (conformers.rotors, −180…180°); its value is the
    GFN2-xTB energy after a short optimization (xtb --opt with a few cycles, as their BFGS to fmax 0.5 eV/Å). Employed
    bees change one turn of a source towards or away from another source, v_j = x_j + φ (x_j − x_k), φ ∈ [−1, 1], and
    keep the better; onlookers do the same on sources chosen by fitness; a source not improved max_trials times is
    given up for a random one (a scout). The global search maximizes −E; every local search maximizes
        F = F_E · F_RMSD, F_E = 1 if E < E_min, else 1 / (1 + 10 ΔE[eV]),
        F_RMSD = CDF of the exponentially modified normal law (K = 1, loc = RMSD_ref, scale = 2) at the smallest RMSD
                 to the conformers already taken (RMSD_ref — the smallest RMSD made by turning the first or the last
                 rotor by 180°),
    i.e. low and unlike the ones found. The best source of each search is optimized fully; it is taken when it differs
    from the taken ones (RMSD ≥ RMSD_SAME) and lies within the energy window ewin (kcal/mol) of the lowest one; a new
    lowest one drops the taken ones that fall out of the window. The window replaces the Boltzmann share of 5 %
    at 298.15 K of the original (P_MIN) — that kept a second conformer only up to 1.74 kcal/mol above the first, so the
    search mostly gave one; the window is the one of CREGEN (6 kcal/mol by default). It stops at n_confs conformers or
    as many rejected.
§2 ALGORITHM
    search(start, …) is a generator: it yields (Molecule, cycles) to compute — cycles: optimization cycles of xtb (0: a
    full optimization) — and receives (energy hartree, Molecule) or None (the calculation failed); its return value is
    the ensemble [(Molecule, energy)]. Structures with atoms run into each other (conformers._score) or whose bonds
    changed after the optimization are not food (F = 0). Vectors closer than THRESHOLD degrees in every turn to one
    already computed are not computed again. The caller (conformer_actions.py) runs xtb for every yielded structure.
§4 SPECIFICATION
    search(start, n_confs=6, global_iterations=10, local_iterations=5, max_trials=5, seed=None, short_cycles=15,
           temperature=298.15, ewin=conformers.EWIN, progress=None) -> generator; progress: a dict the search
           keeps up to date for the window — stage 'global' | 'local', local (the number of the local search, from 1),
           local_max = 2 n_confs − 2 (each local search adds one to the taken or the rejected, and the search stops at
           n_confs of either: at most (n_confs − 1) more taken and n_confs − 1 rejected before the last), taken,
           rejected; exponnorm_cdf(x, k, loc, scale) -> float; probabilities(energies, T).
    ValueError: no rotatable bond; no structure is food (with the reason — bonds xtb changed, xtb failed, or
    clashes).
§6 NOTES
    Not taken from the original: the check of a transition path between two conformers (calculate_PPE_path) and the
    final MP2 optimization in PySCF; the energies are in hartree (the original works in eV). The original
    calculate_energy reads an XYZ as a tuple and then uses it as ase.Atoms — the case of a given global minimum fails
    there; here a given structure is simply the start.
§7 TESTS
    tests/compass/test_abc_search.py (a model energy of the turns instead of xtb).
"""

from __future__ import annotations

import random
from math import erf, exp, sqrt

import numpy as np

from modules.compass.chemistry import conformers as cf
from azimuth.i18n import tr

HARTREE_EV = 27.211386245988
HARTREE_KJ = 2625.4996394799
R_KJ = 0.0083144626  # kJ/(mol K)
THRESHOLD = 1.0  # degrees
RMSD_SAME = 0.15  # Å, as calculate_final_rmsd of the original


def exponnorm_cdf(x, k=1.0, loc=0.0, scale=1.0):
    """scipy.stats.exponnorm.cdf(x, K=k, loc, scale): Φ(z) − exp(1/(2k²) − z/k) Φ(z − 1/k), z = (x − loc)/scale."""
    z = (x - loc) / scale

    def phi(t):
        return 0.5 * (1.0 + erf(t / sqrt(2.0)))

    tail = 1.0 / (2.0 * k * k) - z / k
    if tail > 700:  # far left: the second term equals the first
        return 0.0
    return max(0.0, phi(z) - exp(tail) * phi(z - 1.0 / k))


def probabilities(energies, temperature=298.15):
    """Boltzmann shares of energies in hartree."""
    low = min(energies)
    weights = [exp(-(e - low) * HARTREE_KJ / (R_KJ * temperature)) for e in energies]
    total = sum(weights)
    return [w / total for w in weights]


def _turned(start, found, vector):
    from modules.compass.chemistry import torsion

    m = start
    try:
        for (fixed, moving, _), angle in zip(found, vector):
            if abs(angle) > 1e-9:
                m = torsion.turn(m, fixed, moving, moving, angle)
    except ValueError:
        return None
    return m


def _bonds(molecule):
    from modules.compass.chemistry.builder import connections

    return {(min(i, j), max(i, j)) for i, j, _ in connections(molecule)}


def _wrap(angle):
    return (angle + 180.0) % 360.0 - 180.0


def search(start, n_confs=6, global_iterations=10, local_iterations=5, max_trials=5, seed=None, short_cycles=15,
           temperature=298.15, ewin=None, progress=None):
    ewin = cf.EWIN if ewin is None else ewin  # kcal/mol above the lowest conformer
    if not 0 < ewin <= 100:
        raise ValueError(tr('Окно энергий — от 0 до 100 ккал/моль.'))
    found = cf.rotors(start)
    if not found:
        raise ValueError(tr('Вращаемых связей нет — искать конформеры пчелиным алгоритмом нечего.'))
    rng = random.Random(seed)
    dim = len(found)
    size = max(2, dim)
    pairs = cf._pairs(start)
    bonds = _bonds(start)
    computed = []  # [(vector, energy, Molecule)] of every food source computed
    taken, rejected = [], []  # [(Molecule, energy)]
    broken = {}  # {(i, j): how often} — the bonds xtb broke (or made), to say why nothing is food
    failures = [0]  # xtb runs that gave nothing

    def reference_rmsd():
        flips = [[0.0] * dim, [180.0] + [0.0] * (dim - 1), [0.0] * (dim - 1) + [180.0]]
        a = _turned(start, found, flips[0])
        values = [cf.rmsd_all(a, b) for b in (_turned(start, found, f) for f in flips[1:]) if b is not None]
        return min(values) if values else 0.5

    ref = reference_rmsd() or 0.5

    def fitness(kind, energy, molecule):
        if kind == 'global':
            return -energy
        low = min(e for _, e in taken)
        f_e = 1.0 if energy < low else 1.0 / (1.0 + 10.0 * (energy - low) * HARTREE_EV)
        nearest = min(cf.rmsd_all(molecule, m) for m, _ in taken)
        return f_e * exponnorm_cdf(nearest, 1.0, ref, 2.0)

    def seen(vector):
        return any(all(abs(_wrap(a - b)) < THRESHOLD for a, b in zip(vector, old)) for old, *_ in computed)

    def evaluate(vector, kind):
        """A food source: (vector, energy, Molecule, fitness), or None when it is no food."""
        if seen(vector):
            return None
        m = _turned(start, found, vector)
        if m is None or not cf._score(np.array([a.position for a in m.atoms], float), pairs)[1]:
            return None
        answer = yield (m, short_cycles)
        if answer is None or answer[1] is None:
            failures[0] += 1
            return None
        energy, geometry = answer
        changed = _bonds(geometry) ^ bonds
        if changed:
            for pair in changed:
                broken[pair] = broken.get(pair, 0) + 1
            return None
        computed.append((list(vector), energy, geometry))
        return [list(vector), energy, geometry, fitness(kind, energy, geometry), 0]

    def random_vector():
        """Every turn random, or (half of the time) only a few of them from a source already computed —
        with many rotors a fully random vector mostly runs atoms into each other."""
        if computed and rng.random() < 0.5:
            vector = list(rng.choice(computed)[0])
            for d in rng.sample(range(dim), rng.randint(1, min(3, dim))):
                vector[d] = rng.uniform(-180.0, 180.0)
            return vector
        return [rng.uniform(-180.0, 180.0) for _ in range(dim)]

    def random_source(kind, tries=400, runs=12):
        """A new food source: up to tries vectors (a clash costs nothing) and runs xtb runs."""
        before = len(computed) + failures[0] + sum(broken.values())
        for _ in range(tries):
            source = yield from evaluate(random_vector(), kind)
            if source is not None:
                return source
            if len(computed) + failures[0] + sum(broken.values()) - before >= runs:
                break
        return None

    def why():
        """The reason no structure is food, for the message."""
        if broken:
            (i, j), _ = max(broken.items(), key=lambda item: item[1])
            a, b = start.atoms[i].symbol, start.atoms[j].symbol
            return tr(f'при оптимизации в xtb меняются связи (чаще всего {a}{i + 1}–{b}{j + 1}): молекула распадается '
                      f'или переносит атом. Проверьте заряд и число неспаренных электронов — например, у карбоксилат-'
                      f'аниона без водорода заряд −1, а не радикал')
        if failures[0]:
            return tr('xtb не досчитывает ни одной структуры — посмотрите её вывод в папке ABC среди расчётов')
        return tr('при любом повороте связей атомы налезают друг на друга')

    def improve(population, index, kind, tries=20):
        bee = population[index]
        for _ in range(tries):
            other = rng.choice([k for k in range(len(population)) if k != index])
            d = rng.randrange(dim)
            vector = list(bee[0])
            vector[d] = _wrap(vector[d] + rng.uniform(-1.0, 1.0) * (vector[d] - population[other][0][d]))
            source = yield from evaluate(vector, kind)
            if source is None:
                continue
            if source[3] > bee[3]:
                population[index] = source
            else:
                bee[4] += 1
            return
        bee[4] += 1

    def colony(population, kind, iterations):
        for _ in range(iterations):
            for index in range(len(population)):
                yield from improve(population, index, kind)
            values = [b[3] for b in population]
            low, high = min(values), max(values)
            shares = [0.2 + 0.8 * ((v - low) / (high - low) if high > low else 1.0) for v in values]
            for _ in range(len(population)):
                beta = rng.random() * sum(shares)
                index = next((k for k, s in enumerate(np.cumsum(shares)) if beta < s), len(shares) - 1)
                yield from improve(population, index, kind)
            for index, bee in enumerate(population):
                if bee[4] > max_trials:
                    fresh = yield from random_source(kind)
                    if fresh is not None:
                        population[index] = fresh
        return max(population, key=lambda b: b[3])

    def polish(best):
        """The best source optimized fully; (Molecule, energy) or None."""
        answer = yield (best[2], 0)
        if answer is None or answer[1] is None or _bonds(answer[1]) != bonds:
            return None
        return answer[1], answer[0]

    progress = {} if progress is None else progress  # where the search is, for the status of the window
    progress.update(stage='global', local=0, local_max=max(1, 2 * n_confs - 2), taken=0, rejected=0)
    # the global search: the lowest energy; the start itself is one of the first sources
    population = []
    first = yield from evaluate([0.0] * dim, 'global')
    if first is not None:
        population.append(first)
    elif broken:  # the start itself falls apart — every turn of it will
        raise ValueError(tr(f'Пчелиный поиск: ни одной годной структуры — {why()}.'))
    while len(population) < size:
        source = yield from random_source('global')
        if source is None:
            break
        population.append(source)
    if not population:
        raise ValueError(tr(f'Пчелиный поиск: ни одной годной структуры — {why()}.'))
    if len(population) > 1:
        best = yield from colony(population, 'global', global_iterations)
    else:
        best = population[0]
    lowest = yield from polish(best)
    if lowest is None:
        lowest = (best[2], best[1])
    taken.append(lowest)
    # the local searches: low and unlike the conformers taken
    while len(taken) < n_confs and len(rejected) < n_confs:
        progress.update(stage='local', local=progress['local'] + 1, taken=len(taken), rejected=len(rejected))
        population = sorted(([v, e, m, fitness('local', e, m), 0] for v, e, m in computed), key=lambda b: -b[3])[:size]
        while len(population) < size:
            source = yield from random_source('local')
            if source is None:
                break
            population.append(source)
        if len(population) < 2:
            break
        best = yield from colony(population, 'local', local_iterations)
        found_one = yield from polish(best)
        if found_one is None:
            rejected.append((best[2], best[1]))
            continue
        molecule, energy = found_one
        if any(cf.rmsd_all(molecule, m) < RMSD_SAME for m, _ in taken):
            rejected.append(found_one)
            continue
        low = min([e for _, e in taken] + [energy])
        if (energy - low) * cf.HARTREE_KCAL > ewin:  # the energy window of CREGEN, not a 5 % share
            rejected.append(found_one)
            continue
        taken.append(found_one)
        if energy < min(e for _, e in taken[:-1]):  # a new lowest: the taken ones above the window go
            kept = [(m, e) for m, e in taken[:-1] if (e - energy) * cf.HARTREE_KCAL <= ewin]
            rejected.extend(c for c in taken[:-1] if c not in kept)
            taken = kept + [found_one]
    return sorted(taken, key=lambda item: item[1])

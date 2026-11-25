"""The projected density of states of a crystal: CP2K (its .pdos files, else its Molden file) and Quantum
ESPRESSO (projwfc.x), by element and by s, p, d, f.

§1 THEORY DOS(E) = Σ_i g(E − ε_i); the projected DOS of a set A of atomic functions PDOS_A(E) = Σ_i w_iA g(E − ε_i),
    w_iA — the share of the orbital i on A; the shares of an orbital add up to 1, so the PDOS of all the elements add up
    to the DOS. With orbitals in a Gaussian basis (CP2K, the Γ point of its cell) the share is Mulliken's, w_iμ = c_μi
    (S c_i)_μ, with the overlap of the periodic crystal S_μν = Σ_n ⟨χ_μ | χ_ν(r − n)⟩ (n — the lattice vectors: a
    function overlaps the images of the others); with these S the orbitals are orthonormal, cᵀSc = 1 (checked). CP2K
    writes the coefficients of contractions that are not normalized in its Molden files (the convention «unnormalized
    contractions» of orbital_files). The orbitals of the .pdos files of CP2K (&PRINT &PDOS) come with their projections
    on s, p, d, f of every kind of atom, the empty ones included (NLUMO). projwfc.x of Quantum ESPRESSO writes the PDOS
    of each atomic wave function of each atom (Löwdin projections) already broadened on the grid of dos.x. g — a
    Gaussian of FWHM. E₀ — the top of the valence band (the highest occupied level) or the Fermi level of a metal.
§2 ALGORITHM levels_from_cp2k_pdos(folder): the last .pdos file of each kind; levels_from_molden(text, cell): the Molden
    file of the last step, the periodic overlap (images within the reach of the most diffuse pair, exp(−μR²) < 1e-12);
    the shares by (element, l). curves(levels, fwhm): the DOS and the PDOS on a grid of 0.01 eV. qe_curves(folder):
    azimuth.pdos_atm#… summed by element and l. pdos(run) — the first source there is; the shares of a Molden file are
    kept in pdos-levels.csv of the run (computed once: tens of seconds for a supercell of 54 atoms).
§4 SPECIFICATION Levels(energies eV, occupations, weights {(element, l): array}, source); Curves(x, total, parts [(name,
    y)], orbitals [(name, y)], e0, source, note); periodic_overlap(shells, centres, cell) (bohr);
    levels_from_molden(text, cell Å); levels_from_cp2k_pdos(folder); qe_curves(folder, e0); pdos(run, compute=False,
    fwhm=0.3) -> Curves | None.
§6 NOTES A Molden file of an insulator computed with OT has the occupied orbitals only: its PDOS ends at the top of the
    valence band (said in the note); the runs of 0.151.0 print the .pdos files with the empty orbitals (cp2k_inputs,
    NLUMO).
§7 TESTS tests/compass/test_crystal_pdos.py — the real CELL_OPT of CsCl (CP2K 2026.2): orthonormal orbitals, the shares
    add up to 1, Cl 3p at the top of the valence band, Cs 5p below; .pdos and projwfc files of the format.
"""

from dataclasses import dataclass, field
import csv
from math import ceil, log, pi, sqrt
from pathlib import Path
import re

import numpy as np

HARTREE_EV = 27.211386245988
L_NAMES = 'spdfgh'
CACHE = 'pdos-levels.csv'


@dataclass
class Levels:
    energies: np.ndarray  # eV
    occupations: np.ndarray
    weights: dict  # (element, l) -> array over the levels
    source: str
    complete: bool = True  # the empty levels are there


@dataclass
class Curves:
    x: np.ndarray
    total: np.ndarray
    parts: list  # [(element, y)]
    orbitals: list  # [('Cl p', y)]
    e0: float
    source: str
    note: str = ''
    extra: dict = field(default_factory=dict)


# -- the periodic overlap --------------------------------------------------------------------------------------------
def _shifts(cell, reach):
    cell = np.asarray(cell, dtype=float)
    volume = abs(np.linalg.det(cell))
    heights = [volume / np.linalg.norm(np.cross(cell[(k + 1) % 3], cell[(k + 2) % 3])) for k in range(3)]
    n = [int(ceil(reach / h)) + 1 for h in heights]
    return np.array([(i, j, k) for i in range(-n[0], n[0] + 1) for j in range(-n[1], n[1] + 1)
                     for k in range(-n[2], n[2] + 1)], dtype=float) @ cell


def periodic_overlap(shells, centres, cell):
    """S_μν = Σ_n ⟨χ_μ|χ_ν(r − n)⟩, bohr; the shells of one l at once as in gto.overlap, the images summed per class pair."""
    from modules.spectrum.analysis.gto import _overlap_1d, cartesian

    centres = np.asarray(centres, dtype=float)
    offsets = np.cumsum([0] + [s.size for s in shells])
    result = np.zeros((offsets[-1], offsets[-1]))
    smallest = min(float(s.exponents.min()) for s in shells)
    reach = sqrt(log(1e12) / (smallest / 2))  # exp(−μR²), μ = a·b/(a+b) ≥ smallest/2
    span = np.ptp(centres, axis=0).max() if len(centres) > 1 else 0.0
    shifts = _shifts(cell, reach + span)
    classes = {}
    for index, shell in enumerate(shells):
        classes.setdefault(shell.l, []).append(index)
    packed = {}
    for l, members in classes.items():
        alpha = np.concatenate([shells[i].exponents for i in members])
        weight = np.concatenate([shells[i].radial() for i in members])
        where = np.concatenate([np.repeat(centres[shells[i].centre][None, :], shells[i].exponents.size, 0)
                                for i in members])
        owner = np.concatenate([[n] * shells[i].exponents.size for n, i in enumerate(members)])
        gather = np.zeros((alpha.size, len(members)))
        gather[np.arange(alpha.size), owner] = 1.0
        packed[l] = (members, alpha, weight, where, gather)
    for la, (ma, aa, wa, ra, ga) in packed.items():
        for lb, (mb, ab, wb, rb0, gb) in packed.items():
            if lb < la:
                continue
            a = aa[:, None]
            b = ab[None, :]
            p = a + b
            mu = a * b / p
            monomials_a, monomials_b = cartesian(la), cartesian(lb)
            mono = np.zeros((len(ma), len(mb), len(monomials_a), len(monomials_b)))
            for t in shifts:
                rb = rb0 + t
                diff = ra[:, None, :] - rb[None, :, :]
                exponent = mu * np.einsum('ijk,ijk->ij', diff, diff)
                if exponent.min() > 28:  # exp(−28) ≈ 7e-13
                    continue
                pref = np.exp(-exponent) * (pi / p) ** 1.5 * np.outer(wa, wb)
                tables = []
                for axis in range(3):
                    P = (a * ra[:, axis][:, None] + b * rb[:, axis][None, :]) / p
                    pa, pb = P - ra[:, axis][:, None], P - rb[:, axis][None, :]
                    tables.append({(i, j): _overlap_1d(i, j, pa, pb, p) for i in range(la + 1) for j in range(lb + 1)})
                for ka, (xa, ya, za) in enumerate(monomials_a):
                    for kb, (xb, yb, zb) in enumerate(monomials_b):
                        raw = pref * tables[0][xa, xb] * tables[1][ya, yb] * tables[2][za, zb]
                        mono[:, :, ka, kb] += ga.T @ raw @ gb
            for n, i in enumerate(ma):
                for q, j in enumerate(mb):
                    block = shells[i].angular @ mono[n, q] @ shells[j].angular.T
                    result[offsets[i]:offsets[i + 1], offsets[j]:offsets[j + 1]] = block
                    if la != lb:
                        result[offsets[j]:offsets[j + 1], offsets[i]:offsets[i + 1]] = block.T
    return result


# -- CP2K: the Molden file -------------------------------------------------------------------------------------------
@dataclass
class Wavefunction:
    """The orbitals of a Molden file of CP2K with the periodic overlap: shells, centres (bohr), cell (bohr), c (nbasis ×
    alpha orbitals), energies (eV), occupations, the atoms, s @ c."""
    atoms: tuple
    shells: list
    centres: np.ndarray
    cell: np.ndarray
    c: np.ndarray
    energies: np.ndarray
    occupations: np.ndarray
    sc: np.ndarray


def wavefunction(text, cell, progress=None, overlap=True, renormalized=True):
    """The Wavefunction of a Molden file of CP2K (Γ point); cell — rows a, b, c in Å. ValueError when the orbitals are
    not orthonormal with the periodic overlap under either convention of the contractions. overlap=False (the grids of
    crystal_field, which check the number of electrons instead): no overlap, the convention renormalized or not."""
    from modules.spectrum.analysis.gto import Shell
    from modules.spectrum.readers import orbital_files as of

    flags = set()
    atoms = gto = mo = None
    for name, rest, body in of._sections(text.lstrip()):
        key = name.replace(' ', '')
        if key in ('5d', '5d7f'):
            flags |= {2, 3}
        elif key == '5d10f':
            flags |= {2}
        elif key == '7f':
            flags |= {3}
        elif key == '9g':
            flags |= {4, 5}
        elif key == 'atoms':
            atoms, _ = of._atoms(rest, body)
        elif key == 'gto':
            gto = of._gto(body)
        elif key == 'mo':
            mo = of._mo(body)
    if atoms is None or gto is None or mo is None:
        raise ValueError('a Molden file with orbitals needs the sections [Atoms], [GTO] and [MO]')
    shells = [Shell(c, of.LETTERS[l], of.LETTERS[l] in flags, e, co) for c, l, e, co in gto]
    infos, columns = mo
    nbasis = sum(s.size for s in shells)
    c = np.zeros((nbasis, len(columns)))
    for k, column in enumerate(columns):
        for index, (value, _) in column.items():
            c[index - 1, k] = value
    alpha = [k for k, info in enumerate(infos) if not info.get('spin', 'alpha').lower().startswith('b')]
    c = c[:, alpha]
    energies = np.array([float(infos[k].get('ene', '0').replace('D', 'E')) for k in alpha]) * HARTREE_EV
    occupations = np.array([float(infos[k].get('occup', '0').replace('D', 'E')) for k in alpha])
    centres = np.array([a.position for a in atoms]) / of.BOHR
    cell_bohr = np.asarray(cell, dtype=float) / of.BOHR
    if not overlap:
        chosen = of._renormalized(shells) if renormalized else shells
        return Wavefunction(tuple(atoms), chosen, centres, cell_bohr, c, energies, occupations, None)
    best = None
    for candidate in (of._renormalized(shells), shells):  # CP2K: contractions not normalized
        s = periodic_overlap(candidate, centres, cell_bohr)
        sc = s @ c
        worst = float(np.max(np.abs(c.T @ sc - np.eye(c.shape[1]))))
        if best is None or worst < best[0]:
            best = (worst, candidate, sc)
        if worst < 1e-3:
            break
        if progress:
            progress()
    worst, shells, sc = best
    if worst > 1e-2:
        raise ValueError(f'the orbitals are not orthonormal with the periodic overlap (deviation {worst:.2g})')
    return Wavefunction(tuple(atoms), shells, centres, cell_bohr, c, energies, occupations, sc)


def levels_from_molden(text, cell, progress=None):
    """Levels of a Molden file of CP2K (Γ point); cell — rows a, b, c in Å."""
    w = wavefunction(text, cell, progress)
    atoms, shells, c, sc, energies, occupations = w.atoms, w.shells, w.c, w.sc, w.energies, w.occupations
    per_function = c * sc
    owners = np.concatenate([[s.centre] * s.size for s in shells])
    kinds = np.concatenate([[s.l] * s.size for s in shells])
    weights = {}
    for atom in set(owners.tolist()):
        symbol = atoms[atom].symbol
        for l in set(kinds[owners == atom].tolist()):
            key = (symbol, int(l))
            share = per_function[(owners == atom) & (kinds == l)].sum(axis=0)
            weights[key] = weights.get(key, 0.0) + share
    complete = bool((occupations < 1e-6).any())
    return Levels(energies, occupations, weights, 'molden', complete)


def write_levels(folder, levels):
    keys = sorted(levels.weights)
    with open(Path(folder) / CACHE, 'w', newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(['energy_eV', 'occupation'] + [f'{e} {L_NAMES[l]}' for e, l in keys])
        for k in range(len(levels.energies)):
            writer.writerow([f'{levels.energies[k]:.6f}', f'{levels.occupations[k]:.6f}']
                            + [f'{levels.weights[key][k]:.6f}' for key in keys])


def read_levels(folder):
    path = Path(folder) / CACHE
    if not path.is_file():
        return None
    try:
        rows = list(csv.reader(path.read_text(encoding='utf-8').splitlines()))
        head, body = rows[0], np.array([[float(x) for x in r] for r in rows[1:] if r], dtype=float)
        weights = {}
        for k, name in enumerate(head[2:]):
            element, letter = name.split()
            weights[(element, L_NAMES.index(letter))] = body[:, k + 2]
        occupations = body[:, 1]
        return Levels(body[:, 0], occupations, weights, 'molden', bool((occupations < 1e-6).any()))
    except (OSError, ValueError, IndexError):
        return None


# -- CP2K: the .pdos files -------------------------------------------------------------------------------------------
_KIND = re.compile(r'atomic kind\s+(\S+)')


def _pdos_files(folder):
    """The last .pdos file of each kind (azimuth-k1-1.pdos, azimuth-k1-1_12.pdos — of step 12)."""
    chosen = {}
    for path in Path(folder).glob('*.pdos'):
        m = re.match(r'(.+?-k(\d+)-\d+)(?:_(\d+))?\.pdos$', path.name)
        if not m:
            continue
        kind, step = m[2], int(m[3] or 0)
        if kind not in chosen or step > chosen[kind][0]:
            chosen[kind] = (step, path)
    return [chosen[k][1] for k in sorted(chosen, key=int)]


def levels_from_cp2k_pdos(folder):
    files = _pdos_files(folder)
    if not files:
        return None
    energies = occupations = None
    weights = {}
    for path in files:
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        m = _KIND.search(lines[0]) if lines else None
        if not m or len(lines) < 3:
            continue
        element = re.match(r'[A-Z][a-z]?', m[1])[0]
        head = lines[1].lstrip('#').split()
        columns = head[head.index('Occupation') + 1:]
        data = np.array([[float(x) for x in line.split()] for line in lines[2:] if line.strip()])
        if energies is None:
            energies, occupations = data[:, 1] * HARTREE_EV, data[:, 2]
        elif len(data) != len(energies):
            raise ValueError('the .pdos files have different levels')
        for k, name in enumerate(columns):
            l = L_NAMES.index(name[0])
            key = (element, l)
            weights[key] = weights.get(key, 0.0) + data[:, 3 + k]
    if energies is None:
        return None
    # the projections of an orbital add up to its share on the basis; normalized per level (as Mulliken's)
    total = sum(weights.values())
    total = np.where(np.abs(total) > 1e-12, total, 1.0)
    weights = {key: w / total for key, w in weights.items()}
    return Levels(energies, occupations, weights, 'pdos', bool((occupations < 1e-6).any()))


# -- curves ----------------------------------------------------------------------------------------------------------
def _broaden(energies, weights, x, fwhm):
    sigma = fwhm / (2.0 * sqrt(2.0 * log(2.0)))
    y = np.zeros_like(x)
    for start in range(0, len(energies), 256):
        e = energies[start:start + 256]
        w = weights[start:start + 256]
        y += (w[:, None] * np.exp(-0.5 * ((x[None, :] - e[:, None]) / sigma) ** 2)).sum(axis=0)
    return y / (sigma * sqrt(2 * pi))


def _occupied_top(levels):
    occupied = levels.energies[levels.occupations > 1e-3]
    return float(occupied.max()) if occupied.size else float(levels.energies.max())


def curves(levels, fwhm=0.3, units=1):
    """units — the number of cells of the file in the cell computed (the DOS per cell of the file)."""
    e0 = _occupied_top(levels)
    lo, hi = levels.energies.min() - 3 * fwhm, levels.energies.max() + 3 * fwhm
    x = np.arange(lo, hi, 0.01) - e0
    shifted = levels.energies - e0
    total = _broaden(shifted, np.full(len(shifted), 2.0 / units), x, fwhm)  # two electrons per level (spin)
    by_element, orbitals = {}, []
    for (element, l), w in sorted(levels.weights.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        y = _broaden(shifted, 2.0 * np.asarray(w) / units, x, fwhm)
        by_element[element] = by_element.get(element, 0.0) + y
        orbitals.append((f'{element} {L_NAMES[l]}', y))
    return Curves(x, total, sorted(by_element.items()), orbitals, e0, levels.source)


def qe_curves(folder):
    """The PDOS of projwfc.x (azimuth.pdos_atm#N(El)_wfc#M(l)) summed by element and l; None without them."""
    files = sorted(Path(folder).glob('*.pdos_atm#*'))
    total_file = next(iter(Path(folder).glob('*.pdos_tot')), None)
    if not files or total_file is None:
        return None
    def table(path):
        rows = [line.split() for line in path.read_text(encoding='utf-8', errors='replace').splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
        return np.array([[float(x) for x in r] for r in rows])
    whole = table(total_file)
    x = whole[:, 0]
    by_element, by_orbital = {}, {}
    for path in files:
        m = re.search(r'atm#\d+\(([A-Za-z]+)\d*\)_wfc#\d+\(([spdf])', path.name)
        if not m:
            continue
        element = re.match(r'[A-Z][a-z]?', m[1].capitalize())[0]
        y = table(path)[:, 1]
        if len(y) != len(x):
            continue
        by_element[element] = by_element.get(element, 0.0) + y
        key = f'{element} {m[2]}'
        by_orbital[key] = by_orbital.get(key, 0.0) + y
    return Curves(x, whole[:, 1], sorted(by_element.items()), sorted(by_orbital.items()), 0.0, 'projwfc')


def cp2k_levels(folder, compute=False, progress=None):
    """The levels of a CP2K run: its .pdos files, else the shares kept from its Molden file, else (compute) worked out."""
    from modules.spectrum.readers import cp2k

    found = levels_from_cp2k_pdos(folder)
    if found is not None:
        return found
    molden = cp2k.molden_files(folder)
    kept = read_levels(folder)
    if kept is not None and (not molden or (Path(folder) / CACHE).stat().st_mtime >= molden[-1].stat().st_mtime):
        return kept
    if not compute or not molden:
        return None
    cell = cp2k.last_cell(folder)
    if cell is None:
        raise ValueError('no cell of the run')
    levels = levels_from_molden(molden[-1].read_text(encoding='utf-8', errors='replace'), cell, progress)
    write_levels(folder, levels)
    return levels

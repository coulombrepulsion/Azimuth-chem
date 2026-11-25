"""MOPAC orbitals from the auxiliary file (.aux): Slater functions as fitted Gaussians.

§1 THEORY
    MOPAC (NDDO methods: PM7, PM6, AM1, RM1, MNDO) works in a minimal valence basis of Slater-type orbitals
        chi_nlm(r) = (2 zeta)^(n + 1/2) / sqrt((2n)!) r^(n - 1) exp(-zeta r) Y_lm, Y_lm real and unit-normalized, n the
    principal quantum number (ATOM_PQN), zeta the exponent (AO_ZETA, 1/bohr). NDDO neglects the overlap in the secular
    equations: the orbitals are orthonormal with the unit metric (C^T C = 1), the overlap of the Slater functions enters
    only the resonance integrals, and the MOPAC charges are Coulson charges q_A = Z_A - sum_{mu on A} P_mu,mu. An
    orbital is drawn as psi = sum_mu C_mu chi_mu in the Slater basis — the shape of the orbital, as other viewers of
    MOPAC orbitals draw it; the integral of psi^2 is then close to, not exactly, 1. A Slater function is written as a
    fixed contraction of K Gaussians r^l exp(-alpha_k zeta^2 r^2) fitted once to the Slater radial function of zeta = 1
    (modules/spectrum/analysis/sto_fits.py, tools/fit_sto.py; scaled by zeta^2 in the exponents, the normalized
    coefficients unchanged), so the Gaussian code of Spectrum (gto.py: cubes, density analysis) serves MOPAC unchanged.
§2 ALGORITHM The last «START OF MOPAC FILE … END OF MOPAC FILE» block with orbitals (a file of several jobs — OLDGEO —
    has one block per job). Atoms ATOM_EL, cores ATOM_CORE; the geometry ATOM_X_OPT, else ATOM_X (Å) — the one the
    orbitals belong to. The basis: AO_ATOMINDEX, ATOM_SYMTYPE (S, PX, PY, PZ, X2, XZ, Z2, YZ, XY, the labels of
    openmopac src/output/to_screen.F90), AO_ZETA, ATOM_PQN; one Gaussian shell per s, per p (x, y, z) and per d of an
    atom; the d coefficients are permuted from the MOPAC order X2 (x² − y²), XZ, Z2, YZ, XY to the order of gto.py (z²,
    xz, yz, x² − y², xy). Orbitals: EIGENVECTORS (one orbital after another, nbasis numbers each) numbered by SET_OF_MOS
    (lower, upper: MOPAC prints 10 orbitals on either side of the frontier unless LARGE or AUX(MOS=n) is given),
    EIGENVALUES (eV), MOLECULAR_ORBITAL_OCCUPANCIES, M.O.SYMMETRY_LABELS; UHF: the same items with ALPHA_ / BETA_ in
    front and SET_OF_ALPHA_MOS, SET_OF_BETA_MOS. The occupied orbitals below the printed window (benzene: 1-5, TiCl4:
    1-6) are needed for the density and the charges: the density matrix of the file (TOTAL_DENSITY_MATRIX; UHF ALPHA_
    and BETA_DENSITY_MATRIX) minus the printed occupied orbitals is n times the projector on their space (n = 2, UHF 1);
    its eigenvectors with the eigenvalue n are kept as OrbitalSet.unlisted (not shown in the table: their energies are
    not in the file). Check against MOPAC itself: the overlap of the fitted functions is compared with OVERLAP_MATRIX of
    the file (lower triangle by rows, printed with 4 decimals); deviation = max |S - S_MOPAC|. The sign of the d
    functions is not written in the file: a d type (z², xz, yz, x² − y², xy) whose overlaps with the other atoms come
    out with the opposite sign is flipped on every atom (its coefficients too); a type with no overlap to other atoms
    keeps the gto.py sign. Above TOLERANCE the file is refused (ValueError) — a basis that does not reproduce MOPAC's
    overlaps would draw wrong orbitals.
§3 APPLICATIONS
    orbital_files.read_orbitals (kind 'mopac'), the orbital window and the density panel of Spectrum: the .aux next to a
    MOPAC output is its orbital file (workspace.find_molden).
§4 SPECIFICATION
    has_orbitals(text) -> bool (a MOPAC .aux with eigenvectors).
    read_mopac_orbitals(text) -> orbitals.OrbitalSet with zdo=True (Mulliken = Coulson charges), energies in hartree,
        source 'MOPAC <version> <method>', convention 'Slater → K Gaussians', deviation = max |S - S_MOPAC| (nan when
        the file has no overlap matrix: AUX(XS)).
    ValueError: no orbitals; compressed orbitals (AUX(COMP), MOZYME); an unknown label; f functions; overlap off.
§5 PROCEDURES - below.
§6 NOTES
    TOLERANCE = 2e-3: the printed overlaps are rounded to 5e-5; with the K = 6 fit the largest deviation over the
    reference files of tests/data/mopac is 1.7e-4 (benzene); a wrong exponent, quantum number or sign changes
    overlaps by 1e-2 or more.
    HARTREE_EV = 27.211386245988 (CODATA 2018), as modules/compass/actions/surface_actions.py.
    Verified 2026-11-02 on PM7 outputs of MOPAC 23.2.5 with d functions (H2S, SO2: d on S; TiCl4: 3d on Ti, d on Cl):
    the d functions of MOPAC are the unit-normalized real harmonics of gto.py with the same signs (no type flipped;
    overlaps within 1.2e-4); the flip stays as a guard for other versions.
§7 TESTS
    tests/spectrum/test_mopac_orbitals.py.
§8' ROBUSTNESS
    Counts are checked against the [n] of the items; a block without EIGENVECTORS is skipped.
"""

import re

import numpy as np

from azimuth.core import read_xyz
from modules.compass.chemistry.geometry_tools import BOHR
from modules.spectrum.analysis.gto import Shell, overlap
from modules.spectrum.readers.mopac import ITEM, _number
from modules.spectrum.analysis.orbitals import Orbital, OrbitalSet
from modules.spectrum.analysis.sto_fits import FITS

TOLERANCE = 2e-3
HARTREE_EV = 27.211386245988
L_OF = {'S': 0, 'PX': 1, 'PY': 1, 'PZ': 1, 'X2': 2, 'XZ': 2, 'Z2': 2, 'YZ': 2, 'XY': 2}
P_ORDER = ('PX', 'PY', 'PZ')  # gto.cartesian(1): x, y, z
D_ORDER = ('Z2', 'XZ', 'YZ', 'X2', 'XY')  # gto.pure_order(2): m = 0, +1, -1, +2, -2


def _blocks(text):
    parts = re.split(r'^\s*START OF MOPAC FILE\s*$', text, flags=re.M)
    return parts[1:] if len(parts) > 1 else [text]


def _items(block):
    """{key: [tokens of each occurrence]} in the order of the file; «#» lines are comments."""
    items, current = {}, None
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith('#') or stripped.startswith('END OF MOPAC FILE'):
            continue
        m = ITEM.match(line)
        if m:
            current = m[4].split()
            items.setdefault(m[1], []).append((int(m[3]) if m[3] else None, current))
        elif current is not None and stripped:
            current.extend(line.split())
    return items


def _get(items, key, kind=float):
    found = items.get(key)
    if not found:
        return None
    count, tokens = found[-1]
    values = [kind(t) if kind is not float else _number(t) for t in tokens]
    if count is not None and len(values) != count:
        raise ValueError(f'{key}: {len(values)} values instead of {count}')
    return values


def has_orbitals(text):
    head = text[:4000]
    return 'START OF MOPAC FILE' in head and bool(re.search(r'^\s*(ALPHA_)?EIGENVECTORS\[', text, re.M))


def _basis(items, centres):
    owners = _get(items, 'AO_ATOMINDEX', int)
    labels = _get(items, 'ATOM_SYMTYPE', str)
    zetas = _get(items, 'AO_ZETA')
    pqn = _get(items, 'ATOM_PQN', int)
    if not owners or not labels or not zetas or not pqn or not len(owners) == len(labels) == len(zetas) == len(pqn):
        raise ValueError('the .aux has no complete basis (AO_ATOMINDEX, ATOM_SYMTYPE, AO_ZETA, ATOM_PQN)')
    shells, order = [], []  # order: for every function of the shells, its index in the MOPAC list
    k = 0
    while k < len(labels):
        label = labels[k].upper()
        if label not in L_OF:
            raise ValueError(f'unknown MOPAC basis function {labels[k]!r}')
        l = L_OF[label]
        size = 2 * l + 1
        group = list(range(k, k + size))
        names = [labels[j].upper() for j in group]
        wanted = {0: ('S',), 1: P_ORDER, 2: D_ORDER}[l]
        if len(group) != size or sorted(names) != sorted(wanted) or len({owners[j] for j in group}) != 1:
            raise ValueError(f'MOPAC basis functions {names} of atom {owners[k]} are not a complete shell')
        n, zeta = pqn[k], zetas[k]
        if (n, l) not in FITS:
            raise ValueError(f'no Gaussian fit for a Slater function n = {n}, l = {l}')
        exponents, coefficients = FITS[(n, l)]
        shells.append(Shell(owners[k] - 1, l, l == 2, np.asarray(exponents) * zeta * zeta, coefficients))
        order.extend(group[names.index(w)] for w in wanted)
        k += size
    if max(owners) > len(centres):
        raise ValueError('AO_ATOMINDEX refers to an atom that is not in the file')
    return shells, np.array(order), labels


def _lower_triangle(values, n):
    if len(values) != n * (n + 1) // 2:
        raise ValueError('OVERLAP_MATRIX does not fit the basis')
    s = np.zeros((n, n))
    rows, cols = np.tril_indices(n)
    s[rows, cols] = values
    s[cols, rows] = values
    return s


def _check(shells, centres, order, printed):
    """Signs of the d functions (in shell order) and the deviation from the MOPAC overlap (nan: not printed).

    The sign is a convention of the program, the same for every atom: it is decided per d type (z², xz, yz, x² − y²,
    xy) from all overlaps of the functions of that type with the other atoms; a type without such overlaps keeps
    the sign of gto.py."""
    ours = overlap(shells, centres)
    n = len(order)
    signs = np.ones(n)
    if printed is None:
        return signs, float('nan')
    theirs = _lower_triangle(printed, n)[np.ix_(order, order)]
    owners = np.concatenate([[s.centre] * s.size for s in shells])
    same, flipped = np.zeros(5), np.zeros(5)
    members = [[] for _ in range(5)]
    start = 0
    for shell in shells:
        if shell.l == 2:
            for m in range(5):
                j = start + m
                other = owners != owners[j]
                same[m] += np.sum(np.abs(ours[j, other] - theirs[j, other]))
                flipped[m] += np.sum(np.abs(ours[j, other] + theirs[j, other]))
                members[m].append(j)
        start += shell.size
    for m in range(5):
        if flipped[m] < same[m]:
            signs[members[m]] = -1.0
    ours = ours * np.outer(signs, signs)
    return signs, float(np.max(np.abs(ours - theirs)))


def _unlisted(items, missing, order, signs, nbasis):
    """The occupied orbitals below SET_OF_MOS: the density matrix of the file minus the listed occupied orbitals is the
    projector on their space times the occupation (2, UHF 1); its eigenvectors with that eigenvalue are a basis of it
    (any orthonormal basis gives the same density)."""
    vectors, occupations, spins = [], [], []
    for spin, prefix, count, listed, listed_occupations in missing:
        key = {'': 'TOTAL_DENSITY_MATRIX', 'ALPHA_': 'ALPHA_DENSITY_MATRIX', 'BETA_': 'BETA_DENSITY_MATRIX'}[prefix]
        printed = _get(items, key)
        if printed is None:
            raise ValueError(f'MOPAC printed orbitals from number {count + 1} on and no {key}: the density would be '
                             'incomplete; compute with AUX(MOS=99999) or LARGE')
        unit = 2.0 if prefix == '' else 1.0
        density = _lower_triangle(printed, nbasis)[np.ix_(order, order)] * np.outer(signs, signs)
        for c, n in zip(listed, listed_occupations):
            density -= n * np.outer(c, c)
        values, eigenvectors = np.linalg.eigh(density)
        keep = values > 0.5 * unit
        if int(keep.sum()) != count or np.max(np.abs(values[keep] - unit)) > 0.02:
            raise ValueError(f'the {key} of the .aux does not hold the {count} occupied orbitals that were not printed '
                             f'(found {int(keep.sum())}); compute with AUX(MOS=99999) or LARGE')
        vectors.append(eigenvectors[:, keep])
        occupations += [unit] * count
        spins += [spin] * count
    return np.hstack(vectors), np.array(occupations), tuple(spins)


def _spin_sets(items):
    if items.get('ALPHA_EIGENVECTORS'):
        return (('alpha', 'ALPHA_', 'SET_OF_ALPHA_MOS'), ('beta', 'BETA_', 'SET_OF_BETA_MOS'))
    return (('alpha', '', 'SET_OF_MOS'),)


def read_mopac_orbitals(text):
    block = None
    for candidate in reversed(_blocks(text)):
        items = _items(candidate)
        if items.get('EIGENVECTORS') or items.get('ALPHA_EIGENVECTORS'):
            block = items
            break
    if block is None:
        if 'EIGENVECTOR_COEFFICIENTS' in text:
            raise ValueError('the orbitals of this .aux are compressed (AUX(COMP) or MOZYME); compute without COMP')
        raise ValueError('the .aux has no orbitals (EIGENVECTORS)')
    items = block
    symbols = _get(items, 'ATOM_EL', str)
    xyz = _get(items, 'ATOM_X_OPT') or _get(items, 'ATOM_X')
    if not symbols or not xyz or len(xyz) != 3 * len(symbols):
        raise ValueError('the .aux has no geometry of the orbitals (ATOM_EL, ATOM_X_OPT)')
    method = (items.get('METHOD') or [(None, ['MOPAC'])])[-1][1]
    source = 'MOPAC ' + (method[0] if method else '')
    rows = '\n'.join(f'{s} {xyz[3 * i]} {xyz[3 * i + 1]} {xyz[3 * i + 2]}' for i, s in enumerate(symbols))
    molecule = read_xyz(f'{len(symbols)}\n{source}\n{rows}')
    centres = np.array([a.position for a in molecule.atoms], float) / BOHR
    shells, order, _ = _basis(items, centres)
    nbasis = len(order)
    signs, deviation = _check(shells, centres, order, _get(items, 'OVERLAP_MATRIX'))
    if deviation > TOLERANCE:
        raise ValueError(f'the Gaussian form of the MOPAC basis does not reproduce its overlap matrix '
                         f'(max deviation {deviation:.3g} > {TOLERANCE:g})')
    orbitals, columns, missing = [], [], []
    for spin, prefix, set_key in _spin_sets(items):
        vectors = _get(items, prefix + 'EIGENVECTORS')
        energies = _get(items, prefix + 'EIGENVALUES')
        occupations = _get(items, prefix + 'MOLECULAR_ORBITAL_OCCUPANCIES')
        if not vectors or len(vectors) % nbasis:
            raise ValueError(f'{prefix}EIGENVECTORS does not fit the basis of {nbasis} functions')
        count = len(vectors) // nbasis
        bounds = (items.get(set_key) or [(None, ['1', str(count)])])[-1][1]
        lower = int(bounds[0])
        if not energies or len(energies) != count or (occupations and len(occupations) != count):
            raise ValueError(f'{prefix}EIGENVALUES do not match the {count} orbitals')
        found = items.get(prefix + 'M.O.SYMMETRY_LABELS')
        labels = found[-1][1] if found and len(found[-1][1]) == count else [''] * count
        matrix = np.array(vectors).reshape(count, nbasis)  # one orbital per row, MOPAC order
        for k in range(count):
            occupation = occupations[k] if occupations else 0.0
            orbitals.append(Orbital(lower + k, spin, energies[k] / HARTREE_EV, occupation, labels[k]))
            columns.append(matrix[k, order] * signs)
        if lower > 1:  # orbitals 1 .. lower-1 not printed: all occupied
            missing.append((spin, prefix, lower - 1, [np.array(columns[-count + k]) for k in range(count)],
                            [o.occupation for o in orbitals[-count:]]))
    coefficients = np.array(columns).T
    unlisted = _unlisted(items, missing, order, signs, nbasis) if missing else None
    return OrbitalSet(
        source,
        molecule,
        tuple(float(c) for c in (_get(items, 'ATOM_CORE') or [0] * len(symbols))),
        tuple(shells),
        centres,
        tuple(orbitals),
        coefficients,
        f'Slater → {len(FITS[(1, 0)][0])} Gaussians',
        deviation,
        source,
        zdo=True,
        unlisted=unlisted,
    )

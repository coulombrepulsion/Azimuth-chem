"""Molecular orbitals of a calculation: the common part of all readers, fields on a grid.

§1 THEORY
    A molecular orbital is psi_i = sum_mu C_mu,i phi_mu over the contracted Gaussian basis functions
    phi_mu (modules/spectrum/analysis/gto.py). The orbitals of an SCF calculation are orthonormal:
    C^T S C = 1 with the overlap matrix S of the basis. The electron density is
    rho = sum_i n_i |psi_i|^2 (occupation numbers n_i), the spin density the alpha minus the beta part.
    Mulliken charges: q_A = Z_A - sum_{mu on A} (P S)_mu,mu with P = sum_i n_i C_i C_i^T.
    Files do not always say how their primitives are normalized or which sign their spherical
    functions have; the orthonormality of the orbitals tells which convention a file follows.
§2 ALGORITHM
    select(candidates, ...): the candidate conventions of a reader (shells and a factor per orbital
    coefficient) are tried in order; the first with max |C^T S C - 1| below the tolerance (per spin) is
    kept, else ValueError with the smallest deviation found. Tolerance: the coefficients are printed
    rounded, C = C0 + E with |E| <= Delta (half a unit of the last digit, half_unit()); for exactly
    orthonormal C0, |C^T S C - 1| <= Delta^T |S C| + |S C|^T Delta + Delta^T |S| Delta (entrywise) to
    first order — twice its largest entry, but at least FLOOR, is allowed.
    grid_for: an axis-aligned box around the atoms with MARGIN on every side; the step grows by 10 %
    until the box has at most max_points points. Fields: gto.on_grid for one orbital; the density sums
    n_i psi_i^2 over the occupied orbitals.
§3 APPLICATIONS
    modules/spectrum/readers/orbital_files.py (Molden, Gaussian fchk, ORCA output) and orbitals_view.py.
§4 SPECIFICATION
    Orbital(number from 1 in the file order within its spin, spin 'alpha' | 'beta', energy hartree,
        occupation, symmetry str).
    OrbitalSet(title, molecule (Molecule, angstrom), charges (nuclear charges, effective with ECP), shells,
        centres (bohr), orbitals (tuple of Orbital), coefficients (nbasis, norbitals) in the same order,
        convention str, deviation float, source str = program/format, zdo bool = False: 0.91.6, orbitals
        orthonormal with the unit metric (MOPAC, NDDO) — mulliken() gives the Coulson charges Z_A - sum P_mu,mu).
        unlisted = None | (coefficients (nbasis, k), occupations (k), spins): occupied orbitals the file does
        not list (MOPAC writes only some), as a basis of their space; .occupied(spin=False) -> (coefficients, weights)
        of all occupied orbitals — every density (here, density.py) goes through it.
        .unrestricted; .frontier(spin='alpha') -> (index of HOMO | None, index of LUMO | None);
        .overlap() -> S; .mulliken() -> charges.
    half_unit(token str) -> float; deviation(S, C, spins, half_units=None) -> (deviation, rounding bound).
    select(candidates: iterable of (name, shells, factor (nbasis) or None), centres, coefficients, spins,
        half_units (same shape as coefficients), floor=FLOOR) -> (name, shells, coefficients, deviation).
    grid_for(orbital_set, step=0.15 A, margin=MARGIN A, max_points=MAX_POINTS) -> (origin bohr, step bohr
        (3), shape). orbital_cube(orbital_set, index, step, margin) -> modules.spectrum.readers.cube.Cube of psi
    (bohr^-3/2;
        coordinates in angstrom as the CUBE reader returns them); density_cube(orbital_set, spin=False,
        step, margin, progress=None (called with done, total; False cancels: InterruptedError)).
    write_cube(cube, path or None) -> text of a Gaussian CUBE file (coordinates in bohr).
§5 PROCEDURES - below.
§6 NOTES
    FLOOR = 1e-4: the bound above covers the orbital coefficients only; exponents, contraction
    coefficients and coordinates are printed rounded too (a Molden file of the Molden program with 4-5
    digits deviates by 3.5e-5). A wrong normalization or sign convention gives deviations of 1e-2..1.
    MARGIN = 4 A, as orca_plot (7 bohr = 3.7 A); MAX_POINTS = 2,000,000 = the limit of the CUBE reader.
    BOHR from modules.compass.chemistry.geometry_tools (as the CUBE reader).
§7 TESTS
    tests/spectrum/test_orbitals.py.
§8' ROBUSTNESS
    Grid steps 0.02-1 A, margins 0.5-15 A; other values raise ValueError.
"""

from dataclasses import dataclass
from math import sqrt

import numpy as np

from modules.spectrum.analysis.gto import on_grid, overlap, radial_norm
from azimuth.core import Molecule
from modules.compass.chemistry.geometry_tools import BOHR

MARGIN = 4.0
MAX_POINTS = 2_000_000
MAX_BASIS = 2000
FLOOR = 1e-4


@dataclass(frozen=True)
class Orbital:
    number: int
    spin: str
    energy: float
    occupation: float
    symmetry: str = ''


@dataclass(frozen=True, eq=False)
class OrbitalSet:
    title: str
    molecule: Molecule
    charges: tuple
    shells: tuple
    centres: np.ndarray
    orbitals: tuple
    coefficients: np.ndarray
    convention: str
    deviation: float
    source: str = ''
    zdo: bool = False  # MOPAC (NDDO): C^T C = 1, Coulson charges (mopac_orbitals.py)
    unlisted: object = None  # (coefficients (nbasis, k), occupations (k,), spins) of occupied orbitals not in the file

    @property
    def unrestricted(self):
        return any(o.spin == 'beta' for o in self.orbitals)

    def frontier(self, spin='alpha'):
        own = [k for k, o in enumerate(self.orbitals) if o.spin == spin]
        occupied = [k for k in own if self.orbitals[k].occupation > 1e-6]
        homo = max(occupied, key=lambda k: self.orbitals[k].energy) if occupied else None
        empty = [k for k in own if self.orbitals[k].occupation <= 1e-6]
        lumo = min(empty, key=lambda k: self.orbitals[k].energy) if empty else None
        return homo, lumo

    def occupied(self, spin=False):
        """(coefficients (nbasis, k), weights (k)) of every occupied orbital — the listed ones, then those the
        file left out (unlisted: a basis of their space, rebuilt from the density matrix of the file); spin: beta
        weights negative (the spin density)."""
        listed = [k for k, o in enumerate(self.orbitals) if o.occupation > 1e-8]
        sign = lambda s: (-1.0 if s == 'beta' else 1.0) if spin else 1.0  # noqa: E731
        columns = self.coefficients[:, listed]
        weights = [self.orbitals[k].occupation * sign(self.orbitals[k].spin) for k in listed]
        if self.unlisted is not None:
            c, n, spins = self.unlisted
            columns = np.hstack([columns, c])
            weights += [w * sign(s) for w, s in zip(n, spins)]
        return columns, np.array(weights, dtype=float)

    def overlap(self):
        return overlap(self.shells, self.centres)

    def mulliken_spins(self):
        """The Mulliken spin population of every atom, Σ_{μ∈A} (P^α−β S)_μμ (zeros for a closed shell); they
        add up to N_α − N_β."""
        if self.unrestricted:
            c, weights = self.occupied(spin=True)
        else:  # restricted: the singly occupied levels of a ROHF / ROKS wavefunction carry the spin (none: zeros)
            single = [k for k, o in enumerate(self.orbitals) if 0.5 < o.occupation < 1.5]
            c, weights = self.coefficients[:, single], np.ones(len(single))
        density = (c * weights) @ c.T
        population = np.diag(density) if self.zdo else np.einsum('ij,ji->i', density, self.overlap())
        owners = np.concatenate([[s.centre] * s.size for s in self.shells])
        spins = np.zeros(len(self.molecule.atoms))
        np.add.at(spins, owners, population)
        return spins

    def mulliken(self):
        c, occupations = self.occupied()
        density = (c * occupations) @ c.T
        population = np.diag(density) if self.zdo else np.einsum('ij,ji->i', density, self.overlap())
        owners = np.concatenate([[s.centre] * s.size for s in self.shells])
        charges = np.array(self.charges, dtype=float)
        for k, owner in enumerate(owners):
            charges[owner] -= population[k]
        return charges


def cartesian_norm(alpha, powers):
    """Norm of the primitive x^a y^b z^c exp(-alpha r^2)."""
    from modules.spectrum.analysis.gto import _double_factorial

    l = sum(powers)
    return radial_norm(alpha, l) / sqrt(np.prod([_double_factorial(2 * n - 1) for n in powers]))


ORCA_POWERS = {0: (0, 0, 0), 1: (1, 0, 0), 2: (1, 1, 0), 3: (1, 1, 1), 4: (2, 1, 1), 5: (5, 0, 0)}


def scaled(shells, rule):
    return [s.with_coefficients(rule(s)) for s in shells]


def orca_signs(shells):
    signs = []
    for s in shells:
        f = np.ones(s.size)
        if s.pure:
            from modules.spectrum.analysis.gto import pure_order

            f = np.array([-1.0 if abs(m) in (3, 4) and s.l >= 3 else 1.0 for m in pure_order(s.l)])
        signs.append(f)
    return np.concatenate(signs)


def half_unit(token):
    """Half a unit of the last printed digit of a number written as text (its rounding error)."""
    mantissa, _, exponent = token.lower().replace('d', 'e').partition('e')
    decimals = len(mantissa.split('.')[1]) if '.' in mantissa else 0
    return 0.5 * 10.0 ** (-decimals + (int(exponent) if exponent else 0))


def deviation(s_matrix, coefficients, spins, half_units=None):
    """(max |C^T S C - 1| per spin, its bound from the rounding of the printed coefficients)."""
    worst, bound = 0.0, 0.0
    for spin in set(spins):
        columns = [k for k, x in enumerate(spins) if x == spin]
        c = coefficients[:, columns]
        sc = s_matrix @ c
        m = c.T @ sc
        worst = max(worst, float(np.max(np.abs(m - np.eye(m.shape[0])))))
        if half_units is not None:
            d = half_units[:, columns]
            b = d.T @ np.abs(sc)
            b = b + b.T + d.T @ np.abs(s_matrix) @ d
            bound = max(bound, float(np.max(b)))
    return worst, bound


def select(candidates, centres, coefficients, spins, half_units, floor=FLOOR):
    """The first candidate whose orbitals are orthonormal within max(floor, 2 x the rounding bound)."""
    best = None
    for name, shells, factor in candidates:
        if factor is None:
            c, d = coefficients, half_units
        else:
            c = coefficients * np.asarray(factor)[:, None]
            d = half_units * np.abs(np.asarray(factor))[:, None]
        found, bound = deviation(overlap(shells, centres), c, spins, d)
        tolerance = max(floor, 2 * bound)
        if best is None or found / tolerance < best[3] / best[4]:
            best = (name, shells, c, found, tolerance)
        if found < tolerance:
            return best[:4]
    raise ValueError(
        f'the orbitals are not orthonormal under any known convention (smallest deviation {best[3]:.2g},'
        f' allowed {best[4]:.1g})'
    )


def grid_for(orbital_set, step=0.15, margin=MARGIN, max_points=MAX_POINTS):
    if not (0.02 <= step <= 1.0) or not (0.5 <= margin <= 15.0):
        raise ValueError('grid step 0.02-1 A and margin 0.5-15 A')
    positions = np.array([a.position for a in orbital_set.molecule.atoms])
    low = positions.min(axis=0) - margin
    high = positions.max(axis=0) + margin
    while True:
        shape = tuple(int(np.ceil((high[k] - low[k]) / step)) + 1 for k in range(3))
        if np.prod(shape) <= max_points:
            break
        step *= 1.1
    return low / BOHR, np.full(3, step / BOHR), shape


def _cube(orbital_set, field, origin, step, title, ids=(1,)):
    from modules.spectrum.readers.cube import Cube

    return Cube(
        title,
        orbital_set.molecule,
        origin * BOHR,
        np.diag(step) * BOHR,
        field[..., None],
        tuple(ids),
        'Å',
    )


def orbital_cube(orbital_set, index, step=0.15, margin=MARGIN):
    origin, steps, shape = grid_for(orbital_set, step, margin)
    field = on_grid(orbital_set.shells, orbital_set.centres, orbital_set.coefficients[:, index], origin, steps, shape)
    o = orbital_set.orbitals[index]
    title = f'MO {o.number} {o.spin} · E = {o.energy:.6f} Eh · n = {o.occupation:g}'
    return _cube(orbital_set, field, origin, steps, title, (o.number,))


def density_cube(orbital_set, spin=False, step=0.15, margin=MARGIN, progress=None):
    origin, steps, shape = grid_for(orbital_set, step, margin)
    field = np.zeros(shape)
    columns, weights = orbital_set.occupied(spin)
    for n, weight in enumerate(weights):
        psi = on_grid(orbital_set.shells, orbital_set.centres, columns[:, n], origin, steps, shape)
        field += weight * psi * psi
        if progress is not None and progress(n + 1, len(weights)) is False:
            raise InterruptedError('cancelled')
    return _cube(orbital_set, field, origin, steps, 'spin density' if spin else 'electron density')


def write_cube(cube, path=None):
    from azimuth.core import SYMBOLS as symbols

    values = cube.values[..., 0]
    nx, ny, nz = values.shape
    lines = [cube.title.replace('\n', ' ')[:80], 'Azimuth: values in atomic units, coordinates in bohr']
    origin = np.asarray(cube.origin) / BOHR
    axes = np.asarray(cube.axes) / BOHR
    lines.append(f'{len(cube.molecule.atoms):5d} {origin[0]:12.6f} {origin[1]:12.6f} {origin[2]:12.6f}')
    for n, axis in zip((nx, ny, nz), axes):
        lines.append(f'{n:5d} {axis[0]:12.6f} {axis[1]:12.6f} {axis[2]:12.6f}')
    for atom in cube.molecule.atoms:
        z = symbols.index(atom.symbol) + 1
        x, y, w = (np.asarray(atom.position) / BOHR).tolist()
        lines.append(f'{z:5d} {float(z):12.6f} {x:12.6f} {y:12.6f} {w:12.6f}')
    body = []
    for i in range(nx):
        for j in range(ny):
            row = values[i, j]
            for start in range(0, nz, 6):
                body.append(' '.join(f'{v:13.5E}' for v in row[start : start + 6]))
    text = '\n'.join(lines + body) + '\n'
    if path is not None:
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(text)
    return text

"""Electron density analysis from the orbitals of a calculation: ∇ρ, ∇²ρ, Δρ, QTAIM critical points, bond paths and
slices.

HEADER The orbitals of a Molden file, a Gaussian .fchk or an ORCA output (modules/spectrum/analysis/orbitals.py) give
    the electron density ρ(r) = Σ_i n_i ψ_i(r)² everywhere, and with it everything the quantum theory of atoms in
    molecules (Bader, «Atoms in Molecules», 1990) reads from it: where the density has its critical points, how it is
    concentrated (−∇²ρ), how it moved on forming the molecule (Δρ). Everything is analytic in the Gaussian basis: the
    first and second derivatives of every basis function are written out, no finite differences. Wilkinson convention,
    sections 1-8.

§1 THEORY
    A primitive x^a y^b z^c e^{−α r²} is a product over the axes of f_n(x) = x^n e^{−α x²}, with
        f_n' = n x^{n−1} e − 2α x^{n+1} e, f_n'' = n(n−1) x^{n−2} e − 2α(2n+1) x^n e + 4α² x^{n+2} e,
    so ∂φ/∂x = f_a' f_b f_c, ∂²φ/∂x∂y = f_a' f_b' f_c, ∂²φ/∂x² = f_a'' f_b f_c, and ∇²φ the sum of the three.
    With the density matrix P = C diag(n) Cᵀ: ρ = φᵀPφ, ∇ρ = 2 Σ P_μν φ_μ ∇φ_ν, the Hessian
    ∂²ρ/∂x_k∂x_l = 2 Σ P_μν (∂_k φ_μ ∂_l φ_ν + φ_μ ∂_k∂_l φ_ν), ∇²ρ its trace; the positive kinetic energy density
    G = ½ Σ_i n_i |∇ψ_i|² = ½ Σ P_μν ∇φ_μ·∇φ_ν, the potential energy density from the local virial theorem
    V = ¼∇²ρ − 2G, the energy density H = G + V (Cremer and Kraka 1984: H < 0 — a shared, covalent interaction).
    On a grid, per orbital: ∇²ρ = Σ_i n_i (2 ψ_i ∇²ψ_i + 2 |∇ψ_i|²).
    A critical point (∇ρ = 0) is classified by the signs of the eigenvalues λ1 ≤ λ2 ≤ λ3 of the Hessian:
    (3, −3) a maximum (a nucleus), (3, −1) a bond critical point (BCP), (3, +1) a ring, (3, +3) a cage point. At a
    BCP the ellipticity ε = λ1/λ2 − 1 (0 for a cylindrical bond, 0.2–0.3 for a double bond). The bond path is the
    pair of gradient lines that leave the BCP along the eigenvector of λ3 and end at two nuclei. For an isolated
    molecule the numbers obey the Poincaré–Hopf relation n − b + r − c = 1.
    The difference density Δρ = ρ(molecule) − Σ ρ(fragments), the fragments computed separately at the same positions
    of their atoms; ∫Δρ dV = N(molecule) − Σ N(fragments).
    −∇²ρ > 0 where the density is locally concentrated (the valence shells, lone pairs), < 0 where it is depleted.

§2 ALGORITHM
    basis_values(shells, centres, points, order): φ (m, N), ∇φ (m, N, 3), the Hessian (m, N, 3, 3) of the basis
    functions at points (bohr), per shell and primitive with the 1D factors of §1. density_at(orbital_set, points,
    order): ρ, ∇ρ, the Hessian, ∇²ρ and G at points, in chunks of CHUNK points.
    on_grid_derivatives(shells, centres, vector, origin, step, shape): ψ, ∂ψ/∂x, ∂ψ/∂y, ∂ψ/∂z, ∇²ψ of one orbital on
    the grid of orbitals.grid_for, separably (outer products of the 1D factors over the sub-box of every primitive,
    as gto.on_grid). laplacian_cube: −∇²ρ on the grid. density_on(orbital_set, origin, step, shape): ρ on a given
    grid. difference_cube(molecule, fragments): match_fragments (every atom of a fragment on an atom of the molecule
    within MATCH Å, every atom of the molecule used once) and ρ − Σ ρ_f on the grid of the molecule.
    critical_points(orbital_set): Newton steps x ← x − H⁻¹∇ρ (a step longer than MAX_STEP bohr is shortened) from
    the midpoints of the bonds (modules/compass/chemistry/builder.connections) and from the centroids of the rings (the
    smallest cycle through every bond, up to RING_MAX atoms), all starts at once, until |∇ρ| < GRAD_TOL; the points
    within MERGE bohr of each other merge; the nuclei are the (3, −3) points by definition (one per atom). From every
    BCP the two gradient lines are followed up the density (Heun steps of PATH_STEP bohr, the step normalised) until
    they come within ARRIVE bohr of a nucleus: the bond path and its two atoms.
    Topology_from(cps, orbital_set=None): the critical points found by Multiwfn (multiwfn.parse_cps) as a
    Topology; the bond paths are traced here from every BCP of Multiwfn along the eigenvector of its λ3 (as above),
    the atoms of a bond are those Multiwfn names, or the two nuclei the traced path ends at; n is the number
    of maxima (3, −3) Multiwfn found, kept as Topology.nuclei (with the atom of each).
    plane(orbital_set, atoms): an origin and two orthonormal axes through three atoms; slice_values: ρ, ∇²ρ or Δρ on a
    square grid of that plane.
    contours(values, xs, ys, level): marching squares (saddle cells decided by the mean of the corners).
§3 APPLICATIONS modules/spectrum/views/density_view.py («Анализ ЭП…» in the orbital window): −∇²ρ and Δρ on the Compass
    model (modules/compass/actions/surface_actions.py, kinds 'laplacian' and 'difference'), the critical points and bond
    paths on the model (show_aim), the table, the slice map.
§4 SPECIFICATION
    basis_values(shells, centres, points (m, 3) bohr, order=0|1|2) -> (φ, ∇φ | None, Hessian | None).
    density_at(orbital_set, points (m, 3) bohr, order=2, spin=False) -> dict rho (m), grad (m, 3), hess (m, 3, 3),
        laplacian (m), kinetic (m) — atomic units.
    on_grid_derivatives(...) -> (ψ, gx, gy, gz, lap) arrays of the grid shape.
    laplacian_cube(orbital_set, step=0.15, margin=MARGIN, progress=None) -> Cube of −∇²ρ (e/bohr⁵).
    density_on(orbital_set, origin, step, shape, spin=False, progress=None) -> array.
    difference_cube(molecule_set, fragment_sets, step=0.15, margin=MARGIN, progress=None) -> (Cube of Δρ, ∫Δρ dV).
    match_fragments(molecule, fragments) -> list of index lists; ValueError with a message when they do not fit.
    fukui_cubes(n_set, anion_set, cation_set, step=0.15, margin=MARGIN, progress=None) -> ({'plus' | 'minus' | 'zero' |
        'dual': Cube}, {same keys: ∫ dV}): f⁺ = ρ(N+1) − ρ(N), f⁻ = ρ(N) − ρ(N−1), f⁰ = (f⁺ + f⁻)/2,
        Δf = f⁺ − f⁻ on the grid of N; the three wavefunctions on one geometry (match_fragments), N ± 1 electrons.
    critical_points(orbital_set) -> Topology(points (tuple of CriticalPoint), paths (tuple of (n, 3) arrays, Å, one per
        bond point: nucleus → BCP → nucleus),
        counts {'n', 'b', 'r', 'c'}, poincare_hopf int, notes).
    CriticalPoint(kind 'bond' | 'ring' | 'cage' | 'nucleus', position Å (3), rho, laplacian, eigenvalues (3),
        ellipticity | None, kinetic G, potential V, energy H, atoms (i, j) | ()).
    plane(orbital_set, atoms=None) -> (origin Å, u, v); slice_values(orbital_set, origin, u, v, half, n, field,
        fragments=()) -> (xs Å, ys Å, values (n, n)); contours(values, xs, ys, level) -> (k, 2, 2) segments.
    ValueError for invalid input (no occupied orbitals, a grid out of the bounds of orbitals.grid_for, collinear
    atoms of a plane, fragments that do not fit).
§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    CHUNK = 1500 points: φ, ∇φ and the Hessian of 1500 points and 1000 basis functions take 120 MB. The density
    matrix includes both spins (UHF: P = Pα + Pβ; spin=True: Pα − Pβ). With an effective core potential the core
    electrons are not in the orbitals: ρ has no core and the nuclear maximum may be missing (reported in notes).
    Starting points: bonds as Compass draws them; a BCP that Compass does not draw a bond for (a weak contact) is
    not searched for. Constants: MAX_STEP = 0.3, GRAD_TOL = 1e-8 (au), MERGE = 0.05, PATH_STEP = 0.05, ARRIVE = 0.1
    bohr, MATCH = 0.02 Å, RING_MAX = 8 atoms. A Gaussian basis has no cusp: near a hydrogen the maximum of ρ can sit
    ~0.1–0.2 bohr off the nucleus, so a gradient line also ends where |∇ρ| < PATH_GTOL = 1e-4 au within
    NEAR_NUCLEUS = 0.6 bohr of a nucleus.
§7 TEST CASES (tests/spectrum/test_density.py)
    ρ at points equals orbitals.density_cube on its grid; the analytic gradient and Hessian equal central
    differences of ρ (h = 1e-4 bohr); ∇²ψ on the grid equals the trace of the Hessian at the same points;
    water (GAMESS, Molden): two O–H BCPs closer to H than to O, ρ_BCP 0.30–0.42 au, ∇²ρ < 0, H < 0, ε < 0.05,
    bond paths from O to H, n − b + r − c = 1; divinylbenzene: 20 BCPs, one ring point at the centre of the
    benzene ring, Poincaré–Hopf holds; Δρ of a molecule minus itself is zero, fragments that do not fit are
    refused; marching squares on x² + y² = 1 lies on the unit circle.
§8 ERROR ANALYSIS
    The values are those of the basis-set density (no grid error at points); on a grid only the position of an
    isosurface carries the step. Newton converges quadratically near a CP; GRAD_TOL 1e-8 au places it within
    ~1e-8/|λ| bohr. Bond paths: Heun steps of 0.05 bohr follow a gradient line within ~1e-3 bohr over a bond."""

from __future__ import annotations

from dataclasses import dataclass, field
from math import sqrt

import numpy as np

from modules.spectrum.analysis.gto import CUTOFF
from modules.spectrum.analysis.orbitals import MARGIN, _cube, grid_for
from modules.compass.chemistry.geometry_tools import BOHR
from azimuth.i18n import tr

CHUNK = 1500
MAX_STEP = 0.3
GRAD_TOL = 1e-8
MERGE = 0.05
PATH_STEP = 0.05
ARRIVE = 0.1
MATCH = 0.02
RING_MAX = 8
NEWTON_STEPS = 80
PATH_GTOL = 1e-4  # au: |∇ρ| at which a gradient line has reached its maximum
NEAR_NUCLEUS = 0.6  # bohr: a maximum this close to a nucleus belongs to it
PATH_STEPS = 400


def _xp(x, n):
    """x**n with x**n = 0 for n < 0 (the derivative of x^0)."""
    if n < 0:
        return np.zeros_like(x)
    return x**n if n else np.ones_like(x)


def _factors(x, n, alpha):
    """f_n/e, f_n'/e, f_n''/e of §1 (the Gaussian factor e is applied by the caller)."""
    f0 = _xp(x, n)
    f1 = n * _xp(x, n - 1) - 2 * alpha * _xp(x, n + 1)
    f2 = n * (n - 1) * _xp(x, n - 2) - 2 * alpha * (2 * n + 1) * _xp(x, n) + 4 * alpha * alpha * _xp(x, n + 2)
    return f0, f1, f2


def basis_values(shells, centres, points, order=0):
    centres = np.asarray(centres, dtype=float)
    points = np.atleast_2d(np.asarray(points, dtype=float))
    m = len(points)
    total = sum(s.size for s in shells)
    phi = np.zeros((m, total))
    grad = np.zeros((m, total, 3)) if order >= 1 else None
    hess = np.zeros((m, total, 3, 3)) if order >= 2 else None
    start = 0
    for shell in shells:
        rel = points - centres[shell.centre]
        r2 = np.einsum('ij,ij->i', rel, rel)
        nc = len(shell.monomials)
        cart = np.zeros((m, nc))
        cg = np.zeros((m, nc, 3)) if order >= 1 else None
        ch = np.zeros((m, nc, 3, 3)) if order >= 2 else None
        for alpha, d in zip(shell.exponents, shell.radial()):
            if d == 0:
                continue
            e = d * np.exp(-alpha * r2)
            for c, powers in enumerate(shell.monomials):
                f = [_factors(rel[:, k], powers[k], alpha) for k in range(3)]
                cart[:, c] += e * f[0][0] * f[1][0] * f[2][0]
                if order >= 1:
                    cg[:, c, 0] += e * f[0][1] * f[1][0] * f[2][0]
                    cg[:, c, 1] += e * f[0][0] * f[1][1] * f[2][0]
                    cg[:, c, 2] += e * f[0][0] * f[1][0] * f[2][1]
                if order >= 2:
                    for k in range(3):
                        for l in range(k, 3):
                            if k == l:
                                parts = [f[a][2 if a == k else 0] for a in range(3)]
                            else:
                                parts = [f[a][1 if a in (k, l) else 0] for a in range(3)]
                            value = e * parts[0] * parts[1] * parts[2]
                            ch[:, c, k, l] += value
                            if k != l:
                                ch[:, c, l, k] += value
        a = shell.angular  # (size, ncart)
        phi[:, start : start + shell.size] = cart @ a.T
        if order >= 1:
            grad[:, start : start + shell.size] = np.einsum('mck,sc->msk', cg, a)
        if order >= 2:
            hess[:, start : start + shell.size] = np.einsum('mckl,sc->mskl', ch, a)
        start += shell.size
    return phi, grad, hess


def density_matrix(orbital_set, spin=False):
    c, weights = orbital_set.occupied(spin)  # with the orbitals the file did not list
    if not np.any(np.abs(weights) > 1e-12):
        raise ValueError(tr('В файле нет занятых орбиталей: плотность не построить.'))
    return (c * weights) @ c.T


def density_at(orbital_set, points, order=2, spin=False, matrix=None):
    points = np.atleast_2d(np.asarray(points, dtype=float))
    p = density_matrix(orbital_set, spin) if matrix is None else matrix
    m = len(points)
    out = {'rho': np.zeros(m)}
    if order >= 1:
        out['grad'] = np.zeros((m, 3))
        out['kinetic'] = np.zeros(m)
    if order >= 2:
        out['hess'] = np.zeros((m, 3, 3))
    for lo in range(0, m, CHUNK):
        hi = min(m, lo + CHUNK)
        phi, grad, hess = basis_values(orbital_set.shells, orbital_set.centres, points[lo:hi], order)
        pphi = phi @ p
        out['rho'][lo:hi] = np.einsum('mi,mi->m', pphi, phi)
        if order >= 1:
            out['grad'][lo:hi] = 2 * np.einsum('mi,mik->mk', pphi, grad)
            pg = np.einsum('mik,ij->mjk', grad, p)  # Σ_μ P_μν ∂_k φ_μ
            gg = np.einsum('mjk,mjl->mkl', pg, grad)
            out['kinetic'][lo:hi] = 0.5 * np.einsum('mkk->m', gg)
        if order >= 2:
            out['hess'][lo:hi] = 2 * (gg + np.einsum('mi,mikl->mkl', pphi, hess))
    if order >= 2:
        out['laplacian'] = np.einsum('mkk->m', out['hess'])
    return out


def on_grid_derivatives(shells, centres, vector, origin, step, shape):
    centres = np.asarray(centres, dtype=float)
    vector = np.asarray(vector, dtype=float)
    origin = np.asarray(origin, dtype=float)
    step = np.asarray(step, dtype=float)
    axes = [origin[k] + step[k] * np.arange(shape[k]) for k in range(3)]
    psi, gx, gy, gz, lap = (np.zeros(shape) for _ in range(5))
    start = 0
    for shell in shells:
        weights = shell.angular.T @ vector[start : start + shell.size]
        start += shell.size
        if not np.any(weights):
            continue
        centre = centres[shell.centre]
        for alpha, d in zip(shell.exponents, shell.radial()):
            if d == 0:
                continue
            reach = sqrt(-2 * np.log(CUTOFF) / alpha) * 1.2  # a little further: the derivatives decay later
            ranges = []
            for k in range(3):
                lo = int(np.searchsorted(axes[k], centre[k] - reach, 'left'))
                hi = int(np.searchsorted(axes[k], centre[k] + reach, 'right'))
                ranges.append((lo, hi))
            if any(hi <= lo for lo, hi in ranges):
                continue
            xs = [axes[k][ranges[k][0] : ranges[k][1]] - centre[k] for k in range(3)]
            gauss = [np.exp(-alpha * x * x) for x in xs]
            sl = tuple(slice(lo, hi) for lo, hi in ranges)
            for w, powers in zip(weights, shell.monomials):
                if not w:
                    continue
                f = [[g * part for part in _factors(xs[k], powers[k], alpha)] for k, g in enumerate(gauss)]
                o = np.multiply.outer
                dw = d * w
                psi[sl] += dw * o(o(f[0][0], f[1][0]), f[2][0])
                gx[sl] += dw * o(o(f[0][1], f[1][0]), f[2][0])
                gy[sl] += dw * o(o(f[0][0], f[1][1]), f[2][0])
                gz[sl] += dw * o(o(f[0][0], f[1][0]), f[2][1])
                lap[sl] += dw * (
                    o(o(f[0][2], f[1][0]), f[2][0]) + o(o(f[0][0], f[1][2]), f[2][0]) + o(o(f[0][0], f[1][0]), f[2][2])
                )
    return psi, gx, gy, gz, lap


def _occupied(orbital_set, spin=False):
    """(coefficient columns of the occupied orbitals, their weights) — OrbitalSet.occupied."""
    columns, weights = orbital_set.occupied(spin)
    if not len(weights):
        raise ValueError(tr('В файле нет занятых орбиталей: плотность не построить.'))
    return [columns[:, n] for n in range(columns.shape[1])], list(weights)


def laplacian_cube(orbital_set, step=0.15, margin=MARGIN, progress=None):
    """−∇²ρ on the grid of orbitals.grid_for (positive where the density is concentrated)."""
    origin, steps, shape = grid_for(orbital_set, step, margin)
    used, weights = _occupied(orbital_set)
    field_ = np.zeros(shape)
    for n, (vector, w) in enumerate(zip(used, weights)):
        psi, gx, gy, gz, lap = on_grid_derivatives(orbital_set.shells, orbital_set.centres, vector, origin, steps, shape)
        field_ -= w * 2 * (psi * lap + gx * gx + gy * gy + gz * gz)
        if progress is not None and progress(n + 1, len(used)) is False:
            raise InterruptedError('cancelled')
    return _cube(orbital_set, field_, origin, steps, '−∇²ρ (Laplacian of the electron density, negated)')


def density_on(orbital_set, origin, step, shape, spin=False, progress=None, done=0, total=None):
    from modules.spectrum.analysis.gto import on_grid

    used, weights = _occupied(orbital_set, spin)
    total = total or len(used)
    field_ = np.zeros(shape)
    for n, (vector, w) in enumerate(zip(used, weights)):
        psi = on_grid(orbital_set.shells, orbital_set.centres, vector, origin, step, shape)
        field_ += w * psi * psi
        if progress is not None and progress(done + n + 1, total) is False:
            raise InterruptedError('cancelled')
    return field_


def match_fragments(molecule, fragments, tolerance=MATCH):
    """For every fragment the indices of the atoms of the molecule its atoms sit on (§2); ValueError otherwise."""
    atoms = molecule.atoms
    positions = np.array([a.position for a in atoms])
    used = set()
    out = []
    for f, fragment in enumerate(fragments):
        indices = []
        for atom in fragment.atoms:
            d = np.linalg.norm(positions - np.asarray(atom.position), axis=1)
            k = int(np.argmin(d))
            if d[k] > tolerance or atoms[k].symbol != atom.symbol:
                raise ValueError(tr(f'Атом {atom.symbol} фрагмента {f + 1} не стоит на атоме молекулы (допуск {tolerance} Å): '
                                    'фрагменты надо считать в той же геометрии.'))
            if k in used:
                raise ValueError(tr(f'Атом {atoms[k].symbol}{k + 1} молекулы входит в два фрагмента.'))
            used.add(k)
            indices.append(k)
        out.append(indices)
    if len(used) != len(atoms):
        missing = ', '.join(f'{atoms[k].symbol}{k + 1}' for k in range(len(atoms)) if k not in used)
        raise ValueError(tr(f'Эти атомы молекулы не вошли ни в один фрагмент: {missing}.'))
    return out


def difference_cube(molecule_set, fragment_sets, step=0.15, margin=MARGIN, progress=None):
    """(Cube of Δρ = ρ(molecule) − Σ ρ(fragment) on the grid of the molecule, ∫Δρ dV in electrons)."""
    if not fragment_sets:
        raise ValueError(tr('Добавьте хотя бы один фрагмент.'))
    match_fragments(molecule_set.molecule, [f.molecule for f in fragment_sets])
    origin, steps, shape = grid_for(molecule_set, step, margin)
    counts = [len(_occupied(s)[0]) for s in (molecule_set, *fragment_sets)]
    total = sum(counts)
    field_ = density_on(molecule_set, origin, steps, shape, progress=progress, total=total)
    done = counts[0]
    for s, n in zip(fragment_sets, counts[1:]):
        field_ -= density_on(s, origin, steps, shape, progress=progress, done=done, total=total)
        done += n
    integral = float(field_.sum() * np.prod(steps))
    return _cube(molecule_set, field_, origin, steps, 'Δρ = ρ(molecule) − Σ ρ(fragments)'), integral


def fukui_cubes(n_set, anion_set, cation_set, step=0.15, margin=MARGIN, progress=None):
    """The Fukui functions and the dual descriptor as fields (Parr — Yang 1984 by finite differences, the
    frozen geometry; Morell — Grand — Toro-Labbé 2005): ρ of the three wavefunctions on the grid of N.
    ∫f⁺ = ∫f⁻ = ∫f⁰ = 1 and ∫Δf = 0 up to the step of the grid."""
    for other, name in ((anion_set, 'N + 1'), (cation_set, 'N − 1')):
        match_fragments(n_set.molecule, [other.molecule])  # the same atoms in the same places
    electrons = [float(np.sum(_occupied(s)[1])) for s in (n_set, anion_set, cation_set)]
    if not (abs(electrons[1] - electrons[0] - 1) < 0.01 and abs(electrons[0] - electrons[2] - 1) < 0.01):
        raise ValueError(tr(f'Функции Фукуи: электронов {electrons[0]:.0f}, {electrons[1]:.0f}, {electrons[2]:.0f} — '
                            'нужны N, N + 1 и N − 1.'))
    origin, steps, shape = grid_for(n_set, step, margin)
    counts = [len(_occupied(s)[0]) for s in (n_set, anion_set, cation_set)]
    total, done, fields = sum(counts), 0, []
    for s, n in zip((n_set, anion_set, cation_set), counts):
        fields.append(density_on(s, origin, steps, shape, progress=progress, done=done, total=total))
        done += n
    rho_n, rho_anion, rho_cation = fields
    plus, minus = rho_anion - rho_n, rho_n - rho_cation
    values = {'plus': plus, 'minus': minus, 'zero': (plus + minus) / 2, 'dual': plus - minus}
    titles = {'plus': 'f+ = rho(N+1) - rho(N)', 'minus': 'f- = rho(N) - rho(N-1)', 'zero': 'f0 = (f+ + f-)/2',
              'dual': 'dual descriptor = f+ - f-'}
    volume = float(np.prod(steps))
    cubes = {key: _cube(n_set, field_, origin, steps, titles[key]) for key, field_ in values.items()}
    integrals = {key: float(field_.sum() * volume) for key, field_ in values.items()}
    return cubes, integrals


# -- QTAIM -------------------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class CriticalPoint:
    kind: str
    position: np.ndarray
    rho: float
    laplacian: float
    eigenvalues: np.ndarray
    ellipticity: float | None
    kinetic: float
    potential: float
    energy: float
    atoms: tuple = ()


@dataclass(frozen=True)
class Topology:
    points: tuple
    paths: tuple
    counts: dict
    poincare_hopf: int
    notes: tuple = field(default=())
    nuclei: tuple = field(default=())  # the maxima (3, −3) as CriticalPoint 'nucleus', atoms (i,)


KINDS = {0: 'nucleus', 1: 'bond', 2: 'ring', 3: 'cage'}  # by the number of positive eigenvalues


def rings(count, bonds):
    """The smallest cycle through every bond (atom index lists, up to RING_MAX atoms), without repeats."""
    neighbours = {k: set() for k in range(count)}
    for i, j in bonds:
        neighbours[i].add(j)
        neighbours[j].add(i)
    found = {}
    for i, j in bonds:
        # the shortest path from j back to i that does not use the bond i–j
        previous = {j: None}
        frontier = [j]
        while frontier and i not in previous:
            nxt = []
            for a in frontier:
                for b in neighbours[a]:
                    if (a, b) in ((j, i), (i, j)) or b in previous:
                        continue
                    previous[b] = a
                    nxt.append(b)
            frontier = nxt
            if len(previous) > 4 * count:
                break
        if i not in previous:
            continue
        cycle = [i]
        while cycle[-1] != j:
            cycle.append(previous[cycle[-1]])
        if 3 <= len(cycle) <= RING_MAX:
            found.setdefault(frozenset(cycle), cycle)
    return list(found.values())


def _newton(orbital_set, starts, matrix):
    x = np.array(starts, dtype=float)
    active = np.ones(len(x), bool)
    for _ in range(NEWTON_STEPS):
        if not active.any():
            break
        d = density_at(orbital_set, x[active], 2, matrix=matrix)
        g, h = d['grad'], d['hess']
        done = np.linalg.norm(g, axis=1) < GRAD_TOL
        try:
            dx = -np.linalg.solve(h, g[..., None])[..., 0]
        except np.linalg.LinAlgError:
            dx = -g
        length = np.linalg.norm(dx, axis=1, keepdims=True)
        dx = np.where(length > MAX_STEP, dx * MAX_STEP / np.maximum(length, 1e-30), dx)
        idx = np.flatnonzero(active)
        x[idx[~done]] += dx[~done]
        active[idx[done]] = False
    final = density_at(orbital_set, x, 2, matrix=matrix)
    converged = np.linalg.norm(final['grad'], axis=1) < 1e-6
    return x, final, converged


def _paths(orbital_set, starts, nuclei, matrix):
    """Gradient lines up the density from every start (all at once) until each reaches a nucleus (Heun steps of
    PATH_STEP bohr, shorter near a nucleus): [(points (n, 3) bohr, atom index or None)]."""
    x = np.array(starts, dtype=float)
    lines = [[p.copy()] for p in x]
    ends = [None] * len(x)
    active = np.ones(len(x), bool)
    previous = np.zeros_like(x)  # the last direction of every line

    def gradient(points):
        return density_at(orbital_set, points, 1, matrix=matrix)['grad']

    def direction(g):
        return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-14)

    for _ in range(PATH_STEPS):
        idx = np.flatnonzero(active)
        if not len(idx):
            break
        d = np.linalg.norm(x[idx][:, None, :] - nuclei[None, :, :], axis=2)
        nearest = np.argmin(d, axis=1)
        close = d[np.arange(len(idx)), nearest]
        g1 = gradient(x[idx])
        # at a nucleus, or at the maximum a Gaussian basis puts a little off a light nucleus (H): the line ends —
        # the gradient vanishes or turns back (the step went past the maximum)
        turned = np.einsum('ij,ij->i', direction(g1), previous[idx]) < -0.3
        top = (np.linalg.norm(g1, axis=1) < PATH_GTOL) | turned
        arrived = (close < ARRIVE) | (top & (close < NEAR_NUCLEUS))
        for k, atom in zip(idx[arrived], nearest[arrived]):
            lines[k].append(nuclei[atom].copy())
            ends[k] = int(atom)
            active[k] = False
        active[idx[top & ~arrived]] = False  # a maximum away from every nucleus: no atom
        keep = ~arrived & ~top
        moving = idx[keep]
        if not len(moving):
            break
        step = np.minimum(PATH_STEP, np.maximum(0.5 * close[keep], 0.005))[:, None]
        d1 = direction(g1[keep])
        d2 = direction(gradient(x[moving] + step * d1))
        both = direction(d1 + d2)
        x[moving] = x[moving] + step * both
        previous[moving] = both
        for k in moving:
            lines[k].append(x[k].copy())
    return [(np.array(line), end) for line, end in zip(lines, ends)]


def critical_points(orbital_set, progress=None):
    from modules.compass.chemistry.builder import connections

    molecule = orbital_set.molecule
    nuclei = np.asarray(orbital_set.centres, dtype=float)
    if len(molecule.atoms) < 2:
        raise ValueError(tr('Для критических точек нужна молекула хотя бы из двух атомов.'))
    matrix = density_matrix(orbital_set)
    bonds = [(i, j) for i, j, _ in connections(molecule)]
    cycles = rings(len(molecule.atoms), bonds)
    starts = [(nuclei[i] + nuclei[j]) / 2 for i, j in bonds] + [nuclei[c].mean(axis=0) for c in cycles]
    notes = []
    points, paths = [], []
    if starts:
        x, final, converged = _newton(orbital_set, starts, matrix)
        kept = []
        for k in range(len(x)):
            if not converged[k] or np.min(np.linalg.norm(nuclei - x[k], axis=1)) < 0.2:
                continue
            if any(np.linalg.norm(x[k] - x[j]) < MERGE for j in kept):
                continue
            kept.append(k)
        if progress is not None:
            progress(1, 2)
        found = []
        for k in kept:
            values, vectors = np.linalg.eigh(final['hess'][k])
            found.append((k, values, vectors, KINDS[int(np.sum(values > 0))]))
        bond_points = [(k, vectors) for k, values, vectors, kind in found if kind == 'bond']
        starts = [x[k] + sign * 0.01 * vectors[:, 2] for k, vectors in bond_points for sign in (1, -1)]
        traced = _paths(orbital_set, starts, nuclei, matrix) if starts else []
        ends = {}
        for n, (k, _) in enumerate(bond_points):
            pair = traced[2 * n : 2 * n + 2]
            paths.append(np.concatenate((pair[0][0][::-1], pair[1][0][1:])) * BOHR)  # nucleus → BCP → nucleus
            ends[k] = tuple(sorted(a for _, a in pair if a is not None))
        for k, values, vectors, kind in found:
            rho, lap, g = float(final['rho'][k]), float(final['laplacian'][k]), float(final['kinetic'][k])
            v = lap / 4 - 2 * g
            ellipticity = float(values[0] / values[1] - 1) if kind == 'bond' and values[1] < 0 else None
            points.append(CriticalPoint(kind, x[k] * BOHR, rho, lap, values, ellipticity, g, v, g + v, ends.get(k, ())))
    counts = {'n': len(molecule.atoms), 'b': sum(p.kind == 'bond' for p in points),
              'r': sum(p.kind == 'ring' for p in points), 'c': sum(p.kind == 'cage' for p in points)}
    ph = counts['n'] - counts['b'] + counts['r'] - counts['c']
    if ph != 1:
        notes.append(tr(f'n − b + r − c = {ph}, а не 1: какие-то критические точки не найдены (поиск идёт от связей, '
                        f'которые рисует Компас, и от циклов до {RING_MAX} атомов).'))
    if any(abs(float(c) - z) > 1e-6 for c, z in zip(orbital_set.charges, (_z(a.symbol) for a in molecule.atoms))):
        notes.append(tr('В расчёте есть эффективный потенциал остова: плотность без остовных электронов, у тяжёлых '
                        'атомов максимума на ядре может не быть.'))
    order = {'bond': 0, 'ring': 1, 'cage': 2}
    points.sort(key=lambda p: (order.get(p.kind, 3), p.atoms))
    return Topology(tuple(points), tuple(paths), counts, ph, tuple(notes))


def _z(symbol):
    from azimuth.core import SYMBOLS

    return SYMBOLS.index(symbol) + 1


# -- slices -------------------------------------------------------------------------------------------------------------
def plane(orbital_set, atoms=None):
    """(origin Å, u, v): the plane through three atoms (indices) or the best plane of all atoms."""
    positions = np.array([a.position for a in orbital_set.molecule.atoms], float)
    if atoms is not None:
        if len(set(atoms)) != 3 or not all(0 <= k < len(positions) for k in atoms):
            raise ValueError(tr('Плоскость задают три разных атома.'))
        a, b, c = positions[list(atoms)]
        u = b - a
        n = np.cross(u, c - a)
        if np.linalg.norm(n) < 1e-6 * max(1.0, np.linalg.norm(u)) ** 2:
            raise ValueError(tr('Эти три атома на одной прямой — плоскость не определена.'))
        origin = (a + b + c) / 3
    else:
        origin = positions.mean(axis=0)
        if len(positions) < 3:
            u = positions[-1] - positions[0] if len(positions) > 1 else np.array([1.0, 0.0, 0.0])
            helper = np.array([0.0, 0.0, 1.0]) if abs(u[2]) < 0.9 * np.linalg.norm(u) else np.array([1.0, 0.0, 0.0])
            n = np.cross(u, helper)
        else:
            _, _, vt = np.linalg.svd(positions - origin)
            u, n = vt[0], vt[2]
    n = n / np.linalg.norm(n)
    u = u - n * (u @ n)
    u = u / np.linalg.norm(u)
    v = np.cross(n, u)
    return origin, u, v


def slice_values(orbital_set, origin, u, v, half, n=161, field_='rho', fragments=()):
    """(xs, ys, values (n, n) [row = y]) of ρ, ∇²ρ or Δρ on the square ±half Å of the plane (origin, u, v)."""
    if not (0.5 <= half <= 30.0) or not (21 <= n <= 401):
        raise ValueError(tr('Размер среза — от 0,5 до 30 Å, точек — от 21 до 401.'))
    xs = np.linspace(-half, half, n)
    ys = np.linspace(-half, half, n)
    gx, gy = np.meshgrid(xs, ys)
    points = (np.asarray(origin) + gx.ravel()[:, None] * np.asarray(u) + gy.ravel()[:, None] * np.asarray(v)) / BOHR
    if field_ == 'rho':
        values = density_at(orbital_set, points, 0)['rho']
    elif field_ == 'laplacian':
        values = density_at(orbital_set, points, 2)['laplacian']
    elif field_ == 'difference':
        if not fragments:
            raise ValueError(tr('Для Δρ добавьте фрагменты.'))
        match_fragments(orbital_set.molecule, [f.molecule for f in fragments])
        values = density_at(orbital_set, points, 0)['rho']
        for f in fragments:
            values = values - density_at(f, points, 0)['rho']
    else:
        raise ValueError(field_)
    return xs, ys, values.reshape(n, n)


# the contour levels of Bader's maps: 0.001, 0.002, 0.004, 0.008 × 10^k (atomic units)
BADER = tuple(m * 10.0**k for k in range(-3, 2) for m in (1, 2, 4, 8))
DIFFERENCE = (0.001, 0.002, 0.005, 0.01, 0.02, 0.05, 0.1, 0.2)

# marching squares: for a corner mask (bit 0 = (0, 0), 1 = (1, 0), 2 = (1, 1), 3 = (0, 1)) the pairs of cell edges
# (0 bottom, 1 right, 2 top, 3 left) a contour segment joins
_EDGES = {
    1: ((3, 0),), 2: ((0, 1),), 3: ((3, 1),), 4: ((1, 2),), 6: ((0, 2),), 7: ((3, 2),), 8: ((2, 3),),
    9: ((0, 2),), 11: ((1, 2),), 12: ((1, 3),), 13: ((0, 1),), 14: ((3, 0),),
}


def contours(values, xs, ys, level):
    """Segments (k, 2, 2) in (x, y) of the contour values = level (values[row = y, column = x])."""
    f = np.asarray(values, float) - level
    a, b, c, d = f[:-1, :-1], f[:-1, 1:], f[1:, 1:], f[1:, :-1]  # (x0,y0) (x1,y0) (x1,y1) (x0,y1)
    mask = (a > 0).astype(int) | ((b > 0) << 1) | ((c > 0) << 2) | ((d > 0) << 3)
    out = []
    rows, cols = np.nonzero((mask != 0) & (mask != 15))
    if not len(rows):
        return np.zeros((0, 2, 2))
    x0, x1, y0, y1 = xs[cols], xs[cols + 1], ys[rows], ys[rows + 1]
    fa, fb, fc, fd = a[rows, cols], b[rows, cols], c[rows, cols], d[rows, cols]

    def t(p, q):
        return p / np.where(np.abs(p - q) < 1e-300, 1e-300, p - q)

    edges = (
        np.stack((x0 + t(fa, fb) * (x1 - x0), y0), 1),  # bottom: a → b
        np.stack((x1, y0 + t(fb, fc) * (y1 - y0)), 1),  # right: b → c
        np.stack((x0 + t(fd, fc) * (x1 - x0), y1), 1),  # top: d → c
        np.stack((x0, y0 + t(fa, fd) * (y1 - y0)), 1),  # left: a → d
    )
    centre = (fa + fb + fc + fd) / 4
    for k, case in enumerate(mask[rows, cols]):
        if case == 5:  # a and c above: saddle
            pairs = ((3, 2), (0, 1)) if centre[k] > 0 else ((3, 0), (1, 2))
        elif case == 10:
            pairs = ((0, 3), (1, 2)) if centre[k] > 0 else ((0, 1), (2, 3))
        else:
            pairs = _EDGES[case]
        for e1, e2 in pairs:
            out.append((edges[e1][k], edges[e2][k]))
    return np.array(out)


def topology_from(cps, orbital_set=None, notes=()):
    """A Topology of the critical points of Multiwfn (dicts of modules/spectrum/wavefunction/multiwfn.parse_cps)."""
    maxima = [cp for cp in cps if cp['kind'] == 'nucleus']
    rest = [cp for cp in cps if cp['kind'] in ('bond', 'ring', 'cage')]
    traced = {}  # index in rest -> the bond path, Å
    bonds = [k for k, cp in enumerate(rest) if cp['kind'] == 'bond' and 'bohr' in cp and 'vectors' in cp]
    if orbital_set is not None and bonds:
        nuclei = np.asarray(orbital_set.centres, dtype=float)
        starts = [rest[k]['bohr'] + sign * 0.01 * rest[k]['vectors'][:, 2] for k in bonds for sign in (1, -1)]
        lines = _paths(orbital_set, starts, nuclei, density_matrix(orbital_set))
        ends = {}
        for n, k in enumerate(bonds):
            pair = lines[2 * n: 2 * n + 2]
            traced[k] = np.concatenate((pair[0][0][::-1], pair[1][0][1:])) * BOHR
            ends[k] = tuple(sorted(a for _, a in pair if a is not None))
    else:
        ends = {}

    def point_of(cp, atoms):
        g, v = cp.get('kinetic', float('nan')), cp.get('potential', float('nan'))
        return CriticalPoint(cp['kind'], np.asarray(cp['position'], float), cp['rho'], cp['laplacian'],
                             np.asarray(cp['eigenvalues'], float), cp.get('ellipticity'), g, v, cp.get('energy', g + v),
                             tuple(sorted(atoms)))

    found = []
    for k, cp in enumerate(rest):
        atoms = cp.get('atoms', ())
        if cp['kind'] == 'bond' and len(atoms) != 2 and len(ends.get(k, ())) == 2:
            atoms = ends[k]  # the nuclei at the two ends of the bond path
        found.append((point_of(cp, atoms), traced.get(k)))
    nuclei = tuple(sorted((point_of(cp, cp.get('atoms', ())) for cp in maxima), key=lambda p: p.atoms or (10 ** 6,)))
    order = {'bond': 0, 'ring': 1, 'cage': 2}
    found.sort(key=lambda item: (order.get(item[0].kind, 3), item[0].atoms))
    points = tuple(point for point, _ in found)
    counts = {'n': len(maxima), 'b': sum(p.kind == 'bond' for p in points),
              'r': sum(p.kind == 'ring' for p in points), 'c': sum(p.kind == 'cage' for p in points)}
    ph = counts['n'] - counts['b'] + counts['r'] - counts['c']
    notes = list(notes)
    atoms = len(orbital_set.molecule.atoms) if orbital_set is not None else None
    if atoms is not None and len(maxima) != atoms:
        notes.append(tr(f'Максимумов плотности (3, −3) {len(maxima)}, а атомов {atoms}.'))
    if ph != 1:
        notes.append(tr(f'n − b + r − c = {ph}, а не 1: какие-то критические точки не найдены.'))
    return Topology(points, tuple(path for _, path in found if path is not None), counts, ph, tuple(notes), nuclei)

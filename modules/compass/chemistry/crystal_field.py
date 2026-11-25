"""The electron density and the ELF of a crystal on its model: from the orbitals of CP2K (its Molden file,
the Γ point of the cell computed), periodic.

§1 THEORY ρ(r) = Σ_i n_i ψ_i(r)², ψ_i(r) = Σ_μ c_μi χ_μ(r), the functions of the periodic crystal χ_μ(r) = Σ_n φ_μ(r −
    R_μ − n) (n — the lattice vectors of the cell computed). The electron localization function (Becke, Edgecombe 1990;
    Savin et al. 1992) ELF = 1 / (1 + (D/D₀)²), D = τ − |∇ρ|²/(8ρ), τ = ½ Σ n_i |∇ψ_i|² (the kinetic energy density, the
    von Weizsäcker term subtracted), D₀ = (3/10)(3π²)^(2/3) ρ^(5/3) — of the uniform electron gas (atomic units): ELF ≈
    1 where electrons are paired (bonds, lone pairs, shells), 0.5 — as in the gas. CP2K computes with pseudopotentials
    (GTH): ρ and ELF are of the valence electrons; the cores are empty (ELF near a nucleus means nothing). ∂/∂x of x^a
    y^b z^c e^(−αr²) = (a x^(a−1) − 2α x^(a+1)) y^b z^c e^(−αr²).
§2 ALGORITHM The grid — the cell of the file (the cell of the model): nₖ = ⌈|aₖ| / step⌉ points along each edge (at most
    MAX_POINTS in all), the points f = (i/n₁, j/n₂, k/n₃); a point of the model r = f·A_file goes to the cell computed
    by its fractions: f_computed = f · B⁻¹ / repeat (B — the rows of the primitive cell in the fractions of the file
    when the primitive cell was computed, else 1), r_computed = f_computed · A_computed (crystal_steps.guess_computed
    tells the repeat). By chunks of points: the values and gradients of every function of every atom image within reach
    (e^(−α_min r²) < 1e-10) summed into χ_μ, then ψ = χ C of the occupied orbitals, ρ, ∇ρ, τ. The model: the grid of the
    cell repeated over the cells its atoms take (the fractions of the atoms, floor and ceil), one more layer at the end
    (periodic), as a cube (readers.cube.Cube, axes — the edges of the file over nₖ).
§4 SPECIFICATION
    cell_field(wave, file_cell, mapping, what='density' | 'elf', step=0.12, progress=None) -> (nx, ny, nz) values (a.u.;
    ELF 0–1); mapping — 3 × 3: f_file → f_computed. compute(text, cell, file_cell, mapping, what, step, progress) — from
    the text of the Molden file, the convention of the contractions checked by ∫ρ = the electrons (no overlap needed).
    model_cube(values, file_cell, molecule, title) -> Cube over the
    atoms of the molecule. integral(values, file_cell) — the electrons in the cell (ρ).
§7 TESTS tests/compass/test_crystal_field.py — CsCl (CP2K CELL_OPT): ∫ρ over the cell = 16 valence electrons, ELF in
    0–1, high at the shells of Cl⁻; the cube over a block 2 × 2 × 2.
"""

from math import ceil, floor, log, pi, sqrt

import numpy as np

from modules.compass.chemistry.geometry_tools import BOHR

MAX_POINTS = 120_000
CHUNK = 2048
CUT = 1e-10


def _grid(file_cell, step):
    lengths = np.linalg.norm(np.asarray(file_cell, dtype=float), axis=1)
    while True:
        n = [max(4, int(ceil(x / step))) for x in lengths]
        if n[0] * n[1] * n[2] <= MAX_POINTS:
            return n
        step *= 1.1


def _atom_images(wave, low, high):
    """[(atom, shift bohr)] of the atoms whose functions reach the box low–high (bohr) of the cell computed."""
    reach = {}
    for shell in wave.shells:
        r = sqrt(-log(CUT) / float(shell.exponents.min()))
        reach[shell.centre] = max(reach.get(shell.centre, 0.0), r)
    cell = wave.cell
    volume = abs(np.linalg.det(cell))
    heights = [volume / np.linalg.norm(np.cross(cell[(k + 1) % 3], cell[(k + 2) % 3])) for k in range(3)]
    far = max(reach.values()) + float(np.linalg.norm(high - low))
    n = [int(ceil(far / h)) + 1 for h in heights]
    shifts = np.array([(i, j, k) for i in range(-n[0], n[0] + 1) for j in range(-n[1], n[1] + 1)
                       for k in range(-n[2], n[2] + 1)], dtype=float) @ cell
    found = []
    for atom, centre in enumerate(wave.centres):
        if atom not in reach:
            continue
        places = centre + shifts
        nearest = np.clip(places, low, high)
        near = np.linalg.norm(places - nearest, axis=1) <= reach[atom]
        found += [(atom, t) for t in shifts[near]]
    return found


def _basis(wave, points, gradient):
    """χ (P × nbasis) and, with gradient, ∂χ/∂x, ∂χ/∂y, ∂χ/∂z at points (bohr) of the cell computed."""
    offsets = np.cumsum([0] + [s.size for s in wave.shells])
    nbasis = offsets[-1]
    values = np.zeros((len(points), nbasis))
    grads = np.zeros((3, len(points), nbasis)) if gradient else None
    by_atom = {}
    for k, shell in enumerate(wave.shells):
        by_atom.setdefault(shell.centre, []).append(k)
    low, high = points.min(axis=0), points.max(axis=0)
    for atom, shift in _atom_images(wave, low, high):
        rel = points - (wave.centres[atom] + shift)
        r2 = np.einsum('ij,ij->i', rel, rel)
        powers = [[np.ones(len(points))] for _ in range(3)]
        for axis in range(3):
            for _ in range(6):
                powers[axis].append(powers[axis][-1] * rel[:, axis])
        for k in by_atom[atom]:
            shell = wave.shells[k]
            a_min = float(shell.exponents.min())
            if r2.min() * a_min > -log(CUT):
                continue
            e = np.exp(-np.multiply.outer(r2, shell.exponents))
            radial = e @ shell.radial()
            mono = np.empty((len(points), len(shell.monomials)))
            for m, (a, b, c) in enumerate(shell.monomials):
                mono[:, m] = powers[0][a] * powers[1][b] * powers[2][c]
            values[:, offsets[k]:offsets[k + 1]] += (mono * radial[:, None]) @ shell.angular.T
            if gradient:
                slope = e @ (shell.radial() * shell.exponents)  # Σ d α e^(−αr²)
                for axis in range(3):
                    d = np.empty_like(mono)
                    for m, powers_m in enumerate(shell.monomials):
                        p = powers_m[axis]
                        others = [powers[ax][powers_m[ax]] for ax in range(3) if ax != axis]
                        rest = others[0] * others[1]
                        lower = p * powers[axis][p - 1] if p else 0.0
                        d[:, m] = rest * (lower * radial - 2.0 * powers[axis][p + 1] * slope)
                    grads[axis][:, offsets[k]:offsets[k + 1]] += d @ shell.angular.T
    return values, grads


def cell_field(wave, file_cell, mapping, what='density', step=0.12, progress=None):
    file_cell = np.asarray(file_cell, dtype=float)
    n = _grid(file_cell, step)
    f = np.stack(np.meshgrid(*[np.arange(k) / k for k in n], indexing='ij'), axis=-1).reshape(-1, 3)
    points = (f @ np.asarray(mapping, dtype=float)) @ wave.cell  # bohr, the cell computed
    occupied = wave.occupations > 1e-8
    c, weights = wave.c[:, occupied], wave.occupations[occupied]
    out = np.zeros(len(points))
    chunks = range(0, len(points), CHUNK)
    for number, start in enumerate(chunks):
        chunk = points[start:start + CHUNK]
        values, grads = _basis(wave, chunk, what == 'elf')
        psi = values @ c
        rho = (psi * psi) @ weights
        if what == 'elf':
            dpsi = [g @ c for g in grads]
            grad_rho = np.stack([2.0 * (psi * d) @ weights for d in dpsi], axis=1)
            tau = 0.5 * sum((d * d) @ weights for d in dpsi)
            safe = np.maximum(rho, 1e-12)
            excess = np.maximum(tau - np.einsum('ij,ij->i', grad_rho, grad_rho) / (8.0 * safe), 0.0)
            uniform = 0.3 * (3.0 * pi * pi) ** (2.0 / 3.0) * safe ** (5.0 / 3.0)
            elf = 1.0 / (1.0 + (excess / uniform) ** 2)
            out[start:start + CHUNK] = np.where(rho > 1e-6, elf, 0.0)
        else:
            out[start:start + CHUNK] = rho
        if progress is not None and progress(number + 1, len(chunks)) is False:
            raise InterruptedError('cancelled')
    return out.reshape(n)


def compute(text, cell, file_cell, mapping, what='density', step=0.12, progress=None):
    """The field of a Molden file of CP2K on the cell of the file. The convention of its contractions (CP2K: not
    normalized) is checked by the electrons: ∫ρ over the cell of the file = Σ n_i · |det mapping| (the share of the
    cell computed); the other convention is tried when it fails, ValueError when neither holds."""
    from modules.compass.chemistry import crystal_pdos

    mapping = np.asarray(mapping, dtype=float)
    for renormalized in (True, False):
        wave = crystal_pdos.wavefunction(text, cell, overlap=False, renormalized=renormalized)
        rho = cell_field(wave, file_cell, mapping, 'density', step, progress)
        volume = abs(np.linalg.det(mapping @ wave.cell))  # bohr³ of the cell of the file in the cell computed
        expected = float(wave.occupations.sum()) * abs(np.linalg.det(mapping))
        if abs(rho.mean() * volume - expected) <= 0.01 * max(expected, 1.0):
            return rho if what == 'density' else cell_field(wave, file_cell, mapping, what, step, progress)
    raise ValueError('the density of the Molden file does not hold its electrons under either convention')


def integral(values, file_cell):
    volume = abs(np.linalg.det(np.asarray(file_cell, dtype=float))) / BOHR ** 3
    return float(values.mean() * volume)


def mapping_of(original, computed_cell):
    """The 3 × 3 map of the fractions of the file to those of the cell computed (crystal_steps.guess_computed), None
    when the cell computed is no whole cell of the file."""
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_steps

    guess = crystal_steps.guess_computed(original, computed_cell, tol=0.1)
    if guess is None:
        return None
    repeat, primitive = guess
    base = np.eye(3)
    if primitive:
        basis = cr.primitive_basis(original)
        if basis is None:
            return None
        base = np.linalg.inv(np.asarray(basis, dtype=float))
    return base @ np.diag([1.0 / r for r in repeat])


def model_cube(values, file_cell, molecule, title, units='a.u.'):
    """The field of one cell repeated over the cells the atoms of the model take (the model: the cell at the origin)."""
    from modules.spectrum.readers.cube import Cube

    file_cell = np.asarray(file_cell, dtype=float)
    inverse = np.linalg.inv(file_cell)
    fractions = np.array([a.position for a in molecule.atoms], dtype=float) @ inverse
    low = [int(floor(x + 1e-3)) for x in fractions.min(axis=0)]
    high = [max(low[k] + 1, int(ceil(x - 1e-3))) for k, x in enumerate(fractions.max(axis=0))]
    reps = [high[k] - low[k] for k in range(3)]
    tiled = np.tile(values, reps)
    tiled = np.concatenate([tiled, tiled[:1]], axis=0)
    tiled = np.concatenate([tiled, tiled[:, :1]], axis=1)
    tiled = np.concatenate([tiled, tiled[:, :, :1]], axis=2)
    n = values.shape
    axes = np.array([file_cell[k] / n[k] for k in range(3)])
    origin = np.array(low, dtype=float) @ file_cell
    return Cube(title, molecule, origin, axes, tiled[..., None], (1,), units)

"""Promolecular NCI grids for the tests: sign(λ₂)ρ and RDG of a sum of free-atom densities.

The atoms are spherical Slater densities (J. C. Slater, Phys. Rev. 36, 57 (1930): the screening rules and the effective
quantum numbers 1, 2, 3, 3.7), so the density, its gradient and its Hessian are analytic. Multiwfn's promolecular NCI
uses fitted free-atom densities instead; the shape of the RDG basins between molecules — what the tests of the domains
need — is the same, the values of sign(λ₂)ρ differ by some 10–30 %. RDG is set to 100 where ρ > 0.05 a.u., as Multiwfn
does, so covalent regions have none. The cubes are those of modules/spectrum/readers/cube.py (Å).
"""

from math import gamma, pi

import numpy as np

from azimuth.core import Atom, Molecule
from modules.compass.chemistry.geometry_tools import BOHR
from modules.spectrum.readers.cube import Cube

Z = {'H': 1, 'C': 6, 'N': 7, 'O': 8, 'F': 9, 'Si': 14, 'P': 15, 'S': 16, 'Cl': 17, 'Br': 35}
NSTAR = {1: 1.0, 2: 2.0, 3: 3.0, 4: 3.7}
GROUPS = ((1, 's', 2), (2, 'sp', 8), (3, 'sp', 8), (3, 'd', 10), (4, 'sp', 8))


def shells(symbol):
    """[(electrons, n*, ζ)] of the atom by Slater's rules."""
    left = Z[symbol]
    filled = []
    for n, kind, size in GROUPS:
        if left <= 0:
            break
        filled.append([n, kind, min(size, left)])
        left -= size
    out = []
    for g, (n, kind, count) in enumerate(filled):
        screen = (count - 1) * (0.30 if n == 1 else 0.35)
        for m, other, c in filled[:g]:
            if kind == 'd':
                screen += c
            elif m == n - 1 and kind != 'd':
                screen += 0.85 * c
            else:
                screen += c
        out.append((count, NSTAR[n], (Z[symbol] - screen) / NSTAR[n]))
    return out


def _radial(symbol):
    """[(C, k, a)]: ρ(r) = Σ C r^k exp(−a r), bohr."""
    out = []
    for count, n, zeta in shells(symbol):
        a = 2 * zeta
        out.append((count * a ** (2 * n + 1) / gamma(2 * n + 1) / (4 * pi), 2 * n - 2, a))
    return out


def cubes(rows, step=0.15, margin=2.5, fragments=None):
    """(sign cube, RDG cube) of the promolecule of rows [(symbol, x, y, z) Å]; with fragments (lists of atoms, 0-based)
    the second cube is δg_inter of IGM instead (Lefebvre 2017: |Σ_F |∇ρ_F|| − |∇ρ|, the absolute values per component) —
    the promolecular cousin of IGMH, for the domains of 0.199.0."""
    xyz = np.array([r[1:] for r in rows], float)
    low, high = xyz.min(axis=0) - margin, xyz.max(axis=0) + margin
    dims = np.ceil((high - low) / step).astype(int) + 1
    axes = [np.arange(d) * step + o for d, o in zip(dims, low)]
    grid = np.stack(np.meshgrid(*axes, indexing='ij'), axis=-1).reshape(-1, 3) / BOHR
    rho = np.zeros(len(grid))
    grad = np.zeros((len(grid), 3))
    hess = np.zeros((len(grid), 3, 3))
    owner = {k: f for f, atoms in enumerate(fragments or ()) for k in atoms}
    parts = np.zeros((len(fragments or ()), len(grid), 3))
    for index, ((symbol, *_), centre) in enumerate(zip(rows, xyz / BOHR)):
        d = grid - centre
        r = np.maximum(np.linalg.norm(d, axis=1), 1e-6)
        u = d / r[:, None]
        f = np.zeros_like(r)
        f1 = np.zeros_like(r)
        f2 = np.zeros_like(r)
        for c, k, a in _radial(symbol):
            g = c * r ** k * np.exp(-a * r)
            q = k / r - a
            f += g
            f1 += g * q
            f2 += g * (q * q - k / r ** 2)
        rho += f
        grad += f1[:, None] * u
        if index in owner:
            parts[owner[index]] += f1[:, None] * u
        outer = u[:, :, None] * u[:, None, :]
        hess += f2[:, None, None] * outer + (f1 / r)[:, None, None] * (np.eye(3) - outer)
    lam = np.linalg.eigvalsh(hess)[:, 1]
    sign = np.sign(lam) * rho
    rdg = np.linalg.norm(grad, axis=1) / (2 * (3 * pi ** 2) ** (1 / 3) * np.maximum(rho, 1e-30) ** (4 / 3))
    rdg = np.where(rho > 0.05, 100.0, np.minimum(rdg, 100.0))
    if fragments:
        rdg = np.linalg.norm(np.abs(parts).sum(axis=0), axis=1) - np.linalg.norm(grad, axis=1)
    molecule = Molecule('promolecule', tuple(Atom(s, x, y, z) for s, x, y, z in rows))
    shape = (*dims, 1)
    make = lambda values: Cube('promolecule', molecule, low.copy(), np.eye(3) * step, values.reshape(shape), (1,), 'Å')
    return make(sign), make(rdg)

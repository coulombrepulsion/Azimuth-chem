"""Electron density analysis (modules/spectrum/analysis/density.py).

Oracles, independent of the formulas under test:
  * ρ at points against orbitals.density_cube (gto.on_grid, another evaluation of the same basis);
  * the analytic gradient and Hessian of ρ against central differences of ρ itself (h = 1e-4 bohr: the error is
    O(h²) ≈ 1e-8 relative), ∇²ψ on the grid against the trace of the Hessian of ψ at the same points;
  * chemistry of water (GAMESS-US SCF, Molden file of the Molden program; cclib test data): the O–H bond
    critical point lies on the bond, closer to H (H is less electronegative), ρ_BCP 0.30–0.42 au and ∇²ρ < 0,
    H < 0 (shared interaction; Bader 1990, Popelier 2000 give ρ ≈ 0.36–0.39, ∇²ρ ≈ −1.8…−2.6 au for O–H);
  * the Poincaré–Hopf relation n − b + r − c = 1 (a theorem of topology) for divinylbenzene, whose benzene ring
    has one ring critical point at its centre;
  * Δρ of a molecule minus the same molecule is zero; ∫ρ dV on the grid ≈ the number of electrons;
  * marching squares of x² + y² at level 1 lie on the unit circle.
"""

from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import density
from modules.spectrum.readers.orbital_files import read_orbitals
from modules.spectrum.analysis.orbitals import density_cube, grid_for
from modules.compass.chemistry.geometry_tools import BOHR

DATA = Path(__file__).parents[1] / 'data' / 'orbitals'


def load(name):
    return read_orbitals((DATA / name).read_text(encoding='utf-8', errors='replace'))


@pytest.fixture(scope='module')
def water():
    return load('molden5.7_water_mp2.molden')


def test_density_at_points_equals_the_grid(water):
    cube = density_cube(water, step=0.3)
    nx, ny, nz = cube.values.shape[:3]
    picks = [(nx // 2, ny // 2, nz // 2), (nx // 3, ny // 2, nz // 2 + 1), (1, 2, 3)]
    points = np.array([np.asarray(cube.origin) + np.array(p) @ np.asarray(cube.axes) for p in picks]) / BOHR
    rho = density.density_at(water, points, 0)['rho']
    assert rho == pytest.approx([cube.values[p][0] for p in picks], rel=1e-9, abs=1e-14)


def test_gradient_and_hessian_against_differences(water):
    centre = np.array([a.position for a in water.molecule.atoms]).mean(axis=0) / BOHR
    points = centre + np.array([[0.3, -0.2, 0.25], [0.9, 0.4, -0.3], [-0.5, 0.1, 0.7]])
    d = density.density_at(water, points, 2)
    h = 1e-4
    for k in range(3):
        e = np.zeros(3)
        e[k] = h
        up, down = density.density_at(water, points + e, 1), density.density_at(water, points - e, 1)
        assert d['grad'][:, k] == pytest.approx((up['rho'] - down['rho']) / (2 * h), rel=1e-6, abs=1e-9)
        assert d['hess'][:, :, k] == pytest.approx((up['grad'] - down['grad']) / (2 * h), rel=1e-5, abs=1e-8)
    assert d['laplacian'] == pytest.approx(np.trace(d['hess'], axis1=1, axis2=2))
    assert np.all(d['kinetic'] >= 0)


def test_laplacian_of_an_orbital_on_the_grid(water):
    homo, _ = water.frontier()
    origin, step, shape = grid_for(water, 0.3)
    vector = water.coefficients[:, homo]
    psi, gx, gy, gz, lap = density.on_grid_derivatives(water.shells, water.centres, vector, origin, step, shape)
    picks = [(shape[0] // 2, shape[1] // 2 + 1, shape[2] // 2), (3, 5, 7)]
    points = np.array([origin + np.array(p) * step for p in picks])
    phi, grad, hess = density.basis_values(water.shells, water.centres, points, 2)
    for n, p in enumerate(picks):
        assert psi[p] == pytest.approx(phi[n] @ vector, rel=1e-9, abs=1e-14)
        assert (gx[p], gy[p], gz[p]) == pytest.approx(tuple(grad[n].T @ vector), rel=1e-8, abs=1e-12)
        assert lap[p] == pytest.approx(np.trace(hess[n], axis1=1, axis2=2) @ vector, rel=1e-8, abs=1e-12)


def test_the_number_of_electrons(water):
    cube = density_cube(water, step=0.1)
    steps = np.diag(np.asarray(cube.axes)) / BOHR
    total = cube.values[..., 0].sum() * np.prod(steps)
    electrons = sum(o.occupation for o in water.orbitals)
    assert total == pytest.approx(electrons, rel=0.03)  # a plain sum on a 0.1 Å grid (the cusps cost ~1 %)


def test_bond_critical_points_of_water(water):
    top = density.critical_points(water)
    bonds = [p for p in top.points if p.kind == 'bond']
    assert len(bonds) == 2 and top.counts['r'] == 0 and top.poincare_hopf == 1 and not top.notes
    symbols = [a.symbol for a in water.molecule.atoms]
    o = symbols.index('O')
    positions = np.array([a.position for a in water.molecule.atoms])
    for p in bonds:
        assert sorted(symbols[k] for k in p.atoms) == ['H', 'O']
        h = [k for k in p.atoms if symbols[k] == 'H'][0]
        assert np.linalg.norm(p.position - positions[h]) < np.linalg.norm(p.position - positions[o])
        # on the bond: the distances add up to the bond length within 0.01 Å
        total = np.linalg.norm(p.position - positions[h]) + np.linalg.norm(p.position - positions[o])
        assert total == pytest.approx(np.linalg.norm(positions[h] - positions[o]), abs=0.01)
        assert 0.30 < p.rho < 0.42 and p.laplacian < 0 and p.energy < 0 and p.ellipticity < 0.1
        assert p.eigenvalues[0] < 0 and p.eigenvalues[1] < 0 and p.eigenvalues[2] > 0
        assert p.potential == pytest.approx(p.laplacian / 4 - 2 * p.kinetic)
    for path in top.paths:  # nucleus → BCP → nucleus
        ends = {int(np.argmin(np.linalg.norm(positions - path[0], axis=1))),
                int(np.argmin(np.linalg.norm(positions - path[-1], axis=1)))}
        assert o in ends and len(ends) == 2


def test_divinylbenzene_ring_and_poincare_hopf():
    dvb = load('molden5.7_dvb_un_sp.molden')
    top = density.critical_points(dvb)
    assert top.counts == {'n': 20, 'b': 20, 'r': 1, 'c': 0} and top.poincare_hopf == 1
    (ring,) = [p for p in top.points if p.kind == 'ring']
    carbons = np.array([a.position for a in dvb.molecule.atoms if a.symbol == 'C'])
    ring_atoms = carbons[np.argsort(np.linalg.norm(carbons - ring.position, axis=1))[:6]]
    assert np.linalg.norm(ring.position - ring_atoms.mean(axis=0)) < 0.05
    assert ring.rho < min(p.rho for p in top.points if p.kind == 'bond')


def test_difference_density_and_fragments(water):
    cube, integral = density.difference_cube(water, [water], step=0.3)
    assert np.max(np.abs(cube.values)) < 1e-12 and abs(integral) < 1e-10
    with pytest.raises(ValueError):
        density.match_fragments(water.molecule, [])  # no atoms used
    from dataclasses import replace

    moved = replace(water.molecule, atoms=tuple(replace(a, x=a.x + 0.1) for a in water.molecule.atoms))
    with pytest.raises(ValueError):
        density.match_fragments(water.molecule, [moved])
    with pytest.raises(ValueError):
        density.match_fragments(water.molecule, [water.molecule, water.molecule])


def test_laplacian_cube_and_slice(water):
    cube = density.laplacian_cube(water, step=0.3)
    nx, ny, nz = cube.values.shape[:3]
    picks = [(nx // 2, ny // 2, nz // 2), (nx // 2 + 2, ny // 2 - 1, nz // 2), (4, 6, 8)]
    points = np.array([np.asarray(cube.origin) + np.array(p) @ np.asarray(cube.axes) for p in picks]) / BOHR
    at = density.density_at(water, points, 2)['laplacian']
    assert [cube.values[p][0] for p in picks] == pytest.approx(-at, rel=1e-7, abs=1e-12)  # the cube holds −∇²ρ
    o = [a.symbol for a in water.molecule.atoms].index('O')
    nucleus = np.asarray(water.molecule.atoms[o].position)[None] / BOHR
    assert density.density_at(water, nucleus, 2)['laplacian'][0] < 0  # a maximum: concentrated at the nucleus
    origin, u, v = density.plane(water, (0, 1, 2))
    assert abs(u @ v) < 1e-12 and np.linalg.norm(u) == pytest.approx(1) and np.linalg.norm(v) == pytest.approx(1)
    for atom in water.molecule.atoms:  # the three atoms lie in their plane
        n = np.cross(u, v)
        assert abs((np.asarray(atom.position) - origin) @ n) < 1e-9
    xs, ys, rho = density.slice_values(water, origin, u, v, 3.0, 41, 'rho')
    assert rho.shape == (41, 41) and rho.min() >= -1e-12 and rho.max() > 1
    _, _, lap = density.slice_values(water, origin, u, v, 3.0, 41, 'laplacian')
    assert lap.min() < 0 < lap.max()
    with pytest.raises(ValueError):
        density.plane(water, (0, 0, 1))


def test_marching_squares_on_a_circle():
    xs = ys = np.linspace(-2, 2, 81)
    gx, gy = np.meshgrid(xs, ys)
    segments = density.contours(gx**2 + gy**2, xs, ys, 1.0)
    r = np.linalg.norm(segments.reshape(-1, 2), axis=1)
    assert len(segments) > 50 and np.max(np.abs(r - 1)) < 0.01
    assert len(density.contours(gx**2 + gy**2, xs, ys, 100.0)) == 0

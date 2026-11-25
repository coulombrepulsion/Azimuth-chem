"""Isosurfaces and the ESP map for the Compass model (modules/compass/view/surfaces.py).

Oracles: a Gaussian f = exp(−r²/Å²) has the isosurface f = 1/e on the sphere r = 1 Å (area 4π Å²); the
orbital at the vertices of its surface equals ±level (orbital values from gto.values_at, not from the
grid); the potential of point charges is q / r written out here; for water the potential on the density
surface is most negative near the oxygen and most positive near a hydrogen (the Mulliken charges of the
file: O −0.34, H +0.17).
"""

from math import exp, pi
from pathlib import Path

import numpy as np
import pytest

from modules.compass.view import surfaces
from azimuth.core import Atom, Molecule
from modules.compass.chemistry.geometry_tools import BOHR

vtk = pytest.importorskip('vtk')
DATA = Path(__file__).parents[1] / 'data' / 'orbitals'


def gaussian_cube(step=0.08):
    from modules.spectrum.readers.cube import Cube

    axis = np.arange(-2.4, 2.4 + 1e-9, step)
    x, y, z = np.meshgrid(axis, axis, axis, indexing='ij')
    values = np.exp(-(x * x + y * y + z * z))[..., None]
    return Cube('g', Molecule('He', (Atom('He', 0, 0, 0),)), np.array([axis[0]] * 3), np.diag([step] * 3), values, (1,), 'Å')


def area(mesh):
    a, b, c = (mesh.vertices[mesh.triangles[:, k]] for k in range(3))
    return float(np.linalg.norm(np.cross(b - a, c - a), axis=1).sum() / 2)


def test_sphere_radius_and_area():
    full = surfaces.isosurface(gaussian_cube(), exp(-1), target=10**9)
    radius = np.linalg.norm(full.vertices, axis=1)
    assert np.max(np.abs(radius - 1.0)) < 0.01  # trilinear interpolation on a 0.08 Å grid
    assert area(full) == pytest.approx(4 * pi, rel=0.01)
    small = surfaces.isosurface(gaussian_cube(), exp(-1), target=800)
    assert len(small.triangles) <= 900 and area(small) == pytest.approx(4 * pi, rel=0.03)
    assert surfaces.isosurface(gaussian_cube(), 2.0) is None  # above the maximum: no surface
    with pytest.raises(ValueError):
        surfaces.isosurface(gaussian_cube(), float('nan'))


def water():
    from modules.spectrum.readers.orbital_files import read_orbitals

    return read_orbitals((DATA / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8'))


def test_water_orbital_phases():
    from modules.spectrum.analysis.gto import values_at
    from modules.spectrum.analysis.orbitals import orbital_cube

    orbitals = water()
    homo, _ = orbitals.frontier()
    cube = orbital_cube(orbitals, homo, step=0.1)
    meshes = surfaces.orbital_meshes(cube, 0.05)
    assert [m.color for m in meshes] == ['#3f7fe0', '#e05a4f'] and all(len(m.triangles) for m in meshes)
    for mesh, sign in zip(meshes, (1, -1)):
        psi = values_at(orbitals.shells, orbitals.centres, orbitals.coefficients[:, homo], mesh.vertices / BOHR)
        assert np.median(np.abs(psi - sign * 0.05)) < 0.004  # the decimated surface stays on the level
    # an orbital put over another one — its own pair of colours
    over = surfaces.orbital_meshes(cube, 0.05, colors=surfaces.ORBITAL_PAIRS[1])
    assert [m.color for m in over] == list(surfaces.ORBITAL_PAIRS[1])


def test_point_charge_potential_and_colours():
    v = surfaces.esp_at([[0, 0, 2 * BOHR], [3 * BOHR, 0, 0]], [[0, 0, 0]], [-0.5])
    assert v == pytest.approx([-0.25, -0.5 / 3], rel=1e-12)
    colors, limit = surfaces.esp_colors(np.array([-2.0, 0.0, 1.0, 2.0]))
    assert limit == 2.0 and np.allclose(colors[0], surfaces.RED) and np.allclose(colors[1], 1.0)
    assert np.allclose(colors[3], surfaces.BLUE) and np.allclose(colors[2], (surfaces.WHITE + surfaces.BLUE) / 2)
    mesh = surfaces.Mesh(np.array([[1.0, 0, 0]]), np.zeros((0, 3), int), np.array([[1.0, 0, 0]]))
    turned = surfaces.moved(mesh, np.array([[0, 1, 0], [-1, 0, 0], [0, 0, 1]]), [0, 0, 0], [5, 0, 0])
    assert np.allclose(turned.vertices, [[5, 1, 0]]) and np.allclose(turned.normals, [[0, 1, 0]])


def test_water_esp_on_the_density():
    from modules.spectrum.analysis.orbitals import density_cube

    orbitals = water()
    cube = density_cube(orbitals, step=0.12)
    mesh = surfaces.isosurface(cube, 0.002, color='#8fa6bf')
    charges = orbitals.mulliken()
    assert charges[0] < 0 < charges[1]
    centres = np.array([a.position for a in orbitals.molecule.atoms])
    values = surfaces.esp_at(mesh.vertices, centres, charges)
    nearest = np.argmin(np.linalg.norm(mesh.vertices[:, None, :] - centres[None, :, :], axis=2), axis=1)
    assert nearest[np.argmin(values)] == 0  # the most negative point is near the oxygen
    assert nearest[np.argmax(values)] in (1, 2)  # the most positive near a hydrogen
    distance = np.min(np.linalg.norm(mesh.vertices[:, None, :] - centres[None, :, :], axis=2), axis=1)
    assert 0.8 < distance.min() and distance.max() < 2.6  # around the van der Waals surface (Å)

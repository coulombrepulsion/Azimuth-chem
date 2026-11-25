"""The VTK engine of the Compass model (modules/compass/view/vtk_model.py) against the ray caster.

Oracles: modules/compass/view/raster.py draws the same scene analytically (spheres and rods as exact quadrics), so
the pixels VTK covers must coincide with the ones the ray caster covers; a sphere facing the viewer keeps its
element colour at its centre in both (the lighting of vtk_model §1 is chosen for that). Skipped where VTK is
not installed or cannot draw off screen.

Tolerances (vtk_model §8): edges may differ by about half a pixel, so for a disc of radius r the
intersection over union is at least 1 − 1/r: r = 40 → 0.975, the test asks 0.97; a scene with rods of radius
6 px loses more at their sides: 0.95. Colours: 8-bit rounding and the polygonal normals, 6 levels.
"""

import numpy as np
import pytest

pytest.importorskip('vtkmodules')
from modules.compass.view import raster, vtk_model  # noqa: E402

ok, why = vtk_model.available()
pytestmark = pytest.mark.skipif(not ok, reason='VTK does not draw off screen here: ' + why)

RED, BLUE = (200, 40, 40), (40, 60, 200)


def iou(a, b):
    a, b = a[..., 3] > 127, b[..., 3] > 127
    return (a & b).sum() / max(1, (a | b).sum())


def test_an_empty_scene_is_transparent():
    out = vtk_model.render(32, 24, [], [])
    assert out.shape == (24, 32, 4) and not out.any()


def test_one_sphere_covers_the_same_disc_with_its_colour_at_the_centre():
    scene = [(60.0, 50.0, 0.0, 40.0, RED)], []
    v, r = vtk_model.render(120, 100, *scene), raster.render(120, 100, *scene)
    assert iou(v, r) >= 0.97
    b, g, rr, a = (int(c) for c in v[50, 60])
    assert a == 255 and abs(rr - RED[0]) <= 6 and abs(g - RED[1]) <= 6 and abs(b - RED[2]) <= 6
    assert v[0, 0, 3] == 0 and v[50, 60 + 45, 3] == 0  # outside the disc


def test_two_atoms_and_a_bond_cover_the_pixels_of_the_ray_caster():
    spheres, rods = raster.build_scene(
        [(50.0, 60.0, 0.0, 18.0, RED), (150.0, 60.0, 0.0, 18.0, BLUE)], [(0, 1, 1, 12.0)], 'smooth', None, True
    )
    v, r = vtk_model.render(200, 120, spheres, rods), raster.render(200, 120, spheres, rods)
    assert iou(v, r) >= 0.95
    b, g, rr, a = (int(c) for c in v[60, 100])  # the middle of the bond: the two colours blended
    assert a == 255 and min(RED[0], BLUE[0]) - 6 <= rr <= max(RED[0], BLUE[0]) + 6
    assert rr > b - 40 and b > rr - 40  # neither pure red nor pure blue


def test_a_nearer_sphere_hides_a_farther_one():
    near, far = (60.0, 50.0, 30.0, 25.0, RED), (75.0, 50.0, -30.0, 25.0, BLUE)
    v = vtk_model.render(140, 100, [far, near], [])
    b, g, rr, _ = (int(c) for c in v[50, 62])
    assert rr > b  # the red (near) sphere is in front where they overlap


def test_supersampling_keeps_the_size_and_smooths_the_edge():
    scene = [(30.0, 30.0, 0.0, 20.0, RED)], []
    one, two = vtk_model.render(60, 60, *scene), vtk_model.render(60, 60, *scene, supersample=2)
    assert one.shape == two.shape == (60, 60, 4)
    assert set(np.unique(one[..., 3])) <= {0, 255} and len(np.unique(two[..., 3])) > 2


def test_bad_sizes_are_refused():
    with pytest.raises(ValueError):
        vtk_model.render(0, 10, [], [])
    with pytest.raises(ValueError):
        vtk_model.render(10, 10, [(1.0, float('nan'), 0.0, 1.0, RED)], [])


def sphere_mesh(cx, cy, cz, r, n=48):
    """A UV sphere in output pixels (y down) with its normals in view axes (y up): the oracle is the disc."""
    theta = np.linspace(0, np.pi, n + 1)
    phi = np.linspace(0, 2 * np.pi, 2 * n, endpoint=False)
    t, f = np.meshgrid(theta, phi, indexing='ij')
    nx, ny, nz = np.sin(t) * np.cos(f), np.sin(t) * np.sin(f), np.cos(t)
    normals = np.column_stack((nx.ravel(), ny.ravel(), nz.ravel()))
    points = np.column_stack((cx + r * normals[:, 0], cy - r * normals[:, 1], cz + r * normals[:, 2]))
    tris = []
    m = 2 * n
    for i in range(n):
        for j in range(m):
            a, b = i * m + j, i * m + (j + 1) % m
            c, d = (i + 1) * m + j, (i + 1) * m + (j + 1) % m
            tris += [(a, c, b), (b, c, d)]
    return points, normals, np.array(tris)


def test_a_surface_is_drawn_in_the_scene_of_the_atoms():
    # an isosurface (here a sphere of radius 40 px) covers the same disc as a sphere of the ray caster,
    # keeps its colour facing the viewer, and the depth test puts a nearer atom over it and a farther one under it
    points, normals, tris = sphere_mesh(60.0, 50.0, 0.0, 40.0)
    surface = (points, normals, tris, np.array(BLUE) / 255.0, 1.0)
    v = vtk_model.render(120, 100, [], [], surfaces=[surface])
    disc = raster.render(120, 100, [(60.0, 50.0, 0.0, 40.0, RED)], [])
    assert iou(v, disc) >= 0.95
    b, g, rr, a = (int(c) for c in v[50, 60])
    assert a == 255 and abs(b - BLUE[2]) <= 14 and abs(rr - BLUE[0]) <= 14
    near = vtk_model.render(120, 100, [(60.0, 50.0, 60.0, 15.0, RED)], [], surfaces=[surface])
    b, g, rr, _ = (int(c) for c in near[50, 60])
    assert rr > b  # the atom in front of the surface
    inside = vtk_model.render(120, 100, [(60.0, 50.0, -10.0, 15.0, RED)], [], surfaces=[surface])
    b, g, rr, _ = (int(c) for c in inside[50, 60])
    assert b > rr  # the atom inside the opaque surface is hidden


def test_a_surface_with_colours_per_vertex():
    points, normals, tris = sphere_mesh(40.0, 40.0, 0.0, 30.0, n=24)
    colours = np.where(points[:, :1] < 40.0, np.array([[1.0, 0.0, 0.0]]), np.array([[0.0, 0.0, 1.0]]))
    v = vtk_model.render(80, 80, [], [], surfaces=[(points, normals, tris, colours, 1.0)])
    left, right = v[40, 25], v[40, 55]
    assert left[2] > left[0] and right[0] > right[2]  # B, G, R order: red on the left, blue on the right

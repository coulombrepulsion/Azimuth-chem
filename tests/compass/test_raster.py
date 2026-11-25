"""modules/compass/view/raster.py: per-pixel depth of balls and sticks (contract in the module header).

Oracles are analytic, not taken from the implementation: a sphere's front surface, the straight
intersection line x0 = sqrt(r^2 - rho^2) of a rod leaving its atom in the screen plane, and the
rule that a nearer object hides a farther one.
"""

from math import sqrt
import numpy as np
import pytest
from modules.compass.view import raster
from modules.compass.view.raster import build_scene, render

RED, BLUE, GREY = (220, 40, 40), (40, 40, 220), (120, 136, 151)


def rgb(image, x, y):
    b, g, r, a = (int(v) for v in image[y, x])
    return r, g, b, a


def test_empty_picture_is_transparent():
    image = render(40, 30, [], [])
    assert image.shape == (30, 40, 4) and not image.any()


def test_sphere_covers_its_disk_only():
    image = render(60, 60, [(30.0, 30.0, 0.0, 12.0, RED)], [])
    assert rgb(image, 30, 30)[3] == 255
    assert rgb(image, 30 + 14, 30)[3] == 0 and rgb(image, 5, 5)[3] == 0


def test_surface_facing_the_viewer_keeps_its_colour():
    # N = (0, 0, 1): intensity exactly 1, the highlight lies towards the upper left
    image = render(80, 80, [(40.5, 40.5, 0.0, 30.0, GREY)], [])
    r, g, b, a = rgb(image, 40, 40)
    assert a == 255 and abs(r - GREY[0]) <= 4 and abs(b - GREY[2]) <= 4


def test_upper_left_is_lit_lower_right_is_shaded():
    image = render(80, 80, [(40.5, 40.5, 0.0, 30.0, GREY)], [])
    lit, shade = rgb(image, 28, 28), rgb(image, 52, 52)
    assert sum(lit[:3]) - sum(shade[:3]) >= 3 * 25


@pytest.mark.parametrize('front', [True, False])
def test_rod_in_front_hides_the_sphere_and_rod_behind_does_not(front):
    sphere = (50.5, 50.5, 0.0, 20.0, RED)
    z = 30.0 if front else -30.0
    rod = ((10.0, 50.5, z), (90.0, 50.5, z), 4.0, BLUE, BLUE, (0.5, 0.5))
    alone = render(100, 100, [sphere], [])
    both = render(100, 100, [sphere], [rod])
    if front:
        r, g, b, _ = rgb(both, 50, 50)
        assert b > r  # the rod's colour at the centre
    else:
        assert (rgb(both, 50, 50) == rgb(alone, 50, 50)) and (rgb(both, 50, 40) == rgb(alone, 50, 40))


def test_rod_meets_its_atom_along_the_analytic_intersection_line():
    r, rho, cx, cy = 30.0, 12.0, 40.5, 50.5
    x0 = cx + sqrt(r * r - rho * rho)  # where the rod surface meets the sphere surface
    sphere = (cx, cy, 0.0, r, RED)
    rod = ((cx, cy, 0.0), (cx + 70, cy, 0.0), rho, BLUE, BLUE, (0.5, 0.5))
    image = render(120, 100, [sphere], [rod], outline=False)
    for dy in (-6, 0, 6):  # the line is straight across the whole width of the rod
        before, after = rgb(image, int(x0 - 2), int(cy) + dy), rgb(image, int(x0 + 2), int(cy) + dy)
        assert before[0] > before[2] and after[2] > after[0]


def test_no_contour_where_a_rod_leaves_its_atom():
    sphere = (40.5, 50.5, 0.0, 30.0, RED)
    rod = ((40.5, 50.5, 0.0), (110.0, 50.5, 0.0), 8.0, BLUE, BLUE, (0.5, 0.5))
    plain = render(120, 100, [sphere], [rod], outline=False)
    lined = render(120, 100, [sphere], [rod], outline=True)
    assert np.array_equal(plain[50], lined[50])  # along the axis through the junction


def test_contour_marks_the_hidden_object_beside_a_crossing_rod():
    sphere = (50.5, 50.5, 0.0, 30.0, RED)
    rod = ((0.0, 50.5, 60.0), (100.0, 50.5, 60.0), 5.0, BLUE, BLUE, (0.5, 0.5))
    plain = render(100, 100, [sphere], [rod], outline=False)
    lined = render(100, 100, [sphere], [rod], outline=True)
    for y in (44, 56):  # sphere pixels just above and just below the rod
        assert sum(rgb(lined, 50, y)[:3]) < sum(rgb(plain, 50, y)[:3])
    for y in (45, 55):  # the rod's own edge pixels stay as they are
        assert rgb(lined, 50, y) == rgb(plain, 50, y)
    assert rgb(lined, 50, 50) == rgb(plain, 50, 50)  # the rod itself is not darkened


def test_colour_split_and_blend_along_a_bond():
    atoms = [(20.0, 40.5, 0.0, 6.0, RED), (100.0, 40.5, 0.0, 6.0, BLUE)]
    spheres, rods = build_scene(atoms, [(0, 1, 1, 10.0)], 'split')
    image = render(120, 80, spheres, rods)
    assert rgb(image, 44, 40)[0] > rgb(image, 44, 40)[2] and rgb(image, 76, 40)[2] > rgb(image, 76, 40)[0]
    spheres, rods = build_scene(atoms, [(0, 1, 1, 10.0)], 'smooth')
    middle = rgb(render(120, 80, spheres, rods), 60, 40)
    assert abs(middle[0] - middle[2]) < 30  # half way between red and blue
    spheres, rods = build_scene(atoms, [(0, 1, 1, 10.0)], 'uniform', GREY)
    assert {rods[0][3], rods[0][4]} == {GREY}


def test_bond_order_gives_parallel_rods():
    atoms = [(20.0, 40.0, 0.0, 6.0, RED), (100.0, 40.0, 0.0, 6.0, BLUE)]
    _, rods = build_scene(atoms, [(0, 1, 3, 4.0)])
    assert [rod[0][1] for rod in rods] == [34.0, 40.0, 46.0]  # 1.5 widths apart, across the bond
    _, rods = build_scene(atoms, [(0, 1, 3, 4.0)], multiple=False)
    assert len(rods) == 1


def test_supersampling_smooths_the_silhouette():
    sharp = render(60, 60, [(30.0, 30.0, 0.0, 17.3, RED)], [], supersample=1)
    smooth = render(60, 60, [(30.0, 30.0, 0.0, 17.3, RED)], [], supersample=2)
    assert set(np.unique(sharp[..., 3])) <= {0, 255}
    assert len(np.unique(smooth[..., 3])) > 2


def test_bands_give_the_same_picture(monkeypatch):
    spheres = [(30.0 + 25 * k, 40.0 + 15 * k, 5.0 * k, 14.0, RED) for k in range(4)]
    rods = [((30.0, 40.0, 0.0), (105.0, 85.0, 15.0), 4.0, RED, BLUE, (0.4, 0.6))]
    whole = render(140, 120, spheres, rods, supersample=2)
    monkeypatch.setattr(raster, 'BAND_PIXELS', 900)
    assert np.array_equal(render(140, 120, spheres, rods, supersample=2), whole)


def test_end_on_and_degenerate_rods_are_skipped():
    rods = [
        ((30.0, 30.0, 0.0), (30.0, 30.0, 20.0), 4.0, RED, RED, (0.5, 0.5)),
        ((30.0, 30.0, 0.0), (30.0, 30.0, 0.0), 4.0, RED, RED, (0.5, 0.5)),
    ]
    assert not render(60, 60, [], rods).any()


@pytest.mark.parametrize(
    'args', [(0, 10, [], []), (10, 10, [(1.0, 1.0, float('nan'), 2.0, RED)], []), (100_000, 100_000, [], [])]
)
def test_invalid_input_is_rejected(args):
    with pytest.raises(ValueError):
        render(*args)


def _box(A, B, rho, i0, i1, j0, j1):
    """The whole bounding box: what _strip replaced (the reference for the speed-up)."""
    gy, gx = np.mgrid[j0:j1, i0:i1]
    return gx.ravel(), gy.ravel()


def _random_scene(rng, width, height):
    k = int(rng.integers(1, 8))
    atoms = [
        (
            float(rng.uniform(-20, width + 20)),
            float(rng.uniform(-20, height + 20)),
            float(rng.uniform(-80, 80)),
            float(rng.uniform(3, 60)),
            tuple(int(c) for c in rng.integers(0, 256, 3)),
        )
        for _ in range(k)
    ]
    bonds = [(i, j, int(rng.integers(1, 4)), float(rng.uniform(1, 14))) for i in range(k) for j in range(i + 1, k)]
    return build_scene(atoms, bonds, ('smooth', 'split', 'uniform')[int(rng.integers(3))], (120, 136, 151))


def test_strip_gives_exactly_the_picture_of_the_whole_box(monkeypatch):
    # Oracle: the former exhaustive test of every pixel of a rod's bounding box. The strip only skips
    # pixels that cannot be on the rod, so the pictures must be equal byte for byte, not just close.
    rng = np.random.default_rng(5)
    scenes = []
    for _ in range(60):
        width, height = int(rng.integers(20, 240)), int(rng.integers(20, 240))
        scenes.append((width, height, *_random_scene(rng, width, height), int(rng.integers(1, 4))))
    fast = [render(w, h, s, r, supersample=ss) for w, h, s, r, ss in scenes]
    monkeypatch.setattr(raster, '_strip', _box)
    for image, (w, h, s, r, ss) in zip(fast, scenes):
        assert np.array_equal(image, render(w, h, s, r, supersample=ss))


@pytest.mark.parametrize('end', [(97.0, 23.0), (23.0, 97.0), (60.5, 95.0), (95.0, 60.5), (20.0, 20.4)])
def test_strip_covers_the_whole_silhouette_of_a_rod(end):
    # Oracle: brute-force distance of every pixel centre to the segment.
    A, B, rho = (20.0, 20.0, 0.0), (*end, 10.0), 6.0
    gx, gy = raster._strip(A, B, rho, 0, 120, 0, 120)
    got = set(zip(gx.tolist(), gy.tolist()))
    for x in range(120):
        for y in range(120):
            px, py = x + 0.5, y + 0.5
            ex, ey = B[0] - A[0], B[1] - A[1]
            s = min(1.0, max(0.0, ((px - A[0]) * ex + (py - A[1]) * ey) / (ex * ex + ey * ey)))
            if (px - A[0] - s * ex) ** 2 + (py - A[1] - s * ey) ** 2 <= rho * rho:
                assert (x, y) in got
    assert len(got) == len(gx)  # no pixel twice
    assert len(got) < 0.5 * 120 * 120  # and far fewer than the box for a long diagonal rod


def test_the_box_filter_is_the_mean_of_each_block():
    # raster._box against the mean of each block computed here one by one
    rng = np.random.default_rng(3)
    for ss in (2, 3):
        values = rng.random((6 * ss, 4 * ss, 3)) * 255
        expected = np.array([[values[r * ss:(r + 1) * ss, c * ss:(c + 1) * ss].reshape(-1, 3).mean(axis=0)
                              for c in range(4)] for r in range(6)])
        assert np.allclose(raster._box(values, ss), expected, rtol=0, atol=1e-9)
        alpha = rng.random((6 * ss, 4 * ss)).astype(np.float32)
        assert np.allclose(raster._box(alpha, ss), alpha.reshape(6, ss, 4, ss).mean(axis=(1, 3)), atol=1e-6)


def test_the_types_of_bonds_are_drawn_their_own_way():
    """An aromatic bond — a rod and a thinner dashed one; a partial one — dashes only; a colour of its own colours the
    whole bond."""
    atoms = [(0.0, 0.0, 0.0, 5.0, (200, 0, 0)), (100.0, 0.0, 0.0, 5.0, (0, 0, 200))]
    _, plain = build_scene(atoms, [(0, 1, 1, 4.0)])
    assert len(plain) == 1
    _, aromatic = build_scene(atoms, [(0, 1, 1, 4.0, {'kind': 'aromatic'})])
    full = [r for r in aromatic if r[0][0] == 0.0 and r[1][0] == 100.0]
    dashes = [r for r in aromatic if r not in full]
    assert len(full) == 1 and len(dashes) >= 3 and all(r[2] < full[0][2] for r in dashes)
    assert {r[0][1] for r in dashes} != {full[0][0][1]}  # beside the line, not on it
    _, double = build_scene(atoms, [(0, 1, 1, 4.0, {'kind': 'aromatic'})], aromatic='double')
    assert len(double) == 2
    _, single = build_scene(atoms, [(0, 1, 1, 4.0, {'kind': 'aromatic'})], aromatic='single')
    assert len(single) == 1
    _, partial = build_scene(atoms, [(0, 1, 2, 4.0, {'kind': 'partial'})])
    assert len(partial) >= 3 and all(r[0][1] == 0.0 for r in partial)  # one row of dashes, whatever the order
    assert partial[0][3] == (200, 0, 0) and partial[-1][3] == (0, 0, 200)  # each dash in the colour of its half
    _, tinted = build_scene(atoms, [(0, 1, 1, 4.0, {'color': (10, 200, 10)})])
    assert tinted[0][3] == tinted[0][4] == (10, 200, 10)
    picture = render(120, 20, *build_scene([(10.0, 10.0, 0.0, 4.0, (200, 0, 0)), (110.0, 10.0, 0.0, 4.0, (0, 0, 200))],
                                           [(0, 1, 1, 3.0, {'dashed': True})]))
    row = picture[10, 20:100, 3]
    assert (row > 0).any() and (row == 0).any()  # dashes and the gaps between them


def test_a_delocalized_bond_is_drawn_aromatic():
    # an order 1.5 broke the scene
    # (range of a float); it is a rod and a dashed one beside it, as an aromatic bond
    atoms = [(20.0, 40.5, 0.0, 6.0, RED), (100.0, 40.5, 0.0, 6.0, BLUE)]
    spheres, rods = build_scene(atoms, [(0, 1, 1.5, 10.0)], 'smooth')
    _, marked = build_scene(atoms, [(0, 1, 1, 10.0, {'kind': 'aromatic'})], 'smooth')
    assert len(rods) == len(marked) > 1

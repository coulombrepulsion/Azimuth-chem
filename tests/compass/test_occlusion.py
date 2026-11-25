"""The selection ring is cut by the atoms in front (modules/compass/view/occlusion.py). The oracle:
circles drawn by hand on a plane."""

from modules.compass.view.occlusion import in_front


def test_the_atoms_in_front_that_reach_the_ring():
    points = [(0, 0), (12, 0), (40, 0), (5, 0)]
    depths = [0.0, 1.0, 1.0, -1.0]  # 1 and 2 nearer than 0; 3 behind it
    radii = [10, 5, 5, 10]
    # the ring of 0 reaches 17 px: atom 1 (12 px, r 5) touches it, atom 2 (40 px) does not, atom 3 is behind
    assert in_front(0, points, depths, radii, 17) == [1]
    assert in_front(0, points, depths, radii, 17, drawn=[0, 2, 3]) == []
    assert in_front(1, points, depths, radii, 12) == []  # nothing nearer than atom 1


# what covers the label of each atom, at once — against the loop of label_clip before
from math import hypot  # noqa: E402

from modules.compass.view.occlusion import label_covers  # noqa: E402


def covers_one_by_one(points, depths, radii, drawn):
    found = {}
    for i in range(len(points)):
        (xi, yi), zi, ri = points[i], depths[i], radii[i]
        near = []
        for j in range(len(points)):
            if j == i or depths[j] <= zi or j not in drawn:
                continue
            d = hypot(points[j][0] - xi, points[j][1] - yi)
            if d >= ri + radii[j]:
                continue
            if d + 0.85 * ri <= radii[j]:
                found[i] = 'full'
                break
            near.append(j)
        else:
            if near:
                found[i] = near
    return found


def test_the_covers_of_all_labels_at_once_are_those_of_one_by_one():
    import random

    rng = random.Random(7)
    for n in (1, 2, 30, 600):
        points = [(rng.uniform(0, 400), rng.uniform(0, 300)) for _ in range(n)]
        depths = [rng.uniform(-5, 5) for _ in range(n)]
        radii = [rng.uniform(3, 25) for _ in range(n)]
        drawn = {k for k in range(n) if rng.random() > 0.1}
        assert label_covers(points, depths, radii, drawn) == covers_one_by_one(points, depths, radii, drawn), n
    assert label_covers(points, depths, radii, drawn, rows=[5]) == {
        k: v for k, v in covers_one_by_one(points, depths, radii, drawn).items() if k == 5}

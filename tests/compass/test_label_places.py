"""The labels of the critical points keep clear of each other and of the points (modules/compass/view/label_places.py)."""

from modules.compass.view.label_places import aim_label_places


def hit(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def test_crowded_points_of_ammonia_do_not_overlap():
    # a crowd: the nucleus of an H right under a bond point, another bond point near
    spots = [(630.0, 415.0, 'nucleus'), (632.0, 438.0, 'nucleus'), (632.0, 436.0, 'bond'), (572.0, 437.0, 'bond'),
             (552.0, 442.0, 'nucleus'), (686.0, 467.0, 'bond'), (700.0, 482.0, 'nucleus')]
    sizes = [(16.0, 10.0)] * len(spots)
    places = aim_label_places(spots, sizes)
    rects = [(x, y, w, h) for (x, y), (w, h) in zip(places, sizes)]
    for k in range(len(rects)):
        for j in range(k + 1, len(rects)):
            assert not hit(rects[k], rects[j]), (k, j)
    dots = [(x - 5, y - 5, 10, 10) for x, y, kind in spots if kind != 'nucleus']
    for k, (r, (x, y, kind)) in enumerate(zip(rects, spots)):
        assert not any(hit(r, d) for d in dots if d != (x - 5, y - 5, 10, 10)), k


def test_a_lonely_point_keeps_the_upper_right_and_no_label_no_place():
    assert aim_label_places([(100.0, 100.0, 'bond')], [(20.0, 10.0)]) == [(106.0, 84.0)]
    assert aim_label_places([(100.0, 100.0, 'nucleus')], [(20.0, 10.0)]) == [(111.0, 79.0)]
    assert aim_label_places([(1.0, 1.0, 'bond')], [None]) == [None]

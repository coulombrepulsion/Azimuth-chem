"""Which atoms are drawn in front of an atom — for its selection ring (the rubber band takes every atom inside
it, seen or not).

in_front(i, points, depths, radii, reach, drawn) -> [index]: points — (x, y) on the screen, depths — the z of the view
(greater is nearer), radii — the drawn radii in pixels, reach — the radius around atom i, drawn — the indices drawn
(hidden atoms cover nothing). No Qt.
"""

import numpy as np


def in_front(i, points, depths, radii, reach, drawn=None):
    """The atoms drawn nearer than atom i whose disks reach into the circle of radius `reach` around it —
    those that hide a part of what is drawn around atom i (its selection ring must not lie over
    the atoms in front of it)."""
    xy = np.asarray(points, float).reshape(-1, 2)
    z = np.asarray(depths, float)
    r = np.asarray(radii, float)
    others = np.arange(len(z)) if drawn is None else np.asarray(sorted(drawn), int)
    others = others[(others != i) & (z[others] > z[i])]
    if others.size == 0:
        return []
    d = np.hypot(xy[others, 0] - xy[i, 0], xy[others, 1] - xy[i, 1])
    return [int(j) for j in others[d < reach + r[others]]]


def label_covers(points, depths, radii, drawn=None, rows=None, fill=0.85):
    """For each atom of rows (all by default) what covers its label, at once with numpy —
    {i: 'full'} when a nearer drawn atom covers the whole label (it fills about fill × r around the centre), {i: [j…]}
    the nearer drawn atoms whose disks overlap its circle, nothing for an atom whose label is free. The rule is that
    of viewer_drawing.label_clip before."""
    xy = np.asarray(points, float).reshape(-1, 2)
    z = np.asarray(depths, float)
    r = np.asarray(radii, float)
    n = len(z)
    others = np.arange(n) if drawn is None else np.asarray(sorted(drawn), int)
    rows = np.arange(n) if rows is None else np.asarray(list(rows), int)
    found = {}
    if others.size == 0 or rows.size == 0:
        return found
    # sorted by x: a chunk of neighbouring rows meets only the atoms in its band of x (not all n × n pairs)
    others = others[np.argsort(xy[others, 0], kind='stable')]
    ox, oz, orr = xy[others], z[others], r[others]
    reach = float(orr.max())
    rows = rows[np.argsort(xy[rows, 0], kind='stable')]
    for start in range(0, len(rows), 128):
        chunk = rows[start:start + 128]
        cx, cr = xy[chunk, 0], r[chunk]
        lo = np.searchsorted(ox[:, 0], cx.min() - cr.max() - reach, 'left')
        hi = np.searchsorted(ox[:, 0], cx.max() + cr.max() + reach, 'right')
        if hi <= lo:
            continue
        band, bz, br = ox[lo:hi], oz[lo:hi], orr[lo:hi]
        d = np.hypot(cx[:, None] - band[None, :, 0], xy[chunk, 1][:, None] - band[None, :, 1])
        near = (bz[None, :] > z[chunk][:, None]) & (d < cr[:, None] + br[None, :])
        near &= others[None, lo:hi] != chunk[:, None]
        full = (near & (d + fill * cr[:, None] <= br[None, :])).any(axis=1)
        for k in np.flatnonzero(near.any(axis=1)):
            found[int(chunk[k])] = 'full' if full[k] else sorted(others[lo:hi][near[k]].tolist())
    return found

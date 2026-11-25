"""Per-pixel depth renderer of balls and sticks for the Compass model.

§1 PURPOSE
    Bonds must visibly leave one atom and enter the other, as in Chemcraft: the rod meets the
    sphere along their true intersection, a nearer object hides a farther one at every pixel,
    and spheres and rods share one light. The former renderer (bond_depth.py, QPainter slices
    with aliased clip paths) only approximated this.
§2 ALGORITHM
    Ray casting with orthographic rays along the view axis in screen space. For every pixel of
    an object's bounding box the front surface is found analytically:
        sphere (c, r): z = c_z + sqrt(r^2 - |p - c|^2)
        rod A->B, radius rho: |w_perp + t e_perp|^2 = rho^2, the larger root t,
                              accepted for 0 <= u <= 1 along the axis,
    and kept if it is nearer than what the depth buffer already holds (larger z is nearer).
    Shading: I = ambient + diffuse * max(L.N, 0), normalized so that a surface facing the
    viewer keeps its element colour exactly (I = 1 for N = (0, 0, 1)), with a narrow plateau
    |I - 1| < FLAT so that the middle strip of a rod shows the element colour; on rods only (atoms
    are matte since the white spots on the balls are gone) a white Blinn-Phong
    highlight; a thin darker contour where the depth jumps between objects (one object passes
    in front of another), none where a rod meets its own atom.
    Antialiasing: supersampling by an integer factor, box-filtered with premultiplied alpha.
§3 APPLICATIONS
    modules/compass/view/viewer.py draws the image under labels, measurements and selection marks.
§4 CONTRACT
    render(width, height, spheres, rods, supersample=1, outline=True) -> uint8 array (height, width, 4)
        premultiplied B, G, R, A (the byte order of QImage.Format_ARGB32_Premultiplied on
        little-endian machines). Coordinates in output pixels; y grows downwards; z grows
        towards the viewer, in the same pixel units as x and y.
        spheres: iterable of (x, y, z, r, (R, G, B))
        rods: iterable of (a, b, rho, colour_a, colour_b, (u0, u1)): a, b = (x, y, z) ends;
                 colour_a below u0, colour_b above u1, linear blend in between (u0 = u1: a sharp split).
    Pixels without objects are transparent (0, 0, 0, 0). Raises ValueError for a non-positive
    size, a size above MAX_PIXELS after supersampling, or a non-finite coordinate.
§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    NumPy only, no Qt: testable without a display. A sphere tests its bounding box, a rod only a strip
    along its axis (_strip); colours are computed for the pixels an object wins; contours are looked
    for only where neighbouring pixels show different objects (the same picture byte for
    byte, 2.5-3x faster: benzene filling a 1800x1240 Retina field 148 -> ~50 ms here, about 2.5x less
    on an M-series Mac).
§7 TESTS
    tests/compass/test_raster.py: analytic depth of a sphere, a rod in front of / behind a sphere,
    the intersection line, colour of a viewer-facing surface, transparency, supersampling; the strip
    against the whole box (equal pictures, byte for byte) and against brute-force distances.
§8' ROBUSTNESS
    Degenerate objects (r <= 0, zero-length rods, rods along the view axis) are skipped; their
    end spheres still show them. Objects outside the image are clipped.
"""

from math import isfinite, sqrt
import numpy as np

MAX_PIXELS = 100_000_000  # after supersampling; about 10000 x 10000
BAND_PIXELS = 2_000_000  # supersampled pixels shaded at once (about 70 MB of buffers)
LIGHT = np.array([-1.0, -1.0, 1.6]) / sqrt(1.0 + 1.0 + 1.6 * 1.6)  # upper left, in front
HALF = (LIGHT + np.array([0.0, 0.0, 1.0])) / np.linalg.norm(LIGHT + np.array([0.0, 0.0, 1.0]))
AMBIENT = 0.42
DIFFUSE = (1.0 - AMBIENT) / LIGHT[2]  # I = 1 exactly for a surface facing the viewer
SPECULAR, SHININESS = 0.55, 60
FLAT = 0.05  # |I - 1| below this shows the exact element colour (the middle of a rod, as before)
CONTOUR = 0.62  # brightness kept on a contour pixel
CONTOUR_STEP = 1.5  # depth jump (in supersampled pixels, relative to the nearer radius) that draws a contour


def _span(lo, hi, limit):
    a, b = max(0, int(np.floor(lo))), min(limit, int(np.ceil(hi)) + 1)
    return (a, b) if a < b else None


def _prepare(spheres, rods, ss, W, H):
    """Objects in supersampled pixels with their bounding boxes (i0, i1, j0, j1); invisible ones dropped."""
    items = []
    for x, y, z, r, colour in spheres:
        if not all(isfinite(v) for v in (x, y, z, r)):
            raise ValueError('render: non-finite sphere')
        x, y, z, r = x * ss, y * ss, z * ss, r * ss
        sx, sy = _span(x - r, x + r, W), _span(y - r, y + r, H)
        if r > 0 and sx and sy:
            items.append(('s', (*sx, *sy), (x, y, z, r, np.asarray(colour, np.float32))))
    for a, b, rho, colour_a, colour_b, stops in rods:
        if not all(isfinite(v) for v in (*a, *b, rho)):
            raise ValueError('render: non-finite rod')
        A, B, rho = np.asarray(a, float) * ss, np.asarray(b, float) * ss, rho * ss
        length = float(np.linalg.norm(B - A))
        if rho <= 0 or length < 1e-9:
            continue
        k = (B - A) / length
        if 1.0 - k[2] * k[2] < 1e-9:
            continue  # seen end-on: covered by its end spheres
        sx = _span(min(A[0], B[0]) - rho, max(A[0], B[0]) + rho, W)
        sy = _span(min(A[1], B[1]) - rho, max(A[1], B[1]) + rho, H)
        if sx and sy:
            ca, cb = np.asarray(colour_a, np.float32), np.asarray(colour_b, np.float32)
            items.append(('r', (*sx, *sy), (A, B, rho, length, k, ca, cb, stops)))
    return items


def render(width, height, spheres, rods, supersample=1, outline=True):
    ss = int(supersample)
    if type(width) is not int or type(height) is not int or width < 1 or height < 1 or ss < 1:
        raise ValueError('render: width, height and supersample must be positive integers')
    W, H = width * ss, height * ss
    if W * H > MAX_PIXELS:
        raise ValueError('render: image too large')
    out = np.zeros((height, width, 4), dtype=np.uint8)
    items = _prepare(spheres, rods, ss, W, H)
    if not items:
        return out
    # Work only inside the union of the boxes, aligned to whole output pixels, in bands of rows
    # (BAND_PIXELS supersampled pixels at most) so that large pictures need bounded memory.
    X0 = max(0, (min(b[0] for _, b, _ in items) - 1) // ss * ss)
    X1 = min(W, -(-(max(b[1] for _, b, _ in items) + 1) // ss) * ss)
    Y0 = max(0, (min(b[2] for _, b, _ in items) - 1) // ss * ss)
    Y1 = min(H, -(-(max(b[3] for _, b, _ in items) + 1) // ss) * ss)
    rows = max(ss, BAND_PIXELS // max(1, X1 - X0) // ss * ss)
    for y0 in range(Y0, Y1, rows):
        y1 = min(Y1, y0 + rows)
        r0, r1 = max(0, y0 - ss), min(H, y1 + ss)  # margin rows: contours across band edges
        band = [item for item in items if item[1][2] < r1 and item[1][3] > r0]
        rgb, alpha = _shade(band, ss, X0, X1, r0, r1, outline)
        rgb, alpha = rgb[y0 - r0 : y1 - r0], alpha[y0 - r0 : y1 - r0]
        if ss > 1:  # the box filter as a sum of strided views — 2.5x faster than mean over a 5-D reshape
            rgb, alpha = _box(rgb, ss), _box(alpha, ss)
        view = out[y0 // ss : y1 // ss, X0 // ss : X1 // ss]
        colour = np.rint(rgb).astype(np.uint8)  # premultiplied: rgb already carries the coverage
        view[..., 0], view[..., 1], view[..., 2] = colour[..., 2], colour[..., 1], colour[..., 0]  # B, G, R
        view[..., 3] = np.rint(alpha * 255).astype(np.uint8)
    return out


def _box(values, ss):
    """The mean of every ss × ss block (the supersampled pixels of one output pixel), as the sum of its ss² strided
    views (measured: the mean over axes (1, 3) of a reshape walked memory across and took most of a frame)."""
    out = None
    for i in range(ss):
        for j in range(ss):
            part = values[i::ss, j::ss]
            out = part.copy() if out is None else out.__iadd__(part)
    out *= 1.0 / (ss * ss)
    return out


def _strip(A, B, rho, i0, i1, j0, j1):
    """Pixel indices (gx, gy) of the box [i0, i1) x [j0, j1) within rho + 1 of the line AB.

    A superset of the rod's silhouette (the segment widened by rho), so the shading of every covered
    pixel is unchanged; a long diagonal rod no longer tests its whole bounding box (~50x fewer pixels).
    Spans are taken along the axis the rod runs across most: rows if |ey| >= |ex|, else columns."""
    ex, ey = B[0] - A[0], B[1] - A[1]
    swap = abs(ey) < abs(ex)
    if swap:  # walk columns: the same formulas with x and y exchanged
        A, B, ex, ey, i0, i1, j0, j1 = (A[1], A[0]), (B[1], B[0]), ey, ex, j0, j1, i0, i1
    rows = np.arange(j0, j1)
    centre = A[0] + ex * (rows + 0.5 - A[1]) / ey  # where the axis crosses the row's centre
    half = (rho + 1.0) * np.hypot(ex, ey) / abs(ey)  # half-width of the strip along the row
    lo = np.clip(np.floor(centre - half).astype(np.int64), i0, i1)
    hi = np.clip(np.ceil(centre + half).astype(np.int64) + 1, i0, i1)
    counts = np.maximum(hi - lo, 0)
    total = int(counts.sum())
    starts = np.cumsum(counts) - counts
    across = np.arange(total) - np.repeat(starts, counts) + np.repeat(lo, counts)
    along = np.repeat(rows, counts)
    return (along, across) if swap else (across, along)


def _shade(items, ss, X0, X1, Y0, Y1, outline):
    """Depth test and shading of the supersampled rectangle [X0, X1) x [Y0, Y1); returns (rgb, alpha).

    Colours are computed per object for the pixels it wins, not for the whole
    rectangle afterwards (the same formulas in float32, so the same picture), and a rod tests only a
    strip along its axis (_strip)."""
    h, w = Y1 - Y0, X1 - X0
    depth = np.full((h, w), -1e30, np.float32)  # finite, so differences stay defined
    rgb = np.zeros((h, w, 3), np.float64)  # float64 as the colour formula gives (DIFFUSE is a float64)
    owner = np.full((h, w), -1, np.int32)
    size = np.zeros((h, w), np.float32)  # radius of the visible object, for the contour threshold
    light, half = LIGHT.astype(np.float32), HALF.astype(np.float32)

    for oid, (kind, (i0, i1, j0, j1), data) in enumerate(items):
        j0, j1 = max(j0, Y0), min(j1, Y1)
        if j0 >= j1:
            continue
        if kind == 's':
            gy, gx = np.mgrid[j0:j1, i0:i1]
            gx, gy = gx.ravel(), gy.ravel()
        else:
            A, B = data[0], data[1]
            if (B[0] - A[0]) ** 2 + (B[1] - A[1]) ** 2 < 1e-12:
                continue
            gx, gy = _strip(A, B, data[2], i0, i1, j0, j1)
        px, py = gx + 0.5, gy + 0.5  # pixel centres
        if kind == 's':
            x, y, z, r, colour = data
            dx, dy = px - x, py - y
            h2 = r * r - dx * dx - dy * dy
            keep = np.nonzero(h2 > 0)[0]
            dx, dy, hz = dx[keep], dy[keep], np.sqrt(h2[keep])
            zz = z + hz
            n = np.stack([dx / r, dy / r, hz / r], axis=-1)
            colours = colour
            radius = r
        else:
            A, B, rho, length, k, ca, cb, (u0, u1) = data
            # Cheap 2D test first: the silhouette of a rod is the projected segment widened by rho.
            ex, ey = B[0] - A[0], B[1] - A[1]
            s = np.clip(((px - A[0]) * ex + (py - A[1]) * ey) / (ex * ex + ey * ey), 0.0, 1.0)
            qx, qy = px - A[0] - s * ex, py - A[1] - s * ey
            keep = np.nonzero(qx * qx + qy * qy <= rho * rho)[0]
            wv = np.stack([px[keep] - A[0], py[keep] - A[1], np.full(keep.size, -A[2])], axis=-1)
            e_perp = np.array([0.0, 0.0, 1.0]) - k[2] * k
            qa = float(e_perp @ e_perp)
            along = wv @ k
            w_perp = wv - along[:, None] * k
            qb = w_perp @ e_perp
            qc = np.einsum('ij,ij->i', w_perp, w_perp) - rho * rho
            disc = qb * qb - qa * qc
            t = (-qb + np.sqrt(np.clip(disc, 0.0, None))) / qa  # nearer root: larger z
            u = (along + t * k[2]) / length
            ok = (disc >= 0) & (u >= 0) & (u <= 1)
            keep, t, u = keep[ok], t[ok], u[ok]
            n = (w_perp[ok] + t[:, None] * e_perp) / rho
            f = np.clip((u - u0) / (u1 - u0), 0.0, 1.0) if u1 > u0 else (u >= u0).astype(float)
            colours = ca * (1 - f[:, None]) + cb * f[:, None]
            zz = t
            radius = rho
        rows, cols = gy[keep] - Y0, gx[keep] - X0
        inside = (rows >= 0) & (rows < h) & (cols >= 0) & (cols < w)
        if not inside.all():
            rows, cols, zz, n = rows[inside], cols[inside], zz[inside], n[inside]
            colours = colours if np.ndim(colours) == 1 else colours[inside]
        win = zz > depth[rows, cols]
        if not win.any():
            continue
        rows, cols = rows[win], cols[win]
        normal = n[win].astype(np.float32)
        base = np.asarray(colours if np.ndim(colours) == 1 else colours[win], np.float32)
        lambert = np.clip(normal @ light, 0.0, None)
        shade = AMBIENT + DIFFUSE * lambert - 1.0
        shade = np.sign(shade) * np.maximum(np.abs(shade) - FLAT, 0.0)  # plateau: the element colour itself
        colour = base * (1.0 + shade)[..., None]
        if kind == 'r':  # the highlight: rods only, atoms are matte
            colour = colour + (255.0 * (SPECULAR * np.clip(normal @ half, 0.0, None) ** SHININESS))[..., None]
        depth[rows, cols] = zz[win]
        rgb[rows, cols] = colour
        owner[rows, cols] = oid
        size[rows, cols] = radius

    hit = owner >= 0
    if outline:
        # Only pixel pairs that show two different objects can carry a contour: test those alone
        # (the same rule as before, applied to the few boundary pixels).
        contour = np.zeros((h, w), dtype=bool)
        for axis in (0, 1):
            first = (slice(None, -1), slice(None)) if axis == 0 else (slice(None), slice(None, -1))
            second = (slice(1, None), slice(None)) if axis == 0 else (slice(None), slice(1, None))
            o0, o1 = owner[first], owner[second]
            r, c = np.nonzero((o0 != o1) & (o0 >= 0) & (o1 >= 0))
            r1, c1 = (r + 1, c) if axis == 0 else (r, c + 1)
            d0, d1 = depth[r, c], depth[r1, c1]
            nearer = np.where(d0 > d1, size[r, c], size[r1, c1])
            jump = np.abs(d0 - d1) > np.maximum(CONTOUR_STEP * ss, 0.25 * nearer)
            behind = jump & (d0 < d1)  # the contour lies on the hidden (farther) object
            contour[r[behind], c[behind]] = True
            behind = jump & (d1 < d0)
            contour[r1[behind], c1[behind]] = True
        rgb[contour] *= CONTOUR
    # Colours are never negative (1 + shade >= 0.47) and zero where nothing is drawn: only the top
    # needs clipping (the highlight can exceed 255).
    np.minimum(rgb, 255.0, out=rgb)
    return rgb, hit.astype(np.float32)


DASH = 0.62  # the share of a stretch of a dashed bond its dash takes
DASH_STEP = 2.6  # widths of the rod a stretch (a dash and its gap) is long


def _dashes(a, b, rho, ca, cb, width):
    """A dashed rod from a to b — short rods, each in the colour of its half."""
    length = sqrt(sum((b[k] - a[k]) ** 2 for k in range(2)))
    count = max(3, int(length / max(1e-6, width * DASH_STEP)))
    out = []
    for n in range(count):
        u0 = (n + (1 - DASH) / 2) / count
        u1 = (n + (1 + DASH) / 2) / count
        p0 = tuple(a[k] + (b[k] - a[k]) * u0 for k in range(3))
        p1 = tuple(a[k] + (b[k] - a[k]) * u1 for k in range(3))
        colour = ca if (u0 + u1) / 2 < 0.5 else cb
        out.append((p0, p1, rho, colour, colour, (0.5, 0.5)))
    return out


def build_scene(atoms, bonds, bond_color='smooth', uniform=None, multiple=True, aromatic='dashed'):
    """Spheres and rods for render() from projected atoms and bonds.

    atoms: [(x, y, z, r, (R, G, B))] in pixels; bonds: [(i, j, order, width)] or [(i, j, order, width, style)] with the
    rod width in pixels. A bond of order n is n parallel rods 1.5 widths apart across the screen; each rod runs from
    atom centre to atom centre (the spheres hide its ends) and is split at the middle into the colours of its atoms
    ('smooth': blended over 0.4..0.6; 'uniform': the colour `uniform`). Style — {'kind': 'aromatic' | 'partial' | None,
    'dashed': bool, 'color': (R, G, B) | None}: an aromatic bond is a rod and a thinner dashed one beside it (aromatic
    'dashed'), two rods ('double') or one ('single'); a dashed bond (partial, coordination, long) is one row of short
    rods; a colour of its own colours the whole bond.
    """
    spheres = list(atoms)
    rods = []
    stops = (0.4, 0.6) if bond_color == 'smooth' else (0.5, 0.5)
    for bond in bonds:
        i, j, order, width = bond[:4]
        style = bond[4] if len(bond) > 4 and bond[4] else {}
        (xa, ya, za, _, ca), (xb, yb, zb, _, cb) = atoms[i], atoms[j]
        if bond_color == 'uniform' and uniform is not None:
            ca = cb = uniform
        if style.get('color') is not None:
            ca = cb = style['color']
        dx, dy = xb - xa, yb - ya
        length = sqrt(dx * dx + dy * dy)
        kind = style.get('kind')
        if order != int(order):  # a delocalized bond (1.5) never breaks the drawing — it is drawn aromatic
            kind, order = 'aromatic', 1
        if kind == 'aromatic' and multiple and length > 1e-6 and aromatic != 'single':
            lines = [(-0.75, False, 1.0), (0.75, aromatic == 'dashed', 0.75 if aromatic == 'dashed' else 1.0)]
        elif kind == 'partial' or style.get('dashed'):
            lines = [(0.0, True, 1.0)]
        else:
            count = order if multiple and length > 1e-6 else 1
            lines = [((n - (count - 1) / 2) * 1.5, False, 1.0) for n in range(count)]
        for shift, dashed, thin in lines:
            offset = shift * width
            ox, oy = (-dy / length * offset, dx / length * offset) if length > 1e-6 and offset else (0.0, 0.0)
            a, b = (xa + ox, ya + oy, za), (xb + ox, yb + oy, zb)
            if dashed:
                rods.extend(_dashes(a, b, width * thin / 2, ca, cb, width))
            else:
                rods.append((a, b, width * thin / 2, ca, cb, stops))
    return spheres, rods

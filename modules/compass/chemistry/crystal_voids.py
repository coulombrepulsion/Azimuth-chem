"""The voids of a crystal: where a probe sphere fits between the van der Waals spheres of the atoms — as
«Display Voids» of Mercury (CCDC).

§1 THEORY
    A point of the cell is a free place for the centre of a probe sphere of radius p when it is farther than r_vdW + p
    from every atom (and from its images in the cells around). The void (the «contact surface» of Mercury) is the
    union of the probe spheres put at all the free places: the space a solvent molecule of radius p can take — p = 1.2 Å
    by default (as in Mercury), 1.4 Å for water. p → 0 gives the space outside the van der Waals spheres, the
    complement of Kitaigorodsky's packing coefficient. A single atom of radius R in a large cell leaves the void
    V − 4/3 πR³ (every point beyond R is reached by a probe further out) — the oracle of the tests.
    Van der Waals radii: Bondi (1964) and Mantina et al. (2009), as modules/spectrum/analysis/contacts.VDW; 2.0 Å for an
    element without one.
§2 ALGORITHM
    A periodic grid over the cell (nₖ = ⌈|aₖ| / step⌉, at most MAX_POINTS points); the gap of a point
    g = min over the atoms and their images (|r − R| − r_vdW), by chunks; free = g > p. The union of the probe spheres
    is a periodic convolution of free with a ball of radius p on the grid (numpy FFT; the ball measured in Å in the
    metric of the cell): void = (free ⊛ ball) > ½. The separate voids — the connected parts of void on the periodic grid
    (6 neighbours, across the faces of the cell); a part that joins itself across a face goes on in the next cell —
    a channel along that edge. field — void smoothed by 3 × 3 × 3 averaging, for an isosurface at ½.
§4 SPECIFICATION
    voids(crystal, probe=1.2, step=0.2) -> Voids(volume Å³, fraction, cell_volume, parts [(volume Å³, channel axes 'ab'
    …)], field (n₁, n₂, n₃), probe, step).
§7 TESTS tests/compass/test_crystal_voids.py — one atom in a large cell (V − 4/3 πR³), rock salt without voids, a
    channel through a cell.
§8' ROBUSTNESS
    A probe of 0.1–4 Å; a grid step of 0.1–1 Å (made coarser to MAX_POINTS).
"""

from dataclasses import dataclass
from math import ceil

import numpy as np

MAX_POINTS = 400_000
DEFAULT_RADIUS = 2.0


@dataclass
class Voids:
    volume: float
    fraction: float
    cell_volume: float
    parts: list  # [(volume Å³, channel axes)], the largest first
    field: np.ndarray
    probe: float
    step: float


def _grid(rows, step):
    lengths = np.linalg.norm(rows, axis=1)
    while True:
        n = [max(8, int(ceil(x / step))) for x in lengths]
        if n[0] * n[1] * n[2] <= MAX_POINTS:
            return n, step
        step *= 1.1


def _gaps(atoms, rows, points, reach):
    """min over the atoms and their images of |r − R| − r_vdW at points (Cartesian Å)."""
    from modules.spectrum.analysis.contacts import VDW

    volume = abs(np.linalg.det(rows))
    heights = [volume / np.linalg.norm(np.cross(rows[(k + 1) % 3], rows[(k + 2) % 3])) for k in range(3)]
    m = [int(ceil(reach / h)) + 1 for h in heights]
    shifts = np.array([(i, j, k) for i in range(-m[0], m[0] + 1) for j in range(-m[1], m[1] + 1)
                       for k in range(-m[2], m[2] + 1)], dtype=float) @ rows
    centres = (np.array([a[1:4] for a in atoms], dtype=float) @ rows)
    radii = np.array([VDW.get(a[0], DEFAULT_RADIUS) for a in atoms])
    images = (centres[None, :, :] + shifts[:, None, :]).reshape(-1, 3)
    image_radii = np.tile(radii, len(shifts))
    # only the images that can come within reach of the cell
    low, high = np.zeros(3), np.ones(3)
    f = images @ np.linalg.inv(rows)
    margin = reach / np.array(heights)
    keep = np.all((f > low - margin) & (f < high + margin), axis=1)
    images, image_radii = images[keep], image_radii[keep]
    out = np.empty(len(points))
    for start in range(0, len(points), 2048):
        chunk = points[start:start + 2048]
        lo, hi = chunk.min(axis=0) - reach, chunk.max(axis=0) + reach  # the images near this part of the grid
        near = np.all((images >= lo) & (images <= hi), axis=1)
        if not near.any():
            out[start:start + 2048] = reach
            continue
        d = np.sqrt(((chunk[:, None, :] - images[near][None, :, :]) ** 2).sum(axis=2)) - image_radii[near][None, :]
        out[start:start + 2048] = np.minimum(d.min(axis=1), reach)
    return out


def _ball(n, rows, radius):
    """The periodic grid of the ball of radius (Å) around the node 0 in the metric of the cell."""
    axes = [np.minimum(np.arange(k), k - np.arange(k)) * np.where(np.arange(k) <= k // 2, 1, -1) for k in n]
    frac = np.stack(np.meshgrid(*[a / k for a, k in zip(axes, n)], indexing='ij'), axis=-1)
    distance = np.linalg.norm(frac @ rows, axis=-1)
    return (distance <= radius + 1e-9).astype(float)


def _convolve(a, b):
    return np.real(np.fft.ifftn(np.fft.fftn(a) * np.fft.fftn(b)))


def _labels(mask):
    """The connected parts of mask inside the grid (no wrap), by the smallest index spread to the neighbours."""
    n = mask.size
    label = np.where(mask, np.arange(n).reshape(mask.shape), n)
    while True:
        old = label
        label = label.copy()
        for axis in range(3):
            a = [slice(None)] * 3
            b = [slice(None)] * 3
            a[axis], b[axis] = slice(1, None), slice(None, -1)
            a, b = tuple(a), tuple(b)
            both = mask[a] & mask[b]
            label[a] = np.where(both, np.minimum(label[a], label[b]), label[a])
            label[b] = np.where(both, np.minimum(label[a], label[b]), label[b])
        if np.array_equal(label, old):
            return label


def _parts(mask):
    """[(nodes, axes)] — the connected parts of mask on the periodic grid; axes — the edges along which a part joins
    itself through the next cell (a channel). The parts inside the grid, then joined across its faces as a small graph
    whose edges carry the lattice step; a cycle with a step ≠ 0 is a channel."""
    if not mask.any():
        return []
    label = _labels(mask)
    names, sizes = np.unique(label[mask], return_counts=True)
    size = dict(zip(names.tolist(), sizes.tolist()))
    edges = {k: [] for k in size}
    for axis in range(3):
        hi = [slice(None)] * 3
        lo = [slice(None)] * 3
        hi[axis], lo[axis] = -1, 0
        hi, lo = tuple(hi), tuple(lo)
        both = mask[hi] & mask[lo]
        step = [0, 0, 0]
        step[axis] = 1
        for u, v in set(zip(label[hi][both].tolist(), label[lo][both].tolist())):
            edges[u].append((v, tuple(step)))
            edges[v].append((u, tuple(-x for x in step)))
    offset, found = {}, []
    for root in size:
        if root in offset:
            continue
        offset[root] = (0, 0, 0)
        stack, members, axes = [root], [], set()
        while stack:
            u = stack.pop()
            members.append(u)
            for v, step in edges[u]:
                shifted = tuple(offset[u][i] + step[i] for i in range(3))
                if v not in offset:
                    offset[v] = shifted
                    stack.append(v)
                elif offset[v] != shifted:
                    axes |= {'abc'[i] for i in range(3) if offset[v][i] != shifted[i]}
        found.append((sum(size[m] for m in members), ''.join(sorted(axes))))
    return found


def voids(crystal, probe=1.2, step=0.2):
    from modules.compass.chemistry import crystal as cr
    from modules.spectrum.analysis.contacts import VDW

    if not 0.1 <= probe <= 4.0:
        raise ValueError('a probe of 0.1–4 Å')
    if not 0.1 <= step <= 1.0:
        raise ValueError('a grid step of 0.1–1 Å')
    part = cr.main_part(crystal)
    atoms = [a for a in cr.unit_cell(part) if a[0] != 'X']
    rows = np.array(part.cell.vectors(), dtype=float)
    n, step = _grid(rows, step)
    f = np.stack(np.meshgrid(*[np.arange(k) / k for k in n], indexing='ij'), axis=-1).reshape(-1, 3)
    if atoms:
        reach = max(VDW.get(a[0], DEFAULT_RADIUS) for a in atoms) + probe + 0.5
        gaps = _gaps(atoms, rows, f @ rows, reach).reshape(n)
    else:
        gaps = np.full(n, np.inf)
    free = (gaps > probe).astype(float)
    void = _convolve(free, _ball(n, rows, probe)) > 0.5
    cell_volume = abs(float(np.linalg.det(rows)))
    per_node = cell_volume / void.size
    parts = sorted(((size * per_node, axes) for size, axes in _parts(void)), reverse=True)
    smooth = np.zeros(n)
    for i in (-1, 0, 1):
        for j in (-1, 0, 1):
            for k in (-1, 0, 1):
                smooth += np.roll(void.astype(float), (i, j, k), axis=(0, 1, 2))
    volume = float(void.sum() * per_node)
    return Voids(volume, volume / cell_volume, cell_volume, parts, smooth / 27.0, probe, step)

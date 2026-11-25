"""The Hirshfeld surface of a molecule in a crystal and its fingerprint plot (as CrystalExplorer — Mercury
has none).

§1 THEORY
    Spackman & Byrom (Chem. Phys. Lett. 267, 215, 1997), Spackman & Jayatilaka (CrystEngComm 11, 19, 2009): the
    promolecule — spherical free atoms at the nuclei — gives the weight of a molecule A at a point,
        w(r) = ρ_A(r) / ρ_crystal(r) = Σ_{i∈A} ρ_i(r) / Σ_{all i} ρ_i(r),
    and the Hirshfeld surface is w = ½: where the molecule's own atoms give half the density. The surfaces of the
    molecules of a crystal do not overlap and fill nearly all of it. On the surface: d_i — the distance to the
    nearest nucleus inside, d_e — outside; d_norm = (d_i − r_i^vdW)/r_i^vdW + (d_e − r_e^vdW)/r_e^vdW (negative —
    closer than the van der Waals radii: the red spots of hydrogen bonds). The fingerprint plot: the share of the
    surface area at each (d_i, d_e) — the spikes of H···O bonds, the wings of C–H···π, the diagonal of H···H.
    The spherical atom density here comes from the X-ray scattering factor of the free atom: f(s) is the Fourier
    transform of ρ(r), and the Gaussians of Waasmaier & Kirfel (Acta Cryst. A51, 416, 1995; the table of powder.py),
    f(s) = c + Σ a_k exp(−b_k s²), s = sin θ/λ, transform back into ρ(r) = Σ A_k exp(−α_k r²), α_k = 4π²/b_k,
    A_k = a_k (4π/b_k)^{3/2} (e/Å³). The constant c is a point at the nucleus in this fit, and some atoms (C, N, Fe …)
    have a pair of terms that nearly cancel — a huge a with b ≈ 0 against c (a sharp core): c and the terms with
    b < CORE_B are replaced by one sharp Gaussian of b = CORE_B holding the rest of the electrons, Z − Σ a_k, so that
    ∫ρ = Z — only the core within a few hundredths of an Å changes, not the outer density that the surface lies in.
§2 ALGORITHM
    The centre (the molecules given, else the first of the cell) and its neighbours within CUTOFF Å (crystal_shell);
    by default the H atoms first moved to their neutron distances (crystal_hydrogens, as CrystalExplorer). On a grid
    with the step given over the box of the centre ± MARGIN Å: ρ_in of the centre's atoms and ρ_out of the others,
    each atom only within REACH Å of it; w = ρ_in / (ρ_in + ρ_out). The surface w = ½ by marching tetrahedra (each
    grid cube cut into 6 tetrahedra along its main diagonal, a crossing of an edge interpolated linearly): a soup of
    triangles, each with its area and centroid; d_i, d_e and the elements of the nearest atoms at the centroids.
    The volume: the grid nodes with w ≥ ½ times the volume of a cell of the grid; the globularity G = (36π V²)^{1/3}/A
    (1 for a sphere).
§3 APPLICATIONS
    modules/compass/actions/hirshfeld_window.py: «Кристалл → Поверхность Хиршфельда…».
§4 SPECIFICATION
    density(symbol, r) -> ρ (e/Å³) of the free atom at the distances r (Å, array).
    surface(crystal, centre=None, step=0.2, normalize=True, factor=None) -> Surface: atoms (the centre: (symbol,
        x, y, z) …), others (the neighbours' atoms), origin, step, weight (the grid of w), triangles (m, 3, 3),
        area (m), d_i, d_e, d_norm (m), inside, outside (m, the elements of the nearest atoms), total_area,
        volume, globularity, molecule (the Molecule of the centre).
        Surface.fingerprint(low=0.4, high=2.6, width=0.01, pair=None) -> 2-D array of the area (Å²) in the bins
        [d_i, d_e]; pair = (element inside, element outside) or None for all.
        Surface.fractions(reciprocal=True) -> {'H···O': share of the area, …}; reciprocal — X···Y and Y···X together
        under the name with the elements in alphabetical order (as the tables of CrystalExplorer: 'H···O' is
        O···H/H···O).
    property_grid(surf, name) -> the grid of 'd_i', 'd_e', 'd_norm', 'shape_index' or 'curvedness' at the nodes of
        surf (to colour the surface drawn by VTK; the two curvatures only at the nodes of the cubes the surface
        crosses, 0 elsewhere — the colour of a point of the surface comes from the corners of its cube).
    weight_derivatives(points, inner, outer) -> (w, ∇w (n, 3), ∇∇w (n, 3, 3)) — analytic, from the Gaussians.
    level_curvatures(gradient, hessian) -> (κ1, κ2) of the level surface through each point, κ1 ≥ κ2, positive
        where it bends away from the direction of the gradient (a sphere of radius R around a minimum of f: 1/R).
    shape_curvedness(k1, k2) -> (S, C): S = (2/π) arctan((κ1 + κ2)/(κ1 − κ2)), C = (2/π) ln √((κ1² + κ2²)/2).
    Surface.shape_index(), Surface.curvedness() -> (m) at the centroids of the triangles.
    triangles(values, level, origin, step) -> (m, 3, 3) — marching tetrahedra on a grid with cubic cells.
§5 PROCEDURES - below.
§6 NOTES
    The promolecule and the scattering factors of neutral atoms: the surface does not depend on any calculation, as
    in CrystalExplorer.
    0.175.0 — the shape index and the curvedness (Koenderink & van Doorn, Image Vis. Comput. 10, 557, 1992; for
    Hirshfeld surfaces Spackman & Jayatilaka 2009, §4.2). The surface is the level w = ½ of a smooth function, so its
    principal curvatures come from the gradient g and the Hessian H of f = −w (f grows outward): the mean curvature
    (|g|² tr H − gᵀHg)/(2|g|³), the Gaussian gᵀ adj(H) g/|g|⁴ (Goldman, Comput. Aided Geom. Des. 22, 632, 2005);
    g and H of w are exact — the densities are sums of Gaussians. S = +1 — a cap (convex outward, blue), −1 — a cup
    (a hollow where an atom of a neighbour presses in, red), 0 — a saddle, ½ — a ridge; the red and blue triangles
    («bow ties») of S are the sign of π–π stacking. C — how strongly the surface bends: flat regions (C < −1,
    the faces of stacked rings) and sharp edges between them. The colours as CrystalExplorer: S from −1 red through
    white to +1 blue; C from −4 red to 0.4 blue.
§7 TESTS
    tests/compass/test_crystal_hirshfeld.py.
§8' ROBUSTNESS / ERRORS
    ValueError — a crystal without separate molecules, a centre without neighbours (the surface would be open), more
    than MAX_NODES grid nodes (a step too fine for the molecule).
"""

from dataclasses import dataclass, field
from functools import lru_cache
from math import pi

import numpy as np

from azimuth.i18n import tr

CUTOFF = 6.0  # Å: the molecules with an atom this close to the centre count
MARGIN = 3.2  # Å: the grid around the centre's atoms (d_i stays below 2.8 Å)
REACH = 6.0  # Å: an atom's density is added at the nodes this close
MAX_NODES = 4_000_000
CORE_B = 0.01  # Å²: the core of the scattering factor below it — one sharp Gaussian (§1)


@lru_cache(maxsize=None)
def _gaussians(symbol):
    from modules.compass.chemistry import powder

    entry = powder._f0().get('H' if symbol == 'D' else symbol)
    if entry is None:
        return None
    z, _, a, b = entry
    a, b = np.array(a, float), np.array(b, float)
    keep = b >= CORE_B
    a, b = a[keep], b[keep]
    core = z - a.sum()
    if abs(core) > 1e-9:
        a, b = np.append(a, core), np.append(b, CORE_B)
    return a * (4 * pi / b) ** 1.5, 4 * pi * pi / b


def density(symbol, r):
    r = np.asarray(r, float)
    g = _gaussians(symbol)
    if g is None:
        return np.zeros_like(r)
    amplitudes, exponents = g
    r2 = r * r
    return sum(amp * np.exp(-alpha * r2) for amp, alpha in zip(amplitudes, exponents))


@dataclass
class Surface:
    atoms: list
    others: list
    origin: np.ndarray
    step: float
    weight: np.ndarray
    triangles: np.ndarray
    area: np.ndarray
    d_i: np.ndarray
    d_e: np.ndarray
    d_norm: np.ndarray
    inside: np.ndarray
    outside: np.ndarray
    total_area: float
    volume: float
    globularity: float
    molecule: object = None
    title: str = ''
    extra: dict = field(default_factory=dict)

    def fingerprint(self, low=0.4, high=2.6, width=0.01, pair=None):
        n = int(round((high - low) / width))
        keep = np.ones(len(self.area), bool)
        if pair is not None:
            keep = (self.inside == pair[0]) & (self.outside == pair[1])
        grid, _, _ = np.histogram2d(self.d_i[keep], self.d_e[keep], bins=n, range=((low, high), (low, high)),
                                    weights=self.area[keep])
        return grid

    def curvatures(self):
        """(S, C) at the centroids of the triangles — computed once."""
        if 'curvatures' not in self.extra:
            _, g, h = weight_derivatives(self.triangles.mean(1), self.atoms, self.others)
            self.extra['curvatures'] = shape_curvedness(*level_curvatures(-g, -h))
        return self.extra['curvatures']

    def shape_index(self):
        return self.curvatures()[0]

    def curvedness(self):
        return self.curvatures()[1]

    def fractions(self, reciprocal=True):
        total = float(self.area.sum()) or 1.0
        out = {}
        for a, b, s in zip(self.inside, self.outside, self.area):
            key = '···'.join(sorted((a, b))) if reciprocal else f'{a}···{b}'
            out[key] = out.get(key, 0.0) + float(s)
        return dict(sorted(((k, v / total) for k, v in out.items()), key=lambda kv: -kv[1]))


# the six tetrahedra of a cube along its diagonal 0–6; the corners: 0 (0,0,0) 1 (1,0,0) 2 (1,1,0) 3 (0,1,0)
# 4 (0,0,1) 5 (1,0,1) 6 (1,1,1) 7 (0,1,1)
CORNERS = np.array([(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1)])
TETRAHEDRA = ((0, 5, 1, 6), (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6))


def _cases():
    """{bits of the inside corners: [triangles as triples of edges (p, q)]} for a tetrahedron."""
    out = {}
    for bits in range(16):
        inside = [k for k in range(4) if bits >> k & 1]
        outside = [k for k in range(4) if not bits >> k & 1]
        if len(inside) in (1, 3):
            p = inside[0] if len(inside) == 1 else outside[0]
            q = [k for k in range(4) if k != p]
            out[bits] = [((p, q[0]), (p, q[1]), (p, q[2]))]
        elif len(inside) == 2:
            (p1, p2), (q1, q2) = inside, outside
            out[bits] = [((p1, q1), (p1, q2), (p2, q2)), ((p1, q1), (p2, q2), (p2, q1))]
    return out


CASES = _cases()


def triangles(values, level, origin, step):
    values = np.asarray(values, float)
    origin = np.asarray(origin, float)
    above = values >= level
    nx, ny, nz = values.shape
    corner_above = np.stack([above[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in CORNERS], -1)
    crossing = corner_above.any(-1) & ~corner_above.all(-1)
    cubes = np.argwhere(crossing)
    if not len(cubes):
        return np.zeros((0, 3, 3))
    out = []
    for tet in TETRAHEDRA:
        idx = cubes[:, None, :] + CORNERS[list(tet)][None, :, :]  # (n, 4, 3)
        v = values[idx[..., 0], idx[..., 1], idx[..., 2]]  # (n, 4)
        pos = origin + idx * step
        bits = ((v >= level) * (1 << np.arange(4))).sum(1)
        for code, tris in CASES.items():
            sel = bits == code
            if not sel.any():
                continue
            vs, ps = v[sel], pos[sel]
            for tri in tris:
                corners = []
                for p, q in tri:
                    t = (level - vs[:, p]) / (vs[:, q] - vs[:, p])
                    corners.append(ps[:, p] + t[:, None] * (ps[:, q] - ps[:, p]))
                out.append(np.stack(corners, 1))
    return np.concatenate(out) if out else np.zeros((0, 3, 3))


def _nearest(points, centres, chunk=4000):
    """(distance, index) of the nearest of centres to each point."""
    centres = np.asarray(centres, float)
    dist = np.empty(len(points))
    index = np.empty(len(points), int)
    for lo in range(0, len(points), chunk):
        d = np.linalg.norm(points[lo:lo + chunk, None, :] - centres[None, :, :], axis=2)
        k = np.argmin(d, axis=1)
        index[lo:lo + chunk] = k
        dist[lo:lo + chunk] = d[np.arange(len(k)), k]
    return dist, index


def _vdw(symbol):
    from modules.spectrum.analysis import contacts as mc

    return mc.VDW.get(symbol, 1.8)


def surface(crystal, centre=None, step=0.2, normalize=True, factor=None):
    from azimuth.core import Molecule
    from modules.compass.chemistry import crystal_hydrogens, crystal_shell

    data = crystal_hydrogens.normalized(crystal)[0] if normalize else crystal
    found = crystal_shell.shell(data, centre, CUTOFF, False, factor)
    if not found.neighbours:
        raise ValueError(tr('У молекулы нет соседей ближе {} Å — поверхность Хиршфельда не замкнётся.').format(CUTOFF))
    atoms = [(a.symbol, a.x, a.y, a.z) for a in found.molecule.atoms]
    inner, outer = atoms[:found.centre_atoms], atoms[found.centre_atoms:]
    xyz_in = np.array([a[1:] for a in inner])
    xyz_out = np.array([a[1:] for a in outer])
    origin = xyz_in.min(0) - MARGIN
    shape = np.ceil((xyz_in.max(0) + MARGIN - origin) / step).astype(int) + 1
    if int(np.prod(shape)) > MAX_NODES:
        raise ValueError(tr('Слишком мелкий шаг для такой большой молекулы — возьмите шаг крупнее.'))
    rho_in = np.zeros(shape)
    rho_out = np.zeros(shape)
    reach = int(np.ceil(REACH / step))
    for target, group in ((rho_in, inner), (rho_out, outer)):
        for symbol, *p in group:
            centre_index = np.round((np.array(p) - origin) / step).astype(int)
            lo = np.maximum(centre_index - reach, 0)
            hi = np.minimum(centre_index + reach + 1, shape)
            if np.any(hi <= lo):
                continue
            axes = [origin[k] + step * np.arange(lo[k], hi[k]) - p[k] for k in range(3)]
            r2 = axes[0][:, None, None] ** 2 + axes[1][None, :, None] ** 2 + axes[2][None, None, :] ** 2
            target[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]] += density(symbol, np.sqrt(r2))
    total = rho_in + rho_out
    weight = np.where(total > 1e-12, rho_in / np.maximum(total, 1e-300), 0.0)
    tris = triangles(weight, 0.5, origin, step)
    if not len(tris):
        raise ValueError(tr('Поверхность Хиршфельда не получилась — проверьте молекулу.'))
    area = 0.5 * np.linalg.norm(np.cross(tris[:, 1] - tris[:, 0], tris[:, 2] - tris[:, 0]), axis=1)
    centroids = tris.mean(1)
    d_i, k_in = _nearest(centroids, xyz_in)
    d_e, k_out = _nearest(centroids, xyz_out)
    inside = np.array([inner[k][0] for k in k_in])
    outside = np.array([outer[k][0] for k in k_out])
    r_in = np.array([_vdw(s) for s in inside])
    r_out = np.array([_vdw(s) for s in outside])
    d_norm = (d_i - r_in) / r_in + (d_e - r_out) / r_out
    total_area = float(area.sum())
    volume = float((weight >= 0.5).sum() * step ** 3)
    globularity = float((36 * pi * volume ** 2) ** (1 / 3) / total_area) if total_area else 0.0
    from azimuth.core import Atom

    molecule = Molecule(f'{crystal.title or "crystal"} · Hirshfeld', tuple(Atom(s, x, y, z) for s, x, y, z in inner), None)
    return Surface(inner, outer, origin, step, weight, tris, area, d_i, d_e, d_norm, inside, outside, total_area,
                   volume, globularity, molecule, crystal.title or '')


def _density_derivatives(points, group, chunk=4000):
    """ρ, ∇ρ (n, 3), ∇∇ρ (n, 3, 3) of the spherical atoms of group ((symbol, x, y, z) …) at the points."""
    n = len(points)
    rho, grad, hess = np.zeros(n), np.zeros((n, 3)), np.zeros((n, 3, 3))
    eye = np.eye(3)
    for symbol, *p in group:
        g = _gaussians(symbol)
        if g is None:
            continue
        d = points - np.asarray(p, float)
        r2 = np.einsum('ij,ij->i', d, d)
        near = np.nonzero(r2 < REACH * REACH)[0]
        for lo in range(0, len(near), chunk):
            k = near[lo:lo + chunk]
            dk, rk = d[k], r2[k]
            outer = dk[:, :, None] * dk[:, None, :]
            for amplitude, alpha in zip(*g):
                e = amplitude * np.exp(-alpha * rk)
                rho[k] += e
                grad[k] += (-2 * alpha * e)[:, None] * dk
                hess[k] += (4 * alpha * alpha * e)[:, None, None] * outer - (2 * alpha * e)[:, None, None] * eye
    return rho, grad, hess


def weight_derivatives(points, inner, outer):
    """w = ρ_in/(ρ_in + ρ_out), its gradient and Hessian at the points — the quotient rule on the analytic ρ."""
    points = np.asarray(points, float)
    a, ga, ha = _density_derivatives(points, inner)
    b, gb, hb = _density_derivatives(points, outer)
    s = np.maximum(a + b, 1e-300)
    gs, hs = ga + gb, ha + hb
    w = a / s
    gw = ga / s[:, None] - (a / s ** 2)[:, None] * gs
    hw = (ha / s[:, None, None]
          - (ga[:, :, None] * gs[:, None, :] + gs[:, :, None] * ga[:, None, :]) / (s ** 2)[:, None, None]
          - (a / s ** 2)[:, None, None] * hs
          + (2 * a / s ** 3)[:, None, None] * gs[:, :, None] * gs[:, None, :])
    return w, gw, hw


def level_curvatures(gradient, hessian):
    g = np.asarray(gradient, float)
    h = np.asarray(hessian, float)
    norm2 = np.einsum('ij,ij->i', g, g)
    norm = np.sqrt(np.maximum(norm2, 1e-300))
    trace = np.einsum('ijj->i', h)
    ghg = np.einsum('ij,ijk,ik->i', g, h, g)
    mean = (norm2 * trace - ghg) / (2 * norm ** 3)
    rows = (np.cross(h[:, 1], h[:, 2]), np.cross(h[:, 2], h[:, 0]), np.cross(h[:, 0], h[:, 1]))  # the cofactors
    gauss = sum(g[:, k] * np.einsum('ij,ij->i', rows[k], g) for k in range(3)) / np.maximum(norm2 ** 2, 1e-300)
    spread = np.sqrt(np.maximum(mean * mean - gauss, 0.0))
    return mean + spread, mean - spread


def shape_curvedness(k1, k2):
    k1, k2 = np.asarray(k1, float), np.asarray(k2, float)
    shape = (2 / pi) * np.arctan2(k1 + k2, k1 - k2)
    curvedness = (2 / pi) * np.log(np.maximum(np.sqrt((k1 * k1 + k2 * k2) / 2), 1e-12))
    return shape, curvedness


def _curvature_grid(surf):
    """(S, C) on the nodes of the cubes the surface crosses (0 elsewhere)."""
    if 'curvature_grid' in surf.extra:
        return surf.extra['curvature_grid']
    above = surf.weight >= 0.5
    nx, ny, nz = above.shape
    corners = np.stack([above[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] for i, j, k in CORNERS], -1)
    crossing = corners.any(-1) & ~corners.all(-1)
    band = np.zeros(above.shape, bool)
    for i, j, k in CORNERS:
        band[i:nx - 1 + i, j:ny - 1 + j, k:nz - 1 + k] |= crossing
    nodes = np.argwhere(band)
    _, g, h = weight_derivatives(surf.origin + nodes * surf.step, surf.atoms, surf.others)
    shape_values, curved_values = shape_curvedness(*level_curvatures(-g, -h))
    grids = []
    for values in (shape_values, curved_values):
        grid = np.zeros(above.shape)
        grid[nodes[:, 0], nodes[:, 1], nodes[:, 2]] = values
        grids.append(grid)
    surf.extra['curvature_grid'] = tuple(grids)
    return surf.extra['curvature_grid']


def property_grid(surf, name):
    if name in ('shape_index', 'curvedness'):
        return _curvature_grid(surf)[0 if name == 'shape_index' else 1]
    shape = surf.weight.shape
    idx = np.indices(shape).reshape(3, -1).T
    points = surf.origin + idx * surf.step
    xyz_in = np.array([a[1:] for a in surf.atoms])
    xyz_out = np.array([a[1:] for a in surf.others])
    d_i, k_in = _nearest(points, xyz_in)
    if name == 'd_i':
        return d_i.reshape(shape)
    d_e, k_out = _nearest(points, xyz_out)
    if name == 'd_e':
        return d_e.reshape(shape)
    r_in = np.array([_vdw(a[0]) for a in surf.atoms])[k_in]
    r_out = np.array([_vdw(a[0]) for a in surf.others])[k_out]
    return ((d_i - r_in) / r_in + (d_e - r_out) / r_out).reshape(shape)

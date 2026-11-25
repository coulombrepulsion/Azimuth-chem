"""Isosurfaces on the Compass model: orbitals, electron and spin density, the electrostatic potential mapped on
the density.

§1 THEORY
    An isosurface f(r) = level of a field on a grid: for an orbital two surfaces, +level (one phase) and
    −level (the other); for the density one, typically 0.001–0.002 e/bohr³, close to the van der Waals
    surface. The electrostatic potential (ESP) of the molecule at r is
        V(r) = sum_A Z_A / |r − R_A| − ∫ rho(r') / |r − r'| dr'
    and on the density surface it shows where the molecule attracts a positive (V < 0, red) or a negative
    charge (V > 0, blue). Here V is approximated by the potential of atomic point charges q_A (Mulliken
    charges of the same orbitals): V(r) ≈ sum_A q_A / |r − R_A| (as Avogadro does with partial charges);
    the exact V needs the nuclear-attraction integrals of the whole basis at every point.
§2 ALGORITHM
    isosurface: VTK flying edges (vtkFlyingEdges3D) in the index space of the grid, the points mapped
    with r = origin + (i, j, k) · axes (Å), quadric decimation (vtkQuadricDecimation) down to about TARGET
    triangles, normals (vtkPolyDataNormals); a surface with no triangles gives None. esp_at: the sum of
    q / r with r in bohr (hartree per elementary charge). esp_colors: −limit → red (#d7302f), 0 →
    white, +limit → blue (#2c64c8), linear in between; limit = the largest |V| on the surface unless given.
    moved(mesh, rotation, from_centre, to_centre): (v − from) @ R + to — the frame of the structure in
    Compass (modules/compass/view/result_overlay.match gives R).
§3 APPLICATIONS
    modules/compass/actions/surface_actions.py (Compass), modules/spectrum/views/orbitals_view.py («На модели Компаса»).
§4 SPECIFICATION
    Mesh(vertices (n, 3) Å, triangles (m, 3) int, normals (n, 3), color '#rrggbb', values (n) | None,
    colors (n, 3) 0–1 | None). isosurface(cube, level, dataset=0, target=TARGET, color='#3f7fe0') -> Mesh |
    None; orbital_meshes(cube, level, target=TARGET) -> [Mesh] (+ blue, − red); esp_at(points Å, centres Å, charges) ->
    (n); esp_colors(values, limit=None) -> ((n, 3), limit); moved(mesh, rotation, a, b) -> Mesh.
    Sample(cube, points Å, dataset=0) -> (n) — the field at points, trilinear between the grid nodes
    (outside the grid: the nearest edge); nci_colors(values, low=NCI_LOW, high=NCI_HIGH) -> (n, 3) — the scale
    blue → green → red of sign(λ₂)ρ (a.u.) from NCI_LOW to NCI_HIGH, as Multiwfn's VMD scripts (−0.035 … 0.02).
    Nearest_values(points, known_points, known_values, k=4) -> (n) — inverse-distance weights of the k
    nearest known points (the ESP of Multiwfn at its surface vertices onto the vertices of our surface).
    Name 'shape_index' (−1 red … +1 blue) or 'curvedness' (−4 red … 0.4 blue) — fixed ranges.
    Hirshfeld_colors(values, name='d_norm') -> (n, 3) — red–white–blue as CrystalExplorer (d_norm: white at
    0; d_i, d_e: red at the shortest).
    ValueError: a level that is not finite or not above 0.
§5 PROCEDURES - below.
§6 NOTES
    TARGET = 6000 triangles: about 30 ms of drawing per frame in QPainter, so the model still turns
    smoothly; the decimated surface stays within a fraction of the grid step of the exact one. When VTK draws
    the surface on the graphics card (modules/compass/view/vtk_view.py) it is built again with
    target = viewer.FINE_TRIANGLES, i.e. in practice without decimation.
§7 TESTS
    tests/spectrum/test_surfaces.py (a Gaussian sphere: radius and area; water orbitals: the field at the vertices,
    the two phases; ESP of water: negative at the oxygen, positive at the hydrogens).
§8' ROBUSTNESS
    An empty or flat field (no crossing of the level) gives None, not an error.
"""

from dataclasses import dataclass, replace

import numpy as np

from modules.compass.chemistry.geometry_tools import BOHR

TARGET = 6000
RED, WHITE, BLUE = np.array((0.843, 0.188, 0.184)), np.array((1.0, 1.0, 1.0)), np.array((0.173, 0.392, 0.784))


@dataclass(frozen=True)
class Mesh:
    vertices: np.ndarray
    triangles: np.ndarray
    normals: np.ndarray
    color: str = '#3f7fe0'
    values: np.ndarray | None = None
    colors: np.ndarray | None = None


def isosurface(cube, level, dataset=0, target=TARGET, color='#3f7fe0'):
    import vtk
    from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

    if not np.isfinite(level) or level == 0:
        raise ValueError('the level must be finite and not zero')
    values = np.asarray(cube.values[..., dataset], dtype=np.float32)
    image = vtk.vtkImageData()
    image.SetDimensions(*values.shape)
    image.GetPointData().SetScalars(numpy_to_vtk(values.ravel(order='F'), deep=True))
    contour = vtk.vtkFlyingEdges3D()
    contour.SetInputData(image)
    contour.SetValue(0, float(level))
    contour.Update()
    raw = contour.GetOutput()
    if raw.GetNumberOfPolys() == 0:
        return None
    index = vtk_to_numpy(raw.GetPoints().GetData()).astype(float)
    points = np.asarray(cube.origin, float) + index @ np.asarray(cube.axes, float)
    mapped = vtk.vtkPolyData()
    vpoints = vtk.vtkPoints()
    vpoints.SetData(numpy_to_vtk(points, deep=True))
    mapped.SetPoints(vpoints)
    mapped.SetPolys(raw.GetPolys())
    data = mapped
    count = mapped.GetNumberOfPolys()
    if count > target:
        decimate = vtk.vtkQuadricDecimation()
        decimate.SetInputData(mapped)
        decimate.SetTargetReduction(1.0 - target / count)
        decimate.Update()
        data = decimate.GetOutput()
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(data)
    normals.SplittingOff()
    normals.ConsistencyOn()
    normals.Update()
    out = normals.GetOutput()
    vertices = vtk_to_numpy(out.GetPoints().GetData()).astype(float)
    cells = vtk_to_numpy(out.GetPolys().GetData()).reshape(-1, 4)
    if cells.size == 0 or np.any(cells[:, 0] != 3):
        cells = cells[cells[:, 0] == 3] if cells.size else cells
    triangles = cells[:, 1:4].astype(np.int64)
    vectors = out.GetPointData().GetNormals()
    normal = vtk_to_numpy(vectors).astype(float) if vectors is not None else np.zeros_like(vertices)
    if len(triangles) == 0:
        return None
    return Mesh(vertices, triangles, normal, color)


# the colours (+, −) of the orbitals put over the first one
ORBITAL_PAIRS = (('#3f7fe0', '#e05a4f'), ('#2e9e5b', '#d9a12b'), ('#8a5cc7', '#e07ab5'), ('#23a3b5', '#c9673a'))


def orbital_meshes(cube, level, target=TARGET, colors=ORBITAL_PAIRS[0]):
    level = abs(float(level))
    if not np.isfinite(level) or level == 0:
        raise ValueError('the level must be finite and not zero')
    out = []
    for sign, color in ((1, colors[0]), (-1, colors[1])):
        mesh = isosurface(cube, sign * level, target=target, color=color)
        if mesh is not None:
            out.append(mesh)
    return out


def esp_at(points, centres, charges):
    points = np.asarray(points, float) / BOHR
    centres = np.asarray(centres, float) / BOHR
    charges = np.asarray(charges, float)
    total = np.zeros(len(points))
    for c, q in zip(centres, charges):
        total += q / np.maximum(np.linalg.norm(points - c, axis=1), 1e-6)
    return total


def esp_colors(values, limit=None):
    values = np.asarray(values, float)
    if limit is None:
        limit = float(np.max(np.abs(values))) if values.size else 1.0
    limit = max(limit, 1e-12)
    t = np.clip(values / limit, -1.0, 1.0)[:, None]
    colors = np.where(t < 0, WHITE + (RED - WHITE) * (-t), WHITE + (BLUE - WHITE) * t)
    return colors, limit


NCI_LOW, NCI_HIGH = -0.035, 0.02  # a.u.: the colour range of sign(λ2)ρ of Multiwfn's NCI scripts for VMD
NCI_BLUE, NCI_GREEN, NCI_RED = np.array((0.12, 0.30, 0.90)), np.array((0.20, 0.78, 0.25)), np.array((0.90, 0.20, 0.15))


def sample(cube, points, dataset=0):
    values = np.asarray(cube.values[..., dataset], float)
    index = (np.asarray(points, float) - np.asarray(cube.origin, float)) @ np.linalg.inv(np.asarray(cube.axes, float))
    shape = np.array(values.shape)
    index = np.clip(index, 0, shape - 1)
    low = np.minimum(np.floor(index).astype(int), shape - 2).clip(0)
    t = index - low
    out = np.zeros(len(index))
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (t[:, 0] if dx else 1 - t[:, 0]) * (t[:, 1] if dy else 1 - t[:, 1]) * (t[:, 2] if dz else 1 - t[:, 2])
                i = np.minimum(low + (dx, dy, dz), shape - 1)
                out += w * values[i[:, 0], i[:, 1], i[:, 2]]
    return out


def nci_colors(values, low=NCI_LOW, high=NCI_HIGH):
    t = np.clip((np.asarray(values, float) - low) / (high - low), 0.0, 1.0)[:, None]
    return np.where(t < 0.5, NCI_BLUE + (NCI_GREEN - NCI_BLUE) * (2 * t), NCI_GREEN + (NCI_RED - NCI_GREEN) * (2 * t - 1))


def range_colors(values, low, high):
    """Blue at low, white in the middle, red at high (a function that is not centred on zero)."""
    t = np.clip((np.asarray(values, float) - low) / max(high - low, 1e-12), 0.0, 1.0)[:, None]
    return np.where(t < 0.5, BLUE + (WHITE - BLUE) * (2 * t), WHITE + (RED - WHITE) * (2 * t - 1))


CURVATURE_RANGES = {'shape_index': (-1.0, 1.0), 'curvedness': (-4.0, 0.4)}


def hirshfeld_colors(values, name='d_norm'):
    """The colours of a Hirshfeld surface as CrystalExplorer: d_norm — red below 0 (closer than the van der
    Waals radii, to the lowest value), white at 0, blue above (to the highest); d_i, d_e — red at the shortest, through
    white, blue at the longest."""
    v = np.asarray(values, float)
    if name in CURVATURE_RANGES:  # fixed ranges, as CrystalExplorer — S −1…+1, C −4…0.4
        low, high = CURVATURE_RANGES[name]
        t = np.clip((v - low) / (high - low), 0.0, 1.0)[:, None]
        return np.where(t < 0.5, RED + (WHITE - RED) * (2 * t), WHITE + (BLUE - WHITE) * (2 * t - 1))
    if name == 'd_norm':
        low, high = min(float(v.min()), -1e-6), max(float(v.max()), 1e-6)
        t = np.where(v < 0, -v / -low, v / high)[:, None].clip(0.0, 1.0)
        return np.where(v[:, None] < 0, WHITE + (RED - WHITE) * t, WHITE + (BLUE - WHITE) * t)
    low, high = float(v.min()), float(v.max())
    t = np.clip((v - low) / max(high - low, 1e-12), 0.0, 1.0)[:, None]
    return np.where(t < 0.5, RED + (WHITE - RED) * (2 * t), WHITE + (BLUE - WHITE) * (2 * t - 1))


def nearest_values(points, known_points, known_values, k=4):
    points = np.asarray(points, float)
    known = np.asarray(known_points, float)
    values = np.asarray(known_values, float)
    k = max(1, min(k, len(known)))
    out = np.empty(len(points))
    chunk = max(1, int(2e7 // max(1, len(known))))
    squares = np.sum(known ** 2, axis=1)
    for start in range(0, len(points), chunk):
        part = points[start:start + chunk]
        d2 = np.maximum(np.sum(part ** 2, axis=1)[:, None] + squares[None, :] - 2 * part @ known.T, 0.0)
        near = np.argpartition(d2, k - 1, axis=1)[:, :k] if k < len(known) else np.tile(np.arange(len(known)), (len(part), 1))
        dist = np.sqrt(np.take_along_axis(d2, near, axis=1))
        weight = 1.0 / np.maximum(dist, 1e-6)
        mixed = np.sum(weight * values[near], axis=1) / np.sum(weight, axis=1)
        first = np.argmin(dist, axis=1)  # on a known point: its own value
        same = dist[np.arange(len(part)), first] < 1e-5
        mixed[same] = values[near[np.arange(len(part)), first]][same]
        out[start:start + chunk] = mixed
    return out


def moved(mesh, rotation, from_centre, to_centre):
    rotation = np.asarray(rotation, float)
    vertices = (mesh.vertices - np.asarray(from_centre, float)) @ rotation + np.asarray(to_centre, float)
    return replace(mesh, vertices=vertices, normals=mesh.normals @ rotation)

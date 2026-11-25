"""Atoms and bonds of the Compass model drawn by VTK (OpenGL) instead of the NumPy ray caster.

HEADER
    The same contract as modules/compass/view/raster.py:render, so that modules/compass/view/bond_depth.py can draw
    the model with either engine («Вид → Трёхмерная графика VTK»). Everything else on the field (labels,
    selection rings, measurements, overlays, the cell, surfaces) is still painted by the view with QPainter
    over this picture, and picking, dragging and the camera stay in modules/compass/view/viewer.py.
    Wilkinson convention, sections 1-8.

§1 THEORY
    The scene is given in output pixels with y downwards and z towards the viewer (raster.py §4). VTK draws
    it in an orthographic (parallel) projection whose world units are those pixels: world (X, Y, Z) =
    (x, H − y, z), the camera looks along −Z at the centre of the image, view-up +Y, parallel scale H/2,
    so world X = 0..W and Y = 0..H fill the W × H window exactly and every object lands where the ray
    caster would put it. Spheres are true spheres (glyphs of one sphere source scaled by r); a rod a→b of
    radius ρ is a tube along the polyline a, a + u0(b − a), a + u1(b − a), b with the colours
    colour_a, colour_a, colour_b, colour_b, so the colour is colour_a below u0, colour_b above u1 and
    linear in between (u0 = u1: a split 2·SPLIT wide). The light matches raster.py: one directional light
    from the upper left in front, L = (−1, 1, 1.6)/|·| in world axes (y up), ambient 0.42 and diffuse
    (1 − 0.42)/L_z, so a surface facing the viewer keeps its element colour; atoms are matte, rods have
    the Blinn–Phong highlight of raster.py (power 60).
    Antialiasing: the image is drawn `supersample` times larger and box-filtered, as in raster.py.

§2 ALGORITHM
    One off-screen render window and renderer are kept for the session (creating an OpenGL context per
    frame is slow); per call: remove the old actors, build two actors (spheres, rods), set the window
    size and the camera, render, read the colour and the depth buffers, flip them to y downwards; a pixel
    is covered where its depth is nearer than the far plane (alpha planes are not reliable on every
    OpenGL), box-filter, convert to premultiplied B, G, R, A.

§3 APPLICATIONS
    modules/compass/view/bond_depth.draw_model when view.engine == 'vtk'.

§4 SPECIFICATION
    render(width, height, spheres, rods, supersample=1, outline=True, surfaces=()) -> uint8 array (height, width,
    4), exactly as raster.render (outline is accepted and ignored: VTK draws no contour lines); surfaces:
    (points (n, 3) output pixels, normals (n, 3) in view axes, triangles (m, 3), colours (n, 3) or (3), opacity).
    surface_actor(triangles, colours, opacity) -> (actor, polydata); place_surface(polydata, points, normals, H):
    the isosurfaces of modules/compass/view/surfaces.py in the scene of the atoms (vtk_view.py moves them every frame).
    available() -> (bool, message): whether VTK can be imported and can draw off screen on this computer.
    Raises ValueError for a non-positive size or an image above raster.MAX_PIXELS; RuntimeError if VTK
    cannot render (the caller falls back to raster.render).

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    VTK 9 modules (vtkmodules.*), imported on first use, so that the program starts without VTK. If the
    window returns a buffer of another size (a Retina backing scale), it is resampled to the requested
    size by nearest pixels. Sphere resolution SPHERE_THETA × SPHERE_PHI, tubes TUBE_SIDES sides.

§7 TEST CASES (tests/compass/test_vtk_model.py; skipped where VTK is not installed)
    An empty scene is fully transparent. One sphere: covered pixels agree with the analytic disc
    (the ray caster) to IOU >= 0.97, the centre pixel has the element colour within 6 levels. Two atoms
    and a rod: coverage IOU with raster.render >= 0.95, the rod middle blends the two colours. The
    picture is cached by nothing here (bond_depth caches it).

§8 ERROR ANALYSIS
    Positions: within half a pixel of the ray caster (both map pixel centres the same way); the
    polygonal sphere (SPHERE_THETA = 48) deviates from the true outline by r(1 − cos(π/48)) ≈ 0.002 r,
    below a pixel for r < 500 px. Colours: shading differs from raster.py only by the interpolation of
    normals over the polygons and by the absent contour lines.
"""

from __future__ import annotations

import numpy as np

from modules.compass.view.raster import AMBIENT, MAX_PIXELS, SHININESS, SPECULAR

SPHERE_THETA, SPHERE_PHI = 48, 32
TUBE_SIDES = 32
SPLIT = 1e-3  # half width of a "sharp" colour split along a rod, as a fraction of its length
LIGHT = np.array([-1.0, 1.0, 1.6]) / np.sqrt(1.0 + 1.0 + 1.6 * 1.6)  # raster.LIGHT with y up
DIFFUSE = (1.0 - AMBIENT) / LIGHT[2]

_state = {}


def _vtk():
    import vtkmodules.vtkRenderingOpenGL2  # noqa: F401  (registers the OpenGL implementations)
    from vtkmodules.util.numpy_support import numpy_to_vtk, vtk_to_numpy
    from vtkmodules.vtkCommonCore import vtkPoints
    from vtkmodules.vtkCommonDataModel import vtkCellArray, vtkPolyData
    from vtkmodules.vtkFiltersCore import vtkTubeFilter
    from vtkmodules.vtkFiltersSources import vtkSphereSource
    from vtkmodules.vtkRenderingCore import (
        vtkActor,
        vtkGlyph3DMapper,
        vtkLight,
        vtkPolyDataMapper,
        vtkRenderer,
        vtkRenderWindow,
        vtkWindowToImageFilter,
    )

    return dict(
        numpy_to_vtk=numpy_to_vtk, vtk_to_numpy=vtk_to_numpy, vtkPoints=vtkPoints, vtkCellArray=vtkCellArray,
        vtkPolyData=vtkPolyData, vtkTubeFilter=vtkTubeFilter, vtkSphereSource=vtkSphereSource, vtkActor=vtkActor,
        vtkGlyph3DMapper=vtkGlyph3DMapper, vtkLight=vtkLight, vtkPolyDataMapper=vtkPolyDataMapper,
        vtkRenderer=vtkRenderer, vtkRenderWindow=vtkRenderWindow, vtkWindowToImageFilter=vtkWindowToImageFilter,
    )


def _window():
    """The session's off-screen window, renderer, light and sphere source (created once)."""
    if 'window' in _state:
        return _state
    v = _vtk()
    window = v['vtkRenderWindow']()
    window.SetOffScreenRendering(1)
    window.SetAlphaBitPlanes(1)
    window.SetMultiSamples(0)
    if hasattr(window, 'SetShowWindow'):
        window.SetShowWindow(False)
    renderer = v['vtkRenderer']()
    renderer.SetBackground(0.0, 0.0, 0.0)
    renderer.SetBackgroundAlpha(0.0)
    renderer.AutomaticLightCreationOff()
    light = v['vtkLight']()
    light.SetLightTypeToSceneLight()
    light.SetPositional(False)
    light.SetColor(1.0, 1.0, 1.0)
    light.SetIntensity(1.0)
    renderer.AddLight(light)
    window.AddRenderer(renderer)
    sphere = v['vtkSphereSource']()
    sphere.SetRadius(1.0)
    sphere.SetThetaResolution(SPHERE_THETA)
    sphere.SetPhiResolution(SPHERE_PHI)
    grab = v['vtkWindowToImageFilter']()
    grab.SetInput(window)
    grab.SetInputBufferTypeToRGBA()
    grab.ReadFrontBufferOff()
    depth = v['vtkWindowToImageFilter']()  # coverage from the depth buffer: not every OpenGL keeps alpha
    depth.SetInput(window)
    depth.SetInputBufferTypeToZBuffer()
    depth.ReadFrontBufferOff()
    _state.update(v=v, window=window, renderer=renderer, light=light, sphere=sphere, grab=grab, depth=depth)
    return _state


def available():
    """(True, '') if VTK draws off screen here, else (False, the reason)."""
    import os

    if os.environ.get('AZIMUTH_NO_VTK', '').strip() == '1':  # the Windows machines of GitHub have no OpenGL —
        return False, 'VTK switched off (AZIMUTH_NO_VTK=1)'  # a probe there fell with an access violation, not an error
    try:
        out = render(4, 4, [(2.0, 2.0, 0.0, 1.5, (200, 40, 40))], [])
    except Exception as exc:  # noqa: BLE001 — any failure means "not available"
        return False, f'{type(exc).__name__}: {exc}'
    return bool(out[..., 3].any()), '' if out[..., 3].any() else 'VTK drew nothing'


def _material(mapper):
    """The scalar colours colour both the ambient and the diffuse light (where VTK has the switch)."""
    if hasattr(mapper, 'SetScalarMaterialModeToAmbientAndDiffuse'):
        mapper.SetScalarMaterialModeToAmbientAndDiffuse()


def _colours(v, rgb):
    array = v['numpy_to_vtk'](np.ascontiguousarray(rgb, dtype=np.uint8), deep=True)
    array.SetName('rgb')
    return array


def _sphere_actor(s, spheres, H):
    v = s['v']
    xyz = np.array([(x, H - y, z) for x, y, z, _, _ in spheres], dtype=np.float64)
    radius = v['numpy_to_vtk'](np.array([r for *_, r, _ in spheres], dtype=np.float64), deep=True)
    radius.SetName('radius')
    points = v['vtkPoints']()
    points.SetData(v['numpy_to_vtk'](xyz, deep=True))
    data = v['vtkPolyData']()
    data.SetPoints(points)
    data.GetPointData().AddArray(radius)
    data.GetPointData().AddArray(_colours(v, [c for *_, c in spheres]))
    mapper = v['vtkGlyph3DMapper']()
    mapper.SetInputData(data)
    mapper.SetSourceConnection(s['sphere'].GetOutputPort())
    mapper.SetScaleArray('radius')
    mapper.SetScaleModeToScaleByMagnitude()
    mapper.ScalingOn()
    mapper.OrientOff()
    mapper.SetScalarModeToUsePointFieldData()
    mapper.SelectColorArray('rgb')
    mapper.SetColorModeToDirectScalars()
    _material(mapper)
    mapper.ScalarVisibilityOn()
    actor = v['vtkActor']()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetInterpolationToPhong()
    prop.SetAmbient(AMBIENT)
    prop.SetDiffuse(DIFFUSE)
    prop.SetSpecular(0.0)
    return actor


def _rod_actor(s, rods, H):
    v = s['v']
    xyz, rad, rgb = [], [], []
    lines = v['vtkCellArray']()
    for a, b, rho, ca, cb, (u0, u1) in rods:
        if u1 - u0 < 2 * SPLIT:
            mid = (u0 + u1) / 2
            u0, u1 = max(0.0, mid - SPLIT), min(1.0, mid + SPLIT)
        A = np.array((a[0], H - a[1], a[2]), dtype=np.float64)
        B = np.array((b[0], H - b[1], b[2]), dtype=np.float64)
        stops = [(0.0, ca)] + ([(u0, ca)] if u0 > 0 else []) + ([(u1, cb)] if u1 < 1 else []) + [(1.0, cb)]
        first = len(xyz)
        for u, c in stops:
            xyz.append(A + u * (B - A))
            rad.append(rho)
            rgb.append(c)
        lines.InsertNextCell(len(stops))
        for k in range(len(stops)):
            lines.InsertCellPoint(first + k)
    points = v['vtkPoints']()
    points.SetData(v['numpy_to_vtk'](np.array(xyz, dtype=np.float64), deep=True))
    data = v['vtkPolyData']()
    data.SetPoints(points)
    data.SetLines(lines)
    radius = v['numpy_to_vtk'](np.array(rad, dtype=np.float64), deep=True)
    radius.SetName('radius')
    data.GetPointData().SetScalars(radius)  # the tube filter reads the radius from the active scalars
    data.GetPointData().AddArray(_colours(v, rgb))
    tube = v['vtkTubeFilter']()
    tube.SetInputData(data)
    tube.SetNumberOfSides(TUBE_SIDES)
    tube.SetVaryRadiusToVaryRadiusByAbsoluteScalar()
    tube.CappingOn()
    mapper = v['vtkPolyDataMapper']()
    mapper.SetInputConnection(tube.GetOutputPort())
    mapper.SetScalarModeToUsePointFieldData()
    mapper.SelectColorArray('rgb')
    mapper.SetColorModeToDirectScalars()
    _material(mapper)
    mapper.ScalarVisibilityOn()
    actor = v['vtkActor']()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetInterpolationToPhong()
    prop.SetAmbient(AMBIENT)
    prop.SetDiffuse(DIFFUSE)
    prop.SetSpecular(SPECULAR)
    prop.SetSpecularPower(SHININESS)
    prop.SetSpecularColor(1.0, 1.0, 1.0)
    return actor


def _resample(a, H, W):
    """a with H rows and W columns (nearest pixels): a Retina window may return a larger buffer."""
    h, w = a.shape[:2]
    if (h, w) == (H, W):
        return a
    rows = (np.arange(H) * h // H).clip(0, h - 1)
    cols = (np.arange(W) * w // W).clip(0, w - 1)
    return a[rows][:, cols]


def render(width, height, spheres, rods, supersample=1, outline=True, surfaces=()):
    ss = int(supersample)
    if type(width) is not int or type(height) is not int or width < 1 or height < 1 or ss < 1:
        raise ValueError('render: width, height and supersample must be positive integers')
    W, H = width * ss, height * ss
    if W * H > MAX_PIXELS:
        raise ValueError('render: image too large')
    spheres = [(x * ss, y * ss, z * ss, r * ss, c) for x, y, z, r, c in spheres]
    rods = [(tuple(k * ss for k in a), tuple(k * ss for k in b), rho * ss, ca, cb, u) for a, b, rho, ca, cb, u in rods]
    for item in spheres:
        if not all(np.isfinite(item[:4])):
            raise ValueError('render: non-finite coordinate')
    for a, b, rho, *_ in rods:
        if not (all(np.isfinite(a)) and all(np.isfinite(b)) and np.isfinite(rho)):
            raise ValueError('render: non-finite coordinate')
    surfaces = [(np.asarray(p, float) * ss, n, t, c, o) for p, n, t, c, o in surfaces]
    for p, *_ in surfaces:
        if not np.all(np.isfinite(p)):
            raise ValueError('render: non-finite coordinate')
    out = np.zeros((height, width, 4), dtype=np.uint8)
    if not spheres and not rods and not surfaces:
        return out
    try:
        s = _window()
        renderer, window = s['renderer'], s['window']
        renderer.RemoveAllViewProps()
        if spheres:
            renderer.AddActor(_sphere_actor(s, spheres, H))
        if rods:
            renderer.AddActor(_rod_actor(s, rods, H))
        for points, normals, triangles, colours, opacity in surfaces:
            actor, data = surface_actor(triangles, colours, opacity)
            place_surface(data, points, normals, H)
            renderer.AddActor(actor)
        window.SetSize(W, H)
        zs = [z + r for _, _, z, r, _ in spheres] + [max(a[2], b[2]) + rho for a, b, rho, *_ in rods]
        zs += [float(np.max(p[:, 2])) for p, *_ in surfaces if len(p)]
        top = max(zs) + 10.0 * max(W, H)
        camera = renderer.GetActiveCamera()
        camera.ParallelProjectionOn()
        camera.SetFocalPoint(W / 2, H / 2, 0.0)
        camera.SetPosition(W / 2, H / 2, top)
        camera.SetViewUp(0.0, 1.0, 0.0)
        camera.SetParallelScale(H / 2)
        s['light'].SetFocalPoint(W / 2, H / 2, 0.0)
        s['light'].SetPosition(W / 2 + LIGHT[0] * top, H / 2 + LIGHT[1] * top, LIGHT[2] * top)
        renderer.ResetCameraClippingRange()
        window.Render()
        grab = s['grab']
        grab.Modified()
        grab.Update()
        image = grab.GetOutput()
        w, h, _ = image.GetDimensions()
        pixels = s['v']['vtk_to_numpy'](image.GetPointData().GetScalars()).reshape(h, w, -1)[::-1]
        depth = s['depth']
        depth.Modified()
        depth.Update()
        zimage = depth.GetOutput()
        zw, zh, _ = zimage.GetDimensions()
        zbuf = s['v']['vtk_to_numpy'](zimage.GetPointData().GetScalars()).reshape(zh, zw)[::-1]
    except ValueError:
        raise
    except Exception as exc:  # noqa: BLE001 — reported to the caller, which falls back to raster.render
        raise RuntimeError(f'VTK could not draw the model: {type(exc).__name__}: {exc}') from exc
    pixels, zbuf = _resample(pixels, H, W), _resample(zbuf, H, W)
    alpha = (zbuf < 1.0).astype(np.float64)[..., None]  # the far plane (1.0) is the empty background
    rgb = pixels[..., :3].astype(np.float64) * alpha  # premultiplied
    if ss > 1:
        rgb = rgb.reshape(height, ss, width, ss, 3).mean(axis=(1, 3))
        alpha = alpha.reshape(height, ss, width, ss, 1).mean(axis=(1, 3))
    colour = np.rint(rgb).clip(0, 255).astype(np.uint8)
    out[..., 0], out[..., 1], out[..., 2] = colour[..., 2], colour[..., 1], colour[..., 0]
    out[..., 3] = np.rint(alpha[..., 0] * 255).clip(0, 255).astype(np.uint8)
    return out


# -- the pieces for drawing straight into the window (modules/compass/view/vtk_view.py) -------------
def kit():
    """The VTK classes and the shared unit sphere (no window is made here)."""
    if 'v' not in _state:
        v = _vtk()
        sphere = v['vtkSphereSource']()
        sphere.SetRadius(1.0)
        sphere.SetThetaResolution(SPHERE_THETA)
        sphere.SetPhiResolution(SPHERE_PHI)
        _state.update(v=v, sphere=sphere)
    return _state


def make_light():
    """The light of §1: directional, from the upper left in front (placed by place_camera)."""
    light = kit()['v']['vtkLight']()
    light.SetLightTypeToSceneLight()
    light.SetPositional(False)
    light.SetColor(1.0, 1.0, 1.0)
    light.SetIntensity(1.0)
    return light


def scene_actors(spheres, rods, H):
    """The actors of the spheres and rods of a scene in pixels of a window H pixels high (§1)."""
    s = kit()
    out = []
    if spheres:
        out.append(_sphere_actor(s, spheres, H))
    if rods:
        out.append(_rod_actor(s, rods, H))
    return out


def place_camera(renderer, light, W, H, spheres, rods):
    """The orthographic camera of §1 for a W x H window (world units = pixels) and the light with it."""
    zs = [z + r for _, _, z, r, _ in spheres] + [max(a[2], b[2]) + rho for a, b, rho, *_ in rods] or [0.0]
    top = max(zs) + 10.0 * max(W, H)
    camera = renderer.GetActiveCamera()
    camera.ParallelProjectionOn()
    camera.SetFocalPoint(W / 2, H / 2, 0.0)
    camera.SetPosition(W / 2, H / 2, top)
    camera.SetViewUp(0.0, 1.0, 0.0)
    camera.SetParallelScale(H / 2)
    light.SetFocalPoint(W / 2, H / 2, 0.0)
    light.SetPosition(W / 2 + LIGHT[0] * top, H / 2 + LIGHT[1] * top, LIGHT[2] * top)
    renderer.ResetCameraClippingRange()


# -- isosurfaces (orbitals, densities, ESP) in the same scene as the atoms and bonds ----------------------
def surface_actor(triangles, colours, opacity=1.0):
    """(actor, polydata) of a triangulated surface with per-vertex colours (n, 3) in 0..1 (or one colour (3,)
    for all) and the given opacity; its points and normals are set by place_surface (every frame)."""
    s = kit()
    v = s['v']
    from vtkmodules.util.numpy_support import numpy_to_vtkIdTypeArray

    triangles = np.asarray(triangles, dtype=np.int64).reshape(-1, 3)
    cells = v['vtkCellArray']()
    offsets = np.arange(0, 3 * len(triangles) + 1, 3, dtype=np.int64)
    cells.SetData(numpy_to_vtkIdTypeArray(offsets, deep=True), numpy_to_vtkIdTypeArray(triangles.ravel(), deep=True))
    data = v['vtkPolyData']()
    data.SetPoints(v['vtkPoints']())
    data.SetPolys(cells)
    colours = np.asarray(colours, dtype=float)
    count = int(triangles.max()) + 1 if len(triangles) else 0
    if colours.ndim == 1:
        colours = np.tile(colours, (count, 1))
    data.GetPointData().AddArray(_colours(v, np.rint(np.clip(colours, 0.0, 1.0) * 255)))
    mapper = v['vtkPolyDataMapper']()
    mapper.SetInputData(data)
    mapper.SetScalarModeToUsePointFieldData()
    mapper.SelectColorArray('rgb')
    mapper.SetColorModeToDirectScalars()
    _material(mapper)
    mapper.ScalarVisibilityOn()
    actor = v['vtkActor']()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetInterpolationToPhong()
    prop.SetAmbient(AMBIENT)
    prop.SetDiffuse(DIFFUSE)
    prop.SetSpecular(0.25)
    prop.SetSpecularPower(30.0)
    prop.SetSpecularColor(1.0, 1.0, 1.0)
    prop.SetOpacity(float(min(1.0, max(0.0, opacity))))
    prop.BackfaceCullingOff()
    return actor, data


def hex_rgb(name):
    """'#rrggbb' -> (r, g, b) in 0..1."""
    name = name.lstrip('#')
    return tuple(int(name[k : k + 2], 16) / 255.0 for k in (0, 2, 4))


def place_surface(data, points, normals, H):
    """Put the vertices (n, 3) — output pixels, y down, z towards the viewer, as the spheres — and their normals
    in view axes (x right, y up, z towards the viewer) into the polydata of surface_actor (§1: world Y = H − y)."""
    v = kit()['v']
    points = np.asarray(points, dtype=np.float64)
    world = np.column_stack((points[:, 0], H - points[:, 1], points[:, 2]))
    data.GetPoints().SetData(v['numpy_to_vtk'](world, deep=True))
    normals = np.asarray(normals, dtype=np.float64)
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    array = v['numpy_to_vtk'](normals / np.maximum(length, 1e-12), deep=True)
    array.SetName('Normals')
    data.GetPointData().SetNormals(array)
    data.Modified()

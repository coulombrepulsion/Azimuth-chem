"""Atoms and bonds of the Compass model drawn with a per-pixel depth test.

Contract: draw_model(view, painter, points, colors) paints the spheres of all atoms and the rods of
all bonds (none in spacefill mode or with bonds hidden) into the painter's device at its full
resolution. Every pixel shows the surface nearest to the viewer (modules/compass/view/raster.py), so
a bond visibly leaves one atom and enters the other along their real intersection, and nearer
atoms and bonds hide farther ones. Larger view-space z is nearer. Colours: the element colours
in `colors` (unknown elements #9c80b7); bond halves follow their atoms ('smooth' blends over
0.4..0.6 of the length, other modes split at 0.5; 'uniform' uses one grey). A bond of order n is
n rods 1.5 widths apart when multiple bonds are shown. The rod width is
max(1, bond_width * scale * 0.08 * mean depth factor) pixels, as before.
Supersampling ×2 antialiases screens with a pixel ratio below 2 when the view is still; while it
moves (draw_model) frames are drawn faster at a lower resolution. The picture is cached until the
geometry, view, size or colours change.
With view.engine == 'vtk' the same spheres and rods are drawn by modules/compass/view/vtk_model.py;
if VTK is missing or cannot draw, the view switches back to the built-in renderer and emits
view.engineFailed(message) once.
The molecule, camera, selection and scientific coordinates are never changed.
(replaces the QPainter slices with clip masks, whose aliased clipping blurred the
junctions of bonds and atoms.)
"""

from time import perf_counter
from math import ceil
from PySide6.QtCore import QPointF
from PySide6.QtGui import QColor, QImage, QPainter
from modules.compass.chemistry.builder import connections
from modules.compass.view.raster import build_scene, render

UNKNOWN = '#9c80b7'
UNIFORM = {False: '#788897', True: '#aebdc7'}  # one bond colour in the light / dark theme


def _rgb(name):
    colour = QColor(name)
    return colour.red(), colour.green(), colour.blue()


def model_scene(view, points, colors, ratio=1.0):
    """(spheres, rods) of raster.render for the projected atoms, in device pixels."""
    scale = view.camera()[1]
    # «Скрыть атомы H» — the hidden atoms are left out of the scene (every display mode, both engines)
    hidden = view.hidden_atoms() if hasattr(view, 'hidden_atoms') else frozenset()
    shown = [i for i in range(len(points)) if i not in hidden]
    number = {i: k for k, i in enumerate(shown)}
    atoms = []
    tints = getattr(view, 'atom_tints', None)  # (molecule, {index: colour}) of the crystal coloured by symmetry
    tints = tints[1] if tints and tints[0] is view.molecule else {}
    for i in shown:
        point, z = points[i]
        symbol = view.molecule.atoms[i].symbol
        atoms.append(
            (
                point.x() * ratio,
                point.y() * ratio,
                z * scale * view.depth_factor(z) * ratio,
                view.atom_radius(i) * ratio,
                _rgb(tints[i] if i in tints else colors.get(symbol, '#b9c1cc' if symbol == 'X' else UNKNOWN)),  # X
            )
        )
    bonds = []
    from azimuth import defaults

    if view.display_mode != 'spacefill' and view.show_bonds:
        marks = getattr(view, 'bond_marks', None) or {}  # the type and the colour of a bond of its own
        partial = defaults.get('bond_partial_color')
        long_factor = defaults.get('bond_long_factor') if defaults.get('bond_long_dashed') else None
        for i, j, order in connections(view.molecule):
            if i in hidden or j in hidden:
                continue
            fa, fb = view.depth_factor(points[i][1]), view.depth_factor(points[j][1])
            width = max(1.0, view.bond_width * scale * 0.08 * (fa + fb) / 2)
            mark = marks.get((min(i, j), max(i, j))) or {}
            dashed = mark.get('kind') == 'partial' or (long_factor is not None and is_long(view.molecule, i, j, long_factor))
            colour = mark.get('color') or (partial if dashed and partial else '')
            style = {'kind': mark.get('kind'), 'dashed': dashed, 'color': _rgb(colour) if colour else None}
            bonds.append((number[i], number[j], order, width * ratio, style))
    uniform = defaults.get('bond_uniform_color') or UNIFORM[bool(view.dark)]
    return build_scene(atoms, bonds, view.bond_color, _rgb(uniform), view.multiple_bonds,
                       defaults.get('bond_aromatic_style'))


def is_long(molecule, i, j, factor):
    """A bond longer than factor × the sum of the covalent radii of its atoms (a weak bond, a bond of a
    transition state) — drawn dashed when «Стиль связей → длинные связи пунктиром» is on."""
    from math import dist

    from modules.compass.chemistry.builder import RADII

    a, b = molecule.atoms[i], molecule.atoms[j]
    return dist(a.position, b.position) > factor * (RADII.get(a.symbol, 0.8) + RADII.get(b.symbol, 0.8))


FULL_ENOUGH = 0.03  # s: 0.91.14 — a full-quality frame this fast is kept while the view moves (~30 frames a second)
FAIR_ENOUGH = 0.09  # s: 0.173.1 — a full frame this fast: the moving frames on a Retina screen are drawn at 3/4 of the
# resolution, not 1/2


def draw_model(view, painter, points, colors):
    """Fast frames while the view moves (view.interactive()): no supersampling, and on a Retina screen
    (pixel ratio >= 1.5) half the device resolution, scaled up smoothly — 4 times fewer pixels; the
    full-quality frame follows when the movement stops. Snapshots are always full quality."""
    device_ratio = getattr(view, 'export_ratio', None) or painter.device().devicePixelRatioF()  # SVG/PDF
    fast = view.interactive() if hasattr(view, 'interactive') else view.press is not None
    if fast and getattr(view, '_full_seconds', 1.0) < FULL_ENOUGH:
        fast = False  # a model drawn in full quality fast enough stays sharp while it turns (was blurred)
    from azimuth import defaults

    many = defaults.get('quick_atoms')  # «Настройки → Вид модели» (Display → Quick of Chemcraft)
    large = bool(many and not getattr(view, 'capture', False) and len(points) >= many)
    if large:
        fast = True  # a large model: fast frames always, also at rest; snapshots stay full quality
    if fast and device_ratio >= 1.5:
        fair = not large and getattr(view, '_full_seconds', 1.0) < FAIR_ENOUGH
        ratio = device_ratio * (0.75 if fair else 0.5)
    else:
        ratio = device_ratio
    spheres, rods = model_scene(view, points, colors, ratio)
    width, height = ceil(view.width() * ratio), ceil(view.height() * ratio)
    supersample = 1 if ratio >= 2 or fast else 2
    engine = getattr(view, 'engine', 'raster')
    key = (width, height, supersample, tuple(spheres), tuple(rods), engine)
    cached = getattr(view, '_model_image', None)
    if cached is None or cached[0] != key:
        pixels = None
        if engine == 'vtk':  # the same scene drawn by VTK (modules/compass/view/vtk_model.py)
            try:
                from modules.compass.view import vtk_model

                pixels = vtk_model.render(width, height, spheres, rods, supersample=supersample)
            except (ImportError, RuntimeError) as exc:
                view.engine = 'raster'  # back to the built-in renderer for this session
                key = key[:-1] + ('raster',)
                failed = getattr(view, 'engineFailed', None)
                if failed is not None:
                    failed.emit(str(exc))
        if pixels is None:
            started = perf_counter()
            pixels = render(width, height, spheres, rods, supersample=supersample)
            if not fast:
                view._full_seconds = perf_counter() - started  # the cost of a full-quality frame
        image = QImage(pixels.data, width, height, 4 * width, QImage.Format.Format_ARGB32_Premultiplied).copy()
        image.setDevicePixelRatio(ratio)
        cached = view._model_image = (key, image)
    if ratio != device_ratio:
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawImage(QPointF(0, 0), cached[1])
        painter.restore()
    else:
        painter.drawImage(QPointF(0, 0), cached[1])

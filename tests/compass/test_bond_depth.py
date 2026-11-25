"""Rendered-pixel oracles: front rod covers a sphere; rear rod cannot cover it.

Every oracle runs for both engines of the model — the built-in ray caster ('raster') and VTK
('vtk', skipped where VTK is not installed or cannot draw off screen); a VTK run must not fall back.
"""

import os

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6.QtWidgets import QApplication
from azimuth.core import Molecule, Atom
from modules.compass.view.viewer import MoleculeView

WINDOW_SIZE = 480
FRONT_Z = 1.0
BACK_Z = -1.0


@pytest.fixture(params=['raster', 'vtk'])
def view(request):
    """The same oracles for both engines of the model; VTK only where it draws off screen."""
    if request.param == 'vtk':
        pytest.importorskip('vtkmodules')
        from modules.compass.view import vtk_model

        ok, why = vtk_model.available()
        if not ok:
            pytest.skip('VTK does not draw off screen here: ' + why)
    app = QApplication.instance() or QApplication([])
    widget = MoleculeView()
    widget.engine = request.param
    widget.resize(WINDOW_SIZE, WINDOW_SIZE)
    widget.yaw = widget.pitch = widget.roll = 0.0
    widget.label_mode = 'none'
    widget.show_hbonds = False
    widget.show()
    app.processEvents()
    yield widget
    widget.close()
    widget.deleteLater()
    app.processEvents()


@pytest.mark.parametrize('perspective', [False, True])
@pytest.mark.parametrize('dark', [False, True])
@pytest.mark.parametrize('z', [BACK_Z, FRONT_Z])
def test_renders_correct_occlusion_when_rod_crosses_atom(view, perspective, dark, z):
    # Arrange
    view.perspective = perspective
    view.dark = dark
    view.bond_color = 'uniform'
    view.set_molecule(
        Molecule('occlusion', (Atom('O', 0, 0, 0), Atom('C', -1, 0, z), Atom('C', 1, 0, z)), ((1, 2, 1),))
    )
    view.show_bonds = False
    without = view.grab().toImage().pixelColor(WINDOW_SIZE // 2, WINDOW_SIZE // 2)
    # Act
    view.show_bonds = True
    with_bond = view.grab().toImage().pixelColor(WINDOW_SIZE // 2, WINDOW_SIZE // 2)
    # Assert
    if z == FRONT_Z:
        assert with_bond != without
    else:
        assert with_bond == without


@pytest.mark.parametrize('z', [BACK_Z, FRONT_Z])
def test_renders_attachment_inside_silhouette_only_for_front_bond(view, z):
    # Arrange
    view.set_molecule(Molecule('attachment', (Atom('O', 0, 0, 0), Atom('C', 1, 0, z)), ((0, 1, 1),)))
    view.bond_color = 'uniform'
    center = view.projected()[0][0]
    x, y = round(center.x() + view.atom_radius(0) * 0.6), round(center.y())
    view.show_bonds = False
    without = view.grab().toImage().pixelColor(x, y)
    # Act
    view.show_bonds = True
    with_bond = view.grab().toImage().pixelColor(x, y)
    # Assert
    if z == FRONT_Z:
        assert with_bond != without
    else:
        assert with_bond == without


@pytest.mark.parametrize('reverse_order', [False, True])
def test_renders_front_bond_at_crossing_regardless_of_bond_list_order(view, reverse_order):
    # Arrange
    atoms = (Atom('O', -1, 0, FRONT_Z), Atom('O', 1, 0, FRONT_Z), Atom('N', 0, -1, BACK_Z), Atom('N', 0, 1, BACK_Z))
    front, rear = (0, 1, 1), (2, 3, 1)
    view.set_molecule(Molecule('crossing', atoms, (front,)))
    reference = view.grab().toImage().pixelColor(WINDOW_SIZE // 2, WINDOW_SIZE // 2)
    # Act
    bonds = (rear, front) if reverse_order else (front, rear)
    view.set_molecule(Molecule('crossing', atoms, bonds))
    actual = view.grab().toImage().pixelColor(WINDOW_SIZE // 2, WINDOW_SIZE // 2)
    # Assert
    assert actual == reference


@pytest.mark.parametrize('dark', [False, True])
@pytest.mark.parametrize('roll', [0.0, 1.5707963267948966])
def test_renders_lit_and_shadowed_sides_when_bond_is_cylindrical(view, dark, roll):
    # Arrange
    from PySide6.QtCore import QPointF
    from math import hypot

    MIN_LIGHTNESS_DIFFERENCE = 25
    view.dark = dark
    view.roll = roll
    view.bond_color = 'uniform'
    view.set_molecule(Molecule('rod', (Atom('C', -1, 0, 0), Atom('C', 1, 0, 0)), ((0, 1, 1),)))
    a, b = [point for point, z in view.projected()]
    dx, dy = b.x() - a.x(), b.y() - a.y()
    normal = QPointF(-dy, dx) / hypot(dx, dy)
    if normal.x() + normal.y() > 0:
        normal = -normal
    midpoint = (a + b) / 2
    width = view.camera()[1] * 0.08
    lit, shaded = midpoint + normal * width * 0.3, midpoint - normal * width * 0.3
    # Act
    image = view.grab().toImage()
    light = image.pixelColor(round(lit.x()), round(lit.y())).lightness()
    shadow = image.pixelColor(round(shaded.x()), round(shaded.y())).lightness()
    # Assert
    assert light - shadow >= MIN_LIGHTNESS_DIFFERENCE


def test_the_chosen_engine_is_kept_after_drawing(view):
    # a fallback to the built-in renderer would make the VTK runs above test the ray caster again
    engine = view.engine
    view.set_molecule(Molecule('water', (Atom('O', 0, 0, 0), Atom('H', 0.76, 0.59, 0), Atom('H', -0.76, 0.59, 0)), ((0, 1, 1), (0, 2, 1))))
    image = view.grab().toImage()
    assert view.engine == engine
    assert image.pixelColor(*[round(v) for v in (view.projected()[0][0].x(), view.projected()[0][0].y())]).isValid()

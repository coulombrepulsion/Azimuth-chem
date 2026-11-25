"""Editing with an atom or a fragment chosen: a press on the molecule and a drag show a bond to the new atom or
fragment, and the drag places it relative to the molecule without breaking that bond.

A press on an atom with an atom or a fragment chosen, then a drag: the new atom (fragment) is shown bonded to the
pressed atom on the side of the cursor while the button is held, and is put there on release; a press without a
drag is the click of before (the freest direction)."""

from math import dist

from PySide6.QtCore import QEvent, QPointF
from PySide6.QtGui import QMouseEvent

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_the_builder_puts_the_bond_where_it_is_aimed():
    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry.builder import place_atom, place_fragment
    from modules.compass.chemistry.editing import make_room

    carbon = Molecule('c', (Atom('C', 0, 0, 0),), ())
    one = place_atom(carbon, 'O', None, 0, 1, 1.4, direction=(0, 2, 0))  # any length: a direction only
    assert one.atoms[1].position == pytest.approx((0, 1.4, 0)) and (0, 1, 1) in one.bonds
    group = place_fragment(carbon, 'Метил · —CH₃', None, 0, 1, 1.5, direction=(0, 0, -1))
    assert group.atoms[1].position == pytest.approx((0, 0, -1.5))
    # without a direction — as before, the freest one
    assert place_atom(carbon, 'O', None, 0, 1, 1.4).atoms[1].position == pytest.approx((1.4, 0, 0))
    # a saturated atom gives up the hydrogen nearest to the aim
    methane = Molecule('m', (Atom('C', 0, 0, 0), Atom('H', 0.63, 0.63, 0.63), Atom('H', -0.63, -0.63, 0.63),
                             Atom('H', -0.63, 0.63, -0.63), Atom('H', 0.63, -0.63, -0.63)), None)
    room, index = make_room(methane, 0, 1, toward=(-0.6, 0.6, -0.6))
    assert index == 0 and len(room.atoms) == 4
    assert all(a.position != (-0.63, 0.63, -0.63) for a in room.atoms)  # the one that way is gone
    assert make_room(methane, 0, 1)[0].atoms[-1].position == (-0.63, 0.63, -0.63)  # without: the last one


def _drag(viewer, start, points):
    left, none = Qt.MouseButton.LeftButton, Qt.MouseButton.NoButton
    viewer.mousePressEvent(QMouseEvent(QEvent.Type.MouseButtonPress, QPointF(start), QPointF(start), left, left,
                                       Qt.KeyboardModifier.NoModifier))
    for point in points:
        viewer.mouseMoveEvent(QMouseEvent(QEvent.Type.MouseMove, QPointF(point), QPointF(point), none, left,
                                          Qt.KeyboardModifier.NoModifier))
    return lambda at: viewer.mouseReleaseEvent(QMouseEvent(QEvent.Type.MouseButtonRelease, QPointF(at), QPointF(at),
                                                           left, none, Qt.KeyboardModifier.NoModifier))


def test_a_drag_from_an_atom_aims_the_new_one(window, app):
    window.new_molecule()
    window.element.setCurrentText('C')
    show_model(window, app)
    tidy, hydrogens = window.tidy_live_action.isChecked(), window.hydrogens_live_action.isChecked()
    window.tidy_live_action.setChecked(False)
    window.hydrogens_live_action.setChecked(False)
    try:
        middle = QPoint(window.viewer.width() // 2, window.viewer.height() // 2)
        QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=middle)
        assert len(window.molecule.atoms) == 1
        window.bond_length.setValue(1.5)
        atom = window.viewer.projected()[0][0]
        right = QPointF(atom.x() + 120, atom.y())
        release = _drag(window.viewer, atom, [QPointF(atom.x() + 30, atom.y()), right])
        # while the button is held: shown, not yet made
        assert len(window.viewer.molecule.atoms) == 2 and len(window.molecule.atoms) == 1
        release(right)
        assert len(window.molecule.atoms) == 2
        a, b = window.molecule.atoms
        assert dist(a.position, b.position) == pytest.approx(1.5, abs=1e-6)  # bonded at its length
        p, q = (window.viewer.projected()[i][0] for i in range(2))
        assert q.x() - p.x() > 20 and abs(q.y() - p.y()) < 0.05 * (q.x() - p.x())  # on the side of the cursor
        # upwards from the second atom: the third goes up on the screen
        window.element.setCurrentText('O')
        start = window.viewer.projected()[1][0]
        up = QPointF(start.x(), start.y() - 100)
        _drag(window.viewer, start, [QPointF(start.x(), start.y() - 40), up])(up)
        assert [x.symbol for x in window.molecule.atoms] == ['C', 'C', 'O']
        p, q = (window.viewer.projected()[i][0] for i in (1, 2))
        assert p.y() - q.y() > 20 and abs(q.x() - p.x()) < 0.05 * (p.y() - q.y())
        # a press and a release without a drag: the click of before
        start = window.viewer.projected()[0][0]
        _drag(window.viewer, start, [])(start)
        assert len(window.molecule.atoms) == 4
        # a drag that comes back to the atom: nothing aimed — a click as well, not two atoms
        start = window.viewer.projected()[3][0]
        _drag(window.viewer, start, [QPointF(start.x() + 60, start.y()), QPointF(start.x() + 2, start.y() + 3)])(start)
        assert len(window.molecule.atoms) == 5
    finally:
        window.tidy_live_action.setChecked(tidy)
        window.hydrogens_live_action.setChecked(hydrogens)


def test_a_drag_from_a_hydrogen_puts_the_group_in_its_place(window, app):
    # methane, a hydrogen dragged from: it gives its place, the methyl is bonded to the carbon towards the cursor
    window.new_molecule()
    window.element.setCurrentText('C')
    show_model(window, app)
    hydrogens = window.hydrogens_live_action.isChecked()
    window.hydrogens_live_action.setChecked(True)
    try:
        QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton,
                         pos=QPoint(window.viewer.width() // 2, window.viewer.height() // 2))
        assert window.molecule.formula == 'CH4'
        window.model_menu_tool.choose_fragment('Метил · —CH₃')
        assert window.viewer.mode == 'fragment'
        h = next(i for i, a in enumerate(window.molecule.atoms) if a.symbol == 'H')
        start = window.viewer.projected()[h][0]
        carbon = window.viewer.projected()[0][0]
        away = QPointF(carbon.x() - 130, carbon.y() + 10)
        _drag(window.viewer, start, [QPointF(start.x() - 40, start.y()), away])(away)
        assert window.molecule.formula == 'C2H6'
    finally:
        window.hydrogens_live_action.setChecked(hydrogens)



def test_a_drag_ended_on_another_atom_bonds_to_it(window, app):
    window.new_molecule()
    window.element.setCurrentText('C')
    show_model(window, app)
    tidy, hydrogens = window.tidy_live_action.isChecked(), window.hydrogens_live_action.isChecked()
    window.tidy_live_action.setChecked(False)
    window.hydrogens_live_action.setChecked(False)
    try:
        middle = QPoint(window.viewer.width() // 2, window.viewer.height() // 2)
        QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=middle)
        QTest.mouseClick(window.viewer, Qt.MouseButton.LeftButton, pos=QPoint(middle.x() + 200, middle.y() + 40))
        assert len(window.molecule.atoms) == 2 and not tuple(window.molecule.bonds or ())
        window.bond_length.setValue(1.5)
        window.element.setCurrentText('O')
        first, second = (window.viewer.projected()[i][0] for i in range(2))
        halfway = QPointF((first.x() + second.x()) / 2, (first.y() + second.y()) / 2)
        release = _drag(window.viewer, first, [halfway, second])
        shown = window.viewer.molecule  # over the second atom: it is drawn as the one dragged, bonded
        assert [a.symbol for a in shown.atoms] == ['C', 'O'] and len(window.molecule.atoms) == 2
        release(second)
        assert [a.symbol for a in window.molecule.atoms] == ['C', 'O']
        a, b = window.molecule.atoms
        assert dist(a.position, b.position) == pytest.approx(1.5, abs=1e-6)  # brought to the bond length
        assert {frozenset((i, j)) for i, j, _ in window.molecule.bonds} == {frozenset((0, 1))}
    finally:
        window.tidy_live_action.setChecked(tidy)
        window.hydrogens_live_action.setChecked(hydrogens)

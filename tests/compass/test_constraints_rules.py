"""The rules of the constraints of optimization without Qt (modules/compass/constraints.py) and the tool
with a fake port (modules/compass/actions/constraint_actions.ConstraintTool — its menu needs Qt, the rest does not
touch the window). Oracle: the kinds of the constraints of ORCA's %geom (C, B, A, D) by the number of atoms."""

import pytest

from azimuth.core import read_xyz
from modules.compass import constraints as rules

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')


def test_kinds_find_toggle():
    items = rules.toggled([], [0, 1])
    assert items == [('B', (0, 1))] and rules.find(items, [1, 0]) == ('B', (0, 1))  # either direction
    items = rules.toggled(items, [0])
    assert items == [('B', (0, 1)), ('C', (0,))]
    assert rules.toggled(items, (1, 0)) == [('C', (0,))]  # the same bond, reversed: removed
    assert [rules.toggled([], range(n))[0][0] for n in (1, 2, 3, 4)] == ['C', 'B', 'A', 'D']
    for bad in ([], [0, 1, 2, 3, 4]):
        with pytest.raises(ValueError, match='от одного до четырёх'):
            rules.toggled([], bad)


def test_texts():
    assert rules.text(('B', (0, 1)), WATER) == 'Длина O1–H2'
    assert rules.toggle_title([], [0, 1, 2], WATER) == 'Закрепить угол O1–H2–H3'
    assert rules.toggle_title([('C', (0,))], [0], WATER) == 'Освободить атом O1'
    assert rules.toggle_title([], [], WATER) is None


def test_the_tool_touches_only_its_port():
    pytest.importorskip('PySide6')
    from modules.compass.actions.constraint_actions import ConstraintPort, ConstraintTool

    items, said, changed = [], [], []
    tool = ConstraintTool(ConstraintPort(items=lambda: items, selected=lambda: [1, 2], molecule=lambda: WATER,
                                         notify=lambda text, ms: said.append(text), changed=lambda: changed.append(1)))
    tool.toggle()
    assert items == [('B', (1, 2))] and changed == [1]
    tool.toggle([])
    assert said and changed == [1]  # refused: said, nothing changed
    tool.remove(('B', (1, 2)))
    assert items == [] and changed == [1, 1]

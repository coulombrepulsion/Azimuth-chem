"""The openers of the windows of the path, the rotation about a bond and the conformers through their port
(modules/compass/actions/dialog_openers.py) — the refusals and what is kept, with a fake port; the windows themselves
are opened in tests/gui. Oracle: the conditions of the openers (2 atoms for a path, 4 for conformers, 2 or 4 selected
atoms for a rotation), as."""

from types import SimpleNamespace

import pytest

pytest.importorskip('PySide6')

from modules.compass.actions.dialog_openers import DialogOpeners, DialogPort  # noqa: E402


def port(atoms=1, selected=(), browsing=False):
    said, kept, stopped = [], {}, []
    made = DialogPort(parent=None, molecule=lambda: SimpleNamespace(atoms=[0] * atoms), selected=lambda: list(selected),
                      browsing=lambda: browsing, stop_browsing=lambda: stopped.append(1),
                      notify=lambda text, ms: said.append(text), error=lambda exc: said.append(str(exc)),
                      keep=kept.__setitem__, kept=kept.get)
    return made, said, kept, stopped


def test_the_refusals_are_said_and_nothing_is_opened():
    made, said, kept, stopped = port(atoms=1, browsing=True)
    tools = DialogOpeners(made)
    assert tools.path() is None and 'два атома' in said[-1] and stopped == [1]  # the trajectory closed first
    assert tools.conformers() is None and 'четырёх атомов' in said[-1]
    assert tools.torsion() is None and 'связь' in said[-1]  # nothing selected
    assert kept == {}


def test_no_conformers_of_a_crystal():
    said, kept = [], {}
    made = DialogPort(parent=None, molecule=lambda: SimpleNamespace(atoms=[0] * 72), selected=list,
                      browsing=lambda: False, stop_browsing=lambda: None, notify=lambda text, ms: said.append(text),
                      error=lambda exc: said.append(str(exc)), keep=kept.__setitem__, kept=kept.get,
                      crystal=lambda: True)
    assert DialogOpeners(made).conformers() is None and 'не для кристалла' in said[-1] and kept == {}

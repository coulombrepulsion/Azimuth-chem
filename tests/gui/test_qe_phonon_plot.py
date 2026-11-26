"""The phonon branches and their density of states drawn (modules/compass/actions/qe_plots.py, axis «ν, см⁻¹»)."""

import json
from pathlib import Path

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'


def test_the_branches_of_rock_salt_are_drawn(app, tmp_path):
    from PySide6.QtWidgets import QWidget

    from modules.compass.actions import qe_window
    from modules.sextant import qe_inputs

    for name, target in (('nacl_dispersion.freq', qe_inputs.FREQ_FILE), ('nacl_dispersion.phdos', qe_inputs.PHDOS_FILE),
                         ('nacl_dispersion_path.json', 'path.json')):
        (tmp_path / target).write_bytes((DATA / name).read_bytes())

    class Owner(QWidget):  # what show_phonons asks of the panel: its folder and name
        folder, name = tmp_path, 'NaCl'

    owner = Owner()
    found = qe_window.QePanel.phonon_data(owner)
    window = qe_window.QePanel.show_phonons(owner, found)
    assert window.plot.axis == 'ν, см⁻¹' and not window.plot.zero_line
    assert window.plot.span[1] > 255 and window.rows[0][0] == 0.0 and len(window.header) == 7
    assert owner.phdos_window.plot.axis == 'ν, см⁻¹'
    assert not hasattr(owner, 'thermo_window') and owner.thermo_error  # this owner has no crystal: no table invented
    from modules.compass.chemistry import crystal as cr

    salt = cr.Crystal('NaCl', cr.Cell(3.988, 3.988, 3.988, 60, 60, 60), (cr.Site('Na1', 'Na', 0, 0, 0), cr.Site('Cl1', 'Cl', 0.5, 0.5, 0.5)),
                      (cr.operation('x, y, z'),), 'P 1')
    owner.computed = lambda: (salt, None)
    thermo = qe_window.QePanel.show_thermo(owner, found[2])
    assert thermo.plot.y_axis == 'C_V, Дж/(моль·К)' and len(thermo.plot.series) == 3 and len(thermo.rows) == 44
    assert '47.8' in thermo.note.text() and 'Температура Дебая: 274 K' in thermo.note.text()
    assert abs(thermo.rows[0][5] - 321) < 8 and thermo.rows[-1][0] == 1000.0
    for shown in (window, owner.phdos_window, thermo):
        shown.grab()  # painted without an error
        shown.close()
    path = json.loads((DATA / 'nacl_dispersion_path.json').read_text(encoding='utf-8'))
    assert [label for _, label in window.plot.ticks][:3] == [label for _, label in path['ticks']][:3]

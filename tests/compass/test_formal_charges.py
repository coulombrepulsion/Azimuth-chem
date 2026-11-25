"""Formal charges of molfiles and SDF databases.

Oracles: the CTfile format (BIOVIA, «CTfile Formats»): the charge column «ccc» of the V2000 atom block codes
1 = +3, 2 = +2, 3 = +1, 4 = doublet radical, 5 = −1, 6 = −2, 7 = −3; «M CHG» lines supersede it for the whole
record; V3000 writes «CHG=n» in the atom line. Chemistry: NO₃⁻ drawn as N⁺(=O)(O⁻)(O⁻) has charge −1 and no H; Cl⁻
is one atom with charge −1 (18 electrons, a singlet); the user's database (Cs_full.sdf) gave Cl as a neutral doublet
and chlorate HClO₃-like with three H on its O.
"""

import pytest

from modules.compass.chemistry import formats
from modules.compass.chemistry.editing import skeleton_hydrogens

NITRATE = """Nitrate ion
  test

  4  3  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
    1.2500    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -0.6250    1.0825    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -0.6250   -1.0825    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  2  0
  1  3  1  0
  1  4  1  0
M  CHG  3   1   1   3  -1   4  -1
M  END
> <Name>
Nitrate ion

$$$$
"""
CHLORIDE = """Chloride ion
  test

  1  0  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 Cl  0  5  0  0  0  0  0  0  0  0  0  0
M  END
$$$$
"""
ACETIC = """Acetic acid
  test

  4  3  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.5000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.1000    1.0400    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    2.1000   -1.0400    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  2  3  2  0
  2  4  1  0
M  END
$$$$
"""
V3000 = """ion
  test

  0  0  0     0  0            999 V3000
M  V30 BEGIN CTAB
M  V30 COUNTS 1 0 0 0 0
M  V30 BEGIN ATOM
M  V30 1 Br 0 0 0 0 CHG=-1
M  V30 END ATOM
M  V30 END CTAB
M  END
"""


def test_charges_of_the_records():
    assert formats.mol_charges(NITRATE) == [1, 0, -1, -1]
    assert formats.mol_charges(CHLORIDE) == [-1]  # the column «ccc» = 5
    assert formats.mol_charges(ACETIC) == [0, 0, 0, 0]
    assert formats.mol_charges(V3000) == [-1]
    assert formats.mol_charges('not a molfile') == []
    text = NITRATE + CHLORIDE + ACETIC
    assert formats.sdf_charges(text) == [[1, 0, -1, -1], [-1], [0, 0, 0, 0]]
    assert len(formats.read_sdf_records(text)) == 3


def test_no_hydrogens_on_the_charged_atoms():
    nitrate = formats.read_mol(NITRATE)
    filled, added = skeleton_hydrogens(nitrate, charged=(0, 2, 3))
    assert added == 0 and filled.formula == 'NO3'
    acetic, added = skeleton_hydrogens(formats.read_mol(ACETIC))
    assert added == 4 and acetic.formula == 'C2H4O2'  # a neutral skeleton as before


def test_a_database_with_ions_opened_as_a_set(tmp_path, monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication

    from azimuth.app import Studio

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    path = tmp_path / 'ions.sdf'
    path.write_text(NITRATE + CHLORIDE + ACETIC, encoding='utf-8')
    window = Studio(probe_machine=False)
    try:
        from PySide6.QtWidgets import QMessageBox

        # the hydrogens of a skeleton on opening (the default; another test of the run may have left it off)
        monkeypatch.setattr(window.opening_tool, 'hydrogens_on_open', lambda: True)
        # acetic acid of the file is a flat drawing — Quill offers 3D; «Не сейчас»
        monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.No)
        window.opening_tool.open_path(str(path))
        rows = window.batch_tool.structure_rows()  # the molecules of the project
        assert [m.formula for m, _ in rows] == ['NO3', 'Cl', 'C2H4O2']
        assert window.charge.value() == -1 and window.spin.value() == 1  # the first one: nitrate
        source, chosen = window.batch_tool.batch_source()
        assert [(c, s) for _, _, _, c, s in chosen] == [(-1, 1), (-1, 1), (0, 1)]
    finally:
        window.recovery.finish()
        window.dirty = False
        window.close()
        window.deleteLater()
        assert app is not None

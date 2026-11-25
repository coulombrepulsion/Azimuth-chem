"""Flat structures and their 3D coordinates by RDKit (modules/compass/chemistry/embed3d.py).

Oracles: the CTfile V2000 format (the record written must carry «M CHG» for N⁺ and O⁻, the bonds and every explicit
hydrogen); a fake «Python with RDKit» — a script that moves every atom out of the plane (z + 0.1 × its number) and
marks a record titled «bad» as failed — so the order of the atoms, the names and a failure kept unchanged are
checked without RDKit. RDKit itself is not needed here.
"""

import os
import stat
import sys
from pathlib import Path

import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import embed3d, formats

FAKE = r'''#!{python}
import sys
args = [a for a in sys.argv[1:] if a != '-I']
script, source, target = args[0], args[1], args[2]
open(source + '.seen', 'w').write(open(source).read())
out = []
blocks = [b for b in open(source).read().split('$$$$\n') if b.strip()]
for number, block in enumerate(blocks):
    print(number, len(blocks), flush=True)  # 0.99.1: the progress, as rdkit_embed.py prints it
    sys.stderr.write('RDKit WARNING: ' + 'x' * 70000 + '\n')  # more than a pipe holds: stderr goes to a file
    lines = block.split('\n')
    n = int(lines[3][0:3])
    if lines[0].strip() == 'bad':
        out.append(block.split('M  END')[0].rstrip('\n') + '\nM  END\n>  <Azimuth3D>\nfailed: ETKDG did not embed it\n\n')
        continue
    for k in range(4, 4 + n):
        line = lines[k]
        lines[k] = line[:20] + f'{float(line[20:30]) + 0.1 * (k - 3):10.4f}' + line[30:]
    out.append('\n'.join(lines).split('M  END')[0].rstrip('\n') + '\nM  END\n>  <Azimuth3D>\nok: MMFF94\n\n')
open(target, 'w').write('$$$$\n'.join(out) + '$$$$\n')
'''

NITRATE = Molecule('nitrate', (Atom('N', 0, 0, 0), Atom('O', 1.25, 0, 0), Atom('O', -0.62, 1.08, 0),
                               Atom('O', -0.62, -1.08, 0)), ((0, 1, 2), (0, 2, 1), (0, 3, 1)))
ETHANOL = Molecule('ethanol', (Atom('C', 0, 0, 0), Atom('C', 1.52, 0, 0), Atom('O', 2.1, 1.2, 0),
                               Atom('H', -0.4, 0.5, 0.9), Atom('H', -0.4, 0.5, -0.9), Atom('H', -0.4, -1.0, 0)),
                   ((0, 1, 1), (1, 2, 1), (0, 3, 1), (0, 4, 1), (0, 5, 1)))  # a 2D skeleton, its CH₃ hydrogens added


def fake_python(tmp_path):
    path = tmp_path / 'python'
    path.write_text(FAKE.replace('{python}', sys.executable), encoding='utf-8')
    path.chmod(path.stat().st_mode | stat.S_IXUSR)
    return path


def test_flat_or_not():
    # only a drawing that cannot be the real shape — NO₃⁻ is planar in reality (its N trigonal), ethanol is not
    assert not embed3d.is_flat(NITRATE)
    # the atoms of the file count, the shapes come from the structure with the hydrogens added: the 2D skeleton of
    # ethanol is flat; ethanol with its hydrogens out of the plane is a 3D file (anti-butane of the examples)
    skeleton = Molecule('ethanol', ETHANOL.atoms[:3], ETHANOL.bonds[:2])
    assert embed3d.is_flat(skeleton, ETHANOL) and not embed3d.is_flat(ETHANOL)
    butane = Path(__file__).resolve().parents[2] / 'examples' / '9-torsion' / 'butane.xyz'
    from azimuth.core import read_xyz

    assert not embed3d.is_flat(read_xyz(butane.read_text(encoding='utf-8')))
    water = Molecule('w', (Atom('O', 0, 0, 0), Atom('H', 0.96, 0, 0), Atom('H', -0.24, 0.93, 0)), ((0, 1, 1), (0, 2, 1)))
    assert not embed3d.is_flat(water)
    chlorate = Molecule('ClO3', (Atom('Cl', 0, 0, 0), Atom('O', 1.5, 0, 0), Atom('O', -0.75, 1.3, 0),
                                 Atom('O', -0.75, -1.3, 0)), ((0, 1, 2), (0, 2, 2), (0, 3, 1)))
    assert embed3d.is_flat(chlorate)  # a lone pair on Cl: pyramidal
    raised = Molecule('x', (Atom('C', 0, 0, 0), Atom('C', 1.5, 0, 0), Atom('O', 2, 1, 0.8)), None)
    assert not embed3d.is_flat(raised)
    line = Molecule('co2', (Atom('O', -1.16, 0, 0), Atom('C', 0, 0, 0), Atom('O', 1.16, 0, 0)), None)
    assert not embed3d.is_flat(line) and not embed3d.is_flat(Molecule('cl', (Atom('Cl', 0, 0, 0),), None))
    assert embed3d.flat_count([NITRATE, raised, chlorate]) == 1


def test_the_record_carries_charges_bonds_and_hydrogens():
    text = embed3d.sdf_of([NITRATE, ETHANOL], [[1, 0, -1, -1], ()])
    assert text.count('$$$$') == 2 and 'M  CHG  3   1   1   3  -1   4  -1' in text
    assert formats.sdf_charges(text) == [[1, 0, -1, -1], [0] * 6]
    back = formats.read_sdf_records(text)
    assert [len(m.atoms) for m in back] == [4, 6] and sorted(back[0].bonds) == sorted(NITRATE.bonds)
    aromatic = Molecule('a', (Atom('C', 0, 0, 0), Atom('C', 1.4, 0, 0)), ((0, 1, 1.5),))
    assert '  1  2  4  0' in embed3d.sdf_of([aromatic])


@pytest.mark.skipif(os.name == 'nt', reason='the fake Python is a POSIX script')
def test_run_keeps_order_names_and_failures(tmp_path):
    python = fake_python(tmp_path)
    bad = Molecule('bad', ETHANOL.atoms, ETHANOL.bonds)
    steps = []
    made = embed3d.run(python, [NITRATE, bad, ETHANOL], [[1, 0, -1, -1], (), ()], step=lambda k, n: steps.append((k, n)))
    assert [ok for _, ok, _ in made] == [True, False, True]
    assert steps == [(0, 3), (1, 3), (2, 3), (3, 3)]
    with pytest.raises(InterruptedError):  # Esc: RDKit is stopped
        embed3d.run(python, [NITRATE, ETHANOL], step=lambda k, n: False)
    nitrate, ok, note = made[0]
    assert note == 'MMFF94' and [a.symbol for a in nitrate.atoms] == ['N', 'O', 'O', 'O']
    assert [round(a.z, 4) for a in nitrate.atoms] == [0.1, 0.2, 0.3, 0.4] and nitrate.bonds == NITRATE.bonds
    assert nitrate.title == 'nitrate' and not embed3d.is_flat(nitrate)
    assert made[1][0] is bad and 'ETKDG' in made[1][2]  # kept as it came, with the reason
    assert [round(a.x, 2) for a in made[2][0].atoms] == [round(a.x, 2) for a in ETHANOL.atoms]


def test_the_python_with_rdkit(tmp_path):
    with_rdkit = tmp_path / 'with' / 'bin' / 'python'
    without = tmp_path / 'without' / 'bin' / 'python'
    for path, code in ((with_rdkit, 0), (without, 1)):
        path.parent.mkdir(parents=True)
        path.write_text(f'#!/bin/sh\nexit {code}\n', encoding='utf-8')
        path.chmod(0o755)

    class Settings(dict):
        def value(self, key, default=None):
            return self.get(key, default)

        def setValue(self, key, value):
            self[key] = value

    if os.name == 'nt':
        pytest.skip('POSIX scripts')
    settings = Settings()
    if embed3d.has_rdkit(sys.executable):
        pytest.skip('this Python has RDKit itself')
    assert embed3d.find_python(settings, [without, with_rdkit]) == with_rdkit
    assert settings[embed3d.KEY] == str(with_rdkit)
    assert embed3d.find_python(Settings(), [without]) is None
    home = tmp_path / 'home'
    (home / 'miniconda3' / 'bin').mkdir(parents=True)
    (home / 'miniconda3' / 'envs' / 'chem' / 'bin').mkdir(parents=True)
    for p in (home / 'miniconda3' / 'bin' / 'python3', home / 'miniconda3' / 'envs' / 'chem' / 'bin' / 'python'):
        p.write_text('#!/bin/sh\n', encoding='utf-8')
    found = embed3d.candidates(home)
    assert found[:2] == [home / 'miniconda3' / 'bin' / 'python3', home / 'miniconda3' / 'envs' / 'chem' / 'bin' / 'python']


@pytest.mark.skipif(os.name == 'nt', reason='the fake Python is a POSIX script')
def test_a_flat_database_made_3d_in_compass(tmp_path, monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication

    from azimuth.app import Studio
    from tests.compass.test_formal_charges import ACETIC, CHLORIDE, NITRATE as NITRATE_SDF

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    path = tmp_path / 'flat.sdf'
    path.write_text(NITRATE_SDF + CHLORIDE + ACETIC, encoding='utf-8')
    window = Studio(probe_machine=False)
    try:
        from PySide6.QtWidgets import QMessageBox

        # the hydrogens of a skeleton on opening (the default; another test of the run may have left it off)
        monkeypatch.setattr(window.opening_tool, 'hydrogens_on_open', lambda: True)
        asked = []
        python = fake_python(tmp_path)
        monkeypatch.setattr(embed3d, 'find_python', lambda settings=None, candidates_=None: python)
        # Quill asks right after opening; «Сделать объёмными» runs make_3d
        monkeypatch.setattr(QMessageBox, 'question', lambda parent, title, text, *a: asked.append((title, text))
                            or QMessageBox.StandardButton.Yes)
        window.opening_tool.open_path(str(path))
        assert asked and asked[0][0] == 'Плоская структура' and '1 из 3' in asked[0][1]  # acetic acid only
        rows = window.batch_tool.structure_rows()  # the molecules of the project
        assert [name for _, name in rows] == ['Nitrate ion', 'Chloride ion', 'Acetic acid']
        assert rows[2][0].atoms[0].z != rows[2][0].atoms[1].z  # made 3D by the fake RDKit
        assert not window.document().structure_flat  # nothing flat left
        assert rows[0][0].formula == 'NO3' and rows[1][0].formula == 'Cl'
        _, chosen = window.batch_tool.batch_source()  # the charges for a queue follow the new structures
        assert [(c, s) for _, _, _, c, s in chosen] == [(-1, 1), (-1, 1), (0, 1)]
        seen = (python.parent / 'python').exists()
        assert seen
    finally:
        window.recovery.finish()
        window.dirty = False
        window.close()
        window.deleteLater()
        assert app is not None

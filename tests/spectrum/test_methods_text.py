"""«Методика расчёта» (modules/spectrum/analysis/methods_text.py).

Oracles: the input files themselves, read by eye — the real outputs of ORCA 6.0.1 (tests/data/orca601: water in CPCM,
B3LYP/def2-SVP TightSCF; ethanol NMR with D3BJ) and the real inputs and outputs of pw.x 7.6 (tests/data/qe: NiO with
U = 6 eV, 50/400 Ry, k 6 × 11 × 11, two species of Ni; the vc-relax of silicon, 30/120 Ry, k 9 × 9 × 9).
"""

import zipfile
from pathlib import Path

import pytest

from modules.spectrum.analysis import methods_text as mt

DATA = Path(__file__).resolve().parents[1] / 'data'


def read(*parts):
    return DATA.joinpath(*parts).read_text(encoding='utf-8', errors='replace')


def test_a_molecule_of_orca():
    water = mt.orca(read('orca601', 'h2o_cpcm_water.out'))
    assert (water.program, water.version) == ('ORCA', '6.0.1')
    assert (water.get('method'), water.get('basis'), water.get('solvent')) == ('B3LYP', 'def2-SVP', 'CPCM(Water)')
    assert (water.get('charge'), water.get('multiplicity'), water.get('threshold')) == ('0', '1', 'TightSCF')
    assert water.get('task') == 'энергия' and water.other == () and water.get('dispersion') == ''
    text = mt.paragraph(water)
    assert text.startswith('Расчёты выполнены в программе ORCA 6.0.1. Уровень теории: B3LYP/def2-SVP.')
    assert 'моделью CPCM(Water)' in text and 'Заряд 0, мультиплетность 1' in text and text.endswith('Входные файлы приложены.')
    nmr = mt.orca(read('orca601', 'nmr_conformers', 'ethanol_a.out'))
    assert nmr.get('dispersion') == 'D3BJ' and nmr.get('task') == 'экранирование ЯМР (GIAO)'
    assert 'Уровень теории: B3LYP D3BJ/def2-SVP.' in mt.paragraph(nmr)
    both = mt.orca(read('orca601', 'h2o_optfreq.out'))
    assert both.get('task') == 'оптимизация геометрии, колебательные частоты'
    # a word the tables do not know is not dropped and not explained: it is listed
    made = ('INPUT FILE\n=====\n|  1> ! PBE0 D4 def2-TZVP def2/J RIJCOSX Opt TightOpt DefGrid3 MyOwnWord\n|  2> * xyz -1 2\n'
            '|  3> O 0 0 0\n|  4> *\n\n****END OF INPUT****\n')
    found = mt.orca(made)
    assert (found.get('method'), found.get('dispersion'), found.get('basis')) == ('PBE0', 'D4', 'def2-TZVP')
    assert (found.get('auxiliary'), found.get('approximation'), found.get('grid')) == ('def2/J', 'RIJCOSX', 'DefGrid3')
    assert (found.get('charge'), found.get('multiplicity')) == ('-1', '2') and found.other == ('MyOwnWord',) and found.version == ''
    assert 'Прочие ключевые слова входного файла: MyOwnWord.' in mt.paragraph(found)
    with pytest.raises(ValueError, match='INPUT FILE'):
        mt.orca('no echo here')


def test_a_crystal_of_quantum_espresso():
    nickel = mt.quantum_espresso(read('qe', 'nio_hubbard_hub4.in'), read('qe', 'nio_hubbard_pw76.out'))
    assert (nickel.program, nickel.version, nickel.get('functional')) == ('Quantum ESPRESSO', '7.6', 'PBE')
    assert nickel.get('pseudopotentials') == 'ni_pbe_v1.4.uspp.F.UPF, O.pbe-n-kjpaw_psl.0.1.UPF'  # one file for Ni1 and Ni2
    assert (nickel.get('ecutwfc'), nickel.get('ecutrho'), nickel.get('kpoints')) == ('50', '400', '6 × 11 × 11')
    assert nickel.get('hubbard') == 'U Ni1-3d 6; U Ni2-3d 6' and nickel.get('spin') and nickel.get('smearing') == ''
    text = mt.paragraph(nickel)
    assert 'Quantum ESPRESSO 7.6' in text and 'Поправка Хаббарда (DFT+U): U Ni1-3d 6; U Ni2-3d 6.' in text
    assert 'Сетка k-точек Монкхорста — Пака 6 × 11 × 11.' in text and 'conv_thr = 4.0e-08 Ry' in text
    silicon = mt.quantum_espresso(read('qe', 'si2_vcrelax.in'), read('qe', 'si2_vcrelax_pw76.out'))
    assert silicon.get('task') == 'оптимизация атомов и ячейки (vc-relax)' and silicon.get('kpoints') == '9 × 9 × 9'
    metal = mt.quantum_espresso(read('qe', 'nio_magnetic_mag2.in'))
    assert metal.version == '' and metal.get('smearing').endswith('Ry') and metal.get('functional') == ''
    with pytest.raises(ValueError, match='ATOMIC_SPECIES'):
        mt.quantum_espresso('&CONTROL\n/')


def test_the_archive_of_the_inputs(tmp_path):
    folder = tmp_path / 'qe-NiO'
    (folder / 'pseudo').mkdir(parents=True)
    (folder / 'out' / 'azimuth.save').mkdir(parents=True)
    (folder / 'hub4.in').write_text(read('qe', 'nio_hubbard_hub4.in'), encoding='utf-8')
    (folder / 'pw.out').write_text(read('qe', 'nio_hubbard_pw76.out'), encoding='utf-8')
    (folder / 'pseudo' / 'O.UPF').write_text('<UPF/>', encoding='utf-8')
    (folder / 'out' / 'azimuth.save' / 'O.UPF').write_text('copy of pw.x', encoding='utf-8')
    (folder / 'path.json').write_text('{}', encoding='utf-8')
    (folder / 'run.bat').write_text('@echo off', encoding='utf-8')
    found = mt.of_folder(folder)
    assert found.program == 'Quantum ESPRESSO' and found.version == '7.6'
    assert [p.relative_to(folder).as_posix() for p in mt.inputs_of(folder)] == ['hub4.in', 'path.json', 'pseudo/O.UPF', 'run.bat']
    names = mt.archive(folder, tmp_path / 'inputs.zip', mt.paragraph(found))
    assert names == ['hub4.in', 'path.json', 'pseudo/O.UPF', 'run.bat', 'METHODS.txt']
    with zipfile.ZipFile(tmp_path / 'inputs.zip') as bundle:
        assert sorted(bundle.namelist()) == sorted(names)  # no pw.out, nothing of out/
        assert 'Quantum ESPRESSO 7.6' in bundle.read('METHODS.txt').decode('utf-8')
    orca = tmp_path / 'orca'
    orca.mkdir()
    (orca / 'water.out').write_text(read('orca601', 'h2o_cpcm_water.out'), encoding='utf-8')
    assert mt.of_folder(orca).program == 'ORCA' and mt.of_folder(tmp_path / 'none') is None
    with pytest.raises(ValueError, match='нет входных файлов'):
        mt.archive(orca, tmp_path / 'x.zip')
    empty = tmp_path / 'empty'
    empty.mkdir()
    assert mt.of_folder(empty) is None

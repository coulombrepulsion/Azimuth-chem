"""Compass opens structure files as other programs write them, and a damaged file gives a message that says
the format and the line (modules/compass/chemistry/formats.py, azimuth/core.read_xyz)."""

import pytest

from azimuth.core import read_xyz, xyz_symbol
from modules.compass.chemistry import formats as F

WATER = 'O 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0'


@pytest.mark.parametrize('body', [
    'o 0 0 0\nh 0.96 0 0\nH -0.24 0.93 0',  # lower case
    '8 0 0 0\n1 0.96 0 0\n1 -0.24 0.93 0',  # atomic numbers
    'O1 0 0 0\nH2 0.96 0 0\nH3 -0.24 0.93 0',  # labels
    'O 0 0 0 -0.8\nH 0.96 0 0 0.4\nH -0.24 0.93 0 0.4',  # extended XYZ: a charge column
    'O 0.0D+00 0 0\nH 0.96 0 0\nH -0.24 0.93 0',  # Fortran exponent
    'O\t0\t0\t0\nH\t0.96\t0\t0\nH\t-0.24\t0.93\t0',  # tabs
])
def test_xyz_variants(body):
    m = read_xyz(f'3\nвода\n{body}\n')
    assert [a.symbol for a in m.atoms] == ['O', 'H', 'H']
    assert m.atoms[1].position == pytest.approx((0.96, 0, 0))


def test_xyz_symbols():
    assert [xyz_symbol(t) for t in ('C', 'c', 'CL', 'Cl3', 'C12', '6', 'HG', 'Du', '0')] == \
        ['C', 'C', 'Cl', 'Cl', 'C', 'C', 'Hg', None, None]


def test_xyz_cut_file_is_said():
    with pytest.raises(ValueError, match='обрезан'):
        read_xyz('3\nw\nO 0 0 0\nH 0.96 0 0\n')


def test_xyz_frames_keep_the_frames_before_a_broken_one():
    frame = f'3\nE=-76.1\n{WATER}\n'
    assert len(F.read_xyz_frames(frame * 3 + '3\nE\nO 0 0')) == 3
    with pytest.raises(ValueError, match='кадр 1'):
        F.read_xyz_frames('hello\nworld\n')


def test_cp1251_text(tmp_path):
    path = tmp_path / 'w.xyz'
    path.write_bytes(f'3\nвода\n{WATER}\n'.encode('cp1251'))
    assert read_xyz(F.read_text(path)).title == 'вода'
    path.write_bytes(('﻿' + f'3\nвода\n{WATER}\n').encode('utf-8'))
    assert read_xyz(F.read_text(path)).title == 'вода'


PDB = """HEADER    TEST
ATOM      1  N   ALA A   1      11.104   6.134  -6.504  1.00  0.00           N
ATOM      2  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00           C
ATOM      3  CB AALA A   1      11.118   4.850  -4.390  0.50  0.00           C
ATOM      4  CB BALA A   1      11.200   4.900  -4.300  0.50  0.00           C
HETATM    5 CA    CA A 101      20.000  20.000  20.000  1.00  0.00          CA
END
"""


def test_pdb_alternative_positions_and_hetatm():
    m = F.read_pdb(PDB)
    assert [a.symbol for a in m.atoms] == ['N', 'C', 'C', 'Ca']  # B of CB dropped; the calcium ion kept
    assert m.atoms[2].position == pytest.approx((11.118, 4.850, -4.390))


def test_pdb_element_from_the_atom_name():
    rows = [
        'ATOM      1  CA  ALA A   1      11.639   6.071  -5.147  1.00  0.00',  # C-alpha, not calcium
        'ATOM      2 HB12 ALA A   1      10.100   4.900  -4.300  1.00  0.00',  # a hydrogen, not mercury
        'HETATM    3 CL    CL A 101      20.000  20.000  20.000  1.00  0.00',  # chloride
        'HETATM    4 FE   HEM A 102      25.000  20.000  20.000  1.00  0.00',  # iron
    ]
    assert [a.symbol for a in F.read_pdb('\n'.join(rows)).atoms] == ['C', 'H', 'Cl', 'Fe']


MOL2 = """@<TRIPOS>MOLECULE
water
3 2 0 0 0
SMALL
NO_CHARGES

@<TRIPOS>ATOM
1 O1 0.0 0.0 0.0 O.3 1 HOH 0.0
2 H1 0.96 0.0 0.0 H 1 HOH 0.0
3 H2 -0.24 0.93 0.0 H 1 HOH 0.0
4 X1 0.0 0.0 1.5 Du 1 HOH 0.0
5 LP1 0.0 0.3 0.3 LP 1 HOH 0.0
@<TRIPOS>BOND
1 1 2 1
2 1 3 1
3 1 4 nc
@<TRIPOS>MOLECULE
second
1 0 0 0 0
SMALL
NO_CHARGES

@<TRIPOS>ATOM
1 C1 5.0 5.0 5.0 C.3 1 MET 0.0
"""


def test_mol2_first_molecule_dummy_and_lone_pair():
    m = F.read_mol2(MOL2)
    assert m.title == 'water' and [a.symbol for a in m.atoms] == ['O', 'H', 'H', 'X']
    assert sorted((i, j) for i, j, _ in m.bonds) == [(0, 1), (0, 2)]  # «nc» is not a bond


@pytest.mark.parametrize('reader, text, words', [
    (F.read_pdb, 'ATOM      1  N   ALA A   1      11.104\n', 'PDB, строка 1'),
    (F.read_mol2, '@<TRIPOS>ATOM\n1 O1 0.0 x 0.0 O.3\n', 'MOL2, атом 1'),
    (F.read_mol, 'x\n\n\n  3  2  0  0  0  0  0  0  0  0999 V2000\n 0 0 0 O\n 1 0 0 H\n 0 1 0 H\n 1 2x 1\n 1 3 1\n',
     'Молфайл'),
])
def test_damaged_files_say_format_and_place(reader, text, words):
    with pytest.raises(ValueError, match=words):
        reader(text)


def test_cut_and_spoiled_files_give_only_value_errors():
    import random

    from modules.compass.chemistry.builder import connections
    from modules.compass.chemistry import library

    rnd = random.Random(3)
    for key in list(library.keys())[:6]:
        m = library.molecule(key)
        b = list(connections(m))
        for text, reader in ((F.write_mol(m, b), F.read_mol), (F.write_mol_v3000(m, b), F.read_mol),
                             (F.write_mol2(m, b), F.read_mol2), (F.write_pdb(m, b), F.read_pdb),
                             (m.xyz() * 2, F.read_xyz_frames)):
            for _ in range(60):
                t = list(text)
                if rnd.random() < 0.4:
                    t = t[: rnd.randrange(len(t))]
                else:
                    for _ in range(rnd.randint(1, 5)):
                        t[rnd.randrange(len(t))] = rnd.choice('x \n9.-\t#@$>')
                try:
                    reader(''.join(t))
                except ValueError as exc:
                    assert not str(exc).startswith(('invalid literal', 'could not convert', 'not enough values'))

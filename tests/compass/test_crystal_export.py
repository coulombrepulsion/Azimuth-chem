"""crystal_export: POSCAR, the extended XYZ and the block in P 1 of the crystals of the examples."""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_export as ce

EXAMPLES = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def nacl():
    return cr.parse_cif((EXAMPLES / 'NaCl_rock_salt.cif').read_text(encoding='utf-8'))


def test_poscar_of_rock_salt():
    lines = ce.poscar(nacl()).splitlines()
    assert lines[1] == '1.0' and [float(x) for x in lines[2].split()] == pytest.approx([5.64, 0, 0])
    assert lines[5].split() == ['Na', 'Cl'] and lines[6].split() == ['4', '4'] and lines[7] == 'Direct'
    fractions = [tuple(float(x) for x in line.split()[:3]) for line in lines[8:16]]
    assert fractions[0] == (0, 0, 0) and (0.5, 0.5, 0.5) in fractions[4:]
    assert all(0 <= x < 1 for f in fractions for x in f)


def test_extended_xyz_of_cscl():
    crystal = cr.parse_cif((EXAMPLES / 'CsCl.cif').read_text(encoding='utf-8'))
    lines = ce.extended_xyz(crystal).splitlines()
    a = crystal.cell.a
    assert lines[0] == '2' and 'pbc="T T T"' in lines[1] and f'{a:.10f}' in lines[1]
    cs, cl = lines[2].split(), lines[3].split()
    assert cs[0] == 'Cs' and cl[0] == 'Cl' and [float(x) for x in cl[1:]] == pytest.approx([a / 2] * 3)


@pytest.mark.parametrize('n, atoms', [((1, 1, 1), 8), ((2, 1, 1), 16), ((2, 2, 2), 64)])
def test_the_block_in_p1_is_read_back(n, atoms):
    back = cr.parse_cif(ce.block_cif(nacl(), n))
    assert back.space_group == 'P 1' and len(back.operations) == 1
    assert len(cr.unit_cell(back)) == atoms and back.cell.a == pytest.approx(5.64 * n[0])

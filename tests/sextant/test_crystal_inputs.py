"""crystal_inputs: the .d12 of CRYSTAL for crystals of Compass; the structure read back is the crystal written."""

from pathlib import Path

import pytest

from azimuth.core import SYMBOLS
from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import space_groups
from modules.sextant import crystal_inputs as ci
from modules.spectrum.readers import crystal_out as co

ROOT = Path(__file__).resolve().parents[2]


def example(name):
    return cr.parse_cif((ROOT / 'examples' / '10-crystals' / name).read_text(encoding='utf-8'))


def rebuilt(number, parameters, atoms):
    """The crystal CRYSTAL builds of block 1 (its setting of the number, the minimal parameters)."""
    entry = space_groups.find(number=number)
    p = parameters
    if number >= 195:
        cell = cr.Cell(p[0], p[0], p[0])
    elif number >= 143:
        cell = cr.Cell(p[0], p[0], p[1], 90, 90, 120)
    elif number >= 75:
        cell = cr.Cell(p[0], p[0], p[1])
    elif number >= 16:
        cell = cr.Cell(*p)
    elif number >= 3:
        cell = cr.Cell(p[0], p[1], p[2], 90, p[3], 90)
    else:
        cell = cr.Cell(*p)
    sites = tuple(cr.Site(f'{SYMBOLS[z - 1]}{k}', SYMBOLS[z - 1], x, y, w) for k, (z, x, y, w) in enumerate(atoms))
    return cr.Crystal('', cell, sites, tuple(cr.operation(o) for o in space_groups.operations(entry)), number=number)


def test_rock_salt_by_its_group():
    text = ci.crystal_input(example('NaCl_rock_salt.cif'), 'Энергия')
    lines = text.splitlines()
    assert lines[1:6] == ['CRYSTAL', '0 0 0', '225', '5.64000000', '2']
    assert lines[6].split()[0] == '11' and lines[7].split()[0] == '17'
    assert lines[8:10] == ['BASISSET', 'POB-TZVP'] and 'OPTGEOM' not in text
    assert text.endswith('FMIXING\n30\nEND\n') and 'DFT\nPBE0-D3\nEND' in text and 'SHRINK\n8 16' in text


def test_another_setting_is_written_in_that_of_the_number():
    # benzoic acid of the file is P 21/n; CRYSTAL takes № 14 as P 21/c — the cell is turned to it, the atoms kept
    crystal = example('benzoic_acid.cif')
    number, parameters, atoms = ci.geometry(crystal)
    assert number == 14 and len(parameters) == 4 and len(atoms) == len(crystal.sites)
    back = rebuilt(number, parameters, atoms)
    assert len(cr.unit_cell(back)) == len(cr.unit_cell(crystal))
    assert back.cell.volume() == pytest.approx(crystal.cell.volume(), rel=1e-6)


def test_the_owners_chlorine_back_into_an_input():
    # the last structure of a CRYSTAL run (C m c e) written as an input: a, b, c and the asymmetric unit
    result = co.read((ROOT / 'tests' / 'data' / 'crystal' / 'chlorine-10gpa.out').read_text(encoding='utf-8'))
    crystal = co.final_crystal(result, 'Cl2')
    number, parameters, atoms = ci.geometry(crystal)
    assert number == 64 and len(parameters) == 3 and len(atoms) == 1 and atoms[0][0] == 17
    assert len(cr.unit_cell(rebuilt(number, parameters, atoms))) == 8


def test_the_tasks_and_the_pressure():
    crystal = example('NaCl_rock_salt.cif')
    text = ci.crystal_input(crystal, 'Оптимизация с ячейкой', ci.Options(pressure=0.65))
    block = text.split('OPTGEOM\n')[1].split('END\n')[0]
    assert block.startswith('FULLOPTG\nEXTPRESS\n') and float(block.split()[2]) == pytest.approx(0.65 / 29421.0265)
    assert 'ATOMONLY' in ci.crystal_input(crystal, 'Оптимизация атомов')
    elastic = ci.crystal_input(crystal, 'Упругие константы')
    assert 'ELASTCON\nEND\nBASISSET' in elastic and 'TOLDEE\n10' in elastic
    assert 'FREQCALC\nINTENS\nEND' in ci.crystal_input(crystal, 'Частоты (точка Γ)')
    assert 'DFT' not in ci.crystal_input(crystal, 'Энергия', ci.Options(functional='HF'))
    with pytest.raises(ValueError):
        ci.crystal_input(crystal, 'Энергия', ci.Options(pressure=1.0))
    caesium = example('CsCl.cif')
    with pytest.raises(ValueError, match='Cs'):  # Cs is beyond Br: no pob basis set
        ci.crystal_input(caesium, 'Энергия', ci.Options(basis='POB-DZVP'))
    assert 'STO-3G' in ci.crystal_input(caesium, 'Энергия', ci.Options(basis='STO-3G'))


def test_a_crystal_without_a_known_setting_is_the_whole_cell_in_p1():
    crystal = example('graphite_P1.cif')
    number, parameters, atoms = ci.geometry(crystal)
    assert number == 1 and len(parameters) == 6 and len(atoms) == len(cr.unit_cell(crystal))
    assert ci.topond_input().startswith('TOPO\nTRHO\n')


def test_the_keywords_are_those_of_the_manual_of_crystal23():
    # the GGA functionals are PBEXC and PBESOLXC (PBE alone
    # is no keyword of the DFT block), «-D3» only after a name of the D3 list (no PBEsol), the labels of BASISSET of
    # CRYSTAL23 (no MINIX: it belongs to HF-3c)
    assert {'PBEXC', 'PBESOLXC', 'PBE-D3', 'PBE0-D3', 'B3LYP-D3', 'HSE06-D3'} <= set(ci.FUNCTIONALS)
    assert 'PBE' not in ci.FUNCTIONALS and 'PBESOL' not in ci.FUNCTIONALS and 'PBESOL-D3' not in ci.FUNCTIONALS
    assert set(ci.BASES) <= {'STO-3G', 'STO-6G', 'POB-DZVP', 'POB-DZVPP', 'POB-TZVP', 'POB-DZVP-REV2', 'POB-TZVP-REV2'}
    text = ci.crystal_input(example('NaCl_rock_salt.cif'), 'Энергия', ci.Options(functional='PBESOLXC',
                                                                                basis='POB-TZVP-REV2'))
    assert 'BASISSET\nPOB-TZVP-REV2\nDFT\nPBESOLXC\nEND\n' in text

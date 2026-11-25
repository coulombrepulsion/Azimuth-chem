"""The NMR reference «TMS at the level of the result» (modules/spectrum/analysis/nmr_reference)."""

from pathlib import Path

import pytest

from modules.spectrum.analysis import nmr_reference as n
from modules.spectrum.readers.orca_spectra import Shielding
from modules.spectrum.analysis.reaction import level_of_theory

DATA = Path(__file__).parents[1] / 'data' / 'orca601'


def read(name):
    return (DATA / f'{name}.out').read_text(encoding='utf-8')


def echo(text):
    """An ORCA output that only has the echo of the input `text` (as level_of_theory reads it)."""
    lines = text.split('\n')
    rows = '\n'.join(f'| {k:2d}> {line}' for k, line in enumerate(lines, 1))
    return f'INPUT FILE\n{"=" * 80}\nNAME = tms.inp\n{rows}\n|{len(lines) + 1:3d}>                ****END OF INPUT****\n'


def test_tms_geometry():
    from math import dist

    from modules.compass.chemistry.symmetry import analyze

    m = n.tms_molecule()
    assert analyze(m)['name'] == 'Td' and n.is_tms(m) and m.formula.replace(' ', '') in ('C4H12Si', 'SiC4H12')
    si, carbons = m.atoms[0], m.atoms[1:5]
    assert all(dist(si.position, c.position) == pytest.approx(n.TMS_SI_C) for c in carbons)
    assert not n.is_tms(None)


def test_orca_input_from_the_result():
    from modules.compass.chemistry.formats import read_orca_input

    out = read('h2o_nmr')  # ! B3LYP def2-SVP NMR TightSCF
    kind, text = n.tms_input(out)
    assert kind == 'orca' and text.startswith('# TMS')
    assert '! B3LYP def2-SVP NMR TightSCF' in text and '%maxcore 500' in text and 'H2O' not in text
    molecule, charge, multiplicity = read_orca_input(text)
    assert (charge, multiplicity) == (0, 1) and n.is_tms(molecule)
    assert level_of_theory(echo(text)) == level_of_theory(out) == 'B3LYP DEF2-SVP'


def test_orca_input_keeps_the_level_and_drops_the_jobs_of_the_molecule():
    _, text = n.tms_input(read('h2o_optfreq'))  # Opt Freq, no NMR
    first = next(line for line in text.split('\n') if line.startswith('!')).upper().split()
    assert 'OPT' in first and 'FREQ' not in first and 'NMR' in first
    _, text = n.tms_input(read('h2o_cpcm_water'))
    assert 'CPCM(Water)' in text and level_of_theory(echo(text)) == level_of_theory(read('h2o_cpcm_water'))
    with pytest.raises(ValueError, match='ограничения'):
        n.tms_input(read('h2o_opt_frozen_oh'))  # %geom Constraints refer to the atoms of water
    with pytest.raises(ValueError):
        n.tms_input('no input here')


def test_gaussian_input_from_the_route():
    out = (' Entering Gaussian System, Link 0=g16\n %nprocshared=4\n %mem=4GB\n %chk=water.chk\n'
           ' ----------------------------------------\n #p opt=(ts,calcfc) freq b3lyp/6-311+g(2d,p) scrf=(smd,solv\n'
           ' ent=chloroform) guess=read\n ----------------------------------------\n')
    kind, text = n.tms_input(out, 'Gaussian')
    assert kind == 'gaussian'
    lines = text.split('\n')
    assert lines[:3] == ['%nprocshared=4', '%mem=4GB', '%chk=TMS.chk']
    assert lines[3] == '#p Opt b3lyp/6-311+g(2d,p) scrf=(smd,solvent=chloroform) NMR'
    assert lines[7] == '0 1' and len([l for l in lines[8:] if l.strip()]) == 17


def test_averaged_and_key():
    found = n.averaged([Shielding(0, 'Si', 330.0, None), Shielding(1, 'C', 184.0, None), Shielding(2, 'C', 186.0, None)])
    assert found == {'Si': 330.0, 'C': 185.0}
    assert n.key('B3LYP/6-31G(D)') == 'B3LYP|6-31G(D)'

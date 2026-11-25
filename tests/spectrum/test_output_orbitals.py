"""Orbitals printed in GAMESS, NWChem and Q-Chem outputs (modules/spectrum/readers/output_orbitals.py).

Oracles, independent of the reader: the orthonormality of the orbitals in the overlap of the basis (C^T S C = 1
within the rounding of the printed coefficients, checked by orbitals.select); the Mulliken charges each program
prints itself (from its own density and overlap) against those from the orbitals read here (to 5e-5 with 5–6
printed decimals); the numbers of electrons of the input (dvb: 70; its cation: 69; MoOCl4 with ECPs on Mo and Cl:
52 kept) against the sum of the occupations. Data: cclib test data (BSD-3-Clause), tests/data/<program>/README.md.
"""

from pathlib import Path
import gzip

import numpy as np
import pytest

from modules.spectrum.readers import orbital_files
from modules.spectrum.readers.gamess import read_gamess
from modules.spectrum.readers.nwchem import read_nwchem
from modules.spectrum.readers.output_orbitals import (
    has_orbitals,
    read_gamess_orbitals,
    read_nwchem_orbitals,
    read_qchem_orbitals,
)
from modules.spectrum.readers.qchem import read_qchem

DATA = Path(__file__).parents[1] / 'data'


def text(folder, name):
    return gzip.decompress((DATA / folder / name).read_bytes()).decode('utf-8')


CASES = [
    ('gamess', 'dvb_sp_gamess-2017.out.gz', read_gamess_orbitals, read_gamess, 70, False),
    ('gamess', 'dvb_un_sp_gamess-2017.out.gz', read_gamess_orbitals, read_gamess, 69, True),
    ('gamess', 'MoOCl4-sp_gamess-2017.out.gz', read_gamess_orbitals, read_gamess, 52, False),
    ('nwchem', 'dvb_sp_ks_nwchem-7.0.out.gz', read_nwchem_orbitals, read_nwchem, 70, False),
    ('nwchem', 'dvb_un_sp_ks_nwchem-7.0.out.gz', read_nwchem_orbitals, read_nwchem, 69, True),
    ('qchem', 'dvb_sp_qchem-5.4.out.gz', read_qchem_orbitals, read_qchem, 70, False),
    ('qchem', 'dvb_sp_un_qchem-5.4.out.gz', read_qchem_orbitals, read_qchem, 69, True),
]


@pytest.mark.parametrize('folder, name, read, output, electrons, open_shell', CASES)
def test_orbitals_against_the_printed_charges(folder, name, read, output, electrons, open_shell):
    log = text(folder, name)
    assert has_orbitals(log) and orbital_files.kind(log) == folder
    orbitals = read(log)
    assert orbitals.deviation < 1e-4 and orbitals.unrestricted == open_shell
    assert sum(o.occupation for o in orbitals.orbitals) == pytest.approx(electrons)
    printed = np.array(output(log).properties.charges['mulliken'])
    assert np.max(np.abs(orbitals.mulliken() - printed)) < 5e-5
    assert orbital_files.read_orbitals(log).source == orbitals.source


def test_gamess_cartesian_d_on_several_centres():
    # MoOCl4: Cartesian d on Mo and O — their order and normalization are fixed by the overlaps between the centres
    orbitals = read_gamess_orbitals(text('gamess', 'MoOCl4-sp_gamess-2017.out.gz'))
    assert any(s.l == 2 and not s.pure for s in orbitals.shells) and orbitals.molecule.formula == 'Cl4MoO'


def test_qchem_pure_functions_on_one_atom():
    # C/aug-cc-pVQZ: pure d, f, g; normalized and orthonormal (the order m −l … +l is an assumption, see §6)
    orbitals = read_qchem_orbitals(text('qchem', 'C_bigbasis_qchem-5.4.out.gz'))
    assert {s.l for s in orbitals.shells if s.pure} == {2, 3, 4} and orbitals.deviation < 1e-4
    assert sum(o.occupation for o in orbitals.orbitals) == pytest.approx(6)


def test_outputs_without_orbitals():
    log = text('nwchem', 'water_mp2_nwchem-7.0.out.gz')
    assert not has_orbitals(log)
    with pytest.raises(ValueError):
        read_nwchem_orbitals(log)

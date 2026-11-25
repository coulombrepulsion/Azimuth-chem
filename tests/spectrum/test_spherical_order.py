"""The order of the pure (spherical) functions of a shell in NWChem and Q-Chem outputs (output_orbitals.py).

On one atom the orthonormality of the orbitals does not tell the functions of a shell apart; on several atoms, with
no symmetry, a wrong order of m breaks it, and the Mulliken charges from the orbitals read here no longer match those
the program prints. Data: tests/data/spherical (formaldehyde, B3LYP/cc-pVTZ — pure d on C, O, H and f on C, O),
computed by tools/run_references.py spherical; skipped until the outputs are there.
"""

from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.readers.nwchem import read_nwchem
from modules.spectrum.readers.output_orbitals import read_nwchem_orbitals, read_qchem_orbitals
from modules.spectrum.readers.qchem import read_qchem

DATA = Path(__file__).parents[1] / 'data' / 'spherical'
CASES = [
    ('formaldehyde_tz_nwchem.out', read_nwchem_orbitals, read_nwchem, 0.006),  # DFT prints populations to 0.01
    ('formaldehyde_tz_qchem.out', read_qchem_orbitals, read_qchem, 5e-4),
]


@pytest.mark.parametrize('name, read, output, within', CASES)
def test_pure_d_and_f_on_several_centres(name, read, output, within):
    path = DATA / name
    if not path.exists():
        pytest.skip(f'нет {name}: .venv/bin/python tools/run_references.py spherical --programs nwchem,qchem')
    log = path.read_text(encoding='utf-8', errors='replace')
    orbitals = read(log)
    assert {s.l for s in orbitals.shells if s.pure} >= {2, 3}
    assert orbitals.deviation < 1e-4  # C^T S C = 1: the order of m fits the overlaps between the centres
    assert sum(o.occupation for o in orbitals.orbitals) == pytest.approx(16)
    printed = np.array(output(log).properties.charges['mulliken'])
    assert np.max(np.abs(orbitals.mulliken() - printed)) < within



def test_the_mulliken_charges_of_nwchem_dft():
    """DFT with «mulliken» prints «Total Density - Mulliken Population Analysis» (populations to 0.01), not the
    «Total gross population on atoms» of SCF."""
    path = DATA / 'formaldehyde_tz_nwchem.out'
    if not path.exists():
        pytest.skip('нет formaldehyde_tz_nwchem.out')
    charges = read_nwchem(path.read_text(encoding='utf-8', errors='replace')).properties.charges['mulliken']
    assert charges == pytest.approx((0.16, -0.24, 0.04, 0.04))  # 6 − 5.84, 8 − 8.24, 1 − 0.96

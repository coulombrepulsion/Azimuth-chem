"""The density of states. Oracles: the Mulliken charges that Gaussian 16 wrote into the fchk of MoOCl4 (SCF
density) — the charges made from our shares must be the same; the PDOS of all the fragments add up to the DOS; the area
of a normalized line is one state; the HOMO of water is the lone pair of O."""

from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import dos
from modules.spectrum.readers.orbital_files import read_orbitals

EXAMPLES = Path(__file__).parents[2] / 'examples' / '6-orbitals'


def _fchk_mulliken(text):
    lines = text.splitlines()
    start = next(k for k, line in enumerate(lines) if line.startswith('Mulliken Charges'))
    count = int(lines[start].split()[-1])
    values = []
    for line in lines[start + 1:]:
        values += [float(v) for v in line.split()]
        if len(values) >= count:
            return np.array(values[:count])


def test_shares_give_the_mulliken_charges_of_gaussian():
    text = (EXAMPLES / 'MoOCl4_ecp_gaussian16.fchk').read_text(encoding='utf-8')
    orbitals = read_orbitals(text)
    shares = dos.atom_shares(orbitals)
    assert np.allclose(shares.sum(axis=1), 1.0, atol=1e-6)
    occupations = np.array([o.occupation for o in orbitals.orbitals])
    charges = np.array(orbitals.charges, dtype=float) - occupations @ shares  # Z (valence, with the ECP) − population
    assert np.allclose(charges, _fchk_mulliken(text), atol=2e-6)
    assert [name for name, _ in dos.by_element(orbitals.molecule)] == ['Mo', 'Cl', 'O']  # the metal first


def test_pdos_add_up_and_the_lines_are_one_state_each():
    orbitals = read_orbitals((EXAMPLES / 'water_mp2_gaussian16.fchk').read_text(encoding='utf-8'))
    fragments = dos.by_element(orbitals.molecule)
    data = dos.curves(orbitals, fragments, fwhm=0.3, window=(-40.0, 30.0), points=7000, pair=(0, 1))
    total = data['total']
    assert np.allclose(sum(y for _, y in data['parts']), total, rtol=1e-6, atol=1e-7)
    inside = sum(1 for e, _ in data['levels'] if -38.0 < e < 28.0)
    assert np.trapezoid(total, data['x']) == pytest.approx(inside, rel=1e-3)
    homo = data['homo']
    assert homo == pytest.approx(-0.388214643 * dos.HARTREE_EV)
    row = [k for k, o in enumerate(orbitals.orbitals) if o.occupation > 0][-1]
    assert dos.atom_shares(orbitals)[row, 0] == pytest.approx(1.0, abs=1e-6)  # the lone pair 1b1 — only O
    assert dos.overlap_population(orbitals, (0,), (1, 2))[row] == pytest.approx(0.0, abs=1e-8)  # non-bonding
    assert dos.overlap_population(orbitals, (0,), (1, 2))[0:4].max() > 0.1  # a bonding O–H orbital
    lorentz = dos.broaden([0.0], [1.0], np.linspace(-200, 200, 400001), 0.5, 'lorentz')
    assert np.trapezoid(lorentz, np.linspace(-200, 200, 400001)) == pytest.approx(1.0, abs=2e-3)

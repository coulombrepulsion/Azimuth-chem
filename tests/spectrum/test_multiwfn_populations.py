"""The Hirshfeld charges and the AIM basins of Multiwfn (modules/spectrum/wavefunction/multiwfn_populations.py).

Oracles: the outputs of Multiwfn 2026.7.15 (Homebrew, macOS) recorded on the Mac of the user by
tools/record_multiwfn_populations.py (tests/data/multiwfn/pop_*.txt) — water of Gaussian 16 (MP2, fchk), the UKS cation
of divinylbenzene (ORCA, Molden), [MoOCl4]2− with the ECP of Mo and Cl (Gaussian 16, fchk). The numbers checked are
those Multiwfn printed; the charges of the basins must add up to the net charge Multiwfn printed («Net charge»).
"""

import re
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.wavefunction import multiwfn_populations as mp
from modules.spectrum.readers.orbital_files import read_orbitals

DATA = Path(__file__).parents[1] / 'data'
MWFN = DATA / 'multiwfn'


def text(name):
    return (MWFN / name).read_text(encoding='utf-8', errors='replace')


def nuclear(name):
    return np.array(read_orbitals((DATA / 'orbitals' / name).read_text(encoding='utf-8', errors='replace')).charges)


def net_charge(output):
    return float(re.search(r'Net charge:\s*(-?\d+\.\d+)', output).group(1))


def test_answers_follow_the_record():
    assert mp.HIRSHFELD == ('7', '1', '1', 'n', '0', 'q')
    assert mp.basin_answers() == ('17', '1', '1', '2', '7', '2', '1', '-10', 'q')  # −10 leaves the basin menu
    assert mp.basin_answers(spin=True)[-5:] == ('7', '2', '5', '-10', 'q')
    assert 'answers: ' + ' | '.join(mp.basin_answers(spin=True)) in text('pop_cation_basins_spin.txt')


def test_hirshfeld_charges_as_printed():
    assert mp.parse_hirshfeld(text('pop_water_hirshfeld.txt')) == (-0.30463436, 0.15231718, 0.15231718)
    cation = mp.parse_hirshfeld(text('pop_cation_hirshfeld.txt'))
    assert len(cation) == 20 and cation[0] == 0.06861382 and sum(cation) == pytest.approx(1.0, abs=1e-6)
    metal = mp.parse_hirshfeld(text('pop_MoOCl4_hirshfeld.txt'))
    assert metal[0] == 0.49802143 and sum(metal) == pytest.approx(-2.0, abs=1e-6)
    assert mp.parse_hirshfeld('no Hirshfeld here') is None


def test_basins_of_water():
    output = text('pop_water_basins_exact.txt')
    found, left = mp.parse_basins(output, 3)
    assert left == [0.0] and found[0].tolist() == [8.7524717892, 0.6240545426, 0.6240554772]  # atom 1 (O) — basin 2, 2 — basin 3, 3 — basin 1
    charges = nuclear('water_mp2_g16.fchk') + mp.core_electrons(output, 3) - found[0]
    assert charges == pytest.approx([-0.7524717892, 0.3759454574, 0.3759445228])
    assert charges.sum() == pytest.approx(net_charge(output), abs=1e-3)


def test_basins_of_an_open_shell_charges_and_spins():
    output = text('pop_cation_basins_spin.txt')
    (rho, spin), left = mp.parse_basins(output, 20)
    assert left == [0.0, 0.0]
    charges = nuclear('molden5.7_dvb_un_sp.molden') - rho
    assert charges.sum() == pytest.approx(net_charge(output), abs=2e-3)
    # the spin table is printed by atom: «1 (C ) 14 0.19228782 …», «15 (C ) 10 0.29160260 …»
    assert spin[0] == 0.19228782 and spin[14] == 0.29160260 and spin[10] == -0.02818121
    assert spin.sum() == pytest.approx(0.99993113, abs=1e-7)
    # the attractors of the ρ table belong to the same atoms as the basins of the table by atom
    owner = dict((int(a), int(b)) for a, b in re.findall(r'Attractor\s+(\d+)\s+corresponds to atom\s+(\d+)', output))
    rows = re.findall(r'^\s*(\d+)\s*\(\s*[A-Z][a-z]?\s*\)\s+(\d+)\s+-?\d+\.\d+', output, re.M)
    assert rows and all(owner[int(basin)] == int(atom) for atom, basin in rows)


def test_basins_with_an_ecp_count_the_core_put_back():
    output = text('pop_MoOCl4_basins_exact.txt')
    core = mp.core_electrons(output, 6)
    assert core.tolist() == [28, 0, 10, 10, 10, 10]  # «Mo(    1)      Core electrons: 28» …
    (rho,), _ = mp.parse_basins(output, 6)
    charges = nuclear('Mo4OCl4-sp_g16.fchk') + core - rho
    assert charges.sum() == pytest.approx(net_charge(output), abs=1e-3)  # the dianion: −2
    assert charges[0] == pytest.approx(1.6081, abs=1e-4) and charges[2] == pytest.approx(-0.6935, abs=1e-4)


def test_run_basins_and_hirshfeld_through_a_fake_multiwfn(tmp_path, monkeypatch):
    # the runs read what Multiwfn printed; a basin of no atom (a non-nuclear attractor) is refused, not given to an atom
    monkeypatch.setattr(mp.multiwfn, '_run', lambda program, path, answers, *a, **k: (text(
        'pop_cation_basins_spin.txt' if answers[0] == '17' else 'pop_water_hirshfeld.txt'), {}))
    charges, spins, _ = mp.run_basins('Multiwfn', 'x.molden', nuclear('molden5.7_dvb_un_sp.molden'), spin=True)
    assert len(charges) == len(spins) == 20 and sum(spins) == pytest.approx(1.0, abs=1e-3)
    assert mp.run_hirshfeld('Multiwfn', 'x.fchk')[0][0] == -0.30463436
    nna = text('pop_water_basins_exact.txt').replace('Attractor     1 corresponds to atom     3', 'Attractor     1 is NNA')
    monkeypatch.setattr(mp.multiwfn, '_run', lambda *a, **k: (nna, {}))
    with pytest.raises(ValueError, match='ненуклеарные'):
        mp.run_basins('Multiwfn', 'x.fchk', [8, 1, 1])


def test_hirshfeld_spins_of_the_fuzzy_space():
    # 15 → −1 → 3 (Hirshfeld of the built-in atomic densities, «current: Hirshfeld*») → 1 → 5; the table «Atomic space
    # Value …»: the spin of the cation adds up to 1, ρ of water to 10, and the ρ of the Hirshfeld atoms of water gives
    # the charges of 7 → 1 before its normalization (O −0.30475137 there)
    assert mp.HIRSHFELD_SPIN == ('15', '-1', '3', '1', '5', '0', 'q')
    output = text('pop_cation_hirshfeld3_spin.txt')
    assert 'current: Hirshfeld*' in output
    spins = mp.parse_fuzzy(output)
    assert len(spins) == 20 and spins[0] == 0.16103607 and spins[14] == 0.24689878
    assert sum(spins) == pytest.approx(1.00000680, abs=1e-7)
    rho = mp.parse_fuzzy(text('pop_water_hirshfeld3_rho.txt'))
    assert rho == (8.30469373, 0.84765298, 0.84765298)
    assert 8 - rho[0] == pytest.approx(-0.30475137, abs=1e-4)
    assert mp.parse_fuzzy('nothing') is None

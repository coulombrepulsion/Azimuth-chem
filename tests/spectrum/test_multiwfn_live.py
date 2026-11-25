"""The real Multiwfn of this computer against the records of the Mac.

Every analysis of the program talks to Multiwfn through the numbers of its menus, and those were recorded on the Mac of
the user (Multiwfn 2026.7.15, tests/data/multiwfn). Another build — Windows, an older or a newer version — may number
them differently, and the fake Multiwfn of the other tests would not see it. Here the installed Multiwfn runs the same
answers on the same files, and its results are compared with those parsed from the records of the Mac.

Skipped where Multiwfn is not installed. Run on Windows (and after an update of Multiwfn):
    .venv\\Scripts\\python -m pytest tests/spectrum/test_multiwfn_live.py -v
On a slow computer the benzaldehyde runs take some minutes.
"""

import gzip
import shutil
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import charge_transfer as ct
from modules.spectrum.wavefunction import multiwfn
from modules.spectrum.wavefunction import multiwfn_lmo as ml
from modules.spectrum.wavefunction import multiwfn_populations as mp
from modules.spectrum.wavefunction import multiwfn_resp as mr
from modules.spectrum.readers.orbital_files import read_orbitals

DATA = Path(__file__).parents[1] / 'data'
MWFN = DATA / 'multiwfn'
WATER = DATA / 'orbitals' / 'water_mp2_g16.fchk'
WATER_EXAMPLE = Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk'
CATION = DATA / 'orbitals' / 'molden5.7_dvb_un_sp.molden'
EXCITED = MWFN / 'benzaldehyde_cam-b3lyp_orca.out'
CHO, RING = [1, 2, 9], [3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14]

PROGRAM = multiwfn.find(search=True)
pytestmark = pytest.mark.skipif(PROGRAM is None, reason='Multiwfn is not installed')


def recorded(name):
    return (MWFN / name).read_text(encoding='utf-8', errors='replace')


@pytest.fixture(scope='module')
def benzaldehyde(tmp_path_factory):
    path = tmp_path_factory.mktemp('benzaldehyde') / 'benzaldehyde.molden.input'
    path.write_bytes(gzip.decompress((MWFN / 'benzaldehyde_cam-b3lyp_def2-svpd.molden.gz').read_bytes()))
    return path


@pytest.fixture(autouse=True, scope='module')
def fresh_cache():
    multiwfn.clear_cache()
    yield
    multiwfn.clear_cache()


def test_the_version_is_said():
    text, _ = multiwfn._run(PROGRAM, WATER, ('q',), timeout=120)
    number = multiwfn.version(text)
    print(f'\nMultiwfn {number}: {PROGRAM}')
    assert number, 'Multiwfn started but printed no version:\n' + multiwfn._tail(text)


@pytest.mark.skipif(not WATER_EXAMPLE.is_file(), reason='no examples/6-orbitals')
def test_adch_and_cm5_charges():
    charges, _, _ = multiwfn.run_charges(PROGRAM, WATER_EXAMPLE)
    mac = multiwfn.parse_charges(recorded('water_fchk_adch_2026.7.15.txt') + recorded('water_fchk_cm5_2026.7.15.txt'))
    for key in ('adch', 'cm5'):
        assert charges[key] == pytest.approx(mac[key], abs=1e-4), key


def test_hirshfeld_charges():
    charges, _ = mp.run_hirshfeld(PROGRAM, WATER)
    assert charges == pytest.approx(mp.parse_hirshfeld(recorded('pop_water_hirshfeld.txt')), abs=1e-4)


def test_hirshfeld_spins_of_an_open_shell():
    spins, _ = mp.run_hirshfeld_spins(PROGRAM, CATION)
    assert sum(spins) == pytest.approx(1.0, abs=1e-3)
    assert spins == pytest.approx(mp.parse_fuzzy(recorded('pop_cation_hirshfeld3_spin.txt')), abs=1e-3)


def test_resp_charges():
    charges, _, rrmse, chg, _ = mr.run_resp(PROGRAM, WATER)
    mac, _, mac_rrmse = mr.parse_resp(recorded('resp_water_standard_chg.txt'))
    assert charges == pytest.approx(mac, abs=1e-4) and rrmse == pytest.approx(mac_rrmse, abs=1e-3)
    assert chg and chg.split()[0] == 'O'


def test_aim_charges_of_water():
    nuclear = read_orbitals(WATER.read_text(encoding='utf-8', errors='replace')).charges
    charges, _, _ = mp.run_basins(PROGRAM, WATER, nuclear)
    mac = recorded('pop_water_basins_exact.txt')
    found, _ = mp.parse_basins(mac, 3)
    expected = np.asarray(nuclear, dtype=float) + mp.core_electrons(mac, 3) - found[0]
    assert charges == pytest.approx(expected, abs=2e-3)


def same_lmos(summary, mac):
    """The same LMOs (spin, number), of the same kind, on the same atoms; the shares within 0.5 %."""
    assert sorted(summary) == sorted(mac)
    for key, (kind, shares) in mac.items():
        assert summary[key][0] == kind, key
        assert [a for a, _, _ in summary[key][1]] == [a for a, _, _ in shares], key
        assert [p for _, _, p in summary[key][1]] == pytest.approx([p for _, _, p in shares], abs=0.5), key


def test_localized_orbitals_of_water():
    _, summary, _ = ml.run_lmo(PROGRAM, WATER, 'pm')
    same_lmos(summary, ml.parse_summary(recorded('lmo_water_pm.txt')))


def test_localized_orbitals_of_an_open_shell():
    _, summary, _ = ml.run_lmo(PROGRAM, CATION, 'pm', open_shell=True)
    same_lmos(summary, ml.parse_summary(recorded('lmo_cation_pm_mulliken.txt')))


def test_hole_and_electron_of_s1(benzaldehyde):
    found, _, _ = multiwfn.run_hole_electron(PROGRAM, benzaldehyde, EXCITED, 1)
    mac = multiwfn.parse_hole_electron(recorded('benzaldehyde_orca_hole_s1_2026.7.15.txt'))
    for key in ('d', 'sr', 'h', 't'):
        assert found[key] == pytest.approx(mac[key], abs=0.03), key


def test_charge_transfer_of_s1(benzaldehyde):
    found, _ = ct.run_ifct(PROGRAM, benzaldehyde, EXCITED, 1, [CHO, RING])
    mac = ct.parse_ifct(recorded('exc_ifct2_s1.txt'))
    assert found['hole'] == pytest.approx(mac['hole'], abs=0.05)
    assert found['ct'] == pytest.approx(mac['ct'], abs=0.05)


def test_transition_matrix_of_s1(benzaldehyde):
    matrix, _ = ct.run_matrix(PROGRAM, benzaldehyde, EXCITED, 1, [CHO, RING])
    assert matrix == pytest.approx(ct.read_tmat(recorded('exc_heatmap2_fragments__tmat.txt')), abs=1e-4)
    atoms, _ = ct.run_matrix(PROGRAM, benzaldehyde, EXCITED, 1)
    assert atoms.shape == (14, 14)


def test_a_folder_with_cyrillic_and_spaces(tmp_path):
    # the files of the user lie in «Документы/Расчёты воды»: the program copies them under ASCII names
    folder = tmp_path / 'Расчёты воды'
    folder.mkdir()
    shutil.copyfile(WATER, folder / 'вода.fchk')
    charges, _ = mp.run_hirshfeld(PROGRAM, folder / 'вода.fchk')
    assert len(charges) == 3

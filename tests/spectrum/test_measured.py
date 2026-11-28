"""The measured values of the molecules of the course (modules/spectrum/analysis/measured.py).

Oracles: the numbers of the pages of NIST CCCBDB copied into the file (spot-checked here against the page text: water
3657, 1595, 3756 cm⁻¹, r(OH) 0.958 Å, 1.857 D, ΔfH −241.81 kJ/mol), and the frequencies and the dipole that ORCA
printed in the recorded outputs (tests/data: water B3LYP/def2-SVP, ethylene and formaldehyde B3LYP/6-31G(d)).
"""

import re
from pathlib import Path

import pytest

from modules.spectrum.analysis import measured
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).resolve().parents[1] / 'data'


def _output(path):
    return read_any(path.read_text(encoding='utf-8', errors='replace'), path)


def test_the_data_of_the_thirty_molecules():
    found = measured.molecules()
    assert len(found) == 30 and len({m['key'] for m in found}) == 30
    water = next(m for m in found if m['key'] == 'water')
    assert [v for _, v in water['fundamentals']] == [3657, 1595, 3756] and water['bonds'] == [['O', 'H', 0.958]]
    assert (water['dipole_debye'], water['hf298_kj'], water['ie_ev']) == (1.857, -241.81, 12.621)
    assert measured.url(water) == 'https://cccbdb.nist.gov/exp2x.asp?casno=7732185'
    for m in found:
        n = sum(int(c or 1) for _, c in re.findall(r'([A-Z][a-z]?)(\d*)', m['formula']))
        linear = m['key'] in ('co2', 'hcn', 'acetylene')
        count = len(measured.modes(m))
        # every mode of the molecule, the degenerate ones counted as often as their degeneracy; acetic acid lacks the
        # one its source calls questionable; three molecules have no fundamentals in CCCBDB
        assert count in (3 * n - (5 if linear else 6), 0) or m['key'] == 'acetic_acid', m['key']
        assert m['name']['ru'] and m['name']['en'] and m['name']['zh'] and m['hf_source']
    assert len(measured.modes(next(m for m in found if m['key'] == 'methane'))) == 9  # E twice, T₂ three times


def test_each_molecule_is_told_by_its_structure():
    from modules.compass.chemistry.formats_smiles import from_smiles

    seen = set()
    for m in measured.molecules():
        built = from_smiles(m['smiles'], quick=True)
        assert measured.identify(built)['key'] == m['key'], m['key']
        seen.add(measured.signature(built))
    assert len(seen) == 30  # ethanol and dimethyl ether, the isomers, apart
    assert measured.identify(from_smiles('CCCO', quick=True)) is None and measured.identify(None) is None


def test_water_against_experiment():
    output = _output(DATA / 'orca601' / 'h2o_optfreq.out')
    entry = measured.identify(output.geometry)
    assert entry['key'] == 'water'
    found = measured.compare(entry, output)
    vib = found.vibrations
    computed = (1637.62, 3786.94, 3881.92)  # printed by ORCA
    assert [p[:2] for p in vib.pairs] == [(1637.62, 1595.0), (3786.94, 3657.0), (3881.92, 3756.0)]
    assert vib.mean_abs == pytest.approx((42.62 + 129.94 + 125.92) / 3)
    factor = (1637.62 * 1595 + 3786.94 * 3657 + 3881.92 * 3756) / sum(w * w for w in computed)
    assert vib.factor == pytest.approx(factor) and 0.95 < vib.factor < 0.98  # B3LYP: harmonic ≈ 3–4 % too high
    assert vib.mean_abs_scaled < vib.mean_abs / 2
    (bond,) = found.bonds
    assert bond.pair == 'H–O' and bond.count == 2 and bond.measured == 0.958 and 0.95 < bond.computed < 0.98
    assert found.dipole == (pytest.approx(2.004080973), 1.857)  # «Magnitude (Debye)» of ORCA


def test_ethylene_and_formaldehyde_in_order_of_their_frequencies():
    ethylene = _output(DATA / 'raman' / 'c2h4_raman_numfreq_orca.out')
    entry = measured.identify(ethylene.geometry)
    assert entry['key'] == 'ethylene'
    vib = measured.compare(entry, ethylene).vibrations
    assert len(vib.pairs) == 12 and vib.pairs[0][:2] == (pytest.approx(835.11), 826.0)  # the lowest: the CH₂ rock
    assert vib.pairs[-1][:2] == (pytest.approx(3243.92), 3105.0)
    formaldehyde = _output(DATA / 'raman' / 'ch2o_raman_numfreq_orca.out')
    found = measured.compare(measured.identify(formaldehyde.geometry), formaldehyde)
    assert found.entry['key'] == 'formaldehyde' and found.vibrations.pairs[3][:2] == (pytest.approx(1842.09), 1746.0)
    rows = {row.pair: row for row in found.bonds}
    assert rows['C–O'].measured == 1.205 and abs(rows['C–O'].delta) < 0.02 and rows['C–H'].count == 2


def test_what_cannot_be_paired_is_said():
    entry = next(m for m in measured.molecules() if m['key'] == 'water')
    assert 'мнимые' in measured.vibrations(entry, [-120.0, 1600.0, 3700.0]).reason
    assert 'пары по порядку не составить' in measured.vibrations(entry, [1600.0, 3700.0]).reason
    phenol = next(m for m in measured.molecules() if m['key'] == 'phenol')
    assert 'нет опытных частот' in measured.vibrations(phenol, [100.0] * 33).reason
    # two measured values of one pair of elements: each computed bond goes to the nearer one
    formic = next(m for m in measured.molecules() if m['key'] == 'formic_acid')
    assert [v for a, b, v in formic['bonds'] if {a, b} == {'C', 'O'}] == [1.202, 1.343]

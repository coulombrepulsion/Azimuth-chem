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


def test_the_enthalpy_of_a_reaction_from_experiment():
    # CH₄ + 2 O₂ → CO₂ + 2 H₂O (gas): ΔrH° = −393.51 + 2·(−241.81) − (−74.60) − 2·0 = −802.53 kJ/mol (the ΔfH° of the
    # file); a species without a ΔfH° — no value, named
    from modules.compass.chemistry.formats_smiles import from_smiles
    from modules.spectrum.analysis.reaction import Species, Stage

    def species(smiles, label):
        return Species(label, 0.0, geometry=from_smiles(smiles, quick=True))

    oxygen = species('O=O', 'O₂')
    start = Stage('реагенты', (species('C', 'CH₄'), oxygen, oxygen))
    end = Stage('продукты', (species('O=C=O', 'CO₂'), species('O', 'H₂O'), species('O', 'H₂O')))
    found = measured.reaction_enthalpy(start, end)
    assert found.value == pytest.approx(-802.53) and not found.missing and len(found.known) == 6
    assert measured.enthalpy_of_formation(oxygen.geometry)[0] == 0.0
    other = Stage('x', (species('CCCCCCCCO', 'октанол'),))
    assert measured.reaction_enthalpy(start, other).value is None
    assert measured.reaction_enthalpy(start, other).missing == ('октанол',)


def test_the_computed_bonds_of_each_kind_together():
    # dimethyl ether: two C–H in the plane COC (measured 1.085 Å) and four out of it (1.099 Å); B3LYP makes all of them
    # about 0.01 Å longer — the nearest measured value took every one to the longer kind (the check of the 30
    # molecules, 2026-11-28); the runs of least spread keep the two kinds
    computed = [1.0981, 1.0983, 1.1069, 1.1070, 1.1072, 1.1073]
    assert measured._groups(computed, 2) == [computed[:2], computed[2:]]
    assert measured._groups(computed, 1) == [computed] and measured._groups([1.1], 2) == [[1.1]]
    assert measured._groups([1.20, 1.34], 2) == [[1.20], [1.34]]  # C=O and C–O of formic acid


def test_a_linear_molecule_from_smiles_is_exactly_linear():
    # O=C=O, H–C≡N, H–C≡C–H off the line by 0.001 Å: ORCA removed six modes, a bending one was lost (3 frequencies of
    # CO₂ instead of 4 — the check of the 30 molecules, 2026-11-28)
    import numpy as np

    from modules.compass.chemistry.formats_smiles import from_smiles, linearized

    for smiles in ('O=C=O', 'C#N', 'C#C', 'CC#C'):
        x = np.array([a.position for a in from_smiles(smiles, quick=True).atoms])
        if smiles == 'CC#C':  # propyne: not linear (the methyl hydrogens) — left alone
            continue
        centre = x.mean(axis=0)
        axis = np.linalg.svd(x - centre)[2][0]
        off = np.linalg.norm((x - centre) - np.outer((x - centre) @ axis, axis), axis=1)
        assert off.max() < 1e-9, smiles
    water = from_smiles('O', quick=True)
    assert linearized(water) is water


def test_far_from_experiment_another_conformer_is_suggested():
    # glycine of SMILES in ORCA (B3LYP/def2-SVP, EXPERIMENT_CHECK.md): 5.58 D against 1.095 D of conformer I
    glycine = next(m for m in measured.molecules() if m['key'] == 'glycine')
    far = measured.Comparison(glycine, None, (), None, (5.58, 1.095))
    (hint,) = measured.conformer_hint(far)
    assert 'конформер' in hint and '5.58' in hint and '1.09' in hint
    water = next(m for m in measured.molecules() if m['key'] == 'water')
    near = measured.Comparison(water, None, (), None, (2.004, 1.857))  # the error of the method: no hint
    assert measured.conformer_hint(near) == ()
    output = _output(DATA / 'orca601' / 'h2o_optfreq.out')  # water: 100 cm⁻¹ — within what B3LYP does
    assert measured.compare(water, output).hints == ()
    off = measured.Comparison(water, measured.Vibrations(((1.0, 2.0, 'A'),), '', 150.0, 1.0, 1.0, 10.0))
    assert 'конформер' in measured.conformer_hint(off)[0]

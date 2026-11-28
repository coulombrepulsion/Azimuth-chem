"""The measured NMR shifts of the molecules of the course (modules/spectrum/analysis/measured_nmr.py).

Oracles: the numbers of Fulmer et al., Organometallics 29, 2176 (2010) as printed in its Tables 1 and 2 (acetone in
CDCl3: CH3 2.17 ppm, CO 207.07, CH3 30.92; pyridine C2/C6 149.90; methane −4.63; ethanol in D2O CH3 17.47), and the
count of the atoms of each signal from the structure itself (the hydrogens on the carbon, the carbons alike by
symmetry: six of benzene, two ortho of toluene, one para).
"""

from pathlib import Path

from modules.compass.chemistry.formats_smiles import from_smiles
from modules.spectrum.analysis import measured, measured_nmr, nmr_compare
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).resolve().parents[1] / 'data'


def _built(key):
    entry = next(m for m in measured.molecules() if m['key'] == key)
    return from_smiles(entry['smiles'], quick=True)


def test_the_numbers_of_the_table():
    data = measured_nmr._data()
    assert len(data['molecules']) == 14 and data['solvents'][2] == 'CDCl3' and len(data['solvents']) == 12
    assert set(data['molecules']) <= {m['key'] for m in measured.molecules()}
    acetone = {(s['nucleus'], s['label']): s['shifts'] for s in data['molecules']['acetone']}
    assert acetone[('H', 'CH3')]['CDCl3'] == 2.17 and acetone[('C', 'CO')]['CDCl3'] == 207.07
    assert acetone[('C', 'CH3')]['CDCl3'] == 30.92 and 'TFE-d3' not in acetone[('C', 'CO')]  # swapped in the table
    pyridine = {(s['nucleus'], s['label']): s['shifts'] for s in data['molecules']['pyridine']}
    assert pyridine[('C', 'CH(2,6)')]['CDCl3'] == 149.90
    assert data['molecules']['methane'][1]['shifts']['CDCl3'] == -4.63
    assert {(s['nucleus'], s['label']): s['shifts'] for s in data['molecules']['ethanol']}[('C', 'CH3')]['D2O'] == 17.47
    assert 'water' not in data['molecules']  # its OH moves with the sample


def test_each_signal_finds_its_atoms():
    sizes = {('benzene', 'C', 'CH'): 6, ('benzene', 'H', 'CH'): 6, ('toluene', 'C', 'CH(2,6)'): 2,
             ('toluene', 'C', 'CH(4)'): 1, ('toluene', 'H', 'CH(2,4,6)'): 3, ('toluene', 'H', 'CH3'): 3,
             ('pyridine', 'H', 'CH(2,6)'): 2, ('ethanol', 'H', 'CH2'): 2, ('acetone', 'H', 'CH3'): 6,
             ('acetone', 'C', 'CO'): 1, ('co2', 'C', 'CO2'): 1, ('furan', 'C', 'CH(3,4)'): 2}
    for key, signals in measured_nmr._data()['molecules'].items():
        molecule = _built(key)
        taken = {}
        for signal in signals:
            found = measured_nmr.atoms(molecule, signal)
            assert found and all(molecule.atoms[k].symbol == signal['nucleus'] for k in found), (key, signal['label'])
            assert not set(found) & taken.setdefault(signal['nucleus'], set()), (key, signal['label'])  # one signal each
            taken[signal['nucleus']] |= set(found)
            want = sizes.get((key, signal['nucleus'], signal['label']))
            assert want is None or len(found) == want, (key, signal['label'], found)


def test_ethanol_of_orca():
    # a real geometry of ORCA (the atoms in its order, not in that of the SMILES): the CH3 carbon is the one with
    # three hydrogens, the CH2 one is bonded to the oxygen
    path = DATA / 'orca601' / 'nmr_conformers' / 'ethanol_a.out'
    geometry = read_any(path.read_text(encoding='utf-8', errors='replace'), path).geometry
    assert measured_nmr.solvents(geometry, 'C')[0] == 'CDCl3' and 'D2O' in measured_nmr.solvents(geometry, 'C')
    text = measured_nmr.text(geometry, 'C')
    assert text.splitlines()[0] == '# Fulmer et al., Organometallics 29, 2176 (2010), CDCl3'
    lines = nmr_compare.parse(text)
    assert [m.delta for m in lines] == [18.41, 58.28] and all(len(m.atoms) == 1 for m in lines)
    from modules.compass.chemistry.builder import connections

    near = {}
    for i, j, *_ in connections(geometry):
        near.setdefault(i, []).append(geometry.atoms[j].symbol)
        near.setdefault(j, []).append(geometry.atoms[i].symbol)
    methyl, methylene = (m.atoms[0] - 1 for m in lines)
    assert near[methyl].count('H') == 3 and 'O' in near[methylene]
    hydrogens = nmr_compare.parse(measured_nmr.text(geometry, 'H', 'D2O'))
    assert [len(m.atoms) for m in hydrogens] == [3, 2] and [m.delta for m in hydrogens] == [1.17, 3.65]


def test_what_is_not_in_the_table():
    water = _built('water')
    assert measured_nmr.entry(water) is None and measured_nmr.text(water, 'H') == ''
    assert measured_nmr.solvents(water, 'H') == []
    assert measured_nmr.solvents(_built('co2'), 'H') == []  # no hydrogen
    assert measured_nmr.text(_built('benzene'), 'C', 'D2O') == ''  # not measured in water
    assert measured_nmr.entry(from_smiles('CCCO', quick=True)) is None

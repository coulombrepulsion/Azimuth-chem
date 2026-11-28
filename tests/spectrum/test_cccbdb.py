"""The measured values of any molecule of NIST CCCBDB, found on the network (modules/spectrum/analysis/cccbdb.py).

Oracles: the pages of CCCBDB as the site gave them on 2026-11-28 (tests/data/cccbdb: water, ethanol, chloroform, and
the page the site answered an unknown CAS number with — formaldehyde, the molecule asked before); their numbers read
by eye in the same pages (water: 3657 / 3832, 1595 / 1648, 3756 / 3943 cm⁻¹, r(OH) 0.958 Å, 1.857 D, 12.621 eV,
−241.81 kJ/mol; chloroform: six fundamentals, 1.040 D). A fake urlopen: no network in the tests.
"""

import io
import json
from contextlib import contextmanager
from pathlib import Path

import pytest

from modules.compass.chemistry.formats_smiles import from_smiles
from modules.spectrum.analysis import cccbdb, measured

DATA = Path(__file__).resolve().parents[1] / 'data' / 'cccbdb'


def _page(name):
    return (DATA / name).read_text(encoding='utf-8', errors='replace')


def test_a_page_of_cccbdb_read():
    water = cccbdb.parse(_page('water_7732185.html'), '7732-18-5')
    assert water['formula'] == 'H2O' and water['name']['en'] == 'Water' and water['smiles'] == 'O'
    assert water['inchikey'] == 'XLYOFNOQVPJJNP-UHFFFAOYSA-N'
    assert [v for _, v in water['fundamentals']] == [3657, 1595, 3756] and water['fundamentals'][0][0] == 'A1'
    assert [v for _, v in water['harmonic']][0] == 3832 and len(water['harmonic']) == 3
    assert water['bonds'] == [['O', 'H', 0.958]] and water['dipole_debye'] == 1.857
    assert (water['ie_ev'], water['vertical_ie_ev'], water['hf298_kj'], water['hf298_unc']) == (12.621, 12.600, -241.81, 0.03)
    assert water['hf_source'] == '2006Rus/Pin:6592' and water['hf0_kj'] == -238.90
    chloroform = cccbdb.parse(_page('chloroform_67663.html'), '67-66-3')
    assert chloroform['dipole_debye'] == 1.040 and len(chloroform['fundamentals']) == 6
    assert len(measured.modes(chloroform)) == 9  # three E twice
    assert {(a, b) for a, b, _ in chloroform['bonds']} >= {('C', 'Cl'), ('C', 'H')}
    ethanol = cccbdb.parse(_page('ethanol_64175.html'), '64-17-5')
    assert len(ethanol['fundamentals']) == 21 and ethanol['hf298_kj'] == -234.80
    with pytest.raises(ValueError, match='not a page'):
        cccbdb.parse('<html><h1>Search</h1></html>')


class _Fake:
    def __init__(self, pages):
        self.pages, self.asked = pages, []

    @contextmanager
    def __call__(self, request, timeout):
        url = request.full_url
        self.asked.append(url)
        for key, body in self.pages.items():
            if key in url:
                yield io.BytesIO(body.encode('utf-8'))
                return
        import urllib.error

        raise urllib.error.HTTPError(url, 404, 'not found', None, None)


def test_found_through_pubchem_checked_and_kept(tmp_path):
    synonyms = json.dumps({'InformationList': {'Information': [{'Synonym': ['chloroform', '7647-01-0', '67-66-3']}]}})
    fake = _Fake({'pubchem': synonyms, 'casno=7647010': _page('asked_1234567890_gave_formaldehyde.html'),
                  'casno=67663': _page('chloroform_67663.html')})
    molecule = from_smiles('ClC(Cl)Cl', quick=True)
    found = cccbdb.find(molecule, tmp_path, urlopen=fake)
    # the first number (another substance's) gave the page of another molecule — formaldehyde, as the site answers a
    # number it has no page of with the molecule asked before: refused by its graph
    assert found['formula'] == 'CHCl3' and found['cas'] == '67-66-3' and found['online']
    assert sum('casno=' in url for url in fake.asked) == 2
    again = _Fake({})
    assert cccbdb.find(molecule, tmp_path, urlopen=again)['cas'] == '67-66-3' and not again.asked  # kept: no network
    assert cccbdb.cached(molecule, tmp_path)['cas'] == '67-66-3'
    # not in CCCBDB: None, kept for a day; the network down: a message
    nothing = _Fake({'pubchem': json.dumps({'InformationList': {'Information': [{'Synonym': ['x']}]}})})
    other = from_smiles('CCCCCCCCCO', quick=True)
    assert cccbdb.find(other, tmp_path, urlopen=nothing) is None and cccbdb.cached(other, tmp_path) is None

    def down(request, timeout):
        raise TimeoutError('timed out')

    with pytest.raises(ValueError, match='Поиск в CCCBDB не удался'):
        cccbdb.find(from_smiles('CCCCCCCO', quick=True), tmp_path, urlopen=down)


def test_the_harmonic_frequencies_of_experiment(tmp_path):
    from modules.spectrum.readers.outputs import read_any

    path = Path(__file__).resolve().parents[1] / 'data' / 'orca601' / 'h2o_optfreq.out'
    output = read_any(path.read_text(encoding='utf-8'), path)
    water = cccbdb.parse(_page('water_7732185.html'), '7732-18-5')
    found = measured.compare(water, output)
    # B3LYP/def2-SVP harmonic: 1637.62, 3786.94, 3881.92; experiment harmonic: the page
    harmonic = sorted(v for _, v in water['harmonic'])
    assert [p[1] for p in found.harmonic.pairs] == harmonic
    assert found.harmonic.mean_abs < found.vibrations.mean_abs  # the anharmonicity is not the method's error

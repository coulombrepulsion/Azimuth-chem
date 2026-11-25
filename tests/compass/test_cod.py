"""Crystal structures from COD (modules/compass/chemistry/cod.py) — with a fake server: no network in tests.

Oracles: the formulas in Hill's order written here by hand (C first, then H, then the rest alphabetically; without
carbon all alphabetically — benzoic acid «C7 H6 O2», rutile «O2 Ti», copper sulfate pentahydrate «Cu H10 O9 S»); the
URL of the COD wiki (cod/result?…&format=json, cod/<number>.cif); the CIF of the examples is COD 7133168 (its own
header) and reads back as benzoic acid, P 21/n.
"""

from contextlib import contextmanager
import io
import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from modules.compass.chemistry import cod
from modules.compass.chemistry import crystal as cr

CIF = (Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif').read_text(encoding='utf-8')
RECORD = {'file': '7133168', 'formula': '- C7 H6 O2 -', 'chemname': 'benzoic acid', 'sg': 'P 1 21/n 1',
          'a': '5.502', 'b': '5.157', 'c': '21.884', 'alpha': '90', 'beta': '97.37', 'gamma': '90', 'year': '2024',
          'journal': 'Chemical communications (Cambridge, England)', 'doi': '10.1039/D4CC02134A'}


def fake(answers):
    asked = []

    @contextmanager
    def urlopen(address, timeout):
        asked.append(address)
        yield io.BytesIO(answers(address).encode('utf-8'))

    return urlopen, asked


def test_formulas_in_hill_order():
    assert cod.hill('C7H6O2') == 'C7 H6 O2' and cod.hill('O2H6C7') == 'C7 H6 O2'
    assert cod.hill('TiO2') == 'O2 Ti' and cod.hill('CuSO4H10O5') == 'Cu H10 O9 S'
    assert cod.hill('C6 H6') == 'C6 H6' and cod.hill('CH4') == 'C H4' and cod.hill('') == ''
    for bad in ('benzene', '7C', 'C7H6O2!'):
        with pytest.raises(ValueError):
            cod.hill(bad)


def test_the_url_of_a_search():
    address = cod.url('benzoic acid', 'C7H6O2', ('c', 'O'), exact=True)
    parsed = urlparse(address)
    assert f'{parsed.scheme}://{parsed.netloc}{parsed.path}' == 'https://www.crystallography.net/cod/result'
    query = parse_qs(parsed.query)
    assert query == {'text': ['benzoic acid'], 'formula': ['C7 H6 O2'], 'el1': ['C'], 'el2': ['O'],
                     'strictmin': ['2'], 'strictmax': ['2'], 'format': ['json']}
    with pytest.raises(ValueError):
        cod.url()
    assert cod.cif_url('7133168') == 'https://www.crystallography.net/cod/7133168.cif'


def test_the_records_and_the_cif():
    urlopen, asked = fake(lambda address: json.dumps([RECORD, {'file': '1000000', 'formula': '- O2 Ti -',
                                                                'mineral': 'Rutile', 'sg': 'P 42/m n m'}]))
    entries, count = cod.search(formula='C7H6O2', urlopen=urlopen)
    assert count == 2 and 'formula=C7%20H6%20O2' in asked[0]
    first = entries[0]
    assert (first.number, first.formula, first.name, first.group) == ('7133168', 'C7 H6 O2', 'benzoic acid', 'P 1 21/n 1')
    assert first.cell == (5.502, 5.157, 21.884, 90.0, 97.37, 90.0) and first.year == '2024'
    assert entries[1].name == 'Rutile' and entries[1].cell is None
    empty, _ = fake(lambda address: '[]')
    assert cod.search(text='nothing', urlopen=empty) == ([], 0)
    serve, asked = fake(lambda address: CIF)
    text = cod.fetch('7133168', urlopen=serve)
    assert asked == ['https://www.crystallography.net/cod/7133168.cif']
    crystal = cr.parse_cif(text)
    assert crystal.formula_sum.replace(' ', '') == 'C7H6O2' and len(crystal.operations) == 4
    wrong, _ = fake(lambda address: '<html>not found</html>')
    with pytest.raises(ValueError):
        cod.fetch('7133168', urlopen=wrong)


def test_a_search_by_the_cell():
    # the fields of the form «search by cell» of COD (amin … gamax; checked on the server a
    # 5.4–5.6, b 5.0–5.2, c 21.8–22.0 found 7133168): ± 1 % of each length — 5.502 → 5.447 … 5.557 — and ± 1° of each
    # angle; any order of the axes — the six orders of three different lengths, one request each, merged by number
    assert cod.parse_cell('5.502 5.157 21.884') == (5.502, 5.157, 21.884)
    assert cod.parse_cell('5.502(2), 5.157(1), 21.884(5); 90 97.37° 90') == (5.502, 5.157, 21.884, 90.0, 97.37, 90.0)
    for bad in ('', '5.5 5.1', '5.5 5.1 21.9 90 200 90', 'a b c'):
        with pytest.raises(ValueError):
            cod.parse_cell(bad)
    query = parse_qs(urlparse(cod.url(cell=(5.502, 5.157, 21.884, 90, 97.37, 90))).query)
    assert query['amin'] == ['5.447'] and query['amax'] == ['5.557'] and query['cmin'] == ['21.6652']
    assert query['betmin'] == ['96.37'] and query['betmax'] == ['98.37'] and query['gamax'] == ['91']
    assert len(cod.urls(cell=(5.502, 5.157, 21.884), any_order=True)) == 6
    assert len(cod.urls(cell=(5.0, 5.0, 21.884), any_order=True)) == 3  # two lengths equal — three orders
    other = dict(RECORD, file='7210454')
    urlopen, asked = fake(lambda address: json.dumps([RECORD, other] if 'amin=5.' in address else [RECORD]))
    entries, count = cod.search(cell=(5.502, 5.157, 21.884), any_order=True, urlopen=urlopen)
    assert len(asked) == 6 and count == 2 and [e.number for e in entries] == ['7133168', '7210454']

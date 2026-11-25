"""«Файл → Недавние файлы» and «Сохранить несколько файлов» — the functions without a window."""

from azimuth.core import read_xyz
from modules.compass.actions.file_actions import FileTool, push_recent, safe_name


def test_the_newest_file_first_once():
    paths = push_recent([], 'a')
    paths = push_recent(paths, 'b')
    paths = push_recent(paths, 'a')
    assert paths == ['a', 'b']
    assert len(push_recent([str(k) for k in range(20)], 'new', limit=12)) == 12


def test_file_names_of_structures():
    taken = {'water'}
    assert safe_name('water', taken) == 'water_2'
    assert safe_name('Water', taken) == 'Water_3'  # one file on Windows and macOS
    assert safe_name('C₆H₆ · 2', taken) == 'C₆H₆ · 2'
    assert safe_name('a/b:c*?', taken) == 'a_b_c_'
    assert safe_name('', taken) == 'structure' and safe_name('...', taken) == 'structure_2'


def test_one_xyz_and_one_sdf_of_a_set():
    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
    co = read_xyz('2\nco\nC 0 0 0\nO 0 0 1.128')
    xyz = FileTool.batch_text([(water, 'вода'), (co, 'CO')], '.xyz')
    lines = xyz.splitlines()
    assert lines[0] == '3' and lines[1] == 'вода' and lines[5] == '2' and lines[6] == 'CO' and len(lines) == 9
    sdf = FileTool.batch_text([(water, 'вода'), (co, 'CO')], '.sdf')
    assert sdf.count('$$$$') == 2 and sdf.startswith('вода') and '\nCO\n' in sdf
    from modules.compass.chemistry import formats

    records = formats.read_sdf_records(sdf)
    assert [len(m.atoms) for m in records] == [3, 2]


def test_a_picture_and_a_file_of_one_structure():
    # the test of the user — «CO.xyz» in the folder made the picture «CO_2.png»
    taken = {'co.xyz'}
    assert safe_name('CO', taken, '.png') == 'CO.png'
    assert safe_name('CO', taken, '.xyz') == 'CO_2.xyz'


# -- «Вставить структуру из буфера», «Молекула по названию…» ---------------------------------------------------
def test_a_structure_from_the_clipboard():
    import pytest

    from modules.compass.actions.file_actions import structure_from_text

    whole = '3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n'
    molecule, kind = structure_from_text(whole)
    assert kind == 'xyz' and molecule.formula == 'H2O'
    lines = '  O   0.000000   0.000000   0.000000\r\n  H   0.960000   0.000000   0.000000\r\nH -0.24 0.93 1e-3\n'
    molecule, kind = structure_from_text(lines)  # the lines of an output or an article, without the count
    assert kind == 'xyz' and [a.symbol for a in molecule.atoms] == ['O', 'H', 'H']
    assert molecule.atoms[2].position == (-0.24, 0.93, 0.001)
    molecule, kind = structure_from_text('CCO')
    assert kind == 'smiles' and molecule.formula == 'C2H6O'
    molfile = ('methane\n  Azimuth\n\n  1  0  0  0  0  0  0  0  0  0999 V2000\n'
               '    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\nM  END\n')
    molecule, kind = structure_from_text(molfile)
    assert kind == 'mol' and [a.symbol for a in molecule.atoms] == ['C']
    for text in ('', '   \n', 'two words', 'line one\nline two'):
        with pytest.raises(ValueError):
            structure_from_text(text)


class _Answer:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.text.encode('utf-8')


def _server(answers):
    """A fake PubChem: {a part of the URL: text or an HTTP code}; asked URLs are kept in .asked."""
    import urllib.error

    def urlopen(url, timeout):
        urlopen.asked.append(url)
        for part, answer in answers.items():
            if part in url:
                if isinstance(answer, int):
                    raise urllib.error.HTTPError(url, answer, 'no', {}, None)
                return _Answer(answer)
        raise urllib.error.HTTPError(url, 404, 'no', {}, None)

    urlopen.asked = []
    return urlopen


def test_a_molecule_by_its_name_from_pubchem():
    # the URLs of PUG REST (input by name; the 3D record; the properties renamed in 2025 — the old names still tried)
    from modules.compass.chemistry import pubchem

    sdf = 'aspirin\n  PubChem\n\n  0  0  0  0  0  0  0  0  0  0999 V2000\nM  END\n$$$$\n'
    server = _server({'/aspirin/SDF?record_type=3d': sdf})
    assert pubchem.by_name(' aspirin ', urlopen=server) == ('sdf', sdf)
    assert server.asked == ['https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/aspirin/SDF?record_type=3d']
    # no 3D record: the SMILES; a property the server refuses (400) — the next name
    server = _server({'record_type=3d': 404, '/property/SMILES/': 400,
                      '/property/ConnectivitySMILES/': '{"PropertyTable": {"Properties": [{"CID": 1, '
                                                       '"ConnectivitySMILES": "C[N+](C)(C)C"}]}}'})
    assert pubchem.by_name('tetramethylammonium', urlopen=server) == ('smiles', 'C[N+](C)(C)C')
    # a name PubChem does not know; a space and a Cyrillic name are quoted
    server = _server({})
    assert pubchem.by_name('нет такого вещества', urlopen=server) is None
    assert '%D0%BD%D0%B5%D1%82%20' in server.asked[0] and len(server.asked) == 2
    assert pubchem.by_name('  ', urlopen=server) is None

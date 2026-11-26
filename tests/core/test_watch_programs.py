"""New versions of the calculation programs (tools/watch_programs.py).

Oracles: the order of versions by their numbers whatever the form of the tag (v6.7.1, release-7-3-0, qe-7.5,
v2026.2); the fields of the «latest release» answers of GitHub (tag_name, published_at) and GitLab (a list, tag_name,
released_at) written here; a check that cannot reach the network says «unknown» and does not call it news.
"""

import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('watch_programs', ROOT / 'tools' / 'watch_programs.py')
watch = importlib.util.module_from_spec(spec)
spec.loader.exec_module(watch)


def test_versions_by_their_numbers():
    assert watch.numbers('release-7-3-0') == (7, 3, 0) and watch.numbers('qe-7.5') == (7, 5)
    assert watch.newer('v6.7.2', '6.7.1') and not watch.newer('v6.7.1', '6.7.1')
    assert watch.newer('v1.10', '1.9.1') and not watch.newer('v1.9.1', '1.10')  # 10 after 9, not by the text
    assert watch.newer('v2026.3', '2026.2') and not watch.newer('v2026.2', '2026.2')
    assert not watch.newer('v1.11.0', '1.11') and watch.newer('v1.11.1', '1.11')  # «.0» is the same version
    assert not watch.newer('nightly', '1.0') and not watch.newer('v2', '')


def test_the_table_names_every_program_with_a_page():
    table = json.loads(watch.TABLE.read_text(encoding='utf-8'))
    assert {'ORCA', 'xtb', 'CREST', 'MOPAC', 'Psi4', 'NWChem', 'Quantum ESPRESSO', 'CP2K', 'Multiwfn'} <= set(table)
    for name, entry in table.items():
        assert entry['checked'] and entry['page'].startswith('http'), name
        assert set(entry.get('source', {})) <= {'github', 'gitlab'}, name


def test_the_report_of_new_same_unknown_and_manual():
    table = {'xtb': {'checked': '6.7.1', 'source': {'github': 'grimme-lab/xtb'}, 'page': 'https://x'},
             'MOPAC': {'checked': '23.2.5', 'source': {'github': 'openmopac/mopac'}, 'page': 'https://m'},
             'Quantum ESPRESSO': {'checked': '7.4', 'source': {'gitlab': 'QEF/q-e'}, 'page': 'https://q'},
             'CP2K': {'checked': '2026.2', 'source': {'github': 'cp2k/cp2k'}, 'page': 'https://c'},
             'NWChem': {'checked': '7.2.0', 'source': {'github': 'nwchemgit/nwchem'}, 'page': 'https://n'},
             'ORCA': {'checked': '6.0.1', 'page': 'https://o'}}
    answers = {
        'https://api.github.com/repos/grimme-lab/xtb/releases/latest': {'tag_name': 'v6.8.0', 'published_at': '2026-12-01T10:00:00Z'},
        'https://api.github.com/repos/openmopac/mopac/releases/latest': {'tag_name': 'v23.2.5', 'published_at': '2026-01-01T00:00:00Z'},
        'https://gitlab.com/api/v4/projects/QEF%2Fq-e/releases?per_page=5': [{'tag_name': 'qe-7.5', 'released_at': '2026-11-01T00:00:00Z'}],
        # a project without releases: the tags, the highest by its numbers
        'https://api.github.com/repos/nwchemgit/nwchem/tags?per_page=30': [{'name': 'v7.2.3-release'}, {'name': 'v7.3.0-release'},
                                                                         {'name': 'nightly'}],
    }
    rows = {r['program']: r for r in watch.report(table, answers.get)}
    assert (rows['xtb']['state'], rows['xtb']['latest'], rows['xtb']['date']) == ('new', 'v6.8.0', '2026-12-01')
    assert rows['MOPAC']['state'] == 'same' and rows['Quantum ESPRESSO']['state'] == 'new'
    assert rows['NWChem']['state'] == 'new' and rows['NWChem']['latest'] == 'v7.3.0-release'
    assert rows['CP2K']['state'] == 'unknown' and rows['CP2K']['latest'] == ''  # no answer is not news
    assert rows['ORCA']['state'] == 'manual'
    text = watch.as_text(list(rows.values()))
    assert 'xtb: 6.7.1 → v6.8.0' in text and 'ORCA (проверено 6.0.1): https://o' in text and 'ВЫШЛА НОВАЯ' in text

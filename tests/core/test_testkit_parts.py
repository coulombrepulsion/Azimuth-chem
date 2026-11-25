"""tools/testkit.py: the set in several pytest processes — the split of the files by time, the reports put together,
how many parts tools/test.py takes."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import testkit  # noqa: E402


def test_the_files_are_split_by_time_and_keep_their_order():
    times = {'a.py': 100, 'b.py': 60, 'c.py': 50, 'd.py': 10}
    parts = testkit.plan(['a.py', 'b.py', 'c.py', 'd.py'], 2, times)
    assert parts == [['a.py', 'd.py'], ['b.py', 'c.py']]  # 110 s and 110 s
    assert sorted(f for p in parts for f in p) == ['a.py', 'b.py', 'c.py', 'd.py']  # each file once


def test_no_empty_part_and_a_new_file_has_a_time():
    assert testkit.plan(['x.py'], 4, {}) == [['x.py']]
    assert testkit.estimate(['new.py'], {}) == testkit.UNKNOWN_SECONDS


def _part(folder, name, status, code, outcomes, tests, junit):
    sub = folder / name
    sub.mkdir()
    summary = {'profile': 'full', 'git_commit': 'abc', 'selected_count': sum(outcomes.values()), 'outcomes': outcomes,
               'collection_seconds': 2.0, 'unfinished': [], 'tests': tests, 'command': ['python']}
    (sub / 'summary.json').write_text(json.dumps(summary), encoding='utf-8')
    (sub / 'junit.xml').write_text('<?xml version="1.0" encoding="utf-8"?><testsuites name="pytest tests">'
                                   f'<testsuite name="pytest" tests="1">{junit}</testsuite></testsuites>',
                                   encoding='utf-8')
    (sub / 'log.txt').write_text(f'log of {name}\n', encoding='utf-8')
    return testkit.Result(name, status, code, 10.0, sub, summary)


def test_the_reports_of_the_parts_become_one(tmp_path):
    import xml.etree.ElementTree as ET

    one = _part(tmp_path, 'part-1', 'passed', 0, {'passed': 3}, [{'nodeid': 'a.py::t', 'seconds': 1}],
                '<testcase name="t"/>')
    two = _part(tmp_path, 'part-2', 'failed', 1, {'passed': 1, 'failed': 1}, [{'nodeid': 'b.py::u', 'seconds': 2}],
                '<testcase name="u"><failure/></testcase>')
    summary = testkit.merge(tmp_path, [one, two], 30.0)
    assert summary['outcomes'] == {'passed': 4, 'failed': 1} and summary['selected_count'] == 5
    assert summary['exit_code'] == 1 and summary['workers'] == 2 and len(summary['tests']) == 2
    assert json.loads((tmp_path / 'summary.json').read_text(encoding='utf-8'))['outcomes']['failed'] == 1
    suites = ET.parse(tmp_path / 'junit.xml').getroot().findall('testsuite')
    assert len(suites) == 2 and len(ET.parse(tmp_path / 'junit.xml').getroot().iter('failure').__next__().tag) > 0
    log = (tmp_path / 'log.txt').read_text(encoding='utf-8')
    assert 'log of part-1' in log and 'log of part-2' in log and log.index('part-1') < log.index('part-2')


def test_describe_names_the_failures_of_every_part(tmp_path):
    (tmp_path / 'log.txt').write_text('== short test summary info ==\nFAILED a.py::t\n'
                                      '== short test summary info ==\nFAILED b.py::u\n', encoding='utf-8')
    said = testkit.describe(testkit.Result('full', 'failed', 1, 5.0, tmp_path, {}))
    assert 'FAILED a.py::t' in said and 'FAILED b.py::u' in said


def test_how_many_parts_tools_test_takes(monkeypatch):
    import test as runner

    monkeypatch.setattr(testkit, 'estimate', lambda files, times=None: 600.0)
    monkeypatch.setattr(testkit, 'jobs_auto', lambda: 6)
    monkeypatch.setattr(runner, 'files_of', lambda paths: {f'tests/f{k}.py' for k in range(20)})
    assert runner.parallel_parts('full', ['tests'], [], None) == 6
    assert runner.parallel_parts('full', ['tests'], [], 1) == 1  # --jobs 1: as before
    assert runner.parallel_parts('full', ['tests'], ['tests/core/test_core.py'], None) == 1  # a path among the options
    assert runner.parallel_parts('quick', ['tests/a.py'], [], None) == 1
    assert runner.parallel_parts('affected', ['tests/a.py', 'tests/b.py'], [], None) == 2  # no more than the files
    assert runner.parallel_parts('full', ['tests'], ['-k', 'crystal and not slow'], None) == 6  # an expression
    monkeypatch.setattr(testkit, 'estimate', lambda files, times=None: 70.0)
    assert runner.parallel_parts('affected', ['tests/a.py', 'tests/b.py'], [], None) == 1  # too short to split

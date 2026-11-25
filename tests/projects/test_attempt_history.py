"""Project.forget_attempt: a calculation taken out of the history of a molecule."""

import pytest

from azimuth import projects
from azimuth.core import Atom, Calculation, Molecule


def _project(tmp_path):
    project = projects.Project.create(tmp_path / 'project')
    water = Molecule('water', (Atom('O', 0, 0, 0), Atom('H', 0.96, 0, 0), Atom('H', -0.24, 0.93, 0)), ())
    entry = project.add(water, Calculation())
    entry['attempts'] = [{'id': 'a', 'state': 'done', 'usable': True, 'kind': 'orca'},
                         {'id': 'b', 'state': 'done', 'usable': True, 'kind': 'xtb'},
                         {'id': 'c', 'state': 'running', 'kind': 'orca'}]
    entry['current'] = projects.current_of(entry)
    return project, entry


def test_a_calculation_leaves_the_history_and_the_current_one_is_found_again(tmp_path):
    project, entry = _project(tmp_path)
    assert entry['current'] == 'b'
    taken = project.forget_attempt(entry['id'], 'b')
    assert taken['id'] == 'b' and [a['id'] for a in entry['attempts']] == ['a', 'c']
    assert entry['current'] == 'a'  # the last one with a result before it


def test_a_running_or_unknown_calculation_stays(tmp_path):
    project, entry = _project(tmp_path)
    with pytest.raises(ValueError):
        project.forget_attempt(entry['id'], 'c')  # still running
    with pytest.raises(ValueError):
        project.forget_attempt(entry['id'], 'nothing')
    assert [a['id'] for a in entry['attempts']] == ['a', 'b', 'c']


def test_the_choice_of_the_user_stays_when_another_one_goes(tmp_path):
    project, entry = _project(tmp_path)
    assert project.choose(entry['id'], 'a') and entry['current'] == 'a'
    project.forget_attempt(entry['id'], 'b')
    assert entry['current'] == 'a' and entry.get('chosen') == 'a'


def test_the_folder_of_a_calculation_goes_only_when_it_is_its_own(tmp_path):
    project, entry = _project(tmp_path)
    own = project.root / 'calculations' / 'water-xtb'
    shared = project.root / 'calculations' / 'shared'
    for folder in (own, shared):
        folder.mkdir(parents=True)
    a, b, c = entry['attempts']
    b['folder'] = project.relative(own)
    a['folder'] = c['folder'] = project.relative(shared)  # one folder of two calculations
    assert projects.attempt_folder(project, b) == own
    assert projects.attempt_folder(project, a) is None  # another calculation uses it
    a['folder'] = project.relative(project.root / 'calculations')
    assert projects.attempt_folder(project, a) is None  # never the folder of all the calculations
    assert projects.attempt_folder(project, {'id': 'x'}) is None  # no folder

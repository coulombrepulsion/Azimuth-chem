"""Molecules taken out of a project (azimuth/projects.py removal, remove_molecules, restore_molecules,
calculation_folders; azimuth/runtime/session.ProjectSession.remove_molecules) — without Qt. The oracle is the project
as written on disk: Project.load after every step, the folders on disk."""

import shutil
from pathlib import Path

import pytest

from azimuth import projects
from azimuth.core import Calculation, read_xyz
from azimuth.runtime.session import ProjectSession
from modules.sextant import batch

DATA = Path(__file__).parents[1] / 'data'
MOPAC_OUTPUT = DATA / 'mopac' / 'h2o_pm7_opt.out'
WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')
CALC = Calculation(method='PM7', task='Оптимизация')


def project_with_queue(tmp_path, count=3):
    """A project with count molecules, each with a finished calculation of its own folder in one imported queue."""
    source = tmp_path / 'source'
    source.mkdir()
    items = []
    for k in range(count):
        folder = source / str(k)
        folder.mkdir()
        shutil.copy2(MOPAC_OUTPUT, folder / 'water.out')
        items.append(batch.BatchItem(f'water {k}', WATER, state='done', folder=str(folder),
                                     output=str(folder / 'water.out')))
    batch.Batch('mopac', CALC, items, source).save()
    project = projects.Project.create(tmp_path / 'project')
    with projects.edit(project.path) as fresh:
        queue_folder = fresh.import_batch(source)
    return project.path, Path(queue_folder)


def test_removed_with_their_records_and_put_back_in_place(tmp_path):
    path, queue_folder = project_with_queue(tmp_path)
    ids = [e['id'] for e in projects.Project.load(path).molecules]
    with projects.edit(path) as project:
        project.data['excluded'] = [ids[1]]
        removed = projects.remove_molecules(project, [ids[1]])
    after = projects.Project.load(path)
    assert [e['id'] for e in after.molecules] == [ids[0], ids[2]]
    assert after.data['excluded'] == []
    assert [p for p, _ in removed] == [1] and removed[0][1]['attempts']  # the record of its calculation goes with it
    assert (queue_folder / '1' / 'water.out').is_file()  # files untouched
    # the queue it was in is still read: its row of the molecule removed is skipped, not an error
    projects.refresh(path)
    with projects.edit(path) as project:
        projects.restore_molecules(project, removed)
    back = projects.Project.load(path)
    assert [e['id'] for e in back.molecules] == ids
    assert back.current(back.entry(ids[1])) is not None  # its result again
    with projects.edit(path) as project:  # put back twice: not doubled
        projects.restore_molecules(project, removed)
    assert len(projects.Project.load(path).molecules) == 3


def test_calculation_folders_are_those_of_the_molecule_only(tmp_path):
    path, queue_folder = project_with_queue(tmp_path)
    project = projects.Project.load(path)
    entry = project.molecules[0]
    folders = projects.calculation_folders(project, [entry])
    assert folders == [(queue_folder / '0').resolve()]
    assert queue_folder.resolve() not in folders  # the whole queue (batch.json, «Анализ») stays
    assert projects.calculation_folders(project, project.molecules) == [
        (queue_folder / str(k)).resolve() for k in range(3)]


def test_refused_while_calculated(tmp_path):
    path, _ = project_with_queue(tmp_path, count=2)
    with projects.edit(path) as project:
        project.molecules[0]['attempts'][0]['state'] = 'running'
    project = projects.Project.load(path)
    with pytest.raises(ValueError, match='считаются'):
        projects.removal(project, [project.molecules[0]['id']])
    with pytest.raises(ValueError):
        projects.removal(project, ['no such id'])
    assert projects.removal(project, [project.molecules[1]['id']])  # the other one may go


def test_molecules_made_for_it_by_a_binding_queue_go_with_it(tmp_path):
    path, _ = project_with_queue(tmp_path, count=2)
    with projects.edit(path) as project:
        owner = project.molecules[0]['id']
        complex_ = project.add(WATER, CALC, 'mopac', 'complex')
        complex_['auxiliary'] = {'role': 'complex', 'of': owner, 'ion': 'Na', 'charge': 1}
        ion = project.add(WATER, CALC, 'mopac', 'ion')
        ion['auxiliary'] = {'role': 'ion', 'of': '', 'ion': 'Na', 'charge': 1}
    with projects.edit(path) as project:
        removed = projects.remove_molecules(project, [owner])
    names = [e['name'] for e in projects.Project.load(path).molecules]
    assert [e['name'] for _, e in removed] == ['water 0', 'complex'] and 'ion' in names


def test_session_forgets_their_edits(tmp_path):
    path, _ = project_with_queue(tmp_path, count=2)
    session = ProjectSession(path)
    first, second = session.ids()
    session.edit_molecule(first, molecule=read_xyz('1\nhe\nHe 0 0 0'))
    revision = session.revision
    removed = session.remove_molecules([first])
    assert session.ids() == [second] and session.dirty() == [] and session.revision == revision + 1
    assert session.save() == []  # nothing of it written back
    assert session.restore_molecules(removed) == [first] and session.ids() == [first, second]

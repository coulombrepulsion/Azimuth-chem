"""The open project — ProjectSession over the JSON project (stage B of PROJECT_RUNTIME_GUIDE.md), scenarios
T01–T04 at the level of the session, without Qt.

Oracles: the rules of the guide §1, §4, §11 — the ids are kept from opening to opening, the name of a project opened
from one file is the name of the file, molecules added to a project of one molecule whose name was not chosen make it
«Новый проект», an edit not saved is what an export gives, the molecules of another project never come into it; what
others wrote into project.qcc (the attempts of a queue) stays after a save.
"""

import shutil
from dataclasses import replace

import pytest

from azimuth import projects
from azimuth.core import Calculation, read_xyz
from azimuth.runtime.contracts import CommandError
from azimuth.runtime.session import MoleculeRecord, ProjectConflict, SessionRegistry

CALC = Calculation()


def atom(symbol, x=0.0):
    return read_xyz(f'1\n{symbol}\n{symbol} {x} 0 0')


def record(symbol, x=0.0, name=''):
    return MoleculeRecord(atom(symbol, x), CALC, name=name or symbol)


def new_project(tmp_path, name='p'):
    return projects.Project.create(tmp_path / name).path


def test_t01_one_file_of_many_structures_is_one_project_with_its_name_order_and_ids(tmp_path):
    registry = SessionRegistry()
    session = registry.open(new_project(tmp_path))
    names = [f'ligand {k:02d}' for k in range(1, 45)]
    ids = session.add_molecules([record('He', k, name) for k, name in enumerate(names)], source_name='Cs_full')
    assert len(ids) == len(set(ids)) == 44 and session.name == 'Cs_full' and session.revision == 1
    again = SessionRegistry().open(session.path)  # opened anew (another start of the program)
    assert again.ids() == ids and [m.name for m in again.snapshot().molecules] == names


def test_t02_molecules_added_keep_the_others_and_name_the_project(tmp_path):
    session = SessionRegistry().open(new_project(tmp_path))
    first = session.add_molecules([record('He')], source_name='water')
    assert session.name == 'water'
    with projects.edit(session.path) as project:  # its history: an attempt recorded by a calculation
        project.record(first[0], 'attempt-1', atom('He'), CALC, 'orca', 'running')
    more = session.add_molecules([record('Ne'), record('Ar')])
    assert session.ids() == first + more and session.name == 'Новый проект'  # one molecule, the name not chosen
    kept = projects.Project.view(session.path).entry(first[0])
    assert [a['id'] for a in kept['attempts']] == ['attempt-1']
    named = SessionRegistry().open(new_project(tmp_path, 'q'))
    named.add_molecules([record('He')], source_name='benzene')
    named.rename('Мои лиганды')
    named.add_molecules([record('Ne')])
    assert named.name == 'Мои лиганды'  # chosen by the user: kept


def test_t03_the_first_molecule_drawn_and_its_edit_survive_the_closing(tmp_path):
    registry = SessionRegistry()
    session = registry.open(new_project(tmp_path))
    ident = session.add_molecules([record('C', name='drawn')])[0]  # the first molecule of the empty tab: kept at once
    session.edit_molecule(ident, molecule=atom('C', 1.25))
    assert session.dirty() == [ident]
    assert registry.close(session.project_id) == [ident]  # closing writes the edit
    reopened = SessionRegistry().open(session.path)
    assert reopened.structure(ident).molecule.atoms[0].x == pytest.approx(1.25) and not reopened.dirty()


def test_t04_an_edit_not_saved_is_exported_and_another_project_is_not(tmp_path):
    registry = SessionRegistry()
    a = registry.open(new_project(tmp_path, 'a'))
    b = registry.open(new_project(tmp_path, 'b'))
    he, ne = a.add_molecules([record('He'), record('Ne')])
    b.add_molecules([record('Xe')])
    a.edit_molecule(ne, molecule=atom('Ne', 1.25))
    exported = a.export_snapshot()
    assert [name for _, name, _ in exported] == ['He', 'Ne'] and exported[1][2].atoms[0].x == pytest.approx(1.25)
    saved, _ = projects.Project.view(a.path).read_structure(projects.Project.view(a.path).entry(ne)['structure'])
    assert saved.atoms[0].x == pytest.approx(0.0)  # exporting does not write the project
    assert [m.atoms[0].symbol for _, _, m in a.export_snapshot([ne])] == ['Ne']
    assert not any(m.atoms[0].symbol == 'Xe' for _, _, m in exported)


def test_t05_a_finished_run_of_a_goes_to_its_attempt_while_b_is_edited(tmp_path):
    # the attempt id comes from the record of the sending (remote_job.prepare_remote → runs), the
    # result is recorded by it — not by the molecule on screen
    from azimuth.runtime import runs

    session = SessionRegistry().open(new_project(tmp_path))
    a, b = session.add_molecules([record('He'), record('Ne')])
    sent = runs.new_submission(name_hint='He')
    with projects.edit(session.path) as project:  # A sent: its attempt, by the id of the sending
        project.record(a, sent.attempt_id, atom('He'), CALC, 'orca', 'running')
    session.edit_molecule(b, molecule=atom('Ne', 2.5))  # meanwhile B is edited (the tab shows B)
    with projects.edit(session.path) as project:  # A ends: written by its attempt id
        project.record(a, sent.attempt_id, atom('He'), CALC, 'orca', 'done')
    assert session.structure(b).molecule.atoms[0].x == pytest.approx(2.5) and session.dirty() == [b]
    session.save()
    view = projects.Project.view(session.path)
    assert [(x['id'], x['state']) for x in view.entry(a)['attempts']] == [(sent.attempt_id, 'done')]
    assert view.entry(b)['attempts'] == []
    assert view.read_structure(view.entry(b)['structure'])[0].atoms[0].x == pytest.approx(2.5)


def test_a_save_keeps_what_others_wrote_and_counts_revisions(tmp_path):
    session = SessionRegistry().open(new_project(tmp_path))
    ident = session.add_molecules([record('He')])[0]
    session.edit_molecule(ident, molecule=atom('He', 0.5))
    with projects.edit(session.path) as project:  # a queue records an attempt meanwhile
        project.record(ident, 'attempt-q', atom('He'), CALC, 'orca', 'running')
    revision = session.revision
    assert session.save(expected_revision=revision) == [ident] and session.revision == revision + 1
    entry = projects.Project.view(session.path).entry(ident)
    assert [a['id'] for a in entry['attempts']] == ['attempt-q']
    assert session.save() == []  # nothing changed: nothing written
    view = session.snapshot().molecules[0]
    assert view.working_revision == view.saved_revision == 1


def test_stale_revisions_are_refused(tmp_path):
    session = SessionRegistry().open(new_project(tmp_path))
    ident = session.add_molecules([record('He')])[0]
    try:
        session.add_molecules([record('Ne')], expected_revision=0)
        raise AssertionError('a stale revision was accepted')
    except CommandError as error:
        assert error.code == 'stale_revision'
    assert session.edit_molecule(ident, expected_revision=0, molecule=atom('He', 1.0)) == 1
    assert session.edit_molecule(ident, molecule=atom('He', 1.0)) == 1  # the same state: not a new revision
    with pytest.raises(CommandError):
        session.edit_molecule(ident, expected_revision=0, molecule=atom('He', 2.0))
    with pytest.raises(CommandError):
        session.edit_molecule(ident, colour='red')


def test_one_session_per_project_and_a_copy_is_a_conflict(tmp_path):
    registry = SessionRegistry()
    path = new_project(tmp_path)
    session = registry.open(path)
    assert registry.open(path.parent) is session and registry.get(session.project_id) is session
    shutil.copytree(path.parent, tmp_path / 'copy')
    with pytest.raises(ProjectConflict):
        registry.open(tmp_path / 'copy')  # the same id from another folder: not silently the same project


def test_the_auxiliary_molecules_are_not_exported(tmp_path):
    session = SessionRegistry().open(new_project(tmp_path))
    session.add_molecules([record('He')])
    with projects.edit(session.path) as project:
        entry = project.add(atom('Na'), replace(CALC, charge=1), 'orca', 'Na+')
        entry['auxiliary'] = {'role': 'ion', 'of': '', 'ion': 'Na', 'charge': 1}
    assert [name for _, name, _ in session.export_snapshot()] == ['He'] and len(session.ids()) == 2


def test_queue_view_has_the_working_state_and_keeps_identity(tmp_path):
    # the rows of a queue of the project are read from the session — an edit not saved is what the queue
    # takes (T04 for a queue); a molecule not edited keeps its object while project.qcc is unchanged
    session = SessionRegistry().open(new_project(tmp_path))
    first, second = session.add_molecules([record('He'), record('Ne')])
    before = session.queue_view()
    assert [row[0] for row in before] == [first, second] and session.queue_view()[1][2].molecule is before[1][2].molecule
    key = session.working_key()
    moved = atom('He', 1.5)
    session.edit_molecule(first, molecule=moved)
    after = session.queue_view()
    assert after[0][2].molecule == moved and session.working_key() != key
    assert after[1][2].molecule is before[1][2].molecule  # untouched
    session.save()
    assert session.working_key() == () and session.queue_view()[0][2].molecule == moved


def test_the_saved_state_is_read_once_and_never_shared(tmp_path):
    # the saved structure of a molecule is kept by its text — read again only when it changed; the labels
    # given to a window are its own copy (a window that changes them never changes what the session keeps)
    from azimuth import core

    session = SessionRegistry().open(new_project(tmp_path))
    (ident,) = session.add_molecules([MoleculeRecord(atom('He'), CALC, name='He', labels={0: 'A'})])
    calls = []
    original = core.validate_constraints
    core.validate_constraints = lambda *a: calls.append(a) or original(*a)
    try:
        first = session.structure(ident)
        again = session.structure(ident)
    finally:
        core.validate_constraints = original
    assert len(calls) == 1 and again == first
    first.labels[0] = 'changed by a window'
    assert session.structure(ident).labels == {0: 'A'}
    with projects.edit(session.path) as project:  # written by someone else: read anew
        entry = project.entry(ident)
        entry['structure'] = project.structure(atom('He', 2.5), CALC)
    assert session.structure(ident).molecule.atoms[0].x == pytest.approx(2.5)


def test_a_held_session_looks_at_the_project_once(tmp_path, monkeypatch):
    # within held(), the project is looked at once for many reads; outside, every read looks again
    session = SessionRegistry().open(new_project(tmp_path))
    ids = session.add_molecules([record('He'), record('Ne'), record('Ar')])
    looks = []
    original = projects.Project.view
    monkeypatch.setattr(projects.Project, 'view', classmethod(lambda cls, path: looks.append(path) or original(path)))
    with session.held():
        for ident in ids:
            session.edit_molecule(ident, molecule=atom(session.structure(ident).molecule.atoms[0].symbol, 0.5))
    assert len(looks) == 1
    session.ids()
    assert len(looks) == 2  # not held any more
    assert session.dirty() == ids

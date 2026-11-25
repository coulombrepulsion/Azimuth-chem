"""The metadata of a project in SQLite and the migration of a project of version 1 (azimuth/project_store.py,
azimuth/projects.py; stage F of PROJECT_RUNTIME_GUIDE.md, scenario T20).

Oracles, apart from the code under test: the JSON a project of version 1 holds (written here by hand, as Azimuth
0.100–0.107 wrote it) compared as a dict with what is read back; the rule of the loader of the old versions («format»
and «version» == 1, else «Неизвестный формат»); the tables read with sqlite3 directly; a failure injected at every
step of the migration and inside a transaction — afterwards the project is either the old one whole or the new one.
"""

import json
import shutil
import sqlite3

import pytest

from azimuth import project_store, projects
from azimuth.core import Calculation, read_xyz

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n')
NEON = read_xyz('1\nneon\nNe 0 0 0\n')


def old_project(tmp_path):
    """A project of version 1 as the versions before 0.108 wrote it: everything in project.qcc."""
    made = projects.Project.create(tmp_path / 'scratch')
    water = made.add(WATER, Calculation(), name='вода')
    made.record(water['id'], 'a1', WATER, Calculation(), 'orca', 'failed', note='первая')
    made.record(water['id'], 'a2', WATER, Calculation(), 'orca', 'running')
    made.add(NEON, Calculation(), name='неон')
    data = json.loads(json.dumps(made.data))
    folder = tmp_path / 'old'
    folder.mkdir()
    (folder / 'calculations').mkdir()
    (folder / projects.MANIFEST).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    return folder / projects.MANIFEST, data


def old_loader_refuses(path):
    data = json.loads(path.read_text(encoding='utf-8'))
    return not (data.get('format') == projects.FORMAT and data.get('version') == 1)


def test_a_new_project_keeps_its_metadata_in_sqlite(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    entry = project.add(WATER, Calculation(), name='вода')
    project.record(entry['id'], 'x1', WATER, Calculation(), 'orca', 'running')
    project.save()
    descriptor = json.loads(project.path.read_text(encoding='utf-8'))
    assert descriptor['version'] == 2 and descriptor['database'] == 'project.sqlite' and 'molecules' not in descriptor
    assert old_loader_refuses(project.path)  # an older Azimuth says «unknown format», it never overwrites it
    with sqlite3.connect(project.root / 'project.sqlite') as db:
        assert db.execute('SELECT id FROM molecules').fetchall() == [(entry['id'],)]
        assert db.execute('SELECT molecule_id, id FROM attempts').fetchall() == [(entry['id'], 'x1')]
    again = projects.Project.load(project.path)
    assert again.storage == 'sqlite' and again.data == project.data


def test_a_project_of_version_1_is_read_as_it_is_and_moved_at_its_first_write(tmp_path):
    path, data = old_project(tmp_path)
    before = path.read_bytes()
    view = projects.Project.view(path)
    assert view.storage == 'json' and view.data == data
    assert path.read_bytes() == before and not (path.parent / 'project.sqlite').exists()  # reading changes nothing
    with projects.edit(path) as project:
        project.data['name'] = 'Лиганды'
    assert (path.parent / project_store.BACKUP).read_bytes() == before  # the old file kept
    assert old_loader_refuses(path)
    moved = projects.Project.load(path)
    assert moved.storage == 'sqlite' and moved.data == dict(data, name='Лиганды')
    assert [a['id'] for a in moved.molecules[0]['attempts']] == ['a1', 'a2'] and moved.molecules[0]['attempts'][0]['note'] == 'первая'


@pytest.mark.parametrize('step', ['database', 'move', 'backup', 'descriptor'])
def test_t20_a_migration_cut_at_any_step_leaves_one_whole_project(tmp_path, monkeypatch, step):
    path, data = old_project(tmp_path)
    real = {'write': project_store.write, 'replace': project_store.os.replace, 'copy2': project_store.shutil.copy2,
            'atomic': projects.atomic_json}

    def broken(*args, **kwargs):
        raise OSError(28, 'No space left on device')

    if step == 'database':
        def half(db, d):  # the database half written, then the failure
            real['write'](db, {**d, 'molecules': d['molecules'][:1]})
            raise OSError(28, 'No space left on device')
        monkeypatch.setattr(project_store, 'write', half)
    elif step == 'move':
        monkeypatch.setattr(project_store.os, 'replace', broken)
    elif step == 'backup':
        monkeypatch.setattr(project_store.shutil, 'copy2', broken)
    else:
        monkeypatch.setattr(projects, 'atomic_json', broken)
    with pytest.raises(OSError):
        with projects.edit(path) as project:
            project.data['name'] = 'новое'
    monkeypatch.setattr(project_store, 'write', real['write'])
    monkeypatch.setattr(project_store.os, 'replace', real['replace'])
    monkeypatch.setattr(project_store.shutil, 'copy2', real['copy2'])
    monkeypatch.setattr(projects, 'atomic_json', real['atomic'])
    after = projects.Project.load(path)
    assert after.storage == 'json' and after.data == data  # the old project, whole — the database left aside is ignored
    with projects.edit(path) as project:  # the next write moves it completely
        project.data['name'] = 'новое'
    done = projects.Project.load(path)
    assert done.storage == 'sqlite' and done.data == dict(data, name='новое')
    assert not (path.parent / project_store.MIGRATING).exists()


def test_t20_a_write_cut_inside_the_transaction_is_rolled_back(tmp_path, monkeypatch):
    project = projects.Project.create(tmp_path / 'p')
    project.add(WATER, Calculation(), name='вода')
    project.save()
    before = projects.Project.load(project.path)
    real_dumps = project_store.json.dumps
    calls = []

    def fails_on_the_second_molecule(value, **kwargs):
        if isinstance(value, dict) and value.get('name') == 'неон':
            calls.append(1)
            raise OSError(5, 'Input/output error')
        return real_dumps(value, **kwargs)

    monkeypatch.setattr(project_store.json, 'dumps', fails_on_the_second_molecule)
    with pytest.raises(OSError):
        with projects.edit(project.path) as fresh:
            fresh.data['name'] = 'другое'
            fresh.add(NEON, Calculation(), name='неон')
    monkeypatch.undo()
    assert calls == [1]
    after = projects.Project.load(project.path)
    assert after.data == before.data and after.generation == before.generation


def test_the_view_follows_the_generation_of_the_database(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    first = projects.Project.view(project.path)
    assert projects.Project.view(project.root) is first
    with projects.edit(project.path) as fresh:
        fresh.add(WATER, Calculation(), name='вода')
    second = projects.Project.view(project.path)
    assert second is not first and len(second.molecules) == 1 and second.generation == first.generation + 1
    with projects.edit(project.path) as fresh:  # nothing changed: nothing written
        fresh.data['name'] = fresh.data['name']
    assert projects.Project.view(project.path) is second and projects.Project.load(project.path).generation == second.generation


def test_a_newer_schema_is_never_overwritten(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    with sqlite3.connect(project.database) as db:
        db.execute("UPDATE meta SET value = '99' WHERE key = 'schema'")
    with pytest.raises(ValueError):
        projects.Project.load(project.path)
    with pytest.raises(ValueError, match='более новой'):
        project_store.write(project.database, project.data)


def test_a_damaged_database_is_said(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    project.database.write_bytes(b'not a database at all' * 10)
    with pytest.raises(ValueError, match='повреждена|версия'):
        projects.Project.load(project.path)


def test_the_copy_has_its_own_database(tmp_path):
    project = projects.Project.create(tmp_path / 'p')
    project.add(WATER, Calculation(), name='вода')
    project.save()
    copy = projects.copy_project(project.path, tmp_path / 'copy')
    with projects.edit(copy) as fresh:
        fresh.add(NEON, Calculation(), name='неон')
    assert len(projects.Project.load(project.path).molecules) == 1  # the original untouched
    assert len(projects.Project.load(copy).molecules) == 2
    shutil.rmtree(tmp_path / 'copy')


# -- the review of 2026-11-09, item 5 — a save writes only what changed --------------------------------
def counting(database):
    """A trigger of the test counts the rows written into attempts and molecules (an oracle outside the code)."""
    with sqlite3.connect(database) as db:
        db.executescript('''
            CREATE TABLE IF NOT EXISTS written (tab TEXT);
            CREATE TRIGGER IF NOT EXISTS a_written AFTER INSERT ON attempts BEGIN INSERT INTO written VALUES ('a'); END;
            CREATE TRIGGER IF NOT EXISTS m_written AFTER INSERT ON molecules BEGIN INSERT INTO written VALUES ('m'); END;
        ''')

    def taken():
        with sqlite3.connect(database) as db:
            rows = db.execute('SELECT tab, count(*) FROM written GROUP BY tab').fetchall()
            db.execute('DELETE FROM written')
        return dict(rows)
    return taken


def big(tmp_path, molecules=6, attempts=5):
    project = projects.Project.create(tmp_path / 'p')
    for k in range(molecules):
        entry = project.add(WATER, Calculation(), name=f'm{k}')
        for a in range(attempts):
            project.record(entry['id'], f'a{k}-{a}', WATER, Calculation(), 'orca', 'failed')
    project.save()
    return project


def test_one_attempt_changed_writes_one_row(tmp_path):
    project = big(tmp_path)
    taken = counting(project.database)
    ident = project.molecules[2]['id']
    with projects.edit(project.path) as fresh:
        fresh.entry(ident)['attempts'][3]['note'] = 'changed'
    assert taken() == {'a': 1}
    assert projects.Project.load(project.path).entry(ident)['attempts'][3]['note'] == 'changed'
    with projects.edit(project.path) as fresh:
        fresh.data['name'] = 'renamed'
    assert taken() == {}  # the document only (meta)
    assert projects.Project.load(project.path).data['name'] == 'renamed'


def test_every_kind_of_change_reads_back_the_same(tmp_path):
    project = big(tmp_path)
    with projects.edit(project.path) as fresh:
        molecules = fresh.data['molecules']
        molecules.insert(0, molecules.pop())  # moved
        del molecules[3]  # removed with its attempts
        molecules[1]['attempts'].pop(0)  # an attempt removed
        molecules[1]['attempts'].reverse()  # the others reordered
        fresh.add(NEON, Calculation(), name='new')
        expected = json.loads(json.dumps(fresh.data))
    assert projects.Project.load(project.path).data == expected
    with sqlite3.connect(project.database) as db:  # no row of a removed molecule or attempt is left behind
        assert db.execute('SELECT count(*) FROM molecules').fetchone()[0] == len(expected['molecules'])
        assert db.execute('SELECT count(*) FROM attempts').fetchone()[0] == sum(
            len(m['attempts']) for m in expected['molecules'])


def test_a_write_in_between_makes_the_next_save_whole(tmp_path):
    project = big(tmp_path)
    view = projects.Project.view(project.path)
    stale = projects.Project(view.path, json.loads(json.dumps(view.data)), view.storage, view.generation)
    stale._stored = view.data
    with projects.edit(project.path) as fresh:  # another write after the stale copy was taken
        fresh.data['molecules'].pop()
    stale.data['name'] = 'stale'
    stale.save()  # the generation moved on: every row written again from what it holds
    again = projects.Project.load(project.path)
    assert again.data == stale.data and len(again.molecules) == 6


def test_an_output_of_a_project_is_found_and_a_draft_of_a_file_is_known(tmp_path):
    # the output of a calculation
    # of a project leads to that project, its molecule and attempt; a draft holding only molecules taken from files is
    # «looked at», a molecule drawn is not
    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n')
    project = projects.Project.create(tmp_path / 'Вода')
    entry = project.add(water, Calculation(), 'orca', name='H2O')
    folder = project.root / 'calculations' / 'run'
    folder.mkdir(parents=True)
    output = folder / 'water.out'
    output.write_text('', encoding='utf-8')
    project.record(entry['id'], 'attempt-1', water, Calculation(), 'orca', 'done', folder, output)
    project.save()
    found = projects.attempt_of_file(output)
    assert found is not None and found[0] == project.path and found[1] == entry['id'] and found[2]['id'] == 'attempt-1'
    stray = tmp_path / 'elsewhere' / 'water.out'
    stray.parent.mkdir()
    stray.write_text('', encoding='utf-8')
    assert projects.attempt_of_file(stray) is None and not projects.looked_at_draft(project.path)
    draft = projects.Project.create(tmp_path / 'Новый проект')
    draft.data.update(draft=True)
    draft.add(water, Calculation(), 'orca', name='H2O · water.out')
    draft.save()
    assert projects.looked_at_draft(draft.path)
    drawn = projects.Project.create(tmp_path / 'Новый проект (2)')
    drawn.data.update(draft=True)
    drawn.add(water, Calculation(), 'orca', name='H2O')
    drawn.save()
    assert not projects.looked_at_draft(drawn.path)



def test_a_calculation_opened_is_current_until_a_newer_one_gives_a_result(tmp_path, monkeypatch):
    # the choice is kept through saving and reopening (refresh); a calculation that gives a result after
    # it becomes current by itself
    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469\n')
    monkeypatch.setattr(projects.batch, 'result_of', lambda kind, text: (-76.0, water, None, None))
    project = projects.Project.create(tmp_path / 'Вода')
    entry = project.add(water, Calculation(), 'orca', name='H2O')

    def done(name):
        folder = project.root / 'calculations' / name
        folder.mkdir(parents=True)
        output = folder / 'water.out'
        output.write_text(name, encoding='utf-8')
        project.record(entry['id'], name, water, Calculation(), 'orca', 'done', folder, output)

    done('first')
    done('second')
    assert entry['current'] == 'second'
    assert project.choose(entry['id'], 'first') and entry['current'] == 'first'
    assert not project.choose(entry['id'], 'nothing') and entry['current'] == 'first'
    project.save()
    project = projects.refresh(project.path)
    entry = project.molecules[0]
    assert entry['current'] == 'first' and project.current(entry)['id'] == 'first'
    done('third')
    assert entry['current'] == 'third' and 'chosen' not in entry


def test_the_calculations_of_a_project_left_on_a_server_are_found_to_be_watched(tmp_path):
    # a single calculation sent to a server whose end was not seen is found with what resume_history needs;
    # one done, one of this computer, one without job.json and one skipped (watched already) are not
    project = projects.Project.create(tmp_path / 'Вода')
    entry = project.add(WATER, Calculation(), 'orca', name='H2O')

    def sent(name, place, state, job=True):
        folder = project.root / 'calculations' / name
        folder.mkdir(parents=True)
        if job:
            (folder / 'job.json').write_text(json.dumps({'server': 'hpc', 'folder': '/scratch/' + name, 'job': '42'}),
                                             encoding='utf-8')
        attempt = project.record(entry['id'], name, WATER, Calculation(), 'orca', state, folder, folder / 'water.out')
        attempt['place'] = place
        return str(folder)

    old = sent('old', 'hpc', 'running')
    new = sent('new', 'hpc', 'sent')
    sent('done', 'hpc', 'done')
    sent('here', '', 'running')
    sent('lost', 'hpc', 'running', job=False)
    found = projects.server_attempts(project)
    assert [rec['folder'] for rec in found] == [new, old]
    assert found[0]['place'] == 'hpc' and found[0]['title'] == 'H2O' and found[0]['kind'] == 'orca'
    assert found[0]['output'].endswith('water.out') and 'method' in found[0]
    assert [rec['folder'] for rec in projects.server_attempts(project, skip={new})] == [old]

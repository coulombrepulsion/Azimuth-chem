"""The records of the calculations of a project in its database (azimuth/runtime/records.py, stage G).

Oracles: the table «records» of project.sqlite read with sqlite3 directly; the files of the folder (none in a project
of version 2, the same files as before outside a project); a second process holding the project (subprocess); a
calculation sent to the fake SLURM server from a folder inside a project — what reached the queue, and that the
watching taken up again from the database gives the same number.
"""

import json
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

from azimuth import project_store, projects
from azimuth.runtime import analysis, records, runs

ROOT = Path(__file__).resolve().parents[2]


def project(tmp_path, name='p'):
    made = projects.Project.create(tmp_path / name)
    folder = made.root / 'calculations' / 'H2O_orca_1'
    folder.mkdir(parents=True)
    return made, folder


def rows(made):
    with sqlite3.connect(made.database) as db:
        return db.execute('SELECT folder, name FROM records ORDER BY name').fetchall()


def test_in_a_project_the_record_is_a_row_not_a_file(tmp_path):
    made, folder = project(tmp_path)
    assert records.owner(folder) == (made.root, 'calculations/H2O_orca_1')
    sub = runs.new_submission(name_hint='H2O')
    runs.write(folder, sub)
    assert runs.read(folder) == sub and not (folder / runs.FILE).exists()
    assert rows(made) == [('calculations/H2O_orca_1', 'submission.json')]
    generation = projects.Project.load(made.path).generation
    records.write(folder, 'job.json', {'job': '7'})
    assert records.read(folder, 'job.json') == {'job': '7'} and records.exists(folder, 'job.json')
    assert projects.Project.load(made.path).generation == generation  # the document of the project unchanged
    runs.write_group(folder, 'g1', [])
    with pytest.raises(FileExistsError):
        runs.write_group(folder, 'g2', [])
    assert runs.read_group(folder)['group_id'] == 'g1'


def test_a_file_of_an_older_version_is_read_and_moves_into_the_database(tmp_path):
    made, folder = project(tmp_path)
    (folder / 'job.json').write_text(json.dumps({'job': '42', 'folder': '~/a'}), encoding='utf-8')
    assert records.read(folder, 'job.json') == {'job': '42', 'folder': '~/a'}  # read as it is
    records.write(folder, 'job.json', {'job': '42', 'folder': '~/a', 'seen': 1})
    assert not (folder / 'job.json').exists() and rows(made) == [('calculations/H2O_orca_1', 'job.json')]
    assert records.read(folder, 'job.json')['seen'] == 1


def test_outside_a_project_or_in_one_of_version_1_the_files_stay(tmp_path):
    loose = tmp_path / 'calc'
    loose.mkdir()
    assert records.owner(loose) is None
    records.write(loose, 'job.json', {'job': '1'})
    assert json.loads((loose / 'job.json').read_text(encoding='utf-8')) == {'job': '1'}
    old = tmp_path / 'old'
    (old / 'calculations' / 'x').mkdir(parents=True)
    (old / 'project.qcc').write_text(json.dumps({'format': projects.FORMAT, 'version': 1, 'id': 'a', 'name': 'old',
                                                 'molecules': [], 'batches': [], 'imports': {}}), encoding='utf-8')
    assert records.owner(old / 'calculations' / 'x') is None


def test_moved_and_copied_projects_keep_their_records(tmp_path):
    made, folder = project(tmp_path)
    records.write(folder, 'project-link.json', {'molecule': 'm1', 'attempt': 'a1'})
    moved = tmp_path / 'moved'
    made.root.rename(moved)
    assert records.read(moved / 'calculations' / 'H2O_orca_1', 'project-link.json')['attempt'] == 'a1'
    copy = projects.copy_project(moved / 'project.qcc', tmp_path / 'copy')
    assert records.read(copy.parent / 'calculations' / 'H2O_orca_1', 'project-link.json')['attempt'] == 'a1'


def test_the_ledger_of_analyses_is_in_the_database(tmp_path):
    made, _ = project(tmp_path)
    book = analysis.Ledger(made.root / 'queue' / 'Анализ')
    art = analysis.Artifact('a1', 'w.fchk', str(tmp_path / 'w.fchk'), 'ab' * 32, 1)
    book.finish(book.begin('qtaim', art))
    assert [r.state for r in book.records()] == ['succeeded'] and not book.path.exists()
    assert rows(made) == [('queue/Анализ', 'analyses.json')]


def test_another_process_writing_the_project_refuses_the_write(tmp_path):
    made, folder = project(tmp_path)
    hold = subprocess.Popen([sys.executable, '-c', f'import sys, time; sys.path.insert(0, {str(ROOT)!r}); '
                             'from azimuth.runtime import writer_lock; '
                             f'assert writer_lock.acquire({str(made.root)!r}); print("held", flush=True); time.sleep(60)'],
                            stdout=subprocess.PIPE, text=True)
    try:
        assert hold.stdout.readline().strip() == 'held'
        with pytest.raises(projects.ProjectLocked):
            records.write(folder, 'job.json', {'job': '1'})
        assert records.read(folder, 'job.json') is None  # nothing written anywhere
    finally:
        hold.kill()
        hold.wait()


@pytest.fixture
def server(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    from tests import fake_server

    (tmp_path / 'ctl').mkdir()
    return fake_server.install(tmp_path, monkeypatch)


def test_a_calculation_of_a_project_on_the_server_keeps_its_records_in_the_database(server, tmp_path):
    from azimuth.core import Calculation, read_xyz
    from modules.sextant import cluster, history
    from modules.sextant.remote import ServerProfile
    from modules.sextant.remote_job import RemoteJob, prepare_remote
    from modules.sextant.ssh import Connection

    made = projects.Project.create(tmp_path / 'p')
    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
    plan = cluster.Plan(processes=6, maxcore=1500, mem_request=None, physical=48, physical_free=40, queued=False)
    spec = prepare_remote(water, Calculation(task='Оптимизация', cores=2), (), made.root / 'calculations', plan)
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    j = RemoteJob(spec, profile, Connection(profile, control_dir=tmp_path / 'ctl'), interval=0.1).start()
    end = time.monotonic() + 20
    while j.poll() is None and time.monotonic() < end:
        time.sleep(0.05)
    assert j.poll() == 0, j.message
    assert not (spec.folder / 'job.json').exists() and not (spec.folder / runs.FILE).exists()
    names = {name for _, name in rows(made)}
    assert names == {'job.json', 'submission.json'}
    assert runs.read(spec.folder).state == 'accepted'
    rec = {'folder': str(spec.folder), 'output': str(spec.output), 'kind': 'orca', 'place': 'serv3', 'state': 'running'}
    assert history.remote_info(rec)['job'] == '101' and history.state_of(rec) == 'finished'
    assert project_store.get_record(made.database, f'calculations/{spec.folder.name}', 'job.json')['job'] == '101'


def test_a_queue_of_a_project_is_a_row_and_batch_json_its_derived_view(tmp_path):
    # the list «Очереди» and opening batch.json find the file; the program reads the row
    from azimuth.core import Calculation, read_xyz
    from modules.sextant import batch

    made, _ = project(tmp_path)
    folder = made.root / 'calculations' / 'queue'
    folder.mkdir()
    he = read_xyz('1\nhe\nHe 0 0 0')
    queue = batch.Batch('orca', Calculation(), [batch.BatchItem('He', he)], folder, extra={'origin': {'project': 'p', 'molecule': 'm'}})
    queue.save()
    assert ('calculations/queue', 'batch.json') in rows(made)
    assert json.loads((folder / 'batch.json').read_text(encoding='utf-8'))['items'][0]['name'] == 'He'
    (folder / 'batch.json').write_text(json.dumps({'stale': True}), encoding='utf-8')  # a derived view gone wrong
    again = batch.Batch.load(folder)
    assert [i.name for i in again.items] == ['He'] and again.extra['origin'] == {'project': 'p', 'molecule': 'm'}
    loose = tmp_path / 'loose'
    loose.mkdir()
    batch.Batch('orca', Calculation(), [batch.BatchItem('He', he)], loose).save()  # outside a project: the file only
    assert batch.Batch.load(loose).items[0].name == 'He'

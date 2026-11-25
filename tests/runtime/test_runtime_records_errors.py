"""An unreadable database of a project is said, never taken for «no record» (azimuth/project_store.py,
azimuth/runtime/records.py; the external review of 2026-11-09, item 1).

Oracles: a file of random bytes named project.sqlite (not a database), a database removed, a database locked by
another connection for longer than the timeout, a database of 0.108.0 without the table «records» (made here with
sqlite3 by hand), and the files next to the calculation — they must be neither read instead nor changed.
"""

import json
import sqlite3

import pytest

from azimuth import project_store, projects
from azimuth.runtime import records, runs
from modules.sextant import history


def project(tmp_path):
    made = projects.Project.create(tmp_path / 'p')
    folder = made.root / 'calculations' / 'c1'
    folder.mkdir(parents=True)
    (folder / 'batch.json').write_text(json.dumps({'status': 'old'}), encoding='utf-8')
    return made, folder


def test_a_damaged_database_is_an_error_not_the_old_file(tmp_path):
    made, folder = project(tmp_path)
    made.database.write_bytes(b'\x00not a database\x00' * 64)
    before = (folder / 'batch.json').read_bytes()
    with pytest.raises(project_store.ProjectDatabaseError, match='не читается'):
        records.read(folder, 'batch.json')
    with pytest.raises(project_store.ProjectDatabaseError):
        records.exists(folder, 'job.json')
    with pytest.raises(project_store.ProjectDatabaseError):
        runs.read(folder)  # not «nothing was sent»
    with pytest.raises(project_store.ProjectDatabaseError):
        records.write(folder, 'job.json', {'job': '1'})
    assert (folder / 'batch.json').read_bytes() == before and not (folder / 'job.json').exists()


def test_a_missing_database_of_a_project_of_version_2_is_an_error(tmp_path):
    made, folder = project(tmp_path)
    made.database.unlink()
    with pytest.raises(project_store.ProjectDatabaseError, match='project.sqlite'):
        records.read(folder, 'batch.json')
    with pytest.raises(project_store.ProjectDatabaseError):
        records.write(folder, 'job.json', {'job': '1'})
    assert not made.database.exists()  # not made again with the records alone


def test_a_database_busy_longer_than_its_timeout_is_an_error(tmp_path, monkeypatch):
    made, folder = project(tmp_path)
    records.write(folder, 'job.json', {'job': '5'})
    real = project_store.connect

    def impatient(db, readonly=False):  # 50 ms instead of 10 s of waiting
        connection = real(db, readonly)
        connection.execute('PRAGMA busy_timeout = 50')
        return connection

    monkeypatch.setattr(project_store, 'connect', impatient)
    holder = sqlite3.connect(made.database, isolation_level=None)
    holder.execute('BEGIN EXCLUSIVE')
    try:
        with pytest.raises(project_store.ProjectDatabaseError):
            records.read(folder, 'job.json')
    finally:
        holder.execute('ROLLBACK')
        holder.close()
    assert records.read(folder, 'job.json') == {'job': '5'}


def test_no_row_in_a_sound_database_keeps_the_import_and_the_row_wins(tmp_path):
    made, folder = project(tmp_path)
    assert records.read(folder, 'batch.json') == {'status': 'old'}  # the import of a file of an older version
    records.write(folder, 'batch.json', {'status': 'new'}, mirror=True)
    (folder / 'batch.json').write_text(json.dumps({'status': 'stale'}), encoding='utf-8')
    assert records.read(folder, 'batch.json') == {'status': 'new'}  # the row, never the file


def test_a_database_of_0_108_0_without_the_table_is_supported(tmp_path):
    made, folder = project(tmp_path)
    with sqlite3.connect(made.database) as db:
        db.execute('DROP TABLE records')
    assert records.read(folder, 'batch.json') == {'status': 'old'}
    records.write(folder, 'job.json', {'job': '9'})  # the table is made at the first write
    assert records.read(folder, 'job.json') == {'job': '9'} and not (folder / 'job.json').exists()


def test_the_history_says_unreadable_and_guesses_nothing(tmp_path):
    made, folder = project(tmp_path)
    made.database.write_bytes(b'garbage' * 100)
    rec = {'folder': str(folder), 'output': str(folder / 'x.out'), 'kind': 'orca', 'place': 'serv3', 'state': 'failed'}
    assert history.state_of(rec) == 'unreadable' and history.describe('unreadable') == 'база проекта не читается'
    with pytest.raises(project_store.ProjectDatabaseError):
        history.remote_info(rec)

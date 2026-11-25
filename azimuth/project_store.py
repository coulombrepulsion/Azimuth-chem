"""The metadata of a project in SQLite, the calculations as ordinary files (docs/architecture/PROJECT_RUNTIME_GUIDE.md,
§5).

§1 PURPOSE
    project.qcc was the whole project in one JSON file, rewritten whole at every change. The guide: one source of the
    metadata with transactions, a migration that survives an interruption, a backup. The files of the calculations
    stay files; only the metadata (the document of the project, its molecules, their attempts) moves here.
§2 RULES
    1. Layout: «project.qcc» becomes a small descriptor {format, version: 2, database: «project.sqlite»} — Azimuth
    before
       0.108 refuses it with «Неизвестный формат проекта» (it never writes it); «project.sqlite» holds the metadata.
    2. Tables: meta(key, value) — 'schema' (SCHEMA), 'generation' (grows with every write), 'document' (JSON of the
       fields of the project other than its molecules); molecules(id, position, data) — an entry without its attempts;
       attempts(molecule_id, id, position, data). A write replaces the rows in one transaction (BEGIN IMMEDIATE …
       COMMIT): a reader sees the old or the new project, never a mix; a failed write is rolled back.
    3. journal_mode=DELETE (not WAL: the guide, §5 — a project folder may be copied or moved; one file plus a journal
       that SQLite removes at the commit), synchronous=FULL, a busy timeout for a reader during a write.
    4. read(db) -> (data, generation) in one transaction; generation(db) — for the cache of Project.view.
    5. backup(db, target) — SQLite Backup API (a consistent copy even while it is open), for «Сохранить как…».
    6. Migration of a project of version 1 (projects.Project.save, at its first write): the database is written whole
       into «project.sqlite.migrating», moved over project.sqlite, the JSON kept as «project.qcc.v1-backup», and only
       then project.qcc replaced by the descriptor (atomically). An interruption before that last step leaves the old
       project.qcc whole and in force (the database left behind is rewritten at the next write); after it — the new
       project. Never a mix (T20).
§3 INTERFACE
    DATABASE, BACKUP, SCHEMA, STORAGE_VERSION; descriptor(fmt) -> dict; is_descriptor(data) -> bool;
    write(db, data, previous=None, generation=None) -> generation (only the rows that differ from previous); read(db) ->
    (data, generation); generation(db) -> int; backup(db, target);
    migrate(manifest, data) (projects.py calls it; atomic_json given by the caller).
    Put_record(db, folder, name, data, create=True), get_record(db, folder, name) — the table records (folder
    relative to the project, name of the record, JSON, time) of azimuth/runtime/records.py.
§4 TESTS tests/projects/test_project_store.py.
"""

from __future__ import annotations

import json
import os
import shutil
import sqlite3
from pathlib import Path

DATABASE = 'project.sqlite'
BACKUP = 'project.qcc.v1-backup'
SCHEMA = 1
STORAGE_VERSION = 2
MIGRATING = DATABASE + '.migrating'


def descriptor(fmt):
    return {'format': fmt, 'version': STORAGE_VERSION, 'database': DATABASE,
            'note': 'The metadata of this project are in project.sqlite (Azimuth 0.108 or later).'}


def is_descriptor(data):
    return isinstance(data, dict) and data.get('version') == STORAGE_VERSION and data.get('database') == DATABASE


def connect(db, readonly=False):
    db = Path(db)
    if readonly:
        connection = sqlite3.connect(f'{db.resolve().as_uri()}?mode=ro', uri=True, timeout=10, isolation_level=None)
    else:
        connection = sqlite3.connect(str(db), timeout=10, isolation_level=None)
        connection.execute('PRAGMA journal_mode=DELETE')
        connection.execute('PRAGMA synchronous=FULL')
    return connection


def _init(connection):
    connection.executescript('''
        CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS molecules (id TEXT PRIMARY KEY, position INTEGER NOT NULL, data TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS attempts (molecule_id TEXT NOT NULL, id TEXT NOT NULL, position INTEGER NOT NULL,
                                             data TEXT NOT NULL, PRIMARY KEY (molecule_id, id));
        CREATE TABLE IF NOT EXISTS records (folder TEXT NOT NULL, name TEXT NOT NULL, data TEXT NOT NULL,
                                            changed TEXT NOT NULL, PRIMARY KEY (folder, name));
    ''')


def _meta(connection, key, default=None):
    row = connection.execute('SELECT value FROM meta WHERE key = ?', (key,)).fetchone()
    return row[0] if row else default


def _split(data):
    """{molecule id: (position, row without attempts, {attempt id: (position, attempt)})}, the document."""
    molecules = {}
    for position, entry in enumerate(data.get('molecules', [])):
        row = {k: v for k, v in entry.items() if k != 'attempts'}
        attempts = {a['id']: (k, a) for k, a in enumerate(entry.get('attempts', []))}
        molecules[entry['id']] = (position, row, attempts)
    return molecules, {k: v for k, v in data.items() if k != 'molecules'}


def write(db, data, previous=None, generation=None):
    """The metadata of the project in one transaction; the new generation.
    Previous — the data as the database holds them now (read at the
    generation `generation`): only the rows that differ are written (a changed attempt, a moved molecule) and the
    removed ones deleted; when the database is no longer at that generation (another write came between) or nothing
    is known, every row is written again, as before. Either way one transaction: all or nothing."""
    connection = connect(db)
    try:
        _init(connection)
        connection.execute('BEGIN IMMEDIATE')
        try:
            schema = int(_meta(connection, 'schema', SCHEMA))
            if schema > SCHEMA:
                raise ValueError('Проект записан более новой версией Азимута.')
            now = int(_meta(connection, 'generation', 0))
            molecules, document = _split(data)
            if previous is not None and generation is not None and now == generation:
                old, old_document = _split(previous)
            else:
                connection.execute('DELETE FROM attempts')
                connection.execute('DELETE FROM molecules')
                old, old_document = {}, None
            for ident in old.keys() - molecules.keys():
                connection.execute('DELETE FROM attempts WHERE molecule_id = ?', (ident,))
                connection.execute('DELETE FROM molecules WHERE id = ?', (ident,))
            for ident, (position, row, attempts) in molecules.items():
                before = old.get(ident)
                if before is None or before[0] != position or before[1] != row:
                    connection.execute('INSERT OR REPLACE INTO molecules VALUES (?, ?, ?)',
                                       (ident, position, json.dumps(row, ensure_ascii=False)))
                previous_attempts = before[2] if before is not None else {}
                for gone in previous_attempts.keys() - attempts.keys():
                    connection.execute('DELETE FROM attempts WHERE molecule_id = ? AND id = ?', (ident, gone))
                changed = [(ident, aid, k, json.dumps(a, ensure_ascii=False)) for aid, (k, a) in attempts.items()
                           if previous_attempts.get(aid) != (k, a)]
                connection.executemany('INSERT OR REPLACE INTO attempts VALUES (?, ?, ?, ?)', changed)
            values = [('schema', str(SCHEMA)), ('generation', str(now + 1))]
            if document != old_document:
                values.append(('document', json.dumps(document, ensure_ascii=False)))
            connection.executemany('INSERT OR REPLACE INTO meta VALUES (?, ?)', values)
            connection.execute('COMMIT')
        except BaseException:
            connection.execute('ROLLBACK')
            raise
        return now + 1
    finally:
        connection.close()


def read(db):
    """(data, generation) — the project as one JSON-like dict, read in one transaction."""
    db = Path(db)
    if not db.is_file():
        raise ValueError('Нет базы данных проекта (project.sqlite).')
    connection = connect(db, readonly=True)
    try:
        connection.execute('BEGIN')
        try:
            schema = int(_meta(connection, 'schema', 0))
            if schema != SCHEMA:
                raise ValueError('Неизвестная версия базы данных проекта.')
            generation = int(_meta(connection, 'generation', 0))
            data = json.loads(_meta(connection, 'document', '{}'))
            molecules = []
            attempts = {}
            for molecule_id, data_text in connection.execute('SELECT molecule_id, data FROM attempts '
                                                             'ORDER BY molecule_id, position'):
                attempts.setdefault(molecule_id, []).append(json.loads(data_text))
            for ident, data_text in connection.execute('SELECT id, data FROM molecules ORDER BY position'):
                entry = json.loads(data_text)
                entry['attempts'] = attempts.get(ident, [])
                molecules.append(entry)
        finally:
            connection.execute('COMMIT')
    except sqlite3.DatabaseError as exc:
        raise ValueError(f'База данных проекта повреждена: {exc}') from exc
    finally:
        connection.close()
    data['molecules'] = molecules
    return data, generation


def generation(db):
    try:
        connection = connect(db, readonly=True)
    except sqlite3.Error:
        return -1
    try:
        return int(_meta(connection, 'generation', 0))
    except sqlite3.Error:
        return -1
    finally:
        connection.close()


def backup(db, target):
    """A consistent copy of the database (SQLite Backup API), written whole before it takes the name target."""
    target = Path(target)
    temporary = target.with_name(target.name + '.copying')
    if temporary.exists():
        temporary.unlink()
    source = connect(db, readonly=True)
    try:
        copy = sqlite3.connect(str(temporary))
        try:
            source.backup(copy)
        finally:
            copy.close()
    finally:
        source.close()
    os.replace(temporary, target)


def migrate(manifest, data, atomic_json, fmt):
    """§2.6: a project of version 1 (manifest — its project.qcc, data — what it holds now) moved into SQLite."""
    manifest = Path(manifest)
    root = manifest.parent
    temporary = root / MIGRATING
    for leftover in (temporary, root / (MIGRATING + '-journal')):
        if leftover.exists():
            leftover.unlink()
    write(temporary, data)
    os.replace(temporary, root / DATABASE)
    if not (root / BACKUP).exists() and manifest.is_file():
        try:
            old = json.loads(manifest.read_text(encoding='utf-8-sig'))
        except (OSError, ValueError):
            old = None
        if not is_descriptor(old):
            shutil.copy2(manifest, root / BACKUP)
    atomic_json(manifest, descriptor(fmt))


# -- the records of the calculations of the project (azimuth/runtime/records.py) --------------------
class ProjectDatabaseError(ValueError):
    """Project.sqlite cannot be read or written (damaged, missing, busy too long) — never «no record»: the
    caller says it; a file of the same name next to the calculation is not taken instead of the database."""

    def __init__(self, db, cause):
        self.db, self.cause = str(db), cause
        from azimuth.i18n import tr

        super().__init__(tr('База данных проекта не читается ({}): {}. Последние сведения о расчётах сейчас недоступны; '
                            'закройте другие окна Азимута с этим проектом, при повреждении — восстановите папку проекта '
                            'из резервной копии.').format(db, cause))


def _has_records(connection):
    return connection.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'records'").fetchone() is not None


def put_record(db, folder, name, data, create=True):
    """One record (a JSON value) of the calculation folder `folder` (relative to the project) — replaced whole in one
    transaction; create=False — refused (FileExistsError) when it is there already. The generation of the project does
    not change: the records are not the document of the project. The database must exist (never made here
    beside a project whose database is gone); a failure of SQLite → ProjectDatabaseError."""
    from datetime import datetime, timezone

    if not Path(db).is_file():
        raise ProjectDatabaseError(db, _missing())
    try:
        connection = connect(db)
    except sqlite3.Error as exc:
        raise ProjectDatabaseError(db, exc) from exc
    try:
        _init(connection)
        connection.execute('BEGIN IMMEDIATE')
        try:
            if not create and connection.execute('SELECT 1 FROM records WHERE folder = ? AND name = ?',
                                                 (folder, name)).fetchone():
                raise FileExistsError(f'{folder}/{name}: written once')
            connection.execute('INSERT OR REPLACE INTO records VALUES (?, ?, ?, ?)', (
                folder, name, json.dumps(data, ensure_ascii=False),
                datetime.now(timezone.utc).isoformat(timespec='seconds')))
            connection.execute('COMMIT')
        except BaseException:
            connection.execute('ROLLBACK')
            raise
    except sqlite3.Error as exc:
        raise ProjectDatabaseError(db, exc) from exc
    finally:
        connection.close()


def get_record(db, folder, name):
    """The record, or None — no row, or a database of 0.108.0 without the table «records» yet (both: the file may be
    imported). A database that is missing, damaged or busy → ProjectDatabaseError, never None."""
    if not Path(db).is_file():
        raise ProjectDatabaseError(db, _missing())
    try:
        connection = connect(db, readonly=True)
    except sqlite3.Error as exc:
        raise ProjectDatabaseError(db, exc) from exc
    try:
        if not _has_records(connection):
            return None
        row = connection.execute('SELECT data FROM records WHERE folder = ? AND name = ?', (folder, name)).fetchone()
    except sqlite3.Error as exc:
        raise ProjectDatabaseError(db, exc) from exc
    finally:
        connection.close()
    if row is None:
        return None
    try:
        return json.loads(row[0])
    except ValueError as exc:
        raise ProjectDatabaseError(db, f'запись {folder}/{name} повреждена') from exc


def _missing():
    from azimuth.i18n import tr

    return tr('файла project.sqlite нет')


def peek(db, names=3):
    """2026-11-13 (project_picker, «Открыть проект…»): (the document, the number of molecules, the names of the first
    ones) — read-only, no structure parsed, for a list of many projects."""
    connection = connect(db, readonly=True)
    try:
        document = json.loads(_meta(connection, 'document', '{}'))
        count = connection.execute('SELECT count(*) FROM molecules').fetchone()[0]
        first = [json.loads(row[0]).get('name') or '' for row in
                 connection.execute('SELECT data FROM molecules ORDER BY position LIMIT ?', (int(names),))]
    finally:
        connection.close()
    return document, count, first

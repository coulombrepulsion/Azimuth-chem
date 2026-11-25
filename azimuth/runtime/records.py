"""The records of a calculation — in the database of its project, or a file next to it
(docs/architecture/PROJECT_RUNTIME_GUIDE.md,
§5: the old batch.json, job.json and project-link.json are only a source of import).

§1 PURPOSE
    The record of a sending (submission.json), of a job on the server (job.json), of a group (group.json), the link of
    a calculation to its molecule (project-link.json) and the ledger of analyses (analyses.json) were files in the
    folders of the calculations, beside the database of the project: two sources of the metadata of one project.
§2 RULES
    1. owner(folder): the project the folder belongs to — the nearest parent (the folder itself included) whose
       project.qcc is a descriptor of version 2 (azimuth/project_store.py); the key of the record is the folder
       relative to the project (moving or copying the project keeps it valid).
    2. In a project: the record is a row of the table «records» of project.sqlite, replaced whole in one transaction;
       the file of the same name is then removed — the database is the only source. A file found without a row (made
       by Azimuth, or while the project was still of version 1) is read as it is and moves into the
       database at the next write (import).
    3. Outside a project (a calculation of a tab without a project; a project of version 1): the file, written to a
       temporary file and moved over it, as before.
    4. Another process writes the project (azimuth/runtime/writer_lock.py) → writing is refused (ProjectLocked); reading
       is allowed.
    5. once=True (the composition of a group): refused (FileExistsError) when the record is there.
    6. mirror=True (batch.json of a queue): in a project the row is the source, and the file is written after
       it as a derived view (the guide, §5) — the list «Очереди» and opening
       batch.json find the queue on the disk; a file left behind by a failed write is never read before the row.
    7. A database that cannot be read or written (missing, damaged, busy for longer than its timeout) raises
       project_store.ProjectDatabaseError — never taken for «no record», so a stale file is never read instead.
§3 INTERFACE NAMES; owner(folder) -> (root Path, key str) | None; read(folder, name) -> value | None;
    write(folder, name, value, once=False, mirror=False); exists(folder, name) -> bool.
§4 TESTS tests/runtime/test_runtime_records.py; the fake-server tests of tests/sextant (outside a project: files).
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from azimuth import project_store

MANIFEST = 'project.qcc'
NAMES = ('submission.json', 'job.json', 'group.json', 'project-link.json', 'analyses.json', 'batch.json')


def owner(folder):
    if not folder:
        return None
    path = Path(folder).resolve()
    for root in (path, *path.parents):
        manifest = root / MANIFEST
        if manifest.is_file():
            try:
                data = json.loads(manifest.read_text(encoding='utf-8-sig'))
            except (OSError, ValueError):
                return None
            if project_store.is_descriptor(data):  # also when its database is gone — said, not the files
                return root, path.relative_to(root).as_posix()
            return None  # a project of version 1, or a molecule file: the files
    return None


def _file(folder, name):
    try:
        return json.loads((Path(folder) / name).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def read(folder, name):
    """A database that cannot be read raises project_store.ProjectDatabaseError — the file of the same name is
    read only when the database answers that it has no such record (the import of §2.2), never instead of it."""
    found = owner(folder)
    if found is not None:
        value = project_store.get_record(found[0] / project_store.DATABASE, found[1], name)
        if value is not None:
            return value
    return _file(folder, name)  # outside a project, or not imported yet


def exists(folder, name):
    return read(folder, name) is not None


def write(folder, name, value, once=False, mirror=False):
    """mirror (batch.json): in a project the file is kept too, written after the row — a derived view for
    what finds queues on the disk (the list «Очереди», opening batch.json); read() takes the row."""
    found = owner(folder)
    if found is None or mirror:
        if found is not None:
            _put(found, folder, name, value, once)
        target = Path(folder) / name
        if once and target.exists():
            raise FileExistsError(f'{target}: written once')
        temporary = target.with_name(target.name + '.tmp')
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=1), encoding='utf-8')
        os.replace(temporary, target)
        return
    _put(found, folder, name, value, once)
    for leftover in (Path(folder) / name, Path(folder) / (name + '.tmp')):
        try:
            leftover.unlink()
        except FileNotFoundError:
            pass
        except OSError:
            pass  # the database holds it; a file left is never read before the row


def _put(found, folder, name, value, once):
    root, key = found
    from azimuth import projects

    other = projects.locked_by(root / MANIFEST)
    if other is not None:
        raise projects.ProjectLocked(f'The project is written by another process ({other.get("host", "?")}, '
                                     f'{other.get("pid", "?")}).')
    if once and _file(folder, name) is not None:
        raise FileExistsError(f'{Path(folder) / name}: written once')
    project_store.put_record(root / project_store.DATABASE, key, name, value, create=not once)

"""One writer of a project across processes: a lock between processes, a check of the owner, an explicit read-only
mode in a second window (docs/architecture/PROJECT_RUNTIME_GUIDE.md §5; scenario T19).

§1 PURPOSE
    Two windows of Azimuth (two processes) could open one project and both write project.qcc: the later save silently
    replaced what the other wrote, and a calculation of the project could be resumed — and its result recorded — twice.
§2 RULES
    1. The writer holds an operating-system lock on «.az-writer.lock» in the folder of the project (fcntl.flock on
       macOS and Linux, msvcrt.locking on Windows) for as long as the project is open; the system releases it when the
       process ends, also when it crashes — a lock is never «stale».
    2. Next to it «.az-writer.json» says who holds it (host, process, since) — for the message only; the lock itself
       is the proof.
    3. In one process the lock is counted (two sessions, two registries of the tests): released when the last one
       lets it go.
    4. holder(folder): None when this process holds it or nobody does; else what .az-writer.json says.
§3 INTERFACE acquire(folder) -> bool; release(folder); holder(folder) -> dict | None; LOCK, INFO.
§4 TESTS tests/runtime/test_runtime_writer_lock.py (a second process holds the project).
§5 NOTES
    ASSUMPTION: the folder of the project is on a local file system (the guide, §5: cloud folders and network shares
    are not supported for an open project); flock on a network share may lock nothing.
"""

from __future__ import annotations

import json
import os
import socket
import threading
from datetime import datetime, timezone
from pathlib import Path

LOCK = '.az-writer.lock'
INFO = '.az-writer.json'

_held = {}  # folder → [file descriptor, count]
_guard = threading.Lock()


def _key(folder):
    return str(Path(folder).resolve())


def _try_lock(fd):
    try:
        if os.name == 'nt':
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return True
    except OSError:
        return False


def _unlock(fd):
    try:
        if os.name == 'nt':
            import msvcrt

            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(fd, fcntl.LOCK_UN)
    except OSError:
        pass


def acquire(folder):
    """True when this process is now (or already was) the writer of the project in folder."""
    key = _key(folder)
    with _guard:
        if key in _held:
            _held[key][1] += 1
            return True
        try:
            fd = os.open(os.path.join(key, LOCK), os.O_RDWR | os.O_CREAT, 0o644)
        except OSError:
            return False
        if not _try_lock(fd):
            os.close(fd)
            return False
        _held[key] = [fd, 1]
    info = {'host': socket.gethostname(), 'pid': os.getpid(),
            'since': datetime.now(timezone.utc).isoformat(timespec='seconds')}
    try:
        temporary = Path(key) / (INFO + '.tmp')
        temporary.write_text(json.dumps(info), encoding='utf-8')
        os.replace(temporary, Path(key) / INFO)
    except OSError:
        pass
    return True


def release(folder):
    key = _key(folder)
    with _guard:
        entry = _held.get(key)
        if entry is None:
            return
        entry[1] -= 1
        if entry[1] > 0:
            return
        _held.pop(key)
        fd = entry[0]
    _unlock(fd)
    os.close(fd)


def holder(folder):
    """None — this process writes the project, or nobody does; else who holds it (host, pid, since)."""
    key = _key(folder)
    with _guard:
        if key in _held:
            return None
    path = os.path.join(key, LOCK)
    if not os.path.exists(path):
        return None
    try:
        fd = os.open(path, os.O_RDWR)
    except OSError:
        return None
    try:
        if _try_lock(fd):
            _unlock(fd)
            return None
    finally:
        os.close(fd)
    try:
        return json.loads((Path(key) / INFO).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {'host': '?', 'pid': '?', 'since': ''}

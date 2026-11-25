"""Atomic, process-owned recovery copies of molecular projects.

Contract: Session.write replaces one complete JSON snapshot, never a user's project.
A failed write leaves the previous snapshot intact. Session.claim returns None for
an active writer (including another window in this process). Locks have no age
timeout: a long calculation is not a dead process. close(keep=True) releases the
lock but retains the snapshot; close() removes only this session's snapshot.
Files are limited to 64 MiB. No pickle, execution or automatic opening of paths.
An unchanged snapshot is not written again (its hash is kept, the file is not read back).
set_aside(path) moves a damaged snapshot to «damaged/»; clean_temporary(directory) removes
the temporary files of a write cut off by a crash (older than TEMPORARY_AGE seconds).
Recovery stores project data, not calculation processes, results or crystal cells.
"""

import hashlib
import json
import os
import time
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QLockFile, QStandardPaths

FORMAT = 'azimuth-recovery'
VERSION = 1
MAX_BYTES = 64 * 1024 * 1024
TEMPORARY_AGE = 3600  # s: a write takes milliseconds; an older «.recovery-*» was cut off


def recovery_dir():
    """An explicit override, isolated settings directory, or the OS local data folder."""
    if path := os.environ.get('AZIMUTH_RECOVERY_DIR'):
        return Path(path)
    if path := os.environ.get('AZIMUTH_SETTINGS_FILE'):
        return Path(path).parent / 'recovery'
    return Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.GenericDataLocation)) / 'Azimuth' / 'recovery'


class Session:
    def __init__(self, directory, name=None):
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True)
        name = name or uuid.uuid4().hex
        if len(name) != 32 or any(c not in '0123456789abcdef' for c in name):
            raise ValueError('Invalid recovery session name')
        self.path = directory / (name + '.json')
        self.lock = QLockFile(str(directory / (name + '.lock')))
        self.lock.setStaleLockTime(0)
        self.written = None  # the hash of the last snapshot written by this session
        self.active = self.lock.tryLock(0)
        if not self.active:
            raise OSError('Recovery session is locked')

    @classmethod
    def claim(cls, path):
        try:
            return cls(Path(path).parent, Path(path).stem)
        except (OSError, ValueError):
            return None

    def write(self, entries):
        if not self.active:
            raise OSError('Recovery session is closed')
        payload = json.dumps({'format': FORMAT, 'version': VERSION, 'entries': entries},
                             ensure_ascii=False, allow_nan=False).encode('utf-8')
        if len(payload) > MAX_BYTES:
            raise ValueError('Recovery snapshot exceeds 64 MiB')
        digest = hashlib.sha256(payload).hexdigest()
        if digest == self.written and self.path.exists():
            return
        fd, temporary = tempfile.mkstemp(prefix='.recovery-', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'wb') as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
            self.written = digest
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)

    def read(self):
        with self.path.open('rb') as handle:
            payload = handle.read(MAX_BYTES + 1)
        if len(payload) > MAX_BYTES:
            raise ValueError('Recovery snapshot exceeds 64 MiB')
        data = json.loads(payload)
        if (not isinstance(data, dict) or data.get('format') != FORMAT
                or data.get('version') != VERSION or not isinstance(data.get('entries'), list)):
            raise ValueError('Unknown recovery format')
        return data['entries']

    def close(self, keep=False):
        if not self.active:
            return
        try:
            if not keep:
                self.path.unlink(missing_ok=True)
        finally:
            self.lock.unlock()
            self.active = False


def set_aside(path):
    """A snapshot that cannot be read goes to «damaged/» next to it (it is not offered at every start); the new path."""
    path = Path(path)
    target = path.parent / 'damaged'
    target.mkdir(parents=True, exist_ok=True)
    new = target / path.name
    k = 1
    while new.exists():
        new = target / f'{path.stem}-{k}{path.suffix}'
        k += 1
    os.replace(path, new)
    return new


def clean_temporary(directory, now=None):
    """The «.recovery-*» files of writes cut off by a crash; the number removed."""
    now = time.time() if now is None else now
    removed = 0
    for path in Path(directory).glob('.recovery-*'):
        try:
            if now - path.stat().st_mtime > TEMPORARY_AGE:
                path.unlink()
                removed += 1
        except OSError:
            pass
    return removed

"""Which content a derived result was made from, and whether it is still current.

§1 PURPOSE
    The runs of Multiwfn kept for the session, the surfaces of Compass and a few small caches were keyed by the path
    of the file with its size and time of change. A file replaced by another with the same size and time (a copy
    that keeps the time: cp -p, shutil.copy2, an archive unpacked) gave the old result for the new content; a project
    moved elsewhere lost its keys with its paths.
§2 RULES
    1. fingerprint(path) -> (SHA-256 hex, size), or None when the file cannot be read: the content, not the path.
    2. It is remembered while the file is provably the same: the same resolved path, size, time of change, inode and —
       on macOS and Linux — ctime (the system sets it at every write; no copy can keep it). On Windows the ctime is
       the time of creation, so there the content is hashed every time.
    3. source(path, **parameters) -> a dict for a sidecar of a saved result: the name, SHA-256 and size of the
       source, the version of Azimuth, the time, the parameters of the analysis. write_source(target, path, **p)
       writes it next to target as «<target>.source.json»; a failure to write it never fails the result.
    4. The file is stat'ed again after it is read; changed meanwhile (size, time of change, inode, ctime) — read once
       more; changed again — None: a file being written is no source of a reproducible result (and so no key of a
       cache). source() then says 'stable': False with no SHA-256.
    5. A sidecar not written is no longer silent: it goes to errors.log (azimuth/crash_report.record) with the target
       and the reason; the result itself stays.
§3 INTERFACE fingerprint(path); source(path, **parameters) -> dict; write_source(target, path, **parameters).
§4 TESTS tests/runtime/test_runtime_provenance.py.
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_seen = {}
_guard = threading.Lock()
LIMIT = 256


def _identity(path, info):
    ctime = info.st_ctime_ns if os.name != 'nt' else None
    return str(path), info.st_size, info.st_mtime_ns, info.st_ino, ctime


def _hash(resolved):
    digest = hashlib.sha256()
    with open(resolved, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint(path):
    try:
        resolved = Path(path).resolve()
        info = resolved.stat()
    except OSError:
        return None
    identity = _identity(resolved, info)
    if os.name != 'nt':
        with _guard:
            hit = _seen.get(identity)
        if hit is not None:
            return hit
    for _attempt in range(2):  # §2.4: the content read is the content of one moment, or nothing
        try:
            digest = _hash(resolved)
            after = resolved.stat()
        except OSError:
            return None
        if _identity(resolved, after) == identity:
            break
        identity, info = _identity(resolved, after), after
    else:
        return None
    found = (digest, info.st_size)
    if os.name != 'nt':
        with _guard:
            if len(_seen) >= LIMIT:
                _seen.pop(next(iter(_seen)))
            _seen[identity] = found
    return found


def source(path, **parameters):
    from azimuth import __version__

    found = fingerprint(path)
    return {'source': Path(path).name, 'sha256': found[0] if found else None, 'size': found[1] if found else None,
            'stable': found is not None, 'azimuth': __version__,
            'made': datetime.now(timezone.utc).isoformat(timespec='seconds'),
            'parameters': {k: v for k, v in parameters.items()}}


def write_source(target, path, **parameters):
    try:
        side = Path(str(target) + '.source.json')
        side.write_text(json.dumps(source(path, **parameters), ensure_ascii=False, indent=1, default=str),
                        encoding='utf-8')
        return side
    except OSError as exc:
        note('provenance', f'{target}: the record of its source was not written ({exc})')
        return None


def note(kind, text):
    """§2.5: a failure of a helping record, kept in errors.log — never raised, never a failure of the result."""
    try:
        from azimuth import crash_report

        crash_report.record(kind, text)
    except Exception:  # noqa: BLE001 — the journal is a help too
        pass

"""One writer of a project across processes, a copy with its own id (stage F; T19, T21 of
PROJECT_RUNTIME_GUIDE.md §13). T20 (a save or a migration cut halfway) — tests/projects/test_project_store.py.

Oracles: a second Python process (subprocess) that holds the project — what the operating system says of the lock,
not what this process believes; the ids written in the original and in the copy.
"""

import subprocess
import sys
import time
from pathlib import Path

import pytest

from azimuth import projects
from azimuth.core import Calculation, read_xyz
from azimuth.runtime import writer_lock
from azimuth.runtime.session import MoleculeRecord, SessionRegistry

ROOT = Path(__file__).resolve().parents[2]
HOLD = '''
import os, sys, time
sys.path.insert(0, {root!r})
from azimuth.runtime import writer_lock
assert writer_lock.acquire({folder!r})
print('held', os.getpid(), flush=True)
time.sleep(60)
'''


def atom(symbol, x=0.0):
    return read_xyz(f'1\n{symbol}\n{symbol} {x} 0 0')


def holding(folder):
    """Another process of «Azimuth» with the project open. Its pid is the one it reports: on Windows the python.exe of a
    venv is a launcher that starts the interpreter as its child, so Popen.pid is not the process holding the lock
    (the first run on Windows)."""
    process = subprocess.Popen([sys.executable, '-c', HOLD.format(root=str(ROOT), folder=str(folder))],
                               stdout=subprocess.PIPE, text=True)
    word, pid = process.stdout.readline().split()
    assert word == 'held'
    process.holder_pid = int(pid)
    return process


def test_t19_a_second_process_reads_and_never_writes(tmp_path):
    path = projects.Project.create(tmp_path / 'p').path
    other = holding(path.parent)
    try:
        info = writer_lock.holder(path.parent)
        assert info is not None and info['pid'] == other.holder_pid
        session = SessionRegistry().open(path)
        assert session.read_only is not None and session.read_only['pid'] == other.holder_pid
        before = path.read_bytes()
        with pytest.raises(projects.ProjectLocked, match='другом окне'):
            session.add_molecules([MoleculeRecord(atom('He'), Calculation())])
        with pytest.raises(projects.ProjectLocked):
            with projects.edit(path) as project:
                project.data['name'] = 'changed'
        assert path.read_bytes() == before
    finally:
        other.kill()
        other.wait()
    # the other process ended (even killed): the lock goes with it — never stale. Windows lets the lock of a killed
    # process go a moment after its end (on a busy computer later than wait() returns: Windows check 2026-11-25)
    deadline = time.monotonic() + 5
    while writer_lock.holder(path.parent) is not None and time.monotonic() < deadline:
        time.sleep(0.05)
    assert writer_lock.holder(path.parent) is None
    registry = SessionRegistry()
    fresh = registry.open(path)
    assert fresh.read_only is None
    fresh.add_molecules([MoleculeRecord(atom('Ne'), Calculation())])
    registry.close(fresh.project_id)
    assert writer_lock.holder(path.parent) is None


def test_one_process_counts_its_holds(tmp_path):
    folder = tmp_path / 'q'
    folder.mkdir()
    assert writer_lock.acquire(folder) and writer_lock.acquire(folder)
    writer_lock.release(folder)
    other = subprocess.run([sys.executable, '-c', f'import sys; sys.path.insert(0, {str(ROOT)!r}); '
                            f'from azimuth.runtime import writer_lock; print(writer_lock.acquire({str(folder)!r}))'],
                           capture_output=True, text=True, timeout=30)
    assert other.stdout.strip() == 'False'  # still held here
    writer_lock.release(folder)
    deadline = time.monotonic() + 5
    while writer_lock.holder(folder) is not None and time.monotonic() < deadline:
        time.sleep(0.05)
    assert writer_lock.holder(folder) is None


def test_t21_a_moved_project_keeps_its_id_and_a_copy_gets_its_own(tmp_path):
    path = projects.Project.create(tmp_path / 'p').path
    with projects.edit(path) as project:
        ident = project.add(atom('He'), Calculation(), name='He')['id']
        project.record(ident, 'attempt-1', atom('He'), Calculation(), 'orca', 'failed', path.parent / 'calculations' / 'a1')
    original = projects.Project.view(path).data['id']
    moved = tmp_path / 'elsewhere' / 'p'
    moved.parent.mkdir()
    path.parent.rename(moved)
    assert projects.Project.view(moved / projects.MANIFEST).data['id'] == original
    copy = projects.copy_project(moved / projects.MANIFEST, tmp_path / 'copy')
    data = projects.Project.load(copy).data
    assert data['id'] != original and data['copied_from'] == original
    view = projects.Project.view(copy)
    assert [e['id'] for e in view.molecules] == [ident] and view.molecules[0]['attempts'][0]['id'] == 'attempt-1'
    registry = SessionRegistry()
    a, b = registry.open(moved / projects.MANIFEST), registry.open(copy)  # both open: no conflict
    assert a.project_id == original and b.project_id == data['id']
    assert not (copy.parent / writer_lock.LOCK).exists() or writer_lock.holder(copy.parent) is None
    with pytest.raises(ValueError):
        projects.copy_project(copy, copy.parent / 'inside')
    registry.close(a.project_id)
    registry.close(b.project_id)

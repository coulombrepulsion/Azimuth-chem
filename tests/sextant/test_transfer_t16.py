"""T16 of docs/architecture/PROJECT_RUNTIME_GUIDE.md §13: a cut transfer never gives a file declared complete; it is
resumed with a check.

The fake SLURM server (tests/fake_server.py): cut_downloads — scp brings half of a file and the connection is reset;
short_downloads — half of a file and scp says nothing. Oracles: the bytes of the file on «the server», the files in
the folder of the calculation here, the message of the job.
"""

import os

import pytest

from modules.sextant import remote_job
from tests.sextant.test_remote_job import job, server  # noqa: F401 — the fake server and a job on it

NORMAL = 'FINAL SINGLE POINT ENERGY -76.4\n****ORCA TERMINATED NORMALLY****\n'


def ended_there(server, j):
    """The calculation on «the server» ended: its output and a big file of orbitals are there; the job knows its number."""
    there = server / 'home' / 'azimuth' / 'calculations' / j.spec.folder.name
    there.mkdir(parents=True, exist_ok=True)
    (there / j.spec.output.name).write_text(NORMAL, encoding='utf-8')
    gbw = there / j.spec.output.with_suffix('.gbw').name
    gbw.write_bytes(os.urandom(3 * 1024 * 1024))  # 3 MB
    j.job_id = '7'
    return gbw


@pytest.fixture
def quick(monkeypatch):
    monkeypatch.setattr(remote_job, 'RETRY', (0.01, 0.02, 0.03))


def test_t16_a_cut_transfer_is_taken_again_and_only_the_whole_file_is_ready(server, tmp_path, quick):
    j = job(tmp_path)
    gbw = ended_there(server, j)
    j.spec.output.write_text('', encoding='utf-8')
    (server / 'cut_downloads').write_text('1')  # the first download is cut halfway
    j._finish()
    here = j.spec.folder / gbw.name
    assert j.code == 0 and j.state == 'finished' and 'Не все файлы' not in j.message
    assert here.read_bytes() == gbw.read_bytes()  # whole, taken again
    assert not list(j.spec.folder.glob(remote_job.TRANSFER + '*'))  # no part left


def test_t16_a_short_copy_scp_did_not_notice_is_found_by_its_size(server, tmp_path, quick):
    j = job(tmp_path)
    gbw = ended_there(server, j)
    (server / 'short_downloads').write_text('1')
    j._finish()
    assert (j.spec.folder / gbw.name).read_bytes() == gbw.read_bytes()


def test_t16_a_file_that_never_comes_whole_is_not_declared_ready(server, tmp_path, quick):
    j = job(tmp_path)
    gbw = ended_there(server, j)
    (server / 'short_downloads').write_text('100')
    j._finish()
    # the output copied while it ran says the calculation ended normally; the orbitals are not there, and it is said
    assert j.state == 'finished' and 'Не все файлы' in j.message and gbw.name in j.message
    assert not (j.spec.folder / gbw.name).exists()
    assert not list(j.spec.folder.glob(remote_job.TRANSFER + '*'))
    # a file of the folder is never replaced by a part: the same download of a file already here leaves it whole
    (server / 'short_downloads').write_text('0')
    (tmp_path / 'again').mkdir()
    j2 = job(tmp_path / 'again')
    ended_there(server, j2)
    j2._finish()
    whole = (j2.spec.folder / gbw.name).read_bytes()
    (server / 'short_downloads').write_text('100')
    with pytest.raises(Exception):
        j2._download_verified([gbw.name])
    assert (j2.spec.folder / gbw.name).read_bytes() == whole

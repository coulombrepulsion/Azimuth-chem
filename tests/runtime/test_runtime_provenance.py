"""Derived results keyed by the content of their source (azimuth/runtime/provenance.py; the roadmap of
2026-11-09, B).

Oracles: hashlib.sha256 of the bytes computed here; a file replaced by another of the same size with its time of
change set back (os.utime — what cp -p, shutil.copy2 and unpacking do); a file moved to another folder."""

import hashlib
import json
import os
import shutil

from azimuth.runtime import provenance
from modules.spectrum.wavefunction import field_tables, multiwfn


def same_size_same_time(path, text):
    info = path.stat()
    path.write_text(text, encoding='utf-8')
    os.utime(path, ns=(info.st_atime_ns, info.st_mtime_ns))
    assert path.stat().st_size == info.st_size and path.stat().st_mtime_ns == info.st_mtime_ns


def test_the_content_not_the_path_and_time(tmp_path):
    a = tmp_path / 'w.molden'
    a.write_text('[Molden Format] AAAA', encoding='utf-8')
    first = provenance.fingerprint(a)
    assert first == (hashlib.sha256(a.read_bytes()).hexdigest(), a.stat().st_size)
    same_size_same_time(a, '[Molden Format] BBBB')
    assert provenance.fingerprint(a) != first  # replaced: a new key although size and time are the old ones
    moved = tmp_path / 'elsewhere' / 'w.molden'
    moved.parent.mkdir()
    shutil.copy2(a, moved)
    assert provenance.fingerprint(moved) == provenance.fingerprint(a)  # moved: the same key
    assert provenance.fingerprint(tmp_path / 'none') is None


def test_the_cache_of_multiwfn_follows_the_content(tmp_path):
    path = tmp_path / 'x.fchk'
    path.write_text('content one', encoding='utf-8')
    key = multiwfn._cache_key('multiwfn', path, ('7', '0'), None, ())
    same_size_same_time(path, 'content two')
    assert multiwfn._cache_key('multiwfn', path, ('7', '0'), None, ()) != key
    assert multiwfn._cache_key('multiwfn', path, ('7', '1'), None, ()) != multiwfn._cache_key(
        'multiwfn', path, ('7', '0'), None, ())  # another parameter of the analysis — another key
    copy = tmp_path / 'moved' / 'x.fchk'
    copy.parent.mkdir()
    shutil.copy2(path, copy)
    assert multiwfn._cache_key('multiwfn', copy, ('7', '0'), None, ()) == multiwfn._cache_key(
        'multiwfn', path, ('7', '0'), None, ())


def test_a_saved_output_names_its_source(tmp_path):
    wfn = tmp_path / 'calc' / 'water.molden.input'
    wfn.parent.mkdir()
    wfn.write_text('[Molden Format]\n', encoding='utf-8')
    saved = field_tables.save_output(wfn, 'topology', 'the output of Multiwfn')
    side = json.loads(saved.with_name(saved.name + '.source.json').read_text(encoding='utf-8'))
    assert side['source'] == 'water.molden.input' and side['sha256'] == hashlib.sha256(wfn.read_bytes()).hexdigest()
    assert side['parameters'] == {'analysis': 'topology'} and side['azimuth']


def test_the_check_of_a_mopac_aux_follows_its_content(tmp_path):
    import pytest

    pytest.importorskip('PySide6')  # modules/spectrum/workspace is a part of the window
    from modules.spectrum.workspace import aux_has_orbitals

    aux = tmp_path / 'm.aux'
    aux.write_text('START OF MOPAC FILE\n EIGENVECTORS[0001]=\n', encoding='utf-8')
    assert aux_has_orbitals(aux) is True
    same_size_same_time(aux, 'START OF MOPAC FILE\n NOVECTORSHER[0001]=\n')
    assert aux_has_orbitals(aux) is False


# -- a file changed while it is read, a record of the source not written --
def test_a_file_changed_while_it_is_read_is_no_source(tmp_path, monkeypatch):
    path = tmp_path / 'growing.out'
    path.write_text('first part\n', encoding='utf-8')
    real = provenance._hash
    writes = []

    def hash_while_written(resolved):  # the program still writes its output while it is hashed
        digest = real(resolved)
        if len(writes) < 5:
            with open(resolved, 'a', encoding='utf-8') as f:
                f.write('more\n')
            writes.append(1)
        return digest

    monkeypatch.setattr(provenance, '_hash', hash_while_written)
    assert provenance.fingerprint(path) is None and len(writes) == 2  # read twice, changed both times
    side = provenance.source(path, analysis='x')
    assert side['stable'] is False and side['sha256'] is None


def test_a_file_changed_once_while_read_is_read_again(tmp_path, monkeypatch):
    path = tmp_path / 'done.out'
    path.write_text('first part\n', encoding='utf-8')
    real = provenance._hash
    writes = []

    def once(resolved):
        digest = real(resolved)
        if not writes:
            with open(resolved, 'a', encoding='utf-8') as f:
                f.write('the end\n')
            writes.append(1)
        return digest

    monkeypatch.setattr(provenance, '_hash', once)
    found = provenance.fingerprint(path)
    assert found == (hashlib.sha256(path.read_bytes()).hexdigest(), path.stat().st_size)  # the content as it stands


def test_a_record_of_the_source_not_written_goes_to_the_journal(tmp_path, monkeypatch):
    from azimuth import crash_report

    noted = []
    monkeypatch.setattr(crash_report, 'record', lambda kind, text: noted.append((kind, text)))
    source = tmp_path / 'w.molden'
    source.write_text('x', encoding='utf-8')
    target = tmp_path / 'no-such-folder' / 'out.txt'
    assert provenance.write_source(target, source) is None
    assert noted and noted[0][0] == 'provenance' and 'out.txt' in noted[0][1]

"""The ledger of analyses and the copies they read (azimuth/runtime/analysis.py).

Oracles: hashlib.sha256 of the bytes (computed here, apart), the states of §2 of the module (running → succeeded |
failed), the rule «written whole» (no temporary file left, a cut file reads as none)."""

import hashlib

from azimuth.runtime import analysis, runs


def test_a_snapshot_is_a_copy_with_its_digest(tmp_path):
    source = tmp_path / 'calc' / 'w.molden.input'
    source.parent.mkdir()
    source.write_bytes(b'[Molden Format]\n' * 100)
    art = analysis.snapshot(source, 'a1', tmp_path / 'copy')
    assert art.name == 'w.molden.input' and art.sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert art.size == len(source.read_bytes()) and (tmp_path / 'copy' / 'w.molden.input').read_bytes() == source.read_bytes()
    source.write_bytes(b'changed')
    assert analysis.sha256(art.path) == art.sha256


def test_the_ledger_keeps_every_analysis_whole(tmp_path):
    book = analysis.Ledger(tmp_path / 'q')
    assert book.records() == []
    art = analysis.Artifact('a1', 'w.fchk', str(tmp_path / 'w.fchk'), 'ab' * 32, 10)
    one = book.begin('qtaim', art)
    two = book.begin('qtaim', art)
    assert one.analysis_id != two.analysis_id and [r.state for r in book.records()] == ['running', 'running']
    book.finish(one)
    book.finish(two, 'no points')
    states = {r.analysis_id: (r.state, r.error) for r in book.records()}
    assert states == {one.analysis_id: ('succeeded', ''), two.analysis_id: ('failed', 'no points')}
    assert not list((tmp_path / 'q').glob('*.tmp'))
    (tmp_path / 'q' / analysis.LEDGER).write_text('[{cut', encoding='utf-8')
    assert book.records() == []


def test_the_attempt_of_a_folder(tmp_path):
    assert analysis.attempt_of(tmp_path / 'local-calc') == 'folder:local-calc'
    sent = runs.new_submission()
    runs.write(tmp_path, sent)
    assert analysis.attempt_of(tmp_path) == sent.attempt_id

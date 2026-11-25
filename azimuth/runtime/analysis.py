"""Analyses of the results apart from the queue of calculations (stage E of
docs/architecture/PROJECT_RUNTIME_GUIDE.md, §10 «Результаты, плотность и QTAIM до конца пакета»).

§1 PURPOSE
    QTAIM of a queue («QTAIM для всех») ran Multiwfn on the file of orbitals in the folder of each calculation as it was
    at that moment: a molecule calculated again meanwhile changed the file under the analysis, and nothing said which
    calculation a table belonged to; a failed Multiwfn was only a row of the summary. The guide: an analysis is a job
    of its own, bound to the result and the artifact chosen when it was planned; its failure never makes the
    calculation failed; one molecule ready is analysed without waiting for the others (T15, T17, T18).
§2 RULES
    1. snapshot(path, attempt_id, into): the artifact copied (same name) into a folder of the analysis and its SHA-256
       and size kept — the analysis reads the copy, so a calculation repeated meanwhile changes nothing of it (T18).
    2. A record of every analysis (AnalysisRecord: analysis id, kind, attempt id, the name and digest of the artifact,
       state queued → running → succeeded | failed, the error, the times) in the ledger «analyses.json» of the folder
       of the queue — written atomically, read back by the tables and by the user. The state of the calculation (the
       row of the queue) is never written by an analysis (T17).
    3. attempt_of(folder): the attempt id of the record of the sending (azimuth/runtime/runs.py) when the calculation
       went to a server, else «folder:<name>» — the folder of a local calculation is made once per attempt.
§3 INTERFACE
    LEDGER; Artifact(attempt_id, name, path, sha256, size); snapshot(path, attempt_id, into) -> Artifact;
    AnalysisRecord(...); Ledger(folder): .records() -> [AnalysisRecord], .begin(kind, artifact) -> AnalysisRecord,
    .finish(record, error='') -> AnalysisRecord; attempt_of(folder) -> str; sha256(path) -> hex.
§4 TESTS tests/runtime/test_runtime_analysis.py; tests/spectrum/test_batch_qtaim.py (T15, T17, T18).
"""

from __future__ import annotations

import hashlib
import shutil
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from azimuth.runtime.contracts import new_id

LEDGER = 'analyses.json'
STATES = ('queued', 'running', 'succeeded', 'failed')


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


def sha256(path):
    digest = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True)
class Artifact:
    attempt_id: str
    name: str
    path: str  # the copy the analysis reads
    sha256: str
    size: int


def snapshot(path, attempt_id, into):
    """The file copied into `into` under its own name (Multiwfn and the readers see the same name); its digest."""
    source = Path(path)
    target = Path(into)
    target.mkdir(parents=True, exist_ok=True)
    copy = target / source.name
    shutil.copy2(source, copy)
    return Artifact(attempt_id, source.name, str(copy), sha256(copy), copy.stat().st_size)


def attempt_of(folder):
    from azimuth.runtime import runs

    sent = runs.read(folder) if folder else None
    return sent.attempt_id if sent is not None else f'folder:{Path(folder).name}'


@dataclass(frozen=True)
class AnalysisRecord:
    analysis_id: str
    kind: str
    attempt_id: str
    artifact: str
    sha256: str
    state: str = 'queued'
    error: str = ''
    started: str = ''
    finished: str = ''


class Ledger:
    """The analyses of one queue (or one folder), in analyses.json; every change written whole."""

    def __init__(self, folder):
        self.folder = Path(folder)
        self.path = self.folder / LEDGER

    def records(self):
        from azimuth.runtime import records  # the database of the project of the folder, else the file

        data = records.read(self.folder, LEDGER)
        if not isinstance(data, list):
            return []
        fields = AnalysisRecord.__dataclass_fields__
        return [AnalysisRecord(**{k: d[k] for k in fields if k in d}) for d in data if isinstance(d, dict)]

    def _write(self, records_):
        from azimuth.runtime import records

        self.folder.mkdir(parents=True, exist_ok=True)
        records.write(self.folder, LEDGER, [asdict(r) for r in records_])

    def _put(self, record):
        records = [r for r in self.records() if r.analysis_id != record.analysis_id]
        self._write(records + [record])
        return record

    def begin(self, kind, artifact):
        return self._put(AnalysisRecord(new_id(), kind, artifact.attempt_id, artifact.name, artifact.sha256,
                                        'running', started=_now()))

    def finish(self, record, error=''):
        return self._put(replace(record, state='failed' if error else 'succeeded', error=error, finished=_now()))

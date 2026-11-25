"""Sextant at the start: a queue and a server calculation left unfinished are offered again.

Oracles: the states of the files themselves — a queue with a job waiting is not done (batch.Batch.done), a history
record with job.json of a server and no end in its output is 'server' (history.state_of); the records inside
the folder of the queue are its own jobs (one question for the queue, not one per job); «Нет» is remembered per folder.
"""

import json
from pathlib import Path

import pytest

from azimuth.core import Calculation, read_xyz
from modules.sextant import batch, history, unfinished
from modules.sextant.batch import OPEN_KEY

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')


class Settings(dict):
    def value(self, key, default=None):
        return self.get(key, default)

    def setValue(self, key, value):
        self[key] = value

    def remove(self, key):
        self.pop(key, None)


def server_record(folder, title='вода', when='2026-11-07T10:00:00'):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'job.json').write_text(json.dumps({'job': '77', 'folder': '~/azimuth/x'}), encoding='utf-8')
    (folder / 'water.out').write_text('still running', encoding='utf-8')
    return {'when': when, 'place': 'serv3', 'kind': 'orca', 'title': title, 'folder': str(folder),
            'output': str(folder / 'water.out'), 'state': 'running'}


def queue(folder, place='server', states=('done', 'running', 'waiting')):
    folder.mkdir(parents=True, exist_ok=True)
    items = [batch.BatchItem(f'c{k}', WATER, state=s, folder=str(folder / f'j{k}')) for k, s in enumerate(states)]
    q = batch.Batch('orca', Calculation(), items, folder, place=place, source='CREST')
    q.save()
    return q


def test_the_queue_and_the_jobs_left(tmp_path):
    settings = Settings()
    assert unfinished.pending(settings) == {'batch': None, 'jobs': []}
    q = queue(tmp_path / 'queue')
    own = server_record(tmp_path / 'queue' / 'j1')  # a job of the queue: asked with the queue
    lone = server_record(tmp_path / 'single', 'бензол')
    done = server_record(tmp_path / 'done')
    (tmp_path / 'done' / 'water.out').write_text('****ORCA TERMINATED NORMALLY****', encoding='utf-8')
    history.save(settings, [own, lone, done])
    settings[OPEN_KEY] = str(q.folder)
    found = unfinished.pending(settings)
    assert found['batch'][0] == str(q.folder) and found['batch'][1].counts()['done'] == 1
    assert [r['title'] for r in found['jobs']] == ['бензол']
    unfinished.dismiss(settings, str(q.folder))
    unfinished.dismiss(settings, lone['folder'])
    assert unfinished.pending(settings) == {'batch': None, 'jobs': []}
    assert unfinished.dismissed(settings) == [lone['folder'], str(q.folder)]


def test_a_finished_or_unreadable_queue_is_not_offered(tmp_path):
    settings = Settings()
    settings[OPEN_KEY] = str(queue(tmp_path / 'q', states=('done', 'failed')).folder)
    assert unfinished.pending(settings)['batch'] is None
    settings[OPEN_KEY] = str(tmp_path / 'nothing')
    assert unfinished.pending(settings)['batch'] is None
    settings[unfinished.DISMISSED_KEY] = 'not json'
    assert unfinished.dismissed(settings) == []


def test_the_check_at_the_start(tmp_path, monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication, QMessageBox

    from azimuth.app import Studio

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    window = Studio(probe_machine=False)
    try:
        q = queue(tmp_path / 'queue', place='local', states=('done', 'waiting'))
        window.preferences.setValue(OPEN_KEY, str(q.folder))
        history.save(window.preferences, [server_record(tmp_path / 'single', 'бензол')])
        calls = []
        monkeypatch.setattr(window.batch_tool, 'resume_batch', lambda folder=None: calls.append(('batch', folder)))
        monkeypatch.setattr(window.run_tool, 'resume_history', lambda rec: calls.append(('job', rec['title'])))
        shown = []
        window.unfinished.shown.connect(shown.append)
        answers = iter([QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No])
        monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: next(answers))
        assert window.unfinished.check() == 'batch' and calls == [('batch', str(q.folder))]
        assert shown == ['sextant'] and window.stack.currentIndex() == 1
        assert window.unfinished.check() is None  # «Нет» for the queue: remembered
        # a single calculation on a server is not asked about — its project takes it up when opened
        assert window.unfinished.check() is None and len(calls) == 1
    finally:
        window.preferences.remove(OPEN_KEY)
        window.preferences.remove(history.KEY)
        window.preferences.remove(unfinished.DISMISSED_KEY)
        window.recovery.finish()
        window.close()
        window.deleteLater()
        assert app is not None


def test_the_rest_sent_before_the_exit(tmp_path, monkeypatch):
    # every calculation not sent yet goes to the server, each after the one before (the job running first)
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication

    from azimuth.app import Studio
    from modules.sextant import cluster, remote_job

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    window = Studio(probe_machine=False)
    try:
        q = queue(tmp_path / 'queue', place='server', states=('done', 'running', 'waiting', 'waiting'))
        running = Path(q.items[1].folder)
        running.mkdir()
        (running / 'job.json').write_text(json.dumps({'job': '200'}), encoding='utf-8')
        plan = cluster.Plan(processes=36, maxcore=1000, mem_request=None, physical=48, physical_free=40, queued=False)
        q.kind, q.calc = 'mopac', Calculation(method='PM7', task='Оптимизация')
        q.remote = ('profile', 'connection', plan, '')
        chain = []

        def submitted(spec, profile, connection, after=None):
            chain.append(after)
            return str(201 + len(chain) - 1)
        monkeypatch.setattr(remote_job, 'submit', submitted)
        with window.at_place('server'):
            window.batch = q
        assert window.batch_tool.server_queue_left() is q
        with window.at_place('server'):
            assert window.batch_tool.send_rest_before_exit(q) == 2
        assert chain == ['200', '201'] and [i.state for i in q.items] == ['done', 'running', 'sent', 'sent']
        assert window.batch_tool.server_queue_left() is None
        assert [i.state for i in batch.Batch.load(q.folder).items] == ['done', 'running', 'sent', 'sent']
        assert all('THREADS=36' in (Path(i.folder) / f'{k:02d}.mop').read_text()
                   for k, i in enumerate(q.items[2:], 3))
    finally:
        with window.at_place('server'):
            window.batch = None
        window.recovery.finish()
        window.close()
        window.deleteLater()
        assert app is not None


def test_a_server_queue_is_sent_at_once(tmp_path, monkeypatch):
    # every waiting calculation prepared and sent in one go, run by one SLURM job; nothing is
    # left for the exit
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication

    from azimuth.app import Studio
    from modules.sextant import cluster, remote_job

    app = QApplication.instance() or QApplication([])
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    window = Studio(probe_machine=False)
    try:
        q = queue(tmp_path / 'queue', place='server', states=('done', 'waiting', 'waiting', 'waiting'))
        plan = cluster.Plan(processes=8, maxcore=1000, mem_request=None, physical=48, physical_free=40, queued=False)
        q.kind, q.calc = 'mopac', Calculation(method='PM7', task='Оптимизация')
        q.remote = ('profile', 'connection', plan, 'module load mopac')
        sent = []

        def send_batch(specs, profile, connection, chosen, setup, name, kind='orca'):
            sent.append(([s.folder.name for s in specs], chosen.processes, setup, kind))
            return '300'
        monkeypatch.setattr(remote_job, 'send_batch', send_batch)
        with window.at_place('server'):
            window.batch = q
            assert window.batch_tool._send_queue_at_once(q) is True
        assert len(sent) == 1 and len(sent[0][0]) == 3 and sent[0][1:] == (8, 'module load mopac', 'mopac')
        assert [i.state for i in q.items] == ['done', 'sent', 'sent', 'sent'] and q.extra['batch_job'] == '300'
        assert window.batch_tool.server_queue_left() is None  # the exit has nothing to send
        assert [i.state for i in batch.Batch.load(q.folder).items] == ['done', 'sent', 'sent', 'sent']
        with window.at_place('server'):
            assert window.batch_tool._send_queue_at_once(q) is False  # nothing waits any more
    finally:
        with window.at_place('server'):
            window.batch = None
        window.recovery.finish()
        window.close()
        window.deleteLater()
        assert app is not None

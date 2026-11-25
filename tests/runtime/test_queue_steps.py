"""What a queue does next, without the window (azimuth/runtime/queue_steps.advance).

Real Batch objects in a temporary folder; the steps recorded. Oracles: the rules of queue_steps §2 — the order of the
rows, the states saved in batch.json read back, the calls made.
"""

from types import SimpleNamespace

from azimuth.core import Calculation, read_xyz
from azimuth.runtime.queue_steps import Steps, advance
from modules.sextant import batch

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')


def queue_of(tmp_path, n=3, place='local', states=None):
    items = [batch.BatchItem(f'w{k}', WATER, state=(states or {}).get(k, 'waiting')) for k in range(n)]
    q = batch.Batch('orca', Calculation(), items, tmp_path / 'queue', place)
    q.folder.mkdir(parents=True)
    q.save()
    return q


class Recorded(Steps):
    def __init__(self, tmp_path, fail=(), due=(), searching=False, send=False, queue=None):
        self.calls, self.tmp, self.fail, self.due, self.searching, self.send, self.queue = [], tmp_path, fail, due, searching, send, queue

    def send_all(self):
        self.calls.append('send_all')
        if self.send:
            for item in self.queue.items:
                if item.state == 'waiting':
                    item.state = 'sent'
        return self.send

    def watch(self, item):
        self.calls.append(('watch', item.name))
        return 'watching'

    def search_due(self, item):
        return item.name in self.due and 'searched' not in item.props

    def search(self, item):
        self.calls.append(('search', item.name))
        item.props['searched'] = True
        return self.searching

    def start(self, item):
        self.calls.append(('start', item.name))
        if item.name in self.fail:
            raise ValueError('no program')
        folder = self.tmp / item.name
        return SimpleNamespace(spec=SimpleNamespace(folder=folder, output=folder / 'out'))

    def started(self, item, job):
        self.calls.append(('started', item.name))

    def failed_to_start(self, item, exc):
        self.calls.append(('failed', item.name, str(exc)))

    def stop_rest(self):
        self.calls.append('stop_rest')
        self.queue.stop_rest()

    def complete(self):
        self.calls.append('complete')


def test_the_first_waiting_row_starts_and_is_saved_running(tmp_path):
    q = queue_of(tmp_path, states={0: 'done'})
    steps = Recorded(tmp_path, queue=q)
    job = advance(q, steps)
    assert steps.calls == [('start', 'w1'), ('started', 'w1')]
    saved = batch.Batch.load(q.folder, recover=False)
    assert saved.items[1].state == 'running' and saved.items[1].folder == str(job.spec.folder)


def test_a_row_that_cannot_start_fails_and_the_next_one_starts(tmp_path):
    q = queue_of(tmp_path)
    steps = Recorded(tmp_path, fail=('w0', 'w1'), queue=q)
    advance(q, steps)
    assert steps.calls == [('start', 'w0'), ('failed', 'w0', 'no program'), ('start', 'w1'),
                           ('failed', 'w1', 'no program'), ('start', 'w2'), ('started', 'w2')]
    saved = batch.Batch.load(q.folder, recover=False)
    assert [i.state for i in saved.items] == ['failed', 'failed', 'running'] and saved.items[0].folder == ''


def test_the_end_of_the_rows_completes_the_queue(tmp_path):
    q = queue_of(tmp_path, n=2, states={0: 'done', 1: 'failed'})
    steps = Recorded(tmp_path, queue=q)
    assert advance(q, steps) is None and steps.calls == ['complete']


def test_a_queue_stopping_skips_what_waits_and_completes(tmp_path):
    q = queue_of(tmp_path, states={0: 'done'})
    q.stopping = True
    steps = Recorded(tmp_path, queue=q)
    assert advance(q, steps) is None and steps.calls == ['stop_rest', 'complete']
    assert [i.state for i in batch.Batch.load(q.folder, recover=False).items] == ['done', 'skipped', 'skipped']


def test_a_conformer_is_searched_first_and_a_row_with_nothing_to_search_is_calculated(tmp_path):
    q = queue_of(tmp_path, n=2)
    steps = Recorded(tmp_path, due=('w0',), searching=True, queue=q)
    assert advance(q, steps) is None and steps.calls == [('search', 'w0')]  # the search calls advance later
    steps = Recorded(tmp_path, due=('w1',), searching=False, queue=q)
    q.items[0].state = 'done'
    advance(q, steps)
    assert steps.calls == [('search', 'w1'), ('start', 'w1'), ('started', 'w1')]


def test_a_search_that_does_not_mark_its_row_cannot_loop(tmp_path):
    q = queue_of(tmp_path, n=1)

    class Stubborn(Recorded):
        def search_due(self, item):
            return True

        def search(self, item):
            self.calls.append(('search', item.name))
            return False

    steps = Stubborn(tmp_path, queue=q)
    advance(q, steps)
    assert steps.calls == [('search', 'w0'), ('start', 'w0'), ('started', 'w0')]


def test_a_server_queue_watches_what_runs_there_first_then_what_was_sent(tmp_path):
    q = queue_of(tmp_path, place='server', states={0: 'sent', 1: 'running'})
    steps = Recorded(tmp_path, queue=q)
    assert advance(q, steps) == 'watching' and steps.calls == [('watch', 'w1')]
    q.items[1].state = 'done'
    steps = Recorded(tmp_path, queue=q)
    advance(q, steps)
    assert steps.calls == [('watch', 'w0')]


def test_a_server_queue_sends_its_rest_at_once_and_watches_the_first(tmp_path):
    q = queue_of(tmp_path, place='server')
    steps = Recorded(tmp_path, send=True, queue=q)
    assert advance(q, steps) == 'watching' and steps.calls == ['send_all', ('watch', 'w0')]
    q = queue_of(tmp_path / 'b', place='server')
    steps = Recorded(tmp_path, send=False, queue=q)  # not sent at once (a search of conformers first): one by one
    advance(q, steps)
    assert steps.calls == ['send_all', ('start', 'w0'), ('started', 'w0')]
    q.items[0].state = 'running'
    q.stopping = True
    steps = Recorded(tmp_path, queue=q)  # stopping: nothing is watched, the rest is stopped
    assert advance(q, steps) is None and steps.calls == ['stop_rest', 'complete']

"""What a queue of calculations does next, apart from the window.
§1 PURPOSE
    BatchTool.start_next_batch_item decided and did everything in one method of the window: which row comes next, what
    a queue on a server watches first, when its rest is sent at once, when the conformer of a row is searched first,
    what a row that cannot start becomes, when the queue is complete. The decision could be checked only with the whole
    window. Here the order of the decisions is one function over the queue as saved; the window gives the steps (how a
    job is started, watched, shown) and does what advance() asks.
§2 RULES
    1. A queue on a server that is not stopping watches first the row running there, else the first row sent before
       (in their order: they wait for each other in SLURM); when there is none and steps.send_all() sent the rest at
       once, the first of them. Watching ends this call (the end of that row calls advance again).
    2. Else the first waiting row: none, or the queue stopping → stopping: steps.stop_rest() (what was sent is
       cancelled, what waits is skipped); then steps.complete(); None.
    3. A row whose conformer is due (steps.search_due) — steps.search(row): True, the search runs and calls advance
       when it is over → None; False, nothing to search (the row says why) → the row is calculated now. A row is offered
       to the search once per call (a search that does not mark the row cannot loop).
    4. steps.start(row) -> job; ValueError or OSError: the row 'failed' with no folder, steps.failed_to_start(row, exc),
       the next row; else the row 'running' with the folder and the output of job.spec, the queue saved,
       steps.started(row, job) → job.
    5. advance never sleeps, never touches a widget and never decides by the window: what it reads is the queue.
§3 INTERFACE advance(queue, steps) -> job | None; Steps — the protocol below (BatchTool's _QueueSteps in the window).
§4 TESTS tests/runtime/test_queue_steps.py — real Batch objects, recorded steps, no Qt."""

from __future__ import annotations


class Steps:
    """What the window does for advance(); every method is called only as §2 says."""

    def send_all(self):  # noqa: D401 — a server queue: all the rest sent at once; True when sent
        return False

    def watch(self, item):  # the row on the server watched (again); returns its job
        raise NotImplementedError

    def search_due(self, item):
        return False

    def search(self, item):  # True: the search runs and will call advance; False: nothing to search
        return False

    def start(self, item):  # -> job (with spec.folder and spec.output); ValueError / OSError: it cannot start
        raise NotImplementedError

    def started(self, item, job):
        pass

    def failed_to_start(self, item, exc):
        pass

    def stop_rest(self):
        pass

    def complete(self):
        pass


def advance(queue, steps):
    """§2: the next step of the queue, done by steps; the job started or watched, or None."""
    if queue.place == 'server' and not getattr(queue, 'stopping', False):
        sent = queue.current() or queue.next_sent()
        if sent is None and steps.send_all():
            sent = queue.next_sent()
        if sent is not None:
            return steps.watch(sent)
    offered = set()
    while True:
        item = queue.next_waiting()
        stopping = bool(getattr(queue, 'stopping', False))
        if item is None or stopping:
            if stopping:
                steps.stop_rest()
            steps.complete()
            return None
        if id(item) not in offered and steps.search_due(item):
            offered.add(id(item))
            if steps.search(item):
                return None  # the search calls advance when it is over
            # nothing to search: the row is calculated now (offered to the search once per call, §2.3)
        try:
            job = steps.start(item)
        except (ValueError, OSError) as exc:
            item.folder = ''
            queue.finished(item, 'failed')
            steps.failed_to_start(item, exc)
            continue
        item.state, item.folder, item.output = 'running', str(job.spec.folder), str(job.spec.output)
        queue.save()
        steps.started(item, job)
        return job

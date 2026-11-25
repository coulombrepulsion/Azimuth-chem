"""Long work of the program that goes on behind a window put away — one sign for all of it.

§1 PURPOSE
    Long work (a calculation, a conformer search) can go on behind a window put away. Every such work registers
    here, and the left panel shows one sign for all (the compass of the program, turning, with the ring of the progress
    when it is known).
§2 RULES
    An activity is shown in the panel while it is put away (parked: its window hidden by the user) and it runs, or it
    has ended and nobody has looked at the end yet; opening it (open()) shows its window; an ended activity seen is
    forgotten (seen). Qt-free: the listeners are called with the board after every change.
§3 INTERFACE
    Activity(key, title, state, done, total, note, parked, open, started, spent); Board: start(key, title, open,
    total=None, parked=False), progress(key, done=None, total=None, note=None), finish(key, state='done', spent='',
    note=None), park(key, parked=True), seen(key), get(key), shown() -> [Activity], running() -> bool,
    listen(callback); STATES.
§4 TESTS
    tests/core/test_activities.py; tests/hub/test_hub.py::test_calculation_indicator_in_the_panel.
"""

from dataclasses import dataclass, field
import time

STATES = ('running', 'done', 'failed', 'stopped')


@dataclass
class Activity:
    key: str
    title: str
    state: str = 'running'
    done: int | None = None
    total: int | None = None
    note: str = ''
    parked: bool = False
    open: object = None  # () -> None: show its window
    started: float = field(default_factory=time.monotonic)
    spent: str = ''
    section: str = ''  # the section of a work of run_waiting ('compass', 'crystal', 'sextant', 'spectrum')

    def fraction(self):
        """The share done (0…1) when it is known, else None."""
        if self.total and self.done is not None:
            return max(0.0, min(1.0, self.done / self.total))
        return None


class Board:
    def __init__(self):
        self.items = {}
        self.listeners = []

    def listen(self, callback):
        if callback not in self.listeners:
            self.listeners.append(callback)

    def _changed(self):
        for callback in list(self.listeners):
            try:
                callback(self)
            except RuntimeError:  # a panel being deleted
                pass

    def get(self, key):
        return self.items.get(key)

    def start(self, key, title, open=None, total=None, parked=None):
        old = self.items.get(key)
        self.items[key] = Activity(key, title, 'running', 0 if total else None, total, '',
                                   old.parked if parked is None and old is not None else bool(parked), open)
        self._changed()
        return self.items[key]

    def progress(self, key, done=None, total=None, note=None):
        item = self.items.get(key)
        if item is None:
            return None
        if done is not None:
            item.done = done
        if total is not None:
            item.total = total
        if note is not None:
            item.note = note
        self._changed()
        return item

    def finish(self, key, state='done', spent='', note=None):
        item = self.items.get(key)
        if item is None:
            return None
        item.state = state if state in STATES else 'done'
        item.spent = spent
        if note is not None:
            item.note = note
        if item.state == 'done' and item.total:
            item.done = item.total
        if not item.parked:  # its window is open: the end is seen there
            del self.items[key]
        self._changed()
        return item

    def park(self, key, parked=True):
        item = self.items.get(key)
        if item is None:
            return None
        item.parked = bool(parked)
        if not item.parked and item.state != 'running':
            del self.items[key]  # its window shows the end
        self._changed()
        return item

    def seen(self, key):
        item = self.items.get(key)
        if item is not None and item.state != 'running':
            del self.items[key]
            self._changed()
        return item

    def remove(self, key):
        if self.items.pop(key, None) is not None:
            self._changed()

    def shown(self):
        return [item for item in self.items.values() if item.parked]

    def running(self):
        return any(item.state == 'running' for item in self.items.values())

"""The calculation of each place — this computer and a server — as an explicit object (the external review
of 2026-11-09, item 4, step 2: «Ввести явные объекты состояния локального и серверного запуска»).

§1 PURPOSE
    Sextant ran one calculation per place at the same time. Its state — the job, its window, the queue, the
    tab it came from, what was already shown — lived in a dict of the window read through descriptors whose meaning
    changed with the place chosen in the interface («Где считать») and with a temporary override (at_place). The
    review: the dependencies are not visible, an asynchronous handler cannot be checked apart from the whole window.
§2 RULES
    1. RunSlot: one per place, the fields of §3 with their defaults; the queue of the place (batch) is one of them.
    2. RunSlots: slot(place) — made on first use; places() — those made; of_job(job) — the place whose job is
       that object (identity), whichever place is chosen now; running() — the jobs still going on.
       park(place) — the slot of the place moved aside under «<place>~N» (N from 2, the first free), its job going on
       there with its window; an empty slot for the place in its stead. parked(place) — the slots moved aside, in the
       order made; drop(place) — a slot forgotten; all_places(base) — base, then every other slot made (those parked).
       is_server(place) — «server» and its parked slots.
    3. Slotted(name): the descriptor of the window — reads and writes the field of the slot of job_place() (the place
       chosen, or the override). It keeps the old attribute names working while the handlers are moved to take the
       slot explicitly; the meaning of an attribute never depends on anything else.
    4. A handler of a job that has ended takes the slot of that job (of_job), not the place chosen now: switching
       «Где считать» never changes where an operation already started reports. Owner_of(job, place) —
       finish_job and batch_job_finished of Sextant run inside the slot it gives.
§3 FIELDS job, job_window, job_task, job_document, job_cycles, job_shown (False), job_panel_open (True), job_done
    (False), batch_finished_here (False), batch_project_here (''), last_batch, job_seen (False), batch.
§4 TESTS tests/runtime/test_runtime_places.py (no Qt).
"""

from __future__ import annotations

from dataclasses import dataclass, fields

PLACES = ('local', 'server')
PARKED = '~'  # «server~2» — a calculation on the server moved aside for the next one


def is_server(place):
    return place == 'server' or str(place or '').startswith('server' + PARKED)


@dataclass
class RunSlot:
    place: str
    job: object = None
    job_window: object = None
    job_task: object = None
    job_document: object = None
    job_cycles: object = None
    job_shown: bool = False
    job_panel_open: bool = True
    job_done: bool = False
    batch_finished_here: bool = False
    batch_project_here: str = ''
    last_batch: object = None
    job_seen: bool = False
    batch: object = None


FIELDS = tuple(f.name for f in fields(RunSlot) if f.name != 'place')


class RunSlots:
    def __init__(self):
        self._slots = {}

    def slot(self, place):
        found = self._slots.get(place)
        if found is None:
            found = self._slots[place] = RunSlot(place)
        return found

    def places(self):
        return tuple(self._slots)

    def all_places(self, base=PLACES):
        return tuple(base) + tuple(p for p in self._slots if p not in base)

    def park(self, place):
        old = self.slot(place)
        n = 2
        while f'{place}{PARKED}{n}' in self._slots:
            n += 1
        key = f'{place}{PARKED}{n}'
        del self._slots[place]
        old.place = key
        self._slots[key] = old
        self.slot(place)
        return old

    def parked(self, place):
        return [s for k, s in self._slots.items() if k.startswith(place + PARKED)]

    def drop(self, place):
        return self._slots.pop(place, None)

    def of_job(self, job):
        """The slot whose job is this object, or None."""
        if job is None:
            return None
        return next((s for s in self._slots.values() if s.job is job), None)

    def owner_of(self, job, place):
        """The slot a handler of job works in — the slot of that job when it has one (whichever place is
        chosen now), else the slot of place (a job not stored yet)."""
        return self.of_job(job) or self.slot(place)

    def running(self):
        return [s.job for s in self._slots.values() if s.job is not None and getattr(s.job, 'running', False)]


class Slotted:
    """The attribute `field` of the slot of owner.job_place(); the owner keeps a RunSlots as run_slots."""

    def __init__(self, field=None):
        self.field = field

    def __set_name__(self, owner, name):
        self.field = self.field or name.lstrip('_')
        if self.field not in FIELDS:
            raise AttributeError(f'RunSlot has no field {self.field!r}')

    @staticmethod
    def slots(obj):
        found = obj.__dict__.get('run_slots')
        if found is None:
            found = obj.__dict__['run_slots'] = RunSlots()
        return found

    def __get__(self, obj, owner=None):
        if obj is None:
            return self
        return getattr(self.slots(obj).slot(obj.job_place()), self.field)

    def __set__(self, obj, value):
        setattr(self.slots(obj).slot(obj.job_place()), self.field, value)

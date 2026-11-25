"""The calculation of each place as an explicit object (azimuth/runtime/places.py; the review of 2026-11-09,
item 4). No Qt, no window: a small owner with the descriptors stands for Sextant.

Oracles: the rules of §2 of the module — a field belongs to the slot of the place chosen (or overridden), the
defaults are those of §3, a job is found by identity whichever place is chosen now."""

from types import SimpleNamespace

import pytest

from azimuth.runtime.places import FIELDS, PLACES, RunSlot, RunSlots, Slotted


class Owner:
    job = Slotted()
    job_window = Slotted()
    _job_done = Slotted()
    job_panel_open = Slotted()
    batch = Slotted()

    def __init__(self):
        self.where = 'local'
        self.override = None

    def job_place(self):
        return self.override or self.where


def job(running=True):
    return SimpleNamespace(running=running)


def test_each_place_keeps_its_own_calculation():
    owner = Owner()
    here, there = job(), job()
    owner.job = here
    owner.where = 'server'
    assert owner.job is None and owner._job_done is False and owner.job_panel_open is True  # the defaults of §3
    owner.job = there
    owner.where = 'local'
    assert owner.job is here
    owner.override = 'server'
    assert owner.job is there  # at_place
    slots = Slotted.slots(owner)
    assert slots.slot('local').job is here and slots.slot('server').job is there
    assert set(slots.places()) == set(PLACES)


def test_switching_the_place_never_changes_the_owner_of_a_started_job():
    owner = Owner()
    started = job()
    owner.job = started  # started on this computer
    owner.where = 'server'  # the user switches «Где считать»
    owner.job = job()
    slot = Slotted.slots(owner).of_job(started)
    assert slot.place == 'local' and slot.job is started
    assert Slotted.slots(owner).of_job(SimpleNamespace(running=True)) is None  # an equal object is not that job
    assert Slotted.slots(owner).of_job(None) is None


def test_the_running_jobs_of_both_places():
    slots = RunSlots()
    a, b = job(), job(running=False)
    slots.slot('local').job, slots.slot('server').job = a, b
    assert slots.running() == [a]


def test_a_field_not_of_the_slot_is_refused():
    with pytest.raises((AttributeError, RuntimeError)):
        class Wrong:
            nonsense = Slotted()
    assert 'batch' in FIELDS and 'place' not in FIELDS and RunSlot('local').job_panel_open is True


def test_a_handler_works_in_the_slot_of_its_job():
    # finish_job / batch_job_finished of Sextant take this slot
    slots = RunSlots()
    local, remote = job(), job()
    slots.slot('local').job, slots.slot('server').job = local, remote
    assert slots.owner_of(local, 'server').place == 'local'  # the server is chosen now — the local job's own slot
    assert slots.owner_of(remote, 'local').place == 'server'
    assert slots.owner_of(job(), 'server').place == 'server'  # a job not stored: the place given


def test_a_calculation_on_the_server_is_moved_aside_for_the_next_one():
    # several calculations on a server at the same time
    from azimuth.runtime.places import is_server

    owner = Owner()
    owner.where = 'server'
    first = job()
    owner.job = first
    slots = Slotted.slots(owner)
    parked = slots.park('server')
    assert parked.place == 'server~2' and parked.job is first and owner.job is None  # an empty slot for the next one
    second = job()
    owner.job = second
    assert slots.park('server').place == 'server~3' and [s.job for s in slots.parked('server')] == [first, second]
    assert slots.owner_of(first, 'server').place == 'server~2'  # its end is handled in its own slot
    assert slots.running() == [first, second]
    assert slots.all_places() == ('local', 'server', 'server~2', 'server~3')
    assert is_server('server~2') and is_server('server') and not is_server('local') and not is_server(None)
    assert slots.drop('server~2') is parked and [s.job for s in slots.parked('server')] == [second]

"""Ids, commands and events of the runtime (azimuth/runtime/contracts.py; PROJECT_RUNTIME_GUIDE.md §4, §11).

Oracles: T11 of the guide — an event delivered twice is applied once; an event of an older project revision does not
undo a newer one; the receiver is found by project_id and entity_id, whatever tab is on screen.
"""

import pytest

from azimuth.runtime import contracts as ct


def test_ids_are_made_before_anything_else():
    ids = {ct.new_id() for _ in range(1000)}
    assert len(ids) == 1000 and all(len(i) == 32 and int(i, 16) >= 0 for i in ids)


def test_an_event_is_applied_once_and_never_older():
    delivery = ct.Delivery()
    done = ct.Event('project-a', 'attempt-1', 5, 'attempt_finished', {'execution': 'succeeded'})
    assert delivery.offer(done) == 'applied' and delivery.revision('project-a') == 5
    assert delivery.offer(done) == 'duplicate'  # T11: delivered twice
    older = ct.Event('project-a', 'attempt-1', 4, 'attempt_running')
    assert delivery.offer(older) == 'stale' and delivery.revision('project-a') == 5
    other = ct.Event('project-b', 'attempt-9', 1, 'attempt_running')  # another project: its own revisions
    assert delivery.offer(other) == 'applied' and delivery.revision('project-b') == 1


def test_commands_carry_their_id_and_errors_their_code():
    command = ct.Command('submit_new', ct.new_id(), expected_revision=3, arguments={'run_plan_id': 'p'})
    again = ct.Command('submit_new', command.command_id, expected_revision=3, arguments={'run_plan_id': 'p'})
    assert command == again and hash(command) == hash(again)  # delivered again: the same command
    error = ct.CommandError('stale_revision', 'expected 3, project is at 4')
    assert error.code == 'stale_revision' and 'expected 3' in str(error)
    with pytest.raises(ValueError):
        ct.CommandError('oops')


def test_every_kind_of_data_has_one_owner():
    data = [row[0] for row in ct.OWNERS]
    assert len(data) == len(set(data)) == 6 and all(len(row) == 3 and all(row) for row in ct.OWNERS)

"""The categories of failures and what to do (azimuth/runtime/errors.py; the roadmap of 2026-11-09, C).

Oracles: the table of §2 of the module, the errno of the system, and the real exceptions of the program raised here
(a broken database, a project written by another process, the kinds of SshError, the codes of CommandError)."""

import errno

import pytest

from azimuth import project_store, projects
from azimuth.runtime.contracts import CommandError
from azimuth.runtime.errors import CATEGORIES, classify
from azimuth.runtime.states import TransitionError
from modules.sextant.remote_job import SubmissionUncertain
from modules.sextant.ssh import SshError


@pytest.mark.parametrize('exc, name, action', [
    (SshError('no route', 'connection'), 'connection', 'retry'),
    (SshError('slow', 'timeout'), 'connection', 'retry'),
    (SshError('denied', 'auth'), 'refused', 'ask'),
    (SshError('changed', 'hostkey'), 'refused', 'ask'),
    (SshError('no ssh', 'missing'), 'missing', 'ask'),
    (SshError('exit 1', 'command'), 'execution', 'stop'),
    (SubmissionUncertain('lost'), 'uncertain', 'reconcile'),
    (project_store.ProjectDatabaseError('p.sqlite', 'file is not a database'), 'damaged', 'recover'),
    (project_store.ProjectDatabaseError('p.sqlite', 'database is locked'), 'unavailable', 'retry'),
    (projects.ProjectLocked('another window'), 'unavailable', 'retry'),
    (CommandError('stale_revision'), 'invalid', 'ask'),
    (CommandError('uncertain_submission'), 'uncertain', 'reconcile'),
    (TransitionError('no'), 'invalid', 'ask'),
    (OSError(errno.ENOSPC, 'No space left on device'), 'storage', 'stop'),
    (FileNotFoundError(2, 'gone'), 'missing', 'ask'),
    (PermissionError(13, 'denied'), 'unavailable', 'retry'),
    (RuntimeError('who knows'), 'execution', 'stop'),
])
def test_each_failure_has_its_category_and_action(exc, name, action):
    found = classify(exc)
    assert (found.name, found.action) == (name, action) and type(exc).__name__ in found.cause


def test_an_outside_action_is_repeated_only_where_it_provably_did_not_happen():
    assert not classify(SshError('lost', 'connection')).repeat_outside  # the sending may have reached the server
    assert not classify(SubmissionUncertain('lost')).repeat_outside
    assert not classify(OSError(errno.ENOSPC, 'full')).repeat_outside  # accepted there, not written here
    assert classify(SshError('denied', 'auth')).repeat_outside  # refused before the command ran
    assert set(CATEGORIES) == {'missing', 'unsupported', 'damaged', 'unavailable', 'connection', 'uncertain',
                               'refused', 'execution', 'storage', 'invalid'}
    assert {a for a, _ in CATEGORIES.values()} == {'ask', 'stop', 'recover', 'retry', 'reconcile'}


def test_every_category_has_its_advice_and_a_connection_never_says_run_again():
    from azimuth.runtime.errors import ADVICE, advice

    assert set(ADVICE) == set(CATEGORIES)
    assert 'не отправляется' in advice(classify(SshError('lost', 'connection')))
    assert 'не запуская снова' in advice(classify(SubmissionUncertain('lost')))
    assert advice(classify(RuntimeError('x'))) == ''  # the output of the program says it

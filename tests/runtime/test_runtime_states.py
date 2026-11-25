"""The six dimensions of the state of an attempt (azimuth/runtime/states.py; PROJECT_RUNTIME_GUIDE.md §6, §7).

Oracles: the rules of the guide — no network is not a failure; a late «running» does not undo a terminal state (§6);
a lost answer of sbatch is 'uncertain' and never allows sending again by itself (§7); the captions of §6.
"""

import pytest

from azimuth.runtime import states as st


def test_transitions_are_checked():
    assert st.transition('execution', 'queued', 'running') == 'running'
    assert st.transition('execution', 'running', 'running') == 'running'
    with pytest.raises(st.TransitionError):
        st.transition('execution', 'succeeded', 'running')
    with pytest.raises(st.TransitionError):
        st.transition('submission', 'uncertain', 'submitting')  # no new sending by itself
    with pytest.raises(st.TransitionError):
        st.transition('execution', 'running', 'flying')
    for dimension in st.DIMENSIONS:  # every state named as a target is a state of its table
        table = st.TRANSITIONS[dimension]
        assert all(target in table for targets in table.values() for target in targets), dimension


def test_no_network_is_not_a_failure():
    state = st.AttemptState(submission='accepted', execution='running')
    away = state.moved(connectivity='offline')
    assert away.execution == 'running' and st.caption(away) == 'Выполнялся; связь потеряна'
    assert st.caption(away.moved(connectivity='auth_required')) == 'Выполнялся; нужен вход на сервер'


def test_observations_of_an_old_watcher_twice_or_late_are_dropped():
    watch = st.Watch(generation=2, state=st.AttemptState(submission='accepted', execution='queued'))
    watch, verdict = st.accept(watch, st.Observation('a', 'g', 'squeue', 2, 0, 'running', '2026-11-08T10:00:00Z'))
    assert verdict == 'applied' and watch.state.execution == 'running' and watch.state.seen.startswith('2026-11-08')
    assert st.accept(watch, st.Observation('a', 'g', 'squeue', 1, 9, 'failed'))[1] == 'stale'  # replaced watcher
    assert st.accept(watch, st.Observation('a', 'g', 'squeue', 2, 0, 'running'))[1] == 'duplicate'
    watch, verdict = st.accept(watch, st.Observation('a', 'g', 'marker', 2, 1, 'succeeded'))
    assert verdict == 'applied' and watch.state.execution == 'succeeded'
    late, verdict = st.accept(watch, st.Observation('a', 'g', 'squeue', 2, 2, 'running'))
    assert verdict == 'late' and late.state.execution == 'succeeded'
    conflict, verdict = st.accept(watch, st.Observation('a', 'g', 'sacct', 2, 3, 'failed'))
    assert verdict == 'conflict' and conflict.state.execution == 'succeeded'  # only reconcile() changes it


def test_a_requeue_of_slurm_is_allowed():
    watch = st.Watch(state=st.AttemptState(submission='accepted', execution='running'))
    watch, verdict = st.accept(watch, st.Observation('a', 'g', 'squeue', 0, 0, 'queued'))
    assert verdict == 'applied' and watch.state.execution == 'queued'


def test_a_lost_answer_of_sbatch_is_settled_only_with_a_reason():
    state = st.AttemptState().moved(submission='submitting').moved(submission='uncertain')
    assert st.caption(state) == 'Неизвестно, принят ли сервером'
    with pytest.raises(st.TransitionError):
        st.reconcile(state, 'running', '')
    found, note = st.reconcile(state, 'running', 'one job with the token in squeue')
    assert found.submission == 'accepted' and found.execution == 'running' and 'token' in note
    none, _ = st.reconcile(state, 'not_started', 'no job with the token in squeue and sacct')
    assert none.submission == 'rejected'


def test_captions_say_what_is_not_the_ordinary_course():
    done = st.AttemptState(submission='accepted', execution='succeeded')
    assert st.caption(done) == 'Расчёт завершён'
    assert st.caption(done.moved(artifacts='transferring')) == 'Расчёт завершён; загружаются файлы'
    assert st.caption(done.moved(outcome='unconverged')) == ('Расчёт завершён; без сходимости; последняя геометрия '
                                                             'доступна')
    assert st.caption(st.AttemptState(submission='accepted', execution='running', cancellation='requested')) == \
        'Остановка запрошена'

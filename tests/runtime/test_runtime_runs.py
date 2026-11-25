"""The record of a sending and the reading of the server's answers (azimuth/runtime/runs.py), without a server.

Oracles: the table of transitions of the guide §6 (prepared → submitting → accepted | rejected | uncertain; uncertain
only by an explicit settlement with a reason), the forms of the sbatch answer of the SLURM manual («Submitted batch job
N»; --parsable: «N» or «N;cluster»), and the rule of §7: one found job restores the link, several are a conflict,
none proves nothing.
"""

import json

import pytest

from azimuth.runtime import runs
from azimuth.runtime.states import TransitionError


def test_the_intent_is_kept_before_the_call_and_read_back(tmp_path):
    sub = runs.new_submission(name_hint='C6H6')
    runs.write(tmp_path, sub)
    assert runs.read(tmp_path) == sub
    assert sub.state == 'prepared' and len(sub.token) == 32 and len(sub.attempt_id) == 32 and sub.token != sub.attempt_id
    assert sub.name == f'az-C6H6-{sub.token[:12]}' and len(sub.name) <= 40
    assert not list(tmp_path.glob('*.tmp'))  # written whole, through a temporary file
    data = json.loads((tmp_path / runs.FILE).read_text(encoding='utf-8'))
    assert data['state'] == 'prepared' and data['journal'] == []
    assert runs.read(tmp_path / 'nothing') is None
    (tmp_path / runs.FILE).write_text('{cut', encoding='utf-8')
    assert runs.read(tmp_path) is None


def test_two_sendings_never_share_a_token_or_a_name():
    subs = [runs.new_submission(name_hint='H2O') for _ in range(200)]
    assert len({s.token for s in subs}) == 200 and len({s.name for s in subs}) == 200
    assert runs.job_name('ab' * 16, 'Fe(CO)5 / x') == 'az-Fe_CO_5___x-' + 'ab' * 6


def test_the_moves_are_those_of_the_table():
    sub = runs.new_submission()
    with pytest.raises(TransitionError):
        runs.moved(sub, 'accepted', '5')  # never accepted without the call
    sending = runs.moved(sub, 'submitting', server='serv3', folder='~/a')
    assert sending.server == 'serv3' and sending.folder == '~/a' and 'prepared → submitting' in sending.journal[-1]
    done = runs.moved(sending, 'accepted', 101)
    assert done.job_id == '101'
    for state in ('submitting', 'rejected', 'uncertain', 'prepared'):
        with pytest.raises(TransitionError):
            runs.moved(done, state)
    lost = runs.moved(sending, 'uncertain', note='timeout')
    with pytest.raises(TransitionError):
        runs.moved(lost, 'accepted', '7')  # uncertain is settled, not moved
    with pytest.raises(TransitionError):
        runs.moved(lost, 'submitting')  # and never sent again
    with pytest.raises(TransitionError):
        runs.settle(lost, '7', '  ')
    with pytest.raises(TransitionError):
        runs.settle(lost, '', 'found')
    settled = runs.settle(lost, '7', 'one job of the name in squeue')
    assert settled.state == 'accepted' and settled.job_id == '7' and 'one job of the name' in settled.journal[-1]
    assert runs.settle(lost, '', 'no lock of the token', 'rejected').state == 'rejected'
    with pytest.raises(TransitionError):
        runs.settle(settled, '7', 'again')


@pytest.mark.parametrize('text, job', [
    ('Submitted batch job 4242', '4242'),
    ('4242', '4242'),
    ('4242;serv3', '4242'),
    ('sbatch: warning: memory\n4243', '4243'),
    ('token=ab\njob=77\nname=az-x\n', '77'),
    ('sbatch: error: Batch job submission failed', None),
    ('', None),
])
def test_the_number_from_every_form_of_the_answer(text, job):
    assert runs.answer_job(text) == job


def answer(*lines, end=True):
    return '\n'.join(lines + (('end',) if end else ()))


def test_the_verdict_of_the_server():
    assert runs.verdict(answer('receipt token=ab', 'receipt job=55', 'lock', 'squeue 55', 'nosacct')) == ('accepted', '55')
    assert runs.verdict(answer('nosacct')) == ('absent', None)  # no lock: the helper never ran
    assert runs.verdict('nofolder') == ('absent', None)
    assert runs.verdict(answer('lock', 'squeue 61', 'sacct 61')) == ('accepted', '61')
    assert runs.verdict(answer('lock', 'sacct 61.batch', 'sacct 61')) == ('accepted', '61')
    assert runs.verdict(answer('lock', 'squeue 61', 'sacct 62')) == ('conflict', ('61', '62'))
    assert runs.verdict(answer('lock', 'nosacct')) == ('uncertain', None)  # absent from squeue proves nothing
    assert runs.verdict(answer('receipt token=ab', 'lock', 'squeue 9', end=False)) == ('uncertain', None)  # cut


def test_the_helper_and_the_commands_are_ascii_and_quoted():
    script = runs.helper_script()
    assert script.isascii() and script.startswith('#!/bin/bash')
    assert 'sbatch --parsable -J "$name"' in script and 'mkdir .az-lock' in script and 'mv -f .az-receipt.tmp' in script
    sub = runs.new_submission(name_hint='H2O')
    command = runs.helper_command('"$HOME"/\'a b\'', sub, ('--dependency=afterany:5',))
    assert command.startswith('cd "$HOME"/\'a b\' && bash -lc ')
    assert sub.token in command and sub.name in command and command.rstrip("'").endswith('job.sh')
    find = runs.find_command('"$HOME"/x', sub)
    assert sub.name in find and 'squeue' in find and 'command -v sacct' in find and 'nofolder' in find

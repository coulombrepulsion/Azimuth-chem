"""The sending of one calculation to a SLURM server without a duplicate (stage C of
docs/architecture/PROJECT_RUNTIME_GUIDE.md, §7 «Надёжный удалённый запуск»).

§1 PURPOSE
    Till 0.107.3 the program called «sbatch job.sh» and took the number from its answer. When the answer was lost (the
    connection broke after the server had accepted the job) the calculation was «failed» while it ran on the server,
    and «Рассчитать» again put a second copy in the queue. The guide: durable intent before the outside call, a unique
    submission token, a receipt on the server, «uncertain» for a lost answer, settled only by a check, never by sending
    again.
§2 RULES
    1. prepare_remote writes submission.json (state 'prepared', attempt id, token, job name) and az-submit.sh into the
       job folder before anything reaches the server — the intent survives a crash before sending (T06).
    2. Before the call the record is 'submitting'. The helper on the server (az-submit.sh, in the job folder) runs
       under a lock of the token (mkdir .az-lock — atomic on every file system): a receipt .az-receipt already there is
       printed again (the same number, no second sbatch); else «sbatch --parsable -J <name>», the receipt written
       (temporary file, mv) and printed. A refusal of sbatch removes the lock — nothing was queued.
    3. The answer: a receipt → 'accepted' with the number; a refusal → 'rejected'. A lost answer (the connection or a
       timeout) → the record stays 'submitting' and the server is asked (find_command): the receipt → 'accepted'; no
       lock → the helper never ran, the same token is sent again (that is not a second job: the helper keeps it
       once); a lock without a receipt (sbatch called, its answer unknown) → the jobs of the user named <name> in
       squeue and, when it is there, sacct: exactly one → 'accepted'; several → 'conflict' (no automatic action, the
       numbers are shown); none → 'uncertain' (a job missing from one source is not proven missing). The server not
       reachable → 'uncertain'.
    4. 'uncertain' changes only by settle() with a reason (the journal of the record keeps it) — an explicit check,
       never a new sending; a new calculation is a new attempt with a new token.
    5. The record is written atomically (a temporary file and os.replace); its transitions are those of
       azimuth.runtime.states.TRANSITIONS['submission'].
§3 INTERFACE
    FILE, HELPER, RECEIPT, LOCK; Submission (attempt_id, token, name, state, job_id, server, folder, journal,
    created, changed); new_submission(attempt_id, name_hint) -> Submission; read(folder) -> Submission | None;
    write(folder, sub); moved(sub, state, job_id=None, note='') -> Submission (TransitionError on a move the table
    forbids); settle(sub, job_id, reason, state='accepted') -> Submission (uncertain → accepted | rejected, reason
    kept); helper_script() -> str;
    helper_command(remote_dir, sub, extra=()) -> str; answer_job(text) -> job id | None; find_command(remote_dir, sub)
    -> str; verdict(text) -> ('accepted', id) | ('absent', None) | ('conflict', ids) | ('uncertain', None).
    GROUP; digest(folder, base, kind) -> sha256 hex; write_group(folder, group_id, members) (once);
    read_group(folder) -> dict ({} when missing).
§4 TESTS
    tests/runtime/test_runtime_runs.py (pure), tests/sextant/test_remote_submission.py (against the fake server: the
    lost answer after acceptance, a crash before sending, a full disk after acceptance, zero and several candidates).
§5 NOTES
    ASSUMPTION squeue -n and sacct --name of serv2–serv4 find a job by its name;
    sacct keeps the records some days (its absence is handled: command -v sacct). The receipt is the first source; the
    name is searched only in the narrow window between the acceptance by sbatch and the writing of the receipt.
"""

from __future__ import annotations

import hashlib
import re
import shlex
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path

from azimuth.runtime.contracts import new_id
from azimuth.runtime.states import TRANSITIONS, TransitionError

FILE = 'submission.json'
GROUP = 'group.json'  # the manifest of an ExecutionGroup (stage D)
HELPER = 'az-submit.sh'
RECEIPT = '.az-receipt'
LOCK = '.az-lock'
SEARCH_DAYS = 14


def _now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@dataclass(frozen=True)
class Submission:
    attempt_id: str
    token: str
    name: str
    state: str = 'prepared'
    job_id: str = ''
    server: str = ''
    folder: str = ''
    journal: tuple = field(default_factory=tuple)
    created: str = ''
    changed: str = ''


def job_name(token, hint=''):
    """«az-<formula>-<12 hex of the token>», at most 40 characters: readable in squeue and unique by the token."""
    safe = re.sub(r'[^A-Za-z0-9._-]', '_', hint or '')[:24]
    return f'az-{safe}-{token[:12]}' if safe else f'az-{token[:12]}'


def new_submission(attempt_id=None, name_hint=''):
    token = new_id()
    now = _now()
    return Submission(attempt_id or new_id(), token, job_name(token, name_hint), created=now, changed=now)


def read(folder):
    """From the database of the project of the folder, else the file (azimuth/runtime/records.py)."""
    from azimuth.runtime import records

    from azimuth.project_store import ProjectDatabaseError

    data = records.read(folder, FILE)  # an unreadable database raises — not «nothing was sent»
    try:
        data['journal'] = tuple(data.get('journal', ()))
        return Submission(**{k: data[k] for k in Submission.__dataclass_fields__ if k in data})
    except ProjectDatabaseError:
        raise
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def write(folder, sub):
    from azimuth.runtime import records

    data = asdict(sub)
    data['journal'] = list(sub.journal)
    records.write(folder, FILE, data)


def moved(sub, state, job_id=None, note='', **changes):
    if state != sub.state and state not in TRANSITIONS['submission'][sub.state]:
        raise TransitionError(f'submission: {sub.state} → {state} is not allowed')
    journal = sub.journal + ((f'{_now()} {sub.state} → {state}' + (f': {note}' if note else '')),)
    return replace(sub, state=state, job_id=str(job_id) if job_id else sub.job_id, journal=journal, changed=_now(),
                   **changes)


def settle(sub, job_id, reason, state='accepted'):
    """An uncertain submission settled by an explicit check (guide §7): the job found (accepted) or proven never to
    have reached sbatch (rejected); the reason kept."""
    if sub.state != 'uncertain':
        raise TransitionError(f'settle: the submission is {sub.state}, not uncertain')
    if state not in ('accepted', 'rejected') or not reason or not str(reason).strip():
        raise TransitionError('settle: accepted or rejected, with the reason')
    if state == 'accepted' and not str(job_id).strip().isdigit():
        raise TransitionError('settle: the job number is required')
    journal = sub.journal + (f'{_now()} uncertain → {state} (settled): {reason}',)
    return replace(sub, state=state, job_id=str(job_id or ''), journal=journal, changed=_now())


def helper_script():
    """The helper on the server (ASCII, POSIX sh features only besides bash -lc of the caller)."""
    return f'''#!/bin/bash
# Azimuth: one sbatch per submission token (0.107.4). Usage: bash {HELPER} TOKEN NAME [sbatch options] SCRIPT
cd "$(dirname "$0")" || exit 3
token="$1"; name="$2"; shift 2
if [ -s {RECEIPT} ]; then cat {RECEIPT}; exit 0; fi
if ! mkdir {LOCK} 2>/dev/null; then
  i=0
  while [ $i -lt 20 ]; do
    if [ -s {RECEIPT} ]; then cat {RECEIPT}; exit 0; fi
    sleep 1; i=$((i + 1))
  done
  echo "az-submit: the submission $token is already in progress" >&2; exit 4
fi
echo "$token" > {LOCK}/token
if command -v sbatch >/dev/null 2>&1; then
  answer=$(sbatch --parsable -J "$name" "$@" 2>&1); code=$?
  job=$(printf '%s\\n' "$answer" | grep -E '^[0-9]+(;[^ ]*)?$' | tail -n 1 | cut -d';' -f1)
else
  # a server without SLURM (0.222.19): the script goes on by itself (nohup, its own session), the number is its pid;
  # the time limit of its #SBATCH -t line is kept by timeout
  for a in "$@"; do script="$a"; done
  limit=$(grep -m 1 -E '^#SBATCH[[:space:]]+(-t|--time)' "$script" | sed -E 's/^#SBATCH[[:space:]]+(-t|--time)[= ]*//')
  seconds=$(printf '%s\\n' "$limit" | awk '{{d=0; t=$1; if (t=="") exit; if (index(t,"-")) {{split(t,a,"-"); d=a[1]; t=a[2]; split(t,b,":"); s=b[1]*3600+b[2]*60+b[3]}} else {{n=split(t,b,":"); if (n==3) s=b[1]*3600+b[2]*60+b[3]; else if (n==2) s=b[1]*60+b[2]; else s=b[1]*60}} print d*86400+s}}')
  export SLURM_SUBMIT_DIR="$(pwd)" SLURM_JOB_NAME="$name"
  set -- bash -l "$script"
  if [ -n "$seconds" ] && [ "$seconds" -gt 0 ] && command -v timeout >/dev/null 2>&1; then set -- timeout -s TERM "$seconds" "$@"; fi
  if command -v setsid >/dev/null 2>&1; then set -- setsid "$@"; fi
  nohup "$@" > az-nohup.out 2>&1 < /dev/null &
  job=$!; code=0; answer="started with nohup"
fi
if [ $code -ne 0 ] || [ -z "$job" ]; then
  printf '%s\\n' "$answer"; rm -rf {LOCK}; exit ${{code:-1}}
fi
printf 'token=%s\\njob=%s\\nname=%s\\nuser=%s\\nhost=%s\\nfolder=%s\\n' "$token" "$job" "$name" "$USER" "$(hostname)" "$(pwd)" > {RECEIPT}.tmp
mv -f {RECEIPT}.tmp {RECEIPT}
cat {RECEIPT}
'''


def helper_command(remote_dir, sub, extra=(), script='job.sh'):
    """remote_dir — already quoted for the shell (ssh.shell_path)."""
    inner = ' '.join(shlex.quote(a) for a in ('bash', HELPER, sub.token, sub.name, *extra, script))
    return f'cd {remote_dir} && bash -lc {shlex.quote(inner)}'


def answer_job(text):
    """The number from the answer of the helper (job=N), of sbatch --parsable (N or N;cluster) or of plain sbatch."""
    text = text or ''
    match = re.search(r'^job=(\d+)\s*$', text, re.M)
    if match:
        return match.group(1)
    match = re.search(r'Submitted batch job (\d+)', text)
    if match:
        return match.group(1)
    lines = [line.strip() for line in text.splitlines() if re.fullmatch(r'\d+(;\S*)?', line.strip())]
    return lines[-1].split(';')[0] if lines else None


def find_command(remote_dir, sub):
    """What the server knows of the token: its receipt, its lock, the jobs of the user with its name (squeue, sacct)."""
    name = shlex.quote(sub.name)
    script = (
        f'if [ -s {RECEIPT} ]; then sed "s/^/receipt /" {RECEIPT}; fi; '
        f'if [ -d {LOCK} ]; then echo lock; fi; '
        f'squeue -h -u "$USER" -n {name} -o %i 2>/dev/null | sed "s/^/squeue /"; '
        f'if command -v sacct >/dev/null 2>&1; then '
        f'sacct -n -X -P -u "$USER" --name {name} -o JobID -S now-{SEARCH_DAYS}days 2>/dev/null | sed "s/^/sacct /" '
        f'|| echo nosacct; else echo nosacct; fi; echo end'
    )
    return f'if cd {remote_dir} 2>/dev/null; then bash -lc {shlex.quote(script)}; else echo nofolder; fi'


def verdict(text):
    """§2.3 from the answer of find_command."""
    lines = [line.strip() for line in (text or '').splitlines() if line.strip()]
    if 'nofolder' in lines:
        return 'absent', None  # the folder was never uploaded: nothing reached sbatch
    if 'end' not in lines:
        return 'uncertain', None  # the answer was cut: nothing proven
    receipt = [line.split('=', 1)[1] for line in lines if line.startswith('receipt job=')]
    if receipt and receipt[-1].strip().isdigit():
        return 'accepted', receipt[-1].strip()
    if 'lock' not in lines:
        return 'absent', None
    found = []
    for line in lines:
        source, _, rest = line.partition(' ')
        if source in ('squeue', 'sacct'):
            ident = rest.strip().split(';')[0].split('.')[0].split('_')[0]
            if ident.isdigit() and ident not in found:
                found.append(ident)
    if len(found) == 1:
        return 'accepted', found[0]
    if len(found) > 1:
        return 'conflict', tuple(found)
    return 'uncertain', None


# -- the manifest of a group sent as one job ------------------------------------------------------
def digest(folder, base, kind='orca'):
    """SHA-256 of the input of a job of the group (<base>.inp, <base>.mop of MOPAC); '' when it is missing."""
    for name in (f'{base}.mop', f'{base}.inp') if kind == 'mopac' else (f'{base}.inp', f'{base}.mop'):
        path = Path(folder) / name
        if path.is_file():
            return hashlib.sha256(path.read_bytes()).hexdigest()
    return ''


def write_group(folder, group_id, members):
    """group.json: the group id and its members in the order of the script — attempt, folder, base, sha256. Written
    once, before the sending; the composition of a sent group never changes (guide §8)."""
    from azimuth.runtime import records

    data = {'group_id': group_id, 'created': _now(), 'members': list(members)}
    records.write(folder, GROUP, data, once=True)


def read_group(folder):
    from azimuth.runtime import records

    data = records.read(folder, GROUP)
    return data if isinstance(data, dict) else {}

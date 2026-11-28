"""Sextant: a queue of calculations sent to a SLURM server at once and run one after another by one SLURM job.

§1 PURPOSE
    send_batch uploads the prepared folders (remote_prepare.prepare_remote) with the script of the queue
    (cluster.batch_script) in a folder of its own and submits it once; BatchItemJob watches one calculation of it by
    the markers its folder gets on the server (STARTED, FINISHED, SKIP), with one answer about the group shared by the
    watchers of its members (_GROUPS). The rules of the sending — the token, a lost answer asked of the server, nothing
    sent twice — are those of remote_job.RemoteJob (its §2, §6).
§4 SPECIFICATION
    send_batch(specs, profile, connection, chosen, setup, name, kind='orca') -> job id; SubmissionUncertain;
    BatchItemJob(RemoteJob) — RemoteJob.resume gives it for a job.json with 'batch'; group_command(job_id, parent,
    names) -> command; parse_group(text) -> (squeue text, {folder: (finished, started, skipped)}). Also named from
    remote_job. remote_job.RETRY and GONE_WAIT_S are read from there (the tests set them).
§7 TESTS tests/sextant/test_remote_job.py, tests/sextant/test_remote_submission.py.
"""

from __future__ import annotations

import re
import threading
import time
from datetime import datetime

from azimuth.i18n import tr
from azimuth.runtime import runs
from modules.sextant import cluster, remote_job as _rj
from modules.sextant.remote_job import JOB_JSON, RemoteJob, _by_number
from modules.sextant.ssh import SshError, shell_path

# the last answer about each group of calculations run by one SLURM job (send_batch), shared by its
# watchers: (server address, job number, local folder of the group) -> (monotonic time, squeue text,
# {folder: (finished, started, skipped)})
_GROUPS = {}
_GROUPS_LOCK = threading.Lock()
_GROUP_MARK = '@@azimuth-group@@'


def group_command(job_id, parent, names):
    """One command for a group — the state of its job in squeue, then a line «folder|finished|started|skip»
    for each member folder in parent."""
    import shlex

    folders = ' '.join(shlex.quote(n) for n in names)
    return (f'{cluster.queue_command(job_id)}; echo {_GROUP_MARK}; cd {shell_path(parent)} 2>/dev/null && '
            f'for d in {folders}; do printf "%s|%s|%s|%s\\n" "$d" "$(cat "$d/{cluster.FINISHED}" 2>/dev/null)" '
            f'"$(cat "$d/{cluster.STARTED}" 2>/dev/null)" "$(test -f "$d/{cluster.SKIP}" && echo 1)"; done; true')


def parse_group(text):
    """(squeue text, {folder: (finished, started, skipped)}) from the answer of group_command."""
    head, _, rest = (text or '').partition(_GROUP_MARK)
    markers = {}
    for line in rest.splitlines():
        parts = line.split('|')
        if len(parts) >= 4 and parts[0].strip():
            markers[parts[0].strip()] = (parts[1].strip(), parts[2].strip(), parts[3].strip())
    return head, markers


def send_batch(specs, profile, connection, chosen, setup, name, kind='orca'):
    """The prepared jobs (prepare_remote, in the order of the queue) uploaded, the script of the queue written
    into a folder of its own next to them and submitted once; job.json of every job: the shared number, 'batch': True.
    Returns the number; ValueError when the server did not queue it.
    The folder of the script has group.json (group id, the ordered attempt ids,
    folders and SHA-256 of the inputs) and the record of the sending of the group (azimuth/runtime/runs.py); the script
    is submitted through the helper of the token, the markers of each job name its attempt. A lost answer → the server
    is asked; not settled → SubmissionUncertain (job.json of the jobs without a number, 'group' — the local folder of
    the group: their watching settles it first) — never sent again, never one by one."""
    from pathlib import Path

    if not specs:
        raise ValueError(tr('Нечего отправлять.'))
    parent = profile.folder.strip().rstrip('/') or '~'
    root = Path(specs[0].folder).parent
    folder = root / (re.sub(r'[^A-Za-z0-9._-]', '_', root.name)[:60] + cluster.BATCH_FOLDER_SUFFIX)
    folder.mkdir(parents=True, exist_ok=True)
    members = []
    for spec in specs:
        own = runs.read(spec.folder)
        if own is None:  # a folder prepared
            own = runs.new_submission()
            runs.write(spec.folder, own)
        members.append((spec.folder.name, spec.output.name.rsplit('.', 1)[0], own.attempt_id))
    group = runs.read(folder)
    if group is not None and group.state in ('submitting', 'uncertain', 'accepted'):  # this folder was sent before
        if [m.get('attempt') for m in runs.read_group(folder).get('members', [])] != [m[2] for m in members]:
            raise ValueError(tr(f'Очередь уже отправлялась из папки {folder} — её состояние: {group.state}. Новая '
                                'отправка — новой очередью.'))
    else:
        group = runs.new_submission(name_hint=name[3:] if name.startswith('az-') else name)
        runs.write_group(folder, group.attempt_id, [
            {'attempt': attempt, 'folder': job_folder, 'base': base,
             'sha256': runs.digest(root / job_folder, base, kind)} for job_folder, base, attempt in members])
        (folder / runs.HELPER).write_text(runs.helper_script(), encoding='ascii', newline='\n')
        (folder / 'batch.sh').write_text(cluster.batch_script(chosen, setup, name, members, kind), encoding='utf-8',
                                         newline='\n')
        group = runs.moved(group, 'submitting', server=profile.title(), folder=f'{parent}/{folder.name}')
        runs.write(folder, group)
    remote = shell_path(f'{parent}/{folder.name}')
    job_id, why = None, ''
    for _ in range(3):
        if group.state == 'accepted':
            job_id = group.job_id
            break
        try:
            # all the folders in one archive and the sbatch in the same ssh — two exchanges with the server
            # instead of two for every calculation
            result = connection.upload_packed([spec.folder for spec in specs] + [folder], parent,
                                              then=runs.helper_command(remote, group, (), 'batch.sh'), timeout=600)
        except SshError as exc:
            if exc.kind not in ('connection', 'timeout'):
                runs.write(folder, runs.moved(group, 'rejected', note=str(exc)))
                raise
            try:
                found = runs.verdict(connection.run(runs.find_command(remote, group), timeout=60)
                                     .out.decode('utf-8', errors='replace'))
            except SshError:
                found = ('uncertain', None)
            if found[0] == 'absent':
                continue  # the helper never ran: the same token again
            if found[0] == 'accepted':
                group = runs.moved(group, 'accepted', found[1], note='the answer was lost; found on the server')
                runs.write(folder, group)
                job_id = group.job_id
                break
            why = str(exc) if found[0] == 'uncertain' else f'several jobs of the token: {", ".join(sorted(found[1], key=_by_number))}'
            group = runs.moved(group, 'uncertain', note=why)
            runs.write(folder, group)
            break
        answer = (result.out.decode('utf-8', errors='replace') + '\n' + result.err).strip()
        job_id = runs.answer_job(answer) if result.code == 0 else None
        if job_id is None:
            runs.write(folder, runs.moved(group, 'rejected', note=answer[:300]))
            raise ValueError(tr('Сервер не поставил очередь расчётов: ') + (answer or tr(f'код {result.code}')))
        group = runs.moved(group, 'accepted', job_id)
        runs.write(folder, group)
        break
    for spec in specs:
        job = BatchItemJob(spec, profile, connection)
        job.job_id = job_id
        job.group_dir = str(folder)
        job._write_json()
    if job_id is None:
        raise SubmissionUncertain(tr(f'Связь прервалась при постановке очереди; неизвестно, принял ли её сервер '
                                     f'(метка {group.name}, папка {parent}/{folder.name}). Повторно она не '
                                     'отправлена — Секстант проверит это сам, когда связь вернётся.'))
    return job_id


class SubmissionUncertain(ValueError):
    """The server may have accepted the queue — the jobs are not sent again (nor one by one)."""


class BatchItemJob(RemoteJob):
    """One calculation of a queue run by one SLURM job (send_batch): nothing is sent, its folder is watched."""

    BATCH = True

    def _work(self):
        try:
            if self.job_id is None and not self._settle_group():
                return
            self._set('queued', tr(f'Ждёт своей очереди на сервере (задача {self.job_id}).'))
            self._watch_markers()
        except SshError as exc:
            self._failed(exc, str(exc))
        except Exception as exc:  # noqa: BLE001 — never an exception in the window (§8')
            self._failed(exc, f'{type(exc).__name__}: {exc}')

    def _settle_group(self):
        """The answer to the sending of the queue was lost — the record of the group here (another job of the
        queue may have settled it already), else the server is asked; True when the number is known."""
        from pathlib import Path

        folder = Path(getattr(self, 'group_dir', '') or '')
        group = runs.read(folder) if str(folder) not in ('', '.') else None
        if group is None:
            self._end(1, 'failed', tr('Нет сведений об отправке этой очереди.'))
            return False
        if group.state != 'accepted':
            self._set('sending', tr('Проверяю, принял ли сервер очередь…'))
            try:
                text = self._again(lambda: self.connection.run(runs.find_command(shell_path(group.folder), group),
                                                               timeout=60))
                found, job = runs.verdict(text.out.decode('utf-8', errors='replace'))
            except SshError:
                found, job = 'uncertain', None
            if found == 'accepted':
                group = (runs.settle(group, job, 'checked on the server: the receipt or the only job of the token')
                         if group.state == 'uncertain' else runs.moved(group, 'accepted', job, note='found on the server'))
                self._record_group(folder, group)
            elif found == 'absent':
                reason = 'the server never got this sending (no lock of the token)'
                self._record_group(folder, runs.settle(group, '', reason, 'rejected') if group.state == 'uncertain'
                                   else runs.moved(group, 'rejected', note=reason))
                self._end(1, 'failed', tr('Сервер не получал эту очередь — расчёт не в очереди. Запустите его заново.'))
                return False
            else:
                ids = ', '.join(sorted(job, key=_by_number)) if found == 'conflict' else ''  # squeue lists them in any order
                self._end(1, 'uncertain', tr(f'Неизвестно, принял ли сервер очередь (метка {group.name}'
                                             + (f'; заданий с ней несколько: {ids}' if ids else '')
                                             + f', папка {group.folder}). Повторно ничего не отправлено.'))
                return False
        self.job_id = group.job_id
        try:
            self._write_json()
        except OSError as exc:
            self.local_warning = tr(f'Записать {JOB_JSON} не удалось ({exc}); очередь — задача {self.job_id}.')
        return True

    def _record_group(self, folder, group):
        try:
            runs.write(folder, group)
        except OSError as exc:
            self.local_warning = tr(f'Не удалось записать сведения об отправке очереди ({exc}).')

    def _attempt(self):
        own = runs.read(self.spec.folder)
        return own.attempt_id if own is not None else ''

    def _members(self):
        """The folders of the calculations of the group on the server, in its order (group.json of the local
        folder of the group); this calculation's own at least."""
        names = []
        if getattr(self, 'group_dir', ''):
            try:
                names = [str(m['folder']) for m in runs.read_group(self.group_dir).get('members', []) if m.get('folder')]
            except (OSError, ValueError, KeyError, TypeError):
                names = []
        own = self.spec.folder.name
        return names if own in names else names + [own]

    def _observe(self):
        """(the state in squeue, finished, started, skipped) of this calculation — from one command for the whole group
        (squeue of the shared job and the markers of every member folder), shared by the watchers of the group: the next
        calculation of the queue, taken up when this one ends (or one by one after a restart, when the server ran many
        meanwhile), uses the answer of less than an interval ago instead of asking again. An SshError is raised as
        before (the watching handles the lost connection)."""
        key = (self.profile.address(), str(self.job_id), str(getattr(self, 'group_dir', '') or self.spec.folder.parent))
        own = self.spec.folder.name
        now = time.monotonic()
        with _GROUPS_LOCK:
            seen = _GROUPS.get(key)
        if seen is None or now - seen[0] > self.interval * 0.9 or own not in seen[2]:
            text = self.connection.text(group_command(self.job_id, self.remote_dir.rsplit('/', 1)[0], self._members()),
                                        timeout=60)
            seen = (time.monotonic(),) + parse_group(text)
            with _GROUPS_LOCK:
                _GROUPS[key] = seen
        finished, started, skipped = seen[2].get(own, ('', '', ''))
        return (cluster.queue_state(seen[1]),) + self._own_markers(finished, started, skipped)

    def _markers(self):
        command = (f'cd {self._remote()} 2>/dev/null && printf "%s|%s|%s" "$(cat {cluster.FINISHED} 2>/dev/null)" '
                   f'"$(cat {cluster.STARTED} 2>/dev/null)" "$(test -f {cluster.SKIP} && echo 1)"')
        answer = self.connection.text(command + ' || echo "||"', timeout=30).strip()
        finished, started, skipped = (answer.split('|') + ['', '', ''])[:3]
        return self._own_markers(finished, started, skipped)

    def _own_markers(self, finished, started, skipped):
        # a marker names its attempt («<code or time> <attempt>»); a marker of another attempt is not this one's
        mine = self._attempt()
        def own(marker):
            parts = marker.split()
            return bool(parts) and (len(parts) < 2 or not mine or parts[1] in (mine, '-'))
        finished, started = finished.strip(), started.strip()
        return (finished.split()[0] if own(finished) else ''), own(started), bool(skipped.strip())

    def _queue_log(self):
        """The last lines of slurm-<number>.out of the folder of the queue on the server ('' when there are
        none or the server does not answer) — «orca not found in PATH» stayed there unseen."""
        from pathlib import Path

        group = Path(getattr(self, 'group_dir', '') or '').name
        if not group or not self.job_id:
            return ''
        remote = self.remote_dir.rsplit('/', 1)[0] + '/' + group + f'/slurm-{self.job_id}.out'
        try:
            text = self.connection.text(f'tail -n 3 {shell_path(remote)} 2>/dev/null || true', timeout=30)
        except SshError:
            return ''
        return ' '.join(line.strip() for line in text.splitlines() if line.strip())[:400]

    def _watch_markers(self):
        failures = 0
        while True:
            if self._stop_asked.is_set():  # «Пропустить»: the script ends this calculation and goes on
                try:
                    self.connection.run(f'touch {self._remote(cluster.SKIP)}', timeout=30)
                except SshError:
                    pass
                self._stop_asked.clear()
                self.stopped = True
            try:
                state, finished, started, _ = self._observe()  # one answer for the whole group
                if started:
                    self._fetch_output()
                failures = 0
            except SshError as exc:
                if exc.kind in ('connection', 'timeout'):
                    delay = _rj.RETRY[min(failures, len(_rj.RETRY) - 1)]
                    failures += 1
                    if failures >= 2:
                        self._reconnect_vpn()
                    when = datetime.now().strftime('%H:%M:%S')
                    known = self._last_seen()
                    self._set('offline', tr(f'Нет связи с сервером · попытка в {when}, следующая через {delay:.0f} с. '
                                            'Очередь там продолжается.') + (f' ({known})' if known else ''))
                    self._wait(delay)
                    continue
                raise
            if finished:
                self._finish()
                return
            if state is None and not self._gone_for_sure():  # T10: the marker may come late
                self._observed('gone')
                self._set('running' if started else 'queued',
                          tr(f'Задачи очереди {self.job_id} уже нет на сервере — жду отметку конца этого расчёта.'))
                self._wait(min(self.interval, _rj.GONE_WAIT_S))
                continue
            if state is not None:
                self._gone, self._gone_size = 0, -1
                self._observed('running' if started else 'queued')
            if state is None:  # the job of the queue ended (or was cancelled) before this calculation did
                if started:
                    self._finish()
                elif self.stopped:
                    self._end(-15, 'stopped', tr('Расчёт пропущен.'))
                else:
                    why = self._queue_log()  # what the job of the queue said (its slurm-<номер>.out)
                    self._end(1, 'failed', tr(f'Задача очереди на сервере (номер {self.job_id}) закончилась раньше, '
                                              'чем дошла до этого расчёта.') + (tr(' Сервер: ') + why if why else ''))
                return
            if not started:
                self._set('queued', tr(f'Ждёт своей очереди на сервере (задача {self.job_id}).'))
            else:
                self._set('running', tr(f'Идёт на сервере (очередь — задача {self.job_id}).'))
            self._wait(self.interval)

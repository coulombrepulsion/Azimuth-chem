"""A queue on a server: opening the server for it, sending the waiting calculations at once or before the exit,
picking up a calculation left there, cancelling what was sent, asking about an uncertain row. Methods of BatchTool
(self is the tool; the window only through its port self.w), kept here to make batch_actions.py shorter.

Split off modules/sextant/batch_actions.py (0.222.29).
"""

from dataclasses import replace
from azimuth.i18n import tr
from modules.sextant import batch as batches


def _open_batch_server(self, queue):
    """(profile, connection, chosen processes, setup) — the server opened and the processes asked once."""

    from azimuth.tasks import run_quietly
    from modules.sextant import cluster, remote, server_access

    profile = remote.load(self.w.preferences)
    if not profile.ready():
        self.w.run_tool.edit_server()
        return None
    try:
        kept = queue.extra.get('plan') if isinstance(queue.extra, dict) else None
        # T09: a queue taken up whose calculations are all on the server already (nothing to send) is
        # watched also when the server does not answer now — the watching says «Нет связи», what it knew last
        # and tries again by itself; something still to send needs the server
        watching_only = isinstance(kept, dict) and not any(item.state == 'waiting' for item in queue.items)
        if watching_only:
            opened = server_access.open_for_watching(self.w.widget, profile, waiting=run_quietly)
            if opened is None:
                return None
            connection, resources, why = opened
            if resources is None:
                try:
                    plan = cluster.Plan(**kept)
                except TypeError as exc:
                    raise ValueError(why) from exc
                self.w.notify(tr(f'Сервер {profile.title()} сейчас не отвечает — очередь там идёт; слежу за ней и '
                                 'проверю, как только связь появится.'), 12000)
                return profile, connection, plan, ''
        else:
            opened = server_access.open_server(self.w.widget, profile, waiting=run_quietly)
            if opened is None:
                return None
            connection, resources = opened
        if not resources.slurm:
            raise ValueError(tr(f'На сервере {profile.title()} нет SLURM: расчёты там запускаются сразу (nohup), '
                                'поэтому очередь туда не отправляется — запускайте расчёты по одному.'))
        setup = cluster.server_setup(profile, resources, queue.kind)  # ValueError: the program is not found there
        if isinstance(kept, dict):  # the queue taken up — the processes chosen at its start, not asked again
            try:
                return profile, connection, cluster.Plan(**kept), setup
            except TypeError:
                pass
        # the processes and the memory of the panel for each calculation of the queue — no question
        chosen = cluster.server_plan(resources, self.w.cores.value(), self.w.memory.value(), profile.title())
        self.w.run_tool.notify_server_plan(resources, chosen)
        from dataclasses import asdict

        queue.extra = {**(queue.extra or {}), 'plan': asdict(chosen)}  # for taking the queue up
        queue.save()
        return profile, connection, chosen, setup
    except (ValueError, OSError) as exc:
        self.w.error(exc)
        return None


def _send_queue_at_once(self, queue):
    """Every waiting calculation of a server queue prepared, uploaded and run by
    one SLURM job one after another (remote_job.send_batch, cluster.batch_script); the items become 'sent' and are
    watched one by one (BatchItemJob). Not for a queue that searches conformers first (that search runs here,
    between the calculations) — it is sent one by one as before. False when nothing was sent."""
    from azimuth.tasks import run_waiting
    from modules.sextant import remote_job

    waiting = [item for item in queue.items if item.state == 'waiting']
    if not waiting or any(self.conformer_search_due(queue, item) for item in waiting) or queue.purpose == 'chain':
        return False  # a step of a chain needs the geometry of the one before — one by one
    profile, connection, chosen, setup = queue.remote
    specs = []
    for item in waiting:
        try:
            calc, text = self.batch_item_input(queue, item)
            spec = remote_job.prepare_remote(item.molecule, calc, (), queue.folder, chosen, setup, text=text,
                                             kind=queue.kind)
        except (ValueError, OSError) as exc:
            item.folder = ''
            item.note = str(exc)
            queue.finished(item, 'failed')
            continue
        specs.append((item, spec))
    if not specs:
        return False

    from azimuth.project_store import ProjectDatabaseError

    def work(step):
        step(0, 1)
        return remote_job.send_batch([spec for _, spec in specs], profile, connection, chosen, setup,
                                     f'az-{queue.folder.name}'[:40], queue.kind)

    try:
        job_id = run_waiting(self.w.widget, tr(f'Отправляю очередь на сервер ({len(specs)} расчётов)…'), work, 1,
                             alone=False)
    except InterruptedError:
        return False
    except ProjectDatabaseError as exc:  # the database of the project unreadable — nothing sent, said
        self.w.error(str(exc))
        return True
    except remote_job.SubmissionUncertain as exc:  # maybe accepted — never sent again, nor one by one
        for item, spec in specs:
            item.state, item.folder, item.output = 'sent', str(spec.folder), str(spec.output)
        queue.extra = {**(queue.extra or {}), 'batch_job': ''}
        queue.save()
        self.w.error(str(exc))
        return True
    except Exception as exc:  # noqa: BLE001 — said; the queue is sent one by one then
        self.w.error(tr('Очередь не отправилась на сервер одним заданием — расчёты пойдут по одному: ') + str(exc))
        return False
    for item, spec in specs:
        item.state, item.folder, item.output = 'sent', str(spec.folder), str(spec.output)
    queue.extra = {**(queue.extra or {}), 'batch_job': str(job_id)}
    queue.save()
    self.w.notify(tr(f'Очередь на сервере: {len(specs)} расчётов идут одной задачей {job_id}, один за другим — и без '
                   'программы.'), 9000)
    return True


def _resume_batch_item(self, queue, item):
    """The calculation of the queue that was on the server when the program closed: its watching is taken
    up (remote_job.RemoteJob.resume — the same number in the queue, nothing sent again), the window shows the queue
    as when it ran."""

    from modules.sextant import remote_job
    from modules.sextant.workspace_texts import NAMES

    profile, connection, chosen, _setup = queue.remote
    k = queue.position(item)
    base = queue.calc.title or ''
    calc = replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity, cores=chosen.processes,
                   memory_mb=chosen.maxcore, title=f'{base + "_" if base else ""}{k:02d}')
    try:
        from modules.sextant import history

        # the database of the project, else the file; without job.json — a sending whose answer
        # was lost (submission.json): the server is asked first, nothing is sent again (RemoteJob._settle)
        info = history.remote_info({'folder': str(item.folder), 'kind': queue.kind})
        if not isinstance(info, dict):
            raise ValueError(tr('нет сведений о задании на сервере (job.json)'))
        job = remote_job.RemoteJob.resume(item.folder, item.output, profile, connection, info).start()
    except (OSError, ValueError, KeyError) as exc:
        item.note = tr('слежение не подхвачено: ') + str(exc)  # the reason kept in batch.json
        queue.finished(item, 'failed')
        self.w.notify(tr(f'{item.name}: ') + str(exc), 10000)
        return self.start_next_batch_item()
    item.state = 'running'  # a job sent before the exit is watched now
    queue.save()
    title = tr(f'Очередь {k} из {len(queue.items)}: {item.name} · {NAMES[queue.kind]}')
    self.w.run_tool.job_started(job, calc, queue.kind, None, place=profile.title(), title=title, remember=False,
                     quiet=self.queue_under_way(queue))
    self.w.job_window.show_batch(queue)
    self.show_batch_plan()
    return job


def _cancel_sent(self, queue):
    """«Остановить» a queue with jobs sent ahead: they are taken out of the SLURM queue (scancel) and
    stopped."""

    from modules.sextant import remote_job

    sent = [item for item in queue.items if item.state == 'sent']
    if not sent:
        return 0
    from azimuth.project_store import ProjectDatabaseError
    from azimuth.runtime import records

    ids, unknown = [], []
    for item in sent:
        try:
            ids.append(str(int(records.read(item.folder, remote_job.JOB_JSON)['job'])))
        except ProjectDatabaseError as exc:  # its number unknown now — not «stopped», it may run there
            unknown.append(item.name)
            item.note = str(exc)
            continue
        except (OSError, ValueError, KeyError, TypeError):
            pass
        item.state = 'stopped'
    if unknown:
        self.w.notify(tr('Не удалось прочитать номера заданий на сервере: ') + ', '.join(unknown)
                    + tr(' — они не сняты и могут идти там.'), 15000)
    remote = getattr(queue, 'remote', None)
    if ids and remote is not None:
        try:
            from modules.sextant import cluster

            remote[1].run(cluster.cancel_command(ids), timeout=60)
        except Exception as exc:  # noqa: BLE001 — said; the jobs may still run there
            self.w.notify(tr('Не удалось снять с очереди сервера задачи ') + ', '.join(ids) + ': ' + str(exc), 12000)
    queue.save()
    return len(ids)


def server_queue_left(self):
    """The queue on a server with calculations not sent yet (they wait for Azimuth to send them)."""
    with self.w.at_place('server'):
        queue = self.w.batch
    if queue is None or queue.place != 'server' or getattr(queue, 'remote', None) is None:
        return None
    return queue if queue.next_waiting() is not None and not getattr(queue, 'stopping', False) else None


def send_rest_before_exit(self, queue):
    """Before the exit — every calculation of the queue not sent yet is prepared, sent and queued on the
    server, each waiting for the one before (remote_job.submit, afterany): the queue goes on without the program;
    at the next start Sextant takes it up and watches them one by one (state 'sent'). Returns the number sent; a
    failure of one leaves it and the rest 'waiting' (sent at the next start) and is said."""

    from azimuth.tasks import run_waiting
    from modules.sextant import remote_job

    profile, connection, chosen, setup = queue.remote
    current = queue.current()
    after = None
    if current is not None:
        try:
            from azimuth.runtime import records

            after = (records.read(current.folder, remote_job.JOB_JSON) or {}).get('job')
        except (OSError, ValueError):
            after = None
    waiting = [item for item in queue.items if item.state == 'waiting']

    def work(step):
        nonlocal after
        sent = 0
        for n, item in enumerate(waiting):
            if step(n, len(waiting)) is False:
                break
            calc, text = self.batch_item_input(queue, item)  # tasks and ghosts of a binding queue
            spec = remote_job.prepare_remote(item.molecule, calc, (), queue.folder, chosen, setup, text=text,
                                             kind=queue.kind)
            after = remote_job.submit(spec, profile, connection, after)
            item.state, item.folder, item.output = 'sent', str(spec.folder), str(spec.output)
            queue.save()
            sent += 1
        return sent

    try:
        return run_waiting(self.w.widget, tr(f'Отправляю оставшиеся расчёты на сервер ({len(waiting)})…'), work,
                           len(waiting), alone=False)
    except InterruptedError:
        return sum(1 for item in waiting if item.state == 'sent')
    except Exception as exc:  # noqa: BLE001 — the exit goes on; what was not sent waits for the next start
        self.w.error(tr('Не все расчёты очереди отправлены на сервер — остальные отправятся при следующем запуске: ')
                   + str(exc))
        return sum(1 for item in waiting if item.state == 'sent')


def check_uncertain_item(self, folder, index):
    """0.108.30 «Проверить на сервере» of a row 'uncertain': the server is asked about its sending (the token of
    submission.json); accepted — the job is watched; never reached SLURM — the row fails with that reason and may be
    prepared again; still not known — it stays 'uncertain'. Then the queue goes on as «Продолжить очередь»."""
    try:
        queue = batches.Batch.load(folder)
    except (OSError, ValueError, KeyError) as exc:
        self.w.error(tr('Очередь не прочитана: ') + str(exc))
        return None
    if not 0 <= index < len(queue.items) or queue.items[index].state != 'uncertain':
        return None
    queue.items[index].state = 'sent'  # watched again by start_next_batch_item → _resume_batch_item
    queue.save()
    return self.resume_batch(folder)

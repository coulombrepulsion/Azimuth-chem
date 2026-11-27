"""Running a crystal calculation from QePanel: the steps and their input, the SSSP library, the start here
(Quantum ESPRESSO, CP2K through mpirun) or on the server, a batch of crystals, the progress and the stop. Methods of
QePanel (self is the panel), kept here to make qe_window.py shorter.

Split off modules/compass/actions/qe_window.py (0.222.29).
"""

from datetime import datetime
import os
from pathlib import Path
from azimuth.i18n import tr
from modules.compass.actions.qe_common import HEADER


def steps(self, pseudo_dir=None):
    """[(file, program, text)] of the task: pw.in, or the steps of the bands and the density of states."""
    from modules.sextant import qe_inputs, qe_pseudo

    root = self.root()
    if self.crystal is None:
        raise ValueError(tr('Нет кристалла: откройте файл CIF в «Компас · Кристалл».'))
    if self.program == 'cp2k':  # one input, the basis sets and the potentials of CP2K itself
        from modules.sextant import cp2k_inputs

        crystal, _ = self.computed()
        return [(cp2k_inputs.INPUT, 'cp2k', cp2k_inputs.cp2k_input(crystal, self.task.currentData(), self.options()))]
    library = self.library()
    if not qe_pseudo.installed(root, library):
        from modules.compass.actions.qe_window import own_library

        if library is not qe_pseudo.LIBRARY or own_library(self):  # PBEsol, Windows, the server — downloaded when asked
            raise ValueError(tr('Нет псевдопотенциалов {}: нажмите «Скачать псевдопотенциалы» (около 60 МБ, один раз).')
                             .format(library['name']))
        raise ValueError(tr('Нет псевдопотенциалов SSSP: установите Quantum ESPRESSO — «Расчёт → Установить программы '
                            'для расчёта…» (вместе с ним скачивается библиотека).'))
    crystal, basis = self.computed()
    return qe_inputs.steps(crystal, self.task.currentData(), qe_pseudo.table(root, library),
                           pseudo_dir or str(qe_pseudo.folder(root, library)), 'azimuth', self.spacing.value(), basis,
                           self.crystal, self.options())


def download_library(self):
    """The SSSP library of the functional chosen, downloaded with a waiting window; True when it is there."""
    from azimuth.tasks import run_waiting
    from modules.sextant import qe_pseudo

    library, root = self.library(), self.root()
    if qe_pseudo.installed(root, library):
        return True
    try:
        run_waiting(self, tr('Скачиваю псевдопотенциалы {}…').format(library['name']),
                    lambda step: qe_pseudo.download(root, library=library))
    except (OSError, ValueError) as exc:
        self.status.setText(tr('Псевдопотенциалы не скачались: {}').format(exc))
        return False
    self.settings_changed()
    return qe_pseudo.installed(root, library)


def input_text(self):
    steps = self.steps()
    if len(steps) == 1:
        return steps[0][2]
    return '\n'.join(f'{HEADER.format(name, program)}\n{text}' for name, program, text in steps)


def run_steps(self):
    """The steps that run: those of the settings, or the file edited by hand (split by its headers)."""
    if not self.input_edited:
        return self.steps()
    import re

    text = self.preview.toPlainText()
    if not text.strip():
        raise ValueError(tr('Входной файл пуст.'))
    parts = re.split(r'^# ---- (\S+) \((\S+)\) ----\s*$', text, flags=re.M)
    if len(parts) == 1:
        if self.program == 'cp2k':
            return [('azimuth.inp', 'cp2k', text.rstrip('\n') + '\n')]
        return [('pw.in', 'pw.x', text.rstrip('\n') + '\n')]
    return [(parts[k], parts[k + 1], parts[k + 2].strip('\n') + '\n') for k in range(1, len(parts) - 2, 3)]


def refresh(self):
    try:
        text = self.input_text()
        ready = True
    except ValueError as exc:
        text = ''
        self.status.setText(str(exc))
        ready = False
    self._generated = text
    if not self.input_edited:  # a file edited by hand stays until «Собрать заново»
        self._filling = True
        self.preview.setPlainText(text)
        self._filling = False
    if ready and not (self.job and self.job.running) and self.on_server():
        self.status.setText(tr('Готово к отправке на сервер {} (очередь SLURM).').format(self.server_profile().title()))
    elif ready and not (self.job and self.job.running) and self.program == 'cp2k':
        from modules.sextant import install_tools

        program = install_tools.cp2k_program(self.root())
        if program is None:  # where CP2K comes from on this system
            if os.name == 'nt':  # qe_windows.install_cp2k is written, not offered until it has run on Windows
                self.status.setText(tr('Для Windows нет сборки CP2K: считайте на сервере.'))
            else:  # on a Mac too — through Homebrew
                self.status.setText(tr('CP2K не найден: «Расчёт → Установить программы для расчёта…» → CP2K.'))
            ready = False
        else:
            self.status.setText(tr('CP2K найден — готово к запуску'))
            self.status.setToolTip(str(program))
    elif ready and not (self.job and self.job.running):
        from modules.sextant import install_tools

        program = install_tools.qe_program(self.root())
        if program is None:
            self.status.setText(tr('pw.x не найден: «Расчёт → Установить программы для расчёта…» → Quantum ESPRESSO.'))
            ready = False
        else:  # the path in the tooltip, as the program of a molecule
            self.status.setText(tr('Quantum ESPRESSO найден — готово к запуску'))
            self.status.setToolTip(str(program))
    self.run_button.setEnabled(ready and not (self.job and self.job.running))
    return ready


# -- the run -------------------------------------------------------------------------------------------------
def jobs_root(self):
    tool = getattr(self.owner, 'run_tool', None)
    return Path(tool.jobs_root()) if tool is not None else Path.home() / 'Azimuth' / 'calculations'


def start(self):
    from modules.sextant import install_tools, qe_inputs, runner

    if not self.refresh():
        return None
    if not self.input_edited and not self.ask_magnetism():
        return None
    cp2k = self.program == 'cp2k'
    program = install_tools.cp2k_program(self.root()) if cp2k else install_tools.qe_program(self.root())
    stamp = datetime.now().strftime('%Y%m%d-%H%M%S')
    named = self.batch_name or getattr(self, 'title_text', '') or self.name  # «Название» of Sextant
    if named.lower().endswith('.cif'):
        named = named[:-4]
    safe = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in named)[:40] or 'crystal'
    self.folder = self.jobs_root() / f'{self.program}-{safe}-{stamp}'
    self.folder.mkdir(parents=True, exist_ok=True)
    self.crystal_ident = None  # the crystal of the project the run is of (several in one project)
    try:
        from azimuth import crystal_projects

        manifest = self.folder.parent.parent / 'project.qcc'
        if self.folder.parent.name == 'calculations' and crystal_projects.is_crystal(manifest):
            self.crystal_ident = self.batch_ident or crystal_projects.active(manifest)
    except (OSError, ValueError, KeyError):
        pass
    server = self.on_server()
    try:
        steps = self.run_steps()
    except ValueError as exc:
        self.status.setText(str(exc))
        return None
    beside = os.name == 'nt' and not server and not cp2k  # Windows: see windows_command
    if (server or beside) and not cp2k:  # the pseudopotentials go with the folder
        import re

        steps = [(n, t, re.sub(r"pseudo_dir\s*=\s*'[^']*'", "pseudo_dir = './pseudo'", x)) for n, t, x in steps]
    for name, _, text in steps:
        (self.folder / name).write_text(text, encoding='utf-8', newline='\n')  # also for the server
    self.steps_run = [s[:2] for s in steps]
    if self.task.currentData() in (qe_inputs.BANDS_TASK, qe_inputs.DISPERSION_TASK):  # the path of the plot
        self._write_path()
    if self.task.currentData() == qe_inputs.ELASTIC_TASK:  # which strain each run is of, and the volume
        import json

        from modules.compass.chemistry import elastic

        note = {'plan': [[name, e] for name, e in elastic.plan()], 'volume': self.computed()[0].cell.volume()}
        (self.folder / 'elastic.json').write_text(json.dumps(note), encoding='utf-8', newline='\n')
    if server:
        return self.start_server(steps, safe)
    if cp2k:
        return self._start_cp2k(program)
    if beside:
        try:
            copy_pseudo(self, steps)
        except (ValueError, OSError) as exc:
            self.status.setText(str(exc))
            return None
        command, script, changes = windows_command(steps, program, self.processes.value())
        if script:
            # the line ends of cmd.exe; the files a server gets are written with «\n» (start_server)
            (self.folder / WINDOWS_SCRIPT).write_bytes(script.replace('\n', '\r\n').encode('ascii'))
        spec = runner.JobSpec('qe', self.folder, tuple(command), self.folder / 'pw.out', {**os.environ, **changes})
        try:
            self.job = runner.Job(spec).start()
        except ValueError as exc:
            self.status.setText(str(exc))
            return None
        return self._started(tr('Считается… Папка расчёта: ') + str(self.folder))
    prefix = install_tools.qe_prefix(self.root())
    env = dict(os.environ)
    env['OMP_NUM_THREADS'] = '1'
    if (prefix / 'bin').is_dir():
        env['PATH'] = os.pathsep.join([str(prefix / 'bin'), env.get('PATH', '')])
        env['OPAL_PREFIX'] = str(prefix)  # the Open MPI 5 of the package, apart from the 4.1 of ORCA
    n = self.processes.value()
    mpirun = prefix / 'bin' / 'mpirun'
    parallel = [str(mpirun), '-np', str(n)] if n > 1 and mpirun.is_file() else []
    if len(steps) == 1:
        command = [*parallel, str(program), '-in', 'pw.in']
    else:  # the steps one after another, each only after the one before ended well
        import shlex

        lines = ['#!/bin/sh', 'set -e']
        for name, tool, _ in steps:
            exe = Path(program).with_name(tool) if tool != 'pw.x' else Path(program)
            line = ' '.join(shlex.quote(w) for w in [*(parallel if tool in qe_inputs.PARALLEL else []), str(exe),
                                                      '-in', name])
            if tool in qe_inputs.OPTIONAL:  # projwfc.x — its own output, its error not the job's
                line += f' > {qe_inputs.OPTIONAL[tool]} 2>&1 || true'
            lines.append(line)
        (self.folder / 'run.sh').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
        command = ['/bin/sh', 'run.sh']
    spec = runner.JobSpec('qe', self.folder, tuple(command), self.folder / 'pw.out', env)
    try:
        self.job = runner.Job(spec).start()
    except ValueError as exc:
        self.status.setText(str(exc))
        return None
    return self._started(tr('Считается… Папка расчёта: ') + str(self.folder))


SERIES_FILES = ('eos1.in', 'ela1.in', 'cut1.in', 'kpt1.in', 'vac1.in', 'hub1.in', 'mag1.in')


def series_like(folder):
    """Is the job of the folder a series of runs of pw.x of equal standing (its first input is one of SERIES_FILES)?"""
    return folder is not None and any((Path(folder) / name).is_file() for name in SERIES_FILES)


WINDOWS_SCRIPT = 'run.bat'


def copy_pseudo(self, steps):
    """The pseudopotentials of the species of the first input copied into pseudo/ of the job folder (the inputs name
    them by the relative «./pseudo»: for a server, and on Windows — see windows_command)."""
    import shutil

    from modules.sextant import qe_pseudo

    pseudo = self.folder / 'pseudo'
    pseudo.mkdir(exist_ok=True)
    qe_pseudo.table(self.root(), self.library())  # raises when the library is not there
    source = qe_pseudo.folder(self.root(), self.library())
    species = steps[0][2].split('ATOMIC_SPECIES')[1].split('CELL_PARAMETERS')[0].strip().splitlines()
    for file in {line.split()[2] for line in species}:  # «Si 28.0850 Si.upf»
        shutil.copy2(source / file, pseudo / file)
    return pseudo


def windows_command(steps, program, processes):
    """(command, the text of run.bat or '', the changes of the environment) of a run on Windows.

    The Windows build (modules/sextant/qe_windows.py) has no MPI: the processes asked for become OpenMP threads.
    Nothing in the inputs or in the script names a folder: the programs are found by PATH (their folder put first —
    their DLLs lie there too), the pseudopotentials are in ./pseudo of the job folder. A path with Russian letters —
    the name of the user, the folder of the program — would otherwise have to pass through the code page of cmd.exe
    and through the Fortran run-time, which reads the input as bytes."""
    from modules.sextant import qe_inputs, qe_windows

    folder = str(Path(program).parent)
    changes = {'PATH': os.pathsep.join([folder, os.environ.get('PATH', '')]), 'OMP_NUM_THREADS': str(max(1, int(processes))),
               'OMP_STACKSIZE': qe_windows.OMP_STACK}
    if len(steps) == 1:
        return [str(program), '-in', steps[0][0]], '', changes
    lines = ['@echo off']
    for name, tool, _ in steps:
        line = f'{qe_windows.exe_name(tool)} -in {name}'
        if tool in qe_inputs.OPTIONAL:  # projwfc.x — its own output, its error not the job's
            lines.append(f'{line} > {qe_inputs.OPTIONAL[tool]} 2>&1')
        else:
            lines.append(f'{line} || exit /b 1')
    return ['cmd', '/d', '/c', WINDOWS_SCRIPT], '\n'.join(lines) + '\n', changes


def batch_idents(self):
    """The crystals with a tick of the project shown in the batch mode (two or more), or None."""
    idents = getattr(self.owner, 'crystal_batch_idents', None)
    try:
        found = idents() if callable(idents) else None
    except (OSError, ValueError, KeyError):
        found = None
    return found if found and len(found) > 1 else None


def run_clicked(self):
    """«Запустить расчёт»: the crystal shown — or, in the batch mode of a crystal project, every crystal with a tick
    one after another with these settings (crystal_batch.ask_and_run)."""
    idents = self.batch_idents()
    if idents:
        from modules.compass.actions import crystal_batch

        return crystal_batch.ask_and_run(self, idents)
    return self.start()


def set_crystal_for_batch(self, crystal, name, primitive=True):
    """Another crystal of the batch put in — the settings kept as they are (set_crystal would take the
    program of its last run and drop its charge); its primitive cell as the box says."""
    from modules.compass.chemistry import crystal as cr

    self.crystal, self.name = crystal, name
    self.result = None
    self.primitive_crystal = cr.primitive(crystal)
    whole, small = len(cr.unit_cell(crystal)), len(cr.unit_cell(self.primitive_crystal))
    wanted = primitive  # the choice made before the batch (the box of a primitive cell is off)
    self.primitive.blockSignals(True)
    self.primitive.setEnabled(small < whole)
    self.primitive.setChecked(wanted and small < whole)
    self.primitive.blockSignals(False)
    self._gamma_cells = None
    return self.refresh()


def _start_cp2k(self, program):
    """CP2K on this computer — its MPI build through the mpirun next to it (or of its prefix); a build without MPI
    (Windows) — with the processes asked for as threads (install_tools.cp2k_environment)."""
    from modules.sextant import install_tools, runner

    n = self.processes.value()
    env = install_tools.cp2k_environment(program, n)
    mpirun = Path(program).with_name('mpirun')
    parallel = [str(mpirun), '-np', str(n)] if n > 1 and mpirun.is_file() and 'smp' in Path(program).name else []
    command = [*parallel, str(program), '-i', 'azimuth.inp']
    spec = runner.JobSpec('cp2k', self.folder, tuple(command), self.folder / 'cp2k.out', env)
    try:
        self.job = runner.Job(spec).start()
    except ValueError as exc:
        self.status.setText(str(exc))
        return None
    return self._started(tr('Считается… Папка расчёта: ') + str(self.folder))


def output_path(self):
    return self.folder / ('cp2k.out' if self.program == 'cp2k' else 'pw.out')


def _tell(self, event):
    for listener in list(self.listeners):
        listener(event, self)


def _started(self, text):
    self.result = None
    self.summary.setText('')
    self.aim_button.hide()
    self.charges_button.hide()
    self.open_button.setEnabled(False)
    self.plot_button.hide()
    self.run_button.setEnabled(False)
    self.stop_button.setEnabled(True)
    self.status.setText(text)
    self.timer.start()
    self._tell('start')
    return self.job


def start_server(self, steps, name):
    """The job sent to the server of «Сервер…» (SLURM) and watched here (remote_job.RemoteJob)."""
    from azimuth.tasks import run_quietly
    from modules.sextant import cluster, remote_job, server_access

    profile = self.server_profile()
    try:
        opened = server_access.open_server(self, profile, waiting=run_quietly)
        if opened is None:
            self.status.setText(tr('Сервер не открыт — расчёт не отправлен.'))
            return None
        connection, resources = opened
        kind = self.program  # or CP2K
        setup = cluster.server_setup(profile, resources, kind)  # ValueError: the program is not found there
        if kind == 'qe':
            copy_pseudo(self, steps)
        chosen = cluster.server_plan(resources, self.processes.value(), self.memory.value(), profile.title())
        spec = remote_job.prepare_qe(self.folder, [s[:2] for s in steps], chosen, setup, name, kind)
        self.job = remote_job.RemoteJob(spec, profile, connection).start()
    except (ValueError, OSError) as exc:  # ssh.SshError is a ValueError: its message is for the user
        self.status.setText(str(exc))
        return None
    return self._started(tr('Отправляю на сервер {}… Папка расчёта: ').format(profile.title()) + str(self.folder))


def _write_path(self):
    import json

    from modules.sextant import qe_paths

    _, basis = self.computed()  # the primitive cell and the supercell
    p = qe_paths.path(self.crystal, basis)
    data = {'kind': p.kind, 'general': p.general, 'x': p.x, 'ticks': p.ticks, 'breaks': p.breaks}
    (self.folder / 'path.json').write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8', newline='\n')


def stop(self):
    if self.batch is not None:  # «Остановить» stops the batch too — the crystals left are not started
        self.batch.stopped, self.batch.left = True, []
    if self.job is not None and self.job.running:
        self.job.stop()


def progress_parts(self, text, result):
    """The step of the optimization, the SCF under way (its step, energy and change — CP2K; its iteration and the
    estimated accuracy — pw.x), the last total energy and the pressure."""
    import re

    parts = []
    if self.program == 'cp2k':
        from modules.spectrum.readers import cp2k

        now = cp2k.progress(text)
        if now.get('opt_step'):
            parts.append(tr('шаг оптимизации {}').format(now['opt_step']))
        if 'scf_step' in now:
            parts.append(tr('SCF: шаг {}, E = {} Eh, ΔE = {}').format(
                now['scf_step'], f"{now['scf_energy']:.8f}", f"{now['scf_change']:.1e}"))
        elif result.energies:
            parts.append(tr('энергия {} Eh').format(f'{result.energy_hartree:.8f}'))
        return parts
    steps = re.findall(r'number of bfgs steps\s*=\s*(\d+)', text)
    if steps and 'bfgs converged' not in text:  # the steps made so far, the next one under way
        parts.append(tr('шаг оптимизации {}').format(int(steps[-1]) + 1))
    iterations = re.findall(r'iteration #\s*(\d+)', text)
    accuracy = re.findall(r'estimated scf accuracy\s*<\s*([-\d.Ee+]+)\s*Ry', text)
    if iterations:
        parts.append(tr('SCF: итерация {}').format(iterations[-1])
                     + (f', {tr("точность")} {float(accuracy[-1]):.1e} Ry' if accuracy else ''))
    if result.energies:
        parts.append(tr('энергия {} Ry').format(f'{result.energy:.6f}'))
    if result.pressures:
        parts.append(f'P = {result.pressures[-1]:.2f} kbar')
    return parts


def poll(self):
    from modules.spectrum.readers import qe

    if self.job is None:
        return None
    code = self.job.poll()
    text = self.job.text()
    if self.program == 'cp2k':
        from modules.spectrum.readers import cp2k as reader

        result = reader.read(text, self.folder if code is not None else None)
    else:
        # the scf of the steps (the bands and the density of states follow it); of a series of runs of equal standing
        # (volumes, cutoffs, strains …) — the last one: the summary says «ниже — последний расчёт ряда»
        runs = qe.runs(text) or [text]
        result = qe.read(runs[-1] if series_like(self.folder) else runs[0])
    if code is None:
        parts = [tr('Считается: {} с').format(int(self.job.elapsed()))]
        message = getattr(self.job, 'message', '')
        if message:  # a job on the server — sent, in the queue, running, the connection lost …
            parts = [message]
        parts += self.progress_parts(text, result)
        self.status.setText(' · '.join(parts))
        self._tell('progress')
        return None
    self.timer.stop()
    self.stop_button.setEnabled(False)
    self.result = result
    self.refresh()
    if code != 0 and not result.error and result.done:  # a later step failed
        result.error = tr('шаг после scf закончился с кодом {}').format(code)
    if result.error or not result.done or result.energy is None:
        program = 'CP2K' if self.program == 'cp2k' else 'pw.x'
        why = result.error or (tr('остановлен') if self.job.stopped else tr('{} закончил с кодом {}').format(program, code))
        # the name of the output only — the whole path, a word without spaces, widened the page; the
        # path is in the tooltip (and the folder — the button under the calculation)
        self.status.setText(tr('Расчёт не закончен: ') + why + ' · ' + self.output_path().name)
        self.status.setToolTip(str(self.output_path()))
        self._tell('end')
        return result
    self.status.setText(tr('Готово за {} с · ').format(int(self.job.elapsed())) + self.output_path().name)
    self.status.setToolTip(str(self.output_path()))
    text = self.summary_text(result)
    bands = self.band_data()
    if bands is not None and result.highest is not None:  # the gap along the path
        found, _, e0 = bands
        values = [e for row in found.energies for e in row]
        top = max((e for e in values if e <= e0 + 1e-3), default=None)
        bottom = min((e for e in values if e > e0 + 1e-3), default=None)
        if top is not None and bottom is not None:
            text += '<br>' + tr('Щель по пути в зоне Бриллюэна: {} эВ').format(f'{bottom - top:.3f}')
        from modules.compass.chemistry import band_gap

        # direct or indirect, and where its edges are (the number above stays: the levels by E0 of the scf run)
        path = bands[1]
        detail = band_gap.gap(found.energies, band_gap.occupied_bands(
            self.output_path().read_text(encoding='utf-8', errors='replace')), path['x'], [tuple(t) for t in path['ticks']])
        if detail is not None:
            text += '<br>' + band_gap.text(detail)
        cone = self.cone_data(found, path, self.output_path().read_text(encoding='utf-8', errors='replace'))
        if cone is not None:
            from modules.compass.chemistry import layer

            text += '<br>' + layer.text(cone[0])
    strained = self.elastic_data() if self.program != 'cp2k' else None
    if strained is not None:
        text = '<br>'.join(self.elastic_lines(strained)) + '<br>' + tr('Ниже — последний расчёт ряда.') + '<br>' + text
    series = self.eos_data() if self.program != 'cp2k' else None
    if series is not None:  # the fit first: the energy above is that of the last volume of the series
        text = '<br>'.join(self.eos_lines(series)) + '<br>' + tr('Ниже — последний объём ряда.') + '<br>' + text
    converging = self.series_data() if self.program != 'cp2k' else None
    if converging is not None:
        text = '<br>'.join(self.series_lines(converging)) + '<br>' + tr('Ниже — последняя точка ряда.') + '<br>' + text
    states = self.states_data() if self.program != 'cp2k' else None
    if states is not None and states[1]:
        text = self.states_table(states) + '<br>' + tr('Ниже — последний расчёт ряда.') + '<br>' + text
    if self.program == 'cp2k':
        text += self.multiwfn_line()
    self.summary.setText(text)
    self._record(result)
    self.open_button.setEnabled(result.atoms != () and getattr(self, 'steps_run', None) is not None
                                and len(self.steps_run) == 1)
    branches = self.phonon_data()
    if branches is not None:
        self.plot_button.setText(tr('Показать фононные ветви'))
        self.plot_button.show()
        self.plot_button.setEnabled(True)
    elif strained is not None and strained[0] is not None:
        self.plot_button.setText(tr('Показать E(ε)'))
        self.plot_button.show()
        self.plot_button.setEnabled(True)
    elif series is not None:
        self.plot_button.setText(tr('Показать E(V)'))
        self.plot_button.show()
        self.plot_button.setEnabled(True)
    elif converging is not None and converging[1] is not None:
        self.plot_button.setText(tr('Показать сходимость'))
        self.plot_button.show()
        self.plot_button.setEnabled(True)
    elif bands is not None or self.dos_data() is not None:
        self.plot_button.setText(tr('Показать зоны') if bands is not None else tr('Показать плотность состояний'))
        self.plot_button.show()
        self.plot_button.setEnabled(True)
    self._tell('end')
    return result

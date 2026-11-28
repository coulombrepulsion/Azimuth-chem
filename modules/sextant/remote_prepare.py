"""Sextant: the folder of a calculation for a SLURM server, before it is sent (modules/sextant/remote_job.py sends
and watches it).

§1 PURPOSE
    The inputs of a molecule (ORCA, MOPAC) or of a crystal (Quantum ESPRESSO, CP2K) with the processes and the memory
    of the plan of the server, job.sh of cluster.job_script, the helper of the token and the intent of sending
    (azimuth/runtime/runs.py) written before anything reaches the server, an empty output that the watching fills.
§4 SPECIFICATION
    prepare_remote(molecule, calculation, constraints, root, chosen, setup='', now=None, neb=None, text=None,
    kind='orca') -> runner.JobSpec; prepare_qe(folder, steps, chosen, setup='', name='crystal', kind='qe') -> JobSpec;
    mopac_threads(text, threads) -> text. Also named from remote_job (remote_job.prepare_remote …).
§7 TESTS tests/sextant/test_remote_job.py, tests/sextant/test_remote_submission.py.
"""

from __future__ import annotations

import re
from dataclasses import replace
from datetime import datetime

from azimuth.i18n import tr
from azimuth.runtime import runs
from modules.sextant import cluster, runner
from modules.sextant.inputs import input_files


def prepare_remote(molecule, calculation, constraints, root, chosen, setup='', now=None, neb=None, text=None, kind='orca'):
    from modules.sextant.remote_job import REMOTE_KINDS

    if kind not in REMOTE_KINDS:
        raise ValueError(tr('На сервере считаются ORCA и MOPAC.'))
    calc = replace(calculation, cores=chosen.processes, memory_mb=chosen.maxcore)
    files = input_files(kind, molecule, calc, constraints, neb)  # validates
    main = next(iter(files))  # <base>.inp, named after the calculation (<base>.mop of MOPAC)
    if text is not None:
        if not text.strip():
            raise ValueError(tr('Входной файл пуст.'))
        files[main] = (cluster.with_processes(text.rstrip('\n') + '\n', chosen.processes, chosen.maxcore) if kind == 'orca'
                       else text.rstrip('\n') + '\n')
    if kind == 'mopac':
        files[main] = mopac_threads(files[main], chosen.processes)
    guess = runner.start_orbitals(kind, calc)  # uploaded with the folder
    folder = runner.job_folder(root, molecule, kind, now or datetime.now())
    for name, content in files.items():
        # newline='\n': the files go to Linux; on Windows Python wrote \r\n, and sbatch refused job.sh («DOS line
        # breaks»), bash read «cd …\r» (the owner's Windows, 2026-11-24)
        (folder / name).write_text(content, encoding='utf-8', newline='\n')
    runner.copy_start_orbitals(guess, folder)
    base = main.rsplit('.', 1)[0]
    (folder / 'job.sh').write_text(cluster.job_script(chosen, setup, f'az-{molecule.formula}', base, kind), encoding='utf-8',
                                   newline='\n')
    output = folder / f'{base}.out'
    output.write_bytes(b'')
    # the intent of sending — the attempt id and the token — kept before anything reaches the server
    (folder / runs.HELPER).write_text(runs.helper_script(), encoding='ascii', newline='\n')
    runs.write(folder, runs.new_submission(name_hint=molecule.formula))
    return runner.JobSpec(kind, folder, ('server',), output, {}, output)


def prepare_qe(folder, steps, chosen, setup='', name='crystal', kind='qe'):
    """A job of Quantum ESPRESSO for the server in its prepared folder (the inputs of the steps and the
    pseudopotentials in pseudo/, written by qe_window.QePanel): job.sh (cluster.job_script, program 'qe'), the helper
    and the intent of sending (as prepare_remote), an empty pw.out. Returns the JobSpec of kind 'qe'. Kind
    'cp2k' — its input azimuth.inp, the output cp2k.out (cluster.cp2k_lines)."""
    from pathlib import Path

    folder = Path(folder)
    (folder / 'job.sh').write_text(cluster.job_script(chosen, setup, f'az-{kind}-{name}', 'pw', kind, steps),
                                   encoding='utf-8', newline='\n')
    output = folder / ('cp2k.out' if kind == 'cp2k' else 'pw.out')
    output.write_bytes(b'')
    (folder / runs.HELPER).write_text(runs.helper_script(), encoding='ascii', newline='\n')
    runs.write(folder, runs.new_submission(name_hint=f'{kind}-{name}'))
    return runner.JobSpec(kind, folder, ('server',), output, {}, output)


def mopac_threads(text, threads):
    """«THREADS=n» on the first line of keywords of a .mop (MOPAC takes every core of the machine otherwise —
    on a shared server the job keeps to the cores SLURM gave it, with OMP_NUM_THREADS of job.sh); a THREADS written by
    hand stays. ASSUMPTION: one THREADS on the first job of the file holds for the run (MOPAC 2016 manual: «THREADS=n —
    set the number of threads»); not yet checked on the servers."""
    lines = text.split('\n')
    if lines and not re.search(r'\bTHREADS\s*=', lines[0], re.I):
        lines[0] = lines[0].rstrip() + f' THREADS={int(threads)}'
    return '\n'.join(lines)

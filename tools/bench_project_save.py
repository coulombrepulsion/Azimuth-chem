"""Timing of saving a project into project.sqlite (the external review of 2026-11-09, item 5).

Projects of N molecules (a 30-atom molecule each) with M attempts per molecule are made in a temporary folder; one
attempt state is changed and the project saved through projects.edit (what a queue does after each calculation) —
R repetitions, the median, the 90th percentile and the maximum are printed with the size of the database. Run:
    .venv/bin/python tools/bench_project_save.py [--repeat 30]
"""

import argparse
import platform
import statistics
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from azimuth import projects  # noqa: E402
from azimuth.core import Calculation, read_xyz  # noqa: E402

ATOMS = 30
MOLECULE = read_xyz(f'{ATOMS}\nbench\n' + '\n'.join(f'C {k * 1.5:.3f} {k % 3 * 0.7:.3f} 0' for k in range(ATOMS)))


def made(folder, molecules, attempts):
    project = projects.Project.create(folder)
    for k in range(molecules):
        entry = project.add(MOLECULE, Calculation(), name=f'm{k:03d}')
        for a in range(attempts):
            project.record(entry['id'], f'a{k}-{a}', MOLECULE, Calculation(), 'orca', 'failed', note='x' * 40)
    project.save()
    return project


def timed(project, repeat):
    ids = [e['id'] for e in project.molecules]
    times = []
    for r in range(repeat):
        start = time.perf_counter()
        with projects.edit(project.path) as fresh:
            entry = fresh.entry(ids[r % len(ids)])
            attempt = entry['attempts'][-1]
            attempt['note'] = f'run {r}'
        times.append((time.perf_counter() - start) * 1000)
    return times


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repeat', type=int, default=30)
    args = parser.parse_args()
    print(f'{platform.system()} {platform.machine()}, Python {platform.python_version()}, {ATOMS} atoms per molecule')
    print(f'{"molecules":>9} {"attempts":>8} {"db, KB":>8} {"median, ms":>11} {"p90, ms":>8} {"max, ms":>8}')
    for molecules, attempts in ((5, 1), (44, 1), (44, 10), (200, 5), (200, 50)):
        with tempfile.TemporaryDirectory() as tmp:
            project = made(Path(tmp) / 'p', molecules, attempts)
            times = sorted(timed(project, args.repeat))
            size = project.database.stat().st_size / 1024
            p90 = times[int(0.9 * (len(times) - 1))]
            print(f'{molecules:>9} {attempts:>8} {size:>8.0f} {statistics.median(times):>11.1f} {p90:>8.1f} {times[-1]:>8.1f}')


if __name__ == '__main__':
    main()

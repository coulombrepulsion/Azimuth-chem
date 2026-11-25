"""A small reproducible set of workloads to measure before optimizing.
What is measured (each R times; the median, the slowest and, where it matters, the peak memory):
  start — a new process to the first window: imports, QApplication, Studio (the window of the sections);
               the cold first run is printed apart from the repeated ones
  hub — the whole program window (HubWindow) in a new process
  parse — reading the largest outputs of the examples and the test data (and any file given with --output),
               time and peak Python memory
  orbitals — an orbital on its grid (gto) and its isosurface (VTK) from the .fchk examples
  save — saving a project of 44 × 10 and 200 × 50 attempts (tools/bench_project_save.py)
  hash — the SHA-256 fingerprint of a 200 MB file, cold and remembered
  draw — drawing the model of a molecule of 300 and 1500 atoms (the built-in renderer, offscreen)
  theme — switching the theme of the window there and back
  project — a real project (--project, by default the one with the most molecules in the projects
               folder), copied into a temporary folder first — the original is never touched: opening it, the first
               choice of each molecule in Compass, in Spectrum and in Sextant, choosing them again, the list rebuilt,
               saving, the batch mode on and off; with --profile, where the time of each of these goes
Nothing is changed in the settings of the program: the windows use a temporary settings file and folders.
Run (on the computer to be measured, the window does not show):
    .venv/bin/python tools/bench_workloads.py # all, R = 3
    .venv/bin/python tools/bench_workloads.py --repeat 5 --output ~/calc/big.out --only parse
    .venv/bin/python tools/bench_workloads.py --only draw --profile # where the time of a frame and of
                                                                      # the theme goes (cProfile, the top 30)
    .venv/bin/python tools/bench_workloads.py --only hub --profile # where the time of a start goes
    .venv/bin/python tools/bench_workloads.py --only project --profile # your project of many molecules
    .venv/bin/python tools/bench_workloads.py --only project --project ~/Documents/Azimuth/Проекты/cs
The table is printed; everything is also written to bench-<version>-<date>.json in the current folder — send it."""

import argparse
import json
import os
import platform
import statistics
import subprocess
import sys
import tempfile
import time
import tracemalloc
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

RESULTS = []


def report(group, name, times_ms, **extra):
    times = sorted(times_ms)
    row = {'group': group, 'name': name, 'n': len(times), 'median_ms': round(statistics.median(times), 1),
           'max_ms': round(times[-1], 1), **extra}
    RESULTS.append(row)
    more = '  '.join(f'{k}={v}' for k, v in extra.items())
    print(f'{group:<9} {name:<44} {row["median_ms"]:>10.1f} {row["max_ms"]:>10.1f}  {more}', flush=True)


def timed(fn, repeat):
    out = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        out.append((time.perf_counter() - start) * 1000)
    return out


# -- start: a new process each time ---------------------------------------------------------------------------------
START = r'''
import json, os, sys, tempfile, time
t0 = time.perf_counter()
sys.path.insert(0, {root!r})
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['AZIMUTH_RECOVERY_DIR'] = tempfile.mkdtemp()
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
app = QApplication([])
t1 = time.perf_counter()
{body}
t3 = time.perf_counter()
print(json.dumps({{'imports_qt_ms': (t1 - t0) * 1000, 'window_ms': (t2 - t1) * 1000, 'total_ms': (t3 - t0) * 1000}}))
'''
STUDIO = '''from azimuth.app import Studio
t15 = time.perf_counter()
w = Studio(example=True, probe_machine=False)
app.processEvents()
t2 = time.perf_counter()'''
HUB = '''from hub.window import HubWindow
prefs = QSettings(os.path.join(tempfile.mkdtemp(), 'hub.ini'), QSettings.Format.IniFormat)
w = HubWindow(None, preferences=prefs)  # 0.109.4: the home page, as the program opens (was 'atlas')
w.show()
app.processEvents()
t2 = time.perf_counter()'''


def in_process(body, repeat, name):
    rows = []
    for k in range(repeat + 1):  # the first one is the cold start
        run = subprocess.run([sys.executable, '-c', START.format(root=str(ROOT), body=body)], capture_output=True,
                             text=True, encoding='utf-8', errors='replace', timeout=300)
        line = (run.stdout.strip().splitlines() or [''])[-1]
        try:
            rows.append(json.loads(line))
        except ValueError:
            print(f'start     {name}: did not start\n{run.stderr[-1500:]}')
            return
    cold, warm = rows[0], rows[1:]
    report('start', f'{name}: first (cold) run', [cold['total_ms']], window_ms=round(cold['window_ms']))
    report('start', f'{name}: repeated runs', [r['total_ms'] for r in warm],
           window_ms=round(statistics.median(r['window_ms'] for r in warm)))


PROFILED_START = r'''
import cProfile, io, json, os, pstats, sys, tempfile
sys.path.insert(0, {root!r})
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['AZIMUTH_RECOVERY_DIR'] = tempfile.mkdtemp()
import time
profile = cProfile.Profile()
profile.enable()
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
app = QApplication([])
{body}
profile.disable()
out = {{}}
for order in ('tottime', 'cumulative'):
    text = io.StringIO()
    pstats.Stats(profile, stream=text).strip_dirs().sort_stats(order).print_stats(45)
    out[order] = text.getvalue()
print(json.dumps(out))
'''


def profile_start(body, name):
    """The measurement says the
    window, not the imports (1.4–1.8 s of it). Where the time of a start goes: the whole start of a new process under
    cProfile, and the slowest imports (python -X importtime)."""
    run = subprocess.run([sys.executable, '-c', PROFILED_START.format(root=str(ROOT), body=body)], capture_output=True,
                         text=True, encoding='utf-8', errors='replace', timeout=600)
    try:
        found = json.loads((run.stdout.strip().splitlines() or [''])[-1])
    except ValueError:
        print(f'start     {name}: the profile did not run\n{run.stderr[-1500:]}')
        return
    for order, text in found.items():
        print(f'\n--- profile: the start of {name}, by {order} ---\n{text}')
        RESULTS.append({'group': 'profile', 'name': f'the start of {name} ({order})', 'text': text})
    code = (f'import sys, os; sys.path.insert(0, {str(ROOT)!r}); '
            "os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen'); import hub.window")
    run = subprocess.run([sys.executable, '-X', 'importtime', '-c', code], capture_output=True, text=True,
                         encoding='utf-8', errors='replace', timeout=600)
    rows = []
    for line in run.stderr.splitlines():
        parts = line.split('|')
        if len(parts) == 3 and parts[1].strip().isdigit():
            rows.append((int(parts[1]), parts[2].strip(), len(parts[2]) - len(parts[2].lstrip())))
    top = sorted((r for r in rows if r[2] <= 3), reverse=True)[:30]  # the top levels: cumulative, µs
    text = '\n'.join(f'{us / 1000:9.1f} ms  {module}' for us, module, _ in top)
    print(f'\n--- imports of hub.window: the slowest (cumulative) ---\n{text}')
    RESULTS.append({'group': 'profile', 'name': 'imports of hub.window (cumulative)', 'text': text})


LINE_TIMED_START = r"""
import json, linecache, os, sys, tempfile, time
sys.path.insert(0, {root!r})
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
os.environ['AZIMUTH_RECOVERY_DIR'] = tempfile.mkdtemp()
WATCH = {watch!r}
spent = {{}}


def tracer(frame, event, arg):
    code = frame.f_code
    if (os.path.basename(code.co_filename), code.co_name) not in WATCH:
        return None
    state = [None, 0.0]

    def local(frame, event, arg):
        now = time.perf_counter()
        if state[0] is not None:
            key = (code.co_filename, code.co_name, state[0])
            spent[key] = spent.get(key, 0.0) + now - state[1]
        state[0] = frame.f_lineno if event == 'line' else None
        state[1] = time.perf_counter()
        return local

    return local


from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSettings
app = QApplication([])
sys.settrace(tracer)
{body}
sys.settrace(None)
rows = sorted(spent.items(), key=lambda kv: -kv[1])[:40]
print(json.dumps([[os.path.basename(f), name, line, round(s * 1000, 1), linecache.getline(f, line).strip()[:110]]
                  for (f, name, line), s in rows]))
"""
# the functions of the start whose lines are timed (the profile names them; their own time is mostly the
# constructors of Qt widgets, which cProfile does not see as calls)
LINE_TIMED = [('layout.py', 'structure_page'), ('panel.py', '__init__'), ('calculation_page.py', 'calculation_page'),
              ('app.py', 'build'), ('app.py', '_apply_theme'), ('app.py', '__init__'), ('window.py', '__init__')]


def time_start_lines(body, name):
    """The slowest lines of the functions that build the window (LINE_TIMED), each with the time of what it
    calls; approximate — tracing slows Python code, not the C++ of Qt."""
    run = subprocess.run([sys.executable, '-c', LINE_TIMED_START.format(root=str(ROOT), body=body,
                                                                        watch=set(LINE_TIMED))],
                         capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    try:
        rows = json.loads((run.stdout.strip().splitlines() or [''])[-1])
    except ValueError:
        print(f'start     {name}: the line timing did not run\n{run.stderr[-1500:]}')
        return
    text = '\n'.join(f'{ms:8.1f} ms  {f}:{line} {fn}  {src}' for f, fn, line, ms, src in rows)
    print(f'\n--- the slowest lines of the start of {name} ---\n{text}')
    RESULTS.append({'group': 'profile', 'name': f'the slowest lines of the start of {name}', 'text': text})


# -- parse --------------------------------------------------------------------------------------------------------
def largest_outputs(extra):
    found = [p for folder in (ROOT / 'examples', ROOT / 'tests' / 'data') if folder.is_dir()
             for p in folder.rglob('*') if p.suffix in ('.out', '.log') and p.is_file()]
    found.sort(key=lambda p: p.stat().st_size, reverse=True)
    return [Path(p).expanduser() for p in extra] + found[:5]


def bench_parse(repeat, extra):
    from modules.spectrum.readers.outputs import read_any

    for path in largest_outputs(extra):
        text = path.read_text(encoding='utf-8', errors='replace')
        try:
            times = timed(lambda: read_any(text, str(path)), repeat)
        except Exception as exc:  # noqa: BLE001 — a file this reader does not take is said, not fatal
            print(f'parse     {path.name}: not read ({exc})')
            continue
        tracemalloc.start()
        read_any(text, str(path))
        peak = tracemalloc.get_traced_memory()[1]
        tracemalloc.stop()
        report('parse', path.name, times, size_mb=round(path.stat().st_size / 1e6, 2), peak_mb=round(peak / 1e6, 1))


# -- orbitals -----------------------------------------------------------------------------------------------------
def bench_orbitals(repeat):
    from modules.spectrum.analysis.orbitals import orbital_cube
    from modules.spectrum.readers.orbital_files import read_orbitals

    for path in sorted((ROOT / 'examples' / '6-orbitals').glob('*.fchk')):
        orbitals = read_orbitals(path.read_text(encoding='utf-8', errors='replace'))
        homo, _ = orbitals.frontier()
        cube = orbital_cube(orbitals, homo)
        report('orbitals', f'{path.name}: HOMO on its grid', timed(lambda: orbital_cube(orbitals, homo), repeat),
               points=int(cube.values[..., 0].size))
        try:
            from modules.compass.view.surfaces import isosurface

            report('orbitals', f'{path.name}: isosurface (VTK)', timed(lambda: isosurface(cube, 0.05), repeat))
        except ImportError:
            print('orbitals  isosurface: VTK not installed')


# -- save ---------------------------------------------------------------------------------------------------------
def bench_save(repeat):
    sys.path.insert(0, str(ROOT / 'tools'))
    from bench_project_save import made, timed as save_times

    for molecules, attempts in ((44, 10), (200, 50)):
        with tempfile.TemporaryDirectory() as tmp:
            project = made(Path(tmp) / 'p', molecules, attempts)
            report('save', f'project {molecules} × {attempts}', save_times(project, max(repeat, 10)),
                   db_kb=round(project.database.stat().st_size / 1024))


# -- hash ---------------------------------------------------------------------------------------------------------
def bench_hash(repeat):
    from azimuth.runtime import provenance

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / 'big.out'
        block = os.urandom(1 << 20)
        with open(path, 'wb') as f:
            for _ in range(200):
                f.write(block)
        provenance._seen.clear()
        cold = timed(lambda: (provenance._seen.clear(), provenance.fingerprint(path)), repeat)
        warm = timed(lambda: provenance.fingerprint(path), repeat)
        report('hash', '200 MB file, read and hashed', cold)
        report('hash', '200 MB file, remembered', warm)


# -- draw and theme (one window) ----------------------------------------------------------------------------------
def chain(n):
    lines = [f'{n}', 'bench']
    for k in range(n):
        lines.append(f'C {1.5 * (k % 40):.3f} {1.5 * ((k // 40) % 40):.3f} {1.5 * (k // 1600):.3f}')
    return '\n'.join(lines) + '\n'


PROFILE = False


def profiled(name, fn):
    """Fn once under cProfile; the 30 functions with the most time of their own and with the most time
    under them, written to the results as text too."""
    if not PROFILE:
        return
    import cProfile
    import io
    import pstats

    profile = cProfile.Profile()
    profile.enable()
    fn()
    profile.disable()
    for order in ('tottime', 'cumulative'):
        out = io.StringIO()
        pstats.Stats(profile, stream=out).strip_dirs().sort_stats(order).print_stats(30)
        text = out.getvalue()
        print(f'\n--- profile: {name}, by {order} ---\n{text}')
        RESULTS.append({'group': 'profile', 'name': f'{name} ({order})', 'text': text})


def bench_window(repeat):
    os.environ['AZIMUTH_RECOVERY_DIR'] = tempfile.mkdtemp()
    from PySide6.QtWidgets import QApplication

    from azimuth.app import Studio
    from azimuth.core import read_xyz

    app = QApplication.instance() or QApplication([])
    window = Studio(example=True, probe_machine=False)
    window.resize(1400, 900)
    window.viewer.engine = 'raster'
    window.viewer.set_native(False)
    window.show()
    window.navigate(0)  # Compass
    for n in (300, 1500):
        window.load_molecule(read_xyz(chain(n)))
        app.processEvents()
        viewer = window.viewer

        def draw():
            viewer._model_image = None
            viewer.grab()

        report('draw', f'model of {n} atoms, one frame', timed(draw, repeat))
        if n == 1500:
            profiled('a frame of 1500 atoms', draw)
    if hasattr(window, 'theme') and window.theme.count() > 1:
        start = window.theme.currentIndex()
        other = 1 if start == 0 else 0

        def switch():
            window.theme.setCurrentIndex(other)
            app.processEvents()
            window.theme.setCurrentIndex(start)
            app.processEvents()

        report('theme', 'theme there and back', timed(switch, repeat))
        profiled('the theme there and back', switch)
    window.dirty = False
    for d in window.all_documents():
        d.dirty = False
    window.close()


# -- project: a real project of many molecules, in one window ------------------------------------------------------
def biggest_project(root=None):
    """The project with the most molecules in the projects folder (None when there is none)."""
    from azimuth import projects
    from azimuth.project_folders import projects_root

    root = Path(root) if root else projects_root('')
    best, count = None, -1
    for manifest in root.glob('*/' + projects.MANIFEST):
        try:
            n = len(projects.Project.view(manifest).molecules)
        except Exception:  # noqa: BLE001 — a damaged project is not measured
            continue
        if n > count:
            best, count = manifest, n
    return best


def bench_project(repeat, path=None):
    import shutil

    from PySide6.QtWidgets import QApplication, QMessageBox

    from azimuth import projects
    from azimuth.app import Studio

    source = Path(path).expanduser() if path else biggest_project()
    if source is None:
        raise ValueError('no project found: give one with --project')
    if source.is_dir():
        source = source / projects.MANIFEST
    tmp = Path(tempfile.mkdtemp(prefix='azimuth-bench-project-'))
    copy = tmp / source.parent.name
    started = time.perf_counter()
    shutil.copytree(source.parent, copy)
    print(f'project   copied {source.parent.name} ({(time.perf_counter() - started):.1f} s) into {copy}', flush=True)
    manifest = copy / projects.MANIFEST
    os.environ['AZIMUTH_RECOVERY_DIR'] = tempfile.mkdtemp()
    os.environ['AZIMUTH_PROJECTS_DIR'] = str(tmp / 'new-projects')
    QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.StandardButton.No)  # never a modal question
    QMessageBox.information = QMessageBox.warning = QMessageBox.critical = staticmethod(lambda *a, **k: 0)
    app = QApplication.instance() or QApplication([])
    window = Studio(example=False, probe_machine=False)
    window.resize(1400, 900)
    window.unfinished.timer.stop()
    window.show()
    app.processEvents()
    n = len(projects.Project.view(manifest).molecules)

    def opened():
        window.open_research_project(str(manifest), stay=True)
        app.processEvents()

    report('project', f'open the project ({n} molecules)', timed(opened, 1))
    table = window.project_molecules

    def choose(row):
        table.setCurrentCell(row, 0)
        app.processEvents()

    def every(label, section, profile_name=None):
        window.navigate(section)
        app.processEvents()
        times = []
        for row in range(table.rowCount()):
            start = time.perf_counter()
            choose(row)
            times.append((time.perf_counter() - start) * 1000)
        slowest = sorted(range(len(times)), key=lambda k: -times[k])[:3]
        names = [table.item(k, 1).text()[:40] for k in slowest]
        report('project', label, times, total_s=round(sum(times) / 1000, 1),
               slowest=[f'{names[i]} {times[k]:.0f} ms' for i, k in enumerate(slowest)])
        if profile_name and PROFILE:
            profiled(profile_name, lambda: [choose(row) for row in reversed(range(table.rowCount()))])

    every('each molecule chosen first, Compass', 0)
    every('each molecule chosen again, Compass', 0, 'the molecules chosen again in Compass')
    every('each molecule chosen, Spectrum', 2, 'the molecules chosen in Spectrum')
    every('each molecule chosen, Sextant', 1, 'the molecules chosen in Sextant')
    window.navigate(0)

    def rebuilt():
        window._project_shown = None
        window.refresh_project_navigation()
        app.processEvents()

    report('project', 'the list rebuilt', timed(rebuilt, repeat))
    profiled('the list rebuilt', rebuilt)

    def saved():
        window.save_research_project()
        app.processEvents()

    report('project', 'save (nothing changed)', timed(saved, repeat))
    profiled('save', saved)

    def batch_mode():
        window.set_project_batch_mode(True)
        app.processEvents()
        window.set_project_batch_mode(False)
        app.processEvents()

    report('project', 'batch mode on and off', timed(batch_mode, repeat))
    window.dirty = False
    for d in window.all_documents():
        d.dirty = False
    window.close()
    shutil.rmtree(tmp, ignore_errors=True)


GROUPS = ('start', 'hub', 'parse', 'orbitals', 'save', 'hash', 'draw', 'project')


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--repeat', type=int, default=3)
    parser.add_argument('--output', action='append', default=[], help='an output of a calculation to read (repeatable)')
    parser.add_argument('--only', action='append', choices=GROUPS, help='only these groups (repeatable)')
    parser.add_argument('--profile', action='store_true', help='also profile a frame and the theme (with draw)')
    parser.add_argument('--project', help='project: the folder (or project.qcc) to measure on a copy')
    args = parser.parse_args()
    global PROFILE
    PROFILE = args.profile
    # the windows measured read and write a settings file of their own (as the tests), never the user's
    os.environ.setdefault('AZIMUTH_SETTINGS_FILE', str(Path(tempfile.mkdtemp(prefix='azimuth-bench-settings-'))
                                                       / 'settings.ini'))
    chosen = args.only or tuple(g for g in GROUPS if g != 'project' or args.project)  # project: when asked
    from azimuth import __version__

    machine = {'azimuth': __version__, 'system': platform.platform(), 'machine': platform.machine(),
               'processor': platform.processor(), 'cpus': os.cpu_count(), 'python': platform.python_version()}
    try:
        import PySide6

        machine['pyside6'] = PySide6.__version__
    except ImportError:
        pass
    print(' · '.join(f'{k} {v}' for k, v in machine.items()))
    print(f'{"group":<9} {"what":<44} {"median, ms":>10} {"max, ms":>10}')
    steps = {'start': lambda: in_process(STUDIO, args.repeat, 'Studio window'),
             'hub': lambda: (in_process(HUB, args.repeat, 'whole program (hub)'),
                             (profile_start(HUB, 'the whole program (hub)'), time_start_lines(HUB, 'the whole program (hub)'))
                             if PROFILE else None),
             'parse': lambda: bench_parse(args.repeat, args.output),
             'orbitals': lambda: bench_orbitals(args.repeat),
             'save': lambda: bench_save(args.repeat),
             'hash': lambda: bench_hash(args.repeat),
             'draw': lambda: bench_window(args.repeat),
             'project': lambda: bench_project(args.repeat, args.project)}
    for group in chosen:
        try:
            steps[group]()
        except Exception as exc:  # noqa: BLE001 — one group failing does not stop the others
            print(f'{group:<9} failed: {type(exc).__name__}: {exc}')
            RESULTS.append({'group': group, 'error': f'{type(exc).__name__}: {exc}'})
    name = f'bench-{__version__}-{datetime.now():%Y%m%d-%H%M}.json'
    Path(name).write_text(json.dumps({'machine': machine, 'results': RESULTS}, ensure_ascii=False, indent=1),
                          encoding='utf-8')
    print(f'\nЗаписано: {Path(name).resolve()}')


if __name__ == '__main__':
    main()

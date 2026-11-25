"""The timing of a test run (internal; TEST_FEEDBACK_PLAN.md, stage 1): phases of every test, collection apart, the
environment of the run, a line while one test lasts long, a summary for the developer and a JSON report.

Loaded by tools/test.py (`-p tools.pytest_timing`), or by hand:
    .venv/bin/python -m pytest -p tools.pytest_timing tests/projects
Environment (all optional):
    AZIMUTH_TEST_REPORT=<file.json>  — where the report goes (none: only the summary in the terminal)
    AZIMUTH_TEST_PROFILE=<name>      — the profile written into the report (tools/test.py sets it)
    AZIMUTH_TEST_HEARTBEAT=<s>       — a line every <s> seconds while no test ends (15; 0 — off)
    AZIMUTH_TEST_SLOW=<s>            — a test running longer is named «долгий» in that line (30)
The line says the runner is alive, not that the test is: a test hung in C code shows the same line. The summary
(«Время тестов») lists the slowest tests and files and the time of the phases; with workers (xdist) the sum of the
times of the tests is not the time waited.
The report holds no secrets: the commit, whether files are changed, the versions, the platform, the graphics mode and
the thread limits of numerical libraries — not the settings of a server or the projects of the user."""

import json
import os
import platform
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
THREAD_VARIABLES = ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'VECLIB_MAXIMUM_THREADS',
                    'NUMEXPR_NUM_THREADS')
GRAPHICS_VARIABLES = ('QT_QPA_PLATFORM', 'AZIMUTH_NO_VTK', 'QT_OPENGL', 'LIBGL_ALWAYS_SOFTWARE')


def _git(*args):
    try:
        run = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=10)
        return run.stdout.strip() if run.returncode == 0 else ''
    except (OSError, subprocess.SubprocessError):
        return ''


def _version(distribution):
    try:
        from importlib.metadata import version

        return version(distribution)
    except Exception:  # noqa: BLE001 — not installed
        return ''


def environment():
    """What the times depend on: the commit and its changes, the interpreter, the machine, Qt/VTK, the threads."""
    changed = _git('status', '--porcelain', '--untracked-files=no')
    return {
        'git_commit': _git('rev-parse', 'HEAD'),
        'dirty': bool(changed),
        'changed_files': len(changed.splitlines()) if changed else 0,
        'python': sys.version.split()[0],
        'pytest': pytest.__version__,
        'os': platform.platform(),
        'machine': platform.machine(),
        'cpu_count': os.cpu_count(),
        'processor': platform.processor(),
        'pyside6': _version('PySide6-Essentials') or _version('PySide6'),
        'vtk': _version('vtk'),
        'numpy': _version('numpy'),
        'graphics': {k: os.environ.get(k, '') for k in GRAPHICS_VARIABLES},
        'threads': {k: os.environ.get(k, '') for k in THREAD_VARIABLES},
        'workers': int(os.environ.get('PYTEST_XDIST_WORKER_COUNT', '1') or 1),
        'command': [Path(sys.executable).name, *sys.argv[1:]] if sys.argv else [],
    }


class Timing:
    def __init__(self, config):
        self.config = config
        self.report_path = os.environ.get('AZIMUTH_TEST_REPORT', '')
        self.profile = os.environ.get('AZIMUTH_TEST_PROFILE', '')
        self.heartbeat = float(os.environ.get('AZIMUTH_TEST_HEARTBEAT', '15') or 0)
        self.slow = float(os.environ.get('AZIMUTH_TEST_SLOW', '30') or 30)
        self.started = time.monotonic()
        self.environment = environment()  # at the start: the commit and the files the run took, not those at its end
        self.collected_at = None
        self.selected = 0
        self.deselected = 0
        self.records = []
        self.outcomes = {}  # nodeid -> the outcome of a test that ended (failed beats skipped beats passed)
        self.partial = {}  # the same of the test under way
        self.current = ''
        self.phase = ''
        self.phase_since = time.monotonic()
        self.last_event = time.monotonic()
        self.done = 0
        self.stop = threading.Event()
        self.thread = None

    # -- collection ------------------------------------------------------------------------------------------------
    def pytest_deselected(self, items):
        self.deselected += len(items)

    def pytest_collection_finish(self, session):
        self.collected_at = time.monotonic()
        self.selected = len(session.items)
        if self.heartbeat > 0 and self.thread is None:
            self.thread = threading.Thread(target=self._beat, name='azimuth-test-heartbeat', daemon=True)
            self.thread.start()

    # -- the tests -------------------------------------------------------------------------------------------------
    def pytest_runtest_logstart(self, nodeid, location):
        self.current, self.phase = nodeid, 'setup'
        self.phase_since = self.last_event = time.monotonic()

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(self, item):
        self.phase, self.phase_since = 'call', time.monotonic()
        yield

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_teardown(self, item):
        self.phase, self.phase_since = 'teardown', time.monotonic()
        yield

    def pytest_runtest_logreport(self, report):
        record = {'nodeid': report.nodeid, 'phase': report.when, 'seconds': round(report.duration, 4),
                  'outcome': report.outcome}
        if report.skipped and isinstance(report.longrepr, tuple) and len(report.longrepr) == 3:
            record['skip_reason'] = str(report.longrepr[2])
        if hasattr(report, 'wasxfail'):
            record['xfail'] = str(report.wasxfail)
        worker = getattr(report, 'node', None)
        if worker is not None and getattr(worker, 'gateway', None) is not None:
            record['worker'] = worker.gateway.id
        self.records.append(record)
        rank = {'passed': 0, 'skipped': 1, 'failed': 2}
        old = self.partial.get(report.nodeid, 'passed')
        self.partial[report.nodeid] = report.outcome if rank.get(report.outcome, 0) >= rank.get(old, 0) else old
        if report.when == 'teardown':  # only a test that came to its end has an outcome (an interrupted one has not)
            self.outcomes[report.nodeid] = self.partial.pop(report.nodeid)
            self.done += 1
            self.last_event = time.monotonic()

    def _beat(self):
        while not self.stop.wait(1.0):
            now = time.monotonic()
            if now - self.last_event < self.heartbeat or not self.current:
                continue
            self.last_event = now
            age = now - self.phase_since
            long = ' — долгий тест' if age >= self.slow else ''
            line = (f'\n[тесты идут {_clock(now - self.started)}] {self.done}/{self.selected} · {self.current} '
                    f'({self.phase}, {age:.0f} с){long}\n')
            self._say(line)

    def _say(self, text):
        # while a test runs, the descriptors 1 and 2 of the process are pytest's capture (a line written there is lost,
        # or shown only with a failure): the line goes to the descriptor of the terminal pytest saved before capturing —
        # the terminal, or the log of tools/test.py; without capture (-s) to stderr
        data = text.encode('utf-8', 'replace')
        capture = getattr(self.config.pluginmanager.get_plugin('capturemanager'), '_global_capturing', None)
        for stream in (getattr(capture, 'err', None), getattr(capture, 'out', None)):
            fd = getattr(stream, 'targetfd_save', None)
            if isinstance(fd, int):
                try:
                    os.write(fd, data)
                    return
                except OSError:
                    pass
        try:
            sys.__stderr__.write(text)
            sys.__stderr__.flush()
        except (OSError, ValueError, AttributeError):
            pass

    # -- the end ---------------------------------------------------------------------------------------------------
    def summary(self, exitstatus):
        end = time.monotonic()
        collected = self.collected_at or end
        counts = Counter(self.outcomes.values())
        return {
            'profile': self.profile,
            **self.environment,
            'wall_seconds': round(end - self.started, 2),
            'collection_seconds': round(collected - self.started, 2),
            'run_seconds': round(end - collected, 2),
            'selected_count': self.selected,
            'deselected_count': self.deselected,
            'outcomes': dict(counts),
            'unfinished': sorted(self.partial) + ([self.current] if self.current and self.current not in self.outcomes
                                                  and self.current not in self.partial else []),
            'exit_code': int(exitstatus),
            'tests': self.records,
        }

    def pytest_sessionfinish(self, session, exitstatus):
        self.stop.set()
        if not self.report_path:
            return
        path = Path(self.report_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(self.summary(exitstatus), ensure_ascii=False, indent=1), encoding='utf-8')
        except OSError as exc:
            self._say(f'[timing] отчёт не записан: {exc}\n')

    def pytest_terminal_summary(self, terminalreporter):
        if not self.records:
            return
        write = terminalreporter.write_line
        terminalreporter.section('Время тестов')
        end = time.monotonic()
        collected = self.collected_at or end
        write(f'сбор {collected - self.started:.1f} с · выполнение {end - collected:.1f} с · всего '
              f'{end - self.started:.1f} с · тестов {self.selected}')
        phases = defaultdict(float)
        per_test = defaultdict(float)
        per_file = defaultdict(float)
        for r in self.records:
            phases[r['phase']] += r['seconds']
            per_test[r['nodeid']] += r['seconds']
            per_file[r['nodeid'].split('::')[0]] += r['seconds']
        write('фазы: ' + ', '.join(f'{k} {phases[k]:.1f} с' for k in ('setup', 'call', 'teardown')))
        write('самые долгие тесты:')
        for nodeid, seconds in sorted(per_test.items(), key=lambda kv: -kv[1])[:10]:
            write(f'  {seconds:7.2f} с  {nodeid}')
        write('самые долгие файлы:')
        for name, seconds in sorted(per_file.items(), key=lambda kv: -kv[1])[:10]:
            write(f'  {seconds:7.2f} с  {name}')
        if self.report_path:
            write(f'отчёт: {self.report_path}')


def _clock(seconds):
    seconds = int(seconds)
    return f'{seconds // 60}:{seconds % 60:02d}'


def pytest_configure(config):
    if not hasattr(config, 'workerinput'):  # the controller of xdist (or a run without it) times; workers report
        config.pluginmanager.register(Timing(config), 'azimuth-timing')

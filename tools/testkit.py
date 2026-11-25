"""The runner of tools/test.py and tools/run_test_groups.py (internal; TEST_FEEDBACK_PLAN.md, stages 1–3).

run(): pytest in a child process of its own (the interpreter of the program, the folder of the program as its cwd),
with the timing plugin (tools/pytest_timing.py) and JUnit XML; its output goes to the terminal as it comes and into
log.txt; a limit of time for the whole; Ctrl+C or the limit stops only that child and what it started (gently, then
for good after 10 s). The result says what happened: passed, failed, empty (nothing collected — an error of the
setup, never a success), interrupted (Ctrl+C or an error of collection), timeout, crashed (a native library fell: the
end of the log is shown, not only the lines FAILED) — only «passed» is a success.
Reports: artifacts/tests/<time>-<profile>/{log.txt, summary.json, junit.xml} (artifacts/ is not in git).
groups(): the groups of «isolated» — each folder of tests/ with tests and each test file at its top.
run_parts(): the same set in several pytest processes at once — the files split by their times in the last full run
(plan()), each part a run of its own in part-N/ with its own settings, projects and logs (tests/conftest.py makes them
per process); the reports of the parts are put together (merge()) into those of the whole, so the result reads as one
run. Most of the time of the set is the scenarios of the window, each test building a whole window in one thread:
eight cores did one test at a time."""

import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / 'artifacts' / 'tests'
WINDOWS = os.name == 'nt'
FAULT_SECONDS = 600  # a test longer than this prints the stacks of its threads (pytest faulthandler_timeout); not stopped
STATUS_TEXT = {
    'passed': 'ПРОЙДЕН', 'failed': 'ЕСТЬ ПАДЕНИЯ', 'empty': 'НИЧЕГО НЕ СОБРАНО', 'interrupted': 'ПРЕРВАН',
    'timeout': 'ПРЕВЫШЕНО ВРЕМЯ', 'crashed': 'АВАРИЙНОЕ ЗАВЕРШЕНИЕ', 'error': 'ОШИБКА ЗАПУСКА',
}


@dataclass
class Result:
    label: str
    status: str
    code: int
    seconds: float
    folder: Path
    summary: dict = field(default_factory=dict)

    @property
    def ok(self):
        return self.status == 'passed'


def groups():
    tests = ROOT / 'tests'
    found = [p for p in sorted(tests.iterdir()) if p.is_dir() and any(p.glob('test_*.py'))]
    found += [p for p in sorted(tests.glob('test_*.py'))]
    return [p.relative_to(ROOT).as_posix() for p in found]


def report_folder(profile):
    stamp = time.strftime('%Y%m%d-%H%M%S')
    folder = ARTIFACTS / f'{stamp}-{re.sub(r"[^A-Za-z0-9_.-]+", "_", profile)}'
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def environment(profile, report):
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join([str(ROOT)] + ([env['PYTHONPATH']] if env.get('PYTHONPATH') else []))
    env.setdefault('QT_QPA_PLATFORM', 'offscreen')
    if os.name == 'nt':  # offscreen of Windows knows no fonts of the system without it (as tests/gui_support.py)
        env.setdefault('QT_QPA_FONTDIR', os.path.join(env.get('WINDIR', 'C:\\Windows'), 'Fonts'))
    env.update(PYTHONUNBUFFERED='1', PYTHONDONTWRITEBYTECODE='1', AZIMUTH_TEST_PROFILE=profile,
               AZIMUTH_TEST_REPORT=str(report))
    return env


def command(args, folder):
    return [sys.executable, '-u', '-m', 'pytest', '-p', 'tools.pytest_timing', '-p', 'no:cacheprovider', '-q', '-ra',
            '-o', f'faulthandler_timeout={FAULT_SECONDS}', f'--junitxml={folder / "junit.xml"}', *args]


def _start(cmd, env):
    extra = {'creationflags': subprocess.CREATE_NEW_PROCESS_GROUP} if WINDOWS else {'start_new_session': True}
    return subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, **extra)


def _stop(process):
    """Only this child and its group: first as Ctrl+C (pytest writes its summary), then for good."""
    if process.poll() is not None:
        return
    try:
        if WINDOWS:
            process.send_signal(signal.CTRL_BREAK_EVENT)
        else:
            os.killpg(process.pid, signal.SIGINT)
        process.wait(10)
        return
    except (OSError, subprocess.TimeoutExpired):
        pass
    try:
        if WINDOWS:
            subprocess.run(['taskkill', '/T', '/F', '/PID', str(process.pid)], capture_output=True)
        else:
            os.killpg(process.pid, signal.SIGKILL)
    except OSError:
        pass
    process.wait()


PROGRESS = re.compile(r'\[\s*\d+%\]\s*$|\[тесты идут'.encode())


def _pump(stream, log, echo, label, started):
    """The output of the child into its log; echo True — all of it to the terminal too, 'progress' — only its
    progress: pytest's «[ 42%]» and the timing plugin's lines, with the group and the time gone by."""
    pending = b''
    while True:
        chunk = os.read(stream.fileno(), 65536)
        if not chunk:
            break
        log.write(chunk)
        log.flush()
        if echo is True:
            sys.stdout.buffer.write(chunk)
            sys.stdout.buffer.flush()
        elif echo == 'progress':
            pending += chunk
            *lines, pending = pending.split(b'\n')
            for line in lines:
                if PROGRESS.search(line.rstrip()):
                    percent = re.search(rb'\[\s*(\d+)%\]', line)
                    text = (f'  … {label}: {int(percent.group(1))}% · {_clock(time.monotonic() - started)}'
                            if percent else '  … ' + line.decode('utf-8', 'replace').strip())
                    print(text, flush=True)


def _clock(seconds):
    seconds = int(seconds)
    return f'{seconds // 60}:{seconds % 60:02d}'


QT_CHECK = ('from PySide6.QtWidgets import QApplication; app = QApplication([]); '
            'from PySide6.QtCore import QLibraryInfo; print("Qt", QLibraryInfo.version().toString())')


def qt_ready():
    """Before the tests: can Qt start here at all (the same interpreter and graphics mode)? A Qt that cannot load its
    platform plugin aborts the first test that makes a window, and pytest's capture swallows Qt's reason — so it is
    asked here, where its message is seen. Returns (True, version) or (False, what Qt said)."""
    start = time.monotonic()
    try:
        # Windows: offscreen there reads the font files before the first window — minutes on a computer with many
        # fonts (2–3 min under the MCP server on 2026-11-25), so its limit is longer
        run = subprocess.run([sys.executable, '-c', QT_CHECK], cwd=ROOT, env=environment('qt-check', ''),
                             capture_output=True, text=True, encoding='utf-8', errors='replace',
                             timeout=600 if os.name == 'nt' else 120)
    except (OSError, subprocess.SubprocessError) as exc:
        return False, str(exc)
    if run.returncode == 0:
        return True, f'{run.stdout.strip()} (за {time.monotonic() - start:.0f} с)'
    said = (run.stderr.strip() or run.stdout.strip() or f'код {run.returncode}').splitlines()
    return False, '\n'.join(said[:8])


def run(args, profile, label=None, timeout_minutes=None, echo=True, folder=None):
    folder = folder or report_folder(profile)
    report = folder / 'summary.json'
    label = label or profile
    started = time.monotonic()
    print(f'▶ {label}: {time.strftime("%H:%M:%S")} · отчёт {folder.relative_to(ROOT)}', flush=True)
    try:
        process = _start(command(args, folder), environment(profile, report))
    except OSError as exc:
        print(f'✗ {label}: не запустился pytest — {exc}', flush=True)
        return Result(label, 'error', -1, 0.0, folder)
    with open(folder / 'log.txt', 'wb') as log:
        reader = threading.Thread(target=_pump, args=(process.stdout, log, echo, label, started), daemon=True)
        reader.start()
        status = None
        try:
            while process.poll() is None:
                if timeout_minutes and time.monotonic() - started > timeout_minutes * 60:
                    print(f'\n⏱ {label}: прошло {timeout_minutes} мин — прогон останавливается', flush=True)
                    _stop(process)
                    status = 'timeout'
                    break
                time.sleep(0.3)
        except KeyboardInterrupt:
            print(f'\n■ {label}: остановлен (Ctrl+C) — завершается только его pytest', flush=True)
            _stop(process)
            status = 'interrupted'
        reader.join(5)
    code = process.returncode
    summary = {}
    try:
        summary = json.loads(report.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        pass
    if status is None:
        status = classify(code, summary)
    return Result(label, status, code, time.monotonic() - started, folder, summary)


def jobs_auto():
    """How many parts at once: the cores less two (the machine stays usable), at most 6 (the windows take memory)."""
    return max(1, min(6, (os.cpu_count() or 2) - 2))


def last_times():
    """{test file: seconds} of the newest whole run (a summary of more than 1000 tests), {} without one."""
    for path in sorted(ARTIFACTS.glob('*-full/summary.json'), reverse=True):
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if data.get('selected_count', 0) < 1000:
            continue
        times = {}
        for record in data.get('tests', ()):
            name = record['nodeid'].split('::')[0]
            times[name] = times.get(name, 0.0) + record['seconds']
        return times
    return {}


UNKNOWN_SECONDS = 5.0  # a file of no earlier run (a new one)


def plan(files, parts, times=None):
    """The files in at most `parts` lists of about equal time — the longest first, each to the shortest list so far;
    the lists keep the order of the files. A part of nothing is not made."""
    times = last_times() if times is None else times
    loads = [[0.0, i, []] for i in range(max(1, parts))]
    for name in sorted(files, key=lambda f: (-times.get(f, UNKNOWN_SECONDS), f)):
        least = min(loads, key=lambda load: (load[0], load[1]))
        least[0] += times.get(name, UNKNOWN_SECONDS)
        least[2].append(name)
    order = {name: k for k, name in enumerate(files)}
    return [sorted(load[2], key=order.get) for load in loads if load[2]]


def estimate(files, times=None):
    times = last_times() if times is None else times
    return sum(times.get(f, UNKNOWN_SECONDS) for f in files)


WORST = ('crashed', 'timeout', 'interrupted', 'error', 'failed', 'empty', 'passed')


def merge(folder, results, seconds):
    """The reports of the parts in those of the whole in `folder`: summary.json (the counts added, the tests of all,
    the worst exit code), junit.xml (the suites of all), log.txt (the logs one after another)."""
    summaries = [r.summary for r in results if r.summary]
    first = summaries[0] if summaries else {}
    outcomes = {}
    for s in summaries:
        for key, count in s.get('outcomes', {}).items():
            outcomes[key] = outcomes.get(key, 0) + count
    summary = {**{k: v for k, v in first.items() if k not in ('tests', 'command')},
               'wall_seconds': round(seconds, 2),
               'collection_seconds': max((s.get('collection_seconds', 0) for s in summaries), default=0),
               'run_seconds': round(seconds - max((s.get('collection_seconds', 0) for s in summaries), default=0), 2),
               'selected_count': sum(s.get('selected_count', 0) for s in summaries),
               'deselected_count': sum(s.get('deselected_count', 0) for s in summaries),
               'outcomes': outcomes,
               'unfinished': [n for s in summaries for n in s.get('unfinished', ())],
               'exit_code': max((r.code for r in results), default=0, key=lambda c: (c != 0, abs(c))),
               'workers': len(results),
               'parts': [{'folder': r.folder.name, 'status': r.status, 'seconds': round(r.seconds, 1),
                          'tests': r.summary.get('selected_count', 0)} for r in results],
               'tests': [t for s in summaries for t in s.get('tests', ())]}
    (folder / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=1), encoding='utf-8')
    suites = []
    for r in results:
        try:
            text = (r.folder / 'junit.xml').read_text(encoding='utf-8')
        except OSError:
            continue
        body = re.sub(r'^<\?xml[^>]*\?>\s*', '', text)
        body = re.sub(r'^<testsuites[^>]*>|</testsuites>\s*$', '', body.strip())
        suites.append(body)
    (folder / 'junit.xml').write_text('<?xml version="1.0" encoding="utf-8"?><testsuites>' + ''.join(suites)
                                      + '</testsuites>\n', encoding='utf-8')
    with open(folder / 'log.txt', 'wb') as log:
        for r in results:
            log.write(f'===== {r.label} · {STATUS_TEXT.get(r.status, r.status)} · {r.seconds:.0f} с =====\n'.encode())
            try:
                log.write((r.folder / 'log.txt').read_bytes())
            except OSError:
                pass
            log.write(b'\n')
    return summary


def run_parts(files, extra, profile, parts, timeout_minutes=None, times=None):
    """The files in `parts` pytest processes at once (plan()); the Result of the whole (status: the worst of the parts)
    with the reports put together in its folder. Ctrl+C or the limit of time stops every part."""
    folder = report_folder(profile)
    lists = plan(files, parts, times)
    started = time.monotonic()
    print(f'▶ {profile}: {time.strftime("%H:%M:%S")} · частей {len(lists)} · отчёт {_shown(folder)}',
          flush=True)
    running = []
    for k, chosen in enumerate(lists, 1):
        sub = folder / f'part-{k}'
        sub.mkdir()
        label = f'часть {k}/{len(lists)}'
        try:
            process = _start(command([*chosen, *extra], sub), environment(profile, sub / 'summary.json'))
        except OSError as exc:
            print(f'✗ {label}: не запустился pytest — {exc}', flush=True)
            for _, p, *_ in running:
                _stop(p)
            return Result(profile, 'error', -1, 0.0, folder)
        log = open(sub / 'log.txt', 'wb')
        reader = threading.Thread(target=_pump, args=(process.stdout, log, 'progress', label, started), daemon=True)
        reader.start()
        running.append((label, process, sub, log, reader))
    stopped = None
    try:
        while any(p.poll() is None for _, p, *_ in running):
            if timeout_minutes and time.monotonic() - started > timeout_minutes * 60:
                print(f'\n⏱ {profile}: прошло {timeout_minutes} мин — прогон останавливается', flush=True)
                stopped = 'timeout'
                break
            time.sleep(0.3)
    except KeyboardInterrupt:
        print(f'\n■ {profile}: остановлен (Ctrl+C) — завершаются только его процессы pytest', flush=True)
        stopped = 'interrupted'
    if stopped:
        for _, p, *_ in running:
            _stop(p)
    results = []
    for label, process, sub, log, reader in running:
        reader.join(5)
        log.close()
        summary = {}
        try:
            summary = json.loads((sub / 'summary.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            pass
        status = stopped or classify(process.returncode, summary)
        results.append(Result(label, status, process.returncode, time.monotonic() - started, sub, summary))
        print(f'  {"✓" if status == "passed" else "✗"} {label}: {STATUS_TEXT.get(status, status)} · '
              f'тестов {summary.get("selected_count", "?")}', flush=True)
    seconds = time.monotonic() - started
    summary = merge(folder, results, seconds)
    status = min((r.status for r in results), key=lambda s: WORST.index(s) if s in WORST else 0)
    if status == 'empty' and summary['selected_count'] > 0:
        status = 'passed' if all(r.status in ('passed', 'empty') for r in results) else status
    code = 0 if status == 'passed' else next((r.code for r in results if r.status == status), 1)
    return Result(profile, status, code, seconds, folder, summary)


def classify(code, summary):
    if code == 0:
        return 'passed' if summary.get('selected_count', 1) > 0 else 'empty'
    return {1: 'failed', 2: 'interrupted', 3: 'error', 4: 'error', 5: 'empty'}.get(code, 'crashed')


def _shown(path):
    try:
        return path.relative_to(ROOT)
    except ValueError:
        return path


def describe(result, scope=''):
    """The lines under a run: its verdict, what was run, and — when it did not pass — why, from its log."""
    s = result.summary
    outcomes = s.get('outcomes', {})
    count = ', '.join(f'{k}: {v}' for k, v in sorted(outcomes.items())) or 'нет данных'
    lines = [f'{"✓" if result.ok else "✗"} {result.label}: {STATUS_TEXT.get(result.status, result.status)} · '
             f'{result.seconds:.0f} с · тестов {s.get("selected_count", "?")} ({count}) · код {result.code}']
    if scope:
        lines.append('  ' + scope)
    log = result.folder / 'log.txt'
    text = log.read_text(encoding='utf-8', errors='replace') if log.exists() else ''
    if result.status in ('failed', 'interrupted') and 'short test summary info' in text:
        tail = [t for part in text.split('short test summary info')[1:] for t in part.splitlines()[1:]]
        lines += ['  ' + t for t in tail if t.startswith(('FAILED', 'ERROR'))][:30]
    elif result.status in ('crashed', 'error', 'interrupted', 'timeout', 'empty'):
        every = text.rstrip().splitlines()
        fatal = next((i for i, t in enumerate(every) if 'Fatal Python error' in t), None)
        if fatal is not None:  # a native crash: its cause (and Qt's line before it) and where the main thread was
            lines.append('  причина:')
            lines += ['  | ' + t for t in every[max(0, fatal - 3):fatal + 1]]
            main = next((i for i in range(fatal, len(every)) if every[i].startswith('Current thread')), None)
            if main is not None:
                lines += ['  | ' + t for t in every[main:main + 4]]
        if s.get('unfinished'):
            lines.append('  не завершён: ' + ', '.join(s['unfinished']))
        lines.append('  конец журнала:')
        lines += ['  | ' + t for t in every[-(12 if fatal is not None else 25):]]
    lines.append(f'  журнал: {_shown(log)}')
    return '\n'.join(lines)

"""Checks of the program at three depths (internal; TEST_FEEDBACK_PLAN.md §3) — run with the interpreter of the program:

    .venv/bin/python tools/test.py quick              a first signal after a small change (~30 s) — not the full check
    .venv/bin/python tools/test.py affected           the tests of what changed (uncommitted, else the last commit;
                                                      --base REF — against REF), by the imports (tools/test_affected.py)
    .venv/bin/python tools/test.py area projects      the tests of an area (list — the areas and what they hold)
    .venv/bin/python tools/test.py full               the whole set — before a push, after wide changes, before a release
    .venv/bin/python tools/test.py isolated           each group in a process of its own (after fixtures, settings, imports)
    .venv/bin/python tools/test.py profile            the whole set with the times of the tests (before an optimization)
    .venv/bin/python tools/test.py list               the areas, the quick set, the files of no area
Options: --dry-run (what would run, how many tests; nothing runs), --timeout MIN (stop after MIN minutes: a failure),
--jobs N (full and affected run in N pytest processes at once, the files split by their times — by default the cores
less two, at most 6; --jobs 1 — one process, as before), and after «--» options of pytest (e.g. -- -x -k crystal). Windows: .venv\\Scripts\\python.exe tools\\test.py …
Exit code 0 only when everything selected passed; nothing collected, an interruption, a crash or a timeout is 1.
Each run leaves artifacts/tests/<time>-<profile>/ (log.txt, summary.json, junit.xml)."""

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_profiles  # noqa: E402
import testkit  # noqa: E402

ROOT = testkit.ROOT


def resolve(entries):
    """Paths and node ids as they are; (path, -k expression) — the node ids that expression selects in that file."""
    plain, chosen = [], []
    for entry in entries:
        if isinstance(entry, tuple):
            path, expression = entry
            chosen += collect([path, '-k', expression])
        else:
            plain.append(entry)
    return plain + chosen


def collect(args):
    run = subprocess.run([sys.executable, '-m', 'pytest', '--collect-only', '-q', '-p', 'no:cacheprovider', *args],
                         cwd=ROOT, env=testkit.environment('collect', ''), capture_output=True, text=True,
                         encoding='utf-8', errors='replace')
    if run.returncode not in (0, 5):
        sys.exit('Сбор тестов не удался:\n' + run.stdout[-3000:] + run.stderr[-2000:])
    return [line.strip() for line in run.stdout.splitlines() if '::' in line and not line.startswith(' ')]


def files_of(paths):
    found = set()
    for path in paths:
        p = ROOT / str(path).split('::')[0]
        found |= {f.relative_to(ROOT).as_posix() for f in p.rglob('test_*.py')} if p.is_dir() else {p.relative_to(ROOT).as_posix()}
    return found


def listing():
    print('quick:', len(test_profiles.QUICK), 'записей')
    for entry in test_profiles.QUICK:
        print('  ', entry)
    print('Не входит в quick:', '; '.join(test_profiles.NOT_IN_QUICK))
    print('Области:')
    covered = set()
    for name, entries in test_profiles.AREAS.items():
        paths = [e[0] if isinstance(e, tuple) else e for e in entries]
        covered |= files_of(paths)
        print(f'  {name:9s}', ', '.join(f'{e[0]} (-k {e[1]})' if isinstance(e, tuple) else e for e in entries))
    every = files_of(['tests'])
    loose = sorted(every - covered)
    print('Файлы ни в одной области:', ', '.join(loose) if loose else 'нет')
    return 1 if loose else 0


def dry_run(profile, args):
    ids = collect(args)
    by_file = {}
    for nodeid in ids:
        by_file[nodeid.split('::')[0]] = by_file.get(nodeid.split('::')[0], 0) + 1
    print(f'{profile}: будет запущено тестов: {len(ids)} из {len(by_file)} файлов')
    for name, n in sorted(by_file.items()):
        print(f'  {n:5d}  {name}')
    if not ids:
        print('✗ Ничего не собрано — это ошибка состава профиля, а не успех.')
        return 1
    return 0


PART_SECONDS = 60  # a part shorter than this costs more in its start (imports, collection) than it saves


def parallel_parts(profile, selection, extra, jobs):
    """How many processes: 1 unless full or affected, with whole files chosen (a node id or a path among the options of
    pytest — those run as given, in one process); no more than the files, nor than parts of PART_SECONDS."""
    if profile not in ('full', 'affected') or jobs == 1:
        return 1
    if any('::' in str(s) for s in selection) or any(not str(o).startswith('-') and ('/' in str(o) or str(o).endswith('.py'))
                                                       for o in extra):
        return 1
    files = sorted(files_of(selection)) if selection == ['tests'] else list(selection)
    by_time = int(testkit.estimate(files) // PART_SECONDS) or 1
    return max(1, min(jobs or testkit.jobs_auto(), len(files), by_time))


def qt_or_say():
    ok, said = testkit.qt_ready()
    if ok:
        print(f'{said} запускается ({sys.executable})', flush=True)
        return True
    print('✗ Qt не запускается в этом окружении — тесты окна упали бы аварийно, поэтому прогон не начат.')
    print('  Qt ответил:\n  | ' + said.replace('\n', '\n  | '))
    print('  Частые причины: PySide6 в .venv переустанавливается прямо сейчас или установлен не полностью '
          '(.venv/bin/python -m pip install --force-reinstall --no-deps PySide6-Essentials==… ), '
          'переменные QT_* из другой среды (conda).')
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(prog='tools/test.py', description=__doc__.splitlines()[0])
    parser.add_argument('profile', choices=('quick', 'affected', 'area', 'full', 'isolated', 'profile', 'list'))
    parser.add_argument('--base', default=None, help='affected: сравнить с этой ревизией (по умолчанию — незакоммиченное)')
    parser.add_argument('name', nargs='?', help='область для area (см. list)')
    parser.add_argument('--dry-run', action='store_true', help='показать состав, ничего не запуская')
    parser.add_argument('--timeout', type=float, default=None, help='предел времени, минут (превышение — провал)')
    parser.add_argument('--jobs', type=int, default=None,
                        help='full, affected: столько процессов pytest сразу (по умолчанию ядра минус два, до 6; 1 — один)')
    argv = list(sys.argv[1:] if argv is None else argv)
    extra = argv[argv.index('--') + 1:] if '--' in argv else []
    options = parser.parse_args(argv[:argv.index('--')] if '--' in argv else argv)

    if options.profile == 'list':
        return listing()
    if options.profile == 'area':
        if options.name not in test_profiles.AREAS:
            print(f'Неизвестная область «{options.name}». Есть: {", ".join(test_profiles.AREAS)}.')
            return 2
        label, selection = f'area:{options.name}', resolve(test_profiles.AREAS[options.name])
        scope = f'Проверена область «{options.name}» — это не полная проверка (полная: tools/test.py full).'
    elif options.profile == 'affected':
        import test_affected

        paths = test_affected.changed(options.base)
        files, reasons, notes = test_affected.select(paths)
        print(f'Изменено файлов: {len(paths)}; выбрано файлов тестов: {len(files)}')
        for path in files:
            print(f'  {path} — {reasons[path]}')
        for note in notes:
            print('  ' + note)
        if not files:
            print('Тестов для этих изменений нет.')
            return 0
        label, selection = 'affected', files
        scope = ('Проверено то, что зависит от изменённых файлов, — это не полная проверка (полная перед push: '
                 'tools/test.py full).')
    elif options.profile == 'quick':
        label, selection = 'quick', list(test_profiles.QUICK)
        scope = ('Короткая проверка — не полная. Не проверено: ' + '; '.join(test_profiles.NOT_IN_QUICK)
                 + ' (полная: tools/test.py full).')
    elif options.profile in ('full', 'profile'):
        label, selection = options.profile, ['tests']
        if options.profile == 'profile':
            extra = ['--durations=30', '--durations-min=0.05', *extra]
        scope = 'Полный набор tests/.'
    else:  # isolated
        groups = testkit.groups()
        if not options.dry_run and not qt_or_say():
            return 1
        if options.dry_run:
            print('isolated: группы по отдельности —', ', '.join(groups))
            return 0
        results = []
        for group in groups:
            results.append(testkit.run([group, *extra], f'isolated:{group}', label=group,
                                       timeout_minutes=options.timeout, echo='progress'))
            print(testkit.describe(results[-1]), flush=True)
            if results[-1].status == 'interrupted' and results[-1].code != 2:
                break
        failed = [r.label for r in results if not r.ok]
        print('Все группы прошли по отдельности.' if not failed and len(results) == len(groups)
              else 'Не прошли по отдельности: ' + ', '.join(failed or ['прогон прерван']))
        return 0 if not failed and len(results) == len(groups) else 1

    if options.dry_run:
        return dry_run(label, selection + extra)
    if not qt_or_say():
        return 1
    parts = parallel_parts(options.profile, selection, extra, options.jobs)
    if parts > 1:
        files = sorted(files_of(selection)) if selection == ['tests'] else list(selection)
        result = testkit.run_parts(files, extra, label, parts, timeout_minutes=options.timeout)
    else:
        result = testkit.run(selection + extra, label, timeout_minutes=options.timeout)
    print()
    print(testkit.describe(result, scope))
    return 0 if result.ok else 1


if __name__ == '__main__':
    sys.exit(main())

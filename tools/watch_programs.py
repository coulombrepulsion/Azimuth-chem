"""Have new versions of the calculation programs come out since Azimuth was checked with them?

For the owner of the program, not for its users: Azimuth writes the inputs of these programs and reads their outputs,
so a new version of any of them is a reason to run the checks again (docs/plans/MAIN_PATH.md, tools/run_references.py).

    .venv/bin/python tools/watch_programs.py            # the table; exit code 1 when something new is out
    .venv/bin/python tools/watch_programs.py --json     # the same as JSON
    .venv/bin/python tools/watch_programs.py --why      # and why an address gave nothing
    .venv/bin/python tools/watch_programs.py --checked xtb 6.7.2   # write down the version just checked

What is asked: one public address per program — the latest release of its repository (GitHub or GitLab API, no
account). ORCA, Gaussian, GAMESS and Multiwfn publish no list a program can read: for them the page to look at is
printed. The versions Azimuth was checked with are kept in docs/plans/PROGRAM_VERSIONS.json.

SPECIFICATION
    numbers('v6.7.1') -> (6, 7, 1); newer(latest, checked) -> bool (by the numbers, as many as both have).
    latest_release(source, fetch) -> (tag, date) or None; fetch(url) -> the parsed JSON (None on any failure).
    report(table, fetch) -> rows {program, checked, latest, date, state: 'new' | 'same' | 'unknown' | 'manual', page}.
    main(argv) -> exit code: 0 — nothing new, 1 — a newer version of something is out.
TESTS tests/core/test_watch_programs.py.
"""

import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLE = ROOT / 'docs' / 'plans' / 'PROGRAM_VERSIONS.json'
STATES = {'new': 'ВЫШЛА НОВАЯ', 'same': 'без изменений', 'unknown': 'не удалось узнать', 'manual': 'смотреть вручную'}


def numbers(text):
    """The version numbers of a tag: 'v6.7.1' -> (6, 7, 1), 'release-7-3-0' -> (7, 3, 0), 'qe-7.5' -> (7, 5)."""
    return tuple(int(n) for n in re.findall(r'\d+', str(text or '')))


def newer(latest, checked):
    a, b = numbers(latest), numbers(checked)
    if not a or not b:
        return False
    size = min(len(a), len(b))
    return a[:size] > b[:size] or (a[:size] == b[:size] and len(a) > len(b) and any(a[size:]))


def fetch(url, timeout=15.0):
    """The JSON of a public address, or None (no network, a refusal, not JSON)."""
    request = urllib.request.Request(url, headers={'User-Agent': 'Azimuth-watch-programs', 'Accept': 'application/json'})
    try:
        with _open(request, timeout) as response:
            return json.loads(response.read(2_000_000).decode('utf-8', 'replace'))
    except Exception as error:  # noqa: BLE001 — a check that fails says «unknown», it does not stop the others
        FAILURES.append(f'{url}: {type(error).__name__}: {error}')
        return None


FAILURES = []  # why the addresses that gave nothing gave nothing (printed with --why)


def _open(request, timeout):
    """urlopen with the certificates of the program (the Python of macOS has none of its own: «CERTIFICATE_VERIFY_
    FAILED» for every address) — the same opener as the lookups of Compass; the plain one outside the program."""
    try:
        sys.path.insert(0, str(ROOT))
        from modules.compass.chemistry.pubchem import _urlopen

        return _urlopen(request, timeout)
    except ImportError:
        return urllib.request.urlopen(request, timeout=timeout)


def latest_release(source, fetch=fetch):
    """(tag, date 'YYYY-MM-DD') of the latest release of source {'github': 'owner/repo'} or {'gitlab': 'group/project'}."""
    if source.get('github'):
        data = fetch(f'https://api.github.com/repos/{source["github"]}/releases/latest')
        if isinstance(data, dict) and data.get('tag_name'):
            return str(data['tag_name']), str(data.get('published_at') or '')[:10]
        tags = fetch(f'https://api.github.com/repos/{source["github"]}/tags?per_page=30')  # a project without releases
        if isinstance(tags, list) and tags:
            best = max((t.get('name', '') for t in tags if isinstance(t, dict)), key=numbers, default='')
            return (best, '') if numbers(best) else None
        return None
    if source.get('gitlab'):
        project = source['gitlab'].replace('/', '%2F')
        data = fetch(f'https://gitlab.com/api/v4/projects/{project}/releases?per_page=5')
        if isinstance(data, list) and data and isinstance(data[0], dict) and data[0].get('tag_name'):
            return str(data[0]['tag_name']), str(data[0].get('released_at') or '')[:10]
    return None


def report(table, fetch=fetch):
    rows = []
    for name, entry in table.items():
        row = {'program': name, 'checked': entry.get('checked', ''), 'latest': '', 'date': '', 'page': entry.get('page', '')}
        source = entry.get('source') or {}
        if not source:
            row['state'] = 'manual'
        else:
            found = latest_release(source, fetch)
            if found is None:
                row['state'] = 'unknown'
            else:
                row['latest'], row['date'] = found
                row['state'] = 'new' if newer(found[0], row['checked']) else 'same'
        rows.append(row)
    return rows


def as_text(rows):
    lines = [f'{"Программа":<18}{"Проверено":<14}{"Последняя":<18}{"Дата":<12}Состояние']
    for r in rows:
        lines.append(f'{r["program"]:<18}{r["checked"]:<14}{r["latest"] or "—":<18}{r["date"] or "—":<12}{STATES[r["state"]]}')
    fresh = [r for r in rows if r['state'] == 'new']
    manual = [r for r in rows if r['state'] in ('manual', 'unknown')]
    if fresh:
        lines.append('')
        lines.append('Перепроверить с новой версией (tools/run_references.py, docs/plans/MAIN_PATH.md):')
        lines += [f'  {r["program"]}: {r["checked"]} → {r["latest"]}  {r["page"]}' for r in fresh]
    if manual:
        lines.append('')
        lines.append('Посмотреть вручную:')
        lines += [f'  {r["program"]} (проверено {r["checked"]}): {r["page"]}' for r in manual]
    return '\n'.join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--json', action='store_true')
    parser.add_argument('--why', action='store_true', help='print why an address gave nothing')
    parser.add_argument('--checked', nargs=2, metavar=('PROGRAM', 'VERSION'), help='write down the version just checked')
    args = parser.parse_args(argv)
    table = json.loads(TABLE.read_text(encoding='utf-8'))
    if args.checked:
        name, version = args.checked
        if name not in table:
            print(f'нет программы {name!r}; есть: {", ".join(table)}', file=sys.stderr)
            return 2
        table[name]['checked'] = version
        TABLE.write_text(json.dumps(table, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
        print(f'{name}: проверено {version}')
        return 0
    rows = report(table)
    print(json.dumps(rows, ensure_ascii=False, indent=1) if args.json else as_text(rows))
    if args.why and FAILURES:
        print('\n' + '\n'.join(FAILURES), file=sys.stderr)
    return 1 if any(r['state'] == 'new' for r in rows) else 0


if __name__ == '__main__':
    sys.exit(main())

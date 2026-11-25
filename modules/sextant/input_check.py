"""Sextant: a check of an input file edited by hand before it is run.

HEADER
    The «Входной файл» panel of Sextant can be edited. Before «Запустить расчёт» runs the edited text, check(kind,
    text) looks for the mistakes that stop the program at once: an unclosed block, a coordinate line without three
    numbers, a missing charge and multiplicity, unbalanced brackets. It is not the parser of the program — a
    keyword it does not know is left to the program itself; the aim is to catch a broken structure before a
    calculation folder is made.
    Wilkinson convention, sections 1-8.

§1 THEORY
    ORCA: «! keywords» lines; «%block … end» blocks (one line «%pal nprocs 4 end» or several; the sub-blocks
    Constraints, Scan, Modify_Internal, Coords of %geom close with their own «end»); «%maxcore N», «%moinp "f"»,
    «%base "f"», «%id "s"» take one value and no «end»; the geometry «* xyz q m … *» («* int», «* gzmt» likewise) or
    one line «* xyzfile q m file» (gzmtfile, pdbfile). Gaussian: Link 0 lines «%…», the route «# …» up to a blank
    line, the title up to a blank line, «charge multiplicity» (pairs for fragments), the atoms up to a blank line.
    Psi4: Python with the psithon lines «memory», «set», «unset» and the blocks «molecule {…}», «set {…}»,
    «basis {…}», «pcm = {…}»; after those are blanked the rest must compile as Python.
§2 ALGORITHM
    A pass over the lines with the comments removed (ORCA, Psi4: «#» to the end of the line; Gaussian: «!»), a
    small state machine (outside / block / geometry) for ORCA, the sections in order for Gaussian, a bracket stack
    and compile() for Psi4.
§3 APPLICATIONS
    modules/sextant/workspace.py (run_calculation, the edited input).
§4 SPECIFICATION
    check(kind, text) -> list[Problem]; Problem(line: 1-based or 0 for the whole file, text: str).
    kind in 'orca', 'gaussian', 'psi4'; other kinds: [] (their preview is not edited).
§5 PROCEDURES - below.
§6 NOTES
    ASSUMPTION: from memory of the ORCA 6, Gaussian 16 and Psi4 1.7 manuals, not checked against the programs.
§7 TEST CASES tests/sextant/test_inputs.py::test_input_check.
§8' ROBUSTNESS
    Never raises on any text; the files Azimuth writes itself give no problems (the test checks every task).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from azimuth.i18n import tr

ORCA_ONE_VALUE = {'maxcore', 'moinp', 'base', 'id', 'scfmemory'}
ORCA_SUBBLOCKS = {'constraints', 'scan', 'modify_internal', 'coords'}
ORCA_GEOMETRY_FILES = {'xyzfile', 'gzmtfile', 'pdbfile'}
ORCA_GEOMETRY_BLOCKS = {'xyz', 'int', 'internal', 'gzmt'}
PSITHON_LINE = re.compile(r'^(\s*)(memory|set|unset|molecule|basis|pcm|df_basis_\w+|efp|external_potentials)\b(.*)$')
_NUMBER = re.compile(r'^[-+]?(\d+\.?\d*|\.\d+)([eEdD][-+]?\d+)?$')
_INT = re.compile(r'^[-+]?\d+$')
_SYMBOL = re.compile(r'^[A-Za-z][A-Za-z]?([-_:.]?[\w.]*)?(\(.*\))?$')


@dataclass(frozen=True)
class Problem:
    line: int
    text: str


def check(kind, text):
    try:
        if kind == 'orca':
            return check_orca(text)
        if kind == 'gaussian':
            return check_gaussian(text)
        if kind == 'psi4':
            return check_psi4(text)
    except Exception as exc:  # noqa: BLE001 — the check must never stop the run itself
        return [Problem(0, tr('Не удалось проверить файл: ') + str(exc))]
    return []


def _number(token):
    return bool(_NUMBER.match(token))


def _atom_line(tokens):
    """An atom with x y z: «O 0.0 0.0 0.1» (ORCA, Psi4) — the symbol and the last three tokens numbers."""
    return len(tokens) >= 4 and bool(_SYMBOL.match(tokens[0])) and all(_number(t) for t in tokens[1:4])


def check_orca(text):
    problems = []
    lines = text.splitlines()
    state, block, block_line, depth, geometry_line, geometry_kind = 'out', '', 0, 0, 0, 'xyz'
    keywords = geometries = 0
    for n, raw in enumerate(lines, 1):
        line = raw.split('#', 1)[0].strip()
        if not line:
            continue
        tokens = line.split()
        low = [t.lower() for t in tokens]
        if state == 'block':
            if low == ['end']:
                depth -= 1
                if depth == 0:
                    state = 'out'
            elif low[0] in ORCA_SUBBLOCKS and low[-1] != 'end':
                depth += 1
            elif line.startswith(('%', '!', '*')):
                problems.append(Problem(n, tr(f'Блок %{block} (строка {block_line}) не закрыт словом end перед этой строкой.')))
                state, depth = 'out', 0
            else:
                continue
            if state != 'out' or not line.startswith(('%', '!', '*')):
                continue
        if state == 'geometry':
            if line == '*':
                state = 'out'
                continue
            if line.startswith('%') or line.startswith('!') or line.startswith('*'):
                problems.append(Problem(n, tr(f'Координаты (строка {geometry_line}) не закрыты строкой «*».')))
                state = 'out'
            elif geometry_kind == 'xyz' and not _atom_line(tokens):
                problems.append(Problem(n, tr('Строка координат: нужен символ атома и три числа x y z.')))
                continue
            else:
                continue
        if line.startswith('!'):
            keywords += 1
            if len(line) == 1:
                problems.append(Problem(n, tr('Пустая строка «!» — после «!» нужны ключевые слова.')))
            continue
        if line.startswith('%'):
            name = line[1:].split()[0].lower() if len(line) > 1 and line[1:].split() else ''
            if not name:
                problems.append(Problem(n, tr('После «%» нужно имя блока (например, %pal, %scf).')))
            elif name in ORCA_ONE_VALUE:
                if len(tokens) < 2 and len(line[1:].split()) < 2:
                    problems.append(Problem(n, tr(f'После %{name} нужно значение.')))
            elif low[-1] != 'end' or len(line[1:].split()) == 1:
                state, block, block_line, depth = 'block', name, n, 1
            continue
        if line.startswith('*'):
            parts = line[1:].split()
            what = parts[0].lower() if parts else ''
            geometries += 1
            if what in ORCA_GEOMETRY_FILES:
                if len(parts) < 4:
                    problems.append(Problem(n, tr(f'«* {what}»: нужны заряд, мультиплетность и имя файла.')))
            elif what in ORCA_GEOMETRY_BLOCKS:
                if len(parts) < 3 or not (_INT.match(parts[1]) and _INT.match(parts[2])):
                    problems.append(Problem(n, tr(f'«* {what}»: после него нужны заряд и мультиплетность — два целых числа.')))
                elif int(parts[2]) < 1:
                    problems.append(Problem(n, tr('Мультиплетность — целое число от 1.')))
                state, geometry_line, geometry_kind = 'geometry', n, 'xyz' if what == 'xyz' else 'other'
            else:
                problems.append(Problem(n, tr('Начало координат: «* xyz заряд мультиплетность» (или xyzfile, int, gzmt).')))
            continue
        problems.append(Problem(n, tr('Строка вне блоков: ORCA ждёт здесь «!», «%блок» или «* xyz».')))
    if state == 'block':
        problems.append(Problem(block_line, tr(f'Блок %{block} не закрыт словом end.')))
    if state == 'geometry':
        problems.append(Problem(geometry_line, tr('Координаты не закрыты строкой «*».')))
    if not keywords:
        problems.append(Problem(0, tr('Нет строки ключевых слов «! метод базис задача».')))
    if not geometries:
        problems.append(Problem(0, tr('Нет координат: «* xyz заряд мультиплетность» … «*».')))
    return problems


def check_gaussian(text):
    problems = []
    lines = [raw.split('!', 1)[0].rstrip() for raw in text.splitlines()]
    n = 0
    while n < len(lines) and not lines[n].strip():
        n += 1
    while n < len(lines) and lines[n].lstrip().startswith('%'):  # Link 0
        if '=' not in lines[n] and lines[n].strip().lower() not in ('%nosave', '%save'):
            problems.append(Problem(n + 1, tr('Строка Link 0: «%имя=значение» (например, %mem=2000MB).')))
        n += 1
    if n >= len(lines) or not lines[n].lstrip().startswith('#'):
        return problems + [Problem(n + 1 if n < len(lines) else 0, tr('Нет строки маршрута «# метод/базис задача».'))]
    route_line = n + 1
    route = []
    while n < len(lines) and lines[n].strip():
        route.append(lines[n])
        n += 1
    if ' '.join(route).strip() in ('#', '#P', '#p', '#N', '#n', '#T', '#t'):
        problems.append(Problem(route_line, tr('В строке маршрута нет метода и задачи.')))
    if ' '.join(route).count('(') != ' '.join(route).count(')'):
        problems.append(Problem(route_line, tr('В строке маршрута не закрыта скобка.')))
    n += 1  # the blank line
    title = n
    while n < len(lines) and lines[n].strip():
        n += 1
    if n == title:
        problems.append(Problem(title + 1, tr('После маршрута и пустой строки нужна строка названия.')))
    n += 1
    if n >= len(lines) or not lines[n].strip():
        return problems + [Problem(n + 1 if n < len(lines) else 0, tr('Нет строки «заряд мультиплетность» после названия и пустой строки.'))]
    state = lines[n].replace(',', ' ').split()
    if len(state) < 2 or len(state) % 2 or not all(_INT.match(t) for t in state):
        problems.append(Problem(n + 1, tr('Строка «заряд мультиплетность»: два целых числа (или пары для фрагментов).')))
    elif int(state[1]) < 1:
        problems.append(Problem(n + 1, tr('Мультиплетность — целое число от 1.')))
    n += 1
    atoms = 0
    while n < len(lines) and lines[n].strip():
        tokens = lines[n].replace(',', ' ').split()
        cartesian = len(tokens) >= 4 and all(_number(t) for t in tokens[-3:])
        zmatrix = len(tokens) in (1, 3, 5, 7) or (len(tokens) == 8 and _INT.match(tokens[-1]))
        if not _SYMBOL.match(tokens[0].split('(')[0]) or not (cartesian or zmatrix):
            problems.append(Problem(n + 1, tr('Строка атома: символ и три числа x y z.')))
        atoms += 1
        n += 1
    if not atoms:
        problems.append(Problem(n + 1 if n < len(lines) else 0, tr('Нет атомов после строки «заряд мультиплетность».')))
    return problems


_PAIRS = {')': '(', ']': '[', '}': '{'}


def _brackets(lines):
    """Unbalanced (), [], {} outside strings and comments: [Problem]."""
    stack = []
    for n, raw in enumerate(lines, 1):
        quote = None
        for ch in raw:
            if quote:
                if ch == quote:
                    quote = None
                continue
            if ch == '#':
                break
            if ch in '\'"':
                quote = ch
            elif ch in '([{':
                stack.append((ch, n))
            elif ch in ')]}':
                if not stack or stack[-1][0] != _PAIRS[ch]:
                    return [Problem(n, tr(f'Лишняя закрывающая скобка «{ch}».'))]
                stack.pop()
        if quote:
            return [Problem(n, tr('Не закрыты кавычки.'))]
    if stack:
        ch, n = stack[-1]
        return [Problem(n, tr(f'Не закрыта скобка «{ch}».'))]
    return []


def check_psi4(text):
    lines = text.splitlines()
    problems = _brackets(lines)
    if problems:
        return problems
    python = list(lines)
    molecules = 0
    n = 0
    while n < len(lines):
        match = PSITHON_LINE.match(lines[n].split('#', 1)[0])
        if not match or match.group(3).lstrip().startswith(('(', '.', '[')) or (
                match.group(2) == 'pcm' and not match.group(3).strip().startswith(('=', '{'))):
            n += 1
            continue
        indent, word = match.group(1), match.group(2)
        start = n
        depth = lines[n].split('#', 1)[0].count('{') - lines[n].split('#', 1)[0].count('}')
        while depth > 0 and n + 1 < len(lines):
            n += 1
            depth += lines[n].split('#', 1)[0].count('{') - lines[n].split('#', 1)[0].count('}')
        if word == 'molecule':
            molecules += 1
            if '{' not in lines[start]:
                problems.append(Problem(start + 1, tr('molecule: координаты пишутся в фигурных скобках «molecule { … }».')))
            problems += _psi4_molecule(lines, start, n)
        elif word == 'memory' and not re.match(r'^\s*memory\s+[\d.]+\s*[a-zA-Z]+\s*$', lines[start].split('#', 1)[0]):
            problems.append(Problem(start + 1, tr('memory: число и единица, например «memory 2 gb».')))
        for i in range(start, n + 1):
            python[i] = indent + 'pass' if i == start else ''
        n += 1
    if not molecules:
        problems.append(Problem(0, tr('Нет блока «molecule { … }» с зарядом, мультиплетностью и атомами.')))
    try:
        compile('\n'.join(python) + '\n', 'input.dat', 'exec')
    except SyntaxError as exc:
        problems.append(Problem(exc.lineno or 0, tr('Ошибка синтаксиса Python: ') + (exc.msg or '')))
    return problems


def _psi4_molecule(lines, start, end):
    problems = []
    body = []
    for i in range(start, end + 1):
        line = lines[i].split('#', 1)[0]
        if i == start:
            line = line.split('{', 1)[1] if '{' in line else ''
        if i == end and '}' in line:
            line = line.rsplit('}', 1)[0]
        if line.strip():
            body.append((i + 1, line.split()))
    for n, tokens in body:
        low = tokens[0].lower()
        if low in ('units', 'symmetry', 'no_com', 'nocom', 'no_reorient', 'noreorient', 'pubchem', '--', 'fix_com',
                   'fix_orientation', 'unit', 'zmat'):
            continue
        if len(tokens) == 2 and all(_INT.match(t) for t in tokens):
            if int(tokens[1]) < 1:
                problems.append(Problem(n, tr('Мультиплетность — целое число от 1.')))
            continue
        if not (_atom_line(tokens) or len(tokens) in (1, 3, 5, 7) and _SYMBOL.match(tokens[0])):
            problems.append(Problem(n, tr('Строка атома: символ и три числа x y z.')))
    return problems

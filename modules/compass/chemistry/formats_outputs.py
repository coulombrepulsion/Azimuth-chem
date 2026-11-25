"""Structures read from the inputs and outputs of calculation programs and from trajectories: Gaussian and ORCA
inputs, the orientations of a Gaussian log, Molden, XYZ with many frames (Trajectory, Step).

Split off modules/compass/chemistry/formats.py (0.222.30); formats.py still names them.
"""

import re
from dataclasses import dataclass, field
from azimuth.core import Molecule, SYMBOLS, read_xyz
from azimuth.i18n import tr
from modules.compass.chemistry.formats_common import _element, _f, _molecule, _symbol, readable


BOHR = 0.529177210903


NUMBER = r'[+-]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][+-]?\d+)?'


# -- Gaussian --------------------------------------------------------------------------------------
@readable('Входной файл Gaussian')
def read_gaussian_input(text):
    """(Molecule, charge, multiplicity) of a Gaussian input with Cartesian coordinates."""
    lines = [l.rstrip() for l in text.replace('\r', '').split('\n')]
    k = 0
    while k < len(lines) and (lines[k].startswith('%') or not lines[k].strip()):
        k += 1
    if k >= len(lines) or not lines[k].lstrip().startswith('#'):
        raise ValueError(tr('Gaussian: нет строки маршрута (#).'))
    while k < len(lines) and lines[k].strip():
        k += 1  # route section
    k += 1
    title_lines = []
    while k < len(lines) and lines[k].strip():
        title_lines.append(lines[k].strip())
        k += 1
    k += 1
    if k >= len(lines):
        raise ValueError(tr('Gaussian: нет строки заряда и мультиплетности.'))
    head = lines[k].split()
    charge, mult = int(head[0]), int(head[1])
    k += 1
    atoms = []
    first = lines[k].replace(',', ' ').split() if k < len(lines) else []
    if len([x for x in first[1:] if re.fullmatch(NUMBER, x)]) < 3:
        # a Z-matrix, then (after a blank line) its variables
        from modules.compass.chemistry import zmatrix

        block = []
        while k < len(lines) and lines[k].strip():
            block.append(lines[k])
            k += 1
        k += 1
        variables = []
        while k < len(lines) and lines[k].strip():
            variables.append(lines[k])
            k += 1
        rows = zmatrix.parse(block + [''] + variables)
        mol = zmatrix.to_cartesian([(_symbol(r[0]),) + tuple(r[1:]) for r in rows], ' '.join(title_lines) or 'Gaussian')
        return _molecule(mol.title, [(a.symbol, *a.position) for a in mol.atoms], None), charge, mult
    while k < len(lines) and lines[k].strip():
        f = lines[k].replace(',', ' ').split()
        numbers = [x for x in f[1:] if re.fullmatch(NUMBER, x)]
        if len(numbers) < 3:
            raise ValueError(tr('Gaussian: смешанные декартовы и внутренние координаты не поддерживаются.'))
        name = f[0].split('(')[0].split('-')[0]
        symbol = SYMBOLS[int(name) - 1] if name.isdigit() else _symbol(name)
        x, y, z = (_f(v) for v in numbers[-3:])
        atoms.append((symbol, x, y, z))
        k += 1
    return _molecule(' '.join(title_lines) or 'Gaussian', atoms, None), charge, mult


@readable('Входной файл ORCA')
def read_orca_input(text):
    """(Molecule, charge, multiplicity) of an ORCA input: * xyz, * gzmt or * int blocks."""
    from modules.compass.chemistry import zmatrix

    lines = text.replace('\r', '').split('\n')
    for k, line in enumerate(lines):
        m = re.match(r'^\s*\*\s*(xyz|gzmt|int|internal|xyzfile|gzmtfile)\s+([+-]?\d+)\s+(\d+)', line, re.I)
        if not m:
            continue
        kind, charge, mult = m.group(1).lower(), int(m.group(2)), int(m.group(3))
        if kind.endswith('file'):
            raise ValueError(tr('ORCA: координаты во внешнем файле — откройте этот файл.'))
        block = []
        for row in lines[k + 1 :]:
            if row.strip().startswith('*'):
                break
            if row.split('#')[0].strip():
                block.append(row.split('#')[0].strip())
        if kind == 'xyz':
            atoms = []
            for row in block:
                f = row.split()
                atoms.append((_element(f[0]), _f(f[1]), _f(f[2]), _f(f[3])))
            return _molecule('ORCA', atoms, None), charge, mult
        if kind == 'gzmt':
            rows = zmatrix.parse(block)
        else:  # * int: symbol a b c r angle dihedral, 0 = none
            rows = []
            for n, row in enumerate(block):
                f = row.split()
                refs = [int(x) - 1 for x in f[1:4]]
                vals = [_f(x) for x in f[4:7]]
                rows.append(
                    (
                        _element(f[0]),
                        refs[0] if n >= 1 else None,
                        vals[0] if n >= 1 else None,
                        refs[1] if n >= 2 else None,
                        vals[1] if n >= 2 else None,
                        refs[2] if n >= 3 else None,
                        vals[2] if n >= 3 else None,
                    )
                )
        mol = zmatrix.to_cartesian([(_element(r[0]),) + tuple(r[1:]) for r in rows], 'ORCA')
        return _molecule('ORCA', [(a.symbol, *a.position) for a in mol.atoms], None), charge, mult
    raise ValueError(tr('ORCA: блок координат (* xyz, * gzmt или * int) не найден.'))


@dataclass
class Trajectory:
    """What the optimization drawer of Compass needs (the ORCA Output provides the same fields)."""

    steps: tuple = ()
    initial_geometry: Molecule = None
    geometry: Molecule = None
    title: str = ''
    notes: list = field(default_factory=list)


@dataclass(frozen=True)
class Step:
    cycle: int
    energy: float
    geometry: Molecule


def _orientations(text, header):
    found = []
    for m in re.finditer(header, text):
        block = text[m.end() :].split('\n')
        rows, dashes = [], 0
        for line in block:
            if set(line.strip()) == {'-'}:
                dashes += 1
                if dashes == 3:
                    break
                continue
            if dashes == 2:
                f = line.split()
                if len(f) >= 6:
                    rows.append((SYMBOLS[int(f[1]) - 1], _f(f[3]), _f(f[4]), _f(f[5])))
        if rows:
            found.append((m.start(), rows))
    return found


@readable('Gaussian')
def read_gaussian_log(text):
    if 'Gaussian' not in text[:5000] and 'Entering Gaussian System' not in text:
        raise ValueError(tr('Это не выходной файл Gaussian.'))
    blocks = _orientations(text, r'Standard orientation:') or _orientations(text, r'Input orientation:')
    if not blocks:
        raise ValueError(tr('Gaussian: координаты не найдены (Standard/Input orientation).'))
    energies = [
        (m.start(), _f(m.group(1))) for m in re.finditer(r'SCF Done:\s+E\([^)]*\)\s*=\s*(' + NUMBER + ')', text)
    ]
    steps = []
    for n, (pos, rows) in enumerate(blocks):
        end = blocks[n + 1][0] if n + 1 < len(blocks) else len(text)
        e = next((v for p, v in energies if pos < p < end), None)
        steps.append(Step(n + 1, e, _molecule(tr(f'Шаг {n + 1} Gaussian'), rows, None)))
    initial = _orientations(text, r'Input orientation:')
    first = _molecule(tr('Входная геометрия Gaussian'), initial[0][1], None) if initial else steps[0].geometry
    return Trajectory(tuple(steps), first, steps[-1].geometry, 'Gaussian')


# -- Molden ----------------------------------------------------------------------------------------
@readable('Molden')
def read_molden(text):
    sections = re.split(r'^\s*\[([^\]]+)\]([^\n]*)', text, flags=re.M)
    parts = {}
    for k in range(1, len(sections) - 2, 3):
        head = (sections[k] + ' ' + sections[k + 1]).strip()
        parts[head.split()[0].upper()] = (head, sections[k + 2])
    steps, geometry = [], None
    if 'ATOMS' in parts:
        head, body = parts['ATOMS']
        factor = BOHR if 'AU' in head.upper() else 1.0
        rows = []
        for line in body.strip().splitlines():
            f = line.split()
            if len(f) >= 6:
                rows.append(
                    (
                        SYMBOLS[int(f[2]) - 1] if f[2].isdigit() and int(f[2]) > 0 else _symbol(f[0]),
                        _f(f[3]) * factor,
                        _f(f[4]) * factor,
                        _f(f[5]) * factor,
                    )
                )
        geometry = _molecule('Molden', rows, None) if rows else None
    if 'GEOMETRIES' in parts:
        frames = read_xyz_frames(parts['GEOMETRIES'][1].strip())
        energies = []
        if 'GEOCONV' in parts:
            body = parts['GEOCONV'][1]
            m = re.search(r'energy\s*\n((?:\s*' + NUMBER + r'\s*\n?)+)', body, re.I)
            if m:
                energies = [_f(x) for x in m.group(1).split()]
        steps = [Step(n + 1, energies[n] if n < len(energies) else None, f) for n, f in enumerate(frames)]
    if geometry is None and not steps:
        raise ValueError(tr('Molden: нет разделов [Atoms] или [GEOMETRIES].'))
    return Trajectory(tuple(steps), steps[0].geometry if steps else geometry, geometry or steps[-1].geometry, 'Molden')


# -- XYZ with several frames -----------------------------------------------------------------------
def read_xyz_frames(text):
    lines = text.replace('\r', '').strip('\n').split('\n')
    frames, k = [], 0
    while k < len(lines):
        if not lines[k].strip():
            k += 1
            continue
        try:
            n = int(lines[k].split()[0])
            frames.append(read_xyz('\n'.join(lines[k : k + n + 2])))
        except (ValueError, IndexError):
            if frames:  # a cut or broken last frame (a stopped run): the frames before it are kept
                break
            raise ValueError(tr(f'XYZ, кадр {len(frames) + 1} (строка {k + 1}): не удалось прочитать.')) from None
        k += n + 2
    return frames


def xyz_trajectory(text):
    """Several frames → Trajectory (energies from the comment lines: 'E -76.4' or a number)."""
    frames = read_xyz_frames(text)
    steps = []
    for n, f in enumerate(frames):
        m = re.search(r'(?:E(?:nergy)?\s*[=:]?\s*)(' + NUMBER + ')', f.title) or re.fullmatch(
            r'\s*(' + NUMBER + r')\s*', f.title
        )
        steps.append(Step(n + 1, _f(m.group(1)) if m else None, f))
    return Trajectory(tuple(steps), frames[0], frames[-1], 'XYZ')


def xyz_frame_count(text):
    try:
        return len(read_xyz_frames(text))
    except (ValueError, IndexError):
        return 1

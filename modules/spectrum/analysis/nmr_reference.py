"""The NMR reference «TMS at the level of the result» in one click.

§1 THEORY
    A computed chemical shift is delta = sigma_ref - sigma, with sigma_ref the isotropic shielding of the same
    element in tetramethylsilane (TMS, Si(CH3)4) computed by the same method, basis and solvent model: the
    errors of the level then cancel to a large part. A sigma_ref of another level is wrong by up to several
    ppm for 13C, so the reference is kept per level of theory (reaction.level_of_theory), not per element only.
§2 ALGORITHM
    tms_molecule: Si at the origin, C along the four tetrahedral directions u_i at R(Si–C); the three H of
    the methyl at C_i are staggered, each anti to one of the other Si–C bonds: h = cos(a) u_i - sin(a) p_j,
    p_j the unit projection of u_j onto the plane normal to u_i, a = 180° - angle(Si–C–H). The result has
    the point group Td.
    is_tms: 17 atoms, formula C4H12Si, Si bonded to four C (distance below 2.1 Å), each C to three H.
    averaged: the mean isotropic shielding of every element of a table of shieldings.
    tms_input: the input of the result (ORCA: the echo «| n> …» between «INPUT FILE» and «END OF INPUT»;
    Gaussian: the Link 0 lines and the route section) with the geometry replaced by TMS (charge 0,
    multiplicity 1); the job words that concern the molecule of the result go: frequencies, transition-state
    searches, scans, IRC, NEB, the orbitals read from another file (MORead, %moinp, guess=read,
    geom=check); NMR is added when missing. A %geom block with constraints or a scan and an %eprnmr block
    that lists nuclei by number refer to the atoms of the result: the former raises ValueError, the latter
    is dropped (NMR computes all nuclei).
    key: a text usable as a QSettings key for a level («/» and «\\» replaced).
§3 APPLICATIONS
    modules/spectrum/views/spectra_view.NMRPanel; modules/spectrum/workspace (the input goes to Sextant through
    open_input_file).
§4 SPECIFICATION
    TMS_SI_C = 1.875 Å, TMS_C_H = 1.093 Å, TMS_SI_C_H = 111.0°.
    tms_molecule() -> azimuth.core.Molecule (title «TMS»).
    is_tms(molecule) -> bool.
    averaged(shieldings) -> {element: mean isotropic shielding}.
    tms_input(text, program='') -> (kind 'orca' | 'gaussian', input text); ValueError when the result has
        no readable input or refers to its own atoms.
    key(level) -> str.
§5 PROCEDURES - below.
§6 NOTES
    Geometry: experimental Si–C 1.875 Å and C–H 1.093 Å of TMS (gas-phase electron diffraction, rounded);
    the job keeps the «Opt» of the result, so with an optimisation TMS is optimised at the same level, as is
    the usual protocol.
    ASSUMPTION: a result without «Opt» was computed at a geometry of another source; TMS then is computed at
    the geometry above. The user can add «Opt» in the opened input.
§7 TESTS
    tests/spectrum/test_nmr_reference.py.
§8' ROBUSTNESS
    Everything not understood raises ValueError with a message for the user; nothing is guessed.
"""

from math import cos, dist, radians, sin, sqrt
import re

from azimuth.core import Atom, Molecule
from azimuth.i18n import tr

TMS_SI_C = 1.875
TMS_C_H = 1.093
TMS_SI_C_H = 111.0

_ORCA_DROP = {
    'FREQ', 'NUMFREQ', 'ANFREQ', 'SCANTS', 'IRC', 'NEB', 'NEB-CI', 'NEB-TS', 'ZOOM-NEB-CI', 'MOREAD', 'NUMGRAD',
}
_ORCA_OPT = {'OPTTS': 'Opt'}


def _unit(v):
    n = sqrt(sum(c * c for c in v))
    return tuple(c / n for c in v)


def tms_molecule():
    directions = [_unit(v) for v in ((1, 1, 1), (1, -1, -1), (-1, 1, -1), (-1, -1, 1))]
    a = radians(180.0 - TMS_SI_C_H)
    atoms = [Atom('Si', 0.0, 0.0, 0.0)]
    hydrogens = []
    for i, u in enumerate(directions):
        c = tuple(TMS_SI_C * x for x in u)
        atoms.append(Atom('C', *c))
        for j, w in enumerate(directions):
            if j == i:
                continue
            dot = sum(x * y for x, y in zip(w, u))
            p = _unit(tuple(y - dot * x for x, y in zip(u, w)))
            h = tuple(cos(a) * x - sin(a) * y for x, y in zip(u, p))
            hydrogens.append(Atom('H', *(cc + TMS_C_H * hh for cc, hh in zip(c, h))))
    return Molecule('TMS', tuple(atoms + hydrogens))


def is_tms(molecule):
    if molecule is None or len(molecule.atoms) != 17:
        return False
    atoms = molecule.atoms
    symbols = [a.symbol for a in atoms]
    if sorted(symbols) != sorted(['Si'] + ['C'] * 4 + ['H'] * 12):
        return False
    si = atoms[symbols.index('Si')]
    carbons = [a for a in atoms if a.symbol == 'C']
    if any(dist(si.position, c.position) > 2.1 for c in carbons):
        return False
    hs = [a for a in atoms if a.symbol == 'H']
    return all(sum(dist(c.position, h.position) < 1.25 for h in hs) == 3 for c in carbons)


def averaged(shieldings):
    found = {}
    for s in shieldings:
        found.setdefault(s.element, []).append(s.isotropic)
    return {element: sum(v) / len(v) for element, v in found.items()}


def key(level):
    return re.sub(r'[/\\]', '|', level.strip())


def _coordinates(molecule):
    return '\n'.join(f'{a.symbol:<2} {a.x:13.8f} {a.y:13.8f} {a.z:13.8f}' for a in molecule.atoms)


def _orca_echo(text):
    m = re.search(r'INPUT FILE\s*\n=+\s*\n(.*?)\*{4}END OF INPUT\*{4}', text, re.S)
    if not m:
        raise ValueError(tr('В выводе ORCA нет копии входного файла («INPUT FILE»): входной файл для TMS не собрать.'))
    lines = re.findall(r'^\|\s*\d+>\s?(.*)$', m[1], re.M)
    if not lines:
        raise ValueError(tr('В выводе ORCA нет копии входного файла («INPUT FILE»): входной файл для TMS не собрать.'))
    return lines


def _orca_input(text):
    lines = _orca_echo(text)
    out = []
    has_nmr = False
    k = 0
    while k < len(lines):
        line = lines[k].rstrip()
        stripped = line.strip()
        low = stripped.lower()
        if re.match(r'^\*\s*(xyz|int|internal|gzmt)\b', low):  # the geometry of the result
            k += 1
            while k < len(lines) and lines[k].strip() != '*':
                k += 1
            k += 1
            continue
        if re.match(r'^\*\s*(xyzfile|gzmtfile)\b', low):
            k += 1
            continue
        if low.startswith('%'):
            name = low[1:].split()[0] if low[1:].split() else ''
            block = [line]
            single = name in ('maxcore', 'moinp') or re.search(r'\bend\s*$', low[len(name) + 1:]) is not None
            if not single:
                k += 1
                while k < len(lines) and lines[k].strip().lower() != 'end':
                    block.append(lines[k].rstrip())
                    k += 1
                if k < len(lines):
                    block.append(lines[k].rstrip())
            joined = '\n'.join(block).lower()
            if name == 'coords':
                raise ValueError(tr('Геометрия результата задана блоком %coords: входной файл для TMS не собрать.'))
            if name == 'geom' and re.search(r'\b(constraints|scan|modify_internal)\b', joined):
                raise ValueError(tr('В расчёте есть ограничения или скан геометрии — они относятся к его атомам. '
                                    'Откройте TMS в Компасе и задайте тот же метод и базис.'))
            if name == 'moinp':
                k += 1
                continue
            if name == 'eprnmr':
                if re.search(r'nuclei\s*=\s*\d', joined):
                    k += 1
                    continue
                has_nmr = True
            out.extend(block)
            k += 1
            continue
        if stripped.startswith('!'):
            words = []
            for word in stripped[1:].split():
                upper = word.upper()
                if upper in _ORCA_DROP:
                    continue
                if upper == 'NMR':
                    has_nmr = True
                words.append(_ORCA_OPT.get(upper, word))
            if words:
                out.append('! ' + ' '.join(words))
            k += 1
            continue
        out.append(line)
        k += 1
    while out and not out[-1].strip():
        out.pop()
    if not any(line.strip().startswith('!') for line in out):
        raise ValueError(tr('В копии входного файла ORCA нет строки «!» с методом и базисом.'))
    if not has_nmr:
        first = next(i for i, line in enumerate(out) if line.strip().startswith('!'))
        out[first] += ' NMR'
    if out and out[0].startswith('#'):  # the title comment of the result names its molecule
        out.pop(0)
    out.insert(0, '# TMS - NMR reference at the level of the result')
    return '\n'.join(out) + '\n\n* xyz 0 1\n' + _coordinates(tms_molecule()) + '\n*\n'


def _gaussian_route(text):
    lines = text.replace('\r', '').split('\n')
    for k, line in enumerate(lines):
        if line.startswith(' #') and k > 0 and re.match(r'^ -{5,}\s*$', lines[k - 1]):
            route = [line[1:]]
            for more in lines[k + 1:]:
                if re.match(r'^ -{5,}\s*$', more):
                    break
                route.append(more[1:])
            link0 = [l.strip() for l in lines[:k] if re.match(r'^ %\w+\s*=', l)]
            return ''.join(route).strip(), link0
    raise ValueError(tr('В выводе Gaussian нет маршрута «#…»: входной файл для TMS не собрать.'))


def _gaussian_input(text):
    route, link0 = _gaussian_route(text)
    words = []
    has_nmr = False
    for word in route.split():
        base = re.split(r'[(=]', word, maxsplit=1)[0].lower()
        if base in ('freq', 'irc', 'scan', 'stable'):
            continue
        if base == 'opt':
            options = re.split(r'[=(),]', word.lower())[1:]
            if any(o in ('ts', 'qst2', 'qst3', 'modredundant', 'saddle') or o.startswith('saddle') for o in options):
                word = 'Opt'
        if base in ('guess', 'geom') and re.search(r'read|check|allcheck', word, re.I):
            continue
        if base == 'nmr':
            has_nmr = True
        words.append(word)
    if not has_nmr:
        words.append('NMR')
    head = [l for l in link0 if not l.lower().startswith(('%chk', '%oldchk', '%rwf'))]
    head.append('%chk=TMS.chk')
    return ('\n'.join(head) + '\n' + ' '.join(words) + '\n\nTMS - NMR reference at the level of the result\n\n0 1\n'
            + _coordinates(tms_molecule()) + '\n\n')


def tms_input(text, program=''):
    if 'Gaussian' in program or 'Entering Gaussian System' in text[:20000] or re.search(r'^ Gaussian \d\d:', text[:5000], re.M):
        return 'gaussian', _gaussian_input(text)
    if 'O   R   C   A' in text[:20000] or 'ORCA' in program or 'INPUT FILE' in text:
        return 'orca', _orca_input(text)
    raise ValueError(tr('Входной файл для TMS собирается по выводу ORCA или Gaussian.'))

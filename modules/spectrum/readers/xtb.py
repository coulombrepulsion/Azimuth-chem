"""Read an xtb run (output and the files xtb writes next to it) into an Output.

§1 THEORY
    xtb (Grimme's semiempirical tight-binding GFNn-xTB and the GFN-FF force field) prints the energy,
    the convergence of an optimization and the population analysis in its output, but writes the final
    geometry, the optimization path, the normal modes and some properties to separate files in the
    working directory: xtbopt.xyz, xtbopt.log, g98.out (normal modes in the Gaussian 98 layout),
    vibspectrum, charges, wbo. The bond orders are Wiberg orders (in the orthogonalized AO basis).
§2 ALGORITHM
    Output text: version «xtb version 6.6.1», the coordinate file («coordinate file : name»), energies:
    «| TOTAL ENERGY value Eh |» of the summary boxes, optimization: «GEOMETRY OPTIMIZATION CONVERGED»,
    errors: «[ERROR]» or «abnormal termination of xtb»; normal end: «finished run on». The charge column
    «q» of the table «# Z covCN q C6AA α(0)», the Wiberg table, the dipole «full: x y z tot».
    With the path of the output the neighbours are read: geometry from xtbopt.xyz (an optimization), else
    the coordinate file (when it is an .xyz); steps from xtbopt.log (frames with «energy: E gnorm: g»);
    frequencies and modes from g98.out (gaussian._modes), else the projected frequencies of the output
    (eigval rows, the 6 or 5 zero modes left out); 8-digit charges from «charges» and bond orders from
    «wbo» (i j order) when their atom count matches.
§3 APPLICATIONS
    modules/spectrum/readers/outputs.py.
§4 SPECIFICATION
    is_xtb(text) -> bool; read_xtb(text, path=None) -> orca.Output with program 'xtb <version>', properties
    with charges {'xtb': ...}, mayer_bonds holding the Wiberg orders (bond_kind 'Wiberg'), dipole.
§5 PROCEDURES - below.
§6 NOTES
    Verified 2026-10-23 on the xtb 6.6.1 runs of the cclib test data (data/XTB/basicXTB6.6.1: dvb_sp,
    dvb_opt, dvb_ir, BSD-3-Clause; copies in tests/data/xtb). The dipole components x y z of
    «molecular dipole: full:» are in atomic units and «tot» in Debye: in the scan of H2O2
    (tests/data/scan2d/h2o2_scan2d_xtb.out) |(−0.013, 0.131, 0.005)| = 0.1317 e·bohr = 0.335 D, «tot» 0.334.
§7 TESTS
    tests/spectrum/test_xtb.py.
§8' ROBUSTNESS
    A missing neighbour file leaves that part empty; files that do not match the atoms are ignored.
"""

from dataclasses import replace
from math import isfinite
from pathlib import Path
import re

from modules.spectrum.readers.results import NUMBER, OptimizationStep, Output
from modules.spectrum.readers.orca_properties import Properties
from azimuth.core import read_xyz


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


def is_xtb(text):
    head = text[:20000]
    return bool(re.search(r'\bx\s*T\s*B\b', head)) and 'xtb version' in head


def _neighbour(path, name):
    if path is None:
        return None
    candidate = Path(path).with_name(name)
    try:
        return candidate.read_text(encoding='utf-8', errors='replace') if candidate.is_file() else None
    except OSError:
        return None


def _frames(text):
    from modules.compass.chemistry.formats import read_xyz_frames

    try:
        frames = read_xyz_frames(text)
    except ValueError:
        return []
    energies = [_number(m[1]) for m in re.finditer(r'energy:\s*(' + NUMBER + ')', text)]
    return list(zip(frames, energies)) if len(energies) == len(frames) else [(f, None) for f in frames]


def _charge_table(text, count):
    m = re.search(r'#\s+Z\s+covCN\s+q\s+C6AA', text)
    if not m:
        return None
    values = []
    for line in text[m.end() :].splitlines()[1:]:
        f = line.split()
        if len(f) < 7 or not f[0].isdigit():
            break
        values.append(_number(f[4]))
    return tuple(values) if len(values) == count else None


def _wiberg_table(text, count):
    """Bond orders of the table «largest (>0.10) Wiberg bond orders for each atom»; rows with more than
    three partners continue on lines without the «#  Z sym  total --» part."""
    m = re.search(r'largest \(>0\.10\) Wiberg bond orders for each atom', text)
    if not m:
        return ()
    bonds = {}
    started = False
    atom = None
    for line in text[m.end() :].splitlines():
        f = line.split()
        if not started and (not f or not f[0].isdigit()):
            continue  # the blank line, the dashes and the column titles
        started = True
        if not f or not f[0].isdigit():
            break
        if '--' in f:
            atom = int(f[0]) - 1
            rest = f[f.index('--') + 1 :]
        elif atom is not None and len(f) % 3 == 0:
            rest = f
        else:
            break
        for k in range(0, len(rest) - 2, 3):
            j = int(rest[k]) - 1
            bonds[(min(atom, j), max(atom, j))] = _number(rest[k + 2])
    return tuple((i, j, v) for (i, j), v in sorted(bonds.items()) if i < count and j < count)


def _wbo_file(text, count):
    bonds = []
    for line in text.splitlines():
        f = line.split()
        if len(f) != 3:
            return ()
        i, j = int(f[0]) - 1, int(f[1]) - 1
        if not (0 <= i < count and 0 <= j < count):
            return ()
        bonds.append((min(i, j), max(i, j), _number(f[2])))
    return tuple(sorted(bonds))


def _eigval_frequencies(text, count):
    blocks = list(re.finditer(r'projected vibrational frequencies \(cm⁻¹\)\s*\n((?:eigval :.*\n)+)', text))
    if not blocks:
        return ()
    values = [_number(v) for line in blocks[-1][1].splitlines() for v in line.split(':')[1].split()]
    if count and len(values) != 3 * count:
        return ()
    nonzero = [v for v in values if abs(v) > 0.5]
    return tuple((k + 1, v) for k, v in enumerate(nonzero))


def _scan(path):
    """The relaxed scan of xtb — the frames of xtbscan.log (energy in the comment) and the scanned coordinate
    of xcontrol (the first row of $constrain when there is a $scan); the value of every point from its geometry."""
    log, control = _neighbour(path, 'xtbscan.log'), _neighbour(path, 'xcontrol')
    if not log or not control or '$scan' not in control:
        return None
    from azimuth.core import coordinate_value
    from modules.spectrum.readers.orca_scan import Coordinate, Point, Scan

    found = re.search(r'\$constrain.*?^\s*(distance|angle|dihedral)\s*:\s*([\d,\s]+?),\s*(?:auto|' + NUMBER + r')\s*$',
                      control, re.S | re.M)
    frames = _frames(log)
    if not found or not frames:
        return None
    kind = {'distance': 'B', 'angle': 'A', 'dihedral': 'D'}[found[1]]
    atoms = tuple(int(n) - 1 for n in found[2].replace(',', ' ').split())
    if len(atoms) != {'B': 2, 'A': 3, 'D': 4}[kind] or any(a >= len(frames[0][0].atoms) for a in atoms):
        return None
    coordinate = Coordinate({'B': 'bond', 'A': 'angle', 'D': 'dihedral'}[kind], atoms)
    points = tuple(Point(k + 1, (coordinate_value(f, kind, atoms),), e, replace(f, title=f'xtb · точка {k + 1}'))
                   for k, (f, e) in enumerate(frames))
    return Scan('relaxed', (coordinate,), points)


def read_xtb(text, path=None):
    if not is_xtb(text):
        raise ValueError('not an xtb output')
    version = re.search(r'xtb version (\S+)', text)
    program = f'xtb {version[1]}' if version else 'xtb'
    energies = tuple(_number(m[1]) for m in re.finditer(r'\|\s*TOTAL ENERGY\s+(' + NUMBER + r')\s+Eh\s*\|', text))
    converged = 'GEOMETRY OPTIMIZATION CONVERGED' in text
    error = bool(re.search(r'\[ERROR\]|abnormal termination of xtb', text))
    normal = 'finished run on' in text and not error
    geometry = initial = None
    steps = ()
    log = _neighbour(path, 'xtbopt.log')
    if log:
        frames = _frames(log)
        steps = tuple(
            OptimizationStep(k + 1, e, replace(f, title=f'xtb · шаг {k + 1}')) for k, (f, e) in enumerate(frames)
        )
    optimized = _neighbour(path, 'xtbopt.xyz')
    name = re.search(r'coordinate file\s*:\s*(\S+)', text)
    source = _neighbour(path, Path(name[1]).name) if name else None
    if source and name[1].lower().endswith('.xyz'):
        try:
            initial = read_xyz(source)
        except ValueError:
            initial = None
    if optimized and ('--opt' in text or converged):
        try:
            geometry = read_xyz(optimized)
        except ValueError:
            geometry = None
    if geometry is None:
        geometry = initial
    count = len(geometry.atoms) if geometry else 0
    vibration_geometry, frequencies, modes = None, (), ()
    g98 = _neighbour(path, 'g98.out')
    if g98:
        from modules.spectrum.readers.gaussian import _modes, _orientations

        vibration_geometry, frequencies, modes = _modes(g98, _orientations(g98))
        if vibration_geometry is not None and count and len(vibration_geometry.atoms) != count:
            vibration_geometry, frequencies, modes = None, (), ()
    if not frequencies:
        frequencies = _eigval_frequencies(text, count)
    props = None
    if geometry is not None:
        charges = {}
        file = _neighbour(path, 'charges')
        values = None
        if file:
            numbers = file.split()
            if len(numbers) == count:
                values = tuple(_number(v) for v in numbers)
        values = values or _charge_table(text, count)
        if values:
            charges['xtb'] = values
        bonds = ()
        wbo = _neighbour(path, 'wbo')
        if wbo:
            bonds = _wbo_file(wbo, count)
        bonds = bonds or _wiberg_table(text, count)
        dipole = dipole_debye = None
        m = None
        for m in re.finditer(
            r'molecular dipole:\s*\n.*\n\s*q only:.*\n\s*full:\s*('
            + NUMBER
            + r')\s+('
            + NUMBER
            + r')\s+('
            + NUMBER
            + r')\s+('
            + NUMBER
            + ')',
            text,
        ):
            pass
        if m:
            dipole = tuple(_number(m[i]) for i in (1, 2, 3))
            dipole_debye = _number(m[4])
        props = Properties(geometry, charges, {}, None, bonds, dipole, dipole_debye, None, 'Wiberg')
        if props.empty:
            props = None
    if not energies and geometry is None:
        raise ValueError('no recognizable section of an xtb output')
    scan = _scan(path)
    result = Output(
        normal,
        converged,
        bool(re.search(r'SCC is not converged|SCF not converged', text, re.I)),
        energies,
        frequencies,
        replace(geometry, title=program) if geometry else None,
        False,
        steps,
        vibration_geometry,
        modes,
        'xtb' if error else None,
        False,
        initial,
        props,
        None,
        (),
        (),
        program,
        None,
    )
    return replace(result, scan=scan) if scan is not None else result

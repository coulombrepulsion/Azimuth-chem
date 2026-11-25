"""Read a Gaussian log file (Gaussian 09/16) into the same Output as an ORCA output.

§1 THEORY
    The same quantities as for ORCA (modules/spectrum/readers/orca.py): energies, the last geometry, the steps of an
    optimization, harmonic frequencies with their Cartesian normal modes and IR intensities, population
    charges and the dipole moment, electronic excitations (TD-DFT, CIS), NMR shieldings, potential energy
    surface scans. Gaussian prints geometries in the input orientation and, unless NoSymm, again in its
    standard orientation; populations, the dipole and the normal modes refer to the standard orientation,
    so the standard orientation is used wherever it is printed.
§2 ALGORITHM
    Orientation blocks («Standard orientation:», else «Input orientation:» or «Z-Matrix orientation:»):
    rows «centre, atomic number, type, x, y, z» between dashed lines; dummy atoms (number <= 0) are left
    out. Energies: every «SCF Done: E(...) = value». The archive entry («1\\1\\...\\@») names the method
    (5th field, e.g. RCCSD(T)-FC); when it is correlated (ARCHIVE_ENERGIES) its value there (7 decimals)
    is the final energy; lower levels printed on the way (MP2 of a CCSD job) are not used.
    Termination: the last «Normal termination of Gaussian» after the last «Error termination» (an error
    names its link, e.g. l9999); SCF failure: «Convergence failure» or «Convergence criterion not met».
    Optimization: «Optimization completed» (or «Stationary point found») without a later «Optimization
    stopped». Steps: every orientation block that is followed by «SCF Done» before the next orientation,
    in an optimization (Berny «Step number» present), at least two (a frequency job checks for a
    stationary point with one). Frequencies: the high-precision block (freq=HPModes,
    «Coord Atom Element:») if present, else the standard block («Atom AN X Y Z», three modes side by side);
    the geometry of the modes is the orientation printed before «Harmonic frequencies»; mode numbers
    1..3N-6 as printed. Populations: «Mulliken charges[ and spin densities]:» (G16) / «Mulliken atomic
    charges:» (G09), «APT charges:», «Hirshfeld charges, spin densities, dipoles, and CM5 charges»; each
    belongs to the last orientation before it, rows must match its elements. Dipole: «Dipole moment
    (field-independent basis, Debye)» X Y Z Tot. Excitations: «Excited State n: Singlet-BU E eV λ nm
    f=..». NMR: «n C Isotropic = σ Anisotropy = Δσ». Scans: relaxed (opt=modredundant, «S n step» in
    the ModRedundant input): a point at every «Optimization completed/stopped»; unrelaxed (Scan): one
    point per orientation with its «SCF Done», checked against «Summary of the potential surface scan».
§3 APPLICATIONS
    modules/spectrum/readers/outputs.py (read_any) for the Spectrum workspace and Compass.
§4 SPECIFICATION
    is_gaussian(text) -> bool; read_gaussian(text) -> orca.Output with program 'Gaussian 16' / 'Gaussian 09'
    / 'Gaussian', final_energy (label, hartree) or None. ValueError: no recognizable Gaussian section.
    DEBYE_GAUSSIAN = 2.54174623 D per e*bohr (dipole in a.u. = printed Debye / this factor).
§5 PROCEDURES - below.
§6 NOTES
    Formats verified 2026-10-23 on the Gaussian 16 logs of the cclib test data (github.com/cclib/cclib,
    data/Gaussian/basicGaussian16, commit 76df867, BSD-3-Clause): dvb_gopt, dvb_ir (HPModes), dvb_td,
    dvb_nmr, dvb_scan_relaxed, dvb_scan_unrelaxed, dvb_un_sp, water_mp2, water_ccsdt (excerpts in
    tests/data/gaussian), and all 35 Gaussian 16 and 25 Gaussian 09 logs of basicGaussian16/09 read without
    error. DEBYE_GAUSSIAN = 2.54174623 (CODATA 2006-2010, Gaussian's constants) agrees with Gaussian's own
    numbers: Trp_polar, «Tot= 2.7110» D against the archive «Dipole=» 1.0665926 a.u. gives 2.54174 +- 2e-5
    (the rounding of Tot); it only converts the printed Debye value to a.u. for the length of the arrow.
    Forces («Forces (Hartrees/Bohr)») are printed in the input orientation and are not read.
    0.89.27, Gaussian 09: TD-DFT checked on a G09 A.02 output of the user (tests/data/gaussian09, CRLF) and on a
    G09 A.01 TD + Freq job (anisole, NoSymm, 97 points, not copied — a test job of the Gaussian distribution): with
    the excited-state energies the thermochemistry of thermo.py agrees with Gaussian's printed «Sum of electronic and
    zero-point Energies» −346.562368 and «… thermal Free Energies» −346.595368 to 1e-6 hartree; with the ground SCF
    it was 0.1735 hartree off.
§7 TESTS
    tests/spectrum/test_gaussian.py.
§8' ROBUSTNESS
    Blocks that do not parse or do not match the geometry are skipped; numbers must be finite.
"""

from dataclasses import replace
from math import isfinite
import re

from modules.spectrum.readers.results import NUMBER, OptimizationStep, Output
from modules.spectrum.readers.orca_properties import Properties
from modules.spectrum.readers.orca_spectra import EV_CM, Excitation, Shielding
from azimuth.core import Atom, Molecule, SYMBOLS

DEBYE_GAUSSIAN = 2.54174623
ORIENTATION = re.compile(r'^\s*(Standard|Input|Z-Matrix) orientation:\s*$', re.M)
ARCHIVE_ENERGIES = (
    'CCSD(T)',
    'CCSD',
    'CCD',
    'QCISD(T)',
    'QCISD',
    'CISD',
    'CID',
    'BD(T)',
    'BD',
    'MP5',
    'MP4SDTQ',
    'MP4SDQ',
    'MP4DQ',
    'MP4D',
    'MP3',
    'MP2',
)


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


def is_gaussian(text):
    head = text[:20000]
    return 'Entering Gaussian System' in head or 'Gaussian, Inc.' in head or bool(re.search(r'Gaussian (09|16):', head))


def _all_orientations(text):
    """[(kind, start, end, Molecule)] of every orientation block, in file order."""
    found = []
    for match in ORIENTATION.finditer(text):
        lines = text[match.end() :].splitlines()
        dashes, rows = 0, []
        offset = 0
        for line in lines[1:]:
            offset += len(line) + 1
            if set(line.strip()) == {'-'}:
                dashes += 1
                if dashes == 3:
                    break
                continue
            if dashes == 2:
                f = line.split()
                if len(f) != 6:
                    rows = None
                    break
                z = int(f[1])
                if z <= 0:  # dummy and ghost centres
                    continue
                if z > len(SYMBOLS):
                    rows = None
                    break
                rows.append(Atom(SYMBOLS[z - 1], *(_number(v) for v in f[3:6])))
        if rows:
            found.append((match[1], match.start(), match.end() + offset, Molecule('Gaussian', tuple(rows))))
    return found


def _orientations(text):
    """The standard orientations if Gaussian printed any, else all orientation blocks."""
    found = _all_orientations(text)
    standard = [o for o in found if o[0] == 'Standard']
    return standard if standard else found


def _last_before(orientations, position):
    best = None
    for o in orientations:
        if o[2] <= position:
            best = o
    return best


def _archive(text):
    """(method of the job, {key: value}) from the last archive entry «1\\1\\...\\@», or (None, {})."""
    starts = [m.start() for m in re.finditer(r'^ 1\\1\\', text, re.M)]
    if not starts:
        return None, {}
    joined = ''
    for line in text[starts[-1] :].splitlines():
        joined += line[1:]
        if '\\@' in joined:
            break
    else:
        return None, {}
    parts = joined[: joined.index('\\@')].split('\\')
    method = parts[4] if len(parts) > 4 else None
    if method:
        method = re.sub(r'-(FC|Full|FullDirect|RW|SOS)$', '', method)
        method = re.sub(r'^(RO|R|U)(?=[A-Z])', '', method)
    fields = {}
    for part in parts:
        if '=' in part:
            key, value = part.split('=', 1)
            fields[key.strip()] = value.strip()
    return method, fields


def _final_energy(text):
    """The archive energy of the job's own method when it is correlated (MP2, CCSD(T), ...), else None."""
    method, fields = _archive(text)
    if method in ARCHIVE_ENERGIES and method in fields:
        try:
            return method, _number(fields[method].split(',')[-1])
        except ValueError:
            return None
    return None


def _scf_energies(text):
    return [(m.start(), _number(m[1])) for m in re.finditer(r'SCF Done:\s+E\(\S+\)\s*=\s*(' + NUMBER + ')', text)]


def _route(text):
    """The route section of the first job (« #… » between two lines of dashes, continued lines joined)."""
    m = re.search(r'^ -{5,}\n( #.*?)\n -{5,}$', text[:200000].replace('\r', ''), re.M | re.S)  # CRLF of Windows
    return ''.join(line[1:] for line in m[1].split('\n')) if m else ''


def _excited_energies(text, energies, route):
    """«Total Energy, E(TD-HF/TD-KS) = E» after «This state for optimization …» of root n. A TD (or CIS)
    job with Opt or Freq follows that root: its energies are these (the ground SCF of every point is replaced, as
    ORCA's E(tot)), and the result is (energies, None). A single-point TD keeps the ground SCF and gives
    (energies, (root, E)) — the excited state apart, as for ORCA."""
    states = [(m.start(), int(m[1])) for m in re.finditer(r'Excited State\s+(\d+):', text)]
    found = []
    for m in re.finditer(r'This state for optimization[^\n]*\n\s*Total Energy, E\(TD-HF/TD-KS\)\s*=\s*(' + NUMBER + ')', text):
        before = [n for p, n in states if p < m.start()]  # the root: the last state printed before (its orbital
        if before:                                         # contributions may take a thousand lines, IOp(9/40))
            found.append((m.start(), before[-1], _number(m[1])))
    if not found or not energies:
        return energies, None
    low = route.lower()
    gradient = re.search(r'(^|[\s/#])(td|tda|cis)\b', low) and re.search(r'(^|[\s#])(opt|freq)\b', low)
    if gradient:
        replaced = []
        for k, (position, energy) in enumerate(energies):
            end = energies[k + 1][0] if k + 1 < len(energies) else len(text)
            inside = [e for p, _, e in found if position < p < end]
            if not inside:
                return energies, None  # not every point has its excited state: leave the SCF energies
            replaced.append((position, inside[-1]))
        return replaced, None
    _, root, energy = found[-1]
    return energies, (root, energy)


def _steps(text, orientations, energies):
    if 'Step number' not in text:
        return ()
    steps = []
    for k, o in enumerate(orientations):
        nxt = orientations[k + 1][1] if k + 1 < len(orientations) else len(text)
        inside = [e for p, e in energies if o[2] <= p < nxt]
        if inside:
            steps.append(
                OptimizationStep(len(steps) + 1, inside[-1], replace(o[3], title=f'Gaussian · шаг {len(steps) + 1}'))
            )
    return tuple(steps) if len(steps) > 1 else ()


def _modes(text, orientations):
    from modules.spectrum.readers.vibration_data import Vibration

    heads = [m.start() for m in re.finditer(r'Harmonic frequencies \(cm\*\*-1\)', text)]
    if not heads:
        return None, (), ()
    start = heads[-1]
    # freq=HPModes prints the high-precision table first and the standard one after it: prefer the former
    if len(heads) > 1 and 'Coord Atom Element:' in text[heads[-2] : heads[-1]]:
        start = heads[-2]
    geometry = _last_before(orientations, start)
    geometry = geometry[3] if geometry else None
    natoms = len(geometry.atoms) if geometry else 0
    section = text[start:]
    end = re.search(r'^\s*-{5,}\s*\n\s*-\s*Thermochemistry|^ - Thermochemistry -', section, re.M)
    if end:
        section = section[: end.start()]
    modes = {}
    lines = section.splitlines()
    high = 'Coord Atom Element:' in section
    k = 0
    current = []
    while k < len(lines):
        line = lines[k]
        if high and line.strip().startswith('Frequencies ---'):
            values = [_number(v) for v in line.split('---')[1].split()]
            numbers = (
                [int(x) for x in lines[k - 2].split()]
                if k >= 2 and lines[k - 2].split() and all(x.isdigit() for x in lines[k - 2].split())
                else []
            )
            if len(numbers) != len(values):
                break
            current = numbers
            for n, v in zip(numbers, values):
                modes[n] = {'frequency': v, 'vectors': None, 'intensity': None, 'vcd': None}
        elif line.strip().startswith('Rot. str.') and current:  # Freq=VCD, 10⁻⁴⁴ esu²·cm²
            for n, v in zip(current, re.split(r'-{2,}', line, maxsplit=1)[1].split()):
                modes[n]['vcd'] = _number(v)
        elif high and line.strip().startswith('IR Intensities ---') and current:
            for n, v in zip(current, line.split('---')[1].split()):
                modes[n]['intensity'] = _number(v)
        elif high and line.strip().startswith('Coord Atom Element:') and current:
            vectors = {n: [[0.0, 0.0, 0.0] for _ in range(natoms)] for n in current}
            seen = 0
            for row in lines[k + 1 : k + 1 + 3 * natoms]:
                f = row.split()
                if len(f) != 3 + len(current):
                    break
                axis, atom = int(f[0]) - 1, int(f[1]) - 1
                if not (0 <= axis < 3 and 0 <= atom < natoms):
                    break
                for n, v in zip(current, f[3:]):
                    vectors[n][atom][axis] = _number(v)
                seen += 1
            if seen == 3 * natoms:
                for n in current:
                    modes[n]['vectors'] = tuple(tuple(r) for r in vectors[n])
            k += 3 * natoms
            current = []
        elif not high and line.strip().startswith('Frequencies --'):
            values = [_number(v) for v in line.split('--')[1].split()]
            numbers = (
                [int(x) for x in lines[k - 2].split()]
                if k >= 2 and all(x.isdigit() for x in lines[k - 2].split())
                else []
            )
            if len(numbers) != len(values):
                break
            current = numbers
            for n, v in zip(numbers, values):
                modes[n] = {'frequency': v, 'vectors': None, 'intensity': None, 'vcd': None}
        elif not high and line.strip().startswith('IR Inten') and current:
            for n, v in zip(current, line.split('--')[1].split()):
                modes[n]['intensity'] = _number(v)
        elif not high and line.split()[:4] == ['Atom', 'AN', 'X', 'Y'] and current:
            vectors = {n: [] for n in current}
            ok = True
            for row in lines[k + 1 : k + 1 + natoms]:
                f = row.split()
                if len(f) != 2 + 3 * len(current):
                    ok = False
                    break
                for c, n in enumerate(current):
                    vectors[n].append(tuple(_number(v) for v in f[2 + 3 * c : 5 + 3 * c]))
            if ok and all(len(v) == natoms for v in vectors.values()):
                for n in current:
                    modes[n]['vectors'] = tuple(vectors[n])
            k += natoms
            current = []
        k += 1
    if not modes:
        return geometry, (), ()
    frequencies = tuple((n, modes[n]['frequency']) for n in sorted(modes))
    vibrations = tuple(
        Vibration(n, modes[n]['frequency'], modes[n]['vectors'], modes[n]['intensity'], vcd=modes[n]['vcd'])
        for n in sorted(modes)
    )
    return geometry, frequencies, vibrations


def _population(text, orientations):
    """Properties of the last orientation (charges, spins, dipole) or None."""
    if not orientations:
        return None
    last = orientations[-1]
    geometry = last[3]
    symbols = [a.symbol for a in geometry.atoms]
    tail = text[last[2] :]
    charges, spins = {}, {}

    def rows(start, columns):
        """The values of the rows «n  symbol  v1 [v2]» after a header (and its column line), or None."""
        values = []
        for line in tail[start:].splitlines()[2 : 2 + len(symbols)]:
            f = line.split()
            if len(f) < 2 + columns or not f[0].isdigit():
                return None
            index = int(f[0]) - 1
            if not 0 <= index < len(symbols) or f[1] != symbols[index] or index != len(values):
                return None
            values.append([_number(v) for v in f[2 : 2 + columns]])
        return values if len(values) == len(symbols) else None

    for pattern, key, columns in (
        (r'^ Mulliken charges and spin densities:\s*$', 'mulliken', 2),
        (r'^ Mulliken charges:\s*$', 'mulliken', 1),
        (r'^ Mulliken atomic charges:\s*$', 'mulliken', 1),
        (r'^ APT charges:\s*$', 'apt', 1),
    ):
        found = list(re.finditer(pattern, tail, re.M))
        if not found or key in charges:
            continue
        values = rows(found[-1].end(), columns)
        if values:
            charges[key] = tuple(v[0] for v in values)
            if columns == 2:
                spins[key] = tuple(v[1] for v in values)
    found = list(re.finditer(r'^ Hirshfeld charges, spin densities, dipoles, and CM5 charges.*$', tail, re.M))
    if found:
        values = []
        for line in tail[found[-1].end() :].splitlines()[2 : 2 + len(symbols)]:
            f = line.split()
            if len(f) == 8 and f[0].isdigit() and f[1] == symbols[int(f[0]) - 1]:
                values.append([_number(v) for v in f[2:]])
        if len(values) == len(symbols):
            charges['hirshfeld'] = tuple(v[0] for v in values)
            charges['cm5'] = tuple(v[5] for v in values)
            if any(abs(v[1]) > 0 for v in values):
                spins['hirshfeld'] = tuple(v[1] for v in values)
    dipole = dipole_debye = None
    found = list(
        re.finditer(
            r'Dipole moment \(field-independent basis, Debye\):\s*\n\s*X=\s*(\S+)\s+Y=\s*(\S+)\s+Z=\s*(\S+)\s+Tot=\s*(\S+)',
            tail,
        )
    )
    if found:
        m = found[-1]
        dipole = tuple(_number(m[i]) / DEBYE_GAUSSIAN for i in (1, 2, 3))
        dipole_debye = _number(m[4])
    props = Properties(geometry, charges, spins, None, (), dipole, dipole_debye, None)
    return None if props.empty else props


def _excitations(text):
    found = []
    row = re.compile(
        r'Excited State\s+(\d+):\s+(\S+?)-(\S+)\s+('
        + NUMBER
        + r')\s+eV\s+('
        + NUMBER
        + r')\s+nm\s+f=\s*('
        + NUMBER
        + ')'
    )
    multiplicity = {'Singlet': 1, 'Doublet': 2, 'Triplet': 3, 'Quartet': 4, 'Quintet': 5}
    for m in row.finditer(text):
        energy = _number(m[4])
        found.append(
            Excitation(int(m[1]), '?' if m[3] == '?Sym' else m[3], energy, energy * EV_CM, _number(m[5]), _number(m[6]),
                       multiplicity.get(m[2]))  # «Singlet-?Sym» — the symmetry was not determined (NoSymm)
        )
    last = {}
    for e in found:  # an optimization in the excited state prints them again: the last set
        last[e.state] = e
    if not last:
        return ()
    from modules.spectrum.readers.orca_spectra import with_rotatory

    return with_rotatory(sorted(last.values(), key=lambda e: e.energy_ev), _rotatory(text))  # ECD


PLAIN = r'[+-]?\d+\.\d+'
ROTATORY_ROW = re.compile(r'^\s+(\d+)\s+' + PLAIN + r'\s+' + PLAIN + r'\s+' + PLAIN + r'\s+(' + PLAIN + r')(?:\s+' + PLAIN
                          + r')?\s*$')
TENSOR_LINE = re.compile(r'tensor|^\s+1\s+2\s+3\s*$|^\s+\d\s+(?:\s*[+-]?\d\.\d+D[+-]\d+){3}\s*$')


def _rotatory(text):
    """{state: (R length, R velocity)} in 10^-40 cgs from the last «Rotatory Strengths (R) in cgs» table of
    each gauge (the header names «R(velocity)» or «R(length)»); G09 prints the velocity rows between their tensors."""
    tables = {}
    for m in re.finditer(r'Rotatory Strengths \(R\) in cgs[^\n]*\n([^\n]*)\n', text):
        gauge = 'velocity' if 'R(velocity)' in m[1] else 'length' if 'R(length)' in m[1] else None
        if gauge is None:
            continue
        rows = {}
        for line in text[m.end():].splitlines():
            row = ROTATORY_ROW.match(line)
            if row:
                rows[int(row[1])] = _number(row[2])
            elif not TENSOR_LINE.search(line):
                break
        tables[gauge] = rows  # the last table of the gauge
    length, velocity = tables.get('length', {}), tables.get('velocity', {})
    return {str(k): (length.get(k), velocity.get(k)) for k in set(length) | set(velocity)}


def _shieldings(text):
    starts = [m.end() for m in re.finditer(r'SCF GIAO Magnetic shielding tensor \(ppm\):', text)]
    if not starts:
        return ()
    found = []
    for m in re.finditer(
        r'^\s*(\d+)\s+([A-Z][a-z]?)\s+Isotropic =\s*(' + NUMBER + r')\s+Anisotropy =\s*(' + NUMBER + ')',
        text[starts[-1] :],
        re.M,
    ):
        found.append(Shielding(int(m[1]) - 1, m[2], _number(m[3]), _number(m[4])))
    return tuple(found)


def _scan(text, orientations, energies):
    from modules.spectrum.readers.orca_scan import Coordinate, Point, Scan

    m = re.search(r'The following ModRedundant input section has been read:\s*\n((?:.*\n){1,20}?)\s*\n', text)
    coordinates = []
    if m:
        for line in m[1].splitlines():
            f = line.split()
            kinds = {'B': 'bond', 'A': 'angle', 'D': 'dihedral'}
            if f and f[0] in kinds and 'S' in f:
                n = {'B': 2, 'A': 3, 'D': 4}[f[0]]
                coordinates.append(Coordinate(kinds[f[0]], tuple(int(x) - 1 for x in f[1 : 1 + n])))
    if coordinates:
        points = []
        for mark in re.finditer(r'Optimization (completed|stopped)\.', text):
            o = _last_before(orientations, mark.start())
            before = [e for p, e in energies if p < mark.start()]
            if o is None or not before:
                continue
            values = tuple(_coordinate_value(c, o[3]) for c in coordinates)
            points.append(
                Point(
                    len(points) + 1,
                    values,
                    before[-1],
                    replace(o[3], title=f'Gaussian · точка {len(points) + 1}'),
                    False,
                    mark[1] == 'completed',
                )
            )
        return Scan('relaxed', tuple(coordinates), tuple(points)) if len(points) > 1 else None
    summary = re.search(
        r'Summary of the potential surface scan:\s*\n\s*N\s+(.+?)\s*\n\s*-[-\s]+\n((?:\s*\d+\s+.+\n)+)', text
    )
    if not summary:
        return None
    names = summary[1].split()
    if len(names) < 2:
        return None
    rows = [line.split() for line in summary[2].splitlines() if line.strip() and not set(line.strip()) <= {'-', ' '}]
    points = []
    pairs = []
    for k, o in enumerate(orientations):
        nxt = orientations[k + 1][1] if k + 1 < len(orientations) else len(text)
        inside = [e for p, e in energies if o[2] <= p < nxt]
        if inside:
            pairs.append((o[3], inside[-1]))
    if len(pairs) != len(rows):
        return None
    variables = names[:-1]
    for n, (row, (geometry, energy)) in enumerate(zip(rows, pairs)):
        if abs(_number(row[-1]) - energy) > 6e-6:  # the table prints 5 decimals
            return None
        points.append(
            Point(
                n + 1,
                tuple(_number(v) for v in row[1:-1]),
                energy,
                replace(geometry, title=f'Gaussian · точка {n + 1}'),
            )
        )
    return Scan('unrelaxed', tuple(Coordinate('parameter', (), v) for v in variables), tuple(points))


def _coordinate_value(coordinate, molecule):
    import numpy as np

    p = [np.array(molecule.atoms[i].position) for i in coordinate.atoms]
    if coordinate.kind == 'bond':
        return float(np.linalg.norm(p[0] - p[1]))
    if coordinate.kind == 'angle':
        a, b = p[0] - p[1], p[2] - p[1]
        return float(np.degrees(np.arccos(np.clip(a @ b / np.linalg.norm(a) / np.linalg.norm(b), -1, 1))))
    b1, b2, b3 = p[1] - p[0], p[2] - p[1], p[3] - p[2]
    n1, n2 = np.cross(b1, b2), np.cross(b2, b3)
    x = n1 @ n2
    y = np.cross(n1, n2) @ b2 / np.linalg.norm(b2)
    return float(np.degrees(np.arctan2(y, x)))


def read_gaussian(text):
    if not is_gaussian(text):
        raise ValueError('not a Gaussian log file')
    version = re.search(r'Gaussian (09|16):', text[:20000])
    program = f'Gaussian {version[1]}' if version else 'Gaussian'
    orientations = _orientations(text)
    energies, excited = _excited_energies(text, _scf_energies(text), _route(text))
    errors = list(
        re.finditer(r'Error termination (?:via Lnk1e in \S*?(l\d+)\.exe|request processed by link (\d+))', text)
    )
    normals = [m.start() for m in re.finditer(r'Normal termination of Gaussian', text)]
    error_module = None
    if errors:
        e = errors[-1]
        error_module = e[1] or f'l{e[2]}'
    normal = bool(normals) and (not errors or normals[-1] > errors[-1].start())
    if normal:
        error_module = None
    completed = [m.start() for m in re.finditer(r'Optimization completed\.|-- Stationary point found\.', text)]
    stopped = [m.start() for m in re.finditer(r'Optimization stopped\.', text)]
    converged = bool(completed) and (not stopped or completed[-1] > stopped[-1])
    scan = _scan(text, orientations, energies)
    if scan is not None and scan.kind == 'relaxed':
        converged = all(p.converged for p in scan.points)
    vibration_geometry, frequencies, modes = _modes(text, orientations)
    initial = next((o[3] for o in _all_orientations(text) if o[0] in ('Input', 'Z-Matrix')), None)
    geometry = orientations[-1][3] if orientations else None
    if not energies and geometry is None and not frequencies:
        raise ValueError('no recognizable section of a Gaussian log file')
    final = _final_energy(text)
    return Output(
        normal,
        converged,
        bool(re.search(r'Convergence failure -- run terminated|Convergence criterion not met', text)),
        tuple(e for _, e in energies),
        frequencies,
        replace(geometry, title=program) if geometry else None,
        False,
        _steps(text, orientations, energies) if scan is None else (),
        vibration_geometry,
        modes,
        error_module,
        False,
        initial,
        _population(text, orientations),
        scan,
        _excitations(text),
        _shieldings(text),
        program,
        final,
        excited_energy=excited,
    )

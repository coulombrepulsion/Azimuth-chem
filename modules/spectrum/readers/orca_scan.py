"""Potential energy surface scans and IRC paths in an ORCA output.

§1 THEORY
    A scan follows the energy along chosen internal coordinates: a relaxed scan optimizes all other
    coordinates at every point (a constrained optimization), an unrelaxed (rigid) scan only changes the
    chosen ones. An intrinsic reaction coordinate (IRC) is the steepest-descent path in mass-weighted
    coordinates from a transition state (TS) down to the reactant and the product.
§2 ALGORITHM
    Relaxed scan: the output is cut at «RELAXED SURFACE SCAN STEP n»; in every part the lines
    «Bond|Angle|Dihedral (i, j, ...) : value» give the values of the coordinates and the last block
    «CARTESIAN COORDINATES (ANGSTROEM)» is the optimized geometry of the point; the energy is the n-th
    row of the table «The Calculated Surface using the 'Actual Energy'» (else the last «FINAL SINGLE
    POINT ENERGY» of the part). Unrelaxed scan: the same with «TRAJECTORY STEP n», the first geometry of
    the part and the value lines «NAME : value» (Z-matrix parameters such as D7). IRC: the table after
    «IRC PATH SUMMARY» (step, E, dE, max|G|, RMS G; «<= TS» marks the transition state); the geometries
    are not in the output but in «<name>_IRC_Full_trj.xyz», attached by with_trajectory().
§3 APPLICATIONS
    modules/spectrum/readers/orca.py (Output.scan); the drawer of Compass shows the points
    (modules/compass/actions/trajectory_actions.py).
§4 SPECIFICATION
    read_scan(text) -> Scan | None.
    Scan: kind 'relaxed' | 'unrelaxed' | 'irc'; coordinates: tuple of Coordinate(kind 'bond' | 'angle'
        | 'dihedral' | 'parameter', atoms: tuple of 0-based indices (as ORCA prints them) or, name);
        points: tuple of Point(number from 1, values (one per coordinate; IRC: ()), energy hartree | None,
        geometry Molecule | None, ts bool, converged bool | None (relaxed scan: the constrained
        optimization reported convergence)); reference: index of the point the energies are shown
        relative to (scans: the lowest energy; IRC: the TS).
    with_trajectory(scan, text_of_xyz) -> Scan with geometries from the frames (IRC; the frame count must
        equal the number of points, else ValueError).
    Coordinate.label: 'φ(10–9–4–3)' with 1-based atoms as Compass numbers them; unit: 'Å' or '°' or ''.
§5 PROCEDURES - below.
§6 NOTES
    Scans verified 2026-10-23 on real outputs of ORCA 5.0 and 6.0 (cclib test data, data/ORCA,
    dvb_scan_relaxed.out, dvb_scan_unrelaxed.out; excerpts in tests/data/orca_cclib). The IRC summary
    follows the ORCA 6.0 tutorial (faccts.de/docs/orca/6.0/tutorials/react/irc.html: header
    «Step E(Eh) dE(kcal/mol) max(|G|) RMS(G)», «<= TS»). ASSUMPTION: the row layout of that table
    (whitespace-separated numbers, the marker at the end of the row) - no real IRC output was available.
§7 TESTS
    tests/spectrum/test_orca_scan.py.
§8' ROBUSTNESS
    Parts without a readable geometry keep geometry None; points are never paired by position in two
    independent lists except the energy table, whose coordinate values must equal the point's values.
"""

from dataclasses import dataclass, replace
from math import isfinite
import re

from azimuth.core import Molecule, read_xyz

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?'
GEOMETRY = re.compile(r'CARTESIAN COORDINATES\s*\(ANGSTROE?M\)')
KINDS = {'Bond': 'bond', 'Angle': 'angle', 'Dihedral': 'dihedral'}
SYMBOL = {'bond': 'r', 'angle': '∠', 'dihedral': 'φ'}


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


@dataclass(frozen=True)
class Coordinate:
    kind: str
    atoms: tuple = ()
    name: str = ''

    @property
    def label(self):
        if self.kind == 'parameter':
            return self.name
        return SYMBOL[self.kind] + '(' + '–'.join(str(a + 1) for a in self.atoms) + ')'

    @property
    def unit(self):
        return {'bond': 'Å', 'angle': '°', 'dihedral': '°'}.get(self.kind, '')


@dataclass(frozen=True)
class Point:
    number: int
    values: tuple
    energy: float | None
    geometry: Molecule | None
    ts: bool = False
    converged: bool | None = None


@dataclass(frozen=True)
class Scan:
    kind: str
    coordinates: tuple
    points: tuple

    @property
    def reference(self):
        if self.kind == 'irc':
            return next((k for k, p in enumerate(self.points) if p.ts), 0)
        known = [(p.energy, k) for k, p in enumerate(self.points) if p.energy is not None]
        return min(known)[1] if known else 0


def _geometries(part):
    found = []
    for match in GEOMETRY.finditer(part):
        rows = []
        for line in part[match.end() :].splitlines()[1:]:
            if not rows and (not line.strip() or set(line.strip()) <= {'-'}):
                continue
            fields = line.split()
            if len(fields) == 4 and re.fullmatch(r'[A-Z][a-z]?', fields[0]):
                try:
                    rows.append(f'{fields[0]} {_number(fields[1])} {_number(fields[2])} {_number(fields[3])}')
                    continue
                except ValueError:
                    rows = []
            break
        if rows:
            try:
                found.append(read_xyz(f'{len(rows)}\nORCA\n' + '\n'.join(rows)))
            except ValueError:
                pass
    return found


def _surface(text, columns):
    """Rows of the last «Calculated Surface using the 'Actual Energy'» table: (values, energy)."""
    starts = [m.end() for m in re.finditer(r"The Calculated Surface using the 'Actual Energy'", text)]
    if not starts:
        return []
    rows = []
    for line in text[starts[-1] :].splitlines()[1:]:
        fields = line.split()
        if len(fields) != columns + 1 or not all(re.fullmatch(NUMBER, f) for f in fields):
            break
        values = [_number(f) for f in fields]
        rows.append((tuple(values[:-1]), values[-1]))
    return rows


def _scan_coordinates(head_lines):
    """Coordinates from the value lines at the top of the first part."""
    found = []
    for line in head_lines:
        m = re.search(r'(Bond|Angle|Dihedral)\s*\(([\d,\s]+)\)\s*:\s*(' + NUMBER + ')', line)
        if m:
            atoms = tuple(int(a) for a in m[2].replace(',', ' ').split())
            found.append((Coordinate(KINDS[m[1]], atoms), _number(m[3])))
            continue
        m = re.match(r'^\s*\*?\s*([A-Za-z]\w*)\s*:\s*(' + NUMBER + r')\s*\*?\s*$', line)
        if m:
            found.append((Coordinate('parameter', (), m[1]), _number(m[2])))
    return found


def _read_parts(text, header, kind):
    marks = list(re.finditer(header, text))
    if not marks:
        return None
    coordinates = None
    points = []
    for k, mark in enumerate(marks):
        part = text[mark.end() : marks[k + 1].start() if k + 1 < len(marks) else len(text)]
        found = _scan_coordinates(part.splitlines()[:12])
        if not found:
            return None
        if coordinates is None:
            coordinates = tuple(c for c, _ in found)
        elif tuple(c for c, _ in found) != coordinates:
            return None
        geometries = _geometries(part)
        geometry = (geometries[-1] if kind == 'relaxed' else geometries[0]) if geometries else None
        energies = re.findall(r'FINAL SINGLE POINT ENERGY\s+(' + NUMBER + ')', part)
        converged = ('THE OPTIMIZATION HAS CONVERGED' in part) if kind == 'relaxed' else None
        points.append(
            Point(
                int(mark[1]),
                tuple(v for _, v in found),
                _number(energies[-1]) if energies else None,
                geometry,
                False,
                converged,
            )
        )
    table = _surface(text, len(coordinates))
    if len(table) == len(points):
        for k, (values, energy) in enumerate(table):
            if all(abs(a - b) < 1e-6 for a, b in zip(values, points[k].values)):
                points[k] = replace(points[k], energy=energy)
    signature = None
    for k, p in enumerate(points):  # one molecule: the same elements in every point
        if p.geometry is not None:
            current = [a.symbol for a in p.geometry.atoms]
            signature = signature or current
            if current != signature:
                points[k] = replace(p, geometry=None)
    return Scan(kind, coordinates, tuple(points))


def _read_irc(text):
    starts = [m.end() for m in re.finditer(r'IRC PATH SUMMARY', text)]
    if not starts:
        return None
    lines = text[starts[-1] :].splitlines()
    head = next((k for k, line in enumerate(lines[:12]) if re.search(r'Step\s+E\(Eh\)\s+dE\(kcal/mol\)', line)), None)
    if head is None:
        return None
    points = []
    row = re.compile(
        r'^\s*(\d+)\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s*(<=\s*TS)?\s*$'
    )
    for line in lines[head + 1 :]:
        if not line.strip() or set(line.strip()) <= {'-', '='}:
            if points:
                break
            continue
        m = row.match(line)
        if m is None:
            break
        points.append(Point(int(m[1]), (), _number(m[2]), None, bool(m[6])))
    if not points:
        return None
    return Scan('irc', (), tuple(points))


def read_scan(text):
    try:
        scan = _read_parts(text, r'RELAXED SURFACE SCAN STEP\s+(\d+)', 'relaxed')
        if scan is None:
            scan = _read_parts(text, r'TRAJECTORY STEP\s+(\d+)', 'unrelaxed')
        if scan is None:
            scan = _read_irc(text)
    except ValueError:
        return None
    return scan if scan is not None and scan.points else None


def with_trajectory(scan, xyz_text):
    from modules.compass.chemistry.formats import read_xyz_frames

    frames = read_xyz_frames(xyz_text)
    if len(frames) != len(scan.points):
        raise ValueError(f'{len(frames)} frames for {len(scan.points)} points')
    return replace(scan, points=tuple(replace(p, geometry=f) for p, f in zip(scan.points, frames)))

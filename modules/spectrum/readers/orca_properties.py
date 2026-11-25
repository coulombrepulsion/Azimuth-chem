"""Atomic and molecular properties from an ORCA output: charges, spin populations, Mayer bond orders and
valences, dipole moment, Cartesian gradient.

§1 THEORY
    Population analyses divide the electron density among the atoms. Mulliken shares the overlap
    population equally, Löwdin first orthogonalises the basis symmetrically, Hirshfeld weights the density
    by free-atom densities; all three depend on the method and especially on the basis set, so their
    values are compared within one calculation, never across methods. The spin population is the share
    of alpha minus beta density (open shells only). Mayer bond order B_AB = sum over mu on A, nu on B of
    (PS)_mu,nu (PS)_nu,mu (+ the same for the spin density); Mayer's total valence V_A = sum_B B_AB plus the
    free valence. The dipole moment mu = sum_i q_i r_i over nuclei and electrons, so its vector points
    from the negative towards the positive end (physics convention; chemistry textbooks often draw the
    arrow the other way). The Cartesian gradient dE/dR is minus the force on a nucleus.
§2 ALGORITHM
    The output is cut at its geometry blocks «CARTESIAN COORDINATES (ANGSTROEM)». Every property block
    belongs to the last geometry printed before it. Only properties of the last geometry are returned:
    after an optimization ORCA prints the populations and the dipole again for the final structure, but
    its last gradient belongs to the previous step (the final structure differs by ~5e-4 A), so no
    gradient is returned then. Of several blocks of one kind for that geometry the last one is used.
    Rows are checked against the element symbols of the geometry; a block that does not fit is ignored.
§3 APPLICATIONS
    modules/spectrum/readers/orca.py (Output.properties); Compass shows them on the model
    (modules/compass/actions/property_actions.py, viewer.draw_properties).
§4 SPECIFICATION
    read_properties(text) -> Properties | None (None: no geometry or no property found).
    Properties fields (indices of atoms from 0, in the order of the geometry):
        geometry: Molecule (A); charges: {'mulliken' | 'loewdin' | 'hirshfeld': tuple of floats (e)};
        spins: the same keys, spin populations (open shells); mayer_valence: tuple | None (VA);
        mayer_bonds: ((i, j, order), ...) as printed by ORCA (orders above its threshold, 0.1 by default);
        dipole: (x, y, z) in atomic units (e*bohr) or None; dipole_debye: float | None;
        gradient: ((gx, gy, gz), ...) in hartree/bohr or None.
    DEBYE = 2.541798 D per e*bohr: the factor ORCA uses, verified 2026-10-23 from its own numbers
    (Magnitude (Debye) / Magnitude (a.u.) = 2.5417980 +- 1e-9 in three ORCA 6.0.1 outputs). CODATA
    (e*a0 = 8.4783536e-30 C m, 1 D = 1e-21/c C m) gives 2.5417464, 2e-5 relative less; the program
    shows ORCA's printed Debye value and uses DEBYE only where ORCA printed none.
§5 PROCEDURES - below.
§6 NOTES
    Formats verified 2026-10-23 on 50 real ORCA 5.0.0/5.0.1, 6.0.0/6.0.1 and 6.1 outputs (cclib test data,
    github.com/cclib/cclib, data/ORCA, commit 76df867, BSD-3-Clause; excerpts in tests/data/orca_cclib).
    ASSUMPTION: ORCA 4.x and later versions print the same blocks (not checked).
§7 TESTS
    tests/compass/test_orca_properties.py: values against the files, sums of charges against the total charge,
    sign of the water dipole against the geometry (H side positive), the Mulliken-charge dipole
    sum q_i r_i pointing the same way, Mayer orders against bond types, ownership after an optimization.
§8' ROBUSTNESS
    Unreadable or truncated blocks are skipped rather than guessed; numbers must be finite.
"""

from dataclasses import dataclass, field
from math import isfinite
import re

from azimuth.core import Molecule, read_xyz

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?'
DEBYE = 2.541798  # D per e*bohr as ORCA 5 and 6 convert (see §4; CODATA gives 2.5417464)
GEOMETRY = re.compile(r'CARTESIAN COORDINATES\s*\(ANGSTROE?M\)')
POPULATION = re.compile(r'^(MULLIKEN|LOEWDIN) ATOMIC CHARGES(?: AND SPIN (?:POPULATIONS|DENSITIES))?\s*$', re.M)
ROW = re.compile(r'^\s*(\d+)\s+([A-Z][a-z]?)\s*:\s*(' + NUMBER + r')(?:\s+(' + NUMBER + r'))?\s*$')
BOND = re.compile(r'B\(\s*(\d+)\s*-\s*([A-Z][a-z]?)\s*,\s*(\d+)\s*-\s*([A-Z][a-z]?)\s*\)\s*:\s*(' + NUMBER + r')')


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


@dataclass(frozen=True)
class Properties:
    geometry: Molecule
    charges: dict = field(default_factory=dict)
    spins: dict = field(default_factory=dict)
    mayer_valence: tuple | None = None
    mayer_bonds: tuple = ()
    dipole: tuple | None = None
    dipole_debye: float | None = None
    gradient: tuple | None = None
    bond_kind: str = 'Mayer'  # 'Wiberg' for xtb (the orders are kept in mayer_bonds)
    bond_sets: dict = field(default_factory=dict)  # {'Mayer' | 'Wiberg-Löwdin' | 'Fuzzy' | 'Laplacian': bonds}

    @property
    def empty(self):
        return not (
            self.charges or self.spins or self.mayer_valence or self.mayer_bonds or self.dipole or self.gradient
        )


def _geometries(text):
    """[(end position of the header, Molecule)] of every complete coordinate block."""
    found = []
    for match in GEOMETRY.finditer(text):
        rows = []
        for line in text[match.end() :].splitlines()[1:]:
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
                found.append((match.end(), read_xyz(f'{len(rows)}\nORCA\n' + '\n'.join(rows))))
            except ValueError:
                pass
    return found


def _lines_after(text, position):
    return text[position:].splitlines()


def _atom_rows(lines, symbols, pattern=ROW, skip=3):
    """Values of consecutive atom rows (index, symbol, value, optional second value) after a header."""
    first, second = [], []
    for line in lines:
        m = pattern.match(line)
        if m is None:
            if first:
                break
            if skip <= 0:
                return None
            skip -= 1
            continue
        index = int(m[1])
        if index != len(first) or index >= len(symbols) or m[2] != symbols[index]:
            return None
        first.append(_number(m[3]))
        second.append(_number(m[4]) if m.lastindex >= 4 and m[4] is not None else None)
    if len(first) != len(symbols):
        return None
    return tuple(first), (tuple(second) if all(v is not None for v in second) else None)


def read_properties(text):
    geometries = _geometries(text)
    if not geometries:
        return None
    start, geometry = geometries[-1]
    symbols = [a.symbol for a in geometry.atoms]
    n = len(symbols)
    charges, spins = {}, {}
    try:
        for m in POPULATION.finditer(text, start):
            rows = _atom_rows(_lines_after(text, m.end())[1:], symbols)
            if rows:
                key = m[1].lower()
                charges[key] = rows[0]
                if rows[1] is not None:
                    spins[key] = rows[1]
        for m in re.finditer(r'^HIRSHFELD ANALYSIS\s*$', text[start:], re.M):
            lines = _lines_after(text, start + m.end())
            head = next(
                (k for k, line in enumerate(lines[:20]) if re.match(r'^\s*ATOM\s+CHARGE\s+SPIN\s*$', line)), None
            )
            if head is not None:
                pattern = re.compile(r'^\s*(\d+)\s+([A-Z][a-z]?)\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s*$')
                rows = _atom_rows(lines[head + 1 :], symbols, pattern, skip=0)
                if rows:
                    charges['hirshfeld'] = rows[0]
                    if rows[1] is not None and any(abs(v) > 0 for v in rows[1]):
                        spins['hirshfeld'] = rows[1]
        valence, bonds = None, ()
        for m in re.finditer(r'MAYER POPULATION ANALYSIS', text[start:]):
            lines = _lines_after(text, start + m.end())
            head = next(
                (k for k, line in enumerate(lines[:40]) if re.match(r'^\s*ATOM\s+NA\s+ZA\s+QA\s+VA\s+BVA\s+FA', line)),
                None,
            )
            if head is None:
                continue
            table = re.compile(
                r'^\s*(\d+)\s+([A-Z][a-z]?)\s+('
                + NUMBER
                + r')'
                + r'\s+'
                + NUMBER
                + r'\s+'
                + NUMBER
                + r'\s+('
                + NUMBER
                + r')\s+'
                + NUMBER
                + r'\s+'
                + NUMBER
                + r'\s*$'
            )
            rows = _atom_rows(lines[head + 1 :], symbols, table, skip=0)
            if rows is None:
                continue
            valence = rows[1]
            found = []
            listing = next(
                (k for k, line in enumerate(lines[head : head + n + 6]) if 'Mayer bond orders larger than' in line),
                None,
            )
            if listing is not None:
                for line in lines[head + listing + 1 :]:
                    entries = BOND.findall(line)
                    if not entries:
                        break
                    for i, a, j, b, order in entries:
                        i, j = int(i), int(j)
                        if i < n and j < n and symbols[i] == a and symbols[j] == b:
                            found.append((min(i, j), max(i, j), _number(order)))
            bonds = tuple(found)
        dipole = debye = None
        for m in re.finditer(
            r'Total Dipole Moment\s*:\s*(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')', text[start:]
        ):
            dipole = tuple(_number(v) for v in m.groups())
            after = text[start + m.end() : start + m.end() + 400]
            d = re.search(r'Magnitude \(Debye\)\s*:\s*(' + NUMBER + r')', after)
            debye = _number(d[1]) if d else None
        gradient = None
        for m in re.finditer(r'^CARTESIAN GRADIENT\s*$', text[start:], re.M):
            pattern = re.compile(
                r'^\s*(\d+)\s+([A-Z][a-z]?)\s*:\s*(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s*$'
            )
            rows = []
            for line in _lines_after(text, start + m.end())[1:]:
                g = pattern.match(line)
                if g is None:
                    if rows:
                        break
                    continue
                if int(g[1]) != len(rows) + 1 or len(rows) >= n or g[2] != symbols[len(rows)]:  # 1-based here
                    rows = None
                    break
                rows.append(tuple(_number(v) for v in g.groups()[2:]))
            if rows and len(rows) == n:
                gradient = tuple(rows)
    except ValueError:
        return None
    result = Properties(geometry, charges, spins, valence, bonds, dipole, debye, gradient)
    return None if result.empty else result

"""Read a Q-Chem output (Q-Chem 4.x-6.x) into an Output.

§1 THEORY
    As for ORCA (modules/spectrum/readers/orca.py): energies, geometries, the steps of a geometry optimization, harmonic
    frequencies with normal modes and IR intensities, Mulliken charges and spins, the dipole moment, TD-DFT states.
§2 ALGORITHM
    Banner «Welcome to Q-Chem» / «Q-Chem 5.4, Q-Chem, Inc.»; normal end «Thank you very much for using Q-Chem»;
    geometry blocks «Standard Nuclear Orientation (Angstroms)» (rows «I Atom X Y Z»); SCF energy «Total energy in
    the final basis set =»; correlated energies «<method> total energy = E», «<method> energy = E» and «EMP4 =»
    (MP2, RI-MP2, MP3, MP4, MP4SDQ, CCD, CCSD, CCSD(T), QCISD…) — the last of them is the final energy. Optimization:
    «Energy is E» of the optimizer after
    every cycle with the last orientation block before it; converged with «OPTIMIZATION CONVERGED», the final
    geometry is the «Coordinates (Angstroms)» block after it. Frequencies («VIBRATIONAL ANALYSIS»): blocks «Mode:»
    «Frequency:» (an imaginary one is printed negative) «IR Intens:» (km/mol), then one row «symbol x y z …» per
    atom; the geometry is the last orientation block before the analysis. Mulliken: the last «Ground-State
    Mulliken Net Atomic Charges» (a second column «Spin (a.u.)» for an open shell). Dipole: the last «Dipole Moment
    (Debye)» X Y Z Tot. TD-DFT/CIS: the last «… Excitation Energies» block, «Excited state n: excitation energy
    (eV) = E», «Multiplicity:», «Strength :».
§3 APPLICATIONS
    modules/spectrum/readers/outputs.py.
§4 SPECIFICATION
    is_qchem(text) -> bool; read_qchem(text) -> orca.Output with program 'Q-Chem <version>' and final_energy.
§5 PROCEDURES - below.
§6 NOTES
    Verified 2026-10-26 on the Q-Chem 5.4 outputs of the cclib test data (data/QChem/basicQChem5.4, BSD-3-Clause;
    in tests/data/qchem).
§7 TESTS
    tests/spectrum/test_qchem.py.
§8' ROBUSTNESS
    Blocks that do not parse are skipped; a frequency block must have one row per atom.
"""

from dataclasses import replace
from math import isfinite
import re

from modules.spectrum.readers.nwchem import AU_DEBYE, element
from modules.spectrum.readers.results import NUMBER, OptimizationStep, Output
from modules.spectrum.readers.orca_properties import Properties
from azimuth.core import Atom, Molecule

ORIENTATION = re.compile(r'Standard Nuclear Orientation \((Angstroms|Bohr)\)\s*\n')
METHODS = {'RIMP2': 'MP2', 'RI-MP2': 'MP2', 'SOSMP2': 'SOS-MP2', 'SCSMP2': 'SCS-MP2'}


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


def is_qchem(text):
    head = text[:20000]
    return 'Welcome to Q-Chem' in head or bool(re.search(r'Q-Chem \d+\.\d+.*Q-Chem, Inc\.', head))


def _rows(text, start, factor=1.0, columns=5):
    """Atoms of the rows «n symbol x y z» after start (headers and rules skipped)."""
    rows = []
    for line in text[start:start + 400000].splitlines():
        f = line.split()
        if not rows and (not f or f[0] in ('I', 'ATOM') or set(line.strip()) <= {'-', ' '}):
            continue
        if len(f) == columns and f[0].isdigit():
            try:
                rows.append(Atom(element(f[1]), *(_number(v) * factor for v in f[2:5])))
            except ValueError:
                return []
            continue
        break
    return rows


def _geometries(text):
    found = []
    for match in ORIENTATION.finditer(text):
        from modules.compass.chemistry.geometry_tools import BOHR

        rows = _rows(text, match.end(), BOHR if match[1] == 'Bohr' else 1.0)
        if rows:
            found.append((match.start(), Molecule('Q-Chem', tuple(rows))))
    return found


def _final_energy(text):
    found = []
    for m in re.finditer(r'^\s*E?([A-Za-z0-9()\-]+)\s+(?:total energy|energy)?\s*=\s*(' + NUMBER + ')', text, re.M):
        label = METHODS.get(m[1], m[1])
        if re.fullmatch(r'(?:SOS-|SCS-)?MP[234]|MP4SDQ|CCD|CCSD|CCSD\(T\)|QCISD|QCISD\(T\)|CISD|OO-RI-MP2|OD|QCCD', label):
            found.append((m.start(), label, _number(m[2])))
    if not found:
        return None
    _, label, value = max(found)
    return label, value


def _frequencies(text, natoms):
    from modules.spectrum.readers.vibration_data import Vibration

    start = text.rfind('VIBRATIONAL ANALYSIS')
    if start < 0 or natoms == 0:
        return (), ()
    section = text[start:]
    lines = section.splitlines()
    modes = []
    k = 0
    while k < len(lines):
        f = lines[k].split()
        if f[:1] == ['Mode:'] and all(x.isdigit() for x in f[1:]):
            numbers = [int(x) for x in f[1:]]
            values = {}
            j = k + 1
            while j < len(lines) and not lines[j].strip().startswith('X'):
                row = lines[j].split(':')
                if len(row) == 2:
                    values[row[0].strip()] = row[1].split()
                j += 1
            rows = lines[j + 1:j + 1 + natoms]
            vectors = {n: [] for n in numbers}
            ok = len(rows) == natoms
            for row in rows:
                parts = row.split()
                if len(parts) != 1 + 3 * len(numbers):
                    ok = False
                    break
                for c, n in enumerate(numbers):
                    vectors[n].append(tuple(_number(v) for v in parts[1 + 3 * c:4 + 3 * c]))
            try:
                freqs = [_number(v) for v in values.get('Frequency', [])]
                ir = [_number(v) for v in values.get('IR Intens', [])]
            except ValueError:
                freqs, ir = [], []
            if len(freqs) == len(numbers):
                for c, n in enumerate(numbers):
                    modes.append(Vibration(n, freqs[c], tuple(vectors[n]) if ok else None,
                                           ir[c] if len(ir) == len(numbers) else None))
            k = j + 1 + natoms
            continue
        if lines[k].strip().startswith('STANDARD THERMODYNAMIC QUANTITIES'):
            break
        k += 1
    modes = tuple(modes)
    return tuple((m.index, m.frequency) for m in modes), modes


def _properties(text, geometry):
    if geometry is None:
        return None
    charges, spins = {}, {}
    blocks = list(re.finditer(r'Ground-State Mulliken Net Atomic Charges\s*\n', text))
    if blocks:
        values = []
        for line in text[blocks[-1].end():].splitlines():
            f = line.split()
            if not f or f[0] == 'Atom' or set(line.strip()) <= {'-'}:
                if values and (not f or set(line.strip()) <= {'-'}):
                    break
                continue
            if len(f) not in (3, 4) or not f[0].isdigit():
                break
            values.append((_number(f[2]), _number(f[3]) if len(f) == 4 else None))
        if len(values) == len(geometry.atoms):
            charges['mulliken'] = tuple(v[0] for v in values)
            if all(v[1] is not None for v in values) and any(v[1] for v in values):
                spins['mulliken'] = tuple(v[1] for v in values)
    dipole = dipole_debye = None
    found = list(re.finditer(
        r'Dipole Moment \(Debye\)\s*\n\s*X\s+(' + NUMBER + r')\s+Y\s+(' + NUMBER + r')\s+Z\s+(' + NUMBER + r')\s*\n\s*Tot\s+(' + NUMBER + ')',
        text))
    if found:
        m = found[-1]
        dipole = tuple(_number(m[i]) / AU_DEBYE for i in (1, 2, 3))
        dipole_debye = _number(m[4])
    props = Properties(geometry, charges, spins, None, (), dipole, dipole_debye, None)
    return None if props.empty else props


def _excitations(text):
    from modules.spectrum.readers.orca_spectra import EV_CM, Excitation

    heads = list(re.finditer(r'Excitation Energies\s*\n\s*-+\s*\n', text))
    if not heads:
        return ()
    body = text[heads[-1].end():]
    found = []
    states = list(re.finditer(r'Excited state\s+(\d+): excitation energy \(eV\)\s*=\s*(' + NUMBER + ')', body))
    for k, m in enumerate(states):
        if k and int(m[1]) <= int(states[k - 1][1]):
            break  # the next table
        nxt = states[k + 1].start() if k + 1 < len(states) else min(len(body), m.end() + 3000)
        part = body[m.end():nxt]
        mult = re.search(r'Multiplicity:\s*(\w+)', part)
        strength = re.search(r'Strength\s*:\s*(' + NUMBER + ')', part)
        ev = _number(m[2])
        if not (isfinite(ev) and ev > 0):
            continue
        name = mult[1] if mult else ''
        multiplicity = {'Singlet': 1, 'Doublet': 2, 'Triplet': 3, 'Quartet': 4}.get(name)
        cm = ev * EV_CM
        found.append(Excitation(int(m[1]), name.lower(), ev, cm, 1e7 / cm,
                                max(0.0, _number(strength[1])) if strength else 0.0, multiplicity))
    return tuple(found)


def read_qchem(text):
    if not is_qchem(text):
        raise ValueError('not a Q-Chem output')
    version = re.search(r'Q-Chem (\d+\.\d+(?:\.\d+)?)', text[:20000])
    program = f'Q-Chem {version[1]}' if version else 'Q-Chem'
    geometries = _geometries(text)
    energies = [(m.start(), _number(m[1])) for m in re.finditer(r'Total energy in the final basis set\s*=\s*(' + NUMBER + ')', text)]
    converged_at = text.rfind('OPTIMIZATION CONVERGED')
    steps = []
    for m in re.finditer(r'^\s*Energy is\s+(' + NUMBER + ')', text, re.M):
        before = [g for p, g in geometries if p < m.start()]
        if before:
            k = len(steps) + 1
            steps.append(OptimizationStep(k, _number(m[1]), replace(before[-1], title=f'Q-Chem · шаг {k}')))
    geometry = None
    if converged_at >= 0:
        block = re.search(r'Coordinates \(Angstroms\)\s*\n', text[converged_at:])
        rows = _rows(text, converged_at + block.end()) if block else []
        geometry = Molecule('Q-Chem', tuple(rows)) if rows else None
    if geometry is None and geometries:
        geometry = geometries[-1][1]
    if not energies and geometry is None:
        raise ValueError('no recognizable section of a Q-Chem output')
    start = text.rfind('VIBRATIONAL ANALYSIS')
    vibration_geometry = None
    if start >= 0:
        before = [g for p, g in geometries if p < start]
        vibration_geometry = before[-1] if before else geometry
    frequencies, modes = _frequencies(text, len(vibration_geometry.atoms) if vibration_geometry else 0)
    normal = 'Thank you very much for using Q-Chem' in text
    error = 'Q-Chem' if not normal and re.search(r'Q-Chem fatal error|fatal error occurred', text) else None
    return Output(
        normal,
        converged_at >= 0,
        bool(re.search(r'SCF failed to converge|Convergence failure', text)),
        tuple(e for _, e in energies),
        frequencies,
        replace(geometry, title=program) if geometry else None,
        False,
        tuple(steps) if len(steps) > 1 else (),
        replace(vibration_geometry, title=program) if frequencies and vibration_geometry else None,
        modes,
        error,
        False,
        geometries[0][1] if geometries else None,
        _properties(text, geometry),
        None,
        _excitations(text),
        (),
        program,
        _final_energy(text),
    )

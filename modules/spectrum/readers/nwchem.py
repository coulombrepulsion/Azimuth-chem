"""Read an NWChem output (NWChem 6.x-7.x) into an Output.

§1 THEORY
    As for ORCA (modules/spectrum/readers/orca.py): energies, geometries, the steps of a geometry optimization, harmonic
    frequencies with normal modes and IR intensities, Mulliken charges, the dipole moment, TD-DFT states.
§2 ALGORITHM
    Banner «Northwest Computational Chemistry Package (NWChem) 7.0.0»; normal end «Total times cpu:»; geometry
    blocks «Output coordinates in angstroms|a.u.», rows «No. Tag Charge X Y Z» (the element from the tag, else
    from the nuclear charge). Energies «Total DFT energy =» / «Total SCF energy =»; correlated ones «Total MP2
    energy», «Total SCS-MP2 energy» is not taken, «CCSD total energy / hartree», «CCSD(T) total energy / hartree»
    (TCE) and «Total CCSD energy:» / «Total CCSD(T) energy:» (the CCSD module) — the last of them is the final
    energy. Optimization (DRIVER): the rows «@ Step Energy …» / «@ k E …» give the energy of each step and the
    geometry is the last geometry block before that row; converged with «Optimization converged», the final
    geometry is the block after it. Frequencies (the last «NORMAL MODE EIGENVECTORS IN CARTESIAN COORDINATES»
    block, projected when there are both): columns «P.Frequency» (or «Frequency»), one row per Cartesian
    coordinate (3N); IR intensities in km/mol from the last «Infra Red Intensities» table; the modes of
    translation and rotation (|ν| < 0.5 cm⁻¹, printed 0.00) are left out, the others keep their printed numbers.
    Mulliken: the last «Total gross population on atoms» block (SCF) — charge = nuclear charge of the row − population;
    else the last «Total Density - Mulliken Population Analysis» of DFT with «mulliken» (two decimals).
    Dipole: the last «Multipole analysis of the density», rows L = 1, the «total» column in a.u. TD-DFT: «Root n
    singlet|triplet <irrep> E a.u. E eV» with «Total Oscillator Strength» (older: «Oscillator Strength») below.
    NMR («property shielding»): the last «Chemical Shielding Tensors (GIAO, in ppm)» — «Atom: n X», «isotropic =»,
    «anisotropy =» (verified on NWChem 7.3.0: water B3LYP-D3(BJ)/def2-SVP, O 337.3, H 31.3 ppm; ORCA 337.4, 31.3).
§3 APPLICATIONS
    modules/spectrum/readers/outputs.py.
§4 SPECIFICATION
    is_nwchem(text) -> bool; read_nwchem(text) -> orca.Output with program 'NWChem <version>' and final_energy.
§5 PROCEDURES - below.
§6 NOTES
    Verified 2026-10-26 on the NWChem 7.0 outputs of the cclib test data (data/NWChem/basicNWChem7.0, BSD-3-Clause;
    in tests/data/nwchem). AU_DEBYE = 2.541746473 (CODATA 2018: e·a0 in debye).
§7 TESTS
    tests/spectrum/test_nwchem.py.
§8' ROBUSTNESS
    Blocks that do not parse are skipped; the frequency table must have 3N rows.
"""

from dataclasses import replace
from math import isfinite, sqrt
import re

from modules.spectrum.readers.results import NUMBER, OptimizationStep, Output
from modules.spectrum.readers.orca_properties import Properties
from azimuth.core import Atom, Molecule, SYMBOLS
from modules.compass.chemistry.geometry_tools import BOHR

AU_DEBYE = 2.541746473
GEOMETRY = re.compile(r'Output coordinates in (angstroms|a\.u\.)[^\n]*\n')


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


def element(tag, charge=None):
    """The element of a tag («C», «C1», «Cl2», «carbon») checked against the nuclear charge when it is a whole
    number; else the element of that charge; with a reduced (ECP) charge the tag alone."""
    name = re.sub(r'[^A-Za-z]', '', tag)
    z = round(charge) if charge is not None and charge > 0 and abs(charge - round(charge)) < 1e-6 else None
    candidates = [c for c in (name[:2].capitalize(), name[:1].upper()) if c in SYMBOLS]
    for cand in candidates:
        if z is None or SYMBOLS.index(cand) + 1 == z:
            return cand
    if z is not None and z <= len(SYMBOLS):
        return SYMBOLS[z - 1]
    if candidates:
        return candidates[0]
    raise ValueError(f'unknown element {tag}')


def is_nwchem(text):
    return 'Northwest Computational Chemistry Package (NWChem)' in text[:20000]


def _geometries(text):
    found = []
    for match in GEOMETRY.finditer(text):
        factor = BOHR if match[1] == 'a.u.' else 1.0
        rows = []
        lines = text[match.end():match.end() + 400000].splitlines()
        started = False
        for line in lines:
            f = line.split()
            if not started and (not f or f[0] == 'No.' or set(line.strip()) <= {'-', ' '}):
                continue
            if len(f) == 6 and f[0].isdigit():
                try:
                    charge = _number(f[2])
                    if charge == 0 and f[1].lower().startswith('bq'):
                        continue  # a ghost centre
                    rows.append(Atom(element(f[1], charge), *(_number(v) * factor for v in f[3:6])))
                except ValueError:
                    rows = []
                    break
                started = True
                continue
            break
        if rows:
            found.append((match.start(), Molecule('NWChem', tuple(rows))))
    return found


def _energies(text):
    return [(m.start(), _number(m[1])) for m in re.finditer(r'Total (?:DFT|SCF) energy\s*=\s*(' + NUMBER + ')', text)]


def _final_energy(text):
    patterns = (
        ('MP2', r'Total MP2 energy\s+(' + NUMBER + ')'),
        ('CCSD', r'CCSD total energy / hartree\s*=\s*(' + NUMBER + ')'),
        ('CCSD(T)', r'CCSD\(T\) total energy / hartree\s*=\s*(' + NUMBER + ')'),
        ('CCSD', r'Total CCSD energy:\s*(' + NUMBER + ')'),
        ('CCSD(T)', r'Total CCSD\(T\) energy:\s*(' + NUMBER + ')'),
    )
    found = [(m.start(), label, _number(m[1])) for label, rx in patterns for m in re.finditer(rx, text)]
    if not found:
        return None
    _, label, value = max(found)
    return label, value


def _steps(text, geometries):
    rows = [(m.start(), int(m[1]), _number(m[2])) for m in re.finditer(r'^@\s+(\d+)\s+(' + NUMBER + r')\s', text, re.M)]
    steps, seen = [], set()
    for position, number, energy in rows:
        if number in seen:
            continue  # the last row is printed again after «Optimization converged»
        before = [g for p, g in geometries if p < position]
        if not before:
            continue
        seen.add(number)
        k = len(steps) + 1
        steps.append(OptimizationStep(k, energy, replace(before[-1], title=f'NWChem · шаг {k}')))
    return tuple(steps)


def _frequencies(text, natoms):
    from modules.spectrum.readers.vibration_data import Vibration

    start = text.rfind('NORMAL MODE EIGENVECTORS IN CARTESIAN COORDINATES')
    if start < 0 or natoms == 0:
        return (), ()
    section = text[start:]
    end = section.find('Normal Eigenvalue')
    section = section[:end] if end > 0 else section
    lines = section.splitlines()
    modes = {}
    k = 0
    while k < len(lines):
        f = lines[k].split()
        if f and all(x.isdigit() for x in f) and k + 2 < len(lines):
            numbers = [int(x) for x in f]
            j = k + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            head = lines[j].split() if j < len(lines) else []
            if not head or head[0] not in ('P.Frequency', 'Frequency'):
                k += 1
                continue
            freqs = [_number(v) for v in head[1:]]
            j += 1
            columns = [[] for _ in numbers]
            while j < len(lines) and len(columns[0]) < 3 * natoms:
                row = lines[j].split()
                j += 1
                if not row:
                    continue
                if len(row) != len(numbers) + 1 or not row[0].isdigit():
                    break
                for c in range(len(numbers)):
                    columns[c].append(_number(row[c + 1]))
            if len(freqs) == len(numbers):
                for c, n in enumerate(numbers):
                    vec = columns[c]
                    vectors = tuple(tuple(vec[3 * a:3 * a + 3]) for a in range(natoms)) if len(vec) == 3 * natoms else None
                    modes[n] = (freqs[c], vectors)
            k = j
            continue
        k += 1
    ir = {}
    tables = list(re.finditer(r'Infra Red Intensities\s*\n.*\n\s*-+[- |]*\n', text))
    if tables:
        for line in text[tables[-1].end():].splitlines():
            f = line.replace('||', ' ').split()
            if len(f) < 6 or not f[0].isdigit():
                break
            ir[int(f[0])] = _number(f[4])
    kept = [n for n in sorted(modes) if abs(modes[n][0]) >= 0.5]
    vibrations = tuple(Vibration(n, modes[n][0], modes[n][1], ir.get(n)) for n in kept)
    return tuple((v.index, v.frequency) for v in vibrations), vibrations


def _properties(text, geometry):
    if geometry is None:
        return None
    charges = {}
    blocks = list(re.finditer(r'-+\s*Total\s+gross population on atoms\s*-+\s*\n', text))
    if blocks:
        values = []
        for line in text[blocks[-1].end():].splitlines():
            f = line.split()
            if not f:
                if values:
                    break
                continue
            if len(f) != 4 or not f[0].isdigit():
                break
            values.append(_number(f[2]) - _number(f[3]))
        if len(values) == len(geometry.atoms):
            charges['mulliken'] = tuple(values)
    density = list(re.finditer(r'Total Density - Mulliken Population Analysis\s*\n\s*-+\s*\n', text))
    if 'mulliken' not in charges and density:  # DFT with «mulliken»: «1 C 6 5.84 shells…», two decimals
        values = []
        for line in text[density[-1].end():].splitlines():
            f = line.split()
            if not f or set(line.strip()) <= {'-', ' '} or f[0] == 'Atom':
                if values:
                    break
                continue
            if len(f) < 4 or not f[0].isdigit() or not f[2].isdigit():
                break
            values.append(int(f[2]) - _number(f[3]))
        if len(values) == len(geometry.atoms):
            charges['mulliken'] = tuple(values)
    dipole = dipole_debye = None
    multipoles = list(re.finditer(r'Multipole analysis of the density\s*\n', text))
    if multipoles:
        values = {}
        for m in re.finditer(r'^\s*1\s+([01])\s+([01])\s+([01])\s+(' + NUMBER + ')', text[multipoles[-1].end():][:4000], re.M):
            axis = (m[1], m[2], m[3]).index('1')
            values.setdefault(axis, _number(m[4]))
        if len(values) == 3:
            dipole = tuple(values[k] for k in range(3))
            dipole_debye = sqrt(sum(v * v for v in dipole)) * AU_DEBYE
    props = Properties(geometry, charges, {}, None, (), dipole, dipole_debye, None)
    return None if props.empty else props


def _excitations(text):
    from modules.spectrum.readers.orca_spectra import EV_CM, Excitation

    found = []
    roots = list(re.finditer(r'Root\s+(\d+)\s+(singlet|triplet)?\s*(\S*)\s+(' + NUMBER + r')\s+a\.u\.\s+(' + NUMBER + r')\s+eV', text))
    for k, m in enumerate(roots):
        nxt = roots[k + 1].start() if k + 1 < len(roots) else len(text)
        body = text[m.end():min(nxt, m.end() + 3000)]
        strength = re.search(r'(?:Total |Dipole )?Oscillator Strength\s+(' + NUMBER + ')', body)
        total = re.search(r'Total Oscillator Strength\s+(' + NUMBER + ')', body)
        ev = _number(m[5])
        if not (isfinite(ev) and ev > 0):
            continue
        fosc = _number(total[1]) if total else (_number(strength[1]) if strength else 0.0)
        multiplicity = {'singlet': 1, 'triplet': 3}.get(m[2] or '')
        label = ' '.join(x for x in (m[2], m[3]) if x)
        cm = ev * EV_CM
        found.append(Excitation(int(m[1]), label, ev, cm, 1e7 / cm, max(0.0, fosc), multiplicity))
    numbers = [e.state for e in found]
    if numbers and len(set(numbers)) != len(numbers):  # several TD-DFT runs: the last one
        last = max(i for i, e in enumerate(found) if e.state == found[0].state)
        found = found[last:]
    return tuple(found)


def _shieldings(text):
    """The GIAO shieldings of «property … shielding»: the last «Chemical Shielding Tensors (GIAO, in ppm)», each
    «Atom:   n  X» with its «isotropic =» and «anisotropy =» (ppm)."""
    from modules.spectrum.readers.orca_spectra import Shielding

    starts = [m.end() for m in re.finditer(r'Chemical Shielding Tensors \(GIAO, in ppm\)', text)]
    if not starts:
        return ()
    found = []
    for m in re.finditer(r'^\s*Atom:\s+(\d+)\s+([A-Za-z]{1,2})\s*$(.*?)isotropic =\s*(' + NUMBER + r')\s+anisotropy =\s*('
                         + NUMBER + ')', text[starts[-1]:], re.M | re.S):
        if 'Atom:' in m[3]:  # an atom without its numbers: not paired with the next one
            continue
        found.append(Shielding(int(m[1]) - 1, element(m[2]), _number(m[4]), _number(m[5])))
    return tuple(found)


def read_nwchem(text):
    if not is_nwchem(text):
        raise ValueError('not an NWChem output')
    version = re.search(r'\(NWChem\)\s+(\d+\.\d+(?:\.\d+)?)', text[:20000])
    program = f'NWChem {version[1]}' if version else 'NWChem'
    geometries = _geometries(text)
    energies = _energies(text)
    converged_at = text.rfind('Optimization converged')
    optimization = bool(re.search(r'^@ Step\s+Energy', text, re.M))
    steps = _steps(text, geometries) if optimization else ()
    geometry = None
    if converged_at >= 0:
        after = [g for p, g in geometries if p > converged_at]
        geometry = after[0] if after else None
    if geometry is None and geometries:
        geometry = geometries[-1][1]
    if not energies and geometry is None:
        raise ValueError('no recognizable section of an NWChem output')
    natoms = len(geometry.atoms) if geometry else 0
    start = text.rfind('NORMAL MODE EIGENVECTORS IN CARTESIAN COORDINATES')
    vibration_geometry = None
    if start >= 0:
        before = [g for p, g in geometries if p < start]
        vibration_geometry = before[-1] if before else geometry
        natoms = len(vibration_geometry.atoms) if vibration_geometry else natoms
    frequencies, modes = _frequencies(text, natoms)
    normal = bool(re.search(r'^\s*Total times\s+cpu:', text, re.M))
    error = None
    if not normal and re.search(r'There is an error in the input file|^\s*[A-Za-z_]+:.*\berror\b|ERROR', text[-20000:], re.M):
        error = 'NWChem'
    return Output(
        normal,
        converged_at >= 0,
        bool(re.search(r'Calculation failed to converge|SCF failed to converge', text)),
        tuple(e for _, e in energies),
        frequencies,
        replace(geometry, title=program) if geometry else None,
        False,
        steps if len(steps) > 1 else (),
        replace(vibration_geometry, title=program) if frequencies and vibration_geometry else None,
        modes,
        error,
        False,
        geometries[0][1] if geometries else None,
        _properties(text, geometry),
        None,
        _excitations(text),
        _shieldings(text),
        program,
        _final_energy(text),
    )

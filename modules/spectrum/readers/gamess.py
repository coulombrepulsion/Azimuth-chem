"""Read a GAMESS (US) or Firefly output into an Output.

§1 THEORY
    As for ORCA (modules/spectrum/readers/orca.py): energies, geometries, the steps of a geometry optimization, harmonic
    frequencies with normal modes and IR intensities, Mulliken charges, the dipole moment, TD-DFT states.
§2 ALGORITHM Banner «GAMESS VERSION = 20 APR 2017 (R1)» or «Firefly version 8.0.1»; normal end «EXECUTION OF
    GAMESS|FIREFLY TERMINATED NORMALLY» (abnormal: «TERMINATED -ABNORMALLY-»). Geometry blocks «COORDINATES OF ALL ATOMS
    ARE (ANGS)» and the input geometry «ATOM ATOMIC COORDINATES (BOHR)», rows «name charge x y z» (the element from the
    name checked against the charge, else from the charge). Energies «FINAL <method> ENERGY IS E AFTER n ITERATIONS»
    (Firefly: «FINAL ENERGY IS»); correlated ones «E(MP2)= E», «CCSD ENERGY: E», «CCSD(T) ENERGY: E», «CCD ENERGY: E» —
    the last of them is the final energy. Optimization: «NSERCH: k E= E» (or «NSERCH= k ENERGY= E», Firefly) with the
    last geometry block before it; converged with «EQUILIBRIUM GEOMETRY LOCATED», the final geometry is the next
    «COORDINATES OF ALL ATOMS» block. Frequencies (the last «NORMAL COORDINATE ANALYSIS»): columns of mode numbers,
    «FREQUENCY:» (a following «I» marks an imaginary one: negative), «IR INTENSITY:» in D²/(amu·Å²) × IR_KM = km/mol,
    three rows X Y Z per atom; the modes «MODES i TO j ARE TAKEN AS ROTATIONS AND TRANSLATIONS» are left out. Mulliken:
    the last «TOTAL MULLIKEN AND LOWDIN ATOMIC POPULATIONS» (rows with the charge). Dipole: the last «ELECTROSTATIC
    MOMENTS», «DX DY DZ /D/ (DEBYE)». TD-DFT: «SUMMARY OF TDDFT RESULTS» rows «n irrep E(hartree) ΔE(eV) x y z f».
§3 APPLICATIONS
    modules/spectrum/readers/outputs.py.
§4 SPECIFICATION
    is_gamess(text) -> bool; read_gamess(text) -> orca.Output with program 'GAMESS (US) <date>' or 'Firefly
    <version>' and final_energy. IR_KM = 42.2561 km/mol per D²/(amu·Å²).
§5 PROCEDURES - below.
§6 NOTES
    Verified 2026-10-26 on the GAMESS (US) 2017 and Firefly 8.0 outputs of the cclib test data (data/GAMESS,
    BSD-3-Clause; in tests/data/gamess). IR_KM: 1 D²/(amu·Å²) = 42.2561 km/mol (the factor of GAMESS itself and
    of cclib).
§7 TESTS
    tests/spectrum/test_gamess.py.
§8' ROBUSTNESS
    Blocks that do not parse are skipped; a frequency block must have 3 rows per atom.
"""

from dataclasses import replace
from math import isfinite
import re

from modules.spectrum.readers.nwchem import AU_DEBYE, element
from modules.spectrum.readers.results import NUMBER, OptimizationStep, Output
from modules.spectrum.readers.orca_properties import Properties
from azimuth.core import Atom, Molecule
from modules.compass.chemistry.geometry_tools import BOHR

IR_KM = 42.2561
BLOCKS = re.compile(r'COORDINATES OF ALL ATOMS ARE \(ANGS\)\s*\n|ATOM\s+ATOMIC\s+COORDINATES \(BOHR\)\s*\n')


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


def is_gamess(text):
    head = text[:20000]
    return 'GAMESS VERSION =' in head or 'Firefly version' in head or 'PC GAMESS version' in head


def _geometries(text):
    found = []
    for match in BLOCKS.finditer(text):
        factor = BOHR if 'BOHR' in match[0] else 1.0
        rows = []
        for line in text[match.end():match.end() + 400000].splitlines():
            f = line.split()
            if not rows and (not f or f[0] in ('ATOM', 'CHARGE') or set(line.strip()) <= {'-', ' '}):
                continue
            if len(f) == 5:
                try:
                    charge = _number(f[1])
                    rows.append(Atom(element(f[0], charge), *(_number(v) * factor for v in f[2:5])))
                except ValueError:
                    rows = []
                    break
                continue
            break
        if rows:
            found.append((match.start(), Molecule('GAMESS', tuple(rows))))
    return found


def _final_energy(text):
    patterns = (
        ('MP2', r'E\(MP2\)\s*=\s*(' + NUMBER + ')'),
        ('CCD', r'^\s*CCD\s+ENERGY:\s*(' + NUMBER + ')'),
        ('CCSD', r'^\s*CCSD\s+ENERGY:\s*(' + NUMBER + ')'),
        ('CCSD(T)', r'^\s*CCSD\(T\)\s+ENERGY:\s*(' + NUMBER + ')'),
    )
    found = [(m.start(), label, _number(m[1])) for label, rx in patterns for m in re.finditer(rx, text, re.M)]
    if not found:
        return None
    _, label, value = max(found)
    return label, value


def _values(line):
    """Numbers after «LABEL:»; an «I» after a number makes it negative (an imaginary frequency)."""
    out = []
    for token in line.split(':', 1)[1].split():
        if token == 'I' and out:
            out[-1] = -out[-1]
        else:
            out.append(_number(token))
    return out


def _frequencies(text, natoms):
    from modules.spectrum.readers.vibration_data import Vibration

    start = text.rfind('NORMAL COORDINATE ANALYSIS IN THE HARMONIC APPROXIMATION')
    if start < 0 or natoms == 0:
        return (), ()
    section = text[start:]
    for stop in ('END OF NORMAL COORDINATE ANALYSIS', 'THERMOCHEMISTRY AT T='):
        end = section.find(stop)
        if end > 0:
            section = section[:end]
    skip = set()
    tr = re.search(r'MODES\s+(\d+)\s+TO\s+(\d+)\s+ARE TAKEN AS ROTATIONS AND TRANSLATIONS', section)
    if tr:
        skip = set(range(int(tr[1]), int(tr[2]) + 1))
    lines = section.splitlines()
    modes = {}
    k = 0
    while k < len(lines):
        f = lines[k].split()
        if f and all(x.isdigit() for x in f) and k + 1 < len(lines) and 'FREQUENCY:' in lines[k + 1]:
            numbers = [int(x) for x in f]
            values = {}
            j = k + 1
            while j < len(lines) and lines[j].strip() and ':' in lines[j]:
                label = lines[j].split(':', 1)[0].strip()
                try:
                    values[label] = _values(lines[j]) if label in ('FREQUENCY', 'IR INTENSITY') else None
                except ValueError:
                    values[label] = None
                j += 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            columns = [[] for _ in numbers]
            ok = True
            for a in range(natoms):
                for axis in range(3):
                    if j >= len(lines):
                        ok = False
                        break
                    parts = lines[j].split()
                    j += 1
                    tail = parts[-len(numbers):] if len(parts) >= len(numbers) + 1 else []
                    if not tail or parts[-len(numbers) - 1] != 'XYZ'[axis]:
                        ok = False
                        break
                    for c in range(len(numbers)):
                        columns[c].append(_number(tail[c]))
                if not ok:
                    break
            freqs = values.get('FREQUENCY') or []
            ir = values.get('IR INTENSITY') or []
            if len(freqs) == len(numbers):
                for c, n in enumerate(numbers):
                    vec = columns[c]
                    vectors = tuple(tuple(vec[3 * a:3 * a + 3]) for a in range(natoms)) if ok else None
                    modes[n] = Vibration(n, freqs[c], vectors, ir[c] * IR_KM if len(ir) == len(numbers) else None)
            k = j
            continue
        k += 1
    kept = tuple(modes[n] for n in sorted(modes) if n not in skip)
    return tuple((m.index, m.frequency) for m in kept), kept


def _properties(text, geometry):
    if geometry is None:
        return None
    charges = {}
    blocks = list(re.finditer(r'TOTAL MULLIKEN AND LOWDIN ATOMIC POPULATIONS\s*\n.*\n', text))
    if blocks:
        values = []
        for line in text[blocks[-1].end():].splitlines():
            f = line.split()
            if len(f) == 4 and f[0].isdigit():
                continue  # an open shell prints the populations first without the charge
            if len(f) != 6 or not f[0].isdigit():
                break
            values.append(_number(f[3]))
        if len(values) == len(geometry.atoms):
            charges['mulliken'] = tuple(values)
    dipole = dipole_debye = None
    found = list(re.finditer(r'DX\s+DY\s+DZ\s+/D/\s+\(DEBYE\)\s*\n\s*(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + ')', text))
    if found:
        m = found[-1]
        dipole = tuple(_number(m[i]) / AU_DEBYE for i in (1, 2, 3))
        dipole_debye = _number(m[4])
    props = Properties(geometry, charges, {}, None, (), dipole, dipole_debye, None)
    return None if props.empty else props


def _excitations(text):
    from modules.spectrum.readers.orca_spectra import EV_CM, Excitation

    start = text.rfind('SUMMARY OF TDDFT RESULTS')
    if start < 0:
        return ()
    found = []
    rows = text[start:start + 200000].splitlines()[1:]
    began = False
    for line in rows:
        f = line.split()
        if len(f) == 8 and f[0].isdigit():
            began = True
            try:
                ev, fosc = _number(f[3]), _number(f[7])
            except ValueError:
                continue
            if ev > 0:
                cm = ev * EV_CM
                found.append(Excitation(int(f[0]), f[1].lower(), ev, cm, 1e7 / cm, max(0.0, fosc)))
        elif began and not (len(f) == 4 and f[0] == '0'):
            break
    return tuple(found)


def read_gamess(text):
    if not is_gamess(text):
        raise ValueError('not a GAMESS output')
    firefly = re.search(r'Firefly version\s+(\S+)', text[:20000])
    us = re.search(r'GAMESS VERSION =\s*(.*?)\s*\*', text[:20000])
    program = f'Firefly {firefly[1].rstrip(",")}' if firefly else (f'GAMESS (US) {us[1]}' if us else 'GAMESS')
    geometries = _geometries(text)
    energies = [(m.start(), _number(m[1])) for m in re.finditer(r'FINAL (?:\S+ )?ENERGY IS\s+(' + NUMBER + ')', text)]
    converged_at = text.rfind('EQUILIBRIUM GEOMETRY LOCATED')
    found = {}  # NSERCH -> (position, energy): «NSERCH: k E= …» (10 decimals) over «NSERCH= k ENERGY= …» (Firefly)
    for rx in (r'NSERCH=\s*(\d+)\s+ENERGY=\s*(' + NUMBER + ')', r'NSERCH:\s*(\d+)\s+E=\s*(' + NUMBER + ')'):
        for m in re.finditer(rx, text):
            place = found[int(m[1])][0] if int(m[1]) in found else m.start()
            found[int(m[1])] = (place, _number(m[2]))
    steps = []
    for number in sorted(found):
        place, energy = found[number]
        before = [g for p, g in geometries if p < place]
        if before:
            k = len(steps) + 1
            steps.append(OptimizationStep(k, energy, replace(before[-1], title=f'GAMESS · шаг {k}')))
    geometry = None
    if converged_at >= 0:
        after = [g for p, g in geometries if p > converged_at]
        geometry = after[0] if after else None
    if geometry is None and geometries:
        geometry = geometries[-1][1]
    if not energies and geometry is None:
        raise ValueError('no recognizable section of a GAMESS output')
    start = text.rfind('NORMAL COORDINATE ANALYSIS IN THE HARMONIC APPROXIMATION')
    vibration_geometry = None
    if start >= 0:
        before = [g for p, g in geometries if p < start]
        vibration_geometry = before[-1] if before else geometry
    frequencies, modes = _frequencies(text, len(vibration_geometry.atoms) if vibration_geometry else 0)
    normal = bool(re.search(r'EXECUTION OF (?:GAMESS|FIREFLY|PC GAMESS) TERMINATED NORMALLY', text))
    error = 'GAMESS' if re.search(r'TERMINATED -ABNORMALLY-', text) else None
    return Output(
        normal,
        converged_at >= 0,
        bool(re.search(r'SCF IS UNCONVERGED|DENSITY CONVERGENCE NOT ACHIEVED', text)),
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

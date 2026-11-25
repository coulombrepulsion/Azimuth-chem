"""Read a Psi4 output (Psi4 1.2-1.7) into an Output.

§1 THEORY
    As for ORCA (modules/spectrum/readers/orca.py): energies, geometries, optimization, harmonic frequencies with
    normal modes and IR intensities, Mulliken charges, the dipole moment. Psi4 computes frequencies from
    gradients or energies at displaced geometries (finite differences, FINDIF) unless the Hessian is
    analytic; the first computation of such a job is at the reference geometry.
§2 ALGORITHM
    Version «Psi4 1.7 release»; normal end «*** Psi4 exiting successfully»; geometry blocks «Geometry (in
    Angstrom|Bohr), charge = c, multiplicity = m:» (rows «symbol x y z [mass]»); SCF energies
    «@<method> Final Energy: E»; correlated energies «* MP2|CCSD|CCSD(T) total energy = E» and the DF-MP2
    block «==> DF-MP2 Energies <==» … «Total Energy = E [Eh]» — the last of them is the final energy.
    Optimization (OPTKING): converged with «Optimization is complete» or «Final optimized geometry and
    variables»; the final geometry is the block after the latter; steps: every geometry block followed by
    an SCF energy before the next geometry block. FINDIF («FINDIF» or «Number of displacements per
    irrep»): geometry, vibration geometry, energy and properties are those of the first computation (the
    reference geometry); the energies of the displaced points are not listed. Frequencies:
    «==> Harmonic Vibrational Analysis <==», columns «Vibration n», «Freq [cm^-1]» (an «i» marks an
    imaginary one: negative), «IR activ [km/mol]», then one row per atom with x y z per column. Mulliken:
    «Mulliken Charges: (a.u.)» rows «n symbol alpha beta spin total». Dipole: «Multipole Moments» L = 1
    totals in a.u. (Psi4 1.4+) or «Dipole Moment: [D]» X Y Z Total (older).
§3 APPLICATIONS
    modules/spectrum/readers/outputs.py.
§4 SPECIFICATION
    is_psi4(text) -> bool; read_psi4(text) -> orca.Output with program 'Psi4 <version>' and final_energy.
    DEBYE_PSI4 = 2.5417464519 D per e*a0, printed by Psi4 1.7 itself («Multiply by 2.5417464519»).
§5 PROCEDURES - below.
§6 NOTES
    Verified 2026-10-23 on the Psi4 1.2.1, 1.3.1 and 1.7 outputs of the cclib test data (data/Psi4, BSD-3-
    Clause; excerpts of the 1.7 ones in tests/data/psi4). ASSUMPTION: the older «Dipole Moment: [D]» uses the
    same factor (Psi4 1.2 does not print it).
§7 TESTS
    tests/spectrum/test_psi4.py.
§8' ROBUSTNESS
    Blocks that do not parse are skipped; the frequency table must have one row per atom.
"""

from dataclasses import replace
from math import isfinite
import re

from modules.spectrum.readers.results import NUMBER, OptimizationStep, Output
from modules.spectrum.readers.orca_properties import Properties
from azimuth.core import Atom, Molecule, SYMBOLS
from modules.compass.chemistry.geometry_tools import BOHR

DEBYE_PSI4 = 2.5417464519
GEOMETRY = re.compile(r'Geometry \(in (Angstrom|Bohr)\), charge = (-?\d+), multiplicity = (\d+):\s*\n')


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


def _excitations(text):
    """TD-DFT / TDA states of the tdscf module: the table after the header with «Excitation Energy»
    and «Oscillator Strength»; rows «n GS->ES (k Irrep) E[au] E[eV] E_total[au] f(length) …» — checked on Psi4 1.11
    (tests/data/psi4/ch2o_tddft_d3bj_psi4-1.11.out)."""
    from modules.spectrum.readers.orca_spectra import EV_CM, Excitation

    head = None
    for head in re.finditer(r'Excitation Energy.*Oscillator Strength.*\n.*\n\s*-{3,}[- ]*\n', text):
        pass  # the last table (an optimization can print several)
    if head is None:
        return ()
    found = []
    row = re.compile(
        r'\s*(\d+)\s+(\S+\s*->\s*\S+\s*\([^)]*\))\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')'
    )
    for line in text[head.end():].splitlines():
        m = row.match(line)
        if not m:
            break
        ev, fosc = float(m[4]), float(m[6])
        if not (isfinite(ev) and ev > 0 and isfinite(fosc)):
            continue
        cm = ev * EV_CM
        found.append(Excitation(int(m[1]), re.sub(r'\s*->\s*', '→', re.sub(r'\s+', ' ', m[2])), ev, cm, 1e7 / cm, max(0.0, fosc)))
    return tuple(found)


def is_psi4(text):
    return 'Psi4: An Open-Source Ab Initio Electronic Structure Package' in text[:20000]


def _geometries(text):
    found = []
    for match in GEOMETRY.finditer(text):
        factor = BOHR if match[1] == 'Bohr' else 1.0
        rows = []
        offset = match.end()
        lines = text[match.end() :].splitlines(keepends=True)
        started = False
        for line in lines:
            f = line.split()
            if not started and (not f or f[0] == 'Center' or set(line.strip()) <= {'-', ' '}):
                offset += len(line)
                continue
            if len(f) in (4, 5) and re.fullmatch(r'[A-Z][a-z]?(\d*|\(.*\))', f[0]):
                symbol = re.match(r'[A-Z][a-z]?', f[0])[0]
                if symbol not in SYMBOLS:
                    rows = []
                    break
                try:
                    rows.append(Atom(symbol, *(_number(v) * factor for v in f[1:4])))
                except ValueError:
                    rows = []
                    break
                started = True
                offset += len(line)
                continue
            break
        if rows:
            found.append((match.start(), offset, Molecule('Psi4', tuple(rows))))
    return found


def _energies(text):
    return [(m.start(), _number(m[1])) for m in re.finditer(r'@\S+ Final Energy:\s+(' + NUMBER + ')', text)]


def _final_energy(text):
    found = [
        (m.start(), m[1], _number(m[2]))
        for m in re.finditer(r'\*\s+(MP2|MP3|CCSD|CCSD\(T\)|CISD) total energy\s*=\s*(' + NUMBER + ')', text)
    ]
    for m in re.finditer(
        r'==> DF-MP2 Energies <==((?:.*\n){1,30}?)\s*Total Energy\s*=\s*(' + NUMBER + r')\s*\[Eh\]', text
    ):
        found.append((m.start(), 'MP2', _number(m[2])))
    if not found:
        return None
    _, label, value = max(found)
    return label, value


def _frequencies(text, natoms):
    from modules.spectrum.readers.vibration_data import Vibration

    start = text.rfind('==> Harmonic Vibrational Analysis <==')
    if start < 0:
        return (), ()
    section = text[start:]
    end = section.find('==> Thermochemistry')
    if end > 0:
        section = section[:end]
    lines = section.splitlines()
    modes = {}
    k = 0
    while k < len(lines):
        f = lines[k].split()
        if f[:1] == ['Vibration'] and len(f) > 1 and all(x.isdigit() for x in f[1:]):
            numbers = [int(x) for x in f[1:]]
            values = {}
            j = k + 1
            while j < len(lines) and not (lines[j].strip() and set(lines[j].strip()) <= {'-'}):
                row = lines[j]
                if row.startswith('  Freq [cm^-1]'):
                    values['freq'] = [(-_number(v[:-1]) if v.endswith('i') else _number(v)) for v in row[14:].split()]
                elif row.startswith('  IR activ [km/mol]'):
                    values['ir'] = [_number(v) for v in row[19:].split()]
                j += 1
            vectors = {n: [] for n in numbers}
            rows = lines[j + 1 : j + 1 + natoms]
            ok = len(rows) == natoms
            for row in rows:
                parts = row.split()
                if len(parts) != 2 + 3 * len(numbers):
                    ok = False
                    break
                for c, n in enumerate(numbers):
                    vectors[n].append(tuple(_number(v) for v in parts[2 + 3 * c : 5 + 3 * c]))
            freqs = values.get('freq', [])
            if len(freqs) != len(numbers):
                k = j
                continue
            ir = values.get('ir', [None] * len(numbers))
            for c, n in enumerate(numbers):
                modes[n] = Vibration(
                    n, freqs[c], tuple(vectors[n]) if ok else None, ir[c] if len(ir) == len(numbers) else None
                )
            k = j + 1 + natoms
            continue
        k += 1
    frequencies = tuple((n, modes[n].frequency) for n in sorted(modes))
    return frequencies, tuple(modes[n] for n in sorted(modes))


def _properties(text, geometry):
    if geometry is None:
        return None
    symbols = [a.symbol for a in geometry.atoms]
    charges, spins = {}, {}
    found = list(
        re.finditer(r'Mulliken Charges: \(a\.u\.\)\s*\n\s*Center\s+Symbol\s+Alpha\s+Beta\s+Spin\s+Total\s*\n', text)
    )
    if found:
        values = []
        for line in text[found[-1].end() :].splitlines()[: len(symbols)]:
            f = line.split()
            if len(f) != 6 or not f[0].isdigit() or f[1] != symbols[len(values)]:
                values = []
                break
            values.append((_number(f[5]), _number(f[4])))
        if len(values) == len(symbols):
            charges['mulliken'] = tuple(v[0] for v in values)
            if any(abs(v[1]) > 0 for v in values):
                spins['mulliken'] = tuple(v[1] for v in values)
    dipole = dipole_debye = None
    new = list(
        re.finditer(
            r'Dipole X\s*:\s*\S+\s+\S+\s+(\S+)\s*\n\s*Dipole Y\s*:\s*\S+\s+\S+\s+(\S+)\s*\n\s*Dipole Z\s*:\s*\S+\s+\S+\s+(\S+)\s*\n\s*Magnitude\s*:\s*(\S+)',
            text,
        )
    )
    old = list(re.finditer(r'Dipole Moment: \[D\]\s*\n\s*X:\s*(\S+)\s+Y:\s*(\S+)\s+Z:\s*(\S+)\s+Total:\s*(\S+)', text))
    if new and (not old or new[-1].start() > old[-1].start()):
        m = new[-1]
        dipole = tuple(_number(m[i]) for i in (1, 2, 3))
        dipole_debye = _number(m[4]) * DEBYE_PSI4
    elif old:
        m = old[-1]
        dipole = tuple(_number(m[i]) / DEBYE_PSI4 for i in (1, 2, 3))
        dipole_debye = _number(m[4])
    props = Properties(geometry, charges, spins, None, (), dipole, dipole_debye, None)
    return None if props.empty else props


def read_psi4(text):
    if not is_psi4(text):
        raise ValueError('not a Psi4 output')
    version = re.search(r'Psi4 (\d+\.\d+(?:\.\d+)?)', text[:20000])
    program = f'Psi4 {version[1]}' if version else 'Psi4'
    geometries = _geometries(text)
    energies = all_energies = _energies(text)
    findif = (
        bool(re.search(r'FINDIF|Number of displacements per irrep', text)) and 'Harmonic Vibrational Analysis' in text
    )
    final_block = text.rfind('Final optimized geometry and variables')
    converged = 'Optimization is complete' in text or final_block >= 0
    steps = ()
    # the steps of an optimization end where the frequencies by finite differences begin («Оптимизация + частоты» in
    # one file: optimize(), then frequency()) — such a file had no steps at all (Psi4 1.11, 2026-11-22)
    # a search of a transition state begins with a Hessian by finite differences (full_hess_every 0): that FINDIF
    # stands before the optimization — the one of frequency() is the first after «Final optimized geometry». Without
    # this the file had no steps, and its geometry and energy were those of the start (Psi4 1.11, HCN ⇌ HNC)
    marks = [m.start() for m in re.finditer(r'FINDIF|Number of displacements per irrep', text)] if findif else []
    first_step = text.find('OPTKING')
    hessian_first = bool(marks) and 0 <= marks[0] < first_step
    marker = next((q for q in marks if final_block < 0 or q > final_block), None) if hessian_first else (marks[0] if marks else None)
    optimized = marker if marker is not None and final_block >= 0 and final_block < marker else (None if findif else len(text))
    if hessian_first and optimized is None and final_block >= 0:
        optimized = len(text)  # the search alone, no frequency() after it
    if 'OPTKING' in text and optimized is not None and hessian_first:
        # the steps are the rows of the table of OPTKING («  n  energy  ΔE … ~»): the geometries displaced for the
        # Hessian have energies too and are not steps
        found, used, seen = [], 0, set()
        for row in re.finditer(r'^\s*(\d+)\s+(-?\d+\.\d{6,})\s+\S+\s+\S+.*~\s*$', text[:optimized], re.M):
            if row[1] in seen:
                continue
            seen.add(row[1])
            value = float(row[2])
            at = next((q for q, e in energies if q >= used and q < row.start() and abs(e - value) < 5e-8), None)
            before = [g for g in geometries if at is not None and g[1] <= at]
            if at is None or not before:
                continue
            used = at + 1
            found.append(OptimizationStep(len(found) + 1, value, replace(before[-1][2], title=f'Psi4 · шаг {len(found) + 1}')))
        steps = tuple(found) if len(found) > 1 else ()
    elif 'OPTKING' in text and optimized is not None:
        found = []
        for k, (start, end, molecule) in enumerate(geometries):
            if start >= optimized:
                break
            nxt = geometries[k + 1][0] if k + 1 < len(geometries) else len(text)
            nxt = min(nxt, optimized)
            inside = [e for p, e in energies if end <= p < nxt]
            if inside:
                found.append(
                    OptimizationStep(
                        len(found) + 1, inside[-1], replace(molecule, title=f'Psi4 · шаг {len(found) + 1}')
                    )
                )
        steps = tuple(found) if len(found) > 1 else ()
    geometry = None
    if final_block >= 0:
        after = [g for g in geometries if g[0] > final_block]
        geometry = after[0][2] if after else None
    if findif and geometries and optimized is not None and optimized < len(text):
        # optimize() then frequency(): the frequencies are of the reference geometry of FINDIF — the optimized one, not
        # the first geometry of the file (that was the start: the modes and the energy of the unoptimized molecule)
        reference = [g for g in geometries if g[0] >= optimized]
        geometry = (reference or geometries)[0][2]
        later = [(q, e) for q, e in energies if q >= optimized]
        energies = [(q, e) for q, e in energies if q < optimized] + later[:1]
    elif findif and geometries and not (hessian_first and final_block >= 0):
        geometry = geometries[0][2]
        energies = energies[:1]
    if geometry is None and geometries:
        geometry = geometries[-1][2]
    natoms = len(geometry.atoms) if geometry else 0
    frequencies, modes = _frequencies(text, natoms)
    vibration_geometry = geometry if frequencies else None
    if not energies and geometry is None:
        raise ValueError('no recognizable section of a Psi4 output')
    error = re.search(r'Traceback|PsiException|Fatal Error', text)
    return Output(
        '*** Psi4 exiting successfully' in text,
        converged and 'OPTKING' in text,
        bool(re.search(r'Could not converge SCF iterations|SCFConvergenceError', text)),
        tuple(e for _, e in energies),
        frequencies,
        replace(geometry, title=program) if geometry else None,
        False,
        steps,
        vibration_geometry,
        modes,
        'Psi4' if error and '*** Psi4 exiting successfully' not in text else None,
        False,
        geometries[0][2] if geometries else None,
        _properties(text[: all_energies[1][0]] if findif and len(all_energies) > 1 else text, geometry),
        None,
        _excitations(text),  # TD-DFT (tdscf)
        (),
        program,
        _final_energy(text),
    )

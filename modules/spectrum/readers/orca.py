"""Read a single ORCA output. Missing evidence is kept distinct from success."""

import re
from math import isfinite
from azimuth.core import read_xyz
from azimuth.i18n import tr
from modules.spectrum.readers.orca_properties import read_properties
from modules.spectrum.readers.orca_scan import read_scan
from modules.spectrum.readers.orca_spectra import read_absorption, read_couplings, read_shieldings
# the general model of a result lives in results.py; re-exported here for the old imports
from modules.spectrum.readers.results import MAX_BYTES, NUMBER, OptimizationStep, Output, number, too_large  # noqa: F401


def optimization_steps(text):
    """Pair only explicit cycles; never zip independent energy/coordinate lists."""
    headers = list(re.finditer(r'GEOMETRY OPTIMIZATION CYCLE\s+(\d+)', text))
    steps = []
    signature = None
    for i, header in enumerate(headers):
        block = text[header.end() : headers[i + 1].start() if i + 1 < len(headers) else len(text)]
        # Relaxation and frequency calculations may print other geometries/energies.
        block = re.split(
            r'ORCA GEOMETRY RELAXATION STEP|THE OPTIMIZATION HAS CONVERGED|VIBRATIONAL FREQUENCIES|FINAL ENERGY EVALUATION|NUMERICAL FREQUENCIES',
            block,
        )[0]
        coords = re.search(r'CARTESIAN COORDINATES\s*\(ANGSTROE?M\)', block)
        geometry = None
        if coords:
            rows = []
            for line in block[coords.end() :].splitlines():
                if not rows and (not line.strip() or set(line.strip()) == {'-'}):
                    continue
                if not line.strip():
                    break
                if not re.fullmatch(r'\s*[A-Z][a-z]?\s+' + NUMBER + r'\s+' + NUMBER + r'\s+' + NUMBER + r'\s*', line):
                    rows = []  # A truncated or unsupported coordinate block is not a molecule.
                    break
                f = line.split()
                rows.append(' '.join([f[0], *(str(number(v)) for v in f[1:])]))
            if rows:
                try:
                    geometry = read_xyz(tr(f'{len(rows)}\nЦикл {header[1]} ORCA\n') + '\n'.join(rows))
                except ValueError:
                    pass
        values = re.findall(r'FINAL SINGLE POINT ENERGY\s+(' + NUMBER + ')', block)
        energy = number(values[0]) if len(values) == 1 else None
        gradient = _cycle_gradient(block, len(geometry.atoms) if geometry else 0)
        if energy is not None and not isfinite(energy):
            energy = None
        if geometry:
            current = tuple(a.symbol for a in geometry.atoms)
            if signature is None:
                signature = current
            elif current != signature:
                geometry = None
        steps.append(OptimizationStep(int(header[1]), energy, geometry, gradient if geometry else None))
    return tuple(steps)


def _cycle_gradient(block, count):
    """The last «CARTESIAN GRADIENT» block of a cycle (rows «n El : gx gy gz»), or None if it does not have
    one row per atom."""
    found = list(re.finditer(r'CARTESIAN GRADIENT\s*\n-+\s*\n', block))
    if not found or not count:
        return None
    rows = []
    for line in block[found[-1].end():].splitlines():
        m = re.fullmatch(r'\s*\d+\s+[A-Za-z]+\s*:\s*(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s*', line)
        if m:
            rows.append(tuple(number(v) for v in m.groups()))
        elif rows or line.strip():
            break
    return tuple(rows) if len(rows) == count and all(isfinite(c) for r in rows for c in r) else None


def input_geometry(text):
    """The geometry of the input file echoed at the top of an ORCA output.

    ORCA prints the input as lines '| n> ...'; the block '* xyz charge mult' ... '*' gives the
    starting coordinates in angstrom. Other forms (xyzfile, internal coordinates, Bohr units) give None.
    """
    lines = [m[1] for m in re.finditer(r'^\|\s*\d+>\s?(.*)$', text, re.M)]
    rows, inside = [], False
    for line in lines:
        bare = line.split('#')[0].strip()
        if not inside:
            if re.match(r'^\*\s*xyz\s+[+-]?\d+\s+\d+\s*$', bare, re.I):
                inside = True
            elif re.match(r'^!.*\bbohrs?\b', bare, re.I):
                return None
            continue
        if bare == '*':
            break
        fields = bare.split()
        if (
            len(fields) >= 4
            and re.fullmatch(r'[A-Z][a-z]?', fields[0])
            and all(re.fullmatch(NUMBER, f) for f in fields[1:4])
        ):
            rows.append(' '.join([fields[0], *(str(number(v)) for v in fields[1:4])]))
        elif bare:
            return None  # dummy atoms, ghost atoms, extra columns: not a plain geometry
    if not inside or not rows:
        return None
    try:
        return read_xyz(tr(f'{len(rows)}\nВходной файл ORCA\n') + '\n'.join(rows))
    except ValueError:
        return None


def read_output(text):
    if len(text) > MAX_BYTES:
        raise too_large()
    if text.count('ORCA TERMINATED NORMALLY') > 1 or len(re.findall(r'JOB NUMBER\s+\d+', text)) > 1:
        raise ValueError(tr('Обнаружено несколько заданий. Откройте выходной файл одного задания.'))
    energies = tuple(number(v) for v in re.findall(r'FINAL SINGLE POINT ENERGY\s+(' + NUMBER + ')', text))
    if not energies:  # the total energies of the SCF of each geometry
        energies = tuple(number(v) for v in re.findall(r'^Total Energy\s*:\s*(' + NUMBER + r')\s*Eh', text, re.M))
    # after TD-DFT the «FINAL SINGLE POINT ENERGY» is E(tot) of the root
    # followed (ground + excitation, -76.0408 for water instead of -76.3210); for a single point the energy of the
    # result is the ground state E(SCF) — the excited one is kept apart. An excited-state optimization keeps E(tot).
    excited = None
    totals = re.findall(r'E\(SCF\)\s*=\s*(' + NUMBER + r')\s*Eh\s*\n\s*DE\(CIS\)\s*=\s*' + NUMBER
                        + r'\s*Eh\s*\(Root\s+(\d+)\)\s*\n[\s-]*\n\s*E\(tot\)\s*=\s*(' + NUMBER + ')', text)
    if totals and energies and 'GEOMETRY OPTIMIZATION' not in text:
        ground, root, total = totals[-1]
        if abs(number(total) - energies[-1]) < 1e-6:
            energies = energies[:-1] + (number(ground),)
            excited = (int(root), number(total))
    frequency_blocks = text.split('VIBRATIONAL FREQUENCIES')
    frequencies = []
    if len(frequency_blocks) > 1:
        block = frequency_blocks[-1]
        started = False
        for line in block.splitlines():
            match = re.match(r'\s*(\d+)\s*:\s*(' + NUMBER + r')\s+cm(?:\*\*|\^)?-1', line)
            if match:
                frequencies.append((int(match[1]), number(match[2])))
                started = True
            elif started and line.strip():
                break
    geometry = None
    for block in re.split(r'CARTESIAN COORDINATES\s*\(ANGSTROE?M\)', text)[1:]:
        atoms = []
        for line in block.splitlines():
            if re.fullmatch(r'\s*[A-Z][a-z]?\s+' + NUMBER + r'\s+' + NUMBER + r'\s+' + NUMBER + r'\s*', line):
                fields = line.split()
                atoms.append(' '.join([fields[0], *(str(number(v)) for v in fields[1:])]))
            elif atoms:
                break
        if atoms:
            try:
                geometry = read_xyz(tr(f'{len(atoms)}\nИз выходного файла ORCA\n') + '\n'.join(atoms))
            except ValueError:
                geometry = None
    if not energies and not frequencies and geometry is None and 'ORCA' not in text:
        raise ValueError(tr('Не найдены узнаваемые разделы выходного файла ORCA.'))
    from modules.spectrum.readers.vibration_data import read_vibrations

    vibration_geometry, modes = read_vibrations(text, frequencies)
    errors = re.findall(r'^\s*ORCA finished by error termination in ([A-Za-z][A-Za-z0-9_-]*)\s*$', text, re.M)
    return Output(
        'ORCA TERMINATED NORMALLY' in text,
        'THE OPTIMIZATION HAS CONVERGED' in text,
        bool(
            re.search(
                r'SCF (?:NOT CONVERGED|DID NOT CONVERGE)|SCF CONVERGENCE FAILURE|SCF has not converged', text, re.I
            )
        ),
        energies,
        tuple(frequencies),
        geometry,
        'QCC-STUDIO-SYNTHETIC-DEMO' in text,
        optimization_steps(text),
        vibration_geometry,
        modes,
        errors[-1] if errors else None,
        bool(re.search(r"^.*Failed to get [^\r\n]+ cpu set\s*$", text, re.M)),
        input_geometry(text),
        read_properties(text),
        read_scan(text),
        read_absorption(text),
        read_shieldings(text),
        excited_energy=excited,
        raman_skipped='Analytical Hessian not available for calculation of RAMAN' in text,  # 0.90.1 (ORCA 6.0.1)
        couplings=read_couplings(text),
    )

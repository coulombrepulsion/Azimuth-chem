"""MOPAC results: the output (.out) and its auxiliary file (.aux) — semiempirical PM7, PM6, AM1, RM1, MNDO.

§1 THEORY
    MOPAC gives the heat of formation ΔHf at 298 K (kcal/mol, relative to the elements in their standard states), not
    the total energy of the other programs (hartree). Differences of ΔHf between structures of the same method are
    reaction enthalpies; a ΔHf must never be mixed with ab initio energies (§6). The vibrations come from FORCE on the
    geometry given (MOPAC does not optimize before it): at a geometry that is not stationary the frequencies, and the
    six trivial modes, are wrong — MOPAC 23.2.5 does not stop there (tests/data/mopac).
§2 ALGORITHM
    is_mopac(text): «MOPAC v<version>» or «MOPAC20xx» in the banner and «CALCULATION RESULTS» / «CALCULATION DONE».
    read_aux(text): the «KEY:UNIT[count]=value» items of the .aux (primitive mark-up of openmopac.net/Manual/
    auxiliary.html): the values after «=» and on the following lines up to the next item; «#» lines are comments;
    numbers with D exponents. Repeated keys (the *_UPDATED of every optimization step) are kept in order.
    read_mopac(text, path): the .aux next to the output (same name), when it exists, else the output alone.
      ΔHf: HEAT_OF_FORMATION of the .aux, else the last «FINAL HEAT OF FORMATION = x KCAL/MOL» or «HEAT OF FORMATION
      = x KCALS/MOLE» of the output. Geometry: the last «CARTESIAN COORDINATES» block of the output (9 decimals after
      an optimization), else ATOM_X_OPT. Steps: ATOM_X_UPDATED with HEAT_OF_FORM_UPDATED (energy None: a ΔHf is not a
      hartree energy). Charges ATOM_CHARGES (key 'mopac'), dipole DIP_VEC / DIPOLE (debye; the vector in e·bohr for
      Properties). Vibrations: VIB._FREQ; the first 3N−6 (3N−5 for a linear molecule) are the vibrations, the rest
      the trivial modes (the order of MOPAC 23); NORMAL_MODES are mass-weighted, mode after mode (as the
      «MASS-WEIGHTED COORDINATE ANALYSIS» of the output): divided by sqrt(ISOTOPIC_MASSES) they give the Cartesian
      displacements, drawn on ORIENTATION_ATOM_X (the orientation of the FORCE calculation). IR intensities: none
      (MOPAC prints transition dipoles VIB._T_DIP in «electrons»; their conversion to km/mol is not established).
      Normal end: «JOB ENDED NORMALLY». Converged: «GEOMETRY OPTIMISED» or «IS LESS THAN CUTOFF».
§3 APPLICATIONS
    modules/spectrum/readers/outputs.py (read_any), Spectrum and Compass as for the other programs.
§4 SPECIFICATION
    thermo_table(text) -> ((T, ΔHf kcal/mol, H cal/mol, Cp cal/(K·mol), S cal/(K·mol)), ...) of THERMO (the
      first table at 298 K is the reference, printed twice — kept once); Output.mopac_thermo.
    is_mopac(text) -> bool; read_aux(text) -> {key: [(unit, tokens), ...]}; read_mopac(text, path=None) -> orca.Output
    with energies (no total energy), heat_of_formation (kcal/mol), program 'MOPAC <version> <METHOD>', notes.
    FORCE_GRADIENT = 1.0 kcal/(mol·Å): above it the frequencies are said to come from a geometry that is not
    stationary (a design choice: optimized test geometries have 0.0008–0.014, the unoptimized water 1.84).
    ValueError: not a MOPAC output.
§5 PROCEDURES - below.
§6 NOTES
    Verified on real MOPAC 23.2.5 outputs (conda-forge, macOS arm64), tests/data/mopac (PM7, PM6,
    AM1; RHF, UHF doublet, cation, COSMO; optimization, 1SCF, FORCE, THERMO). The reaction diagram, the
    thermochemistry tab and the conformer search take energies; a MOPAC result has none, so it is never put next to an
    ab initio one. ASSUMPTION: MOPAC 2016 / 2012 write the same .aux keys (not checked).
§7 TESTS
    tests/spectrum/test_mopac.py.
"""

from math import isfinite, sqrt
from pathlib import Path
import re

import numpy as np

from azimuth.core import Atom, Molecule, read_xyz
from modules.spectrum.readers.results import OptimizationStep, Output
from modules.spectrum.readers.orca_properties import DEBYE, Properties
from modules.spectrum.readers.vibration_data import Vibration

FORCE_GRADIENT = 1.0  # kcal/(mol·Å), §4
ITEM = re.compile(r'^\s*([A-Z][A-Z0-9_.]*)(?::([^=\[]*))?(?:\[(\d+)\])?=(.*)$')
ROW = re.compile(r'^\s+\d+\s+([A-Z][a-z]?)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$', re.M)


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


def is_mopac(text):
    head = text[:20000]
    return bool(re.search(r'MOPAC v\d|MOPAC20\d\d', head)) and bool(re.search(r'CALCULATION (RESULTS|DONE)', head))


def read_aux(text):
    items = {}
    current = None
    for line in text.splitlines():
        if line.lstrip().startswith('#'):
            continue
        m = ITEM.match(line)
        if m:
            current = (m[2] or '').strip(), m[4].split()
            items.setdefault(m[1], []).append(current)
        elif current is not None and line.strip() and not line.strip().startswith(('START OF', 'END OF')):
            current[1].extend(line.split())
    return items


def _last(items, key):
    found = items.get(key)
    return found[-1][1] if found else None


def _numbers(tokens):
    """The numbers of a key of the .aux; None when one of them is not a number. For a single atom MOPAC writes an
    overflow (asterisks, glued to the number before it) into the keys of a molecule that has no rotation — the whole
    result failed to open; now only that key is left out."""
    if not tokens:
        return None
    try:
        values = [float(t) for t in tokens]  # the usual form at once; D exponents and the rest below
    except ValueError:
        try:
            return [_number(t) for t in tokens]
        except ValueError:
            return None
    return values if all(isfinite(v) for v in values) else None


def _molecule(symbols, values, title, check=True):
    """A structure of the .aux. check=False: the
    intermediate steps of an optimization — built directly, without read_xyz's test for atoms closer than 0.1 Å (a
    search over all atoms for each of 1276 steps took 2 of the 2.1 s of reading a 6.6 MB output); the first and the last
    step and the geometries are still read through read_xyz."""
    if not symbols or not values or len(values) != 3 * len(symbols):
        return None
    if not check:
        if any(abs(v) >= 100000 for v in values):
            return None
        return Molecule(title, tuple(Atom(s, values[3 * i], values[3 * i + 1], values[3 * i + 2])
                                     for i, s in enumerate(symbols)))
    rows = '\n'.join(f'{s} {values[3 * i]} {values[3 * i + 1]} {values[3 * i + 2]}' for i, s in enumerate(symbols))
    return read_xyz(f'{len(symbols)}\n{title}\n{rows}')


def _out_geometry(text, title):
    heads = list(re.finditer(r'^\s*CARTESIAN COORDINATES\s*$', text, re.M))  # not «… COORDINATE DERIVATIVES»
    if not heads:
        return None
    block = text[heads[-1].end():]
    block = re.split(r'Empirical Formula|General Reference', block, maxsplit=1)[0]
    rows = ROW.findall(block)
    return read_xyz(f'{len(rows)}\n{title}\n' + '\n'.join(' '.join(r) for r in rows)) if rows else None


THERMO_ROW = re.compile(r'^\s*(\d+\.\d+)\s+VIB\.(?:.*\n){4}\s*TOT\.\s+(-?\d+\.\d+)\s+(-?\d+\.\d+)\s+'
                        r'(-?\d+\.\d+)\s+(-?\d+\.\d+)\s*$', re.M)


def thermo_table(text):
    """The «TOT.» rows of «CALCULATED THERMODYNAMIC PROPERTIES»: (T, ΔHf, H, Cp, S), each T once."""
    head = text.rfind('CALCULATED THERMODYNAMIC PROPERTIES')
    if head < 0:
        return ()
    rows = {}
    for m in THERMO_ROW.finditer(text, head):
        rows.setdefault(float(m[1]), tuple(float(x) for x in m.groups()))
    return tuple(rows.values())


def _linear(molecule):
    xyz = np.array([a.position for a in molecule.atoms], float)
    if len(xyz) < 3:
        return True
    return np.linalg.svd(xyz - xyz.mean(axis=0), compute_uv=False)[1] < 1e-3


def read_mopac(text, path=None):
    if not is_mopac(text):
        raise ValueError('not a MOPAC output')
    aux_path = Path(path).with_suffix('.aux') if path else None
    items = {}
    if aux_path is not None and aux_path.is_file():
        try:
            items = read_aux(aux_path.read_text(encoding='utf-8', errors='replace'))
        except (OSError, ValueError):
            items = {}
    version = re.search(r'MOPAC v(\S+)', text) or re.search(r'(MOPAC20\d\d)', text)
    method = (_last(items, 'METHOD') or [None])[0] or (re.search(r'^\s*(\S+)\s+CALCULATION RESULTS', text, re.M) or [None, ''])[1]
    program = ('MOPAC ' + version[1] if version else 'MOPAC') + (f' {method}' if method else '')
    symbols = _last(items, 'ATOM_EL')
    try:
        hof = _number(_last(items, 'HEAT_OF_FORMATION')[0]) if _last(items, 'HEAT_OF_FORMATION') else None
    except ValueError:
        hof = None
    if hof is None:
        found = re.findall(r'(?:FINAL )?HEAT OF FORMATION\s*=\s*(-?\d+\.\d+)\s*KCALS?/MOL', text)
        hof = float(found[-1]) if found else None
    geometry = _out_geometry(text, program)
    if geometry is None and symbols:
        geometry = _molecule(symbols, _numbers(_last(items, 'ATOM_X_OPT')), program)
    steps = []
    updated = items.get('ATOM_X_UPDATED', [])
    for cycle, (_, values) in enumerate(updated, 1):
        step = _molecule(symbols, _numbers(values), f'{program}, step {cycle}', check=cycle in (1, len(updated)))
        if step is not None:
            steps.append(OptimizationStep(cycle, None, step))
    props = None
    charges = _numbers(_last(items, 'ATOM_CHARGES'))
    if geometry is not None and charges and len(charges) == len(geometry.atoms):
        vector = _numbers(_last(items, 'DIP_VEC'))
        total = _numbers(_last(items, 'DIPOLE'))
        props = Properties(geometry, {'mopac': tuple(charges)}, {}, None, (),
                           tuple(v / DEBYE for v in vector) if vector and len(vector) == 3 else None,
                           total[0] if total else None, None)
    frequencies, modes, vibration_geometry = [], [], None
    freqs = _numbers(_last(items, 'VIB._FREQ'))
    if freqs and symbols:
        n = len(symbols)
        reference = geometry or _molecule(symbols, _numbers(_last(items, 'ATOM_X_OPT')), program)
        count = 3 * n - (5 if reference is not None and _linear(reference) else 6)
        vibration_geometry = _molecule(symbols, _numbers(_last(items, 'ORIENTATION_ATOM_X')), program)
        masses = _numbers(_last(items, 'ISOTOPIC_MASSES'))
        normal = _numbers(_last(items, 'NORMAL_MODES'))
        for k, f in enumerate(freqs[:max(0, count)], 1):
            vectors = None
            if normal and masses and len(normal) == len(freqs) * 3 * n and len(masses) == n and vibration_geometry:
                chunk = normal[(k - 1) * 3 * n:k * 3 * n]
                vectors = tuple(tuple(chunk[3 * a + c] / sqrt(masses[a]) for c in range(3)) for a in range(n))
            frequencies.append((k, f))
            modes.append(Vibration(k, f, vectors, None))
    notes = []
    if hof is not None:
        notes.append(f'MOPAC ({method or "?"}): теплота образования ΔHf = {hof:.3f} ккал/моль при 298 К — не полная '
                     'энергия; сравнивать её можно только с результатами MOPAC тем же методом.')
    gnorm = _numbers(_last(items, 'GRADIENT_NORM'))
    if frequencies and gnorm and gnorm[0] > FORCE_GRADIENT:
        notes.append(f'Частоты посчитаны не в стационарной точке: норма градиента {gnorm[0]:.2f} ккал/(моль·Å). '
                     'MOPAC (FORCE) не оптимизирует сам — сначала оптимизация, потом частоты.')
    # «GEOMETRY IN ERROR» (two atoms too close): nothing is computed, and the job still «ENDED NORMALLY»
    # and FORCE refused at a geometry far from a stationary point (the gradient over 10): no frequencies
    normal_exit = ('JOB ENDED NORMALLY' in text and 'GEOMETRY IN ERROR' not in text
                   and 'GRADIENT IS TOO LARGE TO ALLOW THE FORCE MATRIX' not in text)
    return Output(
        normal_exit,
        bool(re.search(r'GEOMETRY OPTIMISED|IS LESS THAN CUTOFF', text)),
        bool(re.search(r'SCF NOT ACHIEVED|UNABLE TO ACHIEVE SELF-CONSISTENCE', text)),
        (),
        tuple(frequencies),
        geometry,
        False,
        tuple(steps),
        vibration_geometry,
        tuple(modes),
        None,
        False,
        None,
        props,
        program=program,
        heat_of_formation=hof,
        notes=tuple(notes),
        mopac_thermo=thermo_table(text),
    )

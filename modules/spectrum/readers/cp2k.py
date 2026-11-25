"""The output of CP2K (Quickstep) for a crystal: the energy, the optimisation, the final cell.

§1 THEORY
    CP2K prints the total energy of each evaluation as «ENERGY| Total FORCE_EVAL ( QS ) energy [hartree]: E» (older
    versions «[a.u.]»); an optimisation counts «OPTIMIZATION STEP: n» and ends «GEOMETRY OPTIMIZATION COMPLETED» (also
    for CELL_OPT); the positions of each step go into <project>-pos-1.xyz (Å), the cell of a CELL_OPT into
    <project>-1.cell («Step Time Ax Ay Az Bx By Bz Cx Cy Cz Volume», Å); a finished run prints «PROGRAM ENDED AT»; an
    error — a box of «*» with «[ABORT]».
§2 ALGORITHM
    read(text, folder=None) -> qe.Result (the same fields as Quantum ESPRESSO, so the window shows both): energies in Ry
    (2 × hartree), energy and energy_hartree of the last one, nat, steps, converged, done, error; with the folder of the
    run — the last frame of the positions and the last cell (or the cell of the input azimuth.inp) as fractions: cell,
    atoms for qe.final_crystal.
§4 SPECIFICATION
    is_cp2k(text) -> bool; read(text, folder=None) -> modules.spectrum.readers.qe.Result.
§7 TESTS
    tests/spectrum/test_cp2k_reader.py — a short output and the files of an optimisation written by hand in the format
    of CP2K 2026 (no run of CP2K on the computer of the tests: its build needs glibc 2.38).
"""

from pathlib import Path
import re

from modules.spectrum.readers.qe import Result

_FLOAT = r'[-+]?\d+\.\d+(?:[EeDd][-+]?\d+)?'
PROJECT = 'azimuth'


def is_cp2k(text):
    return 'CP2K|' in text[:50000] or 'PROGRAM STARTED AT' in text[:50000]


def _frames(path):
    """The frames of an xyz file: [(symbol, (x, y, z))] each."""
    lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
    frames, k = [], 0
    while k < len(lines):
        try:
            n = int(lines[k].split()[0])
        except (ValueError, IndexError):
            break
        rows = lines[k + 2:k + 2 + n]
        frames.append([(r.split()[0], tuple(float(v) for v in r.split()[1:4])) for r in rows if len(r.split()) >= 4])
        k += 2 + n
    return frames


def _input_cell(path):
    text = path.read_text(encoding='utf-8', errors='replace')
    rows = {}
    for name in 'ABC':
        m = re.search(r'^\s*' + name + r'\s+(' + _FLOAT + r')\s+(' + _FLOAT + r')\s+(' + _FLOAT + r')\s*$', text, re.M)
        if not m:
            return None
        rows[name] = tuple(float(v) for v in m.groups())
    return tuple(rows[n] for n in 'ABC')


SCF_LINE = re.compile(r'^\s+(\d+)\s+(\S.*?)\s+\d\.\d+E[+-]\d+\s+[\d.]+\s+[\d.]+(?:E[+-]\d+)?\s+(-?\d+\.\d+)\s+'
                      r'(-?\d\.\d+E[+-]\d+)\s*$', re.M)


def progress(text):
    """What a running CP2K has done — the step of the SCF under way (its number, total energy in hartree and
    change: the line «Step Update method Time Convergence Total energy Change»), the step of the optimization
    (OPTIMIZATION STEP), the SCF cycles converged. {} until the first SCF line."""
    lines = SCF_LINE.findall(text)
    found = {}
    if lines:
        step, method, energy, change = lines[-1]
        found.update(scf_step=int(step), scf_method=method.strip(), scf_energy=float(energy), scf_change=float(change))
    found['scf_converged'] = text.count('SCF run converged')
    steps = re.findall(r'OPTIMIZATION STEP:\s*(\d+)', text)
    found['opt_step'] = int(steps[-1]) if steps else 0
    return found


_ART = re.compile(r'^\s*(?:(?:\[ABORT\]|[/\\_|O]+)\s+)*')


def abort_message(text):
    """The words of the box «[ABORT]» of CP2K — without its picture (the face, the arms, the legs at the left) and
    the place in its sources at the end («… DIRECT_CELL_OPT. O/| / \\ input/input_parsing.F:262»)."""
    lines = [line.rstrip() for line in text.splitlines()]
    start = next((i for i, line in enumerate(lines) if '[ABORT]' in line), None)
    if start is None:
        return ''
    words = []
    for line in lines[start:]:
        if not line.lstrip().startswith('*') or not line.endswith('*') or set(line.strip()) <= {'*'}:
            break
        inner = line.strip()[1:-1]
        words.append(_ART.sub('', inner).strip())
    said = re.sub(r'\s+', ' ', ' '.join(w for w in words if w)).strip()
    return re.sub(r'\s*\S+\.F:\d+$', '', said).strip()


def _input_atoms(path, cell):
    """The atoms of &COORD of azimuth.inp: [(symbol, fractions)] (SCALED, or Cartesian Å through the cell)."""
    import numpy as np

    text = path.read_text(encoding='utf-8', errors='replace')
    block = re.search(r'&COORD\s*\n(.*?)&END COORD', text, re.S)
    if not block:
        return []
    rows = [line.split() for line in block.group(1).splitlines() if line.strip()]
    scaled = any(r[0].upper() == 'SCALED' and (len(r) == 1 or r[1].upper() in ('T', 'TRUE', '.TRUE.')) for r in rows)
    inverse = np.linalg.inv(np.array(cell, dtype=float))
    atoms = []
    for r in rows:
        if len(r) >= 4 and r[0].upper() not in ('SCALED', 'UNIT'):
            xyz = np.array([float(x) for x in r[1:4]])
            atoms.append((r[0], tuple(float(x) for x in (xyz if scaled else xyz @ inverse))))
    return atoms


def steps(folder, text=None):
    """The geometries of a GEO_OPT / CELL_OPT, the start first — [(energy in hartree or None, cell rows in Å,
    ((symbol, fractions), …))]. The start: &CELL and &COORD of azimuth.inp with the first energy of cp2k.out; then the
    frames of azimuth-pos-1.xyz («i = N, E = …»; CP2K 2026.2 writes the steps from i = 1, the start is not there), each
    with the row of azimuth-1.cell of the same step N (the last row before it when there is none — the frame of the end
    repeats the last step; the cell of the input for a GEO_OPT without that file). A frame i = 0 is the start itself.
    [] without frames or without a cell."""
    import numpy as np

    folder = Path(folder)
    positions = folder / f'{PROJECT}-pos-1.xyz'
    if not positions.is_file():
        return []
    frames = _frames(positions)
    numbers, energies = [], []
    for line in positions.read_text(encoding='utf-8', errors='replace').splitlines():
        if 'E =' in line:
            i = re.search(r'i\s*=\s*(\d+)', line)
            e = re.search(r'E\s*=\s*([-+]?\d+\.?\d*(?:[EeDd][-+]?\d+)?)', line)
            numbers.append(int(i.group(1)) if i else len(numbers))
            energies.append(float(e.group(1)) if e else None)
    cells = {}
    file = folder / f'{PROJECT}-1.cell'
    if file.is_file():
        for line in file.read_text(encoding='utf-8', errors='replace').splitlines():
            words = line.split()
            if len(words) >= 11 and not line.lstrip().startswith('#'):
                v = [float(x) for x in words[2:11]]
                cells[int(float(words[0]))] = (tuple(v[0:3]), tuple(v[3:6]), tuple(v[6:9]))
    given = folder / 'azimuth.inp'
    fixed = _input_cell(given) if given.is_file() else None
    found = []
    if fixed is not None and (not numbers or numbers[0] != 0):
        start = _input_atoms(given, fixed)
        if text is None and (folder / 'cp2k.out').is_file():
            text = (folder / 'cp2k.out').read_text(encoding='utf-8', errors='replace')
        first = re.search(r'ENERGY\| Total FORCE_EVAL \( QS \) energy \[[^\]]*\]:?\s*(' + _FLOAT + ')', text or '')
        if start:
            found.append((float(first.group(1)) if first else None, fixed, tuple(start)))
    for k, frame in enumerate(frames):
        n = numbers[k] if k < len(numbers) else k
        known = [m for m in cells if m <= n]
        cell = cells[max(known)] if known else fixed
        if cell is None:
            return []
        inverse = np.linalg.inv(np.array(cell, dtype=float))
        atoms = tuple((s, tuple(float(x) for x in np.array(p) @ inverse)) for s, p in frame)
        found.append((energies[k] if k < len(energies) else None, cell, atoms))
    return found


def read(text, folder=None):
    r = Result(calculation='cp2k')
    version = re.search(r'CP2K\| version string:\s*(.+)', text)
    r.version = version.group(1).strip() if version else ''
    hartree = [float(v) for v in re.findall(r'ENERGY\| Total FORCE_EVAL \( QS \) energy \[[^\]]*\]:?\s*(' + _FLOAT + ')', text)]
    r.energies = [2 * e for e in hartree]
    if hartree:
        r.energy_hartree, r.energy = hartree[-1], 2 * hartree[-1]
    atoms = re.search(r'- Atoms:\s+(\d+)', text)
    r.nat = int(atoms.group(1)) if atoms else 0
    r.steps = len(re.findall(r'OPTIMIZATION STEP:\s*\d+', text))
    # converged as in qe.read — the SCF converged, and an
    # optimization (GEO_OPT, CELL_OPT) completed; an energy alone was never «converged» here
    run_type = re.search(r'GLOBAL\| Run type\s+(\S+)', text)
    optimizing = bool(run_type) and run_type.group(1).upper() in ('GEO_OPT', 'CELL_OPT')
    scf = 'SCF run converged' in text and 'SCF run NOT converged' not in text
    r.converged = scf and ('GEOMETRY OPTIMIZATION COMPLETED' in text or not optimizing)
    r.done = 'PROGRAM ENDED AT' in text
    if '[ABORT]' in text or 'ABORT' in text.split('PROGRAM STARTED AT')[-1]:
        r.error = abort_message(text) or 'ABORT'
        r.done = False
    if folder is not None:
        folder = Path(folder)
        positions = folder / f'{PROJECT}-pos-1.xyz'
        cells = folder / f'{PROJECT}-1.cell'
        cell = None
        if cells.is_file():
            last = [line.split() for line in cells.read_text(encoding='utf-8', errors='replace').splitlines()
                    if line.strip() and not line.lstrip().startswith('#')]
            if last and len(last[-1]) >= 11:
                v = [float(x) for x in last[-1][2:11]]
                cell = (tuple(v[0:3]), tuple(v[3:6]), tuple(v[6:9]))
        if cell is None and (folder / 'azimuth.inp').is_file():
            cell = _input_cell(folder / 'azimuth.inp')
        if positions.is_file() and cell is not None:
            frames = _frames(positions)
            if frames:
                import numpy as np

                inverse = np.linalg.inv(np.array(cell, dtype=float))
                r.cell = cell
                r.atoms = tuple((s, tuple(float(x) for x in np.array(p) @ inverse)) for s, p in frames[-1])
                if not r.nat:
                    r.nat = len(r.atoms)
    return r


# Multiwfn reads the Molden file of
# CP2K as a periodic wave function when two fields are added before it (T. Lu, sobereva.com/651): [Cell] — the three
# vectors of the cell in Å, and [Nval] — the electrons of each element left by its GTH pseudopotential (the effective
# charge of the nucleus; [Atoms] gives the full Z). The valence: the q of DZVP-MOLOPT-SR-GTH-qN in BASIS_MOLOPT of CP2K
# (the same as the GTH-PBE potential CP2K picks for it); checked against «Number of electrons» of cp2k.out.
VALENCE = {
    'H': 1, 'He': 2, 'Li': 3, 'Be': 4, 'B': 3, 'C': 4, 'N': 5, 'O': 6, 'F': 7, 'Ne': 8, 'Na': 9, 'Mg': 10, 'Al': 3,
    'Si': 4, 'P': 5, 'S': 6, 'Cl': 7, 'Ar': 8, 'K': 9, 'Ca': 10, 'Sc': 11, 'Ti': 12, 'V': 13, 'Cr': 14, 'Mn': 15,
    'Fe': 16, 'Co': 17, 'Ni': 18, 'Cu': 11, 'Zn': 12, 'Ga': 13, 'Ge': 4, 'As': 5, 'Se': 6, 'Br': 7, 'Kr': 8, 'Rb': 9,
    'Sr': 10, 'Y': 11, 'Zr': 12, 'Nb': 13, 'Mo': 14, 'Tc': 15, 'Ru': 16, 'Rh': 17, 'Pd': 18, 'Ag': 11, 'Cd': 12,
    'In': 13, 'Sn': 4, 'Sb': 5, 'Te': 6, 'I': 7, 'Xe': 8, 'Cs': 9, 'Ba': 10, 'Hf': 12, 'Ta': 13, 'W': 14, 'Re': 15,
    'Os': 16, 'Ir': 17, 'Pt': 18, 'Au': 11, 'Hg': 12, 'Tl': 13, 'Pb': 4, 'Bi': 5, 'Po': 6, 'At': 7, 'Rn': 8}
FOR_MULTIWFN = PROJECT + '-multiwfn.molden'


def molden_files(folder):
    """The Molden files of a run, the last step last: CP2K writes <project>-MOS-1_N.molden at each step N of an
    optimization (1_0 — the start; the end — the largest N)."""
    found = []
    for path in Path(folder).glob(f'{PROJECT}-MOS-1_*.molden'):
        m = re.fullmatch(re.escape(PROJECT) + r'-MOS-1_(\d+)\.molden', path.name)
        if m:
            found.append((int(m.group(1)), path))
    return [p for _, p in sorted(found)]


def _molden_symbols(text):
    """The symbols of [Atoms] of a Molden file (the first word of each row, «Cs 1 55 x y z»)."""
    block = re.search(r'\[Atoms\][^\n]*\n(.*?)(?=^\s*\[)', text, re.S | re.M)
    symbols = []
    for row in (block.group(1).splitlines() if block else []):
        words = row.split()
        if len(words) >= 6:
            symbols.append(words[0][:1].upper() + words[0][1:].lower())
    return symbols


def last_cell(folder):
    """The cell of the end of the run (Å, rows a, b, c): the last row of <project>-1.cell, else &CELL of the input."""
    folder = Path(folder)
    file = folder / f'{PROJECT}-1.cell'
    if file.is_file():
        rows = [line.split() for line in file.read_text(encoding='utf-8', errors='replace').splitlines()
                if line.strip() and not line.lstrip().startswith('#')]
        if rows and len(rows[-1]) >= 11:
            v = [float(x) for x in rows[-1][2:11]]
            return (tuple(v[0:3]), tuple(v[3:6]), tuple(v[6:9]))
    given = folder / 'azimuth.inp'
    return _input_cell(given) if given.is_file() else None


def for_multiwfn(folder, text=None):
    """The wave function of the end of the run for Multiwfn: <project>-multiwfn.molden in the folder — [Cell] and [Nval]
    before the last Molden file (molden_files). Returns (path or None, a message for the user or '')."""
    from azimuth.i18n import tr

    folder = Path(folder)
    files = molden_files(folder)
    if not files:
        return None, ''
    cell = last_cell(folder)
    if cell is None:
        return None, tr('нет ячейки расчёта')
    molden = files[-1].read_text(encoding='utf-8', errors='replace')
    symbols = _molden_symbols(molden)
    unknown = sorted({s for s in symbols if s not in VALENCE})
    if not symbols or unknown:
        return None, tr('нет числа валентных электронов для {}').format(', '.join(unknown or ['[Atoms]']))
    if text is None and (folder / 'cp2k.out').is_file():
        text = (folder / 'cp2k.out').read_text(encoding='utf-8', errors='replace')
    counted = re.findall(r'Number of electrons:\s+(\d+)', text or '')
    total = sum(VALENCE[s] for s in symbols)
    if counted and int(counted[-1]) != total:  # another pseudopotential (or a charge): Multiwfn would be misled
        return None, tr('в расчёте {} электронов, а по псевдопотенциалам {}').format(counted[-1], total)
    order = list(dict.fromkeys(symbols))
    head = ['[Cell]'] + ['  '.join(f'{x:14.8f}' for x in row) for row in cell]
    head += ['[Nval]'] + [f'{s} {VALENCE[s]}' for s in order]
    path = folder / FOR_MULTIWFN
    path.write_text('\n'.join(head) + '\n' + molden, encoding='utf-8')
    return path, ''


# -- the frequencies at Γ ---------------------------------------------------------------------------------
def read_vibrations(text):
    """The modes of <project>-VIBRATIONS-1.mol of &VIBRATIONAL_ANALYSIS (Molden format): ([(symbol, (x, y, z) Å)],
    [Vibration]) — [FREQ] cm⁻¹ (negative: imaginary), [FR-COORD] in bohr, [FR-NORM-COORD] «vibration k» and a row
    dx dy dz per atom, [INT] km/mol when given; ValueError without frequencies or with rows that do not fit."""
    from modules.spectrum.readers.vibration_data import Vibration

    sections, name = {}, None
    for line in text.splitlines():
        m = re.match(r'\s*\[([^\]]+)\]', line)
        if m:
            name = m.group(1).strip().upper()
            sections[name] = []
        elif name is not None and line.strip():
            sections[name].append(line.split())
    freqs = [float(r[0]) for r in sections.get('FREQ', []) if r]
    if not freqs:
        raise ValueError('no [FREQ] in the file of the vibrations')
    bohr = 0.529177210903
    atoms = [(r[0][:1].upper() + r[0][1:].lower(), tuple(float(x) * bohr for x in r[1:4]))
             for r in sections.get('FR-COORD', []) if len(r) >= 4]
    vectors, current = [], None
    for r in sections.get('FR-NORM-COORD', []):
        if r[0].lower().startswith('vib'):
            current = []
            vectors.append(current)
        elif current is not None and len(r) >= 3:
            current.append(tuple(float(x) for x in r[:3]))
    intensities = [float(r[0]) for r in sections.get('INT', []) if r]
    modes = []
    for k, f in enumerate(freqs):
        v = vectors[k] if k < len(vectors) else None
        if v is not None and len(v) != len(atoms):
            raise ValueError('a mode of the file has another number of atoms')
        modes.append(Vibration(k + 1, f, tuple(v) if v else None, intensities[k] if k < len(intensities) else None))
    return atoms, modes


def vibrations(folder):
    """read_vibrations of the file of a run (None without it)."""
    path = Path(folder) / f'{PROJECT}-VIBRATIONS-1.mol'
    if not path.is_file():
        found = sorted(Path(folder).glob('*VIBRATIONS*.mol'))
        if not found:
            return None
        path = found[-1]
    return read_vibrations(path.read_text(encoding='utf-8', errors='replace'))

"""The output of pw.x (Quantum ESPRESSO): energies, the relaxation, the final cell (внутр. 2026-11-11, для Секстанта и
Спектра).

§1 THEORY pw.x prints each converged total energy on a line «! total energy = … Ry» (1 Ry = ½ hartree); the stress
    tensor with the pressure «P= … kbar»; the total force «Total force = … Ry/bohr»; for insulators «highest occupied
    level (ev)» or «highest occupied, lowest unoccupied level (ev)», for metals «the Fermi energy is … ev»; a relaxation
    counts its steps («number of bfgs steps»), ends «bfgs converged» and writes the structure between «Begin final
    coordinates» and «End final coordinates» (CELL_PARAMETERS — in Å, in bohr or in units of alat; ATOMIC_POSITIONS —
    crystal, angstrom, bohr or alat). A finished run prints «JOB DONE.»; an error is a block between lines of «%».
§2 ALGORITHM
    read(text): the lines above by regular expressions; the cell of the input (CELL_PARAMETERS of the input echo is not
    printed — the «crystal axes» in units of alat with «lattice parameter (alat)» in bohr) for a run without final
    coordinates; final_crystal(result) — the relaxed cell and atoms as a crystal of group P 1.
§4 SPECIFICATION
    is_qe(text) -> bool; Result(version, calculation, nat, energies (Ry), energy (Ry), energy_hartree, highest, lowest,
    fermi (eV), pressures (kbar), forces (Ry/bohr), steps, converged, done, error, cell (3 × 3 Å), atoms [(symbol,
    (fx, fy, fz))], enthalpy (Ry)); read(text) -> Result; final_crystal(result, title) -> crystal.Crystal or None.
    Runs(text) — the texts of the runs of pw.x one after another (the steps of one job, «Program PWSCF»);
    bands(text) -> Bands(k (Å⁻¹ … in 2π/alat as printed), energies [[eV] per k-point]) of the run of calculation 'bands'
    (verbosity 'high': «k = … bands (ev):» and the eigenvalues, which may run together as «-10.1234-9.8765»);
    read_dos(text) -> Dos(energies, dos, integrated, fermi) of the file of dos.x («# E (eV) dos(E) Int dos(E)
    EFermi = … eV»).
    The phonons at Γ (task «Частоты (точка Γ)»: pw.x, ph.x, dynmat.x in one output): phonons(folder) -> Phonons(atoms
    [(symbol, (x, y, z) Å)], modes [Vibration, intensity km/mol], epsilon (3 × 3, ε∞ of ph.x with epsil, or None),
    born [(atom, symbol, mean Z*)] of the last block) — the modes of the Molden file of dynmat.x (filmol,
    qe_inputs.PHONON_FILE; [FR-COORD] in bohr), the IR activities of its table «# mode [cm-1] [THz] IR» in (D/Å)²/amu
    times IR_KM_MOL; None without that file. input_cell(folder) -> the rows of CELL_PARAMETERS angstrom of scf.in.
    The phonon branches and density of states (task «Фононные ветви и плотность состояний»: matdyn.x):
    read_branches(text) -> [[ν, cm⁻¹] per q of the path] of the file flfrq («&plot nbnd= N, nks= M /», then each q and
    its N frequencies); read_phdos(text) -> ([ν], [g(ν)]) of the file fldos (the first two columns, «#» lines skipped).
§7 TESTS
    tests/spectrum/test_qe_reader.py — real outputs of pw.x 7.6 (tests/data/qe); test_qe_phonons.py — of ph.x and
    dynmat.x 7.6 (silicon, rock salt).
"""

from dataclasses import dataclass, field
import re

BOHR = 0.529177210903  # Å (CODATA 2018)
RY_HARTREE = 0.5

_FLOAT = r'[-+]?\d+\.?\d*(?:[EeDd][-+]?\d+)?'


@dataclass
class Result:
    version: str = ''
    calculation: str = ''
    nat: int = 0
    energies: list = field(default_factory=list)
    energy: float | None = None
    energy_hartree: float | None = None
    highest: float | None = None
    lowest: float | None = None
    fermi: float | None = None
    pressures: list = field(default_factory=list)
    forces: list = field(default_factory=list)
    steps: int = 0
    converged: bool = False
    done: bool = False
    error: str = ''
    cell: tuple | None = None
    atoms: tuple = ()
    enthalpy: float | None = None


def is_qe(text):
    return 'Program PWSCF' in text[:20000]


def _f(text):
    return float(text.replace('D', 'E').replace('d', 'e'))


def _initial(text):
    """The cell (Å) of the start: «crystal axes» in units of alat."""
    alat = re.search(r'lattice parameter \(alat\)\s*=\s*(' + _FLOAT + r')\s*a\.u\.', text)
    axes = re.findall(r'a\((\d)\) = \(\s*(' + _FLOAT + r')\s+(' + _FLOAT + r')\s+(' + _FLOAT + r')\s*\)', text)
    if not alat or len(axes) < 3:
        return None
    scale = _f(alat.group(1)) * BOHR
    rows = {int(k): tuple(_f(x) * scale for x in v) for k, *v in axes[:3]}
    return tuple(rows[k] for k in (1, 2, 3))


def _block(lines, start, header):
    """The rows of a block after its header line (until an empty line or another header)."""
    rows = []
    for line in lines[start + 1:]:
        words = line.split()
        if not words or words[0].isupper() and words[0] in ('ATOMIC_POSITIONS', 'CELL_PARAMETERS', 'End'):
            break
        rows.append(words)
    return rows


def _final(text, initial):
    begin = text.rfind('Begin final coordinates')
    if begin < 0:
        return None, ()
    end = text.find('End final coordinates', begin)
    lines = text[begin:end if end > 0 else None].splitlines()
    cell, atoms = initial, []
    alat = re.search(r'lattice parameter \(alat\)\s*=\s*(' + _FLOAT + r')\s*a\.u\.', text)
    alat = _f(alat.group(1)) * BOHR if alat else None
    for k, line in enumerate(lines):
        if line.startswith('CELL_PARAMETERS'):
            unit = line.lower()
            rows = [tuple(_f(x) for x in w[:3]) for w in _block(lines, k, line)[:3]]
            if 'bohr' in unit:
                rows = [tuple(x * BOHR for x in r) for r in rows]
            elif 'alat' in unit:
                found = re.search(r'alat\s*=\s*(' + _FLOAT + r')', line)
                scale = _f(found.group(1)) * BOHR if found else alat
                rows = [tuple(x * scale for x in r) for r in rows]
            cell = tuple(rows)
        if line.startswith('ATOMIC_POSITIONS'):
            unit = line.lower()
            for w in _block(lines, k, line):
                if len(w) >= 4:
                    atoms.append((w[0], tuple(_f(x) for x in w[1:4]), unit))
    if cell is None:
        return None, ()
    import numpy as np

    rows = np.array(cell, dtype=float)
    inverse = np.linalg.inv(rows)
    out = []
    for symbol, xyz, unit in atoms:
        if 'crystal' in unit:
            f = xyz
        else:
            scale = BOHR if 'bohr' in unit else (alat or 1.0) if 'alat' in unit else 1.0
            f = tuple(float(x) for x in np.array(xyz) * scale @ inverse)
        out.append((''.join(ch for ch in symbol if ch.isalpha())[:2].capitalize(), tuple(float(x) for x in f)))
    return cell, tuple(out)


def read(text):
    r = Result()
    found = re.search(r'Program PWSCF v\.(\S+)', text)
    r.version = found.group(1) if found else ''
    found = re.search(r"calculation\s*=\s*'([\w-]+)'", text)
    r.calculation = found.group(1) if found else ('vc-relax' if 'Begin final coordinates' in text and 'new unit-cell'
                                                  in text else 'relax' if 'bfgs' in text else 'scf')
    found = re.search(r'number of atoms/cell\s*=\s*(\d+)', text)
    r.nat = int(found.group(1)) if found else 0
    r.energies = [_f(x) for x in re.findall(r'^!\s+total energy\s*=\s*(' + _FLOAT + r')\s*Ry', text, re.M)]
    if r.energies:
        r.energy = r.energies[-1]
        r.energy_hartree = r.energy * RY_HARTREE
    pair = re.findall(r'highest occupied, lowest unoccupied level \(ev\):\s*(' + _FLOAT + r')\s+(' + _FLOAT + ')', text)
    if pair:
        r.highest, r.lowest = _f(pair[-1][0]), _f(pair[-1][1])
    else:
        high = re.findall(r'highest occupied level \(ev\):\s*(' + _FLOAT + ')', text)
        r.highest = _f(high[-1]) if high else None
    fermi = re.findall(r'the Fermi energy is\s*(' + _FLOAT + r')\s*ev', text)
    r.fermi = _f(fermi[-1]) if fermi else None
    r.pressures = [_f(x) for x in re.findall(r'P=\s*(' + _FLOAT + ')', text)]
    r.forces = [_f(x) for x in re.findall(r'Total force\s*=\s*(' + _FLOAT + ')', text)]
    steps = re.findall(r'number of bfgs steps\s*=\s*(\d+)', text)
    r.steps = int(steps[-1]) + 1 if steps else 0
    r.converged = 'convergence has been achieved' in text and ('bfgs converged' in text or 'relax' not in r.calculation)
    r.done = 'JOB DONE.' in text
    error = re.search(r'%{20,}\n(.*?)\n\s*%{20,}', text, re.S)
    r.error = ' '.join(error.group(1).split()) if error else ''
    enthalpy = re.findall(r'Final enthalpy\s*=\s*(' + _FLOAT + r')\s*Ry', text)
    r.enthalpy = _f(enthalpy[-1]) if enthalpy else None
    initial = _initial(text)
    cell, atoms = _final(text, initial)
    r.cell, r.atoms = (cell, atoms) if cell is not None else (initial, ())
    return r


def final_crystal(result, title='QE'):
    """The relaxed structure as a crystal of group P 1, or None (no final coordinates)."""
    if result.cell is None or not result.atoms:
        return None
    import numpy as np

    from modules.compass.chemistry import crystal as cr

    rows = np.array(result.cell, dtype=float)
    a, b, c = (float(np.linalg.norm(v)) for v in rows)

    def angle(u, v):
        return float(np.degrees(np.arccos(np.clip(u @ v / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1))))

    cell = cr.Cell(a, b, c, angle(rows[1], rows[2]), angle(rows[0], rows[2]), angle(rows[0], rows[1]))
    sites = tuple(cr.Site(f'{s}{k + 1}', s, *f) for k, (s, f) in enumerate(result.atoms))
    return cr.Crystal(title, cell, sites, (cr.operation('x, y, z'),), 'P 1')


def steps(text):
    """the geometries of a relax / vc-relax, the start first — [(energy in hartree or None, cell rows in Å, ((symbol,
    fractions), …))]. The start: the cell of «crystal axes» and the positions of the first «Cartesian axes» (alat
    units); then each ATOMIC_POSITIONS block printed after a step (with the CELL_PARAMETERS of a vc-relax before it), up
    to «Begin final coordinates» (its block repeats the last step; the final scf of a vc-relax is no step). The energy
    of a geometry — the «!» line of its scf, in turn. [] when the output has no start."""
    import numpy as np

    cell = _initial(text)
    if cell is None:
        return []
    alat = re.search(r'lattice parameter \(alat\)\s*=\s*(' + _FLOAT + r')\s*a\.u\.', text)
    alat = _f(alat.group(1)) * BOHR if alat else 1.0
    head = text.split('Begin final coordinates')[0]
    start = re.search(r'positions \(alat units\)\s*\n((?:\s+\d+\s+\S+\s+tau\(.*\n)+)', head)
    if not start:
        return []
    first = []
    inverse = np.linalg.inv(np.array(cell, dtype=float))
    for line in start.group(1).splitlines():
        m = re.search(r'\d+\s+(\S+)\s+tau\(\s*\d+\)\s*=\s*\(\s*(' + _FLOAT + r')\s+(' + _FLOAT + r')\s+(' + _FLOAT + ')', line)
        if m:
            xyz = np.array([_f(x) for x in m.groups()[1:]]) * alat
            first.append((_symbol(m.group(1)), tuple(float(x) for x in xyz @ inverse)))
    energies = [_f(x) * RY_HARTREE for x in re.findall(r'^!\s+total energy\s*=\s*(' + _FLOAT + r')\s*Ry', head, re.M)]
    found = [(cell, tuple(first))]
    lines = head.splitlines()
    for k, line in enumerate(lines):
        if line.startswith('CELL_PARAMETERS'):
            rows = [tuple(_f(x) for x in w[:3]) for w in _block(lines, k, line)[:3]]
            unit = line.lower()
            if 'bohr' in unit:
                rows = [tuple(x * BOHR for x in r) for r in rows]
            elif 'alat' in unit:
                given = re.search(r'alat\s*=\s*(' + _FLOAT + r')', line)
                scale = _f(given.group(1)) * BOHR if given else alat
                rows = [tuple(x * scale for x in r) for r in rows]
            cell = tuple(rows)
        elif line.startswith('ATOMIC_POSITIONS'):
            unit = line.lower()
            inverse = np.linalg.inv(np.array(cell, dtype=float))
            atoms = []
            for w in _block(lines, k, line):
                if len(w) < 4:
                    continue
                xyz = np.array([_f(x) for x in w[1:4]])
                if 'crystal' not in unit:
                    xyz = (xyz * (BOHR if 'bohr' in unit else alat if 'alat' in unit else 1.0)) @ inverse
                atoms.append((_symbol(w[0]), tuple(float(x) for x in xyz)))
            found.append((cell, tuple(atoms)))
    return [(energies[i] if i < len(energies) else None, c, a) for i, (c, a) in enumerate(found)]


def _symbol(label):
    return ''.join(ch for ch in label if ch.isalpha())[:2].capitalize()


# -- the steps of one job, the bands, the density of states --------------------------------------------------
@dataclass
class Bands:
    k: list = field(default_factory=list)
    energies: list = field(default_factory=list)


@dataclass
class Dos:
    energies: list = field(default_factory=list)
    dos: list = field(default_factory=list)
    integrated: list = field(default_factory=list)
    fermi: float | None = None


def runs(text):
    """The texts of the runs of pw.x in one output, in their order (the text before the first one is dropped)."""
    parts = text.split('Program PWSCF')
    return ['Program PWSCF' + p for p in parts[1:]]


def bands(text):
    """The eigenvalues of the band run (the last run with «End of band structure calculation»)."""
    run = next((r for r in reversed(runs(text)) if 'End of band structure calculation' in r), '')
    found = Bands()
    if not run:
        return found
    lines = run[run.index('End of band structure calculation'):].split('\n')
    k = 0
    while k < len(lines):
        line = lines[k]
        if 'bands (ev)' in line and 'k =' in line:
            head = line.split('k =', 1)[1].split('(')[0]
            found.k.append(tuple(float(v) for v in re.findall(r'-?\d+\.\d+', head)[:3]))
            values = []
            k += 1
            while k < len(lines) and not lines[k].strip():
                k += 1
            while k < len(lines) and lines[k].strip() and not lines[k].lstrip().startswith(('k =', 'occupation')):
                values += [float(v) for v in re.findall(r'-?\d+\.\d+', lines[k])]
                k += 1
            found.energies.append(values)
            continue
        if found.k and ('Writing' in line or 'highest' in line or 'the Fermi energy' in line):
            break
        k += 1
    return found


def read_dos(text):
    found = Dos()
    for line in text.split('\n'):
        if line.startswith('#'):
            m = re.search(r'EFermi\s*=\s*(' + _FLOAT + ')', line)
            if m:
                found.fermi = _f(m.group(1))
            continue
        words = line.split()
        if len(words) >= 3:
            try:
                e, d, n = (_f(w) for w in words[:3])
            except ValueError:
                continue
            found.energies.append(e)
            found.dos.append(d)
            found.integrated.append(n)
    return found


# an IR activity of (D/Å)²/amu in km/mol: N_A / (12 ε₀ c²) |∂μ/∂Q|² (SI), CODATA 2018 — 42.2561
_DEBYE_ANGSTROM = 1e-21 / 299792458.0 / 1e-10  # C
IR_KM_MOL = 6.02214076e23 / (12 * 8.8541878128e-12 * 299792458.0 ** 2) * _DEBYE_ANGSTROM ** 2 / 1.66053906660e-27 / 1e3


@dataclass
class Phonons:
    atoms: list
    modes: list
    epsilon: tuple | None = None
    born: list = field(default_factory=list)


def dynmat_ir(text):
    """{mode: IR activity, (D/Å)²/amu} of the last table of dynmat.x («# mode [cm-1] [THz] IR»)."""
    found = {}
    parts = text.split('# mode')
    if len(parts) < 2:
        return found
    for line in parts[-1].splitlines()[1:]:
        cells = line.split()
        if len(cells) < 4 or not cells[0].isdigit():
            if found:
                break
            continue
        found[int(cells[0])] = float(cells[3])
    return found


def dielectric(text):
    """ε∞ — the last «Dielectric constant in cartesian axis» of ph.x (three rows «( a b c )»), or None."""
    at = text.rfind('Dielectric constant in cartesian axis')
    if at < 0:
        return None
    rows = re.findall(r'^\s*\(\s*(' + _FLOAT + r')\s+(' + _FLOAT + r')\s+(' + _FLOAT + r')\s*\)', text[at:], re.M)[:3]
    return tuple(tuple(_f(v) for v in row) for row in rows) if len(rows) == 3 else None


def born_charges(text):
    """[(atom, symbol, mean Z*)] — the effective charges of the last block of ph.x («atom N El Mean Z*: z»)."""
    found = re.findall(r'^\s*atom\s+(\d+)\s+(\S+)\s+Mean Z\*:\s*(' + _FLOAT + ')', text, re.M)
    if not found:
        return []
    count = max(int(n) for n, _, _ in found)
    return [(int(n), symbol, _f(z)) for n, symbol, z in found[-count:]]


def input_cell(folder):
    """The rows (Å) of CELL_PARAMETERS angstrom of the input of the run (scf.in, else pw.in), or None."""
    from pathlib import Path

    for name in ('scf.in', 'pw.in'):
        path = Path(folder) / name
        if not path.is_file():
            continue
        lines = path.read_text(encoding='utf-8', errors='replace').splitlines()
        for k, line in enumerate(lines):
            if line.strip().upper().startswith('CELL_PARAMETERS') and 'angstrom' in line.lower():
                return tuple(tuple(float(v) for v in row.split()[:3]) for row in lines[k + 1:k + 4])
    return None


def phonons(folder, text=None):
    """Phonons of a run of the task «Частоты (точка Γ)» in folder (its output pw.out, or text), None without the
    Molden file of dynmat.x."""
    from dataclasses import replace
    from pathlib import Path

    from modules.sextant.qe_inputs import PHONON_FILE
    from modules.spectrum.readers.cp2k import read_vibrations

    path = Path(folder) / PHONON_FILE
    if not path.is_file():
        return None
    atoms, modes = read_vibrations(path.read_text(encoding='utf-8', errors='replace'))
    if text is None:
        out = Path(folder) / 'pw.out'
        text = out.read_text(encoding='utf-8', errors='replace') if out.is_file() else ''
    ir = dynmat_ir(text)
    modes = [replace(m, intensity=ir[m.index] * IR_KM_MOL) if m.index in ir else m for m in modes]
    return Phonons(atoms, modes, dielectric(text), born_charges(text))


def read_branches(text):
    """[[frequencies, cm⁻¹] of each q] of the file flfrq of matdyn.x; [] without its header. After «&plot nbnd= N,
    nks= M /» each q has a line of its own (its coordinates — four numbers in QE 7.6), then its N frequencies over one
    or more lines."""
    head = re.search(r'&plot\s+nbnd\s*=\s*(\d+)\s*,\s*nks\s*=\s*(\d+)', text)
    if not head:
        return []
    nbnd, nks = int(head.group(1)), int(head.group(2))
    lines = [line for line in text[text.index('/', head.end()) + 1:].splitlines() if line.strip()]
    found, k = [], 0
    while k < len(lines) and len(found) < nks:
        k += 1  # the line of the q
        values = []
        while k < len(lines) and len(values) < nbnd:
            values += [_f(v) for v in re.findall(_FLOAT, lines[k])]
            k += 1
        if len(values) != nbnd:
            break
        found.append(values)
    return found


def read_phdos(text):
    """(frequencies cm⁻¹, density of states) of the file fldos of matdyn.x."""
    nu, g = [], []
    for line in text.splitlines():
        cells = line.split()
        if len(cells) < 2 or line.lstrip().startswith('#'):
            continue
        try:
            nu.append(_f(cells[0]))
            g.append(_f(cells[1]))
        except ValueError:
            continue
    return nu, g

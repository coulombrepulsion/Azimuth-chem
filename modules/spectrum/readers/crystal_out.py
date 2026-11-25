"""The output of CRYSTAL (CRYSTAL14, CRYSTAL17, CRYSTAL23; Dovesi et al.) and of its program properties with TOPOND:
the energy, the optimization with its steps, the external pressure, the band gap, the elastic constants, the critical
points of the electron density.
§1 THEORY CRYSTAL computes a periodic system with atom-centred Gaussian functions (Hartree–Fock or DFT). Its output
    prints the space group and the geometry of the input («LATTICE PARAMETERS … - CONVENTIONAL CELL», then the primitive
    cell), and every geometry it computes as a block «LATTICE PARAMETERS (ANGSTROMS AND DEGREES) - BOHR = …» — the
    primitive cell (a, b, c, α, β, γ) and «ATOMS IN THE ASYMMETRIC UNIT … - ATOMS IN THE UNIT CELL», the atoms of the
    primitive cell in its fractions (T — of the asymmetric unit, F — its images; the element in the second column, the
    atomic number in the first: plus 200 with a pseudopotential). The first such block is «GEOMETRY FOR WAVE FUNCTION»;
    its energy — «== SCF ENDED - CONVERGENCE ON ENERGY E(AU)»; an optimization (OPTGEOM) prints «… OPTIMIZATION - POINT
    n» before each next geometry and «TOTAL ENERGY(DFT)(AU)( k) E» (or (HF)) after it, ends «* OPT END - CONVERGED *
    E(AU): … POINTS n *» and prints «FINAL OPTIMIZED GEOMETRY» (the primitive cell) and «CRYSTALLOGRAPHIC CELL» — the
    conventional cell and the atoms of the primitive cell in its fractions. EXTPRESS (a hydrostatic pressure,
    hartree/bohr³ in the input) is echoed as «EXTERNAL STRESS APPLIED (HARTREE/BOHR^3)» — the diagonal of the stress
    tensor, 1 hartree/bohr³ = 29421 GPa; each gradient prints the pressure from the stress tensor «PRESSURE IN
    GIGAPASCAL» and «ENTHALPY». A band gap: «DIRECT/INDIRECT ENERGY BAND GAP: x eV» at each SCF cycle (the last one
    counts); a metal — «POSSIBLY CONDUCTING STATE». ELASTCON prints «SYMMETRIZED ELASTIC CONSTANTS FOR … CASE, IN GPa» —
    the upper triangle of the 6 × 6 matrix in Voigt notation (numbers may run together: «240.9095-240.9095») — and «K_V
    G_V K_R G_R K_H G_H E_H v_H» (bulk, shear, Young moduli by Voigt, Reuss and Hill, the Poisson ratio). A finished run
    ends «EEEEEEEEEE TERMINATION»; an error — «ERROR **** …». TOPOND (Gatti; the program properties of CRYSTAL, keyword
    TOPO) searches the critical points of ρ: each «CP N. k» with «CP TYPE : (3,-1)» (bond: (3,−1); ring (3,+1); cage
    (3,+3); nuclear attractor (3,−3)), «COORD FRACT. CONV. CELL», «PROPERTIES (RHO,GRHO,LAP)», «KINETIC ENERGY DENSITIES
    (G,K)», «VIRIAL DENSITY» (V), «ELF(PAA)», «ELLIPTICITY» and the cluster of atoms around it (the nearest first:
    number, cell, atomic number, distance in Å). The energy density H = G + V; |V|/G < 1 — closed shells, 1 < |V|/G < 2
    — intermediate, > 2 — shared (Espinosa et al., J. Chem. Phys. 117 (2002) 5529); all quantities in atomic units.
§2 ALGORITHM
    read(text): the lines above by regular expressions. steps(text): the geometry blocks before «FINAL OPTIMIZED
    GEOMETRY» with their energies in turn — the first that of «SCF ENDED», each next the first «TOTAL ENERGY(…)(AU)( k)»
    after it; a run of ELASTCON or FREQCALC (strained or displaced cells, not steps) gives []. The cell rows of a step —
    crystal.Cell(a, b, c, α, β, γ).vectors() (a along x, as the cells of Compass). final_crystal(result): the
    crystallographic cell with the atoms of the asymmetric unit and the operations of its space group (space_groups.find
    of the symbol CRYSTAL prints, «P 21/C», «C M C A»), else the primitive cell in P 1. topond(text) -> [CriticalPoint].
§4 SPECIFICATION
    is_crystal(text), is_topond(text) -> bool; Result(version, title, space_group, energies (hartree), energy, steps,
    converged, done, error, gap (eV), gap_kind, conducting, pressure (GPa, from the stress tensor, the last), external
    (GPa, EXTPRESS), enthalpy (hartree), volume (Å³), cell (a, b, c, α, β, γ of the primitive cell), atoms ((symbol,
    fractions), …), conventional (the six of the crystallographic cell or None), unique (atoms of the asymmetric unit in
    its fractions), elastic (6 × 6, GPa, or None), moduli {K_V, G_V, K_R, G_R, K_H, G_H, E_H, v_H} or {}); read(text) ->
    Result; steps(text) -> [(energy hartree | None, cell rows Å, ((symbol, fractions), …))]; final_crystal(result,
    title) -> crystal.Crystal | None; CriticalPoint(number, kind, fractions, rho, laplacian, g, k, v, elf, ellipticity,
    neighbours ((atom number, symbol, distance Å), …)), .h, .ratio; topond(text) -> [CriticalPoint].
§7 TESTS
    tests/spectrum/test_crystal_reader.py — real outputs (tests/data/crystal: Cl₂ at 10 GPa, CRYSTAL17,
    PBE0; the elastic tensor of RUBSUD at 20 GPa; TOPOND of CRYSTAL14 for bromobenzene), cut to the part CRYSTAL
    wrote."""

from dataclasses import dataclass, field
import re

GPA_PER_AU = 29421.02648438959  # 1 hartree/bohr³ in GPa (CODATA 2018; CRYSTAL prints 29421)
_FLOAT = r'[-+]?\d*\.?\d+(?:[EeDd][-+]?\d+)?'
_ELEMENTS = ('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr '
             'Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W '
             'Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn').split()


# the functionals as CRYSTAL prints them: (exchange, correlation, % of Fock exchange) -> the usual name
_METHODS = {('PERDEW-BURKE-ERNZERHOF', 'PERDEW-BURKE-ERNZERHOF', 25): 'PBE0',
            ('PERDEW-BURKE-ERNZERHOF', 'PERDEW-BURKE-ERNZERHOF', 0): 'PBE',
            ('BECKE 88', 'LEE-YANG-PARR', 20): 'B3LYP', ('BECKE 88', 'LEE-YANG-PARR', 0): 'BLYP',
            ('PBESOL', 'PBESOL', 0): 'PBEsol', ('PBESOL', 'PBESOL', 25): 'PBEsol0'}
# 2002 (ITA 5th ed.): five symbols with a glide «e» — CRYSTAL prints the old ones
_RENAMED = {'abm2': 'Aem2', 'aba2': 'Aea2', 'cmca': 'Cmce', 'cmma': 'Cmme', 'ccca': 'Ccce'}


@dataclass
class Result:
    version: str = ''
    title: str = ''
    space_group: str = ''
    energies: list = field(default_factory=list)
    energy: float | None = None
    steps: int = 0
    converged: bool = False
    optimization: bool = False
    done: bool = False
    error: str = ''
    gap: float | None = None
    gap_kind: str = ''
    conducting: bool = False
    pressure: float | None = None
    external: float | None = None
    enthalpy: float | None = None
    volume: float | None = None
    cell: tuple | None = None
    atoms: tuple = ()
    conventional: tuple | None = None
    unique: tuple = ()
    primitive_unique: tuple = ()  # the atoms T of the last geometry (the primitive cell)
    elastic: tuple | None = None
    moduli: dict = field(default_factory=dict)
    method: str = ''
    basis: str = ''  # the name after BASISSET of the input; '' — written by hand
    basis_ao: int | None = None  # NUMBER OF AO


@dataclass(frozen=True)
class CriticalPoint:
    number: int
    kind: str  # '(3,-1)', …
    fractions: tuple
    rho: float
    laplacian: float
    g: float | None = None
    k: float | None = None
    v: float | None = None
    elf: float | None = None
    ellipticity: float | None = None
    neighbours: tuple = ()

    @property
    def h(self):
        return None if self.g is None or self.v is None else self.g + self.v

    @property
    def ratio(self):
        return None if self.g in (None, 0) or self.v is None else abs(self.v) / self.g


def _f(text):
    return float(text.replace('D', 'E').replace('d', 'e'))


def _numbers(text):
    return [_f(x) for x in re.findall(_FLOAT, text)]


_BANNER = re.compile(r'\*\s+CRYSTAL\d\d\s+\*')


def _banner(text):
    """Where the banner «* CRYSTAL17 *» ends, or None. The script of
    the queue and the echo of the input with its basis sets come first — the banner was at 55 000 characters, past the
    old 30 000, and the file was taken for ORCA; now the first 500 000 characters are looked at."""
    found = _BANNER.search(text[:500000])
    return None if found is None else found.end()


def is_topond(text):
    end = _banner(text)
    return end is not None and 'CRYSTAL - PROPERTIES' in text[:end + 60000]


def is_crystal(text):
    return _banner(text) is not None and not is_topond(text)


def symbol(word, number=None):
    """'CL' -> 'Cl'; the atomic number (minus 200 or 100 of a pseudopotential) when the word is not an element."""
    name = word.strip().capitalize()
    if name in _ELEMENTS:
        return name
    if number is not None:
        z = int(number) % 100
        if 1 <= z <= len(_ELEMENTS):
            return _ELEMENTS[z - 1]
    return name


_ATOM = re.compile(r'^\s*\d+\s+([TF])\s+(\d+)\s+([A-Za-z]{1,2})\s+(' + _FLOAT + r')\s+(' + _FLOAT + r')\s+(' + _FLOAT
                   + r')\s*$')


def _geometry(lines, start):
    """The block of a geometry from its «LATTICE PARAMETERS (ANGSTROMS AND DEGREES) - BOHR» line: (six, volume,
    ((symbol, fractions), …), ((symbol, fractions) of the asymmetric unit), the index after it)."""
    six, volume, atoms, unique = None, None, [], []
    k = start + 1
    while k < len(lines) and k < start + 8:
        line = lines[k]
        found = re.search(r'VOLUME=\s*(' + _FLOAT + ')', line)
        if found:
            volume = _f(found.group(1))
        if re.match(r'^\s+A\s+B\s+C\s+ALPHA', line) and k + 1 < len(lines):
            values = _numbers(lines[k + 1])
            if len(values) >= 6:
                six = tuple(values[:6])
            k += 2
            break
        k += 1
    while k < len(lines) and 'ATOMS IN THE ASYMMETRIC UNIT' not in lines[k] and k < start + 14:
        k += 1
    k += 1
    while k < len(lines):
        line = lines[k]
        match = _ATOM.match(line)
        if match:
            xyz = (_f(match.group(4)), _f(match.group(5)), _f(match.group(6)))
            name = symbol(match.group(3), match.group(2))
            atoms.append((name, xyz))
            if match.group(1) == 'T':
                unique.append((name, xyz))
        elif atoms and line.strip() and not line.strip().startswith('*'):
            break
        elif atoms and not line.strip():
            break
        k += 1
    return six, volume, tuple(atoms), tuple(unique), k


def _gap(text):
    found = re.findall(r'(DIRECT|INDIRECT) ENERGY BAND GAP:\s*(' + _FLOAT + r')\s*eV', text)
    return (_f(found[-1][1]), found[-1][0].lower()) if found else (None, '')


def _elastic(text):
    begin = text.rfind('SYMMETRIZED ELASTIC CONSTANTS')
    if begin < 0:
        return None
    rows = []
    for line in text[begin:].splitlines()[1:]:
        if '|' not in line:
            if rows:
                break
            continue
        rows.append(_numbers(line.replace('|', ' ')))
        if len(rows) == 6:
            break
    if len(rows) != 6 or any(len(r) != 6 - i for i, r in enumerate(rows)):
        return None
    matrix = [[0.0] * 6 for _ in range(6)]
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            matrix[i][i + j] = matrix[i + j][i] = value
    return tuple(tuple(r) for r in matrix)


def _moduli(text):
    found = re.search(r'K_V\s+G_V\s+K_R\s+G_R\s+K_H\s+G_H\s+E_H\s+v_H\s*\n\s*\n?\s*((?:' + _FLOAT + r'\s+){7}' + _FLOAT
                      + ')', text)
    if not found:
        return {}
    values = _numbers(found.group(1))
    return dict(zip(('K_V', 'G_V', 'K_R', 'G_R', 'K_H', 'G_H', 'E_H', 'v_H'), values))


def _external(text):
    """The hydrostatic pressure of EXTPRESS (GPa): the mean of the diagonal of «EXTERNAL STRESS» (hartree/bohr³)."""
    begin = text.find('EXTERNAL STRESS APPLIED (HARTREE/BOHR^3)')
    if begin < 0:
        return None
    rows = []
    for line in text[begin:].splitlines()[1:12]:
        if 'ORDER' in line or not re.search(r'\d[EeDd][-+]\d', line):
            continue
        values = _numbers(line)
        if len(values) == 3:
            rows.append(values)
        if len(rows) == 3:
            break
    if len(rows) != 3:
        return None
    return (rows[0][0] + rows[1][1] + rows[2][2]) / 3 * GPA_PER_AU


def _conventional(text):
    begin = text.rfind('CRYSTALLOGRAPHIC CELL (VOLUME=')
    if begin < 0:
        return None, ()
    lines = text[begin:].splitlines()
    six = None
    for k, line in enumerate(lines[:4]):
        if re.match(r'^\s+A\s+B\s+C\s+ALPHA', line) and k + 1 < len(lines):
            values = _numbers(lines[k + 1])
            six = tuple(values[:6]) if len(values) >= 6 else None
    unique = []
    for line in lines[4:]:
        match = _ATOM.match(line)
        if match:
            if match.group(1) == 'T':
                unique.append((symbol(match.group(3), match.group(2)),
                               (_f(match.group(4)), _f(match.group(5)), _f(match.group(6)))))
        elif unique and not line.strip():
            break
    return six, tuple(unique)


def read(text):
    r = Result()
    found = re.search(r'\*\s+(CRYSTAL\d\d)\s+\*', text)
    r.version = found.group(1) if found else ''
    found = re.search(r'public\s*:\s*([\w.]+)', text[:5000])
    if found:
        r.version += ' ' + found.group(1)
    found = re.search(r'EEEEEEEEEE STARTING.*\n\s*(.+)', text)
    r.title = found.group(1).strip() if found else ''
    found = re.search(r'SPACE GROUP \([^)]*\)\s*:\s*(.+)', text)
    r.space_group = found.group(1).strip() if found else ''
    found = re.search(r'\(EXCHANGE\)\[CORRELATION\] FUNCTIONAL:\(([^)]*)\)\[([^\]]*)\]', text)
    if found:
        exchange, correlation = found.group(1).strip(), found.group(2).strip()
        share = re.search(r'PERCENTAGE OF FOCK EXCHANGE\s*(' + _FLOAT + ')', text)
        share = _f(share.group(1)) if share else 0.0
        r.method = 'HSE06' if 'HSE06' in exchange else _METHODS.get(
            (exchange, correlation, round(share)), f'{exchange} / {correlation}' + (f', {share:g} % HF' if share else ''))
    elif 'HARTREE-FOCK' in text[:200000] or 'TOTAL ENERGY(HF)' in text:
        r.method = 'Hartree–Fock'
    # a basis of the library is named by BASISSET in the input echoed
    # before the banner; one written by hand has no name in the output — only its size
    found = re.search(r'^\s*BASISSET\s*\n\s*(\S+)', text[:max(_banner(text) or 0, 0) or 200000], re.M)
    r.basis = found.group(1).strip() if found else ''
    head = text[:_banner(text) or 200000]
    for keyword, name in (('HF3C', 'HF-3c'), ('PBEH3C', 'PBEh-3c'), ('HSE3C', 'HSE-3c')):  # the composite methods
        if re.search(r'^\s*' + keyword + r'\s*$', head, re.M):
            r.method = name
    found = re.search(r'NUMBER OF AO\s+(\d+)', text)
    r.basis_ao = int(found.group(1)) if found else None
    first = re.search(r'== SCF ENDED - CONVERGENCE ON ENERGY\s+E\(AU\)\s*(' + _FLOAT + ')', text)
    energies = [_f(first.group(1))] if first else []
    energies += [_f(x) for x in re.findall(r'TOTAL ENERGY\((?:DFT|HF)\)\(AU\)\(\s*\d+\)\s*(' + _FLOAT + r')\s+DE \(AU\)',
                                           text)]
    r.energies = energies
    r.optimization = 'OPTIMIZATION - POINT' in text or 'OPT END' in text
    done = re.search(r'\* OPT END - (CONVERGED|FAILED)[^*]*\*\s*E\(AU\):\s*(' + _FLOAT + r')\s+POINTS\s+(\d+)', text)
    if done:
        r.converged = done.group(1) == 'CONVERGED'
        r.energy = _f(done.group(2))
        r.steps = int(done.group(3))
    else:
        r.energy = energies[-1] if energies else None
        r.steps = len(re.findall(r'OPTIMIZATION - POINT\s+\d+', text))
    r.done = 'EEEEEEEEEE TERMINATION' in text
    error = re.findall(r'ERROR \*+\s*(.+)', text)
    r.error = error[-1].strip() if error else ''
    r.gap, r.gap_kind = _gap(text)
    r.conducting = 'POSSIBLY CONDUCTING STATE' in text[-200000:] and r.gap is None
    pressures = re.findall(r'PRESSURE IN GIGAPASCAL:\s*(' + _FLOAT + ')', text)
    r.pressure = _f(pressures[-1]) if pressures else None
    enthalpies = re.findall(r'ENTHALPY:\s*(' + _FLOAT + ')', text)
    r.enthalpy = _f(enthalpies[-1]) if enthalpies else None
    r.external = _external(text)
    lines = text.splitlines()
    last = None
    for k, line in enumerate(lines):
        if 'LATTICE PARAMETERS (ANGSTROMS AND DEGREES) - BOHR' in line:
            last = k
    if last is not None:
        six, volume, atoms, unique, _ = _geometry(lines, last)
        r.cell, r.volume, r.atoms, r.primitive_unique = six, volume, atoms, unique
    r.conventional, r.unique = _conventional(text)
    r.elastic = _elastic(text)
    r.moduli = _moduli(text)
    return r


def steps(text):
    """The geometries of an optimization, the start first: [(energy | None, cell rows Å, ((symbol, fractions), …))]."""
    from modules.compass.chemistry import crystal as cr

    if 'ELASTCON' in text and 'ELASTIC CONSTANTS' in text or 'FREQCALC' in text[:400000] and 'OPT END' not in text:
        return []
    head = text.split('FINAL OPTIMIZED GEOMETRY')[0]
    lines = head.splitlines()
    blocks = [k for k, line in enumerate(lines) if 'LATTICE PARAMETERS (ANGSTROMS AND DEGREES) - BOHR' in line]
    out = []
    for n, k in enumerate(blocks):
        six, _volume, atoms, _unique, end = _geometry(lines, k)
        if six is None or not atoms:
            continue
        upto = blocks[n + 1] if n + 1 < len(blocks) else len(lines)
        tail = '\n'.join(lines[end:upto])
        if n == 0:
            found = re.search(r'== SCF ENDED - CONVERGENCE ON ENERGY\s+E\(AU\)\s*(' + _FLOAT + ')', tail)
        else:
            found = re.search(r'TOTAL ENERGY\((?:DFT|HF)\)\(AU\)\(\s*\d+\)\s*(' + _FLOAT + ')', tail)
        energy = _f(found.group(1)) if found else None
        try:
            rows = cr.Cell(*six).vectors()
        except (TypeError, ValueError):
            continue
        out.append((energy, rows, atoms))
    return out


def _with_group(result, title, six, unique):
    """The crystal of the cell six in the space group of the output with the atoms unique — None when the group is not
    known or its atoms are not those of the cell printed."""
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import space_groups

    entry = space_groups.find(result.space_group)
    renamed = _RENAMED.get(result.space_group.lower().replace(' ', ''))
    if entry is None and renamed:
        entry = space_groups.find(renamed)
    if entry is None:
        return None
    try:
        cell = cr.Cell(*six).validate()
        operations = tuple(cr.operation(op) for op in space_groups.operations(entry))
        sites = tuple(cr.Site(f'{s}{k + 1}', s, *(round(x, 10) % 1.0 for x in f)) for k, (s, f) in enumerate(unique))
        crystal = cr.Crystal(title, cell, sites, operations, entry['short'].replace('_', ''), number=entry['number'])
        made = cr.unit_cell(crystal)
    except (ValueError, KeyError, TypeError):
        return None
    if len(made) != len(result.atoms):
        return None
    import numpy as np

    rows = np.array(cell.vectors(), dtype=float)
    given = np.array([f for _, f in result.atoms], dtype=float)
    for symbol_, *f, _label in made:  # each atom of the group at an atom of the output, the same element
        d = given - np.array(f)
        d -= np.round(d)
        dist = np.linalg.norm(d @ rows, axis=1)
        k = int(np.argmin(dist))
        if dist[k] > 0.05 or result.atoms[k][0] != symbol_:
            return None
    return crystal


_NAMED = re.compile(r'(?i)^(?:pob-?)?(?:[DT]ZVP\d*|[DT]ZVPP|SVP|QZVP|STO-\dG|def2-?\w+|cc-p\w+|6-31\S*|6-311\S*|'
                    r'(?:pob-)?[DT]ZVP-rev\d)$')


def basis_from_name(name):
    """The name of a basis set in the name of a file (CAFORM_DZVP2-PBE0_3.5GPa.out -> 'DZVP2'), or ''."""
    stem = re.sub(r'\.(out|outp|log|txt)$', '', str(name), flags=re.I)
    for token in re.split(r'[_\s]+', stem):
        for part in [token] + token.split('-'):
            if _NAMED.match(part):
                return part
    return ''


def final_crystal(result, title='CRYSTAL'):
    """The last structure: the crystallographic cell with its space group, or the primitive cell in P 1; None if the
    output has no geometry."""
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import space_groups

    if result.conventional is not None and result.unique and result.space_group:
        entry = space_groups.find(result.space_group)
        renamed = _RENAMED.get(result.space_group.lower().replace(' ', ''))
        if entry is None and renamed:
            entry = space_groups.find(renamed)
        if entry is not None:
            operations = tuple(cr.operation(op) for op in space_groups.operations(entry))
            sites = tuple(cr.Site(f'{s}{k + 1}', s, *(round(x, 10) % 1.0 for x in f))
                          for k, (s, f) in enumerate(result.unique))
            try:
                cell = cr.Cell(*result.conventional).validate()
            except ValueError:
                cell = None
            if cell is not None:
                return cr.Crystal(title, cell, sites, operations, entry['short'].replace('_', ''),
                                  number=entry['number'])
    if result.cell is None or not result.atoms:
        return None
    # a primitive lattice (P) — CRYSTAL prints no «CRYSTALLOGRAPHIC CELL», its cell is the primitive one; its asymmetric
    # unit (the atoms marked T) with the operations of the group, when they give back the atoms of the cell, one for one
    unique = result.primitive_unique
    if unique and result.space_group.strip().upper().startswith('P') and result.conventional is None:
        made = _with_group(result, title, result.cell, unique)
        if made is not None:
            return made
    sites = tuple(cr.Site(f'{s}{k + 1}', s, *(x % 1.0 for x in f)) for k, (s, f) in enumerate(result.atoms))
    return cr.Crystal(title, cr.Cell(*result.cell), sites, (cr.operation('x, y, z'),), 'P 1', number=1)


def topond(text):
    """The critical points of ρ found by TOPOND, in the order printed."""
    points = []
    parts = re.split(r'\n\s*CP N\.\s+(\d+)\s*\n', text)
    for k in range(1, len(parts) - 1, 2):
        number, body = int(parts[k]), parts[k + 1]

        def value(label, count=1):
            found = re.search(re.escape(label) + r'[^:\n]*:\s*((?:' + _FLOAT + r'\s*){' + str(count) + '})', body)
            return _numbers(found.group(1))[:count] if found else None

        kind = re.search(r'CP TYPE\s*:\s*(\(3,\s*[-+]?\d\))', body)
        fractions = value('COORD FRACT. CONV. CELL', 3)
        props = value('PROPERTIES (RHO,GRHO,LAP)', 3)
        if not kind or not props:
            continue
        kinetic = value('KINETIC ENERGY DENSITIES (G,K)', 2)
        virial = value('VIRIAL DENSITY')
        elf = value('ELF(PAA)')
        ellipticity = value('ELLIPTICITY')
        neighbours = []
        cluster = body.find('CLUSTER OF ATOMS AROUND THE CP')
        if cluster >= 0:
            for line in body[cluster:].splitlines()[2:]:
                words = line.split()
                if len(words) >= 9 and words[0].isdigit():
                    # NEW OLD CELL(3: may run together as «0-1») AT.NU. X Y Z DISTANCE
                    try:
                        neighbours.append((int(words[1]), symbol('', int(words[-5])), float(words[-1])))
                    except ValueError:
                        continue
                    if len(neighbours) == 6:
                        break
                elif neighbours and not line.strip():
                    break
        points.append(CriticalPoint(number, kind.group(1).replace(' ', ''), tuple(fractions or ()), props[0], props[2],
                                    kinetic[0] if kinetic else None, kinetic[1] if kinetic else None,
                                    virial[0] if virial else None, elf[0] if elf else None,
                                    ellipticity[0] if ellipticity else None, tuple(neighbours)))
    return points

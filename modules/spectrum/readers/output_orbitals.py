"""Orbitals printed in the outputs of GAMESS (US) / Firefly, NWChem and Q-Chem.

§1 THEORY
    As for an ORCA output (orbital_files.read_orca): the basis set and the coefficients of the orbitals in it are
    printed in the output, so the orbitals, the density and its analysis need no Molden or fchk file. The order
    of the functions of a shell and their normalization differ between programs; orbitals.select settles the
    normalization by the orthonormality of the orbitals (C^T S C = 1 within the rounding of the printed
    coefficients).
§2 ALGORITHM
    GAMESS: «ATOMIC BASIS SET» (per symmetry-unique atom, under its name; S P D F G and L = S + P shells), the last
    «EIGENVECTORS» block (energies, symmetries, rows «n NAME atom LABEL c…»; for UHF «----- ALPHA SET -----» and
    «----- BETA SET -----»), the occupied orbitals «NUMBER OF OCCUPIED ORBITALS (ALPHA|BETA) [KEPT IS] =» and the
    geometry before the orbitals (gamess.py); the core electrons of an ECP («ON ATOM n WITH ZCORE z», «… ARE THE SAME
    AS ATOM m») are taken from the nuclear charges of the Mulliken populations. The labels (S, X, Y, Z, XX, XY, …, XXX,
    …) give the Cartesian
    monomial of every row.
    NWChem (with «print "final vectors" "final vectors analysis"»): «Basis "ao basis" -> "ao basis" (cartesian |
    spherical)» per tag; «Final MO vectors» (global arrays «alpha evecs», «beta evecs»: rows = basis functions,
    columns = orbitals); occupations and energies from «Vector n Occ=… E=…» of «Final [Alpha|Beta] Molecular
    Orbital Analysis». Cartesian functions in the order xx, xy, xz, yy, yz, zz (x before y before z); spherical
    ones m = −l … +l, those of odd m > 0 with the Condon–Shortley sign (−1)^m against gto.solid_harmonic.
    Q-Chem (with «PRINT_GENERAL_BASIS true» and «PRINT_ORBITALS true»): «Basis set in general basis input format»
    ($basis, one block per atom ending with ****; S P D F G and SP shells), «RESTRICTED (RHF) | ALPHA | BETA
    MOLECULAR ORBITAL COEFFICIENTS» with «eigenvalues:» and rows «n symbol [k] label c…» (labels s, px, py, pz;
    Cartesian dxx …, pure «d 1» … «d 5» = m −2 … +2, f m −3 … +3), the numbers of electrons «There are a alpha and
    b beta electrons»; the geometry is the last «Standard Nuclear Orientation» (qchem.py).
§3 APPLICATIONS
    orbital_files.read_orbitals (kind 'gamess' | 'nwchem' | 'qchem'), so the results of these programs open their
    orbitals in Spectrum and in the drawer of Compass.
§4 SPECIFICATION
    read_gamess_orbitals(text), read_nwchem_orbitals(text), read_qchem_orbitals(text) -> orbitals.OrbitalSet;
    ValueError when the output has no orbitals or they do not fit the basis. has_orbitals(text) -> bool.
§5 PROCEDURES - below.
§6 NOTES
    Verified 2026-10-26 on the cclib test data: GAMESS (US) 2017 dvb_sp, dvb_un_sp (s, p) and MoOCl4-sp
    (Cartesian d on Mo, O; several centres, so the order and the normalization of d are fixed by the orthonormality),
    NWChem 7.0 dvb_sp_ks, dvb_un_sp_ks (s, p), Q-Chem 5.4 dvb_sp, dvb_sp_un (s, p) and C_bigbasis (pure d, f, g on
    one atom). NWChem 7.3 formaldehyde B3LYP/cc-pVTZ spherical (tests/data/spherical, 2026-11-22): the order m = −l … +l and
    the sign (−1)^m of odd m > 0 fixed by C^T S C over all 88 orbitals (without the sign: deviation 12). ASSUMPTION:
    the spherical order m = −l … +l of Q-Chem (their documentation as remembered)
    — on a single atom the orthonormality does not tell the order of the functions of one shell apart.
§7 TESTS
    tests/spectrum/test_output_orbitals.py.
§8' ROBUSTNESS
    The limits of orbital_files (atoms, basis functions); an incomplete table, unknown labels or a basis that does
    not match the rows raise ValueError.
"""

from math import sqrt
import re

import numpy as np

from modules.spectrum.analysis.gto import Shell, cartesian, pure_order
from modules.spectrum.analysis.orbitals import Orbital, OrbitalSet, half_unit, scaled, select
from azimuth.core import Molecule, SYMBOLS
from modules.compass.chemistry.geometry_tools import BOHR

LETTERS = {'S': 0, 'P': 1, 'D': 2, 'F': 3, 'G': 4, 'H': 5}
NUMBER = r'[+-]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][+-]?\d+)?'
MAX_ATOMS = 500
MAX_BASIS = 2000


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not np.isfinite(value):
        raise ValueError('non-finite number in the output')
    return value


def _powers(label):
    """«XXY», «dxy», «xy» → (2, 1, 0); «S» → (0, 0, 0)."""
    body = label.lower().lstrip('spdfgh') if len(label) > 1 and label[0].lower() in 'spdfgh' else label.lower()
    if label.upper() == 'S' or body == '':
        return (0, 0, 0)
    return (body.count('x'), body.count('y'), body.count('z'))


def _candidates(shells):
    """(name, shells, factor or None) tried by orbitals.select: as printed, renormalized contractions, and the
    Cartesian functions of higher l scaled like x^l (GAMESS normalizes every Cartesian component alike)."""
    renormalized = scaled(shells, lambda s: s.coefficients / sqrt(s.contraction_norm()))
    yield 'standard', shells, None
    yield 'unnormalized contractions', renormalized, None
    if any(not s.pure and s.l >= 2 for s in shells):
        from modules.spectrum.readers.orbital_files import PSI4_CARTESIAN, _monomial_factors

        factor = _monomial_factors(shells, PSI4_CARTESIAN)
        yield 'Cartesian like x^l', shells, factor
        yield 'Cartesian like x^l (normalized contractions)', renormalized, factor
        yield 'Cartesian like x^l, inverse', shells, 1 / factor


def _assemble(program, molecule, shells, orbitals, columns, units, core=None):
    nbasis = sum(s.size for s in shells)
    if len(molecule.atoms) > MAX_ATOMS:
        raise ValueError(f'more than {MAX_ATOMS} atoms')
    if nbasis > MAX_BASIS:
        raise ValueError(f'{nbasis} basis functions: the limit is {MAX_BASIS}')
    coefficients = np.array(columns).T
    half_units = np.array(units).T
    if coefficients.shape[0] != nbasis:
        raise ValueError(f'{program}: {coefficients.shape[0]} coefficients per orbital for {nbasis} basis functions')
    centres = np.array([a.position for a in molecule.atoms]) / BOHR
    spins = [o.spin for o in orbitals]
    name, chosen, c, found = select(list(_candidates(shells)), centres, coefficients, spins, half_units)
    core = core or {}
    charges = [SYMBOLS.index(a.symbol) + 1 - core.get(k, 0) for k, a in enumerate(molecule.atoms)]  # ECP: valence
    return OrbitalSet('', Molecule(program, molecule.atoms), tuple(charges), tuple(chosen), centres, tuple(orbitals),
                      c, name, found, program)


def _occupations(counts, energies_by_spin, restricted):
    """Aufbau occupations: restricted — 2 for the a lowest (and 1 for the a − b open shells), else 1 per spin."""
    alpha, beta = counts
    found = []
    for spin, energies in energies_by_spin:
        order = np.argsort(energies, kind='stable')
        occ = np.zeros(len(energies))
        if restricted:
            occ[order[:beta]] = 2.0
            occ[order[beta:alpha]] = 1.0
        else:
            occ[order[:alpha if spin == 'alpha' else beta]] = 1.0
        found.append(occ)
    return found


# ---------------------------------------------------------------- GAMESS (US) and Firefly
def _gamess_basis(text):
    start = text.find('ATOMIC BASIS SET')
    if start < 0:
        raise ValueError('the GAMESS output has no «ATOMIC BASIS SET»')
    basis, name, shells, current = {}, None, None, None
    lines = text[start:].splitlines()[5:]
    for line in lines:
        f = line.split()
        if not f:
            continue
        if f[0].startswith('$') or f[:2] == ['TOTAL', 'NUMBER'] or 'NUMBER OF' in line or 'SHELLS' in line:
            break
        if len(f) == 1 and re.fullmatch(r'[A-Za-z][A-Za-z0-9]*', f[0]):
            name, shells, current = f[0], [], None
            basis[name] = shells
            continue
        if name is None:
            continue
        if len(f) in (5, 6) and f[0].isdigit() and f[1] in tuple(LETTERS) + ('L',):
            number, kind = int(f[0]), f[1]
            exponent, coefficients = _number(f[3]), [_number(v) for v in f[4:]]
            if current is None or current[0] != number:
                current = (number, kind, [], [])
                shells.append(current)
            current[2].append(exponent)
            current[3].append(coefficients)
            continue
        break
    if not basis:
        raise ValueError('the GAMESS basis could not be read')
    out = {}
    for name, shells in basis.items():
        rows = []
        for _, kind, exponents, coefficients in shells:
            if kind == 'L':
                rows.append((0, exponents, [c[0] for c in coefficients]))
                rows.append((1, exponents, [c[1] for c in coefficients]))
            else:
                rows.append((LETTERS[kind], exponents, [c[0] for c in coefficients]))
        out[name.upper()] = rows
    return out


def _gamess_blocks(text):
    """[(spin, [(energy, [tokens per row])], [(name, atom, label)])] of the last EIGENVECTORS (per spin)."""
    heads = [m.start() for m in re.finditer(r'^\s*EIGENVECTORS\s*$', text, re.M)]
    if not heads:
        raise ValueError('the GAMESS output has no «EIGENVECTORS»')
    last = heads[-1]
    spins = [('alpha', last)]
    beta_mark = text.rfind('----- BETA SET -----', 0, last)
    if beta_mark >= 0 and beta_mark > text.rfind('----- ALPHA SET -----', 0, beta_mark) >= 0 and len(heads) >= 2:
        spins = [('alpha', heads[-2]), ('beta', last)]
    found = []
    for spin, start in spins:
        lines = text[start:].splitlines()[3:]
        orbitals, labels = [], []
        k = 0
        while k < len(lines):
            f = lines[k].split()
            if not f:
                k += 1
                continue
            if not all(x.isdigit() for x in f):
                break
            count = len(f)
            energies = re.findall(NUMBER, lines[k + 1])
            if len(energies) != count:
                break
            k += 2
            if k < len(lines) and lines[k].strip() and not re.match(r'^\s*\d+\s+\S+\s+\d+\s+[SPDFGHXYZ]+\s', lines[k]):
                k += 1  # the symmetries of the orbitals
            block = [(_number(e), []) for e in energies]
            row = 0
            while k < len(lines):
                m = re.match(r'^\s*(\d+)\s+(\S+)\s+(\d+)\s+([SPDFGHXYZ]+)\s+(.*)$', lines[k])
                if not m:
                    break
                values = re.findall(NUMBER, m[5])
                if len(values) != count:
                    raise ValueError(f'a GAMESS orbital row has {len(values)} numbers for {count} orbitals')
                if not orbitals:
                    labels.append((m[2].upper(), int(m[3]), m[4]))
                for n, v in enumerate(values):
                    block[n][1].append(v)
                row += 1
                k += 1
            if row == 0:
                break
            orbitals.extend(block)
        if not orbitals:
            raise ValueError('the GAMESS orbitals could not be read')
        found.append((spin, orbitals, labels))
    return found


def read_gamess_orbitals(text):
    from modules.spectrum.readers.gamess import _geometries

    blocks = _gamess_blocks(text)
    labels = blocks[0][2]
    start = [m.start() for m in re.finditer(r'^\s*EIGENVECTORS\s*$', text, re.M)][-len(blocks)]
    geometries = [g for p, g in _geometries(text) if p < start]
    if not geometries:
        raise ValueError('the GAMESS output has no geometry before the orbitals')
    molecule = geometries[-1]
    basis = _gamess_basis(text)
    shells, permutation = [], []
    k = 0
    for atom in range(len(molecule.atoms)):
        rows = [r for r in range(len(labels)) if labels[r][1] == atom + 1]
        if not rows:
            raise ValueError(f'GAMESS orbitals: no rows for atom {atom + 1}')
        name = labels[rows[0]][0]
        if name not in basis:
            raise ValueError(f'GAMESS orbitals: no basis printed for {name}')
        for l, exponents, coefficients in basis[name]:
            size = (l + 1) * (l + 2) // 2
            block = list(range(k, k + size))
            if len(block) < size or block[-1] >= len(labels) or any(labels[r][1] != atom + 1 for r in block):
                raise ValueError(f'GAMESS orbitals: the rows of atom {atom + 1} do not match its basis')
            powers = [_powers(labels[r][2]) for r in block]
            order = cartesian(l)
            if sorted(powers) != sorted(order) or any(sum(p) != l for p in powers):
                raise ValueError(f'GAMESS orbitals: unexpected labels {[labels[r][2] for r in block]}')
            permutation.extend(block[powers.index(p)] for p in order)
            shells.append(Shell(atom, l, False, exponents, coefficients))
            k += size
    if k != len(labels):
        raise ValueError('GAMESS orbitals: more rows than basis functions')
    alpha = re.findall(r'NUMBER OF OCCUPIED ORBITALS \(ALPHA\)\s*(?:KEPT IS)?\s*=\s*(\d+)', text)
    beta = re.findall(r'NUMBER OF OCCUPIED ORBITALS \(BETA ?\)\s*(?:KEPT IS)?\s*=\s*(\d+)', text)
    counts = (int(alpha[-1]) if alpha else 0, int(beta[-1]) if beta else 0)
    restricted = len(blocks) == 1
    occupations = _occupations(counts, [(s, [e for e, _ in orbs]) for s, orbs, _ in blocks], restricted)
    orbitals, columns, units = [], [], []
    permutation = np.array(permutation)
    for (spin, orbs, _), occ in zip(blocks, occupations):
        for n, (energy, tokens) in enumerate(orbs):
            orbitals.append(Orbital(n + 1, spin, energy, float(occ[n])))
            columns.append(np.array([_number(t) for t in tokens])[permutation])
            units.append(np.array([half_unit(t) for t in tokens])[permutation])
    core = {}  # the core electrons an ECP removes from an atom (its charge for the Mulliken populations)
    for m in re.finditer(r'ON ATOM\s+(\d+)\s+(?:WITH ZCORE\s+(\d+)|ARE THE SAME AS ATOM\s+(\d+))', text):
        atom = int(m[1]) - 1
        core[atom] = int(m[2]) if m[2] else core.get(int(m[3]) - 1, 0)
    return _assemble('GAMESS', molecule, shells, orbitals, columns, units, core)


# ---------------------------------------------------------------- NWChem
def _nwchem_basis(text):
    found = list(re.finditer(r'Basis "ao basis" -> "ao basis" \((cartesian|spherical)\)', text))
    if not found:
        raise ValueError('the NWChem output has no «Basis "ao basis"»')
    head = found[-1]
    pure = head[1] == 'spherical'
    basis, tag, current = {}, None, None
    for line in text[head.end():].splitlines()[2:]:
        f = line.split()
        if line.strip().startswith('Summary of'):
            break
        m = re.match(r'^\s*(\S+)\s+\(([A-Za-z]+)\)\s*$', line)
        if m:
            tag, current = m[1], None
            basis[tag] = []
            continue
        if tag is None or not f or set(line.strip()) <= {'-'} or f[0] == 'Exponent':
            current = None if not f else current
            continue
        if len(f) >= 4 and f[0].isdigit() and f[1].upper() in LETTERS:
            number, l = int(f[0]), LETTERS[f[1].upper()]
            if current is None or current[0] != number:
                current = [number, l, [], []]
                basis[tag].append(current)
            current[2].append(_number(f[2]))
            current[3].append(_number(f[3]))
    if not basis:
        raise ValueError('the NWChem basis could not be read')
    return {t: [(l, e, c) for _, l, e, c in shells] for t, shells in basis.items()}, pure


def _nwchem_vectors(text, spin):
    heads = list(re.finditer(r'global array: ' + spin + r' evecs\[1:(\d+),1:(\d+)\]', text))
    if not heads:
        return None
    head = heads[-1]
    nbasis, norbitals = int(head[1]), int(head[2])
    rows = [[] for _ in range(nbasis)]
    filled = 0
    for line in text[head.end():].splitlines()[1:]:  # the rest of the line: «, handle: -995»
        f = line.split()
        if not f or set(line.strip()) <= {'-', ' '}:
            continue
        if all(x.isdigit() for x in f):
            continue  # the column numbers
        if f[0].isdigit() and len(f) > 1 and re.fullmatch(NUMBER, f[1]):
            r = int(f[0]) - 1
            if 0 <= r < nbasis:
                rows[r].extend(f[1:])
                filled = max(filled, len(rows[r]))
                continue
        break
    if any(len(r) != norbitals for r in rows):
        raise ValueError('the NWChem «Final MO vectors» are incomplete')
    return [[rows[b][o] for b in range(nbasis)] for o in range(norbitals)]


def _nwchem_analysis(text, spin):
    title = {'alpha': r'(?:Alpha )?', 'beta': r'Beta '}[spin]
    heads = list(re.finditer(r'Final ' + title + r'Molecular Orbital Analysis', text))
    if not heads:
        return {}
    found = {}
    end = text.find('Final', heads[-1].end() + 10)
    body = text[heads[-1].end(): end if end > 0 else None]
    for m in re.finditer(r'Vector\s+(\d+)\s+Occ=\s*(' + NUMBER + r')\s+E=\s*(' + NUMBER + ')', body):
        found[int(m[1])] = (_number(m[3]), _number(m[2]))
    return found


def read_nwchem_orbitals(text):
    from modules.spectrum.readers.nwchem import _geometries

    alpha = _nwchem_vectors(text, 'alpha')
    if alpha is None:
        raise ValueError('the NWChem output has no «Final MO vectors»: add print "final vectors" "final vectors analysis"')
    beta = _nwchem_vectors(text, 'beta')
    start = text.rfind('Final MO vectors')
    geometries = [g for p, g in _geometries(text) if p < start]
    if not geometries:
        raise ValueError('the NWChem output has no geometry before the orbitals')
    molecule = geometries[-1]
    basis, pure = _nwchem_basis(text)
    tags = re.findall(r'^\s*\d+\s+(\S+)\s+' + NUMBER + r'\s+' + NUMBER + r'\s+' + NUMBER + r'\s+' + NUMBER + r'\s*$',
                      text[text.rfind('Output coordinates', 0, start):start], re.M)[:len(molecule.atoms)]
    shells, permutation, signs = [], [], []
    k = 0
    for atom, a in enumerate(molecule.atoms):
        tag = tags[atom] if atom < len(tags) and tags[atom] in basis else a.symbol
        if tag not in basis:
            raise ValueError(f'NWChem orbitals: no basis printed for {tag}')
        for l, exponents, coefficients in basis[tag]:
            if pure and l >= 2:
                order = list(range(-l, l + 1))  # m = -l … +l
                permutation.extend(k + order.index(m) for m in pure_order(l))
                signs.extend(-1.0 if m > 0 and m % 2 else 1.0 for m in pure_order(l))  # Condon–Shortley phase
                size = 2 * l + 1
            else:
                printed = [(a_, b_, l - a_ - b_) for a_ in range(l, -1, -1) for b_ in range(l - a_, -1, -1)]
                permutation.extend(k + printed.index(p) for p in cartesian(l))
                signs.extend(1.0 for _ in cartesian(l))
                size = len(printed)
            shells.append(Shell(atom, l, pure and l >= 2, exponents, coefficients))
            k += size
    permutation, signs = np.array(permutation), np.array(signs)
    orbitals, columns, units = [], [], []
    for spin, vectors in (('alpha', alpha), ('beta', beta)):
        if vectors is None:
            continue
        analysis = _nwchem_analysis(text, spin)
        if len(analysis) < len(vectors):
            raise ValueError('the NWChem output has no energies of every orbital: add print "final vectors analysis"')
        for n, tokens in enumerate(vectors):
            energy, occupation = analysis[n + 1]
            orbitals.append(Orbital(n + 1, spin, energy, occupation))
            if len(tokens) != k:
                raise ValueError(f'NWChem orbitals: {len(tokens)} coefficients for {k} basis functions')
            columns.append(np.array([_number(t) for t in tokens])[permutation] * signs)
            units.append(np.array([half_unit(t) for t in tokens])[permutation])
    return _assemble('NWChem', molecule, shells, orbitals, columns, units)


# ---------------------------------------------------------------- Q-Chem
def _qchem_basis(text):
    head = text.rfind('Basis set in general basis input format')
    if head < 0:
        raise ValueError('the Q-Chem output has no basis: add PRINT_GENERAL_BASIS true')
    start = text.find('$basis', head)
    end = text.find('$end', start)
    lines = text[start:end].splitlines()[1:]
    atoms, shells = [], None
    k = 0
    while k < len(lines):
        f = lines[k].split()
        k += 1
        if not f:
            continue
        if f[0] == '****':
            shells = None
            continue
        if shells is None:
            shells = []
            atoms.append((f[0], shells))
            continue
        kind, count = f[0].upper(), int(f[1])
        rows = [[_number(v) for v in lines[k + j].split()] for j in range(count)]
        k += count
        if kind == 'SP':
            shells.append((0, [r[0] for r in rows], [r[1] for r in rows]))
            shells.append((1, [r[0] for r in rows], [r[2] for r in rows]))
        elif kind in LETTERS:
            shells.append((LETTERS[kind], [r[0] for r in rows], [r[1] for r in rows]))
        else:
            raise ValueError(f'unexpected shell {kind!r} in the Q-Chem basis')
    if not atoms:
        raise ValueError('the Q-Chem basis could not be read')
    return atoms


def _qchem_blocks(text):
    found = []
    for title, spin in (('RESTRICTED (RHF)', 'alpha'), ('ALPHA ', 'alpha'), ('BETA  ', 'beta')):
        heads = list(re.finditer(re.escape(title) + r'\s*MOLECULAR ORBITAL COEFFICIENTS', text))
        if not heads:
            continue
        lines = text[heads[-1].end():].splitlines()[1:]
        orbitals, labels = [], []
        k = 0
        while k + 1 < len(lines):
            f = lines[k].split()
            if not f or not all(x.isdigit() for x in f):
                break
            count = len(f)
            m = re.match(r'^\s*eigenvalues:\s*(.*)$', lines[k + 1])
            energies = re.findall(NUMBER, m[1]) if m else []
            if len(energies) != count:
                break
            block = [(_number(e), []) for e in energies]
            k += 2
            while k < len(lines):
                r = re.match(r'^\s*(\d+)\s+([A-Z][a-z]?)\s*(\d*)\s+([spdfgh](?:\s*\d+|[xyz]*))\s+(.*)$', lines[k])
                if not r:
                    break
                values = re.findall(NUMBER, r[5])
                if len(values) != count:
                    raise ValueError(f'a Q-Chem orbital row has {len(values)} numbers for {count} orbitals')
                if not orbitals:
                    labels.append((r[2], r[4].replace(' ', '')))
                for n, v in enumerate(values):
                    block[n][1].append(v)
                k += 1
            orbitals.extend(block)
        if orbitals:
            found.append((spin, orbitals, labels))
    if not found:
        raise ValueError('the Q-Chem output has no «MOLECULAR ORBITAL COEFFICIENTS»: add PRINT_ORBITALS true')
    return found


def read_qchem_orbitals(text):
    from modules.spectrum.readers.qchem import _geometries

    blocks = _qchem_blocks(text)
    labels = blocks[0][2]
    start = text.rfind('MOLECULAR ORBITAL COEFFICIENTS')
    geometries = [g for p, g in _geometries(text) if p < start]
    if not geometries:
        raise ValueError('the Q-Chem output has no geometry before the orbitals')
    molecule = geometries[-1]
    basis = _qchem_basis(text)
    if len(basis) != len(molecule.atoms):
        raise ValueError('the Q-Chem basis is printed for another number of atoms')
    shells, permutation = [], []
    k = 0
    for atom, (symbol, rows) in enumerate(basis):
        for l, exponents, coefficients in rows:
            label = labels[k][1] if k < len(labels) else ''
            pure = l >= 2 and bool(re.fullmatch(r'[dfgh]\d+', label))
            if pure:
                order = list(range(-l, l + 1))  # «d 1» … «d 5» = m −2 … +2
                size = 2 * l + 1
                permutation.extend(k + order.index(m) for m in pure_order(l))
            else:
                size = (l + 1) * (l + 2) // 2
                block = [labels[k + j][1] if k + j < len(labels) else '' for j in range(size)]
                powers = [_powers(b) for b in block]
                if sorted(powers) != sorted(cartesian(l)):
                    raise ValueError(f'Q-Chem orbitals: unexpected labels {block}')
                permutation.extend(k + powers.index(p) for p in cartesian(l))
            shells.append(Shell(atom, l, pure, exponents, coefficients))
            k += size
    if k != len(labels):
        raise ValueError('Q-Chem orbitals: the rows do not match the basis')
    counts = re.findall(r'There are\s+(\d+)\s+alpha and\s+(\d+)\s+beta electrons', text)
    if not counts:
        raise ValueError('the Q-Chem output does not say the number of electrons')
    counts = (int(counts[-1][0]), int(counts[-1][1]))
    restricted = len(blocks) == 1
    occupations = _occupations(counts, [(s, [e for e, _ in orbs]) for s, orbs, _ in blocks], restricted)
    orbitals, columns, units = [], [], []
    permutation = np.array(permutation)
    for (spin, orbs, _), occ in zip(blocks, occupations):
        for n, (energy, tokens) in enumerate(orbs):
            orbitals.append(Orbital(n + 1, spin, energy, float(occ[n])))
            columns.append(np.array([_number(t) for t in tokens])[permutation])
            units.append(np.array([half_unit(t) for t in tokens])[permutation])
    return _assemble('Q-Chem', molecule, shells, orbitals, columns, units)


def has_orbitals(text):
    """Whether a GAMESS, NWChem or Q-Chem output prints its basis and orbitals."""
    from modules.spectrum.readers.outputs import program

    found = program(text)
    if found == 'GAMESS':
        return 'ATOMIC BASIS SET' in text and bool(re.search(r'^\s*EIGENVECTORS\s*$', text, re.M))
    if found == 'NWChem':
        return 'Final MO vectors' in text and 'Basis "ao basis" -> "ao basis"' in text
    if found == 'Q-Chem':
        return 'MOLECULAR ORBITAL COEFFICIENTS' in text and 'Basis set in general basis input format' in text
    return False

"""Readers of molecular orbitals: Molden files, Gaussian formatted checkpoints, ORCA outputs.

§1 THEORY
    All three formats give a contracted Gaussian basis (centres, angular momenta, exponents, contraction
    coefficients) and orbital coefficients in that basis; they differ in the order of the functions of
    a shell and in conventions of normalization and sign, which modules/spectrum/analysis/orbitals.py settles by
    the orthonormality of the orbitals (orbitals.select).
§2 ALGORITHM
    Molden: sections [Atoms] (Angs | AU), [GTO], [MO] and the flags [5D] (= spherical d and f),
    [5D7F], [5D10F] (spherical d only), [7F] (spherical f only), [9G] (spherical g and h); other sections
    are skipped; a shell «sp» is split into an s and a p shell.
    Gaussian fchk: «Shell types» (0 s, 1 p, -1 sp, +-l Cartesian / spherical l), «Number of primitives
    per shell», «Shell to atom map», «Primitive exponents», «Contraction coefficients», «P(S=P)
    Contraction coefficients», «Current cartesian coordinates» (bohr), «Alpha/Beta MO coefficients»
    (orbital by orbital), «Alpha/Beta Orbital Energies»; occupations from the numbers of alpha and beta
    electrons (Aufbau, as the SCF): restricted closed shell 2, restricted open shell 2 and 1,
    unrestricted 1 per spin. Cartesian g and higher come in the reverse alphabetical order
    (zzzz, yzzz, ..., xxxx) and are reordered.
    ORCA output (with %output print[p_basis] 2 print[p_mos] 1 end): «BASIS SET IN INPUT FORMAT»
    (per element), the last «CARTESIAN COORDINATES (ANGSTROEM)» before the last «MOLECULAR ORBITALS»
    block, whose columns give number, energy, occupation and the coefficients; rows «0C 1s», «0C 1pz»...;
    for UHF the beta orbitals follow when the column numbers start again at 0. ORCA orders p as z, x, y
    and spherical functions as m = 0, +1, -1, +2, -2, ...
    read_orbitals(text) recognizes the format from its first lines; the orbitals printed in GAMESS, NWChem
    and Q-Chem outputs are read by output_orbitals.py.
§3 APPLICATIONS
    The orbital window (modules/spectrum/views/orbitals_view.py); the Spectrum workspace opens them.
§4 SPECIFICATION
    read_molden(text), read_fchk(text), read_orca(text), read_orbitals(text) -> orbitals.OrbitalSet;
    ValueError for files without orbitals or with inconsistent data. kind(text) -> 'molden' | 'fchk' |
    'orca' | 'gamess' | 'nwchem' | 'qchem' | None.
§5 PROCEDURES - below.
§6 NOTES
    Molden conventions, from the documentation and tests of IOData (github.com/theochem/iodata,
    iodata/formats/molden.py, commit 9f7e800; facts reimplemented here, no code copied) and checked on
    its test files (not distributed with Azimuth):
      'standard' — contraction coefficients of normalized primitives (Molden, Molpro; CFOUR s and p);
      'ORCA' — orca_2mkl divides the coefficients by the norm of a Cartesian primitive x^0, x, xy, xyz,
        x^2yz, x^5 (s, p, spherical d, f, g, h) and flips the sign of the m = +-3 (f, g, h) and
        m = +-4 (g, h) spherical functions;
      'Psi4 < 1.0' — coefficients divided by the norm of s, x, xy/sqrt(3), xyz/sqrt(15) primitives;
      'Turbomole' — Cartesian d, f, g coefficients multiplied by sqrt(3), sqrt(15), sqrt(105);
      'CFOUR 2.1' — orbital coefficients of Cartesian monomials x^2-, x^3-, x^2y-, x^4-, x^3y-, x^2y^2-,
        x^2yz-type divided by 1/sqrt(3), 1/sqrt(15), 1/sqrt(3), 1/sqrt(105), 1/sqrt(15), 1/3, 1/sqrt(3);
      'unnormalized contractions' — every contraction renormalized (Psi4 1.0 and others);
      'Psi4 <= 1.3.2 (Cartesian)' — renormalized contractions; Cartesian orbital coefficients divided by
        sqrt 3 (xy-type d), sqrt 5 / sqrt 15 (x^2y / xyz f), sqrt 7 / sqrt(35/3) / sqrt 35 (x^3y / x^2y^2
        / x^2yz g).
    fchk conventions (IOData iodata/formats/fchk.py, and the orthonormality on the cclib files):
    normalized primitives, spherical functions m = 0, +1, -1, ...; Cartesian d and f in the Molden order.
    ORCA output: verified on cclib's ORCA 5.0 and 6.0 outputs (STO-3G: s and p only) against the overlap
    matrix ORCA prints. ASSUMPTION: d, f, g rows follow m = 0, +1, -1, ... as ORCA's labels dz2, dxz,
    dyz, dx2y2, dxy say, with the signs of orca_2mkl — the orthonormality check refuses the file
    otherwise.
§7 TESTS
    tests/spectrum/test_orbitals.py (cclib test data: tests/data/orbitals).
§8' ROBUSTNESS
    Limits: 2000 basis functions (orbitals.MAX_BASIS), 500 atoms; non-finite numbers, l > 5 (Molden: also
    Cartesian h), counts that do not match the basis raise ValueError.
"""

from math import sqrt
import re

import numpy as np

from modules.spectrum.analysis.gto import Shell, cartesian
from modules.spectrum.analysis.orbitals import (
    MAX_BASIS,
    ORCA_POWERS,
    Orbital,
    OrbitalSet,
    cartesian_norm,
    half_unit,
    orca_signs,
    scaled,
    select,
)
from azimuth.core import Atom, Molecule, SYMBOLS
from modules.compass.chemistry.geometry_tools import BOHR

LETTERS = {'s': 0, 'p': 1, 'd': 2, 'f': 3, 'g': 4, 'h': 5}
MAX_ATOMS = 500


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not np.isfinite(value):
        raise ValueError('non-finite number in the file')
    return value


def _check_size(atoms, nbasis):
    if len(atoms) > MAX_ATOMS:
        raise ValueError(f'more than {MAX_ATOMS} atoms')
    if nbasis > MAX_BASIS:
        raise ValueError(f'{nbasis} basis functions: the limit is {MAX_BASIS}')


def _renormalized(shells):
    return scaled(shells, lambda s: s.coefficients / sqrt(s.contraction_norm()))


# ---------------------------------------------------------------- Molden


def _sections(text):
    lines = text.splitlines()
    if not lines or lines[0].strip().lower() != '[molden format]':
        raise ValueError('not a Molden file: the first line must be [Molden Format]')
    found = []
    for k, line in enumerate(lines):
        m = re.match(r'^\s*\[([^\]]+)\](.*)$', line)
        if m:
            found.append((m[1].strip().lower(), m[2].strip(), k))
    parts = []
    for n, (name, rest, k) in enumerate(found):
        end = found[n + 1][2] if n + 1 < len(found) else len(lines)
        parts.append((name, rest, lines[k + 1 : end]))
    return parts


def _atoms(rest, body):
    factor = BOHR if 'au' in re.split(r'[\s()]+', rest.lower()) else 1.0
    atoms, charges = [], []
    for line in body:
        f = line.split()
        if not f:
            continue
        if len(f) < 6:
            break
        z = int(f[2])
        symbol = SYMBOLS[z - 1] if 1 <= z <= len(SYMBOLS) else f[0].strip('0123456789').capitalize()
        if symbol not in SYMBOLS:
            raise ValueError(f'unknown element {f[0]!r} in [Atoms]')
        atoms.append(Atom(symbol, *(_number(v) * factor for v in f[3:6])))
        charges.append(z)
    if not atoms:
        raise ValueError('the [Atoms] section is empty')
    return atoms, charges


def _gto(body):
    """[(centre 0-based, letter, exponents, coefficients)]."""
    shells = []
    centre = None
    k = 0
    while k < len(body):
        f = body[k].split()
        k += 1
        if not f:
            continue
        if f[0].isdigit() and (len(f) == 1 or (len(f) == 2 and f[1].isdigit())):
            centre = int(f[0]) - 1
            continue
        letter = f[0].lower()
        if centre is None or (letter not in LETTERS and letter != 'sp') or len(f) < 2:
            raise ValueError(f'unexpected line in [GTO]: {body[k - 1].strip()!r}')
        count = int(f[1])
        rows = []
        for _ in range(count):
            if k >= len(body):
                raise ValueError('[GTO] ends inside a shell')
            rows.append([_number(v) for v in body[k].split()])
            k += 1
        width = 3 if letter == 'sp' else 2
        if any(len(r) < width for r in rows):
            raise ValueError('a primitive line of [GTO] has too few numbers')
        exponents = [r[0] for r in rows]
        if letter == 'sp':
            shells.append((centre, 's', exponents, [r[1] for r in rows]))
            shells.append((centre, 'p', exponents, [r[2] for r in rows]))
        else:
            shells.append((centre, letter, exponents, [r[1] for r in rows]))
    if not shells:
        raise ValueError('the [GTO] section is empty')
    return shells


def _mo(body):
    infos, columns = [], []
    info, column = {}, None
    for line in body:
        text = line.strip()
        if not text:
            continue
        if text.count('=') == 1:
            if column is not None:
                infos.append(info)
                columns.append(column)
                info, column = {}, None
            key, value = text.split('=')
            info[key.strip().lower()] = value.strip()
            continue
        f = text.split()
        if len(f) != 2 or not f[0].isdigit():
            raise ValueError(f'unexpected line in [MO]: {text!r}')
        if column is None:
            column = {}
        column[int(f[0])] = (_number(f[1]), half_unit(f[1]))
    if column is not None:
        infos.append(info)
        columns.append(column)
    if not infos:
        raise ValueError('the [MO] section is empty')
    return infos, columns


def _monomial_factors(shells, table):
    factors = []
    for s in shells:
        if not s.pure and s.l >= 2:
            kinds = [tuple(sorted(m, reverse=True)) for m in s.monomials]
            factors.append(np.array([table.get(k, 1.0) for k in kinds]))
        else:
            factors.append(np.ones(s.size))
    return np.concatenate(factors)


CFOUR = {
    (2, 0, 0): 1 / sqrt(3),
    (3, 0, 0): 1 / sqrt(15),
    (2, 1, 0): 1 / sqrt(3),
    (4, 0, 0): 1 / sqrt(105),
    (3, 1, 0): 1 / sqrt(15),
    (2, 2, 0): 1 / 3,
    (2, 1, 1): 1 / sqrt(3),
}
PSI4_CARTESIAN = {
    (1, 1, 0): sqrt(3),
    (2, 1, 0): sqrt(5),
    (1, 1, 1): sqrt(15),
    (3, 1, 0): sqrt(7),
    (2, 2, 0): sqrt(35 / 3),
    (2, 1, 1): sqrt(35),
}


def _molden_candidates(shells):
    """(name, shells, factor on the orbital coefficients or None), in the order they are tried."""
    yield 'standard', shells, None

    def orca(s):
        if s.pure or s.l <= 1:
            return s.coefficients / cartesian_norm(s.exponents, ORCA_POWERS[s.l])
        return s.coefficients

    yield 'ORCA', scaled(shells, orca), orca_signs(shells)

    def psi4(s):
        if s.l <= 1:
            return s.coefficients / cartesian_norm(s.exponents, ORCA_POWERS[s.l])
        if s.pure and s.l in (2, 3):
            return s.coefficients / (cartesian_norm(s.exponents, ORCA_POWERS[s.l]) / sqrt((3, 15)[s.l - 2]))
        return s.coefficients

    yield 'Psi4 < 1.0', scaled(shells, psi4), None
    cartesian_high = any(not s.pure and s.l >= 2 for s in shells)
    if cartesian_high:

        def turbomole(s):
            if not s.pure and 2 <= s.l <= 4:
                return s.coefficients * sqrt({2: 3, 3: 15, 4: 105}[s.l])
            return s.coefficients

        yield 'Turbomole', scaled(shells, turbomole), None
        yield 'CFOUR 2.1', shells, 1 / _monomial_factors(shells, CFOUR)
    renormalized = _renormalized(shells)
    yield 'unnormalized contractions', renormalized, None
    if cartesian_high:
        yield 'Psi4 <= 1.3.2 (Cartesian)', renormalized, 1 / _monomial_factors(shells, PSI4_CARTESIAN)


def read_molden(text):
    flags = set()
    atoms = charges = gto = mo = None
    title = ''
    for name, rest, body in _sections(text):
        key = name.replace(' ', '')
        if key in ('5d', '5d7f'):
            flags |= {2, 3}
        elif key == '5d10f':
            flags |= {2}
        elif key == '7f':
            flags |= {3}
        elif key == '9g':
            flags |= {4, 5}
        elif key == 'title':
            title = next((line.strip() for line in body if line.strip()), '')
        elif key == 'atoms':
            atoms, charges = _atoms(rest, body)
        elif key == 'gto':
            gto = _gto(body)
        elif key == 'mo':
            mo = _mo(body)
        elif key == 'sto':
            raise ValueError('Slater-type orbitals ([STO]) are not supported')
    if atoms is None or gto is None or mo is None:
        raise ValueError('a Molden file with orbitals needs the sections [Atoms], [GTO] and [MO]')
    shells = []
    for centre, letter, exponents, coefficients in gto:
        if not 0 <= centre < len(atoms):
            raise ValueError(f'[GTO] refers to atom {centre + 1}, the file has {len(atoms)}')
        l = LETTERS[letter]
        if l == 5 and 5 not in flags:
            raise ValueError('Cartesian h functions are not defined in the Molden format')
        shells.append(Shell(centre, l, l in flags, exponents, coefficients))
    nbasis = sum(s.size for s in shells)
    _check_size(atoms, nbasis)
    infos, columns = mo
    coefficients = np.zeros((nbasis, len(columns)))
    half_units = np.zeros((nbasis, len(columns)))
    orbitals = []
    counts = {'alpha': 0, 'beta': 0}
    for k, (info, column) in enumerate(zip(infos, columns)):
        if max(column) > nbasis or min(column) < 1:
            raise ValueError(f'orbital {k + 1} has coefficients for {max(column)} functions, the basis has {nbasis}')
        for index, (value, unit) in column.items():
            coefficients[index - 1, k] = value
            half_units[index - 1, k] = unit
        spin = 'beta' if info.get('spin', 'alpha').lower().startswith('b') else 'alpha'
        counts[spin] += 1
        orbitals.append(
            Orbital(
                counts[spin],
                spin,
                _number(info.get('ene', '0')),
                _number(info.get('occup', '0')),
                info.get('sym', '').strip(),
            )
        )
    centres = np.array([a.position for a in atoms]) / BOHR
    spins = [o.spin for o in orbitals]
    name, chosen, c, found = select(_molden_candidates(shells), centres, coefficients, spins, half_units)
    molecule = Molecule(title or 'Molden', tuple(atoms))
    return OrbitalSet(
        title, molecule, tuple(charges), tuple(chosen), centres, tuple(orbitals), c, name, found, 'Molden'
    )


# ---------------------------------------------------------------- Gaussian fchk


def _fchk_fields(text):
    fields = {}
    lines = text.splitlines()
    k = 2
    head = re.compile(r'^(\S.*?)\s{2,}([IRCHL])\s+(N=)?\s*(\S+)\s*$')
    while k < len(lines):
        m = head.match(lines[k])
        k += 1
        if not m:
            continue
        name, kind, array, value = m[1].strip(), m[2], m[3], m[4]
        if not array:
            fields[name] = _number(value) if kind == 'R' else value
            continue
        count = int(value)
        tokens = []
        while len(tokens) < count and k < len(lines) and not head.match(lines[k]):
            tokens.extend(lines[k].split())
            k += 1
        if kind == 'I':
            fields[name] = np.array([int(t) for t in tokens[:count]])
        elif kind == 'R':
            fields[name] = (np.array([_number(t) for t in tokens[:count]]), tokens[:count])
        else:
            fields[name] = ' '.join(tokens)
    return fields


def _fchk_permutation(l, pure):
    """Positions of the fchk functions of one shell in the order of gto.Shell."""
    if pure or l <= 3:
        return np.arange(2 * l + 1 if pure else len(cartesian(l)))
    mine = cartesian(l)
    alphabetical = [(a, b, l - a - b) for a in range(l, -1, -1) for b in range(l - a, -1, -1)]
    theirs = alphabetical[::-1]
    return np.array([theirs.index(m) for m in mine])


def read_fchk(text):
    fields = _fchk_fields(text)
    need = (
        'Atomic numbers',
        'Current cartesian coordinates',
        'Shell types',
        'Number of primitives per shell',
        'Shell to atom map',
        'Primitive exponents',
        'Contraction coefficients',
        'Alpha MO coefficients',
        'Alpha Orbital Energies',
    )
    missing = [n for n in need if n not in fields]
    if missing:
        raise ValueError('the formatted checkpoint has no ' + ', '.join(missing))
    numbers = fields['Atomic numbers']
    xyz = fields['Current cartesian coordinates'][0].reshape(-1, 3)
    if len(xyz) != len(numbers) or not all(1 <= z <= len(SYMBOLS) for z in numbers):
        raise ValueError('inconsistent atoms in the formatted checkpoint')
    atoms = [Atom(SYMBOLS[z - 1], *(xyz[k] * BOHR)) for k, z in enumerate(numbers)]
    charges = fields['Nuclear charges'][0] if 'Nuclear charges' in fields else numbers.astype(float)
    types = fields['Shell types']
    counts = fields['Number of primitives per shell']
    owners = fields['Shell to atom map'] - 1
    exponents = fields['Primitive exponents'][0]
    contraction = fields['Contraction coefficients'][0]
    sp = fields['P(S=P) Contraction coefficients'][0] if 'P(S=P) Contraction coefficients' in fields else None
    shells, order = [], []
    start = 0
    for t, n, owner in zip(types, counts, owners):
        part = slice(start, start + n)
        start += n
        if t == -1:
            if sp is None:
                raise ValueError('an SP shell without P(S=P) contraction coefficients')
            shells.append(Shell(owner, 0, False, exponents[part], contraction[part]))
            shells.append(Shell(owner, 1, False, exponents[part], sp[part]))
            order += [np.arange(1), np.arange(3)]
            continue
        l, pure = abs(int(t)), t < -1
        if l > 5:
            raise ValueError(f'angular momentum {l} is not supported')
        shells.append(Shell(owner, l, pure, exponents[part], contraction[part]))
        order.append(_fchk_permutation(l, pure))
    nbasis = sum(s.size for s in shells)
    _check_size(atoms, nbasis)
    permutation, offset = [], 0
    for s, o in zip(shells, order):
        permutation.extend(offset + o)
        offset += s.size
    permutation = np.array(permutation)
    n_alpha = int(fields.get('Number of alpha electrons', 0))
    n_beta = int(fields.get('Number of beta electrons', 0))
    unrestricted = 'Beta MO coefficients' in fields
    blocks = []
    for spin in ('Alpha', 'Beta') if unrestricted else ('Alpha',):
        values, tokens = fields[f'{spin} MO coefficients']
        energies = fields[f'{spin} Orbital Energies'][0]
        norb = len(energies)
        if values.size != norb * nbasis:
            raise ValueError(f'{values.size} {spin.lower()} coefficients for {norb} orbitals of {nbasis} functions')
        c = values.reshape(norb, nbasis).T[permutation]
        units = np.array([half_unit(t) for t in tokens]).reshape(norb, nbasis).T[permutation]
        electrons = n_alpha if spin == 'Alpha' else n_beta
        if unrestricted:
            occupation = [1.0 if k < electrons else 0.0 for k in range(norb)]
        else:
            occupation = [2.0 if k < n_beta else (1.0 if k < n_alpha else 0.0) for k in range(norb)]
        blocks.append((spin.lower(), c, units, energies, occupation))
    orbitals, columns, unit_columns = [], [], []
    for spin, c, units, energies, occupation in blocks:
        for k, e in enumerate(energies):
            orbitals.append(Orbital(k + 1, spin, float(e), occupation[k]))
        columns.append(c)
        unit_columns.append(units)
    coefficients = np.hstack(columns)
    half_units = np.hstack(unit_columns)
    centres = xyz.copy()
    spins = [o.spin for o in orbitals]
    candidates = [('standard', shells, None), ('unnormalized contractions', _renormalized(shells), None)]
    name, chosen, c, found = select(candidates, centres, coefficients, spins, half_units)
    title = text.splitlines()[0].strip()
    return OrbitalSet(
        title,
        Molecule(title or 'fchk', tuple(atoms)),
        tuple(float(q) for q in charges),
        tuple(chosen),
        centres,
        tuple(orbitals),
        c,
        name,
        found,
        'Gaussian fchk',
    )


# ---------------------------------------------------------------- ORCA output

ORCA_NUMBER = r'[+-]?\d+\.\d+'


def _orca_basis(text):
    found = [m.start() for m in re.finditer(r'^BASIS SET IN INPUT FORMAT\s*$', text, flags=re.M)]  # not AUXILIARY/J
    start = found[-1] if found else -1
    if start < 0:
        raise ValueError(
            'the ORCA output has no «BASIS SET IN INPUT FORMAT»: add %output print[p_basis] 2 print[p_mos] 1 end'
        )
    basis = {}
    element, shells = None, None
    lines = text[start:].splitlines()[2:]
    k = 0
    while k < len(lines):
        f = lines[k].split()
        k += 1
        if not f:
            continue
        if f[0] == 'NewGTO':
            element, shells = f[1].capitalize(), []
            continue
        if f[0].lower() in ('end;', 'end'):
            if element is not None:
                basis[element] = shells
            element = None
            continue
        if element is None:
            if f[0] == '#':
                continue
            break
        letter = f[0].lower()
        if letter not in LETTERS and letter != 'l':
            raise ValueError(f'unexpected line in the ORCA basis: {lines[k - 1].strip()!r}')
        count = int(f[1])
        rows = [[_number(v) for v in lines[k + j].split()[1:]] for j in range(count)]
        k += count
        if letter == 'l':  # an sp shell: exponent, s and p coefficients
            shells.append((0, [r[0] for r in rows], [r[1] for r in rows]))
            shells.append((1, [r[0] for r in rows], [r[2] for r in rows]))
        else:
            shells.append((LETTERS[letter], [r[0] for r in rows], [r[1] for r in rows]))
    if not basis:
        raise ValueError('the ORCA basis set could not be read')
    return basis


def _orca_coordinates(text, before):
    starts = [m.end() for m in re.finditer(r'CARTESIAN COORDINATES \(ANGSTROEM\)', text[:before])]
    if not starts:
        raise ValueError('the ORCA output has no coordinates before the orbitals')
    atoms = []
    for line in text[starts[-1] :].splitlines()[2:]:
        f = line.split()
        if len(f) != 4 or not re.fullmatch(r'[A-Z][a-z]?', f[0]):
            break
        atoms.append(Atom(f[0], *(_number(v) for v in f[1:])))
    if not atoms:
        raise ValueError('the ORCA coordinates are empty')
    return atoms


def _orca_orbitals(text):
    starts = [m.start() for m in re.finditer(r'MOLECULAR ORBITALS', text)]
    starts = [
        s for s in starts if 'LOEWDIN' not in text[max(0, s - 30) : s] and 'REDUCED' not in text[max(0, s - 30) : s]
    ]
    if not starts:
        raise ValueError('the ORCA output has no «MOLECULAR ORBITALS»: add %output print[p_mos] 1 end')
    start = starts[-1]
    lines = text[start:].splitlines()[2:]
    blocks = []  # per spin: {index: (energy, occupation, {row: (value, token)})}
    labels = []
    k = 0
    current = None
    while k + 3 < len(lines):
        head = lines[k].split()
        if not head or (lines[k].strip().startswith('-') and current is not None):
            k += 1  # blank lines between the column groups; the dashes before the beta orbitals
            continue
        if not all(x.isdigit() for x in head):
            break
        indices = [int(x) for x in head]
        energies = re.findall(ORCA_NUMBER, lines[k + 1])
        occupations = re.findall(ORCA_NUMBER, lines[k + 2])
        if len(energies) != len(indices) or len(occupations) != len(indices):
            break
        if current is None or indices[0] == 0 and current and 0 in current:
            current = {}
            blocks.append(current)
        for n, i in enumerate(indices):
            current[i] = (_number(energies[n]), _number(occupations[n]), [])
        k += 4
        row = 0
        while k < len(lines):
            m = re.match(r'^\s*(\d+)\s*([A-Z][a-z]?)\s+(\d*)([spdfghi])(\S*)\s+(.*)$', lines[k])
            if not m:
                break
            values = re.findall(ORCA_NUMBER, m[6])
            if len(values) != len(indices):
                raise ValueError(f'an ORCA orbital row has {len(values)} numbers for {len(indices)} orbitals')
            if len(blocks) == 1 and indices[0] == 0:
                labels.append((int(m[1]), m[2], m[4], m[5]))
            for n, i in enumerate(indices):
                current[i][2].append(values[n])
            row += 1
            k += 1
        if not blocks or row == 0:
            break
    if not blocks or not labels:
        raise ValueError('the ORCA orbitals could not be read')
    return blocks, labels


def _orca_order(labels):
    """Rows of ORCA (atom, element, letter, suffix) grouped into shells; the permutation into gto order."""
    groups = []
    k = 0
    while k < len(labels):
        atom, element, letter, suffix = labels[k]
        l = LETTERS[letter]
        size = 2 * l + 1
        block = labels[k : k + size]
        if len(block) < size or any(b[0] != atom or b[2] != letter for b in block):
            raise ValueError(f'an incomplete {letter} shell in the ORCA orbitals (atom {atom})')
        if l == 1:
            names = [b[3] for b in block]
            if sorted(names) != ['x', 'y', 'z']:
                raise ValueError(f'unexpected p rows in the ORCA orbitals: {names}')
            local = [names.index('x'), names.index('y'), names.index('z')]
        else:
            local = list(range(size))  # m = 0, +1, -1, +2, -2, ...: the order of gto.pure_order
        groups.append((atom, element, l, [k + j for j in local]))
        k += size
    return groups


def read_orca(text):
    blocks, labels = _orca_orbitals(text)
    start = [m.start() for m in re.finditer(r'MOLECULAR ORBITALS', text)][-1]
    atoms = _orca_coordinates(text, start)
    basis = _orca_basis(text)
    groups = _orca_order(labels)
    shells, permutation = [], []
    per_atom = {}
    for atom, element, l, rows in groups:
        if atom >= len(atoms) or atoms[atom].symbol != element:
            raise ValueError(f'ORCA orbital rows of atom {atom} {element} do not match the coordinates')
        n = per_atom.get(atom, 0)
        per_atom[atom] = n + 1
        if element not in basis or n >= len(basis[element]):
            raise ValueError(f'the ORCA basis of {element} has fewer shells than the orbitals use')
        bl, exponents, coefficients = basis[element][n]
        if bl != l:
            raise ValueError(f'the shells of {element} in the ORCA basis and in the orbitals differ')
        shells.append(Shell(atom, l, l >= 2, exponents, coefficients))
        permutation.extend(rows)
    for atom, count in per_atom.items():
        if count != len(basis[atoms[atom].symbol]):
            raise ValueError(f'atom {atom}: the ORCA orbitals use {count} shells of {len(basis[atoms[atom].symbol])}')
    nbasis = sum(s.size for s in shells)
    _check_size(atoms, nbasis)
    if nbasis != len(labels):
        raise ValueError('the ORCA basis and the orbital rows differ in size')
    permutation = np.array(permutation)
    orbitals, columns, units = [], [], []
    for b, block in enumerate(blocks):
        spin = 'alpha' if b == 0 else 'beta'
        for index in sorted(block):
            energy, occupation, tokens = block[index]
            if len(tokens) != nbasis:
                raise ValueError(f'ORCA orbital {index} has {len(tokens)} coefficients for {nbasis} functions')
            orbitals.append(Orbital(index + 1, spin, energy, occupation))
            columns.append(np.array([_number(t) for t in tokens])[permutation])
            units.append(np.array([half_unit(t) for t in tokens])[permutation])
    coefficients = np.array(columns).T
    half_units = np.array(units).T
    centres = np.array([a.position for a in atoms]) / BOHR
    spins = [o.spin for o in orbitals]
    signs = orca_signs(shells)
    renormalized = _renormalized(shells)
    candidates = [
        ('ORCA', shells, signs),
        ('ORCA (normalized contractions)', renormalized, signs),
        ('standard', shells, None),
        ('unnormalized contractions', renormalized, None),
    ]
    name, chosen, c, found = select(candidates, centres, coefficients, spins, half_units)
    charges = [SYMBOLS.index(a.symbol) + 1 for a in atoms]
    return OrbitalSet(
        '',
        Molecule('ORCA', tuple(atoms)),
        tuple(charges),
        tuple(chosen),
        centres,
        tuple(orbitals),
        c,
        name,
        found,
        'ORCA',
    )


# ---------------------------------------------------------------- dispatch


def kind(text):
    head = text[:4000]
    if head.lstrip().lower().startswith('[molden format]'):
        return 'molden'
    lines = head.splitlines()
    if len(lines) > 3 and re.match(r'^Number of atoms\s+I\s+\d+', lines[2]):
        return 'fchk'
    from modules.spectrum.readers.output_orbitals import has_orbitals  # GAMESS, NWChem, Q-Chem outputs

    if has_orbitals(text):
        from modules.spectrum.readers.outputs import program

        return {'GAMESS': 'gamess', 'NWChem': 'nwchem', 'Q-Chem': 'qchem'}[program(text)]
    from modules.spectrum.readers.mopac_orbitals import has_orbitals as mopac_orbitals  # MOPAC .aux

    if mopac_orbitals(text):
        return 'mopac'
    if 'MOLECULAR ORBITALS' in text and ('ORCA' in text or 'BASIS SET IN INPUT FORMAT' in text):
        return 'orca'
    return None


def read_orbitals(text):
    found = kind(text)
    if found == 'molden':
        return read_molden(text)
    if found == 'fchk':
        return read_fchk(text)
    if found == 'orca':
        return read_orca(text)
    if found == 'mopac':
        from modules.spectrum.readers.mopac_orbitals import read_mopac_orbitals

        return read_mopac_orbitals(text)
    if found in ('gamess', 'nwchem', 'qchem'):
        from modules.spectrum.readers import output_orbitals

        return getattr(output_orbitals, f'read_{found}_orbitals')(text)
    raise ValueError(
        'no orbitals: expected a Molden file, a Gaussian .fchk, an ORCA output with print[p_mos] or a GAMESS, NWChem '
        '(print "final vectors" "final vectors analysis") or Q-Chem (PRINT_ORBITALS, PRINT_GENERAL_BASIS) output, or a '
        'MOPAC .aux'
    )

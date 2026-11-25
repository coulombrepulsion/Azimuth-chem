"""Electronic absorption (TD-DFT, CIS, EOM, ADC), electronic circular dichroism and NMR shieldings
from an ORCA output.

§1 THEORY
    UV-Vis: each excitation i has an energy E_i and an oscillator strength f_i. A band of a finite width
    is modelled by a Gaussian in energy; the decadic molar absorption coefficient then is
        epsilon(nu) = K / (sigma * sqrt(pi)) * sum_i f_i exp(-((nu - nu_i) / sigma)^2) [L mol^-1 cm^-1]
    with nu the wavenumber (cm^-1), sigma the half width at 1/e of the maximum (cm^-1) and
        K = pi e^2 N_A / (1000 ln 10 m_e c^2) = 2.31535e8 L mol^-1 cm^-2 (Gaussian/cgs units),
    so that the integral of epsilon over nu is K f (the textbook relation f = 4.319e-9 * integral of
    epsilon d nu). K / sqrt(pi) = 1.30630e8 is the factor of the Gaussian program's UV-Vis plot.
    FWHM = 2 sqrt(ln 2) sigma. 1 eV = 8065.543937 cm^-1 (CODATA 2018: e / (h c)).
    ECD: each excitation has a rotatory strength R_i (10^-40 esu^2 cm^2 = 10^-40 erg cm^3/G, «cgs»),
    positive or negative; the enantiomer has the opposite signs, an achiral molecule R = 0. With
        R = C_R * integral of delta_epsilon(nu) / nu d nu, C_R = 3000 h c ln 10 / (32 pi^3 N_A)
          = 2.29648e-39 esu^2 cm^2 L^-1 mol cm (Moscowitz; the dipole strength D has 4 C_R = 9.18593e-39),
    a band of the same Gaussian shape as in UV-Vis, scaled by its centre nu_i, gives
        delta_epsilon(nu) = sum_i nu_i R_i / (C_R sigma sqrt(pi)) exp(-((nu - nu_i) / sigma)^2) [L mol^-1 cm^-1]
    (Stephens & Harada, Chirality 22, 229 (2010), eq. 3, written in cm^-1; the ratio nu_i / sigma is the same
    in eV). The velocity gauge is independent of the origin of coordinates; the length gauge is not when the
    basis is incomplete. The velocity R is used when the output has it, else the length R.
    NMR: the chemical shift of a nucleus is delta = sigma_ref - sigma (ppm), sigma_ref the isotropic
    shielding of the same element in the reference molecule (TMS for 1H and 13C) at the same level.
    Atoms that are equivalent by symmetry or fast exchange (a rotating methyl group) give one signal:
    their shieldings are averaged.
§2 ALGORITHM
    read_absorption: the last table «ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS»; three
    row layouts: ORCA 6 «0-1Ag -> 1-3Bu E(eV) E(cm-1) nm fosc ...», ORCA 5 «state cm-1 nm fosc ...»
    or «state cm-1 nm spin forbidden (mult=3)», ORCA 5 ROCIS «from to cm-1 nm fosc». Only excitations
    from the ground state (from-state 0) are kept; spin-forbidden ones get f = 0.
    read_rotatory: the last «CD SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS» (length) and «... VELOCITY
    DIPOLE MOMENTS» (velocity) tables of ORCA 6, or the one «CD SPECTRUM» table of ORCA 5 (taken as length:
    ORCA 5 does not name the gauge); rows as in the absorption tables, R the column after the wavelength.
    The values join the excitations by their label («1-1A», «2-3A» of ORCA 6; the state number of ORCA 5).
    read_shieldings: the last «CHEMICAL SHIELDING SUMMARY (ppm)» table (nucleus index from 0, element,
    isotropic, anisotropy); a calculation for some nuclei only gives only those.
    read_couplings: the last «SUMMARY OF ISOTROPIC COUPLING CONSTANTS J (Hz)» table of ORCA 6 (%eprnmr
    … { ssall }): blocks of at most six columns «i E», rows «i E J J …» — the isotropic total J of every pair once.
    equivalent_groups: atoms related by the symmetry of the geometry — the same Weisfeiler-Lehman
    class of the bond graph and the same sorted distances to the atoms of every element (within
    EQUIVALENT_TOL) — plus the three H of a rotating XH3 group. Topology alone is not enough: the cis
    and trans H of a vinyl =CH2 are topologically equal but do not exchange (26.80 / 27.11 ppm in the
    test data).
§3 APPLICATIONS
    modules/spectrum/readers/orca.py (Output.absorption, Output.shieldings); modules/spectrum/views/spectra_view.py.
§4 SPECIFICATION
    Excitation(state: int, label: str, energy_ev: float, wavenumber: float (cm^-1), wavelength: float (nm),
        fosc: float, multiplicity: int | None, r_length: float | None, r_velocity: float | None (10^-40 cgs));
        Excitation.rotatory -> r_velocity, else r_length, else None.
    read_absorption(text) -> tuple of Excitation (energy order) or; with the rotatory strengths when printed.
    read_rotatory(text) -> {label: (r_length | None, r_velocity | None)}.
    with_rotatory(excitations, table) -> excitations with r_length / r_velocity from table (by label).
    cd_curve(excitations, fwhm_ev, points=1200) -> (wavelength nm increasing, delta_epsilon L mol^-1 cm^-1);
        ValueError for fwhm_ev outside 0.05..2 eV or no excitation with a rotatory strength.
    rotatory_is_zero(excitations) -> True when every |R| < ZERO_ROTATORY (an achiral molecule: no ECD).
    ZERO_ROTATORY = a design choice — chiral molecules give |R| of 1..100; numerical noise
        of planar or symmetric molecules is below 0.01 (benzaldehyde, CAM-B3LYP, length gauge: 0.0047).
    Shielding(atom: int (0-based), element: str, isotropic: float (ppm), anisotropy: float | None).
    read_shieldings(text) -> tuple of Shielding or.
    read_couplings(text) -> tuple of (i, j, J Hz), i < j (0-based), or.
    uv_curve(excitations, fwhm_ev, points=1200) -> (wavelength nm (decreasing energy order: increasing
        nm), epsilon L mol^-1 cm^-1); ValueError for fwhm_ev outside 0.05..2 eV or no allowed excitation.
    shifts(shieldings, reference: {element: sigma_ref}, groups=None) -> [(atoms tuple, element, delta or
        None (no reference), sigma)]: one row per group of equivalent atoms (or per atom), sigma averaged.
    equivalent_groups(molecule, tol=0.01) -> list of tuples of atom indices (each atom in one group).
    EQUIVALENT_TOL = 0.01 A: a design choice — ORCA geometries are symmetric to ~1e-6 A, a hand-built
    structure to ~1e-3 A after «symmetrize»; different environments differ by 0.1 A and more.
§5 PROCEDURES - below.
§6 NOTES
    CD tables: ORCA 6.0.1 outputs of the user (tests/data/orca601) and cclib dvb_td for ORCA 5.0 / 6.0.
    Formats verified 2026-10-23 on real outputs of ORCA 5.0 and 6.0 (cclib test data: dvb_td, dvb_eom_ccsd,
    dvb_adc2, dvb_steom_ccsd, dvb_rocis, dvb_nmr). Constants: CODATA 2018; K derived here and checked in
    the tests from the constants (the 1.3062974e8 of Gaussian's documentation is K/sqrt(pi)).
    ASSUMPTION: the default FWHM of 0.3 eV is a common choice for organic molecules, not a rule.
§7 TESTS
    tests/spectrum/test_orca_spectra.py.
§8' ROBUSTNESS
    Rows that fit none of the layouts end the table; non-finite numbers raise inside and give.
"""

from dataclasses import dataclass
from math import isfinite, log, pi, sqrt
import re

import numpy as np

NUMBER = r'[+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[EeDd][+-]?\d+)?'
EV_CM = 8065.543937  # cm^-1 per eV (CODATA 2018)
K_ABSORPTION = 2.31535e8  # L mol^-1 cm^-2 per unit oscillator strength (§1; tests derive it from CODATA)
C_ROTATORY = 2.29648e-39  # esu^2 cm^2 per (L mol^-1 cm^-1): R = C_R * integral of delta_epsilon / nu (§1; tests: CODATA)
ZERO_ROTATORY = 0.1  # 10^-40 cgs: below it on every excitation the molecule is taken as achiral (a design choice, §4)
DEFAULT_FWHM = 0.3  # eV
EQUIVALENT_TOL = 0.01  # A: symmetry-equivalent atoms have the same distances (a design choice, §4)


def _number(text):
    value = float(text.replace('D', 'E').replace('d', 'e'))
    if not isfinite(value):
        raise ValueError('non-finite number')
    return value


@dataclass(frozen=True)
class Excitation:
    state: int
    label: str
    energy_ev: float
    wavenumber: float
    wavelength: float
    fosc: float
    multiplicity: int | None = None
    r_length: float | None = None  # rotatory strength, 10^-40 cgs, length gauge
    r_velocity: float | None = None  # the same, velocity gauge (independent of the origin)

    @property
    def rotatory(self):
        return self.r_velocity if self.r_velocity is not None else self.r_length


@dataclass(frozen=True)
class Shielding:
    atom: int
    element: str
    isotropic: float
    anisotropy: float | None = None


ROW6 = re.compile(
    r'^\s*(\d+)-([\d.]+)(\S*)\s*->\s*(\d+)-([\d.]+)(\S*)\s+('
    + NUMBER
    + r')\s+('
    + NUMBER
    + r')\s+('
    + NUMBER
    + r')\s+('
    + NUMBER
    + ')'
)
ROW5 = re.compile(r'^\s*(\d+)\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+' + NUMBER)
FORBIDDEN5 = re.compile(r'^\s*(\d+)\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+spin forbidden \(mult=(\d+)\)')
ROCIS5 = re.compile(r'^\s*(\d+)\s+(\d+)\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+(' + NUMBER + r')\s+' + NUMBER)


def _multiplicity(text):
    try:
        value = float(text)
    except ValueError:
        return None
    return int(round(value)) if abs(value - round(value)) < 1e-9 else None


def read_absorption(text):
    starts = [m.end() for m in re.finditer(r'ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS', text)]
    if not starts:
        return ()
    lines = text[starts[-1] :].splitlines()
    found = []
    started = False
    try:
        for line in lines[1:]:
            stripped = line.strip()
            if not stripped:
                if started:
                    break
                continue
            if set(stripped) <= {'-'} or stripped.startswith(('State', 'Transition', '(', 'States')):
                continue
            m = ROW6.match(line)
            if m:
                started = True
                if int(m[1]) != 0:
                    continue  # excited-state absorption
                found.append(
                    Excitation(
                        int(m[4]),
                        f'{m[4]}-{m[5]}{m[6]}',
                        _number(m[7]),
                        _number(m[8]),
                        _number(m[9]),
                        max(0.0, _number(m[10])),
                        _multiplicity(m[5]),
                    )
                )
                continue
            m = FORBIDDEN5.match(line)
            if m:
                started = True
                cm = _number(m[2])
                found.append(Excitation(int(m[1]), m[1], cm / EV_CM, cm, _number(m[3]), 0.0, int(m[4])))
                continue
            m = ROCIS5.match(line)
            if m and line.split()[1].isdigit() and len(line.split()) >= 8 and '.' not in line.split()[1]:
                started = True
                if int(m[1]) != 0:
                    continue
                cm = _number(m[3])
                found.append(Excitation(int(m[2]), m[2], cm / EV_CM, cm, _number(m[4]), max(0.0, _number(m[5]))))
                continue
            m = ROW5.match(line)
            if m:
                started = True
                cm = _number(m[2])
                found.append(Excitation(int(m[1]), m[1], cm / EV_CM, cm, _number(m[3]), max(0.0, _number(m[4]))))
                continue
            break
    except ValueError:
        return ()
    found = sorted((e for e in found if e.wavenumber > 0), key=lambda e: e.wavenumber)
    return with_rotatory(found, read_rotatory(text))


CD6 = re.compile(r'^\s*(\d+)-([\d.]+)(\S*)\s*->\s*(\d+)-([\d.]+)(\S*)\s+' + NUMBER + r'\s+' + NUMBER + r'\s+' + NUMBER
                 + r'\s+(' + NUMBER + r')\s+' + NUMBER + r'\s+' + NUMBER + r'\s+' + NUMBER + r'\s*$')
CD5 = re.compile(r'^\s*(\d+)\s+' + NUMBER + r'\s+' + NUMBER + r'\s+(' + NUMBER + r')\s+' + NUMBER + r'\s+' + NUMBER
                 + r'\s+' + NUMBER + r'\s*$')


def _cd_table(text, start):
    """{label: R} of the CD table that begins at start (the end of its title); {} on a bad number."""
    rows = {}
    try:
        for line in text[start:].splitlines()[1:]:
            stripped = line.strip()
            if not stripped:
                if rows:
                    break
                continue
            if set(stripped) <= {'-'} or stripped.startswith(('Transition', 'State', '(')):
                continue
            m = CD6.match(line)
            if m:
                if int(m[1]) == 0:
                    rows[f'{m[4]}-{m[5]}{m[6]}'] = _number(m[7])
                continue
            m = CD5.match(line)
            if m:
                rows[m[1]] = _number(m[2])
                continue
            break
    except ValueError:
        return {}
    return rows


def read_rotatory(text):
    length = velocity = {}
    for title, gauge in ((r'CD SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS', 'length'),
                         (r'CD SPECTRUM VIA TRANSITION VELOCITY DIPOLE MOMENTS', 'velocity'),
                         (r'CD SPECTRUM\s*\n', 'length5')):
        starts = [m.end() for m in re.finditer(title, text)]
        if not starts:
            continue
        rows = _cd_table(text, starts[-1] - (1 if gauge == 'length5' else 0))
        if gauge == 'velocity':
            velocity = rows
        elif not length:  # ORCA 6 has both titles; «CD SPECTRUM» alone is ORCA 5
            length = rows
    return {k: (length.get(k), velocity.get(k)) for k in set(length) | set(velocity)}


def with_rotatory(excitations, table):
    from dataclasses import replace

    if not table:
        return tuple(excitations)
    out = []
    for e in excitations:
        key = e.label if e.label in table else str(e.state)
        r_length, r_velocity = table.get(key, (None, None))
        out.append(replace(e, r_length=r_length, r_velocity=r_velocity))
    return tuple(out)


def rotatory_is_zero(excitations):
    values = [e.rotatory for e in excitations if e.rotatory is not None]
    return bool(values) and max(abs(v) for v in values) < ZERO_ROTATORY


def cd_curve(excitations, fwhm_ev=DEFAULT_FWHM, points=1200):
    if not isfinite(fwhm_ev) or not 0.05 <= fwhm_ev <= 2.0:
        raise ValueError('FWHM must be 0.05-2 eV')
    given = [e for e in excitations if e.rotatory is not None and isfinite(e.rotatory)]
    if not given:
        raise ValueError('no rotatory strength')
    sigma = fwhm_ev * EV_CM / (2 * sqrt(log(2)))
    low = max(1000.0, min(e.wavenumber for e in given) - 4 * sigma)
    high = max(e.wavenumber for e in given) + 4 * sigma
    nu = np.linspace(low, high, points)
    delta = np.zeros_like(nu)
    for e in given:
        delta += e.wavenumber * e.rotatory * 1e-40 / (C_ROTATORY * sigma * sqrt(pi)) * np.exp(-(((nu - e.wavenumber) / sigma) ** 2))
    order = np.argsort(1e7 / nu)
    return (1e7 / nu)[order], delta[order]


def read_shieldings(text):
    starts = [m.end() for m in re.finditer(r'CHEMICAL SHIELDING SUMMARY \(ppm\)', text)]
    if not starts:
        return ()
    row = re.compile(r'^\s*(\d+)\s+([A-Z][a-z]?)\s+(' + NUMBER + r')(?:\s+(' + NUMBER + r'))?\s*$')
    found = []
    try:
        for line in text[starts[-1] :].splitlines()[1:]:
            m = row.match(line)
            if m:
                found.append(Shielding(int(m[1]), m[2], _number(m[3]), _number(m[4]) if m[4] else None))
            elif found:
                break
    except ValueError:
        return ()
    return tuple(found)


def read_couplings(text):
    """The isotropic spin-spin couplings of the last summary table (tests/data/nmr_j, ORCA 6.0.1)."""
    start = text.rfind('SUMMARY OF ISOTROPIC COUPLING CONSTANTS J (Hz)')
    if start < 0:
        return ()
    found = {}
    columns = []
    head = re.compile(r'^\s*(?:\d+\s+[A-Z][a-z]?\s*)+$')
    for line in text[start:].splitlines()[2:]:
        if not line.strip():
            if found:
                break
            continue
        if line.lstrip().startswith('---'):
            continue
        if head.match(line) and not re.search(r'[+-]?\d+\.\d', line):
            columns = [int(m) for m in re.findall(r'(\d+)\s+[A-Z][a-z]?', line)]
            continue
        m = re.match(r'^\s*(\d+)\s+[A-Z][a-z]?\s+(.*)$', line)
        if not m or not columns:
            break
        values = re.findall(NUMBER, m[2])
        if len(values) != len(columns):
            break
        i = int(m[1])
        for j, value in zip(columns, values):
            if i != j:
                found[(min(i, j), max(i, j))] = _number(value)
    return tuple((i, j, v) for (i, j), v in sorted(found.items()) if v is not None and isfinite(v))


def uv_curve(excitations, fwhm_ev=DEFAULT_FWHM, points=1200):
    if not isfinite(fwhm_ev) or not 0.05 <= fwhm_ev <= 2.0:
        raise ValueError('FWHM must be 0.05-2 eV')
    allowed = [e for e in excitations if e.fosc > 0]
    if not allowed:
        raise ValueError('no allowed excitation')
    sigma = fwhm_ev * EV_CM / (2 * sqrt(log(2)))  # half width at 1/e, cm^-1
    low = max(1000.0, min(e.wavenumber for e in allowed) - 4 * sigma)
    high = max(e.wavenumber for e in allowed) + 4 * sigma
    nu = np.linspace(low, high, points)
    epsilon = np.zeros_like(nu)
    for e in allowed:
        epsilon += K_ABSORPTION / (sigma * sqrt(pi)) * e.fosc * np.exp(-(((nu - e.wavenumber) / sigma) ** 2))
    order = np.argsort(1e7 / nu)
    return (1e7 / nu)[order], epsilon[order]


def _topological_classes(molecule):
    """Weisfeiler-Lehman colours of the bond graph, refined until stable."""
    from modules.compass.chemistry.builder import connections

    atoms = molecule.atoms
    neighbours = [[] for _ in atoms]
    for i, j, _ in connections(molecule):
        neighbours[i].append(j)
        neighbours[j].append(i)
    colours = [a.symbol for a in atoms]
    for _ in range(len(atoms) + 1):
        refined = [
            colours[i] + '(' + ','.join(sorted(colours[j] for j in neighbours[i])) + ')' for i in range(len(atoms))
        ]
        table = {c: str(n) for n, c in enumerate(sorted(set(refined)))}
        refined = [atoms[i].symbol + table[c] for i, c in enumerate(refined)]
        stable = len(set(refined)) == len(set(colours))
        colours = refined
        if stable:
            break
    return colours, neighbours


def equivalent_groups(molecule, tol=EQUIVALENT_TOL):
    """Groups of atoms with one NMR signal: symmetry-equivalent atoms (the same topological class and the
    same distances to all other atoms of each element, within tol A) and the H atoms of a rotating XH3
    group (X with exactly three H and four neighbours: CH3, NH3+, SiH3)."""
    atoms = molecule.atoms
    colours, neighbours = _topological_classes(molecule)
    positions = np.array([a.position for a in atoms], float)
    distances = np.linalg.norm(positions[:, None, :] - positions[None, :, :], axis=-1)
    symbols = [a.symbol for a in atoms]
    fingerprint = []
    for i in range(len(atoms)):
        fingerprint.append(
            {
                e: np.sort(distances[i][[j for j in range(len(atoms)) if symbols[j] == e and j != i]])
                for e in set(symbols)
            }
        )
    parent = list(range(len(atoms)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i, j):
        parent[find(i)] = find(j)

    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            if colours[i] == colours[j] and all(
                np.max(np.abs(fingerprint[i][e] - fingerprint[j][e]), initial=0.0) < tol for e in fingerprint[i]
            ):
                union(i, j)
    for x in range(len(atoms)):
        hydrogens = [j for j in neighbours[x] if symbols[j] == 'H']
        if len(hydrogens) == 3 and len(neighbours[x]) == 4 and symbols[x] != 'H':
            union(hydrogens[0], hydrogens[1])
            union(hydrogens[0], hydrogens[2])
    groups = {}
    for i in range(len(atoms)):
        groups.setdefault(find(i), []).append(i)
    return sorted((tuple(g) for g in groups.values()), key=lambda g: g[0])


def shifts(shieldings, reference, groups=None):
    by_atom = {s.atom: s for s in shieldings}
    if groups is None:
        groups = [(s.atom,) for s in shieldings]
    rows = []
    for group in groups:
        members = [by_atom[a] for a in group if a in by_atom]
        if not members:
            continue
        element = members[0].element
        if any(m.element != element for m in members):
            raise ValueError('a group mixes elements')
        sigma = sum(m.isotropic for m in members) / len(members)
        ref = reference.get(element)
        rows.append((tuple(m.atom for m in members), element, None if ref is None else ref - sigma, sigma))
    return rows

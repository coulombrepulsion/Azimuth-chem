"""Thermochemistry of an ideal gas from a frequency calculation: ZPE, E, H, S, G at T and P.

§1 THEORY
    Rigid rotor – harmonic oscillator (RRHO), as in every quantum-chemistry program: the molecule is an
    ideal gas; translation, rotation, vibration and the electronic ground state are independent.
    Translation: q = (2π m k T / h²)^{3/2} k T / P, S = R (ln q + 5/2), E = 3/2 R T, Cv = 3/2 R.
    Rotation (nonlinear): q = √π / σ · (T³ / (Θa Θb Θc))^{1/2}, Θ = h² / (8 π² I k), S = R (ln q + 3/2),
    E = 3/2 R T; linear: q = T / (σ Θ), S = R (ln q + 1), E = R T. σ — the rotational symmetry number
    (the number of rotations of the point group, proper ones only).
    Vibration (energy from the bottom of the well, ZPE included), Θv = h c ν̃ / k:
    E = R Σ Θv (1/2 + 1/(e^{Θv/T} − 1)), S = R Σ [(Θv/T)/(e^{Θv/T} − 1) − ln(1 − e^{−Θv/T})],
    Cv = R Σ (Θv/T)² e^{Θv/T} / (e^{Θv/T} − 1)². Electronic: S = R ln(2S + 1).
    H = E + R T (pV of an ideal gas), G = H − T S. Low modes (ν̃ ≲ 100 cm⁻¹) are poor harmonic oscillators
    and their S grows without limit as ν̃ → 0; Grimme's quasi-RRHO (Chem. Eur. J. 18, 9955 (2012)) mixes
    S_vib with the entropy of a free rotor of the same moment μ = h / (8π² c ν̃), reduced with
    B_av = 10⁻⁴⁴ kg m²: S_R = R (1/2 + ln((8π³ μ' k T / h²)^{1/2})), μ' = μ B_av / (μ + B_av),
    S = w S_V + (1 − w) S_R, w = 1 / (1 + (ν̃0/ν̃)⁴), ν̃0 = 100 cm⁻¹ (the energy stays harmonic; ORCA uses
    the same for S).
§2 ALGORITHM Masses of the most abundant isotopes (MASSES; elements without an entry: the standard atomic weight,
    reported in notes); the centre of mass, the inertia tensor and its eigenvalues (numpy); the molecule is linear when
    the smallest moment is < 1e-3 of the largest (3N − 5 modes); imaginary and zero frequencies are left out and
    reported (all imaginary and above −SMALL_IMAGINARY_CM: «a nearly free rotor or noise», not «not a minimum»).
    symmetry_number(point group) for the groups of modules/compass/chemistry/symmetry.py.
    find_multiplicity(text): the last multiplicity printed by ORCA, Gaussian, Psi4, GAMESS («SPIN MULTIPLICITY =»),
    NWChem («Spin multiplicity:») and Q-Chem (the second number of
    $molecule), MOPAC («DOUBLET STATE CALCULATION» and the other spin words; «RHF CALCULATION, NO. OF
    DOUBLY OCCUPIED LEVELS» without «SINGLY OCCUPIED» — a singlet), else None; multiplicity(text) — the same, 1 when
    nothing is printed (the callers say so).
    The vibrational terms are written with q = exp(−x) (x = θ/T): 1/(eˣ − 1) = q/(1 − q),
    ln(1 − e⁻ˣ) = log1p(−q), Cv = R x² q/(1 − q)², 1 − q = −expm1(−x) — finite for every x (before, (eˣ − 1)²
    overflowed for x > 355, e.g. 3000 cm⁻¹ at 10 K).
§3 APPLICATIONS
    modules/spectrum/views/thermo_view.py (the «Термохимия» tab of Spectrum).
§4 SPECIFICATION
    thermochemistry(molecule, frequencies, energy=None, temperature=298.15, pressure=101325.0,
                    multiplicity=1, sigma=1, qrrho=False) -> Thermo
    Thermo: zpe, thermal_energy (E − E_el), enthalpy (H − E_el), entropy (Eh/K, total), gibbs (G − E_el)
    in hartree per molecule; parts {translational, rotational, vibrational, electronic}: (E, S, Cv);
    totals E0 + correction when energy is given (total_* properties); linear, modes, left_out, notes.
    symmetry_number(name) -> int; find_multiplicity(text) -> int | None; multiplicity(text) -> int. ValueError: no
    atoms, T ≤ 0, P ≤ 0, σ < 1.
§5 PROCEDURES - below.
§6 NOTES
    Constants CODATA 2018. Verified 2026-10-24 against the thermochemistry printed by Psi4 1.7 for
    divinylbenzene (cclib test data, tests/data/psi4/dvb_ir_rhf_psi4-1.7.out): ZPE, E, H, S, G corrections.
    And against MOPAC 23.2.5 THERMO for water (tests/data/mopac/h2o_pm7_force_thermo.out): H(T) − ZPE and the
    translational, rotational, vibrational entropies at 298 and 398 K (MOPAC: P = 1 atm, average atomic masses —
    0.001 cal/(mol·K) apart in S_trans). The open-shell RHF print of MOPAC contains «SINGLY OCCUPIED»
    (CH3, PM7 RHF, MOPAC 23.2.5: «NO. OF SINGLY OCCUPIED LEVELS = 1»).
§7 TESTS
    tests/spectrum/test_thermo.py.
§8' ROBUSTNESS
    Overflow-safe exponentials (Θv/T > 700 contributes only its ZPE).
"""

from dataclasses import dataclass, field
import math
import re

import numpy as np

from azimuth.i18n import tr

H = 6.62607015e-34  # J s
KB = 1.380649e-23  # J/K
C = 299792458.0  # m/s
NA = 6.02214076e23
HARTREE = 4.3597447222071e-18  # J
AMU = 1.66053906660e-27  # kg
R = KB * NA
KCAL = HARTREE * NA / 4184.0  # kcal/mol per hartree
KJ = HARTREE * NA / 1000.0  # kJ/mol per hartree
B_AV = 1e-44  # kg m², Grimme's average moment
SMALL_IMAGINARY_CM = 30.0  # cm⁻¹: as modules/sextant/doctor.SMALL_CM — a nearly free rotor or noise, not a saddle
NU0 = 100.0  # cm⁻¹

# most abundant isotopes (u), AME 2016 / NIST
MASSES = {
    'H': 1.00782503223, 'He': 4.00260325413, 'Li': 7.0160034366, 'Be': 9.012183065, 'B': 11.00930536,
    'C': 12.0, 'N': 14.00307400443, 'O': 15.99491461957, 'F': 18.99840316273, 'Ne': 19.9924401762,
    'Na': 22.989769282, 'Mg': 23.985041697, 'Al': 26.98153853, 'Si': 27.97692653465, 'P': 30.97376199842,
    'S': 31.9720711744, 'Cl': 34.968852682, 'Ar': 39.9623831237, 'K': 38.9637064864, 'Ca': 39.962590863,
    'Sc': 44.95590828, 'Ti': 47.94794198, 'V': 50.94395704, 'Cr': 51.94050623, 'Mn': 54.93804391,
    'Fe': 55.93493633, 'Co': 58.93319429, 'Ni': 57.93534241, 'Cu': 62.92959772, 'Zn': 63.92914201,
    'Ga': 68.9255735, 'Ge': 73.921177761, 'As': 74.92159457, 'Se': 79.9165218, 'Br': 78.9183376,
    'Kr': 83.9114977282, 'Rb': 84.9117897379, 'Sr': 87.9056125, 'Y': 88.9058403, 'Zr': 89.9046977,
    'Nb': 92.906373, 'Mo': 97.90540482, 'Ru': 101.9043441, 'Rh': 102.905498, 'Pd': 105.9034804,
    'Ag': 106.9050916, 'Cd': 113.90336509, 'In': 114.903878776, 'Sn': 119.90220163, 'Sb': 120.903812,
    'Te': 129.906222748, 'I': 126.9044719, 'Xe': 131.9041550856, 'Cs': 132.905451961, 'Ba': 137.905247,
    'Hf': 179.946557, 'Ta': 180.9479958, 'W': 183.95093092, 'Re': 186.9557501, 'Os': 191.961477,
    'Ir': 192.9629216, 'Pt': 194.9647917, 'Au': 196.96656879, 'Hg': 201.9706434, 'Tl': 204.9744278,
    'Pb': 207.9766525, 'Bi': 208.9803991,
}
SIGMA = {'T': 12, 'Td': 12, 'Th': 12, 'O': 24, 'Oh': 24, 'I': 60, 'Ih': 60, 'D∞h': 2, 'Dinfh': 2, 'C∞v': 1, 'Cinfv': 1}


def symmetry_number(name):
    """The rotational symmetry number of a point group name (C1, Cs, Ci, Cn, Cnv, Cnh, Dn, Dnh, Dnd, Sn, …)."""
    if not name:
        return 1
    if name in SIGMA:
        return SIGMA[name]
    m = re.fullmatch(r'([CDS])(\d+)([vhd]?)', name)
    if not m:
        return 1
    letter, n, _ = m[1], int(m[2]), m[3]
    if letter == 'C':
        return n
    if letter == 'D':
        return 2 * n
    return n // 2  # S2n: the rotations are the C_n subgroup


MULTIPLICITY = (
    r'Multiplicity\s+Mult\s+\.+\s+(\d+)',  # ORCA
    r'Charge\s*=\s*-?\d+\s+Multiplicity\s*=\s*(\d+)',  # Gaussian
    r'charge\s*=\s*-?\d+,\s*multiplicity\s*=\s*(\d+)',  # Psi4
    r'SPIN MULTIPLICITY\s*=\s*(\d+)',  # GAMESS (US), Firefly
    r'Spin multiplicity:\s*(\d+)',  # NWChem
    r'\$molecule\s*\n\s*[+-]?\d+\s+(\d+)\s*\n',  # Q-Chem: charge and multiplicity of the input
)


SPIN_WORDS = {'SINGLET': 1, 'DOUBLET': 2, 'TRIPLET': 3, 'QUARTET': 4, 'QUINTET': 5, 'SEXTET': 6, 'SEPTET': 7,
              'OCTET': 8, 'NONET': 9}
MOPAC_STATE = r'\b(' + '|'.join(SPIN_WORDS) + r') STATE CALCULATION'  # MOPAC, e.g. «DOUBLET STATE CALCULATION»
MOPAC_CLOSED = r'RHF CALCULATION, NO\. OF DOUBLY OCCUPIED LEVELS'  # MOPAC closed shell


def find_multiplicity(text):
    """The last multiplicity printed in an output, or None (no silent singlet)."""
    text = text or ''
    found = [(m.start(), int(m[1])) for rx in MULTIPLICITY for m in re.finditer(rx, text)]
    found += [(m.start(), SPIN_WORDS[m[1]]) for m in re.finditer(MOPAC_STATE, text)]
    if not found and 'SINGLY OCCUPIED' not in text:
        found = [(m.start(), 1) for m in re.finditer(MOPAC_CLOSED, text)]
    return max(found)[1] if found else None


def multiplicity(text):
    found = find_multiplicity(text)
    return found if found is not None else 1


def _mass(symbol, notes):
    if symbol in MASSES:
        return MASSES[symbol]
    from modules.compass.chemistry.symmetry import _symfind

    notes.append(tr(f'Для {symbol} взята средняя атомная масса, а не масса изотопа.'))
    return float(_symfind()._w(symbol))


@dataclass(frozen=True)
class Thermo:
    temperature: float
    pressure: float
    sigma: int
    multiplicity: int
    linear: bool
    modes: int
    zpe: float
    thermal_energy: float
    enthalpy: float
    entropy: float
    gibbs: float
    parts: dict
    energy: float | None = None
    left_out: tuple = ()
    qrrho: bool = False
    notes: tuple = field(default=())

    def total(self, correction):
        return None if self.energy is None else self.energy + correction


def _vibration(freqs, T, qrrho, moments_unused=None):
    e = s = cv = zpe = 0.0
    for nu in freqs:
        theta = H * C * nu * 100.0 / KB  # nu in cm⁻¹
        x = theta / T
        zpe += R * theta / 2
        q = math.exp(-x)  # finite for every x (exp(x) and (e^x - 1)^2 overflowed)
        one = -math.expm1(-x)  # 1 - q, accurate for small x too
        e += R * theta * (0.5 + q / one)
        s_v = R * (x * q / one - math.log1p(-q))
        cv += R * x * x * q / (one * one)
        if qrrho:
            mu = H / (8 * math.pi ** 2 * C * nu * 100.0)
            mu_red = mu * B_AV / (mu + B_AV)
            s_r = R * (0.5 + math.log(math.sqrt(8 * math.pi ** 3 * mu_red * KB * T / H ** 2)))
            w = 1.0 / (1.0 + (NU0 / nu) ** 4)
            s_v = w * s_v + (1 - w) * s_r
        s += s_v
    return zpe, e, s, cv


def thermochemistry(molecule, frequencies, energy=None, temperature=298.15, pressure=101325.0, multiplicity=1,
                    sigma=1, qrrho=False):
    if not molecule or not molecule.atoms:
        raise ValueError(tr('Нет геометрии для термохимии.'))
    if not (temperature > 0 and pressure > 0) or sigma < 1 or multiplicity < 1:
        raise ValueError(tr('Температура и давление должны быть больше нуля, число симметрии — не меньше 1.'))
    T, P = float(temperature), float(pressure)
    notes = []
    masses = np.array([_mass(a.symbol, notes) for a in molecule.atoms]) * AMU
    xyz = np.array([a.position for a in molecule.atoms]) * 1e-10
    total = masses.sum()
    centre = (masses[:, None] * xyz).sum(0) / total
    r = xyz - centre
    inertia = np.zeros((3, 3))
    for m, v in zip(masses, r):
        inertia += m * (np.dot(v, v) * np.eye(3) - np.outer(v, v))
    moments = np.sort(np.linalg.eigvalsh(inertia))
    atoms = len(molecule.atoms)
    linear = atoms == 2 or (atoms > 2 and moments[0] < 1e-3 * moments[2])
    expected = 0 if atoms == 1 else 3 * atoms - (5 if linear else 6)

    real = [f for _, f in frequencies if f > 1e-6] if frequencies and isinstance(frequencies[0], tuple) else [
        f for f in frequencies if f > 1e-6
    ]
    left = tuple(f for f in ((f if not isinstance(f, tuple) else f[1]) for f in frequencies) if f <= 1e-6)
    # ORCA prints all 3N frequencies, the translations and rotations as
    # exact zeros — those (3N − expected of them) are not modes and not a sign of a saddle point; before, every ORCA
    # frequency calculation said «6 imaginary or zero frequencies — not a minimum»
    external = 3 * atoms - expected if atoms > 1 else 0
    zeros = [f for f in left if abs(f) < 1e-6]
    if external and len(real) + len(left) == 3 * atoms and len(zeros) >= external:
        dropped = 0
        kept = []
        for f in left:
            if dropped < external and abs(f) < 1e-6:
                dropped += 1
                continue
            kept.append(f)
        left = tuple(kept)
    if left and all(-SMALL_IMAGINARY_CM < f < -1e-6 for f in left):  # a nearly free rotor or noise
        notes.append(tr(f'Маленьких мнимых частот: {len(left)} — они не учтены; это почти свободное вращение группы '
                        f'или шум гессиана, G почти не меняется.'))
    elif left:
        notes.append(tr(f'Мнимых и нулевых частот: {len(left)} — они не учтены; это не минимум, и G неточна.'))
    if len(real) + len(left) != expected:
        notes.append(tr(f'Частот {len(real) + len(left)}, а для этой молекулы ожидается {expected}.'))

    q_t = (2 * math.pi * total * KB * T / H ** 2) ** 1.5 * KB * T / P
    s_t = R * (math.log(q_t) + 2.5)
    e_t = 1.5 * R * T
    if atoms == 1:
        s_r = e_r = cv_r = 0.0
    elif linear:
        theta = H ** 2 / (8 * math.pi ** 2 * moments[2] * KB)
        s_r = R * (math.log(T / (sigma * theta)) + 1.0)
        e_r, cv_r = R * T, R
    else:
        thetas = H ** 2 / (8 * math.pi ** 2 * moments * KB)
        q_r = math.sqrt(math.pi) / sigma * math.sqrt(T ** 3 / float(np.prod(thetas)))
        s_r = R * (math.log(q_r) + 1.5)
        e_r, cv_r = 1.5 * R * T, 1.5 * R
    zpe, e_v, s_v, cv_v = _vibration(real, T, qrrho)
    s_e = R * math.log(multiplicity)
    per = 1.0 / (HARTREE * NA)  # J/mol -> hartree per molecule
    parts = {
        'translational': (e_t * per, s_t * per, 1.5 * R * per),
        'rotational': (e_r * per, s_r * per, cv_r * per),
        'vibrational': (e_v * per, s_v * per, cv_v * per),
        'electronic': (0.0, s_e * per, 0.0),
    }
    thermal = (e_t + e_r + e_v) * per
    enthalpy = thermal + R * T * per
    entropy = (s_t + s_r + s_v + s_e) * per
    return Thermo(
        T, P, int(sigma), int(multiplicity), bool(linear), len(real), zpe * per, thermal, enthalpy, entropy,
        enthalpy - T * entropy, parts, energy, left, bool(qrrho), tuple(notes),
    )

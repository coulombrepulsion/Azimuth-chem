"""A hindered internal rotation from a relaxed scan of a dihedral angle: levels, partition function, the correction of G.

§1 THEORY
    A torsion with a low barrier is a poor harmonic oscillator: above the barrier it turns freely. The top is treated as a
    one-dimensional rotor with the reduced moment of inertia I in the potential V(φ) of the scan:
        H = −(ħ²/2I) d²/dφ² + V(φ),   V(φ) = a₀ + Σ_k (a_k cos kφ + b_k sin kφ).
    In the basis of the free rotor e^{imφ}/√2π, m = −M … M: H_mm′ = B m² δ_mm′ + c_{m−m′}, B = ħ²/2I, c_k — the complex
    Fourier coefficients of V (c₀ = a₀, c_{±k} = (a_k ∓ i b_k)/2). Its eigenvalues E_i give, from the lowest level,
        q_hr(T) = (1/σ) Σ_i exp(−(E_i − E₀)/kT),   ZPE_hr = E₀ − V_min,
    σ — the symmetry number of the rotor (3 for a methyl group, 2 for a phenyl or an OH₂ top, 1 for a top without
    symmetry). The free energy of the mode from the bottom of the well: G_hr = ZPE_hr − kT ln q_hr; of the harmonic
    oscillator of wavenumber ν̃ that the frequency calculation put in its place: G_ho = hcν̃/2 + kT ln(1 − e^{−hcν̃/kT}).
    The correction to the G of the rigid rotor – harmonic oscillator is ΔG = G_hr − G_ho, and an equilibrium or rate
    constant computed with G is multiplied by exp(−ΔG/kT) of each species.
    Limits: V = 0 — the free rotor, E_m = B m², q → √(8π³ I kT)/(σh) at high T; a high barrier of n equal wells —
    n harmonic oscillators of ω = √(V″(φ_min)/I), q_hr → (n/σ) q_ho.
    The reduced moment: the molecule is cut at the central bond j–k of the dihedral i–j–k–l into two tops; I_L and I_R
    are their moments about the axis of the bond, 1/I = 1/I_L + 1/I_R (both tops turn about the same axis: the
    approximation I(2,1) of East and Radom for an axis fixed in the bond; the coupling with the overall rotation is
    left out — a few per cent for a light top on a heavy frame, more for two tops of similar size).

§2 ALGORITHM
    points_of(scan) -> [(φ°, E hartree)] of a relaxed scan of one dihedral. unfold(points, cover): the points over
    the whole turn — cover 'full' (the scan goes round, 360°), 'mirror' (0…180° of a potential with V(−φ) = V(φ)),
    'period2', 'period3' (a scan of 180° or 120° of a potential that repeats). cover_of(points) proposes it.
    fit(points) -> Potential: least squares, K = min(8, (N − 1)//2) harmonics for N distinct angles; its minimum on a
    grid of 0.25° and the curvature there. reduced_moment(molecule, j, k) (kg·m²): the two sides of the bond by the
    connectivity (ValueError when the bond is in a ring or a top lies on the axis). levels(potential, moment, M=120).
    row(potential, moment, sigma, wavenumber, T) -> Row; table(…, temperatures).

§3 APPLICATIONS
    modules/spectrum/views/tools_view.py — «Инструменты → Заторможенный ротатор…» of Spectrum.

§4 SPECIFICATION
    Potential(coefficients a (K+1), b (K+1), minimum_angle °, minimum hartree, barrier hartree (max − min),
    curvature hartree/rad², rms hartree — of the fit at the points); value(φ°).
    Row(temperature, q_hr, q_ho, q_free, zpe_hr, zpe_ho, g_hr, g_ho, correction (ΔG), factor exp(−ΔG/kT)) — hartree.
    harmonic_wavenumber(potential, moment) -> cm⁻¹ of the oscillator of the curvature at the minimum.
    ValueError with a message for the user: not a scan of one dihedral, too few points, an unknown cover, a bond in a
    ring, T ≤ 0, σ < 1, ν̃ ≤ 0.

§7 TESTS
    tests/spectrum/test_hindered_rotor.py.

§8 ERROR ANALYSIS
    The levels are variational in M: with M = 120 the lowest hundred are converged to 1e-9 hartree for barriers up to
    tens of kcal/mol and B ≥ 0.1 cm⁻¹. The fit carries the step of the scan: 12 points round the turn resolve six
    harmonics — enough for one- to threefold barriers. The larger errors are physical: a fixed reduced moment (it
    changes along the turn by 5–20 %), and the separation of the torsion from the other modes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from azimuth.i18n import tr
from modules.spectrum.analysis import thermo

COVERS = ('full', 'mirror', 'period2', 'period3')
TEMPERATURES = tuple(float(t) for t in range(200, 601, 50))
CM = 100.0 * thermo.H * thermo.C  # J per cm⁻¹


@dataclass(frozen=True)
class Potential:
    a: tuple
    b: tuple
    minimum_angle: float
    minimum: float
    barrier: float
    curvature: float
    rms: float

    def value(self, angle):
        """V(φ) in hartree, φ in degrees."""
        x = math.radians(angle)
        return sum(self.a[k] * math.cos(k * x) + self.b[k] * math.sin(k * x) for k in range(len(self.a)))


@dataclass(frozen=True)
class Row:
    temperature: float
    q_hr: float
    q_ho: float
    q_free: float
    zpe_hr: float
    zpe_ho: float
    g_hr: float
    g_ho: float
    correction: float
    factor: float


def points_of(scan):
    """[(angle °, energy hartree)] of a relaxed scan of exactly one dihedral angle."""
    coordinates = getattr(scan, 'coordinates', ()) if scan is not None else ()
    if scan is None or scan.kind not in ('relaxed', 'unrelaxed') or len(coordinates) != 1 or coordinates[0].kind != 'dihedral':
        raise ValueError(tr('Нужен скан одного двугранного угла (задача «Скан ППЭ с релаксацией» по торсионному углу).'))
    found = [(p.values[0], p.energy) for p in scan.points if p.energy is not None and len(p.values) == 1]
    if len(found) < 5:
        raise ValueError(tr('В скане меньше пяти точек с энергией — для потенциала вращения этого мало.'))
    return found


def cover_of(points):
    """What the scan covers, by its span: 'full' (360°, the last point may be left out), 'mirror' (exactly 180°),
    'period2' (180° without its last point), 'period3' (120°); None — unclear."""
    angles = sorted(a for a, _ in points)
    span = angles[-1] - angles[0]
    step = span / (len(angles) - 1)
    if abs(span - 360.0) < 1e-3 or abs(span + step - 360.0) < 1e-3:
        return 'full'
    if abs(span - 180.0) < 1e-3:
        return 'mirror'
    if abs(span + step - 180.0) < 1e-3:
        return 'period2'
    if abs(span - 120.0) < 1e-3 or abs(span + step - 120.0) < 1e-3:
        return 'period3'
    return None


def unfold(points, cover='full'):
    """The points over the whole turn, angles in [0, 360), one energy per angle (§2)."""
    if cover not in COVERS:
        raise ValueError(tr('Неизвестно, какую часть оборота покрывает скан.'))
    base = [(float(a), float(e)) for a, e in points]
    if cover == 'mirror':
        origin = min(a for a, _ in base)
        base = base + [(2 * origin - a, e) for a, e in base]
    elif cover in ('period2', 'period3'):
        period = 180.0 if cover == 'period2' else 120.0
        base = [(a + n * period, e) for a, e in base for n in range(int(round(360.0 / period)))]
    merged = {}
    for a, e in base:
        key = round(a % 360.0, 3) % 360.0
        merged.setdefault(key, []).append(e)
    out = sorted((a, sum(v) / len(v)) for a, v in merged.items())
    if len(out) < 5:
        raise ValueError(tr('В скане меньше пяти точек с энергией — для потенциала вращения этого мало.'))
    gap = max((b[0] - a[0]) for a, b in zip(out, out[1:] + [(out[0][0] + 360.0, 0.0)]))
    if gap > 90.0:
        raise ValueError(tr('Скан не покрывает весь оборот: сканируйте угол от 0 до 360° или выберите, какую часть '
                            'оборота он покрывает.'))
    return out


def fit(points, cover='full'):
    """The Fourier series of the scan (§2)."""
    full = unfold(points, cover)
    angles = np.radians([a for a, _ in full])
    energies = np.array([e for _, e in full])
    count = min(8, (len(full) - 1) // 2)
    columns = [np.ones_like(angles)]
    for k in range(1, count + 1):
        columns += [np.cos(k * angles), np.sin(k * angles)]
    solution, *_ = np.linalg.lstsq(np.stack(columns, axis=1), energies, rcond=None)
    a = [float(solution[0])] + [float(solution[2 * k - 1]) for k in range(1, count + 1)]
    b = [0.0] + [float(solution[2 * k]) for k in range(1, count + 1)]
    grid = np.radians(np.arange(0.0, 360.0, 0.25))
    values = sum(a[k] * np.cos(k * grid) + b[k] * np.sin(k * grid) for k in range(count + 1))
    low = int(np.argmin(values))
    x = float(grid[low])
    curvature = sum(-k * k * (a[k] * math.cos(k * x) + b[k] * math.sin(k * x)) for k in range(count + 1))
    fitted = sum(a[k] * np.cos(k * angles) + b[k] * np.sin(k * angles) for k in range(count + 1))
    rms = float(np.sqrt(np.mean((fitted - energies) ** 2)))
    return Potential(tuple(a), tuple(b), math.degrees(x), float(values[low]), float(values.max() - values[low]),
                     float(curvature), rms)


def reduced_moment(molecule, j, k):
    """I of the two tops about the bond j–k (0-based atoms), kg·m² (§1)."""
    from modules.compass.chemistry.editing import connections

    atoms = molecule.atoms
    count = len(atoms)
    if not (0 <= j < count and 0 <= k < count) or j == k:
        raise ValueError(tr('Атомы оси вращения заданы неверно.'))
    neighbours = {n: set() for n in range(count)}
    for first, second, _ in connections(molecule):
        if {first, second} != {j, k}:
            neighbours[first].add(second)
            neighbours[second].add(first)
    side = {j}
    queue = [j]
    while queue:
        for n in neighbours[queue.pop()]:
            if n not in side:
                side.add(n)
                queue.append(n)
    if k in side:
        raise ValueError(tr('Связь, вокруг которой идёт вращение, входит в цикл: волчок нельзя отделить от остова.'))
    notes = []
    origin = np.array(atoms[j].position, dtype=float)
    axis = np.array(atoms[k].position, dtype=float) - origin
    axis /= np.linalg.norm(axis)
    moments = [0.0, 0.0]
    for n, atom in enumerate(atoms):
        r = np.array(atom.position, dtype=float) - origin
        across = r - np.dot(r, axis) * axis
        moments[0 if n in side else 1] += thermo._mass(atom.symbol, notes) * thermo.AMU * float(np.dot(across, across)) * 1e-20
    if min(moments) < 1e-50:
        raise ValueError(tr('Один из волчков лежит на оси вращения — вращать нечего.'))
    return moments[0] * moments[1] / (moments[0] + moments[1])


def rotational_constant(moment):
    """B = ħ²/2I in hartree."""
    if not moment > 0:
        raise ValueError(tr('Приведённый момент инерции должен быть больше нуля.'))
    hbar = thermo.H / (2 * math.pi)
    return hbar * hbar / (2 * moment) / thermo.HARTREE


def levels(potential, moment, size=120):
    """The eigenvalues of §1 in hartree, ascending (2·size + 1 of them)."""
    b = rotational_constant(moment)
    m = np.arange(-size, size + 1)
    matrix = np.zeros((m.size, m.size), dtype=complex)
    matrix[np.diag_indices(m.size)] = b * m.astype(float) ** 2 + potential.a[0]
    for k in range(1, len(potential.a)):
        c = (potential.a[k] - 1j * potential.b[k]) / 2  # the coefficient of e^{ikφ}
        index = np.arange(m.size - k)
        matrix[index + k, index] = c
        matrix[index, index + k] = np.conj(c)
    return np.linalg.eigvalsh(matrix)


def harmonic_wavenumber(potential, moment):
    """ν̃ (cm⁻¹) of the harmonic oscillator of the curvature of V at its minimum."""
    if potential.curvature <= 0:
        raise ValueError(tr('У потенциала нет минимума с положительной кривизной.'))
    omega = math.sqrt(potential.curvature * thermo.HARTREE / moment)
    return omega / (2 * math.pi * thermo.C * 100.0)


def row(potential, moment, sigma=1, wavenumber=None, temperature=298.15, energies=None):
    """The partition functions and the correction of G at one temperature (§1)."""
    if not temperature > 0:
        raise ValueError(tr('Температура должна быть больше нуля.'))
    if type(sigma) is not int or sigma < 1:
        raise ValueError(tr('Число симметрии — целое, не меньше 1.'))
    nu = harmonic_wavenumber(potential, moment) if wavenumber is None else float(wavenumber)
    if not nu > 0:
        raise ValueError(tr('Частота гармонического колебания должна быть больше нуля.'))
    found = levels(potential, moment) if energies is None else energies
    kt = thermo.KB * temperature / thermo.HARTREE
    weights = np.exp(-(found - found[0]) / kt)
    q_hr = float(weights.sum()) / sigma
    zpe_hr = float(found[0] - potential.minimum)
    x = nu * CM / (thermo.KB * temperature)
    q_ho = 1.0 / -math.expm1(-x)
    zpe_ho = 0.5 * nu * CM / thermo.HARTREE
    q_free = math.sqrt(8 * math.pi ** 3 * moment * thermo.KB * temperature) / (sigma * thermo.H)
    g_hr = zpe_hr - kt * math.log(q_hr)
    g_ho = zpe_ho - kt * math.log(q_ho)
    correction = g_hr - g_ho
    return Row(float(temperature), q_hr, q_ho, q_free, zpe_hr, zpe_ho, g_hr, g_ho, correction,
               math.exp(max(min(-correction / kt, 700.0), -700.0)))


def table(potential, moment, sigma=1, wavenumber=None, temperatures=TEMPERATURES):
    found = levels(potential, moment)
    return [row(potential, moment, sigma, wavenumber, t, found) for t in temperatures]

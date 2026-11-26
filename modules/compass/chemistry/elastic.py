"""The elastic constants of a cubic crystal from the energies of strained cells.

§1 THEORY
    A small homogeneous strain ε (a symmetric 3 × 3 matrix; in Voigt's notation ε₁ = ε_xx, ε₂ = ε_yy, ε₃ = ε_zz,
    ε₄ = 2ε_yz, ε₅ = 2ε_xz, ε₆ = 2ε_xy) raises the energy of a crystal at equilibrium by
        E(ε) = E₀ + (V₀ / 2) Σ_ij C_ij ε_i ε_j + O(ε³).
    A cubic crystal has three independent constants: C₁₁, C₁₂ and C₄₄ (axes along the cubic edges). Three strains of
    amplitude e give them, each from the curvature of ΔE/V₀ at e = 0:
        'c11' — a stretch along x, ε₁ = e:                     ΔE/V₀ = ½ C₁₁ e²          → C₁₁ = d²/de²
        'cp'  — a stretch along x and a squeeze along y,
                ε₁ = e, ε₂ = −e:                               ΔE/V₀ = (C₁₁ − C₁₂) e²    → C₁₁ − C₁₂ = ½ d²/de²
        'c44' — a shear in the xy plane, ε₆ = e (ε_xy = e/2):  ΔE/V₀ = ½ C₄₄ e²          → C₄₄ = d²/de²
    Then the bulk modulus B = (C₁₁ + 2C₁₂)/3 (it must agree with that of the equation of state), the anisotropy of
    Zener A = 2C₄₄/(C₁₁ − C₁₂) (1 for an isotropic body) and the Cauchy relation C₁₂ = C₄₄ (it holds for central
    forces between atoms at centres of inversion; its violation measures the non-central part of the bonding).
    A cubic crystal is stable when C₁₁ − C₁₂ > 0, C₁₁ + 2C₁₂ > 0 and C₄₄ > 0 (Born).
    The cell must be at equilibrium for the functional and the settings used (optimize it first): at another volume
    the terms linear in e are not zero and the curvatures are not the constants. Atoms off the centres of inversion
    move inside a sheared cell (silicon), so the atoms are relaxed in every strained cell.
§2 ALGORITHM
    matrix(kind, e) -> ε; deformed(crystal, rows, ε): the rows of the cell (Å, in the frame of the cubic axes) times
    (1 + ε), the fractions of the atoms kept — a crystal of group P 1 with the lengths and the angles of the new rows.
    fit(points, volume): points {kind: [(e, E eV)]} with the unstrained cell (e = 0) in each; a cubic polynomial in e
    by least squares (the odd term takes the asymmetry of a stretch; at least five amplitudes); the curvature 2·c₂
    in eV/Å³ → GPa (× 160.21766).
§4 SPECIFICATION
    KINDS = ('c11', 'cp', 'c44'); AMPLITUDES = (−0.015, −0.010, −0.005, 0.005, 0.010, 0.015); GPA = 160.21766208;
    plan() -> [(kind | None, e)] — the unstrained cell first, then the strains of KINDS by AMPLITUDES.
    Elastic(c11, c12, c44, bulk, anisotropy | None, curves {kind: (coefficients high → low, rms eV/Å³)}, volume),
    all GPa. curve(found, kind, e) -> ΔE/V₀ of the fit, eV/Å³; stable(found) -> bool; lines(found) -> the conclusion (Russian, keys of tr). ValueError with a message
    for the user.
§7 TESTS
    tests/compass/test_elastic.py.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from azimuth.i18n import tr

KINDS = ('c11', 'cp', 'c44')
AMPLITUDES = (-0.015, -0.010, -0.005, 0.005, 0.010, 0.015)
GPA = 160.21766208  # GPa in one eV/Å³


def matrix(kind, e):
    eps = np.zeros((3, 3))
    if kind == 'c11':
        eps[0, 0] = e
    elif kind == 'cp':
        eps[0, 0], eps[1, 1] = e, -e
    elif kind == 'c44':
        eps[0, 1] = eps[1, 0] = e / 2
    else:
        raise ValueError(kind)
    return eps


def plan():
    return [(None, 0.0)] + [(kind, e) for kind in KINDS for e in AMPLITUDES]


def deformed(crystal, rows, eps):
    """The crystal with the cell rows·(1 + ε) and the fractions of its atoms kept (§2)."""
    from modules.compass.chemistry import crystal as cr

    new = np.array(rows, dtype=float) @ (np.eye(3) + np.array(eps, dtype=float))
    lengths = [float(np.linalg.norm(v)) for v in new]

    def angle(u, v):
        return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)), -1.0, 1.0))))

    cell = cr.Cell(lengths[0], lengths[1], lengths[2], angle(new[1], new[2]), angle(new[0], new[2]), angle(new[0], new[1]))
    atoms = [a for a in cr.unit_cell(crystal) if a[0] != 'X']
    sites = tuple(cr.Site(f'{a[0]}{k}', a[0], a[1], a[2], a[3]) for k, a in enumerate(atoms, 1))
    return cr.Crystal(crystal.title, cell, sites, (cr.operation('x, y, z'),), 'P 1')


@dataclass(frozen=True)
class Elastic:
    c11: float
    c12: float
    c44: float
    bulk: float
    anisotropy: float | None
    curves: dict
    volume: float


def fit(points, volume):
    if not volume or volume <= 0:
        raise ValueError(tr('Упругие постоянные: не задан объём ячейки.'))
    curvature, curves = {}, {}
    for kind in KINDS:
        pairs = sorted({(round(float(e), 9), float(energy)) for e, energy in points.get(kind, ())})
        if len(pairs) < 5 or not any(abs(e) < 1e-9 for e, _ in pairs):
            raise ValueError(tr('Упругие постоянные: для деформации {} посчитано меньше пяти точек (вместе с '
                                'недеформированной ячейкой).').format(kind))
        e = np.array([p[0] for p in pairs])
        zero = next(energy for value, energy in pairs if abs(value) < 1e-9)
        density = (np.array([p[1] for p in pairs]) - zero) / volume
        coefficients = np.polyfit(e, density, 3)
        rms = float(np.sqrt(np.mean((np.polyval(coefficients, e) - density) ** 2)))
        curvature[kind] = 2.0 * float(coefficients[1]) * GPA
        curves[kind] = (tuple(float(c) for c in coefficients), rms)
    c11 = curvature['c11']
    c12 = c11 - curvature['cp'] / 2.0
    c44 = curvature['c44']
    return Elastic(c11, c12, c44, (c11 + 2 * c12) / 3.0, 2 * c44 / (c11 - c12) if abs(c11 - c12) > 1e-9 else None,
                   curves, float(volume))


def curve(found, kind, e):
    """ΔE/V₀ of the fit of a strain at the amplitude e, eV/Å³."""
    return float(np.polyval(found.curves[kind][0], e))


def stable(found):
    return found.c11 - found.c12 > 0 and found.c11 + 2 * found.c12 > 0 and found.c44 > 0


def lines(found):
    text = [tr('Упругие постоянные: C₁₁ = {} ГПа, C₁₂ = {} ГПа, C₄₄ = {} ГПа.').format(
        f'{found.c11:.1f}', f'{found.c12:.1f}', f'{found.c44:.1f}'),
        tr('Модуль всестороннего сжатия B = (C₁₁ + 2C₁₂)/3 = {} ГПа — сравните с B₀ уравнения состояния.').format(
            f'{found.bulk:.1f}')]
    if found.anisotropy is not None:
        text.append(tr('Анизотропия A = 2C₄₄/(C₁₁ − C₁₂) = {} (1 — изотропное тело). Соотношение Коши: C₁₂ − C₄₄ = {} ГПа.')
                    .format(f'{found.anisotropy:.2f}', f'{found.c12 - found.c44:+.1f}'))
    if not stable(found):
        text.append(tr('Условия устойчивости кубического кристалла нарушены (нужно C₁₁ − C₁₂ > 0, C₁₁ + 2C₁₂ > 0, '
                       'C₄₄ > 0): ячейка не в равновесии или расчёт не сошёлся.'))
    text.append(tr('Постоянные верны для равновесной ячейки: сначала оптимизируйте её тем же функционалом и с теми же '
                   'настройками.'))
    return text

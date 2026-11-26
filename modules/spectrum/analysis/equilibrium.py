"""The equilibrium of two forms of one molecule (conformers, tautomers, isomers): K(T), the shares and what K is made of.

§1 THEORY
    A ⇌ B, both ideal gases of the same composition. K(T) = x_B / x_A = (n_B q_B / n_A q_A) · exp(−ΔE₀ / kT),
    ΔE₀ = (E_B + ZPE_B) − (E_A + ZPE_A), q — the partition function per molecule counted from the zero-point level,
    q = q_trans · q_rot · q_vib · q_el (rigid rotor, harmonic oscillator: modules/spectrum/analysis/thermo.py §1),
    n — the number of mirror forms (2 for a chiral form whose two enantiomers are both present, else 1). So
        K = exp(−ΔE₀/kT) · f_trans · f_rot · f_vib · f_el · f_mirror,   f_x = q_x(B) / q_x(A),   f_mirror = n_B / n_A.
    f_trans = 1 for isomers (the same mass). The rotational symmetry number σ stands in q_rot (q_rot ∝ 1/σ): a form with
    σ = 2 has half the rotational states of the same form counted with σ = 1. The shares: x_B = K / (1 + K),
    x_A = 1 / (1 + K). ΔG°(T) = −kT ln K; without the mirror factor it is G_B − G_A of the two thermochemistries.
    Each factor is taken from the thermodynamic functions of thermo.thermochemistry, f_x = exp(−(g_x(B) − g_x(A))/kT)
    with g_trans = E_trans + kT − T S_trans, g_rot = E_rot − T S_rot, g_vib = (E_vib − ZPE) − T S_vib,
    g_el = −T S_el (their sum with the ZPE is G − E_el), so the quasi-RRHO entropy of the low modes is in f_vib when
    it is asked for.

§2 ALGORITHM
    point(a, b, T, …): two thermochemistries at T, the differences, the factors, K, the shares.
    table(a, b, temperatures, …) -> [Point]. mirror_forms(geometry): 2 when the point group has no improper element
    (C1, Cn, Dn, T, O, I), else 1 — a proposal the user may change (two enantiomers count as one form when only one
    of them is in the sample).
    Refused (ValueError): a form without frequencies or geometry, different atoms, σ < 1 or n not 1 or 2, T ≤ 0.
    warnings(a, b): those of reaction.suitability (levels of theory, imaginary frequencies, charges, multiplicity).

§3 APPLICATIONS
    modules/spectrum/views/tools_view.py — «Инструменты → Равновесие двух форм…» of Spectrum.

§4 SPECIFICATION
    Point(temperature, delta_e0, delta_g — hartree, constant K, share_a, share_b, factors {'energy', 'translational',
    'rotational', 'vibrational', 'electronic', 'mirror'} — their product is K).
    point(a, b, temperature=298.15, pressure=101325.0, qrrho=False, sigma=None, mirror=(1, 1)) -> Point; a, b —
    reaction.Species; sigma — (σ_A, σ_B) or None for those of the species.
    table(a, b, temperatures=TEMPERATURES, …) -> [Point]; TEMPERATURES = 200 … 600 K in steps of 50.
    mirror_forms(geometry) -> 1 | 2; warnings(a, b) -> [text].

§7 TESTS
    tests/spectrum/test_equilibrium.py.

§8 ERROR ANALYSIS
    K is exponential in ΔE₀: an error of 1 kcal/mol in the energy difference is a factor of 5.4 in K at 298 K — the
    level of theory of ΔE decides, the partition functions rarely change K by more than a factor of 2–3 (σ and the
    mirror forms exactly by integers). Low torsional modes are poor harmonic oscillators (thermo.py §1).
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass

from azimuth.i18n import tr
from modules.spectrum.analysis import thermo

TEMPERATURES = tuple(float(t) for t in range(200, 601, 50))
FACTORS = ('energy', 'translational', 'rotational', 'vibrational', 'electronic', 'mirror')
_CHIRAL = re.compile(r'^(C\d+|D\d+|T|O|I)$')
ATM = 101325.0


@dataclass(frozen=True)
class Point:
    temperature: float
    delta_e0: float
    delta_g: float
    constant: float
    share_a: float
    share_b: float
    factors: dict


def mirror_forms(geometry):
    """2 for a chiral point group (no mirror plane, inversion centre or improper axis), else 1 (§2)."""
    try:
        from modules.compass.chemistry.symmetry import analyze

        found = analyze(geometry)
        name = found.get('name', '') if 'err' not in found else ''
    except Exception:  # noqa: BLE001 — only a proposal; 1 when the group is not found
        return 1
    return 2 if _CHIRAL.match(str(name).strip()) else 1


def _parts(species, temperature, pressure, qrrho, sigma):
    if species.geometry is None or not [f for f in species.frequencies if f > 1e-6]:
        raise ValueError(tr(f'У формы «{species.label}» нет частот: для K(T) нужен расчёт «Оптимизация + частоты».'))
    r = thermo.thermochemistry(species.geometry, species.frequencies, None, temperature, pressure,
                               species.multiplicity or 1, sigma, qrrho)
    kt = thermo.KB * temperature / thermo.HARTREE
    e_t, s_t, _ = r.parts['translational']
    e_r, s_r, _ = r.parts['rotational']
    e_v, s_v, _ = r.parts['vibrational']
    _, s_e, _ = r.parts['electronic']
    return {
        'zpe': r.zpe,
        'translational': e_t + kt - temperature * s_t,
        'rotational': e_r - temperature * s_r,
        'vibrational': e_v - r.zpe - temperature * s_v,
        'electronic': -temperature * s_e,
    }


def _exp(x):
    return math.exp(max(min(x, 700.0), -700.0))


def point(a, b, temperature=298.15, pressure=ATM, qrrho=False, sigma=None, mirror=(1, 1)):
    """K, the shares and the factors of A ⇌ B at one temperature (§1)."""
    if not temperature > 0 or not pressure > 0:
        raise ValueError(tr('Температура и давление должны быть больше нуля.'))
    if a.counts and b.counts and tuple(a.counts) != tuple(b.counts):
        raise ValueError(tr(f'Формы разного состава ({a.formula} и {b.formula}): равновесие двух форм — для изомеров.'))
    sigma_a, sigma_b = sigma if sigma is not None else (a.sigma or 1, b.sigma or 1)
    if type(sigma_a) is not int or type(sigma_b) is not int or sigma_a < 1 or sigma_b < 1:
        raise ValueError(tr('Число симметрии — целое, не меньше 1.'))
    if tuple(mirror) not in ((1, 1), (1, 2), (2, 1), (2, 2)):
        raise ValueError(tr('Число зеркальных форм — 1 или 2.'))
    pa = _parts(a, temperature, pressure, qrrho, sigma_a)
    pb = _parts(b, temperature, pressure, qrrho, sigma_b)
    kt = thermo.KB * temperature / thermo.HARTREE
    delta_e0 = (b.energy + pb['zpe']) - (a.energy + pa['zpe'])
    factors = {'energy': _exp(-delta_e0 / kt)}
    for key in ('translational', 'rotational', 'vibrational', 'electronic'):
        factors[key] = _exp(-(pb[key] - pa[key]) / kt)
    factors['mirror'] = mirror[1] / mirror[0]
    log_k = -delta_e0 / kt + math.log(factors['mirror']) - sum(
        (pb[key] - pa[key]) / kt for key in ('translational', 'rotational', 'vibrational', 'electronic'))
    constant = _exp(log_k)
    share_b = 1.0 / (1.0 + _exp(-log_k))
    return Point(float(temperature), delta_e0, -kt * log_k, constant, 1.0 - share_b, share_b, factors)


def table(a, b, temperatures=TEMPERATURES, pressure=ATM, qrrho=False, sigma=None, mirror=(1, 1)):
    return [point(a, b, t, pressure, qrrho, sigma, mirror) for t in temperatures]


def warnings(a, b):
    from modules.spectrum.analysis import reaction

    return list(reaction.suitability([a, b], 'ensemble'))

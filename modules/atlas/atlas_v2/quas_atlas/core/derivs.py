"""Properties as derivatives of the energy: finite differences and the choice of the step, the finite-field dipole
moment and polarizability, the two-level picture of the polarizability and the basis.

HEADER
    Model of the page "Свойства как производные энергии" (web/<lang>/derivatives.html), Atlas 2026-11-24; lectures 1
    and 5 of the course «Квантово-химические методы». Wilkinson convention, sections 1-8.

§1 THEORY
    In a field F the energy is a series E(F) = E0 − μF − ½αF² − (1/6)βF³ − (1/24)γF⁴: the properties are its
    derivatives, μ = −∂E/∂F, α = −∂²E/∂F² (Hellmann–Feynman: dE/dλ = ⟨Ψ|∂Ĥ/∂λ|Ψ⟩ for an exact or a fully variational
    function). Finite differences from the Taylor series f(x ± h) = f ± hf′ + h²f″/2 ± h³f‴/6 + …:
        forward (f(x+h) − f(x))/h = f′ + (h/2)f″ + …;  central (f(x+h) − f(x−h))/(2h) = f′ + (h²/6)f‴ + …;
        second (f(x+h) + f(x−h) − 2f(x))/h² = f″ + (h²/12)f⁗ + ….
    With energies known to δE the noise is ~δE/h (first derivative) and ~δE/h² (second): a small step is as bad as a
    large one. The optimum of the central difference h ≈ (3δE/|f‴|)^{1/3}. The lecture's example: a Morse curve
    E(R) = De(1 − e^{−a(R−Re)})², De = 0.17, a = 1.0, Re = 1.4 bohr, at R = 1.6: E′ = 0.050460; energies rounded to
    10⁻⁶ hartree — the best is the central difference with h = 0.01, h_opt ≈ (3·10⁻⁶/0.63)^{1/3} ≈ 0.017 bohr.
    Finite field: μ = −(E₊ − E₋)/(2F), α = −(E₊ + E₋ − 2E₀)/F²: the error of the energy δE gives δα ~ 2δE/F²
    (δE = 10⁻⁸: 2 at F = 10⁻⁴, 0.02 at 10⁻³, 0.005 at 2·10⁻³); from the dipole in the field α = (μ(F) − μ(−F))/(2F)
    and δα ~ δμ/F — the noise is divided by F, not F². Water: ½αF² at F = 2·10⁻³ is 2·10⁻⁵ hartree, 0.05 kJ/mol.
    Two levels: α = 2Σ|⟨n|μ̂|0⟩|²/(E_n − E0) ≈ 2|μ01|²/ΔE: large transition dipoles and small gaps give a large α.
    The field pulls the density outward, where only diffuse functions can describe it: B3LYP for water (ORCA 6.0.1,
    23.11.2026, the lecture): def2-SVP 5.32, def2-TZVP 6.77, def2-SVPD 9.76, def2-TZVPD 9.95, aug-cc-pVTZ 9.92 a.u.;
    the experiment 9.8 a.u.

§2 ALGORITHM
    The formulas above; the energies rounded to 10^{−digits} (the lecture's table) or shifted by a fixed pseudo-random
    noise of size δE (the finite field), the dipoles by the same δμ = δE (printed to the same number of digits).

§3 APPLICATIONS
    Endpoints der.steps, der.field, der.twolevel.

§4 SPECIFICATION
    steps(digits, R=1.6) -> {"h": [h], "forward": [|err|], "central": [|err|], "second": [|err|], "exact": {"d1", "d2",
        "d3"}, "h_opt", "best": {"forward": {"h", "err"}, "central": {...}, "second": {...}}}.
    field(lgF, lgdE) -> {"F": [F], "mu_err": [], "alpha_E_err": [], "alpha_mu_err": [], "at": {"mu", "alpha_E",
        "alpha_mu", "F", "kj"}, "true": {"mu", "alpha"}}.
    twolevel(mu01, dE) -> {"alpha", "basis": [{"name", "alpha"}], "exp"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (the site runs it in Pyodide). Atomic units: 1 a.u. of dipole = 2.5417 D; 1 hartree =
    2625.5 kJ/mol.
§7 TEST CASES (tests/atlas/test_atlas_derivs.py)
    The lecture's table: E′(1.6) = 0.050460; with exact energies the forward error 7.9·10⁻³ at h = 0.1 and the central
    −1.1·10⁻³; rounded to 10⁻⁶: the best central at h = 0.01 (−9.6·10⁻⁶), the forward at h = 10⁻⁵ is −5·10⁻² (zero
    difference); h_opt ≈ 0.017. The finite field: α exact without noise to O(F²), δα ~ 2δE/F²; two levels.
§8 ERROR ANALYSIS
    The model molecule of the finite field has the textbook values of water (μ = 0.728 a.u. = 1.85 D, α = 9.8 a.u.) and
    illustrative β, γ.
"""

import math

DE, A, RE = 0.17, 1.0, 1.4
WATER = {"mu": 0.728, "alpha": 9.8, "beta": -18.0, "gamma": 1200.0}
BASIS = [("def2-SVP", 5.32), ("def2-TZVP", 6.77), ("def2-SVPD", 9.76), ("def2-TZVPD", 9.95), ("aug-cc-pVTZ", 9.92)]
EXP_ALPHA = 9.8
HARTREE_KJ = 2625.4996


def morse(R):
    return DE * (1 - math.exp(-A * (R - RE))) ** 2


def _morse_derivs(R):
    u = math.exp(-A * (R - RE))
    d1 = 2 * DE * A * u * (1 - u)
    d2 = 2 * DE * A * A * u * (2 * u - 1)
    d3 = 2 * DE * A ** 3 * u * (1 - 4 * u)
    return d1, d2, d3


def _round(e, digits):
    if digits is None:
        return e
    q = 10.0 ** (-digits)
    return round(e / q) * q


def steps(digits=6, R=1.6):
    """The errors of the forward, the central and the second differences against the step, with the energies rounded
    to 10^−digits hartree (digits None: exact)."""
    if digits is not None and not 3 <= digits <= 14:
        raise ValueError("digits 3..14")
    d1, d2, d3 = _morse_derivs(R)
    hs = [10 ** (-5 + 4.5 * i / 90) for i in range(91)]
    E = lambda r: _round(morse(r), digits)
    e0 = E(R)
    fw, ce, se = [], [], []
    for h in hs:
        ep, em = E(R + h), E(R - h)
        fw.append((ep - e0) / h - d1)
        ce.append((ep - em) / (2 * h) - d1)
        se.append((ep + em - 2 * e0) / (h * h) - d2)
    dE = 0.5 * 10 ** (-digits) if digits is not None else 1e-16

    def best(errs):
        i = min(range(len(hs)), key=lambda j: abs(errs[j]))
        return {"h": hs[i], "err": errs[i]}

    return {"h": hs, "forward": fw, "central": ce, "second": se, "exact": {"d1": d1, "d2": d2, "d3": d3},
            "h_opt": (3 * (2 * dE) / abs(d3)) ** (1 / 3), "best": {"forward": best(fw), "central": best(ce),
            "second": best(se)}, "digits": digits}


def _lcg(seed, n):
    state = seed * 2654435761 % 2 ** 32 or 1
    out = []
    for _ in range(n):
        state = (1103515245 * state + 12345) % 2 ** 31
        out.append(state / 2 ** 31 * 2 - 1)
    return out


def _energy(F, w=WATER):
    return -76.0 - w["mu"] * F - 0.5 * w["alpha"] * F * F - w["beta"] * F ** 3 / 6 - w["gamma"] * F ** 4 / 24


def _dipole(F, w=WATER):
    return w["mu"] + w["alpha"] * F + 0.5 * w["beta"] * F * F + w["gamma"] * F ** 3 / 6


def field(lgF=-2.7, lgdE=-8.0):
    """The finite-field μ and α of a model water molecule (μ = 0.728, α = 9.8 a.u.) from energies with an error δE and
    from dipoles with δμ = δE, against the field; the values at F = 10^lgF."""
    if not (-5 <= lgF <= -1 and -12 <= lgdE <= -4):
        raise ValueError("lgF −5..−1, lgdE −12..−4")
    dE = 10 ** lgdE
    Fs = [10 ** (-5 + 4 * i / 80) for i in range(81)]
    noise = _lcg(7, 3 * len(Fs) + 3)

    def at(F, k):
        e0 = _energy(0.0) + dE * noise[3 * k]
        ep = _energy(F) + dE * noise[3 * k + 1]
        em = _energy(-F) + dE * noise[3 * k + 2]
        mp = _dipole(F) + dE * noise[3 * k + 1]
        mm = _dipole(-F) + dE * noise[3 * k + 2]
        return -(ep - em) / (2 * F), -(ep + em - 2 * e0) / (F * F), (mp - mm) / (2 * F)

    rows = [at(F, k) for k, F in enumerate(Fs)]
    F = 10 ** lgF
    mu, aE, aM = at(F, len(Fs))
    w = WATER
    return {"F": Fs, "mu_err": [abs(r[0] - w["mu"]) for r in rows], "alpha_E_err": [abs(r[1] - w["alpha"]) for r in rows],
            "alpha_mu_err": [abs(r[2] - w["alpha"]) for r in rows],
            "at": {"F": F, "mu": mu, "alpha_E": aE, "alpha_mu": aM, "kj": 0.5 * w["alpha"] * F * F * HARTREE_KJ,
                   "noise_E": 2 * dE / (F * F), "noise_mu": dE / F},
            "true": {"mu": w["mu"], "alpha": w["alpha"], "mu_D": w["mu"] * 2.5417}}


def twolevel(mu01=1.2, dE=0.3):
    """α = 2|μ01|²/ΔE of two levels, and the polarizability of water in the bases of the lecture."""
    if not (0.05 <= mu01 <= 3 and 0.05 <= dE <= 2):
        raise ValueError("mu01 0.05..3, dE 0.05..2 hartree")
    return {"alpha": 2 * mu01 * mu01 / dE, "basis": [{"name": n, "alpha": a} for n, a in BASIS], "exp": EXP_ALPHA}

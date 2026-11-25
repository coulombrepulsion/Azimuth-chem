"""Conceptual DFT: electronegativity, hardness, electrophilicity from I and A; Fukui functions by finite
differences in the Hückel model (Atlas).

HEADER
    Model of the panel "Глобальные индексы и функции Фукуи" of the page "Метод Хюккеля" (web/<lang>/huckel.html).
    Wilkinson convention, sections 1-8.

§1 THEORY
    The energy as a function of the number of electrons, E(N), is approximated by a parabola through
    E(N − 1), E(N), E(N + 1), i.e. through the ionisation energy I and the electron affinity A:
        μ = ∂E/∂N ≈ −(I + A)/2 = −χ (chemical potential; χ — Mulliken electronegativity),
        η = ∂²E/∂N² ≈ (I − A)/2 (chemical hardness, Parr–Pearson; softness S = 1/(2η)),
        ω = μ²/(2η) = χ²/(2η) (electrophilicity index, Parr 1999).
    The Fukui function f(r) = ∂ρ(r)/∂N tells where the density changes: f⁺ = ρ_{N+1} − ρ_N (attack of a
    nucleophile), f⁻ = ρ_N − ρ_{N−1} (attack of an electrophile), f⁰ = (f⁺ + f⁻)/2 (radical). Condensed to
    atoms with π-electron populations of the Hückel model, where the orbitals do not relax on adding or
    removing an electron, f⁺_r = c²_{r,LUMO} and f⁻_r = c²_{r,HOMO} exactly — the frontier-orbital densities.
    Atomic I and A (eV, NIST): H 13.598/0.754, Li 5.392/0.618, C 11.260/1.262, N 14.534/−0.07 (the anion
    is unbound), O 13.618/1.461, F 17.423/3.401, Na 5.139/0.548, Cl 12.968/3.613, Br 11.814/3.364, I 10.451/3.059.

§2 ALGORITHM
    Direct formulas; f± from core.huckel.solve at the charges 0, −1, +1 (q(N) − q(N ± 1)).

§3 APPLICATIONS
    Endpoints react.global, react.fukui.

§4 SPECIFICATION
    global_(I, A) -> {"chi", "mu", "eta", "S", "omega"} (eV, S in 1/eV); atoms() -> [[symbol, I, A]].
    fukui(types, bonds) -> {"fplus": [...], "fminus": [...], "f0": [...], "fH": [...], "fL": [...]}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    η > 0 is required (I > A).
§7 TEST CASES (tests/test_atlas_course1.py)
    χ(F) = 10.41 eV, η(F) = 7.01 eV; Σ f⁺ = Σ f⁻ = 1; in the Hückel model f⁺ = c²(LUMO), f⁻ = c²(HOMO)
    (non-degenerate frontier orbitals); allyl-free butadiene: f⁻ largest at the terminal carbons.
§8 ERROR ANALYSIS
    The finite-difference parabola and the Hückel model are the approximations; arithmetic ~1e-15.
"""
from __future__ import annotations

from . import huckel

ATOMS = [["H", 13.598, 0.754], ["Li", 5.392, 0.618], ["C", 11.260, 1.262], ["N", 14.534, -0.07], ["O", 13.618, 1.461],
         ["F", 17.423, 3.401], ["Na", 5.139, 0.548], ["Cl", 12.968, 3.613], ["Br", 11.814, 3.364], ["I", 10.451, 3.059]]


def global_(I: float, A: float) -> dict:
    if not (0 < I <= 100) or not (-20 <= A < I):
        raise ValueError("need 0 < I <= 100 eV and A < I")
    chi = (I + A) / 2
    eta = (I - A) / 2
    return {"chi": chi, "mu": -chi, "eta": eta, "S": 1 / (2 * eta), "omega": chi * chi / (2 * eta)}


def fukui(types: list, bonds: list) -> dict:
    R0 = huckel.solve(types, bonds, 0)
    Rm = huckel.solve(types, bonds, -1)  # one electron more
    Rp = huckel.solve(types, bonds, 1)   # one electron less
    fplus = [a - b for a, b in zip(R0["q"], Rm["q"])]
    fminus = [b - a for a, b in zip(R0["q"], Rp["q"])]
    return {"fplus": fplus, "fminus": fminus, "f0": [(a + b) / 2 for a, b in zip(fplus, fminus)],
            "fH": R0["fH"], "fL": R0["fL"]}

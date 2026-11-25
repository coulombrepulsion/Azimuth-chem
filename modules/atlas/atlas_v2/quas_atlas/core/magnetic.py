"""EPR and NICS for the NMR page: the Fermi contact of the hydrogen atom and the density at the nucleus in Gaussian
bases, and the field of a ring current — the sign of NICS inside and outside an aromatic or antiaromatic ring.

HEADER
    Model of the panels «ЭПР» and «NICS» of the page "ЯМР: от экранирования к химическому сдвигу" (web/<lang>/nmr.html),
    Atlas 2026-11-24; lecture 5 of the course «Квантово-химические методы» (derivations 6 and 9). Wilkinson
    convention, sections 1-8.

§1 THEORY
    Fermi contact: A_iso = (2μ0/3h) g_e μ_B g_N μ_N |ψ(0)|²; for the hydrogen 1s |ψ(0)|² = 1/(πa0³) and A_iso ≈ 1423 MHz
    (experiment 1420.4 MHz, the 21 cm line). A Gaussian has no cusp: the density at the nucleus relative to the exact
    one is 0.24 for one optimal Gaussian (α = 8/(9π)), 0.65 for STO-3G and 0.88 for STO-6G — small errors for the
    energy, large ones for hyperfine constants: hence the EPR-II/III, pcJ bases with tight uncontracted s functions.
    NICS = −σ at an empty point (Schleyer 1996). A field B perpendicular to a ring induces a ring current; its field
    (a current loop of radius R, Biot–Savart) opposes B inside the ring and along the axis and adds to it outside in
    the plane. For 4n + 2 π electrons the current is diatropic (NICS < 0 inside, ring protons deshielded), for 4n
    paratropic (NICS > 0). On the axis NICS(z) = NICS(0)·R³/(R² + z²)^{3/2}.

§2 ALGORITHM
    Closed formulas for the Gaussians; the in-plane field of the loop by the trapezoidal rule over the angle.

§3 APPLICATIONS
    Endpoints nmr.fermi, nmr.ring.

§4 SPECIFICATION
    fermi(basis) -> {"r", "exact", "approx", "ratio", "a_iso", "a_exact", "energy", "exp"}.
    ring(nics0, R) -> {"z", "axis", "rho", "plane", "nics0", "nics1", "proton": {"rho", "dshift"}}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (Pyodide). CODATA constants; the STO-3G and STO-6G contractions for ζ = 1 (Hehre, Stewart,
    Pople 1969).
§7 TEST CASES (tests/atlas/test_atlas_magnetic.py)
    A_iso(exact) ≈ 1423 MHz; the ratios 0.24, 0.65, 0.88; NICS(z) on the axis; the sign change at the ring.
§8 ERROR ANALYSIS
    The ring-current loop is the π part only (no σ contribution; NICS(1) is used in practice to reduce it); NICS(0)
    of the presets are the lecture's reference values (benzene ≈ −10, cyclobutadiene ≈ +27 ppm, Schleyer et al., JACS
    118, 6317 (1996)).
"""

import math

MU0, H, GE, MUB, GN, MUN, A0 = 4e-7 * math.pi, 6.62607015e-34, 2.00231930436, 9.2740100783e-24, 5.5856946893, \
    5.0507837461e-27, 5.29177210903e-11
BASES = {"g1": ([8 / (9 * math.pi)], [1.0]),
         "sto3g": ([2.22766, 0.405771, 0.109818], [0.154329, 0.535328, 0.444635]),
         "sto6g": ([23.10303149, 4.235915534, 1.185056519, 0.4070988982, 0.1580884151, 0.06510953954],
                   [0.009163596281, 0.04936149294, 0.1685383049, 0.3705627997, 0.4164915298, 0.1303340841])}
A_EXP_MHZ = 1420.405


def _norm(a):
    return (2 * a / math.pi) ** 0.75


def _gto(basis):
    a, c = BASES[basis]
    S = sum(ci * cj * _norm(ai) * _norm(aj) * (math.pi / (ai + aj)) ** 1.5 for ai, ci in zip(a, c) for aj, cj in zip(a, c))
    T = sum(ci * cj * _norm(ai) * _norm(aj) * 3 * ai * aj / (ai + aj) * (math.pi / (ai + aj)) ** 1.5
            for ai, ci in zip(a, c) for aj, cj in zip(a, c))
    V = sum(-ci * cj * _norm(ai) * _norm(aj) * 2 * math.pi / (ai + aj) for ai, ci in zip(a, c) for aj, cj in zip(a, c))
    k = 1 / math.sqrt(S)
    return (lambda r: k * sum(ci * _norm(ai) * math.exp(-ai * r * r) for ai, ci in zip(a, c))), (T + V) / S


def fermi(basis="sto3g"):
    """The hydrogen 1s exact and in a Gaussian basis: ψ(r), the density at the nucleus, A_iso (MHz), the energy."""
    if basis not in BASES:
        raise ValueError("basis g1|sto3g|sto6g")
    f, e = _gto(basis)
    rs = [3 * i / 150 for i in range(151)]
    exact = [math.exp(-r) / math.sqrt(math.pi) for r in rs]
    ratio = f(0.0) ** 2 * math.pi
    a_exact = 2 * MU0 / (3 * H) * GE * MUB * GN * MUN / (math.pi * A0 ** 3) / 1e6
    return {"r": rs, "exact": exact, "approx": [f(r) for r in rs], "ratio": ratio, "a_iso": a_exact * ratio,
            "a_exact": a_exact, "energy": e, "exp": A_EXP_MHZ, "basis": basis}


def _plane(rho, R, n=720):
    """B_z of a unit loop at an in-plane point at distance rho from the centre, divided by its value at the centre."""
    s = 0.0
    for k in range(n):
        p = 2 * math.pi * (k + 0.5) / n
        s += R * (R - rho * math.cos(p)) / (R * R + rho * rho - 2 * R * rho * math.cos(p)) ** 1.5
    return s * (2 * math.pi / n) / (2 * math.pi / R)


def ring(nics0=-10.0, R=1.39):
    """NICS of a π ring current scaled to NICS(0): along the axis and in the plane; the shift of a ring proton
    (1.09 Å outside the ring)."""
    if not (-40 <= nics0 <= 40 and 0.6 <= R <= 3):
        raise ValueError("nics0 −40..40 ppm, R 0.6..3 Å")
    zs = [4 * i / 80 for i in range(81)]
    axis = [nics0 * R ** 3 / (R * R + z * z) ** 1.5 for z in zs]
    rhos = [4 * i / 160 for i in range(161)]
    plane = [None if abs(r - R) < 0.12 else nics0 * _plane(r, R) for r in rhos]
    rh = R + 1.09
    return {"z": zs, "axis": axis, "rho": rhos, "plane": plane, "nics0": nics0, "nics1": nics0 * R ** 3 / (R * R + 1) ** 1.5,
            "proton": {"rho": rh, "dshift": nics0 * _plane(rh, R)}, "R": R}

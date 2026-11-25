"""H2 in a minimal basis: RHF, UHF, full CI, MP2 and the lowest triplet.

HEADER
    Numerical model of the Atlas page "Dissociation of H2: RHF, UHF, CI"
    (web/<lang>/h2.html). Port of ``h2point`` and the page's data tables
    from Atlas v1.0. Wilkinson convention, §1-§8.

§1 THEORY
    Two STO-3G 1s functions chi_A, chi_B (Slater exponent zeta = 1.24, the
    Szabo-Ostlund value for H2) on nuclei at z = 0 and z = R. With overlap
    s = S_AB the symmetry-adapted MOs are
        sigma_g = (chi_A + chi_B) / sqrt(2(1 + s)),
        sigma_u = (chi_A - chi_B) / sqrt(2(1 - s)),
    which already solve the RHF equations (symmetry fixes them). In the MO
    basis, with h_pq = <p|h|q> and (pq|rs) chemists' integrals:
        J_gg = (gg|gg), J_uu = (uu|uu), J_gu = (gg|uu), K = (gu|gu);
        E0 = 2 h_gg + J_gg |sigma_g alpha sigma_g beta|
        E1 = 2 h_uu + J_uu |sigma_u alpha sigma_u beta|
        <0|H|1> = K.
    Full CI in this basis (Szabo & Ostlund, ch. 4) is the 2x2 problem
        E_CI = (E0 + E1)/2 - sqrt(((E1 - E0)/2)^2 + K^2),
        (c0, c1) proportional to (K, E_CI - E0), normalised, c0 > 0.
    Orbital energies eps_g = h_gg + J_gg, eps_u = h_uu + 2 J_gu - K, and the
    MP2 energy E_MP2 = E0 + K^2 / (2 (eps_g - eps_u)) (one double
    excitation; Szabo & Ostlund, ch. 6, minimal-basis H2 example). The triplet 3Sigma_u+ (sigma_g
    sigma_u, parallel spins): E_T = h_gg + h_uu + J_gu - K. UHF from
    core.sto3g.uhf (spin-symmetry broken beyond the Coulson-Fischer point).
    All energies are total (electronic + V_nn = 1/R), hartree; R in bohr.

    Valence-bond view: with A = chi_A, B = chi_B and normalised MOs,
    Psi_CI proportional to [A(1)B(2)+B(1)A(2)] + lambda [A(1)A(2)+B(1)B(2)],
        lambda = (c0 n_g^2 + c1 n_u^2) / (c0 n_g^2 - c1 n_u^2),
    n_g, n_u the MO normalisation factors (lambda = 1 for RHF, i.e. c1 = 0).

§2 ALGORITHM
    h2_point(R, zeta): integrals -> X -> MO transform of h (C^T H C) and of
    the four needed ERIs by explicit quadruple sums -> formulas of §1 ->
    uhf(I, X) from the default broken-symmetry start.
    h2_scan(): h2_point on R = 0.5, 0.55, ..., 8.0 (151 points) plus the
    dissociation limit 2 E(H) taken as the UHF energy at R = 40 bohr, and
    R_e = argmin over the grid of E_RHF.
    orbital_curves(R): values on the axis z in [-2, R + 2] (260 points) of
    sigma_g, sigma_u and the UHF alpha, beta orbitals (coefficients from
    the UHF densities: c = (sqrt(P_11), P_12/sqrt(P_11))).
    error_budget(R, basis, method, iters): decomposition of E - E_exact into
    SCF, method and basis errors from tabulated reference energies (§4).

§3 APPLICATIONS
    The page plots E(R) of all methods, prints the numbers at the chosen R,
    shows c0, natural-orbital occupations 2c0^2 / 2c1^2, <S^2>, the HOMO-LUMO
    gap, the orbitals, the covalent/ionic ratio lambda, and the three kinds
    of error (SCF convergence, method, basis).

§4 SPECIFICATION
    h2_point(R: float in (0, 100], zeta: float > 0 = 1.24) -> dict with
        R, s, Vnn, rhf, ci, mp2, trip, uhf, s2, c0, c1, eg, eu, K, ca, cb,
        ng, nu (floats or 2-lists), and lam (covalent/ionic ratio, §1).
    h2_scan() -> {"R": [...151], "rhf", "uhf", "ci", "mp2", "trip", "s2",
        "c0", "c1": lists of 151 floats, "lim": float, "re": float}.
    orbital_curves(R) -> {"z": 260 floats, "g", "u", "a", "b": 260 floats}.
    error_budget(R in {1.4, 10}, basis in {"STO-3G","6-31G","6-31G**"},
        method in {"rhf","mp2","fci"}, iters in {0,1,2,3}) -> {E, total,
        scf, method, basis, nbf}. Reference energies: RHF iteration
        histories, RHF, MP2 and FCI energies per basis were computed for
        Atlas v1.0 by its author with an external program (the values
        agree with PySCF 2.x to 1e-7 Eh, see tests/test_h2.py); exact energies: Kolos & Wolniewicz,
        E(1.4 bohr) = -1.174475 Eh; E(10 bohr) = -1 Eh (two H atoms).
    Reference implementation: Atlas v1.0 ``h2point`` (h2.html), V8.
    Equivalence tier: ``bound`` with B_direct = 1e-12 Eh for rhf, ci, mp2,
    trip and the coefficients; B_iter = 1e-9 Eh for uhf, 1e-8 for s2, ca,
    cb (core.sto3g §8 (d), (e)).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * The scan (151 points, each with a UHF) takes ~1 s in CPython; it is
      memoised (functools.lru_cache) because the page requests it once per
      load.
    * js_hypot reproduces V8's Math.hypot so that c0, c1 normalisation is
      bitwise comparable.
    * eps_g - eps_u -> 0 as R -> infinity, so E_MP2 diverges: this is the
      physics the page demonstrates, not a numerical failure. For R up to
      8 bohr the denominator stays > 0.05 Eh.
§7 TEST CASES (tests/test_h2.py)
    * R = 1.4, zeta = 1.24: E_RHF = -1.1167 Eh, E_CI = -1.1373 Eh,
      E_corr = -0.0206 Eh (Szabo & Ostlund, ch. 4, minimal-basis H2;
      independent printed oracle, 4 decimals).
    * PySCF 2.14 (optional) RHF and FCI with the same 6-digit basis:
      E_RHF(1.4) = -1.1167142748, E_FCI(1.4) = -1.1372759045 Eh.
      Known v1.0 deviation, kept for equivalence: the closed formulas of §1
      assume <chi|chi> = 1, but the 6-digit contraction gives 1.0000014,
      so rhf, ci, mp2, trip are low by ~1e-6 Eh (rhf -9.9e-7, ci -1.16e-6
      at 1.4 bohr); uhf (computed through S^-1/2) is exact. Invisible at
      the 4 decimals the page prints; listed for the author in CHANGELOG.
    * Invariants: E_CI <= E_RHF; E_CI <= E_UHF <= E_RHF; c0^2 + c1^2 = 1;
      0 <= <S^2> <= 1; E_UHF -> 2 E(H, STO-3G) = -0.9332 Eh as R -> 40.
    * error_budget totals reproduce E - E_exact exactly (sum of parts).
    * Differential test against the original JS on 12 R values (fixtures).
§8 ERROR ANALYSIS
    See core.sto3g §8: direct quantities agree with the reference to
    <= 1e-12 Eh (condition number of the 2x2 CI is
    |E1 - E0| / (2 disc) <= 1, so no amplification); UHF quantities to the
    iteration bound. Physical accuracy (model error) is not numerical
    error: the minimal basis overestimates E_RHF(1.4) by 0.010 Eh relative
    to the RHF limit -- shown on the page as "basis error".
"""
from __future__ import annotations

import functools
import math

from .jsmath import js_hypot, sq
from .smallmat import mmul
from .sto3g import chi_on_axis, integrals, uhf, x_matrix

ZETA = 1.24
SCAN_R = [0.5 + i * 0.05 for i in range(151)]

# Reference energies for the error budget (hartree); see §4 for provenance.
ERR = {
    "1.4|STO-3G": {"it": [-1.1167142, -1.1167142], "rhf": -1.1167142, "mp2": -1.1298721, "fci": -1.1372759, "nbf": 2},
    "1.4|6-31G": {"it": [-1.0741494, -1.1254477, -1.1267136, -1.1267421, -1.1267427, -1.1267427, -1.1267427, -1.1267427],
                  "rhf": -1.1267427, "mp2": -1.1441332, "fci": -1.151679, "nbf": 4},
    "1.4|6-31G**": {"it": [-1.0691853, -1.1300438, -1.1312592, -1.1312838, -1.1312843, -1.1312843, -1.1312843, -1.1312843],
                    "rhf": -1.1312843, "mp2": -1.1576261, "fci": -1.1651534, "nbf": 10},
    "10|STO-3G": {"it": [-0.5959702, -0.5959702], "rhf": -0.5959702, "mp2": -1.164213, "fci": -0.9331635, "nbf": 2},
    "10|6-31G": {"it": [-0.7324808, -0.747911, -0.7480703, -0.748072, -0.748072, -0.748072, -0.748072, -0.748072],
                 "rhf": -0.748072, "mp2": -1.0378641, "fci": -0.996466, "nbf": 4},
    "10|6-31G**": {"it": [-0.7324773, -0.7479165, -0.7480759, -0.7480777, -0.7480777, -0.7480777, -0.7480777, -0.7480777],
                   "rhf": -0.7480777, "mp2": -1.042176, "fci": -0.9964661, "nbf": 10},
}
EXACT = {"1.4": -1.174475, "10": -1.0}


def _point(R: float, zeta: float) -> dict:
    """h2point of v1.0, returning also the integrals (key 'I')."""
    I = integrals([{"Z": 1, "zeta": zeta, "z": 0.0}, {"Z": 1, "zeta": zeta, "z": R}])
    X = x_matrix(I["S"])
    s = I["S"][0][1]
    # symmetry-adapted MO coefficients (columns: sigma_g, sigma_u)
    ng = 1 / math.sqrt(2 * (1 + s))
    nu = 1 / math.sqrt(2 * (1 - s))
    C = [[ng, nu], [ng, -nu]]
    # one-electron integrals in the MO basis: h = C^T H C
    h = mmul(mmul([[C[0][0], C[1][0]], [C[0][1], C[1][1]]], I["H"]), C)
    E = I["ERI"]

    def mo(p, q, r, t):  # (pq|rt) in the MO basis by a full AO quadruple sum
        v = 0.0
        for a in range(2):
            for b in range(2):
                for c in range(2):
                    for d in range(2):
                        v = v + C[a][p] * C[b][q] * C[c][r] * C[d][t] * E[a][b][c][d]
        return v
    Jgg, Juu, Jgu, Kgu = mo(0, 0, 0, 0), mo(1, 1, 1, 1), mo(0, 0, 1, 1), mo(0, 1, 0, 1)
    # 2x2 full CI between |g g-bar| and |u u-bar|
    E0 = 2 * h[0][0] + Jgg
    E1 = 2 * h[1][1] + Juu
    disc = math.sqrt(sq((E1 - E0) / 2) + Kgu * Kgu)
    Eci = (E0 + E1) / 2 - disc
    c0, c1 = Kgu, Eci - E0
    n = js_hypot(c0, c1)
    c0 /= n
    c1 /= n
    if c0 < 0:
        c0, c1 = -c0, -c1
    # orbital energies and MP2 (single double excitation g g -> u u)
    eg = h[0][0] + Jgg
    eu = h[1][1] + 2 * Jgu - Kgu
    Emp2 = E0 + Kgu * Kgu / (2 * (eg - eu))
    Et = h[0][0] + h[1][1] + Jgu - Kgu
    u = uhf(I, X)

    def vec(P):  # orbital coefficients from a rank-1 density P = c c^T
        a = math.sqrt(max(P[0][0], 1e-30))
        return [a, P[0][1] / a]
    g2, u2 = ng * ng, nu * nu
    cov, ion = c0 * g2 - c1 * u2, c0 * g2 + c1 * u2
    return {"R": R, "s": s, "Vnn": I["Vnn"], "rhf": E0 + I["Vnn"], "ci": Eci + I["Vnn"],
            "mp2": Emp2 + I["Vnn"], "trip": Et + I["Vnn"], "uhf": u["E"], "s2": u["S2"],
            "c0": c0, "c1": c1, "eg": eg, "eu": eu, "K": Kgu, "ca": vec(u["Pa"]), "cb": vec(u["Pb"]),
            "ng": ng, "nu": nu, "lam": ion / cov, "I": I}


def _check_R(R: float) -> float:
    R = float(R)
    if not (0 < R <= 100) or math.isnan(R):
        raise ValueError(f"R must be in (0, 100] bohr, got {R}")
    return R


@functools.lru_cache(maxsize=512)
def h2_point(R: float, zeta: float = ZETA) -> dict:
    """All energies and wavefunction descriptors of H2 at bond length R (bohr)."""
    R = _check_R(R)
    if not zeta > 0:
        raise ValueError("zeta must be positive")
    p = _point(R, zeta)
    p.pop("I")
    return p


@functools.lru_cache(maxsize=1)
def h2_scan() -> dict:
    """Potential curves on the page grid, the dissociation limit and R_e."""
    pts = [h2_point(R) for R in SCAN_R]
    keys = ("rhf", "uhf", "ci", "mp2", "trip", "s2", "c0", "c1")
    out = {"R": list(SCAN_R)}
    out.update({k: [p[k] for p in pts] for k in keys})
    out["lim"] = h2_point(40.0)["uhf"]
    best = pts[0]
    for p in pts:  # first minimum, as Array.reduce in v1.0
        if p["rhf"] < best["rhf"]:
            best = p
    out["re"] = best["R"]
    return out


@functools.lru_cache(maxsize=256)
def orbital_curves(R: float, zeta: float = ZETA, npts: int = 260) -> dict:
    """sigma_g, sigma_u and UHF alpha/beta orbitals on the molecular axis."""
    R = _check_R(R)
    p = _point(R, zeta)
    I = p["I"]
    z0, z1 = -2.0, R + 2
    zs = [z0 + (z1 - z0) * i / (npts - 1) for i in range(npts)]
    ch = [(chi_on_axis(I, 0, z), chi_on_axis(I, 1, z)) for z in zs]

    def f(c):
        return [c[0] * x[0] + c[1] * x[1] for x in ch]
    return {"z": zs, "g": f([p["ng"], p["ng"]]), "u": f([p["nu"], -p["nu"]]),
            "a": f(p["ca"]), "b": f(p["cb"])}


def error_budget(R: float, basis: str, method: str, iters: int) -> dict:
    """E - E_exact split into SCF-convergence, method and basis errors."""
    key = f"{R:g}|{basis}"
    if key not in ERR:
        raise ValueError(f"no reference data for R={R}, basis={basis}")
    if method not in ("rhf", "mp2", "fci"):
        raise ValueError(f"unknown method {method}")
    if iters not in (0, 1, 2, 3):
        raise ValueError("iters must be 0 (converged) or 1..3")
    d, ex = ERR[key], EXACT[f"{R:g}"]
    rhf_only = method == "rhf"
    it = d["it"][min(iters, len(d["it"])) - 1] if rhf_only and iters > 0 else d["rhf"]
    meth = d[method]
    E = it if rhf_only else meth
    e_scf = it - d["rhf"] if rhf_only else 0.0
    e_meth = meth - d["fci"]
    e_basis = d["fci"] - ex
    return {"E": E, "total": E - ex, "scf": e_scf, "method": e_meth, "basis": e_basis, "nbf": d["nbf"]}

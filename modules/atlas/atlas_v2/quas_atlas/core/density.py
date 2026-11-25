"""Electron density of H2 and HeH+ (STO-3G RHF): rho, deformation density,
Laplacian, electrostatic potential and the bond critical point.

HEADER
    Numerical model of the Atlas page "Electron density"
    (web/<lang>/density.html).  Port of molSetup, gTerms, ev, lap, hess, esp,
    bcp and the map/profile sampling of v1.0.  Wilkinson convention, §1-§8.

§1 THEORY
    With the converged RHF density matrix P (core.sto3g) and contracted 1s
    Gaussians chi_mu = sum_a d_a exp(-a |r - A_mu|^2), the density is
        rho(r) = sum_{mu,nu} P_{mu nu} chi_mu(r) chi_nu(r).
    The product of two s Gaussians is one s Gaussian (Gaussian product
    theorem): exp(-a|r-A|^2) exp(-b|r-B|^2) = K_ab exp(-p |r - C|^2) with
    p = a + b, C = (aA + bB)/p, K_ab = exp(-ab/p |A - B|^2).  Hence rho is a
    finite sum of terms K exp(-p (x^2 + (z - c)^2)) (x = distance from the
    axis), merged when (p, c) coincide.  On this sum, in closed form:
        Laplacian  nabla^2 [K e^{-p s}] = K e^{-p s} (4 p^2 s - 6 p),
                   s = x^2 + (z - c)^2;
        Hessian on the axis: lambda_perp = sum -2 p K e^{-p d^2} (twice),
                   lambda_par = sum K e^{-p d^2} (4 p^2 d^2 - 2 p), d = z - c;
        potential of one Gaussian charge q = K (pi/p)^{3/2}:
                   phi = q erf(sqrt(p) r)/r  (-> 2 q sqrt(p/pi) at r = 0),
    and phi(r) = sum_A Z_A/|r - R_A| - sum_terms phi_term.  The erf is the
    Abramowitz-Stegun 7.1.26 rational approximation (|error| < 1.5e-7),
    adequate for a colour map.
    Deformation density: Delta rho = rho_molecule - rho_promolecule, the
    promolecule being free atoms (H: zeta = 1, one electron each; HeH+:
    He with zeta = 1.6875 holding two electrons, a bare proton).
    Bond critical point (Bader): on the axis between the nuclei rho has a
    minimum (lambda_par > 0) while it is maximal across (lambda_perp < 0);
    nabla^2 rho = 2 lambda_perp + lambda_par classifies the interaction.

§2 ALGORITHM
    setup(mol, R): integrals and RHF (P0 = 0, tol 1e-11, <= 500 cycles);
    terms(B, M) for every pair (mu, nu) with |M_mu nu| >= 1e-14 and every
    primitive pair: (K = M_mu nu d_a d_b K_ab, p, c); merge entries whose
    (p, c) agree to 10 decimals (insertion order kept, K summed); drop
    |K| < 1e-14.  Molecular terms tM, atomic tA; tD = tM followed by tA
    with negated K.
    bcp: scan rho(0, z) at z = R i / 600, i = 1..599; if the minimum is
    interior (2 < i < 598) refine by 80 ternary-section steps on
    [z_{i-1}, z_{i+1}]; accept if lambda_par > 0.
    grid(view): 240 x 147 cells over a 8.6-bohr window centred on the bond;
    cell centres (x, z); value f(|x|, z); rows below the axis copied from
    their mirror rows (rotational symmetry).
    profile(view): f(0, z) at 701 equidistant z over the window.

§3 APPLICATIONS
    Colour/contour maps of rho, Delta rho, nabla^2 rho, phi; profiles along
    the bond; values under the cursor; the bond critical point and its
    disappearance in compressed H2 or in HeH+ at short R (a known artefact
    of Gaussian basis sets without nuclear cusps).

§4 SPECIFICATION
    mol in {"H2", "HeH"}; R in [0.3, 20] bohr; view in {"rho", "drho",
    "lap", "esp"}; (x, z) in bohr, |x|, |z| <= 50.
    view_data(mol, R, view) -> {E, P, bcp: {z, rho, lap, l1, l3, drho} or
        None, grid: {nx: 240, ny: 147, g: [nx*ny]} (row-major, row j is
        x = HB/2 - (j + 1/2) CH/ny / SC), prof: [701], atB: f(0, z_bcp) or
        None}.
    point(mol, R, x, z) -> {rho, drho, lap, esp} at (|x|, z).
    Units: e/bohr^3, e/bohr^5, hartree/e (atomic units).
    Reference: v1.0 density.html.  Equivalence tier ``bound``: B = 1e-12
    relative for rho, Delta rho, nabla^2 rho, phi values (sums of exp
    terms, core.sto3g §8 (b)), B = 1e-7 for z_bcp (ternary section, §8),
    and the RHF density inherits B = 1e-12 (tol 1e-11 in rmsd).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * The term list has ~20 entries; the map needs ~17 600 distinct cells
      (half grid) x ~20 exponentials: ~0.3 s in CPython (ESP ~0.6 s), so
      results are memoised per (mol, R, view).
    * The merge key formats with 10 decimals; Python's '%.10f' and
      JavaScript's toFixed(10) can differ only for exact decimal ties,
      which cannot occur for these values (they are not short binary
      fractions); identical floats always give identical keys.
§7 TEST CASES (tests/test_density.py)
    * Normalisation: the integral of rho over space equals the number of
      electrons, sum_terms K (pi/p)^{3/2} = 2 (analytic Gaussian integral;
      independent of the grid); the integral of Delta rho is 0.
    * Laplacian: the term formula vs a central finite difference of rho.
    * ESP far away: phi -> total charge / r (0 for H2, 1/r for HeH+).
    * H2 BCP at the bond midpoint by symmetry.
    * Differential test against the v1.0 JavaScript.
§8 ERROR ANALYSIS
    Each field value is a sum of <= ~40 terms K e^{-p s} (or the ESP
    terms): relative error <= gamma_40 + 2u per term in either
    implementation, differences dominated by exp (<= 1 ulp): the absolute
    difference is <= 50 u sum |terms| -- below 1e-12 for every point of the
    window (sum |terms| <= 8 at the nuclei).  The A&S erf (1.5e-7) is a
    *model* error shared by both implementations, not a difference.
    BCP position: ternary section brackets shrink by (2/3)^80 (< 1e-14);
    comparison flips are possible only where |rho(m1) - rho(m2)| is below
    the evaluation noise (1e-16), i.e. within sqrt(1e-16/lambda_par) ~ 1e-8
    bohr of the minimum (lambda_par ~ 1): B = 1e-7.
"""
from __future__ import annotations

import functools
import math

from .jsmath import exp, js_hypot, js_pow, sq
from .sto3g import basis, integrals, rhf_run, x_matrix

MOLD = {
    "H2": {"Z": (1, 1), "zeta": (1.24, 1.24), "zf": (1.0, 1.0), "R": 1.4, "pro": (1, 1)},
    "HeH": {"Z": (2, 1), "zeta": (2.0925, 1.24), "zf": (1.6875, 1.0), "R": 1.4632, "pro": (2, 0)},
}
CW, CH, WB = 720, 440, 8.6
SC = CW / WB
HB = CH / SC
NX = 240
NY = round(NX * CH / CW)
NPROF = 700


def _erfD(x: float) -> float:
    """Abramowitz-Stegun 7.1.26 (|error| < 1.5e-7)."""
    t = 1 / (1 + 0.3275911 * x)
    return 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t * exp(-x * x)


def g_terms(B, M) -> list[dict]:
    """Gaussian terms {K, p, c} of sum_{mu nu} M_{mu nu} chi_mu chi_nu, merged."""
    T = []
    n = len(B)
    for m in range(n):
        for nn in range(n):
            if abs(M[m][nn]) < 1e-14:
                continue
            for a in B[m]:
                for b in B[nn]:
                    p = a["a"] + b["a"]
                    c = (a["a"] * a["c"] + b["a"] * b["c"]) / p
                    K = M[m][nn] * a["d"] * b["d"] * exp(-a["a"] * b["a"] / p * sq(a["c"] - b["c"]))
                    T.append({"K": K, "p": p, "c": c})
    merged: dict[str, dict] = {}
    for t in T:
        k = f"{t['p']:.10f}|{t['c']:.10f}"
        o = merged.get(k)
        if o:
            o["K"] = o["K"] + t["K"]
        else:
            merged[k] = dict(t)
    return [t for t in merged.values() if abs(t["K"]) > 1e-14]


@functools.lru_cache(maxsize=64)
def setup(mol: str, R: float) -> dict:
    if mol not in MOLD:
        raise ValueError(f"unknown molecule {mol}")
    if not 0.3 <= R <= 20:
        raise ValueError("R must be in [0.3, 20] bohr")
    md = MOLD[mol]
    at = [{"Z": md["Z"][i], "zeta": md["zeta"][i], "z": R if i else 0.0} for i in range(2)]
    I = integrals(at)
    X = x_matrix(I["S"])
    r = rhf_run(I, X, [[0.0, 0.0], [0.0, 0.0]], tol=1e-11, maxit=500)
    P = r["P"]
    pro = [[float(md["pro"][0]), 0.0], [0.0, float(md["pro"][1])]]
    Bf = [basis(md["zf"][i], R if i else 0.0) for i in range(2)]
    tM, tA = g_terms(I["B"], P), g_terms(Bf, pro)
    tD = [dict(t) for t in tM] + [dict(t, K=-t["K"]) for t in tA]
    return {"mol": mol, "R": R, "at": at, "E": r["E"], "P": P, "S": I["S"], "tM": tM, "tA": tA, "tD": tD}


def ev(T, x, z):
    """Sum of Gaussian terms at distance x from the axis, height z."""
    v = 0.0
    for t in T:
        dz = z - t["c"]
        v = v + t["K"] * exp(-t["p"] * (x * x + dz * dz))
    return v


def lap(T, x, z):
    """Laplacian of the Gaussian sum."""
    v = 0.0
    for t in T:
        dz = z - t["c"]
        s = x * x + dz * dz
        v = v + t["K"] * exp(-t["p"] * s) * (4 * t["p"] * t["p"] * s - 6 * t["p"])
    return v


def hess(T, z):
    """Curvatures of the Gaussian sum on the axis: across (each of 2) and along."""
    perp = par = 0.0
    for t in T:
        d = z - t["c"]
        g = t["K"] * exp(-t["p"] * d * d)
        perp = perp + -2 * t["p"] * g
        par = par + g * (4 * t["p"] * t["p"] * d * d - 2 * t["p"])
    return perp, par


def esp(M, x, z):
    """Electrostatic potential of nuclei and electron cloud."""
    v = 0.0
    for a in M["at"]:
        d = js_hypot(x, z - a["z"])
        v = v + a["Z"] / max(d, 1e-6)
    for t in M["tM"]:
        d = js_hypot(x, z - t["c"])
        q = t["K"] * js_pow(math.pi / t["p"], 1.5)
        v = v - (q * 2 * math.sqrt(t["p"] / math.pi) if d < 1e-6 else q * _erfD(math.sqrt(t["p"]) * d) / d)
    return v


def bcp(M):
    """Bond critical point on the axis, or None (see §2)."""
    R, n = M["R"], 600
    best, bv = -1, math.inf
    for i in range(1, n):
        z = R * i / n
        v = ev(M["tM"], 0.0, z)
        if v < bv:
            bv, best = v, i
    if best <= 2 or best >= n - 2:
        return None
    a, b = R * (best - 1) / n, R * (best + 1) / n
    for _ in range(80):
        m1 = a + (b - a) / 3
        m2 = b - (b - a) / 3
        if ev(M["tM"], 0.0, m1) < ev(M["tM"], 0.0, m2):
            b = m2
        else:
            a = m1
    z = (a + b) / 2
    perp, par = hess(M["tM"], z)
    if par <= 0:
        return None
    return {"z": z, "rho": ev(M["tM"], 0.0, z), "lap": 2 * perp + par, "l1": perp, "l3": par,
            "drho": ev(M["tD"], 0.0, z)}


def _field(M, view):
    if view == "rho":
        return lambda x, z: ev(M["tM"], x, z)
    if view == "drho":
        return lambda x, z: ev(M["tD"], x, z)
    if view == "lap":
        return lambda x, z: lap(M["tM"], x, z)
    if view == "esp":
        return lambda x, z: esp(M, x, z)
    raise ValueError(f"unknown view {view}")


@functools.lru_cache(maxsize=64)
def view_data(mol: str, R: float, view: str) -> dict:
    """Map, profile, bond critical point for one molecule, R and field."""
    M = setup(mol, R)
    f = _field(M, view)
    B = bcp(M)

    def toZ(px):
        return M["R"] / 2 - WB / 2 + px / SC

    def toX(py):
        return HB / 2 - py / SC
    g = [0.0] * (NX * NY)
    for j in range(NY):
        x = toX((j + 0.5) * CH / NY)
        xa = abs(x)
        jm = NY - 1 - j
        if jm < j:  # mirror row
            g[j * NX:(j + 1) * NX] = g[jm * NX:(jm + 1) * NX]
            continue
        for i in range(NX):
            g[j * NX + i] = f(xa, toZ((i + 0.5) * CW / NX))
    z0, z1 = M["R"] / 2 - WB / 2, M["R"] / 2 + WB / 2
    prof = [f(0.0, z0 + (z1 - z0) * i / NPROF) for i in range(NPROF + 1)]
    return {"E": M["E"], "P": M["P"], "bcp": B, "grid": {"nx": NX, "ny": NY, "g": g}, "prof": prof,
            "atB": f(0.0, B["z"]) if B else None}


def point(mol: str, R: float, x: float, z: float) -> dict:
    """All four fields at one point (|x| used: axial symmetry)."""
    M = setup(mol, R)
    xa = abs(x)
    return {"rho": ev(M["tM"], xa, z), "drho": ev(M["tD"], xa, z), "lap": lap(M["tM"], xa, z),
            "esp": esp(M, xa, z)}

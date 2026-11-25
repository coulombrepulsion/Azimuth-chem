"""Minimal-basis (STO-3G 1s) Hartree-Fock machinery for a diatomic molecule.

HEADER
    Port of the computational core shared by the Atlas v1.0 pages
    "Dissociation of H2" (h2.html), "SCF" (scf.html) and "Electron density"
    (density.html).  Follows Szabo & Ostlund, *Modern Quantum Chemistry*,
    ch. 3 and appendix A.  Documentation: Wilkinson convention, §1-§8.

§1 THEORY
    Basis.  Each atom A carries one contracted Gaussian
        chi_A(r) = sum_{i=1..3} d_i g(alpha_i zeta^2, r - R_A),
        g(a, r) = (2a/pi)^{3/4} exp(-a r^2)        (normalised 1s Gaussian),
    with the STO-3G exponents alpha = (0.109818, 0.405771, 2.22766) and
    coefficients d = (0.444635, 0.535328, 0.154329) for zeta = 1 (Hehre,
    Stewart & Pople 1969, rounded to 6 digits as printed in Szabo & Ostlund,
    ch. 3).  Because of the rounding, <chi_A|chi_A> = 1.0000014, not 1.
    Both nuclei lie on the z axis, so every centre is a scalar coordinate.

    One-electron integrals over primitives p, q (exponents a, b, centres A, B,
    g = a + b, P = (aA + bB)/g, |AB|^2 = (A - B)^2):
        S_pq = (pi/g)^{3/2} exp(-ab/g |AB|^2)
        T_pq = (ab/g)(3 - 2 ab/g |AB|^2)(pi/g)^{3/2} exp(-ab/g |AB|^2)
        V_pq^C = -(2 pi/g) Z_C exp(-ab/g |AB|^2) F0(g |PC|^2)
    two-electron integral (chemists' notation):
        (pq|rs) = 2 pi^{5/2} / (g1 g2 sqrt(g1 + g2))
                  exp(-ab/g1 |AB|^2 - cd/g2 |CD|^2) F0(g1 g2/(g1+g2) |PQ|^2)
    with the Boys function F0(t) = (1/2) sqrt(pi/t) erf(sqrt t), F0(0) = 1.
    Contracted integrals are sums over primitives weighted by the products
    of normalised contraction coefficients.

    Closed-shell RHF (Roothaan): F C = S C eps,
        F_ij = H_ij + G_ij,  G_ij = sum_kl P_kl [(ij|kl) - 1/2 (il|kj)],
        P_kl = 2 sum_{a occ} C_ka C_la,  E_el = 1/2 sum_ij P_ij (H_ij + F_ij).
    Loewdin orthogonalisation X = S^{-1/2} turns it into F' C' = C' eps,
    F' = X^T F X, C = X C'.

    UHF with one alpha and one beta electron (H2, HeH+):
        F^a = H + J[P^a + P^b] - K[P^a],   F^b likewise,
        E = 1/2 sum_ij [P^t_ij H_ij + P^a_ij F^a_ij + P^b_ij F^b_ij] + V_nn,
        <S^2> = 1 - |<phi_a|phi_b>|^2  for the M_S = 0 two-electron UHF
        determinant (singlet would have 0, a 50/50 singlet-triplet mix 1).

    DIIS (Pulay 1980): extrapolate F = sum_k c_k F_k with sum c_k = 1
    minimising ||sum c_k e_k||, error vector e = F P S - S P F.

    Numerical trap: erf by its Maclaurin series loses accuracy for large x
    (terms of size x^{2n+1}/n! cancel); here the series is used only for
    x < 3 (largest term ~170, sum of magnitudes ~1445: at most ~3.2 of 16
    digits lost, see §8 (a)) and a continued fraction for erfc for x >= 3.

§2 ALGORITHM
    erf(x):  x < 0 -> -erf(-x);
             x < 3 -> (2/sqrt(pi)) sum_n (-1)^n x^{2n+1} / (n! (2n+1)),
                      stop when |term| <= 1e-17 |sum| and n >= 3;
             x >= 3 -> 1 - exp(-x^2) / sqrt(pi) / (x + f),
                       f from the continued fraction f = k/2 / (x + f),
                       k = 60, 59, ..., 1 (backward recurrence, f_61 = 0).
    integrals(atoms): S, T, V, H = T + V, all (ij|kl), V_nn = Z1 Z2 / R.
    x_matrix(S) = V diag(w^{-1/2}) V^T from eig_sym(S).
    solve_fc(F, X): F' = X^T F X; (eps, C') = eig_sym(F'); C = X C';
                    each column's largest-|.| element made positive.
    uhf: start P^a = e1 e1^T, P^b = e2 e2^T (electrons on different atoms,
         which breaks the spin symmetry when that lowers the energy); iterate
         new P from the lowest orbital of F^a, F^b; damp
         P := mix P_new + (1 - mix) P_old; stop when
         max(rmsd(P^a_new, P^a), rmsd(P^b_new, P^b)) < 1e-10 and it > 3,
         or after maxit iterations.  Energy re-evaluated at the final P.
    rhf_run: plain, damped or DIIS(2) SCF from a given P0; stop when
         rmsd(P_new, P) < tol (default 1e-6) or after maxit (default 200).

§3 APPLICATIONS
    * core.h2.h2_point: RHF, UHF, 2x2 CI, MP2 and triplet energies of H2.
    * The SCF page: iteration histories of plain/damped/DIIS SCF for H2 and
      HeH+ (rhf_run, uhf).
    * The density page: densities on the molecular axis (chi_on_axis).

§4 SPECIFICATION
    STO3G_A, STO3G_D : tuple[float, float, float], exponents and
        coefficients for zeta = 1 (dimensionless; bohr^-2 after scaling).
    Primitive : dict with keys a (exponent, bohr^-2), d (coefficient times
        normalisation), c (centre z, bohr).
    basis(zeta, center) -> list[Primitive] (3 items).
    integrals(atoms) -> Integrals dict: B (basis), S, T, V, H (n x n lists,
        hartree), ERI (n^4 nested lists, hartree), Vnn (hartree), n (int).
        atoms: list of dicts {Z: nuclear charge (> 0), zeta: Slater exponent
        (> 0), z: position on the axis in bohr}; exactly two atoms at
        different positions (Vnn divides by |z1 - z2|).
    x_matrix(S) -> S^{-1/2};  S must be positive definite.
    build_g(I, P), build_f(I, P) -> {G, F};  P: n x n density matrix.
    solve_fc(I, F, X) -> {eps, C, Fp}.
    density_from(C, nocc) -> P = 2 C_occ C_occ^T.
    energy(I, P) -> electronic energy (hartree, without V_nn).
    rmsd(A, B) -> root-mean-square element difference.
    chi_on_axis(I, mu, z) -> value of basis function mu at (0, 0, z).
    build_jk(I, P) -> {J, K}.
    uhf(I, X, init=None, maxit=500, mix=0.5) -> {E (total, hartree),
        S2 (<S^2>), Pa, Pb (2x2), it (iterations done)}.  2 basis functions.
    diis_error(F, P, S), diis_extrap(list) -> {F, c}.
    rhf_run(I, X, P0, maxit=200, tol=1e-6, damp=0, diis=False) -> {E, P,
        hist: list of {k, E, dP, eps}}.  2 basis functions, 1 occupied MO.

    Reference implementation: Atlas v1.0 JavaScript (reference/original_v1.0
    /h2.html, functions of the same names), run in Chromium/V8.
    Equivalence tier: ``bound`` -- order of operations preserved literally,
    but exp, pow and erf's exp come from different libm implementations
    (V8 fdlibm port vs. the C library under CPython); both are accurate to
    < 1 ulp but not always identically rounded.  Bounds derived in §8.
    Deterministic: yes.  Inputs are never modified in place.

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    * Nested lists, not numpy: n = 2 here, and plain floats keep the
      operation order identical to the JavaScript reference.
    * ERI are cached by index tuple exactly like the original (all n^4 are
      computed; no 8-fold symmetry is exploited -- with n = 2 that costs
      16 x 81 primitive integrals, about 2 ms in CPython).
    * F0 is memoised on the exact float argument.  The argument
      g1 g2/(g1+g2) |PQ|^2 is bitwise invariant under the 8 index
      permutations of (pq|rs) (multiplication and addition are commutative
      in IEEE 754 and |PQ|^2 = (P-Q)^2 = (Q-P)^2 exactly), so the cache
      returns exactly the value a recomputation would; it removes ~80% of
      the erf series evaluations (profile: 5.9 s -> see CHANGELOG).
    * F0(t) for t < 1e-8 uses 1 - t/3 (two Taylor terms; next term t^2/10
      < 1e-17, below u).
    * uhf/rhf_run hard-code 2x2 matrices as the original does; calling them
      with n != 2 raises ValueError instead of failing obscurely.

§7 TEST CASES (tests/test_sto3g.py, tests/test_h2.py)
    * erf against math.erf (independent implementation) on [0, 6]:
      |diff| <= 2e-16 (§8).
    * H2 at R = 1.4 bohr, zeta = 1.24: S_12 = 0.6593, T_11 = 0.7600,
      T_12 = 0.2365, H_11 = -1.1204, H_12 = -0.9584, (11|11) = 0.7746,
      (11|22) = 0.5697, (21|11) = 0.4441, (21|21) = 0.2970,
      E_RHF = -1.1167 Eh -- the worked minimal-basis H2 example of Szabo &
      Ostlund, ch. 3; independent printed oracle to 4 decimals.
    * PySCF 2.14 (optional, Linux/macOS) with the *same* 6-digit
      contraction: E_RHF(1.4) = -1.1167142748376588 Eh; rhf_run and uhf
      reproduce it to < 1e-12 (different integral code, same basis).
    * Differential comparison with the original JavaScript (fixtures) at the
      §8 bounds.

§8 ERROR ANALYSIS
    u = 2^-53.
    (a) erf: series part -- the alternating sum for x < 3 has N <= 40
        terms whose magnitudes add up to S(x) = sum |t_n|/(2n+1)
        = int_0^x exp(t^2) dt (about 1445 at x = 3; the largest single term
        is ~170 at n = 9), while the result is ~1: cancellation.  Standard
        summation analysis (Higham §4.2) gives
            |fl(erf x) - erf x| <= (2/sqrt(pi)) gamma_N S(x) + 2u,
        i.e. <= 7.3e-12 at x -> 3 in the worst case; observed maximum over
        a 1e-4 grid on [0, 6]: 7.4e-14 at x = 2.949 (round-off behaves like
        a random walk, ~sqrt(N) rather than N).  tests/test_sto3g.py checks
        the bound pointwise against math.erf.  Continued fraction for
        x >= 3: 60 terms give truncation error < 1e-20.  Against the v1.0
        JavaScript the series part is bitwise identical (only + - * / and
        sqrt(pi) are involved); the x >= 3 branch differs only through exp.
    (b) Each primitive integral: one exp, one or two pow, F0 (erf, sqrt):
        relative error <= ~6u in either implementation; difference between
        two implementations <= 12u relative per primitive.
    (c) Contracted integrals: sums of 9 (one-electron) or 81 (ERI) terms of
        the same sign (S, T, ERI are positive here; V negative): relative
        difference stays <= 12u + gamma_81 ~ 1e-14.
    (d) Direct quantities of core.h2 (RHF, CI, MP2, triplet energies) are
        rational/sqrt functions of O(10) integrals with condition numbers
        <= 10 for R in [0.5, 40] bohr: |Delta E| <= 10 * 1e-14 * |E| ->
        bound B_direct = 1e-12 hartree.
    (e) Iterative quantities (UHF, rhf_run): the iteration is a contraction
        towards a fixed point with rate rho < 1; a perturbation delta in the
        integrals moves the fixed point by delta * kappa/(1 - rho) and may
        change the step at which the stopping test fires.  The test uses
        rmsd < 1e-10 (UHF): if both implementations stop at different steps,
        the energies differ by at most the change of E over one step, and E
        is stationary at the fixed point, so |Delta E| <= c * (1e-10)^... --
        conservatively first order: B_iter = 1e-9 hartree for UHF energies,
        1e-8 for <S^2> and density elements (stopping tolerance 1e-10 times a
        damping factor 1/(1 - rho) <= 100 observed near the
        Coulson-Fischer point, where rho -> 1).  For rhf_run (tol = 1e-6)
        the histories are compared step by step: B = 1e-12 for every step
        that both implementations execute (no stopping-test ambiguity unless
        dP lies within 1e-12 of tol, which the tests check explicitly).
"""
from __future__ import annotations

import functools
import math
from typing import Any

from .smallmat import Matrix, eig_sym, gauss, mat, mmul, tps
from .jsmath import exp, js_pow, sq

STO3G_A = (0.109818, 0.405771, 2.22766)
STO3G_D = (0.444635, 0.535328, 0.154329)

Primitive = dict[str, float]
Integrals = dict[str, Any]


# ---------------------------------------------------------------- special fn
def erf(x: float) -> float:
    """Error function: Maclaurin series for x < 3, erfc continued fraction beyond."""
    if x < 0:
        return -erf(-x)
    if x < 3:
        # erf x = 2/sqrt(pi) * sum_n (-1)^n x^(2n+1) / (n! (2n+1));
        # t carries (-1)^n x^(2n+1)/n!
        s = 0.0
        t = x
        n = 0
        while abs(t) > 1e-17 * abs(s) or n < 3:
            s = s + t / (2 * n + 1)
            n += 1
            t = t * (-x * x / n)
        return 2 / math.sqrt(math.pi) * s
    # erfc x = exp(-x^2)/sqrt(pi) / (x + 1/2/(x + 1/(x + 3/2/(x + ...))))
    f = 0.0
    for k in range(60, 0, -1):
        f = k / 2 / (x + f)
    return 1 - exp(-x * x) / math.sqrt(math.pi) / (x + f)


@functools.lru_cache(maxsize=1 << 16)
def F0(t: float) -> float:
    """Boys function of order 0 (memoised: see §6)."""
    return 1 - t / 3 if t < 1e-8 else 0.5 * math.sqrt(math.pi / t) * erf(math.sqrt(t))


# ---------------------------------------------------------------- basis
def basis(zeta: float, center: float) -> list[Primitive]:
    """STO-3G 1s contraction scaled to Slater exponent zeta, centred at z."""
    return [{"a": a * zeta * zeta,
             "d": STO3G_D[i] * js_pow(2 * a * zeta * zeta / math.pi, 0.75),
             "c": center}
            for i, a in enumerate(STO3G_A)]


def _d2(A: float, B: float) -> float:
    return (A - B) * (A - B)


# ---------------------------------------------------------------- primitives
def s_prim(p: Primitive, q: Primitive) -> float:
    """Overlap of two unnormalised s Gaussians."""
    g = p["a"] + q["a"]
    return js_pow(math.pi / g, 1.5) * exp(-p["a"] * q["a"] / g * _d2(p["c"], q["c"]))


def t_prim(p: Primitive, q: Primitive) -> float:
    """Kinetic-energy integral of two s Gaussians."""
    g = p["a"] + q["a"]
    r = p["a"] * q["a"] / g
    return r * (3 - 2 * r * _d2(p["c"], q["c"])) * js_pow(math.pi / g, 1.5) * exp(-r * _d2(p["c"], q["c"]))


def v_prim(p: Primitive, q: Primitive, C: float, Z: float) -> float:
    """Nuclear attraction to charge Z at z = C."""
    g = p["a"] + q["a"]
    P = (p["a"] * p["c"] + q["a"] * q["c"]) / g
    return -2 * math.pi / g * Z * exp(-p["a"] * q["a"] / g * _d2(p["c"], q["c"])) * F0(g * _d2(P, C))


def eri_prim(p: Primitive, q: Primitive, r: Primitive, s: Primitive) -> float:
    """Two-electron repulsion (pq|rs) of s Gaussians."""
    g1 = p["a"] + q["a"]
    g2 = r["a"] + s["a"]
    P = (p["a"] * p["c"] + q["a"] * q["c"]) / g1
    Q = (r["a"] * r["c"] + s["a"] * s["c"]) / g2
    return (2 * js_pow(math.pi, 2.5) / (g1 * g2 * math.sqrt(g1 + g2))
            * exp(-p["a"] * q["a"] / g1 * _d2(p["c"], q["c"]) - r["a"] * s["a"] / g2 * _d2(r["c"], s["c"]))
            * F0(g1 * g2 / (g1 + g2) * _d2(P, Q)))


def c2(f, A: list[Primitive], B: list[Primitive]) -> float:
    """Contract a one-electron primitive integral over two basis functions."""
    s = 0.0
    for p in A:
        for q in B:
            s = s + p["d"] * q["d"] * f(p, q)
    return s


def c4(A, B, C, D) -> float:
    """Contract (pq|rs) over four basis functions."""
    s = 0.0
    for p in A:
        for q in B:
            for r in C:
                for t in D:
                    s = s + p["d"] * q["d"] * r["d"] * t["d"] * eri_prim(p, q, r, t)
    return s


def integrals(atoms: list[dict]) -> Integrals:
    """All integrals for two atoms on the z axis, one 1s function each."""
    if len(atoms) != 2:
        raise ValueError("integrals: exactly two atoms are supported")
    for at in atoms:
        if not (at["Z"] > 0 and at["zeta"] > 0):
            raise ValueError("integrals: Z and zeta must be positive")
    if atoms[0]["z"] == atoms[1]["z"]:
        raise ValueError("integrals: atoms must be at different positions")
    B = [basis(at["zeta"], at["z"]) for at in atoms]
    n = len(B)
    S, T, V, H = [], [], [], []
    for i in range(n):
        S.append([]); T.append([]); V.append([]); H.append([])
        for j in range(n):
            S[i].append(c2(s_prim, B[i], B[j]))
            T[i].append(c2(t_prim, B[i], B[j]))
            v = 0.0
            for at in atoms:  # sum over nuclei, in atom order (JS reduce)
                v = v + c2(lambda p, q, at=at: v_prim(p, q, at["z"], at["Z"]), B[i], B[j])
            V[i].append(v)
            H[i].append(T[i][j] + V[i][j])
    cache: dict[tuple[int, int, int, int], float] = {}

    def eri(i, j, k, l):
        key = (i, j, k, l)
        if key not in cache:
            cache[key] = c4(B[i], B[j], B[k], B[l])
        return cache[key]

    G = [[[[eri(i, j, k, l) for l in range(n)] for k in range(n)] for j in range(n)] for i in range(n)]
    Vnn = atoms[0]["Z"] * atoms[1]["Z"] / abs(atoms[0]["z"] - atoms[1]["z"])
    return {"B": B, "S": S, "T": T, "V": V, "H": H, "ERI": G, "Vnn": Vnn, "n": n}


# ---------------------------------------------------------------- SCF pieces
def x_matrix(S: Matrix) -> Matrix:
    """Symmetric (Loewdin) orthogonaliser S^{-1/2}."""
    w, Vv = eig_sym(S)
    if min(w) <= 0:
        raise ValueError("x_matrix: overlap matrix is not positive definite")
    return mmul(mmul(Vv, mat(len(w), lambda i, j: 1 / math.sqrt(w[i]) if i == j else 0.0)), tps(Vv))


def build_g(I: Integrals, P: Matrix) -> Matrix:
    """Two-electron part G_ij = sum_kl P_kl [(ij|kl) - 1/2 (il|kj)]."""
    n, E = I["n"], I["ERI"]

    def g(i, j):
        s = 0.0
        for k in range(n):
            for l in range(n):
                s = s + P[k][l] * (E[i][j][k][l] - 0.5 * E[i][l][k][j])
        return s
    return mat(n, g)


def build_f(I: Integrals, P: Matrix) -> dict[str, Matrix]:
    """Fock matrix F = H + G[P]."""
    G = build_g(I, P)
    return {"G": G, "F": mat(I["n"], lambda i, j: I["H"][i][j] + G[i][j])}


def solve_fc(I: Integrals, F: Matrix, X: Matrix) -> dict[str, Any]:
    """Solve F C = S C eps via F' = X^T F X; sign convention: largest |c| > 0."""
    Fp = mmul(mmul(tps(X), F), X)
    w, Vv = eig_sym(Fp)
    C = mmul(X, Vv)
    cols = []
    for col in tps(C):
        m = 0.0
        for x in col:  # first element of largest magnitude (JS reduce)
            m = x if abs(x) > abs(m) else m
        cols.append([-x for x in col] if m < 0 else col)
    return {"eps": w, "C": tps(cols), "Fp": Fp}


def density_from(C: Matrix, nocc: int) -> Matrix:
    """Closed-shell density P = 2 sum_{a<nocc} C_ia C_ja."""
    def p(i, j):
        s = 0.0
        for a in range(nocc):
            s = s + 2 * C[i][a] * C[j][a]
        return s
    return mat(len(C), p)


def energy(I: Integrals, P: Matrix) -> float:
    """Electronic RHF energy 1/2 sum P (H + F)."""
    F = build_f(I, P)["F"]
    s = 0.0
    for i in range(I["n"]):
        for j in range(I["n"]):
            s = s + 0.5 * P[i][j] * (I["H"][i][j] + F[i][j])
    return s


def rmsd(A: Matrix, B: Matrix) -> float:
    """Root-mean-square difference of matrix elements."""
    fa = [x for r in A for x in r]
    fb = [x for r in B for x in r]
    s = 0.0
    for k, x in enumerate(fa):
        s = s + sq(x - fb[k])
    return math.sqrt(s / len(fa))


def chi_on_axis(I: Integrals, mu: int, z: float) -> float:
    """Basis function mu evaluated on the molecular axis."""
    s = 0.0
    for p in I["B"][mu]:
        s = s + p["d"] * exp(-p["a"] * sq(z - p["c"]))
    return s


# ---------------------------------------------------------------- UHF
def build_jk(I: Integrals, P: Matrix) -> dict[str, Matrix]:
    """Coulomb J_ij = sum P_kl (ij|kl) and exchange K_ij = sum P_kl (il|kj)."""
    n, E = I["n"], I["ERI"]

    def j_(i, j):
        s = 0.0
        for k in range(n):
            for l in range(n):
                s = s + P[k][l] * E[i][j][k][l]
        return s

    def k_(i, j):
        s = 0.0
        for k in range(n):
            for l in range(n):
                s = s + P[k][l] * E[i][l][k][j]
        return s
    return {"J": mat(n, j_), "K": mat(n, k_)}


def _require2(I: Integrals, who: str) -> None:
    if I["n"] != 2:
        raise ValueError(f"{who}: implemented for two basis functions only")


def uhf(I: Integrals, X: Matrix, init=None, maxit: int = 500, mix: float = 0.5) -> dict[str, Any]:
    """Two-electron UHF (one alpha, one beta) with density damping."""
    _require2(I, "uhf")
    Pa = init[0] if init else [[1.0, 0.0], [0.0, 0.0]]
    Pb = init[1] if init else [[0.0, 0.0], [0.0, 1.0]]
    H = I["H"]
    ca = cb = None
    it = 0
    while True:
        it += 1
        if it > maxit:
            break
        Pt = mat(2, lambda i, j: Pa[i][j] + Pb[i][j])
        Jt = build_jk(I, Pt)["J"]
        Ka = build_jk(I, Pa)["K"]
        Kb = build_jk(I, Pb)["K"]
        Fa = mat(2, lambda i, j: H[i][j] + Jt[i][j] - Ka[i][j])
        Fb = mat(2, lambda i, j: H[i][j] + Jt[i][j] - Kb[i][j])
        En = 0.0
        for i in range(2):
            for j in range(2):
                En = En + 0.5 * (Pt[i][j] * H[i][j] + Pa[i][j] * Fa[i][j] + Pb[i][j] * Fb[i][j])
        ra = solve_fc(I, Fa, X)
        rb = solve_fc(I, Fb, X)
        ca = [r[0] for r in ra["C"]]  # lowest alpha orbital
        cb = [r[0] for r in rb["C"]]  # lowest beta orbital
        Na = mat(2, lambda i, j: ca[i] * ca[j])
        Nb = mat(2, lambda i, j: cb[i] * cb[j])
        d = max(rmsd(Na, Pa), rmsd(Nb, Pb))
        Pa = mat(2, lambda i, j: mix * Na[i][j] + (1 - mix) * Pa[i][j])
        Pb = mat(2, lambda i, j: mix * Nb[i][j] + (1 - mix) * Pb[i][j])
        if d < 1e-10 and it > 3:
            break
    # energy at the final (damped) densities
    Pt = mat(2, lambda i, j: Pa[i][j] + Pb[i][j])
    Jt = build_jk(I, Pt)["J"]
    Ka = build_jk(I, Pa)["K"]
    Kb = build_jk(I, Pb)["K"]
    E = 0.0
    for i in range(2):
        for j in range(2):
            E = E + 0.5 * (Pt[i][j] * H[i][j] + Pa[i][j] * (H[i][j] + Jt[i][j] - Ka[i][j])
                           + Pb[i][j] * (H[i][j] + Jt[i][j] - Kb[i][j]))
    sab = 0.0
    for i in range(2):
        for j in range(2):
            sab = sab + ca[i] * I["S"][i][j] * cb[j]
    return {"E": E + I["Vnn"], "S2": 1 - sab * sab, "Pa": Pa, "Pb": Pb, "it": it}


# ---------------------------------------------------------------- DIIS / SCF
def diis_error(F: Matrix, P: Matrix, S: Matrix) -> Matrix:
    """Commutator error e = F P S - S P F."""
    A = mmul(mmul(F, P), S)
    B = mmul(mmul(S, P), F)
    return mat(len(F), lambda i, j: A[i][j] - B[i][j])


def diis_extrap(lst: list[dict]) -> dict[str, Any]:
    """Pulay DIIS extrapolation over the stored (F, e) pairs."""
    m = len(lst)
    if m < 2:
        return {"F": lst[m - 1]["F"], "c": [1.0]}
    n = m + 1
    B = mat(n, lambda i, j: 0.0)
    rhs = [0.0] * n
    flat = [[x for r in it["e"] for x in r] for it in lst]
    for i in range(m):
        for j in range(m):
            s = 0.0
            for k, x in enumerate(flat[i]):
                s = s + x * flat[j][k]
            B[i][j] = s
    for i in range(m):
        B[i][m] = -1.0
        B[m][i] = -1.0
    rhs[m] = -1.0
    # scale the error block to O(1) so the 1e-14 pivot test is meaningful
    sc = max([1e-30] + [abs(B[i][i]) for i in range(m)])
    for i in range(m):
        for j in range(m):
            B[i][j] = B[i][j] / sc
    c = gauss(B, rhs)
    if not c or any(not math.isfinite(x) for x in c):
        return {"F": lst[m - 1]["F"], "c": [1.0 if i == m - 1 else 0.0 for i in range(m)]}
    nF = len(lst[0]["F"])

    def f(i, j):
        s = 0.0
        for k, it in enumerate(lst):
            s = s + c[k] * it["F"][i][j]
        return s
    return {"F": mat(nF, f), "c": c[:m]}


def rhf_run(I: Integrals, X: Matrix, P0: Matrix, maxit: int = 200, tol: float = 1e-6,
            damp: float = 0.0, diis: bool = False) -> dict[str, Any]:
    """RHF iterations (plain, damped or DIIS with 2 vectors) for 1 doubly occupied MO."""
    _require2(I, "rhf_run")
    P = [list(r) for r in P0]
    hist = []
    dl: list[dict] = []
    E = 0.0
    for k in range(1, (maxit or 200) + 1):
        F = build_f(I, P)["F"]
        Fu = F
        if diis and k >= 2:
            dl.append({"F": F, "e": diis_error(F, P, I["S"])})
            if len(dl) > 2:
                dl.pop(0)
            Fu = diis_extrap(dl)["F"]
        r = solve_fc(I, Fu, X)
        Pn = density_from(r["C"], 1)
        a = 0.0 if diis else (damp or 0.0)
        Pn = mat(2, lambda i, j: (1 - a) * Pn[i][j] + a * P[i][j])
        d = rmsd(Pn, P)
        P = Pn
        E = energy(I, P) + I["Vnn"]
        hist.append({"k": k, "E": E, "dP": d, "eps": r["eps"]})
        if d < (tol or 1e-6):
            break
    return {"E": E, "P": P, "hist": hist}

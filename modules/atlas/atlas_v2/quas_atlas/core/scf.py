"""The self-consistent field procedure, step by step (H2 and HeH+, STO-3G).

HEADER
    Numerical model of the Atlas page "SCF" (web/<lang>/scf.html): the
    Roothaan iteration shown stage by stage, DIIS, damping, the RHF/UHF
    potential curves, the variational principle in the Slater exponent, and
    Mulliken/Loewdin population analysis. Port of the v1.0 page script;
    machinery in core.sto3g. Wilkinson convention, §1-§8.

§1 THEORY
    Closed-shell RHF for two electrons in two basis functions chi_1, chi_2
    (core.sto3g §1). One SCF cycle k:
        F^(k) = h + G[P^(k-1)] (Fock matrix)
        F^(k) C = S C eps (Roothaan equations)
        P_new = 2 c_1 c_1^T (both electrons in phi_1)
        P^(k) = (1 - a) P_new + a P^(k-1) (damping, 0 <= a < 1)
        E^(k) = 1/2 tr P^(k) (h + F[P^(k)]) + V_nn
    stopped when ||Delta P||_rms = rmsd(P^(k), P^(k-1)) < delta = 1e-6 or
    after 200 cycles. With DIIS (Pulay) the matrix diagonalised from the
    third cycle on is F_DIIS = sum c_i F^(i) over the last two cycles, with
    error vectors e = F P S - S P F (zero exactly at self-consistency);
    damping is then switched off.

    Variational principle: for fixed R the RHF energy as a function of the
    Slater exponent zeta of the 1s functions has a minimum; any other zeta
    gives a higher energy.

    Population analysis of the converged P:
        Mulliken N_A = (PS)_AA, q_A = Z_A - (PS)_AA,
        overlap population 2 P_12 S_12,
        Loewdin N_A = (S^{1/2} P S^{1/2})_AA,
        Mayer bond order (PS)_12 (PS)_21.

§2 ALGORITHM
    trajectory(): integrals, X = S^{-1/2}; reference energy E_conv by plain
    iterations from P = 0 to rmsd < 1e-12 (<= 500 cycles); the requested
    run from P^(0) (0, or both electrons on atom A or B) with the cycle of
    §1, recording for every cycle G, F, F_DIIS (or None) and its
    coefficients, eps, C, P_old, P, E, rmsd and max |Delta P|, Mulliken
    charges q_A = Z_A - sum_j P_Aj S_jA, and the orbitals and density on
    the molecular axis; the "ghost" run is the same calculation with DIIS
    toggled (core.sto3g.rhf_run).
    scan(): RHF (tol 1e-9) and UHF energies and <S^2> on R = 0.6..6 step
    0.05 bohr; limit = min(E_RHF, E_UHF) at 40 bohr; R_e by 40 ternary
    section steps of E_RHF(R) (tol 1e-10) on [max(R_min - 0.1),
    R_min + 0.1], R_min = grid minimum.
    zeta_curve(): E_RHF on zeta = 0.6..3.6 step 0.04 and the minimiser by
    60 ternary-section steps on [0.6, 3.6].
    populations(): the formulas of §1 at R and on R = 0.6..6 step 0.1.

§3 APPLICATIONS
    The page animates the cycle (flow chart, matrices, orbital diagram,
    orbitals and density on the axis, convergence plot, a program-style
    log), compares plain/damped/DIIS iterations, shows the RHF dissociation
    failure of H2 (UHF symmetry breaking at the Coulson-Fischer point,
    spin contamination), the variational minimum in zeta, and how Mulliken
    and Loewdin charges differ.

§4 SPECIFICATION
    mol in {"HeH", "H2"}; R in [0.3, 40] bohr; zeta_a, zeta_b in (10];
    guess in {"core", "A", "B"}; damp in [0, 0.99]; diis: bool;
    who: list of atom indices whose zeta is varied ([0, 1] for H2).
    trajectory(...) -> {I: {S, H, ERI, Vnn}, P0, Econv, ghost: [{k, dP}],
        iters: [{G, F, Fd, dc, eps, C, Pold, P, E, dP, mDP, q, orb: [2 x
        240], rho: [240]}], axis: {z, chi0, chi1, rho0 (zeros), rhoP0}}.
    scan(mol, za, zb) -> {pts: [{R, rhf, uhf, s2}] x 109, lim, limA, zat, re, reE};
      limA: free atoms with their own optimal zeta (ternary search on
      [0.6, 3.0], 50 steps; zat its argument), 0.80.
    zeta_curve(mol, R, za, zb, who) -> {pts: [{z, E}] x 76, zm, Em}.
    populations(mol, R, za, zb) -> {p: Pop(R), curve: [Pop] x 55};
        Pop = {R, P, S, net, op, gm, gl, qm, ql, mayer}.
    Energies in hartree, lengths in bohr.
    Reference implementation: v1.0 scf.html (reset, step, computeScan,
    Ezeta/zMin, popAt/popCurve), V8.
    Equivalence tier: ``bound`` -- order of operations preserved; libm
    differences (core.sto3g §8): B = 1e-12 for every recorded quantity of
    the trajectory and the populations except the DIIS coefficients
    (B_c = 64 u / min ||e|| + 1e-12, §8); R_e and zeta_min from ternary
    section: B = 1e-7 (§8).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * The page's state machine (stages init -> guess -> F -> diag -> P ->
      check) stays in the browser; it only walks through the recorded
      trajectory, so every intermediate matrix it shows is a Python result.
    * scan/zeta_curve/populations are memoised: each costs 100-200 SCF runs
      (~1-2 s in CPython) and the page asks for them on every redraw.
§7 TEST CASES (tests/test_scf.py)
    * HeH+ at R = 1.4632 bohr, zeta = (2.0925, 1.24): E = -2.86066 Eh
      (Szabo & Ostlund, ch. 3, printed in the page text and in the book);
      first-iteration Mulliken charge of H +0.84 -> converged +0.53 (page
      text, from the book's discussion).
    * Invariants: sum of Mulliken charges = total charge (+1 for HeH+, 0 for
      H2); tr(PS) = 2; Loewdin populations sum to 2; for H2 both charges 0
      and the Mayer order 1 at every R; the DIIS run converges in no more
      cycles than the plain one; zeta minimum energy <= energy at any grid
      zeta.
    * PySCF (optional) with the same basis: converged RHF energies.
    * Differential test against the v1.0 JavaScript (fixtures).
§8 ERROR ANALYSIS
    Per cycle every quantity is a fixed sequence of +,-,*,/,sqrt and the
    libm calls inside the integrals (core.sto3g §8 (b)-(c): relative
    1e-14); the SCF map is contractive with rate < 1 for these systems, so
    the difference between two implementations stays O(1e-14) per element
    and does not accumulate beyond 1e-12 over 200 cycles (contraction).
    The stopping test could fire one cycle earlier or later only if rmsd
    fell within 1e-12 of delta -- the tests check that the recorded
    trajectories have equal length. Ternary section: after n steps the
    bracket is (2/3)^n of its start: 0.2 (2/3)^40 = 1.8e-8 bohr for R_e,
    3 (2/3)^60 = 8e-11 for zeta_min. Near the minimum E(m1) and E(m2)
    differ by ~ k (Delta)^2; a comparison can flip between implementations
    only when that difference is below the energy noise (1e-15 Eh), i.e.
    for Delta < sqrt(1e-15/k) ~ 1e-7 (k ~ 0.1-0.5 Eh/bohr^2). Hence
    B = 1e-7 for R_e and zeta_min; energies at those points then differ by
    k B^2 < 1e-14.
    DIIS coefficients are the exception to B = 1e-12: they solve a system
    built from the error vectors e = F P S - S P F, which vanish at
    convergence. Each element of e is computed from O(1) matrices with an
    absolute error <= ~16 u (two 2x2 products, entries <= 3), so its
    relative error is ~16 u / ||e||, doubled in B_ij = e_i . e_j and
    amplified by the 3x3 solve (kappa <= ~2 after the page's scaling):
    |Delta c| <= 64 u / min ||e|| + 1e-12. Near convergence (||e|| ~ 1e-9)
    that is ~6e-6; observed 3.5e-11 (HeH+, last DIIS cycle). F_DIIS itself
    stays accurate to B: with sum c = 1, Delta F_DIIS = Delta c_1 (F_1 - F_2)
    and F_1 - F_2 = O(||e||), so the two small factors cancel.
"""
from __future__ import annotations

import functools
import math

from .smallmat import eig_sym, mat, mmul, tps
from .sto3g import (build_f, chi_on_axis, density_from, diis_error, diis_extrap, energy, integrals,
                    rhf_run, rmsd, solve_fc, uhf, x_matrix)

MOLS = {
    "HeH": {"Z": (2, 1), "zeta": (2.0925, 1.24), "R": 1.4632},
    "H2": {"Z": (1, 1), "zeta": (1.24, 1.24), "R": 1.4},
}
DELTA = 1e-6
MAXIT = 200
AXIS_N = 240


def check(mol: str, R: float, za: float, zb: float) -> None:
    if mol not in MOLS:
        raise ValueError(f"unknown molecule {mol}")
    if not (0.3 <= R <= 40):
        raise ValueError("R must be in [0.3, 40] bohr")
    if not (0.1 < za <= 10 and 0.1 < zb <= 10):
        raise ValueError("zeta must be in (0.1, 10]")


def atoms(mol: str, R: float, za: float, zb: float) -> list[dict]:
    Z = MOLS[mol]["Z"]
    return [{"Z": Z[0], "zeta": za, "z": 0.0}, {"Z": Z[1], "zeta": zb, "z": R}]


def p0(guess: str) -> list[list[float]]:
    """Initial density: both electrons on atom A, on atom B, or none (core)."""
    if guess == "A":
        return [[2.0, 0.0], [0.0, 0.0]]
    if guess == "B":
        return [[0.0, 0.0], [0.0, 2.0]]
    if guess == "core":
        return [[0.0, 0.0], [0.0, 0.0]]
    raise ValueError(f"unknown initial guess {guess}")


def _charges(I, at, P):
    """Mulliken charges q_A = Z_A - sum_j P_Aj S_jA."""
    out = []
    for i, a in enumerate(at):
        s = 0.0
        for j, x in enumerate(P[i]):
            s = s + x * I["S"][j][i]
        out.append(a["Z"] - s)
    return out


def _axis(I, R):
    z0, z1 = -2.2, R + 2.2
    zs = [z0 + (z1 - z0) * i / (AXIS_N - 1) for i in range(AXIS_N)]
    chi = [(chi_on_axis(I, 0, z), chi_on_axis(I, 1, z)) for z in zs]
    return zs, chi


def _rho(chi, P):
    return [P[0][0] * c[0] * c[0] + 2 * P[0][1] * c[0] * c[1] + P[1][1] * c[1] * c[1] for c in chi]


def _orb(chi, C):
    return [[c[0] * C[0][m] + c[1] * C[1][m] for c in chi] for m in (0, 1)]


@functools.lru_cache(maxsize=64)
def trajectory(mol: str, R: float, za: float, zb: float, guess: str, damp: float, diis: bool) -> dict:
    """Every cycle of the SCF as the page shows it (see §2)."""
    check(mol, R, za, zb)
    if not 0 <= damp <= 0.99:
        raise ValueError("damp must be in [0, 0.99]")
    at = atoms(mol, R, za, zb)
    I = integrals(at)
    X = x_matrix(I["S"])
    # reference: plain iterations from P = 0 to rmsd < 1e-12
    P = [[0.0, 0.0], [0.0, 0.0]]
    for _ in range(500):
        F = build_f(I, P)["F"]
        C = solve_fc(I, F, X)["C"]
        Pn = density_from(C, 1)
        d = rmsd(Pn, P)
        P = Pn
        if d < 1e-12:
            break
    Econv = energy(I, P) + I["Vnn"]
    ghost = rhf_run(I, X, p0(guess), diis=not diis, damp=damp)["hist"]
    zs, chi = _axis(I, R)
    # the requested run, cycle by cycle
    P = p0(guess)
    dl: list[dict] = []
    iters: list[dict] = []
    k = 0
    while True:
        if iters and iters[-1]["dP"] < DELTA:
            break
        if k >= MAXIT:
            break
        k += 1
        r = build_f(I, P)
        G, F = r["G"], r["F"]
        Fd = dc = None
        if diis and k >= 2:
            dl.append({"F": F, "e": diis_error(F, P, I["S"])})
            if len(dl) > 2:
                dl.pop(0)
            if len(dl) >= 2:
                x = diis_extrap(dl)
                Fd, dc = x["F"], x["c"]
        sol = solve_fc(I, Fd or F, X)
        eps, C = sol["eps"], sol["C"]
        Pn = density_from(C, 1)
        a = 0.0 if diis else damp
        Pm = [[(1 - a) * x + a * P[i][j] for j, x in enumerate(row)] for i, row in enumerate(Pn)]
        dP = rmsd(Pm, P)
        fo, fn = [x for row in P for x in row], [x for row in Pm for x in row]
        mDP = max(abs(x - fo[i]) for i, x in enumerate(fn))
        Pold, P = P, Pm
        E = energy(I, P) + I["Vnn"]
        iters.append({"k": k, "G": G, "F": F, "Fd": Fd, "dc": dc, "eps": eps, "C": C, "Pold": Pold, "P": P,
                      "E": E, "dP": dP, "mDP": mDP, "q": _charges(I, at, P), "orb": _orb(chi, C),
                      "rho": _rho(chi, P)})
    return {"I": {"S": I["S"], "H": I["H"], "ERI": I["ERI"], "Vnn": I["Vnn"]}, "P0": p0(guess),
            "Econv": Econv, "ghost": [{"k": h["k"], "dP": h["dP"]} for h in ghost], "iters": iters,
            "axis": {"z": zs, "chi0": [c[0] for c in chi], "chi1": [c[1] for c in chi],
                     "rho0": [0.0] * AXIS_N, "rhoP0": _rho(chi, p0(guess))}}


def _rhf_E(mol, R, za, zb, tol, maxit=200):
    I = integrals(atoms(mol, R, za, zb))
    return rhf_run(I, x_matrix(I["S"]), [[0.0, 0.0], [0.0, 0.0]], tol=tol, maxit=maxit)["E"]


@functools.lru_cache(maxsize=16)
def scan(mol: str, za: float, zb: float) -> dict:
    """RHF and UHF curves, dissociation limit and R_e (see §2)."""
    check(mol, 1.0, za, zb)
    pts = []
    for i in range(109):
        R = 0.6 + i * 0.05
        I = integrals(atoms(mol, R, za, zb))
        X = x_matrix(I["S"])
        r = rhf_run(I, X, [[0.0, 0.0], [0.0, 0.0]], tol=1e-9, maxit=300)
        u = uhf(I, X)
        pts.append({"R": R, "rhf": r["E"], "uhf": u["E"], "s2": u["S2"]})
    If = integrals(atoms(mol, 40, za, zb))
    Xf = x_matrix(If["S"])
    lim = min(rhf_run(If, Xf, [[0.0, 0.0], [0.0, 0.0]], tol=1e-10)["E"], uhf(If, Xf)["E"])

    def e_at(z):
        # free atoms with their own exponent (the molecular zeta is not optimal for the atom)
        Ia = integrals(atoms(mol, 40, z, z if mol == "H2" else zb))
        Xa = x_matrix(Ia["S"])
        return min(rhf_run(Ia, Xa, [[0.0, 0.0], [0.0, 0.0]], tol=1e-10)["E"], uhf(Ia, Xa)["E"])
    ta, tb = 0.6, 3.0
    for _ in range(50):
        m1 = ta + (tb - ta) / 3
        m2 = tb - (tb - ta) / 3
        if e_at(m1) < e_at(m2):
            tb = m2
        else:
            ta = m1
    zat = (ta + tb) / 2
    lim_a = e_at(zat)
    pm = pts[0]
    for p in pts:
        if p["rhf"] < pm["rhf"]:
            pm = p
    a, b = max(0.6, pm["R"] - 0.1), pm["R"] + 0.1

    def fR(R):
        return _rhf_E(mol, R, za, zb, 1e-10)
    for _ in range(40):  # ternary section for the minimum of E_RHF(R)
        m1 = a + (b - a) / 3
        m2 = b - (b - a) / 3
        if fR(m1) < fR(m2):
            b = m2
        else:
            a = m1
    re = (a + b) / 2
    return {"pts": pts, "lim": lim, "limA": lim_a, "zat": zat, "re": re, "reE": fR(re)}


@functools.lru_cache(maxsize=32)
def zeta_curve(mol: str, R: float, za: float, zb: float, who: tuple[int, ...]) -> dict:
    """E_RHF as a function of the Slater exponent of the atoms in ``who``."""
    check(mol, R, za, zb)
    if not who or any(i not in (0, 1) for i in who):
        raise ValueError("who must list atom indices 0 and/or 1")

    def Ez(z):
        zs = [za, zb]
        for i in who:
            zs[i] = z
        return _rhf_E(mol, R, zs[0], zs[1], 1e-9, 300)
    pts = [{"z": 0.6 + i * 0.04, "E": Ez(0.6 + i * 0.04)} for i in range(76)]
    a, b = 0.6, 3.6
    for _ in range(60):
        m1 = a + (b - a) / 3
        m2 = b - (b - a) / 3
        if Ez(m1) < Ez(m2):
            b = m2
        else:
            a = m1
    zm = (a + b) / 2
    return {"pts": pts, "zm": zm, "Em": Ez(zm)}


def _sqrt_s(S):
    w, V = eig_sym(S)
    return mmul(mmul(V, mat(len(S), lambda i, j: math.sqrt(w[i]) if i == j else 0.0)), tps(V))


def pop_at(mol: str, R: float, za: float, zb: float) -> dict:
    """Mulliken / Loewdin / Mayer analysis of the converged RHF density."""
    at = atoms(mol, R, za, zb)
    I = integrals(at)
    X = x_matrix(I["S"])
    P = rhf_run(I, X, [[0.0, 0.0], [0.0, 0.0]], tol=1e-10, maxit=400)["P"]
    S = I["S"]
    PS = mmul(P, S)
    Sh = _sqrt_s(S)
    L = mmul(mmul(Sh, P), Sh)
    return {"R": R, "P": P, "S": S, "net": [P[0][0], P[1][1]], "op": 2 * P[0][1] * S[0][1],
            "gm": [PS[0][0], PS[1][1]], "gl": [L[0][0], L[1][1]],
            "qm": [a["Z"] - PS[i][i] for i, a in enumerate(at)],
            "ql": [a["Z"] - L[i][i] for i, a in enumerate(at)], "mayer": PS[0][1] * PS[1][0]}


@functools.lru_cache(maxsize=16)
def pop_curve(mol: str, za: float, zb: float) -> list[dict]:
    return [pop_at(mol, 0.6 + i * 0.1, za, zb) for i in range(55)]


@functools.lru_cache(maxsize=128)
def populations(mol: str, R: float, za: float, zb: float) -> dict:
    check(mol, R, za, zb)
    return {"p": pop_at(mol, R, za, zb), "curve": pop_curve(mol, za, zb)}

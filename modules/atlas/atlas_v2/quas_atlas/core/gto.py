"""Gaussian-type orbitals: basis sets, McMurchie-Davidson integrals, RHF with DIIS, MP2, dipole
moment, electrostatic potential, basis-function values and the electron density with derivatives.

HEADER
    The calculation engine of the pages "Проверка расчётов" and "Атомы в
    молекулах" (v1.0 validation.js / aim.js: function ENGINE, object GTO:
    sto3g, b631, AUG, BASES, primNorm, buildBasis, Ecoef, boys, Rtab,
    pairData, oneElectron, Rflat, pairERI, eri, jacobi, mm, tr, nucRep,
    prep, rhf, solve, mp2, dipole, espPrep, bfEval, rhoAt).  Wilkinson
    convention, sections 1-8.  Atomic units (bohr, hartree).

§1 THEORY
    Cartesian Gaussians x^lx y^ly z^lz exp(-a r^2) (six Cartesian d
    functions, as in the original 6-31G*), primitive norm (2a/pi)^(3/4)
    (4a)^(L/2) / sqrt((2lx-1)!!(2ly-1)!!(2lz-1)!!), contractions normalised
    on the lx = L component.  Basis sets: STO-3G (Hehre, Stewart, Pople
    1969, universal expansions scaled by zeta^2), 6-31G, 6-31G*, 6-31G**
    (Hehre, Ditchfield, Pople 1972; Hariharan, Pople 1973), and an
    aug-cc-pVDZ-like set for He.  McMurchie-Davidson: Hermite expansion
    coefficients E_t^{ij} by the two-term recursion E_t^{i+1,j} =
    E_{t-1}^{ij}/(2p) + X_PA E_t^{ij} + (t+1) E_{t+1}^{ij} (likewise for
    j), E_0^{00} = exp(-q X_AB^2), q = ab/p; overlap S = E_0 (pi/p)^(3/2)
    per direction; kinetic energy from overlaps with j+2, j, j-2; Coulomb
    integrals through the Hermite integrals R_{tuv}^n (recursion on
    t, u, v from R_{000}^n = (-2p)^n F_n(p R_PC^2)) and the Boys function
    F_n(T) (series for F_nmax and downward recursion; asymptotic form for
    T > 35; 1/(2n+1) for T < 1e-12).  Two-electron integrals with the
    8-fold permutational symmetry, Schwarz screening |(ab|cd)| <=
    Q_ab Q_cd < 1e-11 skipped.  RHF: canonical orthogonalisation
    (eigenvalues of S below 1e-7 dropped), generalised Wolfsberg-Helmholz
    or core guess, Fock matrix F = H + J - K/2 from the unique integrals,
    DIIS on the commutator FDS - SDF (at most 8 vectors), stop when |dE| <
    1e-10 and max |FDS - SDF| < 1e-7.  The energy is always evaluated with
    the returned density and its Fock matrix.  MP2: four quarter
    transformations to (ia|jb), E2 = sum (ia|jb)(2(ia|jb) - (ib|ja)) /
    (e_i + e_j - e_a - e_b).  Dipole: sum Z_A R_A - sum D <mu|r|nu>
    (first Hermite moment).  ESP: V(r) = sum Z/|r - R| - sum over
    primitive pairs of D-weighted Hermite expansions times R_{tuv}(r).
    Basis-function values with first and second derivatives; density
    rho = sum D phi phi, gradient, Hessian, positive-definite kinetic
    energy density G = (1/2) sum D grad phi . grad phi.

§2 ALGORITHM
    As v1.0, statement by statement, with the same summation orders
    (pure-Python reference path).  numpy accelerates the two-electron
    integrals (primitive quartets of all shell quartets of the same shape
    in one batch), the Fock build, the Jacobi rotations and every
    evaluation on many points; see §4 for why the results do not change.

§3 APPLICATIONS
    core.qtaim (critical points, Bader basins), the endpoints val.* (page
    validation) and aim.* (page aim).

§4 SPECIFICATION
    build_basis(atoms, name) -> {"shells": [{atom, l, O, e, cc, comps,
      off}], "nbf"}; atoms [{el, x, y, z}] in bohr.
    prep(atoms, basis, charge=0) -> sys {atoms (with Z; ghost -> 0), bs,
      one {S, T, V}, two {G}, ne, Enuc}; matrices are flat row-major lists.
    rhf(sys, guess=None|"core", diis=True, maxit=100, tol=1e-10) ->
      {E, Eel, eps, C, nmo, D, H, F, nocc, log, converged, iterations}.
    mp2(sys, res), dipole(sys, res) -> [mx, my, mz], esp_prep(sys, res) ->
      V(x, y, z), bf_eval(bs, x, y, z, deriv), rho_at(bs, D, x, y, z, deriv).
    Batch versions (numpy): bf_eval_np, rho_at_np(..., kin) at arrays of
      points; V.many_exact(points) for the ESP; V.many (faster, matmul
      order: bound tier |dV| <= 1e-12 |V|, not used by the pages).
    Equivalence tier: bitwise vs v1.0 (V8 in Chromium on Linux/glibc) for
    both paths.  The pure-Python path is the statement-by-statement port;
    the numpy path (used automatically when numpy is importable: ERI and
    RHF for nbf > NP_MIN, grids always) evaluates the same scalar
    expressions with array operands -- elementwise IEEE operations, the
    vectorised fdlibm exp of jsmath_np, sums accumulated in the scalar
    order -- so every number is the same double.  Verified for H2O
    (STO-3G, 6-31G, 6-31G*, 6-31G**), He2 with a ghost atom, the seven
    molecules of the validation table and the molecules of tests/test_aim.
    prep() results are cached per (geometry, basis, charge).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Float64Array -> Python list of floats (zero-initialised with 0.0);
    Math.pow -> js_pow, Math.exp -> jsmath.exp (fdlibm, as V8),
    Math.hypot -> js_hypot.  `if(!x)continue` skips +0, -0 and NaN as in
    JS (`not x` in Python is True for +-0.0; NaN never occurs).  The ERI
    array uses the canonical pair index i(i+1)/2 + j as in v1.0.
§7 TEST CASES (tests/test_gto.py)
    Independent oracles: Boys F_n(0) = 1/(2n+1) and F_0(T) = sqrt(pi/T)
    erf(sqrt T)/2 (math.erf); contracted functions normalised (S_ii = 1);
    virial theorem -V/T = 2 at the converged HF geometry-independent
    level for atoms (He); H2O energies of Szabo & Ostlund (table 3.x:
    STO-3G -74.963, 6-31G* -76.011, 6-31G** -76.023) to 1e-3 and the
    Crawford project 3/4 values (E = -74.942079928192, E2 =
    -0.049149636120, mu = 0.603521296525, q_O = -0.253146052405) to 1e-6;
    PySCF (optional, importorskip) for RHF energies with cart=True;
    vs v1.0 (fixtures recorded in Chromium 141).
§8 ERROR ANALYSIS
    Integrals: Boys function to 1e-17 relative (series stop), downward
    recursion stable; contraction sums of <= 36 terms of like sign
    except sp shells: relative error ~1e-15.  SCF converged to |dE| <
    1e-10 E_h and max|FDS - SDF| < 1e-7, so energies carry ~1e-10 E_h of
    convergence error, densities ~1e-7.  Comparison with published
    energies is limited by the published digits (three decimals in the
    table of the page: 0.5 mE_h); the two N2 entries differ by 0.69 mE_h
    and are marked as unconfirmed on the page.  Equality with v1.0 is exact
    (§4), so no tolerance is needed for it; the only platform dependence is
    Math.pow (core.jsmath.js_pow calls the platform pow, which equals V8 on
    Linux/glibc; exp/log/sin/cos are ports) -- on another libm the last bit
    of pow-dependent primitive norms could differ, which is why the tier is
    stated for Linux/glibc.
"""
from __future__ import annotations

import math

from .jsmath import exp, js_hypot, js_pow, js_sign

try:  # optional accelerator (§4)
    import numpy as _np
    from .jsmath_np import exp_np, seq_sum
except ImportError:  # pragma: no cover - exercised by tests with QUAS_NO_NUMPY
    _np = None
import os as _os

if _os.environ.get("QUAS_NO_NUMPY") == "1":
    _np = None

PI = math.pi
NP_MIN = 12   # use numpy kernels above this number of basis functions

# ---------------------------------------------------------------- basis sets
S3 = {"e1": [2.227660584, 0.405771156, 0.109818036], "c1": [0.154328967, 0.535328142, 0.444634542],
      "e2": [0.994202729, 0.231031333, 0.0751385857], "c2s": [-0.0999672292, 0.399512826, 0.700115469], "c2p": [0.155916275, 0.607683719, 0.391957393],
      "e3": [0.482854150, 0.134715100, 0.0527266000], "c3s": [-0.219620369, 0.225595934, 0.900398426], "c3p": [0.010587604, 0.595167005, 0.462001012]}
ZETA = {"H": [1.24], "He": [1.69], "Li": [2.69, 0.80], "Be": [3.68, 1.15], "B": [4.68, 1.50], "C": [5.67, 1.72], "N": [6.67, 1.95],
        "O": [7.66, 2.25], "F": [8.65, 2.55], "Ne": [9.64, 2.88], "Cl": [16.43, 6.26, 2.10]}


def sto3g(el):
    z = ZETA[el]
    sh = []

    def sc(e, k):
        return [x * k * k for x in e]
    sh.append({"l": 0, "e": sc(S3["e1"], z[0]), "c": S3["c1"]})
    if len(z) > 1:
        e = sc(S3["e2"], z[1])
        sh.append({"l": 0, "e": e, "c": S3["c2s"]})
        sh.append({"l": 1, "e": e, "c": S3["c2p"]})
    if len(z) > 2:
        e = sc(S3["e3"], z[2])
        sh.append({"l": 0, "e": e, "c": S3["c3s"]})
        sh.append({"l": 1, "e": e, "c": S3["c3p"]})
    return sh


B631 = {
    "H": {"s": [[18.7311370, 0.03349460], [2.8253937, 0.23472695], [0.6401217, 0.81375733]], "o": 0.1612778, "d": 1.1},
    "He": {"s": [[38.4216340, 0.0237660], [5.7780300, 0.1546790], [1.2417740, 0.4696300]], "o": 0.2979640, "d": 1.1},
    "C": {"c": [[3047.5249, 0.0018347], [457.36951, 0.0140373], [103.94869, 0.0688426], [29.210155, 0.2321844], [9.2866630, 0.4679413], [3.1639270, 0.3623120]],
          "v": [[7.8682724, -0.1193324, 0.0689991], [1.8812885, -0.1608542, 0.3164240], [0.5442493, 1.1434564, 0.7443083]], "o": 0.1687144, "d": 0.8},
    "N": {"c": [[4173.5110, 0.0018348], [627.45790, 0.0139950], [142.90210, 0.0685870], [40.234330, 0.2322410], [12.820210, 0.4690700], [4.3904370, 0.3604550]],
          "v": [[11.626358, -0.1149610, 0.0675800], [2.7162800, -0.1691180, 0.3239070], [0.7722180, 1.1458520, 0.7408950]], "o": 0.2120313, "d": 0.8},
    "O": {"c": [[5484.6717, 0.0018311], [825.23495, 0.0139501], [188.04696, 0.0684451], [52.964500, 0.2327143], [16.897570, 0.4701930], [5.7996353, 0.3585209]],
          "v": [[15.539616, -0.1107775, 0.0708743], [3.5999336, -0.1480263, 0.3397528], [1.0137618, 1.1307670, 0.7271586]], "o": 0.2700058, "d": 0.8},
    "Li": {"c": [[642.418915, 0.00214260], [96.7985153, 0.0162089], [22.0911212, 0.0773156], [6.20107025, 0.245786], [1.93511768, 0.470189], [0.636735789, 0.345471]],
           "v": [[2.32491783, -0.0350917, 0.00894150], [0.632430357, -0.191233, 0.141010], [0.0790534224, 1.08399, 0.945364]], "o": 0.0359620, "d": 0.2},
    "F": {"c": [[7001.7130, 0.0018196], [1051.3660, 0.0139160], [239.28570, 0.0684053], [67.397450, 0.2331850], [21.519570, 0.4712670], [7.4031010, 0.3566190]],
          "v": [[20.847952, -0.1085070, 0.0716287], [4.8083080, -0.1464520, 0.3459121], [1.3440700, 1.1286880, 0.7224700]], "o": 0.3581514, "d": 0.8},
}


def b631(el, pol):
    b = B631[el]
    sh = []
    if "s" in b:
        sh.append({"l": 0, "e": [x[0] for x in b["s"]], "c": [x[1] for x in b["s"]]})
        sh.append({"l": 0, "e": [b["o"]], "c": [1]})
        if pol >= 2:
            sh.append({"l": 1, "e": [b["d"]], "c": [1]})
        return sh
    sh.append({"l": 0, "e": [x[0] for x in b["c"]], "c": [x[1] for x in b["c"]]})
    ev = [x[0] for x in b["v"]]
    sh.append({"l": 0, "e": ev, "c": [x[1] for x in b["v"]]})
    sh.append({"l": 1, "e": ev, "c": [x[2] for x in b["v"]]})
    sh.append({"l": 0, "e": [b["o"]], "c": [1]})
    sh.append({"l": 1, "e": [b["o"]], "c": [1]})
    if pol >= 1:
        sh.append({"l": 2, "e": [b["d"]], "c": [1]})
    return sh


ZN = {"H": 1, "He": 2, "Li": 3, "Be": 4, "B": 5, "C": 6, "N": 7, "O": 8, "F": 9, "Ne": 10, "Cl": 17}
AUG = {"He": [{"l": 0, "e": [38.36, 5.77, 1.24], "c": [0.023809, 0.154891, 0.469987]}, {"l": 0, "e": [0.2976], "c": [1]},
              {"l": 1, "e": [1.275], "c": [1]}, {"l": 0, "e": [0.07255], "c": [1]}, {"l": 1, "e": [0.2473], "c": [1]}]}


def _aug(el):
    if el not in AUG:
        raise KeyError("no")
    return AUG[el]


BASES = {"aug-cc-pVDZ": _aug, "STO-3G": sto3g, "6-31G": lambda el: b631(el, 0), "6-31G*": lambda el: b631(el, 1),
         "6-31G**": lambda el: b631(el, 2)}


def has_basis(name, el) -> bool:
    try:
        BASES[name](el)
        return True
    except (KeyError, TypeError):
        return False


CART = [[[0, 0, 0]], [[1, 0, 0], [0, 1, 0], [0, 0, 1]], [[2, 0, 0], [0, 2, 0], [0, 0, 2], [1, 1, 0], [1, 0, 1], [0, 1, 1]]]


def dfact(n):
    return 1 if n <= 0 else n * dfact(n - 2)


def prim_norm(a, lx, ly, lz):
    L = lx + ly + lz
    return js_pow(2 * a / PI, 0.75) * js_pow(4 * a, L / 2) / math.sqrt(dfact(2 * lx - 1) * dfact(2 * ly - 1) * dfact(2 * lz - 1))


def build_basis(atoms, name):
    shells = []
    nbf = 0
    for ia, A in enumerate(atoms):
        for s in BASES[name](A["el"]):
            comps = CART[s["l"]]
            L = s["l"]
            np_ = len(s["e"])
            ss = 0
            for i in range(np_):
                for j in range(np_):
                    a, b = s["e"][i], s["e"][j]
                    ss += (s["c"][i] * s["c"][j] * prim_norm(a, L, 0, 0) * prim_norm(b, L, 0, 0) * js_pow(PI / (a + b), 1.5)
                           * dfact(2 * L - 1) / js_pow(2 * (a + b), L))
            cn = 1 / math.sqrt(ss)
            cc = [[s["c"][i] * cn * prim_norm(a, lx, ly, lz) for i, a in enumerate(s["e"])] for lx, ly, lz in comps]
            shells.append({"atom": ia, "l": L, "O": [A["x"], A["y"], A["z"]], "e": list(s["e"]), "cc": cc, "comps": comps, "off": nbf})
            nbf += len(comps)
    return {"shells": shells, "nbf": nbf}


# ---------------------------------------------------------------- Hermite coefficients, Boys function
def ecoef(i, j, a, b, Qx):
    p = a + b
    q = a * b / p
    T = [[[0.0] * (ii + jj + 1) for jj in range(j + 1)] for ii in range(i + 1)]
    T[0][0][0] = exp(-q * Qx * Qx)
    XPA = -b * Qx / p
    XPB = a * Qx / p
    ip2 = 1 / (2 * p)
    for ii in range(i + 1):
        for jj in range(j + 1):
            if ii == 0 and jj == 0:
                continue
            cur = T[ii][jj]
            if ii > 0:
                pr = T[ii - 1][jj]
                X = XPA
            else:
                pr = T[ii][jj - 1]
                X = XPB
            npr = len(pr)
            for t in range(ii + jj + 1):
                v = 0
                if t - 1 >= 0 and t - 1 < npr:
                    v += ip2 * pr[t - 1]
                if t < npr:
                    v += X * pr[t]
                if t + 1 < npr:
                    v += (t + 1) * pr[t + 1]
                cur[t] = float(v)
    return T


def boys(nmax, T):
    F = [0.0] * (nmax + 1)
    if T < 1e-12:
        for n in range(nmax + 1):
            F[n] = 1 / (2 * n + 1)
        return F
    if T > 35:
        F[0] = 0.5 * math.sqrt(PI / T)
        e = exp(-T)
        for n in range(nmax):
            F[n + 1] = ((2 * n + 1) * F[n] - e) / (2 * T)
        return F
    e = exp(-T)
    term = 1 / (2 * nmax + 1)
    s = term
    for k in range(1, 200):
        term *= 2 * T / (2 * nmax + 2 * k + 1)
        s += term
        if term < 1e-17 * s:
            break
    F[nmax] = e * s
    for n in range(nmax, 0, -1):
        F[n - 1] = (2 * T * F[n] + e) / (2 * n - 1)
    return F


def rtab(tmax, umax, vmax, p, PC):
    """R_{tuv}^0 as a dict-free closure, v1.0 Rtab."""
    N = tmax + umax + vmax
    F = boys(N, p * (PC[0] * PC[0] + PC[1] * PC[1] + PC[2] * PC[2]))
    D1, D2, D3 = tmax + 1, umax + 1, vmax + 1
    S = D1 * D2 * D3
    R = [0.0] * ((N + 1) * S)

    def idx(n, t, u, v):
        return n * S + (t * D2 + u) * D3 + v
    f = 1
    for n in range(N + 1):
        R[idx(n, 0, 0, 0)] = f * F[n]
        f *= -2 * p
    for n in range(N - 1, -1, -1):
        rem = N - n
        for t in range(min(tmax, rem) + 1):
            for u in range(min(umax, rem - t) + 1):
                for v in range(min(vmax, rem - t - u) + 1):
                    if t + u + v == 0:
                        continue
                    if t > 0:
                        val = PC[0] * R[idx(n + 1, t - 1, u, v)]
                        if t > 1:
                            val += (t - 1) * R[idx(n + 1, t - 2, u, v)]
                    elif u > 0:
                        val = PC[1] * R[idx(n + 1, t, u - 1, v)]
                        if u > 1:
                            val += (u - 1) * R[idx(n + 1, t, u - 2, v)]
                    else:
                        val = PC[2] * R[idx(n + 1, t, u, v - 1)]
                        if v > 1:
                            val += (v - 1) * R[idx(n + 1, t, u, v - 2)]
                    R[idx(n, t, u, v)] = val
    return lambda t, u, v: R[(t * D2 + u) * D3 + v]


def pair_data(A, B):
    prims = []
    for i in range(len(A["e"])):
        for j in range(len(B["e"])):
            a, b = A["e"][i], B["e"][j]
            p = a + b
            P = [(a * A["O"][k] + b * B["O"][k]) / p for k in range(3)]
            E = [ecoef(A["l"], B["l"], a, b, A["O"][k] - B["O"][k]) for k in range(3)]
            prims.append({"i": i, "j": j, "a": a, "b": b, "p": p, "P": P, "E": E})
    return prims


def one_electron(bs, atoms):
    n = bs["nbf"]
    S = [0.0] * (n * n)
    T = [0.0] * (n * n)
    V = [0.0] * (n * n)
    sh = bs["shells"]
    for I in range(len(sh)):
        for J in range(I + 1):
            A, B = sh[I], sh[J]
            pd = pair_data(A, B)
            pdK = [[ecoef(A["l"], B["l"] + 2, q["a"], q["b"], A["O"][k] - B["O"][k]) for k in range(3)] for q in pd]
            for ia, ca in enumerate(A["comps"]):
                for ib, cb in enumerate(B["comps"]):
                    s = t = v = 0
                    for kq, q in enumerate(pd):
                        w = A["cc"][ia][q["i"]] * B["cc"][ib][q["j"]]
                        E = q["E"]
                        p = q["p"]
                        sx = E[0][ca[0]][cb[0]][0]
                        sy = E[1][ca[1]][cb[1]][0]
                        sz = E[2][ca[2]][cb[2]][0]
                        pre = js_pow(PI / p, 1.5)
                        s += w * pre * sx * sy * sz
                        E2 = pdK[kq]
                        b = q["b"]

                        def s1(d):
                            e2 = E2[d]
                            m = cb[d]
                            r = -2 * b * b * e2[ca[d]][m + 2][0] + b * (2 * m + 1) * e2[ca[d]][m][0]
                            if m >= 2:
                                r -= 0.5 * m * (m - 1) * e2[ca[d]][m - 2][0]
                            return r
                        t += w * pre * (s1(0) * sy * sz + sx * s1(1) * sz + sx * sy * s1(2))
                        tm, um, vm = ca[0] + cb[0], ca[1] + cb[1], ca[2] + cb[2]
                        for C in atoms:
                            R = rtab(tm, um, vm, p, [q["P"][0] - C["x"], q["P"][1] - C["y"], q["P"][2] - C["z"]])
                            acc = 0
                            for tt in range(tm + 1):
                                ex = E[0][ca[0]][cb[0]][tt]
                                if not ex:
                                    continue
                                for uu in range(um + 1):
                                    ey = E[1][ca[1]][cb[1]][uu]
                                    if not ey:
                                        continue
                                    for vv in range(vm + 1):
                                        ez = E[2][ca[2]][cb[2]][vv]
                                        if not ez:
                                            continue
                                        acc += ex * ey * ez * R(tt, uu, vv)
                            v += -float(C["Z"]) * w * 2 * PI / p * acc
                    mu, nu = A["off"] + ia, B["off"] + ib
                    S[mu * n + nu] = S[nu * n + mu] = s
                    T[mu * n + nu] = T[nu * n + mu] = t
                    V[mu * n + nu] = V[nu * n + mu] = v
    return {"S": S, "T": T, "V": V}


# ---------------------------------------------------------------- two-electron integrals
def rflat(L, al, PQ, R, W):
    D = L + 1
    S = D * D * D
    T = al * (PQ[0] * PQ[0] + PQ[1] * PQ[1] + PQ[2] * PQ[2])
    Fb = boys(L, T)
    f = 1
    for n in range(L + 1):
        W[n * S] = f * Fb[n]
        f *= -2 * al
    X, Y, Z = PQ
    for n in range(L - 1, -1, -1):
        rem = L - n
        base = n * S
        nb = (n + 1) * S
        for t in range(rem + 1):
            for u in range(rem - t + 1):
                for v in range(rem - t - u + 1):
                    if t + u + v == 0:
                        continue
                    if t > 0:
                        val = X * W[nb + ((t - 1) * D + u) * D + v]
                        if t > 1:
                            val += (t - 1) * W[nb + ((t - 2) * D + u) * D + v]
                    elif u > 0:
                        val = Y * W[nb + (t * D + u - 1) * D + v]
                        if u > 1:
                            val += (u - 1) * W[nb + (t * D + u - 2) * D + v]
                    else:
                        val = Z * W[nb + (t * D + u) * D + v - 1]
                        if v > 1:
                            val += (v - 1) * W[nb + (t * D + u) * D + v - 2]
                    W[base + (t * D + u) * D + v] = val
    for i in range(S):
        R[i] = W[i]


def pair_eri(A, B):
    nA, nB = len(A["comps"]), len(B["comps"])
    Lab = A["l"] + B["l"]
    herm = []
    for t in range(Lab + 1):
        for u in range(Lab - t + 1):
            for v in range(Lab - t - u + 1):
                herm.append((t, u, v))
    nh = len(herm)
    prims = []
    for q in pair_data(A, B):
        E = [0.0] * (nA * nB * nh)
        for ia in range(nA):
            for ib in range(nB):
                ca, cb = A["comps"][ia], B["comps"][ib]
                w = A["cc"][ia][q["i"]] * B["cc"][ib][q["j"]]
                Ex = q["E"][0][ca[0]][cb[0]]
                Ey = q["E"][1][ca[1]][cb[1]]
                Ez = q["E"][2][ca[2]][cb[2]]
                for h, (t, u, v) in enumerate(herm):
                    E[(ia * nB + ib) * nh + h] = w * Ex[t] * Ey[u] * Ez[v] if (t < len(Ex) and u < len(Ey) and v < len(Ez)) else 0.0
        prims.append({"p": q["p"], "P": q["P"], "E": E})
    return {"A": A, "B": B, "nA": nA, "nB": nB, "herm": herm, "prims": prims}


def _idx2(i, j):
    return i * (i + 1) // 2 + j if i > j else j * (j + 1) // 2 + i


def _quartet_py(pa, pb, R, W):
    n1 = pa["nA"] * pa["nB"]
    n2 = pb["nA"] * pb["nB"]
    h1 = len(pa["herm"])
    h2 = len(pb["herm"])
    out = [0.0] * (n1 * n2)
    L = pa["A"]["l"] + pa["B"]["l"] + pb["A"]["l"] + pb["B"]["l"]
    D = L + 1
    sg = [(-1.0 if (t + u + v) & 1 else 1.0) for t, u, v in pb["herm"]]
    sidx = [((t + a) * D + u + b) * D + v + c for (t, u, v) in pa["herm"] for (a, b, c) in pb["herm"]]
    X = [0.0] * (h1 * n2)
    p25 = js_pow(PI, 2.5)
    for q1 in pa["prims"]:
        for q2 in pb["prims"]:
            p, qq = q1["p"], q2["p"]
            al = p * qq / (p + qq)
            rflat(L, al, [q1["P"][0] - q2["P"][0], q1["P"][1] - q2["P"][1], q1["P"][2] - q2["P"][2]], R, W)
            pre = 2 * p25 / (p * qq * math.sqrt(p + qq))
            E2 = q2["E"]
            for i in range(h1):
                ro = i * h2
                for k in range(n2):
                    s = 0
                    eo = k * h2
                    for j in range(h2):
                        e = E2[eo + j]
                        if e:
                            s += R[sidx[ro + j]] * sg[j] * e
                    X[i * n2 + k] = s
            E1 = q1["E"]
            for b in range(n1):
                eo = b * h1
                for i in range(h1):
                    e = E1[eo + i]
                    if not e:
                        continue
                    f = pre * e
                    xo = i * n2
                    for k in range(n2):
                        out[b * n2 + k] += f * X[xo + k]
    return out


def eri(bs):
    """Unique two-electron integrals (pq|rs) in v1.0 packed order; numpy path bitwise identical."""
    n = bs["nbf"]
    sh = bs["shells"]
    NS = len(sh)
    npair = n * (n + 1) // 2
    pairs = [pair_eri(sh[I], sh[J]) for I in range(NS) for J in range(I + 1)]
    if _np is not None and n > NP_MIN:
        return _eri_np(bs, pairs)
    G = [0.0] * (npair * (npair + 1) // 2)
    Lmax = 4 * max(s["l"] for s in sh)
    Dm = Lmax + 1
    R = [0.0] * (Dm * Dm * Dm)
    W = [0.0] * ((Lmax + 1) * Dm * Dm * Dm)
    Q = []
    for pa in pairs:
        o = _quartet_py(pa, pa, R, W)
        m = 0
        n1 = pa["nA"] * pa["nB"]
        for i in range(n1):
            m = max(m, abs(o[i * n1 + i]))
        Q.append(math.sqrt(m))
    for P1 in range(len(pairs)):
        pa = pairs[P1]
        for P2 in range(P1 + 1):
            pb = pairs[P2]
            if Q[P1] * Q[P2] < 1e-11:
                continue
            out = _quartet_py(pa, pb, R, W)
            _store(G, pa, pb, out)
    return {"G": G}


def _store(G, pa, pb, out):
    A, B, C, Dd = pa["A"], pa["B"], pb["A"], pb["B"]
    nB, nD = pa["nB"], pb["nB"]
    n2 = pb["nA"] * pb["nB"]
    for ia in range(pa["nA"]):
        for ib in range(nB):
            ij = _idx2(A["off"] + ia, B["off"] + ib)
            for ic in range(pb["nA"]):
                for idd in range(nD):
                    G[_idx2(ij, _idx2(C["off"] + ic, Dd["off"] + idd))] = float(out[(ia * nB + ib) * n2 + ic * nD + idd])


def _eri_np(bs, pairs):
    """Batched numpy version: Hermite integrals of all primitive quartets with the same total L are
    computed together (chunked), the contraction per shell quartet; arithmetic as in _quartet_py."""
    np = _np
    n = bs["nbf"]
    npair = n * (n + 1) // 2
    G = np.zeros(npair * (npair + 1) // 2)
    for pa in pairs:
        _pair_np(pa)
    diagq = [(P, P) for P in range(len(pairs))]
    outs = _quartets_np(pairs, diagq)
    Q = []
    for P, o in zip(range(len(pairs)), outs):
        n1 = pairs[P]["nA"] * pairs[P]["nB"]
        m = 0
        for i in range(n1):
            m = max(m, abs(float(o[i * n1 + i])))
        Q.append(math.sqrt(m))
    todo = [(P1, P2) for P1 in range(len(pairs)) for P2 in range(P1 + 1) if not (Q[P1] * Q[P2] < 1e-11)]
    # packed target indices of every quartet, then one scatter
    _quartets_np(pairs, todo, G)
    return {"G": G.tolist()}


def _targets(pa, pb):
    np = _np
    key = "_tg" + str(id(pb))
    A, B, C, Dd = pa["A"], pa["B"], pb["A"], pb["B"]
    i = A["off"] + np.arange(pa["nA"])[:, None, None, None]
    j = B["off"] + np.arange(pa["nB"])[None, :, None, None]
    k = C["off"] + np.arange(pb["nA"])[None, None, :, None]
    l_ = Dd["off"] + np.arange(pb["nB"])[None, None, None, :]
    ij = np.where(i > j, i * (i + 1) // 2 + j, j * (j + 1) // 2 + i)
    kl = np.where(k > l_, k * (k + 1) // 2 + l_, l_ * (l_ + 1) // 2 + k)
    return np.where(ij > kl, ij * (ij + 1) // 2 + kl, kl * (kl + 1) // 2 + ij).ravel()


def _quartets_np(pairs, quartets, G=None):
    """out arrays (n1*n2,) of the shell quartets [(P1, P2)], bitwise as _quartet_py.
    Quartets with the same shapes (angular momenta, numbers of primitives) are
    evaluated together: every array operation is elementwise across quartets and
    every sum runs over its own axis in the scalar order.  With G given, the
    results are scattered into G (packed indices, quartet by quartet) instead."""
    np = _np
    groups: dict = {}
    for qi, (P1, P2) in enumerate(quartets):
        pa, pb = pairs[P1], pairs[P2]
        A, B = pa["_np"], pb["_np"]
        L = pa["A"]["l"] + pa["B"]["l"] + pb["A"]["l"] + pb["B"]["l"]
        key = (L, A["p"].shape[0], B["p"].shape[0], A["E"].shape, B["E"].shape, A["herm"].tobytes(), B["herm"].tobytes(),
               pa["nA"], pa["nB"], pb["nA"], pb["nB"])
        groups.setdefault(key, []).append(qi)
    res = [None] * len(quartets) if G is None else None
    for key, qis in groups.items():
        L, m1, m2 = key[0], key[1], key[2]
        D = L + 1
        D3 = D * D * D
        m = m1 * m2
        P0 = quartets[qis[0]]
        A0, B0 = pairs[P0[0]]["_np"], pairs[P0[1]]["_np"]
        h1, h2 = A0["herm"], B0["herm"]
        sg = np.where(h2.sum(1) & 1, -1.0, 1.0)
        sidx = (((h1[:, None, 0] + h2[None, :, 0]) * D + h1[:, None, 1] + h2[None, :, 1]) * D + h1[:, None, 2] + h2[None, :, 2])
        ncA, ncB = A0["E"].shape[1], B0["E"].shape[1]
        cq = max(1, int(4e6 // ((L + 2) * D3 * m + h1.shape[0] * h2.shape[0] * ncB * m + 1)))
        for c0 in range(0, len(qis), cq):
            chunk = qis[c0:c0 + cq]
            Q = len(chunk)
            PA = [pairs[quartets[q][0]] for q in chunk]
            PB = [pairs[quartets[q][1]] for q in chunk]
            Ap = np.stack([x["_np"]["p"] for x in PA])
            Bp = np.stack([x["_np"]["p"] for x in PB])
            AP = np.stack([x["_np"]["P"] for x in PA])
            BP = np.stack([x["_np"]["P"] for x in PB])
            AE = np.stack([x["_np"]["E"] for x in PA])
            BE = np.stack([x["_np"]["E"] for x in PB])
            p = np.repeat(Ap, m2, axis=1)
            qq = np.tile(Bp, (1, m1))
            al = p * qq / (p + qq)
            PQ = np.repeat(AP, m2, axis=1) - np.tile(BP, (1, m1, 1))
            pre = 2 * _P25 / (p * qq * np.sqrt(p + qq))
            R = _rflat_np(L, al.ravel(), PQ.reshape(-1, 3)).reshape(Q, m, D3)
            Rg = R[:, :, sidx] * sg[None, None, None, :]
            E2 = np.tile(BE, (1, m1, 1, 1))
            nh1, nh2 = sidx.shape
            # X[q, i, h1, b] = sum_h2 Rg[q, i, h1, h2] E2[q, i, b, h2] (h2 in order, from +0)
            X = np.zeros((Q, m, nh1, ncB))
            for h in range(nh2):
                X += Rg[:, :, :, None, h] * E2[:, :, None, :, h]
            f = pre[:, :, None, None] * np.repeat(AE, m2, axis=1)
            # out[q, a, b] = sum over (i, h1) in row-major order of f[q, i, a, h1] X[q, i, h1, b]
            out = np.zeros((Q, ncA, ncB))
            for i in range(m):
                fi, Xi = f[:, i], X[:, i]
                for h in range(nh1):
                    out += fi[:, :, h, None] * Xi[:, h, None, :]
            out = out.reshape(Q, -1)
            if G is None:
                for k, q in enumerate(chunk):
                    res[q] = out[k]
            else:
                G[_targets_many(PA, PB)] = out.ravel()
    return res


def _targets_many(PA, PB):
    """_targets of several quartets of the same shape, concatenated quartet by quartet."""
    np = _np
    pa, pb = PA[0], PB[0]
    oA = np.array([x["A"]["off"] for x in PA])[:, None, None, None, None]
    oB = np.array([x["B"]["off"] for x in PA])[:, None, None, None, None]
    oC = np.array([x["A"]["off"] for x in PB])[:, None, None, None, None]
    oD = np.array([x["B"]["off"] for x in PB])[:, None, None, None, None]
    i = oA + np.arange(pa["nA"])[None, :, None, None, None]
    j = oB + np.arange(pa["nB"])[None, None, :, None, None]
    k = oC + np.arange(pb["nA"])[None, None, None, :, None]
    l_ = oD + np.arange(pb["nB"])[None, None, None, None, :]
    ij = np.where(i > j, i * (i + 1) // 2 + j, j * (j + 1) // 2 + i)
    kl = np.where(k > l_, k * (k + 1) // 2 + l_, l_ * (l_ + 1) // 2 + k)
    return np.where(ij > kl, ij * (ij + 1) // 2 + kl, kl * (kl + 1) // 2 + ij).ravel()


def eri_get(two, i, j, k, l):
    return two["G"][_idx2(_idx2(i, j), _idx2(k, l))]


# numpy kernel of one shell quartet: the same arithmetic as _quartet_py, vectorised over primitive
# quartets and Hermite indices; sums are accumulated with ufunc.accumulate (sequential), so the
# result is bitwise identical to the scalar path (§4, §8)
def _boys_np(nmax, T):
    np = _np
    T = np.asarray(T, dtype=float)
    F = np.zeros((nmax + 1,) + T.shape)
    small = T < 1e-12
    big = T > 35
    mid = ~(small | big)
    for n in range(nmax + 1):
        F[n][small] = 1 / (2 * n + 1)
    if big.any():
        Tb = T[big]
        Fb = np.zeros((nmax + 1,) + Tb.shape)
        Fb[0] = 0.5 * np.sqrt(PI / Tb)
        e = exp_np(-Tb)
        for n in range(nmax):
            Fb[n + 1] = ((2 * n + 1) * Fb[n] - e) / (2 * Tb)
        F[:, big] = Fb
    if mid.any():
        Tm = T[mid]
        e = exp_np(-Tm)
        s = np.full(Tm.shape, 1 / (2 * nmax + 1))
        # the series of every element runs until its own stopping test (elements
        # that stopped are taken out of the working arrays; same per-element operations)
        ix = np.arange(Tm.size)
        ta, sa, Ta = s.copy(), s.copy(), Tm.copy()
        for k in range(1, 200):
            ta = ta * (2 * Ta / (2 * nmax + 2 * k + 1))
            sa = sa + ta
            done = ta < 1e-17 * sa
            if done.any():
                s[ix[done]] = sa[done]
                keep = ~done
                ix, ta, sa, Ta = ix[keep], ta[keep], sa[keep], Ta[keep]
            if not ix.size:
                break
        if ix.size:
            s[ix] = sa
        Fm = np.zeros((nmax + 1,) + Tm.shape)
        Fm[nmax] = e * s
        for n in range(nmax, 0, -1):
            Fm[n - 1] = (2 * Tm * Fm[n] + e) / (2 * n - 1)
        F[:, mid] = Fm
    return F


def _rflat_np(L, al, PQ):
    """Hermite integrals R_{tuv}^0 for arrays al (m,), PQ (m, 3) -> (m, D, D, D); rflat() elementwise."""
    np = _np
    m = al.shape[0]
    D = L + 1
    T = al * (PQ[:, 0] * PQ[:, 0] + PQ[:, 1] * PQ[:, 1] + PQ[:, 2] * PQ[:, 2])
    Fb = _boys_np(L, T)
    W = np.zeros((L + 1, m, D, D, D))
    f = np.ones(m)
    for n in range(L + 1):
        W[n, :, 0, 0, 0] = f * Fb[n]
        f = f * (-2 * al)
    X, Y, Z = PQ[:, 0], PQ[:, 1], PQ[:, 2]
    for n in range(L - 1, -1, -1):
        rem = L - n
        Wn, Wn1 = W[n], W[n + 1]
        for t in range(rem + 1):
            for u in range(rem - t + 1):
                for v in range(rem - t - u + 1):
                    if t + u + v == 0:
                        continue
                    if t > 0:
                        val = X * Wn1[:, t - 1, u, v]
                        if t > 1:
                            val = val + (t - 1) * Wn1[:, t - 2, u, v]
                    elif u > 0:
                        val = Y * Wn1[:, t, u - 1, v]
                        if u > 1:
                            val = val + (u - 1) * Wn1[:, t, u - 2, v]
                    else:
                        val = Z * Wn1[:, t, u, v - 1]
                        if v > 1:
                            val = val + (v - 1) * Wn1[:, t, u, v - 2]
                    Wn[:, t, u, v] = val
    return W[0]


def _pair_np(pa):
    c = pa.get("_np")
    if c is None:
        np = _np
        nh = len(pa["herm"])
        n1 = pa["nA"] * pa["nB"]
        c = {"p": np.array([q["p"] for q in pa["prims"]]), "P": np.array([q["P"] for q in pa["prims"]]).reshape(-1, 3),
             "E": np.array([q["E"] for q in pa["prims"]]).reshape(len(pa["prims"]), n1, nh),
             "herm": np.array(pa["herm"], dtype=np.int64).reshape(nh, 3)}
        pa["_np"] = c
    return c


def _seq0(a, axis):
    """Sequential sum along axis starting from +0 (bitwise equal to a left-to-right loop)."""
    np = _np
    z = np.zeros_like(np.take(a, [0], axis=axis))
    return np.add.accumulate(np.concatenate((z, a), axis=axis), axis=axis).take(-1, axis=axis)


_P25 = js_pow(PI, 2.5)


def _quartet_np(pa, pb):
    np = _np
    A, B = _pair_np(pa), _pair_np(pb)
    m1, m2 = A["p"].shape[0], B["p"].shape[0]
    L = pa["A"]["l"] + pa["B"]["l"] + pb["A"]["l"] + pb["B"]["l"]
    D = L + 1
    p = np.repeat(A["p"], m2)
    qq = np.tile(B["p"], m1)
    al = p * qq / (p + qq)
    PQ = np.repeat(A["P"], m2, axis=0) - np.tile(B["P"], (m1, 1))
    pre = 2 * _P25 / (p * qq * np.sqrt(p + qq))
    R = _rflat_np(L, al, PQ).reshape(m1 * m2, D * D * D)
    h1, h2 = A["herm"], B["herm"]
    sg = np.where(h2.sum(1) & 1, -1.0, 1.0)
    sidx = (((h1[:, None, 0] + h2[None, :, 0]) * D + h1[:, None, 1] + h2[None, :, 1]) * D + h1[:, None, 2] + h2[None, :, 2])
    Rg = R[:, sidx] * sg[None, None, :]                       # (m, h1, h2): R*sg
    E2 = np.tile(B["E"], (m1, 1, 1))                          # (m, n2, h2)
    X = _seq0(Rg[:, :, None, :] * E2[:, None, :, :], -1)      # (m, h1, n2): sum_j (R sg) e
    f = pre[:, None, None] * np.repeat(A["E"], m2, axis=0)   # (m, n1, h1)
    terms = f.transpose(0, 2, 1)[:, :, :, None] * X[:, :, None, :]   # (m, h1, n1, n2)
    out = _seq0(terms.reshape(-1, terms.shape[2], terms.shape[3]), 0)
    return out.ravel()


# ---------------------------------------------------------------- linear algebra
def jacobi(Ain, n):
    A = list(Ain)
    V = [0.0] * (n * n)
    for i in range(n):
        V[i * n + i] = 1.0
    for _sweep in range(100):
        off = 0
        for i in range(n):
            for j in range(i + 1, n):
                off += A[i * n + j] * A[i * n + j]
        if off < 1e-22:
            break
        for p in range(n):
            for q in range(p + 1, n):
                apq = A[p * n + q]
                if abs(apq) < 1e-300:
                    continue
                th = (A[q * n + q] - A[p * n + p]) / (2 * apq)
                sg = 1 if th == 0 or th != th else js_sign(th)
                t = sg / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    akp, akq = A[k * n + p], A[k * n + q]
                    A[k * n + p] = c * akp - s * akq
                    A[k * n + q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = A[p * n + k], A[q * n + k]
                    A[p * n + k] = c * apk - s * aqk
                    A[q * n + k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = V[k * n + p], V[k * n + q]
                    V[k * n + p] = c * vkp - s * vkq
                    V[k * n + q] = s * vkp + c * vkq
    ev = [A[i * n + i] for i in range(n)]
    order = sorted(range(n), key=lambda i: ev[i])
    W = [0.0] * (n * n)
    for k, o in enumerate(order):
        for i in range(n):
            W[i * n + k] = V[i * n + o]
    return {"e": [ev[o] for o in order], "V": W}


def mm(A, B, n, m, k):
    C = [0.0] * (n * k)
    for i in range(n):
        for l_ in range(m):
            a = A[i * m + l_]
            if not a:
                continue
            ck = i * k
            bk = l_ * k
            for j in range(k):
                C[ck + j] += a * B[bk + j]
    return C


def tr(A, n, m):
    B = [0.0] * (m * n)
    for i in range(n):
        for j in range(m):
            B[j * n + i] = A[i * m + j]
    return B


# ---------------------------------------------------------------- RHF
def nuc_rep(atoms):
    e = 0
    for i in range(len(atoms)):
        for j in range(i):
            a, b = atoms[i], atoms[j]
            e += a["Z"] * b["Z"] / js_hypot(a["x"] - b["x"], a["y"] - b["y"], a["z"] - b["z"])
    return e


_PREP: dict = {}


def prep(atoms_in, basis, charge=0):
    key = (tuple((a["el"], float(a["x"]), float(a["y"]), float(a["z"]), bool(a.get("ghost"))) for a in atoms_in), basis, charge)
    if key in _PREP:
        return _PREP[key]
    atoms = [{**a, "Z": 0 if a.get("ghost") else ZN[a["el"]]} for a in atoms_in]
    bs = build_basis(atoms, basis)
    one = one_electron(bs, atoms)
    two = eri(bs)
    ne = 0
    for a in atoms:
        ne = ne + a["Z"]
    ne -= charge or 0
    sys_ = {"atoms": atoms, "bs": bs, "one": one, "two": two, "ne": ne, "Enuc": nuc_rep(atoms)}
    if len(_PREP) > 64:
        _PREP.pop(next(iter(_PREP)))
    _PREP[key] = sys_
    return sys_


def solve(A, b):
    n = len(b)
    M = [list(r) + [b[i]] for i, r in enumerate(A)]
    for c in range(n):
        p = c
        for r in range(c + 1, n):
            if abs(M[r][c]) > abs(M[p][c]):
                p = r
        if abs(M[p][c]) < 1e-14:
            return None
        M[c], M[p] = M[p], M[c]
        for r in range(n):
            if r == c:
                continue
            f = M[r][c] / M[c][c]
            for k in range(c, n + 1):
                M[r][k] -= f * M[c][k]
    return [r[n] / r[i] for i, r in enumerate(M)]


def _fock_py(H, D, G, n):
    J = [0.0] * (n * n)
    K = [0.0] * (n * n)
    for i in range(n):
        for j in range(i + 1):
            ij = i * (i + 1) // 2 + j
            base = ij * (ij + 1) // 2
            for k in range(i + 1):
                lmax = j if k == i else k
                kk = k * (k + 1) // 2
                for l_ in range(lmax + 1):
                    v = G[base + kk + l_]
                    if v == 0:
                        continue
                    f = 1
                    if i != j:
                        f *= 2
                    if k != l_:
                        f *= 2
                    if not (i == k and j == l_):
                        f *= 2
                    w = v * f
                    J[i * n + j] += D[k * n + l_] * w
                    J[k * n + l_] += D[i * n + j] * w
                    K[i * n + k] += D[j * n + l_] * w
                    K[i * n + l_] += D[j * n + k] * w
                    K[j * n + k] += D[i * n + l_] * w
                    K[j * n + l_] += D[i * n + k] * w
    F = list(H)
    for i in range(n):
        for j in range(n):
            Jij = (J[i * n + j] + J[j * n + i]) / 4
            Kij = (K[i * n + j] + K[j * n + i]) / 8
            F[i * n + j] += Jij - 0.5 * Kij
    return F


def _fock_tables(sys_):
    """Index tables of the unique non-zero integrals in v1.0 loop order (numpy path), cached on sys."""
    t = sys_.get("_ft")
    if t is None:
        np = _np
        n = sys_["bs"]["nbf"]
        G = sys_["two"]["G"]
        I, J, K, L, Wv = [], [], [], [], []
        for i in range(n):
            for j in range(i + 1):
                ij = i * (i + 1) // 2 + j
                base = ij * (ij + 1) // 2
                for k in range(i + 1):
                    lmax = j if k == i else k
                    kk = k * (k + 1) // 2
                    for l_ in range(lmax + 1):
                        v = G[base + kk + l_]
                        if v == 0:
                            continue
                        f = 1
                        if i != j:
                            f *= 2
                        if k != l_:
                            f *= 2
                        if not (i == k and j == l_):
                            f *= 2
                        I.append(i); J.append(j); K.append(k); L.append(l_); Wv.append(v * f)
        I, J, K, L = (np.array(x, dtype=np.int64) for x in (I, J, K, L))
        w = np.array(Wv)
        t = {"tJ": np.stack((I * n + J, K * n + L), 1).ravel(), "sJ": np.stack((K * n + L, I * n + J), 1).ravel(), "wJ": np.repeat(w, 2),
             "tK": np.stack((I * n + K, I * n + L, J * n + K, J * n + L), 1).ravel(),
             "sK": np.stack((J * n + L, J * n + K, I * n + L, I * n + K), 1).ravel(), "wK": np.repeat(w, 4)}
        sys_["_ft"] = t
    return t


def _fock_np(H, D, t, n):
    np = _np
    Jm = np.zeros(n * n)
    Km = np.zeros(n * n)
    np.add.at(Jm, t["tJ"], D[t["sJ"]] * t["wJ"])
    np.add.at(Km, t["tK"], D[t["sK"]] * t["wK"])
    Jm = Jm.reshape(n, n)
    Km = Km.reshape(n, n)
    Jij = (Jm + Jm.T) / 4
    Kij = (Km + Km.T) / 8
    return (H.reshape(n, n) + (Jij - 0.5 * Kij)).ravel()


def mm_np(A, B, n, m, k):
    """mm() on numpy arrays: C_ij = sum_l A_il B_lj accumulated in l order (bitwise as mm)."""
    np = _np
    A = np.asarray(A).reshape(n, m)
    B = np.asarray(B).reshape(m, k)
    return _seq0(A[:, :, None] * B[None, :, :], 1).ravel()


def jacobi_np(Ain, n):
    """jacobi() with vectorised rotations (bitwise as jacobi)."""
    np = _np
    A = np.array(Ain, dtype=float).reshape(n, n)
    V = np.eye(n)
    iu = np.triu_indices(n, 1)
    for _sweep in range(100):
        a = A[iu]
        off = seq_sum(a * a)
        if off < 1e-22:
            break
        for p in range(n):
            for q in range(p + 1, n):
                apq = A[p, q]
                if abs(apq) < 1e-300:
                    continue
                th = float((A[q, q] - A[p, p]) / (2 * apq))  # Python float: th*th may overflow to inf silently, as in JS
                sg = 1 if th == 0 or th != th else js_sign(th)
                t = sg / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                akp, akq = A[:, p].copy(), A[:, q].copy()
                A[:, p] = c * akp - s * akq
                A[:, q] = s * akp + c * akq
                apk, aqk = A[p, :].copy(), A[q, :].copy()
                A[p, :] = c * apk - s * aqk
                A[q, :] = s * apk + c * aqk
                vkp, vkq = V[:, p].copy(), V[:, q].copy()
                V[:, p] = c * vkp - s * vkq
                V[:, q] = s * vkp + c * vkq
    ev = [float(A[i, i]) for i in range(n)]
    order = sorted(range(n), key=lambda i: ev[i])
    return {"e": [ev[o] for o in order], "V": V[:, order].ravel()}


def rhf(sys_, guess=None, diis=True, maxit=100, tol=1e-10, guessF=None):
    """Closed-shell Hartree-Fock (v1.0 rhf).  numpy path (nbf > NP_MIN) is bitwise identical."""
    if _np is not None and sys_["bs"]["nbf"] > NP_MIN:
        return _rhf_np(sys_, guess, diis, maxit, tol, guessF)
    bs, one, two, ne = sys_["bs"], sys_["one"], sys_["two"], sys_["ne"]
    n = bs["nbf"]
    nocc = ne / 2
    S, T, V = one["S"], one["T"], one["V"]
    H = [T[i] + V[i] for i in range(n * n)]
    sd = jacobi(S, n)
    keep = [i for i, v in enumerate(sd["e"]) if v > 1e-7]
    m = len(keep)
    X = [0.0] * (n * m)
    for c, k in enumerate(keep):
        f = 1 / math.sqrt(sd["e"][k])
        for i in range(n):
            X[i * m + c] = sd["V"][i * n + k] * f
    Xt = tr(X, n, m)

    def fock(D):
        return _fock_py(H, D, two["G"], n)

    def diag(F):
        Fp = mm(mm(Xt, F, m, n, n), X, m, n, m)
        r = jacobi(Fp, m)
        return {"e": r["e"], "C": mm(X, r["V"], n, m, m)}

    def dens(C):
        D = [0.0] * (n * n)
        for i in range(n):
            for j in range(n):
                s = 0
                k = 0
                while k < nocc:
                    s += C[i * m + k] * C[j * m + k]
                    k += 1
                D[i * n + j] = 2 * s
        return D

    def gwh():
        F = [0.0] * (n * n)
        for i in range(n):
            for j in range(n):
                F[i * n + j] = H[i * n + i] if i == j else 0.875 * S[i * n + j] * (H[i * n + i] + H[j * n + j])
        return F

    r = diag(guessF or (H if guess == "core" else gwh()))
    D = dens(r["C"])
    E = Eold = 0
    conv = False
    hist, errs, log = [], [], []
    for it in range(1, (maxit or 100) + 1):
        F = fock(D)
        E = 0
        for i in range(n * n):
            E += 0.5 * D[i] * (H[i] + F[i])
        FDS = mm(mm(F, D, n, n, n), S, n, n, n)
        SDF = tr(FDS, n, n)
        err = [0.0] * (n * n)
        en = 0
        for i in range(n * n):
            err[i] = FDS[i] - SDF[i]
            en = max(en, abs(err[i]))
        log.append({"it": it, "E": E + sys_["Enuc"], "dE": E - Eold, "err": en})
        if it > 1 and abs(E - Eold) < (tol or 1e-10) and en < 1e-7:
            conv = True
            break
        Eold = E
        if diis is not False:
            hist.append(F)
            errs.append(err)
            if len(hist) > 8:
                hist.pop(0)
                errs.pop(0)
            k = len(hist)
            if k >= 2:
                B = [[0] * (k + 1) for _ in range(k + 1)]
                for a in range(k):
                    for b in range(k):
                        s = 0
                        ea, eb = errs[a], errs[b]
                        for i in range(n * n):
                            s += ea[i] * eb[i]
                        B[a][b] = s
                for a in range(k):
                    B[a][k] = B[k][a] = -1
                rhs = [0] * (k + 1)
                rhs[k] = -1
                c = solve(B, rhs)
                if c:
                    Fn = [0.0] * (n * n)
                    for a in range(k):
                        ha = hist[a]
                        ca = c[a]
                        for i in range(n * n):
                            Fn[i] += ca * ha[i]
                    F = Fn
        r = diag(F)
        D = dens(r["C"])
    Fin = fock(D)
    fr = diag(Fin)
    Ef = 0
    for i in range(n * n):
        Ef += 0.5 * D[i] * (H[i] + Fin[i])
    return {"E": Ef + sys_["Enuc"], "Eel": Ef, "eps": fr["e"], "C": fr["C"], "nmo": m, "D": D, "H": H, "F": Fin, "nocc": nocc,
            "log": log, "converged": conv, "iterations": len(log)}


def _rhf_np(sys_, guess, diis, maxit, tol, guessF):
    np = _np
    bs, one, ne = sys_["bs"], sys_["one"], sys_["ne"]
    n = bs["nbf"]
    nocc = ne / 2
    no = math.ceil(nocc)
    S = np.asarray(one["S"])
    H = np.asarray(one["T"]) + np.asarray(one["V"])
    sd = jacobi_np(S, n)
    keep = [i for i, v in enumerate(sd["e"]) if v > 1e-7]
    m = len(keep)
    Vs = np.asarray(sd["V"]).reshape(n, n)
    X = np.zeros((n, m))
    for c, k in enumerate(keep):
        X[:, c] = Vs[:, k] * (1 / math.sqrt(sd["e"][k]))
    X = X.ravel()
    Xt = X.reshape(n, m).T.ravel().copy()
    tabs = _fock_tables(sys_)

    def diag(F):
        Fp = mm_np(mm_np(Xt, F, m, n, n), X, m, n, m)
        r = jacobi_np(Fp, m)
        return {"e": r["e"], "C": mm_np(X, r["V"], n, m, m)}

    def dens(C):
        Cm = C.reshape(n, m)[:, :no]
        return (2 * _seq0(Cm[:, None, :] * Cm[None, :, :], 2)).ravel()

    def gwh():
        d = np.diag(H.reshape(n, n))
        F = 0.875 * S.reshape(n, n) * (d[:, None] + d[None, :])
        F[np.diag_indices(n)] = d
        return F.ravel()

    gF = np.asarray(guessF) if guessF is not None else None
    r = diag(gF if gF is not None else (H if guess == "core" else gwh()))
    D = dens(r["C"])
    E = Eold = 0
    conv = False
    hist, errs, log = [], [], []
    for it in range(1, (maxit or 100) + 1):
        F = _fock_np(H, D, tabs, n)
        E = seq_sum(0.5 * D * (H + F))
        FDS = mm_np(mm_np(F, D, n, n, n), S, n, n, n)
        SDF = FDS.reshape(n, n).T.ravel()
        err = FDS - SDF
        en = float(np.max(np.abs(err))) if err.size else 0
        en = max(0, en)
        log.append({"it": it, "E": E + sys_["Enuc"], "dE": E - Eold, "err": en})
        if it > 1 and abs(E - Eold) < (tol or 1e-10) and en < 1e-7:
            conv = True
            break
        Eold = E
        if diis is not False:
            hist.append(F)
            errs.append(err)
            if len(hist) > 8:
                hist.pop(0)
                errs.pop(0)
            k = len(hist)
            if k >= 2:
                B = [[0] * (k + 1) for _ in range(k + 1)]
                for a in range(k):
                    for b in range(k):
                        B[a][b] = seq_sum(errs[a] * errs[b])
                for a in range(k):
                    B[a][k] = B[k][a] = -1
                rhs = [0] * (k + 1)
                rhs[k] = -1
                c = solve(B, rhs)
                if c:
                    F = _seq0(np.stack([c[a] * hist[a] for a in range(k)]), 0)
        r = diag(F)
        D = dens(r["C"])
    Fin = _fock_np(H, D, tabs, n)
    fr = diag(Fin)
    Ef = seq_sum(0.5 * D * (H + Fin))
    return {"E": Ef + sys_["Enuc"], "Eel": Ef, "eps": fr["e"], "C": fr["C"].tolist(), "nmo": m, "D": D.tolist(), "H": H.tolist(),
            "F": Fin.tolist(), "nocc": nocc, "log": log, "converged": conv, "iterations": len(log)}


# ---------------------------------------------------------------- MP2
def mp2(sys_, res, allow_unconverged=False):
    if res["converged"] is False and not allow_unconverged:
        raise ValueError("MP2: SCF did not converge")
    n = sys_["bs"]["nbf"]
    m = res["nmo"]
    o = int(res["nocc"])
    C = res["C"]
    nv = m - o
    G = sys_["two"]["G"]

    def g(i, j, k, l_):
        return G[_idx2(_idx2(i, j), _idx2(k, l_))]
    half = [0.0] * (o * n * n * n)
    for i in range(o):
        for nu in range(n):
            for la in range(n):
                for si in range(la + 1):
                    s = 0
                    for mu in range(n):
                        s += C[mu * m + i] * g(mu, nu, la, si)
                    half[((i * n + nu) * n + la) * n + si] = half[((i * n + nu) * n + si) * n + la] = s
    iaLS = [0.0] * (o * nv * n * n)
    for i in range(o):
        for a in range(nv):
            for la in range(n):
                for si in range(n):
                    s = 0
                    for nu in range(n):
                        s += C[nu * m + o + a] * half[((i * n + nu) * n + la) * n + si]
                    iaLS[((i * nv + a) * n + la) * n + si] = s
    iaj = [0.0] * (o * nv * o * n)
    for ia in range(o * nv):
        for j in range(o):
            for si in range(n):
                s = 0
                for la in range(n):
                    s += C[la * m + j] * iaLS[(ia * n + la) * n + si]
                iaj[(ia * o + j) * n + si] = s
    K = [0.0] * (o * nv * o * nv)
    for ia in range(o * nv):
        for j in range(o):
            for b in range(nv):
                s = 0
                for si in range(n):
                    s += C[si * m + o + b] * iaj[(ia * o + j) * n + si]
                K[(ia * o + j) * nv + b] = s
    e = res["eps"]
    E = 0
    for i in range(o):
        for a in range(nv):
            for j in range(o):
                for b in range(nv):
                    iajb = K[((i * nv + a) * o + j) * nv + b]
                    ibja = K[((i * nv + b) * o + j) * nv + a]
                    E += iajb * (2 * iajb - ibja) / (e[i] + e[j] - e[o + a] - e[o + b])
    return E


# ---------------------------------------------------------------- properties
def dipole(sys_, res):
    bs = sys_["bs"]
    n = bs["nbf"]
    sh = bs["shells"]
    D = res["D"]
    mu = [0, 0, 0]
    for I in range(len(sh)):
        for J in range(len(sh)):
            A, B = sh[I], sh[J]
            pd = pair_data(A, B)
            for ia, ca in enumerate(A["comps"]):
                for ib, cb in enumerate(B["comps"]):
                    d = D[(A["off"] + ia) * n + B["off"] + ib]
                    if not d:
                        continue
                    for q in pd:
                        w = A["cc"][ia][q["i"]] * B["cc"][ib][q["j"]] * js_pow(PI / q["p"], 1.5)
                        E = q["E"]
                        e0 = [E[k][ca[k]][cb[k]][0] for k in range(3)]
                        for k in range(3):
                            ek = E[k][ca[k]][cb[k]]
                            r1 = (ek[1] if len(ek) > 1 else 0) + q["P"][k] * ek[0]
                            v = w * r1
                            for o in range(3):
                                if o != k:
                                    v *= e0[o]
                            mu[k] -= d * v
    for a in sys_["atoms"]:
        mu[0] += a["Z"] * a["x"]
        mu[1] += a["Z"] * a["y"]
        mu[2] += a["Z"] * a["z"]
    return mu


def esp_prep(sys_, res):
    """Electrostatic potential V(x, y, z) (closure; v1.0 espPrep).  V.many(points) evaluates arrays (numpy)."""
    bs = sys_["bs"]
    sh = bs["shells"]
    n = bs["nbf"]
    D = res["D"]
    items = []
    Lmax = 0
    for I in range(len(sh)):
        for J in range(I + 1):
            A, B = sh[I], sh[J]
            L = A["l"] + B["l"]
            Dm = L + 1
            herm = [(t, u, v) for t in range(L + 1) for u in range(L - t + 1) for v in range(L - t - u + 1)]
            idx = [(t * Dm + u) * Dm + v for t, u, v in herm]
            for q in pair_data(A, B):
                Dv = [0.0] * len(herm)
                mx = 0
                for ia, ca in enumerate(A["comps"]):
                    for ib, cb in enumerate(B["comps"]):
                        mu_, nu = A["off"] + ia, B["off"] + ib
                        d = D[mu_ * n + nu] * (1 if I == J else 2)
                        if not d:
                            continue
                        w = d * A["cc"][ia][q["i"]] * B["cc"][ib][q["j"]]
                        Ex, Ey, Ez = q["E"][0][ca[0]][cb[0]], q["E"][1][ca[1]][cb[1]], q["E"][2][ca[2]][cb[2]]
                        for h, (t, u, v) in enumerate(herm):
                            if t < len(Ex) and u < len(Ey) and v < len(Ez):
                                Dv[h] += w * Ex[t] * Ey[u] * Ez[v]
                for x in Dv:
                    mx = max(mx, abs(x))
                if mx < 1e-11:
                    continue
                items.append({"p": q["p"], "P": q["P"], "L": L, "idx": idx, "Dv": Dv, "herm": herm, "f": 2 * PI / q["p"]})
                if L > Lmax:
                    Lmax = L
    Dm = Lmax + 1
    R = [0.0] * (Dm * Dm * Dm)
    W = [0.0] * ((Lmax + 1) * Dm * Dm * Dm)
    at = [a for a in sys_["atoms"] if a["Z"] > 0]

    def V(x, y, z):
        vn = 0
        for a in at:
            d = js_hypot(x - a["x"], y - a["y"], z - a["z"])
            vn += a["Z"] / d if d else math.inf  # JS: Z/0 = Infinity
        ve = 0
        for it in items:
            rflat(it["L"], it["p"], [it["P"][0] - x, it["P"][1] - y, it["P"][2] - z], R, W)
            s = 0
            Dv = it["Dv"]
            idx = it["idx"]
            for h in range(len(Dv)):
                s += Dv[h] * R[idx[h]]
            ve += it["f"] * s
        return vn - ve

    def many(pts):
        """V at an (m, 3) array of points: bound tier (numpy order of summation)."""
        np = _np
        P = np.asarray(pts, dtype=float).reshape(-1, 3)
        out = np.zeros(P.shape[0])
        for a in at:
            out += a["Z"] / np.sqrt((P[:, 0] - a["x"]) ** 2 + (P[:, 1] - a["y"]) ** 2 + (P[:, 2] - a["z"]) ** 2)
        groups: dict = {}
        for it in items:
            groups.setdefault(it["L"], []).append(it)
        for L, its in groups.items():
            herm = its[0]["herm"]
            hh = np.array(herm, dtype=int).reshape(-1, 3)
            for it in its:
                PQ = np.asarray(it["P"])[None, :] - P
                Rv = _rflat_np(L, np.full(P.shape[0], it["p"]), PQ)
                vals = Rv[:, hh[:, 0], hh[:, 1], hh[:, 2]] @ np.asarray(it["Dv"])
                out -= it["f"] * vals
        return out

    def many_exact(pts):
        """V at an (m, 3) array of points, bitwise equal to V point by point
        (same sums in the same order; _rflat_np is the elementwise rflat)."""
        np = _np
        from .jsmath_np import hypot3_np
        P = np.asarray(pts, dtype=float).reshape(-1, 3)
        m = P.shape[0]
        vn = np.zeros(m)
        for a in at:
            vn = vn + a["Z"] / hypot3_np(P[:, 0] - a["x"], P[:, 1] - a["y"], P[:, 2] - a["z"])
        ve = np.zeros(m)
        for it in items:
            L = it["L"]
            PQ = np.asarray(it["P"])[None, :] - P
            Rv = _rflat_np(L, np.full(m, it["p"]), PQ).reshape(m, -1)
            s = np.zeros(m)
            Dv = it["Dv"]
            for h, ix in enumerate(it["idx"]):
                s = s + Dv[h] * Rv[:, ix]
            ve = ve + it["f"] * s
        return vn - ve

    V.many = many
    V.many_exact = many_exact
    return V


# ---------------------------------------------------------------- values of basis functions, density
def bf_eval(bs, x, y, z, deriv=0):
    n = bs["nbf"]
    val = [0.0] * n
    gx = [0.0] * n if deriv else None
    gy = [0.0] * n if deriv else None
    gz = [0.0] * n if deriv else None
    H = [[0.0] * n for _ in range(6)] if deriv and deriv >= 2 else None
    for s in bs["shells"]:
        dx, dy, dz = x - s["O"][0], y - s["O"][1], z - s["O"][2]
        r2 = dx * dx + dy * dy + dz * dz
        ex = [exp(-a * r2) for a in s["e"]]
        for k, c in enumerate(s["comps"]):
            f0 = f1 = f2 = 0
            cck = s["cc"][k]
            for i, a in enumerate(s["e"]):
                w = cck[i] * ex[i]
                f0 += w
                f1 += w * a
                f2 += w * a * a

            def pw(d, l_):
                return 1 if l_ == 0 else (d if l_ == 1 else d * d)
            X, Y, Z = pw(dx, c[0]), pw(dy, c[1]), pw(dz, c[2])
            mu = s["off"] + k
            val[mu] = X * Y * Z * f0
            if not deriv:
                continue

            def d1(d, l_):
                return 0 if l_ == 0 else (1 if l_ == 1 else 2 * d)
            DX, DY, DZ = d1(dx, c[0]), d1(dy, c[1]), d1(dz, c[2])
            gx[mu] = DX * Y * Z * f0 - 2 * dx * X * Y * Z * f1
            gy[mu] = X * DY * Z * f0 - 2 * dy * X * Y * Z * f1
            gz[mu] = X * Y * DZ * f0 - 2 * dz * X * Y * Z * f1
            if H:
                P = [X, Y, Z]
                Dp = [DX, DY, DZ]
                D2 = [2 if l_ == 2 else 0 for l_ in c]
                dd = [dx, dy, dz]
                q = 0
                for i in range(3):
                    for j in range(i, 3):
                        oth = [t for t in (0, 1, 2) if t != i and t != j]
                        o_ = 1
                        for t in oth:
                            o_ = o_ * P[t]
                        if i == j:
                            val2 = o_ * (D2[i] * f0 - 2 * Dp[i] * dd[i] * f1 * 2 + P[i] * (-2 * f1 + 4 * dd[i] * dd[i] * f2))
                        else:
                            val2 = o_ * (Dp[i] * Dp[j] * f0 - 2 * (Dp[i] * P[j] * dd[j] + P[i] * Dp[j] * dd[i]) * f1 + 4 * P[i] * P[j] * dd[i] * dd[j] * f2)
                        H[q][mu] = val2
                        q += 1
    return {"val": val, "gx": gx, "gy": gy, "gz": gz, "H": H}


def rho_at(bs, D, x, y, z, deriv=0):
    n = bs["nbf"]
    b = bf_eval(bs, x, y, z, deriv)
    r = 0
    g = [0, 0, 0]
    h = [0, 0, 0, 0, 0, 0] if deriv and deriv >= 2 else None
    val, bgx, bgy, bgz = b["val"], b["gx"], b["gy"], b["gz"]
    for i in range(n):
        bi = val[i]
        s = sx = sy = sz = 0
        Di = i * n
        for j in range(n):
            d = D[Di + j]
            if not d:
                continue
            s += d * val[j]
            if deriv:
                sx += d * bgx[j]
                sy += d * bgy[j]
                sz += d * bgz[j]
        r += bi * s
        if deriv:
            g[0] += 2 * bgx[i] * s
            g[1] += 2 * bgy[i] * s
            g[2] += 2 * bgz[i] * s
            if h:
                gi = [bgx[i], bgy[i], bgz[i]]
                sj = [sx, sy, sz]
                q = 0
                for a in range(3):
                    for c in range(a, 3):
                        h[q] += 2 * (b["H"][q][i] * s + gi[a] * sj[c])
                        q += 1
    G = 0
    if deriv:
        for i in range(n):
            for j in range(n):
                d = D[i * n + j]
                if d:
                    G += d * (bgx[i] * bgx[j] + bgy[i] * bgy[j] + bgz[i] * bgz[j])
    return {"rho": r, "g": g, "h": h, "G": 0.5 * G}


# ------------------------------------------------- numpy batch over points (bitwise)
def bf_eval_np(bs, x, y, z, deriv=0):
    """bf_eval at arrays of points x, y, z: the same expressions with array
    operands (elementwise IEEE operations, same order) and the vectorised fdlibm
    exp, hence bitwise equal to bf_eval point by point."""
    from .jsmath_np import exp_np
    n = bs["nbf"]
    val = [None] * n
    gx = [None] * n if deriv else None
    gy = [None] * n if deriv else None
    gz = [None] * n if deriv else None
    H = [[None] * n for _ in range(6)] if deriv and deriv >= 2 else None
    np = _np
    geo, args = [], []
    for s in bs["shells"]:
        dx, dy, dz = x - s["O"][0], y - s["O"][1], z - s["O"][2]
        r2 = dx * dx + dy * dy + dz * dz
        geo.append((dx, dy, dz))
        args.extend(-a * r2 for a in s["e"])
    m = np.shape(args[0])
    if args:  # one vectorised exp for every primitive (elementwise); exp(x) = +0 exactly for x < -746
        st_ = np.stack(args)
        allex = np.zeros(st_.shape)
        sel = st_ > -746.0
        if sel.any():
            allex[sel] = exp_np(st_[sel])
    pos = 0
    for s, (dx, dy, dz) in zip(bs["shells"], geo):
        ex = [allex[pos + i].reshape(m) for i in range(len(s["e"]))]
        pos += len(s["e"])
        for k, c in enumerate(s["comps"]):
            f0 = f1 = f2 = 0
            cck = s["cc"][k]
            for i, a in enumerate(s["e"]):
                w = cck[i] * ex[i]
                f0 = f0 + w
                f1 = f1 + w * a
                f2 = f2 + w * a * a

            def pw(d, l_):
                return 1 if l_ == 0 else (d if l_ == 1 else d * d)
            X, Y, Z = pw(dx, c[0]), pw(dy, c[1]), pw(dz, c[2])
            mu = s["off"] + k
            val[mu] = X * Y * Z * f0
            if not deriv:
                continue

            def d1(d, l_):
                return 0 if l_ == 0 else (1 if l_ == 1 else 2 * d)
            DX, DY, DZ = d1(dx, c[0]), d1(dy, c[1]), d1(dz, c[2])
            gx[mu] = DX * Y * Z * f0 - 2 * dx * X * Y * Z * f1
            gy[mu] = X * DY * Z * f0 - 2 * dy * X * Y * Z * f1
            gz[mu] = X * Y * DZ * f0 - 2 * dz * X * Y * Z * f1
            if H:
                P = [X, Y, Z]
                Dp = [DX, DY, DZ]
                D2 = [2 if l_ == 2 else 0 for l_ in c]
                dd = [dx, dy, dz]
                q = 0
                for i in range(3):
                    for j in range(i, 3):
                        oth = [t for t in (0, 1, 2) if t != i and t != j]
                        o_ = 1
                        for t in oth:
                            o_ = o_ * P[t]
                        if i == j:
                            val2 = o_ * (D2[i] * f0 - 2 * Dp[i] * dd[i] * f1 * 2 + P[i] * (-2 * f1 + 4 * dd[i] * dd[i] * f2))
                        else:
                            val2 = o_ * (Dp[i] * Dp[j] * f0 - 2 * (Dp[i] * P[j] * dd[j] + P[i] * Dp[j] * dd[i]) * f1 + 4 * P[i] * P[j] * dd[i] * dd[j] * f2)
                        H[q][mu] = val2
                        q += 1
    return {"val": val, "gx": gx, "gy": gy, "gz": gz, "H": H}


def rho_at_np(bs, D, x, y, z, deriv=0, kin=False):
    """rho_at at arrays of points (bitwise, see bf_eval_np); the kinetic term G only if kin."""
    n = bs["nbf"]
    b = bf_eval_np(bs, x, y, z, deriv)
    r = 0
    g = [0, 0, 0]
    h = [0, 0, 0, 0, 0, 0] if deriv and deriv >= 2 else None
    val, bgx, bgy, bgz = b["val"], b["gx"], b["gy"], b["gz"]
    for i in range(n):
        bi = val[i]
        s = sx = sy = sz = 0
        Di = i * n
        for j in range(n):
            d = D[Di + j]
            if not d:
                continue
            s = s + d * val[j]
            if deriv:
                sx = sx + d * bgx[j]
                sy = sy + d * bgy[j]
                sz = sz + d * bgz[j]
        r = r + bi * s
        if deriv:
            g[0] = g[0] + 2 * bgx[i] * s
            g[1] = g[1] + 2 * bgy[i] * s
            g[2] = g[2] + 2 * bgz[i] * s
            if h:
                gi = [bgx[i], bgy[i], bgz[i]]
                sj = [sx, sy, sz]
                q = 0
                for a in range(3):
                    for c in range(a, 3):
                        h[q] = h[q] + 2 * (b["H"][q][i] * s + gi[a] * sj[c])
                        q += 1
    out = {"rho": r, "g": g, "h": h}
    if kin and deriv:
        G = 0
        for i in range(n):
            for j in range(n):
                d = D[i * n + j]
                if d:
                    G = G + d * (bgx[i] * bgx[j] + bgy[i] * bgy[j] + bgz[i] * bgz[j])
        out["G"] = 0.5 * G
    return out

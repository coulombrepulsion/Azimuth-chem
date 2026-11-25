"""Density functionals on model one- and two-electron systems: self-interaction of the H atom,
E(N) at fractional electron number, and the delocalisation error of H2+.

HEADER
    Model of the page "Метод функционала плотности" (v1.0 dft.js: CX, G,
    ecPW92, exB88s, exPBEs, rho1, radGrid, atomXC, atomE, golden, atomOpt,
    atomFunc, gaussLeg, beckeW, h2grid, h2comp, h2table, h2E, h2min and the
    precomputed array DATA; page code sec1, sec2, sec3). Wilkinson
    convention, sections 1-8. Atomic units (E_h, bohr).

§1 THEORY
    Spin densities rho_a, rho_b. LSDA exchange
      E_x = -C_x sum_s int rho_s^(4/3), C_x = (3/2)(3/(4 pi))^(1/3);
    the spin-unpolarised LDA uses rho_a = rho_b = rho/2. B88 exchange per
    spin: -C_x rho^(4/3) - b rho^(4/3) x^2 / (1 + 6 b x asinh x), x =
    |grad rho|/rho^(4/3), b = 0.0042. PBE exchange by spin scaling,
    E_x[rho_s] = E_x^unpol[2 rho_s]/2, with F(s) = 1 + kappa - kappa/(1 +
    mu s^2/kappa), kappa = 0.804, mu = 0.2195149727645171, s = |grad n|/(2
    k_F n), k_F = (3 pi^2 n)^(1/3). Correlation PW92: eps_c(r_s, zeta) =
    e0 + alpha_c f(zeta)/f''(0) (1 - zeta^4) + (e1 - e0) f(zeta) zeta^4,
    G(r_s) = -2A(1 + a1 r_s) ln(1 + 1/(2A(b1 r_s^(1/2) + b2 r_s + b3
    r_s^(3/2) + b4 r_s^2))) with the PW92 parameter sets (paramagnetic,
    ferromagnetic, -alpha_c), f''(0) = 1.709921.
    Model densities: a Slater 1s with exponent zeta, rho_1 = zeta^3/pi
    e^(-2 zeta r), |grad rho_1| = 2 zeta rho_1; for one electron T =
    zeta^2/2, V = -zeta, J = 5 zeta/16. An exact one-electron functional
    must give E_x = -J, E_c = 0 (no self-interaction). For N electrons in
    the 1s (alpha filled first, n_a = min(N, 1), n_b = max(N - 1, 0)) and
    a fraction a of exact exchange: E = N(zeta^2/2 - zeta) + N^2 J_1 + a K
    + (1 - a) E_x^LSDA + E_c^LSDA, K = -(n_a^2 + n_b^2) J_1, J_1 = 5zeta/16;
    zeta optimised for each N. The exact E(N) is piecewise linear between
    -1/2 (H) and -1/2 - 0.0277 (H-, EA = 0.0277 E_h).
    H2+ in STO-3G (one 1s on each proton, scaled by zeta): delocalised
    sigma_g c = (1, 1)/sqrt(2(1 + S)) or localised c = (1, 0); energy
    h + V_nn + (1 - a)(J + E_x^LSDA[rho]) + E_c^LSDA[rho], rho fully spin
    polarised (one alpha electron); exact (HF) = h + V_nn. Integrals from
    core.sto3g; exchange-correlation integrals on a two-centre Becke grid
    (Becke weights with three iterations of p(m) = 1.5 m - 0.5 m^3). The
    energy is minimised over zeta in [0.8, 1.7] (step 0.02) with a
    parabolic refinement.

§2 ALGORITHM
    Radial quadrature: Gauss-Chebyshev of the second kind, n points, x_i =
    cos(i pi/(n+1)), Becke's mapping r = r_m (1 + x)/(1 - x), weight w_i
    = pi/(n+1) sin^2(...)/sqrt(1 - x^2) dr/dx 4 pi r^2 (n = 120 for the
    atom, 60 per centre for H2+, r_m = 1); angular: Gauss-Legendre with
    36 points in cos(theta) (Newton iteration, |dz| < 1e-15), the
    azimuth integrated analytically (cylindrical symmetry). Golden-section
    search (ratio 1.618034, 60 or 50 steps). All sums in v1.0 order.
    The arrays of DATA (E(N) for 21 fractions a and 81 values of N; H2+
    curves on 95 distances) were precomputed by the author with the same
    functions and rounded to 5 decimals; precompute_* reproduce them.

§3 APPLICATIONS
    Endpoints dft.meta, dft.sie, dft.en, dft.h2.

§4 SPECIFICATION
    sie() -> {rows: [{x, c, T, V, J, Ex, Ec, E, Eo, zo, s}], pct, sie, sieKJ}
      (rows in the order HF, LDA, LSDA, B88+LSDA, PBE+LSDA).
    en(ai) -> E(N) curves for a = DATA.A[ai] with slopes and deviations.
    h2(ai, ri) -> H2+ curves for a = DATA.A[ai] and the values at R = RR[ri].
    precompute_en(a), precompute_h2(R, a) -> the unrounded values.
    Tier: bitwise vs v1.0 on Linux/glibc (EXACT) for sie/en/h2; pow is
    the platform pow (glibc on Linux, as in V8); sin/cos/exp/log/cbrt/asinh
    are the V8 ports of core.jsmath.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    x**2 -> sq(x); Math.pow -> js_pow; unary minus binds before * as in
    JS (-C*x = (-C)*x, the same double as -(C*x)).
§7 TEST CASES (tests/test_dft.py)
    Independent oracles: C_x = 0.7386; LSDA exchange of the hydrogen 1s
    density in closed form, E_x = -C_x 2^(1/3) ... = -0.2680 (int rho^(4/3)
    = 27/(128 pi^(1/3)) zeta for rho_1, value 0.26806 at zeta = 1, Parr &
    Yang); spin-unpolarised exchange = 2^(-1/3) LSDA; J = 5/16; HF has no
    self-interaction; radial grid integrates rho_1 to 1 (1e-10);
    Gauss-Legendre nodes/weights exact for polynomials of degree 71; Becke
    weights sum to 1; PW92 at r_s = 1, zeta = 0 equals -0.0598 (Perdew &
    Wang 1992 table); exact E(N) piecewise linear; DATA reproduced by
    precompute_* to the printed 5 decimals; vs v1.0 bitwise.
§8 ERROR ANALYSIS
    Quadrature: 120 radial points integrate the 1s densities to < 1e-10
    relative; the H2+ grid (2 x 60 x 36) to ~1e-6, comparable to the 5
    decimals of DATA. Golden section to (1.6)^-60 ~ 5e-13 in zeta, energy
    error second order. The model (minimal basis, one exponent) is the
    dominant error: the page draws qualitative conclusions only.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from . import sto3g
from .jsmath import asinh, cbrt, cos, exp, js_hypot, js_pow, log, sin, sq

PI = math.pi
KJ = 2625.5
DATA = json.loads((Path(__file__).parent / "data" / "dft.json").read_text(encoding="utf-8"))
F43 = 4 / 3
CX = 1.5 * cbrt(3 / (4 * PI))
FPP = 1.709921


def G(rs, A, a1, b1, b2, b3, b4):
    s = math.sqrt(rs)
    return -2 * A * (1 + a1 * rs) * log(1 + 1 / (2 * A * (b1 * s + b2 * rs + b3 * rs * s + b4 * rs * rs)))


def ec_pw92(ra, rb):
    n = ra + rb
    if n < 1e-14:
        return 0
    rs = cbrt(3 / (4 * PI * n))
    z = max(-1, min(1, (ra - rb) / n))
    e0 = G(rs, 0.031091, 0.21370, 7.5957, 3.5876, 1.6382, 0.49294)
    e1 = G(rs, 0.015545, 0.20548, 14.1189, 6.1977, 3.3662, 0.62517)
    ac = -G(rs, 0.016887, 0.11125, 10.357, 3.6231, 0.88026, 0.49671)
    f = (js_pow(1 + z, F43) + js_pow(1 - z, F43) - 2) / (js_pow(2, F43) - 2)
    z4 = z * z * z * z
    return e0 + ac * f / FPP * (1 - z4) + (e1 - e0) * f * z4


def ex_b88s(r, g):
    if r < 1e-14:
        return 0
    r43 = js_pow(r, F43)
    x = g / r43
    b = 0.0042
    return -CX * r43 - b * r43 * x * x / (1 + 6 * b * x * asinh(x))


def ex_pbes(r, g):
    if r < 1e-14:
        return 0
    n = 2 * r
    gn = 2 * g
    kf = cbrt(3 * PI * PI * n)
    s = gn / (2 * kf * n)
    k = 0.804
    mu = 0.2195149727645171
    ex = -0.75 * cbrt(3 / PI) * js_pow(n, F43) * (1 + k - k / (1 + mu * s * s / k))
    return ex / 2


def rho1(r, z):
    return z * z * z / PI * exp(-2 * z * r)


def rad_grid(n, rm):
    P = []
    for i in range(1, n + 1):
        x = cos(i * PI / (n + 1))
        w0 = PI / (n + 1) * sq(sin(i * PI / (n + 1))) / math.sqrt(1 - x * x)
        r = rm * (1 + x) / (1 - x)
        dr = rm * 2 / sq(1 - x)
        P.append((r, w0 * dr * r * r * 4 * PI))
    return P


RG = rad_grid(120, 1)


def atom_xc(z, na, nb, kind):
    s = 0
    for r, w in RG:
        p = rho1(r, z)
        ra = na * p
        rb = nb * p
        ga = 2 * z * ra
        gb = 2 * z * rb
        e = 0
        if kind == "xlsda":
            e = -CX * (js_pow(ra, F43) + js_pow(rb, F43))
        elif kind == "xb88":
            e = ex_b88s(ra, ga) + ex_b88s(rb, gb)
        elif kind == "xpbe":
            e = ex_pbes(ra, ga) + ex_pbes(rb, gb)
        elif kind == "clsda":
            e = (ra + rb) * ec_pw92(ra, rb)
        elif kind == "xlda":
            e = -CX * 2 * js_pow((ra + rb) / 2, F43)
        elif kind == "clda":
            e = (ra + rb) * ec_pw92((ra + rb) / 2, (ra + rb) / 2)
        s += w * e
    return s


def atom_e(N, z, a, mode):
    na = min(N, 1)
    nb = max(N - 1, 0)
    J1 = 5 * z / 16
    one = N * (z * z / 2 - z)
    J = N * N * J1
    K = -(na * na + nb * nb) * J1
    if mode == "hf":
        return one + J + K
    xl = atom_xc(z, na, nb, "xlsda")
    c = atom_xc(z, na, nb, "clsda")
    return one + J + a * K + (1 - a) * xl + c


def golden(f, a, b, it=60):
    x1 = b - (b - a) / 1.618034
    x2 = a + (b - a) / 1.618034
    f1 = f(x1)
    f2 = f(x2)
    for _k in range(it):
        if f1 < f2:
            b = x2
            x2 = x1
            f2 = f1
            x1 = b - (b - a) / 1.618034
            f1 = f(x1)
        else:
            a = x1
            x1 = x2
            f1 = f2
            x2 = a + (b - a) / 1.618034
            f2 = f(x2)
    x = (a + b) / 2
    return {"x": x, "f": f(x)}


def atom_opt(N, a, mode):
    if N < 1e-9:
        return {"x": 1, "f": 0}
    return golden(lambda z: atom_e(N, z, a, mode), 0.3, 2.5, 50)


def atom_func(z, x, c):
    J = 5 * z / 16
    Ex = -J if x == "hf" else atom_xc(z, 1, 0, x)
    Ec = atom_xc(z, 1, 0, c) if c else 0
    return {"T": z * z / 2, "V": -z, "J": J, "Ex": Ex, "Ec": Ec, "E": z * z / 2 - z + J + Ex + Ec}


# ---------------------------------------------------------------- H2+ on a Becke grid
def gauss_leg(n):
    xs, ws = [], []
    for i in range(1, n + 1):
        z = cos(PI * (i - 0.25) / (n + 0.5))
        pp = 0
        for _it in range(100):
            p1 = 1
            p2 = 0
            for j in range(1, n + 1):
                p3 = p2
                p2 = p1
                p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j
            pp = n * (z * p1 - p2) / (z * z - 1)
            z1 = z
            z = z1 - p1 / pp
            if abs(z - z1) < 1e-15:
                break
        xs.append(z)
        ws.append(2 / ((1 - z * z) * pp * pp))
    return {"x": xs, "w": ws}


GL = gauss_leg(36)
RG2 = rad_grid(60, 1)


def becke_w(rA, rB, R):
    m = (rA - rB) / R
    for _k in range(3):
        m = 1.5 * m - 0.5 * m * m * m
    return 0.5 * (1 - m)


def h2grid(R):
    P = []
    for ia, c in enumerate((0, R)):
        for r, wr in RG2:
            for k in range(len(GL["x"])):
                ct = GL["x"][k]
                st = math.sqrt(1 - ct * ct)
                z = c + r * ct
                x = r * st
                rA = js_hypot(x, z)
                rB = js_hypot(x, z - R)
                wA = becke_w(rA, rB, R)
                wB = 1 - wA
                w = wr / (4 * PI) * 2 * PI * GL["w"][k] * (wA if ia == 0 else wB)
                P.append((x, z, w))
    return P


def h2comp(R, z, grid):
    I = sto3g.integrals([{"Z": 1, "zeta": z, "z": 0}, {"Z": 1, "zeta": z, "z": R}])
    S = I["S"][0][1]
    cg = [1 / math.sqrt(2 * (1 + S)), 1 / math.sqrt(2 * (1 + S))]
    cl = [1, 0]
    H = I["H"]

    def one(c):
        return c[0] * c[0] * H[0][0] + 2 * c[0] * c[1] * H[0][1] + c[1] * c[1] * H[1][1]

    def two(c):
        s = 0
        for i in range(2):
            for j in range(2):
                for k in range(2):
                    for l in range(2):
                        s += c[i] * c[j] * c[k] * c[l] * I["ERI"][i][j][k][l]
        return s / 2

    xg = eg = xl = el = 0
    for x, zz, w in grid:
        a = 0
        b = 0
        for p in I["B"][0]:
            a += p["d"] * exp(-p["a"] * (x * x + zz * zz))
        for p in I["B"][1]:
            b += p["d"] * exp(-p["a"] * (x * x + sq(zz - R)))
        rg = sq(cg[0] * a + cg[1] * b)
        rl = a * a
        xg += w * (-CX * js_pow(rg, F43))
        eg += w * rg * ec_pw92(rg, 0)
        xl += w * (-CX * js_pow(rl, F43))
        el += w * rl * ec_pw92(rl, 0)
    return {"hg": one(cg) + I["Vnn"], "Jg": two(cg), "Xg": xg, "Cg": eg, "hl": one(cl) + I["Vnn"], "Jl": two(cl), "Xl": xl, "Cl": el}


ZS = [0.8 + i * 0.02 for i in range(46)]


def h2table(R):
    g = h2grid(R)
    return [h2comp(R, z, g) for z in ZS]


def h2e(c, a, loc):
    if loc:
        return c["hl"] + (1 - a) * (c["Jl"] + c["Xl"]) + c["Cl"]
    return c["hg"] + (1 - a) * (c["Jg"] + c["Xg"]) + c["Cg"]


def h2min(tab, a, loc, hf):
    def f(c):
        return (c["hl"] if loc else c["hg"]) if hf else h2e(c, a, loc)
    k = 0
    best = math.inf
    for i, c in enumerate(tab):
        v = f(c)
        if v < best:
            best = v
            k = i
    if 0 < k < len(tab) - 1:
        y0, y1, y2 = f(tab[k - 1]), best, f(tab[k + 1])
        d = y0 - 2 * y1 + y2
        if d > 0:
            t = 0.5 * (y0 - y2) / d
            return {"E": y1 - 0.25 * (y0 - y2) * t, "z": ZS[k] + t * 0.02}
    return {"E": best, "z": ZS[k]}


def precompute_en(a):
    """E(N) for the fraction a of exact exchange on DATA.NN (unrounded; DATA.EN holds 5 decimals)."""
    return [atom_opt(N, a, "dft")["f"] for N in DATA["NN"]]


def precompute_h2(R, a):
    """H2+ energies at R: (exact = HF sigma_g, functional sigma_g, functional localised)."""
    tab = h2table(R)
    return h2min(tab, a, False, True)["E"], h2min(tab, a, False, False)["E"], h2min(tab, a, True, False)["E"]


# ---------------------------------------------------------------- page sections
FUNCS = [("hf", None), ("xlda", "clda"), ("xlsda", "clsda"), ("xb88", "clsda"), ("xpbe", "clsda")]


def sie() -> dict:
    rows = []
    for x, c in FUNCS:
        r = atom_func(1, x, c)
        o = golden(lambda z: atom_func(z, x, c)["E"], 0.5, 1.6, 60)
        rows.append({"x": x, "c": c, **r, "Eo": o["f"], "zo": o["x"], "s": r["J"] + r["Ex"] + r["Ec"]})
    ls = rows[2]
    s = ls["J"] + ls["Ex"] + ls["Ec"]
    return {"rows": rows, "pct": (ls["Ex"] + 0.3125) * 100 / 0.3125, "sie": s, "sieKJ": s * KJ}


def exact_e(N):
    return -0.5 * N if N <= 1 else -0.5 - 0.0277 * (N - 1)


def _lin(arr, N):
    NN = DATA["NN"]
    i0 = NN.index(0 if N <= 1 else 1)
    i1 = NN.index(1 if N <= 1 else 2)
    t = N if N <= 1 else N - 1
    return arr[i0] + (arr[i1] - arr[i0]) * t


def meta() -> dict:
    return {"A": DATA["A"], "ri0": DATA["RR"].index(2), "nR": len(DATA["RR"])}


def en(ai: int) -> dict:
    a = DATA["A"][ai]
    E = DATA["EN"][ai]
    H = DATA["ENhf"]
    NN = DATA["NN"]
    i1 = NN.index(1)
    sL = (E[i1] - E[i1 - 1]) / 0.025
    sR = (E[i1 + 1] - E[i1]) / 0.025
    i5 = NN.index(0.5)
    tan = [[[u, E[i1] + s * (u - 1)], [v, E[i1] + s * (v - 1)]] for s, u, v in ((sL, 0.55, 1), (sR, 1, 1.45))]
    return {"a": a, "NN": NN, "E": E, "H": H, "exact": [exact_e(N) for N in NN], "ex012": [exact_e(N) for N in (0, 1, 2)],
            "devH": [H[i] - _lin(H, N) for i, N in enumerate(NN)], "devE": [E[i] - _lin(E, N) for i, N in enumerate(NN)],
            "tan": tan, "sL": sL, "sR": sR, "I": -E[i1], "gap": sR - sL, "half": E[i5] - E[i1] / 2}


def h2(ai: int, ri: int) -> dict:
    a = DATA["A"][ai]
    RR = DATA["RR"]
    hf = DATA["H2"]["hf"]
    d = DATA["H2"]["d"][ai]
    l_ = DATA["H2"]["l"][ai]
    iF = len(RR) - 1
    return {"a": a, "RR": RR, "hf": hf, "d": d, "l": l_, "R": RR[ri], "hfR": hf[ri], "dR": d[ri], "lR": l_[ri],
            "dkj": (d[ri] - hf[ri]) * KJ, "dF": d[iF], "lF": l_[iF], "hfF": hf[iF], "errF": (hf[iF] - d[iF]) * KJ}

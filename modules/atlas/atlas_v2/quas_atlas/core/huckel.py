"""Simple Hueckel method for planar pi systems: orbitals, charges, bond orders, free valence,
delocalisation energy, reactivity indices, and the Woodward-Hoffmann analysis built on it.

HEADER
    Model of the pages "Метод Хюккеля" (v1.0 huckel.js: HT, bondK, jacobi,
    maxMatching, solve, reactivity, polyFromRoots) and "π-орбитали и
    перициклические реакции" (v1.0 wh.js: the same solver plus electro,
    symOf, correl and the frontier-orbital analysis of section 3).
    Wilkinson convention, sections 1-8.  Energies in units of beta
    (E = alpha + x beta, beta < 0, so larger x is lower in energy).

§1 THEORY
    One p orbital per atom r; Coulomb integral alpha_r = alpha + h_r beta,
    resonance integral beta_rs = k_rs beta for bonded neighbours, zero
    otherwise, overlap neglected (Streitwieser parameters: C h 0 k 1;
    pyridine-type N 0.5/1, 1 pi electron; pyrrole-type N 1.5/0.8, 2;
    carbonyl O 1.0/1, 1; furan-type O 2.0/0.8, 2; k between two
    heteroatoms is the product).  Dividing the secular problem by beta
    leaves the real symmetric matrix A (A_rr = h_r, A_rs = k_rs) whose
    eigenvalues are the x of E = alpha + x beta.  Degenerate levels form a
    shell; electrons fill shells from the largest x (Aufbau), a partly
    filled shell shares its electrons equally between its orbitals.  With
    occupations n_i: bond order p_rs = sum n_i c_ri c_si, pi density P_rr,
    charge q_r = z_r - P_rr, free valence F_r = sqrt(3) - sum_s p_rs (only
    for C), E_pi = n alpha + B beta with B = sum n_i x_i.  Delocalisation
    energy (all-carbon systems only) DE = B - 2 m, m = min(maximum
    matching of the bond graph, floor(n_e/2)) isolated C=C bonds.
    Frontier densities f_r = mean over the HOMO (LUMO) shell of c_r^2.
    Reactivity: substitutable atoms are C with at most two pi neighbours;
    electrophile/nucleophile sites by the most negative/positive q (charge
    control) or largest HOMO/LUMO density (orbital control), radical
    sites by the largest F; ties within 1e-3.  The characteristic
    polynomial is prod (x - x_i), i.e. det(A - x) up to the sign
    convention of the page.
    Woodward-Hoffmann: for an electrocyclic ring closure of an open chain
    of n atoms with n_e pi electrons the frontier orbital is the HOMO
    (index n_e/2 - 1) or, photochemically, the next one; the closure is
    conrotatory if c_1 c_n < 0, disrotatory if > 0.  Orbital symmetry
    under the mirror (disrotation) or the C2 axis (conrotation) is the
    sign of s = sum_k c_k c_(n+1-k) (mirror: S if s > 0; C2: S if s < 0).
    The correlation diagram links reactant and product orbitals of equal
    symmetry in order of energy (product: sigma at x = 2.6, the pi
    orbitals of the (n-2)-chain, sigma* at x = -2.6).  For a supra-supra
    cycloaddition the selected frontier pair overlaps in phase at an end
    if -c_A c_B > 0 there (the drawing places B's lobes facing A's);
    allowed if both ends are in phase after an overall sign change of B.

§2 ALGORITHM
    As v1.0: cyclic Jacobi (at most 100 sweeps, stop when the
    off-diagonal sum of squares < 1e-22, skip |A_pq| < 1e-15); stable sort
    by decreasing x; sign convention: the first coefficient with |c| >
    1e-6 is positive; degenerate shells (|dx| < 1e-6) are given the
    "standard" basis obtained by Gram-Schmidt on the projections of the
    atomic orbitals 1, 2, ... onto the shell (norm > 1e-6 kept);
    maximum matching by exhaustive search.  Every sum is accumulated in
    the v1.0 order.

§3 APPLICATIONS
    Endpoints huckel.solve (page huckel) and wh.hk, wh.electro, wh.correl,
    wh.cyclo (page wh).

§4 SPECIFICATION
    solve(types, bonds, charge) -> {n, A, mos: [{x, c, occ, shell}],
      shells: [{x, mo, ne}], ne, P, q, bo, F (None for non-C), B, homo,
      lumo (shell indices, -1 if none), fH, fL (None if no such shell),
      DE, m (None unless all C), allC, deg, ring, unpaired}.
      types: list of keys of HT; bonds: list of [i, j], 0 <= i, j < n.
    reactivity(types, R, mode in q/fo) -> None | {cand, polar, E, N, R}.
    poly_from_roots(roots) -> coefficients of prod (x + r) (v1.0
      convention: d[i+1] += v a).
    electro(n, ne, photo), correl(n, ne, mode), cyclo(A, B, photo2, pair)
      -> see the functions.
    Tier: bitwise vs v1.0 on Linux/glibc (EXACT); only + - * / and sqrt,
    and js_hypot, whose glibc path is the one V8 uses.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Math.sign(th || 1) -> 1 for th = 0 or NaN, else js_sign(th).
    c**2 -> sq(c).  Integer zeros are kept where v1.0 starts sums from 0;
    adding a float to the integer 0 gives the same double as in JS (the
    sign of an exact zero sum is +0 in both).
§7 TEST CASES (tests/test_huckel.py, tests/test_wh.py)
    Independent oracles: ethylene x = +-1; butadiene x = +-1.618, +-0.618
    (2 cos(k pi/5)); benzene levels 2 cos(2 pi k/6) and DE = 2; ring
    eigenvalues 2 cos(2 pi k/n) for n = 3..10, chain 2 cos(k pi/(n+1));
    Coulson-Rushbrooke: all q = 0 in neutral alternant hydrocarbons;
    butadiene p12 = 0.894, p23 = 0.447 (closed form 2(c1c2 + ...));
    allyl cation/anion charges +-0.5 on the termini; coefficients
    orthonormal; characteristic polynomial of benzene x^6 - 6x^4 + 9x^2 - 4;
    electrocyclic selection rules for 4n/4n+2 electrons, thermal and
    photochemical; [4+2] thermally allowed, [2+2] forbidden; vs v1.0.
§8 ERROR ANALYSIS
    Jacobi converges quadratically; at off-diagonal norm 1e-11 the
    eigenvalues are accurate to ~1e-22/gap and the vectors to ~1e-11/gap
    (gaps of the presets >= 0.2 apart from exact degeneracies, which are
    resolved by the Gram-Schmidt basis).  Printed with 3 decimals.  The
    1e-6 degeneracy and 1e-3 tie thresholds are far above these errors and
    far below the smallest genuine differences (>= 0.01).
"""
from __future__ import annotations

import math

from .jsmath import js_hypot, js_sign, sq

HT = {
    "C": {"h": 0, "k": 1, "z": 1},
    "N1": {"h": 0.5, "k": 1, "z": 1},
    "N2": {"h": 1.5, "k": 0.8, "z": 2},
    "O1": {"h": 1.0, "k": 1, "z": 1},
    "O2": {"h": 2.0, "k": 0.8, "z": 2},
}
S3 = math.sqrt(3)


def bond_k(a: str, b: str):
    if a == "C":
        return HT[b]["k"]
    if b == "C":
        return HT[a]["k"]
    return HT[a]["k"] * HT[b]["k"]


def jacobi(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for _sweep in range(100):
        off = 0
        for i in range(n):
            for j in range(i + 1, n):
                off += A[i][j] * A[i][j]
        if off < 1e-22:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-15:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                sg = 1 if th == 0 or th != th else js_sign(th)
                t = sg / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    akp, akq = A[k][p], A[k][q]
                    A[k][p] = c * akp - s * akq
                    A[k][q] = s * akp + c * akq
                for k in range(n):
                    apk, aqk = A[p][k], A[q][k]
                    A[p][k] = c * apk - s * aqk
                    A[q][k] = s * apk + c * aqk
                for k in range(n):
                    vkp, vkq = V[k][p], V[k][q]
                    V[k][p] = c * vkp - s * vkq
                    V[k][q] = s * vkp + c * vkq
    return [A[i][i] for i in range(n)], V


def max_matching(n: int, bonds) -> int:
    best = 0
    used = [False] * n

    def rec(b, cnt):
        nonlocal best
        if b == len(bonds):
            if cnt > best:
                best = cnt
            return
        i, j = bonds[b]
        if not used[i] and not used[j]:
            used[i] = used[j] = True
            rec(b + 1, cnt + 1)
            used[i] = used[j] = False
        rec(b + 1, cnt)

    rec(0, 0)
    return best


def solve(types, bonds, charge=0) -> dict:
    n = len(types)
    A = [[0] * n for _ in range(n)]
    for i, t in enumerate(types):
        A[i][i] = HT[t]["h"]
    for i, j in bonds:
        A[i][j] = A[j][i] = bond_k(types[i], types[j])
    w, V = jacobi(A)
    idx = sorted(range(n), key=lambda i: -w[i])
    mos = []
    for i in idx:
        c = [r[i] for r in V]
        f = next((x for x in c if abs(x) > 1e-6), None)
        if f is not None and f < 0:
            c = [-x for x in c]
        mos.append({"x": w[i], "c": c, "occ": 0})
    shells = []
    for i, m in enumerate(mos):
        s = shells[-1] if shells else None
        if s and abs(mos[s["mo"][0]]["x"] - m["x"]) < 1e-6:
            s["mo"].append(i)
        else:
            shells.append({"x": m["x"], "mo": [i]})
    for sh in shells:
        if len(sh["mo"]) < 2:
            continue
        B = [mos[i]["c"] for i in sh["mo"]]
        out = []
        for r in range(n):
            if len(out) >= len(B):
                break
            v = [0] * n
            for b in B:
                for k in range(n):
                    v[k] += b[r] * b[k]
            for o in out:
                d = 0
                for k, x in enumerate(o):
                    d = d + x * v[k]
                for k in range(n):
                    v[k] -= d * o[k]
            L = js_hypot(*v)
            if L > 1e-6:
                out.append([x / L for x in v])
        for j, i in enumerate(sh["mo"]):
            mos[i]["c"] = out[j]
    zsum = 0
    for t in types:
        zsum = zsum + HT[t]["z"]
    ne = zsum - (charge or 0)
    left = max(0, min(2 * n, ne))
    for si, s in enumerate(shells):
        cap = 2 * len(s["mo"])
        put = min(cap, left)
        left -= put
        s["ne"] = put
        for i in s["mo"]:
            mos[i]["occ"] = put / len(s["mo"])
        for i in s["mo"]:
            mos[i]["shell"] = si
    P = [[0] * n for _ in range(n)]
    for m in mos:
        if m["occ"]:
            for r in range(n):
                for s_ in range(n):
                    P[r][s_] += m["occ"] * m["c"][r] * m["c"][s_]
    q = [HT[t]["z"] - P[r][r] for r, t in enumerate(types)]
    bo = [P[i][j] for i, j in bonds]
    F = []
    for r, t in enumerate(types):
        if t != "C":
            F.append(None)
            continue
        acc = 0
        for b, (i, j) in enumerate(bonds):
            acc = acc + (bo[b] if (i == r or j == r) else 0)
        F.append(S3 - acc)
    Bsum = 0
    for m in mos:
        Bsum = Bsum + m["occ"] * m["x"]
    homo = lumo = -1
    for k, s in enumerate(shells):
        if s["ne"] > 0:
            homo = k
    for k, s in enumerate(shells):
        if lumo < 0 and s["ne"] < 2 * len(s["mo"]):
            lumo = k

    def dens(k):
        if k < 0:
            return None
        res = []
        for r in range(n):
            acc = 0
            for i in shells[k]["mo"]:
                acc = acc + sq(mos[i]["c"][r])
            res.append(acc / len(shells[k]["mo"]))
        return res

    allC = all(t == "C" for t in types)
    DE = m_ = None
    if allC:
        m_ = min(max_matching(n, bonds), ne // 2)
        DE = Bsum - 2 * m_
    deg = [sum(1 for i, j in bonds if i == r or j == r) for r in range(n)]
    ring = n >= 3 and len(bonds) == n and all(d == 2 for d in deg)
    unp = 0
    for sh in shells:
        g = len(sh["mo"])
        unp = unp + (sh["ne"] if sh["ne"] <= g else 2 * g - sh["ne"])
    return {"n": n, "A": A, "mos": mos, "shells": shells, "ne": ne, "P": P, "q": q, "bo": bo, "F": F, "B": Bsum,
            "homo": homo, "lumo": lumo, "fH": dens(homo), "fL": dens(lumo), "DE": DE, "m": m_, "allC": allC,
            "deg": deg, "ring": ring, "unpaired": unp}


def reactivity(types, R, mode: str):
    cand = [r for r in range(len(types)) if types[r] == "C" and R["deg"][r] <= 2]
    if not cand:
        return None
    qs = [R["q"][r] for r in cand]
    spread = max(qs) - min(qs)

    def pick(key, sgn):
        v = [key(r) for r in cand]
        best = max(sgn * x for x in v)
        return [r for i, r in enumerate(cand) if abs(sgn * v[i] - best) < 1e-3]

    if mode == "q":
        E = pick(lambda r: R["q"][r], -1)
        N = pick(lambda r: R["q"][r], 1)
    else:
        E = pick(lambda r: R["fH"][r], 1) if R["fH"] else []
        N = pick(lambda r: R["fL"][r], 1) if R["fL"] else []
    return {"cand": cand, "polar": spread > 0.02, "E": E, "N": N, "R": pick(lambda r: R["F"][r], 1)}


def poly_from_roots(roots):
    c = [1]
    for a in roots:
        d = [0] * (len(c) + 1)
        for i, v in enumerate(c):
            d[i] += v
            d[i + 1] += v * a
        c = d
    return c


def page(types, bonds, charge) -> dict:
    """Everything the huckel page needs for one molecule: solve, both reactivity criteria, polynomial."""
    R = solve(types, bonds, charge)
    R["react"] = {"q": reactivity(types, R, "q"), "fo": reactivity(types, R, "fo")}
    R["poly"] = poly_from_roots([m["x"] for m in R["mos"]]) if R["n"] <= 10 else None
    return R


# ---------------------------------------------------------------- Woodward-Hoffmann (page wh)
def chain(types, charge=0):
    n = len(types)
    return list(types), [[i, i + 1] for i in range(n - 1)], charge


HK = {"eth": (2, False, 0), "all+": (3, False, 1), "buta": (4, False, 0), "hexa": (6, False, 0),
      "cbd": (4, True, 0), "bz": (6, True, 0)}
SYS = {"buta": (4, 4), "hexa": (6, 6), "al+": (3, 2), "pd+": (5, 4)}
COMP = {"eth": {"t": ["C", "C"], "ends": [0, 1], "ne": 2}, "buta": {"t": ["C", "C", "C", "C"], "ends": [0, 3], "ne": 4},
        "hexa": {"t": ["C"] * 6, "ends": [0, 5], "ne": 6}, "acro": {"t": ["O1", "C", "C", "C"], "ends": [2, 3], "ne": 4, "nr": 2}}


def hk(sys_: str) -> dict:
    n, ring, ch = HK[sys_]
    bonds = [[i, i + 1] for i in range(n - 1)]
    if ring:
        bonds.append([n - 1, 0])
    return solve(["C"] * n, bonds, ch)


def electro(n: int, ne: int, photo: bool) -> dict:
    R = solve(["C"] * n, [[i, i + 1] for i in range(n - 1)], n - ne)
    mos = R["mos"]
    h = ne / 2 - 1
    fo = int(h + 1 if photo else h)
    c = mos[fo]["c"]
    prod = c[0] * c[n - 1]
    return {"homo": int(h), "fo": fo, "c": c, "prod": prod, "allowed": "con" if prod < 0 else "dis"}


def sym_of(c, el: str) -> str:
    n = len(c)
    s = 0
    for k in range(n):
        s += c[k] * c[n - 1 - k]
    if el == "m":
        return "S" if s > 0 else "A"
    return "S" if s < 0 else "A"


def _chain_mos(n):
    return solve(["C"] * n, [[i, i + 1] for i in range(n - 1)], 0)["mos"]


def correl(n: int, ne: int, mode: str) -> dict:
    el = "C2" if mode == "con" else "m"
    L = [{"x": m["x"], "sym": sym_of(m["c"], el), "name": "ψ" + str(i + 1)} for i, m in enumerate(_chain_mos(n))]
    inner = []
    if n - 2 > 0:
        for i, m in enumerate(_chain_mos(n - 2)):
            if n - 2 == 1:
                nm = "p"
            elif n - 2 == 2:
                nm = "π*" if i else "π"
            else:
                nm = "π" + str(i + 1) + ("*" if m["x"] < -1e-6 else "")
            inner.append({"x": m["x"], "sym": sym_of(m["c"], el), "name": nm})
    Rt = [{"x": 2.6, "sym": "S", "name": "σ"}, *inner, {"x": -2.6, "sym": "A", "name": "σ*"}]
    Rt = sorted(Rt, key=lambda o: -o["x"])
    links = []
    for s in ("S", "A"):
        lft = [i for i, o in enumerate(L) if o["sym"] == s]
        rgt = [i for i, o in enumerate(Rt) if o["sym"] == s]
        for k, i in enumerate(lft):
            if k < len(rgt):
                links.append([i, rgt[k]])
    occL = [2 if i < ne / 2 else 0 for i in range(len(L))]
    occR = [0] * len(Rt)
    for i, j in links:
        occR[j] = occL[i]
    ground = [2 if i < ne / 2 else 0 for i in range(len(Rt))]
    ok = all(v == ground[i] for i, v in enumerate(occR))
    return {"L": L, "R": Rt, "links": links, "occL": occL, "occR": occR, "ok": ok}


def cyclo(A: str, B: str, photo2: bool, pair) -> dict:
    """Frontier-orbital analysis of the supra-supra cycloaddition A + B (wh section 3)."""
    ca, cb = COMP[A], COMP[B]
    RA = solve(*chain(ca["t"]))
    RB = solve(*chain(cb["t"]))
    hA, lA, hB, lB = RA["homo"], RA["lumo"], RB["homo"], RB["lumo"]
    xA = [m["x"] for m in RA["mos"]]
    xB = [m["x"] for m in RB["mos"]]
    pairs = [["LL", lA, lB], ["HH", hA, hB]] if photo2 else [["HL", hA, lB], ["LH", lA, hB]]

    def gap(p):
        return abs(xA[p[1]] - xB[p[2]])

    if not pair or not any(p[0] == pair for p in pairs):
        pair = sorted(pairs, key=gap)[0][0]
    pr = next(p for p in pairs if p[0] == pair)
    cA = list(RA["mos"][pr[1]]["c"])
    cB = list(RB["mos"][pr[2]]["c"])
    a1, a2 = 0, len(ca["t"]) - 1
    b1, b2 = cb["ends"]
    s1 = -cA[a1] * cB[b1]
    s2 = -cA[a2] * cB[b2]
    if s1 < 0 and s2 < 0:
        cB = [-x for x in cB]
        s1 = -s1
        s2 = -s2
    allowed = s1 > 0 and s2 > 0
    occA = [2 if i < ca["ne"] / 2 else 0 for i in range(len(xA))]
    if photo2:
        occA[hA] = 1
        occA[lA] = 1
    occB = [2 if i < cb["ne"] / 2 else 0 for i in range(len(xB))]
    k = (ca.get("nr") or ca["ne"]) + (cb.get("nr") or cb["ne"])
    gE = abs(xA[hA] - solve(*chain(["C", "C"]))["mos"][1]["x"])
    gC = abs(xA[hA] - xB[lB])
    return {"tA": ca["t"], "tB": cb["t"], "endsB": cb["ends"], "hA": hA, "lA": lA, "hB": hB, "lB": lB, "xA": xA, "xB": xB,
            "pair": pair, "pr": pr, "gap": gap(pr), "cA": cA, "cB": cB, "s1": s1, "s2": s2, "allowed": allowed,
            "occA": occA, "occB": occB, "k": k, "rule": k % 4 == 2, "gE": gE, "gC": gC}

"""MO diagrams of first- and second-row diatomics: a qualitative extended-Hueckel model in the
minimal valence basis, MO names, occupations, bond order, unpaired electrons, ground term.

HEADER
    Model of the page "МО-диаграммы двухатомных молекул" (v1.0
    diatomics.js: AO, VAL, OV, spf, gsolve, jac, mo, build, SPEC).
    Wilkinson convention, sections 1-8.  Energies in eV.

§1 THEORY
    Valence AOs with ionisation-like energies (H 1s -13.6 eV, ... Ne 2s
    -48.5, 2p -21.6).  Extended Hueckel: H_ii = alpha_i, H_ij = K S_ij
    (alpha_i + alpha_j)/2 (Wolfsberg-Helmholz, K = 1.75); model overlaps
    between atoms S(ss) = 0.18, S(pp sigma) = 0.40, S(pp pi) = 0.18, and
    S(sp) = 0.45 f with the s-p mixing factor f = 1/(1 + exp((d -
    14)/1)), d = mean 2s-2p gap of the two atoms (30 eV for H/He); the
    overlap matrix used in the secular problem is scaled by 0.65.  H C =
    S C E is solved by Loewdin orthogonalisation (Jacobi).  sigma block
    [sA, pzA, sB, pzB], pi block [pxA, pxB] (doubly degenerate).  MO names:
    for two second-row atoms the two sigma MOs with the largest s weight
    are sigma2s/sigma*2s, the other two sigma2p/sigma*2p; homonuclear g/u
    parity from the sign of the coefficient products.  Aufbau with
    capacity 2 (sigma) or 4 (pi pair, Hund); bond order (n_b - n_a)/2;
    ground term from the single open shell (2Sigma+, 3Sigma-, 2Pi).
    Experimental R_e (A) and D_0 (eV) of the species table are data of
    v1.0 (Huber and Herzberg 1979 / NIST WebBook).

§2 ALGORITHM
    As v1.0, step by step (Jacobi with 60 sweeps, threshold 1e-24;
    stable sorts).

§3 APPLICATIONS
    Endpoints dia.spec, dia.build.

§4 SPECIFICATION
    build(A, B, Q, mix) -> {M: [{E, sym, deg, c, nm, bt, num, par?, occ,
      w}], nV, core, hom, both2, noneP, nb, na, bo, unp, term | None,
      termMult, neg, aoA, aoB, vA, vB}.  w: AO weights c^2 / sum c^2 by
      "<atom><s|p>".  term None: several open shells (multiplicity
      termMult).  Tier: bitwise vs v1.0 on Linux/glibc (EXACT).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The qualitative model is not a quantum-chemical calculation; it is
    tuned to give the textbook level orders (pi2p below sigma2p for B2,
    C2, N2; above for O2, F2).
§7 TEST CASES (tests/test_diatomics.py)
    Bond orders and unpaired electrons of the textbook table (H2 1/0, He2
    0, Li2 1, B2 1/2, C2 2/0, N2 3/0, O2 2/2, F2 1/0, NO 2.5/1, CO 3/0,
    O2- 1.5/1, O2 2- 1/0); level order switch between N2 and O2; ground
    terms (O2 3Sigma_g-, N2+ 2Sigma_g+, NO 2Pi, B2 3Sigma_g-); MO
    coefficients S-orthonormal in the scaled metric; vs v1.0.
§8 ERROR ANALYSIS
    Jacobi to 1e-12 off-diagonal; energies are model values (0.1 eV
    printed); bond orders and occupations are integers/halves, exact.
"""
from __future__ import annotations

import math

from .jsmath import exp, js_sign

ELS = ["H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne"]
AO = {"H": [-13.6], "He": [-24.6], "Li": [-5.4, -3.5], "Be": [-9.3, -6.0], "B": [-14.0, -8.3], "C": [-19.4, -10.7],
      "N": [-25.6, -13.2], "O": [-32.4, -15.9], "F": [-40.2, -18.7], "Ne": [-48.5, -21.6]}
VAL = {"H": 1, "He": 2, "Li": 1, "Be": 2, "B": 3, "C": 4, "N": 5, "O": 6, "F": 7, "Ne": 8}
OV = {"ss": 0.18, "sp": 0.45, "pp": 0.40, "pi": 0.18, "K": 1.75, "dc": 14.0, "w": 1.0, "sm": 0.65}
# [A, B, charge, R_e (A), D_0 (eV)]; None: no data or unbound
SPEC = [["H", "H", 1, 1.052, 2.65], ["H", "H", 0, 0.741, 4.48], ["He", "He", 1, 1.081, 2.4], ["He", "He", 0, None, 0], ["Li", "Li", 0, 2.673, 1.05],
        ["Be", "Be", 0, 2.45, 0.1], ["B", "B", 0, 1.590, 3.0], ["C", "C", 0, 1.243, 6.2], ["N", "N", 0, 1.098, 9.76], ["O", "O", 0, 1.208, 5.12],
        ["F", "F", 0, 1.412, 1.60], ["Ne", "Ne", 0, None, 0], ["N", "N", 1, 1.116, 8.71], ["O", "O", 1, 1.116, 6.66], ["O", "O", -1, 1.35, None],
        ["O", "O", -2, 1.49, None], ["C", "C", -2, 1.19, None], ["C", "O", 0, 1.128, 11.09], ["C", "N", 0, 1.172, 7.7], ["C", "N", -1, 1.16, None],
        ["N", "O", 0, 1.151, 6.50], ["N", "O", 1, 1.063, 10.85], ["H", "F", 0, 0.917, 5.87], ["O", "H", 0, 0.970, 4.39]]


def is_h(X):
    return X in ("H", "He")


def spf(A, B):
    if len(AO[A]) < 2 or len(AO[B]) < 2:
        return 1
    g = lambda X: AO[X][1] - AO[X][0] if len(AO[X]) > 1 else 30  # noqa: E731
    d = (g(A) + g(B)) / 2
    return 1 / (1 + exp((d - OV["dc"]) / OV["w"]))


def jac(A0):
    n = len(A0)
    A = [list(r) for r in A0]
    V = [[1 if i == j else 0 for j in range(n)] for i in range(n)]
    for _sw in range(60):
        off = 0
        for i in range(n):
            for j in range(i + 1, n):
                off += A[i][j] * A[i][j]
        if off < 1e-24:
            break
        for p in range(n):
            for q in range(p + 1, n):
                if abs(A[p][q]) < 1e-15:
                    continue
                th = (A[q][q] - A[p][p]) / (2 * A[p][q])
                t = (1 if th == 0 or th != th else js_sign(th)) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(n):
                    a, b = A[k][p], A[k][q]
                    A[k][p] = c * a - s * b
                    A[k][q] = s * a + c * b
                for k in range(n):
                    a, b = A[p][k], A[q][k]
                    A[p][k] = c * a - s * b
                    A[q][k] = s * a + c * b
                for k in range(n):
                    a, b = V[k][p], V[k][q]
                    V[k][p] = c * a - s * b
                    V[k][q] = s * a + c * b
    return [A[i][i] for i in range(n)], V


def _mm(A, B):
    out = []
    for r in A:
        row = []
        for j in range(len(B[0])):
            s = 0
            for k, x in enumerate(r):
                s = s + x * B[k][j]
            row.append(s)
        out.append(row)
    return out


def gsolve(H, S):
    """H C = S C E by Loewdin orthogonalisation X = S^-1/2."""
    n = len(H)
    val, vec = jac(S)
    X = []
    for i in range(n):
        row = []
        for j in range(n):
            s = 0
            for k in range(n):
                s += vec[i][k] * vec[j][k] / math.sqrt(val[k])
            row.append(s)
        X.append(row)
    Hp = _mm(_mm(X, H), X)
    E, F = jac(Hp)
    return E, _mm(X, F)


def mo(A, B, mix):
    has_p = lambda x: len(AO[x]) > 1  # noqa: E731
    bas = []
    for X, at in ((A, 0), (B, 1)):
        bas.append({"at": at, "t": "s", "e": AO[X][0]})
        if has_p(X):
            bas.append({"at": at, "t": "p", "e": AO[X][1]})
    n = len(bas)
    H, S = [], []
    for i in range(n):
        H.append([])
        S.append([])
        for j in range(n):
            s = 0
            a, b = bas[i], bas[j]
            if i == j:
                s = 1
            elif a["at"] != b["at"]:
                if a["t"] == "s" and b["t"] == "s":
                    s = OV["ss"]
                elif a["t"] == "p" and b["t"] == "p":
                    s = OV["pp"]
                else:
                    s = OV["sp"] * spf(A, B) if mix else 0
            S[i].append(s)
            H[i].append(a["e"] if i == j else OV["K"] * s * (a["e"] + b["e"]) / 2)
    Sm = [[1 if i == j else OV["sm"] * x for j, x in enumerate(r)] for i, r in enumerate(S)]
    E, C = gsolve(H, Sm)
    out = []
    for k, e in enumerate(E):
        out.append({"E": e, "sym": "σ", "c": [{"at": b["at"], "t": b["t"], "c": C[i][k]} for i, b in enumerate(bas)]})
    if has_p(A) and has_p(B):
        ea, eb, s = AO[A][1], AO[B][1], OV["pi"]
        h = OV["K"] * s * (ea + eb) / 2
        pe, pc = gsolve([[ea, h], [h, eb]], [[1, OV["sm"] * s], [OV["sm"] * s, 1]])
        for k, e in enumerate(pe):
            out.append({"E": e, "sym": "π", "deg": 2, "c": [{"at": 0, "t": "p", "c": pc[0][k]}, {"at": 1, "t": "p", "c": pc[1][k]}]})
    else:
        X = A if has_p(A) else B if has_p(B) else None
        if X:
            out.append({"E": AO[X][1], "sym": "π", "deg": 2, "c": [{"at": 0 if X == A else 1, "t": "p", "c": 1}]})
    for o in out:
        o["deg"] = o.get("deg") or 1
    return sorted(out, key=lambda o: o["E"])


def _sum_sq(cs):
    s = 0
    for x in cs:
        s = s + x["c"] * x["c"]
    return s


def build(A, B, Q, mix) -> dict:
    M = mo(A, B, mix)
    hom = A == B
    nV = VAL[A] + VAL[B] - Q
    core = (0 if is_h(A) else 1) + (0 if is_h(B) else 1)
    both2 = not is_h(A) and not is_h(B)
    noneP = is_h(A) and is_h(B)
    sig = [o for o in M if o["sym"] == "σ"]
    pis = [o for o in M if o["sym"] == "π"]
    if noneP:
        sig[0].update(nm="σ1s", bt=1)
        sig[1].update(nm="σ*1s", bt=-1)
    elif both2:
        sw = lambda o: _sum_sq([x for x in o["c"] if x["t"] == "s"]) / _sum_sq(o["c"])  # noqa: E731
        bys = sorted(sig, key=lambda o: -sw(o))
        S2 = sorted(bys[:2], key=lambda o: o["E"])
        P2 = sorted(bys[2:], key=lambda o: o["E"])
        S2[0].update(nm="σ2s", bt=1)
        S2[1].update(nm="σ*2s", bt=-1)
        P2[0].update(nm="σ2p", bt=1)
        P2[1].update(nm="σ*2p", bt=-1)
        pis[0].update(nm="π2p", bt=1)
        pis[1].update(nm="π*2p", bt=-1)
    else:
        X = B if is_h(A) else A
        sig[0].update(nm=f"σ(2s {X})", bt=0)
        sig[1].update(nm="σ", bt=1)
        sig[2].update(nm="σ*", bt=-1)
        pis[0].update(nm=f"π(2p {X})", bt=0)
    if hom:
        ng = nu = 1 if noneP else 2
        pu = pg = 1
        for o in M:
            if o["sym"] == "σ":
                s = 0
                for x in o["c"]:
                    if x["at"] == 0:
                        y = next((y for y in o["c"] if y["at"] == 1 and y["t"] == x["t"]), None)
                        s = s + x["c"] * (y["c"] if y else 0)
                o["par"] = "g" if s > 0 else "u"
                if o["par"] == "g":
                    o["num"] = f"{ng}σ<sub>g</sub>"
                    ng += 1
                else:
                    o["num"] = f"{nu}σ<sub>u</sub>"
                    nu += 1
            else:
                s = o["c"][0]["c"] * o["c"][1]["c"]
                o["par"] = "u" if s > 0 else "g"
                if o["par"] == "u":
                    o["num"] = f"{pu}π<sub>u</sub>"
                    pu += 1
                else:
                    o["num"] = f"{pg}π<sub>g</sub>"
                    pg += 1
    else:
        ns, np_ = 1 + core, 1
        for o in M:
            o["par"] = None
            if o["sym"] == "σ":
                o["num"] = f"{ns}σ"
                ns += 1
            else:
                o["num"] = f"{np_}π"
                np_ += 1
    left = max(0, nV)
    for o in M:
        o["occ"] = min(2 * o["deg"], left)
        left -= o["occ"]
    nb = na = unp = 0
    for o in M:
        if o.get("bt", 0) > 0:
            nb += o["occ"]
        if o.get("bt", 0) < 0:
            na += o["occ"]
        unp += o["occ"] % 2 if o["deg"] == 1 else (o["occ"] if o["occ"] <= 2 else 4 - o["occ"])
    opn = [o for o in M if o["occ"] % (2 * o["deg"]) != 0]
    term = None
    if not opn:
        term = "¹Σ" + ("<sub>g</sub>" if hom else "") + "<sup>+</sup>"
    elif len(opn) == 1:
        o = opn[0]
        g = "<sub>" + ("g" if o["sym"] == "π" and o["occ"] == 2 else o["par"]) + "</sub>" if hom else ""
        if o["sym"] == "σ":
            term = "²Σ" + g + "<sup>+</sup>"
        elif o["occ"] == 2:
            term = "³Σ" + g + "<sup>−</sup>"
        else:
            term = "²Π" + g
    for o in M:
        tot = _sum_sq(o["c"])
        w = {}
        for at in (0, 1):
            for t in ("s", "p"):
                if any(x["at"] == at and x["t"] == t for x in o["c"]):
                    w[f"{at}{t}"] = _sum_sq([x for x in o["c"] if x["at"] == at and x["t"] == t]) / tot
        o["w"] = w
    return {"M": M, "nV": nV, "core": core, "hom": hom, "both2": both2, "noneP": noneP, "nb": nb, "na": na, "bo": (nb - na) / 2,
            "unp": unp, "term": term, "termMult": unp + 1, "neg": nV < 0, "aoA": AO[A], "aoB": AO[B], "vA": VAL[A], "vB": VAL[B]}


def spec() -> list:
    out = []
    for a, b, q, re_, d in SPEC:
        R = build(a, b, q, True)
        out.append({"a": a, "b": b, "q": q, "re": re_, "d": d, "nV": R["nV"], "bo": R["bo"], "unp": R["unp"]})
    return out

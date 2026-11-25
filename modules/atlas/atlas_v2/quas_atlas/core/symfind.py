"""Point group of a molecule given by coordinates (XYZ, SDF or the page library).

HEADER
    Port of "своя молекула: определение точечной группы по координатам" of
    v1.0 symmetry.js (normSym ... analyzeMolecule).  Wilkinson convention,
    sections 1-8.

§1 THEORY
    Candidate symmetry elements of a molecule (centred at its centre of
    mass) lie along the principal axes of inertia, along atom position
    vectors, along sums, differences and cross products of the positions of
    two equidistant atoms of the same element, and along normals of the
    "faces" formed by an atom and two nearest equivalent neighbours.  A
    candidate direction u is accepted as a C_n axis (n = 8..2) or a plane
    normal if the operation maps every atom onto an atom of the same element
    within a tolerance tol (default 0.1 Angstrom on the page); directions
    that pass only with 3 tol are refined from the matched atom pairs (noisy
    coordinates).  The point group follows from the elements (flow chart).
    The molecule is then rotated into the standard orientation of that group
    (principal axis along z, a C2 or sigma_v along x or in xz, as in the
    page's reference generators), symmetrised (average of g^-1 x(g a) over
    the group) and scaled so that the median bond length is 1.

§2 ALGORITHM
    As v1.0, function by function: parse_xyz, parse_sdf, centered,
    find_elements, classify, std_gens, elems_of_group, frame_of, align_to,
    symmetrize, bonds_of, analyze_molecule.

§3 APPLICATIONS
    Endpoint sym.analyze (molecule library, XYZ input, PubChem SDF).

§4 SPECIFICATION
    analyze(...) -> {'name', 'gens', 'model': {'atoms', 'bonds'}, 'rmsd'
      [, 'tolUsed' if a larger tolerance found a higher group, 2.7.0]} or
    {'err': code, 'arg': str}.  Error codes (texts are in the page):
    empty_input, bad_line (arg = first 40 characters), no_atoms,
    empty_response, too_big, one_atom, unsupported (arg = group),
    align, symmetrize.  Bitwise equal to v1.0 in Chromium 141.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * JS Number() / parseFloat() / parseInt() semantics are reproduced by
      _js_number / _js_parse_float / _js_parse_int for the inputs that can
      occur (decimal and exponent notation, surrounding whitespace).
    * The generator table of the named groups is the one of the page's
      model list (GROUPS in v1.0), so the same closure order (and
      therefore the same symmetrised coordinates) results.
§7 TEST CASES (tests/test_symmetry.py)
    Every molecule of the page library (364) gives the group stated in the
    library; noisy H2O (0.02 Angstrom) is C2v; a single atom -> one_atom;
    151 atoms -> too_big; malformed XYZ -> bad_line; vs Chromium for all
    library molecules (group name and symmetrised coordinates).
§8 ERROR ANALYSIS
    The tolerance decides; numerical errors (O(10u) relative) are far
    below it.  Symmetrisation removes noise below tol exactly onto the
    symmetric configuration (to O(u)).
"""
from __future__ import annotations

import math
import re

from .jsmath import js_hypot, js_sign
from .symmetry import (C2x, GROUP_GENS, I3, INV, PI, SH, Cn, Sn, SVxz, closure, cross, dot, info, mm, mv, nrm, refl, srot,
                       rot, tp)

COVR = {"H": .31, "D": .31, "He": .28, "Li": 1.28, "Be": .96, "B": .84, "C": .76, "N": .71, "O": .66, "F": .57,
        "Ne": .58, "Na": 1.66, "Mg": 1.41, "Al": 1.21, "Si": 1.11, "P": 1.07, "S": 1.05, "Cl": 1.02, "Ar": 1.06,
        "K": 2.03, "Ca": 1.76, "Ti": 1.6, "V": 1.53, "Cr": 1.39, "Mn": 1.39, "Fe": 1.32, "Co": 1.26, "Ni": 1.24,
        "Cu": 1.32, "Zn": 1.22, "Ga": 1.22, "Ge": 1.2, "As": 1.19, "Se": 1.2, "Br": 1.2, "Kr": 1.16, "Mo": 1.54,
        "Ru": 1.46, "Rh": 1.42, "Pd": 1.39, "Ag": 1.45, "Sn": 1.39, "Sb": 1.39, "Te": 1.38, "I": 1.39, "Xe": 1.4,
        "W": 1.62, "Os": 1.44, "Ir": 1.41, "Pt": 1.36, "Au": 1.36, "Hg": 1.32, "Pb": 1.46, "U": 1.96}
AMASS = {"H": 1.008, "D": 2.014, "He": 4, "Li": 6.94, "Be": 9.01, "B": 10.8, "C": 12.01, "N": 14.01, "O": 16, "F": 19,
         "Ne": 20.2, "Na": 23, "Mg": 24.3, "Al": 27, "Si": 28.1, "P": 31, "S": 32.1, "Cl": 35.5, "Ar": 39.9,
         "K": 39.1, "Ca": 40.1, "Ti": 47.9, "V": 50.9, "Cr": 52, "Mn": 54.9, "Fe": 55.8, "Co": 58.9, "Ni": 58.7,
         "Cu": 63.5, "Zn": 65.4, "Ga": 69.7, "Ge": 72.6, "As": 74.9, "Se": 79, "Br": 79.9, "Kr": 83.8, "Mo": 95.9,
         "Ru": 101, "Rh": 103, "Pd": 106, "Ag": 108, "Sn": 119, "Sb": 122, "Te": 128, "I": 127, "Xe": 131,
         "W": 184, "Os": 190, "Ir": 192, "Pt": 195, "Au": 197, "Hg": 201, "Pb": 207, "U": 238}
ZSYM = ["", "H", "He", "Li", "Be", "B", "C", "N", "O", "F", "Ne", "Na", "Mg", "Al", "Si", "P", "S", "Cl", "Ar", "K",
        "Ca", "Sc", "Ti", "V", "Cr", "Mn", "Fe", "Co", "Ni", "Cu", "Zn", "Ga", "Ge", "As", "Se", "Br", "Kr"]

# ------------------------------------------------------------- parsing
_JS_WS = " \t\n\v\f\r             " \
         "    　﻿"
_DEC = re.compile(r"[+-]?(?:\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?|Infinity)")


def _js_number(s: str) -> float:
    """ECMAScript Number(string) for decimal literals (NaN otherwise)."""
    t = s.strip(_JS_WS)
    if t == "":
        return 0.0
    if re.fullmatch(r"0[xX][0-9a-fA-F]+", t):
        return float(int(t, 16))
    if re.fullmatch(r"0[oO][0-7]+", t):
        return float(int(t[2:], 8))
    if re.fullmatch(r"0[bB][01]+", t):
        return float(int(t[2:], 2))
    if _DEC.fullmatch(t):
        return float(t.replace("Infinity", "inf"))
    return float("nan")


def _js_parse_float(s: str) -> float:
    m = _DEC.match(s.lstrip(_JS_WS))
    return float(m.group(0).replace("Infinity", "inf")) if m else float("nan")


def _js_parse_int(s: str) -> float:
    m = re.match(r"[+-]?\d+", s.lstrip(_JS_WS))
    return float(int(m.group(0))) if m else float("nan")


def _isfinite(x: float) -> bool:
    return x == x and x not in (float("inf"), float("-inf"))


def norm_sym(s: str):
    if re.fullmatch(r"\d+", s):
        i = int(s)
        return (ZSYM[i] or None) if i < len(ZSYM) else None
    m = re.match(r"([A-Za-z]{1,2})", str(s))
    if not m:
        return None
    w = m.group(1)
    t = w[0].upper() + (w[1] if len(w) > 1 else "").lower()
    if t not in AMASS and len(t) == 2 and t[0] in AMASS:
        t = t[0]
    return t if t in AMASS else None


def _js_trim_lines(txt: str):
    return [ln.strip(_JS_WS) for ln in re.split(r"\r?\n", txt)]


def parse_xyz(txt: str) -> dict:
    L = [s for s in _js_trim_lines(txt) if len(s)]
    if not L:
        return {"err": "empty_input"}
    i = 0
    if re.fullmatch(r"\d+", L[0]):
        i = 2
        if len(L) > 1 and re.match(r"[A-Za-z]{1,2}\s+[-\d.]", L[1]):
            i = 1
    at = []
    while i < len(L):
        f = re.split(r"\s+", L[i].replace(",", " "))
        if len(f) >= 4:
            t = norm_sym(f[0])
            p = [_js_number(x) for x in f[1:4]]
            if not t or any(not _isfinite(x) for x in p):
                return {"err": "bad_line", "arg": L[i][:40]}
            at.append({"t": t, "p": p})
        i += 1
    if not at:
        return {"err": "no_atoms"}
    return {"atoms": at}


def parse_sdf(txt: str) -> dict:
    L = re.split(r"\r?\n", txt)
    if len(L) < 5:
        return {"err": "empty_response"}
    n = _js_parse_int(L[3][0:3])
    at = []
    k = 0
    while k < n:  # NaN compares false: no atoms
        if 4 + k >= len(L) or not L[4 + k]:
            break
        s = L[4 + k]
        x, y, z = _js_parse_float(s[0:10]), _js_parse_float(s[10:20]), _js_parse_float(s[20:30])
        t = norm_sym(s[31:34].strip(_JS_WS))
        if t:
            at.append({"t": t, "p": [x, y, z]})
        k += 1
    return {"atoms": at} if at else {"err": "empty_response"}


# ---------------------------------------------------- symmetry elements
def jac3(A):
    a = [list(r) for r in A]
    V = [[1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]]
    for _sw in range(50):
        off = 0.0
        for p in range(3):
            for q in range(p + 1, 3):
                off += a[p][q] * a[p][q]
        if off < 1e-20:
            break
        for p in range(3):
            for q in range(p + 1, 3):
                if abs(a[p][q]) < 1e-18:
                    continue
                th = (a[q][q] - a[p][p]) / (2 * a[p][q])
                t = js_sign(th or 1) / (abs(th) + math.sqrt(th * th + 1))
                c = 1 / math.sqrt(t * t + 1)
                s = t * c
                for k in range(3):
                    akp, akq = a[k][p], a[k][q]
                    a[k][p] = c * akp - s * akq
                    a[k][q] = s * akp + c * akq
                for k in range(3):
                    apk, aqk = a[p][k], a[q][k]
                    a[p][k] = c * apk - s * aqk
                    a[q][k] = s * apk + c * aqk
                for k in range(3):
                    vkp, vkq = V[k][p], V[k][q]
                    V[k][p] = c * vkp - s * vkq
                    V[k][q] = s * vkp + c * vkq
    return [{"w": a[i][i], "v": [V[0][i], V[1][i], V[2][i]]} for i in range(3)]


def sym_test(at, tol):
    def ok(M):
        for a in at:
            q = mv(M, a["p"])
            if not any(b["t"] == a["t"] and abs(q[0] - b["p"][0]) < tol and abs(q[1] - b["p"][1]) < tol
                       and abs(q[2] - b["p"][2]) < tol
                       and js_hypot(q[0] - b["p"][0], q[1] - b["p"][1], q[2] - b["p"][2]) < tol for b in at):
                return False
        return True
    return ok


def _w(t):
    return AMASS.get(t) or 40


def centered(at):
    m = 0
    c = [0, 0, 0]
    for a in at:
        w = _w(a["t"])
        m += w
        for k in range(3):
            c[k] += w * a["p"][k]
    c = [x / m for x in c]
    return [{"t": a["t"], "p": [x - c[k] for k, x in enumerate(a["p"])]} for a in at]


def _dist(q, p):
    return js_hypot(q[0] - p[0], q[1] - p[1], q[2] - p[2])


def find_elements(at, tol):
    ok = sym_test(at, tol)
    dirs = []

    def add_dir(v):
        l = js_hypot(*v)
        if l < 1e-6:
            return
        u = [x / l for x in v]
        if not any(abs(dot(d, u)) > 0.99999 for d in dirs):
            dirs.append(u)

    I = [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    for a in at:
        w = _w(a["t"])
        x, y, z = a["p"]
        I[0][0] += w * (y * y + z * z)
        I[1][1] += w * (x * x + z * z)
        I[2][2] += w * (x * x + y * y)
        I[0][1] -= w * x * y
        I[0][2] -= w * x * z
        I[1][2] -= w * y * z
    I[1][0], I[2][0], I[2][1] = I[0][1], I[0][2], I[1][2]
    for e in jac3(I):
        add_dir(e["v"])
    for a in at:
        if js_hypot(*a["p"]) > tol:
            add_dir(a["p"])
    n = len(at)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = at[i], at[j]
            if a["t"] != b["t"]:
                continue
            ra, rb = js_hypot(*a["p"]), js_hypot(*b["p"])
            if abs(ra - rb) > 2 * tol:
                continue
            add_dir([x + b["p"][k] for k, x in enumerate(a["p"])])
            add_dir([x - b["p"][k] for k, x in enumerate(a["p"])])
            c = cross(a["p"], b["p"])
            if js_hypot(*c) > tol * max(ra, 0.5):
                add_dir(c)
            if len(dirs) > 3000:
                break  # as v1.0: leaves the inner loop only
    for i, a in enumerate(at):
        nb = []
        for j, b in enumerate(at):
            nb.append({"j": j, "d": 1e9 if (j == i or b["t"] != a["t"]) else _dist(b["p"], a["p"])})
        nb.sort(key=lambda x: x["d"])
        d0 = nb[0]["d"]
        nb = [x for x in nb if x["d"] < d0 * 1.25 and x["d"] < 1e8][:4]
        for x in range(len(nb)):
            for y in range(x + 1, len(nb)):
                u = [v - a["p"][k] for k, v in enumerate(at[nb[x]["j"]]["p"])]
                w = [v - a["p"][k] for k, v in enumerate(at[nb[y]["j"]]["p"])]
                add_dir(cross(u, w))
    axes, planes = [], []

    def same(v, w):
        return abs(dot(v, w)) > 0.99

    def err(M):
        mx = 0
        for a in at:
            q = mv(M, a["p"])
            bd = 1e9
            for b in at:
                if b["t"] == a["t"]:
                    d = _dist(q, b["p"])
                    if d < bd:
                        bd = d
            if bd > mx:
                mx = bd
        return mx

    loose = sym_test(at, 3 * tol)

    def pairs(M):
        out = []
        for a in at:
            q = mv(M, a["p"])
            b, bd = None, 1e9
            for c in at:
                if c["t"] != a["t"]:
                    continue
                d = _dist(q, c["p"])
                if d < bd:
                    bd, b = d, c
            out.append((a["p"], b["p"]))
        return out

    def refine(u, plane):
        ps = pairs(refl(u) if plane else rot(u, PI))
        s = [0, 0, 0]
        for a, b in ps:
            v = [x - b[k] for k, x in enumerate(a)] if plane else [x + b[k] for k, x in enumerate(a)]
            sg = -1 if dot(v, u) < 0 else 1
            s = [x + sg * v[k] for k, x in enumerate(s)]
        return nrm(s) if js_hypot(*s) > 1e-6 else u

    def put_ax(v, n):
        e = err(rot(v, 2 * PI / n))
        o = next((a for a in axes if same(a["v"], v)), None)
        if o is None:
            axes.append({"v": v, "n": n, "e": e})
            return
        if n > o["n"] or (n == o["n"] and e < o["e"]):
            o["v"], o["n"], o["e"] = v, n, e

    def put_pl(v):
        e = err(refl(v))
        o = next((p for p in planes if same(p["v"], v)), None)
        if o is None:
            planes.append({"v": v, "e": e})
        elif e < o["e"]:
            o["v"], o["e"] = v, e

    for u in dirs:
        f = False
        for n in range(8, 1, -1):
            if ok(rot(u, 2 * PI / n)):
                put_ax(u, n)
                f = True
                break
        if not f and loose(rot(u, PI)):
            w = refine(u, False)
            if ok(rot(w, PI)):
                put_ax(w, 2)
        if ok(refl(u)):
            put_pl(u)
        elif loose(refl(u)):
            w = refine(u, True)
            if ok(refl(w)):
                put_pl(w)
    planes = [p["v"] for p in planes]
    inv = ok(INV)
    S = [{"v": a["v"], "n": 2 * a["n"]} for a in axes if ok(srot(a["v"], PI / a["n"]))]
    return {"axes": axes, "planes": planes, "inv": inv, "S": S}


def classify(at, tol):
    far = at[0]
    for a in at:
        if js_hypot(*a["p"]) > js_hypot(*far["p"]):
            far = a
    if len(at) == 1:
        return {"name": "Kh"}
    u = nrm(far["p"])
    if all(js_hypot(*cross(a["p"], u)) < tol for a in at):
        inv = sym_test(at, tol)(INV)
        return {"name": "D∞h" if inv else "C∞v", "lin": u, "el": {"axes": [], "planes": [], "inv": inv, "S": []}}
    el = find_elements(at, tol)
    axes, planes, inv, S = el["axes"], el["planes"], el["inv"], el["S"]
    high = [a for a in axes if a["n"] >= 3]
    if len(high) >= 2:
        def c(k):
            return sum(1 for a in axes if a["n"] == k)
        valid = c(5) >= 6 if c(5) else c(4) >= 3 if c(4) else c(3) >= 4
        if not valid:
            mx = max(a["n"] for a in high)
            cands = [{"a": a, "k": sum(1 for b in axes if b["n"] == 2 and abs(dot(a["v"], b["v"])) < 0.06)}
                     for a in high if a["n"] == mx]
            cands.sort(key=lambda x: (-x["k"], x["a"]["e"]))
            best = cands[0]["a"]
            axes = [a for a in axes if a["n"] < 3 or a is best]
            el["axes"] = axes
            high = [best]
    if len(high) >= 2:
        n5 = any(a["n"] == 5 for a in axes)
        n4 = any(a["n"] == 4 for a in axes)
        name = ("Ih" if inv else "I") if n5 else ("Oh" if inv else "O") if n4 else "Th" if inv else "Td" if planes else "T"
        return {"el": el, "name": name}
    if not axes:
        return {"el": el, "name": "Cs" if planes else "Ci" if inv else "C1"}
    n = max(a["n"] for a in axes)
    pa, bp = None, -1
    for a in axes:
        if a["n"] != n:
            continue
        k = sum(1 for b in axes if b["n"] == 2 and abs(dot(a["v"], b["v"])) < 0.06) + \
            (0.5 if any(x["n"] == 2 * n and abs(abs(dot(x["v"], a["v"])) - 1) < 0.06 for x in S) else 0)
        if k > bp:
            bp, pa = k, a["v"]
    perp = sum(1 for b in axes if b["n"] >= 2 and abs(dot(pa, b["v"])) < 0.06)
    sh = any(abs(abs(dot(p, pa)) - 1) < 0.06 for p in planes)
    sv = any(abs(dot(p, pa)) < 0.06 for p in planes)
    if perp >= n:
        return {"el": el, "pa": pa, "name": f"D{n}{'h' if sh else 'd' if sv else ''}"}
    if sh:
        return {"el": el, "pa": pa, "name": f"C{n}h"}
    if sv:
        return {"el": el, "pa": pa, "name": f"C{n}v"}
    if any(abs(abs(dot(s["v"], pa)) - 1) < 0.06 and s["n"] == 2 * n for s in S):
        return {"el": el, "pa": pa, "name": f"S{2 * n}"}
    return {"el": el, "pa": pa, "name": f"C{n}"}


# --------------------------------------------- standard orientation
def std_gens(name: str):
    """Reference generators of a group (v1.0 stdGens); None if the page does not know the group."""
    if name in GROUP_GENS:
        return GROUP_GENS[name]
    if name == "C1":
        return []
    if name == "Cs":
        return [SH]
    if name == "Ci":
        return [INV]
    for pat, f in ((r"C(\d)", lambda n: [Cn(n)]), (r"C(\d)v", lambda n: [Cn(n), SVxz]),
                   (r"C(\d)h", lambda n: [Cn(n), SH]), (r"S(\d+)", lambda n: [Sn(n)]),
                   (r"D(\d)", lambda n: [Cn(n), C2x]), (r"D(\d)h", lambda n: [Cn(n), C2x, SH]),
                   (r"D(\d)d", lambda n: [Sn(2 * n), C2x])):
        m = re.fullmatch(pat, name)
        if m:
            return f(int(m.group(1)))
    return None


def elems_of_group(G):
    axes, planes = [], []
    for M in G:
        f = info(M)
        if f["t"] == "C":
            a = next((a for a in axes if abs(abs(dot(a["v"], f["ax"])) - 1) < 1e-4), None)
            if a:
                a["n"] = max(a["n"], f["n"])
            else:
                axes.append({"v": f["ax"], "n": f["n"]})
        elif f["t"] == "s" and not any(abs(abs(dot(p, f["ax"])) - 1) < 1e-4 for p in planes):
            planes.append(f["ax"])
    return {"axes": axes, "planes": planes}


def frame_of(a, b):
    e3 = nrm(a)
    w = b
    if not w or js_hypot(*cross(w, e3)) < 1e-6:
        w = [1, 0, 0] if abs(e3[0]) < 0.9 else [0, 1, 0]
    d = dot(w, e3)
    e1 = nrm([x - d * e3[k] for k, x in enumerate(w)])
    e2 = cross(e3, e1)
    return [[e1[0], e2[0], e3[0]], [e1[1], e2[1], e3[1]], [e1[2], e2[2], e3[2]]]


def _elist(x):
    return [{"v": a["v"], "ty": "C" + str(a["n"])} for a in x["axes"]] + [{"v": p, "ty": "s"} for p in x["planes"]]


def _ty_rank(e):
    return 0 if e["ty"] == "s" else int(e["ty"][1:])


def align_to(at, gens, el, tol):
    if not gens:
        return I3
    G = closure(gens)
    E = elems_of_group(G)
    T = _elist(E)
    T.sort(key=lambda e: -_ty_rank(e))
    if not T:
        return I3
    U = T[0]
    V = next((e for e in T if abs(abs(dot(e["v"], U["v"])) - 1) > 1e-3), None)
    F0 = frame_of(U["v"], V and V["v"])
    Mo = _elist(el)
    cUV = abs(dot(U["v"], V["v"])) if V else 0

    def test(Q):
        q = [{"t": a["t"], "p": mv(Q, a["p"])} for a in at]
        ok = sym_test(q, tol * 3)
        return all(ok(g) for g in gens)

    for mu in [e for e in Mo if e["ty"] == U["ty"]]:
        for su in (1, -1):
            a = [x * su for x in mu["v"]]
            if V:
                cand = [e for e in Mo if e["ty"] == V["ty"] and abs(abs(dot(e["v"], mu["v"])) - cUV) < 0.06
                        and abs(abs(dot(e["v"], mu["v"])) - 1) > 1e-3]
            else:
                cand = [None]
            for mv2 in cand:
                for sv in ((1, -1) if V else (1,)):
                    Q = mm(F0, tp(frame_of(a, mv2 and [x * sv for x in mv2["v"]])))
                    if test(Q):
                        return Q
    return None


def symmetrize(at, G, tol):
    n = len(at)
    acc = [[0, 0, 0] for _ in at]
    for g in G:
        gt = tp(g)
        for i in range(n):
            q = mv(g, at[i]["p"])
            j, bd = -1, 1e9
            for k, b in enumerate(at):
                if b["t"] != at[i]["t"]:
                    continue
                d = _dist(q, b["p"])
                if d < bd:
                    bd, j = d, k
            if bd > tol * 3:
                return None
            r = mv(gt, at[j]["p"])
            for k in range(3):
                acc[i][k] += r[k]
    return [{"t": a["t"], "p": [x / len(G) for x in acc[i]]} for i, a in enumerate(at)]


def bonds_of(at):
    b = []
    for i in range(len(at)):
        for j in range(i + 1, len(at)):
            a, c = at[i], at[j]
            if a["t"] == "H" and c["t"] == "H":
                continue
            d = _dist(a["p"], c["p"])
            if d < 1.2 * ((COVR.get(a["t"]) or 1.4) + (COVR.get(c["t"]) or 1.4)) and d > 0.3:
                b.append([i, j, d])
    return b


def _analyze_at(at, tol):
    """One pass of v1.0 at tolerance tol on centred atoms -> (result, rmsd, group order)."""
    cl = classify(at, tol)
    name = cl["name"]
    if cl.get("lin"):
        gens = GROUP_GENS[name]
        u = cl["lin"]
        dev = [sum((a["p"][k] - dot(a["p"], u) * u[k]) ** 2 for k in range(3)) for a in at]
        at = [{"t": a["t"], "p": [0, 0, dot(a["p"], u)]} for a in at]
    else:
        gens = std_gens(name)
        if gens is None:
            return {"err": "unsupported", "arg": name}, None, 0
        Q = align_to(at, gens, cl["el"], tol)
        if Q is None:
            return {"err": "align"}, None, 0
        at = [{"t": a["t"], "p": mv(Q, a["p"])} for a in at]
        dev = None
    G = closure(gens)
    sy = symmetrize(at, G, tol)
    if sy is None:
        return {"err": "symmetrize"}, None, 0
    if dev is None:
        dev = [sum((a["p"][k] - b["p"][k]) ** 2 for k in range(3)) for a, b in zip(sy, at)]
    rmsd = math.sqrt(sum(dev) / len(dev))
    bd = bonds_of(sy)
    med = sorted(b[2] for b in bd)[len(bd) >> 1] if bd else 1.5
    sc = 1 / med
    atoms = [{"t": a["t"], "p": [x * sc for x in a["p"]]} for a in sy]
    return {"name": name, "gens": gens, "model": {"atoms": atoms, "bonds": [[b[0], b[1]] for b in bd]}}, rmsd, len(G)


# 2.7.0: noisy coordinates.  At the page tolerance a slightly distorted molecule can lose elements and
# come out in a subgroup (CH4 with 0.02 A noise -> C3v) or fail to align.  The analysis is repeated
# with larger tolerances; a higher group found there is accepted only if the symmetrised structure
# stays within the page tolerance of the input (root-mean-square displacement <= tol), so real
# distortions (larger than tol) keep their lower symmetry.  Exact input gives the v1.0 result.
TOL_SCAN = (1.5, 2.0, 3.0)


def analyze_molecule(raw, tol) -> dict:
    if len(raw) > 150:
        return {"err": "too_big"}
    at = centered(raw)
    if len(at) == 1:
        return {"err": "one_atom"}
    best, rmsd, order = _analyze_at(at, tol)
    if "err" in best or best["name"] != "Ih":
        for f in TOL_SCAN:
            r, d, o = _analyze_at(at, tol * f)
            if "err" not in r and d is not None and d <= tol and o > order:
                best, rmsd, order = r, d, o
                best["tolUsed"] = tol * f
    if "err" not in best:
        best["rmsd"] = rmsd
    return best

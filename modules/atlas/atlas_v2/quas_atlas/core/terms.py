"""Atomic terms: microstates of a configuration, term extraction, Hund's rules, ground terms H-Kr.

HEADER
    Model of the page "Термы атомов" (v1.0 terms.js: parseCfg, shellStates,
    micro, table, extract, hund, econf, cfgStr, groundZ).  Wilkinson
    convention, sections 1-8.  Pure integer combinatorics.

§1 THEORY
    A subshell l with N electrons has C(2(2l+1), N) microstates (Pauli: each
    spin-orbital m_l, m_s at most once); for several subshells the
    microstates combine as a direct product.  Tabulating the number of
    microstates per (M_L, M_S) and repeatedly removing the block
    |M_L| <= L, |M_S| <= S of the largest remaining (M_L, then M_S) yields
    the terms ^{2S+1}L (Condon and Shortley; Slater's method), each with
    (2L+1)(2S+1) microstates and J = |L-S| .. L+S.  Hund's rules for the
    ground term: maximal S, then maximal L; J = |L - S| for a less than
    half-filled, L + S for a more than half-filled subshell (for several
    open subshells the J rule is applied to the open subshell of highest l,
    as on the page).  Ground configurations of H-Kr by the Madelung order
    1s 2s 2p 3s 3p 4s 3d 4p with the exceptions Cr 3d5 4s1, Cu 3d10 4s1.

§2 ALGORITHM
    As v1.0 (recursive enumeration in the order m_l = l..-l, alpha before
    beta; extraction scanning M_L from the top, M_S from the top).

§3 APPLICATIONS
    Endpoints terms.analyze, terms.element.

§4 SPECIFICATION
    analyze(cfg) -> {sh, nmicro, binom, T: {"ML|2MS": count}, Lm, Sm,
      terms: [{L, S2, cells, mult, J2}], ground: {L, S2, J2, ...}, gi} or
      {err, a}: err in bad_token (a = [token]), count (a = [letter, max]),
      empty, duplicate, too_many.  S2 = 2S, J2 = 2J.
    element(Z in 1..36) -> {occ, core, rest, open, ground}.
    Exact (integers).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Parsing follows the JS regular expressions (lower-cased input, commas
    and semicolons as separators, at most 8 electrons for several
    subshells).
§7 TEST CASES (tests/test_terms.py)
    p2 -> 15 microstates, terms 1D, 3P, 1S (ground 3P0); d2 -> 45 and
    1G 3F 1D 3P 1S; p3 -> 4S, 2D, 2P; sum of (2L+1)(2S+1) = number of
    microstates for every preset; ground terms of all 36 elements against
    the NIST ground levels (Fe 5D4, Cr 7S3, Cu 2S1/2, O 3P2, N 4S3/2, ...);
    vs v1.0 for all presets and all elements.
§8 ERROR ANALYSIS
    Integer arithmetic; binom via the JS formula r = r (n - k + i) / i in
    floating point is exact for n <= 14 and rounded.
"""
from __future__ import annotations

import re

from .jsmath import js_round

LL = "SPDFGHIKLMNOQ"
LN = "spdf"
EL = "H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr".split(" ")
ORD = [(1, 0), (2, 0), (2, 1), (3, 0), (3, 1), (4, 0), (3, 2), (4, 1)]
NOBLE = {2: "He", 10: "Ne", 18: "Ar"}


def binom(n: int, k: int) -> int:
    r = 1
    for i in range(1, k + 1):
        r = r * (n - k + i) / i
    return int(js_round(r))


def parse_cfg(s: str) -> dict:
    parts = [p for p in re.split(r"\s+", re.sub(r"[,;]+", " ", s.strip().lower())) if p]
    out = []
    for p in parts:
        m = re.fullmatch(r"(\d)?([spdf])(\d{1,2})?", p, re.ASCII)
        if not m:
            return {"err": "bad_token", "a": [p]}
        l = LN.index(m.group(2))
        N = int(m.group(3)) if m.group(3) else 1
        if N < 1 or N > 2 * (2 * l + 1):
            return {"err": "count", "a": [m.group(2), 2 * (2 * l + 1)]}
        out.append({"n": int(m.group(1)) if m.group(1) else None, "l": l, "N": N})
    if not out:
        return {"err": "empty"}
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            if out[i]["l"] == out[j]["l"] and out[i]["n"] == out[j]["n"]:
                return {"err": "duplicate"}
    if sum(x["N"] for x in out) > 8 and len(out) > 1:
        return {"err": "too_many"}
    return {"sh": out}


def shell_states(l: int, N: int):
    so = []
    for m in range(l, -l - 1, -1):
        so.append((m, 1))
        so.append((m, -1))
    res = []

    def rec(st, k, ml, ms):
        if k == N:
            res.append((ml, ms))
            return
        for i in range(st, len(so)):
            rec(i + 1, k + 1, ml + so[i][0], ms + so[i][1])
    rec(0, 0, 0, 0)
    return res


def micro(sh):
    acc = [(0, 0)]
    for x in sh:
        st = shell_states(x["l"], x["N"])
        acc = [(a[0] + b[0], a[1] + b[1]) for a in acc for b in st]
    return acc


def table(ms):
    T = {}
    Lm = Sm = 0
    for ml, s in ms:
        k = f"{ml}|{s}"
        T[k] = T.get(k, 0) + 1
        Lm = max(Lm, ml)
        Sm = max(Sm, s)
    return {"T": T, "Lm": Lm, "Sm": Sm}


def extract(tb):
    T = dict(tb["T"])
    terms = []
    for _guard in range(500):
        L = S2 = -1
        ml = tb["Lm"]
        while ml >= 0 and L < 0:
            for s in range(tb["Sm"], -1, -1):
                if T.get(f"{ml}|{s}", 0) > 0:
                    L, S2 = ml, s
                    break
            ml -= 1
        if L < 0:
            break
        cells = []
        for ml in range(-L, L + 1):
            for s in range(-S2, S2 + 1, 2):
                k = f"{ml}|{s}"
                T[k] = T.get(k, 0) - 1  # JS: undefined-- gives NaN; never reached for a valid table
                cells.append(k)
        terms.append({"L": L, "S2": S2, "cells": cells})
    return terms


def hund(sh) -> dict:
    S2 = L = 0
    boxes = []
    for x in sh:
        n = 2 * x["l"] + 1
        up = min(x["N"], n)
        dn = x["N"] - up
        occ = [(1 if k < up else 0) + (1 if k < dn else 0) for k in range(n)]
        ml = 0
        for k in range(n):
            m = x["l"] - k
            if k < up:
                ml += m
            if k < dn:
                ml += m
        S2 += up - dn
        L += ml
        boxes.append({"x": x, "occ": occ, "up": up, "dn": dn, "ml": ml})
    L = abs(L)
    opn = sorted([x for x in sh if x["N"] < 2 * (2 * x["l"] + 1)], key=lambda x: -x["l"])
    op = opn[0] if opn else sh[0]
    n = 2 * op["l"] + 1
    J2 = abs(2 * L - S2) if op["N"] < n else 2 * L + S2
    return {"L": L, "S2": S2, "J2": J2, "boxes": boxes, "less": op["N"] < n, "more": op["N"] > n, "halfF": op["N"] == n}


def analyze(cfg: str) -> dict:
    r = parse_cfg(cfg)
    if "err" in r:
        return r
    sh = r["sh"]
    ms = micro(sh)
    tb = table(ms)
    terms = extract(tb)
    for t in terms:
        t["mult"] = (2 * t["L"] + 1) * (t["S2"] + 1)
        t["J2"] = list(range(abs(2 * t["L"] - t["S2"]), 2 * t["L"] + t["S2"] + 1, 2))
    gr = hund(sh)
    gi = next((i for i, q in enumerate(terms) if q["L"] == gr["L"] and q["S2"] == gr["S2"]), -1) if len(sh) == 1 else -1
    return {"sh": sh, "nmicro": len(ms), "binom": [binom(2 * (2 * x["l"] + 1), x["N"]) for x in sh], "T": tb["T"],
            "Lm": tb["Lm"], "Sm": tb["Sm"], "terms": terms, "ground": gr, "gi": gi}


def econf(Z: int):
    sym = EL[Z - 1]
    left = Z
    occ = []
    for n, l in ORD:
        c = min(left, 2 * (2 * l + 1))
        if c <= 0:
            break
        occ.append({"n": n, "l": l, "N": c})
        left -= c
    if sym in ("Cr", "Cu"):
        s4 = next(x for x in occ if x["n"] == 4 and x["l"] == 0)
        d3 = next(x for x in occ if x["n"] == 3 and x["l"] == 2)
        s4["N"] = 1
        d3["N"] += 1
    return occ


def open_sh(Z: int):
    return [x for x in econf(Z) if x["N"] < 2 * (2 * x["l"] + 1)]


def ground_z(Z: int) -> dict:
    op = open_sh(Z)
    if not op:
        return {"L": 0, "S2": 0, "J2": 0, "boxes": [], "closed": True}
    return hund(op)


def element(Z: int) -> dict:
    """Configuration (core + rest, v1.0 cfgStr), open subshells and ground term of element Z."""
    oc = econf(Z)
    core = 0
    for z in (18, 10, 2):
        if Z > z:
            core = z
            break
    cocc = econf(core) if core else []
    cset = {(x["n"], x["l"]): x["N"] for x in cocc}
    rest = [x for x in oc if (x["n"], x["l"]) not in cset or x["N"] != cset[(x["n"], x["l"])]]
    return {"sym": EL[Z - 1], "occ": oc, "core": NOBLE.get(core), "rest": rest, "open": open_sh(Z), "ground": ground_z(Z)}

"""Molecular Hamiltonian of any molecule: nuclei, electrons and term counts.

HEADER
    Model of the Atlas page "Molecular Hamiltonian" (web/<lang>/hamiltonian.html).
    Port of parse/order/nucleiOf and the term counting of v1.0.  Wilkinson
    convention; §8' (integer counting, no floating-point analysis needed
    except the nuclear masses, which are products of two constants).

§1 THEORY
    For M nuclei (charges Z_A, masses M_A in electron masses) and N
    electrons, in atomic units
        H = - sum_A 1/(2 M_A) nabla_A^2 - 1/2 sum_i nabla_i^2
            - sum_i sum_A Z_A / r_Ai + sum_{i<j} 1/r_ij + sum_{A<B} Z_A Z_B / R_AB.
    The number of terms: T_N: M, T_e: N, V_eN: N M, V_ee: N(N-1)/2,
    V_NN: M(M-1)/2.  N = sum Z_A - q for a particle of charge q.
    Masses: isotope mass of the most abundant isotope (u) times
    m_u/m_e = 1822.888.

§2 ALGORITHM
    parse(formula): strip whitespace; a trailing charge "(digits)(+|-)"
    after a letter or bracket gives q; recursive descent over groups
    "(...)n" / "[...]n" and tokens "El n"; counts merged in first-seen
    order.  order(): Hill-like -- if C is present: C, H, then the rest
    alphabetically; otherwise by decreasing Z (stable).  nuclei(): one entry
    per atom in that order, labelled El1, El2, ... when an element repeats.

§3 APPLICATIONS
    The page writes the Hamiltonian of the chosen molecule term by term
    (explicit sums for few nuclei, Sigma notation otherwise), counts the
    terms, and drills the counting in a trainer.

§4 SPECIFICATION
    molecule(formula: str (<= 200 chars), q: int | None) ->
      {ok: False, error: "parse" | "noelectrons" | "toomany"}  or
      {ok: True, q, nuc: [{e, Z, m, lab}], M, Zs, N,
       counts: {TN, Te, VeN, Vee, VNN, total}, zz: [[a, b, Z_a Z_b]] (only
       when M(M-1)/2 <= 6, the pairs the page writes out)}.
    q None -> the charge written in the formula (0 if none).
    Errors are checked in the v1.0 order: parse, N < 1, M > 200.
    Reference: v1.0 hamiltonian.html.  Equivalence tier ``bitwise``
    (integer arithmetic; masses are one product of two decimal constants,
    correctly rounded in both languages).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The element table holds the elements the v1.0 page knew (H...U and D);
    an unknown symbol is a parse error, exactly as before.
§7 TEST CASES (tests/test_hamiltonian.py)
    H2O: M = 3, N = 10, V_eN = 30, V_ee = 45, V_NN = 3; NH4+: N = 10;
    Fe(C5H5)2: M = 21, N = 96; C6H6: total terms 42 + 252 + 861 + 66 ...
    (independent hand counts); parse errors for "Xx2", "H2O)", "(H2O".
    Differential test against v1.0 on all example formulas.
§8' ROBUSTNESS
    Formulas longer than 200 characters are rejected by the endpoint;
    deeply nested brackets are bounded by the length; M > 200 reported as
    "toomany" (the page cannot typeset it), N < 1 as "noelectrons".
"""
from __future__ import annotations

import re

EL = {"H": (1, 1.00783), "He": (2, 4.0026), "Li": (3, 7.016), "Be": (4, 9.0122), "B": (5, 11.0093), "C": (6, 12),
      "N": (7, 14.0031), "O": (8, 15.9949), "F": (9, 18.9984), "Ne": (10, 19.9924), "Na": (11, 22.9898), "Mg": (12, 23.985),
      "Al": (13, 26.9815), "Si": (14, 27.9769), "P": (15, 30.9738), "S": (16, 31.9721), "Cl": (17, 34.9689), "Ar": (18, 39.9624),
      "K": (19, 38.9637), "Ca": (20, 39.9626), "Sc": (21, 44.9559), "Ti": (22, 47.9479), "V": (23, 50.944), "Cr": (24, 51.9405),
      "Mn": (25, 54.938), "Fe": (26, 55.9349), "Co": (27, 58.9332), "Ni": (28, 57.9353), "Cu": (29, 62.9296), "Zn": (30, 63.9291),
      "Ga": (31, 68.9256), "Ge": (32, 73.9212), "As": (33, 74.9216), "Se": (34, 79.9165), "Br": (35, 78.9183), "Kr": (36, 83.9115),
      "Rb": (37, 84.9118), "Sr": (38, 87.9056), "Ag": (47, 106.905), "Cd": (48, 113.903), "Sn": (50, 119.902), "Sb": (51, 120.904),
      "Te": (52, 129.906), "I": (53, 126.904), "Xe": (54, 131.904), "Cs": (55, 132.905), "Ba": (56, 137.905), "W": (74, 183.951),
      "Os": (76, 191.961), "Pt": (78, 194.965), "Au": (79, 196.967), "Hg": (80, 201.971), "Pb": (82, 207.977), "U": (92, 238.051),
      "D": (1, 2.01410)}
AMU = 1822.888


class FormulaError(ValueError):
    pass


def parse(f: str) -> tuple[dict[str, int], int]:
    """Element counts and the charge written in a formula."""
    f = re.sub(r"\s+", "", f)
    q = 0
    m = re.match(r"^(.*?)([0-9]*)([+-])$", f)
    if m and m.group(1) and re.search(r"[A-Za-z)\]]$", m.group(1)):
        q = (1 if m.group(3) == "+" else -1) * (int(m.group(2)) if m.group(2) and int(m.group(2)) else 1)
        f = m.group(1)
    i = 0

    def group() -> dict[str, int]:
        nonlocal i
        cnt: dict[str, int] = {}
        while i < len(f) and f[i] not in ")]":
            if f[i] in "([":
                i += 1
                g = group()
                if i >= len(f) or f[i] not in ")]":
                    raise FormulaError("brackets")
                i += 1
                d = ""
                while i < len(f) and f[i] in "0123456789":  # JS /\d/ is ASCII-only
                    d += f[i]
                    i += 1
                k = int(d) if d and int(d) else 1
                for e in g:
                    cnt[e] = cnt.get(e, 0) + g[e] * k
                continue
            mm = re.match(r"([A-Z][a-z]?)([0-9]*)", f[i:])
            if not mm or mm.group(1) not in EL:
                raise FormulaError("element")
            i += len(mm.group(0))
            cnt[mm.group(1)] = cnt.get(mm.group(1), 0) + (int(mm.group(2)) if mm.group(2) and int(mm.group(2)) else 1)
        return cnt
    c = group()
    if i < len(f):
        raise FormulaError("brackets")
    return c, q


def order(cnt: dict[str, int]) -> list[str]:
    ks = list(cnt)
    if cnt.get("C"):
        return [k for k in ["C", "H"] + sorted(k for k in ks if k not in ("C", "H")) if cnt.get(k)]
    return sorted(ks, key=lambda e: -EL[e][0])  # stable, like Array.sort in V8


def nuclei(cnt: dict[str, int]) -> list[dict]:
    out = []
    for e in order(cnt):
        for k in range(1, cnt[e] + 1):
            out.append({"e": e, "Z": EL[e][0], "m": EL[e][1] * AMU, "lab": f"{e}{k}" if cnt[e] > 1 else e})
    return out


def molecule(formula: str, q: int | None = None) -> dict:
    """Nuclei, electron count and Hamiltonian term counts (see §4)."""
    try:
        cnt, q0 = parse(formula)
    except FormulaError:
        return {"ok": False, "error": "parse"}
    if q is None:
        q = q0
    nuc = nuclei(cnt)
    M = len(nuc)
    Zs = sum(a["Z"] for a in nuc)
    N = Zs - q
    if N < 1:
        return {"ok": False, "error": "noelectrons"}
    if M > 200:
        return {"ok": False, "error": "toomany"}
    pairs = M * (M - 1) // 2
    counts = {"TN": M, "Te": N, "VeN": N * M, "Vee": N * (N - 1) // 2, "VNN": pairs}
    counts["total"] = N + N * M + N * (N - 1) // 2 + pairs
    zz = [[a, b, nuc[a]["Z"] * nuc[b]["Z"]] for a in range(M) for b in range(a + 1, M)] if pairs <= 6 else []
    return {"ok": True, "q": q, "nuc": nuc, "M": M, "Zs": Zs, "N": N, "counts": counts, "zz": zz}

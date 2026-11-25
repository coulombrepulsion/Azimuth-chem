"""Slater-Condon rules: matrix elements of the Hamiltonian between Slater determinants.

HEADER
    Model of the page "Правила Слейтера–Кондона" (v1.0 slater.js: align,
    ckey, add, element, iname, expr).  Wilkinson convention, sections 1-8.
    Symbolic: the result is a linear combination of one-electron integrals
    h_pq and two-electron integrals (pq|rs) over real spatial orbitals.

§1 THEORY
    For determinants |Psi> and |Psi'> of N spin-orbitals (Szabo and
    Ostlund, Modern Quantum Chemistry, table 2.3/2.4), after reordering the
    columns of Psi' for maximal coincidence (sign (-1)^inversions):
      0 differences:  sum_i h_ii + sum_{i<j} (<ij|ij> - <ij|ji>);
      1 (m -> p):     h_mp + sum_{n != m} (<mn|pn> - <mn|np>);
      2 (m->p, n->q): <mn|pq> - <mn|qp>;
      3 or more:      0 (H has at most two-electron operators).
    Spin integration: <ab|cd> = (ac|bd) delta(s_a, s_c) delta(s_b, s_d) in
    chemists' notation; a term vanishes unless the spins match.  Integrals
    over real orbitals have the 8-fold symmetry used by the canonical key
    (ab|cd) with a <= b, c <= d, (a, b) <= (c, d).

§2 ALGORITHM
    As v1.0: greedy alignment (first unused equal spin-orbital), the
    remaining columns in order; inversion count of the permutation; the
    coefficients accumulated in an insertion-ordered dict (entries whose
    coefficient cancels are removed, as `delete` in JS).

§3 APPLICATIONS
    Endpoint slater.element.

§4 SPECIFICATION
    element(A, B), A/B = [[orbital 1..K, 'α'|'β'], ...] ->
      {bad: 'N'} | {al: {B2, perm, inv, sign, diff}, nd, T: {key: int}, zero,
      notes: [{i: template 0..5, a: [labels]}], expr: html}
    keys 'h:p,q' and 'c:a,b|c,d'.  Exact (integer coefficients).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    expr orders the keys h before c, then by String.localeCompare
    (jsmath.locale_key).  The note texts are on the page; `i` selects the
    template, `a` fills its placeholders in order.
§7 TEST CASES (tests/test_slater.py)
    He 1s^2: 2h11 + J11; triplet phi1a phi2a: h11 + h22 + J12 - K12;
    <sg^2|H|su^2> = K12 (H2 CI); Brillouin case h12 + (11|12); three
    differences -> 0; permutation sign; vs v1.0 for the presets and random
    pairs.
§8 ERROR ANALYSIS
    Integer arithmetic; the |T| < 1e-12 test of v1.0 only removes exact
    cancellations.
"""
from __future__ import annotations

from .jsmath import locale_key


def _key(x):
    return f"{x[0]}{x[1]}"


def align(A, B):
    used = [False] * len(B)
    tgt = [None] * len(A)
    for k, x in enumerate(A):
        j = next((jj for jj, y in enumerate(B) if not used[jj] and x == y), -1)
        if j >= 0:
            used[j] = True
            tgt[k] = j
    rest = [j for j in range(len(B)) if not used[j]]
    r = 0
    for k in range(len(A)):
        if tgt[k] is None:
            tgt[k] = rest[r]
            r += 1
    inv = sum(1 for i in range(len(tgt)) for j in range(i + 1, len(tgt)) if tgt[i] > tgt[j])
    diff = [[x, B[tgt[k]]] for k, x in enumerate(A) if x != B[tgt[k]]]
    return {"B2": [B[j] for j in tgt], "perm": tgt, "inv": inv, "sign": -1 if inv % 2 else 1, "diff": diff}


def ckey(a, b, c, d) -> str:
    p, q = [min(a, b), max(a, b)], [min(c, d), max(c, d)]
    x, y = (p, q) if (p[0] < q[0] or (p[0] == q[0] and p[1] <= q[1])) else (q, p)
    return f"{x[0]},{x[1]}|{y[0]},{y[1]}"


def _add(T, k, v):
    T[k] = T.get(k, 0) + v
    if abs(T[k]) < 1e-12:
        del T[k]


def iname(k: str) -> str:
    if k[0] == "h":
        a, b = k[2:].split(",")
        return f"h<sub>{a}{b}</sub>"
    p, q = (list(map(int, x.split(","))) for x in k[2:].split("|"))
    if p[0] == p[1] and q[0] == q[1]:
        return f"J<sub>{p[0]}{q[0]}</sub>"
    if p[0] == q[0] and p[1] == q[1]:
        return f"K<sub>{p[0]}{p[1]}</sub>"
    return f"({p[0]}{p[1]}|{q[0]}{q[1]})"


def expr(T: dict) -> str:
    ks = sorted(T, key=lambda k: (0 if k[0] == "h" else 1, locale_key(k)))
    if not ks:
        return "0"
    out = []
    for i, k in enumerate(ks):
        v = T[k]
        a = abs(v)
        out.append((" + " if v > 0 else " − ") if i else ("−" if v < 0 else ""))
        out.append(("" if a == 1 else str(a)) + iname(k))
    return "".join(out)


def element(A, B) -> dict:
    A = [tuple(x) for x in A]
    B = [tuple(x) for x in B]
    if len(A) != len(B):
        return {"bad": "N"}
    if len(set(A)) != len(A) or len(set(B)) != len(B):
        return {"bad": "pauli"}      # 2.7.0: a spin-orbital twice in one determinant (it vanishes)
    al = align(A, B)
    nd = len(al["diff"])
    T: dict = {}
    S = al["sign"]
    notes = []
    if nd == 0:
        for x in A:
            _add(T, f"h:{x[0]},{x[0]}", S)
        for i in range(len(A)):
            for j in range(i + 1, len(A)):
                a, b = A[i], A[j]
                _add(T, "c:" + ckey(a[0], a[0], b[0], b[0]), S)
                if a[1] == b[1]:
                    _add(T, "c:" + ckey(a[0], b[0], b[0], a[0]), -S)
                else:
                    notes.append({"i": 0, "a": [_key(a), _key(b)]})
    elif nd == 1:
        m, p = al["diff"][0]
        if m[1] != p[1]:
            notes.append({"i": 1, "a": [_key(m), _key(p)]})
            return _out(al, nd, T, True, notes)
        _add(T, f"h:{min(m[0], p[0])},{max(m[0], p[0])}", S)
        for n in A:
            if n == m:
                continue
            _add(T, "c:" + ckey(m[0], p[0], n[0], n[0]), S)
            if n[1] == m[1]:
                _add(T, "c:" + ckey(m[0], n[0], n[0], p[0]), -S)
            else:
                notes.append({"i": 2, "a": [_key(n)]})
    elif nd == 2:
        (m, p), (n, q) = al["diff"]
        if m[1] == p[1] and n[1] == q[1]:
            _add(T, "c:" + ckey(m[0], p[0], n[0], q[0]), S)
        else:
            notes.append({"i": 3, "a": [_key(m), _key(n), _key(p), _key(q)]})
        if m[1] == q[1] and n[1] == p[1]:
            _add(T, "c:" + ckey(m[0], q[0], n[0], p[0]), -S)
        else:
            notes.append({"i": 4, "a": [_key(m), _key(n), _key(q), _key(p)]})
    else:
        return _out(al, nd, T, True, [{"i": 5, "a": []}])
    return _out(al, nd, T, len(T) == 0, notes)


def _out(al, nd, T, zero, notes):
    j = lambda xs: [list(x) for x in xs]  # noqa: E731
    al = {"B2": j(al["B2"]), "perm": al["perm"], "inv": al["inv"], "sign": al["sign"],
          "diff": [[list(a), list(b)] for a, b in al["diff"]]}
    return {"al": al, "nd": nd, "T": T, "zero": zero, "notes": notes, "expr": expr(T)}

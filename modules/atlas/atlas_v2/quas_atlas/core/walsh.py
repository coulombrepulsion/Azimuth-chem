"""Walsh diagram of AH2 molecules from a minimal one-electron (Hückel-type) model (Atlas).

HEADER
    Model of the page "Диаграммы Уолша: форма молекулы из орбиталей" (web/<lang>/walsh.html).
    Wilkinson convention, sections 1-8.

§1 THEORY
    Walsh (1953): the shape of a molecule follows the sum of the energies of its occupied valence orbitals as a
    function of the geometry. For AH₂ the basis is the s and p orbitals of A and the two H 1s; on bending from
    180° the 1πu pair splits: 1b1 (pz ⟂ plane) stays non-bonding, 2a1 (in-plane p plus s) is stabilised a lot;
    1b2 (σu) is destabilised a little, 1a1 (σg) slightly stabilised. Four valence electrons (BeH₂) fill only
    1a1 and 1b2 — the molecule is linear; from five electrons (BH₂) on, 2a1 is occupied and the molecule bends.
    One-electron Hamiltonian (eV), A at the origin, H at (0, ±sin θ/2, cos θ/2), bond length fixed:
        H_ss = α_s, H_pp = α_p, H_HH = α_H; H_sH = β_s; H_pH = β_p·(cosine of the angle between p and A–H);
        H_H1H2 = β_HH·exp(−2(d_HH/r − 1)), d_HH/r = 2 sin(θ/2).
    Parameters (fitted to give BeH₂ linear and H₂O ≈ 102°): α_s = −21, α_p = −13, α_H = −13.6, β_s = −6,
    β_p = −7, β_HH = −0.6 eV. The model is qualitative: no electron repulsion, fixed bond length.

§2 ALGORITHM
    θ from 80° to 180° step 1°; eigenvectors of the 6x6 H (core.smallmat.eig_sym) labelled by C2v symmetry
    (b1 — weight on p_x; b2 — weight on p_y or on H1 − H2; a1 — the rest) and numbered within each symmetry;
    Walsh energy E(θ) = Σ n_i ε_i(θ) with aufbau occupations; the predicted angle is the minimum of E on the grid,
    refined by a parabola through the three lowest points.

§3 APPLICATIONS
    Endpoint walsh.diagram.

§4 SPECIFICATION
    diagram(ne) -> {"theta": [...], "orbitals": {label: [ε]}, "E": [...], "best": angle, "occ": {label: n at best}}
    for ne = 2..8 valence electrons.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Labels at 180°: 1a1 → σg, 1b2 → σu, 2a1 and 1b1 → πu.
§7 TEST CASES (tests/test_atlas_course1.py)
    ne = 4: linear (180°); ne = 5: 125–140°; ne = 8: 95–110°; 2a1 decreases and 1b2 increases on bending,
    1b1 is constant (α_p); at 180° 2a1 and 1b1 are degenerate.
§8 ERROR ANALYSIS
    6x6 symmetric eigenproblem, 1e-12; the model error (parameters, no repulsion) dominates: angles to ~10°.
"""
from __future__ import annotations

import math

from .smallmat import eig_sym

P = {"a_s": -21.0, "a_p": -13.0, "a_h": -13.6, "b_s": -6.0, "b_p": -7.0, "b_hh": -0.6}


def hamiltonian(theta: float) -> list:
    t = math.radians(theta / 2)
    H = [[0.0] * 6 for _ in range(6)]
    for i, a in enumerate([P["a_s"], P["a_p"], P["a_p"], P["a_p"], P["a_h"], P["a_h"]]):
        H[i][i] = a
    for k, (y, z) in enumerate([(math.sin(t), math.cos(t)), (-math.sin(t), math.cos(t))]):
        j = 4 + k
        H[0][j] = H[j][0] = P["b_s"]
        for ip, c in ((1, 0.0), (2, y), (3, z)):
            H[ip][j] = H[j][ip] = P["b_p"] * c
    d = 2 * math.sin(t)
    H[4][5] = H[5][4] = P["b_hh"] * math.exp(-2.0 * (d - 1.0))
    return H


def levels(theta: float) -> list:
    """[(label, energy)] sorted by energy."""
    w, V = eig_sym(hamiltonian(theta))
    out = []
    for m in range(6):
        c = [V[i][m] for i in range(6)]
        if c[1] ** 2 > 0.5:
            s = "b1"
        elif c[2] ** 2 + (c[4] - c[5]) ** 2 / 2 > 0.5:
            s = "b2"
        else:
            s = "a1"
        out.append((s, w[m]))
    out.sort(key=lambda x: x[1])
    count, lab = {}, []
    for s, e in out:
        count[s] = count.get(s, 0) + 1
        lab.append((f"{count[s]}{s}", e))
    return lab


def _walsh(lv, ne):
    E, n, occ = 0.0, ne, {}
    for lb, e in lv:
        take = min(2, n)
        if take <= 0:
            break
        E += take * e
        occ[lb] = take
        n -= take
    return E, occ


def diagram(ne: int) -> dict:
    if not 2 <= ne <= 8:
        raise ValueError("2..8 valence electrons")
    th = list(range(80, 181))
    orbs: dict = {}
    Es = []
    for t in th:
        lv = levels(t)
        for lb, e in lv:
            orbs.setdefault(lb, []).append(e)
        Es.append(_walsh(lv, ne)[0])
    i = min(range(len(th)), key=lambda k: Es[k])
    best = float(th[i])
    if 0 < i < len(th) - 1:
        a, b, c = Es[i - 1], Es[i], Es[i + 1]
        den = a - 2 * b + c
        if den > 0:
            best = th[i] + 0.5 * (a - c) / den
    return {"theta": th, "orbitals": orbs, "E": Es, "best": best, "occ": _walsh(levels(round(best)), ne)[1]}

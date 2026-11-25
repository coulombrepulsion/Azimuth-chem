"""Defects and surfaces of crystals: vacancies, charged defects, the supercell, the slab.

HEADER
    Model of the page "Дефекты и поверхности" (web/<lang>/defects.html), Atlas 2026-11-24; lecture 15 of the course
    «Квантово-химические методы» (its derivations 1, 2, 4, 5, 6). Wilkinson convention, sections 1-8.

§1 THEORY
    A vacancy: N atoms of a supercell, one removed; the atom went to the surface of the crystal, so the cell with the
    vacancy is compared with as many atoms of the perfect crystal:  E_f = E_{N−1} − (N − 1)/N · E_N.  With all the
    energy in bonds (ε per bond, four bonds per atom of Si, each shared by two) E_f = 4ε − 2ε = 2ε. The vacancy
    costs E_f but can sit on any site (entropy): at equilibrium c = n_vac/n_sites = e^{−E_f/kT}; Si, E_f = 3.6 eV:
    2·10⁻¹¹ at the melting point 1687 K, e^{−139} at 300 K. An error δ of E_f is a factor e^{δ/kT} in c.
    A charged defect exchanges electrons with a reservoir at the Fermi level E_F (counted from the top of the valence
    band):  E_f(q; E_F) = E_f(q; 0) + q·E_F — a line of slope q for every charge. Where two lines cross the defect
    changes its charge: ε(q/q′) = (E_f(q; 0) − E_f(q′; 0))/(q′ − q). Below ε(+/0) the defect is a donor (+), above
    ε(0/−) an acceptor (−); if ε(+/0) > ε(0/−) the neutral state is never the lowest (a «negative U» defect) and the
    charge goes from + to − at ε(+/−).
    A charge q in a cubic supercell of edge L, repeated, on the compensating background, screened by ε_r: the first
    term of Makov and Payne  ΔE ≈ q²α/(2ε_r L)·14.4 eV·Å, α = 2.8373 (simple cubic). Si, q = 1, 64 atoms (L = 10.9 Å):
    0.16 eV; it falls as 1/L — slowly.
    A surface: a slab of N layers, E_slab(N) = N·E_bulk + 2Aγ (two surfaces of area A). Breaking bonds: n broken bonds
    per surface atom, ε/2 to each new surface: γ ≈ n·(ε/2)/A_atom. Si (ε = 2.17 eV of the model potential):
    (111) one bond, A = √3/4·a² = 12.8 Å², γ = 0.085 eV/Å² = 1.36 J/m²; (100) two bonds, A = a²/2 = 14.7 Å², γ = 2.36 J/m²;
    (100) after the optimization the surface atoms pair (dimers, period doubled): 1.44 J/m² (lecture 15, slide 11).
    With E_bulk taken from a separate calculation with an error δ (other k-meshes) γ is off by Nδ/(2A) — it grows with
    the thickness; the slope of E_slab(N) gives E_bulk consistent with the slabs and γ from the intercept.

§2 ALGORITHM
    The formulas above. The slab: E_slab(N) = N·E_bulk + 2Aγ + a fixed pseudo-random noise (the convergence of each
    calculation); γ from the external bulk energy E_bulk + δ, and γ from the straight line through the slabs up to N
    (least squares; from three slabs on).

§3 APPLICATIONS
    Endpoints def.vacancy, def.charged, def.slab.

§4 SPECIFICATION
    vacancy(ef, T, sites=5.0e22, err=0.3) -> {"c", "per_cm3", "one_in", "factor", "curve": {"T", "log10c", "lo", "hi"},
        "melt": {"T", "c"}}  (sites per cm³; err — the error of E_f, eV).
    charged(e_plus, e_zero, e_minus, gap) -> {"lines": {"+": [E], "0": [E], "−": [E]}, "ef": [E_F], "lowest": [E],
        "levels": [{"label", "at"}], "stable": [{"from", "to", "q"}]}.
    supercell(q, eps, a=5.431, base=8) -> {"rows": [{"atoms", "L", "dE"}]}  (cubic supercells of 2³…6³ cells).
    slab(face, delta, noise, n_max) -> {"gamma" (J/m²), "A", "bonds", "N": [n], "E": [eV], "ext": [J/m²],
        "fit": [J/m² or None], "err_formula": [J/m²]}  (delta, noise in meV).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (the site runs it in Pyodide). 1 eV/Å² = 16.0218 J/m².
§7 TEST CASES (tests/atlas/test_atlas_defects.py)
    The numbers of the lecture: c(3.6 eV, 1687 K) = e^{−24.8} ≈ 2·10⁻¹¹; ε(+/0) = 0.5 and ε(0/−) = 0.9 eV for
    2.9, 3.4, 4.3 eV; ΔE = 0.16 eV for Si, q = 1, 64 atoms, 0.11 eV for 216; γ(111) = 1.36, γ(100) = 2.36 J/m²;
    Δγ = Nδ/(2A).
§8 ERROR ANALYSIS
    The models are those of the lecture: no vibrational entropy of formation, the first Makov–Payne term only, the
    bonds of nearest neighbours only.
"""

import math

K_B = 8.617333262e-5  # eV/K
EV_A2_J_M2 = 16.0217663  # 1 eV/Å² in J/m²
MADELUNG_SC = 2.8373
COULOMB = 14.399645  # e²/(4πε0) in eV·Å
SI_A = 5.431  # Å
SI_BOND = 2.17  # eV, ε of the model potential of the lecture (2ε = 4.34 eV)
FACES = {  # broken bonds per surface atom, area per surface atom (Å²), γ (J/m²) when not from the bonds
    '111': {'bonds': 1, 'A': math.sqrt(3) / 4 * SI_A ** 2},
    '100': {'bonds': 2, 'A': SI_A ** 2 / 2},
    '100r': {'bonds': 2, 'A': SI_A ** 2 / 2, 'gamma': 1.44},  # (100) with dimers, after the optimization
}


def vacancy(ef=3.6, T=1687.0, sites=5.0e22, err=0.3):
    """The equilibrium share of vacancies e^{−E_f/kT}, per cm³, «one in» how many sites, the factor of an error of E_f;
    log10 c against T (300–2000 K) for E_f and E_f ± err."""
    if not (0.1 <= ef <= 8 and 100 <= T <= 3000):
        raise ValueError("E_f 0.1..8 eV, T 100..3000 K")
    x = ef / (K_B * T)
    log10c = -x / math.log(10)
    ts = [300 + 10 * i for i in range(171)]
    curve = {"T": ts, "log10c": [-ef / (K_B * t) / math.log(10) for t in ts],
             "lo": [-(ef - err) / (K_B * t) / math.log(10) for t in ts],
             "hi": [-(ef + err) / (K_B * t) / math.log(10) for t in ts]}
    c = 10 ** log10c if log10c > -300 else 0.0
    return {"c": c, "log10c": log10c, "x": x, "per_cm3": c * sites, "one_in": 10 ** (-log10c),
            "factor": math.exp(err / (K_B * T)), "curve": curve,
            "melt": {"T": 1687.0, "c": math.exp(-ef / (K_B * 1687.0))}}


def charged(e_plus=2.9, e_zero=3.4, e_minus=4.3, gap=1.17, n=121):
    """The lines E_f(q; E_F) of the charges +1, 0, −1 over the gap, the lowest of them, the transition levels."""
    if not (0.2 <= gap <= 6 and all(-2 <= e <= 10 for e in (e_plus, e_zero, e_minus))):
        raise ValueError("gap 0.2..6 eV, energies −2..10 eV")
    at0 = {1: e_plus, 0: e_zero, -1: e_minus}
    names = {1: '+', 0: '0', -1: '−'}
    efs = [gap * i / (n - 1) for i in range(n)]
    lines = {names[q]: [at0[q] + q * x for x in efs] for q in at0}

    def best(x):
        return min(at0, key=lambda q: (at0[q] + q * x, -q))

    lowest = [min(at0[q] + q * x for q in at0) for x in efs]
    # the charge on the lowest line, walked from the top of the valence band up; a change is a transition level
    stable, levels = [], []
    q = best(0.0)
    start = 0.0
    while True:
        later = [(at0[r] - at0[q]) / (q - r) for r in at0 if r < q]  # where a lower charge crosses q
        later = [(x, r) for x, r in zip(later, [r for r in at0 if r < q]) if x > start + 1e-12]
        if not later:
            stable.append({"from": start, "to": gap, "q": names[q]})
            break
        x, r = min(later, key=lambda p: (p[0], -p[1]))  # the first crossing; at a tie the farther charge
        if x >= gap:
            stable.append({"from": start, "to": gap, "q": names[q]})
            break
        stable.append({"from": start, "to": x, "q": names[q]})
        levels.append({"label": f"{names[q]}/{names[r]}", "at": x})
        q, start = r, x
    return {"ef": efs, "lines": lines, "lowest": lowest, "levels": levels, "stable": stable,
            "pairs": {"+/0": e_zero - e_plus, "0/−": e_minus - e_zero}}


def supercell(q=1, eps=11.7, a=SI_A, base=8):
    """The first Makov–Payne term q²α/(2εL)·14.4 eV·Å for cubic supercells of 2³…6³ cells of `base` atoms."""
    if not (1 <= abs(q) <= 3 and 1 <= eps <= 100):
        raise ValueError("|q| 1..3, ε 1..100")
    rows = []
    for m in range(2, 7):
        L = a * m
        rows.append({"atoms": base * m ** 3, "L": L, "dE": q * q * MADELUNG_SC * COULOMB / (2 * eps * L)})
    return {"rows": rows}


def _lcg(seed, n):
    state = seed * 2654435761 % 2 ** 32 or 1
    out = []
    for _ in range(n):
        state = (1103515245 * state + 12345) % 2 ** 31
        out.append(state / 2 ** 31 * 2 - 1)
    return out


def slab(face="111", delta=5.0, noise=1.0, n_max=16, seed=3):
    """E_slab(N) of Si slabs of 2…n_max layers (one atom per layer in the surface cell) with a noise of up to noise meV;
    γ from a separate bulk energy off by delta meV, and γ from the line through the slabs; J/m²."""
    if face not in FACES or not (0 <= abs(delta) <= 50 and 0 <= noise <= 20 and 4 <= n_max <= 30):
        raise ValueError("face 111 | 100 | 100r, delta 0..50 meV, noise 0..20 meV, n_max 4..30")
    f = FACES[face]
    A = f['A']
    gamma = f.get('gamma', f['bonds'] * SI_BOND / 2 / A * EV_A2_J_M2)  # J/m²
    g = gamma / EV_A2_J_M2  # eV/Å²
    bulk = -2 * SI_BOND
    ns = list(range(2, n_max + 1))
    shake = _lcg(seed, len(ns))
    energies = [n * bulk + 2 * A * g + s * noise / 1000 for n, s in zip(ns, shake)]
    ext = [(e - n * (bulk + delta / 1000)) / (2 * A) * EV_A2_J_M2 for n, e in zip(ns, energies)]
    fit = []
    for j in range(len(ns)):
        xs, ys = ns[:j + 1], energies[:j + 1]
        if len(xs) < 3:
            fit.append(None)
            continue
        mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
        slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
        fit.append((my - slope * mx) / (2 * A) * EV_A2_J_M2)
    return {"gamma": gamma, "A": A, "bonds": f['bonds'], "N": ns, "E": energies, "ext": ext, "fit": fit,
            "err_formula": [-n * delta / 1000 / (2 * A) * EV_A2_J_M2 for n in ns], "bulk": bulk}

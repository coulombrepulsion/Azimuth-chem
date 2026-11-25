"""Solids: the Bloch theorem, k-points and plane waves; bands and the density of states.

HEADER
    Model of the pages "Теорема Блоха и k-точки" (web/<lang>/bloch.html) and "Зонная структура и плотность
    состояний" (web/<lang>/bands.html), Atlas 2026-11-24. Wilkinson convention, sections 1-8.

§1 THEORY
    Bloch: in a potential with the period a of the lattice every one-electron state can be chosen as
        ψ_k(x + a) = e^{ika} ψ_k(x),   ψ_k(x) = e^{ikx} u_k(x),  u periodic;
    k and k + G (G = 2πm/a) give the same state on the lattice, so k is taken in the first Brillouin zone
    −π/a < k ≤ π/a. A chain of atoms with one orbital each (energy α, hopping β to a neighbour) has one band
        E(k) = α + 2β cos(ka),   width 4|β|.
    A chain of two atoms per cell (on-site ±Δ/2, hoppings β1 inside the cell and β2 to the next one) has two:
        E±(k) = ±sqrt(Δ²/4 + β1² + β2² + 2β1β2 cos(ka));   the gap at k = π/a is 2·sqrt(Δ²/4 + (β1 − β2)²).
    The share of atom A in a state of energy E of H = [[h, f], [f*, −h]] (h = Δ/2) is |c_A|² = (E + h)/(2E):
    the upper band lies on the atom of the higher on-site energy (the PDOS of a calculation shows the same).
    Graphene (one pz per atom, two atoms per cell, nearest neighbours β): E = ±sqrt(Δ²/4 + β²|1 + e^{ik·a1} +
    e^{ik·a2}|²) — at Γ ±3|β|, at M ±|β|, at K ±Δ/2: with Δ = 0 the bands touch (the Dirac cone), with Δ ≠ 0
    (two different atoms, as B and N) a gap Δ opens. β ≈ −2.8 eV (Castro Neto et al., Rev. Mod. Phys. 81, 109, 2009).
    Integrals over the zone are sums over a mesh of k-points: the energy per cell of a full band (an insulator)
    converges with the mesh exponentially, a band cut by the Fermi level (a metal) slowly — this is why metals
    need denser meshes or a smearing. The half-filled chain has the exact band energy −4|β|/π per atom.
    Plane waves: an orbital of a crystal is a sum of e^{i(k+G)·r} over the reciprocal vectors G with
    |k + G|²/2 ≤ E_cut (hartree; in Ry |k + G|² ≤ E_cut with lengths in bohr). Their number at Γ is about
    N ≈ V·G_max³/(6π²), G_max = sqrt(E_cut[Ry]) — the volume of the sphere over the volume of a reciprocal cell.
    The density needs four times the cutoff (eight for ultrasoft pseudopotentials): eight to 23 times more vectors.
    Nearly free electrons: in V(x) = 2V cos(2πx/a) the plane waves e^{i(k+G)x} are mixed by V; on the boundary
    of the zone the two waves of equal energy split by 2|V| — the band gap of the first order.

§2 ALGORITHM
    chain / pair / graphene: the formulas above on a grid of k; the density of states — the eigenvalues of a fine
    mesh, each a Gaussian of width σ (the DOS of a cell integrates to the number of bands; the PDOS of A and B
    to their shares). The Fermi level: the states of the mesh sorted, filled with the electrons (two per state).
    k-mesh: Γ-centred mesh k_j = 2πj/n, j = 0…n − 1; the energy per cell is (2/n)·Σ of the filled states (the
    last one filled in part when the electrons do not fill it whole). The square mesh of the plane: the n × n
    points (shifted by half a step or not), the operations of the square (C4v with time reversal) join equal
    points; the weight of a point is the number of the points it stands for.
    plane waves: every G = m1·b1 + m2·b2 + m3·b3 with |m_i| ≤ G_max|a_i|/(2π) counted when |G|² ≤ E_cut.
    nearly free electrons: the plane waves m = −M…M, H_mm = (k + 2πm)² (units ħ²/(2m a²), a = 1),
    H_m,m±1 = V; a symmetric tridiagonal matrix, its eigenvalues by bisection with the Sturm sequence.

§3 APPLICATIONS
    Endpoints sol.wave, sol.mesh, sol.mesh2d, sol.pw, sol.pair, sol.graphene, sol.nfe.

§4 SPECIFICATION
    wave(k, m, beta) -> {"k", "E", "band": {k, E}, "x", "re", "re_g", "sites": [{x, re}]}  (k in units π/a).
    mesh(kind, n_max, delta, beta) -> {"rows": [{"n", "E", "err"}], "exact"}  kind 'metal' | 'insulator'.
    mesh2d(n, shift) -> {"points": [[kx, ky]], "irreducible": [{"k", "w"}]}  (fractions of 2π/a).
    plane_waves(cell (3×3 Å), ecut (Ry)) -> {"V" (bohr³), "N", "N_est", "N_rho4", "N_rho8"}.
    pair(delta, b1, b2, electrons, sigma) -> {"k", "lower", "upper", "E", "dos", "pdos_a", "pdos_b", "ef", "gap",
        "metal"}.
    graphene(delta, beta, sigma) -> {"x", "lower", "upper", "ticks", "E", "dos", "gap"}.
    nfe(V, M) -> {"k", "bands": [[E]], "gaps": [{"k", "gap"}]}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (the site runs it in Pyodide). Energies of the chain and of graphene are in the units
    of their β (eV for graphene); of the nearly free electrons in ħ²/(2m a²).
§7 TEST CASES (tests/atlas/test_atlas_solids.py)
    The plane waves of the Si cell of tests/data/qe/si_bands.in: 5985 vectors at 120 Ry and 16889 at 240 Ry —
    the smooth and the dense grid of Quantum ESPRESSO 7.6 in si_bands_pw76.out; the half-filled chain → −4|β|/π;
    graphene ±3|β| at Γ, ±|β| at M, 0 at K; the gap of the pair 2·sqrt(Δ²/4 + (β1 − β2)²); |c_A|² = 1/2 when Δ = 0;
    the nearly free electrons: gap → 2|V| for a weak V; the square 4 × 4 mesh — 3 points shifted, 6 not.
§8 ERROR ANALYSIS
    The models are exact for themselves; the broadening σ smooths the van Hove peaks of the DOS (the chain has
    1/sqrt singularities at its band edges). The bisection stops at 1e-12 of the spread of the spectrum.
"""
import math

BOHR = 0.529177210903  # Å (CODATA 2018)

# the cells of plane_waves (Å): Si as the cell of tests/data/qe/si_bands.in (a = 5.431 Å, primitive fcc);
# NaCl (a = 5.640 Å) and Cu (a = 3.615 Å) primitive fcc cells
def _fcc(a):
    h = a / 2
    return [[0.0, h, h], [h, 0.0, h], [h, h, 0.0]]


CELLS = {
    "si": [[3.84029693, 0.0, 0.0], [1.92014846, 3.32579470, 0.0], [1.92014846, 1.10859823, 3.13558931]],
    "nacl": _fcc(5.640),
    "cu": _fcc(3.615),
}


# ---- the Bloch wave on a chain ----
def wave(k, m=0, beta=-1.0, sites=6, per=24):
    """k in units of π/a (−1…1), m — the reciprocal vector added (k + 2m): the same Bloch state on the sites."""
    if not -1 <= k <= 1:
        raise ValueError("k must be in the first zone: −1…1 (π/a)")
    kk, kg = math.pi * k, math.pi * (k + 2 * m)
    xs = [i / per for i in range(-sites * per, sites * per + 1)]
    band = [j / 100 for j in range(-100, 101)]
    return {
        "k": k, "E": 2 * beta * math.cos(kk),
        "band": {"k": band, "E": [2 * beta * math.cos(math.pi * q) for q in band]},
        "x": xs, "re": [math.cos(kk * x) for x in xs], "re_g": [math.cos(kg * x) for x in xs],
        "sites": [{"x": n, "re": math.cos(kk * n)} for n in range(-sites, sites + 1)],
    }


# ---- k-meshes ----
def _pair_bands(delta, b1, b2, q):
    s = math.sqrt(max(delta * delta / 4 + b1 * b1 + b2 * b2 + 2 * b1 * b2 * math.cos(q), 0.0))
    return -s, s


def _band_energy(levels, electrons):
    """Two electrons per state, the lowest first; the last state filled in part."""
    total, left = 0.0, electrons
    for e in sorted(levels):
        take = min(2.0, left)
        if take <= 0:
            break
        total += take * e
        left -= take
    return total


def mesh(kind="metal", n_max=24, delta=1.0, beta=-1.0):
    """The band energy per cell with the Γ-centred mesh of n = 1…n_max points: a half-filled chain (a metal,
    one electron per atom) or a full lower band of a two-atom chain with on-site ±Δ/2 (an insulator)."""
    if kind not in ("metal", "insulator") or not 1 <= n_max <= 200:
        raise ValueError("kind: metal | insulator; n_max 1..200")

    def energy(n):
        qs = [2 * math.pi * j / n for j in range(n)]
        if kind == "metal":
            return _band_energy([2 * beta * math.cos(q) for q in qs], n) / n
        return sum(2 * _pair_bands(delta, beta, beta, q)[0] for q in qs) / n

    if kind == "metal":
        exact = -4 * abs(beta) / math.pi
    else:  # the integral of a smooth periodic function: the trapezoid rule of many points is exact to rounding
        exact = energy(4096)
    rows = []
    for n in range(1, n_max + 1):
        e = energy(n)
        rows.append({"n": n, "E": e, "err": e - exact})
    return {"rows": rows, "exact": exact, "kind": kind}


def mesh2d(n=4, shift=True):
    """The n × n mesh of a square lattice (fractions of 2π/a in −1/2…1/2) and its points that differ by the
    symmetry of the square: C4v with time reversal (k ≡ −k), the weights summing to n²."""
    if not 1 <= n <= 24:
        raise ValueError("n 1..24")
    off = 0.5 if shift else 0.0
    def fold(v):
        v = (v + 0.5) % 1.0 - 0.5
        return 0.5 if abs(v + 0.5) < 1e-12 else round(v, 12)
    points = [[fold((i + off) / n), fold((j + off) / n)] for i in range(n) for j in range(n)]
    groups = {}
    for x, y in points:
        images = []
        for a, b in ((x, y), (y, x)):
            for sa in (1, -1):
                for sb in (1, -1):
                    images.append((fold(sa * a), fold(sb * b)))
        key = max(images)  # the image with kx ≥ ky ≥ 0
        groups.setdefault(key, 0)
        groups[key] += 1
    irreducible = [{"k": list(k), "w": w} for k, w in sorted(groups.items())]
    return {"points": points, "irreducible": irreducible, "n": n, "shift": shift}


# ---- plane waves ----
def _cross(u, v):
    return [u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0]]


def _dot(u, v):
    return u[0] * v[0] + u[1] * v[1] + u[2] * v[2]


def _count(a, b, ecut):
    g = math.sqrt(ecut)
    lim = [int(g * math.sqrt(_dot(v, v)) / (2 * math.pi)) + 1 for v in a]
    n = 0
    for i in range(-lim[0], lim[0] + 1):
        for j in range(-lim[1], lim[1] + 1):
            x0 = [i * b[0][t] + j * b[1][t] for t in range(3)]
            for k in range(-lim[2], lim[2] + 1):
                x = x0[0] + k * b[2][0]
                y = x0[1] + k * b[2][1]
                z = x0[2] + k * b[2][2]
                if x * x + y * y + z * z <= ecut:
                    n += 1
    return n


def plane_waves(cell, ecut, dense=True):
    """The plane waves of an orbital at Γ (|G|² ≤ E_cut, Ry and bohr) of the cell (rows a1, a2, a3 in Å), the
    estimate V·G_max³/(6π²), and the vectors of the density at 4·E_cut and at 8·E_cut."""
    if not 1 <= ecut <= 200:
        raise ValueError("E_cut 1..200 Ry")
    a = [[x / BOHR for x in v] for v in cell]
    V = _dot(a[0], _cross(a[1], a[2]))
    if abs(V) < 1e-6:
        raise ValueError("the cell vectors are in one plane")
    V = abs(V)
    b = [[2 * math.pi * x / V for x in _cross(a[(i + 1) % 3], a[(i + 2) % 3])] for i in range(3)]
    if _dot(b[0], a[0]) < 0:
        b = [[-x for x in v] for v in b]
    est = lambda e: V * e ** 1.5 / (6 * math.pi ** 2)
    out = {"V": V, "N": _count(a, b, ecut), "N_est": est(ecut), "ecut": ecut}
    if dense:
        out["N_rho4"] = _count(a, b, 4 * ecut)
        out["N_rho8"] = _count(a, b, 8 * ecut) if 8 * ecut <= 600 else round(est(8 * ecut))
    return out


# ---- bands and the density of states ----
def _gauss(levels, weights, grid, sigma, norm):
    c = 1 / (sigma * math.sqrt(2 * math.pi) * norm)
    out = [0.0] * len(grid)
    for e, w in zip(levels, weights):
        for i, x in enumerate(grid):
            d = (x - e) / sigma
            if d * d < 40:
                out[i] += w * c * math.exp(-0.5 * d * d)
    return out


def pair(delta=0.0, b1=-1.0, b2=-1.0, electrons=2.0, sigma=0.08, nk=101, nmesh=600, ne=241):
    """The two bands of a chain of two atoms per cell along −π/a…π/a, the DOS and the PDOS of the atoms (A has the
    on-site +Δ/2), the Fermi level for the electrons per cell, the gap."""
    if not 0 <= electrons <= 4 or not 0.005 <= sigma <= 2:
        raise ValueError("electrons 0..4, σ 0.005..2")
    ks = [-1 + 2 * j / (nk - 1) for j in range(nk)]
    lo, up = zip(*(_pair_bands(delta, b1, b2, math.pi * q) for q in ks))
    h = delta / 2
    levels, wa = [], []
    qs = [2 * math.pi * (j + 0.5) / nmesh for j in range(nmesh)]
    for q in qs:
        for e in _pair_bands(delta, b1, b2, q):
            levels.append(e)
            wa.append(0.5 if abs(e) < 1e-12 else (e + h) / (2 * e))
    top = max(abs(x) for x in up) + 4 * sigma + 0.2
    grid = [-top + 2 * top * i / (ne - 1) for i in range(ne)]
    dos = _gauss(levels, [1.0] * len(levels), grid, sigma, nmesh)
    pa = _gauss(levels, wa, grid, sigma, nmesh)
    pb = [t - x for t, x in zip(dos, pa)]
    vbm, cbm = max(lo), min(up)
    gap = max(cbm - vbm, 0.0)
    # the states of the mesh filled by the electrons (two per state): f states of 2·nmesh
    order = sorted(levels)
    f = electrons * nmesh / 2
    if f <= 1e-9:
        ef, metal = order[0], False
    elif f >= len(order) - 1e-9:
        ef, metal = order[-1], False
    elif abs(f - nmesh) < 1e-9 and gap > 1e-6:
        ef, metal = (vbm + cbm) / 2, False  # the lower band full: the level in the middle of the gap
    else:
        ef, metal = order[min(math.ceil(f - 1e-9), len(order)) - 1], True
    return {"k": ks, "lower": list(lo), "upper": list(up), "E": grid, "dos": dos, "pdos_a": pa, "pdos_b": pb,
            "ef": ef, "gap": gap, "metal": metal, "vbm": vbm, "cbm": cbm}


def _graphene_e(delta, beta, kx, ky):
    # a1 = (1, 0), a2 = (1/2, √3/2) in units of a; k in units of 1/a
    re = 1 + math.cos(kx) + math.cos(kx / 2 + ky * math.sqrt(3) / 2)
    im = math.sin(kx) + math.sin(kx / 2 + ky * math.sqrt(3) / 2)
    s = math.sqrt(delta * delta / 4 + beta * beta * (re * re + im * im))
    return -s, s


def graphene(delta=0.0, beta=-2.8, sigma=0.12, nseg=60, nmesh=90, ne=241):
    """Graphene (Δ = 0) or a hexagonal sheet of two different atoms (Δ ≠ 0, as h-BN) in the model of one pz
    orbital per atom: the bands along Γ–M–K–Γ and the DOS of the whole zone."""
    if not 0.01 <= sigma <= 2 or not -10 <= beta < 0:
        raise ValueError("σ 0.01..2, β −10..0")
    s3 = math.sqrt(3)
    G, M, K = (0.0, 0.0), (math.pi, math.pi / s3), (4 * math.pi / 3, 0.0)
    legs = ((G, M), (M, K), (K, G))
    xs, lo, up, ticks, x0 = [], [], [], [0.0], 0.0
    for p, q in legs:
        length = math.dist(p, q)
        for j in range(nseg + (1 if q is G else 0)):
            t = j / nseg
            kx, ky = p[0] + t * (q[0] - p[0]), p[1] + t * (q[1] - p[1])
            e1, e2 = _graphene_e(delta, beta, kx, ky)
            xs.append(x0 + t * length)
            lo.append(e1)
            up.append(e2)
        x0 += length
        ticks.append(x0)
    # the zone sampled by the reciprocal cell b1 = 2π(1, −1/√3), b2 = 2π(0, 2/√3)
    levels = []
    for i in range(nmesh):
        for j in range(nmesh):
            u, v = (i + 0.5) / nmesh, (j + 0.5) / nmesh
            kx, ky = 2 * math.pi * u, 2 * math.pi * (-u / s3 + 2 * v / s3)
            levels.extend(_graphene_e(delta, beta, kx, ky))
    top = 3 * abs(beta) + 4 * sigma + 0.3
    grid = [-top + 2 * top * i / (ne - 1) for i in range(ne)]
    dos = _gauss(levels, [1.0] * len(levels), grid, sigma, nmesh * nmesh)
    gap = abs(delta)
    return {"x": xs, "lower": lo, "upper": up, "ticks": ticks, "labels": ["Γ", "M", "K", "Γ"], "E": grid,
            "dos": dos, "gap": gap}


def _sturm_count(d, e, x):
    """How many eigenvalues of the symmetric tridiagonal matrix (diagonal d, off-diagonal e) are below x."""
    count, q = 0, 1.0
    for i in range(len(d)):
        q = d[i] - x - (e[i - 1] ** 2 / q if i else 0.0)
        if q == 0.0:
            q = 1e-300
        if q < 0:
            count += 1
    return count


def _tridiag_eigs(d, e, how_many):
    lo = min(d) - 2 * max([abs(x) for x in e] + [0.0]) - 1
    hi = max(d) + 2 * max([abs(x) for x in e] + [0.0]) + 1
    tol = 1e-12 * (hi - lo)
    out = []
    for n in range(how_many):
        a, b = lo, hi
        while b - a > tol:
            m = (a + b) / 2
            if _sturm_count(d, e, m) > n:
                b = m
            else:
                a = m
        out.append((a + b) / 2)
    return out


def nfe(V=0.3, M=3, nk=81, bands=4):
    """Nearly free electrons in V(x) = 2V cos(2πx/a): the lowest bands over −π/a…π/a with 2M + 1 plane waves
    (energies in ħ²/(2m a²)), and the gaps at the centre and at the boundary of the zone."""
    if not 0 <= abs(V) <= 20 or not 0 <= M <= 20:
        raise ValueError("|V| ≤ 20, M 0..20")
    bands = min(bands, 2 * M + 1)
    ks = [-1 + 2 * j / (nk - 1) for j in range(nk)]
    out = [[] for _ in range(bands)]
    for q in ks:
        d = [(math.pi * (q + 2 * m)) ** 2 for m in range(-M, M + 1)]
        es = _tridiag_eigs(d, [V] * (len(d) - 1), bands)
        for i, x in enumerate(es):
            out[i].append(x)
    gaps = []
    for q in (1.0, 0.0):
        d = [(math.pi * (q + 2 * m)) ** 2 for m in range(-M, M + 1)]
        es = _tridiag_eigs(d, [V] * (len(d) - 1), bands)
        for i in range(bands - 1):
            if (q == 1.0 and i % 2 == 0) or (q == 0.0 and i % 2 == 1):
                gaps.append({"k": q, "between": [i + 1, i + 2], "gap": es[i + 1] - es[i]})
    return {"k": ks, "bands": out, "gaps": sorted(gaps, key=lambda g: g["between"]), "V": V, "M": M}


# ---- properties of crystals: the equation of state, phonons, heat capacity ----
# (the page «Свойства кристаллов: сжатие и фононы», web/<lang>/solidprops.html)
EV_A3_GPA = 160.21766208  # 1 eV/Å³ in GPa
# reference values (≈): V0 (Å³ per atom or per formula unit), B0 (GPa), B0' — Kittel, Introduction to Solid State
# Physics (8th ed., tables of the elastic constants and bulk moduli); MgO — the usual B0 ≈ 160 GPa
EOS_PRESETS = {
    'al': {'V0': 16.60, 'B0': 72.2, 'Bp': 4.5, 'per': 'atom'},
    'cu': {'V0': 11.81, 'B0': 137.0, 'Bp': 5.0, 'per': 'atom'},
    'si': {'V0': 20.02, 'B0': 98.8, 'Bp': 4.2, 'per': 'atom'},
    'nacl': {'V0': 44.86, 'B0': 24.0, 'Bp': 5.0, 'per': 'NaCl'},
    'mgo': {'V0': 18.68, 'B0': 160.0, 'Bp': 4.1, 'per': 'MgO'},
}
# Debye temperatures, K (Kittel, the table of θ_D)
DEBYE = {'pb': 105.0, 'nacl': 321.0, 'cu': 343.0, 'al': 428.0, 'si': 645.0, 'diamond': 2230.0}
AMU = 1.66053906660e-27  # kg
C_CM = 2.99792458e10  # cm/s
K_B, H_PLANCK = 1.380649e-23, 6.62607015e-34


def birch_murnaghan(V, V0, B0, Bp, E0=0.0):
    """The third-order Birch–Murnaghan energy (eV) at V (Å³); B0 in GPa."""
    b = B0 / EV_A3_GPA
    x = (V0 / V) ** (2.0 / 3.0)
    return E0 + 9.0 * V0 * b / 16.0 * ((x - 1.0) ** 3 * Bp + (x - 1.0) ** 2 * (6.0 - 4.0 * x))


def _solve(m, v):
    """Gaussian elimination with partial pivoting (small dense systems)."""
    n = len(v)
    a = [row[:] + [v[i]] for i, row in enumerate(m)]
    for c in range(n):
        p = max(range(c, n), key=lambda r: abs(a[r][c]))
        a[c], a[p] = a[p], a[c]
        if abs(a[c][c]) < 1e-300:
            raise ValueError("the fit is singular: take points over a wider range")
        for r in range(c + 1, n):
            f = a[r][c] / a[c][c]
            for k in range(c, n + 1):
                a[r][k] -= f * a[c][k]
    out = [0.0] * n
    for r in range(n - 1, -1, -1):
        out[r] = (a[r][n] - sum(a[r][k] * out[k] for k in range(r + 1, n))) / a[r][r]
    return out


def eos_fit(volumes, energies):
    """The fit of E(V) by Birch–Murnaghan: E is a cubic polynomial in x = V^(-2/3) (least squares); its minimum gives
    V0 and E0, the curvature B0 = V d²E/dV², the third derivative B0'. Returns V0 (Å³), E0 (eV), B0 (GPa), Bp."""
    if len(volumes) < 4:
        raise ValueError("at least four points")
    xs = [v ** (-2.0 / 3.0) for v in volumes]
    xm = sum(xs) / len(xs)
    xw = max(abs(x - xm) for x in xs) or 1.0  # centred and scaled: t = (x − xm)/xw keeps the normal equations sound
    ts = [(x - xm) / xw for x in xs]
    rows = [[t ** k for k in range(4)] for t in ts]
    ata = [[sum(r[i] * r[j] for r in rows) for j in range(4)] for i in range(4)]
    atb = [sum(r[i] * e for r, e in zip(rows, energies)) for i in range(4)]
    c = _solve(ata, atb)
    # dE/dt = c1 + 2 c2 t + 3 c3 t² = 0 — the root near the points
    import cmath

    a2, a1, a0 = 3 * c[3], 2 * c[2], c[1]
    roots = [(-a1 + s * cmath.sqrt(a1 * a1 - 4 * a2 * a0)) / (2 * a2) for s in (1, -1)] if abs(a2) > 1e-300 else [complex(-a0 / a1)]
    good = [r.real for r in roots if abs(r.imag) < 1e-12 and xm + xw * r.real > 0]
    if not good:
        raise ValueError("no minimum in the points: take a range around the equilibrium")
    t0 = min(good, key=abs)
    x0 = xm + xw * t0
    V0 = x0 ** (-1.5)
    E = lambda x: c[0] + c[1] * x + c[2] * x * x + c[3] * x ** 3  # in t
    d1 = lambda x: (c[1] + 2 * c[2] * t0 + 3 * c[3] * t0 * t0) / xw  # dE/dx at x0
    d2 = lambda x: (2 * c[2] + 6 * c[3] * t0) / xw ** 2
    d3 = 6 * c[3] / xw ** 3
    # V d²E/dV² with x = V^(-2/3): dx/dV = -2/3 x/V, d²x/dV² = 10/9 x/V²
    xv, xvv = -2.0 / 3.0 * x0 / V0, 10.0 / 9.0 * x0 / V0 ** 2
    B = V0 * (d2(x0) * xv * xv + d1(x0) * xvv)
    # B' = dB/dP = -(V/B) dB/dV at V0, with B(V) = V E''(V): dB/dV = E'' + V E'''
    xvvv = -80.0 / 27.0 * x0 / V0 ** 3
    E2 = d2(x0) * xv * xv + d1(x0) * xvv
    E3 = d3 * xv ** 3 + 3 * d2(x0) * xv * xvv + d1(x0) * xvvv
    Bp = -(V0 / B) * (E2 + V0 * E3) if B else float('nan')
    return {"V0": V0, "E0": E(t0), "B0": B * EV_A3_GPA, "Bp": Bp}


def eos(kind="si", span=6.0, n=9, noise=0.0, seed=1):
    """E(V) points of a material (its reference V0, B0, B0') at n volumes over ±span % of V0, each with a «numerical
    noise» of up to noise meV (fixed pseudo-random numbers), the fit and the curve; what is per atom or per unit."""
    if kind not in EOS_PRESETS or not 0.5 <= span <= 30 or not 4 <= n <= 30 or not 0 <= noise <= 50:
        raise ValueError("kind, span 0.5..30 %, n 4..30, noise 0..50 meV")
    p = EOS_PRESETS[kind]
    V0, B0, Bp = p['V0'], p['B0'], p['Bp']
    vols = [V0 * (1 + span / 100 * (2 * i / (n - 1) - 1)) for i in range(n)]
    state = seed * 2654435761 % 2 ** 32 or 1
    shake = []
    for _ in vols:  # a fixed linear congruential sequence: the same noise for the same seed
        state = (1103515245 * state + 12345) % 2 ** 31
        shake.append((state / 2 ** 31 * 2 - 1) * noise / 1000.0)
    energies = [birch_murnaghan(v, V0, B0, Bp) + s for v, s in zip(vols, shake)]
    fit = eos_fit(vols, energies)
    lo, hi = V0 * (1 - max(span, 8) / 100 * 1.25), V0 * (1 + max(span, 8) / 100 * 1.25)
    curve_v = [lo + (hi - lo) * i / 120 for i in range(121)]
    return {"V": vols, "E": energies, "fit": fit, "true": {"V0": V0, "B0": B0, "Bp": Bp}, "per": p['per'],
            "curve": {"V": curve_v, "E": [birch_murnaghan(v, fit['V0'], fit['B0'], fit['Bp'], fit['E0']) for v in curve_v]}}


def phonons(m1=28.09, m2=28.09, C=50.0, nk=121):
    """The phonons of a chain of two atoms per cell (masses m1, m2 in amu, the spring C in N/m between neighbours):
    ω² = C(1/m1 + 1/m2) ∓ C·sqrt((1/m1 + 1/m2)² − 4 sin²(ka/2)/(m1 m2)); in cm⁻¹. One atom (m1 = m2): the two
    branches join into one, folded at k = π/(2a)."""
    if not (1 <= m1 <= 300 and 1 <= m2 <= 300 and 1 <= C <= 1000):
        raise ValueError("masses 1..300 amu, C 1..1000 N/m")
    a, b = 1 / (m1 * AMU), 1 / (m2 * AMU)
    to_cm = 1 / (2 * math.pi * C_CM)
    ks = [-1 + 2 * j / (nk - 1) for j in range(nk)]
    acoustic, optical = [], []
    for q in ks:
        s = math.sin(math.pi * q / 2) ** 2
        root = math.sqrt(max((a + b) ** 2 - 4 * s * a * b, 0.0))
        acoustic.append(math.sqrt(max(C * (a + b - root), 0.0)) * to_cm)
        optical.append(math.sqrt(C * (a + b + root)) * to_cm)
    heavy, light = max(m1, m2), min(m1, m2)
    edges = {"acoustic_top": math.sqrt(2 * C / (heavy * AMU)) * to_cm, "optical_bottom": math.sqrt(2 * C / (light * AMU)) * to_cm,
             "optical_top": math.sqrt(2 * C * (a + b)) * to_cm}
    edges["gap"] = edges["optical_bottom"] - edges["acoustic_top"]
    return {"k": ks, "acoustic": acoustic, "optical": optical, **edges}


def debye_cv(T, theta, n=400):
    """Cv/(3R) of the Debye model: 3 (T/θ)³ ∫₀^{θ/T} x⁴eˣ/(eˣ−1)² dx (Simpson's rule)."""
    if T <= 0:
        return 0.0
    top = theta / T
    if top > 60:  # the T³ law to rounding: the integral is 4π⁴/15
        return 4 * math.pi ** 4 / 5 * (T / theta) ** 3
    h = top / n
    f = lambda x: x ** 4 * math.exp(x) / math.expm1(x) ** 2 if x > 1e-8 else x * x
    s = f(0) + f(top) + sum((4 if i % 2 else 2) * f(i * h) for i in range(1, n))
    return 3 * (T / theta) ** 3 * s * h / 3


def einstein_cv(T, theta):
    """Cv/(3R) of the Einstein model: (θ/T)² e^{θ/T}/(e^{θ/T} − 1)²."""
    if T <= 0:
        return 0.0
    x = theta / T
    if x > 700:
        return 0.0
    return x * x * math.exp(x) / math.expm1(x) ** 2


def heat_capacity(kind="cu", T=300.0, ratio=0.806):
    """Cv/(3R) against T for the Debye temperature of the material and an Einstein model with θ_E = ratio·θ_D, the
    values at T, the low-temperature law (12π⁴/5)(T/θ)³ R per atom."""
    if kind not in DEBYE or not 1 <= T <= 3000:
        raise ValueError("kind, T 1..3000 K")
    theta = DEBYE[kind]
    top = max(1.5 * theta, 1.25 * T, 300)
    ts = [top * i / 150 for i in range(1, 151)]
    return {"theta": theta, "theta_E": ratio * theta, "T": ts,
            "debye": [debye_cv(t, theta) for t in ts], "einstein": [einstein_cv(t, ratio * theta) for t in ts],
            "at": {"T": T, "debye": debye_cv(T, theta), "einstein": einstein_cv(T, ratio * theta),
                   "t3": min(4 * math.pi ** 4 / 5 * (T / theta) ** 3, 10.0)}}

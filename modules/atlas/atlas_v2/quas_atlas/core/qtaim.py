"""Quantum theory of atoms in molecules on a Hartree-Fock density: critical points, gradient paths,
Bader basins and charges, Mulliken and Loewdin populations.

HEADER
    Port of the QT object of v1.0 ENGINE (validation.js / aim.js: makeField,
    eig3, findCPs, ascend, attractors, descendPlane, baderCharges, gauleg,
    popAnalysis).  Wilkinson convention, sections 1-8.  Atomic units.

§1 THEORY
    rho(r) = 2 sum_k |psi_k|^2 over the doubly occupied MOs (fast path) or
    sum D phi phi with gradient and Hessian (core.gto.rho_at).  Critical
    points (grad rho = 0) are classified by the signs of the Hessian
    eigenvalues (rank 3, signature -3 nucleus, -1 bond, +1 ring, +3
    cage).  Bond paths: steepest ascent from a bond CP along +-v3 (the
    eigenvector of the positive eigenvalue) to the nuclear attractors.
    Laplacian lap = tr H, energy densities G (kinetic, positive definite),
    V = lap/4 - 2G (local virial theorem), H = G + V, ellipticity
    l1/l2 - 1 at bond CPs.  Bader basins: the zero-flux partition, here by
    the on-grid steepest-ascent assignment of Henkelman et al. (26
    neighbours, gain weighted by 1/distance) and an atom-centred
    quadrature (Becke-weighted Gauss-Chebyshev x Gauss-Legendre x
    trapezoid) in which every point takes the label of its grid cell, or
    of an explicit RK2 ascent if the eight surrounding labels differ,
    or of its own atom inside the beta sphere.  Charges q_A = Z_A - N_A.
    Mulliken N_A = sum_{mu in A} (DS)_mu,mu; Loewdin N_A = sum (S^1/2 D
    S^1/2)_mu,mu.

§2 ALGORITHM
    As v1.0 (Newton steps through the Hessian eigenbasis, step <= 0.3
    bohr, eigenvalues regularised to +-1e-6; 80 iterations; starting
    points: nuclei, five points on every pair < 8 bohr, triangle
    centroids, the centroid for N >= 6; duplicates within 1e-3 merged;
    CPs with |l| < 1e-7 rejected; RK4 (bond paths) and RK2 (basins) on
    the unit gradient field).

§3 APPLICATIONS
    Pages aim (all of it) and validation (populations).

§4 SPECIFICATION
    make_field(sys, res) -> F with F.rho(x,y,z), F.grad(x,y,z) -> {rho, g},
      F.full(x,y,z,deriv) -> core.gto.rho_at.
    find_cps(sys, res, F) -> [cp]; cp = {p, type n/b/r/c, rho, lap, l, v, G,
      V, H, eps, atom (nuclei), atoms and path (bond CPs)}.
    bader_charges(sys, res, F, cps, h=None, margin=4.5, nr=50, nt=12,
      wide=1) -> {pop, q, tot, ntr, grid {lo, h, nn, lab}}.
    pop_analysis(sys, res) -> {mul, low} (charges).
    Batch (numpy) helpers: F.grad_np, F.rho_np, rho_points_np,
      ascend_many, descend_plane_many (lockstep paths), _newton_many
      (lockstep Newton search), _becke_np, _basin_labels_np.
    Tier: bitwise vs v1.0 on Linux/glibc (pure path and the numpy batch
    paths, which keep the per-point operation order; see core.gto §4).
    The lockstep versions run each path or Newton search with exactly the
    scalar recurrence; only the bookkeeping (which points are still
    active) is shared.  _basin_labels_np replaces the sequential walk by
    pointer jumping to the chain roots: the walk gives every node the label
    of the root its ascent ends in, independent of the visiting order,
    because an ascent never enters a node with rho < 1e-6.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The fast rho skips terms with a r^2 >= 46 (exp < 1e-20) exactly as
    v1.0.  Grid labels Int16 -> Python ints; the density grid of the
    basin search is Float32 in v1.0 (rounded with numpy.float32 /
    struct here, the same IEEE rounding).
§7 TEST CASES (tests/test_qtaim.py)
    Poincare-Hopf n - b + r - c = 1 for every molecule; H2O: 3 nuclei, 2
    bond CPs on the O-H lines, Bader populations summing to N (1e-3),
    q_O(Bader) more negative than Mulliken; Mulliken charges of the
    Crawford water (q_O = -0.253146) to 1e-6; vs v1.0.
§8 ERROR ANALYSIS
    CP positions converge to |grad rho| < 1e-9 max(1, rho); Bader
    populations carry the grid error of the basin labels (~1e-3 e for h
    = 0.16 bohr, v1.0 design) and the quadrature error (~1e-5 e).
"""
from __future__ import annotations

import math
import struct

from . import gto
from .jsmath import cos, exp, js_hypot, js_pow, js_round, js_sign, sin

_F32 = struct.Struct("<f")


def f32(x: float) -> float:
    """Round to IEEE single precision (Float32Array storage)."""
    try:
        return _F32.unpack(_F32.pack(x))[0]
    except OverflowError:
        return math.copysign(math.inf, x)


# ---------------------------------------------------------------- density field
def make_field(sys_, res):
    bs = sys_["bs"]
    n = bs["nbf"]
    m = res["nmo"]
    o = int(math.ceil(res["nocc"]))
    C = res["C"]
    Co = [0.0] * (n * o)
    for i in range(n):
        for k in range(o):
            Co[i * o + k] = C[i * m + k]

    def rho(x, y, z):
        ps = [0.0] * o
        for s in bs["shells"]:
            dx, dy, dz = x - s["O"][0], y - s["O"][1], z - s["O"][2]
            r2 = dx * dx + dy * dy + dz * dz
            ne = len(s["e"])
            for k in range(len(s["comps"])):
                f0 = 0
                c = s["cc"][k]
                for i in range(ne):
                    ar = s["e"][i] * r2
                    if ar < 46:
                        f0 += c[i] * exp(-ar)
                if f0 == 0:
                    continue
                cp = s["comps"][k]
                v = f0
                if cp[0]:
                    v *= dx if cp[0] == 1 else dx * dx
                if cp[1]:
                    v *= dy if cp[1] == 1 else dy * dy
                if cp[2]:
                    v *= dz if cp[2] == 1 else dz * dz
                row = (s["off"] + k) * o
                for q in range(o):
                    ps[q] += Co[row + q] * v
        r = 0
        for q in range(o):
            r += ps[q] * ps[q]
        return 2 * r

    def full(x, y, z, deriv=0):
        return gto.rho_at(bs, res["D"], x, y, z, deriv)

    def grad(x, y, z):
        ps = [0.0] * o
        pg = [[0.0] * o, [0.0] * o, [0.0] * o]
        b = gto.bf_eval(bs, x, y, z, 1)
        for mu in range(n):
            v, gx, gy, gz = b["val"][mu], b["gx"][mu], b["gy"][mu], b["gz"][mu]
            if not v and not gx and not gy and not gz:
                continue
            row = mu * o
            for q in range(o):
                c = Co[row + q]
                ps[q] += c * v
                pg[0][q] += c * gx
                pg[1][q] += c * gy
                pg[2][q] += c * gz
        r = g0 = g1 = g2 = 0
        for q in range(o):
            p = ps[q]
            r += p * p
            g0 += p * pg[0][q]
            g1 += p * pg[1][q]
            g2 += p * pg[2][q]
        return {"rho": 2 * r, "g": [4 * g0, 4 * g1, 4 * g2]}

    def grad_np(X, Y, Z):
        """grad at arrays of points: the loops of grad with array operands (bitwise)."""
        np = gto._np
        b = gto.bf_eval_np(bs, X, Y, Z, 1)
        m = np.shape(X)[0]
        ps = np.zeros((m, o))
        pgx, pgy, pgz = np.zeros((m, o)), np.zeros((m, o)), np.zeros((m, o))
        Ca = np.asarray(Co, dtype=float).reshape(n, o)
        for mu in range(n):
            v, gx, gy, gz = b["val"][mu], b["gx"][mu], b["gy"][mu], b["gz"][mu]
            nz_ = (v != 0) | (gx != 0) | (gy != 0) | (gz != 0)
            c = Ca[mu][None, :]
            if nz_.all():
                ps += c * v[:, None]
                pgx += c * gx[:, None]
                pgy += c * gy[:, None]
                pgz += c * gz[:, None]
            elif nz_.any():  # v1.0 skips basis functions that vanish (with derivatives) at the point
                ix = np.nonzero(nz_)[0]
                ps[ix] += c * v[ix, None]
                pgx[ix] += c * gx[ix, None]
                pgy[ix] += c * gy[ix, None]
                pgz[ix] += c * gz[ix, None]
        r = g0 = g1 = g2 = np.zeros(m)
        for q in range(o):
            p = ps[:, q]
            r = r + p * p
            g0 = g0 + p * pgx[:, q]
            g1 = g1 + p * pgy[:, q]
            g2 = g2 + p * pgz[:, q]
        return 2 * r, (4 * g0, 4 * g1, 4 * g2)

    class Field:
        pass
    F = Field()
    F.rho, F.grad, F.full = rho, grad, full
    F.grad_np = grad_np
    F.rho_np = lambda X, Y, Z: rho_points_np(F, gto._np.stack((X, Y, Z), 1))
    F.sys, F.res, F.Co, F.o = sys_, res, Co, o
    return F


def eig3(h):
    M = [h[0], h[1], h[2], h[1], h[3], h[4], h[2], h[4], h[5]]
    r = gto.jacobi(M, 3)
    return {"l": r["e"], "v": [[r["V"][0 * 3 + k], r["V"][1 * 3 + k], r["V"][2 * 3 + k]] for k in range(3)]}


def _hyp(*a):
    return js_hypot(*a)


# ---------------------------------------------------------------- critical points
def find_cps(sys_, res, F):
    at = sys_["atoms"]
    N = len(at)
    starts = [[a["x"], a["y"], a["z"]] for a in at]
    for i in range(N):
        for j in range(i):
            a, b = at[i], at[j]
            d = _hyp(a["x"] - b["x"], a["y"] - b["y"], a["z"] - b["z"])
            if d > 8:
                continue
            for f in (0.5, 0.35, 0.65, 0.25, 0.75):
                starts.append([a["x"] + f * (b["x"] - a["x"]), a["y"] + f * (b["y"] - a["y"]), a["z"] + f * (b["z"] - a["z"])])
    for i in range(N):
        for j in range(i):
            for k in range(j):
                a, b, c = at[i], at[j], at[k]
                starts.append([(a["x"] + b["x"] + c["x"]) / 3, (a["y"] + b["y"] + c["y"]) / 3, (a["z"] + b["z"] + c["z"]) / 3])
    if N >= 6:
        c = []
        for d in ("x", "y", "z"):
            s = 0
            for a in at:
                s = s + a[d]
            c.append(s / N)
        starts.append(c)
    cps = []
    found = _newton_many(F, starts) if gto._np is not None else [_newton(F, s0) for s0 in starts]
    finals = _full_many(F, [p for p, ok in found if ok]) if gto._np is not None else None
    nf = 0
    for p, ok in found:
        if not ok:
            continue
        if finals is not None:
            f = finals[nf]
            nf += 1
        else:
            f = F.full(p[0], p[1], p[2], 2)
        if f["rho"] < 1e-5:
            continue
        if any(_hyp(c["p"][0] - p[0], c["p"][1] - p[1], c["p"][2] - p[2]) < 1e-3 for c in cps):
            continue
        e = eig3(f["h"])
        sig = 0
        for l_ in e["l"]:
            sig = sig + (1 if l_ > 0 else -1)
        if any(abs(l_) < 1e-7 for l_ in e["l"]):
            continue
        typ = "n" if sig == -3 else "b" if sig == -1 else "r" if sig == 1 else "c"
        lap = f["h"][0] + f["h"][3] + f["h"][5]
        V = 0.25 * lap - 2 * f["G"]
        cp = {"p": p, "type": typ, "rho": f["rho"], "lap": lap, "l": e["l"], "v": e["v"], "G": f["G"], "V": V, "H": f["G"] + V,
              "eps": e["l"][0] / e["l"][1] - 1 if typ == "b" else None}
        if typ == "n":
            bi, bd = -1, 1e9
            for i, a in enumerate(at):
                d = _hyp(a["x"] - p[0], a["y"] - p[1], a["z"] - p[2])
                if d < bd:
                    bd, bi = d, i
            cp["atom"] = bi if bd < 0.3 else -1
        cps.append(cp)
    for i, a in enumerate(at):
        if not any(c["type"] == "n" and c.get("atom") == i for c in cps):
            r0 = F.rho(a["x"], a["y"], a["z"])
            is_max = True
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)):
                if F.rho(a["x"] + 0.03 * d[0], a["y"] + 0.03 * d[1], a["z"] + 0.03 * d[2]) >= r0:
                    is_max = False
            if is_max:
                f = F.full(a["x"], a["y"], a["z"], 2)
                cps.append({"p": [a["x"], a["y"], a["z"]], "type": "n", "rho": f["rho"], "lap": f["h"][0] + f["h"][3] + f["h"][5],
                            "l": [0, 0, 0], "v": [], "G": f["G"], "V": 0, "H": 0, "eps": None, "atom": i})
    att = attractors(at, cps)
    bonds = [c for c in cps if c["type"] == "b"]
    starts = []
    for c in bonds:
        v = c["v"][2]
        for sg in (1, -1):
            starts.append([c["p"][0] + sg * 0.02 * v[0], c["p"][1] + sg * 0.02 * v[1], c["p"][2] + sg * 0.02 * v[2]])
    if gto._np is not None and starts:
        trs = ascend_many(F, starts, at, 0.04, 800, None, att)
    else:
        trs = [ascend(F, p, at, 0.04, 800, None, att) for p in starts]
    for n_, c in enumerate(bonds):
        c["path"] = [trs[2 * n_]["pts"], trs[2 * n_ + 1]["pts"]]
        c["atoms"] = [trs[2 * n_]["atom"], trs[2 * n_ + 1]["atom"]]
    return cps


def _newton_step(f, p):
    """One Newton step of v1.0 findCPs: (new p, state) with state None (continue) or ok flag."""
    gn = _hyp(*f["g"])
    if gn < 1e-9 * max(1, f["rho"]):
        return p, True
    H = f["h"]
    e = eig3(H)
    st = [0, 0, 0]
    for k in range(3):
        v = e["v"][k]
        gv = v[0] * f["g"][0] + v[1] * f["g"][1] + v[2] * f["g"][2]
        lk = e["l"][k]
        if abs(lk) < 1e-6:
            lam = (1 if lk == 0 or lk != lk else js_sign(lk)) * 1e-6
        else:
            lam = lk
        for d in range(3):
            st[d] -= gv / lam * v[d]
    L = _hyp(*st)
    if L > 0.3:
        st = [x * 0.3 / L for x in st]
    p = [x + st[d] for d, x in enumerate(p)]
    if L < 1e-12:
        return p, gn < 1e-6 * max(1, f["rho"])
    return p, None


def _newton(F, s0):
    p = list(s0)
    for _it in range(80):
        p, state = _newton_step(F.full(p[0], p[1], p[2], 2), p)
        if state is not None:
            return p, state
    return p, False


def _full_many(F, pts):
    """F.full(x, y, z, 2) at many points (numpy batch, bitwise), as a list of dicts of floats."""
    np = gto._np
    if not pts:
        return []
    Q = np.asarray(pts, dtype=float).reshape(-1, 3)
    f = gto.rho_at_np(F.sys["bs"], F.res["D"], Q[:, 0], Q[:, 1], Q[:, 2], 2, kin=True)
    rho, g, h, G = f["rho"].tolist(), [x.tolist() for x in f["g"]], [x.tolist() for x in f["h"]], f["G"].tolist()
    return [{"rho": rho[j], "g": [g[0][j], g[1][j], g[2][j]], "h": [h[q][j] for q in range(6)], "G": G[j]} for j in range(len(rho))]


def _newton_many(F, starts):
    """_newton for all starting points in lockstep: the densities of the active
    points are evaluated in one batch per iteration, the steps point by point."""
    m = len(starts)
    P = [list(s0) for s0 in starts]
    res = [None] * m
    act = list(range(m))
    for _it in range(80):
        if not act:
            break
        fs = _full_many(F, [P[k] for k in act])
        nxt = []
        for k, f in zip(act, fs):
            P[k], state = _newton_step(f, P[k])
            if state is None:
                nxt.append(k)
            else:
                res[k] = state
        act = nxt
    return [(P[k], res[k] if res[k] is not None else False) for k in range(m)]


def _unit(g):
    n = _hyp(*g) or 1
    return [x / n for x in g]


def ascend(F, p0, at, h, maxs, rb, att, rk2=False):
    p = list(p0)
    pts = [list(p)]
    N = len(at)

    def dir_(q):
        return _unit(F.grad(q[0], q[1], q[2])["g"])
    for _s in range(maxs):
        for i in range(N):
            a = att[i] if att else [at[i]["x"], at[i]["y"], at[i]["z"]]
            if not a:
                continue
            r = rb[i] if rb else max(0.06, h)
            if _hyp(a[0] - p[0], a[1] - p[1], a[2] - p[2]) < r:
                if not rb:
                    pts.append(list(a))
                return {"pts": pts, "atom": i}
        if rk2:
            k1 = dir_(p)
            k2 = dir_([x + 0.5 * h * k1[d] for d, x in enumerate(p)])
            p = [x + h * k2[d] for d, x in enumerate(p)]
        else:
            k1 = dir_(p)
            k2 = dir_([x + 0.5 * h * k1[d] for d, x in enumerate(p)])
            k3 = dir_([x + 0.5 * h * k2[d] for d, x in enumerate(p)])
            k4 = dir_([x + h * k3[d] for d, x in enumerate(p)])
            p = [x + h / 6 * (k1[d] + 2 * k2[d] + 2 * k3[d] + k4[d]) for d, x in enumerate(p)]
        pts.append(list(p))
    return {"pts": pts, "atom": -1}


def attractors(at, cps):
    out = []
    for i in range(len(at)):
        c = next((c for c in cps if c["type"] == "n" and c.get("atom") == i), None)
        out.append(list(c["p"]) if c else None)
    return out


def descend_plane(F, p0, P, h, maxs, stop):
    p = list(p0)
    pts = [list(p)]

    def dir_(q):
        g = F.grad(q[0], q[1], q[2])["g"]
        a = g[0] * P["u"][0] + g[1] * P["u"][1] + g[2] * P["u"][2]
        b = g[0] * P["w"][0] + g[1] * P["w"][1] + g[2] * P["w"][2]
        d = [a * P["u"][0] + b * P["w"][0], a * P["u"][1] + b * P["w"][1], a * P["u"][2] + b * P["w"][2]]
        n = _hyp(*d) or 1
        return [-x / n for x in d]
    for _s in range(maxs):
        k1 = dir_(p)
        k2 = dir_([x + 0.5 * h * k1[d] for d, x in enumerate(p)])
        p = [x + h * k2[d] for d, x in enumerate(p)]
        pts.append(list(p))
        if stop(p):
            break
    return pts


# ---------------------------------------------------------------- Bader charges
RBRAGG = {"H": 0.35, "He": 0.3, "Li": 1.45, "Be": 1.05, "B": 0.85, "C": 0.7, "N": 0.65, "O": 0.6, "F": 0.5}


def gauleg(n):
    xs, ws = [0.0] * n, [0.0] * n
    for i in range(n):
        z = cos(math.pi * (i + 0.75) / (n + 0.5))
        pp = 0
        for _it in range(100):
            p1, p2 = 1, 0
            for j in range(1, n + 1):
                p3 = p2
                p2 = p1
                p1 = ((2 * j - 1) * z * p2 - (j - 1) * p3) / j
            pp = n * (z * p1 - p2) / (z * z - 1)
            z1 = z
            z = z1 - p1 / pp
            if abs(z - z1) < 1e-15:
                break
        xs[i] = z
        ws[i] = 2 / ((1 - z * z) * pp * pp)
    return {"x": xs, "w": ws}


def _rho_grid_box(F, lo, h, nn):
    """Float32 density on the basin grid (v1.0 loop order), numpy batch when available."""
    nx, ny, nz = nn
    if gto._np is not None:
        return list(rho_points_np(F, _box_points(lo, h, nn)).astype("float32").astype(float))
    R = [0.0] * (nx * ny * nz)
    for i in range(nx):
        x = lo[0] + i * h
        for j in range(ny):
            y = lo[1] + j * h
            for k in range(nz):
                R[(i * ny + j) * nz + k] = f32(F.rho(x, y, lo[2] + k * h))
    return R


def _box_points(lo, h, nn):
    np = gto._np
    nx, ny, nz = nn
    x = lo[0] + np.arange(nx) * h
    y = lo[1] + np.arange(ny) * h
    z = lo[2] + np.arange(nz) * h
    X, Y, Z = np.meshgrid(x, y, z, indexing="ij")
    return np.stack((X.ravel(), Y.ravel(), Z.ravel()), 1)


def rho_points_np(F, pts):
    """F.rho at an (m, 3) array of points: the scalar algorithm vectorised over points (bitwise)."""
    np = gto._np
    from .jsmath_np import exp_np
    bs = F.sys["bs"]
    o = F.o
    Co = np.asarray(F.Co).reshape(-1, o)
    P = np.asarray(pts, dtype=float).reshape(-1, 3)
    m = P.shape[0]
    ps = np.zeros((m, o))
    for s in bs["shells"]:
        dx, dy, dz = P[:, 0] - s["O"][0], P[:, 1] - s["O"][1], P[:, 2] - s["O"][2]
        r2 = dx * dx + dy * dy + dz * dz
        ar = [a * r2 for a in s["e"]]
        ex = []
        for x in ar:  # exp only where it is used (a r^2 < 46): same values, less work
            e_ = np.zeros(m)
            sel = np.nonzero(x < 46)[0]
            if sel.size:
                e_[sel] = exp_np(x[sel] * -1.0)
            ex.append(e_)
        for k in range(len(s["comps"])):
            c = s["cc"][k]
            f0 = np.zeros(m)
            for i in range(len(s["e"])):
                f0 = np.where(ar[i] < 46, f0 + c[i] * ex[i], f0)
            cp = s["comps"][k]
            v = f0
            if cp[0]:
                v = v * (dx if cp[0] == 1 else dx * dx)
            if cp[1]:
                v = v * (dy if cp[1] == 1 else dy * dy)
            if cp[2]:
                v = v * (dz if cp[2] == 1 else dz * dz)
            nz_ = f0 != 0
            row = Co[s["off"] + k][None, :]
            # ps[q] += Co*v for points with f0 != 0 (v1.0 skips f0 == 0)
            if nz_.all():
                ps += row * v[:, None]
            elif nz_.any():
                ix = np.nonzero(nz_)[0]
                ps[ix] += row * v[ix, None]
    r = np.zeros(m)
    for q in range(o):
        r = r + ps[:, q] * ps[:, q]
    return 2 * r


def bader_charges(sys_, res, F, cps, h=None, margin=None, nr=None, nt=None, wide=None):
    at = sys_["atoms"]
    N = len(at)
    mar = margin or 4.5
    lo = [min(a[d] for a in at) - mar for d in ("x", "y", "z")]
    hi = [max(a[d] for a in at) + mar for d in ("x", "y", "z")]
    hh = h or 0.16
    vol = (hi[0] - lo[0]) * (hi[1] - lo[1]) * (hi[2] - lo[2])
    if not h:
        hh = max(0.12, _cbrt(vol / 4e5))
    h = hh
    nn = [int(math.ceil((hi[d] - lo[d]) / h)) + 1 for d in range(3)]
    nx, ny, nz = nn
    NT = nx * ny * nz
    R = _rho_grid_box(F, lo, h, nn)
    nb = []
    for a in (-1, 0, 1):
        for b in (-1, 0, 1):
            for c in (-1, 0, 1):
                if a or b or c:
                    nb.append((a, b, c, 1 / js_hypot(a, b, c)))
    attG = attractors(at, cps)
    lab = _basin_labels_np(R, nn, nb, lo, h, attG) if gto._np is not None else _basin_labels(R, nn, nb, lo, h, attG)
    nr = nr or 50
    nt = nt or 12
    np_ = 2 * nt
    gl = gauleg(nt)
    pop = [0.0] * N
    tot = 0
    Rb = [RBRAGG.get(a["el"], 0.7) for a in at]
    ntr = 0
    att = attractors(at, cps)
    rbeta = []
    for i, a in enumerate(at):
        if not att[i]:
            rbeta.append(0)
            continue
        d = 1e9
        for c in cps:
            if c["type"] != "n":
                q = js_hypot(c["p"][0] - att[i][0], c["p"][1] - att[i][1], c["p"][2] - att[i][2])
                if q < d:
                    d = q
        for j, b in enumerate(at):
            if j != i:
                d = min(d, 0.5 * js_hypot(a["x"] - b["x"], a["y"] - b["y"], a["z"] - b["z"]))
        rbeta.append(0.5 * d)
    W = 0 if wide == 0 else 1
    Rbc = [[js_hypot(at[B]["x"] - at[C]["x"], at[B]["y"] - at[C]["y"], at[B]["z"] - at[C]["z"]) for C in range(N)] for B in range(N)]
    pts, meta = _atomic_points(at, Rb, nr, nt, np_, gl)
    rho_all = rho_points_np(F, pts).tolist() if gto._np is not None else None
    batch = gto._np is not None
    acc, pend = [], []
    if batch:
        WB, DIST = _becke_np(at, Rbc, meta)
    for idx, (A, r, wr, wt, px, py, pz) in enumerate(meta):
        if batch:
            wb = WB[idx]
            if wb < 1e-12:
                continue
            dist = DIST[idx]
        else:
            dist = [js_hypot(at[B]["x"] - px, at[B]["y"] - py, at[B]["z"] - pz) for B in range(N)]
            num = den = 0
            for B in range(N):
                P = 1
                for C in range(N):
                    if C == B:
                        continue
                    mu = (dist[B] - dist[C]) / Rbc[B][C]
                    for _q in range(3):
                        mu = 1.5 * mu - 0.5 * mu * mu * mu
                    P *= 0.5 * (1 - mu)
                den += P
                if B == A:
                    num = P
            wb = num / den if den > 0 else 0
        if wb < 1e-12:
            continue
        rho = rho_all[idx] if rho_all is not None else F.rho(px, py, pz)
        if rho < 1e-10:
            continue
        w = wr * wt * wb * rho
        fi, fj, fk = (px - lo[0]) / h, (py - lo[1]) / h, (pz - lo[2]) / h
        gi, gj, gk = math.floor(fi), math.floor(fj), math.floor(fk)
        L = -1
        if r < rbeta[A]:
            L = A
        elif gi >= 0 and gj >= 0 and gk >= 0 and gi < nx - 1 and gj < ny - 1 and gk < nz - 1:
            l0 = -3
            same = True
            a = -W
            while a < 2 + W and same:
                b = -W
                while b < 2 + W and same:
                    for c in range(-W, 2 + W):
                        ii, jj, kk = gi + a, gj + b, gk + c
                        if ii < 0 or jj < 0 or kk < 0 or ii >= nx or jj >= ny or kk >= nz:
                            continue
                        v = lab[(ii * ny + jj) * nz + kk]
                        if v < 0:
                            continue
                        if l0 == -3:
                            l0 = v
                        elif v != l0:
                            same = False
                            break
                    b += 1
                a += 1
            if same and l0 >= 0:
                L = l0
            elif rho > 1e-5:
                ntr += 1
                if batch:
                    # traced later for all such points at once; accumulated below in point order
                    pend.append(len(acc))
                    acc.append([None, w, dist, (px, py, pz)])
                    continue
                tr = ascend(F, [px, py, pz], at, 0.12, 300, rbeta, att, True)
                L = tr["atom"]
        acc.append([L, w, dist, None])
    if pend:
        trs = ascend_many(F, [acc[k][3] for k in pend], at, 0.12, 300, rbeta, att, True, keep=False)
        for k, tr in zip(pend, trs):
            acc[k][0] = tr["atom"]
    for L, w, dist, _p in acc:
        if L < 0:
            bd = 1e9
            for B in range(N):
                if att[B] and dist[B] < bd:
                    bd = dist[B]
                    L = B
        pop[L] += w
        tot += w
    return {"pop": pop, "q": [a["Z"] - pop[i] for i, a in enumerate(at)], "tot": tot, "ntr": ntr,
            "grid": {"lo": lo, "h": h, "nn": nn, "lab": lab}}


def _becke_np(at, Rbc, meta):
    """Becke weights of all quadrature points (the loops of bader_charges with
    array operands; bitwise).  Returns (weights list, distances per point)."""
    np = gto._np
    from .jsmath_np import hypot3_np
    N = len(at)
    M = np.asarray(meta, dtype=float)
    A = M[:, 0].astype(int)
    px, py, pz = M[:, 4], M[:, 5], M[:, 6]
    dist = [hypot3_np(at[B]["x"] - px, at[B]["y"] - py, at[B]["z"] - pz) for B in range(N)]
    num = np.zeros(len(meta))
    den = np.zeros(len(meta))
    for B in range(N):
        P = np.ones(len(meta))
        for C in range(N):
            if C == B:
                continue
            mu = (dist[B] - dist[C]) / Rbc[B][C]
            for _q in range(3):
                mu = 1.5 * mu - 0.5 * mu * mu * mu
            P = P * (0.5 * (1 - mu))
        den = den + P
        num = np.where(A == B, P, num)
    with np.errstate(divide="ignore", invalid="ignore"):
        wb = np.where(den > 0, num / np.where(den > 0, den, 1.0), 0.0)
    D = np.stack(dist, 1).tolist()
    return wb.tolist(), D


def _cbrt(x):
    from .jsmath import cbrt
    return cbrt(x)


def _atomic_points(at, Rb, nr, nt, np_, gl):
    pts, meta = [], []
    for A in range(len(at)):
        a = at[A]
        rm = Rb[A]
        for ir in range(1, nr + 1):
            x = cos(ir * math.pi / (nr + 1))
            r = rm * (1 + x) / (1 - x)
            wr = (math.pi / (nr + 1) * js_pow(sin(ir * math.pi / (nr + 1)), 2) / math.sqrt(1 - x * x) * 2 * rm / js_pow(1 - x, 2) * r * r)
            for it in range(nt):
                ct = gl["x"][it]
                st = math.sqrt(1 - ct * ct)
                wt = gl["w"][it] * 2 * math.pi / np_
                for ip in range(np_):
                    ph = 2 * math.pi * ip / np_
                    px = a["x"] + r * st * cos(ph)
                    py = a["y"] + r * st * sin(ph)
                    pz = a["z"] + r * ct
                    pts.append((px, py, pz))
                    meta.append((A, r, wr, wt, px, py, pz))
    return pts, meta


def _basin_labels(R, nn, nb, lo, h, attG):
    nx, ny, nz = nn
    NT = nx * ny * nz
    lab = [-1] * NT
    path = []
    for s in range(NT):
        if lab[s] >= 0:
            continue
        if R[s] < 1e-6:
            lab[s] = -2
            continue
        path.clear()
        c = s
        while True:
            if lab[c] >= 0 or lab[c] == -2:
                break
            path.append(c)
            k = c % nz
            j = ((c - k) // nz) % ny
            i = (c - k - j * nz) // (nz * ny)
            best = -1
            bg = 0
            Rc = R[c]
            for a, b, d, w in nb:
                ii, jj, kk = i + a, j + b, k + d
                if ii < 0 or jj < 0 or kk < 0 or ii >= nx or jj >= ny or kk >= nz:
                    continue
                t = (ii * ny + jj) * nz + kk
                g = (R[t] - Rc) * w
                if g > bg:
                    bg = g
                    best = t
            if best < 0:
                ba, bd = 0, 1e9
                x, y, z = lo[0] + i * h, lo[1] + j * h, lo[2] + k * h
                for ia, A in enumerate(attG):
                    if not A:
                        continue
                    dd = js_hypot(A[0] - x, A[1] - y, A[2] - z)
                    if dd < bd:
                        bd, ba = dd, ia
                lab[c] = ba
                break
            c = best
        L = lab[c]
        for q in path:
            lab[q] = L
    return lab


# ---------------------------------------------------------------- populations
LOWDIN_ORTHO_D = True   # 2.7.0; False reproduces v1.0 / Atlas 0.80 (orientation-dependent Loewdin)


def _sym_pow(A, m, p):
    """A^p for a small symmetric positive-definite m x m matrix (flat list)."""
    e = gto.jacobi(A, m)
    return [sum(e["V"][i * m + k] * e["e"][k] ** p * e["V"][j * m + k] for k in range(m)) for i in range(m) for j in range(m)]


def _orthonormal_cartesian_d(sys_, S, D, n):
    """2.7.0: Loewdin charges independent of the orientation of the molecule.

    The six Cartesian d functions of a shell are not orthonormal, so a rotation mixes them by a
    non-orthogonal matrix and symmetric orthogonalisation of the whole basis (S^1/2) is not
    rotation-covariant: equivalent atoms got slightly different Loewdin charges (NH3/6-31G*:
    0.2677 / 0.2692 / 0.2692).  Each 6-function shell is first orthonormalised within itself
    (phi' = phi S_shell^-1/2, a polar factor, so rotations act orthogonally on phi'); the space and
    the Mulliken charges are unchanged.  Bases without Cartesian d return (S, D) untouched."""
    blocks = [(sh["off"], len(sh["comps"])) for sh in sys_["bs"]["shells"] if len(sh["comps"]) == 6]
    if not blocks or not LOWDIN_ORTHO_D:
        return S, D
    T = [1.0 if i == j else 0.0 for i in range(n) for j in range(n)]
    Ti = list(T)
    for off, m in blocks:
        Sb = [S[(off + i) * n + off + j] for i in range(m) for j in range(m)]
        X, Y = _sym_pow(Sb, m, -0.5), _sym_pow(Sb, m, 0.5)
        for i in range(m):
            for j in range(m):
                T[(off + i) * n + off + j] = X[i * m + j]
                Ti[(off + i) * n + off + j] = Y[i * m + j]
    Tt = [T[j * n + i] for i in range(n) for j in range(n)]
    Tit = [Ti[j * n + i] for i in range(n) for j in range(n)]
    S2 = gto.mm(gto.mm(Tt, S, n, n, n), T, n, n, n)          # T^T S T
    D2 = gto.mm(gto.mm(Ti, D, n, n, n), Tit, n, n, n)        # T^-1 D T^-T
    return S2, D2


def pop_analysis(sys_, res):
    n = sys_["bs"]["nbf"]
    S = sys_["one"]["S"]
    D = res["D"]
    at = sys_["atoms"]
    own = [0] * n
    for s in sys_["bs"]["shells"]:
        for k in range(len(s["comps"])):
            own[s["off"] + k] = s["atom"]
    mul = [0.0] * len(at)
    for i in range(n):
        s = 0
        for j in range(n):
            s += D[i * n + j] * S[j * n + i]
        mul[own[i]] += s
    S, D = _orthonormal_cartesian_d(sys_, S, D, n)
    e = gto.jacobi(S, n)
    Sh = [0.0] * (n * n)
    for i in range(n):
        for j in range(n):
            s = 0
            for k in range(n):
                s += e["V"][i * n + k] * math.sqrt(max(e["e"][k], 0)) * e["V"][j * n + k]
            Sh[i * n + j] = s
    T = gto.mm(gto.mm(Sh, D, n, n, n), Sh, n, n, n)
    low = [0.0] * len(at)
    for i in range(n):
        low[own[i]] += T[i * n + i]
    return {"mul": [a["Z"] - mul[i] for i, a in enumerate(at)], "low": [a["Z"] - low[i] for i, a in enumerate(at)]}


# ---------------------------------------------------------------- batch (lockstep) versions, numpy
def _unit_np(g):
    from .jsmath_np import hypot3_np
    np = gto._np
    n = hypot3_np(*g)
    n = np.where(n == 0, 1.0, n)  # `|| 1`
    return g[0] / n, g[1] / n, g[2] / n


def ascend_many(F, starts, at, h, maxs, rb, att, rk2=False, keep=True):
    """ascend() for many starting points at once.  Every path runs the same
    scalar recurrence elementwise (bitwise equal to ascend point by point);
    a path leaves the batch when it reaches an attractor."""
    np = gto._np
    from .jsmath_np import hypot3_np
    N = len(at)
    P = np.array(starts, dtype=float).reshape(-1, 3)
    m = P.shape[0]
    atom = np.full(m, -1)
    act = np.ones(m, dtype=bool)
    pts = [[list(p)] for p in P.tolist()] if keep else None
    A = [att[i] if att else [at[i]["x"], at[i]["y"], at[i]["z"]] for i in range(N)]
    R = [rb[i] if rb else max(0.06, h) for i in range(N)]

    def dir_(Q):
        _r, g = F.grad_np(Q[:, 0], Q[:, 1], Q[:, 2])
        return np.stack(_unit_np(g), 1)
    for _s in range(maxs):
        for i in range(N):
            a = A[i]
            if not a:
                continue
            ix = np.nonzero(act)[0]
            if not ix.size:
                break
            Q = P[ix]
            hit = hypot3_np(a[0] - Q[:, 0], a[1] - Q[:, 1], a[2] - Q[:, 2]) < R[i]
            hi = ix[hit]
            atom[hi] = i
            act[hi] = False
            if keep and not rb:
                for k in hi.tolist():
                    pts[k].append(list(a))
        ix = np.nonzero(act)[0]
        if not ix.size:
            break
        Q = P[ix]
        if rk2:
            k1 = dir_(Q)
            k2 = dir_(Q + 0.5 * h * k1)
            Q = Q + h * k2
        else:
            k1 = dir_(Q)
            k2 = dir_(Q + 0.5 * h * k1)
            k3 = dir_(Q + 0.5 * h * k2)
            k4 = dir_(Q + h * k3)
            Q = Q + h / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        P[ix] = Q
        if keep:
            for k, q in zip(ix.tolist(), Q.tolist()):
                pts[k].append(q)
    return [{"pts": pts[k] if keep else None, "atom": int(atom[k])} for k in range(m)]


def descend_plane_many(F, starts, P, h, maxs, stop_np):
    """descend_plane() for many starting points at once (bitwise per path).
    stop_np(Q, ix) -> bool array for the points Q of the paths ix."""
    np = gto._np
    from .jsmath_np import hypot3_np
    X = np.array(starts, dtype=float).reshape(-1, 3)
    m = X.shape[0]
    u, w = P["u"], P["w"]
    pts = [[list(p)] for p in X.tolist()]
    act = np.ones(m, dtype=bool)

    def dir_(Q):
        _r, g = F.grad_np(Q[:, 0], Q[:, 1], Q[:, 2])
        a = g[0] * u[0] + g[1] * u[1] + g[2] * u[2]
        b = g[0] * w[0] + g[1] * w[1] + g[2] * w[2]
        d = (a * u[0] + b * w[0], a * u[1] + b * w[1], a * u[2] + b * w[2])
        n = hypot3_np(*d)
        n = np.where(n == 0, 1.0, n)
        return np.stack((-d[0] / n, -d[1] / n, -d[2] / n), 1)
    for _s in range(maxs):
        ix = np.nonzero(act)[0]
        if not ix.size:
            break
        Q = X[ix]
        k1 = dir_(Q)
        k2 = dir_(Q + 0.5 * h * k1)
        Q = Q + h * k2
        X[ix] = Q
        for k, q in zip(ix.tolist(), Q.tolist()):
            pts[k].append(q)
        act[ix[stop_np(Q, ix)]] = False
    return pts


def _basin_labels_np(R, nn, nb, lo, h, attG):
    """_basin_labels vectorised: the steepest-ascent neighbour of every node
    (same comparisons, same neighbour order) and the root of every chain by
    pointer jumping.  The sequential v1.0 walk assigns each chain the label of
    its root (labels do not depend on the visiting order: an ascent never
    enters a node with rho < 1e-6), so the result is the same."""
    np = gto._np
    nx, ny, nz = nn
    A = np.asarray(R, dtype=float).reshape(nx, ny, nz)
    best = np.full((nx, ny, nz), -1, dtype=np.int64)
    bg = np.zeros((nx, ny, nz))
    flat = np.arange(nx * ny * nz).reshape(nx, ny, nz)
    for a, b, d, w in nb:
        si = slice(max(0, -a), nx - max(0, a))
        sj = slice(max(0, -b), ny - max(0, b))
        sk = slice(max(0, -d), nz - max(0, d))
        ti = slice(max(0, a), nx - max(0, -a))
        tj = slice(max(0, b), ny - max(0, -b))
        tk = slice(max(0, d), nz - max(0, -d))
        g = (A[ti, tj, tk] - A[si, sj, sk]) * w
        better = g > bg[si, sj, sk]
        bg[si, sj, sk] = np.where(better, g, bg[si, sj, sk])
        best[si, sj, sk] = np.where(better, flat[ti, tj, tk], best[si, sj, sk])
    best = best.ravel()
    root = np.where(best < 0, np.arange(best.size), best)
    while True:
        nxt = root[root]
        if np.array_equal(nxt, root):
            break
        root = nxt
    roots = np.nonzero(best < 0)[0]
    rl = {}
    for c in roots.tolist():
        k = c % nz
        j = ((c - k) // nz) % ny
        i = (c - k - j * nz) // (nz * ny)
        ba, bd = 0, 1e9
        x, y, z = lo[0] + i * h, lo[1] + j * h, lo[2] + k * h
        for ia, At in enumerate(attG):
            if not At:
                continue
            dd = js_hypot(At[0] - x, At[1] - y, At[2] - z)
            if dd < bd:
                bd, ba = dd, ia
        rl[c] = ba
    labr = np.zeros(best.size, dtype=np.int64)
    if rl:
        keys = np.fromiter(rl.keys(), dtype=np.int64)
        vals = np.fromiter(rl.values(), dtype=np.int64)
        lut = np.zeros(best.size, dtype=np.int64)
        lut[keys] = vals
        labr = lut[root]
    lab = np.where(A.ravel() < 1e-6, -2, labr)
    return lab.tolist()

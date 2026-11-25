"""Atoms in molecules page: molecules, the staged calculation, volume grids, isosurfaces, ESP.

HEADER
    The calculation behind the page "Атомы в молекулах (QTAIM)": for a
    molecule k of the page and a basis b, RHF (core.gto), critical points,
    gradient paths and Bader charges (core.qtaim), the density and its
    Laplacian on a plane (contour map) and on 3-D grids (isosurfaces drawn by
    the page), the molecular electrostatic potential on the 0.001 au
    density surface with its local extrema, single MOs on the grid and
    density profiles along bond lines. Port of GEO, VOL and AIMJOB of the
    v1.0 page script. Wilkinson convention, sections 1-8.

§1 THEORY
    Geometries: experimental structures (angstrom) of v1.0, converted with
    a0 = 0.52917721092 A. The map plane is spanned by the orthonormal u, w
    of the page table PL; the window is the projected molecule +-2.6 bohr,
    at least 7 bohr wide and with aspect ratio limited to 1.6 / 1.25.
    Gradient paths in the plane: descent of rho along the in-plane
    projection of -grad rho (qtaim.descend_plane), started on a circle
    around each in-plane attractor; interatomic surfaces: the same descent
    from a bond CP along its in-plane negative-curvature eigenvector.
    Volume grids: rho = 2 sum_occ psi_k^2 at the nodes of a box around the
    molecule (padding 4.5 / 2.2 bohr) with the step chosen so that the
    number of nodes does not exceed a limit; Laplacian by the 7-point
    finite difference. Isosurfaces: marching tetrahedra (six tetrahedra
    per cube, vertices on cube edges by linear interpolation, normals from
    the interpolated finite-difference gradient). ESP on the surface of
    ln(rho) = ln; extrema: vertices with no greater (smaller) mesh
    neighbour and no more extreme vertex within 1.6 bohr.

§2 ALGORITHM
    job(k, b): cached state; stage(k, b, name) for name in scf, map, vol,
    esp, bader computes the stage (and the ones it needs) once and returns
    the message the v1.0 worker posted. Float32 arrays are returned as
    {"f32": base64} (little-endian), index arrays as {"u32": base64}.
    Batch evaluation over grid points uses gto.bf_eval_np / rho_at_np /
    V.many_exact, which evaluate the scalar expressions with array operands.

§3 APPLICATIONS
    pages/aim.py (endpoints aim.meta, aim.stage, aim.mo, aim.prof).

§4 SPECIFICATION
    MOLS: tuple of page keys; PL: key -> (u, w).
    atoms(k) -> list of {el, x, y, z} (bohr).
    plane(atoms, k) -> {u, w, n, inpl, pr, s0, s1, t0, t1}.
    box(atoms, pad, max_pts, hmin) -> {o, h, n}.
    rho_grid(bs, res, G), mo_grid(bs, C, m, kmo, G), lap_grid(R, G)
      -> list of float32 values (as Python floats), index (k ny + j) nx + i.
    iso(F, G, level, sign=1) -> {pos, nrm (float32 lists), idx (ints)}.
    extrema(mesh, V, rad) -> list of {p, n, v, type}.
    stage(k, b, name) -> dict (see the page); prof(k, b, ia, ib) -> {RHO, LAP}.
    allowed(k, b) -> bool (all elements have the basis and nbf <= 60).
    Tier: bitwise vs v1.0 (Chromium on Linux/glibc) for every number,
      including the numpy batch paths; "ms" (wall time) excepted.

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    Float32 storage is emulated with struct ('<f') or numpy float32; values
    read back from a Float32Array are float32 numbers in double arithmetic,
    exactly as here. The job cache holds at most 24 (k, b) states (oldest
    dropped); a lock per job makes concurrent requests for the same job
    wait instead of computing twice.

§7 TEST CASES (tests/test_aim.py)
    Oracles: Poincare-Hopf n - b + r - c = 1; sum of Bader populations =
    number of electrons; iso of a sphere-like field: all vertices at the
    level value (interpolation exact for a linear field); the volume
    density integrates to N (trapezoid, 1e-2). Differential: geometry,
    planes and the five staged runs, the MO grids, isosurfaces and bond
    profiles vs v1.0 fixtures (exact, large arrays by exact fingerprints).

§8 ERROR ANALYSIS
    The grids are display data: rho on a 0.12 bohr grid has interpolation
    errors far above rounding; the isosurface of rho = 0.001 is located to
    O(h^2 rho'') ~ 1e-3 bohr. The extrema of the ESP carry the mesh
    resolution (~0.1 bohr in position, < 1 kJ/mol in value). None of this
    affects equality with v1.0, which is exact.
"""
from __future__ import annotations

import base64
import math
import struct
import threading
import time
from collections import OrderedDict

from . import gto, qtaim
from .jsmath import cbrt, cos, js_hypot, js_round, log, sin

PI = math.pi
D2R = PI / 180
BOHR = 0.52917721092
SQ = math.sqrt


def _lin(a, b, r):
    return [[a, 0.0, 0.0, 0.0], [b, 0.0, 0.0, r]]


def _ch4(r):
    c = r / SQ(3)
    return [["C", 0.0, 0.0, 0.0], ["H", c, c, c], ["H", -c, -c, c], ["H", -c, c, -c], ["H", c, -c, -c]]


def _nh3():
    r, th = 1.012, 106.7 * D2R
    rho = r * SQ((2 - 2 * cos(th)) / 3)
    h = SQ(r * r - rho * rho)
    return [["N", 0.0, 0.0, 0.0], ["H", rho, 0.0, -h], ["H", -rho / 2, rho * SQ(3) / 2, -h], ["H", -rho / 2, -rho * SQ(3) / 2, -h]]


def _c2h4():
    cc, ch, a = 1.339, 1.087, (180 - 117.4 / 2) * D2R
    x = cc / 2
    return [["C", 0.0, 0.0, x], ["C", 0.0, 0.0, -x], ["H", 0.0, ch * sin(a), x - ch * cos(a)], ["H", 0.0, -ch * sin(a), x - ch * cos(a)],
            ["H", 0.0, ch * sin(a), -x + ch * cos(a)], ["H", 0.0, -ch * sin(a), -x + ch * cos(a)]]


def _c3h6():
    cc, ch, hch = 1.510, 1.089, 115.1 * D2R
    R = cc / SQ(3)
    a = []
    for i in range(3):
        t = 2 * PI * i / 3
        c = [cos(t), sin(t)]
        a.append(["C", R * c[0], R * c[1], 0.0])
        zr, rr = ch * sin(hch / 2), ch * cos(hch / 2)
        a.append(["H", (R + rr) * c[0], (R + rr) * c[1], zr])
        a.append(["H", (R + rr) * c[0], (R + rr) * c[1], -zr])
    return a


def _f2co():
    a = 107.6 / 2 * D2R
    return [["C", 0.0, 0.0, 0.0], ["O", 0.0, 0.0, 1.172], ["F", 0.0, 1.312 * sin(a), -1.312 * cos(a)], ["F", 0.0, -1.312 * sin(a), -1.312 * cos(a)]]


def _ring6(el2, cc, cx):
    a = []
    for i in range(6):
        t = 2 * PI * i / 6
        a.append(["C", cc * cos(t), cc * sin(t), 0.0])
    for i in range(6):
        t = 2 * PI * i / 6
        a.append([el2, (cc + cx) * cos(t), (cc + cx) * sin(t), 0.0])
    return a


GEO = {
    "H2": _lin("H", "H", 0.741), "LiH": _lin("Li", "H", 1.595), "LiF": _lin("Li", "F", 1.564), "HF": _lin("F", "H", 0.917),
    "N2": _lin("N", "N", 1.098), "CO": _lin("C", "O", 1.128), "F2": _lin("F", "F", 1.412),
    "H2O": [["O", 0.0, 0.0, 0.1173], ["H", 0.0, 0.7572, -0.4692], ["H", 0.0, -0.7572, -0.4692]],
    "NH3": _nh3(), "CH4": _ch4(1.087), "C2H4": _c2h4(),
    "C2H2": [["C", 0.0, 0.0, 0.6015], ["C", 0.0, 0.0, -0.6015], ["H", 0.0, 0.0, 1.6645], ["H", 0.0, 0.0, -1.6645]],
    "C3H6": _c3h6(), "CO2": [["O", 0.0, 0.0, -1.160], ["C", 0.0, 0.0, 0.0], ["O", 0.0, 0.0, 1.160]], "F2CO": _f2co(),
    "BF3": [["B", 0.0, 0.0, 0.0]] + [["F", 1.307 * cos(2 * PI * k / 3), 1.307 * sin(2 * PI * k / 3), 0.0] for k in range(3)],
    "C6F6": _ring6("F", 1.394, 1.327), "C6H6": _ring6("H", 1.397, 1.084),
}
_S2 = SQ(0.5)  # Math.SQRT1_2
_X = ([0.0, 0.0, 1.0], [1.0, 0.0, 0.0])
PL = {"H2": _X, "LiH": _X, "LiF": _X, "HF": _X, "N2": _X, "CO": _X, "F2": _X,
      "H2O": ([0.0, 1.0, 0.0], [0.0, 0.0, 1.0]), "NH3": ([1.0, 0.0, 0.0], [0.0, 0.0, 1.0]), "CH4": ([_S2, _S2, 0.0], [0.0, 0.0, 1.0]),
      "C2H4": ([0.0, 0.0, 1.0], [0.0, 1.0, 0.0]), "C3H6": ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]), "C6H6": ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]),
      "CO2": _X, "F2CO": ([0.0, 1.0, 0.0], [0.0, 0.0, 1.0]), "BF3": ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0]), "C6F6": ([1.0, 0.0, 0.0], [0.0, 1.0, 0.0])}
MOLS = tuple(PL)
BASES = ("STO-3G", "6-31G", "6-31G*", "6-31G**")
_NBF = {"STO-3G": (1, 5), "6-31G": (2, 9), "6-31G*": (2, 15), "6-31G**": (5, 15)}


def atoms(k):
    return [{"el": el, "x": x / BOHR, "y": y / BOHR, "z": z / BOHR} for el, x, y, z in GEO[k]]


def has_basis(b, el):
    try:
        gto.BASES[b](el)
        return True
    except Exception:  # noqa: BLE001 - v1.0 hasBasis: any failure means "no"
        return False


def nbf_of(k, b):
    h, o = _NBF[b]
    return sum(h if a[0] == "H" else o for a in GEO[k])


def allowed(k, b):
    return nbf_of(k, b) <= 60 and all(has_basis(b, a[0]) for a in GEO[k])


def meta():
    return {"M": {k: {"a": GEO[k]} for k in MOLS}, "PL": {k: [list(v) for v in PL[k]] for k in MOLS},
            "has": {b: [e for e in ("H", "Li", "B", "C", "N", "O", "F") if has_basis(b, e)] for b in BASES}}


# ---------------------------------------------------------------- map plane
def plane(at, k):
    u, w = PL[k]
    n = [u[1] * w[2] - u[2] * w[1], u[2] * w[0] - u[0] * w[2], u[0] * w[1] - u[1] * w[0]]
    inpl = [abs(a["x"] * n[0] + a["y"] * n[1] + a["z"] * n[2]) < 0.05 for a in at]
    pr = [[a["x"] * u[0] + a["y"] * u[1] + a["z"] * u[2], a["x"] * w[0] + a["y"] * w[1] + a["z"] * w[2]] for a in at]
    s0 = min(p[0] for p in pr) - 2.6
    s1 = max(p[0] for p in pr) + 2.6
    t0 = min(p[1] for p in pr) - 2.6
    t1 = max(p[1] for p in pr) + 2.6
    cx, cy = (s0 + s1) / 2, (t0 + t1) / 2
    ws, wt = max(s1 - s0, 7), max(t1 - t0, 7)
    if ws / wt > 1.6:
        wt = ws / 1.6
    if wt / ws > 1.25:
        ws = wt / 1.25
    return {"u": list(u), "w": list(w), "n": n, "inpl": inpl, "pr": pr, "s0": cx - ws / 2, "s1": cx + ws / 2, "t0": cy - wt / 2, "t1": cy + wt / 2}


def to3(P, s, t):
    return [s * P["u"][0] + t * P["w"][0], s * P["u"][1] + t * P["w"][1], s * P["u"][2] + t * P["w"][2]]


def to2(P, p):
    return [p[0] * P["u"][0] + p[1] * P["u"][1] + p[2] * P["u"][2], p[0] * P["w"][0] + p[1] * P["w"][1] + p[2] * P["w"][2]]


def off_pl(P, p):
    return abs(p[0] * P["n"][0] + p[1] * P["n"][1] + p[2] * P["n"][2])


# ---------------------------------------------------------------- float32 helpers
_F = struct.Struct("<f")


def f32(x):
    return qtaim.f32(x)


def f32_list(vals):
    np = gto._np
    if np is not None:
        return np.asarray(vals, dtype=float).astype(np.float32).astype(float).tolist()
    return [f32(v) for v in vals]


def b64_f32(vals):
    np = gto._np
    if np is not None:
        raw = np.asarray(vals, dtype=float).astype("<f4").tobytes()
    else:
        raw = struct.pack("<%df" % len(vals), *vals)
    return {"f32": base64.b64encode(raw).decode("ascii")}


def b64_u32(vals):
    return {"u32": base64.b64encode(struct.pack("<%dI" % len(vals), *vals)).decode("ascii")}


# ---------------------------------------------------------------- volume grids
def box(at, pad, max_pts, hmin):
    lo = [min(a[c] for a in at) - pad for c in "xyz"]
    hi = [max(a[c] for a in at) + pad for c in "xyz"]
    L = [hi[k] - lo[k] for k in range(3)]
    h = max(hmin, cbrt(L[0] * L[1] * L[2] / max_pts))
    n = [math.ceil(l / h) + 1 for l in L]
    return {"o": lo, "h": h, "n": n}


def _grid_xyz(G):
    """Node coordinates in v1.0 loop order (k outer, i inner) as numpy arrays."""
    np = gto._np
    nx, ny, nz = G["n"]
    x = G["o"][0] + np.arange(nx) * G["h"]
    y = G["o"][1] + np.arange(ny) * G["h"]
    z = G["o"][2] + np.arange(nz) * G["h"]
    Z, Y, X = np.meshgrid(z, y, x, indexing="ij")
    return X.ravel(), Y.ravel(), Z.ravel()


_CHUNK = 16384


def _mo_values_np(bs, C, m, ks, X, Y, Z):
    """psi_k at arrays of points, v1.0 moVals: s = sum_i C[i m + k] b_i, all i in order."""
    n = bs["nbf"]
    b = gto.bf_eval_np(bs, X, Y, Z, 0)["val"]
    out = []
    for k in ks:
        s = 0
        for i in range(n):
            s = s + C[i * m + k] * b[i]
        out.append(s)
    return out


def _mo_values(bs, C, m, ks, x, y, z):
    b = gto.bf_eval(bs, x, y, z, 0)["val"]
    n = bs["nbf"]
    out = []
    for k in ks:
        s = 0
        for i in range(n):
            s += C[i * m + k] * b[i]
        out.append(s)
    return out


def rho_grid(bs, res, G):
    nx, ny, nz = G["n"]
    occ = list(range(int(res["nocc"])))
    C, m = res["C"], res["nmo"]
    np = gto._np
    if np is not None:
        X, Y, Z = _grid_xyz(G)
        R = np.empty(X.size)
        for a in range(0, X.size, _CHUNK):
            sl = slice(a, a + _CHUNK)
            ps = _mo_values_np(bs, C, m, occ, X[sl], Y[sl], Z[sl])
            s = 0
            for p in ps:
                s = s + p * p
            R[sl] = 2 * s
        return R.astype(np.float32).astype(float).tolist()
    R = [0.0] * (nx * ny * nz)
    for k in range(nz):
        z = G["o"][2] + k * G["h"]
        for j in range(ny):
            y = G["o"][1] + j * G["h"]
            for i in range(nx):
                x = G["o"][0] + i * G["h"]
                s = 0
                for p in _mo_values(bs, C, m, occ, x, y, z):
                    s += p * p
                R[(k * ny + j) * nx + i] = f32(2 * s)
    return R


def mo_grid(bs, C, m, kmo, G):
    nx, ny, nz = G["n"]
    np = gto._np
    if np is not None:
        X, Y, Z = _grid_xyz(G)
        F = np.empty(X.size)
        for a in range(0, X.size, _CHUNK):
            sl = slice(a, a + _CHUNK)
            F[sl] = _mo_values_np(bs, C, m, [kmo], X[sl], Y[sl], Z[sl])[0]
        return F.astype(np.float32).astype(float).tolist()
    F = [0.0] * (nx * ny * nz)
    for k in range(nz):
        z = G["o"][2] + k * G["h"]
        for j in range(ny):
            y = G["o"][1] + j * G["h"]
            for i in range(nx):
                F[(k * ny + j) * nx + i] = f32(_mo_values(bs, C, m, [kmo], G["o"][0] + i * G["h"], y, z)[0])
    return F


def lap_grid(R, G):
    nx, ny, nz = G["n"]
    h2 = G["h"] * G["h"]
    np = gto._np
    if np is not None:
        A = np.asarray(R, dtype=float).reshape(nz, ny, nx)
        L = np.zeros_like(A)
        c = A[1:-1, 1:-1, 1:-1]
        L[1:-1, 1:-1, 1:-1] = (A[1:-1, 1:-1, 2:] + A[1:-1, 1:-1, :-2] + A[1:-1, 2:, 1:-1] + A[1:-1, :-2, 1:-1]
                               + A[2:, 1:-1, 1:-1] + A[:-2, 1:-1, 1:-1] - 6 * c) / h2
        return L.ravel().astype(np.float32).astype(float).tolist()
    L = [0.0] * len(R)
    for k in range(1, nz - 1):
        for j in range(1, ny - 1):
            for i in range(1, nx - 1):
                c = (k * ny + j) * nx + i
                L[c] = f32((R[c + 1] + R[c - 1] + R[c + nx] + R[c - nx] + R[c + nx * ny] + R[c - nx * ny] - 6 * R[c]) / h2)
    return L


# ---------------------------------------------------------------- isosurface (marching tetrahedra)
_TET = ((0, 5, 1, 6), (0, 1, 2, 6), (0, 2, 3, 6), (0, 3, 7, 6), (0, 7, 4, 6), (0, 4, 5, 6))
_CORN = ((0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0), (0, 0, 1), (1, 0, 1), (1, 1, 1), (0, 1, 1))


def iso(F, G, level, sign=None):
    nx, ny, nz = G["n"]
    s = sign or 1
    o0, o1, o2 = G["o"]
    h = G["h"]
    pos, nrm, idx = [], [], []
    vmap = {}

    def val(i, j, k):
        return F[(min(nz - 1, max(0, k)) * ny + min(ny - 1, max(0, j))) * nx + min(nx - 1, max(0, i))]

    def grad(i, j, k):
        return (-(val(i + 1, j, k) - val(i - 1, j, k)) * s, -(val(i, j + 1, k) - val(i, j - 1, k)) * s, -(val(i, j, k + 1) - val(i, j, k - 1)) * s)

    def vert(a, b):
        key = (a, b) if a < b else (b, a)
        v = vmap.get(key)
        if v is not None:
            return v
        ia, ja, ka = a % nx, (a // nx) % ny, a // (nx * ny)
        ib, jb, kb = b % nx, (b // nx) % ny, b // (nx * ny)
        fa = s * (F[a] - level)
        fb = s * (F[b] - level)
        t = fa / (fa - fb)
        v = len(pos) // 3
        pos.extend((o0 + (ia + t * (ib - ia)) * h, o1 + (ja + t * (jb - ja)) * h, o2 + (ka + t * (kb - ka)) * h))
        ga, gb = grad(ia, ja, ka), grad(ib, jb, kb)
        nrm.extend((ga[0] + t * (gb[0] - ga[0]), ga[1] + t * (gb[1] - ga[1]), ga[2] + t * (gb[2] - ga[2])))
        vmap[key] = v
        return v

    nxy = nx * ny
    offs = [d[0] + d[1] * nx + d[2] * nxy for d in _CORN]
    fs = [s * (x - level) for x in F]
    for k in range(nz - 1):
        for j in range(ny - 1):
            base = (k * ny + j) * nx
            for i in range(nx - 1):
                g0 = base + i
                c = [g0 + d for d in offs]
                f = [fs[q] for q in c]
                anyP = anyN = False
                for x in f:
                    if x > 0:
                        anyP = True
                    else:
                        anyN = True
                if not anyP or not anyN:
                    continue
                for t in _TET:
                    v = [c[q] for q in t]
                    fv = [f[q] for q in t]
                    ins = [q for q in range(4) if fv[q] > 0]
                    if len(ins) == 0 or len(ins) == 4:
                        continue
                    out = [q for q in range(4) if fv[q] <= 0]
                    if len(ins) == 1:
                        a = ins[0]
                        x1 = vert(v[a], v[out[0]])
                        x2 = vert(v[a], v[out[1]])
                        x3 = vert(v[a], v[out[2]])
                        idx.extend((x1, x2, x3))
                    elif len(ins) == 3:
                        a = out[0]
                        x1 = vert(v[a], v[ins[0]])
                        x2 = vert(v[a], v[ins[2]])
                        x3 = vert(v[a], v[ins[1]])
                        idx.extend((x1, x2, x3))
                    else:
                        a, b = ins
                        p, q = out
                        v1 = vert(v[a], v[p])
                        v2 = vert(v[a], v[q])
                        v3 = vert(v[b], v[q])
                        v4 = vert(v[b], v[p])
                        idx.extend((v1, v2, v3, v1, v3, v4))
    P = f32_list(pos)
    N = f32_list(nrm)
    for o in range(0, len(N), 3):
        l = js_hypot(N[o], N[o + 1], N[o + 2]) or 1
        N[o] = f32(N[o] / l)
        N[o + 1] = f32(N[o + 1] / l)
        N[o + 2] = f32(N[o + 2] / l)
    return {"pos": P, "nrm": N, "idx": idx}


def esp_on(Vf, mesh):
    P = mesh["pos"]
    nv = len(P) // 3
    np = gto._np
    if np is not None and hasattr(Vf, "many_exact"):
        return f32_list(Vf.many_exact(np.asarray(P, dtype=float).reshape(-1, 3)))
    return [f32(Vf(P[3 * i], P[3 * i + 1], P[3 * i + 2])) for i in range(nv)]


def extrema(mesh, V, rad):
    P, I = mesh["pos"], mesh["idx"]
    nv = len(V)
    nb = [set() for _ in range(nv)]
    for t in range(0, len(I), 3):
        a, b, c = I[t], I[t + 1], I[t + 2]
        nb[a].update((b, c))
        nb[b].update((a, c))
        nb[c].update((a, b))
    cand = []
    for i in range(nv):
        mx = mn = True
        for j in nb[i]:
            if V[j] > V[i]:
                mx = False
            if V[j] < V[i]:
                mn = False
        if mx:
            cand.append((i, 1))
        if mn:
            cand.append((i, -1))
    cand.sort(key=lambda c: -(c[1] * V[c[0]]))  # stable, v1.0 comparator b.s V_b - a.s V_a
    np = gto._np
    if np is not None:
        from .jsmath_np import hypot3_np
        Pa = np.asarray(P, dtype=float).reshape(-1, 3)
        Va = np.asarray(V, dtype=float)
    res = []
    for i, s in cand:
        def dist(j):
            return js_hypot(P[3 * i] - P[3 * j], P[3 * i + 1] - P[3 * j + 1], P[3 * i + 2] - P[3 * j + 2])
        if not all(t != s or dist(j) > rad for j, t in res):
            continue
        if np is not None:
            d = hypot3_np(P[3 * i] - Pa[:, 0], P[3 * i + 1] - Pa[:, 1], P[3 * i + 2] - Pa[:, 2])
            best = not bool(np.any((s * (Va - V[i]) > 1e-9) & (d < rad)))
        else:
            best = True
            for j in range(nv):
                if s * (V[j] - V[i]) > 1e-9 and dist(j) < rad:
                    best = False
                    break
        if best:
            res.append((i, s))
    out = []
    for i, s in res:
        if any(o["s"] == s and abs(o["v"] - V[i]) < 1e-3 for o in out):
            continue
        out.append({"i": i, "s": s, "v": V[i]})
    Nn = mesh["nrm"]
    return [{"p": [P[3 * o["i"]], P[3 * o["i"] + 1], P[3 * o["i"] + 2]], "n": [Nn[3 * o["i"]], Nn[3 * o["i"] + 1], Nn[3 * o["i"] + 2]],
             "v": o["v"], "type": "max" if o["s"] > 0 else "min"} for o in out]


# ---------------------------------------------------------------- the staged job
class _Job:
    def __init__(self, k, b):
        self.k, self.b = k, b
        self.lock = threading.Lock()
        self.ms = 0.0
        self.out = {}
        self.st = None


_JOBS: "OrderedDict[tuple, _Job]" = OrderedDict()
_JLOCK = threading.Lock()
MAXJOBS = 24
STAGES = ("scf", "map", "vol", "esp", "bader")


def _job(k, b):
    with _JLOCK:
        j = _JOBS.get((k, b))
        if j is None:
            j = _JOBS[(k, b)] = _Job(k, b)
            while len(_JOBS) > MAXJOBS:
                _JOBS.popitem(last=False)
        else:
            _JOBS.move_to_end((k, b))
        return j


def _cp_out(c):
    return {"p": c["p"], "type": c["type"], "rho": c["rho"], "lap": c["lap"], "l": c["l"], "eps": c.get("eps"), "G": c["G"], "V": c["V"], "H": c["H"],
            "atom": c.get("atom"), "atoms": c.get("atoms"), "path": c.get("path")}


def _scf(J):
    at = atoms(J.k)
    sys_ = gto.prep(at, J.b)
    res = gto.rhf(sys_)
    F = qtaim.make_field(sys_, res)
    cps = qtaim.find_cps(sys_, res, F)
    pa = qtaim.pop_analysis(sys_, res)
    J.st = {"sys": sys_, "res": res, "F": F, "cps": cps}
    return {"stage": "scf", "E": res["E"], "noatt": [a is None for a in qtaim.attractors(sys_["atoms"], cps)], "nbf": sys_["bs"]["nbf"],
            "it": len(res["log"]), "conv": res["converged"], "eps": list(res["eps"][:int(res["nocc"]) + 3]), "nocc": res["nocc"], "nmo": res["nmo"],
            "atoms": [{"el": a["el"], "x": a["x"], "y": a["y"], "z": a["z"], "Z": a["Z"]} for a in sys_["atoms"]],
            "cps": [_cp_out(c) for c in cps], "mul": pa["mul"], "low": pa["low"]}


def _descend_paths(F, starts, P, h, maxs, stops):
    return [qtaim.descend_plane(F, p0, P, h, maxs, stop) for p0, stop in zip(starts, stops)]


def _map(J):
    st = J.st
    sys_, res, F, cps = st["sys"], st["res"], st["F"], st["cps"]
    at = sys_["atoms"]
    P = plane(at, J.k)
    nx = min(190, int(js_round((P["s1"] - P["s0"]) / 0.065)))
    ny = int(js_round(nx * (P["t1"] - P["t0"]) / (P["s1"] - P["s0"])))
    np = gto._np
    ts = [P["t1"] - (P["t1"] - P["t0"]) * j / (ny - 1) for j in range(ny)]
    ss = [P["s0"] + (P["s1"] - P["s0"]) * i / (nx - 1) for i in range(nx)]
    if np is not None:
        T, S = np.meshgrid(np.asarray(ts), np.asarray(ss), indexing="ij")
        T, S = T.ravel(), S.ravel()
        q = to3(P, S, T)
        Rr, Lr = np.empty(S.size), np.empty(S.size)
        for a in range(0, S.size, _CHUNK):
            sl = slice(a, a + _CHUNK)
            f = gto.rho_at_np(sys_["bs"], res["D"], q[0][sl], q[1][sl], q[2][sl], 2)
            Rr[sl] = f["rho"]
            Lr[sl] = f["h"][0] + f["h"][3] + f["h"][5]
        R, L = Rr.tolist(), Lr.tolist()
    else:
        R, L = [], []
        for t in ts:
            for s in ss:
                q = to3(P, s, t)
                f = F.full(q[0], q[1], q[2], 2)
                R.append(f["rho"])
                L.append(f["h"][0] + f["h"][3] + f["h"][5])

    def in_box(q):
        p = to2(P, q)
        return P["s0"] - 0.5 < p[0] < P["s1"] + 0.5 and P["t0"] - 0.5 < p[1] < P["t1"] + 0.5
    att = qtaim.attractors(at, cps)
    saddles = [c["p"] for c in cps if c["type"] != "n"]

    def stop(q):
        return (not in_box(q)) or F.rho(q[0], q[1], q[2]) < 4e-4 or any(js_hypot(s[0] - q[0], s[1] - q[1], s[2] - q[2]) < 0.04 for s in saddles)
    gp_starts, ias_starts, ias_cp = [], [], []
    for i, a in enumerate(at):
        if not P["inpl"][i] or not att[i]:
            continue
        ns = 28 if a["el"] == "H" else 40
        r0 = 0.25 if a["el"] == "H" else 0.12
        c = att[i]
        for m in range(ns):
            ph = 2 * PI * (m + 0.5) / ns
            cph, sph = cos(ph), sin(ph)
            d = [cph * P["u"][0] + sph * P["w"][0], cph * P["u"][1] + sph * P["w"][1], cph * P["u"][2] + sph * P["w"][2]]
            gp_starts.append([c[0] + r0 * d[0], c[1] + r0 * d[1], c[2] + r0 * d[2]])
    for c in cps:
        if c["type"] != "b" or off_pl(P, c["p"]) > 0.05:
            continue
        best, bv = None, 0
        for m in range(2):
            v = c["v"][m]
            s_ = abs(v[0] * P["u"][0] + v[1] * P["u"][1] + v[2] * P["u"][2]) + abs(v[0] * P["w"][0] + v[1] * P["w"][1] + v[2] * P["w"][2])
            if s_ > bv:
                bv, best = s_, v
        cp_ = c["p"]
        for sg in (1, -1):
            ias_starts.append([cp_[0] + sg * 0.03 * best[0], cp_[1] + sg * 0.03 * best[1], cp_[2] + sg * 0.03 * best[2]])
            ias_cp.append(cp_)
    if np is not None:
        from .jsmath_np import hypot3_np

        def stop_np(excl):
            def f(Q, ix):
                p0 = Q[:, 0] * P["u"][0] + Q[:, 1] * P["u"][1] + Q[:, 2] * P["u"][2]
                p1 = Q[:, 0] * P["w"][0] + Q[:, 1] * P["w"][1] + Q[:, 2] * P["w"][2]
                inb = (p0 > P["s0"] - 0.5) & (p0 < P["s1"] + 0.5) & (p1 > P["t0"] - 0.5) & (p1 < P["t1"] + 0.5)
                st = ~inb | (F.rho_np(Q[:, 0], Q[:, 1], Q[:, 2]) < 4e-4)
                for si, sp in enumerate(saddles):
                    near = hypot3_np(sp[0] - Q[:, 0], sp[1] - Q[:, 1], sp[2] - Q[:, 2]) < 0.04
                    if excl is not None:
                        near = near & np.array([excl[k] is not sp for k in ix.tolist()], dtype=bool)
                    st = st | near
                return st
            return f
        gpp = qtaim.descend_plane_many(F, gp_starts, P, 0.07, 260, stop_np(None)) if gp_starts else []
        iap = qtaim.descend_plane_many(F, ias_starts, P, 0.05, 400, stop_np(ias_cp)) if ias_starts else []
    else:
        gpp = [qtaim.descend_plane(F, p0, P, 0.07, 260, stop) for p0 in gp_starts]

        def stop2(cp_):
            return lambda q: (not in_box(q)) or F.rho(q[0], q[1], q[2]) < 4e-4 or any(
                s is not cp_ and js_hypot(s[0] - q[0], s[1] - q[1], s[2] - q[2]) < 0.04 for s in saddles)
        iap = [qtaim.descend_plane(F, p0, P, 0.05, 400, stop2(cp_)) for p0, cp_ in zip(ias_starts, ias_cp)]
    gp = [[to2(P, q) for q in pts] for pts in gpp]
    ias = [[to2(P, cp_)] + [to2(P, q) for q in pts] for pts, cp_ in zip(iap, ias_cp)]
    bpaths = [[[to2(P, q) for q in hh] for hh in c["path"]] for c in cps if c["type"] == "b" and off_pl(P, c["p"]) < 0.05]
    return {"stage": "map", "P": {"s0": P["s0"], "s1": P["s1"], "t0": P["t0"], "t1": P["t1"], "inpl": P["inpl"], "pr": P["pr"]},
            "nx": nx, "ny": ny, "R": f32_list(R), "L": f32_list(L), "gp": gp, "ias": ias, "bpaths": bpaths,
            "cp2": [{"xy": to2(P, c["p"]), "off": off_pl(P, c["p"]), "type": c["type"]} for c in cps]}


def _vol(J):
    st = J.st
    sys_, res = st["sys"], st["res"]
    G = box(sys_["atoms"], 4.5, 110000, 0.12)
    R = rho_grid(sys_["bs"], res, G)
    GL = box(sys_["atoms"], 2.2, 170000, 0.07)
    L = lap_grid(rho_grid(sys_["bs"], res, GL), GL)
    st["G"] = G
    return {"stage": "vol", "G": G, "R": R, "GL": GL, "L": L}


def _esp(J):
    st = J.st
    sys_, res = st["sys"], st["res"]
    Gc = box(sys_["atoms"], 4.5, 42000, 0.2)
    Rc = [f32(log(x + 1e-30)) for x in rho_grid(sys_["bs"], res, Gc)]
    mesh = iso(Rc, Gc, log(0.001))
    Vf = gto.esp_prep(sys_, res)
    V = esp_on(Vf, mesh)
    return {"stage": "esp", "mesh": mesh, "V": V, "ext": extrema(mesh, V, 1.6)}


def _bader(J):
    st = J.st
    bd = qtaim.bader_charges(st["sys"], st["res"], st["F"], st["cps"])
    return {"stage": "bader", "q": bd["q"], "pop": bd["pop"], "tot": bd["tot"]}


_RUN = {"scf": _scf, "map": _map, "vol": _vol, "esp": _esp, "bader": _bader}


def stage(k, b, name):
    """Message of stage `name` for molecule k, basis b (computed once; plain lists of floats)."""
    if k not in PL or b not in BASES or name not in _RUN:
        raise ValueError("unknown molecule, basis or stage")
    if not allowed(k, b):
        raise ValueError(f"{k}/{b}: basis not available or too many basis functions")
    J = _job(k, b)
    with J.lock:
        for s in STAGES:
            if s in J.out:
                if s == name:
                    break
                continue
            t0 = time.perf_counter()
            msg = _RUN[s](J)
            J.ms += (time.perf_counter() - t0) * 1000
            msg["ms"] = round(J.ms)
            J.out[s] = msg
            if s == name:
                break
        return J.out[name]


def state(k, b):
    """(sys, res) of a job whose scf stage is done (computing it if needed)."""
    stage(k, b, "scf")
    st = _job(k, b).st
    return st["sys"], st["res"]


def mo(k, b, kmo):
    """One MO on the 'vol' grid G (float32 values)."""
    sys_, res = state(k, b)
    if not 0 <= kmo < res["nmo"]:
        raise ValueError("no such orbital")
    G = stage(k, b, "vol")["G"]
    return mo_grid(sys_["bs"], res["C"], res["nmo"], kmo, G)


def prof(k, b, ia, ib):
    """rho and its Laplacian at 421 points on the line through nuclei ia -> ib (v1.0 prof())."""
    sys_, res = state(k, b)
    at = sys_["atoms"]
    if not (0 <= ia < len(at) and 0 <= ib < len(at)) or ia == ib:
        raise ValueError("bad atom indices")
    bs = gto.build_basis([{"el": a["el"], "x": a["x"], "y": a["y"], "z": a["z"], "Z": a["Z"]} for a in at], b)
    n, m, C, o = bs["nbf"], res["nmo"], res["C"], int(res["nocc"])
    D = [0.0] * (n * n)
    for i in range(n):
        for j in range(i + 1):
            v = 0
            for q in range(o):
                v += C[i * m + q] * C[j * m + q]
            D[i * n + j] = D[j * n + i] = 2 * v
    A, B = at[ia], at[ib]
    d = [B["x"] - A["x"], B["y"] - A["y"], B["z"] - A["z"]]
    L = js_hypot(*d)
    u = [x / L for x in d]
    s0, s1, N = -1.2, L + 1.2, 420
    ts = [s0 + (s1 - s0) * q / N for q in range(N + 1)]
    np = gto._np
    if np is not None:
        t = np.asarray(ts)
        r = gto.rho_at_np(bs, D, A["x"] + u[0] * t, A["y"] + u[1] * t, A["z"] + u[2] * t, 2)
        return {"RHO": r["rho"].tolist(), "LAP": (r["h"][0] + r["h"][3] + r["h"][5]).tolist()}
    RHO, LAP = [], []
    for t in ts:
        r = gto.rho_at(bs, D, A["x"] + u[0] * t, A["y"] + u[1] * t, A["z"] + u[2] * t, 2)
        RHO.append(r["rho"])
        LAP.append(r["h"][0] + r["h"][3] + r["h"][5])
    return {"RHO": RHO, "LAP": LAP}


def encode(msg):
    """Message for the page: float32 arrays and index arrays as base64 (see §2)."""
    out = dict(msg)
    st = msg["stage"]
    if st in ("map", "vol"):
        out["R"], out["L"] = b64_f32(msg["R"]), b64_f32(msg["L"])
    if st == "esp":
        me = msg["mesh"]
        out["mesh"] = {"pos": b64_f32(me["pos"]), "nrm": b64_f32(me["nrm"]), "idx": b64_u32(me["idx"])}
        out["V"] = b64_f32(msg["V"])
    return out

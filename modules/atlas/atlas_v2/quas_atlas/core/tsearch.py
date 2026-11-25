"""The search for a transition state and the reaction path: eigenvector following, IRC, the nudged elastic band,
a relaxed scan — on model surfaces of two coordinates.

HEADER
    Model of the page "Поиск переходного состояния и путь реакции" (web/<lang>/tsneb.html), Atlas 2026-11-24;
    lecture 3 of the course «Квантово-химические методы» (its derivations 2 and 3). Wilkinson convention, §1-§8.

§1 THEORY
    A transition state is a first-order saddle point: zero gradient, one negative eigenvalue of the Hessian. A minimizer
    (BFGS keeps its Hessian positive) rolls down from it. Eigenvector following: in the basis of the modes the Newton
    step falls apart into steps along each mode, −g_i/λ_i; for a saddle the step along the followed mode goes up,
    +g_i/|λ_i|, along all the others down, −g_i/|λ_i|; each limited by a trust radius. The lecture surface
    E = (x² − 1)² + y² (minima (±1, 0), the saddle (0, 0) with E = 1, H = diag(12x² − 4, 2)): from (0.8, 0.3) with the
    radius 0.3 — (0.5, 0), (0.2, 0), (−0.018, 0), (0, 0), λ = (−4, 2); plain Newton goes to the minimum (1.11, 0).
    The intrinsic reaction coordinate (IRC): from the saddle a small step along the negative mode, both ways, then
    steepest descent (in mass-weighted coordinates; here the masses are equal) — it must end in the reactant and in
    the product.
    The nudged elastic band (NEB): images R_i between the reactant and the product; the tangent τ_i = (R_{i+1} −
    R_{i−1})/|…|; the force F_i = −∇E_i + (∇E_i·τ_i)τ_i + k(|R_{i+1} − R_i| − |R_i − R_{i−1}|)τ_i — of the true force
    only the part across the path, of the springs only the part along it. Without the projections (the plain band)
    the springs pull the images off the valley (corners cut) and the true force drags them down to the ends. The
    climbing image (CI-NEB): the highest image has no spring and climbs along the path, F = −∇E + 2(∇E·τ)τ — it
    converges to the saddle.
    A relaxed scan: one coordinate fixed in turn, the others optimized; the maximum of the profile is not checked —
    when the reaction runs along two coordinates at once, the profile can jump into the other valley, and the scan
    forward and the scan backward differ (hysteresis).
    The Müller–Brown surface (K. Müller, L. D. Brown, Theor. Chim. Acta 53, 75 (1979)): minima A (−0.558, 1.442),
    E = −146.70, and C (−0.050, 0.467), −80.77; between them the saddle (−0.822, 0.624), −40.66, on a curved path.

§2 ALGORITHM
    Eigenvector following: the 2 × 2 Hessian diagonalized; the followed mode is the one closest to the previous
    followed direction (at the start the chosen axis); the steps in the eigenbasis clipped to the radius.
    NEB: steepest descent of all images at once, each move clipped to 0.02; 1500 iterations; the climbing image
    switched on after 300. The scan: 41 values of the coordinate, at each the other one optimized by Newton from the
    previous point. The saddle of Müller–Brown: Newton from (−0.82, 0.62).

§3 APPLICATIONS
    Endpoints ts.follow, ts.neb, ts.scan.

§4 SPECIFICATION
    follow(x0, y0, mode='x', radius=0.3) -> {"ef": [[x, y, E]], "newton": [[x, y, E]], "lam": [λ1, λ2], "found", "steps",
        "irc": [[[x, y]], [[x, y]]], "grid": {...}}.
    neb(n, k, kind) -> {"images": [[x, y]], "E": [E], "start": [[x, y]], "barrier", "saddle": {"x", "y", "E"},
        "top_distance", "gradients", "grid": {...}}  kind 'plain' | 'neb' | 'ci'.
    scan(coord) -> {"forward": {"q", "E", "x", "y"}, "backward": {...}, "max_f", "max_b", "saddle": {...}, "grid"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (the site runs it in Pyodide). Energies of Müller–Brown in its own units.
§7 TEST CASES (tests/atlas/test_atlas_tsearch.py)
    The steps of the lecture (0.8, 0.3) → (0.5, 0) → (0.2, 0) → (−0.018, 0) → (0, 0) and λ = (−4, 2); Newton → (1.11, 0);
    the IRC ends at (±1, 0); the saddle of Müller–Brown (−0.822, 0.624), −40.66; CI-NEB converges to it, the plain band
    does not; the scan forward and backward differ.
§8 ERROR ANALYSIS
    Two coordinates only: in a molecule the same algorithms work in 3N − 6.
"""

import math

MB_A = (-200.0, -100.0, -170.0, 15.0)
MB_a = (-1.0, -1.0, -6.5, 0.7)
MB_b = (0.0, 0.0, 11.0, 0.6)
MB_c = (-10.0, -10.0, -6.5, 0.7)
MB_x = (1.0, 0.0, -0.5, -1.0)
MB_y = (0.0, 0.5, 1.5, 1.0)
MB_MIN_A = (-0.558224, 1.441726)
MB_MIN_C = (-0.050011, 0.466694)


def mb(x, y):
    """The Müller–Brown energy and its gradient."""
    e = gx = gy = 0.0
    for A, a, b, c, x0, y0 in zip(MB_A, MB_a, MB_b, MB_c, MB_x, MB_y):
        dx, dy = x - x0, y - y0
        t = A * math.exp(a * dx * dx + b * dx * dy + c * dy * dy)
        e += t
        gx += t * (2 * a * dx + b * dy)
        gy += t * (b * dx + 2 * c * dy)
    return e, gx, gy


def _hess(f, x, y, h=1e-4):
    _, gx1, gy1 = f(x + h, y)
    _, gx0, gy0 = f(x - h, y)
    _, hx1, hy1 = f(x, y + h)
    _, hx0, hy0 = f(x, y - h)
    hxx, hyy = (gx1 - gx0) / (2 * h), (hy1 - hy0) / (2 * h)
    hxy = ((gy1 - gy0) + (hx1 - hx0)) / (4 * h)
    return hxx, hxy, hyy


def _eig2(hxx, hxy, hyy):
    """Eigenvalues (ascending) and unit eigenvectors of a symmetric 2 × 2 matrix."""
    tr, det = hxx + hyy, hxx * hyy - hxy * hxy
    d = math.sqrt(max(tr * tr / 4 - det, 0.0))
    out = []
    for lam in (tr / 2 - d, tr / 2 + d):
        if abs(hxy) > 1e-14:
            v = (lam - hyy, hxy)
        else:
            v = (1.0, 0.0) if abs(hxx - lam) <= abs(hyy - lam) else (0.0, 1.0)
        n = math.hypot(*v)
        out.append((lam, (v[0] / n, v[1] / n)))
    return out


def quartic(x, y):
    """The surface of the lecture: (x² − 1)² + y²."""
    return (x * x - 1) ** 2 + y * y, 4 * x * (x * x - 1), 2 * y


def _grid(f, x0, x1, y0, y1, n=48, cap=None):
    xs = [x0 + (x1 - x0) * i / (n - 1) for i in range(n)]
    ys = [y0 + (y1 - y0) * j / (n - 1) for j in range(n)]
    rows = []
    for y in ys:
        row = []
        for x in xs:
            e = f(x, y)[0]
            row.append(min(e, cap) if cap is not None else e)
        rows.append(row)
    return {"x": xs, "y": ys, "E": rows}


def _ef_steps(f, x, y, follow, radius, newton=False, steps=30):
    path = [[x, y, f(x, y)[0]]]
    direction = follow
    lam = None
    for _ in range(steps):
        e, gx, gy = f(x, y)
        modes = _eig2(*_hess(f, x, y))
        j = max(range(2), key=lambda i: abs(modes[i][1][0] * direction[0] + modes[i][1][1] * direction[1]))
        sx = sy = 0.0
        for i, (l, v) in enumerate(modes):
            g = gx * v[0] + gy * v[1]
            if newton:
                s = -g / l if abs(l) > 1e-12 else 0.0
            else:
                s = (g if i == j else -g) / max(abs(l), 1e-12)
            s = max(-radius, min(radius, s))
            sx += s * v[0]
            sy += s * v[1]
        v = modes[j][1]
        direction = v if v[0] * direction[0] + v[1] * direction[1] >= 0 else (-v[0], -v[1])
        x, y = x + sx, y + sy
        path.append([x, y, f(x, y)[0]])
        if math.hypot(sx, sy) < 1e-9:
            break
    lam = [m[0] for m in _eig2(*_hess(f, x, y))]
    return path, lam


def _descend(f, x, y, step=0.01, n=600):
    pts = [[x, y]]
    for _ in range(n):
        _, gx, gy = f(x, y)
        g = math.hypot(gx, gy)
        if g < 1e-6:
            break
        s = min(step, 0.5 * g)
        x, y = x - s * gx / g, y - s * gy / g
        pts.append([x, y])
    return pts


def follow(x0=0.8, y0=0.3, mode="x", radius=0.3):
    """Eigenvector following on (x² − 1)² + y² from (x0, y0), the followed mode along x or y; plain Newton from the
    same point; the IRC from the point found when it is a saddle."""
    if not (-1.6 <= x0 <= 1.6 and -1.2 <= y0 <= 1.2 and mode in ("x", "y") and 0.05 <= radius <= 1):
        raise ValueError("x0 −1.6..1.6, y0 −1.2..1.2, mode x | y, radius 0.05..1")
    start = (1.0, 0.0) if mode == "x" else (0.0, 1.0)
    ef, lam = _ef_steps(quartic, x0, y0, start, radius, steps=25)
    nw, _ = _ef_steps(quartic, x0, y0, start, radius, newton=True, steps=25)
    end = ef[-1]
    saddle = lam[0] < 0 < lam[1] and math.hypot(*quartic(end[0], end[1])[1:]) < 1e-6
    irc = []
    if saddle:
        v = _eig2(*_hess(quartic, end[0], end[1]))[0][1]
        for sgn in (1, -1):
            irc.append(_descend(quartic, end[0] + sgn * 0.02 * v[0], end[1] + sgn * 0.02 * v[1]))
    steps = next((i for i, p in enumerate(ef) if math.hypot(*quartic(p[0], p[1])[1:]) < 1e-3), None)  # |g| < 0.001
    return {"ef": ef, "newton": nw, "lam": lam, "found": saddle, "irc": irc, "steps": steps,
            "grid": _grid(quartic, -1.6, 1.6, -1.2, 1.2, cap=2.5)}


def mb_saddle(x=-0.82, y=0.62):
    for _ in range(50):
        _, gx, gy = mb(x, y)
        hxx, hxy, hyy = _hess(mb, x, y)
        det = hxx * hyy - hxy * hxy
        dx, dy = -(hyy * gx - hxy * gy) / det, -(-hxy * gx + hxx * gy) / det
        x, y = x + dx, y + dy
        if math.hypot(dx, dy) < 1e-12:
            break
    return {"x": x, "y": y, "E": mb(x, y)[0]}


def neb(n=9, k=50.0, kind="ci", iters=1500):
    """A band of n images (the ends fixed at A and C of Müller–Brown) relaxed by steepest descent: plain springs,
    NEB, or NEB with the climbing image."""
    if not (3 <= n <= 21 and 1 <= k <= 1000 and kind in ("plain", "neb", "ci")):
        raise ValueError("n 3..21, k 1..1000, kind plain | neb | ci")
    (ax, ay), (cx, cy) = MB_MIN_A, MB_MIN_C
    R = [[ax + (cx - ax) * i / (n - 1), ay + (cy - ay) * i / (n - 1)] for i in range(n)]
    start = [p[:] for p in R]
    alpha, cap = 2e-4, 0.02
    gradients = 0
    for it in range(iters):
        E = [mb(*p) for p in R]
        gradients += n - 2
        top = max(range(1, n - 1), key=lambda i: E[i][0])
        new = [p[:] for p in R]
        for i in range(1, n - 1):
            tx, ty = R[i + 1][0] - R[i - 1][0], R[i + 1][1] - R[i - 1][1]
            tn = math.hypot(tx, ty) or 1.0
            tx, ty = tx / tn, ty / tn
            _, gx, gy = E[i]
            d1 = math.hypot(R[i + 1][0] - R[i][0], R[i + 1][1] - R[i][1])
            d0 = math.hypot(R[i][0] - R[i - 1][0], R[i][1] - R[i - 1][1])
            if kind == "plain":
                fx = -gx + k * (R[i + 1][0] - 2 * R[i][0] + R[i - 1][0])
                fy = -gy + k * (R[i + 1][1] - 2 * R[i][1] + R[i - 1][1])
            else:
                gt = gx * tx + gy * ty
                if kind == "ci" and i == top and it >= 300:
                    fx, fy = -gx + 2 * gt * tx, -gy + 2 * gt * ty
                else:
                    fs = k * (d1 - d0)
                    fx, fy = -gx + gt * tx + fs * tx, -gy + gt * ty + fs * ty
            dx, dy = alpha * fx, alpha * fy
            m = math.hypot(dx, dy)
            if m > cap:
                dx, dy = dx * cap / m, dy * cap / m
            new[i] = [R[i][0] + dx, R[i][1] + dy]
        R = new
    E = [mb(*p)[0] for p in R]
    s = mb_saddle()
    top = max(range(n), key=lambda i: E[i])
    return {"images": R, "E": E, "start": start, "barrier": E[top] - E[0], "saddle": s,
            "true_barrier": s["E"] - mb(*MB_MIN_A)[0], "top": top,
            "top_distance": math.hypot(R[top][0] - s["x"], R[top][1] - s["y"]), "gradients": gradients,
            "grid": _grid(mb, -1.5, 0.7, 0.0, 2.0, n=48, cap=0.0)}


def _relax(fix, q, other, steps=60):
    """Minimize Müller–Brown over the other coordinate with the coordinate `fix` held at q (Newton, damped)."""
    for _ in range(steps):
        x, y = (q, other) if fix == "x" else (other, q)
        _, gx, gy = mb(x, y)
        hxx, _, hyy = _hess(mb, x, y)
        g, h = (gy, hyy) if fix == "x" else (gx, hxx)
        step = -g / h if h > 1e-9 else -0.01 * math.copysign(1, g)
        step = max(-0.05, min(0.05, step))
        other += step
        if abs(step) < 1e-10:
            break
    return other


def scan(coord="y", n=41):
    """A relaxed scan of x or y from A to C (forward) and from C to A (backward)."""
    if coord not in ("x", "y"):
        raise ValueError("coord x | y")
    (ax, ay), (cx, cy) = MB_MIN_A, MB_MIN_C
    q0, q1 = (ax, cx) if coord == "x" else (ay, cy)
    o0, o1 = (ay, cy) if coord == "x" else (ax, cx)
    qs = [q0 + (q1 - q0) * i / (n - 1) for i in range(n)]

    def run(values, other):
        out = {"q": [], "E": [], "x": [], "y": []}
        for q in values:
            other = _relax(coord, q, other)
            x, y = (q, other) if coord == "x" else (other, q)
            out["q"].append(q)
            out["E"].append(mb(x, y)[0])
            out["x"].append(x)
            out["y"].append(y)
        return out

    fwd = run(qs, o0)
    bwd = run(list(reversed(qs)), o1)
    s = mb_saddle()
    return {"forward": fwd, "backward": bwd, "max_f": max(fwd["E"]), "max_b": max(bwd["E"]), "saddle": s,
            "E_A": mb(ax, ay)[0], "grid": _grid(mb, -1.5, 0.7, 0.0, 2.0, n=48, cap=0.0)}

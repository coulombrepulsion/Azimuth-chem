"""Molecular dynamics and machine learning: the Verlet integrator, a committee of learned potentials, fluctuations and
rare events; Δ-learning, the honest test of a model, the convex hull of a screening.

HEADER
    Model of the pages "Молекулярная динамика и потенциалы машинного обучения" (web/<lang>/mlmd.html) and "Машинное
    обучение в квантовой химии" (web/<lang>/mlqc.html), Atlas 2026-11-24; lectures 16 and 17 of the course
    «Квантово-химические методы». Wilkinson convention, sections 1-8.

§1 THEORY
    Velocity Verlet: v½ = v + Δt·F/(2m); r′ = r + Δt·v½; v′ = v½ + Δt·F(r′)/(2m). It is reversible in time, the error
    of the energy does not grow but oscillates, ∝ Δt². Euler (r′ = r + Δt·v, v′ = v + Δt·F/m) is not: its energy
    grows every step. The step is a tenth to a twentieth of the period of the fastest vibration: O–H 3700 cm⁻¹ — 9 fs,
    Δt ≤ 0.5 fs; the optical phonon of Si 15.5 THz — 64 fs, Δt ≤ 3–6 fs.
    A committee of M models trained on different random parts of the data: the mean Ē and the spread σ² = ⟨(E_m − Ē)²⟩.
    Where the data are many the models agree; outside the training range each extrapolates in its own way — σ grows
    with the error, and σ > 3σ_train sends the structure to a DFT calculation (active learning).
    The instantaneous temperature T = 2E_kin/(3Nk) is a sum of 3N squares: δT/T = sqrt(2/(3N)) (64 atoms: ±10 %).
    A barrier ΔG is crossed at the Eyring rate k = (kT/h)·e^{−ΔG/kT}: the events a trajectory of length t sees are k·t.
    Δ-learning: E_expensive = E_cheap + Δ; the error of a model at n data scales with the spread of what it learns,
    so the smooth small Δ is learned with fewer data; the learning curve δ = A·n^{−a} is a straight line in log axes.
    Kernel ridge regression (KRR): f(x) = Σ_j α_j k(x, x_j), (K + λI)α = y; here k = e^{−|x − x′|/σ} (the Laplacian
    kernel of the lecture) for Δ-learning and the Gaussian kernel for the committee.
    The test of a model: MAE = (1/n)Σ|e_k| is a mean and is known within δ(MAE) = σ(|e|)/√n; for normal errors
    σ(|e|)/MAE = sqrt(π/2 − 1) ≈ 0.75 — 20 test molecules: ±17 %.
    The convex hull of a binary system A–B: the formation energies per atom of the known phases against the share x of
    B; the lower convex envelope. A new compound is stable when it lies below the hull; above it, it decomposes into
    the two neighbouring phases. Here x = 1/3 at −0.40 and x = 1/2 at −0.50 eV/atom: at x = 0.4 the hull is −0.44, a
    compound at −0.41 is 30 meV/atom above it (the lecture's −0.30 at x = 1/3 lies above the line from A to AB itself).

§2 ALGORITHM
    The oscillator: a Morse bond V = De(1 − e^{−a(r − r0)})², a = ω·sqrt(μ/(2De)), started at rest from the turning
    point of the energy E0; Verlet or Euler for the time t_end; the total energy against time.
    KRR: the matrix K + λI solved by Cholesky. The committee: M = 5 models, each on a fixed pseudo-random 70 % of the
    points. Δ-learning: random training points (fixed seed) in the range, the MAE on a grid of 200 test points, for
    n = 4…128; a — the slope of the line through the logarithms (least squares).
    The hull: the lower convex envelope of the points (monotone chain), its value at x by interpolation.

§3 APPLICATIONS
    Endpoints ml.verlet, ml.committee, ml.events (mlmd.html); ml.delta, ml.mae, ml.hull (mlqc.html).

§4 SPECIFICATION
    verlet(system, dt, method, E0, t_end=200) -> {"t" (fs), "dE" (meV), "period", "steps", "max", "drift", "nu"}.
    committee(n, hi, M=5, sigma=0.25) -> {"r", "true", "mean", "spread", "train": {"r", "E"}, "flag": [bool],
        "err_in", "err_out", "sigma_in", "sigma_out", "at"}  (eV, Å).
    events(N, T, barrier, length_ps) -> {"dT", "rel", "rate", "wait_ps", "events", "steps", "ml_hours", "dft_days",
        "curve": {"barrier", "wait_ps"}}.
    delta(n, cheap, sigma) -> {"ns", "direct", "delta", "a_direct", "a_delta", "at": {"n", "direct", "delta"}, "x",
        "true", "cheap", "fit_direct", "fit_delta", "train"}.
    mae(n, mae_a, mae_b) -> {"ns", "a": {"mean", "lo", "hi"}, "b": {...}, "at": {...}, "rel"}.
    hull(e13, e12, x, e) -> {"phases", "hull": {"x", "E"}, "at_hull", "above"}.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    Standard library only (the site runs it in Pyodide). Units: eV, Å, fs, amu; 1 eV/(amu·Å²) → (fs)⁻²: 9.6485e-3.
§7 TEST CASES (tests/atlas/test_atlas_ml.py)
    The periods 9.0 fs (3700 cm⁻¹) and 64.5 fs (15.5 THz); the Verlet error ∝ Δt², Euler's energy grows; the committee
    small inside the training range and large outside; δT/T = sqrt(2/(3N)) (0.10 for 64 atoms); the Eyring rate;
    the slopes of the learning curves positive and the Δ model better at small n; δ(MAE)/MAE → 0.75/√n; the hull:
    −0.44 at x = 0.4, +30 meV for −0.41.
§8 ERROR ANALYSIS
    The models are illustrations of the lecture, one-dimensional: a real potential has hundreds of coordinates. The
    random choices are fixed (the same answer for the same input).
"""

import math

K_B = 8.617333262e-5  # eV/K
H_EV = 4.135667696e-15  # eV·s
C_CM = 2.99792458e10  # cm/s
ACC = 9.648533212e-3  # 1 eV/(amu·Å) in Å/fs²
SYSTEMS = {  # ω (cm⁻¹), reduced mass (amu), De (eV), r0 (Å)
    'oh': {'wn': 3700.0, 'mu': 0.9483, 'De': 4.6, 'r0': 0.97},
    'od': {'wn': 2700.0, 'mu': 1.7889, 'De': 4.6, 'r0': 0.97},
    'si': {'wn': 15.5e12 / C_CM, 'mu': 14.04, 'De': 2.3, 'r0': 2.35},
}


def _lcg(seed, n):
    state = seed * 2654435761 % 2 ** 32 or 1
    out = []
    for _ in range(n):
        state = (1103515245 * state + 12345) % 2 ** 31
        out.append(state / 2 ** 31)
    return out


def verlet(system="oh", dt=0.5, method="verlet", E0=0.3, t_end=200.0):
    """The total energy of a Morse bond integrated by velocity Verlet or by Euler; meV against fs."""
    if system not in SYSTEMS or method not in ("verlet", "euler") or not (0.05 <= dt <= 10 and 0.01 <= E0 <= 2):
        raise ValueError("system oh | od | si, method verlet | euler, dt 0.05..10 fs, E0 0.01..2 eV")
    s = SYSTEMS[system]
    nu = s['wn'] * C_CM  # 1/s
    period = 1e15 / nu  # fs
    omega = 2 * math.pi * nu * 1e-15  # 1/fs
    De, mu, r0 = s['De'], s['mu'], s['r0']
    a = omega * math.sqrt(mu / (2 * De * ACC))  # 1/Å: ω² = 2De·a²/μ
    V = lambda r: De * (1 - math.exp(-a * (r - r0))) ** 2
    F = lambda r: -2 * De * a * math.exp(-a * (r - r0)) * (1 - math.exp(-a * (r - r0)))
    E0 = min(E0, 0.9 * De)
    r = r0 - math.log(1 + math.sqrt(E0 / De)) / a  # the inner turning point
    v = 0.0
    e_start = V(r)
    steps = int(round(t_end / dt))
    ts, de = [0.0], [0.0]
    every = max(1, steps // 400)
    for i in range(1, steps + 1):
        if method == "verlet":
            vh = v + dt * F(r) / mu * ACC / 2
            r = r + dt * vh
            v = vh + dt * F(r) / mu * ACC / 2
        else:
            f = F(r)
            r, v = r + dt * v, v + dt * f / mu * ACC
        e = 0.5 * mu * v * v / ACC + V(r)
        if not math.isfinite(e) or e > 50 * De:
            ts.append(i * dt)
            de.append(float('nan'))
            break
        if i % every == 0 or i == steps:
            ts.append(i * dt)
            de.append((e - e_start) * 1000)
    good = [x for x in de if math.isfinite(x)]
    return {"t": ts, "dE": de, "period": period, "nu": nu, "steps": steps, "ratio": dt / period,
            "max": max(abs(x) for x in good), "drift": good[-1], "blown": len(good) < len(de)}


def _cholesky_solve(A, b):
    n = len(b)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = A[i][j] - sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                L[i][i] = math.sqrt(max(s, 1e-14))
            else:
                L[i][j] = s / L[j][j]
    y = [0.0] * n
    for i in range(n):
        y[i] = (b[i] - sum(L[i][k] * y[k] for k in range(i))) / L[i][i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (y[i] - sum(L[k][i] * x[k] for k in range(i + 1, n))) / L[i][i]
    return x


def _krr(xs, ys, kernel, lam):
    n = len(xs)
    A = [[kernel(xs[i], xs[j]) + (lam if i == j else 0.0) for j in range(n)] for i in range(n)]
    mean = sum(ys) / n
    alpha = _cholesky_solve(A, [y - mean for y in ys])
    return lambda x: mean + sum(a * kernel(x, xj) for a, xj in zip(alpha, xs))


def _morse(r, De=2.3, a=1.6, r0=2.35):
    return De * (1 - math.exp(-a * (r - r0))) ** 2 - De


def committee(n=16, hi=2.9, M=5, sigma=0.25):
    """M Gaussian-kernel models of a Morse bond (the «DFT»), each on 70 % of n points between 2.15 Å and hi; their mean
    and spread from 1.85 to 3.6 Å; where the spread exceeds three times the one inside the training range."""
    if not (4 <= n <= 40 and 2.4 <= hi <= 3.5):
        raise ValueError("n 4..40, hi 2.4..3.5 Å")
    lo = 2.15
    xs = [lo + (hi - lo) * i / (n - 1) for i in range(n)]
    ys = [_morse(x) for x in xs]
    kern = lambda x, y: math.exp(-((x - y) / sigma) ** 2 / 2)
    models = []
    for m in range(M):
        pick = [i for i, u in enumerate(_lcg(17 + m, n)) if u < 0.7] or [0, n - 1]
        if len(pick) < 3:
            pick = list(range(n))
        models.append(_krr([xs[i] for i in pick], [ys[i] for i in pick], kern, 1e-6))
    rs = [1.85 + 1.75 * i / 175 for i in range(176)]
    preds = [[f(r) for f in models] for r in rs]
    mean = [sum(p) / M for p in preds]
    spread = [math.sqrt(sum((q - mu) ** 2 for q in p) / M) for p, mu in zip(preds, mean)]
    true = [_morse(r) for r in rs]
    inside = [i for i, r in enumerate(rs) if lo <= r <= hi]
    outside = [i for i in range(len(rs)) if i not in inside]
    s_in = math.sqrt(sum(spread[i] ** 2 for i in inside) / len(inside))
    flag = [s > 3 * s_in for s in spread]
    err = lambda idx: sum(abs(mean[i] - true[i]) for i in idx) / len(idx)
    return {"r": rs, "true": true, "mean": mean, "spread": spread, "train": {"r": xs, "E": ys}, "flag": flag,
            "err_in": err(inside), "err_out": err(outside), "sigma_in": s_in,
            "sigma_out": math.sqrt(sum(spread[i] ** 2 for i in outside) / len(outside)),
            "at": {"r": rs[0], "err": abs(mean[0] - true[0]), "sigma": spread[0]}, "lo": lo, "hi": hi}


def events(N=64, T=300.0, barrier=0.8, length_ps=100.0):
    """δT of N atoms; the Eyring rate of a barrier at T, the waiting time, the events in a trajectory; its cost with a
    learned potential (30 ms a step) and with DFT (3 min a step) at Δt = 1 fs."""
    if not (2 <= N <= 1e6 and 50 <= T <= 3000 and 0.05 <= barrier <= 3 and 0.1 <= length_ps <= 1e7):
        raise ValueError("N 2..1e6, T 50..3000 K, barrier 0.05..3 eV, length 0.1..1e7 ps")
    rel = math.sqrt(2 / (3 * N))
    pre = K_B * T / H_EV  # 1/s
    rate = lambda g: pre * math.exp(-g / (K_B * T))
    k = rate(barrier)
    steps = length_ps * 1000
    bs = [0.1 + 1.9 * i / 95 for i in range(96)]
    return {"rel": rel, "dT": rel * T, "rate": k, "wait_ps": 1e12 / k, "events": k * length_ps * 1e-12,
            "steps": steps, "ml_hours": steps * 0.03 / 3600, "dft_days": steps * 180 / 86400,
            "curve": {"barrier": bs, "wait_ps": [1e12 / rate(b) for b in bs]}}


def _target(x, cheap):
    """«Expensive»: a Morse curve with a small wiggle; «cheap»: a harmonic-like approximation that misses by `cheap`."""
    expensive = 4.0 * (1 - math.exp(-1.8 * (x - 1.0))) ** 2 + 0.15 * math.sin(6 * x)
    approx = 4.0 * (1 - math.exp(-1.8 * (1 + cheap * 0.2) * (x - 1.0))) ** 2
    return expensive, approx


def delta(n=16, cheap=0.5, sigma=0.5):
    """Learning curves of KRR (Laplacian kernel) learning the «expensive» energy directly or as a correction to the
    cheap one; the MAE on 200 test points for n = 4…128; the slopes; the fits at the chosen n."""
    if not (4 <= n <= 128 and 0 <= cheap <= 1 and 0.05 <= sigma <= 3):
        raise ValueError("n 4..128, cheap 0..1, sigma 0.05..3")
    lo, hi = 0.75, 2.5
    test = [lo + (hi - lo) * (i + 0.5) / 200 for i in range(200)]
    kern = lambda x, y: math.exp(-abs(x - y) / sigma)
    rnd = _lcg(5, 128)
    pool = [lo + (hi - lo) * u for u in rnd]

    def fit(m):
        xs = pool[:m]
        e = [_target(x, cheap) for x in xs]
        direct = _krr(xs, [a for a, _ in e], kern, 1e-8)
        corr = _krr(xs, [a - b for a, b in e], kern, 1e-8)
        return direct, corr

    def maes(m):
        direct, corr = fit(m)
        d = c = 0.0
        for x in test:
            a, b = _target(x, cheap)
            d += abs(direct(x) - a)
            c += abs(corr(x) + b - a)
        return d / len(test), c / len(test)

    ns = [4, 8, 16, 32, 64, 128]
    rows = [maes(m) for m in ns]

    def slope(vals):
        lx, ly = [math.log(m) for m in ns], [math.log(v) for v in vals]
        mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
        return -sum((a - mx) * (b - my) for a, b in zip(lx, ly)) / sum((a - mx) ** 2 for a in lx)

    direct, corr = fit(int(n))
    xs = [lo + (hi - lo) * i / 150 for i in range(151)]
    at = maes(int(n))
    return {"ns": ns, "direct": [r[0] for r in rows], "delta": [r[1] for r in rows],
            "a_direct": slope([r[0] for r in rows]), "a_delta": slope([r[1] for r in rows]),
            "at": {"n": int(n), "direct": at[0], "delta": at[1]},
            "x": xs, "true": [_target(x, cheap)[0] for x in xs], "cheap": [_target(x, cheap)[1] for x in xs],
            "fit_direct": [direct(x) for x in xs], "fit_delta": [corr(x) + _target(x, cheap)[1] for x in xs],
            "train": {"x": pool[:int(n)], "E": [_target(x, cheap)[0] for x in pool[:int(n)]]}}


def _normal(seed, n):
    u = _lcg(seed, 2 * n)
    return [math.sqrt(-2 * math.log(max(u[2 * i], 1e-12))) * math.cos(2 * math.pi * u[2 * i + 1]) for i in range(n)]


def mae(n=20, mae_a=10.0, mae_b=11.0):
    """The MAE of two models measured on test sets of 5…200 molecules (errors normal, fixed draws), with ±δ(MAE)."""
    if not (3 <= n <= 1000 and 0.1 <= mae_a <= 100 and 0.1 <= mae_b <= 100):
        raise ValueError("n 3..1000, MAE 0.1..100")
    k = math.sqrt(math.pi / 2)  # σ of the errors for a given MAE
    ns = [5, 10, 20, 40, 80, 160, 320]

    def run(true_mae, seed, m):
        errs = [abs(z) * true_mae * k for z in _normal(seed, m)]
        mean = sum(errs) / m
        sd = math.sqrt(sum((e - mean) ** 2 for e in errs) / max(1, m - 1))
        return mean, sd / math.sqrt(m)

    out = {}
    for key, value, seed in (("a", mae_a, 99), ("b", mae_b, 189)):  # draws close to their means
        rows = [run(value, seed, m) for m in ns]
        out[key] = {"mean": [r[0] for r in rows], "lo": [r[0] - r[1] for r in rows], "hi": [r[0] + r[1] for r in rows]}
        m, d = run(value, seed, int(n))
        out[key]["at"] = {"mae": m, "err": d}
    out["ns"] = ns
    out["rel"] = math.sqrt(math.pi / 2 - 1) / math.sqrt(n)
    out["n"] = int(n)
    return out


def _lower_hull(points):
    pts = sorted(points)
    hull = []
    for p in pts:
        while len(hull) >= 2 and ((hull[-1][0] - hull[-2][0]) * (p[1] - hull[-2][1])
                                  - (hull[-1][1] - hull[-2][1]) * (p[0] - hull[-2][0])) <= 0:
            hull.pop()
        hull.append(p)
    return hull


def hull(e13=-0.40, e12=-0.50, x=0.4, e=-0.41):
    """The lower convex hull of A, AB2 (x = 1/3), AB (x = 1/2) and B, the hull at x, the height of a compound (x, e)."""
    if not (-2 <= e13 <= 0.5 and -2 <= e12 <= 0.5 and 0.02 <= x <= 0.98 and -2 <= e <= 0.5):
        raise ValueError("energies −2..0.5 eV/atom, x 0.02..0.98")
    phases = [(0.0, 0.0), (1 / 3, e13), (0.5, e12), (1.0, 0.0)]
    h = _lower_hull(phases)
    at = None
    for (x1, y1), (x2, y2) in zip(h, h[1:]):
        if x1 <= x <= x2:
            at = y1 + (y2 - y1) * (x - x1) / (x2 - x1)
            break
    above = e - at
    new = _lower_hull(phases + [(x, e)])
    return {"phases": [{"x": a, "E": b, "on": (a, b) in h} for a, b in phases], "hull": {"x": [p[0] for p in h],
            "E": [p[1] for p in h]}, "new_hull": {"x": [p[0] for p in new], "E": [p[1] for p in new]},
            "at_hull": at, "above": above, "x": x, "e": e}

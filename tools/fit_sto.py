"""Fit Slater-type radial functions with K Gaussians; writes modules/spectrum/analysis/sto_fits.py.

§1 THEORY
    The normalized Slater radial function of zeta = 1, R_n(r) = 2^(n+1/2) / sqrt((2n)!) r^(n-1) e^(-r), is approximated
    by g(r) = sum_k d_k N_k r^l exp(-alpha_k r^2), N_k the radial normalization of a Gaussian
    (N_k^2 = 2 (2 alpha_k)^(l+3/2) / Gamma(l + 3/2)). For fixed exponents the best coefficients (largest overlap
    <R|g> at ||g|| = 1) are d = G^-1 b with G_kj = (2 sqrt(alpha_k alpha_j) / (alpha_k + alpha_j))^(l+3/2),
    b_k = <R_n|N_k r^l e^(-alpha_k r^2)>, and <R|g>^2 = b^T G^-1 b; the exponents are optimized for the largest
    overlap (the least-squares STO-nG fit of Hehre, Stewart, Pople, J. Chem. Phys. 51, 2657 (1969)). Another zeta:
    exponents alpha_k zeta^2, the same d.
§2 ALGORITHM
    b_k by the trapezoidal rule in t = ln r on [-14, 4.5] with 6001 points (the integrand is smooth and vanishes at
    both ends, so the rule converges exponentially; checked against scipy.integrate.quad to 1e-12 relative);
    exponents: Nelder-Mead then Powell on ln alpha from five even-tempered starts, neighbours at least a factor
    1.15 apart (keeps G well conditioned); the best start is kept.
§3 USE
    python3 tools/fit_sto.py [K=6] (needs scipy; the program itself does not). About a minute per function.
§4 OUTPUT
    modules/spectrum/analysis/sto_fits.py: FITS {(n, l): (exponents, coefficients)} for n = 1..6, l = 0..min(2, n - 1);
    ERRORS {(n, l): 1 - <R|g>}.
"""

import sys
from math import factorial, gamma, sqrt
from pathlib import Path

import numpy as np
from scipy.optimize import minimize

T = np.linspace(-14, 4.5, 6001)
R = np.exp(T)
STEP = T[1] - T[0]


def gaussian_norm(a, l):
    return np.sqrt(2 * (2 * a) ** (l + 1.5) / gamma(l + 1.5))


def projections(a, n, l):
    norm = 2 ** (n + 0.5) / sqrt(factorial(2 * n))
    f = R ** (n + l + 2) * np.exp(-R)[None, :] * np.exp(-np.outer(a, R * R))  # r^(n-1) r^l r^2, dr = r dt
    return norm * gaussian_norm(a, l) * f.sum(axis=1) * STEP


def metric(a, l):
    return (2 * np.sqrt(np.outer(a, a)) / np.add.outer(a, a)) ** (l + 1.5)


def miss(x, n, l):
    x = np.sort(x)
    if not np.all(np.isfinite(x)) or np.min(np.diff(x)) < np.log(1.15) or x[0] < -20 or x[-1] > 20:
        return 1.0
    a = np.exp(x)
    try:
        w, v = np.linalg.eigh(metric(a, l))
    except np.linalg.LinAlgError:
        return 1.0
    keep = w > 1e-11 * w.max()
    p = v[:, keep].T @ projections(a, n, l)
    return 1 - sqrt(max(float(np.sum(p * p / w[keep])), 0.0))


def fit(n, l, k):
    best = None
    for low, ratio in ((0.02, 3.0), (0.04, 2.6), (0.01, 3.4), (0.06, 2.3), (0.03, 2.8)):
        x0 = np.log(low * ratio ** np.arange(k) / n**1.5)
        r = minimize(miss, x0, args=(n, l), method='Nelder-Mead',
                     options=dict(maxiter=40000, maxfev=40000, xatol=1e-8, fatol=1e-15))
        r = minimize(miss, r.x, args=(n, l), method='Powell', options=dict(xtol=1e-9, ftol=1e-15))
        if best is None or r.fun < best.fun:
            best = r
    a = np.exp(np.sort(best.x))
    g = metric(a, l)
    d = np.linalg.solve(g, projections(a, n, l))
    d /= sqrt(d @ g @ d)
    return a, d, 1 - float(d @ projections(a, n, l))


def main(k=6):
    pairs = [(n, l) for n in range(1, 7) for l in range(0, min(2, n - 1) + 1)]
    lines = [
        f'"""Slater-type radial functions (zeta = 1) as {k} normalized Gaussians each — written by tools/fit_sto.py (0.91.6).',
        '',
        '§4 SPECIFICATION',
        '    FITS {(n, l): (exponents, coefficients)}: R_n(r) ~ sum_k d_k N_k r^l exp(-alpha_k r^2), primitives normalized;',
        '    for the exponent zeta multiply the exponents by zeta^2. ERRORS {(n, l): 1 - overlap with the Slater function}.',
        '"""',
        '',
        'FITS = {',
    ]
    errors = {}
    for n, l in pairs:
        a, d, e = fit(n, l, k)
        errors[(n, l)] = e
        print(n, l, f'{e:.2e}', flush=True)
        lines.append(f'    ({n}, {l}): (')
        lines.append('        (' + ', '.join(f'{x:.12e}' for x in a) + '),')
        lines.append('        (' + ', '.join(f'{x:.12e}' for x in d) + '),')
        lines.append('    ),')
    lines.append('}')
    lines.append('ERRORS = {' + ', '.join(f'({n}, {l}): {e:.2e}' for (n, l), e in errors.items()) + '}')
    target = Path(__file__).resolve().parent.parent / 'modules' / 'spectrum' / 'analysis' / 'sto_fits.py'
    target.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print(target)


if __name__ == '__main__':
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 6)

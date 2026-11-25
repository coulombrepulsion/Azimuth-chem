"""Vectorised (numpy) counterparts of core.jsmath and order-preserving reductions.

HEADER
    Accelerators for the GTO engine (core.gto, core.qtaim) that keep the
    results bitwise identical to the scalar code: elementwise IEEE
    operations (+ - * / sqrt) give the same doubles whether executed by
    CPython or by numpy ufuncs, so a vectorised loop body is exact as long
    as every transcendental function is the same algorithm and every sum
    is accumulated in the same order.  Wilkinson convention, sections 1-8.

§1 THEORY
    exp: fdlibm __ieee754_exp (V8 Math.exp) evaluated on arrays: argument
    reduction x = k ln2 + r with the split constant ln2 = LN2HI + LN2LO,
    the rational approximation in r, scaling by 2^k (ldexp is exact for
    normal results).  Sequential sum: sum_i x_i accumulated left to right,
    starting from +0, equals cumsum([0, x...])[-1] (numpy's cumsum is a
    sequential recurrence; np.sum may use pairwise summation and is
    therefore not used where bitwise agreement is required).

§2 ALGORITHM
    exp_np: the branches of jsmath.exp as masks; integer k by truncation
    of INVLN2 x + 1/2 sign(x), as the C cast does.

§3 APPLICATIONS
    core.gto (Boys function, basis-function values), core.qtaim (grids).

§4 SPECIFICATION
    exp_np(x: ndarray) -> ndarray, elementwise equal (bitwise) to
      [jsmath.exp(v) for v in x] for every finite or infinite input.
    seq_sum(x: 1-d ndarray) -> float, bitwise equal to the loop
      s = 0; for v in x: s += v.
    Tier: bitwise.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The fdlibm comparisons of the high word are expressed through the
    thresholds _T_* of core.jsmath (see there).
§7 TEST CASES (tests/test_gto.py::test_exp_np)
    300 000 random arguments in [-746, 710] including the branch
    boundaries, +-0, +-inf: equal bit for bit to jsmath.exp.
§8 ERROR ANALYSIS
    Same as fdlibm exp (< 1 ulp); the point is equality with V8, not
    accuracy.
"""
from __future__ import annotations

import numpy as np

from . import jsmath as _j


def _ldexp(y, k):
    """np.ldexp with the exponent as a C int. Where the C long has 32 bits (a browser: Pyodide, WebAssembly) numpy
    refuses a 64-bit exponent («ufunc 'ldexp' not supported for the input types»). Beyond ±3000 the answer is the
    same 0 or infinity, so the exponent is clipped before it is narrowed."""
    return np.ldexp(y, np.clip(k, -3000, 3000).astype(np.intc))


def exp_np(x):
    x = np.asarray(x, dtype=float)
    ax = np.abs(x)
    if not (ax < _j._T_BIG).all():  # NaN, infinities, over/underflow: the general path
        return _exp_np_general(x)
    # fast path: every element goes through the reduction branch of fdlibm exp
    xsb = np.signbit(x)
    k2 = np.trunc(_j._INVLN2 * x + np.where(xsb, _j._HALF[1], _j._HALF[0]))
    hi = x - k2 * _j._LN2HI[0]
    lo = k2 * _j._LN2LO[0]
    k = k2.astype(np.int64)
    m1 = (ax >= _j._T_HALF) & (ax < _j._T_ONEHALF)
    if m1.any():
        s1 = xsb[m1]
        hi[m1] = x[m1] - np.where(s1, _j._LN2HI[1], _j._LN2HI[0])
        lo[m1] = np.where(s1, _j._LN2LO[1], _j._LN2LO[0])
        k[m1] = 1 - 2 * s1.astype(np.int64)
    red = ax >= _j._T_HALF
    xx = np.where(red, hi - lo, x)
    k = np.where(red, k, 0)
    t = xx * xx
    c = xx - t * (_j._P1 + t * (_j._P2 + t * (_j._P3 + t * (_j._P4 + t * _j._P5))))
    y = 1.0 - ((lo - (xx * c) / (2.0 - c)) - hi)
    small = k < -1021
    with np.errstate(over="ignore", under="ignore"):
        res = _ldexp(y, k)
        if small.any():
            res[small] = _ldexp(y[small], k[small] + 1000) * _j._TWOM1000
    z = k == 0
    if z.any():
        xz, cz = xx[z], c[z]
        res[z] = 1.0 - ((xz * cz) / (cz - 2.0) - xz)
    tiny = ax < _j._T_TINY
    if tiny.any():
        res[tiny] = 1.0 + x[tiny]
    return res


def _exp_np_general(x):
    out = np.empty_like(x)
    ax = np.abs(x)
    nan = x != x
    big = (ax >= _j._T_BIG) & ~nan
    out[nan] = x[nan] + x[nan]
    xb = x[big]
    vb = np.where(xb > _j._O_THR, np.inf, np.where(xb < _j._U_THR, 0.0, np.nan))
    vb = np.where(np.isinf(xb), np.where(xb > 0, xb, 0.0), vb)
    out[big] = vb
    # values of the big branch that are neither over- nor underflow fall through
    rest = ~nan & (~big | np.isnan(out))
    xr = x[rest]
    axr = ax[rest]
    xsb = (np.signbit(xr)).astype(np.int64)
    k = np.zeros(xr.shape, dtype=np.int64)
    hi = np.zeros(xr.shape)
    lo = np.zeros(xr.shape)
    red = axr >= _j._T_HALF
    tiny = (~red) & (axr < _j._T_TINY)
    m1 = red & (axr < _j._T_ONEHALF)
    m2 = red & ~m1
    ln2hi = np.where(xsb == 1, _j._LN2HI[1], _j._LN2HI[0])
    ln2lo = np.where(xsb == 1, _j._LN2LO[1], _j._LN2LO[0])
    hi = np.where(m1, xr - ln2hi, hi)
    lo = np.where(m1, ln2lo, lo)
    k = np.where(m1, 1 - xsb - xsb, k)
    half = np.where(xsb == 1, _j._HALF[1], _j._HALF[0])
    k2 = np.trunc(_j._INVLN2 * xr + half)
    t2 = k2
    hi = np.where(m2, xr - t2 * _j._LN2HI[0], hi)
    lo = np.where(m2, t2 * _j._LN2LO[0], lo)
    k = np.where(m2, k2.astype(np.int64), k)
    xx = np.where(red, hi - lo, xr)
    t = xx * xx
    c = xx - t * (_j._P1 + t * (_j._P2 + t * (_j._P3 + t * (_j._P4 + t * _j._P5))))
    r0 = 1.0 - ((xx * c) / (c - 2.0) - xx)
    y = 1.0 - ((lo - (xx * c) / (2.0 - c)) - hi)
    with np.errstate(over="ignore", under="ignore"):
        rk = np.where(k >= -1021, _ldexp(y, k), _ldexp(y, k + 1000) * _j._TWOM1000)
    res = np.where(k == 0, r0, rk)
    res = np.where(tiny, 1.0 + xr, res)
    out[rest] = res
    return out


def seq_sum(x) -> float:
    x = np.asarray(x, dtype=float).ravel()
    if x.size == 0:
        return 0.0
    return float(np.cumsum(np.concatenate(([0.0], x)))[-1])


def hypot3_np(x, y, z):
    """jsmath.hypot3 (V8 Math.hypot of three finite numbers) elementwise; bitwise."""
    a, b, c = np.abs(x), np.abs(y), np.abs(z)
    M = np.where(a > b, a, b)
    M = np.where(c > M, c, M)
    zero = M == 0
    Ms = np.where(zero, 1.0, M)
    n = a / Ms
    s = n * n
    n = b / Ms
    summand = n * n
    prelim = s + summand
    comp = (prelim - s) - summand
    n = c / Ms
    s = prelim + (n * n - comp)
    return np.where(zero, 0.0, np.sqrt(s) * Ms)

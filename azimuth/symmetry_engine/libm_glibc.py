"""sin and cos exactly as V8 (Chromium 141) computes Math.sin / Math.cos.

Port of glibc_sin / glibc_cos from V8's third_party/glibc (IBM Accurate
Mathematical Library, glibc sysdeps/ieee754/dbl-64/s_sin.c, revision
4e21c2075193e406a92c0d1cb091a7c804fda4d9), which V8 14.1 uses for Math.sin and
Math.cos (V8_USE_LIBM_TRIG_FUNCTIONS).

Copyright (C) 2001-2022 Free Software Foundation, Inc.  This file is a
derivative work and is licensed under the GNU Lesser General Public License
2.1 or later; see LICENSE-glibc.txt in this directory.  The rest of the
project is not affected by this licence (the module is a separate,
replaceable component).

HEADER
    Wilkinson convention, §1-§8.

§1 THEORY
    sin and cos of x are computed from a table of sin x_k, cos x_k at
    x_k = k/128 (each stored as a double plus a correction term) and short
    Taylor polynomials for the remainder d = x - x_k (|d| <= 1/256):
        sin(x_k + d) = sin x_k cos d + cos x_k sin d,
        cos(x_k + d) = cos x_k cos d - sin x_k sin d.
    Arguments beyond 0.855 are reduced modulo pi/2 with pi/2 split into
    three parts (mp1 + mp2 + pp3 + pp4, 136 bits), giving the quadrant n and
    a double-double remainder a + da.  The library's error is <= 0.548 ulp.
    Reproducing it operation by operation gives the same bits as V8 on every
    platform (the platform libm -- glibc of another version, macOS, MSVC --
    differs in the last bit for ~0.1 % of arguments, measured).

§2 ALGORITHM
    As in the C source (functions of the same names): TAYLOR_SIN for
    |x| < 0.126, table + correction otherwise; range splits at 2^-26,
    0.855469, 2.426265 and 105414350.

§3 APPLICATIONS
    Every model that uses sin/cos (wavefunctions in a box, time phases,
    rotation matrices, angular functions).

§4 SPECIFICATION
    sin(x), cos(x): float -> float, bitwise equal to V8 Math.sin/Math.cos
    for |x| < 105414350.  Larger arguments need glibc's __branred (Payne-
    Hanek reduction, not ported): the platform math.sin/cos is used there
    (no Atlas model reaches it; documented in §6).

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    * u.i[LOW_HALF] of big + |x| (big = 1.5 * 2^45, so the sum rounds |x|
      to a multiple of 2^-7) is the table index; in Python it is the low
      32 bits of the IEEE representation.
    * The C code is compiled without FMA contraction on x86-64 (no FMA in the
      baseline instruction set), which is also Python's behaviour.
§7 TEST CASES (tests/test_jsmath.py)
    47 784 arguments (uniform in [-10, 10], [-1e5, 1e5], [-1, 1] and the
    grid n pi x of the particle-in-a-box page) against Chromium 141:
    0 mismatches (system glibc 2.39: 60 mismatches); a 2 000-point subset
    is kept as a regression fixture.
§8 ERROR ANALYSIS
    The library's documented accuracy: < 0.55 ulp; the port adds no error
    (identical operations).
"""
from __future__ import annotations

import math
import struct

from ._sincostab import SINCOSTAB as _T

_D = struct.Struct("<d")
_Q = struct.Struct("<Q")


def _f(h: str) -> float:
    return float.fromhex(h)


# constants of usncs.h and s_sin.c (hexadecimal, as in the source)
s1, s2, s3, s4, s5 = _f("-0x1.5555555555555p-3"), _f("0x1.1111111110ECEp-7"), _f("-0x1.A01A019DB08B8p-13"), \
    _f("0x1.71DE27B9A7ED9p-19"), _f("-0x1.ADDFFC2FCDF59p-26")
big = _f("0x1.8000000000000p45")
hp0, hp1 = _f("0x1.921FB54442D18p0"), _f("0x1.1A62633145C07p-54")
mp1, mp2 = _f("0x1.921FB58000000p0"), _f("-0x1.DDE973C000000p-27")
pp3, pp4 = _f("-0x1.CB3B398000000p-55"), _f("-0x1.d747f23e32ed7p-83")
hpinv, toint = _f("0x1.45F306DC9C883p-1"), _f("0x1.8000000000000p52")
sn3, sn5 = -1.66666666666664880952546298448555E-01, 8.33333214285722277379541354343671E-03
cs2, cs4, cs6 = 4.99999999999999999999950396842453E-01, -4.16666666666664434524222570944589E-02, \
    1.38888874007937613028114285595617E-03


def _low(x: float) -> int:
    return _Q.unpack(_D.pack(x))[0] & 0xFFFFFFFF


def _hiabs(x: float) -> int:
    return (_Q.unpack(_D.pack(x))[0] >> 32) & 0x7FFFFFFF


def _taylor_sin(xx, x, dx):
    poly = ((((s5 * xx + s4) * xx + s3) * xx + s2) * xx) + s1
    t = ((poly * x - 0.5 * dx) * xx + dx)
    return x + t


def _do_cos(x, dx):
    if x < 0:
        dx = -dx
    u = big + abs(x)
    x = abs(x) - (u - big) + dx
    xx = x * x
    s = x + x * xx * (sn3 + xx * sn5)
    c = xx * (cs2 + xx * (cs4 + xx * cs6))
    k = _low(u) << 2
    sn, ssn, cs, ccs = _T[k], _T[k + 1], _T[k + 2], _T[k + 3]
    cor = (ccs - s * ssn - cs * c) - sn * s
    return cs + cor


def _do_sin(x, dx):
    xold = x
    if abs(x) < 0.126:
        return _taylor_sin(x * x, x, dx)
    if x <= 0:
        dx = -dx
    u = big + abs(x)
    x = abs(x) - (u - big)
    xx = x * x
    s = x + (dx + x * xx * (sn3 + xx * sn5))
    c = x * dx + xx * (cs2 + xx * (cs4 + xx * cs6))
    k = _low(u) << 2
    sn, ssn, cs, ccs = _T[k], _T[k + 1], _T[k + 2], _T[k + 3]
    cor = (ssn + s * ccs - sn * c) + cs * s
    return math.copysign(sn + cor, xold)


def _reduce_sincos(x):
    t = (x * hpinv + toint)
    xn = t - toint
    y = (x - xn * mp1) - xn * mp2
    n = _low(t) & 3
    t1 = xn * pp3
    t2 = y - t1
    db = (y - t2) - t1
    t1 = xn * pp4
    b = t2 - t1
    db += (t2 - b) - t1
    return n, b, db


def _do_sincos(a, da, n):
    retval = _do_cos(a, da) if n & 1 else _do_sin(a, da)
    return -retval if n & 2 else retval


def sin(x: float) -> float:
    """Math.sin of V8 (glibc_sin), bit for bit for |x| < 105414350."""
    k = _hiabs(x)
    if k < 0x3E500000:  # |x| < 2^-26: sin x = x
        return x
    if k < 0x3FEB6000:  # |x| < 0.855469
        return _do_sin(x, 0.0)
    if k < 0x400368FD:  # |x| < 2.426265: sin x = cos(pi/2 - |x|) with the sign of x
        t = hp0 - abs(x)
        return math.copysign(_do_cos(t, hp1), x)
    if k < 0x419921FB:  # |x| < 105414350
        n, a, da = _reduce_sincos(x)
        return _do_sincos(a, da, n)
    if k < 0x7FF00000:
        return math.sin(x)  # Payne-Hanek range (not ported, see §4)
    return x / x if x == x else x


def cos(x: float) -> float:
    """Math.cos of V8 (glibc_cos), bit for bit for |x| < 105414350."""
    k = _hiabs(x)
    if k < 0x3E400000:  # |x| < 2^-27
        return 1.0
    if k < 0x3FEB6000:
        return _do_cos(x, 0.0)
    if k < 0x400368FD:
        y = hp0 - abs(x)
        a = y + hp1
        da = (y - a) + hp1
        return _do_sin(a, da)
    if k < 0x419921FB:
        n, a, da = _reduce_sincos(x)
        return _do_sincos(a, da, n + 1)
    if k < 0x7FF00000:
        return math.cos(x)
    return math.nan

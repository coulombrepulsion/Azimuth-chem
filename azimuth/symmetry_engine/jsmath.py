"""JavaScript Math semantics needed for faithful ports of the Atlas v1.0 code.

HEADER
    Small helpers reproducing ECMAScript ``Math`` functions whose Python
    counterparts round differently. Wilkinson convention, sections 1-8.

§1 THEORY
    ``Math.hypot(a, b, ...)`` in V8 (src/builtins/math.tq, ``MathHypot``)
    scales every argument by M = max |x_i| and sums (x_i / M)^2 with Kahan
    compensation, returning sqrt(sum) * M. CPython's ``math.hypot`` (>= 3.10)
    uses a different, more accurate algorithm, so the two may differ in the
    last bit. Reproducing the V8 algorithm makes ported code bitwise
    comparable to the original wherever only +,-,*,/,sqrt are involved.

    ``Math.round(x)`` rounds half up (towards +inf): floor(x + 0.5) for the
    representable cases used here; Python's ``round`` rounds half to even.

    ``Math.sign`` returns -1, +1, +-0 or NaN.

    ``Math.exp`` and ``Math.log`` in V8 are the fdlibm algorithms
    (src/base/ieee754.cc, from FreeBSD msun e_exp.c / e_log.c): argument
    reduction by k ln 2 with ln 2 split into a high part with 32 trailing
    zero bits and a low part, a minimax polynomial on [-ln2/2, ln2/2] (exp)
    or in s = f/(2 + f) (log), and exponent reconstruction by integer
    arithmetic on the high word. Ported line by line, they reproduce V8
    bit for bit -- and, being pure Python, they give the same bits on
    every operating system (CPython's math.exp/log call the platform libm,
    which differs between glibc, macOS and the MSVC runtime).
    ``Math.sin``/``Math.cos`` in V8 14.1 are glibc's IBM Accurate
    Mathematical Library bundled in V8; they are re-exported here from
    core.libm_glibc (an LGPL-2.1 module).
    ``Math.acos``, ``atan``, ``atan2``, ``log10``, ``log1p``, ``asinh``,
    ``cbrt`` and ``tan`` in V8 14.1 are fdlibm (FreeBSD msun: e_acos.c,
    s_atan.c, e_atan2.c, e_log10.c, s_log1p.c, s_asinh.c, s_cbrt.c, s_tan.c
    with k_tan.c and e_rem_pio2.c) and are ported line by line as well.
    ``String.prototype.localeCompare`` (ICU root collation, Chromium locale
    en-US) is reproduced for the label alphabet of the pages (punctuation,
    digits with their super/subscript variants, Latin, Greek): primary
    weights in ICU order, then tertiary differences (digit variants,
    lower < upper case), measured in Chromium 141.
    ``Math.pow`` in V8 returns x*x for y = 2, sqrt(x) for y = 0.5 and
    otherwise the platform pow (glibc on Linux); ``js_pow`` does the same.

§2 ALGORITHM
    exp, log: fdlibm, see the code (constants are the fdlibm ones, written
    with their hexadecimal high/low words in comments of the original).
    js_hypot: if any |x| is inf -> inf; if any is NaN -> NaN; M = max |x|;
    if M == 0 -> 0; Kahan-sum (x_i/M)^2; return sqrt(sum) * M.
    js_round: r = floor(x); r += 1 if x - r >= 0.5 (exact, since x - r is
    computed without rounding for |x| < 2^52); -0 for x in [-0.5, -0];
    values with |x| >= 2^52 are already integers and are returned unchanged.

§3 APPLICATIONS
    Normalising 2-vectors (CI coefficients in core.h2), rounding of
    percentages that the pages print.

§4 SPECIFICATION
    js_hypot(*xs: float) -> float, the V8 result bit for bit.
    js_round(x: float) -> float (integral value), ECMAScript Math.round.
    js_sign(x: float) -> float.
    exp(x), log(x) -> float, Math.exp / Math.log of V8, every float input.
    acos(x), atan(x), atan2(y, x), log10, log1p, asinh, cbrt -> float, as V8.
    tan(x): as V8 for |x| <= 2^19 pi/2 (platform tan beyond: the Payne-Hanek
    branch of rem_pio2 is not ported; no page reaches it).
    js_pow(x, y) -> float, Math.pow of V8 on Linux (platform pow elsewhere).
    Reference: V8 in Chromium 141.0.7390.37 (Playwright 1.56 build) --
    tier ``bitwise`` for exp, log, hypot, round, sign; ``bitwise`` on Linux
    and ``ulp(1)`` elsewhere for js_pow.

§5 PROCEDURES -- below.
§6 IMPLEMENTATION NOTES
    The Kahan step is written exactly as in V8 so that compensation terms
    round identically.
§7 TEST CASES (tests/test_jsmath.py) js_hypot(3, 4) == 5; js_hypot(0, 0) == 0; js_round(2.5) == 3, js_round(-2.5) == -2;
    agreement with values recorded from Chromium. Verified 2026-10-19 against Chromium 141 on random samples: exp 62 000
    arguments in [-745, 709] (0 mismatches; math.exp under glibc: 5 788), log 52 000 arguments in [1e-6, 1e304] (0
    mismatches; math.log: 2 553), pow 51 000 pairs + 72 000 pairs at 18 special exponents (0 mismatches for js_pow;
    plain math.pow: 3 at y = 0.5 and 4 at y = 2); acos 50 009 arguments in [-1, 1] incl. 10 000 within 1e-17..1 of +-1
    (0 mismatches; math.acos: 3 169), atan 40 000 (0; math.atan: 2 189), atan2 35 200 pairs incl. signed zeros and
    infinities (0; math.atan2: 5 736); log10 30 007 (0; math.log10: 695), log1p 30 004 (0; 17), asinh 30 000 (0; 728),
    cbrt 30 004 (0; math.cbrt: 14 968), tan 32 004 incl. |x| <= 1e5 (0; 1 006). The fixture
    tests/fixtures/js_reference/jsmath.json keeps 2 000 of these as a regression check on every platform.
§8 ERROR ANALYSIS
    fdlibm acos/atan/atan2: < 1 ulp (Sun).
    fdlibm exp and log: < 1 ulp (Sun's error bounds: exp 0.75 ulp-ish,
    log < 1 ulp); they are not always correctly rounded -- which is
    exactly why the port, not the platform libm, is needed for bitwise
    agreement.
    js_hypot has relative error <= ~2u (scaling exact up to rounding of the
    quotient, compensated sum, one sqrt, one multiply); it is not used for
    error-critical quantities -- its purpose is bitwise agreement.
"""
from __future__ import annotations

import math
import struct

from .libm_glibc import cos, sin  # noqa: F401  (V8's Math.sin/Math.cos; LGPL module)

_D = struct.Struct("<d")
_Q = struct.Struct("<Q")


def _bits(x: float) -> int:
    return _Q.unpack(_D.pack(x))[0]


def _from(b: int) -> float:
    return _D.unpack(_Q.pack(b & 0xFFFFFFFFFFFFFFFF))[0]


def _hi(x: float) -> int:
    """High 32-bit word as a signed int (fdlibm __HI)."""
    v = _bits(x) >> 32
    return v - (1 << 32) if v & 0x80000000 else v


def _with_hi(x: float, hi: int) -> float:
    return _from(((hi & 0xFFFFFFFF) << 32) | (_bits(x) & 0xFFFFFFFF))


# ---------------------------------------------------------------- exp (fdlibm)
_HALF = (0.5, -0.5)
_LN2HI = (6.93147180369123816490e-01, -6.93147180369123816490e-01)
_LN2LO = (1.90821492927058770002e-10, -1.90821492927058770002e-10)
_INVLN2 = 1.44269504088896338700e+00
_P1, _P2, _P3, _P4, _P5 = (1.66666666666666019037e-01, -2.77777777770155933842e-03, 6.61375632143793436117e-05,
                           -1.65339022054652515390e-06, 4.13813679705723846039e-08)
_O_THR, _U_THR = 7.09782712893383973096e+02, -7.45133219101941108420e+02
_TWOM1000 = 9.33263618503218878990e-302


# fdlibm compares the high word of |x| with constants; for non-negative
# doubles that is the same as comparing |x| with the double whose high word is
# the constant (low word 0) -- or the next one for a strict ">".
_T_BIG = _from(0x40862E42 << 32)        # hx >= 0x40862E42   <=> |x| >= _T_BIG
_T_HALF = _from(0x3FD62E43 << 32)       # hx >  0x3FD62E42   <=> |x| >= _T_HALF
_T_ONEHALF = _from(0x3FF0A2B2 << 32)    # hx <  0x3FF0A2B2   <=> |x| <  _T_ONEHALF
_T_TINY = _from(0x3E300000 << 32)       # hx <  0x3E300000   <=> |x| <  2^-28
_ldexp = math.ldexp


def exp(x: float) -> float:
    """Math.exp of V8 (fdlibm __ieee754_exp), bit for bit.

    Adding k to the exponent field of y (fdlibm) equals ldexp(y, k) exactly
    whenever the result is normal, which fdlibm guarantees in that branch.
    """
    ax = -x if x < 0 else x
    if ax >= _T_BIG or x != x:
        if x != x:
            return x + x
        if ax == math.inf:
            return x if x > 0 else 0.0
        if x > _O_THR:
            return math.inf
        if x < _U_THR:
            return 0.0
    xsb = 1 if (x < 0 or (x == 0 and math.copysign(1.0, x) < 0)) else 0
    k = 0
    hi = lo = 0.0
    if ax >= _T_HALF:  # |x| > ln2/2: reduce x = k ln2 + r
        if ax < _T_ONEHALF:
            hi = x - _LN2HI[xsb]
            lo = _LN2LO[xsb]
            k = 1 - xsb - xsb
        else:
            k = int(_INVLN2 * x + _HALF[xsb])
            t = float(k)
            hi = x - t * _LN2HI[0]
            lo = t * _LN2LO[0]
        x = hi - lo
    elif ax < _T_TINY:  # |x| < 2^-28
        return 1.0 + x
    t = x * x
    c = x - t * (_P1 + t * (_P2 + t * (_P3 + t * (_P4 + t * _P5))))
    if k == 0:
        return 1.0 - ((x * c) / (c - 2.0) - x)
    y = 1.0 - ((lo - (x * c) / (2.0 - c)) - hi)
    if k >= -1021:
        return _ldexp(y, k)
    return _ldexp(y, k + 1000) * _TWOM1000


# ---------------------------------------------------------------- log (fdlibm)
_LN2_HI, _LN2_LO, _TWO54 = 6.93147180369123816490e-01, 1.90821492927058770002e-10, 1.80143985094819840000e+16
_LG = (6.666666666666735130e-01, 3.999999999940941908e-01, 2.857142874366239149e-01, 2.222219843214978396e-01,
       1.818357216161805012e-01, 1.531383769920937332e-01, 1.479819860511658591e-01)


def log(x: float) -> float:
    """Math.log of V8 (fdlibm __ieee754_log), bit for bit."""
    b = _bits(x)
    hx = _hi(x)
    lx = b & 0xFFFFFFFF
    k = 0
    if hx < 0x00100000:  # x < 2^-1022 (or negative)
        if ((hx & 0x7FFFFFFF) | lx) == 0:
            return -math.inf
        if hx < 0:
            return math.nan
        k -= 54
        x *= _TWO54
        hx = _hi(x)
    if hx >= 0x7FF00000:
        return x + x
    k += (hx >> 20) - 1023
    hx &= 0x000FFFFF
    i = (hx + 0x95F64) & 0x100000
    x = _with_hi(x, hx | (i ^ 0x3FF00000))  # normalise x or x/2 into [sqrt2/2, sqrt2)
    k += i >> 20
    f = x - 1.0
    Lg1, Lg2, Lg3, Lg4, Lg5, Lg6, Lg7 = _LG
    if (0x000FFFFF & (2 + hx)) < 3:  # |f| < 2^-20
        if f == 0.0:
            if k == 0:
                return 0.0
            dk = float(k)
            return dk * _LN2_HI + dk * _LN2_LO
        R = f * f * (0.5 - 0.33333333333333333 * f)
        if k == 0:
            return f - R
        dk = float(k)
        return dk * _LN2_HI - ((R - dk * _LN2_LO) - f)
    s = f / (2.0 + f)
    dk = float(k)
    z = s * s
    i = hx - 0x6147A
    w = z * z
    j = 0x6B851 - hx
    t1 = w * (Lg2 + w * (Lg4 + w * Lg6))
    t2 = z * (Lg1 + w * (Lg3 + w * (Lg5 + w * Lg7)))
    i |= j
    R = t2 + t1
    if i > 0:
        hfsq = 0.5 * f * f
        if k == 0:
            return f - (hfsq - s * (hfsq + R))
        return dk * _LN2_HI - ((hfsq - (s * (hfsq + R) + dk * _LN2_LO)) - f)
    if k == 0:
        return f - s * (f - R)
    return dk * _LN2_HI - ((s * (f - R) - dk * _LN2_LO) - f)


def js_pow(x: float, y: float) -> float:
    """Math.pow of V8: x*x for y = 2, sqrt for y = 0.5 (x >= 0), else the platform pow.

    Established empirically against Chromium 141 (18 exponents x 4000 bases):
    V8 equals glibc pow except at y = 2 and y = 0.5, where glibc pow is not
    always correctly rounded and V8 uses the exact operation.
    """
    if y == 2:
        return x * x
    if y == 0.5 and x >= 0 and not math.isinf(x):
        return math.sqrt(x)
    try:
        return math.pow(x, y)
    except (OverflowError, ValueError):
        if x < 0 and y != int(y):
            return math.nan
        return math.inf if abs(x) > 1 and y > 0 or abs(x) < 1 and y < 0 else 0.0


def sq(x: float) -> float:
    """JavaScript ``x**2`` (= x*x, see js_pow); Python's float ** 2 calls pow()."""
    return x * x


_INF = math.inf
_sqrt = math.sqrt


def hypot3(x: float, y: float, z: float) -> float:
    """js_hypot(x, y, z) unrolled (same operations, same order; hot path of the symmetry page)."""
    a, b, c = abs(x), abs(y), abs(z)
    if not (a < _INF and b < _INF and c < _INF):
        return _hypot_any((a, b, c))
    M = a if a > b else b
    if c > M:
        M = c
    if M == 0:
        return 0.0
    n = a / M
    s = n * n          # first Kahan step: comp = 0, s = n*n exactly as in the loop
    n = b / M
    summand = n * n
    prelim = s + summand
    comp = (prelim - s) - summand
    n = c / M
    s = prelim + (n * n - comp)
    return _sqrt(s) * M


def js_hypot(*xs: float) -> float:
    """ECMAScript Math.hypot as implemented in V8 (scaled Kahan sum)."""
    if len(xs) == 3:
        return hypot3(*xs)
    return _hypot_any(xs)


def _hypot_any(xs) -> float:
    absx = [abs(x) for x in xs]
    if any(math.isinf(x) for x in absx):
        return math.inf
    if any(math.isnan(x) for x in absx):
        return math.nan
    M = max(absx) if absx else 0.0
    if M == 0:
        return 0.0
    s = 0.0
    comp = 0.0
    for x in absx:
        n = x / M
        summand = n * n - comp
        prelim = s + summand
        comp = (prelim - s) - summand
        s = prelim
    return math.sqrt(s) * M


def js_round(x: float) -> float:
    """ECMAScript Math.round: nearest integer, halves towards +infinity."""
    if math.isnan(x) or math.isinf(x) or abs(x) >= 2.0 ** 52:
        return x
    # floor(x + 0.5) would misround 0.49999999999999994 (x + 0.5 rounds up);
    # compare the exact fractional part instead.
    r = float(math.floor(x))
    if x - r >= 0.5:
        r += 1.0
    if r == 0 and (x < 0 or math.copysign(1.0, x) < 0):
        return -0.0  # Math.round(-0.2) is -0
    return r


def js_sign(x: float) -> float:
    """ECMAScript Math.sign."""
    if math.isnan(x):
        return math.nan
    if x > 0:
        return 1.0
    if x < 0:
        return -1.0
    return x  # +0.0 or -0.0


# ------------------------------------------------- acos, atan, atan2 (fdlibm)
_PIO2_HI, _PIO2_LO = 1.57079632679489655800e+00, 6.12323399573676603587e-17
_PI = 3.14159265358979311600e+00
_PS = (1.66666666666666657415e-01, -3.25565818622400915405e-01, 2.01212532134862925881e-01,
       -4.00555345006794114027e-02, 7.91534994289814532176e-04, 3.47933107596021167570e-05)
_QS = (-2.40339491173441421878e+00, 2.02094576023350569471e+00, -6.88283971605453293030e-01,
       7.70381505559019352791e-02)


def _acos_rq(z: float) -> tuple[float, float]:
    pS0, pS1, pS2, pS3, pS4, pS5 = _PS
    qS1, qS2, qS3, qS4 = _QS
    p = z * (pS0 + z * (pS1 + z * (pS2 + z * (pS3 + z * (pS4 + z * pS5)))))
    q = 1.0 + z * (qS1 + z * (qS2 + z * (qS3 + z * qS4)))
    return p, q


def acos(x: float) -> float:
    """Math.acos of V8 (fdlibm __ieee754_acos), bit for bit."""
    hx = _hi(x)
    ix = hx & 0x7FFFFFFF
    if ix >= 0x3FF00000:
        if x == 1.0:
            return 0.0
        if x == -1.0:
            return _PI + 2.0 * _PIO2_LO
        return math.nan
    if ix < 0x3FE00000:
        if ix <= 0x3C600000:
            return _PIO2_HI + _PIO2_LO
        z = x * x
        p, q = _acos_rq(z)
        r = p / q
        return _PIO2_HI - (x - (_PIO2_LO - x * r))
    if hx < 0:
        z = (1.0 + x) * 0.5
        p, q = _acos_rq(z)
        s = math.sqrt(z)
        r = p / q
        w = r * s - _PIO2_LO
        return _PI - 2.0 * (s + w)
    z = (1.0 - x) * 0.5
    s = math.sqrt(z)
    df = _from(_bits(s) & 0xFFFFFFFF00000000)
    c = (z - df * df) / (s + df)
    p, q = _acos_rq(z)
    r = p / q
    w = r * s + c
    return 2.0 * (df + w)


_ATANHI = (4.63647609000806093515e-01, 7.85398163397448278999e-01, 9.82793723247329054082e-01,
           1.57079632679489655800e+00)
_ATANLO = (2.26987774529616870924e-17, 3.06161699786838301793e-17, 1.39033110312309984516e-17,
           6.12323399573676603587e-17)
_AT = (3.33333333333329318027e-01, -1.99999999998764832476e-01, 1.42857142725034663711e-01,
       -1.11111104054623557880e-01, 9.09088713343650656196e-02, -7.69187620504482999495e-02,
       6.66107313738753120669e-02, -5.83357013379057348645e-02, 4.97687799461593236017e-02,
       -3.65315727442169155270e-02, 1.62858201153657823623e-02)


# fdlibm compares the high word of |x| (low word ignored): ix < C  <=>  |x| < double(C:0),
# ix >= C <=> |x| >= double(C:0); the thresholds as doubles:
_A66, _A04375, _A2M27 = 2.0 ** 66, 0.4375, 2.0 ** -27
_A11875, _A06875, _A24375 = 1.1875, 0.6875, 2.4375


def atan(x: float) -> float:
    """Math.atan of V8 (fdlibm atan), bit for bit (word tests written as comparisons of |x|)."""
    ax = abs(x)
    if not ax < _A66:
        if x != x:
            return x + x
        return _ATANHI[3] + _ATANLO[3] if x > 0 else -_ATANHI[3] - _ATANLO[3]
    neg = x < 0
    if ax < _A04375:
        if ax < _A2M27:
            return x
        idx = -1
    else:
        x = ax
        if ax < _A11875:
            if ax < _A06875:
                idx = 0
                x = (2.0 * x - 1.0) / (2.0 + x)
            else:
                idx = 1
                x = (x - 1.0) / (x + 1.0)
        elif ax < _A24375:
            idx = 2
            x = (x - 1.5) / (1.0 + 1.5 * x)
        else:
            idx = 3
            x = -1.0 / x
    a = _AT
    z = x * x
    w = z * z
    s1 = z * (a[0] + w * (a[2] + w * (a[4] + w * (a[6] + w * (a[8] + w * a[10])))))
    s2 = w * (a[1] + w * (a[3] + w * (a[5] + w * (a[7] + w * a[9]))))
    if idx < 0:
        return x - x * (s1 + s2)
    z = _ATANHI[idx] - ((x * (s1 + s2) - _ATANLO[idx]) - x)
    return -z if neg else z


_PI_O_4, _PI_O_2, _PI_LO = 7.8539816339744827900E-01, 1.5707963267948965580E+00, 1.2246467991473531772E-16


def atan2(y: float, x: float) -> float:
    """Math.atan2 of V8 (fdlibm __ieee754_atan2), bit for bit (tiny = 1e-300 adds nothing)."""
    if x != x or y != y:
        return x + y
    if x == 1.0:
        return atan(y)
    if x and y:  # fast path: finite, nonzero, exponents close -> fdlibm's k is within +-60
        ex, ey = math.frexp(x)[1], math.frexp(y)[1]
        if -59 <= ey - ex <= 59 and -1021 <= ex <= 1024 and -1021 <= ey <= 1024:
            z = atan(abs(y / x))
            if x > 0:
                return z if y > 0 else -z
            return _PI - (z - _PI_LO) if y > 0 else (z - _PI_LO) - _PI
    hx, hy = _hi(x), _hi(y)
    ix, iy = hx & 0x7FFFFFFF, hy & 0x7FFFFFFF
    m = (1 if hy < 0 else 0) | (2 if hx < 0 else 0)
    if y == 0.0:
        return (y, y, _PI, -_PI)[m]
    if x == 0.0:
        return -_PI_O_2 if hy < 0 else _PI_O_2
    if ix == 0x7FF00000:
        if iy == 0x7FF00000:
            return (_PI_O_4, -_PI_O_4, 3.0 * _PI_O_4, -3.0 * _PI_O_4)[m]
        return (0.0, -0.0, _PI, -_PI)[m]
    if iy == 0x7FF00000:
        return -_PI_O_2 if hy < 0 else _PI_O_2
    k = (iy - ix) >> 20
    if k > 60:
        z = _PI_O_2 + 0.5 * _PI_LO
        m &= 1
    elif hx < 0 and k < -60:
        z = 0.0
    else:
        z = atan(abs(y / x))
    if m == 0:
        return z
    if m == 1:
        return -z
    if m == 2:
        return _PI - (z - _PI_LO)
    return (z - _PI_LO) - _PI


# ------------------------------------------- log10, log1p, asinh, cbrt, tan (fdlibm)
def _lo(x: float) -> int:
    return _bits(x) & 0xFFFFFFFF


def _set_lo(x: float, lo: int) -> float:
    return _from((_bits(x) & 0xFFFFFFFF00000000) | (lo & 0xFFFFFFFF))


def _words(hi: int, lo: int) -> float:
    return _from(((hi & 0xFFFFFFFF) << 32) | (lo & 0xFFFFFFFF))


_IVLN10, _LOG10_2HI, _LOG10_2LO = 4.34294481903251816668e-01, 3.01029995663611771306e-01, 3.69423907715893078616e-13


def log10(x: float) -> float:
    """Math.log10 of V8 (fdlibm __ieee754_log10, using the fdlibm log above), bit for bit."""
    hx, lx = _hi(x), _lo(x)
    k = 0
    if hx < 0x00100000:
        if ((hx & 0x7FFFFFFF) | lx) == 0:
            return -math.inf
        if hx < 0:
            return math.nan
        k -= 54
        x *= _TWO54
        hx, lx = _hi(x), _lo(x)
    if hx >= 0x7FF00000:
        return x + x
    if hx == 0x3FF00000 and lx == 0:
        return 0.0
    k += (hx >> 20) - 1023
    i = 1 if k < 0 else 0
    hx = (hx & 0x000FFFFF) | ((0x3FF - i) << 20)
    y = float(k + i)
    x = _words(hx, lx)
    z = y * _LOG10_2LO + _IVLN10 * log(x)
    return z + y * _LOG10_2HI


_LP = (6.666666666666735130e-01, 3.999999999940941908e-01, 2.857142874366239149e-01, 2.222219843214978396e-01,
       1.818357216161805012e-01, 1.531383769920937332e-01, 1.479819860511658591e-01)


def log1p(x: float) -> float:
    """Math.log1p of V8 (fdlibm log1p), bit for bit."""
    hx = _hi(x)
    ax = hx & 0x7FFFFFFF
    k = 1
    f = c = 0.0
    hu = 0
    if hx < 0x3FDA827A:
        if ax >= 0x3FF00000:
            return -math.inf if x == -1.0 else math.nan
        if ax < 0x3E200000:
            if ax < 0x3C900000:
                return x
            return x - x * x * 0.5
        if hx > 0 or hx <= -1076707644:  # (int32_t)0xBFD2BEC4
            k = 0
            f = x
            hu = 1
    if hx >= 0x7FF00000:
        return x + x
    if k != 0:
        if hx < 0x43400000:
            u = 1.0 + x
            hu = _hi(u)
            k = (hu >> 20) - 1023
            c = (1.0 - (u - x)) if k > 0 else (x - (u - 1.0))
            c /= u
        else:
            u = x
            hu = _hi(u)
            k = (hu >> 20) - 1023
            c = 0.0
        hu &= 0x000FFFFF
        if hu < 0x6A09E:
            u = _with_hi(u, hu | 0x3FF00000)
        else:
            k += 1
            u = _with_hi(u, hu | 0x3FE00000)
            hu = (0x00100000 - hu) >> 2
        f = u - 1.0
    hfsq = 0.5 * f * f
    if hu == 0:
        if f == 0.0:
            if k == 0:
                return 0.0
            c += k * _LN2_LO
            return k * _LN2_HI + c
        R = hfsq * (1.0 - 0.66666666666666666 * f)
        if k == 0:
            return f - R
        return k * _LN2_HI - ((R - (k * _LN2_LO + c)) - f)
    Lp1, Lp2, Lp3, Lp4, Lp5, Lp6, Lp7 = _LP
    s = f / (2.0 + f)
    z = s * s
    R = z * (Lp1 + z * (Lp2 + z * (Lp3 + z * (Lp4 + z * (Lp5 + z * (Lp6 + z * Lp7))))))
    if k == 0:
        return f - (hfsq - s * (hfsq + R))
    return k * _LN2_HI - ((hfsq - (s * (hfsq + R) + (k * _LN2_LO + c))) - f)


_LN2D = 6.93147180559945286227e-01


def asinh(x: float) -> float:
    """Math.asinh of V8 (fdlibm asinh), bit for bit."""
    hx = _hi(x)
    ix = hx & 0x7FFFFFFF
    if ix >= 0x7FF00000:
        return x + x
    if ix < 0x3E300000:
        return x
    if ix > 0x41B00000:
        w = log(abs(x)) + _LN2D
    elif ix > 0x40000000:
        t = abs(x)
        w = log(2.0 * t + 1.0 / (math.sqrt(x * x + 1.0) + t))
    else:
        t = x * x
        w = log1p(abs(x) + t / (1.0 + math.sqrt(1.0 + t)))
    return w if hx > 0 else -w


_CB_B1, _CB_B2 = 715094163, 696219795
_CB_P = (1.87595182427177009643, -1.88497979543377169875, 1.621429720105354466140, -0.758397934778766047437,
         0.145996192886612446982)


def cbrt(x: float) -> float:
    """Math.cbrt of V8 (FreeBSD/fdlibm cbrt), bit for bit."""
    b = _bits(x)
    hx = (b >> 32) & 0xFFFFFFFF
    low = b & 0xFFFFFFFF
    sign = hx & 0x80000000
    hx ^= sign
    if hx >= 0x7FF00000:
        return x + x
    if hx < 0x00100000:
        if (hx | low) == 0:
            return x
        t = _words(0x43500000, 0) * x
        high = _hi(t) & 0xFFFFFFFF
        t = _words(sign | ((high & 0x7FFFFFFF) // 3 + _CB_B2), 0)
    else:
        t = _words(sign | (hx // 3 + _CB_B1), 0)
    P0, P1, P2, P3, P4 = _CB_P
    r = (t * t) * (t / x)
    t = t * ((P0 + r * (P1 + r * P2)) + ((r * r) * r) * (P3 + r * P4))
    t = _from((_bits(t) + 0x80000000) & 0xFFFFFFFFC0000000)
    s = t * t
    r = x / s
    w = t + t
    r = (r - t) / (w + r)
    return t + t * r


_TT = (3.33333333333334091986e-01, 1.33333333333201242699e-01, 5.39682539762260521377e-02, 2.18694882948595424599e-02,
       8.86323982359930005737e-03, 3.59207910759131235356e-03, 1.45620945432529025516e-03, 5.88041240820264096874e-04,
       2.46463134818469906812e-04, 7.81794442939557092300e-05, 7.14072491382608190305e-05, -1.85586374855275456654e-05,
       2.59073051863633712884e-05)
_PIO4, _PIO4LO = 7.85398163397448278999e-01, 3.06161699786838301793e-17


def _kernel_tan(x, y, iy):
    T = _TT
    hx = _hi(x)
    ix = hx & 0x7FFFFFFF
    if ix < 0x3E300000:
        if ((ix | _lo(x)) | (iy + 1)) == 0:
            return 1.0 / abs(x)
        if iy == 1:
            return x
        z = w = x + y
        z = _set_lo(z, 0)
        v = y - (z - x)
        t = a = -1.0 / w
        t = _set_lo(t, 0)
        s = 1.0 + t * z
        return t + a * (s + t * v)
    if ix >= 0x3FE59428:
        if hx < 0:
            x, y = -x, -y
        z = _PIO4 - x
        w = _PIO4LO - y
        x = z + w
        y = 0.0
    z = x * x
    w = z * z
    r = T[1] + w * (T[3] + w * (T[5] + w * (T[7] + w * (T[9] + w * T[11]))))
    v = z * (T[2] + w * (T[4] + w * (T[6] + w * (T[8] + w * (T[10] + w * T[12])))))
    s = z * x
    r = y + z * (s * (r + v) + y)
    r += T[0] * s
    w = x + r
    if ix >= 0x3FE59428:
        v = float(iy)
        return (-1 if hx < 0 else 1) * (v - 2.0 * (x - (w * w / (w + v) - r)))
    if iy == 1:
        return w
    z = _set_lo(w, 0)
    v = r - (z - x)
    t = a = -1.0 / w
    t = _set_lo(t, 0)
    s = 1.0 + t * z
    return t + a * (s + t * v)


_NPIO2_HW = (0x3FF921FB, 0x400921FB, 0x4012D97C, 0x401921FB, 0x401F6A7A, 0x4022D97C, 0x4025FDBB, 0x402921FB,
             0x402C463A, 0x402F6A7A, 0x4031475C, 0x4032D97C, 0x40346B9C, 0x4035FDBB, 0x40378FDB, 0x403921FB,
             0x403AB41B, 0x403C463A, 0x403DD85A, 0x403F6A7A, 0x40407E4C, 0x4041475C, 0x4042106C, 0x4042D97C,
             0x4043A28C, 0x40446B9C, 0x404534AC, 0x4045FDBB, 0x4046C6CB, 0x40478FDB, 0x404858EB, 0x404921FB)
_INVPIO2 = 6.36619772367581382433e-01
_PIO2_1, _PIO2_1T = 1.57079632673412561417e+00, 6.07710050650619224932e-11
_PIO2_2, _PIO2_2T = 6.07710050630396597660e-11, 2.02226624879595063154e-21
_PIO2_3, _PIO2_3T = 2.02226624871116645580e-21, 8.47842766036889956997e-32


def _rem_pio2(x):
    """fdlibm __ieee754_rem_pio2 for |x| <= 2^19 pi/2: (n, y0, y1); None beyond."""
    hx = _hi(x)
    ix = hx & 0x7FFFFFFF
    if ix <= 0x3FE921FB:
        return 0, x, 0.0
    if ix < 0x4002D97C:
        if hx > 0:
            z = x - _PIO2_1
            if ix != 0x3FF921FB:
                y0 = z - _PIO2_1T
                return 1, y0, (z - y0) - _PIO2_1T
            z -= _PIO2_2
            y0 = z - _PIO2_2T
            return 1, y0, (z - y0) - _PIO2_2T
        z = x + _PIO2_1
        if ix != 0x3FF921FB:
            y0 = z + _PIO2_1T
            return -1, y0, (z - y0) + _PIO2_1T
        z += _PIO2_2
        y0 = z + _PIO2_2T
        return -1, y0, (z - y0) + _PIO2_2T
    if ix <= 0x413921FB:
        t = abs(x)
        n = int(t * _INVPIO2 + 0.5)
        fn = float(n)
        r = t - fn * _PIO2_1
        w = fn * _PIO2_1T
        if n < 32 and ix != _NPIO2_HW[n - 1]:
            y0 = r - w
        else:
            j = ix >> 20
            y0 = r - w
            i = j - ((_hi(y0) >> 20) & 0x7FF)
            if i > 16:
                t = r
                w = fn * _PIO2_2
                r = t - w
                w = fn * _PIO2_2T - ((t - r) - w)
                y0 = r - w
                i = j - ((_hi(y0) >> 20) & 0x7FF)
                if i > 49:
                    t = r
                    w = fn * _PIO2_3
                    r = t - w
                    w = fn * _PIO2_3T - ((t - r) - w)
                    y0 = r - w
        y1 = (r - y0) - w
        if hx < 0:
            return -n, -y0, -y1
        return n, y0, y1
    return None


def tan(x: float) -> float:
    """Math.tan of V8 (fdlibm tan), bit for bit for |x| <= 2^19 pi/2 (platform tan beyond,
    where fdlibm needs the Payne-Hanek reduction; no Atlas page reaches it)."""
    ix = _hi(x) & 0x7FFFFFFF
    if ix <= 0x3FE921FB:
        return _kernel_tan(x, 0.0, 1)
    if ix >= 0x7FF00000:
        return x - x
    r = _rem_pio2(x)
    if r is None:
        return math.tan(x)
    n, y0, y1 = r
    return _kernel_tan(y0, y1, 1 - ((n & 1) << 1))


# ------------------------------------------- String.prototype.localeCompare
# ICU root collation (Chromium's localeCompare, locale en-US) for the characters of class and
# operation labels.  Primary order, as listed by Chromium 141 for these characters:
_ICU_ORDER = (' _-,;:!?.·\'"()[]{}⟨⟩@*/\\&#%′″‴`^→+×<=>|~−∞$0123456789'
              'abcdefghijklmnopqrstuvwxyzαβγδεζηθικλμνξοπρστυφχψω')
_PRIMARY = {c: i for i, c in enumerate(_ICU_ORDER)}
for _d in range(10):  # superscript and subscript digits: same primary, tertiary 1 and 2
    _PRIMARY["⁰¹²³⁴⁵⁶⁷⁸⁹"[_d]] = _PRIMARY["₀₁₂₃₄₅₆₇₈₉"[_d]] = _PRIMARY[str(_d)]
for _c in "abcdefghijklmnopqrstuvwxyzαβγδεζηθικλμνξοπρστυφχψω":
    _PRIMARY[_c.upper()] = _PRIMARY[_c]
_TERT = {**{c: 1 for c in "⁰¹²³⁴⁵⁶⁷⁸⁹"}, **{c: 2 for c in "₀₁₂₃₄₅₆₇₈₉"}}


def locale_key(s: str):
    """Sort key equivalent to ICU root localeCompare on the label alphabet (see jsmath §1):
    primary weights of all characters, then tertiary (digit variant, lower < upper case)."""
    prim = tuple(_PRIMARY.get(c, 1000 + ord(c)) for c in s)
    tert = tuple(_TERT.get(c, 0) + (4 if c.isupper() else 0) for c in s)
    return prim, tert, s


def locale_compare(a: str, b: str) -> int:
    ka, kb = locale_key(a), locale_key(b)
    return (ka > kb) - (ka < kb)



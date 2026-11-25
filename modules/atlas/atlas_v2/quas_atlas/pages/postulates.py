"""Endpoints of the page "Postulates and measurement" (web/<lang>/postulates.html); model: core.postulates."""
import math

from ..api import Param, endpoint
from ..core import postulates as m

_C = Param("list", check=lambda v: len(v) == m.NMAX, doc=f"{m.NMAX} amplitudes {{re, im}}")
_t = Param("float", check=lambda v: abs(v) <= 1e6, doc="|t| <= 1e6 (units of T1)")
_r = Param("float", check=lambda v: 0 <= v < 1, doc="uniform random number in [0, 1)")
_four = Param("list", check=lambda v: len(v) == 4 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v))


@endpoint("post.prepare", a=_four, ph=_four)
def prepare(a, ph):
    """Normalised superposition of psi_1..psi_4."""
    return m.prepare([float(x) for x in a], [float(x) for x in ph])


@endpoint("post.frame", C=_C, t=_t, t0=_t)
def frame(C, t, t0):
    """|Psi|^2, Re Psi, observables and probabilities at time t."""
    return m.frame(C, t, t0)


@endpoint("post.measureE", C=_C, t=_t, t0=_t, r=_r)
def measure_e(C, t, t0, r):
    """One energy measurement with collapse."""
    return m.measure_energy(C, t, t0, r)


@endpoint("post.measureMany", a=_four, ph=_four,
          rs=Param("list", check=lambda v: 0 < len(v) <= 5000 and all(isinstance(x, (int, float)) and 0 <= x < 1 for x in v)))
def measure_many(a, ph, rs):
    """Energy measured once on each of len(rs) identically prepared systems."""
    return m.measure_many([float(x) for x in a], [float(x) for x in ph], [float(x) for x in rs])


@endpoint("post.measureX", C=_C, t=_t, t0=_t, r=_r, sigma=Param("float", check=lambda v: 0.005 <= v <= 0.2))
def measure_x(C, t, t0, r, sigma):
    """Position measurement with resolution sigma."""
    return m.measure_position(C, t, t0, r, sigma)


@endpoint("post.operator", C=_C, t=_t, t0=_t, op=Param("str", check=lambda v: v in ("H", "p", "x"), doc="H, p or x"))
def operator(C, t, t0, op):
    """A Psi for an observable, <A> and the spread of its values (section 4)."""
    return m.operator(C, t, t0, op)


@endpoint("post.meanSeries", a=_four, ph=_four,
          rs=Param("list", check=lambda v: 0 < len(v) <= 5000 and all(isinstance(x, (int, float)) and 0 <= x < 1 for x in v)))
def mean_series(a, ph, rs):
    """Running mean of the measured energy against <E> (section 5)."""
    return m.mean_series([float(x) for x in a], [float(x) for x in ph], [float(x) for x in rs])

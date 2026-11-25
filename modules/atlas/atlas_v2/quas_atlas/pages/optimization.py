"""Endpoints of the page "Geometry optimisation" (web/<lang>/optimization.html); model: core.optimization."""
import math

from ..api import Param, endpoint
from ..core import optimization as op


@endpoint("opt.static")
def static():
    """Minimum of the H2O surface, contour segments, Hessian eigenvalues and harmonic frequencies at the minimum."""
    return op.static()


def _start(v):
    return (isinstance(v, list) and len(v) == 2 and all(isinstance(x, (int, float)) and math.isfinite(x) for x in v)
            and op.inside(v[0], v[1]))


@endpoint("opt.runs", start=Param("list", check=_start), step=Param("float", check=lambda v: 0 < v <= 5))
def runs(start, step):
    """Trajectories of steepest descent, line-search descent, Newton-Raphson and BFGS from a start (r A, theta deg)."""
    return op.runs(start, step)

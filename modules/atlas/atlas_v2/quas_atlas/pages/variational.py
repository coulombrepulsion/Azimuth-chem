"""Endpoints of the page "Variational method and perturbation theory" (web/<lang>/variational.html);
model: core.variational."""
from ..api import Param, endpoint
from ..core import variational as V


@endpoint("var.trial", trial=Param("str", check=lambda v: v in V.TRIAL), v=Param("float", check=lambda v: 1e-4 <= v <= 100))
def trial(trial, v):
    """E(parameter) curve, radial densities and the virial ratio for a Slater or Gaussian trial function."""
    return V.trial(trial, v)


_N = Param("int", check=lambda v: 1 <= v <= 10)
_a0 = Param("float", check=lambda v: 1e-5 <= v <= 10)
_be = Param("float", check=lambda v: 1.01 <= v <= 20)


@endpoint("var.lvm", N=_N, a0=_a0, be=_be)
def lvm(N, a0, be):
    """Linear variation in N even-tempered s-Gaussians: roots, E(N), the ground-state function."""
    return V.lvm_view(N, a0, be)


@endpoint("var.optimize", N=_N, a0=_a0, be=_be)
def optimize(N, a0, be):
    """Pattern-search optimum of a0 and beta for N functions (beta = 4 for N = 1)."""
    r = V.opt_for(N, a0, be)
    return {"a0": r["a0"], "be": 4 if N == 1 else r["be"], "E": r["E"]}


@endpoint("var.optcurve")
def optcurve():
    """Energies with optimised even-tempered bases for N = 1..10."""
    return list(V.opt_curve())


@endpoint("var.pt", lam=Param("float", check=lambda v: 0 <= v <= 1), n=Param("int", check=lambda v: 0 <= v <= 3))
def pt(lam, n):
    """Perturbation series vs exact levels of x^2/2 + lambda x^4; the potential and its levels."""
    return V.pt(lam, n)

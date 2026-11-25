"""Endpoints of the page "Basis sets" (web/<lang>/basis.html); model: core.basis."""
import math

from ..api import Param, endpoint
from ..core import basis


def _exps(v):
    return isinstance(v, list) and 1 <= len(v) <= 6 and all(isinstance(x, (int, float)) and math.isfinite(x) and 1e-3 <= x <= 1e3 for x in v)


@endpoint("basis.part1", set=Param("str", check=lambda v: v in ("sto", "opt", "cust")), n=Param("int", check=lambda v: 1 <= v <= 6),
          cust=Param("list", None, check=lambda v: v is None or _exps(v)), sc=Param("str", check=lambda v: v in ("lin", "log")))
def part1(set, n, cust, sc):  # noqa: A002 (name of the page parameter)
    """Hydrogen 1s in s-Gaussians: exponents, coefficients, psi and radial-density curves, energies, overlap."""
    if set == "sto" and n not in basis.STONG:
        raise ValueError("STO-nG exists for n = 1, 2, 3, 6")
    if set == "cust" and (cust is None or len(cust) != n):
        raise ValueError("cust: n exponents expected")
    return basis.part1(set, n, cust, sc)


@endpoint("basis.optimize", start=Param("list", check=_exps))
def optimize(start):
    """Energy-optimal exponents from the given start (Nelder-Mead in ln a)."""
    return basis.optimize(len(start), 1, start)


@endpoint("basis.part2", la=Param("float", check=lambda v: -3 <= v <= 2))
def part2(la):
    """One Gaussian exp(-a r^2) for H: T, V, E(a), virial ratio and the optimum a = 8/(9 pi)."""
    return basis.part2(la)


@endpoint("basis.part3", f=Param("str"))
def part3(f):
    """Numbers of basis functions, primitives, integrals and relative HF cost of eleven basis sets for a formula."""
    return basis.part3(f)

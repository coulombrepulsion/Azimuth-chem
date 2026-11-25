"""Endpoints of the page "Reaction rate: transition state" (web/<lang>/kinetics.html); model: core.kinetics."""
from ..api import Param, endpoint
from ..core import kinetics


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("kin.state", dH=_rng(0, 400), dS=_rng(-400, 400), T=_rng(1, 5000), n=Param("int", check=lambda v: v in (1, 2)),
          nu=_rng(100, 5000), im=_rng(0, 10000))
def state(dH, dS, T, n, nu, im):
    """dG‡, Eyring k, half-life, Arrhenius Ea and A, the t½(dG‡) line, isotope effect, Wigner kappa."""
    return kinetics.state(dH, dS, T, n, nu, im)


@endpoint("kin.custom", Gr=_rng(-1e6, 1e6), Gt=_rng(-1e6, 1e6), T=Param("float", check=lambda v: 0 < v <= 1e5),
          n=Param("int", check=lambda v: v in (1, 2)), sol=Param("bool"), im=_rng(0, 1e5))
def custom(Gr, Gt, T, n, sol, im):
    """Barrier, rate constant and half-life from free energies G(R), G(TS) in hartree."""
    return kinetics.custom(Gr, Gt, T, n, sol, im)

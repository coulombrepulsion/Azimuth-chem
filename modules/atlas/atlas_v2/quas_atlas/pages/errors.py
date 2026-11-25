"""Endpoints of the page on the error of a calculation (errors.html); model: core.errors."""
from ..api import Param, endpoint
from ..core import errors


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("err.sum", sm=_rng(0, 30), sb=_rng(0, 30), sc=_rng(0, 30))
def total(sm, sb, sc):
    """Independent errors added in squares."""
    return errors.total(sm, sb, sc)


@endpoint("err.interval", mae=_rng(0.5, 30), T=_rng(200, 1000))
def interval(mae, T):
    """From the mean absolute error to σ, the 95 % interval and the factor in a rate constant."""
    return errors.interval(mae, T)


@endpoint("err.isodesmic", dch=_rng(0, 20), dcc=_rng(0, 20), dco=_rng(0, 20), doh=_rng(0, 20), sigma=_rng(0, 30),
          rho=_rng(-1, 1))
def isodesmic(dch, dcc, dco, doh, sigma, rho):
    """Bond errors through atomization and through an isodesmic reaction; a correction by a related system."""
    return errors.isodesmic(dch, dcc, dco, doh, sigma, rho)


@endpoint("err.conformers", dG=_rng(-10, 10), s=_rng(0, 10), T=_rng(200, 1000))
def conformers(dG, s, T):
    """The share of the second of two conformers and its interval."""
    return errors.conformers(dG, s, T)

"""Endpoints of the pages on molecular dynamics and learned potentials (mlmd.html) and on machine learning in quantum
chemistry (mlqc.html); model: core.mlpot."""
from ..api import Param, endpoint
from ..core import mlpot


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("ml.verlet", system=Param("str", check=lambda v: v in mlpot.SYSTEMS),
          method=Param("str", check=lambda v: v in ("verlet", "euler")), dt=_rng(0.05, 6), E0=_rng(0.02, 1.5))
def verlet(system, method, dt, E0):
    """The total energy of a Morse bond by velocity Verlet or Euler over 200 fs."""
    return mlpot.verlet(system, dt, method, E0)


@endpoint("ml.committee", n=Param("int", check=lambda v: 4 <= v <= 40), hi=_rng(2.4, 3.5))
def committee(n, hi):
    """Five models of a bond trained inside 2.15 Å…hi: their mean, spread and error inside and outside."""
    return mlpot.committee(n, hi)


@endpoint("ml.events", N=_rng(8, 100000), T=_rng(100, 2500), barrier=_rng(0.1, 2), length=_rng(1, 1e6))
def events(N, T, barrier, length):
    """δT of N atoms; the Eyring rate of a barrier, the events in a trajectory of `length` ps and its cost."""
    return mlpot.events(N, T, barrier, length)


@endpoint("ml.delta", n=Param("int", check=lambda v: 4 <= v <= 128), cheap=_rng(0, 1), sigma=_rng(0.1, 2))
def delta(n, cheap, sigma):
    """Learning curves of the energy learned directly and as a correction to a cheap method."""
    return mlpot.delta(n, cheap, sigma)


@endpoint("ml.mae", n=Param("int", check=lambda v: 3 <= v <= 400), a=_rng(1, 30), b=_rng(1, 30))
def mae(n, a, b):
    """The MAE of two models measured on n test molecules, with its uncertainty."""
    return mlpot.mae(n, a, b)


@endpoint("ml.hull", e13=_rng(-1, 0.3), e12=_rng(-1, 0.3), x=_rng(0.05, 0.95), e=_rng(-1, 0.3))
def hull(e13, e12, x, e):
    """The convex hull of A, AB2, AB, B and the height of a new compound above it."""
    return mlpot.hull(e13, e12, x, e)

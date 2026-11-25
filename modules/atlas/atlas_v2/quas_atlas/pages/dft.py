"""Endpoints of the page "Density functional theory" (web/<lang>/dft.html); model: core.dft."""
from ..api import Param, endpoint
from ..core import dft

_ai = Param("int", check=lambda v: 0 <= v < len(dft.DATA["A"]))


@endpoint("dft.meta")
def meta():
    """Fractions a of exact exchange and the default distance index of the H2+ section."""
    return dft.meta()


@endpoint("dft.sie")
def sie():
    """Self-interaction of the H atom for HF, LDA, LSDA, B88+LSDA, PBE+LSDA (fixed and optimal zeta)."""
    return dft.sie()


@endpoint("dft.en", ai=_ai)
def en(ai):
    """E(N) of H for 0 <= N <= 2 with the fraction a of exact exchange: curves, slopes, deviation from linearity."""
    return dft.en(ai)


@endpoint("dft.h2", ai=_ai, ri=Param("int", check=lambda v: 0 <= v < len(dft.DATA["RR"])))
def h2(ai, ri):
    """H2+ dissociation curves (exact, functional delocalised and localised) and the values at R = RR[ri]."""
    return dft.h2(ai, ri)

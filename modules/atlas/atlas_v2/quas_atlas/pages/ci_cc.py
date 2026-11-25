"""Endpoints of the page "CI and coupled clusters" (web/<lang>/ci-cc.html); model: core.ci_cc."""
from ..api import Param, endpoint
from ..core import ci_cc


@endpoint("cicc.dets", m=Param("int", check=lambda v: 0 <= v < len(ci_cc.MOL)), b=Param("int", check=lambda v: 0 <= v <= 3))
def dets(m, b):
    """Numbers of determinants by excitation level, CISD and full CI sizes for a molecule and basis set."""
    return ci_cc.dets(m, b)


@endpoint("cicc.h2")
def h2():
    """H2/STO-3G 2x2 CI curve (HF and full CI) and the (H2)n size-consistency table."""
    return ci_cc.h2()


@endpoint("cicc.state", i=Param("int", check=lambda v: 0 <= v < len(ci_cc.P)))
def state(i):
    """H2 at grid point i: CI matrix, weights, correlation energy, n-pair CISD model and dimer amplitudes."""
    return ci_cc.state(i)

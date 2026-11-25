"""Endpoints of the page "Perturbation theory and MP2" (web/<lang>/mp2.html); model: core.mp2."""
from ..api import Param, endpoint
from ..core import mp2


@endpoint("mp2.meta")
def meta():
    """H2 data rows (STO-3G) and the lengths of the MPn series."""
    return mp2.meta()


@endpoint("mp2.h2", i=Param("int", check=lambda v: 0 <= v < len(mp2.D["h2"])))
def h2(i):
    """H2 at the i-th distance: E(0), E(1), E(2), orbital gap, exact correlation, MP2 share."""
    return mp2.h2(i)


@endpoint("mp2.series", g=Param("int", check=lambda v: 0 <= v < 3, doc="0: R_e, 1: 1.5 R_e, 2: 2 R_e"))
def series(g):
    """Partial sums of the MPn series of water and their errors vs full CI (mEh)."""
    return mp2.series(g)


@endpoint("mp2.tab")
def tab():
    """MP2 correlation energy as a percentage of CCSD(T) (cc-pVDZ)."""
    return mp2.tab()

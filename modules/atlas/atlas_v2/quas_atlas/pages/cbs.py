"""Endpoints of the page "Basis convergence and the CBS limit" (web/<lang>/cbs.html); model: core.cbs."""
from ..api import Param, endpoint
from ..core import cbs


@endpoint("cbs.meta")
def meta():
    """Molecules and those with cc-pV5Z results."""
    return cbs.meta()


@endpoint("cbs.conv", m=Param("int", check=lambda v: 0 <= v < len(cbs.D["mols"])), q=Param("int", check=lambda v: 0 <= v <= 3))
def conv(m, q):
    """HF energy, MP2 / CCSD(T) correlation or atomisation energy vs X, and the CBS limit."""
    return cbs.conv(m, q)


@endpoint("cbs.xtab", p=Param("int", check=lambda v: 0 <= v <= 2))
def xtab(p):
    """Two-point X^-3 extrapolation of the CCSD(T) correlation energy vs the best estimate."""
    return cbs.xtab(p)


@endpoint("cbs.tae")
def tae():
    """CCSD(T) atomisation energies in DZ, TZ, QZ and the TZ/QZ CBS estimate."""
    return cbs.tae_all()

"""Endpoints of the EPR and NICS panels of the NMR page (nmr.html); model: core.magnetic."""
from ..api import Param, endpoint
from ..core import magnetic


@endpoint("nmr.fermi", basis=Param("str", check=lambda v: v in ("g1", "sto3g", "sto6g")))
def fermi(basis):
    """The Fermi contact of hydrogen with the density at the nucleus in a Gaussian basis."""
    return magnetic.fermi(basis)


@endpoint("nmr.ring", nics0=Param("float", check=lambda v: -40 <= v <= 40, doc="−40..40"),
          R=Param("float", check=lambda v: 0.6 <= v <= 3, doc="0.6..3"))
def ring(nics0, R):
    """NICS of a π ring current along the axis and in the plane."""
    return magnetic.ring(nics0, R)

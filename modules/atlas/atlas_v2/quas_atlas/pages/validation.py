"""Endpoints of the page "Validation" (web/<lang>/validation.html); model: core.validation."""
from ..api import Param, endpoint
from ..core import validation as va


@endpoint("val.rhf", i=Param("int", check=lambda v: 0 <= v < len(va.DATA["mol"])), b=Param("int", check=lambda v: 0 <= v < len(va.BASES)))
def rhf(i, b):
    """RHF energy of molecule i of the table in basis b (0 STO-3G, 1 6-31G*, 2 6-31G**)."""
    return va.rhf_energy(i, b)


@endpoint("val.cr")
def cr():
    """Water, STO-3G, Crawford geometry: RHF energy, MP2 correction, |dipole|, Mulliken charges of O and H."""
    return va.crawford()

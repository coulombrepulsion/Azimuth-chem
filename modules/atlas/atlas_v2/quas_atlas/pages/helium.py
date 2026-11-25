"""Endpoints of the page "Helium atom and electron correlation" (web/<lang>/helium.html); model: core.helium."""
from ..api import Param, endpoint
from ..core import helium as He

_Z = Param("int", check=lambda v: v in (1, 2, 3, 4))


@endpoint("he.table", Z=_Z)
def table(Z):
    """Energies of the approximation ladder (bare nucleus ... Hylleraas 6 terms, exact) and their errors."""
    return He.table(Z)


@endpoint("he.zeta", Z=_Z, zeta=Param("float", check=lambda v: 0.01 <= v <= 20))
def zeta(Z, zeta):
    """Effective-charge model: T, V_ne, V_ee and E as functions of zeta; values at zeta."""
    return He.zeta_view(Z, zeta)


@endpoint("he.hole", memo=True, Z=_Z, r1=Param("float", check=lambda v: 0.01 <= v <= 10))
def hole(Z, r1):
    """Conditional density of electron 2 (6-term Hylleraas) vs uncorrelated, <r12>, <1/r12>."""
    return He.hole(Z, r1)

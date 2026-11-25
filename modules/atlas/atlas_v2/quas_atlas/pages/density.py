"""Endpoints of the page "Electron density" (web/<lang>/density.html); model: core.density."""
from ..api import Param, endpoint
from ..core import density

_mol = Param("str", check=lambda v: v in density.MOLD, doc="H2 or HeH")
_R = Param("float", check=lambda v: 0.3 <= v <= 20, doc="0.3 <= R <= 20 bohr")
_c = Param("float", check=lambda v: abs(v) <= 50, doc="|coordinate| <= 50 bohr")


@endpoint("dens.view", mol=_mol, R=_R, view=Param("str", check=lambda v: v in ("rho", "drho", "lap", "esp")))
def view(mol, R, view):
    """Map (240 x 147), axis profile and bond critical point of one field."""
    return density.view_data(mol, R, view)


@endpoint("dens.point", mol=_mol, R=_R, x=_c, z=_c)
def point(mol, R, x, z):
    """rho, Delta rho, Laplacian and potential at one point."""
    return density.point(mol, R, x, z)

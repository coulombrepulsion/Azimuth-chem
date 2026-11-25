"""Endpoints of the page "Dissociation of H2" (web/<lang>/h2.html); model: core.h2."""
from ..api import Param, endpoint
from ..core import h2

_R = Param("float", check=lambda R: 0 < R <= 100, doc="0 < R <= 100 bohr")


@endpoint("h2.scan", memo=True)  # 1,8 s, the same every time
def scan():
    """Energies of all methods on the grid R = 0.5..8 bohr, limit 2E(H), R_e."""
    return h2.h2_scan()


@endpoint("h2.point", R=_R)
def point(R):
    """All quantities at one R plus the orbitals on the axis."""
    return {"p": h2.h2_point(R), "orb": h2.orbital_curves(R)}


@endpoint("h2.errors",
          R=Param("float", check=lambda v: v in (1.4, 10.0), doc="1.4 or 10"),
          basis=Param("str", check=lambda v: v in ("STO-3G", "6-31G", "6-31G**")),
          method=Param("str", check=lambda v: v in ("rhf", "mp2", "fci")),
          iters=Param("int", 0, check=lambda v: v in (0, 1, 2, 3)))
def errors(R, basis, method, iters):
    """SCF / method / basis decomposition of E - E_exact."""
    return h2.error_budget(R, basis, method, iters)

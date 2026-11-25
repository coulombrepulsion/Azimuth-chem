"""Endpoints of the page "Potential energy surface" (web/<lang>/pes.html); model: core.pes."""
from ..api import Param, endpoint
from ..core import pes

_r = Param("float", check=lambda v: 0.3 <= v <= 5, doc="0.3 <= r <= 5 angstrom")
_iso = Param("str", check=lambda v: v in ("H", "D"))


@endpoint("pes.static", memo=True)
def static():
    """TS, reaction path with ZPE, barriers and the map grids."""
    return pes.static()


@endpoint("pes.point", r1=_r, r2=_r, iso=_iso)
def point(r1, r2, iso):
    """Energy, gradient, curvatures, frequencies and the kind of point."""
    return pes.analyse(r1, r2, iso)


@endpoint("pes.descend", r1=_r, r2=_r, iso=_iso)
def descend(r1, r2, iso):
    """Steepest descent from (r1, r2)."""
    return pes.descend(r1, r2, iso)


@endpoint("pes.newton", r1=_r, r2=_r, iso=_iso)
def newton(r1, r2, iso):
    """Newton's method from (r1, r2)."""
    return pes.newton(r1, r2, iso)


@endpoint("pes.traj", Ecol=Param("float", check=lambda v: 0 < v <= 5), vib=Param("bool"),
          phase=Param("float", check=lambda v: 0 <= v < 360), iso=_iso)
def traj(Ecol, vib, phase, iso):
    """One collinear A + BC trajectory."""
    return pes.trajectory(Ecol, vib, phase, iso)


@endpoint("pes.series", Ecol=Param("float", check=lambda v: 0 < v <= 5), iso=_iso)
def series(Ecol, iso):
    """Reaction outcome for 24 vibrational phases."""
    return pes.series(Ecol, iso)


@endpoint("pes.kie", T=Param("float", check=lambda v: 10 <= v <= 5000))
def kie(T):
    """Wigner factors and the ZPE barrier ratio at temperature T."""
    return pes.kie(T)


@endpoint("pes.lz", lv=Param("float", check=lambda v: -6 <= v <= 1), v=Param("float", check=lambda v: 1 <= v <= 1e5))
def lz(lv, v):
    """Avoided crossing Na + Cl and Landau-Zener probabilities."""
    return pes.lz(lv, v)

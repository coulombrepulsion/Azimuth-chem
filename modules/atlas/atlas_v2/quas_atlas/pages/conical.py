"""Endpoints of the page on conical intersections and biradicals (conical.html); model: core.conical."""
from ..api import Param, endpoint
from ..core import conical


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


def _sw():
    return Param("int", check=lambda v: v in (0, 1), doc="0|1")


@endpoint("cone.cross", c=_rng(0, 0.5), sym=_sw())
def cross(c, sym):
    """Two diabatic curves and their adiabatic states: avoided crossing or crossing."""
    return conical.cross(c, sym)


@endpoint("cone.cone", g=_rng(0.2, 2), h=_rng(0, 2), y0=_rng(-1, 1), tilt=_rng(-1, 1), tddft=_sw(),
          atoms=Param("int", check=lambda v: 2 <= v <= 30))
def cone(g, h, y0, tilt, tddft, atoms):
    """The double cone in the branching plane, its sections and the dimension of the seam."""
    return conical.cone(g, h, y0, tilt, tddft, atoms)


@endpoint("cone.twosite", t=_rng(0, 2), U=_rng(1, 10), K=_rng(0, 0.3))
def twosite(t, U, K):
    """The singlet–triplet splitting of the two-centre model and the hopping of the benzynes."""
    return conical.twosite(t, U, K)


@endpoint("cone.yamaguchi", dE=_rng(0, 100), s2=_rng(0, 1.5))
def yamaguchi(dE, s2):
    """The Yamaguchi formula for a broken-symmetry solution; p-benzyne by several methods."""
    return conical.yamaguchi(dE, s2)

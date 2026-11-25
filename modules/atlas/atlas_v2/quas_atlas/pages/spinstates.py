"""Endpoints of the page on the spin states of transition-metal complexes (spinstates.html); model: core.spinstates."""
from ..api import Param, endpoint
from ..core import spinstates


@endpoint("spin.gap", a=Param("float", check=lambda v: 0 <= v <= 60, doc="0..60"))
def gap(a):
    """The spin gap of three Fe(II) complexes against the share of exact exchange."""
    return spinstates.gap(a)


@endpoint("spin.contam", S=Param("float", check=lambda v: v in (0, 0.5, 1, 1.5, 2, 2.5, 3), doc="0, ½, …, 3"),
          s2=Param("float", check=lambda v: 0 <= v <= 20, doc="0..20"))
def contam(S, s2):
    """The exact ⟨S²⟩, the excess and the admixture of the next spin state."""
    return spinstates.contam(S, s2)


@endpoint("spin.geom", key=Param("str", check=lambda v: v in ("water", "nch", "co")))
def geom(key):
    """The Fe–L bonds of the quintet and the singlet of a complex."""
    return spinstates.geom(key)

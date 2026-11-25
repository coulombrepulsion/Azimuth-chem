"""Endpoints of the page "Atomic terms" (web/<lang>/terms.html); model: core.terms."""
from ..api import Param, endpoint
from ..core import terms


@endpoint("terms.analyze", cfg=Param("str"))
def analyze(cfg):
    """Microstates, (M_L, M_S) table, terms, J values and Hund ground term of a configuration (or an error code)."""
    return terms.analyze(cfg)


@endpoint("terms.element", Z=Param("int", check=lambda v: 1 <= v <= 36, doc="1..36"))
def element(Z):
    """Ground configuration and ground term of element Z (H-Kr)."""
    return terms.element(Z)

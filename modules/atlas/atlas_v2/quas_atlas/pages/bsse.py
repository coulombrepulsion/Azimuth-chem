"""Endpoints of the page "Basis set superposition error" (web/<lang>/bsse.html); model: core.bsse."""
from ..api import Param, endpoint
from ..core import bsse


@endpoint("bsse.bars", m=Param("str", check=lambda v: v in bsse.METH))
def bars(m):
    """Raw and counterpoise-corrected interaction energies of (H2O)2 per basis set, BSSE, CBS reference."""
    return bsse.bars(m)


@endpoint("bsse.bases")
def bases():
    """Basis sets with MP2 scans of R(O...O)."""
    return list(bsse.D["scan"])


@endpoint("bsse.scan", b=Param("str", check=lambda v: v in bsse.D["scan"]))
def scan(b):
    """MP2 binding curves (raw, counterpoise, aug-cc-pVTZ reference) and their interpolated minima."""
    return bsse.scan(b)

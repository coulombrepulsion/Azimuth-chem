"""Endpoints of the page "Intermolecular interactions" (web/<lang>/dispersion.html); model: core.dispersion."""
from ..api import Param, endpoint
from ..core import dispersion


@endpoint("disp.sys", sys=Param("str", check=lambda v: v in dispersion.SYS))
def system(sys):  # noqa: A002 (page parameter name)
    """Interaction curves (HF, MP2; raw and counterpoise) in display units, table rows, minima and reference."""
    return dispersion.system(sys)


@endpoint("disp.r6")
def r6():
    """Correlation part of the He2 interaction, the C6/R^6 line, slope and effective C6."""
    return dispersion.r6()

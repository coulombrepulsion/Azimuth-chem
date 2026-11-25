"""Endpoints of the page "Equilibrium: from energy to constant" (web/<lang>/equilibrium.html);
model: core.equilibrium."""
import math

from ..api import Param, endpoint
from ..core import equilibrium as eq

_rx = Param("int", check=lambda v: 0 <= v < len(eq.RX))
_T = Param("float", check=lambda v: 1 <= v <= 1e5)


@endpoint("eq.reactions")
def reactions():
    """Stoichiometry of the page's reactions ([species, coefficient] lists)."""
    return eq.RX


@endpoint("eq.state", rx=_rx, T=_T)
def state(rx, T):
    """dE_el, dZPE, dH°(0), thermal correction, dH°, dS°, dG°, K at T; tabulated dG°(298)."""
    return eq.state(rx, T)


@endpoint("eq.sens", d=Param("float", check=lambda v: abs(v) <= 1000), T=_T)
def sens(d, T):
    """Factor by which an error d (kJ/mol) in dG° changes K; RT ln 10."""
    return eq.sens(d, T)


@endpoint("eq.chart", rx=_rx)
def chart(rx):
    """dG°, dH°, -TdS°, lg K for T = 200..1500 K and the temperature where dG° changes sign."""
    return eq.chart(rx)


@endpoint("eq.example")
def example():
    """Model electronic energies and G corrections reproducing dH°(298) of NH3 synthesis."""
    return eq.example()


def _rows_ok(v):
    return 2 <= len(v) <= 50 and all(isinstance(r, list) and len(r) == 3 and all(
        isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in r) and r[0] != 0 for r in v)


@endpoint("eq.custom", T=Param("float", check=lambda v: v > 0), rows=Param("list", check=_rows_ok, doc="[coefficient, E, G_corr] rows"))
def custom(T, rows):
    """dE, dG° and K of a reaction from quantum-chemical energies (hartree)."""
    return eq.custom(T, [[float(x) for x in r] for r in rows])

"""Endpoints of the page "Born-Oppenheimer and vibrations" (web/<lang>/bo.html); model: core.bo."""
from ..api import Param, endpoint
from ..core import bo


@endpoint("bo.state", mu=Param("float", check=lambda v: 1 <= v <= 1e5, doc="1 <= mu <= 1e5 electron masses"),
          pot=Param("str", check=lambda v: v in ("morse", "harm", "both")),
          v=Param("int", 0, check=lambda v: 0 <= v <= 10000))
def state(mu, pot, v):
    """Levels, turning points, potentials, wavefunction and time scales."""
    return bo.state(mu, pot, v)

"""Endpoints of the page "Atomic charges" (web/<lang>/charges.html); model: core.charges."""
from ..api import Param, endpoint
from ..core import charges


@endpoint("charges.meta")
def meta():
    """Molecules (atom labels, unique elements, presence of H) and basis sets."""
    return charges.meta()


@endpoint("charges.view", m=Param("int", check=lambda v: 0 <= v < len(charges.D)), b=Param("str", check=lambda v: v in charges.B))
def view(m, b):
    """RHF energy, charges of the three schemes, density and point-charge dipoles, experiment."""
    return charges.view(m, b)


@endpoint("charges.series", m=Param("int", check=lambda v: 0 <= v < len(charges.D)), i=Param("int", check=lambda v: 0 <= v < 20))
def series(m, i):
    """Charge of atom i in the four basis sets for each scheme."""
    if i >= len(charges.D[m]["at"]):
        raise ValueError("i out of range")
    return charges.series(m, i)

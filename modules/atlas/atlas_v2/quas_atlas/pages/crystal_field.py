"""Endpoints of the page "Crystal and ligand field" (web/<lang>/crystal-field.html); model: core.crystal_field."""
from ..api import Param, endpoint
from ..core import crystal_field as cf


@endpoint("cf.state", geo=Param("str", check=lambda v: v in cf.GEO), t=Param("float", check=lambda v: 0 <= v <= 2),
          lig=Param("int", check=lambda v: 0 <= v < len(cf.LIG)), nd=Param("int", check=lambda v: 1 <= v <= 10),
          P=Param("float", check=lambda v: 0 <= v <= 100000))
def state(geo, t, lig, nd, P):
    """AOM d levels, ground-state filling, Delta_o, moments, LFSE, spin crossover lines and the Jahn-Teller curve."""
    return cf.state(geo, t, lig, nd, P)


@endpoint("cf.cx")
def cx():
    """Octahedral complexes of the quiz with d count, spin state, t2g/eg filling, unpaired electrons and LFSE."""
    return cf.cx()

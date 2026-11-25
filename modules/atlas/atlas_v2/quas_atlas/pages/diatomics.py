"""Endpoints of the page "MO diagrams of diatomics" (web/<lang>/diatomics.html); model: core.diatomics."""
from ..api import Param, endpoint
from ..core import diatomics

_el = Param("str", check=lambda v: v in diatomics.ELS)


@endpoint("dia.spec")
def spec():
    """Species of the property table: experimental R_e and D_0 with the model bond order and unpaired electrons."""
    return diatomics.spec()


@endpoint("dia.build", A=_el, B=_el, Q=Param("int", check=lambda v: -2 <= v <= 2), mix=Param("bool"))
def build(A, B, Q, mix):
    """MO energies, coefficients, names, occupations, bond order, unpaired electrons and ground term of A-B^Q."""
    return diatomics.build(A, B, Q, mix)

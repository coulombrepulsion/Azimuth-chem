"""Endpoints of the page on properties as derivatives of the energy (derivatives.html); model: core.derivs."""
from ..api import Param, endpoint
from ..core import derivs


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("der.steps", digits=Param("int", check=lambda v: 3 <= v <= 14))
def steps(digits):
    """The errors of the forward, central and second differences of a Morse curve against the step."""
    return derivs.steps(digits)


@endpoint("der.field", lgF=_rng(-5, -1), lgdE=_rng(-12, -4))
def field(lgF, lgdE):
    """The finite-field dipole and polarizability of a model water molecule against the field."""
    return derivs.field(lgF, lgdE)


@endpoint("der.twolevel", mu01=_rng(0.05, 3), dE=_rng(0.05, 2))
def twolevel(mu01, dE):
    """The polarizability of two levels and that of water in the bases of the lecture."""
    return derivs.twolevel(mu01, dE)

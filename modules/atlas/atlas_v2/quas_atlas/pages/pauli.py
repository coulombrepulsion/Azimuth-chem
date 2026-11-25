"""Endpoints of the page "Pauli principle and the exchange hole" (web/<lang>/pauli.html); model: core.pauli."""
from ..api import Param, endpoint
from ..core import pauli

_mode = Param("str", check=lambda v: v in pauli.MODES)
_orb = Param("int", check=lambda v: 1 <= v <= 4)
_x1 = Param("float", check=lambda v: 0 <= v <= 1)


@endpoint("pauli.map", mode=_mode, a=_orb, b=_orb, view=Param("str", check=lambda v: v in ("P", "W")))
def map_(mode, a, b, view):
    """|psi(x1, x2)|^2 or psi on the 120 x 120 map (float64, base64) and its maximum modulus."""
    return pauli.grid_map(mode, a, b, view)


@endpoint("pauli.cond", mode=_mode, a=_orb, b=_orb, ms=Param("int", check=lambda v: v in (-1, 0, 1)), x1=_x1)
def cond(mode, a, b, ms, x1):
    """Conditional density of electron 2, reference density, hole and its integral (null if psi = 0)."""
    return pauli.conditional(mode, a, b, ms, x1)


@endpoint("pauli.orbs", a=_orb, b=_orb)
def orbs(a, b):
    """phi_a and phi_b on the 301-point grid."""
    return pauli.orbs(a, b)


@endpoint("pauli.energy", a=_orb, b=_orb)
def energy(a, b):
    """Coulomb and exchange integrals J_ab, K_ab and the interaction energies of the five states."""
    return pauli.energy(a, b)


@endpoint("pauli.cimap", th=Param("float", check=lambda v: -90 <= v <= 90))
def cimap(th):
    """|psi_CI|^2 of cos(th) phi1^2 + sin(th) phi2^2 on the 110 x 110 map."""
    return pauli.ci_map(th)


@endpoint("pauli.ci", th=Param("float", check=lambda v: -90 <= v <= 90), lam=Param("float", check=lambda v: 0 <= v <= 20), x1=_x1)
def ci(th, lam, x1):
    """Coulomb hole of the 2x2 CI: conditional density, hole depth, E(theta), minimum."""
    return pauli.ci(th, lam, x1)

"""Endpoints of the page on the bond through orbitals (bonding.html); model: core.bonding."""
from ..api import Param, endpoint
from ..core import bonding


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("bond.rotate", theta=_rng(-90, 90))
def rotate(theta):
    """Two canonical orbitals rotated by θ: the orbitals, the unchanged density, the Boys spread."""
    return bonding.rotate(theta)


@endpoint("bond.hybrid", angle=_rng(90.5, 180), nb=Param("int", check=lambda v: v in (2, 3)))
def hybrid(angle, nb):
    """The s character of bond hybrids and lone pairs from the bond angle."""
    return bonding.hybrid(angle, nb)


@endpoint("bond.e2", F=_rng(0, 0.3), gap=_rng(0.1, 2), n=_rng(1, 2))
def e2(F, gap, n):
    """The NBO donor–acceptor energy E(2) and the exact 2 × 2 lowering."""
    return bonding.e2(F, gap, n)


@endpoint("bond.nci", kind=Param("str", check=lambda v: v in ("one", "dimer", "ring")), d=_rng(2.5, 7))
def nci(kind, d):
    """The NCI points (sign(λ2)ρ, s) of one fragment, a dimer or a ring."""
    return bonding.nci(kind, d)

"""Endpoints of the page "Slater-Condon rules" (web/<lang>/slater.html); model: core.slater."""
from ..api import Param, endpoint
from ..core import slater


def _det_ok(v):
    return len(v) <= 8 and all(isinstance(x, list) and len(x) == 2 and isinstance(x[0], int) and not isinstance(x[0], bool)
                               and 1 <= x[0] <= 8 and x[1] in ("α", "β") for x in v) and len({tuple(x) for x in v}) == len(v)


_D = Param("list", check=_det_ok, doc="determinant: up to 8 distinct [orbital 1..8, 'α'|'β']")


@endpoint("slater.element", A=_D, B=_D)
def element(A, B):
    """<A|H|B> in spatial integrals: alignment, permutation sign, differing spin-orbitals, spin notes."""
    return slater.element(A, B)

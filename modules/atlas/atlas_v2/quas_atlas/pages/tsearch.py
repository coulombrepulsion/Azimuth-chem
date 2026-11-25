"""Endpoints of the page on the search for a transition state and the reaction path (tsneb.html); model: core.tsearch."""
from ..api import Param, endpoint
from ..core import tsearch


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("ts.follow", x0=_rng(-1.6, 1.6), y0=_rng(-1.2, 1.2), mode=Param("str", check=lambda v: v in ("x", "y")),
          radius=_rng(0.05, 1))
def follow(x0, y0, mode, radius):
    """Eigenvector following and plain Newton on (x² − 1)² + y², the IRC from the saddle found."""
    return tsearch.follow(x0, y0, mode, radius)


@endpoint("ts.neb", n=Param("int", check=lambda v: 3 <= v <= 21), k=_rng(1, 1000),
          kind=Param("str", check=lambda v: v in ("plain", "neb", "ci")))
def neb(n, k, kind):
    """A band of n images on the Müller–Brown surface: plain springs, NEB or CI-NEB."""
    return tsearch.neb(n, k, kind)


@endpoint("ts.scan", coord=Param("str", check=lambda v: v in ("x", "y")))
def scan(coord):
    """A relaxed scan of x or y on the Müller–Brown surface, forward and backward."""
    return tsearch.scan(coord)

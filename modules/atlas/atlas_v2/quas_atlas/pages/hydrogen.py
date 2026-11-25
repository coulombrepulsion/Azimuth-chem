"""Endpoints of the page "Hydrogen atom and atomic orbitals" (web/<lang>/hydrogen.html); model: core.hydrogen."""
from ..api import Param, endpoint
from ..core import hydrogen as h

_n = Param("int", check=lambda v: 1 <= v <= 4)
_k = Param("int", check=lambda v: 0 <= v < len(h.ORB), doc="index into the orbital list")
_Z = Param("int", check=lambda v: v in (1, 2, 3))


def _ok(n, k):
    if h.ORB[k][1] >= n:
        raise ValueError("l must be smaller than n")


@endpoint("h.map", n=_n, oi=_k, Z=_Z, plane=Param("str", check=lambda v: v in ("xz", "xy", "yz")),
          W=Param("int", check=lambda v: 2 <= v <= 1000), H=Param("int", check=lambda v: 2 <= v <= 1000))
def map_(n, oi, Z, plane, W, H):
    """psi on the pixel grid of a plane through the nucleus (float32, base64) and its maximum."""
    _ok(n, oi)
    return h.map_grid(n, oi, Z, plane, W, H)


@endpoint("h.radial", n=_n, oi=_k, Z=_Z)
def radial(n, oi, Z):
    """R(r), r^2 R^2, radial nodes, <r>, most probable r, energy."""
    _ok(n, oi)
    return h.radial(n, oi, Z)


@endpoint("h.cloud", n=_n, oi=_k, Z=_Z, seed=Param("int", check=lambda v: 0 <= v < 2 ** 32))
def cloud(n, oi, Z, seed):
    """5000 points sampled from |psi|^2 (rejection sampling) with the sign of psi."""
    _ok(n, oi)
    return h.cloud(n, oi, Z, seed)


@endpoint("h.levels", Z=_Z, series=Param("int", check=lambda v: v in (1, 2, 3)))
def levels(Z, series):
    """Energy levels and the first six lines and the limit of a spectral series."""
    return h.levels(Z, series)


@endpoint("h.quiz", n=_n, k=_k)
def quiz(n, k):
    """Radial and angular node counts and the energy (eV) of orbital nk of hydrogen."""
    _ok(n, k)
    return h.quiz(n, k)

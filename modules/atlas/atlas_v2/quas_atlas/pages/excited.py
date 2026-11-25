"""Endpoints of the page "Excited states and spectra" (web/<lang>/excited.html); model: core.excited."""
import math

from ..api import Param, endpoint
from ..core import excited


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("exc.state", S=_rng(0, 10), w=_rng(50, 5000), E00=_rng(0.5, 10), fw=_rng(10, 5000))
def state(S, w, E00, fw):
    """Franck-Condon progression: potentials, vibronic absorption/emission envelopes, key energies.
    w and fw in cm^-1, E00 in eV."""
    return excited.state(S, w, E00, fw)


@endpoint("exc.jab", E1=_rng(0.1, 10), K=_rng(0, 5))
def jab(E1, K):
    """T1 below S1 by twice the exchange integral."""
    return excited.jab(E1, K)


def _rows_ok(v):
    return 0 < len(v) <= 500 and all(isinstance(r, list) and 2 <= len(r) <= 10 and all(
        isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x) for x in r) for r in v)


@endpoint("exc.spectrum", rows=Param("list", check=_rows_ok, doc="rows [E, f, ...] of finite numbers"),
          unit=Param("str", check=lambda v: v in ("eV", "nm")), fw=Param("float", check=lambda v: v > 0))
def spectrum(rows, unit, fw):
    """Gaussian-broadened absorption spectrum from (energy, oscillator strength) pairs."""
    return excited.spectrum(rows, unit, fw)

"""Endpoints of the page "Solvent models" (web/<lang>/solvation.html); model: core.solvation."""
from ..api import Param, endpoint
from ..core import solvation


@endpoint("solv.born", eps=Param("float", check=lambda v: 1 <= v <= 1000, doc="1..1000"),
          dp=Param("float", check=lambda v: 0 <= v <= 5), dm=Param("float", check=lambda v: 0 <= v <= 5))
def born(eps, dp, dm):
    """Born hydration free energies of nine ions with enlarged radii, and their mean abs. error."""
    return solvation.born(eps, dp, dm)


@endpoint("solv.pcm")
def pcm():
    """C-PCM vs experimental solvation free energies of eleven molecules."""
    return solvation.pcm()


@endpoint("solv.eps", i=Param("int", check=lambda v: v in (0, 1)))
def eps(i):
    """C-PCM solvation energy vs permittivity and the (eps-1)/eps reference curve."""
    return solvation.eps_curve(i)

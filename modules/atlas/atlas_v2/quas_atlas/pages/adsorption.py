"""Endpoints of the page on adsorption and magnetism (adsorption.html); model: core.adsorption."""
from ..api import Param, endpoint
from ..core import adsorption


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("ads.chem", ea=_rng(-6, 2), ed=_rng(-5, 1), W=_rng(1, 10), V=_rng(0, 4))
def chem(ea, ed, W, V):
    """The adsorbate level on a d band: its projected DOS, the bond energy; the same adsorbate on Ni…Ag."""
    out = adsorption.chemisorption(ea, ed, W, V)
    out["trend"] = adsorption.trend(ea, V)["metals"]
    return out


@endpoint("ads.stoner", n=_rng(0, 10), W=_rng(1, 12), I=_rng(0, 2))
def stoner(n, W, I):
    """E(m) of the Stoner model, the moment, N(E_F) and I·N(E_F)."""
    return adsorption.stoner(n, W, I)


@endpoint("ads.hubbard", U=_rng(0, 20), Ueff=_rng(0, 10))
def hubbard(U, Ueff):
    """The Hubbard dimer (t = 1) against U; the DFT+U penalty and potential for U_eff (eV)."""
    out = adsorption.hubbard(U)
    out["plus_u"] = adsorption.plus_u(Ueff)
    return out

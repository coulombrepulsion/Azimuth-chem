"""Endpoints of the page on defects and surfaces (defects.html); model: core.defects."""
from ..api import Param, endpoint
from ..core import defects


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


@endpoint("def.vacancy", ef=_rng(0.5, 6), T=_rng(200, 2500))
def vacancy(ef, T):
    """The equilibrium share of vacancies e^{−E_f/kT} (Si sites), its curve against T, the factor of ±0.3 eV."""
    return defects.vacancy(ef, T)


@endpoint("def.charged", ep=_rng(-1, 8), e0=_rng(-1, 8), em=_rng(-1, 8), gap=_rng(0.3, 5), q=_rng(1, 3), eps=_rng(1, 60))
def charged(ep, e0, em, gap, q, eps):
    """The formation energies of the charges +, 0, − against the Fermi level, the transition levels; the correction
    of a charged supercell (Makov–Payne) for the charge q and the permittivity ε."""
    out = defects.charged(ep, e0, em, gap)
    out["supercell"] = defects.supercell(round(q), eps)["rows"]
    return out


@endpoint("def.slab", face=Param("str", check=lambda v: v in defects.FACES), delta=_rng(-50, 50), noise=_rng(0, 20))
def slab(face, delta, noise):
    """Si slabs of 2…16 layers: γ from a separate bulk energy off by delta meV, and from the line through the slabs."""
    return defects.slab(face, delta, noise)

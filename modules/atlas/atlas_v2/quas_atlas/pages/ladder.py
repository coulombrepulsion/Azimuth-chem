"""Endpoints of the page "Method hierarchy and Jacob's ladder" (web/<lang>/ladder.html); model: core.ladder."""
from ..api import Param, endpoint
from ..core import ladder as L


@endpoint("lad.meta")
def meta():
    """Molecules with FCI scans (and their number of points), molecules and methods of the atomisation set."""
    return {"fciMols": list(L.D["fci"]), "nk": {m: len(v) for m, v in L.D["fci"].items()}, "taeMols": L.D["tae"]["mols"],
            "maeKeys": list(L.D["tae"]["mae"])}


@endpoint("lad.fci", mol=Param("str", check=lambda v: v in L.D["fci"]))
def fci(mol):
    """Errors relative to FCI (mEh) and recovered correlation along the bond stretch."""
    return L.fci(mol)


@endpoint("lad.cost", f=Param("int", check=lambda v: 1 <= v <= 20))
def cost(f):
    """Cost growth factors f^p and FCI determinant counts."""
    return L.cost(f)


@endpoint("lad.times")
def times():
    """Measured timings on log-log axes and fitted exponents."""
    return L.times()


@endpoint("lad.tae")
def tae():
    """Atomisation energies by method, errors vs CCSD(T)/CBS, mean absolute errors."""
    return L.tae()

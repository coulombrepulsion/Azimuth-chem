"""Endpoints of the pages "Hueckel method" (web/<lang>/huckel.html) and "pi orbitals and pericyclic
reactions" (web/<lang>/wh.html); model: core.huckel."""
from ..api import Param, endpoint
from ..core import huckel


def _types(v):
    return isinstance(v, list) and 2 <= len(v) <= 20 and all(t in huckel.HT for t in v)


def _bonds(v):
    return isinstance(v, list) and len(v) <= 60 and all(
        isinstance(b, list) and len(b) == 2 and all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < 20 for i in b)
        and b[0] != b[1] for b in v)


@endpoint("huckel.solve", types=Param("list", check=_types), bonds=Param("list", check=_bonds),
          charge=Param("int", check=lambda v: -2 <= v <= 2))
def solve(types, bonds, charge):
    """Hueckel MOs, occupations, charges, bond orders, free valence, DE, reactivity sites and the secular polynomial."""
    n = len(types)
    if any(i >= n or j >= n for i, j in bonds):
        raise ValueError("bond index out of range")
    return huckel.page(types, bonds, charge)


@endpoint("wh.hk", sys=Param("str", check=lambda v: v in huckel.HK))
def hk(sys):  # noqa: A002
    """Hueckel pi orbitals of the six example systems of section 1."""
    return huckel.hk(sys)


@endpoint("wh.electro", sys=Param("str", check=lambda v: v in huckel.SYS), photo=Param("bool"))
def electro(sys, photo):  # noqa: A002
    """Frontier orbital of an electrocyclic closure and the allowed rotation mode."""
    return huckel.electro(*huckel.SYS[sys], photo)


@endpoint("wh.correl", sys=Param("str", check=lambda v: v in huckel.SYS), mode=Param("str", check=lambda v: v in ("con", "dis")))
def correl(sys, mode):  # noqa: A002
    """Orbital correlation diagram reactant -> product for the C2 (con) or mirror (dis) symmetry."""
    return huckel.correl(*huckel.SYS[sys], mode)


@endpoint("wh.cyclo", A=Param("str", check=lambda v: v in ("eth", "buta", "hexa")), B=Param("str", check=lambda v: v in ("eth", "acro", "buta")),
          photo=Param("bool"), pair=Param("str", None, check=lambda v: v is None or v in ("HL", "LH", "LL", "HH")))
def cyclo(A, B, photo, pair):
    """Frontier-orbital overlap of a supra-supra cycloaddition A + B, thermal or with A excited."""
    return huckel.cyclo(A, B, photo, pair)

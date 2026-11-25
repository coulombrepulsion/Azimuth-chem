"""Endpoints of the page "Thermochemistry from frequencies" (web/<lang>/thermochemistry.html);
model: core.thermochemistry."""
import math

from ..api import Param, endpoint
from ..core import thermochemistry as tc


def _num(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _mol_ok(v):
    if isinstance(v, int) and not isinstance(v, bool):
        return 0 <= v < len(tc.MOL)
    return (isinstance(v, dict) and _num(v.get("m")) and v["m"] > 0 and isinstance(v.get("lin"), bool)
            and isinstance(v.get("B"), list) and len(v["B"]) == (1 if v["lin"] else 3)
            and all(_num(b) and b > 0 for b in v["B"]) and _num(v.get("sig")) and v["sig"] >= 1
            and _num(v.get("g")) and v["g"] >= 1 and isinstance(v.get("nu"), list) and len(v["nu"]) <= 600
            and all(_num(x) and x > 0 for x in v["nu"]))


def _mol(v):
    if isinstance(v, int):
        return tc.MOL[v]
    return {"m": float(v["m"]), "lin": v["lin"], "B": [float(b) for b in v["B"]], "sig": v["sig"], "g": v["g"],
            "nu": [float(x) for x in v["nu"]], "S": None}


_M = Param("any", check=_mol_ok, doc="index into therm.mols or {m, lin, B, sig, g, nu}")
_p = Param("float", check=lambda v: 0 < v <= 1e9)


@endpoint("therm.mols")
def mols():
    """The page's molecules: masses, rotational constants, symmetry numbers, frequencies, S°(NIST-JANAF)."""
    return tc.MOL


@endpoint("therm.state", mol=_M, T=Param("float", check=lambda v: 1 <= v <= 1e5), p=_p)
def state(mol, T, p):
    """Translational/rotational/vibrational/electronic S, H, Cp; ZPE, H_corr, G_corr; comparison with JANAF."""
    return tc.state(_mol(mol), T, p)


@endpoint("therm.chart", mol=_M, p=_p)
def chart(mol, p):
    """All contributions for T = 50..2000 K."""
    return tc.chart(_mol(mol), p)


def _nums(v, n=600):
    return isinstance(v, list) and len(v) <= n and all(_num(x) for x in v)


@endpoint("therm.custom", m=Param("float", check=lambda v: v > 0), B=Param("list", check=lambda v: len(v) in (1, 3) and _nums(v) and all(x > 0 for x in v)),
          Bu=Param("str", check=lambda v: v in ("cm", "GHz", "MHz")), sig=Param("int", check=lambda v: v >= 1),
          g=Param("int", check=lambda v: v >= 1), sc=Param("float", check=lambda v: v > 0),
          nu=Param("list", check=_nums), low=Param("bool"))
def custom(m, B, Bu, sig, g, sc, nu, low):
    """Own molecule from user input: B converted to cm^-1, frequencies scaled and filtered."""
    return tc.custom(m, [float(x) for x in B], Bu, sig, g, sc, [float(x) for x in nu], low)

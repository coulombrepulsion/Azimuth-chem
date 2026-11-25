"""Endpoints of the page "Molecular symmetry" (web/<lang>/symmetry.html); models: core.symmetry,
core.symvib, core.symfind.

The page keeps its molecule models (geometry of the GROUPS list and the
molecule library) as content and sends them here; every group-theoretical
result -- the group, classes and their labels, the character table binding,
orbital symmetry, Gamma counts, normal modes, the correlation of classes on
descent, the multiplication table and the point group of a user molecule --
is computed by the server.
"""
from __future__ import annotations

import json
import math
from collections import OrderedDict

from ..api import Param, endpoint
from ..core import symfind, symmetry as sy, symvib

MAX_ATOMS = 400


def _finite(x) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def _atoms_ok(v) -> bool:
    return isinstance(v, list) and 0 < len(v) <= MAX_ATOMS and all(
        isinstance(a, dict) and set(a) == {"t", "p"} and isinstance(a["t"], str) and 0 < len(a["t"]) <= 3
        and isinstance(a["p"], list) and len(a["p"]) == 3 and all(_finite(x) and abs(x) < 1e4 for x in a["p"])
        for a in v)


def _bonds_ok(v) -> bool:
    return isinstance(v, list) and len(v) <= 4 * MAX_ATOMS and all(
        isinstance(b, list) and len(b) == 2 and all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < MAX_ATOMS
                                                     for i in b) for b in v)


def _gens_ok(v) -> bool:
    return isinstance(v, list) and len(v) <= 4 and all(
        isinstance(M, list) and len(M) == 3 and all(isinstance(r, list) and len(r) == 3 and all(_finite(x) and abs(x) <= 1.000001
                                                                                                 for x in r) for r in M)
        for M in v)


_gens = Param("list", check=_gens_ok, doc="up to 4 orthogonal 3x3 matrices")
_atoms = Param("list", check=_atoms_ok, doc=f"1..{MAX_ATOMS} atoms {{t, p:[x,y,z]}}")
_bonds = Param("list", check=_bonds_ok, doc="pairs of atom indices")


def _floats(atoms):
    return [{"t": a["t"], "p": [float(x) for x in a["p"]]} for a in atoms]


def _mat(M):
    return [[float(x) for x in r] for r in M]


# ------------------------------------------------ parent group (memoised)
_CACHE: "OrderedDict[str, dict]" = OrderedDict()


def _parent(gens, atoms) -> dict:
    """closure -> stabiliser of the model -> labelled classes; memoised (16 entries)."""
    k = json.dumps([gens, atoms])
    hit = _CACHE.get(k)
    if hit is not None:
        _CACHE.move_to_end(k)
        return hit
    full = sy.stabilizer(sy.closure(gens), atoms)
    res = {"full": full, "P": sy.classes_for(full, atoms)}
    _CACHE[k] = res
    if len(_CACHE) > 16:
        _CACHE.popitem(last=False)
    return res


def _ser_l(L) -> dict:
    """Classes for the page: matrices are referenced by index into the group list."""
    out = []
    for c in L["cls"]:
        d = {k: c[k] for k in ("kind", "base", "label", "full", "n", "idx") if k in c}
        for k in ("tag", "note", "k", "onPa", "lin", "f", "rep"):
            if c.get(k) is not None:
                d[k] = c[k]
        out.append(d)
    gid = {k: v for k, v in L["id"].items() if v is not None}
    return {"id": gid, "cls": out}


def _same_atoms(a, b) -> bool:
    return len(a) == len(b) and all(x["t"] == y["t"] and x["p"] == y["p"] for x, y in zip(a, b))


def _state(gens, atoms, model) -> tuple:
    par = _parent(gens, atoms)
    full = par["full"]
    H = full if _same_atoms(model, atoms) else sy.stabilizer(full, model)
    L = par["P"] if H is full else sy.classes_for(H, model)
    return par, H, L


@endpoint("sym.group", gens=_gens, atoms=_atoms,
          descents=Param("list", check=lambda v: len(v) <= 16 and all(_atoms_ok(m) for m in v)))
def group(gens, atoms, descents):
    """Operations and labelled classes of a model; the group reached by each of its descents."""
    gens, atoms = [_mat(M) for M in gens], _floats(atoms)
    par = _parent(gens, atoms)
    full = par["full"]
    names = []
    for m in descents:
        m = _floats(m)
        H = sy.stabilizer(full, m)
        names.append(sy.classes_for(H, m)["id"]["name"])
    return {"full": full, "parent": _ser_l(par["P"]), "descNames": names}


@endpoint("sym.state", gens=_gens, atoms=_atoms, model=_atoms)
def state(gens, atoms, model):
    """Everything the tabs show for the (possibly distorted) model: group, classes, character
    table binding, orbital symmetry, Gamma counts, multiplication table, class correlation."""
    gens, atoms, model = [_mat(M) for M in gens], _floats(atoms), _floats(model)
    if len(model) != len(atoms):
        raise ValueError("model and base model must have the same atoms")
    par, H, L = _state(gens, atoms, model)
    lin = bool(L["id"].get("lin"))
    ct = None if lin else sy.CT.get(L["id"]["name"])
    B = sy.bind_ct(H, L, ct) if ct else None
    out = {"H": H, "L": _ser_l(L), "corr": sy.correlation(par["P"], L)}
    if B:
        out["B"] = {"Q": B["Q"], "opCol": B["opCol"], "colCls": B["colCls"], "ct": ct}
        out["orb"] = sy.orb_irreps(H, B)
        out["gamma"] = sy.gamma_all(H, model, B)
    if not lin:
        ops = sy.op_list(H, L)
        out["ops"] = ops
        out["mul"] = sy.mult_table(H, ops)
    return out


@endpoint("sym.vib", gens=_gens, atoms=_atoms, model=_atoms, bonds=_bonds)
def vib(gens, atoms, model, bonds):
    """Normal modes of the model in the page's force field, grouped into degenerate sets with
    their symmetry species and IR / Raman activity."""
    gens, atoms, model = [_mat(M) for M in gens], _floats(atoms), _floats(model)
    if len(model) != len(atoms) or any(i >= len(model) for b in bonds for i in b):
        raise ValueError("inconsistent model")
    _, H, L = _state(gens, atoms, model)
    lin = bool(L["id"].get("lin"))
    ct = None if lin else sy.CT.get(L["id"]["name"])
    B = sy.bind_ct(H, L, ct) if ct else None
    if not B and not lin:
        return None
    v = symvib.vib_sets(model, bonds, H, B, lin)
    ga = sy.gamma_all(H, model, B) if B else None
    sets = []
    for x in v["sets"]:
        if lin:
            r = symvib.vib_lin_label(x["set"], model, L["id"]["name"] == "D∞h")
        else:
            j = next(i for i, c in enumerate(x["n"]) if c > 0)
            r = {"lab": ct["irreps"][j]["lab"], "ir": ga["ir"][j], "ra": ga["ra"][j]}
        sets.append({"lab": r["lab"], "ir": r["ir"], "ra": r["ra"], "acc": bool(x.get("acc")),
                     "set": [{"u": m["u"]} for m in x["set"]]})
    return {"sets": sets}


@endpoint("sym.analyze", tol=Param("float", check=lambda v: 0.001 <= v <= 1, doc="0.001..1 angstrom"),
          atoms=Param("list", None, check=lambda v: v is None or _atoms_ok(v)),
          xyz=Param("text", None), sdf=Param("text", None))
def analyze(tol, atoms, xyz, sdf):
    """Point group of a molecule (library atoms, XYZ text or PubChem SDF text), its standard
    orientation, symmetrised and scaled coordinates and bonds; or an error code."""
    given = [x is not None for x in (atoms, xyz, sdf)]
    if sum(given) != 1:
        raise ValueError("exactly one of atoms, xyz, sdf expected")
    if atoms is not None:
        raw = _floats(atoms)
    else:
        r = symfind.parse_xyz(xyz) if xyz is not None else symfind.parse_sdf(sdf)
        if "err" in r:
            return r
        raw = r["atoms"]
    r = symfind.analyze_molecule(raw, tol)
    if "err" not in r:
        r["n"] = len(raw)
    return r

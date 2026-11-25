"""Endpoints of the page "Atoms in molecules" (web/<lang>/aim.html); model: core.aim."""
from ..api import Param, endpoint
from ..core import aim

_k = Param("str", check=lambda v: v in aim.PL, doc="molecule key of the page")
_b = Param("str", check=lambda v: v in aim.BASES, doc="STO-3G, 6-31G, 6-31G*, 6-31G**")


@endpoint("aim.meta")
def meta():
    """Molecules (angstrom), map planes and the elements each basis covers."""
    return aim.meta()


@endpoint("aim.stage", k=_k, b=_b, stage=Param("str", check=lambda v: v in aim.STAGES, doc="scf, map, vol, esp, bader"))
def stage(k, b, stage):
    """One stage of the calculation (RHF + critical points, map, volume grids, ESP surface, Bader charges); cached."""
    return aim.encode(aim.stage(k, b, stage))


@endpoint("aim.mo", k=_k, b=_b, kmo=Param("int", check=lambda v: 0 <= v < 200))
def mo(k, b, kmo):
    """Molecular orbital kmo on the volume grid of the 'vol' stage (float32, base64)."""
    return aim.b64_f32(aim.mo(k, b, kmo))


@endpoint("aim.prof", k=_k, b=_b, ia=Param("int", check=lambda v: 0 <= v < 50), ib=Param("int", check=lambda v: 0 <= v < 50))
def prof(k, b, ia, ib):
    """Density and its Laplacian along the line from nucleus ia through nucleus ib (421 points)."""
    return aim.prof(k, b, ia, ib)

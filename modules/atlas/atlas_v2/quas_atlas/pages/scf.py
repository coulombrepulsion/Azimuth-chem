"""Endpoints of the page "SCF" (web/<lang>/scf.html); model: core.scf."""
from ..api import Param, endpoint
from ..core import scf

_mol = Param("str", check=lambda v: v in scf.MOLS, doc="HeH or H2")
_R = Param("float", check=lambda v: 0.3 <= v <= 40, doc="0.3 <= R <= 40 bohr")
_z = Param("float", check=lambda v: 0.1 < v <= 10, doc="0.1 < zeta <= 10")


@endpoint("scf.run", mol=_mol, R=_R, za=_z, zb=_z,
          guess=Param("str", "core", check=lambda v: v in ("core", "A", "B")),
          damp=Param("float", 0.0, check=lambda v: 0 <= v <= 0.99, doc="0 <= damp <= 0.99"),
          diis=Param("bool", False))
def run(mol, R, za, zb, guess, damp, diis):
    """Every SCF cycle (matrices, energies, charges, orbitals on the axis)."""
    return scf.trajectory(mol, R, za, zb, guess, damp, diis)


@endpoint("scf.scan", mol=_mol, za=_z, zb=_z)
def scan(mol, za, zb):
    """RHF/UHF potential curves, <S^2>, limit R -> infinity, R_e."""
    return scf.scan(mol, za, zb)


@endpoint("scf.zeta", mol=_mol, R=_R, za=_z, zb=_z,
          who=Param("list", check=lambda v: 0 < len(v) <= 2 and all(i in (0, 1) for i in v)))
def zeta(mol, R, za, zb, who):
    """E_RHF versus the Slater exponent and its minimum."""
    return scf.zeta_curve(mol, R, za, zb, tuple(who))


@endpoint("scf.pop", mol=_mol, R=_R, za=_z, zb=_z)
def pop(mol, R, za, zb):
    """Mulliken / Loewdin / Mayer analysis at R and along R."""
    return scf.populations(mol, R, za, zb)

"""Endpoints of the page "Normal vibrations" (web/<lang>/vibrations.html); model: core.vibrations."""
from ..api import Param, endpoint
from ..core import vibrations


@endpoint("vib.list")
def mol_list():
    """Molecules of the page: id, formula, point group, linearity."""
    return vibrations.mol_list()


@endpoint("vib.mol", m=Param("int", check=lambda v: 0 <= v < len(vibrations.MOLS)))
def mol(m):
    """Normal modes (species, degeneracy, displacements, IR/Raman activity), Gamma_3N reduction and quiz answers."""
    return vibrations.mol(m)

"""Endpoints added on 2026-10-25 for the lectures of the first course: SALCs (symmetry.html), Koopmans' theorem
(scf.html), Walsh diagrams (walsh.html), global reactivity indices and Fukui functions, semi-empirical levels
(huckel.html); models: core.salc, core.koopmans, core.walsh, core.reactivity, core.semiemp."""
from ..api import Param, endpoint
from ..core import huckel, koopmans, reactivity, salc, scf, semiemp, walsh


@endpoint("sym.salc", key=Param("str", check=lambda v: v in salc.MOLECULES))
def salc_(key):
    """Reducible representation of the ligand σ orbitals, the reduction formula and the SALCs."""
    return salc.salc(key)


@endpoint("scf.koopmans", mol=Param("str", check=lambda v: v in scf.MOLS), R=Param("float", check=lambda v: 0.3 <= v <= 40),
          za=Param("float", check=lambda v: 0.1 < v <= 10), zb=Param("float", check=lambda v: 0.1 < v <= 10))
def koop(mol, R, za, zb):
    """Koopmans, ΔSCF and full-CI ionisation energies; orbital energies (hartree)."""
    return koopmans.koopmans(mol, R, za, zb)


@endpoint("walsh.diagram", ne=Param("int", check=lambda v: 2 <= v <= 8))
def walsh_(ne):
    """Orbital energies of AH2 against the angle, the Walsh energy and the predicted angle."""
    return walsh.diagram(ne)


@endpoint("react.global", I=Param("float", check=lambda v: 0 < v <= 100), A=Param("float", check=lambda v: -20 <= v <= 100))
def glob(I, A):
    """Electronegativity, chemical potential, hardness, softness, electrophilicity (eV)."""
    return reactivity.global_(I, A)


@endpoint("react.atoms")
def atoms():
    """Atomic ionisation energies and electron affinities (eV, NIST)."""
    return reactivity.ATOMS


def _types(v):
    return isinstance(v, list) and 2 <= len(v) <= 20 and all(t in huckel.HT for t in v)


def _bonds(v):
    return isinstance(v, list) and len(v) <= 60 and all(
        isinstance(b, list) and len(b) == 2 and all(isinstance(i, int) and not isinstance(i, bool) and 0 <= i < 20 for i in b)
        and b[0] != b[1] for b in v)


@endpoint("react.fukui", types=Param("list", check=_types), bonds=Param("list", check=_bonds))
def fukui(types, bonds):
    """Condensed Fukui functions f+, f-, f0 from Hückel populations of N, N + 1, N − 1 electrons."""
    if any(i >= len(types) or j >= len(types) for i, j in bonds):
        raise ValueError("bond index out of range")
    return reactivity.fukui(types, bonds)


# Azimuth up to 5000 atoms of each kind — the example «a protein, 1000 heavy atoms» asked for 1000 and was refused
@endpoint("semi.count", n=Param("int", check=lambda v: 0 <= v <= 5000), m=Param("int", check=lambda v: 0 <= v <= 5000))
def count(n, m):
    """Basis sizes and numbers of two-electron integrals: ab initio against NDDO, INDO, CNDO."""
    return semiemp.count(n, m)

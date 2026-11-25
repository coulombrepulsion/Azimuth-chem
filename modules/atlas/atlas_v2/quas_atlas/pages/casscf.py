"""Endpoints of the page "Multiconfigurational methods: CASSCF" (web/<lang>/casscf.html); model: core.casscf."""
from ..api import Param, endpoint
from ..core import casscf


@endpoint("cas.meta")
def meta():
    """Curves of H2, ethylene and N2 (cc-pVDZ) and the energy of two H atoms."""
    return casscf.meta()


@endpoint("cas.h2", i=Param("int", check=lambda v: 0 <= v < len(casscf.D["h2"])))
def h2(i):
    """H2: energies above full CI (kJ/mol) at the i-th distance."""
    return casscf.h2(i)


@endpoint("cas.eth", i=Param("int", check=lambda v: 0 <= v < len(casscf.D["eth"])))
def eth(i):
    """Ethylene torsion: relative energies (kJ/mol), barriers, values at the i-th angle."""
    return casscf.eth(i)


@endpoint("cas.n2", i=Param("int", check=lambda v: 0 <= v < len(casscf.D["n2"])))
def n2(i):
    """N2: energies relative to 1.1 A (eV), dissociation energies at 3 A, CCSD(T) - NEVPT2 deviation."""
    return casscf.n2(i)


@endpoint("cas.size", ne=Param("int", check=lambda v: 0 <= v <= 40), no=Param("int", check=lambda v: 1 <= v <= 40))
def size(ne, no):
    """Number of determinants and CSFs of CAS(ne, no) and the memory of one CI vector."""
    return casscf.size(ne, no)

"""Endpoints of the pages on the Bloch theorem and k-points (bloch.html) and on bands and the density of states
(bands.html), on the properties of crystals (solidprops.html); model: core.solids."""
from ..api import Param, endpoint
from ..core import solids


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


# ---- the Bloch theorem and k-points ----
@endpoint("sol.wave", k=_rng(-1, 1), m=Param("int", check=lambda v: -3 <= v <= 3))
def wave(k, m):
    """The Bloch wave of a chain at k (π/a) and the same state written with k + 2m (π/a); the band E(k)."""
    return solids.wave(k, m)


@endpoint("sol.mesh", kind=Param("str", check=lambda v: v in ("metal", "insulator")),
          n=Param("int", check=lambda v: 2 <= v <= 60), delta=_rng(0.1, 6))
def mesh(kind, n, delta):
    """The band energy per cell for the meshes of 1…n points: a metal or an insulator chain, and the exact value."""
    return solids.mesh(kind, n, delta)


@endpoint("sol.mesh2d", n=Param("int", check=lambda v: 1 <= v <= 12), shift=Param("bool"))
def mesh2d(n, shift):
    """The n × n mesh of a square lattice and its points different by symmetry, with weights."""
    return solids.mesh2d(n, shift)


@endpoint("sol.pw", cell=Param("str", check=lambda v: v in solids.CELLS), ecut=_rng(5, 120))
def pw(cell, ecut):
    """Plane waves of an orbital at Γ for the cutoff (Ry), the estimate, the vectors of the density."""
    return solids.plane_waves(solids.CELLS[cell], ecut)


# ---- bands and the density of states ----
@endpoint("sol.pair", delta=_rng(0, 6), b1=_rng(-3, -0.1), b2=_rng(-3, -0.1), e=_rng(0, 4), sigma=_rng(0.02, 0.5))
def pair(delta, b1, b2, e, sigma):
    """The bands, DOS and PDOS of a chain of two atoms per cell; the Fermi level for e electrons per cell."""
    return solids.pair(delta, b1, b2, e, sigma)


@endpoint("sol.graphene", delta=_rng(0, 8), sigma=_rng(0.05, 0.6))
def graphene(delta, sigma):
    """Graphene (Δ = 0) or a sheet of two different atoms: the bands Γ–M–K–Γ and the DOS (eV, β = −2.8 eV)."""
    return solids.graphene(delta, -2.8, sigma)


@endpoint("sol.nfe", V=_rng(0, 3), M=Param("int", check=lambda v: 0 <= v <= 10))
def nfe(V, M):
    """Nearly free electrons: the bands with 2M + 1 plane waves and the gaps."""
    return solids.nfe(V, M)


# ---- the properties of crystals: compression, phonons, heat capacity ----
@endpoint("sol.eos", kind=Param("str", check=lambda v: v in solids.EOS_PRESETS), span=_rng(0.5, 30),
          n=Param("int", check=lambda v: 4 <= v <= 30), noise=_rng(0, 50))
def eos(kind, span, n, noise):
    """E(V) points over ±span % of V0 with a noise of up to noise meV, the Birch–Murnaghan fit, the reference values."""
    return solids.eos(kind, span, n, noise)


@endpoint("sol.phonons", m1=_rng(1, 300), m2=_rng(1, 300), C=_rng(1, 1000))
def phonons(m1, m2, C):
    """The acoustic and optical branches of a chain of two atoms (amu, N/m), cm⁻¹, and the gap."""
    return solids.phonons(m1, m2, C)


@endpoint("sol.cv", kind=Param("str", check=lambda v: v in solids.DEBYE), T=_rng(1, 3000))
def cv(kind, T):
    """The heat capacity Cv/3R by Debye and by Einstein against T, the values at T and the T³ law."""
    return solids.heat_capacity(kind, T)

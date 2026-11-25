"""Endpoints of the pages added on NMR (nmr.html), conformers (conformers.html), heavy elements
(relativity.html) and crystals (crystals.html); models: core.nmr, core.conformers, core.relativity, core.crystals."""
from ..api import Param, endpoint
from ..core import conformers, crystals, nmr, relativity


def _rng(a, b):
    return Param("float", check=lambda v: a <= v <= b, doc=f"{a}..{b}")


# ---- NMR ----
@endpoint("nmr.larmor", B0=_rng(0.01, 100))
def larmor(B0):
    """Larmor frequencies (MHz) and Hz per ppm of 1H, 13C, 15N, 19F, 31P at B0 (T)."""
    return nmr.larmor(B0)


@endpoint("nmr.shifts", sigmas=Param("list"), ref=_rng(-1000, 10000), slope=_rng(-10, 10),
          intercept=Param("float", default=None))
def shifts(sigmas, ref, slope, intercept):
    """Chemical shifts δ from shieldings σ (ppm) with a reference or a linear scaling."""
    if not all(isinstance(x, (int, float)) and not isinstance(x, bool) and abs(x) < 1e5 for x in sigmas):
        raise ValueError("shieldings must be numbers")
    return nmr.shifts([float(x) for x in sigmas], ref, slope, intercept)


@endpoint("nmr.multiplet", n=Param("int", check=lambda v: 0 <= v <= 12), J=_rng(0, 500), nu0=_rng(1, 2000),
          delta=_rng(-50, 300))
def multiplet(n, J, nu0, delta):
    """First-order multiplet of n equivalent spin-1/2 neighbours: lines (ppm, intensity), width."""
    return nmr.multiplet(n, J, nu0, delta)


@endpoint("nmr.spectrum", peaks=Param("list"), nu0=_rng(1, 2000), fwhm=_rng(0.05, 50), lo=_rng(-50, 300),
          hi=_rng(-50, 300), N=Param("int", check=lambda v: 10 <= v <= 5000))
def spectrum(peaks, nu0, fwhm, lo, hi, N):
    """A stick-and-Lorentzian spectrum of the peaks [{delta, count, n, J}]."""
    if not all(isinstance(p, dict) and isinstance(p.get("delta"), (int, float)) for p in peaks):
        raise ValueError("peaks: [{delta, count, n, J}]")
    return nmr.spectrum(peaks, nu0, fwhm, lo, hi, N)


# ---- conformers ----
@endpoint("conf.profile", V1=_rng(-100, 100), V2=_rng(-100, 100), V3=_rng(-100, 100), T=_rng(1, 5000))
def profile(V1, V2, V3, T):
    """Torsion profile, minima (with Boltzmann fractions at T) and maxima."""
    return conformers.profile(V1, V2, V3, T)


@endpoint("conf.cost", n=Param("int", check=lambda v: 1 <= v <= 40), k=Param("int", check=lambda v: 2 <= v <= 12),
          minutes=_rng(0.001, 10000))
def cost(n, k, minutes):
    """Starting structures of a grid search k^n and its time."""
    return conformers.grid_cost(n, k, minutes)


# ---- heavy elements ----
@endpoint("rel.atom", Z=Param("int", check=lambda v: 1 <= v <= 118))
def atom(Z):
    """Hydrogen-like 1s: v/c, γ, radius ratio, Schrödinger and Dirac energies; def2 ECP core size."""
    return {**relativity.hydrogenic(Z), "ecp": relativity.ecp(Z)}


@endpoint("rel.curve")
def curve():
    """[Z, radius ratio, energy ratio] for Z = 1..118."""
    return relativity.curve()


# ---- crystals ----
_len = _rng(0.5, 100)
_ang = _rng(20, 160)


@endpoint("cr.presets")
def presets():
    """Cells of the examples (Å, degrees, Z, M, centring)."""
    return crystals.PRESETS


@endpoint("cr.cell", a=_len, b=_len, c=_len, al=_ang, be=_ang, ga=_ang, Z=Param("int", check=lambda v: 1 <= v <= 1000),
          M=_rng(0.001, 1e5))
def cell(a, b, c, al, be, ga, Z, M):
    """Cell volume (Å³) and density (g/cm³)."""
    return crystals.cell(a, b, c, al, be, ga, Z, M)


@endpoint("cr.pattern", a=_len, b=_len, c=_len, al=_ang, be=_ang, ga=_ang,
          cent=Param("str", check=lambda v: v in ("P", "I", "F", "D", "H")), lam=_rng(0.1, 5),
          n=Param("int", check=lambda v: 1 <= v <= 60))
def pattern(a, b, c, al, be, ga, cent, lam, n):
    """Allowed reflections hkl with d, 2θ and multiplicity, sorted by 2θ."""
    return crystals.pattern(a, b, c, al, be, ga, cent, lam, 4, n)


@endpoint("cr.packing", kind=Param("str", check=lambda v: v in crystals.PACKING))
def packing(kind):
    """Atoms per cell, packing fraction, coordination number, a/r of a cubic packing."""
    return crystals.packing(kind)

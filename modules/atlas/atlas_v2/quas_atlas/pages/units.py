"""Endpoints of the page "Atomic units" (web/<lang>/units.html); model: core.units."""
from ..api import Param, endpoint
from ..core import units as u


@endpoint("au.constants")
def constants():
    """CODATA 2018 factors used by the page."""
    return u.constants()


@endpoint("au.convert", cat=Param("str", check=lambda v: v in u.CAT), unit=Param("str"),
          value=Param("float"))
def convert(cat, unit, value):
    """A value in one unit expressed in all units of its category."""
    return u.convert(cat, unit, value)


@endpoint("au.estimate", Z=Param("int", check=lambda v: 1 <= v <= 6), r=Param("float", check=lambda v: 0.01 <= v <= 10))
def estimate(Z, r):
    """Kinetic, potential and total energy of an electron confined to radius r."""
    return u.estimate(Z, r)


@endpoint("au.scale", unit=Param("str", check=lambda v: v in ("Eh", "eV", "kJ", "cm")))
def scale(unit):
    """The page's energy scale in the chosen unit."""
    return u.scale(unit)

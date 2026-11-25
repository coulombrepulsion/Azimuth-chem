"""Endpoints of the page "Molecular Hamiltonian" (web/<lang>/hamiltonian.html); model: core.hamiltonian."""
from ..api import Param, endpoint
from ..core import hamiltonian as h


@endpoint("ham.molecule", formula=Param("str"),
          q=Param("any", None, check=lambda v: v is None or (isinstance(v, int) and not isinstance(v, bool) and abs(v) <= 20),
                  doc="integer charge or null"))
def molecule(formula, q):
    """Nuclei, electrons and the number of each kind of Hamiltonian term."""
    return h.molecule(formula, q)

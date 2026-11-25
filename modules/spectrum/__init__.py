"""Azimuth spectrum module."""

# own version numbers of the sections, shown in About (hub/about.py)
# thermochemistry, convergence, comparison of spectra, Psi4 TD-DFT
# the energy diagram of a reaction (reaction.py, reaction_view.py)
# electron density analysis (density.py, density_view.py)
# the tabs of Compass, a result per tab
# the orbitals of an ORCA result from its .gbw (orca_2mkl)
# the orbital window hands its work over to the density panel of Compass
# Quill with the magnifier while a tab has no result
# the results of NWChem, Q-Chem, GAMESS (US) and Firefly
# the orbitals printed in GAMESS, NWChem and Q-Chem outputs
# thermochemistry finite at low temperatures; the multiplicity of GAMESS, NWChem, Q-Chem
# big outputs are read in the background
# orbitals and the density are computed off the window thread
# the versions of the sections stay below 1 until the first release (the user's wish): the major number 1 (2 for the
# Atlas) is dropped and the next minor is taken — 1.6.4 → 0.7.0
# electronic circular dichroism (rotatory strengths of ORCA and Gaussian, the ECD curve)
# the results of MOPAC (mopac.py: the output and its .aux)
__version__ = '0.9.0'

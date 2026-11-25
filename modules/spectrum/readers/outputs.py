"""One entry for the outputs of all supported programs.

read_any(text, path=None) -> orca.Output: Gaussian (gaussian.py), xtb (xtb.py; path: the output file, whose neighbours
xtbopt.xyz, g98.out, charges, wbo are read), Psi4 (psi4.py), NWChem (nwchem.py), Q-Chem (qchem.py), GAMESS (US) and
Firefly (gamess.py), MOPAC (mopac.py, with the .aux next to the output), else ORCA (orca.py, which raises ValueError for
text it does not recognize). program(text) -> 'Gaussian' | 'xtb' | 'Psi4' | 'NWChem' | 'Q-Chem' | 'GAMESS' | 'ORCA'.
Recognition uses the banners of the first 20000 characters: «Entering Gaussian System» / «Gaussian, Inc.» / «Gaussian
09|16:», «xtb version», «Psi4: An Open-Source Ab Initio Electronic Structure Package», «Northwest Computational
Chemistry Package (NWChem)», «Welcome to Q-Chem», «GAMESS VERSION =» / «Firefly version», «MOPAC v<version>» with
«CALCULATION RESULTS». The extensions .nwout, .qcout, .gamout are results too (modules/compass/workspace.file_kind).
Tests: tests/spectrum/test_outputs.py.
"""

from modules.spectrum.readers.gamess import is_gamess, read_gamess
from modules.spectrum.readers.gaussian import is_gaussian, read_gaussian
from modules.spectrum.readers.mopac import is_mopac, read_mopac
from modules.spectrum.readers.nwchem import is_nwchem, read_nwchem
from modules.spectrum.readers.orca import read_output
from modules.spectrum.readers.results import MAX_BYTES
from modules.spectrum.readers.psi4 import is_psi4, read_psi4
from modules.spectrum.readers.qchem import is_qchem, read_qchem
from modules.spectrum.readers.xtb import is_xtb, read_xtb


def program(text):
    if is_gaussian(text):
        return 'Gaussian'
    if is_xtb(text):
        return 'xtb'
    if is_psi4(text):
        return 'Psi4'
    if is_nwchem(text):
        return 'NWChem'
    if is_qchem(text):
        return 'Q-Chem'
    if is_gamess(text):
        return 'GAMESS'
    if is_mopac(text):
        return 'MOPAC'
    return 'ORCA'


READERS = {'NWChem': read_nwchem, 'Q-Chem': read_qchem, 'GAMESS': read_gamess}
FILTER = 'ORCA, Gaussian, xtb, Psi4, NWChem, Q-Chem, GAMESS, MOPAC (*.out *.log *.nwout *.qcout *.gamout);;Все файлы (*)'


def read_any(text, path=None):
    if len(text) > MAX_BYTES:
        return read_output(text)  # raises the size message
    found = program(text)
    if found == 'Gaussian':
        return read_gaussian(text)
    if found == 'xtb':
        return read_xtb(text, path)
    if found == 'Psi4':
        return read_psi4(text)
    if found == 'MOPAC':  # the .aux next to the output is read too
        return read_mopac(text, path)
    if found in READERS:
        return READERS[found](text)
    return read_output(text)

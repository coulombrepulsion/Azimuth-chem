"""The point group of molecules that are not in the library of Compass, built from SMILES by Compass itself
(formats.from_smiles) — as a student gets them. Checked 2026-11-22 on the owner's Mac against the known groups, also
after a GFN2-xTB optimization (the same groups). H₂O₂, spiropentane and the dichloroethenes were built wrong then
(flat, coplanar rings, «/» not read) — the builder was corrected (0.222.9); ethanol and ethylene glycol come out as
gauche conformers (C1, a right answer for that geometry)."""

import pytest

from modules.compass.chemistry import symmetry
from modules.compass.chemistry.formats import from_smiles

CASES = [
    ('O', 'C2v'), ('N', 'C3v'), ('C', 'Td'), ('O=C=O', 'D∞h'), ('C#N', 'C∞v'), ('C#C', 'D∞h'), ('C=C', 'D2h'),
    ('CC', 'D3d'), ('ClCCl', 'C2v'), ('ClC(Cl)Cl', 'C3v'), ('ClC(Cl)(Cl)Cl', 'Td'), ('CCl', 'C3v'), ('C=O', 'C2v'),
    ('FB(F)F', 'D3h'), ('FS(F)(F)(F)(F)F', 'Oh'), ('ClP(Cl)(Cl)(Cl)Cl', 'D3h'), ('c1ccccc1', 'D6h'),
    ('c1ccc2ccccc2c1', 'D2h'), ('C1CCCCC1', 'D3d'), ('C=C=C', 'D2d'), ('CO', 'Cs'), ('CC(C)=O', 'C2v'),
    ('c1ccncc1', 'C2v'), ('c1ccoc1', 'C2v'), ('c1ccsc1', 'C2v'), ('C1CC1', 'D3h'), ('C12C3C4C1C5C2C3C45', 'Oh'),
    ('C1C2CC3CC1CC(C2)C3', 'Td'), ('O=S=O', 'C2v'), ('C=C=O', 'C2v'), ('CN', 'Cs'), ('C1CO1', 'C2v'),
    ('Clc1ccc(Cl)cc1', 'D2h'), ('Clc1cccc(Cl)c1', 'C2v'), ('Clc1ccccc1Cl', 'C2v'), ('Clc1cc(Cl)cc(Cl)c1', 'D3h'),
    ('Fc1c(F)c(F)c(F)c(F)c1F', 'D6h'), ('C=CC=C', 'C2h'), ('COC', 'C2v'), ('CC#N', 'C3v'), ('CCCC', 'C2h'),
    ('NC(N)=O', 'C2'), ('CC(O)=O', 'Cs'), ('Cc1ccccc1', 'Cs'), ('F[Xe](F)(F)F', 'D4h'), ('CN(C)C', 'C3v'),
    ('OO', 'C2'), ('C1CC12CC2', 'D2d'), ('Cl/C=C/Cl', 'C2h'), ('Cl/C=C\\Cl', 'C2v'),
]


@pytest.mark.parametrize('smiles, group', CASES)
def test_the_point_group_of_a_molecule_built_from_smiles(smiles, group):
    assert symmetry.analyze(from_smiles(smiles))['name'] == group

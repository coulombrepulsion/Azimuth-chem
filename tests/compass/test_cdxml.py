"""ChemDraw CDXML (modules/compass/chemistry/formats.read_cdxml). Oracle: a file of acetic acid written here
as ChemDraw writes it (nodes with p and Element, carbon without it; bonds with Order), its bond lengths of 14.4 pt."""

from math import dist

import pytest

from modules.compass.chemistry import formats

ACETIC = '''<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE CDXML SYSTEM "http://www.cambridgesoft.com/xml/cdxml.dtd" >
<CDXML><page id="1">
<fragment id="2">
<n id="3" p="100 100"/>
<n id="4" p="112.47 107.2"/>
<n id="5" p="124.94 100" Element="8"/>
<n id="6" p="112.47 121.6" Element="8" NumHydrogens="0"/>
<b id="7" B="3" E="4"/>
<b id="8" B="4" E="5"/>
<b id="9" B="4" E="6" Order="2"/>
</fragment>
<t id="10" p="90 140"><s font="3" size="10">acetic acid</s></t>
</page></CDXML>
'''


def test_acetic_acid_from_chemdraw():
    molecule = formats.read_cdxml(ACETIC)
    assert [a.symbol for a in molecule.atoms] == ['C', 'C', 'O', 'O'] and molecule.title == 'acetic acid'
    assert sorted(o for _, _, o in molecule.bonds) == [1, 1, 2]
    assert all(abs(a.z) < 1e-12 for a in molecule.atoms)  # flat: «Сделать 3D» raises it
    assert abs(dist(molecule.atoms[0].position, molecule.atoms[1].position) - 1.45) < 0.01  # 14.4 pt → 1.45 Å
    assert formats.cdxml_charges(ACETIC) == [0, 0, 0, 0]


def test_an_abbreviation_and_an_empty_file_are_said():
    phenyl = ACETIC.replace('<n id="3" p="100 100"/>',
                            '<n id="3" p="100 100" NodeType="Fragment"><fragment id="20"/><t><s>Ph</s></t></n>')
    with pytest.raises(ValueError, match='Ph'):
        formats.read_cdxml(phenyl)
    with pytest.raises(ValueError):
        formats.read_cdxml('<CDXML><page/></CDXML>')

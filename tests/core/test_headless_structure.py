"""Structures without the window (azimuth/headless_structure.py): a molecule built and edited in turn, a crystal changed
in turn, the files Compass opens, the numbers of the atoms in the answer, the errors that name the operation."""

import json
from pathlib import Path

import pytest

from azimuth import headless_structure as hs

ROOT = Path(__file__).resolve().parents[2]
SILICON = ROOT / 'examples' / '10-crystals' / 'Si_diamond.cif'


def test_a_molecule_is_built_and_edited_in_turn(tmp_path):
    # ethane: one H becomes F, another H a methyl (propane-like), the C–C–C–H… dihedral set, UFF at the end
    answer = hs.build_molecule({'smiles': 'CC', 'title': 'ethane'}, [], root=tmp_path)
    listed = answer['list']
    assert answer['formula'] == 'C2H6' and answer['atoms'] == 8 and listed[0][:2] == [1, 'C']
    hydrogens = [n for n, symbol, *_ in listed if symbol == 'H']
    assert Path(answer['file']).parent == tmp_path and Path(answer['file']).suffix == '.xyz'
    edited = hs.build_molecule({'path': answer['file']}, [
        {'op': 'element', 'atom': hydrogens[0], 'symbol': 'f'},
        {'op': 'substitute', 'atom': hydrogens[-1], 'fragment': 'methyl'},
        {'op': 'set', 'atoms': [1, 2], 'value': 1.6},
        {'op': 'optimize'},
    ], out=str(tmp_path / 'edited.mol'))
    assert edited['formula'] == 'C3H7F' and edited['file'] == str(tmp_path / 'edited.mol')
    assert 'V2000' in Path(edited['file']).read_text(encoding='utf-8') and edited['uff_energy_kcal_mol'] < 50
    assert any('UFF' in n for n in edited['notes'])
    bonded = {tuple(sorted(b[:2])) for b in edited['bonds']}
    assert (1, 2) in bonded  # the bonds of the answer carry the numbers of the list
    # the same file is never overwritten: a second write gets a number
    again = hs.build_molecule({'path': edited['file']}, [], out=str(tmp_path / 'edited.mol'))
    assert again['file'] == str(tmp_path / 'edited-2.mol')


def test_a_distance_an_angle_and_conformers(tmp_path):
    answer = hs.build_molecule({'smiles': 'CCCC', 'title': 'butane'}, [
        {'op': 'set', 'atoms': [1, 2, 3, 4], 'value': 60},
        {'op': 'conformers', 'count': 3},
    ], root=tmp_path)
    assert answer['formula'] == 'C4H10' and 1 <= len(answer.get('other_conformers', [])) + 1 <= 3
    assert all(Path(p).is_file() for p in answer.get('other_conformers', []))


def test_the_library_and_the_errors(tmp_path):
    water = hs.build_molecule({'library': 'water'}, [], root=tmp_path)
    assert water['formula'] == 'H2O'
    benzene = hs.build_molecule({'library': 'Бензол'}, [{'op': 'substitute', 'atom': 12, 'fragment': 'hydroxyl'}],
                                root=tmp_path)
    assert benzene['formula'] == 'C6H6O'
    with pytest.raises(ValueError, match=r'operation 1 \(element\): no atom 9'):
        hs.build_molecule({'smiles': 'CC'}, [{'op': 'element', 'atom': 9, 'symbol': 'N'}], root=tmp_path)
    with pytest.raises(ValueError, match='operation 1 .*an operation is'):
        hs.build_molecule({'smiles': 'CC'}, [{'op': 'explode'}], root=tmp_path)
    with pytest.raises(ValueError, match='no single fragment'):
        hs.build_molecule({'smiles': 'CC'}, [{'op': 'substitute', 'atom': 3, 'fragment': 'zzz'}], root=tmp_path)
    with pytest.raises(ValueError, match='no single molecule'):
        hs.molecule({'library': 'nothing-like-this'})
    with pytest.raises(ValueError, match='"out" ends with'):
        hs.build_molecule({'smiles': 'C'}, [], out=str(tmp_path / 'x.pdb'))
    assert len(list(tmp_path.iterdir())) == 2  # nothing written by the failed commands


def test_a_crystal_is_changed_in_turn(tmp_path):
    from modules.compass.chemistry import crystal as cr

    first = hs.build_crystal({'path': str(SILICON)}, [{'op': 'primitive'}], root=tmp_path)
    assert first['atoms_in_cell'] == 2 and first['composition'] == {'Si': 2}
    doped = hs.build_crystal({'path': str(SILICON)}, [
        {'op': 'primitive'}, {'op': 'supercell', 'n': [2, 2, 2]},
        {'op': 'substitute', 'sites': [1], 'symbol': 'p'}, {'op': 'vacancy', 'sites': [16]},
    ], out=str(tmp_path / 'si_p.cif'))
    assert doped['composition'] == {'Si': 14, 'P': 1} and doped['atoms_in_cell'] == 15
    assert doped['sites'][0][1:3] == ['P1', 'P'] and doped['space_group'] == 'P 1'
    back = cr.parse_cif(Path(doped['file']).read_text(encoding='utf-8'))  # the file is a CIF Compass reads
    assert len(cr.unit_cell(back)) == 15
    slab = hs.build_crystal({'path': str(SILICON)}, [{'op': 'surface', 'hkl': [1, 1, 1], 'layers': 2, 'vacuum': 12}],
                            root=tmp_path)
    assert slab['cell']['c'] > 12 and slab['composition'] == {'Si': slab['atoms_in_cell']}
    with pytest.raises(ValueError, match=r'operation 2 \(substitute\): no site 99'):
        hs.build_crystal({'path': str(SILICON)}, [{'op': 'primitive'}, {'op': 'substitute', 'sites': [99], 'symbol': 'C'}],
                         root=tmp_path)
    catalogue = hs.catalogue()
    assert 'methyl' in catalogue['fragments']['short names'] and 'vacancy' in catalogue['crystal_operations']


def test_through_the_server(tmp_path):
    import sys

    sys.path.insert(0, str(ROOT / 'tools'))
    import azimuth_mcp

    server = azimuth_mcp.Server.__new__(azimuth_mcp.Server)  # no jobs, no settings: only the structure tools
    names = {t['name'] for t in azimuth_mcp.TOOLS}
    assert {'azimuth_structure_molecule', 'azimuth_structure_crystal', 'azimuth_structure_catalogue'} <= names
    answer = server.handle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call', 'params': {
        'name': 'azimuth_structure_molecule',
        'arguments': {'molecule': {'smiles': 'O'}, 'out': str(tmp_path / 'water.xyz')}}})
    found = json.loads(answer['result']['content'][0]['text'])
    assert not answer['result']['isError'] and found['formula'] == 'H2O' and Path(found['file']).is_file()
    wrong = server.handle({'jsonrpc': '2.0', 'id': 2, 'method': 'tools/call', 'params': {
        'name': 'azimuth_structure_crystal', 'arguments': {'crystal': {'path': str(SILICON)},
                                                           'operations': [{'op': 'supercell', 'n': [2]}]}}})
    assert wrong['result']['isError'] and 'supercell' in wrong['result']['content'][0]['text']

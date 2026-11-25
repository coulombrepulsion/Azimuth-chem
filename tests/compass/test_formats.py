"""Molecule files of other programs (modules/compass/chemistry/formats.py)."""

from math import dist

import pytest

from azimuth.core import EXAMPLES, read_xyz
from modules.compass.chemistry.builder import connections
from modules.compass.chemistry import formats
from modules.compass.chemistry.names import name

WATER = read_xyz(EXAMPLES['Вода · H₂O'])
BONDS = ((0, 1, 1), (0, 2, 1))


def named(m):
    return name([a.symbol for a in m.atoms], [(i, j) for i, j, _ in connections(m)])


@pytest.mark.parametrize(
    'write,read',
    [
        (formats.write_mol, formats.read_mol),
        (formats.write_sdf, formats.read_mol),
        (formats.write_mol2, formats.read_mol2),
        (formats.write_pdb, formats.read_pdb),
    ],
)
def test_round_trip(write, read):
    back = read(write(WATER, BONDS))
    assert [a.symbol for a in back.atoms] == ['O', 'H', 'H'] and named(back) == 'вода'
    assert all(dist(a.position, b.position) < 1e-3 for a, b in zip(back.atoms, WATER.atoms))
    assert sorted((min(i, j), max(i, j), o) for i, j, o in back.bonds) == [(0, 1, 1), (0, 2, 1)]


def test_molfile_orders_and_aromatic_kekule():
    co2 = (
        'CO2\n\n\n  3  2  0  0  0  0  0  0  0  0999 V2000\n'
        + ''.join(f'{x:10.4f}    0.0000    0.0000 {s:<3} 0  0\n' for s, x in (('O', -1.16), ('C', 0), ('O', 1.16)))
        + '  1  2  2  0\n  2  3  2  0\nM  END\n'
    )
    assert {o for *_, o in formats.read_mol(co2).bonds} == {2}
    ring = formats.kekule(6, [(k, (k + 1) % 6, 4) for k in range(6)])
    assert sorted(o for *_, o in ring) == [1, 1, 1, 2, 2, 2]


def test_gaussian_input():
    text = '%nproc=4\n#p B3LYP/6-31G* opt\n\nwater\n\n0 1\nO 0.0 0.0 0.0\nH 0.7586 0.0 0.5043\n8 -0.0 0.0 1.5\n\n'
    text = text.replace('8 -0.0 0.0 1.5\n', 'H -0.7586 0.0 0.5043\n')
    mol, charge, mult = formats.read_gaussian_input(text)
    assert (charge, mult) == (0, 1) and named(mol) == 'вода' and mol.title == 'water'
    oh, _, _ = formats.read_gaussian_input('#p hf\n\nz\n\n0 1\nO\nH 1 0.96\n\n')  # a Z-matrix
    assert dist(oh.atoms[0].position, oh.atoms[1].position) == pytest.approx(0.96)


def orientation(rows):
    return (
        '                         Standard orientation:\n '
        + '-' * 60
        + '\n Center  Atomic  Atomic  Coordinates (Angstroms)\n'
        ' Number  Number  Type    X Y Z\n '
        + '-' * 60
        + '\n'
        + ''.join(f'    {k + 1}    {z}    0    {x:.6f}    {y:.6f}    {w:.6f}\n' for k, (z, x, y, w) in enumerate(rows))
        + ' '
        + '-' * 60
        + '\n'
    )


def test_gaussian_log_steps():
    a = [(8, 0, 0, 0), (1, 0.8, 0, 0.55), (1, -0.8, 0, 0.55)]
    b = [(8, 0, 0, 0), (1, 0.7586, 0, 0.5043), (1, -0.7586, 0, 0.5043)]
    text = (
        ' Entering Gaussian System\n'
        + orientation(a)
        + ' SCF Done:  E(RB3LYP) =  -76.40  A.U.\n'
        + orientation(b)
        + ' SCF Done:  E(RB3LYP) =  -76.42  A.U.\n'
    )
    t = formats.read_gaussian_log(text)
    assert len(t.steps) == 2 and [s.energy for s in t.steps] == [-76.40, -76.42]
    assert t.steps[1].geometry.atoms[1].x == pytest.approx(0.7586)


def test_molden_and_xyz_frames():
    frames = ''.join(f'3\nE {e}\nO 0 0 0\nH {x} 0 0.5\nH -{x} 0 0.5\n' for e, x in ((-76.0, 0.8), (-76.1, 0.76)))
    molden = (
        '[Molden Format]\n[Atoms] Angs\nO 1 8 0 0 0\nH 2 1 0.76 0 0.5\nH 3 1 -0.76 0 0.5\n[GEOCONV]\nenergy\n-76.0\n-76.1\n[GEOMETRIES] XYZ\n'
        + frames
    )
    t = formats.read_molden(molden)
    assert len(t.steps) == 2 and t.steps[1].energy == -76.1 and named(t.geometry) == 'вода'
    x = formats.xyz_trajectory(frames)
    assert formats.xyz_frame_count(frames) == 2 and [s.energy for s in x.steps] == [-76.0, -76.1]


@pytest.mark.parametrize(
    'smiles,expected',
    [
        ('CCO', 'этанол'),
        ('c1ccccc1', 'бензол'),
        ('CC(=O)O', 'этановая (уксусная) кислота'),
        ('C1CCCCC1', 'циклогексан'),
        ('O.N', 'вода + аммиак'),
    ],
)
def test_from_smiles(smiles, expected):
    m = formats.from_smiles(smiles)
    assert named(m) == expected
    if smiles == 'c1ccccc1':
        ring = [dist(m.atoms[k].position, m.atoms[(k + 1) % 6].position) for k in range(6)]
        assert max(ring) - min(ring) < 0.01
    with pytest.raises(ValueError):
        formats.from_smiles('C1CC(')


def test_gif_encoder_without_pillow():
    import numpy as np
    from modules.compass.view import gif

    a = np.zeros((12, 16, 4), np.uint8)
    a[..., 0] = 200
    a[..., 3] = 255
    a[2:5, 2:5, 3] = 0
    data = gif.encode([a, a[::-1].copy()], 100)
    assert data[:6] == b'GIF89a' and data[-1:] == b';' and b'NETSCAPE2.0' in data


def test_sdf_records_each_molecule():
    # an SDF with several records — every one of them (empty records are skipped)
    neon = read_xyz('1\nneon\nNe 0 0 0\n')
    text = formats.write_sdf(WATER, BONDS) + '\n$$$$\n' + formats.write_sdf(neon, ())
    records = formats.read_sdf_records(text)
    assert [m.formula for m in records] == ['H2O', 'Ne'] and records[0].bonds == BONDS
    with pytest.raises(ValueError):
        formats.read_sdf_records('$$$$\n')


def test_v3000_for_big_molecules_round_trip():
    # more than 999 atoms do not fit the counts of V2000 — the V3000 molfile (Compass itself keeps 500
    # atoms at most for now, ROADMAP «Потом»), read back by read_mol
    from azimuth.core import Atom, Molecule

    big = Molecule('chain', tuple(Atom('He', 1.5 * k, 0.0, 0.0) for k in range(1002)))
    text = formats.write_mol(big, ())
    assert 'V3000' in text.splitlines()[3] and 'M  V30 COUNTS 1002 0' in text and 'M  V30 1002 He 1501.5000' in text
    small = formats.read_mol(formats.write_mol_v3000(WATER, BONDS))
    assert small.bonds == BONDS and [a.position for a in small.atoms] == [a.position for a in WATER.atoms]


def test_pdb_models_are_frames():
    # MODEL … ENDMDL frames (an MD or NMR ensemble) — steps; CONECT written once after the last model
    def frame(x):
        moved = read_xyz(f'3\nw\nO 0 0 0\nH {x} 0 0\nH -0.24 0.93 0\n')
        return [line for line in formats.write_pdb(moved, BONDS).splitlines() if line.startswith('HETATM')]

    conect = [line for line in formats.write_pdb(WATER, BONDS).splitlines() if line.startswith('CONECT')]
    text = ''.join(f'MODEL {k}\n' + '\n'.join(frame(x)) + '\nENDMDL\n' for k, x in ((1, 0.95), (2, 0.97), (3, 0.99)))
    text += '\n'.join(conect) + '\nEND\n'
    assert formats.pdb_model_count(text) == 3 and formats.pdb_model_count(formats.write_pdb(WATER, BONDS)) == 1
    trajectory = formats.pdb_trajectory(text)
    assert [s.geometry.atoms[1].x for s in trajectory.steps] == [0.95, 0.97, 0.99]
    assert all(s.geometry.bonds == BONDS and s.energy is None for s in trajectory.steps)


def test_pdb_residues_as_labels():
    # one label per residue — on CA of an amino acid, on the first atom otherwise; a chain prefix with
    # several chains; none for a small molecule (one residue or the generic MOL of Azimuth's own PDB)
    rows = [
        ('N', 'ALA', 'A', 1), ('CA', 'ALA', 'A', 1), ('C', 'ALA', 'A', 1),
        ('N', 'GLY', 'A', 2), ('CA', 'GLY', 'A', 2), ('O', 'HOH', 'B', 3),
    ]
    text = ''.join(
        f'ATOM  {k + 1:5d} {name:<4} {res:>3} {chain}{seq:4d}    {k * 1.5:8.3f}{0:8.3f}{0:8.3f}  1.00  0.00          {name[0]:>2}\n'
        for k, (name, res, chain, seq) in enumerate(rows)
    ) + 'END\n'
    assert formats.pdb_labels(text) == {1: 'A:Ala1', 4: 'A:Gly2', 5: 'B:HOH3'}
    assert formats.pdb_labels(formats.write_pdb(WATER, BONDS)) == {}


def test_sdf_without_names_and_loose_columns():
    """SDF records with an empty first line (RDKit, Open Babel, PubChem without a name) are read: before,
    the empty name was cut together with the end of «$$$$» and the counts line moved up; also counts and atoms
    not in their columns, a lost header line and old Mac line ends (CR)."""
    from modules.compass.chemistry import formats

    record = (
        '\n     RDKit          3D\n\n'
        '  2  1  0  0  0  0  0  0  0  0999 V2000\n'
        '    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '    1.2000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '  1  2  2  0\n'
        'M  END\n$$$$\n'
    )
    found = formats.read_sdf_records(record + record)
    assert [len(m.atoms) for m in found] == [2, 2]
    assert [a.symbol for a in found[1].atoms] == ['C', 'O']
    loose = 'name\nprog\n\n2 1 0 0 0 0 0 0 0 0 999 V2000\n0.0 0.0 0.0 C 0 0\n1.2 0.0 0.0 O 0 0\n1 2 2 0\nM  END\n'
    assert [a.symbol for a in formats.read_mol(loose).atoms] == ['C', 'O']
    lost = loose.split('\n', 1)[1]  # the name line is missing
    assert len(formats.read_mol(lost).atoms) == 2
    assert len(formats.read_sdf_records(record.replace('\n', '\r'))[0].atoms) == 2


def test_sdf_records_named_by_their_data_items():
    """The user's database Cs_full.sdf (RDKit): the header line of every record is empty, the name
    is the data item «> <Name> (n)» — every record was «Молфайл». The records below are its own (acetic acid, n 11)
    and the form of its unnamed ones («nan» of a table)."""
    from modules.compass.chemistry import formats

    body = (
        '\n     RDKit          2D\n\n'
        '  4  3  0  0  0  0  0  0  0  0999 V2000\n'
        '    1.2990    0.7500    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '    2.5981   -0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '    1.2990    2.2500    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '    0.0000    0.0000    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0\n'
        '  1  2  1  0\n  1  3  2  0\n  1  4  1  0\nM  END\n'
    )
    acetic = body + '>  <Name>  (11) \nEthanoic_acid_(Acetic_acid)\n\n>  <logK_Cs_z=1.0_T=25_I=0.1>  (11) \n-0.33\n\n$$$$\n'
    unnamed = body + '>  <logK_Cs_z=1_T=25.0_I=0.0>  (41) \n6.15\n\n>  <Name>  (41) \nnan\n\n$$$$\n'
    pubchem = 'aspirin\n' + body[1:] + '>  <PUBCHEM_IUPAC_NAME>\nacetic acid\n\n$$$$\n'
    found = formats.read_sdf_records(acetic + unnamed + pubchem)
    assert [m.title for m in found][0] == 'Ethanoic acid (Acetic acid)'  # the underscores are its spaces
    assert found[1].title != 'nan' and formats.sdf_name(formats.sdf_items(unnamed)) == ''  # no name: the formula
    assert found[2].title == 'aspirin'  # a header line of its own wins over the items
    assert formats.sdf_items(acetic) == {'Name': 'Ethanoic_acid_(Acetic_acid)', 'logK_Cs_z=1.0_T=25_I=0.1': '-0.33'}
    assert formats.sdf_name({'PUBCHEM_IUPAC_NAME': '2-acetyloxybenzoic acid', 'id': '7'}) == '2-acetyloxybenzoic acid'
    assert formats.sdf_name({'logK': '0.2'}) == ''


def test_an_orca_input_with_atomic_numbers():
    # ORCA takes the element as a
    # symbol or as its atomic number, and «*xyz» may stand after a space; difluoroacetic acid as she wrote it
    text = '''%PAL NPROCS 10 END
! B3LYP RIJCOSX def2-SVP def2/J CPCM(water)

 *xyz 0 1
1       -0.647066880      0.000000000     -3.257334726
8       -0.647066880     -0.507766095     -2.428331138
8       -0.647066880      1.603052223     -1.642788308
6       -0.647066880      0.411818743     -1.429297183
6       -0.647066880     -0.247834459     -0.073962214
9        0.234081120     -0.887746826      0.029389331
1       -0.647066880      0.516223241      0.701993181
9       -1.528214880     -0.887746826      0.029389331
*
'''
    from modules.compass.chemistry import formats

    molecule, charge, mult = formats.read_orca_input(text)
    assert [a.symbol for a in molecule.atoms] == ['H', 'O', 'O', 'C', 'C', 'F', 'H', 'F'] and (charge, mult) == (0, 1)
    assert molecule.atoms[5].x == 0.23408112
    with pytest.raises(ValueError):
        formats.read_orca_input('* xyz 0 1\n200 0 0 0\n*\n')  # no element 200

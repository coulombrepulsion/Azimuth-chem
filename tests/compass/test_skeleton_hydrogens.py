"""The hydrogens of a file of the heavy atoms only (compass.editing.skeleton_hydrogens).

Oracles: the molecular formulas of benzene C6H6, ethanol C2H6O, acetone C3H6O, pyridine C5H5N and acetic acid
C2H4O2 (the skeletons in XYZ without bonds — the orders from the lengths, as a database file is read); a structure
with one hydrogen is not touched.
"""

from math import cos, pi, sin

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import editing


def ring(symbols, r=1.39):
    return Molecule('', tuple(Atom(s, r * cos(2 * pi * k / 6), r * sin(2 * pi * k / 6), 0.0) for k, s in enumerate(symbols)), None)


def formula_after(molecule):
    result, added = editing.skeleton_hydrogens(molecule)
    return result.formula, added


def test_aromatic_rings_get_one_hydrogen_per_ch():
    assert formula_after(ring('CCCCCC')) == ('C6H6', 6)
    assert formula_after(ring('NCCCCC')) == ('C5H5N', 5)


def test_chains_with_single_and_double_bonds():
    ethanol = Molecule('', (Atom('C', 0, 0, 0), Atom('C', 1.52, 0, 0), Atom('O', 2.0, 1.35, 0)), None)
    assert formula_after(ethanol) == ('C2H6O', 6)
    acetone = Molecule('', (Atom('C', 0, 0, 0), Atom('O', 0, 1.21, 0), Atom('C', 1.30, -0.75, 0), Atom('C', -1.30, -0.75, 0)), None)
    assert formula_after(acetone) == ('C3H6O', 6)
    acid = Molecule('', (Atom('C', 0, 0, 0), Atom('C', 1.50, 0, 0), Atom('O', 2.10, 1.05, 0), Atom('O', 2.20, -1.16, 0)), None)
    assert formula_after(acid) == ('C2H4O2', 4)


def test_new_hydrogens_follow_the_atoms_of_the_file():
    benzene = ring('CCCCCC')
    result, _ = editing.skeleton_hydrogens(benzene)
    assert result.atoms[:6] == benzene.atoms  # the numbers of the file stay (labels, constraints)
    assert all(a.symbol == 'H' for a in result.atoms[6:])
    assert all(abs(a.z) < 1e-6 for a in result.atoms)  # in the plane of the ring


def test_files_with_hydrogens_or_without_organic_atoms_are_left():
    methanol_part = Molecule('', (Atom('C', 0, 0, 0), Atom('O', 1.43, 0, 0), Atom('H', 1.75, 0.9, 0)), None)
    assert editing.skeleton_hydrogens(methanol_part) == (methanol_part, 0)  # one H written: on purpose
    metal = Molecule('', (Atom('Fe', 0, 0, 0),), None)
    assert editing.skeleton_hydrogens(metal) == (metal, 0)
    empty = Molecule('', (), None)
    assert editing.skeleton_hydrogens(empty) == (empty, 0)
    assert editing.skeleton_hydrogens(ring('CCCCCC'), limit=5)[1] == 0  # too big: as it is


def sdf(atoms, bonds):
    text = f'm\n  test\n\n{len(atoms):3d}{len(bonds):3d}  0  0  0  0  0  0  0  0999 V2000\n'
    text += ''.join(f'{x:10.4f}{y:10.4f}{z:10.4f} {e:<3} 0  0  0  0  0  0  0  0  0  0  0  0\n' for e, x, y, z in atoms)
    return text + ''.join(f'{a:3d}{b:3d}{o:3d}  0\n' for a, b, o in bonds) + 'M  END\n'


def hydrogens_on(molecule):
    """{atom: how many H} of the heavy atoms."""
    count = {}
    for i, j, _ in editing.bonds_with_orders(molecule):
        for a, b in ((i, j), (j, i)):
            if molecule.atoms[b].symbol == 'H':
                count[a] = count.get(a, 0) + 1
    return count


def test_bond_orders_written_in_the_file_are_followed():
    # a double bond of the file is kept whatever its length — ethylene with a C=C of
    # 1.50 Å (single by its length) and order 2 in the molfile is C2H4; the same atoms in XYZ (no orders) — by length
    from modules.compass.chemistry import formats

    stretched = formats.read_mol(sdf([('C', 0, 0, 0), ('C', 1.50, 0, 0)], [(1, 2, 2)]))
    assert formula_after(stretched) == ('C2H4', 4)
    assert formula_after(formats.read_xyz('2\n\nC 0 0 0\nC 1.50 0 0\n'))[0] == 'C2H6'
    assert formula_after(formats.read_xyz('2\n\nC 0 0 0\nC 1.33 0 0\n'))[0] == 'C2H4'
    # PDB: a double bond is listed twice in CONECT (acetone C=O)
    pdb = ('HETATM    1  C1  LIG A   1       0.000   0.000   0.000  1.00  0.00           C\n'
           'HETATM    2  O1  LIG A   1       1.230   0.000   0.000  1.00  0.00           O\n'
           'HETATM    3  C2  LIG A   1      -0.750   1.300   0.000  1.00  0.00           C\n'
           'HETATM    4  C3  LIG A   1      -0.750  -1.300   0.000  1.00  0.00           C\n'
           'CONECT    1    2    2    3    4\nCONECT    2    1    1\nCONECT    3    1\nCONECT    4    1\nEND\n')
    assert formula_after(formats.read_pdb(pdb)) == ('C3H6O', 6)


def test_aromatic_bonds_of_a_file_without_hydrogens():
    # aromatic bonds (type 4 of a molfile) of the heavy atoms only: the NH of pyrrole and of imidazole (one N), no H on
    # O and S of furan and thiophene, none on the N of pyridine and pyrimidine
    from modules.compass.chemistry import formats

    def aromatic(symbols, r):
        n = len(symbols)
        atoms = [(s, r * cos(2 * pi * k / n), r * sin(2 * pi * k / n), 0.0) for k, s in enumerate(symbols)]
        return formats.read_mol(sdf(atoms, [(k + 1, (k + 1) % n + 1, 4) for k in range(n)]))

    for symbols, r, formula, on_hetero in (('NCCCC', 1.18, 'C4H5N', {0: 1}), ('NCNCC', 1.18, 'C3H4N2', {0: 0, 2: 1}),
                                           ('OCCCC', 1.18, 'C4H4O', {0: 0}), ('SCCCC', 1.20, 'C4H4S', {0: 0}),
                                           ('NCCCCC', 1.39, 'C5H5N', {0: 0}), ('NCNCCC', 1.39, 'C4H4N2', {0: 0, 2: 0})):
        result, _ = editing.skeleton_hydrogens(aromatic(symbols, r))
        count = hydrogens_on(result)
        assert result.formula == formula, symbols
        assert {k: count.get(k, 0) for k in on_hetero} == on_hetero, symbols
        assert all(count.get(k, 0) == 1 for k, s in enumerate(symbols) if s == 'C'), symbols


def test_small_molecules_without_hydrogens_stay():
    # the user agreed — hydrogens only for an organic skeleton (two bonded carbons); CO from a file was HCO
    line = lambda *atoms: Molecule('', tuple(Atom(s, x, 0, 0) for s, x in atoms), None)
    for molecule in (line(('C', 0), ('O', 1.128)), line(('O', -1.16), ('C', 0), ('O', 1.16)), line(('N', 0), ('N', 1.10)),
                     Molecule('', (Atom('S', 0, 0, 0), Atom('O', 1.43, 0, 0), Atom('O', -0.7, 1.25, 0)), None)):
        assert editing.skeleton_hydrogens(molecule) == (molecule, 0), molecule.formula
    far = line(('C', 0), ('O', 1.43), ('C', 2.86))  # dimethyl ether in an XYZ: no C–C bond — left as well
    assert editing.skeleton_hydrogens(far)[1] == 0
    methanol = Molecule('', (Atom('C', 0, 0, 0), Atom('O', 1.43, 0, 0)), ((0, 1, 1),))  # a MOL/SDF with its bond
    assert editing.skeleton_hydrogens(methanol)[0].formula == 'CH4O'


def test_a_flat_drawing_with_straight_chains_gets_its_hydrogens():
    # a 2D drawing of a cage has CH₂ in
    # straight lines (the bonds of the carbon opposite) and CH with three bonds at 120° — the sum of the bonds is zero;
    # «Направление не определено» left the whole structure without hydrogens. Oracle: the formula by the valences —
    # [2.2.2]cryptand C18H36N2O6 drawn flat: two N bridgeheads, three straight chains N–C–C–O–C–C–O–C–C–N
    from math import dist

    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry.editing import skeleton_hydrogens

    atoms, bonds = [Atom('N', -6.0, 0.0, 0.0), Atom('N', 6.0, 0.0, 0.0)], []
    for y in (-2.0, 0.0, 2.0):  # three straight chains between the two N, every link 1.5 Å along x
        previous = 0
        for k, symbol in enumerate('CCOCCOCC', 1):
            atoms.append(Atom(symbol, -6.0 + 1.5 * k * 12 / 13.5, y if k not in (1, 8) else y / 2, 0.0))
            bonds.append((previous, len(atoms) - 1, 1))
            previous = len(atoms) - 1
        bonds.append((previous, 1, 1))
    made, added = skeleton_hydrogens(Molecule('cryptand', tuple(atoms), tuple(bonds)))
    assert added == 36 and made.formula.replace(' ', '') in ('C18H36N2O6', 'C₁₈H₃₆N₂O₆')
    hydrogens = [a for a in made.atoms if a.symbol == 'H']
    assert all(min(dist(h.position, a.position) for a in made.atoms if a.symbol != 'H') < 1.2 for h in hydrogens)
    # a CH with three bonds at 120° in the plane (isobutane drawn flat): its H out of the plane
    flat = Molecule('isobutane', (Atom('C', 0, 0, 0), Atom('C', 1.5, 0, 0), Atom('C', -0.75, 1.3, 0),
                                  Atom('C', -0.75, -1.3, 0)), ((0, 1, 1), (0, 2, 1), (0, 3, 1)))
    made, added = skeleton_hydrogens(flat)
    assert added == 10


FUSED_CROWN = """
     RDKit          2D

 19 20  0  0  0  0  0  0  0  0999 V2000
    4.5156    4.2079    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    5.3973    2.9943    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    4.7872    1.6240    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.2954    1.4672    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.6073    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    3.2954   -1.4672    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    2.4138   -2.6807    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.1147   -3.4307    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3771   -3.5875    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -1.8037   -3.1240    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -2.9184   -2.1203    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -3.5285   -0.7500    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -3.5285    0.7500    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -2.9184    2.1203    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
   -1.8037    3.1240    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
   -0.3771    3.5875    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    1.1147    3.4307    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
    2.4138    2.6807    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
    3.0239    4.0511    0.0000 C   0  0  0  0  0  0  0  0  0  0  0  0
  1  2  1  0
  2  3  1  0
  3  4  1  0
  4  5  1  0
  5  6  1  0
  6  7  1  0
  7  8  1  0
  8  9  1  0
  9 10  1  0
 10 11  1  0
 11 12  1  0
 12 13  1  0
 13 14  1  0
 14 15  1  0
 15 16  1  0
 16 17  1  0
 17 18  1  0
 18 19  1  0
 19  1  1  0
 18  4  1  0
M  END
"""


def test_the_ring_fusion_of_a_flat_drawing_gets_its_hydrogens_out_of_the_plane():
    # the two CH of the ring fusion have their three bonds in the plane of the drawing; their H went into that plane
    # towards each other (0.07 Å apart, «Два атома расположены ближе 0,1 Å») and the structure was left without any
    # hydrogens. Oracle: the formula of the name — C14H26O5; no two atoms closer than 0.5 Å
    from math import dist

    from modules.compass.chemistry import formats

    made, added = editing.skeleton_hydrogens(formats.read_mol(FUSED_CROWN))
    assert added == 26 and made.formula == 'C14H26O5'
    atoms = made.atoms
    assert min(dist(atoms[i].position, atoms[j].position) for i in range(len(atoms)) for j in range(i)) > 0.5

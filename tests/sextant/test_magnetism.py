"""The magnetic order of a crystal: modules/sextant/magnetism.py and its species in pw.x and CP2K."""

from collections import Counter

import pytest

from modules.compass.chemistry import crystal as cr
from modules.sextant import cp2k_inputs as ci, hubbard, magnetism, qe_inputs as qi
from tests.sextant.test_hubbard import nickel_oxide


def primitive_nio():
    # the primitive fcc cell of rock salt: a/√2 = 4.177/√2 = 2.9536 Å, α = β = γ = 60°; Ni at the node, O at (½, ½, ½)
    return cr.Crystal('NiO', cr.Cell(2.9536, 2.9536, 2.9536, 60, 60, 60),
                      (cr.Site('Ni1', 'Ni', 0, 0, 0), cr.Site('O1', 'O', .5, .5, .5)), (cr.operation('x, y, z'),), 'P 1')


def bcc_iron():
    return cr.Crystal('Fe', cr.Cell(2.87, 2.87, 2.87), (cr.Site('Fe1', 'Fe', 0, 0, 0), cr.Site('Fe2', 'Fe', .5, .5, .5)),
                      (cr.operation('x, y, z'),), 'P 1')


def test_the_two_sublattices():
    # one Ni in the primitive cell — no antiferromagnet in it; 2 × 1 × 1: the copies n₁ = 0 and 1 — the (111) planes
    # n₁ + n₂ + n₃ = 0 and 1 of AFM-II
    with pytest.raises(ValueError):
        magnetism.afm_signs(primitive_nio())
    two = cr.supercell(primitive_nio(), (2, 1, 1))
    atoms = [a for a in cr.unit_cell(two)]
    signs = magnetism.afm_signs(two, (2, 1, 1))
    assert sorted(s for a, s in zip(atoms, signs) if a[0] == 'Ni') == [-1, 1]
    assert all(s == 0 for a, s in zip(atoms, signs) if a[0] == 'O')
    # 2 × 2 × 2: the sign (−1)^(n₁ + n₂ + n₃) — every Ni has its 6 nearest neighbours of the other (111) planes up and
    # down equally: 4 up, 4 down
    eight = cr.supercell(primitive_nio(), (2, 2, 2))
    signs = magnetism.afm_signs(eight, (2, 2, 2))
    ni = [(a, s) for a, s in zip(cr.unit_cell(eight), signs) if a[0] == 'Ni']
    assert Counter(s for _, s in ni) == {1: 4, -1: 4}
    for a, s in ni:
        assert s == (-1) ** round(2 * (a[1] + a[2] + a[3]))  # the copy n_i = 2·x_i of a node of the supercell
    # bcc iron in its cubic cell: the corner and the centre — nearest neighbours, two sublattices (B2 order)
    assert magnetism.afm_signs(bcc_iron()) in ((1, -1), (-1, 1))
    # the Ni of the conventional cell of NiO — fcc, triangles of nearest neighbours: frustrated, a supercell is needed
    with pytest.raises(ValueError):
        magnetism.afm_signs(nickel_oxide())
    with pytest.raises(ValueError):  # nothing magnetic
        magnetism.afm_signs(cr.Crystal('NaCl', cr.Cell(5.64, 5.64, 5.64), (cr.Site('Na1', 'Na', 0, 0, 0),),
                                       (cr.operation('x, y, z'),), 'P 1'))
    assert magnetism.usually_magnetic(['Ni', 'O', 'Zn', 'Ti', 'Fe']) == ['Ni', 'Fe']


def test_the_species_up_and_down():
    two = cr.supercell(primitive_nio(), (2, 1, 1))
    signs = magnetism.afm_signs(two, (2, 1, 1))
    pseudo = {'Ni': ('ni.upf', 45.0, 360.0), 'O': ('O.upf', 50.0, 400.0)}
    text = qi.pw_input(two, 'Энергия', pseudo, options=qi.Options(magnetic=signs, magnetization=0.5,
                                                                    hubbard=hubbard.parse('Ni 6.2')))
    # INPUT_PW: two species of one element (the same file), starting_magnetization by species, nspin = 2; fixed
    # occupations of an insulator with nspin = 2 — tot_magnetization (0: an antiferromagnet)
    assert '  ntyp = 3' in text and '  nspin = 2' in text and '  tot_magnetization = 0' in text
    species = text.split('ATOMIC_SPECIES\n')[1].split('CELL_PARAMETERS')[0]
    assert '  Ni1 58.6930 ni.upf' in species and '  Ni2 58.6930 ni.upf' in species and '  O 15.9990 O.upf' in species
    order = [line.split()[0] for line in species.strip().splitlines()]
    for k, name in enumerate(order, 1):
        expected = {'Ni1': 0.5, 'Ni2': -0.5}.get(name)
        if expected is None:
            assert f'starting_magnetization({k})' not in text
        else:
            assert f'  starting_magnetization({k}) = {expected:g}' in text
    assert text.endswith('HUBBARD (ortho-atomic)\n  U Ni1-3d 6.2\n  U Ni2-3d 6.2\n')
    positions = text.split('ATOMIC_POSITIONS crystal\n')[1].split('K_POINTS')[0]
    assert Counter(line.split()[0] for line in positions.strip().splitlines()) == {'Ni1': 1, 'Ni2': 1, 'O': 2}
    with pytest.raises(ValueError):  # the signs of another cell
        qi.pw_input(primitive_nio(), 'Энергия', pseudo, options=qi.Options(magnetic=signs))
    # CP2K: two kinds of Ni (ELEMENT Ni, MAGNETIZATION ±2), UKS; the U on both
    inp = ci.cp2k_input(two, options=ci.Options(magnetic=signs, hubbard=hubbard.parse('Ni 6.2')))
    assert '    UKS\n' in inp and 'MULTIPLICITY' not in inp
    for name, m in (('Ni1', 2), ('Ni2', -2)):
        block = inp.split(f'    &KIND {name}\n')[1].split('    &END KIND')[0]
        assert ('      ELEMENT Ni\n      BASIS_SET DZVP-MOLOPT-SR-GTH\n      POTENTIAL GTH-PBE\n'
                f'      MAGNETIZATION {m}\n      &DFT_PLUS_U T\n') in block
    coord = inp.split('      SCALED\n')[1].split('    &END COORD')[0]
    assert Counter(line.split()[0] for line in coord.strip().splitlines()) == {'Ni1': 1, 'Ni2': 1, 'O': 2}
    with pytest.raises(ValueError):
        ci.cp2k_input(two, options=ci.Options(magnetic=signs, functional='GFN1-XTB'))

"""Properties read from real ORCA outputs (modules/spectrum/readers/orca_properties.py).

Oracles, independent of the parser:
  * numbers copied by hand from the files (tests/data/orca_cclib, cclib test data; see its README);
  * conservation: the charges add up to the total charge, the spin populations to the number of unpaired
    electrons; tolerance n * 0.5e-6 + 0.5e-6 from the 6 printed decimals of n atoms (Hirshfeld is
    integrated numerically: ORCA itself prints a total of 0.000168 for a neutral molecule, so 1e-3);
  * |mu| in a.u. times ORCA's factor 2.541798 D/(e*bohr) equals its Debye value within the rounding
    of the printed numbers (components 0.5e-5 -> |mu| ~0.9e-5 -> 2.2e-5 D, plus 0.5e-5 D printed): 3e-5 D;
  * chemistry: the water dipole points from O to the hydrogens (mu = sum q r, the H side is positive);
    the dipole of the Mulliken point charges lies along the same C2 axis (cos > 0.99); Mayer orders
    are near 1 for C-H and larger for the vinyl C=C than for the ring bonds;
  * after an optimization the properties are those of the final geometry and the gradient (of the
    previous step) is not returned.
"""

from math import sqrt
from pathlib import Path

import pytest

from modules.spectrum.readers.orca import read_output
from modules.spectrum.readers.orca_properties import DEBYE, read_properties

DATA = Path(__file__).parents[1] / 'data' / 'orca_cclib'
BOHR = 0.529177210544  # A, CODATA 2022 (the value of modules.compass.chemistry.geometry_tools)


def load(name):
    return read_properties((DATA / name).read_text(encoding='utf-8'))


def test_water_values_as_printed():
    p = load('water_mp2_orca5.0.out')
    assert [a.symbol for a in p.geometry.atoms] == ['O', 'H', 'H']
    assert p.charges['mulliken'] == (-0.361723, 0.180857, 0.180866)
    assert p.charges['loewdin'] == (-0.250698, 0.125347, 0.125351)
    assert p.dipole == (0.15024, -0.11207, -0.64976)
    assert p.dipole_debye == 1.71890
    assert p.spins == {} and p.gradient is None


def test_dipole_magnitude_matches_orca_debye_value():
    for name in ('water_mp2_orca5.0.out', 'dvb_sp_un_dft_orca6.0.out'):
        p = load(name)
        magnitude = sqrt(sum(c * c for c in p.dipole))
        assert magnitude * DEBYE == pytest.approx(p.dipole_debye, abs=3e-5)


def test_water_dipole_points_to_the_hydrogens():
    p = load('water_mp2_orca5.0.out')
    o, h1, h2 = (a.position for a in p.geometry.atoms)
    towards_h = [(h1[k] + h2[k]) / 2 - o[k] for k in range(3)]
    mu = p.dipole
    cos = sum(m * t for m, t in zip(mu, towards_h)) / sqrt(sum(m * m for m in mu) * sum(t * t for t in towards_h))
    assert cos > 0.99
    q = p.charges['mulliken']
    point = [sum(q[i] * p.geometry.atoms[i].position[k] / BOHR for i in range(3)) for k in range(3)]
    cos = sum(m * c for m, c in zip(mu, point)) / sqrt(sum(m * m for m in mu) * sum(c * c for c in point))
    assert cos > 0.99


@pytest.mark.parametrize(
    'name, charge, unpaired',
    [('water_mp2_orca5.0.out', 0, 0), ('dvb_sp_un_dft_orca6.0.out', 1, 1), ('dvb_gopt_orca6.0.out', 0, 0)],
)
def test_charges_and_spins_add_up(name, charge, unpaired):
    p = load(name)
    n = len(p.geometry.atoms)
    for key in ('mulliken', 'loewdin'):
        assert sum(p.charges[key]) == pytest.approx(charge, abs=n * 0.5e-6 + 0.5e-6)
        if unpaired:
            assert sum(p.spins[key]) == pytest.approx(unpaired, abs=n * 0.5e-6 + 0.5e-6)
        else:
            assert key not in p.spins
    if 'hirshfeld' in p.charges:
        assert sum(p.charges['hirshfeld']) == pytest.approx(charge, abs=1e-3)


def test_open_shell_cation_spins_and_mayer_orders():
    p = load('dvb_sp_un_dft_orca6.0.out')
    assert p.spins['mulliken'][0] == 0.213760 and p.spins['loewdin'][14] == 0.313396
    assert p.charges['hirshfeld'][0] == pytest.approx(0.0, abs=0.2)
    orders = {(i, j): o for i, j, o in p.mayer_bonds}
    assert orders[(0, 2)] == 1.2632 and orders[(10, 14)] == 1.7047
    symbols = [a.symbol for a in p.geometry.atoms]
    ch = [o for (i, j), o in orders.items() if {symbols[i], symbols[j]} == {'C', 'H'}]
    assert len(ch) == 10 and all(0.9 < o < 1.0 for o in ch)  # 10 C-H bonds in C10H10
    ring = [orders[(0, 2)], orders[(0, 5)], orders[(2, 4)]]
    assert orders[(10, 14)] > max(ring)  # the vinyl double bond
    assert len(p.mayer_valence) == 20 and 3.8 < p.mayer_valence[0] < 4.1 and 0.9 < p.mayer_valence[6] < 1.1


def test_gradient_of_the_only_geometry():
    p = load('dvb_raman_orca6.0.out')
    assert len(p.gradient) == 20
    assert p.gradient[0] == (0.000762832, 0.000179580, 0.000000133)
    # the forces of an isolated molecule add up to zero (translation invariance), printed to 1e-9
    for k in range(3):
        assert sum(g[k] for g in p.gradient) == pytest.approx(0.0, abs=20 * 0.5e-9 + 1e-8)


def test_after_an_optimization_properties_belong_to_the_final_geometry():
    text = (DATA / 'dvb_gopt_orca6.0.out').read_text(encoding='utf-8')
    p = read_properties(text)
    final = text[text.index('FINAL ENERGY EVALUATION AT THE STATIONARY POINT') :]
    row = final[final.index('MULLIKEN ATOMIC CHARGES') :].splitlines()[2]
    assert p.charges['mulliken'][0] == float(row.split(':')[1])
    assert p.gradient is None  # its last gradient belongs to the previous step
    coords = final[final.index('CARTESIAN COORDINATES (ANGSTROEM)') :].splitlines()[2].split()
    assert p.geometry.atoms[0].position == tuple(float(v) for v in coords[1:])


def test_output_carries_the_properties():
    output = read_output((DATA / 'water_mp2_orca5.0.out').read_text(encoding='utf-8'))
    assert output.properties is not None and output.properties.dipole_debye == 1.71890


def test_damaged_blocks_are_skipped_not_guessed():
    text = (DATA / 'water_mp2_orca5.0.out').read_text(encoding='utf-8')
    assert read_properties(text.replace('   1 H :    0.180857', '   1 C :    0.180857')).charges.get('mulliken') is None
    truncated = text.replace('   2 H :    0.180866\n', '')
    assert 'mulliken' not in read_properties(truncated).charges
    assert read_properties('no geometry here') is None


def _moved(molecule, matrix=None, shift=(0.0, 0.0, 0.0), atom_shift=None):
    from azimuth.core import Atom, Molecule
    import numpy as np

    m = np.eye(3) if matrix is None else np.asarray(matrix, float)
    atoms = []
    for k, a in enumerate(molecule.atoms):
        p = np.asarray(a.position) @ m + np.asarray(shift)
        if atom_shift and atom_shift[0] == k:
            p = p + np.asarray(atom_shift[1])
        atoms.append(Atom(a.symbol, *map(float, p)))
    return Molecule('moved', tuple(atoms))


def _rotation():
    import numpy as np

    a, b = 0.7, -1.1  # an arbitrary proper rotation: about z, then about x
    rz = np.array([[np.cos(a), np.sin(a), 0], [-np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(b), np.sin(b)], [0, -np.sin(b), np.cos(b)]])
    return rz @ rx


def test_overlay_follows_a_turned_structure_and_turns_the_vectors():
    import numpy as np
    from modules.compass.view.result_overlay import overlay

    p = load('water_mp2_orca5.0.out')
    turned = _moved(p.geometry, _rotation(), (1.0, -2.0, 0.5))
    shown = overlay(p, turned, {'atom': 'mulliken', 'dipole': True, 'bonds': True})
    assert shown['atom'] == ('mulliken', p.charges['mulliken'])
    expected = np.asarray(p.dipole) @ _rotation()  # oracle: the rotation applied to the structure
    assert np.allclose(shown['dipole'][0], expected, atol=1e-6) and shown['dipole'][1] == 1.71890
    assert shown['bonds'] == list(p.mayer_bonds) and shown['forces'] is None


def test_overlay_refuses_other_structures():
    from modules.compass.view.result_overlay import overlay, match

    from azimuth.core import Atom, Molecule
    from modules.spectrum.readers.orca_properties import Properties

    chiral = Molecule(
        '',
        (
            Atom('C', 0, 0, 0),
            Atom('H', 0, 0, 1.09),
            Atom('F', 1.3, 0, -0.45),
            Atom('Cl', -0.9, 1.5, -0.6),
            Atom('Br', -0.9, -1.6, -0.7),
        ),
    )
    mirror = _moved(chiral, [[1, 0, 0], [0, 1, 0], [0, 0, -1]])
    assert match(Properties(chiral, dipole=(0.1, 0.2, 0.3)), mirror) is None  # wrong handedness
    assert match(Properties(chiral, dipole=(0.1, 0.2, 0.3)), _moved(chiral, _rotation())) is not None
    p = load('water_mp2_orca5.0.out')
    assert overlay(p, _moved(p.geometry, atom_shift=(1, (0.05, 0.0, 0.0))), {'atom': 'mulliken'}) is None
    from azimuth.core import Molecule

    swapped = Molecule('', (p.geometry.atoms[1], p.geometry.atoms[0], p.geometry.atoms[2]))
    assert match(p, swapped) is None
    assert match(p, _moved(p.geometry, atom_shift=(1, (0.003, 0.0, 0.0)))) is not None  # symmetrization noise


def test_forces_are_minus_the_gradient():
    from modules.compass.view.result_overlay import overlay

    p = load('dvb_raman_orca6.0.out')
    shown = overlay(p, p.geometry, {'forces': True})
    assert shown['forces'][0] == pytest.approx(tuple(-g for g in p.gradient[0]), abs=1e-15)


def test_bonds_from_mayer_orders():
    from modules.compass.view.result_overlay import mayer_structure

    p = load('dvb_sp_un_dft_orca6.0.out')
    bonds = {(min(i, j), max(i, j)): o for i, j, o in mayer_structure(p, p.geometry).bonds}
    assert len(bonds) == 20
    ring = [(0, 2), (0, 5), (1, 3), (1, 4), (2, 4), (3, 5)]
    assert all(bonds[b] == 1.5 for b in ring)  # the (quinoid, delocalized) ring of the cation: 1.26 / 1.55
    assert bonds[(10, 14)] == 2 and bonds[(11, 15)] == 2 and bonds[(0, 11)] == 1  # vinyl groups: 1.70, 1.17
    assert sum(1 for o in bonds.values() if o == 1) == 12  # 10 C-H and 2 ring-vinyl bonds


def test_neutral_benzene_ring_becomes_aromatic():
    # Mayer orders of the ring of neutral divinylbenzene are ~1.36-1.47: plain rounding would make all
    # six single; the six-membered-ring rule keeps it aromatic
    from modules.compass.view.result_overlay import mayer_structure

    p = load('dvb_gopt_orca6.0.out')
    ring = {(0, 2), (0, 5), (1, 3), (1, 4), (2, 4), (3, 5)}
    orders = {(min(i, j), max(i, j)): o for i, j, o in p.mayer_bonds}
    assert all(1.3 < orders[b] < 1.5 for b in ring)
    bonds = {(min(i, j), max(i, j)): o for i, j, o in mayer_structure(p, p.geometry).bonds}
    assert all(bonds[b] == 1.5 for b in ring) and (4, 5) not in bonds  # the 0.10 para contact is no bond

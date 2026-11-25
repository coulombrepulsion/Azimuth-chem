"""The bonds of a crystal by QTAIM (modules/spectrum/wavefunction/crystal_aim.py).

Oracle: CsCl computed in CP2K 2026.2 (CELL_OPT, a supercell 3 × 3 × 3 of 54 atoms, PBE-D3(BJ), DZVP-MOLOPT-SR-GTH) and
its critical points found by Multiwfn (2026.10.28, Homebrew, macOS) with the answers of the topology of a
molecule: the bond Cs–Cl at a√3/2 = 3.59 Å (a = 12.4255 / 3 = 4.1418 Å), ρ ≈ 0.0094 a.u., ∇²ρ > 0, H > 0, |V|/G < 1 —
closed shells, an ionic bond; the contacts Cl–Cl and Cs–Cs at a = 4.14 Å. Per atom: 8 Cs–Cl (the cube of the CsCl
structure), 6 Cl–Cl; Multiwfn missed 17 of the 81 points Cs–Cs (4.74 of 6 per Cs), and the sum of Poincaré–Hopf is
exactly 17. The charges (7 → 16 CM5 on the even grid of 0.4 bohr): Hirshfeld Cs +0.299, CM5 +0.547.
"""

from pathlib import Path

import numpy as np

from modules.spectrum.wavefunction import crystal_aim, multiwfn

DATA = Path(__file__).resolve().parents[1] / 'data' / 'multiwfn'


def load():
    cell, atoms = crystal_aim.geometry((DATA / 'crystal_cscl333_geometry.molden').read_text(encoding='utf-8'))
    cps = multiwfn.parse_cps((DATA / 'crystal_topology_cp2k-CsCl-20261112-144541__CPprop.txt').read_text(encoding='utf-8'))
    return cell, atoms, cps


def test_the_geometry_of_the_file_for_multiwfn():
    cell, atoms = load()[:2]
    assert len(atoms) == 54 and sum(s == 'Cs' for s, _ in atoms) == 27
    assert abs(np.linalg.norm(cell[0]) * crystal_aim.BOHR - 12.42552641) < 1e-6


def test_the_kinds_of_bonds_of_cscl():
    cell, atoms, cps = load()
    kinds = crystal_aim.bond_kinds(cps, atoms, cell)
    assert [('–'.join(k.pair), k.length) for k in kinds] == [('Cl–Cs', 3.59), ('Cl–Cl', 4.14), ('Cs–Cs', 4.14)]
    ionic = kinds[0]
    assert abs(ionic.rho - 0.0094) < 2e-4 and ionic.laplacian > 0 and ionic.energy > 0 and ionic.ratio < 1
    assert all(k.nature == 'closed' for k in kinds)
    assert abs(ionic.length - 12.4255264 / 3 * 3 ** 0.5 / 2) < 0.01
    assert ionic.per_atom == {'Cl': 8.0, 'Cs': 8.0} and kinds[1].per_atom == {'Cl': 6.0}
    assert kinds[2].count == 64 and crystal_aim.census(cps, cell) == {'nucleus': 54, 'bond': 361, 'ring': 648, 'cage': 324,
                                                                      'poincare_hopf': 17}
    rows = crystal_aim.table_rows(kinds)
    assert rows[0][0] == 'Cl–Cs' and rows[0][3] == '0.0094' and rows[0][-1] == 'closed'


def test_a_point_twice_on_a_face_is_one():
    cell = np.eye(3) * 10.0
    atoms = [('Na', np.zeros(3)), ('Cl', np.array([5.0, 0, 0]))]
    point = {'kind': 'bond', 'atoms': (0, 1), 'rho': 0.02, 'laplacian': 0.1, 'kinetic': 0.02, 'potential': -0.015,
             'energy': 0.005, 'bohr': np.array([2.5, 0.0, 0.0])}
    again = dict(point, bohr=np.array([2.5, 10.0, 0.0]))  # the same point in the next cell
    other = dict(point, bohr=np.array([7.5, 0.0, 0.0]))  # Cl–Na the other way
    kinds = crystal_aim.bond_kinds([point, again, other], atoms, cell)
    assert len(kinds) == 1 and kinds[0].count == 2 and kinds[0].per_atom == {'Cl': 2.0, 'Na': 2.0}
    assert kinds[0].length == round(5.0 * crystal_aim.BOHR, 2)
    census = crystal_aim.census([point, again, other, dict(point, kind='nucleus', bohr=np.zeros(3))], cell)
    assert census['bond'] == 2 and census['nucleus'] == 1 and census['poincare_hopf'] == -1


def test_the_nature():
    assert crystal_aim.nature(-0.5, -0.3) == 'shared'
    assert crystal_aim.nature(0.1, -0.01) == 'intermediate'
    assert crystal_aim.nature(0.03, 0.001) == 'closed'


def test_the_charges_of_cscl():
    cell, atoms = crystal_aim.geometry((DATA / 'crystal_cscl333_geometry.molden').read_text(encoding='utf-8'))
    charges = crystal_aim.parse_charges((DATA / 'crystal_cm5_a_cp2k-CsCl-20261112-144541.txt').read_text(encoding='utf-8'))
    assert len(charges['cm5']) == len(charges['hirshfeld']) == 54 and abs(sum(charges['cm5'])) < 1e-4
    assert crystal_aim.charge_rows(atoms, charges) == [('Cs', '27', '+0.299', '+0.547', '0.000'),
                                                       ('Cl', '27', '-0.299', '-0.547', '0.000')]
    # the answers of a molecule end at the grid spacing («n» is no number): no table, no charges
    assert crystal_aim.parse_charges((DATA / 'crystal_cm5_cp2k-CsCl-20261112-144541.txt').read_text(encoding='utf-8')) == {}

"""Atomic displacement ellipsoids (modules/compass/chemistry/crystal_adp.py).

Oracles, independent of the tested code:
  * an orthogonal cell: U_cart = diag(U11, U22, U33) with U12 etc. as they are (N A = I there);
  * a monoclinic cell: U_eq of the tensor equals the formula of Fischer & Tillmanns (1988),
    U_eq = 1/3 sum_ij U^ij a*_i a*_j (a_i . a_j), written here from the cell parameters;
  * a twofold axis along b maps U12 and U23 to −U12, −U23 and keeps U11, U22, U33, U13 (the rotation diag(−1, 1, −1));
  * an isotropic atom: a circle of radius 1.5382 sqrt(U_iso) on the screen whatever the view; 1.5382 is the square root
    of the median of chi-square with 3 degrees of freedom (2.3660);
  * B = 8 pi^2 U in the CIF reader.
"""

from math import cos, pi, radians, sin, sqrt

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_adp as adp


def test_orthogonal_and_monoclinic_cells():
    cell = cr.Cell(5, 6, 7)
    u = adp.u_cart(cell, (0.01, 0.02, 0.03, 0.001, 0.002, 0.003))
    expect = [[0.01, 0.001, 0.002], [0.001, 0.02, 0.003], [0.002, 0.003, 0.03]]
    assert all(abs(u[i][j] - expect[i][j]) < 1e-12 for i in range(3) for j in range(3))
    a, b, c, beta = 7.0, 8.0, 9.0, 110.0
    mono = cr.Cell(a, b, c, 90, beta, 90)
    u6 = (0.02, 0.03, 0.025, 0.0, 0.004, 0.0)
    s = sin(radians(beta))
    astar, bstar, cstar = 1 / (a * s), 1 / b, 1 / (c * s)  # monoclinic b-unique reciprocal lengths
    metric = {(0, 0): a * a, (1, 1): b * b, (2, 2): c * c, (0, 2): a * c * cos(radians(beta))}
    stars = (astar, bstar, cstar)
    full = {(0, 0): u6[0], (1, 1): u6[1], (2, 2): u6[2], (0, 2): u6[4]}
    ueq = sum(full[(i, j)] * stars[i] * stars[j] * metric[(i, j)] * (1 if i == j else 2) for (i, j) in full) / 3
    assert abs(adp.u_eq(adp.u_cart(mono, u6)) - ueq) < 1e-12


def test_a_twofold_axis_turns_the_tensor():
    cell = cr.Cell(5, 6, 7)
    site = cr.Site('C1', 'C', 0.1, 0.2, 0.3, 1.0, '', (0.01, 0.02, 0.03, 0.001, 0.002, 0.003), 0.0)
    crystal = cr.Crystal('t', cell, (site,), (cr.operation('x,y,z'), cr.operation('-x,y,-z')))
    (f1, u1), (f2, u2) = adp.tensors(crystal)
    assert abs(u2[0][1] + u1[0][1]) < 1e-12 and abs(u2[1][2] + u1[1][2]) < 1e-12
    assert abs(u2[0][2] - u1[0][2]) < 1e-12 and all(abs(u2[k][k] - u1[k][k]) < 1e-12 for k in range(3))
    found = adp.for_atoms(crystal, [cell.cartesian(f2), cell.cartesian((0.5, 0.5, 0.5))])
    assert found[0] == u2 and found[1] is None


def test_isotropic_circle_and_b_values():
    for basis in (((1, 0, 0), (0, 1, 0), (0, 0, 1)), ((0, 0.6, 0.8), (1, 0, 0), (0, 0.8, -0.6))):
        a, b, _ = adp.ellipse([[0.04, 0, 0], [0, 0.04, 0], [0, 0, 0.04]], basis)
        assert abs(a - 1.5382 * 0.2) < 1e-9 and abs(b - a) < 1e-9
    a, b, angle = adp.ellipse([[0.09, 0, 0], [0, 0.01, 0], [0, 0, 0.04]], ((1, 0, 0), (0, 1, 0), (0, 0, 1)))
    assert abs(a - 1.5382 * 0.3) < 1e-9 and abs(b - 1.5382 * 0.1) < 1e-9 and abs(angle % 180) < 1e-6
    text = ('data_b\n_cell_length_a 5\n_cell_length_b 5\n_cell_length_c 5\nloop_\n_atom_site_label\n_atom_site_fract_x\n'
            '_atom_site_fract_y\n_atom_site_fract_z\n_atom_site_B_iso_or_equiv\nO1 0 0 0 1.5\nH1 0.1 0 0 ?\n'
            'loop_\n_atom_site_aniso_label\n_atom_site_aniso_B_11\n_atom_site_aniso_B_22\n_atom_site_aniso_B_33\n'
            '_atom_site_aniso_B_12\n_atom_site_aniso_B_13\n_atom_site_aniso_B_23\nO1 1.5 1.5 1.5 0 0 0\n')
    c = cr.parse_cif(text)
    assert abs(c.sites[0].u_iso - 1.5 / (8 * pi * pi)) < 1e-12 and abs(c.sites[0].u[0] - 1.5 / (8 * pi * pi)) < 1e-12
    assert c.sites[1].u == () and c.sites[1].u_iso == 0.0
    assert adp.tensors(c)[1][1] is None
    assert abs(sqrt(2.3660) - adp.P50) < 1e-3

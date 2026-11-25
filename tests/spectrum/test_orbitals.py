"""Molecular orbitals without CUBE files: gto.py, orbitals.py, orbital_files.py.

Oracles, independent of the code under test:
  * textbook forms of the real solid harmonics (d0 ~ 2z^2 - x^2 - y^2, ..., g+4 ~ x^4 - 6x^2y^2 + y^4) and
    their orthogonality;
  * overlaps: three-dimensional Gauss-Hermite quadrature of the function values (gto.values_at), exact for
    polynomial times Gaussian integrands — a different route than the analytic formula of gto.overlap;
  * the overlap matrix printed by ORCA (6 decimals: 5e-7) for its own basis;
  * Mulliken charges printed by the programs: ORCA 6.0 (dvb, closed and open shell), Gaussian 16 (Mo4OCl4
    with an ECP; water from the MP2 density stored in the fchk), GAMESS-US 2018 (water, SCF; the Molden
    file was written by the Molden 5.7 program from that output). Tolerance derived from the rounding of
    the printed orbital coefficients (half a unit of the last digit, propagated to first order) plus the
    rounding of the printed charge;
  * the SCF density matrix Gaussian stores in the fchk against the one rebuilt from the orbitals.
Data: cclib test data (BSD-3-Clause), tests/data/orbitals/README.md.
"""

from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import gto
from modules.spectrum.readers.cube import read_cube
from modules.spectrum.readers.orbital_files import _fchk_fields, kind, read_fchk, read_molden, read_orbitals
from modules.spectrum.analysis.orbitals import (
    density_cube,
    grid_for,
    half_unit,
    orbital_cube,
    write_cube,
)

DATA = Path(__file__).parents[1] / 'data' / 'orbitals'


def text(name):
    return (DATA / name).read_text(encoding='utf-8')


# ------------------------------------------------------------------ basis functions


def _proportional(a, b):
    """a = k b with k > 0 (relative 1e-10)."""
    k = (a @ b) / (b @ b)
    return k > 0 and np.max(np.abs(a - k * b)) <= 1e-10 * np.max(np.abs(a))


TEXTBOOK = {
    (2, 0): lambda x, y, z: 2 * z * z - x * x - y * y,
    (2, 1): lambda x, y, z: x * z,
    (2, -1): lambda x, y, z: y * z,
    (2, 2): lambda x, y, z: x * x - y * y,
    (2, -2): lambda x, y, z: x * y,
    (3, 0): lambda x, y, z: z * (2 * z * z - 3 * x * x - 3 * y * y),
    (3, 1): lambda x, y, z: x * (4 * z * z - x * x - y * y),
    (3, -1): lambda x, y, z: y * (4 * z * z - x * x - y * y),
    (3, 2): lambda x, y, z: z * (x * x - y * y),
    (3, -2): lambda x, y, z: x * y * z,
    (3, 3): lambda x, y, z: x * (x * x - 3 * y * y),
    (3, -3): lambda x, y, z: y * (3 * x * x - y * y),
    (4, 4): lambda x, y, z: x**4 - 6 * x * x * y * y + y**4,
    (4, -4): lambda x, y, z: x * y * (x * x - y * y),
    (4, 0): lambda x, y, z: 35 * z**4 - 30 * z * z * (x * x + y * y + z * z) + 3 * (x * x + y * y + z * z) ** 2,
}


def test_solid_harmonics_match_textbook_forms_and_molden_order():
    rng = np.random.default_rng(3)
    points = rng.normal(size=(40, 3))
    for (l, m), form in TEXTBOOK.items():
        terms = gto.solid_harmonic(l, m)
        mine = sum(c * points[:, 0] ** a * points[:, 1] ** b * points[:, 2] ** cz for (a, b, cz), c in terms.items())
        assert _proportional(mine, form(*points.T)), (l, m)
    assert gto.pure_order(3) == (0, 1, -1, 2, -2, 3, -3)
    assert gto.cartesian(2) == ((2, 0, 0), (0, 2, 0), (0, 0, 2), (1, 1, 0), (1, 0, 1), (0, 1, 1))


def _gauss_hermite_overlap(sa, sb, ra, rb, nodes=12):
    """Integral of phi_i(a) phi_j(b) for single-primitive shells, by quadrature of their values."""
    a, b = sa.exponents[0], sb.exponents[0]
    p = a + b
    centre = (a * np.asarray(ra) + b * np.asarray(rb)) / p
    u, w = np.polynomial.hermite.hermgauss(nodes)
    grid = np.array(np.meshgrid(u, u, u, indexing='ij')).reshape(3, -1).T
    weight = np.prod(np.array(np.meshgrid(w, w, w, indexing='ij')).reshape(3, -1), axis=0)
    points = centre + grid / np.sqrt(p)
    centres = np.array([ra, rb])
    result = np.zeros((sa.size, sb.size))
    for i in range(sa.size):
        vi = gto.values_at([sa], centres, np.eye(sa.size)[i], points)
        for j in range(sb.size):
            vj = gto.values_at(
                [gto.Shell(1, sb.l, sb.pure, sb.exponents, sb.coefficients)], centres, np.eye(sb.size)[j], points
            )
            # the integrand divided by the weight exp(-|u|^2) is a polynomial: exact
            result[i, j] = np.sum(weight * vi * vj * np.exp(np.sum(grid * grid, axis=1))) / p**1.5
    return result


@pytest.mark.parametrize('l', [0, 1, 2, 3, 4, 5])
def test_normalized_functions_and_overlaps_against_quadrature(l):
    ra, rb = np.array([0.1, -0.2, 0.3]), np.array([0.9, 0.4, -0.5])
    for pure in (False, True) if l < 5 else (True,):
        if l == 0 and pure:
            continue
        sa = gto.Shell(0, l, pure, [0.8], [1.0])
        sb = gto.Shell(0, 2, True, [0.45], [1.0])
        own = gto.overlap([sa], [ra])
        assert np.allclose(own, np.eye(sa.size), atol=1e-12) if pure or l <= 1 else np.allclose(np.diag(own), 1.0)
        quadrature = _gauss_hermite_overlap(sa, sb, ra, rb)
        analytic = gto.overlap([sa, gto.Shell(1, 2, True, [0.45], [1.0])], [ra, rb])[: sa.size, sa.size :]
        assert np.max(np.abs(quadrature - analytic)) < 1e-11, (l, pure)
        assert np.allclose(_gauss_hermite_overlap(sa, sa, ra, ra), own, atol=1e-11)
        assert np.allclose(gto.overlap_by_pairs([sa, sb], [ra, rb]), gto.overlap([sa, sb], [ra, rb]), atol=1e-14)


def test_contraction_norm_and_grid_values():
    shell = gto.Shell(0, 2, True, [3.0, 0.7, 0.2], [0.3, 0.5, 0.4])
    s = gto.overlap([shell], [[0, 0, 0]])
    assert np.allclose(np.diag(s), shell.contraction_norm(), rtol=1e-13)
    shells = [shell, gto.Shell(1, 1, False, [1.1, 0.3], [0.6, 0.5]), gto.Shell(0, 4, True, [0.5], [1.0])]
    centres = np.array([[0.0, 0.0, 0.0], [1.2, -0.4, 0.3]])
    vector = np.random.default_rng(5).normal(size=sum(x.size for x in shells))
    origin, step, shape = np.array([-4.0, -4.5, -4.2]), np.array([0.3, 0.35, 0.32]), (30, 28, 29)
    field = gto.on_grid(shells, centres, vector, origin, step, shape)
    idx = np.random.default_rng(6).integers(0, shape, size=(80, 3))
    direct = gto.values_at(shells, centres, vector, origin + idx * step)
    assert np.max(np.abs(field[tuple(idx.T)] - direct)) < 1e-9 * np.max(np.abs(direct))


# ------------------------------------------------------------------ the readers


def _mulliken_bound(orbital_set, half_units):
    """First-order bound of the Mulliken charges from the rounding of the printed coefficients."""
    c = orbital_set.coefficients
    n = np.array([o.occupation for o in orbital_set.orbitals])
    s = np.abs(orbital_set.overlap())
    dp = (half_units * n) @ np.abs(c).T
    dp = dp + dp.T
    owners = np.concatenate([[x.centre] * x.size for x in orbital_set.shells])
    per_function = np.sum(dp * s, axis=1)
    return np.array([per_function[owners == a].sum() for a in range(len(orbital_set.charges))])


def _orca_units(orbital_set):
    return np.full(orbital_set.coefficients.shape, 5e-7)  # ORCA prints %10.6f


def _printed(block_text, column):
    return np.array([float(line.split(':')[1].split()[column]) for line in block_text])


def test_orca_output_basis_overlap_and_mulliken():
    out = text('dvb_sp_dft_orca6.0.out')
    assert kind(out) == 'orca'
    found = read_orbitals(out)
    assert found.source == 'ORCA' and found.convention == 'ORCA' and not found.unrestricted
    assert len(found.orbitals) == 60 and sum(s.size for s in found.shells) == 60
    homo, lumo = found.frontier()
    assert (found.orbitals[homo].number, found.orbitals[lumo].number) == (35, 36)  # 70 electrons
    # ORCA's printed overlap matrix (its order: per atom s..., p as z, x, y)
    lines = out.splitlines()
    start = next(k for k, line in enumerate(lines) if line.strip() == 'OVERLAP MATRIX') + 2
    printed = np.zeros((60, 60))
    k = start
    while k < len(lines) and lines[k].split() and all(x.isdigit() for x in lines[k].split()):
        columns = [int(x) for x in lines[k].split()]
        for row in range(60):
            values = lines[k + 1 + row].split()[1:]
            printed[row, columns] = [float(v) for v in values]
        k += 61
    order = []
    offset = 0
    for shell in found.shells:  # my order x, y, z for p; ORCA's z, x, y
        order.extend([offset] if shell.l == 0 else [offset + 2, offset, offset + 1])
        offset += shell.size
    mine = found.overlap()[np.ix_(order, order)]
    # ORCA used unrounded coordinates; the output prints them to 1e-6 A: their rounding (5e-7 A) moves S by
    # at most sum over coordinates of |dS/dx| * 5e-7 A (central differences, h = 1e-4 bohr)
    from modules.compass.chemistry.geometry_tools import BOHR

    moved = np.zeros_like(mine)
    for atom in range(len(found.centres)):
        for axis in range(3):
            shift = np.zeros_like(found.centres)
            shift[atom, axis] = 1e-4
            derivative = (
                gto.overlap(found.shells, found.centres + shift) - gto.overlap(found.shells, found.centres - shift)
            ) / 2e-4
            moved += np.abs(derivative[np.ix_(order, order)]) * 5e-7 / BOHR
    assert np.all(np.abs(mine - printed) <= 5e-7 + moved + 1e-9)
    assert np.max(moved) < 2e-6
    start = next(k for k, line in enumerate(lines) if line.strip() == 'MULLIKEN ATOMIC CHARGES') + 2
    charges = _printed(lines[start : start + 20], 0)
    bound = _mulliken_bound(found, _orca_units(found)) + 5e-7
    assert np.all(np.abs(found.mulliken() - charges) <= bound)
    assert np.max(bound) < 1e-4  # the check is not vacuous


def test_orca_unrestricted_orbitals_and_spin():
    out = text('dvb_sp_un_dft_orca6.0.out')
    found = read_orbitals(out)
    assert found.unrestricted
    alpha = [o for o in found.orbitals if o.spin == 'alpha']
    beta = [o for o in found.orbitals if o.spin == 'beta']
    assert len(alpha) == len(beta) == 60
    assert sum(o.occupation for o in alpha) == 35 and sum(o.occupation for o in beta) == 34  # the cation
    lines = out.splitlines()
    start = next(k for k, line in enumerate(lines) if line.startswith('MULLIKEN ATOMIC CHARGES AND SPIN')) + 2
    charges = _printed(lines[start : start + 20], 0)
    spins = _printed(lines[start : start + 20], 1)
    bound = _mulliken_bound(found, _orca_units(found)) + 5e-7
    assert np.all(np.abs(found.mulliken() - charges) <= bound)
    from dataclasses import replace

    only = lambda spin: replace(  # noqa: E731
        found,
        orbitals=tuple(replace(o, occupation=o.occupation if o.spin == spin else 0.0) for o in found.orbitals),
    )
    spin_population = (np.array(found.charges) - only('alpha').mulliken()) - (
        np.array(found.charges) - only('beta').mulliken()
    )
    assert np.all(np.abs(spin_population - spins) <= bound + 5e-7)
    homo_a, lumo_a = found.frontier('alpha')
    homo_b, lumo_b = found.frontier('beta')
    assert found.orbitals[homo_a].number == 35 and found.orbitals[homo_b].number == 34


def test_gaussian_fchk_with_ecp_and_d_functions():
    fchk = text('Mo4OCl4-sp_g16.fchk')
    assert kind(fchk) == 'fchk'
    found = read_fchk(fchk)
    assert found.convention == 'standard' and any(s.pure and s.l == 2 for s in found.shells)
    assert found.charges[0] == 14.0  # Mo with a 28-electron core potential: Nuclear charges in the fchk
    gaussian = np.array([0.623379, -0.466090, -0.539319, -0.539322, -0.539326, -0.539322])  # Mo4OCl4-sp.log
    bound = _mulliken_bound(found, _fchk_units(fchk, found)) + 5e-7
    assert np.all(np.abs(found.mulliken() - gaussian) <= bound)


def _fchk_units(fchk, found):
    tokens = _fchk_fields(fchk)['Alpha MO coefficients'][1]
    return np.full(found.coefficients.shape, max(half_unit(t) for t in tokens))


def test_gaussian_fchk_density_and_mp2_charges():
    fchk = text('water_mp2_g16.fchk')
    found = read_fchk(fchk)
    fields = _fchk_fields(fchk)
    n = sum(s.size for s in found.shells)

    def square(name):
        packed = fields[name][0]
        m = np.zeros((n, n))
        m[np.tril_indices(n)] = packed
        return m + np.tril(m, -1).T

    occupations = np.array([o.occupation for o in found.orbitals])
    rebuilt = (found.coefficients * occupations) @ found.coefficients.T
    assert np.max(np.abs(rebuilt - square('Total SCF Density'))) < 1e-7
    # Mulliken charges of the MP2 density with the overlap computed here: Gaussian prints -0.319889 (O)
    mp2 = square('Total MP2 Density')
    population = np.einsum('ij,ji->i', mp2, found.overlap())
    owners = np.concatenate([[s.centre] * s.size for s in found.shells])
    charges = np.array(found.charges) - np.array([population[owners == a].sum() for a in range(3)])
    assert np.allclose(charges, [-0.319889, 0.159944, 0.159944], atol=1e-6)


def test_molden_written_by_molden_from_gamess():
    molden = text('molden5.7_water_mp2.molden')
    found = read_molden(molden)
    assert found.convention == 'standard' and found.source == 'Molden'
    homo, lumo = found.frontier()
    assert (found.orbitals[homo].number, found.orbitals[lumo].number) == (5, 6)
    # GAMESS-US 2018 water_mp2.out, SCF density: O -0.339215, H 0.169607 (6 decimals in the Molden file)
    units = np.full(found.coefficients.shape, 1e-6)  # 6 decimals; Molden 5.7 truncates: a whole unit
    bound = _mulliken_bound(found, units) + 5e-7
    gamess = np.array([-0.339215, 0.169607, 0.169607])
    assert np.all(np.abs(found.mulliken() - gamess) <= bound)
    fchk = read_fchk(text('water_mp2_g16.fchk'))  # the same molecule and basis from Gaussian
    assert np.allclose(fchk.mulliken(), found.mulliken(), atol=2e-4)


def test_unrestricted_molden_and_orca_convention_detected():
    found = read_molden(text('molden5.7_dvb_un_sp.molden'))
    assert found.unrestricted and found.convention == 'standard'
    assert np.isclose(np.sum(found.mulliken()), 1.0, atol=1e-5)  # the cation
    # the same file rewritten as orca_2mkl writes s and p (coefficients times the primitive norm)
    from modules.spectrum.analysis.orbitals import ORCA_POWERS, cartesian_norm

    lines = text('molden5.7_water_mp2.molden').splitlines()
    out, shell = [], None
    for line in lines:
        f = line.split()
        if len(f) == 3 and f[0] in ('s', 'p') and f[1].isdigit():
            shell = 'sp'.index(f[0])
            out.append(line)
            continue
        if shell is not None and len(f) == 2 and 'e' in f[0]:
            alpha, c = float(f[0]), float(f[1])
            out.append(f'{alpha:.9e} {c * cartesian_norm(alpha, ORCA_POWERS[shell]):.9e}')
            continue
        if not f or f[0].startswith('['):
            shell = None
        out.append(line)
    orca = read_molden('\n'.join(out))
    assert orca.convention == 'ORCA'
    assert np.allclose(orca.mulliken(), read_molden(text('molden5.7_water_mp2.molden')).mulliken(), atol=1e-6)


def test_wrong_coefficients_are_refused():
    lines = text('molden5.7_water_mp2.molden').splitlines()
    start = lines.index('[MO]')
    broken = lines[: start + 1] + [
        (
            f'{line.split()[0]} {float(line.split()[1]) * 1.05:.6f}'
            if len(line.split()) == 2 and line.split()[0].isdigit()
            else line
        )
        for line in lines[start + 1 :]
    ]
    with pytest.raises(ValueError, match='not orthonormal'):
        read_molden('\n'.join(broken))
    with pytest.raises(ValueError):
        read_orbitals('just text')
    with pytest.raises(ValueError, match='p_basis'):
        read_orbitals(text('dvb_sp_dft_orca6.0.out').replace('BASIS SET IN INPUT FORMAT', 'BASIS SET (hidden)'))


def test_half_unit():
    assert half_unit('0.123456') == pytest.approx(5e-7)
    assert half_unit('-9.94562843E-01') == pytest.approx(5e-10)
    assert half_unit('1.2D+02') == pytest.approx(5.0)


# ------------------------------------------------------------------ fields and CUBE


def test_orbital_cube_values_norm_and_round_trip(tmp_path):
    found = read_molden(text('molden5.7_water_mp2.molden'))
    homo, _ = found.frontier()
    cube = orbital_cube(found, homo, step=0.12)
    origin, step, shape = grid_for(found, 0.12)
    assert cube.values.shape == (*shape, 1)
    from modules.compass.chemistry.geometry_tools import BOHR

    volume = np.prod(step)
    # a valence orbital on a 0.12 A grid with 4 A of margin: the integral of psi^2 within 1 %
    assert np.sum(cube.values**2) * volume == pytest.approx(1.0, rel=0.01)
    idx = np.random.default_rng(2).integers(0, shape, size=(40, 3))
    direct = gto.values_at(found.shells, found.centres, found.coefficients[:, homo], origin + idx * step)
    assert np.max(np.abs(cube.values[..., 0][tuple(idx.T)] - direct)) < 1e-12
    written = tmp_path / 'homo.cube'
    write_cube(cube, written)
    again = read_cube(written.read_text(encoding='utf-8'))
    assert again.values.shape == cube.values.shape
    assert np.allclose(again.values, cube.values, rtol=1e-5, atol=1e-10)  # %13.5E
    assert np.allclose(again.origin, cube.origin, atol=1e-6 * BOHR) and np.allclose(again.axes, cube.axes, atol=1e-6)
    assert [a.symbol for a in again.molecule.atoms] == ['O', 'H', 'H']
    density = density_cube(found, step=0.2)
    assert np.all(density.values >= 0)
    with pytest.raises(ValueError):
        grid_for(found, 0.001)
    big = grid_for(found, 0.02, max_points=100_000)
    assert np.prod(big[2]) <= 100_000


def test_mulliken_spin_populations_are_those_of_orca():
    # the spin populations made from the α and β orbitals of the UKS divinylbenzene cation are ORCA's own
    # «MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS» (the same excerpt), and they add up to Nα − Nβ = 1
    import re

    from modules.spectrum.readers.orbital_files import read_orbitals

    text = (Path(__file__).parents[1] / 'data' / 'orbitals' / 'dvb_sp_un_dft_orca6.0.out').read_text(encoding='utf-8')
    block = text.split('MULLIKEN ATOMIC CHARGES AND SPIN POPULATIONS', 1)[1]
    printed = [float(m.group(1)) for m in re.finditer(r'^\s*\d+\s+[A-Z][a-z]?\s*:\s*\S+\s+(\S+)\s*$', block, re.M)]
    orbitals = read_orbitals(text)
    spins = orbitals.mulliken_spins()
    assert len(printed) == len(spins) == 20
    assert np.allclose(spins, printed, atol=2e-6) and abs(spins.sum() - 1.0) < 1e-4
    closed = read_orbitals((Path(__file__).parents[1] / 'data' / 'orbitals' / 'dvb_sp_dft_orca6.0.out').read_text(encoding='utf-8'))
    assert np.allclose(closed.mulliken_spins(), 0.0)

"""MOPAC orbitals from .aux: Slater functions as fitted Gaussians, checked against what MOPAC itself printed.

Oracles: the overlap matrix MOPAC 23.2.5 wrote into the .aux (its own Slater integrals), its Coulson charges
(ATOM_CHARGES), its orbital energies and occupations; the Slater functions themselves by direct radial quadrature.
"""

from math import factorial, gamma, sqrt
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis.gto import Shell, overlap
from modules.spectrum.readers.mopac import read_aux
from modules.spectrum.readers.mopac_orbitals import (HARTREE_EV, TOLERANCE, _lower_triangle, has_orbitals,
                                              read_mopac_orbitals)
from modules.spectrum.readers.orbital_files import kind, read_orbitals
from modules.spectrum.analysis.sto_fits import ERRORS, FITS

DATA = Path(__file__).parents[1] / 'data' / 'mopac'


def aux(name):
    return (DATA / f'{name}.aux').read_text(encoding='utf-8')


def test_every_fit_is_normalized_and_close_to_its_slater_function():
    # radial quadrature on a uniform grid in r (not the log grid of tools/fit_sto.py)
    r = np.linspace(1e-6, 60.0, 600001)
    dr = r[1] - r[0]
    for (n, l), (exponents, coefficients) in FITS.items():
        shell = Shell(0, l, False, exponents, coefficients)
        assert shell.contraction_norm() == pytest.approx(1.0, abs=1e-10), (n, l)
        sto = 2 ** (n + 0.5) / sqrt(factorial(2 * n)) * r ** (n - 1) * np.exp(-r)
        a = np.asarray(exponents)
        norms = np.sqrt(2 * (2 * a) ** (l + 1.5) / gamma(l + 1.5))
        gauss = (np.asarray(coefficients) * norms) @ np.exp(-np.outer(a, r * r)) * r**l
        assert np.sum(sto * sto * r * r) * dr == pytest.approx(1.0, abs=1e-6)
        found = np.sum(sto * gauss * r * r) * dr
        assert 1 - found < 2e-6 and 1 - found == pytest.approx(ERRORS[(n, l)], abs=1e-6), (n, l)


def test_water_reproduces_the_overlap_charges_and_levels_of_mopac():
    text = aux('h2o_pm7_opt')
    assert has_orbitals(text) and kind(text) == 'mopac'
    o = read_orbitals(text)
    assert o.zdo and o.source == 'MOPAC PM7' and not o.unrestricted
    assert o.deviation < 5e-4  # MOPAC prints its Slater overlaps with 4 decimals
    assert [x.number for x in o.orbitals] == [1, 2, 3, 4, 5, 6]
    assert [x.occupation for x in o.orbitals] == [2, 2, 2, 2, 0, 0]
    assert o.orbitals[0].energy == pytest.approx(-29.615 / HARTREE_EV) and o.orbitals[0].symmetry == '1a1'
    assert o.frontier() == (3, 4)
    c = o.coefficients
    assert np.max(np.abs(c.T @ c - np.eye(6))) < 1e-3  # NDDO: orthonormal with the unit metric
    printed = [float(x) for x in read_aux(text)['ATOM_CHARGES'][-1][1]]
    assert tuple(o.mulliken()) == pytest.approx(printed, abs=1e-3)  # Coulson charges
    assert o.charges == (6.0, 1.0, 1.0)
    assert o.molecule.atoms[1].y == pytest.approx(0.7598)  # ATOM_X_OPT, the geometry of the orbitals


def test_the_overlap_is_checked_element_by_element():
    text = aux('ch2o_am1_1scf')
    o = read_mopac_orbitals(text)
    printed = [float(x) for x in read_aux(text)['OVERLAP_MATRIX'][-1][1]]
    theirs = _lower_triangle(printed, 10)
    # the shell order of Azimuth is the MOPAC order for s and p
    assert np.max(np.abs(o.overlap() - theirs)) == pytest.approx(o.deviation)
    assert o.deviation < 5e-4 and o.source == 'MOPAC AM1'


def test_benzene_has_the_printed_window_of_orbitals():
    o = read_mopac_orbitals(aux('c6h6_pm7_opt'))
    assert [x.number for x in o.orbitals] == list(range(6, 26))  # SET_OF_MOS 6 25: 10 on either side
    homo, lumo = o.frontier()
    assert o.orbitals[homo].number in (14, 15) and o.orbitals[lumo].number == 16  # e1g: 14 and 15 degenerate
    assert o.orbitals[8].energy == pytest.approx(o.orbitals[9].energy)
    assert o.coefficients.shape == (30, 20) and o.deviation < 5e-4


def test_radical_has_alpha_and_beta_orbitals():
    text = aux('ch3_pm7_uhf_doublet_opt')
    o = read_mopac_orbitals(text)
    assert o.unrestricted
    assert sum(x.occupation for x in o.orbitals if x.spin == 'alpha') == 4
    assert sum(x.occupation for x in o.orbitals if x.spin == 'beta') == 3
    printed = [float(x) for x in read_aux(text)['ATOM_CHARGES'][-1][1]]
    assert tuple(o.mulliken()) == pytest.approx(printed, abs=1e-3)


def test_two_jobs_take_the_orbitals_of_the_last():
    o = read_mopac_orbitals(aux('h2o_pm7_opt_then_force_oldgeo'))
    assert len(o.orbitals) == 6 and o.deviation < 5e-4


def test_an_orbital_on_a_grid_is_close_to_normalized():
    from modules.spectrum.analysis.orbitals import orbital_cube

    o = read_mopac_orbitals(aux('h2o_pm7_opt'))
    cube = orbital_cube(o, 3, step=0.12, margin=5.0)
    from modules.compass.chemistry.geometry_tools import BOHR

    volume = abs(np.linalg.det(np.asarray(cube.axes) / BOHR))
    norm = float(np.sum(cube.values[..., 0] ** 2) * volume)
    c = o.coefficients[:, 3]
    assert norm == pytest.approx(float(c @ o.overlap() @ c), abs=5e-3)  # grid and analytic overlap agree
    assert 0.8 < norm < 1.2  # ZDO orbitals are not exactly normalized in the Slater metric


def _synthetic_h2s(flip):
    """A .aux of H2S with s, p, d on S whose printed overlap is our own with the sign of `flip` d labels changed."""
    labels = ['S', 'PX', 'PY', 'PZ', 'X2', 'XZ', 'Z2', 'YZ', 'XY', 'S', 'S']
    owners = [1] * 9 + [2, 3]
    zetas = [2.2, 2.0, 2.0, 2.0, 1.5, 1.5, 1.5, 1.5, 1.5, 1.2, 1.2]
    pqn = [3, 3, 3, 3, 3, 3, 3, 3, 3, 1, 1]
    xyz = [0.0, 0.0, 0.1, 0.45, 0.85, -0.83, -0.62, -0.74, -0.80]  # not planar: every d type overlaps a hydrogen
    from modules.compass.chemistry.geometry_tools import BOHR
    from modules.spectrum.readers.mopac_orbitals import D_ORDER

    centres = np.array(xyz).reshape(3, 3) / BOHR
    shells = [Shell(0, 0, False, np.array(FITS[(3, 0)][0]) * 2.2**2, FITS[(3, 0)][1]),
              Shell(0, 1, False, np.array(FITS[(3, 1)][0]) * 4.0, FITS[(3, 1)][1]),
              Shell(0, 2, True, np.array(FITS[(3, 2)][0]) * 2.25, FITS[(3, 2)][1]),
              Shell(1, 0, False, np.array(FITS[(1, 0)][0]) * 1.44, FITS[(1, 0)][1]),
              Shell(2, 0, False, np.array(FITS[(1, 0)][0]) * 1.44, FITS[(1, 0)][1])]
    ours = overlap(shells, centres)  # shell order: s, px py pz, z2 xz yz x2 xy, s, s
    shell_index = [0, 1, 2, 3] + [4 + D_ORDER.index(x) for x in labels[4:9]] + [9, 10]
    sign = np.array([-1.0 if labels[k] in flip else 1.0 for k in range(11)])
    theirs = ours[np.ix_(shell_index, shell_index)] * np.outer(sign, sign)
    triangle = [f'{theirs[i, j]:.4f}' for i in range(11) for j in range(i + 1)]
    vectors = ' '.join('1.0' if i == j else '0.0' for j in range(11) for i in range(11))
    return '\n'.join([
        ' START OF MOPAC FILE', ' METHOD=PM7', ' ATOM_EL[03]=', '  S  H  H', ' ATOM_CORE[03]=', '  6  1  1',
        ' ATOM_X_OPT:ANGSTROMS[09]=', ' ' + ' '.join(map(str, xyz)),
        ' AO_ATOMINDEX[11]=', ' ' + ' '.join(map(str, owners)), ' ATOM_SYMTYPE[11]=', ' ' + ' '.join(labels),
        ' AO_ZETA[11]=', ' ' + ' '.join(map(str, zetas)), ' ATOM_PQN[11]=', ' ' + ' '.join(map(str, pqn)),
        f' OVERLAP_MATRIX[{len(triangle)}]=', ' #  Lower half triangle only', ' ' + ' '.join(triangle),
        ' SET_OF_MOS=       1      11', ' EIGENVECTORS[121]=', ' ' + vectors,
        ' EIGENVALUES[11]=', ' ' + ' '.join(['-10.0'] * 11),
        ' MOLECULAR_ORBITAL_OCCUPANCIES[00011]=', ' ' + ' '.join(['2.0'] * 4 + ['0.0'] * 7), ' END OF MOPAC FILE', '',
    ]), labels


def test_the_sign_of_d_functions_follows_the_printed_overlap():
    from modules.spectrum.readers.mopac_orbitals import D_ORDER

    for flip in ((), ('XZ',), ('X2', 'XY'), ('Z2', 'YZ', 'XZ')):
        text, labels = _synthetic_h2s(flip)
        o = read_mopac_orbitals(text)
        assert o.deviation < 1e-4, flip
        # orbital k is the k-th MOPAC function: its coefficient sits at the shell position, flipped when asked
        for k, label in enumerate(labels[4:9], 4):
            row = 4 + D_ORDER.index(label)
            assert o.coefficients[row, k] == (-1.0 if label in flip else 1.0), (flip, label)


def test_a_wrong_overlap_refuses_the_file():
    text, _ = _synthetic_h2s(())
    lines = text.splitlines()
    k = lines.index(' AO_ZETA[11]=') + 1
    lines[k] = ' 2.2 2.0 2.0 2.0 1.5 1.5 1.5 1.5 1.5 1.6 1.6'  # other hydrogen exponents than the overlap was made with
    with pytest.raises(ValueError) as error:
        read_mopac_orbitals('\n'.join(lines))
    assert 'overlap' in str(error.value) and TOLERANCE > 0


def test_files_without_orbitals_are_refused():
    text = aux('h2o_pm7_opt')
    cut = text[:text.index(' EIGENVECTORS')] + ' END OF MOPAC FILE\n'
    assert not has_orbitals(cut)
    with pytest.raises(ValueError):
        read_mopac_orbitals(cut)


def test_spectrum_finds_the_aux_next_to_the_output():
    pytest.importorskip('PySide6')
    from modules.spectrum.workspace import SpectrumWorkspace

    found = SpectrumWorkspace.find_molden(DATA / 'h2o_pm7_opt.out')
    assert found == DATA / 'h2o_pm7_opt.aux'


def test_d_functions_reproduce_mopac():
    # MOPAC 23.2.5, PM7 (the user's computer): d on S (H2S, SO2), on Ti and Cl (TiCl4) — the unit-normalized
    # real harmonics of gto.py with their signs reproduce the printed overlaps; no d type is flipped
    from modules.spectrum.readers.mopac_orbitals import _check, _basis, _blocks, _get, _items

    for name, nd in (('h2s_pm7_opt', 5), ('so2_pm7_opt', 5), ('ticl4_pm7_opt', 25)):
        text = aux(name)
        o = read_mopac_orbitals(text)
        assert o.deviation < 5e-4, name
        assert sum(s.size for s in o.shells if s.l == 2) == nd
        items = _items(_blocks(text)[-1])
        shells, order, _ = _basis(items, o.centres)
        signs, _ = _check(shells, o.centres, order, _get(items, 'OVERLAP_MATRIX'))
        assert np.all(signs == 1.0), name
        printed = [float(x) for x in read_aux(text)['ATOM_CHARGES'][-1][1]]
        assert tuple(o.mulliken()) == pytest.approx(printed, abs=1e-3), name


def test_orbitals_below_the_printed_window_come_from_the_density_matrix():
    # benzene: MOPAC prints 6-25, TiCl4 7-26; the occupied ones below are rebuilt from TOTAL_DENSITY_MATRIX, so the
    # density holds every electron and the Coulson charges are MOPAC's
    for name, missing, electrons in (('c6h6_pm7_opt', 5, 30.0), ('ticl4_pm7_opt', 6, 32.0)):
        text = aux(name)
        o = read_mopac_orbitals(text)
        assert o.unlisted is not None and o.unlisted[0].shape[1] == missing
        assert o.unlisted[1].tolist() == [2.0] * missing
        columns, weights = o.occupied()
        assert weights.sum() == pytest.approx(electrons)
        assert np.max(np.abs(columns.T @ columns - np.eye(columns.shape[1]))) < 2e-3  # one orthonormal set
        printed = [float(x) for x in read_aux(text)['ATOM_CHARGES'][-1][1]]
        assert tuple(o.mulliken()) == pytest.approx(printed, abs=1e-3), name
    assert read_mopac_orbitals(aux('h2o_pm7_opt')).unlisted is None
    text = aux('c6h6_pm7_opt')
    cut = text[:text.index(' TOTAL_DENSITY_MATRIX')] + text[text.index(' M.O.SYMMETRY_LABELS'):]
    with pytest.raises(ValueError) as error:
        read_mopac_orbitals(cut)
    assert 'MOS=99999' in str(error.value)

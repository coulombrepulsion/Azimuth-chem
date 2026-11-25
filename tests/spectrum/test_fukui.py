"""The condensed Fukui functions and the global indices (modules/spectrum/analysis/fukui.py).

The algebra of §2 on numbers chosen so that the sums are exact; the Hirshfeld charges themselves come from Multiwfn
(tests/spectrum/test_multiwfn_populations.py — the same run_hirshfeld).
"""

import pytest

from modules.spectrum.analysis import fukui


def test_the_three_states():
    assert fukui.states(0, 1) == [('n', 0, 1), ('anion', -1, 2), ('cation', 1, 2)]
    assert fukui.states(0, 2) == [('n', 0, 2), ('anion', -1, 1), ('cation', 1, 1)]  # a radical: the low spin
    assert fukui.states(1, 3) == [('n', 1, 3), ('anion', 0, 2), ('cation', 2, 2)]


def test_condensed_functions_add_up():
    # formaldehyde-like: the added electron goes mostly to C, the removed one from O
    q_n = (-0.30, 0.10, 0.10, 0.10)
    q_anion = (-0.50, -0.30, -0.10, -0.10)
    q_cation = (0.30, 0.30, 0.20, 0.20)
    found = fukui.condensed(q_n, q_anion, q_cation)
    assert found['plus'] == pytest.approx((0.20, 0.40, 0.20, 0.20))
    assert found['minus'] == pytest.approx((0.60, 0.20, 0.10, 0.10))
    assert sum(found['plus']) == pytest.approx(1) and sum(found['minus']) == pytest.approx(1)
    assert found['zero'] == pytest.approx((0.40, 0.30, 0.15, 0.15))
    assert found['dual'] == pytest.approx((-0.40, 0.20, 0.10, 0.10)) and sum(found['dual']) == pytest.approx(0)
    with pytest.raises(ValueError):
        fukui.condensed((0, 0), (0,), (0, 0))


def test_global_indices_in_ev():
    ev = 1 / fukui.HARTREE_EV
    found = fukui.global_indices(-100.0, -100.0 - 1.0 * ev, -100.0 + 10.0 * ev)  # IP 10 eV, EA 1 eV
    assert found['ip'] == pytest.approx(10) and found['ea'] == pytest.approx(1)
    assert found['mu'] == pytest.approx(-5.5) and found['chi'] == pytest.approx(5.5)
    assert found['eta'] == pytest.approx(9) and found['omega'] == pytest.approx(5.5 ** 2 / 18)
    assert fukui.global_indices(None, -1.0, -1.0) is None


def test_table_by_atom():
    charges = {'n': (-0.3, 0.3), 'anion': (-0.8, -0.2), 'cation': (0.2, 0.8)}
    values = fukui.condensed(*charges.values())
    header, rows = fukui.table(['O', 'H'], charges, values)
    assert header[0] == 'Атом' and header[-1] == 'Δf' and rows[0][0] == 'O1' and rows[1][4] == '0.50000'


def test_fukui_fields_of_frozen_orbitals():
    """The fields f⁺, f⁻, f⁰, Δf (density.fukui_cubes). The oracle, independent of it: with the orbitals of
    N frozen, N + 1 is one more electron in the LUMO and N − 1 one less in the HOMO, so f⁺ = |ψ_LUMO|² and
    f⁻ = |ψ_HOMO|² exactly (the frontier-orbital picture of Fukui), computed from orbitals.orbital_cube."""
    from dataclasses import replace
    from pathlib import Path

    import numpy as np

    from modules.spectrum.analysis import density
    from modules.spectrum.readers.orbital_files import read_orbitals
    from modules.spectrum.analysis.orbitals import orbital_cube

    text = (Path(__file__).parents[1] / 'data' / 'orbitals' / 'molden5.7_water_mp2.molden').read_text(encoding='utf-8')
    n = read_orbitals(text)
    occupations = [o.occupation for o in n.orbitals]
    homo = max(k for k, w in enumerate(occupations) if w > 1.5)
    lumo = min(k for k, w in enumerate(occupations) if w < 0.5)

    def occupied(change, k):
        orbitals = list(n.orbitals)
        orbitals[k] = replace(orbitals[k], occupation=orbitals[k].occupation + change)
        return replace(n, orbitals=tuple(orbitals))

    step = 0.3
    cubes, integrals = density.fukui_cubes(n, occupied(1, lumo), occupied(-1, homo), step=step)
    psi_lumo = orbital_cube(n, lumo, step=step).values[..., 0]
    psi_homo = orbital_cube(n, homo, step=step).values[..., 0]
    assert np.allclose(cubes['plus'].values[..., 0], psi_lumo ** 2, atol=1e-10)
    assert np.allclose(cubes['minus'].values[..., 0], psi_homo ** 2, atol=1e-10)
    assert np.allclose(cubes['zero'].values[..., 0], (psi_lumo ** 2 + psi_homo ** 2) / 2, atol=1e-10)
    assert np.allclose(cubes['dual'].values[..., 0], psi_lumo ** 2 - psi_homo ** 2, atol=1e-10)
    assert integrals['dual'] == pytest.approx(integrals['plus'] - integrals['minus'])
    assert 0.9 < integrals['minus'] < 1.05  # a normalized orbital, up to the coarse grid and the box
    with pytest.raises(ValueError):  # not N ± 1
        density.fukui_cubes(n, n, occupied(-1, homo), step=step)

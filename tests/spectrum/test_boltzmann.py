"""The Boltzmann shares and the energies of several results (modules/spectrum/analysis/boltzmann.py)."""

from math import exp

import pytest

from modules.spectrum.analysis import boltzmann
from modules.spectrum.analysis.reaction import typed_species


def test_shares_of_two_and_three():
    # 1 kcal/mol at 298.15 K: exp(−503.2/298.15)… the ratio is exp(−ΔE/RT) with R = 1.987204e-3 kcal/(mol K)
    rows = boltzmann.typed_table([('a', 0.0), ('b', 1.0)], 'kcal', 298.15, 627.509474)
    ratio = exp(-1.0 / (0.0019872043 * 298.15))
    assert rows[1][3] / rows[0][3] == pytest.approx(ratio, rel=1e-6) and rows[0][3] + rows[1][3] == pytest.approx(1)
    assert rows[1][2] == pytest.approx(1.0) and rows[0][2] == 0
    equal = boltzmann.shares([-1.0, -1.0, -1.0], 300)
    assert equal == pytest.approx([1 / 3] * 3)
    with pytest.raises(ValueError):
        boltzmann.shares([0.0], 0)


def test_typed_energies():
    rows = boltzmann.parse_energies('conf 1  -76,4321\n\n# comment\nconf 2; -76.4300\n−76.4000')
    assert rows == [('conf 1', -76.4321), ('conf 2', -76.43), ('3', -76.4)]
    with pytest.raises(ValueError):
        boltzmann.parse_energies('nothing here')


def test_energies_of_files_use_g_only_when_every_one_has_it():
    made = {'a.out': typed_species('a', -100.0, gibbs=0.02, formula='C2H6O', charge=0),
            'b.out': typed_species('b', -99.998, gibbs=0.019, formula='C2H6O', charge=0)}
    found = boltzmann.files_table(['a.out', 'b.out'], 298.15, 627.509474, read=lambda p, label: made[p])
    assert found['by'] == 'G' and found['warnings'] == []
    a, b = found['rows']
    assert b[5] == pytest.approx(0.002 * 627.509474) and b[6] == pytest.approx(0.001 * 627.509474)
    made['b.out'] = typed_species('b', -99.998, formula='C2H4O', charge=0)
    found = boltzmann.files_table(['a.out', 'b.out'], 298.15, 627.509474, read=lambda p, label: made[p])
    assert found['by'] == 'E' and len(found['warnings']) == 2  # another composition; G not of every one


# -- the review of 2026-11-09, item 2 — the input is checked, nothing is dropped silently ---------------
def test_a_typo_in_one_line_is_an_error_naming_the_line():
    with pytest.raises(ValueError, match='строка 3') as caught:
        boltzmann.parse_energies('A -76\nB -76.1\nC typo')
    assert '«C typo»' in str(caught.value)


@pytest.mark.parametrize('bad', ['nan', 'inf', '-inf', '1e999', 'NaN'])
def test_energies_that_are_not_finite_never_reach_the_shares(bad):
    with pytest.raises(ValueError, match='строка 2'):
        boltzmann.parse_energies(f'A -76\nB {bad}')
    with pytest.raises(ValueError, match='не конечное'):
        boltzmann.shares([-76.0, float(bad)], 298.15)


def test_a_header_comments_and_empty_lines_are_allowed():
    rows = boltzmann.parse_energies('Название  Энергия\n\n# conformers of ethanol\nanti −154,0001\ngauche -154.0\n')
    assert rows == [('anti', -154.0001), ('gauche', -154.0)]
    with pytest.raises(ValueError):  # a line without digits after the first one is not a header
        boltzmann.parse_energies('anti -154.0\nгош энергия')


@pytest.mark.parametrize('temperature', [0, -10, float('nan'), float('inf')])
def test_the_temperature_must_be_finite_and_positive(temperature):
    with pytest.raises(ValueError, match='Температура'):
        boltzmann.shares([-1.0, -1.1], temperature)


def test_an_empty_set_is_an_error():
    with pytest.raises(ValueError):
        boltzmann.shares([], 298.15)
    with pytest.raises(ValueError):
        boltzmann.typed_table([], 'hartree', 298.15, 627.509474)
    with pytest.raises(ValueError):
        boltzmann.parse_energies('# only a comment\n\n')


def test_equal_and_very_different_energies_give_finite_normalised_shares():
    from math import isfinite

    equal = boltzmann.shares([-500.0] * 44, 298.15)
    assert equal == pytest.approx([1 / 44] * 44)
    far = boltzmann.shares([-500.0, -499.0, -100.0, 1e5], 298.15)  # 1 hartree ≈ 627 kcal/mol: no overflow, no nan
    assert all(isfinite(p) and p >= 0 for p in far) and sum(far) == pytest.approx(1) and far[0] == pytest.approx(1)
    # the same shares by hand for a small difference (oracle: exp(−ΔE/kT) with k in hartree/K)
    k = 3.166811563e-6
    pair = boltzmann.shares([-76.0, -75.999], 300)
    w = exp(-0.001 / (k * 300))
    assert pair == pytest.approx([1 / (1 + w), w / (1 + w)], rel=1e-12)


# -- the review of 2026-11-09, item 3 — the same warnings as the diagram of a reaction ------------------
def test_the_notes_of_a_result_reach_the_table_of_shares():
    from dataclasses import replace

    good = typed_species('anti', -154.0, gibbs=0.05, formula='C2H6O', charge=0)
    doubtful = replace(typed_species('gauche', -153.999, gibbs=0.05, formula='C2H6O', charge=0),
                       notes=('нормальное завершение не подтверждено',))
    made = {'a.out': good, 'b.out': doubtful}
    found = boltzmann.files_table(['a.out', 'b.out'], 298.15, 627.509474, read=lambda p, label: made[p])
    assert '«gauche»: нормальное завершение не подтверждено' in found['warnings']
    assert found['notes'] == {'gauche': ('нормальное завершение не подтверждено',)} and found['by'] == 'G'
    from modules.spectrum.analysis import reaction

    profile = reaction.profile([reaction.Stage('A', (good,)), reaction.Stage('B', (doubtful,))], 'E', 'kcal')
    assert '«gauche»: нормальное завершение не подтверждено' in profile.warnings  # the same in both tools


def test_unknown_charges_and_other_levels_are_said_not_taken_for_a_match():
    from dataclasses import replace

    a = replace(typed_species('a', -100.0, formula='CH4O'), level='B3LYP/def2-SVP')
    b = replace(typed_species('b', -99.999, formula='CH4O', charge=0), level='PBE0/def2-TZVP')
    made = {'a.out': a, 'b.out': b}
    found = boltzmann.files_table(['a.out', 'b.out'], 298.15, 627.509474, read=lambda p, label: made[p])
    text = ' '.join(found['warnings'])
    assert 'Заряд не известен для: «a»' in text and 'Уровень теории разный' in text and found['by'] == 'E'
    charged = {'a.out': replace(a, charge=0, level=''), 'b.out': replace(b, charge=1, level='')}
    found = boltzmann.files_table(['a.out', 'b.out'], 298.15, 627.509474, read=lambda p, label: charged[p])
    assert any(w.startswith('Заряды разные') for w in found['warnings'])


def test_an_imaginary_frequency_is_not_a_conformer():
    from dataclasses import replace

    minimum = replace(typed_species('min', -10.0, formula='H2O', charge=0), frequencies=(1600.0, 3700.0, 3800.0))
    saddle = replace(typed_species('ts', -9.99, formula='H2O', charge=0), frequencies=(-900.0, 3700.0, 3800.0))
    made = {'a': minimum, 'b': saddle}
    found = boltzmann.files_table(['a', 'b'], 298.15, 627.509474, read=lambda p, label: made[p])
    assert any('мнимых частот: 1' in w and '«ts»' in w for w in found['warnings'])

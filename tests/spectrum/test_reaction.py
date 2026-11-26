"""The energy diagram of a reaction (modules/spectrum/analysis/reaction.py).

Oracles: differences computed by hand with 1 Eh = 627.5094740631 kcal/mol = 2625.4996394799 kJ/mol =
27.211386245988 eV (CODATA 2018, typed in here, not taken from the module); the standard-state correction
RT ln(RT c°/P) = 1.8943 kcal/mol at 298.15 K and 1 atm (RT ln 24.465; the textbook 1.89 kcal/mol); the
thermochemistry Psi4 1.7 printed for divinylbenzene (σ = 2: ZPE 0.19168059, H − E 0.19983311, G − E 0.16038928 Eh).
Rates of Eyring: k_B T/h = 6.2124·10¹² s⁻¹ at 298.15 K (k_B and h exact in SI 2019, typed in here); the independent
implementation of the Atlas (quas_atlas/core/kinetics.py, its own constants); a bimolecular k is the same whichever
standard state ΔG‡ is given for — the physics, not the formula of the module.
"""

import json
from pathlib import Path

import pytest

from modules.spectrum.analysis import reaction
from modules.spectrum.analysis.reaction import Stage, profile, typed_species

KCAL, KJ, EV = 627.5094740631, 2625.4996394799, 27.211386245988
DATA = Path(__file__).parents[1] / 'data'


def ts(label, energy, formula='', charge=None, typed=(None, None, None)):
    """A typed species marked as a transition state."""
    return typed_species(label, energy, *typed, formula=formula, charge=charge, ts=True)


def simple():
    r = typed_species('R', -100.0, formula='CH4')
    t = ts('TS', -99.96, formula='CH4')
    p = typed_species('P', -100.02, formula='CH4')
    return [Stage('R', (r,)), Stage('TS', (t,)), Stage('P', (p,))]


def test_relative_energies_barriers_and_energy_of_reaction():
    for unit, u in (('kcal', KCAL), ('kj', KJ), ('ev', EV)):
        r = profile(simple(), 'E', unit)
        assert r.values[0] == 0.0
        assert r.values[1] == pytest.approx(0.04 * u, rel=1e-9)
        assert r.values[2] == pytest.approx(-0.02 * u, rel=1e-9)
        assert r.kinds == ('min', 'ts', 'min')
        (b,) = r.barriers
        assert (b.ts, b.start, b.end) == (1, 0, 2)
        assert b.forward == pytest.approx(0.04 * u, rel=1e-9) and b.reverse == pytest.approx(0.06 * u, rel=1e-9)
        assert r.reaction == pytest.approx(-0.02 * u, rel=1e-9)
        assert r.warnings == ()
    assert profile(simple(), 'E', 'kcal').values[1] == pytest.approx(25.1004, abs=1e-4)


def test_another_reference_stage():
    r = profile(simple(), 'E', 'kcal', reference=2)
    assert r.values[2] == 0.0 and r.values[0] == pytest.approx(0.02 * KCAL, rel=1e-9)
    assert r.reaction == pytest.approx(-0.02 * KCAL, rel=1e-9)  # last − first does not depend on the reference


def test_a_stage_is_the_sum_of_its_species():
    a = typed_species('A', -40.5, formula='CH4')
    b = typed_species('B', -100.4, formula='HF')
    c = typed_species('C', -140.92, formula='CH3F')
    d = typed_species('D', -1.17, formula='H2')
    r = profile([Stage('A + B', (a, b)), Stage('C + D', (c, d))], 'E', 'kcal')
    assert r.values[1] == pytest.approx((-140.92 - 1.17 - (-40.5 - 100.4)) * KCAL, rel=1e-9)
    assert r.warnings == ()  # CH4 + HF = CH3F + H2: the atoms balance


def test_unbalanced_atoms_and_charges_are_named():
    a = typed_species('A', -40.5, formula='CH4', charge=0)
    c = typed_species('C', -140.9, formula='CH3F', charge=-1)
    r = profile([Stage('A', (a,)), Stage('C', (c,))], 'E', 'kcal')
    text = '\n'.join(r.warnings)
    assert 'Атомы не сходятся' in text and '«C»' in text and 'F: +1' in text and 'H: -1' in text
    assert 'Заряд не сходится' in text


def test_gibbs_energy_needs_corrections_and_names_who_lacks_them():
    stages = simple()
    r = profile(stages, 'G', 'kcal')
    assert r.values == (None, None, None) and r.barriers == () and r.reaction is None
    assert any('R' in w and 'частот' in w for w in r.warnings)
    with_g = [Stage(s.label, tuple(typed_species(x.label, x.energy, 0.01, 0.012, g, formula=x.formula) for x in s.species))
              for s, g in zip(stages, (-0.02, -0.025, -0.018))]
    r = profile(with_g, 'G', 'kcal')
    assert r.values[1] == pytest.approx((0.04 - 0.005) * KCAL, rel=1e-9)
    assert r.values[2] == pytest.approx((-0.02 + 0.002) * KCAL, rel=1e-9)
    assert any('вручную' in w for w in r.warnings)  # typed corrections do not follow T
    e0 = profile(with_g, 'E0', 'kcal')
    assert e0.values[1] == pytest.approx(0.04 * KCAL, rel=1e-9)  # the same ZPE everywhere


def test_standard_state_of_one_mole_per_litre():
    assert reaction.molar_shift(298.15, 101325.0) * KCAL == pytest.approx(1.8943, abs=2e-4)
    a = typed_species('A', -50.0, 0.0, 0.0, 0.0, formula='CH4')
    b = typed_species('B', -50.0, 0.0, 0.0, 0.0, formula='CH4')
    c = typed_species('A2', -100.0, 0.0, 0.0, 0.0, formula='C2H8')
    gas = profile([Stage('A + B', (a, b)), Stage('A2', (c,))], 'G', 'kcal')
    sol = profile([Stage('A + B', (a, b)), Stage('A2', (c,))], 'G', 'kcal', molar=True)
    assert gas.values[1] == pytest.approx(0.0, abs=1e-9)
    assert sol.values[1] == pytest.approx(-1.8943, abs=2e-4)  # one molecule fewer
    same = profile([Stage('A', (a,)), Stage('B', (b,))], 'G', 'kcal', molar=True)
    assert same.values[1] == pytest.approx(0.0, abs=1e-9)  # unchanged number of molecules: no effect


def test_one_imaginary_frequency_makes_a_transition_state():
    from dataclasses import replace

    a = typed_species('A', -1.0)
    t = replace(typed_species('T', -0.95), frequencies=(-450.0, 300.0))
    r = profile([Stage('A', (a,)), Stage('T', (t,))], 'E', 'kcal')
    assert r.kinds == ('min', 'ts') and r.barriers[0].start == 0 and r.barriers[0].end is None
    assert r.barriers[0].reverse is None and r.barriers[0].forward == pytest.approx(0.05 * KCAL, rel=1e-9)


def test_two_imaginary_frequencies_and_different_levels_are_warned():
    from dataclasses import replace

    a = replace(typed_species('A', -1.0), frequencies=(-300.0, -120.0, 500.0), level='B3LYP DEF2-SVP')
    b = replace(typed_species('B', -1.1), level='HF STO-3G')
    r = profile([Stage('A', (a,)), Stage('B', (b,))], 'E', 'kcal')
    text = '\n'.join(r.warnings)
    assert 'мнимых частот: 2' in text and 'Уровень теории разный' in text
    assert r.kinds == ('min', 'min')  # two imaginary frequencies: not a TS


def test_levels_of_theory_from_the_outputs():
    orca = '|  1> ! B3LYP D3BJ def2-SVP Opt Freq TightSCF\n|  2> %pal nprocs 4 end\n'
    assert reaction.level_of_theory(orca, 'ORCA') == 'B3LYP D3BJ DEF2-SVP'
    assert reaction.level_of_theory('|  1> ! b3lyp DEF2-svp OptTS NumFreq\n', 'ORCA') == 'B3LYP DEF2-SVP'
    gaussian = (DATA / 'gaussian' / 'dvb_ir_g16.log').read_text(encoding='utf-8', errors='replace')
    assert reaction.level_of_theory(gaussian, 'Gaussian 16') == 'B3LYP/STO-3G'
    route = ' Entering Gaussian System\n #p opt freq b3lyp/6-31g(d) scf=tight\n'
    assert reaction.level_of_theory(route, 'Gaussian') == 'B3LYP/6-31G(D)'
    assert reaction.level_of_theory('', 'ORCA') == ''


def test_a_real_result_divinylbenzene_psi4():
    s = reaction.read_species(DATA / 'psi4' / 'dvb_ir_rhf_psi4-1.7.out')
    assert s.formula == 'C10H10' and s.program.startswith('Psi4') and s.sigma == 2 and not s.is_ts
    zpe, h, g = reaction.corrections(s)
    assert zpe == pytest.approx(0.19168059, abs=5e-8)
    assert h == pytest.approx(0.19983311, abs=5e-8)
    assert g == pytest.approx(0.16038928, abs=5e-8)
    r = profile([Stage('dvb', (s,)), Stage('dvb again', (s,))], 'G', 'kcal')
    assert r.values == (0.0, 0.0) and r.warnings == ()


def test_invalid_input_is_refused():
    with pytest.raises(ValueError):
        profile([], 'E')
    with pytest.raises(ValueError):
        profile(simple(), 'S')
    with pytest.raises(ValueError):
        profile(simple(), 'E', 'cal')
    with pytest.raises(ValueError):
        profile(simple(), 'E', reference=3)
    with pytest.raises(ValueError):
        profile([Stage('empty', ())], 'E')
    with pytest.raises(ValueError):
        typed_species('', -1.0)
    with pytest.raises(ValueError):
        typed_species('X', None)
    with pytest.raises(ValueError):
        reaction.parse_formula('Ca(OH)2')
    assert reaction.parse_formula('C2H6O') == (('C', 2), ('H', 6), ('O', 1))


def test_save_and_load(tmp_path):
    result = tmp_path / 'dvb.out'
    result.write_text((DATA / 'psi4' / 'dvb_ir_rhf_psi4-1.7.out').read_text(encoding='utf-8'), encoding='utf-8')
    s = reaction.read_species(result, 'divinylbenzene')
    stages = simple() + [Stage('dvb', (s,))]
    data = reaction.save(stages, {'quantity': 'G', 'unit': 'kj'}, tmp_path)
    assert data['stages'][3]['species'][0]['file']['relative'] == 'dvb.out'
    text = json.dumps(data, ensure_ascii=False)
    back, settings, problems = reaction.load(json.loads(text), tmp_path)
    assert problems == [] and settings == {'quantity': 'G', 'unit': 'kj'}
    assert [st.label for st in back] == ['R', 'TS', 'P', 'dvb']
    assert back[3].species[0].label == 'divinylbenzene' and back[3].species[0].energy == s.energy
    assert back[0].species[0].energy == -100.0 and back[0].species[0].formula == 'CH4'
    result.unlink()
    back, _, problems = reaction.load(json.loads(text), tmp_path)
    assert len(back) == 3 and problems and 'dvb.out' in problems[0]
    assert [st.kind for st in back] == ['min', 'ts', 'min']  # a typed TS stays a TS
    with pytest.raises(ValueError):
        reaction.load({'kind': 'other'}, tmp_path)


def test_table_rows():
    stages = simple()
    r = profile(stages, 'E', 'kcal')
    rows = reaction.rows(r, stages)
    assert rows[0] == ('R', '', '', '-100.00000000', '0.00')
    assert rows[2][2] == 'TS' and rows[3][2] == 'TS' and rows[3][1] == 'TS (CH4)'


KB_SI, H_SI, NA_SI = 1.380649e-23, 6.62607015e-34, 6.02214076e23


def test_eyring_by_hand_and_against_the_atlas():
    import sys

    from modules.atlas.paths import ATLAS_HOME

    if str(ATLAS_HOME) not in sys.path:
        sys.path.insert(0, str(ATLAS_HOME))
    from quas_atlas.core import kinetics

    assert KB_SI * 298.15 / H_SI == pytest.approx(6.2124e12, rel=1e-4)
    g = 20.0 / KCAL  # 20 kcal/mol in hartree
    by_hand = KB_SI * 298.15 / H_SI * 2.718281828459045 ** (-20.0 * 4184.0 / (KB_SI * NA_SI * 298.15))
    assert reaction.eyring(g, 298.15) == pytest.approx(by_hand, rel=1e-9)
    assert reaction.eyring(g, 298.15) == pytest.approx(kinetics.rate(20.0 * 4.184, 0.0, 298.15), rel=1e-6)
    with pytest.raises(ValueError):
        reaction.eyring(g, 0.0)


def _with_g(label, energy, g, formula, ts=False):
    return typed_species(label, energy, 0.0, 0.0, g, formula=formula, ts=ts)


def bimolecular():
    a, b = _with_g('A', -50.0, 0.0, 'CH4'), _with_g('B', -50.0, 0.0, 'CH4')
    t = _with_g('TS', -99.97, 0.0, 'C2H8', ts=True)
    c = _with_g('C', -100.01, 0.0, 'C2H8')
    return [Stage('A + B', (a, b)), Stage('TS', (t,)), Stage('C', (c,))]


def test_the_rates_of_the_barriers_of_a_gibbs_profile():
    stages = bimolecular()
    gas = profile(stages, 'G', 'kcal')
    sol = profile(stages, 'G', 'kcal', molar=True)
    fg, rg = reaction.barrier_rates(gas, stages)
    fs, rs = reaction.barrier_rates(sol, stages, molar=True)
    assert (fg.direction, fg.order, rg.direction, rg.order) == ('forward', 2, 'reverse', 1)
    assert fg.barrier == pytest.approx(0.03) and fs.barrier == pytest.approx(0.03 - 1.8943 / KCAL, abs=1e-6)
    assert fg.k == pytest.approx(fs.k, rel=1e-9)  # one k in L/(mol s), whatever the standard state
    assert rg.k == pytest.approx(rs.k, rel=1e-9) and rg.half_life == pytest.approx(0.6931471805599453 / rg.k)
    assert fg.half_life is None  # second order: t½ depends on the concentrations
    assert reaction.barrier_rates(profile(stages, 'E', 'kcal'), stages) == []  # only for ΔG‡
    rows = reaction.rate_table(stages, (300.0, 400.0))
    assert [(r[0], r[3]) for r in rows] == [(300.0, 'forward'), (300.0, 'reverse'), (400.0, 'forward'), (400.0, 'reverse')]
    assert rows[2][6] > rows[0][6]  # faster when hotter


def test_the_units_and_numbers_of_rates_as_shown():
    assert reaction.rate_unit(1) == 'с⁻¹' and reaction.rate_unit(2) == 'л·моль⁻¹·с⁻¹'
    assert reaction.rate_unit(3) == 'л²·моль⁻²·с⁻¹'
    assert reaction.scientific(1.234e5) == '1.23·10⁵' and reaction.scientific(4.56e-7) == '4.56·10⁻⁷'
    assert reaction.scientific(12.5) == '12.5'
    assert reaction.duration(90.0) == '1.5 мин' and reaction.duration(2e-4) == '200 мкс'
    assert reaction.duration(3.15576e8).endswith('лет')

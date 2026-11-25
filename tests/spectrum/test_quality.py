"""The facts of a result and its fitness for an operation as codes (modules/spectrum/analysis/quality.py).

Oracles: Output objects made here by hand (an optimization of two steps that did not converge, a single point, an
output without its normal end), typed species, and the rules of §2 of the module — an unknown is never a confirmation,
a value taken by default is told apart from one read, the severity of each code."""

from dataclasses import replace

from azimuth.core import read_xyz
from modules.spectrum.analysis import quality, reaction
from modules.spectrum.readers.results import OptimizationStep, Output

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')
TEXT = 'Total Charge           Charge          ....    0\nMultiplicity           Mult            ....    1\n'


def output(normal=True, converged=True, steps=2, scf_failed=False):
    made = tuple(OptimizationStep(k, -76.0 - k * 1e-4, WATER) for k in range(steps))
    return Output(normal, converged, scf_failed, (-76.0,), (), WATER, False, made)


def codes(found):
    return [(f.code, f.severity) for f in found]


def test_an_optimization_that_did_not_converge_is_a_fact_a_single_point_is_not():
    bad = reaction.species_from_output(output(converged=False), TEXT, 'a.out')
    assert 'optimization_unconverged' in bad.facts
    single = reaction.species_from_output(output(converged=False, steps=0), TEXT, 'b.out')
    assert 'optimization_unconverged' not in single.facts  # no optimization was run
    found = quality.findings([bad, single], 'ensemble')
    assert ('optimization_unconverged', 'warn') in codes(found) and found[0].subject == 'a'
    assert '«a»: оптимизация не сошлась — геометрия не минимум' in quality.messages(found)


def test_an_incomplete_output_and_a_failed_scf_are_said():
    s = reaction.species_from_output(output(normal=False, scf_failed=True), TEXT, 'c.out')
    assert {'normal_exit_unconfirmed', 'scf_failed'} <= set(s.facts)
    assert {('normal_exit_unconfirmed', 'warn'), ('scf_failed', 'warn')} <= set(codes(quality.findings([s], 'profile')))


def test_a_value_taken_by_default_is_told_apart_from_one_read():
    read = reaction.species_from_output(output(), TEXT, 'r.out')
    guessed = reaction.species_from_output(output(), 'no multiplicity, no charge here', 'g.out')
    assert 'multiplicity_default' not in read.facts and 'charge_unknown' not in read.facts and read.charge == 0
    assert {'multiplicity_default', 'charge_unknown'} <= set(guessed.facts) and guessed.charge is None
    found = quality.findings([read, guessed], 'ensemble')
    assert ('charge_unknown', 'missing') in codes(found)  # not enough data — never a match
    assert ('charges_differ', 'warn') not in codes(found)


def test_typed_numbers_and_their_unknown_charge():
    typed = reaction.typed_species('t', -1.0, formula='H2O')
    assert typed.facts == ('typed', 'charge_unknown')
    assert quality.findings([typed], 'profile') == []  # typed by hand is no doubt about a result


def test_the_severities_and_the_texts():
    a = replace(reaction.typed_species('a', -1.0, formula='H2O', charge=0), frequencies=(-200.0, 1600.0))
    b = replace(reaction.typed_species('b', -1.0, formula='H2O2', charge=1), level='PBE0', multiplicity=3)
    c = replace(reaction.typed_species('c', -1.0, formula='H2O', charge=0), level='B3LYP')
    found = quality.findings([a, b, c], 'ensemble')
    assert set(codes(found)) == {('imaginary_frequencies', 'warn'), ('levels_differ', 'warn'),
                                 ('composition_differs', 'warn'), ('charges_differ', 'warn'),
                                 ('multiplicities_differ', 'warn')}
    assert all(f.severity in ('refuse', 'warn', 'missing') for f in found)
    assert quality.findings([a], 'profile') == []  # one imaginary frequency: a transition state of a reaction
    texts = quality.messages(found)
    assert texts == list(dict.fromkeys(texts)) and any(t.startswith('Заряды разные') for t in texts)


def test_a_note_of_older_code_is_kept_as_it_is():
    s = replace(reaction.typed_species('x', -1.0, charge=0), notes=('введено вручную', 'своё замечание'))
    assert codes(quality.findings([s], 'profile')) == [('note', 'warn')]
    assert quality.messages(quality.findings([s], 'profile')) == ['«x»: своё замечание']
    old = replace(reaction.typed_species('y', -1.0, charge=0), notes=('нормальное завершение не подтверждено',))
    assert ('normal_exit_unconfirmed', 'warn') in codes(quality.findings([old], 'profile'))  # a note read as a fact


def test_the_assessment_and_the_comparison_follow_the_same_facts():
    # one set of rules — Output.facts; the words of the assessment and the
    # facts of a species are both read from it, so they cannot disagree
    cases = {
        'unconverged': output(converged=False),
        'single point': output(converged=False, steps=1),
        'no normal end, SCF': output(normal=False, scf_failed=True),
        'demo': replace(output(), demo=True),
    }
    for name, made in cases.items():
        facts = set(made.facts)
        species = set(reaction.species_from_output(made, TEXT, f'{name}.out').facts)
        shared = {'demo', 'normal_exit_unconfirmed', 'scf_failed', 'optimization_unconverged'}
        assert species & shared == facts & shared, name
        words = made.assessment
        assert ('Найдено сообщение о несходимости SCF' in words) == ('scf_failed' in facts), name
        assert ('Метка нормального завершения не найдена' in words) == ('normal_exit_unconfirmed' in facts), name
        assert ('Подтверждение сходимости оптимизации не найдено' in words) == bool(
            facts & {'optimization_unconverged', 'optimization_unconfirmed'}), name
    assert 'optimization_unconfirmed' in output(converged=False, steps=1).facts
    assert 'optimization_unconverged' not in reaction.species_from_output(output(converged=False, steps=1), TEXT,
                                                                           's.out').facts


def test_results_of_two_programs_are_said_to_be_of_two_programs():
    # «B3LYP» of ORCA (VWN5) and of Psi4 and NWChem (VWN1RPA) are different functionals: water B3LYP-D3(BJ)/def2-SVP
    # −76.32185 against −76.35890 Eh on the owner's Mac, 2026-11-22 (docs/plans/TASK_MATRIX.md) — and the level of
    # theory read from the two outputs is the same text. Versions of one program are one program; a result typed in
    # by hand names no program and says nothing
    base = reaction.species_from_output(output(), TEXT, 'a.out')
    orca = replace(base, label='a', program='ORCA', level='B3LYP/def2-SVP')
    psi4 = replace(base, label='b', program='Psi4 1.11', level='B3LYP/def2-SVP')
    found = quality.findings([orca, psi4], 'profile')
    assert ('programs_differ', 'warn') in codes(found) and 'levels_differ' not in [f.code for f in found]
    text = ' '.join(quality.messages(found))
    assert 'Программы разные: ORCA · Psi4' in text and '«B3LYP» в ORCA' in text
    hf = quality.messages(quality.findings([replace(orca, level='HF/def2-SVP'), replace(psi4, level='HF/def2-SVP')], 'profile'))
    assert any('Программы разные' in m for m in hf) and not any('B3LYP' in m for m in hf)
    same = quality.findings([replace(psi4, label='c', program='Psi4 1.7'), psi4], 'profile')
    assert 'programs_differ' not in [f.code for f in same]
    typed = quality.findings([orca, replace(orca, label='t', program='')], 'profile')
    assert 'programs_differ' not in [f.code for f in typed]
    assert quality.family('xtb 6.7.1') == 'xtb' and quality.family('') == ''

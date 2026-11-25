"""What is known of a result and whether it is fit for an operation — codes, not texts (the roadmap of
2026-11-09, «A. Единая модель качества результата»).

§1 PURPOSE
    The tools comparing results (the diagram of a reaction, the energies of several files and their Boltzmann shares)
    said their doubts as sentences built here and there; a sentence lost on the way or a value taken by
    default without a word (the multiplicity 1 when the output names none) could not be checked by a program. Here the
    facts of one result are codes, the fitness for an operation is a list of findings with a severity, and the text
    for the user is made apart (and translated).
§2 RULES
    1. Facts of a result (Species.facts, set by reaction.species_from_output / typed_species; those of an
       output are taken from Output.facts — the same codes its assessment says in words, one set of rules):
       normal_exit_unconfirmed, scf_failed, optimization_unconverged (an optimization was run and did not converge;
       a single point has no such fact), demo, multiplicity_default (2S + 1 not in the output — 1 was taken),
       charge_unknown (not read), typed (the numbers were typed in by hand). An unknown is a fact of its own, never
       taken for a confirmation.
    2. findings(species, purpose) — purpose 'profile' (a reaction: one imaginary frequency is a transition state) or
       'ensemble' (conformers or isomers of one substance). Severity:
         'refuse' — the operation means nothing (none at present: the refusals — no energy, a value not finite —
                     are ValueErrors where the numbers are read);
         'warn' — the numbers are shown, the doubt is said: normal_exit_unconfirmed, scf_failed,
                     optimization_unconverged, demo, imaginary_frequencies (> 1 for a profile, ≥ 1 for an ensemble),
                     levels_differ, programs_differ (two programs among the results: the same name of a method
                     is not always the same method — «B3LYP» of ORCA and of Psi4); for an ensemble
                     composition_differs, charges_differ, multiplicities_differ;
         'missing' — not enough data to check: multiplicity_default (with frequencies), charge_unknown (in an
                     ensemble of more than one).
       A note of a result that is no known fact (from older code) is kept as the finding 'note' with its text.
    3. message(finding) — the sentence for the user (azimuth.i18n.tr), ««label»: …» for a finding of one result.
§3 INTERFACE Finding(code, severity, subject='', values=()); CODES {code: (severity, template)};
    findings(species, purpose) -> [Finding]; message(finding) -> str; messages(findings) -> [str] (each once).
§4 TESTS tests/spectrum/test_quality.py; tests/spectrum/test_boltzmann.py, test_reaction.py (the texts).
"""

from __future__ import annotations

from dataclasses import dataclass

from azimuth.i18n import tr

CODES = {
    'normal_exit_unconfirmed': ('warn', 'нормальное завершение не подтверждено'),
    'scf_failed': ('warn', 'найдено сообщение о несходимости SCF'),
    'optimization_unconverged': ('warn', 'оптимизация не сошлась — геометрия не минимум'),
    'demo': ('warn', 'учебный пример, не настоящий расчёт'),
    'multiplicity_default': ('missing', 'мультиплетность в выводе не найдена — взята 1'),
    'imaginary_frequencies': ('warn', None),
    'levels_differ': ('warn', None),
    'programs_differ': ('warn', None),
    'composition_differs': ('warn', 'Состав молекул разный — сравнивать их энергии нельзя (это не изомеры).'),
    'charges_differ': ('warn', None),
    'charge_unknown': ('missing', None),
    'multiplicities_differ': ('warn', 'Мультиплетность разная — это разные состояния, не конформеры.'),
    'note': ('warn', None),
}
FACTS = ('normal_exit_unconfirmed', 'scf_failed', 'optimization_unconverged', 'demo', 'multiplicity_default',
         'charge_unknown', 'typed')
_FACT_OF_NOTE = {text: code for code, (_, text) in CODES.items() if code in FACTS and text}


@dataclass(frozen=True)
class Finding:
    code: str
    severity: str
    subject: str = ''
    values: tuple = ()


def _make(code, subject='', values=()):
    return Finding(code, CODES[code][0], subject, tuple(values))


def facts_of(s):
    """The facts of a Species: its own, and those an older note names."""
    facts = list(getattr(s, 'facts', ()) or ())
    for note in s.notes:
        code = _FACT_OF_NOTE.get(note) or _FACT_OF_NOTE.get(_untranslated(note))
        if code and code not in facts:
            facts.append(code)
    return facts


def _untranslated(note):
    from azimuth.i18n import to_source

    try:
        return to_source(note)
    except Exception:  # noqa: BLE001 — a note in another language: compared as it is
        return note


def family(program):
    """The program without its version («Psi4 1.11» → «Psi4», «xtb 6.7.1» → «xtb»); '' when not known (typed in)."""
    return (program or '').split()[0] if (program or '').split() else ''


def findings(species, purpose):
    species = list(species)
    found = []
    known = {text for _, text in CODES.values() if text} | {tr('введено вручную'), 'введено вручную'}
    for s in species:
        facts = facts_of(s)
        n = len(s.imaginary)
        if (purpose == 'profile' and n > 1) or (purpose == 'ensemble' and n > 0):
            found.append(_make('imaginary_frequencies', s.label, (n, purpose)))
        for code in ('normal_exit_unconfirmed', 'scf_failed', 'optimization_unconverged', 'demo'):
            if code in facts:
                found.append(_make(code, s.label))
        if 'multiplicity_default' in facts and s.frequencies:
            found.append(_make('multiplicity_default', s.label))
        for note in s.notes:
            if note not in known and _untranslated(note) not in known:
                found.append(_make('note', s.label, (note,)))
    levels = sorted({s.level for s in species if s.level})
    if len(levels) > 1:
        found.append(_make('levels_differ', '', tuple(levels)))
    # the same name of a method is not the same method in two programs: «B3LYP» of ORCA has the VWN5 correlation, that
    # of Psi4 and NWChem — VWN1RPA (water B3LYP-D3(BJ)/def2-SVP: −76.32185 against −76.35890 Eh, 23 kcal/mol,
    # 2026-11-22), and ORCA takes 5 d functions for a Pople basis where the others take 6. levels_differ sees none of it
    programs = sorted({family(s.program) for s in species if family(s.program)})
    if len(programs) > 1:
        b3lyp = any('B3LYP' in (s.level or '').upper() for s in species)
        found.append(_make('programs_differ', '', (tuple(programs), b3lyp)))
    if purpose == 'ensemble' and len(species) > 1:
        if len({s.counts for s in species}) > 1:
            found.append(_make('composition_differs'))
        charges = [s.charge for s in species]
        if all(c is not None for c in charges):
            if len(set(charges)) > 1:
                found.append(_make('charges_differ', '', tuple((s.label, s.charge) for s in species)))
        else:
            found.append(_make('charge_unknown', '', tuple(s.label for s in species if s.charge is None)))
        read = [s for s in species if 'multiplicity_default' not in facts_of(s)]
        if len({s.multiplicity for s in read}) > 1:
            found.append(_make('multiplicities_differ'))
    return found


def message(f):
    if f.code == 'imaginary_frequencies':
        n, purpose = f.values
        if purpose == 'profile':
            return tr(f'У «{f.subject}» мнимых частот: {n} — это не минимум и не переходное состояние.')
        return tr(f'У «{f.subject}» мнимых частот: {n} — это не минимум, его доля в смеси не имеет смысла.')
    if f.code == 'levels_differ':
        joined = ' · '.join(f.values)
        return tr(f'Уровень теории разный: {joined} — сравнивать энергии так нельзя.')
    if f.code == 'programs_differ':
        programs, b3lyp = f.values
        text = tr('Программы разные: {} — их энергии сравнимы, только если метод и базис в них заданы одинаково.').format(' · '.join(programs))
        if b3lyp:
            text += ' ' + tr('«B3LYP» в ORCA и «B3LYP» в Psi4, NWChem и Gaussian — разные функционалы: энергии отличаются на десятки ккал/моль.')
        return text
    if f.code == 'charges_differ':
        return tr('Заряды разные: ') + ', '.join(f'«{label}» {charge:+d}' for label, charge in f.values) + '.'
    if f.code == 'charge_unknown':
        return (tr('Заряд не известен для: ') + ', '.join(f'«{label}»' for label in f.values)
                + tr(' — совпадение зарядов не проверено.'))
    if f.code == 'note':
        return f'«{f.subject}»: {f.values[0]}'
    text = tr(CODES[f.code][1])
    return f'«{f.subject}»: {text}' if f.subject else text


def messages(found):
    return list(dict.fromkeys(message(f) for f in found))

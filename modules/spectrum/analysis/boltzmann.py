"""Energies of several results and the Boltzmann shares — Simple utilities of Chemcraft's Tools.

§1 PURPOSE
    For Spectrum («Инструменты»): «Энергии из нескольких файлов…» — the outputs of conformers, isomers or a scan
    side by side: E, G when there are frequencies, ΔE and ΔG in the unit of «Настройки → Единицы» and the shares at
    T; «Доли по Больцману…» — the same for energies typed or pasted (one per line, a name before it if one likes).
§1 THEORY
    The share of a species k: p_k = exp(−ΔX_k / kT) / Σ exp(−ΔX_j / kT), ΔX from the lowest, k = 3.166811563e-6
    hartree/K (CODATA 2018). With G of every result the shares are those of G (at the T of the thermochemistry,
    reaction.corrections), else of E — the result says which. Structures of different composition cannot be compared
    by energy: a warning says so (and different levels of theory, as reaction.profile does).
§4 SPECIFICATION
    a line not read, a value or a temperature not finite, an empty set — ValueError naming it (never a
    share of nan, never a structure dropped in silence).
    K_HARTREE; UNIT_TO_HARTREE {'hartree', 'kcal', 'kj', 'ev'}; parse_energies(text) -> [(name, value)];
    shares(values_hartree, temperature) -> [share]; typed_table(rows, unit, temperature, out_factor) -> rows
    (name, value, ΔE in the unit, share); files_table(paths, temperature, out_factor, read=reaction.read_species) ->
    {'rows': [(name, program, level, E, G | None, ΔE, ΔG | None, share)], 'by': 'G' | 'E', 'warnings': [...],
    'notes': {name: (note, …)}} — the warnings of reaction.suitability(species, 'ensemble') (the notes of the
    results, imaginary frequencies, levels, composition, charges, multiplicity) and the E/G note.
§7 TESTS
    tests/spectrum/test_boltzmann.py.
"""

from math import exp, isfinite
from pathlib import Path

from azimuth.i18n import tr

K_HARTREE = 3.166811563e-6  # Boltzmann constant, hartree per kelvin
UNIT_TO_HARTREE = {'hartree': 1.0, 'kcal': 1 / 627.509474, 'kj': 1 / 2625.499639, 'ev': 1 / 27.211386246}


def parse_energies(text):
    """«-76.4321», «conf-1 -76.4321», «A; -12,5» (a decimal comma, a Unicode minus) → [(name, value)].
    Empty lines and lines starting with «#» are skipped, and so is a first
    line without a single digit (a header «Название Энергия»); any other line without a number at its end, or with a
    number that is not finite (nan, inf, 1e999), is an error naming its line — a set with one structure dropped is
    never shown as read."""
    rows, bad, first = [], [], True
    for number, line in enumerate((text or '').splitlines(), 1):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        header, first = first and not any(ch.isdigit() for ch in stripped), False
        if header:
            continue
        parts = stripped.replace(';', ' ').replace('\t', ' ').split()
        try:
            value = float(parts[-1].replace(',', '.').replace('−', '-'))
        except ValueError:
            bad.append(tr(f'строка {number} («{stripped[:40]}»): нет числа в конце'))
            continue
        if not isfinite(value):
            bad.append(tr(f'строка {number} («{stripped[:40]}»): энергия не конечное число'))
            continue
        name = ' '.join(parts[:-1]) or str(len(rows) + 1)
        rows.append((name, value))
    if bad:
        raise ValueError(tr('Не все строки прочитаны — исправьте их, иначе доли посчитаются не по всем структурам: ')
                         + '; '.join(bad) + '.')
    if not rows:
        raise ValueError(tr('Нет ни одного числа: по одной энергии в строке, перед ней можно название.'))
    return rows


def _check(values, temperature):
    if not values:
        raise ValueError(tr('Нет ни одной энергии.'))
    if not isinstance(temperature, (int, float)) or not isfinite(temperature) or temperature <= 0:
        raise ValueError(tr('Температура должна быть больше нуля.'))
    if not all(isinstance(v, (int, float)) and isfinite(v) for v in values):
        raise ValueError(tr('Среди энергий есть не конечное число (nan, inf) — доли не посчитать.'))


def shares(values, temperature):
    """The shares, from the lowest value (no overflow: every exponent ≤ 0); finite, ≥ 0, their sum 1."""
    values = list(values)
    _check(values, temperature)
    low = min(values)
    weights = [exp(-(v - low) / (K_HARTREE * temperature)) for v in values]
    total = sum(weights)  # ≥ 1: the lowest one has weight 1
    return [w / total for w in weights]


def typed_table(rows, unit, temperature, out_factor):
    """rows [(name, value in unit)] → [(name, value, ΔE × out_factor (hartree → the unit shown), share)]."""
    if unit not in UNIT_TO_HARTREE:
        raise ValueError(unit)
    rows = list(rows)
    hartree = [v * UNIT_TO_HARTREE[unit] for _, v in rows]
    _check(hartree, temperature)
    low = min(hartree)
    return [(name, value, (h - low) * out_factor, p)
            for (name, value), h, p in zip(rows, hartree, shares(hartree, temperature))]


def files_table(paths, temperature, out_factor, read=None):
    from modules.spectrum.analysis import reaction

    read = read or reaction.read_species
    species = [read(str(p), Path(p).stem) for p in paths]
    if not species:
        raise ValueError('Не выбрано ни одного файла.')
    gibbs = []
    for s in species:
        found = reaction.corrections(s, temperature)
        gibbs.append(None if found is None or found[2] is None else s.energy + found[2])
    by = 'G' if all(g is not None for g in gibbs) else 'E'
    key = gibbs if by == 'G' else [s.energy for s in species]
    low_e = min(s.energy for s in species)
    low_g = min(g for g in gibbs if g is not None) if any(g is not None for g in gibbs) else None
    rows = [(s.label, s.program, s.level, s.energy, g, (s.energy - low_e) * out_factor,
             None if g is None else (g - low_g) * out_factor, p)
            for s, g, p in zip(species, gibbs, shares(key, temperature))]
    # the warnings of reaction.suitability are the notes of the results too (as in the diagram of a reaction)
    warnings = reaction.suitability(species, 'ensemble')
    if by == 'E' and any(g is not None for g in gibbs):
        warnings.append(tr('Частоты есть не у всех — доли посчитаны по E, не по G.'))
    typed = tr('введено вручную')  # not a doubt about the result
    notes = {s.label: kept for s in species if (kept := tuple(n for n in s.notes if n != typed))}
    return {'rows': rows, 'by': by, 'warnings': warnings, 'notes': notes}

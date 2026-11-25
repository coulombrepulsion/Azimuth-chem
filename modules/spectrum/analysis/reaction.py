"""Spectrum: the energy diagram of a reaction from several calculation results.

HEADER A reaction is a row of stages (reactants, intermediates, transition states, products); a stage is one or more
    species (A + B), each a result of a calculation (ORCA, Gaussian, xtb, Psi4 — modules/spectrum/readers/outputs.py) or
    numbers typed in by hand. The diagram shows ΔE, ΔE₀ (with ZPE), ΔH or ΔG of every stage relative to a chosen one,
    marks the stages with a transition state, and gives the barriers and the energy of reaction. It also checks what a
    student easily gets wrong: every stage must have the same atoms and the same total charge, and all species should be
    computed at one level of theory. Wilkinson convention, sections 1-8.

§1 THEORY
    The energy of a stage is the sum over its species: X_stage = Σ X_i, X ∈ {E, E₀ = E + ZPE, H = E + H_corr,
    G = E + G_corr}; E is the electronic energy of the result (the correlated one if the program printed it),
    the corrections are those of the ideal gas, rigid rotor and harmonic oscillator at T and P
    (modules/spectrum/analysis/thermo.py, with σ from the point group and 2S + 1 from the output). Relative values:
    ΔX_k = (X_k − X_ref)·u, u = 627.5094740631 kcal/mol, 2625.4996394799 kJ/mol or 27.211386245988 eV per
    hartree (CODATA 2018).
    A species with exactly one imaginary frequency is a transition state (a first-order saddle point); a stage
    with one is a TS stage. For a TS stage k: the forward barrier ΔX‡ = X_k − X_j (j — the nearest minimum stage
    before k), the reverse one X_k − X_l (l — the nearest minimum stage after k). The energy of reaction is
    X_last − X_first.
    Standard state 1 mol/L instead of the ideal gas at P (only for G): each species gets
    ΔG°(1 M) = RT ln(RT c° / P), c° = 1000 mol/m³ — 1.894 kcal/mol at 298.15 K and 1 atm; it matters only when the
    number of molecules changes along the reaction (A + B → C).

§2 ALGORITHM
    species_from_output(output, text, path): E, the geometry (that of the frequencies if any), the frequencies,
    2S + 1 (thermo.multiplicity), the charge (charge_of), the level of theory (level_of_theory), σ (point group by
    modules/compass/chemistry/symmetry.py; 1 if it cannot be found), the atoms (counts). corrections(species, T, P,
    qrrho)
    -> (ZPE, H_corr, G_corr) or None (no real frequencies and nothing typed in); memoised.
    profile(stages, quantity, unit, reference, T, P, qrrho, molar): the absolute values of the stages (None where
    a species has no corrections and H or G is asked for), the relative ones, the kinds ('ts' / 'min'), the
    barriers, the energy of reaction and the warnings: a stage without a value, atoms or charge not those of the
    reference stage, more than one imaginary frequency, different levels of theory, an unconfirmed normal
    termination, corrections typed in by hand (they do not follow T).
    Suitability(species, purpose 'profile' | 'ensemble') -> [warning] — shared with boltzmann.files_table.
    save(stages, settings, folder) -> dict and load(data, folder, read) -> (stages, settings): a .json diagram
    with the paths of the results (relative to the file where possible) and the hand-typed numbers.

§3 APPLICATIONS
    modules/spectrum/views/reaction_view.py — «Файл → Диаграмма реакции…» of Spectrum and «В диаграмму реакции» on
    the results page.

§4 SPECIFICATION
    Species(label, energy, geometry=None, frequencies=(), multiplicity=1, charge=None, sigma=1, level='',
            program='', path='', counts=(), typed=None, notes=(), marked_ts=False) — typed: (ZPE, H_corr, G_corr)
            in hartree (None entries allowed) for a species typed in by hand; marked_ts — typed in as a TS.
    Stage(label, species). QUANTITIES = ('E', 'E0', 'H', 'G'); UNITS = {'kcal', 'kj', 'ev'}.
    profile(...) -> Profile(quantity, unit, labels, absolute, values, kinds, barriers, reaction, warnings).
    Barrier(ts, start, end, forward, reverse) — stage indices (start / end may be None) and values in the unit.
    rows(profile, stages) -> list of rows for a table (stage, species, kind, X in hartree, ΔX in the unit).
    read_species(path) -> Species. ValueError with a message for the user on every invalid input.

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    The level of theory is read best-effort: the «!» lines of the ORCA input echo, the method and basis of the
    Gaussian archive (or its route line), «xtb» for xtb; job keywords (Opt, Freq, TightSCF …) are dropped, the
    rest is compared as a set. Psi4: not read (no warning). ASSUMPTION: the user's outputs carry the input echo
    (ORCA prints it by default).

§7 TEST CASES (tests/spectrum/test_reaction.py)
    Hand-computed ΔE, barriers and energy of reaction in kcal/mol, kJ/mol and eV; sums over a stage; the 1 M
    correction (1.894 kcal/mol, RT ln 24.465); G without frequencies is missing and named; the atom and charge
    balance; two imaginary frequencies; the levels of ORCA and Gaussian; a real result (Psi4, divinylbenzene) —
    the corrections equal those printed by Psi4; save and load.

§8 ERROR ANALYSIS
    The energies are differences of large numbers: the outputs print 8–10 decimals of a hartree, 1e-8 Eh ≈
    6e-6 kcal/mol — far below the shown 0.1. The corrections carry the errors of RRHO (thermo.py §8), usually
    0.5–1 kcal/mol for G of flexible molecules (low modes; quasi-RRHO helps).
"""

from __future__ import annotations

import functools
import math
import re
from dataclasses import dataclass, field
from pathlib import Path

from modules.spectrum.analysis import thermo
from azimuth.i18n import tr

QUANTITIES = ('E', 'E0', 'H', 'G')
EV = 27.211386245988  # eV per hartree, CODATA 2018
UNITS = {'kcal': thermo.KCAL, 'kj': thermo.KJ, 'ev': EV}
ATM = 101325.0
C_STANDARD = 1000.0  # mol/m³ = 1 mol/L

# words of an input line that say what to do, not at which level (ORCA «!» line, Gaussian route), upper case
JOB_WORDS = {
    'OPT', 'FREQ', 'NUMFREQ', 'ANFREQ', 'TIGHTOPT', 'VERYTIGHTOPT', 'LOOSEOPT', 'COPT', 'ZOPT', 'GDIIS-COPT',
    'OPTTS', 'SCANTS', 'IRC', 'NEB', 'NEB-CI', 'NEB-TS', 'ZOOM-NEB-CI', 'SP', 'ENERGY', 'ENGRAD', 'NUMGRAD',
    'TIGHTSCF', 'VERYTIGHTSCF', 'NORMALSCF', 'LOOSESCF', 'SLOPPYSCF', 'EXTREMESCF', 'STRONGSCF', 'NOAUTOSTART',
    'PRINTBASIS', 'LARGEPRINT', 'MINIPRINT', 'NORMALPRINT', 'SMALLPRINT', 'KEEPDENS', 'NMR', 'MOREAD', 'UNO',
    'PAL2', 'PAL4', 'PAL6', 'PAL8', 'PAL16', 'PAL32', 'GRID4', 'GRID5', 'GRID6', 'FINALGRID5', 'FINALGRID6',
    'DEFGRID1', 'DEFGRID2', 'DEFGRID3', 'XYZFILE', 'PDBFILE', 'HIRSHFELD', 'MULLIKEN', 'LOEWDIN', 'NBO',
    'CHELPG', 'MAYER', 'NOPOP', 'NOSYMM', 'SYMMETRY', 'TEST', 'POP', 'SCF', 'INT', 'INTEGRAL', 'GEOM', 'GUESS',
    'IOP', 'OUTPUT', 'PUNCH', 'GFINPUT', 'GFPRINT', 'UNITS', 'TD', 'TDA', 'CIS', 'SCAN', 'FORCE', 'STABLE',
}
_NUMBER = r'[-+]?\d+(?:\.\d*)?(?:[EeDd][-+]?\d+)?'


@dataclass(frozen=True)
class Species:
    label: str
    energy: float
    geometry: object = None
    frequencies: tuple = ()
    multiplicity: int = 1
    charge: int | None = None
    sigma: int = 1
    level: str = ''
    program: str = ''
    path: str = ''
    counts: tuple = ()
    typed: tuple | None = None
    notes: tuple = ()
    marked_ts: bool = False  # typed in by hand as a transition state
    facts: tuple = ()  # the codes of modules/spectrum/analysis/quality.py (FACTS)

    @property
    def imaginary(self):
        return tuple(f for f in self.frequencies if f < 0)

    @property
    def is_ts(self):
        return self.marked_ts or len(self.imaginary) == 1

    @property
    def formula(self):
        return ''.join(s + (str(n) if n > 1 else '') for s, n in self.counts)


@dataclass(frozen=True)
class Stage:
    label: str
    species: tuple

    @property
    def kind(self):
        return 'ts' if any(s.is_ts for s in self.species) else 'min'


@dataclass(frozen=True)
class Barrier:
    ts: int
    start: int | None
    end: int | None
    forward: float | None
    reverse: float | None


@dataclass(frozen=True)
class Profile:
    quantity: str
    unit: str
    labels: tuple
    absolute: tuple
    values: tuple
    kinds: tuple
    barriers: tuple
    reaction: float | None
    warnings: tuple = field(default=())
    reference: int = 0


def counts_of(molecule):
    """((symbol, number), …) of a Molecule, C and H first (Hill order), or () without atoms."""
    if molecule is None or not getattr(molecule, 'atoms', None):
        return ()
    found = {}
    for atom in molecule.atoms:
        found[atom.symbol] = found.get(atom.symbol, 0) + 1
    order = (['C', 'H'] + sorted(set(found) - {'C', 'H'})) if 'C' in found else sorted(found)
    return tuple((s, found[s]) for s in order if s in found)


def charge_of(text):
    """The total charge printed by ORCA, Gaussian or Psi4 (the last one), or None."""
    found = re.findall(r'Total Charge\s+Charge\s+\.+\s+(-?\d+)', text)  # ORCA
    found += re.findall(r'Charge\s*=\s*(-?\d+)\s+Multiplicity\s*=', text)  # Gaussian
    found += re.findall(r'charge\s*=\s*(-?\d+),\s*multiplicity\s*=', text)  # Psi4
    return int(found[-1]) if found else None


def _keywords(words):
    out = set()
    for word in words:
        word = re.sub(r'^LIBXC\((.+)\)$', r'\1', word.strip().upper())  # LibXC(B3LYP) is the level B3LYP
        if not word or word.startswith('#') or word.startswith('%'):
            continue
        base = re.split(r'[(=]', word, maxsplit=1)[0]
        if base in JOB_WORDS or base.startswith('PAL') and base[3:].isdigit():
            continue
        out.add(re.sub(r'^(RO|R|U)(?=[A-Z0-9])', '', word) if '/' in word or word in ('RHF', 'UHF', 'ROHF') else word)
    return out


def level_of_theory(text, program=''):
    """The method and basis an output was computed with, as a normalised text (§6), or ''."""
    if not text:
        return ''
    if 'xtb' in program.lower():
        return 'XTB'
    if 'Gaussian' in program or 'Entering Gaussian System' in text[:20000]:
        joined = text.replace('\n ', '')
        archive = re.findall(r'1\\1\\[^\\]*\\[^\\]*\\([^\\]+)\\([^\\]+)\\', joined)
        if archive:
            method, basis = archive[-1]
            return ' '.join(sorted(_keywords([method + '/' + basis])))
        route = re.search(r'^ (#.*)$', text, re.M)
        return ' '.join(sorted(_keywords(route[1].split()))) if route else ''
    lines = re.findall(r'^\|\s*\d+>\s*!(.*)$', text, re.M)  # ORCA: the echo of the input file
    words = [w for line in lines for w in line.split()]
    return ' '.join(sorted(_keywords(words)))


def _sigma(geometry):
    try:
        from modules.compass.chemistry.symmetry import analyze

        found = analyze(geometry)
        return thermo.symmetry_number(found.get('name', '') if 'err' not in found else '')
    except Exception:  # noqa: BLE001 — σ is only a proposal; 1 when the group is not found
        return 1


def species_from_output(output, text='', path='', label=None):
    """A Species of a calculation result (modules/spectrum/readers/orca.Output) and the text it was read from."""
    if output.final_energy:
        energy = float(output.final_energy[1])
    elif output.energies:
        energy = float(output.energies[-1])
    else:
        raise ValueError(tr('В результате нет энергии: ') + (Path(path).name if path else tr('текущий результат')))
    geometry = output.vibration_geometry or output.geometry
    frequencies = tuple(float(f) for _, f in output.frequencies)
    notes, facts = [], []
    # the facts of the output from the output itself (Output.facts) — one set of rules with its assessment
    raw = set(getattr(output, 'facts', ()) or ())
    if 'demo' in raw:
        notes.append(tr('учебный пример, не настоящий расчёт'))
        facts.append('demo')
    if 'normal_exit_unconfirmed' in raw:
        notes.append(tr('нормальное завершение не подтверждено'))
        facts.append('normal_exit_unconfirmed')
    if text and thermo.find_multiplicity(text) is None and frequencies:  # no silent singlet
        notes.append(tr('мультиплетность в выводе не найдена — взята 1'))
    # facts as codes (quality.py) — also what had no note: SCF, an optimization that did not converge, a
    # value taken by default (the multiplicity) or not read (the charge)
    for code in ('scf_failed', 'optimization_unconverged'):
        if code in raw:
            facts.append(code)
    if not text or thermo.find_multiplicity(text) is None:
        facts.append('multiplicity_default')
    charge = charge_of(text) if text else None
    if charge is None:
        facts.append('charge_unknown')
    name = label or (Path(path).stem if path else '') or (geometry.title if geometry is not None and geometry.title else '')
    counts = counts_of(geometry)
    if not name:
        name = ''.join(s + (str(n) if n > 1 else '') for s, n in counts) or tr('вещество')
    return Species(
        label=name,
        energy=energy,
        geometry=geometry,
        frequencies=frequencies,
        multiplicity=(thermo.find_multiplicity(text) or 1) if text else 1,
        charge=charge,
        sigma=_sigma(geometry) if geometry is not None and frequencies else 1,
        level=level_of_theory(text, output.program),
        program=output.program,
        path=str(path or ''),
        counts=counts,
        notes=tuple(notes),
        facts=tuple(facts),
    )


def read_species(path, label=None):
    """Read a result file into a Species (ValueError with a message when it cannot be read)."""
    from modules.spectrum.readers.outputs import read_any

    p = Path(path)
    try:
        from modules.spectrum.readers.results import MAX_BYTES, too_large

        if p.stat().st_size > MAX_BYTES:  # 256 MB (was 32)
            raise too_large()
        text = p.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        raise ValueError(tr('Не удалось прочитать файл: ') + f'{p.name} ({exc})') from exc
    return species_from_output(read_any(text, str(p)), text, str(p), label)


def typed_species(label, energy, zpe=None, enthalpy=None, gibbs=None, formula='', charge=None, ts=False):
    """A species typed in by hand: E and the corrections ZPE, H − E, G − E in hartree (None — not known);
    ts — it is a transition state."""
    if not label or not str(label).strip():
        raise ValueError(tr('У вещества должно быть название.'))
    values = [energy, zpe, enthalpy, gibbs]
    for v in values:
        if v is not None and not (isinstance(v, (int, float)) and math.isfinite(v)):
            raise ValueError(tr('Энергии должны быть числами.'))
    if energy is None:
        raise ValueError(tr('Нужна электронная энергия E (хартри).'))
    counts = parse_formula(formula) if formula else ()
    return Species(
        label=str(label).strip(), energy=float(energy), counts=counts, charge=charge,
        typed=(zpe, enthalpy, gibbs), notes=(tr('введено вручную'),), marked_ts=bool(ts),
        facts=('typed',) + (() if charge is not None else ('charge_unknown',)),
    )


def parse_formula(text):
    """((symbol, n), …) of a formula such as C2H6O (no brackets); ValueError otherwise."""
    text = text.strip()
    parts = re.findall(r'([A-Z][a-z]?)(\d*)', text)
    if not parts or ''.join(s + n for s, n in parts) != text:
        raise ValueError(tr('Формула пишется так: C2H6O (без скобок).'))
    found = {}
    for symbol, n in parts:
        found[symbol] = found.get(symbol, 0) + (int(n) if n else 1)
    order = (['C', 'H'] + sorted(set(found) - {'C', 'H'})) if 'C' in found else sorted(found)
    return tuple((s, found[s]) for s in order if s in found)


@functools.lru_cache(maxsize=512)
def corrections(species, temperature=298.15, pressure=ATM, qrrho=False):
    """(ZPE, H − E, G − E) in hartree per molecule, or None when they are not known (§2)."""
    if species.typed is not None:
        return species.typed
    real = [f for f in species.frequencies if f > 1e-6]
    if species.geometry is None or not real:
        return None
    r = thermo.thermochemistry(
        species.geometry, species.frequencies, None, temperature, pressure, species.multiplicity or 1,
        species.sigma or 1, qrrho,
    )
    return r.zpe, r.enthalpy, r.gibbs


def molar_shift(temperature, pressure):
    """ΔG°(1 M) of one species in hartree: RT ln(RT c° / P) (§1)."""
    r = thermo.R
    return r * temperature * math.log(r * temperature * C_STANDARD / pressure) / (thermo.HARTREE * thermo.NA)


def value(species, quantity, temperature=298.15, pressure=ATM, qrrho=False, molar=False):
    """X of one species in hartree (§1), or None when the needed correction is not known."""
    if quantity == 'E':
        return species.energy
    c = corrections(species, temperature, pressure, qrrho)
    index = {'E0': 0, 'H': 1, 'G': 2}[quantity]
    if c is None or c[index] is None:
        return None
    out = species.energy + c[index]
    if quantity == 'G' and molar:
        out += molar_shift(temperature, pressure)
    return out


def _balance(counts):
    total = {}
    for c in counts:
        for symbol, n in c:
            total[symbol] = total.get(symbol, 0) + n
    return total


def _difference(a, b):
    keys = sorted(set(a) | set(b), key=lambda s: (s not in ('C', 'H'), s != 'C', s))
    return ', '.join(f'{s}: {b.get(s, 0) - a.get(s, 0):+d}' for s in keys if a.get(s, 0) != b.get(s, 0))


def profile(stages, quantity='E', unit='kcal', reference=0, temperature=298.15, pressure=ATM, qrrho=False,
            molar=False):
    """The diagram of §1–§2 (see Profile, Barrier). ValueError on invalid input."""
    stages = list(stages)
    if not stages:
        raise ValueError(tr('Добавьте хотя бы одну стадию.'))
    if quantity not in QUANTITIES or unit not in UNITS:
        raise ValueError(tr('Неизвестная величина или единица.'))
    if not (isinstance(reference, int) and 0 <= reference < len(stages)):
        raise ValueError(tr('Опорная стадия выбрана неверно.'))
    if not (temperature > 0 and pressure > 0):
        raise ValueError(tr('Температура и давление должны быть больше нуля.'))
    for stage in stages:
        if not stage.species:
            raise ValueError(tr('В стадии нет веществ: ') + stage.label)
    factor = UNITS[unit]
    warnings = []
    absolute = []
    for stage in stages:
        parts = [value(s, quantity, temperature, pressure, qrrho, molar) for s in stage.species]
        missing = [s.label for s, v in zip(stage.species, parts) if v is None]
        if missing:
            names = ', '.join(missing)
            warnings.append(tr(f'Нет поправок (нужен расчёт частот): {names} — стадия «{stage.label}» не показана.'))
            absolute.append(None)
        else:
            absolute.append(sum(parts))
    ref = absolute[reference]
    values = tuple(None if a is None or ref is None else (a - ref) * factor for a in absolute)
    kinds = tuple(stage.kind for stage in stages)
    barriers = []
    for k, kind in enumerate(kinds):
        if kind != 'ts' or values[k] is None:
            continue
        start = next((j for j in range(k - 1, -1, -1) if kinds[j] == 'min' and values[j] is not None), None)
        end = next((j for j in range(k + 1, len(stages)) if kinds[j] == 'min' and values[j] is not None), None)
        barriers.append(Barrier(
            k, start, end,
            None if start is None else values[k] - values[start],
            None if end is None else values[k] - values[end],
        ))
    reaction = None if values[0] is None or values[-1] is None or len(stages) < 2 else values[-1] - values[0]
    # what a student easily gets wrong
    known = [all(s.counts for s in stage.species) for stage in stages]
    if known[reference]:
        base = _balance(s.counts for s in stages[reference].species)
        for stage, ok in zip(stages, known):
            if ok:
                other = _balance(s.counts for s in stage.species)
                if other != base:
                    diff = _difference(base, other)
                    warnings.append(tr(f'Атомы не сходятся: «{stage.label}» против «{stages[reference].label}» ({diff})'))
    charges = [[s.charge for s in stage.species] for stage in stages]
    if all(c is not None for row in charges for c in row):
        totals = [sum(row) for row in charges]
        for stage, total in zip(stages, totals):
            if total != totals[reference]:
                warnings.append(tr(f'Заряд не сходится: у «{stage.label}» {total:+d}, у опорной стадии {totals[reference]:+d}'))
    warnings += suitability([s for stage in stages for s in stage.species], 'profile')  # shared
    if quantity in ('H', 'G') and any(s.typed is not None for stage in stages for s in stage.species):
        warnings.append(tr('Поправки, введённые вручную, не меняются с температурой и давлением.'))
    return Profile(
        quantity, unit, tuple(s.label for s in stages), tuple(absolute), values, kinds, tuple(barriers), reaction,
        tuple(dict.fromkeys(warnings)), reference,
    )


def suitability(species, purpose):
    """The warnings every tool comparing results gives the same way —
    profile() (purpose 'profile') and boltzmann.files_table() ('ensemble'). The texts of the findings of
    modules/spectrum/analysis/quality.py (codes and severities there: what is a doubt, what is not enough data)."""
    from modules.spectrum.analysis import quality

    return quality.messages(quality.findings(species, purpose))


def rows(result, stages, temperature=298.15, pressure=ATM, qrrho=False, molar=False):
    """Table rows: (stage, species, kind, X in hartree, ΔX in the unit) — a stage row, then its species."""
    out = []
    for k, stage in enumerate(stages):
        a, v = result.absolute[k], result.values[k]
        out.append((stage.label, '', 'TS' if result.kinds[k] == 'ts' else '', '' if a is None else f'{a:.8f}',
                    '' if v is None else f'{v:.2f}'))
        for s in stage.species:
            x = value(s, result.quantity, temperature, pressure, qrrho, molar)
            out.append(('', s.label + (f' ({s.formula})' if s.formula else ''), 'TS' if s.is_ts else '',
                        '' if x is None else f'{x:.8f}', ''))
    return out


# -- saving --------------------------------------------------------------------------------------------------
def save(stages, settings, folder=None):
    """The diagram as a JSON-ready dict; paths relative to folder where they lie under it."""
    def where(path):
        if not path:
            return None
        p = Path(path)
        if folder is not None:
            try:
                return {'relative': p.resolve().relative_to(Path(folder).resolve()).as_posix(), 'absolute': str(p)}
            except ValueError:
                pass
        return {'absolute': str(p)}

    data = {'kind': 'azimuth-reaction', 'version': 1, 'settings': dict(settings), 'stages': []}
    for stage in stages:
        items = []
        for s in stage.species:
            if s.typed is not None or not s.path:
                items.append({
                    'label': s.label, 'energy': s.energy, 'typed': list(s.typed) if s.typed else [None, None, None],
                    'formula': s.formula, 'charge': s.charge, 'ts': s.is_ts,
                })
            else:
                items.append({'label': s.label, 'file': where(s.path)})
        data['stages'].append({'label': stage.label, 'species': items})
    return data


def load(data, folder=None, read=read_species):
    """(stages, settings, problems) from save(); a result that cannot be read is left out and named."""
    if not isinstance(data, dict) or data.get('kind') != 'azimuth-reaction' or not isinstance(data.get('stages'), list):
        raise ValueError(tr('Это не файл диаграммы реакции Азимута.'))
    stages, problems = [], []
    for entry in data['stages']:
        if not isinstance(entry, dict):
            raise ValueError(tr('Файл диаграммы повреждён.'))
        species = []
        for item in entry.get('species', []):
            if not isinstance(item, dict):
                raise ValueError(tr('Файл диаграммы повреждён.'))
            if 'file' in item and item['file']:
                where = item['file']
                candidates = []
                if folder is not None and where.get('relative'):
                    candidates.append(Path(folder) / where['relative'])
                if where.get('absolute'):
                    candidates.append(Path(where['absolute']))
                path = next((c for c in candidates if c.is_file()), None)
                if path is None:
                    problems.append(tr('Не найден файл: ') + str(where.get('relative') or where.get('absolute')))
                    continue
                try:
                    species.append(read(str(path), item.get('label')))
                except ValueError as exc:
                    problems.append(f'{path.name}: {exc}')
            else:
                typed = item.get('typed') or [None, None, None]
                species.append(typed_species(
                    item.get('label', ''), item.get('energy'), *(list(typed) + [None] * 3)[:3],
                    formula=item.get('formula') or '', charge=item.get('charge'), ts=bool(item.get('ts')),
                ))
        if species:
            stages.append(Stage(str(entry.get('label', '')), tuple(species)))
    settings = data.get('settings') if isinstance(data.get('settings'), dict) else {}
    return stages, settings, problems

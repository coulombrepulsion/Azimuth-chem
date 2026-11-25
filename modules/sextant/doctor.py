"""The doctor of a calculation: what went wrong in a calculation, why, and — where a safe remedy is known — the
settings to repeat it with.
§1 PURPOSE
    Sextant told what went wrong (runner.diagnose) and what to change by hand. The remedy is mechanical in many cases:
    a harder SCF convergence, twice the cycles from the last geometry, fewer processes with more memory each. The doctor
    names it and gives the changed settings; the window repeats the calculation with them at one click.
§2 RULES
    1. examine(kind, text, code, calc, molecule=None, edited=False) -> [Remedy] — one for each problem recognised
       (runner.problem_keys: at most two), in their order. A Remedy with label '' has no automatic repeat: the advice
       alone (a full disk, a basis the doctor cannot choose).
    2. A remedy changes only settings of the calculation (Calculation fields), may ask to start from the last
       geometry of the output (last_geometry) or to build the input file anew (rebuild_input: it was edited by hand).
       It never changes the method, the basis or the state of the molecule on its own judgement, with three
       exceptions said in its label: a basis that has no functions for an element → def2-SVP; a functional ORCA
       cannot use for the task → PBE0; a multiplicity impossible for the number of electrons → the lowest possible.
    3. A remedy already applied is not offered again: SlowConv → VerySlowConv → advice only; one process cannot be
       halved; def2-SVP is not replaced by itself. So the repeats end.
    4. Remedies (key of the problem → change):
       SCF not converged slow_conv '' → 'SlowConv' → 'VerySlowConv' (not xtb, not MOPAC: no such setting)
       optimization not converged max_cycles × 2 (at least 200; 0 — the program's limit — stays) + last geometry
       not enough memory / killed cores // 2 and memory per process × 2 (the same total); one process: memory × 2
       MPI failure cores = 16 when there were more, else 1; an optimization from its last geometry
       input error, edited by hand rebuild_input
       no basis for an element basis = 'def2-SVP'
       functional not usable method = 'PBE0'
       charge and multiplicity multiplicity = 1 for an even number of electrons, 2 for an odd one (molecule given)
       full disk, CREST 3.0.2 advice only
    5. An optimization stopped — «Продолжить с последней геометрии» (STOPPED, stopped()); an optimization with
    frequencies that ended with an
       imaginary frequency (not a search of a transition state) — not a minimum: «Сдвинуть по мнимой моде и
       оптимизировать заново» (IMAGINARY, imaginary(): the geometry moved along the mode of the lowest frequency by
       NUDGE Å at the atom that moves most, the optimization tight); above −SMALL_CM cm⁻¹ — SMALL_IMAGINARY: a nearly
       free rotor or noise, practically a minimum (the methyl of toluene in GFN2-xTB stays at −11 cm⁻¹ even after the
       step), the same remedy offered.
§3 INTERFACE
    Remedy(key, what, why, label, changes, last_geometry, rebuild_input, displace); examine(...); apply(calc, remedy) ->
    Calculation; last_geometry(text, path=None) -> Molecule | None (the last geometry the output holds);
    stopped(calc) -> Remedy | None; imaginary(kind, text, calc, path=None) -> Remedy | None; displaced(text, path=None,
    step=NUDGE) -> Molecule | None.
§4 TESTS tests/sextant/test_doctor.py — real outputs of the test data cut where they fail, and the rules of §2."""

from __future__ import annotations

from dataclasses import dataclass, field, replace

from azimuth.i18n import tr
from modules.sextant import runner

SCF = 'Самосогласованное поле (SCF) не сошлось.'
OPT = 'Оптимизация геометрии не сошлась за отведённые циклы.'
MEMORY = 'Не хватило памяти.'
INPUT = 'Ошибка во входном файле.'
BASIS = 'Базиса нет для одного из элементов.'
STATE = 'Заряд и мультиплетность не подходят к молекуле.'
MPI = 'Сбой параллельного запуска (MPI).'
MPI_CORES = 16  # the processes a repeat after an MPI failure on many takes
FUNCTIONALS = ('ORCA не считает оптимизацию возбуждённого состояния с этим функционалом.',
               'ORCA не считает градиенты возбуждённых состояний с мета-GGA функционалом.')
SLOW = ('', 'SlowConv', 'VerySlowConv')
NO_SLOW = ('xtb', 'mopac', 'crest')
SAFE_BASIS, SAFE_FUNCTIONAL = 'def2-SVP', 'PBE0'
MIN_CYCLES = 200
STOPPED = 'Расчёт остановлен до конца оптимизации.'
IMAGINARY = 'Есть мнимая частота: структура — не минимум.'
SMALL_IMAGINARY = 'Маленькая мнимая частота: почти свободное вращение группы или шум гессиана.'
SMALL_CM = 30.0  # cm⁻¹: a smaller imaginary frequency is a nearly free rotor (a methyl of toluene) or numerical noise
NUDGE = 0.15  # Å: the largest move of an atom along the imaginary mode


@dataclass(frozen=True)
class Remedy:
    key: str  # the problem (its text in runner.PROBLEMS, not translated)
    what: str  # the problem, in the language of the program
    why: str
    label: str = ''  # the button of the repeat ('' — advice only)
    changes: dict = field(default_factory=dict)  # Calculation fields to set
    last_geometry: bool = False
    rebuild_input: bool = False
    displace: bool = False  # start from the geometry moved along the imaginary mode (displaced)


def _electrons(molecule, charge):
    from azimuth.core import Z

    return sum(Z.get(a.symbol, 0) for a in molecule.atoms) - int(charge)


def _remedy(key, kind, calc, molecule, edited):
    """(label, changes, last_geometry, rebuild_input) for the problem key, or None — advice only (§2.3–4)."""
    if key == SCF:
        if kind in NO_SLOW or calc.slow_conv not in SLOW[:2]:
            return None
        harder = SLOW[SLOW.index(calc.slow_conv) + 1]
        name = tr('трудной') if harder == 'SlowConv' else tr('очень трудной')
        return tr('Повторить с {} сходимостью SCF').format(name), {'slow_conv': harder}, False, False
    if key == OPT:
        cycles = 0 if calc.max_cycles == 0 else max(MIN_CYCLES, 2 * calc.max_cycles)
        label = (tr('Продолжить с последней геометрии') if cycles == 0 else
                 tr('Продолжить с последней геометрии, циклов: {}').format(cycles))
        return label, {'max_cycles': cycles}, True, False
    if key in (MEMORY, runner.KILLED):
        if calc.cores > 1:
            cores, memory = calc.cores // 2, calc.memory_mb * 2
        else:
            cores, memory = 1, calc.memory_mb * 2
        return (tr('Повторить: процессов {}, память на процесс {} МБ').format(cores, memory),
                {'cores': cores, 'memory_mb': memory}, False, False)
    if key == MPI:
        if calc.cores <= 1:
            return None
        # 41 processes on a server broke in MPI_Init again and again — fewer of them first, and an
        # optimization goes on from where it stopped
        cores = MPI_CORES if calc.cores > MPI_CORES else 1
        again = 'Оптимизация' in (calc.task or '') or 'Скан' in (calc.task or '')
        label = tr('Повторить на одном процессе') if cores == 1 else tr('Повторить на {} процессах').format(cores)
        if again:
            label += tr(', с последней геометрии')
        return label, {'cores': cores}, again, False
    if key == INPUT:
        return (tr('Собрать входной файл заново и повторить'), {}, False, True) if edited else None
    if key == BASIS:
        if calc.basis == SAFE_BASIS:
            return None
        return tr('Повторить с базисом {}').format(SAFE_BASIS), {'basis': SAFE_BASIS}, False, False
    if key in FUNCTIONALS:
        if calc.method == SAFE_FUNCTIONAL:
            return None
        return tr('Повторить с функционалом {}').format(SAFE_FUNCTIONAL), {'method': SAFE_FUNCTIONAL}, False, False
    if key == STATE and molecule is not None and molecule.atoms:
        lowest = 1 if _electrons(molecule, calc.charge) % 2 == 0 else 2
        if (calc.multiplicity - lowest) % 2 == 0:
            return None  # the parity is right: the program meant something else
        return tr('Повторить с мультиплетностью {}').format(lowest), {'multiplicity': lowest}, False, False
    return None


def examine(kind, text, code, calc, molecule=None, edited=False):
    found = []
    for key, why in runner.problem_keys(kind, text, code):
        remedy = _remedy(key, kind, calc, molecule, edited)
        label, changes, geometry, rebuild = remedy if remedy else ('', {}, False, False)
        found.append(Remedy(key, tr(key), tr(why), label, dict(changes), geometry, rebuild))
    return found


def apply(calc, remedy):
    """The settings of the repeat (the fields of remedy.changes replaced)."""
    return replace(calc, **remedy.changes) if remedy.changes else calc


def last_geometry(text, path=None):
    """The last geometry an output holds — the last step of its optimization, else its geometry; None when it has none
    or cannot be read."""
    from modules.spectrum.readers.outputs import read_any

    try:
        output = read_any(text, path)
    except Exception:  # noqa: BLE001 — an output that cannot be read gives no geometry
        return None
    steps = [s.geometry for s in (getattr(output, 'steps', ()) or ()) if getattr(s, 'geometry', None) is not None]
    return steps[-1] if steps else getattr(output, 'geometry', None)


def _optimizes(calc):
    from azimuth.core import TASKS

    return 'Opt' in TASKS.get(calc.task, '')


def stopped(calc):
    """§2.5: the remedy of an optimization stopped before its end — on from its last geometry; None for another task."""
    if not _optimizes(calc):
        return None
    return Remedy(STOPPED, tr(STOPPED), tr('Сделанные шаги сохранены в выходном файле: оптимизация продолжится с последней '
                                           'геометрии с теми же настройками.'),
                  tr('Продолжить с последней геометрии'), {}, True, False)


def _vibrations(text, path=None):
    from modules.spectrum.readers.outputs import read_any

    try:
        return read_any(text, path)
    except Exception:  # noqa: BLE001 — an output that cannot be read gives nothing
        return None


def imaginary(kind, text, calc, path=None):
    """§2.5: an optimization with frequencies (or the frequencies alone) of a minimum that ended with an imaginary
    frequency — the remedy «move along it and optimize again», or None."""
    from azimuth.core import TASKS

    if calc.ts or 'Freq' not in TASKS.get(calc.task, '') or 'Переходное' in calc.task or kind in ('crest',):
        return None
    output = _vibrations(text, path)
    found = [f for _, f in (getattr(output, 'frequencies', ()) or ()) if f < 0]
    if output is None or not found or displaced(text, path, output=output) is None:
        return None
    lowest = min(found)
    if lowest > -SMALL_CM:
        return Remedy(SMALL_IMAGINARY, tr(SMALL_IMAGINARY),
                      tr('Мнимая частота {} см⁻¹ мала: так бывает у почти свободного вращения группы (метила) или от '
                         'неточности гессиана — геометрия практически минимум, энергия и термохимия почти не '
                         'меняются. Сдвиг вдоль моды и строгая сходимость часто убирают и её.').format(f'{lowest:.0f}'),
                      tr('Сдвинуть по мнимой моде и оптимизировать заново'),
                      {'task': 'Оптимизация + частоты', 'opt_conv': 'tight'}, False, False, True)
    return Remedy(IMAGINARY, tr(IMAGINARY), tr('Мнимая частота {} см⁻¹: молекула стоит на седле, а не в минимуме. '
                                               'Сдвиг вдоль этой моды и новая оптимизация (строгая сходимость) обычно '
                                               'уводят её в минимум.').format(f'{lowest:.0f}'),
                  tr('Сдвинуть по мнимой моде и оптимизировать заново'),
                  {'task': 'Оптимизация + частоты', 'opt_conv': 'tight'}, False, False, True)


def displaced(text, path=None, step=NUDGE, output=None):
    """The geometry of the frequencies moved along the mode of the lowest (imaginary) frequency so that the atom that
    moves most moves by step Å; None without such a mode."""
    from dataclasses import replace as _replace

    output = output or _vibrations(text, path)
    if output is None:
        return None
    modes = [m for m in (getattr(output, 'modes', ()) or ()) if m.frequency < 0 and m.vectors]
    base = getattr(output, 'vibration_geometry', None) or getattr(output, 'geometry', None)
    if not modes or base is None:
        return None
    mode = min(modes, key=lambda m: m.frequency)
    if len(mode.vectors) != len(base.atoms):
        return None
    largest = max((sum(v * v for v in row) ** 0.5 for row in mode.vectors), default=0.0)
    if largest <= 0:
        return None
    k = step / largest
    atoms = tuple(_replace(a, x=a.x + k * v[0], y=a.y + k * v[1], z=a.z + k * v[2]) for a, v in zip(base.atoms, mode.vectors))
    return _replace(base, atoms=atoms)

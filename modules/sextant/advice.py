"""Sextant: what the molecule suggests — charge and multiplicity, the computer's cores and memory, a method.

§1 THEORY
    Charge: formal charges of atoms whose bonds exceed their usual valence in one way only — N, P, As with four
    bonds (ammonium, pyridinium) +1, O, S, Se with three (oxonium) +1, B, Al with four (borate) −1. Everything else is
    counted neutral (an O–H or C with a missing bond may be a radical, an anion or a cation — the user decides).
    Multiplicity: a single atom — its ground term by Hund's rules (C, O: triplet; N: quartet; Cr: septet …);
    O₂ — triplet; otherwise the lowest one allowed by the number of electrons (1 for even, 2 for odd).
    Resources: the number of logical and physical cores and the memory of the computer (macOS sysctl, Linux
    /proc/meminfo, Windows GlobalMemoryStatusEx). A calculation uses one process per physical core, leaving one
    free when there are more than two, and about 60 % of the memory spread over the processes (ORCA %maxcore is
    per process and may be exceeded, hence the margin), between 500 and 8000 MB per process.
    Method: rules of the common practice of computational chemistry for teaching (not a guarantee for every
    molecule): geometries and frequencies with a hybrid functional with D3(BJ) dispersion in a double-ζ basis
    (B3LYP-D3(BJ)/def2-SVP), energies in a triple-ζ basis, diffuse functions for anions and excited states,
    range-separated functionals for TD-DFT (CAM-B3LYP), PBE0 for NMR shieldings, TPSSh or PBE0 for transition
    metals with a note on spin states, a GGA (PBE-D3(BJ)) for large molecules, MP2 for a few atoms.
§2 ALGORITHM
    guess_state(molecule) -> (charge, multiplicity, note); machine() -> Machine; recommended(machine) ->
    (processes, memory per process MB); recommend(molecule, task, kind, charge, multiplicity) -> Advice with the
    method, basis and dispersion available in that program, and the reasons in a sentence.
§3 APPLICATIONS
    modules/sextant/workspace.py: charge and multiplicity follow the molecule until the user changes them;
    the advice in the tooltips of the method and basis pickers and as their first menu item («★ Рекомендуется»);
    the processes and memory chosen on the first start, the advised values in their tooltips.
§4 SPECIFICATION
    above. Advice(method, basis, dispersion, text); Machine(logical, physical, memory_mb).
§5 PROCEDURES - below.
§6 NOTES
    ASSUMPTION: the recommendations follow reviews of DFT practice (Bursch, Mewes, Hansen, Grimme 2022 «Best-
    practice DFT protocols»; Goerigk & Grimme GMTKN55) in a simplified form, from memory.
§7 TESTS
    tests/sextant/test_advice.py.
§8' ROBUSTNESS
    Every probe of the computer may fail: then os.cpu_count() and no memory (the defaults of Sextant stay).
"""

from dataclasses import dataclass
import os
import subprocess
import sys

from azimuth.core import BASIS_TABLE, FREQ_TASK, FUKUI_TASK, TASKS, TDDFT_TASKS, TS_TASK, Z, bases_for, methods_for
from azimuth.i18n import tr

# ground-state multiplicities of the atoms H–Kr (Hund's rules)
ATOM_MULTIPLICITY = dict(zip(
    'H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr'.split(),
    (2, 1, 2, 1, 2, 3, 4, 3, 2, 1, 2, 1, 2, 3, 4, 3, 2, 1, 2, 1, 2, 3, 4, 7, 6, 5, 4, 3, 2, 1, 2, 3, 4, 3, 2, 1),
))
ONIUM = {'N': 4, 'P': 4, 'As': 4, 'O': 3, 'S': 3, 'Se': 3}  # bonds that make the atom +1
ATE = {'B': 4, 'Al': 4}  # bonds that make it −1
NMR_TASK = 'ЯМР (экранирование)'


def bond_valences(molecule):
    from modules.compass.chemistry.editing import perceived_orders

    valence = [0.0] * len(molecule.atoms)
    for i, j, order in perceived_orders(molecule):
        valence[i] += order
        valence[j] += order
    return [round(v) for v in valence]


def guess_state(molecule):
    """(charge, multiplicity, note) suggested by the structure."""
    atoms = molecule.atoms
    if not atoms:
        return 0, 1, ''
    if len(atoms) == 1:
        symbol = atoms[0].symbol
        return 0, ATOM_MULTIPLICITY.get(symbol, 2 if Z[symbol] % 2 else 1), tr('атом: основной терм по правилам Хунда')
    valence = bond_valences(molecule)
    charge = 0
    for atom, v in zip(atoms, valence):
        if ONIUM.get(atom.symbol) == v:
            charge += 1
        elif ATE.get(atom.symbol) == v:
            charge -= 1
    if sorted(a.symbol for a in atoms) == ['O', 'O']:
        return 0, 3, tr('O₂: основное состояние — триплет')
    electrons = molecule.electrons(charge)
    multiplicity = 1 if electrons % 2 == 0 else 2
    note = ''
    if any(21 <= Z[a.symbol] <= 30 for a in atoms):
        note = tr('у переходного металла проверьте спиновое состояние')
    elif multiplicity == 2:
        note = tr('нечётное число электронов: радикал')
    return charge, multiplicity, note


@dataclass(frozen=True)
class Machine:
    logical: int
    physical: int | None
    memory_mb: int | None


def _run(args):
    try:
        return subprocess.run(args, capture_output=True, text=True, timeout=3,
                              encoding='utf-8', errors='replace').stdout.strip()  # not the locale code page
    except (OSError, subprocess.SubprocessError):
        return ''


def machine():
    """Cores and memory of this computer; anything that cannot be read is None."""
    logical = os.cpu_count() or 1
    physical, memory = None, None
    try:
        if sys.platform == 'darwin':
            physical = int(_run(['/usr/sbin/sysctl', '-n', 'hw.physicalcpu']) or 0) or None
            memory = int(_run(['/usr/sbin/sysctl', '-n', 'hw.memsize']) or 0) // 2**20 or None
        elif sys.platform.startswith('linux'):
            with open('/proc/meminfo', encoding='ascii') as f:
                for line in f:
                    if line.startswith('MemTotal:'):
                        memory = int(line.split()[1]) // 1024
            cores = set()
            with open('/proc/cpuinfo', encoding='ascii', errors='replace') as f:
                phys = core = None
                for line in f:
                    if line.startswith('physical id'):
                        phys = line.split(':')[1].strip()
                    elif line.startswith('core id'):
                        core = line.split(':')[1].strip()
                    elif not line.strip() and core is not None:
                        cores.add((phys, core))
                        phys = core = None
            physical = len(cores) or None
        elif os.name == 'nt':
            import ctypes

            class Status(ctypes.Structure):
                _fields_ = [('length', ctypes.c_ulong), ('load', ctypes.c_ulong), ('total', ctypes.c_ulonglong),
                            ('avail', ctypes.c_ulonglong), ('page', ctypes.c_ulonglong), ('apage', ctypes.c_ulonglong),
                            ('virtual', ctypes.c_ulonglong), ('avirtual', ctypes.c_ulonglong), ('ext', ctypes.c_ulonglong)]

            status = Status()
            status.length = ctypes.sizeof(Status)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                memory = status.total // 2**20
    except (OSError, ValueError, AttributeError):
        pass
    return Machine(logical, physical, memory)


def recommended(m):
    """(processes, memory per process in MB) for this machine (§1)."""
    cores = m.physical or max(1, m.logical // 2)
    processes = max(1, min(16, cores - 1 if cores > 2 else cores))
    if not m.memory_mb:
        return processes, 1000
    per = int(0.6 * m.memory_mb / processes) // 100 * 100
    return processes, max(500, min(8000, per))


@dataclass(frozen=True)
class Advice:
    method: str
    basis: str
    dispersion: str
    text: str
    relativistic: str = ''  # a Hamiltonian to choose too (lanthanides, actinides in ORCA), '' — leave it


def _available(kind, method, basis, fallback_basis='def2-TZVP'):
    if method not in methods_for(kind):
        method = 'B3LYP'
    if basis not in bases_for(kind):
        basis = fallback_basis if fallback_basis in bases_for(kind) else 'def2-SVP'
    return method, basis


def _fits(basis, molecule):
    ranges = BASIS_TABLE[basis][4]
    return all(any(lo <= Z[a.symbol] <= hi for lo, hi in ranges) for a in molecule.atoms)


def recommend(molecule, task, kind, charge=0, multiplicity=1):
    """A sensible start for teaching (§1); None for xtb and CREST (GFN2-xTB has no choice) or no atoms."""
    if kind not in ('orca', 'gaussian', 'psi4') or not molecule.atoms:
        return None
    n = len(molecule.atoms)
    # the 4d and 5d metals are metals too (were only Sc–Zn), and the f elements need a Hamiltonian
    numbers = {Z[a.symbol] for a in molecule.atoms}
    metal = any(21 <= z <= 30 or 39 <= z <= 48 or 57 <= z <= 80 or 89 <= z <= 103 for z in numbers)
    f_block = sorted(z for z in numbers if 58 <= z <= 71 or z > 86)
    ecp = sorted(z for z in numbers if 37 <= z <= 57 or 72 <= z <= 86)
    method, basis, disp, why = 'B3LYP', 'def2-SVP', 'D3BJ', [tr('гибридный функционал с дисперсией D3(BJ) — надёжный старт для органических молекул')]
    if task in TDDFT_TASKS:
        method, basis = 'CAM-B3LYP', 'def2-SVPD'
        why = [tr('для UV-Vis — функционал с разделением по расстоянию (переходы с переносом заряда) и диффузные функции')]
    elif task == NMR_TASK:
        method, basis, disp = 'PBE0', 'def2-TZVP', ''
        why = [tr('экранирование ЯМР — гибрид PBE0 в трёхэкспонентном базисе, на геометрии из оптимизации')]
    elif task == FUKUI_TASK:
        basis = 'def2-SVPD'
        why = [tr('функции Фукуи: среди трёх расчётов — анион (N + 1), ему нужны диффузные функции; геометрия — из '
                  'оптимизации, одна для всех трёх')]
    elif metal:
        # the keywords of the task (the Russian name never contained «Opt»: the optimizations got PBE0/TZVP)
        method, basis = ('TPSSh', 'def2-SVP') if 'Opt' in TASKS.get(task, '') or task == FREQ_TASK else ('PBE0', 'def2-TZVP')
        why = [tr('переходный металл: TPSSh/PBE0 с D3(BJ); сравните несколько спиновых состояний')]
    elif n > 80:
        method = 'PBE'
        why = [tr('большая молекула: функционал GGA (PBE-D3(BJ)) дешевле гибрида; геометрию можно сначала уточнить в xtb')]
    elif task == 'Энергия':
        basis = 'def2-TZVP'
        why.append(tr('для энергии — трёхэкспонентный базис на геометрии, оптимизированной в def2-SVP'))
        if n <= 6 and _fits('cc-pVTZ', molecule):
            method, basis, disp = 'MP2', 'cc-pVTZ', ''
            why = [tr('несколько атомов: точнее посчитать энергию методом MP2 в базисе cc-pVTZ')]
    if charge < 0 and task not in TDDFT_TASKS:
        basis = {'def2-SVP': 'def2-SVPD', 'def2-TZVP': 'def2-TZVPD', 'cc-pVTZ': 'aug-cc-pVTZ'}.get(basis, basis)
        why.append(tr('анион: нужны диффузные функции'))
    if kind == 'gaussian' and basis in ('def2-SVPD', 'def2-TZVPD') and _fits('6-31+G*', molecule):
        basis = '6-31+G*'  # Gaussian has no def2-…D: the diffuse Pople basis
    method, basis = _available(kind, method, basis)
    if not _fits(basis, molecule):
        basis = 'def2-SVP'
    relativistic = ''
    symbols = {v: k for k, v in Z.items()}
    if f_block:  # def2 has no ECP for Ce–Lu and after Rn — DKH2 with SARC in ORCA
        names = ', '.join(symbols[z] for z in f_block)
        if kind == 'orca':
            relativistic = 'DKH'
            if tr('анион: нужны диффузные функции') in why:  # no diffuse DKH-def2: the note of the anion would mislead
                why = [w for w in why if w != tr('анион: нужны диффузные функции')]
                why.append(tr('диффузных версий DKH-def2 нет — диффузные функции здесь не добавить'))
            # the triple-zeta of an energy or NMR (def2-TZVP did not fit the lanthanide above and fell to def2-SVP)
            basis = 'def2-TZVP' if task in ('Энергия', NMR_TASK) else 'def2-SVP'
            why.append(tr(f'{names}: в def2 нет псевдопотенциала — гамильтониан DKH2, на {names} всеэлектронный '
                          f'SARC-DKH-TZVP, на остальных атомах {basis} в версии DKH; f-оболочка открыта — сравните '
                          'мультиплетности'))
        else:
            why.append(tr(f'{names}: здесь нет базиса — для лантаноидов и актиноидов выберите ORCA (DKH2 и SARC)'))
    elif ecp and basis.startswith('def2'):
        names = ', '.join(symbols[z] for z in ecp)
        why.append(tr(f'{names}: в def2 — псевдопотенциал на внутренних электронах (скалярный релятивизм уже учтён), '
                      'гамильтониан не нужен'))
    if multiplicity > 1:
        why.append(tr('открытая оболочка: неограниченный расчёт, проверьте ⟨S²⟩'))
    if task == TS_TASK:
        why.append(tr('переходное состояние: начните со структуры, близкой к нему (скан или NEB), и проверьте, что '
                      'мнимая частота одна и её колебание ведёт от реагентов к продуктам'))
    elif task == FREQ_TASK:
        why.append(tr('частоты — тем же методом и базисом, что оптимизация, и на её геометрии: иначе это не минимум'))
    elif 'Opt' in TASKS.get(task, ''):  # was «'Opt' in task» — never true for the Russian names
        why.append(tr('после оптимизации — частоты, чтобы убедиться в минимуме'))
    return Advice(method, basis, disp, '; '.join(why) + '.', relativistic)


# the settings that come with a task when it is chosen (with its method, recommend) — the other fields of
# Calculation keep their values. Reasons: before frequencies the optimization is converged tightly (loose geometries
# give spurious low or imaginary modes); NMR shieldings want a finer DFT grid; the TD-DFT settings return to the
# program's own (TDA in ORCA, full TD-DFT in Gaussian), 10 states, the first root, singlets.
TASK_BASE = {'scf': 'tight', 'grid': '', 'opt_conv': 'normal', 'calc_hessian': False, 'num_freq': False,
             'tddft_mode': '', 'triplets': False, 'root': 1, 'states': 10}
TASK_SETTINGS = {
    'Оптимизация + частоты': {'opt_conv': 'tight'},
    TS_TASK: {'opt_conv': 'tight'},
    'ЯМР (экранирование)': {'grid': 'fine'},
}


def task_settings(task):
    """{field of Calculation: value} for the task (TASK_BASE with its own changes)."""
    return {**TASK_BASE, **TASK_SETTINGS.get(task, {})}


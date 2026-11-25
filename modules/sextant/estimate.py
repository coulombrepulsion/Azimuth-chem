"""A rough estimate of the time of a calculation, shown in Sextant.

§1 THEORY
    The cost of a calculation grows as a power of the number of basis functions N: HF and DFT with density fitting
    ~ N³, MP2 ~ N⁴ (RI), CCSD ~ N⁶, CCSD(T) ~ N⁷; xtb ~ (atoms)². A geometry optimization repeats an energy and a
    gradient for a number of steps that grows with the size of the molecule; frequencies cost several gradients per
    atom (analytic Hessian), TD-DFT and NMR a few energies. The processes share the work with an efficiency < 1.
§2 ALGORITHM
    N = Σ over atoms of the functions of the basis on that atom (FUNCTIONS: H / He, the 2nd period, the 3rd one, heavier
    — for STO-3G, 6-31G*, def2-SVP, def2-TZVP(P), cc-pVDZ, cc-pVTZ, aug- adds ~60 %; an unknown name by its zeta);
    t₁ = C·N^p (C, p of the method family; DFT and HF N^2.3, calibrated on 29 real ORCA runs and on
    benzene, 114 functions in def2-SVP: B3LYP energy ~15 s on one core); divided by cores^0.9; task: optimization
    (5 + 0.6·atoms, ≤ 60) gradients of 1.5·t₁, analytic frequencies 2·atoms·t₁, numerical 6·atoms gradients, TD-DFT
    ×3, NMR ×2, NEB ×8 optimizations; with several processes ORCA pays STEP_S for each energy or gradient and
    PARALLEL_START_S once (mpirun of its modules). + the start of the program (START_S) and
    EVALUATION_S per energy of HF, DFT and the others (measured on ORCA 6.0.1 for water; they decide a small molecule).
    The answer is a range t/3 … 3t, rounded to a readable time — an order of magnitude, nothing more.
§4 SPECIFICATION
    basis_functions(molecule, basis) -> int; seconds(molecule, calc, program) -> float; text(seconds) -> 'от … до …'.
§6 NOTES
    The constants are rough (a laptop of 2024); a cluster node is faster, a large memory demand slower.
§7 TESTS
    tests/sextant/test_estimate.py.
"""

from azimuth.core import TASKS, Z
from azimuth.i18n import tr

# functions per atom: (H–He, Li–Ne, Na–Ar, K and heavier)
FUNCTIONS = {
    'sto-3g': (1, 5, 9, 18),
    '3-21g': (2, 9, 13, 23),
    '6-31g': (2, 9, 13, 23),
    '6-31g*': (2, 15, 19, 29),
    '6-31g(d)': (2, 15, 19, 29),
    '6-31g**': (5, 15, 19, 29),
    '6-31g(d,p)': (5, 15, 19, 29),
    '6-311g**': (6, 18, 22, 32),
    'def2-svp': (5, 14, 18, 30),
    'def2-svpd': (5, 18, 22, 34),
    'def2-tzvp': (6, 31, 37, 50),
    'def2-tzvpp': (14, 31, 37, 50),
    'def2-qzvp': (30, 57, 65, 80),
    'cc-pvdz': (5, 14, 18, 30),
    'cc-pvtz': (14, 30, 34, 50),
    'cc-pvqz': (30, 55, 59, 80),
}
# (C, p): t₁ = C·N^p seconds on one core
METHODS = {
    'hf': (1.2e-4, 2.3),  # RIJCOSX — N^2.3, HF a little cheaper than hybrid DFT
    'dft': (2.0e-4, 2.3),
    'mp2': (1.2e-7, 4.0),
    'ccsd': (1.0e-10, 6.0),
    'ccsd(t)': (1.4e-11, 7.0),
}


def _row(symbol):
    z = Z.get(symbol, 0)
    return 0 if z <= 2 else 1 if z <= 10 else 2 if z <= 18 else 3


def basis_functions(molecule, basis):
    name = (basis or '').strip().lower()
    aug = name.startswith('aug-') or name.startswith('ma-')
    key = name[4:] if name.startswith('aug-') else name[3:] if name.startswith('ma-') else name
    if key not in FUNCTIONS:
        zeta = 'q' if 'qz' in key else 't' if 'tz' in key or '311' in key else 'd'
        key = {'q': 'def2-qzvp', 't': 'def2-tzvp', 'd': 'def2-svp'}[zeta]
    per = FUNCTIONS[key]
    n = sum(per[_row(a.symbol)] for a in molecule.atoms if a.symbol != 'X')
    return round(n * 1.6) if aug else n


def _family(method):
    m = (method or '').strip().lower()
    if 'ccsd(t)' in m:
        return 'ccsd(t)'
    if 'ccsd' in m or m.startswith('qcisd'):
        return 'ccsd'
    if 'mp2' in m or m.startswith('dlpno'):
        return 'mp2'
    if m in ('hf', 'rhf', 'uhf', 'rohf'):
        return 'hf'
    return 'dft'


# a small molecule costs the start of the program and a fixed part of every energy (integrals, grid) —
# measured with ORCA 6.0.1 on a Mac (M-series, one core) on water B3LYP/def2-SVP: energy 2 s, optimization 6 s,
# + frequencies 10 s, TD-DFT 2 s, NMR 2 s (tools/check_programs.py).
# Calibrated on 29 real ORCA runs (water to 84 atoms, 24 to 1354 functions, 7 and 40 processes) and the one-core
# points above. What they showed: with several processes ORCA starts every module through mpirun — a water energy on
# 7 cores takes 10–14 s, not 2 s (PARALLEL_START_S, STEP_S per energy or gradient); a gradient costs 1.5 energies; DFT
# with RIJCOSX grows as N^2.3, not N³ (the 40-process runs of 1000+ functions were overestimated tenfold); the
# processes share the work as cores^0.9. The middle of the estimate is within a factor of 2 of most runs, 3.6 at
# worst (an optimization ended after one cycle, or took 40): the number of cycles is not known in advance.
START_S = {'orca': 1.5, 'gaussian': 2.0, 'psi4': 2.0, 'xtb': 0.5}
PARALLEL_START_S = {'orca': 6.0}  # the first mpirun and the modules of the start, with several processes
STEP_S = {'orca': 5.0}  # each energy or gradient with several processes (mpirun of its modules); one process: STEP_1
STEP_1 = 0.05
EVALUATION_S = 0.2
GRADIENT = 1.5  # the cost of an energy with its gradient, in energies
HESSIAN = 2.0  # analytic frequencies: energies per atom
SHARE = 0.9  # time / cores^SHARE


def seconds(molecule, calc, program='orca'):
    atoms = sum(1 for a in molecule.atoms if a.symbol != 'X')
    if atoms == 0:
        return 0.0
    cores = max(1, calc.cores)
    parallel = cores > 1
    if program == 'xtb':
        energy = (0.02 + 0.002 * atoms ** 2) / cores ** SHARE
        step = 0.0
    else:
        c, p = METHODS[_family(calc.method)]
        energy = (EVALUATION_S + c * basis_functions(molecule, calc.basis) ** p) / cores ** SHARE
        step = STEP_S.get(program, 0.3) if parallel else STEP_1
    single = step + energy
    gradient = step + GRADIENT * energy
    keys = TASKS.get(calc.task, '')
    total = single
    steps = min(60.0, 5 + 0.6 * atoms)
    if 'Opt' in keys or 'NEB' in keys:
        total = steps * gradient
    if 'NEB' in keys:
        total *= 8
    if 'NumFreq' in keys:  # two displacements of every coordinate — 6·atoms gradients
        total += step + 6 * atoms * GRADIENT * energy
    elif 'Freq' in keys:
        total += step + HESSIAN * atoms * energy
    if calc.task.startswith('Спектр UV-Vis'):
        total = step + 3 * energy
    if 'TD-DFT' in calc.task and 'Opt' in keys:  # an excited-state optimization — TD-DFT gradients every step
        total = steps * (step + 4 * energy)
    if 'NMR' in keys:
        total = step + 2 * energy
    if calc.task == 'Скан ППЭ с релаксацией':  # a short constrained optimization at every point
        total = calc.scan_steps * 0.5 * steps * gradient
    if calc.task.startswith('Функции Фукуи'):  # three single points (the ions open-shell: a slower SCF)
        total = 3 * step + 3.5 * energy
    start = START_S.get(program, 1.5) + (PARALLEL_START_S.get(program, 0.0) if parallel else 0.0)
    return start + total


def _readable(t):
    if t < 60:
        return tr(f'{max(1, round(t))} с')
    if t < 3600:
        return tr(f'{round(t / 60)} мин')
    if t < 86400:
        h = t / 3600
        return tr(f'{h:.1f} ч').replace('.', ',') if h < 10 else tr(f'{round(h)} ч')
    return tr(f'{round(t / 86400)} сут')


def text(t):
    """'от 5 с до 45 с'-like range of an order of magnitude around t."""
    if t <= 0:
        return ''
    low, high = _readable(t / 3), _readable(t * 3)
    return tr('меньше минуты') if t * 3 < 60 else tr(f'от {low} до {high}')

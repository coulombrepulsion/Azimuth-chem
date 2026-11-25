"""Input files of Gaussian, Psi4 and xtb for the Sextant settings (ORCA: azimuth.core.orca_input).

§1 THEORY
    The same calculation (method, basis, task, charge, multiplicity, processes, memory, implicit solvent,
    empirical dispersion, optimization constraints) is written in the language of each program.
    Solvent: a continuum around the molecule — CPCM in ORCA and Gaussian, the analytical linearized
    Poisson–Boltzmann model ALPB in xtb, CPCM of PCMSolver in Psi4; every program has its own list of
    solvent names (azimuth.core.SOLVENTS). Dispersion: Grimme's D3 with Becke–Johnson damping or D4,
    added to a DFT energy (GFN2-xTB contains D4 itself). TD-DFT gives the excitation energies and the
    oscillator strengths of the UV-Vis spectrum; NMR — the magnetic shielding tensors (GIAO).
§2 ALGORITHM
    Gaussian (.gjf): %nprocshared, %mem = processes × memory per process (MB), the route
    «#P method/basis task [EmpiricalDispersion=GD3BJ] [SCRF=(CPCM,Solvent=…)] SCF=Tight», a title,
    «charge multiplicity», the atoms, a blank line; an optimization with constraints is
    «Opt=ModRedundant» (Opt+Freq: «Opt=ModRedundant Freq») with the lines «X i F» (atom), «B i j F»,
    «A i j k F», «D i j k l F» (1-based) after the geometry. Basis names: def2SVP, def2TZVP, STO-3G.
    TD-DFT: «TD(NStates=n)», NMR: «NMR». Gaussian 16 has no D4: refused. «Дополнительные
    настройки»: SCF NormalSCF/TightSCF/VeryTightSCF (Gaussian —/SCF=Tight/SCF=VeryTight, Psi4 convergence 6/8/10),
    a finer DFT grid (ORCA DefGrid3, Gaussian Integral=SuperFineGrid, Psi4 99/590 points), no RI (ORCA NoRI, Psi4
    scf_type pk), a transition state (ORCA OptTS + Calc_Hess, Gaussian Opt=(TS,CalcFC,NoEigenTest), Psi4 opt_type
    ts + full_hess_every 0), tight optimization, the cycle limit, the Hessian at the start, Hirshfeld and NBO
    populations (ORCA, Gaussian), orbitals into the output (ORCA Print[P_MOs], Gaussian Pop=Full GFInput, Psi4
    molden_write, xtb --molden), the number of TD-DFT states, temperature and pressure of the thermochemistry
    (ORCA %freq, Gaussian Temperature/Pressure, Psi4 t/p in Pa) and a line of the user's own keywords. The method and
    basis names of every program come from azimuth.core.METHOD_TABLE / BASIS_TABLE (PBE0 = PBE1PBE in Gaussian,
    6-31G* = 6-31G(d), def2-TZVP = def2TZVP …); a method or basis the program has not is refused.
    Psi4 (input.dat): «memory N mb», the molecule block «charge multiplicity / atoms», «set {basis,
    reference, scf_type df, e_convergence 8, d_convergence 8}» (reference rhf/uhf for HF, rks/uks for
    DFT, open-shell for multiplicity > 1), the method name with «-d3bj» / «-d4», calls energy() /
    optimize() / optimize() then frequency(); TD-DFT: «set tdscf_states n» and energy(); constraints:
    «set optking {frozen_cartesian "i xyz …" frozen_distance "i j …" frozen_bend … frozen_dihedral …}»;
    solvent: «set pcm true», «set pcm_scf_type total» and the pcm = {…} block (Medium CPCM, cavity GePol
    with UFF radii). Psi4 has no NMR shieldings, and no PCM gradients (an optimization in a solvent): refused.
    xtb: «xtb <имя>.xyz --gfn 2 --chrg q --uhf 2S [--opt | --ohess] [--alpb solvent] [--input xcontrol]
    -P n»; xcontrol: «$fix atoms: …» and «$constrain force constant=0.5 distance|angle|dihedral: …, auto».
    xtb has no TD-DFT or NMR, and ALPB no ethanol: refused.
§3 APPLICATIONS
    modules/sextant/runner.py (job files), modules/sextant/workspace.py (the preview).
§4 SPECIFICATION
    gaussian_input(molecule, calculation, constraints=()) -> str
    psi4_input(molecule, calculation, constraints=()) -> str
    xtb_arguments(calculation, constraints=()) -> list[str]; xcontrol(constraints) -> str
    validate_xtb(molecule, calculation); xtb_preview(molecule, calculation, constraints=()) -> str
    input_files(kind, molecule, calculation, constraints=()) -> {file name: text} (the files of a job)
    preview(kind, molecule, calculation, constraints=()) -> str
    All raise ValueError for settings the program cannot do (the message says what to choose).
§5 PROCEDURES - below.
§6 NOTES
    Sources (ASSUMPTION: from memory of the manuals, not checked against a running program):
    Gaussian 16 keywords EmpiricalDispersion, SCRF, TD, NMR, Opt=ModRedundant; Psi4 1.7 manual (DFT
    dispersion suffixes, tdscf_states, optking frozen_* options, PCMSolver input); xtb 6 documentation
    («Commandline Usage», «Implicit Solvation», «Detailed Input»).
§7 TESTS
    tests/sextant/test_inputs.py.
§8' ROBUSTNESS
    The common checks of Calculation.validate (the elements of the basis — def2 with its ECP up to Rn, STO-3G H–Ar —,
    the electronic state) run first.
"""

from azimuth.core import (
    BASIS_TABLE, CDA_TASK, WAVEFUNCTION, INTERACTION_TASK, EXCITED_OPT_TASK, FREQ_TASK, FUKUI_TASK, NEB_TASK, PROGRAM_COLUMN, SCAN_TASK, SOLVENTS, TASKS, TDDFT_TASK, TS_TASK, Z,
    calculation_title, file_base,
    orca_input, program_names,
    validate_constraints,
)
import re
from dataclasses import replace

from azimuth.i18n import tr

KINDS = ('orca', 'gaussian', 'psi4', 'xtb', 'crest', 'mopac', 'gamess', 'nwchem')  # GAMESS, NWChem
NAMES = {'orca': 'ORCA', 'gaussian': 'Gaussian', 'psi4': 'Psi4', 'xtb': 'xtb', 'crest': 'CREST', 'mopac': 'MOPAC',
         'gamess': 'GAMESS', 'nwchem': 'NWChem'}
# outside the beta (AGENTS.md §0): the programs whose inputs Sextant writes but no real run has checked — marked
# «не проверено» in the list of programs (docs/plans/MAIN_PATH.md)
UNVERIFIED = {
    'gaussian': 'Входные файлы Gaussian ни разу не запускались настоящей программой — проверьте вход перед расчётом.',
    'gamess': 'Входные файлы GAMESS ни разу не запускались настоящей программой — проверьте вход перед расчётом.',
}
UNVERIFIED_MARK = 'не проверено'
NMR_TASK = 'ЯМР (экранирование)'
GAUSSIAN_BASIS = {k: row[2] for k, row in BASIS_TABLE.items() if row[2]}  # azimuth.core.BASIS_TABLE
GAUSSIAN_TASK = {'Энергия': '', 'Оптимизация': 'Opt', 'Оптимизация + частоты': 'Opt Freq', FREQ_TASK: 'Freq',
                 TS_TASK: 'Opt Freq',
                 TDDFT_TASK: '{td}', NMR_TASK: 'NMR', EXCITED_OPT_TASK: '{td} Opt', SCAN_TASK: 'Opt'}  # 0.91.20 # {td}
                 # — see _gaussian_td
XTB_TASK = {'Энергия': [], 'Оптимизация': ['--opt'], 'Оптимизация + частоты': ['--ohess'], FREQ_TASK: ['--hess'],
            SCAN_TASK: ['--opt']}  # the relaxed scan of xtb ($scan of xcontrol; «Быстрый расчёт xtb» of Compass)
FORCE_CONSTANT = 0.5  # Eh/bohr², the example value of the xtb documentation
PSI4_MIN_MEMORY = 264  # MB for the whole calculation: Psi4 refuses less than 250 MiB (263 MB)
SOLVENT_COLUMN = {'orca': 1, 'gaussian': 2, 'xtb': 3, 'psi4': 4, 'crest': 3}  # CREST: the ALPB names of xtb


def solvent_name(kind, calculation):
    """The program's name of the solvent ('' for the gas phase); ValueError if the program has none."""
    if not calculation.solvent:
        return ''
    name = SOLVENTS[calculation.solvent][SOLVENT_COLUMN[kind]]
    if name is None:
        raise ValueError(
            tr(f'В {NAMES[kind]} нет растворителя «{tr(SOLVENTS[calculation.solvent][0])}» — выберите другой.')
        )
    return name


def _atoms(molecule, c=None, style=''):
    """The lines of the coordinates; an atom with an isotope (Calculation.isotopes) — «H(Iso=2)» for Gaussian,
    «H@2.014102» for Psi4 (their ways of an isotope; ORCA writes «M = …», azimuth.core.coordinate_lines)."""
    from azimuth.core import isotope_masses

    masses = isotope_masses(getattr(c, 'isotopes', ''), molecule) if style else {}
    lines = molecule.xyz().splitlines()[2:]
    for k, mass in masses.items():
        symbol, rest = lines[k].split(None, 1)
        label = f'{symbol}(Iso={round(mass)})' if style == 'gaussian' else f'{symbol}@{mass:.6f}'
        lines[k] = f'{label:<2} {rest}'
    return '\n'.join(lines)


def _constraints(molecule, calculation, constraints):
    return validate_constraints(constraints, len(molecule.atoms)) if 'Opt' in TASKS[calculation.task] else ()


def _no_neb(kind, calculation):
    if calculation.task == NEB_TASK:
        raise ValueError(tr(f'Путь реакции (NEB) здесь пишется только для ORCA, не для {NAMES[kind]}.'))
    if calculation.task == SCAN_TASK and kind not in ('orca', 'gaussian', 'xtb'):  # 0.91.20; xtb
        raise ValueError(tr(f'Скан ППЭ здесь пишется для ORCA, Gaussian и xtb, не для {NAMES[kind]}.'))
    if calculation.task == FUKUI_TASK:  # Multiwfn needs the orbitals of the three calculations (ORCA Molden)
        raise ValueError(tr('Функции Фукуи считаются с ORCA: нужны файлы орбиталей всех трёх расчётов.'))
    if calculation.task == CDA_TASK:  # the same — the orbitals of the complex and of the fragments
        raise ValueError(tr('CDA считается с ORCA: нужны файлы орбиталей комплекса и обоих фрагментов.'))
    if calculation.task == INTERACTION_TASK:  # the ghost atoms of the counterpoise correction
        raise ValueError(tr('Энергия взаимодействия с BSSE считается с ORCA: нужны атомы-призраки.'))


def _gaussian_td(c):
    """TD(NStates=n[,Root=k][,50-50]) or TDA(…) of Gaussian 16."""
    options = [f'NStates={c.states}']
    if c.task == EXCITED_OPT_TASK:
        options.append(f'Root={c.root}')
    if c.triplets:
        options.append('50-50')
    return ('TDA' if c.tddft_mode == 'tda' else 'TD') + '(' + ','.join(options) + ')'


def gaussian_input(molecule, calculation, constraints=()):
    c = calculation
    _no_neb('gaussian', c)
    c.validate(molecule)
    if c.dispersion == 'D4':
        raise ValueError(tr('Gaussian 16 не знает поправку D4 — выберите D3(BJ).'))
    if c.relativistic not in ('', 'DKH'):
        raise ValueError(tr(f'Gaussian 16 из скалярных релятивистских поправок знает DKH2, не {c.relativistic} — выберите DKH2 или ORCA.'))
    if c.relativistic and any(Z[a.symbol] > 36 for a in molecule.atoms):
        raise ValueError(tr('Встроенных всеэлектронных базисов для DKH2 у атомов тяжелее Kr в Gaussian нет: выберите '
                            'гамильтониан «Нет» (def2 с псевдопотенциалом) или ORCA (SARC).'))
    fixed = _constraints(molecule, c, constraints)
    scan = ''
    if c.task == SCAN_TASK:  # «S n step» — n steps from the value of the geometry (n + 1 points)
        from azimuth.core import scan_plan

        if c.scan2_index >= 0:
            raise ValueError(tr('Двумерный скан здесь пишется только для ORCA — выберите ORCA или «Нет» во второй '
                                'координате.'))
        kind, atoms, start, end, steps, fixed = scan_plan(molecule, c, fixed)
        step = (end - start) / (steps - 1)
        scan = f'{kind} {" ".join(str(i + 1) for i in atoms)} S {steps - 1} {step:.{4 if kind == "B" else 3}f}\n'
    task = GAUSSIAN_TASK[c.task].format(td=_gaussian_td(c))
    if c.num_freq and 'Freq' in task:
        task = task.replace('Freq', 'Freq=Numer')
    if 'Opt' in task:  # the options of Opt: TS, CalcFC, Tight, MaxCycles, ModRedundant
        options = (['TS', 'CalcFC', 'NoEigenTest'] if c.is_ts else ['CalcFC'] if c.calc_hessian else [])
        options += (['Tight'] if c.opt_conv == 'tight' else []) + ([f'MaxCycles={c.max_cycles}'] if c.max_cycles else [])
        options += ['ModRedundant'] if fixed or scan else []
        if options:
            task = task.replace('Opt', 'Opt=' + (options[0] if len(options) == 1 else '(' + ','.join(options) + ')'), 1)
    solvent = solvent_name('gaussian', c)
    method, basis = program_names('gaussian', c)
    general = _gaussian_gen(molecule, c)  # the own basis sets of elements
    if general:
        basis = 'Gen'
    if c.population == 'nbo':
        population = 'Pop=NBO'
    elif c.population == 'hirshfeld':
        population = 'Pop=Hirshfeld'
    else:
        population = 'Pop=Full GFInput' if c.orbitals else ''
    route = ' '.join(filter(None, (
        f'#P {method}/{basis}',
        task,
        {'D3BJ': 'EmpiricalDispersion=GD3BJ', 'D3ZERO': 'EmpiricalDispersion=GD3'}.get(c.dispersion, ''),
        f'SCRF=({"SMD" if c.solvent_model == "smd" else "CPCM"},Solvent={solvent})' if solvent else '',
        'Stable=Opt' if c.stability and c.task == 'Энергия' else '',
        _gaussian_group('SCF', [{'normal': '', 'tight': 'Tight', 'verytight': 'VeryTight'}[c.scf],
                                'XQC' if c.slow_conv else '']),  # a hard SCF — the quadratic fallback
        _gaussian_group('Integral', ['DKH2' if c.relativistic == 'DKH' else '',
                                     'SuperFineGrid' if c.grid == 'fine' and c.method not in WAVEFUNCTION else '']),
        population,
        f'Temperature={c.temperature:g} Pressure={c.pressure:g}' if 'Freq' in task and c.thermo_changed() else '',
        ' '.join(c.extra.split()),
    )))
    text = (
        f'%nprocshared={c.cores}\n%mem={c.memory_mb * c.cores}MB\n{route}\n\n{calculation_title(molecule, c, "gaussian")}\n\n'
        f'{c.charge} {c.multiplicity}\n{_atoms(molecule, c, "gaussian")}\n\n'
    )
    if fixed or scan:
        letter = {'C': 'X', 'B': 'B', 'A': 'A', 'D': 'D'}
        text += ''.join(f'{letter[k]} {" ".join(str(i + 1) for i in a)} F\n' for k, a in fixed) + scan + '\n'
    return text + general  # the basis set input after the modifications of the coordinates (Gaussian 16 input order)


def _gaussian_gen(molecule, c):
    """The input of «Gen» — the elements by their basis sets, «C H O 0 / 6-31G(d) / ****» (the names of the
    built-in basis sets are allowed there), or '' without own basis sets of the elements of the molecule. Not with
    atoms heavier than Kr: «Gen» does not bring the ECP of def2 that the keyword Def2TZVP brings (it would need GenECP
    and the potentials written out)."""
    from azimuth.core import element_bases

    present = sorted({a.symbol for a in molecule.atoms}, key=Z.get)
    own = {s: k for s, k in element_bases(c.element_basis).items() if s in present}
    if not own:
        return ''
    if any(Z[s] > 36 for s in present):
        raise ValueError(tr('Базисы по элементам с атомами тяжелее Kr Gaussian здесь не пишет (Gen без псевдопотенциалов '
                            'def2) — выберите один базис на всю молекулу или ORCA.'))
    groups = {}
    for symbol in present:
        key = own.get(symbol, c.basis)
        name = BASIS_TABLE[key][PROGRAM_COLUMN['gaussian']]
        if name is None:
            raise ValueError(tr(f'В Gaussian нет базиса {key} — выберите другой.'))
        groups.setdefault(name, []).append(symbol)
    return ''.join(f'{" ".join(symbols)} 0\n{name}\n****\n' for name, symbols in groups.items()) + '\n'


def _psi4_assign(molecule, c):
    """[(symbol, Psi4 name)] of the own basis sets of the elements of the molecule."""
    from azimuth.core import element_bases

    present = {a.symbol for a in molecule.atoms}
    found = []
    for symbol, key in sorted(element_bases(c.element_basis).items(), key=lambda p: Z[p[0]]):
        if symbol in present:
            name = BASIS_TABLE[key][PROGRAM_COLUMN['psi4']]
            if name is None:
                raise ValueError(tr(f'В Psi4 нет базиса {key} — выберите другой.'))
            found.append((symbol, name))
    return found


def _gaussian_group(name, options):
    """«SCF=Tight», «SCF=(Tight,XQC)» or '' (several options of one keyword in brackets)."""
    options = [o for o in options if o]
    if not options:
        return ''
    return f'{name}={options[0]}' if len(options) == 1 else f'{name}=(' + ','.join(options) + ')'


def psi4_input(molecule, calculation, constraints=()):
    c = calculation
    _no_neb('psi4', c)
    c.validate(molecule)
    if c.relativistic:
        raise ValueError(tr('Релятивистские поправки здесь пишутся для ORCA и Gaussian, не для Psi4.'))
    if c.task == EXCITED_OPT_TASK:
        raise ValueError(tr('Оптимизацию возбуждённого состояния здесь пишут ORCA и Gaussian, не Psi4.'))
    if c.task == NMR_TASK:
        raise ValueError(tr('Psi4 не считает экранирование ЯМР — выберите ORCA или Gaussian.'))
    if c.memory_mb * c.cores < PSI4_MIN_MEMORY:
        # Psi4 1.11: «set_memory(): Requested 1.91e+02 MiB (2e+02 MB); minimum 250 MiB (263 MB)» — it stops before
        # the calculation (benzene with 100 MB per process on 2 processes, 2026-11-22)
        raise ValueError(tr('Psi4 не запускается с памятью меньше {} МБ на весь расчёт (сейчас {} МБ) — увеличьте '
                            '«Память / процесс».').format(PSI4_MIN_MEMORY, c.memory_mb * c.cores))
    solvent = solvent_name('psi4', c)
    if solvent and 'Opt' in TASKS[c.task]:
        raise ValueError(tr('В Psi4 нет градиентов с растворителем (PCM): оптимизацию в растворе сделайте в ORCA или Gaussian.'))
    if c.dispersion == 'D4':
        # the conda-forge build of Psi4 1.11 registers no «-d4» functional, dftd4-python and gcp-correction installed
        # or not (2026-11-22: «Method=b3lyp-d4 is not available»)
        raise ValueError(tr('Psi4 1.11 не знает поправку D4 — выберите D3(BJ).'))
    fixed = _constraints(molecule, c, constraints)
    name, basis = program_names('psi4', c)
    method = name + {'': '', 'D3BJ': '-d3bj', 'D3ZERO': '-d3zero'}[c.dispersion]
    open_shell = c.multiplicity > 1
    reference = ('uhf' if open_shell else 'rhf') if c.method in WAVEFUNCTION else ('uks' if open_shell else 'rks')
    if c.population != 'mulliken':
        raise ValueError(tr('В Psi4 здесь — только заряды по Малликену; Хиршфельд и NBO — в ORCA или Gaussian.'))
    conv = {'normal': 6, 'tight': 8, 'verytight': 10}[c.scf]
    own = _psi4_assign(molecule, c)  # the own basis sets of elements — a «basis {…}» block instead
    # conventional CCSD(T) of Psi4 (ccenergy) on the exact integrals of the SCF — checked on Psi4 1.11 (2026-11-22,
    # water cc-pVTZ, tests/data/psi4/water_ccsdt_fc_psi4-1.11.out)
    exact = c.no_ri or c.method == 'CCSD(T)'
    options = ([] if own else [f'basis {basis}']) + [f'reference {reference}', 'scf_type ' + ('pk' if exact else 'df'),
               f'e_convergence {conv}', f'd_convergence {conv}']
    if c.method in ('MP2', 'CCSD(T)'):
        # the 1s of C–Ne and the like not correlated, as ORCA and Gaussian do by default (Psi4 correlates all electrons
        # unless told): the energies of the three programs then compare
        options.append('freeze_core true')
    if c.task == TDDFT_TASK:
        options.append(f'tdscf_states {c.states}')
        # the residual of the states as ORCA and Gaussian converge them; the default of Psi4 1.11 follows d_convergence
        # (1e-8 → 1e-6), and the residual of formaldehyde stayed at 2.3e-6 for 60 iterations: no spectrum
        options.append('tdscf_r_convergence 1e-4')
        if c.tddft_mode:
            options.append('tdscf_tda ' + ('true' if c.tddft_mode == 'tda' else 'false'))
        if c.triplets:
            options.append('tdscf_triplets also')
    if c.slow_conv:  # damping of the SCF
        options.append('damping_percentage ' + ('20' if c.slow_conv == 'SlowConv' else '40'))
    if c.grid == 'fine' and c.method not in WAVEFUNCTION:
        options += ['dft_radial_points 99', 'dft_spherical_points 590']
    if 'Opt' in TASKS[c.task]:
        options += (['opt_type ts'] if c.is_ts else []) + (['full_hess_every 0'] if c.is_ts or c.calc_hessian else [])
        options += (['g_convergence gau_tight'] if c.opt_conv == 'tight' else []) + ([f'geom_maxiter {c.max_cycles}'] if c.max_cycles else [])
    if 'Freq' in TASKS[c.task] and c.thermo_changed():
        options += [f't {c.temperature:g}', f'p {c.pressure * 101325:g}']
    if c.orbitals:
        options.append('molden_write true')
    # no symmetry for an optimization: a geometry of SMILES is near C2v, found Cs, and optking of Psi4
    # 1.11 stopped «Point group changed! (c2v <-- cs)» when the steps made it C2v (2026-11-22, water)
    # TD-DFT too: with the symmetry Psi4 shares the states out among the irreps, and the Davidson solver of Psi4 1.11 did
    # not converge those of A″ of formaldehyde (Cs) in 60 iterations; without it the states are the lowest ones, as asked
    lowest = '\nsymmetry c1' if 'Opt' in TASKS[c.task] or c.task == TDDFT_TASK else ''
    text = (
        f'# {calculation_title(molecule, c, "psi4")}\nmemory {c.memory_mb * c.cores} mb\n\nmolecule {{\n{c.charge} {c.multiplicity}\n'
        f'{_atoms(molecule, c, "psi4")}{lowest}\n}}\n\nset {{\n' + ''.join(f'  {o}\n' for o in options) + '}\n'
    )
    if own:
        text += f'\nbasis {{\n  assign {basis}\n' + ''.join(f'  assign {s} {name}\n' for s, name in own) + '}\n'
    if fixed:
        names = {'C': 'frozen_cartesian', 'B': 'frozen_distance', 'A': 'frozen_bend', 'D': 'frozen_dihedral'}
        rows = []
        for kind, name in names.items():
            groups = [a for k, a in fixed if k == kind]
            if groups:
                if kind == 'C':
                    value = ' '.join(f'{a[0] + 1} xyz' for a in groups)
                else:
                    value = ' '.join(str(i + 1) for a in groups for i in a)
                rows.append(f'  {name} "{value}"\n')
        text += '\nset optking {\n' + ''.join(rows) + '}\n'
    if solvent:
        text += (
            '\nset pcm true\nset pcm_scf_type total\n\npcm = {\n  Units = Angstrom\n  Medium {\n    SolverType = CPCM\n'
            f'    Solvent = {solvent}\n  }}\n  Cavity {{\n    RadiiSet = UFF\n    Type = GePol\n    Scaling = False\n'
            '    Area = 0.3\n    Mode = Implicit\n  }\n}\n'
        )
    if c.extra.strip():  # the user's lines before the calls
        text += '\n' + c.extra.strip() + '\n'
    calls = {
        'Энергия': [f"energy('{method}')"],
        'Оптимизация': [f"optimize('{method}')"],
        'Оптимизация + частоты': [f"optimize('{method}')",
                                  f"frequency('{method}'" + (", dertype='energy')" if c.num_freq else ')')],
        TDDFT_TASK: [f"energy('td-{method}')"],  # Psi4 1.11: «tdscf_states» alone runs no TD-DFT («td-» does)
        FREQ_TASK: [f"frequency('{method}'" + (", dertype='energy')" if c.num_freq else ')')],
        TS_TASK: [f"optimize('{method}')", f"frequency('{method}'" + (", dertype='energy')" if c.num_freq else ')')],
    }[c.task]
    return text + '\n' + '\n'.join(calls) + '\n'


def validate_xtb(molecule, calculation):
    calculation.validate_settings()
    _no_neb('xtb', calculation)
    if not molecule.atoms:
        raise ValueError(tr('Добавьте атомы перед созданием входного файла.'))
    molecule.validate_state(calculation.charge, calculation.multiplicity)
    if any(Z[a.symbol] > 86 for a in molecule.atoms):
        raise ValueError(tr('GFN2-xTB определён для элементов H–Rn (Z ≤ 86).'))
    if calculation.task not in XTB_TASK:
        raise ValueError(tr('xtb не считает TD-DFT и ЯМР — выберите ORCA (или Gaussian, Psi4 для UV-Vis).'))
    if calculation.relativistic:
        raise ValueError(tr('В GFN2-xTB нет релятивистских поправок — выберите «Нет» или ORCA.'))
    if calculation.is_ts and 'Opt' in TASKS[calculation.task]:
        raise ValueError(tr('xtb не ищет переходные состояния — снимите «Переходное состояние» или выберите ORCA, Gaussian, Psi4.'))
    solvent_name('xtb', calculation)


def xcontrol(constraints, scan=None):
    """$fix / $constrain of xtb for 0-based constraints [(kind, atoms)], kinds C, B, A, D; atoms 1-based.
    Scan = (kind, atoms, start, end, points) — the relaxed scan: its coordinate is the first of $constrain
    (held at the start value) and «$scan 1: start,end,points» moves it (the xtb documentation, «Constraining
    potentials» and «$scan»: the number of the constraint, the first and the last value — Å or degrees — the points)."""
    if not constraints and scan is None:
        return ''
    fixed = [a[0] + 1 for k, a in constraints if k == 'C']
    names = {'B': 'distance', 'A': 'angle', 'D': 'dihedral'}
    rows = [f'   {names[k]}: {", ".join(str(i + 1) for i in a)}, auto\n' for k, a in constraints if k in names]
    digits = 4
    if scan is not None:
        kind, atoms, first, last, points = scan
        digits = 4 if kind == 'B' else 2
        rows.insert(0, f'   {names[kind]}: {", ".join(str(i + 1) for i in atoms)}, {first:.{digits}f}\n')
    text = ''
    if fixed:
        text += '$fix\n   atoms: ' + ','.join(map(str, fixed)) + '\n'
    if rows:
        text += f'$constrain\n   force constant={FORCE_CONSTANT}\n' + ''.join(rows)
    if scan is not None:
        text += f'$scan\n   1: {first:.{digits}f},{last:.{digits}f},{points}\n'
    return text + '$end\n'


def xtb_control(molecule, calculation, fixed):
    """The text of the file xcontrol of a job ('' — none): the constraints, and for a relaxed scan its
    coordinate (core.scan_plan: the start in the geometry, the end, the points) with the other constraints held."""
    if calculation.task == SCAN_TASK:
        from azimuth.core import scan_plan

        if calculation.scan2_index >= 0:  # xtb 6.7.1 scans two coordinates one after the other, not a grid
            raise ValueError(tr('xtb не делает двумерный скан сеткой (два скана идут по очереди) — выберите ORCA или '
                                '«Нет» во второй координате.'))
        kind, atoms, first, last, points, rest = scan_plan(molecule, calculation, fixed)
        return xcontrol(rest, (kind, atoms, first, last, points))
    return xcontrol(fixed) if fixed else ''


def xtb_arguments(calculation, constraints=(), xyz='molecule.xyz'):
    """Xyz — the name of the coordinate file (file_base(…, 'xtb') + '.xyz' in a job)."""
    c = calculation
    method = ['--gfnff'] if c.xtb_method == 'gfnff' else ['--gfn', '2']  # the force field of xtb
    args = [xyz] + method + ['--chrg', str(c.charge), '--uhf', str(c.multiplicity - 1)]
    task = list(XTB_TASK[c.task])
    optimizing = 'Opt' in TASKS[c.task]  # --hess (frequencies alone) takes no optimization options
    if optimizing and c.opt_conv == 'tight':  # --opt tight / --ohess tight
        task.append('tight')
    args += task
    if c.solvent:
        args += ['--alpb', solvent_name('xtb', c)]
    if (constraints and 'Opt' in TASKS[c.task]) or c.task == SCAN_TASK:  # a scan always has xcontrol
        args += ['--input', 'xcontrol']
    if c.max_cycles and optimizing:
        args += ['--cycles', str(c.max_cycles)]
    if c.orbitals:
        args.append('--molden')
    return args + c.extra.split() + ['-P', str(c.cores)]


def xtb_preview(molecule, calculation, constraints=()):
    """What will be run and written: the command line, <formula>_GFN2-xTB.xyz and xcontrol (Sextant's preview)."""
    validate_xtb(molecule, calculation)
    constraints = _constraints(molecule, calculation, constraints)
    xyz = file_base(molecule, calculation, 'xtb') + '.xyz'
    text = '# ' + tr('Команда в папке расчёта:') + '\nxtb ' + ' '.join(xtb_arguments(calculation, constraints, xyz))
    text += f'\n\n# {xyz}\n' + molecule.xyz()
    control = xtb_control(molecule, calculation, constraints)  # and the scan
    if control:
        text += '\n# xcontrol\n' + control
    return text


def crest_arguments(calculation, quick=False, xyz='molecule.xyz', ewin=None, mdlen=None):
    """CREST's iMTD-GC conformer search (its defaults: GFN2-xTB, CREGEN sorting). Ewin — the energy
    window in kcal/mol («--ewin <REAL>», CREST's default 6); mdlen — a factor of the metadynamics length CREST chooses
    («--mdlen x<REAL>»; CREST gives a molecule it finds rigid the shortest one, 5 ps). Flags as in the CREST
    documentation, crest-lab.github.io/crest-docs/page/documentation/keywords.html."""
    c = calculation
    args = [xyz, '--gfn2', '--chrg', str(c.charge), '--uhf', str(c.multiplicity - 1), '-T', str(c.cores)]
    if c.solvent:
        args += ['--alpb', solvent_name('crest', c)]
    if ewin is not None:
        if not 0 < ewin <= 100:
            raise ValueError(tr('Окно энергий — от 0 до 100 ккал/моль.'))
        args += ['--ewin', f'{ewin:g}']
    if mdlen is not None and abs(mdlen - 1.0) > 1e-9:
        if not 0.1 <= mdlen <= 10:
            raise ValueError(tr('Множитель длины метадинамики — от 0,1 до 10.'))
        args += ['--mdlen', f'x{mdlen:g}']
    return args + (['--quick'] if quick else [])


# MOPAC (openmopac.github.io/keywords). The dielectric constants of COSMO (EPS=) for the solvents of the program —
# values of the CRC Handbook of Chemistry and Physics at 20–25 °C, rounded (within 5 % of the table of ADF COSMO; for
# COSMO, which goes as 1/ε, the difference does not matter); MOPAC takes a number.
MOPAC_EPS = {'water': 78.4, 'methanol': 32.6, 'ethanol': 24.6, 'acetonitrile': 35.7, 'dmso': 46.7, 'acetone': 20.7,
             'chloroform': 4.81, 'dichloromethane': 8.93, 'thf': 7.58, 'toluene': 2.38, 'benzene': 2.27, 'hexane': 1.89}
MOPAC_SPIN = {1: '', 2: 'DOUBLET', 3: 'TRIPLET', 4: 'QUARTET', 5: 'QUINTET', 6: 'SEXTET'}
MOPAC_TASKS = ('Энергия', 'Оптимизация', 'Оптимизация + частоты', FREQ_TASK, TS_TASK)  # + two


# the tasks each program is offered in Sextant (the others are not in its list) and the settings shown under a
# task — with the programs whose inputs write them (gaussian_input, psi4_input, xtb_arguments, mopac_input, orca_input)
PROGRAM_TASKS = {
    'orca': tuple(TASKS),
    'gaussian': tuple(t for t in TASKS if t not in (NEB_TASK, FUKUI_TASK, CDA_TASK, INTERACTION_TASK)),  # no file of
    # orbitals for Fukui (nor for CDA)
    'psi4': ('Энергия', 'Оптимизация', 'Оптимизация + частоты', FREQ_TASK, TS_TASK, TDDFT_TASK),  # no scan
    'xtb': tuple(XTB_TASK),
    'mopac': MOPAC_TASKS,
    # what both write here
    'gamess': ('Энергия', 'Оптимизация', 'Оптимизация + частоты', FREQ_TASK, TS_TASK, TDDFT_TASK),
    'nwchem': ('Энергия', 'Оптимизация', 'Оптимизация + частоты', FREQ_TASK, TS_TASK, TDDFT_TASK, NMR_TASK),
    # CREST does one thing — its conformer search (iMTD-GC, GFN2-xTB), ending with optimized conformers; the molecule is
    # checked as for an optimization (input_files). Without this entry it was offered all the tasks of ORCA and the
    # chains built of them.
    'crest': ('Оптимизация',),
}
TASK_TITLES = {('crest', 'Оптимизация'): 'Поиск конформеров (iMTD-GC)'}  # (kind, task) -> what the list shows


def task_title(kind, task):
    """The Russian name of a task in the list of the program (the key of tr): its own name for CREST."""
    return TASK_TITLES.get((kind, task), task)
TASK_OPTIONS = {  # key: (when — 'opt' | 'freq' | 'td' | 'spectrum' (TD-DFT spectrum only) | 'root', programs)
    'ts': ('opt', ('orca', 'gaussian', 'psi4', 'mopac')),
    'opt_conv': ('opt', ('orca', 'gaussian', 'psi4', 'xtb', 'gamess')),
    'max_cycles': ('opt', ('orca', 'gaussian', 'psi4', 'xtb', 'gamess', 'nwchem')),
    'calc_hessian': ('opt', ('orca', 'gaussian', 'psi4', 'gamess')),
    'temperature': ('freq', ('orca', 'gaussian', 'psi4', 'mopac', 'gamess', 'nwchem')),
    'pressure': ('freq', ('orca', 'gaussian', 'psi4')),
    'num_freq': ('freq', ('orca', 'gaussian', 'psi4')),
    'raman': ('freq', ('orca',)),
    'couplings': ('nmr', ('orca',)),
    'states': ('td', ('orca', 'gaussian', 'psi4', 'gamess', 'nwchem')),
    'tddft_mode': ('td', ('orca', 'gaussian', 'psi4')),
    'triplets': ('spectrum', ('orca', 'gaussian', 'psi4', 'nwchem')),  # the excited-state optimization follows a singlet
    'root': ('root', ('orca', 'gaussian')),
    'stability': ('energy', ('orca', 'gaussian')),
    # the relaxed scan — which coordinate, to what value, in how many points
    'scan_index': ('scan', ('orca', 'gaussian', 'xtb')),  # xtb too
    'scan_end': ('scan', ('orca', 'gaussian', 'xtb')),  # xtb too
    'scan_steps': ('scan', ('orca', 'gaussian', 'xtb')),  # xtb too
    'scan2_index': ('scan', ('orca',)),  # the second coordinate of a two-dimensional scan
    'scan2_end': ('scan', ('orca',)),
    'scan2_steps': ('scan', ('orca',)),
    'nto': ('spectrum', ('orca',)),  # the natural transition orbitals of the states
    'guess': ('any', ('orca',)),  # MORead — the orbitals of an earlier calculation of ORCA
    # CDA — the atoms of fragment 1 (with «Из выделения» of Compass), its charge and multiplicity, the
    # multiplicity of fragment 2
    'cda_atoms': ('cda', ('orca',)),
    'cda_pick': ('cda', ('orca',)),
    'cda_charge': ('cda', ('orca',)),
    'cda_mult1': ('cda', ('orca',)),
    'cda_mult2': ('cda', ('orca',)),
}


def tasks_for(kind):
    """The tasks of the program kind, in the order of core.TASKS."""
    return PROGRAM_TASKS.get(kind, tuple(TASKS))


def task_options(kind, task):
    """The keys of TASK_OPTIONS shown under the task for the program, in their order."""
    if task not in TASKS:
        return ()
    when = {'energy', 'any'} if task == 'Энергия' else {'any'}
    if 'Opt' in TASKS[task]:
        when.add('opt')
    if 'Freq' in TASKS[task]:
        when.add('freq')
    if task in (TDDFT_TASK, EXCITED_OPT_TASK):
        when.add('td')
    if task == TDDFT_TASK:
        when.add('spectrum')
    if task == EXCITED_OPT_TASK:
        when.add('root')
    if task == SCAN_TASK:
        when.add('scan')
    if task == NMR_TASK:
        when.add('nmr')
    if task == CDA_TASK:
        when.add('cda')
    shown = tuple(key for key, (need, programs) in TASK_OPTIONS.items() if need in when and kind in programs)
    # the task is the transition state: the switch and the exact Hessian (computed for a TS anyway) are not choices
    # a scan is a series of minima — no switch of the transition state
    return tuple(k for k in shown if not (task == TS_TASK and k in ('ts', 'calc_hessian') or task == SCAN_TASK and k == 'ts'))


def mopac_input(molecule, calculation, constraints=()):
    """The .mop of MOPAC — keywords, two title lines, the Cartesian geometry with optimization flags (0 for the atoms
    frozen in Compass). «Энергия» 1SCF; «Оптимизация» PRECISE (MOPAC optimizes by default); «Оптимизация + частоты» two
    jobs in one file: the optimization, then «FORCE THERMO OLDGEO» — the frequencies at its geometry (MOPAC does not
    optimize before FORCE; OLDGEO checked on MOPAC 23.2.5, tests/data/mopac/h2o_pm7_opt_then_force_oldgeo: the
    frequencies of the two separate runs, 1394.92 / 2809.65 / 2856.03 cm⁻¹). AUX always — the .aux is what Spectrum
    reads."""
    from azimuth.core import methods_for

    c = calculation
    c.validate(molecule)
    if c.method not in methods_for('mopac'):
        raise ValueError(tr('Для MOPAC выберите полуэмпирический метод: PM7, PM6, PM6-D3H4, AM1, RM1 или MNDO.'))
    if c.task not in MOPAC_TASKS:
        raise ValueError(tr('MOPAC в Азимуте считает энергию, оптимизацию и оптимизацию с частотами — для этой задачи '
                            'выберите ORCA.'))
    if c.multiplicity not in MOPAC_SPIN:
        raise ValueError(tr('Мультиплетность для MOPAC — от 1 до 6.'))
    # the heavy elements of the methods (Stewart: PM6 2007 and PM7 2013 — H–Ba, La, Lu–Bi; AM1, RM1, MNDO here
    # up to Kr and iodine); ASSUMPTION: the sparkles of the lanthanides are not written by Azimuth
    heavy = {Z[a.symbol] for a in molecule.atoms if Z[a.symbol] > 36}
    allowed = (set(range(37, 58)) | set(range(71, 84))) if c.method.startswith(('PM6', 'PM7')) else {53}
    if heavy - allowed:
        symbols = {v: k for k, v in Z.items()}
        names = ', '.join(symbols[n] for n in sorted(heavy - allowed))
        raise ValueError(tr(f'{c.method} в MOPAC не параметризован для {names} — возьмите PM7 (H–Ba, La, Lu–Bi) или ORCA.'))
    if c.relativistic:
        raise ValueError(tr('В MOPAC нет релятивистских гамильтонианов — выберите «Нет» или ORCA.'))
    if c.solvent and c.solvent not in MOPAC_EPS:
        raise ValueError(tr('Для этого растворителя нет диэлектрической проницаемости — выберите другой.'))
    fixed = _constraints(molecule, c, constraints)
    if any(kind != 'C' for kind, _ in fixed):  # C — a frozen atom (core.CONSTRAINT_KINDS)
        raise ValueError(tr('В MOPAC здесь замораживаются только атомы (декартовы координаты), не расстояния и углы.'))
    frozen = {atoms[0] for _, atoms in fixed}
    common = [c.method]
    if c.charge:
        common.append(f'CHARGE={c.charge}')
    if c.multiplicity > 1:
        common += [MOPAC_SPIN[c.multiplicity], 'UHF']
    if c.solvent:
        common.append(f'EPS={MOPAC_EPS[c.solvent]:g}')
    first = list(common)
    thermo = (f'THERMO=({c.temperature:g},{c.temperature + 100:g},100)'  # MOPAC takes no pressure
              if abs(c.temperature - 298.15) > 1e-9 else 'THERMO')
    if c.task == 'Энергия':
        first.append('1SCF')
    elif c.task == FREQ_TASK:  # at the given geometry (MOPAC does not optimize before FORCE)
        first += ['FORCE', thermo]
    else:
        first.append('PRECISE')
        if c.is_ts:
            first.append('TS')
    first.append('AUX')
    title = calculation_title(molecule, c, 'mopac')[:78]
    flag = 0 if c.task in ('Энергия', FREQ_TASK) else 1
    rows = []
    for k, a in enumerate(molecule.atoms):
        f = 0 if k in frozen else flag
        x, y, z = a.position
        rows.append(f'{a.symbol:2s} {x:13.8f} {f} {y:13.8f} {f} {z:13.8f} {f}')
    text = ' '.join(first) + '\n' + title + '\n' + 'Azimuth\n' + '\n'.join(rows) + '\n'
    if c.task in ('Оптимизация + частоты', TS_TASK):
        # the form checked on MOPAC 23.2.5 (start, end, step): THERMO=(298,398,100) printed 298 and 398 K
        text += '\n' + ' '.join(common + ['FORCE', thermo, 'OLDGEO', 'AUX']) + '\n' + title + '\nAzimuth: frequencies\n'
    return text


def input_files(kind, molecule, calculation, constraints=(), neb=None):
    """neb = (end Molecule, images) for the NEB task of ORCA. The files are named after the
    calculation (core.file_base: its title or formula_method_basis[_solvent]); the main input is the first key."""
    base = file_base(molecule, calculation, kind)
    if kind == 'orca':
        end, images = neb if neb else (None, 8)
        files = {f'{base}.inp': orca_input(molecule, calculation, constraints, end, images)}
        if calculation.task == NEB_TASK:
            files['end.xyz'] = end.xyz()
        return files
    if kind == 'gaussian':
        return {f'{base}.gjf': gaussian_input(molecule, calculation, constraints)}
    if kind == 'psi4':
        return {f'{base}.dat': psi4_input(molecule, calculation, constraints)}
    if kind == 'crest':
        validate_xtb(molecule, replace(calculation, task='Оптимизация'))
        return {f'{base}.xyz': molecule.xyz()}
    if kind == 'mopac':
        return {f'{base}.mop': mopac_input(molecule, calculation, constraints)}
    if kind in ('gamess', 'nwchem'):
        from modules.sextant import inputs_more

        write = inputs_more.gamess_input if kind == 'gamess' else inputs_more.nwchem_input
        return {inputs_more.file_name(kind, molecule, calculation): write(molecule, calculation, constraints)}
    if kind == 'xtb':
        validate_xtb(molecule, calculation)
        fixed = _constraints(molecule, calculation, constraints)
        files = {f'{base}.xyz': molecule.xyz()}
        control = xtb_control(molecule, calculation, fixed)  # and the scan
        if control:
            files['xcontrol'] = control
        return files
    raise ValueError(kind)


def preview(kind, molecule, calculation, constraints=(), neb=None):
    if kind == 'xtb':
        return xtb_preview(molecule, calculation, constraints)
    if kind == 'crest':
        files = input_files(kind, molecule, calculation)
        xyz = next(iter(files))
        return ('# ' + tr('Команда в папке расчёта:') + '\ncrest ' + ' '.join(crest_arguments(calculation, xyz=xyz))
                + f'\n\n# {xyz}\n' + files[xyz])
    files = input_files(kind, molecule, calculation, constraints, neb)
    text = next(iter(files.values()))
    if 'end.xyz' in files:
        text += '\n# end.xyz\n' + files['end.xyz']
    return text


# an input file opened in Sextant — what of the settings can be read back from it ---------------------------
INPUT_SUFFIXES = {'.inp': 'orca', '.gjf': 'gaussian', '.com': 'gaussian', '.gjc': 'gaussian'}


def input_kind(path, text):
    """'orca' or 'gaussian' by the suffix, else by the text (a Gaussian route starts with #)."""
    from pathlib import Path

    kind = INPUT_SUFFIXES.get(Path(path).suffix.lower())
    if kind:
        return kind
    head = [l.strip() for l in text.splitlines() if l.strip() and not l.strip().startswith('%')]
    return 'gaussian' if head and head[0].startswith('#') else 'orca'


def read_settings(kind, text):
    """{'method', 'basis', 'task', 'dispersion', 'solvent'} found in the keywords of an ORCA («!» lines) or Gaussian
    (route «#») input — only what this program writes the same way; the rest is left as it is in Sextant."""
    from azimuth.core import BASIS_TABLE, METHOD_TABLE, PROGRAM_COLUMN, DISPERSIONS

    column = PROGRAM_COLUMN[kind]
    if kind == 'orca':
        words = ' '.join(l.strip()[1:] for l in text.splitlines() if l.strip().startswith('!')).split()
        blocks = text.lower()
    else:
        lines = text.replace('\r', '').split('\n')
        route, inside = [], False
        for line in lines:
            if line.strip().startswith('#'):
                inside = True
            if inside:
                if not line.strip():
                    break
                route.append(line.strip().lstrip('#').strip())
        words = []
        for token in ' '.join(route).split():
            words.extend(token.split('/') if '/' in token and '=' not in token.split('/')[0] else [token])
        blocks = ' '.join(route).lower()
    lower = [re.sub(r'^libxc\((.+)\)$', r'\1', w.lower()) for w in words]  # «LibXC(B3LYP)» is B3LYP
    found = {}
    for key, row in METHOD_TABLE.items():
        if row[column] and row[column].lower() in lower:
            found['method'] = key
            break
    for key, row in BASIS_TABLE.items():
        if row[column] and row[column].lower() in lower:
            found['basis'] = key
            break
    opt = any(w.startswith('opt') for w in lower)
    freq = any(w.startswith('freq') or w == 'numfreq' for w in lower)
    if kind == 'orca' and '%tddft' in blocks or kind == 'gaussian' and any(w.startswith(('td(', 'td=', 'tda')) or w == 'td'
                                                                       for w in lower):
        found['task'] = EXCITED_OPT_TASK if opt else TDDFT_TASK
    elif any(w == 'nmr' or w.startswith('nmr') for w in lower):
        found['task'] = NMR_TASK
    elif kind == 'orca' and re.search(r'%eprnmr.*?ssall', text.lower(), re.S):  # σ and J without «NMR»
        found['task'] = NMR_TASK
        found['couplings'] = True
    elif any('neb' in w for w in lower):
        found['task'] = NEB_TASK
    elif opt and (kind == 'orca' and re.search(r'^\s*scan\b', blocks, re.M)
                  or kind == 'gaussian' and re.search(r'^\s*[bad](?:\s+\d+){2,4}\s+s\s+\d+', text.lower(), re.M)):
        found['task'] = SCAN_TASK  # %geom Scan of ORCA, «S n step» of Gaussian
    elif opt and freq:
        found['task'] = TS_TASK if any(w.startswith('optts') or 'ts,' in w or '(ts' in w for w in lower) \
            else 'Оптимизация + частоты'
    elif freq:
        found['task'] = FREQ_TASK  # 0.91.14 (was read as «Энергия»)
    elif opt:
        found['task'] = 'Оптимизация'
    else:
        found['task'] = 'Энергия'
    if kind == 'orca':
        for key, word in DISPERSIONS.items():
            if word and word.lower() in lower:
                found['dispersion'] = key
    elif any('empiricaldispersion=gd3bj' in w for w in lower):
        found['dispersion'] = 'D3BJ'
    elif any(w == 'empiricaldispersion=gd3' for w in lower):
        found['dispersion'] = 'D3ZERO'
    return found


def set_input_files(kind, structures, calculation, state=None):
    """The input files of a set of structures with the same settings — ({file name: text}, [(name, why)]).
    structures: [(Molecule, name)]; state(molecule) -> (charge, multiplicity) for each structure (else those of
    calculation). Each file is named «<name>_<method>_<basis>[_solvent]» (core.auto_title without the formula); a name
    used twice gets _2, _3…; end.xyz of a path and xcontrol are not written (they belong to one structure)."""
    from azimuth.core import auto_title, safe_name

    files, failed, used = {}, [], set()
    for k, (molecule, name) in enumerate(structures, start=1):
        calc = calculation
        if state is not None:
            charge, multiplicity = state(molecule)
            calc = replace(calc, charge=charge, multiplicity=multiplicity)
        tail = auto_title(molecule, calc, kind).split('_', 1)
        title = safe_name(name or f'{k}') + ('_' + tail[1] if len(tail) == 2 else '')
        base, n = title, 2
        while base.lower() in used:
            base, n = f'{title}_{n}', n + 1
        used.add(base.lower())
        try:
            made = input_files(kind, molecule, replace(calc, title=base))
        except ValueError as exc:
            failed.append((name, str(exc)))
            continue
        main = next(iter(made))
        files[main] = made[main]
    return files, failed

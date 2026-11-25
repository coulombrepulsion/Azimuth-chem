"""Input files of GAMESS (US) and NWChem for the Sextant settings.
§1 PURPOSE
    Spectrum reads the outputs of GAMESS (US) / Firefly and NWChem; Sextant wrote no inputs for them. Here the
    same calculation as for ORCA and Gaussian is written in their languages — what both programs do in the same way,
    and nothing else: what one of them has not, or what is not checked here, is refused with what to choose instead.
§2 RULES
    Common: the method and the basis by azimuth.core.GAMESS_* / NWCHEM_* (program_names); charge and multiplicity;
    memory = processes × memory per process; the coordinates in ångström, the molecule as it is (no symmetry, no
    reorientation: the atoms of the result keep the numbers of the model). Refused: a solvent, constraints of an
    optimization, D4, relativistic corrections, an own basis of elements, the tasks of NEB, a scan, the optimization of
    an excited state, Fukui and CDA queues; GAMESS also NMR.
    GAMESS (<name>.inp; columns: a $ group starts in column 2, as in the inputs echoed by GAMESS 2017):
        $CONTRL SCFTYP=RHF|UHF RUNTYP=ENERGY|OPTIMIZE|HESSIAN|SADPOINT ICHARG MULT [DFTTYP] [MPLEVL=2]
                [TDDFT=EXCITE] [ISPHER=1 for cc-pVnZ and pcseg] COORD=CART UNITS=ANGS NOSYM=1 MAXIT $END
        $SYSTEM MWORDS (1 MW = 8 MB) $END, $BASIS …, $SCF DIRSCF=.TRUE. $END,
        $STATPT OPTTOL NSTEP [HSSEND=.TRUE. — the Hessian at the end of an optimization: «Оптимизация + частоты»;
                HESS=CALC of a transition state] $END, [$DFT IDCVER=4 — D3(BJ)], [$TDDFT NSTATE], [$FORCE TEMP]
        $DATA / title / C1 / «symbol Z x y z» / $END. SCFTYP=UHF for multiplicity > 1.
    NWChem (<name>.nw): start, title, memory total N mb, charge, «geometry units angstroms noautosym nocenter
        noautoz» … end, «basis [spherical]» «* library name» end (+ «ecp * library def2-ecp end» for def2 and Rb–Rn),
        dft { xc …, mult, [disp vdw 4], [grid fine], iterations, convergence energy } or scf { rhf|uhf, nopen } for
        HF and MP2 (+ mp2 { freeze atomic } — the frozen core of ORCA and Psi4), driver { maxiter } of an
        optimization, tddft { nroots, [notriplet] },
        property { shielding } for NMR; task dft|scf|mp2|tddft
        energy|optimize|freq|saddle|property.
§3 INTERFACE gamess_input(molecule, calculation, constraints=()) -> str; nwchem_input(…) -> str;
    file_name(kind, molecule, calculation) -> str. ValueError with the reason for what the program cannot do here.
§4 TESTS tests/sextant/test_inputs_more.py — against the inputs of cclib (GAMESS 2017, NWChem 7.0) whose outputs
    are in tests/data, and the rules above.
§5 NOT CHECKED ASSUMPTION: no GAMESS input written here has been run by GAMESS in this project; its keywords are
    those of the manual and of the cclib inputs (§2). NWChem 7.3.0 ran every task of its list on macOS, 2026-11-22
    (docs/plans/TASK_MATRIX.md)."""

from azimuth.core import (EXCITED_OPT_TASK, FREQ_TASK, NEB_TASK, SCAN_TASK, TASKS, TDDFT_TASK, TS_TASK, Z,
                          calculation_title, file_base, program_names)
from azimuth.i18n import tr

NMR_TASK = 'ЯМР (экранирование)'
TASKS_HERE = ('Энергия', 'Оптимизация', 'Оптимизация + частоты', FREQ_TASK, TS_TASK, TDDFT_TASK, NMR_TASK)
EXTENSION = {'gamess': '.inp', 'nwchem': '.nw'}
NAMES = {'gamess': 'GAMESS', 'nwchem': 'NWChem'}


def file_name(kind, molecule, calculation):
    return file_base(molecule, calculation, kind) + EXTENSION[kind]


def _common(kind, molecule, c, constraints):
    """§2: what neither program is given here — refused with the reason."""
    name = NAMES[kind]
    c.validate(molecule)
    if c.task in (NEB_TASK, SCAN_TASK, EXCITED_OPT_TASK) or c.task not in TASKS_HERE:
        raise ValueError(tr(f'Эту задачу для {name} Секстант не пишет — выберите ORCA или Gaussian.'))
    if c.solvent:
        raise ValueError(tr(f'Секстант пока не пишет растворитель для {name} — уберите его или выберите ORCA или Gaussian.'))
    if constraints and 'Opt' in TASKS[c.task]:
        raise ValueError(tr(f'Ограничения оптимизации для {name} Секстант пока не пишет — снимите их или выберите ORCA.'))
    if c.dispersion in ('D4', 'D3ZERO'):
        raise ValueError(tr(f'В {name} здесь из дисперсии — только D3(BJ).'))
    if c.relativistic:
        raise ValueError(tr(f'Релятивистские поправки здесь пишутся для ORCA и Gaussian, не для {name}.'))
    if getattr(c, 'element_basis', ''):
        raise ValueError(tr(f'Свои базисы элементов для {name} Секстант не пишет — уберите их.'))
    if c.dispersion and c.method in ('HF', 'MP2'):
        raise ValueError(tr('Дисперсионная поправка D3 добавляется к DFT, не к HF или MP2.'))
    return program_names(kind, c)


def _covered(molecule, ranges, basis, name):
    bad = sorted({a.symbol for a in molecule.atoms if not any(lo <= Z[a.symbol] <= hi for lo, hi in ranges)},
                 key=lambda s: Z[s])
    if bad:
        raise ValueError(tr(f'В {name} базис {basis} не задан для: ') + ', '.join(bad) + '.')


# -- GAMESS ---------------------------------------------------------------------------------------------------------
def gamess_input(molecule, calculation, constraints=()):
    c = calculation
    (dft, mplevel), (keywords, spherical, ranges) = _common('gamess', molecule, c, constraints)
    if c.task == NMR_TASK:
        raise ValueError(tr('ЯМР для GAMESS Секстант не пишет — выберите ORCA или Gaussian.'))
    if c.task == TDDFT_TASK and not dft:
        raise ValueError(tr('TD-DFT в GAMESS — для функционала DFT, не для HF или MP2.'))
    _covered(molecule, ranges, c.basis, 'GAMESS')
    runtyp = {'Энергия': 'ENERGY', 'Оптимизация': 'OPTIMIZE', 'Оптимизация + частоты': 'OPTIMIZE',
              FREQ_TASK: 'HESSIAN', TS_TASK: 'SADPOINT', TDDFT_TASK: 'ENERGY'}[c.task]
    contrl = [f'SCFTYP={"UHF" if c.multiplicity > 1 else "RHF"}', f'RUNTYP={runtyp}', f'ICHARG={c.charge}',
              f'MULT={c.multiplicity}']
    if dft:
        contrl.append(f'DFTTYP={dft}')
    if mplevel:
        contrl.append(f'MPLEVL={mplevel}')
    if c.task == TDDFT_TASK:
        contrl.append('TDDFT=EXCITE')
    if spherical:
        contrl.append('ISPHER=1')  # the manual: cc-pVnZ and PCseg «refuse to run without ISPHER being set»
    contrl += ['COORD=CART', 'UNITS=ANGS', 'NOSYM=1', f'MAXIT={200 if c.slow_conv else 100}']
    lines = [' $CONTRL ' + ' '.join(contrl[:4]), '        ' + ' '.join(contrl[4:]) + ' $END',
             f' $SYSTEM MWORDS={max(1, c.memory_mb // 8)} $END',
             f' $BASIS  {keywords} $END',
             ' $SCF    DIRSCF=.TRUE. $END']
    if 'Opt' in TASKS[c.task]:
        statpt = [f'OPTTOL={"1.0E-5" if c.opt_conv == "tight" else "1.0E-4"}', f'NSTEP={c.max_cycles or 100}']
        if c.task in ('Оптимизация + частоты', TS_TASK):
            statpt.append('HSSEND=.TRUE.')
        if c.task == TS_TASK or c.calc_hessian:
            statpt.append('HESS=CALC')
        lines.append(' $STATPT ' + ' '.join(statpt) + ' $END')
    if c.dispersion == 'D3BJ':
        lines.append(' $DFT    IDCVER=4 $END')
    if c.task == TDDFT_TASK:
        lines.append(f' $TDDFT  NSTATE={c.states} $END')
    if 'Freq' in TASKS[c.task] and c.thermo_changed():
        lines.append(f' $FORCE  TEMP(1)={c.temperature:g} $END')
    if c.extra.strip():
        lines += [' ' + line.strip() for line in c.extra.strip().splitlines()]
    lines += [' $DATA', calculation_title(molecule, c, 'gamess')[:80], 'C1']
    for a in molecule.atoms:
        x, y, z = a.position
        lines.append(f' {a.symbol:<2} {Z[a.symbol]:>5.1f} {x:16.10f} {y:16.10f} {z:16.10f}')
    lines.append(' $END')
    return '\n'.join(lines) + '\n'


# -- NWChem ---------------------------------------------------------------------------------------------------------
def _nwchem_base(molecule, c):
    return file_base(molecule, c, 'nwchem').replace(' ', '_') or 'input'


def nwchem_input(molecule, calculation, constraints=()):
    c = calculation
    xc, (library, spherical) = _common('nwchem', molecule, c, constraints)
    title = calculation_title(molecule, c, 'nwchem').replace('"', "'")
    lines = [f'start {_nwchem_base(molecule, c)}', f'title "{title}"', '',
             f'memory total {c.memory_mb} mb', f'charge {c.charge}', '',
             'geometry units angstroms noautosym nocenter noautoz']
    for a in molecule.atoms:
        x, y, z = a.position
        lines.append(f'  {a.symbol:<2} {x:16.10f} {y:16.10f} {z:16.10f}')
    lines += ['end', '', 'basis spherical' if spherical else 'basis', f'  * library {library}', 'end']
    if library.startswith('def2') and any(Z[a.symbol] > 36 for a in molecule.atoms):
        lines += ['ecp', '  * library def2-ecp', 'end']
    hf = xc in ('', 'mp2')
    iterations = 200 if c.slow_conv else 100
    energy = {'normal': '1e-6', 'tight': '1e-7', 'verytight': '1e-8'}[c.scf]
    if hf:
        block = ['', 'scf', '  ' + ('uhf' if c.multiplicity > 1 else 'rhf')]
        if c.multiplicity > 1:
            block.append(f'  nopen {c.multiplicity - 1}')
        block += [f'  maxiter {iterations}', 'end']
        if xc == 'mp2':
            # the core orbitals frozen, as ORCA and Psi4 (freeze_core) do by default: NWChem correlates all the
            # electrons otherwise — water MP2/cc-pVDZ −76.23073 against −76.22842 (ORCA) and −76.22836 (Psi4, DF)
            block += ['', 'mp2', '  freeze atomic', 'end']
        lines += block
    else:
        block = ['', 'dft'] + ['  xc ' + part if k == 0 else '  ' + part for k, part in enumerate(xc.split('\n'))]
        block += [f'  mult {c.multiplicity}', f'  iterations {iterations}', f'  convergence energy {energy}']
        if c.dispersion == 'D3BJ':
            block.append('  disp vdw 4')  # the documentation: «vdw 4 triggers the DFT-D3BJ dispersion model»
        if c.grid == 'fine':
            block.append('  grid fine')
        lines += block + ['end']
    theory = 'scf' if xc == '' else 'mp2' if xc == 'mp2' else 'dft'
    if c.task == TDDFT_TASK:
        if hf:
            raise ValueError(tr('TD-DFT в NWChem — для функционала DFT, не для HF или MP2.'))
        lines += ['', 'tddft', f'  nroots {c.states}'] + ([] if c.triplets else ['  notriplet']) + ['end']
        tasks = ['task tddft energy']
    elif c.task == NMR_TASK:
        if theory == 'mp2':
            raise ValueError(tr('ЯМР в NWChem здесь — для HF или DFT, не для MP2.'))
        lines += ['', 'property', '  shielding', 'end']
        tasks = [f'task {theory} property']
    else:
        tasks = {'Энергия': ['energy'], 'Оптимизация': ['optimize'], 'Оптимизация + частоты': ['optimize', 'freq'],
                 FREQ_TASK: ['freq'], TS_TASK: ['saddle', 'freq']}[c.task]
        tasks = [f'task {theory} {t}' for t in tasks]
    if 'Opt' in TASKS[c.task] and c.max_cycles:
        # «Предел циклов» of Sextant (0 — the limit of NWChem): without it the remedy of the doctor «Продолжить с
        # последней геометрии, циклов: N» changed nothing in the file. NWChem 7.3.0 ends such an optimization with
        # «Failed to converge in maximum number of steps or available time» (glycine, maxiter 3, 2026-11-22)
        lines += ['', 'driver', f'  maxiter {c.max_cycles}', 'end']
    if 'Freq' in TASKS[c.task] and c.thermo_changed():
        lines += ['', 'freq', f'  temp 1 {c.temperature:g}', 'end']
    if c.extra.strip():
        lines += [''] + c.extra.strip().splitlines()
    return '\n'.join(lines + [''] + tasks) + '\n'

"""The input of pw.x (Quantum ESPRESSO) for a crystal of Compass.

§1 THEORY pw.x computes a periodic crystal with plane waves up to the kinetic energy ecutwfc (and ecutrho for the
    density; Ry) and the Brillouin zone sampled on a Monkhorst–Pack grid n1 × n2 × n3. The grid follows the size of the
    cell: n_i = max(1, ⌈2π |a*_i| / Δk⌉) with the reciprocal vector a*_i (|a*_i| = 1/d of the planes (100), (010),
    (001)) and the spacing Δk (Å⁻¹; 0.25 by default — about 5 × 5 × 5 for silicon, a = 5.43 Å). Metals (an element not
    in NONMETALS of crystal_symmetry; every element a metal — crystal_symmetry.is_metal) get the cold smearing of
    Marzari–Vanderbilt (degauss 0.02 Ry), the rest fixed occupations.
§2 ALGORITHM
    pw_input(crystal, task, pseudo, …): the atoms of one cell (crystal.unit_cell) in fractions; the species in the order
    of their first atom, with the standard atomic weight (structure_tools.AVERAGE) and the file of the library; the
    cutoffs — the largest of the
    elements in the library; &CONTROL (calculation, prefix, pseudo_dir, outdir, forces and stress), &SYSTEM (ibrav = 0,
    nat, ntyp, ecutwfc, ecutrho, occupations), &ELECTRONS (conv_thr 1e-8 Ry per atom … the default of pw.x × nat), &IONS
    for relax and vc-relax, &CELL for vc-relax; CELL_PARAMETERS angstrom — the vectors of the cell (a along x, as
    crystal.Cell); ATOMIC_POSITIONS crystal; K_POINTS automatic.
§4 SPECIFICATION
    TASKS = {'Энергия': 'scf', 'Оптимизация атомов': 'relax', 'Оптимизация с ячейкой': 'vc-relax'}; kpoints(cell,
    spacing)
    -> (n1, n2, n3); pw_input(crystal, task='scf', pseudo=None, pseudo_dir='.', prefix='azimuth', spacing=0.25,
    smearing=None) -> text; ValueError for an element without a pseudopotential. STEPS {task: ((file, program), …)} —
    the band structure («Зонная структура»: scf, then calculation = 'bands' along the path of qe_paths, explicit
    «K_POINTS crystal») and the density of states («Плотность состояний»: scf, nscf on a grid of the spacing ×
    DOS_DENSER with occupations 'tetrahedra_opt', then dos.x, DeltaE 0.01 eV) run as steps of one job; nbnd = ⌈N/2⌉ +
    max(4, ⌈N/8⌉) bands for N valence electrons (z_valence of the UPF files) so that empty bands are computed too.
    «Сходимость по энергии обрезания» and «Сходимость по k-сетке» (CUTOFF_TASK, KGRID_TASK): scf runs with the cutoffs
    or the grids of convergence.py (cut1.in …, kpt1.in …), everything else as in the settings.
    «Ряд по U (DFT+U)» (HUBBARD_TASK): scf runs with U = U_VALUES on the elements of Options.hubbard (hub1.in …);
    «Магнитный порядок…» (MAGNETIC_TASK): the cell of the settings without spin, ferromagnetic and with the
    antiferromagnetic order of Options.magnetic (mag1.in …) — both with the empty bands of bands_count.
    «Уравнение состояния (ряд объёмов)» (EOS_TASK): seven runs of pw.x at EOS_FACTORS of the volume (eos1.in …), the
    atoms relaxed in each cell — for the fit of equation_of_state.py.
    steps(crystal, task, pseudo, pseudo_dir, prefix, spacing, basis) -> [(file, program, text)]; valence(path) -> float
    | None; bands_count(crystal, pseudo, pseudo_dir) -> int | None; dos_input(prefix) -> text. Options — the settings of
    the page of Sextant: the cutoffs (None — those of the library), an explicit grid n1 × n2 × n3 (None — by the
    spacing), the occupations ('auto' — smearing for a metal, else fixed; 'fixed'; 'smearing' with smearing 'mv' |
    'gaussian' | 'fd' and degauss Ry), the dispersion correction ('' | 'd3' — DFT-D3 with zero damping, dftd3_version 3
    | 'd3bj' — DFT-D3(BJ), version 4 | 'd2' — Grimme-D2), spin (nspin 2 with the starting magnetization of every
    species; with 'auto' occupations then smearing — fixed occupations of nspin 2 would need the total magnetization),
    conv (conv_thr per atom, Ry), forces (forc_conv_thr, Ry/bohr) and pressure (press_conv_thr, kbar) of a relaxation —
    None: the defaults of pw.x. pw_input(…, options=None), steps(…, options=None). Options.functional — '' PBE and
    'pbesol' (the functional of the pseudopotentials: the SSSP library of library_of(functional)), 'vdw-df2',
    'vdw-df2-b86r' (rev-vdW-DF2), 'vdw-df-cx', 'rvv10' — the non-local functionals of the vdW-DF family as input_dft
    with the PBE files (the usual practice; pw.x warns that the functional of the files is overridden) and no vdw_corr
    with them (ValueError: the dispersion is in the functional); VDW + 'ts' (vdw_corr = 'ts-vdw', Tkatchenko–Scheffler)
    and 'mbd' ('mbd_vdw', many-body dispersion); Options.charge — tot_charge. XDM is left out: in QE it needs PAW files,
    and SSSP mixes kinds. The hybrids 'pbe0' and 'hse' (HSE06, screening 0.106 bohr⁻¹ by default) as input_dft with the
    PBE files; the task «Энергия» only (ValueError otherwise): with US/PAW files — most of SSSP — pw.x stops a
    relaxation («forces for hybrid functionals + US/PAW not implemented») and computes no stress; nqx1…3 — the default
    of pw.x (the grid of the k-points), ecutfock — the default (ignored with US/PAW). DFT-D3 knows both names (hse →
    hse06 in dftd3_qe.f90). Options.magnetic — the antiferromagnetic order (modules/sextant/magnetism.py): the atoms up
    and down of a magnetic element as two species (Ni1, Ni2: the same mass and file) with starting_magnetization ±m (m —
    magnetization,
    0.5 when 0), nspin 2; fixed occupations (an insulator, 'auto') with tot_magnetization = 0 — an antiferromagnet has
    no net moment (pw.x needs it for nspin 2 with fixed occupations); the U of DFT+U on both species.
    Options.hubbard — the card HUBBARD (ortho-atomic) of modules/sextant/hubbard.py after K_POINTS (every step
    of the bands and the DOS too); ValueError for an element of it not in the cell.
§7 TESTS
    tests/sextant/test_qe_inputs.py — the input of silicon written by hand; on a computer with pw.x the real run;
    tests/sextant/test_qe_paths.py — the steps of the bands and the density of states.
"""

from dataclasses import dataclass
from math import ceil, pi

from azimuth.i18n import tr

TASKS = {'Энергия': 'scf', 'Оптимизация атомов': 'relax', 'Оптимизация с ячейкой': 'vc-relax'}
# the steps that may fail without failing the job (projwfc.x — the PDOS: its output goes to projwfc.out,
# not to pw.out, and an error of it leaves the DOS of dos.x)
OPTIONAL = {'projwfc.x': 'projwfc.out'}
BANDS_TASK, DOS_TASK = 'Зонная структура', 'Плотность состояний'  # steps of one job (STEPS)
PHONON_TASK = 'Частоты (точка Γ)'  # pw.x, ph.x at q = 0, dynmat.x — the modes in Molden format (PHONON_FILE)
# pw.x, ph.x on a grid of q, q2r.x (the force constants), matdyn.x along the path of qe_paths and matdyn.x for the DOS
DISPERSION_TASK = 'Фононные ветви и плотность состояний'
# the equation of state: the same crystal at EOS_FACTORS of its volume, one run of pw.x each (the atoms relaxed in the
# scaled cell; scf with a hybrid functional, which has no forces here) — then the Birch–Murnaghan fit of
# modules/compass/chemistry/equation_of_state.py
EOS_TASK = 'Уравнение состояния (ряд объёмов)'
EOS_FACTORS = (0.94, 0.96, 0.98, 1.0, 1.02, 1.04, 1.06)
# the convergence series: the same crystal with a row of cutoffs (cut1.in …) or of grids of k-points (kpt1.in …), one
# scf run of pw.x each — the values and the table: modules/compass/chemistry/convergence.py
CUTOFF_TASK, KGRID_TASK = 'Сходимость по энергии обрезания', 'Сходимость по k-сетке'
# the series of a magnetic crystal, scf runs with empty bands (the gap of a spin-polarized run is read from the levels):
# the U of DFT+U from U_VALUES (hub1.in …; the elements and shells of the settings, the same U for all of them), and the
# magnetic orders of one cell — without spin, ferromagnetic, antiferromagnetic (mag1.in …; the antiferromagnetic
# order of the settings is needed: it tells which atoms are up and which down)
HUBBARD_TASK, MAGNETIC_TASK = 'Ряд по U (DFT+U)', 'Магнитный порядок (без спина, ФМ, АФМ)'
U_VALUES = (0.0, 2.0, 4.0, 6.0, 8.0)  # eV
MAGNETIC_STATES = ('без спина', 'ферромагнитный', 'антиферромагнитный')
# the vacuum of a layer raised (vac1.in …): the same layer in cells of layer.vacuums, the other settings as they are
VACUUM_TASK = 'Сходимость по вакууму (слой)'
SERIES = {CUTOFF_TASK: 'cut', KGRID_TASK: 'kpt', VACUUM_TASK: 'vac', HUBBARD_TASK: 'hub', MAGNETIC_TASK: 'mag'}
STEPS = {EOS_TASK: tuple((f'eos{n + 1}.in', 'pw.x') for n in range(len(EOS_FACTORS))),
         CUTOFF_TASK: tuple((f'cut{n + 1}.in', 'pw.x') for n in range(7)),
         KGRID_TASK: tuple((f'kpt{n + 1}.in', 'pw.x') for n in range(8)),
         VACUUM_TASK: tuple((f'vac{n + 1}.in', 'pw.x') for n in range(7)),
         HUBBARD_TASK: tuple((f'hub{n + 1}.in', 'pw.x') for n in range(len(U_VALUES))),
         MAGNETIC_TASK: tuple((f'mag{n + 1}.in', 'pw.x') for n in range(len(MAGNETIC_STATES))),
         BANDS_TASK: (('scf.in', 'pw.x'), ('bands.in', 'pw.x')),
         DOS_TASK: (('scf.in', 'pw.x'), ('nscf.in', 'pw.x'), ('dos.in', 'dos.x'), ('projwfc.in', 'projwfc.x')),
         PHONON_TASK: (('scf.in', 'pw.x'), ('ph.in', 'ph.x'), ('dynmat.in', 'dynmat.x')),
         DISPERSION_TASK: (('scf.in', 'pw.x'), ('ph.in', 'ph.x'), ('q2r.in', 'q2r.x'), ('matdyn.in', 'matdyn.x'),
                           ('phdos.in', 'matdyn.x'))}
FREQ_FILE, PHDOS_FILE = 'azimuth.freq', 'azimuth.phdos'  # matdyn.x: the branches along the path, the phonon DOS
Q_SPACING = 0.6  # Å⁻¹: the grid of q of ph.x (kpoints of it), 2 to Q_MAX along each axis
Q_MAX = 4
PHDOS_GRID = 16  # the grid of matdyn.x for the density of states
PARALLEL = ('pw.x', 'ph.x')  # the steps run with mpirun; dos.x, projwfc.x and dynmat.x are quick
PHONON_FILE = 'azimuth.mold'  # the modes of dynmat.x (filmol): [FREQ], [FR-COORD], [FR-NORM-COORD] as Molden
# ph.x computes no response for these: the hybrids (no linear response with exact exchange), the dispersion
# corrections other than Grimme-D2 and the non-local vdW-DF family (ASSUMPTION: by the user guide of PHonon 7.x,
# «not implemented» — to be confirmed on a run before they are offered)
PHONON_REFUSED = ('pbe0', 'hse', 'vdw-df2', 'vdw-df2-b86r', 'vdw-df-cx', 'rvv10')
ALL_TASKS = tuple(TASKS) + tuple(STEPS)
SPACING = 0.25  # Å⁻¹
DEGAUSS = 0.02  # Ry
VDW = {'': '', 'd3': "  vdw_corr = 'dft-d3'\n  dftd3_version = 3", 'd3bj': "  vdw_corr = 'dft-d3'\n  dftd3_version = 4",
       'd2': "  vdw_corr = 'grimme-d2'",
       'ts': "  vdw_corr = 'ts-vdw'", 'mbd': "  vdw_corr = 'mbd_vdw'"}
VDW_NAMES = {'': 'нет', 'd3': 'DFT-D3 (нулевое затухание)', 'd3bj': 'DFT-D3(BJ)', 'd2': 'Grimme-D2',
             'ts': 'Ткаченко — Шеффлер (TS)', 'mbd': 'многочастичная дисперсия (MBD)'}
# the functional — PBE and PBEsol by their own SSSP library (qe_pseudo.LIBRARIES), the non-local vdW-DF family
# with the PBE files and input_dft (the names of Modules/funct.f90 of QE)
FUNCTIONALS = {'': 'PBE', 'pbesol': 'PBEsol — решётки твёрдых тел', 'lda': 'LDA (Пердью — Цунгер)', 'vdw-df2': 'vdW-DF2 (нелокальный)',
               'vdw-df2-b86r': 'rev-vdW-DF2 (нелокальный)', 'vdw-df-cx': 'vdW-DF-cx (нелокальный)',
               'rvv10': 'rVV10 (нелокальный)', 'pbe0': 'PBE0 (гибридный: 25 % обмена ХФ)',
               'hse': 'HSE06 (гибридный, экранированный — щели полупроводников)'}
NONLOCAL = ('vdw-df2', 'vdw-df2-b86r', 'vdw-df-cx', 'rvv10')
HYBRIDS = ('pbe0', 'hse')


def library_of(functional):
    """'PBEsol', 'LDA' or 'PBE' — the library of the pseudopotentials for the functional (qe_pseudo.LIBRARIES)."""
    return 'PBEsol' if functional == 'pbesol' else 'LDA' if functional == 'lda' else 'PBE'
SMEARINGS = {'mv': 'Марцари — Вандербильт', 'gaussian': 'гауссово', 'fd': 'Ферми — Дирак'}
OCCUPATIONS = {'auto': 'авто (металл — размытие)', 'fixed': 'фиксированные (изолятор)', 'smearing': 'размытие'}


@dataclass(frozen=True)
class Options:
    ecutwfc: float | None = None
    ecutrho: float | None = None
    grid: tuple | None = None
    occupations: str = 'auto'
    smearing: str = 'mv'
    degauss: float = 0.02
    vdw: str = ''
    spin: bool = False
    magnetization: float = 0.5
    conv: float = 1e-8
    forces: float | None = None
    pressure: float | None = None
    functional: str = ''  # FUNCTIONALS
    charge: float = 0.0  # tot_charge (a jellium background compensates it)
    hubbard: tuple = ()  # DFT+U — hubbard.parse: ((element, manifold, U eV), …)
    magnetic: tuple = ()  # the antiferromagnetic order — magnetism.afm_signs, +1/−1/0 per atom of the cell
    external: float | None = None  # the pressure on the cell of vc-relax, GPa (press, kbar = 10 × GPa)
    dofree: str = ''  # what of the cell a vc-relax changes — DOFREE (cell_dofree of pw.x); '' — all of it


# cell_dofree of pw.x: a layer (graphene, a slab with vacuum along c) must keep its c — else the vacuum collapses
DOFREE = {'': 'вся ячейка', '2Dxy': 'только в плоскости ab (слой с вакуумом)', 'volume': 'только объём, форма сохраняется',
          'shape': 'только форма, объём сохраняется'}
DOS_DENSER = 0.7  # the spacing of the grid of the density of states, × that of scf


def kpoints(cell, spacing=SPACING):
    import numpy as np

    rows = np.array(cell.vectors(), dtype=float)
    star = np.linalg.inv(rows).T
    return tuple(max(1, ceil(2 * pi * float(np.linalg.norm(v)) / spacing - 1e-9)) for v in star)


def grid_of(crystal, spacing=SPACING):
    """The grid of k-points of a crystal: kpoints of its cell, and one point along the vacuum of a layer (graphene, a
    slab — layer.vacuum_axis): the bands have no dispersion there."""
    from modules.compass.chemistry import layer

    grid = list(kpoints(crystal.cell, spacing))
    axis = layer.vacuum_axis(crystal)
    if axis is not None:
        grid[axis] = 1
    return tuple(grid)


def _species(atoms):
    order = []
    for a in atoms:
        if a[0] not in order:
            order.append(a[0])
    return order


def pw_input(crystal, task='scf', pseudo=None, pseudo_dir='.', prefix='azimuth', spacing=SPACING, smearing=None,
             nbnd=None, card=None, options=None):
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_symmetry as cs
    from modules.compass.chemistry.structure_tools import AVERAGE as MASSES  # standard atomic weights

    calculation = TASKS.get(task, task)
    if calculation not in tuple(TASKS.values()) + ('bands', 'nscf'):
        raise ValueError(tr('Quantum ESPRESSO: задача {} не поддерживается.').format(task))
    atoms = [a for a in cr.unit_cell(crystal) if a[0] != 'X']
    species = _species(atoms)
    pseudo = pseudo or {}
    missing = [s for s in species if s not in pseudo]
    if missing:
        raise ValueError(tr('Quantum ESPRESSO: нет псевдопотенциала для {}.').format(', '.join(missing)))
    o = options or Options()
    if o.magnetic and len(o.magnetic) != len(atoms):
        raise ValueError(tr('Магнитный порядок задан для другой ячейки — соберите входной файл заново.'))
    # the antiferromagnetic order — the up and the down atoms of an element are two species (Ni1, Ni2)
    from modules.sextant import magnetism

    names = magnetism.labels(atoms, o.magnetic) if o.magnetic else [a[0] for a in atoms]
    kinds = list(dict.fromkeys(names))
    element_of = {n: a[0] for n, a in zip(names, atoms)}
    ecutwfc = o.ecutwfc or max(pseudo[s][1] for s in species)
    ecutrho = o.ecutrho or max(max(pseudo[s][2] for s in species), 4 * ecutwfc if o.ecutwfc else 0)
    metal = cs.is_metal(species) if smearing is None else bool(smearing)  # a salt is no metal
    if o.occupations == 'fixed':
        metal = False
    elif o.occupations == 'smearing' or (o.spin and not o.magnetic and o.occupations == 'auto'):
        metal = True
    n = tuple(int(k) for k in o.grid) if o.grid else grid_of(crystal, spacing)
    control = ['  tprnfor = .true.', '  tstress = .true.'] if calculation in TASKS.values() else ["  verbosity = 'high'"]
    if o.forces and calculation in ('relax', 'vc-relax'):
        control.append(f'  forc_conv_thr = {o.forces:.1e}')
    lines = ['&CONTROL', f"  calculation = '{calculation}'", f"  prefix = '{prefix}'", f"  pseudo_dir = '{pseudo_dir}'",
             "  outdir = './out'"] + control + ['/',
             '&SYSTEM', '  ibrav = 0', f'  nat = {len(atoms)}', f'  ntyp = {len(kinds)}',
             f'  ecutwfc = {ecutwfc:g}', f'  ecutrho = {ecutrho:g}']
    if nbnd:
        lines.append(f'  nbnd = {nbnd}')
    if calculation == 'nscf':  # the density of states on a dense grid
        lines += ["  occupations = 'tetrahedra_opt'"]
    elif metal:
        lines += ["  occupations = 'smearing'", f"  smearing = '{o.smearing}'", f'  degauss = {o.degauss:g}']
    if o.magnetic:  # ±m on the two species of a magnetic element; fixed occupations — no net moment
        lines.append('  nspin = 2')
        m = abs(o.magnetization) or 0.5
        for k, name in enumerate(kinds):
            if name != element_of[name]:
                lines.append(f'  starting_magnetization({k + 1}) = {m if name.endswith("1") else -m:g}')
        if not metal and calculation != 'nscf':
            lines.append('  tot_magnetization = 0')
    elif o.spin:
        lines.append('  nspin = 2')
        lines += [f'  starting_magnetization({k + 1}) = {o.magnetization:g}' for k in range(len(kinds))]
    if o.functional in NONLOCAL:
        if o.vdw:
            raise ValueError(tr('Quantum ESPRESSO: нелокальный функционал {} уже учитывает дисперсию — уберите '
                                'поправку {}.').format(FUNCTIONALS[o.functional], VDW_NAMES.get(o.vdw, o.vdw)))
        lines.append(f"  input_dft = '{o.functional}'")
    elif o.functional in HYBRIDS:  # PW/src/setup.f90 of QE refuses relax and vc-relax of a hybrid with US/PAW
        if calculation != 'scf':
            raise ValueError(tr('Quantum ESPRESSO: с гибридным функционалом {} — только «Энергия»: силы и напряжения '
                                'гибридов с ультрамягкими и PAW-псевдопотенциалами SSSP pw.x не считает, зоны и DOS '
                                'требуют Ваннье-интерполяции.').format(FUNCTIONALS[o.functional]))
        lines.append(f"  input_dft = '{o.functional}'")
    elif o.functional not in ('', 'pbesol', 'lda'):  # these — by the functional of their pseudopotential files
        raise ValueError(tr('Quantum ESPRESSO: функционал {} не поддерживается.').format(o.functional))
    if o.charge:
        lines.append(f'  tot_charge = {o.charge:g}')
    if VDW.get(o.vdw):
        lines += VDW[o.vdw].split('\n')
    lines += ['/', '&ELECTRONS', f'  conv_thr = {o.conv * len(atoms):.1e}', '/']
    if calculation in ('relax', 'vc-relax'):
        lines += ['&IONS', '/']
    if calculation == 'vc-relax':
        if o.dofree not in DOFREE:
            raise ValueError(tr('Quantum ESPRESSO: неизвестный способ оптимизации ячейки {}.').format(o.dofree))
        lines += ['&CELL'] + ([f"  cell_dofree = '{o.dofree}'"] if o.dofree else []) + (
            [f'  press = {o.external * 10:g}'] if o.external else []) + (
            [f'  press_conv_thr = {o.pressure:g}'] if o.pressure else []) + ['/']
    lines += ['ATOMIC_SPECIES']
    lines += [f'  {k} {MASSES.get(element_of[k], 1.0):.4f} {pseudo[element_of[k]][0]}' for k in kinds]
    lines += ['CELL_PARAMETERS angstrom']
    lines += ['  ' + ' '.join(f'{x:14.8f}' for x in v) for v in crystal.cell.vectors()]
    lines += ['ATOMIC_POSITIONS crystal']
    lines += [f'  {name} {a[1]:.8f} {a[2]:.8f} {a[3]:.8f}' for name, a in zip(names, atoms)]
    lines += [card] if card else ['K_POINTS automatic', f'  {n[0]} {n[1]} {n[2]} 0 0 0']
    if o.hubbard:
        from modules.sextant import hubbard

        absent = [e for e, _, _ in o.hubbard if e not in species]
        if absent:
            raise ValueError(tr('DFT+U: {} нет в ячейке.').format(', '.join(absent)))
        # the U of an element on each of its species
        lines += hubbard.qe_card(tuple((k, m, u) for e, m, u in o.hubbard for k in kinds if element_of[k] == e))
    lines.append('')
    return '\n'.join(lines)


def valence(path):
    """The number of valence electrons of a pseudopotential file (UPF 2: z_valence="…"; UPF 1: «… Z valence»)."""
    import re

    try:
        with open(path, encoding='utf-8', errors='replace') as f:
            head = f.read(200000)
    except OSError:
        return None
    m = re.search(r'z_valence\s*=\s*"\s*([-+0-9.EeDd]+)', head) or re.search(r'([-+0-9.EeDd]+)\s+Z valence', head)
    return float(m.group(1).replace('D', 'E').replace('d', 'e')) if m else None


def bands_count(crystal, pseudo, pseudo_dir):
    """nbnd: the occupied bands and at least 4 (or ⅛ more) empty ones; None when a z_valence is not found."""
    from collections import Counter
    from math import ceil
    from pathlib import Path

    from modules.compass.chemistry import crystal as cr

    counts = Counter(a[0] for a in cr.unit_cell(crystal) if a[0] != 'X')
    total = 0.0
    for symbol, n in counts.items():
        z = valence(Path(pseudo_dir) / pseudo[symbol][0]) if symbol in pseudo else None
        if z is None:
            return None
        total += z * n
    occupied = ceil(total / 2 - 1e-9)
    return occupied + max(4, ceil(occupied / 8))


def dos_input(prefix='azimuth'):
    return '\n'.join(['&DOS', f"  prefix = '{prefix}'", "  outdir = './out'", f"  fildos = '{prefix}.dos'",
                       '  DeltaE = 0.01', '/', ''])


def projwfc_input(prefix='azimuth'):
    """The projected DOS (Löwdin projections on the atomic wave functions of the pseudopotentials):
    <prefix>.pdos_tot and <prefix>.pdos_atm#N(El)_wfc#M(l), on the grid of dos.x (crystal_pdos.qe_curves)."""
    return '\n'.join(['&PROJWFC', f"  prefix = '{prefix}'", "  outdir = './out'", f"  filpdos = '{prefix}'",
                       '  DeltaE = 0.01', '/', ''])


def ph_input(prefix='azimuth', epsil=True):
    """ph.x at q = 0 (Γ): the dynamical matrix in <prefix>.dyn; epsil — the dielectric tensor and the Born effective
    charges (an insulator only: ph.x stops on a metal), which give the IR intensities and the LO–TO splitting."""
    return '\n'.join(['phonons at Gamma', '&INPUTPH', f"  prefix = '{prefix}'", "  outdir = './out'",
                       f"  fildyn = '{prefix}.dyn'", '  tr2_ph = 1.0d-14', f"  epsil = {'.true.' if epsil else '.false.'}",
                       '/', '0.0 0.0 0.0', ''])


def qgrid(cell):
    """The grid of q of ph.x: by the spacing Q_SPACING, at least 2 and at most Q_MAX along each axis (the cost of
    ph.x grows with every irreducible q)."""
    return tuple(max(2, min(Q_MAX, n)) for n in kpoints(cell, Q_SPACING))


def ph_grid_input(grid, prefix='azimuth', epsil=True):
    """ph.x on the grid of q (ldisp): <prefix>.dyn0 (the list of q) and <prefix>.dynN of each irreducible q."""
    n1, n2, n3 = grid
    return '\n'.join(['phonons on a grid of q', '&INPUTPH', f"  prefix = '{prefix}'", "  outdir = './out'",
                       f"  fildyn = '{prefix}.dyn'", '  tr2_ph = 1.0d-14', f"  epsil = {'.true.' if epsil else '.false.'}",
                       '  ldisp = .true.', f'  nq1 = {n1}', f'  nq2 = {n2}', f'  nq3 = {n3}', '/', ''])


def q2r_input(prefix='azimuth'):
    """q2r.x: the dynamical matrices of the grid → the interatomic force constants in real space."""
    return '\n'.join(['&INPUT', f"  fildyn = '{prefix}.dyn'", "  zasr = 'crystal'", f"  flfrc = '{prefix}.fc'", '/', ''])


def matdyn_path_input(fractions, prefix='azimuth'):
    """matdyn.x: the frequencies at the q of the path (crystal coordinates, as K_POINTS crystal of the bands)."""
    lines = ['&INPUT', "  asr = 'crystal'", f"  flfrc = '{prefix}.fc'", f"  flfrq = '{FREQ_FILE}'",
             '  q_in_cryst_coord = .true.', '/', f'{len(fractions)}']
    lines += [f'  {f[0]:.8f} {f[1]:.8f} {f[2]:.8f}' for f in fractions]
    return '\n'.join(lines) + '\n'


def matdyn_dos_input(prefix='azimuth', grid=PHDOS_GRID):
    """matdyn.x: the phonon density of states on a grid of q (deltaE 1 cm⁻¹)."""
    return '\n'.join(['&INPUT', "  asr = 'crystal'", f"  flfrc = '{prefix}.fc'", '  dos = .true.',
                       f"  fldos = '{PHDOS_FILE}'", f'  nk1 = {grid}', f'  nk2 = {grid}', f'  nk3 = {grid}',
                       '  deltaE = 1.0', '/', ''])


def dynmat_input(prefix='azimuth'):
    """dynmat.x: the acoustic sum rule imposed on the matrix of ph.x (asr 'crystal' — three zero modes), the modes
    written for Molden (filmol) and the IR activities (with the Born charges of epsil)."""
    return '\n'.join(['&INPUT', f"  fildyn = '{prefix}.dyn'", "  asr = 'crystal'", f"  filmol = '{PHONON_FILE}'",
                       "  filout = 'dynmat.modes'", '/', ''])


def steps(crystal, task, pseudo, pseudo_dir='.', prefix='azimuth', spacing=SPACING, basis=None, conventional=None,
          options=None):
    """[(file, program, text)] of a task: one pw.in for TASKS, the steps of STEPS for the bands and the density of
    states. crystal — the cell computed; conventional — the cell of the file (its path; basis — the rows of crystal in
    its fractions, crystal.primitive_basis) for the band path."""
    if task in TASKS:
        return [('pw.in', 'pw.x', pw_input(crystal, task, pseudo, pseudo_dir, prefix, spacing, options=options))]
    if task not in STEPS:
        raise ValueError(tr('Quantum ESPRESSO: задача {} не поддерживается.').format(task))
    if task in SERIES:
        import re
        from dataclasses import replace

        from modules.compass.chemistry import convergence

        o = options or Options()
        if task in (HUBBARD_TASK, MAGNETIC_TASK):
            if task == HUBBARD_TASK:
                if not o.hubbard:
                    raise ValueError(tr('Ряд по U: задайте в настройках DFT+U, к каким элементам ставить U (например, '
                                        '«Ni 6») — значение в ряду меняется от {:g} до {:g} эВ.').format(U_VALUES[0], U_VALUES[-1]))
                variants = [replace(o, hubbard=tuple((e, m, u) for e, m, _ in o.hubbard) if u else ()) for u in U_VALUES]
            else:
                if not o.magnetic:
                    raise ValueError(tr('Магнитный порядок: выберите в настройках антиферромагнитный порядок (и суперячейку, '
                                        'в которой он помещается) — ряд сравнит его с ферромагнитным и с расчётом без спина.'))
                variants = [replace(o, spin=False, magnetic=()), replace(o, spin=True, magnetic=()), replace(o, spin=True)]
            nbnd = bands_count(crystal, pseudo, pseudo_dir)  # empty bands: the gap of the levels
            return [(f'{SERIES[task]}{n + 1}.in', 'pw.x', pw_input(crystal, 'scf', pseudo, pseudo_dir, prefix, spacing,
                                                                   nbnd=nbnd, options=variant)) for n, variant in enumerate(variants)]
        if task == VACUUM_TASK:
            from modules.compass.chemistry import layer

            axis = layer.vacuum_axis(crystal)
            if axis is None:
                raise ValueError(tr('Ряд по вакууму: в ячейке нет вакуума (пустого промежутка от {:g} Å) — это не слой.')
                                 .format(layer.LEAST))
            same = o if o.grid else replace(o, grid=grid_of(crystal, spacing))  # one grid for every cell
            return [(f'vac{n + 1}.in', 'pw.x', pw_input(layer.with_vacuum(crystal, value, axis), 'scf', pseudo, pseudo_dir,
                                                       prefix, spacing, options=same))
                    for n, value in enumerate(layer.vacuums(layer.vacuum(crystal, axis)))]
        if task == CUTOFF_TASK:  # around the cutoffs the plain input would get, with its ratio ecutrho / ecutwfc
            plain = pw_input(crystal, 'scf', pseudo, pseudo_dir, prefix, spacing, options=o)
            wfc, rho = (float(re.search(rf'{key} = ([\d.eE+-]+)', plain).group(1)) for key in ('ecutwfc', 'ecutrho'))
            grid = o.grid or grid_of(crystal, spacing)
            variants = [replace(o, ecutwfc=w, ecutrho=r, grid=grid) for w, r in convergence.cutoffs(wfc, rho / wfc)]
        else:
            variants = [replace(o, grid=g) for g in convergence.grids(tuple(o.grid or grid_of(crystal, spacing)))]
        return [(f'{SERIES[task]}{n + 1}.in', 'pw.x', pw_input(crystal, 'scf', pseudo, pseudo_dir, prefix, spacing,
                                                               options=variant)) for n, variant in enumerate(variants)]
    if task == EOS_TASK:
        from modules.compass.chemistry import equation_of_state

        from dataclasses import replace

        o = options or Options()
        kind = 'scf' if o.functional in HYBRIDS else 'relax'
        # one grid of k-points for every volume (that of the cell as it is): a grid that changed along the series
        # would put a step into E(V)
        same = o if o.grid else replace(o, grid=grid_of(crystal, spacing))
        return [(name, tool, pw_input(equation_of_state.scaled(crystal, factor), kind, pseudo, pseudo_dir, prefix, spacing,
                                      options=same))
                for (name, tool), factor in zip(STEPS[EOS_TASK], EOS_FACTORS)]
    if task in (PHONON_TASK, DISPERSION_TASK):
        o = options or Options()
        if o.functional in PHONON_REFUSED or o.vdw not in ('', 'd2'):
            raise ValueError(tr('ph.x не считает частоты с этим функционалом или поправкой на дисперсию — выберите PBE '
                                'или PBEsol (дисперсия: нет или Grimme-D2) либо CP2K.'))
        # without the operations of fractional translations: ph.x stops on those the FFT grid of pw.x does not
        # carry («scale_sym_ops: incompatible FFT grid» — silicon of Fd-3m :2 on a grid of q, QE 7.6)
        scf = pw_input(crystal, 'scf', pseudo, pseudo_dir, prefix, spacing, options=options).replace(
            '&SYSTEM\n', '&SYSTEM\n  force_symmorphic = .true.\n', 1)
        metal = "occupations = 'smearing'" in scf
        if task == PHONON_TASK:
            return [('scf.in', 'pw.x', scf), ('ph.in', 'ph.x', ph_input(prefix, epsil=not metal)),
                    ('dynmat.in', 'dynmat.x', dynmat_input(prefix))]
        from modules.sextant import qe_paths

        p = qe_paths.path(conventional or crystal, basis)
        return [('scf.in', 'pw.x', scf), ('ph.in', 'ph.x', ph_grid_input(qgrid(crystal.cell), prefix, epsil=not metal)),
                ('q2r.in', 'q2r.x', q2r_input(prefix)), ('matdyn.in', 'matdyn.x', matdyn_path_input(p.fractions, prefix)),
                ('phdos.in', 'matdyn.x', matdyn_dos_input(prefix))]
    nbnd = bands_count(crystal, pseudo, pseudo_dir)
    scf = pw_input(crystal, 'scf', pseudo, pseudo_dir, prefix, spacing, options=options)
    if task == BANDS_TASK:
        from modules.sextant import qe_paths

        p = qe_paths.path(conventional or crystal, basis)
        second = pw_input(crystal, 'bands', pseudo, pseudo_dir, prefix, spacing, nbnd=nbnd, card=qe_paths.kpoints_card(p),
                          options=options)
        return [('scf.in', 'pw.x', scf), ('bands.in', 'pw.x', second)]
    dense = None
    if options is not None and options.grid:
        from dataclasses import replace

        dense = replace(options, grid=tuple(max(1, ceil(k / DOS_DENSER)) for k in options.grid))
    nscf = pw_input(crystal, 'nscf', pseudo, pseudo_dir, prefix, spacing * DOS_DENSER, nbnd=nbnd, options=dense or options)
    return [('scf.in', 'pw.x', scf), ('nscf.in', 'pw.x', nscf), ('dos.in', 'dos.x', dos_input(prefix)),
            ('projwfc.in', 'projwfc.x', projwfc_input(prefix))]

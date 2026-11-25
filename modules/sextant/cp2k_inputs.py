"""The input of CP2K (Quickstep, GPW) for a crystal of Compass.

§1 THEORY
    CP2K computes a periodic cell with Gaussian basis sets and plane waves for the density (GPW, VandeVondele et al.,
    Comput. Phys. Commun. 167 (2005) 103): the molecularly optimised basis sets DZVP-MOLOPT-SR-GTH (VandeVondele &
    Hutter, J. Chem. Phys. 127 (2007) 114105), the pseudopotentials of Goedecker–Teter–Hutter for PBE (GTH-PBE), the
    grid of the density up to CUTOFF Ry (REL_CUTOFF for the Gaussians mapped on it). Quickstep samples the Brillouin
    zone at Γ only here: a cell of 10 Å and more (a molecular crystal of tens of atoms) needs no more; a small cell is
    computed in a supercell (crystal.supercell). An insulator converges with the orbital transformation (OT); a metal —
    by diagonalisation with Fermi–Dirac smearing and added empty orbitals. The dispersion correction of Grimme D3 (zero
    damping) or D3(BJ) — dftd3.dat of CP2K.
§2 ALGORITHM cp2k_input(crystal, task, options): &GLOBAL (PROJECT azimuth, RUN_TYPE ENERGY | GEO_OPT | CELL_OPT);
    &FORCE_EVAL with &DFT (BASIS_SET_FILE_NAME BASIS_MOLOPT, POTENTIAL_FILE_NAME GTH_POTENTIALS, &MGRID, &QS
    EPS_DEFAULT, &SCF — OT or diagonalisation with &SMEAR, &XC PBE with &VDW_POTENTIAL) and &SUBSYS (&CELL A, B, C in Å
    — the vectors of the cell, a along x, as crystal.Cell; &COORD SCALED — the fractions of the atoms; &KIND per
    element: the basis set and GTH-PBE); &PRINT &MO_MOLDEN of &DFT — the wave function in Molden format
    (azimuth-MOS-1_N.molden at each step N, 2026-11-12; readers.cp2k.for_multiwfn adds [Cell] and [Nval] to the last one
    for Multiwfn); &PDOS — the projected DOS with NLUMO = 4 per atom (at most 300) empty levels, of the last step of an
    optimization; STRESS_TENSOR ANALYTICAL for CELL_OPT; VIBRATIONAL_ANALYSIS — the frequencies at Γ
    (&VIBRATIONAL_ANALYSIS, DX 0.01 bohr, FULLY_PERIODIC, the modes in azimuth-VIBRATIONS-1.mol; EPS_SCF at most 1e-8;
    no orbitals or PDOS printed at the 6N displaced cells); &MOTION (&GEO_OPT or &CELL_OPT, BFGS, MAX_ITER, the position
    file every step).
§4 SPECIFICATION
    TASKS = {'Энергия': 'ENERGY', 'Оптимизация атомов': 'GEO_OPT', 'Оптимизация с ячейкой': 'CELL_OPT'};
    BASES — the basis sets offered; ELEMENTS — the elements with DZVP-MOLOPT-SR-GTH in BASIS_MOLOPT of CP2K 2026.2;
    Options(cutoff=400, rel_cutoff=50, basis='DZVP-MOLOPT-SR-GTH', vdw='d3bj', occupations='auto', temperature=300 K,
    eps_scf=1e-6, max_iter=200, spin=False); cp2k_input(crystal, task, options=None) -> text; ValueError for an element
    without the basis set; INPUT = 'azimuth.inp', OUTPUT = 'cp2k.out'.
    Options.charge — CHARGE of &DFT; an odd number of electrons (Z − charge: the GTH cores hold even numbers)
    — UKS with MULTIPLICITY 2. Options.functional — FUNCTIONALS (PBE, PBEsol, revPBE, BLYP; POTENTIALS — GTH-PBE,
    GTH-BLYP for BLYP: ValueError for an element without it), the reference functional of D3 the same; BASES +
    DZVP-MOLOPT-GTH and TZVP-MOLOPT-GTH; the full MOLOPT sets (MOLOPT_FULL) — H C N O F Si P S Cl only (BASIS_MOLOPT,
    read 2026-11-15). Functional 'GFN1-XTB' — GFN1-xTB (Grimme, Bannwarth, Shushkov, J. Chem. Theory Comput. 13 (2017)
    1989) of Quickstep, periodic as tests/xTB/regtest-1/si_geo.inp of CP2K (read 2026-11-15): &QS METHOD xTB, &XTB (no
    DO_EWALD: CP2K 2026.2 calls it deprecated — the periodicity is that of &CELL PERIODIC XYZ) with the D3 of the method
    (&PARAMETER DISPERSION_PARAMETER_FILE dftd3.dat), &POISSON &EWALD SPME ALPHA 1.0 GMAX (ewald_gmax — 25 points over
    5.431 Å scaled to the cell), diagonalisation with DIRECT_P_MIXING; no basis, potentials, &XC, &VDW_POTENTIAL, &KIND
    or Molden file; the elements H–Rn; DFT+U — ValueError.
    0.189.0 (&KIND of src/input_cp2k_subsys.F v2026.2: ELEMENT, MAGNETIZATION — «the magnetization used in the atomic
    initial guess»): Options.magnetic — the antiferromagnetic order (modules/sextant/magnetism.py): the kinds Ni1 and
    Ni2 with ELEMENT Ni and MAGNETIZATION ±magnetization, UKS; Options.spin — UKS, MAGNETIZATION on every d or f kind.
    Not with GFN1-xTB (ValueError).
    Options.hubbard — DFT+U (modules/sextant/hubbard.py): PLUS_U_METHOD MULLIKEN, &DFT_PLUS_U of the kinds.
§7 TESTS
    tests/sextant/test_cp2k_inputs.py — the input of silicon; tests/data/cp2k — the real runs of CP2K 2026.2.
"""

from dataclasses import dataclass
from math import ceil

from azimuth.i18n import tr

TASKS = {'Энергия': 'ENERGY', 'Оптимизация атомов': 'GEO_OPT', 'Оптимизация с ячейкой': 'CELL_OPT',
         'Частоты (точка Γ)': 'VIBRATIONAL_ANALYSIS'}  # the phonons at Γ of the cell computed
INPUT, OUTPUT, PROJECT = 'azimuth.inp', 'cp2k.out', 'azimuth'
VIBRATIONS = PROJECT + '-VIBRATIONS-1.mol'  # the modes in Molden format (&VIBRATIONAL_ANALYSIS &PRINT &MOLDEN_VIB)
PDOS_LUMO_PER_ATOM, PDOS_LUMO_MAX = 4, 300  # the empty levels in the .pdos files
MOLDEN = PROJECT + '-MOS-1_0.molden'  # the wave function of the start (&MO_MOLDEN, Γ point); _N — of step N
BASES = {'DZVP-MOLOPT-SR-GTH': 'DZVP-MOLOPT-SR (двухэкспонентный, все элементы)',
         'DZVP-MOLOPT-GTH': 'DZVP-MOLOPT (двухэкспонентный с диффузными, H C N O F Si P S Cl)',
         'TZVP-MOLOPT-GTH': 'TZVP-MOLOPT (трёхэкспонентный, H C N O F Si P S Cl)',
         'TZV2P-MOLOPT-GTH': 'TZV2P-MOLOPT (трёхэкспонентный, две поляризующие, H C N O F Si P S Cl)'}
VDW_NAMES = {'': 'нет', 'd3': 'DFT-D3 (нулевое затухание)', 'd3bj': 'DFT-D3(BJ)'}
ELEMENTS = frozenset(
    'H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo '
    'Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn'.split())
# the full MOLOPT sets — the nine elements of the original paper only
# (before, TZV2P was taken for H–Ar: CP2K stopped on Na, Mg, Al, Ar, … with «basis set not found»)
MOLOPT_FULL = frozenset('H C N O F Si P S Cl'.split())
TZV2P = MOLOPT_FULL
# the functionals (&XC_FUNCTIONAL; PBEsol and revPBE — PARAMETRIZATION of &PBE, input_cp2k_xc.F) with their
# GTH pseudopotentials (no GTH-PBEsol or GTH-revPBE: the GTH-PBE ones, as usual) and REFERENCE_FUNCTIONAL of D3 —
# qs_scaling_dftd3 and qs_scaling_dftd3bj of CP2K hold PBE, PBESOL, REVPBE and BLYP
FUNCTIONALS = {'PBE': 'PBE', 'PBESOL': 'PBEsol — решётки твёрдых тел', 'REVPBE': 'revPBE', 'BLYP': 'BLYP',
               'GFN1-XTB': 'GFN1-xTB (полуэмпирика: быстро, большие ячейки)'}
XTB = 'GFN1-XTB'  # &QS METHOD xTB — no basis, potentials or &XC; its own D3
POTENTIALS = {'PBE': 'GTH-PBE', 'PBESOL': 'GTH-PBE', 'REVPBE': 'GTH-PBE', 'BLYP': 'GTH-BLYP'}
# the elements with the alias GTH-BLYP in GTH_POTENTIALS of CP2K (read 2026-11-15) — of the same valence as GTH-PBE
BLYP = frozenset('H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Sr Y '
                 'Zr Mo Ru Rh Pd Ag In Sb Te I Ba W Au Bi'.split())


@dataclass(frozen=True)
class Options:
    cutoff: float = 400.0
    rel_cutoff: float = 50.0
    basis: str = 'DZVP-MOLOPT-SR-GTH'
    vdw: str = 'd3bj'
    occupations: str = 'auto'  # 'auto' | 'fixed' (OT) | 'smearing'
    temperature: float = 300.0  # K, Fermi–Dirac
    eps_scf: float = 1e-6
    max_iter: int = 200
    spin: bool = False
    charge: int = 0  # CHARGE of the cell
    functional: str = 'PBE'  # FUNCTIONALS
    hubbard: tuple = ()  # DFT+U — hubbard.parse
    magnetic: tuple = ()  # the antiferromagnetic order — magnetism.afm_signs per atom of the cell
    magnetization: float = 2.0  # MAGNETIZATION of a magnetic kind (electrons) in the atomic guess
    external: float | None = None  # the pressure on the cell of CELL_OPT, GPa (EXTERNAL_PRESSURE in bar)


def ewald_gmax(cell):
    """GMAX of the SPME Ewald sum along a, b, c — the density of tests/xTB/regtest-1/si_geo.inp of CP2K (25
    points over 5.431 Å), odd, at least 25."""
    out = []
    for length in (cell.a, cell.b, cell.c):
        g = max(25, ceil(25 * length / 5.431 - 1e-9))
        out.append(g + 1 - g % 2)
    return tuple(out)


def _species(atoms):
    order = []
    for a in atoms:
        if a[0] not in order:
            order.append(a[0])
    return order


def cp2k_input(crystal, task='Энергия', options=None):
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_symmetry as cs

    o = options or Options()
    run = TASKS.get(task, task)
    if run not in TASKS.values():
        raise ValueError(tr('CP2K: задача {} не поддерживается.').format(task))
    atoms = [a for a in cr.unit_cell(crystal) if a[0] != 'X']
    species = _species(atoms)
    from modules.sextant import magnetism

    if o.magnetic and len(o.magnetic) != len(atoms):
        raise ValueError(tr('Магнитный порядок задан для другой ячейки — соберите входной файл заново.'))
    if (o.magnetic or o.spin) and o.functional == 'GFN1-XTB':
        raise ValueError(tr('CP2K: магнитный порядок — только с функционалом DFT, не с GFN1-xTB.'))
    names = magnetism.labels(atoms, o.magnetic) if o.magnetic else [a[0] for a in atoms]
    if o.functional not in FUNCTIONALS:
        raise ValueError(tr('CP2K: функционал {} не поддерживается.').format(o.functional))
    xtb = o.functional == XTB
    if xtb:  # GFN1-xTB is parametrized for H–Rn (Z 1–86)
        from azimuth.core import Z as _z

        known = {s for s in species if 0 < _z.get(s, 0) <= 86}
    else:
        known = ELEMENTS if o.basis == 'DZVP-MOLOPT-SR-GTH' else MOLOPT_FULL
    if xtb and o.hubbard:
        raise ValueError(tr('CP2K: DFT+U — только с функционалом DFT, не с GFN1-xTB.'))
    no_potential = [s for s in species if o.functional == 'BLYP' and s not in BLYP]
    if no_potential:
        raise ValueError(tr('CP2K: нет псевдопотенциала GTH-BLYP для {}.').format(', '.join(no_potential)))
    missing = [s for s in species if s not in known]
    if missing:
        if xtb:
            raise ValueError(tr('GFN1-xTB: нет параметров для {} (только H–Rn).').format(', '.join(missing)))
        raise ValueError(tr('CP2K: нет базиса {} для {}.').format(o.basis, ', '.join(missing)))
    from modules.sextant import hubbard

    absent = [e for e, _, _ in o.hubbard if e not in species]
    if absent:
        raise ValueError(tr('DFT+U: {} нет в ячейке.').format(', '.join(absent)))
    metal = cs.is_metal(species)  # every element a metal; CsCl, NaCl are insulators
    smear = o.occupations == 'smearing' or (o.occupations == 'auto' and metal)
    lines = ['&GLOBAL', f'  PROJECT {PROJECT}', f'  RUN_TYPE {run}', '  PRINT_LEVEL LOW', '&END GLOBAL',
             '&FORCE_EVAL', '  METHOD Quickstep']
    if run == 'CELL_OPT':
        lines.append('  STRESS_TENSOR ANALYTICAL')
    from azimuth.core import Z

    lines += ['  &DFT'] + ([] if xtb else ['    BASIS_SET_FILE_NAME BASIS_MOLOPT', '    POTENTIAL_FILE_NAME GTH_POTENTIALS'])
    lines.append(f'    CHARGE {int(o.charge)}')
    odd = (sum(Z.get(a[0], 0) for a in atoms) - int(o.charge)) % 2  # the GTH cores hold even numbers
    if o.hubbard:
        lines.append('    PLUS_U_METHOD MULLIKEN')
    if o.spin or o.magnetic or odd:
        lines.append('    UKS')
    if odd:
        lines.append('    MULTIPLICITY 2')
    vibrations = run == 'VIBRATIONAL_ANALYSIS'
    eps_scf = min(o.eps_scf, 1e-8) if vibrations else o.eps_scf  # the forces of the displaced cells: a tight SCF
    if xtb:  # as tests/xTB/regtest-1/si_geo.inp of CP2K — Ewald (SPME) for the periodic Coulomb term
        lines += ['    &POISSON', '      &EWALD', '        EWALD_TYPE SPME', '        ALPHA 1.0',
                  '        GMAX ' + ' '.join(str(g) for g in ewald_gmax(crystal.cell)), '      &END EWALD', '    &END POISSON',
                  '    &QS', '      METHOD xTB', '      &XTB', '        &PARAMETER',
                  '          DISPERSION_PARAMETER_FILE dftd3.dat', '        &END PARAMETER', '      &END XTB', '    &END QS',
                  '    &SCF', '      SCF_GUESS MOPAC', f'      EPS_SCF {eps_scf:.1E}']
    else:
        lines += ['    &MGRID', f'      CUTOFF {o.cutoff:g}', f'      REL_CUTOFF {o.rel_cutoff:g}', '    &END MGRID',
                  '    &QS', '      EPS_DEFAULT 1.0E-12', '    &END QS', '    &SCF', '      SCF_GUESS ATOMIC',
                  f'      EPS_SCF {eps_scf:.1E}']
    if xtb:  # diagonalisation with the density mixing of the xTB tests of CP2K
        lines += ['      MAX_SCF 300', '      &MIXING', '        METHOD DIRECT_P_MIXING', '        ALPHA 0.1', '      &END MIXING']
        if smear:
            lines += ['      ADDED_MOS 20', '      &SMEAR ON', '        METHOD FERMI_DIRAC',
                      f'        ELECTRONIC_TEMPERATURE [K] {o.temperature:g}', '      &END SMEAR']
    elif smear:
        lines += ['      MAX_SCF 300', '      ADDED_MOS 20', '      &DIAGONALIZATION', '        ALGORITHM STANDARD',
                  '      &END DIAGONALIZATION', '      &MIXING', '        METHOD BROYDEN_MIXING', '        ALPHA 0.2',
                  '      &END MIXING', '      &SMEAR ON', '        METHOD FERMI_DIRAC',
                  f'        ELECTRONIC_TEMPERATURE [K] {o.temperature:g}', '      &END SMEAR']
    else:
        lines += ['      MAX_SCF 50', '      &OT', '        MINIMIZER DIIS', '        PRECONDITIONER FULL_SINGLE_INVERSE',
                  '      &END OT', '      &OUTER_SCF', '        MAX_SCF 20', f'        EPS_SCF {eps_scf:.1E}',
                  '      &END OUTER_SCF']
    lines += ['    &END SCF']
    if not xtb:
        lines += ['    &XC']
    if xtb:
        pass
    elif o.functional in ('PBE', 'BLYP'):
        lines += [f'      &XC_FUNCTIONAL {o.functional}', '      &END XC_FUNCTIONAL']
    else:  # PBEsol, revPBE
        lines += ['      &XC_FUNCTIONAL', '        &PBE', f'          PARAMETRIZATION {o.functional}', '        &END PBE',
                  '      &END XC_FUNCTIONAL']
    if o.vdw and not xtb:
        lines += ['      &VDW_POTENTIAL', '        POTENTIAL_TYPE PAIR_POTENTIAL', '        &PAIR_POTENTIAL',
                  f"          TYPE {'DFTD3(BJ)' if o.vdw == 'd3bj' else 'DFTD3'}", '          PARAMETER_FILE_NAME dftd3.dat',
                  f'          REFERENCE_FUNCTIONAL {o.functional}', '        &END PAIR_POTENTIAL', '      &END VDW_POTENTIAL']
    # the orbitals in Molden format —
    # azimuth-MOS-1_0.molden (Γ point), read by Multiwfn (its CP2K interface)
    if not xtb:
        lines += ['    &END XC']
    if not vibrations:  # 6N displaced cells of the frequencies — no orbitals and PDOS of each
        lines += ['    &PRINT']
        if not xtb:  # the STO-nG orbitals of xTB — not for Multiwfn (its valence table is that of GTH)
            lines += ['      &MO_MOLDEN', '        NDIGITS 9', '        GTO_KIND SPHERICAL', '      &END MO_MOLDEN']
        # the projected density of states — azimuth-k<kind>-1.pdos (s, p, d, f of each kind, the empty
        # levels too: NLUMO; an optimization prints it at its last step only, ADD_LAST NUMERIC → …-1_<step>.pdos)
        # CP2K 2026.2 keeps the
        # PDOS inside the print key DOS (src/input_cp2k_print_dft.F of v2026.2, «Nest PDOS controls inside DOS print
        # section», #5335) — NLUMO and the iteration levels are those of DOS; the files stay <project>-k<kind>-1.pdos
        # (qs_pdos.F of v2026.2: middle name «k<kind>», extension .pdos)
        lines += ['      &DOS', f'        NLUMO {min(PDOS_LUMO_MAX, PDOS_LUMO_PER_ATOM * len(atoms))}']
        if run in ('GEO_OPT', 'CELL_OPT'):
            lines += ['        ADD_LAST NUMERIC', '        &EACH', f'          {run} 0', '        &END EACH']
        lines += ['        &PDOS', '          COMPONENTS F', '        &END PDOS', '      &END DOS', '    &END PRINT']
    lines += ['  &END DFT', '  &SUBSYS', '    &CELL']
    for name, v in zip('ABC', crystal.cell.vectors()):
        lines.append(f'      {name} ' + ' '.join(f'{x:14.8f}' for x in v))
    lines += ['      PERIODIC XYZ', '    &END CELL', '    &COORD', '      SCALED']
    lines += [f'      {name} {a[1]:.8f} {a[2]:.8f} {a[3]:.8f}' for name, a in zip(names, atoms)]
    lines += ['    &END COORD']
    element_of = {n: a[0] for n, a in zip(names, atoms)}
    moving = set(magnetism.magnetic(species)) if o.spin and not o.magnetic else set()
    for s in ([] if xtb else list(dict.fromkeys(names))):
        e = element_of[s]
        kind = [f'    &KIND {s}'] + ([f'      ELEMENT {e}'] if s != e else [])
        kind += [f'      BASIS_SET {o.basis}', f'      POTENTIAL {POTENTIALS[o.functional]}']
        if s != e:  # the up (…1) and the down (…2) kind of an antiferromagnet; the moment of the guess
            kind.append(f'      MAGNETIZATION {o.magnetization if s.endswith("1") else -o.magnetization:g}')
        elif e in moving:  # a ferromagnet: every magnetic kind up
            kind.append(f'      MAGNETIZATION {o.magnetization:g}')
        lines += kind + [*hubbard.cp2k_kind(o.hubbard, e), '    &END KIND']
    lines += ['  &END SUBSYS', '&END FORCE_EVAL']
    if run in ('GEO_OPT', 'CELL_OPT'):
        section = run
        # CP2K 2026.2 refuses MOTION/CELL_OPT/TYPE — «removed because
        # cell optimizations now always use DIRECT_CELL_OPT»
        lines += ['&MOTION', f'  &{section}']
        if run == 'CELL_OPT' and o.external:
            lines.append(f'    EXTERNAL_PRESSURE [bar] {o.external * 1e4:g}')
        lines += ['    OPTIMIZER BFGS', f'    MAX_ITER {o.max_iter}', f'  &END {section}', '  &PRINT',
                  '    &TRAJECTORY', '      &EACH', f'        {run} 1', '      &END EACH', '    &END TRAJECTORY',
                  '    &CELL', '      &EACH', f'        {run} 1', '      &END EACH', '    &END CELL', '  &END PRINT',
                  '&END MOTION']
    if vibrations:  # the Hessian by finite differences (±DX bohr), the cell periodic: no rotations removed
        lines += ['&VIBRATIONAL_ANALYSIS', '  DX 0.01', '  NPROC_REP 1', '  FULLY_PERIODIC T', '  &PRINT',
                  '    &MOLDEN_VIB', '    &END MOLDEN_VIB', '  &END PRINT', '&END VIBRATIONAL_ANALYSIS']
    lines.append('')
    return '\n'.join(lines)

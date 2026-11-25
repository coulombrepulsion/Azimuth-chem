"""The input of CRYSTAL (.d12) for a crystal of Compass, and of its program properties with TOPOND (.d3).
§1 THEORY CRYSTAL (Dovesi et al., WIREs Comput. Mol. Sci. 8 (2018) e1360) reads its input in blocks. 1 — the geometry: a
    title; CRYSTAL; «IFLAG IFHR IFSO» (0 — the space group by its number; IFHR 0 — hexagonal axes of a rhombohedral
    group; IFSO 0 — of two origin choices the second one, as most CIFs and the table of Compass), the number, the
    minimal lattice parameters of the crystal system (cubic a; tetragonal, trigonal and hexagonal a, c; orthorhombic a,
    b, c; monoclinic a, b, c and the angle of the unique axis; triclinic all six), the number of atoms of the asymmetric
    unit and each «Z x y z» in fractions of the conventional cell; then the keywords of the geometry — OPTGEOM
    (FULLOPTG: atoms and cell; ATOMONLY; EXTPRESS — a hydrostatic pressure in hartree/bohr³, 1 hartree/bohr³ = 29421
    GPa; MAXCYCLE), ELASTCON (the elastic tensor by strains of the cell), FREQCALC (the phonons at Γ, INTENS — the IR
    intensities) — each closed by END, and END of the block. 2 — the basis set: written by hand, or (CRYSTAL17 and
    later) BASISSET with the name of one of the library — then BASISSET and the name take the place of the END of the
    geometry: POB-DZVP, POB-DZVPP, POB-TZVP (Peintinger, Vilela Oliveira, Bredow, J. Comput. Chem. 34 (2013) 451 — for
    solids, H–Br; their -REV2 in CRYSTAL23), STO-3G, STO-6G. 3 — the Hamiltonian and the SCF: DFT with the functional
    («PBE0», «B3LYP», «HSE06»; the GGA ones «PBEXC», «PBESOLXC»; with «-D3» — Grimme's D3, for the names of its list)
    and END (Hartree–Fock: no DFT block); SHRINK IS ISP — the Monkhorst–Pack net of k points and the Gilat net, TOLINTEG
    (the truncation of the bielectronic integrals; the default 6 6 6 6 12, here stricter 7 7 7 7 14), TOLDEE (the SCF to
    10⁻ⁿ hartree; CRYSTAL raises it to 7 for OPTGEOM and 9 for FREQCALC by itself), MAXCYCLE, FMIXING (the mixing of the
    Fock matrix, %) and END — checked against the manual of CRYSTAL23. Real inputs (CRYSTAL17 1.0.2) are written this
    way: «BASISSET / POB-DZVP», «DFT / PBE0-D3 / END», «SHRINK / 8 16», «TOLINTEG / 14 14 14 14 24», «EXTPRESS /
    0.0000220929» (0.65 GPa). TOPOND (Gatti, in the program properties, input .d3, with the wave function .f9 of the
    run; the TOPOND14 manual, the same keywords in CRYSTAL17 and CRYSTAL23, whose manual sends to it): TOPO, then TRHO —
    the topology of ρ: IAUTO −2 (the automatic search of all the critical points around a seed point); IEXT 1 (the
    extended properties: G, K, V, ELF — what the table shows), ICRIT 0 (all kinds), IBPAT 0 (no bond paths), IPRINT 0,
    NSTEP 100 (the steps of the search), NNB 30 (the neighbours listed), RMAX 100 (the cluster), TH 100 (how far the
    (3,−1) points are looked for — read from the next line); the seed IFRA 0, at the origin (Cartesian). The record is
    that of real runs (CRYSTAL14): «TRHO / -2 / 1,0,0,0,100,30,100. / 100. / 0,0.0,0.0,0.0», then END — TOPO is the last
    of a run.
§2 ALGORITHM
    crystal_input(crystal, task, options): the crystal of the file (its first part if disordered) in the setting
    CRYSTAL takes for its number (space_groups.find(number=…) — origin choice 2, hexagonal axes, b-unique monoclinic
    cell 1; crystal_setting.settings finds the matrix to it when the file is in another one, P 21/n → P 21/c), the
    atoms of the asymmetric unit (a site equal by an operation of the group to one before it is dropped — some CIFs list
    the whole cell); when no setting is found — the whole cell in P 1 (correct, but without the savings of the
    symmetry). The k net: IS = ⌈K / shortest edge⌉ (K = 40 Å, 8 for 5 Å; at most 16), ISP = 2 IS, unless given.
§4 SPECIFICATION
    TASKS — the tasks (the Russian names of the window → the keyword); FUNCTIONALS, BASES; Options(functional='PBE0-D3',
    basis='POB-TZVP', pressure=0 GPa, shrink=0 (automatic), toldee=8, tolinteg='7 7 7 7 14', maxcycle=200 (of the
    geometry), scf_cycles=200, fmixing=30); crystal_input(crystal, task, options) -> text; ValueError for an element the
    basis set has not, for a pressure with a task without the cell; topond_input() -> text; geometry(crystal) ->
    (number, parameters, [(Z, x, y, z)]) — the block 1 data; shrink(crystal) -> (IS, ISP); au_pressure(gpa).
§7 TESTS
    tests/sextant/test_crystal_inputs.py — NaCl (F m -3 m: one parameter, two atoms), benzoic acid P 21/n → P 21/c, a
    sodium formate (C 2/c, a b c β), a pressure, the tasks; the text read back by crystal_out's rules."""

from dataclasses import dataclass
from math import ceil

from azimuth.i18n import tr

GPA_PER_AU = 29421.02648438959
TASKS = {'Энергия': '', 'Оптимизация атомов': 'ATOMONLY', 'Оптимизация с ячейкой': 'FULLOPTG',
         'Упругие константы': 'ELASTCON', 'Частоты (точка Γ)': 'FREQCALC'}
# 2026-11-18 (the manual of CRYSTAL23, read: the standalone keywords of the DFT block — PBEXC and PBESOLXC for the GGA
# ones, PBE0, B3LYP, HSE06 for the hybrids; «-D3» after a name of the D3 list: BLYP, PBE, B97, B3LYP, PBE0, PW1PW, M06,
# HSE06, HSEsol, LC-wPBE — not PBEsol)
FUNCTIONALS = {'PBE0-D3': 'PBE0 + D3', 'PBE0': 'PBE0', 'B3LYP-D3': 'B3LYP + D3', 'B3LYP': 'B3LYP',
               'HSE06-D3': 'HSE06 + D3', 'HSE06': 'HSE06', 'PBE-D3': 'PBE + D3', 'PBEXC': 'PBE', 'PBESOLXC': 'PBEsol',
               'HF': 'Хартри — Фок'}
# the labels of BASISSET in CRYSTAL23: CUSTOM, STO-3G, STO-6G, POB-DZVP, POB-DZVPP, POB-TZVP, POB-DZVP-REV2,
# POB-TZVP-REV2 (MINIX — of the composite HF-3c only)
BASES = {'POB-TZVP': 'pob-TZVP (трёхэкспонентный, H–Br)', 'POB-DZVP': 'pob-DZVP (двухэкспонентный, H–Br)',
         'POB-DZVPP': 'pob-DZVPP (двухэкспонентный с поляризацией, H–Br)',
         'POB-TZVP-REV2': 'pob-TZVP-rev2 (трёхэкспонентный, H–Br, CRYSTAL23)',
         'POB-DZVP-REV2': 'pob-DZVP-rev2 (двухэкспонентный, H–Br, CRYSTAL23)',
         'STO-3G': 'STO-3G (минимальный, для проб)', 'STO-6G': 'STO-6G (минимальный)'}
POB = frozenset({'POB-TZVP', 'POB-DZVP', 'POB-DZVPP', 'POB-TZVP-REV2', 'POB-DZVP-REV2'})
POB_LAST = 35  # Br: the pob basis sets are made for H–Br
SHRINK_LENGTH = 40.0  # Å: IS × the shortest edge of the cell
TOPOND = 'TOPO\nTRHO\n-2\n1,0,0,0,100,30,100.\n100.\n0,0.0,0.0,0.0\nEND\n'


@dataclass
class Options:
    functional: str = 'PBE0-D3'
    basis: str = 'POB-TZVP'
    pressure: float = 0.0  # GPa (EXTPRESS of OPTGEOM with the cell)
    shrink: int = 0  # 0 — automatic
    toldee: int = 8
    tolinteg: str = '7 7 7 7 14'
    maxcycle: int = 200
    scf_cycles: int = 200
    fmixing: int = 30


def au_pressure(gpa):
    return float(gpa) / GPA_PER_AU


def _standard(crystal):
    """The crystal in the setting CRYSTAL takes for its number, or None."""
    from modules.compass.chemistry import crystal_setting as cs
    from modules.compass.chemistry import space_groups

    own = cs.identify(crystal.operations)
    if own is None:
        return None
    target = space_groups.find(number=own['number'])
    if target is None:
        return None
    if own['hall'] == target['hall']:
        return crystal
    try:
        for entry, m, _cell in cs.settings(crystal):
            if entry['hall'] == target['hall']:
                return cs.transform(crystal, m)
    except ValueError:
        return None
    return None


def _asymmetric(crystal):
    """The sites, a site equal by an operation to one kept before dropped."""
    from modules.compass.chemistry import crystal as cr

    kept, images = [], []
    for site in crystal.sites:
        point = (site.x % 1.0, site.y % 1.0, site.z % 1.0)
        if any(cr._separation(crystal.cell, point, other) < 0.05 for other in images):
            continue
        kept.append(site)
        for op in crystal.operations:
            images.append(cr._wrap(cr._apply(op, (site.x, site.y, site.z))))
    return kept


def _parameters(number, cell):
    if number >= 195:
        return (cell.a,)
    if number >= 75:  # tetragonal, trigonal (hexagonal axes), hexagonal
        return cell.a, cell.c
    if number >= 16:
        return cell.a, cell.b, cell.c
    if number >= 3:  # monoclinic: the angle of the unique axis
        odd = max(((abs(v - 90.0), v) for v in (cell.alpha, cell.beta, cell.gamma)))[1]
        return cell.a, cell.b, cell.c, odd
    return cell.a, cell.b, cell.c, cell.alpha, cell.beta, cell.gamma


def geometry(crystal):
    """(space group number, the lattice parameters, [(Z, x, y, z)]) of block 1."""
    from azimuth.core import Z
    from modules.compass.chemistry import crystal as cr

    whole = cr.main_part(crystal)
    standard = _standard(whole)
    if standard is not None:
        from modules.compass.chemistry import crystal_setting as cs

        entry = cs.identify(standard.operations)
        number = entry['number'] if entry else 1
        sites = _asymmetric(standard)
        atoms = [(Z.get(s.symbol, 0), s.x, s.y, s.z) for s in sites]
        if number > 1 and all(z for z, *_ in atoms):
            return number, _parameters(number, standard.cell), atoms
    cell = whole.cell
    atoms = [(Z.get(symbol, 0), x, y, z) for symbol, x, y, z, _label in cr.unit_cell(whole)]
    return 1, (cell.a, cell.b, cell.c, cell.alpha, cell.beta, cell.gamma), atoms


def shrink(crystal, given=0):
    if given:
        return int(given), 2 * int(given)
    cell = crystal.cell
    shortest = min(cell.a, cell.b, cell.c)
    n = max(1, min(16, ceil(SHRINK_LENGTH / shortest)))
    return n, 2 * n


def _title(crystal):
    text = ''.join(ch if 32 <= ord(ch) < 127 else '_' for ch in (crystal.title or 'Azimuth'))
    return (text.strip() or 'Azimuth')[:72]


def crystal_input(crystal, task='Энергия', options=None):
    o = options or Options()
    if task not in TASKS:
        raise ValueError(tr('CRYSTAL: задача {} не поддерживается.').format(task))
    if o.functional not in FUNCTIONALS:
        raise ValueError(tr('CRYSTAL: функционал {} не поддерживается.').format(o.functional))
    if o.basis not in BASES:
        raise ValueError(tr('CRYSTAL: базис {} не поддерживается.').format(o.basis))
    if o.pressure and TASKS[task] != 'FULLOPTG':
        raise ValueError(tr('CRYSTAL: давление задаётся только для оптимизации с ячейкой.'))
    number, parameters, atoms = geometry(crystal)
    if any(z == 0 for z, *_ in atoms):
        raise ValueError(tr('CRYSTAL: в кристалле есть атомы без элемента.'))
    if o.basis in POB:
        from azimuth.core import SYMBOLS

        heavy = sorted({SYMBOLS[z - 1] for z, *_ in atoms if z > POB_LAST})
        if heavy:
            raise ValueError(tr('CRYSTAL: базисы pob-* сделаны для H–Br, а здесь {}. Выберите STO-3G или STO-6G либо '
                                'впишите свой базис в файл.').format(', '.join(heavy)))
    lines = [_title(crystal), 'CRYSTAL', '0 0 0', str(number), ' '.join(f'{p:.8f}' for p in parameters),
             str(len(atoms))]
    lines += [f'{z:<4d} {x:16.10f} {y:16.10f} {zz:16.10f}' for z, x, y, zz in atoms]
    run = TASKS[task]
    if run in ('ATOMONLY', 'FULLOPTG'):
        lines += ['OPTGEOM', run]
        if o.pressure:
            lines += ['EXTPRESS', f'{au_pressure(o.pressure):.12f}']
        lines += ['MAXCYCLE', str(int(o.maxcycle)), 'END']
    elif run == 'ELASTCON':
        lines += ['ELASTCON', 'END']
    elif run == 'FREQCALC':
        lines += ['FREQCALC', 'INTENS', 'END']
    lines += ['BASISSET', o.basis]
    if o.functional != 'HF':
        lines += ['DFT', o.functional, 'END']
    is_, isp = shrink(crystal, o.shrink)
    toldee = max(int(o.toldee), 10) if run in ('ELASTCON', 'FREQCALC') else int(o.toldee)
    lines += ['SHRINK', f'{is_} {isp}', 'TOLINTEG', o.tolinteg, 'TOLDEE', str(toldee), 'MAXCYCLE',
              str(int(o.scf_cycles)), 'FMIXING', str(int(o.fmixing)), 'END']
    return '\n'.join(lines) + '\n'


def topond_input():
    return TOPOND

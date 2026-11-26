"""The elements (SYMBOLS, Z, the dummy atom X), the tables of methods and basis sets of the programs (METHOD_TABLE, BASIS_TABLE, the names of GAMESS and NWChem)
and the basis sets of a calculation: those of an element (its own basis), the relativistic ones of heavy atoms, the
names ORCA knows.

Split off azimuth/core.py (0.222.30); azimuth.core still names them.
"""

import re
from azimuth.i18n import tr


SYMBOLS = (
    'H He Li Be B C N O F Ne Na Mg Al Si P S Cl Ar K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe Cs Ba La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn Fr Ra Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'
).split()
Z = {s: i + 1 for i, s in enumerate(SYMBOLS)}
# a dummy atom (Chemcraft «X»): a point without nucleus, electrons or basis — for Z-matrices, the centre of a
# ring, an axis; not an element (not in SYMBOLS), no bonds, left out of the formula and of the calculations
DUMMY = 'X'
Z[DUMMY] = 0


# methods and basis sets. key -> (family, ORCA, Gaussian, Psi4); None — that program has no such keyword
# (ASSUMPTION: the keyword lists of the ORCA 6, Gaussian 16 and Psi4 1.7 manuals, from memory, 2026-10)
METHOD_TABLE = {
    'HF': ('Хартри — Фок', 'HF', 'HF', 'hf'),
    'MP2': ('Теория возмущений', 'MP2', 'MP2', 'mp2'),
    'BLYP': ('DFT: GGA', 'BLYP', 'BLYP', 'blyp'),
    'BP86': ('DFT: GGA', 'BP86', 'BP86', 'bp86'),
    'PBE': ('DFT: GGA', 'PBE', 'PBEPBE', 'pbe'),
    'TPSS': ('DFT: мета-GGA', 'TPSS', 'TPSSTPSS', 'tpss'),
    'r2SCAN': ('DFT: мета-GGA', 'r2SCAN', None, 'r2scan'),
    'B3LYP': ('DFT: гибридные', 'B3LYP', 'B3LYP', 'b3lyp'),
    'PBE0': ('DFT: гибридные', 'PBE0', 'PBE1PBE', 'pbe0'),
    'TPSSh': ('DFT: гибридные', 'TPSSh', 'TPSSh', 'tpssh'),
    'M06-2X': ('DFT: гибридные', 'M062X', 'M062X', 'm06-2x'),
    'CAM-B3LYP': ('DFT: с разделением по расстоянию', 'CAM-B3LYP', 'CAM-B3LYP', 'cam-b3lyp'),
    'ωB97X-D': ('DFT: с разделением по расстоянию', None, 'wB97XD', 'wb97x-d'),
    'ωB97X-D3': ('DFT: с разделением по расстоянию', 'wB97X-D3', None, None),
    'ωB97X-V': ('DFT: с разделением по расстоянию', 'wB97X-V', None, 'wb97x-v'),
    'B2PLYP': ('DFT: двойные гибридные', 'B2PLYP', 'B2PLYP', 'b2plyp'),
    # coupled clusters — the energy of a geometry found by DFT (no gradients here): canonical CCSD(T), N⁷; DLPNO —
    # ORCA's local approximation of it (with an auxiliary basis, AutoAux), for molecules of tens of atoms
    'CCSD(T)': ('Связанные кластеры', 'CCSD(T)', 'CCSD(T)', 'ccsd(t)'),
    'DLPNO-CCSD(T)': ('Связанные кластеры', 'DLPNO-CCSD(T)', None, None),
    # the semiempirical methods of MOPAC (the fifth column; the other programs have none of them)
    'PM7': ('Полуэмпирические (MOPAC)', None, None, None, 'PM7'),
    'PM6': ('Полуэмпирические (MOPAC)', None, None, None, 'PM6'),
    'PM6-D3H4': ('Полуэмпирические (MOPAC)', None, None, None, 'PM6-D3H4'),
    'AM1': ('Полуэмпирические (MOPAC)', None, None, None, 'AM1'),
    'RM1': ('Полуэмпирические (MOPAC)', None, None, None, 'RM1'),
    'MNDO': ('Полуэмпирические (MOPAC)', None, None, None, 'MNDO'),
}


# key -> (family, ORCA, Gaussian, Psi4, elements as ranges of Z)
_HKR, _HAR, _HCA = ((1, 36),), ((1, 18),), ((1, 20),)


# def2 — all-electron H–Kr, the Stuttgart–Cologne ECP Rb–La (28, 46 core electrons) and Hf–Rn (60); the
# lanthanides Ce–Lu and the elements after Rn are not covered (Weigend, Ahlrichs 2005; the Atlas topic «Тяжёлые
# элементы», quas_atlas/core/relativity.ecp). ORCA, Gaussian 16 and Psi4 take the ECP together with the basis.
_DEF2 = ((1, 57), (72, 86))


BASIS_TABLE = {
    'STO-3G': ('Минимальный', 'STO-3G', 'STO-3G', 'sto-3g', _HAR),
    '6-31G': ('Попла', '6-31G', '6-31G', '6-31g', ((1, 30),)),
    '6-31G*': ('Попла', '6-31G*', '6-31G(d)', '6-31g*', ((1, 30),)),
    '6-31G**': ('Попла', '6-31G**', '6-31G(d,p)', '6-31g**', ((1, 30),)),
    '6-31+G*': ('Попла', '6-31+G*', '6-31+G(d)', '6-31+g*', _HCA),
    '6-311G**': ('Попла', '6-311G**', '6-311G(d,p)', '6-311g**', _HCA),
    'def2-SVP': ('Альрихса (def2)', 'def2-SVP', 'def2SVP', 'def2-svp', _DEF2),
    'def2-TZVP': ('Альрихса (def2)', 'def2-TZVP', 'def2TZVP', 'def2-tzvp', _DEF2),
    'def2-TZVPP': ('Альрихса (def2)', 'def2-TZVPP', 'def2TZVPP', 'def2-tzvpp', _DEF2),
    'def2-QZVP': ('Альрихса (def2)', 'def2-QZVP', 'def2QZVP', 'def2-qzvp', _DEF2),
    'def2-SVPD': ('Альрихса (def2)', 'def2-SVPD', None, 'def2-svpd', _DEF2),
    'def2-TZVPD': ('Альрихса (def2)', 'def2-TZVPD', None, 'def2-tzvpd', _DEF2),
    'cc-pVDZ': ('Даннинга (cc)', 'cc-pVDZ', 'cc-pVDZ', 'cc-pvdz', ((1, 18), (31, 36))),
    'cc-pVTZ': ('Даннинга (cc)', 'cc-pVTZ', 'cc-pVTZ', 'cc-pvtz', ((1, 18), (31, 36))),
    'aug-cc-pVDZ': ('Даннинга (cc)', 'aug-cc-pVDZ', 'Aug-cc-pVDZ', 'aug-cc-pvdz', ((1, 18), (31, 36))),
    'aug-cc-pVTZ': ('Даннинга (cc)', 'aug-cc-pVTZ', 'Aug-cc-pVTZ', 'aug-cc-pvtz', ((1, 18), (31, 36))),
    'pcseg-1': ('Йенсена (pcseg)', 'pcseg-1', None, 'pcseg-1', _HKR),
    'pcseg-2': ('Йенсена (pcseg)', 'pcseg-2', None, 'pcseg-2', _HKR),
    # the extrapolation to the complete basis set of ORCA — two calculations (X = 2/3 or 3/4) and E(CBS) of both:
    # the SCF part by exp(−α√X), the correlation part by X^(−β) (the exponents of Neese and Valeev, JCTC 7, 33,
    # 2011). An energy of a correlated method only (CBS_BASES, Calculation.validate_settings). ORCA 6.0.1 ran
    # «Extrapolate(2/3,cc)» with DLPNO-CCSD(T) (tests/data/orca601/cbs_h2o).
    'CBS(cc-pVDZ/TZ)': ('Экстраполяция к полному базису (CBS)', 'Extrapolate(2/3,cc)', None, None, ((1, 18), (31, 36))),
    'CBS(cc-pVTZ/QZ)': ('Экстраполяция к полному базису (CBS)', 'Extrapolate(3/4,cc)', None, None, ((1, 18), (31, 36))),
    'CBS(aug-cc-pVDZ/TZ)': ('Экстраполяция к полному базису (CBS)', 'Extrapolate(2/3,aug-cc)', None, None,
                            ((1, 18), (31, 36))),
    'CBS(def2-SVP/TZVPP)': ('Экстраполяция к полному базису (CBS)', 'Extrapolate(2/3,def2)', None, None, _DEF2),
    'CBS(def2-TZVPP/QZVPP)': ('Экстраполяция к полному базису (CBS)', 'Extrapolate(3/4,def2)', None, None, _DEF2),
}
CBS_BASES = frozenset(k for k in BASIS_TABLE if k.startswith('CBS('))


PROGRAM_COLUMN = {'orca': 1, 'gaussian': 2, 'psi4': 3, 'mopac': 4}  # MOPAC — methods only, no basis sets


PROGRAM_TITLES = {'orca': 'ORCA', 'gaussian': 'Gaussian', 'psi4': 'Psi4', 'mopac': 'MOPAC', 'gamess': 'GAMESS',
                  'nwchem': 'NWChem'}


# GAMESS (US) and NWChem — their own tables, not columns of the two above: a basis set of GAMESS covers other
# elements than the common ranges, and a name of either may be several keywords. Sources: the GAMESS
# manual, $CONTRL, $BASIS and $DFT groups (gms21sep); the NWChem documentation «Density Functional Theory for
# Molecules» (nwchemgit.github.io); the inputs of cclib (data/GAMESS/basicGAMESS-US2017, data/NWChem/basicNWChem7.0).
# GAMESS: method -> (DFTTYP or '' for HF / MP2, MPLEVL); basis -> ($BASIS keywords, ISPHER=1 needed, element ranges).
GAMESS_METHODS = {
    'HF': ('', 0), 'MP2': ('', 2), 'BLYP': ('BLYP', 0), 'BP86': ('BP86', 0), 'PBE': ('PBE', 0), 'TPSS': ('TPSS', 0),
    'B3LYP': ('B3LYP', 0), 'PBE0': ('PBE0', 0), 'TPSSh': ('TPSSh', 0), 'M06-2X': ('M06-2X', 0),
    'CAM-B3LYP': ('CAMB3LYP', 0), 'ωB97X-D': ('wB97X-D', 0), 'B2PLYP': ('B2PLYP', 0),
}


GAMESS_BASES = {
    'STO-3G': ('GBASIS=STO NGAUSS=3', False, ((1, 54),)),
    '6-31G': ('GBASIS=N31 NGAUSS=6', False, ((1, 36),)),
    '6-31G*': ('GBASIS=N31 NGAUSS=6 NDFUNC=1', False, ((1, 36),)),
    '6-31G**': ('GBASIS=N31 NGAUSS=6 NDFUNC=1 NPFUNC=1', False, ((1, 36),)),
    '6-31+G*': ('GBASIS=N31 NGAUSS=6 NDFUNC=1 DIFFSP=.TRUE.', False, ((1, 36),)),
    '6-311G**': ('GBASIS=N311 NGAUSS=6 NDFUNC=1 NPFUNC=1', False, ((1, 18),)),  # H–Ne, with MC for Na–Ar
    'cc-pVDZ': ('GBASIS=CCD', True, ((1, 18), (20, 20), (31, 36))),
    'cc-pVTZ': ('GBASIS=CCT', True, ((1, 36),)),
    'aug-cc-pVDZ': ('GBASIS=ACCD', True, ((1, 18), (20, 20), (31, 36))),
    'aug-cc-pVTZ': ('GBASIS=ACCT', True, ((1, 36),)),
    'pcseg-1': ('GBASIS=PCseg-1', True, ((1, 36),)),
    'pcseg-2': ('GBASIS=PCseg-2', True, ((1, 36),)),
}


# NWChem: method -> the lines of «xc» ('' — HF «task scf», 'mp2' — «task mp2»); basis -> (library name, spherical)
NWCHEM_METHODS = {
    'HF': '', 'MP2': 'mp2', 'BLYP': 'becke88 lyp', 'BP86': 'becke88 perdew86', 'PBE': 'xpbe96 cpbe96',
    'TPSS': 'xtpss03 ctpss03', 'r2SCAN': 'r2scan', 'B3LYP': 'b3lyp', 'PBE0': 'pbe0', 'TPSSh': 'xctpssh',
    'M06-2X': 'm06-2x', 'CAM-B3LYP': 'xcamb88 1.00 lyp 0.81 vwn_5 0.19 hfexch 1.00\n  cam 0.33 cam_alpha 0.19 cam_beta 0.46',
    'ωB97X-D3': 'wb97x-d3',
}


NWCHEM_BASES = {
    'STO-3G': ('sto-3g', False), '6-31G': ('6-31g', False), '6-31G*': ('6-31g*', False), '6-31G**': ('6-31g**', False),
    '6-31+G*': ('6-31+g*', False), '6-311G**': ('6-311g**', False), 'def2-SVP': ('def2-svp', True),
    'def2-TZVP': ('def2-tzvp', True), 'def2-TZVPP': ('def2-tzvpp', True), 'def2-QZVP': ('def2-qzvp', True),
    'def2-SVPD': ('def2-svpd', True), 'def2-TZVPD': ('def2-tzvpd', True), 'cc-pVDZ': ('cc-pvdz', True),
    'cc-pVTZ': ('cc-pvtz', True), 'aug-cc-pVDZ': ('aug-cc-pvdz', True), 'aug-cc-pVTZ': ('aug-cc-pvtz', True),
    'pcseg-1': ('pcseg-1', True), 'pcseg-2': ('pcseg-2', True),
}


OWN_TABLES = {'gamess': (GAMESS_METHODS, GAMESS_BASES), 'nwchem': (NWCHEM_METHODS, NWCHEM_BASES)}


def program_names(kind, calculation):
    """(method, basis) in the words of the program; ValueError when it has no such method or basis. GAMESS
    and NWChem — the entries of their own tables (OWN_TABLES)."""
    if kind in OWN_TABLES:
        methods, bases = OWN_TABLES[kind]
        if calculation.method not in methods:
            raise ValueError(tr(f'В {PROGRAM_TITLES[kind]} нет метода {calculation.method} — выберите другой.'))
        if calculation.basis not in bases:
            raise ValueError(tr(f'В {PROGRAM_TITLES[kind]} нет базиса {calculation.basis} — выберите другой.'))
        return methods[calculation.method], bases[calculation.basis]
    column = PROGRAM_COLUMN[kind]
    method, basis = METHOD_TABLE[calculation.method][column], BASIS_TABLE[calculation.basis][column]
    if method is None:
        raise ValueError(tr(f'В {PROGRAM_TITLES[kind]} нет метода {calculation.method} — выберите другой.'))
    if basis is None:
        raise ValueError(tr(f'В {PROGRAM_TITLES[kind]} нет базиса {calculation.basis} — выберите другой.'))
    return method, basis


# the basis of an ORCA calculation with a scalar relativistic Hamiltonian (a student's report: «! B3LYP def2-TZVP
# DKH» — ORCA 6 no longer substitutes the relativistic versions, «Relativistic versions of basis sets now have to be
# requested explicitly with the appropriate prefix», manual 6.1, 2.12; the Atlas topic «Тяжёлые элементы» teaches
# «! DKH DKH-def2-TZVP SARC/J», «! ZORA ZORA-def2-TZVP SARC/J», «! X2C x2c-TZVPall»).
# ASSUMPTION: the names of the ORCA 6 basis library, from the manual and the Atlas topic, not run in ORCA here.
RELATIVISTIC_BASES = {
    'DKH': {'def2-SVP': 'DKH-def2-SVP', 'def2-TZVP': 'DKH-def2-TZVP', 'def2-TZVPP': 'DKH-def2-TZVPP',
            'cc-pVDZ': 'cc-pVDZ-DK', 'cc-pVTZ': 'cc-pVTZ-DK', 'aug-cc-pVDZ': 'aug-cc-pVDZ-DK',
            'aug-cc-pVTZ': 'aug-cc-pVTZ-DK'},
    'ZORA': {'def2-SVP': 'ZORA-def2-SVP', 'def2-TZVP': 'ZORA-def2-TZVP', 'def2-TZVPP': 'ZORA-def2-TZVPP'},
    'X2C': {'def2-SVP': 'x2c-SVPall', 'def2-TZVP': 'x2c-TZVPall', 'def2-TZVPP': 'x2c-TZVPPall',
            'def2-QZVP': 'x2c-QZVPall'},
}


def element_bases(text):
    """{symbol: basis key} of «Fe=def2-TZVP; Cl=def2-SVP» (also «Fe: def2-TZVP», commas or new lines between
    the pairs); ValueError for an unknown element or basis set, or an element given twice."""
    found = {}
    for part in re.split(r'[;,\n]+', text or ''):
        part = part.strip()
        if not part:
            continue
        pieces = re.split(r'\s*[=:]\s*|\s+', part, maxsplit=1)
        if len(pieces) != 2 or not pieces[1].strip():
            raise ValueError(tr(f'Базисы по элементам: «{part}» — пишите «элемент=базис», например Fe=def2-TZVP.'))
        symbol, basis = pieces[0].strip(), pieces[1].strip()
        symbol = symbol[:1].upper() + symbol[1:].lower()
        if symbol not in Z or symbol == DUMMY:
            raise ValueError(tr(f'Базисы по элементам: нет элемента «{pieces[0]}».'))
        key = next((k for k in BASIS_TABLE if k.lower() == basis.lower()), None)
        if key is None:
            raise ValueError(tr(f'Базисы по элементам: нет базиса «{basis}» в списке Секстанта.'))
        if key in CBS_BASES:
            raise ValueError(tr(f'Базисы по элементам: «{key}» — экстраполяция, а не базис; её выбирают в поле «Базис».'))
        if symbol in found:
            raise ValueError(tr(f'Базисы по элементам: {symbol} задан дважды.'))
        found[symbol] = key
    return found


def element_basis_text(bases):
    """«Fe=def2-TZVP; Cl=def2-SVP» of {symbol: basis key}, by the atomic numbers."""
    return '; '.join(f'{s}={bases[s]}' for s in sorted(bases, key=Z.get))


# the all-electron SARC basis sets of the heavy atoms with DKH and ZORA (Pantazis, Neese: La–Lu 2009, Ac–Lr
# 2011, Hf–Hg 2008, Tl–Rn 2012): DKH-def2 and ZORA-def2 are defined for H–Kr only, a heavy atom gets its own basis
# (the Atlas: «%basis NewGTO Au "SARC-ZORA-TZVP" end end»); x2c-…all cover H–Rn (Pollak, Weigend 2017) without Ce–Lu.
# also Rb–Ba — the table of the ORCA 6.1 manual (2.7 Basis Sets) gives SARC-DKH-TZVP(P) and SARC-ZORA-TZVP(P)
# for «Rb--Rn, Ac--Lr» (Rb–Xe: Rolfes, Neese, Pantazis 2020); before, Rb–Ba with DKH/ZORA was refused (an ASSUMPTION)
SARC = frozenset(range(37, 87)) | frozenset(range(89, 104))


def _names(numbers):
    symbols = {v: k for k, v in Z.items()}
    return ', '.join(symbols[n] for n in sorted(numbers))


def relativistic_basis(calculation, molecule=None):
    """(the ORCA name of the recontracted basis, the Coulomb-fitting basis or '', the %basis block of the heavy atoms
    or '') for calculation.relativistic; ValueError when the chosen basis has no relativistic version or a heavy atom of
    molecule has no basis for this Hamiltonian."""
    c = calculation
    found = RELATIVISTIC_BASES[c.relativistic].get(c.basis)
    if found is None:
        names = ', '.join(RELATIVISTIC_BASES[c.relativistic])
        raise ValueError(tr(f'У базиса {c.basis} нет релятивистской версии для {c.relativistic}: обычный базис с '
                            f'релятивистским гамильтонианом несогласован. Выберите один из: {names}.'))
    fitting = 'SARC/J' if found.startswith(('DKH-def2', 'ZORA-def2')) else ''
    heavy = sorted({Z[a.symbol] for a in molecule.atoms if Z[a.symbol] > 36}) if molecule else []
    if not heavy:
        return found, fitting, ''
    if c.relativistic == 'X2C':
        bad = [n for n in heavy if n > 86 or 58 <= n <= 71]
        if bad:
            raise ValueError(tr(f'Базисы x2c-…all определены для H–Rn без лантаноидов Ce–Lu, а здесь {_names(bad)}: '
                                'выберите гамильтониан DKH или ZORA — для тяжёлых атомов подставится базис SARC.'))
        return found, fitting, ''
    if not fitting:
        raise ValueError(tr(f'С тяжёлыми атомами ({_names(heavy)}) и {c.relativistic} выберите базис def2: лёгкие атомы '
                            f'получат {c.relativistic}-def2, тяжёлые — всеэлектронный SARC.'))
    bad = [n for n in heavy if n not in SARC]
    if bad:
        raise ValueError(tr(f'Для {_names(bad)} нет всеэлектронного базиса SARC с {c.relativistic}: выберите X2C '
                            '(базисы x2c-…all до Rn) или гамильтониан «Нет» — def2 с псевдопотенциалом.'))
    own = element_bases(c.element_basis)
    symbols = {v: k for k, v in Z.items()}
    block = ''.join(f'  NewGTO {symbols[n]} "SARC-{c.relativistic}-TZVP" end\n' for n in heavy if symbols[n] not in own)
    return found, fitting, block


def orca_bases(calculation, molecule):
    """(the basis of the «!» line, the fitting basis or '', the %basis block or '') of an ORCA input: the own
    basis sets of elements (NewGTO; a heavy element with def2 gets its ECP too — NewECP «def2-ECP», needed when the
    main basis is not def2), the recontracted ones with a relativistic Hamiltonian and SARC for its heavy atoms.
    ASSUMPTION: the ECP name «def2-ECP» of the library of ORCA 6, from its manual, not run here."""
    c = calculation
    _, main = program_names('orca', c)
    fitting, lines = '', ''
    present = {a.symbol for a in molecule.atoms}
    own = {s: k for s, k in element_bases(c.element_basis).items() if s in present}
    for symbol in sorted(own, key=Z.get):
        key = own[symbol]
        name = BASIS_TABLE[key][PROGRAM_COLUMN['orca']]
        if name is None:
            raise ValueError(tr(f'В ORCA нет базиса {key} — выберите другой.'))
        if c.relativistic:
            if Z[symbol] > 36 and c.relativistic != 'X2C':
                raise ValueError(tr(f'С {c.relativistic} тяжёлому атому {symbol} подставляется всеэлектронный SARC — '
                                    f'уберите {symbol} из базисов по элементам.'))
            name = RELATIVISTIC_BASES[c.relativistic].get(key)
            if name is None:
                names = ', '.join(RELATIVISTIC_BASES[c.relativistic])
                raise ValueError(tr(f'У базиса {key} нет релятивистской версии для {c.relativistic}: обычный базис с '
                                    f'релятивистским гамильтонианом несогласован. Выберите один из: {names}.'))
        lines += f'  NewGTO {symbol} "{name}" end\n'
        if not c.relativistic and Z[symbol] > 36 and BASIS_TABLE[key][4] == _DEF2:
            lines += f'  NewECP {symbol} "def2-ECP" end\n'
    if c.relativistic:
        main, fitting, heavy = relativistic_basis(c, molecule)
        lines += heavy
    return main, fitting, '%basis\n' + lines + 'end\n' if lines else ''

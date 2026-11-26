"""Chemistry data and validation; no GUI or external calculation dependencies."""

from dataclasses import dataclass, asdict
from math import isfinite, dist
import json
import re
from azimuth.i18n import tr
from azimuth.core_bases import CBS_BASES, SYMBOLS, element_bases, element_basis_text, _names, orca_bases, BASIS_TABLE, DUMMY, PROGRAM_COLUMN, Z, _DEF2, program_names, METHOD_TABLE, OWN_TABLES  # noqa: F401 — also named from here
from azimuth.core_isotopes import isotope_abundance, isotope_name, isotope_masses, isotope_text, ISOTOPES  # noqa: F401 — also named from here



def without_dummies(molecule):
    """The molecule without its dummy atoms X (bonds renumbered); the same object when it has none."""
    if not any(a.symbol == DUMMY for a in molecule.atoms):
        return molecule
    keep = [k for k, a in enumerate(molecule.atoms) if a.symbol != DUMMY]
    new = {old: n for n, old in enumerate(keep)}
    bonds = None
    if molecule.bonds is not None:
        bonds = tuple((new[i], new[j], o) for i, j, o in molecule.bonds if i in new and j in new)
    return Molecule(molecule.title, tuple(molecule.atoms[k] for k in keep), bonds)


@dataclass(frozen=True)
class Atom:
    symbol: str
    x: float
    y: float
    z: float

    @property
    def position(self):
        return self.x, self.y, self.z


@dataclass(frozen=True)
class Molecule:
    title: str
    atoms: tuple[Atom, ...]
    bonds: tuple[tuple[int, int, int], ...] | None = None

    @property
    def formula(self):
        counts = {}
        for atom in self.atoms:
            if atom.symbol != DUMMY:  # dummy atoms are not in the formula
                counts[atom.symbol] = counts.get(atom.symbol, 0) + 1
        order = (['C', 'H'] + sorted(set(counts) - {'C', 'H'})) if 'C' in counts else sorted(counts)
        return ''.join(s + (str(counts[s]) if counts[s] > 1 else '') for s in order if s in counts)

    def xyz(self):
        return f'{len(self.atoms)}\n{self.title}\n' + ''.join(
            f'{a.symbol:<2} {a.x: .8f} {a.y: .8f} {a.z: .8f}\n' for a in self.atoms
        )

    def electrons(self, charge):
        return sum(Z[a.symbol] for a in self.atoms) - charge

    def validate_state(self, charge, multiplicity):
        if type(charge) is not int or type(multiplicity) is not int:
            raise ValueError(tr('Заряд и мультиплетность должны быть целыми числами.'))
        n = self.electrons(charge)
        if n < 1 or multiplicity < 1 or multiplicity > n + 1:
            raise ValueError(tr('Заряд или мультиплетность несовместимы с числом электронов.'))
        if (n - multiplicity + 1) % 2:
            raise ValueError(tr(f'Электронов: {n}. Проверьте чётность мультиплетности ({multiplicity}).'))


MAX_ATOMS = 2000  # atoms of one structure (was 500); the searches below are by cells, not over all pairs


def near_pairs(positions, cutoff, strict=False):
    """The pairs (j, i), j < i, closer than cutoff (≤ cutoff; < with strict), ordered by i and then j — as
    the loop over all pairs gave them, but through cubic cells of the cutoff size: O(n) for a structure of usual
    density instead of n²/2 distances (2000 atoms: 2 million)."""
    if cutoff <= 0 or len(positions) < 2:
        return []
    size = cutoff
    cells = {}
    for i, p in enumerate(positions):
        cells.setdefault((int(p[0] // size), int(p[1] // size), int(p[2] // size)), []).append(i)
    found = []
    for i, p in enumerate(positions):
        cx, cy, cz = int(p[0] // size), int(p[1] // size), int(p[2] // size)
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for j in cells.get((cx + dx, cy + dy, cz + dz), ()):
                        if j < i:
                            d = dist(p, positions[j])
                            if d < cutoff or (not strict and d == cutoff):
                                found.append((j, i))
    found.sort(key=lambda pair: (pair[1], pair[0]))
    return found


def xyz_symbol(text):
    """The element of an XYZ line as programs write it: «C», «c», «CL», an atomic number «6», a label
    «C12» or «Cl3»; None when it is not an element."""
    if text in Z:
        return text
    if text.isdigit():
        n = int(text)
        return SYMBOLS[n - 1] if 1 <= n <= len(SYMBOLS) and SYMBOLS[n - 1] != 'X' else None
    m = re.fullmatch(r'([A-Za-z]{1,2})\d*', text)
    if not m:
        return None
    letters = m.group(1)
    for cand in (letters.capitalize(), letters[0].upper()) if m.group(0) != letters else (letters.capitalize(),):
        if cand in Z:
            return cand
    return None


def read_xyz(text):
    if not isinstance(text, str):
        raise ValueError(tr('Координаты XYZ должны быть текстом.'))
    lines = text.strip().splitlines()
    if len(lines) < 3:
        raise ValueError(tr('XYZ: нужны число атомов, строка комментария и координаты.'))
    try:
        count = int(lines[0])
    except ValueError:
        raise ValueError(tr('Первая строка XYZ должна содержать число атомов.')) from None
    if not 1 <= count <= MAX_ATOMS:
        raise ValueError(tr(f'В этой версии поддерживается от 1 до {MAX_ATOMS} атомов.'))
    if len(lines) < count + 2:  # a cut file is said as such (was «open a single frame»)
        raise ValueError(tr(f'В XYZ указано {count} атомов, а строк координат только {len(lines) - 2}: файл обрезан?'))
    if len(lines) != count + 2:
        raise ValueError(
            tr(f'В XYZ указано {count} атомов, найдено строк координат: {len(lines) - 2}. Откройте один кадр.')
        )
    atoms = []
    for i, line in enumerate(lines[2:], 3):
        fields = line.split()
        symbol = xyz_symbol(fields[0]) if fields else None
        # extended XYZ — columns after the three coordinates (charges, forces) are ignored
        if len(fields) < 4 or symbol is None:
            raise ValueError(tr(f'Строка {i}: ожидается символ элемента и три координаты в Å.'))
        try:
            xyz = tuple(float(v.replace('D', 'E').replace('d', 'e')) for v in fields[1:4])  # also Fortran 1.0D+00
        except ValueError:
            raise ValueError(tr(f'Строка {i}: координаты должны быть числами с точкой.')) from None
        if not all(isfinite(v) and abs(v) < 100000 for v in xyz):
            raise ValueError(tr(f'Строка {i}: недопустимые координаты.'))
        atoms.append(Atom(symbol, *xyz))
    if near_pairs([a.position for a in atoms], 0.1, strict=True):
        raise ValueError(tr('Два атома расположены ближе 0,1 Å. Проверьте геометрию.'))
    return Molecule(lines[1].strip() or tr('Молекула'), tuple(atoms))


CC_METHODS = frozenset(('CCSD(T)', 'DLPNO-CCSD(T)'))  # the energy only
XTB_ORCA = 'GFN2-xTB'  # the method «! XTB2» of ORCA: no basis set, the program xtb behind it
CBS_METHODS = frozenset(('MP2', 'CCSD(T)', 'DLPNO-CCSD(T)'))  # a basis of CBS_BASES: the correlation energy extrapolated
WAVEFUNCTION = ('HF', 'MP2', 'CCSD(T)', 'DLPNO-CCSD(T)')  # no grid of DFT, the reference of the SCF is HF
# a D3(BJ) / D4 correction is added only to functionals without their own dispersion and with parameters for it
DISPERSION_METHODS = frozenset(('BLYP', 'BP86', 'PBE', 'TPSS', 'r2SCAN', 'B3LYP', 'PBE0', 'TPSSh', 'CAM-B3LYP', 'B2PLYP'))
# the dispersion of a new calculation: D3(BJ) — the owner, 2026-11-22 (the defaults of teaching: B3LYP-D3(BJ)/def2-SVP).
# One place for the window of Sextant (modules/sextant/workspace.py) and a calculation sent without it
# (azimuth/headless.py): kept in the window alone till 0.222.26, the two gave different numbers for one molecule
DEFAULT_DISPERSION = 'D3BJ'


def default_dispersion(method):
    """DEFAULT_DISPERSION for a method with parameters of it, else '' (HF, MP2, ωB97X-D, the semiempirical ones)."""
    return DEFAULT_DISPERSION if method in DISPERSION_METHODS else ''
METHODS = tuple(METHOD_TABLE)
BASES = tuple(BASIS_TABLE)


def methods_for(kind):
    """Method keys the program knows; xtb and CREST: none (GFN2-xTB is its own method)."""
    if kind in OWN_TABLES:
        return tuple(k for k in METHOD_TABLE if k in OWN_TABLES[kind][0])
    column = PROGRAM_COLUMN.get(kind)
    return tuple(k for k, row in METHOD_TABLE.items() if column and len(row) > column and row[column]) if column else ()


def bases_for(kind):
    if kind == 'mopac':  # a minimal basis of Slater functions is part of each method
        return ()
    if kind in OWN_TABLES:
        return tuple(k for k in BASIS_TABLE if k in OWN_TABLES[kind][1])
    column = PROGRAM_COLUMN.get(kind)
    return tuple(k for k, row in BASIS_TABLE.items() if column and row[column]) if column else ()


TASKS = {
    'Энергия': '',
    'Оптимизация': 'Opt',
    'Оптимизация + частоты': 'Opt Freq',
    # the frequencies (and the thermochemistry) at the given geometry — after an optimization made elsewhere
    'Частоты и термохимия': 'Freq',
    # a transition state and its frequencies (one imaginary) — the switch «ts» as a task of its own
    'Переходное состояние + частоты': 'Opt Freq',
    'Спектр UV-Vis (TD-DFT)': '',  # the %tddft block (TDDFT_STATES excited states)
    'ЯМР (экранирование)': 'NMR',
    'Путь реакции (NEB-CI)': 'NEB-CI',  # ORCA only; the end structure: end.xyz
    # the intrinsic reaction coordinate from a transition state down to both minima (ORCA only; the block %irc: irc_block)
    'Путь от переходного состояния (IRC)': 'IRC',
    # the geometry of an excited state (the root «root» of TD-DFT; ORCA %tddft iroot, Gaussian TD(Root=…) Opt)
    'Оптимизация возбуждённого состояния (TD-DFT)': 'Opt',
    # a relaxed scan — the coordinate chosen among the constraints of Compass goes from its value to the end
    # value in equal steps, everything else optimized at every point (ORCA %geom Scan, Gaussian Opt=ModRedundant «S»)
    'Скан ППЭ с релаксацией': 'Opt',
    # three single points at the geometry — N, N + 1 and N − 1 electrons — as a queue of Sextant; then the condensed
    # Fukui functions and the dual descriptor (modules/spectrum/analysis/fukui.py). ORCA only: the orbitals of the three
    'Функции Фукуи (N, N+1, N−1)': '',
    # the charge decomposition analysis of Dapprich — Frenking — three single points at the geometry (the
    # complex, its fragment 1 — the atoms chosen —, fragment 2 — the rest) as a queue; then Multiwfn 16
    # (modules/spectrum/wavefunction/multiwfn_cda.py). ORCA only: the files of the orbitals of the three
    'Донорно-акцепторная связь CDA (комплекс и фрагменты)': '',
    # the interaction energy of two molecules with the counterpoise correction — five single points as a queue
    # (modules/sextant/interaction.py). ORCA only: the ghost atoms
    'Энергия взаимодействия с BSSE (две молекулы)': '',
}
FUKUI_TASK = 'Функции Фукуи (N, N+1, N−1)'
CDA_TASK = 'Донорно-акцепторная связь CDA (комплекс и фрагменты)'
INTERACTION_TASK = 'Энергия взаимодействия с BSSE (две молекулы)'
FREQ_TASK = 'Частоты и термохимия'
TS_TASK = 'Переходное состояние + частоты'
TDDFT_TASK = 'Спектр UV-Vis (TD-DFT)'
EXCITED_OPT_TASK = 'Оптимизация возбуждённого состояния (TD-DFT)'
TDDFT_TASKS = (TDDFT_TASK, EXCITED_OPT_TASK)
# scalar relativistic Hamiltonians (ORCA keywords; Gaussian knows DKH2 only) and help for a hard SCF
RELATIVISTIC = {'': 'Нет', 'DKH': 'DKH2 (Дуглас — Кролл — Хесс)', 'ZORA': 'ZORA', 'X2C': 'X2C'}
SLOW_CONV = {'': 'Обычная', 'SlowConv': 'Трудная (SlowConv)', 'VerySlowConv': 'Очень трудная (VerySlowConv)'}
TDDFT_MODES = {'': 'Как в программе', 'tda': 'TDA (Тамм — Данков)', 'full': 'Полное TD-DFT (RPA)'}
NEB_TASK = 'Путь реакции (NEB-CI)'
# what GFN2-xTB through ORCA is offered for: a quick path and its ends (the frequencies and the rest — the program
# xtb itself, or DFT)
XTB_ORCA_TASKS = ('Энергия', 'Оптимизация', NEB_TASK)
IRC_TASK = 'Путь от переходного состояния (IRC)'
SCAN_TASK = 'Скан ППЭ с релаксацией'
SCAN_LIMITS = {'B': (0.3, 10.0), 'A': (1.0, 179.0), 'D': (-360.0, 360.0)}  # Å, °, °: the end value of a scan
SCAN_UNITS = {'B': 'Å', 'A': '°', 'D': '°'}
GUESS_FILE = 'start-orbitals.gbw'  # the copy of the orbitals to start from, in the job folder (MORead)
TDDFT_STATES = 10
# convergence of the SCF and population analyses (names shown in «Дополнительные настройки…»)
SCF_LEVELS = {'normal': 'Обычная', 'tight': 'Строгая (Tight)', 'verytight': 'Очень строгая (VeryTight)'}
POPULATIONS = {'mulliken': 'Малликен (по умолчанию)', 'hirshfeld': 'Хиршфельд', 'nbo': 'NBO (нужна программа NBO)'}
# empirical dispersion: key -> ORCA keyword (the other programs: modules/sextant/inputs.py)
DISPERSIONS = {'': '', 'D3BJ': 'D3BJ', 'D3ZERO': 'D3ZERO', 'D4': 'D4'}  # + D3 with zero damping, «D3(0)»
SOLVENT_MODELS = ('cpcm', 'smd')  # SMD — for solvation free energies (ORCA, Gaussian)
# implicit solvent; key -> (name shown, ORCA CPCM, Gaussian SCRF, xtb ALPB, Psi4 PCMSolver);
# None: the program (its model) has no such solvent
SOLVENTS = {
    '': ('Газовая фаза', None, None, None, None),
    'water': ('Вода', 'Water', 'Water', 'water', 'Water'),
    'methanol': ('Метанол', 'Methanol', 'Methanol', 'methanol', 'Methanol'),
    'ethanol': ('Этанол', 'Ethanol', 'Ethanol', None, 'Ethanol'),
    'acetonitrile': ('Ацетонитрил', 'Acetonitrile', 'Acetonitrile', 'acetonitrile', 'Acetonitrile'),
    'dmso': ('Диметилсульфоксид', 'DMSO', 'DiMethylSulfoxide', 'dmso', 'Dimethylsulfoxide'),
    'acetone': ('Ацетон', 'Acetone', 'Acetone', 'acetone', 'Acetone'),
    'chloroform': ('Хлороформ', 'Chloroform', 'Chloroform', 'chcl3', 'Chloroform'),
    'dichloromethane': ('Дихлорметан', 'CH2Cl2', 'Dichloromethane', 'ch2cl2', 'Methylenechloride'),
    'thf': ('Тетрагидрофуран', 'THF', 'TetraHydroFuran', 'thf', 'Tetrahydrofurane'),
    'toluene': ('Толуол', 'Toluene', 'Toluene', 'toluene', 'Toluene'),
    'benzene': ('Бензол', 'Benzene', 'Benzene', 'benzene', 'Benzene'),
    'hexane': ('Гексан', 'Hexane', 'n-Hexane', 'hexane', None),
}


@dataclass(frozen=True)
class Calculation:
    method: str = 'B3LYP'
    basis: str = 'def2-SVP'
    task: str = 'Оптимизация + частоты'
    charge: int = 0
    multiplicity: int = 1
    cores: int = 2
    memory_mb: int = 1000
    solvent: str = ''  # a key of SOLVENTS ('' = gas phase); older projects have neither field
    dispersion: str = ''  # a key of DISPERSIONS
    # settings for advanced users («Дополнительные настройки…»); the defaults give the files of 0.47.0
    scf: str = 'tight'  # a key of SCF_LEVELS
    grid: str = ''  # '' — the program's DFT grid, 'fine' — a finer one
    no_ri: bool = False  # switch off RI / RIJCOSX / density fitting
    ts: bool = False  # an optimization to a transition state (a saddle point)
    opt_conv: str = 'normal'  # 'normal' or 'tight' convergence of an optimization
    max_cycles: int = 100  # 0 — the program's limit; 100 by default, changeable
    calc_hessian: bool = False  # the exact Hessian at the start of an optimization
    population: str = 'mulliken'  # a key of POPULATIONS
    orbitals: bool = False  # print the orbitals and the basis into the output (Spectrum reads them)
    states: int = TDDFT_STATES  # TD-DFT excited states
    temperature: float = 298.15  # K, thermochemistry
    pressure: float = 1.0  # atm, thermochemistry
    extra: str = ''  # keywords added to the input as they are
    rijcosx: bool = False  # ORCA RIJCOSX (RI for Coulomb, COSX for exchange); def2/J for a basis outside def2
    title: str = ''  # the name of the calculation (first line of the file, name of its files); '' — auto_title
    # a relativistic Hamiltonian, a hard SCF, AutoAux, numerical
    # frequencies, the TD-DFT approximation, triplets and the root followed by an excited-state optimization
    relativistic: str = ''  # a key of RELATIVISTIC
    slow_conv: str = ''  # a key of SLOW_CONV
    auto_aux: bool = False  # ORCA: auxiliary basis sets made from the orbital basis
    num_freq: bool = False  # numerical frequencies (ORCA NumFreq, Gaussian Freq=Numer)
    tddft_mode: str = ''  # a key of TDDFT_MODES
    triplets: bool = False  # TD-DFT: the triplet states too
    root: int = 1  # the excited state of EXCITED_OPT_TASK
    raman: bool = False  # Raman activities with the frequencies (ORCA: NumFreq and %elprop Polar 1)
    couplings: bool = False  # NMR spin-spin couplings too (ORCA %eprnmr … { shift, ssall })
    # the solvation model (SMD — ORCA %cpcm smd, Gaussian SCRF=SMD; the other programs: their own model) and
    # the stability analysis of the wavefunction of an energy (ORCA %scf STABPerform, Gaussian Stable=Opt)
    solvent_model: str = 'cpcm'
    stability: bool = False
    # a relaxed scan (SCAN_TASK): the scan_index-th bond, angle or dihedral among the constraints (the atoms
    # frozen in Compass do not count), from its value in the geometry to scan_end (Å or °) in scan_steps points
    scan_index: int = 0
    scan_end: float = 0.0
    scan_steps: int = 10
    # the second coordinate of a two-dimensional scan (ORCA): its index among the constraints (-1 — none),
    # its end and points; ORCA scans it inside every point of the first one
    scan2_index: int = -1
    scan2_end: float = 0.0
    scan2_steps: int = 5
    xtb_method: str = ''  # '' — GFN2-xTB, 'gfnff' — the force field GFN-FF (xtb --gfnff)
    # the start from the orbitals of an earlier calculation — the path of its .gbw (ORCA MORead); the job
    # folder gets a copy named GUESS_FILE
    guess: str = ''
    nto: bool = False  # the natural transition orbitals of the TD-DFT states (ORCA %tddft DoNTO)
    # CDA_TASK — the atoms of fragment 1 (the donor; «1-4, 7», 1-based), its charge and multiplicity; fragment
    # 2 is the rest, its charge the charge of the complex minus cda_charge
    cda_atoms: str = ''
    cda_charge: int = 0
    cda_mult1: int = 1
    cda_mult2: int = 1
    # own basis sets of some elements, «Fe=def2-TZVP; Cl=def2-SVP» (element_bases); the others take basis
    element_basis: str = ''
    # isotopes of some atoms, «3 H 2.014102; 7 C 13.003355» (1-based numbers, the element they were set on,
    # the mass in u — isotope_masses); ORCA takes them as «M = …» in the coordinates
    isotopes: str = ''

    def validate_settings(self):
        if self.method not in METHODS or self.basis not in BASES or self.task not in TASKS:
            raise ValueError(tr('Метод, базис или задача не поддерживаются этой версией.'))
        if self.solvent_model not in SOLVENT_MODELS or type(self.stability) is not bool:
            raise ValueError(tr('Модель растворителя или анализ устойчивости заданы неверно.'))
        if not (type(self.solvent) is str and self.solvent in SOLVENTS and type(self.dispersion) is str and self.dispersion in DISPERSIONS):
            raise ValueError(tr('Растворитель или дисперсионная поправка не поддерживаются этой версией.'))
        if self.dispersion and self.method not in DISPERSION_METHODS:
            raise ValueError(
                tr(f'Поправку D3(BJ)/D4 к {self.method} здесь не добавить (HF, MP2 или своя дисперсия, нет параметров) — выберите «нет».')
            )
        if self.task in TDDFT_TASKS and self.method == 'MP2':
            raise ValueError(tr('TD-DFT для MP2 не считается — выберите HF или функционал DFT.'))
        if self.method in CC_METHODS and self.task != 'Энергия':
            raise ValueError(tr('CCSD(T) здесь считает только энергию (без градиентов): оптимизируйте геометрию '
                                'функционалом DFT, затем посчитайте на ней «Энергию» этим методом.'))
        if self.basis in CBS_BASES and self.method != XTB_ORCA:  # GFN2-xTB has no basis set at all
            if self.method not in CBS_METHODS or self.task != 'Энергия':
                raise ValueError(tr('Экстраполяция к полному базису (CBS) — для «Энергии» методами MP2, CCSD(T) и '
                                    'DLPNO-CCSD(T): геометрию и частоты считайте функционалом DFT в обычном базисе.'))
            if self.element_basis.strip() or self.relativistic:
                raise ValueError(tr('С экстраполяцией к полному базису (CBS) свои базисы элементов и релятивистский '
                                    'гамильтониан здесь не сочетаются — уберите их.'))
        self.validate_advanced()
        if type(self.cores) is not int or not 1 <= self.cores <= 128:
            raise ValueError(tr('Число процессов должно быть от 1 до 128.'))
        if type(self.memory_mb) is not int or not 100 <= self.memory_mb <= 1000000:
            raise ValueError(tr('Память на процесс должна быть от 100 до 1 000 000 МБ.'))
        if (
            type(self.charge) is not int
            or type(self.multiplicity) is not int
            or not 1 <= self.multiplicity <= 30
            or not -20 <= self.charge <= 20
        ):
            raise ValueError(tr('Недопустимые заряд или мультиплетность.'))

    def validate_advanced(self):
        """The settings of «Дополнительные настройки…»."""
        number = lambda v: type(v) in (int, float) and v == v  # noqa: E731  (not a bool, not NaN)
        if self.scf not in SCF_LEVELS or self.grid not in ('', 'fine') or self.opt_conv not in ('normal', 'tight'):
            raise ValueError(tr('Сходимость SCF, сетка или сходимость оптимизации не поддерживаются этой версией.'))
        if any(type(v) is not bool for v in (self.no_ri, self.ts, self.calc_hessian, self.orbitals, self.rijcosx)):
            raise ValueError(tr('Повреждены дополнительные настройки расчёта.'))
        if self.population not in POPULATIONS:
            raise ValueError(tr('Такой анализ заселённостей не поддерживается этой версией.'))
        if type(self.max_cycles) is not int or not 0 <= self.max_cycles <= 2000:
            raise ValueError(tr('Число циклов оптимизации — от 0 (как в программе) до 2000.'))
        if type(self.states) is not int or not 1 <= self.states <= 100:
            raise ValueError(tr('Число возбуждённых состояний — от 1 до 100.'))
        if not number(self.temperature) or not 1 <= self.temperature <= 5000:
            raise ValueError(tr('Температура — от 1 до 5000 K.'))
        if not number(self.pressure) or not 0.001 <= self.pressure <= 1000:
            raise ValueError(tr('Давление — от 0,001 до 1000 атм.'))
        if type(self.extra) is not str or len(self.extra) > 2000 or any(ord(ch) < 32 and ch not in '\n\t' for ch in self.extra):
            raise ValueError(tr('Строка ключевых слов — обычный текст не длиннее 2000 знаков.'))
        if self.relativistic not in RELATIVISTIC or self.slow_conv not in SLOW_CONV or self.tddft_mode not in TDDFT_MODES:
            raise ValueError(tr('Релятивистская поправка, сходимость SCF или вариант TD-DFT не поддерживаются этой версией.'))
        if any(type(v) is not bool for v in (self.auto_aux, self.num_freq, self.triplets, self.raman)):
            raise ValueError(tr('Повреждены дополнительные настройки расчёта.'))
        if type(self.root) is not int or not 1 <= self.root <= self.states:
            raise ValueError(tr('Оптимизируемое возбуждённое состояние — от 1 до числа состояний TD-DFT.'))
        if self.task == EXCITED_OPT_TASK and self.triplets:
            raise ValueError(tr('Оптимизация возбуждённого состояния здесь — только синглеты: снимите «Триплеты».'))
        if type(self.scan_index) is not int or self.scan_index < 0 or not number(self.scan_end) \
                or type(self.scan_steps) is not int or not 2 <= self.scan_steps <= 100:
            raise ValueError(tr('Скан: от 2 до 100 точек, конечное значение — число.'))
        if type(self.nto) is not bool:
            raise ValueError(tr('Повреждены дополнительные настройки расчёта.'))
        if type(self.cda_atoms) is not str or len(self.cda_atoms) > 2000 or type(self.cda_charge) is not int or any(
                type(m) is not int or not 1 <= m <= 11 for m in (self.cda_mult1, self.cda_mult2)):
            raise ValueError(tr('CDA: фрагмент — номера атомов, заряд — целое число, мультиплетность — от 1 до 11.'))
        if type(self.guess) is not str or len(self.guess) > 4096 or self.guess and (
                not self.guess.lower().endswith('.gbw') or any(ord(ch) < 32 for ch in self.guess)):
            raise ValueError(tr('Начальные орбитали — файл .gbw прошлого расчёта ORCA.'))
        if type(self.element_basis) is not str or len(self.element_basis) > 2000:
            raise ValueError(tr('Повреждены дополнительные настройки расчёта.'))
        element_bases(self.element_basis)

    def basis_of(self, symbol):
        """The basis key of an element — its own (element_basis) or the basis of the calculation."""
        return element_bases(self.element_basis).get(symbol, self.basis)

    def thermo_changed(self):
        return abs(self.temperature - 298.15) > 1e-9 or abs(self.pressure - 1.0) > 1e-12

    @property
    def is_ts(self):
        """A transition state is searched — the switch, or the task «Переходное состояние + частоты»."""
        return self.ts and self.task != SCAN_TASK or self.task == TS_TASK  # a scan is a series of minima

    def validate(self, molecule):
        self.validate_settings()
        if not molecule.atoms:
            raise ValueError(tr('Добавьте атомы перед созданием входного файла.'))
        molecule.validate_state(self.charge, self.multiplicity)
        if self.method == XTB_ORCA:  # no basis set to check the elements against (orca_xtb_input, the program xtb)
            return
        # heavier than Kr — def2 with its ECP up to Rn; with DKH, ZORA, X2C — the all-electron bases of
        # relativistic_basis (a student's report: «Элементы тяжелее Kr не поддерживаются вообще», for Y, Bi, Ac, Ln)
        # each element by its own basis (basis_of)
        symbols = {v: k for k, v in Z.items()}
        elements = sorted({a.symbol for a in molecule.atoms}, key=Z.get)
        if self.relativistic:  # the heavy atoms: relativistic_basis of orca_input, or the refusal of the other programs
            elements = [s for s in elements if Z[s] <= 36]
        else:
            outside = [Z[s] for s in elements if (58 <= Z[s] <= 71 or Z[s] > 86) and BASIS_TABLE[self.basis_of(s)][4] == _DEF2]
            if outside:
                raise ValueError(tr(f'В def2 нет псевдопотенциалов для {_names(outside)} (лантаноиды Ce–Lu и элементы '
                                    'тяжелее Rn): выберите в ORCA гамильтониан DKH или ZORA — подставится '
                                    'всеэлектронный базис SARC.'))
        for symbol in elements:
            key = self.basis_of(symbol)
            ranges = BASIS_TABLE[key][4]  # the elements every basis set is defined for
            if not any(lo <= Z[symbol] <= hi for lo, hi in ranges):
                where = ', '.join(f'{symbols[lo]}–{symbols[hi]}' for lo, hi in ranges)
                raise ValueError(tr(f'Базис {key} в этой версии — только для элементов {where}.'))


CONSTRAINT_KINDS = {'C': 1, 'B': 2, 'A': 3, 'D': 4}  # atom (Cartesian), bond, angle, dihedral: number of atoms


def coordinate_value(molecule, kind, atoms):
    """The value of an internal coordinate of molecule — a bond in Å, an angle or a dihedral in degrees (the
    dihedral from −180 to 180, the sign of IUPAC: clockwise seen along the middle bond is positive)."""
    from math import acos, atan2, degrees, sqrt

    p = [molecule.atoms[i].position for i in atoms]

    def sub(a, b):
        return tuple(x - y for x, y in zip(a, b))

    def dot(a, b):
        return sum(x * y for x, y in zip(a, b))

    def cross(a, b):
        return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

    if kind == 'B':
        return sqrt(dot(sub(p[0], p[1]), sub(p[0], p[1])))
    if kind == 'A':
        u, v = sub(p[0], p[1]), sub(p[2], p[1])
        cosine = dot(u, v) / sqrt(dot(u, u) * dot(v, v))
        return degrees(acos(max(-1.0, min(1.0, cosine))))
    if kind == 'D':
        b1, b2, b3 = sub(p[1], p[0]), sub(p[2], p[1]), sub(p[3], p[2])
        n1, n2 = cross(b1, b2), cross(b2, b3)
        m = cross(n1, tuple(x / sqrt(dot(b2, b2)) for x in b2))
        return -degrees(atan2(dot(m, n2), dot(n1, n2)))  # = atan2((n1 × n2)·b2/|b2|, n1·n2)
    raise ValueError(tr('Сканировать можно длину связи, угол или двугранный угол.'))


def scan_coordinates(constraints):
    """The bonds, angles and dihedrals among the constraints — what a scan can follow — [(kind, atoms)]."""
    return [(kind, tuple(atoms)) for kind, atoms in constraints or () if kind in SCAN_LIMITS]


def scan_plan(molecule, calculation, constraints):
    """(kind, atoms 0-based, start, end, steps, the other constraints) of a relaxed scan; ValueError with what
    to do when there is nothing to scan or the end is out of range."""
    fixed = validate_constraints(constraints, len(molecule.atoms))
    coordinates = scan_coordinates(fixed)
    if not coordinates:
        raise ValueError(tr('Для скана задайте в Компасе координату: «Ограничения оптимизации» — длину, угол или '
                            'двугранный угол (2–4 выделенных атома).'))
    c = calculation
    if not 0 <= c.scan_index < len(coordinates):
        raise ValueError(tr('Выберите координату скана заново: ограничения в Компасе изменились.'))
    kind, atoms = coordinates[c.scan_index]
    low, high = SCAN_LIMITS[kind]
    if not low <= c.scan_end <= high:
        raise ValueError(tr(f'Конец скана — от {low:g} до {high:g} {SCAN_UNITS[kind]}.'))
    start = coordinate_value(molecule, kind, atoms)
    if abs(c.scan_end - start) < (0.01 if kind == 'B' else 0.5):
        raise ValueError(tr('Конец скана совпадает с началом — задайте другое значение.'))
    second = scan_plan2(molecule, c, fixed)
    rest = tuple(item for item in fixed if item != (kind, atoms) and (second is None or item != (second[0], second[1])))
    return kind, atoms, start, float(c.scan_end), c.scan_steps, rest


def scan_plan2(molecule, calculation, constraints):
    """(kind, atoms, start, end, steps) of the second coordinate of a two-dimensional scan, or None."""
    c = calculation
    if getattr(c, 'scan2_index', -1) < 0:
        return None
    coordinates = scan_coordinates(validate_constraints(constraints, len(molecule.atoms)))
    if not 0 <= c.scan2_index < len(coordinates):
        raise ValueError(tr('Выберите вторую координату скана заново: ограничения в Компасе изменились.'))
    if c.scan2_index == c.scan_index:
        raise ValueError(tr('Вторая координата скана совпадает с первой — выберите другую или «Нет».'))
    kind, atoms = coordinates[c.scan2_index]
    low, high = SCAN_LIMITS[kind]
    if not low <= c.scan2_end <= high:
        raise ValueError(tr(f'Конец второй координаты — от {low:g} до {high:g} {SCAN_UNITS[kind]}.'))
    start = coordinate_value(molecule, kind, atoms)
    if abs(c.scan2_end - start) < (0.01 if kind == 'B' else 0.5):
        raise ValueError(tr('Конец второй координаты совпадает с началом — задайте другое значение.'))
    return kind, atoms, start, float(c.scan2_end), c.scan2_steps


# the name of a calculation ------------------------------------------------------------------------------
XTB_KINDS = ('xtb', 'crest')
_NAME_MAP = str.maketrans({'ω': 'w', 'Ω': 'W', '*': 's', '(': '', ')': '', ',': '', ' ': '_', '/': '-'})
_RU = dict(zip('абвгдеёжзийклмнопрстуфхцчшщъыьэюя',
               ['a', 'b', 'v', 'g', 'd', 'e', 'e', 'zh', 'z', 'i', 'y', 'k', 'l', 'm', 'n', 'o', 'p', 'r', 's', 't', 'u',
                'f', 'kh', 'ts', 'ch', 'sh', 'shch', '', 'y', '', 'e', 'yu', 'ya']))
_RU_MAP = str.maketrans({**_RU, **{k.upper(): v.capitalize() for k, v in _RU.items()}})


def auto_title(molecule, calculation, kind='orca'):
    """formula_method_basis[_solvent], e.g. «H2O_B3LYP_def2-SVP_water»; xtb and CREST: formula_GFN2-xTB[_solvent]."""
    c = calculation
    parts = [molecule.formula or 'molecule']
    parts += ['GFN2-xTB'] if kind in XTB_KINDS else [c.method] if kind == 'mopac' or c.method == XTB_ORCA \
        else [c.method, c.basis]  # no basis
    if c.solvent:
        parts.append(c.solvent)
    return '_'.join(p for p in parts if p)


def calculation_title(molecule, calculation, kind='orca'):
    """The title the user wrote (one line, at most 120 characters) or auto_title."""
    text = ' '.join((calculation.title or '').split())[:120]
    return text or auto_title(molecule, calculation, kind)


def safe_name(text, limit=80):
    """A file name from a title: Latin letters, digits and . _ + - (Russian letters transliterated, ω → w, * → s,
    spaces → _); '' when nothing is left."""
    out = re.sub(r'[^A-Za-z0-9._+-]', '_', (text or '').translate(_NAME_MAP).translate(_RU_MAP))
    out = re.sub(r'_+', '_', out).strip('._-')
    return out[:limit].rstrip('._-')


def file_base(molecule, calculation, kind='orca'):
    """The name of the files of a calculation without extension: safe_name(calculation_title) or «input»."""
    return safe_name(calculation_title(molecule, calculation, kind)) or 'input'


def validate_constraints(constraints, count):
    """[(kind, (i, ...)), ...] with 0-based atom indices; returns a tuple of tuples."""
    out = []
    for item in constraints or ():
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError(tr('Повреждённый список ограничений.'))
        kind, atoms = item
        atoms = tuple(atoms) if isinstance(atoms, (list, tuple)) else None
        if (
            kind not in CONSTRAINT_KINDS
            or atoms is None
            or len(atoms) != CONSTRAINT_KINDS[kind]
            or any(type(i) is not int or not 0 <= i < count for i in atoms)
            or len(set(atoms)) != len(atoms)
        ):
            raise ValueError(tr('Повреждённый список ограничений.'))
        out.append((kind, atoms))
    return tuple(out)


def irc_block(c):
    """%irc of ORCA: both directions from the transition state, the Hessian computed at the start (numerically for the
    correlated wave-function methods and with «Численные частоты»), MaxIter — steps in each direction (the limit of cycles)."""
    hessian = 'calc_numfreq' if c.num_freq or c.method in WAVEFUNCTION and c.method != 'HF' else 'calc_anfreq'
    rows = '  Direction both\n' + f'  InitHess {hessian}\n'
    rows += f'  MaxIter {c.max_cycles}\n' if c.max_cycles else ''
    return '%irc\n' + rows + 'end\n'


def neb_block(molecule, end, images):
    """%neb of ORCA: the product in end.xyz (the same atoms in the same order), the number of images."""
    if end is None:
        raise ValueError(tr('Для пути реакции задайте конечную структуру: Компас → «Правка → Путь между структурами…».'))
    if [a.symbol for a in end.atoms] != [a.symbol for a in molecule.atoms]:
        raise ValueError(tr('Конечная структура пути — другие атомы или другой порядок; постройте путь заново.'))
    if type(images) is not int or not 1 <= images <= 50:
        raise ValueError(tr('Промежуточных структур — от 1 до 50.'))
    return f'%neb\n  neb_end_xyzfile "end.xyz"\n  nimages {images}\nend\n'


META_GGA = frozenset(('TPSS', 'r2SCAN', 'TPSSh', 'M06-2X'))  # meta-GGA and meta-hybrid functionals


def orca_xtb_input(molecule, c, constraints, neb_end, neb_images):
    """«! XTB2 …»: GFN2-xTB of the program xtb driven by ORCA — no basis set, no RI, no grid; the solvent is ALPB
    of xtb. ORCA 6.0.1 ran «! XTB2 NEB-CI» with XTBEXE set (tests/data/orca601/xtb_neb_hcn)."""
    if c.task not in XTB_ORCA_TASKS:
        raise ValueError(tr('GFN2-xTB в ORCA здесь — для «Энергии», «Оптимизации» и «Пути реакции (NEB-CI)»: '
                            'частоты и остальное считайте программой xtb или функционалом DFT.'))
    if c.element_basis.strip() or c.relativistic or c.ts:
        raise ValueError(tr('С GFN2-xTB свои базисы элементов, релятивистский гамильтониан и поиск переходного '
                            'состояния здесь не сочетаются — уберите их.'))
    if c.solvent and SOLVENTS[c.solvent][3] is None:
        raise ValueError(tr(f'Для растворителя «{SOLVENTS[c.solvent][0]}» в модели ALPB метода GFN2-xTB нет '
                            'параметров — выберите другой растворитель или газовую фазу.'))
    task = TASKS[c.task]
    optimizing = 'Opt' in task
    solvent = f'ALPB({SOLVENTS[c.solvent][3]})' if c.solvent else ''
    keywords = ' '.join(filter(None, ('XTB2', task, 'TightOpt' if optimizing and c.opt_conv == 'tight' else '', solvent)))
    rows = ''
    if optimizing:
        fixed = validate_constraints(constraints, len(molecule.atoms))
        if fixed:
            rows += '  Constraints\n' + ''.join(f'    {{ {kind} {" ".join(map(str, atoms))} C }}\n' for kind, atoms in fixed) + '  end\n'
        if c.max_cycles:
            rows += f'  MaxIter {c.max_cycles}\n'
    blocks = '%geom\n' + rows + 'end\n' if rows else ''
    if c.task == NEB_TASK:
        blocks += neb_block(molecule, neb_end, neb_images)
    if c.extra.strip():
        blocks += c.extra.strip() + '\n'
    return (
        f'# {calculation_title(molecule, c)}\n! {keywords}\n'
        f'%pal nprocs {c.cores} end\n%maxcore {c.memory_mb}\n' + (blocks and '\n' + blocks) + '\n'
        f'* xyz {c.charge} {c.multiplicity}\n' + coordinate_lines(molecule, c) + '\n*\n'
    )


def orca_input(molecule, calculation, constraints=(), neb_end=None, neb_images=8):
    calculation.validate(molecule)
    c = calculation
    if c.method == XTB_ORCA:
        return orca_xtb_input(molecule, c, constraints, neb_end, neb_images)
    if c.task == EXCITED_OPT_TASK and c.method in META_GGA:
        # ORCA 6.0.1 stops at once — «Meta-GGA functionals can only be used in combination with the
        # excited-state gradient if the functional is defined via the %method block» (the user's run, TPSSh)
        raise ValueError(tr(f'ORCA не считает градиенты возбуждённых состояний с мета-GGA функционалом {c.method} — '
                            'для «Оптимизации возбуждённого состояния» возьмите CAM-B3LYP, PBE0 или B3LYP.'))
    solvent = f'CPCM({SOLVENTS[c.solvent][1]})' if c.solvent else ''
    method, _ = program_names('orca', c)
    if c.task == EXCITED_OPT_TASK and method == 'B3LYP' and c.dispersion in ('', 'D3BJ'):
        # ORCA 6.1.1 has no native third derivative of B88 exchange for the TD-DFT gradient (code 55);
        # its LibXC B3LYP is the same functional (VWN5) — formaldehyde S1, 7 cycles each: ORCA 6.0.1 native −114.218015,
        # LibXC −114.218016, ORCA 6.1.1 LibXC −114.218020 hartree; with D3BJ ORCA 6.0.1 took the B3LYP parameters
        # (s8 1.9889, a1 0.3981, a2 4.4211). D3(0) and D4 under the LibXC name were not run: those keep «B3LYP».
        method = 'LibXC(B3LYP)'
    # the RI-MP2 part of a double hybrid and the pair approximations of DLPNO need an auxiliary basis
    aux = 'AutoAux' if c.method in ('B2PLYP', 'DLPNO-CCSD(T)') or c.auto_aux else ''
    # the recontracted basis, and the SARC/J fitting basis of DKH- and ZORA-def2; SARC for the heavy
    # atoms; the own basis sets of elements
    basis, fitting, heavy = orca_bases(c, molecule)
    fitting = '' if aux == 'AutoAux' or c.no_ri else fitting
    task = TASKS[c.task]
    optimizing = 'Opt' in task
    if c.is_ts and optimizing:  # 0.48.0; or the task «Переходное состояние + частоты»
        task = task.replace('Opt', 'OptTS', 1)
    if (c.num_freq or c.raman) and 'Freq' in task:  # 0.73.0; ORCA 6.0.1 prints Raman only with NumFreq
        task = re.sub(r'\bFreq\b', 'NumFreq', task)
    scf = {'normal': 'NormalSCF', 'tight': 'TightSCF', 'verytight': 'VeryTightSCF'}[c.scf]
    more = [
        'TightOpt' if optimizing and c.opt_conv == 'tight' else '',
        'DefGrid3' if c.grid == 'fine' and c.method not in WAVEFUNCTION else '',
        'NoRI' if c.no_ri else '',
        # RIJCOSX asked for (it is ORCA's default for hybrid DFT anyway); a basis outside def2 gets the universal
        # Coulomb-fitting basis def2/J (a def2 basis gets it from ORCA by itself)
        'RIJCOSX' if c.rijcosx and not c.no_ri else '',
        'def2/J' if c.rijcosx and not c.no_ri and not c.basis.lower().startswith('def2') and aux != 'AutoAux' else '',
        fitting,
        'NBO' if c.population == 'nbo' else '',
        c.relativistic,  # DKH, ZORA, X2C
        c.slow_conv,
    ]
    more.append('MORead' if c.guess else '')  # the orbitals of an earlier calculation as the start
    couplings = c.couplings and task == 'NMR'
    if couplings:  # the form verified on ORCA 6.0.1 (tests/data/nmr_j) — %eprnmr after the geometry, no «NMR»
        task = ''
    keywords = ' '.join(filter(None, (method, DISPERSIONS[c.dispersion], basis, aux, task, scf, solvent, *more)))
    # frozen atoms and internal coordinates, only for an optimization; MaxIter, Calc_Hess
    rows = ''
    if c.task == SCAN_TASK:  # the scanned coordinate in Scan, the others stay constraints
        second = scan_plan2(molecule, c, constraints)  # a two-dimensional scan, verified on ORCA 6.0.1
        kind, atoms, start, end, steps, constraints = scan_plan(molecule, c, constraints)
        lines = ''
        for kind, atoms, start, end, steps in ((kind, atoms, start, end, steps),) + ((second,) if second else ()):
            digits = 4 if kind == 'B' else 2
            lines += f'    {kind} {" ".join(map(str, atoms))} = {start:.{digits}f}, {end:.{digits}f}, {steps}\n'
        rows += '  Scan\n' + lines + '  end\n'
    if optimizing:
        fixed = validate_constraints(constraints, len(molecule.atoms))
        if fixed:
            rows += '  Constraints\n' + ''.join(f'    {{ {kind} {" ".join(map(str, atoms))} C }}\n' for kind, atoms in fixed) + '  end\n'
        if c.max_cycles:
            rows += f'  MaxIter {c.max_cycles}\n'
        if c.calc_hessian or c.is_ts:
            rows += '  Calc_Hess true\n'
    blocks = '%geom\n' + rows + 'end\n' if rows else ''
    blocks += heavy
    if c.task in TDDFT_TASKS:  # 0.37.0; TDA or not, triplets, the root of an excited-state optimization
        rows = f'  nroots {c.states}\n'
        rows += {'tda': '  tda true\n', 'full': '  tda false\n'}.get(c.tddft_mode, '')
        rows += '  triplets true\n' if c.triplets else ''
        rows += f'  iroot {c.root}\n' if c.task == EXCITED_OPT_TASK else ''
        rows += '  DoNTO true\n' if c.nto and c.task == TDDFT_TASK else ''  # NTOStates empty — every state
        blocks += '%tddft\n' + rows + 'end\n'
    output = ('  Print[P_Hirshfeld] 1\n' if c.population == 'hirshfeld' else '') + (
        '  Print[P_MOs] 1\n  Print[P_Basis] 2\n' if c.orbitals else ''
    )
    if output:
        blocks += '%output\n' + output + 'end\n'
    if 'Freq' in task and c.thermo_changed():
        blocks += f'%freq\n  Temp {c.temperature:g}\n  Pressure {c.pressure:g}\nend\n'
    if c.raman and 'Freq' in task:  # the polarizability and its derivatives along the modes
        blocks += '%elprop\n  Polar 1\nend\n'
    if c.task == NEB_TASK:
        blocks += neb_block(molecule, neb_end, neb_images)
    if c.task == IRC_TASK:
        blocks += irc_block(c)
    if c.solvent and c.solvent_model == 'smd':  # SMD on the CPCM cavity, the same solvent name
        blocks += f'%cpcm\n  smd true\n  SMDsolvent "{SOLVENTS[c.solvent][1]}"\nend\n'
    if c.stability and c.task == 'Энергия':  # the SCF solution checked (and followed) for instabilities
        blocks += '%scf\n  STABPerform true\nend\n'
    if c.guess:  # the copy in the job folder (runner.prepare)
        blocks += f'%moinp "{GUESS_FILE}"\n'
    if c.extra.strip():  # as written by the user
        blocks += c.extra.strip() + '\n'
    return (
        f'# {calculation_title(molecule, c)}\n! {keywords}\n'
        f'%pal nprocs {c.cores} end\n%maxcore {c.memory_mb}\n' + (blocks and '\n' + blocks) + '\n'
        f'* xyz {c.charge} {c.multiplicity}\n' + coordinate_lines(molecule, c) + '\n*\n'
    ) + (nmr_couplings_block(molecule) if couplings else '')


def coordinate_lines(molecule, c=None):
    """The lines of the coordinates of an ORCA input; an atom with an isotope gets «M = mass»."""
    masses = isotope_masses(getattr(c, 'isotopes', ''), molecule)
    lines = molecule.xyz().splitlines()[2:]
    return '\n'.join(line + (f'  M = {masses[k]:.6f}' if k in masses else '') for k, line in enumerate(lines))


def nmr_couplings_block(molecule):
    """σ and every J of the H, C, F and P of the molecule (ORCA wants the block after the coordinates)."""
    present = [e for e in ('H', 'C', 'F', 'P') if any(a.symbol == e for a in molecule.atoms)]
    return '%eprnmr\n' + ''.join(f'  Nuclei = all {e} {{ shift, ssall }}\n' for e in present) + 'end\n'


def validate_bonds(edges, count):
    if not isinstance(edges, (list, tuple)):
        raise ValueError(tr('Повреждён список связей.'))
    result = []
    seen = set()
    for edge in edges:
        # a project saved by 0.216.x with a delocalized bond of the Mayer orders (1.5) opens — the bond
        # single (the drawing and the files keep whole orders)
        if isinstance(edge, (list, tuple)) and len(edge) == 3 and type(edge[2]) is float and edge[2] in (1.5, 1.0, 2.0, 3.0):
            edge = (edge[0], edge[1], 1 if edge[2] == 1.5 else int(edge[2]))
        if not isinstance(edge, (list, tuple)) or len(edge) != 3 or any(type(v) is not int for v in edge):
            raise ValueError(tr('Повреждена запись связи.'))
        a, b, order = edge
        if a == b or not 0 <= a < count or not 0 <= b < count or order not in (1, 2, 3):
            raise ValueError(tr('Недопустимая связь в проекте.'))
        a, b = sorted((a, b))
        if (a, b) in seen:
            raise ValueError(tr('Повторяющаяся связь в проекте.'))
        seen.add((a, b))
        result.append((a, b, order))
    return tuple(result)


def project_text(molecule, calculation, constraints=(), labels=None):
    calculation.validate_settings()
    data = {
        'format': 'azimuth',  # 0.86.5 (was 'qcc-studio'; both are read)
        'version': 2,
        'xyz': molecule.xyz(),
        'bonds': molecule.bonds,
        'calculation': asdict(calculation),
    }
    if constraints:  # 0.32.0; older versions ignore the key
        data['constraints'] = [[k, list(a)] for k, a in validate_constraints(constraints, len(molecule.atoms))]
    if labels:  # own labels of atoms; older versions ignore the key
        data['labels'] = {str(i): str(t) for i, t in sorted(labels.items()) if 0 <= i < len(molecule.atoms) and t}
    return json.dumps(data, ensure_ascii=False, indent=2)


def project_labels(text):
    """The own labels of atoms stored in a project {index: text} (empty for older projects)."""
    try:
        data = json.loads(text)
        count = len(read_project(text)[0].atoms)
        raw = data.get('labels') or {}
        if not isinstance(raw, dict):
            raise TypeError
        return {int(k): str(v)[:40] for k, v in raw.items() if 0 <= int(k) < count and str(v)}
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        raise ValueError(tr('Повреждённый файл проекта «Азимута».')) from exc


def project_constraints(text):
    """The optimization constraints stored in a project (empty for older projects)."""
    try:
        data = json.loads(text)
        mol, _ = read_project(text)
        return validate_constraints(data.get('constraints') or (), len(mol.atoms))
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(tr('Повреждённый файл проекта «Азимута».')) from exc


def read_project(text):
    try:
        data = json.loads(text)
        if not isinstance(data, dict) or data.get('format') not in ('azimuth', 'qcc-studio') or data.get('version') not in (1, 2):
            raise ValueError(tr('Неизвестный формат проекта.'))
        xyz = data['xyz']
        if isinstance(xyz, str) and len(xyz.splitlines()) == 2 and xyz.splitlines()[0] == '0':
            mol = Molecule(xyz.splitlines()[1], (), ())
        else:
            mol = read_xyz(xyz)
        if data.get('bonds') is not None:
            bonds = validate_bonds(data['bonds'], len(mol.atoms))
            mol = Molecule(mol.title, mol.atoms, bonds)
        calc = Calculation(**data['calculation'])
        calc.validate_settings()
        return mol, calc
    except (KeyError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(tr('Повреждённый файл проекта «Азимута».')) from exc


EXAMPLES = {
    'Вода · H₂O': '3\nВода\nO 0 0 0\nH 0.7586 0 0.5043\nH -0.7586 0 0.5043',
    'Аммиак · NH₃': '4\nАммиак\nN 0 0 0.12\nH 0.94 0 -0.25\nH -0.47 0.814 -0.25\nH -0.47 -0.814 -0.25',
    'Метан · CH₄': '5\nМетан\nC 0 0 0\nH 0.63 0.63 0.63\nH -0.63 -0.63 0.63\nH -0.63 0.63 -0.63\nH 0.63 -0.63 -0.63',
}

# Approximate ethane starting geometry for demonstrating rigid fragment edits.
EXAMPLES['Этан · C₂H₆ · перемещение фрагмента'] = (
    '8\nЭтан — учебная начальная геометрия\nC -0.77 0 0\nC 0.77 0 0\nH -1.133 1.028 0\nH -1.133 -0.514 0.890\nH -1.133 -0.514 -0.890\nH 1.133 -1.028 0\nH 1.133 0.514 0.890\nH 1.133 0.514 -0.890'
)

"""The handbook of «Справка → Справочник» (azimuth/handbook_window.py): units and constants, solvents, scaling factors
of frequencies and where to find experimental data — what one looks up while preparing a calculation or reading it.

§1 PURPOSE
    The facts a student needs next to a calculation, each with its source: the units of energy, length and dipole
    moment converted into each other with the constants of CODATA; which solvent each program knows and under what name;
    the scaling factors of harmonic frequencies; the databases of measured spectra, structures and thermochemistry, and
    links to them for the formula of the molecule.
§2 RULES
    1. Nothing is typed twice: the solvents come from the table Sextant writes inputs with (azimuth.core.SOLVENTS,
       modules.sextant.inputs.MOPAC_EPS), the factors from modules/spectrum/analysis/scaling.py (NIST CCCBDB).
    2. The constants are those of CODATA 2018, the values the program computes with
       (physics.nist.gov/cuu/Constants). CODATA 2022 changed none of them in a digit that matters here: the hartree in
       eV in the twelfth (27.211386245981), the bohr radius in the tenth (0.529177210544 Å).
    3. A link is made from a formula only where the site takes one in its address (NIST WebBook, PubChem); the other
       databases are listed with what they hold.
§3 INTERFACE
    CONSTANTS [(name, symbol, value, unit, exact)]; ENERGY {unit: per hartree}; LENGTH {unit: per bohr}; DIPOLE {unit: per
    e·bohr}; convert(kind, value, unit) -> {unit: value} (kind 'energy' | 'length' | 'dipole'; energy also as a
    wavelength 'nm'); solvent_rows() -> [dict]; factor_rows(method=None) -> [dict]; DATABASES [dict];
    formula_links(formula) -> [(title, url)].
§7 TESTS tests/core/test_handbook.py.
"""

import re
from urllib.parse import quote

CODATA = 'CODATA 2018, physics.nist.gov/cuu/Constants'
CODATA_URL = 'https://physics.nist.gov/cuu/Constants/'

# CODATA 2018: the defining constants of the SI (exact) and the measured ones the program uses
C = 299792458.0  # m/s, exact
H = 6.62607015e-34  # J·s, exact
E = 1.602176634e-19  # C, exact
KB = 1.380649e-23  # J/K, exact
NA = 6.02214076e23  # 1/mol, exact
HARTREE_J = 4.3597447222071e-18  # J
BOHR_M = 0.529177210903e-10  # m
ME = 9.1093837015e-31  # kg
DALTON = 1.66053906660e-27  # kg
EPS0 = 8.8541878128e-12  # F/m

CONSTANTS = (
    ('Скорость света в вакууме', 'c', C, 'м/с', True),
    ('Постоянная Планка', 'h', H, 'Дж·с', True),
    ('Приведённая постоянная Планка', 'ħ', H / (2 * 3.141592653589793), 'Дж·с', True),
    ('Элементарный заряд', 'e', E, 'Кл', True),
    ('Постоянная Больцмана', 'k_B', KB, 'Дж/К', True),
    ('Постоянная Авогадро', 'N_A', NA, '1/моль', True),
    ('Универсальная газовая постоянная', 'R', KB * NA, 'Дж/(моль·К)', True),
    ('Постоянная Фарадея', 'F', E * NA, 'Кл/моль', True),
    ('Энергия Хартри', 'E_h', HARTREE_J, 'Дж', False),
    ('Боровский радиус', 'a₀', BOHR_M, 'м', False),
    ('Масса электрона', 'm_e', ME, 'кг', False),
    ('Атомная единица массы (дальтон)', 'u', DALTON, 'кг', False),
    ('Электрическая постоянная', 'ε₀', EPS0, 'Ф/м', False),
)

KJ_MOL = HARTREE_J * NA / 1000  # 2625.4996394799
ENERGY = {  # per hartree
    'Eh': 1.0,
    'эВ': HARTREE_J / E,  # 27.211386245988
    'ккал/моль': KJ_MOL / 4.184,  # the thermochemical calorie
    'кДж/моль': KJ_MOL,
    'см⁻¹': HARTREE_J / (H * C) / 100,  # 219474.6313632
    'К': HARTREE_J / KB,  # the temperature of kT = E
    'ТГц': HARTREE_J / H / 1e12,
}
WAVELENGTH = 'нм'  # of a photon of that energy: λ = 10⁷ / ν̃(см⁻¹)
LENGTH = {'бор': 1.0, 'Å': BOHR_M * 1e10, 'пм': BOHR_M * 1e12, 'нм': BOHR_M * 1e9}
DEBYE_CM = 1e-21 / C  # C·m: 10⁻¹⁸ statC·cm
DIPOLE = {'e·бор': 1.0, 'Д (дебай)': E * BOHR_M / DEBYE_CM, 'Кл·м': E * BOHR_M, 'e·Å': BOHR_M * 1e10}
KINDS = {'energy': ENERGY, 'length': LENGTH, 'dipole': DIPOLE}


def units(kind):
    """The units of a quantity in the order shown; energy with the wavelength of a photon last."""
    found = list(KINDS[kind])
    return found + [WAVELENGTH] if kind == 'energy' else found


def convert(kind, value, unit):
    """{unit: value} of one quantity in every unit of its kind; ValueError for a wavelength that is not positive."""
    table = KINDS[kind]
    value = float(value)
    if kind == 'energy' and unit == WAVELENGTH:
        if value <= 0:
            raise ValueError('Длина волны должна быть больше нуля.')
        base = 1e7 / value / table['см⁻¹']
    else:
        base = value / table[unit]
    found = {name: base * per for name, per in table.items()}
    if kind == 'energy':
        wavenumber = found['см⁻¹']
        found[WAVELENGTH] = 1e7 / wavenumber if wavenumber > 0 else None
    return found


PROGRAM_COLUMNS = (  # (title, how the name is found) for solvent_rows
    ('ORCA (CPCM)', 'orca'), ('Gaussian (SCRF)', 'gaussian'), ('xtb, CREST (ALPB)', 'xtb'),
    ('Psi4 (PCM)', 'psi4'), ('MOPAC (COSMO)', 'mopac'),
)


def solvent_rows():
    """[{'key', 'name', 'epsilon', 'orca', 'gaussian', 'xtb', 'psi4', 'mopac'}] — the solvents of Sextant: the
    dielectric constant (CRC Handbook, 20–25 °C, as MOPAC is given it) and the name each program takes (None — it has no
    such solvent). GAMESS and NWChem: Sextant writes no solvent for them yet."""
    from azimuth.core import SOLVENTS
    from modules.sextant.inputs import MOPAC_EPS, SOLVENT_COLUMN

    rows = []
    for key, entry in SOLVENTS.items():
        if not key:
            continue
        row = {'key': key, 'name': entry[0], 'epsilon': MOPAC_EPS.get(key)}
        for _, kind in PROGRAM_COLUMNS:
            if kind == 'mopac':
                row[kind] = f'EPS={MOPAC_EPS[key]:g}' if key in MOPAC_EPS else None
            else:
                row[kind] = entry[SOLVENT_COLUMN[kind]]
        rows.append(row)
    return rows


def factor_rows(method=None):
    """[{'method', 'basis', 'factor', 'uncertainty'}] of NIST CCCBDB, the methods in the order of the table."""
    from modules.spectrum.analysis import scaling

    return [{'method': m, 'basis': b, 'factor': f, 'uncertainty': u}
            for m, bases in scaling.FACTORS.items() if method in (None, m)
            for b, (f, u) in bases.items()]


FACTOR_SOURCE = 'NIST CCCBDB, «Precomputed vibrational scaling factors»'
FACTOR_URL = 'https://cccbdb.nist.gov/vibscalejustx.asp'

DATABASES = (  # what each holds, read on the site 2026-11-21
    {'name': 'NIST Chemistry WebBook', 'url': 'https://webbook.nist.gov/chemistry/',
     'what': 'ИК-, УФ- и масс-спектры, термохимия (энтальпии образования, теплоёмкости), энергии ионизации — '
             'газовая фаза и растворы'},
    {'name': 'NIST CCCBDB', 'url': 'https://cccbdb.nist.gov/',
     'what': 'малые молекулы в газе: опытные геометрии, частоты колебаний, вращательные постоянные, дипольные '
             'моменты, поляризуемости, энтальпии образования — рядом с рассчитанными разными методами'},
    {'name': 'Active Thermochemical Tables (ATcT)', 'url': 'https://atct.anl.gov/',
     'what': 'согласованные энтальпии и энергии Гиббса образования, энергии связей, в том числе радикалов и '
             'короткоживущих частиц'},
    {'name': 'SDBS (AIST)', 'url': 'https://sdbs.db.aist.go.jp/',
     'what': 'ИК, рамановские, ЯМР ¹H и ¹³C и масс-спектры органических соединений'},
    {'name': 'nmrshiftdb2', 'url': 'https://nmrshiftdb.nmr.uni-koeln.de/',
     'what': 'открытая база ЯМР-спектров органических соединений: химические сдвиги по атомам'},
    {'name': 'NIST Atomic Spectra Database', 'url': 'https://www.nist.gov/pml/atomic-spectra-database',
     'what': 'уровни энергии и линии атомов и ионов: энергии возбуждения и ионизации'},
    {'name': 'Crystallography Open Database (COD)', 'url': 'https://www.crystallography.net/cod/',
     'what': 'открытые кристаллические структуры (CIF); поиск из программы — «Файл → Найти кристалл в COD…»'},
    {'name': 'PubChem', 'url': 'https://pubchem.ncbi.nlm.nih.gov/',
     'what': 'названия, идентификаторы, свойства и ссылки на опытные данные из других баз'},
)


def formula_links(formula):
    """[(title, url)] — the pages of the databases that take a formula in their address."""
    formula = re.sub(r'\s+', '', formula or '')
    if not formula:
        return []
    code = quote(formula)
    return [('NIST Chemistry WebBook', f'https://webbook.nist.gov/cgi/cbook.cgi?Formula={code}&NoIon=on&Units=SI'),
            ('PubChem', f'https://pubchem.ncbi.nlm.nih.gov/#query={code}')]

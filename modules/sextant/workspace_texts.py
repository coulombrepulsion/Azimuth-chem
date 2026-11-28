"""The texts and names of the page of Sextant: the programs, the notes of their input files, the defaults.

Split off modules/sextant/workspace.py (0.222.29); workspace.py and calculation_page.py import what they use.
"""

from modules.sextant import inputs

PROGRAMS = (('orca', 'ORCA'), ('gaussian', 'Gaussian'), ('psi4', 'Psi4'), ('xtb', 'xtb (GFN2-xTB)'),
            ('mopac', 'MOPAC (PM7, PM6, AM1)'), ('gamess', 'GAMESS (US)'), ('nwchem', 'NWChem'))
NAMES = inputs.NAMES
DISPERSION_NAMES = {'': 'нет', 'D3BJ': 'D3(BJ)', 'D3ZERO': 'D3(0)', 'D4': 'D4'}  # D3(0)
# the dispersion of a new window: DEFAULT_DISPERSION of azimuth/core.py (D3(BJ), the owner, 2026-11-22);
# a method without parameters for it (HF, MP2, ωB97X-D…) and xtb switch it off (update_dispersion), a project
# brings its own
TITLES = {'orca': 'Входной файл ORCA', 'gaussian': 'Входной файл Gaussian', 'psi4': 'Входной файл Psi4',
          'xtb': 'Команда и файлы xtb', 'mopac': 'Входной файл MOPAC', 'gamess': 'Входной файл GAMESS',
          'nwchem': 'Входной файл NWChem'}
GAUSSIAN_NOTICE = (
    '%nprocshared — число процессов, %mem — память на все процессы\n# — метод/базис, задача, растворитель '
    '(SCRF), дисперсия\nзатем название, заряд и мультиплетность, геометрия'
)
PSI4_NOTICE = (
    'memory — память на весь расчёт\nmolecule — заряд, мультиплетность и геометрия\nset — базис, тип '
    'волновой функции, сходимость\nпоследние строки — что считать: energy, optimize, frequency'
)
ORCA_NOTICE = (
    '! — метод, базис и задача\n%pal — число процессов\n%maxcore — память на процесс, не общий лимит\n'
    '* xyz — заряд, мультиплетность и геометрия'
)
XTB_NOTICE = (
    '--gfn 2 — метод GFN2-xTB (метод и базис выше не используются)\n--chrg — заряд, --uhf — число '
    'неспаренных электронов (2S)\n--opt — оптимизация, --ohess — оптимизация и частоты\n-P — число процессов'
)
MOPAC_NOTICE = (
    'первая строка — метод (PM7…), заряд (CHARGE=), спин (DOUBLET UHF…), растворитель (EPS=), задача (1SCF — без '
    'оптимизации)\nдве строки — название\nгеометрия: x 1 y 1 z 1 — «1» оптимизировать координату, «0» — нет\n'
    'второе задание с OLDGEO — частоты (FORCE) на оптимизированной геометрии; базиса нет: он часть метода'
)
GAMESS_NOTICE = (
    '$CONTRL — тип волновой функции (RHF/UHF), задача (RUNTYP), заряд, мультиплетность, функционал (DFTTYP)\n'
    '$SYSTEM MWORDS — память на процесс (1 MW = 8 МБ)\n$BASIS — базис; $STATPT — оптимизация\n'
    '$DATA — название, C1 (без симметрии) и атомы: символ, заряд ядра, x y z; запуск — rungms'
)
NWCHEM_NOTICE = (
    'memory total — память на процесс\ngeometry — атомы (без симметрии и переноса); basis — базис из библиотеки\n'
    'dft — функционал (xc), мультиплетность; scf — для HF и MP2\nпоследние строки task — что считать'
)
NOTICES = {'orca': ORCA_NOTICE, 'gaussian': GAUSSIAN_NOTICE, 'psi4': PSI4_NOTICE, 'xtb': XTB_NOTICE, 'mopac': MOPAC_NOTICE,
           'gamess': GAMESS_NOTICE, 'nwchem': NWCHEM_NOTICE}
EDIT_NOTE = ('Файл можно править прямо здесь — перед запуском он проверяется. Расчёт запускается в своей папке внутри '
             'папки расчётов (какая это папка, показывает кнопка с папкой); результат откроется в Компасе или в Спектре.')


def input_help(notice):
    """The text of «?» by the input file: the meaning of its lines, then what the file is and where it runs."""
    from azimuth.i18n import tr

    return tr(notice) + '\n\n' + tr(EDIT_NOTE)


DEFAULT_MOPAC_METHOD = 'PM7'
DEFAULT_METHOD, DEFAULT_BASIS = 'B3LYP', 'def2-SVP'
# the sign of a comment line in the input of each program (Ctrl+/ of the editor of the input)
COMMENT_SIGNS = {'orca': '#', 'gaussian': '!', 'gamess': '!', 'mopac': '*', 'nwchem': '#', 'psi4': '#', 'xtb': '#'}

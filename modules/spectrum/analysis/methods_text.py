"""«Методика расчёта»: the paragraph of the computational details of a result, and the archive of its input files.

§1 PURPOSE
    A report must say enough to repeat the calculation: the program and its version, the method, the basis set or
    the pseudopotentials with the cutoffs, the grid of k-points, the convergence thresholds, the solvent model. All of
    it is in the files of the calculation — here it is read from them and written as sentences. Nothing is added that
    the files do not say: a setting left to the default of the program is not named (the program and its version
    define it), and what was not recognized is listed as it stands in the input, for the author of the report to word.
§2 ALGORITHM
    orca(text of an output): the version («Program Version 6.0.1»), the echo of the input («| 1> ! B3LYP D3BJ …»): each
    word of the «!» lines is put into one of the kinds — method, basis, auxiliary basis, dispersion, approximation
    (RIJCOSX …), solvent (CPCM(water), SMD in %cpcm), task (Opt, Freq, NMR, OptTS, NEB-CI, IRC), thresholds (TightSCF,
    TightOpt, VeryTightSCF …), grid (DefGrid3); the charge and the multiplicity of «* xyz 0 1»; a word of none of the
    kinds goes to «other».
    quantum_espresso(input text of pw.x, output text ''): calculation, ecutwfc and ecutrho, K_POINTS, the smearing,
    conv_thr, forc_conv_thr, press_conv_thr, nspin, tot_charge, input_dft, vdw_corr, the card HUBBARD, the files of
    ATOMIC_SPECIES; of the output — the version and the line «Exchange-correlation=».
    Each returns Details(program, version, items [(name, value)], other [str]); paragraph(details) -> one paragraph
    (Russian, keys of tr).
    archive(folder, target, text): a zip of the input files of a calculation folder — by suffix and name (the inputs,
    the scripts of the run, the pseudopotentials copied beside them, path.json and the like; no outputs, no wave
    functions) — and METHODS.txt with the paragraph; returns the names put in.
§4 SPECIFICATION
    Details (.get(name)); orca(text) -> Details; quantum_espresso(input, output='') -> Details; of_folder(folder) ->
    Details | None (the kind of the calculation by its files); paragraph(details) -> str; inputs_of(folder) -> [Path];
    archive(folder, target, text='') -> [names]. ValueError with a message for the user.
§7 TESTS
    tests/spectrum/test_methods_text.py.
"""

from __future__ import annotations

import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from azimuth.i18n import tr

INPUT_SUFFIXES = ('.inp', '.in', '.gjf', '.com', '.xyz', '.sh', '.bat', '.cif', '.mop', '.nw', '.upf')
INPUT_NAMES = ('path.json', 'elastic.json')
ORCA_TASKS = {'opt': 'оптимизация геометрии', 'freq': 'колебательные частоты', 'numfreq': 'колебательные частоты (численно)',
              'nmr': 'экранирование ЯМР (GIAO)', 'optts': 'поиск переходного состояния', 'neb-ci': 'путь реакции NEB-CI',
              'neb-ts': 'путь реакции NEB-TS', 'irc': 'путь от переходного состояния (IRC)', 'sp': 'энергия',
              'engrad': 'энергия и градиент'}
ORCA_THRESHOLDS = ('loosescf', 'normalscf', 'tightscf', 'verytightscf', 'extremescf', 'looseopt', 'normalopt', 'tightopt',
                   'verytightopt')
ORCA_APPROXIMATIONS = ('rijcosx', 'ri', 'rijk', 'nori', 'ri-mp2', 'nofrozencore', 'frozencore')
ORCA_DISPERSION = ('d3', 'd3bj', 'd3zero', 'd4', 'd2', 'nl', 'scnl')
ORCA_METHODS = ('hf', 'mp2', 'ccsd', 'ccsd(t)', 'dlpno-ccsd(t)', 'dlpno-ccsd', 'b3lyp', 'pbe0', 'pbe', 'bp86', 'blyp', 'tpss',
                'tpssh', 'm062x', 'wb97x-d3', 'wb97x-v', 'wb97x', 'cam-b3lyp', 'b2plyp', 'r2scan', 'r2scan-3c', 'b97-3c',
                'xtb2', 'xtb1', 'hf-3c', 'pbeh-3c', 'dlpno-mp2', 'lda', 'revpbe', 'b97m-v', 'wb97m-v')
# «Exchange-correlation=» of pw.x names the parts of the functional when the files of the species word it differently
QE_FUNCTIONALS = {'SLA PW PBX PBC': 'PBE', 'SLA PW PSX PSC': 'PBEsol', 'SLA PZ NOGX NOGC': 'LDA (PZ)',
                  'SLA PW NOGX NOGC': 'LDA (PW)'}
QE_CALCULATIONS = {'scf': 'энергия (scf)', 'relax': 'оптимизация атомов (relax)',
                   'vc-relax': 'оптимизация атомов и ячейки (vc-relax)', 'nscf': 'несамосогласованный расчёт (nscf)',
                   'bands': 'зонная структура (bands)'}


@dataclass(frozen=True)
class Details:
    program: str
    version: str = ''
    items: tuple = ()
    other: tuple = field(default_factory=tuple)

    def get(self, name, default=''):
        return next((value for key, value in self.items if key == name), default)


def _bases():
    from azimuth import core_bases

    return {str(row[1]).lower() for row in core_bases.BASIS_TABLE.values() if row[1]}


def orca(text):
    echo = re.search(r'INPUT FILE\s*\n=+\s*\n(.*?)\*{4}END OF INPUT\*{4}', text or '', re.S)
    lines = re.findall(r'^\|\s*\d+>\s?(.*)$', echo[1], re.M) if echo else []
    if not lines:
        raise ValueError(tr('В выводе ORCA нет копии входного файла («INPUT FILE»): методику по нему не собрать.'))
    version = re.search(r'Program Version\s+(\S+)', text)
    bases = _bases()
    found = {key: [] for key in ('method', 'basis', 'auxiliary', 'dispersion', 'approximation', 'solvent', 'task',
                                 'threshold', 'grid')}
    other = []
    for line in lines:
        if not line.strip().startswith('!'):
            continue
        for word in line.strip()[1:].split():
            low = word.lower()
            if low in ORCA_METHODS:
                found['method'].append(word)
            elif low in bases or low.startswith('extrapolate('):
                found['basis'].append(word)
            elif low.endswith(('/c', '/j', '/jk')) or low == 'autoaux':
                found['auxiliary'].append(word)
            elif low in ORCA_DISPERSION:
                found['dispersion'].append(word)
            elif low in ORCA_APPROXIMATIONS:
                found['approximation'].append(word)
            elif low.startswith(('cpcm', 'smd', 'alpb', 'cosmo')):
                found['solvent'].append(word)
            elif low in ORCA_TASKS:
                found['task'].append(tr(ORCA_TASKS[low]))
            elif low in ORCA_THRESHOLDS:
                found['threshold'].append(word)
            elif low.startswith('defgrid'):
                found['grid'].append(word)
            else:
                other.append(word)
    body = '\n'.join(lines)
    solvent = re.search(r'smdsolvent\s+"([^"]+)"', body, re.I)
    if re.search(r'smd\s+true', body, re.I):
        found['solvent'] = ['SMD' + (f'({solvent[1]})' if solvent else '')]
    start = re.search(r'^\*\s*(?:xyz|xyzfile|int)\s+(-?\d+)\s+(\d+)', body, re.M | re.I)
    if not found['task']:
        found['task'].append(tr(ORCA_TASKS['sp']))
    items = [(key, (', ' if key == 'task' else ' ').join(found[key])) for key in found]
    items += [('charge', start[1] if start else ''), ('multiplicity', start[2] if start else '')]
    return Details('ORCA', version[1] if version else '', tuple((k, v) for k, v in items if v), tuple(other))


def _namelist(text, key):
    found = re.search(rf'^\s*{re.escape(key)}\s*=\s*([^\n,/]+)', text, re.M | re.I)
    return found[1].strip().strip("'\"") if found else ''


def quantum_espresso(source, output=''):
    if 'ATOMIC_SPECIES' not in (source or ''):
        raise ValueError(tr('Это не входной файл pw.x: в нём нет карты ATOMIC_SPECIES.'))
    version = re.search(r'Program PWSCF v\.(\S+)', output or '')
    functional = re.search(r'Exchange-correlation\s*=\s*(.+)', output or '')
    files = []
    for line in source.split('ATOMIC_SPECIES')[1].splitlines()[1:]:
        parts = line.split()
        if len(parts) != 3 or not parts[2].lower().endswith('.upf'):
            break
        files.append(parts[2])
    grid = re.search(r'K_POINTS\s+\{?\s*automatic\s*\}?\s*\n\s*(\d+)\s+(\d+)\s+(\d+)', source, re.I)
    gamma = re.search(r'K_POINTS\s+\{?\s*gamma', source, re.I)
    calculation = _namelist(source, 'calculation') or 'scf'
    smearing = _namelist(source, 'smearing')
    hubbard = []
    if 'HUBBARD' in source:
        hubbard = [' '.join(line.split()) for line in source.split('HUBBARD')[1].splitlines()[1:]
                   if line.strip().startswith(('U ', 'J ', 'V '))]
    named = ' '.join(functional[1].split()) if functional else ''
    items = [('functional', _namelist(source, 'input_dft') or QE_FUNCTIONALS.get(named, named)),
             ('pseudopotentials', ', '.join(dict.fromkeys(files))),
             ('ecutwfc', _namelist(source, 'ecutwfc')), ('ecutrho', _namelist(source, 'ecutrho')),
             ('kpoints', f'{grid[1]} × {grid[2]} × {grid[3]}' if grid else ('Γ' if gamma else '')),
             ('smearing', f'{smearing}, {_namelist(source, "degauss")} Ry' if smearing else ''),
             ('spin', 'nspin = 2' if _namelist(source, 'nspin') == '2' else ''),
             ('hubbard', '; '.join(hubbard)), ('dispersion', _namelist(source, 'vdw_corr')),
             ('charge', _namelist(source, 'tot_charge')),
             ('task', tr(QE_CALCULATIONS.get(calculation, calculation))),
             ('conv_thr', _namelist(source, 'conv_thr')), ('forc_conv_thr', _namelist(source, 'forc_conv_thr')),
             ('press_conv_thr', _namelist(source, 'press_conv_thr')), ('cell_dofree', _namelist(source, 'cell_dofree'))]
    return Details('Quantum ESPRESSO', version[1] if version else '', tuple((k, v) for k, v in items if v))


def of_folder(folder):
    folder = Path(folder)
    if not folder.is_dir():
        return None
    for path in sorted(folder.glob('*.in')):
        try:
            source = path.read_text(encoding='utf-8', errors='replace')
        except OSError:
            continue
        if 'ATOMIC_SPECIES' in source:
            out = folder / 'pw.out'
            return quantum_espresso(source, out.read_text(encoding='utf-8', errors='replace') if out.is_file() else '')
    for path in sorted(folder.glob('*.out')):
        try:
            return orca(path.read_text(encoding='utf-8', errors='replace'))
        except (OSError, ValueError):
            continue
    return None


def paragraph(found):
    program = found.program + (f' {found.version}' if found.version else '')
    get = found.get
    if found.program == 'Quantum ESPRESSO':
        parts = [tr('Расчёты выполнены в программе {} методом функционала плотности в базисе плоских волн.').format(program)]
        if get('functional'):
            parts.append(tr('Обменно-корреляционный функционал: {}.').format(get('functional')))
        if get('pseudopotentials'):
            parts.append(tr('Псевдопотенциалы: {}.').format(get('pseudopotentials')))
        if get('ecutwfc'):
            parts.append(tr('Энергия обрезания волновых функций {} Ry').format(get('ecutwfc'))
                         + (tr(', плотности {} Ry').format(get('ecutrho')) if get('ecutrho') else '') + '.')
        if get('kpoints'):
            parts.append(tr('Зона Бриллюэна: только точка Γ.') if get('kpoints') == 'Γ'
                         else tr('Сетка k-точек Монкхорста — Пака {}.').format(get('kpoints')))
        if get('smearing'):
            parts.append(tr('Размытие заселённостей: {}.').format(get('smearing')))
        if get('spin'):
            parts.append(tr('Расчёт спин-поляризованный.'))
        if get('hubbard'):
            parts.append(tr('Поправка Хаббарда (DFT+U): {}.').format(get('hubbard')))
        if get('dispersion'):
            parts.append(tr('Дисперсионная поправка: {}.').format(get('dispersion')))
        if get('charge'):
            parts.append(tr('Заряд ячейки: {}.').format(get('charge')))
        parts.append(tr('Тип расчёта: {}.').format(get('task')))
        thresholds = [f'{name} = {get(name)} {unit}' for name, unit in (
            ('conv_thr', 'Ry'), ('forc_conv_thr', 'Ry/bohr'), ('press_conv_thr', tr('кбар'))) if get(name)]
        if thresholds:
            parts.append(tr('Пороги сходимости: {}.').format(', '.join(thresholds)))
        if get('cell_dofree'):
            parts.append(tr('При оптимизации ячейки менялось: {}.').format(get('cell_dofree')))
    else:
        level = '/'.join(v for v in (' '.join(v for v in (get('method'), get('dispersion')) if v), get('basis')) if v)
        parts = [tr('Расчёты выполнены в программе {}.').format(program)]
        if level:
            parts.append(tr('Уровень теории: {}.').format(level))
        if get('auxiliary') or get('approximation'):
            parts.append(tr('Приближения и вспомогательные базисы: {}.').format(
                ' '.join(v for v in (get('approximation'), get('auxiliary')) if v)))
        if get('solvent'):
            parts.append(tr('Растворитель учтён моделью {}.').format(get('solvent')))
        if get('charge'):
            parts.append(tr('Заряд {}, мультиплетность {}.').format(get('charge'), get('multiplicity')))
        parts.append(tr('Тип расчёта: {}.').format(get('task')))
        if get('threshold') or get('grid'):
            parts.append(tr('Критерии сходимости и сетка интегрирования: {}.').format(
                ' '.join(v for v in (get('threshold'), get('grid')) if v)))
        if found.other:
            parts.append(tr('Прочие ключевые слова входного файла: {}.').format(' '.join(found.other)))
    parts.append(tr('Остальные параметры — по умолчанию программы. Входные файлы приложены.'))
    return ' '.join(parts)


def inputs_of(folder):
    folder = Path(folder)
    found = []
    for path in sorted(folder.rglob('*')):
        inside = path.relative_to(folder).parts[:-1]
        if not path.is_file() or 'out' in inside or any(part.endswith('.save') for part in inside):
            continue
        if path.name in INPUT_NAMES or path.suffix.lower() in INPUT_SUFFIXES:
            found.append(path)
    return found


def archive(folder, target, text=''):
    folder = Path(folder)
    files = inputs_of(folder)
    if not files:
        raise ValueError(tr('В папке расчёта нет входных файлов.'))
    with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as bundle:
        for path in files:
            bundle.write(path, path.relative_to(folder).as_posix())
        if text:
            bundle.writestr('METHODS.txt', text + '\n')
    return [path.relative_to(folder).as_posix() for path in files] + (['METHODS.txt'] if text else [])

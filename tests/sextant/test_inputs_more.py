"""Input files of GAMESS (US) and NWChem (modules/sextant/inputs_more.py).

Oracles: the inputs of cclib that GAMESS 2017 and NWChem 7.0 ran (tests/data/inputs_ref; their outputs are in
tests/data/gamess and tests/data/nwchem) — the groups, keywords and their values for the same settings; the manuals'
rules of §2 of the module (ISPHER=1 with cc-pVnZ, HSSEND for an optimization with frequencies, «vdw 4» for D3(BJ));
and the refusals the module promises.
"""

import re
from pathlib import Path

import pytest

from azimuth.core import Calculation, bases_for, methods_for, program_names, read_xyz
from modules.sextant import inputs_more
from modules.sextant.inputs_more import gamess_input, nwchem_input
from tests.fake_programs import program_script

REF = Path(__file__).resolve().parents[1] / 'data' / 'inputs_ref'
WATER = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')


def gamess_keywords(text):
    """{(group, keyword): value} of the $ groups of a GAMESS input, case-insensitive (the $DATA cards left out)."""
    found = {}
    body = text.split('$DATA')[0] if '$DATA' in text.upper() else text
    body = re.split(r'\$data', body, flags=re.I)[0]
    for group, content in re.findall(r'\$(\w+)(.*?)\$END', body, re.S | re.I):
        for key, value in re.findall(r'(\w+)=(\S+)', content):
            found[(group.upper(), key.upper())] = value.upper()
    return found


def nwchem_lines(text):
    return [' '.join(line.split()).lower() for line in text.splitlines() if line.strip()]


def calc(**kw):
    base = dict(method='B3LYP', basis='STO-3G', task='Энергия', cores=1, memory_mb=1000)
    base.update(kw)
    return Calculation(**base)


# -- GAMESS ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize('ref, settings, same', [
    ('dvb_gopt_a.inp', dict(task='Оптимизация'),
     [('CONTRL', 'RUNTYP'), ('CONTRL', 'SCFTYP'), ('CONTRL', 'DFTTYP'), ('BASIS', 'GBASIS'), ('BASIS', 'NGAUSS'),
      ('CONTRL', 'UNITS'), ('STATPT', 'OPTTOL')]),
    ('dvb_un_sp.inp', dict(charge=1, multiplicity=2),
     [('CONTRL', 'RUNTYP'), ('CONTRL', 'SCFTYP'), ('CONTRL', 'DFTTYP'), ('CONTRL', 'MULT'), ('CONTRL', 'ICHARG'),
      ('BASIS', 'GBASIS'), ('BASIS', 'NGAUSS')]),
    ('dvb_ir.inp', dict(task='Частоты и термохимия'),
     [('CONTRL', 'RUNTYP'), ('CONTRL', 'SCFTYP'), ('DFT', 'DFTTYP'), ('BASIS', 'GBASIS'), ('SCF', 'DIRSCF')]),
    ('water_mp2.inp', dict(method='MP2'), [('CONTRL', 'MPLEVL'), ('CONTRL', 'SCFTYP'), ('BASIS', 'GBASIS')]),
    ('dvb_td.inp', dict(task='Спектр UV-Vis (TD-DFT)', basis='6-31G*'),
     [('CONTRL', 'TDDFT'), ('CONTRL', 'DFTTYP'), ('BASIS', 'NDFUNC'), ('CONTRL', 'SCFTYP')]),
])
def test_gamess_writes_what_gamess_ran(ref, settings, same):
    theirs = gamess_keywords((REF / 'gamess' / ref).read_text())
    mine = gamess_keywords(gamess_input(WATER, calc(**settings)))
    for group, key in same:
        expected = theirs.get((group, key)) or theirs.get(('CONTRL', key)) or theirs.get(('DFT', key))
        got = mine.get((group, key)) or mine.get(('CONTRL', key)) or mine.get(('DFT', key))
        assert got == expected, (ref, group, key, got, expected)
    if ref == 'dvb_td.inp':
        assert mine[('TDDFT', 'NSTATE')] == str(calc(**settings).states)


def test_gamess_cards_and_columns():
    text = gamess_input(WATER, calc())
    lines = text.splitlines()
    assert all(line.startswith(' $') or line.startswith('        ') for line in lines[:5])  # a group from column 2
    data = lines.index(' $DATA')
    assert lines[data + 2] == 'C1' and lines[-1] == ' $END'  # C1: the atoms right after it, no blank card
    o = lines[data + 3].split()
    assert o[0] == 'O' and float(o[1]) == 8.0 and [float(v) for v in o[2:]] == [0.0, 0.0, 0.117]
    assert gamess_keywords(text)[('SYSTEM', 'MWORDS')] == '125'  # 1000 MB = 125 MW (8 bytes a word)


def test_gamess_rules_of_the_manual():
    k = gamess_keywords(gamess_input(WATER, calc(basis='cc-pVDZ', task='Оптимизация + частоты', dispersion='D3BJ')))
    assert k[('CONTRL', 'ISPHER')] == '1' and k[('BASIS', 'GBASIS')] == 'CCD'
    assert k[('CONTRL', 'RUNTYP')] == 'OPTIMIZE' and k[('STATPT', 'HSSEND')] == '.TRUE.'
    assert k[('DFT', 'IDCVER')] == '4'
    ts = gamess_keywords(gamess_input(WATER, calc(task='Переходное состояние + частоты')))
    assert ts[('CONTRL', 'RUNTYP')] == 'SADPOINT' and ts[('STATPT', 'HESS')] == 'CALC'
    assert ('CONTRL', 'ISPHER') not in gamess_keywords(gamess_input(WATER, calc(basis='6-31G**')))


@pytest.mark.parametrize('settings, why', [
    (dict(basis='def2-SVP'), 'нет базиса'), (dict(method='r2SCAN'), 'нет метода'),
    (dict(task='ЯМР (экранирование)'), 'ЯМР'), (dict(solvent='water'), 'растворитель'),
    (dict(dispersion='D4'), 'D3'), (dict(method='HF', task='Спектр UV-Vis (TD-DFT)'), 'TD-DFT'),
])
def test_gamess_refuses_what_it_is_not_given(settings, why):
    with pytest.raises(ValueError, match=why):
        gamess_input(WATER, calc(**settings))


def test_gamess_basis_covers_its_own_elements():
    potassium = read_xyz('2\nKH\nH 0 0 0\nK 0 0 2.24')
    assert 'N31' in gamess_input(potassium, calc(basis='6-31G*'))
    with pytest.raises(ValueError, match='K'):
        gamess_input(potassium, calc(basis='6-311G**'))  # N311 of GAMESS: H–Ar (MC for Na–Ar), not K


# -- NWChem ---------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize('ref, settings, lines', [
    ('dvb_gopt_ks.in', dict(task='Оптимизация'), ['* library sto-3g', 'xc b3lyp', 'task dft optimize']),
    ('dvb_gopt_hf.in', dict(method='HF', task='Оптимизация'), ['* library sto-3g', 'task scf optimize']),
    ('dvb_un_sp_ks.in', dict(charge=1, multiplicity=2), ['charge 1', 'mult 2', 'xc b3lyp']),
    ('water_mp2.in', dict(method='MP2'), ['* library sto-3g', 'task mp2 energy']),
    ('dvb_td.in', dict(task='Спектр UV-Vis (TD-DFT)'), ['xc b3lyp', 'task tddft energy']),
    ('dvb_dispersion_bp86_d3zero.in', dict(method='BP86'), ['xc becke88 perdew86']),
])
def test_nwchem_writes_what_nwchem_ran(ref, settings, lines):
    theirs = nwchem_lines((REF / 'nwchem' / ref).read_text())
    mine = nwchem_lines(nwchem_input(WATER, calc(**settings)))
    for line in lines:
        mine_has = line in mine
        if line == 'task mp2 energy':  # «task mp2» of cclib = «task mp2 energy» (energy is the default operation)
            assert 'task mp2' in theirs and mine_has
            continue
        assert line in theirs and mine_has, line
    assert 'geometry units angstroms noautosym nocenter noautoz' in mine and 'end' in mine


def test_nwchem_mp2_freezes_the_core_as_orca_and_psi4_do():
    # NWChem 7.3.0 correlates every electron by default («Frozen core = 0»): water MP2/cc-pVDZ −76.230728; with
    # «freeze atomic» −76.228415434 — ORCA 6.0.1 −76.228415381 (tests/spectrum/test_nwchem.py). HF and DFT have no block
    mine = nwchem_lines(nwchem_input(WATER, calc(method='MP2', basis='cc-pVDZ')))
    k = mine.index('mp2')
    assert mine[k:k + 3] == ['mp2', 'freeze atomic', 'end'] and mine.index('scf') < k < mine.index('task mp2 energy')
    assert 'mp2' not in nwchem_lines(nwchem_input(WATER, calc(method='HF')))
    assert 'freeze atomic' not in nwchem_lines(nwchem_input(WATER, calc()))


def test_nwchem_tddft_block_and_rules():
    text = nwchem_lines(nwchem_input(WATER, calc(task='Спектр UV-Vis (TD-DFT)', states=5)))
    assert text[text.index('tddft') + 1] == 'nroots 5' and 'notriplet' in text
    d3 = nwchem_lines(nwchem_input(WATER, calc(dispersion='D3BJ', basis='def2-SVP', task='Оптимизация + частоты')))
    assert 'disp vdw 4' in d3 and 'basis spherical' in d3 and d3[-2:] == ['task dft optimize', 'task dft freq']
    open_hf = nwchem_lines(nwchem_input(WATER, calc(method='HF', charge=1, multiplicity=2)))
    assert 'uhf' in open_hf and 'nopen 1' in open_hf
    nmr = nwchem_lines(nwchem_input(WATER, calc(task='ЯМР (экранирование)')))
    assert 'shielding' in nmr and nmr[-1] == 'task dft property'


def test_nwchem_ecp_for_heavy_atoms_with_def2():
    iodine = read_xyz('2\nHI\nH 0 0 0\nI 0 0 1.61')
    assert '* library def2-ecp' in nwchem_lines(nwchem_input(iodine, calc(basis='def2-SVP')))
    assert 'ecp' not in nwchem_lines(nwchem_input(WATER, calc(basis='def2-SVP')))


@pytest.mark.parametrize('settings, why', [
    (dict(method='B2PLYP'), 'нет метода'), (dict(solvent='water'), 'растворитель'),
    (dict(task='Путь реакции (NEB-CI)'), 'задачу'), (dict(method='MP2', task='ЯМР (экранирование)'), 'MP2'),
])
def test_nwchem_refuses_what_it_is_not_given(settings, why):
    with pytest.raises(ValueError, match=why):
        nwchem_input(WATER, calc(**settings))


def test_the_tables_name_only_what_the_programs_have():
    assert 'def2-SVP' not in bases_for('gamess') and 'def2-SVP' in bases_for('nwchem')
    assert 'r2SCAN' not in methods_for('gamess') and 'r2SCAN' in methods_for('nwchem')
    assert program_names('gamess', calc(method='CAM-B3LYP'))[0] == ('CAMB3LYP', 0)
    assert inputs_more.file_name('nwchem', WATER, calc()).endswith('.nw')


# -- the runner: the command, the output, the end and the stages (against the outputs of tests/data) ---------------
def test_gamess_and_nwchem_in_the_runner(tmp_path):
    import gzip

    from modules.sextant import runner

    data = Path(__file__).resolve().parents[1] / 'data'
    for kind, name, stages in (('gamess', 'gamess/dvb_gopt_a_gamess-2017.out.gz', {'setup', 'scf', 'opt'}),
                               ('gamess', 'gamess/dvb_ir_gamess-2017.out.gz', {'setup', 'scf', 'freq', 'thermo'}),
                               ('gamess', 'gamess/dvb_td_gamess-2017.out.gz', {'setup', 'excited'}),
                               ('nwchem', 'nwchem/dvb_gopt_ks_nwchem-7.0.out.gz', {'setup', 'scf', 'opt'}),
                               ('nwchem', 'nwchem/dvb_ir_nwchem-7.0.out.gz', {'setup', 'freq'}),
                               ('nwchem', 'nwchem/dvb_td_nwchem-7.0.out.gz', {'setup', 'excited'})):
        out = gzip.decompress((data / name).read_bytes()).decode('utf-8', errors='replace')
        assert runner.finished_normally(kind, out, 0) and not runner.finished_normally(kind, out, 1), name
        passed = {key for key, _, marks in runner.MILESTONES if any(m in out for m in marks.get(kind, ()))}
        assert stages <= passed, (name, passed)
        cycles, energy = runner.progress(kind, out)
        assert energy is not None and energy < -300, name
        if 'gopt' in name:
            assert cycles >= 2, name
    for kind, argv in (('gamess', lambda base: [base, '00', '1']), ('nwchem', lambda base: [base + '.nw'])):
        fake = tmp_path / runner.PROGRAM_NAMES[kind][0]
        fake = program_script(fake, '')
        spec = runner.prepare(kind, fake, WATER, calc(basis='cc-pVDZ'), (), tmp_path / 'jobs')
        main = next(spec.folder.glob('*' + inputs_more.EXTENSION[kind]))
        assert list(spec.command[1:]) == argv(main.stem) and spec.output.name == runner.OUTPUT[kind].format(main.stem)
        assert spec.stdout == spec.output  # their output is what they print


def test_nwchem_writes_the_limit_of_the_optimization_cycles():
    # «Предел циклов» goes into «driver maxiter»: the remedy of the doctor for an optimization that ran out of cycles
    # («…, циклов: 200») changed nothing in the NWChem file before. 0 — the limit of NWChem; no block without an
    # optimization. NWChem 7.3.0 stops glycine at «maxiter 3» with «Failed to converge in maximum number of steps»
    # (tests/data/nwchem/glycine_opt_maxiter3_nwchem-7.3.out.gz)
    from modules.sextant import inputs

    mine = nwchem_lines(nwchem_input(WATER, calc(task='Оптимизация', max_cycles=200)))
    k = mine.index('driver')
    assert mine[k:k + 3] == ['driver', 'maxiter 200', 'end'] and k < mine.index('task dft optimize')
    assert 'driver' not in nwchem_lines(nwchem_input(WATER, calc(task='Оптимизация', max_cycles=0)))
    assert 'driver' not in nwchem_lines(nwchem_input(WATER, calc(task='Энергия')))
    assert 'maxiter 100' in nwchem_lines(nwchem_input(WATER, calc(task='Переходное состояние + частоты')))
    assert 'nwchem' in inputs.TASK_OPTIONS['max_cycles'][1]

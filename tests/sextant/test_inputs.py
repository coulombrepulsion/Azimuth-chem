"""Input files of ORCA (solvent, dispersion, TD-DFT, NMR), Gaussian, Psi4 and xtb.

Oracles written here by hand from the manuals: Gaussian 16 (route, %mem, Opt=ModRedundant with «B i j F»,
SCRF=(CPCM,Solvent=…), EmpiricalDispersion=GD3BJ, TD(NStates=n), NMR), Psi4 1.7 (memory, molecule block,
set block, method-d3bj, optimize/frequency, tdscf_states, optking frozen_*), ORCA (CPCM(…), D3BJ, D4, NMR,
%tddft nroots), xtb (--alpb). The texts of the defaults are the same as.
"""

from dataclasses import replace
import json

from pathlib import Path

import pytest

from modules.sextant import inputs
from azimuth.core import Atom, Calculation, Molecule, orca_input, project_text, read_project
from tests.fake_programs import program_script

WATER = Molecule('water', (Atom('O', 0.0, 0.0, 0.117), Atom('H', 0.0, 0.757, -0.469), Atom('H', 0.0, -0.757, -0.469)))
ATOMS = 'O   0.00000000  0.00000000  0.11700000\nH   0.00000000  0.75700000 -0.46900000\nH   0.00000000 -0.75700000 -0.46900000'
TDDFT = 'Спектр UV-Vis (TD-DFT)'
NMR = 'ЯМР (экранирование)'


def test_orca_keywords_for_solvent_dispersion_tddft_and_nmr():
    default = orca_input(WATER, Calculation())
    assert default.splitlines()[1] == '! B3LYP def2-SVP Opt Freq TightSCF'
    text = orca_input(WATER, Calculation(solvent='water', dispersion='D3BJ'))
    assert text.splitlines()[1] == '! B3LYP D3BJ def2-SVP Opt Freq TightSCF CPCM(Water)'
    assert orca_input(WATER, Calculation(solvent='dichloromethane', dispersion='D4')).splitlines()[1] == (
        '! B3LYP D4 def2-SVP Opt Freq TightSCF CPCM(CH2Cl2)'
    )
    td = orca_input(WATER, Calculation(task=TDDFT, cores=1))
    assert td.splitlines()[1] == '! B3LYP def2-SVP TightSCF' and '%tddft\n  nroots 10\nend\n' in td
    assert orca_input(WATER, Calculation(task=NMR)).splitlines()[1] == '! B3LYP def2-SVP NMR TightSCF'


def test_gaussian_golden():
    calc = Calculation(task='Оптимизация + частоты', cores=4, memory_mb=1000, solvent='water', dispersion='D3BJ')
    assert inputs.gaussian_input(WATER, calc) == (
        '%nprocshared=4\n%mem=4000MB\n'
        '#P B3LYP/def2SVP Opt=MaxCycles=100 Freq EmpiricalDispersion=GD3BJ SCRF=(CPCM,Solvent=Water) SCF=Tight\n\n'
        'H2O_B3LYP_def2-SVP_water\n\n0 1\n' + ATOMS + '\n\n'  # the title of the calculation, 100 cycles
    )
    fixed = inputs.gaussian_input(WATER, Calculation(task='Оптимизация', cores=1), (('B', (0, 1)), ('C', (2,)), ('A', (1, 0, 2))))
    assert '#P B3LYP/def2SVP Opt=(MaxCycles=100,ModRedundant) SCF=Tight\n' in fixed
    assert fixed.endswith(ATOMS + '\n\nB 1 2 F\nX 3 F\nA 2 1 3 F\n\n')
    assert '#P HF/STO-3G TD(NStates=10) SCF=Tight' in inputs.gaussian_input(WATER, Calculation('HF', 'STO-3G', TDDFT))
    assert '#P PBE1PBE/def2TZVP NMR SCF=Tight' in inputs.gaussian_input(WATER, Calculation('PBE0', 'def2-TZVP', NMR))
    assert 'ModRedundant' not in inputs.gaussian_input(WATER, Calculation(task='Энергия'), (('B', (0, 1)),))
    assert '-1 2\n' in inputs.gaussian_input(WATER, Calculation(charge=-1, multiplicity=2))
    with pytest.raises(ValueError):
        inputs.gaussian_input(WATER, Calculation(dispersion='D4'))  # Gaussian 16 has no D4


def test_psi4_golden():
    calc = Calculation(task='Оптимизация + частоты', cores=2, memory_mb=1000, dispersion='D3BJ')
    assert inputs.psi4_input(WATER, calc) == (
        '# H2O_B3LYP_def2-SVP\nmemory 2000 mb\n\nmolecule {\n0 1\n' + ATOMS + '\nsymmetry c1\n}\n\n'
        'set {\n  basis def2-svp\n  reference rks\n  scf_type df\n  e_convergence 8\n  d_convergence 8\n'
        '  geom_maxiter 100\n}\n\n'  # the title of the calculation and 100 optimization cycles
        "optimize('b3lyp-d3bj')\nfrequency('b3lyp-d3bj')\n"
    )
    ion = inputs.psi4_input(WATER, Calculation('HF', task='Энергия', charge=1, multiplicity=2))
    assert 'reference uhf' in ion and "energy('hf')" in ion and '1 2\n' in ion
    assert 'reference uks' in inputs.psi4_input(WATER, Calculation(charge=1, multiplicity=2, dispersion='D3BJ'))
    with pytest.raises(ValueError):  # Psi4 1.11 of conda-forge registers no «-d4» functional
        inputs.psi4_input(WATER, Calculation(dispersion='D4'))
    td = inputs.psi4_input(WATER, Calculation(task=TDDFT))
    assert '  tdscf_states 10\n' in td and td.endswith("energy('td-b3lyp')\n")  # Psi4 1.11: «td-» runs TD-DFT
    assert 'symmetry c1' in td and 'symmetry c1' not in inputs.psi4_input(WATER, Calculation(task='Энергия'))
    frozen = inputs.psi4_input(WATER, Calculation(task='Оптимизация'), (('B', (0, 1)), ('B', (0, 2)), ('C', (1,)), ('A', (1, 0, 2))))
    assert 'set optking {\n  frozen_cartesian "2 xyz"\n  frozen_distance "1 2 1 3"\n  frozen_bend "2 1 3"\n}\n' in frozen
    solvated = inputs.psi4_input(WATER, Calculation(task='Энергия', solvent='dmso'))
    assert 'set pcm true' in solvated and 'SolverType = CPCM' in solvated and 'Solvent = Dimethylsulfoxide' in solvated
    for bad in (Calculation(task=NMR), Calculation(task='Оптимизация', solvent='water'), Calculation(task='Энергия', solvent='hexane')):
        with pytest.raises(ValueError):
            inputs.psi4_input(WATER, bad)  # no NMR, no PCM gradients, no hexane in PCMSolver


def test_xtb_solvent_and_refusals():
    calc = Calculation(task='Оптимизация', cores=1, solvent='chloroform')
    assert inputs.xtb_arguments(calc) == ['molecule.xyz', '--gfn', '2', '--chrg', '0', '--uhf', '0', '--opt', '--alpb', 'chcl3',
                                          '--cycles', '100', '-P', '1']  # 100 cycles by default
    for bad in (Calculation(task=TDDFT), Calculation(task=NMR), Calculation(solvent='ethanol')):
        with pytest.raises(ValueError):
            inputs.validate_xtb(WATER, bad)


def test_every_solvent_has_a_name_in_each_program_or_a_refusal():
    from azimuth.core import SOLVENTS

    for key in SOLVENTS:
        calc = Calculation(task='Энергия', solvent=key)
        for kind in inputs.KINDS:
            given = replace(calc, method='PM7') if kind == 'mopac' else calc  # MOPAC has its own methods
            given = replace(given, basis='cc-pVDZ') if kind == 'gamess' else given  # GAMESS has no def2
            try:
                text = inputs.preview(kind, WATER, given)
            except ValueError as exc:
                assert key and 'растворител' in str(exc)  # only a named solvent is refused, and with this message
                continue
            if kind == 'mopac':  # COSMO takes the dielectric constant, not a name
                assert not key or f'EPS={inputs.MOPAC_EPS[key]:g}' in text.splitlines()[0]
                continue
            assert not key or inputs.solvent_name(kind, calc) in text


def test_settings_validation_and_projects():
    with pytest.raises(ValueError):
        orca_input(WATER, Calculation('HF', dispersion='D3BJ'))  # dispersion only for DFT here
    for bad in ({'solvent': 'mercury'}, {'dispersion': 'D2'}, {'solvent': ['water']}):
        with pytest.raises(ValueError):
            orca_input(WATER, replace(Calculation(), **bad))
    calc = Calculation(task=TDDFT, solvent='acetonitrile', dispersion='D4')
    assert read_project(project_text(WATER, calc)) == (WATER, calc)
    old = json.loads(project_text(WATER, Calculation()))
    del old['calculation']['solvent'], old['calculation']['dispersion']  # a project of 0.36.0
    assert read_project(json.dumps(old))[1] == Calculation()
    files = inputs.input_files('xtb', WATER, Calculation(task='Оптимизация'), (('B', (0, 1)),))
    assert set(files) == {'H2O_GFN2-xTB.xyz', 'xcontrol'}  # named after the calculation
    assert set(inputs.input_files('psi4', WATER, Calculation())) == {'H2O_B3LYP_def2-SVP.dat'}
    mine = Calculation(title='Вода, шаг 2')
    assert set(inputs.input_files('orca', WATER, mine)) == {'Voda_shag_2.inp'}
    assert orca_input(WATER, mine).startswith('# Вода, шаг 2\n') and read_project(project_text(WATER, mine))[1] == mine


def test_orca_neb_input():
    # NEB-CI with the product in end.xyz (the ORCA 5/6 %neb keywords; ASSUMPTION: from the manual)
    from azimuth.core import NEB_TASK

    end = Molecule('product', tuple(Atom(a.symbol, a.x, a.y + 0.1, a.z) for a in WATER.atoms))
    calc = Calculation(task=NEB_TASK, cores=1)
    text = orca_input(WATER, calc, (), end, 6)
    assert text.splitlines()[1] == '! B3LYP def2-SVP NEB-CI TightSCF'
    assert '%neb\n  neb_end_xyzfile "end.xyz"\n  nimages 6\nend\n' in text
    files = inputs.input_files('orca', WATER, calc, (), (end, 6))
    assert files['end.xyz'] == end.xyz() and 'end.xyz' in inputs.preview('orca', WATER, calc, (), (end, 6))
    with pytest.raises(ValueError):
        orca_input(WATER, calc)  # no end structure
    with pytest.raises(ValueError):
        orca_input(WATER, calc, (), Molecule('x', (end.atoms[1], end.atoms[0], end.atoms[2])), 6)  # another order
    with pytest.raises(ValueError):
        orca_input(WATER, calc, (), end, 0)
    for kind in ('gaussian', 'psi4', 'xtb'):
        with pytest.raises(ValueError):
            inputs.input_files(kind, WATER, calc)


def test_methods_and_bases_of_each_program():
    # the keyword of every program written here by hand from the manuals (Gaussian 16: PBE1PBE,
    # TPSSTPSS, wB97XD, 6-31G(d,p), def2TZVP; Psi4: lower case, «-d3bj»; ORCA: M062X, AutoAux for B2PLYP)
    from azimuth.core import BASES, METHODS, bases_for, methods_for

    assert {'B3LYP', 'PBE0', 'HF', 'MP2', 'M06-2X', 'CAM-B3LYP', 'B2PLYP'} <= set(methods_for('orca')) & set(methods_for('gaussian'))
    assert 'ωB97X-D' in methods_for('gaussian') and 'ωB97X-D' not in methods_for('orca')
    assert 'ωB97X-D3' in methods_for('orca') and 'r2SCAN' not in methods_for('gaussian')
    assert 'pcseg-1' in bases_for('psi4') and 'pcseg-1' not in bases_for('gaussian') and 'def2-SVPD' not in bases_for('gaussian')
    assert 'pcSseg-2' in bases_for('orca') and 'pcSseg-2' not in bases_for('psi4')  # a basis for shieldings: ORCA alone
    assert methods_for('xtb') == () and bases_for('crest') == ()
    assert set(methods_for('orca')) <= set(METHODS) and set(bases_for('orca')) == set(BASES)
    first = lambda text: text.splitlines()[1]  # noqa: E731
    assert first(orca_input(WATER, Calculation('M06-2X', '6-31G**'))) == '! M062X 6-31G** Opt Freq TightSCF'
    assert first(orca_input(WATER, Calculation('B2PLYP', 'def2-TZVP', dispersion='D3BJ'))) == '! B2PLYP D3BJ def2-TZVP AutoAux Opt Freq TightSCF'
    g = inputs.gaussian_input(WATER, Calculation('TPSS', '6-311G**', 'Энергия', dispersion='D3BJ'))
    assert '#P TPSSTPSS/6-311G(d,p) EmpiricalDispersion=GD3BJ SCF=Tight' in g
    assert '#P wB97XD/Aug-cc-pVDZ Opt=MaxCycles=100 SCF=Tight' in inputs.gaussian_input(WATER, Calculation('ωB97X-D', 'aug-cc-pVDZ', 'Оптимизация'))
    p = inputs.psi4_input(WATER, Calculation('MP2', 'cc-pVTZ', 'Энергия', multiplicity=1))
    assert '  basis cc-pvtz\n  reference rhf\n' in p and "energy('mp2')" in p
    assert '  freeze_core true\n' in p  # the core not correlated, as ORCA and Gaussian
    assert "optimize('cam-b3lyp-d3bj')" in inputs.psi4_input(WATER, Calculation('CAM-B3LYP', '6-31G*', 'Оптимизация', dispersion='D3BJ'))
    for kind, calc in (
        ('gaussian', Calculation('r2SCAN')),  # no r2SCAN in Gaussian 16
        ('gaussian', Calculation(basis='pcseg-1')),
        ('psi4', Calculation('ωB97X-D3')),
        ('orca', Calculation('ωB97X-D')),
    ):
        with pytest.raises(ValueError):
            inputs.input_files(kind, WATER, calc)
    for calc in (Calculation('M06-2X', dispersion='D3BJ'), Calculation('MP2', dispersion='D4'), Calculation('MP2', task=TDDFT)):
        with pytest.raises(ValueError):
            orca_input(WATER, calc)
    zinc = Molecule('Zn', (Atom('Zn', 0, 0, 0),))
    with pytest.raises(ValueError):
        orca_input(zinc, Calculation('HF', 'cc-pVDZ', 'Энергия', multiplicity=1))  # cc-pVDZ: H–Ar, Ga–Kr here
    assert '! HF 6-31G* TightSCF' in orca_input(zinc, Calculation('HF', '6-31G*', 'Энергия'))


def test_advanced_settings_in_every_program():
    # «Дополнительные настройки» — the keywords written here by hand from the manuals of ORCA 6,
    # Gaussian 16, Psi4 1.7 and xtb 6; the defaults keep the files of 0.47.0 (the golden tests above), except the
    # 100 optimization cycles of 0.67.0
    adv = Calculation(
        'B3LYP', 'def2-SVP', 'Оптимизация + частоты', scf='verytight', grid='fine', no_ri=True, ts=True, opt_conv='tight',
        max_cycles=150, population='hirshfeld', orbitals=True, temperature=350.0, pressure=2.0, extra='%scf MaxIter 300 end',
    )
    text = orca_input(WATER, adv, (('B', (0, 1)),))
    assert text.splitlines()[1] == '! B3LYP def2-SVP OptTS Freq VeryTightSCF TightOpt DefGrid3 NoRI'
    assert '%geom\n  Constraints\n    { B 0 1 C }\n  end\n  MaxIter 150\n  Calc_Hess true\nend\n' in text
    assert '%output\n  Print[P_Hirshfeld] 1\n  Print[P_MOs] 1\n  Print[P_Basis] 2\nend\n' in text
    assert '%freq\n  Temp 350\n  Pressure 2\nend\n' in text and '%scf MaxIter 300 end\n' in text
    td = orca_input(WATER, Calculation(task=TDDFT, states=25))
    assert '%tddft\n  nroots 25\nend\n' in td
    assert 'NBO' in orca_input(WATER, Calculation(population='nbo')).splitlines()[1]
    g = inputs.gaussian_input(WATER, adv, (('B', (0, 1)),))
    route = g.splitlines()[2]
    assert route == ('#P B3LYP/def2SVP Opt=(TS,CalcFC,NoEigenTest,Tight,MaxCycles=150,ModRedundant) Freq SCF=VeryTight '
                     'Integral=SuperFineGrid Pop=Hirshfeld Temperature=350 Pressure=2 %scf MaxIter 300 end')
    assert 'Opt=(CalcFC,MaxCycles=100)' in inputs.gaussian_input(WATER, Calculation(task='Оптимизация', calc_hessian=True))
    assert 'Opt=CalcFC ' in inputs.gaussian_input(WATER, Calculation(task='Оптимизация', calc_hessian=True, max_cycles=0))
    assert 'TD(NStates=5)' in inputs.gaussian_input(WATER, Calculation(task=TDDFT, states=5))
    p = inputs.psi4_input(WATER, replace(adv, population='mulliken', extra="set print 2"))
    for line in ('scf_type pk', 'e_convergence 10', 'dft_radial_points 99', 'opt_type ts', 'full_hess_every 0',
                 'g_convergence gau_tight', 'geom_maxiter 150', 't 350', 'p 202650', 'molden_write true'):
        assert f'  {line}\n' in p, line
    assert '\nset print 2\n' in p
    with pytest.raises(ValueError):
        inputs.psi4_input(WATER, Calculation(population='nbo'))  # NBO and Hirshfeld: ORCA, Gaussian
    x = inputs.xtb_arguments(Calculation(task='Оптимизация', opt_conv='tight', max_cycles=50, orbitals=True, extra='--etemp 500', cores=1))
    assert x[x.index('--opt'):] == ['--opt', 'tight', '--cycles', '50', '--molden', '--etemp', '500', '-P', '1']
    with pytest.raises(ValueError):
        inputs.input_files('xtb', WATER, Calculation(task='Оптимизация', ts=True))  # xtb has no TS search
    for bad in (dict(scf='loose'), dict(grid='ultra'), dict(max_cycles=-1), dict(states=0), dict(temperature=0.0),
                dict(pressure=-1.0), dict(population='becke'), dict(no_ri=1), dict(extra='a\x00b')):
        with pytest.raises(ValueError):
            Calculation(**bad).validate_settings()
    assert orca_input(WATER, Calculation(task='Энергия')) == orca_input(WATER, Calculation(ts=True, task='Энергия'))  # no Opt: no TS
    calc = replace(adv, ts=False)
    assert read_project(project_text(WATER, calc))[1] == calc  # the project keeps them


def test_input_check():
    # the files Azimuth writes pass the check for every task and the usual options; a broken structure is
    # found with its line: an unclosed %block or geometry, a coordinate without three numbers, no charge and
    # multiplicity, an unclosed bracket or a Python mistake in Psi4
    from azimuth.core import TASKS
    from modules.sextant.input_check import check

    checked = 0
    for kind in ('orca', 'gaussian', 'psi4'):
        for task in TASKS:
            for options in ({}, {'solvent': 'water'}, {'multiplicity': 3}, {'dispersion': 'D3BJ'},
                            {'orbitals': True, 'population': 'hirshfeld', 'max_cycles': 50, 'ts': True,
                             'temperature': 350.0, 'scf': 'verytight', 'grid': 'fine', 'no_ri': True}):
                for constraints in ((), (('B', (0, 1)), ('C', (2,)), ('A', (1, 0, 2)))):
                    try:
                        text = inputs.preview(kind, WATER, replace(Calculation(task=task), **options), constraints)
                    except ValueError:
                        continue  # a task the program cannot do
                    assert check(kind, text) == [], (kind, task, options, constraints)
                    checked += 1
    assert checked > 100
    orca = orca_input(WATER, Calculation(task='Оптимизация', max_cycles=0))  # without its own %geom block
    problems = check('orca', orca.replace('\n*\n', '\n'))  # «* xyz» without its «*»
    assert problems and 'Координаты' in problems[0].text
    broken = orca.replace('%maxcore 1000\n', '%maxcore 1000\n%geom\n  MaxIter 50\n')
    first = check('orca', broken)[0]
    assert first.line == broken.splitlines().index('* xyz 0 1') + 1 and '%geom' in first.text
    assert check('orca', orca.replace('H   0.00000000  0.75700000 -0.46900000', 'H 0.0 0.757'))[0].line == 8
    assert any('!' in p.text for p in check('orca', '* xyz 0 1\nO 0 0 0\n*\n'))
    gaussian = inputs.gaussian_input(WATER, Calculation())
    assert check('gaussian', gaussian.replace('0 1\n', '')) != []
    assert check('gaussian', gaussian.replace('#P ', '')) and check('gaussian', gaussian.replace('0.75700000', 'x'))
    psi4 = inputs.psi4_input(WATER, Calculation(task='Энергия'))
    assert check('psi4', psi4.replace("energy('b3lyp')", "energy('b3lyp'")) or check('psi4', psi4.rstrip()[:-1])
    assert check('psi4', psi4 + 'print(1\n')[0].text.startswith('Не закрыта скобка')
    assert 'Python' in check('psi4', psi4 + 'x = = 1\n')[0].text
    assert check('xtb', 'anything') == []


def test_edited_input_is_written(tmp_path):
    # runner.prepare writes the text edited in Sextant instead of the generated input

    from modules.sextant import runner

    orca = tmp_path / 'orca'
    orca = program_script(orca, '')
    (tmp_path / 'orca_scf').write_text('')
    text = orca_input(WATER, replace(Calculation(task='Энергия'), cores=1)) + '# mine'
    spec = runner.prepare('orca', orca, WATER, replace(Calculation(task='Энергия'), cores=1), (), tmp_path / 'jobs', text=text)
    assert (spec.folder / 'H2O_B3LYP_def2-SVP.inp').read_text(encoding='utf-8') == text + '\n'  # its name
    assert spec.command[1] == 'H2O_B3LYP_def2-SVP.inp' and spec.output.name == 'H2O_B3LYP_def2-SVP.out'
    with pytest.raises(ValueError):
        runner.prepare('orca', orca, WATER, replace(Calculation(task='Энергия'), cores=1), (), tmp_path / 'jobs', text='  ')


def test_rijcosx_for_orca():
    # RIJCOSX asked for; def2/J for a basis outside def2; nothing with «Без RI»; projects of older versions
    # have no field and read as off
    hf = orca_input(WATER, Calculation('HF', 'def2-SVP', 'Энергия', rijcosx=True))
    assert hf.splitlines()[1].split()[-1] == 'RIJCOSX' and 'def2/J' not in hf
    pople = orca_input(WATER, Calculation('HF', '6-31G*', 'Энергия', rijcosx=True))
    assert 'RIJCOSX def2/J' in pople.splitlines()[1]
    off = orca_input(WATER, Calculation('HF', 'def2-SVP', 'Энергия', rijcosx=True, no_ri=True))
    assert 'RIJCOSX' not in off and 'NoRI' in off
    assert 'RIJCOSX' not in orca_input(WATER, Calculation('HF', 'def2-SVP', 'Энергия'))
    data = json.loads(project_text(WATER, Calculation()))
    data['calculation'].pop('rijcosx')
    assert read_project(json.dumps(data))[1].rijcosx is False


def test_relativistic_scf_help_tddft_options_and_excited_state_optimization():
    # the defaults give the files of 0.72 (the other tests); DKH, ZORA, X2C, SlowConv, AutoAux, NumFreq, TDA /
    # full TD-DFT, triplets and the optimization of an excited state. Oracles: the ORCA 6 manual (simple input keywords
    # DKH, ZORA, X2C, SlowConv, VerySlowConv, AutoAux, NumFreq; %tddft nroots, tda, triplets, iroot), Gaussian 16
    # (Integral=DKH2, SCF=XQC, Freq=Numer, TD(NStates,Root,50-50), TDA), Psi4 1.7 (tdscf_tda, tdscf_triplets,
    # damping_percentage)
    from azimuth.core import EXCITED_OPT_TASK, TDDFT_TASK, read_xyz

    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
    text = orca_input(water, Calculation(relativistic='DKH', slow_conv='SlowConv', auto_aux=True, num_freq=True))
    # the recontracted basis of the Hamiltonian (DKH-def2-*, ZORA-def2-* with SARC/J; x2c-*all)
    assert text.splitlines()[1] == '! B3LYP DKH-def2-SVP AutoAux Opt NumFreq TightSCF DKH SlowConv'
    assert '! B3LYP ZORA-def2-SVP Opt Freq TightSCF SARC/J ZORA' in orca_input(water, Calculation(relativistic='ZORA'))
    td = orca_input(water, Calculation(task=TDDFT_TASK, tddft_mode='full', triplets=True, states=6))
    assert '%tddft\n  nroots 6\n  tda false\n  triplets true\nend\n' in td
    excited = orca_input(water, Calculation(task=EXCITED_OPT_TASK, states=5, root=2, tddft_mode='tda'))
    assert excited.splitlines()[1].startswith('! LibXC(B3LYP) def2-SVP Opt ')  # the LibXC B3LYP
    assert '%tddft\n  nroots 5\n  tda true\n  iroot 2\nend\n' in excited and 'MaxIter 100' in excited
    g = inputs.gaussian_input(water, Calculation(task=EXCITED_OPT_TASK, states=5, root=2, relativistic='DKH', slow_conv='SlowConv'))
    route = g.splitlines()[2]
    assert 'TD(NStates=5,Root=2) Opt=MaxCycles=100' in route and 'SCF=(Tight,XQC)' in route and 'Integral=DKH2' in route
    assert 'TDA(NStates=10,50-50)' in inputs.gaussian_input(water, Calculation(task=TDDFT_TASK, tddft_mode='tda', triplets=True))
    assert 'Freq=Numer' in inputs.gaussian_input(water, Calculation(num_freq=True)).splitlines()[2]
    with pytest.raises(ValueError):
        inputs.gaussian_input(water, Calculation(relativistic='ZORA'))
    p = inputs.psi4_input(water, Calculation(task=TDDFT_TASK, tddft_mode='tda', triplets=True, slow_conv='VerySlowConv'))
    assert 'tdscf_tda true' in p and 'tdscf_triplets also' in p and 'damping_percentage 40' in p
    assert "frequency('b3lyp', dertype='energy')" in inputs.psi4_input(water, Calculation(num_freq=True))
    for bad in (Calculation(relativistic='DKH'), Calculation(task=EXCITED_OPT_TASK)):
        with pytest.raises(ValueError):
            inputs.psi4_input(water, bad)
    for bad in (dict(root=11), dict(task=EXCITED_OPT_TASK, triplets=True), dict(relativistic='Pauli'), dict(tddft_mode='x')):
        with pytest.raises(ValueError):
            Calculation(**bad).validate_settings()
    with pytest.raises(ValueError):
        inputs.validate_xtb(water, Calculation(relativistic='DKH', task='Оптимизация'))


def test_settings_read_back_from_an_input_file():
    # an input file opened in Sextant — its method, basis, task and dispersion as the files Sextant writes
    from azimuth.core import TDDFT_TASK, read_xyz

    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
    for calc in (Calculation(), Calculation(method='PBE0', basis='def2-TZVP', task='Энергия', dispersion='D3BJ'),
                 Calculation(task=TDDFT_TASK), Calculation(task='Оптимизация')):
        for kind, text in (('orca', orca_input(water, calc)), ('gaussian', inputs.gaussian_input(water, calc))):
            found = inputs.read_settings(kind, text)
            assert (found['method'], found['basis'], found['task']) == (calc.method, calc.basis, calc.task), (kind, found)
            assert found.get('dispersion', '') == calc.dispersion
    assert inputs.input_kind('a.gjf', '') == 'gaussian' and inputs.input_kind('a.inp', '#p hf') == 'orca'
    assert inputs.input_kind('a.txt', '%nproc=2\n#p B3LYP/6-31G(d)\n') == 'gaussian'
    hand = '! wB97X-D3 def2-TZVP Opt\n* xyz 0 1\nHe 0 0 0\n*\n'
    assert inputs.read_settings('orca', hand) == {'method': 'ωB97X-D3', 'basis': 'def2-TZVP', 'task': 'Оптимизация'}


def test_input_files_of_a_set_of_structures():
    # one setting, many structures — one file each, named after the structure, charge and multiplicity of each
    from azimuth.core import read_xyz

    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
    oh = read_xyz('2\nhydroxyl\nO 0 0 0\nH 0 0 0.97')
    neon = read_xyz('1\nneon\nNe 0 0 0')
    states = {'H2O': (0, 1), 'HO': (0, 2), 'Ne': (0, 1)}
    files, failed = inputs.set_input_files('orca', [(water, 'вода'), (oh, 'OH-радикал'), (neon, 'вода'), (water, '')],
                                           Calculation(task='Энергия'), state=lambda m: states[m.formula])
    assert list(files) == ['voda_B3LYP_def2-SVP.inp', 'OH-radikal_B3LYP_def2-SVP.inp', 'voda_B3LYP_def2-SVP_2.inp',
                           '4_B3LYP_def2-SVP.inp'] and not failed
    assert '* xyz 0 2' in files['OH-radikal_B3LYP_def2-SVP.inp'] and files['voda_B3LYP_def2-SVP.inp'].startswith('# voda_B3LYP')
    bad, failed = inputs.set_input_files('orca', [(oh, 'радикал')], Calculation(task='Энергия'))  # the doublet is wrong
    assert not bad and failed and failed[0][0] == 'радикал'


def test_crest_energy_window_and_metadynamics_length():
    # «--ewin <REAL>» and «--mdlen x<REAL>» of the CREST documentation (keywords page)
    from azimuth.core import Calculation
    from modules.sextant.inputs import crest_arguments

    calc = Calculation(task='Оптимизация', cores=4)
    plain = crest_arguments(calc, xyz='m.xyz')
    assert plain == ['m.xyz', '--gfn2', '--chrg', '0', '--uhf', '0', '-T', '4']
    args = crest_arguments(calc, xyz='m.xyz', ewin=10.0, mdlen=2.0)
    assert args[args.index('--ewin') + 1] == '10' and args[args.index('--mdlen') + 1] == 'x2'
    assert '--mdlen' not in crest_arguments(calc, ewin=6.0, mdlen=1.0) and crest_arguments(calc, quick=True)[-1] == '--quick'
    for bad in ({'ewin': 0.0}, {'mdlen': 20.0}):
        with pytest.raises(ValueError):
            crest_arguments(calc, **bad)


def _mopac_jobs(text):
    """The jobs of a .mop: (keywords, geometry rows) — the next job starts after the blank line ending the geometry."""
    jobs, lines, k = [], text.splitlines(), 0
    while k < len(lines):
        if not lines[k].strip():
            k += 1
            continue
        keywords, k = lines[k].split(), k + 3  # the keyword line and the two title lines
        rows = []
        while k < len(lines) and lines[k].strip():
            rows.append(lines[k].split())
            k += 1
        jobs.append((keywords, rows))
    return jobs


def test_mopac_input_for_every_task():
    # the .mop of Sextant; «Оптимизация + частоты» — the two jobs with OLDGEO that MOPAC 23.2.5 ran
    # (tests/data/mopac/inputs/h2o_pm7_opt_then_force_oldgeo.mop: the frequencies of two separate runs)
    from dataclasses import replace

    from azimuth.core import Calculation, bases_for, methods_for, read_xyz
    from modules.sextant.inputs import input_files, mopac_input

    assert methods_for('mopac') == ('PM7', 'PM6', 'PM6-D3H4', 'AM1', 'RM1', 'MNDO') and bases_for('mopac') == ()
    assert 'PM7' not in methods_for('orca') and 'B3LYP' not in methods_for('mopac')
    water = read_xyz('3\nw\nO 0 0 0.117\nH 0 0.757 -0.467\nH 0 -0.757 -0.467\n')
    calc = Calculation(method='PM7', task='Оптимизация + частоты')
    assert list(input_files('mopac', water, calc)) == ['H2O_PM7.mop']  # no basis in the name
    ours = _mopac_jobs(mopac_input(water, calc))
    reference = _mopac_jobs((Path(__file__).parents[1] / 'data' / 'mopac' / 'inputs' / 'h2o_pm7_opt_then_force_oldgeo.mop')
                            .read_text(encoding='utf-8'))
    assert [sorted(k) for k, _ in ours] == [sorted(k) for k, _ in reference]  # PM7 PRECISE AUX / PM7 FORCE THERMO OLDGEO AUX
    assert len(ours[0][1]) == 3 and ours[1][1] == [] and all(r[2] == r[4] == r[6] == '1' for r in ours[0][1])
    energy = _mopac_jobs(mopac_input(water, replace(calc, task='Энергия')))
    assert len(energy) == 1 and energy[0][0] == ['PM7', '1SCF', 'AUX'] and all(r[2] == '0' for r in energy[0][1])
    ion = _mopac_jobs(mopac_input(water, replace(calc, task='Оптимизация', charge=1, multiplicity=2, solvent='water')))
    assert ion[0][0] == ['PM7', 'CHARGE=1', 'DOUBLET', 'UHF', 'EPS=78.4', 'PRECISE', 'AUX']
    frozen = _mopac_jobs(mopac_input(water, replace(calc, task='Оптимизация'), (('C', (0,)),)))
    assert frozen[0][1][0][2::2] == ['0', '0', '0'] and frozen[0][1][1][2::2] == ['1', '1', '1']
    hot = _mopac_jobs(mopac_input(water, replace(calc, temperature=350.0)))
    assert 'THERMO=(350,450,100)' in hot[1][0]  # the form (start, end, step) checked: THERMO=(298,398,100)
    for bad, constraints in ((dict(method='B3LYP'), ()), (dict(task='ЯМР (экранирование)'), ()), ({}, (('B', (0, 1)),)),
                             (dict(multiplicity=2), ())):
        with pytest.raises(ValueError):
            mopac_input(water, replace(calc, **bad), constraints)


def test_mopac_in_the_runner():
    # the command, the output, the normal end and the stages of MOPAC 23.2.5
    from azimuth.core import Calculation, read_xyz
    from modules.sextant import runner

    out = (Path(__file__).parents[1] / 'data' / 'mopac' / 'h2o_pm7_opt_then_force_oldgeo.out').read_text(encoding='utf-8')
    assert runner.finished_normally('mopac', out, 0) and not runner.finished_normally('mopac', out, 1)
    assert not runner.finished_normally('mopac', out.replace('JOB ENDED NORMALLY', ''), 0)
    assert runner.progress('mopac', out) == (4, None)  # four optimization cycles; a ΔHf is not a hartree energy
    passed = {key for key, _, marks in runner.MILESTONES if any(m in out for m in marks.get('mopac', ()))}
    assert {'setup', 'scf', 'opt', 'freq', 'thermo'} <= passed
    assert runner.OUTPUT['mopac'] == '{}.out' and 'mopac' in runner.PROGRAM_NAMES['mopac']
    water = read_xyz('3\nw\nO 0 0 0.117\nH 0 0.757 -0.467\nH 0 -0.757 -0.467\n')
    assert 'mopac' in runner.KINDS  # GAMESS and NWChem after it
    import os
    import tempfile

    with tempfile.TemporaryDirectory() as root:
        fake = Path(root) / 'mopac'
        fake = program_script(fake, '')
        spec = runner.prepare('mopac', fake, water, Calculation(method='PM7', task='Энергия'), (), Path(root) / 'jobs')
        assert spec.command == (str(fake), 'H2O_PM7.mop') and spec.output.name == 'H2O_PM7.out'
        assert (spec.folder / 'H2O_PM7.mop').read_text(encoding='utf-8').startswith('PM7 1SCF AUX\n')
        edited = runner.prepare('mopac', fake, water, Calculation(method='PM7', task='Энергия'), (), Path(root) / 'jobs',
                                text='PM6 1SCF AUX\nt\n\nO 0 0 0 0 0 0\n')
        assert (edited.folder / 'H2O_PM7.mop').read_text(encoding='utf-8') == 'PM6 1SCF AUX\nt\n\nO 0 0 0 0 0 0\n'
        assert os.access(fake, os.X_OK)


# the tasks and the settings Sextant offers per program — checked against the input writers themselves


def _calc(kind, **changes):
    if changes.get('task') == inputs.SCAN_TASK:  # the O–H bond of WATER (0.957 Å) to 1.2 Å
        changes = {'scan_end': 1.2, **changes}
    calc = Calculation(**changes)
    return replace(calc, method='PM7') if kind == 'mopac' else calc


def _preview(kind, calc):
    end = Molecule('end', WATER.atoms)
    fixed = (('B', (0, 1)),) if calc.task == inputs.SCAN_TASK else ()  # what the scan follows
    return inputs.preview(kind, WATER, calc, fixed, (end, 4) if calc.task == inputs.NEB_TASK else None)


def test_the_tasks_of_each_program_are_the_tasks_it_writes():
    from azimuth.core import TASKS

    for kind in ('orca', 'gaussian', 'psi4', 'xtb', 'mopac'):
        offered = inputs.tasks_for(kind)
        assert offered and set(offered) <= set(TASKS)
        for task in TASKS:
            calc = _calc(kind, task=task)
            if task in offered:
                assert _preview(kind, calc), (kind, task)
            else:
                with pytest.raises(ValueError):
                    _preview(kind, calc)


CHANGED = {'ts': True, 'opt_conv': 'tight', 'max_cycles': 37, 'calc_hessian': True, 'temperature': 350.0,
           'pressure': 2.0, 'num_freq': True, 'raman': True, 'states': 7, 'tddft_mode': 'tda', 'triplets': True,
           'root': 2, 'stability': True, 'scan_end': 1.3, 'scan_steps': 7, 'guess': '/earlier/water.gbw',
           'nto': True}


def test_the_settings_under_a_task_are_the_ones_its_program_writes():
    # a setting shown for (program, task) changes the input; one not shown would change nothing (or is refused) —
    # so nothing in the form is a dead switch, and nothing the program writes is missing from it
    for kind in ('orca', 'gaussian', 'psi4', 'xtb', 'mopac'):
        for task in inputs.tasks_for(kind):
            shown = inputs.task_options(kind, task)
            base = _preview(kind, _calc(kind, task=task))
            for key, value in CHANGED.items():
                try:
                    text = _preview(kind, _calc(kind, task=task, **{key: value}))
                except ValueError:
                    text = base  # refused: not something this program does here
                if key in shown:
                    assert text != base, (kind, task, key)
                else:
                    assert text == base, (kind, task, key)


def test_orca_refuses_an_excited_state_optimization_with_a_meta_gga():
    # ORCA 6.0.1 stopped the user's run at once (TPSSh, tests/data/orca601/h2o_excited_opt_tpssh_meta_gga.out)
    from azimuth.core import EXCITED_OPT_TASK, META_GGA, TDDFT_TASK

    for method in sorted(META_GGA):
        with pytest.raises(ValueError) as error:
            orca_input(WATER, Calculation(method=method, task=EXCITED_OPT_TASK))
        assert 'мета-GGA' in str(error.value) and 'CAM-B3LYP' in str(error.value)
        assert '%tddft' in orca_input(WATER, Calculation(method=method, task=TDDFT_TASK))  # the spectrum is fine
    assert 'iroot 1' in orca_input(WATER, Calculation(method='CAM-B3LYP', task=EXCITED_OPT_TASK))


def test_excited_state_optimization_with_b3lyp_uses_libxc():
    # ORCA 6.1.1 stops a B3LYP excited-state optimization (no native third derivative of B88 exchange); the LibXC
    # B3LYP ran on ORCA 6.0.1 and 6.1.1 (tools/check_programs.py --beta) — the same energy, D3BJ parameters
    from azimuth.core import EXCITED_OPT_TASK, TDDFT_TASK

    line = lambda **k: orca_input(WATER, Calculation(**k)).splitlines()[1]
    assert line(task=EXCITED_OPT_TASK).startswith('! LibXC(B3LYP) def2-SVP Opt')
    assert line(task=EXCITED_OPT_TASK, dispersion='D3BJ').startswith('! LibXC(B3LYP) D3BJ ')
    assert line(task=EXCITED_OPT_TASK, dispersion='D4').startswith('! B3LYP D4 ')  # not run under the LibXC name
    assert line(task=TDDFT_TASK).startswith('! B3LYP ') and line(task='Оптимизация').startswith('! B3LYP ')
    assert line(task=EXCITED_OPT_TASK, method='PBE0').startswith('! PBE0 ')
    opened = inputs.read_settings('orca', orca_input(WATER, Calculation(task=EXCITED_OPT_TASK, dispersion='D3BJ')))
    assert opened['method'] == 'B3LYP' and opened['dispersion'] == 'D3BJ'  # the file opened again in Sextant


def test_smd_d3_zero_and_stability():
    # SMD (ORCA %cpcm smd, Gaussian SCRF=SMD), D3 with zero damping (ORCA D3ZERO, Gaussian GD3, Psi4 -d3zero),
    # the stability analysis of an energy (ORCA STABPerform, Gaussian Stable=Opt) — and the files read back
    smd = Calculation(task='Энергия', solvent='water', solvent_model='smd', dispersion='D3ZERO', stability=True)
    text = orca_input(WATER, smd)
    assert text.splitlines()[1].split()[1:3] == ['B3LYP', 'D3ZERO'] and 'CPCM(Water)' in text.splitlines()[1]
    assert '%cpcm\n  smd true\n  SMDsolvent "Water"\nend' in text and 'STABPerform true' in text
    assert inputs.read_settings('orca', text)['dispersion'] == 'D3ZERO'
    gjf = inputs.gaussian_input(WATER, smd)
    route = gjf.splitlines()[[k for k, l in enumerate(gjf.splitlines()) if l.startswith('#')][0]]
    assert 'EmpiricalDispersion=GD3 ' in route + ' ' and 'SCRF=(SMD,Solvent=Water)' in route and 'Stable=Opt' in route
    assert inputs.read_settings('gaussian', gjf)['dispersion'] == 'D3ZERO'
    assert "energy('b3lyp-d3zero')" in inputs.psi4_input(WATER, replace(smd, solvent='', solvent_model='cpcm', stability=False))
    with pytest.raises(ValueError):
        Calculation(solvent_model='cosmo').validate_settings()
    opt = replace(smd, task='Оптимизация')  # the analysis is for an energy only
    assert 'STABPerform' not in orca_input(WATER, opt) and 'Stable=Opt' not in inputs.gaussian_input(WATER, opt)


def test_task_settings_come_with_the_task():
    from modules.sextant import advice

    assert advice.task_settings('Оптимизация + частоты')['opt_conv'] == 'tight'
    assert advice.task_settings('ЯМР (экранирование)')['grid'] == 'fine'
    assert advice.task_settings('Энергия')['opt_conv'] == 'normal'
    assert set(advice.task_settings('Энергия')) <= set(Calculation.__dataclass_fields__)


def test_relaxed_scan_of_orca_and_gaussian():
    # the bond, angle or dihedral chosen among the constraints goes from its value to the end in equal steps. Oracles:
    # ORCA prints «Dihedral (9, 8, 3, 2): range= 0 .. 360 steps = 12» and 12 points 32.727° apart
    # (tests/data/orca_cclib/dvb_scan_relaxed_orca6.0.out) — the third number is the number of points, the atoms
    # 0-based; Gaussian echoes «D 3 4 9 10 S 12 30.000» and gives 13 points from the value of the geometry
    # (tests/data/gaussian/dvb_scan_relaxed_g16.log) — n steps, n + 1 points. ASSUMPTION: the ORCA input line «B i j =
    # start, end, n» inside «Scan … end» of %geom — from the ORCA manual, not from an echoed input.
    from azimuth.core import SCAN_TASK, coordinate_value
    from modules.spectrum.readers.orca_scan import read_scan

    calc = Calculation(task=SCAN_TASK, scan_end=1.2, scan_steps=6)
    fixed = (('C', (2,)), ('B', (0, 1)))
    text = orca_input(WATER, calc, fixed)
    assert '  Scan\n    B 0 1 = 0.9573, 1.2000, 6\n  end\n' in text and '{ C 2 C }' in text
    assert '{ B 0 1 C }' not in text and '! B3LYP def2-SVP Opt TightSCF' in text
    gaussian = inputs.gaussian_input(WATER, calc, fixed)
    assert 'Opt=(MaxCycles=100,ModRedundant)' in gaussian
    assert gaussian.rstrip().endswith('X 3 F\nB 1 2 S 5 0.0485')  # (1.2 − 0.9573) / 5
    for kind, written in (('orca', text), ('gaussian', gaussian)):
        assert inputs.read_settings(kind, written)['task'] == SCAN_TASK
    # an angle and a dihedral in degrees; the sign of the dihedral is ORCA's (its scan points, measured here)
    angle = orca_input(WATER, Calculation(task=SCAN_TASK, scan_end=120.0, scan_steps=5), (('A', (1, 0, 2)),))
    assert 'A 1 0 2 = 104.51, 120.00, 5' in angle
    scan = read_scan((Path(__file__).parents[1] / 'data' / 'orca_cclib' / 'dvb_scan_relaxed_orca6.0.out').read_text(encoding='utf-8'))
    for point in scan.points[1:4]:
        assert coordinate_value(point.geometry, 'D', scan.coordinates[0].atoms) == pytest.approx(point.values[0], abs=1e-3)
    # what to do when there is nothing to scan, the list changed, or the end is out of range
    for bad, constraints, words in ((calc, (), 'Ограничения оптимизации'),
                                    (replace(calc, scan_index=3), fixed, 'заново'),
                                    (replace(calc, scan_end=20.0), fixed, 'от 0.3 до 10'),
                                    (replace(calc, scan_end=0.9573), fixed, 'совпадает')):
        with pytest.raises(ValueError, match=words):
            orca_input(WATER, bad, constraints)
    assert SCAN_TASK in inputs.tasks_for('orca') and SCAN_TASK in inputs.tasks_for('gaussian')
    assert all(SCAN_TASK not in inputs.tasks_for(kind) for kind in ('psi4', 'mopac'))
    assert SCAN_TASK in inputs.tasks_for('xtb')  # $scan в xcontrol
    assert inputs.task_options('orca', SCAN_TASK)[-7:] == ('scan_index', 'scan_end', 'scan_steps', 'scan2_index',
                                                         'scan2_end', 'scan2_steps', 'guess')  # the 2D scan
    assert 'ts' not in inputs.task_options('orca', SCAN_TASK)


def test_orca_starts_from_the_orbitals_of_an_earlier_calculation():
    # «! … MORead» and «%moinp "start-orbitals.gbw"» (ORCA manual: MORead with %moinp naming the .gbw; the
    # name differs from the job's own .gbw, which ORCA would overwrite); only a .gbw is taken
    from azimuth.core import GUESS_FILE

    text = orca_input(WATER, Calculation(task='Энергия', guess='/x/earlier.gbw'))
    assert text.splitlines()[1] == '! B3LYP def2-SVP TightSCF MORead' and f'%moinp "{GUESS_FILE}"\n' in text
    assert 'MORead' not in orca_input(WATER, Calculation(task='Энергия'))
    for bad in ('/x/earlier.out', 'a\nb.gbw', 5):
        with pytest.raises(ValueError, match='gbw'):
            orca_input(WATER, Calculation(guess=bad))
    assert inputs.task_options('orca', 'Энергия')[-1] == 'guess' and 'guess' not in inputs.task_options('gaussian', 'Энергия')


def test_relativistic_basis_sets_of_orca():
    # a student's report — «! B3LYP def2-TZVP TightSCF DKH» for ZnCl2; ORCA 6 wants the relativistic version
    # by its prefix (manual 6.1, 2.12), as the Atlas topic «Тяжёлые элементы» teaches
    from azimuth.core import read_xyz

    zncl2 = read_xyz('3\nZnCl2\nZn 0 0 0\nCl 0 0 2.07\nCl 0 0 -2.07')
    line = lambda **k: orca_input(zncl2, Calculation(task='Энергия', basis='def2-TZVP', **k)).splitlines()[1]
    assert line(relativistic='DKH') == '! B3LYP DKH-def2-TZVP TightSCF SARC/J DKH'
    assert line(relativistic='ZORA') == '! B3LYP ZORA-def2-TZVP TightSCF SARC/J ZORA'
    assert line(relativistic='X2C') == '! B3LYP x2c-TZVPall TightSCF X2C'
    assert line() == '! B3LYP def2-TZVP TightSCF'
    assert 'SARC/J' not in line(relativistic='DKH', no_ri=True)
    with pytest.raises(ValueError, match='def2-TZVP'):
        orca_input(zncl2, Calculation(task='Энергия', basis='6-31G*', relativistic='DKH'))
    with pytest.raises(ValueError):
        orca_input(zncl2, Calculation(task='Энергия', basis='def2-TZVPD', relativistic='ZORA'))


def test_heavy_elements():
    # a student's report — «Элементы тяжелее Kr не поддерживаются вообще» (Y, Bi, Ac, the lanthanides). def2
    # with its ECP up to Rn (ORCA and Gaussian take it with the basis), SARC for the heavy atoms with DKH and ZORA, x2c
    # up to Rn; refused where a program has no basis (oracle: the Atlas topic «Тяжёлые элементы», ORCA 6.1 manual 2.12)
    from azimuth.core import read_xyz

    ycl3 = read_xyz('4\nYCl3\nY 0 0 0\nCl 2.4 0 0\nCl -1.2 2.08 0\nCl -1.2 -2.08 0')
    auh = read_xyz('2\nAuH\nAu 0 0 0\nH 0 0 1.52')
    eucl2 = read_xyz('3\nEuCl2\nEu 0 0 0\nCl 0 0 2.6\nCl 0 0 -2.6')
    energy = lambda **k: Calculation(task='Энергия', **k)
    assert orca_input(ycl3, energy()).splitlines()[1] == '! B3LYP def2-SVP TightSCF'
    assert inputs.gaussian_input(ycl3, energy()).splitlines()[2].startswith('#P B3LYP/def2SVP')
    assert '! B3LYP x2c-SVPall TightSCF X2C' in orca_input(ycl3, energy(relativistic='X2C'))
    zora = orca_input(auh, energy(relativistic='ZORA', basis='def2-TZVP'))
    assert '! B3LYP ZORA-def2-TZVP TightSCF SARC/J ZORA' in zora and '%basis\n  NewGTO Au "SARC-ZORA-TZVP" end\nend\n' in zora
    dkh = orca_input(eucl2, energy(relativistic='DKH', multiplicity=8))
    assert '  NewGTO Eu "SARC-DKH-TZVP" end\n' in dkh and 'NewGTO Cl' not in dkh
    # SARC also for Rb–Ba (the ORCA 6.1 manual: «Rb--Rn, Ac--Lr»), before refused
    assert '  NewGTO Y "SARC-DKH-TZVP" end\n' in orca_input(ycl3, energy(relativistic='DKH'))
    for molecule, calc in ((eucl2, energy(multiplicity=8)),  # no def2 ECP for Ce–Lu
                           (eucl2, energy(relativistic='X2C', multiplicity=8)),  # x2c: H–Rn without Ce–Lu
                           (auh, energy(relativistic='DKH', basis='cc-pVDZ'))):  # cc-pVnZ-DK: not for Au here
        with pytest.raises(ValueError):
            orca_input(molecule, calc)
    with pytest.raises(ValueError, match='Gaussian'):
        inputs.gaussian_input(auh, energy(relativistic='DKH'))
    assert 'PM7' in inputs.mopac_input(ycl3, energy(method='PM7'))
    with pytest.raises(ValueError, match='не параметризован'):
        inputs.mopac_input(ycl3, energy(method='AM1'))


def test_element_bases():
    # own basis sets of elements — ORCA %basis NewGTO (with NewECP def2-ECP for a heavy element under a basis
    # that is not def2), Gaussian Gen (built-in names, «****»), Psi4 basis { assign }; oracles: the manuals of ORCA 6
    # (%basis NewGTO/NewECP), Gaussian 16 (Gen, basis set input after the coordinates), Psi4 1.7 (basis blocks)
    from azimuth.core import element_basis_text, element_bases, read_xyz

    assert element_bases('fe: def2-tzvp,  Cl=def2-SVP\n') == {'Fe': 'def2-TZVP', 'Cl': 'def2-SVP'}
    assert element_basis_text({'Fe': 'def2-TZVP', 'Cl': 'def2-SVP'}) == 'Cl=def2-SVP; Fe=def2-TZVP'
    for bad in ('Fe', 'Qq=def2-SVP', 'Fe=def2-XYZ', 'Fe=def2-SVP; Fe=def2-TZVP'):
        with pytest.raises(ValueError):
            element_bases(bad)
    fecl2 = read_xyz('3\nFeCl2\nFe 0 0 0\nCl 0 0 2.1\nCl 0 0 -2.1')
    calc = Calculation(task='Энергия', basis='6-31G*', element_basis='Fe=def2-TZVP; Cl=def2-SVP', multiplicity=5)
    orca = orca_input(fecl2, calc)
    assert '! B3LYP 6-31G* TightSCF' in orca and '%basis\n  NewGTO Cl "def2-SVP" end\n  NewGTO Fe "def2-TZVP" end\nend\n' in orca
    g = inputs.gaussian_input(fecl2, calc)
    assert '#P B3LYP/Gen ' in g and g.endswith('\nCl 0\ndef2SVP\n****\nFe 0\ndef2TZVP\n****\n\n')
    p = inputs.psi4_input(fecl2, calc)
    assert 'basis {\n  assign 6-31g*\n  assign Cl def2-svp\n  assign Fe def2-tzvp\n}\n' in p and '  basis 6-31g*' not in p
    # an element absent from the molecule is ignored; the main basis no longer has to fit an element with its own
    water = read_xyz('3\nwater\nO 0 0 0.117\nH 0.757 0 -0.469\nH -0.757 0 -0.469')
    assert '%basis' not in orca_input(water, Calculation(element_basis='Fe=def2-TZVP'))
    yh2 = read_xyz('3\nYH2\nY 0 0 0\nH 0 0 2.0\nH 0 0 -2.0')
    with pytest.raises(ValueError):
        orca_input(yh2, Calculation(task='Энергия', basis='6-31G*', multiplicity=2))
    y = orca_input(yh2, Calculation(task='Энергия', basis='6-31G*', element_basis='Y=def2-TZVP', multiplicity=2))
    assert '  NewGTO Y "def2-TZVP" end\n  NewECP Y "def2-ECP" end\n' in y
    with pytest.raises(ValueError, match='Gaussian'):
        inputs.gaussian_input(yh2, Calculation(task='Энергия', element_basis='H=def2-TZVP', multiplicity=2))
    # with a Hamiltonian: the recontracted version for a light element, a heavy one keeps SARC
    auh = read_xyz('2\nAuH\nAu 0 0 0\nH 0 0 1.52')
    zora = orca_input(auh, Calculation(task='Энергия', relativistic='ZORA', element_basis='H=def2-TZVP'))
    assert '  NewGTO H "ZORA-def2-TZVP" end\n  NewGTO Au "SARC-ZORA-TZVP" end\n' in zora
    with pytest.raises(ValueError):
        orca_input(auh, Calculation(task='Энергия', relativistic='ZORA', element_basis='Au=def2-TZVP'))


def test_advice_for_heavy_elements():
    # the 4d/5d metals are metals; the lanthanides get DKH2 (ORCA; SARC on them) and no diffuse basis
    from azimuth.core import read_xyz
    from modules.sextant import advice

    eucl2 = read_xyz('3\nEuCl2\nEu 0 0 0\nCl 0 0 2.6\nCl 0 0 -2.6')
    ptcl2 = read_xyz('3\nPtCl2\nPt 0 0 0\nCl 0 0 2.3\nCl 0 0 -2.3')
    found = advice.recommend(eucl2, 'Энергия', 'orca', 0, 8)
    assert found.relativistic == 'DKH' and found.basis == 'def2-TZVP' and 'SARC' in found.text
    orca_input(eucl2, Calculation(found.method, found.basis, 'Энергия', dispersion=found.dispersion,
                                  relativistic=found.relativistic, multiplicity=8))  # the advice gives a valid input
    anion = advice.recommend(eucl2, 'Оптимизация', 'orca', -1, 7)
    assert anion.basis == 'def2-SVP' and 'диффузных версий DKH-def2 нет' in anion.text
    assert 'выберите ORCA' in advice.recommend(eucl2, 'Энергия', 'gaussian', 0, 8).text
    pt = advice.recommend(ptcl2, 'Оптимизация + частоты', 'orca', 0, 1)
    assert pt.method == 'TPSSh' and pt.relativistic == '' and 'псевдопотенциал' in pt.text


def test_gamess_nwchem_and_crest_are_offered_only_what_they_do():
    # GAMESS and NWChem write every task of their list and refuse the others (cc-pVDZ: GAMESS has no def2 sets);
    # CREST does one thing, its conformer search — no other task, no chain of tasks
    from azimuth.core import TASKS, Calculation, read_xyz
    from modules.sextant import chain

    water = read_xyz('3\nw\nO 0 0 0.117\nH 0 0.757 -0.467\nH 0 -0.757 -0.467\n')
    for kind in ('gamess', 'nwchem'):
        offered = inputs.tasks_for(kind)
        for task in TASKS:
            calc = Calculation(method='B3LYP', basis='cc-pVDZ', task=task)
            if task in offered:
                assert inputs.preview(kind, water, calc), (kind, task)
            else:
                with pytest.raises(ValueError):
                    inputs.preview(kind, water, calc)
    assert inputs.tasks_for('crest') == ('Оптимизация',)
    assert inputs.task_title('crest', 'Оптимизация') == 'Поиск конформеров (iMTD-GC)'
    assert inputs.task_title('orca', 'Оптимизация') == 'Оптимизация'
    assert not [key for key in chain.PRESETS if chain.available(key, 'crest')]
    for kind in inputs.KINDS:  # a chain is offered only of tasks its program has
        for key in chain.PRESETS:
            if chain.available(key, kind):
                assert all(task in inputs.tasks_for(kind) for task, _ in chain.PRESETS[key][1]), (kind, key)


def test_psi4_is_not_written_with_less_memory_than_it_starts_with():
    # Psi4 1.11 stops at once with «set_memory(): Requested 1.91e+02 MiB (2e+02 MB); minimum 250 MiB (263 MB)» — 100 MB
    # per process on 2 processes, the least Sextant lets one choose (benzene MP2/def2-TZVP, 2026-11-22). The limit is of
    # the whole calculation: 264 MB on one process is written
    with pytest.raises(ValueError, match='264 МБ на весь расчёт .сейчас 200 МБ.'):
        inputs.psi4_input(WATER, Calculation(task='Энергия', cores=2, memory_mb=100))
    assert 'memory 264 mb' in inputs.psi4_input(WATER, Calculation(task='Энергия', cores=1, memory_mb=264))
    assert 'memory 400 mb' in inputs.psi4_input(WATER, Calculation(task='Энергия', cores=4, memory_mb=100))
    assert '%maxcore 100' in orca_input(WATER, Calculation(task='Энергия', cores=2, memory_mb=100))  # ORCA runs with it

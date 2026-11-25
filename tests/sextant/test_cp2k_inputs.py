"""The input of CP2K for a crystal and its job on a server.

Oracles: the sections of the manual of CP2K (GLOBAL, FORCE_EVAL/DFT/SCF/OT or SMEAR, XC/VDW_POTENTIAL, SUBSYS/CELL,
COORD SCALED, KIND, MOTION) written by hand for silicon — the cell vectors are those of crystal.Cell, the fractions
those of the file; a metal (Cu) gets the smearing, an element without the basis set — an error.
"""

import pytest

from modules.compass.chemistry import crystal as cr
from modules.sextant import cluster, cp2k_inputs as ci, install_tools
from tests.sextant.test_qe_inputs import silicon


def test_the_input_of_silicon():
    text = ci.cp2k_input(silicon(), 'Энергия')
    assert '  RUN_TYPE ENERGY' in text and '    BASIS_SET_FILE_NAME BASIS_MOLOPT' in text
    assert '      &OT' in text and '&SMEAR' not in text  # an insulator: the orbital transformation
    assert "          TYPE DFTD3(BJ)" in text and '      CUTOFF 400' in text and '      REL_CUTOFF 50' in text
    assert '      A     5.43100000     0.00000000     0.00000000' in text
    assert text.count('      Si ') == 8 and '      SCALED' in text
    assert '    &KIND Si\n      BASIS_SET DZVP-MOLOPT-SR-GTH\n      POTENTIAL GTH-PBE\n    &END KIND' in text
    assert '&MOTION' not in text
    lines = [line.strip() for line in text.splitlines()]
    opened = [line[1:].split()[0] for line in lines if line.startswith('&') and not line.startswith('&END')]
    closed = [line.split()[1] for line in lines if line.startswith('&END')]
    assert sorted(opened) == sorted(closed)  # every section is closed


def test_a_cell_optimisation_and_a_metal():
    text = ci.cp2k_input(silicon(), 'Оптимизация с ячейкой', ci.Options(vdw='', max_iter=50))
    assert '  RUN_TYPE CELL_OPT' in text and '  STRESS_TENSOR ANALYTICAL' in text and 'VDW_POTENTIAL' not in text
    assert '  &CELL_OPT\n    OPTIMIZER BFGS\n    MAX_ITER 50' in text
    copper = cr.Crystal('Cu', cr.Cell(3.61, 3.61, 3.61), (cr.Site('Cu1', 'Cu', 0, 0, 0),),
                        tuple(cr.operation(o) for o in ('x, y, z', 'x, y+1/2, z+1/2', 'x+1/2, y, z+1/2', 'x+1/2, y+1/2, z')),
                        'F m -3 m')
    metal = ci.cp2k_input(copper)
    assert '&SMEAR ON' in metal and 'ADDED_MOS 20' in metal and '&OT' not in metal
    gadolinium = cr.Crystal('Gd', cr.Cell(3.6, 3.6, 5.8, 90, 90, 120), (cr.Site('Gd1', 'Gd', 0, 0, 0),),
                            (cr.operation('x, y, z'),), 'P 1')
    with pytest.raises(ValueError):
        ci.cp2k_input(gadolinium)
    with pytest.raises(ValueError):
        ci.cp2k_input(copper, options=ci.Options(basis='TZV2P-MOLOPT-GTH'))


def test_the_job_on_a_server_and_the_installation():
    plan = cluster.Plan(processes=8, maxcore=1500, mem_request=None, physical=48, physical_free=40, queued=False)
    script = cluster.job_script(plan, 'module load cp2k/2025.1', 'az-cp2k-Si', 'pw', 'cp2k')
    assert '#SBATCH -n 8' in script and 'module load cp2k/2025.1' in script
    assert 'command -v cp2k.psmp' in script and '"$CP2K" -i azimuth.inp > cp2k.out 2>&1' in script
    found = cluster.parse_probe('@progmodule cp2k/2025.1\n')
    assert cluster.find_on_server(found, 'cp2k') is not None and cluster.suggested_setup(found, 'cp2k') == 'module load cp2k/2025.1'
    assert install_tools.cp2k_installable('Linux') and install_tools.cp2k_installable('Darwin')
    assert not install_tools.cp2k_installable('Windows')
    assert install_tools.cp2k_by_brew('Darwin') and not install_tools.cp2k_by_brew('Linux')
    assert install_tools.command('mamba', '/r', ['cp2k'])[-1] == 'cp2k'


def test_cp2k_of_homebrew_on_a_mac(tmp_path, monkeypatch, capsys):
    # «Установить программы для расчёта…» → CP2K on a Mac runs
    # «brew install cp2k» and checks that cp2k starts; no Homebrew — what to do, no installation
    import os
    import stat
    import sys

    if os.name == 'nt':
        return
    bin_dir = tmp_path / 'brew' / 'bin'
    bin_dir.mkdir(parents=True)
    brew = bin_dir / 'brew'
    brew.write_text(f'#!{sys.executable}\nimport sys, pathlib\nd = pathlib.Path({str(bin_dir)!r})\n'
                    "(d / 'asked').write_text(' '.join(sys.argv[1:]))\n"
                    "p = d / 'cp2k.psmp'\np.write_text('#!/bin/sh\\necho \" CP2K version 2026.2\"\\n')\np.chmod(0o755)\n",
                    encoding='utf-8')
    brew.chmod(brew.stat().st_mode | stat.S_IXUSR)
    monkeypatch.setattr(install_tools, 'CP2K_DIRS', (str(bin_dir),))
    monkeypatch.setattr(install_tools, 'default_root', lambda: tmp_path / 'root')
    monkeypatch.setattr(install_tools, 'BREW_PATHS', (str(brew),))
    monkeypatch.setattr(install_tools.platform, 'system', lambda: 'Darwin')
    monkeypatch.setattr(install_tools.shutil, 'which', lambda name, *a, **k: None)
    assert install_tools.main(['cp2k', '--root', str(tmp_path / 'root')]) == 0
    assert (bin_dir / 'asked').read_text() == 'install cp2k'
    assert 'CP2K version 2026.2' in capsys.readouterr().out
    monkeypatch.setattr(install_tools, 'BREW_PATHS', ())
    assert install_tools.install_cp2k_brew() == 1 and 'https://brew.sh' in capsys.readouterr().out


def test_the_wave_function_is_always_written():
    # &MO_MOLDEN in &DFT for every task
    for task in ci.TASKS:
        if ci.TASKS[task] == 'VIBRATIONAL_ANALYSIS':  # the displaced cells of the frequencies — none
            continue
        text = ci.cp2k_input(silicon(), task)
        dft = text[text.index('  &DFT'):text.index('  &END DFT')]
        assert '&MO_MOLDEN' in dft and 'GTO_KIND SPHERICAL' in dft and 'NDIGITS 9' in dft
    assert ci.MOLDEN == 'azimuth-MOS-1_0.molden'


def test_the_projected_dos_is_printed():
    # the PDOS with the empty levels (NLUMO 4 per atom); an optimization — at its last step only.
    # CP2K 2026.2 stopped on «unknown subsection PDOS of section PRINT» — &PDOS lives inside &DOS there
    # (src/input_cp2k_print_dft.F of v2026.2: the print key DOS, add_dos_keywords — NLUMO, then the section PDOS)
    energy = ci.cp2k_input(silicon(), 'Энергия')
    assert ('    &PRINT\n      &MO_MOLDEN\n        NDIGITS 9\n        GTO_KIND SPHERICAL\n      &END MO_MOLDEN\n      &DOS\n'
            '        NLUMO 32\n        &PDOS\n          COMPONENTS F\n        &END PDOS\n      &END DOS\n    &END PRINT\n') in energy
    relax = ci.cp2k_input(silicon(), 'Оптимизация с ячейкой')
    block = relax[relax.index('&DOS'):relax.index('&END DOS')]
    assert 'ADD_LAST NUMERIC' in block and 'CELL_OPT 0' in block and block.index('&EACH') < block.index('&PDOS')


def test_a_salt_is_no_metal():
    # CsCl was smeared as a metal (its Cs) — and CP2K at the Γ point blew its cell up by 28 %
    from modules.compass.chemistry import crystal_symmetry as cs

    assert cs.is_metal({'Cu'}) and cs.is_metal({'Cu', 'Zn'}) and not cs.is_metal({'Cs', 'Cl'})
    assert not cs.is_metal({'Na', 'Cl'}) and not cs.is_metal({'C', 'H', 'O'}) and not cs.is_metal(set())


def test_the_frequencies_at_gamma():
    # VIBRATIONAL_ANALYSIS with the modes in Molden format, the cell
    # periodic (no rotations removed), a tight SCF, no orbitals or PDOS at the displaced cells
    text = ci.cp2k_input(silicon(), 'Частоты (точка Γ)')
    assert 'RUN_TYPE VIBRATIONAL_ANALYSIS' in text and 'FULLY_PERIODIC T' in text and '&MOLDEN_VIB' in text
    assert 'EPS_SCF 1.0E-08' in text and '&MO_MOLDEN' not in text and '&PDOS' not in text and '&DOS' not in text
    assert ci.VIBRATIONS == 'azimuth-VIBRATIONS-1.mol'


def test_the_charge_of_the_cell():
    # CHARGE of &DFT; an odd number of electrons (Z of Si 14 × 8 = 112, a charge of +1 — 111) — UKS with
    # MULTIPLICITY 2 (the GTH cores hold even numbers of electrons, so the parity is that of Z − q)
    text = ci.cp2k_input(silicon(), 'Энергия', ci.Options(charge=1))
    assert '    CHARGE 1' in text and '    UKS' in text and '    MULTIPLICITY 2' in text
    even = ci.cp2k_input(silicon(), 'Энергия', ci.Options(charge=2))
    assert '    CHARGE 2' in even and 'UKS' not in even and 'MULTIPLICITY' not in even
    assert '    CHARGE 0' in ci.cp2k_input(silicon(), 'Энергия')


def test_the_functionals_and_the_full_molopt_bases():
    # 0.183.0 — CP2K, read &PBE PARAMETRIZATION ORIG | revPBE | PBEsol (src/input_cp2k_xc.F); D3 and D3(BJ)
    # parameters of PBE, PBESOL, REVPBE, BLYP (qs_scaling_dftd3, qs_scaling_dftd3bj of src/qs_dispersion_utils.F);
    # GTH-BLYP of Si and of Na in data/GTH_POTENTIALS, none for Cs; the full MOLOPT sets in data/BASIS_MOLOPT — the nine
    # elements H C N O F Si P S Cl
    plain = ci.cp2k_input(silicon())
    assert '      &XC_FUNCTIONAL PBE\n      &END XC_FUNCTIONAL' in plain and 'REFERENCE_FUNCTIONAL PBE\n' in plain
    for name in ('PBESOL', 'REVPBE'):
        text = ci.cp2k_input(silicon(), options=ci.Options(functional=name))
        assert (f'      &XC_FUNCTIONAL\n        &PBE\n          PARAMETRIZATION {name}\n        &END PBE\n'
                '      &END XC_FUNCTIONAL') in text
        assert f'REFERENCE_FUNCTIONAL {name}\n' in text and 'POTENTIAL GTH-PBE\n' in text
    blyp = ci.cp2k_input(silicon(), options=ci.Options(functional='BLYP'))
    assert '      &XC_FUNCTIONAL BLYP\n' in blyp and 'POTENTIAL GTH-BLYP\n' in blyp and 'REFERENCE_FUNCTIONAL BLYP\n' in blyp
    caesium = cr.Crystal('CsCl', cr.Cell(4.12, 4.12, 4.12), (cr.Site('Cs1', 'Cs', 0, 0, 0), cr.Site('Cl1', 'Cl', .5, .5, .5)),
                         (cr.operation('x, y, z'),), 'P 1')
    assert 'POTENTIAL GTH-PBE' in ci.cp2k_input(caesium)
    with pytest.raises(ValueError):
        ci.cp2k_input(caesium, options=ci.Options(functional='BLYP'))
    with pytest.raises(ValueError):
        ci.cp2k_input(silicon(), options=ci.Options(functional='B3LYP'))
    for basis in ('DZVP-MOLOPT-GTH', 'TZVP-MOLOPT-GTH', 'TZV2P-MOLOPT-GTH'):
        assert f'BASIS_SET {basis}\n' in ci.cp2k_input(silicon(), options=ci.Options(basis=basis))
    salt = cr.Crystal('NaCl', cr.Cell(5.64, 5.64, 5.64), (cr.Site('Na1', 'Na', 0, 0, 0), cr.Site('Cl1', 'Cl', .5, .5, .5)),
                      (cr.operation('x, y, z'),), 'P 1')
    assert 'BASIS_SET DZVP-MOLOPT-SR-GTH' in ci.cp2k_input(salt)
    with pytest.raises(ValueError):  # TZV2P was offered for Na: CP2K found no such basis
        ci.cp2k_input(salt, options=ci.Options(basis='TZV2P-MOLOPT-GTH'))


def test_periodic_gfn1_xtb():
    # as tests/xTB/regtest-1/si_geo.inp of CP2K (DO_EWALD left out — deprecated in 2026.2): &QS METHOD xTB with &XTB and
    # DISPERSION_PARAMETER_FILE dftd3.dat, &POISSON &EWALD SPME ALPHA 1.0 GMAX 25 for silicon (a = 5.431 Å)
    text = ci.cp2k_input(silicon(), 'Оптимизация с ячейкой', ci.Options(functional='GFN1-XTB'))
    assert ('    &POISSON\n      &EWALD\n        EWALD_TYPE SPME\n        ALPHA 1.0\n        GMAX 25 25 25\n      &END EWALD\n'
            '    &END POISSON\n    &QS\n      METHOD xTB\n      &XTB\n        &PARAMETER\n'
            '          DISPERSION_PARAMETER_FILE dftd3.dat\n        &END PARAMETER\n      &END XTB\n    &END QS\n') in text
    assert '        METHOD DIRECT_P_MIXING' in text and '      SCF_GUESS MOPAC' in text and '  STRESS_TENSOR ANALYTICAL' in text
    for absent in ('BASIS_SET', 'POTENTIAL', '&XC', '&KIND', 'MO_MOLDEN', 'VDW_POTENTIAL', '&MGRID', '&OT'):
        assert absent not in text, absent
    # a cell of 11 Å: GMAX ⌈25 × 11 / 5.431⌉ = 51 (odd); of 6 Å: 28 → 29
    assert ci.ewald_gmax(cr.Cell(11.0, 6.0, 5.431)) == (51, 29, 25)
    gadolinium = cr.Crystal('Gd', cr.Cell(3.6, 3.6, 5.8, 90, 90, 120), (cr.Site('Gd1', 'Gd', 0, 0, 0),),
                            (cr.operation('x, y, z'),), 'P 1')
    metal = ci.cp2k_input(gadolinium, options=ci.Options(functional='GFN1-XTB'))  # no DZVP for Gd — xTB has it
    assert '&SMEAR ON' in metal and 'ADDED_MOS 20' in metal
    from modules.sextant import hubbard

    with pytest.raises(ValueError):
        ci.cp2k_input(silicon(), options=ci.Options(functional='GFN1-XTB', hubbard=hubbard.parse('Ni 5')))


def test_the_pressure_on_the_cell():
    # EXTERNAL_PRESSURE of CELL_OPT, bar
    text = ci.cp2k_input(silicon(), 'Оптимизация с ячейкой', ci.Options(external=3.5))
    assert '    EXTERNAL_PRESSURE [bar] 35000' in text
    assert 'EXTERNAL_PRESSURE' not in ci.cp2k_input(silicon(), 'Оптимизация атомов', ci.Options(external=3.5))


def test_cp2k_starts_through_mpirun_first():
    # serv3, 2026-11-23: the Open MPI of the toolchain of CP2K has no PMI of SLURM — under «srun -n 4» every process
    # stopped in MPI_Init; «mpirun -np 4» ran (Si8, PBE-D3(BJ): −31.208273 Eh). srun stays for a server without mpirun
    lines = '\n'.join(cluster.cp2k_lines(4))
    assert 'RUN="mpirun -np 4"' in lines and 'RUN="srun -n 4"' in lines
    assert lines.index('mpirun -np 4') < lines.index('srun -n 4')
    assert 'mpirun' not in '\n'.join(cluster.cp2k_lines(1)).split('else RUN=""')[1]  # one process: the program itself


def test_quantum_espresso_starts_through_mpirun_first():
    # serv3, 2026-11-23 (pw.x 7.6 of conda-forge): «srun -n 4» started four separate copies of pw.x, each with one MPI
    # process, into one pw.out; «mpirun -np 4» — one run of four (Si8: −91.35816549 Ry either way, 9 s instead of 28)
    lines = '\n'.join(cluster.qe_lines(4, (('pw.in', 'pw.x'),)))
    assert lines.index('RUN="mpirun -np 4"') < lines.index('RUN="srun -n 4"')
    assert '$RUN "$PW" -in pw.in >> pw.out' in lines

"""The reader of CP2K (modules/spectrum/readers/cp2k.py) on the files written by hand in tests/data/cp2k.

Oracles: the numbers written into those files — three energies (hartree), two steps, the last cell 5.47 Å, the last
frame the diamond structure (fractions 0, ¼, ½, ¾).
"""

from pathlib import Path

from modules.spectrum.readers import cp2k, qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'cp2k'


def test_a_cell_optimisation():
    r = cp2k.read((DATA / 'cellopt.out').read_text(encoding='utf-8'), DATA)
    assert r.version == 'CP2K version 2026.2' and r.nat == 8 and r.done and not r.error
    assert r.energy_hartree == -31.5813 and r.energy == -63.1626 and len(r.energies) == 3
    assert r.steps == 2 and r.converged
    assert r.cell == ((5.47, 0.0, 0.0), (0.0, 5.47, 0.0), (0.0, 0.0, 5.47))
    assert r.atoms[4][0] == 'Si' and all(abs(f - 0.25) < 1e-9 for f in r.atoms[4][1])
    crystal = qe.final_crystal(r, 'Si (CP2K)')
    assert crystal is not None and abs(crystal.cell.a - 5.47) < 1e-9 and len(crystal.sites) == 8


def test_an_error():
    text = ' CP2K| version string:   CP2K version 2026.2\n PROGRAM STARTED AT 2026\n' \
           ' *******************************************************************************\n' \
           ' *   ___                                                                       *\n' \
           ' *  [ABORT]                                                                    *\n' \
           ' *  The basis set DZVP-MOLOPT-SR-GTH for the kind Gd was not found            *\n' \
           ' *******************************************************************************\n'
    r = cp2k.read(text)
    assert not r.done and 'Gd was not found' in r.error and r.energy is None


def test_a_real_energy_of_cscl():
    # a real run (CP2K 2026.2 of Homebrew, macOS): an ENERGY of CsCl of the examples;
    # oracle — the line of CP2K itself, −35.102402520934618 hartree, and its «SCF run converged in 16 steps»
    from modules.sextant import runner

    text = (DATA / 'cscl_energy_2026.2.out').read_text(encoding='utf-8')
    r = cp2k.read(text)
    assert r.version == 'CP2K version 2026.2' and r.nat == 2
    assert r.energy_hartree == -35.102402520934618 and abs(r.energy - 2 * -35.102402520934618) < 1e-12
    assert r.converged and r.done and not r.error and r.steps == 0
    assert runner.finished_normally('cp2k', text, 0)
    # an energy whose SCF did not converge is not «converged»
    assert not cp2k.read(text.replace('SCF run converged', 'SCF run NOT converged')).converged


def test_the_progress_of_a_run():
    # what the card of a running calculation says — oracle: the lines of the real output (step 4 of the SCF
    # of CsCl, −35.0300624697 hartree, change −1.99; its last step 16)
    text = (DATA / 'cscl_energy_2026.2.out').read_text(encoding='utf-8')
    half = cp2k.progress(text[:text.index('     5 Broy')])
    assert half['scf_step'] == 4 and half['scf_energy'] == -35.0300624697 and half['scf_change'] == -1.99
    assert half['scf_converged'] == 0 and half['opt_step'] == 0 and half['scf_method'] == 'Broy./Diag.'
    whole = cp2k.progress(text)
    assert whole['scf_step'] == 16 and whole['scf_converged'] == 1
    ot = '     9 OT DIIS     0.80E-01    3.3     0.00430207      -301.1140011848 -1.38E-01\n'
    assert cp2k.progress(ot)['scf_method'] == 'OT DIIS' and cp2k.progress(ot)['scf_energy'] == -301.1140011848
    assert cp2k.progress(' OPTIMIZATION STEP:      3\n')['opt_step'] == 3 and cp2k.progress('') == {'scf_converged': 0, 'opt_step': 0}


def test_the_progress_lines_of_the_card():
    # the line of the card while CP2K or pw.x runs (QePanel.progress_parts) — from the real outputs
    from types import SimpleNamespace

    from modules.compass.actions.qe_window import QePanel

    text = (DATA / 'cscl_energy_2026.2.out').read_text(encoding='utf-8')
    half = text[:text.index('     5 Broy')]
    said = QePanel.progress_parts(SimpleNamespace(program='cp2k'), half, cp2k.read(half))
    assert said == ['SCF: шаг 4, E = -35.03006247 Eh, ΔE = -2.0e+00']
    vc = (DATA.parent / 'qe' / 'si2_vcrelax_pw76.out').read_text(encoding='utf-8')
    running = vc[:vc.index('number of bfgs steps    =   1') + 40]
    said = QePanel.progress_parts(SimpleNamespace(program='qe'), running, qe.read(running))
    assert said[0] == 'шаг оптимизации 2' and said[1].startswith('SCF: итерация ') and 'Ry' in said[1]


def test_the_words_of_a_real_abort():
    # a real CELL_OPT refused by CP2K 2026.2 (MOTION/CELL_OPT/TYPE); the message is the
    # text of its box, without the picture at the left and the place in its sources (it read «… O/| / \ input_….F:262»)
    text = (DATA / 'cellopt_type_abort_2026.2.out').read_text(encoding='utf-8')
    r = cp2k.read(text)
    assert not r.done and r.energy is None
    assert r.error == ("The specified keyword 'TYPE' is not available anymore: The keyword MOTION/CELL_OPT/TYPE has been "
                       "removed because cell optimizations now always use DIRECT_CELL_OPT.")


def test_the_wave_function_for_multiwfn(tmp_path):
    # the real CELL_OPT of CsCl (CP2K 2026.2) wrote a Molden file at each step; the one of the end (1_9) gets
    # [Cell] — the last row of azimuth-1.cell, a = 5.2841042 Å — and [Nval] — Cs 9, Cl 7 (GTH-PBE-q9, -q7; 16 electrons,
    # as «Number of electrons: 16» of cp2k.out) before it (T. Lu, sobereva.com/651)
    import shutil

    for item in (DATA / 'cscl_cellopt').iterdir():
        shutil.copyfile(item, tmp_path / item.name)
    assert [p.name for p in cp2k.molden_files(tmp_path)] == ['azimuth-MOS-1_8.molden', 'azimuth-MOS-1_9.molden']
    path, why = cp2k.for_multiwfn(tmp_path)
    assert why == '' and path.name == 'azimuth-multiwfn.molden'
    lines = path.read_text(encoding='utf-8').splitlines()
    assert lines[0] == '[Cell]' and [float(x) for x in lines[1].split()] == [5.2841042, 0.0, 0.0]
    assert abs(float(lines[3].split()[2]) - 5.2841042007) < 1e-8
    assert lines[4:7] == ['[Nval]', 'Cs 9', 'Cl 7'] and lines[7].strip() == '[Molden Format]'
    assert '4.992755' in lines[10]  # Cl of the last step (1_8 has 4.992408)
    (tmp_path / 'cp2k.out').write_text('Number of electrons: 18\n', encoding='utf-8')  # another pseudopotential
    path, why = cp2k.for_multiwfn(tmp_path)
    assert path is None and '18' in why and '16' in why
    for item in tmp_path.glob('*.molden'):
        item.unlink()
    assert cp2k.for_multiwfn(tmp_path) == (None, '')

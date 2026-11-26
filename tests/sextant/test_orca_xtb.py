"""GFN2-xTB through ORCA («! XTB2») for a quick reaction path (azimuth/core.py orca_xtb_input, runner.xtb_for_orca).

Oracles: the input of the real run of ORCA 6.0.1 with xtb 6.7.1 behind it (tests/data/orca601/xtb_neb_hcn: HCN → HNC,
NEB-CI, 6 images — converged), the keyword «XTB2» and «ALPB(solvent)» of the ORCA manual; the message of ORCA without
the program xtb («Please set the XTBEXE environment variable», code 52 — the output kept in the same folder); the
energies of the path file ORCA wrote, copied by hand.
"""

from pathlib import Path

import pytest

from azimuth.core import NEB_TASK, XTB_ORCA, Atom, Calculation, Molecule, methods_for, orca_input, read_xyz
from modules.sextant import inputs, runner

RUN = Path(__file__).resolve().parents[1] / 'data' / 'orca601' / 'xtb_neb_hcn'
HCN = read_xyz('3\nHCN\nC 0.000 0.000 0.000\nN 1.156 0.000 0.000\nH -1.064 0.120 0.000')
HNC = read_xyz('3\nHNC\nC 0.000 0.000 0.000\nN 1.170 0.000 0.000\nH 2.165 0.120 0.000')


def calc(**changes):
    return Calculation(**{'method': XTB_ORCA, 'task': NEB_TASK, 'cores': 1, **changes})


def test_the_input_is_the_one_orca_ran():
    text = orca_input(HCN, calc(), (), HNC, 6)
    ran = (RUN / 'hcn_xtb_neb.inp').read_text(encoding='utf-8')
    assert text.splitlines()[1] == '! XTB2 NEB-CI' == ran.splitlines()[1]
    assert '%neb\n  neb_end_xyzfile "end.xyz"\n  nimages 6\nend\n' in text and '%neb' in ran
    assert 'def2' not in text and 'TightSCF' not in text and 'D3' not in text  # no basis set, no SCF of ORCA
    assert list(inputs.input_files('orca', HCN, calc(), (), (HNC, 6))) == ['CHN_GFN2-xTB.inp', 'end.xyz']


def test_energy_optimization_and_the_solvent():
    assert orca_input(HCN, calc(task='Энергия')).splitlines()[1] == '! XTB2'
    text = orca_input(HCN, calc(task='Оптимизация', opt_conv='tight', max_cycles=50, solvent='water'), (('B', (0, 1)),))
    assert text.splitlines()[1] == '! XTB2 Opt TightOpt ALPB(water)'
    assert '{ B 0 1 C }' in text and 'MaxIter 50' in text and 'CPCM' not in text
    with pytest.raises(ValueError, match='ALPB'):
        orca_input(HCN, calc(task='Энергия', solvent='ethanol'))  # no ALPB parameters of ethanol in xtb


def test_what_the_method_is_not_offered_for():
    assert XTB_ORCA in methods_for('orca') and XTB_ORCA not in methods_for('gaussian') and XTB_ORCA not in methods_for('psi4')
    for task in ('Оптимизация + частоты', 'Частоты и термохимия', 'Переходное состояние + частоты', 'ЯМР (экранирование)'):
        with pytest.raises(ValueError, match='GFN2-xTB'):
            orca_input(HCN, calc(task=task))
    for wrong in (dict(ts=True, task='Оптимизация'), dict(relativistic='DKH', task='Энергия'),
                  dict(element_basis='C=def2-TZVP', task='Энергия')):
        with pytest.raises(ValueError):
            orca_input(HCN, calc(**wrong))
    with pytest.raises(ValueError):
        inputs.input_files('gaussian', HCN, calc(task='Энергия'))
    # the method stays chosen when the program is xtb itself: its own tasks are not refused by the rule of ORCA
    assert inputs.input_files('xtb', HCN, calc(task='Оптимизация + частоты'))
    # an element no basis set of the list has is not refused: there is no basis set
    gold = Molecule('AuH', (Atom('Au', 0.0, 0.0, 0.0), Atom('H', 0.0, 0.0, 1.52)))
    assert orca_input(gold, calc(task='Энергия', basis='cc-pVDZ')).splitlines()[1] == '! XTB2'


def test_the_input_is_read_back():
    found = inputs.read_settings('orca', orca_input(HCN, calc(), (), HNC, 6))
    assert found['method'] == XTB_ORCA and found['task'] == NEB_TASK


def test_orca_is_told_where_xtb_is(tmp_path):
    orca = tmp_path / 'orca' / 'orca'
    orca.parent.mkdir()
    orca.write_text('')
    xtb = tmp_path / 'tools' / 'xtb'
    assert runner.xtb_for_orca(orca, configured=None, environ={'XTBEXE': '/somewhere/xtb'}) is None  # already told
    (orca.parent / 'otool_xtb').write_text('')
    assert runner.xtb_for_orca(orca, environ={}) is None  # ORCA's own copy next to it
    (orca.parent / 'otool_xtb').rename(orca.parent / 'other')
    found = runner.find_program('xtb')
    if found is None:
        with pytest.raises(ValueError, match='xtb'):
            runner.xtb_for_orca(orca, configured=str(xtb), environ={})
    else:
        assert runner.xtb_for_orca(orca, environ={}) == found


def test_the_real_run_and_the_run_without_xtb():
    text = (RUN / 'hcn_xtb_neb.out').read_text(encoding='utf-8')
    assert 'Environment variable XTBEXE for xtb has been set!' in text
    stages = [key for key, _ in runner.milestones('orca', text)]
    assert 'neb' in stages and runner.finished_normally('orca', text, 0)
    without = (RUN / 'hcn_xtb_neb_no_xtb.out').read_text(encoding='utf-8')
    assert 'Please set the XTBEXE environment variable' in without and not runner.finished_normally('orca', without, 52)
    found = runner.diagnose('orca', without, 52)
    assert found and 'xtb' in found[0][0]
    from modules.compass.chemistry.formats import read_xyz_frames

    frames = read_xyz_frames((RUN / 'hcn_xtb_neb_MEP_trj.xyz').read_text(encoding='utf-8'))
    assert len(frames) == 8 and all(len(f.atoms) == 3 for f in frames)  # the two ends and six images
    # «PATH SUMMARY» of the output, by hand: the climbing image is the fourth, −5.38737 Eh, 72.40 kcal/mol over HCN
    import re

    energies = [float(e) for e in re.findall(r'_MEP E\s+(-?\d+\.\d+)', (RUN / 'hcn_xtb_neb_MEP_trj.xyz').read_text(encoding='utf-8'))]
    assert energies.index(max(energies)) == 3 and max(energies) == pytest.approx(-5.38737, abs=1e-5)
    assert (max(energies) - energies[0]) * 627.5094740631 == pytest.approx(72.40, abs=0.01)
    assert '3     0.998      -5.38737     72.40' in text and '<= CI' in text

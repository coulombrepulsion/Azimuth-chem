"""The charge decomposition analysis CDA of Multiwfn (modules/spectrum/wavefunction/multiwfn_cda.py).

Oracles: the outputs of Multiwfn 2026.7.15 recorded on the Mac of the user by tools/record_multiwfn_cda.py
(tests/data/multiwfn/cda_*): H3N→BH3 and OC→BH3 computed by ORCA 6 (B3LYP/def2-SVP) — the complex and the two fragments
at its geometry, Molden files of orca_2mkl kept as cda_<system>_<part>.molden.gz.
"""

import gzip
import re
from pathlib import Path

import pytest

from modules.spectrum.wavefunction import multiwfn
from modules.spectrum.wavefunction import multiwfn_cda as cda
from tests.fake_programs import fake_program, q

MWFN = Path(__file__).parents[1] / 'data' / 'multiwfn'


def text(name):
    return (MWFN / name).read_text(encoding='utf-8', errors='replace')


def test_the_way_through_the_menus_is_that_of_the_record():
    menu = text('cda_nh3bh3_menu.txt')
    assert re.search(r'^\s*16 Charge decomposition analysis \(CDA\)', menu, re.M)
    assert 'How many fragments do you want to define?' in menu
    assert re.search(r'Input \.mwfn/\.fch/\.molden/\.gms file of fragment\s+1', menu)
    assert re.search(r'^\s*-1 Return to main menu', menu, re.M)  # after the result: back, then «q»
    assert cda.answers('frag1.molden', 'frag2.molden') == ('16', '2', 'frag1.molden', 'frag2.molden', '-1', 'q')


def test_ammonia_borane():
    found = cda.parse_cda(text('cda_nh3bh3_menu.txt'))
    s = found['sum']
    assert (s['occ'], s['d'], s['b'], s['d_b'], s['r']) == (18.0, 0.268420, 0.015423, 0.252997, -0.257198)
    assert len(found['orbitals']) == 9 and found['orbitals'][6] == (7, 2.0, 0.166697, 0.046277, 0.120421, -0.498620)
    assert sum(row[2] for row in found['orbitals']) == pytest.approx(s['d'], abs=1e-5)  # the sum is of the rows
    assert found['net'] == 0.4532 and found['ecda'] == {'pl1_ct12': 0.4816, 'pl1_ct21': 0.0284, 'pl2_ct12': 0.5097,
                                                        'pl2_ct21': 0.0565}
    assert cda.main_orbitals(found, 2)[0][0] == 7 and cda.main_orbitals(found, 2)[1][0] == 6  # the B–N σ orbitals


def test_borane_carbonyl_has_back_donation():
    found = cda.parse_cda(text('cda_cobh3_cda.txt'))
    s = found['sum']
    assert (s['d'], s['b'], s['r']) == (0.348270, 0.156425, -0.263004) and found['net'] == 0.3281
    nh3 = cda.parse_cda(text('cda_nh3bh3_cda.txt'))['sum']
    assert s['b'] / s['d'] > 5 * nh3['b'] / nh3['d']  # CO takes electrons back (π), NH3 hardly
    header, rows = cda.table(found)
    assert header[2:] == ['d', 'b', 'd − b', 'r'] and rows[-1][2:4] == ['0.348270', '0.156425']


def test_run_copies_the_three_files_under_ascii_names(tmp_path):
    folder = tmp_path / 'Расчёт с пробелом'
    folder.mkdir()
    paths = []
    for part in ('complex', 'frag1', 'frag2'):
        path = folder / f'{part}.molden.input'
        path.write_bytes(gzip.decompress((MWFN / f'cda_nh3bh3_{part}.molden.gz').read_bytes()))
        paths.append(path)
    recorded = MWFN / 'cda_nh3bh3_menu.txt'
    fake = fake_program(tmp_path / 'bin', f'''
assert args[0] == 'complex.molden', args
assert answers(4) == '16 2 frag1.molden frag2.molden', lines
assert answer(4) == '-1' and answer(5) == 'q'
assert all(os.path.getsize(n) > 1000 for n in ('complex.molden', 'frag1.molden', 'frag2.molden'))
cat({q(recorded)})
''')
    multiwfn.clear_cache()
    found, output = cda.run_cda(fake, paths[0], paths[1:])
    assert found['sum']['d'] == 0.268420 and 'Charge decomposition analysis' in output
    with pytest.raises(ValueError):
        cda.run_cda(fake, paths[0], paths[1:2])
    empty = fake_program(tmp_path / 'bin2', 'echo("Multiwfn Version 2026.7.15 — nothing")')
    multiwfn.clear_cache()
    with pytest.raises(ValueError):
        cda.run_cda(empty, paths[0], paths[1:])
    assert cda.parse_cda('nothing') is None


def test_the_three_calculations():
    """The plan of the queue — fragment 1 the atoms given, fragment 2 the rest; the complex reordered."""
    from azimuth.core import Atom, CDA_TASK, Calculation, Molecule

    # borane carbonyl written acceptor first: B, H, H, H, C, O
    atoms = (Atom('B', 0, 0, 1.53), Atom('H', 1.16, 0, 1.82), Atom('H', -0.58, 1.0, 1.82), Atom('H', -0.58, -1.0, 1.82),
             Atom('C', 0, 0, 0), Atom('O', 0, 0, -1.13))
    molecule = Molecule('H3BCO', atoms)
    calc = Calculation(task=CDA_TASK, cda_atoms='5-6')
    found = cda.plan(molecule, calc)
    assert found['fragments'] == ((4, 5), (0, 1, 2, 3)) and found['order'] == (4, 5, 0, 1, 2, 3)
    keys = [(key, m.formula, q, mult) for key, m, q, mult in found['parts']]
    assert [k[0] for k in keys] == list(cda.PARTS) and keys[1][1:] == ('CO', 0, 1) and keys[2][2:] == (0, 1)
    assert [a.symbol for a in found['parts'][0][1].atoms] == ['C', 'O', 'B', 'H', 'H', 'H']
    for wrong in ('', '1-6', '7'):
        with pytest.raises(ValueError):
            cda.plan(molecule, Calculation(task=CDA_TASK, cda_atoms=wrong))
    with pytest.raises(ValueError):  # BH3 with a charge of +1 and a singlet: an odd number of electrons
        cda.plan(molecule, Calculation(task=CDA_TASK, cda_atoms='5,6', charge=1, cda_charge=0))
    ion = cda.plan(molecule, Calculation(task=CDA_TASK, cda_atoms='5,6', charge=1, multiplicity=2, cda_charge=0,
                                         cda_mult2=2))
    assert ion['parts'][2][2:] == (1, 2)

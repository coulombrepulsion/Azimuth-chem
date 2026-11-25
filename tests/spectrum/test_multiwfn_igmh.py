"""IGMH from Multiwfn (modules/spectrum/wavefunction/multiwfn_igmh.py).

Oracles: the runs recorded with Multiwfn 2026.7.15 by tools/record_multiwfn_igmh.py (ORCA 6.0.1 B3LYP-D3(BJ)/def2-SVP):
the S22 water dimer — the atom pair H3···O4 carries 44.45 % of the δG of the pairs, the sum of the pairs 0.179168 a.u.,
the integral of δg_inter 0.093529 a.u.; benzene···methane with a C–H at the centre of the ring — H14 carries 56 % of the
methane side, every ring carbon about 13.9 % of the benzene side. The way through the menus is that of the source of
Multiwfn (visweak.f90, subroutine IGM) and of the record.
"""

import gzip
from pathlib import Path

import numpy as np
import pytest

from azimuth.core import Atom, Molecule
from modules.spectrum.analysis import nci_domains as nd
from modules.spectrum.readers.cube import read_cube
from modules.spectrum.wavefunction import multiwfn
from modules.spectrum.wavefunction import multiwfn_igmh as igmh
from tests.fake_programs import fake_program, q

MWFN = Path(__file__).parents[1] / 'data' / 'multiwfn'


def recorded(name, what):
    return (MWFN / f'igmh_{name}_{what}').read_text(encoding='utf-8')


def grids(name):
    return [read_cube(gzip.open(MWFN / f'igmh_{name}_{c}.cub.gz', 'rt', encoding='utf-8').read())
            for c in ('sl2r', 'dg_inter')]


def test_the_way_through_the_menus_is_that_of_the_record():
    head = recorded('dimer', 'output.txt').split('\n', 1)[0]
    assert head == 'answers: ' + ' | '.join(igmh.answers([[0, 1, 2], [3, 4, 5]], 'low', (0, 1))[:-1])
    three = igmh.answers([[0], [1, 2], [3]], 'medium', (1, 2), cubes=False)
    assert three == ('20', '11', '3', '1', '2-3', '4', '2', '6', '2,3', '2', 'n', '0', '0', 'q', 'q')
    assert igmh.ranges([6, 0, 1, 2, 9, 10]) == '1-3,7,10-11' and igmh.ranges([4]) == '5'


def test_the_atom_pairs_of_the_water_dimer():
    found = igmh.parse_atmdg(recorded('dimer', 'atmdg.txt'))
    assert found['total'] == 0.179168 and len(found['pairs']) == 9
    assert found['pairs'][0] == (2, 3, 0.079633, 44.45)
    assert found['atoms'][1][0] == (2, 0.119766, 66.85) and found['atoms'][2][0] == (3, 0.117844, 65.77)
    assert sum(p[2] for p in found['pairs']) == pytest.approx(0.179168, abs=1e-5)
    assert igmh.parse_integrals(recorded('dimer', 'output.txt')) == {'dg': 1.100554, 'dg_inter': 0.093529,
                                                                      'dg_intra': 1.007025}
    assert igmh.parse_atmdg('nothing') is None


def test_the_domains_of_igmh_with_their_pairs():
    sign, field = grids('dimer')
    molecule = field.molecule
    pairs = igmh.parse_atmdg(recorded('dimer', 'atmdg.txt'))['pairs']
    found = nd.attach(nd.find(sign, field, kind='igmh'), pairs, molecule)
    assert [d.kind for d in found] == ['hydrogen'] and found[0].site == 2 and found[0].acceptor == 3
    assert -0.035 < found[0].peak < -0.02 and found[0].dg == pytest.approx(0.179166, abs=1e-5)
    symbols = [a.symbol for a in molecule.atoms]
    header, rows = nd.table(found, symbols)
    assert header[-1] == 'δG пар, а. е.' and rows[0][-1] == '0.1792' and 'IGMH' in nd.detail(found[0], symbols)
    assert nd.find(sign, field, kind='igmh', level=0.02)[0].volume < found[0].volume


def test_ch_pi_by_igmh():
    sign, field = grids('benzene_methane')
    molecule = field.molecule
    found = igmh.parse_atmdg(recorded('benzene_methane', 'atmdg.txt'))
    assert found['atoms'][2][0][:2] == (13, 0.201901)  # H14 — the hydrogen pointing at the ring
    assert all(abs(p - 13.9) < 0.1 for _, _, p in found['atoms'][1][:6])  # the six carbons alike
    domains = nd.attach(nd.find(sign, field, kind='igmh'), found['pairs'], molecule)
    assert [d.kind for d in domains] == ['ch-pi'] and (domains[0].donor, domains[0].site) == (12, 13)
    assert domains[0].strength == 'weak' and domains[0].dg > 0.3


def test_fragments_and_contacts():
    rows = [('O', 0, 0, 0), ('H', 0.96, 0, 0), ('H', -0.24, 0.93, 0),
            ('O', 2.9, 0, 0), ('H', 3.2, 0.9, 0), ('H', 3.2, -0.9, 0),
            ('O', 20, 0, 0), ('H', 20.96, 0, 0), ('H', 19.76, 0.93, 0)]
    molecule = Molecule('t', tuple(Atom(s, x, y, z) for s, x, y, z in rows))
    frags = igmh.fragments(molecule)
    assert frags == [[0, 1, 2], [3, 4, 5], [6, 7, 8]] and igmh.in_contact(molecule, frags) == [(0, 1)]
    single = Molecule('w', molecule.atoms[:3])
    with pytest.raises(ValueError):
        igmh.run_igmh(None, 'x.molden', single)


def test_run_reads_the_grids_and_the_pairs(tmp_path):
    folder = tmp_path / 'Расчёт с пробелом'
    folder.mkdir()
    path = folder / 'dimer.molden.input'
    path.write_bytes(gzip.decompress((MWFN / 'igmh_dimer.molden.gz').read_bytes()))
    fake = fake_program(tmp_path / 'bin', f'''
assert answers(9) == '20 11 2 1-3 4-6 1 3 6 2', lines
assert answer(9) == 'n'
gunzip({q(MWFN / 'igmh_dimer_sl2r.cub.gz')}, 'sl2r.cub')
gunzip({q(MWFN / 'igmh_dimer_dg_inter.cub.gz')}, 'dg_inter.cub')
cp({q(MWFN / 'igmh_dimer_atmdg.txt')}, 'atmdg.txt')
cat({q(MWFN / 'igmh_dimer_output.txt')})
''')
    multiwfn.clear_cache()
    sign, field = grids('dimer')
    found = igmh.run_igmh(fake, path, field.molecule)
    assert found['fragments'] == [[0, 1, 2], [3, 4, 5]] and found['pairs'][0] == (2, 3, 0.079633, (0, 1))
    assert found['atoms'][2] == pytest.approx(0.119766) and found['integrals']['dg_inter'] == 0.093529
    assert np.allclose(found['field'].values, field.values) and found['version'] == '2026.7.15'
    empty = fake_program(tmp_path / 'bin2', 'echo(" Version 2026.7.15 (release date is the same as version name)")')
    multiwfn.clear_cache()
    with pytest.raises(ValueError):
        igmh.run_igmh(empty, path, field.molecule)

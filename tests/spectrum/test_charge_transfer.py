"""The charge transfer of an excited state: IFCT and the transition matrix
(modules/spectrum/analysis/charge_transfer.py).

Oracles: the outputs of Multiwfn 2026.7.15 recorded on the Mac of the user by tools/record_multiwfn_excitations.py
(tests/data/multiwfn/exc_*) — the TD-DFT of benzaldehyde (ORCA 6, CAM-B3LYP/def2-SVPD), the fragments CHO (O1, C2, H9)
and the ring. The answers built here are those of the records, line for line.
"""

from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import charge_transfer as ct

MWFN = Path(__file__).parents[1] / 'data' / 'multiwfn'
CHO, RING = [1, 2, 9], [3, 4, 5, 6, 7, 8, 10, 11, 12, 13, 14]


def text(name):
    return (MWFN / name).read_text(encoding='utf-8', errors='replace')


def recorded(name):
    return tuple(text(name).splitlines()[0].removeprefix('answers: ').split(' | '))


def test_atoms_are_read_and_written_as_multiwfn_takes_them():
    assert ct.parse_atoms('1,2,9', 14) == CHO
    assert ct.parse_atoms(' 3-8, 10-14 ', 14) == RING
    assert ct.parse_atoms('8-3 1 1', 14) == [1, 3, 4, 5, 6, 7, 8]
    assert ct.atoms_text(CHO) == '1,2,9' and ct.atoms_text(RING) == '3-8,10-14'
    assert ct.atoms_text([1, 2, 4, 5, 6]) == '1,2,4-6'
    for wrong in ('1,a', '0', '15', '2-20'):
        with pytest.raises(ValueError):
            ct.parse_atoms(wrong, 14)


def test_one_fragment_makes_the_rest_the_second():
    assert ct.fragments(['1,2,9', ''], 14) == [CHO, RING]
    assert ct.fragments(['1,2,9', '3-8,10-14', ''], 14) == [CHO, RING]
    for wrong in ([''], ['1-14'], ['1,2', '2,3']):
        with pytest.raises(ValueError):
            ct.fragments(wrong, 14)


def test_answers_are_those_recorded():
    assert ct.ifct_answers('excited.out', 1, [CHO, RING]) == recorded('exc_ifct2_s1.txt')
    assert ct.ifct_answers('excited.out', 3, [CHO, RING]) == recorded('exc_ifct2_s3.txt')
    assert ct.matrix_answers('excited.out', 1) == recorded('exc_heatmap2_atoms.txt')
    assert ct.matrix_answers('excited.out', 1, [CHO, RING]) == recorded('exc_heatmap2_fragments.txt')


def test_ifct_of_s1_is_mostly_local_on_the_formyl():
    found = ct.parse_ifct(text('exc_ifct2_s1.txt'))
    assert found['hole'] == [85.44, 14.56] and found['electron'] == [70.62, 29.38]
    assert found['variation'] == [-0.14818, 0.14818] and found['redistribution'] == [0.60332, 0.04279]
    assert found['transfer'] == {(1, 2): 0.25103, (2, 1): 0.10285} and found['net'] == {(1, 2): 0.14818}
    assert (found['ct'], found['le'], found['ct_apparent'], found['le_apparent']) == (35.388, 64.612, 14.818, 85.182)
    assert found['ct'] + found['le'] == pytest.approx(100)


def test_ifct_of_s3_moves_the_electron_to_the_formyl():
    found = ct.parse_ifct(text('exc_ifct2_s3.txt'))
    assert found['net'] == {(1, 2): -0.32345}  # the net goes from the ring to CHO
    assert found['ct'] == pytest.approx(45.31, abs=0.01)
    assert found['variation'][0] == pytest.approx(0.32345)
    assert ct.parse_ifct('no IFCT here') == {}


def test_the_matrix_of_the_atoms_sums_to_that_of_the_fragments():
    atoms = ct.read_tmat(text('exc_heatmap2_atoms__tmat.txt'))
    frags = ct.read_tmat(text('exc_heatmap2_fragments__tmat.txt'))
    assert atoms.shape == (14, 14) and frags.shape == (2, 2)
    assert frags == pytest.approx(np.array([[0.771906, 0.244371], [0.607003, 0.192166]]))
    index = [np.array(CHO) - 1, np.array(RING) - 1]
    for i in range(2):
        for j in range(2):
            assert atoms[np.ix_(index[i], index[j])].sum() == pytest.approx(frags[i, j], abs=2e-5)
    assert atoms.sum() == pytest.approx(frags.sum(), abs=1e-4)
    with pytest.raises(ValueError):
        ct.read_tmat('')


def test_runs_take_the_output_and_the_matrix(monkeypatch, tmp_path):
    from modules.spectrum.wavefunction import multiwfn

    asked = []

    def fake(program, path, answers, cores=1, step=None, timeout=600, name=None, keep=()):
        asked.append(answers)
        if answers[1] == '8':
            return text('exc_ifct2_s1.txt'), {}
        return text('exc_heatmap2_fragments.txt'), {'tmat.txt': text('exc_heatmap2_fragments__tmat.txt')}

    monkeypatch.setattr(multiwfn, '_run', fake)
    wavefunction, output = tmp_path / 'b.molden', tmp_path / 'b.out'
    wavefunction.write_text('x')
    output.write_text('x')
    found, _ = ct.run_ifct('mwfn', wavefunction, output, 1, [CHO, RING])
    assert found['ct'] == 35.388
    matrix, _ = ct.run_matrix('mwfn', wavefunction, output, 1, [CHO, RING])
    assert matrix.shape == (2, 2)
    assert asked[0][3] == 'excited.out' and asked[1][:2] == ('18', '2')
    monkeypatch.setattr(multiwfn, '_run', lambda *a, **k: ('nothing', {}))
    with pytest.raises(ValueError):
        ct.run_ifct('mwfn', wavefunction, output, 1, [CHO, RING])
    with pytest.raises(ValueError):
        ct.run_matrix('mwfn', wavefunction, output, 1)

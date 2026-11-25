"""QTAIM of every calculation of a queue (modules/spectrum/wavefunction/batch_qtaim.py).

Oracles: the topology Multiwfn 2026.7.15 recorded for water of examples/6-orbitals (MP2/Gaussian 16 .fchk): 3 nuclei, 2
bond critical points O–H, n − b + r − c = 1 (tests/spectrum/test_multiwfn.py reads the same file); the counts of the
tables follow from it — every molecule done gives one summary row and two bond rows; a calculation without a file of
orbitals gives a row with its reason and no bonds.
"""

import shutil
from pathlib import Path

import pytest

from modules.sextant.batch import BatchItem
from modules.spectrum.wavefunction import batch_qtaim, multiwfn
from modules.spectrum.wavefunction.field_tables import read_csv
from azimuth.core import read_xyz

ROOT = Path(__file__).resolve().parents[2]
FCHK = ROOT / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk'
CPPROP = Path(__file__).parents[1] / 'data' / 'multiwfn' / 'water_fchk_CPprop_2026.7.15.txt'
WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')


def item(tmp_path, name, orbitals=True, state='done'):
    folder = tmp_path / name
    folder.mkdir()
    output = folder / (name + '.out')
    output.write_text('output', encoding='utf-8')
    if orbitals:
        shutil.copy(FCHK, folder / (name + '.fchk'))
    return BatchItem(name, WATER, state=state, folder=str(folder), output=str(output))


def recorded(calls):
    def run(program, path, cores, step):
        calls.append(Path(path).name)
        assert step(0, 1) is True
        return multiwfn.parse_cps(CPPROP.read_text(encoding='utf-8')), 'recorded', '2026.7.15', []
    return run


def test_every_calculation_done_of_a_queue(tmp_path):
    items = [item(tmp_path, 'conf1'), item(tmp_path, 'conf2'), item(tmp_path, 'conf3', orbitals=False),
             item(tmp_path, 'conf4', state='failed')]
    calls, steps = [], []
    results = batch_qtaim.analyse('multiwfn', items, 2, lambda k, n: steps.append((k, n)) or True, recorded(calls))
    assert calls == ['conf1.fchk', 'conf2.fchk']  # not done — not run; no orbitals — not run
    assert [r.name for r in results] == ['conf1', 'conf2', 'conf3'] and steps[-1] == (3, 3)
    assert results[2].topology is None and results[2].error == 'нет файла орбиталей'
    for r in results[:2]:
        assert r.topology.counts == {'n': 3, 'b': 2, 'r': 0, 'c': 0} and r.topology.poincare_hopf == 1
        assert [c.kind for c in r.contacts] == ['covalent', 'covalent']
        # the tables of one search, in «Анализ» of its folder
        assert (Path(r.item.folder) / 'Анализ' / (r.name + '_qtaim_bonds.csv')).is_file()
    tables = batch_qtaim.tables(results)
    header, rows = tables['summary']
    assert header[:6] == ['Молекула', 'n', 'b', 'r', 'c', 'n − b + r − c']
    assert rows[0][:7] == ['conf1', 3, 2, 0, 0, 1, 2] and rows[2][0] == 'conf3' and rows[2][-1] == 'нет файла орбиталей'
    header, rows = tables['bonds']
    assert [(r[0], r[1], r[3]) for r in rows] == [('conf1', 'b1', 'ковалентная связь'), ('conf1', 'b2', 'ковалентная связь'),
                                                  ('conf2', 'b1', 'ковалентная связь'), ('conf2', 'b2', 'ковалентная связь')]
    assert {r[2] for r in rows} == {'O1–H2', 'O1–H3'} and 0.30 < float(rows[0][4]) < 0.42
    header, rows = tables['contacts']
    assert header[0] == 'Молекула' and rows == []  # water alone: no weak interactions


def test_the_file_of_orbitals_next_to_the_output(tmp_path):
    one = item(tmp_path, 'a', orbitals=False)
    assert batch_qtaim.wavefunction_of(one) is None
    (Path(one.folder) / 'other.molden').write_text('x')
    assert batch_qtaim.wavefunction_of(one).name == 'other.molden'
    (Path(one.folder) / 'a.molden.input').write_text('x')
    assert batch_qtaim.wavefunction_of(one).name == 'a.molden.input'  # ORCA's orca_2mkl, named after the output
    assert batch_qtaim.wavefunction_of(BatchItem('b', WATER)) is None


def test_a_failure_of_one_and_the_cancel(tmp_path):
    items = [item(tmp_path, 'x'), item(tmp_path, 'y')]

    def fails(program, path, cores, step):
        raise ValueError('Multiwfn не нашёл критических точек.\nконец вывода')
    results = batch_qtaim.analyse('multiwfn', items, run=fails)
    assert [r.error for r in results] == ['Multiwfn не нашёл критических точек.'] * 2
    with pytest.raises(InterruptedError):
        batch_qtaim.analyse('multiwfn', items, step=lambda k, n: k < 1, run=recorded([]))


def test_the_tables_written_in_the_style_of_the_program(tmp_path):
    from modules.spectrum.wavefunction import field_tables

    results = batch_qtaim.analyse('multiwfn', [item(tmp_path, 'w')], run=recorded([]))
    written = field_tables.write_tables(tmp_path, 'batch_qtaim', batch_qtaim.tables(results))
    assert [p.name for p in written] == ['batch_qtaim_summary.csv', 'batch_qtaim_bonds.csv', 'batch_qtaim_contacts.csv']
    header, rows = read_csv(written[1])
    assert header[0] == 'Молекула' and len(rows) == 2


# -- an analysis is a job of its own, bound to the artifact chosen ------------------------------
def test_t15_one_molecule_ready_is_analysed_before_the_others(tmp_path):
    from azimuth.runtime import analysis

    items = [item(tmp_path, 'ready'), item(tmp_path, 'later', state='running'), item(tmp_path, 'next', state='waiting')]
    calls = []
    results = batch_qtaim.analyse('multiwfn', items, run=recorded(calls), ledger=tmp_path / 'queue')
    assert calls == ['ready.fchk'] and [r.name for r in results] == ['ready'] and results[0].topology is not None
    (record,) = analysis.Ledger(tmp_path / 'queue').records()
    assert record.state == 'succeeded' and record.artifact == 'ready.fchk' and record.kind == 'qtaim'
    assert record.attempt_id == 'folder:ready' and record.sha256 == analysis.sha256(FCHK)
    assert [i.state for i in items] == ['done', 'running', 'waiting']  # the queue is not touched


def test_t17_a_failed_multiwfn_is_the_analysis_failure_not_the_calculation(tmp_path):
    from azimuth.runtime import analysis

    items = [item(tmp_path, 'x')]

    def fails(program, path, cores, step):
        raise ValueError('Multiwfn: формат файла не распознан')
    results = batch_qtaim.analyse('multiwfn', items, run=fails, ledger=tmp_path / 'queue')
    assert results[0].topology is None and items[0].state == 'done'
    (record,) = analysis.Ledger(tmp_path / 'queue').records()
    assert record.state == 'failed' and 'формат' in record.error and record.finished
    assert not list((Path(items[0].folder) / 'Анализ').glob('.az-input-*'))  # the copy removed


def test_t18_the_molecule_calculated_again_during_its_qtaim(tmp_path):
    from azimuth.runtime import analysis

    one = item(tmp_path, 'm')
    original = analysis.sha256(FCHK)
    seen = []

    def recalculated_meanwhile(program, path, cores, step):
        (Path(one.folder) / 'm.fchk').write_text('a new calculation wrote another file', encoding='utf-8')
        seen.append(analysis.sha256(path))  # what Multiwfn reads now
        return recorded([])(program, path, cores, step)
    results = batch_qtaim.analyse('multiwfn', [one], run=recalculated_meanwhile, ledger=tmp_path / 'queue')
    assert seen == [original] and results[0].topology.counts['b'] == 2  # the analysis kept the file chosen
    (record,) = analysis.Ledger(tmp_path / 'queue').records()
    assert record.sha256 == original != analysis.sha256(Path(one.folder) / 'm.fchk')

"""The queue of calculations for a set of structures (modules/sextant/batch.py).

Oracles: ΔE and the Boltzmann shares computed here by hand (exp(−ΔE/RT), R = 1.987204259e-3 kcal/(mol·K), CODATA
2018); the final energy and the Gibbs free energy printed by ORCA 6.0.1 for water (tests/data/orca601/h2o_optfreq.out).
"""

import math
import re
from pathlib import Path

import pytest

from azimuth.core import Atom, Calculation, Molecule
from modules.sextant import batch

DATA = Path(__file__).parents[1] / 'data'


def water(dx=0.0):
    return Molecule('w', (Atom('O', dx, 0, 0), Atom('H', dx + 0.96, 0, 0), Atom('H', dx - 0.24, 0.93, 0)), ((0, 1, 1), (0, 2, 1)))


def test_default_count_takes_the_window():
    assert batch.default_count([0.0, 0.8, 2.99, 3.2, 7.0]) == 3
    assert batch.default_count([None, None]) == 2  # nothing known: all
    assert batch.default_count([5.0]) == 1  # at least one
    assert batch.default_count([0.0, 3.0, 3.0001]) == 2  # the edge of the window counts, past it — not


def test_summary_sorts_again_and_gives_shares(tmp_path):
    items = [batch.BatchItem(f'c{k}', water(k), start_delta=d) for k, d in enumerate((0.0, 0.5, 1.0))]
    b = batch.Batch('orca', Calculation(), items, tmp_path)
    b.finished(items[0], 'done', energy=-76.000)
    b.finished(items[1], 'done', energy=-76.002)  # lower after DFT: the order changes
    b.finished(items[2], 'failed')
    rows = b.summary()
    assert [r['name'] for r in rows] == ['c1', 'c0'] and not rows[0]['by_gibbs']
    delta = 0.002 * batch.HARTREE_KCAL
    assert rows[1]['delta'] == pytest.approx(delta)
    w = math.exp(-delta / (batch.R_KCAL * 298.15))
    assert rows[0]['share'] == pytest.approx(1 / (1 + w)) and rows[1]['share'] == pytest.approx(w / (1 + w))
    header, table = b.table()
    assert header[5] == 'ΔE, ккал/моль' and table[0][1] == 'c1' and table[-1][1] == 'c2' and table[-1][-1] == 'ошибка'
    b.finished(items[0], 'done', energy=-76.000, gibbs=-75.990)
    b.finished(items[1], 'done', energy=-76.002, gibbs=-75.989)
    assert [r['name'] for r in b.summary()] == ['c0', 'c1'] and b.summary()[0]['by_gibbs']  # by G when all have it


def test_batch_json_round_trip_and_resume(tmp_path):
    items = [batch.BatchItem('c1', water(), 0, 1, start_delta=0.0), batch.BatchItem('c2', water(1.0), 0, 1, start_delta=1.2)]
    calc = Calculation(method='PBE0', basis='def2-TZVP', title='set')
    b = batch.Batch('orca', calc, items, tmp_path, source='CREST')
    items[0].state, items[0].folder = 'running', str(tmp_path / 'a')
    b.save()
    again = batch.Batch.load(tmp_path)
    assert again.calc == calc and again.source == 'CREST' and again.kind == 'orca' and again.purpose == ''
    assert [i.name for i in again.items] == ['c1', 'c2'] and again.items[1].molecule == items[1].molecule
    assert again.items[0].state == 'waiting'  # it was running when the program closed: started again
    loose = batch.Batch('xtb', calc, [batch.BatchItem('x', Molecule('w', water().atoms, None))], tmp_path / 'xyz')
    loose.folder.mkdir()
    loose.save()  # a molecule without bonds given (an XYZ) — written and read back as such
    assert batch.Batch.load(loose.folder).items[0].molecule.bonds is None
    assert again.next_waiting() is again.items[0] and not again.done()
    again.stop_rest()
    assert again.done() and again.counts()['skipped'] == 2
    fukui = batch.Batch('orca', calc, items, tmp_path / 'fukui', purpose='fukui')
    fukui.folder.mkdir()
    fukui.save()
    assert batch.Batch.load(fukui.folder).purpose == 'fukui'


def test_folder_and_result_of_an_orca_output(tmp_path):
    from datetime import datetime

    now = datetime(2026, 11, 2, 10, 30, 0)
    folder = batch.batch_folder(tmp_path, water(), 'orca', now)
    assert folder.name == '2026-11-02_10-30-00_H2O_batch_orca' and folder.is_dir()
    assert batch.batch_folder(tmp_path, water(), 'orca', now).name.endswith('-2')  # the same second: another folder
    # ORCA 6.0.1, optimization + frequencies of water: the last «FINAL SINGLE POINT ENERGY» and «Final Gibbs free
    # energy» (298.15 K, σ = 2 of C2v) — G of modules/spectrum/analysis/thermo.py agrees within 1e-6 Eh
    text = (DATA / 'orca601' / 'h2o_optfreq.out').read_text(encoding='utf-8', errors='replace')
    energy, geometry, gibbs, heat = batch.result_of('orca', text)
    last = float(re.findall(r'FINAL SINGLE POINT ENERGY\s+(-?\d+\.\d+)', text)[-1])
    orca_gibbs = float(re.findall(r'Final Gibbs free energy\s+\.\.\.\s+(-?\d+\.\d+)', text)[-1])
    assert energy == pytest.approx(last, abs=1e-10) and geometry is not None and len(geometry.atoms) == 3
    assert gibbs == pytest.approx(orca_gibbs, abs=1e-6) and heat is None
    optimization = (DATA / 'orca601' / 'h2o_opt_frozen_oh.out').read_text(encoding='utf-8', errors='replace')
    assert batch.result_of('orca', optimization)[2] is None  # no frequencies: no G
    assert batch.result_of('orca', 'not an output') == (None, None, None, None)


def test_mopac_results_are_sorted_by_the_heat_of_formation(tmp_path):
    # MOPAC prints no total energy — the queue ranks by ΔHf (kcal/mol, the last «FINAL HEAT OF FORMATION» of
    # MOPAC 23.2.5, tests/data/mopac)
    text = (DATA / 'mopac' / 'c2h4_pm7_opt.out').read_text(encoding='utf-8', errors='replace')
    energy, geometry, gibbs, heat = batch.result_of('mopac', text)
    printed = float(re.findall(r'FINAL HEAT OF FORMATION\s*=\s*(-?\d+\.\d+)', text)[-1])
    assert energy is None and gibbs is None and heat == pytest.approx(printed, abs=1e-3)
    assert geometry is not None and len(geometry.atoms) == 6
    items = [batch.BatchItem(f'c{k}', water(k)) for k in range(3)]
    b = batch.Batch('mopac', Calculation(), items, tmp_path)
    b.finished(items[0], 'done', heat=-10.0)
    b.finished(items[1], 'done', heat=-11.5)
    b.finished(items[2], 'failed')
    rows = b.summary()
    assert [r['name'] for r in rows] == ['c1', 'c0'] and rows[0]['by'] == 'heat'
    assert rows[1]['delta'] == pytest.approx(1.5)  # kcal/mol directly, not hartree
    header, table = b.table()
    assert header[5] == 'ΔΔHf, ккал/моль' and table[0][4] == '-11.500' and table[0][2] == '' and table[-1][1] == 'c2'
    assert batch.Batch.load(tmp_path).items[1].heat == -11.5


def test_an_item_sent_to_a_server_stays_running_after_a_restart(tmp_path):
    # the program closed while a job of a server queue ran there (job.json in its folder): it is not sent again,
    # its watching is taken up (batch_actions._resume_batch_item); a local one, or one never sent, starts again
    sent, unsent = tmp_path / 'j1', tmp_path / 'j2'
    sent.mkdir()
    unsent.mkdir()
    (sent / 'job.json').write_text('{"job": "123", "folder": "~/azimuth/j1"}', encoding='utf-8')
    items = [batch.BatchItem('a', water(), state='running', folder=str(sent)),
             batch.BatchItem('b', water(), state='running', folder=str(unsent)), batch.BatchItem('c', water())]
    server = batch.Batch('orca', Calculation(), items, tmp_path, place='server')
    server.save()
    again = batch.Batch.load(tmp_path)
    assert [i.state for i in again.items] == ['running', 'waiting', 'waiting'] and again.current().name == 'a'
    local = tmp_path / 'local'
    local.mkdir()
    batch.Batch('orca', Calculation(), [batch.BatchItem('a', water(), state='running', folder=str(sent))], local).save()
    assert batch.Batch.load(local).items[0].state == 'waiting'


def test_jobs_sent_ahead_and_the_reason_of_a_failure(tmp_path):
    # the rest of a server queue sent before the exit is 'sent' (in SLURM, watched later one by one): not done,
    # kept by batch.json; the reason of a failure is kept with it
    items = [batch.BatchItem('a', water(), state='done'), batch.BatchItem('b', water(), state='sent', folder='x'),
             batch.BatchItem('c', water(), state='sent', folder='y'), batch.BatchItem('d', water(), state='failed', note='MOPAC завершилась с ошибкой')]
    q = batch.Batch('mopac', Calculation(), items, tmp_path, place='server', extra={'plan': {'processes': 36}})
    assert not q.done() and q.next_sent().name == 'b' and q.next_waiting() is None and q.counts()['sent'] == 2
    q.save()
    again = batch.Batch.load(tmp_path)
    assert [i.state for i in again.items] == ['done', 'sent', 'sent', 'failed']
    assert again.items[3].note == 'MOPAC завершилась с ошибкой' and again.extra['plan']['processes'] == 36
    assert batch.STATE_NAMES['sent'] == 'отправлен на сервер'

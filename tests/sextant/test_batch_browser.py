"""Saved packages survive restarts as packages; inspection must not submit work or alter results.

Independent oracles: 44 named records, 40 completed/4 failed, exact coordinates and explicit charge/spin; byte
snapshots of manifests before/after browsing. Server callbacks fail unless the explicit resume action is tested.
"""

import os
from pathlib import Path

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import pytest
from PySide6.QtCore import QCoreApplication, QEvent
from PySide6.QtWidgets import QApplication

from azimuth.app import Studio
from azimuth.core import Calculation, read_xyz
from modules.sextant import batch, history
from modules.sextant.batch_browser import folders, restore_completed_results


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, tmp_path, monkeypatch):
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    owner = Studio(example=True, probe_machine=False)
    owner.unfinished.timer.stop()
    monkeypatch.setattr(owner.run_tool, 'jobs_root', lambda: tmp_path / 'jobs')
    monkeypatch.setattr(owner, 'notify', lambda *a: None)

    def forbidden(*a, **kw):
        pytest.fail('Browsing a package must not submit, resume or contact a server')

    monkeypatch.setattr(owner.batch_tool, '_run_batch', forbidden)
    monkeypatch.setattr(owner.batch_tool, '_open_batch_server', forbidden)
    yield owner
    owner.dirty = False
    for document in owner.all_documents():
        document.dirty = False
    owner.close()
    owner.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)


def package(folder, kind='mopac', count=44):
    folder.mkdir(parents=True)
    items = []
    for k in range(count):
        molecule = read_xyz(f'3\nwater\nO {k} 0 0\nH {k + 0.96} 0 0\nH {k - 0.24} 0.93 0\n')
        done = k < count - 4 if count > 4 else True
        items.append(batch.BatchItem(f'Молекула {k + 1}', molecule, charge=1 if k == 1 else 0,
                                     multiplicity=2 if k == 1 else 1, state='done' if done else 'failed',
                                     geometry=molecule if done else None, heat=float(k) if done else None,
                                     note='' if done else 'SCF did not converge'))
    queue = batch.Batch(kind, Calculation(), items, folder, place='server')
    queue.save()
    return queue


def test_discovery_includes_completed_and_external_packages(tmp_path):
    a = package(tmp_path / 'jobs' / 'finished')
    b = package(tmp_path / 'external' / 'queue')
    (tmp_path / 'jobs' / 'ordinary').mkdir()
    assert set(folders(tmp_path / 'jobs', [b.folder, a.folder, a.folder / 'batch.json'])) == {a.folder, b.folder}
    assert folders(tmp_path / 'nonexistent') == []


def test_reopen_all_44_without_starting_or_rewriting(window):
    queue = package(window.run_tool.jobs_root() / 'finished_mopac')
    before = (queue.folder / 'batch.json').read_bytes()
    window.preferences.remove(batch.OPEN_KEY)  # completing a queue removed this key in 0.96.0
    history.save(window.preferences, [])  # package discovery must not depend on the 60 individual history entries
    dialog = window.batch_tool.show_saved_batches()
    assert dialog.table.rowCount() == 44
    assert dialog.table.item(0, 0).text() == 'Молекула 1'
    assert dialog.table.item(43, 0).text() == 'Молекула 44'
    assert dialog.table.item(43, 5).text() == 'SCF did not converge'
    assert 'готово: 40, с ошибкой: 4' in dialog.summary.text()
    assert not dialog.resume_button.isEnabled()
    assert not dialog.qtaim_button.isEnabled()
    assert 'MOPAC' in dialog.analysis_note.text() and 'ORCA' in dialog.analysis_note.text()
    assert dialog.structures_button.isEnabled()
    dialog.close()
    again = window.opening_tool.open_path(str(queue.folder / 'batch.json'))
    assert again.table.rowCount() == 44
    assert (queue.folder / 'batch.json').read_bytes() == before
    assert window.batch is None


def test_qtaim_uses_selected_package_not_last(window, monkeypatch):
    a = package(window.run_tool.jobs_root() / 'orca_a', 'orca', 2)
    b = package(window.run_tool.jobs_root() / 'orca_b', 'orca', 2)
    window.last_batch = b
    calls = []
    monkeypatch.setattr(window.batch_tool, 'batch_qtaim', lambda folder=None: calls.append(folder))
    dialog = window.batch_tool.show_saved_batches(a.folder)
    assert dialog.qtaim_button.isEnabled()
    dialog.qtaim_button.click()
    assert calls == [str(a.folder)]
    dialog.packages.setCurrentIndex(dialog.packages.findData(str(b.folder)))
    dialog.qtaim_button.click()
    assert calls == [str(a.folder), str(b.folder)]


def test_pending_package_is_resumed_only_by_explicit_click(window, monkeypatch):
    q = package(window.run_tool.jobs_root() / 'pending', 'orca', 2)
    q.items[0].state = 'sent'
    q.save()
    calls = []
    monkeypatch.setattr(window.batch_tool, 'resume_batch', lambda folder: calls.append(folder) or q)
    dialog = window.batch_tool.show_saved_batches(q.folder)
    assert calls == [] and dialog.resume_button.isEnabled()
    dialog.resume_button.click()
    assert calls == [str(q.folder)]


def test_completed_geometries_names_and_charge_spin_are_kept(window):
    q = package(window.run_tool.jobs_root() / 'finished')
    first = window.document()
    original = window.coordinate_tool.table_molecule()
    before = (q.folder / 'batch.json').read_bytes()
    dialog = window.batch_tool.show_saved_batches(q.folder)
    assert dialog.open_structures() == 40
    assert window.document() is not first
    assert window.project_molecules.count() == 40  # a project of their own
    assert not window.drawer.conformers  # distinct molecules must not acquire Boltzmann populations
    source, rows = window.batch_tool.batch_source()
    assert source == 'Пакет · ' + q.folder.name
    assert [row[0] for row in rows] == [f'Молекула {k + 1}' for k in range(40)]
    assert rows[1][3:] == (1, 2)
    assert rows[39][1].atoms[0].x == 39
    assert all(len(row[1].atoms) == 3 for row in rows)
    target = window.current_document
    window.switch_document(0)
    assert window.coordinate_tool.table_molecule() == original
    window.switch_document(target)
    assert window.batch_tool.batch_source()[1][1][3:] == (1, 2)
    assert (q.folder / 'batch.json').read_bytes() == before


def test_bad_package_is_visible_but_cannot_run(window):
    folder = window.run_tool.jobs_root() / 'broken'
    folder.mkdir(parents=True)
    (folder / 'batch.json').write_text('{broken', encoding='utf-8')
    dialog = window.batch_tool.show_saved_batches(folder)
    assert 'Очередь не прочитана' in dialog.summary.text()
    assert not dialog.resume_button.isEnabled() and not dialog.qtaim_button.isEnabled()


def test_recover_old_missing_geometry_without_changing_manifest_or_failure(tmp_path):
    q = package(tmp_path / 'q', count=2)
    output = Path(__file__).parents[1] / 'data' / 'mopac' / 'h2o_pm7_opt.out'
    for item in q.items:
        item.geometry = None
        item.output = str(output)
    q.items[1].state = 'failed'
    q.save()
    before = (q.folder / 'batch.json').read_bytes()
    restore_completed_results(q)
    assert len(q.items[0].geometry.atoms) == 3
    assert q.items[1].geometry is None and q.items[1].state == 'failed'
    assert (q.folder / 'batch.json').read_bytes() == before


def test_invalid_completed_geometry_is_not_replaced_by_input(window):
    q = package(window.run_tool.jobs_root() / 'invalid', count=2)
    output = q.folder / 'invalid.out'
    output.write_text('''MOPAC v23.2.5
 PM7 CALCULATION RESULTS
 CARTESIAN COORDINATES
    1 O 0.000000 0.000000 0.000000
    2 H 0.002000 0.000000 0.000000
    3 H 0.000000 0.960000 0.000000
 JOB ENDED NORMALLY
''', encoding='utf-8')
    q.items[0].geometry = None
    q.items[0].output = str(output)
    q.save()
    dialog = window.batch_tool.show_saved_batches(q.folder)
    assert dialog.queue.items[0].geometry is None
    assert '0,1 Å' in dialog.table.item(0, 5).text()
    assert dialog.open_structures() == 1  # no substitution of the unoptimized input for an invalid output

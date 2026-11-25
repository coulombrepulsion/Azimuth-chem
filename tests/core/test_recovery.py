"""Recovery contracts: durable copies, concurrent windows and actual Studio tabs."""
import os
import subprocess
import sys

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QFileDialog
from PySide6.QtGui import QCloseEvent

from azimuth.core import Calculation, read_xyz, read_project, project_text
from azimuth.recovery import Session
from azimuth.recovery_ui import decode_entry

WATER = '3\nWater\nO 0 0 0\nH 0.76 0 0.5\nH -0.76 0 0.5'
HELIUM = '1\nHelium\nHe 0 0 0'
MEMORY_MB = 2048
LABEL = 'central oxygen'
CONSTRAINTS = [('C', (0,)), ('B', (0, 1))]
EDIT = ('! HF STO-3G SP\n* xyz 0 1\nHe 0 0 0\n*', 'generated input')


def entry(xyz=WATER):
    return {'id': 'water', 'title': 'Working molecule', 'project': project_text(read_xyz(xyz), Calculation()),
            'program': 'orca', 'origin': '', 'input_edit': None}


@pytest.fixture
def session(tmp_path):
    value = Session(tmp_path)
    yield value
    value.close()


def test_preserves_previous_snapshot_when_atomic_replace_fails(session, monkeypatch):
    # Arrange
    original = [entry()]
    session.write(original)
    def fail(*args):
        raise OSError('disk unavailable')
    monkeypatch.setattr(os, 'replace', fail)
    # Act
    with pytest.raises(OSError, match='disk unavailable'):
        session.write([entry(HELIUM)])
    # Assert
    assert session.read() == original
    assert not list(session.path.parent.glob('.recovery-*'))


def test_skips_active_session_when_another_window_claims_it(session):
    # Arrange
    session.write([entry()])
    # Act
    other = Session.claim(session.path)
    # Assert
    assert other is None
    assert session.read() == [entry()]


def test_recovers_snapshot_when_writer_process_crashes(tmp_path):
    # Arrange
    script = 'from azimuth.recovery import Session; import os,sys; s=Session(sys.argv[1]); s.write([]); os._exit(0)'
    subprocess.run([sys.executable, '-c', script, str(tmp_path)], check=True)
    path = next(tmp_path.glob('*.json'))
    # Act
    claimed = Session.claim(path)
    # Assert
    assert claimed is not None
    try:
        assert claimed.read() == []
    finally:
        claimed.close()


def test_keeps_file_timestamp_when_snapshot_is_unchanged(session):
    # Arrange
    session.write([entry()])
    timestamp = session.path.stat().st_mtime_ns
    # Act
    session.write([entry()])
    # Assert
    assert session.path.stat().st_mtime_ns == timestamp


def test_rejects_corrupt_file_without_removing_it(session):
    # Arrange
    broken = '{broken json'
    session.path.write_text(broken)
    # Act
    with pytest.raises(ValueError, match='property name'):
        session.read()
    # Assert
    assert session.path.read_text() == broken


def test_restores_unsaved_copy_when_original_project_path_was_saved(tmp_path):
    # Arrange
    draft = entry()
    original = tmp_path / 'original.qcc'
    original.write_text('original contents')
    draft['origin'] = str(original)
    # Act
    doc = decode_entry(draft)
    # Assert
    assert doc.project_path is None
    assert doc.dirty
    assert original.read_text() == 'original contents'


@pytest.fixture
def windows(tmp_path, monkeypatch):
    monkeypatch.setenv('AZIMUTH_RECOVERY_DIR', str(tmp_path / 'recovery'))
    app = QApplication.instance() or QApplication([])
    from azimuth.app import Studio
    created = []
    def make():
        window = Studio(probe_machine=False)
        created.append(window)
        return window
    yield make
    for window in created:
        window.recovery.finish()
        window.dirty = False
        for doc in window.all_documents():
            doc.dirty = False
        window.close()
        window.deleteLater()
    from PySide6.QtCore import QCoreApplication, QEvent
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    assert app is not None


def approve(monkeypatch, answer=QMessageBox.StandardButton.Yes):
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: answer)


def test_restores_both_tabs_with_settings_labels_and_input_when_session_is_abandoned(windows, monkeypatch):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.memory.setValue(MEMORY_MB)
    window.viewer.custom_labels = {0: LABEL}
    window.constraints = list(CONSTRAINTS)
    window.input_tool.restore_input_edit(EDIT)
    window.new_document('Second', read_xyz(HELIUM))
    window.recovery.capture()
    source = window.recovery.session.path
    window.recovery.finish(keep=True)
    restored = windows()
    from PySide6.QtTest import QSignalSpy
    spy = QSignalSpy(restored.recovery.restored)
    expected_notifications = 1
    approve(monkeypatch)
    # Act
    restored.recovery.recover()
    # Assert
    assert spy.count() == expected_notifications
    docs = [d for d in restored.all_documents() if d.molecule.atoms]
    assert [d.molecule.formula for d in docs] == [read_xyz(WATER).formula, read_xyz(HELIUM).formula]
    assert docs[0].calculation.memory_mb == MEMORY_MB
    assert docs[0].labels == {0: LABEL}
    assert docs[0].constraints == CONSTRAINTS
    assert docs[0].input_edit == EDIT
    assert all(d.dirty and d.project_path is None for d in docs)
    assert not source.exists()
    assert restored.recovery.session.path.exists()


def test_keeps_last_valid_draft_when_current_coordinate_is_incomplete(windows):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.recovery.capture()
    before = window.recovery.session.read()
    # Act
    window.table.item(0, 1).setText('-')
    result = window.recovery.capture()
    # Assert
    assert not result
    assert window.recovery.session.read() == before


def test_retains_cleared_geometry_when_user_deletes_all_atoms(windows):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.recovery.capture()
    # Act
    from modules.compass.panels.documents import empty_molecule
    window.load_molecule(empty_molecule())
    window.recovery.capture()
    # Assert
    draft = window.recovery.session.read()[0]
    assert not read_project(draft['project'])[0].atoms


def test_keeps_other_tabs_when_user_closes_one_tab(windows, monkeypatch):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.new_document('Second', read_xyz(HELIUM))
    window.recovery.capture()
    approve(monkeypatch)
    # Act
    window.close_document(0)
    # Assert
    drafts = window.recovery.session.read()
    assert [read_project(d['project'])[0].formula for d in drafts] == [read_xyz(HELIUM).formula]


def test_preserves_old_copy_when_recovery_is_deferred(windows, monkeypatch):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.recovery.capture()
    path = window.recovery.session.path
    window.recovery.finish(keep=True)
    restored = windows()
    approve(monkeypatch, QMessageBox.StandardButton.No)
    # Act
    restored.recovery.recover()
    # Assert
    assert path.exists()
    assert not restored.molecule.atoms


def test_preserves_source_when_restored_snapshot_cannot_be_written(windows, monkeypatch):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.recovery.capture()
    source = window.recovery.session.path
    window.recovery.finish(keep=True)
    restored = windows()
    approve(monkeypatch)
    def fail(*args):
        raise OSError('disk full')
    monkeypatch.setattr(os, 'replace', fail)
    # Act
    restored.recovery.recover()
    # Assert
    assert source.exists()
    assert restored.own_molecule().formula == read_xyz(WATER).formula


def test_saves_every_modified_tab_when_user_accepts_exit(windows, tmp_path, monkeypatch):
    # Arrange
    window = windows()
    first, second = tmp_path / 'first.qcc', tmp_path / 'second.qcc'
    window.load_molecule(read_xyz(WATER))
    window.project_path = first
    window.new_document('Second', read_xyz(HELIUM))
    window.project_path = second
    window.dirty = True
    window.recovery.capture()
    snapshot = window.recovery.session.path
    approve(monkeypatch, QMessageBox.StandardButton.Save)
    # Act
    event = QCloseEvent()
    window.closeEvent(event)
    # Assert
    assert event.isAccepted()
    assert read_project(first.read_text(encoding='utf-8'))[0].formula == read_xyz(WATER).formula
    assert read_project(second.read_text(encoding='utf-8'))[0].formula == read_xyz(HELIUM).formula
    assert not snapshot.exists()


def test_retains_recovery_when_save_dialog_is_cancelled_at_exit(windows, monkeypatch):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.recovery.capture()
    path = window.recovery.session.path
    approve(monkeypatch, QMessageBox.StandardButton.Save)
    monkeypatch.setattr(QFileDialog, 'getSaveFileName', lambda *a, **k: ('', ''))
    # Act
    event = QCloseEvent()
    window.closeEvent(event)
    # Assert
    assert not event.isAccepted()
    assert path.exists()
    assert window.recovery.capture()


def test_keeps_snapshot_of_live_window_when_recovery_is_requested(windows):
    # Arrange
    first = windows()
    first.load_molecule(read_xyz(WATER))
    first.recovery.capture()
    second = windows()
    # Act
    second.recovery.recover()
    # Assert
    assert not second.molecule.atoms
    assert first.recovery.session.path.exists()


def test_captures_molecule_tabs_when_crystal_section_is_selected(windows):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.crystal_tool.set_compass_mode('crystal')
    selected = window.document()
    # Act
    window.recovery.capture()
    # Assert
    drafts = window.recovery.session.read()
    assert [read_project(d['project'])[0].formula for d in drafts] == [read_xyz(WATER).formula]
    assert window.document() is selected
    assert window.document_kind == 'crystal'


def test_keeps_own_structure_and_drawer_when_previewing_trajectory(windows):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    own = window.own_molecule()
    window.trajectory_tool.enter_trajectory()
    window.trajectory_tool.show_molecule(read_xyz(HELIUM))
    displayed = window.molecule
    # Act
    window.recovery.capture()
    # Assert
    draft = window.recovery.session.read()[0]
    assert read_project(draft['project'])[0].formula == own.formula
    assert window.browsing
    assert window.molecule is displayed


def test_captures_periodically_when_timer_event_fires(windows):
    # Arrange
    window = windows()
    window.load_molecule(read_xyz(WATER))
    # Act
    window.recovery.timer.timeout.emit()
    # Assert
    draft = window.recovery.session.read()[0]
    assert read_project(draft['project'])[0].formula == read_xyz(WATER).formula


def test_rejects_invalid_entry_before_creating_any_tabs(windows, tmp_path):
    # Arrange
    window = windows()
    source = Session(tmp_path / 'recovery')
    source.write([entry(), {'project': 123}])
    path = source.path
    source.close(keep=True)
    original_docs = list(window.all_documents())
    # Act
    window.recovery.recover()
    # Assert — set aside into «damaged/», not offered again at the next start
    assert window.all_documents() == original_docs
    assert not path.exists() and (path.parent / 'damaged' / path.name).exists()


def test_removes_only_own_snapshot_when_exit_is_discarded(windows, monkeypatch):
    # Arrange
    first, second = windows(), windows()
    first.load_molecule(read_xyz(WATER))
    second.load_molecule(read_xyz(HELIUM))
    first.recovery.capture()
    second.recovery.capture()
    own, other = first.recovery.session.path, second.recovery.session.path
    approve(monkeypatch, QMessageBox.StandardButton.Discard)
    # Act
    first.closeEvent(QCloseEvent())
    # Assert
    assert not own.exists()
    assert other.exists()


# -- 0.93.0 ---------------------------------------------------------------------------------------------------------
def test_does_not_read_the_file_back_to_skip_an_unchanged_snapshot(session, monkeypatch):
    from pathlib import Path

    session.write([entry()])
    def refuse(self):
        raise AssertionError('read back')
    monkeypatch.setattr(Path, 'read_bytes', refuse)
    session.write([entry()])  # the hash of the last write decides
    monkeypatch.undo()
    session.path.unlink()
    session.write([entry()])  # the file gone (removed by hand): written again
    assert session.read() == [entry()]


def test_sets_a_damaged_snapshot_aside_and_cleans_cut_off_writes(tmp_path):
    from azimuth.recovery import clean_temporary, set_aside, TEMPORARY_AGE

    first, second = tmp_path / ('a' * 32 + '.json'), tmp_path / ('b' * 32 + '.json')
    first.write_text('{broken')
    second.write_text('{broken too')
    moved = set_aside(first)
    assert moved == tmp_path / 'damaged' / first.name and moved.read_text() == '{broken' and not first.exists()
    (tmp_path / 'damaged' / second.name).write_text('older')
    assert set_aside(second).name == 'b' * 32 + '-1.json'
    old, fresh = tmp_path / '.recovery-old', tmp_path / '.recovery-fresh'
    old.write_text('x')
    fresh.write_text('y')
    now = fresh.stat().st_mtime
    os.utime(old, (now - TEMPORARY_AGE - 10, now - TEMPORARY_AGE - 10))
    assert clean_temporary(tmp_path, now=now) == 1 and not old.exists() and fresh.exists()


def test_rejects_an_unknown_program():
    draft = entry()
    draft['program'] = 'rm -rf'
    with pytest.raises(ValueError, match='Unknown program'):
        decode_entry(draft)


def test_leaves_a_saved_unchanged_tab_to_its_project(windows, tmp_path):
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.project_path = tmp_path / 'water.qcc'
    window.dirty = False
    window.new_document('Second', read_xyz(HELIUM))
    window.dirty = True
    assert window.recovery.capture()
    drafts = window.recovery.session.read()
    assert [read_project(d['project'])[0].formula for d in drafts] == [read_xyz(HELIUM).formula]


def test_deletes_the_copy_when_the_user_asks(windows, monkeypatch):
    window = windows()
    window.load_molecule(read_xyz(WATER))
    window.dirty = True
    window.recovery.capture()
    path = window.recovery.session.path
    window.recovery.finish(keep=True)
    restored = windows()
    approve(monkeypatch, QMessageBox.StandardButton.Discard)
    restored.recovery.recover()
    assert not path.exists() and not restored.molecule.atoms


def test_exit_does_not_save_a_crystal_tab_as_a_project(windows, tmp_path, monkeypatch):
    window = windows()
    first = tmp_path / 'first.qcc'
    window.load_molecule(read_xyz(WATER))
    window.project_path = first
    window.dirty = True
    window.crystal_tool.set_compass_mode('crystal')
    window.load_molecule(read_xyz(HELIUM))
    window.dirty = True
    asked = []
    def answer(parent, title, text, *rest):
        asked.append(title)
        if len(asked) == 1:
            return QMessageBox.StandardButton.Save
        return QMessageBox.StandardButton.Cancel
    monkeypatch.setattr(QMessageBox, 'question', answer)
    event = QCloseEvent()
    window.closeEvent(event)
    # the molecule tab is saved, the crystal one is not written as a .qcc; the exit asks and is cancelled
    assert read_project(first.read_text(encoding='utf-8'))[0].formula == read_xyz(WATER).formula
    assert asked[-1] == 'Несохранённый кристалл' and not event.isAccepted()
    assert window.document_kind == 'crystal' and window.recovery.session is not None
    assert not list(tmp_path.glob('*.qcc'))[1:]

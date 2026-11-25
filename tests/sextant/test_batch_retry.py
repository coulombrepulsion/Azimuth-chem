"""Independent retry oracles: only chosen records, corrected Cl− input, exact parent bytes, no job submission."""

from dataclasses import replace

import pytest

from azimuth.core import Atom, Calculation, read_xyz
from modules.sextant import batch, batch_retry
from tests.sextant.test_batch_browser import app, window, package  # noqa: F401 — shared isolated Qt fixtures


def test_only_selected_rows_become_fresh_waiting_jobs(tmp_path):
    parent = package(tmp_path / 'parent')
    before = (parent.folder / 'batch.json').read_bytes()
    calc = Calculation(method='PM6', task='Энергия')
    requests = [(k, parent.items[k].molecule, 0, 1, 'input') for k in (40, 43)]
    new = batch_retry.prepare(parent, requests, calc, 'mopac', 'local', tmp_path / 'jobs')
    assert [i.name for i in new.items] == ['Молекула 41', 'Молекула 44']
    assert all(i.state == 'waiting' and i.output == '' and i.folder == '' and i.geometry is None for i in new.items)
    assert new.extra['retry_of'] == str(parent.folder)
    assert [r['index'] for r in new.extra['retry_items']] == [41, 44]
    assert batch.Batch.load(new.folder).extra == new.extra
    assert (parent.folder / 'batch.json').read_bytes() == before


def test_invalid_spin_or_geometry_creates_no_package(tmp_path):
    parent = package(tmp_path / 'parent', count=2)
    chlorine = read_xyz('1\nchlorine\nCl 0 0 0')
    calc = Calculation(method='PM6', task='Энергия')
    root = tmp_path / 'jobs'
    requests = [(0, parent.items[0].molecule, 0, 1, 'input'), (1, chlorine, 0, 1, 'current')]
    with pytest.raises(ValueError):
        batch_retry.prepare(parent, requests, calc, 'mopac', 'local', root)
    assert not root.exists()
    collapsed = replace(chlorine, atoms=(Atom('Cl', 0, 0, 0), Atom('H', 0.002, 0, 0)))
    with pytest.raises(ValueError):
        batch_retry.prepare(parent, [(0, collapsed, 0, 1, 'current')], calc, 'mopac', 'local', root)
    assert not root.exists()
    requests[1] = (1, chlorine, -1, 1, 'current')
    new = batch_retry.prepare(parent, requests, calc, 'mopac', 'local', root)
    assert new.items[1].charge == -1 and new.items[1].multiplicity == 1
    from modules.sextant.inputs import input_files
    generated = next(iter(input_files('mopac', chlorine, replace(calc, charge=-1)).values()))
    assert 'CHARGE=-1' in generated and 'DOUBLET' not in generated


def test_invalid_indices_cannot_duplicate_jobs(tmp_path):
    parent = package(tmp_path / 'parent', count=2)
    calc = Calculation(method='PM6', task='Энергия')
    request = (0, parent.items[0].molecule, 0, 1, 'input')
    with pytest.raises(ValueError):
        batch_retry.prepare(parent, [request, request], calc, 'mopac', 'local', tmp_path / 'jobs')
    with pytest.raises(ValueError):
        batch_retry.prepare(parent, [], calc, 'mopac', 'local', tmp_path / 'jobs')
    assert not (tmp_path / 'jobs').exists()


def test_multi_selection_and_explicit_draft_creation(window):
    parent = package(window.run_tool.jobs_root() / 'parent')
    parent.calc = Calculation(method='PM6', task='Энергия')
    parent.items[0].geometry = None  # completed but unusable also counts as a problem
    parent.save()
    before = (parent.folder / 'batch.json').read_bytes()
    browser = window.batch_tool.show_saved_batches(parent.folder)
    browser.problems_button.click()
    assert browser.selected_indices() == [0, 40, 41, 42, 43]
    assert not browser.input_button.isEnabled() and not browser.result_button.isEnabled()
    dialog = browser.prepare_selected()
    assert len(dialog.rows) == 5 and dialog.created is None
    dialog.place.setCurrentIndex(dialog.place.findData('local'))
    dialog.create_button.click()
    assert dialog.created is not None and len(dialog.created.items) == 5
    assert window.batch is None
    assert window._batch_browser.resume_button.text() == 'Запустить пакет'
    assert (parent.folder / 'batch.json').read_bytes() == before


def test_original_structure_and_current_tab_can_correct_a_single_item(window):
    parent = package(window.run_tool.jobs_root() / 'parent', count=2)
    parent.items[0].molecule = read_xyz('1\nchlorine\nCl 0 0 0')
    parent.items[0].charge, parent.items[0].multiplicity = 0, 2
    parent.calc = Calculation(method='PM6', task='Энергия')
    parent.save()
    before = (parent.folder / 'batch.json').read_bytes()
    original_document = window.document()
    browser = window.batch_tool.show_saved_batches(parent.folder)
    browser.open_input_structure()
    assert window.document() is not original_document
    assert window.coordinate_tool.table_molecule().formula == 'Cl'
    assert window.charge.value() == 0 and window.spin.value() == 2
    assert window.program_kind() == 'mopac'
    browser = window.batch_tool.show_saved_batches(parent.folder)
    dialog = browser.prepare_selected()
    _, source, charge, spin, _ = dialog.rows[0]
    source.setCurrentIndex(source.findData('current'))
    charge.setValue(-1)
    spin.setValue(1)
    dialog.place.setCurrentIndex(dialog.place.findData('local'))
    dialog.create_button.click()
    assert dialog.created.items[0].molecule.formula == 'Cl'
    assert dialog.created.items[0].charge == -1 and dialog.created.items[0].multiplicity == 1
    assert dialog.created.extra['retry_items'][0]['geometry_source'] == 'current'
    assert window.batch is None and (parent.folder / 'batch.json').read_bytes() == before


def test_running_items_cannot_be_repeated_from_browser(window):
    parent = package(window.run_tool.jobs_root() / 'parent', count=2)
    parent.items[0].state = 'sent'
    parent.save()
    browser = window.batch_tool.show_saved_batches(parent.folder)
    assert not browser.retry_button.isEnabled()
    assert browser.prepare_selected() is None


def test_a_row_whose_sending_is_not_known_is_checked_not_repeated(window, monkeypatch):
    # no new attempt is prepared for it; «Проверить на сервере» asks the
    # server about the same sending (the row becomes 'sent' and the queue is taken up — nothing new is sent)
    parent = package(window.run_tool.jobs_root() / 'parent', count=2)
    parent.items[0].state = 'uncertain'
    parent.items[0].note = 'the answer of the server is not known'
    parent.save()
    browser = window.batch_tool.show_saved_batches(parent.folder)
    browser.table.selectRow(0)
    assert not browser.retry_button.isEnabled() and browser.prepare_selected() is None
    assert browser.check_button.isEnabled()
    assert 'Проверить на сервере' in browser.table.item(0, 5).text()
    taken = []
    monkeypatch.setattr(window.batch_tool, 'resume_batch', lambda folder=None: taken.append(folder) or 'resumed')
    browser.check_button.click()  # the button itself, not the method
    assert taken == [str(parent.folder)]
    assert batch.Batch.load(parent.folder).items[0].state == 'sent'
    browser = window.batch_tool.show_saved_batches(parent.folder)
    browser.table.selectRow(1)
    assert not browser.check_button.isEnabled()


def test_empty_output_diagnosis_is_available_without_geometry(window):
    parent = package(window.run_tool.jobs_root() / 'parent', count=2)
    output = parent.folder / 'empty.out'
    output.touch()
    parent.items[0].output = str(output)
    parent.items[0].state = 'failed'
    parent.save()
    browser = window.batch_tool.show_saved_batches(parent.folder)
    dialog = browser.inspect_selected()
    from PySide6.QtWidgets import QPlainTextEdit
    assert 'Файл результата пуст' in dialog.findChild(QPlainTextEdit).toPlainText()
    assert parent.items[0].state == 'failed'

"""Prepare a new package from selected calculations without overwriting or resubmitting the old ones.

Contract: inspect_item reads a local output only, returning a parsed geometry and a diagnostic. It never
changes the stored state: normal program termination does not prove that the requested calculation is correct.
prepare(parent, requests, calc, kind, place, root) validates every selected geometry and input before creating a
folder. Requests are (zero-based parent index, Molecule, charge, multiplicity, source label). All new items wait;
extra records parent folder/index and geometry source, but not server job IDs. No network/process is started.
Original files/states are immutable. UI allows explicit source/charge/spin choices and creates a draft; only the
existing start/resume action submits it. Tests check exact inputs, independent parent snapshots and zero submissions.
"""

from dataclasses import replace
from pathlib import Path

from azimuth.core import read_xyz
from azimuth.i18n import tr
from modules.sextant import batch, inputs


def inspect_item(item):
    """Return (geometry or None, diagnostic); read output without trusting its stored batch state."""
    from modules.spectrum.readers.outputs import read_any

    if not item.output or not Path(item.output).is_file():
        return None, tr('Файл результата отсутствует.')
    try:
        text = Path(item.output).read_text(encoding='utf-8', errors='replace')
        if not text.strip():
            return None, tr('Файл результата пуст. Причину нужно искать в журнале запуска или на сервере.')
        result = read_any(text)
        geometry = result.geometry
        if geometry is not None:
            read_xyz(geometry.xyz())
        message = (tr('В выводе есть нормальное завершение программы.') if result.normal_exit
                   else tr('В выводе нет подтверждения нормального завершения программы.'))
        message += ' ' + (tr('Геометрия прочитана. Это не подтверждает сходимость оптимизации или верность заряда.')
                          if geometry is not None else tr('Геометрия результата не прочитана.'))
        return geometry, message
    except (OSError, ValueError, KeyError, IndexError) as exc:
        return None, tr('Результат не прочитан: ') + str(exc)


def prepare(parent, requests, calc, kind, place, root):
    """Validate all inputs, then save a fresh waiting package. Never mutate parent or start work."""
    if not requests:
        raise ValueError(tr('Выберите хотя бы одну структуру.'))
    if place not in ('local', 'server'):
        raise ValueError(tr('Неизвестное место расчёта.'))
    if place == 'server':
        from modules.sextant.remote_job import REMOTE_KINDS

        if kind not in REMOTE_KINDS:
            raise ValueError(tr('Для этой программы выберите расчёт на этом компьютере.'))
    items, origins, seen = [], [], set()
    for index, molecule, charge, multiplicity, source in requests:
        if type(index) is not int or not 0 <= index < len(parent.items) or index in seen:
            raise ValueError(tr('Неверный или повторяющийся номер структуры.'))
        seen.add(index)
        item = parent.items[index]
        if item.state in batch.NOT_REPEATABLE:  # it runs, or may run, on the server — never twice
            raise ValueError(tr(f'{item.name}: расчёт идёт или мог быть принят сервером — повтор не готовится, пока '
                                'сервер не проверен.'))
        try:
            if molecule is None:
                raise ValueError(tr('Нет выбранной геометрии.'))
            read_xyz(molecule.xyz())  # finite coordinates, supported elements and minimum distances
            if type(charge) is not int or type(multiplicity) is not int:
                raise ValueError(tr('Заряд и мультиплетность должны быть целыми числами.'))
            chosen = replace(calc, charge=charge, multiplicity=multiplicity)
            inputs.input_files(kind, molecule, chosen)  # program-specific validation, no filesystem writes
        except (ValueError, KeyError) as exc:
            raise ValueError(f'{item.name}: {exc}') from exc
        items.append(batch.BatchItem(item.name, molecule, charge, multiplicity,
                                     props=dict(item.props), formal=tuple(item.formal)))
        origins.append({'index': index + 1, 'name': item.name, 'geometry_source': source})
    if parent.extra.get('project'):
        from azimuth.projects import Project, project_of_queue

        root = Project.load(project_of_queue(parent)).root / 'calculations'
    folder = batch.batch_folder(root, items[0].molecule, kind)
    retry = batch.Batch(kind, calc, items, folder, place=place, source=tr('Повтор · ') + parent.folder.name,
                        purpose=parent.purpose if parent.purpose in ('conformers', 'structures') else '',
                        extra={'retry_of': str(parent.folder), 'retry_items': origins})
    if parent.extra.get('project'):
        from azimuth.projects import attach, project_of_queue

        attach(retry, project_of_queue(parent), [parent.extra['project']['ids'][r[0]] for r in requests])
    else:
        retry.save()
    return retry


def retry_dialog(owner, parent, indices):
    """Build a nonmodal editor. Preparing writes a new package only after the user presses its button."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QAbstractItemView, QComboBox, QDialog, QHBoxLayout, QHeaderView,
                                   QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

    from azimuth.ui import button, label

    dialog = QDialog(owner)
    dialog.setWindowTitle(tr('Подготовить повтор выбранных расчётов'))
    layout = QVBoxLayout(dialog)
    note = label(tr('Проверьте геометрию, заряд и мультиплетность каждой строки. Будет создан новый пакет без запуска. '
                    'Исходный пакет останется без изменений. Для редактирования одной геометрии сначала используйте '
                    '«Исходная структура в Компас», затем выберите здесь текущую вкладку.'))
    if parent.extra.get('project'):
        note.setText(tr('Проверьте геометрию, заряд и мультиплетность. Расчёты добавятся к выбранным молекулам проекта. '
                        'Предыдущие попытки сохранятся. Запуск выполняется отдельно после подготовки очереди.'))
    layout.addWidget(note)
    settings = QComboBox()
    settings.addItem((tr('Настройки первой выбранной молекулы (для всех строк)') if parent.extra.get('project_selection')
                     else tr('Метод и задача исходного пакета')) + f' · {parent.kind.upper()} · {parent.calc.method} · '
                     + tr(parent.calc.task), 'parent')
    settings.addItem(tr('Текущие настройки Секстанта'), 'current')
    layout.addWidget(settings)
    table = QTableWidget(len(indices), 5)
    table.setHorizontalHeaderLabels([tr('Структура'), tr('Геометрия'), tr('Заряд'), tr('Мультиплетность'), tr('Вывод')])
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setWordWrap(False)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    for column in (0, 4):
        table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeMode.Stretch)
    widgets = []
    for row, index in enumerate(indices):
        item = parent.items[index]
        geometry, diagnostic = inspect_item(item)
        sources = QComboBox()
        sources.addItem(tr('Исходная'), 'input')
        if geometry is not None:
            sources.addItem(tr('Из результата'), 'output')
        if len(indices) == 1:
            sources.addItem(tr('Текущая вкладка Компаса'), 'current')
        charge, spin = QSpinBox(), QSpinBox()
        charge.setRange(min(-20, item.charge), max(20, item.charge))
        spin.setRange(1, max(30, item.multiplicity))
        charge.setValue(item.charge)
        spin.setValue(item.multiplicity)
        name_cell = QTableWidgetItem(item.name + '\n' + item.molecule.formula)
        name_cell.setToolTip(name_cell.text())
        table.setItem(row, 0, name_cell)
        table.setVerticalHeaderItem(row, QTableWidgetItem(str(index + 1)))
        for column, widget in ((1, sources), (2, charge), (3, spin)):
            holder = QWidget()
            cell_layout = QHBoxLayout(holder)
            cell_layout.setContentsMargins(4, 4, 4, 4)
            cell_layout.addWidget(widget, 1, Qt.AlignmentFlag.AlignVCenter)
            table.setCellWidget(row, column, holder)
        cell = QTableWidgetItem(diagnostic)
        cell.setToolTip(diagnostic)
        table.setItem(row, 4, cell)
        widgets.append((index, sources, charge, spin, geometry))

        def show_formula(_value, row=row, item=item, sources=sources, geometry=geometry):
            source = sources.currentData()
            molecule = (owner.coordinate_tool.table_molecule() if source == 'current' else
                        geometry if source == 'output' else item.molecule)
            table.item(row, 0).setText(item.name + '\n' + (molecule.formula if molecule is not None else ''))
            table.item(row, 0).setToolTip(table.item(row, 0).text())

        sources.currentIndexChanged.connect(show_formula)
        table.setRowHeight(row, 64)
    layout.addWidget(table, 1)
    error = label('', 'subtitle')
    error.setTextFormat(Qt.TextFormat.PlainText)
    layout.addWidget(error)
    row = QHBoxLayout()

    def create():
        try:
            calc = owner.calculation() if settings.currentData() == 'current' else parent.calc
            kind = owner.program_kind() if settings.currentData() == 'current' else parent.kind
            requests = []
            for index, sources, charge, spin, geometry in widgets:
                source = sources.currentData()
                molecule = (owner.coordinate_tool.table_molecule() if source == 'current' else
                            geometry if source == 'output' else parent.items[index].molecule)
                requests.append((index, molecule, charge.value(), spin.value(), source))
            retry = prepare(parent, requests, calc, kind, place.currentData(), owner.run_tool.jobs_root())
        except (OSError, ValueError, KeyError) as exc:
            error.setText(str(exc))
            return None
        if hasattr(owner, 'batch_tool'):
            owner.batch_tool.with_conformer_search(retry)
            retry.save()
        dialog.created = retry
        dialog.accept()
        owner.batch_tool.show_saved_batches(retry.folder)
        owner.notify(tr('Новый пакет подготовлен. Проверьте строки и нажмите «Запустить пакет».'), 10000)
        return retry

    place = QComboBox()
    place.addItem(tr('Этот компьютер'), 'local')
    place.addItem(tr('Сервер'), 'server')
    place.setCurrentIndex(place.findData(parent.place))
    row.addWidget(place)
    create_button = button(tr('Создать новый пакет'), create, True)
    row.addWidget(create_button)
    row.addStretch(1)
    row.addWidget(button(tr('Отмена'), dialog.reject))
    layout.addLayout(row)
    dialog.rows, dialog.settings, dialog.place = widgets, settings, place
    dialog.create_button, dialog.error, dialog.created = create_button, error, None
    dialog.resize(1100, 660)
    return dialog

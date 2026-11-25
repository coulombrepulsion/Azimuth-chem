"""«Найти в NIST…» of the button «Эксперимент и конформеры»: a measured IR or UV-Vis spectrum from the NIST
Chemistry WebBook laid over the computed one (modules/spectrum/readers/nist.py).

A measured spectrum from the NIST Chemistry WebBook.
NistWindow(panel, kind, text): the search (the formula of the result put in; a name or a CAS number typed instead), the
compounds found, the spectra of the one chosen (the phase, the way it was measured, its source), «Наложить на график».
The requests in a worker thread (threading + a queued signal, as «Найти кристалл в COD…»); search_function and
spectra_function replaced in the tests (no network there). busy — a request is running.
"""

import threading

from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QDialog, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QTableWidget, QTableWidgetItem,
                               QVBoxLayout)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.spectrum.readers import nist


class _Relay(QObject):
    done = Signal(object)


class NistWindow(QDialog):
    def __init__(self, panel, kind='IR', text=''):
        super().__init__(panel)
        self.panel, self.kind, self.busy = panel, kind, False
        self.found, self.chosen, self.shown_spectra = [], None, []
        self.search_function, self.spectra_function = nist.search, nist.spectra
        self.relay = _Relay(self)
        self.relay.done.connect(self.answer)
        self.setWindowTitle(tr('Спектр из NIST'))
        layout = QVBoxLayout(self)
        note = QLabel(tr('NIST Chemistry WebBook — измеренные спектры: ИК чаще всего газовой фазы (база NIST/EPA), у '
                         'части веществ — конденсированной фазы; UV-Vis. Нужен интернет; отправляются только условия '
                         'поиска.') if kind == 'IR' else
                      tr('NIST Chemistry WebBook — измеренные спектры UV-Vis (для части веществ). Нужен интернет; '
                         'отправляются только условия поиска.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        row = QHBoxLayout()
        self.query = QLineEdit(text)
        self.query.setPlaceholderText(tr('формула (C8H10N4O2), название по-английски (caffeine) или номер CAS (58-08-2)'))
        self.query.returnPressed.connect(self.find)
        row.addWidget(self.query, 1)
        self.find_button = action_button(tr('Найти'), self.find, 'search')
        row.addWidget(self.find_button)
        layout.addLayout(row)
        self.status = QLabel('')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.compounds = self._table([tr('Вещество'), tr('Код NIST')])
        self.compounds.itemSelectionChanged.connect(self.compound_chosen)
        layout.addWidget(self.compounds, 1)
        self.spectra = self._table([tr('№'), tr('Спектр')])
        self.spectra.itemSelectionChanged.connect(self._selected)
        self.spectra.cellDoubleClicked.connect(lambda r, _c: self.use(r))
        layout.addWidget(self.spectra, 1)
        bottom = QHBoxLayout()
        self.use_button = action_button(tr('Наложить на график'), lambda: self.use(), 'import')
        self.page_button = action_button(tr('Страница в NIST'), self.open_page, 'link')
        bottom.addWidget(self.use_button)
        bottom.addWidget(self.page_button)
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.reject, 'close'))
        layout.addLayout(bottom)
        self._selected()
        self.resize(720, 520)

    @staticmethod
    def _table(headers):
        table = QTableWidget(0, len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        table.horizontalHeader().setStretchLastSection(True)
        return table

    @staticmethod
    def _row(table):
        rows = sorted({i.row() for i in table.selectedIndexes()})
        return rows[0] if rows else None

    def _selected(self):
        row = self._row(self.spectra)
        self.use_button.setEnabled(not self.busy and row is not None and row < len(self.shown_spectra))
        self.page_button.setEnabled(self.chosen is not None)

    def _run(self, kind, job):
        self.busy = True
        self.find_button.setEnabled(False)
        self._selected()
        relay = self.relay

        def work():
            try:
                relay.done.emit((kind, job(), None))
            except Exception as exc:  # no network, a timeout, a page not as expected: said in the status line
                relay.done.emit((kind, None, exc))

        threading.Thread(target=work, daemon=True).start()
        return True

    def find(self):
        text = self.query.text().strip()
        if self.busy or not text:
            return False
        self.status.setText(tr('Ищу в NIST…'))
        search = self.search_function
        return self._run('search', lambda: search(text))

    def compound_chosen(self):
        row = self._row(self.compounds)
        if self.busy or row is None or not 0 <= row < len(self.found):
            return False
        self.chosen = self.found[row]
        self.status.setText(tr('Загружаю спектры «{}»…').format(self.chosen[1]))
        spectra, kind, ident = self.spectra_function, self.kind, self.chosen[0]
        return self._run('spectra', lambda: spectra(ident, kind))

    def answer(self, message):
        kind, payload, error = message
        self.busy = False
        self.find_button.setEnabled(True)
        if error is not None:
            self.status.setText(self.problem(error))
            self._selected()
            return None
        if kind == 'search':
            self.found, self.chosen, self.shown_spectra = list(payload), None, []
            self.spectra.setRowCount(0)
            self.compounds.blockSignals(True)
            self.compounds.setRowCount(len(self.found))
            for k, (ident, name) in enumerate(self.found):
                self.compounds.setItem(k, 0, QTableWidgetItem(name))
                self.compounds.setItem(k, 1, QTableWidgetItem(ident))
            self.compounds.blockSignals(False)
            self.status.setText(tr('Ничего не найдено. Попробуйте название по-английски или номер CAS.')
                                if not self.found else tr('Найдено веществ: {}. Выберите вещество.').format(len(self.found)))
            if len(self.found) == 1:
                self.compounds.selectRow(0)
            self._selected()
            return self.found
        self.shown_spectra = list(payload)
        self.spectra.setRowCount(len(self.shown_spectra))
        for k, (index, description, _text) in enumerate(self.shown_spectra):
            self.spectra.setItem(k, 0, QTableWidgetItem(str(index + 1)))
            self.spectra.setItem(k, 1, QTableWidgetItem(description or tr('без описания')))
        name = self.chosen[1] if self.chosen else ''
        if not self.shown_spectra:
            self.status.setText(tr('У «{}» в NIST нет спектра ИК.').format(name) if self.kind == 'IR' else
                                tr('У «{}» в NIST нет спектра UV-Vis.').format(name))
        else:
            self.status.setText(tr('Спектров: {}. Двойной щелчок — наложить на график.').format(len(self.shown_spectra)))
            self.spectra.selectRow(0)
        self._selected()
        return self.shown_spectra

    def use(self, row=None):
        from modules.spectrum.analysis import experiment

        row = self._row(self.spectra) if row is None else row
        if self.busy or row is None or not 0 <= row < len(self.shown_spectra):
            return None
        index, description, text = self.shown_spectra[row]
        name = (self.chosen[1] if self.chosen else '') + ' · NIST'
        try:
            measured = experiment.parse(text, name)
        except ValueError as exc:
            self.status.setText(str(exc))
            return None
        said = self.panel.use_experiment(replace_name(measured, name), name)
        if said:
            self.accept()
        return said

    def open_page(self):
        if self.chosen is None:
            return False
        return QDesktopServices.openUrl(QUrl(nist.PAGE.format(self.chosen[0])))

    @staticmethod
    def problem(error):
        from modules.compass.chemistry import pubchem

        if isinstance(error, ValueError):
            return str(error)
        why = pubchem.reason(error)
        return {
            'certificate': tr('NIST: не удалось проверить сертификат сервера. Python с python.org не знает корневых '
                              'сертификатов — запустите «Install Certificates.command» из папки Python в «Программах».'),
            'timeout': tr('NIST не ответил вовремя — попробуйте ещё раз.'),
            'server': tr('NIST ответил ошибкой: ') + str(getattr(error, 'code', '')),
        }.get(why, tr('NIST недоступен — проверьте подключение к интернету.') + ' (' +
              str(getattr(error, 'reason', error))[:120] + ')')


def replace_name(measured, name):
    from dataclasses import replace

    return replace(measured, name=name)

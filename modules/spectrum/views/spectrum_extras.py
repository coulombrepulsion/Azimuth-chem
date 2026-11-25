"""The button «Эксперимент и конформеры» of the IR (Raman) and the UV-Vis (ECD) spectra.

Two additions of Spectrum:
  · «Экспериментальный спектр…» — a measured spectrum (JCAMP-DX, CSV, text) over the computed one, with how alike they
    are; «Подогнать к эксперименту» — the factor of the frequencies (IR) or the shift of the energies (UV-Vis, ECD) with
    which they are most alike, put into the plot;
  · «Среднее по конформерам…» — the outputs of the conformers, their Boltzmann shares (a table, the temperature), and
    their spectra added by them (modules/spectrum/analysis/ensemble.py).
The core is in modules/spectrum/analysis/experiment.py and ensemble.py; here the menu, the dialogs and the messages.

ExtrasMixin — for a panel with: plot (the widget with .experiment, .ensemble, .score()), EXPERIMENT_AXIS ('cm-1' or
'nm'), signed() -> bool, fit_values, fit_curve(value) -> (x, y), apply_fit(value) -> text, fit_neutral -> value,
ensemble_lists(outputs) -> lists of the lines, set_ensemble_lines(lines, name) and source_path (the file of the result).
"""

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFileDialog, QMenu, QPushButton

from azimuth.i18n import tr
from modules.spectrum.views.tools_view import EnergiesDialog

def num(value, spec):
    """A number for a message: with the decimal comma in Russian."""
    from azimuth import i18n

    text = format(value, spec)
    return text.replace('.', ',') if i18n.LANG == 'ru' else text


FILTER = 'Спектры (*.jdx *.dx *.jcamp *.csv *.txt *.dat *.tsv *.xy *.prn);;Все файлы (*)'


class ConformersDialog(EnergiesDialog):
    """«Энергии из нескольких файлов» with a button that builds the average spectrum of them. «Закрыть» only closes —
    the average is asked for by
    its own signal (build), not by accepted, which «Закрыть» of EnergiesDialog gives too."""

    build = Signal(list, float)  # the paths, the temperature

    def __init__(self, owner, paths=None, temperature=298.15):
        super().__init__(owner, paths, temperature)
        from azimuth.ui import button

        self.setWindowTitle(tr('Среднее по конформерам'))
        from azimuth.ui import label

        hint = label(tr('Добавьте выводы конформеров той же молекулы, посчитанных одним методом; показанный результат '
                        'уже в списке. Доли — по G, если у всех есть частоты, иначе по E.'), 'subtitle')
        hint.setWordWrap(True)
        self.layout().insertWidget(0, hint)
        self.build_button = button(tr('Построить средний спектр'), self.build_average, True)
        self.build_button.setToolTip(tr('Сложить спектры конформеров с их долями по Больцману'))
        bottom = self.layout().itemAt(self.layout().count() - 1).layout()
        bottom.insertWidget(bottom.count() - 1, self.build_button)
        self.build_button.setEnabled(len(self.paths) > 1 and self.table.rowCount() > 1)

    def build_average(self):
        paths, temperature = list(self.paths), self.temperature.value()
        self.accept()
        self.build.emit(paths, temperature)

    def choose(self):
        """The files chosen are added to the list (the result shown stays in it)."""
        from modules.spectrum.views.reaction_view import RESULT_FILTER

        paths, _ = QFileDialog.getOpenFileNames(self, tr('Результаты расчётов'), '', tr(RESULT_FILTER))
        if paths:
            self.fill(self.paths + [p for p in paths if p not in self.paths])
        return paths

    def fill(self, paths, read=None):
        found = super().fill(paths, read)
        if hasattr(self, 'build_button'):
            self.build_button.setEnabled(bool(found) and len(found['rows']) > 1)
        return found


class ExtrasMixin:
    experiment_raw = None
    ensemble_data = None
    source_path = None
    source_formula = ''  # the formula of the result — the search of «Найти в NIST…»
    NIST_KIND = 'IR'

    def make_extras_button(self, echo_layout=None):
        """The icon with the menu; a line of messages (StatusEcho) — into echo_layout, hidden."""
        from azimuth.icons import iconify
        from azimuth.ui import StatusEcho

        self.extras_button = iconify(QPushButton(), 'experiment',
                                     tr('Эксперимент и конформеры · наложить измеренный спектр, подогнать к нему, '
                                        'усреднить спектры конформеров по Больцману'))
        self.extras_button.clicked.connect(self.extras_menu)
        self.extras_echo = StatusEcho()
        if echo_layout is not None:
            echo_layout.addWidget(self.extras_echo)
        return self.extras_button

    def extras_menu(self, *args):
        """The menu under the button (as the menu of the NTO: a popup, no arrow drawn on the icon)."""
        from azimuth.ui import rounded

        menu = rounded(QMenu(self))
        self._fill_extras_menu(menu)
        menu.popup(self.extras_button.mapToGlobal(self.extras_button.rect().bottomLeft()))
        self.extras_popup = menu
        return menu

    def _fill_extras_menu(self, menu):
        menu.addAction(tr('Экспериментальный спектр…'), lambda: self.open_experiment())
        menu.addAction(tr('Найти в NIST…'), lambda: self.open_nist())
        fit = menu.addAction(tr('Подогнать к эксперименту'), lambda: self.fit_experiment())
        fit.setEnabled(self.experiment_raw is not None)
        fit.setToolTip(self.fit_hint())
        menu.setToolTipsVisible(True)
        drop = menu.addAction(tr('Убрать эксперимент'), lambda: self.clear_experiment())
        drop.setEnabled(self.experiment_raw is not None)
        menu.addSeparator()
        menu.addAction(tr('Среднее по конформерам…'), lambda: self.open_conformers())
        drop = menu.addAction(tr('Убрать среднее'), lambda: self.clear_conformers())
        drop.setEnabled(self.ensemble_data is not None)
        self.extra_actions(menu)

    def extra_actions(self, menu):
        """A panel's own items at the end of the menu."""

    def tell(self, text):
        self.extras_echo.setText(text)
        return text

    # -- the experiment ------------------------------------------------------------------------------------------------
    def open_experiment(self, path=None):
        from modules.spectrum.analysis import experiment
        from modules.spectrum.views.spectrum_common import show_error

        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, tr('Экспериментальный спектр'), str(Path.home()), tr(FILTER))
        if not path:
            return None
        try:
            measured = experiment.read(path)
        except ValueError as exc:
            show_error(self, str(exc))
            return None
        return self.use_experiment(measured, Path(path).name)

    def use_experiment(self, measured, label):
        """The measured spectrum (experiment.Experiment) over the plot; the message said, or None."""
        from modules.spectrum.views.spectrum_common import show_error

        try:
            self.experiment_raw = measured
            self.show_experiment()
        except ValueError as exc:
            self.experiment_raw = None
            self.plot.experiment = None
            self.plot.update()
            show_error(self, str(exc))
            return None
        # fitted at once — the factor (IR) or the shift
        # (UV-Vis, ECD) with which the spectra are most alike; «Подогнать к эксперименту» again after a change
        fitted = self.fit_experiment(quiet=True)
        score = self.plot.score()
        return self.tell(tr('Эксперимент: {}.').format(label) + ' ' + (
            fitted or ('' if score is None else tr('Сходство с расчётом: {}.').format(num(score, '.2f')))))

    def open_nist(self, text=None):
        """«Найти в NIST…»: the window of the search, the formula of the result put in."""
        from modules.spectrum.views.nist_window import NistWindow

        window = NistWindow(self, self.NIST_KIND, self.source_formula if text is None else text)
        self.nist_window = window
        window.show()
        if window.query.text():
            window.find()
        return window

    def show_experiment(self):
        """The measured spectrum on the axis of the plot (again when the view changes: ECD is signed)."""
        from modules.spectrum.analysis import experiment

        if self.experiment_raw is None:
            self.plot.experiment = None
        else:
            x, y = experiment.on_axis(self.experiment_raw, self.EXPERIMENT_AXIS, signed=self.signed())
            self.plot.experiment = (tuple(x.tolist()), tuple(y.tolist()), self.experiment_raw.name)
        self.plot.update()

    def clear_experiment(self):
        self.experiment_raw = None
        self.show_experiment()

    def fit_experiment(self, quiet=False):
        """The best factor (shift) put into the plot; quiet — nothing said when the spectra do not overlap."""
        from modules.spectrum.analysis import experiment
        from modules.spectrum.views.spectrum_common import show_error

        if self.plot.experiment is None:
            return None
        before = self.plot.score()
        try:
            value, score = experiment.best(self.fit_curve, self.fit_values, self.plot.experiment[:2], self.signed())
        except ValueError as exc:
            if not quiet:
                show_error(self, str(exc))
            return None
        what = self.apply_fit(value)
        self.plot.update()
        text = tr('Лучше всего совпадает: {} — сходство {}').format(what, num(score, '.2f'))
        if before is not None:
            text += tr(' (было {})').format(num(before, '.2f'))
        return text + '.' if quiet else self.tell(text + '.')

    # -- the conformers ------------------------------------------------------------------------------------------------
    def open_conformers(self, paths=None, temperature=None):
        """The dialog of the shares (the result shown is in it already); its button builds the average."""
        from azimuth.ui import open_window

        start = list(paths) if paths else ([self.source_path] if self.source_path else [])
        dialog = ConformersDialog(self, start, temperature or 298.15)
        dialog.build.connect(self.build_conformers)
        open_window(dialog)
        self.conformers_dialog = dialog
        return dialog

    def build_conformers(self, paths, temperature):
        from azimuth import defaults
        from modules.spectrum.analysis import ensemble
        from modules.spectrum.views.spectrum_common import show_error

        try:
            data = ensemble.conformers(paths, temperature, defaults.energy_factor())
        except ValueError as exc:
            show_error(self, str(exc))
            return None
        lists = self.ensemble_lists(data['outputs'])
        lacking = ensemble.missing(data['names'], lists)
        if lacking:
            show_error(self, self.lacking_text() + ', '.join(lacking) + '.')
            return None
        self.ensemble_data = data
        self.show_ensemble()
        shares = ', '.join(f'{name} {100 * share:.0f} %' for name, share in zip(data['names'], data['shares']))
        by = tr('по G') if data['by'] == 'G' else tr('по E')
        text = tr('Среднее по {} конформерам ({}, {} K): {}.').format(len(paths), by, num(temperature, 'g'), shares)
        # the warnings (composition, level, charges) were in the note of the dialog before its button; said again here
        return self.tell(' '.join([text] + [tr(w) for w in data['warnings']]))

    def show_ensemble(self):
        from modules.spectrum.analysis import ensemble

        data = self.ensemble_data
        if data is None:
            self.set_ensemble_lines(None, '')
            return
        lines = ensemble.weighted_excitations if self.EXPERIMENT_AXIS == 'nm' else ensemble.weighted_modes
        by = 'G' if data['by'] == 'G' else 'E'
        self.set_ensemble_lines(lines(self.ensemble_lists(data['outputs']), data['shares']),
                                tr('среднее по {} конформерам ({})').format(len(data['paths']), by))

    def clear_conformers(self):
        self.ensemble_data = None
        self.show_ensemble()

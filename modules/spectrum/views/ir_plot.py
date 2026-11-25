"""The plot of an IR or Raman spectrum (a Qt widget; moved here from modules/spectrum/analysis/ir_spectrum.py,
which keeps the broadening). Contract: docs/features/IR_SPECTRUM.md.

The same plot draws a Raman spectrum — the modes of raman.raman_modes carry the activity (A^4/amu) or the
relative intensity in «intensity»; IRSpectrum.kind ('ir', 'activity', 'intensity') names the axis, the empty plot,
the CSV columns and the SVG title.

Experiment (x cm⁻¹, y normalised, name) — a measured spectrum drawn green over the computed one, as high as the plot,
with how alike they are (experiment.similarity) in the legend; ensemble (modes, name) — the spectrum of the conformers
averaged by their Boltzmann shares (ensemble.weighted_modes), violet; the factor of the frequencies applies to it
too."""

from math import isfinite
import numpy as np
from PySide6.QtCore import Qt, Signal, QPointF, QSize
from PySide6.QtGui import QPainter, QPainterPath, QPen, QColor
from PySide6.QtWidgets import QWidget
from PySide6.QtSvg import QSvgGenerator
from azimuth.i18n import tr
from modules.spectrum.analysis.ir_spectrum import broaden, lines


class IRSpectrum(QWidget):
    selected = Signal(int)

    def __init__(self):
        super().__init__()
        self.modes = ()
        self.reference = None  # (modes, name) of a second result drawn for comparison
        self.current = -1
        self.smooth = False
        self.width_cm = 20.0
        self.kind = 'ir'  # 'ir', or the Raman 'activity' / 'intensity' (raman.KINDS)
        self.scale = 1.0  # the frequencies of the spectrum × scale (set_scale); the modes stay as read
        self._original = ()
        self._cache = None
        self.experiment = None  # (x cm⁻¹, y with max 1, name) of a measured spectrum
        self.ensemble = None  # (modes, name) — the average of conformers, unscaled
        self._score = None
        self.setMinimumHeight(180)
        self.setToolTip(
            tr(
                'Щелчок выбирает ближайшую исходную моду. Гауссово уширение — модель; мнимые и нулевые частоты исключены.'
            )
        )

    def set_scale(self, factor):
        """Draw (and export) the frequencies multiplied by factor; 1.0 — as the program computed them."""
        from dataclasses import replace

        if not isfinite(factor) or not 0.5 <= factor <= 1.5:
            raise ValueError(tr('Множитель частот — от 0,5 до 1,5.'))
        original = self._original if self.scale != 1.0 and self._original else self.modes
        self.scale = float(factor)
        self._original = tuple(original)
        self.modes = self._original if self.scale == 1.0 else tuple(
            replace(m, frequency=m.frequency * self.scale) for m in self._original)
        self._cache = None
        self.update()

    def curve(self):
        if self._cache is None or self._cache[0] is not self.modes or self._cache[1] != self.width_cm:
            self._cache = (self.modes, self.width_cm, self._broaden(self.modes))
        return self._cache[2]

    # -- VCD (kind 'vcd') — a signed spectrum: the zero line in the middle, bands up and down ------------
    @property
    def signed(self):
        return self.kind == 'vcd'

    def _lines(self, modes):
        return lines(modes, self.signed)

    def _broaden(self, modes):
        return broaden(modes, self.width_cm, self.signed)

    def zero_y(self):
        return self.height() - 32 - (max(1, self.height() - 75) / 2 if self.signed else 0)

    def ensemble_modes(self):
        """The modes of the average of conformers as drawn: × the factor of the frequencies too."""
        if not self.ensemble:
            return ()
        from dataclasses import replace

        modes = self.ensemble[0]
        return tuple(modes) if self.scale == 1.0 else tuple(replace(m, frequency=m.frequency * self.scale) for m in modes)

    def compared_curve(self):
        """The curve compared with the experiment: the average of conformers when there is one, else this result —
        broadened with the width of the plot (in the view of sticks too)."""
        modes = self.ensemble_modes() if self.ensemble else self.modes
        return self._broaden(modes)

    def score(self):
        """How alike the computed spectrum and the measured one are (cosine, 0…1), or None."""
        if not self.experiment:
            return None
        key = (id(self.modes), id(self.ensemble), self.width_cm, self.scale, id(self.experiment))
        if self._score is None or self._score[0] != key:
            from modules.spectrum.analysis.experiment import similarity

            try:
                value = similarity(self.compared_curve(), self.experiment[:2], self.signed)
            except ValueError:
                value = None
            self._score = (key, value)
        return self._score[1]

    def limits(self):
        values = self._lines(self.modes)
        other = self._lines(self.reference[0]) if self.reference else []
        other = other + self._lines(self.ensemble_modes())
        if self.smooth:
            x, y = self.curve()
            xmax, ymax = float(x[-1]), max(1e-12, float(abs(y).max()))
            if self.reference and self._lines(self.reference[0]):
                rx, ry = self._broaden(self.reference[0])
                xmax, ymax = max(xmax, float(rx[-1])), max(ymax, float(abs(ry).max()))
            if self.ensemble and self._lines(self.ensemble_modes()):
                rx, ry = self._broaden(self.ensemble_modes())
                xmax, ymax = max(xmax, float(rx[-1])), max(ymax, float(abs(ry).max()))
            return xmax, ymax
        both = values + other
        return max(4000.0, max((m.frequency * 1.05 for _, m in both), default=0.0)), max(
            1e-12, max((abs(m.intensity) for _, m in both), default=0.0)
        )

    REFERENCE_INK = '#e0709a'

    def draw_reference(self, p, xmax, ymax):
        """The second spectrum: a dashed curve or thin sticks, and the two names as a legend."""
        modes, name = self.reference
        ink = QColor(self.REFERENCE_INK)
        if self.smooth:
            x, y = self._broaden(modes)
            path = QPainterPath()
            path.moveTo(self.point(x[0], y[0], xmax, ymax))
            for a, b in zip(x[1:], y[1:]):
                path.lineTo(self.point(a, b, xmax, ymax))
            p.setPen(QPen(ink, 1.6, Qt.PenStyle.DashLine))
            p.drawPath(path)
        else:
            p.setPen(QPen(ink, 1.2))
            for _, m in self._lines(modes):
                point = self.point(m.frequency, m.intensity, xmax, ymax)
                p.drawLine(QPointF(point.x() + 2, self.zero_y()), QPointF(point.x() + 2, point.y()))

    ENSEMBLE_INK, EXPERIMENT_INK = '#9b6fd6', '#2f9e66'

    def draw_ensemble(self, p, xmax, ymax):
        """The average of conformers — a violet curve, or violet sticks a little to the left."""
        modes = self.ensemble_modes()
        ink = QColor(self.ENSEMBLE_INK)
        if self.smooth:
            x, y = self._broaden(modes)
            path = QPainterPath()
            path.moveTo(self.point(x[0], y[0], xmax, ymax))
            for a, b in zip(x[1:], y[1:]):
                path.lineTo(self.point(a, b, xmax, ymax))
            p.setPen(QPen(ink, 1.8))
            p.drawPath(path)
        else:
            p.setPen(QPen(ink, 1.4))
            for _, m in self._lines(modes):
                point = self.point(m.frequency, m.intensity, xmax, ymax)
                p.drawLine(QPointF(point.x() - 2, self.zero_y()), QPointF(point.x() - 2, point.y()))

    def draw_experiment(self, p, xmax, ymax):
        """The measured spectrum, green, its highest band at the top of the plot."""
        x, y = np.asarray(self.experiment[0]), np.asarray(self.experiment[1])
        keep = (x >= 0) & (x <= xmax)
        if keep.sum() < 2:
            return
        x, y = x[keep], y[keep] * ymax * 0.95
        path = QPainterPath()
        path.moveTo(self.point(x[0], y[0], xmax, ymax))
        for a, b in zip(x[1:], y[1:]):
            path.lineTo(self.point(a, b, xmax, ymax))
        p.setPen(QPen(QColor(self.EXPERIMENT_INK), 1.5))
        p.drawPath(path)

    def legend(self):
        """(ink, text) of what is drawn, when more than this result is."""
        entries = []
        if self.reference and self._lines(self.reference[0]):
            entries.append((self.REFERENCE_INK, ('- - ' if self.smooth else '— ') + self.reference[1][:34]))
        if self.ensemble and self._lines(self.ensemble_modes()):
            entries.append((self.ENSEMBLE_INK, '— ' + self.ensemble[1][:40]))
        if self.experiment:
            score = self.score()
            from modules.spectrum.views.spectrum_extras import num

            alike = '' if score is None else ' · ' + tr('сходство {}').format(num(score, '.2f'))
            entries.append((self.EXPERIMENT_INK, '— ' + tr('эксперимент: ') + self.experiment[2][:28] + alike))
        if entries:
            entries.insert(0, ('#6ea2f0', '— ' + tr('этот результат')))
        return entries

    def draw_legend(self, p):
        entries = self.legend()
        if not entries:
            return
        widest = max(p.fontMetrics().horizontalAdvance(text) for _, text in entries)
        left = max(60, self.width() - widest - 24)
        for k, (ink, text) in enumerate(entries):
            p.setPen(QColor(ink))
            p.drawText(left, 18 + 16 * k, text)

    def point(self, x, y, xmax, ymax):
        h = max(1, self.height() - 75)
        return QPointF(
            52 + (xmax - x) / xmax * max(1, self.width() - 70),
            self.zero_y() - y / ymax * (h / 2 if self.signed else h),
        )

    def peaks(self):
        xmax, ymax = self.limits()
        return [
            (i, self.point(m.frequency, m.intensity if not self.smooth else 0, xmax, ymax))
            for i, m in self._lines(self.modes)
        ]

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        from azimuth.ui import frame_plot  # the border of the plot (light theme)

        frame_plot(p, self)
        p.setPen(self.palette().text().color())
        if not self._lines(self.modes):
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       tr('ИК-интенсивности недоступны') if self.kind == 'ir' else
                       tr('Вращательных сил ВКД нет') if self.signed else tr('Активности Рамана недоступны'))
            return
        try:
            xmax, ymax = self.limits()
        except ValueError as exc:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, str(exc))
            return
        p.drawText(6, 18, self.axis_title())
        p.drawText(5, 38, '1' if self.smooth else f'{ymax:.3g}')
        if self.signed:  # VCD — the lower end of the axis and the zero line
            p.drawText(5, self.height() - 36, '−1' if self.smooth else f'{-ymax:.3g}')
        if self.smooth:
            p.drawText(130, 18, tr(f'Гаусс · FWHM {self.width_cm:g} см⁻¹'))
        if self.scale != 1.0:  # the spectrum is not the one of the output — said on it (and on a picture of it)
            # ends before it
            from modules.spectrum.views.spectrum_extras import num

            said = tr('частоты × {}').format(num(self.scale, '.3f'))
            p.drawText(self.width() - 60 - p.fontMetrics().horizontalAdvance(said), self.height() - 10, said)
        p.drawText(52, self.height() - 10, f'{xmax:.0f}')
        p.drawText(self.width() - 48, self.height() - 10, '0')
        p.drawText(self.width() // 2 - 20, self.height() - 10, tr('см⁻¹'))
        p.setPen(QPen(self.palette().mid().color(), 1))
        p.drawLine(52, 32, 52, self.height() - 32)
        p.drawLine(52, self.height() - 32, self.width() - 18, self.height() - 32)
        if self.signed:
            p.drawLine(QPointF(52, self.zero_y()), QPointF(self.width() - 18, self.zero_y()))
        if self.reference and self._lines(self.reference[0]):
            self.draw_reference(p, xmax, ymax)
        if self.experiment:
            self.draw_experiment(p, xmax, ymax)
        if self.ensemble and self._lines(self.ensemble_modes()):
            self.draw_ensemble(p, xmax, ymax)
        if self.smooth:
            x, y = self.curve()
            path = QPainterPath()
            path.moveTo(self.point(x[0], y[0], xmax, ymax))
            for a, b in zip(x[1:], y[1:]):
                path.lineTo(self.point(a, b, xmax, ymax))
            p.setPen(QPen(QColor('#6ea2f0'), 2))
            p.drawPath(path)
            if 0 <= self.current < len(self.modes):
                m = self.modes[self.current]
                if m.frequency > 0 and m.intensity is not None:
                    a = self.point(m.frequency, 0, xmax, ymax)
                    b = self.point(m.frequency, float(np.interp(m.frequency, x, y)), xmax, ymax)
                    p.setPen(QPen(QColor('#ffb454'), 2, Qt.PenStyle.DashLine))
                    p.drawLine(a, b)
        else:
            for i, point in self.peaks():
                p.setPen(QPen(QColor('#ffb454' if i == self.current else '#6ea2f0'), 3 if i == self.current else 2))
                p.drawLine(QPointF(point.x(), self.zero_y()), point)
        self.draw_legend(p)

    def axis_title(self):
        """What the vertical axis shows."""
        if self.signed:
            return tr('ВКД · отн. ед.') if self.smooth else tr('ВКД · R, 10⁻⁴⁴ esu²·см²')
        if self.kind == 'intensity':
            return tr('Раман · интенсивность, отн. ед. (532 нм, 298 К)')
        if self.kind == 'activity':
            return tr('Раман · отн. ед.') if self.smooth else tr('Раман · Å⁴/а.е.м.')
        return tr('ИК · отн. ед.') if self.smooth else tr('ИК · км/моль')

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self._lines(self.modes):
            return
        if not 52 <= event.position().x() <= self.width() - 18 or not 32 <= event.position().y() <= self.height() - 32:
            return
        try:
            peaks = self.peaks()
        except ValueError:
            return
        i, point = min(peaks, key=lambda v: abs(v[1].x() - event.position().x()))
        if self.smooth or abs(point.x() - event.position().x()) < 15:
            self.selected.emit(i)

    def export(self, path):
        if not self._lines(self.modes):
            raise ValueError(tr('Нет ИК-интенсивностей для экспорта.') if self.kind in ('ir', 'vcd')
                             else tr('Нет активностей Рамана для экспорта.'))
        self.limits()  # Validate before opening or overwriting output.
        suffix = path.suffix.lower()
        if suffix == '.csv':
            from modules.spectrum.wavefunction import field_tables

            # the style of «Таблицы CSV» (Russian Excel: «;» and the decimal comma, UTF-8 with BOM)
            unit = {'ir': 'km/mol', 'activity': 'A4/amu', 'intensity': 'relative', 'vcd': '1e-44_esu2_cm2'}[self.kind]
            name = 'intensity' if self.kind == 'ir' else 'vcd_R' if self.signed else 'raman_' + self.kind
            header = ['wavenumber_cm-1' + (f' (x{self.scale:.3f})' if self.scale != 1.0 else ''),
                      f'density_({unit})/(cm-1)' if self.smooth else f'{name}_{unit}']
            rows = ([float(a), float(b)] for a, b in zip(*self.curve())) if self.smooth else (
                [m.frequency, m.intensity] for _, m in self._lines(self.modes))
            field_tables.write_csv(path, header, list(rows))
        elif suffix == '.png':
            if not self.grab().save(str(path)):
                raise OSError(tr('Не удалось сохранить PNG.'))
        elif suffix == '.svg':
            self.grab()  # Settle pending widget layout before sizing the vector document.
            device = QSvgGenerator()
            device.setFileName(str(path))
            device.setSize(QSize(self.width(), self.height()))
            device.setViewBox(self.rect())
            device.setTitle('Azimuth · IR spectrum' if self.kind == 'ir' else 'Azimuth · VCD spectrum' if self.signed
                            else 'Azimuth · Raman spectrum')
            painter = QPainter(device)
            if not painter.isActive():
                raise OSError(tr('Не удалось создать SVG.'))
            self.render(painter, QPointF(0, 0).toPoint())
            painter.end()
        else:
            raise ValueError(tr('Поддерживаются PNG, SVG и CSV.'))

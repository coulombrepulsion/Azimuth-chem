"""Gaussian IR broadening (the lines and the broadened curve). Contract: docs/features/IR_SPECTRUM.md.

The plot itself (IRSpectrum, a Qt widget) moved to modules/spectrum/views/ir_plot.py — an analysis module
does not depend on the interface (tests/core/test_architecture_boundaries.py)."""

from math import ceil, isfinite, log, pi, sqrt
import numpy as np
from azimuth.i18n import tr


def lines(modes, signed=False):
    """(index, mode) of the modes drawn; signed — a VCD spectrum: the heights may be negative."""
    result = []
    for i, mode in enumerate(modes):
        if not isfinite(mode.frequency):
            raise ValueError(tr('Неконечная частота.'))
        if mode.intensity is not None and (not isfinite(mode.intensity) or (mode.intensity < 0 and not signed)):
            raise ValueError(tr('Некорректная ИК-интенсивность.'))
        if mode.frequency > 0 and mode.intensity is not None:
            result.append((i, mode))
    return result


def broaden(modes, width, signed=False):
    if not isfinite(width) or not 2 <= width <= 200:
        raise ValueError(tr('Ширина полосы должна быть от 2 до 200 см⁻¹.'))
    values = lines(modes, signed)
    xmax = max(4000.0, max((m.frequency + 5 * width for _, m in values), default=0.0))
    count = max(2001, ceil(xmax / width * 10) + 1)
    if count > 100001:
        raise ValueError(tr('Слишком большой диапазон частот для выбранной ширины.'))
    x = np.linspace(0, xmax, count)
    y = np.zeros_like(x)
    sigma = width / (2 * sqrt(2 * log(2)))
    for _, mode in values:
        y += mode.intensity / (sigma * sqrt(2 * pi)) * np.exp(-0.5 * ((x - mode.frequency) / sigma) ** 2)
    return x, y

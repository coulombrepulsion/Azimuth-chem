"""Rigid geometry alignment (Kabsch); contract: docs/features/GEOMETRY_COMPARISON.md."""

from dataclasses import replace
import numpy as np
from azimuth.core import Atom
from azimuth.i18n import tr


def align(reference, target):
    if not reference.atoms or tuple(a.symbol for a in reference.atoms) != tuple(a.symbol for a in target.atoms):
        raise ValueError(tr('Число и порядок элементов должны совпадать.'))
    x = np.array([a.position for a in reference.atoms], dtype=float)
    y = np.array([a.position for a in target.atoms], dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all() or max(np.abs(x).max(), np.abs(y).max()) > 1e6:
        raise ValueError(tr('Некорректные координаты для сравнения.'))
    xc = x - x.mean(axis=0)
    yc = y - y.mean(axis=0)
    u, _, vt = np.linalg.svd(xc.T @ yc)
    correction = np.eye(3)
    correction[2, 2] = 1 if np.linalg.det(u @ vt) >= 0 else -1
    fitted = xc @ (u @ correction @ vt) + y.mean(axis=0)
    rmsd = float(np.sqrt(np.mean(np.sum((fitted - y) ** 2, axis=1))))
    return replace(
        reference, atoms=tuple(Atom(a.symbol, *map(float, p)) for a, p in zip(reference.atoms, fitted))
    ), rmsd


# the comparison is shown in Compass (the starting geometry under the optimization drawer).

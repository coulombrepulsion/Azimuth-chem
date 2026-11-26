"""Computed chemical shifts against the measured ones: the errors, the linear correction, the assignment.

§1 THEORY
    The error of a computed spectrum is judged signal by signal: the mean absolute error (MAE), the root mean square
    one and the largest deviation, separately for each nucleus (¹H is good to tenths of a ppm, ¹³C to a few ppm).
    A systematic part of the error — the slope of the shieldings against the experiment is not exactly −1, the
    reference molecule has an error of its own — is removed by a straight line through the points
    σ_calc = a + b·δ_exp (least squares; b near −1, a near the shielding of the reference): the corrected shift
    is δ = (σ − a) / b and needs no reference molecule. The line is fitted to the same signals it is judged by, so the
    error after the correction is a lower bound: with few signals it flatters the method.
    Without an assignment the signals are matched by their order: the largest computed shift to the largest
    measured one. That is the assignment the calculation proposes; two computed signals closer to each other than
    the error of the method can be swapped, and such pairs are said (doubtful).
§4 SPECIFICATION
    parse(text) -> [Measured(atoms — 1-based numbers of the line or (), delta)]: a line — «77.2», «C1 77.2»,
      «H3, H4, H5: 2.15», «3 4 5 2,15» (the last number is δ; a decimal comma is read; # starts a remark).
    pairs(rows, measured) -> [Pair(atoms, sigma, calc, exp)]; rows — (atoms 0-based, element, δ | None, σ) of one
      nucleus (orca_spectra.shifts). Lines with atoms: each takes the rows its atoms are in (σ and δ averaged over
      them); lines without — by the order of σ, the counts must agree. ValueError with a message for the user.
    stats(pairs, key='calc') -> Stats(count, mae, rmse, largest, largest_at — the index of the pair); None without δ.
    linear(pairs) -> Fit(a, b, r2, shifts — the corrected δ of the pairs, stats); ValueError under three signals.
    doubtful(pairs, tolerance) -> [(i, j)] of pairs of signals whose computed shifts differ by less than tolerance
      while the measured ones differ.
§7 TESTS
    tests/spectrum/test_nmr_compare.py.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from math import sqrt

from azimuth.i18n import tr


@dataclass(frozen=True)
class Measured:
    atoms: tuple
    delta: float


@dataclass(frozen=True)
class Pair:
    atoms: tuple  # 0-based, of the computed rows
    sigma: float
    calc: float | None
    exp: float


@dataclass(frozen=True)
class Stats:
    count: int
    mae: float
    rmse: float
    largest: float
    largest_at: int


@dataclass(frozen=True)
class Fit:
    a: float
    b: float
    r2: float
    shifts: tuple
    stats: Stats


def parse(text):
    found = []
    for raw in str(text or '').splitlines():
        line = raw.split('#')[0].strip()
        if not line:
            continue
        numbers = re.findall(r'[-+]?\d+(?:[.,]\d+)?', line)
        if not numbers:
            raise ValueError(tr('Строка «{}»: не нашлось числа — сдвига в м.д.').format(raw.strip()))
        delta = float(numbers[-1].replace(',', '.'))
        head = line[:line.rfind(numbers[-1])]
        atoms = tuple(int(n) for n in re.findall(r'\d+', head))
        if any(n < 1 for n in atoms) or re.search(r'\d[.,]\d', head):
            raise ValueError(tr('Строка «{}»: перед сдвигом ждутся номера атомов (целые, с единицы).').format(raw.strip()))
        found.append(Measured(atoms, delta))
    return found


def pairs(rows, measured):
    rows, measured = list(rows), list(measured)
    if not rows:
        raise ValueError(tr('В расчёте нет экранирований этого ядра.'))
    if not measured:
        raise ValueError(tr('Введите экспериментальные сдвиги: по одному сигналу в строке.'))
    named = [bool(m.atoms) for m in measured]
    if any(named) and not all(named):
        raise ValueError(tr('Номера атомов указаны не у всех сигналов: укажите у всех или ни у одного.'))
    found = []
    if all(named):
        where = {a: k for k, row in enumerate(rows) for a in row[0]}
        taken = set()
        for m in measured:
            lacking = [n for n in m.atoms if n - 1 not in where]
            if lacking:
                raise ValueError(tr('Атома {} нет среди ядер этого элемента в расчёте.').format(lacking[0]))
            chosen = sorted({where[n - 1] for n in m.atoms})
            if taken & set(chosen):
                raise ValueError(tr('Атом {} попал в два экспериментальных сигнала.').format(m.atoms[0]))
            taken |= set(chosen)
            weights = [len(rows[k][0]) for k in chosen]
            total = sum(weights)
            sigma = sum(rows[k][3] * w for k, w in zip(chosen, weights)) / total
            deltas = [rows[k][2] for k in chosen]
            calc = None if any(d is None for d in deltas) else sum(d * w for d, w in zip(deltas, weights)) / total
            found.append(Pair(tuple(a for k in chosen for a in rows[k][0]), sigma, calc, m.delta))
        return found
    if len(measured) != len(rows):
        raise ValueError(tr('Сигналов в расчёте {}, в эксперименте {}: без номеров атомов они сопоставляются по '
                            'порядку, и число должно совпадать. Включите усреднение эквивалентных атомов или '
                            'укажите номера атомов у каждого сигнала.').format(len(rows), len(measured)))
    by_sigma = sorted(rows, key=lambda row: row[3])  # the smallest shielding — the largest shift
    by_delta = sorted(measured, key=lambda m: -m.delta)
    return [Pair(tuple(row[0]), row[3], row[2], m.delta) for row, m in zip(by_sigma, by_delta)]


def _stats(errors):
    size = [abs(e) for e in errors]
    at = max(range(len(size)), key=size.__getitem__)
    return Stats(len(size), sum(size) / len(size), sqrt(sum(e * e for e in errors) / len(size)), errors[at], at)


def stats(found):
    found = list(found)
    if not found or any(p.calc is None for p in found):
        return None
    return _stats([p.calc - p.exp for p in found])


def linear(found):
    found = list(found)
    n = len(found)
    if n < 3:
        raise ValueError(tr('Для линейной поправки нужны хотя бы три сигнала.'))
    x = [p.exp for p in found]
    y = [p.sigma for p in found]
    mx, my = sum(x) / n, sum(y) / n
    sxx = sum((v - mx) ** 2 for v in x)
    syy = sum((v - my) ** 2 for v in y)
    if sxx < 1e-12 or syy < 1e-12:
        raise ValueError(tr('Все сигналы совпадают: прямую по ним не провести.'))
    sxy = sum((u - mx) * (v - my) for u, v in zip(x, y))
    b = sxy / sxx
    a = my - b * mx
    shifts = tuple((p.sigma - a) / b for p in found)
    return Fit(a, b, sxy * sxy / (sxx * syy), shifts, _stats([d - p.exp for d, p in zip(shifts, found)]))


def doubtful(found, tolerance):
    found = list(found)
    close = []
    for i in range(len(found)):
        for j in range(i + 1, len(found)):
            if abs(found[i].sigma - found[j].sigma) < tolerance and abs(found[i].exp - found[j].exp) > 1e-9:
                close.append((i, j))
    return close

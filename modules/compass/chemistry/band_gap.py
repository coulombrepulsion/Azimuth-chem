"""The band gap of a band structure: the top of the valence band, the bottom of the conduction band, the direct and
the indirect gap.

§1 THEORY
    With N_occ occupied bands at every k-point (an insulator or a semiconductor without spin polarization:
    N_occ = N_electrons / 2), the top of the valence band is E_v = max_k ε_{N_occ}(k) and the bottom of the conduction
    band E_c = min_k ε_{N_occ+1}(k). The fundamental gap is E_g = E_c − E_v; it is direct when both are at the same k
    and indirect otherwise. The smallest direct (optical) gap is min_k [ε_{N_occ+1}(k) − ε_{N_occ}(k)] ≥ E_g. When
    E_c ≤ E_v the bands overlap: a metal or a semimetal, no gap.
§2 ALGORITHM
    occupied_bands(text of pw.x): «number of electrons = N» of the run, N even and no spin-polarized bands
    («SPIN UP») → N/2, else None. gap(energies, occupied, x, ticks): the edges over the points of the path (the first
    point of the extremum; a tie within TOLERANCE of the other edge's k is taken as direct). where(index, x, ticks): a
    point of high symmetry by its letter, else «между Γ и X, 85 %» — the share of the way from the left tick to the
    right one.
§4 SPECIFICATION
    Edge(energy eV, index, where); Gap(kind 'direct' | 'indirect' | 'metal', vbm, cbm, gap eV (0 for a metal), direct
    eV, direct_index, direct_where, occupied); gap(...) -> Gap | None (None: fewer bands than N_occ + 1, or no
    points); marks(gap, x, e0) -> the dots of the edges for qe_plots.BandsPlot; text(gap) -> the line shown under the plot (Russian, the key of tr with the numbers put in).
§6 NOTES
    Only the points of the path are looked at: an edge off the path (a general point of the zone) is missed — rare
    for the paths of the high-symmetry lines, and said in the line. A gap of a GGA functional is too small (silicon:
    0.57 eV with PBE here, 1.17 eV measured).
§7 TESTS
    tests/compass/test_band_gap.py — the real bands of silicon (pw.x 7.6, tests/data/qe/si_bands_pw76.out).
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from azimuth.i18n import tr

TOLERANCE = 1e-3  # eV: the eigenvalues are printed with four decimals


@dataclass(frozen=True)
class Edge:
    energy: float
    index: int
    where: str = ''


@dataclass(frozen=True)
class Gap:
    kind: str
    vbm: Edge
    cbm: Edge
    gap: float
    direct: float
    direct_index: int
    direct_where: str
    occupied: int


def occupied_bands(text):
    """N_occ of a run of pw.x without spin polarization, or None (§2)."""
    if re.search(r'SPIN UP', text or ''):
        return None
    found = re.findall(r'number of electrons\s*=\s*(\d+(?:\.\d+)?)', text or '')
    if not found:
        return None
    electrons = float(found[-1])
    if abs(electrons - round(electrons)) > 1e-6 or round(electrons) % 2:
        return None
    return int(round(electrons)) // 2


def where(index, x=None, ticks=None):
    """The place of the point of the path: «Γ», or «между Γ и X, 85 %» (§2); '' without the path."""
    if not x or not ticks or not 0 <= index < len(x):
        return ''
    position = x[index]
    ticks = sorted(ticks)
    for at, label in ticks:
        if abs(at - position) < 1e-6:
            return label
    left = [t for t in ticks if t[0] < position]
    right = [t for t in ticks if t[0] > position]
    if not left or not right:
        return ''
    (a, first), (b, second) = left[-1], right[0]
    share = round(100 * (position - a) / (b - a))
    return tr('между {} и {}, {} % пути').format(first.split('|')[-1], second.split('|')[0], share)


def gap(energies, occupied, x=None, ticks=None):
    """The gap of the bands [[eV] per k-point] with `occupied` filled bands (§1); None when it cannot be told."""
    if not energies or not occupied or occupied < 1 or min(len(row) for row in energies) < occupied + 1:
        return None
    valence = [sorted(row)[occupied - 1] for row in energies]
    conduction = [sorted(row)[occupied] for row in energies]
    top = max(range(len(valence)), key=lambda k: (valence[k], -k))
    bottom = min(range(len(conduction)), key=lambda k: (conduction[k], k))
    differences = [c - v for c, v in zip(conduction, valence)]
    narrow = min(range(len(differences)), key=lambda k: (differences[k], k))
    fundamental = conduction[bottom] - valence[top]
    vbm = Edge(valence[top], top, where(top, x, ticks))
    cbm = Edge(conduction[bottom], bottom, where(bottom, x, ticks))
    if fundamental <= TOLERANCE:
        return Gap('metal', vbm, cbm, 0.0, max(0.0, differences[narrow]), narrow, where(narrow, x, ticks), occupied)
    direct = differences[narrow] - fundamental <= TOLERANCE
    if direct:  # both edges at the point of the smallest direct gap
        vbm = Edge(valence[narrow], narrow, where(narrow, x, ticks))
        cbm = Edge(conduction[narrow], narrow, where(narrow, x, ticks))
    return Gap('direct' if direct else 'indirect', vbm, cbm, fundamental, differences[narrow], narrow,
               where(narrow, x, ticks), occupied)


def marks(found, x, e0):
    """The dots of the edges on a plot whose energies are E − e0: [(x, E − e0, 'v' | 'c')]; [] for a metal or no gap."""
    if found is None or found.kind == 'metal':
        return []
    return [(x[found.vbm.index], found.vbm.energy - (e0 or 0.0), 'v'),
            (x[found.cbm.index], found.cbm.energy - (e0 or 0.0), 'c')]


def _at(place):
    return (' ' + tr('в точке') + ' ' + place if ' ' not in place else ' (' + place + ')') if place else ''


def text(found):
    """The line under the plot of the bands."""
    if found is None:
        return ''
    if found.kind == 'metal':
        return tr('Валентная зона и зона проводимости перекрываются: металл или полуметалл, щели нет.')
    if found.kind == 'direct':
        line = tr('Щель прямая: {:.2f} эВ').format(found.gap) + _at(found.vbm.where) + '.'
    else:
        line = (tr('Щель непрямая: {:.2f} эВ').format(found.gap) + '; ' + tr('потолок валентной зоны') + _at(found.vbm.where)
                + ', ' + tr('дно зоны проводимости') + _at(found.cbm.where) + '. '
                + tr('Наименьшая прямая щель {:.2f} эВ').format(found.direct) + _at(found.direct_where) + '.')
    return line + ' ' + tr('Щель найдена по точкам пути; без гибридного функционала расчёт обычно занижает её.')

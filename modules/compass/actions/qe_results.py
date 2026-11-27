"""The results of a crystal calculation in QePanel: the bands, the densities of states, the phonons, QTAIM and the
charges of a CP2K run (their table windows), the summary, the optimized cell and its steps. Methods of QePanel (self
is the panel), kept here to make qe_window.py shorter.

Split off modules/compass/actions/qe_window.py (0.222.29).
"""

from datetime import datetime
from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QVBoxLayout
from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.actions.qe_common import RY_EV, phonon_lines


def reference(self, r):
    """E0 of the plots: the highest occupied level (an insulator) or the Fermi level (a metal), eV."""
    return r.highest if r.highest is not None else r.fermi


def band_data(self):
    """(Bands, path dict, E0) of the finished job of the bands, or None."""
    import json

    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / 'path.json').is_file() or self.result is None:
        return None
    found = qe.bands((self.folder / 'pw.out').read_text(encoding='utf-8', errors='replace'))
    path = json.loads((self.folder / 'path.json').read_text(encoding='utf-8'))
    if not found.energies or len(found.energies) != len(path['x']):
        return None
    return found, path, self.reference(self.result)


def dos_data(self):
    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / 'azimuth.dos').is_file() or self.result is None:
        return None
    found = qe.read_dos((self.folder / 'azimuth.dos').read_text(encoding='utf-8', errors='replace'))
    e0 = self.reference(self.result)
    if e0 is None:
        e0 = found.fermi
    return (found, e0) if found.energies else None


def magnetic_lines(r):
    """The magnetization of a spin-polarized run for the summary: per cell and the moments of the atoms that have one."""
    if r.magnetization is None and not r.moments:
        return []
    lines = []
    if r.magnetization is not None:
        lines.append(tr('Намагниченность ячейки: полная {} μB, абсолютная {} μB').format(
            f'{r.magnetization:.2f}', '—' if r.absolute_magnetization is None else f'{r.absolute_magnetization:.2f}'))
    shown = [(n, m) for n, m in r.moments if abs(m) >= 0.05]
    if shown:
        symbols = [a[0] for a in r.atoms] if r.atoms else []
        names = [f'{symbols[n - 1] if n - 1 < len(symbols) else "№ "}{n} {m:+.2f}' for n, m in shown[:12]]
        lines.append(tr('Магнитные моменты атомов, μB: {}').format(', '.join(names)) + (' …' if len(shown) > 12 else ''))
    return lines


def states_data(self):
    """(kind 'hub' | 'mag', rows) of a finished series of U or of magnetic orders: a row — (label, E eV per cell, gap eV
    | None — a metal, the largest |moment| μB | None, the absolute magnetization | None); None when the job is not
    such a series."""
    import re

    from modules.sextant import qe_inputs
    from modules.spectrum.readers import qe

    kind = next((k for k in ('hub', 'mag') if self.folder is not None and (self.folder / f'{k}1.in').is_file()), None)
    if kind is None or not (self.folder / 'pw.out').is_file():
        return None
    rows = []
    for n, run in enumerate(qe.runs((self.folder / 'pw.out').read_text(encoding='utf-8', errors='replace')), 1):
        source = self.folder / f'{kind}{n}.in'
        if not source.is_file():
            break
        r = qe.read(run)
        if r.energy is None:
            continue
        if kind == 'hub':
            found = re.search(r'^\s*U\s+\S+\s+([\d.]+)', source.read_text(encoding='utf-8', errors='replace'), re.M)
            label = f'U = {float(found.group(1)) if found else 0.0:g} ' + tr('эВ')
        else:
            label = tr(qe_inputs.MAGNETIC_STATES[n - 1]) if n <= len(qe_inputs.MAGNETIC_STATES) else str(n)
        gap = r.lowest - r.highest if r.highest is not None and r.lowest is not None else None
        moment = max((abs(m) for _, m in r.moments), default=None)
        rows.append((label, r.energy * 13.605693122994, gap, moment, r.absolute_magnetization))
    return kind, rows


def states_table(self, found):
    """The table of the series as HTML for the summary."""
    kind, rows = found
    if not rows:
        return ''
    low = min(row[1] for row in rows)
    heads = [tr('Состояние') if kind == 'mag' else 'U', tr('Щель, эВ'), tr('Наибольший момент, μB'),
             tr('Абсолютная намагниченность, μB')]
    if kind == 'mag':  # one cell and one U: the energies compare
        heads.insert(1, tr('ΔE, мэВ на ячейку'))
    html = '<table><tr>' + ''.join(f'<th align="right">&nbsp;{h}&nbsp;</th>' for h in heads) + '</tr>'
    for label, energy, gap, moment, absolute in rows:
        cells = [label, '—' if gap is None else tr('металл') if gap <= 0 else f'{gap:.2f}', '—' if moment is None else f'{moment:.2f}',
                 '—' if absolute is None else f'{absolute:.2f}']
        if kind == 'mag':
            cells.insert(1, f'{1000 * (energy - low):.1f}')
        html += '<tr>' + ''.join(f'<td align="right">&nbsp;{c}&nbsp;</td>' for c in cells) + '</tr>'
    note = tr('Энергии с разным U между собой не сравнивают: смотрите на щель и момент.') if kind == 'hub' else tr(
        'Основное состояние — с наименьшей энергией.')
    note += ' ' + tr('Щель — по уровням расчёта scf на его k-сетке; прочерк — расчёт с размытием (металл или состояние, '
                     'заселённости которого программа подбирала сама): уровни краёв щели в нём не печатаются.')
    return html + '</table>' + note


def series_data(self):
    """(kind 'cut' | 'kpt', [convergence.Row]) of a finished convergence series — the runs of pw.out with the values
    of their input files —, (kind, None) when the series gave too few points (the reason in self.series_error), or
    None when the job is not such a series."""
    import re

    from modules.compass.chemistry import convergence
    from modules.spectrum.readers import qe

    kind = next((k for k in ('cut', 'kpt', 'vac') if self.folder is not None and (self.folder / f'{k}1.in').is_file()),
                None)
    if kind is None or not (self.folder / 'pw.out').is_file():
        return None
    runs = qe.runs((self.folder / 'pw.out').read_text(encoding='utf-8', errors='replace'))
    points = []
    for n, run in enumerate(runs, 1):
        source = self.folder / f'{kind}{n}.in'
        if not source.is_file():
            break
        text = source.read_text(encoding='utf-8', errors='replace')
        r = qe.read(run)
        if r.energy is None or not r.done:
            continue
        if kind == 'cut':
            label = re.search(r'ecutwfc\s*=\s*([\d.]+)', text).group(1) + ' Ry'
        elif kind == 'vac':
            from modules.compass.chemistry import layer

            size = layer.vacuum_of_input(text)
            label = '?' if size is None else f'{size:g} Å'
        else:
            label = ' × '.join(text.split('K_POINTS automatic')[1].split()[:3])
        gap = r.lowest - r.highest if r.highest is not None and r.lowest is not None else None
        # the pressure of a cell with vacuum says nothing of the layer: left out of the series of vacuum
        points.append(convergence.Point(label, r.energy * 13.605693122994, r.nat or 1,
                                        r.pressures[-1] if r.pressures and kind != 'vac' else None, gap,
                                        r.fermi if r.fermi is not None else r.highest))
    self.series_error = ''
    try:
        return kind, convergence.rows(points)
    except ValueError as exc:
        self.series_error = str(exc)
        return kind, None


def series_lines(self, found):
    from modules.compass.chemistry import convergence

    kind, table = found
    if table is None:
        return [self.series_error]
    return convergence.summary(table) + family_lines(kind, table)


SERIES_TITLES = {'cut': ('Сходимость по энергии обрезания · ', 'ecutwfc, Ry', 'ecutwfc'),
                 'kpt': ('Сходимость по k-сетке · ', 'k-сетка', 'k grid'),
                 'vac': ('Сходимость по вакууму · ', 'Вакуум, Å', 'vacuum')}  # the units of the axes (0.248.15)


def with_corner(label):
    """Does a grid «N × N × 1» of a layer contain the corner K of a hexagonal zone (N a multiple of 3)?"""
    parts = label.split(' × ')
    return len(parts) == 3 and parts[2] == '1' and parts[0] == parts[1] and int(parts[0]) % 3 == 0


def family_lines(kind, table):
    """The two families of grids of a layer: those with N a multiple of 3 hold the point K of a hexagonal zone."""
    if kind != 'kpt' or not all(r.label.endswith('× 1') for r in table) or not any(with_corner(r.label) for r in table):
        return []
    return [tr('Сетки N × N × 1 с N, кратным 3, содержат угол K шестиугольной зоны (на графике — зелёные точки). У графена '
               'в K касаются зоны, поэтому энергия и уровень Ферми для двух семейств сеток сходятся по разным кривым.')]


def show_series(self, found):
    """ΔE of the series with the band of the tolerance; the table under the plot."""
    from modules.compass.actions import qe_plots
    from modules.compass.chemistry import convergence

    kind, table = found
    if table is None:
        return None
    title, axis, column = SERIES_TITLES[kind]
    plot = qe_plots.SeriesPlot()
    plot.labels = [r.label for r in table]
    plot.values = [r.delta for r in table]
    plot.tolerance = convergence.TOLERANCE_MEV
    plot.axis = axis
    plot.marked = [kind == 'kpt' and with_corner(r.label) for r in table]
    rows = [(r.label, r.energy_per_atom, r.delta, '' if r.pressure is None else r.pressure, '' if r.gap is None else r.gap,
             '' if r.fermi is None else r.fermi) for r in table]
    window = qe_plots.QePlotWindow(self, tr(title) + self.name, plot, rows,
                                   [column, 'E per atom, eV', 'dE, meV per atom', 'P, kbar', 'gap, eV',
                                    'E_F or highest occupied level, eV'], 'convergence.csv')
    head = '<tr>' + ''.join(f'<th align="right">&nbsp;{tr(h)}&nbsp;</th>' for h in (
        axis, 'ΔE, мэВ на атом', 'Давление, кбар', 'Щель, эВ', 'Уровень Ферми, эВ')) + '</tr>'
    body = ''.join('<tr>' + ''.join(f'<td align="right">&nbsp;{c}&nbsp;</td>' for c in (
        r.label, f'{r.delta:+.2f}', '' if r.pressure is None else f'{r.pressure:.2f}', '' if r.gap is None else f'{r.gap:.3f}',
        '' if r.fermi is None else f'{r.fermi:.4f}')) + '</tr>' for r in table)
    window.note.setText('<table>' + head + body + '</table>' + ' '.join(convergence.summary(table) + family_lines(kind, table))
                        + ' ' + tr('Уровень Ферми — из расчёта с размытием; без размытия в этом столбце верхний занятый '
                                   'уровень.'))
    self.plot_window = window
    window.show()
    return window


def cone_data(self, found, path, text):
    """The Dirac cone of the bands of a hexagonal layer (layer.Cone) with the bands of the tight-binding model along
    the path, or None: (cone, [(E−, E+)] | None)."""
    from modules.compass.chemistry import band_gap, layer

    if self.crystal is None or 'K' not in [t[1] for t in path['ticks']]:
        return None
    ticks = [tuple(t) for t in path['ticks']]
    cone = layer.cone(found.energies, band_gap.occupied_bands(text), path['x'], ticks, self.crystal.cell.a)
    if cone is None:
        return None
    model = None
    try:
        from modules.sextant import qe_paths

        crystal, basis = self.computed()
        fractions = qe_paths.path(self.crystal, basis).fractions
        if len(fractions) == len(path['x']):
            model = layer.tight_binding(fractions, cone.hopping, cone.energy, layer.neighbour_cells(crystal))
    except (ValueError, AttributeError):
        model = None
    return cone, model


def show_cone(self, found, path, e0, cone, model):
    """The neighbourhood of K: the bands, the cone of the slopes found and the tight-binding model (dashed)."""
    from modules.compass.actions import qe_plots
    from modules.compass.chemistry import layer

    centre = path['x'][cone.index]
    plot = qe_plots.BandsPlot()
    plot.x = path['x']
    plot.energies = [[e - cone.energy for e in row] for row in found.energies]
    plot.ticks, plot.breaks = [tuple(t) for t in path['ticks']], path['breaks']
    plot.xrange = (max(0.0, centre - 0.35), min(path['x'][-1], centre + 0.35))
    plot.span = (-2.5, 2.5)
    plot.axis = 'E − E(K), эВ'
    if model is not None:
        plot.model = [[low - cone.energy, high - cone.energy] for low, high in model]
    rows = [(x, *row) for x, row in zip(plot.x, plot.energies) if plot.xrange[0] <= x <= plot.xrange[1]]
    header = ['k, 1/A'] + [f'E{n + 1} - E(K), eV' for n in range(len(found.energies[0]))]
    window = qe_plots.QePlotWindow(self, tr('Конус Дирака · ') + self.name, plot, rows, header, 'dirac_cone.csv')
    slopes = ', '.join(f'{name}, K→{cone.left if side == "left" else cone.right}: {value:.2f}'
                       for (name, side), value in cone.slopes.items())
    window.note.setText(layer.text(cone) + ' ' + tr('Наклоны зон, эВ·Å: {}.').format(slopes) + (
        ' ' + tr('Штриховые линии — модель сильной связи с этим t.') if model is not None else ''))
    self.cone_window = window
    window.show()
    return window


def eos_data(self):
    """(Fit, [(V Å³, E eV)]) of a finished series of volumes («Уравнение состояния»), (None, points) when the points
    do not give a fit (with the reason in self.eos_error), or None when the job is not such a series."""
    from modules.compass.chemistry import equation_of_state
    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / 'eos1.in').is_file() or not (self.folder / 'pw.out').is_file():
        return None
    text = (self.folder / 'pw.out').read_text(encoding='utf-8', errors='replace')
    points = equation_of_state.points_of_runs([qe.read(run) for run in qe.runs(text)])
    self.eos_error = ''
    try:
        return equation_of_state.fit([v for v, _ in points], [e for _, e in points]), points
    except ValueError as exc:
        self.eos_error = str(exc)
        return None, points


def eos_lines(self, found):
    """The lines of the summary: V₀, the lattice parameters at V₀, B₀ and B₀′."""
    fit, points = found
    if fit is None:
        return [tr('Уравнение состояния не подогнано: {}').format(self.eos_error)]
    lines = [tr('Уравнение состояния Бирча — Мурнагана по {} объёмам: V₀ = {} Å³ на ячейку расчёта, B₀ = {} ГПа, B₀′ = {}')
             .format(len(points), f'{fit.v0:.3f}', f'{fit.b0:.1f}', f'{fit.b0_prime:.2f}')]
    cell = getattr(self.crystal, 'cell', None)
    try:
        computed, _ = self.computed()
        scale = (fit.v0 / computed.cell.volume()) ** (1.0 / 3.0)
        lines.append(tr('Равновесная ячейка файла: a = {}, b = {}, c = {} Å (среднеквадратичное отклонение подгонки {} мэВ)')
                     .format(f'{cell.a * scale:.4f}', f'{cell.b * scale:.4f}', f'{cell.c * scale:.4f}', f'{1000 * fit.rms:.2f}'))
    except (AttributeError, ValueError, ZeroDivisionError):
        pass
    return lines


def show_eos(self, found):
    """E(V) of the series with the curve of the fit."""
    from modules.compass.actions import qe_plots
    from modules.compass.chemistry import equation_of_state

    fit, points = found
    plot = qe_plots.EosPlot()
    zero = fit.e0 if fit is not None else min(e for _, e in points)
    plot.volumes = [v for v, _ in points]
    plot.energies = [1000 * (e - zero) for _, e in points]
    if fit is not None:
        lo, hi = min(plot.volumes), max(plot.volumes)
        plot.curve = [(v, 1000 * (equation_of_state.energy(fit, v) - zero))
                      for v in (lo + (hi - lo) * k / 100 for k in range(101))]
        plot.minimum = fit.v0
    rows = [(v, e, (equation_of_state.pressure(fit, v) if fit is not None else '')) for v, e in points]
    window = qe_plots.QePlotWindow(self, tr('Уравнение состояния · ') + self.name, plot, rows,
                                   ['V, A^3', 'E, eV', 'P(fit), GPa'], 'equation_of_state.csv')
    window.note.setText(' '.join(self.eos_lines(found)))
    self.plot_window = window
    window.show()
    return window


def elastic_data(self):
    """(elastic.Elastic | None, {kind: [(e, E eV)]}) of a finished series of strains («Упругие постоянные»): the runs
    of pw.out by the plan of elastic.json; None when the job is not such a series. The reason of a failed fit — in
    self.elastic_error."""
    import json

    from modules.compass.chemistry import elastic
    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / 'elastic.json').is_file() or not (self.folder / 'pw.out').is_file():
        return None
    try:
        note = json.loads((self.folder / 'elastic.json').read_text(encoding='utf-8'))
        plan, volume = [(name, float(e)) for name, e in note['plan']], float(note['volume'])
    except (ValueError, KeyError, TypeError):
        return None
    runs = qe.runs((self.folder / 'pw.out').read_text(encoding='utf-8', errors='replace'))
    points = {kind: [] for kind in elastic.KINDS}
    for (name, e), run in zip(plan, runs):
        r = qe.read(run)
        if r.energy is None or not r.done:
            continue
        energy = r.energy * 13.605693122994
        for kind in (elastic.KINDS if name is None else (name,)):  # the unstrained cell is a point of each curve
            points[kind].append((e, energy))
    self.elastic_error = ''
    try:
        return elastic.fit(points, volume), points
    except ValueError as exc:
        self.elastic_error = str(exc)
        return None, points


def elastic_lines(self, found):
    from modules.compass.chemistry import elastic

    if found[0] is None:
        return [self.elastic_error]
    return elastic.lines(found[0])


ELASTIC_NAMES = {'c11': 'растяжение вдоль x: C₁₁', 'cp': 'растяжение x, сжатие y: C₁₁ − C₁₂', 'c44': 'сдвиг xy: C₄₄'}


def show_elastic(self, found):
    """ΔE/V₀ of the three strains with the curves of the fit."""
    from modules.compass.actions import qe_plots
    from modules.compass.chemistry import elastic

    fit, points = found
    if fit is None:
        return None
    plot = qe_plots.CurvesPlot()
    plot.x_axis, plot.y_axis = 'Деформация e', 'ΔE/V₀, мэВ/Å³'
    rows = []
    for kind, colour in zip(elastic.KINDS, ('#2a62b8', '#c0504d', '#2e8b57')):
        zero = next(energy for e, energy in points[kind] if abs(e) < 1e-9)
        dots = sorted((e, 1000 * (energy - zero) / fit.volume) for e, energy in points[kind])
        lo, hi = dots[0][0], dots[-1][0]
        line = [(e, 1000 * elastic.curve(fit, kind, e)) for e in (lo + (hi - lo) * k / 80 for k in range(81))]
        plot.series.append((tr(ELASTIC_NAMES[kind]), colour, dots, line))
        rows += [(kind, e, energy, 1000 * (energy - zero) / fit.volume) for e, energy in sorted(points[kind])]
    window = qe_plots.QePlotWindow(self, tr('Упругие постоянные · ') + self.name, plot, rows,
                                   ['strain', 'e', 'E, eV', 'dE/V0, meV/A^3'], 'elastic.csv')
    window.note.setText(' '.join(self.elastic_lines(found)))
    self.plot_window = window
    window.show()
    return window


def phonon_data(self):
    """(branches [[ν cm⁻¹] per q], path dict, (ν, g) of the phonon DOS or None) of a finished job of the phonon
    branches (the files of matdyn.x), or None."""
    import json

    from modules.sextant import qe_inputs
    from modules.spectrum.readers import qe

    if self.folder is None or not (self.folder / qe_inputs.FREQ_FILE).is_file() or not (
            self.folder / 'path.json').is_file():
        return None
    branches = qe.read_branches((self.folder / qe_inputs.FREQ_FILE).read_text(encoding='utf-8', errors='replace'))
    path = json.loads((self.folder / 'path.json').read_text(encoding='utf-8'))
    if not branches or len(branches) != len(path['x']):
        return None
    dos = None
    if (self.folder / qe_inputs.PHDOS_FILE).is_file():
        dos = qe.read_phdos((self.folder / qe_inputs.PHDOS_FILE).read_text(encoding='utf-8', errors='replace'))
    return branches, path, dos


def show_phonons(self, found):
    """The phonon branches along the path and, beside, the phonon density of states."""
    from modules.compass.actions import qe_plots

    branches, path, dos = found
    values = [v for row in branches for v in row]
    top = max(values) if values else 1.0
    plot = qe_plots.BandsPlot()
    plot.axis, plot.zero_line, plot.x_axis = 'ν, см⁻¹', False, 'Волновой вектор q'
    plot.span = (min(0.0, min(values, default=0.0)) - 0.03 * top, 1.08 * top)
    plot.x, plot.energies = path['x'], branches
    plot.ticks, plot.breaks = [tuple(t) for t in path['ticks']], path['breaks']
    rows = [(x, *row) for x, row in zip(plot.x, branches)]
    header = ['q, 1/A'] + [f'nu{n + 1}, cm-1' for n in range(len(branches[0]))]
    window = qe_plots.QePlotWindow(self, tr('Фононные ветви · ') + self.name, plot, rows, header, 'phonons.csv')
    window.note.setText(tr('Отрицательные частоты — мнимые: структура не в минимуме (или мала сетка q). У ионного '
                           'кристалла у Γ видно расщепление LO–TO.'))
    self.plot_window = window
    window.show()
    if dos is not None and dos[0]:
        density = qe_plots.DosPlot()
        density.axis, density.label = 'ν, см⁻¹', 'g(ν), состояний/см⁻¹'
        density.energies, density.dos = dos
        density.span = plot.span
        second = qe_plots.QePlotWindow(self, tr('Фононная плотность состояний · ') + self.name, density,
                                       list(zip(*dos)), ['nu, cm-1', 'g(nu)'], 'phonon_dos.csv')
        self.phdos_window = second
        second.show()
        show_thermo(self, dos)  # by the function: an owner that is not the panel has no such method
    return window


def thermo_data(self, dos):
    """(rows, summary, atoms in the cell computed, formula units in it) of the harmonic thermodynamics of the phonon
    density of states (phonon_thermo), or None with the reason in self.thermo_error."""
    from collections import Counter
    from functools import reduce
    from math import gcd

    from modules.compass.chemistry import crystal as cr, phonon_thermo

    self.thermo_error = ''
    try:
        counts = Counter(a[0] for a in cr.unit_cell(self.computed()[0]) if a[0] != 'X')
        atoms = sum(counts.values())
        units = reduce(gcd, counts.values())
        rows = phonon_thermo.table(dos[0], dos[1], atoms, units)
        return rows, phonon_thermo.summary(dos[0], dos[1], atoms, units, rows), atoms, units
    except (ValueError, AttributeError, TypeError) as exc:
        self.thermo_error = str(exc)
        return None


def show_thermo(self, dos):
    """C_V(T) of the phonon density of states with the Debye curve fitted to it; the table of C_V, S, U, F and Θ(T)."""
    from modules.compass.actions import qe_plots
    from modules.compass.chemistry import phonon_thermo

    found = thermo_data(self, dos)
    if found is None:
        return None
    rows, summary, atoms, units = found
    joule = phonon_thermo.EV * phonon_thermo.NA / units
    plot = qe_plots.CurvesPlot()
    plot.x_axis, plot.y_axis = 'T, K', 'C_V, Дж/(моль·К)'
    points = [(r.temperature, r.heat) for r in rows]
    span = [rows[0].temperature + (rows[-1].temperature - rows[0].temperature) * k / 120 for k in range(121)]
    plot.series.append((tr('по фононному спектру'), '#2a62b8', points, points))
    plot.series.append((tr('модель Дебая, Θ = {} K').format(f'{summary.theta_fit:.0f}'), '#c0504d', [],
                        [(t, phonon_thermo.debye_heat(t, summary.theta_fit, atoms) * joule) for t in span]))
    plot.series.append((tr('предел Дюлонга — Пти'), '#888888', [], [(span[0], summary.limit), (span[-1], summary.limit)]))
    table = [(r.temperature, r.heat, r.entropy, r.energy, r.free, '' if r.theta is None else r.theta) for r in rows]
    window = qe_plots.QePlotWindow(self, tr('Теплоёмкость · ') + self.name, plot, table,
                                   ['T K', 'C_V J/(mol K)', 'S J/(mol K)', 'U - E0 kJ/mol', 'F - E0 kJ/mol', 'Theta_D(T) K'],
                                   'phonon_thermodynamics.csv')
    room = min(rows, key=lambda r: abs(r.temperature - 298.15))
    window.note.setText(' '.join(phonon_thermo.lines(summary, room)))
    self.thermo_window = window
    window.show()
    return window


def show_plot(self):
    """The bands or the density of states of the finished job (qe_plots.QePlotWindow)."""
    from modules.compass.actions import qe_plots

    phonons = self.phonon_data()
    if phonons is not None:
        return self.show_phonons(phonons)
    strained = self.elastic_data()
    if strained is not None:
        return self.show_elastic(strained)
    series = self.eos_data()
    if series is not None:
        return self.show_eos(series)
    convergence = self.series_data()
    if convergence is not None:
        return self.show_series(convergence)
    bands = self.band_data()
    if bands is not None:
        found, path, e0 = bands
        plot = qe_plots.BandsPlot()
        plot.x = path['x']
        plot.energies = [[e - (e0 or 0.0) for e in row] for row in found.energies]
        plot.ticks, plot.breaks = [tuple(t) for t in path['ticks']], path['breaks']
        rows = [(x, *row) for x, row in zip(plot.x, plot.energies)]
        header = ['k, 1/A'] + [f'E{n + 1} - E0, eV' for n in range(len(found.energies[0]))]
        window = qe_plots.QePlotWindow(self, tr('Зонная структура · ') + self.name, plot, rows, header, 'bands.csv')
        from modules.compass.chemistry import band_gap

        text = (self.folder / 'pw.out').read_text(encoding='utf-8', errors='replace')
        self.gap = band_gap.gap(found.energies, band_gap.occupied_bands(text), plot.x, plot.ticks)
        plot.marks = band_gap.marks(self.gap, plot.x, e0)
        window.note.setText(band_gap.text(self.gap))
        cone = self.cone_data(found, path, text)
        if cone is not None:  # graphene: the cone at K in a window of its own, the model on both plots
            from modules.compass.chemistry import layer

            if cone[1] is not None:
                plot.model = [[low - (e0 or 0.0), high - (e0 or 0.0)] for low, high in cone[1]]
            window.note.setText(window.note.text() + ' ' + layer.text(cone[0]))
            self.show_cone(found, path, e0, *cone)
        if path.get('general'):
            window.note.setText((window.note.text() + ' ').lstrip() + tr(
                'Для этой решётки путь общий: Γ–X, Γ–Y, Γ–Z вдоль осей обратной ячейки файла.'))
    else:
        dos = self.dos_data()
        if dos is None:
            return None
        found, e0 = dos
        plot = qe_plots.DosPlot()
        plot.energies = [e - (e0 or 0.0) for e in found.energies]
        plot.dos = found.dos
        rows = list(zip(plot.energies, found.dos, found.integrated))
        window = qe_plots.QePlotWindow(self, tr('Плотность состояний · ') + self.name, plot, rows,
                                       ['E - E0, eV', 'DOS, 1/eV', 'integrated'], 'dos.csv')
    window.note.setText((window.note.text() + ' ' if window.note.text() else '') +
                        tr('E₀ — верх валентной зоны (у металла — уровень Ферми) по расчёту scf.'))
    self.plot_window = window
    window.show()
    return window


def multiwfn_line(self):
    """The wave function of the end of a CP2K run made ready for Multiwfn (cp2k.for_multiwfn) — a line of
    the summary: the file, or why there is none."""
    from modules.spectrum.readers import cp2k

    try:
        path, why = cp2k.for_multiwfn(self.folder)
    except (OSError, ValueError) as exc:
        path, why = None, str(exc)
    self.multiwfn_file = path
    self.aim_button.setVisible(path is not None)
    self.charges_button.setVisible(path is not None)
    if path is not None:
        return '<br>' + tr('Волновая функция для Multiwfn: {}').format(path.name)
    return '<br>' + tr('Волновая функция для Multiwfn не подготовлена: {}').format(why) if why else ''


def multiwfn_found(self):
    """Multiwfn of the settings of the program (as for a molecule), or found where it is usually installed."""
    from modules.compass.actions import crystal_analysis

    return crystal_analysis.multiwfn_program(self.owner)


def show_aim(self):
    """the bonds by QTAIM of the CP2K run (crystal_analysis.compute_aim) — a table in its own window, aim-bonds.csv
    in the folder of the run. None when nothing was done."""
    from modules.compass.actions import crystal_analysis
    from modules.compass.chemistry.crystal_results import Run

    if getattr(self, 'multiwfn_file', None) is None or self.folder is None:
        return None
    try:
        rows, meta = crystal_analysis.compute_aim(self, Run(self.folder, 'cp2k'), self.multiwfn_found(),
                                                  self.processes.value(), self.multiwfn_file)
    except InterruptedError:
        return None
    except (OSError, ValueError) as exc:
        self.status.setText(str(exc))
        return None
    self.aim_window = crystal_analysis.aim_window(self, self.name, rows, meta)
    self.aim_window.show()
    return self.aim_window


def show_charges(self):
    """The charges of Hirshfeld and CM5 of the atoms (crystal_analysis.compute_charges) — per element in
    a window, per atom in charges.csv. None when nothing was done."""
    from modules.compass.actions import crystal_analysis
    from modules.compass.chemistry.crystal_results import Run

    if getattr(self, 'multiwfn_file', None) is None or self.folder is None:
        return None
    try:
        symbols, charges, version = crystal_analysis.compute_charges(
            self, Run(self.folder, 'cp2k'), self.multiwfn_found(), self.processes.value(), self.multiwfn_file)
    except InterruptedError:
        return None
    except (OSError, ValueError) as exc:
        self.status.setText(str(exc))
        return None
    self.charges_window = crystal_analysis.charges_window(self, self.name, symbols, charges, version)
    self.charges_window.show()
    return self.charges_window


def _record(self, r):
    """A run in the folder of a crystal project is written into the project (crystal_projects.runs)."""
    from azimuth import crystal_projects

    manifest = self.folder.parent.parent / 'project.qcc' if self.folder is not None else None
    if manifest is None or self.folder.parent.name != 'calculations' or not crystal_projects.is_crystal(manifest):
        return False
    try:
        crystal_projects.record_run(manifest, {
            'folder': f'calculations/{self.folder.name}', 'task': self.task.currentData(),
            'time': datetime.now().isoformat(timespec='seconds'), 'energy_ry': r.energy,
            'energy_eh': getattr(r, 'energy_hartree', None),
            'place': self.where.currentData(), 'program': self.program}, getattr(self, 'crystal_ident', None))
    except (OSError, ValueError) as exc:  # a project open for writing elsewhere: the run stays in its folder
        self.status.setText(self.status.text() + ' · ' + str(exc))
        return False
    return True


def summary_text(self, r):
    n = r.nat or 1
    lines = [tr('Полная энергия ячейки: {} Ry = {} Eh = {} эВ ({} эВ на атом)').format(
        f'{r.energy:.6f}', f'{r.energy_hartree:.6f}', f'{r.energy * RY_EV:.4f}', f'{r.energy * RY_EV / n:.4f}')]
    if r.pressures:
        lines.append(tr('Давление: {} кбар').format(f'{r.pressures[-1]:.2f}'))
    if r.highest is not None and r.lowest is not None:
        lines.append(tr('Щель (по сетке k): {} эВ').format(f'{r.lowest - r.highest:.3f}'))
    elif r.fermi is not None:
        lines.append(tr('Уровень Ферми: {} эВ').format(f'{r.fermi:.4f}'))
    if r.steps:
        lines.append(tr('Шагов оптимизации: {}{}').format(r.steps, '' if r.converged else tr(' (не сошлась)')))
    if r.cell is not None and r.atoms:
        import numpy as np

        lengths = [float(np.linalg.norm(v)) for v in r.cell]
        lines.append(tr('Оптимизированная ячейка: a = {}, b = {}, c = {} Å').format(*(f'{x:.4f}' for x in lengths)))
        file_cell = self.file_cell_of(r.cell)
        if file_cell is not None:  # the primitive cell (Si: 3.87 Å) differs from the CIF cell (5.47 Å)
            lines.append(tr('В ячейке файла (как в CIF): a = {}, b = {}, c = {} Å').format(
                *(f'{x:.4f}' for x in file_cell)))
    if self.program != 'cp2k':
        lines += magnetic_lines(r)
    if self.program != 'cp2k' and getattr(self, 'folder', None) is not None:
        from modules.spectrum.readers import qe

        found = qe.phonons(self.folder)
        if found is not None:
            lines += phonon_lines(found)
    return '<br>'.join(lines)


def file_cell_of(self, cell):
    """The edges a, b, c (Å) of the cell of the file that the optimized cell computed (primitive and/or a
    supercell, computed()) stands for — the rows of the file cell are B⁻¹ · R; None when the cell of the file was
    computed itself."""
    import numpy as np

    try:
        _crystal, basis = self.computed()
    except (ValueError, AttributeError, TypeError):
        return None
    if basis is None:
        return None
    try:
        rows = np.linalg.inv(np.array(basis, dtype=float)) @ np.array(cell, dtype=float)
    except (np.linalg.LinAlgError, ValueError):
        return None
    return [float(np.linalg.norm(v)) for v in rows]


def open_relaxed(self):
    """The steps of the optimization in the tab
    of this crystal in «Компас · Кристалл» (as the steps of a molecule: the last one shown, the start as a ghost,
    RMSD and the change of the cell) — no CIF of its own, no new project; «Взять эту геометрию» there gives the cell
    of the file in its group when the optimization kept it (crystal_steps.back_to_the_file). Without steps (an
    output of one geometry) the end itself is taken so."""
    from modules.compass.chemistry import crystal_steps

    steps = self.optimization_steps()
    if not steps and self.result is not None and self.result.cell is not None and self.result.atoms:
        steps = crystal_steps.make_steps([(self.result.energy_hartree, self.result.cell, self.result.atoms)],
                                         self.crystal.title or self.name, *self.computed_as())
    if not steps or not hasattr(self.owner, 'trajectory_tool'):
        return False
    program = 'CP2K' if self.program == 'cp2k' else 'Quantum ESPRESSO'
    if getattr(self.owner, 'compass_mode', 'crystal') != 'crystal' and hasattr(self.owner, 'crystal_tool'):
        self.owner.crystal_tool.set_compass_mode('crystal')
    self.owner.trajectory_tool.load_crystal_steps(steps, tr('оптимизация {} · {}').format(program, self.name),
                                                  self.folder)
    return True


def computed_as(self):
    """(the crystal of the file, the supercell computed, whether the primitive cell was) — for crystal_steps."""
    primitive = self.primitive.isChecked() and self.primitive_crystal is not self.crystal
    return self.crystal, tuple(b.value() for b in self.supercell), primitive


def optimization_steps(self):
    """The steps of the optimization just done (crystal_steps.CrystalStep, the start first), when the
    output or its files cannot be read."""
    from modules.compass.chemistry import crystal_steps
    from modules.spectrum.readers import cp2k, qe

    if self.job is None and self.folder is not None:  # a run of the project shown again — its supercell
        try:                                           # read back from its first step (crystal_steps.run_steps)
            return crystal_steps.run_steps(self.folder, self.program, self.crystal, self.crystal.title or self.name)
        except (OSError, ValueError, IndexError):
            return ()
    try:
        if self.program == 'cp2k':
            raw = cp2k.steps(self.folder) if self.folder is not None else []
        else:
            text = self.job.text() if self.job is not None else ''
            raw = qe.steps((qe.runs(text) or [text])[0])
        return crystal_steps.make_steps(raw, self.crystal.title or self.name, *self.computed_as())
    except (OSError, ValueError, IndexError):
        return ()


class TableWindow(QDialog):
    """A table of a result of Multiwfn for a crystal and what its columns mean (the bonds by AIM, the
    charges)."""

    def __init__(self, parent, title, heads, rows, lines):
        from PySide6.QtWidgets import QHeaderView, QTableWidget, QTableWidgetItem

        super().__init__(parent)
        self.setWindowTitle(title)
        layout = QVBoxLayout(self)
        self.table = QTableWidget(len(rows), len(heads))
        self.table.setHorizontalHeaderLabels(heads)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(value))
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        layout.addWidget(self.table, 1)
        self.note = QLabel('<br>'.join(lines))
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(900, 420)


class AimWindow(TableWindow):
    """The kinds of bonds of a crystal by QTAIM (crystal_aim)."""

    def __init__(self, parent, name, rows, census, atoms, version=None):
        from modules.spectrum.wavefunction import crystal_aim

        heads = [tr('Связь'), tr('Длина, Å'), tr('Связей у атома'), 'ρ, a.u.', '∇²ρ, a.u.', 'H, a.u.', '|V|/G',
                 tr('Тип взаимодействия')]
        shown = [row[:-1] + (tr(crystal_aim.NATURE[row[-1]]),) for row in rows]
        lines = [tr('Критические точки (3,−1) электронной плотности, найденные Multiwfn в ячейке расчёта ({} атомов); '
                    'одинаковые связи (те же элементы и длина) собраны в строку.').format(atoms),
                 tr('∇²ρ > 0 и H > 0 (|V|/G < 1) — замкнутые оболочки: ионная связь или слабый контакт; ∇²ρ > 0 и H < 0 — '
                    'промежуточная; ∇²ρ < 0 — обобществлённая (ковалентная). Bader, 1990; Cremer, Kraka, 1984; '
                    'Espinosa и др., 2002.')]
        if census['poincare_hopf'] != 0:
            lines.append(tr('Найдены не все критические точки (ядра − связи + кольца − клетки = {}, а должно быть 0): '
                            '«связей у атома» может быть меньше настоящего.').format(census['poincare_hopf']))
        lines.append(tr('Multiwfn {} — T. Lu, F. Chen, J. Comput. Chem. 33, 580 (2012). Таблица — aim-bonds.csv в папке '
                        'расчёта.').format(version or ''))
        super().__init__(parent, tr('Связи по AIM · ') + name, heads, shown, lines)


class ChargesWindow(TableWindow):
    """The charges of Hirshfeld and CM5 of the atoms of a crystal, per element (crystal_aim.charge_rows)."""

    def __init__(self, parent, name, rows, version=None):
        heads = [tr('Элемент'), tr('Атомов в ячейке'), tr('Хиршфельд'), 'CM5', tr('Разброс CM5')]
        lines = [tr('Заряды атомов по разбиению Хиршфельда (на свободные атомы) и CM5 (Хиршфельд с поправкой, '
                    'воспроизводящей дипольные моменты; Marenich и др., 2012) — среднее по атомам элемента в ячейке '
                    'расчёта. Атомы, одинаковые по симметрии, имеют одинаковый заряд; заметный разброс — атомы разные '
                    'или сетка груба.'),
                 tr('Для кристалла Multiwfn не считает ADCH; интегрирование — на равномерной сетке ячейки (шаг 0,4 бохр).'),
                 tr('Multiwfn {} — T. Lu, F. Chen, J. Comput. Chem. 33, 580 (2012). По атомам — charges.csv в папке '
                    'расчёта.').format(version or '')]
        super().__init__(parent, tr('Заряды атомов · ') + name, heads, rows, lines)

"""An experimental spectrum over the computed one.

§1 PURPOSE
    A measured IR, Raman, UV-Vis or ECD
    spectrum opened from a file and drawn over the spectrum of the result; how alike they are, as a number; the factor
    of the frequencies (IR, Raman) or the shift of the excitation energies (UV-Vis, ECD) with which they are most alike.
§1 THEORY
    Both curves are put on one grid over the range they share and compared by the cosine of the angle between them —
    1 for the same shape, 0 for nothing in common, < 0 (ECD only) for bands of the opposite sign; the heights are
    normalised, so only the positions, the widths and the ratios of the bands count. An IR spectrum measured as
    transmittance is turned into absorbance A = −lg T first (the bands go up, as computed), and the lowest absorbance
    is taken as the baseline. The best factor is searched for in 0.90–1.05 (step 0.001), the best shift in −1…+1 eV
    (step 0.01): a harmonic method overestimates the frequencies, TD-DFT is off by a few tenths of an eV.
§4 SPECIFICATION
    Experiment(x, y, name, x_unit, y_unit) — x ascending as in the file's unit; read(path) / parse(text, name):
      JCAMP-DX (##XYDATA=(X++(Y..Y)) in AFFN and in the compressed ASDF forms SQZ, DIF, DUP with the Y check of DIF
      lines; ##XYPOINTS and ##PEAK TABLE as pairs; ##XFACTOR, ##YFACTOR, ##FIRSTX, ##LASTX, ##XUNITS, ##YUNITS);
      any other text — the first two numbers of each line (a decimal comma when the columns are split by «;» or a tab);
      the lines without two numbers (a header) are skipped. ValueError when fewer than 5 points are read.
    on_axis(experiment, axis, signed=False) -> (x, y): axis 'cm-1' (IR, Raman) or 'nm' (UV-Vis, ECD); the unit of a
      text file is guessed from the range (cm⁻¹ beyond 5000 for 'nm', eV below 15, µm below 30 for 'cm-1'); an IR
      transmittance (YUNITS, or a baseline near the top of the values) → absorbance; lg ε (YUNITS «LOGARITHM
      EPSILON» of the UV-Vis of NIST) → ε; heights / their largest |y|.
    similarity(curve, experiment_xy, signed=False) -> float | None (None: less than a tenth of the range shared).
    best(make_curve, values, experiment_xy, signed=False) -> (value, score) — the value of values with the largest
      score; FACTORS, SHIFTS. scaled(curve, factor), shifted_nm(wavelength, shift_ev),
      shifted_excitations(excitations, shift_ev).
§7 TESTS
    tests/spectrum/test_experiment.py.
"""

import re
from dataclasses import dataclass
from math import isfinite
from pathlib import Path

import numpy as np

from azimuth.i18n import tr

HC_EV_NM = 1239.841984  # λ (nm) × E (eV)
EV_CM = 8065.54394  # cm⁻¹ per eV
FACTORS = tuple(round(0.90 + 0.001 * k, 3) for k in range(151))
SHIFTS = tuple(round(-1.0 + 0.01 * k, 2) for k in range(201))
GRID = 800
MAX_BYTES = 64 * 1024 * 1024


@dataclass(frozen=True)
class Experiment:
    x: tuple
    y: tuple
    name: str = ''
    x_unit: str | None = None  # 'cm-1', 'nm', 'um', 'ev' or None (a text file: guessed on_axis)
    y_unit: str | None = None  # 'transmittance', 'absorbance', 'log' (lg ε, NIST UV-Vis) or None


# -- reading ---------------------------------------------------------------------------------------------------------

def read(path):
    p = Path(path)
    try:
        if p.stat().st_size > MAX_BYTES:
            raise ValueError(tr('Файл спектра больше 64 МБ.'))
        text = p.read_text(encoding='utf-8', errors='replace')
    except OSError as exc:
        raise ValueError(tr('Не удалось прочитать файл: ') + f'{p.name} ({exc})') from exc
    return parse(text, p.name)


def parse(text, name=''):
    if '##' in text and re.search(r'^\s*##\s*(XYDATA|XYPOINTS|PEAK\s*TABLE)\s*=', text, re.M | re.I):
        return _jcamp(text, name)
    return _columns(text, name)


def _columns(text, name):
    xs, ys = [], []
    for line in text.splitlines():
        line = line.strip()
        if not line or line[0] in '#%!':
            continue
        if ';' in line or '\t' in line:
            fields = [f.strip().replace(',', '.') for f in re.split(r'[;\t]', line) if f.strip()]
        elif ',' in line and '.' not in line and ' ' in line:
            fields = line.replace(',', '.').split()  # «1234,5 0,56»: decimal commas, the columns by spaces
        elif ',' in line:
            fields = [f.strip() for f in line.split(',')]  # «1234.5,0.56» or «1234.5, 0.56» — CSV
        else:
            fields = line.split()
        try:
            a, b = float(fields[0]), float(fields[1])
        except (ValueError, IndexError):
            continue
        if isfinite(a) and isfinite(b):
            xs.append(a)
            ys.append(b)
    return _finish(xs, ys, name, None, None)


def _finish(xs, ys, name, x_unit, y_unit):
    if len(xs) < 5:
        raise ValueError(tr('В файле нет спектра: нужны хотя бы 5 точек «x y» (столбцы через пробел, «;» или '
                            'табуляцию) или файл JCAMP-DX.'))
    order = np.argsort(np.asarray(xs, dtype=float), kind='stable')
    x = np.asarray(xs, dtype=float)[order]
    y = np.asarray(ys, dtype=float)[order]
    return Experiment(tuple(x.tolist()), tuple(y.tolist()), name, x_unit, y_unit)


def _labels(text):
    out = {}
    for m in re.finditer(r'^\s*##\s*([^=]+?)\s*=(.*)$', text, re.M):
        key = re.sub(r'[\s_/-]', '', m.group(1)).upper()
        out.setdefault(key, m.group(2).strip())
    return out


def _float(value, default=None):
    try:
        return float(str(value).split()[0].replace(',', '.'))
    except (ValueError, IndexError):
        return default


SQZ = {'@': 0, **{c: i + 1 for i, c in enumerate('ABCDEFGHI')}, **{c: -(i + 1) for i, c in enumerate('abcdefghi')}}
DIF = {'%': 0, **{c: i + 1 for i, c in enumerate('JKLMNOPQR')}, **{c: -(i + 1) for i, c in enumerate('jklmnopqr')}}
DUP = {**{c: i + 1 for i, c in enumerate('STUVWXYZ')}, 's': 9}


def _tokens(line):
    """The numbers of an ASDF line as they stand: an ordinary (AFFN) number, or one starting with a SQZ, a DIF or a
    DUP character."""
    out, k, n = [], 0, len(line)
    while k < n:
        c = line[k]
        if c in SQZ or c in DIF or c in DUP:
            j = k + 1
            while j < n and (line[j].isdigit() or line[j] == '.'):
                j += 1
        elif c.isdigit() or c in '+-.':
            j = k + 1
            while j < n and (line[j].isdigit() or line[j] == '.' or (line[j] in 'eE' and j + 1 < n
                                                                      and line[j + 1] in '+-0123456789')
                             or (line[j] in '+-' and line[j - 1] in 'eE')):
                j += 1
        else:
            k += 1  # a separator, or a «?» of a missing point
            continue
        out.append(line[k:j])
        k = j
    return out


def _asdf_line(line):
    """One line of ##XYDATA=(X++(Y..Y)): its X, its Ys (ASDF decoded) and whether it ended in a DIF form (then the
    first Y of the next line is a check value, the same Y again)."""
    x, values, step, last_dif = None, [], None, False
    for token in _tokens(line):
        head, rest = token[0], token[1:]
        if head in DUP:
            count = int(str(DUP[head]) + rest)
            for _ in range(count - 1):
                if not values:
                    break
                values.append(values[-1] + step if last_dif and step is not None else values[-1])
            continue
        if head in DIF:
            if not values:
                continue
            step = (-1 if DIF[head] < 0 else 1) * float(str(abs(DIF[head])) + rest)
            values.append(values[-1] + step)
            last_dif = True
            continue
        if head in SQZ:
            number = (-1 if SQZ[head] < 0 else 1) * float(str(abs(SQZ[head])) + rest)
        else:
            try:
                number = float(token)
            except ValueError:
                continue
        if x is None:
            x = number
            continue
        values.append(number)
        step, last_dif = None, False
    return x, values, last_dif


def _jcamp(text, name):
    labels = _labels(text)
    xf, yf = _float(labels.get('XFACTOR'), 1.0), _float(labels.get('YFACTOR'), 1.0)
    xu = (labels.get('XUNITS') or '').upper().replace(' ', '')
    yu = (labels.get('YUNITS') or '').upper()
    x_unit = ('cm-1' if '1/CM' in xu or 'CM-1' in xu or 'WAVENUMBER' in xu else 'nm' if 'NANOMETER' in xu or xu == 'NM'
              else 'um' if 'MICROMETER' in xu or xu in ('UM', 'MICRONS') else 'ev' if xu == 'EV' else None)
    # the UV-Vis of the NIST WebBook is «LOGARITHM EPSILON» — lg ε
    y_unit = ('transmittance' if 'TRANSMIT' in yu else 'log' if 'LOG' in yu else 'absorbance' if 'ABSORB' in yu
              else None)
    title = labels.get('TITLE') or name
    xs, ys = [], []
    block = re.search(r'^\s*##\s*XYDATA\s*=\s*\(X\+\+\(Y\.\.Y\)\)\s*$(.*?)(?=^\s*##)', text + '\n##END=',
                      re.M | re.S | re.I)
    if block:
        ys_all, previous_dif = [], False
        for line in block.group(1).splitlines():
            line = line.split('$$')[0].strip()
            if not line:
                continue
            x, values, ended_dif = _asdf_line(line)
            if x is None:
                continue
            if previous_dif and values and ys_all:
                values = values[1:]  # the Y check: the last Y of the line before, repeated
            ys_all.extend(values)
            previous_dif = ended_dif
        first, last = _float(labels.get('FIRSTX')), _float(labels.get('LASTX'))
        if ys_all and first is not None and last is not None:
            count = len(ys_all)
            xs = np.linspace(first, last, count).tolist() if count > 1 else [first]
            ys = [v * yf for v in ys_all]
    else:
        block = re.search(r'^\s*##\s*(?:XYPOINTS|PEAK\s*TABLE)\s*=\s*\(XY\.\.XY\)\s*$(.*?)(?=^\s*##)', text + '\n##END=',
                          re.M | re.S | re.I)
        if block:
            numbers = [float(v) for v in re.findall(r'[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?', block.group(1).split('$$')[0])]
            pairs = list(zip(numbers[0::2], numbers[1::2]))
            xs, ys = [a * xf for a, _ in pairs], [b * yf for _, b in pairs]
    return _finish(xs, ys, title or name, x_unit, y_unit)


# -- the axis of the plot ---------------------------------------------------------------------------------------------

def _unit(experiment, axis):
    if experiment.x_unit:
        return experiment.x_unit
    x = np.asarray(experiment.x)
    middle = float(np.median(x))
    if axis == 'nm':
        return 'cm-1' if middle > 5000 else 'ev' if middle < 15 else 'nm'
    return 'um' if middle < 30 else 'cm-1'


def is_transmittance(experiment):
    if experiment.y_unit:
        return experiment.y_unit == 'transmittance'
    y = np.asarray(experiment.y)
    if y.min() < -1e-9 or y.max() <= 0:
        return False
    return float(np.median(y)) > 0.7 * float(y.max())  # the baseline near the top — the bands go down


def on_axis(experiment, axis, signed=False):
    """(x ascending in cm⁻¹ or nm, y with its largest |y| = 1)."""
    x = np.asarray(experiment.x, dtype=float)
    y = np.asarray(experiment.y, dtype=float)
    unit = _unit(experiment, axis)
    if axis == 'cm-1':
        x = {'cm-1': x, 'um': 1e4 / np.where(x > 0, x, np.nan), 'nm': 1e7 / np.where(x > 0, x, np.nan),
             'ev': x * EV_CM}[unit]
    else:
        x = {'nm': x, 'cm-1': 1e7 / np.where(x > 0, x, np.nan), 'ev': HC_EV_NM / np.where(x > 0, x, np.nan),
             'um': x * 1000}[unit]
    if experiment.y_unit == 'log':
        y = np.power(10.0, np.clip(y, -30, 30))
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    if axis == 'cm-1' and not signed and is_transmittance(experiment):
        top = float(y.max())
        t = np.clip(y / (100.0 if top > 1.5 else 1.0), 1e-4, None)
        y = -np.log10(t)
    if not signed:
        y = y - float(y.min())
    order = np.argsort(x, kind='stable')
    x, y = x[order], y[order]
    peak = float(np.abs(y).max()) if len(y) else 0.0
    if len(x) < 5 or peak <= 0:
        raise ValueError(tr('В экспериментальном спектре нет полос.'))
    return x, y / peak


# -- how alike ---------------------------------------------------------------------------------------------------------

def similarity(curve, experiment_xy, signed=False):
    cx, cy = (np.asarray(v, dtype=float) for v in curve)
    ex, ey = experiment_xy
    order = np.argsort(cx, kind='stable')
    cx, cy = cx[order], cy[order]
    lo, hi = max(float(cx[0]), float(ex[0])), min(float(cx[-1]), float(ex[-1]))
    span = max(float(cx[-1]) - float(cx[0]), float(ex[-1]) - float(ex[0]))
    if hi <= lo or (hi - lo) < 0.1 * span:
        return None
    grid = np.linspace(lo, hi, GRID)
    a, b = np.interp(grid, cx, cy), np.interp(grid, ex, ey)
    if not signed:
        a, b = a - a.min(), b - b.min()
    norm = float(np.linalg.norm(a) * np.linalg.norm(b))
    return float(np.dot(a, b) / norm) if norm > 0 else None


def best(make_curve, values, experiment_xy, signed=False):
    found = None
    for value in values:
        try:
            score = similarity(make_curve(value), experiment_xy, signed)
        except ValueError:
            continue
        if score is not None and (found is None or score > found[1] + 1e-12):
            found = (value, score)
    if found is None:
        raise ValueError(tr('Расчётный и экспериментальный спектры почти не перекрываются — сравнить их нельзя.'))
    return found


def scaled(curve, factor):
    x, y = curve
    return np.asarray(x) * factor, np.asarray(y)


def shifted_nm(wavelength, shift_ev):
    """λ (nm) of a band whose energy is moved by shift_ev."""
    energy = HC_EV_NM / np.asarray(wavelength, dtype=float) + shift_ev
    return HC_EV_NM / np.where(energy > 0, energy, np.nan)


def shifted_excitations(excitations, shift_ev):
    """The excitations with their energies moved by shift_ev (UV-Vis, ECD); a band pushed below zero — left out."""
    if not shift_ev:
        return tuple(excitations)
    from dataclasses import replace

    out = []
    for e in excitations:
        energy = e.energy_ev + shift_ev
        if energy > 0:
            out.append(replace(e, energy_ev=energy, wavenumber=energy * EV_CM, wavelength=HC_EV_NM / energy))
    return tuple(out)

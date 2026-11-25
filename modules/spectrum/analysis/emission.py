"""Fluorescence and phosphorescence from an optimization of an excited state.

§1 PURPOSE
    Emission next to absorption. An optimization in an excited state (ORCA TD-DFT with %tddft iroot n, Gaussian
    TD(Root=n) Opt) holds the emission:
    the excitation energy of the root followed at the relaxed geometry of that state is the energy of the light it
    gives (vertical emission); at the starting geometry (the ground-state minimum, when the job starts from it) it is
    the absorption of the same state — their difference is the Stokes shift.
§1 THEORY
    Emission (Kasha): from the lowest state of its multiplicity — a singlet: fluorescence; a triplet: phosphorescence
    (its oscillator strength in TD-DFT without spin–orbit coupling is zero: the energy only). The radiative rate of
    a fluorescence (Einstein A coefficient, the Strickler–Berg form for one line in vacuum, n = 1):
        k_r = 8π² e² ν̃² f / (m_e c) = 0.6670 · ν̃²[cm⁻¹] · f s⁻¹, τ_r = 1 / k_r
    (in a solvent × n²). Stokes shift Δν̃ = ν̃_abs − ν̃_em; both vertical, no vibrational structure (that is ESD/FC).
§4 SPECIFICATION
    Point(root, energy_ev, fosc, multiplicity) — the root followed at one geometry.
    Emission(points, multiplicity, absorption, first) — points: one per geometry of the run; absorption: the
      excitations (orca_spectra.Excitation) at the first geometry. Properties: start, end (the first, the last point),
      stokes_cm, stokes_ev, rate (s⁻¹ or None when f ≈ 0 or a triplet), lifetime_ns, kind ('fluorescence' |
      'phosphorescence').
    read(text, program='') -> Emission | None — None unless the root of an excited state is followed at two or
      more geometries (ORCA: «DE(CIS) = … Eh (Root n)» of each cycle with its absorption table; Gaussian: the line
      «Excited State n: …» before «This state for optimization» of each cycle).
    A_COEFFICIENT = 0.6670; DARK = 1e-4 (an f below it: no rate — a forbidden transition).
§7 TESTS
    tests/spectrum/test_emission.py (ORCA 6.1.1, formaldehyde S1: n→π*, dark).
"""

import re
from dataclasses import dataclass

from azimuth.i18n import tr

A_COEFFICIENT = 0.6670  # s⁻¹ per (cm⁻¹)² per unit f: 8π²e²/(m_e c), cgs
DARK = 1e-4
EV_CM = 8065.543937
HC_EV_NM = 1239.841984
NUMBER = r'[-+]?\d+\.\d+(?:[eEdD][-+]?\d+)?'


@dataclass(frozen=True)
class Point:
    root: int
    energy_ev: float
    fosc: float | None
    multiplicity: int

    @property
    def wavelength(self):
        return HC_EV_NM / self.energy_ev

    @property
    def wavenumber(self):
        return self.energy_ev * EV_CM


@dataclass(frozen=True)
class Emission:
    points: tuple
    multiplicity: int
    absorption: tuple = ()  # the excitations at the first geometry

    @property
    def start(self):
        return self.points[0]

    @property
    def end(self):
        return self.points[-1]

    @property
    def kind(self):
        return 'phosphorescence' if self.multiplicity == 3 else 'fluorescence'

    @property
    def stokes_cm(self):
        return self.start.wavenumber - self.end.wavenumber

    @property
    def stokes_ev(self):
        return self.start.energy_ev - self.end.energy_ev

    @property
    def rate(self):
        f = self.end.fosc
        if self.kind == 'phosphorescence' or f is None or f < DARK:
            return None
        return A_COEFFICIENT * self.end.wavenumber ** 2 * f

    @property
    def lifetime_ns(self):
        rate = self.rate
        return None if not rate else 1e9 / rate


def _number(text):
    return float(text.replace('D', 'E').replace('d', 'e'))


def _orca(text):
    from modules.spectrum.readers.orca_spectra import read_absorption

    roots = [(m.start(), int(m[2]), _number(m[1])) for m in
             re.finditer(r'DE\(CIS\)\s*=\s*(' + NUMBER + r')\s*Eh\s*\(Root\s+(\d+)\)', text)]
    if len(roots) < 2:
        return None
    wanted = re.search(r'^\|\s*\d+>\s*irootmult\s+(\w+)', text, re.M | re.I)
    multiplicity = 3 if wanted and wanted[1].lower().startswith('trip') else 1
    headers = [m.start() for m in re.finditer(r'ABSORPTION SPECTRUM VIA TRANSITION ELECTRIC DIPOLE MOMENTS', text)]
    points, first = [], ()
    for k, (position, root, hartree) in enumerate(roots):
        energy = hartree * 27.211386246
        # the absorption table of this geometry: the last one printed before its «DE(CIS)»
        before = [h for h in headers if h < position]
        table = ()
        if before:
            end = next((h for h in headers if h > before[-1]), len(text))
            table = read_absorption(text[:end])
        if k == 0:
            first = table
        fosc = None
        if multiplicity == 1:
            match = [e for e in table if e.state == root and (e.multiplicity in (None, 1) or e.multiplicity == 1)]
            fosc = match[0].fosc if match else None
        points.append(Point(root, energy, fosc, multiplicity))
    return Emission(tuple(points), multiplicity, tuple(first))


def _gaussian(text):
    from modules.spectrum.readers.gaussian import _excitations

    row = re.compile(r'Excited State\s+(\d+):\s+(\S+?)-(\S+)\s+(' + NUMBER + r')\s+eV\s+(' + NUMBER + r')\s+nm\s+f=\s*('
                     + NUMBER + ')')
    states = list(row.finditer(text))
    followed = [m.start() for m in re.finditer(r'This state for optimization', text)]
    if len(followed) < 2:
        return None
    names = {'Singlet': 1, 'Doublet': 2, 'Triplet': 3, 'Quartet': 4, 'Quintet': 5}
    points = []
    for position in followed:
        before = [m for m in states if m.start() < position]
        if not before:
            continue
        m = before[-1]
        multiplicity = names.get(m[2], 1)
        points.append(Point(int(m[1]), _number(m[4]), _number(m[6]), multiplicity))
    if len(points) < 2:
        return None
    # the excitations of the first geometry: up to the first state printed after the first «This state …»
    second = next((m.start() for m in states if m.start() > followed[0] and int(m[1]) == 1), len(text))
    multiplicity = points[-1].multiplicity
    return Emission(tuple(points), 3 if multiplicity == 3 else 1, tuple(_excitations(text[:second])))


def read(text, program=''):
    if not text:
        return None
    if 'Gaussian' in program or 'Entering Gaussian System' in text:
        return _gaussian(text)
    return _orca(text)


def _n(value, spec):
    from azimuth import i18n

    text = format(value, spec)
    return text.replace('.', ',') if i18n.LANG == 'ru' else text


def summary(found):
    """One line of words for the panel."""
    if found is None:
        return ''
    end, start = found.end, found.start
    letter = 'T' if found.multiplicity == 3 else 'S'
    name = tr('Фосфоресценция') if found.kind == 'phosphorescence' else tr('Флуоресценция')
    text = tr('{} {}{}: {} нм ({} эВ)').format(name, letter, end.root, _n(end.wavelength, '.0f'),
                                               _n(end.energy_ev, '.2f'))
    if found.kind == 'fluorescence' and end.fosc is not None:
        text += ', f = ' + _n(end.fosc, '.4f')
    text += ' · ' + tr('поглощение того же состояния в начальной геометрии: {} нм ({} эВ)').format(
        _n(start.wavelength, '.0f'), _n(start.energy_ev, '.2f'))
    text += ' · ' + tr('стоксов сдвиг {} см⁻¹ ({} эВ)').format(_n(found.stokes_cm, '.0f'), _n(found.stokes_ev, '.2f'))
    if found.kind == 'phosphorescence':
        text += ' · ' + tr('интенсивность в TD-DFT без спин-орбитального взаимодействия не определена')
    elif found.lifetime_ns is not None:
        text += ' · ' + tr('излучательное время жизни τ ≈ {} нс').format(_n(found.lifetime_ns, '.3g'))
    else:
        text += ' · ' + tr('переход запрещён (f ≈ 0): излучение слабое')
    return text

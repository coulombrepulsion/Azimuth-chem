"""NMR multiplets from computed spin-spin couplings: the first-order splitting of every signal.

§1 PURPOSE
    The «ЯМР» page of Spectrum shows not only the shifts δ but how each signal is split by its neighbours: the
    CH₂ of ethanol a quartet from the CH₃, the vinyl protons of chloroethene doublets of doublets. The couplings J are
    those of the calculation (orca_spectra.read_couplings); the equivalent atoms (orca_spectra.equivalent_groups) give
    one signal, and their couplings to another group are averaged (the three H of a rotating CH₃ — 2.1, 5.3 and 14.3 Hz
    in the static geometry of the test data — give the familiar 7.2 Hz).
§2 MODEL (first order)
    A group A is split by every other group B of an observed partner element (ACTIVE: ¹H, ¹⁹F, ³¹P — spin ½ and near
    100 % abundant; ¹³C is 1.1 % and does not split the ¹H spectrum visibly) into n_B + 1 lines with binomial
    intensities, J_AB apart; the patterns of all partners are convolved. Couplings inside a group do not show.
    For a heteronucleus (¹³C …) the partners H are left out when decoupled (the usual ¹³C{¹H} spectrum).
    |J| below MIN_J (0.5 Hz) is hidden in the line width. ASSUMPTION — first order: valid while the shift difference
    |Δν| is much larger than J; for strongly coupled spins (the vinyl group at low field) the real pattern leans
    («roof effect») and has extra lines — said under the plot.
§3 INTERFACE
    group_couplings(groups, couplings) -> {(a, b): J} for group indices a < b (mean over the pairs that were computed).
    partners(index, groups, elements, couplings, decoupled=True) -> [(n, J)] by decreasing |J|.
    lines(delta, partners, mhz) -> [(ppm, intensity)] summing to 1 (mhz: the frequency of this nucleus).
    name(partners, lang=None) -> 'с', 'д', 'т', 'к', 'дт', 'м' … in Russian; s, d, t, q, dt, m in English and Chinese.
    curve(lines_by_signal, mhz, width_hz=1.0, lo, hi, points) -> (ppm, intensity): Lorentzians of width_hz.
    frequency(element, mhz_h) -> MHz of the nucleus at the field of an mhz_h ¹H spectrometer.
"""

from math import comb

import numpy as np


ACTIVE = {'H', 'F', 'P'}
MIN_J = 0.5  # Hz
RATIO = {'H': 1.0, 'C': 0.251449530, 'N': 0.101329118, 'F': 0.940866982, 'P': 0.404807356, 'Si': 0.198684}
LETTERS = {  # the abbreviations of the multiplets: Russian, and the international ones (en, zh)
    'ru': {0: 'с', 1: 'д', 2: 'т', 3: 'к', 4: 'квинт', 5: 'секст', 6: 'септ', None: 'м'},
    'en': {0: 's', 1: 'd', 2: 't', 3: 'q', 4: 'quint', 5: 'sext', 6: 'sept', None: 'm'},
}


def frequency(element, mhz_h):
    """The Larmor frequency of the nucleus (MHz) at the field of a mhz_h ¹H spectrometer (IUPAC Ξ ratios)."""
    return mhz_h * RATIO.get(element, 1.0)


def group_couplings(groups, couplings):
    at = {}
    for g, group in enumerate(groups):
        for a in group:
            at[a] = g
    sums = {}
    for i, j, value in couplings:
        if i not in at or j not in at or at[i] == at[j]:
            continue
        key = (min(at[i], at[j]), max(at[i], at[j]))
        total, count = sums.get(key, (0.0, 0))
        sums[key] = (total + value, count + 1)
    return {key: total / count for key, (total, count) in sums.items()}


def partners(index, groups, elements, couplings, decoupled=True):
    """The groups that split group index: (number of their atoms, J Hz), the largest |J| first."""
    own = elements[index]
    found = []
    for (a, b), value in group_couplings(groups, couplings).items():
        if index not in (a, b):
            continue
        other = b if a == index else a
        element = elements[other]
        if element not in ACTIVE or abs(value) < MIN_J:
            continue
        if decoupled and own != 'H' and element == 'H':
            continue
        found.append((len(groups[other]), value))
    return sorted(found, key=lambda p: -abs(p[1]))


def lines(delta, splitting, mhz):
    """The lines of one signal: (ppm, intensity) with the intensities summing to 1."""
    peaks = {0.0: 1.0}
    for n, j in splitting:
        pattern = [((k - n / 2.0) * j, comb(n, k) / 2.0 ** n) for k in range(n + 1)]
        new = {}
        for hz, weight in peaks.items():
            for shift, share in pattern:
                key = round(hz + shift, 6)
                new[key] = new.get(key, 0.0) + weight * share
        peaks = new
    return sorted((delta + hz / mhz, weight) for hz, weight in peaks.items())


def name(splitting, lang=None):
    from azimuth import i18n

    letters = LETTERS['ru' if (lang or i18n.LANG) == 'ru' else 'en']
    if not splitting:
        return letters[0]
    if len(splitting) > 3:
        return letters[None]
    return ''.join(letters.get(n, letters[None]) for n, _ in splitting)


def curve(signals, mhz, width_hz=1.0, lo=None, hi=None, points=4000):
    """signals: [(lines, weight)] — weight is the number of atoms. → (ppm increasing, intensity)."""
    every = [p for ls, _ in signals for p, _ in ls]
    if not every:
        return np.array([]), np.array([])
    pad = 20 * width_hz / mhz
    lo = min(every) - pad if lo is None else lo
    hi = max(every) + pad if hi is None else hi
    x = np.linspace(lo, hi, points)
    gamma = width_hz / 2.0 / mhz
    y = np.zeros_like(x)
    for ls, weight in signals:
        for ppm, share in ls:
            y += weight * share * gamma ** 2 / ((x - ppm) ** 2 + gamma ** 2)
    return x, y

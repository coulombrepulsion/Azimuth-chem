"""The isotope pattern of a molecular ion: M, M+1, M+2… with their exact masses.

§1 PURPOSE
    «Mass spectrum analysis tools» of Chemcraft, for Spectrum («Инструменты → Изотопный пик молекулярного иона…»):
    what the molecular-ion cluster of a formula looks like — 3:1 at M and M+2 for one chlorine, 1:2:1 for two
    bromines, the M+1 of thirteen-carbon that grows with the number of carbons.
§1 THEORY
    The natural isotopes of an element are independent: the distribution of the molecule is the convolution of the
    distributions of its atoms. Peaks are grouped by the nominal shift from the lightest combination (M + n, n the
    sum of the mass numbers above the lightest isotopes); a group has the sum of the probabilities and their mean
    exact mass. Data: NIST «Atomic Weights and Isotopic Compositions» (relative atomic masses, representative isotopic
    compositions); Cl-35 34.968852682, Cl-37 36.965902602 were checked against the NIST page on
    2026-11-05; every value of this table compared with the NIST page «for All Elements» — the same. The
    elements it has not are taken from azimuth/isotope_table.py (the same NIST page).
§2 ALGORITHM
    formula_counts(text) reads «C6H5Cl», «C2H6O», «(CH3)2CO» is not supported (no brackets). pattern(counts): fold
    the element distributions one atom at a time by binary powers (n atoms = sums of 1, 2, 4… atoms), dropping
    probabilities below CUT; the result relative to the largest peak (100) and also to M (the monoisotopic peak).
§4 SPECIFICATION
    ISOTOPES {symbol: ((mass number, exact mass, abundance), …)}; formula_counts(text) -> {symbol: n};
    pattern(counts, least=0.01) -> [(shift n, mean exact mass, % of the largest)] with % ≥ least; monoisotopic(counts)
    -> exact mass; average(counts) -> molar mass from the same table. ValueError for an element without data.
§7 TESTS tests/spectrum/test_isotopes.py: Cl₂ 100 : 63.97 : 10.23 (exact: 0.7576² : 2·0.7576·0.2424 : 0.2424²), Br₂
    1:2:1 near, CH₄ M+1 ≈ 1.1 %, the monoisotopic mass of water 18.010565.
"""

import re

CUT = 1e-12
ISOTOPES = {
    'H': ((1, 1.00782503223, 0.999885), (2, 2.01410177812, 0.000115)),
    'Li': ((6, 6.0151228874, 0.0759), (7, 7.0160034366, 0.9241)),
    'B': ((10, 10.01293695, 0.199), (11, 11.00930536, 0.801)),
    'C': ((12, 12.0, 0.9893), (13, 13.00335483507, 0.0107)),
    'N': ((14, 14.00307400443, 0.99636), (15, 15.00010889888, 0.00364)),
    'O': ((16, 15.99491461957, 0.99757), (17, 16.9991317565, 0.00038), (18, 17.99915961286, 0.00205)),
    'F': ((19, 18.99840316273, 1.0),),
    'Na': ((23, 22.989769282, 1.0),),
    'Mg': ((24, 23.985041697, 0.7899), (25, 24.985836976, 0.1), (26, 25.982592968, 0.1101)),
    'Al': ((27, 26.98153853, 1.0),),
    'Si': ((28, 27.97692653465, 0.92223), (29, 28.9764946649, 0.04685), (30, 29.973770136, 0.03092)),
    'P': ((31, 30.97376199842, 1.0),),
    'S': ((32, 31.9720711744, 0.9499), (33, 32.9714589098, 0.0075), (34, 33.967867004, 0.0425),
          (36, 35.96708071, 0.0001)),
    'Cl': ((35, 34.968852682, 0.7576), (37, 36.965902602, 0.2424)),
    'K': ((39, 38.9637064864, 0.932581), (40, 39.963998166, 0.000117), (41, 40.9618252579, 0.067302)),
    'Fe': ((54, 53.93960899, 0.05845), (56, 55.93493633, 0.91754), (57, 56.93539284, 0.02119),
           (58, 57.93327443, 0.00282)),
    'Cu': ((63, 62.92959772, 0.6915), (65, 64.9277897, 0.3085)),
    'Zn': ((64, 63.92914201, 0.4917), (66, 65.92603381, 0.2773), (67, 66.92712775, 0.0404),
           (68, 67.92484455, 0.1845), (70, 69.9253192, 0.0061)),
    'Se': ((74, 73.922475934, 0.0089), (76, 75.919213704, 0.0937), (77, 76.919914154, 0.0763),
           (78, 77.91730928, 0.2377), (80, 79.9165218, 0.4961), (82, 81.9166995, 0.0873)),
    'Br': ((79, 78.9183376, 0.5069), (81, 80.9162897, 0.4931)),
    'I': ((127, 126.9044719, 1.0),),
}
# the elements this table had no data for — from the table of all the stable isotopes (Pt, Sn, Hg …)
from azimuth.isotope_table import STABLE as _STABLE  # noqa: E402

for _symbol, _rows in _STABLE.items():
    ISOTOPES.setdefault(_symbol, _rows)


def formula_counts(text):
    counts = {}
    clean = (text or '').replace(' ', '')
    if not clean or not re.fullmatch(r'([A-Z][a-z]?\d*)+', clean):
        raise ValueError('Формула — символы элементов с числами, например C6H5Cl (без скобок).')
    for symbol, number in re.findall(r'([A-Z][a-z]?)(\d*)', clean):
        counts[symbol] = counts.get(symbol, 0) + (int(number) if number else 1)
    return counts


def _check(counts):
    missing = sorted(s for s, n in counts.items() if n and s not in ISOTOPES)
    if missing:
        raise ValueError('Нет данных об изотопах для: ' + ', '.join(missing))


def _fold(a, b):
    """The convolution of two distributions {shift: (probability, probability × mass)}."""
    out = {}
    for sa, (pa, ma) in a.items():
        for sb, (pb, mb) in b.items():
            p = pa * pb
            if p < CUT:
                continue
            old = out.get(sa + sb, (0.0, 0.0))
            out[sa + sb] = (old[0] + p, old[1] + pa * mb + pb * ma)  # Σ p·(mass_a + mass_b)
    return out


def _element(symbol):
    rows = ISOTOPES[symbol]
    light = rows[0][0]
    return {number - light: (share, share * mass) for number, mass, share in rows}


def _power(dist, n):
    result, base = {0: (1.0, 0.0)}, dist
    while n:
        if n & 1:
            result = _fold(result, base)
        n >>= 1
        if n:
            base = _fold(base, base)
    return result


def pattern(counts, least=0.01):
    _check(counts)
    total = {0: (1.0, 0.0)}
    for symbol, n in sorted(counts.items()):
        if n:
            total = _fold(total, _power(_element(symbol), n))
    top = max(p for p, _ in total.values())
    return [(shift, weighted / p, 100 * p / top) for shift, (p, weighted) in sorted(total.items())
            if 100 * p / top >= least]


def monoisotopic(counts):
    _check(counts)
    return sum(n * ISOTOPES[s][0][1] for s, n in counts.items())


def average(counts):
    _check(counts)
    return sum(n * sum(mass * share for _, mass, share in ISOTOPES[s]) for s, n in counts.items())

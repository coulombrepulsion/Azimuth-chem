"""Scaling factors of harmonic frequencies for the IR spectrum of Spectrum.

§1 THEORY
    Harmonic frequencies of a quantum-chemical method are higher than the observed fundamentals (anharmonicity, the
    method and the basis): B3LYP by about 3–4 %, HF by about 10 %. One factor per method and basis, fitted on many
    molecules, brings them close on average: ν(observed) ≈ c · ω(computed). The uncertainty (one standard deviation
    of the fit) says how far a single band may still be.
§2 SOURCE
    NIST Computational Chemistry Comparison and Benchmark DataBase (CCCBDB), «Precomputed vibrational scaling
    factors», https://cccbdb.nist.gov/vibscalejustx.asp and the pages of each pair
    https://cccbdb.nist.gov/vibscale2x.asp?method=…&basis=… (read 2026-11-01; e.g. B3LYP/6-31G* 0.960 ± 0.022 from
    266 molecules, 2626 vibrations). def2-TZVPP — the ECP table of the same page (no uncertainty given). The basis sets
    of Sextant without a CCCBDB entry (def2-SVP, def2-TZVP, pcseg-n …) take the factor of the CCCBDB basis of the same
    size (SIMILAR), and it is said so.
§4 SPECIFICATION
    FACTORS {method: {basis: (factor, uncertainty | None)}}; recommended(level) -> Suggestion | None,
    Suggestion(factor, uncertainty, method, basis, exact, note); METHOD_NAMES (aliases of the programs).
§7 TESTS tests/spectrum/test_scaling.py.
"""

import re
from dataclasses import dataclass

from azimuth.i18n import tr

SOURCE = 'NIST CCCBDB, cccbdb.nist.gov/vibscalejustx.asp (2026-11-01)'

# basis ids of CCCBDB (checked on the pages of B3LYP): 20 STO-3G, 9 6-31G, 1 6-31G*, 3 6-31G**, 4 6-31+G**,
# 21 6-311G**, 32 TZVP, 5 cc-pVDZ, 6 cc-pVTZ, 17 aug-cc-pVDZ, 18 aug-cc-pVTZ
FACTORS = {
    'HF': {'STO-3G': (0.817, 0.048), '6-31G': (0.903, 0.040), '6-31G*': (0.899, 0.025), '6-31G**': (0.903, 0.026),
           '6-31+G**': (0.904, 0.025), '6-311G**': (0.909, 0.025), 'TZVP': (0.909, 0.022), 'cc-pVDZ': (0.908, 0.025),
           'cc-pVTZ': (0.910, 0.027), 'aug-cc-pVDZ': (0.911, 0.025), 'aug-cc-pVTZ': (0.910, 0.024),
           'def2-TZVPP': (0.906, None)},
    'MP2': {'STO-3G': (0.872, 0.057), '6-31G': (0.957, 0.046), '6-31G*': (0.943, 0.027), '6-31G**': (0.937, 0.027),
            '6-31+G**': (0.941, 0.031), '6-311G**': (0.950, 0.025), 'TZVP': (0.948, 0.058), 'cc-pVDZ': (0.953, 0.028),
            'cc-pVTZ': (0.950, 0.072), 'aug-cc-pVDZ': (0.959, 0.031), 'aug-cc-pVTZ': (0.953, 0.033),
            'def2-TZVPP': (0.952, None)},
    'B3LYP': {'STO-3G': (0.892, 0.051), '6-31G': (0.962, 0.041), '6-31G*': (0.960, 0.022), '6-31G**': (0.961, 0.045),
              '6-31+G**': (0.964, 0.023), '6-311G**': (0.967, 0.021), 'TZVP': (0.965, 0.020), 'cc-pVDZ': (0.970, 0.025),
              'cc-pVTZ': (0.967, 0.018), 'aug-cc-pVDZ': (0.970, 0.026), 'aug-cc-pVTZ': (0.968, 0.019),
              'def2-TZVPP': (0.963, None)},
    'PBE0': {'STO-3G': (0.882, 0.055), '6-31G': (0.956, 0.041), '6-31G*': (0.950, 0.019), '6-31G**': (0.953, 0.021),
             '6-31+G**': (0.955, 0.022), '6-311G**': (0.959, 0.021), 'TZVP': (0.960, 0.021), 'cc-pVDZ': (0.962, 0.025),
             'cc-pVTZ': (0.961, 0.021), 'aug-cc-pVDZ': (0.962, 0.025), 'aug-cc-pVTZ': (0.962, 0.021)},
    'M06-2X': {'6-31G*': (0.947, 0.019), '6-31G**': (0.950, 0.022), '6-31+G**': (0.952, 0.022), 'TZVP': (0.946, 0.068),
               'cc-pVTZ': (0.955, 0.019), 'aug-cc-pVTZ': (0.956, 0.019)},
    'ωB97X-D': {'6-31G*': (0.949, 0.019), '6-31+G**': (0.952, 0.020), '6-311G**': (0.957, 0.020), 'TZVP': (0.955, 0.020),
                'cc-pVDZ': (0.953, 0.020), 'cc-pVTZ': (0.956, 0.020), 'aug-cc-pVDZ': (0.957, 0.020),
                'aug-cc-pVTZ': (0.957, 0.020), 'def2-TZVPP': (0.955, None)},
    'B2PLYP': {'6-31G*': (0.949, 0.020), '6-31+G**': (0.952, 0.022), 'TZVP': (0.954, 0.059), 'cc-pVDZ': (0.958, 0.064),
               'cc-pVTZ': (0.959, 0.019), 'aug-cc-pVTZ': (0.961, 0.018)},
    'BLYP': {'STO-3G': (0.925, 0.060), '6-31G': (0.992, 0.047), '6-31G*': (0.992, 0.027), '6-31G**': (0.992, 0.027),
             '6-31+G**': (0.995, 0.030), '6-311G**': (0.996, 0.026), 'TZVP': (0.998, 0.025), 'cc-pVDZ': (1.002, 0.030),
             'cc-pVTZ': (0.997, 0.026), 'aug-cc-pVDZ': (0.998, 0.030), 'aug-cc-pVTZ': (0.997, 0.021)},
    'PBE': {'STO-3G': (0.914, 0.058), '6-31G': (0.986, 0.045), '6-31G*': (0.986, 0.026), '6-31G**': (0.986, 0.026),
            '6-31+G**': (0.989, 0.027), '6-311G**': (0.991, 0.025), 'TZVP': (0.989, 0.060), 'cc-pVDZ': (0.994, 0.030),
            'cc-pVTZ': (0.993, 0.025), 'aug-cc-pVDZ': (0.994, 0.031), 'aug-cc-pVTZ': (0.994, 0.022),
            'def2-TZVPP': (0.988, None)},
    'TPSSh': {'6-31G': (0.962, 0.066), '6-31G*': (0.959, 0.021), '6-31G**': (0.959, 0.056), '6-31+G**': (0.963, 0.021),
              'TZVP': (0.964, 0.061), 'cc-pVDZ': (0.972, 0.023), 'cc-pVTZ': (0.968, 0.019), 'aug-cc-pVDZ': (0.967, 0.058),
              'aug-cc-pVTZ': (0.965, 0.061)},
}
# the names programs print → the names above
METHOD_NAMES = {'HF': 'HF', 'RHF': 'HF', 'UHF': 'HF', 'MP2': 'MP2', 'RI-MP2': 'MP2', 'B3LYP': 'B3LYP', 'PBE0': 'PBE0',
                'PBE1PBE': 'PBE0', 'M062X': 'M06-2X', 'M06-2X': 'M06-2X', 'WB97XD': 'ωB97X-D', 'WB97X-D': 'ωB97X-D',
                'ΩB97X-D': 'ωB97X-D', 'B2PLYP': 'B2PLYP', 'BLYP': 'BLYP', 'PBE': 'PBE', 'PBEPBE': 'PBE', 'TPSSH': 'TPSSh'}
# a basis of Sextant without its own CCCBDB entry → the CCCBDB basis of the same size
SIMILAR = {'def2-SVP': 'cc-pVDZ', 'pcseg-1': 'cc-pVDZ', 'def2-SVPD': 'aug-cc-pVDZ', 'def2-TZVP': 'TZVP',
           'def2-TZVPD': 'aug-cc-pVTZ', 'def2-QZVP': 'cc-pVTZ', 'pcseg-2': 'cc-pVTZ', '6-31+G*': '6-31+G**'}
BASES = ('STO-3G', '6-31G', '6-31G*', '6-31G**', '6-31+G*', '6-31+G**', '6-311G**', 'TZVP', 'def2-SVP', 'def2-SVPD',
         'def2-TZVP', 'def2-TZVPD', 'def2-TZVPP', 'def2-QZVP', 'cc-pVDZ', 'cc-pVTZ', 'aug-cc-pVDZ', 'aug-cc-pVTZ',
         'pcseg-1', 'pcseg-2')


@dataclass(frozen=True)
class Suggestion:
    factor: float
    uncertainty: object
    method: str
    basis: str
    exact: bool
    note: str


def _norm(text):
    return text.upper().replace('(D)', '*').replace('(D,P)', '**').replace('-D3BJ', '').replace('-D3', '')


def parse_level(level):
    """(method, basis) of a level of theory as reaction.level_of_theory gives it («B3LYP/6-31G(d)», «MP2 STO-3G»)."""
    words = re.split(r'[\s/]+', level.strip())
    method = basis = None
    by_name = {_norm(b): b for b in BASES}
    for word in words:
        w = _norm(word)
        if method is None and w in METHOD_NAMES:
            method = METHOD_NAMES[w]
        elif basis is None and w in by_name:
            basis = by_name[w]
    return method, basis


def recommended(level=None, method=None, basis=None):
    if level:
        method, basis = parse_level(level)
    if method not in FACTORS or not basis:
        return None
    table = FACTORS[method]
    if basis in table:
        factor, unc = table[basis]
        return Suggestion(factor, unc, method, basis, True, tr(f'{method}/{basis} — {SOURCE}'))
    near = SIMILAR.get(basis)
    if near in table:
        factor, unc = table[near]
        return Suggestion(factor, unc, method, basis, False,
                          tr(f'Для {method}/{basis} в CCCBDB множителя нет; взят {method}/{near} (базис того же размера) — {SOURCE}'))
    return None

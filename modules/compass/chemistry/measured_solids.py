"""The measured lattice constants, bulk moduli and band gaps of simple solids, and their PBE values of the
literature — next to a calculation of a crystal (the panel of Quantum ESPRESSO and CP2K, the result without the window).

§1 PURPOSE
    A calculation of Si, MgO or NaCl is judged against two numbers: experiment (how good the method is) and PBE of the
    literature (whether the calculation is done right: the pseudopotentials, the cutoffs, the k grid). A PBE lattice
    constant 1 % above experiment is the method; one 1 % off the PBE of the literature is the calculation.
§2 DATA (data/measured_solids.json)
    The 24 solids of Csonka et al., Phys. Rev. B 79, 155107 (2009), arXiv:0903.4037, Tables II and V: the lattice
    constant measured and corrected for the zero-point anharmonic expansion (ZPAE) — the lattice of the static nuclei,
    the one a DFT calculation gives —, its PBE value, the bulk modulus measured (corrected for the temperature, not for
    the zero-point motion) and of PBE. The band gaps measured — Tran, Blaha, Phys. Rev. Lett. 102, 226401 (2009), Table I
    (the semiconductors and insulators there).
§3 RECOGNITION
    identify(crystal): the space group (crystal.number, else found by its symbol — space_groups.find) and the formula
    of the cell reduced by the greatest common divisor equal to those of an entry. A file that is a supercell or of
    another polymorph is not recognized (another group or no group).
§4 SPECIFICATION
    solids() -> [dict]; identify(crystal) -> dict | None; lattice_line(entry, a) / bulk_line(entry, b0) /
    gap_line(entry, gap) -> str ('' when the entry has no such value); SOURCE.
§7 TESTS tests/compass/test_measured_solids.py.
"""

from __future__ import annotations

import json
from functools import lru_cache
from math import gcd
from pathlib import Path

from azimuth.i18n import tr

DATA = Path(__file__).resolve().parent / 'data' / 'measured_solids.json'
SOURCE = 'Csonka et al., PRB 79, 155107 (2009); band gaps — Tran, Blaha, PRL 102, 226401 (2009)'


@lru_cache(maxsize=1)
def _data():
    return json.loads(DATA.read_text(encoding='utf-8'))


def solids():
    return _data()['solids']


def _reduced(counts):
    g = 0
    for n in counts.values():
        g = gcd(g, int(n))
    return {k: int(n) // max(1, g) for k, n in counts.items()}


def _number(crystal):
    number = int(getattr(crystal, 'number', 0) or 0)
    if number:
        return number
    from modules.compass.chemistry import space_groups

    found = space_groups.find(getattr(crystal, 'space_group', '') or '')
    return int(found['number']) if found else 0


def identify(crystal):
    """The entry of the crystal, or None."""
    if crystal is None:
        return None
    from modules.compass.chemistry import crystal as cr

    try:
        atoms = cr.unit_cell(crystal)
    except (ValueError, AttributeError, TypeError):
        return None
    counts = {}
    for atom in atoms:
        if atom[0] != 'X':  # a dummy site
            counts[atom[0]] = counts.get(atom[0], 0) + 1
    if not counts:
        return None
    formula, number = _reduced(counts), _number(crystal)
    return next((s for s in solids() if s['space_group'] == number and _reduced(s['composition']) == formula), None)


def _percent(value, reference):
    return 100.0 * (value - reference) / reference


def lattice_line(entry, a=None):
    """The lattice constant of the cell of the file (a cubic one) against experiment and PBE of the literature."""
    if entry is None or entry.get('a_exp') is None:
        return ''
    text = tr('Опыт: a = {} Å (без нулевых колебаний), PBE в литературе {} Å').format(
        f"{entry['a_exp']:.3f}", f"{entry['a_pbe']:.3f}")
    if a:
        text += tr('; здесь {} Å — {} % от опыта, {} % от PBE литературы').format(
            f'{a:.3f}', f"{_percent(a, entry['a_exp']):+.1f}", f"{_percent(a, entry['a_pbe']):+.1f}")
    return text + '.'


def bulk_line(entry, b0=None):
    if entry is None or entry.get('b_exp') is None:
        return ''
    text = tr('Опыт: B₀ = {} ГПа, PBE в литературе {} ГПа').format(f"{entry['b_exp']:g}", f"{entry['b_pbe']:g}")
    if b0:
        text += tr('; здесь {} ГПа').format(f'{b0:.1f}')
    return text + '.'


def gap_line(entry, gap=None):
    if entry is None or entry.get('gap_exp') is None:
        return ''
    text = tr('Опытная щель {} эВ').format(f"{entry['gap_exp']:g}")
    if gap is not None:
        text += tr(' (здесь {} эВ: PBE и LDA занижают щель — обычно в полтора-два раза)').format(f'{gap:.2f}')
    return text + '.'

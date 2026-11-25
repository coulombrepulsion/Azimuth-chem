"""The 230 space groups in their 530 settings: operations from a symbol.

§1 THEORY
    A space group is given in a CIF by its operations (_space_group_symop_operation_xyz); many older files and those
    of other programs give only the symbol (_space_group_name_H-M_alt, _symmetry_space_group_name_H-M, the Hall
    symbol _space_group_name_Hall) or the number (_space_group_IT_number). The symbol names the setting: the axes
    (P 1 21/c 1 or P 1 21/n 1, P n m a or P b n m), the origin choice (F d -3 m :1 or :2), hexagonal or rhombohedral
    axes (R -3 :H, R -3 :R). The table (data/space_groups.json, from spglib 2.7.0, tools/make_crystal_tables.py)
    lists each of the 530 settings of the International Tables vol. A with its Hall number: the centring
    translations and one operation of each coset; the operations are their products.
§2 ALGORITHM
    key(symbol): lower case without spaces and underscores ('P 21/c' -> 'p21/c', 'P2_1/c' -> 'p21/c'; a monoclinic
    full symbol also without its two 1s, 'P 1 21/n 1' -> 'P 21/n', as most files write it); a suffix
    ':1', ':2', ':h', ':r' (or an origin '1'/'2' and 'H'/'R' as spglib writes the choice) names the setting.
    find(symbol, hall_symbol, number): the Hall symbol first (it is unique), then the Hermann–Mauguin symbol among
    the short, full and alias symbols of every setting — when several settings share it (origin choices, the
    cells of a monoclinic group), the one named by the suffix, else the default of the CIF dictionary and of most
    programs: origin choice 2, hexagonal axes, the first (b-unique, cell 1) monoclinic setting; then the number alone
    (its default setting as above).
§3 APPLICATIONS
    modules/compass/chemistry/crystal.py parse_cif: the operations of a file that gives only a symbol or a number.
§4 SPECIFICATION
    find(symbol='', hall_symbol='', number=0) -> dict (hall, number, choice, short, full, aliases, hall_symbol,
    centring, operations) or None; operations(entry) -> tuple of 'x,y,z' texts (the full group, coset by coset);
    describe(entry) -> 'P 1 21/c 1 (№ 14)'.
§5 PROCEDURES - below.
§6 NOTES
    The table is read once on first use (150 KB). Unknown symbols give None: the file is then taken as P1 and the
    window says so, as before.
§7 TESTS
    tests/compass/test_space_groups.py.
§8' ROBUSTNESS / ERRORS
    No exceptions for unknown or malformed symbols; a missing table file raises (it is part of the program).
"""

from fractions import Fraction
from functools import lru_cache
import json
from pathlib import Path

TABLE = Path(__file__).with_name('data') / 'space_groups.json'
_DEFAULT = {'': 0, 'b': 0, 'b1': 0, '2': 0, 'H': 0}  # the preferred choices; others rank by Hall number


def key(symbol):
    text = str(symbol or '').strip().strip('\'"').lower().replace('_', '').replace(' ', '')
    setting = ''
    if ':' in text:
        text, setting = text.split(':', 1)
    return text, setting


@lru_cache(maxsize=1)
def _table():
    groups = json.loads(TABLE.read_text(encoding='utf-8'))['groups']
    by_symbol, by_hall, by_number = {}, {}, {}
    for g in groups:
        by_hall[g['hall_symbol'].lower().replace(' ', '')] = g
        by_number.setdefault(g['number'], []).append(g)
        names = {g['short'], g['full'], *g['aliases']}
        tokens = g['full'].split()
        if len(tokens) == 4 and tokens[1:].count('1') == 2:  # monoclinic 'P 1 2_1/n 1' is also written 'P 21/n'
            names.add(' '.join([tokens[0]] + [t for t in tokens[1:] if t != '1']))
        for s in names:
            by_symbol.setdefault(key(s)[0], []).append(g)
    return groups, by_symbol, by_hall, by_number


def _rank(g):
    return (_DEFAULT.get(g['choice'], 1), g['hall'])


def _pick(candidates, setting):
    if not candidates:
        return None
    if setting:
        named = [g for g in candidates if g['choice'].lower() == setting
                 or g['choice'].lower() == setting.lstrip('0')]
        if named:
            return min(named, key=_rank)
    return min(candidates, key=_rank)


def find(symbol='', hall_symbol='', number=0):
    _, by_symbol, by_hall, by_number = _table()
    if hall_symbol:
        g = by_hall.get(str(hall_symbol).strip().strip('\'"').lower().replace(' ', '').replace('_', ''))
        if g is not None:
            return g
    if symbol:
        text, setting = key(symbol)
        found = by_symbol.get(text, [])
        if number:
            found = [g for g in found if g['number'] == number] or found
        g = _pick(found, setting)
        if g is not None:
            return g
    if number and int(number) in by_number:
        return _pick(by_number[int(number)], '')
    return None


def _fraction_text(f):
    return f'{f.numerator}/{f.denominator}' if f.denominator > 1 else str(f.numerator)


def _text(rows, t):
    parts = []
    for row, shift in zip(rows, t):
        terms = ''
        for coeff, name in zip(row, 'xyz'):
            if coeff:
                terms += ('-' if coeff < 0 else ('+' if terms else '')) + ('' if abs(coeff) == 1 else str(abs(coeff))) + name
        shift = Fraction(shift) % 1
        parts.append(terms + (f'+{_fraction_text(shift)}' if shift else ''))
    return ','.join(parts)


def operations(entry):
    """All operations of the setting: every coset operation plus every centring translation."""
    from modules.compass.chemistry import crystal as cr

    out = []
    for c in entry['centring']:
        shift = [Fraction(x) for x in c.split(',')]
        for text in entry['operations']:
            rows, t = cr.operation(text)
            out.append(_text(rows, [t[i] + shift[i] for i in range(3)]))
    return tuple(out)


def describe(entry):
    return f"{entry['full'].replace('_', '')} (№ {entry['number']})"

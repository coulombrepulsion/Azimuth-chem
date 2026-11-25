"""Make the crystal data tables of Compass from spglib and xraydb.

Run once, in a throw-away environment with `pip install spglib xraydb`:
    python tools/make_crystal_tables.py
It writes
    modules/compass/chemistry/data/space_groups.json — the 530 settings (Hall numbers) of the 230 space groups of
        spglib 2.7.0 (BSD-3-Clause, © Spglib team; the text of the licence in data/LICENSE-spglib.txt): number,
        setting (choice), Hermann–Mauguin symbols, Hall symbol, the point group (both notations), the centring
        translations and one operation of
        each coset as 'x,y,z' texts;
    modules/compass/chemistry/data/xray_f0.json — the coefficients of the X-ray atomic scattering factors of
        Waasmaier & Kirfel (Acta Cryst. A51, 416, 1995) as tabulated by xraydb 4.5.8 (MIT, © M. Newville; the text
        in data/LICENSE-xraydb.txt): f0(s) = c + sum a_i exp(-b_i s^2), s = sin(theta)/lambda in 1/A.
Neither package is needed by the program.
"""

import json
import sqlite3
from fractions import Fraction
from pathlib import Path

import numpy as np
import spglib
import xraydb

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'modules' / 'compass' / 'chemistry' / 'data'


def _frac(t):
    f = Fraction(float(t)).limit_denominator(12) % 1
    return f


def xyz(rotation, translation):
    parts = []
    for row, t in zip(rotation, translation):
        text = ''
        for coeff, name in zip(row, 'xyz'):
            c = int(round(coeff))
            if c == 0:
                continue
            sign = '-' if c < 0 else ('+' if text else '')
            text += sign + ('' if abs(c) == 1 else str(abs(c))) + name
        f = _frac(t)
        if f:
            text += f'+{f.numerator}/{f.denominator}' if f.denominator > 1 else f'+{f.numerator}'
        parts.append(text)
    return ','.join(parts)


def space_groups():
    groups = []
    for hall in range(1, 531):
        t = spglib.get_spacegroup_type(hall)
        ops = spglib.get_symmetry_from_database(hall)
        rotations, translations = ops['rotations'], ops['translations']
        identity = np.eye(3, dtype=int)
        centring = sorted({tuple(_frac(x) for x in tr) for r, tr in zip(rotations, translations)
                           if (r == identity).all()})
        reps, seen = [], set()
        for r, tr in zip(rotations, translations):
            key = tuple(r.flatten())
            if key in seen:
                continue
            seen.add(key)
            reps.append(xyz(r, tr))
        assert len(reps) * len(centring) == len(rotations), hall
        aliases = [a.strip() for a in t.international.split('=')]
        groups.append({
            'hall': hall, 'number': t.number, 'choice': t.choice, 'short': t.international_short,
            'full': t.international_full, 'aliases': aliases, 'hall_symbol': t.hall_symbol,
            'point_group': t.pointgroup_international, 'schoenflies': t.pointgroup_schoenflies,
            'centring': [','.join(str(x) for x in c) for c in centring], 'operations': reps,
        })
    return groups


def f0_table():
    db = sqlite3.connect(str(Path(xraydb.__file__).with_name('xraydb.sqlite')))
    table = {}
    for z, ion, offset, scale, exponents in db.execute(
            'select atomic_number, ion, offset, scale, exponents from Waasmaier order by id'):
        table[ion] = [z, offset, json.loads(scale), json.loads(exponents)]
    return table


def main():
    OUT.mkdir(exist_ok=True)
    head = {'source': 'spglib ' + spglib.__version__ + ' (BSD-3-Clause), tools/make_crystal_tables.py'}
    (OUT / 'space_groups.json').write_text(
        json.dumps({**head, 'groups': space_groups()}, ensure_ascii=False, separators=(',', ':')) + '\n', encoding='utf-8')
    head = {'source': 'Waasmaier & Kirfel, Acta Cryst. A51, 416 (1995), from xraydb ' + xraydb.__version__
            + ' (MIT), tools/make_crystal_tables.py', 'form': 'f0(s) = c + sum a_i exp(-b_i s^2), s = sin(theta)/lambda',
            'columns': ['Z', 'c', 'a1..a5', 'b1..b5']}
    (OUT / 'xray_f0.json').write_text(json.dumps({**head, 'ions': f0_table()}, separators=(',', ':')) + '\n', encoding='utf-8')


if __name__ == '__main__':
    main()

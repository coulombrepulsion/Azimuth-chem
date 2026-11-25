"""Internal coordinates (Z-matrix) of the Compass structure.

build(molecule) writes every atom through three earlier atoms: a bonded earlier atom for the
distance (the nearest earlier atom if none is bonded), then for the angle and the dihedral
earlier atoms bonded to those (or the nearest), never three on one line (an angle of 0–5° or
175–180° would leave the dihedral undefined). The order of the atoms is kept. to_cartesian()
builds coordinates back (natural extension reference frame): first atom at the origin, second on
+z, third in the xz plane — the usual convention of Gaussian and ORCA. text() gives the block of
both programs (Gaussian: after the charge/multiplicity line; ORCA: between `* gzmt q m` and `*`).
parse() reads such a block, with or without a list of variables (r1=0.96 or r1 0.96).
"""

import re
from math import acos, atan2, cos, degrees, dist, radians, sin, sqrt

from azimuth.core import Atom, Molecule
from azimuth.i18n import tr

NUMBER = r'[+-]?(?:\d+\.?\d*|\.\d+)(?:[EeDd][+-]?\d+)?'


def _sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    n = sqrt(_dot(a, a))
    return tuple(x / n for x in a)


def angle(a, b, c):
    u, v = _sub(a, b), _sub(c, b)
    return degrees(acos(max(-1.0, min(1.0, _dot(u, v) / sqrt(_dot(u, u) * _dot(v, v))))))


def dihedral(a, b, c, d):
    b0, b1, b2 = _sub(a, b), _sub(c, b), _sub(d, c)
    b1 = _unit(b1)
    v = _sub(b0, tuple(x * _dot(b0, b1) for x in b1))
    w = _sub(b2, tuple(x * _dot(b2, b1) for x in b1))
    return degrees(atan2(_dot(_cross(b1, v), w), _dot(v, w)))


def build(molecule, bonds=None):
    """Rows (symbol, a, r, b, angle, c, dihedral); references are 0-based indices or None."""
    from modules.compass.chemistry.builder import connections

    atoms = molecule.atoms
    p = [a.position for a in atoms]
    links = connections(molecule) if bonds is None else bonds
    neighbours = [set() for _ in atoms]
    for i, j, _ in links:
        neighbours[i].add(j)
        neighbours[j].add(i)

    def earlier(i, exclude, near, prefer):
        pool = [k for k in range(i) if k not in exclude]
        good = [k for k in pool if k in prefer]
        return sorted(good or pool, key=lambda k: dist(p[k], p[near]))

    rows = []
    for i, atom in enumerate(atoms):
        if i == 0:
            rows.append((atom.symbol, None, None, None, None, None, None))
            continue
        a = earlier(i, (), i, neighbours[i])[0]
        if i == 1:
            rows.append((atom.symbol, a, dist(p[i], p[a]), None, None, None, None))
            continue
        b = next((k for k in earlier(i, (a,), a, neighbours[a]) if 5 < angle(p[i], p[a], p[k]) < 175), None)
        b = earlier(i, (a,), a, neighbours[a])[0] if b is None else b
        if i == 2:
            rows.append((atom.symbol, a, dist(p[i], p[a]), b, angle(p[i], p[a], p[b]), None, None))
            continue
        c = next(
            (k for k in earlier(i, (a, b), b, neighbours[b] | neighbours[a]) if 5 < angle(p[a], p[b], p[k]) < 175), None
        )
        if c is None:
            c = earlier(i, (a, b), b, neighbours[b])[0]
        rows.append((atom.symbol, a, dist(p[i], p[a]), b, angle(p[i], p[a], p[b]), c, dihedral(p[i], p[a], p[b], p[c])))
    return rows


def to_cartesian(rows, title=''):
    p = []
    for k, (s, a, r, b, th, c, ph) in enumerate(rows):
        if k == 0:
            p.append((0.0, 0.0, 0.0))
        elif k == 1:
            p.append((0.0, 0.0, r))
        elif k == 2:
            A, B = p[a], p[b]
            u = _unit(_sub(B, A))
            perp = (1, 0, 0) if abs(u[0]) < 0.9 else (0, 1, 0)
            n = _unit(_cross(u, perp))
            m = _cross(n, u)
            t = radians(th)
            p.append(tuple(A[q] + r * (cos(t) * u[q] + sin(t) * m[q]) for q in range(3)))
        else:
            A, B, C = p[a], p[b], p[c]
            bc = _unit(_sub(A, B))
            n = _unit(_cross(_sub(B, C), bc))
            m = _cross(n, bc)
            t, f = radians(th), radians(ph)
            d2 = (-r * cos(t), r * sin(t) * cos(f), r * sin(t) * sin(f))
            p.append(tuple(A[q] + d2[0] * bc[q] + d2[1] * m[q] + d2[2] * n[q] for q in range(3)))
    return Molecule(title, tuple(Atom(s, *xyz) for (s, *_), xyz in zip(rows, p)), None)


def text(rows):
    out = []
    for s, a, r, b, th, c, ph in rows:
        line = f'{s:<3}'
        if a is not None:
            line += f' {a + 1:4d} {r:12.6f}'
        if b is not None:
            line += f' {b + 1:4d} {th:12.4f}'
        if c is not None:
            line += f' {c + 1:4d} {ph:12.4f}'
        out.append(line.rstrip())
    return '\n'.join(out) + '\n'


def parse(lines):
    """Rows from Z-matrix lines (1-based references; numbers or variable names); then variables."""
    lines = [l.split('!')[0].replace(',', ' ').strip() for l in lines]
    body, variables, k = [], {}, 0
    while k < len(lines) and lines[k] and not re.match(r'^(variables:|constants:)', lines[k], re.I):
        body.append(lines[k].split())
        k += 1
    for line in lines[k:]:
        m = re.match(r'^([A-Za-z]\w*)\s*[= ]\s*(' + NUMBER + ')', line)
        if m:
            variables[m.group(1)] = float(m.group(2).replace('D', 'E').replace('d', 'e'))

    def value(token):
        sign = -1 if token.startswith('-') else 1
        name = token.lstrip('+-')
        if re.fullmatch(NUMBER, token):
            return float(token.replace('D', 'E').replace('d', 'e'))
        if name in variables:
            return sign * variables[name]
        raise ValueError(tr(f'Z-матрица: не задана переменная {name}.'))

    rows = []
    for n, f in enumerate(body):
        symbol = re.sub(r'\d+$', '', f[0].split('(')[0]).capitalize()
        need = min(n, 3)
        if len(f) < 1 + 2 * need:
            raise ValueError(tr(f'Z-матрица: в строке {n + 1} мало чисел.'))
        refs = [int(f[1 + 2 * q]) - 1 for q in range(need)]
        vals = [value(f[2 + 2 * q]) for q in range(need)]
        if any(not 0 <= x < n for x in refs) or len(set(refs)) != len(refs):
            raise ValueError(tr(f'Z-матрица: в строке {n + 1} неверные номера атомов.'))
        row = [symbol, None, None, None, None, None, None]
        for q in range(need):
            row[1 + 2 * q], row[2 + 2 * q] = refs[q], vals[q]
        rows.append(tuple(row))
    if not rows:
        raise ValueError(tr('Z-матрица пуста.'))
    return rows

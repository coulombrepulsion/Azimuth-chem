"""Coordinate blocks and ordered geometric measurements. Internal lengths are Å."""

import re
from math import sqrt, acos, atan2, degrees, dist
from azimuth.i18n import tr

BOHR = 0.529177210544


def sub(a, b):
    return tuple(x - y for x, y in zip(a, b))


def dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def unit(a):
    length = sqrt(dot(a, a))
    if length < 1e-12:
        raise ValueError(tr('Угол не определён для совпадающих или коллинеарных точек'))
    return tuple(x / length for x in a)


def measurement(points):
    if len(points) == 2:
        return tr('Расстояние'), dist(*points)
    if len(points) == 3:
        a, b, c = points
        u = unit(sub(a, b))
        v = unit(sub(c, b))
        return tr('Угол'), degrees(acos(max(-1, min(1, dot(u, v)))))
    if len(points) == 4:
        a, b, c, d = points
        axis = unit(sub(c, b))
        u = sub(a, b)
        v = sub(d, c)
        u = unit(tuple(x - dot(u, axis) * y for x, y in zip(u, axis)))
        v = unit(tuple(x - dot(v, axis) * y for x, y in zip(v, axis)))
        return tr('Двугранный угол'), degrees(atan2(dot(cross(axis, u), v), dot(u, v)))
    return '', None


def coordinate_text(mol, fmt, bohr=False, charge=0, multiplicity=1):
    factor = BOHR if bohr else 1
    rows = '\n'.join(f'{a.symbol:<3} ' + ' '.join(f'{x / factor: .10f}' for x in a.position) for a in mol.atoms)
    if fmt == 'XYZ':
        if bohr:
            raise ValueError(tr('Стандартный XYZ экспортируется в ангстремах'))
        return f'{len(mol.atoms)}\n{mol.title}\n{rows}\n'
    if fmt == 'ORCA':  # ORCA calls a dummy atom DA
        rows = '\n'.join(re.sub(r'^X  ', 'DA ', line) for line in rows.splitlines())
        return f'! {"Bohrs" if bohr else "Angs"}\n* xyz {charge} {multiplicity}\n{rows}\n*\n'
    if fmt == 'NWChem':
        return f'geometry units {"au" if bohr else "angstrom"}\n{rows}\nend\n'
    if fmt == 'Gaussian':
        return f'{charge} {multiplicity}\n{rows}\n\n'
    return rows + '\n'

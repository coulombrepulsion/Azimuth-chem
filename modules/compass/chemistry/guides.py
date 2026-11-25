"""Vectors and planes on the model, as «Operations with vectors and planes» of Chemcraft.

§1 PURPOSE
    Chemcraft draws vectors and planes made from selected atoms
    or typed coordinates, measures the angles between them and lets them be edited as text. Here: a vector between two
    atoms or two points, the normal of the mean plane of atoms, the mean plane itself drawn as a translucent sheet; the
    angles between any two of them; one line of text per object, read back after editing.
§2 ALGORITHM
    A guide is a dict: {'kind': 'vector', 'atoms': (i, j)} or {'kind': 'vector', 'points': ((x, y, z), (x, y, z))};
    {'kind': 'normal' | 'plane', 'atoms': (i, j, k, …)}. Atom-made guides follow the atoms when they move.
    The mean plane: the centre and the unit normal of structure_tools.plane (least squares, SVD). The sheet is the
    rectangle of the plane's own axes (the two directions of the largest spread) that covers the projections of its
    atoms with MARGIN Å to spare; the normal is drawn NORMAL_LENGTH Å long from the centre, on the side of +z of the
    model frame (the sign of a normal is a convention). Angles: vector–vector 0–180°; a normal is a line without a
    sense: with a vector or a normal 0–90°; plane–plane 0–90° (a plane has no side); a vector or a normal with a plane
    90° − the angle to the plane's normal (0–90°).
§4 SPECIFICATION
    KINDS; geometry(guide, molecule) -> {'kind', 'start', 'end'} for vector and normal, {'kind', 'corners', 'centre'}
    for plane; None if its atoms are not in the structure; direction(guide, molecule) -> unit vector;
    angle(a, b, molecule) -> degrees; text(guides) -> str; parse(text, count, symbols=None) -> [guide] (ValueError
    with the line); describe(guide, symbols) -> «вектор C1 → O2».
§7 TESTS
    tests/compass/test_guides.py; tests/test_gui.py::test_vectors_and_planes_on_the_model.
"""

from math import acos, degrees, sqrt

from azimuth.i18n import tr

KINDS = ('vector', 'normal', 'plane')
WORDS = {'vector': 'вектор', 'normal': 'нормаль', 'plane': 'плоскость'}
READ = {'вектор': 'vector', 'vector': 'vector', 'нормаль': 'normal', 'normal': 'normal', 'плоскость': 'plane',
        'plane': 'plane'}
MARGIN = 0.8  # Å around the atoms of a plane (the default of the setting guide_plane_margin)
NORMAL_LENGTH = 1.5  # Å (the default of guide_normal_length)


def _setting(key, fallback):
    """«Стиль векторов и плоскостей…» (azimuth.defaults) — the program's value, else the fallback."""
    try:
        from azimuth import defaults

        return float(defaults.get(key))
    except Exception:  # noqa: BLE001 — without the settings of the program: the constants
        return fallback


def _sub(a, b):
    return tuple(a[k] - b[k] for k in range(3))


def _dot(a, b):
    return sum(a[k] * b[k] for k in range(3))


def _unit(v):
    n = sqrt(_dot(v, v))
    if n < 1e-9:
        raise ValueError(tr('Начало и конец вектора совпадают.'))
    return tuple(c / n for c in v)


def _valid(guide, molecule):
    atoms = guide.get('atoms')
    return atoms is None or all(0 <= i < len(molecule.atoms) for i in atoms)


def _plane(guide, molecule):
    """(centre, unit normal, axis u, axis v, half sizes) of the mean plane of the guide's atoms."""
    import numpy as np

    xyz = np.array([molecule.atoms[i].position for i in guide['atoms']], float)
    if len(xyz) < 3:
        raise ValueError(tr('Для плоскости нужны хотя бы три атома.'))
    centre = xyz.mean(axis=0)
    _, values, vt = np.linalg.svd(xyz - centre)
    if values[1] < 1e-6:
        raise ValueError(tr('Атомы лежат на одной прямой — плоскость не определена.'))
    u, v, normal = vt[0], vt[1], vt[2]
    if normal[2] < -1e-9 or (abs(normal[2]) <= 1e-9 and (normal[1] < 0 or (normal[1] == 0 and normal[0] < 0))):
        normal, v = -normal, -v  # the +z side; the frame stays right-handed
    margin = _setting('guide_plane_margin', MARGIN)
    a = float(np.abs((xyz - centre) @ u).max()) + margin
    b = float(np.abs((xyz - centre) @ v).max()) + margin
    as_tuple = lambda w: tuple(map(float, w))  # noqa: E731
    return as_tuple(centre), as_tuple(normal), as_tuple(u), as_tuple(v), (a, b)


def geometry(guide, molecule):
    if not _valid(guide, molecule):
        return None
    kind = guide['kind']
    if kind == 'vector':
        if 'points' in guide:
            start, end = guide['points']
        else:
            i, j = guide['atoms']
            start, end = molecule.atoms[i].position, molecule.atoms[j].position
        return {'kind': kind, 'start': tuple(start), 'end': tuple(end)}
    centre, normal, u, v, (a, b) = _plane(guide, molecule)
    if kind == 'normal':
        length = _setting('guide_normal_length', NORMAL_LENGTH)
        return {'kind': kind, 'start': centre, 'end': tuple(centre[k] + length * normal[k] for k in range(3))}
    corners = tuple(tuple(centre[k] + s * a * u[k] + t * b * v[k] for k in range(3))
                    for s, t in ((-1, -1), (1, -1), (1, 1), (-1, 1)))
    return {'kind': kind, 'corners': corners, 'centre': centre}


def direction(guide, molecule):
    if guide['kind'] == 'vector':
        g = geometry(guide, molecule)
        return _unit(_sub(g['end'], g['start']))
    return _plane(guide, molecule)[1]


def angle(a, b, molecule):
    """The angle between two guides, degrees (§2)."""
    da, db = direction(a, molecule), direction(b, molecule)
    cosine = max(-1.0, min(1.0, _dot(da, db)))
    if a['kind'] == b['kind'] == 'vector':
        return degrees(acos(cosine))  # two vectors keep their sense
    planes = (a['kind'] == 'plane') + (b['kind'] == 'plane')
    between = degrees(acos(abs(cosine)))  # of the two directions as lines
    return 90.0 - between if planes == 1 else between  # a line and a plane: 90° − the angle to its normal


def describe(guide, symbols):
    name = lambda i: f'{symbols[i]}{i + 1}' if 0 <= i < len(symbols) else str(i + 1)  # noqa: E731
    if guide['kind'] == 'vector':
        if 'points' in guide:
            s, e = guide['points']
            return tr('вектор') + ' (' + ', '.join(f'{c:g}' for c in s) + ') → (' + ', '.join(f'{c:g}' for c in e) + ')'
        return tr('вектор') + f' {name(guide["atoms"][0])} → {name(guide["atoms"][1])}'
    from modules.compass.chemistry.structure_tools import numbers_text

    return tr(WORDS[guide['kind']]) + ' ' + numbers_text(sorted(guide['atoms']), symbols)


def text(guides, lang=None):
    """One line a guide: «вектор 1 2», «вектор 0 0 0 1.5 0 0», «нормаль 1-6», «плоскость 1-6» (numbers from 1); in
    English (vector, normal, plane) when the program is not in Russian — parse reads both."""
    from azimuth import i18n
    from modules.compass.chemistry.structure_tools import numbers_text

    words = WORDS if (lang or i18n.LANG) == 'ru' else {k: k for k in WORDS}
    lines = []
    for g in guides:
        if g['kind'] == 'vector' and 'points' in g:
            lines.append(words['vector'] + ' ' + ' '.join(f'{c:.4f}'.rstrip('0').rstrip('.') for p in g['points']
                                                          for c in p))
        elif g['kind'] == 'vector':
            lines.append(f'{words["vector"]} {g["atoms"][0] + 1} {g["atoms"][1] + 1}')
        else:
            lines.append(words[g['kind']] + ' ' + numbers_text(sorted(g['atoms'])).replace('–', '-'))
    return '\n'.join(lines)


def parse(source, count, symbols=None):
    """The guides of the text of text() (also in English: vector, normal, plane; «#» starts a comment)."""
    from azimuth import atom_labels

    guides = []
    for number, line in enumerate(source.splitlines(), start=1):
        line = line.split('#')[0].strip()
        if not line:
            continue
        word, _, rest = line.partition(' ')
        kind = READ.get(word.lower())
        if kind is None:
            raise ValueError(tr('Строка ') + str(number) + tr(': нужно «вектор», «нормаль» или «плоскость».'))
        numbers = rest.replace(',', ' ').replace(';', ' ').split()
        if kind == 'vector' and len(numbers) == 6:
            try:
                values = [float(n) for n in numbers]
            except ValueError:
                values = None
            if values is not None:
                guide = {'kind': 'vector', 'points': (tuple(values[:3]), tuple(values[3:]))}
                _unit(_sub(guide['points'][1], guide['points'][0]))
                guides.append(guide)
                continue
        try:
            if kind == 'vector':  # the order matters: from the first atom to the second
                atoms = [n - 1 for token in numbers for n in atom_labels.parse(token, count, symbols)]
            else:
                atoms = [n - 1 for n in atom_labels.parse(rest, count, symbols)]
        except ValueError as exc:
            raise ValueError(tr('Строка ') + str(number) + ': ' + str(exc)) from exc
        if kind == 'vector':
            if len(atoms) != 2 or atoms[0] == atoms[1]:
                raise ValueError(tr('Строка ') + str(number) + tr(': вектору нужны два разных атома или шесть '
                                                                  'координат (начало и конец, Å).'))
            guides.append({'kind': 'vector', 'atoms': (atoms[0], atoms[1])})
        else:
            if len(set(atoms)) < 3:
                raise ValueError(tr('Строка ') + str(number) + tr(': плоскости и нормали нужны три атома или больше.'))
            guides.append({'kind': kind, 'atoms': tuple(dict.fromkeys(atoms))})
    return guides

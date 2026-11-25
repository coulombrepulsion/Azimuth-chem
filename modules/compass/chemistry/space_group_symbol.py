"""What the Hermann–Mauguin symbol of a space group says, part by part, and the Bravais lattice.

§1 THEORY
    International Tables for Crystallography A (2016), §1.4.1 and Table 2.1.3.1. The symbol is the letter of the
    lattice centring and up to three positions; each position is a symmetry direction of the crystal system, and in
    it stands the axis along that direction and/or (after «/») the plane perpendicular to it:
        triclinic — one position, no direction (1 or −1);
        monoclinic — b (unique axis b; the short symbol P2₁/c names only it, the full P 1 2₁/c 1 — a, b, c);
        orthorhombic — a, b, c;
        tetragonal — [001], ⟨100⟩, ⟨110⟩; trigonal and hexagonal — [001], ⟨100⟩, ⟨1−10⟩ (hexagonal axes);
        cubic — ⟨100⟩, ⟨111⟩, ⟨110⟩.
    Axes: n — a rotation by 360°/n; n_m — a screw: the rotation and a shift by m/n of the period along the axis;
    −n — a rotoinversion. Planes: m — a mirror; a, b, c — a glide: the reflection and a shift by half the period
    along that axis; n — along half a face diagonal; d — a quarter («diamond»); e — two glides in one plane.
    Centring: P — nodes only at the corners; A, B, C — also at the centre of the face bc, ac or ab; I — at the
    centre of the cell; F — at the centres of all faces; R — the rhombohedral lattice in hexagonal axes, nodes
    (⅔, ⅓, ⅓) and (⅓, ⅔, ⅔). The 14 Bravais lattices: the system and the centring (aP, mP, mC, oP, oC, oI, oF, tP,
    tI, hP, hR, cP, cI, cF — the symbols of Pearson); an A or B monoclinic or orthorhombic cell is the C one in
    another setting.
§4 SPECIFICATION
    parse(symbol) -> (letter, [position …]) — 'P 1 21/n 1', 'P21/c', 'Fm-3m', 'P63/mmc', 'I41/amd', 'R-3c' …; a
        position as written with the subscripts as digits ('21/n', '-3', 'm').
    bravais(system, centring) -> (Pearson symbol, name) | None; system in Russian, as crystal_symmetry.SYSTEMS.
    explain(symbol, system) -> [str] — the lines: the lattice, then each position with its direction.
    lattice_nodes(centring, n=(1, 1, 1)) -> [(x, y, z) fractional] — the nodes of the block of n₁ × n₂ × n₃ cells.
§7 TESTS
    tests/compass/test_space_group_symbol.py.
"""

from fractions import Fraction
import re

from azimuth.i18n import tr

DIRECTIONS = {
    'триклинная': (None,),
    'моноклинная': ('a', 'b', 'c'),  # the full symbol; the short one — b alone
    'ромбическая': ('a', 'b', 'c'),
    'тетрагональная': ('[001]', '⟨100⟩', '⟨110⟩'),
    'тригональная': ('[001]', '⟨100⟩', '⟨1−10⟩'),
    'гексагональная': ('[001]', '⟨100⟩', '⟨1−10⟩'),
    'кубическая': ('⟨100⟩', '⟨111⟩', '⟨110⟩'),
}
CENTRING = {
    'P': 'примитивная: узлы решётки только в вершинах ячейки',
    'A': 'центрированы грани bc: ещё узел в центре этих граней, (0, ½, ½)',
    'B': 'центрированы грани ac: ещё узел в центре этих граней, (½, 0, ½)',
    'C': 'центрированы грани ab: ещё узел в центре этих граней, (½, ½, 0)',
    'I': 'объёмноцентрированная: ещё узел в центре ячейки, (½, ½, ½)',
    'F': 'гранецентрированная: ещё узлы в центрах всех граней',
    'R': 'ромбоэдрическая: в гексагональных осях ещё узлы (⅔, ⅓, ⅓) и (⅓, ⅔, ⅔)',
}
SHIFTS = {
    'P': (),
    'A': ((0, Fraction(1, 2), Fraction(1, 2)),),
    'B': ((Fraction(1, 2), 0, Fraction(1, 2)),),
    'C': ((Fraction(1, 2), Fraction(1, 2), 0),),
    'I': ((Fraction(1, 2),) * 3,),
    'F': ((0, Fraction(1, 2), Fraction(1, 2)), (Fraction(1, 2), 0, Fraction(1, 2)), (Fraction(1, 2), Fraction(1, 2), 0)),
    'R': ((Fraction(2, 3), Fraction(1, 3), Fraction(1, 3)), (Fraction(1, 3), Fraction(2, 3), Fraction(2, 3))),
}
PEARSON = {'триклинная': 'a', 'моноклинная': 'm', 'ромбическая': 'o', 'тетрагональная': 't', 'тригональная': 'h',
           'гексагональная': 'h', 'кубическая': 'c'}
LATTICE_NAMES = {
    'aP': 'триклинная примитивная', 'mP': 'моноклинная примитивная', 'mC': 'моноклинная базоцентрированная',
    'oP': 'ромбическая примитивная', 'oC': 'ромбическая базоцентрированная', 'oI': 'ромбическая объёмноцентрированная',
    'oF': 'ромбическая гранецентрированная', 'tP': 'тетрагональная примитивная',
    'tI': 'тетрагональная объёмноцентрированная', 'hP': 'гексагональная примитивная', 'hR': 'ромбоэдрическая',
    'cP': 'кубическая примитивная', 'cI': 'кубическая объёмноцентрированная', 'cF': 'кубическая гранецентрированная',
}
PLANES = {
    'm': 'зеркальная плоскость',
    'a': 'плоскость скольжения: отражение и сдвиг на ½ a',
    'b': 'плоскость скольжения: отражение и сдвиг на ½ b',
    'c': 'плоскость скольжения: отражение и сдвиг на ½ c',
    'n': 'плоскость скольжения n: отражение и сдвиг на половину диагонали грани',
    'd': 'плоскость скольжения d («алмазная»): отражение и сдвиг на четверть диагонали',
    'e': 'двойная плоскость скольжения e: два сдвига в одной плоскости',
}
_SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
_TOKEN = re.compile(r'(-?[1-6])([1-5](?![0-9]))?(?:/([mabcnde]))?|([mabcnde])')


def parse(symbol):
    text = (symbol or '').strip().replace('_', '').replace('−', '-')
    if not text or text[0].upper() not in CENTRING:
        raise ValueError(tr('Не понимаю символ группы: {}').format(symbol))
    letter, rest = text[0].upper(), text[1:].strip()
    parts = rest.split() if ' ' in rest else None
    positions = []
    for chunk in (parts if parts is not None else [rest]):
        at = 0
        while at < len(chunk):
            m = _TOKEN.match(chunk, at)
            if not m or m.end() == at:
                raise ValueError(tr('Не понимаю символ группы: {}').format(symbol))
            screw = m.group(2)
            axis = m.group(1)
            if screw and axis and (axis.startswith('-') or int(screw) >= int(axis)):
                raise ValueError(tr('Не понимаю символ группы: {}').format(symbol))
            positions.append(m.group(0))
            at = m.end()
    if not positions:
        raise ValueError(tr('Не понимаю символ группы: {}').format(symbol))
    return letter, positions


def bravais(system, centring):
    first = PEARSON.get(system)
    if first is None or centring not in CENTRING:
        return None
    if first in ('m', 'o') and centring in ('A', 'B', 'C'):
        letter = 'C'
    elif first == 'h' and centring == 'R':
        letter = 'R'
    else:
        letter = centring
    code = first + letter
    return (code, LATTICE_NAMES[code]) if code in LATTICE_NAMES else None


def _axis_text(axis, screw):
    if axis == '1':
        return tr('нет симметрии')
    if axis == '-1':
        return tr('центр инверсии')
    n = int(axis.lstrip('-'))
    if axis.startswith('-'):
        return tr('инверсионная ось −{}: поворот на {}° и инверсия').format(n, 360 // n)
    if screw:
        shift = Fraction(int(screw), n)
        return tr('винтовая ось {}: поворот на {}° и сдвиг на {}/{} периода вдоль оси').format(
            axis + str(screw).translate(_SUB), 360 // n, shift.numerator, shift.denominator)
    return tr('ось {}-го порядка: поворот на {}°').format(n, 360 // n)


def explain(symbol, system):
    letter, positions = parse(symbol)
    found = bravais(system, letter)
    lines = [tr('{} — решётка {}').format(letter, tr(CENTRING[letter]))]
    if found:
        lines.append(tr('Решётка Браве: {} ({})').format(tr(found[1]), found[0]))
    directions = DIRECTIONS.get(system, (None, None, None))
    short_monoclinic = system == 'моноклинная' and len(positions) == 1
    for k, position in enumerate(positions):
        m = _TOKEN.fullmatch(position)
        if not m:
            continue
        axis, screw, plane, alone = m.group(1), m.group(2), m.group(3), m.group(4)
        if short_monoclinic:
            where = 'b'
        else:
            where = directions[k] if k < len(directions) else None
        written = (axis or '') + (str(screw).translate(_SUB) if screw else '') + (f'/{plane}' if plane else '') + (alone or '')
        said = []
        if axis:
            said.append(_axis_text(axis, screw))
        for p in (plane, alone):
            if p:
                said.append(tr(PLANES[p]) + (tr(', перпендикулярная {}').format(where) if where else ''))
        head = written.replace('-', '−') + (tr(' вдоль {}').format(where) if where and axis else '')
        lines.append(f'{head}: ' + '; '.join(said))
    if short_monoclinic:
        lines.append(tr('Краткий символ моноклинной группы называет одно направление — единственную ось b; полный '
                        'символ называет все три (P2₁/c — это P 1 2₁/c 1).'))
    return lines


def lattice_nodes(centring, n=(1, 1, 1)):
    shifts = ((0, 0, 0),) + tuple(SHIFTS.get(centring, ()))
    out = set()
    for i in range(n[0] + 1):
        for j in range(n[1] + 1):
            for k in range(n[2] + 1):
                for s in shifts:
                    p = (i + s[0], j + s[1], k + s[2])
                    if all(0 <= p[q] <= n[q] for q in range(3)):
                        out.add(tuple(Fraction(x) for x in p))
    return sorted(tuple(float(x) for x in p) for p in out)

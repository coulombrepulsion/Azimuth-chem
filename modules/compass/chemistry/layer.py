"""A layer with vacuum (graphene, a slab): its vacuum axis, the series of vacuum, the Dirac cone of graphene.

§1 THEORY
    A two-dimensional crystal is computed in a three-dimensional cell with an empty gap — the vacuum — between the
    layer and its periodic images. Along the vacuum the bands have no dispersion, so one k-point is enough there, and
    the vacuum is raised until the energy stops changing (the images stop feeling each other).
    Graphene. In the tight-binding model of the π electrons with the hopping t between the nearest neighbours the
    two bands are E(k) = E_D ± t |f(k)|, f(k) = 1 + exp(i k·a₁) + exp(i k·a₂). They touch at the corner K of the
    Brillouin zone, where f = 0, and near it the spectrum is a cone E = E_D ± ħ v_F |k − K| with
    ħ v_F = (√3/2) a t, a — the lattice parameter (2.46 Å). A calculation gives the slope of the bands at K; the
    hopping that reproduces it is t = 2 ħ v_F / (√3 a). The cone is not exactly symmetric (the π* band is steeper
    than the π band, and the directions K–M and K–Γ differ away from K — trigonal warping), so the four slopes are
    given and their mean is taken.
§2 ALGORITHM
    vacuum_axis(crystal, least=LEAST): for each axis the atoms of the cell are sorted by their fraction along it; the
    largest gap between neighbours (the one through the edge of the cell too) times the spacing of the lattice
    planes of that axis is the vacuum; the axis with the largest vacuum ≥ least, or None. thickness(crystal, axis):
    the spacing of the planes minus the vacuum.
    with_vacuum(crystal, vacuum, axis): the same layer in a cell (group P 1) whose axis is as long as gives that
    vacuum; the atoms keep their Cartesian distances along the axis and the layer is put in the middle of the cell.
    For an axis perpendicular to the other two only (as a slab or a layer is built) — ValueError otherwise.
    sheets(crystal, axis, gap): the atoms sorted along the axis are cut into sheets where the next atom is `gap` Å
    or more above; monolayer(crystal, vacuum): the lowest sheet in a cell with that vacuum (MoS₂ of the bulk 2H cell —
    one S–Mo–S sandwich).
    vacuums(now): the values of the series, VACUUMS and the present one. vacuum_of_input(text of pw.in) -> Å | None.
    cone(energies, occupied, x, ticks, a, window=WINDOW): the point K of the path (the first tick «K»); the bands
    N_occ and N_occ + 1 there must be within TOUCH of each other; on each side of K (the points of the same run of
    the path nearer than window Å⁻¹) and for each of the two bands the slope of |E − E_K| against |k − K| by least
    squares through zero; ħv_F — the mean of the slopes found; v_F = ħv_F / ħ; t = 2 ħv_F / (√3 a).
    tight_binding(fractions, t, energy, cells): E_D ± t |Σ exp(2πi f·n)| at the points of the path given in fractions
    of the reciprocal vectors of the two-atom cell (k·a_j = 2π f_j); n — the cells of the three nearest neighbours
    (neighbour_cells(crystal): they depend on how the cell is drawn — γ = 120° or 60°).
§4 SPECIFICATION
    LEAST = 7 Å; SHEET_GAP = 2.4 Å; VACUUMS = (8, 10, 12, 15, 18, 20) Å; WINDOW = 0.12 Å⁻¹; TOUCH = 0.05 eV; HBAR = 6.582119569e-16 eV·s.
    Cone(index, energy eV, slopes {('π' | 'π*', 'left' | 'right'): eV·Å}, hv eV·Å, velocity m/s, hopping eV | None,
    left, right — the labels of the neighbouring ticks). cone(...) -> Cone | None. text(cone) -> the line for the
    summary (Russian, keys of tr). ValueError with a message for the user.
§7 TESTS
    tests/compass/test_layer.py — the real bands of graphene (pw.x 7.6, tests/data/qe/graphene_bands_pw76.out).
"""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt

from azimuth.i18n import tr

LEAST = 7.0
SHEET_GAP = 2.4  # Å: an empty stretch along c that parts the sheets of a layered crystal (MoS₂ 3.0, graphite 3.35)
VACUUMS = (8.0, 10.0, 12.0, 15.0, 18.0, 20.0)
WINDOW = 0.12
TOUCH = 0.05
HBAR = 6.582119569e-16  # eV·s


def _atoms(crystal):
    from modules.compass.chemistry import crystal as cr

    return [a for a in cr.unit_cell(crystal) if a[0] != 'X']


def _spacing(crystal, axis):
    """The distance between the lattice planes perpendicular to the reciprocal vector of the axis, Å."""
    import numpy as np

    rows = np.array(crystal.cell.vectors(), dtype=float)
    star = np.linalg.inv(rows).T
    return 1.0 / float(np.linalg.norm(star[axis]))


def _gap(crystal, axis):
    """(the largest empty gap along the axis in fractions, the fraction it starts at)."""
    values = sorted(a[1 + axis] % 1.0 for a in _atoms(crystal))
    if not values:
        return 1.0, 0.0
    best, start = 0.0, values[-1]
    for low, high in zip(values, values[1:] + [values[0] + 1.0]):
        if high - low > best:
            best, start = high - low, low
    return best, start


def vacuum_axis(crystal, least=LEAST):
    found = None
    for axis in range(3):
        vacuum = _gap(crystal, axis)[0] * _spacing(crystal, axis)
        if vacuum >= least and (found is None or vacuum > found[1]):
            found = (axis, vacuum)
    return found[0] if found else None


def vacuum(crystal, axis):
    return _gap(crystal, axis)[0] * _spacing(crystal, axis)


def thickness(crystal, axis):
    return _spacing(crystal, axis) - vacuum(crystal, axis)


def with_vacuum(crystal, wanted, axis=None):
    from dataclasses import replace

    from modules.compass.chemistry import crystal as cr

    axis = vacuum_axis(crystal, 0.0) if axis is None else axis
    cell = crystal.cell
    angles = [cell.alpha, cell.beta, cell.gamma]
    others = [angles[k] for k in range(3) if k != axis]  # the angles the axis takes part in (α is of b and c …)
    if any(abs(angle - 90.0) > 1e-6 for angle in others):
        raise ValueError(tr('Ряд по вакууму: ось вакуума должна быть перпендикулярна слою.'))
    if wanted <= 0:
        raise ValueError(tr('Ряд по вакууму: вакуум должен быть больше нуля.'))
    lengths = [cell.a, cell.b, cell.c]
    old = lengths[axis]
    share, start = _gap(crystal, axis)
    thick = old * (1.0 - share)
    new = thick + wanted
    first = (start + share) % 1.0  # the lowest atom of the layer
    sites = []
    for k, atom in enumerate(_atoms(crystal), 1):
        f = list(atom[1:4])
        height = ((f[axis] - first) % 1.0) * old  # Å above the lowest atom
        if height > thick + 1e-6:
            height -= old
        f[axis] = (0.5 * wanted + height) / new
        sites.append(cr.Site(f'{atom[0]}{k}', atom[0], *f))
    lengths[axis] = new
    return cr.Crystal(crystal.title, replace(cell, a=lengths[0], b=lengths[1], c=lengths[2]), tuple(sites),
                      (cr.operation('x, y, z'),), 'P 1')


def sheets(crystal, axis=2, gap=SHEET_GAP):
    """The atoms of the cell gathered into the sheets of a layered crystal: along the axis the atoms are sorted, and
    an empty stretch of `gap` Å or more (the one through the edge of the cell too) starts a new sheet. [[atoms]] from
    the lowest sheet; one sheet — the crystal is not layered along this axis."""
    step = _spacing(crystal, axis)
    atoms = sorted(_atoms(crystal), key=lambda a: a[1 + axis] % 1.0)
    if not atoms:
        return []
    groups = [[atoms[0]]]
    for before, atom in zip(atoms, atoms[1:]):
        if ((atom[1 + axis] % 1.0) - (before[1 + axis] % 1.0)) * step >= gap:
            groups.append([])
        groups[-1].append(atom)
    around = ((atoms[0][1 + axis] % 1.0) + 1.0 - (atoms[-1][1 + axis] % 1.0)) * step
    if len(groups) > 1 and around < gap:  # the first and the last are one sheet through the edge of the cell
        groups[0] = groups.pop() + groups[0]
    return groups


def monolayer(crystal, wanted=15.0, axis=2, gap=SHEET_GAP):
    """One sheet of a layered crystal (MoS₂, graphite, h-BN) in a cell with `wanted` Å of vacuum (group P 1): the
    in-plane cell as it is, the sheet in the middle. ValueError when the crystal has no separate sheets along the
    axis or the axis is not perpendicular to them."""
    from dataclasses import replace

    from modules.compass.chemistry import crystal as cr

    cell = crystal.cell
    angles = [cell.alpha, cell.beta, cell.gamma]
    if any(abs(angles[k] - 90.0) > 1e-6 for k in range(3) if k != axis):
        raise ValueError(tr('Монослой: ось c должна быть перпендикулярна слоям.'))
    found = sheets(crystal, axis, gap)
    if len(found) < 2:
        raise ValueError(tr('Монослой: в ячейке нет отдельных слоёв — между атомами вдоль оси c нет промежутка от {:g} Å.')
                         .format(gap))
    lengths = [cell.a, cell.b, cell.c]
    old = lengths[axis]
    sheet = found[0]
    first = sheet[0][1 + axis] % 1.0
    heights = [(((a[1 + axis] % 1.0) - first) % 1.0) * old for a in sheet]
    thick = max(heights)
    new = thick + wanted
    sites = []
    for k, (atom, height) in enumerate(zip(sheet, heights), 1):
        f = list(atom[1:4])
        f[axis] = (0.5 * wanted + height) / new
        sites.append(cr.Site(f'{atom[0]}{k}', atom[0], *f))
    lengths[axis] = new
    return cr.Crystal(crystal.title, replace(cell, a=lengths[0], b=lengths[1], c=lengths[2]), tuple(sites),
                      (cr.operation('x, y, z'),), 'P 1')


def vacuum_of_input(text):
    """The vacuum (Å) of an input of pw.x written here (CELL_PARAMETERS angstrom, ATOMIC_POSITIONS crystal): the
    largest of the three axes; None when the cards are not found."""
    import numpy as np

    try:
        rows = np.array([[float(v) for v in line.split()[:3]]
                         for line in text.split('CELL_PARAMETERS')[1].splitlines()[1:4]])
        lines = text.split('ATOMIC_POSITIONS')[1].splitlines()[1:]
        atoms = []
        for line in lines:
            parts = line.split()
            if len(parts) < 4:
                break
            try:
                atoms.append([float(v) for v in parts[1:4]])
            except ValueError:
                break
        star = np.linalg.inv(rows).T
    except (IndexError, ValueError, np.linalg.LinAlgError):
        return None
    if not atoms:
        return None
    best = 0.0
    for axis in range(3):
        values = sorted(a[axis] % 1.0 for a in atoms)
        gap = max(high - low for low, high in zip(values, values[1:] + [values[0] + 1.0]))
        best = max(best, gap / float(np.linalg.norm(star[axis])))
    return best


def vacuums(now=None):
    values = set(VACUUMS)
    if now is not None and min(abs(now - v) for v in VACUUMS) > 0.25:
        values.add(round(float(now), 2))
    return sorted(values)


@dataclass(frozen=True)
class Cone:
    index: int
    energy: float
    slopes: dict
    hv: float
    velocity: float
    hopping: float | None
    left: str = ''
    right: str = ''


def cone(energies, occupied, x, ticks, a=None, window=WINDOW):
    if not energies or not occupied or len(energies[0]) <= occupied:
        return None
    at = next((k for k, (_, label) in enumerate(ticks) if label == 'K'), None)
    if at is None:
        return None
    position = ticks[at][0]
    index = next((k for k, value in enumerate(x) if abs(value - position) < 1e-9), None)
    if index is None:
        return None
    lower, upper = energies[index][occupied - 1], energies[index][occupied]
    if abs(upper - lower) > TOUCH:
        return None
    centre = 0.5 * (lower + upper)
    slopes = {}
    for side, step in (('left', -1), ('right', 1)):
        points = []
        k = index + step
        while 0 <= k < len(x) and 1e-9 < abs(x[k] - position) <= window:
            points.append(k)
            k += step
        if len(points) < 2:
            continue
        for name, band in (('π', occupied - 1), ('π*', occupied)):
            dk = [abs(x[k] - position) for k in points]
            de = [abs(energies[k][band] - centre) for k in points]
            slopes[(name, side)] = sum(u * v for u, v in zip(dk, de)) / sum(u * u for u in dk)
    if not slopes:
        return None
    hv = sum(slopes.values()) / len(slopes)
    labels = [label for _, label in ticks]
    return Cone(index, centre, slopes, hv, hv * 1e-10 / HBAR, 2 * hv / (sqrt(3) * a) if a else None,
                labels[at - 1] if at else '', labels[at + 1] if at + 1 < len(labels) else '')


def neighbour_cells(crystal):
    """The cells (n₁, n₂, n₃) in which the three nearest neighbours of the first atom of a two-atom honeycomb cell
    lie (copies of its second atom); ValueError when the cell is not such a one."""
    import numpy as np

    atoms = _atoms(crystal)
    if len(atoms) != 2:
        raise ValueError(tr('Модель сильной связи графена: в ячейке должно быть два атома.'))
    rows = np.array(crystal.cell.vectors(), dtype=float)
    first, second = (np.array(a[1:4], dtype=float) for a in atoms)
    found = []
    for n1 in (-1, 0, 1):
        for n2 in (-1, 0, 1):
            shift = np.array((n1, n2, 0), dtype=float)
            found.append((float(np.linalg.norm((second + shift - first) @ rows)), (n1, n2, 0)))
    found.sort()
    if abs(found[2][0] - found[0][0]) > 0.05 or found[3][0] - found[2][0] < 0.3:
        raise ValueError(tr('Модель сильной связи графена: у атома должно быть три равноудалённых соседа.'))
    return [cell for _, cell in found[:3]]


def tight_binding(fractions, t, energy=0.0, cells=((0, 0, 0), (1, 0, 0), (0, 1, 0))):
    """[(E_D − t|f|, E_D + t|f|)] at the points of the path given in fractions of the reciprocal vectors of the cell
    (k·a_j = 2π f_j); f = Σ exp(2πi f·n) over the cells n of the three neighbours (neighbour_cells)."""
    from cmath import exp
    from math import pi

    found = []
    for f in fractions:
        size = abs(sum(exp(2j * pi * (f[0] * n[0] + f[1] * n[1] + f[2] * n[2])) for n in cells))
        found.append((energy - t * size, energy + t * size))
    return found


def text(found):
    if found is None:
        return ''
    line = tr('Конус Дирака в точке K: зоны π и π* касаются при {} эВ. Скорость Ферми v_F = {}·10⁶ м/с (ħv_F = {} эВ·Å, '
              'среднее наклонов зон у K).').format(f'{found.energy:.3f}', f'{found.velocity / 1e6:.3f}', f'{found.hv:.2f}')
    if found.hopping is not None:
        line += ' ' + tr('Интеграл перескока модели сильной связи t = 2ħv_F/(√3·a) = {} эВ.').format(f'{found.hopping:.2f}')
    line += ' ' + tr('PBE занижает v_F: в опыте около 1.0·10⁶ м/с.')
    return line

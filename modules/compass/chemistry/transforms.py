"""Rigid fragment edits; cycles are rejected when cutting a bond cannot isolate a side."""

from dataclasses import replace
from math import sin, cos, dist
from azimuth.core import Atom
from modules.compass.chemistry.builder import connections, checked
from modules.compass.chemistry.geometry_tools import unit, dot, cross, sub
from azimuth.i18n import tr


def bond_side(molecule, a, b):
    edges = connections(molecule)
    if not any({i, j} == {a, b} for i, j, _ in edges):
        raise ValueError(tr('Выберите два связанных атома: первый неподвижный, второй со стороны фрагмента.'))
    graph = {i: set() for i in range(len(molecule.atoms))}
    for i, j, _ in edges:
        if {i, j} != {a, b}:
            graph[i].add(j)
            graph[j].add(i)
    seen = {b}
    todo = [b]
    while todo:
        i = todo.pop()
        for j in graph[i] - seen:
            seen.add(j)
            todo.append(j)
    if a in seen:
        raise ValueError(tr('Связь входит в цикл: невозможно отделить фрагмент без деформации кольца.'))
    return sorted(seen)



def angle_fragment(molecule, pressed):
    """The fragment a press on an atom turns about its pivot — of the bonds of
    the pressed atom and of its neighbours, the one that cuts off, on the side of the pressed atom, the smallest piece
    of two or more atoms with a heavy pivot (not a ring bond): a press on a methyl or on one of its hydrogens turns
    the methyl about the carbon it hangs on. (pivot, sorted indices of the fragment), or None — no such piece
    (water: a hydrogen turns alone, as before)."""
    edges = connections(molecule)
    near = {i: set() for i in range(len(molecule.atoms))}
    for i, j, _ in edges:
        near[i].add(j)
        near[j].add(i)
    best = None
    for b in [pressed] + sorted(near.get(pressed, ())):
        for a in sorted(near[b]):
            if molecule.atoms[a].symbol == 'H':
                continue
            try:
                side = bond_side(molecule, a, b)
            except ValueError:
                continue
            if pressed in side and 2 <= len(side) < len(molecule.atoms) - 1 and (best is None or len(side) < len(best[1])):
                best = (a, side)
    return best

def rotate_atoms(molecule, indices, pivot, axis, angle):
    if not indices:
        raise ValueError(tr('Сначала выберите атомы фрагмента.'))
    axis = unit(axis)
    selected = set(indices)
    atoms = []
    for i, a in enumerate(molecule.atoms):
        if i not in selected:
            atoms.append(a)
            continue
        v = sub(a.position, pivot)
        w = cross(axis, v)
        pos = tuple(
            pivot[k] + v[k] * cos(angle) + w[k] * sin(angle) + axis[k] * dot(axis, v) * (1 - cos(angle))
            for k in range(3)
        )
        atoms.append(Atom(a.symbol, *pos))
    return checked(replace(molecule, atoms=tuple(atoms), bonds=connections(molecule)))


def stretch_bond(molecule, a, b, delta):
    indices = set(bond_side(molecule, a, b))
    p = molecule.atoms[a].position
    q = molecule.atoms[b].position
    if dist(p, q) + delta < 0.2:
        raise ValueError(tr('Длина связи должна быть не меньше 0.2 Å.'))
    direction = unit(sub(q, p))
    atoms = tuple(
        Atom(atom.symbol, *(atom.position[k] + direction[k] * delta for k in range(3))) if i in indices else atom
        for i, atom in enumerate(molecule.atoms)
    )
    return checked(replace(molecule, atoms=atoms, bonds=connections(molecule)))


def set_measurement(molecule, indices, target, move_fragment=True):
    """Change an ordered distance/angle/dihedral, keeping earlier reference atoms fixed. An angle with move_fragment —
    both sides turn about the
    middle atom, each by half of the change (each with its fragment), as in Chemcraft; the middle atom stays. A first
    atom whose side cannot be cut off (not bonded to the middle one, a ring) stays, and the last side turns the whole
    change, as before."""
    from math import isfinite, radians
    from modules.compass.chemistry.geometry_tools import measurement

    if len(indices) not in (2, 3, 4) or len(set(indices)) != len(indices):
        raise ValueError(tr('Выберите последовательно 2, 3 или 4 разных атома.'))
    if any(i < 0 or i >= len(molecule.atoms) for i in indices):
        raise ValueError(tr('Выделение устарело. Выберите атомы заново.'))
    if not isfinite(target):
        raise ValueError(tr('Введите конечное числовое значение.'))
    count = len(indices)
    points = [molecule.atoms[i].position for i in indices]
    if count == 2 and target < 0.2:
        raise ValueError(tr('Расстояние должно быть не меньше 0.2 Å.'))
    if count == 3 and not 0 <= target <= 180:
        raise ValueError(tr('Угол должен быть от 0 до 180°.'))
    if count == 4 and not -180 <= target <= 180:
        raise ValueError(tr('Двугранный угол должен быть от −180 до 180°.'))
    current = measurement(points)[1]
    group = [indices[-1]]
    if move_fragment:
        cut = (indices[0], indices[1]) if count == 2 else (indices[1], indices[2])
        group = bond_side(molecule, *cut)
        if indices[-1] not in group:
            raise ValueError(tr('Последний атом должен находиться со стороны перемещаемого фрагмента.'))
        fixed = indices[:-1] if count != 4 else indices[:2]
        if any(i in group for i in fixed):
            raise ValueError(tr('Фрагмент включает опорный атом. Выберите режим перемещения последнего атома.'))
    molecule = replace(molecule, bonds=connections(molecule))
    if count == 2:
        direction = unit(sub(points[1], points[0]))
        delta = target - current
        atoms = tuple(
            Atom(a.symbol, *(a.position[k] + direction[k] * delta for k in range(3))) if i in group else a
            for i, a in enumerate(molecule.atoms)
        )
        result = checked(replace(molecule, atoms=atoms))
    elif count == 3:
        u = sub(points[0], points[1])
        v = sub(points[2], points[1])
        axis = cross(u, v)
        if dot(axis, axis) < 1e-16:
            direction = unit(u)
            helper = min([(1, 0, 0), (0, 1, 0), (0, 0, 1)], key=lambda x: abs(dot(direction, x)))
            axis = cross(direction, helper)
        first = []
        if move_fragment:
            try:
                first = bond_side(molecule, indices[1], indices[0])
            except ValueError:
                first = []
            if set(first) & set(group) or indices[1] in first:
                first = []
        if first:
            half = radians(target - current) / 2
            result = rotate_atoms(rotate_atoms(molecule, group, points[1], axis, half), first, points[1], axis, -half)
        else:
            result = rotate_atoms(molecule, group, points[1], axis, radians(target - current))
    else:
        axis = sub(points[2], points[1])
        delta = (target - current + 180) % 360 - 180
        result = rotate_atoms(molecule, group, points[2], axis, radians(delta))
    actual = measurement([result.atoms[i].position for i in indices])[1]
    error = (actual - target + 180) % 360 - 180 if count == 4 else actual - target
    if abs(error) > 1e-5:
        raise ValueError(tr('Не удалось задать геометрию для этого выделения.'))
    return result

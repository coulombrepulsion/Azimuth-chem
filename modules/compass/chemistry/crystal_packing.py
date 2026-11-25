"""The packing of a crystal: a block by ranges of the coordinates, the molecules coloured by symmetry.

§1 THEORY
    A block of the crystal is often wanted not as whole cells but as a region: −0.5 ≤ x ≤ 1.5 along a, one layer
    0.2 ≤ z ≤ 0.8 … (Mercury: «Packing → Range»). The molecules of a cell are copies of those of the asymmetric unit
    by the operations of the group; copies by one operation differ only by lattice translations — the same
    orientation. Colouring the molecules by the operation that makes them shows the motifs of the packing: the
    herring-bone of a 2₁ axis, the layers of a glide plane.
§2 ALGORITHM build_range(crystal, lo, hi, whole): the atoms of the cell (crystal.unit_cell) moved by every lattice
    vector that reaches the range, kept with lo − EDGE ≤ f ≤ hi + EDGE for every axis; with whole — the molecules of
    crystal_symmetry.molecules (unwrapped, centroid in the cell) moved likewise and kept when their centroid is in the
    range, the infinite parts by their atoms. classes(crystal, molecule): each atom of the model (Cartesian, the cell at
    the origin) to the first operation k and site whose copy op_k(site) is the atom (mod the lattice, within
    crystal.MERGE, the same element) — k of the first operation with the same rotation part, so the copies by a centring
    vector (C, I, F) are one class; each fragment of the model (its bonds, builder.connections) gets the smallest k of
    its atoms — a molecule on a special position, made of halves by two operations, keeps one colour. colours(…) ->
    {atom index: colour} with PALETTE[k mod 10].
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py: «Диапазон координат» of the «Кристалл» window, «Окраска по симметрии»
    of the menu «Вид кристалла».
§4 SPECIFICATION
    build_range(crystal, lo, hi, whole=False, factor=None) -> Molecule; classes(crystal, molecule) -> [int | None];
    colours(crystal, molecule) -> {index: '#rrggbb'}; legend(crystal, molecule) -> [(colour, operation text, count)].
§5 PROCEDURES - below.
§6 NOTES
    EDGE = 1e-4: an atom exactly on a bound of the range (0 and 1 of a cell) is in it. The palette — Tableau 10 (the
    categorical colours of Tableau, widely used for plots); groups with more than 10 operations repeat colours.
§7 TESTS
    tests/compass/test_crystal_packing.py.
§8' ROBUSTNESS / ERRORS
    ValueError for a range with lo > hi or wider than 10 cells on an axis, and beyond MAX_ATOMS atoms.
"""

from math import ceil, floor

from azimuth.i18n import tr

EDGE = 1e-4
PALETTE = ('#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac')


def _translations(lo, hi):
    ranges = [range(floor(lo[k]) - 1, ceil(hi[k]) + 1) for k in range(3)]
    return [(i, j, k) for i in ranges[0] for j in ranges[1] for k in ranges[2]]


def _inside(f, lo, hi):
    return all(lo[k] - EDGE <= f[k] <= hi[k] + EDGE for k in range(3))


def build_range(crystal, lo, hi, whole=False, factor=None):
    from azimuth.core import MAX_ATOMS, Atom, Molecule
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_symmetry as cs

    lo, hi = tuple(float(x) for x in lo), tuple(float(x) for x in hi)
    if any(lo[k] > hi[k] or hi[k] - lo[k] > 10 for k in range(3)):
        raise ValueError(tr('Диапазон координат: от не больше до, не шире 10 ячеек по каждой оси.'))
    shifts = _translations(lo, hi)
    picked = []
    if whole:
        packing = cs.molecules(crystal, factor)
        for part in packing.molecules:
            centre = [sum(f[k] for _, f in part) / len(part) for k in range(3)]
            for t in shifts:
                if _inside([centre[k] + t[k] for k in range(3)], lo, hi):
                    picked += [(symbol, [f[k] + t[k] for k in range(3)]) for symbol, f in part]
        loose = [atom for _, part in packing.frameworks for atom in part]
    else:
        loose = [(a[0], a[1:4]) for a in cr.unit_cell(crystal)]
    for symbol, f in loose:
        for t in shifts:
            g = [f[k] + t[k] for k in range(3)]
            if _inside(g, lo, hi):
                picked.append((symbol, g))
    if len(picked) > MAX_ATOMS:
        raise ValueError(tr('Получится {} атомов — больше {}. Уменьшите число ячеек.').format(len(picked), MAX_ATOMS))
    atoms = tuple(Atom(symbol, *crystal.cell.cartesian(g)) for symbol, g in picked)
    span = ' '.join(f'{lo[k]:g}…{hi[k]:g}' for k in range(3))
    return Molecule(f'{crystal.title or "crystal"} {span}', atoms, None)


def classes(crystal, molecule):
    import numpy as np

    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry.builder import connections

    rows = np.array(crystal.cell.vectors(), dtype=float)
    inverse = np.linalg.inv(rows)
    copies = []  # (operation index, symbol, fractional in [0, 1))
    first = {}  # the rotation part -> the first operation with it: copies by a centring vector are one class
    for k, op in enumerate(crystal.operations):
        cls = first.setdefault(op[0], k)
        for site in crystal.sites:
            copies.append((cls, site.symbol, np.array(cr._wrap(cr._apply(op, (site.x, site.y, site.z))))))
    found = []
    for atom in molecule.atoms:
        f = np.array(atom.position, dtype=float) @ inverse
        f -= np.floor(f)
        best = None
        for k, symbol, g in copies:
            if symbol != atom.symbol:
                continue
            d = f - g
            d -= np.round(d)
            if np.linalg.norm(d @ rows) <= cr.MERGE:
                best = k
                break
        found.append(best)
    n = len(molecule.atoms)
    neighbours = [[] for _ in range(n)]
    for i, j, _ in connections(molecule):
        neighbours[i].append(j)
        neighbours[j].append(i)
    seen = [False] * n
    for start in range(n):
        if seen[start]:
            continue
        part, stack = [], [start]
        seen[start] = True
        while stack:
            k = stack.pop()
            part.append(k)
            for m in neighbours[k]:
                if not seen[m]:
                    seen[m] = True
                    stack.append(m)
        known = [found[k] for k in part if found[k] is not None]
        if known:
            for k in part:
                found[k] = min(known)
    return found


def colours(crystal, molecule):
    return {i: PALETTE[k % len(PALETTE)] for i, k in enumerate(classes(crystal, molecule)) if k is not None}


def legend(crystal, molecule):
    from modules.compass.chemistry.surface import operation_text

    counts = {}
    for k in classes(crystal, molecule):
        if k is not None:
            counts[k] = counts.get(k, 0) + 1
    return [(PALETTE[k % len(PALETTE)], operation_text(crystal.operations[k]), counts[k]) for k in sorted(counts)]

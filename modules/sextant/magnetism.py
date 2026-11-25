"""The magnetic order of a crystal: ferro- or antiferromagnetic starting moments of its d and f atoms.

§1 THEORY
    A spin-polarized calculation converges to the order it starts from. NiO, MnO, FeO, CoO, Cr₂O₃, α-Fe₂O₃ … are
    antiferromagnets: half of the magnetic atoms spin up, half down. A code finds such a state only when the two halves
    are different species with starting moments of opposite sign (Quantum ESPRESSO: two labels of one element with
    starting_magnetization ±m; CP2K: two kinds with ELEMENT and MAGNETIZATION ±m), in a cell that holds both halves.
    The rock-salt oxides take the order AFM-II — ferromagnetic (111) planes stacked antiparallel: in the primitive fcc
    cell a lattice node R = n₁a₁ + n₂a₂ + n₃a₃ lies in the (111) plane n₁ + n₂ + n₃, so the supercell 2 × 1 × 1 of the
    primitive cell (or 2 × 2 × 2) with the sign (−1)^(n₁ + n₂ + n₃) is AFM-II.
§2 ALGORITHM
    afm_signs(crystal, supercell): the magnetic atoms (elements with a d or f shell, hubbard.MANIFOLDS) of the cell
    computed. A supercell with even repetitions along some axes: the sign of an atom (−1)^Σ ⌊nᵢ·xᵢ⌋ over those axes
    (xᵢ — its fraction in the supercell: ⌊nᵢ·xᵢ⌋ is the copy of the cell it is in). Else the cell itself: the
    magnetic atoms joined to their nearest magnetic neighbours (all periodic images; up to 5 % farther than the
    nearest) are coloured in two colours by a search through the graph; an odd ring (an atom with itself as a neighbour
    — one magnetic atom per cell — or a frustrated lattice like fcc) has no such colouring: ValueError advising the
    supercell 2 × 1 × 1. Every element must have both signs.
§4 SPECIFICATION
    ORDERS = {'fm': …, 'afm': …}; magnetic(symbols) -> [element]; usually_magnetic(symbols) -> [element] (the open-shell
    ions of USUALLY: V Cr Mn Fe Co Ni Cu, Ce–Yb, U Np Pu); afm_signs(crystal, supercell=(1, 1, 1)) -> tuple of +1/−1/0
    per atom of crystal.unit_cell (X left out); labels(atoms, signs) -> [label] (Ni1 — up, Ni2 — down).
§7 TESTS
    tests/sextant/test_magnetism.py.
"""

from math import floor

from azimuth.i18n import tr

ORDERS = {'fm': 'ферромагнитный', 'afm': 'антиферромагнитный'}
USUALLY = frozenset('V Cr Mn Fe Co Ni Cu Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb U Np Pu'.split())


def magnetic(symbols):
    from modules.sextant.hubbard import MANIFOLDS

    return [s for s in dict.fromkeys(symbols) if s in MANIFOLDS]


def usually_magnetic(symbols):
    return [s for s in dict.fromkeys(symbols) if s in USUALLY]


def afm_signs(crystal, supercell=(1, 1, 1)):
    import numpy as np

    from modules.compass.chemistry import crystal as cr

    atoms = [a for a in cr.unit_cell(crystal) if a[0] != 'X']
    found = set(magnetic(a[0] for a in atoms))
    if not found:
        raise ValueError(tr('Антиферромагнитный порядок: в ячейке нет атомов d- или f-элементов.'))
    index = [k for k, a in enumerate(atoms) if a[0] in found]
    signs = [0] * len(atoms)
    even = [i for i, n in enumerate(supercell) if int(n) % 2 == 0]
    if even:
        for k in index:
            copy = sum(floor(int(supercell[i]) * (atoms[k][1 + i] % 1.0) + 1e-6) for i in even)
            signs[k] = 1 if copy % 2 == 0 else -1
    else:
        frac = np.array([atoms[k][1:4] for k in index], float) % 1.0
        cell = np.array(crystal.cell.vectors(), float)
        shifts = np.array([(i, j, l) for i in (-1, 0, 1) for j in (-1, 0, 1) for l in (-1, 0, 1)], float)
        n = len(index)
        dist = np.full((n, n), np.inf)
        for p in range(n):
            delta = (frac[None, :, :] - frac[p][None, None, :] + shifts[:, None, :]) @ cell  # (27, n, 3)
            d = np.linalg.norm(delta, axis=2)
            d[d < 1e-6] = np.inf  # the atom itself, not its images
            dist[p] = d.min(axis=0)
        nearest = dist.min()
        joined = dist <= nearest * 1.05
        colour = [0] * n
        for start in range(n):
            if colour[start]:
                continue
            colour[start] = 1
            queue = [start]
            while queue:
                p = queue.pop()
                for q in np.nonzero(joined[p])[0]:
                    if q == p or colour[q] == colour[p]:
                        raise ValueError(tr('Антиферромагнитный порядок: в этой ячейке магнитные атомы нельзя разделить '
                                            'на две подрешётки — увеличьте суперячейку, например 2 × 1 × 1 (для NiO, '
                                            'MnO в примитивной ячейке это порядок AFM-II).'))
                    if not colour[q]:
                        colour[q] = -colour[p]
                        queue.append(q)
        for p, k in enumerate(index):
            signs[k] = colour[p]
    for element in found:
        seen = {signs[k] for k in index if atoms[k][0] == element}
        if seen != {1, -1}:
            raise ValueError(tr('Антиферромагнитный порядок: у {} в этой ячейке все моменты в одну сторону — '
                                'увеличьте суперячейку, например 2 × 1 × 1.').format(element))
    return tuple(signs)


def labels(atoms, signs):
    """Ni1 — spin up, Ni2 — spin down, the rest — the element."""
    out = []
    for a, s in zip(atoms, signs):
        out.append(a[0] + ('1' if s > 0 else '2') if s else a[0])
    return out

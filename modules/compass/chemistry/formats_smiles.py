"""A structure from SMILES (from_smiles): the graph made into coordinates, the hydrogens put in, the bonds written as
double kept so, the chalcogens turned.

Split off modules/compass/chemistry/formats.py (0.222.30); formats.from_smiles still names it.
"""

from azimuth.core import Atom, Molecule
from azimuth.i18n import tr
from modules.compass.chemistry.formats_common import kekule


# -- SMILES → 3D -----------------------------------------------------------------------------------
TRAPPED = 20.0  # energy of the tidying above which a hydrogen is likely caught in a ring (100 and more)


ROUGH = 1e-2  # the largest force (cleanup units) at which a start is tidied enough to be compared


def _hydrogen_inside(molecule, limit=1.7):
    """A hydrogen closer than limit Å to a heavy atom it is not bonded to (caught inside a ring)."""
    bonded = {(i, j) for i, j, _ in molecule.bonds} | {(j, i) for i, j, _ in molecule.bonds}
    atoms = molecule.atoms
    for h, a in enumerate(atoms):
        if a.symbol != 'H':
            continue
        for k, b in enumerate(atoms):
            if b.symbol != 'H' and (h, k) not in bonded:
                if sum((p - q) ** 2 for p, q in zip(a.position, b.position)) < limit * limit:
                    return True
    return False


def _replace_hydrogens(molecule):
    """Every hydrogen put again in the direction its heavy atom gives by its shape and its heavy
    neighbours (editing._directions); the order of the atoms and the bonds stay."""
    from modules.compass.chemistry.editing import _directions
    from modules.compass.chemistry.builder import bond_length, add, mul

    atoms = list(molecule.atoms)
    heavy_bonds = [b for b in molecule.bonds if atoms[b[0]].symbol != 'H' and atoms[b[1]].symbol != 'H']
    for i, a in enumerate(molecule.atoms):
        if a.symbol == 'H':
            continue
        hs = [j if k == i else k for k, j, _ in molecule.bonds if i in (k, j) and atoms[j if k == i else k].symbol == 'H']
        if not hs:
            continue
        orders = [o for k, j, o in molecule.bonds if i in (k, j)]
        current = Molecule('', tuple(atoms), tuple(heavy_bonds))
        dirs = _directions(current, i, heavy_bonds, len(hs), orders)
        if len(dirs) < len(hs):
            continue
        for h, d in zip(hs, dirs):
            atoms[h] = Atom('H', *add(a.position, mul(d, bond_length(a.symbol, 'H', 1))))
    return Molecule(molecule.title, tuple(atoms), molecule.bonds)


QUICK_STEPS = 400


def from_smiles(text, quick=False):
    """A 3D starting structure: atoms placed along a spanning tree by their shapes, then tidied. quick: one
    short tidying of the straightened start, no other starts — for a structure set right afterwards (peptide.py)."""
    from modules.compass.chemistry.names import smiles_graph
    from modules.compass.chemistry.editing import _directions
    from modules.compass.chemistry.cleanup import clean
    from modules.compass.chemistry.builder import bond_length, add, mul

    directed = []
    try:
        symbols, links, orders = smiles_graph(text.strip(), strict=True, directed=directed)
    except ValueError:
        raise ValueError(
            tr(
                'Не удалось разобрать SMILES. Поддерживаются органические атомы, ветви, циклы, ароматика и [атомы] в скобках.'
            )
        ) from None
    from azimuth.core import MAX_ATOMS

    if len(symbols) > (MAX_ATOMS if quick else 300):  # the full search is too slow above 300 atoms
        raise ValueError(tr('SMILES: слишком большая молекула для этой версии.'))
    n = len(symbols)
    neighbours = [[] for _ in range(n)]
    for (i, j), o in zip(links, orders):
        neighbours[i].append((j, o))
        neighbours[j].append((i, o))
    position = [None] * n
    placed_bonds = []
    components = 0
    for root in range(n):
        if position[root] is not None:
            continue
        position[root] = (components * 6.0, 0.0, 0.0)
        components += 1
        queue = [root]
        while queue:
            i = queue.pop(0)
            todo = [(j, o) for j, o in neighbours[i] if position[j] is None]
            if not todo:
                continue
            atoms = tuple(Atom(symbols[k], *(position[k] or (0, 0, 0))) for k in range(n))
            current = Molecule('', atoms, tuple(placed_bonds))
            shape = [o for _, o in neighbours[i]]
            dirs = _directions(current, i, placed_bonds, len(todo), shape)
            while len(dirs) < len(todo):
                dirs.append(dirs[-1] if dirs else (1, 0, 0))
            for (j, o), d in zip(todo, dirs):
                length = bond_length(symbols[i], symbols[j], int(o) if o in (1, 2, 3) else 2)
                position[j] = add(position[i], mul(d, length))
                placed_bonds.append((i, j, o))
                queue.append(j)
    atoms = tuple(Atom(s, *p) for s, p in zip(symbols, position))
    bonds = kekule(n, [(i, j, o) for (i, j), o in zip(links, orders)], symbols)
    from modules.compass.chemistry.cleanup import straighten

    start = straighten(Molecule('SMILES ' + text.strip(), atoms, bonds))  # chains as anti zigzags
    from modules.compass.chemistry.names import double_bond_stereo

    stereo = double_bond_stereo(links, orders, directed)  # «/» and «\\»: cis and trans as written
    start = _double_bonds_as_written(start, stereo)
    start = _skewed_chalcogen_bonds(start)  # H2O2, disulfides: not flat anti
    if quick:
        result = clean(start, steps=QUICK_STEPS, tolerance=ROUGH, method='lbfgs')[0]
        if _hydrogen_inside(result):  # a hydrogen placed while a ring was open (the N–H of indole): again by the ring
            result = clean(_replace_hydrogens(result), steps=QUICK_STEPS, tolerance=ROUGH, method='lbfgs')[0]
        return result
    best, best_e = None, None
    import random

    rnd = random.Random(7)  # deterministic: the same SMILES gives the same structure
    for attempt in range(6):
        trial = (
            start
            if attempt == 0
            else Molecule(
                start.title,
                tuple(Atom(a.symbol, *[c + rnd.uniform(-0.6, 0.6) for c in a.position]) for a in start.atoms),
                bonds,
            )
        )
        result, _, energy = clean(trial, steps=4000, tolerance=ROUGH, method='lbfgs')
        if energy >= TRAPPED or _hydrogen_inside(result):
            # a hydrogen placed while a ring was still open can end up inside the ring (naphthalene);
            # put the hydrogens again by the tidied heavy atoms and tidy once more. Only then — the
            # residual energy of an unstrained chain is 1–12, not below 0.05, so the second tidying ran every time
            again, _, e2 = clean(_replace_hydrogens(result), steps=4000, tolerance=ROUGH, method='lbfgs')
            if e2 < energy:
                result, energy = again, e2
        if best_e is None or energy < best_e:
            best, best_e = result, energy
        if best_e < 0.05:  # no strain left (a residue of fused rings is fine)
            break
    # the starts are compared tidied roughly (their energies differ by a rotamer, 1 and more), only the
    # lowest is tidied to the end
    best, _, best_e = clean(best, steps=4000, method='lbfgs')
    if stereo and _double_bonds_as_written(best, stereo) is not best:  # a start turned a double bond over
        best = clean(_double_bonds_as_written(best, stereo), steps=4000, method='lbfgs')[0]
    return best


SKEW = {'O': 112.0, 'S': 85.0, 'Se': 87.0}  # ° X–O–O–Y (H2O2 gas 111.8), X–S–S–Y (dimethyl disulfide 84.7)


def _skewed_chalcogen_bonds(molecule):
    """An O–O, S–S (Se–Se) single bond between two atoms of two neighbours, not in a ring: the side of one turned so
    that the dihedral X–A–A–Y is the measured one (SKEW) — the chains come straightened anti and flat (H2O2 C2h, a
    saddle xtb kept), and the force field has no torsion for such a bond, so the turn stays."""
    import numpy as np

    from modules.compass.chemistry.cleanup import dihedrals

    atoms = molecule.atoms
    neighbours = [[] for _ in atoms]
    for i, j, _ in molecule.bonds:
        neighbours[i].append(j)
        neighbours[j].append(i)
    x = np.array([a.position for a in atoms], dtype=float)
    turned = False
    for j, k, o in molecule.bonds:
        if o != 1 or atoms[j].symbol != atoms[k].symbol or atoms[j].symbol not in SKEW:
            continue
        if len(neighbours[j]) != 2 or len(neighbours[k]) != 2:
            continue
        a = next(n for n in neighbours[j] if n != k)
        d = next(n for n in neighbours[k] if n != j)
        side, todo = {k}, [k]
        while todo:
            n = todo.pop()
            for m in neighbours[n]:
                if m != j and m not in side:
                    side.add(m)
                    todo.append(m)
        if j in side:
            continue  # in a ring
        phi = float(dihedrals(x, *[np.array([q]) for q in (a, j, k, d)])[0][0])
        target = np.radians(SKEW[atoms[j].symbol]) * (1 if phi >= 0 else -1)
        axis = (x[k] - x[j]) / np.linalg.norm(x[k] - x[j])
        for sign in (1.0, -1.0):
            th = sign * (target - phi)
            trial = x.copy()
            for n in side:
                v = x[n] - x[k]
                trial[n] = x[k] + v * np.cos(th) + np.cross(axis, v) * np.sin(th) + axis * np.dot(axis, v) * (1 - np.cos(th))
            now = abs(float(dihedrals(trial, *[np.array([q]) for q in (a, j, k, d)])[0][0]))
            if abs(now - abs(target)) < 1e-3:
                x, turned = trial, True
                break
    if not turned:
        return molecule
    return Molecule(molecule.title, tuple(Atom(a.symbol, *map(float, q)) for a, q in zip(atoms, x)), molecule.bonds)


def _double_bonds_as_written(molecule, stereo):
    """The double bonds a–j=k–d of SMILES «/», «\\\\» cis or trans as written: the side of k turned by 180° about j=k
    when it is not. The same molecule when nothing was turned."""
    from math import pi

    import numpy as np

    from modules.compass.chemistry.cleanup import dihedrals

    if not stereo:
        return molecule
    x = np.array([a.position for a in molecule.atoms], dtype=float)
    neighbours = [[] for _ in molecule.atoms]
    for i, j, _ in molecule.bonds:
        neighbours[i].append(j)
        neighbours[j].append(i)
    turned = False
    for a, j, k, d, kind in stereo:
        phi = abs(float(dihedrals(x, *[np.array([q]) for q in (a, j, k, d)])[0][0]))
        if (kind == 'cis') == (phi < pi / 2):
            continue
        side, todo = {k}, [k]  # the atoms on the side of k, not through j
        while todo:
            n = todo.pop()
            for m in neighbours[n]:
                if m != j and m not in side:
                    side.add(m)
                    todo.append(m)
        if j in side:
            continue  # the double bond is in a ring: nothing to turn
        axis = (x[k] - x[j]) / np.linalg.norm(x[k] - x[j])
        for n in side:
            v = x[n] - x[k]
            x[n] = x[k] + 2 * np.dot(v, axis) * axis - v  # 180° about j=k
        turned = True
    if not turned:
        return molecule
    return Molecule(molecule.title, tuple(Atom(a.symbol, *map(float, q)) for a, q in zip(molecule.atoms, x)), molecule.bonds)

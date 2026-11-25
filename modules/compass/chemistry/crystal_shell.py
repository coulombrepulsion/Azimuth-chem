"""The molecular shell of a crystal: a molecule and all the molecules near it (as «Molecular Shell» of Mercury).

§1 THEORY
    In a molecular crystal every molecule is surrounded by others; those that come near it are its shell, and their
    number is the molecular coordination number (Kitaigorodsky: 12 or 14 in most organic crystals, as the 12 of the
    closest packing of balls). «Near» is either a distance between atoms (any atom of the neighbour within R Å of an
    atom of the centre) or a contact of the van der Waals spheres (d ≤ r_vdW(i) + r_vdW(j) + margin).
§2 ALGORITHM
    crystal_symmetry.walk gives the molecules of the cell whole (an atom i of molecule c at frac[i] + shift[i] −
    move[c], the centroid of c in the cell); a copy of c is (c, T), T a lattice vector. The centre: the copies given
    (from the atoms picked on the model, located by their fractional coordinates — locate()), else the first
    molecule of the cell. Every copy (c, T) with T in a box around the centre (wide enough for the reach and the
    sizes of the molecules) whose centroids are near enough is tested atom against atom (numpy); the copies of the
    centre are not neighbours. The symmetry code of a neighbour is that of its first atom seen from the first atom of
    the (first) centre put into the asymmetric unit (crystal_contacts.symmetry_code).
§3 APPLICATIONS
    modules/compass/actions/shell_window.py: «Кристалл → Молекулярная оболочка…».
§4 SPECIFICATION
    shell(crystal, centre=None, radius=4.0, vdw=False, factor=None) -> Shell(molecule, centre_atoms, neighbours,
        centres): molecule — the atoms of the centre first (centre_atoms of them), then of the neighbours in the order
        of neighbours; neighbours — (Neighbour(component, translation, code, distance, pair, formula), …) by distance.
        radius: Å between atoms, or the margin over the sum of the van der Waals radii when vdw is True.
    locate(crystal, points, factor=None) -> {(component, T)} — the molecules of the cell that the Cartesian points
        (atoms of the model: the cell at the origin) belong to; points of an infinite part are left out.
§5 PROCEDURES - below.
§6 NOTES
    A crystal without separate molecules (a salt, a metal, a framework) has no shell: ValueError with a sentence.
    The model is limited by azimuth.core.MAX_ATOMS (ValueError).
§7 TESTS
    tests/compass/test_crystal_shell.py.
§8' ROBUSTNESS / ERRORS
    A point of the model not found among the atoms of the cell (an atom added by hand) is ignored by locate().
"""

from dataclasses import dataclass

from azimuth.i18n import tr
from modules.compass.chemistry import crystal_contacts as cc
from modules.compass.chemistry import crystal_symmetry as cs
from modules.spectrum.analysis import contacts as mc


@dataclass(frozen=True)
class Neighbour:
    component: int
    translation: tuple
    code: str  # the symmetry code of the copy ('' — the centre itself shifted by nothing: never a neighbour)
    distance: float  # the shortest distance between an atom of it and an atom of the centre, Å
    pair: tuple  # (label of the atom of the centre, label of the atom of the neighbour) of that distance
    formula: str


@dataclass(frozen=True)
class Shell:
    molecule: object
    centre_atoms: int
    neighbours: tuple
    centres: tuple  # the copies (component, T) of the centre


def _groups(w):
    groups = {}
    for i, c in enumerate(w.component):
        groups.setdefault(c, []).append(i)
    return groups


def _whole(w, c, members):
    """(n, 3) fractional positions of molecule c, whole, its centroid in the cell."""
    import numpy as np

    m = w.move[c]
    return np.array([[w.frac[i][k] + w.shift[i][k] - m[k] for k in range(3)] for i in members], dtype=float)


def _formula(symbols):
    count = {}
    for s in symbols:
        count[s] = count.get(s, 0) + 1
    return cs._formula_text(count)


def locate(crystal, points, factor=None, w=None):
    import numpy as np

    w = w or cs.walk(crystal, factor)
    vectors = np.array(w.vectors, dtype=float)
    inverse = np.linalg.inv(vectors)
    found = set()
    for p in points:
        f = np.array(p, dtype=float) @ inverse
        for i in range(len(w.atoms)):
            n = np.round(f - w.frac[i])
            if np.linalg.norm((f - w.frac[i] - n) @ vectors) < 0.05:
                c = w.component[i]
                if not w.periods[c]:
                    m = w.move[c]
                    found.add((c, tuple(int(n[k] - w.shift[i][k] + m[k]) for k in range(3))))
                break
    return found


def shell(crystal, centre=None, radius=4.0, vdw=False, factor=None):
    import numpy as np

    from azimuth.core import MAX_ATOMS, Atom, Molecule

    w = cs.walk(crystal, factor)
    groups = {c: members for c, members in _groups(w).items() if not w.periods[c]}
    if not groups:
        raise ValueError(tr('В этом кристалле нет отдельных молекул — молекулярной оболочки нет.'))
    centres = sorted(centre) if centre else [(min(groups), (0, 0, 0))]
    centres = [(c, tuple(t)) for c, t in centres if c in groups]
    if not centres:
        raise ValueError(tr('Выделенные атомы не принадлежат отдельным молекулам кристалла.'))
    vectors = np.array(w.vectors, dtype=float)
    whole = {c: _whole(w, c, members) for c, members in groups.items()}
    radii = {c: np.array([mc.VDW.get(w.atoms[i][0], 1.8) for i in members]) for c, members in groups.items()}
    reach = float(radius) + (2 * max(mc.VDW.get(a[0], 1.8) for a in w.atoms) if vdw else 0.0)
    centre_xyz = np.vstack([(whole[c] + np.array(t)) @ vectors for c, t in centres])
    centre_r = np.concatenate([radii[c] for c, _ in centres])
    centre_labels = [w.atoms[i][4] for c, _ in centres for i in groups[c]]
    middle = centre_xyz.mean(axis=0)
    size = {c: float(np.max(np.linalg.norm(whole[c] @ vectors - (whole[c] @ vectors).mean(axis=0), axis=1)))
            for c in groups}
    extent = float(np.max(np.linalg.norm(centre_xyz - middle, axis=1)))
    heights = 1.0 / np.linalg.norm(np.linalg.inv(vectors), axis=0)  # the distances between the lattice planes
    limit = extent + reach + max(size.values())
    box = [int(np.ceil(limit / h)) + 1 for h in heights]
    base = np.round(middle @ np.linalg.inv(vectors)).astype(int)
    taken = set(centres)
    found = []
    first_c, first_t = centres[0]
    first_atom = groups[first_c][0]
    donor = (first_atom, tuple(int(w.shift[first_atom][k] - w.move[first_c][k] + first_t[k]) for k in range(3)))
    for c, members in groups.items():
        local = whole[c] @ vectors
        centroid = local.mean(axis=0)
        for i in range(-box[0], box[0] + 1):
            for j in range(-box[1], box[1] + 1):
                for k in range(-box[2], box[2] + 1):
                    t = (int(base[0] + i), int(base[1] + j), int(base[2] + k))
                    if (c, t) in taken:
                        continue
                    shift = np.array(t, dtype=float) @ vectors
                    if np.linalg.norm(centroid + shift - middle) > extent + size[c] + reach + 1e-6:
                        continue
                    d = np.linalg.norm(centre_xyz[:, None, :] - (local + shift)[None, :, :], axis=2)
                    near = d - (centre_r[:, None] + radii[c][None, :]) if vdw else d
                    if near.min() > radius + 1e-9:
                        continue
                    a, b = np.unravel_index(int(np.argmin(d)), d.shape)
                    atom = members[0]
                    node = (atom, tuple(int(w.shift[atom][q] - w.move[c][q] + t[q]) for q in range(3)))
                    code = cc.symmetry_code(crystal, w, donor, node)
                    found.append(Neighbour(c, t, '?' if code is None else (code or 'x, y, z'), float(d[a, b]),
                                           (centre_labels[a], w.atoms[members[b]][4]),
                                           _formula(w.atoms[q][0] for q in members)))
    found.sort(key=lambda n: (n.distance, n.component, n.translation))
    atoms = []
    for c, t in centres + [(n.component, n.translation) for n in found]:
        for f, i in zip(whole[c] + np.array(t), groups[c]):
            atoms.append(Atom(w.atoms[i][0], *crystal.cell.cartesian([float(x) for x in f])))
    if len(atoms) > MAX_ATOMS:
        raise ValueError(tr('Получится {} атомов — больше {}. Уменьшите радиус оболочки.').format(len(atoms), MAX_ATOMS))
    title = f'{crystal.title or "crystal"} ' + tr('молекулярная оболочка')
    count = sum(len(groups[c]) for c, _ in centres)
    return Shell(Molecule(title, tuple(atoms), None), count, tuple(found), tuple(centres))

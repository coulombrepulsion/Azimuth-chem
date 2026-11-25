"""Point group, symmetrisation and standard orientation of the Compass structure.

The analysis is the one of the Atlas page «Симметрия» (azimuth/symmetry_engine/symfind.py since 2026-11-13, the
Atlas's own file; it was read from quas_atlas.core; Wilkinson convention): candidate elements from the inertia axes and
atom positions, a tolerance in angstrom
(0.1 by default), a repeated pass with 1.5, 2 and 3 times the tolerance that accepts a higher group
only if the symmetrised structure stays within the tolerance of the input (root-mean-square shift).
Unlike the Atlas page the coordinates are not scaled: the symmetrised structure keeps its bond
lengths, either in its own place and orientation or moved to the standard orientation of the group
(centre of mass at the origin, principal axis along z, a C2 or σv along x / in xz).
"""

import math
from dataclasses import replace

from azimuth.core import Atom

MAX_ATOMS = 150  # as on the Atlas page
AUTO_ATOMS = 40  # the status line analyses smaller structures after every change
MIN_SEPARATION = 0.4  # Å: closer atoms of a symmetrised structure mean a wrong group
MAX_SHIFT = 2.0  # × the tolerance: the largest shift of one atom a group may ask
SCAN = (0.2, 0.35, 0.5, 0.7, 1.0, 1.5, 2.0, 3.0)  # × the tolerance: where the groups are looked for


def _symfind():
    """The engine of the program (azimuth/symmetry_engine — the Atlas's own files), not the Atlas's folder."""
    from azimuth.symmetry_engine import symfind

    return symfind


def _pass(sf, at, tol):
    """One analysis at tolerance tol of centred atoms -> dict or {'err'}."""
    cl = sf.classify(at, tol)
    name = cl['name']
    if cl.get('lin'):
        u = cl['lin']
        gens = sf.GROUP_GENS[name]
        e3 = list(u)
        a = [1, 0, 0] if abs(u[0]) < 0.9 else [0, 1, 0]
        e1 = sf.nrm(sf.cross(a, e3))
        e2 = sf.cross(e3, e1)
        Q = [e1, e2, e3]  # rows: u goes to z
        aligned = [{'t': p['t'], 'p': [0, 0, sf.dot(p['p'], u)]} for p in at]
    else:
        gens = sf.std_gens(name)
        if gens is None:
            return {'err': 'unsupported', 'name': name}
        Q = sf.align_to(at, gens, cl['el'], tol)
        if Q is None:
            return {'err': 'align', 'name': name}
        aligned = [{'t': p['t'], 'p': sf.mv(Q, p['p'])} for p in at]
    G = sf.closure(gens)
    sym = _symmetrize(sf, aligned, G, tol)
    if sym is None:
        return {'err': 'symmetrize', 'name': name}
    if cl.get('lin'):
        # the off-axis parts were dropped: measure them against the input, not the projection
        dev = [sum((sf.mv(Q, p['p'])[k] - s['p'][k]) ** 2 for k in range(3)) for p, s in zip(at, sym)]
    else:
        dev = [sum((p['p'][k] - s['p'][k]) ** 2 for k in range(3)) for p, s in zip(aligned, sym)]
    # a symmetrised structure is a structure — no two atoms in one place (the nearest-atom mapping of a too high group
    # at a loose tolerance pulled atoms together: toluene came out D8h, formamide C∞v), and no atom moved much more than
    # the tolerance (the mean shift alone let one atom go far)
    pts = [s['p'] for s in sym]
    near = min((math.dist(pts[i], pts[j]) for i in range(len(pts)) for j in range(i + 1, len(pts))), default=9.0)
    if near < MIN_SEPARATION:
        return {'err': 'collapse', 'name': name}
    return {'name': name, 'Q': Q, 'atoms': sym, 'rmsd': math.sqrt(sum(dev) / len(dev)), 'order': len(G), 'tol': tol,
            'max_shift': math.sqrt(max(dev))}


def _symmetrize(sf, at, G, tol):
    """As symfind.symmetrize, but every operation must move the atoms onto one another one to one (a
    permutation of the atoms of each element). The nearest-atom mapping alone let a group with more images than atoms
    pass: NH₃ came out C4v and ethane C8v at 0.2–0.3 Å, two hydrogens mapped onto one."""
    n = len(at)
    acc = [[0.0, 0.0, 0.0] for _ in at]
    for g in G:
        gt = sf.tp(g)
        taken = set()
        for i in range(n):
            q = sf.mv(g, at[i]['p'])
            j, bd = -1, 1e9
            for k, b in enumerate(at):
                if b['t'] == at[i]['t']:
                    d = math.dist(q, b['p'])
                    if d < bd:
                        bd, j = d, k
            if bd > tol * 3 or j in taken:
                return None
            taken.add(j)
            r = sf.mv(gt, at[j]['p'])
            for k in range(3):
                acc[i][k] += r[k]
    return [{'t': a['t'], 'p': [x / len(G) for x in acc[i]]} for i, a in enumerate(at)]


_CACHE = {}  # (tol, symbols and coordinates) -> the result with the atoms only (0.222.1)
CACHE_SIZE = 256


def analyze(molecule, tol=0.1):
    """{'name', 'rmsd', 'tol', 'order', 'standard': Molecule, 'in_place': Molecule} or {'err', ...}.

    Remembered for the same atoms and tolerance: Spectrum asked again at every choice of a molecule with frequencies
    (σ of the thermochemistry) — a macrocycle of a project of 44 molecules took up to 1.7 s each time.
    """
    key = (round(float(tol), 9), tuple((a.symbol, *(round(float(x), 6) for x in a.position)) for a in molecule.atoms))
    found = _CACHE.get(key)
    if found is None:
        found = _analyze(molecule, tol)
        found = {k: (v.atoms if k in ('standard', 'in_place') else v) for k, v in found.items()}
        if len(_CACHE) >= CACHE_SIZE:
            _CACHE.pop(next(iter(_CACHE)))
        _CACHE[key] = found
    return {k: (replace(molecule, atoms=v) if k in ('standard', 'in_place') else v) for k, v in found.items()}


def _analyze(molecule, tol=0.1):
    atoms = molecule.atoms
    if len(atoms) < 2:
        return {'err': 'one_atom' if atoms else 'empty'}
    if len(atoms) > MAX_ATOMS:
        return {'err': 'too_big'}
    # the point group of one molecule only — of two or more separate molecules (a dimer, a
    # salt, a cluster) it would describe their arrangement, which is not what is asked; dummy atoms X do not count
    from azimuth.core import without_dummies
    from modules.compass.chemistry.structure_tools import fragments

    parts = fragments(without_dummies(molecule))
    if len(parts) > 1:
        return {'err': 'several', 'count': len(parts)}
    sf = _symfind()
    raw = [{'t': a.symbol, 'p': list(a.position)} for a in atoms]
    mass = [sf._w(a.symbol) for a in atoms]
    centre = [sum(m * a.position[k] for m, a in zip(mass, atoms)) / sum(mass) for k in range(3)]
    at = sf.centered(raw)
    # the analysis at several tolerances, down and up from the chosen one; of the groups whose symmetrised
    # structure stays within the tolerance (mean and largest shift, atoms kept apart) the highest is taken. The group
    # found at the chosen tolerance alone could be too high (a mean shift within it, one atom far away) and then there
    # was no lower group to fall back to.
    found = []
    for f in SCAN:
        r = _pass(sf, at, tol * f)
        if 'err' not in r and r['rmsd'] <= tol and r['max_shift'] <= MAX_SHIFT * tol:
            found.append(r)
    if not found:
        return {'err': 'symmetrize', 'name': 'C1'}
    best = max(found, key=lambda r: (r['order'], -r['rmsd']))
    Qt = sf.tp(best['Q'])
    standard = tuple(Atom(a.symbol, *s['p']) for a, s in zip(atoms, best['atoms']))
    in_place = tuple(
        Atom(a.symbol, *[sf.mv(Qt, s['p'])[k] + centre[k] for k in range(3)]) for a, s in zip(atoms, best['atoms'])
    )
    return {
        'name': best['name'],
        'rmsd': best['rmsd'],
        'tol': best['tol'],
        'order': best['order'],
        'standard': replace(molecule, atoms=standard),
        'in_place': replace(molecule, atoms=in_place),
    }


def group_html(name):
    """C2v -> C<sub>2v</sub>; D∞h -> D<sub>∞h</sub>."""
    return name[0] + (f'<sub>{name[1:]}</sub>' if len(name) > 1 else '')


LOOSER = (0.2, 0.3, 0.5)  # Å: where a higher group is looked for when the chosen tolerance gives C1


def nearest_higher(molecule, tol):
    """C1 is often right for the geometry as it is (a conformer of a force field, a drawing with hydrogens put in), yet
    the structure is near a higher group. The first tolerance above tol that gives a group of order > 1 -> that result
    (its 'tol' and 'rmsd' tell how far the structure is from it), or None."""
    for loose in LOOSER:
        if loose <= tol + 1e-9:
            continue
        result = analyze(molecule, loose)
        if 'name' in result and result.get('order', 1) > 1 and 'err' not in result:
            return result
    return None

"""A path between two structures of the same atoms: linear and IDPP interpolation.

§1 THEORY
    A reaction path joins the reactant and the product through images, the starting guess of the nudged
    elastic band (NEB) that finds the minimum-energy path and its saddle point. The two ends must have the
    same atoms in the same order and the least relative rotation, so the product is renumbered after the
    reactant and turned onto it first (overlay.superimpose). Linear interpolation of the Cartesian
    coordinates x(t) = (1 − t) x0 + t x1 is the simplest guess, but where a group turns it cuts the arc
    and shortens bonds. The image-dependent pair potential (IDPP; Smidstrup, Pedersen, Stokbro, Jónsson,
    J. Chem. Phys. 140, 214106 (2014)) interpolates the distances instead: image k gets the target
    distances D_ij(t) = (1 − t) d_ij(0) + t d_ij(1) and minimizes
        S = sum_{i<j} w(D_ij) (d_ij − D_ij)², w(D) = D⁻⁴,
    which keeps near (bonded) pairs at their interpolated length.
§2 ALGORITHM
    ends(start, end, renumber): superimpose (pairing and Kabsch) when renumber, else Kabsch in the given
    order. linear: t = k / (n + 1), k = 1…n. idpp: from the linear image, gradient descent on S with
    backtracking (the step halves until S decreases, grows by 1.2 after an accepted step) up to STEPS
    steps or a gradient norm below TOL; every image is turned back (Kabsch) onto its linear guess so the
    path does not drift. path(...) -> the n + 2 frames start, images, end.
§3 APPLICATIONS
    modules/compass/actions/path_actions.py (Compass «Путь между структурами…»), Sextant (ORCA NEB-CI).
§4 SPECIFICATION
    ends(start, end, renumber=True) -> (start, end aligned in the order of start, rmsd);
    linear(start, end, images) -> [Molecule] of the inner images; idpp(start, end, images, steps=STEPS,
    tol=TOL) -> [Molecule]; path(start, end, images=8, method='idpp', renumber=True) -> (frames, rmsd);
    frames_xyz(frames, title) -> multi-frame XYZ text. ValueError: different atoms, images outside 1–50,
    an unknown method, atoms closer than 0.1 Å at an end.
§5 PROCEDURES - below.
§6 NOTES
    STEPS = 2000, TOL = 1e-6 (Å⁻³ for the gradient of S): far below what moves an atom visibly.
§7 TESTS
    tests/compass/test_reaction_path.py.
§8' ROBUSTNESS
    A coincident pair of atoms in a target (D = 0, only if both ends have it) is skipped.
"""

from dataclasses import replace

import numpy as np

from azimuth.core import Atom
from azimuth.i18n import tr

STEPS = 2000
TOL = 1e-6
METHODS = ('idpp', 'linear')


def _xyz(molecule):
    return np.array([a.position for a in molecule.atoms], float)


def _with(molecule, x, title):
    return replace(molecule, title=title, atoms=tuple(Atom(a.symbol, *map(float, p)) for a, p in zip(molecule.atoms, x)))


def _kabsch_onto(x, y):
    """x turned and shifted onto y (proper rotation)."""
    xc, yc = x.mean(0), y.mean(0)
    u, _, vt = np.linalg.svd((x - xc).T @ (y - yc))
    d = np.eye(3)
    d[2, 2] = 1.0 if np.linalg.det(u @ vt) >= 0 else -1.0
    return (x - xc) @ (u @ d @ vt) + yc


def ends(start, end, renumber=True):
    if len(start.atoms) != len(end.atoms) or sorted(a.symbol for a in start.atoms) != sorted(a.symbol for a in end.atoms):
        raise ValueError(tr('У начала и конца пути должны быть одни и те же атомы.'))
    if renumber:
        from modules.compass.chemistry.overlay import superimpose

        found = superimpose(start, end)
        return start, replace(found.aligned, bonds=None), found.rmsd
    if [a.symbol for a in start.atoms] != [a.symbol for a in end.atoms]:
        raise ValueError(tr('Атомы идут в разном порядке: включите перенумерацию.'))
    x = _kabsch_onto(_xyz(end), _xyz(start))
    rmsd = float(np.sqrt(np.mean(np.sum((x - _xyz(start)) ** 2, axis=1))))
    return start, _with(end, x, end.title), rmsd


def _check(images):
    if not isinstance(images, int) or not 1 <= images <= 50:
        raise ValueError(tr('Промежуточных структур — от 1 до 50.'))


def linear(start, end, images):
    _check(images)
    x0, x1 = _xyz(start), _xyz(end)
    return [_with(start, (1 - t) * x0 + t * x1, tr(f'Путь · кадр {k + 1}'))
            for k, t in enumerate(np.arange(1, images + 1) / (images + 1))]


def _distances(x):
    diff = x[:, None, :] - x[None, :, :]
    return diff, np.sqrt(np.einsum('ijk,ijk->ij', diff, diff))


def _objective(x, target, weight):
    diff, d = _distances(x)
    delta = d - target
    value = 0.5 * float(np.sum(weight * delta * delta))  # every pair twice: 1/2
    with np.errstate(divide='ignore', invalid='ignore'):
        factor = np.where(d > 1e-12, 2 * weight * delta / d, 0.0)
    gradient = np.einsum('ij,ijk->ik', factor, diff)
    return value, gradient


def idpp(start, end, images, steps=STEPS, tol=TOL):
    _check(images)
    x0, x1 = _xyz(start), _xyz(end)
    _, d0 = _distances(x0)
    _, d1 = _distances(x1)
    np.fill_diagonal(d0, 1.0)
    np.fill_diagonal(d1, 1.0)
    if np.min(d0) < 0.1 or np.min(d1) < 0.1:
        raise ValueError(tr('В начале или в конце пути два атома ближе 0,1 Å.'))
    frames = []
    for k, t in enumerate(np.arange(1, images + 1) / (images + 1)):
        target = (1 - t) * d0 + t * d1
        weight = np.where(target > 1e-9, 1.0 / np.maximum(target, 1e-9) ** 4, 0.0)
        np.fill_diagonal(weight, 0.0)
        np.fill_diagonal(target, 0.0)
        guess = (1 - t) * x0 + t * x1
        x = guess.copy()
        value, gradient = _objective(x, target, weight)
        step = 0.01
        for _ in range(steps):
            if np.linalg.norm(gradient) < tol:
                break
            trial = x - step * gradient
            trial_value, trial_gradient = _objective(trial, target, weight)
            if trial_value < value:
                x, value, gradient = trial, trial_value, trial_gradient
                step *= 1.2
            else:
                step *= 0.5
                if step < 1e-12:
                    break
        frames.append(_with(start, _kabsch_onto(x, guess), tr(f'Путь · кадр {k + 1}')))
    return frames


def path(start, end, images=8, method='idpp', renumber=True):
    if method not in METHODS:
        raise ValueError(method)
    start, end, rmsd = ends(start, end, renumber)
    inner = idpp(start, end, images) if method == 'idpp' else linear(start, end, images)
    return [start, *inner, end], rmsd


def frames_xyz(frames, title='Azimuth path'):
    out = []
    for k, frame in enumerate(frames):
        lines = frame.xyz().splitlines()
        lines[1] = f'{title} · frame {k} of {len(frames) - 1}'
        out.append('\n'.join(lines))
    return '\n'.join(out) + '\n'

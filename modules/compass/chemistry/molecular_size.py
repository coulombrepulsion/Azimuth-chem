"""The size of a molecule: the van der Waals volume, the surface areas, the effective diameter.

§1 PURPOSE
    «Calculate effective size / molecular area» of Chemcraft's Tools, for Compass («Инструменты → Объём и площадь
    поверхности…»): how big the molecule is — for a cavity of a solvent model, a diffusion estimate, the comparison
    of two conformers.
§1 THEORY
    The molecule is the union of spheres of the van der Waals radii of Bondi (J. Phys. Chem. 1964, 68, 441; 1.8 Å
    for an element without one). Volume V: the points of a cubic grid of step h inside at least one sphere, times
    h³ (the error falls as h; 0.1 Å gives about 0.5 % for small molecules). Surface (Shrake & Rupley, J. Mol. Biol.
    1973, 79, 351): POINTS points spread evenly over every sphere of radius r + probe (a Fibonacci sphere); a point
    inside no other such sphere is on the surface, and the area is 4π(r + probe)² × the share of such points. With
    probe 0 — the van der Waals surface; with 1.4 Å — the solvent-accessible surface (SASA, water). The effective
    diameter is that of the sphere of the same volume: d = (6V/π)^(1/3).
§4 SPECIFICATION
    BONDI {symbol: Å}; radius(symbol); volume(molecule, step=0.1) -> Å³; area(molecule, probe=0.0, points=POINTS)
    -> Å²; size(molecule, step=0.1) -> {'volume', 'area', 'sasa', 'diameter', 'atoms'}. X (dummy) atoms left out.
§7 TESTS
    tests/compass/test_molecular_size.py: one atom (4/3 π r³, 4π r²), two overlapping spheres (the lens formula), and
    two far apart (twice one).
"""

from math import pi, sqrt

import numpy as np

BONDI = {'H': 1.20, 'He': 1.40, 'Li': 1.82, 'C': 1.70, 'N': 1.55, 'O': 1.52, 'F': 1.47, 'Ne': 1.54, 'Na': 2.27,
         'Mg': 1.73, 'Si': 2.10, 'P': 1.80, 'S': 1.80, 'Cl': 1.75, 'Ar': 1.88, 'K': 2.75, 'Ni': 1.63, 'Cu': 1.40,
         'Zn': 1.39, 'Ga': 1.87, 'As': 1.85, 'Se': 1.90, 'Br': 1.85, 'Kr': 2.02, 'Pd': 1.63, 'Ag': 1.72, 'Cd': 1.58,
         'In': 1.93, 'Sn': 2.17, 'Te': 2.06, 'I': 1.98, 'Xe': 2.16, 'Pt': 1.75, 'Au': 1.66, 'Hg': 1.55, 'Tl': 1.96,
         'Pb': 2.02, 'U': 1.86}
DEFAULT = 1.8
POINTS = 960
WATER = 1.4  # Å, the probe of the solvent-accessible surface


def radius(symbol):
    return BONDI.get(symbol, DEFAULT)


def _spheres(molecule):
    chosen = [a for a in molecule.atoms if a.symbol != 'X']
    if not chosen:
        raise ValueError('no atoms')
    return np.array([a.position for a in chosen], float), np.array([radius(a.symbol) for a in chosen], float)


def volume(molecule, step=0.1):
    centres, radii = _spheres(molecule)
    low, high = (centres - radii[:, None]).min(0), (centres + radii[:, None]).max(0)
    axes = [np.arange(low[k] + step / 2, high[k], step) for k in range(3)]
    inside = 0
    gx, gy = np.meshgrid(axes[0], axes[1], indexing='ij')
    plane = np.stack([gx.ravel(), gy.ravel()], axis=1)
    for z in axes[2]:  # one plane at a time: memory stays small for a protein-sized box
        hit = np.zeros(len(plane), bool)
        for c, r in zip(centres, radii):
            if abs(z - c[2]) >= r:
                continue
            d2 = (plane[:, 0] - c[0]) ** 2 + (plane[:, 1] - c[1]) ** 2 + (z - c[2]) ** 2
            hit |= d2 < r * r
        inside += int(hit.sum())
    return inside * step ** 3


def _sphere_points(n):
    k = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * k / n)
    theta = pi * (1 + sqrt(5)) * k
    return np.stack([np.cos(theta) * np.sin(phi), np.sin(theta) * np.sin(phi), np.cos(phi)], axis=1)


def area(molecule, probe=0.0, points=POINTS):
    centres, radii = _spheres(molecule)
    radii = radii + probe
    unit = _sphere_points(points)
    total = 0.0
    for i, (c, r) in enumerate(zip(centres, radii)):
        dots = c + r * unit
        near = [j for j in range(len(centres)) if j != i and np.linalg.norm(centres[j] - c) < r + radii[j]]
        free = np.ones(points, bool)
        for j in near:
            free &= ((dots - centres[j]) ** 2).sum(1) >= radii[j] ** 2
        total += 4 * pi * r * r * free.mean()
    return float(total)


def size(molecule, step=0.1):
    v = volume(molecule, step)
    return {'volume': v, 'area': area(molecule), 'sasa': area(molecule, WATER),
            'diameter': (6 * v / pi) ** (1 / 3), 'atoms': sum(a.symbol != 'X' for a in molecule.atoms)}

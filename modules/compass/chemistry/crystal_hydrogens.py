"""The hydrogen atoms of an X-ray structure moved to their neutron distances — as Mercury does before it
looks for contacts.

§1 THEORY
    X-rays are scattered by the electrons; the one electron of a hydrogen atom is pulled into its bond, so X-ray
    structures put H about 0.1 Å too near its atom (C–H ≈ 0.95–0.98 Å instead of 1.08 Å). H···A distances of hydrogen
    bonds are then too long by about as much. Neutrons see the nuclei: the mean bond lengths of neutron structures
    (Allen & Bruno, Acta Cryst. B66, 380, 2010) — C–H 1.083, N–H 1.009, O–H 0.983, B–H 1.19 Å. Normalising moves each H
    along its bond to that length; the direction of the bond is kept.
§2 ALGORITHM
    For each H site of the asymmetric unit: its atom — the nearest atom of the cell or of the 26 cells around that is
    not H, within BOND Å; the new place D + (H − D)·L / |H − D| (Cartesian), back to fractions. An H without an atom
    so near (a hydride, a disordered water) or bonded to an element not in the table stays.
§4 SPECIFICATION
    normalized(crystal) -> (crystal, number of H moved); LENGTHS {element: Å}.
§7 TESTS tests/compass/test_crystal_hydrogens.py.
"""

from dataclasses import replace

import numpy as np

LENGTHS = {'C': 1.083, 'N': 1.009, 'O': 0.983, 'B': 1.19}
BOND = 1.35


def normalized(crystal):
    from modules.compass.chemistry import crystal as cr

    rows = np.array(crystal.cell.vectors(), dtype=float)
    inverse = np.linalg.inv(rows)
    heavy = [a for a in cr.unit_cell(crystal) if a[0] not in ('H', 'D', 'X')]
    if not heavy:
        return crystal, 0
    shifts = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)], dtype=float)
    frac = np.array([a[1:4] for a in heavy], dtype=float)
    images = (frac[None, :, :] + shifts[:, None, :]).reshape(-1, 3) @ rows
    symbols = [a[0] for a in heavy] * len(shifts)
    sites, moved = [], 0
    for site in crystal.sites:
        if site.symbol not in ('H', 'D'):
            sites.append(site)
            continue
        f = np.array((site.x, site.y, site.z)) % 1.0
        h = f @ rows
        d = np.linalg.norm(images - h, axis=1)
        k = int(np.argmin(d))
        length = LENGTHS.get(symbols[k])
        if d[k] > BOND or length is None or d[k] < 1e-6:
            sites.append(site)
            continue
        new = images[k] + (h - images[k]) * length / d[k]
        g = new @ inverse + (np.array((site.x, site.y, site.z)) - f)  # back near the original place
        sites.append(replace(site, x=float(g[0]), y=float(g[1]), z=float(g[2])))
        moved += 1
    return replace(crystal, sites=tuple(sites)), moved

"""Results of the cell computed put on the model of the crystal: the displacements of the vibrations at Γ
and the critical points of the density — on every atom and in every cell of the block shown.

§1 THEORY
    The cell computed (a supercell, a primitive cell, the cell of the file — crystal_steps.guess_computed) and the cell
    of the model are the same lattice: the fractions of the file f go to those of the cell computed by the matrix
    M (crystal_field.mapping_of), f_c = f M; a point of the model r = f A goes to r_c = f M A_c = r L with
    L = A⁻¹ M A_c — and a vector (a displacement) the same way, d_model = d_c L⁻¹ (a primitive cell is turned against
    the cell of the file; an optimized cell is stretched). A mode at Γ of the cell computed repeats with it: an atom of
    the block moves as the atom of the cell computed at its place modulo the lattice. A critical point repeats with the
    cell too: it is shown in every cell of the block where it falls.
§4 SPECIFICATION
    linear(file_rows, mapping, computed_rows) -> L; partners(model_atoms, computed_atoms, file_rows, mapping,
    computed_rows) -> [index | None]; model_modes(modes, computed_atoms, model, file_rows, mapping, computed_rows) ->
    [Vibration]; model_points(points, file_rows, mapping, computed_rows, n) -> [(kind, (x, y, z) Å, extra)] in the
    block of n cells (the faces included); bond_paths(points, model) -> [3 × 3 arrays] atom–point–atom.
§7 TESTS tests/compass/test_crystal_model_map.py.
"""

from dataclasses import replace
from itertools import product

import numpy as np

MATCH = 0.8  # Å


def linear(file_rows, mapping, computed_rows):
    return np.linalg.inv(np.asarray(file_rows, float)) @ np.asarray(mapping, float) @ np.asarray(computed_rows, float)


def partners(model_atoms, computed_atoms, file_rows, mapping, computed_rows):
    """For each atom of the model (Atom), the index of the atom of the cell computed at its place (mod the lattice)."""
    rows_c = np.asarray(computed_rows, float)
    inverse_c = np.linalg.inv(rows_c)
    lin = linear(file_rows, mapping, rows_c)
    fc = np.array([p for _, p in computed_atoms], float) @ inverse_c
    symbols = [s for s, _ in computed_atoms]
    out = []
    for atom in model_atoms:
        f = (np.array(atom.position, float) @ lin) @ inverse_c
        d = f[None, :] - fc
        d -= np.round(d)
        lengths = np.linalg.norm(d @ rows_c, axis=1)
        best = None
        for k in np.argsort(lengths):
            if lengths[k] > MATCH:
                break
            if symbols[k] == atom.symbol:
                best = int(k)
                break
        out.append(best)
    return out


def model_modes(modes, computed_atoms, model, file_rows, mapping, computed_rows):
    lin_inverse = np.linalg.inv(linear(file_rows, mapping, computed_rows))
    found = partners(model.atoms, computed_atoms, file_rows, mapping, computed_rows)
    out = []
    for mode in modes:
        if mode.vectors is None:
            out.append(mode)
            continue
        v = np.array(mode.vectors, float) @ lin_inverse
        vectors = tuple(tuple(float(x) for x in v[k]) if k is not None else (0.0, 0.0, 0.0) for k in found)
        out.append(replace(mode, vectors=vectors))
    return out


def model_points(points, file_rows, mapping, computed_rows, n=(1, 1, 1), edge=1e-3, merge=0.15):
    """points — [(kind, (x, y, z) Å of the cell computed, extra)]; their copies in the block of n cells of the model:
    [(kind, (x, y, z) Å, extra)] — one point where the copies of the cell computed meet (within merge Å)."""
    rows = np.asarray(file_rows, float)
    lin_inverse = np.linalg.inv(linear(rows, mapping, computed_rows))
    inverse = np.linalg.inv(rows)
    out, grid = [], {}  # grid: (kind, the cell of merge Å) -> indices of out — the merging without a search of all
    shifts = np.array(list(product(*[range(-1, k + 1) for k in n])), float)
    upper = np.array(n, float) + edge
    for kind, xyz, extra in points:
        f = (np.asarray(xyz, float) @ lin_inverse) @ inverse
        f -= np.floor(f + edge)
        for g in f + shifts:
            if not (np.all(g >= -edge) and np.all(g <= upper)):
                continue
            r = g @ rows
            key = tuple(int(np.floor(x / merge)) for x in r)
            near = [k for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)
                    for k in grid.get((kind, key[0] + dx, key[1] + dy, key[2] + dz), ())]
            if any(np.linalg.norm(r - out[k][1]) < merge for k in near):
                continue
            grid.setdefault((kind, *key), []).append(len(out))
            out.append((kind, r, extra))
    return [(kind, tuple(float(x) for x in r), extra) for kind, r, extra in out]


def bond_paths(points, model, reach=4.0):
    """For each bond point (extra — the two elements), the straight path atom–point–atom to the nearest atoms of those
    elements of the model (None when one of them is not in the block)."""
    xyz = np.array([a.position for a in model.atoms], float)
    symbols = np.array([a.symbol for a in model.atoms])
    paths = []
    for kind, r, extra in points:
        if kind != 'bond' or not extra or len(extra) != 2:
            continue
        r = np.asarray(r)
        d = np.linalg.norm(xyz - r, axis=1)
        ends = []
        for element in extra:
            order = [k for k in np.argsort(d) if symbols[k] == element and d[k] <= reach and k not in ends]
            if order:
                ends.append(int(order[0]))
        if len(ends) == 2:
            paths.append(np.array([xyz[ends[0]], r, xyz[ends[1]]]))
    return paths

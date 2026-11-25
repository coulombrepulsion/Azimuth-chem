"""Surfaces (slabs) of a crystal by Miller indices and CIF files of crystals and slabs.

§1 THEORY
    A plane (hkl) cuts the lattice of the cell a1, a2, a3 at a1/h, a2/k, a3/l; all lattice vectors
    n1 a1 + n2 a2 + n3 a3 with h n1 + k n2 + l n3 = 0 lie in it. A surface cell is a basis of the whole
    lattice v1, v2, v3 (integer rows of a matrix V with det V = ±1, so it holds the same atoms as the
    cell) whose first two vectors span the plane; v3 then steps from one plane to the next. A slab is
    `layers` such steps; the in-plane cell may be repeated, and vacuum separates the slab from its
    periodic images along the normal (the usual model of a surface).
§2 ALGORITHM
    surface_basis(h, k, l, cell): the integers are divided by their gcd; for planes with two zero
    indices the cell vectors are permuted; otherwise (the algorithm of ASE, ase.build.general_surface,
    Sun & Ceder, Surf. Sci. 617, 53 (2013)) p, q with p k + q l = gcd(k, l) (extended Euclid), shifted by
    c (l, −k) to make v1 as short as possible against v2, v1 = p (k, −h, 0) + q (l, 0, −h),
    v2 = (0, l, −k) / gcd(k, l), and a, b with a (p k + q l) − b h = 1 give v3 = (b, a p, a q).
    If v3 points to the side opposite to v1 × v2 it is reversed. slab(crystal, hkl, layers, vacuum):
    the atoms of the cell (unit_cell) translated over the integer box spanned by the corners of the new
    cell, kept when their coordinates g = (V^T)^-1 f satisfy 0 <= g1, g2 < 1, 0 <= g3 < layers; the
    Cartesian frame is turned so that A1 = v1 · cell lies along x, A1 × A2 along z; the new third vector
    is layers · A3 + vacuum · ẑ; the atoms are moved up by vacuum / 2 (the slab in the middle). The
    result is a Crystal with that cell, its atoms as P1 sites, so build() and cell_edges() of crystal.py
    work for it (n1 × n2 × 1 repetitions in the plane).
    write_cif(crystal): data block, cell, the space group name when known, the operations
    (_space_group_symop_operation_xyz) and the sites (_atom_site_label, _type_symbol, fract_x/y/z,
    occupancy) with 6 decimals.
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py (the «Кристалл» window: «Поверхность (hkl)», «Сохранить CIF…»).
§4 SPECIFICATION
    surface_basis(h, k, l) -> ((v1, v2, v3)) integer 3-tuples; slab(crystal, (h, k, l), layers=1,
    vacuum=15.0) -> Crystal; write_cif(crystal) -> str; operation_text(op) -> 'x, -y, z+1/2'.
    ValueError: indices all zero or above 9 in magnitude, layers outside 1-20, vacuum outside 0-100 A.
§5 PROCEDURES - below.
§6 NOTES
    The cell vectors are those of the CIF (the conventional cell); for a face-centred lattice a surface
    cell from the conventional one is a supercell of the primitive surface cell (the same plane, more
    atoms), as in ASE.
§7 TESTS
    tests/compass/test_surface.py.
§8' ROBUSTNESS
    Atoms are compared with a tolerance of 1e-6 in fractional coordinates; duplicates are removed.
"""

from fractions import Fraction
from math import gcd, isfinite

import numpy as np

from modules.compass.chemistry.crystal import Cell, Crystal, Site, unit_cell
from azimuth.i18n import tr

EPS = 1e-6


def _ext_gcd(a, b):
    """(x, y) with a x + b y = ±gcd(a, b) (as in ASE; the sign does not matter for det V = ±1)."""
    if b == 0:
        return 1, 0
    if a % b == 0:
        return 0, 1
    x, y = _ext_gcd(b, a % b)
    return y, x - y * (a // b)


def surface_basis(h, k, l, cell=None):
    if any(not isinstance(v, int) for v in (h, k, l)) or (h, k, l) == (0, 0, 0) or max(abs(h), abs(k), abs(l)) > 9:
        raise ValueError(tr('Индексы Миллера — целые от −9 до 9, не все нули.'))
    g = gcd(gcd(h, k), l)
    h, k, l = h // g, k // g, l // g
    if h == 0 and k == 0:
        return (1, 0, 0), (0, 1, 0), (0, 0, 1 if l > 0 else -1)
    if h == 0 and l == 0:
        return (0, 0, 1), (1, 0, 0), (0, 1 if k > 0 else -1, 0)
    if k == 0 and l == 0:
        return (0, 1, 0), (0, 0, 1), (1 if h > 0 else -1, 0, 0)
    vectors = np.array((cell or Cell(1, 1, 1)).vectors(), float)
    a1, a2, a3 = vectors
    p, q = _ext_gcd(k, l)
    k1 = np.dot(p * (k * a1 - h * a2) + q * (l * a1 - h * a3), l * a2 - k * a3)
    k2 = np.dot(l * (k * a1 - h * a2) - k * (l * a1 - h * a3), l * a2 - k * a3)
    if abs(k2) > 1e-10:
        c = -int(round(k1 / k2))
        p, q = p + c * l, q - c * k
    v1 = (p * k + q * l, -p * h, -q * h)
    gkl = gcd(k, l)
    v2 = (0, l // gkl, -k // gkl)
    a, b = _ext_gcd(p * k + q * l, h)
    v3 = (b, a * p, a * q)
    return v1, v2, v3


def slab(crystal, hkl, layers=1, vacuum=15.0):
    h, k, l = (int(x) for x in hkl)
    if not isinstance(layers, int) or not 1 <= layers <= 20:
        raise ValueError(tr('Слоёв — от 1 до 20.'))
    if not isfinite(vacuum) or not 0 <= vacuum <= 100:
        raise ValueError(tr('Вакуум — от 0 до 100 Å.'))
    cell = crystal.cell
    V = np.array(surface_basis(h, k, l, cell), float)
    if abs(round(abs(np.linalg.det(V))) - 1) > 1e-9:
        raise ValueError('surface basis is not unimodular')  # never: the construction gives det = ±1
    M = np.array(cell.vectors(), float)
    A = V @ M  # rows: A1, A2, A3 in the Cartesian frame of the CIF cell
    e1 = A[0] / np.linalg.norm(A[0])
    e3 = np.cross(A[0], A[1])
    e3 /= np.linalg.norm(e3)
    if np.dot(A[2], e3) < 0:
        V[2] = -V[2]
        A[2] = -A[2]
    e2 = np.cross(e3, e1)
    R = np.array((e1, e2, e3))  # new Cartesian = R @ old
    a_new, b_new = R @ A[0], R @ A[1]
    c_new = layers * (R @ A[2]) + np.array((0.0, 0.0, vacuum))
    inverse = np.linalg.inv(V.T)
    corners = np.array([[i, j, m * layers] for i in (0, 1) for j in (0, 1) for m in (0, 1)], float) @ V
    lo, hi = np.floor(corners.min(0)).astype(int) - 1, np.ceil(corners.max(0)).astype(int) + 1
    content = unit_cell(crystal)
    found = {}
    for symbol, fx, fy, fz, label in content:
        for i in range(lo[0], hi[0] + 1):
            for j in range(lo[1], hi[1] + 1):
                for m in range(lo[2], hi[2] + 1):
                    f = np.array((fx + i, fy + j, fz + m))
                    g = inverse @ f
                    if -EPS <= g[0] < 1 - EPS and -EPS <= g[1] < 1 - EPS and -EPS <= g[2] < layers - EPS:
                        key = tuple(np.round(g, 5))
                        found.setdefault(key, (symbol, label, R @ (f @ M)))
    new_cell = _cell_from(a_new, b_new, c_new)
    frame = np.array(new_cell.vectors(), float)
    shift = np.array((0.0, 0.0, vacuum / 2))
    sites = []
    for n, (symbol, label, r) in enumerate(found.values()):
        f = np.linalg.solve(frame.T, r + shift)
        sites.append(Site(f'{label or symbol}_{n + 1}', symbol, *(float(x) for x in f)))
    hkl_text = ''.join(str(x) if x >= 0 else f'-{-x}' for x in (h, k, l))
    title = f'{crystal.title or "crystal"} ({hkl_text})'
    notes = (tr(f'Поверхность ({hkl_text}): слоёв {layers}, вакуум {vacuum:g} Å, атомов в ячейке {len(sites)}.'),)
    identity = (((1, 0, 0), (0, 1, 0), (0, 0, 1)), (Fraction(0), Fraction(0), Fraction(0)))
    return Crystal(title, new_cell, tuple(sites), (identity,), 'P 1', notes)


def _cell_from(a, b, c):
    la, lb, lc = (float(np.linalg.norm(v)) for v in (a, b, c))

    def angle(u, v):
        return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1))))

    return Cell(la, lb, lc, angle(b, c), angle(a, c), angle(a, b)).validate()


def operation_text(op):
    rows, shifts = op
    parts = []
    for row, shift in zip(rows, shifts):
        text = ''
        for coefficient, name in zip(row, 'xyz'):
            if coefficient:
                sign = '-' if coefficient < 0 else ('+' if text else '')
                text += sign + ('' if abs(coefficient) == 1 else str(abs(coefficient))) + name
        shift = Fraction(shift) % 1
        if shift:
            text += f'+{shift.numerator}/{shift.denominator}'
        parts.append(text or '0')
    return ', '.join(parts)


def write_cif(crystal):
    c = crystal.cell
    name = ''.join(ch if ch.isalnum() else '_' for ch in (crystal.title or 'azimuth')) or 'azimuth'
    lines = [
        '# Written by Azimuth',
        f'data_{name}',
        f'_cell_length_a {c.a:.6f}',
        f'_cell_length_b {c.b:.6f}',
        f'_cell_length_c {c.c:.6f}',
        f'_cell_angle_alpha {c.alpha:.6f}',
        f'_cell_angle_beta {c.beta:.6f}',
        f'_cell_angle_gamma {c.gamma:.6f}',
    ]
    if crystal.space_group:
        lines.append(f"_space_group_name_H-M_alt '{crystal.space_group}'")
    if getattr(crystal, 'number', 0):
        lines.append(f'_space_group_IT_number {crystal.number}')
    if getattr(crystal, 'formula_sum', ''):
        lines.append(f"_chemical_formula_sum '{crystal.formula_sum}'")
    if getattr(crystal, 'formula_z', 0):
        lines.append(f'_cell_formula_units_Z {crystal.formula_z:g}')
    lines += ['', 'loop_', '_space_group_symop_operation_xyz']
    lines += [f"'{operation_text(op)}'" for op in crystal.operations]
    lines += ['', 'loop_', '_atom_site_label', '_atom_site_type_symbol', '_atom_site_fract_x',
              '_atom_site_fract_y', '_atom_site_fract_z', '_atom_site_occupancy']
    for s in crystal.sites:
        lines.append(f'{s.label or s.symbol} {s.symbol} {s.x:.6f} {s.y:.6f} {s.z:.6f} {s.occupancy:.4f}')
    return '\n'.join(lines) + '\n'

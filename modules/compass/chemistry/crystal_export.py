"""The crystal to other programs: POSCAR of VASP, the extended XYZ of ASE and OVITO, the block as CIF in P 1.

§1 THEORY POSCAR (VASP 5): a comment line, the scale (1.0), the three vectors of the cell (Å, rows), the element
    symbols, their counts, «Direct» and the fractions of the atoms grouped by element in that order. The extended XYZ
    (ASE, OVITO, Atomsk): the count, a line «Lattice="ax ay az bx … cz" Properties=species:S:1:pos:R:3 pbc="T T T"», the
    atoms in Å. The block of n₁ × n₂ × n₃ cells is the crystal of group P 1 with the edges n·a and every atom of the
    cell repeated (crystal.supercell): a program that reads it gets the same periodic crystal, each atom once.
§4 SPECIFICATION
    poscar(crystal, title=None) -> str; extended_xyz(crystal) -> str; block_cif(crystal, n) -> str (surface.write_cif of
    crystal.supercell). The atoms of the cell — crystal.unit_cell of its main disorder part (crystal.main_part); the
    dummy atoms X are left out.
§7 TESTS tests/compass/test_crystal_export.py — CsCl and NaCl: counts, fractions, the cell; read back by parse_cif.
"""

from modules.compass.chemistry import crystal as cr


def _atoms(crystal):
    return [a for a in cr.unit_cell(cr.main_part(crystal)) if a[0] != 'X']


def _grouped(atoms):
    order = []
    for a in atoms:
        if a[0] not in order:
            order.append(a[0])
    return order, {s: [a for a in atoms if a[0] == s] for s in order}


def poscar(crystal, title=None):
    atoms = _atoms(crystal)
    if not atoms:
        raise ValueError('no atoms in the cell')
    order, groups = _grouped(atoms)
    lines = [(title or crystal.title or 'crystal').replace('\n', ' ') + ' — Azimuth', '1.0']
    lines += ['  ' + ' '.join(f'{x:16.10f}' for x in v) for v in crystal.cell.vectors()]
    lines += ['  ' + ' '.join(f'{s:>4}' for s in order), '  ' + ' '.join(f'{len(groups[s]):>4}' for s in order), 'Direct']
    for s in order:
        lines += [f'  {a[1]:.10f} {a[2]:.10f} {a[3]:.10f}  {s}' for a in groups[s]]
    return '\n'.join(lines) + '\n'


def extended_xyz(crystal):
    atoms = _atoms(crystal)
    if not atoms:
        raise ValueError('no atoms in the cell')
    lattice = ' '.join(f'{x:.10f}' for v in crystal.cell.vectors() for x in v)
    lines = [str(len(atoms)), f'Lattice="{lattice}" Properties=species:S:1:pos:R:3 pbc="T T T"']
    for symbol, fx, fy, fz, _ in atoms:
        x, y, z = crystal.cell.cartesian((fx, fy, fz))
        lines.append(f'{symbol:<3} {x:16.10f} {y:16.10f} {z:16.10f}')
    return '\n'.join(lines) + '\n'


def block_cif(crystal, n):
    from modules.compass.chemistry import surface

    big = cr.supercell(cr.main_part(crystal), n)
    if tuple(n) == (1, 1, 1):  # the cell itself in P 1: every atom of the cell written out
        from modules.compass.chemistry.crystal import Crystal, Site, operation

        big = Crystal(f'{crystal.title or "crystal"} P1', crystal.cell,
                      tuple(Site(label, symbol, fx, fy, fz) for symbol, fx, fy, fz, label in _atoms(crystal)),
                      (operation('x, y, z'),), 'P 1', (), 1, crystal.formula_sum, crystal.formula_z)
    return surface.write_cif(big)

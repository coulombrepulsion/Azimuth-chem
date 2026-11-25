"""The bonds of a crystal by QTAIM: the critical points of the electron density that Multiwfn finds in the periodic wave
function of CP2K, gathered into kinds of bonds.

§1 THEORY
    In the theory of atoms in molecules (R. F. W. Bader, Atoms in Molecules, 1990) two atoms are bonded when a path of
    the maximal density joins their nuclei; on it lies a bond critical point (3,−1). Its density ρ (the strength), the
    Laplacian ∇²ρ and the energy density H = G + V (G — the kinetic, V — the potential energy density) tell the kind of
    the interaction (D. Cremer, E. Kraka, Angew. Chem. 23 (1984) 627; E. Espinosa et al., J. Chem. Phys. 117 (2002)
    5529): ∇²ρ > 0 and H > 0 (|V|/G < 1) — closed shells: an ionic bond, a van der Waals or a hydrogen contact; ∇²ρ > 0
    and H < 0 (1 < |V|/G < 2) — an intermediate (a dative bond, a strong hydrogen bond, a metal); ∇²ρ < 0 — a shared
    (covalent) bond. In a crystal the points of the cell repeat with it: the points of the same kind (the same pair
    of elements at the same distance) are one row, and their number per atom is the coordination of that kind (each
    point is counted once — the points on a face of the cell that Multiwfn gives twice, at x and x + 1, are one).
    The rule of Poincaré and Hopf for a periodic system: nuclei − bonds + rings − cages = 0 (one cell).
§2 ALGORITHM
    geometry(molden) — the cell ([Cell], Å) and the atoms ([Atoms] AU) of the file azimuth-multiwfn.molden
    (readers.cp2k.for_multiwfn); bond_kinds(cps, atoms, cell) — the bond points (multiwfn.parse_cps), repeated ones
    dropped (the fractions modulo 1), the length of the bond as the two straight pieces nucleus–point–nucleus by the
    nearest images, grouped by (the elements, the length to 0.01 Å): count, per atom of each element, the mean ρ, ∇²ρ,
    G, V, H, |V|/G and the kind; census(cps, cell) — the numbers of each kind of points and the sum of Poincaré–Hopf.
§4 SPECIFICATION
    geometry(text) -> (cell 3×3 in bohr, [(symbol, position in bohr)]); bond_kinds(...) -> [BondKind]; census(...) ->
    dict; nature(laplacian, energy) -> 'shared' | 'intermediate' | 'closed'; NATURE — the names for the user.
§7 TESTS
    tests/spectrum/test_crystal_aim.py — CsCl, 3 × 3 × 3, CP2K 2026.2 + Multiwfn.
"""

import re
from dataclasses import dataclass

import numpy as np

BOHR = 0.529177210903  # Å
NATURE = {'closed': 'замкнутые оболочки (ионная или слабая)', 'intermediate': 'промежуточная',
          'shared': 'обобществлённая (ковалентная)'}


@dataclass(frozen=True)
class BondKind:
    pair: tuple  # (element, element), sorted
    length: float  # Å
    count: int  # the points of this kind in the cell
    per_atom: dict  # {element: the bonds of this kind of one atom of it}
    rho: float  # a.u.
    laplacian: float
    kinetic: float  # G
    potential: float  # V
    energy: float  # H
    ratio: float  # |V| / G
    nature: str


def geometry(text):
    cell = re.search(r'\[Cell\]\s*\n(.*?)\n\s*\[', text, re.S)
    if not cell:
        raise ValueError('в файле нет [Cell]')
    rows = [[float(x) for x in line.split()] for line in cell.group(1).strip().splitlines()[:3]]
    block = re.search(r'\[Atoms\]\s*(\w*)[^\n]*\n(.*?)(?=^\s*\[)', text, re.S | re.M)
    if not block or len(rows) != 3:
        raise ValueError('в файле нет [Atoms] или ячейки из трёх векторов')
    scale = 1.0 if block.group(1).upper().startswith('AU') else 1 / BOHR
    atoms = []
    for line in block.group(2).splitlines():
        words = line.split()
        if len(words) >= 6:
            atoms.append((words[0][:1].upper() + words[0][1:].lower(), np.array([float(v) for v in words[3:6]]) * scale))
    return np.array(rows) / BOHR, atoms


def nature(laplacian, energy):
    if laplacian < 0:
        return 'shared'
    return 'intermediate' if energy < 0 else 'closed'


def _fractions(position, inverse):
    f = np.asarray(position) @ inverse
    return f - np.floor(f + 1e-6)


def _unique(points, inverse, key=lambda cp: cp['bohr']):
    """The points once: two at the same fractions modulo 1 (to 1e-4) are one."""
    seen, kept = [], []
    for cp in points:
        f = _fractions(key(cp), inverse)
        if any(np.all(np.abs(((f - g) + 0.5) % 1.0 - 0.5) < 1e-4) for g in seen):
            continue
        seen.append(f)
        kept.append(cp)
    return kept


def bond_kinds(cps, atoms, cell):
    cell = np.asarray(cell, dtype=float)
    inverse = np.linalg.inv(cell)

    def nearest(v):
        f = np.asarray(v) @ inverse
        return (f - np.round(f)) @ cell

    groups = {}
    for cp in _unique([c for c in cps if c['kind'] == 'bond' and len(c['atoms']) == 2], inverse):
        a, b = cp['atoms']
        if max(a, b) >= len(atoms):
            continue
        length = (np.linalg.norm(nearest(cp['bohr'] - atoms[a][1])) + np.linalg.norm(nearest(cp['bohr'] - atoms[b][1])))
        pair = tuple(sorted((atoms[a][0], atoms[b][0])))
        groups.setdefault((pair, round(length * BOHR, 2)), []).append(cp)
    counts = {}
    for symbol, _ in atoms:
        counts[symbol] = counts.get(symbol, 0) + 1
    kinds = []
    for (pair, length), found in sorted(groups.items(), key=lambda item: (item[0][1], item[0][0])):
        mean = {k: float(np.mean([c[k] for c in found])) for k in ('rho', 'laplacian', 'kinetic', 'potential', 'energy')}
        if pair[0] == pair[1]:
            per_atom = {pair[0]: 2 * len(found) / counts[pair[0]]}
        else:
            per_atom = {s: len(found) / counts[s] for s in pair}
        kinds.append(BondKind(pair, length, len(found), per_atom, mean['rho'], mean['laplacian'], mean['kinetic'],
                              mean['potential'], mean['energy'], abs(mean['potential']) / mean['kinetic']
                              if mean['kinetic'] else float('nan'), nature(mean['laplacian'], mean['energy'])))
    return kinds


def unique_points(cps, atoms, cell):
    """The critical points of the cell once (kind, position in Å, ρ, the elements of a bond point) — for the
    model of the crystal (crystal_model_map)."""
    inverse = np.linalg.inv(np.asarray(cell, dtype=float))
    out = []
    for cp in _unique([c for c in cps if c['kind'] in ('bond', 'ring', 'cage')], inverse):
        pair = [atoms[k][0] for k in cp.get('atoms', ()) if k < len(atoms)] if cp['kind'] == 'bond' else []
        out.append({'kind': cp['kind'], 'xyz': [float(x) * BOHR for x in cp['bohr']], 'rho': float(cp.get('rho', 0.0)),
                    'elements': pair})
    return out


def census(cps, cell):
    inverse = np.linalg.inv(np.asarray(cell, dtype=float))
    numbers = {}
    for kind in ('nucleus', 'bond', 'ring', 'cage'):
        numbers[kind] = len(_unique([c for c in cps if c['kind'] == kind], inverse))
    numbers['poincare_hopf'] = numbers['nucleus'] - numbers['bond'] + numbers['ring'] - numbers['cage']
    return numbers


def table_rows(kinds):
    """The rows of the table and of the CSV: elements, length Å, per atom, ρ, ∇²ρ, H, |V|/G (a.u.), the nature."""
    return [('–'.join(k.pair), f'{k.length:.2f}', ', '.join(f'{s}: {n:g}' for s, n in k.per_atom.items()),
             f'{k.rho:.4f}', f'{k.laplacian:+.4f}', f'{k.energy:+.5f}', f'{k.ratio:.2f}', k.nature) for k in kinds]


# -- the charges of the atoms of a crystal --------------------------------------------------------------------
# For a periodic wave function Multiwfn integrates Hirshfeld on an even grid of the cell (7 → 16 CM5, which prints the
# Hirshfeld charges too → «1» the even grids — the choice for valence electrons → the spacing, bohr → n: no .chg file);
# ADCH is not offered for it («This method currently does not support periodic wavefunction!»). Recorded on CsCl
# 3 × 3 × 3 (Multiwfn 2026.10.28): Hirshfeld Cs +0.299, Cl −0.299; CM5 ±0.547; 75 s on 4 cores.
CHARGES = ('7', '16', '1', '0.4', 'n', '0', 'q')
_CM5_ROW = re.compile(r'^\s*Atom:\s*(\d+)\s*([A-Za-z]{1,3})\s+CM5 charge:\s*(-?\d+\.\d+)\s+Hirshfeld charge:\s*(-?\d+\.\d+)',
                      re.M)


def parse_charges(text):
    """{'cm5': (…), 'hirshfeld': (…)} in the order of the atoms, from the table «CM5 charges»; {} without it."""
    rows = sorted((int(n), float(cm5), float(hirshfeld)) for n, _, cm5, hirshfeld in _CM5_ROW.findall(text))
    if not rows or [r[0] for r in rows] != list(range(1, len(rows) + 1)):
        return {}
    return {'cm5': tuple(r[1] for r in rows), 'hirshfeld': tuple(r[2] for r in rows)}


def run_charges(program, path, cores=1, step=None, timeout=3600):
    from modules.spectrum.wavefunction import multiwfn

    text, _ = multiwfn._run(program, path, CHARGES, cores, step, timeout)
    charges = parse_charges(text)
    if not charges:
        raise ValueError('Multiwfn не напечатал зарядов CM5. Конец его вывода:\n' + multiwfn._tail(text))
    return charges, text, multiwfn.version(text)


def charge_rows(atoms, charges):
    """Per element: the number of atoms, the mean Hirshfeld and CM5 charges and the spread (max − min) of CM5 — the
    atoms equal by symmetry have the same charge, a spread shows they are not (or the grid is coarse)."""
    rows = []
    for symbol in dict.fromkeys(s for s, _ in atoms):
        index = [k for k, (s, _) in enumerate(atoms) if s == symbol]
        hirshfeld = [charges['hirshfeld'][k] for k in index]
        cm5 = [charges['cm5'][k] for k in index]
        rows.append((symbol, str(len(index)), f'{np.mean(hirshfeld):+.3f}', f'{np.mean(cm5):+.3f}',
                     f'{max(cm5) - min(cm5):.3f}'))
    return rows

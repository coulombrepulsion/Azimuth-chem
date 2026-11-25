"""Multiwfn: IGMH — the weak interactions between fragments and the atoms and atom pairs that make them.

§1 THEORY
    The independent gradient model (Lefebvre et al., Phys. Chem. Chem. Phys. 19, 17928 (2017)) compares the gradient of
    the density with the gradient it would have if the contributions of the atoms did not cancel:
        δg(r) = |Σ_A |∇ρ_A(r)|| − |Σ_A ∇ρ_A(r)| (the absolute values taken per component),
    and δg_inter does the same with the fragments in place of the atoms: it is non-zero only where the densities of two
    fragments meet, i.e. where they interact. IGMH (T. Lu, Q. Chen, J. Comput. Chem. 43, 539 (2022)) takes the ρ_A of
    the Hirshfeld partition of the real density instead of free atoms: the isosurface of δg_inter (0.005 a.u. as in
    the paper) coloured by sign(λ₂)ρ looks like NCI, but belongs to the pair of fragments, and its integral splits
    into atom pairs — the atom-pair δG index δG_pair(A, B) (integrated δg of the pair, a.u.), whose sum per atom is the
    atomic δG index: which atoms make the interaction, in per cent. Within a family of complexes these indices follow
    the strength of the contacts (Lu & Chen 2022, Figs. 6–8).
§2 ALGORITHM The fragments are the molecules of the structure (the components of the bond graph of contacts.py) — at
    least two. The recipe, from the source of Multiwfn (visweak.f90, subroutine IGM; tools/record_multiwfn_igmh.py
    records it): 20 (visual study of weak interactions) → 11 (IGMH) → the number of fragments → the atoms of each
    («1-3,7») → the grid 1 | 2 | 3 → 3 (sl2r.cub = sign(λ₂)ρ, dg_inter.cub, dg_intra.cub, dg.cub) → 6 (the δG indices of
    two fragments; with more than two Multiwfn asks «1,3» first) → the integration grid 2 (high quality, radial 40,
    angular 170) → n (no atmdg.pdb) → 0 → 0 → q. atmdg.txt: «Atomic delta-g indices of fragment 1 …», rows « Atom 3 :
    0.012345 ( 45.67 % )», then «Atomic pair delta-g indices …», rows « 3 4 : 0.006789 ( 33.21 % )», and « Sum of all
    atomic pair delta-g indices: 0.020440». The output prints « Integral of delta-g_inter over whole space: … a.u.».
    Checked on Multiwfn 2026.7.15 (tools/record_multiwfn_igmh.py, ORCA 6.0.1 B3LYP-D3(BJ)/def2-SVP): the S22 water dimer
    — H3···O4 44.45 % of the pairs, their sum 0.179168 a.u., ∫δg_inter 0.093529 a.u.; benzene···methane — the hydrogen
    pointing at the ring 56 % of the methane side. atmdg.txt holds one pair of fragments; for more fragments every other
    pair in contact (atoms within the sum of van der Waals radii + 1 Å) is run again with the low grid and without the
    cubes.
§4 SPECIFICATION
    fragments(molecule) -> [atoms (0-based)] of the molecules, by the first atom; ranges(atoms) -> '1-3,7' (1-based);
    in_contact(molecule, fragments) -> [(a, b)] fragment pairs (0-based) whose atoms touch;
    answers(fragments, grid, pair=None, cubes=True) -> tuple of the answers;
    parse_atmdg(text) -> {'atoms': {fragment (1-based): [(atom 0-based, value, percent)]}, 'pairs': [(i, j, value,
        percent)] (0-based atoms), 'total': float | None} | None; parse_integrals(text) -> {'dg', 'dg_inter',
        'dg_intra'};
    run_igmh(program, path, molecule, grid='low', cores=1, step=None, timeout=1800) -> dict: sign (Cube), field (Cube of
        δg_inter), fragments, pairs [(i, j, value, fragment pair)], atoms {atom: value}, integrals, text, version.
    ValueError: fewer than two molecules, Multiwfn wrote no grids.
§6 NOTES
    MAX_PAIRS = 6 fragment pairs at most. δG indices are in a.u.; the percent of a pair is within its fragment pair.
§7 TESTS tests/spectrum/test_multiwfn_igmh.py.
"""

from __future__ import annotations

import re
from math import dist

from azimuth.i18n import tr
from modules.spectrum.analysis import contacts
from modules.spectrum.wavefunction import multiwfn

MAX_PAIRS = 6
REACH = 1.0  # Å over the sum of van der Waals radii: two fragments in contact
_ATOM = re.compile(r'^\s*Atom\s+(\d+)\s*:\s*(-?\d+\.\d+)\s*\(\s*(-?[\d.]+|NaN)\s*%\s*\)', re.I)
_PAIR = re.compile(r'^\s*(\d+)\s+(\d+)\s*:\s*(-?\d+\.\d+)\s*\(\s*(-?[\d.]+|NaN)\s*%\s*\)')
_FRAG = re.compile(r'Atomic delta-g indices of fragment\s*(\d+)', re.I)
_TOTAL = re.compile(r'Sum of all atomic pair delta-g indices:\s*(-?\d+\.\d+)', re.I)
_INTEGRAL = re.compile(r'Integral of delta-g(_inter|_intra)? over whole space:\s*(-?\d+\.\d+)', re.I)


def _xyz(molecule):
    return [tuple(float(c) for c in a.position) for a in molecule.atoms]


def fragments(molecule):
    symbols = [a.symbol for a in molecule.atoms]
    group = contacts._components(contacts._bonds(symbols, _xyz(molecule)))
    found = {}
    for k, g in enumerate(group):
        found.setdefault(g, []).append(k)
    return sorted(found.values(), key=lambda atoms: atoms[0])


def ranges(atoms):
    numbers = sorted(k + 1 for k in atoms)
    parts, start = [], None
    for k, n in enumerate(numbers):
        if start is None:
            start = n
        if k + 1 == len(numbers) or numbers[k + 1] != n + 1:
            parts.append(str(start) if start == n else f'{start}-{n}')
            start = None
    return ','.join(parts)


def in_contact(molecule, frags):
    xyz = _xyz(molecule)
    symbols = [a.symbol for a in molecule.atoms]
    out = []
    for a in range(len(frags)):
        for b in range(a + 1, len(frags)):
            if any(dist(xyz[i], xyz[j]) <= contacts.VDW.get(symbols[i], 1.8) + contacts.VDW.get(symbols[j], 1.8) + REACH
                   for i in frags[a] for j in frags[b]):
                out.append((a, b))
    return out


def answers(frags, grid='low', pair=None, cubes=True):
    out = ['20', '11', str(len(frags)), *(ranges(f) for f in frags), multiwfn.GRIDS[grid]]
    if cubes:
        out.append('3')
    if pair is not None:
        out.append('6')
        if len(frags) > 2:
            out.append(f'{pair[0] + 1},{pair[1] + 1}')
        out += ['2', 'n']
    return tuple(out + ['0', '0', 'q', 'q'])


def _percent(text):
    try:
        return float(text)
    except ValueError:
        return None


def parse_atmdg(text):
    atoms, pairs, total, fragment, section = {}, [], None, None, None
    for line in text.replace('\r', '').split('\n'):
        head = _FRAG.search(line)
        if head:
            fragment, section = int(head.group(1)), 'atoms'
            atoms[fragment] = []
            continue
        found = _TOTAL.search(line)
        if found:
            total = float(found.group(1))
            continue
        if 'pair delta-g indices' in line.lower():
            section = 'pairs'
            continue
        if section == 'atoms':
            row = _ATOM.match(line)
            if row:
                atoms[fragment].append((int(row.group(1)) - 1, float(row.group(2)), _percent(row.group(3))))
        elif section == 'pairs':
            row = _PAIR.match(line)
            if row:
                pairs.append((int(row.group(1)) - 1, int(row.group(2)) - 1, float(row.group(3)), _percent(row.group(4))))
    if not atoms and not pairs:
        return None
    return {'atoms': atoms, 'pairs': pairs, 'total': total}


def parse_integrals(text):
    out = {}
    for name, value in _INTEGRAL.findall(text):
        out['dg' + name] = float(value)
    return out


def run_igmh(program, path, molecule, grid='low', cores=1, step=None, timeout=1800):
    from modules.spectrum.readers.cube import read_cube

    frags = fragments(molecule)
    if len(frags) < 2:
        raise ValueError(tr('Для IGMH нужно хотя бы две молекулы: фрагменты — молекулы структуры.'))
    touching = in_contact(molecule, frags)[:MAX_PAIRS]
    first = touching[0] if touching else (0, 1)
    text, kept = multiwfn._run(program, path, answers(frags, grid, first), cores, step, timeout,
                               keep=('sl2r.cub', 'dg_inter.cub', 'atmdg.txt'))
    if 'sl2r.cub' not in kept or 'dg_inter.cub' not in kept:
        raise ValueError(tr('Multiwfn не записал сетки IGMH. Конец его вывода:') + '\n' + multiwfn._tail(text))
    sign, field = read_cube(kept['sl2r.cub']), read_cube(kept['dg_inter.cub'])
    if sign.values.shape != field.values.shape:
        raise ValueError(tr('Сетки разного размера.'))
    pairs, atoms = [], {}

    def take(found, pair):
        if not found:
            return
        for i, j, value, _ in found['pairs']:
            pairs.append((i, j, value, pair))
        for rows in found['atoms'].values():
            for k, value, _ in rows:
                atoms[k] = atoms.get(k, 0.0) + value

    take(parse_atmdg(kept.get('atmdg.txt', '')), first)
    for pair in touching[1:]:
        more, extra = multiwfn._run(program, path, answers(frags, 'low', pair, cubes=False), cores, step, timeout,
                                    keep=('atmdg.txt',))
        take(parse_atmdg(extra.get('atmdg.txt', '')), pair)
        text += '\n' + more
    pairs.sort(key=lambda p: -p[2])
    return {'sign': sign, 'field': field, 'fragments': frags, 'pairs': pairs, 'atoms': atoms,
            'integrals': parse_integrals(text), 'text': text, 'version': multiwfn.version(text)}

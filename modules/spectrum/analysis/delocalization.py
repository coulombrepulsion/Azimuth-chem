"""Electron delocalization between atoms and the aromaticity of rings.

§1 THEORY
    The delocalization index DI(A, B) is the number of electron pairs shared by the atoms A and B (Bader, Stephens,
    J. Am. Chem. Soc. 97, 7391 (1975); Fradera, Austen, Bader, J. Phys. Chem. A 103, 304 (1999)): about 1 for a single
    bond, 1.4–1.5 for an aromatic C–C, 2 for a double bond, a few hundredths for a hydrogen bond; with a metal it tells
    a covalent bond (DI ~ 0.5–1) from an ionic one (small). LI(A) — the electrons that stay on A. In the fuzzy atomic
    spaces of Becke (overlapping, smooth) they come from the atomic overlap matrix of the occupied orbitals and are
    also known as the fuzzy bond order (Mayer, Salvador, Chem. Phys. Lett. 383, 368 (2004)); Multiwfn computes them.
    Aromaticity of a ring: PDI — the mean DI of the para pairs of a six-membered ring (Poater et al., Chem. Eur. J. 9,
    400 (2003); benzene ~0.1, larger is more aromatic); FLU — how much the DI of the ring bonds fluctuate from those of
    the reference aromatics (Matito, Duran, Solà, J. Chem. Phys. 122, 014109 (2005); 0 for benzene, larger is less
    aromatic); MCI — the multicenter index over the whole ring (Bultinck, Ponec, Van Damme, J. Phys. Org. Chem. 18, 706
    (2005); larger is more aromatic), shown also normalized. HOMA — a geometric index from the bond lengths alone
    (Kruszewski, Krygowski, Tetrahedron Lett. 13, 3839 (1972); Krygowski, J. Chem. Inf. Comput. Sci. 33, 70 (1993)):
    HOMA = 1 − (1/n) Σ α_ij (R_opt − R_i)², 1 for benzene, 0 for the Kekulé structure.
§2 ALGORITHM
    Multiwfn (2026.7.15, answers recorded in tests/data/multiwfn/fuzzy_*.txt): LI and DI — 15 → 4 → n → 0 → q: the
    matrix «Total delocalization index matrix» (blocks of five columns; the diagonal is the valence) and «Localization
    index:» (an open shell prints α and β first, then the totals). PDI, FLU, MCI — 15 → 5 → ring → q → 6 → ring → q
    → 11 → ring → q → 0 → q: every item asks for rings until «q» («PDI value is», «FLU value is», «Multicenter DI:»
    and «… in normalized form:» — in the order of the rings given); only for a closed shell (an open shell: «Error:
    This function is only available for closed-shell system!»). HOMA is computed here from the geometry. The rings:
    the cycles of 5–7 atoms of the bonds of the molecule.
§4 SPECIFICATION
    parse_lidi(text) -> {'di': (n, n) ndarray, 'li': (n) ndarray}; parse_rings(text) -> {'pdi': [float], 'flu':
    [float], 'mci': [(value, normalized)]}; HOMA_PARAMETERS {(element, element): (R_opt Å, α)}; homa(molecule, ring) ->
    float | None (a bond without parameters); rings(molecule, bonds, sizes=(5, 6, 7)) -> [tuple of atoms in order];
    LIDI, ring_answers(rings) -> tuple; run_lidi(program, path, cores=1, step=None) -> (result, text);
    run_rings(program, path, rings, cores=1, step=None) -> (result, text).
§7 TESTS tests/spectrum/test_delocalization.py.
"""

import re

import numpy as np

from azimuth.i18n import tr

NUMBER = r'[+-]?\d+\.\d+'
LIDI = ('15', '4', 'n', '0', 'q')
# HOMA parameters: R_opt in Å and the normalization α — those Multiwfn 2026.7.15 prints as its defaults (menu 25 → 6
# → 1; tests/data/multiwfn/fuzzy_benzaldehyde_homa.txt): C–C, C–N, C–O, N–N of Krygowski (J. Chem. Inf. Comput. Sci.
# 33, 70 (1993)) and the others it lists
HOMA_PARAMETERS = {('B', 'C'): (1.4235, 104.507), ('B', 'N'): (1.402, 72.03), ('C', 'C'): (1.388, 257.7),
                   ('C', 'N'): (1.334, 93.52), ('C', 'O'): (1.265, 157.38), ('C', 'P'): (1.698, 118.91),
                   ('C', 'S'): (1.677, 94.09), ('N', 'N'): (1.309, 130.33), ('N', 'O'): (1.248, 57.21)}


def _matrix(text, start):
    """The square matrix printed by Multiwfn after the line at start, in blocks of columns («1 2 3» headers)."""
    rows = {}
    columns = []
    for line in text[start:].splitlines()[1:]:
        parts = line.split()
        if not parts:
            if rows:
                break
            continue
        if all(p.isdigit() for p in parts):
            columns = [int(p) for p in parts]
            continue
        if not columns or not parts[0].isdigit() or len(parts) != len(columns) + 1:
            break
        row = int(parts[0])
        for c, value in zip(columns, parts[1:]):
            rows.setdefault(row, {})[c] = float(value)
    if not rows:
        return None
    n = max(rows)
    out = np.zeros((n, n))
    for r, values in rows.items():
        for c, v in values.items():
            out[r - 1, c - 1] = v
    return out


def parse_lidi(text):
    heads = [m.start() for m in re.finditer(r'\*+ Total delocalization index matrix \*+', text)] or \
        [m.start() for m in re.finditer(r'\*+ Delocalization index matrix \*+', text)]
    if not heads:
        raise ValueError('no delocalization index matrix in the output of Multiwfn')
    di = _matrix(text, heads[-1])
    li_heads = [m.end() for m in re.finditer(r'^ Localization index:\s*$', text, re.M)]
    li = None
    if li_heads:
        block = []
        for line in text[li_heads[-1]:].splitlines()[1:]:
            found = re.findall(rf'(\d+)\(\s*[A-Za-z]+\s*\):\s*({NUMBER})', line)
            if not found:
                break
            block += [(int(a), float(v)) for a, v in found]
        li = np.zeros(di.shape[0])
        for a, v in block:
            li[a - 1] = v
    return {'di': di, 'li': li}


def parse_rings(text):
    return {'pdi': [float(v) for v in re.findall(rf'PDI value is\s+({NUMBER})', text)],
            'flu': [float(v) for v in re.findall(rf'FLU value is\s+({NUMBER})', text)],
            'mci': [(float(a), float(b)) for a, b in re.findall(
                rf'Multicenter DI:\s+({NUMBER})\s+Multicenter DI in normalized form:\s+({NUMBER})', text)]}


def homa(molecule, ring):
    """HOMA of a ring (0-based atoms in ring order); None when a bond has no parameters."""
    total = 0.0
    for k, a in enumerate(ring):
        b = ring[(k + 1) % len(ring)]
        pair = tuple(sorted((molecule.atoms[a].symbol, molecule.atoms[b].symbol)))
        if pair not in HOMA_PARAMETERS:
            return None
        r_opt, alpha = HOMA_PARAMETERS[pair]
        r = float(np.linalg.norm(np.subtract(molecule.atoms[a].position, molecule.atoms[b].position)))
        total += alpha * (r_opt - r) ** 2
    return 1.0 - total / len(ring)


def rings(molecule, bonds, sizes=(5, 6, 7)):
    """The cycles of the given sizes of the bond graph, each once, in ring order from its smallest atom, sorted."""
    near = {k: set() for k in range(len(molecule.atoms))}
    for bond in bonds:
        i, j = bond[0], bond[1]
        near[i].add(j)
        near[j].add(i)
    found = set()
    biggest = max(sizes)

    def walk(path):
        if len(path) > biggest:
            return
        for j in near[path[-1]]:
            if j == path[0] and len(path) in sizes:
                cycle = path[:]
                best = min(cycle)
                k = cycle.index(best)
                cycle = cycle[k:] + cycle[:k]
                if cycle[1] > cycle[-1]:
                    cycle = [cycle[0]] + cycle[1:][::-1]
                found.add(tuple(cycle))
            elif j > path[0] and j not in path:
                walk(path + [j])

    for start in range(len(molecule.atoms)):
        walk([start])
    # chords: a ring of 7 that is two smaller rings glued is not a ring of its own
    rings_ = sorted(found, key=lambda r: (len(r), r))
    return [r for r in rings_ if not any(set(small) < set(r) for small in rings_ if len(small) < len(r))
            and not _has_chord(r, near)]


def _has_chord(ring, near):
    members = set(ring)
    for k, a in enumerate(ring):
        neighbours = {ring[k - 1], ring[(k + 1) % len(ring)]}
        if (near[a] & members) - neighbours:
            return True
    return False


def ring_answers(rings_):
    """The answers of Multiwfn for PDI (six-membered rings), FLU and MCI of the rings (1-based in the answers)."""
    text = [','.join(str(a + 1) for a in r) for r in rings_]
    six = [t for t, r in zip(text, rings_) if len(r) == 6]
    answers = ['15']
    if six:
        answers += ['5', *six, 'q']
    answers += ['6', *text, 'q', '11', *text, 'q', '0', 'q']
    return tuple(answers)


def run_lidi(program, path, cores=1, step=None, timeout=1800):
    from modules.spectrum.wavefunction.multiwfn import _run

    text, _ = _run(program, path, LIDI, cores, step, timeout)
    return parse_lidi(text), text


def run_rings(program, path, rings_, cores=1, step=None, timeout=1800):
    from modules.spectrum.wavefunction.multiwfn import _run

    text, _ = _run(program, path, ring_answers(rings_), cores, step, timeout)
    if 'only available for closed-shell' in text or 'only available for single-determinant closed-shell' in text:
        raise ValueError(tr('PDI, FLU и MCI Multiwfn считает только для закрытой оболочки.'))
    return parse_rings(text), text

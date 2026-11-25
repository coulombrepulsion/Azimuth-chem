"""Peptides built from a sequence: «Правка → Построить пептид…».

§1 PURPOSE
    A short peptide in a chosen conformation — α-helix, β-strand, extended chain — for a first look at a protein,
    hydrogen bonds of a helix, the ribbon (protein.py), or a starting structure for a calculation.
§2 ALGORITHM
    1. The SMILES of the chain from the one-letter codes (RESIDUES: the side chain as a branch of Cα; proline a
       ring closed on N), H₂N– … –COOH, read by formats.from_smiles(quick=True) — for its atoms, bonds and hydrogens
       only (the full search took 13 s for Ala₁₂; the quick start had the N–H of indole inside the ring).
       The geometry of every residue comes from its free amino acid built once by from_smiles (_template), made L
       (§2.3) and put on the ideal N, Cα, C of §2.4; the heavy atoms are matched in the order of the SMILES fragment
       (from_smiles keeps it), the hydrogens by their atom.
    2. The backbone (protein.backbone) gives N, Cα, C, O of every residue in the order of the chain.
    3. Chirality (SMILES of Azimuth carries no @): every Cα made L, and the Cβ of Thr and Ile as in the natural
       amino acids (2S,3R and 2S,3S), by the rule checked on all 42 non-glycine residues, the 6 Thr and 5 Ile of
       crambin (tests/data/protein/1crn.pdb): with n = (b − a) × (d − a) for the neighbours a, b, d in the order
       (C, Cβ, N) of Cα, (Oγ1, Cγ2, Cα) of the Cβ of Thr, (Cγ1, Cγ2, Cα) of the Cβ of Ile, and h the direction of the
       fourth neighbour (H), n · h < 0. A wrong centre has two of its branches swapped by a turn of 180° about
       their bisector (each branch keeps its own shape).
    4. The backbone N, Cα, C built from the ideal bonds and angles of Engh and Huber (1991) with φ, ψ of the
       conformation and ω 180° (NeRF; proline φ −63°), and every residue — its side chain, its H — moved rigidly onto
       its N, Cα, C; then the O of every peptide bond and its amide H put in the peptide plane, on the bisector opposite
       the two bonds (1.229 and 1.01 Å). (Turning the rough start about its bonds kept its uneven bond angles: the
       helix of Trp₃₀ came out broken.) Before that every side chain is turned about Cα–Cβ and Cβ–Cγ to the staggered
       position with the fewest clashes (_choose_rotamers) — in a helix the side chains of the start overlapped.
    5. The simple field of cleanup.py relaxes everything but the backbone N, Cα, C, O — the side chains and
       hydrogens settle, φ and ψ stay (UFF afterwards: «Оптимизировать (UFF)»; with the backbone held it took 40 s for
       Trp₁₅, the simple field about a second).
§3 INTERFACE
    CONFORMATIONS = {key: (φ, ψ, title)}; RESIDUES = {letter: (three-letter name, side-chain SMILES)};
    smiles(sequence) -> str; build(sequence, conformation='helix', relax=True) -> Molecule; ValueError for an
    unknown letter, fewer than 2 or more than MAX_RESIDUES residues.
    chirality(x, centre, a, b, d) -> float — n · h of §2.3 (negative for L and for the natural Thr, Ile).
§4 NOTES
    Angles: α-helix φ −57°, ψ −47°; antiparallel β-strand −139°, +135°; extended 180°, 180°; ω 180° (trans). The
    ends are free (NH₂, COOH), not charged.
§5 TESTS
    tests/compass/test_peptide.py — the formulas, every Cα L and Thr/Ile as in crambin, φ/ψ measured back, an Ala₁₂
    helix recognised as a helix by protein.secondary (its i → i + 4 hydrogen bonds), Pro and Trp built.
"""

import numpy as np

from azimuth.core import Atom, Molecule
from azimuth.i18n import tr

MAX_RESIDUES = 30
BOND = {'N-CA': 1.458, 'CA-C': 1.525, 'C-N': 1.329}  # Å, Engh and Huber (1991)
ANGLE = {'N-CA-C': 111.2, 'CA-C-N': 116.2, 'C-N-CA': 121.7}  # degrees
PROLINE_PHI = -63.0  # the ring of proline holds φ near −63°
RELAX_STEPS = 1000
CONFORMATIONS = {
    'helix': (-57.0, -47.0, 'α-спираль'),
    'strand': (-139.0, 135.0, 'β-слой'),
    'extended': (180.0, 180.0, 'вытянутая цепь'),
}
RESIDUES = {
    'A': ('Ala', 'C'), 'R': ('Arg', 'CCCNC(N)=N'), 'N': ('Asn', 'CC(N)=O'), 'D': ('Asp', 'CC(=O)O'),
    'C': ('Cys', 'CS'), 'E': ('Glu', 'CCC(=O)O'), 'Q': ('Gln', 'CCC(N)=O'), 'G': ('Gly', ''),
    'H': ('His', 'Cc1c[nH]cn1'), 'I': ('Ile', 'C(CC)C'), 'L': ('Leu', 'CC(C)C'), 'K': ('Lys', 'CCCCN'),
    'M': ('Met', 'CCSC'), 'F': ('Phe', 'Cc1ccccc1'), 'P': ('Pro', None), 'S': ('Ser', 'CO'),
    'T': ('Thr', 'C(O)C'), 'W': ('Trp', 'Cc1c[nH]c2ccccc12'), 'Y': ('Tyr', 'Cc1ccc(O)cc1'), 'V': ('Val', 'C(C)C'),
}


def clean_sequence(sequence):
    letters = ''.join(ch for ch in sequence.upper() if not ch.isspace() and ch not in '-,;')
    bad = sorted({ch for ch in letters if ch not in RESIDUES})
    if bad:
        raise ValueError(tr('Неизвестные буквы аминокислот: {}. Однобуквенные коды: {}.').format(
            ', '.join(bad), ''.join(RESIDUES)))
    if not 2 <= len(letters) <= MAX_RESIDUES:
        raise ValueError(tr('Пептид — от 2 до {} остатков.').format(MAX_RESIDUES))
    return letters


def smiles(sequence):
    parts = []
    for letter in clean_sequence(sequence):
        side = RESIDUES[letter][1]
        if side is None:  # proline: N, Cδ, Cγ, Cβ, Cα closed on N
            parts.append('N9CCCC9C(=O)')
        else:
            parts.append('NC' + (f'({side})' if side else '') + 'C(=O)')
    return ''.join(parts) + 'O'


def chirality(x, centre, a, b, d):
    others = [x[a], x[b], x[d]]
    u = [(p - x[centre]) / np.linalg.norm(p - x[centre]) for p in others]
    h = -(u[0] + u[1] + u[2])
    return float(np.dot(np.cross(x[b] - x[a], x[d] - x[a]), h))


def _branch(near, root, start):
    """The atoms reached from start without passing root (start included)."""
    seen, stack = {start}, [start]
    while stack:
        a = stack.pop()
        for b in near[a]:
            if b != root and b not in seen:
                seen.add(b)
                stack.append(b)
    return seen


def _turn(x, atoms, pivot, axis, angle):
    axis = axis / np.linalg.norm(axis)
    k = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    r = np.eye(3) + np.sin(angle) * k + (1 - np.cos(angle)) * k @ k
    idx = sorted(atoms)
    x[idx] = (x[idx] - x[pivot]) @ r.T + x[pivot]


def _swap(x, near, centre, first, second):
    """Swap the branches of centre at first and second: a turn of 180° about their bisector."""
    u = (x[first] - x[centre]) / np.linalg.norm(x[first] - x[centre])
    v = (x[second] - x[centre]) / np.linalg.norm(x[second] - x[centre])
    atoms = _branch(near, centre, first) | _branch(near, centre, second)
    _turn(x, atoms, centre, u + v, np.pi)


def _dihedral(x, a, b, c, d):
    b0, b1, b2 = x[a] - x[b], x[c] - x[b], x[d] - x[c]
    b1n = b1 / np.linalg.norm(b1)
    v = b0 - np.dot(b0, b1n) * b1n
    w = b2 - np.dot(b2, b1n) * b1n
    return np.degrees(np.arctan2(np.dot(np.cross(b1n, v), w), np.dot(v, w)))


_TEMPLATES = {}


def _heavy_count(letter):
    from modules.compass.chemistry.names import smiles_graph

    side = RESIDUES[letter][1]
    if side is None:
        return 7  # N, Cδ, Cγ, Cβ, Cα, C, O
    return 4 + sum(1 for s in smiles_graph(side, strict=True)[0] if s != 'H') if side else 4


def _carbonyl(letter):
    """The index of C among the heavy atoms of the fragment: N, Cα, side chain…, C, O (proline: N, Cδ, Cγ, Cβ, Cα, C)."""
    return 5 if RESIDUES[letter][1] is None else _heavy_count(letter) - 2


def _template(letter):
    """The free amino acid of the letter built by from_smiles (its full search: good rings) and made L (Thr, Ile as
    natural) — (molecule, neighbours, symbols, positions); kept for the session."""
    from modules.compass.chemistry import protein
    from modules.compass.chemistry.formats import from_smiles

    if letter not in _TEMPLATES:
        side = RESIDUES[letter][1]
        text = 'N9CCCC9C(=O)O' if side is None else 'NC' + (f'({side})' if side else '') + 'C(=O)O'
        made = from_smiles(text)
        molecule = made[0] if isinstance(made, tuple) else made
        near = protein._neighbours(molecule)
        symbols = [a.symbol for a in molecule.atoms]
        x = np.array([a.position for a in molecule.atoms], float)
        ca = 4 if side is None else 1
        c = _carbonyl(letter)
        if side != '':
            _make_natural(x, near, symbols, letter, 0, ca, c)
        _TEMPLATES[letter] = (molecule, near, symbols, x)
    return _TEMPLATES[letter]


def _make_natural(x, near, symbols, letter, n, ca, c):
    """Cα made L (and the Cβ of Thr and Ile as in the natural amino acids) — the rule of §2.3."""
    side = [k for k in near[ca] if k not in (n, c)]
    heavy = [k for k in side if symbols[k] != 'H']
    if not heavy:
        return
    cb = heavy[0]
    hydrogen = next((k for k in side if k != cb and symbols[k] == 'H'), None)
    if hydrogen is not None and chirality(x, ca, c, cb, n) > 0:
        _swap(x, near, ca, cb, hydrogen)
    if letter in 'TI':
        rest = [k for k in near[cb] if k != ca and symbols[k] != 'H']
        hb = next(k for k in near[cb] if symbols[k] == 'H')
        if letter == 'T':
            first = next(k for k in rest if symbols[k] == 'O')
        else:  # Ile: Cγ1 is the ethyl (it has a further carbon)
            first = next(k for k in rest if any(symbols[m] == 'C' and m != cb for m in near[k]))
        second = next(k for k in rest if k != first)
        if chirality(x, cb, first, second, ca) > 0:
            _swap(x, near, cb, second, hb)


def _turned(x, atoms, pivot, axis, angle):
    trial = x.copy()
    _turn(trial, atoms, pivot, axis, angle)
    return trial


def _clash(x, moving, others, symbols):
    """Σ (d₀ − d)² over the pairs of moving and other atoms closer than d₀ (2.8 Å between heavy atoms, 2.0 with H)."""
    if not moving or not others:
        return 0.0
    a, b = x[sorted(moving)], x[sorted(others)]
    heavy_a = np.array([symbols[i] != 'H' for i in sorted(moving)])
    heavy_b = np.array([symbols[i] != 'H' for i in sorted(others)])
    limit = np.where(heavy_a[:, None] & heavy_b[None, :], 2.8, 2.0)
    d = np.linalg.norm(a[:, None, :] - b[None, :, :], axis=2)
    return float(np.sum(np.clip(limit - d, 0.0, None) ** 2))


def _choose_rotamers(x, near, symbols, chain, letters, passes=2):
    """The side chains turned about Cα–Cβ and Cβ–Cγ to the staggered position (χ ± 120°) with the fewest clashes with
    the rest of the peptide — from the N end, twice (a side chain built from the SMILES start points anywhere: in an
    α-helix those of i and i + 3, i + 4 overlapped)."""
    everything = set(range(len(x)))
    last = chain[-1]
    for _ in range(passes):
        moving = _branch_without(near, {last.ca}, last.c) - {last.c}  # the COOH of the C end: ψ is free there
        others = everything - moving - {last.c, last.ca}
        options = [(turn, _clash(_turned(x, moving, last.c, x[last.c] - x[last.ca], turn), moving, others, symbols))
                   for turn in np.radians(np.arange(0, 360, 30))]
        best = min(options, key=lambda option: option[1])[0]
        if best:
            _turn(x, moving, last.c, x[last.c] - x[last.ca], best)
        for letter, r in zip(letters, chain):
            if letter in 'GP':
                continue
            cb = next((k for k in near[r.ca] if k not in (r.n, r.c) and symbols[k] != 'H'), None)
            if cb is None:
                continue
            for root, tip in ((r.ca, cb),) + tuple((cb, k) for k in near[cb] if k != r.ca and symbols[k] == 'C'
                                                   and len(near[k]) > 1):
                moving = _branch_without(near, {root}, tip) - {tip}
                if not moving:
                    continue
                others = everything - moving - {tip, root}
                axis = x[tip] - x[root]
                best, best_score = 0.0, _clash(x, moving, others, symbols)
                for turn in (2 * np.pi / 3, -2 * np.pi / 3):
                    trial = x.copy()
                    _turn(trial, moving, tip, axis, turn)
                    score = _clash(trial, moving, others, symbols)
                    if score < best_score - 1e-9:
                        best, best_score = turn, score
                if best:
                    _turn(x, moving, tip, axis, best)


def _branch_without(near, stop, start):
    seen, todo = {start}, [start]
    while todo:
        a = todo.pop()
        for b in near[a]:
            if b not in stop and b not in seen:
                seen.add(b)
                todo.append(b)
    return seen


def _place(a, b, c, length, angle, torsion):
    """NeRF: the point d with |cd| = length, ∠bcd = angle, dihedral a–b–c–d = torsion (degrees)."""
    angle, torsion = np.radians(angle), np.radians(torsion)
    bc = (c - b) / np.linalg.norm(c - b)
    n = np.cross(b - a, bc)
    n /= np.linalg.norm(n)
    m = np.cross(n, bc)
    d2 = np.array([-length * np.cos(angle), length * np.sin(angle) * np.cos(torsion),
                   length * np.sin(angle) * np.sin(torsion)])
    return c + d2[0] * bc + d2[1] * m + d2[2] * n


def _backbone_coordinates(angles):
    """[(N, Cα, C)] of a chain with the ideal bonds and angles (Engh and Huber, Acta Cryst. A47, 392 (1991)), the
    given (φ, ψ) of every residue and ω = 180°."""
    n = np.array([0.0, 0.0, 0.0])
    ca = np.array([BOND['N-CA'], 0.0, 0.0])
    c = ca + BOND['CA-C'] * np.array([-np.cos(np.radians(ANGLE['N-CA-C'])), np.sin(np.radians(ANGLE['N-CA-C'])), 0.0])
    out = [(n, ca, c)]
    for k in range(1, len(angles)):
        n_new = _place(out[-1][0], out[-1][1], out[-1][2], BOND['C-N'], ANGLE['CA-C-N'], angles[k - 1][1])
        ca_new = _place(out[-1][1], out[-1][2], n_new, BOND['N-CA'], ANGLE['C-N-CA'], 180.0)
        c_new = _place(out[-1][2], n_new, ca_new, BOND['CA-C'], ANGLE['N-CA-C'], angles[k][0])
        out.append((n_new, ca_new, c_new))
    return [np.array(t) for t in out]


def _kabsch(old, new):
    """(R, t) with old @ R.T + t ≈ new (three or more points, no reflection)."""
    a, b = old - old.mean(axis=0), new - new.mean(axis=0)
    u, _, vt = np.linalg.svd(a.T @ b)
    sign = np.sign(np.linalg.det(u @ vt)) or 1.0
    rotation = (u @ np.diag([1.0, 1.0, sign]) @ vt).T
    return rotation, new.mean(axis=0) - old.mean(axis=0) @ rotation.T


def _plane(x, centre, a, b, atom, length):
    """Put atom on the bisector opposite the bonds centre–a and centre–b (in their plane), length from centre."""
    u = (x[a] - x[centre]) / np.linalg.norm(x[a] - x[centre])
    v = (x[b] - x[centre]) / np.linalg.norm(x[b] - x[centre])
    w = -(u + v)
    x[atom] = x[centre] + length * w / np.linalg.norm(w)


def build(sequence, conformation='helix', relax=True):
    from modules.compass.chemistry import protein
    from modules.compass.chemistry.formats import from_smiles

    letters = clean_sequence(sequence)
    if conformation not in CONFORMATIONS:
        raise ValueError(conformation)
    made = from_smiles(smiles(letters), quick=True)
    molecule = made[0] if isinstance(made, tuple) else made
    chains = protein.backbone(molecule)
    if len(chains) != 1 or len(chains[0]) != len(letters):
        raise ValueError(tr('Не удалось построить цепь пептида.'))
    chain = chains[0]
    near = protein._neighbours(molecule)
    symbols = [a.symbol for a in molecule.atoms]
    x = np.array([a.position for a in molecule.atoms], float)
    phi, psi, _ = CONFORMATIONS[conformation]
    ideal = _backbone_coordinates([(PROLINE_PHI if letter == 'P' else phi, psi) for letter in letters])
    heavy = [i for i, s in enumerate(symbols) if s != 'H']
    start = 0
    for k, (letter, r) in enumerate(zip(letters, chain)):  # every residue: its template on its ideal N, Cα, C
        t_mol, t_near, t_symbols, t_x = _template(letter)
        count = _heavy_count(letter)
        mine = heavy[start:start + count]
        start += count
        rotation, shift = _kabsch(t_x[[0, 1, _carbonyl(letter)]], ideal[k])
        placed = t_x @ rotation.T + shift
        pairs = list(zip(range(count), mine))  # the heavy atoms in the order of the fragment (as from_smiles keeps it)
        if k + 1 == len(letters):  # the last residue keeps the OH of its acid
            oxt = count
            pairs.append((oxt, next(m for m in near[mine[_carbonyl(letter)]] if symbols[m] == 'O' and m != r.o)))
        for t_i, i in list(pairs):  # the hydrogens of every heavy atom (the amide H of N: set in its plane below)
            if t_i == 0 and k > 0:
                continue
            t_h = sorted(m for m in t_near[t_i] if t_symbols[m] == 'H')
            h = sorted(m for m in near[i] if symbols[m] == 'H')
            pairs += list(zip(t_h, h))
        for t_i, i in pairs:
            x[i] = placed[t_i]
        x[[r.n, r.ca, r.c]] = ideal[k]
    _choose_rotamers(x, near, symbols, chain, letters)
    for k in range(len(chain) - 1):  # the peptide planes exact: O and the amide H in the plane, opposite their bonds
        r, nxt = chain[k], chain[k + 1]
        _plane(x, r.c, r.ca, nxt.n, r.o, 1.229)
        hydrogen = [m for m in near[nxt.n] if symbols[m] == 'H']
        if hydrogen:
            _plane(x, nxt.n, r.c, nxt.ca, hydrogen[0], 1.01)
    atoms = tuple(Atom(a.symbol, *map(float, p)) for a, p in zip(molecule.atoms, x))
    title = '-'.join(RESIDUES[ch][0] for ch in letters) if len(letters) <= 6 else ''.join(letters)
    built = Molecule(title, atoms, molecule.bonds)
    if relax:  # the side chains and hydrogens tidied by the simple field of cleanup.py (UFF took 40 s for Trp₁₅)
        from modules.compass.chemistry.cleanup import clean

        fixed = {a for r in chain for a in (r.n, r.ca, r.c, r.o)}
        movable = [i for i in range(len(atoms)) if i not in fixed]
        built = Molecule(title, clean(built, movable, steps=RELAX_STEPS, method='lbfgs')[0].atoms, molecule.bonds)
    return built

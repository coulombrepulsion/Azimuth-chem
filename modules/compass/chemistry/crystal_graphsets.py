"""Graph sets of the hydrogen bonds of a crystal (Etter).

§1 THEORY Etter, MacDonald & Bernstein (Acta Cryst. B46, 256, 1990) and Bernstein, Davis, Shimoni & Chang (Angew. Chem.
    Int. Ed. 34, 1555, 1995) name the pattern of hydrogen bonds G^a_d(n): G is S (the bond closes a ring inside one
    molecule), D (a finite pattern without a ring: one bond between two molecules), C (an infinite chain) or R (a ring
    of several molecules); a the number of acceptor atoms and d of donor atoms (hydrogens) of the pattern — written when
    not 1; n the number of atoms of the ring or of the repeat of the chain (hydrogens counted). The first level (the
    «unitary» graph set) is the pattern of one kind of hydrogen bond with all its symmetry copies: the carboxylic acid
    dimer R²₂(8), the amide chain C(4), the water chain C(2).
§2 ALGORITHM crystal_contacts.contacts gives the hydrogen bonds of the cell (each with its H and its acceptor as (atom,
    cell shift)); grouped joins the symmetry copies (the same labels, distance). For one group: every bond and its
    lattice translations join copies of molecules — a copy is (component, translation T), the node (atom, s) belongs to
    the copy T = s − shift of the atom in its component (crystal_symmetry.walk). A bond inside one copy — S(n), n the
    atoms of the shortest covalent path from the acceptor to the H. Otherwise a breadth-first walk over the copies from
    the copy of the H (at most LIMIT copies): a copy of the start molecule moved by a lattice vector reached — C(n) (the
    first such copy: the shortest repeat); a copy reached by a second bond — a ring R^a_d(n). n — over the molecules of
    the ring or of the repeat, the atoms of the covalent path between the two atoms where the bonds meet the molecule;
    a, d — the distinct acceptor and hydrogen atoms of the ring. A chain is named before a ring (a ladder is a chain at
    the first level); nothing found — D. The second level (Bernstein и др. 1995, §«binary graph sets»): the patterns of
    two kinds of bonds together that use bonds of both kinds. A depth-first walk over simple paths of copies (at most
    DEPTH bonds) from each molecule of the cell: back to the start copy — a ring, to the start molecule moved by a
    lattice vector — a chain; n is counted as above, a and d over the molecules of the ring or of the repeat. The
    smallest ring and the smallest chain are named (a ladder gives both), the ring first.
§3 APPLICATIONS
    modules/compass/actions/crystal_actions.py: the column «Граф-набор» of the «Контакты» window.
§4 SPECIFICATION
    graph_set(walk, bonds) -> str ('R²₂(8)', 'C(4)', 'S(6)', 'D', '' for a bond of an infinite framework);
    for_contacts(crystal, found, factor=None) -> [str] — one per row of crystal_contacts.grouped(found, atoms);
    binary(w, first, second) -> str ('R²₂(8)', 'C²₂(4)', 'R²₄(8), C²₂(6)', '' — no ring and no chain of both kinds);
    second_level(crystal, found, factor=None) -> [(row i, row j, str)] — the pairs of rows with a pattern.
§5 PROCEDURES - below.
§6 NOTES
    Graph sets are named for the bonds to the conventional acceptors (ACCEPTORS: N, O, F, S, Cl, Br, Se, I), as in the
    papers; the H···C and H···π contacts that the IUPAC criteria of the table also call hydrogen bonds get none.
    At the first level the patterns of two kinds of bonds together (R²₂(8) of two independent molecules, Z′ = 2) are
    not named — each of their bonds is D, as in the papers; second_level names them. Finite patterns of the second
    level (two D bonds at one molecule) are not named; neither are the levels above the second.
§7 TESTS
    tests/compass/test_crystal_graphsets.py.
§8' ROBUSTNESS / ERRORS
    Bonds of an infinite framework (no molecules) — ''; the walk stops at LIMIT copies.
"""

from collections import deque

LIMIT = 200
DEPTH = 6  # the second level: the most bonds of a ring or of the repeat of a chain
ACCEPTORS = ('N', 'O', 'F', 'S', 'Cl', 'Br', 'Se', 'I')  # the conventional acceptors (§6): no C–H···π, no H···C
_SUP = str.maketrans('0123456789', '⁰¹²³⁴⁵⁶⁷⁸⁹')
_SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')


def _sub(a, b):
    return tuple(a[k] - b[k] for k in range(3))


def _add(a, b):
    return tuple(a[k] + b[k] for k in range(3))


def _path(w, a, b):
    """The number of atoms of the shortest covalent path from atom a to atom b of one molecule (both counted)."""
    if a == b:
        return 1
    seen = {a: 1}
    queue = deque([a])
    while queue:
        k = queue.popleft()
        for m, _ in w.edges[k]:
            if m not in seen:
                seen[m] = seen[k] + 1
                if m == b:
                    return seen[m]
                queue.append(m)
    return 0


def name(kind, n, a=1, d=1):
    if kind == 'D':
        return 'D'
    if kind == 'R' or (kind == 'C' and (a, d) != (1, 1)):  # a chain of the second level: C²₂(4)
        return f'{kind}{str(a).translate(_SUP)}{str(d).translate(_SUB)}({n})'
    return f'{kind}({n})'


def graph_set(w, bonds):
    """bonds: the CrystalContact of one kind of hydrogen bond (the symmetry copies)."""
    instances = []
    for c in bonds:
        if c.site is None or c.acceptor is None:
            continue
        (h, sh), (a, sa) = c.site, c.acceptor
        if w.periods[w.component[h]] or w.periods[w.component[a]]:
            return ''
        mh = (w.component[h], _sub(sh, w.shift[h]))
        ma = (w.component[a], _sub(sa, w.shift[a]))
        instances.append((h, a, mh, ma))
    if not instances:
        return ''
    h0, a0, mh0, ma0 = instances[0]
    if mh0 == ma0:
        return name('S', _path(w, a0, h0))

    def edges(copy):
        component, t = copy
        for k, (h, a, mh, ma) in enumerate(instances):
            if mh[0] == component:
                shift = _sub(t, mh[1])
                yield (ma[0], _add(ma[1], shift)), h, a, (k, shift), 'H'
            if ma[0] == component:
                shift = _sub(t, ma[1])
                yield (mh[0], _add(mh[1], shift)), a, h, (k, shift), 'A'

    start = mh0
    tree = {start: None}  # copy -> (parent, atom of the copy on the bond, atom of the parent on it, bond key, role in copy)
    queue = deque([start])
    ring = None
    while queue and len(tree) < LIMIT:
        copy = queue.popleft()
        entering = tree[copy][3] if tree[copy] else None
        for other, mine, theirs, key, role in edges(copy):
            if key == entering:
                continue
            if other[0] == start[0] and other[1] != start[1]:  # the start molecule one lattice vector on: a chain
                n = 0
                chain = [copy]
                while tree[chain[-1]] is not None:
                    chain.append(tree[chain[-1]][0])
                chain.reverse()  # start … copy
                for k, x in enumerate(chain):
                    into = theirs if k == 0 else tree[x][1]  # the start: where its translated copy is bonded
                    out = mine if k == len(chain) - 1 else tree[chain[k + 1]][2]
                    n += _path(w, into, out)
                return name('C', n)
            if other in tree:
                if tree[other] is not None and tree[other][3] == key:
                    continue  # the bond to a child of this copy
                if ring is None:
                    ring = (copy, other, mine, theirs, role)
                continue
            tree[other] = (copy, theirs, mine, key, 'A' if role == 'H' else 'H')
            queue.append(other)
    if ring is None:
        return 'D'
    copy, other, mine, theirs, role = ring

    def up(x):
        line = [x]
        while tree[line[-1]] is not None:
            line.append(tree[line[-1]][0])
        return line

    left, right = up(copy), up(other)
    common = next(x for x in left if x in right)
    left, right = left[:left.index(common) + 1], right[:right.index(common) + 1]
    attach = {}  # copy -> the atoms where bonds of the ring meet it
    acceptors, donors = set(), set()

    def bond(x, ax, rx, y, ay):
        attach.setdefault(x, []).append(ax)
        attach.setdefault(y, []).append(ay)
        hydrogen, acceptor = ((x, ax), (y, ay)) if rx == 'H' else ((y, ay), (x, ax))
        donors.add(hydrogen)
        acceptors.add(acceptor)

    bond(copy, mine, role, other, theirs)
    for line in (left, right):
        for x in line[:-1]:
            parent, here, there, _, rx = tree[x]
            bond(x, here, rx, parent, there)
    n = sum(_path(w, *pair) for pair in attach.values() if len(pair) == 2)
    return name('R', n, len(acceptors), len(donors))


def _instances(w, bonds, kind):
    out = []
    for c in bonds:
        if c.site is None or c.acceptor is None:
            continue
        (h, sh), (a, sa) = c.site, c.acceptor
        if w.periods[w.component[h]] or w.periods[w.component[a]]:
            return None
        out.append((h, a, (w.component[h], _sub(sh, w.shift[h])), (w.component[a], _sub(sa, w.shift[a])), kind))
    return out


def binary(w, first, second):
    """The second-level graph sets of two kinds of hydrogen bonds (lists of CrystalContact, the symmetry copies)."""
    one, two = _instances(w, first, 0), _instances(w, second, 1)
    if not one or not two:
        return ''
    instances = one + two

    def edges(copy):
        component, t = copy
        for k, (h, a, mh, ma, kind) in enumerate(instances):
            if mh[0] == component:
                shift = _sub(t, mh[1])
                yield (ma[0], _add(ma[1], shift)), h, a, (k, shift), 'H', kind
            if ma[0] == component:
                shift = _sub(t, ma[1])
                yield (mh[0], _add(mh[1], shift)), a, h, (k, shift), 'A', kind

    best = {}  # 'R' / 'C' -> (n, a, d)

    def found(kind, steps):
        # steps: (atom of the copy before, its role, atom of the copy after) for each bond; copy i -> i + 1 (mod k)
        k = len(steps)
        n = sum(_path(w, steps[i - 1][2], steps[i][0]) for i in range(k))
        acceptors, donors = set(), set()
        for i, (mine, role, theirs) in enumerate(steps):
            h, a = ((i, mine), ((i + 1) % k, theirs)) if role == 'H' else (((i + 1) % k, theirs), (i, mine))
            donors.add(h)
            acceptors.add(a)
        value = (n, len(acceptors), len(donors))
        if kind not in best or value < best[kind]:
            best[kind] = value

    def walk(start, copy, path, keys, steps, kinds):
        for other, mine, theirs, key, role, kind in edges(copy):
            if key in keys:
                continue
            step = steps + [(mine, role, theirs)]
            used = kinds | {kind}
            if other == start:
                if len(used) == 2:
                    found('R', step)
                continue
            if other[0] == start[0]:
                if len(used) == 2:
                    found('C', step)
                continue
            if other in path or len(step) >= DEPTH:
                continue
            walk(start, other, path | {other}, keys | {key}, step, used)

    for start in sorted({(c[0], (0, 0, 0)) for i in instances for c in (i[2], i[3])}):
        walk(start, start, {start}, frozenset(), [], frozenset())
    return ', '.join(name(kind, *best[kind]) for kind in ('R', 'C') if kind in best)


def _rows(crystal, found):
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_contacts as cc

    atoms = cr.unit_cell(crystal)
    rows = []  # as grouped: (kind, text, distance of the first, [contacts])
    for c in found:
        t = cc.text(c, atoms)
        for row in rows:
            if row[0] == c.kind and row[1] == t and abs(row[2] - c.distance) < 1e-3:
                row[3].append(c)
                break
        else:
            rows.append([c.kind, t, c.distance, [c]])

    def counted(row):
        c = row[3][0]
        return row[0] == 'hydrogen' and c.acceptor is not None and atoms[c.acceptor[0]][0] in ACCEPTORS

    return rows, [counted(row) for row in rows]


def second_level(crystal, found, factor=None):
    """(i, j, name) for the pairs of rows of crystal_contacts.grouped whose bonds make a pattern together."""
    from modules.compass.chemistry import crystal_symmetry as cs

    rows, counted = _rows(crystal, found)
    kinds = [k for k, ok in enumerate(counted) if ok]
    if len(kinds) < 2:
        return []
    w = cs.walk(crystal, factor)
    out = []
    for x, i in enumerate(kinds):
        for j in kinds[x + 1:]:
            text = binary(w, rows[i][3], rows[j][3])
            if text:
                out.append((i, j, text))
    return out


def for_contacts(crystal, found, factor=None):
    """The graph set of each row of crystal_contacts.grouped(found, atoms), in its order ('' for other kinds)."""
    from modules.compass.chemistry import crystal_symmetry as cs

    rows, counted = _rows(crystal, found)
    if not any(counted):
        return ['' for _ in rows]
    w = cs.walk(crystal, factor)
    return [graph_set(w, list(row[3])) if ok else '' for row, ok in zip(rows, counted)]

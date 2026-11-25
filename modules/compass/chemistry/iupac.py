"""Systematic (IUPAC) names of the structure built in Compass, in Russian, English or Chinese.

§1 THEORY
    Substitutive nomenclature names a molecule as a parent hydride (a carbon chain or a carbocycle) with a
    principal characteristic group expressed as a suffix and all other groups as alphabetised prefixes with
    locants. The parent and its numbering follow the IUPAC 1993 recommendations (R-4.1), as in most
    textbooks — not the 2013 ones, where the longest chain outranks unsaturation (2-ethylbut-1-ene here,
    3-methylidenepentane in 2013). Seniority of principal groups: carboxylic acid > ester > amide >
    nitrile > aldehyde > ketone > alcohol > amine. Retained names used by IUPAC for single benzene
    derivatives: phenol, aniline, benzoic acid, benzaldehyde, benzonitrile, benzamide.
§2 ALGORITHM
    1. Graph: heavy atoms with H counts and bond orders (editing.perceived_orders; benzene rings 1.5);
       a structure without any H gets them from the valences (C 4, N 3, O 2, halogens 1). Every atom must
       have its usual valence (nitro groups excepted), or the structure is "not named".
    2. Groups on carbon atoms: =O, OH, halogens, nitro, ether/ester O, amine/amide N, nitrile N.
    3. Candidate parents: every monocyclic carbocycle, and every path through acyclic carbons (C atoms
       of non-principal COOH, CONH2, CN, COO groups are not chain atoms; a non-principal CHO carbon is,
       as "oxo": 3-oxopropanenitrile). For each parent and each
       numbering (two directions of a chain; 2n of a ring) the key, smallest wins:
         (-principal groups, ring 0 / chain 1, -multiple bonds, -length, -double bonds,
          principal locants, multiple-bond locants, double-bond locants, -prefixes, prefix locants,
          locants in alphabetical order of the prefixes of the language).
    4. Everything attached to the parent that is not the principal group becomes a prefix; a carbon
       branch is named recursively as a substituent numbered from its attachment atom (isopropyl,
       isobutyl, sec-butyl, tert-butyl are used for the four C3/C4 branches), a ring as phenyl or
       cycloalkyl, an O-alkyl as alkoxy, a nitrogen's other carbons as N-alkyl (alphabetised with the
       other prefixes, locant "N" first: N,N,2-trimethylpropan-1-amine).
    5. Rendering: en and ru by IUPAC (elision of the final "e", euphonic "a" before di/tri, locants
       omitted for one- and two-carbon parents, monosubstituted rings, the only possible position of a
       multiple bond in a three-carbon chain and terminal suffixes); zh in the traditional Chinese form
       used by the program's names table (2-丁烯, 2-甲基丙烷, 2-丙醇, 丙酮, 乙酸乙酯; substituents in
       ascending CIP-like order: alkyl before O-, N- and halogen groups; 甲苯, 乙苯, 苯乙烯, 苯甲醇,
       苯乙酮, 丙烯醛, 丙烯酸, 乙二醇 as in common use).
    6. The last numbering rule depends on the language (lowest locant to the prefix cited first), so
       name() keeps all tied numberings and Renderer.pick chooses: 1-chloro-3-fluoropropane, but
       1-фтор-3-хлорпропан and 1-氟-3-氯丙烷. Retained: biphenyl; methyl benzoate.
§3 APPLICATIONS
    The «IUPAC» button of Compass (naming_actions.show_iupac_name); if name() returns None, the names
    table of the program (names.name) and then PubChem (pubchem.py) are asked.
§4 SPECIFICATION
    name(molecule, lang='ru') -> str | None
        molecule: azimuth.core.Molecule (atoms, bonds optional); lang: 'ru', 'en' or 'zh'.
        None when the structure is outside the rules: other elements than C H N O F Cl Br I, charges or
        unusual valences (radicals), rings with heteroatoms or shared atoms (naphthalene, pyridine,
        oxirane), ring assemblies other than biphenyl, exocyclic double bonds, heteroatom-heteroatom
        bonds (peroxides, N-N) except nitro, C=N, acyl halides, HCN, CO2 and carbonic acid derivatives,
        anhydrides, several esters, esters of ring acids other than benzoates, N-substituted amides and
        polyamines, complex alkoxy groups, chains longer than C20. Several separate molecules are
        named one by one and joined with " + " (None if any of them is not named).
    ValueError for an unknown lang.
§5 PROCEDURES - below.
§6 NOTES
    Pure Python, no Qt. A tree of n carbons gives n(n+1)/2 chains; substituents are memoised, so a teaching
    molecule takes milliseconds (icosane 0.01 s, a 60-carbon chain 0.2 s on 2026-10-23). Stems go up to
    icosane (C20): a longer parent chain or substituent is "not named".
§7 TESTS
    tests/compass/test_iupac.py: names of 72 structures in three languages written by hand from the rules,
    the systematic names of the library table (library.NAMES), the "not named" cases, independence of
    the atom order. A fuzz run of 6000 random structures raised no exception.
§8' ROBUSTNESS
    Unsupported structures return None rather than a wrong name; within the rules the result depends only
    on the connectivity, not on the coordinates or the atom order.
    ASSUMPTION: the Chinese form (traditional order of substituents, 甲苯/乙苯 for alkylbenzenes) follows
    the program's names table and common textbook usage, not a checked edition of the CCS rules.
"""

from collections import Counter

from modules.compass.chemistry.editing import aromatize, perceived_orders

VALENCE = {'C': 4, 'N': 3, 'O': 2, 'F': 1, 'Cl': 1, 'Br': 1, 'I': 1}
Z = {'C': 6, 'N': 7, 'O': 8, 'F': 9, 'Cl': 17, 'Br': 35, 'I': 53}
HALO = {'F': 'fluoro', 'Cl': 'chloro', 'Br': 'bromo', 'I': 'iodo'}
SENIORITY = ('acid', 'ester', 'amide', 'nitrile', 'aldehyde', 'ketone', 'alcohol', 'amine')
TERMINAL = ('acid', 'ester', 'amide', 'nitrile', 'aldehyde')  # their carbon ends a chain
LANGS = ('ru', 'en', 'zh')


class Unsupported(Exception):
    pass


# -- 1. the graph ------------------------------------------------------------------------------------
class Graph:
    def __init__(self, molecule):
        atoms = molecule.atoms
        if not atoms:
            raise Unsupported('empty')
        sym = [a.symbol for a in atoms]
        bonds = aromatize(len(atoms), perceived_orders(molecule))
        explicit_h = any(s == 'H' for s in sym)
        self.sym, self.adj, self.h = {}, {}, {}
        for i, s in enumerate(sym):
            if s == 'H':
                continue
            if s not in VALENCE:
                raise Unsupported(s)
            self.sym[i], self.adj[i], self.h[i] = s, {}, 0
        for i, j, o in bonds:
            if sym[i] == 'H' and sym[j] == 'H':
                raise Unsupported('H2')
            if sym[i] == 'H' or sym[j] == 'H':
                if o != 1:
                    raise Unsupported('H multiple bond')
                self.h[j if sym[i] == 'H' else i] += 1
            else:
                self.adj[i][j] = self.adj[j][i] = o
        if not explicit_h:
            for i in self.sym:
                self.h[i] = max(0, VALENCE[self.sym[i]] - round(sum(self.adj[i].values())))
        self.nitro = set()
        for i, s in self.sym.items():  # N(=O)O as drawn, whatever the perceived orders
            nb = list(self.adj[i])
            if s == 'N' and len(nb) == 3 and self.h[i] == 0:
                os_ = [j for j in nb if self.sym[j] == 'O' and len(self.adj[j]) == 1 and self.h[j] == 0]
                cs = [j for j in nb if self.sym[j] == 'C']
                if len(os_) == 2 and len(cs) == 1:
                    self.nitro.add(i)
        skip = self.nitro | {j for n in self.nitro for j in self.adj[n] if self.sym[j] == 'O'}
        for i, s in self.sym.items():
            if i in skip:
                continue
            if abs(sum(self.adj[i].values()) + self.h[i] - VALENCE[s]) > 1e-6:
                raise Unsupported(f'valence of {s}{i}')
            if s in HALO and self.h[i]:
                raise Unsupported('hydrogen halide')
        for i, s in self.sym.items():
            for j, o in self.adj[i].items():
                if s != 'C' and self.sym[j] != 'C' and not (i in self.nitro or j in self.nitro):
                    raise Unsupported('heteroatom-heteroatom bond')
                if o == 2 and {s, self.sym[j]} == {'C', 'N'}:
                    raise Unsupported('C=N (imines, oximes)')

    def components(self):
        seen, out = set(), []
        for start in sorted(self.sym):
            if start in seen:
                continue
            stack, comp = [start], set()
            while stack:
                k = stack.pop()
                if k in comp:
                    continue
                comp.add(k)
                stack.extend(self.adj[k])
            seen |= comp
            out.append(comp)
        return out


def _rings(graph, atoms):
    """Simple cycles of the component as atom lists in ring order; shared atoms are not supported."""
    adj = {i: [j for j in graph.adj[i] if j in atoms] for i in atoms}
    # cycle basis by a spanning tree
    parent, order, rings = {}, [], []
    for root in sorted(atoms):
        if root in parent:
            continue
        parent[root] = None
        stack = [root]
        while stack:
            u = stack.pop()
            order.append(u)
            for v in adj[u]:
                if v not in parent:
                    parent[v] = u
                    stack.append(v)
    depth = {}
    for u in order:
        depth[u] = 0 if parent[u] is None else depth[parent[u]] + 1
    seen_edges = set()
    for u in atoms:
        for v in adj[u]:
            if parent.get(v) == u or parent.get(u) == v or (min(u, v), max(u, v)) in seen_edges:
                continue
            seen_edges.add((min(u, v), max(u, v)))
            a, b, left, right = u, v, [u], [v]
            while a != b:
                if depth[a] >= depth[b]:
                    a = parent[a]
                    left.append(a)
                else:
                    b = parent[b]
                    right.append(b)
            rings.append(left + right[-2::-1])
    used = [a for r in rings for a in r]
    if len(used) != len(set(used)):
        raise Unsupported('fused or bridged rings')
    for r in rings:
        if any(graph.sym[a] != 'C' for a in r):
            raise Unsupported('heterocycle')
    return rings


# -- 2. groups ----------------------------------------------------------------------------------------
class Groups:
    """What hangs on every carbon: oxo, hydroxy, halogens, nitro, amine/amide/nitrile N, ether O."""

    def __init__(self, g, comp):
        self.g = g
        self.carbons = sorted(i for i in comp if g.sym[i] == 'C')
        self.kind = {}  # carbon -> principal-type group carried (acid, ester, amide, nitrile, aldehyde, ketone)
        self.alcohols, self.amines = [], {}  # OH carbons; amine N -> its carbons
        self.ester_o = {}  # carbonyl carbon -> alkyl-side O
        for c in self.carbons:
            nb = g.adj[c]
            oxo = [j for j, o in nb.items() if g.sym[j] == 'O' and o == 2]
            oh = [j for j, o in nb.items() if g.sym[j] == 'O' and o == 1 and g.h[j] == 1]
            ether = [j for j, o in nb.items() if g.sym[j] == 'O' and o == 1 and g.h[j] == 0 and len(g.adj[j]) == 2]
            amn = [j for j, o in nb.items() if g.sym[j] == 'N' and o == 1 and j not in g.nitro]
            nitrile = [j for j, o in nb.items() if g.sym[j] == 'N' and o == 3]
            cn = sum(1 for j in nb if g.sym[j] == 'C')
            if (oxo or nitrile) and any(g.sym[j] in HALO for j in nb):
                raise Unsupported('acyl halide or cyanogen halide')
            if nitrile and not cn:
                raise Unsupported('hydrogen cyanide')
            if nitrile:
                if len(g.adj[nitrile[0]]) != 1:
                    raise Unsupported('isonitrile')
                self.kind[c] = 'nitrile'
            elif oxo:
                if len(oxo) > 1 or len(oh) + len(ether) + len(amn) > 1:
                    raise Unsupported('CO2, carbonic acid or carbamic acid derivative')
                if oh:
                    self.kind[c] = 'acid'
                elif ether:
                    self.kind[c] = 'ester'
                    self.ester_o[c] = ether[0]
                elif amn:
                    n = amn[0]
                    if g.h[n] != 2:
                        raise Unsupported('substituted amide')
                    self.kind[c] = 'amide'
                elif cn >= 2:
                    self.kind[c] = 'ketone'
                else:
                    self.kind[c] = 'aldehyde'
            elif oh:
                self.alcohols.extend([c] * len(oh))
        for n in comp:
            if g.sym[n] == 'N' and n not in g.nitro and all(o == 1 for o in g.adj[n].values()):
                cs = [j for j in g.adj[n] if g.sym[j] == 'C']
                if any(self.kind.get(c) == 'amide' for c in cs):
                    continue
                self.amines[n] = cs
        for o in comp:  # ether O: between two carbons, not of an ester
            if g.sym[o] == 'O' and len(g.adj[o]) == 2 and not any(self.ester_o.get(c) == o for c in g.adj[o]):
                if (
                    any(self.kind.get(c) == 'ester' for c in g.adj[o])
                    and sum(self.kind.get(c) == 'ester' for c in g.adj[o]) > 1
                ):
                    raise Unsupported('anhydride')
        esters = [c for c, k in self.kind.items() if k == 'ester']
        if len(esters) > 1:
            raise Unsupported('several esters')
        kinds = (
            set(self.kind.values()) | ({'alcohol'} if self.alcohols else set()) | ({'amine'} if self.amines else set())
        )
        self.principal = next((k for k in SENIORITY if k in kinds), None)
        if self.principal != 'ester' and esters:
            raise Unsupported('ester with a senior group')

    def principal_sites(self):
        """[(carbon, kind)] of the principal groups (an amine N counts once per carbon it may sit on)."""
        p = self.principal
        if p is None:
            return []
        if p == 'alcohol':
            return [(c, p) for c in self.alcohols]
        if p == 'amine':
            return [(c, p, n) for n, cs in self.amines.items() for c in cs]
        return [(c, p) for c, k in self.kind.items() if k == p]


# -- 3. parents and numberings ---------------------------------------------------------------------
class Parent:
    """A parent hydride with a numbering: atoms[k] has locant k+1."""

    def __init__(self, ring, atoms):
        self.ring, self.atoms = ring, list(atoms)
        self.loc = {a: k + 1 for k, a in enumerate(self.atoms)}


def _chains(g, groups, rings):
    ring_atoms = {a for r in rings for a in r}
    p = groups.principal
    # a carbon of COOH, CONH2, CN, COOR that is not principal cannot be a chain atom; a CHO carbon can
    # (3-oxopropanenitrile, not 2-formylethanenitrile)
    excluded = {c for c, k in groups.kind.items() if k in TERMINAL and k != p and k != 'aldehyde'}
    allowed = [c for c in groups.carbons if c not in ring_atoms and c not in excluded]
    allowed_set = set(allowed)
    adj = {c: [j for j in g.adj[c] if j in allowed_set] for c in allowed}
    out = []
    for start in allowed:
        # all simple paths from start (the acyclic part is a forest: one path per pair)
        stack = [(start, [start])]
        while stack:
            node, path = stack.pop()
            if path[0] <= path[-1]:
                out.append(path)
            for nxt in adj[node]:
                if nxt not in path:
                    stack.append((nxt, path + [nxt]))
    return out


def _numberings(parent_atoms, ring):
    if not ring:
        yield parent_atoms
        if len(parent_atoms) > 1:
            yield parent_atoms[::-1]
        return
    n = len(parent_atoms)
    for s in range(n):
        yield [parent_atoms[(s + k) % n] for k in range(n)]
        yield [parent_atoms[(s - k) % n] for k in range(n)]


class Naming:
    """Build the language-independent description of one connected molecule."""

    def __init__(self, g, comp):
        self.g, self.comp = g, comp
        self.groups = Groups(g, comp)
        self.rings = _rings(g, comp)
        self.ring_of = {a: tuple(r) for r in self.rings for a in r}

    def describe(self):
        g, groups = self.g, self.groups
        p = groups.principal
        sites = groups.principal_sites()
        if p == 'ester':
            return self._ester()
        candidates = []
        for ring in self.rings:
            for order in _numberings(ring, True):
                candidates.append(Parent(True, order))
        for chain in _chains(g, groups, self.rings):
            for order in _numberings(chain, False):
                candidates.append(Parent(False, order))
        if not candidates:
            raise Unsupported('no carbon')
        best = []
        for par in candidates:
            try:
                d = self._parent_description(par, sites)
            except Unsupported:
                continue
            if not best or d['key'] < best[0]['key']:
                best = [d]
            elif d['key'] == best[0]['key']:
                best.append(d)
        if not best:
            raise Unsupported('no parent')
        top = best[0]
        same = [
            x
            for _, x in top['prefixes']
            if x[0] == 'ring'
            and top['parent'].ring
            and len(x[1]['parent'].atoms) == len(top['parent'].atoms)
            and x[1]['benzene'] == top['benzene']
        ]
        if same:  # ring assemblies: only biphenyl itself
            if top['benzene'] and len(top['prefixes']) == 1 and not top['found'] and not same[0][1]['prefixes']:
                return [{'retained': ('бифенил', 'biphenyl', '联苯'), 'key': ()}]
            raise Unsupported('ring assembly')
        return best

    # the principal group on (or attached to) a parent
    def _principal_on(self, par, sites):
        g, atoms = self.g, set(par.atoms)
        found = []
        for site in sites:
            c, kind = site[0], site[1]
            if kind == 'amine':
                if c in atoms:
                    found.append((c, kind, site[2], 'in'))
            elif c in atoms:
                if kind in TERMINAL and not par.ring and kind != 'ketone':
                    found.append((c, kind, None, 'in'))
                elif kind in ('ketone', 'alcohol'):
                    found.append((c, kind, None, 'in'))
            elif par.ring and kind in TERMINAL:
                anchor = next((a for a in g.adj[c] if a in atoms), None)
                if anchor is not None:
                    found.append((anchor, kind, c, 'attached'))
        if not par.ring:  # a terminal group must end the chain
            for c, kind, _, mode in found:
                if kind in TERMINAL and c not in (par.atoms[0], par.atoms[-1]):
                    raise Unsupported('terminal group inside a chain')
        # amine: one N per parent position; the same N on two carbons of the chain is a ring (not here)
        return found

    def _parent_description(self, par, sites):
        g = self.g
        if len(par.atoms) > len(STEMS['en']):
            raise Unsupported('parent longer than icosane')
        found = self._principal_on(par, sites)
        atoms = set(par.atoms)
        if par.ring and len(par.atoms) != len(self.ring_of.get(par.atoms[0], ())):
            raise Unsupported('ring')
        # multiple bonds of the parent; none may leave it
        mult = []
        for k, a in enumerate(par.atoms):
            nxt = par.atoms[(k + 1) % len(par.atoms)] if (par.ring or k + 1 < len(par.atoms)) else None
            if nxt is not None and not (not par.ring and k + 1 >= len(par.atoms)):
                o = g.adj[a][nxt]
                if o in (2, 3):
                    mult.append(
                        (
                            min(par.loc[a], par.loc[nxt])
                            if not (par.ring and {par.loc[a], par.loc[nxt]} == {1, len(par.atoms)})
                            else len(par.atoms),
                            o,
                        )
                    )
            for j, o in g.adj[a].items():
                if g.sym[j] == 'C' and j not in atoms and o >= 2:
                    raise Unsupported('exocyclic multiple bond')
        benzene = (
            par.ring
            and len(par.atoms) == 6
            and all(g.adj[a][par.atoms[(k + 1) % 6]] == 1.5 for k, a in enumerate(par.atoms))
        )
        if par.ring and not benzene and any(o == 1.5 for a in par.atoms for o in g.adj[a].values()):
            raise Unsupported('aromatic ring other than benzene')
        if benzene:
            mult = []
        principal_atoms = {f[0] for f in found if f[3] == 'in'} | {f[2] for f in found if f[3] == 'attached'}
        principal_n = {f[2] for f in found if f[1] == 'amine'}
        for c, kind, _, mode in found:  # the heteroatom of a principal group on a parent atom
            if mode != 'in' or kind in ('amine', 'ketone', 'aldehyde'):
                continue
            if kind == 'ester':
                principal_n.add(self.groups.ester_o[c])
                continue
            want = {'alcohol': ('O', 1), 'acid': ('O', 1), 'amide': ('N', 1), 'nitrile': ('N', 3)}[kind]
            het = next(
                j
                for j, o in g.adj[c].items()
                if (g.sym[j], o) == want
                and j not in principal_n
                and j not in g.nitro
                and (kind == 'nitrile' or g.h[j] >= 1)
            )
            principal_n.add(het)
        prefixes = []  # (locant, descriptor)
        n_prefixes = []
        for a in par.atoms:
            for j, o in g.adj[a].items():
                if j in atoms:
                    continue
                if j in principal_atoms or j in principal_n:
                    continue
                prefixes.append((par.loc[a], self._substituent(a, j, atoms, found)))
            # groups carried by the parent atom itself (oxo / hydroxy not principal)
            kind = self.groups.kind.get(a)
            is_principal = any(f[0] == a and f[3] == 'in' for f in found)
            if kind in ('ketone', 'aldehyde') and not is_principal:
                prefixes.append((par.loc[a], ('oxo',)))
            if kind in ('acid', 'amide', 'nitrile') and not is_principal:
                raise Unsupported('non-principal C-group in the chain')
        # N-substituents of a principal amine
        amines = [f for f in found if f[1] == 'amine']
        if len(amines) > 1 and any(len(self.g.adj[f[2]]) > 1 for f in amines):
            raise Unsupported('N-substituted polyamine (N1,N3 locants)')
        for c, kind, n, mode in found:
            if kind == 'amine':
                for j in g.adj[n]:
                    if j != c:
                        n_prefixes.append(('N', self._branch(n, j)))
        # oxo/hydroxy on the parent atom were counted above via neighbours; drop principal ones
        cleaned = []
        for loc, d in prefixes:
            if d is None:
                continue
            cleaned.append((loc, d))
        prefixes = cleaned
        principal_locs = sorted(par.loc[f[0]] for f in found)
        double = sorted(l for l, o in mult if o == 2)
        all_mult = sorted(l for l, o in mult)
        pref_locs = sorted(l for l, _ in prefixes)
        if (
            not found
            and self.groups.principal is not None
            and self.groups.principal in ('alcohol', 'amine', 'ketone', 'aldehyde', 'acid', 'amide', 'nitrile')
        ):
            pass  # the principal group is elsewhere: a weaker candidate
        d = {
            'parent': par,
            'benzene': benzene,
            'found': found,
            'mult': sorted(mult),
            'prefixes': prefixes,
            'n_prefixes': n_prefixes,
            'principal': self.groups.principal if found else None,
        }
        d['key'] = (
            -len(found),
            0 if par.ring else 1,
            -len(mult),
            -len(par.atoms),
            -len(double),
            principal_locs,
            all_mult,
            double,
            -(len(prefixes) + len(n_prefixes)),
            pref_locs,
        )
        p = self.groups.principal
        if p == 'amine':  # an N with several carbons is one group
            on_parent, total = len({f[2] for f in found}), len(self.groups.amines)
        else:
            on_parent, total = len(found), len(self.groups.principal_sites())
        if p and found and on_parent < total:
            # principal groups outside the parent would need prefixes of the same kind: not supported
            raise Unsupported('principal groups outside the parent')
        return d

    def _substituent(self, a, j, parent_atoms, found):
        g = self.g
        s = g.sym[j]
        if s in HALO:
            return ('halo', s)
        if j in g.nitro:
            return ('nitro',)
        if s == 'O':
            o = g.adj[a][j]
            if o == 2:
                return None  # oxo of the parent atom itself: handled as the atom's kind
            if g.h[j] == 1:
                return ('hydroxy',)
            other = next(k for k in g.adj[j] if k != a)
            return ('alkoxy', self._branch(j, other))
        if s == 'N':
            if g.adj[a][j] == 3:
                raise Unsupported('nitrile N on a parent atom')
            if g.h[j] == 2:
                return ('amino',)
            raise Unsupported('substituted amino prefix')
        # carbon
        kind = self.groups.kind.get(j)
        if kind == 'acid':
            return ('carboxy',)
        if kind == 'nitrile':
            return ('cyano',)
        if kind == 'aldehyde':
            return ('formyl',)
        if kind in ('amide', 'ester'):
            raise Unsupported('amide/ester prefix')
        return self._branch(a, j)

    def _branch(self, attach, root):
        """A substituent starting at atom root (bonded to attach): alkyl, ring (phenyl, cycloalkyl).
        Memoised: every candidate parent asks for the same branches again (icosane: 30 s -> 0.1 s)."""
        cache = self.__dict__.setdefault('_branches', {})
        if (attach, root) not in cache:
            try:
                cache[attach, root] = self._branch_uncached(attach, root)
            except Unsupported as exc:
                cache[attach, root] = exc
        found = cache[attach, root]
        if isinstance(found, Unsupported):
            raise found
        return found

    def _branch_uncached(self, attach, root):
        g = self.g
        if g.sym[root] != 'C':
            raise Unsupported('heteroatom substituent')
        if root in self.ring_of:
            ring = list(self.ring_of[root])
            # numbering from the attachment atom, both directions
            k = ring.index(root)
            orders = [ring[k:] + ring[:k], [ring[k]] + ring[:k][::-1] + ring[k + 1 :][::-1]]
            best = None
            for order in orders:
                par = Parent(True, order)
                d = self._sub_description(par, attach)
                if best is None or d['key'] < best['key']:
                    best = d
            return ('ring', best)
        # acyclic: chains from root
        seen = {attach}
        best = None
        stack = [(root, [root])]
        while stack:
            node, path = stack.pop()
            try:
                d = self._sub_description(Parent(False, path), attach)
            except Unsupported:
                d = None  # e.g. a vinyl group cut inside its double bond; a longer path may do
            if d is not None and (best is None or d['key'] < best['key']):
                best = d
            for nxt in g.adj[node]:
                if (
                    g.sym[nxt] == 'C'
                    and nxt not in path
                    and nxt not in seen
                    and nxt not in self.ring_of
                    and self.groups.kind.get(nxt) is None
                ):
                    stack.append((nxt, path + [nxt]))
        if best is None:
            raise Unsupported('substituent')
        return ('alkyl', best)

    def _sub_description(self, par, attach):
        g = self.g
        if len(par.atoms) > len(STEMS['en']):
            raise Unsupported('substituent longer than icosyl')
        atoms = set(par.atoms)
        mult = []
        for k, a in enumerate(par.atoms):
            last = k + 1 >= len(par.atoms)
            if par.ring or not last:
                nxt = par.atoms[(k + 1) % len(par.atoms)]
                o = g.adj[a][nxt]
                if o in (2, 3):
                    mult.append((min(par.loc[a], par.loc[nxt]), o))
            for j, o in g.adj[a].items():
                if j == attach and a == par.atoms[0]:
                    if o != 1:
                        raise Unsupported('ylidene')
                    continue
                if g.sym[j] == 'C' and j not in atoms and o >= 2:
                    raise Unsupported('exocyclic multiple bond')
        benzene = (
            par.ring
            and len(par.atoms) == 6
            and all(g.adj[a][par.atoms[(k + 1) % 6]] == 1.5 for k, a in enumerate(par.atoms))
        )
        if benzene:
            mult = []
        prefixes = []
        for a in par.atoms:
            for j in g.adj[a]:
                if j in atoms or (j == attach and a == par.atoms[0]):
                    continue
                d = self._substituent_in_branch(a, j)
                prefixes.append((par.loc[a], d))
            if self.groups.kind.get(a) is not None:
                raise Unsupported('group inside a substituent')
        double = sorted(l for l, o in mult if o == 2)
        d = {'parent': par, 'benzene': benzene, 'mult': sorted(mult), 'prefixes': prefixes}
        d['key'] = (
            -len(mult),
            -len(par.atoms),
            -len(double),
            sorted(l for l, _ in mult),
            double,
            -len(prefixes),
            sorted(l for l, _ in prefixes),
        )
        return d

    def _substituent_in_branch(self, a, j):
        g = self.g
        s = g.sym[j]
        if s in HALO:
            return ('halo', s)
        if j in g.nitro:
            return ('nitro',)
        if s == 'O' and g.adj[a][j] == 1 and g.h[j] == 1:
            return ('hydroxy',)
        if s == 'N' and g.h[j] == 2 and g.adj[a][j] == 1:
            return ('amino',)
        if s == 'C':
            if self.groups.kind.get(j) is not None:
                raise Unsupported('group in a substituent')
            return self._branch(a, j)
        raise Unsupported('substituent in a branch')

    def _ester(self):
        g, groups = self.g, self.groups
        c = next(c for c, k in groups.kind.items() if k == 'ester')
        o = groups.ester_o[c]
        alkyl_root = next(k for k in g.adj[o] if k != c)
        sites = [(c, 'ester')]
        alkyl = self._branch(o, alkyl_root)
        acid_c = [k for k in g.adj[c] if g.sym[k] == 'C']
        if acid_c and acid_c[0] in self.ring_of:  # only methyl benzoate and the like
            ring = self.ring_of[acid_c[0]]
            atoms = {a for a in ring} | {c, o} | {j for j, x in g.adj[c].items() if x == 2}
            bare = all(j in atoms or g.sym[j] == 'H' for a in ring for j in g.adj[a])
            benzene = len(ring) == 6 and all(g.adj[ring[i]][ring[(i + 1) % 6]] == 1.5 for i in range(6))
            if benzene and bare:
                return [{'retained_ester': True, 'ester_alkyl': alkyl, 'key': ()}]
            raise Unsupported('ester of a ring acid')
        best = []
        for chain in _chains(g, groups, self.rings):
            if c not in chain:
                continue
            for order in _numberings(chain, False):
                if order[0] != c:
                    continue
                try:
                    d = self._parent_description(Parent(False, order), sites)
                except Unsupported:
                    continue
                d['ester_alkyl'] = alkyl
                d['principal'] = 'ester'
                if not best or d['key'] < best[0]['key']:
                    best = [d]
                elif d['key'] == best[0]['key']:
                    best.append(d)
        if not best:
            raise Unsupported('ester')
        return best


# -- 4. rendering ---------------------------------------------------------------------------------------
STEMS = {
    'en': [
        'meth',
        'eth',
        'prop',
        'but',
        'pent',
        'hex',
        'hept',
        'oct',
        'non',
        'dec',
        'undec',
        'dodec',
        'tridec',
        'tetradec',
        'pentadec',
        'hexadec',
        'heptadec',
        'octadec',
        'nonadec',
        'icos',
    ],
    'ru': [
        'мет',
        'эт',
        'проп',
        'бут',
        'пент',
        'гекс',
        'гепт',
        'окт',
        'нон',
        'дек',
        'ундек',
        'додек',
        'тридек',
        'тетрадек',
        'пентадек',
        'гексадек',
        'гептадек',
        'октадек',
        'нонадек',
        'эйкоз',
    ],
    'zh': [
        '甲',
        '乙',
        '丙',
        '丁',
        '戊',
        '己',
        '庚',
        '辛',
        '壬',
        '癸',
        '十一',
        '十二',
        '十三',
        '十四',
        '十五',
        '十六',
        '十七',
        '十八',
        '十九',
        '二十',
    ],
}
MULT = {
    'en': ['', 'di', 'tri', 'tetra', 'penta', 'hexa', 'hepta', 'octa'],
    'ru': ['', 'ди', 'три', 'тетра', 'пента', 'гекса', 'гепта', 'окта'],
    'zh': ['', '二', '三', '四', '五', '六', '七', '八'],
}
SIMPLE = {
    'fluoro': ('фтор', 'fluoro', '氟'),
    'chloro': ('хлор', 'chloro', '氯'),
    'bromo': ('бром', 'bromo', '溴'),
    'iodo': ('иод', 'iodo', '碘'),
    'nitro': ('нитро', 'nitro', '硝基'),
    'hydroxy': ('гидрокси', 'hydroxy', '羟基'),
    'amino': ('амино', 'amino', '氨基'),
    'oxo': ('оксо', 'oxo', '氧代'),
    'formyl': ('формил', 'formyl', '甲酰基'),
    'carboxy': ('карбокси', 'carboxy', '羧基'),
    'cyano': ('циано', 'cyano', '氰基'),
}
RETAINED_ALKYL = {  # (chain length, sorted methyl locants) -> names
    (2, (1,)): ('изопропил', 'isopropyl', '异丙基', 'изопроп', 'isoprop', '异丙'),
    (3, (2,)): ('изобутил', 'isobutyl', '异丁基', 'изобут', 'isobut', '异丁'),
    (3, (1,)): ('втор-бутил', 'sec-butyl', '仲丁基', 'втор-бут', 'sec-but', '仲丁'),
    (2, (1, 1)): ('трет-бутил', 'tert-butyl', '叔丁基', 'трет-бут', 'tert-but', '叔丁'),
}
# principal suffixes: (in chain / on a ring atom, attached to a ring)
SUFFIX = {
    'acid': {'en': ('oic acid', 'carboxylic acid'), 'ru': ('овая кислота', 'карбоновая кислота'), 'zh': ('酸', '甲酸')},
    'amide': {'en': ('amide', 'carboxamide'), 'ru': ('амид', 'карбоксамид'), 'zh': ('酰胺', '甲酰胺')},
    'nitrile': {'en': ('nitrile', 'carbonitrile'), 'ru': ('нитрил', 'карбонитрил'), 'zh': ('腈', '甲腈')},
    'aldehyde': {'en': ('al', 'carbaldehyde'), 'ru': ('аль', 'карбальдегид'), 'zh': ('醛', '甲醛')},
    'ketone': {'en': ('one', None), 'ru': ('он', None), 'zh': ('酮', None)},
    'alcohol': {'en': ('ol', None), 'ru': ('ол', None), 'zh': ('醇', None)},
    'amine': {'en': ('amine', None), 'ru': ('амин', None), 'zh': ('胺', None)},
}
BENZENE_RETAINED = {  # one principal group on benzene
    'alcohol': ('фенол', 'phenol', '苯酚'),
    'amine': ('анилин', 'aniline', '苯胺'),
    'acid': ('бензойная кислота', 'benzoic acid', '苯甲酸'),
    'aldehyde': ('бензальдегид', 'benzaldehyde', '苯甲醛'),
    'nitrile': ('бензонитрил', 'benzonitrile', '苯甲腈'),
    'amide': ('бензамид', 'benzamide', '苯甲酰胺'),
}
LI = {'ru': 0, 'en': 1, 'zh': 2}


def _locs(locs):
    """'N,N,2' / '1,3': nitrogen locants first, then the numbers."""
    return ','.join(str(x) for x in sorted(locs, key=lambda x: (0, 0) if x == 'N' else (1, x)))


class Renderer:
    def __init__(self, lang):
        if lang not in LANGS:
            raise ValueError(f'unknown language {lang!r}')
        self.lang = lang
        self.li = LI[lang]

    # -- substituent names -------------------------------------------------------------------------
    def prefix_name(self, d):
        """(name, alphabetisation key, zh order key, complex?) of a prefix descriptor."""
        kind = d[0]
        if kind == 'halo':
            key = HALO[d[1]]
            name = SIMPLE[key][self.li]
            return name, name, (Z[d[1]], 0, name), False
        if kind in SIMPLE:
            name = SIMPLE[kind][self.li]
            z = {'nitro': 7, 'amino': 7, 'hydroxy': 8, 'oxo': 8, 'formyl': 6, 'carboxy': 6, 'cyano': 6}[kind]
            return name, name, (z, 1, name), False
        if kind == 'alkoxy':
            return self.alkoxy(d[1])
        if kind in ('alkyl', 'ring'):
            name, complex_ = self.substituent(d)
            size = len(d[1]['parent'].atoms)
            alpha = name.replace('втор-', '').replace('трет-', '').replace('sec-', '').replace('tert-', '')
            return name, alpha.strip('()'), (6, size, name), complex_
        raise Unsupported(kind)

    def substituent(self, d):
        """Name of an alkyl or ring substituent; complex ones in parentheses."""
        kind, desc = d
        par = desc['parent']
        n = len(par.atoms)
        L = self.lang
        pre = desc['prefixes']
        if kind == 'ring':
            if desc['benzene']:
                base = {'ru': 'фенил', 'en': 'phenyl', 'zh': '苯基'}[L]
            else:
                base = self._cyclo(n, desc['mult'], 'yl')
        else:
            methyls = tuple(
                sorted(
                    loc
                    for loc, x in pre
                    if x[0] == 'alkyl' and len(x[1]['parent'].atoms) == 1 and not x[1]['prefixes'] and not x[1]['mult']
                )
            )
            if not desc['mult'] and methyls and len(methyls) == len(pre) and (n, methyls) in RETAINED_ALKYL:
                return RETAINED_ALKYL[(n, methyls)][self.li], False
            base = self._chain(n, desc['mult'], 'yl')
        if not pre:
            return base, False
        text = self._prefix_block(pre, n, ring=kind == 'ring', omit=n == 1)  # chloromethyl, not 1-chloromethyl
        name = text + ('-' if base[0].isdigit() else '') + base
        return '(' + name + ')', True

    def alkoxy(self, desc):
        kind, d = desc
        L = self.lang
        if kind != 'alkyl' or d['mult']:
            raise Unsupported('alkoxy')
        n = len(d['parent'].atoms)
        pre = d['prefixes']
        if not pre:
            name = {
                'ru': STEMS['ru'][n - 1] + 'окси',
                'en': STEMS['en'][n - 1] + 'oxy',
                'zh': STEMS['zh'][n - 1] + '氧基',
            }[L]
            if L == 'en' and n > 4:
                name = STEMS['en'][n - 1] + 'yloxy'
            if L == 'ru' and n > 4:
                name = STEMS['ru'][n - 1] + 'илокси'
            return name, name, (8, n, name), False
        methyls = tuple(sorted(loc for loc, x in pre if x[0] == 'alkyl' and len(x[1]['parent'].atoms) == 1))
        if (n, methyls) == (2, (1,)) and len(pre) == 1:
            name = {'ru': 'изопропокси', 'en': 'isopropoxy', 'zh': '异丙氧基'}[L]
            return name, name, (8, 3, name), False
        raise Unsupported('complex alkoxy')

    # -- parent hydrides --------------------------------------------------------------------------
    def _unsat(self, n, mult, ring, bare=True):
        """(euphonic 'a', unsaturation text) for en/ru: 'an' / '-2-en' / 'a-1,3-dien' / '-1-en-3-yn'."""
        L = self.lang
        enes = [l for l, o in mult if o == 2]
        ynes = [l for l, o in mult if o == 3]
        if not enes and not ynes:
            return {'en': 'an', 'ru': 'ан'}[L]
        omit = (n <= 3 and len(mult) == 1 and not ring and bare) or (n == 2) or (ring and len(mult) == 1 and bare)
        parts = []
        first = True
        for locs, word in ((enes, {'en': 'en', 'ru': 'ен'}[L]), (ynes, {'en': 'yn', 'ru': 'ин'}[L])):
            if not locs:
                continue
            m = MULT[L][len(locs) - 1]
            a = 'a' if (first and m and L == 'en') else ('а' if (first and m and L == 'ru') else '')
            if omit:
                parts.append(a + m + word)
            else:
                parts.append(a + '-' + _locs(locs) + '-' + m + word)
            first = False
        return ''.join(parts)

    def _chain(self, n, mult, ending, bare=True):
        L = self.lang
        stem = STEMS[L][n - 1]
        if L == 'zh':
            if ending != 'yl':
                raise AssertionError('zh parents are built in _zh')
            enes = [l for l, o in mult if o == 2]
            ynes = [l for l, o in mult if o == 3]
            if not enes and not ynes:
                return stem + '基'
            return self._zh_unsat(stem, enes, ynes, n == 2, tail=True) + '基'
        u = self._unsat(n, mult, False, bare and ending != 'yl')
        if ending == 'yl':
            if u in ('an', 'ан'):
                return stem + ('yl' if L == 'en' else 'ил')
            return stem + u + ('yl' if L == 'en' else 'ил')
        return stem + u

    def _cyclo(self, n, mult, ending, bare=True):
        L = self.lang
        if L == 'zh':
            stem = '环' + STEMS['zh'][n - 1]
            if ending == 'yl':
                return stem + ('基' if not mult else '烯基')
            return stem
        stem = ('cyclo' if L == 'en' else 'цикло') + STEMS[L][n - 1]
        u = self._unsat(n, mult, True, bare and ending != 'yl')
        if ending == 'yl':
            return stem + (u if u not in ('an', 'ан') else '') + ('yl' if L == 'en' else 'ил')
        return stem + u

    def _prefix_block(self, prefixes, n, ring, omit):
        """'2-chloro-3-methyl' / '2-метил-3-хлор' / zh '2-甲基-3-氯' from [(locant, descriptor)]."""
        L = self.lang
        named = {}
        for loc, d in prefixes:
            name, alpha, zkey, complex_ = self.prefix_name(d)
            entry = named.setdefault(name, {'locs': [], 'alpha': alpha, 'z': zkey, 'complex': complex_})
            entry['locs'].append(loc)
        if L == 'zh':
            items = sorted(named.items(), key=lambda kv: kv[1]['z'])
        else:
            items = sorted(named.items(), key=lambda kv: kv[1]['alpha'].lower())
        parts = []
        for name, e in items:
            count = len(e['locs'])
            if e['complex']:
                m = {
                    'en': ['', 'bis', 'tris', 'tetrakis'],
                    'ru': ['', 'бис', 'трис', 'тетракис'],
                    'zh': ['', '二', '三', '四'],
                }[L][count - 1]
            else:
                m = MULT[L][count - 1]
            if omit and 'N' not in e['locs']:
                parts.append(m + name)
            else:
                parts.append(_locs(e['locs']) + '-' + m + name)
        out = ''
        for k, part in enumerate(parts):
            if k and (part[0].isdigit() or part[0] == 'N'):
                out += '-'
            out += part
        return out

    # -- whole names ---------------------------------------------------------------------------------
    def pick(self, ties):
        """Last rule of numbering: the lowest locants to the prefix cited first in this language."""

        def order(d):
            if 'prefixes' not in d:
                return []
            named = {}
            for loc, x in d['prefixes']:
                name, alpha, zkey, _ = self.prefix_name(x)
                named.setdefault(name, [alpha, zkey, []])[2].append(loc)
            key = (lambda v: v[1]) if self.lang == 'zh' else (lambda v: v[0].lower())
            return [loc for v in sorted(named.values(), key=key) for loc in sorted(v[2])]

        return min(ties, key=order)

    def render(self, d):
        if 'retained' in d:
            return d['retained'][self.li]
        if d.get('principal') == 'ester' or d.get('retained_ester'):
            return self._ester(d)
        L = self.lang
        par = d['parent']
        n = len(par.atoms)
        found = d['found']
        prefixes = list(d['prefixes'])
        n_pre = d['n_prefixes']
        if d['benzene']:
            return self._benzene(d)
        # locant omission
        total_sub = len(prefixes) + len(found) + len(n_pre)
        omit_pre = (
            (n == 1) or (n == 2 and not par.ring and total_sub == 1) or (par.ring and total_sub == 1 and not d['mult'])
        )
        if L == 'zh':
            return self._zh(d, omit_pre)
        everything = prefixes + list(n_pre)  # N-alkyl groups are alphabetised with the others
        text = self._prefix_block(everything, n, par.ring, omit_pre) if everything else ''
        parent = self._parent_with_suffix(d)
        if text and parent[0].isdigit():
            text += '-'
        return text + parent

    def _parent_with_suffix(self, d):
        L = self.lang
        par = d['parent']
        n = len(par.atoms)
        found = d['found']
        p = d['principal']
        if par.ring:
            base = self._cyclo(n, d['mult'], '', bare=not found)
        else:
            base = self._chain(n, d['mult'], '', bare=not found and not d['prefixes'] and not d['n_prefixes'])
        if not found:
            return base + ('e' if L == 'en' else '')
        mode = 'attached' if found[0][3] == 'attached' else 'in'
        word = SUFFIX[p][L][1 if mode == 'attached' else 0]
        locs = [par.loc[f[0]] for f in found]
        count = len(found)
        m = MULT[L][count - 1]
        terminal = p in TERMINAL and mode == 'in'
        omit = (
            terminal
            or (n <= 2 and count == 1)
            or (par.ring and count == 1 and not d['mult'] and not d['prefixes'])
            or (mode == 'attached' and count == 1)
        )
        if L == 'en':
            first = (m + word)[0]
            keep_e = first not in 'aeiouy'
            stem = base + ('e' if keep_e else '')
            if p == 'acid' and mode == 'in':
                stem = base + ('' if (m + word)[0] in 'aeiouy' else 'e')
            if omit:
                return stem + m + word
            return stem + '-' + _locs(locs) + '-' + m + word
        # ru
        if omit:
            if p == 'acid' and mode == 'in':
                return base + m + word if m else base + word
            return base + m + word
        if p == 'acid' and mode == 'in':
            return base + m + word
        return base + '-' + _locs(locs) + '-' + m + word

    def _benzene(self, d):
        L = self.lang
        par = d['parent']
        found = d['found']
        p = d['principal']
        prefixes = list(d['prefixes'])
        if found and len(found) == 1 and p in BENZENE_RETAINED:  # 4-chlorophenol, N,N-dimethylaniline
            everything = prefixes + list(d['n_prefixes'])
            block = self._prefix_block(everything, 6, True, False) if everything else ''
            return block + BENZENE_RETAINED[p][self.li]
        if d['n_prefixes']:
            raise Unsupported('N-substituted benzenediamine')
        if found:
            if p not in ('alcohol', 'amine'):
                raise Unsupported('several C-groups on benzene')
            # benzene-1,2-diol
            locs = sorted(par.loc[f[0]] for f in found)
            m = MULT[L][len(found) - 1]
            block = self._prefix_block(prefixes, 6, True, False) if prefixes else ''
            if L == 'zh':
                word = {'alcohol': '苯' + m + '酚', 'amine': '苯' + m + '胺'}[p]
                return (block + '-' if block else '') + _locs(locs) + '-' + word
            word = SUFFIX[p][L][0]
            base = {'en': 'benzene', 'ru': 'бензол'}[L]
            return (
                block + ('-' if block else '') + base + '-' + _locs(locs) + '-' + m + word
                if block
                else base + '-' + _locs(locs) + '-' + m + word
            )
        # substituted benzene
        if L == 'zh':
            return self._zh_benzene(prefixes)
        base = {'en': 'benzene', 'ru': 'бензол'}[L]
        if not prefixes:
            return base
        omit = len(prefixes) == 1
        return self._prefix_block(prefixes, 6, True, omit) + base

    def _zh_benzene(self, prefixes):
        if not prefixes:
            return '苯'
        if len(prefixes) == 1 and prefixes[0][1][0] == 'alkyl':
            only = prefixes[0][1][1]
            if len(only['parent'].atoms) == 2 and only['mult'] == [(1, 2)] and not only['prefixes']:
                return '苯乙烯'  # styrene: the name used in Chinese
        omit = len(prefixes) == 1
        # alkylbenzenes: 甲苯, 乙苯, 1,2-二甲苯 (the 基 of an alkyl is dropped before 苯)
        block = self._prefix_block(prefixes, 6, True, omit)
        if (
            all(d[0] == 'alkyl' and not d[1]['mult'] for _, d in prefixes)
            and len({self.prefix_name(d)[0] for _, d in prefixes}) == 1
        ):
            block = block[:-1] if block.endswith('基') else block
        return block + '苯'

    def _zh(self, d, omit_pre):
        par = d['parent']
        n = len(par.atoms)
        found = d['found']
        p = d['principal']
        prefixes = d['prefixes']
        everything = list(prefixes) + list(d['n_prefixes'])
        block = self._prefix_block(everything, n, par.ring, omit_pre) if everything else ''
        if len(everything) == 1 and everything[0][1][0] == 'ring' and everything[0][1][1]['benzene']:
            if not everything[0][1][1]['prefixes'] and not par.ring and n <= 2:
                # ASSUMPTION (common usage): 苯甲醇, 苯甲胺, 苯乙酮, 2-苯乙醇 rather than 苯基甲醇
                block = '苯' if n == 1 or p == 'ketone' else f'{everything[0][0]}-苯'
        stem = ('环' if par.ring else '') + STEMS['zh'][n - 1]
        enes = [l for l, o in d['mult'] if o == 2]
        ynes = [l for l, o in d['mult'] if o == 3]
        one = len(d['mult']) == 1
        omit_u = (
            n == 2
            or (par.ring and one and not found)
            or (not par.ring and n <= 3 and one and not prefixes and (not found or p in TERMINAL))
        )  # ASSUMPTION: 丙烯, 丙烯醛, 丙烯酸 as in common use, 2-丙烯-1-醇
        if not found:
            if not enes and not ynes:
                core = stem + '烷'
            else:
                core = self._zh_unsat(stem, enes, ynes, omit_u, tail=True)
            return (block + '-' if block and core[0].isdigit() else block) + core
        mode = 'attached' if found[0][3] == 'attached' else 'in'
        word = SUFFIX[p]['zh'][1 if mode == 'attached' else 0]
        count = len(found)
        m = MULT['zh'][count - 1]
        locs = _locs(par.loc[f[0]] for f in found)
        terminal = p in TERMINAL and mode == 'in'
        omit_s = (
            terminal or n <= 2 or mode == 'attached' or (par.ring and count == 1 and not d['mult'] and not prefixes)
        )
        if p == 'ketone' and n == 3 and not enes and not ynes:
            omit_s = True  # 丙酮
        if mode == 'attached':
            core = stem + '烷' + word if not d['mult'] else self._zh_unsat(stem, enes, ynes, omit_u, tail=True) + word
        elif not enes and not ynes:
            core = (stem + m + word) if omit_s else (locs + '-' + stem + m + word)
        else:
            u = self._zh_unsat(stem, enes, ynes, omit_u, tail=False)
            core = u + ('' if omit_s else '-' + locs + '-') + m + word
        if p == 'amide' and mode == 'in':
            core = core.replace('酰胺', '酰胺')
        return (block + '-' if block and core[0].isdigit() else block) + core

    def _zh_unsat(self, stem, enes, ynes, omit, tail):
        out = ''
        if enes:
            m = MULT['zh'][len(enes) - 1]
            out = (stem + m + '烯') if omit else (_locs(enes) + '-' + stem + m + '烯')
        if ynes:
            m = MULT['zh'][len(ynes) - 1]
            if out:
                out += ('' if omit else '-' + _locs(ynes) + '-') + m + '炔'
            else:
                out = (stem + m + '炔') if omit else (_locs(ynes) + '-' + stem + m + '炔')
        return out

    def _ester(self, d):
        L = self.lang
        alkyl_name, _ = self.substituent(d['ester_alkyl'])
        if d.get('retained_ester'):
            if L == 'zh':
                return '苯甲酸' + (alkyl_name[:-1] if alkyl_name.endswith('基') else alkyl_name) + '酯'
            return alkyl_name + (' benzoate' if L == 'en' else 'бензоат')
        acid = dict(d)
        acid['principal'] = 'acid'
        par = d['parent']
        n = len(par.atoms)
        if L == 'zh':
            acid_name = self._zh(acid, n <= 2 and len(d['prefixes']) <= 1)
            alk = alkyl_name[:-1] if alkyl_name.endswith('基') else alkyl_name
            return acid_name + alk + '酯'
        block = self._prefix_block(d['prefixes'], n, False, n <= 2 and len(d['prefixes']) <= 1) if d['prefixes'] else ''
        base = self._chain(n, d['mult'], '', bare=False)
        if L == 'en':
            acid_part = base + 'oate'
            if block and block[-1].isdigit():
                block += '-'
            return alkyl_name + ' ' + block + acid_part
        acid_part = base + 'оат'
        if block and block[-1].isdigit():
            block += '-'
        return alkyl_name + ('-' if block[:1].isdigit() else '') + block + acid_part


def name(molecule, lang='ru'):
    renderer = Renderer(lang)
    try:
        g = Graph(molecule)
        names = [renderer.render(renderer.pick(Naming(g, comp).describe())) for comp in g.components()]
        counts = Counter(names)  # the form of names.name: '2 × метан'
        return ' + '.join(
            f'{c} × {n}' if c > 1 else n for n, c in sorted(counts.items(), key=lambda x: names.index(x[0]))
        )
    except Unsupported:
        return None

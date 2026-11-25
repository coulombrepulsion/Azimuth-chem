"""Names of common molecules for the Compass status line.

A structure is recognised by its connectivity: the atoms (hydrogens explicit) and which atoms are
bonded, not the bond orders or the geometry. The reference structures are written as SMILES in
NAMES below and parsed by the small reader in this file (organic subset, branches, ring closures,
aromatic lower-case atoms, [bracket] atoms with H counts). Two graphs are compared by a
Weisfeiler–Lehman colour refinement, enough for the small molecules of the table. A structure of
several pieces gets the names of its pieces joined by " + "; anything not in the table has no name
and the caller shows only the formula. This is a lookup of known molecules, not a general IUPAC
nomenclature generator.
"""

import re
from collections import Counter

# SMILES, Russian (IUPAC, then the common name), English, Chinese
NAMES = [
    ('O', 'вода', 'water', '水'),
    ('[H][H]', 'водород', 'hydrogen', '氢气'),
    ('O=O', 'кислород', 'oxygen', '氧气'),
    ('N#N', 'азот', 'nitrogen', '氮气'),
    ('FF', 'фтор', 'fluorine', '氟气'),
    ('ClCl', 'хлор', 'chlorine', '氯气'),
    ('[C-]#[O+]', 'монооксид углерода (угарный газ)', 'carbon monoxide', '一氧化碳'),
    ('O=C=O', 'диоксид углерода', 'carbon dioxide', '二氧化碳'),
    ('O=[O+][O-]', 'озон', 'ozone', '臭氧'),
    ('N', 'аммиак', 'ammonia', '氨'),
    ('NN', 'гидразин', 'hydrazine', '肼'),
    ('OO', 'пероксид водорода', 'hydrogen peroxide', '过氧化氢'),
    ('S', 'сероводород', 'hydrogen sulfide', '硫化氢'),
    ('F', 'фтороводород', 'hydrogen fluoride', '氟化氢'),
    ('Cl', 'хлороводород', 'hydrogen chloride', '氯化氢'),
    ('Br', 'бромоводород', 'hydrogen bromide', '溴化氢'),
    ('C#N', 'циановодород', 'hydrogen cyanide', '氰化氢'),
    ('O=S=O', 'диоксид серы', 'sulfur dioxide', '二氧化硫'),
    ('O=S(=O)=O', 'триоксид серы', 'sulfur trioxide', '三氧化硫'),
    ('[N]=O', 'монооксид азота', 'nitric oxide', '一氧化氮'),
    ('O=[N]=O', 'диоксид азота', 'nitrogen dioxide', '二氧化氮'),
    ('P', 'фосфин', 'phosphine', '膦'),
    ('B(F)(F)F', 'трифторид бора', 'boron trifluoride', '三氟化硼'),
    ('OS(=O)(=O)O', 'серная кислота', 'sulfuric acid', '硫酸'),
    ('O[N+](=O)[O-]', 'азотная кислота', 'nitric acid', '硝酸'),
    ('C', 'метан', 'methane', '甲烷'),
    ('CC', 'этан', 'ethane', '乙烷'),
    ('CCC', 'пропан', 'propane', '丙烷'),
    ('CCCC', 'бутан', 'butane', '丁烷'),
    ('CC(C)C', '2-метилпропан (изобутан)', '2-methylpropane (isobutane)', '2-甲基丙烷（异丁烷）'),
    ('CCCCC', 'пентан', 'pentane', '戊烷'),
    ('CCCCCC', 'гексан', 'hexane', '己烷'),
    ('C=C', 'этен (этилен)', 'ethene (ethylene)', '乙烯'),
    ('C=CC', 'пропен', 'propene', '丙烯'),
    ('C=CC=C', 'бута-1,3-диен', 'buta-1,3-diene', '1,3-丁二烯'),
    ('C#C', 'этин (ацетилен)', 'ethyne (acetylene)', '乙炔'),
    ('C1CC1', 'циклопропан', 'cyclopropane', '环丙烷'),
    ('C1CCC1', 'циклобутан', 'cyclobutane', '环丁烷'),
    ('C1CCCC1', 'циклопентан', 'cyclopentane', '环戊烷'),
    ('C1CCCCC1', 'циклогексан', 'cyclohexane', '环己烷'),
    ('c1ccccc1', 'бензол', 'benzene', '苯'),
    ('Cc1ccccc1', 'метилбензол (толуол)', 'methylbenzene (toluene)', '甲苯'),
    ('Oc1ccccc1', 'фенол', 'phenol', '苯酚'),
    ('Nc1ccccc1', 'анилин', 'aniline', '苯胺'),
    ('c1ccncc1', 'пиридин', 'pyridine', '吡啶'),
    ('c1cc[nH]c1', 'пиррол', 'pyrrole', '吡咯'),
    ('c1ccoc1', 'фуран', 'furan', '呋喃'),
    ('c1ccsc1', 'тиофен', 'thiophene', '噻吩'),
    ('c1ccc2ccccc2c1', 'нафталин', 'naphthalene', '萘'),
    ('CO', 'метанол', 'methanol', '甲醇'),
    ('CCO', 'этанол', 'ethanol', '乙醇'),
    ('CCCO', 'пропан-1-ол', 'propan-1-ol', '1-丙醇'),
    ('CC(C)O', 'пропан-2-ол (изопропанол)', 'propan-2-ol (isopropanol)', '2-丙醇（异丙醇）'),
    ('OCCO', 'этан-1,2-диол (этиленгликоль)', 'ethane-1,2-diol (ethylene glycol)', '乙二醇'),
    ('OCC(O)CO', 'пропан-1,2,3-триол (глицерин)', 'propane-1,2,3-triol (glycerol)', '丙三醇（甘油）'),
    ('COC', 'метоксиметан (диметиловый эфир)', 'methoxymethane (dimethyl ether)', '甲醚（二甲醚）'),
    ('CCOCC', 'этоксиэтан (диэтиловый эфир)', 'ethoxyethane (diethyl ether)', '乙醚'),
    ('C=O', 'метаналь (формальдегид)', 'methanal (formaldehyde)', '甲醛'),
    ('CC=O', 'этаналь (ацетальдегид)', 'ethanal (acetaldehyde)', '乙醛'),
    ('CC(C)=O', 'пропан-2-он (ацетон)', 'propan-2-one (acetone)', '丙酮'),
    ('OC=O', 'метановая (муравьиная) кислота', 'methanoic (formic) acid', '甲酸'),
    ('CC(O)=O', 'этановая (уксусная) кислота', 'ethanoic (acetic) acid', '乙酸'),
    ('CCOC(C)=O', 'этилэтаноат (этилацетат)', 'ethyl ethanoate (ethyl acetate)', '乙酸乙酯'),
    ('NC=O', 'метанамид (формамид)', 'methanamide (formamide)', '甲酰胺'),
    ('CC(N)=O', 'этанамид (ацетамид)', 'ethanamide (acetamide)', '乙酰胺'),
    ('NC(N)=O', 'мочевина', 'urea', '尿素'),
    ('NCC(O)=O', 'глицин', 'glycine', '甘氨酸'),
    ('CC(N)C(O)=O', 'аланин', 'alanine', '丙氨酸'),
    ('CN', 'метанамин (метиламин)', 'methanamine (methylamine)', '甲胺'),
    ('CNC', 'N-метилметанамин (диметиламин)', 'N-methylmethanamine (dimethylamine)', '二甲胺'),
    ('CN(C)C', 'N,N-диметилметанамин (триметиламин)', 'N,N-dimethylmethanamine (trimethylamine)', '三甲胺'),
    ('CC#N', 'этаннитрил (ацетонитрил)', 'ethanenitrile (acetonitrile)', '乙腈'),
    ('C[N+](=O)[O-]', 'нитрометан', 'nitromethane', '硝基甲烷'),
    ('CS(C)=O', 'диметилсульфоксид', 'dimethyl sulfoxide', '二甲基亚砜'),
    ('CS', 'метантиол', 'methanethiol', '甲硫醇'),
    ('CF', 'фторметан', 'fluoromethane', '氟甲烷'),
    ('CCl', 'хлорметан', 'chloromethane', '氯甲烷'),
    ('ClCCl', 'дихлорметан', 'dichloromethane', '二氯甲烷'),
    ('ClC(Cl)Cl', 'трихлорметан (хлороформ)', 'trichloromethane (chloroform)', '三氯甲烷（氯仿）'),
    ('ClC(Cl)(Cl)Cl', 'тетрахлорметан', 'tetrachloromethane', '四氯化碳'),
    ('FC(F)(F)F', 'тетрафторметан', 'tetrafluoromethane', '四氟化碳'),
    ('CBr', 'бромметан', 'bromomethane', '溴甲烷'),
    ('CCCl', 'хлорэтан', 'chloroethane', '氯乙烷'),
    ('C=CCl', 'хлорэтен (винилхлорид)', 'chloroethene (vinyl chloride)', '氯乙烯'),
    ('ClC(Cl)=O', 'карбонилдихлорид (фосген)', 'carbonyl dichloride (phosgene)', '光气'),
    ('C1CO1', 'оксиран', 'oxirane', '环氧乙烷'),
    ('C1CCOC1', 'оксолан (тетрагидрофуран)', 'oxolane (tetrahydrofuran)', '四氢呋喃'),
    ('C1COCCO1', '1,4-диоксан', '1,4-dioxane', '1,4-二氧六环'),
    ('O=Cc1ccccc1', 'бензальдегид', 'benzaldehyde', '苯甲醛'),
    ('OC(=O)c1ccccc1', 'бензойная кислота', 'benzoic acid', '苯甲酸'),
    ('Clc1ccccc1', 'хлорбензол', 'chlorobenzene', '氯苯'),
    ('[O-][N+](=O)c1ccccc1', 'нитробензол', 'nitrobenzene', '硝基苯'),
    ('CC=CC', 'бут-2-ен', 'but-2-ene', '2-丁烯'),
    ('C=CCC', 'бут-1-ен', 'but-1-ene', '1-丁烯'),
    ('CC#CC', 'бут-2-ин', 'but-2-yne', '2-丁炔'),
    ('C#CC', 'пропин', 'propyne', '丙炔'),
    ('C=C=C', 'пропадиен (аллен)', 'propadiene (allene)', '丙二烯'),
    # the larger library of Compass
    ('C=Cc1ccccc1', 'этенилбензол (стирол)', 'ethenylbenzene (styrene)', '苯乙烯'),
    ('CC(=O)c1ccccc1', '1-фенилэтан-1-он (ацетофенон)', '1-phenylethan-1-one (acetophenone)', '苯乙酮'),
    ('Cc1ccc(C)cc1', '1,4-диметилбензол (п-ксилол)', '1,4-dimethylbenzene (p-xylene)', '对二甲苯'),
    ('c1c[nH]cn1', '1H-имидазол', '1H-imidazole', '咪唑'),
    ('c1cncnc1', 'пиримидин', 'pyrimidine', '嘧啶'),
    ('c1ccc2[nH]ccc2c1', '1H-индол', '1H-indole', '吲哚'),
    ('O=C1C=CC(=O)C=C1', 'циклогекса-2,5-диен-1,4-дион (п-бензохинон)', 'cyclohexa-2,5-diene-1,4-dione (p-benzoquinone)', '对苯醌'),
    ('CC(C)(C)O', '2-метилпропан-2-ол (трет-бутанол)', '2-methylpropan-2-ol (tert-butanol)', '叔丁醇'),
    ('CS(C)(=O)=O', 'диметилсульфон', 'dimethyl sulfone', '二甲基砜'),
    ('OC(=O)C(O)=O', 'этандиовая (щавелевая) кислота', 'ethanedioic (oxalic) acid', '草酸'),
    ('c1ccc2cc3ccccc3cc2c1', 'антрацен', 'anthracene', '蒽'),
    # hypervalent molecules of the library (the builder now gives them octahedral and bipyramidal angles)
    ('FS(F)(F)(F)(F)F', 'гексафторид серы', 'sulfur hexafluoride', '六氟化硫'),
    ('FP(F)(F)(F)F', 'пентафторид фосфора', 'phosphorus pentafluoride', '五氟化磷'),
    ('[OH-]', 'гидроксид-ион', 'hydroxide ion', '氢氧根离子'),
    ('[OH3+]', 'ион гидроксония', 'hydronium ion', '水合氢离子'),
    ('[NH4+]', 'ион аммония', 'ammonium ion', '铵离子'),
    ('[He]', 'гелий', 'helium', '氦'),
    ('[Ne]', 'неон', 'neon', '氖'),
    ('[Ar]', 'аргон', 'argon', '氩'),
]

VALENCE = {
    'B': (3,),
    'C': (4,),
    'N': (3, 5),
    'O': (2,),
    'P': (3, 5),
    'S': (2, 4, 6),
    'F': (1,),
    'Cl': (1,),
    'Br': (1,),
    'I': (1,),
}
TOKEN = re.compile(r'\[[^\]]+\]|Br|Cl|[BCNOPSFI]|[bcnops]|[=#\-\(\)\./\\]|%\d\d|\d')


def double_bond_stereo(bonds, orders, directed):
    """[(a, j, k, d, 'cis' | 'trans')] for every double bond j=k with a written direction on both sides: a, d — the
    neighbours of j and k joined by «/» or «\\». The direction seen from the double-bond atom outward is that of the
    bond read from it, reversed when the bond was written towards it («F/C» is «C\\F»); the same outward direction on
    both ends is cis (F/C=C\\F), opposite ones trans (F/C=C/F)."""
    outward = {}
    for i, j, s in directed:
        outward.setdefault(i, []).append((j, s))
        outward.setdefault(j, []).append((i, -s))
    found = []
    for (j, k), o in zip(bonds, orders):
        if o != 2 or j not in outward or k not in outward:
            continue
        left = [(a, s) for a, s in outward[j] if a != k]
        right = [(d, s) for d, s in outward[k] if d != j]
        if left and right:
            (a, sa), (d, sd) = left[0], right[0]
            found.append((a, j, k, d, 'cis' if sa == sd else 'trans'))
    return found


def parse_smiles(text):
    """(symbols, bonds) with explicit hydrogens; bonds as (i, j) pairs."""
    symbols, bonds, _ = smiles_graph(text)
    return symbols, bonds


def smiles_graph(text, strict=False, directed=None):
    """(symbols, bonds (i, j), orders) with explicit hydrogens; aromatic bonds have order 1.5.
    strict: a text with characters outside the supported SMILES subset raises ValueError. directed — a list that
    gets (i, j, ±1) for every single bond written «/» (+1) or «\\» (−1) from atom i to atom j (the cis / trans of a
    double bond: double_bond_stereo); a ring closure with a direction is read as a plain single bond."""
    tokens = TOKEN.findall(text)
    if strict and ''.join(tokens) != re.sub(r'\s+', '', text):
        raise ValueError('smiles')
    symbols, bonds, order_sum, explicit_h, aromatic, orders = [], [], [], [], [], []
    stack, rings, prev, order = [], {}, None, 1
    direction = 0
    for token in tokens:
        if token == '.':
            prev, order, direction = None, 1, 0
            continue
        if token in '=#-':
            order = {'=': 2, '#': 3, '-': 1}[token]
            continue
        if token in '/\\':
            order, direction = 1, (1 if token == '/' else -1)
            continue
        if token == '(':
            stack.append(prev)
            continue
        if token == ')':
            if not stack:
                raise ValueError('smiles')
            prev = stack.pop()
            continue
        if token[0] == '%' or token.isdigit():
            if token in rings:
                other, o = rings.pop(token)
                o = max(o, order)
                bonds.append((other, prev))
                w = 1.5 if aromatic[other] and aromatic[prev] and o == 1 else o
                orders.append(w)
                order_sum[other] += w
                order_sum[prev] += w
            else:
                rings[token] = (prev, order)
            order, direction = 1, 0
            continue
        if token.startswith('['):
            m = re.fullmatch(r'\[(\d*)([A-Z][a-z]?|[a-z]{1,2})(H\d*)?([+-]+\d*)?\]', token)
            if m is None:
                raise ValueError('smiles')
            element, h = m.group(2), m.group(3)
            hydrogens = 0 if not h else (int(h[1:]) if len(h) > 1 else 1)
            arom = element.islower()
            element = element.capitalize()
        else:
            arom = token.islower()
            element = token.capitalize()
            hydrogens = None
        index = len(symbols)
        symbols.append(element)
        order_sum.append(0.0)
        explicit_h.append(hydrogens)
        aromatic.append(arom)
        if prev is not None:
            bonds.append((prev, index))
            w = 1.5 if arom and aromatic[prev] and order == 1 else order
            orders.append(w)
            order_sum[prev] += w
            order_sum[index] += w
            if direction and directed is not None:
                directed.append((prev, index, direction))
        prev, order, direction = index, 1, 0
    heavy = len(symbols)
    for i in range(heavy):
        if explicit_h[i] is not None:
            count = explicit_h[i]
        elif symbols[i] == 'H':
            count = 0
        else:
            used = int(order_sum[i] + 0.5) if aromatic[i] else int(order_sum[i])
            if aromatic[i] and symbols[i] in ('O', 'S', 'Se'):
                # a lone-pair donor of an aromatic ring (furan, thiophene): its two ring bonds are
                # single; without this, thiophene got an extra H on S (C4H5S; fixed 2026-10-23)
                used = sum(1 for b in bonds if i in b)
            if aromatic[i] and symbols[i] in ('N', 'P') and sum(1 for b in bonds if i in b) >= 3:
                # the nitrogen of N-methylpyrrole, of caffeine: three bonds, its lone pair in the ring — no hydrogen.
                # Counted as 1.5 + 1.5 + 1 = 4 it was taken for a five-valent nitrogen and given one (C5H8N, «Электронов:
                # 105» for caffeine, 2026-11-23)
                used = max(VALENCE.get(symbols[i], (3,)))
            count = next((v - used for v in VALENCE.get(symbols[i], (0,)) if v >= used), 0)
        for _ in range(count):
            symbols.append('H')
            bonds.append((i, len(symbols) - 1))
            orders.append(1)
    if strict and (rings or stack or not symbols):
        raise ValueError('smiles')
    return symbols, bonds, orders


def signature(symbols, bonds, rounds=4):
    neighbours = [[] for _ in symbols]
    for i, j in bonds:
        neighbours[i].append(j)
        neighbours[j].append(i)
    colours = list(symbols)
    for _ in range(rounds):
        colours = [
            colours[i] + '(' + ','.join(sorted(colours[j] for j in neighbours[i])) + ')' for i in range(len(symbols))
        ]
        table = {c: str(n) for n, c in enumerate(sorted(set(colours)))}
        colours = [symbols[i] + table[c] for i, c in enumerate(colours)]
    return tuple(sorted(Counter(colours).items())), tuple(sorted(Counter(symbols).items()))


def _components(count, bonds):
    parent = list(range(count))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, j in bonds:
        parent[find(i)] = find(j)
    groups = {}
    for i in range(count):
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


_TABLE = None


def _table():
    global _TABLE
    if _TABLE is None:
        _TABLE = {}
        for smiles, ru, en, zh in NAMES:
            sig = signature(*parse_smiles(smiles))
            _TABLE.setdefault(sig, {'ru': ru, 'en': en, 'zh': zh})
    return _TABLE


def name(symbols, bonds, language='ru'):
    """The name of the structure (pieces joined by ' + '), or '' if a piece is not in the table."""
    if not symbols:
        return ''
    parts = []
    for group in sorted(_components(len(symbols), bonds), key=lambda g: g[0]):
        index = {a: n for n, a in enumerate(group)}
        sub = [symbols[a] for a in group]
        edges = [(index[i], index[j]) for i, j in bonds if i in index and j in index]
        entry = _table().get(signature(sub, edges))
        if entry is None:
            return ''
        parts.append(entry.get(language) or entry['ru'])
    counts = Counter(parts)
    return ' + '.join(
        (f'{n} × {p}' if n > 1 else p) for p, n in sorted(counts.items(), key=lambda x: parts.index(x[0]))
    )

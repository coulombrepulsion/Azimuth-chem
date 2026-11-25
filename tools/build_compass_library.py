"""Build modules/compass/chemistry/library.json: the molecules and fragments of the Compass menus.

§1 THEORY
    A teaching editor needs ready molecules and substituents with sensible starting geometries:
    correct connectivity and bond orders, bond lengths close to experiment, and the symmetry a
    student expects (benzene D6h, not a slightly distorted C1 hexagon). The geometries are made by
    the Compass's own builder, independent of any external program: SMILES -> a spanning-tree
    placement by atom shapes -> the "cleanup" force field (modules/compass/chemistry/formats.from_smiles,
    modules/compass/chemistry/cleanup) -> symmetrisation to the expected point group by the analysis of the
    Atlas (modules/compass/chemistry/symmetry.analyze). They are starting structures, not optimised ones.
§2 ALGORITHM
    Molecule (smiles, expected group G):
        m0 = from_smiles(smiles); candidates = m0 and cleanup(m0 + random shifts) for seeds 1..SEEDS
        for each candidate, for tol in TOLS: r = analyze(candidate, tol);
            accept the first r with r.name == G and r.rmsd <= tol; keep r.standard (centre of mass
            at the origin, principal axis along z)
        no candidate accepted -> the build fails with the list of groups found.
    Fragment (smiles starting with [H], the cut point):
        m = from_smiles(smiles); H = atom 0, A = its only neighbour.
        Rotate so that H - A points along -X (the anchor of place_fragment lies there), turn about X
        so that the first other heavy neighbour of A (else any atom off the axis) lies in the xy-plane
        with y > 0, translate A to the origin, drop H; A becomes atom 0.
§3 APPLICATIONS
    Run after changing MOLECULES or FRAGMENTS: python tools/build_compass_library.py (the molecules already
    in library.json are kept as they are; --rebuild builds every one again)
    The menus read the JSON (modules/compass/chemistry/library.py); tests/compass/test_compass_library.py checks it.
§4 SPECIFICATION
    MOLECULES: [(group title (ru), smiles, expected point group[, 'zigzag'])]; 'zigzag': an
        unbranched chain built as a planar zigzag (the anti conformer) instead of from_smiles,
        which has no torsion terms and tends to gauche forms; the Russian,
        English and Chinese names come from modules/compass/chemistry/names.NAMES by SMILES.
    FRAGMENTS: [(group title (ru), key (ru), smiles starting with '[H]')].
    FORMULA: {smiles: formula as written} for inorganic molecules; others: Hill order.
    Output JSON: {'version': 1, 'molecules': [{group, key, smiles, point_group, xyz, bonds}],
        'fragments': [{group, key, smiles, atoms: [[symbol, x, y, z]], bonds: [[i, j, order]]}],
        'groups': {ru: [en, zh]}}; coordinates in angstrom, rounded to 1e-4.
    Exit status 1 and a message for every molecule that did not reach its group.
§5 CODE - below.
§6 NOTES
    Deterministic (fixed seeds). Takes about a minute. Standard library + the Compass modules.
§7 TESTS
    tests/compass/test_compass_library.py: point groups re-analysed, names recognised from the geometry,
    bond lengths against typical experimental values, fragments attach and keep their shape.
§8' ROBUSTNESS
    A SMILES that the builder cannot read, or a molecule that never reaches its expected group,
    stops the build with its name; nothing is written then.
"""

import json
import random
import sys
from math import sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from azimuth.core import Atom, Molecule  # noqa: E402
from modules.compass.chemistry.formats import from_smiles  # noqa: E402
from modules.compass.chemistry.cleanup import clean  # noqa: E402
from modules.compass.chemistry import symmetry  # noqa: E402
from modules.compass.chemistry.names import NAMES  # noqa: E402

OUT = ROOT / 'modules' / 'compass' / 'chemistry' / 'library.json'
SEEDS = 40
TOLS = (0.05, 0.1, 0.15, 0.2)

GROUPS = {
    'Неорганические': ['Inorganic', '无机物'],
    'Алканы и циклоалканы': ['Alkanes and cycloalkanes', '烷烃和环烷烃'],
    'Алкены, диены и алкины': ['Alkenes, dienes and alkynes', '烯烃、二烯烃和炔烃'],
    'Ароматические и гетероциклы': ['Aromatics and heterocycles', '芳香化合物和杂环'],
    'Спирты и простые эфиры': ['Alcohols and ethers', '醇和醚'],
    'Карбонильные соединения и кислоты': ['Carbonyl compounds and acids', '羰基化合物和酸'],
    'Азот, сера, галогены': ['Nitrogen, sulfur, halogens', '含氮、硫和卤素的化合物'],
    'Углеводородные': ['Hydrocarbon groups', '烃基'],
    'Кислородсодержащие': ['Oxygen groups', '含氧基团'],
    'Азот и сера': ['Nitrogen and sulfur groups', '含氮和硫的基团'],
    'Галогены': ['Halogens', '卤素'],
}

I, A, U, R, O, C, N = (
    'Неорганические',
    'Алканы и циклоалканы',
    'Алкены, диены и алкины',
    'Ароматические и гетероциклы',
    'Спирты и простые эфиры',
    'Карбонильные соединения и кислоты',
    'Азот, сера, галогены',
)
# (group, SMILES as in names.NAMES, expected point group of the usual conformer)
MOLECULES = [
    (I, 'O', 'C2v'),
    (I, 'N', 'C3v'),
    (I, 'S', 'C2v'),
    (I, 'P', 'C3v'),
    (I, 'C#N', 'C∞v'),
    (I, 'O=C=O', 'D∞h'),
    (I, 'O=S=O', 'C2v'),
    (I, 'O=S(=O)=O', 'D3h'),
    (I, 'B(F)(F)F', 'D3h'),
    (I, 'OO', 'C2'),
    (I, 'NN', 'C2'),
    (I, 'F', 'C∞v'),
    (I, 'Cl', 'C∞v'),
    (I, 'N#N', 'D∞h'),
    (I, 'OS(=O)(=O)O', 'C2'),
    (A, 'C', 'Td'),
    (A, 'CC', 'D3d'),
    (A, 'CCC', 'C2v'),
    (A, 'CCCC', 'C2h', 'zigzag'),
    (A, 'CC(C)C', 'C3v'),
    (A, 'CCCCC', 'C2v', 'zigzag'),
    (A, 'CCCCCC', 'C2h', 'zigzag'),
    (A, 'C1CC1', 'D3h'),
    (A, 'C1CCCCC1', 'D3d'),
    (U, 'C=C', 'D2h'),
    (U, 'C=CC', 'Cs'),
    (U, 'C=CC=C', 'C2h'),
    (U, 'C#C', 'D∞h'),
    (U, 'C#CC', 'C3v'),
    (U, 'C=C=C', 'D2d'),
    (R, 'c1ccccc1', 'D6h'),
    (R, 'Cc1ccccc1', 'Cs'),
    (R, 'Oc1ccccc1', 'Cs'),
    (R, 'c1ccncc1', 'C2v'),
    (R, 'c1cc[nH]c1', 'C2v'),
    (R, 'c1ccoc1', 'C2v'),
    (R, 'c1ccsc1', 'C2v'),
    (R, 'c1ccc2ccccc2c1', 'D2h'),
    (R, 'O=Cc1ccccc1', 'Cs'),
    (R, 'OC(=O)c1ccccc1', 'Cs'),
    (R, 'Clc1ccccc1', 'C2v'),
    (O, 'CO', 'Cs'),
    (O, 'CCO', 'Cs'),
    (O, 'COC', 'C2v'),
    (O, 'CCOCC', 'C2v', 'zigzag'),
    (O, 'C1CO1', 'C2v'),
    (C, 'C=O', 'C2v'),
    (C, 'CC=O', 'Cs'),
    (C, 'CC(C)=O', 'C2v'),
    (C, 'OC=O', 'Cs'),
    (C, 'CC(O)=O', 'Cs'),
    (C, 'NC=O', 'Cs'),
    (C, 'ClC(Cl)=O', 'C2v'),
    (N, 'CN', 'Cs'),
    (N, 'CN(C)C', 'C3v'),
    (N, 'CC#N', 'C3v'),
    (N, 'CS(C)=O', 'Cs'),
    (N, 'CS', 'Cs'),
    (N, 'CF', 'C3v'),
    (N, 'CCl', 'C3v'),
    (N, 'ClCCl', 'C2v'),
    (N, 'ClC(Cl)Cl', 'C3v'),
    (N, 'ClC(Cl)(Cl)Cl', 'Td'),
    (N, 'FC(F)(F)F', 'Td'),
    (N, 'C=CCl', 'Cs'),
    # the larger library the molecules of names.NAMES that were not here, and new ones
    (I, '[H][H]', 'D∞h'),
    (I, 'FF', 'D∞h'),
    (I, 'ClCl', 'D∞h'),
    (I, '[C-]#[O+]', 'C∞v'),
    (I, 'FS(F)(F)(F)(F)F', 'Oh'),
    (I, 'FP(F)(F)(F)F', 'D3h'),
    (I, 'O=[O+][O-]', 'C2v'),
    (I, 'Br', 'C∞v'),
    (I, 'O[N+](=O)[O-]', 'Cs'),
    (A, 'C1CCC1', 'D4h'),
    (A, 'C1CCCC1', 'Cs'),
    (U, 'CC=CC', 'C2h'),
    (U, 'C=CCC', 'Cs'),
    (U, 'CC#CC', 'D3d'),
    (R, 'Nc1ccccc1', 'Cs'),
    (R, '[O-][N+](=O)c1ccccc1', 'C2v'),
    (R, 'C=Cc1ccccc1', 'Cs'),
    (R, 'CC(=O)c1ccccc1', 'Cs'),
    (R, 'Cc1ccc(C)cc1', 'C2h'),
    (R, 'c1cncnc1', 'C2v'),
    (R, 'c1c[nH]cn1', 'Cs'),
    (R, 'c1ccc2[nH]ccc2c1', 'Cs'),
    (R, 'c1ccc2cc3ccccc3cc2c1', 'D2h'),
    (R, 'O=C1C=CC(=O)C=C1', 'D2h'),
    (O, 'CCCO', 'Cs', 'zigzag'),
    (O, 'CC(C)O', 'Cs'),
    (O, 'CC(C)(C)O', 'Cs'),
    (O, 'OCCO', 'C2'),
    (O, 'C1CCOC1', 'Cs'),
    (O, 'C1COCCO1', 'C2h'),
    (C, 'CCOC(C)=O', 'Cs'),
    (C, 'CC(N)=O', 'Cs'),
    (C, 'OC(=O)C(O)=O', 'C2h'),
    (C, 'NC(N)=O', 'C2'),
    (C, 'NCC(O)=O', 'C1'),
    (C, 'CC(N)C(O)=O', 'C1'),
    (N, 'CNC', 'Cs'),
    (N, 'C[N+](=O)[O-]', 'Cs'),
    (N, 'CS(C)(=O)=O', 'C2v'),
    (N, 'CBr', 'C3v'),
    (N, 'CCCl', 'Cs'),
]

H, OX, NS, X = 'Углеводородные', 'Кислородсодержащие', 'Азот и сера', 'Галогены'
FRAGMENTS = [
    (H, 'Этил · —C₂H₅', '[H]CC'),
    (H, 'Изопропил · —CH(CH₃)₂', '[H]C(C)C'),
    (H, 'трет-Бутил · —C(CH₃)₃', '[H]C(C)(C)C'),
    (H, 'Винил · —CH=CH₂', '[H]C=C'),
    (H, 'Этинил · —C≡CH', '[H]C#C'),
    (H, 'Циклогексил · —C₆H₁₁', '[H]C1CCCCC1'),
    (H, 'Бензил · —CH₂C₆H₅', '[H]Cc1ccccc1'),
    (OX, 'Метокси · —OCH₃', '[H]OC'),
    (OX, 'Формил · —CHO', '[H]C=O'),
    (OX, 'Ацетил · —C(O)CH₃', '[H]C(C)=O'),
    (OX, 'Карбоксил · —COOH', '[H]C(=O)O'),
    (OX, 'Метоксикарбонил · —COOCH₃', '[H]C(=O)OC'),
    (NS, 'Метиламино · —NHCH₃', '[H]NC'),
    (NS, 'Диметиламино · —N(CH₃)₂', '[H]N(C)C'),
    (NS, 'Карбамоил · —C(O)NH₂', '[H]C(N)=O'),
    (NS, 'Нитро · —NO₂', '[H][N+](=O)[O-]'),
    (NS, 'Циано · —C≡N', '[H]C#N'),
    (NS, 'Сульфанил · —SH', '[H]S'),
    (NS, 'Сульфо · —SO₃H', '[H]S(=O)(=O)O'),
    (X, 'Фтор · —F', '[H]F'),
    (X, 'Хлор · —Cl', '[H]Cl'),
    (X, 'Бром · —Br', '[H]Br'),
    (X, 'Иод · —I', '[H]I'),
    (X, 'Трифторметил · —CF₃', '[H]C(F)(F)F'),
]

SUB = str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')
# the usual way of writing inorganic formulas (the Hill order would give H₃N, O₂S, ClH, CHN)
FORMULA = {
    'FS(F)(F)(F)(F)F': 'SF₆',
    'FP(F)(F)(F)F': 'PF₅',
    'N': 'NH₃',
    'P': 'PH₃',
    'S': 'H₂S',
    'C#N': 'HCN',
    'O=S=O': 'SO₂',
    'O=S(=O)=O': 'SO₃',
    'NN': 'N₂H₄',
    'F': 'HF',
    'Cl': 'HCl',
    'OS(=O)(=O)O': 'H₂SO₄',
    '[H][H]': 'H₂',
    'FF': 'F₂',
    'ClCl': 'Cl₂',
    '[C-]#[O+]': 'CO',
    'O=[O+][O-]': 'O₃',
    'Br': 'HBr',
    'O[N+](=O)[O-]': 'HNO₃',
}


def zigzag(smiles):
    """An unbranched chain as a planar zigzag (all anti), hydrogens by valence, then cleanup."""
    from math import cos, radians, sin
    from modules.compass.chemistry.names import smiles_graph
    from modules.compass.chemistry.editing import add_hydrogens
    from modules.compass.chemistry.builder import bond_length

    symbols, links, _ = smiles_graph(smiles)
    heavy = [k for k, s in enumerate(symbols) if s != 'H']
    pos, x, y = [], 0.0, 0.0
    for n, k in enumerate(heavy):
        if n:
            step = bond_length(symbols[heavy[n - 1]], symbols[k])
            x, y = x + step * cos(radians(35.25)), y + step * sin(radians(35.25)) * (1 if n % 2 else -1)
        pos.append((x, y, 0.0))
    skeleton = Molecule(
        '', tuple(Atom(symbols[k], *p) for k, p in zip(heavy, pos)), tuple((n - 1, n, 1) for n in range(1, len(heavy)))
    )
    return clean(add_hydrogens(skeleton)[0], steps=4000)[0]


def candidates(smiles, hint=None):
    """from_smiles (or the zigzag), then cleanup from SEEDS randomly shifted starts (other conformers)."""
    m0 = zigzag(smiles) if hint == 'zigzag' else from_smiles(smiles)
    yield m0
    for seed in range(1, SEEDS + 1):
        rnd = random.Random(seed)
        shifted = Molecule(
            m0.title,
            tuple(Atom(a.symbol, *[c + rnd.uniform(-0.8, 0.8) for c in a.position]) for a in m0.atoms),
            m0.bonds,
        )
        try:
            yield clean(shifted, steps=4000)[0]
        except ValueError:
            continue  # this start collapsed two atoms; try the next one


def symmetric(smiles, group, hint=None):
    found = []
    for m in candidates(smiles, hint):
        for tol in TOLS:
            r = symmetry.analyze(m, tol)
            if r.get('name') == group and r['rmsd'] <= tol:
                return r['standard'], None
            found.append(r.get('name', r.get('err')))
    return None, sorted(set(found))


def names_for(smiles):
    for s, ru, en, zh in NAMES:
        if s == smiles:
            return ru, en, zh
    raise ValueError(f'{smiles}: not in names.NAMES')


def xyz(m, title):
    return f'{len(m.atoms)}\n{title}\n' + '\n'.join(f'{a.symbol} {a.x:.4f} {a.y:.4f} {a.z:.4f}' for a in m.atoms)


def fragment(smiles):
    m = from_smiles(smiles)
    bonds = list(m.bonds)
    nb = [j if i == 0 else i for i, j, _ in bonds if 0 in (i, j)]
    if m.atoms[0].symbol != 'H' or len(nb) != 1:
        raise ValueError(f'{smiles}: the first atom must be an H with one bond')
    a = nb[0]
    pa, ph = m.atoms[a].position, m.atoms[0].position
    d = [ph[k] - pa[k] for k in range(3)]
    n = sqrt(sum(x * x for x in d))
    ex = [-x / n for x in d]  # template +X: from the anchor side (-X) into the fragment
    others = [j if i == a else i for i, j, _ in bonds if a in (i, j) and 0 not in (i, j)]
    others += [k for k in range(1, len(m.atoms)) if k != a]
    ey = None
    for k in others:
        v = [m.atoms[k].position[c] - pa[c] for c in range(3)]
        v = [v[c] - sum(v[i] * ex[i] for i in range(3)) * ex[c] for c in range(3)]
        lv = sqrt(sum(x * x for x in v))
        if lv > 1e-3:
            ey = [x / lv for x in v]
            break
    if ey is None:  # a single atom or a linear group: any perpendicular
        ref = [0, 0, 1] if abs(ex[2]) < 0.9 else [0, 1, 0]
        v = [ref[1] * ex[2] - ref[2] * ex[1], ref[2] * ex[0] - ref[0] * ex[2], ref[0] * ex[1] - ref[1] * ex[0]]
        lv = sqrt(sum(x * x for x in v))
        ey = [x / lv for x in v]
    ez = [ex[1] * ey[2] - ex[2] * ey[1], ex[2] * ey[0] - ex[0] * ey[2], ex[0] * ey[1] - ex[1] * ey[0]]
    order = [a] + [k for k in range(1, len(m.atoms)) if k != a]
    index = {old: new for new, old in enumerate(order)}
    atoms = []
    for k in order:
        v = [m.atoms[k].position[c] - pa[c] for c in range(3)]
        atoms.append([m.atoms[k].symbol] + [round(sum(v[c] * e[c] for c in range(3)), 4) + 0.0 for e in (ex, ey, ez)])
    edges = [[index[i], index[j], o] for i, j, o in bonds if 0 not in (i, j)]
    return atoms, edges


def main():
    out = {'version': 1, 'groups': GROUPS, 'molecules': [], 'fragments': []}
    failed = []
    # the molecules already in library.json keep their geometry (only the new ones are built); --rebuild
    # builds all of them again
    old = {}
    if OUT.is_file() and '--rebuild' not in sys.argv:
        old = {e['smiles']: e for e in json.loads(OUT.read_text(encoding='utf-8'))['molecules']}
    for group, smiles, point_group, *hint in MOLECULES:
        if smiles in old and old[smiles]['point_group'] == point_group:
            out['molecules'].append(dict(old[smiles], group=group))
            continue
        ru, en, zh = names_for(smiles)
        try:
            m, found = symmetric(smiles, point_group, hint[0] if hint else None)
        except ValueError as exc:
            m, found = None, f'builder error: {exc}'
        if m is None:
            failed.append(f'{smiles} ({ru}): expected {point_group}, found {found}')
            continue
        formula = FORMULA.get(smiles) or m.formula.translate(SUB)
        title = ru[0].upper() + ru[1:]
        out['molecules'].append(
            {
                'group': group,
                'key': f'{title} · {formula}',
                'names': [f'{title} · {formula}', f'{en[0].upper() + en[1:]} · {formula}', f'{zh} · {formula}'],
                'smiles': smiles,
                'point_group': point_group,
                'xyz': xyz(m, title),
                'bonds': [list(b) for b in m.bonds],
            }
        )
        print('ok', point_group, smiles, flush=True)
    for group, key, smiles in FRAGMENTS:
        atoms, bonds = fragment(smiles)
        out['fragments'].append({'group': group, 'key': key, 'smiles': smiles, 'atoms': atoms, 'bonds': bonds})
    if failed:
        print('FAILED:\n  ' + '\n  '.join(failed))
        return 1
    OUT.write_text(json.dumps(out, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(f'{len(out["molecules"])} molecules, {len(out["fragments"])} fragments -> {OUT}')
    added = translate_menu_names(out['molecules'])
    if added:
        print(f'{added} names added to azimuth/locale/en.json and zh.json')
    return 0


def translate_menu_names(molecules):
    """The menu «Примеры молекул» shows tr(key); the English and Chinese names of each molecule go into the
    dictionaries of the program (before, the molecules added in 0.89.0 stayed in Russian in the English menu)."""
    added = 0
    for column, code in ((1, 'en'), (2, 'zh')):
        path = ROOT / 'azimuth' / 'locale' / f'{code}.json'
        table = json.loads(path.read_text(encoding='utf-8'))
        new = {e['key']: e['names'][column] for e in molecules if e['key'] not in table}
        if new:
            table.update(new)
            path.write_text(json.dumps(table, ensure_ascii=False, indent=1), encoding='utf-8')
            added += len(new) if code == 'en' else 0
    return added


if __name__ == '__main__':
    raise SystemExit(main())

"""The molecule and fragment library of Compass (modules/compass/chemistry/library.py, tools/build_compass_library.py)
and the builder fixes made with it.

Oracles, independent of the builder:
  * the point group a chemist expects for the usual conformer (written in the build script, re-analysed here);
  * the name recognised from the connectivity alone (modules/compass/chemistry/names: Weisfeiler-Lehman graphs);
  * typical experimental bond lengths, REFERENCE below. Values: Allen et al., J. Chem. Soc. Perkin Trans. 2
    (1987) S1 and CRC Handbook tables (ASSUMPTION: quoted from memory, not re-fetched), except O-O 1.474
    (H2O2, gas) and S-OH 1.574 (H2SO4), verified 2026-10-23 via webqc.org;
  * VSEPR shapes: CO2 and allene linear, SO2 bent (~119 deg), SO3 planar, H2SO4 tetrahedral, DMSO pyramidal.
Tolerance for bond lengths (section 8): the builder's single bond is the sum of covalent radii and its multiple
bonds are fixed fractions of it; for polar bonds this model is off by up to ~0.06 A (B-F 1.37 vs 1.31,
H-Cl 1.33 vs 1.27, C=O of CO2 1.24 vs 1.16 is not in the table), so 0.07 A.
"""

from math import acos, degrees, dist, sqrt

import pytest

from azimuth.core import EXAMPLES, Molecule, read_xyz
from modules.compass.chemistry.builder import BASIC_FRAGMENTS, FRAGMENT_BONDS, FRAGMENT_GROUPS, FRAGMENTS, connections
from modules.compass.chemistry import library
from modules.compass.chemistry.editing import substitute
from modules.compass.chemistry.formats import from_smiles, kekule
from modules.compass.chemistry.names import NAMES, name, smiles_graph
from modules.compass.chemistry.symmetry import analyze

ENTRIES = {e['key']: e for e in library._DATA['molecules']}
BOUND = 0.07
REFERENCE = {  # (sorted symbols, order): typical length in angstrom
    ('C', 'H', 1): 1.09,
    ('C', 'C', 1): 1.53,
    ('C', 'C', 2): 1.34,
    ('C', 'C', 3): 1.20,
    ('C', 'O', 1): 1.43,
    ('C', 'O', 2): 1.21,
    ('H', 'O', 1): 0.96,
    ('H', 'N', 1): 1.01,
    ('C', 'N', 1): 1.47,
    ('C', 'N', 3): 1.16,
    ('C', 'Cl', 1): 1.77,
    ('C', 'F', 1): 1.35,
    ('H', 'S', 1): 1.34,
    ('C', 'S', 1): 1.82,
    ('Cl', 'H', 1): 1.27,
    ('F', 'H', 1): 0.92,
    ('N', 'N', 3): 1.10,
    ('N', 'N', 1): 1.45,
    ('O', 'O', 1): 1.474,
    ('H', 'P', 1): 1.42,
    ('B', 'F', 1): 1.31,
    ('O', 'S', 1): 1.574,
}
AROMATIC = {('C', 'C'): 1.39, ('C', 'O'): 1.36, ('C', 'S'): 1.71}  # C-N: pyridine 1.34, pyrrole 1.37


def entry_molecule(entry):
    m = read_xyz(entry['xyz'])
    return Molecule(m.title, m.atoms, tuple(tuple(b) for b in entry['bonds']))


def test_library_groups_and_lookup():
    assert len(ENTRIES) >= 60 and len(library.MOLECULE_GROUPS) == 7
    assert library.keys()[: len(EXAMPLES)] == list(EXAMPLES)  # the teaching examples stay first
    for key in library.keys():
        m = library.molecule(key)
        assert m.atoms and (key in EXAMPLES or m.bonds)
    with pytest.raises(KeyError):
        library.molecule('нет такой молекулы')


@pytest.mark.parametrize('key', sorted(ENTRIES))
def test_molecule_has_its_point_group_name_and_bond_lengths(key):
    entry = ENTRIES[key]
    m = entry_molecule(entry)
    assert analyze(m, 0.02)['name'] == entry['point_group']
    ru = next(r for s, r, en, zh in NAMES if s == entry['smiles'])
    assert name([a.symbol for a in m.atoms], [(i, j) for i, j, _ in m.bonds]) == ru
    m.validate_state(0, 1)  # a closed-shell neutral molecule
    _, links, orders = smiles_graph(entry['smiles'])
    aromatic = {frozenset(link) for link, o in zip(links, orders) if o == 1.5}
    for i, j, o in m.bonds:
        pair = tuple(sorted((m.atoms[i].symbol, m.atoms[j].symbol)))
        if frozenset((i, j)) in aromatic:
            if pair == ('C', 'N'):
                n = i if m.atoms[i].symbol == 'N' else j
                ref = 1.37 if sum(n in b[:2] for b in m.bonds) == 3 else 1.34
            else:
                ref = AROMATIC.get(pair)
        elif entry['smiles'] == 'O=[O+][O-]':
            ref = 1.28  # ozone: the two O–O bonds are equal (order 1.5), neither single nor double
        else:
            ref = REFERENCE.get(pair + (o,))
        if ref is not None:
            assert abs(dist(m.atoms[i].position, m.atoms[j].position) - ref) <= BOUND, (pair, o)
    bonded = {frozenset(b[:2]) for b in m.bonds}
    for a in range(len(m.atoms)):
        for b in range(a):
            if frozenset((a, b)) not in bonded:
                assert dist(m.atoms[a].position, m.atoms[b].position) > 1.5  # no clash, also 1-3 pairs


# substituting one H of methane: the product named by its connectivity (None: not in names.NAMES)
PRODUCTS = {
    'Этил · —C₂H₅': 'пропан',
    'Изопропил · —CH(CH₃)₂': '2-метилпропан (изобутан)',
    'Винил · —CH=CH₂': 'пропен',
    'Этинил · —C≡CH': 'пропин',
    'Метокси · —OCH₃': 'метоксиметан (диметиловый эфир)',
    'Формил · —CHO': 'этаналь (ацетальдегид)',
    'Ацетил · —C(O)CH₃': 'пропан-2-он (ацетон)',
    'Карбоксил · —COOH': 'этановая (уксусная) кислота',
    'Метиламино · —NHCH₃': 'N-метилметанамин (диметиламин)',
    'Диметиламино · —N(CH₃)₂': 'N,N-диметилметанамин (триметиламин)',
    'Карбамоил · —C(O)NH₂': 'этанамид (ацетамид)',
    'Нитро · —NO₂': 'нитрометан',
    'Циано · —C≡N': 'этаннитрил (ацетонитрил)',
    'Сульфанил · —SH': 'метантиол',
    'Фтор · —F': 'фторметан',
    'Хлор · —Cl': 'хлорметан',
    'Бром · —Br': 'бромметан',
}


@pytest.mark.parametrize('key', sorted(library.FRAGMENTS))
def test_fragment_replaces_a_hydrogen_of_methane(key):
    methane = read_xyz(EXAMPLES['Метан · CH₄'])
    product = substitute(methane, 1, key)
    assert len(product.atoms) == len(methane.atoms) - 1 + len(FRAGMENTS[key])
    expected = PRODUCTS.get(key)
    if expected is not None:
        assert name([a.symbol for a in product.atoms], [(i, j) for i, j, _ in connections(product)]) == expected
    template = FRAGMENTS[key]
    assert template[0][1:] == (0.0, 0.0, 0.0)  # the attachment atom at the origin
    # the open bond points to -X: no fragment atom comes near the anchor 1.5 A behind the attachment atom
    assert all(dist((x, y, z), (-1.5, 0.0, 0.0)) > 1.6 for _, x, y, z in template[1:])
    bonded = {frozenset(b[:2]) for b in connections(product)}
    for a in range(len(product.atoms)):  # no clash in the product (1-3 pairs are farther than 1.5 A too)
        for b in range(a):
            if frozenset((a, b)) not in bonded:
                assert dist(product.atoms[a].position, product.atoms[b].position) > 1.5
    for a, b, o in FRAGMENT_BONDS[key]:
        assert 0 <= a < len(template) and 0 <= b < len(template) and o in (1, 2, 3)


def test_fragment_menus_keep_the_first_five_and_group_the_rest():
    assert BASIC_FRAGMENTS == ('Метил · —CH₃', 'Гидроксил · —OH', 'Амино · —NH₂', 'Карбонил · >C=O', 'Фенил · —C₆H₅')
    grouped = [k for keys in FRAGMENT_GROUPS.values() for k in keys]
    assert set(grouped) == set(FRAGMENTS) - set(BASIC_FRAGMENTS) and len(grouped) == len(set(grouped))


def angle(m, a, c, b):
    u = [m.atoms[a].position[k] - m.atoms[c].position[k] for k in range(3)]
    v = [m.atoms[b].position[k] - m.atoms[c].position[k] for k in range(3)]
    cosine = sum(x * y for x, y in zip(u, v)) / sqrt(sum(x * x for x in u) * sum(y * y for y in v))
    return degrees(acos(max(-1.0, min(1.0, cosine))))  # an exactly linear O=C=O (0.249.28) rounds to −1 − ε


def centre_angles(m, symbol):
    c = next(k for k, a in enumerate(m.atoms) if a.symbol == symbol)
    ns = [j if i == c else i for i, j, _ in m.bonds if c in (i, j)]
    return [angle(m, ns[x], c, ns[y]) for x in range(len(ns)) for y in range(x + 1, len(ns))]


def test_vsepr_shapes_of_the_smiles_builder():
    assert centre_angles(from_smiles('O=C=O'), 'C') == pytest.approx([180], abs=2)
    assert abs(centre_angles(from_smiles('O=S=O'), 'S')[0] - 119.5) < 6  # bent, not linear (was linear)
    so3 = centre_angles(from_smiles('O=S(=O)=O'), 'S')
    assert sum(so3) == pytest.approx(360, abs=2)  # planar, oxygens apart (they used to collapse)
    sulfuric = centre_angles(from_smiles('OS(=O)(=O)O'), 'S')
    assert len(sulfuric) == 6 and all(95 < a < 125 for a in sulfuric)  # tetrahedral
    assert sum(centre_angles(from_smiles('CS(C)=O'), 'S')) < 345  # DMSO is pyramidal


@pytest.mark.parametrize('smiles', ['c1ccoc1', 'c1ccsc1', 'c1cc[nH]c1'])
def test_five_ring_heteroaromatics(smiles):
    symbols, links, orders = smiles_graph(smiles)
    bonds = kekule(len(symbols), [(i, j, o) for (i, j), o in zip(links, orders)], symbols)
    hetero = next(k for k, s in enumerate(symbols) if s in ('O', 'S', 'N'))
    assert all(o == 1 for i, j, o in bonds if hetero in (i, j))  # no C=O, C=S, C=N in the ring
    assert sum(1 for i, j, o in bonds if o == 2) == 2
    assert analyze(from_smiles(smiles), 0.1)['name'] == 'C2v'  # flat and symmetric


def test_measured_single_bonds_in_the_builder():
    # O-O of H2O2 1.474 and S-OH of H2SO4 1.574 (verified 2026-10-23); multiple bonds keep the radii model
    from modules.compass.chemistry.builder import bond_length

    assert bond_length('O', 'O') == pytest.approx(1.474) and bond_length('S', 'O') == pytest.approx(1.574)
    peroxide = from_smiles('OO')
    o = [k for k, a in enumerate(peroxide.atoms) if a.symbol == 'O']
    assert dist(peroxide.atoms[o[0]].position, peroxide.atoms[o[1]].position) == pytest.approx(1.474, abs=0.03)
    acid = from_smiles('OS(=O)(=O)O')
    lengths = sorted(
        dist(acid.atoms[i].position, acid.atoms[j].position)
        for i, j, _ in acid.bonds
        if {acid.atoms[i].symbol, acid.atoms[j].symbol} == {'S', 'O'}
    )
    assert lengths[:2] == pytest.approx([1.50, 1.50], abs=0.04) and lengths[2:] == pytest.approx(
        [1.574, 1.574], abs=0.04
    )


def test_json_matches_the_build_script():
    import importlib.util
    from azimuth.paths import ROOT

    spec = importlib.util.spec_from_file_location('build', ROOT / 'tools' / 'build_compass_library.py')
    build = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(build)
    assert [(m[0], m[1], m[2]) for m in build.MOLECULES] == [
        (e['group'], e['smiles'], e['point_group']) for e in library._DATA['molecules']
    ]
    assert [(f[0], f[1], f[2]) for f in build.FRAGMENTS] == [
        (e['group'], e['key'], e['smiles']) for e in library._DATA['fragments']
    ]


def test_every_molecule_name_of_the_menu_is_translated():
    # the menu «Примеры молекул» shows tr(key) — every key has its English and Chinese name in the dictionaries
    # (tools/build_compass_library.py adds them); before, the 41 molecules of 0.89.0–0.89.1 stayed in Russian
    import json
    from pathlib import Path

    folder = Path(__file__).resolve().parents[2] / 'azimuth' / 'locale'
    for column, code in ((1, 'en'), (2, 'zh')):
        table = json.loads((folder / f'{code}.json').read_text(encoding='utf-8'))
        data = json.loads((Path(library.__file__).with_name('library.json')).read_text(encoding='utf-8'))
        missing = [e['key'] for e in data['molecules'] if table.get(e['key']) != e['names'][column]]
        assert not missing, (code, missing)

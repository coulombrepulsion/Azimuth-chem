"""IUPAC names of Compass structures (modules/compass/chemistry/iupac.py), the SMILES writer and the PubChem query
(modules/compass/chemistry/pubchem.py), the «IUPAC» button (modules/compass/actions/naming_actions.py); 2026-10-23.

Oracles:
  * NAMED: names written by hand from the IUPAC 1993 recommendations and textbooks (ru: Russian
    textbook forms; zh: the traditional form of the program's names table), not produced by the code;
  * the names table of the library (library.NAMES), filled earlier from other sources: every systematic
    name there must be reproduced (RETAINED lists where the table uses a common name instead);
  * names.smiles_graph, the SMILES parser written earlier for the names table, reads the SMILES writer's
    output back to the same graph.
Exact comparison of strings: names are discrete, no tolerance applies.
"""

import random
import re
import urllib.error

import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import iupac, library, pubchem
from modules.compass.chemistry.editing import perceived_orders
from modules.compass.chemistry.formats import from_smiles
from modules.compass.chemistry.names import signature, smiles_graph

NAMED = [  # SMILES, ru, en, zh
    ('CC(C)C', '2-метилпропан', '2-methylpropane', '2-甲基丙烷'),
    ('CC=CC', 'бут-2-ен', 'but-2-ene', '2-丁烯'),
    ('C=CC=C', 'бута-1,3-диен', 'buta-1,3-diene', '1,3-丁二烯'),
    ('CC#CC', 'бут-2-ин', 'but-2-yne', '2-丁炔'),
    ('C=CC#C', 'бут-1-ен-3-ин', 'but-1-en-3-yne', '1-丁烯-3-炔'),
    ('CC(C)(C)C', '2,2-диметилпропан', '2,2-dimethylpropane', '2,2-二甲基丙烷'),
    ('CC(C)CC(C)(C)C', '2,2,4-триметилпентан', '2,2,4-trimethylpentane', '2,2,4-三甲基戊烷'),
    ('CC(C)CCC(CC)C(C)C', '2,6-диметил-3-этилгептан', '3-ethyl-2,6-dimethylheptane', '2,6-二甲基-3-乙基庚烷'),
    ('CCC(=C)CC', '2-этилбут-1-ен', '2-ethylbut-1-ene', '2-乙基-1-丁烯'),
    ('ClCC=C', '3-хлорпроп-1-ен', '3-chloroprop-1-ene', '3-氯-1-丙烯'),
    ('ClCCCF', '1-фтор-3-хлорпропан', '1-chloro-3-fluoropropane', '1-氟-3-氯丙烷'),
    ('ClCCCl', '1,2-дихлорэтан', '1,2-dichloroethane', '1,2-二氯乙烷'),
    ('CC[N+](=O)[O-]', 'нитроэтан', 'nitroethane', '硝基乙烷'),
    ('CC(O)C', 'пропан-2-ол', 'propan-2-ol', '2-丙醇'),
    ('CC(C)(C)O', '2-метилпропан-2-ол', '2-methylpropan-2-ol', '2-甲基-2-丙醇'),
    ('OCCO', 'этан-1,2-диол', 'ethane-1,2-diol', '乙二醇'),
    ('ClCCO', '2-хлорэтанол', '2-chloroethanol', '2-氯乙醇'),
    ('C=CC(O)C', 'бут-3-ен-2-ол', 'but-3-en-2-ol', '3-丁烯-2-醇'),
    ('OCC=C', 'проп-2-ен-1-ол', 'prop-2-en-1-ol', '2-丙烯-1-醇'),
    ('CCC(CC)CO', '2-этилбутан-1-ол', '2-ethylbutan-1-ol', '2-乙基-1-丁醇'),
    ('CC(=O)CCC(C)C', '5-метилгексан-2-он', '5-methylhexan-2-one', '5-甲基-2-己酮'),
    ('CC(O)CC(C)=O', '4-гидроксипентан-2-он', '4-hydroxypentan-2-one', '4-羟基-2-戊酮'),
    ('CC(Cl)CC=O', '3-хлорбутаналь', '3-chlorobutanal', '3-氯丁醛'),
    ('O=CCC=O', 'пропандиаль', 'propanedial', '丙二醛'),
    ('C=CC=O', 'проп-2-еналь', 'prop-2-enal', '丙烯醛'),
    ('CC(C)CC(=O)O', '3-метилбутановая кислота', '3-methylbutanoic acid', '3-甲基丁酸'),
    ('OC(=O)CC(=O)O', 'пропандиовая кислота', 'propanedioic acid', '丙二酸'),
    ('CC=CC(=O)O', 'бут-2-еновая кислота', 'but-2-enoic acid', '2-丁烯酸'),
    ('OC(=O)C(O)C', '2-гидроксипропановая кислота', '2-hydroxypropanoic acid', '2-羟基丙酸'),
    ('NCC(=O)O', '2-аминоэтановая кислота', '2-aminoethanoic acid', '2-氨基乙酸'),
    ('CC(=O)OC', 'метилэтаноат', 'methyl ethanoate', '乙酸甲酯'),
    ('CCC(=O)OCC', 'этилпропаноат', 'ethyl propanoate', '丙酸乙酯'),
    ('CC(=O)OC(C)C', 'изопропилэтаноат', 'isopropyl ethanoate', '乙酸异丙酯'),
    ('C=CC(=O)OC', 'метилпроп-2-еноат', 'methyl prop-2-enoate', '丙烯酸甲酯'),
    ('COC(=O)c1ccccc1', 'метилбензоат', 'methyl benzoate', '苯甲酸甲酯'),
    ('CCCC(=O)N', 'бутанамид', 'butanamide', '丁酰胺'),
    ('CCC#N', 'пропаннитрил', 'propanenitrile', '丙腈'),
    ('CNC', 'N-метилметанамин', 'N-methylmethanamine', 'N-甲基甲胺'),
    ('CCN(CC)CC', 'N,N-диэтилэтанамин', 'N,N-diethylethanamine', 'N,N-二乙基乙胺'),
    ('NCCO', '2-аминоэтанол', '2-aminoethanol', '2-氨基乙醇'),
    ('CC(C)OC', '2-метоксипропан', '2-methoxypropane', '2-甲氧基丙烷'),
    ('C1=CCCCC1', 'циклогексен', 'cyclohexene', '环己烯'),
    ('CC1CC=CCC1', '4-метилциклогексен', '4-methylcyclohexene', '4-甲基环己烯'),
    ('CC1CCCCC1C', '1,2-диметилциклогексан', '1,2-dimethylcyclohexane', '1,2-二甲基环己烷'),
    ('OC1CCCC1', 'циклопентанол', 'cyclopentanol', '环戊醇'),
    ('OC1CC=CCC1', 'циклогекс-3-ен-1-ол', 'cyclohex-3-en-1-ol', '3-环己烯-1-醇'),
    ('O=C1CCCCC1', 'циклогексанон', 'cyclohexanone', '环己酮'),
    ('NC1CCCCC1', 'циклогексанамин', 'cyclohexanamine', '环己胺'),
    ('OC(=O)C1CCCCC1', 'циклогексанкарбоновая кислота', 'cyclohexanecarboxylic acid', '环己烷甲酸'),
    ('O=CC1CCCCC1', 'циклогексанкарбальдегид', 'cyclohexanecarbaldehyde', '环己烷甲醛'),
    ('Nc1ccccc1', 'анилин', 'aniline', '苯胺'),
    ('Clc1ccc(O)cc1', '4-хлорфенол', '4-chlorophenol', '4-氯苯酚'),
    ('Oc1ccc(cc1)[N+](=O)[O-]', '4-нитрофенол', '4-nitrophenol', '4-硝基苯酚'),
    ('OC(=O)c1ccc(Cl)cc1', '4-хлорбензойная кислота', '4-chlorobenzoic acid', '4-氯苯甲酸'),
    ('Oc1ccccc1O', 'бензол-1,2-диол', 'benzene-1,2-diol', '1,2-苯二酚'),
    ('Cc1ccccc1C', '1,2-диметилбензол', '1,2-dimethylbenzene', '1,2-二甲苯'),
    ('Cc1cc(C)cc(C)c1', '1,3,5-триметилбензол', '1,3,5-trimethylbenzene', '1,3,5-三甲苯'),
    ('CCc1ccccc1', 'этилбензол', 'ethylbenzene', '乙苯'),
    ('CC(C)c1ccccc1', 'изопропилбензол', 'isopropylbenzene', '异丙苯'),
    ('C=Cc1ccccc1', 'этенилбензол', 'ethenylbenzene', '苯乙烯'),
    ('CN(C)c1ccccc1', 'N,N-диметиланилин', 'N,N-dimethylaniline', 'N,N-二甲基苯胺'),
    ('OCc1ccccc1', 'фенилметанол', 'phenylmethanol', '苯甲醇'),
    ('CC(=O)c1ccccc1', '1-фенилэтанон', '1-phenylethanone', '苯乙酮'),
    ('C(C=O)C#N', '3-оксопропаннитрил', '3-oxopropanenitrile', '3-氧代丙腈'),
    ('CCC(C=C)CCl', '3-(хлорметил)пент-1-ен', '3-(chloromethyl)pent-1-ene', '3-(氯甲基)-1-戊烯'),
    ('CC(C)CN(C)C', 'N,N,2-триметилпропан-1-амин', 'N,N,2-trimethylpropan-1-amine', 'N,N,2-三甲基-1-丙胺'),
    ('CNCC(Cl)C', 'N-метил-2-хлорпропан-1-амин', '2-chloro-N-methylpropan-1-amine', 'N-甲基-2-氯-1-丙胺'),
    ('CCC(CC(=O)OC)CC', 'метил-3-этилпентаноат', 'methyl 3-ethylpentanoate', '3-乙基戊酸甲酯'),
    ('FC(Cl)Cl', 'фтордихлорметан', 'dichlorofluoromethane', '氟二氯甲烷'),
    ('c1ccccc1-c1ccccc1', 'бифенил', 'biphenyl', '联苯'),
    ('CCCCCCCCCCCC', 'додекан', 'dodecane', '十二烷'),
    ('C.C', '2 × метан', '2 × methane', '2 × 甲烷'),
]
NOT_NAMED = [
    'NCC(N(C)C)CC',  # N-substituted diamine: N1/N2 locants are not written
    'O',
    'N',
    'CS',
    'C#N',
    'ClC(Cl)=O',
    'CC(Cl)=O',
    'O=C(OC)OC',
    'NC(=O)N',
    'O=C=O',
    'c1ccncc1',
    'c1ccc2ccccc2c1',
    'C1CO1',
    'C1CCC(CC1)C1CCCCC1',
    'CC.O',
    'CC(=O)NC',
]
RETAINED = {  # the table uses a common name; ours is the systematic one
    ('zh', '甲醚（二甲醚） · C₂H₆O'),
    ('zh', '乙醚 · C₄H₁₀O'),
    ('zh', '三甲胺 · C₃H₉N'),
    ('zh', '四氯化碳 · CCl₄'),
    ('zh', '四氟化碳 · CF₄'),
    ('zh', '丙二烯 · C₃H₄'),
    ('ru', 'Пропадиен (аллен) · C₃H₄'),
    ('en', 'Propadiene (allene) · C₃H₄'),  # ours: propa-1,2-diene
    # the library names acetophenone by IUPAC 2013 with the locant of the suffix; ours follows 1993
    # (iupac.py §2: no locant for a two-carbon parent) — 1-фенилэтанон / 1-phenylethanone; both are correct
    ('ru', '1-фенилэтан-1-он (ацетофенон) · C₈H₈O'),
    ('en', '1-phenylethan-1-one (acetophenone) · C₈H₈O'),
    # common names of the molecules added in 0.89.0 (ours in brackets)
    ('zh', '对二甲苯 · C₈H₁₀'),  # 1,4-二甲苯
    ('zh', '对苯醌 · C₆H₄O₂'),  # 2,5-环己二烯-1,4-二酮
    ('zh', '叔丁醇 · C₄H₁₀O'),  # 2-甲基-2-丙醇
    ('zh', '草酸 · C₂H₂O₄'),  # 乙二酸
    ('ru', 'Глицин · C₂H₅NO₂'), ('en', 'Glycine · C₂H₅NO₂'), ('zh', '甘氨酸 · C₂H₅NO₂'),  # 2-аминоэтановая кислота
    ('ru', 'Аланин · C₃H₇NO₂'), ('en', 'Alanine · C₃H₇NO₂'), ('zh', '丙氨酸 · C₃H₇NO₂'),  # 2-аминопропановая кислота
    ('zh', '二甲胺 · C₂H₇N'),  # N-甲基甲胺
}


@pytest.mark.parametrize('case', NAMED)
def test_names_in_three_languages(case):
    smiles, *expected = case
    molecule = from_smiles(smiles)
    assert [iupac.name(molecule, lang) for lang in iupac.LANGS] == expected


@pytest.mark.parametrize('smiles', NOT_NAMED)
def test_structures_outside_the_rules_are_not_named(smiles):
    molecule = from_smiles(smiles)
    assert all(iupac.name(molecule, lang) is None for lang in iupac.LANGS)


def _systematic(text):
    return re.sub(r'\s*[(（][^)）]*[)）]', '', text.split(' · ')[0]).strip().lower()


def test_library_names_are_reproduced():
    checked = 0
    for key in library.keys():
        if key not in library.NAMES:
            continue
        molecule = library.molecule(key)
        for k, lang in enumerate(('ru', 'en', 'zh')):
            ours = iupac.name(molecule, lang)
            table = library.NAMES[key][k]
            if ours is None or (lang, table) in RETAINED:
                continue
            assert ours.lower() == _systematic(table), (key, lang)
            checked += 1
    assert checked >= 110  # 118 names on 2026-10-23 (42 named structures x 3, minus RETAINED)


def test_name_does_not_depend_on_atom_order_or_hydrogens_being_drawn():
    rng = random.Random(7)
    for smiles in ('CC(C)CCC(CC)C(C)C', 'CC(O)CC(C)=O', 'Clc1ccc(O)cc1', 'CC(=O)OC(C)C'):
        molecule = from_smiles(smiles)
        reference = iupac.name(molecule, 'en')
        order = list(range(len(molecule.atoms)))
        rng.shuffle(order)
        where = {old: new for new, old in enumerate(order)}
        bonds = tuple((where[i], where[j], o) for i, j, o in perceived_orders(molecule))
        shuffled = Molecule('', tuple(molecule.atoms[i] for i in order), bonds)
        assert iupac.name(shuffled, 'en') == reference
    ethanol = library.molecule(next(k for k in library.keys() if k.startswith('Этанол')))
    heavy = Molecule('', tuple(a for a in ethanol.atoms if a.symbol != 'H'))  # bonds from the distances
    assert iupac.name(heavy, 'ru') == 'этанол'


def test_unknown_language():
    with pytest.raises(ValueError):
        iupac.name(from_smiles('C'), 'de')


def test_empty_and_odd_valence_structures():
    assert iupac.name(Molecule('', ()), 'ru') is None
    methyl = Molecule(
        '',
        (Atom('C', 0, 0, 0), Atom('H', 1.09, 0, 0), Atom('H', -0.5, 0.94, 0), Atom('H', -0.5, -0.94, 0)),
        ((0, 1, 1), (0, 2, 1), (0, 3, 1)),
    )
    assert iupac.name(methyl, 'ru') is None  # a radical: CH3 has a free valence


def test_smiles_writer_reads_back_to_the_same_graph():
    for key in library.keys():
        molecule = library.molecule(key)
        symbols, bonds, _ = smiles_graph(pubchem.to_smiles(molecule))
        own = signature([a.symbol for a in molecule.atoms], [(i, j) for i, j, _ in perceived_orders(molecule)])
        assert signature(symbols, bonds) == own, key
    assert pubchem.to_smiles(Molecule('', ())) == ''


class _Response:
    def __init__(self, text):
        self.text = text

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return self.text.encode()


def test_pubchem_lookup_with_a_fake_server():
    asked = []

    def ok(url, timeout):
        asked.append((url, timeout))
        return _Response('propan-2-one\n')

    assert pubchem.lookup('CC(=O)C', urlopen=ok) == 'propan-2-one'
    assert asked == [
        ('https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/CC%28%3DO%29C/property/IUPACName/txt', 8.0)
    ]

    def missing(url, timeout):
        raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)

    assert pubchem.lookup('C[Xe]', urlopen=missing) is None

    def offline(url, timeout):
        raise urllib.error.URLError('no network')

    with pytest.raises(OSError):
        pubchem.lookup('C', urlopen=offline)
    assert pubchem.lookup('') is None


def test_button_keeps_the_name_until_the_structure_changes(monkeypatch):
    pytest.importorskip('PySide6')
    from modules.compass.actions import naming_actions

    class Host:  # a fake window — NamingTool reaches it through its port
        def __init__(self, molecule):
            self.molecule, self.messages, self.updates = molecule, [], 0
            self.iupac_button = type('B', (), {'setEnabled': lambda self, on: None})()
            self.symmetry_tool = type('S', (), {'update_symmetry': lambda s: setattr(self, 'updates', self.updates + 1)})()

        def notify(self, text, ms=8000):
            self.messages.append(text)

    import modules.compass.workspace as workspace

    monkeypatch.setattr(workspace, 'LANG_CODE', lambda: 'en')
    host = Host(from_smiles('CC(O)C'))
    tool = naming_actions.NamingTool(host)
    tool.show_iupac_name()
    assert tool.iupac_title(host.molecule, 'ru') == 'пропан-2-ол'
    assert tool.iupac_title(host.molecule, 'zh') == '2-丙醇'
    assert tool.iupac_title(from_smiles('CCCO'), 'ru') is None  # another structure: the name is dropped
    host = Host(from_smiles('c1ccncc1'))  # not by the rules: the names table
    tool = naming_actions.NamingTool(host)
    tool.show_iupac_name()
    assert tool.iupac_title(host.molecule, 'ru') == 'пиридин'
    tool._pubchem_answer((naming_actions.topology(host.molecule), 'pyridine', None))
    assert tool.iupac_title(host.molecule, 'ru') == 'pyridine'  # the English PubChem name stays English


def test_pubchem_knows_root_certificates_and_names_what_failed():
    # on the Python of python.org (macOS) urllib had no root certificates, every request failed with
    # CERTIFICATE_VERIFY_FAILED and Compass said «no internet»; the context now always has root certificates
    import socket
    import ssl

    assert pubchem._ssl_context().cert_store_stats().get('x509_ca', 0) > 0
    bad_cert = urllib.error.URLError(ssl.SSLCertVerificationError(1, '[SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed'))
    assert pubchem.reason(bad_cert) == 'certificate'
    assert pubchem.reason(urllib.error.URLError(socket.timeout('timed out'))) == 'timeout'
    assert pubchem.reason(TimeoutError()) == 'timeout'
    assert pubchem.reason(urllib.error.HTTPError('u', 503, 'Busy', {}, None)) == 'server'
    assert pubchem.reason(urllib.error.URLError(socket.gaierror(8, 'nodename nor servname'))) == 'network'


def test_pubchem_inchi_with_a_fake_server():
    # InChI and InChIKey of the coordinates tab, by the SMILES of the structure
    import json

    asked = []

    def ok(url, timeout):
        asked.append(url)
        return _Response(json.dumps({'PropertyTable': {'Properties': [
            {'CID': 962, 'InChI': 'InChI=1S/H2O/h1H2', 'InChIKey': 'XLYOFNOQVPJJNP-UHFFFAOYSA-N'}]}}))

    assert pubchem.lookup_inchi('O', urlopen=ok) == ('InChI=1S/H2O/h1H2', 'XLYOFNOQVPJJNP-UHFFFAOYSA-N')
    assert asked == ['https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/smiles/O/property/InChI,InChIKey/JSON']

    def missing(url, timeout):
        raise urllib.error.HTTPError(url, 404, 'Not Found', {}, None)

    assert pubchem.lookup_inchi('C[Xe]', urlopen=missing) is None
    assert pubchem.lookup_inchi('', urlopen=ok) is None

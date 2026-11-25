"""Names of common molecules (modules/compass/chemistry/names.py)."""

from collections import Counter

from modules.compass.chemistry.names import NAMES, name, parse_smiles, signature


def test_every_entry_is_a_distinct_structure():
    seen = {}
    for smiles, ru, en, zh in NAMES:
        assert ru and en and zh
        key = signature(*parse_smiles(smiles))
        assert key not in seen, (ru, seen.get(key))
        seen[key] = ru


def test_smiles_reader_adds_the_hydrogens():
    def formula(smiles):
        symbols, _ = parse_smiles(smiles)
        return dict(Counter(symbols))

    assert formula('c1ccccc1') == {'C': 6, 'H': 6}
    assert formula('c1cc[nH]c1') == {'C': 4, 'N': 1, 'H': 5}
    assert formula('CC(O)=O') == {'C': 2, 'O': 2, 'H': 4}
    assert formula('CS(C)=O') == {'C': 2, 'S': 1, 'O': 1, 'H': 6}
    assert formula('[NH4+]') == {'N': 1, 'H': 4}
    # an aromatic nitrogen with three bonds has no hydrogen (its lone pair is in the ring): N-methylpyrrole C5H7N,
    # N-methylimidazole C4H6N2, N-methyl-2-pyridone C6H7NO, caffeine C8H10N4O2 (the formulas of the handbooks) — each
    # got one hydrogen too many, and a calculation of caffeine was refused for its odd number of electrons
    assert formula('Cn1cccc1') == {'C': 5, 'H': 7, 'N': 1}
    assert formula('Cn1ccnc1') == {'C': 4, 'H': 6, 'N': 2}
    assert formula('Cn1ccccc1=O') == {'C': 6, 'H': 7, 'N': 1, 'O': 1}
    assert formula('Cn1cnc2c1c(=O)n(C)c(=O)n2C') == {'C': 8, 'H': 10, 'N': 4, 'O': 2}
    assert formula('c1ccncc1') == {'C': 5, 'H': 5, 'N': 1} and formula('c1ccn2cccc2c1') == {'C': 8, 'H': 7, 'N': 1}  # indolizine


def test_isomers_get_their_own_names_and_pieces_are_joined():
    assert name(*parse_smiles('CCO')) == 'этанол'
    assert name(*parse_smiles('COC'), 'en') == 'methoxymethane (dimethyl ether)'
    symbols, bonds = parse_smiles('O')
    two = symbols + symbols, bonds + [(i + 3, j + 3) for i, j in bonds]
    assert name(*two) == '2 × вода'
    assert name(symbols + ['Xe'], bonds) == ''  # an unknown piece: no name at all
    # order of atoms does not matter
    s, b = parse_smiles('CCO')
    perm = list(reversed(range(len(s))))
    assert name([s[i] for i in perm], [(perm.index(i), perm.index(j)) for i, j in b], 'zh') == '乙醇'

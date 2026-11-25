"""The localized orbitals of Multiwfn (modules/spectrum/wavefunction/multiwfn_lmo.py).

Oracles: the outputs of Multiwfn 2026.7.15 recorded on the Mac of the user by tools/record_multiwfn_lmo.py
(tests/data/multiwfn/lmo_*.txt and the new.fch it wrote, gzip) — water of Gaussian 16 and benzaldehyde of ORCA (Molden,
def2-SVPD), Pipek–Mezey with Mulliken populations; the list of methods of item −6. The kinds are checked against
chemistry: water has one core, two O–H bonds and two lone pairs; benzaldehyde C7H6O has 8 cores (7 C, 1 O) and 28
occupied orbitals.
"""

import gzip
import re
from pathlib import Path

import pytest

from modules.spectrum.wavefunction import multiwfn_lmo as ml
from modules.spectrum.readers.orbital_files import read_orbitals

MWFN = Path(__file__).parents[1] / 'data' / 'multiwfn'


def text(name):
    return (MWFN / name).read_text(encoding='utf-8', errors='replace')


def lmo_set(name):
    return read_orbitals(gzip.decompress((MWFN / f'{name}__new.fch.gz').read_bytes()).decode('utf-8', 'replace'))


def test_methods_are_the_items_multiwfn_lists():
    listing = text('lmo_methods.txt')
    for key, item in ml.METHODS.items():
        assert re.search(rf'^\s*{item}\s+(Pipek-Mezey|Foster-Boys)', listing, re.M), key
    assert ml.answers('boys') == ('19', '-6', '10', '1', '0', 'q')
    assert 'answers: ' + ' | '.join(ml.answers('pm')[:2]) in listing  # −6 answered after 19, as recorded


def test_summary_of_water():
    summary = ml.parse_summary(text('lmo_water_pm.txt'))
    a = lambda n: ('alpha', n)  # noqa: E731 — a closed shell: the orbitals of the file are «alpha»
    assert summary[a(1)] == ('one', [(1, 'O', 99.7)])
    assert summary[a(2)] == ('two', [(1, 'O', 63.4), (2, 'H', 33.8)])
    assert sorted(n for _, n in summary) == [1, 2, 3, 4, 5]
    orbitals = lmo_set('lmo_water_pm')
    named = ml.kinds(summary, orbitals)
    assert [named[a(n)] for n in range(1, 6)] == ['остов', 'связь', 'связь', 'НП', 'НП']
    assert ml.describe(summary[a(2)][1]) == 'O1–H2 63/34 %' and ml.describe(summary[a(4)][1]) == 'O1 96 %'


def test_summary_of_benzaldehyde_with_the_delocalized_ones():
    summary = ml.parse_summary(text('lmo_benzaldehyde_pm.txt'))
    assert sorted(n for _, n in summary) == list(range(1, 29))  # every occupied orbital of C7H6O has its kind
    assert summary[('alpha', 10)] == ('more', [(4, 'C', 48.9), (10, 'H', 23.1), (5, 'C', 14.8)])
    named = ml.kinds(summary, lmo_set('lmo_benzaldehyde_pm'))
    named = {n: v for (_, n), v in named.items()}
    assert [named[n] for n in range(1, 9)] == ['остов'] * 8  # O 1s and the seven C 1s
    assert named[9] == named[26] == 'НП' and named[21] == named[22] == 'связь'  # the lone pairs and C=O of O1


def test_boys_puts_the_core_anywhere_and_becke_keeps_the_ch_bonds():
    # Boys: the O 1s of water is LMO 5 (99.8 %), the lone pairs 1 and 4 (94.1 %) — the core is the most localized
    summary = ml.parse_summary(text('lmo_water_boys.txt'))
    named = ml.kinds(summary, lmo_set('lmo_water_boys'))
    assert [named[('alpha', n)] for n in range(1, 6)] == ['НП', 'связь', 'связь', 'НП', 'остов']
    # Pipek–Mezey with Becke populations (the diffuse def2-SVPD): every C–H is a two-center bond, three π delocalized
    becke = ml.parse_summary(text('lmo_benzaldehyde_pm_becke.txt'))
    kinds = [kind for kind, _ in becke.values()]
    assert len(becke) == 28 and kinds.count('more') == 3
    ch = [shares for kind, shares in becke.values() if kind == 'two' and {s for _, s, _ in shares} == {'C', 'H'}]
    assert len(ch) == 6  # C7H6O: six C–H bonds
    assert len(ml.parse_summary(text('lmo_benzaldehyde_boys.txt'))) == 28


def test_an_open_shell_is_localized_with_the_composition_by_mulliken():
    # with −9 → 1 Multiwfn localized α and β of the cation (C10H10+: 35 α, 34 β electrons); β numbered from 1 again
    assert ml.answers('pm', open_shell=True) == ('19', '-9', '1', '-6', '1', '1', '0', 'q')
    output = text('lmo_cation_pm_mulliken.txt')
    assert output.startswith('answers: 19 | -9 | 1 | 1')  # recorded: −9 → 1, then the localization (the default method)
    summary = ml.parse_summary(output)
    alpha = sorted(n for spin, n in summary if spin == 'alpha')
    beta = sorted(n for spin, n in summary if spin == 'beta')
    assert alpha == list(range(1, 36)) and beta == list(range(1, 35))
    orbitals = lmo_set('lmo_cation_pm_mulliken')
    assert orbitals.unrestricted
    named = ml.kinds(summary, orbitals)
    for spin in ('alpha', 'beta'):
        assert sum(1 for (s, _), v in named.items() if s == spin and v == 'остов') == 10  # the ten C 1s


def test_core_count_with_and_without_an_ecp():
    assert [ml.core_count(z) for z in (1, 6, 8, 17, 42)] == [0, 1, 1, 5, 18]
    assert ml.core_count(42, 14) == 4 and ml.core_count(17, 7) == 0  # Mo and Cl of an ECP (28 and 10 core electrons)


def test_the_file_of_the_localized_orbitals_is_read():
    orbitals = lmo_set('lmo_water_pm')
    canonical = read_orbitals((Path(__file__).parents[1] / 'data' / 'orbitals' / 'water_mp2_g16.fchk').read_text(encoding='utf-8'))
    assert len(orbitals.orbitals) == len(canonical.orbitals) == 7 and not orbitals.unrestricted
    assert [a.symbol for a in orbitals.molecule.atoms] == [a.symbol for a in canonical.molecule.atoms]
    # the occupied orbitals are new (localized), the virtual ones the canonical ones of the file
    import numpy as np

    assert not np.allclose(np.abs(orbitals.coefficients[:, 1]), np.abs(canonical.coefficients[:, 1]), atol=1e-3)
    assert np.allclose(np.abs(orbitals.coefficients[:, 5]), np.abs(canonical.coefficients[:, 5]), atol=1e-5)


def test_run_lmo_refuses_when_multiwfn_wrote_nothing(monkeypatch):
    # the open shell of the cation: Multiwfn fell (SIGSEGV) after its α orbitals — no new.fch
    monkeypatch.setattr(ml.multiwfn, '_run', lambda *a, **k: (text('lmo_cation_pm.txt'), {}))
    with pytest.raises(ValueError, match='не записал'):
        ml.run_lmo('Multiwfn', 'x.molden')
    fch = gzip.decompress((MWFN / 'lmo_water_pm__new.fch.gz').read_bytes()).decode()
    monkeypatch.setattr(ml.multiwfn, '_run', lambda *a, **k: (text('lmo_water_pm.txt'), {'new.fch': fch}))
    got, summary, _ = ml.run_lmo('Multiwfn', 'x.fchk', 'pm')
    assert got == fch and len(summary) == 5

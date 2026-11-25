"""Natural transition orbitals of ORCA: the printout of a real output (tests/data/orca_nto/README.md) and the
index of an NTO in the orbitals read from its file."""

from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.spectrum.analysis import nto

DATA = Path(__file__).parents[1] / 'data' / 'orca_nto'


def test_the_pairs_of_each_state_heaviest_first():
    found = nto.read_ntos((DATA / 'open_shell_tda_nto_excerpt.out').read_text(encoding='utf-8'))
    assert sorted(found) == [1, 2]
    one = found[1]
    assert one.file == 'OrcaRun.s1.nto' and one.energy_ev == pytest.approx(1.898)
    assert len(one.pairs) == 13  # every printed pair, α and β
    assert one.pairs[0] == nto.NtoPair(320, 321, 'b', 0.96066403)
    assert one.pairs[1] == nto.NtoPair(319, 322, 'b', 0.03066164)
    assert sum(p.weight for p in one.pairs) == pytest.approx(1.0, abs=0.003)  # the weights add up to about 1
    assert nto.describe(one) == '320b → 321b · 0.961; 319b → 322b · 0.031'
    assert found[2].file == 'OrcaRun.s2.nto' and found[2].pairs[0].weight == pytest.approx(0.95627403)
    assert nto.read_ntos('no NTO here') == {}


def test_where_the_file_is_and_which_orbital_is_which(tmp_path):
    entry = nto.NtoState(3, 2.1, '', ())
    assert nto.nto_gbw(tmp_path / 'water.out', entry) == tmp_path / 'water.s3.nto'  # the name when none was printed
    named = nto.NtoState(1, 1.9, 'OrcaRun.s1.nto', ())
    assert nto.nto_gbw(tmp_path / 'run' / 'OrcaRun.out', named) == tmp_path / 'run' / 'OrcaRun.s1.nto'
    with pytest.raises(ValueError, match='DoNTO'):
        nto.nto_orbitals(tmp_path / 'water.out', entry)
    orbitals = [SimpleNamespace(spin='alpha')] * 4 + [SimpleNamespace(spin='beta')] * 4
    restricted = SimpleNamespace(orbitals=orbitals[:4])
    unrestricted = SimpleNamespace(orbitals=orbitals)
    assert nto.orbital_index(restricted, 'a', 2) == 2
    assert nto.orbital_index(unrestricted, 'b', 1) == 5  # after the four α orbitals
    with pytest.raises(ValueError):
        nto.orbital_index(restricted, 'a', 4)

"""Delocalization indices and the aromaticity of rings — the outputs of Multiwfn 2026.7.15 recorded on the
user's Mac by tools/record_multiwfn_fuzzy.py (tests/data/multiwfn/fuzzy_*.txt), HOMA by its formula."""

import gzip
import re
from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry.builder import connections
from azimuth.core import Atom, Molecule
from modules.spectrum.analysis import delocalization as d
from modules.spectrum.readers.orbital_files import read_orbitals

DATA = Path(__file__).parents[1] / 'data' / 'multiwfn'


def recorded(name):
    return (DATA / f'fuzzy_{name}.txt').read_text(encoding='utf-8')


def test_delocalization_indices_of_multiwfn():
    water = d.parse_lidi(recorded('water_lidi'))
    assert water['di'] == pytest.approx(np.array([[1.87886132, 0.93943066, 0.93943066],
                                                  [0.93943066, 0.96326101, 0.02383035],
                                                  [0.93943066, 0.02383035, 0.96326101]]))
    assert list(water['li']) == [7.639, 0.229, 0.229]
    metal = d.parse_lidi(recorded('MoOCl4_lidi'))  # six columns: two blocks of the matrix
    assert metal['di'].shape == (6, 6) and metal['di'][0, 1] == pytest.approx(2.68857161)  # Mo=O
    assert metal['di'][5, 5] == pytest.approx(1.58129811) and metal['li'][0] == pytest.approx(11.212)
    for di in (water['di'], metal['di']):  # the diagonal is the valence: the sum of its row
        assert np.allclose(np.diag(di), di.sum(axis=1) - np.diag(di), atol=1e-6)
    cation = d.parse_lidi(recorded('dvb_lidi'))  # open shell: α, β, then the totals — the totals are taken
    assert cation['di'].shape == (20, 20) and cation['di'][0, 2] == pytest.approx(1.28232079)
    assert cation['li'][0] == pytest.approx(3.832)


def test_aromaticity_of_multiwfn_and_homa():
    assert d.parse_rings(recorded('benzaldehyde_pdi'))['pdi'] == [0.098111]
    assert d.parse_rings(recorded('benzaldehyde_flu'))['flu'] == [0.001165]
    assert d.parse_rings(recorded('benzaldehyde_mci'))['mci'][0] == (0.0175886, 0.5099628)
    # the recipe of the program — PDI, FLU and MCI in one run of Multiwfn (recorded with ring_answers): the same values
    assert d.parse_rings(recorded('benzaldehyde_rings')) == {'pdi': [0.098111], 'flu': [0.001165],
                                                            'mci': [(0.0175886, 0.5099628)]}
    molecule = read_orbitals(gzip.decompress((DATA / 'benzaldehyde_cam-b3lyp_def2-svpd.molden.gz').read_bytes())
                             .decode('utf-8')).molecule
    rings = d.rings(molecule, connections(molecule))
    assert rings == [(2, 3, 4, 5, 6, 7)]  # the benzene ring, C3…C8, not the C=O side
    assert d.ring_answers(rings) == ('15', '5', '3,4,5,6,7,8', 'q', '6', '3,4,5,6,7,8', 'q', '11', '3,4,5,6,7,8', 'q',
                                     '0', 'q')
    # our HOMA is that of Multiwfn (menu 25 → 6 → 0, «HOMA value is 0.999079»)
    value = float(re.search(r'HOMA value is\s+([\d.]+)', recorded('benzaldehyde_homa_value')).group(1))
    assert d.homa(molecule, rings[0]) == pytest.approx(value, abs=1e-6)
    # HOMA by its formula: a regular hexagon with R_opt is 1, the Kekulé structure (1.33 / 1.52 Å) about 0
    import math

    def hexagon(sides):
        atoms, x, y, angle = [], 0.0, 0.0, 0.0
        for side in sides:
            atoms.append(Atom('C', x, y, 0.0))
            x, y, angle = x + side * math.cos(angle), y + side * math.sin(angle), angle + math.pi / 3
        return Molecule('', tuple(atoms))

    assert d.homa(hexagon([1.388] * 6), range(6)) == pytest.approx(1.0, abs=1e-9)
    kekule = d.homa(hexagon([1.33, 1.52] * 3), range(6))
    assert kekule == pytest.approx(1 - 257.7 * ((1.388 - 1.33) ** 2 + (1.388 - 1.52) ** 2) / 2, abs=0.02)
    assert d.homa(Molecule('', (Atom('C', 0, 0, 0), Atom('Si', 1.9, 0, 0), Atom('C', 0.95, 1.4, 0))), (0, 1, 2)) is None
    # the parameters are the defaults Multiwfn prints (menu 25 → 6 → 1)
    printed = recorded('benzaldehyde_homa')
    for (a, b), (r, alpha) in d.HOMA_PARAMETERS.items():
        assert re.search(rf'{a}\s*-\s*{b}\s*:\s+{r:.4f}\s+{alpha:.4f}', printed), (a, b)


def test_rings_of_naphthalene_are_the_two_hexagons():
    import math

    # two fused hexagons: the perimeter of ten is not a ring of its own, the shared bond is no chord of a hexagon
    points = [(0, 0), (1.4, 0), (2.1, 1.21), (1.4, 2.42), (0, 2.42), (-0.7, 1.21),
              (3.5, 1.21), (4.2, 2.42), (3.5, 3.63), (2.1, 3.63)]
    mol = Molecule('', tuple(Atom('C', x, y, 0.0) for x, y in points))
    bonds = [(i, j, 1) for i in range(10) for j in range(i + 1, 10)
             if 1.3 < math.dist(points[i], points[j]) < 1.5]
    found = d.rings(mol, bonds)
    assert len(found) == 2 and all(len(r) == 6 for r in found)

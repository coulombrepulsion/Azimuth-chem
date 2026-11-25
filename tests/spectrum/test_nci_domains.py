"""Weak interactions told apart by NCI (modules/spectrum/analysis/nci_domains.py).

Oracles: the grids of the S22 water dimer recorded with Multiwfn 2026.7.15 (B3LYP wavefunction and promolecular
density, tests/data/multiwfn): one hydrogen bond O1–H3···O4 with the spike of the plot at sign(λ₂)ρ ≈ −0.021 and
−0.030 a.u.; promolecular grids of tests/promolecule.py for geometries built for the purpose: the linear C–Br···N of
CF3Br···NH3 (a halogen bond, IUPAC 2013), the benzene sandwich and the parallel-displaced dimer at 3.5–3.7 Å (π–π
stacking, Janiak 2000), methane with a C–H pointing at the centre of benzene (C–H···π), the centre of the benzene ring
(repulsion: sign(λ₂)ρ > 0, Johnson et al. 2010, Fig. 3), the methane dimer (van der Waals). The thresholds of the grades
as written in §1 of the module.
"""

import gzip
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import nci_domains as nd
from modules.spectrum.analysis.density import CriticalPoint, Topology
from modules.spectrum.readers.cube import read_cube
from tests.promolecule import cubes

DATA = Path(__file__).parents[1] / 'data' / 'multiwfn'
CH4 = [('C', 0, 0, 0), ('H', 0, 0, 1.09), ('H', 1.028, 0, -0.363), ('H', -0.514, 0.890, -0.363),
       ('H', -0.514, -0.890, -0.363)]


def recorded(tag):
    return [read_cube(gzip.open(DATA / f'dimer_nci_{tag}_{f}.cub.gz', 'rt', encoding='utf-8').read())
            for f in ('func1', 'func2')]


def benzene(z=0.0, dx=0.0):
    ring = [('C', 1.39 * np.cos(a) + dx, 1.39 * np.sin(a), z) for a in np.radians(np.arange(0, 360, 60))]
    return ring + [('H', 2.47 * np.cos(a) + dx, 2.47 * np.sin(a), z) for a in np.radians(np.arange(0, 360, 60))]


def run(rows, **options):
    sign, field = cubes(rows)
    return nd.find(sign, field, **options), [r[0] for r in rows]


def kinds(found):
    return [d.kind for d in found]


@pytest.mark.parametrize('tag, peak', [('low', -0.0207), ('promol', -0.0303)])
def test_the_water_dimer_from_multiwfn(tag, peak):
    sign, field = recorded(tag)
    found = nd.find(sign, field)
    symbols = [a.symbol for a in field.molecule.atoms]
    assert len(found) == 1
    hb = found[0]
    assert hb.kind == 'hydrogen' and (hb.donor, hb.site, hb.acceptor) == (0, 2, 3) and hb.atoms == (2, 3)
    assert hb.peak == pytest.approx(peak, abs=2e-4) and hb.strength == 'medium' and not hb.intra
    assert hb.energy == pytest.approx(-223.08 * -hb.peak + 0.7423) and hb.grade == 'weak-medium'
    assert hb.attractive > 0 and hb.repulsive == 0 and hb.volume > 0
    assert hb.distance == pytest.approx(1.952, abs=5e-3) and hb.angle > 170
    assert nd.label(hb, symbols) == 'водородная O1–H3···O4'
    assert 'Emamian' in nd.detail(hb, symbols)
    header, rows = nd.table(found, symbols)
    assert len(header) == len(rows[0]) and rows[0][:2] == ['водородная', 'O1–H3···O4'] and rows[0][9] == 'нет'
    centre = np.array(hb.centre)  # between H3 and O4
    xyz = np.array([a.position for a in field.molecule.atoms], float)
    assert np.linalg.norm(centre - xyz[2]) < 1.3 and np.linalg.norm(centre - xyz[3]) < 1.3


def test_the_bcp_of_the_main_pair_and_a_higher_level():
    sign, field = recorded('promol')
    point = CriticalPoint('bond', np.zeros(3), 0.024, 0.08, np.array([-0.03, -0.03, 0.14]), 0.02, 0.02, -0.016,
                          0.004, (3, 2))
    found = nd.find(sign, field, topology=Topology((point,), (), {}, 1))
    assert found[0].point is point and 'QTAIM' in nd.detail(found[0], [a.symbol for a in field.molecule.atoms])
    assert nd.find(sign, field, level=0.6)[0].volume > found[0].volume
    assert nd.find(sign, field, level=0.1) == ()
    with pytest.raises(ValueError):
        nd.find(sign, recorded('low')[1])


def test_halogen_bond():
    cf3 = [('F', 1.33 * 0.9428 * np.cos(a), 1.33 * 0.9428 * np.sin(a), -1.33 / 3) for a in (0.0, 2.0944, 4.1888)]
    ammonia = [('N', 0, 0, 4.83)] + [('H', 0.94 * np.cos(a), 0.94 * np.sin(a), 5.21) for a in (0.0, 2.0944, 4.1888)]
    found, symbols = run([('C', 0, 0, 0)] + cf3 + [('Br', 0, 0, 1.93)] + ammonia)
    xb = [d for d in found if d.kind == 'halogen']
    assert len(xb) == 1 and (xb[0].donor, xb[0].site, xb[0].acceptor) == (0, 4, 5)
    assert -0.035 < xb[0].peak < -0.010 and xb[0].strength == 'medium' and xb[0].energy is None
    assert nd.label(xb[0], symbols) == 'галогенная C1–Br5···N6'


def test_the_ring_of_benzene_repels():
    found, symbols = run(benzene())
    assert kinds(found) == ['ring']
    ring = found[0]
    assert ring.peak > 0.01 and ring.strength == 'repulsive' and ring.intra and ring.repulsive > 0
    assert np.linalg.norm(ring.centre) < 0.1 and nd.label(ring, symbols) == 'отталкивание в кольце'
    assert ring.sides == ((0, 1, 2, 3, 4, 5), ()) and nd.chain(ring, symbols) == 'Cg(C1–C6)'


@pytest.mark.parametrize('shift, z', [(0.0, 3.7), (1.5, 3.5)])
def test_benzene_dimers_stack(shift, z):
    found, symbols = run(benzene() + benzene(z, shift))
    assert sorted(kinds(found)) == ['ring', 'ring', 'stacking']
    stack = next(d for d in found if d.kind == 'stacking')
    assert stack.sides == ((0, 1, 2, 3, 4, 5), (12, 13, 14, 15, 16, 17)) and stack.strength == 'weak'
    assert abs(stack.peak) < 0.01 and stack.centre[2] == pytest.approx(z / 2, abs=0.3)
    assert nd.chain(stack, symbols) == 'Cg(C1–C6)···Cg(C13–C18)' and nd.label(stack, symbols) == 'π-стэкинг'


def test_ch_pi():
    methane = [(s, x, y, 3.59 - z) for s, x, y, z in CH4]  # its C–H points down at the centre of the ring, H at 2.5 Å
    found, symbols = run(benzene() + methane)
    assert kinds(found) == ['ch-pi', 'ring']
    ch = found[0]
    assert (ch.donor, ch.site) == (12, 13) and symbols[ch.acceptor] == 'C' and ch.angle > 170
    assert ch.strength == 'weak' and ch.energy is None and nd.label(ch, symbols).startswith('C–H···π C13–H14···C')


def test_methane_dimer_is_van_der_waals():
    other = [('C', 0, 0, 3.7)] + [('H', 1.028 * np.cos(a), 1.028 * np.sin(a), 3.337) for a in np.radians((60, 180, 300))]
    found, symbols = run(CH4 + other + [('H', 0, 0, 4.79)])
    assert kinds(found) == ['vdw'] and not found[0].intra and found[0].peak < 0
    assert nd.chain(found[0], symbols) == 'H2···C6'


def test_pieces_join_by_26_neighbours_and_drop_the_small():
    mask = np.zeros((6, 6, 6), bool)
    mask[1, 1, 1] = mask[2, 2, 2] = mask[3, 3, 3] = True  # diagonal: one piece
    mask[5, 5, 0] = True  # alone
    flat, label = nd._pieces(mask)
    assert len(flat) == 4 and len(set(label[:3])) == 1 and label[3] != label[0]
    assert nd._pieces(np.zeros((3, 3, 3), bool))[0].size == 0


def test_promolecular_igm_finds_the_hydrogen_bond_by_delta_g_inter():
    rows = [(a.symbol, *a.position) for a in recorded('promol')[1].molecule.atoms]
    sign, field = cubes(rows, fragments=[[0, 1, 2], [3, 4, 5]])
    found = nd.find(sign, field, kind='igmh')
    assert [d.kind for d in found] == ['hydrogen'] and found[0].atoms == (2, 3) and found[0].peak < -0.02

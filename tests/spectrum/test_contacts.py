"""Weak interactions named after a QTAIM search (modules/spectrum/analysis/contacts.py).

Oracles: the IUPAC definitions of the hydrogen (2011), halogen (2013), chalcogen (2019) and pnictogen (2023) bonds —
an electrophilic site pointing at a nucleophile — on geometries built for the purpose (a linear C–Br···N is a
halogen bond, the same at 120° is not); the S22 water dimer (CCSD(T)/cc-pVQZ geometry: O–H···O, H···O 1.95 Å);
the fitted equation of Emamian et al. (J. Comput. Chem. 2019, 40, 2868) as printed, BE = −223.08 ρ + 0.7423 kcal/mol
for neutral complexes and −332.34 ρ − 1.0661 for charged ones; the regions of |V|/G of Espinosa et al. (J. Chem.
Phys. 2002, 117, 5529): < 1, 1–2, > 2.
"""

import numpy as np
import pytest

from azimuth.core import Atom, Molecule
from modules.spectrum.analysis import contacts
from modules.spectrum.analysis.density import CriticalPoint, Topology

DIMER = [('O', -1.551007, -0.114520, 0.0), ('H', -1.934259, 0.762503, 0.0), ('H', -0.599677, 0.040712, 0.0),
         ('O', 1.350625, 0.111469, 0.0), ('H', 1.680398, -0.373741, -0.758561),
         ('H', 1.680398, -0.373741, 0.758561)]


def molecule(rows):
    return Molecule('test', tuple(Atom(s, x, y, z) for s, x, y, z in rows))


def bcp(i, j, rho, g=0.02, v=-0.016):
    return CriticalPoint('bond', np.zeros(3), rho, 0.08, np.array([-0.03, -0.03, 0.14]), 0.02, g, v, g + v, (i, j))


def topology(*points):
    return Topology(tuple(points), (), {}, 1)


def ammonia(z, sign=1.0):
    """NH3 with its lone pair at −sign·z towards the origin, N at (0, 0, z)."""
    return [('N', 0.0, 0.0, z)] + [('H', 0.94 * np.cos(a), 0.94 * np.sin(a), z + sign * 0.38)
                                   for a in (0.0, 2.0944, 4.1888)]


def tetrahedral(centre, symbol, bond, axis_atom):
    """centre with one ligand along −z and three others (a C3v fragment)."""
    out = [(centre, 0.0, 0.0, 0.0), (axis_atom, 0.0, 0.0, -bond)]
    for a in (0.0, 2.0944, 4.1888):
        out.append((symbol, bond * 0.9428 * np.cos(a), bond * 0.9428 * np.sin(a), bond / 3))
    return out


def find(found, kind):
    return [c for c in found if c.kind == kind]


def test_water_dimer_hydrogen_bond_with_its_bcp():
    found = contacts.classify(molecule(DIMER), topology(bcp(0, 1, 0.36, 0.06, -0.6), bcp(2, 3, 0.024)))
    covalent, hb = found[0], found[1]
    assert covalent.kind == 'covalent' and covalent.region == 'shared'  # |V|/G = 10
    assert hb.kind == 'hydrogen' and (hb.donor, hb.site, hb.acceptor) == (0, 2, 3)
    assert hb.distance == pytest.approx(1.952, abs=2e-3) and hb.angle > 170 and not hb.intra
    assert hb.region == 'closed'  # 0.016 / 0.02 = 0.8
    assert hb.energy == pytest.approx(-223.08 * 0.024 + 0.7423) and hb.strength == 'weak-medium'
    symbols = [a[0] for a in DIMER]
    assert contacts.label(hb, symbols) == 'водородная O1–H3···O4'
    assert 'Emamian' in contacts.detail(hb, symbols) and contacts.by_point(found)[id(hb.point)] is hb
    header, rows = contacts.table(found, symbols)
    assert rows[0][:2] == ['водородная', 'O1–H3···O4'] and rows[0][5] == 'да' and rows[0][-1] == '-4.61'


def test_hydrogen_bond_without_a_bcp_and_charged_energy():
    found = contacts.classify(molecule(DIMER))
    hb = find(found, 'hydrogen')
    assert len(hb) == 1 and hb[0].point is None and hb[0].energy is None and hb[0].site == 2
    assert 'нет' in contacts.detail(hb[0], [a[0] for a in DIMER])
    charged = contacts.classify(molecule(DIMER), topology(bcp(2, 3, 0.05)), charge=-1)
    assert charged[0].energy == pytest.approx(-332.34 * 0.05 - 1.0661) and charged[0].strength == 'strong'
    assert contacts.strength(-2.0) == 'very weak' and contacts.strength(-12.0, True) == 'medium'


def test_halogen_bond_and_a_bent_contact():
    cf3br = tetrahedral('C', 'F', 1.33, 'F')
    cf3br = [(s, x, y, -z) for s, x, y, z in cf3br]  # F3C with the bromine up
    rows = [('C', 0, 0, 0)] + cf3br[2:] + [('Br', 0, 0, 1.93)] + ammonia(1.93 + 2.90)
    xb = find(contacts.classify(molecule(rows)), 'halogen')
    assert len(xb) == 1 and (xb[0].donor, xb[0].site, xb[0].acceptor) == (0, 4, 5)
    assert xb[0].angle == pytest.approx(180, abs=0.5) and xb[0].energy is None
    assert contacts.label(xb[0], [r[0] for r in rows]) == 'галогенная C1–Br5···N6'
    bent = [('C', 0, 0, 0), ('Br', 0, 0, 1.93), ('N', 2.9 * np.sin(np.radians(60)), 0, 1.93 + 2.9 * np.cos(np.radians(60)))]
    assert [c.kind for c in contacts.classify(molecule(bent))] == ['vdw']


def test_type_two_halogen_contact():
    rows = [('C', -1.94, 0, 0), ('Br', 0, 0, 0), ('Br', 3.5, 0, 0), ('C', 3.5, 1.94, 0)]
    xb = find(contacts.classify(molecule(rows)), 'halogen')
    assert len(xb) == 1 and (xb[0].site, xb[0].acceptor) == (1, 2) and xb[0].angle == pytest.approx(180)


def test_chalcogen_pnictogen_and_tetrel_bonds():
    sulfide = [('S', 0, 0, 0), ('C', 0, 0, -1.81), ('C', 1.81 * np.sin(np.radians(99)), 0, -1.81 * np.cos(np.radians(99))),
               ('O', 0, 0, 3.0), ('H', 0.76, 0, 3.0 + 0.59), ('H', -0.76, 0, 3.0 + 0.59)]
    chb = find(contacts.classify(molecule(sulfide)), 'chalcogen')
    assert len(chb) == 1 and (chb[0].donor, chb[0].site, chb[0].acceptor) == (1, 0, 3)
    pf3 = tetrahedral('P', 'F', 1.57, 'F')
    pnb = find(contacts.classify(molecule(pf3 + ammonia(3.0))), 'pnictogen')
    assert len(pnb) == 1 and (pnb[0].site, pnb[0].acceptor) == (0, 5) and pnb[0].donor == 1
    sif4 = tetrahedral('Si', 'F', 1.56, 'F')
    ttb = find(contacts.classify(molecule(sif4 + ammonia(3.0))), 'tetrel')
    assert len(ttb) == 1 and (ttb[0].site, ttb[0].acceptor) == (0, 5)


def test_methane_dimer_is_van_der_waals_and_nothing_within_a_molecule():
    ch4 = [('C', 0, 0, 0), ('H', 0, 0, 1.09), ('H', 1.028, 0, -0.363), ('H', -0.514, 0.890, -0.363),
           ('H', -0.514, -0.890, -0.363)]
    other = [(s, x, y, 3.6 - z) for s, x, y, z in ch4]
    found = contacts.classify(molecule(ch4 + other))
    assert found and all(c.kind == 'vdw' and not c.intra for c in found)
    assert ('H', 'H') in {tuple(sorted((ch4 + other)[k][0] for k in c.atoms)) for c in found}
    assert contacts.classify(molecule(ch4)) == ()  # 1–2 and 1–3 pairs are not contacts


def test_a_bent_hydrogen_bond_named_for_its_bcp():
    # the methyl C–H···O=C of caffeine
    # (B3LYP/def2-SVP: H···O 2.25 Å, C–H···O 107°, BCP ρ 0.0193, ∇²ρ 0.0725) — a hydrogen bond for the
    # BCP in the ranges of Koch and Popelier (1995), though under 120°
    def bent(angle):
        a = np.radians(angle)
        return molecule([('C', 1.09, 0.0, 0.0), ('H', 0.0, 0.0, 0.0),
                         ('O', 2.25 * np.cos(a), 2.25 * np.sin(a), 0.0)])

    def point(rho=0.0193, laplacian=0.0725):
        return CriticalPoint('bond', np.zeros(3), rho, laplacian, np.array([-0.02, -0.01, 0.10]), 1.05, 0.0167,
                             -0.0152, 0.0015, (1, 2))

    c = contacts.classify(bent(107.0), topology(point()))[0]
    assert c.kind == 'hydrogen' and c.by_bcp and c.site == 1 and c.acceptor == 2 and c.angle == pytest.approx(107.0)
    assert c.energy == pytest.approx(-223.08 * 0.0193 + 0.7423) and c.strength == 'weak-medium'
    assert 'Koch, Popelier' in contacts.detail(c, ['C', 'H', 'O'])
    assert all(k.kind != 'hydrogen' for k in contacts.classify(bent(107.0)))  # by the geometry alone: not
    assert contacts.classify(bent(107.0), topology(point(rho=0.05)))[0].kind == 'vdw'  # ρ above the range
    assert contacts.classify(bent(107.0), topology(point(laplacian=0.01)))[0].kind == 'vdw'
    assert contacts.classify(bent(85.0), topology(point()))[0].kind == 'vdw'  # beside the C–H, not at the O
    straight = contacts.classify(bent(170.0), topology(point(rho=0.05)))[0]  # at a usual angle: as before
    assert straight.kind == 'hydrogen' and not straight.by_bcp

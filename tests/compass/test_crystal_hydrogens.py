"""crystal_hydrogens: the H atoms of benzoic acid (X-ray) moved to the neutron lengths; an H across a face of the cell."""

from pathlib import Path

import numpy as np
import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_hydrogens as ch

CIF = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'


def bonds_to_h(crystal):
    rows = np.array(crystal.cell.vectors())
    atoms = cr.unit_cell(crystal)
    heavy = [(a[0], np.array(a[1:4])) for a in atoms if a[0] != 'H']
    out = []
    for a in atoms:
        if a[0] != 'H':
            continue
        best = min(((np.linalg.norm(((np.array(a[1:4]) - f + 0.5) % 1 - 0.5) @ rows), s) for s, f in heavy))
        out.append(best)
    return out


def test_benzoic_acid():
    crystal = cr.parse_cif(CIF.read_text(encoding='utf-8'))
    before = bonds_to_h(crystal)
    assert all(d < 1.0 for d, _ in before)  # X-ray: C–H 0.93–0.95, O–H 0.82–0.98
    moved, n = ch.normalized(crystal)
    after = bonds_to_h(moved)
    assert n == sum(1 for s in crystal.sites if s.symbol == 'H')
    for d, symbol in after:
        assert d == pytest.approx(ch.LENGTHS[symbol], abs=1e-6)


def test_an_h_across_a_face_and_a_lone_h():
    # O at x = 0.98, its H at x = 0.02 of the next cell (0.96 Å along a); a lone H far from any atom stays
    cell = cr.Cell(24.0, 10.0, 10.0)
    sites = (cr.Site('O1', 'O', 0.98, 0.5, 0.5), cr.Site('H1', 'H', 0.02, 0.5, 0.5), cr.Site('H2', 'H', 0.5, 0.0, 0.0))
    crystal = cr.Crystal('t', cell, sites, (cr.operation('x,y,z'),))
    moved, n = ch.normalized(crystal)
    assert n == 1
    h = moved.sites[1]
    assert (h.x - 0.98) * 24.0 == pytest.approx(0.983, abs=1e-9) or (h.x + 1 - 0.98) * 24.0 == pytest.approx(0.983)
    assert moved.sites[2] == sites[2]

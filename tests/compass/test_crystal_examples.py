"""The molecular crystal of the examples: benzoic acid of COD 7133168 — the carboxylic dimer R²₂(8),
no π–π stacking (a herringbone packing: the rings are farther than 4 Å apart)."""

from pathlib import Path

from modules.compass.chemistry import crystal as cr, crystal_contacts as cc, crystal_graphsets as gs, crystal_rings as rr

EXAMPLE = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'


def test_benzoic_acid_example():
    data = cr.parse_cif(EXAMPLE.read_text(encoding='utf-8'))
    assert data.space_group == 'P 1 21/n 1' and len(cr.unit_cell(data)) == 60  # Z = 4 × C7H6O2
    found = cc.contacts(data)
    bonds = [c for c in found if c.kind == 'hydrogen' and c.distance < 2.0]
    assert bonds and all(1.7 < c.distance < 1.9 and c.angle > 150 for c in bonds)  # O–H···O
    assert 'R²₂(8)' in gs.for_contacts(data, found)
    # the second level — the C–H···O contacts join the dimers; every name a ring or a chain of both kinds
    import re

    pairs = gs.second_level(data, found)
    assert pairs and all(re.fullmatch(r'[RC][⁰¹²³⁴⁵⁶⁷⁸⁹]*[₀₁₂₃₄₅₆₇₈₉]*\(\d+\)(, C\S*\(\d+\))?', text) for _, _, text in pairs)
    rings, stacks = rr.stacking(data)
    assert len(rings) == 4 and stacks == ()

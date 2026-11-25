"""Conformer search (modules/compass/chemistry/conformers.py).

Oracles: butane has one rotor and the three staggered conformers anti (180°) and gauche (±60°) of the
C–C–C–C dihedral (torsion.dihedral, computed again here); in pentane the two «syn-pentane» combinations
g+g− and g−g+ bring two hydrogens closer than the clash limit (the distance is measured here on a structure
turned by hand); a turn of the OH of ethanol gives three conformers, of methanol one (the CH3 makes the
three positions the same structure); rings and an amide C–N have no rotors; Boltzmann weights follow
p_k / p_0 = exp(−ΔE_k / RT).
"""

from math import exp

import numpy as np
import pytest

from modules.compass.chemistry import conformers as cf
from modules.compass.chemistry import library, torsion


def lib(prefix):
    return library.molecule(next(k for k in library.keys() if k.startswith(prefix)))


def carbon_chain(m):
    from modules.compass.chemistry.builder import connections

    carbons = [i for i, a in enumerate(m.atoms) if a.symbol == 'C']
    nb = {i: {j if k == i else k for k, j, _ in connections(m) if i in (k, j)} & set(carbons) for i in carbons}
    chain = [next(i for i in carbons if len(nb[i]) == 1)]
    while len(chain) < len(carbons):
        chain.append(next(j for j in nb[chain[-1]] if j not in chain))
    return chain


def test_butane_staggered_conformers():
    m = lib('Бутан')
    assert len(cf.rotors(m)) == 1
    found = cf.candidates(m)
    a, b, c, d = carbon_chain(m)
    angles = sorted(round(torsion.dihedral(x, a, b, c, d)) % 360 for x, _ in found)  # compared on [0, 360)
    start = torsion.dihedral(m, a, b, c, d)
    expected = sorted(round(start + k * 120) % 360 for k in range(3))
    assert len(found) == 3 and angles == expected
    assert any(cf.rmsd_heavy(x, m) < 1e-9 for x, _ in found)  # the given structure is one of them


def test_pentane_syn_combinations_clash():
    m = lib('Пентан')
    found = cf.candidates(m)
    assert len(cf.rotors(m)) == 2 and len(found) == 7  # 9 combinations without g+g− and g−g+
    (f1, m1, _), (f2, m2, _) = cf.rotors(m)
    syn = torsion.turn(torsion.turn(m, f1, m1, m1, 120), f2, m2, m2, 240)
    alt = torsion.turn(torsion.turn(m, f1, m1, m1, 240), f2, m2, m2, 120)
    hydrogens = [i for i, a in enumerate(m.atoms) if a.symbol == 'H']
    for x in (syn, alt):
        if all(cf.rmsd_heavy(x, y) >= cf.SAME for y, _ in found):  # this one was left out
            p = np.array([x.atoms[i].position for i in hydrogens])
            d = np.linalg.norm(p[:, None] - p[None], axis=2) + np.eye(len(p)) * 9
            assert d.min() < cf.CLASH * 2 * cf.RADII['H']


def test_hydroxyl_turns_rings_and_amides():
    assert len(cf.candidates(lib('Этанол'))) == 3
    assert len(cf.candidates(lib('Метанол'))) == 1
    for prefix in ('Бензол', 'Циклогексан', 'Метанамид'):
        assert cf.rotors(lib(prefix)) == []
    with pytest.raises(ValueError):
        cf.candidates(lib('Бутан'), step=70)
    with pytest.raises(ValueError):
        cf.candidates(lib('Бутан'), limit=0)


def test_random_sample_keeps_the_start():
    m = lib('Гексан')
    assert len(cf.rotors(m)) == 3
    few = cf.candidates(m, limit=10, seed=3)
    assert 1 <= len(few) <= 10 and any(cf.rmsd_heavy(x, m) < 1e-9 for x, _ in few)
    assert [round(s, 9) for _, s in cf.candidates(m, limit=10, seed=3)] == [round(s, 9) for _, s in few]  # reproducible


def test_boltzmann_weights():
    m = lib('Бутан')
    found = [x for x, _ in cf.candidates(m)]
    e0 = -15.0
    data = [(found[0], e0 + 0.001), (found[1], e0), (found[2], e0 + 0.002), (found[1], e0 + 1e-6)]  # the last: a duplicate
    out = cf.ranked(data)
    assert len(out) == 3 and out[0][1] == e0 and out[0][2] == 0.0
    assert sum(w for *_, w in out) == pytest.approx(1.0)
    dE = out[1][2]
    assert dE == pytest.approx(0.001 * cf.HARTREE_KCAL, rel=1e-12)
    assert out[1][3] / out[0][3] == pytest.approx(exp(-dE / (cf.R_KCAL * 298.15)), rel=1e-12)
    assert cf.ranked([]) == []


def test_cregen_duplicates_rotamers_and_window():
    # CREST's rules (thresholds of `crest --help`: ewin 6 kcal/mol, rthr 0.125 Å, ethr 0.05 kcal/mol,
    # bthr 1 %). Butane with one CH3 turned by 120° is the same structure with other H numbers: RMSD in the
    # fixed order 0.78 Å but the same rotational constants — a rotamer, not a new conformer.
    m = lib('Бутан')
    turned = torsion.turn(m, 1, 0, 0, 120)
    assert cf.rmsd_all(m, turned) > cf.RTHR
    assert cf.rotational_constants(turned) == pytest.approx(cf.rotational_constants(m), rel=1e-4)  # the library CH3 is C3 to 1e-5
    gauche = [x for x, _ in cf.candidates(m) if cf.rmsd_heavy(x, m) > 0.3][0]
    kcal = 1 / cf.HARTREE_KCAL
    data = [
        (m, -15.0),
        (m, -15.0 + 0.01 * kcal),  # a duplicate: ΔE < 0.05 kcal/mol and RMSD 0
        (turned, -15.0 + 0.02 * kcal),  # a rotamer of the lowest
        (gauche, -15.0 + 0.9 * kcal),
        (m, -15.0 + 3.0 * kcal),  # the same geometry but 3 kcal/mol higher: CREGEN keeps it
        (gauche, -15.0 + 7.0 * kcal),  # beyond the window
    ]
    out = cf.cregen(data)
    assert [round(r[2], 6) for r in out] == [0.0, 0.9, 3.0] and [r[4] for r in out] == [2, 1, 1]
    rt = cf.R_KCAL * 298.15
    z = 2 + exp(-0.9 / rt) + exp(-3.0 / rt)
    assert [r[3] for r in out] == pytest.approx([2 / z, exp(-0.9 / rt) / z, exp(-3.0 / rt) / z], rel=1e-12)
    assert cf.rotational_constants(m)[0] > cf.rotational_constants(m)[1] > cf.rotational_constants(m)[2]


def test_read_crest_ensemble():
    m = lib('Бутан')
    lines = m.xyz().splitlines()
    text = '\n'.join([lines[0], '  -15.12345678', *lines[2:], lines[0], ' -15.0 extra words', *lines[2:]]) + '\n'
    ensemble = cf.read_ensemble(text)
    assert [e for _, e in ensemble] == [-15.12345678, -15.0] and len(ensemble[1][0].atoms) == len(m.atoms)


def formic_acid():
    """Syn and anti formic acid fully optimized by GFN2-xTB (xtb 6.7.1, the bee colony search,
    gnorm < 2e-4): the energies on the comment lines, anti 7.09 kcal/mol above syn."""
    import re
    from pathlib import Path

    from azimuth.core import read_xyz

    out = []
    for name in ('syn', 'anti'):
        text = (Path(__file__).parents[1] / 'data' / 'conformers' / f'formic_acid_{name}_gfn2.xyz').read_text(encoding='utf-8')
        out.append((read_xyz(text), float(re.search(r'energy:\s*(-?\d+\.\d+)', text)[1])))
    return out


def test_energy_window_and_what_it_leaves_out():
    data = formic_acid()
    delta = (data[1][1] - data[0][1]) * cf.HARTREE_KCAL
    assert delta == pytest.approx(7.0910, abs=1e-3)
    assert len(cf.cregen(data)) == 1  # CREST's 6 kcal/mol: the anti form is left out ...
    count, nearest = cf.above_window(data)
    assert count == 1 and nearest == pytest.approx(delta)  # ... and the search says so
    wide = cf.cregen(data, ewin=10.0)
    assert len(wide) == 2 and wide[1][2] == pytest.approx(delta) and cf.above_window(data, 10.0) == (0, None)
    rt = cf.R_KCAL * 298.15
    assert wide[1][3] == pytest.approx(exp(-delta / rt) / (1 + exp(-delta / rt)), rel=1e-12)
    assert cf.above_window([]) == (0, None)

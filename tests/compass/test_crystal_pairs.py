"""Interaction energies of pairs, the lattice energy, the energy framework (crystal_pairs.py).

Oracles, independent of the tested code: a model energy that is a sum over all atom pairs, u(r) = −C/r⁶ — then
E(AB) − E(A) − E(B) is exactly the sum of u over the atom pairs between A and B, computed here directly from the atoms
of each neighbour; argon in a cubic cell a = 3.8 Å has 6 neighbours at a (3.8 Å, the radius included): E_latt =
½ · 6 · u(a), one dimer computed for the six; for benzoic acid every neighbour gets the direct sum even where the
energy of a pair is computed once for the copies that the symmetry makes (inversion: the same distances).
"""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_pairs as cp

C6 = 50.0


def u(r):
    return -C6 / r ** 6 / cp.HARTREE_KJ  # hartree, so that E_int comes out as −C/r⁶ kJ/mol


def model(molecule):
    atoms = molecule.atoms
    total = 0.0
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            a, b = atoms[i], atoms[j]
            total += u(((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5)
    return total


def argon(a):
    return cr.Crystal('Ar', cr.Cell(a, a, a), (cr.Site('Ar1', 'Ar', 0.0, 0.0, 0.0),), (cr.operation('x, y, z'),),
                      'P 1', (), 1, 'Ar', 1)


def test_argon_in_a_cubic_cell():
    p = cp.plan(argon(3.8))
    asked = []
    result = cp.compute(p, lambda m: asked.append(len(m.atoms)) or model(m))
    assert len(result.pairs) == 6 and asked == [1, 2] and result.calculations == 2 and result.failed == 0
    assert all(abs(x.energy + C6 / 3.8 ** 6) < 1e-9 and abs(x.distance - 3.8) < 1e-9 for x in result.pairs)
    assert abs(result.lattice - 0.5 * 6 * (-C6 / 3.8 ** 6)) < 1e-9
    cylinders = cp.frame(result, p.centroids[0], p.centroids[1])
    assert len(cylinders) == 6 and all(width == 1.0 and attractive for _, _, width, attractive in cylinders)


def test_benzoic_acid_every_pair_its_own_sum():
    path = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'
    p = cp.plan(cr.parse_cif(path.read_text(encoding='utf-8')))
    result = cp.compute(p, model)
    shell = p.shell
    atoms = shell.molecule.atoms
    centre, start = atoms[:shell.centre_atoms], shell.centre_atoms
    assert len(p.dimers) < len(result.pairs)  # the copies made by the symmetry computed once
    for pair in result.pairs:
        other = atoms[start:start + shell.centre_atoms]  # Z′ = 1: every neighbour has the atoms of the centre
        start += shell.centre_atoms
        direct = sum(-C6 / (((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 3) for a in centre for b in other)
        assert pair.energy == pytest.approx(direct, rel=1e-9, abs=1e-12)
    strongest = min(result.pairs, key=lambda x: x.energy)
    assert result.lattice == pytest.approx(0.5 * sum(x.energy for x in result.pairs))
    assert strongest.distance < 8.0


def test_a_failed_energy_is_left_out():
    p = cp.plan(argon(3.8))
    calls = []

    def flaky(m):
        calls.append(1)
        if len(m.atoms) == 2:
            raise ValueError('xtb gave no energy')
        return model(m)

    result = cp.compute(p, flaky)
    assert result.failed == 6 and result.lattice == 0.0 and all(x.energy is None for x in result.pairs)


def test_the_energy_of_an_xtb_output():
    text = '''
         :::::::::::::::::::::::::::::::::::::::::::::::::::::
         ::                     SUMMARY                     ::
         :: total energy             -11.385460543130 Eh    ::
          -------------------------------------------------
          | TOTAL ENERGY              -11.385460543130 Eh   |
          | GRADIENT NORM               0.000368651432 Eh/α |
'''
    assert cp.energy_of(text) == -11.38546054313 and cp.energy_of('nothing') is None


@pytest.mark.skipif(__import__('os').name == 'nt', reason='a script with #! stands in for xtb only on macOS and Linux')
def test_run_xtb_with_a_stand_in(tmp_path):
    # a stand-in for xtb (a script): it echoes its arguments and an energy; an odd number of electrons asks --uhf 1
    import os
    import sys

    from azimuth.core import Atom, Molecule

    script = tmp_path / 'xtb'
    script.write_text(f'#!{sys.executable}\nimport sys\nprint(" ".join(sys.argv[1:]))\n'
                      'print("          | TOTAL ENERGY              -1.234500000000 Eh   |")\n', encoding='utf-8')
    os.chmod(script, 0o755)
    water = Molecule('w', (Atom('O', 0, 0, 0), Atom('H', 0.96, 0, 0), Atom('H', -0.24, 0.93, 0)), None)
    assert cp.run_xtb(script, water, tmp_path / 'a') == -1.2345
    out = (tmp_path / 'a' / 'xtb.out').read_text(encoding='utf-8')
    assert 'mol.xyz --gfn 2 --sp --chrg 0' in out and '--uhf' not in out
    radical = Molecule('oh', water.atoms[:2], None)
    cp.run_xtb(script, radical, tmp_path / 'b')
    assert '--uhf 1' in (tmp_path / 'b' / 'xtb.out').read_text(encoding='utf-8')
    assert (tmp_path / 'b' / 'mol.xyz').read_text(encoding='utf-8').splitlines()[0] == '2'


def test_the_terms_of_the_xtb_summary():
    # the SUMMARY of tests/data/xtb/dvb_sp/dvb_sp.out, its lines read by eye: isotropic ES 0.001896100208,
    # anisotropic ES 0.005789527134, anisotropic XC 0.022968381942, dispersion −0.016488579108, repulsion
    # 0.478639495328, TOTAL ENERGY −26.425939358406 Eh
    text = (Path(__file__).resolve().parents[1] / 'data' / 'xtb' / 'dvb_sp' / 'dvb_sp.out').read_text(encoding='utf-8')
    terms = cp.terms_of(text)
    assert terms['total'] == pytest.approx(-26.425939358406)
    assert terms['es'] == pytest.approx(0.001896100208 + 0.005789527134)
    assert terms['xc'] == pytest.approx(0.022968381942) and terms['disp'] == pytest.approx(-0.016488579108)
    assert terms['rep'] == pytest.approx(0.478639495328)
    assert cp.terms_of('no summary') is None


def split_model(molecule):
    """A model with terms: dispersion −C/r⁶ and an 'electrostatic' +q/r of every atom pair, repulsion 0 — so the terms
    of E_int are the sums over the atom pairs between the molecules of each part, the rest 0."""
    atoms = molecule.atoms
    disp = es = 0.0
    for i in range(len(atoms)):
        for j in range(i + 1, len(atoms)):
            a, b = atoms[i], atoms[j]
            r = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2 + (a.z - b.z) ** 2) ** 0.5
            disp += u(r)
            es += 0.3 / r / cp.HARTREE_KJ
    return {'total': disp + es, 'es': es, 'xc': 0.0, 'disp': disp, 'rep': 0.0}


def test_the_terms_of_a_pair():
    p = cp.plan(argon(3.8))
    result = cp.compute(p, split_model)
    for pair in result.pairs:
        assert pair.terms['disp'] == pytest.approx(-C6 / 3.8 ** 6) and pair.terms['es'] == pytest.approx(0.3 / 3.8)
        assert pair.terms['rep'] == pytest.approx(0.0) and pair.terms['rest'] == pytest.approx(0.0, abs=1e-9)
        assert pair.energy == pytest.approx(sum(pair.terms.values()))
    assert all(pair.terms is None for pair in cp.compute(p, model).pairs)  # a plain number: no terms


def salt_cell():
    """Methylammonium chloride written for the test in a P 1 cell of 7 Å: CH₃NH₃⁺ (C–N 1.47, C–H and N–H 1.04 Å) and
    Cl⁻ 3.2 Å from N — the cation is in no table: it takes the charge that makes the cell neutral, +1."""
    a = 7.0
    atoms = [('C1', 'C', 0.0, 0.0, 0.0), ('N1', 'N', 1.47, 0.0, 0.0)]
    from math import cos, radians, sin

    for k in range(3):
        angle = radians(120 * k)
        atoms.append((f'H{k + 1}', 'H', -0.35, 0.98 * cos(angle), 0.98 * sin(angle)))
        atoms.append((f'H{k + 4}', 'H', 1.82, 0.98 * cos(angle + radians(60)), 0.98 * sin(angle + radians(60))))
    atoms.append(('Cl1', 'Cl', 4.67, 0.0, 0.0))
    sites = tuple(cr.Site(label, symbol, (x + 1.0) / a, (y + 3.5) / a, (z + 3.5) / a) for label, symbol, x, y, z in atoms)
    return cr.Crystal('MeNH3Cl', cr.Cell(a, a, a), sites, (cr.operation('x, y, z'),), 'P 1')


def test_the_charges_of_a_salt():
    guessed = cp.guess_charges(salt_cell())
    assert guessed.by_formula == {'CH6N': 1, 'Cl': -1} and guessed.known == {'CH6N': False, 'Cl': True}
    assert guessed.balanced and guessed.counts == {'CH6N': 1, 'Cl': 1}
    assert cp.guess_charges(argon(3.8)).by_formula == {'Ar': 0}
    # the charges reach the energies: each monomer its own, each pair the sum
    p = cp.plan(salt_cell(), radius=4.0)
    asked = []

    def energy(molecule, charge=0):
        asked.append((molecule.formula, charge))
        return model(molecule)

    cp.compute(p, energy)
    charges = dict(asked)
    assert charges.get('CH6N') == 1 and charges.get('Cl') == -1 and charges.get('CH6ClN') == 0
    neutral = cp.plan(argon(3.8))
    assert cp.compute(neutral, model).failed == 0  # a neutral crystal: energy(molecule) with no charge, as before

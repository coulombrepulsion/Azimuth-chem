"""The interaction energy of a pair with BSSE (modules/sextant/interaction.py).

Oracles, written here: a water dimer (two molecules 3 Å apart) — two parts of 3 atoms; the queue — the pair, each
molecule in the basis of the pair (the atoms of the other one ghosts, «O :» in the ORCA input), each alone; ΔE, BSSE
and ΔE(CP) from energies set by hand: E_AB = −152.000, E_A(AB) = −76.002, E_B(AB) = −75.990, E_A = −76.000,
E_B = −75.989 → ΔE = −0.011 Eh = −6.90 kcal/mol, ΔE(CP) = −0.008 Eh = −5.02 kcal/mol, BSSE = 1.88 kcal/mol
(627.5094740631 kcal/mol per hartree).
"""

import pytest

from azimuth.core import Atom, Calculation, Molecule
from modules.sextant import interaction


def water_dimer(gap=3.0):
    one = [Atom('O', 0.0, 0.0, 0.0), Atom('H', 0.96, 0.0, 0.0), Atom('H', -0.24, 0.93, 0.0)]
    two = [Atom(a.symbol, a.x, a.y, a.z + gap) for a in one]
    return Molecule('w2', tuple(one + two), None)


def test_plan_and_ghosts():
    items = interaction.plan(water_dimer(), Calculation())
    assert [i.props['role'] for i in items] == ['ab', 'a_ab', 'b_ab', 'a', 'b']
    assert items[1].props['ghosts'] == [3, 4, 5] and items[2].props['ghosts'] == [0, 1, 2]
    assert [len(i.molecule.atoms) for i in items] == [6, 6, 6, 3, 3]
    from modules.sextant import binding

    text = binding.input_text('orca', items[1].molecule, Calculation(task='Энергия'), items[1].props['ghosts'])
    rows = [line.split()[0:2] for line in text.split('\n') if line[:1] in 'OH' and len(line.split()) >= 4]
    assert rows[3] == ['O', ':'] and rows[0][1] != ':'


def test_energies():
    from modules.sextant.batch import Batch

    items = interaction.plan(water_dimer(), Calculation())
    for item, energy in zip(items, (-152.000, -76.002, -75.990, -76.000, -75.989)):
        item.state, item.energy = 'done', energy
    queue = Batch('orca', Calculation(), items, None, purpose='interaction')
    found = interaction.energies(queue)
    assert abs(found['dE'] - (-0.011 * 627.5094740631)) < 1e-9
    assert abs(found['dE_cp'] - (-0.008 * 627.5094740631)) < 1e-9 and abs(found['bsse'] - 0.003 * 627.5094740631) < 1e-9
    header, rows = interaction.table(queue)
    assert rows == [['-6.90', '1.88', '-5.02']]


def test_refused():
    with pytest.raises(ValueError):
        interaction.plan(Molecule('w', water_dimer().atoms[:3], None), Calculation())  # one molecule
    with pytest.raises(ValueError):
        interaction.plan(water_dimer(), Calculation(charge=1, multiplicity=2))

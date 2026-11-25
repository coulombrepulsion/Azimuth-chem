"""A metal ion with a set of ligands — the place of the ion, the queue, ghost atoms, binding energies."""

import math

import pytest

from azimuth.core import Atom, Calculation, Molecule
from modules.sextant import batch, binding


def crown():
    """A model 18-crown-6 without hydrogens: six O on a circle of 2.85 Å, two C between each pair, ±0.25 Å puckering."""
    atoms = []
    for k in range(6):
        a = k * math.pi / 3
        atoms.append(Atom('O', 2.85 * math.cos(a), 2.85 * math.sin(a), 0.25 * (-1) ** k))
        for t in (0.33, 0.67):
            b = a + t * math.pi / 3
            atoms.append(Atom('C', 3.35 * math.cos(b), 3.35 * math.sin(b), 0.0))
    return Molecule('18-crown-6', tuple(atoms))


def formate():
    return Molecule('formate', (Atom('C', 0.0, 0.0, 0.0), Atom('O', 1.25, 0.0, 0.0), Atom('O', -0.62, 1.08, 0.0),
                                Atom('H', -0.55, -0.95, 0.0)))


class TestPlaceIon:
    def test_puts_cesium_over_the_cavity_when_ligand_is_a_crown(self):
        # Arrange
        ligand = crown()
        # Act
        complex_ = binding.place_ion(ligand, 'Cs')
        ion = complex_.atoms[-1]
        distances = [math.dist(ion.position, a.position) for a in complex_.atoms[:-1] if a.symbol == 'O']
        # Assert
        assert ion.symbol == 'Cs' and len(complex_.atoms) == len(ligand.atoms) + 1
        assert math.hypot(ion.x, ion.y) < 0.5
        assert all(abs(d - binding.IONS['Cs'][1]) < 0.4 for d in distances)

    def test_holds_both_oxygens_when_ligand_is_a_carboxylate(self):
        # Arrange
        ligand = formate()
        # Act
        ion = binding.place_ion(ligand, 'Sr').atoms[-1]
        # Assert
        d1, d2 = (math.dist(ion.position, ligand.atoms[k].position) for k in (1, 2))
        assert abs(d1 - 2.58) < 0.35 and abs(d2 - 2.58) < 0.35
        assert math.dist(ion.position, ligand.atoms[3].position) > 2.4


class TestPlan:
    def test_lists_ion_ligands_and_complexes_when_two_ligands_are_given(self):
        # Arrange
        ligands = [('crown', crown(), 0, 1, {'logK': '0.99'}, ()), ('formate', formate(), -1, 1, {}, ())]
        # Act
        items, extra = binding.plan(ligands, 'Cs', bsse=True)
        # Assert
        assert [i.props['role'] for i in items] == ['ion', 'ligand', 'complex', 'ligand', 'complex']
        assert [i.charge for i in items] == [1, 0, 1, -1, 0]
        assert items[2].props['complex_of'] == 1 and items[2].props['logK'] == '0.99'
        assert items[0].props['task'] == 'Энергия' and extra['binding']['bsse']

    def test_adds_three_single_points_when_a_complex_is_done_with_bsse(self, tmp_path):
        # Arrange
        items, extra = binding.plan([('formate', formate(), -1, 1, {}, ())], 'Cs', bsse=True)
        queue = batch.Batch('orca', Calculation(), items, tmp_path, extra=extra)
        complex_ = items[2]
        complex_.state, complex_.geometry, complex_.energy = 'done', complex_.molecule, -200.0
        # Act
        added = binding.follow_ups(queue, complex_)
        again = binding.follow_ups(queue, complex_)
        # Assert
        assert [i.props['role'] for i in added] == ['bsse_l', 'bsse_lg', 'bsse_mg'] and again == []
        assert added[1].props['ghosts'] == [4] and added[2].props['ghosts'] == [0, 1, 2, 3]
        assert added[0].charge == -1 and added[2].charge == 1 and len(added[0].molecule.atoms) == 4


class TestGhosts:
    def test_marks_the_ion_and_keeps_the_charge_when_input_is_written(self):
        # Arrange
        complex_ = binding.place_ion(formate(), 'Cs')
        calc = Calculation(charge=-1, multiplicity=1, task='Энергия')
        # Act
        text = binding.input_text('orca', complex_, calc, [4])
        # Assert
        lines = text.split('\n')
        start = next(k for k, line in enumerate(lines) if line.startswith('* xyz'))
        assert lines[start] == '* xyz -1 1'
        assert lines[start + 5].startswith('Cs : ') and not lines[start + 1].startswith('C :')


class TestEnergies:
    def test_subtracts_and_corrects_when_every_part_is_done(self, tmp_path):
        # Arrange
        items, extra = binding.plan([('formate', formate(), -1, 1, {}, ())], 'Cs', bsse=True)
        queue = batch.Batch('orca', Calculation(task='Оптимизация'), items, tmp_path, extra=extra)
        ion, ligand, complex_ = items
        for item, energy in ((ion, -20.0), (ligand, -189.0), (complex_, -209.05)):
            item.state, item.energy, item.geometry = 'done', energy, item.molecule
        l_own, l_ghost, m_ghost = binding.follow_ups(queue, complex_)
        for item, energy in ((l_own, -188.99), (l_ghost, -188.992), (m_ghost, -20.001)):
            item.state, item.energy = 'done', energy
        # Act
        row = binding.energies(queue)[0]
        # Assert
        hk = binding.HARTREE_KCAL
        assert row['dE'] == pytest.approx(-0.05 * hk)
        assert row['bsse'] == pytest.approx((0.002 + 0.001) * hk)
        assert row['dE_cp'] == pytest.approx(row['dE'] + row['bsse'])
        assert binding.descriptor_rows(queue)['formate']['ΔE связывания, ккал/моль'] == pytest.approx(row['dE'])


class TestProjectEntries:
    def test_finds_the_ion_and_complex_again_when_binding_runs_twice(self, tmp_path):
        # Arrange
        from azimuth import projects

        project = projects.Project.create(tmp_path / 'project')
        ligand = project.add(formate(), Calculation(charge=-1), name='formate')
        items, _ = binding.plan([('formate', formate(), -1, 1, {}, ())], 'Cs')
        ion, _, complex_ = items
        keys = ({'role': 'ion', 'of': '', 'ion': 'Cs', 'charge': 1},
                {'role': 'complex', 'of': ligand['id'], 'ion': 'Cs', 'charge': 0})
        # Act
        first = [projects.auxiliary_entry(project, item, Calculation(), 'orca', key)['id']
                 for item, key in zip((ion, complex_), keys)]
        second = [projects.auxiliary_entry(project, item, Calculation(), 'orca', key)['id']
                  for item, key in zip((ion, complex_), keys)]
        # Assert
        assert first == second and len(project.molecules) == 3
        assert [e['id'] for e in projects.queueable(project)] == [ligand['id']]
        assert [e['id'] for e in projects.listed(project)] == [ligand['id'], first[1]]

"""Descriptors of a queue against the constants of its records (modules/spectrum/analysis/descriptors.py)."""

import json
import math
from pathlib import Path

import pytest

from azimuth.core import Atom, Molecule
from modules.compass.chemistry import formats
from modules.sextant import batch
from modules.spectrum.analysis import descriptors

SDF = '''
     RDKit          2D

  1  0  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 O   0  0  0  0  0  0  0  0  0  0  0  0
M  END
>  <Name>  (1)
Water

>  <logK_Cs_z=1.0_T=25_I=0.1>  (1)
0.6

$$$$

     RDKit          2D

  1  0  0  0  0  0  0  0  0  0999 V2000
    0.0000    0.0000    0.0000 N   0  0  0  0  0  0  0  0  0  0  0  0
M  END
>  <Name>  (2)
Ammonia

>  <logK_Cs_z=1.0_T=25_I=0.1>  (2)
1,25

$$$$
'''


def crown(distance=3.0):
    """Cs⁺ with six O on a ring at distance, and six C farther out."""
    atoms = [Atom('Cs', 0.0, 0.0, 0.0)]
    for k in range(6):
        a = k * math.pi / 3
        atoms.append(Atom('O', distance * math.cos(a), distance * math.sin(a), 0.3 * (-1) ** k))
        b = a + math.pi / 6
        atoms.append(Atom('C', 4.2 * math.cos(b), 4.2 * math.sin(b), 0.0))
    return Molecule('crown', tuple(atoms))


class TestFit:
    def test_gives_perfect_scores_when_points_lie_on_a_line(self):
        # Arrange
        x = [1.0, 2.0, 3.0, 4.0]
        y = [2.5 + 0.5 * v for v in x]
        # Act
        result = descriptors.fit(x, y)
        # Assert
        assert result.slope == pytest.approx(0.5) and result.intercept == pytest.approx(2.5)
        assert result.r2 == pytest.approx(1.0) and result.q2 == pytest.approx(1.0) and result.rmse == pytest.approx(0.0)
        assert result.outliers == []

    def test_matches_the_textbook_numbers_when_points_scatter(self):
        # Arrange
        import numpy as np

        x = [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        y = [1.1, 1.9, 3.2, 3.8, 5.3, 5.9, 12.0]
        slope, intercept = np.polyfit(x, y, 1)
        predicted = np.polyval([slope, intercept], x)
        r2 = 1 - ((np.array(y) - predicted) ** 2).sum() / ((np.array(y) - np.mean(y)) ** 2).sum()
        press = sum((y[i] - np.polyval(np.polyfit(np.delete(x, i), np.delete(y, i), 1), x[i])) ** 2 for i in range(7))
        q2 = 1 - press / ((np.array(y) - np.mean(y)) ** 2).sum()
        # Act
        result = descriptors.fit(x, y)
        # Assert
        assert result.slope == pytest.approx(slope) and result.intercept == pytest.approx(intercept)
        assert result.r2 == pytest.approx(r2) and result.q2 == pytest.approx(q2)

    def test_rings_the_point_when_one_lies_far_off_the_line(self):
        # Arrange
        x = list(range(10))
        noise = [0.05, -0.04, 0.03, -0.02, 0.04, -0.05, 3.0, 0.02, -0.03, 0.01]
        y = [1.0 + 0.5 * v + e for v, e in zip(x, noise)]
        # Act
        result = descriptors.fit(x, y)
        # Assert
        assert result.outliers == [6]

    def test_refuses_when_fewer_than_three_pairs(self):
        # Arrange, Act, Assert
        with pytest.raises(ValueError):
            descriptors.fit([1.0, 2.0, None], [1.0, 2.0, 3.0])


class TestSphere:
    def test_counts_six_oxygens_when_cesium_sits_in_a_crown(self):
        # Arrange
        molecule = crown()
        # Act
        i = descriptors.metal_index(molecule)
        shell = descriptors.sphere(molecule, i)
        # Assert
        assert molecule.atoms[i].symbol == 'Cs'
        assert len(shell) == 6 and {s for _, s, _ in shell} == {'O'}

    def test_reads_bcp_sums_when_qtaim_was_run(self):
        # Arrange
        molecule = crown()
        bcp = {'bcp': [{'atoms': [0, 1], 'rho': 0.01, 'laplacian': 0.04, 'G': 0.008, 'V': -0.006, 'H': 0.002},
                       {'atoms': [3, 0], 'rho': 0.012, 'laplacian': 0.05, 'G': 0.009, 'V': -0.007, 'H': 0.002},
                       {'atoms': [1, 2], 'rho': 0.25, 'laplacian': -0.5, 'G': 0.1, 'V': -0.6, 'H': -0.5}]}
        item = batch.BatchItem('crown', molecule, 1, 1, state='done', energy=-100.0, geometry=molecule)
        # Act
        values = descriptors.of_item(item, qtaim=bcp, text='')
        # Assert
        assert values['CN'] == 6 and values['BCP M–D'] == 2
        assert values['Σρ(M–D)'] == pytest.approx(0.022) and values['ΣV(M–D)'] == pytest.approx(-0.013)


class TestTable:
    def test_keeps_the_constants_of_the_records_when_the_queue_is_tabulated(self, tmp_path):
        # Arrange
        props = formats.sdf_properties(SDF)
        items = [batch.BatchItem(p['Name'], crown(), 1, 1, state='done', energy=-100.0 - k, props=p)
                 for k, p in enumerate(props)]
        queue = batch.Batch('orca', None, items, tmp_path)
        # Act
        columns, rows = descriptors.table(queue)
        numeric = descriptors.constant_columns(columns, rows + rows)
        # Assert
        k = columns.index('logK_Cs_z=1.0_T=25_I=0.1')
        assert [descriptors.number(row[k]) for row in rows] == [0.6, 1.25]
        assert 'logK_Cs_z=1.0_T=25_I=0.1' in numeric and 'CN' in numeric

    def test_round_trips_props_and_formal_when_the_queue_is_saved(self, tmp_path):
        # Arrange
        from azimuth.core import Calculation

        item = batch.BatchItem('ion', crown(), 1, 1, props={'logK': '0.6'}, formal=(1,) + (0,) * 12)
        queue = batch.Batch('orca', Calculation(), [item], tmp_path)
        # Act
        queue.save()
        loaded = batch.Batch.load(tmp_path)
        # Assert
        assert loaded.items[0].props == {'logK': '0.6'} and loaded.items[0].formal == (1,) + (0,) * 12

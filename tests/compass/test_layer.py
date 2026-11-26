"""A layer with vacuum and the Dirac cone of graphene (modules/compass/chemistry/layer.py; the series of
modules/sextant/qe_inputs.py and their table in modules/compass/actions/qe_results.py).

Oracles. Graphene by hand: a = 2.46 Å, the cell 2.46 × 2.46 × 15 Å with γ = 120°, both atoms at z = ½ — the layer has
no thickness, the vacuum is the whole c. A slab of two planes 3 Å apart in a cell of 20 Å: vacuum 17 Å.
Tight binding: |f| = 3 at Γ, 1 at M, 0 at K — the bands at ±3t, ±t, 0; near K the cone has ħv_F = (√3/2) a t, so a
cone cut out of the model itself must give back its t. The real bands of graphene (pw.x 7.6, PBE,
tests/data/qe/README.md): the numbers of the levels at K and beside it copied from the output.
"""

import json
from math import sqrt
from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.compass.chemistry import band_gap, crystal as cr, layer
from modules.sextant import qe_inputs, qe_paths
from modules.spectrum.readers import qe

DATA = Path(__file__).resolve().parents[1] / 'data' / 'qe'
RY = 13.605693122994


def graphene(c=15.0):
    text = (f'data_graphene\n_cell_length_a 2.46\n_cell_length_b 2.46\n_cell_length_c {c}\n_cell_angle_alpha 90\n'
            "_cell_angle_beta 90\n_cell_angle_gamma 120\n_space_group_name_H-M_alt 'P 6/m m m'\nloop_\n_atom_site_label\n"
            '_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\nC1 0.333333333 0.666666667 0.5\n')
    return cr.parse_cif(text)


def slab():
    sites = (cr.Site('Al1', 'Al', 0.0, 0.0, 0.10), cr.Site('Al2', 'Al', 0.5, 0.5, 0.25))
    return cr.Crystal('slab', cr.Cell(4.0, 4.0, 20.0), sites, (cr.operation('x, y, z'),), 'P 1')


def test_the_vacuum_of_a_layer():
    from tests.sextant.test_qe_inputs import silicon

    assert layer.vacuum_axis(graphene()) == 2 and layer.vacuum(graphene(), 2) == pytest.approx(15.0)
    assert layer.thickness(graphene(), 2) == pytest.approx(0.0, abs=1e-9)
    assert layer.vacuum_axis(silicon()) is None and layer.vacuum_axis(graphene(6.0)) is None  # under LEAST
    assert layer.vacuum_axis(slab()) == 2 and layer.vacuum(slab(), 2) == pytest.approx(17.0)
    assert layer.thickness(slab(), 2) == pytest.approx(3.0)
    # one k-point along the vacuum; the path of a hexagonal layer stays in its plane
    assert qe_inputs.grid_of(graphene()) == (12, 12, 1) and qe_inputs.grid_of(silicon()) == (5, 5, 5)
    assert [label for _, label in qe_paths.path(graphene()).ticks] == ['Γ', 'M', 'K', 'Γ']
    assert 'A' in [label for _, label in qe_paths.path(graphene(6.7)).ticks]  # a bulk hexagonal cell: the whole path


def test_the_same_layer_with_another_vacuum():
    wide = layer.with_vacuum(slab(), 10.0)
    assert (wide.cell.a, wide.cell.b, wide.cell.c) == pytest.approx((4.0, 4.0, 13.0))
    atoms = cr.unit_cell(wide)
    z = sorted(a[3] * 13.0 for a in atoms)
    assert z == pytest.approx([5.0, 8.0])  # 3 Å apart as before, in the middle: 5 Å of vacuum on each side
    assert layer.vacuum(wide, 2) == pytest.approx(10.0) and len(atoms) == 2
    thin = layer.with_vacuum(graphene(), 8.0)
    assert thin.cell.c == pytest.approx(8.0) and thin.cell.gamma == 120 and [a[3] for a in cr.unit_cell(thin)] == [0.5, 0.5]
    assert layer.vacuums(15.0) == [8.0, 10.0, 12.0, 15.0, 18.0, 20.0] and layer.vacuums(13.3) == [8.0, 10.0, 12.0, 13.3, 15.0, 18.0, 20.0]
    with pytest.raises(ValueError, match='больше нуля'):
        layer.with_vacuum(slab(), 0.0)
    tilted = cr.Crystal('t', cr.Cell(4.0, 4.0, 20.0, 80.0, 90.0, 90.0), slab().sites, slab().operations, 'P 1')
    with pytest.raises(ValueError, match='перпендикулярна'):
        layer.with_vacuum(tilted, 10.0, 2)


def test_the_inputs_of_the_series_of_vacuum():
    from tests.sextant.test_qe_inputs import silicon

    pseudo = {'C': ('C.upf', 45.0, 360.0), 'Si': ('Si.upf', 30.0, 240.0)}
    found = qe_inputs.steps(graphene(), qe_inputs.VACUUM_TASK, pseudo, '/p')
    assert [name for name, _, _ in found] == [f'vac{n}.in' for n in range(1, 7)]
    assert [layer.vacuum_of_input(text) for _, _, text in found] == pytest.approx([8, 10, 12, 15, 18, 20])
    assert {text.split('K_POINTS automatic')[1].strip() for _, _, text in found} == {'12 12 1 0 0 0'}  # one grid
    assert all('0.50000000\n' in text for _, _, text in found)
    with pytest.raises(ValueError, match='не слой'):
        qe_inputs.steps(silicon(), qe_inputs.VACUUM_TASK, pseudo, '/p')
    grids = qe_inputs.steps(graphene(), qe_inputs.KGRID_TASK, pseudo, '/p')
    assert [text.split('K_POINTS automatic')[1].split()[0] for _, _, text in grids] == ['6', '8', '9', '10', '12', '15', '18', '24']
    assert layer.vacuum_of_input('nothing') is None


def test_the_tight_binding_model_and_its_cone():
    prim = cr.primitive(graphene())
    cells = layer.neighbour_cells(prim)
    assert len(cells) == 3 and (0, 0, 0) in cells
    t = 2.7
    assert layer.tight_binding([(0, 0, 0)], t, 1.0, cells)[0] == pytest.approx((1.0 - 3 * t, 1.0 + 3 * t))  # Γ
    assert layer.tight_binding([(0.5, 0, 0)], t, 0.0, cells)[0] == pytest.approx((-t, t))  # M
    assert layer.tight_binding([(1 / 3, 1 / 3, 0)], t, 0.0, cells)[0] == pytest.approx((0.0, 0.0), abs=1e-9)  # K
    # the cone cut out of the model gives its hopping back (the slopes of a cosine band are a little under the limit)
    path = qe_paths.path(graphene(), None, step=0.01)
    model = layer.tight_binding(path.fractions, t, 0.0, cells)
    found = layer.cone([list(pair) for pair in model], 1, path.x, path.ticks, 2.46, window=0.05)
    assert found.hopping == pytest.approx(t, rel=0.01) and found.hv == pytest.approx(sqrt(3) / 2 * 2.46 * t, rel=0.01)
    assert found.energy == pytest.approx(0.0, abs=1e-9) and (found.left, found.right) == ('M', 'Γ')
    with pytest.raises(ValueError, match='два атома'):
        layer.neighbour_cells(slab().__class__('x', slab().cell, slab().sites[:1], slab().operations, 'P 1'))
    with pytest.raises(ValueError, match='три'):
        layer.neighbour_cells(slab())


def test_the_real_cone_of_graphene():
    text = (DATA / 'graphene_bands_pw76.out').read_text(encoding='utf-8')
    path = json.loads((DATA / 'graphene_bands_path.json').read_text(encoding='utf-8'))
    bands = qe.bands(text)
    ticks = [tuple(t) for t in path['ticks']]
    assert band_gap.occupied_bands(text) == 4 and len(bands.energies) == len(path['x']) == 162
    gap = band_gap.gap(bands.energies, 4, path['x'], ticks)
    assert gap.kind == 'metal' and gap.vbm.where == 'K'  # a semimetal: the bands touch
    found = layer.cone(bands.energies, 4, path['x'], ticks, 2.46)
    at = found.index
    # along the path K is |ΓM| + |MK| = (2π/a)(1/√3 + 1/3) from the start
    assert path['x'][at] == pytest.approx(2 * 3.141592653589793 / 2.46 * (1 / sqrt(3) + 1 / 3))
    assert bands.energies[at][3] == pytest.approx(bands.energies[at][4], abs=2e-4) and found.energy == pytest.approx(-1.6887, abs=2e-4)
    # PBE in the literature: v_F ≈ 0.83·10⁶ m/s, t ≈ 2.6 eV; measured ≈ 1.0·10⁶ m/s
    assert found.velocity == pytest.approx(0.831e6, rel=0.005) and found.hv == pytest.approx(5.47, abs=0.01)
    assert found.hopping == pytest.approx(2.567, abs=0.005)
    assert set(found.slopes) == {('π', 'left'), ('π*', 'left'), ('π', 'right'), ('π*', 'right')}
    assert found.slopes[('π', 'right')] > found.slopes[('π', 'left')]  # warping: steeper towards Γ than towards M
    assert '0.831' in layer.text(found) and '2.57' in layer.text(found)
    # the model with this t follows the real bands near K (0.08 Å⁻¹ away: to 0.03 eV)
    model = layer.tight_binding(path['fractions'], found.hopping, found.energy, layer.neighbour_cells(cr.primitive(graphene())))
    for k in (at - 3, at + 3):
        assert model[k][0] == pytest.approx(bands.energies[k][3], abs=0.03) and model[k][1] == pytest.approx(bands.energies[k][4], abs=0.03)
    assert layer.cone(bands.energies, 3, path['x'], ticks, 2.46) is None  # the bands 3 and 4 do not touch at K
    assert layer.cone(bands.energies, 4, path['x'], [t for t in ticks if t[1] != 'K'], 2.46) is None


# the series of grids N × N × 1: «!» of pw.x, Ry, and its highest occupied level, eV
KGRID = {6: (-36.88273798, -1.6872), 8: (-36.88692760, -2.7170), 9: (-36.88570343, -1.6882), 10: (-36.88730442, -2.7214),
         12: (-36.88643135, -1.6887), 15: (-36.88669642, -1.6887), 18: (-36.88681630, -1.6887), 24: (-36.88691161, -1.6888)}
VACUUM = {8: -36.88639034, 10: -36.88642974, 12: -36.88643168, 15: -36.88643135, 18: -36.88643243, 20: -36.88643085}


def _folder(tmp_path, kind, count):
    for n in range(1, count + 1):
        (tmp_path / f'{kind}{n}.in').write_text((DATA / f'graphene_{kind}{n}.in').read_text(encoding='utf-8'), encoding='utf-8')
    (tmp_path / 'pw.out').write_text((DATA / f'graphene_{kind}_pw76.out').read_text(encoding='utf-8'), encoding='utf-8')
    return SimpleNamespace(folder=tmp_path, series_error='')


def test_the_two_families_of_grids_of_graphene(tmp_path):
    from modules.compass.actions import qe_results

    kind, table = qe_results.series_data(_folder(tmp_path, 'kpt', 8))
    assert kind == 'kpt' and [r.label for r in table] == [f'{n} × {n} × 1' for n in KGRID]
    assert [r.fermi for r in table] == [level for _, level in KGRID.values()]
    last = KGRID[24][0]
    assert [r.delta for r in table] == pytest.approx([1000 * (e - last) * RY / 2 for e, _ in KGRID.values()], abs=1e-6)
    with_k = [r for r in table if qe_results.with_corner(r.label)]
    without = [r for r in table if not qe_results.with_corner(r.label)]
    assert [r.label.split()[0] for r in with_k] == ['6', '9', '12', '15', '18', '24']
    # with K the energy comes down to the limit from above and the highest level is the Dirac point; without K the
    # energy is under the limit and the highest level 1 eV lower (the nearest point of the grid is off the cone)
    assert all(r.delta >= 0 for r in with_k) and all(a.delta > b.delta for a, b in zip(with_k, with_k[1:]))
    assert all(r.delta < 0 for r in without)
    assert all(abs(r.fermi + 1.688) < 0.002 for r in with_k) and all(r.fermi < -2.7 for r in without)
    assert len(qe_results.family_lines(kind, table)) == 1 and qe_results.family_lines('cut', table) == []
    assert not qe_results.with_corner('5 × 5 × 5') and not qe_results.with_corner('9 × 9 × 9')


def test_the_series_of_vacuum_of_graphene(tmp_path):
    from modules.compass.actions import qe_results
    from modules.compass.chemistry import convergence

    kind, table = qe_results.series_data(_folder(tmp_path, 'vac', 6))
    assert kind == 'vac' and [r.label for r in table] == [f'{v} Å' for v in VACUUM]
    assert [r.delta for r in table] == pytest.approx([1000 * (e - VACUUM[20]) * RY / 2 for e in VACUUM.values()], abs=1e-6)
    assert all(r.pressure is None for r in table)  # of a cell with vacuum it says nothing
    assert convergence.converged(table) == 0 and abs(table[0].delta) < 0.3  # 8 Å is enough to 1 meV per atom
    assert qe_results.family_lines(kind, table) == []

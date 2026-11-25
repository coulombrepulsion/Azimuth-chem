"""Multiwfn charges (modules/spectrum/wavefunction/multiwfn.py).

Oracles: outputs of Multiwfn 2026.7.15 recorded on macOS (Homebrew) for the water of examples/6-orbitals
(water_mp2_gaussian16.fchk) and the methane of an ORCA 6 B3LYP/def2-SVP Molden file (tests/data/multiwfn/); the numbers
below are copied from those outputs. A fake Multiwfn (tests/fake_programs.py: a Python script printing the recorded
outputs — on Windows too) checks the run; the live test runs only where Multiwfn is installed.
"""

import os
from pathlib import Path

import pytest

from modules.spectrum.wavefunction import multiwfn
from tests.fake_programs import fake_program, q

DATA = Path(__file__).parents[1] / 'data' / 'multiwfn'


def recorded(name):
    return (DATA / name).read_text(encoding='utf-8')


def test_parse_adch_cm5_and_version():
    adch = multiwfn.parse_charges(recorded('water_fchk_adch_2026.7.15.txt'))
    assert adch == {'adch': (-0.58474246, 0.29237123, 0.29237123)}
    cm5 = multiwfn.parse_charges(recorded('water_fchk_cm5_2026.7.15.txt'))
    assert cm5 == {'cm5': (-0.6149238, 0.3074619, 0.3074619)}
    both = multiwfn.parse_charges(recorded('water_fchk_adch_2026.7.15.txt') + recorded('water_fchk_cm5_2026.7.15.txt'))
    assert set(both) == {'adch', 'cm5'} and both['cm5'][0] == pytest.approx(-0.6149238)
    methane = multiwfn.parse_charges(recorded('ch4_orca_molden_cm5_2026.7.15.txt'))
    assert methane['cm5'] == pytest.approx((-0.30812688, 0.07703172, 0.07703172, 0.07703173, 0.07703171))
    assert abs(sum(methane['cm5'])) < 1e-6  # normalized by Multiwfn
    assert multiwfn.version(recorded('ch4_orca_molden_cm5_2026.7.15.txt')) == '2026.7.15'
    assert multiwfn.parse_charges('Multiwfn crashed') == {}


def test_wavefunction_names():
    assert multiwfn.wavefunction_name('/a/Расчёты/CH4_B3LYP.molden.input') == 'input.molden'
    assert multiwfn.wavefunction_name('x.FCHK') == 'input.fchk'
    with pytest.raises(ValueError):
        multiwfn.wavefunction_name('x.out')


def test_fake_multiwfn_run_and_search(tmp_path):
    out = tmp_path / 'both.txt'
    out.write_text(recorded('water_fchk_adch_2026.7.15.txt') + recorded('water_fchk_cm5_2026.7.15.txt'), encoding='utf-8')
    # it checks its arguments and its input as the real one would read them
    fake = fake_program(tmp_path / 'bin', f'''
if args[:2] != ['input.fchk', '-nt'] or not os.path.isfile('input.fchk'):
    sys.exit(3)
if ''.join(lines[:3]) != '7111':
    sys.exit(4)
cat({q(out)})
''')
    source = tmp_path / 'Папка с пробелом' / 'water.fchk'
    source.parent.mkdir()
    source.write_text('fchk', encoding='utf-8')
    if os.name != 'nt':  # on Windows it looks for Multiwfn.exe — the fake there is a .cmd
        assert multiwfn.find(path_env=str(fake.parent), home=tmp_path, search=True) == fake
    assert multiwfn.find(path_env=str(fake.parent), home=tmp_path, search=False) is None
    assert multiwfn.find(configured=str(fake), path_env='') == fake
    charges, text, number = multiwfn.run_charges(fake, source, cores=2)
    assert charges['adch'][0] == pytest.approx(-0.58474246) and number == '2026.7.15'
    stops = iter([True, False])
    slow = fake_program(tmp_path / 'bin', 'time.sleep(30)', name='slow')
    with pytest.raises(InterruptedError):  # a cancel is not a failure
        multiwfn.run_charges(slow, source, step=lambda *a: next(stops, False))
    with pytest.raises(ValueError):
        multiwfn.run_charges(None, source)


@pytest.mark.skipif(multiwfn.find(search=True) is None, reason='Multiwfn is not installed')
def test_live_multiwfn_on_orca_methane():
    charges, _, number = multiwfn.run_charges(multiwfn.find(search=True), DATA / 'ch4_orca.molden.input')
    assert charges['cm5'][0] == pytest.approx(-0.30812688, abs=2e-4)
    assert charges['adch'][0] < 0 and abs(sum(charges['adch'])) < 1e-3


def nci_cubes(name):
    import gzip

    from modules.spectrum.readers.cube import read_cube

    return tuple(read_cube(gzip.open(DATA / f'dimer_{name}_{f}.cub.gz', 'rt').read()) for f in ('func1', 'func2'))


def test_nci_grids_of_the_water_dimer():
    # Multiwfn 2026.7.15 on the S22 water dimer (xtb GFN2 Molden and promolecular density), cubes cropped
    # around the molecules: the low-RDG points between the molecules have sign(λ₂)ρ of a hydrogen bond (≈ −0.02 a.u.
    # with xtb, ≈ −0.03 promolecular; values read from the recorded grids at their RDG minimum)
    import numpy as np

    from modules.compass.view import surfaces

    for name, expected in (('nci_low', -0.0182), ('nci_promol', -0.0303)):
        sign, field = nci_cubes(name)
        rdg = field.values[..., 0]
        k = np.unravel_index(np.argmin(rdg), rdg.shape)
        point = sign.origin + np.array(k) @ sign.axes
        o1, h, o2 = (np.array(sign.molecule.atoms[i].position) for i in (0, 2, 3))
        assert np.linalg.norm(point - (h + o2) / 2) < 0.6  # between the donor H and the acceptor O
        assert surfaces.sample(sign, [point])[0] == pytest.approx(expected, abs=0.004)
        xs, ys = multiwfn.scatter(sign, field, *multiwfn.PLOT_WINDOWS['nci'])
        assert len(xs) and xs.min() >= -0.05 and ys.max() <= 2.0
        spike = xs[ys < 0.5]
        assert len(spike) and spike.max() < -0.01  # the H-bond spike: attraction, blue
        colour = surfaces.nci_colors([expected])[0]
        assert colour[2] > colour[0] and expected < (surfaces.NCI_LOW + surfaces.NCI_HIGH) / 2  # the blue half
    assert len(multiwfn.scatter(sign, field, limit=50)[0]) == 50
    assert multiwfn.version((DATA / 'dimer_nci_low_2026.7.15.txt').read_text(encoding='utf-8')) == '2026.7.15'


def test_fake_multiwfn_nci_run(tmp_path):
    from azimuth.core import read_xyz

    one, two = (DATA / f'dimer_nci_promol_{f}.cub.gz' for f in ('func1', 'func2'))
    fake = fake_program(tmp_path, f'''
if args[:1] != ['input.xyz'] or not any(line.startswith('O ') for line in open('input.xyz', encoding='utf-8')):
    sys.exit(3)
if answers(4) != '20 2 2 3':
    sys.exit(4)
gunzip({q(one)}, 'func1.cub')
gunzip({q(two)}, 'func2.cub')
echo(' Version 2026.7.15 (release date is the same as version name)')
''')
    dimer = read_xyz((DATA / 'water_dimer_s22.xyz').read_text(encoding='utf-8'))
    sign, field, _, number = multiwfn.run_nci(fake, None, 'promolecular', 'medium', molecule=dimer)
    assert number == '2026.7.15' and sign.values.shape == field.values.shape
    assert [a.symbol for a in field.molecule.atoms] == ['O', 'H', 'H', 'O', 'H', 'H']
    with pytest.raises(ValueError):
        multiwfn.run_nci(fake, None, 'promolecular', molecule=None)
    with pytest.raises(ValueError):
        multiwfn.run_nci(fake, DATA / 'ch4_orca.molden.input', 'nci')  # the fake writes no grids for it
    with pytest.raises(ValueError):
        multiwfn.run_nci(fake, None, 'elf')


@pytest.mark.skipif(multiwfn.find(search=True) is None, reason='Multiwfn is not installed')
def test_live_multiwfn_promolecular_nci():
    from azimuth.core import read_xyz

    dimer = read_xyz((DATA / 'water_dimer_s22.xyz').read_text(encoding='utf-8'))
    sign, field, _, _ = multiwfn.run_nci(multiwfn.find(search=True), None, 'promolecular', 'low', molecule=dimer)
    xs, ys = multiwfn.scatter(sign, field)
    assert xs[ys < 0.5].max() < -0.01


# -- the topology of ρ and the ESP on the surface ------------------------------------------------------------------
def gz(name):
    import gzip

    return gzip.open(DATA / name, 'rt').read()


def test_topology_of_water_agrees_with_our_own_search():
    # Multiwfn 2026.7.15 on examples/6-orbitals/water_mp2_gaussian16.fchk (CPprop.txt) against density.critical_points
    # of Azimuth — two independent searches: the same bond critical points
    import numpy as np

    from modules.spectrum.analysis import density
    from modules.spectrum.readers.orbital_files import read_orbitals

    cps = multiwfn.parse_cps(recorded('water_fchk_CPprop_2026.7.15.txt'))
    assert [c['kind'] for c in cps] == ['nucleus'] * 3 + ['bond'] * 2
    bond = cps[3]
    assert bond['atoms'] == (2, 0) and bond['rho'] == pytest.approx(0.3515442357)
    assert bond['laplacian'] == pytest.approx(-1.930952844) and bond['ellipticity'] == pytest.approx(0.045307)
    assert cps[0]['ellipticity'] is None and cps[1]['atoms'] == (0,)
    orbitals = read_orbitals((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                             .read_text(encoding='utf-8'))
    ours = density.critical_points(orbitals)
    theirs = density.topology_from(cps, orbitals)
    assert theirs.counts == {'n': 3, 'b': 2, 'r': 0, 'c': 0} and theirs.poincare_hopf == 1 and not theirs.notes
    for a, b in zip(ours.points, theirs.points):
        assert a.atoms == b.atoms and a.rho == pytest.approx(b.rho, abs=1e-4)
        assert a.laplacian == pytest.approx(b.laplacian, abs=1e-3)
        assert np.linalg.norm(a.position - b.position) < 1e-3
    assert len(theirs.paths) == 2 and all(len(p) > 5 for p in theirs.paths)
    multiwfn_text = recorded('dimer_xtb_topology_2026.7.15.txt')
    assert 'Some (3,-3) may missing' in multiwfn_text


def test_fake_multiwfn_topology_and_esp(tmp_path):
    import numpy as np

    from modules.compass.view import surfaces

    fake = fake_program(tmp_path, f'''
if answer(0) == '2':
    cp({q(DATA / "water_fchk_CPprop_2026.7.15.txt")}, 'CPprop.txt')
    cat({q(DATA / "dimer_xtb_topology_2026.7.15.txt")})
if answer(0) == '12':
    gunzip({q(DATA / "water_fchk_esp_vtx.txt.gz")}, 'vtx.txt')
    gunzip({q(DATA / "water_fchk_esp_surf.cub.gz")}, 'surf.cub')
    cat({q(DATA / "water_fchk_esp_2026.7.15.txt")})
''')
    source = tmp_path / 'water.fchk'
    source.write_text('fchk', encoding='utf-8')
    cps, _, number, warnings = multiwfn.run_topology(fake, source)
    assert len(cps) == 5 and number == '2026.7.15' and warnings  # the warning of the recorded xtb output
    esp = multiwfn.run_esp(fake, source)
    assert esp['minima'] == [(-43.49811, (-0.042768, -0.029406, 1.62099), True)]
    assert esp['maxima'][0][0] == pytest.approx(30.953485)
    assert esp['summary']['area'] == pytest.approx(39.14277) and esp['summary']['volume'] == pytest.approx(22.22538)
    assert esp['points'].shape == (2998, 3) and esp['esp'].min() == pytest.approx(-0.0693185919)
    assert esp['density'].values.shape[:3] == (40, 44, 40)
    # the ESP of the vertices onto themselves and onto points next to them
    assert np.allclose(surfaces.nearest_values(esp['points'][:50], esp['points'], esp['esp']), esp['esp'][:50])
    near = surfaces.nearest_values(esp['points'][:50] + 0.01, esp['points'], esp['esp'])
    assert np.max(np.abs(near - esp['esp'][:50])) < 0.01
    # the minimum lies near the oxygen (its lone pairs), the maximum beyond a hydrogen... of the recorded water
    with pytest.raises(ValueError):
        multiwfn.run_esp(tmp_path / 'none', source)


def test_esp_surface_of_methane_and_the_parser():
    methane = multiwfn.parse_surface(recorded('ch4_orca_esp_2026.7.15.txt'))
    assert len(methane['minima']) == 18 and len(methane['maxima']) == 5
    assert sum(top for *_, top in methane['minima']) == 1 and sum(top for *_, top in methane['maxima']) == 1
    assert methane['summary']['nonpolar_share'] == 100.0 and methane['summary']['polar_area'] == 0.0
    water = multiwfn.parse_surface(recorded('water_fchk_esp_2026.7.15.txt'))
    assert water['summary']['balance'] == pytest.approx(0.21604597) and water['summary']['mpi'] == pytest.approx(20.89464)


@pytest.mark.skipif(multiwfn.find(search=True) is None, reason='Multiwfn is not installed')
def test_live_multiwfn_topology_and_esp_of_water():
    water = Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk'
    cps, _, _, warnings = multiwfn.run_topology(multiwfn.find(search=True), water)
    bonds = [c for c in cps if c['kind'] == 'bond']
    assert len(bonds) == 2 and bonds[0]['rho'] == pytest.approx(0.35154, abs=1e-4) and not warnings
    esp = multiwfn.run_esp(multiwfn.find(search=True), water)
    assert esp['minima'][0][0] == pytest.approx(-43.498, abs=0.05)
    assert esp['summary']['area'] == pytest.approx(39.143, abs=0.05)


def test_elf_and_lol_grids(tmp_path):
    # Multiwfn 2026.7.15, the ELF and LOL of the water of examples/6-orbitals (grids cropped around it): ELF is
    # near 1 where the electrons are paired (it reaches 0.9999), LOL below 1
    import numpy as np

    fake = fake_program(tmp_path, f'''
if (answer(0), answer(2), answer(3)) != ('5', '2', '2'):
    sys.exit(4)
if answer(1) == '9':
    gunzip({q(DATA / "water_fchk_ELF.cub.gz")}, 'ELF.cub')
cat({q(DATA / "elf_water_2026.7.15.txt")})
''')
    source = tmp_path / 'water.fchk'
    source.write_text('fchk', encoding='utf-8')
    cube, _, number = multiwfn.run_function(fake, source, 'elf', 'medium')
    assert number == '2026.7.15' and 0.999 < cube.values.max() <= 1.0 and cube.values.min() >= 0
    assert [a.symbol for a in cube.molecule.atoms] == ['O', 'H', 'H']
    with pytest.raises(ValueError):
        multiwfn.run_function(fake, source, 'lol', 'medium')  # the fake writes no LOL.cub
    with pytest.raises(ValueError):
        multiwfn.run_function(fake, source, 'rdg')
    lol = gz('water_fchk_LOL.cub.gz')
    from modules.spectrum.readers.cube import read_cube

    assert 0.9 < np.max(read_cube(lol).values) < 0.91


@pytest.mark.skipif(multiwfn.find(search=True) is None, reason='Multiwfn is not installed')
def test_live_multiwfn_elf_of_water():
    water = Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk'
    cube, _, _ = multiwfn.run_function(multiwfn.find(search=True), water, 'elf', 'low')
    assert 0.99 < cube.values.max() <= 1.0


# -- bond orders, the composition of the orbitals, the grids of the orbitals ---------------------------------------
def test_bond_orders_of_methane():
    # the recorded outputs of Multiwfn 2026.7.15 for the methane of an ORCA Molden file, one per method (Mayer, Wiberg in
    # the Löwdin basis, fuzzy, Laplacian), put one after another as one run with 9 → 1 → n → 3 → n → 7 → n → 8 → n prints
    orders = multiwfn.parse_bond_orders(recorded('ch4_orca_bond_orders_2026.7.15.txt'))
    assert [orders[k][0] for k in multiwfn.BOND_KINDS] == [(0, 1, 0.99865228), (0, 1, 0.99089237), (0, 1, 0.96128455),
                                                          (0, 1, 1.006548)]
    assert all(len(orders[k]) == 4 for k in multiwfn.BOND_KINDS)
    assert orders['valence'][0] == pytest.approx(3.99460909) and len(orders['valence']) == 5


def test_composition_of_the_water_homo():
    from types import SimpleNamespace

    from modules.spectrum.readers.orbital_files import read_orbitals

    found = multiwfn.parse_composition(recorded('water_fchk_composition_2026.7.15.txt'))
    assert found == {5: (-0.388215, {0: 93.124, 1: 3.438, 2: 3.438})}
    water = read_orbitals((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                          .read_text(encoding='utf-8'))
    assert multiwfn.composition_of(water, found) == {4: {0: 93.124, 1: 3.438, 2: 3.438}}  # HOMO: the fifth orbital
    assert multiwfn.composition_of(water, {5: (-0.5, {0: 100.0})}) == {}  # another energy: not this orbital
    o = lambda spin: SimpleNamespace(spin=spin)  # noqa: E731
    open_shell = SimpleNamespace(orbitals=[o('alpha'), o('alpha'), o('alpha'), o('beta'), o('beta'), o('beta')])
    assert [multiwfn.orbital_number(open_shell, k) for k in range(6)] == [1, 2, 3, 4, 5, 6]
    assert multiwfn.orbital_number(water, 4) == 5


def test_the_homo_grid_of_multiwfn_is_our_orbital():
    # two independent computations of the HOMO of water: the grid of Multiwfn 2026.7.15 (5 → 4 → 5, cropped and thinned)
    # and the orbital from the basis of Azimuth at its points — the same within the printed digits
    import numpy as np

    from modules.spectrum.analysis import density
    from modules.spectrum.readers.cube import read_cube
    from modules.spectrum.readers.orbital_files import read_orbitals
    from modules.compass.chemistry.geometry_tools import BOHR

    water = read_orbitals((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                          .read_text(encoding='utf-8'))
    cube = read_cube(gz('water_fchk_homo.cub.gz'))
    shape = cube.values.shape[:3]
    index = np.array(np.meshgrid(*(np.arange(0, n, 3) for n in shape), indexing='ij')).reshape(3, -1).T
    points = cube.origin + index @ cube.axes  # Å
    phi, _, _ = density.basis_values(water.shells, water.centres, points / BOHR, 0)
    ours = phi @ water.coefficients[:, 4]
    theirs = cube.values[index[:, 0], index[:, 1], index[:, 2], 0]
    if np.dot(ours, theirs) < 0:  # the phase of an orbital is arbitrary
        ours = -ours
    assert np.max(np.abs(ours - theirs)) < 1e-4 * max(1.0, np.max(np.abs(theirs))) + 2e-5


def test_fake_multiwfn_orders_composition_and_grids(tmp_path):
    from modules.spectrum.readers.orbital_files import read_orbitals

    fake = fake_program(tmp_path, f'''
if answer(0) == '9':
    cat({q(DATA / "ch4_orca_bond_orders_2026.7.15.txt")})
if answer(0) == '8':
    cat({q(DATA / "water_fchk_composition_2026.7.15.txt")})
if answer(0) == '5':
    gunzip({q(DATA / "water_fchk_homo.cub.gz")}, 'MOvalue.cub')
    cat({q(DATA / "water_fchk_homo_grid_2026.7.15.txt")})
''')
    fchk = Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk'
    orders, _, number = multiwfn.run_bond_orders(fake, fchk)
    assert set(orders) >= set(multiwfn.BOND_KINDS) and number == '2026.7.15'
    found, _, _ = multiwfn.run_composition(fake, fchk, 7)
    assert found[5][1][0] == pytest.approx(93.124)
    water = read_orbitals(fchk.read_text(encoding='utf-8'))
    cube = multiwfn.field_cube((fake, fchk, 1), water, 'orbital', 4, 0.15)
    assert cube.values.shape[:3] == (25, 22, 22)  # Multiwfn's grid
    broken = fake_program(tmp_path / 'broken', 'sys.exit(1)', name='broken')
    with pytest.raises(ValueError):  # Multiwfn replaces our grid — its failure is said, not hidden
        multiwfn.field_cube((broken, fchk, 1), water, 'orbital', 4, 0.25)
    assert multiwfn.field_cube(None, water, 'density', step=0.25).values.max() > 1
    assert multiwfn.grid_for_step(0.25) == 'low' and multiwfn.grid_for_step(0.15) == 'medium'
    assert multiwfn.grid_for_step(0.10) == 'high'


@pytest.mark.skipif(multiwfn.find(search=True) is None, reason='Multiwfn is not installed')
def test_live_multiwfn_bond_orders_and_composition():
    water = Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk'
    orders, _, _ = multiwfn.run_bond_orders(multiwfn.find(search=True), water)
    assert set(multiwfn.BOND_KINDS) <= set(orders) and len(orders['mayer']) >= 2
    found, _, _ = multiwfn.run_composition(multiwfn.find(search=True), water, 7)
    assert found[5][1][0] == pytest.approx(93.124, abs=0.5) and len(found) == 7


def test_fake_multiwfn_line_and_plane(tmp_path):
    # the answers of the line (3 → ρ → two atoms → «1,2» → 2) and of the plane (4 → ρ → 1 → «N,N» → 4 →
    # «1,2,3» → −6) as Multiwfn 2026.7.15 reads them; the files it writes are the recorded ones
    fake = fake_program(tmp_path, f'''
if answers(4) == '3 1 1 1,2':
    gunzip({q(DATA / "water_fchk_rho_line_O1-H2.txt.gz")}, 'line.txt')
if answers(6) == '4 1 1 100,100 4 1,2,3':
    gunzip({q(DATA / "water_fchk_rho_plane_1-2-3.txt.gz")}, 'plane.txt')
''')
    fchk = Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk'
    line = multiwfn.run_line(fake, fchk, 'rho', (0, 1))
    assert line['values'].max() == pytest.approx(193.35234678)
    plane = multiwfn.run_plane(fake, fchk, 'rho', (0, 1, 2), 100)
    assert plane['values'].shape == (100, 100)
    with pytest.raises(ValueError):
        multiwfn.run_line(fake, fchk, 'rho', (1, 2))  # the fake writes nothing for other atoms
    with pytest.raises(ValueError):
        multiwfn.run_plane(fake, fchk, 'orbital', (0, 1, 2))


# -- excited states ----------------------------------------------------------------------------------------------
def test_hole_electron_indices_of_benzaldehyde():
    # Multiwfn 2026.7.15 on a CAM-B3LYP/def2-SVPD TD-DFT of benzaldehyde (ORCA, 10 states; the user's calculation):
    # S1 (n → π*, 3.787 eV) and S3 (the bright π → π*, 5.597 eV) — both local: t < 0, D about 1 Å
    s1 = multiwfn.parse_hole_electron(recorded('benzaldehyde_orca_hole_s1_2026.7.15.txt'))
    assert s1 == {'sr': 0.52079, 'sm': 0.26063, 'd': 0.905, 'h': 1.645, 't': -0.235, 'hdi': 23.74, 'edi': 13.1,
                  'energy': 3.787, 'hole': 0.989034, 'electron': 0.989177}
    s3 = multiwfn.parse_hole_electron(recorded('benzaldehyde_orca_hole_s3_2026.7.15.txt'))
    assert s3['d'] == 1.111 and s3['t'] == -0.288 and s3['energy'] == 5.597
    assert multiwfn.parse_delta_r(recorded('benzaldehyde_orca_delta_r_s1_2026.7.15.txt')) == {1: 1.749411}
    every = multiwfn.parse_delta_r(recorded('benzaldehyde_orca_delta_r_all_2026.7.15.txt'))  # 18 → 4 → out → «»
    assert len(every) == 10 and every[1] == 1.749411 and every[4] == 3.175143 and max(every, key=every.get) == 4


def test_fake_multiwfn_excitations(tmp_path):
    fake = fake_program(tmp_path, f'''
if not (os.path.isfile('excited.out') and os.path.isfile('input.molden')):
    sys.exit(3)
if ' '.join(lines[1:4]) == '1 excited.out 1':
    cat({q(DATA / "benzaldehyde_orca_hole_s1_2026.7.15.txt")})
if ' '.join(lines[1:4]) == '1 excited.out 3':
    cat({q(DATA / "benzaldehyde_orca_hole_s3_2026.7.15.txt")})
if answer(1) == '4':
    cat({q(DATA / "benzaldehyde_orca_delta_r_s1_2026.7.15.txt")})
''')
    molden = tmp_path / 'Бензальдегид.molden.input'
    molden.write_text('[Molden Format]\n', encoding='utf-8')
    out = tmp_path / 'benz.out'
    out.write_text('ORCA', encoding='utf-8')
    indices, _, number = multiwfn.run_hole_electron(fake, molden, out, 3)
    assert indices['d'] == 1.111 and number == '2026.7.15'
    assert multiwfn.run_delta_r(fake, molden, out)[0] == {1: 1.749411}
    with pytest.raises(ValueError):
        multiwfn.run_hole_electron(fake, molden, out, 2)  # nothing printed for it


def test_cache_of_runs_and_old_versions(tmp_path):
    # the same run (program, file, answers) is taken from the cache; a changed file runs again; the old 3.7
    # is told once through on_version
    counter = tmp_path / 'count'
    fake = fake_program(tmp_path, f'''
with open({q(counter)}, 'a', encoding='utf-8') as out:
    out.write('x\\n')
echo(' Multiwfn -- Version 3.7(dev)')
''')
    wfn = tmp_path / 'a.fchk'
    wfn.write_text('one')
    said = []
    multiwfn.clear_cache()
    old_hook = multiwfn.on_version
    multiwfn.on_version = lambda number, old: said.append((number, old))
    multiwfn._versions_said.discard('3.7(dev)')
    try:
        first, _ = multiwfn._run(fake, wfn, ('1', 'q'))
        second, _ = multiwfn._run(fake, wfn, ('1', 'q'))
        assert first == second and counter.read_text().count('x') == 1
        multiwfn._run(fake, wfn, ('2', 'q'))  # other answers
        assert counter.read_text().count('x') == 2
        wfn.write_text('changed file')
        multiwfn._run(fake, wfn, ('1', 'q'))
        assert counter.read_text().count('x') == 3
        assert said == [('3.7(dev)', True)]
    finally:
        multiwfn.on_version = old_hook
        multiwfn.clear_cache()
    assert multiwfn.is_old('3.7') and not multiwfn.is_old('3.8(dev)') and not multiwfn.is_old('2026.7.15')
    assert multiwfn.version_tuple('2026.7.15') == (2026, 7, 15) and multiwfn.version_tuple(None) is None


def test_windows_command_folder_and_search(tmp_path, monkeypatch):
    # on Windows Multiwfn is the build with a window — «-silent» keeps it in the text mode; the temporary folder
    # has an ASCII path even under a Cyrillic user name; the unpacked «Multiwfn*» folders are searched
    assert multiwfn.command('C:/M/Multiwfn.exe', 'input.fchk', 4, windows=True)[-1] == '-silent'
    assert '-silent' not in multiwfn.command('/opt/homebrew/bin/Multiwfn', 'input.fchk', 4, windows=False)
    cyrillic = tmp_path / 'Сергей'
    cyrillic.mkdir()
    public = tmp_path / 'Public'
    public.mkdir()
    monkeypatch.setenv('PUBLIC', str(public))
    folder = multiwfn.work_folder(windows=True, base=cyrillic)
    assert str(folder).isascii() or not str(public).isascii()
    assert folder.parent.parent == public
    unpacked = tmp_path / 'Downloads' / 'Multiwfn_2026.7.15_bin_Win64'
    unpacked.mkdir(parents=True)
    assert unpacked in multiwfn.windows_dirs(tmp_path, drives=())
    # «Извлечь всё» of Explorer — a folder of the name of the archive inside; the Desktop of OneDrive
    twice = tmp_path / 'Multiwfn_2026.7.15_bin_Win64' / 'Multiwfn_2026.7.15_bin_Win64'
    twice.mkdir(parents=True)
    cloud = tmp_path / 'OneDrive' / 'Desktop' / 'Multiwfn'
    cloud.mkdir(parents=True)
    found = multiwfn.windows_dirs(tmp_path, drives=())
    assert twice in found and twice.parent in found and cloud in found
    # the build for Windows waits for ENTER without settings.ini (Multiwfn 2026.10.18): the settings.ini of
    # its package is copied into the folder of the run; with none, an empty first answer; macOS — the answers as
    # they are
    package, run = tmp_path / 'package', tmp_path / 'run'
    package.mkdir()
    run.mkdir()
    exe = package / 'Multiwfn.exe'
    answers = ('7', '1', '1', 'n', '0', 'q')
    assert multiwfn.windows_answers(exe, run, answers, windows=False) == answers
    assert multiwfn.windows_answers(exe, run, answers, windows=True, environ={}) == ('',) + answers
    (package / 'settings.ini').write_text('nthreads= 2\n', encoding='utf-8')
    assert multiwfn.windows_answers(exe, run, answers, windows=True, environ={}) == answers
    assert (run / 'settings.ini').read_text(encoding='utf-8') == 'nthreads= 2\n'
    (package / 'settings.ini').unlink()
    (run / 'settings.ini').unlink()
    elsewhere = tmp_path / 'settings'
    elsewhere.mkdir()
    (elsewhere / 'settings.ini').write_text('', encoding='utf-8')
    found = multiwfn.windows_answers(exe, run, answers, windows=True, environ={'Multiwfnpath': str(elsewhere)})
    assert found == answers


def test_singlets_and_triplets_of_orca(tmp_path):
    # Multiwfn asks «Load which kind of excited states? 1: Singlet 3: Triplet» — the kind is answered before the
    # number of the state, which is that within its kind
    from types import SimpleNamespace

    from modules.spectrum.views.uv_view import UVVisPanel

    fake = fake_program(tmp_path, f'''
if ' '.join(lines[1:5]) == '1 excited.out 3 1':
    cat({q(DATA / "benzaldehyde_orca_hole_s1_2026.7.15.txt")})
''')
    molden = tmp_path / 'water.molden.input'
    molden.write_text('[Molden Format]\n', encoding='utf-8')
    out = tmp_path / 'water.out'
    out.write_text('ORCA', encoding='utf-8')
    indices, _, _ = multiwfn.run_hole_electron(fake, molden, out, 1, kind='3')
    assert indices['d'] == 0.905
    # the rows of the table (by the energy, the kinds mixed) to the numbers within the kind, as ORCA prints them
    rows = [SimpleNamespace(state=1, multiplicity=3), SimpleNamespace(state=1, multiplicity=1),
            SimpleNamespace(state=2, multiplicity=3)]
    view = SimpleNamespace(excitations=rows)
    view.mixed_kinds = lambda: UVVisPanel.mixed_kinds(view)
    assert [UVVisPanel.multiwfn_state(view, k) for k in (1, 2, 3)] == [(1, '3'), (1, '1'), (2, '3')]
    view.excitations = [SimpleNamespace(state=1, multiplicity=1), SimpleNamespace(state=2, multiplicity=1)]
    assert UVVisPanel.multiwfn_state(view, 2) == (2, None)  # one kind: no question

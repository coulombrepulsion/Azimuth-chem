"""The tables written into the folder of a calculation (modules/spectrum/wavefunction/field_tables.py).

Oracles: the grids and outputs recorded with Multiwfn 2026.7.15 (tests/data/multiwfn/): the ELF of water has its
attractors on the nuclei and two lone pairs of the oxygen; the HOMO two lobes of opposite sign on the oxygen; the
deepest dip of RDG of the water dimer at the donor hydrogen; the CSV files open as tables.
"""

import gzip
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.wavefunction import field_tables, multiwfn
from modules.spectrum.readers.cube import read_cube

DATA = Path(__file__).parents[1] / 'data' / 'multiwfn'


def cube(name):
    return read_cube(gzip.open(DATA / name, 'rt').read())


def read(path):
    header, rows = field_tables.read_csv(path)
    return [header] + [[c.replace(',', '.') for c in row] for row in rows]


def test_extrema_of_elf_homo_and_rdg():
    elf = field_tables.grid_extrema(cube('water_fchk_ELF.cub.gz'), 'max')
    assert len(elf) == 5 and all(e['kind'] == 'max' for e in elf)
    assert sorted(e['atom'] for e in elf) == [0, 0, 0, 1, 2]  # O core, two lone pairs, two H
    pairs = [e for e in elf if e['atom'] == 0 and e['distance'] > 0.3]
    assert len(pairs) == 2 and all(0.4 < e['distance'] < 0.7 and e['value'] > 0.9 for e in pairs)
    homo = field_tables.grid_extrema(cube('water_fchk_homo.cub.gz'), 'both')
    assert [e['kind'] for e in homo] == ['max', 'min'] and homo[0]['value'] == pytest.approx(-homo[1]['value'], rel=0.05)
    rdg = field_tables.grid_extrema(cube('dimer_nci_promol_func2.cub.gz'), 'min', below=1.0)
    assert rdg[0]['value'] < 0.2 and rdg[0]['atom'] == 2 and all(e['value'] < 1.0 for e in rdg)
    flat = read_cube(gzip.open(DATA / 'dimer_nci_promol_func2.cub.gz', 'rt').read())
    plateau = field_tables.grid_extrema(flat, 'min')  # without «below»: the plateau of 100 is no minimum
    assert all(e['value'] < 100 for e in plateau)


def test_csv_tables(tmp_path):
    from modules.spectrum.analysis import density
    from modules.spectrum.readers.orbital_files import read_orbitals

    elf = cube('water_fchk_ELF.cub.gz')
    header, rows = field_tables.extrema_table(field_tables.grid_extrema(elf, 'max'), ['O', 'H', 'H'])
    written = field_tables.write_tables(tmp_path, 'water', {'elf_extrema': (header, rows)})
    assert [p.name for p in written] == ['water_elf_extrema.csv']
    assert written[0].parent == tmp_path / 'Анализ'  # the subfolder of the analysis
    table = read(written[0])
    assert table[0][0] == '№' and len(table) == 6 and table[1][6] in ('O1', 'H2', 'H3')
    assert written[0].read_bytes().startswith(b'\xef\xbb\xbf')  # the BOM: spreadsheets read the Cyrillic
    esp = multiwfn.parse_surface((DATA / 'water_fchk_esp_2026.7.15.txt').read_text(encoding='utf-8'))
    tables = field_tables.esp_tables(esp, ['O', 'H', 'H'], elf.molecule.atoms)
    assert set(tables) == {'esp_extrema', 'esp_summary'}
    _, extrema = tables['esp_extrema']
    assert extrema[0][1] == 'минимум' and extrema[0][2] == '-0.069319' and extrema[0][4] == '-43.4981'
    assert extrema[0][9] == 'O1'  # the minimum of the ESP lies over the oxygen
    summary = dict((row[0], row[1]) for row in tables['esp_summary'][1])
    assert summary['Площадь поверхности'] == '39.1428' and summary['Индекс полярности MPI'] == '20.8946'
    alie = multiwfn.parse_surface((DATA / 'water_fchk_alie_surface_2026.7.15.txt').read_text(encoding='utf-8'))
    alie['mapped'] = 'alie'
    tables = field_tables.esp_tables(alie, ['O', 'H', 'H'])
    assert set(tables) == {'alie_extrema', 'alie_summary'} and tables['alie_extrema'][1][0][3] == '14.9016'
    assert dict((r[0], r[2]) for r in tables['alie_summary'][1])['Минимум'] == 'эВ'
    water = read_orbitals((Path(__file__).parents[2] / 'examples' / '6-orbitals' / 'water_mp2_gaussian16.fchk')
                          .read_text(encoding='utf-8'))
    topology = density.topology_from(multiwfn.parse_cps((DATA / 'water_fchk_CPprop_2026.7.15.txt')
                                                        .read_text(encoding='utf-8')), water)
    cps = field_tables.cp_tables(topology, ['O', 'H', 'H'])
    assert set(cps) == {'qtaim_nuclei', 'qtaim_bonds'}  # no rings and cages in water: no files for them
    header, bonds = cps['qtaim_bonds']
    assert header[:2] == ['№', 'Атомы'] and [r[1] for r in bonds] == ['O1–H2', 'O1–H3']
    assert bonds[0][5] == '0.351544' and bonds[0][7] == '0.0453'
    assert [r[1] for r in cps['qtaim_nuclei'][1]] == ['O1', 'H2', 'H3']
    paths = field_tables.write_tables(tmp_path, 'water', cps)
    assert sorted(p.name for p in paths) == ['water_qtaim_bonds.csv', 'water_qtaim_nuclei.csv']
    assert np.isclose(float(read(paths[0])[1][5]), 0.351544) or np.isclose(float(read(paths[1])[1][5]), 0.351544)


def test_profile_and_map_of_water():
    # Multiwfn 2026.7.15, ρ of the water of examples/6-orbitals along O1–H2 (3 → 1 → 1 → 1,2) and in the plane of the
    # three atoms (4 → 1 → 1 → 100,100 → 4 → 1,2,3): the minimum of ρ between O and H is the bond critical point —
    # ρ = 0.3515, as the topology (CPprop.txt) gives; the map has its maxima on the three nuclei
    line = multiwfn.read_line(gzip.open(DATA / 'water_fchk_rho_line_O1-H2.txt.gz', 'rt').read())
    assert line['points'].shape == (3000, 3)
    extrema = field_tables.line_extrema(line['x'], line['values'], line['points'])
    assert [e['kind'] for e in extrema] == ['max', 'min', 'max']
    assert extrema[1]['value'] == pytest.approx(0.3515442357, abs=2e-4)
    cps = multiwfn.parse_cps((DATA / 'water_fchk_CPprop_2026.7.15.txt').read_text(encoding='utf-8'))
    bcp = next(c for c in cps if c['kind'] == 'bond' and set(c['atoms']) == {0, 1})
    assert np.linalg.norm(extrema[1]['position'] - bcp['position']) < 0.01
    plane = multiwfn.read_plane(gzip.open(DATA / 'water_fchk_rho_plane_1-2-3.txt.gz', 'rt').read())
    assert plane['values'].shape == (100, 100) and plane['points'].shape == (100, 100, 3)
    tops = [e for e in field_tables.map_extrema(plane['values'], plane['points']) if e['kind'] == 'max']
    assert len(tops) == 3 and tops[0]['value'] > 100  # the oxygen nucleus, then the two hydrogens
    laplacian = multiwfn.read_plane(gzip.open(DATA / 'water_fchk_laplacian_plane_1-2-3.txt.gz', 'rt').read())
    assert laplacian['values'].min() < 0 < laplacian['values'].max()


def test_csv_styles(tmp_path):
    # «;» and the decimal comma for a Russian spreadsheet, «,» and the point otherwise; text cells untouched
    header, rows = ['№', 'x, Å', 'Атом'], [[1, '-0.5000', 'O1'], [2, '1e-05', 'H2–O1']]
    ru = field_tables.write_tables(tmp_path, 'a', {'t': (header, rows)}, 'ru')[0]
    assert ru.read_text(encoding='utf-8-sig').splitlines() == ['№;x, Å;Атом', '1;-0,5000;O1', '2;1e-05;H2–O1']
    intl = field_tables.write_tables(tmp_path, 'b', {'t': (header, rows)}, 'intl')[0]
    assert intl.read_text(encoding='utf-8-sig').splitlines()[1] == '1,-0.5000,O1'
    assert field_tables.read_csv(ru) == (header, [['1', '-0,5000', 'O1'], ['2', '1e-05', 'H2–O1']])
    assert field_tables.read_csv(intl)[0] == header
    # the separator and the decimal sign apart («Файл → Настройки…»): Tab with the comma, «;» with the point
    tab = field_tables.write_tables(tmp_path, 'c', {'t': (header, rows)}, '\t,')[0]
    assert tab.read_text(encoding='utf-8-sig').splitlines()[1] == '1\t-0,5000\tO1'
    assert field_tables.read_csv(tab)[0] == header
    point = field_tables.write_tables(tmp_path, 'd', {'t': (header, rows)}, ';.')[0]
    assert point.read_text(encoding='utf-8-sig').splitlines()[1] == '1;-0.5000;O1'
    assert field_tables.style_code(';', ',') == 'ru' and field_tables.style_code(',', '.') == 'intl'
    assert field_tables.style_code(',', ',') == 'intl'  # the comma between the columns takes the point
    assert field_tables.style_code('\t', '.') == '\t.' and field_tables.style_parts('\t.') == ('\t', '.')
    assert field_tables.valid_style('xx') == field_tables.valid_style(',,') == 'ru'
    assert field_tables.valid_style(';.') == ';.' and field_tables.valid_style('intl') == 'intl'
    saved = field_tables.save_output(tmp_path / 'w.molden.input', 'esp', 'text')
    assert saved == tmp_path / 'Анализ' / 'w_multiwfn_esp.txt' and saved.read_text() == 'text'


def test_a_search_again_writes_its_tables_in_place(tmp_path):
    # the same files written again; a table the new search has not is removed, not left from the one before
    header, rows = ['№', 'ρ'], [[1, '0.3']]
    first = {'qtaim_bonds': (header, rows), 'qtaim_rings': (header, rows), 'qtaim_contacts': (header, rows)}
    field_tables.write_tables(tmp_path, 'mol', first, family=field_tables.QTAIM_TABLES)
    field_tables.write_tables(tmp_path, 'mol', {'elf_extrema': (header, rows)})  # another analysis
    again = field_tables.write_tables(tmp_path, 'mol', {'qtaim_bonds': (header, [[1, '0.4']])},
                                      family=field_tables.QTAIM_TABLES)
    names = sorted(p.name for p in (tmp_path / field_tables.ANALYSIS).iterdir())
    assert names == ['mol_elf_extrema.csv', 'mol_qtaim_bonds.csv'] and again[0].name == 'mol_qtaim_bonds.csv'
    assert field_tables.read_csv(again[0])[1] == [['1', '0,4']]


def test_the_points_found_are_kept_for_the_same_file_of_orbitals(tmp_path):
    # the topology written beside the result is read back for the .gbw and for its Molden alike, while the file Multiwfn
    # read is the same; computed again — none
    from modules.spectrum.analysis.density import CriticalPoint, Topology

    molden = tmp_path / 'water_B3LYP.molden.input'
    molden.write_text('[Molden Format]\n', encoding='utf-8')
    bond = CriticalPoint('bond', np.array([0.1, 0.2, 0.3]), 0.35, -2.1, np.array([-1.0, -0.9, 0.5]), 0.02, 0.1,
                         -0.5, -0.4, (0, 1))
    nucleus = CriticalPoint('nucleus', np.zeros(3), 300.0, -1e4, np.array([-1e3, -1e3, -1e3]), None, 0.0, 0.0, 0.0,
                            (0,))
    topology = Topology((bond,), (np.array([[0.0, 0.0, 0.0], [0.1, 0.2, 0.3], [0.9, 0.0, 0.0]]),),
                        {'n': 1, 'b': 1, 'r': 0, 'c': 0}, 0, ('a note',), (nucleus,))
    assert field_tables.save_topology(molden, topology) is not None
    for name in ('water_B3LYP.molden.input', 'water_B3LYP.gbw'):
        back = field_tables.load_topology(tmp_path / name)
        assert back is not None and back.counts == topology.counts and back.notes == ('a note',)
        assert back.points[0].atoms == (0, 1) and back.points[0].rho == pytest.approx(0.35)
        assert np.allclose(back.points[0].position, bond.position) and back.nuclei[0].ellipticity is None
        assert np.allclose(back.paths[0], topology.paths[0])
    molden.write_text('[Molden Format]\n[Atoms] again\n', encoding='utf-8')
    assert field_tables.load_topology(molden) is None
    assert field_tables.load_topology(tmp_path / 'other.molden') is None


def test_an_output_kept_is_read_back_while_its_orbitals_are_the_same(tmp_path):
    # the charges of Multiwfn opened again without it — the check of the file of orbitals is cheap (its
    # size and that it did not change after the record), not its SHA-256
    gbw = tmp_path / 'water.gbw'
    gbw.write_bytes(b'0' * 100)
    assert field_tables.saved_output(gbw, 'charges') is None  # nothing kept
    field_tables.save_output(gbw, 'charges', 'CM5 charges ---')
    assert field_tables.saved_output(gbw, 'charges') == 'CM5 charges ---'
    assert field_tables.saved_output(tmp_path / 'water.molden.input', 'charges') == 'CM5 charges ---'  # its Molden
    gbw.write_bytes(b'1' * 101)  # computed again
    assert field_tables.saved_output(gbw, 'charges') is None


def test_the_last_map_and_profile_are_kept_for_the_same_orbitals(tmp_path):
    molden = tmp_path / 'water.molden.input'
    molden.write_text('[Molden Format]\n', encoding='utf-8')
    u, v = np.linspace(-3, 3, 5), np.linspace(-2, 2, 4)
    plane = {'u': u, 'v': v, 'values': np.arange(20.0).reshape(5, 4), 'points': np.zeros((5, 4, 3))}
    assert field_tables.save_field(molden, 'map', plane, 'rho', (0, 1, 2)) is not None
    data, name, atoms = field_tables.load_field(tmp_path / 'water.gbw', 'map')
    assert name == 'rho' and atoms == (0, 1, 2) and np.allclose(data['values'], plane['values'])
    assert np.allclose(data['u'], u) and data['points'].shape == (5, 4, 3)
    assert field_tables.load_field(molden, 'line') is None
    molden.write_text('[Molden Format]\nchanged\n', encoding='utf-8')
    assert field_tables.load_field(molden, 'map') is None


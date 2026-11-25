"""A crystal as a project (azimuth/crystal_projects.py).

Oracles: the file of the crystal is the text given byte for byte; a project of molecules made by Project.create is not
a crystal project and its document has no key «crystal» (it is written as before); a run recorded is read back.
"""

from pathlib import Path

from azimuth import crystal_projects, projects

CIF = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'benzoic_acid.cif'


def test_a_crystal_project_keeps_its_file_and_runs(tmp_path):
    text = CIF.read_text(encoding='utf-8')
    path = crystal_projects.create(tmp_path, 'benzoic_acid', text)
    assert path.name == 'project.qcc' and (path.parent / 'calculations').is_dir()
    assert crystal_projects.is_crystal(path) and crystal_projects.is_crystal(path.parent)
    assert crystal_projects.cif_text(path) == text and crystal_projects.title(path) == 'benzoic_acid'
    assert crystal_projects.info(path)['formula'] == 'C7H6O2'
    project = projects.Project.view(path)
    assert project.molecules == [] and project.data['name'] == 'benzoic_acid' and not project.data.get('draft')
    crystal_projects.record_run(path, {'folder': 'calculations/qe-x', 'task': 'Энергия', 'energy_ry': -1.5})
    assert crystal_projects.info(path)['runs'] == [{'folder': 'calculations/qe-x', 'task': 'Энергия', 'energy_ry': -1.5}]
    again = crystal_projects.create(tmp_path, 'benzoic_acid', text)  # the same name — a folder of its own
    assert again.parent != path.parent and crystal_projects.is_crystal(again)


def test_a_molecule_project_is_not_a_crystal(tmp_path):
    project = projects.Project.create(tmp_path / 'molecules')
    assert not crystal_projects.is_crystal(project.path) and crystal_projects.KEY not in project.data
    assert not crystal_projects.is_crystal(tmp_path / 'nothing') and not crystal_projects.is_crystal('')


def test_several_crystals_in_one_project(tmp_path):
    # each crystal has its file and its runs; the first stays where an older Azimuth reads it
    text = CIF.read_text(encoding='utf-8')
    other = (CIF.parent / 'CsCl.cif').read_text(encoding='utf-8')
    path = crystal_projects.create(tmp_path, 'benzoic_acid', text)
    crystal_projects.record_run(path, {'folder': 'calculations/a'})
    ident = crystal_projects.add(path, other, 'CsCl')
    assert crystal_projects.active(path) == ident and crystal_projects.title(path) == 'CsCl'
    assert crystal_projects.cif_text(path) == other and crystal_projects.info(path)['runs'] == []
    crystal_projects.record_run(path, {'folder': 'calculations/b'})
    crystal_projects.set_active(path, crystal_projects.FIRST)
    assert crystal_projects.cif_text(path) == text and crystal_projects.info(path)['runs'] == [{'folder': 'calculations/a'}]
    assert [(c['id'], c['title'], c['runs']) for c in crystal_projects.crystals(path)] == [
        ('crystal', 'benzoic_acid', [{'folder': 'calculations/a'}]), (ident, 'CsCl', [{'folder': 'calculations/b'}])]
    data = projects.Project.view(path).data[crystal_projects.KEY]  # what an older Azimuth reads
    assert data['cif'] == 'crystal.cif' and data['runs'] == [{'folder': 'calculations/a'}]
    assert crystal_projects.add(path, other, 'CsCl') != ident  # each its own file


def test_the_columns_of_a_crystal_in_the_list(tmp_path):
    # the method and the energy of the file
    # (an output of CRYSTAL) until a run has them; the formula and the atoms of the cell
    from modules.compass.chemistry import surface
    from modules.spectrum.readers import crystal_out as co

    out = Path(__file__).resolve().parents[1] / 'data' / 'crystal' / 'caform-final.out'
    result = co.read(out.read_text())
    path = crystal_projects.create(tmp_path, 'CAFORM', surface.write_cif(co.final_crystal(result, 'CAFORM')))
    info = crystal_projects.info(path)
    assert info['atoms'] == 72 and info['formula'] == 'C2H2CaO4'  # the formula unit, Ca(HCOO)2
    crystal_projects.set_result(path, 'CRYSTAL17 · PBE0', result.energy)
    method, energy, atoms, *_ = crystal_projects.cells(path, crystal_projects.info(path))
    assert method == 'CRYSTAL17 · PBE0' and atoms == '72'
    crystal_projects.record_run(path, {'folder': 'calculations/qe', 'program': 'qe', 'task': 'relax', 'energy_ry': -2.0})
    method, energy, *_ = crystal_projects.cells(path, crystal_projects.info(path))
    assert method == 'Quantum ESPRESSO · relax' and energy == '-1.000000'


def test_the_batch_of_crystals(tmp_path):
    # the ticks of the batch
    text = CIF.read_text(encoding='utf-8')
    path = crystal_projects.create(tmp_path, 'benzoic_acid', text)
    second = crystal_projects.add(path, text, 'benzoic_acid 2')
    assert crystal_projects.batch_ids(path) == ['crystal', second]
    crystal_projects.set_in_batch(path, 'crystal', False)
    assert crystal_projects.batch_ids(path) == [second]
    crystal_projects.set_in_batch(path, 'crystal', True)
    assert crystal_projects.batch_ids(path) == ['crystal', second]
    crystal_projects.set_result(path, 'CRYSTAL17 · PBE0', -1.0, second, pressure=3.5)
    assert crystal_projects.pressure(crystal_projects.info(path, second)) == 3.5
    assert crystal_projects.pressure(crystal_projects.info(path, 'crystal')) is None  # the first: none

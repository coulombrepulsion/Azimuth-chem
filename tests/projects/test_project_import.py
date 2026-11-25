"""A project of calculations done outside Azimuth (azimuth/project_import.py).

Calculations done outside Azimuth (usually a folder each) become a project; the files of a calculation share a name.
Oracles: the files of an output are those of its name (and not those of a longer name of another output beside it); a
project made has a molecule per molecule, a done record per output with its energy as the output prints it, the files
copied into its folder, the originals untouched.
"""

from pathlib import Path
import shutil

from azimuth import project_import, projects

DATA = Path(__file__).resolve().parents[1] / 'data'


def calculations(tmp_path):
    source = tmp_path / 'source'
    one = source / 'water-cpcm'
    one.mkdir(parents=True)
    shutil.copy(DATA / 'orca601' / 'h2o_cpcm_water.out', one / 'water.out')
    (one / 'water.gbw').write_bytes(b'gbw')
    (one / 'water.inp').write_text('! B3LYP def2-SVP\n', encoding='utf-8')
    (one / 'water.tmp.0').write_bytes(b'')
    two = source / 'ch2o'
    two.mkdir()
    shutil.copy(DATA / 'orca601' / 'ch2o_excited_opt.out', two / 'ch2o.out')
    shutil.copy(DATA / 'orca611' / 'ch2o_excited_opt_libxc_b3lyp.out', two / 'ch2o_libxc.out')
    (two / 'ch2o.gbw').write_bytes(b'gbw')
    (two / 'ch2o_trj.xyz').write_text('', encoding='utf-8')
    (two / 'ch2o_libxc.gbw').write_bytes(b'gbw2')
    (source / 'notes.txt').write_text('not a calculation', encoding='utf-8')
    return source


def test_the_files_of_one_name(tmp_path):
    source = calculations(tmp_path)
    found = {f.output.name: sorted(p.name for p in f.files) for f in project_import.find([source])}
    assert found == {'water.out': ['water.gbw', 'water.inp', 'water.out'],
                     'ch2o.out': ['ch2o.gbw', 'ch2o.out', 'ch2o_trj.xyz'],
                     'ch2o_libxc.out': ['ch2o_libxc.gbw', 'ch2o_libxc.out']}


def test_a_project_of_calculations(tmp_path):
    source = calculations(tmp_path)
    manifest, report = project_import.build(tmp_path / 'projects', 'Импорт', [source])
    assert len(report) == 3 and all(outcome.startswith('готово') for _, outcome in report), report
    project = projects.Project.view(manifest)
    assert project.data['name'] == 'Импорт' and not project.data.get('draft')
    names = sorted(e['name'] for e in project.molecules)
    assert names[0].startswith('ch2o') and 'water' in names  # CH2O twice from the same start — one molecule
    assert sorted(len(e['attempts']) for e in project.molecules) == [1, 2]
    for entry in project.molecules:
        current = project.current(entry)
        assert current is not None and current['state'] == 'done' and current['keywords']
        folder = projects.attempt_folder(project, current)
        assert (folder / Path(current['output']).name).is_file() and any(folder.glob('*.gbw'))
        assert not any(folder.glob('*.tmp*'))
    assert (source / 'water-cpcm' / 'water.out').is_file()  # the originals stay


def test_a_run_that_failed_is_said(tmp_path):
    source = tmp_path / 'failed'
    source.mkdir()
    shutil.copy(DATA / 'orca611' / 'ch2o_excited_opt_b3lyp.out', source / 'bad.out')  # «use the LibXC version»
    shutil.copy(DATA / 'orca601' / 'h2o_cpcm_water.out', source / 'water.out')
    _, report = project_import.build(tmp_path / 'projects', 'x', [source])
    said = {Path(o).name: outcome for o, outcome in report}
    assert said['bad.out'].startswith('не прочитан') and said['water.out'].startswith('готово')


def test_one_molecule_computed_otherwise_is_one_molecule(tmp_path):
    # water by B3LYP/CPCM and by MP2 from other starts —
    # one molecule with two calculations
    source = tmp_path / 'water'
    for name, path in (('b3lyp', DATA / 'orca601' / 'h2o_cpcm_water.out'),
                       ('mp2', Path(__file__).resolve().parents[2] / 'examples' / '1-properties' / 'water_mp2_orca5.out')):
        (source / name).mkdir(parents=True)
        shutil.copy(path, source / name / f'{name}.out')
    manifest, report = project_import.build(tmp_path / 'projects', 'Вода', [source])
    project = projects.Project.view(manifest)
    assert len(project.molecules) == 1 and len(project.molecules[0]['attempts']) == 2, report


def test_conformers_are_not_one_molecule():
    from dataclasses import replace

    from azimuth.core import Atom
    from modules.compass.chemistry import library, torsion

    butane = library.molecule('Бутан · C₄H₁₀')
    anti = torsion.set_dihedral(butane, 0, 1, 2, 3, 2, 180.0)
    gauche = torsion.set_dihedral(butane, 0, 1, 2, 3, 2, 60.0)
    moved = replace(anti, atoms=tuple(Atom(a.symbol, a.x + 0.02, a.y - 0.01, a.z + 0.015) for a in anti.atoms))
    assert project_import.same_molecule(anti, moved) and not project_import.same_molecule(anti, gauche)
    reordered = replace(anti, atoms=tuple(reversed(anti.atoms)), bonds=None)  # the atoms in another order
    assert project_import.same_molecule(anti, reordered)
    assert not project_import.same_molecule(anti, replace(gauche, atoms=tuple(reversed(gauche.atoms)), bonds=None))


def test_a_copy_of_an_output_is_taken_once(tmp_path):
    source = tmp_path / 'copies'
    # the same output copied beside its Molden file is one calculation
    for sub in ('a', 'a/molden'):
        (source / sub).mkdir(parents=True)
        shutil.copy(DATA / 'orca601' / 'h2o_cpcm_water.out', source / sub / 'water.out')
    manifest, report = project_import.build(tmp_path / 'projects', 'x', [source])
    assert len(projects.Project.view(manifest).molecules[0]['attempts']) == 1
    assert sorted(outcome.split(':')[0] for _, outcome in report)[-1] == 'не взят'


def test_the_atom_of_the_guess_is_a_file_of_its_calculation(tmp_path):
    # «<name>_atom38.out» — the SCF of a free atom ORCA writes for
    # its guess beside the output — goes with that calculation, it is no calculation of its own
    folder = tmp_path / 'sr'
    folder.mkdir()
    shutil.copy(DATA / 'orca601' / 'h2o_cpcm_water.out', folder / 'complex.out')
    shutil.copy(DATA / 'orca601' / 'h2o_cpcm_water.out', folder / 'complex_atom38.out')
    found = project_import.find([folder])
    assert [f.output.name for f in found] == ['complex.out']
    assert 'complex_atom38.out' in [p.name for p in found[0].files]


def test_an_output_without_the_final_single_point_energy():
    # the energy is the last «Total Energy» of the SCF
    import re

    from modules.spectrum.readers.outputs import read_any

    text = (DATA / 'orca601' / 'h2o_cpcm_water.out').read_text(encoding='utf-8', errors='replace')
    last = float(re.findall(r'^Total Energy\s*:\s*(-?\d+\.\d+)', text, re.M)[-1])
    stripped = re.sub(r'FINAL SINGLE POINT ENERGY.*\n', '', text)
    assert read_any(stripped).energies[-1] == last


def test_the_files_each_program_needs(tmp_path):
    # xtb — its files of fixed
    # names; Gaussian — the checkpoint of «%chk=» and its .fchk under the name of the output (Spectrum looks there);
    # Psi4 alone in its folder — its Molden; NWChem — the files of its prefix; MOPAC — .aux and .arc, ΔHf as result
    import gzip

    source = tmp_path / 'programs'
    shutil.copytree(DATA / 'xtb' / 'dvb_opt', source / 'xtb')
    (source / 'g16').mkdir(parents=True)
    shutil.copy(DATA / 'gaussian' / 'dvb_gopt_g16.log', source / 'g16' / 'dvb_gopt_g16.log')
    (source / 'g16' / 'dvb.chk').write_bytes(b'chk')
    (source / 'g16' / 'dvb.fchk').write_text('fchk', encoding='utf-8')
    (source / 'psi4').mkdir()
    shutil.copy(DATA / 'psi4' / 'dvb_sp_rhf_psi4-1.7.out', source / 'psi4' / 'output.dat')
    (source / 'psi4' / 'dvb.molden').write_text('[Molden Format]', encoding='utf-8')
    (source / 'nw').mkdir()
    (source / 'nw' / 'run.out').write_bytes(gzip.open(DATA / 'nwchem' / 'dvb_sp_ks_nwchem-7.0.out.gz').read())
    (source / 'nw' / 'dvb.movecs').write_bytes(b'mo')
    (source / 'mopac').mkdir()
    for ext in ('.out', '.aux', '.arc'):
        shutil.copy(DATA / 'mopac' / ('h2o_pm7_opt' + ext), source / 'mopac' / ('h2o_pm7_opt' + ext))
    found = {f.output.name: f for f in project_import.find([source])}
    assert set(found) == {'dvb_opt.out', 'dvb_gopt_g16.log', 'output.dat', 'run.out', 'h2o_pm7_opt.out'}
    files = {name: sorted(p.name for p in f.files) for name, f in found.items()}
    assert {'xtbopt.xyz', 'xtbopt.log', 'charges', 'wbo', 'dvb_opt.xyz'} <= set(files['dvb_opt.out'])
    assert files['dvb_gopt_g16.log'] == ['dvb.chk', 'dvb.fchk', 'dvb_gopt_g16.log']
    assert {k: v.name for k, v in found['dvb_gopt_g16.log'].renamed.items()} == {'dvb_gopt_g16.fchk': 'dvb.fchk'}
    assert {k: v.name for k, v in found['output.dat'].renamed.items()} == {'output.molden': 'dvb.molden'}
    assert 'dvb.movecs' in files['run.out'] and files['h2o_pm7_opt.out'] == ['h2o_pm7_opt.arc', 'h2o_pm7_opt.aux',
                                                                             'h2o_pm7_opt.out']
    manifest, report = project_import.build(tmp_path / 'projects', 'Программы', [source])
    assert all(outcome.startswith('готово') for _, outcome in report), report
    project = projects.Project.view(manifest)
    for entry in project.molecules:
        current = project.current(entry)
        folder = projects.attempt_folder(project, current)
        if current['kind'] == 'gaussian':
            assert (folder / 'dvb_gopt_g16.fchk').is_file()  # where Spectrum finds the orbitals
        if current['kind'] == 'xtb':
            assert (folder / 'xtbopt.xyz').is_file() and current['keywords'] == 'GFN2-xTB'

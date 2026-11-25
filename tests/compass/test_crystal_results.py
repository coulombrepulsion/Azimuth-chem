"""The results of the runs of a project of a crystal (modules/compass/chemistry/crystal_results.py).

Oracles: the real runs of the tests — the CELL_OPT of CsCl (CP2K 2026.2: 11 steps, the last cell 5.2841042 Å), the
vc-relax of silicon and its DOS (pw.x 7.6); the CM5 charges of Multiwfn of CsCl 3 × 3 × 3 (±0.547) put on the atoms of
the cell of the file — one Cs, one Cl."""

from pathlib import Path
import shutil

from azimuth import crystal_projects
from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_results as R
from modules.spectrum.wavefunction import crystal_aim

DATA = Path(__file__).resolve().parents[1] / 'data'
EXAMPLES = Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'


def project(tmp_path):
    manifest = crystal_projects.create(tmp_path, 'CsCl', (EXAMPLES / 'CsCl.cif').read_text(encoding='utf-8'))
    folder = Path(manifest).parent / 'calculations'
    shutil.copytree(DATA / 'cp2k' / 'cscl_cellopt', folder / 'cp2k-1')
    (folder / 'qe-1').mkdir()
    shutil.copyfile(DATA / 'qe' / 'si_dos_pw76.out', folder / 'qe-1' / 'pw.out')
    shutil.copyfile(DATA / 'qe' / 'si_dos_pw76.dos', folder / 'qe-1' / 'azimuth.dos')
    for name, program in (('cp2k-1', 'cp2k'), ('qe-1', 'qe'), ('gone', 'qe')):
        crystal_projects.record_run(manifest, {'folder': f'calculations/{name}', 'program': program, 'task': 'x'})
    return Path(manifest)


def test_the_runs_and_their_steps(tmp_path):
    manifest = project(tmp_path)
    runs = R.runs(manifest)
    assert [r.folder.name for r in runs] == ['cp2k-1', 'qe-1']  # a folder gone is left out
    assert R.last(manifest).program == 'qe' and R.last(manifest, 'cp2k').folder.name == 'cp2k-1'
    assert R.last(manifest, having='*.molden').folder.name == 'cp2k-1'
    table = R.steps_table(R.steps(runs[0]))
    assert len(table) == 11 and abs(table[-1]['a'] - 5.2841042) < 1e-6
    assert abs(table[-1]['volume'] - 5.2841042 ** 3) < 1e-3
    assert R.result(runs[0]).energy_hartree is not None


def test_the_dos_and_the_vc_relax_of_quantum_espresso(tmp_path):
    folder = tmp_path / 'qe'
    folder.mkdir()
    shutil.copyfile(DATA / 'qe' / 'si_dos_pw76.out', folder / 'pw.out')
    shutil.copyfile(DATA / 'qe' / 'si_dos_pw76.dos', folder / 'azimuth.dos')
    found, e0 = R.dos(R.Run(folder, 'qe'))
    assert found.energies and e0 is not None
    assert R.bands(R.Run(folder, 'qe')) is None  # no path.json: not a run of the bands
    shutil.copyfile(DATA / 'qe' / 'si2_vcrelax_pw76.out', folder / 'pw.out')
    rows = R.steps_table(R.steps(R.Run(folder, 'qe')))
    assert len(rows) >= 2 and rows[0]['volume'] != rows[-1]['volume']


def test_what_multiwfn_computed_is_kept(tmp_path):
    R.write_charges(tmp_path, [('Cs', None), ('Cl', None)], {'cm5': (0.5, -0.5), 'hirshfeld': (0.3, -0.3)})
    assert R.read_charges(tmp_path) == (('Cs', 'Cl'), {'hirshfeld': (0.3, -0.3), 'cm5': (0.5, -0.5)})
    rows = [('Cl–Cs', '3.59', 'Cl: 8, Cs: 8', '0.0094', '+0.0272', '+0.00115', '0.80', 'closed')]
    R.write_aim(tmp_path, rows, {'census': {'poincare_hopf': 17}, 'atoms': 54, 'version': 'x'})
    assert R.read_aim(tmp_path) == (rows, {'census': {'poincare_hopf': 17}, 'atoms': 54, 'version': 'x'})
    assert R.read_charges(tmp_path / 'нет') is None and R.read_aim(tmp_path / 'нет') is None


def test_the_charges_of_a_supercell_on_the_model():
    text = (DATA / 'multiwfn' / 'crystal_cscl333_geometry.molden').read_text(encoding='utf-8')
    charges = crystal_aim.parse_charges((DATA / 'multiwfn' / 'crystal_cm5_a_cp2k-CsCl-20261112-144541.txt')
                                        .read_text(encoding='utf-8'))
    original = cr.parse_cif((EXAMPLES / 'CsCl.cif').read_text(encoding='utf-8'))
    points = [(a[0], original.cell.cartesian(a[1:4])) for a in cr.unit_cell(original)]
    points += [('Cs', (4.123, 4.123, 0.0)), ('Cl', (1.0, 0.0, 0.0))]  # a corner of the next cell; an atom nowhere
    shown = R.model_charges(text, charges['cm5'], original.cell.vectors(), points)
    assert [round(v, 3) if v is not None else None for v in shown] == [0.547, -0.547, 0.547, None]

"""An optimization that converged gives the molecule of the project its geometry, so a sequence MOPAC → ORCA →
QTAIM needs no manual transfer.

Oracles: the final geometry ORCA prints in tests/data/orca_cclib/dvb_gopt_orca6.0.out (THE OPTIMIZATION HAS CONVERGED)
and the one MOPAC prints in tests/data/mopac/c2h4_pm7_opt.out (GEOMETRY OPTIMISED) — read by batch.result_of, the
reader the project already uses for its results.
"""

import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from azimuth import projects
from azimuth.core import Calculation
from modules.sextant import batch

DATA = Path(__file__).parents[1] / 'data'


def setup(tmp_path, kind, name, task='Оптимизация'):
    project = projects.Project.create(tmp_path / 'project')
    source = DATA / ('orca_cclib' if kind == 'orca' else 'mopac') / name
    output = project.root / 'calculations' / 'job' / name
    output.parent.mkdir(parents=True)
    shutil.copy(source, output)
    _, final, _, _ = batch.result_of(kind, output.read_text(encoding='utf-8', errors='replace'))
    start = replace(final, atoms=tuple(replace(a, x=a.x + 0.1) for a in final.atoms))  # the structure before
    calc = Calculation(task=task, method='PM7' if kind == 'mopac' else 'B3LYP')
    with projects.edit(project.path) as changed:
        ident = changed.add(start, calc, kind, 'molecule')['id']
    return project.path, ident, start, final, calc, output


def positions(molecule):
    return [v for a in molecule.atoms for v in a.position]


def test_a_converged_optimization_gives_its_geometry(tmp_path):
    for kind, name in (('orca', 'dvb_gopt_orca6.0.out'), ('mopac', 'c2h4_pm7_opt.out')):
        path, ident, start, final, calc, output = setup(tmp_path / kind, kind, name)
        with projects.edit(path) as project:
            project.record(ident, 'attempt-1', start, calc, kind, 'done', output.parent, output)
        project = projects.Project.load(path)
        entry = project.entry(ident)
        molecule, _ = project.read_structure(entry['structure'])
        assert entry['adopted'] == 'attempt-1', kind
        assert positions(molecule) == pytest.approx(positions(final), abs=1e-6)
        started, _ = project.read_structure(entry['attempts'][0]['input'])
        assert positions(started) == pytest.approx(positions(start), abs=1e-6)  # the structure before: in the attempt


def test_energy_task_and_an_edit_after_the_start_keep_the_structure(tmp_path):
    path, ident, start, final, calc, output = setup(tmp_path, 'orca', 'dvb_gopt_orca6.0.out', task='Энергия')
    with projects.edit(path) as project:
        project.record(ident, 'attempt-1', start, calc, 'orca', 'done', output.parent, output)
    entry = projects.Project.load(path).entry(ident)
    assert 'adopted' not in entry  # not an optimization
    path, ident, start, final, calc, output = setup(tmp_path / 'b', 'orca', 'dvb_gopt_orca6.0.out')
    edited = replace(start, atoms=tuple(replace(a, y=a.y + 0.5) for a in start.atoms))
    with projects.edit(path) as project:
        project.record(ident, 'attempt-1', start, calc, 'orca', 'running', output.parent, output)
        entry = project.entry(ident)
        entry['structure'] = project.structure(edited, calc)  # the user edited the molecule while it ran
    with projects.edit(path) as project:
        project.record(ident, 'attempt-1', start, calc, 'orca', 'done', output.parent, output)
    project = projects.Project.load(path)
    entry = project.entry(ident)
    molecule, _ = project.read_structure(entry['structure'])
    assert 'adopted' not in entry and positions(molecule) == pytest.approx(positions(edited), abs=1e-6)


def test_an_optimization_that_did_not_converge_is_not_taken(tmp_path):
    path, ident, start, final, calc, output = setup(tmp_path, 'orca', 'dvb_gopt_orca6.0.out')
    output.write_text(output.read_text(encoding='utf-8', errors='replace').replace('THE OPTIMIZATION HAS CONVERGED',
                                                                                   'THE OPTIMIZATION STOPPED'),
                      encoding='utf-8')
    with projects.edit(path) as project:
        project.record(ident, 'attempt-1', start, calc, 'orca', 'done', output.parent, output)
    assert 'adopted' not in projects.Project.load(path).entry(ident)

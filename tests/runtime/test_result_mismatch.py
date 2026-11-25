"""T23 of docs/architecture/PROJECT_RUNTIME_GUIDE.md §13: after a change of the method, charge or geometry the results
and analyses are not rebound, and the mismatch is shown.

Oracles: the input of the attempt as recorded at its start (Project.record) and the geometry the calculation printed
(tests/data/orca_cclib/dvb_gopt_orca6.0.out, read by batch.result_of — the reader of the project); the record of an
analysis (azimuth/runtime/analysis.Ledger) with the SHA-256 of the artifact it copied.
"""

import shutil
from dataclasses import replace

from azimuth import projects
from azimuth.runtime import analysis
from tests.runtime.test_adopted_geometry import setup


def recorded(tmp_path, task='Энергия'):
    path, ident, start, final, calc, output = setup(tmp_path, 'orca', 'dvb_gopt_orca6.0.out', task=task)
    with projects.edit(path) as project:
        project.record(ident, 'attempt-1', start, calc, 'orca', 'done', output.parent, output)
    return path, ident, start, final, calc, output


def edit(path, ident, molecule, calc, kind='orca'):
    with projects.edit(path) as project:
        entry = project.entry(ident)
        entry['structure'] = project.structure(molecule, calc)
        entry['kind'] = kind


def mismatch(path, ident, **now):
    project = projects.Project.load(path)
    return projects.result_mismatch(project, project.entry(ident), **now)


def test_a_result_of_the_data_of_the_molecule_has_no_mismatch(tmp_path):
    path, ident, *_ = recorded(tmp_path / 'energy')
    assert mismatch(path, ident) == ()
    path, ident, _, final, *_ = recorded(tmp_path / 'opt', task='Оптимизация')  # adopted: the result's own geometry
    assert projects.Project.load(path).entry(ident)['adopted'] == 'attempt-1' and mismatch(path, ident) == ()
    # the geometry of the optimization, kept a few thousandths of an Å
    # off (written with another precision) — still the result's own; a real edit (0.3 Å) is a change
    nudged = replace(final, atoms=tuple(replace(a, x=a.x + 0.006) for a in final.atoms))
    assert mismatch(path, ident, molecule=nudged) == ()
    moved = replace(final, atoms=tuple(replace(a, x=a.x + 0.3) for a in final.atoms))
    assert mismatch(path, ident, molecule=moved) == ('geometry',)
    path, ident, start, final, calc, output = setup(tmp_path / 'none', 'orca', 'dvb_gopt_orca6.0.out')
    assert mismatch(path, ident) == ()  # no result — nothing to differ from


def test_each_change_is_named_and_the_result_stays_its_own(tmp_path):
    path, ident, start, final, calc, output = recorded(tmp_path)
    moved = replace(start, atoms=tuple(replace(a, z=a.z + 0.3) for a in start.atoms))
    for molecule, changed, kind, expected in (
            (moved, calc, 'orca', ('geometry',)),
            (start, replace(calc, charge=1, multiplicity=2), 'orca', ('charge', 'multiplicity')),
            (start, replace(calc, method='PBE0'), 'orca', ('theory',)),
            (start, replace(calc, solvent='water'), 'orca', ('theory',)),
            (start, replace(calc, cores=8, memory_mb=4000), 'orca', ()),  # resources are not the data of the result
            (start, calc, 'gaussian', ('program',))):
        edit(path, ident, molecule, changed, kind)
        assert mismatch(path, ident) == expected, expected
        project = projects.Project.load(path)
        entry = project.entry(ident)
        assert entry['current'] == 'attempt-1'  # not rebound, not dropped
        then, then_calc = project.read_structure(entry['attempts'][0]['input'])
        assert then_calc.charge == 0 and then_calc.method == calc.method
        assert projects._same_geometry(then, start)
    edit(path, ident, start, calc)
    assert mismatch(path, ident) == ()
    # an edit in the tab, not saved yet, is what the tab shows
    assert mismatch(path, ident, molecule=moved) == ('geometry',)
    assert mismatch(path, ident, calc=replace(calc, charge=-1)) == ('charge',)
    assert projects.mismatch_text(('geometry', 'charge')) == 'геометрия, заряд'


def test_t23_a_new_charge_keeps_the_old_result_and_its_analysis_until_its_own_result(tmp_path):
    path, ident, start, final, calc, output = recorded(tmp_path)
    # an analysis of the result of attempt-1 (QTAIM reads a copy of the artifact — §3d)
    ledger = analysis.Ledger(tmp_path / 'analyses')
    artifact = analysis.snapshot(output, 'attempt-1', tmp_path / 'analyses' / 'a1')
    ledger.finish(ledger.begin('qtaim', artifact))
    charged = replace(calc, charge=1, multiplicity=2)
    edit(path, ident, start, charged)
    # Act: the calculation with the new charge fails — the old result stays current, its mismatch said
    second = output.parent.parent / 'job-2' / output.name
    second.parent.mkdir()
    shutil.copy(output, second)
    with projects.edit(path) as project:
        project.record(ident, 'attempt-2', start, charged, 'orca', 'failed', second.parent, second)
    project = projects.Project.load(path)
    entry = project.entry(ident)
    assert entry['current'] == 'attempt-1' and mismatch(path, ident) == ('charge', 'multiplicity')
    # Act: it succeeds — its own result is current, nothing differs; the old attempt and the analysis stay as they were
    with projects.edit(path) as project:
        project.record(ident, 'attempt-2', start, charged, 'orca', 'done', second.parent, second)
    project = projects.Project.load(path)
    entry = project.entry(ident)
    assert entry['current'] == 'attempt-2' and mismatch(path, ident) == ()
    assert [a['id'] for a in entry['attempts']] == ['attempt-1', 'attempt-2']
    assert project.read_structure(entry['attempts'][0]['input'])[1].charge == 0
    (record,) = analysis.Ledger(tmp_path / 'analyses').records()
    assert record.state == 'succeeded' and record.attempt_id == 'attempt-1'
    assert record.sha256 == analysis.sha256(output)

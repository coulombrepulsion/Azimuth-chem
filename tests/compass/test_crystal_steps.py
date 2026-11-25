"""The steps of the optimization of a crystal (modules/compass/chemistry/crystal_steps.py).

Oracles: shifts known by construction in a cubic cell of 10 Å (an atom moved by 1 Å, an atom across a face by 0.4 Å, a
drift of the whole content), the cell of pw.x 7.6 (vc-relax of Si: 3.840 → 3.866 Å, the volume (3.8661/3.84)³ − 1).
"""

from pathlib import Path

import pytest

from modules.compass.chemistry import crystal_steps as cs
from modules.spectrum.readers import cp2k, qe

DATA = Path(__file__).resolve().parents[1] / 'data'
CUBE = ((10.0, 0.0, 0.0), (0.0, 10.0, 0.0), (0.0, 0.0, 10.0))


def pair(*steps):
    return [s.crystal for s in cs.make_steps([(None, CUBE, atoms) for atoms in steps])]


def test_one_atom_moved_by_one_angstrom():
    first, step = pair((('Na', (0.1, 0.5, 0.5)), ('Cl', (0.5, 0.5, 0.5))),
                       (('Na', (0.2, 0.5, 0.5)), ('Cl', (0.5, 0.5, 0.5))))
    d = cs.difference(first, step)
    # shifts (1, 0, 0) and 0; the drift of the whole (0.5, 0, 0) out: 0.5 Å each
    assert d.rmsd == pytest.approx(0.5) and d.largest == pytest.approx(0.5) and d.volume_percent == pytest.approx(0)
    assert cs.ghost(first, step).atoms[0].x == pytest.approx(1.0)


def test_an_atom_across_a_face_moved_a_little():
    first, step = pair((('O', (0.98, 0.5, 0.5)), ('H', (0.5, 0.5, 0.5))),
                       (('O', (0.02, 0.5, 0.5)), ('H', (0.5, 0.5, 0.5))))
    d = cs.difference(first, step)
    assert d.rmsd == pytest.approx(0.2) and d.largest == pytest.approx(0.2)  # 0.4 Å, not 9.6 Å back across the cell
    assert cs.ghost(first, step).atoms[0].x == pytest.approx(-0.2)  # the start at the image beside the atom of the step


def test_a_drift_of_the_whole_is_no_shift():
    first, step = pair((('C', (0.1, 0.2, 0.3)), ('N', (0.4, 0.5, 0.6))),
                       (('C', (0.13, 0.22, 0.31)), ('N', (0.43, 0.52, 0.61))))
    assert cs.difference(first, step).rmsd == pytest.approx(0, abs=1e-12)


def test_other_atoms_are_refused():
    first, step = pair((('C', (0.1, 0.2, 0.3)),), (('N', (0.1, 0.2, 0.3)),))
    with pytest.raises(ValueError):
        cs.difference(first, step)


def test_the_vc_relax_of_silicon():
    steps = cs.make_steps(qe.steps((DATA / 'qe' / 'si2_vcrelax_pw76.out').read_text(encoding='utf-8')), 'Si')
    assert [s.cycle for s in steps] == [0, 1, 2]
    assert [s.energy for s in steps] == [-16.92416232 / 2, -16.92442218 / 2, -16.92452158 / 2]  # the «!» lines, Ry
    d = cs.difference(steps[0].crystal, steps[2].crystal)
    assert d.volume_percent == pytest.approx(100 * ((3.866076314 / 3.84) ** 3 - 1), abs=0.01)
    assert d.cell[0] == pytest.approx(3.866076314 - 3.84, abs=1e-4) and max(abs(x) for x in d.cell[3:]) < 1e-4
    text = cs.describe(d, steps[2].crystal)
    assert text.startswith('От начальной: RMSD ') and 'ΔV +2.05 %' in text


def test_the_frames_of_cp2k():
    steps = cs.make_steps(cp2k.steps(DATA / 'cp2k'), 'Si')
    assert [round(s.crystal.cell.a, 4) for s in steps] == [5.431, 5.45, 5.47] and len(steps[0].geometry.atoms) == 8


def cscl():
    from modules.compass.chemistry import crystal as cr

    return cr.parse_cif((Path(__file__).resolve().parents[2] / 'examples' / '10-crystals' / 'CsCl.cif').read_text(
        encoding='utf-8'))


def test_the_group_of_the_file_comes_back():
    # the real CELL_OPT of CsCl (CP2K 2026.2): the cell grew (Γ point, a salt smeared as a metal — see is_metal), the
    # atoms stayed at 0 and ½: «Взять» gives P m -3 m with the labels of the file
    original = cscl()
    steps = cs.make_steps(cp2k.steps(DATA / 'cp2k' / 'cscl_cellopt'), 'CsCl', original)
    assert len(steps) == 11 and steps[0].crystal.cell.a == pytest.approx(4.123)
    last = steps[-1]
    assert last.note == '' and last.adopted.space_group == original.space_group
    assert last.adopted.cell.a == pytest.approx(5.2841042045) and [s.label for s in last.adopted.sites] == ['Cs1', 'Cl1']


def test_a_supercell_folds_back_and_a_broken_symmetry_is_said():
    from modules.compass.chemistry import crystal as cr

    original = cscl()
    big = cr.supercell(original, (3, 3, 3))
    rows = big.cell.vectors()
    atoms = tuple((s.symbol, (s.x, s.y, s.z)) for s in big.sites)
    step = cs.make_steps([(None, rows, atoms)], 'CsCl', original, (3, 3, 3))[0]
    assert len(step.crystal.sites) == 54 and step.adopted.space_group == original.space_group
    assert step.adopted.cell.a == pytest.approx(original.cell.a)
    # one Cl of the 27 moved: the copies differ — the supercell stays, in P 1, and the reason is said
    moved = tuple((s, (x + 0.01, y, z)) if k == 1 else (s, (x, y, z)) for k, (s, (x, y, z)) in enumerate(atoms))
    broken = cs.make_steps([(None, rows, moved)], 'CsCl', original, (3, 3, 3))[0]
    assert broken.adopted.space_group == 'P 1' and len(broken.adopted.sites) == 54 and 'суперячейки' in broken.note
    # the cell of the file with Cl off the centre: P m -3 m no longer holds
    off = cs.make_steps([(None, original.cell.vectors(), (('Cs', (0, 0, 0)), ('Cl', (0.52, 0.5, 0.5))))], 'CsCl',
                        original)[0]
    assert off.adopted.space_group == 'P 1' and 'симметрия' in off.note


def test_the_cell_computed_is_read_back():
    # a run kept in a project records no supercell — its first step tells it: CsCl a = 4.123 Å of the file,
    # 12.369 Å computed — 3 × 3 × 3 of the cell of the file; 4.123 — 1 × 1 × 1; 5.0 — no cell of the file fits
    original = cscl()
    a = original.cell.a
    assert cs.guess_computed(original, ((3 * a, 0, 0), (0, 3 * a, 0), (0, 0, 3 * a))) == ((3, 3, 3), False)
    assert cs.guess_computed(original, ((a, 0, 0), (0, a, 0), (0, 0, 2 * a))) == ((1, 1, 2), False)
    assert cs.guess_computed(original, ((5.0, 0, 0), (0, 5.0, 0), (0, 0, 5.0))) is None


def test_the_steps_of_a_run_of_the_project(tmp_path):
    # the real CELL_OPT of CsCl kept in a project: its steps found again from the record of the run
    import shutil

    from azimuth import crystal_projects

    manifest = crystal_projects.create(tmp_path, 'CsCl', (Path(__file__).resolve().parents[2] / 'examples' / '10-crystals'
                                                         / 'CsCl.cif').read_text(encoding='utf-8'))
    run = Path(manifest).parent / 'calculations' / 'cp2k-CsCl-1'
    shutil.copytree(DATA / 'cp2k' / 'cscl_cellopt', run)
    crystal_projects.record_run(manifest, {'folder': 'calculations/cp2k-CsCl-1', 'program': 'cp2k',
                                           'task': 'Оптимизация с ячейкой'})
    steps, folder = cs.project_steps(manifest, cscl(), 'CsCl')
    assert folder == run and len(steps) == 11 and abs(steps[-1].adopted.cell.a - 5.2841042) < 1e-6
    assert steps[-1].adopted.space_group.replace(' ', '') == 'Pm-3m'
    assert cs.project_steps(crystal_projects.create(tmp_path, 'Пусто', (Path(__file__).resolve().parents[2] / 'examples'
                                                    / '10-crystals' / 'CsCl.cif').read_text(encoding='utf-8')),
                            cscl(), 'CsCl') == ((), None)

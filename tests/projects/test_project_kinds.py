"""The kinds of the projects on disk and their sorting into «Молекулы» and «Кристаллы» (azimuth/project_kinds.py,
2026-11-13). Oracle: projects made here — of molecules, of a crystal, an empty draft, one already in «Кристаллы», a
folder without a project; where each must go follows from what it is."""

from pathlib import Path

from azimuth import crystal_projects, project_folders, project_kinds, projects
from azimuth.core import Calculation, read_xyz

WATER = '3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n'


def make(root):
    from modules.compass.chemistry import surface
    from tests.sextant.test_qe_inputs import silicon

    molecules = projects.Project.create(root / 'Вода')
    molecules.add(read_xyz(WATER), Calculation(method='PM7', task='Энергия'), 'mopac', name='Вода')
    molecules.save()
    crystal = crystal_projects.create(root, 'Si', surface.write_cif(silicon()))
    draft = projects.Project.create(root / 'Новый проект')
    draft.data.update(name='Новый проект', draft=True)
    draft.save()
    crystal_projects.create(root / 'Кристаллы', 'Si', surface.write_cif(silicon()))  # sorted already: «Кристаллы/Si»
    (root / 'не проект').mkdir()
    return Path(crystal)


def test_the_kinds(tmp_path):
    crystal = make(tmp_path)
    assert project_kinds.kind(crystal) == 'crystal'
    assert project_kinds.kind(tmp_path / 'Вода' / 'project.qcc') == 'molecule'
    assert project_kinds.kind(tmp_path / 'Новый проект' / 'project.qcc') == 'empty'
    assert project_kinds.kind(tmp_path / 'нет' / 'project.qcc') is None


def test_the_sorting(tmp_path):
    make(tmp_path)
    plan = {folder.name: target.relative_to(tmp_path).as_posix() for folder, target in project_kinds.plan(tmp_path, False)}
    assert plan == {'Вода': 'Молекулы/Вода', 'Si': 'Кристаллы/Si (2)', 'Новый проект': 'Молекулы/Новый проект'}
    moved, failed = project_kinds.sort(tmp_path, False)
    assert len(moved) == 3 and not failed and (tmp_path / 'Кристаллы' / 'Si (2)' / 'project.qcc').is_file()
    assert project_kinds.kind(tmp_path / 'Кристаллы' / 'Si (2)' / 'project.qcc') == 'crystal'
    assert (tmp_path / 'не проект').is_dir() and project_kinds.plan(tmp_path, False) == []
    assert project_folders.kind_root(tmp_path, 'crystal', windows=True).name == 'Crystals'

"""A project in the lists («Продолжить» of the home page, «Файл → Недавние файлы») is shown by its name, not as
project.qcc."""

from azimuth import projects


def test_a_project_is_shown_by_its_name_and_other_files_by_theirs(tmp_path):
    project = projects.Project.create(tmp_path / 'folder')
    with projects.edit(project.path) as changed:
        changed.data['name'] = 'cs'
    assert projects.display_name(project.path) == 'cs'
    other = tmp_path / 'water.xyz'
    other.write_text('1\nHe\nHe 0 0 0\n', encoding='utf-8')
    assert projects.display_name(other) == 'water.xyz'
    broken = tmp_path / 'broken' / projects.MANIFEST
    broken.parent.mkdir()
    broken.write_text('not a project', encoding='utf-8')
    assert projects.display_name(broken) == 'broken'  # unreadable: named by its folder


def test_the_folder_of_the_calculation_of_a_molecule(tmp_path):
    # the folder of its current
    # result, else of its newest attempt with a folder; None without a calculation
    from azimuth.core import Calculation, read_xyz

    project = projects.Project.create(tmp_path / 'p')
    water = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0')
    with projects.edit(project.path) as changed:
        ident = changed.add(water, Calculation(), 'orca', 'water')['id']
    assert projects.calculation_folder(projects.Project.load(project.path), projects.Project.load(project.path).entry(ident)) is None
    first, second = (project.root / 'calculations' / name for name in ('first', 'second'))
    for folder in (first, second):
        folder.mkdir(parents=True)
    with projects.edit(project.path) as changed:
        changed.record(ident, 'a1', water, Calculation(), 'orca', 'failed', first, first / 'w.out')
        changed.record(ident, 'a2', water, Calculation(), 'orca', 'running', second, second / 'w.out')
    loaded = projects.Project.load(project.path)
    assert projects.calculation_folder(loaded, loaded.entry(ident)) == second.resolve()  # the newest attempt
    second.rmdir()
    loaded = projects.Project.load(project.path)
    assert projects.calculation_folder(loaded, loaded.entry(ident)) == first.resolve()  # a folder gone: the one before

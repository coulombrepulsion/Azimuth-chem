"""The read-only view of a project is kept until project.qcc changes (azimuth/projects.py)."""

from azimuth import projects
from azimuth.core import Calculation, read_xyz

WATER = read_xyz('3\nwater\nO 0 0 0\nH 0.96 0 0\nH -0.24 0.93 0\n')


class TestView:
    def test_gives_the_same_project_when_nothing_changed(self, tmp_path):
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        project.add(WATER, Calculation(), name='water')
        project.save()
        # Act
        first = projects.Project.view(project.path)
        second = projects.Project.view(project.root)
        # Assert
        assert first is second and len(first.molecules) == 1

    def test_reads_again_when_the_project_is_edited(self, tmp_path):
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        project.save()
        before = projects.Project.view(project.path)
        # Act
        with projects.edit(project.path) as fresh:
            fresh.add(WATER, Calculation(), name='water')
        after = projects.Project.view(project.path)
        # Assert
        assert after is not before and len(after.molecules) == 1 and not before.molecules

    def test_leaves_the_file_alone_when_an_edit_changes_nothing(self, tmp_path):
        # choosing a molecule, the mode or a tick opened edit() and rewrote project.qcc each time
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        entry = project.add(WATER, Calculation(), name='water')
        project.save()
        stat = project.path.stat()
        # Act
        with projects.edit(project.path) as fresh:
            fresh.entry(entry['id'])['name'] = 'water'  # the same value again
        # Assert
        again = project.path.stat()
        assert (again.st_mtime_ns, again.st_ino) == (stat.st_mtime_ns, stat.st_ino)

    def test_keeps_the_view_unchanged_while_an_edit_is_open(self, tmp_path):
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        entry = project.add(WATER, Calculation(), name='water')
        project.save()
        view = projects.Project.view(project.path)
        # Act
        with projects.edit(project.path) as fresh:
            fresh.entry(entry['id'])['name'] = 'вода'
            during = view.entry(entry['id'])['name']
        # Assert
        assert during == 'water' and projects.Project.view(project.path).entry(entry['id'])['name'] == 'вода'

    def test_parses_a_structure_once_when_read_twice(self, tmp_path):
        # Arrange
        project = projects.Project.create(tmp_path / 'project')
        entry = project.add(WATER, Calculation(), name='water')
        # Act
        first, _ = project.read_structure(entry['structure'])
        second, _ = project.read_structure(dict(entry['structure']))
        # Assert
        assert first is second and first.formula == 'H2O'

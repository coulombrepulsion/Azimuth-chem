"""The folders of the projects (azimuth/project_folders.py) — PROJECT_RUNTIME_GUIDE.md §1."""

from pathlib import Path

import pytest

from azimuth import project_folders as pf


def test_the_default_root():
    assert pf.default_projects_root('/home/u', windows=False) == Path('/home/u/Documents/Azimuth/Проекты')
    assert pf.default_projects_root('C:/Users/sergey', windows=True) == Path('C:/Users/sergey/Documents/Azimuth/Projects')
    # a home folder in Cyrillic on Windows: the programs there would not open the files of the calculations
    public = pf.default_projects_root('C:/Users/Пользователь', windows=True, environ={'PUBLIC': 'C:/Users/Public'})
    assert public == Path('C:/Users/Public/Documents/Azimuth/Projects')


def test_the_root_chosen_and_the_override():
    assert pf.projects_root('/data/p', environ={}, windows=False) == Path('/data/p')
    assert pf.projects_root('', environ={pf.ENV: '/tmp/t'}) == Path('/tmp/t')
    # a root chosen with Cyrillic on Windows is not used
    assert pf.projects_root('D:/Проекты', environ={}, windows=True).name == 'Projects'


def test_folder_names():
    assert pf.folder_name('Лиганды: серия 2/3', windows=False) == 'Лиганды_ серия 2_3'
    assert pf.folder_name('Лиганды щёлочи', windows=True) == 'Ligandy shhyolochi'
    assert pf.folder_name('  ...  ', windows=False) == 'Project'
    assert pf.folder_name('CON', windows=False) == 'CON_'
    assert len(pf.folder_name('a' * 200, windows=False)) == pf.MAX_NAME
    assert pf.folder_name('水分子', windows=True) == '___'


def test_a_clash_gets_a_number(tmp_path):
    first = pf.new_project_folder(tmp_path, 'Вода', windows=False)
    second = pf.new_project_folder(tmp_path, 'Вода', windows=False)
    third = pf.new_project_folder(tmp_path, 'Вода', windows=False)
    assert [p.name for p in (first, second, third)] == ['Вода', 'Вода (2)', 'Вода (3)']
    assert all(p.is_dir() and not any(p.iterdir()) for p in (first, second, third))


def test_folder_names_are_valid_everywhere(tmp_path):
    for name in ('a<b>c', 'x|y?z*', 'tab\tname', 'dot.', 'Новый проект'):
        folder = pf.new_project_folder(tmp_path, name, windows=True)
        assert folder.name.isascii() and folder.exists()
    (tmp_path / 'file.txt').write_text('')
    with pytest.raises(OSError):
        pf.new_project_folder(tmp_path / 'file.txt' / 'x', 'a')  # a file in the way

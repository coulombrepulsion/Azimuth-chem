"""«Файлы на сервере»: modules/sextant/server_files.py and server_browser.py.

Oracles: listings printed by GNU ls (Linux servers of the laboratory) and BSD ls (macOS; the fake server of the tests
runs there) written by hand from their documented layout; the files the fake server (tests/fake_server.py: ssh runs
bash in <tmp>/home, scp copies) really has after each command.
"""

import os
from pathlib import Path

import pytest

from modules.sextant import server_files as sf
from tests import fake_server

GNU = """/home/user/azimuth/calculations
total 16
drwxr-xr-x 3 user users 4096 Nov  8 10:01 2026-11-08_H2O_orca
-rw-r--r-- 1 user users 1532 Nov  8 09:58 orca.sh
-rw-r--r-- 1 user users 120 Oct 27  2026 a file with spaces.inp
lrwxrwxrwx 1 user users 9 Nov  8 10:00 link -> orca.sh
"""
BSD = """/Users/x/azimuth
total 8
drwxr-xr-x@ 4 x  staff   128 Nov  8 10:01 Results
-rw-r--r--@ 1 x  staff  2048 Nov  8 09:58 b.out
"""


def test_listings_of_gnu_and_bsd_ls():
    path, entries = sf.parse_listing(GNU)
    assert path == '/home/user/azimuth/calculations'
    assert [(e.name, e.kind) for e in entries] == [('2026-11-08_H2O_orca', 'dir'), ('a file with spaces.inp', 'file'),
                                                   ('link -> orca.sh', 'link'), ('orca.sh', 'file')]
    assert entries[1].size == 120 and entries[1].when == 'Oct 27 2026'
    path, entries = sf.parse_listing(BSD)
    assert path == '/Users/x/azimuth' and [(e.name, e.kind, e.size) for e in entries] == [('Results', 'dir', 128),
                                                                                         ('b.out', 'file', 2048)]
    assert sf.parse_listing('') == ('', [])


def test_paths_and_commands():
    assert sf.child('~/a', 'b c') == '~/a/b c' and sf.child('/', 'x') == '/x' and sf.parent('/home/a/b') == '/home/a'
    assert sf.parent('/home') == '/' and sf.parent('~') == '/'
    assert sf.remove_command('~/a', ['x y', 'z']) == 'rm -rf -- "$HOME"/\'a/x y\' "$HOME"/a/z'
    assert sf.rename_command('/srv', 'a', 'b b') == "mv -- /srv/a '/srv/b b'"
    for bad in ('', '..', 'a/b'):
        with pytest.raises(ValueError):
            sf.make_command('/srv', bad)
    assert sf.human(512) == '512 Б' and sf.human(2048) == '2.0 КБ' and sf.human(5 * 1024 ** 3) == '5.0 ГБ'


@pytest.fixture
def server(tmp_path, monkeypatch):
    if os.name == 'nt':
        pytest.skip('the fake server is a set of POSIX scripts')
    return fake_server.install(tmp_path, monkeypatch)


def connection(tmp_path):
    from modules.sextant.remote import ServerProfile
    from modules.sextant.ssh import Connection

    (tmp_path / 'ctl').mkdir(exist_ok=True)
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', '~/azimuth/calculations')
    return profile, Connection(profile, control_dir=tmp_path / 'ctl')


def test_commands_on_the_fake_server(server, tmp_path):
    profile, c = connection(tmp_path)
    home = server / 'home'
    c.text(sf.make_command('~', 'res 1'))
    assert (home / 'res 1').is_dir()
    local = tmp_path / 'here'
    (local / 'sub').mkdir(parents=True)
    (local / 'water.inp').write_text('! HF\n', encoding='utf-8')
    (local / 'sub' / 'x.xyz').write_text('1\n\nH 0 0 0\n', encoding='utf-8')
    c.put([local / 'water.inp', local / 'sub'], '~/res 1')
    path, entries = sf.parse_listing(c.text(sf.list_command('~/res 1')))
    assert Path(path).resolve() == (home / 'res 1').resolve()
    assert [(e.name, e.kind) for e in entries] == [('sub', 'dir'), ('water.inp', 'file')]
    c.text(sf.rename_command('~/res 1', 'water.inp', 'water 2.inp'))
    back = tmp_path / 'back'
    back.mkdir()
    c.get(['water 2.inp', 'sub'], '~/res 1', back)
    assert (back / 'water 2.inp').read_text() == '! HF\n' and (back / 'sub' / 'x.xyz').exists()
    c.text(sf.remove_command('~/res 1', ['sub', 'water 2.inp']))
    assert list((home / 'res 1').iterdir()) == []


def test_the_window_on_the_fake_server(server, tmp_path, monkeypatch):
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication, QWidget

    from modules.sextant.server_browser import ServerBrowser

    app = QApplication.instance() or QApplication([])
    profile, c = connection(tmp_path)
    home = server / 'home'
    (home / 'azimuth' / 'calculations' / 'job1').mkdir(parents=True)
    (home / 'azimuth' / 'calculations' / 'job1' / 'w.out').write_text('ORCA output\n', encoding='utf-8')
    local = tmp_path / 'here'
    local.mkdir()
    (local / 'a.inp').write_text('! HF\n* xyz 0 1\nHe 0 0 0\n*\n', encoding='utf-8')
    opened = []

    class Owner(QWidget):
        def jobs_root(self):
            return tmp_path / 'jobs'

        def file_kind(self, path):
            return 'output' if path.endswith('.out') else 'xyz'

        def navigate(self, index):
            opened.append(('section', index))

        def drop_paths(self, paths):
            opened.append(('open', Path(paths[0]).read_text()))
            return paths[0]

        # the opening and the view are parts of the window (opening_tool, view_tool)
        @property
        def opening_tool(self):
            return self

        @property
        def view_tool(self):
            return self

    owner = Owner()
    browser = ServerBrowser(owner, profile, c, str(local))
    try:
        assert [e.name for e in browser.remote.entries] == ['job1'] and browser.remote.path.endswith('calculations')
        browser._activated(browser.remote, browser.remote.entries[0])  # into the folder
        assert [e.name for e in browser.remote.entries] == ['w.out']
        browser.active = browser.remote
        browser.remote.select(['w.out'])
        assert browser.open_in_azimuth() and opened[-2:] == [('section', 2), ('open', 'ORCA output\n')]
        browser.active = browser.local  # F5 here → there
        browser.local.select(['a.inp'])
        assert browser.copy() == 1 and (home / 'azimuth' / 'calculations' / 'job1' / 'a.inp').exists()
        browser.active = browser.remote
        browser.remote.select(['a.inp'])
        assert browser.edit(save=lambda text: text.replace('HF', 'PBE0')) is not None
        assert '! PBE0' in (home / 'azimuth' / 'calculations' / 'job1' / 'a.inp').read_text()
        assert browser.rename('b.inp') == 'b.inp' and browser.make_folder('new folder') == 'new folder'
        assert {e.name for e in browser.remote.entries} == {'b.inp', 'new folder', 'w.out'}
        browser.remote.select(['b.inp', 'new folder'])
        assert browser.delete(confirm=False) == 0 and browser.delete(confirm=True) == 2
        assert [e.name for e in browser.remote.entries] == ['w.out']
        browser.active = browser.remote
        browser.remote.select(['w.out'])
        assert browser.copy() == 1 and (local / 'w.out').exists()  # there → here
        browser.grab()
    finally:
        browser.close()
        owner.deleteLater()
        assert app is not None


def test_the_dates_of_the_listings_sort():
    # 2026-11-21 (Ctrl+F5 of «Файлы на сервере»): the dates of this computer and of ls, this year or another
    from datetime import datetime

    when_key = sf.when_key
    now = datetime(2026, 11, 21, 12, 0)
    assert when_key('2026-11-08 10:01') == (2026, 11, 8, 10, 1)
    assert when_key('Nov  8 10:01', now) == (2026, 11, 8, 10, 1)
    assert when_key('Dec 30 09:00', now) == (2025, 12, 30, 9, 0)  # in the future this year: the last one
    assert when_key('Oct 27 2024', now) == (2024, 10, 27, 0, 0) and when_key('вчера') == ()
    assert sf.parse_found('./a.out\n./job 1/w.out\n') == ['a.out', 'job 1/w.out']
    assert "-iname '*.out'" in sf.find_command('~/x', '*.out') and 'head -n 500' in sf.find_command('~/x', '*.out')


def test_the_keys_of_total_commander_on_the_fake_server(server, tmp_path):
    # marks by a mask and
    # by Insert, the order, F3 view, Shift+F4 a new file, F6 move, Alt+F7 find, Ctrl+D favourites, Ctrl+Shift+C paths
    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication, QWidget

    from modules.sextant.server_browser import ServerBrowser

    app = QApplication.instance() or QApplication([])
    profile, c = connection(tmp_path)
    home = server / 'home'
    job = home / 'azimuth' / 'calculations' / 'job1'
    job.mkdir(parents=True)
    (job / 'w.out').write_text('ORCA output\nFINAL SINGLE POINT ENERGY -76.0\n', encoding='utf-8')
    (job / 'deep').mkdir()
    (job / 'deep' / 'opt.out').write_text('x\n', encoding='utf-8')
    local = tmp_path / 'here'
    local.mkdir()
    for name, text in (('a.inp', '! HF\n'), ('b.out', 'b' * 300), ('c.out', 'c' * 30), ('d.xyz', '1\n\nH 0 0 0\n')):
        (local / name).write_text(text, encoding='utf-8')
    owner = QWidget()
    browser = ServerBrowser(owner, profile, c, str(local), '~/azimuth/calculations/job1')
    try:
        browser.active = browser.local
        browser._focus(browser.local)
        pane = browser.local
        assert browser.select_mask('*.out') == 2 and {e.name for e in pane.marked()} == {'b.out', 'c.out'}
        assert 'Выделено 2 из 4' in pane.marked_line.text()
        assert browser.invert() == 2 and {e.name for e in pane.marked()} == {'a.inp', 'd.xyz'}
        assert browser.select_mask('*', False) == 4 and pane.marked() == []
        from PySide6.QtCore import QItemSelectionModel

        pane.tree.setCurrentItem(pane.tree.topLevelItem(0), 0, QItemSelectionModel.SelectionFlag.NoUpdate)
        assert browser.mark() is True and pane.current().name == 'b.out'  # marked, the cursor one line down
        assert browser.sort_by('size') == ('size', True) and [e.name for e in pane.entries][0] == 'b.out'
        assert browser.sort_by('type')[0] == 'type' and [e.name for e in pane.entries][:3] == ['a.inp', 'b.out', 'c.out']
        browser.sort_by('name')
        pane.select(['a.inp'])
        assert browser.view(show=False) == '! HF\n'
        here = pane.path  # the real path (/private/var/… of a temporary folder on macOS)
        assert browser.copy_paths() == str(Path(here) / 'a.inp')
        assert sorted(browser.search('*.out', show=False)) == ['b.out', 'c.out']
        assert browser.add_favourite() == [here] and browser.favourites() == [here]
        browser.go_local(str(tmp_path))
        assert browser.go_favourite(here) and browser.local.path == here
        menu = browser.favourites_menu(show=False)
        assert here in [a.text() for a in menu.actions()]
        browser.active = browser.remote
        browser._focus(browser.remote)
        assert sorted(browser.search('*.out', show=False)) == ['deep/opt.out', 'w.out']
        assert browser.new_file('new.inp', save=lambda text: '! PBE0\n') is not None
        assert (job / 'new.inp').read_text() == '! PBE0\n'
        browser.remote.select(['w.out'])
        assert browser.move(confirm=False) == 0 and (job / 'w.out').exists()
        assert browser.move(confirm=True) == 1  # there → here: copied, then taken from the server
        assert (local / 'w.out').exists() and not (job / 'w.out').exists()
        # the files dragged into the window (from Finder) and between its panes
        from PySide6.QtCore import QMimeData, QUrl

        outside = tmp_path / 'outside.inp'
        outside.write_text('! HF\n', encoding='utf-8')
        dropped = QMimeData()
        dropped.setUrls([QUrl.fromLocalFile(str(outside))])
        assert browser.dropped_on(browser.remote, dropped) == 1 and (job / 'outside.inp').exists()
        assert browser.dropped_on(browser.local, dropped) == 1 and (local / 'outside.inp').exists()
        items = [browser.remote.tree.topLevelItem(k) for k in range(browser.remote.tree.topLevelItemCount())]
        dragged = browser.drag_data(browser.remote, [i for i in items if i.text(0) == 'new.inp'])
        assert browser.dragged(dragged)[0] == 'remote' and dragged.hasUrls()  # downloaded for a drop outside
        assert browser.dropped_on(browser.remote, dragged) == 0  # dropped where it came from
        assert browser.dropped_on(browser.local, dragged) == 1 and (local / 'new.inp').read_text() == '! PBE0\n'
        box = browser.show_keys()
        box.close()
        browser.grab()
    finally:
        browser.close()
        owner.deleteLater()
        assert app is not None

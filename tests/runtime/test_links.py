"""Links azimuth:// (azimuth/links.py) — without Qt. The oracles: the addresses written out by hand, the
library of Compass itself, the rules of quoting of a Windows command line, a registry that is a dictionary here."""

import contextlib

import pytest

from azimuth import links


@pytest.mark.parametrize('text, key', [
    ('azimuth://compass/water', 'water'),
    ('azimuth://compass/water/', 'water'),  # browsers and Windows may add the slash
    ('AZIMUTH://Compass/benzene', 'benzene'),
    ('  azimuth://compass/h2o2\n', 'h2o2'),
])
def test_addresses_understood(text, key):
    link = links.parse(text)
    assert (link.action, link.key) == ('compass', key)
    assert link.name == links.MOLECULES[key]


@pytest.mark.parametrize('text', [
    '', None, 5, 'water', 'azimuth:', 'azimuth://', 'azimuth://compass', 'azimuth://compass/',
    'azimuth://compass/unobtainium',  # not in the table
    'azimuth://compass/Water',  # keys are lower-case
    'azimuth://compass/water/more', 'azimuth://compass/water?x=1', 'azimuth://compass/water#x',
    'azimuth://compass/../../etc/passwd', 'azimuth://compass/water%00', 'azimuth://compass/wa ter',
    'azimuth://open/water', 'azimuth://compass//water', 'azimuth:compass/water', 'azimuth:///compass/water',
    'azimuth://user@compass/water', 'azimuth://compass:80/water', 'azimuth://compass/water" --install-tools "',
    'http://compass/water', 'file:///compass/water', 'azimuth://compass/' + 'a' * 41,
    'azimuth://compass/water\nazimuth://compass/benzene', 'azimuth://compass/' + 'water' * 60,
    'azimuth://compass/вода',
])
def test_everything_else_refused(text):
    assert links.parse(text) is None


def test_every_key_is_a_molecule_of_the_library():
    from modules.compass.chemistry import library

    assert len(links.MOLECULES) == 26
    assert set(links.MOLECULES.values()) <= set(library.keys())
    for key, name in links.MOLECULES.items():
        assert links.parse(links.address(key)).name == name
        assert len(library.molecule(name).atoms) >= 2
    with pytest.raises(ValueError):
        links.address('unobtainium')


def test_the_link_among_the_arguments():
    assert links.link_in(['gui_launcher.py', '--module', 'compass']) is None
    assert links.link_in(['Azimuth.exe', 'azimuth://compass/water']) == 'azimuth://compass/water'
    assert links.link_in(['x', 'AZIMUTH:whatever', 'azimuth://compass/water']) == 'AZIMUTH:whatever'  # as given
    assert links.link_in([]) is None


def test_command_lines():
    exe = r'C:\Users\Иван Петров\AppData\Local\Programs\Azimuth\Azimuth.exe'
    assert links.command_line(exe) == '"' + exe + '" "%1"'
    python, script = r'C:\A zimuth\.venv\Scripts\pythonw.exe', r'C:\A zimuth\gui_launcher.py'
    assert links.command_line(python, script) == '"' + python + '" -B "' + script + '" "%1"'
    for bad in ('C:\\a"b.exe', '', '  '):
        with pytest.raises(ValueError):
            links.command_line(bad)
    with pytest.raises(ValueError):
        links.command_line(exe, 'a"b.py')


class Registry:
    """What winreg does for these calls, over a dictionary {key path: {value name: data}}."""
    HKEY_CURRENT_USER, REG_SZ = 'HKCU', 1

    def __init__(self):
        self.keys = {}
        self.written = 0

    @contextlib.contextmanager
    def OpenKey(self, root, path):
        assert root == 'HKCU'
        if path not in self.keys:
            raise FileNotFoundError(path)
        yield path

    @contextlib.contextmanager
    def CreateKey(self, root, path):
        assert root == 'HKCU'
        self.keys.setdefault(path, {})
        yield path

    def QueryValueEx(self, key, name):
        if name not in self.keys[key]:
            raise FileNotFoundError(name)
        return self.keys[key][name], self.REG_SZ

    def SetValueEx(self, key, name, reserved, kind, data):
        assert reserved == 0 and kind == self.REG_SZ and isinstance(data, str)
        self.keys[key][name] = data
        self.written += 1


def test_registered_once_and_again_when_the_program_moved():
    registry = Registry()
    first = links.command_line(r'C:\Old\Azimuth.exe')
    assert links.register(first, registry) is True
    # what Windows needs to treat the key as a scheme: the empty value «URL Protocol» and shell\open\command
    assert registry.keys[r'Software\Classes\azimuth']['URL Protocol'] == ''
    assert registry.keys[r'Software\Classes\azimuth\shell\open\command'][''] == r'"C:\Old\Azimuth.exe" "%1"'
    written = registry.written
    assert links.register(first, registry) is False and registry.written == written  # nothing rewritten
    second = links.command_line(r'C:\New\Azimuth.exe')
    assert links.register(second, registry) is True
    assert registry.keys[r'Software\Classes\azimuth\shell\open\command'][''] == second
    del registry.keys[r'Software\Classes\azimuth']['URL Protocol']  # damaged by hand: put back
    assert links.register(second, registry) is True
    assert registry.keys[r'Software\Classes\azimuth']['URL Protocol'] == ''


def test_the_bundle_is_registered_once_for_a_version_and_a_place(tmp_path):
    bundle = tmp_path / 'Azimuth.app'
    (bundle / 'Contents').mkdir(parents=True)
    (bundle / 'Contents' / 'Info.plist').write_text('<plist/>', encoding='utf-8')
    tool = tmp_path / 'lsregister'
    tool.write_text('', encoding='utf-8')
    marker = tmp_path / 'logs' / 'links-registered.txt'
    calls, code = [], [0]

    class Done:
        def __init__(self, returncode):
            self.returncode = returncode

    def run(command, **options):
        calls.append(command)
        return Done(code[0])

    assert links.register_bundle(bundle, marker, '0.131.0', run, tool) is True
    assert calls == [[str(tool), '-f', str(bundle)]]
    assert links.register_bundle(bundle, marker, '0.131.0', run, tool) is False and len(calls) == 1  # not again
    assert links.register_bundle(bundle, marker, '0.131.1', run, tool) is True and len(calls) == 2  # a new version
    moved = tmp_path / 'elsewhere' / 'Azimuth.app'
    (moved / 'Contents').mkdir(parents=True)
    (moved / 'Contents' / 'Info.plist').write_text('<plist/>', encoding='utf-8')
    assert links.register_bundle(moved, marker, '0.131.1', run, tool) is True and calls[-1][-1] == str(moved)
    code[0] = 1  # the system refused: not marked, asked again next time
    assert links.register_bundle(moved, marker, '0.131.2', run, tool) is False and len(calls) == 4
    code[0] = 0
    assert links.register_bundle(moved, marker, '0.131.2', run, tool) is True and len(calls) == 5
    # nothing to register, or nothing to register with
    assert links.register_bundle(tmp_path / 'none.app', marker, '9', run, tool) is False
    assert links.register_bundle(moved, marker, '9', run, tmp_path / 'no-tool') is False
    assert len(calls) == 5

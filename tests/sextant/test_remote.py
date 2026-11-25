"""The server profile of Sextant: checks, the line run on the server, the settings without a password."""

import json

from modules.sextant import remote
from modules.sextant.remote import ServerProfile


class Settings:
    def __init__(self):
        self.data = {}

    def value(self, key, default=None):
        return self.data.get(key, default)

    def setValue(self, key, value):
        self.data[key] = value


def lab():
    return ServerProfile('Кластер', '10.0.0.5', 2222, 'student', '~/azimuth/calculations',
                         'module load run_mpi && orca.sh -i {folder}')


def test_profile_checks():
    assert lab().ready() and lab().address() == 'student@10.0.0.5:2222' and lab().title() == 'Кластер'
    assert not ServerProfile().ready()  # no address, no login
    bad = ServerProfile('', 'my host', 70000, 'ivan petrov', '', 'orca.sh', 'x y')
    problems = bad.validate()
    assert len(problems) == 5  # address, port, login, folder, the intermediate server (no start command needed)
    assert ServerProfile(host='h', user='u', command='').ready()
    assert not ServerProfile(host='h', user='u', setup='module load orca\0').ready()
    again = ServerProfile.from_dict({**lab().to_dict(), 'setup': 'module load orca-6.1.1'})
    assert again.setup == 'module load orca-6.1.1' and ServerProfile.from_dict({'setup': 5}).setup == ''
    assert ServerProfile(host='h', user='u', jump='me@gate.lab.ru:22').ready()
    assert not ServerProfile(host='h', user='u', command='orca.sh -i {folder}\nrm -rf ~').ready()


def test_line_run_on_the_server():
    line = lab().remote_command('h2o-orca-2026-10-25-1')
    assert line == 'cd "$HOME"/azimuth/calculations && module load run_mpi && orca.sh -i h2o-orca-2026-10-25-1'
    odd = ServerProfile(host='h', user='u', folder='/data/my calcs', command='run {folder}')
    assert odd.remote_command("it's") == "cd '/data/my calcs' && run 'it'\"'\"'s'"
    assert ServerProfile(host='h', user='u', folder='~').remote_command('a').startswith('cd "$HOME" && ')


def test_profiles_are_kept_without_a_password():
    settings = Settings()
    remote.save(settings, lab())
    stored = json.loads(settings.data[remote.PROFILES_KEY])
    assert len(stored) == 1 and 'password' not in stored[0] and stored[0]['host'] == '10.0.0.5'
    assert remote.load(settings) == lab() and settings.data[remote.CURRENT_KEY] == 'Кластер'
    home = ServerProfile('Дома', '192.168.1.2', 22, 'me')
    remote.save(settings, home)
    assert [p.title() for p in remote.load_all(settings)] == ['Кластер', 'Дома'] and remote.load(settings) == home
    renamed = ServerProfile('Лаборатория', '10.0.0.5', 2222, 'student')
    remote.save(settings, renamed, old_title='Кластер')  # the loaded profile renamed: replaced, not doubled
    assert [p.title() for p in remote.load_all(settings)] == ['Дома', 'Лаборатория']
    assert [p.title() for p in remote.remove(settings, 'Дома')] == ['Лаборатория'] and remote.load(settings) == renamed
    settings.data[remote.PROFILES_KEY] = '{broken'
    assert remote.load(settings) == ServerProfile()


def test_profile_of_the_first_version_is_taken_over():
    settings = Settings()
    settings.data[remote.PROFILE_KEY] = json.dumps(lab().to_dict())
    assert remote.load(settings) == lab()
    settings.data[remote.PROFILE_KEY] = json.dumps({'host': 5, 'port': 'x', 'unknown': 1})
    loaded = remote.load(settings)
    assert loaded.host == '' and loaded.port == 22


def test_the_lines_of_one_program_are_kept_with_the_profile():
    # «окно для строк окружения для каждой программы отдельно»: the lines of CP2K of the laboratory server («module
    # load cp2k», «source …/toolchain/install/setup») belong to its jobs only. Kept with the profile; an older profile
    # has none; what is not a known program or not a text is dropped
    cp2k = 'module load cp2k\nsource /opt/cp2k/tools/toolchain/install/setup'
    settings = Settings()
    profile = ServerProfile('serv3', '192.0.2.103', 22, 'user', setup='#SBATCH --exclusive', setups={'cp2k': cp2k})
    remote.save(settings, profile)
    loaded = remote.load(settings)
    assert loaded == profile and loaded.setup_of('cp2k') == cp2k and loaded.setup_of('orca') == ''
    assert json.loads(settings.data[remote.PROFILES_KEY])[0]['setups'] == {'cp2k': cp2k}
    assert lab().setups == {} and lab().setup_of('cp2k') == '' and ServerProfile.from_dict(lab().to_dict()) == lab()
    old = {k: v for k, v in lab().to_dict().items() if k != 'setups'}  # a profile saved before
    assert ServerProfile.from_dict(old).setups == {}
    odd = ServerProfile.from_dict({**lab().to_dict(), 'setups': {'cp2k': '  module load cp2k \n', 'gaussian': 'x', 'qe': 5, 'orca': ' '}})
    assert odd.setups == {'cp2k': 'module load cp2k'}
    assert ServerProfile.from_dict({**lab().to_dict(), 'setups': 'text'}).setups == {}
    bad = ServerProfile('s', 'h', 22, 'u', setups={'cp2k': 'a\0b'})
    assert any('недопустимый символ' in p for p in bad.validate())

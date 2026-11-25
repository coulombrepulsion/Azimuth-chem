"""The log of errors and the report for the author (azimuth/crash_report.py) — without Qt."""

import os
import sys
import zipfile

import pytest

from azimuth import crash_report as cr


@pytest.fixture
def logs(tmp_path, monkeypatch):
    monkeypatch.setenv('AZIMUTH_LOG_DIR', str(tmp_path / 'logs'))
    return tmp_path / 'logs'


class Settings:
    """What QSettings gives the report: the keys and their values."""

    def __init__(self, values):
        self.values = dict(values)

    def allKeys(self):
        return list(self.values)

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


def test_errors_are_appended_with_the_time_and_the_version(logs):
    try:
        1 / 0
    except ZeroDivisionError:
        text = cr.format_exception(*sys.exc_info())
    path = cr.record('exception', text)
    cr.record('qt warning', 'QWidget::setLayout: something')
    log = path.read_text(encoding='utf-8')
    assert path == logs / cr.ERRORS and log.count('=== ') == 2
    from azimuth import __version__

    assert f'· {__version__} · exception' in log and 'ZeroDivisionError' in log and 'qt warning' in log


def test_the_log_is_cut_to_its_end(logs, monkeypatch):
    monkeypatch.setattr(cr, 'LOG_LIMIT', 2000)
    for k in range(200):
        cr.record('exception', f'error number {k}')
    log = (logs / cr.ERRORS).read_text(encoding='utf-8')
    assert len(log) < 4200 and 'error number 199' in log and 'error number 0\n' not in log
    assert log.startswith('[... earlier entries cut ...]\n=== ')


def test_the_report_has_the_logs_the_versions_and_no_passwords(logs, tmp_path):
    cr.record('exception', 'Traceback: boom')
    (logs / cr.CRASH).write_text('Fatal Python error: Segmentation fault\n', encoding='utf-8')
    settings = Settings({'remote/serv3/address': '192.0.2.103', 'remote/serv3/password': 'hunter2',
                         'ssh_private_key': '-----BEGIN', 'api_token': 'x', 'csv_style': 'ru'})
    report = cr.make_report(tmp_path / 'report.zip', settings)
    with zipfile.ZipFile(report) as box:
        names = set(box.namelist())
        assert {'errors.log', 'crash.log', 'system.txt', 'settings.txt'} <= names
        text = box.read('settings.txt').decode('utf-8')
        system = box.read('system.txt').decode('utf-8')
    assert 'csv_style = ru' in text and '192.0.2.103' in text
    assert 'hunter2' not in text and 'BEGIN' not in text and 'api_token' not in text
    assert system.startswith('Azimuth ') and 'Python ' in system and 'numpy' in system


def test_a_crash_is_told_once(logs):
    settings = Settings({})
    assert not cr.crashed_before(settings)  # no crash.log
    (logs / cr.CRASH).write_text('Fatal Python error: Segmentation fault\n', encoding='utf-8')
    assert cr.crashed_before(settings)
    cr.mark_crash_seen(settings)
    assert not cr.crashed_before(settings)
    with open(logs / cr.CRASH, 'a', encoding='utf-8') as out:
        out.write('Fatal Python error: Aborted\n')
    assert cr.crashed_before(settings)


def test_the_folder_of_the_logs(monkeypatch, tmp_path):
    monkeypatch.delenv('AZIMUTH_LOG_DIR', raising=False)
    monkeypatch.setenv('QUAIL_LOG_DIR', str(tmp_path / 'old'))  # the variable of gui_launcher still works
    assert cr.log_dir() == tmp_path / 'old' and (tmp_path / 'old').is_dir()
    monkeypatch.delenv('QUAIL_LOG_DIR')
    monkeypatch.setattr(cr.sys, 'platform', 'darwin')
    monkeypatch.setattr(cr.Path, 'home', lambda: tmp_path / 'home')
    assert cr.log_dir() == tmp_path / 'home' / 'Library' / 'Logs' / 'Azimuth'
    assert os.path.isdir(cr.log_dir())


def test_the_letter_to_the_author(logs, tmp_path):
    # the last entry of errors.log goes into the letter; the link mailto stays short enough for Windows
    from urllib.parse import parse_qs, unquote, urlsplit

    assert cr.last_error() == ''
    cr.record('exception', 'Traceback: the first')
    cr.record('exception', 'Traceback:\n' + 'x' * 5000 + '\nValueError: the second')
    last = cr.last_error()
    assert 'the second' in last and 'the first' not in last and len(last) <= cr.MAIL_ERROR + 1
    report = tmp_path / 'azimuth-report.zip'
    url = cr.mail_url(report, last)
    assert len(url) <= cr.MAIL_LIMIT and url.startswith(f'mailto:{cr.AUTHOR}?subject=')
    fields = parse_qs(urlsplit(url).query)
    from azimuth import __version__

    assert __version__ in fields['subject'][0]
    body = fields['body'][0]
    assert str(report) in body and 'ValueError: the second' in body and body.count('Python ') == 1
    assert unquote(url).count('\n') > 5  # lines of the letter, not one line
    # no error — still a letter with the system and the report
    assert 'Последняя ошибка' not in parse_qs(urlsplit(cr.mail_url(report)).query)['body'][0]


def test_the_address_is_that_of_about():
    import re
    from pathlib import Path

    about = (Path(cr.__file__).resolve().parents[1] / 'hub' / 'about.py').read_text(encoding='utf-8')
    assert re.search(r"^EMAIL = '([^']+)'", about, re.M).group(1) == cr.AUTHOR  # hub/about.py imports Qt


def test_the_report_holds_only_the_programs_settings(logs, tmp_path):
    # the global domain of the system is not read, its keys are left out, the home is «~»
    from pathlib import Path

    class Mac(Settings):
        def __init__(self, own, system):
            super().__init__(own)
            self.system, self.fallbacks = dict(system), True

        def fallbacksEnabled(self):
            return self.fallbacks

        def setFallbacksEnabled(self, on):
            self.fallbacks = on

        def allKeys(self):
            return list(self.values) + (list(self.system) if self.fallbacks else [])

    home = str(Path.home())
    settings = Mac({'theme': 'light', 'recent_files': f'["{home}/Downloads/LyS.xyz"]'},
                   {'NSUserDictionaryReplacementItems': 'итд', 'com/apple/TimeZonePref/Last_Selected_City': 'Moscow'})
    rows = dict(cr.safe_settings(settings))
    assert rows == {'recent_files': '["~/Downloads/LyS.xyz"]', 'theme': 'light'} and settings.fallbacks
    rows = dict(cr.safe_settings(Settings({'AppleLanguages': 'ru', 'com/apple/mouse/scaling': '1.5', 'theme': 'dark'})))
    assert rows == {'theme': 'dark'}  # even read with the fallbacks: the keys of the system left out

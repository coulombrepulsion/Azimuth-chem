"""The check of a newer version (azimuth/updates.py).

Oracles: the fields of the answer of the GitHub API «Get the latest release» (docs.github.com/rest/releases: tag_name,
html_url, published_at, draft, prerelease) in an answer written here; the order of versions by their numbers
(0.224.0 after 0.99.9 — not by the text); a check that cannot reach GitHub says nothing.
"""

import io
import json
import urllib.error

import pytest

from azimuth import updates


@pytest.fixture
def app():
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


def answer(**fields):
    data = {'tag_name': 'v0.224.0', 'html_url': 'https://github.com/coulombrepulsion/Azimuth-chem/releases/tag/v0.224.0',
            'published_at': '2026-11-26T10:00:00Z', 'draft': False, 'prerelease': False, **fields}
    body = json.dumps(data).encode('utf-8')
    seen = []

    class Response(io.BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

    def urlopen(request, timeout):
        seen.append((request, timeout))
        return Response(body)

    return urlopen, seen


def test_versions_are_compared_by_their_numbers():
    assert updates.parse('v0.224.0') == (0, 224, 0) and updates.parse('0.99.9') == (0, 99, 9)
    assert updates.newer('0.224.0', '0.99.9') and not updates.newer('0.99.9', '0.224.0')
    assert not updates.newer('0.224.0', '0.224.0')
    assert updates.parse('v1.0') is None and updates.parse('latest') is None and not updates.newer('x', '0.1.0')


def test_the_latest_release_of_github():
    urlopen, seen = answer()
    release = updates.latest(urlopen=urlopen)
    assert release == updates.Release('0.224.0', 'v0.224.0',
                                      'https://github.com/coulombrepulsion/Azimuth-chem/releases/tag/v0.224.0', '2026-11-26')
    request, timeout = seen[0]
    assert request.full_url == updates.LATEST and timeout == 6.0
    assert request.get_header('User-agent', '').startswith('Azimuth/')  # GitHub refuses a request without one


def test_drafts_prereleases_and_odd_answers_are_not_offered():
    for fields in ({'draft': True}, {'prerelease': True}, {'tag_name': 'nightly'}):
        assert updates.latest(urlopen=answer(**fields)[0]) is None
    # a page that is not of GitHub is replaced by the page of the latest release
    release = updates.latest(urlopen=answer(html_url='http://example.org/')[0])
    assert release.url == 'https://github.com/coulombrepulsion/Azimuth-chem/releases/latest'


@pytest.mark.parametrize('error', [urllib.error.URLError('offline'), TimeoutError(), ValueError('broken')])
def test_a_check_that_fails_says_nothing(error):
    def urlopen(request, timeout):
        raise error

    assert updates.latest(urlopen=urlopen) is None


def test_what_is_offered_and_what_is_remembered():
    release = updates.Release('0.224.0', 'v0.224.0', 'https://github.com/x')
    assert updates.should_offer(release, '0.223.0') and not updates.should_offer(release, '0.224.0')
    assert not updates.should_offer(release, '0.223.0', skipped='0.224.0')  # «Не напоминать об этой версии»
    assert updates.should_offer(updates.Release('0.225.0', 'v0.225.0', ''), '0.223.0', skipped='0.224.0')
    assert not updates.should_offer(None, '0.223.0')

    class Store(dict):
        def value(self, key, default=None):
            return self.get(key, default)

        def setValue(self, key, value):  # noqa: N802 — the name of QSettings
            self[key] = value

    store = Store()
    assert updates.enabled(store)  # on by default
    updates.set_enabled(store, False)
    assert not updates.enabled(store)
    store[updates.CHECK_KEY] = 'false'  # as an INI file gives it back
    assert not updates.enabled(store)
    updates.skip(store, '0.224.0')
    assert updates.skipped(store) == '0.224.0'


def test_the_message_and_the_download_page():
    release = updates.Release('0.224.0', 'v0.224.0', '')
    text = updates.message(release, '0.222.50')
    assert '0.224.0' in text and '0.222.50' in text and 'Скачать' in text
    assert 'git pull' in updates.message(release, '0.222.50', source=True)
    assert updates.download_page('en') == 'https://www.azimuth-chem.com/?lang=en#download'
    assert updates.download_page('ru').startswith('https://ru.azimuth-chem.com/') and updates.download_page('ru').endswith('#download')


def test_the_offer_opens_the_site_or_remembers_the_skip(app, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    release = updates.Release('0.224.0', 'v0.224.0', 'https://github.com/notes')
    monkeypatch.setattr(updates, 'from_source', lambda: False)
    opened = []

    def choose(label):
        def run(box):
            for b in box.buttons():
                if b.text() == label:
                    b.click()
                    return 0
            raise AssertionError(label)
        return run

    for label, expected, url in (('Скачать', 'download', updates.download_page('ru')),
                                 ('Что нового', 'notes', 'https://github.com/notes'), ('Позже', 'later', None)):
        monkeypatch.setattr(QMessageBox, 'exec', choose(label))
        assert updates.offer(None, release, open_url=opened.append) == expected
        assert (opened.pop() if url else None) == url
    store = {}

    class Store:
        def setValue(self, key, value):  # noqa: N802
            store[key] = value

    monkeypatch.setattr(QMessageBox, 'exec', choose('Не напоминать об этой версии'))
    assert updates.offer(None, release, settings=Store(), open_url=opened.append) == 'skip'
    assert store == {updates.SKIP_KEY: '0.224.0'} and opened == []


def test_the_background_check_reports_in_the_window_thread(app):
    from PySide6.QtCore import QCoreApplication, QElapsedTimer

    got = []
    checker = updates.Checker(None, fetch=lambda: updates.Release('9.0.0', 'v9.0.0', ''))
    checker.found.connect(got.append)
    checker.start()
    clock = QElapsedTimer()
    clock.start()
    while not got and clock.elapsed() < 5000:
        QCoreApplication.processEvents()
    assert got and got[0].version == '9.0.0'

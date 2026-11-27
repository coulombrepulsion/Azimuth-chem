"""Is there a newer version of Azimuth: the latest release of GitHub against the running one.

§1 PURPOSE
    The installers of the site are those of the latest release of github.com/coulombrepulsion/Azimuth-chem (the
    buttons of «Скачать» point to releases/latest/download/…), so the version of the site is the tag of that release.
    At the start the program asks for it once, in the background, and offers the download when it is newer; «Справка →
    Проверить обновления…» asks at any time and also says that the version is the latest.

§2 ALGORITHM
    latest(timeout, urlopen) -> Release or None: GET LATEST (the GitHub API, JSON, no token needed), its tag_name
    («v0.224.0»), html_url and published_at. Any failure (no network, a proxy, a refusal, a rate limit of GitHub,
    a broken answer) -> None: a check that fails says nothing at the start.
    parse(text) -> (0, 224, 0) or None; newer(remote, local) compares the tuples.
    should_offer(release, current, skipped): newer than the running version and not the one the user chose to skip.
    Settings: CHECK_KEY (bool, on by default — Файл → Настройки → «Оформление»), SKIP_KEY (the version «Не напоминать»).
    from_source(): the program runs from a git checkout — the offer says «git pull» instead of the installer.

§3 APPLICATIONS
    hub/launch.py (check_later after the window shows), hub/menus.py («Проверить обновления…»),
    azimuth/settings_dialog.py (the switch).

§4 SPECIFICATION
    Release(version: str «0.224.0», tag, url — the page of the release, published — ISO date or '').
    latest(timeout=6.0, urlopen=pubchem._urlopen) -> Release | None; parse; newer; should_offer; from_source();
    enabled(settings) / set_enabled(settings, on); skipped(settings) / skip(settings, version);
    Checker(parent) — a QObject: start() runs latest() in a thread, the signal found(object) gives the Release or None
    in the thread of the window; offer(parent, release, manual=False) — the message with «Скачать», «Что нового»,
    «Позже», «Не напоминать об этой версии».

§6 IMPLEMENTATION NOTES
    No personal data is sent: one GET of a public address, the header User-Agent «Azimuth/<version>» (GitHub refuses
    requests without one). The download opens the section «Скачать» of the site in the browser; the program does not
    replace itself.

§7 TESTS
    tests/core/test_updates.py.
"""

from dataclasses import dataclass
import json
import re
import sys
from pathlib import Path

from azimuth.i18n import tr

LATEST = 'https://api.github.com/repos/coulombrepulsion/Azimuth-chem/releases/latest'
CHECK_KEY = 'check_updates'
SKIP_KEY = 'skipped_update'
_VERSION = re.compile(r'^v?(\d+)\.(\d+)\.(\d+)$')


@dataclass(frozen=True)
class Release:
    version: str
    tag: str
    url: str
    published: str = ''


def parse(text):
    """(major, minor, patch) of «0.224.0» or «v0.224.0», or None."""
    m = _VERSION.match(str(text or '').strip())
    return tuple(int(x) for x in m.groups()) if m else None


def newer(remote, local):
    a, b = parse(remote), parse(local)
    return a is not None and b is not None and a > b


def current():
    from azimuth import __version__

    return __version__


def _request(url):
    import urllib.request

    return urllib.request.Request(url, headers={'User-Agent': f'Azimuth/{current()}',
                                                'Accept': 'application/vnd.github+json'})


def _open(request, timeout):
    from modules.compass.chemistry.pubchem import _urlopen

    return _urlopen(request, timeout)


def latest(timeout=6.0, urlopen=_open):
    """The latest release, or None on any failure (§2)."""
    try:
        with urlopen(_request(LATEST), timeout) as response:
            data = json.loads(response.read(200_000).decode('utf-8', 'replace'))
    except Exception:  # no network, a proxy, a refusal, a rate limit, a broken answer: nothing to say
        return None
    if not isinstance(data, dict) or data.get('draft') or data.get('prerelease'):
        return None
    tag = str(data.get('tag_name') or '')
    if parse(tag) is None:
        return None
    url = str(data.get('html_url') or '')
    if not url.startswith('https://github.com/'):
        url = 'https://github.com/coulombrepulsion/Azimuth-chem/releases/latest'
    return Release('.'.join(map(str, parse(tag))), tag, url, str(data.get('published_at') or '')[:10])


def should_offer(release, running, skipped=''):
    return release is not None and newer(release.version, running) and release.version != skipped


def from_source():
    """A git checkout (the owner, a developer), not an installed copy."""
    if getattr(sys, 'frozen', False):
        return False
    return (Path(__file__).resolve().parents[1] / '.git').exists()


def enabled(settings):
    value = settings.value(CHECK_KEY, True)
    return value not in (False, 'false', '0', 0)


def set_enabled(settings, on):
    settings.setValue(CHECK_KEY, bool(on))


def skipped(settings):
    return str(settings.value(SKIP_KEY, '') or '')


def skip(settings, version):
    settings.setValue(SKIP_KEY, version)


def download_page(language='ru'):
    from azimuth import site

    return site.home(language) + f'?lang={language}#download'


def _make_checker():
    from PySide6.QtCore import QObject, Signal

    class Checker(QObject):
        """latest() in a thread; found(Release | None) arrives in the thread of the window."""

        found = Signal(object)

        def __init__(self, parent=None, fetch=latest):
            super().__init__(parent)
            self.fetch = fetch

        def start(self):
            import threading

            threading.Thread(target=lambda: self.found.emit(self.fetch()), name='azimuth-updates', daemon=True).start()

    return Checker


_CHECKER = []


def Checker(parent=None, fetch=latest):  # noqa: N802 — a class made on first use (Qt imported only then)
    if not _CHECKER:
        _CHECKER.append(_make_checker())
    return _CHECKER[0](parent, fetch)


def message(release, running, source=False):
    """The text of the offer (Russian, the key of tr; the numbers outside)."""
    text = tr('Вышла новая версия «Азимута»: {}. У вас {}.').format(release.version, running)
    if source:
        return text + '\n\n' + tr('Программа запущена из папки с исходным кодом: обновите её командой git pull.')
    return text + '\n\n' + tr('Установщик — на сайте, в разделе «Скачать». Ваши настройки, проекты и расчёты '
                              'останутся на месте.')


def offer(parent, release, language='ru', manual=False, settings=None, open_url=None):
    """The message of a newer release; returns what was chosen: 'download', 'notes', 'later' or 'skip'."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices
    from PySide6.QtWidgets import QMessageBox

    source = from_source()
    from azimuth import quill

    box = QMessageBox(parent)
    quill.set_icon(box, 'update', QMessageBox.Icon.Information)  # the picture of the state, as the other dialogs
    box.setWindowTitle(tr('Обновление'))
    box.setText(message(release, current(), source))
    download = None if source else box.addButton(tr('Скачать'), QMessageBox.ButtonRole.AcceptRole)
    notes = box.addButton(tr('Что нового'), QMessageBox.ButtonRole.HelpRole)
    later = box.addButton(tr('Позже'), QMessageBox.ButtonRole.RejectRole)
    never = None if manual else box.addButton(tr('Не напоминать об этой версии'), QMessageBox.ButtonRole.DestructiveRole)
    box.setDefaultButton(download or later)
    box.exec()
    chosen = box.clickedButton()
    go = open_url or (lambda url: QDesktopServices.openUrl(QUrl(url)))
    if download is not None and chosen is download:
        go(download_page(language))
        return 'download'
    if chosen is notes:
        go(release.url)
        return 'notes'
    if never is not None and chosen is never:
        if settings is not None:
            skip(settings, release.version)
        return 'skip'
    return 'later'


def check_later(window, language='ru', delay_ms=4000):
    """At the start: in the background, after the window shows; nothing is said unless a newer version is out."""
    from PySide6.QtCore import QTimer

    from azimuth.settings import open_settings

    settings = open_settings()
    if not enabled(settings):
        return None
    checker = Checker(window)

    def found(release):
        if should_offer(release, current(), skipped(settings)):
            offer(window, release, getattr(window, 'language', language), settings=settings)

    checker.found.connect(found)
    window.update_checker = checker  # kept alive
    QTimer.singleShot(delay_ms, checker.start)
    return checker


def check_now(window, language='ru', fetch=latest):
    """«Справка → Проверить обновления…»: the answer in any case."""
    from azimuth import quill

    release = fetch()
    language = getattr(window, 'language', language)
    if release is None:
        quill.information(window, tr('Обновление'), tr('Не удалось узнать последнюю версию: нет связи с GitHub. '
                                                       'Попробуйте позже или загляните на сайт.'), 'offline')
        return None
    if newer(release.version, current()):
        return offer(window, release, language, manual=True)
    quill.information(window, tr('Обновление'), tr('У вас последняя версия «Азимута»: {}.').format(current()), 'update')
    return 'latest'

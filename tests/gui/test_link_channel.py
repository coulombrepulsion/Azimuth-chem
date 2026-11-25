"""The way of a link to the running program (azimuth/link_channel.py). The oracle: the text the handler
of a listener receives, against the text sent; every test has a socket name of its own."""

import os
import subprocess
import sys
import time
import uuid

import pytest
from PySide6.QtCore import QCoreApplication, QEvent, QUrl
from PySide6.QtGui import QFileOpenEvent
from PySide6.QtNetwork import QLocalSocket
from PySide6.QtWidgets import QApplication

from azimuth import link_channel


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def name():
    return f'azimuth-test-{os.getpid()}-{uuid.uuid4().hex[:8]}'


def pump(app, condition, seconds=5):
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        app.processEvents()
        if condition():
            return True
        time.sleep(0.01)
    return False


def send(app, address, name):
    """link_channel.send, as from another copy of the program. On Windows a line written into the pipe of QLocalServer
    is taken only when the listener reads it in its event loop, and a sender in the same process (or in a thread of
    it, without an event loop of its own) waits in vain — so there the line is sent by another process, as a new copy
    of the program does, while this one runs the events (checked on Windows 2026-11-25: twice in a row, both arrive)."""
    if sys.platform != 'win32':
        return link_channel.send(address, name)
    code = ('import sys; sys.path.insert(0, sys.argv[3]); from PySide6.QtCore import QCoreApplication; '
            'app = QCoreApplication([]); from azimuth import link_channel; '
            'print(link_channel.send(sys.argv[1], sys.argv[2]))')
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    child = subprocess.Popen([sys.executable, '-c', code, address, name, root], stdout=subprocess.PIPE, text=True)
    while child.poll() is None:
        app.processEvents()
        time.sleep(0.005)
    return child.stdout.read().strip() == 'True'


def closed(listener, app):
    app.removeEventFilter(listener)
    listener.server.close()


def test_nothing_is_sent_when_nobody_listens(app, name):
    assert link_channel.send('azimuth://compass/water', name) is False


def test_an_address_sent_arrives(app, name):
    got = []
    listener = link_channel.Listener(app, got.append, name)
    try:
        assert listener.listening
        assert send(app, 'azimuth://compass/water', name) is True
        assert pump(app, lambda: got) and got == ['azimuth://compass/water']
        assert send(app, '  azimuth://compass/benzene  ', name) is True
        assert pump(app, lambda: len(got) == 2) and got[1] == 'azimuth://compass/benzene'
    finally:
        closed(listener, app)


def test_the_first_listener_keeps_its_place(app, name):
    first, second = [], []
    one = link_channel.Listener(app, first.append, name)
    two = link_channel.Listener(app, second.append, name)
    try:
        assert one.listening and not two.listening
        assert send(app, 'azimuth://compass/hf', name) is True
        assert pump(app, lambda: first) and first == ['azimuth://compass/hf'] and second == []
    finally:
        closed(two, app)
        closed(one, app)


def test_a_long_line_is_cut_and_the_next_one_still_read(app, name):
    got = []
    listener = link_channel.Listener(app, got.append, name)
    try:
        socket = QLocalSocket()
        socket.connectToServer(name)
        assert socket.waitForConnected(2000)
        socket.write(b'x' * 5000 + b'\nazimuth://compass/n2\n')
        socket.waitForBytesWritten(2000)
        assert pump(app, lambda: len(got) == 2)
        assert 0 < len(got[0]) <= link_channel.LIMIT and set(got[0]) == {'x'}
        assert got[1] == 'azimuth://compass/n2'
        socket.disconnectFromServer()
    finally:
        closed(listener, app)


def test_the_event_of_macos_goes_to_the_handler(app, name):
    got = []
    listener = link_channel.Listener(app, got.append, name)
    try:
        try:
            event = QFileOpenEvent(QUrl('azimuth://compass/water'))
        except TypeError:  # a version of Qt that keeps the making of this event to itself
            pytest.skip('QFileOpenEvent cannot be made here')
        QCoreApplication.sendEvent(app, event)
        assert got == ['azimuth://compass/water']
        QCoreApplication.sendEvent(app, QFileOpenEvent(QUrl('file:///tmp/a.xyz')))  # not ours: left to the others
        assert got == ['azimuth://compass/water']
        assert listener.eventFilter(app, QEvent(QEvent.Type.Timer)) is False
    finally:
        closed(listener, app)


def test_a_file_opened_in_finder_goes_to_the_file_handler(app, name, tmp_path):
    # an event FileOpen with
    # a file of this computer goes to file_handler, a link still to the handler of the links
    links, files = [], []
    listener = link_channel.Listener(app, links.append, name, file_handler=files.append)
    project = tmp_path / 'hexane.qcc'
    project.write_text('{}', encoding='utf-8')
    try:
        try:
            event = QFileOpenEvent(QUrl.fromLocalFile(str(project)))
        except TypeError:
            pytest.skip('QFileOpenEvent cannot be made here')
        QCoreApplication.sendEvent(app, event)
        assert files == [str(project)] and links == []
        QCoreApplication.sendEvent(app, QFileOpenEvent(QUrl('azimuth://compass/water')))
        assert links == ['azimuth://compass/water'] and len(files) == 1
    finally:
        closed(listener, app)


def test_the_application_declares_its_documents():
    # Azimuth.app owns .qcc (its own type) and is offered for the files of structures and results
    import plistlib
    from pathlib import Path

    info = plistlib.loads((Path(__file__).resolve().parents[2] / 'Azimuth.app' / 'Contents' / 'Info.plist').read_bytes())
    types = {t['CFBundleTypeName']: t for t in info['CFBundleDocumentTypes']}
    assert types['Azimuth project']['CFBundleTypeExtensions'] == ['qcc']
    assert types['Azimuth project']['LSHandlerRank'] == 'Owner'
    assert {'cif', 'xyz', 'out'} <= set(types['Chemical structure or calculation']['CFBundleTypeExtensions'])
    exported = info['UTExportedTypeDeclarations'][0]
    assert exported['UTTypeTagSpecification']['public.filename-extension'] == ['qcc']

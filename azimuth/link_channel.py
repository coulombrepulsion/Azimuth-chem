"""The way of an azimuth:// link to the running program; the addresses themselves — azimuth/links.py.

§1 PURPOSE
    Windows starts a new copy of the program for every link opened. When the program already runs, the new copy
    hands the address to it and ends; macOS gives the address to the running program itself, as an event.
§2 RULES
    1. One local socket of the user (QLocalServer, name NAME + the name of the user): the copy that listens first
       receives the addresses. A copy started without a link listens when nobody does and otherwise simply works —
       several windows of the program stay possible as before.
    2. send(address) — connect (WAIT_MS), write the address in UTF-8 and a line feed, wait until it is written;
       True when it was handed over. A listener first asks whether somebody answers on the socket: if so it does not
       listen; if not — a socket left by a program that crashed refuses the connection — it removes what is left
       and takes the place.
    3. A line received is passed to the handler as text, at most LIMIT bytes; the rest of a longer one is dropped.
       The handler checks it (links.parse) — the channel carries text and trusts nothing.
    4. macOS: an event QEvent.FileOpen with an address of the scheme goes to the same handler; one with a file of this
       computer goes to file_handler (the types of documents of Azimuth.app/Contents/Info.plist).
    5. Windows: before sending, the new copy lets the running one come to the front
       (AllowSetForegroundWindow) — a window may not raise itself there otherwise.
§3 INTERFACE
    send(address) -> bool; Listener(app, handler, name=None, file_handler=None) — .listening: bool.
§4 TESTS
    tests/gui/test_link_channel.py — an address sent arrives at the handler of a listener of the same process, a
    second listener does not take the place of the first, nothing is sent when nobody listens, a long line is cut."""

import getpass
import sys
from pathlib import Path

from PySide6.QtCore import QEvent, QObject
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from azimuth import links

NAME = 'azimuth-links-'
WAIT_MS = 700
LIMIT = 400


def _name():
    try:
        user = getpass.getuser()
    except Exception:  # no name of the user in the environment
        user = 'user'
    return NAME + ''.join(c if c.isalnum() else '_' for c in user)


def send(address, name=None):
    socket = QLocalSocket()
    socket.connectToServer(name or _name())
    if not socket.waitForConnected(WAIT_MS):
        return False
    if sys.platform == 'win32':  # §2.5
        try:
            import ctypes

            ctypes.windll.user32.AllowSetForegroundWindow(-1)
        except Exception:
            pass
    socket.write((str(address).strip() + '\n').encode('utf-8'))
    socket.flush()
    # waitForBytesWritten answers False when nothing is left to write: a line already taken counts as handed over
    done = socket.bytesToWrite() == 0 or socket.waitForBytesWritten(WAIT_MS)
    socket.disconnectFromServer()
    return bool(done)


class Listener(QObject):
    def __init__(self, app, handler, name=None, file_handler=None):
        super().__init__(app)
        self.handler = handler
        self.file_handler = file_handler
        self.name = name or _name()
        self.server = QLocalServer(self)
        self.server.setSocketOptions(QLocalServer.SocketOption.UserAccessOption)
        self.server.newConnection.connect(self._connected)
        # the question «does somebody listen» comes first: with the access option set Qt on macOS and Linux puts a
        # new socket over the old one without a word, and listen() of a second copy took the place of the first
        self.listening = False
        if not self._alive():
            QLocalServer.removeServer(self.name)  # §2.2: left by a program that crashed, if anything is left
            self.listening = self.server.listen(self.name)
        app.installEventFilter(self)

    def _alive(self):
        probe = QLocalSocket()
        probe.connectToServer(self.name)
        alive = probe.waitForConnected(WAIT_MS)
        probe.abort()
        return alive

    def _connected(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.setReadBufferSize(64 * 1024)  # a line without an end is not gathered without a bound
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(socket.deleteLater)
            if socket.bytesAvailable():
                self._read(socket)

    def _read(self, socket):
        while socket.canReadLine():
            line = bytes(socket.readLine(LIMIT + 1).data())
            if not line.endswith(b'\n'):  # longer than LIMIT: the rest of it is dropped
                while socket.bytesAvailable() and not bytes(socket.readLine(LIMIT + 1).data()).endswith(b'\n'):
                    pass
                line = line[:LIMIT]
            text = line.decode('utf-8', 'replace').strip()
            if text:
                self.handler(text)

    def eventFilter(self, watched, event):  # §2.4
        if event.type() == QEvent.Type.FileOpen:
            address = event.url().toString()
            if links.link_in([address]) is not None:
                self.handler(address)
                return True
            path = event.file() or (event.url().toLocalFile() if event.url().isLocalFile() else '')
            if path and self.file_handler is not None:  # §2.4: a document opened from Finder
                self.file_handler(str(Path(path)))  # Qt gives «C:/…» on Windows: the separators of the system
                return True
        return False

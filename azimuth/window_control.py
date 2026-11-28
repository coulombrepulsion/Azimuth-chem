"""The open window of Azimuth answers a language model on this computer: a structure shown, atoms chosen, a picture.

§1 PURPOSE
    The structures built without the window (azimuth/headless_structure.py) were files that the user opened by hand.
    With the window open the model shows what it built there (ROADMAP 26(б), the owner 2026-11-27: «чтобы пользователь
    видел, что строится»): tools/azimuth_mcp.py asks the window through this channel.
§2 RULES — the window is the user's, so the channel is narrow:
    1. Only this computer and only this user: a TCP socket on 127.0.0.1 (a port the system gives) and a token of
       TOKEN_BYTES random bytes, both written to STATE (the file of the user, mode 600); a request without the token
       is answered with an error and nothing is done.
    2. A request is one line of JSON {"token", "op", …}, at most LIMIT bytes; the answer is one line of JSON.
    3. What can be asked (OPS), nothing else — no command, no setting, no file written but a picture:
       state — the section shown, the tab, the formula and the atoms of the structure in Compass;
       show {path} — a structure, a crystal or a project of this computer opened in Compass as by «Файл → Открыть…»
       (SHOWN — the kinds of files; not a result of a calculation, not anything else);
       select {atoms: [1-based numbers]} — the atoms chosen on the model of Compass (an empty list — none);
       snapshot — the window as a PNG in PICTURES (a folder of the user's temporary files), its path answered.
    4. The file STATE goes when the window closes (stop); a file left by a window that crashed names a port nobody
       answers — the client says the window is not open.
§3 INTERFACE
    state_file() -> Path; Control(window) — .start() -> bool (listening), .stop(); handle(window, request) -> dict
    (the requests without the socket — the tests); azimuth/window_client.py — the side of the model, without Qt.
§7 TESTS tests/hub/test_window_control.py.
"""

import hmac
import json
import os
import secrets
import sys
import tempfile
import time
from pathlib import Path

TOKEN_BYTES = 24
LIMIT = 16_384
OPS = ('state', 'show', 'select', 'snapshot')
SHOWN = ('.xyz', '.mol', '.sdf', '.mol2', '.pdb', '.cif', '.cml', '.cdxml', '.qcc', '.gjf', '.com', '.inp', '.zmat')
PICTURES = Path(tempfile.gettempdir()) / 'azimuth-window'


def state_file():
    """Where the port and the token of the open window are written (the folder of the user's own data)."""
    given = os.environ.get('AZIMUTH_CONTROL_FILE')
    if given:
        return Path(given)
    if sys.platform == 'darwin':
        base = Path.home() / 'Library' / 'Application Support' / 'Azimuth'
    elif os.name == 'nt':
        base = Path(os.environ.get('APPDATA') or Path.home()) / 'Azimuth'
    else:
        base = Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local' / 'state') / 'azimuth'
    return base / 'window.json'


def _studio(window):
    return getattr(window, 'studio', window)


def _state(window):
    studio = _studio(window)
    molecule = studio.own_molecule() if hasattr(studio, 'own_molecule') else None
    atoms = list(molecule.atoms) if molecule is not None else []
    viewer = getattr(studio, 'viewer', None)
    return {'section': getattr(window, 'current', None), 'mode': getattr(studio, 'compass_mode', 'molecule'),
            'title': window.windowTitle(), 'formula': getattr(molecule, 'formula', '') if atoms else '',
            'atoms': [{'n': k + 1, 'element': a.symbol, 'xyz': [round(a.x, 4), round(a.y, 4), round(a.z, 4)]}
                      for k, a in enumerate(atoms[:500])],
            'selected': [i + 1 for i in getattr(viewer, 'selected', [])]}


def handle(window, request):
    """The answer to one request already read (the token checked by the caller)."""
    op = request.get('op')
    if op not in OPS:
        raise ValueError(f'unknown op {op!r}; there are: {", ".join(OPS)}')
    if op == 'state':
        return _state(window)
    if op == 'show':
        path = Path(str(request.get('path') or '')).expanduser()
        if path.suffix.lower() not in SHOWN:
            raise ValueError(f'only a structure, a crystal or a project is shown ({", ".join(SHOWN)}), not {path.name!r}')
        if not path.is_file():
            raise ValueError(f'no such file: {path}')
        if window.open_file(str(path)) is None:
            raise ValueError(f'not opened: {path}')
        return _state(window)
    if op == 'select':
        studio = _studio(window)
        viewer = getattr(studio, 'viewer', None)
        molecule = getattr(viewer, 'molecule', None)
        count = len(molecule.atoms) if molecule is not None else 0
        atoms = request.get('atoms') or []
        if not isinstance(atoms, list) or not all(isinstance(n, int) and 1 <= n <= count for n in atoms):
            raise ValueError(f'atoms are numbers from 1 to {count}')
        viewer.set_selection([n - 1 for n in atoms])
        return _state(window)
    # snapshot
    PICTURES.mkdir(parents=True, exist_ok=True)
    path = PICTURES / time.strftime('window-%Y%m%d-%H%M%S.png')
    if not window.grab().save(str(path)):
        raise ValueError('the picture of the window was not written')
    return {'path': str(path), 'width': window.width(), 'height': window.height()}


class Control:
    """The listening side, in the window (hub/launch.py starts it)."""

    def __init__(self, window, path=None):
        from PySide6.QtNetwork import QHostAddress, QTcpServer

        self.window = window
        self.path = Path(path) if path else state_file()
        self.token = secrets.token_hex(TOKEN_BYTES)
        self.server = QTcpServer(window)
        self._host = QHostAddress.SpecialAddress.LocalHost
        self.server.newConnection.connect(self._connected)

    def start(self):
        if not self.server.listen(self._host, 0):
            return False
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = json.dumps({'port': self.server.serverPort(), 'token': self.token, 'pid': os.getpid()})
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as out:
            out.write(data)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        return True

    def stop(self):
        self.server.close()
        try:
            known = json.loads(self.path.read_text(encoding='utf-8'))
            if known.get('token') == self.token:  # not the file of another window started since
                self.path.unlink()
        except (OSError, ValueError):
            pass

    def _connected(self):
        while self.server.hasPendingConnections():
            socket = self.server.nextPendingConnection()
            socket.setProperty('buffer', b'')
            socket.readyRead.connect(lambda s=socket: self._read(s))
            socket.disconnected.connect(socket.deleteLater)

    def _read(self, socket):
        data = bytes(socket.property('buffer') or b'') + bytes(socket.readAll())
        if b'\n' not in data:
            if len(data) > LIMIT:
                self._answer(socket, {'error': 'the request is too long'})
            else:
                socket.setProperty('buffer', data)
            return
        line = data.split(b'\n', 1)[0]
        try:
            request = json.loads(line.decode('utf-8'))
            if not isinstance(request, dict) or not hmac.compare_digest(str(request.get('token', '')), self.token):
                raise PermissionError('a request without the token of this window')
            answer = {'ok': True, 'answer': handle(self.window, request)}
        except PermissionError as exc:
            answer = {'error': str(exc)}
        except (ValueError, KeyError, TypeError, AttributeError, OSError) as exc:
            answer = {'error': f'{type(exc).__name__}: {exc}'}
        self._answer(socket, answer)

    @staticmethod
    def _answer(socket, answer):
        socket.write((json.dumps(answer, ensure_ascii=False) + '\n').encode('utf-8'))
        socket.flush()
        socket.disconnectFromHost()

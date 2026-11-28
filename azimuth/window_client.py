"""The side of a language model of the channel to the open window of Azimuth (azimuth/window_control.py): no Qt.

§1 PURPOSE tools/azimuth_mcp.py — azimuth_window_state, azimuth_window_show, azimuth_window_select,
    azimuth_window_snapshot — asks the window the user has open (ROADMAP 26(б)).
§2 RULES The port and the token are read from window_control.state_file(); one request, one answer, TIMEOUT seconds;
    no file or a port nobody answers — «the window of Azimuth is not open»; an error of the window — ValueError with
    its words.
§3 INTERFACE ask(op, state=None, timeout=TIMEOUT, **fields) -> dict (state — the file of the window, the tests).
§7 TESTS tests/hub/test_window_control.py.
"""

import json
import socket

TIMEOUT = 20.0


def ask(op, state=None, timeout=TIMEOUT, **fields):
    from azimuth.window_control import LIMIT, state_file

    where = state or state_file()  # the file of the window; path — a field of «show»
    try:
        known = json.loads(where.read_text(encoding='utf-8'))
        port, token = int(known['port']), str(known['token'])
    except (OSError, ValueError, KeyError, TypeError):
        raise ValueError('the window of Azimuth is not open (start the program; the window answers this computer '
                         'only)') from None
    request = dict(fields, op=op, token=token)
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=timeout) as link:
            link.sendall((json.dumps(request, ensure_ascii=False) + '\n').encode('utf-8'))
            data = b''
            while b'\n' not in data and len(data) < 64 * LIMIT:
                part = link.recv(65536)
                if not part:
                    break
                data += part
    except OSError:
        raise ValueError('the window of Azimuth is not open (no answer on its port)') from None
    try:
        answer = json.loads(data.split(b'\n', 1)[0].decode('utf-8'))
    except ValueError:
        raise ValueError('the window of Azimuth gave no answer') from None
    if 'error' in answer:
        raise ValueError(answer['error'])
    return answer['answer']

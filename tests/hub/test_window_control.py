"""azimuth/window_control.py and azimuth/window_client.py — the open window answers a language model of this computer
(ROADMAP 26(б)): a request without the token does nothing, a structure is shown, atoms chosen, a picture written."""

import threading
from pathlib import Path

import pytest
from PySide6.QtTest import QTest

from azimuth import window_client, window_control
from tests.hub.test_hub import app, hub  # noqa: F401

ROOT = Path(__file__).resolve().parents[2]


def asked(app, op, state, **fields):
    """The client in a thread (it waits on its socket), the window's loop here."""
    box = {}

    def run():
        try:
            box['answer'] = window_client.ask(op, state=state, timeout=10, **fields)
        except ValueError as exc:
            box['error'] = str(exc)

    thread = threading.Thread(target=run)
    thread.start()
    while thread.is_alive():
        app.processEvents()
        QTest.qWait(10)
    thread.join()
    if 'error' in box:
        raise ValueError(box['error'])
    return box['answer']


def test_the_window_answers_this_computer_with_its_token(hub, app, tmp_path):
    state = tmp_path / 'window.json'
    with pytest.raises(ValueError, match='not open'):
        window_client.ask('state', state=state)
    control = window_control.Control(hub, state)
    assert control.start() and state.is_file() and oct(state.stat().st_mode & 0o777) == '0o600'
    hub.resize(1200, 760)
    hub.show()
    try:
        water = ROOT / 'tests' / 'data' / 'water.xyz'
        if not water.is_file():
            water = tmp_path / 'water.xyz'
            water.write_text('3\nwater\nO 0 0 0.1173\nH 0 0.7572 -0.4692\nH 0 -0.7572 -0.4692\n', encoding='utf-8')
        shown = asked(app, 'show', state, path=str(water))
        assert shown['section'] == 'compass' and shown['formula'] == 'H2O' and len(shown['atoms']) == 3
        chosen = asked(app, 'select', state, atoms=[1, 3])
        assert chosen['selected'] == [1, 3] and hub.studio.viewer.selected == [0, 2]
        with pytest.raises(ValueError, match='from 1 to 3'):
            asked(app, 'select', state, atoms=[4])
        picture = asked(app, 'snapshot', state)
        assert Path(picture['path']).is_file() and Path(picture['path']).read_bytes()[:4] == b'\x89PNG'
        # only a structure is opened, and only what is asked
        script = tmp_path / 'x.sh'
        script.write_text('echo\n')
        with pytest.raises(ValueError, match='only a structure'):
            asked(app, 'show', state, path=str(script))
        with pytest.raises(ValueError, match='unknown op'):
            asked(app, 'settings', state)
        # a request with another token does nothing
        import json

        known = json.loads(state.read_text())
        state.write_text(json.dumps(dict(known, token='0' * 48)))
        with pytest.raises(ValueError, match='without the token'):
            asked(app, 'select', state, atoms=[])
        assert hub.studio.viewer.selected == [0, 2]
        state.write_text(json.dumps(known))
    finally:
        control.stop()
    assert not state.exists()

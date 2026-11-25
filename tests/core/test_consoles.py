"""No console windows on Windows for the programs Azimuth starts (azimuth/consoles.py)."""

import subprocess
import sys
import types

import pytest

from azimuth import consoles


def fake_module():
    started = []

    class Popen:
        def __init__(self, *args, **kwargs):
            started.append(kwargs)

    class STARTUPINFO:
        def __init__(self):
            self.dwFlags, self.wShowWindow = 0, 1

    return types.SimpleNamespace(Popen=Popen, STARTUPINFO=STARTUPINFO, STARTF_USESHOWWINDOW=1), started


def test_children_get_no_window_unless_they_ask_for_a_console():
    module, started = fake_module()
    assert not consoles.install(module, windows=False) and not getattr(module.Popen, 'azimuth_hidden', False)
    assert consoles.install(module, windows=True) and module.Popen.azimuth_hidden
    first = module.Popen
    assert consoles.install(module, windows=True) and module.Popen is first  # once
    module.Popen(['orca', 'input.inp'])
    module.Popen(['ssh-copy-id', 'me@server'], creationflags=consoles.CREATE_NEW_CONSOLE)  # the user types there
    module.Popen(['orca'], creationflags=0x200)  # CREATE_NEW_PROCESS_GROUP of a job kept
    module.Popen(['x'], creationflags=consoles.DETACHED_PROCESS)
    flags = [kwargs['creationflags'] for kwargs in started]
    assert flags == [consoles.CREATE_NO_WINDOW, consoles.CREATE_NEW_CONSOLE, 0x200 | consoles.CREATE_NO_WINDOW,
                     consoles.DETACHED_PROCESS]
    # a window of its own (Multiwfn's graphical build) starts hidden; the console asked for stays as it is
    assert started[0]['startupinfo'].wShowWindow == 0 and started[0]['startupinfo'].dwFlags & 1
    assert 'startupinfo' not in started[1]


@pytest.mark.skipif(sys.platform != 'win32', reason='CREATE_NO_WINDOW is a flag of Windows')
def test_a_console_program_prints_through_the_hidden_popen(monkeypatch):
    monkeypatch.setattr(subprocess, 'Popen', subprocess.Popen)  # the original back after the test
    assert consoles.install() and subprocess.Popen.azimuth_hidden
    done = subprocess.run([sys.executable, '-c', 'print(42)'], capture_output=True, text=True)
    assert done.returncode == 0 and done.stdout.strip() == '42'  # the output still comes, no window is shown

"""No console windows on Windows for the programs Azimuth starts.

§1 PURPOSE
    The program is started without a console on Windows (Launch-Windows.bat runs pythonw.exe), so every console program
    it starts — ORCA and its parts (orca_2mkl, mpiexec), xtb, Multiwfn, ssh, the queries of OpenVPN Connect, the checks
    of the installed programs — got a black console window of its own: a row of small windows flashing at the start of
    the program, the window of ORCA over everything during a calculation.
§2 ALGORITHM
    install() replaces subprocess.Popen — which subprocess.run, check_output and call use — by a subclass that adds
    CREATE_NO_WINDOW to the flags of a child unless it asked for a console of its own (CREATE_NEW_CONSOLE — the window
    where the user types the password of a server, server_access) or for none (DETACHED_PROCESS). A console program
    started so has a console that is never shown; its own children (the processes of mpiexec, the parts of ORCA)
    share it and show nothing either. And, unless given, STARTUPINFO with SW_HIDE: a program of the window subsystem
    that makes its console itself (the build of Multiwfn for Windows has a graphical part) or opens a window starts
    with it hidden. The output still goes to the pipes and files given. Nothing on macOS and Linux.
§4 SPECIFICATION
    install(module=subprocess, windows=None) -> bool (True when installed; again — nothing more); hidden(flags) -> int.
§7 TESTS tests/core/test_consoles.py.
"""

import os
import subprocess

CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_CONSOLE = 0x00000010
DETACHED_PROCESS = 0x00000008


def hidden(flags):
    """The creation flags of a child with CREATE_NO_WINDOW, unless it asked for a console of its own or for none."""
    flags = int(flags or 0)
    if flags & (CREATE_NEW_CONSOLE | DETACHED_PROCESS):
        return flags
    return flags | CREATE_NO_WINDOW


def install(module=subprocess, windows=None):
    windows = os.name == 'nt' if windows is None else windows
    if not windows:
        return False
    base = module.Popen
    if getattr(base, 'azimuth_hidden', False):
        return True

    class HiddenPopen(base):
        azimuth_hidden = True

        def __init__(self, *args, **kwargs):
            flags = hidden(kwargs.get('creationflags', 0))
            kwargs['creationflags'] = flags
            info = getattr(module, 'STARTUPINFO', None)
            if info is not None and kwargs.get('startupinfo') is None and not flags & CREATE_NEW_CONSOLE:
                startup = info()
                startup.dwFlags |= getattr(module, 'STARTF_USESHOWWINDOW', 1)
                startup.wShowWindow = 0  # SW_HIDE
                kwargs['startupinfo'] = startup
            super().__init__(*args, **kwargs)

    module.Popen = HiddenPopen
    return True

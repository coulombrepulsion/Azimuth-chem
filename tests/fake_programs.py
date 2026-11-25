"""Fake programs for the tests — on macOS, Linux and Windows alike.

The fake Multiwfn was a shell script («#!/bin/sh», read, cat, gunzip) — so the tests that need it were skipped on
Windows, and the runs of Multiwfn there went unchecked. Now the fake is a Python script with a launcher: a small shell
script on macOS / Linux, a .cmd on Windows (the program starts it as it starts Multiwfn.exe: the arguments, the answers
on the input, the files in its folder, the exit code).

fake_program(folder, body, name='Multiwfn') -> the path to give the program. body — Python run after the prelude:
    args the arguments («input.fchk», «-nt», «2» …)
    answer(k) the answer k (from 0) given on the input, stripped; '' past the last
    answers(n) the first n answers joined by spaces («7 1 1»)
    lines all the answers
    cat(*paths) the files to the output, byte for byte (the encoding of Windows does not touch them)
    echo(text) a line to the output
    gunzip(src, dst), cp(src, dst), sys.exit(code), time.sleep(s)
q(path) — a path as a Python literal for the body.

program_script(path, text) -> the path to give the program: a fake calculation program (xtb, CREST, ORCA)
    from a Python text, with or without its «#!» line — on macOS / Linux the script itself, executable; on Windows the
    script next to a .cmd that starts it with the Python of the tests (the .cmd is returned; runner.find_program looks
    for name.exe, name.cmd, name.bat there). No prelude: stdin is not read.
"""

import hashlib
import os
import sys
import tempfile
from pathlib import Path

# on macOS the first run of an executable that a
# Python process wrote waits for a check of the system — 0.7–4 s, and
# every test made its fake programs anew. executable(path, text) keeps each text once in CACHE (named by its hash) and
# puts at path a hard link to it: the check happens once per text, for all the tests and runs. The launchers carry no
# path of a test (they find their script as "$0.py"), so the same launcher serves every test.
CACHE = Path(tempfile.gettempdir()) / 'azimuth-test-programs'


def executable(path, text):
    """path — an executable with this text (POSIX): a hard link to the copy of the text in CACHE (a copy where a link
    cannot be made). The copy is read-only: a test that writes into a linked fake fails instead of changing it for all."""
    path = Path(path)
    data = text.encode('utf-8')
    cached = CACHE / hashlib.sha256(data).hexdigest()[:32]
    if not cached.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(dir=CACHE)
        with os.fdopen(fd, 'wb') as out:
            out.write(data)
        os.chmod(temporary, 0o555)
        os.replace(temporary, cached)
    if path.exists() or path.is_symlink():
        path.unlink()
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        os.link(cached, path)
    except OSError:
        path.write_bytes(data)
        path.chmod(0o755)
    return path


PYTHON_LAUNCHER = """#!{python}
import runpy, sys
sys.argv[0] = sys.argv[0] + '.py'
runpy.run_path(sys.argv[0], run_name='__main__')
"""


def launcher_text():
    """The launcher of a fake on macOS / Linux: the Python of the tests with the script next to it ("$0.py")."""
    return f'#!/bin/sh\nexec "{sys.executable}" "$0.py" "$@"\n'

PRELUDE = '''import gzip
import os
import shutil
import sys
import time

args = sys.argv[1:]
lines = sys.stdin.read().splitlines()


def answer(k):
    return lines[k].strip() if k < len(lines) else ''


def answers(n):
    return ' '.join(answer(k) for k in range(n))


def cat(*paths):
    for path in paths:
        with open(path, 'rb') as source:
            sys.stdout.buffer.write(source.read())
    sys.stdout.flush()


def echo(text):
    sys.stdout.buffer.write((text + '\\n').encode('utf-8'))
    sys.stdout.flush()


def gunzip(source, target):
    with gzip.open(source, 'rb') as packed, open(target, 'wb') as out:
        shutil.copyfileobj(packed, out)


def cp(source, target):
    shutil.copyfile(source, target)


'''


def q(path):
    return repr(str(path))


def fake_program(folder, body, name='Multiwfn'):
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    script = folder / f'{name}.py'
    script.write_text(PRELUDE + body.strip() + '\n', encoding='utf-8')
    if os.name == 'nt':
        # a settings.ini next to the fake, as in the package of Multiwfn — without it the program gives the
        # build for Windows an empty first answer (multiwfn.windows_answers: it waits for ENTER), and every answer of
        # the fake moved by one (all the tests with a fake Multiwfn failed on Windows)
        settings = folder / 'settings.ini'
        if not settings.exists():
            settings.write_text('', encoding='ascii')
        # the paths are not written into the .cmd (cmd.exe reads a batch file in the OEM code page — a Cyrillic folder
        # would break): the Python of the tests comes from the environment, the script lies next to the launcher
        os.environ['AZIMUTH_FAKE_PYTHON'] = sys.executable
        launcher = folder / f'{name}.cmd'
        launcher.write_text('@"%AZIMUTH_FAKE_PYTHON%" "%~dpn0.py" %*\r\n@exit /b %errorlevel%\r\n', encoding='ascii')
        return launcher
    return executable(folder / name, launcher_text())  # the script is folder/name.py — "$0.py" of the launcher


def program_script(path, text):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = text.split('\n', 1)[1] if text.startswith('#!') else text
    if os.name == 'nt':
        script = path.with_name(path.name + '.py')
        script.write_text(body, encoding='utf-8')
        os.environ['AZIMUTH_FAKE_PYTHON'] = sys.executable
        launcher = path.with_name(path.name + '.cmd')
        launcher.write_text('@"%AZIMUTH_FAKE_PYTHON%" "%~dpn0.py" %*\r\n@exit /b %errorlevel%\r\n', encoding='ascii')
        return launcher
    # the text (with the paths of its test) next to it as path.py; path — the launcher of every test, in
    # Python itself, not /bin/sh: on macOS /bin/sh drops DYLD_* (test_mpi_wrapper_restores_the_library_path)
    path.with_name(path.name + '.py').write_text(body, encoding='utf-8')
    return executable(path, PYTHON_LAUNCHER.format(python=sys.executable))


def alive(pid):
    """Whether the process pid still runs — os.kill(pid, 0) on POSIX; on Windows os.kill would end it, so the exit
    code is asked (STILL_ACTIVE)."""
    if os.name != 'nt':
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return True
        return True
    import ctypes

    kernel = ctypes.windll.kernel32
    handle = kernel.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
    if not handle:
        return False
    try:
        code = ctypes.c_ulong()
        if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
            return False
        return code.value == 259  # STILL_ACTIVE
    finally:
        kernel.CloseHandle(handle)

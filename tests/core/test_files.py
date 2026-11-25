"""azimuth/files.py — a text file written whole or not at all.

Oracles: the file read back (UTF-8, «\\n» line ends whatever the system); a failed write leaves the old file and no
temporary file in the folder; the module needs neither Qt nor the main window (it is imported in a fresh interpreter
and azimuth.app is not loaded).
"""

import subprocess
import sys
from pathlib import Path

import pytest

from azimuth.files import atomic_write

ROOT = Path(__file__).parents[2]


def test_written_whole_and_read_back(tmp_path):
    path = tmp_path / 'молекула.xyz'
    atomic_write(path, '1\nвода\r\nO 0 0 0\n')
    assert path.read_bytes() == '1\nвода\r\nO 0 0 0\n'.encode('utf-8')
    atomic_write(path, 'second')
    assert path.read_text(encoding='utf-8') == 'second' and [p.name for p in tmp_path.iterdir()] == ['молекула.xyz']


def test_a_failed_write_keeps_the_old_file(tmp_path):
    path = tmp_path / 'project.txt'
    atomic_write(path, 'old')

    class Broken:
        def __str__(self):
            raise RuntimeError('broken')

    with pytest.raises(TypeError):
        atomic_write(path, Broken())  # not text: the write fails after the temporary file is made
    assert path.read_text(encoding='utf-8') == 'old' and [p.name for p in tmp_path.iterdir()] == ['project.txt']


def test_no_window_is_loaded():
    code = 'import sys; import azimuth.files; print("azimuth.app" in sys.modules, "PySide6" in sys.modules)'
    done = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert done.stdout.split() == ['False', 'False']

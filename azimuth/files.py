"""Writing a text file whole or not at all.

§1 PURPOSE
    A file the program saves (a project, a structure, a table, a picture's data) is never left half written: a crash or
    a full disk in the middle leaves the old file as it was. Without Qt, so any part of the program — a dialog, a
    reader, a command without the window (azimuth/headless.py) — writes through it without importing the main window.
§2 ALGORITHM
    The text goes into a temporary file of the same folder (so the move stays on one disk), in UTF-8 with «\\n» line
    ends; os.replace puts it in place in one step; a temporary file left by an error is removed.
§4 SPECIFICATION
    atomic_write(path, text) — OSError as the system raises it.
§7 TESTS tests/core/test_files.py; tests/gui/test_gui_settings.py::test_atomic_unicode_save.
"""

import os
from pathlib import Path
import tempfile


def atomic_write(path, text):
    path = Path(path)
    descriptor, temporary = tempfile.mkstemp(prefix='.qcc-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8', newline='\n') as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)

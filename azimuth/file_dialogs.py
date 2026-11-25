"""The folder of the file windows: every «Открыть…» starts where the last file was opened.

§1 PURPOSE
    The windows for opening files started in the home folder; the user wants the folder of the last file opened —
    the calculations lie deep in Documents.
    With no folder kept, the windows start in the folder of the projects (root, given by the
    window); only a file or a folder opened is kept — a file saved somewhere (a report, a picture) does not move where
    the next «Открыть…» starts; a bare name to save (no folder) goes into that folder, not the working one of the
    program.
§2 ALGORITHM
    install(settings) wraps the static functions of QFileDialog once: getOpenFileName, getOpenFileNames,
    getExistingDirectory and getSaveFileName. When the folder given to them is the home folder, empty, or a file
    name in the home folder (a suggested name to save), the folder of the settings value KEY is used instead (a file
    name keeps its name there); a folder given on purpose (the programs, the examples) stays. After the window, the
    folder of the file chosen (or the folder chosen) is kept in KEY. Nothing changes when KEY names no folder that
    exists any more.
§4 SPECIFICATION KEY = 'last_open_folder'; install(settings, root=None) -> None (again: only the settings change);
    wrap(original, settings, kind ('open' | 'open-many' | 'folder' | 'save')) -> function; start(given, settings) ->
    str; remember(settings, chosen, kind).
§7 TESTS
    tests/core/test_file_dialogs.py."""

from pathlib import Path

# a key of its own — the old 'last_folder' kept also the folders of files saved (a report, a picture)
KEY = 'last_open_folder'
_state = {'settings': None, 'installed': False, 'root': None}
KEPT = ('open', 'open-many', 'folder')  # what is opened is kept, not what is saved


def _root():
    """The folder of the projects of Azimuth (the window gives it), when it exists."""
    root = _state.get('root')
    try:
        path = Path(str(root() if callable(root) else root)) if root else None
    except Exception:  # noqa: BLE001 — no folder of the projects: as before
        return None
    return path if path is not None and path.is_dir() else None


def _folder(settings):
    try:
        value = settings.value(KEY, '') if settings is not None else ''
    except Exception:  # noqa: BLE001 — settings that cannot be read: as before
        value = ''
    path = Path(str(value)) if value else None
    if path is not None and path.is_dir():
        return path
    return _root()  # nothing opened yet (or the folder is gone) — the projects of Azimuth


def start(given, settings):
    """The folder (or file path) the window starts in."""
    folder = _folder(settings)
    if folder is None:
        return given
    home = Path.home()
    text = str(given or '')
    if not text or Path(text) == home:
        return str(folder)
    path = Path(text)
    if not path.is_absolute():  # a bare name to save — there, not in the working folder of the program
        return str(folder / path)
    if path.parent == home and not path.is_dir():  # a name suggested in the home folder: the same name there
        return str(folder / path.name)
    return given


def remember(settings, chosen, kind):
    if settings is None or not chosen or kind not in KEPT:
        return
    first = chosen[0] if isinstance(chosen, (list, tuple)) else chosen
    if not first:
        return
    path = Path(str(first))
    folder = path if kind == 'folder' else path.parent
    if folder.is_dir():
        settings.setValue(KEY, str(folder))


def wrap(original, settings=None, kind='open'):
    def call(parent=None, caption='', dir='', *args, **kwargs):  # noqa: A002 — the name of Qt's argument
        if 'directory' in kwargs:  # the keyword of getExistingDirectory
            kwargs['directory'] = start(kwargs['directory'], _state['settings'] if settings is None else settings)
        else:
            dir = start(dir, _state['settings'] if settings is None else settings)
        result = original(parent, caption, dir, *args, **kwargs)
        chosen = result[0] if isinstance(result, tuple) else result
        remember(_state['settings'] if settings is None else settings, chosen, kind)
        return result

    call.__wrapped__ = original
    return staticmethod(call)


def install(settings, root=None):
    """root — the folder of the projects (a path or a function giving it): where the windows start first."""
    from PySide6.QtWidgets import QFileDialog

    _state['settings'] = settings
    if root is not None:
        _state['root'] = root
    if _state['installed']:
        return
    for name, kind in (('getOpenFileName', 'open'), ('getOpenFileNames', 'open-many'),
                       ('getExistingDirectory', 'folder'), ('getSaveFileName', 'save')):
        setattr(QFileDialog, name, wrap(getattr(QFileDialog, name), None, kind))
    _state['installed'] = True

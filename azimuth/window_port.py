"""The declared part of the window a tool may use: Studio holds the tools and links them through a small explicit
interface of commands and events, not through free access to the window.

WindowPort(window, names) — reading and setting only the names given (each tool writes them as its PORT); any other
name is an AttributeError naming the tool's missing declaration, so a new dependency on the window is a visible change
of PORT, not a silent one. The names are looked up on the window when used (a method replaced later — by a test, by a
subclass — is the one called). .widget — the window as the parent of Qt objects; .has(name) — hasattr of a declared
name.
"""


def part(window, name, module, cls):
    """The part `name` of the window made once from module.cls (it gets the window; its PORT says what of the
    window it uses). For properties of the window classes: part_tool = property(lambda self: part(self, ...))."""
    tool = window.__dict__.get('_' + name)
    if tool is None:
        import importlib

        tool = window.__dict__['_' + name] = getattr(importlib.import_module(module), cls)(window)
    return tool


class WindowPort:
    __slots__ = ('_window', '_names')

    def __init__(self, window, names):
        object.__setattr__(self, '_window', window)
        object.__setattr__(self, '_names', frozenset(names))

    def __getattr__(self, name):
        if name not in self._names:
            raise AttributeError(f'{name!r} is not in the port of this tool (add it to its PORT)')
        return getattr(self._window, name)

    def __setattr__(self, name, value):
        if name not in self._names:
            raise AttributeError(f'{name!r} is not in the port of this tool (add it to its PORT)')
        setattr(self._window, name, value)

    def __bool__(self):
        return True

    @property
    def widget(self):
        """The window as the parent of the dialogs, menus, actions and Qt objects of the tool."""
        return self._window

    def has(self, name):
        """hasattr on the window for a declared name (a part of the window that may not be built yet)."""
        if name not in self._names:
            raise AttributeError(f'{name!r} is not in the port of this tool (add it to its PORT)')
        return hasattr(self._window, name)

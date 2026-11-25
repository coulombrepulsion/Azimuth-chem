"""Compass: optimization constraints. No longer a mixin of the window — ConstraintTool, a part
of its own with an explicit port (the roadmap of 2026-11-09, stage 5); the rules are modules/compass/constraints.py.

The port (ConstraintPort) is all the tool knows of the window: the list of constraints of the document, the selected
atoms, the molecule, a message, «the constraints changed» and the parent of its menu. The window builds it
(CompassWorkspace.constraint_tool) and calls the tool; the tool reads no other attribute of the window.
"""

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from azimuth.i18n import tr
from azimuth.ui import smooth
from modules.compass import constraints as rules


@dataclass(frozen=True)
class ConstraintPort:
    items: Callable[[], list]  # the list of the document (changed in place: the document owns it)
    selected: Callable[[], list]
    molecule: Callable[[], object]
    notify: Callable[[str, int], None]
    changed: Callable[[], None]  # the window shows them and marks the document changed
    parent: object = None


class ConstraintTool:
    KINDS = rules.KINDS

    def __init__(self, port):
        self.port = port

    def find(self, atoms):
        """The stored constraint on these atoms (in either direction), or None."""
        return rules.find(self.port.items(), atoms)

    def toggle(self, atoms=None):
        atoms = list(self.port.selected() if atoms is None else atoms)
        try:
            new = rules.toggled(self.port.items(), atoms)
        except ValueError as exc:
            self.port.notify(str(exc), 8000)
            return
        self.port.items()[:] = new
        self.port.changed()

    def remove(self, item):
        items = self.port.items()
        if item in items:
            items.remove(item)
        self.port.changed()

    def clear(self):
        self.port.items().clear()
        self.port.changed()

    def text(self, item):
        return rules.text(item, self.port.molecule())

    def menu(self):
        menu = smooth(QMenu(self.port.parent))
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        title = rules.toggle_title(self.port.items(), self.port.selected(), self.port.molecule())
        if title:
            menu.addAction(title).triggered.connect(lambda: self.toggle())
        else:
            item = menu.addAction(tr('Выделите 1–4 атома: атом, длина, угол, двугранный угол'))
            item.setEnabled(False)
        items = self.port.items()
        if items:
            menu.addSeparator()
            head = menu.addAction(tr('Закреплено (щелчок — снять):'))
            head.setEnabled(False)
            for item in list(items):
                menu.addAction('  ' + self.text(item)).triggered.connect(lambda checked=False, c=item: self.remove(c))
            menu.addSeparator()
            menu.addAction(tr('Снять все ограничения')).triggered.connect(self.clear)
        return menu

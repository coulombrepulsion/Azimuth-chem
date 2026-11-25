"""Compass: the openers of three windows of Compass — the reaction path, the rotation about a bond, the search of
conformers (were the mixins PathActions, TorsionActions, ConformerActions of the window — the roadmap of
2026-11-09, stage 5).

DialogPort is all the openers know of the window: the parent of the windows, the molecule of the table, the selected
atoms, whether a trajectory is being browsed and how to close it, the messages, and where the open window is kept
(path_window, torsion_window, conformer_window — read by the window elsewhere). The windows themselves
(PathWindow, TorsionWindow, ConformerWindow) still get the window as their parent: their own port is a later step.
"""

from dataclasses import dataclass
from typing import Callable

from azimuth.i18n import tr


@dataclass(frozen=True)
class DialogPort:
    parent: object
    molecule: Callable[[], object]
    selected: Callable[[], list]
    browsing: Callable[[], bool]
    stop_browsing: Callable[[], None]
    notify: Callable[[str, int], None]
    error: Callable[[Exception], None]
    keep: Callable[[str, object], None]
    kept: Callable[[str], object]
    crystal: Callable[[], bool] = lambda: False  # «Компас · Кристалл» is shown


class DialogOpeners:
    def __init__(self, port):
        self.port = port

    def _leave_browsing(self):
        if self.port.browsing():
            self.port.stop_browsing()

    def path(self):
        from modules.compass.actions.path_actions import PathWindow

        self._leave_browsing()
        if len(self.port.molecule().atoms) < 2:
            self.port.notify(tr('Для пути нужны хотя бы два атома.'), 6000)
            return None
        window = PathWindow(self.port.parent)
        self.port.keep('path_window', window)
        window.show()
        return window

    def conformers(self):
        from modules.compass.actions.conformer_actions import ConformerWindow

        running = self.port.kept('conformer_window')
        try:  # a search going on (perhaps put away) — its window, not a new one
            if running is not None and running.searching():
                running.reopen()
                return running
        except (RuntimeError, AttributeError):
            pass
        if self.port.crystal():
            # the conformations of a crystal are fixed by its packing — a molecule taken out of it is searched in
            # «Компас · Молекула»
            self.port.notify(tr('Конформеры ищут для молекулы, а не для кристалла: в кристалле конформацию задаёт '
                                'упаковка. Выделите молекулу и «Правка → Выделенные молекулы — в новую вкладку '
                                'молекулы» — там поиск конформеров есть.'), 12000)
            return None
        self._leave_browsing()
        if len(self.port.molecule().atoms) < 4:
            self.port.notify(tr('Для конформеров нужна молекула хотя бы из четырёх атомов.'), 6000)
            return None
        window = ConformerWindow(self.port.parent)
        self.port.keep('conformer_window', window)
        window.show()
        return window

    def torsion(self, b=None, c=None):
        from modules.compass.actions.torsion_actions import TorsionWindow

        a = d = None
        if b is None or c is None:
            chosen = list(self.port.selected())
            if len(chosen) == 2:
                b, c = chosen
            elif len(chosen) == 4:
                a, b, c, d = chosen
            else:
                self.port.notify(tr('Выделите два связанных атома (связь) или четыре атома двугранного угла.'), 8000)
                return None
        old = self.port.kept('torsion_window')
        if old is not None and old.isVisible():
            old.cancel()
        try:
            window = TorsionWindow(self.port.parent, b, c, a, d)
        except ValueError as exc:
            self.port.error(exc)
            return None
        self.port.keep('torsion_window', window)
        window.show()
        return window

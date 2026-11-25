"""Showing a section of the hub: the switch with its transition, the calculation following into Sextant, the history
of the sections (back and forward), the page or the mode of Compass changed by itself. Methods of HubWindow (self is
the window), kept here to make window.py shorter.

Split off hub/window.py (0.222.30).
"""

from PySide6.QtCore import QEasingCurve, QPropertyAnimation
from hub.texts import TEXT


FADE_MS = 180


HOME = 'home'  # the program's start page; opened by the application icon in the top-left corner


HISTORY_LIMIT = 60


# -- sections ----------------------------------------------------------------------------
def show_section(self, ident, animate=True):
    if ident not in self.sections and ident != HOME:
        raise ValueError(f'Unknown section {ident!r}')
    if ident == self.current:
        if ident in self.buttons:
            self._mark_buttons(ident)
        return
    if ident == 'atlas':  # the Atlas of the site in the browser; the window stays where it is
        self.open_site_atlas()
        if self.current in self.buttons:
            self._mark_buttons(self.current)
        return
    previous = self.current
    studio = getattr(self, 'studio', None)
    mode = 'crystal' if ident == 'crystal' else 'molecule'
    if ident in ('compass', 'crystal') and studio is not None and getattr(studio, 'compass_mode', 'molecule') != mode:
        from azimuth.tasks import held

        if held():  # Молекула ↔ Кристалл changes the tabs shown — not under a work going on
            if self.current in self.buttons:
                self._mark_buttons(self.current)
            return
    self._transition(lambda: self._switch(ident), animate and previous is not None)


def _switch(self, ident):
    # while the hub itself changes the section, the page and the mode of Studio change under it — those
    # are not steps of the user (Sextant → «Кристалл» left an extra «Компас» in the history of «Назад»)
    if getattr(self, '_switching', False):
        return
    self._switching = True
    try:
        self._switch_now(ident)
    finally:
        self._switching = False
    page = self.sections[ident]['page'] if ident in self.sections else None
    if page is not None and self.studio.stack.currentIndex() != page:
        self._studio_page_changed(self.studio.stack.currentIndex())  # Studio went elsewhere itself: follow it


def _switch_now(self, ident):
    self.current = ident
    if hasattr(self, 'ornament'):
        self.ornament.set_section(ident)  # the picture of the section in the lower left corner
    self._update_header()
    if ident == HOME:
        self.home.show_texts(self.language, self.dark, getattr(self, 'family', ''), self.windowIcon())
        self.stack.setCurrentWidget(self.home)
        self.studio.vibrations.set_playing(False)
        for button in self.buttons.values():
            button.setChecked(False)
        self.setWindowTitle(TEXT[self.language]['brand'] + ' · ' + self.name(ident))
        self.preferences.setValue('hub_section', ident)
        self._remember((ident, None))
        self._job_follow()
        return
    item = self.sections[ident]
    self.stack.setCurrentWidget(self.studio)
    if self.studio.stack.currentIndex() != item['page']:
        self.studio.navigate(item['page'])
    if item['page'] == 0:  # «Компас · Молекула» and «Компас · Кристалл» share the page
        self.studio.crystal_tool.set_compass_mode('crystal' if ident == 'crystal' else 'molecule')
    self._mark_buttons(ident)
    self.setWindowTitle(TEXT[self.language]['brand'] + ' · ' + self.name(ident))
    self.preferences.setValue('hub_section', ident)
    self._remember((ident, None))
    self._job_follow()


def _job_follow(self):
    """The calculation is a panel of Sextant there and a window elsewhere (Sextant.job_follow)."""
    follow = getattr(getattr(self, 'studio', None), 'job_follow', None)
    if follow is not None:
        follow()


# -- history: back / forward ------------------------------------------------------------
def _remember(self, entry):
    """Add (section, None) to the history after the current position."""
    if self._history_nav:
        return
    if self.history_pos >= 0:
        here = self.history[self.history_pos]
        if here == entry:
            return
    del self.history[self.history_pos + 1 :]
    self.history.append(entry)
    if len(self.history) > HISTORY_LIMIT:
        del self.history[0]
    self.history_pos = len(self.history) - 1
    self._history_buttons()


def _history_buttons(self):
    if hasattr(self, 'back_button'):
        self.back_button.setEnabled(self.history_pos > 0)
        self.forward_button.setEnabled(self.history_pos < len(self.history) - 1)


def go_history(self, step):
    """Back (-1) or forward (+1) through the sections shown."""
    target = self.history_pos + step
    if not 0 <= target < len(self.history):
        return
    self.history_pos = target
    ident, _ = self.history[target]
    self._history_nav = True
    try:
        self.show_section(ident)
    finally:
        self._history_nav = False
    self._history_buttons()


def _told(self, text):
    if text:
        self.statusBar().clearMessage()
        self.statusBar().hide()
        self.studio.notify(text, 9000)


def _studio_page_changed(self, index):
    # Studio's own buttons (e.g. Compass -> Sextant) move the hub selection along.
    if self.current in (None, HOME) or getattr(self, '_switching', False):
        return
    wanted = 'crystal' if getattr(self.studio, 'compass_mode', 'molecule') == 'crystal' else 'compass'
    for ident, item in self.sections.items():
        if item['page'] is not None and item['page'] == index and ident != self.current:
            if index == 0 and ident != wanted and wanted in self.sections:
                continue  # the Compass page: the section of its mode
            self._switch(ident)
            break


def _compass_mode_changed(self, mode):
    """The Compass page changed its mode itself (a CIF was opened): the hub shows the matching section."""
    ident = 'crystal' if mode == 'crystal' else 'compass'
    if self.current in ('compass', 'crystal') and ident != self.current and ident in self.sections:
        self._switch(ident)


def _transition(self, change, animate):
    if self._animation is not None:
        self._animation.stop()
        self.fader.hide()
        self._animation = None
    if not animate or FADE_MS <= 0 or not self.isVisible():
        change()
        return
    try:
        still = self.content.grab()
    except Exception:  # noqa: BLE001 — 0.91.52: an error while painting the still: change without the fade
        still = None
    if still is None or still.isNull():
        change()
        return
    change()
    self.fader.setPixmap(still)
    self.fader.setGeometry(self.content.rect())
    self.fader_effect.setOpacity(1.0)
    self.fader.show()
    self.fader.raise_()
    animation = QPropertyAnimation(self.fader_effect, b'opacity', self)
    animation.setDuration(FADE_MS)
    animation.setStartValue(1.0)
    animation.setEndValue(0.0)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)
    animation.finished.connect(self._transition_done)
    self._animation = animation
    animation.start()


def _transition_done(self):
    self.fader.hide()
    self._animation = None

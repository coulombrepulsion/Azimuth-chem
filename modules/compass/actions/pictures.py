"""Compass: PNG snapshots and GIF animations of the model (moved from workspace.py).

Since 2026-10-22 every picture is saved where the user chooses in a save dialog (azimuth.ui.ask_picture_path):
first the folder used last time, else the system Pictures folder. Nothing is written into the program folder,
and a cancelled dialog writes nothing and renders no frames.
"""

from datetime import datetime
from math import radians
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMenu

from azimuth.ui import ask_picture_path, smooth
from azimuth.i18n import tr


class PictureTool:
    """Was the mixin PictureActions of the window; a tool of its own — it reaches the window only through the names of
    PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'preferences',
        'browsing',
        'drawer',
        'error',
        'molecule',
        'notify',
        'trajectory_tool',
        'view_tool',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def picture_path(self, suffix):
        """Ask where to save a '.png' or '.gif'; None if the user cancels."""
        title = tr('Сохранить снимок') if suffix == '.png' else tr('Сохранить GIF')
        name = 'Azimuth-' + datetime.now().strftime('%Y%m%d-%H%M%S')
        return ask_picture_path(self.w.widget, title, name, suffix, getattr(self.w, 'preferences', None))

    def save_screenshot(self, scale=1):
        """The model as PNG (scale 1, or the ×N of «Настройки → Снимки»); returns the path, or None if cancelled or failed."""
        try:
            path = self.picture_path('.png')
            if path is None:
                return None
            self.w.viewer.scale_capture = scale
            try:
                self.w.viewer.screenshot(path)
            finally:
                self.w.viewer.scale_capture = 1
            self.w.notify(tr('Снимок сохранён: ') + str(path), 12000)
            return path
        except OSError as exc:
            self.w.error(exc)

    def snapshot_menu(self):
        from azimuth import defaults

        menu = smooth(QMenu(self.w.widget))
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        menu.addAction(tr('Снимок PNG')).triggered.connect(lambda: self.save_screenshot(1))
        large = defaults.get('picture_scale')  # «Настройки → Снимки» (was ×3)
        menu.addAction(tr('Снимок высокого разрешения') + f' (×{large})').triggered.connect(
            lambda: self.save_screenshot(large))
        menu.addAction(tr('Рисунок SVG (подписи — векторами)')).triggered.connect(lambda: self.w.view_tool.save_document('.svg'))
        menu.addAction(tr('Рисунок PDF (подписи — векторами)')).triggered.connect(lambda: self.w.view_tool.save_document('.pdf'))
        item = menu.addAction(tr('Прозрачный фон'))
        item.setCheckable(True)
        item.setChecked(self.w.viewer.transparent)
        item.toggled.connect(self.set_transparent_pictures)
        menu.addSeparator()
        menu.addAction(tr('GIF: вращение молекулы')).triggered.connect(self.save_rotation_gif)
        steps = [s for s in self.w.drawer.steps if s.geometry is not None] if self.w.browsing else []
        item = menu.addAction(tr('GIF: шаги оптимизации'))
        item.setEnabled(len(steps) > 1)
        item.triggered.connect(self.save_steps_gif)
        if not self.w.browsing:
            item.setToolTip(tr('Откройте шаги оптимизации (☰), чтобы записать их'))
        return menu

    def set_transparent_pictures(self, on):
        """The switch of the menu and of «Настройки → Снимки» — one choice, kept until the next start."""
        from azimuth import defaults

        self.w.viewer.transparent = defaults.put('picture_transparent', on, getattr(self.w, 'preferences', None))
        return self.w.viewer.transparent

    def _frame(self):
        pixmap = self.w.viewer.render_image(1, self.w.viewer.transparent)
        return pixmap.toImage()

    def write_gif(self, path, frames, delay_ms):
        from modules.compass.view.gif import write_gif

        write_gif(path, frames, delay_ms)
        self.w.notify(tr('GIF сохранён: ') + str(path), 12000)
        return path

    def save_rotation_gif(self):
        """A full turn about the vertical axis of the screen, 36 frames of 10°."""
        if not self.w.molecule.atoms:
            return
        try:
            path = self.picture_path('.gif')
            if path is None:
                return None
            self.w.viewer.keep_camera()
            yaw = self.w.viewer.yaw
            frames = []
            for k in range(36):
                self.w.viewer.yaw = yaw + k * radians(10)
                frames.append(self._frame())
            self.w.viewer.yaw = yaw
            self.w.viewer.update()
            return self.write_gif(path, frames, 80)
        except (OSError, ValueError) as exc:
            self.w.error(exc)

    def save_steps_gif(self):
        """The cycles of the open optimization, one frame each (the starting geometry as in the field)."""
        if not self.w.browsing:
            return
        try:
            path = self.picture_path('.gif')
            if path is None:
                return None
            current = self.w.drawer.current
            frames = []
            for row, step in enumerate(self.w.drawer.steps):
                if step.geometry is None:
                    continue
                self.w.drawer.select(row)
                self.w.trajectory_tool.show_trajectory_step(row)
                frames.append(self._frame())
            self.w.drawer.select(current)
            return self.write_gif(path, frames, 400)
        except (OSError, ValueError) as exc:
            self.w.error(exc)

"""Compass: «Вид → Схема отображения» — ready looks, the user's own, element colours.

§1 THEORY modules/compass/view/schemes.py §1.
§2 ALGORITHM current_scheme() reads the look from the controls and the viewer; apply_scheme(s) sets the
               controls (display mode, labels, projection, axes), the bond options with their menu items,
               and the viewer (palette, size of the atoms, background, grid); every setting is kept in the
               settings of the program as before (new keys: atom_scale, palette, element_colors,
               background, grid). The user's schemes are kept under SETTINGS_KEY (schemes.dump). The
               menu marks the scheme equal to the current look. «Цвет элемента…» (atom menu) sets one
               element colour for the current look.
§3 APPLICATIONS «Вид → Схема отображения» of Compass, the atom menu of the model.
§4 SPECIFICATION current_scheme() -> dict; apply_scheme(s); save_scheme(name=None) -> name or None;
               delete_scheme(name, ask=True) -> bool; set_element_color(symbol, color=None);
               reset_element_colors(); fill_scheme_menu(menu).
§5 PROCEDURES below.
§6 NOTES the theme of the program is not part of a scheme (the background can be fixed instead).
§7 TESTS tests/compass/test_schemes.py (the schemes); tests/test_gui.py::test_display_schemes.
§8' ROBUSTNESS damaged saved settings fall back to the default look with a message, the saved text is kept.
"""

import json

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QInputDialog, QMenu, QMessageBox

from modules.compass.view import schemes
from azimuth.i18n import tr
from azimuth import quill  # Quill over the waste basket asks about deleting and replacing
from azimuth.ui import smooth

YES_NO = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

SETTINGS_KEY = 'display_schemes'


def _flag(value, default):
    if value is None or value == '':
        return default
    return str(value).lower() in ('true', '1')


class SchemeTool:
    """Was the mixin SchemeActions of the window; a part of its own — it reaches the window only through the names
    of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'axes_button',
        'bond_color_actions',
        'bond_option_actions',
        'bond_width_actions',
        'change_display_mode',
        'change_labels',
        'change_projection',
        'display_mode',
        'error',
        'label_mode',
        'notify',
        'preferences',
        'projection',
        'scheme_editor_action',
        'scheme_menu',
        'toggle_axes',
        'user_schemes',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def build_scheme_actions(self):
        self.w.user_schemes = {}
        text = self.w.preferences.value(SETTINGS_KEY, '')
        if text:
            try:
                self.w.user_schemes = schemes.parse(str(text))
            except ValueError as exc:
                self.w.notify(tr('Схемы отображения не прочитаны: ') + str(exc), 12000)
        v = self.w.viewer
        try:
            v.atom_scale = min(2.5, max(0.4, float(self.w.preferences.value('atom_scale', 1.0))))
        except (TypeError, ValueError):
            v.atom_scale = 1.0
        name = self.w.preferences.value('palette', 'azimuth')
        self.palette_name = name if name in schemes.FIELDS['palette'] else 'azimuth'
        try:
            colors = json.loads(self.w.preferences.value('element_colors', '') or '{}')
            self.element_colors = schemes.normalize({**schemes.DEFAULT, 'colors': colors})['colors']
        except (TypeError, ValueError):
            self.element_colors = {}
        background = self.w.preferences.value('background', 'theme')
        v.background = background if background in schemes.FIELDS['background'] else 'theme'
        v.grid = _flag(self.w.preferences.value('grid', True), True)
        self._refresh_palette()
        self.w.scheme_menu = smooth(QMenu(tr('Схема отображения'), self.w.widget))
        self.w.scheme_menu.aboutToShow.connect(lambda: self.fill_scheme_menu(self.w.scheme_menu))
        from PySide6.QtGui import QAction

        self.w.scheme_editor_action = QAction(tr('Свой вид…'), self.w.widget)  # «Отображение» of the hub
        self.w.scheme_editor_action.setToolTip(tr('Все параметры вида модели в одном окне; сохранить как свою схему'))
        self.w.scheme_editor_action.triggered.connect(self.open_scheme_editor)

    def _refresh_palette(self):
        self.w.viewer.palette = schemes.palette(
            {**schemes.DEFAULT, 'palette': self.palette_name, 'colors': dict(self.element_colors)}
        )
        self.w.viewer.update()

    def current_scheme(self):
        v = self.w.viewer
        return schemes.normalize(
            {
                'display_mode': v.display_mode,
                'bond_color': v.bond_color,
                'bond_width': float(v.bond_width),
                'show_bonds': bool(v.show_bonds),
                'multiple_bonds': bool(v.multiple_bonds),
                'label_mode': v.label_mode,
                'perspective': bool(v.perspective),
                'show_axes': bool(v.show_axes),
                'atom_scale': float(v.atom_scale),
                'palette': self.palette_name,
                'colors': dict(self.element_colors),
                'background': v.background,
                'grid': bool(v.grid),
            }
        )

    def apply_scheme(self, scheme):
        s = schemes.normalize(scheme)
        v, prefs = self.w.viewer, self.w.preferences
        self.w.display_mode.setCurrentIndex(max(0, self.w.display_mode.findData(s['display_mode'])))
        self.w.change_display_mode()
        self.w.label_mode.setCurrentIndex(max(0, self.w.label_mode.findData(s['label_mode'])))
        self.w.change_labels()
        self.w.projection.setCurrentIndex(1 if s['perspective'] else 0)
        self.w.change_projection()
        self.w.axes_button.setChecked(s['show_axes'])
        self.w.toggle_axes()
        v.bond_color = s['bond_color']
        prefs.setValue('bond_color', s['bond_color'])
        for key, item in getattr(self.w, 'bond_color_actions', {}).items():
            item.setChecked(key == s['bond_color'])
        v.bond_width = s['bond_width']
        prefs.setValue('bond_width', s['bond_width'])
        for value, item in getattr(self.w, 'bond_width_actions', {}).items():
            item.setChecked(abs(value - s['bond_width']) < 1e-9)
        for key in ('show_bonds', 'multiple_bonds'):
            setattr(v, key, s[key])
            prefs.setValue(key, s[key])
            item = getattr(self.w, 'bond_option_actions', {}).get(key)
            if item is not None:
                item.setChecked(s[key])
        v.atom_scale = s['atom_scale']
        self.palette_name = s['palette']
        self.element_colors = dict(s['colors'])
        v.background = s['background']
        v.grid = s['grid']
        prefs.setValue('atom_scale', v.atom_scale)
        prefs.setValue('palette', self.palette_name)
        prefs.setValue('element_colors', json.dumps(self.element_colors))
        prefs.setValue('background', v.background)
        prefs.setValue('grid', v.grid)
        v.locked_camera = None
        self._refresh_palette()

    START_KEY = 'start_scheme'  # «Настройки → Вид модели»: '' — the look of the last session

    def scheme_names(self):
        """The ready schemes and the user's own, in the order of the menu."""
        return list(schemes.BUILTIN) + [n for n in getattr(self.w, 'user_schemes', {}) if n not in schemes.BUILTIN]

    def start_scheme(self):
        name = str(self.w.preferences.value(self.START_KEY, '') or '')
        return name if name in self.scheme_names() else ''

    def set_start_scheme(self, name):
        self.w.preferences.setValue(self.START_KEY, name if name in self.scheme_names() else '')
        return self.start_scheme()

    def apply_start_scheme(self):
        """At the start of the program: the scheme chosen in «Настройки», if any (else the look stays as it was left)."""
        name = self.start_scheme()
        if name:
            self.apply_scheme(getattr(self.w, 'user_schemes', {}).get(name) or schemes.BUILTIN[name])
        return name

    def open_scheme_editor(self):
        """«Отображение → Свой вид…» (modules/compass/panels/scheme_editor.py)."""
        from modules.compass.panels.scheme_editor import SchemeEditor

        old = getattr(self, 'scheme_editor', None)
        if old is not None:
            try:
                old.close()
            except RuntimeError:
                pass
        self.scheme_editor = editor = SchemeEditor(self.w.widget)
        editor.show()
        editor.raise_()
        return editor

    def _set(self, **changes):
        s = self.current_scheme()
        s.update(changes)
        self.apply_scheme(s)

    def save_scheme(self, name=None):
        if name is None:
            name, ok = QInputDialog.getText(self.w.widget, tr('Сохранить схему отображения'), tr('Название схемы:'))
            if not ok:
                return None
        name = ' '.join(str(name).split())
        if not name or len(name) > 60:
            self.w.error(ValueError(tr('Название схемы — от 1 до 60 знаков.')))
            return None
        if name in schemes.BUILTIN or tr(name) in {tr(k) for k in schemes.BUILTIN}:
            self.w.error(ValueError(tr('Так называется готовая схема — выберите другое название.')))
            return None
        if name in self.w.user_schemes and (
            quill.question(self.w.widget, tr('Схемы отображения'), tr('Заменить схему «') + name + tr('»?'),
                           YES_NO, QMessageBox.StandardButton.No, 'delete')
            != QMessageBox.StandardButton.Yes
        ):
            return None
        self.w.user_schemes[name] = self.current_scheme()
        self.w.preferences.setValue(SETTINGS_KEY, schemes.dump(self.w.user_schemes))
        self.w.notify(tr('Схема «') + name + tr('» сохранена: «Вид → Схема отображения».'), 8000)
        return name

    def delete_scheme(self, name, ask=True):
        if name not in self.w.user_schemes:
            return False
        if ask and (
            quill.question(self.w.widget, tr('Схемы отображения'), tr('Удалить схему «') + name + tr('»?'),
                           YES_NO, QMessageBox.StandardButton.No, 'delete')
            != QMessageBox.StandardButton.Yes
        ):
            return False
        del self.w.user_schemes[name]
        self.w.preferences.setValue(SETTINGS_KEY, schemes.dump(self.w.user_schemes))
        return True

    def set_element_color(self, symbol, color=None):
        if color is None:
            from modules.compass.actions.style_form import pick_colour

            color = pick_colour(self.w.viewer.palette.get(symbol, schemes.NEUTRAL), self.w.widget,
                                tr('Цвет элемента ') + symbol)  # one compact picker everywhere
            if not color:
                return
        colors = dict(self.element_colors)
        colors[symbol] = color
        self._set(colors=colors)

    def reset_element_colors(self):
        self._set(colors={})

    def fill_scheme_menu(self, menu):
        menu.clear()
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint)
        menu.setToolTipsVisible(True)
        now = self.current_scheme()

        def add(target, title, scheme):
            item = target.addAction(title)
            item.setCheckable(True)
            item.setChecked(schemes.same(scheme, now))
            item.triggered.connect(lambda checked=False, s=scheme: self.apply_scheme(s))

        for name, scheme in schemes.BUILTIN.items():
            add(menu, tr(name), scheme)
        if self.w.user_schemes:
            menu.addSeparator()
            for name, scheme in self.w.user_schemes.items():
                add(menu, name, scheme)
        menu.addSeparator()

        def choice(title, key, options):
            sub = smooth(menu.addMenu(tr(title)))
            sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            sub.setWindowFlags(sub.windowFlags() | Qt.WindowType.FramelessWindowHint)
            for label, value in options:
                item = sub.addAction(tr(label))
                item.setCheckable(True)
                item.setChecked(now[key] == value)
                item.triggered.connect(lambda checked=False, k=key, x=value: self._set(**{k: x}))

        choice('Размер атомов', 'atom_scale', [('Мелкие · 0,7', 0.7), ('Обычные · 1', 1.0), ('Крупные · 1,3', 1.3), ('Очень крупные · 1,6', 1.6)])
        choice('Цвета элементов', 'palette', [('Азимут', 'azimuth'), ('Jmol (CPK)', 'jmol'), ('Оттенки серого', 'mono')])
        choice('Фон', 'background', [('Как тема', 'theme'), ('Белый', 'white'), ('Чёрный', 'black')])
        grid = menu.addAction(tr('Сетка точек'))
        grid.setCheckable(True)
        grid.setChecked(now['grid'])
        grid.toggled.connect(lambda on: self._set(grid=bool(on)))
        item = menu.addAction(tr('Сбросить свои цвета элементов'))
        item.setEnabled(bool(self.element_colors))
        item.triggered.connect(self.reset_element_colors)
        menu.addSeparator()
        menu.addAction(tr('Свой вид…')).triggered.connect(self.open_scheme_editor)  # every parameter at once
        menu.addAction(tr('Сохранить текущий вид как схему…')).triggered.connect(lambda: self.save_scheme())
        if self.w.user_schemes:
            sub = smooth(menu.addMenu(tr('Удалить схему')))
            sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            sub.setWindowFlags(sub.windowFlags() | Qt.WindowType.FramelessWindowHint)
            for name in self.w.user_schemes:
                sub.addAction(name).triggered.connect(lambda checked=False, n=name: self.delete_scheme(n))

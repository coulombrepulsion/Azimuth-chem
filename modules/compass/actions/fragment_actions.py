"""Compass: the user's own fragments — save a group of the model, reuse it, share it.

§1 THEORY the fragment frame and the cut: modules/compass/chemistry/user_fragments.py §1–§2.
§2 ALGORITHM «Сохранить выделенное как фрагмент…» cuts the selected atoms (all atoms if none is
               selected), asks for a name (the formula of the group is offered) and keeps the set in
               the settings of the program (QSettings key SETTINGS_KEY, the JSON of user_fragments);
               the fragments appear in the «Фрагмент» menu under «Мои фрагменты» and are placed and
               put on hydrogens like the built-in ones. Delete asks first. Export writes the JSON file;
               import adds the fragments of a file, a name already in use gets « (2)», « (3)»….
§3 APPLICATIONS the «Фрагмент» button menu, «Правка → Сохранить выделенное как фрагмент…».
§4 SPECIFICATION save_selection_as_fragment(name=None) -> key or None; delete_user_fragment(key,
               ask=True) -> bool; export_user_fragments(path=None); import_user_fragments(path=None)
               -> number added; add_fragment_tools(menu).
§5 PROCEDURES below.
§6 NOTES the settings survive updates of the program; the export file is the way to move the
               fragments to another computer.
§7 TESTS tests/compass/test_user_fragments.py (the cut and the file); tests/test_gui.py::
               test_user_fragment_saved_placed_exported_and_deleted.
§8' ROBUSTNESS damaged settings are reported once and left untouched (not overwritten until the
               next save); a damaged import file adds nothing.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from modules.compass.chemistry import user_fragments, user_molecules
from azimuth.i18n import set_combo_key, tr
from azimuth import quill  # Quill over the waste basket asks about deleting and replacing
from azimuth.ui import smooth

YES_NO = QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No

SETTINGS_KEY = 'user_fragments'
MOLECULES_KEY = 'user_molecules'  # «Мои молекулы» (user_molecules.py)


class FragmentTool:
    """Was the mixin FragmentActions of the window; a tool of its own — it reaches the window only through the names of
    PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'build_mode',
        'charge',
        'confirm_replace',
        'coordinate_tool',
        'crystal_tool',
        'error',
        'fragment',
        'load_molecule',
        'notify',
        'preferences',
        'project_path',
        'save_text',
        'spin',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    # -- «Мои молекулы» -----------------------------------------------------------------------------------------
    def build_molecule_store(self):
        """The user's molecules from the settings into user_molecules.USER (a damaged entry: said, none taken)."""
        text = self.w.preferences.value(MOLECULES_KEY, '')
        found = {}
        if text:
            try:
                found = user_molecules.parse(str(text))
            except ValueError as exc:
                self.w.notify(tr('Мои молекулы не прочитаны: ') + str(exc), 12000)
        user_molecules.register(found)

    def _store_molecules(self, mapping):
        user_molecules.register(mapping)
        self.w.preferences.setValue(MOLECULES_KEY, user_molecules.dump(user_molecules.USER))

    def save_molecule(self, indices=None, name=None):
        """«Сохранить молекулу в «Мои молекулы»…»: the atoms indices (None — the atoms chosen, else all) under a name
        asked (the title of the structure, else its formula). The name, or None."""
        molecule = self.w.coordinate_tool.table_molecule()
        if indices is None:
            indices = list(self.w.viewer.selected) or list(range(len(molecule.atoms)))
        try:
            kept = user_molecules.cut(molecule, indices)
        except ValueError as exc:
            self.w.error(exc)
            return None
        if name is None:
            title = (kept.title or '').strip()
            default = title if title and title != tr('Новая молекула') else kept.formula
            name, ok = QInputDialog.getText(self.w.widget, tr('Мои молекулы'),
                                            tr('Название молекулы ({} атомов):').format(len(kept.atoms)), text=default)
            if not ok:
                return None
        try:
            key = user_molecules.check_name(name)
        except ValueError as exc:
            if ' '.join(str(name or '').split()) not in user_molecules.USER:
                self.w.error(exc)
                return None
            key = ' '.join(str(name).split())
        if key in user_molecules.USER and (
            quill.question(self.w.widget, tr('Мои молекулы'), tr('Заменить молекулу «{}»?').format(key),
                           YES_NO, QMessageBox.StandardButton.No, 'delete')
            != QMessageBox.StandardButton.Yes
        ):
            return None
        from dataclasses import replace

        mapping = dict(user_molecules.USER)
        mapping[key] = replace(kept, title=key)
        self._store_molecules(mapping)
        self.w.notify(tr('Молекула «{}» сохранена: «Файл → Примеры молекул → Мои молекулы» и «Молекула» при '
                         'построении.').format(key), 10000)
        return key

    def delete_user_molecule(self, key, ask=True):
        if key not in user_molecules.USER:
            return False
        if ask and (
            quill.question(self.w.widget, tr('Мои молекулы'), tr('Удалить молекулу «{}» из «Моих молекул»?').format(key),
                           YES_NO, QMessageBox.StandardButton.No, 'delete')
            != QMessageBox.StandardButton.Yes
        ):
            return False
        self._store_molecules({k: v for k, v in user_molecules.USER.items() if k != key})
        return True

    def open_user_molecule(self, key):
        """«Файл → Примеры молекул → Мои молекулы → …»: into the tab, as an example."""
        if key not in user_molecules.USER or not self.w.confirm_replace():
            return False
        self.w.crystal_tool.clear_crystal()
        self.w.project_path = None
        self.w.load_molecule(user_molecules.USER[key])
        self.w.charge.setValue(0)
        self.w.spin.setValue(1)
        return True

    def fill_user_molecules_menu(self, menu):
        """«Мои молекулы» of «Файл → Примеры молекул», made anew each time it opens."""
        menu.clear()
        for key in user_molecules.USER:
            menu.addAction(key).triggered.connect(lambda checked=False, k=key: self.open_user_molecule(k))
        if not user_molecules.USER:
            empty = menu.addAction(tr('Пока пусто — сохраните молекулу пунктом ниже'))
            empty.setEnabled(False)
        menu.addSeparator()
        self.add_molecule_tools(menu)
        return menu

    def add_molecule_tools(self, menu):
        """«Сохранить молекулу…» and «Удалить мою молекулу» at the bottom of a menu."""
        menu.addAction(tr('Сохранить молекулу в «Мои молекулы»…')).triggered.connect(lambda: self.save_molecule())
        if user_molecules.USER:
            sub = smooth(menu.addMenu(tr('Удалить мою молекулу')))
            sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            sub.setWindowFlags(sub.windowFlags() | Qt.WindowType.FramelessWindowHint)
            for key in user_molecules.USER:
                sub.addAction(key).triggered.connect(lambda checked=False, k=key: self.delete_user_molecule(k))
        return menu

    def build_fragment_actions(self):
        self.build_molecule_store()
        text = self.w.preferences.value(SETTINGS_KEY, '')
        fragments = {}
        if text:
            try:
                fragments = user_fragments.parse(str(text))
            except ValueError as exc:
                self.w.notify(tr('Мои фрагменты не прочитаны: ') + str(exc), 12000)
        try:
            user_fragments.register(fragments)
        except ValueError as exc:
            self.w.notify(tr('Мои фрагменты не прочитаны: ') + str(exc), 12000)
            user_fragments.register({})
        for key in user_fragments.USER:
            self.w.fragment.addItem(key)

    def _store_fragments(self, fragments):
        before = set(user_fragments.USER)
        user_fragments.register(fragments)
        self.w.preferences.setValue(SETTINGS_KEY, user_fragments.dump(user_fragments.USER))
        present = {self.w.fragment.itemText(i) for i in range(self.w.fragment.count())}
        for key in user_fragments.USER:
            if key not in present:
                self.w.fragment.addItem(key)
        for i in reversed(range(self.w.fragment.count())):  # only the deleted user fragments go
            if self.w.fragment.itemText(i) in before - set(user_fragments.USER):
                self.w.fragment.removeItem(i)

    def save_selection_as_fragment(self, name=None):
        molecule = self.w.coordinate_tool.table_molecule()
        indices = list(self.w.viewer.selected) or list(range(len(molecule.atoms)))
        try:
            atoms, bonds = user_fragments.cut(molecule, indices)
        except ValueError as exc:
            self.w.error(exc)
            return None
        if name is None:
            from azimuth.core import Atom, Molecule

            formula = Molecule('', tuple(Atom(s, x, y, z) for s, x, y, z in atoms)).formula
            name, ok = QInputDialog.getText(
                self.w.widget,
                tr('Сохранить как фрагмент'),
                tr('Название фрагмента (атом присоединения — ') + atoms[0][0] + '):',
                text=formula,
            )
            if not ok:
                return None
        replace = False
        try:
            key = user_fragments.check_name(name)
            if key in user_fragments.USER:
                replace = True
        except ValueError as exc:
            self.w.error(exc)
            return None
        if replace and (
            quill.question(self.w.widget, tr('Мои фрагменты'), tr('Заменить фрагмент «') + key + tr('»?'),
                           YES_NO, QMessageBox.StandardButton.No, 'delete')
            != QMessageBox.StandardButton.Yes
        ):
            return None
        fragments = dict(user_fragments.USER)
        fragments[key] = (atoms, bonds)
        self._store_fragments(fragments)
        self.w.notify(tr('Фрагмент «') + key + tr('» сохранён: кнопка «Фрагмент» → «Мои фрагменты».'), 10000)
        return key

    def delete_user_fragment(self, key, ask=True):
        if key not in user_fragments.USER:
            return False
        if ask and (
            quill.question(self.w.widget, tr('Мои фрагменты'), tr('Удалить фрагмент «') + key + tr('»?'),
                           YES_NO, QMessageBox.StandardButton.No, 'delete')
            != QMessageBox.StandardButton.Yes
        ):
            return False
        fragments = {k: v for k, v in user_fragments.USER.items() if k != key}
        self._store_fragments(fragments)
        return True

    def export_user_fragments(self, path=None):
        text = user_fragments.dump(user_fragments.USER)
        if path is None:
            self.w.save_text(tr('Экспорт моих фрагментов'), tr('Фрагменты «Азимута» (*.json)'), text, 'fragments.json')
            return
        from azimuth.files import atomic_write  # the writer of save_text

        atomic_write(path, text)

    def import_user_fragments(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(
                self.w.widget, tr('Импорт фрагментов'), str(Path.home()), tr('Фрагменты «Азимута» (*.json);;Все файлы (*)')
            )
            if not path:
                return 0
        try:
            found = user_fragments.parse(Path(path).read_text(encoding='utf-8'))
        except (OSError, UnicodeError, ValueError) as exc:
            self.w.error(exc)
            return 0
        fragments = dict(user_fragments.USER)
        added = 0
        for key, value in found.items():
            new, n = key, 2
            while True:
                try:
                    new = user_fragments.check_name(new, taken=set(fragments))
                    break
                except ValueError:
                    new = f'{key} ({n})'
                    n += 1
                    if n > 99:
                        new = None
                        break
            if new is None:
                continue
            fragments[new] = value
            added += 1
        self._store_fragments(fragments)
        self.w.notify(tr(f'Добавлено фрагментов: {added}'), 8000)
        return added

    def add_fragment_tools(self, menu):
        """The management items at the bottom of the «Фрагмент» menu."""
        menu.addSeparator()
        menu.addAction(tr('Сохранить выделенное как фрагмент…')).triggered.connect(
            lambda: self.save_selection_as_fragment()
        )
        if user_fragments.USER:
            sub = smooth(menu.addMenu(tr('Удалить мой фрагмент')))
            sub.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
            sub.setWindowFlags(sub.windowFlags() | Qt.WindowType.FramelessWindowHint)
            for key in user_fragments.USER:
                sub.addAction(key).triggered.connect(lambda checked=False, k=key: self.delete_user_fragment(k))
            menu.addAction(tr('Экспорт моих фрагментов…')).triggered.connect(lambda: self.export_user_fragments())
        menu.addAction(tr('Импорт фрагментов…')).triggered.connect(lambda: self.import_user_fragments())
        return menu

    def choose_user_fragment(self, key):
        if set_combo_key(self.w.fragment, key):
            self.w.build_mode.setCurrentIndex(2)


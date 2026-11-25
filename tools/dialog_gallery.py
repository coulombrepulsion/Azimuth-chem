"""Галерея окон «Азимута»: снимки всех диалогов, окон сообщений и меню в светлой и тёмной теме.

Запуск из папки программы: .venv/bin/python tools/dialog_gallery.py (Windows: .venv\\Scripts\\python ...)

Окна по очереди открываются и закрываются на экране (около минуты, ничего не нажимайте). Настройки — свои, во
временном файле: настройки пользователя не меняются. Снимки — в папке .gallery/ программы (PNG и index.html), список
окон, которые открыть не удалось, — в .gallery/errors.txt.

Как это работает: модальные окна (QDialog.exec, QMessageBox, QInputDialog.getText/getInt) и меню (QMenu.exec /
popup) подменяются так, что окно показывается, снимается (QWidget.grab) и закрывается с ответом «Отмена»; немодальные
окна (таблица Менделеева, орбитали, Z-матрица…) снимаются после вызова метода, который их открывает. Выпадающие списки
— их раскрытый список. Системные окна выбора файла и цвета не снимаются (их рисует macOS / Windows).
"""

import os
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault('AZIMUTH_SETTINGS_FILE', os.path.join(tempfile.mkdtemp(prefix='azimuth-gallery-'), 'settings.ini'))

from PySide6.QtCore import QPoint, QTimer  # noqa: E402
from PySide6.QtGui import QColor  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QApplication,
    QColorDialog,
    QDialog,
    QFileDialog,
    QInputDialog,
    QLineEdit,
    QMenu,
    QMessageBox,
)

OUT = ROOT / '.gallery'
state = {'theme': 'light', 'scene': '', 'n': 0, 'shots': [], 'errors': []}
app = None


def settle(rounds=6):
    for _ in range(rounds):
        app.processEvents()


def shoot(widget, what=''):
    """A picture of the widget (its window) as it is on the screen."""
    settle()
    state['n'] += 1
    label = (state['scene'] + (' · ' + what if what else '')).strip(' ·')
    name = f"{state['theme']}_{state['n']:03d}_{''.join(c if c.isalnum() else '_' for c in label)[:60]}.png"
    widget.grab().save(str(OUT / name))
    state['shots'].append((state['theme'], label, name, widget.windowTitle() if widget.isWindow() else ''))


# -- the modal windows and menus are shown, photographed and closed ---------------------------------------------------
def fake_exec(self, *args, **kwargs):
    self.show()
    self.raise_()
    shoot(self, self.windowTitle() or type(self).__name__)
    self.hide()
    return 0


def menu_exec(self, *args, **kwargs):
    self.popup(QPoint(240, 200))
    shoot(self, self.title() or 'меню')
    self.hide()
    return None


real_popup = QMenu.popup


def menu_popup(self, *args, **kwargs):
    real_popup(self, *args, **kwargs)
    shoot(self, self.title() or 'меню')
    self.hide()


def input_text(parent, title, label, echo=QLineEdit.EchoMode.Normal, text='', *args, **kwargs):
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setTextEchoMode(echo)
    dialog.setTextValue(text)
    dialog.exec()
    return '', False


def input_int(parent, title, label, value=0, low=-2147483647, high=2147483647, step=1, *args, **kwargs):
    dialog = QInputDialog(parent)
    dialog.setWindowTitle(title)
    dialog.setLabelText(label)
    dialog.setInputMode(QInputDialog.InputMode.IntInput)
    dialog.setIntRange(low, high)
    dialog.setIntValue(value)
    dialog.exec()
    return value, False


def install_fakes():
    QDialog.exec = fake_exec
    QMessageBox.exec = fake_exec
    QMenu.exec = menu_exec
    QMenu.popup = menu_popup
    QInputDialog.getText = staticmethod(input_text)
    QInputDialog.getInt = staticmethod(input_int)
    QColorDialog.getColor = staticmethod(lambda *a, **k: QColor())
    QFileDialog.getOpenFileName = staticmethod(lambda *a, **k: ('', ''))
    QFileDialog.getOpenFileNames = staticmethod(lambda *a, **k: ([], ''))
    QFileDialog.getSaveFileName = staticmethod(lambda *a, **k: ('', ''))
    QFileDialog.getExistingDirectory = staticmethod(lambda *a, **k: '')


def scene(name, action, window):
    """Run action; the windows it opened (not modal) are photographed and hidden."""
    state['scene'] = name
    before = {id(w) for w in QApplication.topLevelWidgets() if w.isVisible()}
    try:
        action()
    except Exception:  # noqa: BLE001 — a window that cannot be opened here is written down, the gallery goes on
        state['errors'].append(f"[{state['theme']}] {name}:\n{traceback.format_exc()}")
    settle(10)
    for widget in QApplication.topLevelWidgets():
        if widget.isVisible() and id(widget) not in before and widget is not window and not isinstance(widget, QMenu):
            if type(widget).__name__ in ('QComboBoxPrivateContainer', 'QTipLabel'):
                continue
            shoot(widget, widget.windowTitle() or type(widget).__name__)
            widget.hide()


def combo(widget):
    """The open list of a combo box."""
    def run():
        widget.showPopup()
        settle(8)
        shoot(widget.view().window(), widget.accessibleName() or widget.currentText())
        widget.hidePopup()
    return run


def scenes(window):
    from modules.sextant.batch_actions import BatchDialog

    examples = ROOT / 'examples'
    ethanol = examples / '8-compare' / 'ethanol.xyz'

    def molecule():
        window.navigate(0)
        window.confirm_replace = lambda: True
        window.opening_tool.open_path(str(ethanol))
        window.dirty = False

    def selected(*indices):
        def run():
            window.viewer.selected = list(indices)
        return run

    plan = [
        ('Компас: молекула', molecule),
        ('Компас: таблица Менделеева', window.show_periodic_table),
        ('Компас: Z-матрица', window.view_tool.open_zmatrix_editor),
        ('Компас: вращение вокруг связи', lambda: window.compass_dialogs.torsion(0, 1)),
        ('Компас: поиск конформеров', window.compass_dialogs.conformers),
        ('Компас: путь реакции', window.compass_dialogs.path),
        ('Компас: моменты инерции', window.structure_tool.show_inertia),
        ('Компас: статистика атомов', window.structure_tool.show_statistics),
        ('Компас: масса', window.structure_tool.show_masses),
        ('Компас: выделить в области', window.structure_tool.select_in_box),
        ('Компас: выделить по номерам', window.structure_tool.select_by_numbers),
        ('выделение', selected(0)),
        ('Компас: сменить элемент', window.structure_tool.set_selected_element),
        ('Компас: свои подписи', window.edit_custom_labels),
        ('Компас: сохранить фрагмент', window.fragment_tool.save_selection_as_fragment),
        ('Компас: молекула по SMILES', window.opening_tool.molecule_from_smiles),
        ('Компас: сохранить схему', window.scheme_tool.save_scheme),
        ('Компас: меню атома', lambda: window.model_menu_tool.atom_menu(0, QPoint(300, 300))),
        ('Компас: меню связи', lambda: window.model_menu_tool.bond_menu(0, 1, QPoint(300, 300))),
        ('Компас: меню снимка', window.picture_tool.snapshot_menu),
        ('Компас: меню ограничений', window.constraint_tool.menu),
        ('Компас: меню симметрии', window.symmetry_tool.symmetry_menu),
        ('Компас: ошибка', lambda: window.error('Пример сообщения: файл не прочитан — неизвестный формат.')),
        ('Компас: заменить структуру?', lambda: (setattr(window, 'dirty', True), type(window).confirm_replace(window),
                                                 setattr(window, 'dirty', False))),
        ('Компас: кристалл', lambda: window.crystal_tool.open_crystal_text((examples / '10-crystals' / 'CsCl.cif').read_text(encoding='utf-8'),
                                                             'CsCl.cif')),
        ('Компас: молекула', molecule),
    ]
    # the menus of the menu bar — not on macOS: there the system draws them in its own bar (they cannot be photographed
    # and stayed open until a click)
    for action in ([] if sys.platform == 'darwin' else window.menuBar().actions()):
        menu = action.menu()
        if menu is not None:
            plan.append((f'Меню «{action.text()}»', lambda m=menu: m.exec()))
            for sub in menu.actions():
                if sub.menu() is not None:
                    plan.append((f'Меню «{action.text()} → {sub.text()}»', lambda m=sub.menu(): m.exec()))
    plan += [
        ('Секстант', lambda: window.navigate(1)),
        ('Секстант: дополнительные настройки', window.show_options),
        ('Секстант: метод', lambda: window.method_picker.open_menu()),
        ('Секстант: базис', lambda: window.basis_picker.open_menu()),
        ('Секстант: программа', combo(window.program)),
        ('Секстант: задача', combo(window.task)),
        ('Секстант: растворитель', combo(window.solvent)),
        ('Секстант: сервер', window.run_tool.edit_server),
        ('Секстант: история расчётов', window.run_tool.show_history),
        ('Секстант: очередь', lambda: BatchDialog(window, 'Конформеры: 5 · CREST', [(f'Конформер {k}', d) for k, d in
                                                                         enumerate((0.0, 0.4, 1.8, 2.9, 4.6), 1)]).exec()),
        ('Секстант: установка программ', lambda: window.run_tool.install_tools_dialog(('xtb', 'crest'))),
        ('Секстант: проверка входного файла', lambda: window.input_tool.confirm_input_problems(
            [type('P', (), {'line': 4, 'text': 'незакрытый блок %scf'})(),
             type('P', (), {'line': 9, 'text': 'в строке атома не три числа'})()])),
        ('Секстант: число процессов на сервере', lambda: QInputDialog.getInt(
            window, 'Расчёт на сервере', 'cluster: 64 ядра, свободно 48.\nСколько процессов ORCA?', 8, 1, 64)),
        ('Секстант: пароль', lambda: QInputDialog.getText(window, 'Вход на сервер', 'Пароль student@10.0.0.5:',
                                                          QLineEdit.EchoMode.Password)),
        ('Спектр: результат', lambda: window.opening_tool.open_example_path(str(examples / '4-vibrations' /
                                                                  'divinylbenzene_freq_psi4.out'))),
        ('Спектр: орбитали', lambda: window.open_orbitals_text((examples / '6-orbitals' / 'water_gamess.molden')
                                                               .read_text(encoding='utf-8'), 'water_gamess.molden')),
        ('Спектр: анализ ЭП', lambda: window.orbitals_dialog.density_analysis()),
        ('Спектр: окно CUBE', window.demo_cube),
        ('Спектр: диаграмма реакции', window.reaction_diagram),
        ('Спектр: ввести энергию', lambda: window.reaction_window.type_in()),
        ('Спектр: тема', combo(window.theme)),
    ]
    return plan


def write_index():
    rows = []
    for theme in ('light', 'dark'):
        rows.append(f'<h2>{"Светлая" if theme == "light" else "Тёмная"} тема</h2><div class="grid">')
        for t, label, name, title in state['shots']:
            if t == theme:
                rows.append(f'<figure><img src="{name}"><figcaption>{label}</figcaption></figure>')
        rows.append('</div>')
    errors = ''.join(f'<pre>{e}</pre>' for e in state['errors'])
    (OUT / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>Окна «Азимута»</title><style>body{font-family:sans-serif;'
        'background:#f5f6f8;margin:24px}.grid{display:flex;flex-wrap:wrap;gap:16px}figure{margin:0;background:white;'
        'padding:8px;border-radius:10px;max-width:520px}img{max-width:500px;display:block}figcaption{font-size:12px;'
        'color:#5b6474;margin-top:6px}</style><h1>Окна «Азимута»</h1>' + ''.join(rows)
        + (f'<h2>Не открылись</h2>{errors}' if errors else ''), encoding='utf-8')
    (OUT / 'errors.txt').write_text('\n'.join(state['errors']) or 'нет', encoding='utf-8')


def main():
    global app
    from azimuth.app import STYLE, Studio

    OUT.mkdir(exist_ok=True)
    for old in OUT.glob('*.png'):
        old.unlink()
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(STYLE)
    try:
        from azimuth import qt_language

        qt_language.install('ru')
    except Exception:  # noqa: BLE001
        pass
    window = Studio(example=True, probe_machine=False)
    window.resize(1440, 900)
    window.show()
    settle(20)
    install_fakes()
    for index, theme in enumerate(('light', 'dark')):
        state['theme'] = theme
        window.theme.setCurrentIndex(index)
        settle(10)
        for name, action in scenes(window):
            scene(name, action, window)
    write_index()
    print(f'Снимков: {len(state["shots"])}; не открылись: {len(state["errors"])}. Папка: {OUT}')
    QTimer.singleShot(0, app.quit)
    window.dirty = False
    for doc in getattr(window, 'documents', ()):
        doc.dirty = False
    os._exit(0)  # no «save changes?» at the end


if __name__ == '__main__':
    main()

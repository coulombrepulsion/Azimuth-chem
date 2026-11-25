"""Compass: standard views, the Z-matrix editor, SVG / PDF pictures, files dropped on the window.

§1 PURPOSE
    Standard views look along an axis of the coordinate frame, along a selected bond, or at the plane of
    three selected atoms. The Z-matrix editor changes bond lengths, angles and dihedrals as numbers and
    shows the result at once; the structure is put back in its place (the Z-matrix itself starts at the
    origin). SVG and PDF keep labels, measurements and lines as vectors for a paper or a slide.
§2 ALGORITHM
    look_along: viewer.look_along(direction, right) — x of the screen along `right` without its part along
    the line of sight. Bond: direction b − a, right — a perpendicular helper. Plane of i, j, k: direction
    (j − i) × (k − i), right j − i. Editor: rows of zmatrix.build; a change of a number → to_cartesian →
    Kabsch rotation and shift (SVD, det = +1) onto the structure before the edit, all atoms weighted equally
    → shown without history; «Готово» — one undoable change with the bonds of the structure, «Отмена» /
    closing — the structure before. A row with a linear angle (0 or 180°) before a dihedral, a non-number or
    a length ≤ 0 shows the message and keeps the last valid picture. Drop: the first local file of the drop
    opens as with «Файл → Открыть пример…» (a result goes to the steps drawer or to Spectrum, a structure
    or a CIF to Compass, a fragments .json to «Мои фрагменты»); with Spectrum on screen a result stays there.
§3 APPLICATIONS
    «Вид → Стандартный вид», «Правка → Редактор Z-матрицы…», the «Снимок» menu (SVG, PDF), Studio.dropEvent.
§4 SPECIFICATION
    standard_view(kind) -> bool, kind ∈ {'x', 'y', 'z', 'bond', 'plane', 'best'}; aligned(new, reference) ->
    Molecule; ZMatrixWindow(owner): rows(), apply(), commit(), cancel(), save(path=None) («Сохранить…» — the
    Z-matrix to a text file); save_document(suffix, path=None);
    drop_paths(paths) -> the path opened or None.
§5 PROCEDURES - below.
§6 NOTES
    The model in SVG/PDF is an image (the renderer shades every pixel, raster.py) at 4 × the resolution of
    the field; everything drawn over it is vector.
§7 TESTS
    tests/test_gui.py::test_standard_views_zmatrix_editor_and_documents.
§8' ROBUSTNESS
    No structure, a missing selection: a message, nothing changes.
"""

from dataclasses import replace
from pathlib import Path

import numpy as np
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMenu,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from modules.compass.chemistry import zmatrix
from azimuth.core import Atom
from azimuth.i18n import tr
from azimuth.ui import smooth

HEADERS = ('Атом', '№', 'r, Å', '№', '∠, °', '№', 'φ, °')


def aligned(new, reference):
    """new moved and turned (proper rotation) onto reference, atom by atom."""
    x = np.array([a.position for a in new.atoms], float)
    y = np.array([a.position for a in reference.atoms], float)
    xc, yc = x.mean(0), y.mean(0)
    if len(x) > 1:
        u, _, vt = np.linalg.svd((x - xc).T @ (y - yc))
        d = np.eye(3)
        d[2, 2] = 1.0 if np.linalg.det(u @ vt) >= 0 else -1.0
        rotation = u @ d @ vt
    else:
        rotation = np.eye(3)
    moved = (x - xc) @ rotation + yc
    return replace(new, atoms=tuple(Atom(a.symbol, *map(float, p)) for a, p in zip(new.atoms, moved)))


class ZMatrixWindow(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr('Редактор Z-матрицы'))
        self.start = owner.coordinate_tool.table_molecule()
        self.shown = self.start
        self._done = False
        rows = zmatrix.build(self.start)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr('Измените длины связей, углы и двугранные углы — модель меняется сразу. Номера атомов — с 1.')))
        self.table = QTableWidget(len(rows), len(HEADERS))
        self.table.setHorizontalHeaderLabels([tr(h) for h in HEADERS])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().setVisible(True)
        self._loading = True
        for i, row in enumerate(rows):
            symbol, a, r, b, th, c, ph = row
            cells = [symbol, a, r, b, th, c, ph]
            for j, value in enumerate(cells):
                if j == 0:
                    text = symbol
                elif value is None:
                    text = ''
                elif j in (1, 3, 5):
                    text = str(value + 1)
                else:
                    text = f'{value:.6f}' if j == 2 else f'{value:.4f}'
                item = QTableWidgetItem(text)
                if j in (0, 1, 3, 5) or value is None:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(i, j, item)
        self._loading = False
        self.table.cellChanged.connect(self.apply)
        layout.addWidget(self.table, 1)
        self.message = QLabel('')
        self.message.setObjectName('error')
        self.message.setWordWrap(True)
        self.message.hide()
        layout.addWidget(self.message)
        buttons = QHBoxLayout()
        # the Z-matrix as it stands in the
        # table, to a text file (zmatrix.text: the element, the atom and the length, the atom and the angle, the atom
        # and the dihedral; numbers of the atoms from 1) — the window stays open
        save = QPushButton(tr('Сохранить…'))
        save.setToolTip(tr('Сохранить Z-матрицу в текстовый файл'))
        save.clicked.connect(lambda *_: self.save())
        buttons.addWidget(save)
        buttons.addStretch(1)
        cancel = QPushButton(tr('Отмена'))
        cancel.clicked.connect(self.cancel)
        done = QPushButton(tr('Готово'))
        done.setDefault(True)
        done.clicked.connect(self.commit)
        buttons.addWidget(cancel)
        buttons.addWidget(done)
        layout.addLayout(buttons)
        self.resize(640, 420)
        self.finished.connect(lambda *_: self._restore())

    def rows(self):
        out = []
        for i in range(self.table.rowCount()):
            row = [self.table.item(i, 0).text()]
            for j in (1, 3, 5):
                ref, value = self.table.item(i, j).text(), self.table.item(i, j + 1).text()
                if not ref:
                    row += [None, None]
                    continue
                try:
                    number = float(value.replace(',', '.'))
                except ValueError as exc:
                    raise ValueError(tr(f'Строка {i + 1}: «{value}» — не число.')) from exc
                if not np.isfinite(number):
                    raise ValueError(tr(f'Строка {i + 1}: «{value}» — не число.'))
                if j == 1 and number <= 0:
                    raise ValueError(tr(f'Строка {i + 1}: длина связи должна быть больше нуля.'))
                if j == 3 and not 0 < number < 180 and i >= 2:
                    raise ValueError(tr(f'Строка {i + 1}: угол должен быть больше 0° и меньше 180°.'))
                row += [int(ref) - 1, number]
            out.append(tuple(row))
        return out

    def apply(self, *args):
        if self._loading:
            return None
        try:
            built = zmatrix.to_cartesian(self.rows(), self.start.title)
            result = aligned(replace(built, bonds=self.start.bonds), self.start)
        except (ValueError, IndexError, ZeroDivisionError) as exc:
            self.message.setText(str(exc))
            self.message.show()
            return None
        self.message.hide()
        self.shown = result
        self.owner.trajectory_tool.show_molecule(result)
        self.owner.viewer.update()
        return result

    def save(self, path=None):
        """The Z-matrix of the table to a file (a window asks where without path) → the path written, or None."""
        try:
            text = zmatrix.text(self.rows())
        except (ValueError, IndexError) as exc:
            self.message.setText(str(exc))
            self.message.show()
            return None
        if path is None:
            from PySide6.QtWidgets import QFileDialog

            name = (self.start.title or 'molecule').strip().replace('/', '_') or 'molecule'
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить Z-матрицу'), f'{name}.zmat',
                                                  tr('Z-матрица') + ' (*.zmat *.txt);;' + tr('Все файлы') + ' (*)')
            if not path:
                return None
        try:
            Path(path).write_text(text, encoding='utf-8')
        except OSError as exc:
            self.message.setText(tr('Не удалось сохранить файл: ') + str(exc))
            self.message.show()
            return None
        self.message.hide()
        self.owner.notify(tr('Z-матрица сохранена: ') + Path(path).name, 6000)
        return str(path)

    def commit(self):
        result = self.shown
        self.owner.trajectory_tool.show_molecule(self.start)
        if result.atoms != self.start.atoms:
            self.owner.model_menu_tool.edit_structure(result, tr('Геометрия изменена в редакторе Z-матрицы.'))
        self._done = True
        self.accept()

    def cancel(self):
        self.reject()

    def _restore(self):
        if not self._done:
            self.owner.trajectory_tool.show_molecule(self.start)
            self.owner.viewer.update()


VIEW_PANEL_WIDTH = 80  # px: the panel of the view (layout.py)
EDGE_GAP = 7  # px: the gap (6) and the line (1) between the panel and the column of buttons (one box)


class ViewTool:
    """Was the mixin ViewActions of the window; a part of its own — it reaches the window only through the names
    of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'browsing',
        'coordinate_tool',
        'engine_action',
        'error',
        'isVisible',
        'notify',
        'open_files_project',
        'open_output_path',
        'opening_tool',
        'preferences',
        'stack',
        'standard_view_menu',
        'view_panel',
        'view_panel_motion',
        'view_panel_toggle',
        'view_panel_edge',
        'view_panel_gap',
        'viewer',
        'zmatrix_window',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)

    # -- the panel of the view on the right folds away ------------------------------------------------------
    def view_panel_open(self):
        motion = getattr(self.w, 'view_panel_motion', None)
        if motion is not None:
            return motion.endValue() > 0
        return not self.w.view_panel.isHidden() and self.w.view_panel.width() > 0

    def _edge(self):
        return self.w.view_panel_edge if self.w.has('view_panel_edge') else None

    def _gap(self):
        return getattr(self.w, 'view_panel_gap', 0) if self.w.has('view_panel_gap') else 0

    def panel_full(self):
        """The width of the open panel — its buttons and the spacing from the field inside it."""
        return VIEW_PANEL_WIDTH + self._gap()

    def edge_full(self):
        """The width of the box of the line — the spacing after the panel, the gap and the line."""
        return self._gap() + EDGE_GAP

    def _view_panel_span(self):
        """The width of the panel and of the box of its line together."""
        edge = self._edge()
        panel = self.w.view_panel
        return (panel.width() if not panel.isHidden() else 0) + (edge.width() if edge is not None and not edge.isHidden() else 0)

    def _view_panel_step(self, width):
        """As project_navigation._project_slide_step — the layout and the field follow each step at once.
        Width is of the panel and the box of the line together — the panel goes first, then the box: the
        field comes up to the line and covers it (and back the other way)."""
        from azimuth.project_widgets import slide_log_start, slide_log_step

        panel = self.w.view_panel
        edge = self._edge()
        gap = self.edge_full() if edge is not None else 0
        inner, outer = max(0, width - gap), min(gap, width)
        if panel.width() == inner and (edge is None or edge.width() == outer):
            return
        started = slide_log_start()
        self.w.viewer.layout_motion()
        panel.setFixedWidth(inner)
        if edge is not None:
            edge.setFixedWidth(outer)
            edge.setVisible(outer > 0)
        holder = panel.parentWidget()
        if holder is not None and holder.layout() is not None:
            holder.layout().activate()
        slide_log_step(started, width)  # AZIMUTH_SLIDE_LOG — the steps of this panel too

    def set_view_panel_open(self, opened, animate=True):
        """The panel of the view (turns, shifts, zoom) comes out or folds (SLIDE_MS, the curves of the drawer); the
        chevron points where it goes; the choice is kept in the preferences."""
        from PySide6.QtCore import QEasingCurve, QVariantAnimation

        from modules.compass.panels.trajectory_drawer import SLIDE_MS

        panel = self.w.view_panel
        target = self.panel_full() if opened else 0
        # one sign both ways
        self.w.view_panel_toggle.setToolTip(tr('Свернуть панель вида') if opened else tr('Показать панель вида'))
        if self.w.has('preferences'):
            self.w.preferences.setValue('view_panel_open', bool(opened))
        motion = getattr(self.w, 'view_panel_motion', None)
        if motion is not None:
            motion.stop()
            self.w.view_panel_motion = None
        edge = self.w.view_panel_edge if self.w.has('view_panel_edge') else None
        if opened:
            if panel.isHidden():  # from nothing — the box of the line comes out first, then the panel
                panel.setFixedWidth(0)
                if edge is not None:
                    edge.setFixedWidth(0)
            panel.show()
            if edge is not None:
                edge.show()
        viewer = self.w.viewer
        whole = target + (self.edge_full() if opened and edge is not None else 0)
        if not animate or not self.w.isVisible() or self._view_panel_span() == whole:
            panel.setFixedWidth(target)
            panel.setVisible(bool(target))
            if edge is not None:
                edge.setFixedWidth(self.edge_full())
                edge.setVisible(bool(target))
            if hasattr(viewer, 'end_glide'):
                viewer.end_glide()
            return
        if hasattr(viewer, 'begin_glide'):
            viewer.begin_glide()  # as the panel of the project molecules — the field slides as one picture
        motion = QVariantAnimation(self.w.widget)
        motion.setDuration(SLIDE_MS)
        # out the same smooth curve as back, its steps no larger than 1.5 times the mean
        motion.setEasingCurve(QEasingCurve.Type.InOutCubic)
        motion.setStartValue(self._view_panel_span())
        motion.setEndValue(whole)
        # its 80 px in whole pixels — in
        # even ones the slow start and end of the curve stood still a frame and then jumped two pixels
        motion.valueChanged.connect(lambda value: self._view_panel_step(int(round(value))))

        from azimuth.project_widgets import slide_profile_begin, slide_profile_end

        from azimuth.ui import freeze_ornaments

        freeze_ornaments(self.w.widget)  # the scales of the window a picture while the panel slides
        profiled = slide_profile_begin()  # AZIMUTH_SLIDE_LOG

        def done():
            slide_profile_end(profiled, 'панель вида')
            freeze_ornaments(self.w.widget, False)
            panel.setFixedWidth(target)
            panel.setVisible(bool(target))
            if edge is not None:
                edge.setFixedWidth(self.edge_full())
                edge.setVisible(bool(target))
            if self.w.view_panel_motion is motion:
                self.w.view_panel_motion = None
                if hasattr(viewer, 'end_glide'):
                    holder = panel.parentWidget()
                    if holder is not None and holder.layout() is not None:
                        holder.layout().activate()
                    viewer.end_glide()

        motion.finished.connect(done)
        self.w.view_panel_motion = motion
        motion.start()

    def build_view_actions(self):
        menu = smooth(QMenu(tr('Стандартный вид'), self.w.widget))
        for kind, title in (
            ('x', 'Вдоль оси x'),
            ('y', 'Вдоль оси y'),
            ('z', 'Вдоль оси z'),
            (None, None),
            ('bond', 'Вдоль выбранной связи (2 атома)'),
            ('plane', 'На плоскость трёх выбранных атомов'),
            # «Наилучший вид» left out, «Вид → Лучший ракурс» stays (standard_view('best') too)
        ):
            if kind is None:
                menu.addSeparator()
                continue
            menu.addAction(tr(title)).triggered.connect(lambda checked=False, k=kind: self.standard_view(k))
        self.w.standard_view_menu = menu
        return menu

    def standard_view(self, kind):
        viewer = self.w.viewer
        mol = viewer.molecule
        if not mol or not mol.atoms:
            return False
        if kind == 'best':
            viewer.best_view()
            return True
        axes = {'x': ((1, 0, 0), (0, 1, 0)), 'y': ((0, 1, 0), (0, 0, 1)), 'z': ((0, 0, 1), (1, 0, 0))}
        if kind in axes:
            return viewer.look_along(*axes[kind])
        chosen = list(viewer.selected)
        p = [mol.atoms[i].position for i in chosen if 0 <= i < len(mol.atoms)]
        sub = lambda u, v: tuple(u[k] - v[k] for k in range(3))  # noqa: E731
        if kind == 'bond':
            if len(p) != 2:
                self.w.notify(tr('Выделите два атома: смотреть будем вдоль линии между ними.'), 8000)
                return False
            return viewer.look_along(sub(p[1], p[0]))
        if kind == 'plane':
            if len(p) != 3:
                self.w.notify(tr('Выделите три атома: плоскость через них встанет в плоскость экрана.'), 8000)
                return False
            u, v = sub(p[1], p[0]), sub(p[2], p[0])
            normal = (u[1] * v[2] - u[2] * v[1], u[2] * v[0] - u[0] * v[2], u[0] * v[1] - u[1] * v[0])
            if not viewer.look_along(normal, u):
                self.w.notify(tr('Три атома на одной прямой: плоскость не определена.'), 8000)
                return False
            return True
        raise ValueError(kind)

    def open_zmatrix_editor(self):
        if getattr(self.w, 'browsing', False):
            self.w.notify(tr('Сначала закройте шаги оптимизации (☰).'), 6000)
            return None
        mol = self.w.coordinate_tool.table_molecule()
        if len(mol.atoms) < 2:
            self.w.notify(tr('Для Z-матрицы нужны хотя бы два атома.'), 6000)
            return None
        old = getattr(self.w, 'zmatrix_window', None)
        if old is not None and old.isVisible():
            old.cancel()
        try:
            window = ZMatrixWindow(self.w.widget)
        except ValueError as exc:
            self.w.error(exc)
            return None
        self.w.zmatrix_window = window
        window.show()
        return window

    def save_document(self, suffix, path=None):
        """The model as SVG or PDF; returns the path or None."""
        from azimuth.ui import ask_picture_path
        from datetime import datetime

        try:
            if path is None:
                name = 'Azimuth-' + datetime.now().strftime('%Y%m%d-%H%M%S')
                path = ask_picture_path(self.w.widget, tr('Сохранить рисунок'), name, suffix, getattr(self.w, 'preferences', None))
                if path is None:
                    return None
            self.w.viewer.export_document(path)
            self.w.notify(tr('Рисунок сохранён: ') + str(path), 12000)
            return Path(path)
        except (OSError, ValueError) as exc:
            self.w.error(exc)
            return None

    def drop_paths(self, paths):
        files = [Path(p) for p in paths if Path(p).is_file()]
        if not files:
            return None
        if all(self.w.opening_tool.opens_as_project(str(p)) for p in files):  # not a trajectory
            return self.w.open_files_project(files, append=True)
        path = str(files[0])
        if len(files) > 1:
            self.w.notify(tr(f'Открыт первый из файлов: {files[0].name} (из {len(files)}).'), 8000)
        if self.w.stack.currentIndex() == 2 and self.w.opening_tool.file_kind(path) in ('output', 'gaussian_log'):
            self.w.open_output_path(path)  # Spectrum on screen: the result stays there
        else:
            self.w.opening_tool.open_example_path(path)
        return path

    # -- who draws the atoms and bonds («Вид → Трёхмерная графика VTK (проба)») -------------------
    ENGINE_KEY = 'compass_engine'

    def set_engine(self, on, quiet=False):
        """Draw the model with VTK (on) or with the built-in renderer; the choice is remembered. Turning VTK on
        first checks that it draws off screen here; if not, the built-in renderer stays and a message says why."""
        engine = 'raster'
        if on:
            from modules.compass.view import vtk_model

            ok, why = vtk_model.available()
            if ok:
                engine = 'vtk'
            elif not quiet:
                self.w.notify(tr('Трёхмерная графика VTK недоступна: ') + why, 12000)
        self.w.viewer.engine = engine
        self.w.viewer._model_image = None
        # VTK draws straight into the window where it can (modules/compass/view/vtk_view.py); else the picture
        # is drawn in a hidden VTK window and copied, as in 0.51
        native = self.w.viewer.set_native(engine == 'vtk')
        from modules.compass.view import vtk_view

        error = getattr(self.w.viewer, 'native_error', '')
        if engine == 'vtk' and not native and not quiet and 'restart:' in error:
            self.w.notify(tr('Трёхмерная графика VTK включена; прямо в окне она начнёт рисовать после перезапуска Азимута.'), 12000)
        elif engine == 'vtk' and not native and not quiet and vtk_view.ENABLED:
            self.w.notify(tr('VTK рисует через скрытое окно (прямо в окне не получилось: ') + getattr(self.w.viewer, 'native_error', '') + ')', 12000)
        if self.w.has('preferences'):
            self.w.preferences.setValue(self.ENGINE_KEY, engine)
        action = getattr(self.w, 'engine_action', None)
        if action is not None and action.isChecked() != (engine == 'vtk'):
            action.blockSignals(True)
            action.setChecked(engine == 'vtk')
            action.blockSignals(False)
        self.w.viewer.update()
        return engine == 'vtk'

    def engine_failed(self, message):
        """VTK failed while drawing: the view already went back to the built-in renderer."""
        self.set_engine(False, quiet=True)
        self.w.notify(tr('Трёхмерная графика VTK перестала рисовать, Компас вернулся к встроенной: ') + message, 12000)

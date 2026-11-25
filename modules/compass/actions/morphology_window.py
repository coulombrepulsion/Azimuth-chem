"""«Кристалл → Форма кристалла (BFDH)…»: the shape of the crystal by the spacings of its planes
(crystal_morphology), turned with the mouse, its forms {hkl} in a table.

§1 PURPOSE
    BFDH morphology, as in Mercury: why one crystal grows as a
    needle and another as a plate — from the cell and the space group alone.
§4 SPECIFICATION
    show(studio) -> MorphologyWindow | None; MorphologyWindow(parent, crystal, title); ShapeView.along(k) — look along
    the edge k of the cell; save_picture(path).
§7 TESTS tests/gui/test_gui_files.py::test_the_shape_of_a_crystal.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen, QPolygonF
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.actions.brillouin_window import _rotation
from modules.compass.chemistry import crystal_morphology as cm

COLOURS = ('#6ea2f0', '#e0a030', '#59a14f', '#e15759', '#b07aa1', '#76b7b2', '#9c755f', '#edc948')


class ShapeView(QWidget):
    def __init__(self, shape):
        import numpy as np

        super().__init__()
        self.shape = shape
        self.rotation = _rotation(-0.45, 0.6)
        self.last = None
        self.setMinimumSize(380, 380)
        p = np.array(shape.vertices)
        self.extent = float(np.linalg.norm(p, axis=1).max()) if len(p) else 1.0
        self.colour = {}
        for k, form in enumerate(shape.forms):
            for f in shape.faces:
                if abs(f.d - form.d) < 1e-6 and f.hkl not in self.colour:
                    self.colour[f.hkl] = COLOURS[k % len(COLOURS)]

    def turn(self, rotation):
        import numpy as np

        self.rotation = np.array(rotation, dtype=float)
        self.update()

    def along(self, k):
        import numpy as np

        axis = np.array(self.shape.cell[k], dtype=float)
        z = axis / np.linalg.norm(axis)
        helper = np.array((0, 0, 1.0)) if abs(z[2]) < 0.9 else np.array((0, 1.0, 0))
        x = np.cross(helper, z)
        x /= np.linalg.norm(x)
        self.turn(np.array([x, np.cross(z, x), z]))

    def mousePressEvent(self, event):
        self.last = event.position()

    def mouseMoveEvent(self, event):
        if self.last is None:
            return
        d = event.position() - self.last
        self.last = event.position()
        self.turn(_rotation(d.y() * 0.01, d.x() * 0.01) @ self.rotation)

    def mouseReleaseEvent(self, event):
        self.last = None

    def _screen(self, v):
        import numpy as np

        r = self.rotation @ np.array(v, dtype=float)
        scale = 0.4 * min(self.width(), self.height()) / self.extent
        return QPointF(self.width() / 2 + r[0] * scale, self.height() / 2 - r[1] * scale)

    def paintEvent(self, event):
        import numpy as np

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().windowText().color()
        vertices = np.array(self.shape.vertices)
        light = np.array((-0.35, 0.45, 0.82))
        light /= np.linalg.norm(light)
        grey = QColor('#8a96a3')
        p.setFont(QFont(p.font().family(), 9))
        for k, a in enumerate(self.shape.cell):  # the edges of the cell, behind the crystal
            tip = np.array(a) / np.linalg.norm(a) * self.extent * 1.35
            p.setPen(QPen(grey, 1.0, Qt.PenStyle.DotLine))
            p.drawLine(self._screen((0, 0, 0)), self._screen(tip))
            p.drawText(self._screen(tip) + QPointF(3, -3), 'abc'[k])
        bold = QFont(p.font().family(), 9)
        bold.setBold(True)
        for face in self.shape.faces:
            normal = self.rotation @ np.array(face.normal)
            if normal[2] <= 0:
                continue
            shade = 0.55 + 0.45 * max(0.0, float(normal @ light))
            colour = QColor(self.colour.get(face.hkl, COLOURS[0]))
            colour = QColor.fromHsvF(colour.hsvHueF(), colour.hsvSaturationF() * 0.8, min(1.0, colour.valueF() * shade))
            p.setBrush(colour)
            p.setPen(QPen(ink, 1.3))
            p.drawPolygon(QPolygonF([self._screen(vertices[m]) for m in face.vertices]))
            if face.area / max(f.area for f in self.shape.faces) > 0.08 and normal[2] > 0.25:
                centre = self._screen(vertices[face.vertices].mean(axis=0))
                p.setFont(bold)
                p.setPen(QColor('#10151c'))
                p.drawText(QRectF(centre.x() - 50, centre.y() - 8, 100, 16), Qt.AlignmentFlag.AlignCenter,
                           cm.hkl_text(face.hkl))
        p.end()


class MorphologyWindow(QDialog):
    def __init__(self, parent, crystal, title=''):
        super().__init__(parent)
        self.shape = cm.morphology(crystal)
        s = self.shape
        self.setWindowTitle(tr('Форма кристалла (BFDH) · ') + (title or crystal.title or 'CIF'))
        layout = QHBoxLayout(self)
        self.view = ShapeView(s)
        layout.addWidget(self.view, 3)
        side = QVBoxLayout()
        layout.addLayout(side, 2)
        main = s.forms[0] if s.forms else None
        self.summary = QLabel(tr('Граней: {}; главная форма {} — {} % поверхности.').format(
            len(s.faces), '{' + cm.hkl_text(main.hkl) + '}', f'{100 * main.share:.0f}') if main else '')
        self.summary.setWordWrap(True)
        side.addWidget(self.summary)
        self.table = QTableWidget(len(s.forms), 4)
        self.table.setHorizontalHeaderLabels([tr('Форма'), 'd, Å', tr('Граней'), tr('Доля поверхности')])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        for r, form in enumerate(s.forms):
            name = '{' + cm.hkl_text(form.hkl) + '}'
            if form.n > 1:
                name += tr(' (как {})').format(cm.hkl_text(tuple(form.n * x for x in form.hkl)))
            cells = (name, f'{form.d:.3f}', str(form.faces), f'{100 * form.share:.1f} %')
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 0:
                    item.setForeground(QColor(self.view.colour.get(next(
                        (f.hkl for f in s.faces if abs(f.d - form.d) < 1e-6), form.hkl), COLOURS[0])))
                self.table.setItem(r, c, item)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        side.addWidget(self.table, 1)
        note = QLabel(tr('Закон Браве — Фриделя — Доннея — Харкера: грани кристалла — плоскости с наибольшим '
                         'межплоскостным расстоянием d, они растут медленнее всех; грань стоит на расстоянии 1/d от '
                         'центра. Погасания группы (центрировка, винтовые оси, плоскости скольжения) делят d: грань '
                         '{100} гранецентрированной решётки растёт как (200). Форма — по одной геометрии решётки, без '
                         'энергий связей и растворителя.'))
        note.setWordWrap(True)
        side.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Смотреть вдоль:')))
        self.axes = []
        for k in range(3):
            button = QPushButton('abc'[k])
            button.clicked.connect(lambda checked=False, k=k: self.view.along(k))
            self.axes.append(button)
            row.addWidget(button)
        row.addStretch(1)
        side.addLayout(row)
        bottom = QHBoxLayout()
        bottom.addWidget(action_button(tr('Сохранить картинку…'), self.save_picture, 'save'))
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        side.addLayout(bottom)
        self.resize(900, 520)

    def save_picture(self, path=None):
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить картинку'), 'morphology.png', 'PNG (*.png)')
        if path:
            self.view.grab().save(path)
        return path


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    window = MorphologyWindow(studio if isinstance(studio, QWidget) else None, crystal)
    studio._morphology_window = window
    window.show()
    return window

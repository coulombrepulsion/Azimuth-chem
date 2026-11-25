"""«Кристалл → Зона Бриллюэна…»: the first Brillouin zone of the crystal shown, its points of high symmetry
and the path of its band structure (modules/compass/chemistry/brillouin.py), turned with the mouse.

§1 PURPOSE
    The Brillouin zone of the crystal with the path of the bands: where the letters under the bands of Spectrum («Зоны»)
    are. The edges in front are solid, those behind dashed; the path in
    blue, Γ in the centre; b₁, b₂, b₃ of the cell of the file in grey.
§4 SPECIFICATION
    show(studio) -> BrillouinWindow | None; BrillouinWindow(parent, crystal, title); ZoneView.turn(rotation 3 × 3),
    ZoneView.along(k) — look along b_k.
§7 TESTS tests/gui/test_gui_files.py::test_brillouin_zone_window.
"""

from math import cos, sin

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import brillouin

KINDS = {'cP': 'простая кубическая решётка', 'cF': 'гранецентрированная кубическая решётка',
         'cI': 'объёмноцентрированная кубическая решётка', 'hP': 'гексагональная решётка',
         'tP': 'простая тетрагональная решётка', 'oP': 'простая ромбическая решётка',
         'other': 'общий путь вдоль осей обратной решётки (для этой решётки нет таблицы точек)'}
BLUE, BLUE_DARK = '#2a62b8', '#6ea2f0'


def _rotation(ax, ay):
    import numpy as np

    rx = np.array([[1, 0, 0], [0, cos(ax), -sin(ax)], [0, sin(ax), cos(ax)]])
    ry = np.array([[cos(ay), 0, sin(ay)], [0, 1, 0], [-sin(ay), 0, cos(ay)]])
    return ry @ rx


class ZoneView(QWidget):
    def __init__(self, zone):
        import numpy as np

        super().__init__()
        self.zone = zone
        self.rotation = _rotation(-0.35, 0.55)
        self.last = None
        self.setMinimumSize(380, 380)
        p = np.array(zone.vertices)
        self.extent = float(np.linalg.norm(p, axis=1).max()) if len(p) else 1.0

    def turn(self, rotation):
        import numpy as np

        self.rotation = np.array(rotation, dtype=float)
        self.update()

    def along(self, k):
        """Look along b_k of the cell of the file (b_k towards the viewer)."""
        import numpy as np

        axis = np.array(self.zone.conventional[k], dtype=float)
        z = axis / np.linalg.norm(axis)
        helper = np.array((0, 0, 1.0)) if abs(z[2]) < 0.9 else np.array((0, 1.0, 0))
        x = np.cross(helper, z)
        x /= np.linalg.norm(x)
        y = np.cross(z, x)
        self.turn(np.array([x, y, z]))

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
        scale = 0.38 * min(self.width(), self.height()) / self.extent
        return QPointF(self.width() / 2 + r[0] * scale, self.height() / 2 - r[1] * scale), float(r[2])

    def paintEvent(self, event):
        import numpy as np

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().windowText().color()
        dark = ink.lightness() > 128
        faint = QColor(ink)
        faint.setAlpha(90)
        z = self.zone
        vertices = np.array(z.vertices)
        front = set()
        for face in z.faces:
            c = vertices[face].mean(axis=0)
            if (self.rotation @ c)[2] > 0:  # the outward normal of a face of a zone centred on Γ is along its centre
                for a, b in zip(face, face[1:] + face[:1]):
                    front.add((min(a, b), max(a, b)))
        edges = set()
        for face in z.faces:
            for a, b in zip(face, face[1:] + face[:1]):
                edges.add((min(a, b), max(a, b)))
        for a, b in sorted(edges):
            shown = (a, b) in front
            p.setPen(QPen(ink if shown else faint, 1.4 if shown else 1.0,
                          Qt.PenStyle.SolidLine if shown else Qt.PenStyle.DashLine))
            p.drawLine(self._screen(vertices[a])[0], self._screen(vertices[b])[0])
        grey = QColor('#8a96a3')
        p.setFont(QFont(p.font().family(), 9))
        for k, b in enumerate(z.conventional):
            tip = np.array(b) * 0.5 * self.extent / np.linalg.norm(b) * 1.6
            p.setPen(QPen(grey, 1.0, Qt.PenStyle.DotLine))
            p.drawLine(self._screen((0, 0, 0))[0], self._screen(tip)[0])
            p.drawText(self._screen(tip)[0] + QPointF(3, -3), 'b' + '₁₂₃'[k])
        blue = QColor(BLUE_DARK if dark else BLUE)
        p.setPen(QPen(blue, 2.4))
        for run in z.runs:
            for a, b in zip(run, run[1:]):
                p.drawLine(self._screen(z.points[a])[0], self._screen(z.points[b])[0])
        bold = QFont(p.font().family(), 11)
        bold.setBold(True)
        p.setFont(bold)
        for label, point in z.points.items():
            at, depth = self._screen(point)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(blue)
            p.drawEllipse(at, 3.5, 3.5)
            p.setPen(ink)
            p.drawText(at + QPointF(6, -6), label)
        p.end()


class BrillouinWindow(QDialog):
    def __init__(self, parent, crystal, title=''):
        import numpy as np

        super().__init__(parent)
        self.zone = brillouin.zone(crystal)
        z = self.zone
        self.setWindowTitle(tr('Зона Бриллюэна · ') + (title or crystal.title or 'CIF'))
        layout = QHBoxLayout(self)
        self.view = ZoneView(z)
        layout.addWidget(self.view, 3)
        side = QVBoxLayout()
        layout.addLayout(side, 2)
        self.summary = QLabel(tr('{}. Путь зон: {}. Объём зоны {} Å⁻³ = (2π)³ / V примитивной ячейки.').format(
            tr(KINDS[z.kind]).capitalize(), brillouin.describe(z), f'{z.volume:.4f}'))
        self.summary.setWordWrap(True)
        side.addWidget(self.summary)
        self.table = QTableWidget(len(z.points), 3)
        self.table.setHorizontalHeaderLabels([tr('Точка'), tr('Доли b₁, b₂, b₃'), '|k|, Å⁻¹'])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        inverse = np.linalg.inv(np.array(z.conventional))
        for r, (label, point) in enumerate(z.points.items()):
            f = np.array(point) @ inverse
            cells = (label, ', '.join(f'{x:.3f}'.rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0' for x in f),
                     f'{np.linalg.norm(point):.3f}')
            for c, text in enumerate(cells):
                self.table.setItem(r, c, QTableWidgetItem(text))
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        side.addWidget(self.table, 1)
        note = QLabel(tr('Первая зона Бриллюэна — ячейка Вигнера — Зейтца обратной решётки примитивной ячейки: точки, '
                         'ближайшие к Γ. Буквы и путь — как под зонами в Спектре (Setyawan, Curtarolo, 2010); доли — '
                         'в векторах обратной решётки ячейки файла. Поверните зону мышью; задние рёбра — штрихом.'))
        note.setWordWrap(True)
        side.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Смотреть вдоль:')))
        self.axes = []
        for k in range(3):
            button = QPushButton('b' + '₁₂₃'[k])
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
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить картинку'), 'brillouin.png', 'PNG (*.png)')
        if path:
            self.view.grab().save(path)
        return path


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    window = BrillouinWindow(studio if isinstance(studio, QWidget) else None, crystal)
    studio._brillouin_window = window
    window.show()
    return window

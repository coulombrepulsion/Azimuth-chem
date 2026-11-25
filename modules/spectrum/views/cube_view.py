"""Independent VTK viewer for scalar CUBE fields; no editor mutations."""

from pathlib import Path
import sys
from time import monotonic
from datetime import datetime
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QDoubleSpinBox,
    QPushButton,
    QCheckBox,
    QFileDialog,
    QApplication,
)
from modules.spectrum.readers.cube import read_cube, MAX_BYTES
from modules.compass.chemistry.builder import connections
from modules.compass.view.viewer import COLORS
from azimuth.icons import iconify
from azimuth.i18n import tr
from azimuth import quill  # the messages with Quill
from azimuth.ui import ask_picture_path


def surface(cube, dataset, level):
    if not np.isfinite(level) or level == 0:
        raise ValueError(tr('Уровень должен быть конечным и ненулевым.'))
    image = vtk.vtkImageData()
    image.SetDimensions(*cube.values.shape[:3])
    image.GetPointData().SetScalars(
        numpy_to_vtk(cube.values[..., dataset].astype(np.float32).ravel(order='F'), deep=True)
    )
    contour = vtk.vtkFlyingEdges3D()
    contour.SetInputData(image)
    contour.SetValue(0, level)
    contour.ComputeNormalsOff()
    contour.Update()
    matrix = vtk.vtkMatrix4x4()
    for row in range(3):
        for col in range(3):
            matrix.SetElement(row, col, float(cube.axes[col, row]))
        matrix.SetElement(row, 3, float(cube.origin[row]))
    transform = vtk.vtkTransform()
    transform.SetMatrix(matrix)
    converted = vtk.vtkTransformPolyDataFilter()
    converted.SetInputConnection(contour.GetOutputPort())
    converted.SetTransform(transform)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputConnection(converted.GetOutputPort())
    normals.ConsistencyOn()
    normals.AutoOrientNormalsOn()
    normals.SplittingOff()
    normals.Update()
    result = vtk.vtkPolyData()
    result.DeepCopy(normals.GetOutput())
    return result


def actor_for(data, color, opacity=1.0):
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(data)
    mapper.ScalarVisibilityOff()
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*color)
    actor.GetProperty().SetOpacity(opacity)
    actor.GetProperty().SetInterpolationToPhong()
    actor.GetProperty().SetSpecular(0.25)
    actor.GetProperty().SetSpecularPower(30)
    return actor


def rgb(hexcolor):
    return tuple(int(hexcolor[i : i + 2], 16) / 255 for i in (1, 3, 5))


class CubeInteractor(QVTKRenderWindowInteractor):
    """Break Qt 6.10+ / Cocoa render→expose feedback without changing VTK."""

    def paintEvent(self, event):
        if sys.platform == 'darwin' and monotonic() - getattr(self, '_paint_finished', 0) < 0.04:
            return
        super().paintEvent(event)
        self._paint_finished = monotonic()


class CubeDialog(QDialog):
    def __init__(self, parent=None, dark=False):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(tr('Азимут · CUBE · орбитали и плотность'))
        self.resize(1080, 760)
        self.cube = None
        self.surfaces = []
        self.atoms = []
        layout = QVBoxLayout(self)
        bar = QHBoxLayout()
        self.open_button = QPushButton(tr('Открыть CUBE…'))
        bar.addWidget(self.open_button)
        self.dataset = QComboBox()
        self.dataset.setToolTip(tr('Набор данных из CUBE; номера взяты из файла.'))
        bar.addWidget(self.dataset)
        self.kind = QComboBox()
        self.kind.addItems([tr('Два знака (орбиталь)'), tr('Один уровень (плотность)')])
        self.kind.setToolTip(tr('Тип поля задаётся пользователем: CUBE не всегда указывает его однозначно.'))
        bar.addWidget(self.kind)
        bar.addStretch()
        self.center = QPushButton()
        iconify(self.center, 'center', tr('Центровать 3D-вид'))
        bar.addWidget(self.center)
        self.capture = QPushButton()
        iconify(self.capture, 'camera', tr('Сохранить изображение 3D-окна'))
        bar.addWidget(self.capture)
        layout.addLayout(bar)
        settings = QHBoxLayout()
        settings.addWidget(QLabel(tr('Уровень')))
        self.level = QDoubleSpinBox()
        self.level.setDecimals(7)
        self.level.setRange(0.0000001, 1e9)
        self.level.setSingleStep(0.01)
        self.level.setValue(0.05)
        self.level.setKeyboardTracking(False)
        self.level.setToolTip(
            tr('Изоповерхность поля при значениях +уровень и −уровень. Значения и единицы поля сохраняются как в CUBE.')
        )
        settings.addWidget(self.level)
        settings.addWidget(QLabel(tr('Непрозрачность')))
        self.opacity = QDoubleSpinBox()
        self.opacity.setRange(0.05, 1)
        self.opacity.setSingleStep(0.05)
        self.opacity.setValue(0.65)
        self.opacity.setKeyboardTracking(False)
        settings.addWidget(self.opacity)
        self.show_atoms = QCheckBox(tr('Молекула'))
        self.show_atoms.setChecked(True)
        settings.addWidget(self.show_atoms)
        self.parallel = QCheckBox(tr('Без перспективы'))
        self.parallel.setChecked(True)
        settings.addWidget(self.parallel)
        self.legend = QLabel(tr('Синий: +   Красный: −'))
        settings.addStretch()
        settings.addWidget(self.legend)
        layout.addLayout(settings)
        self.info = QLabel()
        self.info.setTextFormat(Qt.TextFormat.PlainText)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        self.vtk_widget = CubeInteractor(self)
        self.vtk_widget.setMinimumSize(400, 300)
        layout.addWidget(self.vtk_widget, 1)
        self.vtk_widget.setToolTip(tr('ЛКМ — вращение; колёсико — масштаб; средняя кнопка или Shift + ЛКМ — сдвиг.'))
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetUseDepthPeeling(True)
        self.renderer.SetMaximumNumberOfPeels(100)
        self.renderer.SetOcclusionRatio(0.05)
        self.window = self.vtk_widget.GetRenderWindow()
        self.window.SetAlphaBitPlanes(1)
        self.window.SetMultiSamples(0)
        self.window.AddRenderer(self.renderer)
        self.renderer.GetActiveCamera().ParallelProjectionOn()
        self.vtk_widget.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
        self.vtk_widget.Initialize()
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.set_theme(dark, render=False)
        self.open_button.clicked.connect(self.open_file)
        self.dataset.currentIndexChanged.connect(self.rebuild)
        self.kind.currentIndexChanged.connect(self.rebuild)
        self.level.valueChanged.connect(self.rebuild)
        self.opacity.valueChanged.connect(self.change_opacity)
        self.show_atoms.toggled.connect(self.change_atoms)
        self.center.clicked.connect(self.center_view)
        self.capture.clicked.connect(self.save_image)
        self.parallel.toggled.connect(self.change_projection)

    def set_theme(self, dark, render=True):
        self.renderer.SetBackground(*rgb('#11151c' if dark else '#f5f6f8'))
        if render and self.isVisible():
            self.window.Render()

    def load_cube(self, cube):
        self.cube = cube
        self.renderer.RemoveAllViewProps()
        self.surfaces = []
        self.atoms = []
        self.dataset.blockSignals(True)
        self.dataset.clear()
        for idx in cube.ids:
            self.dataset.addItem(tr(f'Набор {idx}'))
        self.dataset.blockSignals(False)
        self.info.setText(
            tr(f'{cube.title}\nСетка: {" × ".join(map(str, cube.values.shape[:3]))} · Координаты: {cube.units}')
        )
        peak = float(np.max(np.abs(cube.values[..., 0])))
        self.level.blockSignals(True)
        self.level.setValue(max(1e-7, min(0.05, peak * 0.2)))
        self.level.blockSignals(False)
        for atom in cube.molecule.atoms:
            sphere = vtk.vtkSphereSource()
            sphere.SetCenter(*atom.position)
            sphere.SetRadius(0.16 if atom.symbol == 'H' else 0.24)
            sphere.SetThetaResolution(24)
            sphere.SetPhiResolution(20)
            sphere.Update()
            actor = actor_for(sphere.GetOutput(), rgb(COLORS.get(atom.symbol, '#9c80b7')))
            self.atoms.append(actor)
            self.renderer.AddActor(actor)
        for a, b, _ in connections(cube.molecule):
            line = vtk.vtkLineSource()
            line.SetPoint1(*cube.molecule.atoms[a].position)
            line.SetPoint2(*cube.molecule.atoms[b].position)
            tube = vtk.vtkTubeFilter()
            tube.SetInputConnection(line.GetOutputPort())
            tube.SetRadius(0.055)
            tube.SetNumberOfSides(12)
            tube.CappingOn()
            tube.Update()
            actor = actor_for(tube.GetOutput(), (0.5, 0.55, 0.6))
            self.atoms.append(actor)
            self.renderer.AddActor(actor)
        self.rebuild()
        self.change_atoms(self.show_atoms.isChecked())
        self.center_view()

    def rebuild(self, *args):
        if self.cube is None:
            return
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            level = self.level.value()
            dataset = self.dataset.currentIndex()
            data = self.cube.values[..., dataset]
            signs = (1, -1) if self.kind.currentIndex() == 0 else (1,)
            new = []
            for sign in signs:
                mesh = surface(self.cube, dataset, sign * level)
                if mesh.GetNumberOfPoints():
                    new.append(
                        actor_for(mesh, (0.2, 0.45, 0.9) if sign > 0 else (0.9, 0.25, 0.22), self.opacity.value())
                    )
            for actor in self.surfaces:
                self.renderer.RemoveActor(actor)
            self.surfaces = new
            for actor in new:
                self.renderer.AddActor(actor)
            self.legend.setText(tr('Синий: +   Красный: −') if len(signs) == 2 else tr('Синий: +уровень'))
            self.status.setText(
                tr(f'Диапазон поля: {float(data.min()):.6g} … {float(data.max()):.6g} · Поверхностей: {len(new)}')
                + (tr(' · На этом уровне поверхность отсутствует.') if not new else '')
            )
            if self.isVisible():
                self.window.Render()
        except (ValueError, RuntimeError) as exc:
            quill.warning(self, 'CUBE', str(exc))
        finally:
            QApplication.restoreOverrideCursor()

    def change_opacity(self, value):
        for actor in self.surfaces:
            actor.GetProperty().SetOpacity(value)
        if self.isVisible():
            self.window.Render()

    def change_atoms(self, on):
        for actor in self.atoms:
            actor.SetVisibility(on)
        if self.isVisible():
            self.window.Render()

    def change_projection(self, on):
        self.renderer.GetActiveCamera().SetParallelProjection(on)
        self.renderer.ResetCameraClippingRange()
        if self.isVisible():
            self.window.Render()

    def center_view(self):
        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
        if self.isVisible():
            self.window.Render()

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, tr('Открыть CUBE'), str(Path.home()), tr('CUBE (*.cube *.cub);;Все файлы (*)')
        )
        if not path:
            return
        try:
            p = Path(path)
            if p.stat().st_size > MAX_BYTES:
                raise ValueError(tr('CUBE: предел размера — 64 МБ.'))
            self.load_cube(read_cube(p.read_text(encoding='utf-8-sig')))
        except (OSError, ValueError, UnicodeError) as exc:
            quill.warning(self, tr('Не удалось открыть CUBE'), str(exc), 'file-unreadable')

    def write_image(self, path):
        self.window.Render()
        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(self.window)
        capture.ReadFrontBufferOff()
        capture.SetInputBufferTypeToRGB()
        capture.Update()
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(path))
        writer.SetInputConnection(capture.GetOutputPort())
        writer.Write()
        if writer.GetErrorCode() or not Path(path).exists():
            raise OSError(tr('Не удалось сохранить PNG.'))

    def save_image(self):
        # offered in the last picture folder or Pictures, not in the program folder
        preferences = getattr(self.parent(), 'preferences', None)
        name = 'CUBE-' + datetime.now().strftime('%Y%m%d-%H%M%S')
        path = ask_picture_path(self, tr('Сохранить 3D-изображение'), name, '.png', preferences)
        if path:
            try:
                self.write_image(path)
            except OSError as exc:
                quill.warning(self, tr('Сохранение'), str(exc))

    def showEvent(self, event):
        super().showEvent(event)
        self.window.Render()

    def closeEvent(self, event):
        self.vtk_widget.Finalize()
        super().closeEvent(event)

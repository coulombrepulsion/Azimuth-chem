"""Compass: VTK draws the atoms and bonds straight into the window, with no copy of the picture.

HEADER
    In 0.51 VTK drew the model in a hidden window and the picture was copied back into the field each frame
    (modules/compass/view/vtk_model.render); the copy, not the drawing, cost most of the time. Here the field gets
    two children laid over it: an OpenGL widget (VTKGLWidget, a QOpenGLWidget in which a vtkGenericOpenGLRenderWindow
    renders with Qt's own context, as VTK's C++ QVTKOpenGLNativeWidget does, so Qt composites it like any widget)
    that draws the background and the model on the graphics card, and a
    transparent overlay on top of it that paints everything else exactly as before (labels, selection rings,
    measurements, the overlay for comparison, the cell, hydrogen bonds, surfaces, the dot grid). Both children
    ignore the mouse, so picking, dragging, menus and the keyboard stay with modules/compass/view/viewer.py.
    Wilkinson convention, sections 1-8.

§1 THEORY
    a surface on the model (an orbital, a density, the ESP map — modules/compass/actions/surface_actions.py) is
    drawn by VTK in the same scene, with the depth buffer and dual depth peeling for its transparency, instead of
    QPainter's far half under the model and near half over it; its vertices are put in the pixels of the atoms
    (viewer.project_vertices) and its normals turned with the view (viewer.view_matrix), and the mesh is the one
    without decimation (viewer.surface_meshes). The legend of the surface stays on the overlay.
    The scene is the one of vtk_model §1 (spheres and rods in device pixels from bond_depth.model_scene, the
    orthographic camera in pixels, the light from the upper left), so the picture, the projection and the
    positions the view picks atoms by are those of the other engines. What the built-in renderer draws
    *under* the model (the grid, axes, cell edges, the start structure, hydrogen bonds, the
    far half of a surface) is painted into a transparent image from which the silhouette of the model (discs
    of the atoms, quads of the bonds — viewer.model_silhouette) is cleared, and that image is shown over the
    model: on screen it looks drawn under it.

§2 ALGORITHM
    attach(view): create the two children (VTK first, the overlay above), a renderer with the light of
    vtk_model, and return the object, or raise RuntimeError when VTK cannot draw into a QOpenGLWidget here.
    refresh(): read the size of the VTK window in device pixels (W, H; the pixel ratio is H / view height),
    build the scene for that ratio, replace the actors, place the camera, set the background colour of the
    field, ask the OpenGL widget to repaint, repaint the overlay. The view calls schedule() from update()
    and resizeEvent(); several calls in one turn of the event loop draw once.

§3 APPLICATIONS
    «Вид → Трёхмерная графика VTK» (view_actions.set_engine): MoleculeView.set_native(True).

§4 SPECIFICATION
    NativeModel(view): .gl (the VTK widget), .overlay, .active; schedule(); refresh(); close().
    Pictures (PNG, SVG, PDF, GIF frames) are still drawn by the view itself with the hidden-window path
    (vtk_model.render): the children are hidden while a picture is taken.

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    0.53.0 used vtkmodules.qt.QVTKRenderWindowInteractor on the QOpenGLWidget base; in VTK 9.5 it still makes a
    native window (winId() + SetWindowInfo, WA_PaintOnScreen) that Qt cannot paint over: the field showed stale
    pictures of other pages. VTKGLWidget follows QVTKRenderWindowAdapter instead: format OpenGL 3.2 core, the
    window SetReadyForRendering(True), SetOwnContext(0), OpenGLInitContext() in initializeGL; observers make the
    context current and answer «is current» (SetIsCurrent); in paintGL the GL state cache of VTK is reset and
    pushed, VTK renders, its display framebuffer is blitted into defaultFramebufferObject() (scissor off), and
    the alpha of the field is set to 1. Any failure turns the native view off and the hidden-window path stays.
    Two conditions found on the Mac (tools/vtk_window_check*.py): the program must compose its windows with OpenGL
    (opengl_setup.prepare() before QApplication; otherwise NativeModel refuses with «restart: …»), and VTK must make
    the context current through QOpenGLContext.makeCurrent(surface), never QOpenGLWidget.makeCurrent().
    On the 'offscreen' and 'minimal' Qt platforms (the tests) there is no OpenGL: refused.

§7 TEST CASES (tests/test_gui.py::test_vtk_draws_straight_into_the_window)
    The children exist and ignore the mouse; a grab of the field shows the element colour at the centre of
    an atom close to the built-in renderer's, the label and the selection ring over it, the grid not over the
    atom; picking an atom by its position works; pictures are taken without the children; turning VTK off
    removes them.

§8 ERROR ANALYSIS
    As vtk_model §8; the overlay image is cleared along the same silhouette the model is drawn with, so the
    edge of an object under the model may differ from the built-in renderer by a pixel.
"""

from __future__ import annotations

from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import QWidget

from modules.compass.view import vtk_model
from modules.compass.view.bond_depth import model_scene


# On again (after tools/vtk_window_check*.py on the user's Mac). The two failures of the first trials:
# (1) a window with WebEngine is composed with Metal and does not show a QOpenGLWidget at all (the Atlas turned
# black) — opengl_setup.prepare() composes the whole program with OpenGL before QApplication; (2) VTK aborted as
# soon as the scene had an actor because QOpenGLWidget.makeCurrent() rebinds the widget's framebuffer in the middle
# of VTK's frame — the context is now made current through QOpenGLContext itself, as VTK's C++ adapter does.
ENABLED = True


from PySide6.QtOpenGLWidgets import QOpenGLWidget  # noqa: E402


class VTKGLWidget(QOpenGLWidget):
    """A QOpenGLWidget in which VTK draws with Qt's own OpenGL context — the Python counterpart of VTK's
    C++ QVTKOpenGLNativeWidget / QVTKRenderWindowAdapter: a vtkGenericOpenGLRenderWindow without a window of its
    own renders in paintGL, and its picture is blitted into the widget's framebuffer on the graphics card, so Qt
    composites the widget like any other and the overlay can lie on top of it."""

    def __init__(self, parent):
        super().__init__(parent)
        from PySide6.QtGui import QSurfaceFormat

        fmt = QSurfaceFormat(QSurfaceFormat.defaultFormat())  # OpenGL 3.2 core, set by opengl_setup.prepare()
        fmt.setVersion(3, 2)  # VTK's OpenGL2 back end needs OpenGL 3.2 core
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setDepthBufferSize(24)
        fmt.setStencilBufferSize(8)
        fmt.setAlphaBufferSize(8)
        fmt.setSamples(0)
        self.setFormat(fmt)
        self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
        import vtkmodules.vtkRenderingOpenGL2 as gl2

        self.window = gl2.vtkGenericOpenGLRenderWindow()
        self.window.SetMultiSamples(0)
        # not QOpenGLWidget.makeCurrent(): it rebinds the widget's framebuffer in the middle of VTK's frame, and the
        # OpenGL driver of macOS aborts as soon as the scene has an actor (tools/vtk_window_check3.py, cases M-R)
        self.window.AddObserver('WindowMakeCurrentEvent', self._make_current)
        self.window.AddObserver('WindowIsCurrentEvent', self._is_current)
        self.window.AddObserver('WindowFrameEvent', lambda obj, event: None)  # Qt presents the frame
        self.window.SetIsDirect(1)
        self.window.SetSupportsOpenGL(1)
        self.ready = False
        self.failed = ''
        self.on_failure = None

    def _make_current(self, obj, event):
        from PySide6.QtGui import QOpenGLContext

        ctx = self.context()
        if ctx is not None and QOpenGLContext.currentContext() is not ctx:
            ctx.makeCurrent(ctx.surface())

    def _is_current(self, obj, event):
        from PySide6.QtGui import QOpenGLContext

        obj.SetIsCurrent(self.context() is not None and QOpenGLContext.currentContext() is self.context())

    def initializeGL(self):
        try:
            ctx = self.context()
            fmt = ctx.format()
            if (fmt.majorVersion(), fmt.minorVersion()) < (3, 2):
                raise RuntimeError(f'OpenGL {fmt.majorVersion()}.{fmt.minorVersion()} here, VTK needs 3.2')
            if hasattr(self.window, 'SetUseOffScreenBuffers'):
                self.window.SetUseOffScreenBuffers(False)
            self.window.SetReadyForRendering(True)
            self.window.SetOwnContext(0)
            self.window.SetFrameBlitModeToNoBlit()  # the picture is blitted into Qt's framebuffer in paintGL
            self.window.OpenGLInitContext()
            ctx.aboutToBeDestroyed.connect(self._cleanup)
            self.ready = True
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)

    def _cleanup(self):
        if self.ready:
            self.makeCurrent()
            try:
                self.window.Finalize()
            except Exception:  # noqa: BLE001
                pass
            self.ready = False

    def _fail(self, exc):
        self.ready = False
        self.failed = f'{type(exc).__name__}: {exc}'
        if self.on_failure is not None:
            QTimer.singleShot(0, lambda: self.on_failure(self.failed))

    def device_size(self):
        ratio = self.devicePixelRatioF()
        return max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio))

    def paintGL(self):
        if not self.ready:
            return
        try:
            W, H = self.device_size()
            self.window.SetSize(W, H)
            state = self.window.GetState()  # Qt changed the GL state since the last frame: VTK must not trust its cache
            state.Reset()
            state.Push()
            try:
                self.window.Render()
            finally:
                state.Pop()
            f = self.context().functions()
            GL_DRAW_FRAMEBUFFER, GL_SCISSOR_TEST, GL_COLOR_BUFFER_BIT, GL_LINEAR = 0x8CA9, 0x0C11, 0x4000, 0x2601
            f.glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self.defaultFramebufferObject())
            scissor = f.glIsEnabled(GL_SCISSOR_TEST)
            f.glDisable(GL_SCISSOR_TEST)
            self.window.BlitDisplayFramebuffer(0, 0, 0, W, H, 0, 0, W, H, GL_COLOR_BUFFER_BIT, GL_LINEAR)
            # the field is opaque: alpha 1 everywhere, as the adapter of VTK does (clearAlpha)
            f.glBindFramebuffer(GL_DRAW_FRAMEBUFFER, self.defaultFramebufferObject())
            f.glColorMask(False, False, False, True)
            f.glClearColor(0.0, 0.0, 0.0, 1.0)
            f.glClear(GL_COLOR_BUFFER_BIT)
            f.glColorMask(True, True, True, True)
            if scissor:
                f.glEnable(GL_SCISSOR_TEST)
        except Exception as exc:  # noqa: BLE001
            self._fail(exc)


class _Overlay(QWidget):
    """Transparent, over the VTK widget: the view paints its labels, rings, measurements … here."""

    def __init__(self, view):
        super().__init__(view)
        self.view = view
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAutoFillBackground(False)

    def paintEvent(self, event):
        self.view.paint_over_native(self)


class NativeModel:
    def __init__(self, view):
        from PySide6.QtGui import QGuiApplication

        if not ENABLED:
            raise RuntimeError('drawing straight into the window is switched off')
        if QGuiApplication.platformName() in ('offscreen', 'minimal'):
            raise RuntimeError('no OpenGL on the ' + QGuiApplication.platformName() + ' platform')  # tests, servers
        from modules.compass.view import opengl_setup

        if not opengl_setup.ready():  # the windows are composed with Metal/Direct3D: the widget would not show
            raise RuntimeError('restart: ' + opengl_setup.reason())
        self.view = view
        self.active = False
        gl = VTKGLWidget(view)
        gl.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        gl.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        gl.on_failure = self._failed
        self.gl = gl
        kit = vtk_model.kit()['v']
        self.renderer = kit['vtkRenderer']()
        self.renderer.AutomaticLightCreationOff()
        if hasattr(self.renderer, 'UseFXAAOn'):
            self.renderer.UseFXAAOn()  # smooth edges without multisampling (cheap, on the graphics card)
        # translucent surfaces in the right order with the atoms (dual depth peeling on the graphics card)
        self.renderer.SetUseDepthPeeling(True)
        self.renderer.SetMaximumNumberOfPeels(8)
        self.renderer.SetOcclusionRatio(0.02)
        gl.window.SetAlphaBitPlanes(1)
        self._surfaces = (None, [])  # (the meshes, [(actor, polydata, mesh)]) — built once per surface
        self.light = vtk_model.make_light()
        self.renderer.AddLight(self.light)
        gl.window.AddRenderer(self.renderer)
        self.overlay = _Overlay(view)
        self._pending = False
        self.error = ''
        for child in (gl, self.overlay):
            child.setGeometry(view.rect())
            child.show()
        self.overlay.raise_()
        self.active = True

    def schedule(self):
        if self.active and not self._pending:
            self._pending = True
            QTimer.singleShot(0, self.refresh)

    def refresh(self):
        self._pending = False
        if not self.active:
            return
        try:
            self._refresh()
        except Exception as exc:  # noqa: BLE001 — VTK failed in the window: back to the built-in renderer
            self.error = f'{type(exc).__name__}: {exc}'
            failed = getattr(self.view, 'engineFailed', None)
            self.view.set_native(False)
            if failed is not None:
                failed.emit(self.error)

    def _refresh(self):
        view = self.view
        for child in (self.gl, self.overlay):
            if child.geometry() != view.rect():
                child.setGeometry(view.rect())
        W, H = self.gl.device_size()
        ratio = H / max(1, view.height())
        spheres, rods = [], []
        if view.molecule and view.molecule.atoms:
            view._paint_camera = view.camera()
            try:
                spheres, rods = model_scene(view, view.projected(), view.palette, ratio)
            finally:
                view._paint_camera = None
        self.renderer.RemoveAllViewProps()
        for actor in vtk_model.scene_actors(spheres, rods, H):
            self.renderer.AddActor(actor)
        for actor in self._surface_actors(ratio, H):
            self.renderer.AddActor(actor)
        vtk_model.place_camera(self.renderer, self.light, W, H, spheres, rods)
        colour = view.field_color()
        self.renderer.SetBackground(colour.redF(), colour.greenF(), colour.blueF())
        if self.gl.failed:
            raise RuntimeError(self.gl.failed)
        self.gl.update()  # the QOpenGLWidget repaints: VTK renders in its paintGL
        self.overlay.update()

    def _surface_actors(self, ratio, H):
        """The actors of the surface on the model (orbital, density, ESP), moved to this frame: the polydata are
        made once per surface and only their points and normals change when the view turns."""
        view = self.view
        meshes, opacity = view.surface_meshes() if hasattr(view, 'surface_meshes') else ([], None)
        if not meshes:
            return []
        if self._surfaces[0] is not meshes:
            built = []
            for mesh in meshes:
                colours = mesh.colors if mesh.colors is not None else vtk_model.hex_rgb(mesh.color)
                actor, data = vtk_model.surface_actor(mesh.triangles, colours, opacity)
                built.append((actor, data, mesh))
            self._surfaces = (meshes, built)
        rotation = view.view_matrix()
        out = []
        for actor, data, mesh in self._surfaces[1]:
            vtk_model.place_surface(data, view.project_vertices(mesh.vertices, ratio), mesh.normals @ rotation, H)
            actor.GetProperty().SetOpacity(float(opacity))
            out.append(actor)
        return out

    def _failed(self, message):
        failed = getattr(self.view, 'engineFailed', None)
        self.view.set_native(False)
        if failed is not None:
            failed.emit(message)

    def set_visible(self, on):
        for child in (self.gl, self.overlay):
            child.setVisible(on)

    def close(self):
        self.active = False
        for child in (self.overlay, self.gl):
            child.hide()
            child.setParent(None)
            child.deleteLater()

"""Compass: the whole program composes its windows with OpenGL when VTK is to draw straight into the window.

HEADER
    VTK can draw into a Qt window only through a QOpenGLWidget (modules/compass/view/vtk_view.py), and Qt shows such a
    widget only in a window composed with OpenGL. On macOS a window with a Qt WebEngine page (the Atlas) is composed
    with Metal, and there a QOpenGLWidget is not shown at all ("'Metal' is not compatible with QOpenGLWidget"); this
    is why the first trials left the field empty and the Atlas black. The choice of the graphics interface can be
    made only before QApplication exists, so prepare() is called by every entry point (hub/launch.py,
    azimuth/app.py, gui_launcher.py) first. It switches only when the user chose «Вид → Трёхмерная графика VTK»
    (the remembered preference), so without VTK the program draws exactly as before.
    Wilkinson convention, sections 1-8.

§1 THEORY
    Qt 6 composes a top-level window through one graphics interface (RHI: Metal, Direct3D, Vulkan or OpenGL); a
    QOpenGLWidget can be part of the window only when that interface is OpenGL. Qt Quick, under which WebEngine
    draws, has the same choice (QQuickWindow.setGraphicsApi). Checked on the user's Mac (tools/vtk_window_check*.py,
    2026-10-25): with OpenGL for both, a WebEngine page and VTK in a QOpenGLWidget share one window, 30 frames each.

§2 ALGORITHM
    prepare(): if a QApplication already exists, or the Qt platform is 'offscreen'/'minimal' (tests, servers), or
    the user did not choose VTK (wanted()), do nothing and record why. Else: QSG_RHI_BACKEND=opengl and
    QT_WIDGETS_RHI_BACKEND=opengl in the environment, the attribute AA_ShareOpenGLContexts, the default surface
    format OpenGL 3.2 core (depth 24, stencil 8, alpha 8) and QQuickWindow.setGraphicsApi(OpenGL); record it.
    wanted(): the environment AZIMUTH_OPENGL=1 / 0 decides if set; else the preference compass_engine == 'vtk'.

§3 APPLICATIONS
    vtk_view.NativeModel refuses to start unless ready() (the hidden-window path of VTK stays, and the Compass says
    that drawing in the window starts after a restart).

§4 SPECIFICATION
    prepare() -> bool (True when switched); ready() -> bool; reason() -> str (why not); wanted() -> bool.

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    QSettings is read through azimuth.settings.open_settings (organisation and application «Azimuth»),
    which works before QApplication.

§7 TEST CASES (tests/compass/test_opengl_setup.py)
    With a QApplication present prepare() returns False and says why; AZIMUTH_OPENGL overrides the preference.

§8 ERROR ANALYSIS
    No numbers. A wrong answer of wanted() only changes the interface the windows are composed with.
"""

from __future__ import annotations

import os

KEY = 'compass_engine'
_state = {'ready': False, 'reason': 'not prepared before the application started'}


def wanted():
    """True if the windows should be composed with OpenGL: AZIMUTH_OPENGL=1/0, else the user chose VTK."""
    forced = os.environ.get('AZIMUTH_OPENGL', '').strip()
    if forced in ('0', '1'):
        return forced == '1'
    try:
        from azimuth.settings import open_settings

        return str(open_settings().value(KEY, 'raster')) == 'vtk'
    except Exception:  # noqa: BLE001 — no preference: as before
        return False


def prepare():
    """Before QApplication: compose with OpenGL if VTK is to draw in the window (§2). True if switched."""
    from PySide6.QtCore import QCoreApplication

    if QCoreApplication.instance() is not None:
        _state.update(ready=False, reason='the application already existed')
        return False
    if os.environ.get('QT_QPA_PLATFORM', '').split(':')[0] in ('offscreen', 'minimal'):
        _state.update(ready=False, reason='no OpenGL on this Qt platform')
        return False
    if not wanted():
        _state.update(ready=False, reason='VTK was off when the program started')
        return False
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QSurfaceFormat
        from PySide6.QtQuick import QQuickWindow, QSGRendererInterface

        os.environ['QSG_RHI_BACKEND'] = 'opengl'
        os.environ['QT_WIDGETS_RHI_BACKEND'] = 'opengl'
        QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
        fmt = QSurfaceFormat()
        fmt.setVersion(3, 2)  # VTK's OpenGL2 back end needs OpenGL 3.2 core
        fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
        fmt.setDepthBufferSize(24)
        fmt.setStencilBufferSize(8)
        fmt.setAlphaBufferSize(8)
        QSurfaceFormat.setDefaultFormat(fmt)
        QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    except Exception as exc:  # noqa: BLE001 — Qt without Qt Quick or OpenGL: as before
        _state.update(ready=False, reason=f'{type(exc).__name__}: {exc}')
        return False
    _state.update(ready=True, reason='')
    return True


def ready():
    return _state['ready']


def reason():
    return _state['reason']

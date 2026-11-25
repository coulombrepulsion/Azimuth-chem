"""Check, round 3: which part of the VTK scene aborts when VTK draws into a Qt OpenGL widget?

Not a part of the program. Run from the program folder:

    .venv/bin/python tools/vtk_window_check3.py

Round 2 (tools/vtk_window_check2.py, removed 0.222.28; rounds 1–2 are in the CHANGELOG): with Qt composing through OpenGL, the WebEngine page and an OpenGL widget
share a window; VTK draws its first frame (empty, no actors yet) and aborts on a later frame. Here the scene is
put in before the first frame, every case asks for 15 frames (one every 0.1 s) and prints a line before and
after each Render, so the log shows the frame and the scene that abort. Settings as in round 2 (OpenGL
composition, shared contexts, default format 3.2 core).

Cases (no WebEngine page, except T): L empty scene M one plain VTK sphere (vtkSphereSource + vtkPolyDataMapper, no
    colours per point) N the spheres of the Compass (vtkGlyph3DMapper, colours and radii per point) O the bonds of the
    Compass (vtkTubeFilter, colours per point) P spheres and bonds (as the Compass), VTK log at the most detailed level
    Q as P, but VTK makes the context current through QOpenGLContext (not QOpenGLWidget.makeCurrent) R as P, but without
    saving and restoring the OpenGL state around Render T as Q, with the WebEngine page beside
Output: terminal (short), vtk-window-check3.log (full), Azimuth-vtk-check3-<case>.png (ignored by git).
"""

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / 'vtk-window-check3.log'
CASES = {
    'L': dict(web=False, scene='empty', current='widget', state=True, trace=False),
    'M': dict(web=False, scene='plain', current='widget', state=True, trace=False),
    'N': dict(web=False, scene='spheres', current='widget', state=True, trace=False),
    'O': dict(web=False, scene='rods', current='widget', state=True, trace=False),
    'P': dict(web=False, scene='both', current='widget', state=True, trace=True),
    'Q': dict(web=False, scene='both', current='context', state=True, trace=False),
    'R': dict(web=False, scene='both', current='widget', state=False, trace=False),
    'T': dict(web=True, scene='both', current='context', state=True, trace=False),
}
FRAMES = 15


def say(text):
    print(text, flush=True)


def run_case(name):
    import faulthandler

    faulthandler.enable()
    case = CASES[name]
    sys.path.insert(0, str(ROOT))
    os.environ['QSG_RHI_BACKEND'] = 'opengl'
    os.environ['QT_WIDGETS_RHI_BACKEND'] = 'opengl'
    from PySide6.QtCore import QCoreApplication, Qt, QTimer
    from PySide6.QtGui import QOpenGLContext, QSurfaceFormat

    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
    fmt = QSurfaceFormat()
    fmt.setVersion(3, 2)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    fmt.setDepthBufferSize(24)
    fmt.setStencilBufferSize(8)
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)
    from PySide6.QtQuick import QQuickWindow, QSGRendererInterface

    QQuickWindow.setGraphicsApi(QSGRendererInterface.GraphicsApi.OpenGL)
    from PySide6.QtOpenGLWidgets import QOpenGLWidget
    from PySide6.QtWidgets import QApplication, QHBoxLayout, QWidget

    from vtkmodules.vtkCommonCore import vtkLogger, vtkObject, vtkOutputWindow

    vtkObject.GlobalWarningDisplayOn()
    try:
        vtkOutputWindow.GetInstance().SetDisplayModeToAlwaysStdErr()
    except Exception:  # noqa: BLE001
        pass
    vtkLogger.SetStderrVerbosity(vtkLogger.VERBOSITY_MAX if case['trace'] else vtkLogger.VERBOSITY_INFO)
    import vtkmodules.vtkRenderingOpenGL2 as gl2
    from modules.compass.view import vtk_model

    app = QApplication(sys.argv[:1])
    say(f'{name}: QApplication, platform {app.platformName()}; case {case}')
    window = QWidget()
    window.setWindowTitle(f'VTK check 3 {name}')
    window.resize(900, 420)
    row = QHBoxLayout(window)
    if case['web']:
        from PySide6.QtWebEngineWidgets import QWebEngineView

        web = QWebEngineView()
        web.setHtml('<html><body style="background:#2a62b8;color:white;font:32px Helvetica">WebEngine</body></html>')
        row.addWidget(web, 1)
    status = {'frames': 0, 'error': ''}

    class Traced(QOpenGLWidget):
        def __init__(self):
            super().__init__()
            self.setUpdateBehavior(QOpenGLWidget.UpdateBehavior.NoPartialUpdate)
            self.window = gl2.vtkGenericOpenGLRenderWindow()
            self.window.SetMultiSamples(0)
            if case['current'] == 'context':
                self.window.AddObserver('WindowMakeCurrentEvent', self._make_current_context)
            else:
                self.window.AddObserver('WindowMakeCurrentEvent', lambda o, e: self.makeCurrent())
            self.window.AddObserver('WindowIsCurrentEvent', self._is_current)
            self.window.AddObserver('WindowFrameEvent', lambda o, e: None)
            self.window.SetIsDirect(1)
            self.window.SetSupportsOpenGL(1)
            self.ready = False

        def _make_current_context(self, obj, event):
            ctx = self.context()
            if ctx is not None and QOpenGLContext.currentContext() is not ctx:
                ctx.makeCurrent(ctx.surface())

        def _is_current(self, obj, event):
            obj.SetIsCurrent(self.context() is not None and QOpenGLContext.currentContext() is self.context())

        def initializeGL(self):
            f = self.context().format()
            say(f'{name}: initializeGL, context {f.majorVersion()}.{f.minorVersion()} {f.profile().name}')
            self.window.SetReadyForRendering(True)
            self.window.SetOwnContext(0)
            self.window.SetFrameBlitModeToNoBlit()
            self.window.OpenGLInitContext()
            self.ready = True

        def paintGL(self):
            if not self.ready:
                return
            n = status['frames'] + 1
            ratio = self.devicePixelRatioF()
            W, H = max(1, round(self.width() * ratio)), max(1, round(self.height() * ratio))
            self.window.SetSize(W, H)
            state = self.window.GetState() if case['state'] else None
            if state is not None:
                state.Reset()
                state.Push()
            say(f'{name}: frame {n} {W}x{H}: Render ...')
            self.window.Render()
            say(f'{name}: frame {n}: Render done')
            if state is not None:
                state.Pop()
            if case['current'] == 'widget':
                self.makeCurrent()
            g = self.context().functions()
            g.glBindFramebuffer(0x8CA9, self.defaultFramebufferObject())
            g.glDisable(0x0C11)
            self.window.BlitDisplayFramebuffer(0, 0, 0, W, H, 0, 0, W, H, 0x4000, 0x2601)
            say(f'{name}: frame {n}: blit done')
            status['frames'] = n

    widget = Traced()
    widget.setMinimumSize(400, 380)
    row.addWidget(widget, 1)
    v = vtk_model.kit()['v']
    renderer = v['vtkRenderer']()
    renderer.AutomaticLightCreationOff()
    light = vtk_model.make_light()
    renderer.AddLight(light)
    renderer.SetBackground(0.96, 0.965, 0.97)
    widget.window.AddRenderer(renderer)
    # the scene for the size the widget will have (the layout gives it about 430 x 400 points)
    W, H = 860, 760
    spheres = [(W * 0.35, H * 0.5, 0.0, H * 0.16, (220, 40, 40)), (W * 0.65, H * 0.5, 0.0, H * 0.12, (40, 60, 210))]
    rods = [((W * 0.35, H * 0.5, 0.0), (W * 0.65, H * 0.5, 0.0), H * 0.03, (220, 40, 40), (40, 60, 210), (0.4, 0.6))]
    scene = case['scene']
    if scene == 'plain':
        source = v['vtkSphereSource']()
        source.SetCenter(W * 0.35, H * 0.5, 0.0)
        source.SetRadius(H * 0.16)
        mapper = v['vtkPolyDataMapper']()
        mapper.SetInputConnection(source.GetOutputPort())
        actor = v['vtkActor']()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(0.86, 0.16, 0.16)
        renderer.AddActor(actor)
    elif scene != 'empty':
        use_s = spheres if scene in ('spheres', 'both') else []
        use_r = rods if scene in ('rods', 'both') else []
        for actor in vtk_model.scene_actors(use_s, use_r, H):
            renderer.AddActor(actor)
    vtk_model.place_camera(renderer, light, W, H, spheres, rods)
    say(f'{name}: scene "{scene}": {renderer.GetActors().GetNumberOfItems()} actor(s)')
    timer = QTimer()
    timer.setInterval(100)
    timer.timeout.connect(widget.update)
    window.show()
    timer.start()
    start = time.time()

    def finish():
        timer.stop()
        say(f'{name}: frames drawn {status["frames"]}')
        picture = window.grab()
        path = ROOT / f'Azimuth-vtk-check3-{name}.png'
        picture.save(str(path))
        image = picture.toImage()
        ratio = image.devicePixelRatio()
        centre = widget.mapTo(window, widget.rect().center())
        x, y = round((centre.x() - widget.width() * 0.15) * ratio), round(centre.y() * ratio)
        c = image.pixelColor(x, y)
        say(f'{name}: pixel where red should be: rgb({c.red()},{c.green()},{c.blue()})'
            + ('  -> DRAWN' if c.red() > 150 and c.green() < 110 else '  -> not red'))
        say(f'{name}: {time.time() - start:.1f} s; finished without a crash')
        app.quit()

    QTimer.singleShot(int((FRAMES * 0.1 + 1.5) * 1000), finish)
    app.exec()


def main():
    lines = [f'== VTK window check, round 3, {time.strftime("%Y-%m-%d %H:%M:%S")}, Python {sys.version.split()[0]}']
    try:
        import PySide6
        import vtkmodules.vtkCommonCore as core

        lines.append(f'PySide6 {PySide6.__version__}, VTK {core.vtkVersion.GetVTKVersion()}')
    except Exception as exc:  # noqa: BLE001
        lines.append(f'import failed: {exc}')
    for line in lines:
        say(line)
    summary = []
    for name in CASES:
        say(f'-- case {name}: {CASES[name]}')
        try:
            done = subprocess.run(
                [sys.executable, str(Path(__file__).resolve()), name],
                capture_output=True, text=True, timeout=60, cwd=str(ROOT), env=dict(os.environ, PYTHONIOENCODING='utf-8'),
                encoding='utf-8', errors='replace',  # the child writes UTF-8, not the Windows code page
            )
            out = (done.stdout + '\n' + done.stderr).strip().splitlines()
            code = done.returncode
            verdict = 'ok' if code == 0 else (f'CRASH (signal {-code})' if code < 0 else f'error (exit {code})')
        except subprocess.TimeoutExpired as exc:
            out = ((exc.stdout or b'').decode(errors='replace') + (exc.stderr or b'').decode(errors='replace')).splitlines()
            verdict = 'HUNG (60 s)'
        frames = [x for x in out if ': frame ' in x]
        shown = [x for x in out if ': frame ' not in x and 'Extension modules' not in x][-25:]
        for line in shown:
            say('   ' + line[:300])
        if frames:
            say('   ... ' + frames[-1])
        say(f'   => case {name}: {verdict}')
        drawn = [x for x in out if 'DRAWN' in x or 'not red' in x]
        last = frames[-1].split(': ', 1)[1] if frames else 'no frame'
        summary.append(f'{name}: {verdict}; last: {last}' + (f'; {drawn[0].split(": ", 1)[1]}' if drawn else ''))
        lines += [f'-- case {name}: {CASES[name]}'] + ['   ' + x for x in out] + [f'   => case {name}: {verdict}']
    lines += ['== summary'] + summary
    say('== summary')
    for line in summary:
        say('   ' + line)
    LOG.write_text('\n'.join(lines) + '\n', encoding='utf-8')
    say(f'written {LOG}')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] in CASES:
        run_case(sys.argv[1])
    else:
        main()

"""Azimuth entry points. CLI and shared-state contract: docs/MODULES.md."""

import argparse
import os
import sys
from PySide6.QtWidgets import QApplication
from azimuth.app import Studio, theme_style_sheet, use_fusion


def register_links():
    """The scheme azimuth:// leads to this installation (azimuth/links.py §2.4) — the registry of the user
    on Windows; on macOS the system is asked to read Azimuth.app again, once for a version."""
    from pathlib import Path

    from azimuth import links

    if sys.platform == 'darwin' and not getattr(sys, 'frozen', False):
        try:
            from azimuth import __version__
            from azimuth.crash_report import log_dir

            bundle = Path(__file__).resolve().parents[1] / 'Azimuth.app'
            return links.register_bundle(bundle, log_dir() / 'links-registered.txt', __version__)
        except Exception as exc:  # the program starts whatever happens to the registration
            print(f'Azimuth: the scheme azimuth:// was not registered: {exc!r}', file=sys.stderr)
            return False
    if sys.platform != 'win32':
        return False

    try:
        if getattr(sys, 'frozen', False):
            command = links.command_line(sys.executable)
        else:
            windowed = Path(sys.executable).with_name('pythonw.exe')
            script = Path(__file__).resolve().parents[1] / 'gui_launcher.py'
            command = links.command_line(windowed if windowed.is_file() else sys.executable, script)
        return links.register(command)
    except (OSError, ValueError) as exc:
        print(f'Azimuth: the scheme azimuth:// was not registered: {exc!r}', file=sys.stderr)
        return False


def main(default=None):
    parser = argparse.ArgumentParser(description='Quantum chemistry Analysis & Simulation')
    parser.add_argument('--module', choices=['atlas', 'compass', 'sextant', 'spectrum'], default=default)
    parser.add_argument('link', nargs='?', default=None)  # azimuth://… given by the system (azimuth/links.py)
    args = parser.parse_args()
    from azimuth import consoles
    from modules.compass.view import opengl_setup

    consoles.install()  # no console windows of the programs started (ORCA, Multiwfn, ssh…) on Windows

    opengl_setup.prepare()  # before QApplication; OpenGL composition when VTK draws in the window
    if args.module in ('compass', 'sextant', 'spectrum'):
        app = QApplication(sys.argv)
        app.setApplicationName('Азимут')
        use_fusion(app)  # once: the window does not set it again (azimuth/app.py use_fusion)
        app.setStyleSheet(theme_style_sheet())  # both themes, before the windows
        window = Studio()
        window.sidebar.hide()
        window.panel_toggle.hide()
        index = ('compass', 'sextant', 'spectrum').index(args.module)
        window.navigate(index)
        title = ('Компас', 'Секстант', 'Спектр')[index]
        from azimuth.i18n import tr  # the title in the language of the program

        window.setWindowTitle(tr('Азимут') + ' · ' + tr(title))
    elif args.module == 'atlas':  # the Atlas is on the site — opened in the browser, no window of its own
        from azimuth import site

        app = QApplication(sys.argv)
        return 0 if site.open_atlas() else 1
    else:
        from hub.window import HubWindow

        app = QApplication(sys.argv)
        app.setApplicationName('Азимут')
        app.setDesktopFileName('azimuth')  # Linux (Wayland) — the icon and the name of azimuth.desktop
        # a link azimuth:// — handed to the program that already runs (this copy then ends), else opened here
        from azimuth import link_channel, links

        if args.link and links.parse(args.link) and link_channel.send(args.link):
            return 0
        use_fusion(app)  # once: the window does not set it again (azimuth/app.py use_fusion)
        app.setStyleSheet(theme_style_sheet())  # both themes, before the windows
        window = HubWindow(initial=args.module)
        app.link_listener = link_channel.Listener(app, window.open_link, file_handler=window.open_file)
        # a language model of this computer shows in the open window what it built (azimuth/window_control.py)
        from azimuth.window_control import Control

        app.window_control = Control(window)
        if app.window_control.start():
            app.aboutToQuit.connect(app.window_control.stop)
        register_links()
        if args.link:
            from PySide6.QtCore import QTimer as _Timer

            # a file given on the command line («Открыть с помощью» of Windows and Linux) is opened too
            given = args.link
            _Timer.singleShot(0, lambda: window.open_file(given) if os.path.isfile(given) else window.open_link(given))
    from azimuth.polish import install as polish  # centred tables and smooth dialogs in every window

    polish(app)
    # the errors of the program go to a log, the window says so, a report goes to the author
    from azimuth import crash_report

    crash_report.install(app, lambda: window)
    window.show()
    from PySide6.QtCore import QTimer

    QTimer.singleShot(2500, lambda: crash_report.ask_after_crash(window))
    # a newer release on GitHub (the installers of the site) — asked in the background, said only when there is one
    from azimuth import updates

    updates.check_later(window)
    # Sextant offers the queue or the calculation on a server left unfinished when the program was closed
    studio = getattr(window, 'studio', window)
    if hasattr(studio, 'unfinished'):
        QTimer.singleShot(1500, studio.unfinished.check)
    return app.exec()

"""GUI startup with a persistent diagnostic log, including when no terminal is present."""

import sys, traceback


def log_path():
    """startup.log in the folder of the logs (azimuth/crash_report.log_dir); the log of the run before is kept
    as startup.previous.log (it was overwritten — the output of the run that failed was lost at the next start)."""
    from azimuth.crash_report import log_dir

    from azimuth import links

    if links.link_in(sys.argv) is not None:
        # a copy started by the system for a link azimuth:// usually hands the link to the program that
        # runs and ends — it keeps a log of its own and leaves startup.log of that program alone
        return log_dir() / 'startup.link.log'
    path = log_dir() / 'startup.log'
    if path.is_file():
        try:
            path.replace(path.with_name('startup.previous.log'))
        except OSError:
            pass
    return path


CHECK_STAMP = '.venv/.azimuth-checked'  # Azimuth.app checks the environment again only without it


def forget_check():
    """A start that failed on an import: the next start of Azimuth.app checks the environment (and offers the setup
    in Terminal) instead of trusting the stamp of the last good check."""
    import os

    try:
        os.remove(os.path.join(os.path.dirname(os.path.abspath(__file__)), CHECK_STAMP))
    except OSError:
        pass


def run():
    if '--install-tools' in sys.argv:  # the .exe of the installer installs xtb, MOPAC, MS-MPI itself
        from modules.sextant.install_tools import main

        argv = [a for a in sys.argv[1:] if a != '--install-tools']
        if '--log' in argv and argv.index('--log') + 1 < len(argv):  # a window .exe has no standard output —
            log = open(argv[argv.index('--log') + 1], 'a', encoding='utf-8', buffering=1)  # the log of the window
            sys.stdout = sys.stderr = log
        return main(argv)
    if not getattr(sys, 'frozen', False):
        # started by the system for a link azimuth:// the folder is not that of the program
        import os

        os.chdir(os.path.dirname(os.path.abspath(__file__)))
    path = log_path()
    with path.open('w', encoding='utf-8', buffering=1) as log:
        sys.stdout = sys.stderr = log
        try:
            from hub.launch import main

            if '--check' in sys.argv:
                from hub.window import HubWindow
                from PySide6.QtWidgets import QApplication
                from PySide6.QtCore import QTimer
                from modules.compass.view import opengl_setup

                opengl_setup.prepare()  # before QApplication
                from azimuth import consoles

                consoles.install()  # no console windows on Windows
                app = QApplication([])
                window = HubWindow()
                window.show()
                timer = QTimer()

                def ready():
                    if window.ready:  # no Atlas in the window (its item opens the site: not pressed here)
                        start = window.current
                        for section in ['home', *(s for s in window.sections if s != 'atlas')]:
                            window.show_section(section, animate=False)
                        window.show_section(start, animate=False)  # keep the user's last section
                        print(
                            'Azimuth hub startup verified: home, ' + ', '.join(s for s in window.sections if s != 'atlas')
                        )
                        window.compass.dirty = False
                        window.close()
                        app.exit(0)

                timer.timeout.connect(ready)
                timer.start(100)
                QTimer.singleShot(30000, lambda: app.exit(1))
                return app.exec()
            return main()
        except Exception as exc:
            traceback.print_exc()
            if isinstance(exc, ImportError):
                forget_check()
            try:
                from PySide6.QtWidgets import QApplication, QMessageBox

                app = QApplication.instance() or QApplication([])
                QMessageBox.critical(
                    None, 'Азимут: ошибка запуска', f'Не удалось запустить программу. Подробности записаны в:\n{path}'
                )
            except Exception:
                pass
            return 1


if __name__ == '__main__':
    raise SystemExit(run())

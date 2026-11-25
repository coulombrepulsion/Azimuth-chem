"""ServerWatchTool: the server of the profile watched from
Sextant — its dialog, «Проверить подключение» and the mark next to it (✓ free cores and memory, or ✗ and why), the
probe again every SERVER_PING_S s in a thread of its own, «Файлы на сервере». Was a part of RunTool, which reached for
all of it through its port of 87 names; now a part of its own with the names it needs. RunTool keeps the same methods,
which hand the call over here, and reads what the watching knows (watch, resources).

State: watch — {'profile', 'connection', 'thread', 'result', 'started'} of the server being watched, or None;
resources — (title of the server, cluster.Resources) of the last answer, or None.
"""

from pathlib import Path

from PySide6.QtCore import QTimer

from azimuth.i18n import tr
from modules.sextant import remote


class ServerWatchTool:
    PORT = (
        'SERVER_PING_S',
        'check_server_button',
        'error',
        'preferences',
        'run_tool',
        'server_browser',
        'server_mark',
        'server_spinner',
        'server_watch_timer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)
        self.watch = None
        self.resources = None

    def edit_server(self):
        from modules.sextant.server_dialog import ServerDialog

        dialog = ServerDialog(remote.load(self.w.preferences), self.w.widget, settings=self.w.preferences)
        accepted = dialog.exec() == ServerDialog.DialogCode.Accepted  # the dialog saves the profile itself
        if accepted and self.w.has('server_mark'):  # another profile — the old mark means nothing
            self.stop_server_watch()
            self.w.server_mark.hide()
        self.w.run_tool.refresh_program_path()
        return dialog.profile() if accepted else None

    def _connection(self):
        """(profile, connection) of the server of the profile — that of «Проверить подключение» when it is open, else
        the server opened; None (no profile yet: its dialog; or it did not open)."""
        from azimuth.tasks import run_quietly
        from modules.sextant import server_access

        profile = remote.load(self.w.preferences)
        if not profile.ready():
            self.edit_server()
            return None
        watch = self.watch
        connection = watch['connection'] if watch and watch.get('profile') == profile else None
        if connection is None:
            try:
                opened = server_access.open_server(self.w.widget, profile, waiting=run_quietly)
            except ValueError as exc:
                self.w.error(exc)
                return None
            if opened is None:
                return None
            connection = opened[0]
        return profile, connection

    def open_cluster_queue(self):
        """«Сервер → Очередь кластера…» — the jobs of SLURM with their cancel (cluster_queue.QueueWindow);
        one window, kept on this part."""
        from modules.sextant import cluster_queue

        found = self._connection()
        if found is None:
            return None
        old = getattr(self, 'queue_window', None)
        if old is not None:
            try:
                old.close()
            except RuntimeError:
                pass
        window = cluster_queue.QueueWindow(self.w.widget, *found)
        self.queue_window = window
        window.show()
        return window

    def open_server_files(self):
        """«Файлы на сервере» — the two-pane file manager (server_browser.ServerBrowser) over the connection of
        «Проверить подключение» when it is open, else the server is opened."""
        from modules.sextant.server_browser import ServerBrowser

        found = self._connection()
        if found is None:
            return None
        profile, connection = found
        old = getattr(self.w, 'server_browser', None)
        if old is not None:
            old.close()
        local = self.w.run_tool.jobs_root()
        browser = ServerBrowser(self.w.widget, profile, connection, str(local if Path(local).is_dir() else Path.home()),
                                profile.folder or '~')
        self.w.server_browser = browser
        browser.show()
        return browser

    def check_server(self):
        """Log in to the server of the profile, read what it has now; True when
        the server answered, False when not, None when cancelled. Then it is watched (server_ping)."""
        from modules.sextant import server_access

        self.stop_server_watch()
        profile = remote.load(self.w.preferences)
        if not profile.ready():
            self.edit_server()
            return None
        from azimuth.tasks import run_quietly

        self.w.server_mark.hide()
        self.w.check_server_button.setEnabled(False)
        self.w.server_spinner.start()
        try:
            # no waiting window — the spinner turns next to the button (the password is still asked if needed)
            opened = server_access.open_server(self.w.widget, profile, waiting=run_quietly)
        except ValueError as exc:  # ssh.SshError: the message of ssh for the user
            self.show_server_state(profile, None, str(exc))
            return False
        finally:
            self.w.server_spinner.stop()
            self.w.check_server_button.setEnabled(True)
        if opened is None:
            return None
        connection, resources = opened
        self.watch = {'profile': profile, 'connection': connection, 'thread': None, 'result': None,
                              'started': __import__('time').monotonic()}
        self.show_server_state(profile, resources)
        if not self.w.has('server_watch_timer'):
            self.w.server_watch_timer = QTimer(self.w.widget)
            self.w.server_watch_timer.setInterval(300)
            self.w.server_watch_timer.timeout.connect(self.server_ping)
        self.w.server_watch_timer.start()
        return True

    def server_ping(self):
        """Every SERVER_PING_S s: the probe again in a thread of its own; its answer (or the error) updates the mark."""
        import threading
        import time

        from modules.sextant import cluster

        watch = self.watch
        if watch is None:
            return None
        thread = watch['thread']
        if thread is not None and thread.is_alive():
            return None
        if thread is not None:  # the last probe is over
            watch['thread'] = None
            kind, value = watch['result']
            if kind == 'ok':
                self.show_server_state(watch['profile'], value)
            else:
                self.show_server_state(watch['profile'], None, value)
            return kind == 'ok'
        if time.monotonic() - watch['started'] < self.w.SERVER_PING_S:
            return None
        connection, profile = watch['connection'], watch['profile']

        def probe():
            try:
                text = connection.text(cluster.probe_command(profile.folder, profile.partition), timeout=30)
                watch['result'] = ('ok', cluster.parse_probe(text))
            except Exception as exc:  # noqa: BLE001 — any failure means «no answer», its text for the tooltip
                watch['result'] = ('fail', str(exc) or exc.__class__.__name__)

        watch['started'] = time.monotonic()
        watch['thread'] = threading.Thread(target=probe, daemon=True)
        watch['thread'].start()
        return None

    def stop_server_watch(self):
        self.watch = None
        if self.w.has('server_watch_timer'):
            self.w.server_watch_timer.stop()

    def show_server_state(self, profile, resources, error=''):
        """The mark next to the button: ✓ and «свободно N из M ядер · K ГБ», or ✗ and why (in the tooltip)."""
        from modules.sextant import cluster

        if resources is not None:
            self.resources = (profile.title(), resources)  # the programs there, for the tick
            chosen = cluster.plan(resources)
            memory = cluster.free_memory(resources)
            text = '✓ ' + tr(f'{chosen.physical_free} из {chosen.physical} ядер') + (
                tr(f' · {memory / 1024:.0f} ГБ') if memory else '')
            colour, tip = '#2e9e5b', cluster.summary(resources, chosen, profile.title())
        else:
            text, colour = '✗ ' + tr('нет связи'), '#c8453c'
            tip = profile.title() + ': ' + (error or tr('сервер не отвечает'))
        self.w.server_mark.setText(text)
        self.w.server_mark.setStyleSheet(f'color: {colour}; font-weight: 600;')
        self.w.server_mark.setToolTip(tip)
        self.w.server_mark.show()
        if resources is not None:
            self.w.run_tool.apply_server_resources(profile, resources)
            self.w.run_tool.refresh_program_path()  # is the chosen program there
        return text

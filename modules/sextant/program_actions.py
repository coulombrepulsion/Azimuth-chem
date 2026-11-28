"""ProgramTool: the program of Sextant shown and chosen —
its mark, name and tick (the path in the tooltip), «Указать…», «Искать самой», «Установить…» shown when it is missing,
and, with «Сервер», what the check of the server found there. Was a part of RunTool; RunTool keeps the same methods,
which hand the call over here. The program configured is asked through RunTool (run_tool.configured_program
is the public face: what the window, the settings and the tests use or replace — read here as there).
"""

import os

from PySide6.QtWidgets import QFileDialog

from azimuth.i18n import tr
from modules.sextant import remote, runner
from modules.sextant.inputs import NAMES
from modules.sextant.job_window import program_badge


class ProgramTool:
    PORT = (
        'check_server_button',
        'choose_program_button',
        'error',
        'found_program',
        'install_missing_button',
        'preferences',
        'program_badge',
        'program_found',
        'program_kind',
        'program_missing',
        'program_missing_text',
        'program_path',
        'run_tool',
        'server_button',
        'server_files_button',
        'server_mark',
        'server_watch_tool',
        'set_run_status',
        'where',
        'where_buttons',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)

    def configured_program(self, kind):
        return self.w.preferences.value(f'programs/{kind}', '') or None

    SERVER_TIP = 'Считать на сервере (кластере) — профиль: «Сервер…»'

    def follow_server_place(self, kind):
        """«Сервер» only for the programs a server runs (remote_job.REMOTE_KINDS: ORCA, MOPAC, xtb): for the others its tip
        tells so and a press of it says so in the status line (run_actions.set_where; a button switched off said
        nothing — the owner's Windows, 2026-11-28), and a choice of «Сервер» goes back to this computer — the error
        came only after «Запустить расчёт» (ROADMAP, Sextant 1: «честно показывать в интерфейсе, что где
        считается»). True when the place changed."""
        from modules.sextant.remote_job import REMOTE_KINDS

        buttons = getattr(self.w, 'where_buttons', None) if self.w.has('where_buttons') else None
        if not buttons or 'server' not in buttons:
            return False
        able = kind in REMOTE_KINDS
        item = buttons['server']
        item.setEnabled(True)
        item.setToolTip(tr(self.SERVER_TIP) if able else tr('{} считается только на этом компьютере; на сервере — ORCA, '
                                                            'MOPAC и xtb').format(NAMES[kind]))
        if not able and getattr(self.w, 'where', 'local') == 'server':
            self.w.run_tool.set_where('local')
            self.w.set_run_status(tr(self.w.run_tool.SERVER_ONLY).format(NAMES[kind]))
            return True
        return False

    def refresh_program_path(self):
        kind = self.w.program_kind()
        if self.follow_server_place(kind):  # set_where('local') has shown the program of this computer
            return self.w.found_program
        found = runner.find_program(kind, self.w.run_tool.configured_program(kind))
        self.w.found_program = found
        # the mark, the name and a tick — the path is in the tooltip only
        self.w.program_badge.setPixmap(program_badge(kind, 22, self.w.program_badge.devicePixelRatioF()))
        server = getattr(self.w, 'where', 'local') == 'server' and self.w.has('server_button')
        if server:  # the profile of the server instead of the program found here
            profile = remote.load(self.w.preferences)
            known = self.w.server_watch_tool.resources  # what the check found on this server
            if known is not None and known[0] != profile.title():
                known = None
            self.w.program_found.hide()
            if not profile.ready():
                self.w.program_path.setText(tr('Сервер не настроен — «Сервер…»'))
                tip = tr('Укажите адрес и логин: «Сервер…»')
            elif known is None:
                self.w.program_path.setText(f'{NAMES[kind]} · {profile.title()}')
                tip = tr(f'Сервер: {profile.address()} · есть ли там программа, покажет проверка подключения')
            else:
                from modules.sextant import cluster

                where = cluster.find_on_server(known[1], kind, profile.setup, profile.setup_of(kind))
                if where:
                    self.w.program_path.setText(f'{NAMES[kind]} · {profile.title()}')
                    tip = tr(f'{NAMES[kind]} на сервере {profile.title()}: {where}')
                    self.w.program_found.show()
                else:
                    self.w.program_path.setText(tr(f'{NAMES[kind]} нет на сервере {profile.title()}'))
                    tip = tr(f'На сервере {profile.title()} не нашлось {NAMES[kind]} ни в PATH, ни среди модулей; если она '
                             'там есть, впишите строки окружения в «Сервер…» (например, module load …).')
        else:
            self.w.program_path.setText(NAMES[kind] if found else tr(f'{NAMES[kind]} не найдена — «Указать…»'))
            tip = tr(f'Программа найдена: {found}') if found else tr(f'{NAMES[kind]} не найдена — укажите файл программы кнопкой «Указать…».')
            self.w.program_found.setVisible(found is not None)
        if self.w.has('program_missing'):
            self.w.program_missing.setVisible(not server and found is None)
            # 0.91.5; xtb and MOPAC on Windows too (conda-forge win-64), CREST not
            installable = kind in (('xtb', 'mopac') if os.name == 'nt' else ('xtb', 'crest', 'mopac'))
            from modules.sextant.remote_job import REMOTE_KINDS

            # «Сервер» only where a server runs it
            missing = (tr(f'{NAMES[kind]} на этом компьютере не нашлась. Укажите файл программы кнопкой «Указать…» '
                          '— или выберите «Сервер», если считаете на кластере.') if kind in REMOTE_KINDS
                       else tr(f'{NAMES[kind]} не найдена — укажите файл программы кнопкой «Указать…».'))
            self.w.program_missing_text.setText(
                missing + (' ' + tr('Её можно и установить в папку программы (conda-forge).') if installable else ''))
            self.w.install_missing_button.setVisible(installable)
        for item in (self.w.program_badge, self.w.program_path, self.w.program_found):
            item.setToolTip(tip)
        if self.w.has('server_button'):
            self.w.server_button.setVisible(server)
            if self.w.has('server_files_button'):
                self.w.server_files_button.setVisible(server)
            self.w.choose_program_button.setVisible(not server)
        if self.w.has('check_server_button'):
            self.w.check_server_button.setVisible(server)
            if not server:
                self.w.server_mark.hide()
                self.w.run_tool.stop_server_watch()  # «Этот компьютер» — the server is not watched
        return found

    def choose_program(self, kind=None, path=None):
        """The file of a program (by default — of the program of Sextant); any of them from «Настройки →
        Программы», path — without the dialog (the tests). Returns the program found, or None."""
        kind = kind if isinstance(kind, str) else self.w.program_kind()  # clicked(bool) passes a flag
        if path is None:
            here = runner.find_program(kind, self.w.run_tool.configured_program(kind))
            start = str(here.parent) if here else '/Applications'
            path, _ = QFileDialog.getOpenFileName(self.w.widget, tr(f'Файл программы {NAMES[kind]}'), start,
                                                  tr('Все файлы (*)'))
        if not path:
            return None
        try:
            runner.check_program(kind, path)
        except ValueError as exc:
            self.w.error(exc)
            return None
        self.w.preferences.setValue(f'programs/{kind}', str(path))
        found = runner.find_program(kind, str(path))
        self.refresh_program_path()
        return found

    def forget_program(self, kind):
        """«Искать самой» — the path given is forgotten, the program is looked for in PATH and the usual
        folders again."""
        self.w.preferences.remove(f'programs/{kind}')
        self.refresh_program_path()
        return runner.find_program(kind, None)

    def program_chosen(self, *args):
        """A program chosen by the user while «Сервер» is on: is it there — the server is checked if it was not
        checked yet (logging in, as «Проверить подключение»); a server being watched answers at once."""
        if getattr(self.w, 'where', 'local') != 'server' or not self.w.has('check_server_button'):
            return None
        if self.w.server_watch_tool.watch is not None:
            return self.refresh_program_path()
        if not remote.load(self.w.preferences).ready():
            return None
        return self.w.run_tool.check_server()

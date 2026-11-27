"""InstallTool: «Установить программы для расчёта» —
the question of Quill, the installation of Open MPI (MS-MPI), xtb, CREST and MOPAC from conda-forge into the folder of
the program as a job of its own, shown in the window of the calculation of this computer, and its end. Was a part of
RunTool; RunTool keeps the same methods, which hand the call over here.
"""

import os
import sys

from azimuth import quill
from azimuth.i18n import tr
from modules.sextant import runner


NAMES = {'openmpi': 'MS-MPI' if os.name == 'nt' else 'Open MPI 4.1', 'xtb': 'xtb', 'crest': 'CREST', 'mopac': 'MOPAC',
         'qe': 'Quantum ESPRESSO', 'nwchem': 'NWChem', 'psi4': 'Psi4', 'cp2k': 'CP2K'}


def size_note(package):
    """The approximate size of a large package (download, then on disk), or '' — measured 2026-11-24 on the owner's Mac
    (osx-arm64, conda-meta of .tools/qe, .tools/nwchem, .tools/psi4 and du); ASSUMPTION: about the same on Linux.
    CP2K (Homebrew on a Mac) was not measured."""
    if package == 'qe' and os.name == 'nt':  # the build of MSYS2 (qe_windows): the mirror, 2026-11-26 — 15 packages
        return tr('≈ 90 МБ загрузки, ≈ 140 МБ на диске')
    return {
        'qe': tr('≈ 280 МБ загрузки, ≈ 900 МБ на диске'),
        'nwchem': tr('≈ 140 МБ загрузки, ≈ 650 МБ на диске'),
        'psi4': tr('≈ 220 МБ загрузки, ≈ 1,1 ГБ на диске'),
    }.get(package, '')


SMALL = ('openmpi', 'xtb', 'crest', 'mopac')  # the shared .tools/calc: together ≈ 26 МБ of download, ≈ 72 МБ on disk
DEFAULT = ('xtb', 'mopac')  # ticked by the menu when not found; the rest only when asked


class InstallTool:
    PORT = (
        'at_place',
        'error',
        'folder_button',
        'input_tool',
        'install_job',
        'install_timer',
        'job_window',
        'job_window_button',
        'mpi_button',
        'notify',
        'run_tool',
        'set_run_status',
        'show_job_window',
        'stop_button',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)
        self.last = None  # the installation that ended last: «Вывод программы» shows its log after it

    def offered(self):
        """What «Установить программы для расчёта…» offers — [(package, name, found path or None)]: MPI, xtb, CREST (not
        on Windows: no build there), MOPAC; found — where the program is already (on this computer, in PATH or the usual
        folders)."""
        names = NAMES
        found = {'openmpi': runner.find_mpirun()}
        for kind in ('xtb', 'crest', 'mopac'):
            found[kind] = runner.find_program(kind, self.w.run_tool.configured_program(kind))
        from modules.sextant import install_tools

        # Quantum ESPRESSO on Windows — the native build of MSYS2 (modules/sextant/qe_windows.py)
        packages = ('openmpi', 'xtb', 'mopac', 'qe') if os.name == 'nt' else ('openmpi', 'xtb', 'crest', 'mopac', 'qe')
        found['qe'] = install_tools.qe_program()
        if os.name != 'nt':
            packages += ('nwchem',)  # its own prefix and MPI, as Quantum ESPRESSO
            found['nwchem'] = runner.find_program('nwchem', self.w.run_tool.configured_program('nwchem'))
            packages += ('psi4',)  # its own prefix and Python
            found['psi4'] = runner.find_program('psi4', self.w.run_tool.configured_program('psi4'))
            if install_tools.cp2k_installable():  # Linux (conda-forge); and a Mac (Homebrew)
                packages += ('cp2k',)
                found['cp2k'] = install_tools.cp2k_program()
        return [(p, names[p], found.get(p)) for p in packages]

    def choose_packages(self, chosen=None):
        """The dialog of the menu: a tick for each program offered — xtb and MOPAC ticked when not found yet (DEFAULT),
        the large ones with their size (size_note); the path of the one found in its tip and «уже есть». chosen — the packages ticked without the dialog (the tests). Returns the
        packages to install, or None (cancelled, nothing ticked)."""
        from PySide6.QtWidgets import QCheckBox, QDialog, QDialogButtonBox, QLabel, QVBoxLayout

        from modules.sextant import install_tools

        offered = self.offered()
        box = QDialog(self.w.widget)
        box.setWindowTitle(tr('Программы для расчёта'))
        layout = QVBoxLayout(box)
        head = QLabel(tr('Что установить?'))
        head.setObjectName('cardtitle')
        layout.addWidget(head)
        ticks = {}
        for package, name, found in offered:
            size = size_note(package)
            tick = QCheckBox(name + (' — ' + tr('уже есть') if found else (' — ' + size if size else '')))
            tick.setChecked(found is None and package in DEFAULT)  # xtb and MOPAC; the rest only when asked
            tick.setToolTip(str(found) if found else tr('Не найдена на этом компьютере'))
            ticks[package] = tick
            layout.addWidget(tick)
        note = QLabel(tr(f'С conda-forge в папку программы ({install_tools.prefix(install_tools.default_root())}). Нужен '
                         'интернет. xtb, MOPAC, CREST и MPI вместе — около 30 МБ загрузки и 75 МБ на диске; первая установка '
                         'ещё скачивает менеджер пакетов micromamba (7 МБ). Права администратора не нужны, '
                         'настройки терминала не меняются.') + (' ' + tr('Quantum ESPRESSO, NWChem и Psi4 — в '
                                                                        'отдельные папки .tools/qe, .tools/nwchem и .tools/psi4.') if os.name != 'nt' else ' ' + tr(
                             'Quantum ESPRESSO для Windows берётся из репозитория MSYS2 (сборка без MPI: процессы '
                             'становятся потоками OpenMP) и ставится в .tools/qe.'))
                     + (' ' + tr('CP2K на Mac ставится через Homebrew (brew install cp2k); если Homebrew нет — '
                                 'сначала установите его с brew.sh.') if sys.platform == 'darwin' else ''))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr('Установить'))
        buttons.accepted.connect(box.accept)
        buttons.rejected.connect(box.reject)
        layout.addWidget(buttons)
        self.choice_box = box  # the tests look at it
        if chosen is not None:
            for package, tick in ticks.items():
                tick.setChecked(package in chosen)
        elif box.exec() != QDialog.DialogCode.Accepted:
            return None
        packages = tuple(p for p, tick in ticks.items() if tick.isChecked())
        return packages or None

    def install_tools_dialog(self, packages=None, chosen=None):
        """packages — what a button of Sextant installs (its question first); None — the menu: the choice of the
        programs (choose_packages) is the question."""
        from PySide6.QtWidgets import QMessageBox

        from modules.sextant import install_tools

        if packages is None:
            packages = self.choose_packages(chosen)
            return self.start_install(packages) if packages else None
        names = NAMES
        if os.name == 'nt':  # CREST has no Windows build
            packages = tuple(p for p in packages if p != 'crest') or ('xtb',)
        # the question first (in bold), the details under it
        text = tr(f'Скачать и установить {", ".join(names[p] for p in packages)}?') + '\n' + tr(
            f'С conda-forge в папку программы ({install_tools.prefix(install_tools.default_root())}). Нужен интернет; '
            'займёт несколько минут и до нескольких сотен МБ. Права администратора не нужны, настройки терминала не меняются.'
        )
        answer = quill.question(  # Quill with her tools
            self.w.widget, tr('Программы для расчёта'), text,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.Yes, 'install',
        )
        if answer != QMessageBox.StandardButton.Yes:
            return None
        return self.start_install(packages)

    def start_install(self, packages):
        with self.w.at_place('local'):  # the installation is shown in the window of this computer
            return self._start_install(packages)

    def poll_install(self):
        with self.w.at_place('local'):
            return self._poll_install()

    def _start_install(self, packages):
        import sys

        from modules.sextant import install_tools

        if self.w.install_job is not None and self.w.install_job.running:
            self.w.notify(tr('Установка уже идёт.'), 6000)
            self.w.show_job_window()  # where it goes on
            return None
        root = install_tools.default_root()
        log = root / '.tools' / 'install.log'
        log.parent.mkdir(parents=True, exist_ok=True)
        if getattr(sys, 'frozen', False):  # the .exe of the installer runs the script itself (gui_launcher)
            command = (sys.executable, '--install-tools', '--root', str(root), '--log', str(log), *packages)
        else:
            command = (sys.executable, '-m', 'modules.sextant.install_tools', '--root', str(root), *packages)
        # the console of a Russian Windows is cp1251: «→» of the log broke the installation (UnicodeEncodeError,
        # Windows check 2026-11-24) — the script writes UTF-8
        env = dict(__import__('os').environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1')
        spec = runner.JobSpec('tools', root, command, log, env, log)
        try:
            self.w.install_job = runner.Job(spec).start()
        except ValueError as exc:
            self.w.error(exc)
            return None
        self.w.mpi_button.hide()
        self.install_places = install_tools.places(root, packages)  # NWChem, QE, CP2K — folders of their own
        self.w.job_window.begin(tr('Установка программ для расчёта'),
                                ' '.join(packages) + ' → ' + ', '.join(str(p) for p in self.install_places))
        self.w.job_window_button.hide()  # the panel is in this card
        self.w.stop_button.setEnabled(False)
        self.w.folder_button.setEnabled(False)
        self.w.job_window_button.show()
        self.w.set_run_status(tr('Ставлю программы для расчёта… (лог — .tools/install.log)'))
        self.w.show_job_window()
        self.w.install_timer.start()
        return self.w.install_job

    def _poll_install(self):
        job = self.w.install_job
        if job is None:
            self.w.install_timer.stop()
            return None
        code = job.poll()
        if code is None:
            return None
        self.w.install_timer.stop()
        self.w.install_job = None
        self.last = job  # the installation that ended last: «Вывод программы» shows its log after the end
        self.w.job_window.finish()
        self.w.folder_button.setEnabled(True)
        if code == 0 and '[tools] done' in job.text():
            self.w.job_window.show_picture('install-done')  # not «Расчёт закончен»: the programs are installed
            # where they are, and that Finder hides
            # the folders whose names begin with a dot
            from modules.sextant import install_tools

            where = ', '.join(str(p) for p in getattr(self, 'install_places', None)
                              or [install_tools.prefix(install_tools.default_root())])
            hidden = (' ' + tr('Папка .tools скрыта в Finder: показать скрытые — ⌘⇧.')) if sys.platform == 'darwin' else ''
            self.w.set_run_status(tr('Программы для расчёта установлены.') + ' ' + (tr('Папки:') if ', ' in where else tr('Папка:')) + f' {where}.' + hidden)
        else:
            self.w.set_run_status(tr(f'Установка не удалась (код {code}): что случилось — в «Вывод программы» (.tools/install.log).'))
        self.w.run_tool.refresh_program_path()
        self.w.input_tool.refresh_input()
        return code

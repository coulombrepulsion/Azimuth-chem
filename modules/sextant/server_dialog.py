"""Sextant: the dialog «Сервер для расчётов» — the profile of remote.py.

§1 PURPOSE
    The user's own access to a server: address, port, login, folder of calculations, start command, intermediate
    server, and — for a server behind OpenVPN — the profile of OpenVPN Connect the program switches on itself
    (vpn.py). The login is the window; «Настройки сервера» slides out the calculations on the server (folder,
    environment, SLURM) and the VPN to its right, «Скрыть настройки сервера» back (toggle_settings; also when a field
    there is wrong at «Сохранить»). «Проверить подключение» tells whether the server answers; if not and a VPN profile is chosen, it asks
    OpenVPN Connect to connect and waits up to WAIT_S seconds, checking every CHECK_MS.
    Several profiles — the list on top, «Новый» and «Удалить», «Сохранить» keeps the profile under its name and
    chooses it; the password field (kept for the session, and in the Keychain of macOS or the Credential Manager of Windows when ticked — keychain.py; never
    in the settings); drawn like the program — cards on the background of the sections, its buttons.
    «Строки окружения» (the lines of job.sh that put ORCA into PATH; empty — found on the server) instead of the
    start command of 0.63.0 (kept hidden, so an old profile keeps it); «Узнать ресурсы» connects (password, VPN —
    server_access.open_server) and shows what the server has now: free cores, memory, disk, where ORCA is, and the
    environment lines it would use.
§4 SPECIFICATION ServerDialog(profile, parent=None, connect_app=None, settings=None): profiles (QComboBox, with
    settings), new_button, delete_button, fields name, host, port, user, password, remember, folder, setup
    (QPlainTextEdit), command (hidden), jump; probe_button, probe() -> Resources | None; new_profile();
    setup_program (QComboBox: '' — the lines of every job, a kind of remote.SETUP_KINDS — the lines of its jobs only;
    «·» marks those with lines), show_setup(), keep_setup(), mark_setups() — setup shows and edits the lines of the one
    chosen;
    choose_profile(index); remove_profile(); save() (with settings: the profile and the password); vpn (QComboBox, data
    — the id of the profile, '' — none), vpn_disconnect (QCheckBox), check_button, status; profile() -> ServerProfile;
    vpn_on, vpn_off (icon buttons), connect_vpn() -> bool, disconnect_vpn() -> bool — the VPN by hand; the window of
    OpenVPN Connect is kept off this one (vpn.connect hides it on macOS, come_forward() raises this window) and shown
    when it has not connected in vpn.REVEAL_AFTER_S;
    load_vpn_profiles() -> [VpnProfile]; import_vpn(path) -> bool; check() -> bool (True: the server answers now; False:
    not yet — waiting, or no VPN); problems, preview (QLabel); accept() only when the profile is valid;
    settings_panel, settings_button, toggle_settings(shown=None) -> bool, settings_shown() -> bool.
§7 TEST CASES tests/test_gui.py::test_sextant_where_to_calculate.
"""

import os
import time
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLayout,
    QLineEdit,
    QPlainTextEdit,
    QSpinBox,
    QVBoxLayout,
)

from modules.sextant import keychain, remote, vpn
from modules.sextant.remote import ServerProfile
from azimuth.i18n import tr
from azimuth.ui import button, card, icon_button, label

WAIT_S = 60
SETUP_TITLES = {'orca': 'ORCA', 'mopac': 'MOPAC', 'xtb': 'xtb', 'qe': 'Quantum ESPRESSO', 'cp2k': 'CP2K'}
SETUP_EXAMPLES = {'orca': 'module load orca-6.1.1', 'mopac': 'export PATH=/opt/mopac/bin:$PATH',
                  'xtb': 'export PATH=/opt/anaconda3/envs/xtb/bin:$PATH',
                  'qe': 'module load qe', 'cp2k': 'module load cp2k'}
CHECK_MS = 2000


class _Status(QLabel):
    """The line of the answer of the server: tells when its text changes (ServerDialog.fit_status)."""

    changed = Signal()

    def setText(self, text):
        super().setText(text)
        # an empty line takes no room: it kept the buttons under the cards a line and two gaps lower (the owner,
        # 2026-11-23: «нижние кнопки теперь тоже поднять можно»)
        self.setVisible(bool(text))
        self.changed.emit()


class ServerDialog(QDialog):
    def __init__(self, profile, parent=None, connect_app=None, settings=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Сервер для расчётов'))
        self.setObjectName('workspace')  # the background of the sections, cards on it
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.settings = settings
        self.loaded_title = profile.title() or None
        self.connect_app = connect_app if connect_app is not None else vpn.find_connect()
        self.waiting_since = None
        self.timer = QTimer(self)
        self.timer.setInterval(CHECK_MS)
        self.timer.timeout.connect(self._wait_step)
        outer = QVBoxLayout(self)
        # 2026-11-19 (the same screenshot: «Строки окружения» lay over the line «Вход: … Перед ORCA …»): the window is
        # never smaller than what its cards need — it was, and Qt laid their rows over each other
        outer.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize)
        outer.setContentsMargins(18, 18, 18, 18)
        outer.setSpacing(14)
        # the saved profiles
        top = QHBoxLayout()
        top.setSpacing(8)
        top.addWidget(label(tr('Профиль') + ':'))  # as the names of the other fields
        self.profiles = QComboBox()
        self.profiles.setMinimumWidth(260)
        top.addWidget(self.profiles, 1)
        self.new_button = icon_button(tr('Новый профиль'), self.new_profile, 'plus')
        self.delete_button = icon_button(tr('Удалить профиль'), self.remove_profile, 'delete')
        top.addWidget(self.new_button)
        top.addWidget(self.delete_button)
        outer.addLayout(top)
        columns = QHBoxLayout()
        columns.setSpacing(14)
        outer.addLayout(columns, 1)
        # the login
        frame, box = card(tr('Вход'))
        form = QFormLayout()
        form.setSpacing(10)
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr('например, Кластер лаборатории'))
        self.host = QLineEdit()
        self.host.setPlaceholderText('10.0.0.5')
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setFixedWidth(110)
        self.user = QLineEdit()
        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText(tr('спросить при подключении'))
        # macOS: the Keychain; Windows: the Credential Manager. The text is short: a longer one widens the login
        # window past 500 px
        windows = os.name == 'nt'
        self.remember = QCheckBox(tr('Запомнить в Windows') if windows else tr('Запомнить в Связке ключей'))
        if windows:
            self.remember.setToolTip(tr('Пароль хранится в диспетчере учётных данных Windows, зашифрованный ключом '
                                        'вашей учётной записи Windows.'))
        self.remember.setVisible(keychain.available())
        self.jump = QLineEdit()
        self.jump.setPlaceholderText(tr('нет'))
        for title, widget in ((tr('Название'), self.name), (tr('Адрес'), self.host), (tr('Порт'), self.port),
                              (tr('Логин'), self.user), (tr('Пароль'), self.password), ('', self.remember),
                              (tr('Промежуточный сервер'), self.jump)):
            form.addRow(title, widget)
        box.addLayout(form)
        # the store of the system, where there is one: elsewhere the note says no more than is true (the owner's Windows,
        # 2026-11-24)
        if not keychain.available():
            note = tr('Пароль не попадает в настройки программы: он хранится только до выхода из программы.')
        elif windows:
            note = tr('Пароль не попадает в настройки программы: он хранится до выхода из программы, '
                      'а с галочкой — в диспетчере учётных данных Windows.')
        else:
            note = tr('Пароль не попадает в настройки программы: он хранится до выхода из программы, '
                      'а с галочкой — в Связке ключей macOS.')
        box.addWidget(label(note, 'subtitle'))
        # what is done with the login stands with it (the owner, 2026-11-22: the window of the login narrower — the six
        # buttons in one row under the cards made it 820 px wide)
        self.check_button = button(tr('Проверить подключение'), self.check)
        self.key_button = button(tr('Вход без пароля'), self.key_login)
        self.key_button.setToolTip(tr('Создать ключ программы и один раз по паролю записать его на сервер — дальше вход '
                                      'без пароля (на Windows без этого пароль спрашивался бы на каждую команду)'))
        login_buttons = QHBoxLayout()
        login_buttons.setSpacing(8)
        login_buttons.addWidget(self.check_button)
        login_buttons.addWidget(self.key_button)
        login_buttons.addStretch(1)
        box.addLayout(login_buttons)
        # «Узнать ресурсы» under them, not in the row of «Сохранить»: that row set the width of the window («и само
        # окно можно сделать еще уже»)
        self.probe_button = button(tr('Узнать ресурсы'), self.probe)
        self.probe_button.setToolTip(tr('Войти на сервер и узнать свободные ядра, память, диск и где ORCA'))
        probe_row = QHBoxLayout()
        probe_row.addWidget(self.probe_button)
        probe_row.addStretch(1)
        box.addLayout(probe_row)
        box.addStretch(1)
        columns.addWidget(frame, 1)
        right = QVBoxLayout()
        right.setSpacing(14)
        # the calculations on the server
        frame, box = card(tr('Расчёты на сервере'))
        form = QFormLayout()
        form.setSpacing(10)
        self.folder = QLineEdit()
        self.command = QLineEdit()  # unused since kept so that an old profile keeps it
        self.command.hide()
        # the lines of the job script that put a program into PATH on this server: those of every job of the profile
        # («Все программы») and those of the jobs of one program only (the list above the field chooses whose lines the
        # field shows) — the lines CP2K needs have no place in a job of ORCA
        self.setup_program = QComboBox()
        self.setup_program.addItem(tr('Все программы'), '')
        for kind in remote.SETUP_KINDS:
            self.setup_program.addItem(SETUP_TITLES[kind], kind)
        self.setup_program.setToolTip(tr('Чьи строки показаны ниже: «Все программы» — попадают в каждую задачу этого '
                                         'сервера; строки программы — только в её задачи, после общих. У программы со '
                                         'своими строками они используются как есть, сама она на сервере не ищется'))
        self._setups = {'': ''}  # '' — the common lines, a kind — its own; the field shows those of _setup_shown
        self._setup_shown = ''
        self._found = {}  # {kind: the lines found on the server by «Узнать ресурсы»}
        self.setup = QPlainTextEdit()
        self.setup.setFixedHeight(70)  # three lines (the hint of an empty field has two); the whole width of the card
        self.setup.setToolTip(tr('Строки выполняются в задаче перед программой — как в Терминале после входа на сервер'))
        self.setup_program.currentIndexChanged.connect(self.show_setup)
        # short titles: the panel of the settings is as wide as the card of the login (the owner, 2026-11-22)
        form.addRow(tr('Папка расчётов'), self.folder)
        form.addRow(tr('Окружение для'), self.setup_program)
        form.addRow(self.setup)  # the whole width of the card: the lines are paths, and long
        # what a cluster other than the laboratory ones wants of every job (empty — its defaults)
        self.partition, self.time_limit, self.account, self.qos = QLineEdit(), QLineEdit(), QLineEdit(), QLineEdit()
        self.partition.setPlaceholderText(tr('по умолчанию'))
        self.time_limit.setPlaceholderText(tr('по умолчанию'))
        self.account.setPlaceholderText(tr('нет'))
        self.qos.setPlaceholderText(tr('нет'))
        self.partition.setToolTip(tr('#SBATCH -p — раздел кластера (sinfo показывает разделы); свободные ядра '
                                     'узнаются в нём же'))
        self.time_limit.setToolTip(tr('#SBATCH -t — сколько задаче дают времени: 90 (минуты), 12:00:00, 2-00:00:00 '
                                      '(дни-часы:минуты:секунды). Пусто — предел раздела по умолчанию, на больших '
                                      'кластерах он бывает коротким'))
        self.account.setToolTip(tr('#SBATCH -A — проект, на который пишется время, если кластер его требует'))
        self.qos.setToolTip(tr('#SBATCH --qos — качество обслуживания, если на кластере их несколько. Другие строки '
                               '#SBATCH (--gres, --constraint…) можно вписать в «Строки окружения»'))
        for left, right_field, one, two in ((self.partition, self.time_limit, tr('раздел'), tr('время')),
                                            (self.account, self.qos, tr('проект'), 'QoS')):
            pair = QHBoxLayout()
            pair.setSpacing(6)
            pair.addWidget(left, 1)
            pair.addWidget(label(two, 'subtitle'))
            pair.addWidget(right_field, 1)
            form.addRow('SLURM: ' + one, pair)
            for field in (left, right_field):
                field.setMinimumWidth(60)
        box.addLayout(form)
        self.preview = label('', 'subtitle')
        self.preview.setWordWrap(True)
        self.preview.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        # room for the login and three wrapped lines of what stands before the program: the layout counts a wrapped
        # label as one line, and with the lines of a program next to the common ones the text took four — the card
        # was then squeezed, and the field of the lines lay over the rows of SLURM
        # the lines «Вход: … / Перед ORCA в задаче: …» repeated the fields above them and took four lines of the card
        # (the owner, 2026-11-22: «лишние фразы и комментарии убери»): the text is the tip of the field of the lines
        self.preview.hide()
        # the rows stay under the title when the card is taller than they need (the column is as tall as the login):
        # left to the layout, the room went above the title, and «Расчёты на сервере» stood lower than «Вход»
        box.addStretch(1)
        right.addWidget(frame)
        # OpenVPN Connect switched on by the program
        frame, box = card(tr('VPN'))
        self.vpn = QComboBox()
        vpn_row = QHBoxLayout()
        vpn_row.setSpacing(6)
        vpn_row.addWidget(self.vpn, 1)
        # the VPN switched on and off by hand (the owner, 2026-11-22); the program still switches it on itself when the
        # server does not answer
        self.vpn_on = icon_button(tr('Подключить VPN'), self.connect_vpn, 'play')
        self.vpn_off = icon_button(tr('Отключить VPN'), self.disconnect_vpn, 'stop')
        vpn_row.addWidget(self.vpn_on)
        vpn_row.addWidget(self.vpn_off)
        self.vpn.currentIndexChanged.connect(self.update_vpn_buttons)
        gui = vpn.is_gui(self.connect_app)  # OpenVPN GUI of the community (Windows) instead of OpenVPN Connect
        self.vpn_refresh = icon_button(tr('Профили OpenVPN GUI') if gui else tr('Профили OpenVPN Connect'),
                                       self.load_vpn_profiles, 'search')
        self.vpn_import = icon_button(tr('Импортировать .ovpn…'), self.choose_ovpn, 'file-open')
        vpn_row.addWidget(self.vpn_refresh)
        vpn_row.addWidget(self.vpn_import)
        box.addLayout(vpn_row)
        self.vpn_disconnect = QCheckBox(tr('Отключать VPN после расчётов'))
        self.vpn.setMinimumWidth(80)
        box.addWidget(self.vpn_disconnect)
        # said in the tip of the list, not as a note under it: the two lines of the note made the window with the
        # settings taller than a laptop screen of 768 px once the environment lines got their list of programs
        self.vpn.setToolTip(tr('Если сервер не отвечает, программа сама попросит OpenVPN GUI подключиться.') if gui
                            else tr('Если сервер не отвечает, программа сама попросит OpenVPN Connect подключиться.'))
        self.vpn_disconnect.setToolTip(tr('VPN отключается, когда расчётов на сервере не осталось'))
        if self.connect_app is None:
            for item in (self.vpn_refresh, self.vpn_import, self.vpn_on, self.vpn_off):
                item.setEnabled(False)
            self.vpn.setToolTip(tr('Не найден ни OpenVPN Connect, ни OpenVPN GUI') if os.name == 'nt'
                                else tr('OpenVPN Connect не найден в «Программах»'))
        right.addWidget(frame)
        right.addStretch(1)
        # the settings of the server — the calculations on it (folder, environment, SLURM) and the VPN — slide out to
        # the right of the login on «Настройки сервера» (the owner, 2026-11-22: the login is the window; the rest when
        # asked)
        from PySide6.QtWidgets import QSizePolicy, QWidget

        self.settings_panel = QWidget()
        self.settings_panel.setObjectName('serverSettings')
        self.settings_panel.setLayout(right)
        right.setContentsMargins(0, 0, 0, 0)
        self.settings_panel.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.settings_panel.hide()
        self.settings_width = 0
        self.columns = columns
        columns.addWidget(self.settings_panel)
        self.problems = label('', 'error')
        self.problems.setWordWrap(True)
        self.problems.hide()
        outer.addWidget(self.problems)
        # the answer of the server
        # (its free cores, memory, disk, ORCA) on a line of its own over the buttons — it was squeezed between them
        # into a narrow column of six lines
        self.status = _Status('')
        self.status.hide()
        self.status.setObjectName('subtitle')
        self.status.changed.connect(self.fit_status)
        self.status.setWordWrap(True)
        self.status.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        outer.addWidget(self.status)
        bottom = QHBoxLayout()
        bottom.setSpacing(8)
        # clicked(bool) of a button that is not checkable is always False: given to toggle_settings as «shown», it
        # hid a panel that was hidden — the button opened nothing since it was made (the owner, 2026-11-22)
        self.settings_button = button(tr('Настройки сервера'), lambda *args: self.toggle_settings())
        self.settings_button.setToolTip(tr('Папка расчётов, строки окружения, SLURM и VPN'))
        bottom.addWidget(self.settings_button)
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Отмена'), self.reject))
        self.save_button = button(tr('Сохранить'), self.accept, True)
        self.save_button.setDefault(True)
        bottom.addWidget(self.save_button)
        outer.addLayout(bottom)
        for widget in (self.name, self.host, self.user, self.folder, self.command, self.jump, self.setup, self.partition,
                       self.time_limit, self.account, self.qos):
            widget.textChanged.connect(self.update_preview)
        self.port.valueChanged.connect(self.update_preview)
        self.fill(profile)
        self.fill_profile_list()
        self.profiles.currentIndexChanged.connect(self.choose_profile)
        self.animation = None
        self.login_card = columns.itemAt(0).widget()
        # the login alone: as narrow as its fields allow (the size hint of the wrapped note asked 860 px)
        # as tall as the window with the settings out needs — opening them does not move anything down (the owner,
        # 2026-11-23: «немного смещается по высоте … при открытии доп настроек»)
        self.base_height = self.minimumSizeHint().height()  # till the window is shown and measured
        self.resize(max(460, self.minimumSizeHint().width()), self.base_height)

    # -- the settings of the server, sliding out ---------------------------------------------------------------
    SETTINGS_WIDTH = 380  # the least width of the cards of the calculations on the server and of the VPN
    SLIDE_MS = 220

    def settings_shown(self):
        return not self.settings_panel.isHidden() and self.settings_width > 0

    def toggle_settings(self, shown=None):
        """Slide the settings out (or back); shown — True / False, None — the other way. Returns the state."""
        from PySide6.QtCore import QEasingCurve, QVariantAnimation

        from azimuth.polish import animations_allowed

        shown = not self.settings_shown() if shown is None else bool(shown)
        self.settings_button.setText(tr('Скрыть настройки сервера') if shown else tr('Настройки сервера'))
        if self.animation is not None:
            self.animation.stop()
        if self.settings_width == 0:  # the login card as wide as the window gives it now, before the panel shows
            margins = self.layout().contentsMargins()
            self.login_width = self.width() - margins.left() - margins.right()
        width = self.settings_panel_target()
        start = self.settings_width
        end = width if shown else 0
        self.settings_panel.show()
        if not animations_allowed() or start == end:
            self._slide(end)
            return shown
        self.animation = QVariantAnimation(self)
        self.animation.setStartValue(start)
        self.animation.setEndValue(end)
        self.animation.setDuration(self.SLIDE_MS)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.animation.valueChanged.connect(lambda value: self._slide(int(value)))
        self.animation.start()
        return shown

    def _slide(self, width):
        """The panel this wide; the card of the login keeps its width, the window is exactly as wide as the two (its
        left edge in place). Left to the layout, a wider window gave the room to the login card and pushed the panel
        out of the window."""
        margins = self.layout().contentsMargins()
        login = self.login_width
        self.settings_width = width
        gap = self.columns.spacing() if width else 0
        self.settings_panel.setFixedWidth(width)
        self.login_card.setFixedWidth(login)
        self.setFixedWidth(margins.left() + login + gap + width + margins.right())
        if width == 0:
            self.settings_panel.hide()
        self.layout().activate()
        self.fit_wrapped()
        if width == 0:  # the login alone again: the height it had (the window grew for the settings)
            self.resize(self.width(), max(self.base_height, self.minimumSizeHint().height()))

    def fit_status(self):
        """The line of the answer gets the height of its text, and the window grows by it: the layout counts a wrapped
        label as one line, so a long answer (the programs found on the server) squeezed the card of the login — its
        fields lay over each other (the owner's screenshot, 2026-11-23)."""
        width = self.status.width() if self.status.width() > 60 else self.width() - 40
        need = self.status.heightForWidth(width) if self.status.text() else 0
        if need != self.status.minimumHeight():
            self.status.setMinimumHeight(max(0, need))
            self.layout().activate()
            least = self.layout().minimumSize().height()
            if least > self.height():
                self.resize(self.width(), least)

    def fit_wrapped(self):
        """Every wrapped note gets the height its lines take at its width now: the layout counts such a label as one
        line, so a card with a note of two or three lines was given too little room and its rows lay over each other
        (the field of the environment lines over «SLURM: раздел», 2026-11-22)."""
        from PySide6.QtWidgets import QLabel

        changed = False
        for root in (self.login_card, self.settings_panel):
            if root.isHidden():
                continue
            for note in root.findChildren(QLabel):
                if note is self.preview or not note.wordWrap() or note.width() < 60:
                    continue
                need = note.heightForWidth(note.width())
                if need > 0 and need != note.minimumHeight():
                    note.setMinimumHeight(need)
                    changed = True
        if changed:
            self.layout().activate()

    def measure_height(self):
        """base_height — what the window with the settings out needs: they are put out and back at once, before
        anything is painted; the login alone is given the same height."""
        if self.settings_shown() or self.animation is not None or not self.isVisible():
            return
        margins = self.layout().contentsMargins()
        self.login_width = self.width() - margins.left() - margins.right()
        self.settings_panel.show()
        self._slide(self.settings_panel_target())  # the settings out, as «Настройки сервера» puts them
        self.base_height = max(self.base_height, self.height(), self.layout().minimumSize().height())
        self._slide(0)
        self.setFixedWidth(margins.left() + self.login_width + margins.right())
        if self.height() < self.base_height:
            self.resize(self.width(), self.base_height)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self.fit_wrapped)  # the widths are known once the window is laid out
        QTimer.singleShot(0, self.measure_height)  # and the heights of the wrapped notes with them

    def settings_panel_target(self):
        """As wide as the card of the login next to it (not narrower than its own rows need)."""
        login = getattr(self, 'login_width', 0) or self.login_card.width()
        return max(self.SETTINGS_WIDTH, login, self.settings_panel.layout().minimumSize().width())

    # -- profiles ---------------------------------------------------------------------------------------------
    def fill(self, profile):
        self.name.setText(profile.name)
        self.host.setText(profile.host)
        self.port.setValue(profile.port if isinstance(profile.port, int) and 1 <= profile.port <= 65535 else 22)
        self.user.setText(profile.user)
        self.folder.setText(profile.folder)
        self.command.setText(profile.command)
        self._setups = {'': profile.setup, **{kind: profile.setup_of(kind) for kind in remote.SETUP_KINDS}}
        self._setup_shown = self.setup_program.currentData() or ''
        self.setup.setPlainText(self._setups.get(self._setup_shown, ''))
        self.mark_setups()
        for field, value in ((self.partition, profile.partition), (self.time_limit, profile.time_limit),
                             (self.account, profile.account), (self.qos, profile.qos)):
            field.setText(value)
        self.jump.setText(profile.jump)
        if hasattr(self, 'vpn_on'):
            QTimer.singleShot(0, self.update_vpn_buttons)
        self.vpn.clear()
        self.vpn.addItem(tr('Без VPN'), '')
        if profile.vpn_id:
            self.vpn.addItem(profile.vpn_name or profile.vpn_id, profile.vpn_id)
            self.vpn.setCurrentIndex(1)
        self.vpn_disconnect.setChecked(profile.vpn_disconnect)
        saved = keychain.get(keychain.service_for(profile), profile.user) if profile.host and profile.user else None
        self.password.setText(saved or '')
        self.remember.setChecked(bool(saved) or keychain.available())
        self.loaded_title = profile.title() or None
        self.problems.hide()
        self.status.clear()
        self.update_preview()

    def fill_profile_list(self):
        self.profiles.blockSignals(True)
        self.profiles.clear()
        titles = [p.title() for p in remote.load_all(self.settings)] if self.settings is not None else []
        for title in titles:
            self.profiles.addItem(title, title)
        if self.loaded_title not in titles:
            self.profiles.addItem(tr('Новый профиль'), None)
        self.profiles.setCurrentIndex(max(0, self.profiles.findData(self.loaded_title)) if self.loaded_title in titles
                                      else self.profiles.count() - 1)
        self.profiles.blockSignals(False)
        self.profiles.setVisible(self.settings is not None)
        for item in (self.new_button, self.delete_button):
            item.setVisible(self.settings is not None)
        self.delete_button.setEnabled(self.loaded_title in titles)

    def choose_profile(self, index):
        title = self.profiles.itemData(index)
        if title is None or self.settings is None:
            return None
        for profile in remote.load_all(self.settings):
            if profile.title() == title:
                self.fill(profile)
                self.fill_profile_list()
                return profile
        return None

    def new_profile(self):
        self.fill(ServerProfile())
        self.fill_profile_list()
        self.name.setFocus()

    def remove_profile(self):
        if self.settings is None or not self.loaded_title:
            return []
        old = self.profile()
        keychain.delete(keychain.service_for(old), old.user)
        left = remote.remove(self.settings, self.loaded_title)
        self.fill(left[0] if left else ServerProfile())
        self.fill_profile_list()
        return left

    def save(self):
        """Keep the profile under its name (replacing the one loaded) and its password; True when it was valid."""
        profile = self.profile()
        problems = profile.validate()
        if problems:
            self.problems.setText('\n'.join(problems))
            self.problems.show()
            from dataclasses import replace

            # a wrong field of the settings (the folder, SLURM) is shown: they slide out
            if replace(profile, host='server', user='user', port=22, jump='', command='').validate():
                self.toggle_settings(True)
            return False
        self.problems.hide()
        if self.settings is not None:
            remote.save(self.settings, profile, self.loaded_title)
            self.loaded_title = profile.title()
            self.fill_profile_list()
        if self.password.text():
            keychain.put(keychain.service_for(profile), profile.user, self.password.text(), self.remember.isChecked())
        return True

    # -- the environment lines of each program ------------------------------------------------------------------------
    def keep_setup(self):
        """The text of the field goes to the lines it shows (before another program is shown, before the profile is read)."""
        self._setups[self._setup_shown] = self.setup.toPlainText().strip()

    def show_setup(self, *args):
        """The field shows the lines of the program chosen in the list (those of the one shown before are kept)."""
        self.keep_setup()
        self._setup_shown = self.setup_program.currentData() or ''
        self.setup.blockSignals(True)
        self.setup.setPlainText(self._setups.get(self._setup_shown, ''))
        self.setup.blockSignals(False)
        self.mark_setups()
        self.update_preview()

    def mark_setups(self):
        """«·» after the names in the list that have lines, and the hint of the empty field."""
        for k in range(self.setup_program.count()):
            kind = self.setup_program.itemData(k) or ''
            title = tr('Все программы') if not kind else SETUP_TITLES[kind]
            self.setup_program.setItemText(k, title + (' ·' if self._setups.get(kind, '').strip() else ''))
        kind = self._setup_shown
        if not kind:
            hint = tr('Строки для каждой задачи этого сервера. Пусто — ничего.\nНапример: #SBATCH --gres=gpu:1')
        elif self._found.get(kind):
            hint = tr('Найдено на сервере (будет использовано):\n') + self._found[kind]
        else:
            hint = tr('Пусто — {} найдётся на сервере сама (модуль или PATH).\nНапример: {}').format(
                SETUP_TITLES[kind], SETUP_EXAMPLES[kind])
        self.setup.setPlaceholderText(hint)
        self.setup.viewport().update()  # the hint of the program shown before stayed painted under the new one

    def profile(self):
        self.keep_setup()
        return ServerProfile(self.name.text().strip(), self.host.text().strip(), self.port.value(),
                             self.user.text().strip(), self.folder.text().strip(), self.command.text().strip(),
                             self.jump.text().strip(), vpn_id=self.vpn.currentData() or '',
                             vpn_name=self.vpn.currentText() if self.vpn.currentData() else '',
                             vpn_disconnect=self.vpn_disconnect.isChecked(), setup=self._setups.get('', ''),
                             partition=self.partition.text().strip(), time_limit=self.time_limit.text().strip(),
                             account=self.account.text().strip(), qos=self.qos.text().strip(),
                             setups={kind: self._setups[kind] for kind in remote.SETUP_KINDS if self._setups.get(kind)})

    def update_preview(self, *args):
        p = self.profile()
        kind = self._setup_shown or 'orca'  # the program whose lines are shown (ORCA with the common ones)
        own = p.setup + ('\n' + p.setup_of(kind) if p.setup_of(kind) else '')
        lines = '; '.join(line.strip() for line in own.splitlines() if line.strip())
        slurm = ' '.join(d.replace('#SBATCH ', '') for d in p.directives())
        self.preview.setText(tr('Вход: ') + p.address() + '\n' + tr('Перед {} в задаче: ').format(SETUP_TITLES[kind]) +
                             (lines or tr('найдётся на сервере при запуске'))
                             + ('\n' + tr('Задаче SLURM: ') + slurm if slurm else ''))
        self.setup.setToolTip(tr('Строки выполняются в задаче перед программой — как в Терминале после входа на сервер')
                              + '\n\n' + self.preview.text())

    def probe(self):
        """Connect and show what the server has now (server_access.open_server); the resources or None."""
        from modules.sextant import cluster, server_access
        from modules.sextant.ssh import SshError

        p = self.profile()
        problems = p.validate()
        if problems:
            self.problems.setText('\n'.join(problems))
            self.problems.show()
            return None
        self.problems.hide()
        if self.password.text():
            keychain.put(keychain.service_for(p), p.user, self.password.text(), False)
        if self.vpn_first(p, self.probe):
            return None
        try:
            with self.asking(tr('Спрашиваю сервер: ядра, память, программы…')) as quietly:
                opened = server_access.open_server(self, p, connect_app=self.connect_app, search=True, waiting=quietly)
        except SshError as exc:
            self.status.setText(str(exc))
            return None
        if opened is None:
            self.status.setText(tr('Отменено.'))
            return None
        _, resources = opened
        plan = cluster.plan(resources)
        where = (', '.join(resources.orca_modules) or ', '.join(resources.orca_dirs) or resources.orca
                 or tr('не найдена — впишите строки окружения'))
        text = cluster.summary(resources, plan, p.title()) + '\n' + tr('ORCA: ') + where
        if not resources.slurm:
            text += '\n' + tr('SLURM нет: расчёт запускается сразу (nohup), только на свободных ядрах.')
        self._found = {kind: cluster.suggested_setup(resources, kind) for kind in remote.SETUP_KINDS}
        # a program that is only outside PATH (conda, /opt, the home folder) gets its line written into the profile —
        # a sending does not search the folders again; the lines the user wrote are his
        self.keep_setup()
        filled = []
        for kind in remote.SETUP_KINDS:
            line = cluster.path_line(resources, kind)
            if line and line == self._found[kind] and not self._setups.get(kind):
                self._setups[kind] = line
                filled.append(SETUP_TITLES[kind])
        if filled:
            self.setup.blockSignals(True)
            self.setup.setPlainText(self._setups.get(self._setup_shown, ''))
            self.setup.blockSignals(False)
            text += '\n' + tr('Строки окружения вписаны: ') + ', '.join(filled) + tr(' — «Сохранить» запомнит их.')
        outside = [f'{kind} — {path}' for kind, path in cluster.found_programs(resources)]
        if outside:
            text += '\n' + tr('Вне PATH: ') + '; '.join(outside)
        self.status.setText(text)
        self.mark_setups()
        self.update_preview()
        return resources

    def key_login(self):
        """«Вход без пароля» (server_access.set_up_key); the message or None."""
        from modules.sextant import server_access
        from modules.sextant.ssh import SshError

        p = self.profile()
        problems = p.validate()
        if problems:
            self.problems.setText('\n'.join(problems))
            self.problems.show()
            return None
        self.problems.hide()
        if self.password.text():
            keychain.put(keychain.service_for(p), p.user, self.password.text(), False)
        if self.vpn_first(p, self.key_login):
            return None
        if os.name == 'nt':
            self.status.setText(tr('Откроется окно ssh — введите в нём пароль от сервера (один раз).'))
        try:
            with self.asking(tr('Вхожу на сервер…')) as quietly:
                message = server_access.set_up_key(self, p, connect_app=self.connect_app, waiting=quietly)
        except (SshError, InterruptedError) as exc:
            message = str(exc) or tr('Отменено.')
        self.status.setText(message)
        return message

    # -- VPN --------------------------------------------------------------------------------------------------
    def load_vpn_profiles(self):
        if self.connect_app is None:
            return []
        try:
            profiles = vpn.list_profiles(self.connect_app)
        except ValueError as exc:
            self.status.setText(str(exc))
            return []
        chosen = self.vpn.currentData() or ''
        self.vpn.clear()
        self.vpn.addItem(tr('Без VPN'), '')
        for item in profiles:
            self.vpn.addItem(item.name + (f' · {item.host}' if item.host else ''), item.id)
        index = self.vpn.findData(chosen) if chosen else -1  # «Без VPN» has the data '' too: not a choice made
        if index < 0 and len(profiles) == 1:
            index = 1  # the only profile — the laboratory one
        self.vpn.setCurrentIndex(max(0, index))
        self.status.setText(tr(f'Профилей в OpenVPN GUI: {len(profiles)}.') if vpn.is_gui(self.connect_app)
                            else tr(f'Профилей в OpenVPN Connect: {len(profiles)}.'))
        return profiles

    def choose_ovpn(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Файл профиля OpenVPN'), str(Path.home()), tr('OpenVPN (*.ovpn)'))
        return self.import_vpn(path) if path else False

    def import_vpn(self, path):
        try:
            vpn.import_profile(self.connect_app, path, Path(path).stem)
        except ValueError as exc:
            self.status.setText(str(exc))
            return False
        before = {self.vpn.itemData(i) for i in range(self.vpn.count())}
        profiles = self.load_vpn_profiles()
        new = [p for p in profiles if p.id not in before and p.name == Path(path).stem]
        if new:
            self.vpn.setCurrentIndex(self.vpn.findData(new[0].id))
        return True

    # -- check ------------------------------------------------------------------------------------------------
    def check(self):
        p = self.profile()
        if not p.host:
            self.status.setText(tr('Укажите адрес сервера.'))
            return False
        self.timer.stop()
        if vpn.reachable(p.host, p.port, 1.5):
            self.status.setText(tr('Сервер отвечает ✓'))
            return True
        if not p.vpn_id or self.connect_app is None:
            self.status.setText(tr('Сервер не отвечает — подключён ли VPN?'))
            return False
        return self._start_vpn(p)

    def asking(self, text):
        """While the server is asked: the text in the line of the answer, the buttons of the login off, the window alive
        (tasks.run_quietly — the waiting that held every click back looked like a hang). Gives the waiting."""
        from contextlib import contextmanager

        from azimuth.tasks import run_quietly

        @contextmanager
        def held():
            buttons = (self.check_button, self.key_button, self.probe_button, self.save_button)
            self.status.setText(text)
            for item in buttons:
                item.setEnabled(False)
            try:
                yield run_quietly
            finally:
                for item in buttons:
                    try:
                        item.setEnabled(True)
                    except RuntimeError:  # the window was closed meanwhile
                        pass

        return held()

    def vpn_first(self, p, then):
        """The server of p does not answer and the profile has a VPN: OpenVPN Connect is asked to connect, the answer
        is waited for by the timer — the window stays alive — and then() is called (True: wait). Left to
        open_server, the wait held every click back for up to a minute (the owner, 2026-11-22: «окно зависает и нельзя
        никуда нажать»)."""
        if self.connect_app is None or not p.vpn_id or not p.host or vpn.reachable(p.host, p.port, 1.5):
            return False
        self.timer.stop()
        self._start_vpn(p)
        self._after_vpn = then if self.timer.isActive() else None
        return self.timer.isActive()

    def _start_vpn(self, p):
        """OpenVPN Connect asked to connect the profile of p; the answer of the server is waited for (the timer)."""
        self._after_vpn = None
        try:
            vpn.connect(self.connect_app, p.vpn_id)
        except ValueError as exc:
            self.status.setText(str(exc))
            return False
        if vpn.is_gui(self.connect_app):
            self.status.setText(tr('Подключаю VPN в OpenVPN GUI… Если он спросит пароль, его окно появится само.'))
        else:
            self.status.setText(tr('Подключаю VPN в OpenVPN Connect… Его окно скрыто; если он не подключится за {} с, '
                                   'оно откроется — возможно, он спросит пароль.').format(int(vpn.REVEAL_AFTER_S)))
        self.waiting_since = time.monotonic()
        self._vpn_revealed = False
        self.timer.start()
        self.come_forward()
        return False

    def come_forward(self):
        """This window in front again a moment after OpenVPN Connect was started (it opens its own over it; on macOS
        it is hidden by vpn.connect as well — here for Windows and Linux too)."""
        for delay in (700, 1800, 3300):
            QTimer.singleShot(delay, self._forward)

    def _forward(self):
        if self.isVisible():
            self.raise_()
            self.activateWindow()

    def update_vpn_buttons(self, *args):
        ready = self.connect_app is not None
        self.vpn_on.setEnabled(ready and bool(self.vpn.currentData()))
        self.vpn_off.setEnabled(ready)

    def connect_vpn(self):
        """«Подключить VPN»: the profile chosen in the list, now; False when there is none to connect."""
        p = self.profile()
        if self.connect_app is None or not p.vpn_id:
            self.status.setText(tr('Выберите профиль VPN в списке.'))
            return False
        self.timer.stop()
        if not p.host:  # nothing to wait for: only the command
            try:
                vpn.connect(self.connect_app, p.vpn_id)
            except ValueError as exc:
                self.status.setText(str(exc))
                return False
            self.status.setText((tr('OpenVPN GUI подключает профиль «{}».') if vpn.is_gui(self.connect_app)
                                 else tr('OpenVPN Connect подключает профиль «{}».')).format(p.vpn_name))
            self.come_forward()
            return True
        self._start_vpn(p)
        return True

    def disconnect_vpn(self):
        """«Отключить VPN»: OpenVPN Connect is asked to disconnect."""
        if self.connect_app is None:
            return False
        self.timer.stop()
        try:
            vpn.disconnect(self.connect_app)
        except ValueError as exc:
            self.status.setText(str(exc))
            return False
        self.status.setText(tr('OpenVPN GUI отключает VPN.') if vpn.is_gui(self.connect_app)
                            else tr('OpenVPN Connect отключает VPN.'))
        self.come_forward()
        return True

    def _answers(self, p):
        """Whether the server answered the last question; the next one is asked in a thread of its own — asked here,
        a server behind a VPN that is not up yet stopped the window for a second of every two."""
        import threading

        state = self.__dict__.setdefault('_reach', {'busy': False, 'ok': False, 'who': None})
        who = (p.host, p.port, self.waiting_since)
        if state['who'] != who:
            state.update(busy=False, ok=False, who=who)
        if state['ok']:
            return True
        if not state['busy']:
            state['busy'] = True

            def ask():
                try:
                    ok = bool(vpn.reachable(p.host, p.port, 1.0))
                except Exception:  # noqa: BLE001 — no answer
                    ok = False
                if state['who'] == who:
                    state.update(ok=ok, busy=False)

            threading.Thread(target=ask, name='azimuth-vpn-wait', daemon=True).start()
        return False

    def _wait_step(self):
        p = self.profile()
        if self._answers(p):
            self.timer.stop()
            self.status.setText(tr('VPN подключён, сервер отвечает ✓'))
            then, self._after_vpn = getattr(self, '_after_vpn', None), None
            if then is not None:  # what was asked before the VPN («Узнать ресурсы», «Вход без пароля»)
                QTimer.singleShot(0, then)
            return True
        waited = time.monotonic() - self.waiting_since
        if waited > vpn.REVEAL_AFTER_S and not getattr(self, '_vpn_revealed', True):
            self._vpn_revealed = True  # it may be asking for a password: its window is shown
            if vpn.reveal(self.connect_app):
                self.status.setText(tr('OpenVPN Connect ещё не подключился — его окно открыто: если он спрашивает '
                                       'пароль, введите его там.'))
        if waited > WAIT_S:
            self.timer.stop()
            self.status.setText(tr('Сервер так и не ответил за минуту — проверьте VPN и адрес.'))
        return False

    def accept(self):
        if not self.save():
            return
        self.timer.stop()
        super().accept()

    def reject(self):
        self.timer.stop()
        super().reject()

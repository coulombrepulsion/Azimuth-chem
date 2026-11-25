"""Qt's own texts in the language of the program.

Standard buttons of message boxes and dialogs (Yes, No, Save, Don't Save, Cancel, OK...), the context
menus of text fields, the colour and input dialogs and the macOS application menu are Qt's texts, not
ours: without a translator they stay English, so a question in Russian offered English answers.
install(language) loads qtbase_<language>.qm from the PySide6 wheel and, under it, BUTTONS below, so
the standard buttons are translated even when the .qm file is missing or lacks one of them. Called by HubWindow at start
and by Studio.set_language; installing the same language again does nothing.
"""

from PySide6.QtCore import QCoreApplication, QLibraryInfo, QTranslator

QM = {'ru': 'qtbase_ru', 'zh': 'qtbase_zh_CN'}

# source texts of QPlatformTheme / QCocoaTheme / QMessageBox (Qt 6); '&' marks the mnemonic
BUTTONS = {
    'ru': {
        'OK': 'ОК',
        'Save': 'Сохранить',
        'Save All': 'Сохранить все',
        'Open': 'Открыть',
        '&Yes': '&Да',
        'Yes': 'Да',
        'Yes to &All': 'Да для &всех',
        '&No': '&Нет',
        'No': 'Нет',
        'N&o to All': 'Н&ет для всех',
        'Abort': 'Прервать',
        'Retry': 'Повторить',
        'Ignore': 'Пропустить',
        'Close': 'Закрыть',
        'Cancel': 'Отмена',
        'Discard': 'Не сохранять',
        "Don't Save": 'Не сохранять',
        'Help': 'Справка',
        'Apply': 'Применить',
        'Reset': 'Сбросить',
        'Restore Defaults': 'По умолчанию',
        'Show Details...': 'Подробнее…',
        'Hide Details...': 'Скрыть подробности…',
    },
    'zh': {
        'OK': '确定',
        'Save': '保存',
        'Save All': '全部保存',
        'Open': '打开',
        '&Yes': '是(&Y)',
        'Yes': '是',
        'Yes to &All': '全部是(&A)',
        '&No': '否(&N)',
        'No': '否',
        'N&o to All': '全部否(&O)',
        'Abort': '中止',
        'Retry': '重试',
        'Ignore': '忽略',
        'Close': '关闭',
        'Cancel': '取消',
        'Discard': '不保存',
        "Don't Save": '不保存',
        'Help': '帮助',
        'Apply': '应用',
        'Reset': '重置',
        'Restore Defaults': '恢复默认',
        'Show Details...': '显示详细信息…',
        'Hide Details...': '隐藏详细信息…',
    },
}

_installed = []
_current = None


class ButtonTranslator(QTranslator):
    """The standard button texts of BUTTONS[language] whatever the context. It is installed first, so Qt asks
    it last (after qtbase_<language>.qm): an unknown text comes back unchanged, which is what Qt shows anyway
    when no translator knows it (an empty answer could be taken for a translation)."""

    def __init__(self, table, parent=None):
        super().__init__(parent)
        self.table = table

    def translate(self, context, source, disambiguation=None, n=-1):
        return self.table.get(source, source)

    def isEmpty(self):
        return not self.table


def current():
    return _current


def install(language):
    """Qt's texts in language (ru, en, zh); True when the translators changed."""
    global _current
    app = QCoreApplication.instance()
    if app is None or language == _current:
        return False
    for translator in _installed:
        app.removeTranslator(translator)
        translator.deleteLater()
    _installed.clear()
    _current = language
    numbers(language)
    if language in BUTTONS:
        own = ButtonTranslator(BUTTONS[language], app)
        app.installTranslator(own)  # installed first: asked last, after Qt's own translation
        _installed.append(own)
    name = QM.get(language)
    if name:
        qm = QTranslator(app)
        if qm.load(name, QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)):
            app.installTranslator(qm)
            _installed.append(qm)
        else:
            qm.deleteLater()
    return True


def numbers(language):
    """2026-11-17 (the screenshots of the site in English and Chinese: «298,15 K», «1,000 atm» — read as a thousand):
    the numbers of the fields (spin boxes) in the way of the language of the program — 298,15 in Russian, 298.15 in
    English and Chinese — not of the system of the computer; no separator of thousands. The default locale for the
    fields made later, and the fields already there are told; returns the locale."""
    from PySide6.QtCore import QLocale

    language_of = {'ru': (QLocale.Language.Russian, QLocale.Country.Russia),
                   'en': (QLocale.Language.English, QLocale.Country.UnitedStates),
                   'zh': (QLocale.Language.Chinese, QLocale.Country.China)}
    locale = QLocale(*language_of.get(language, language_of['ru']))
    locale.setNumberOptions(QLocale.NumberOption.OmitGroupSeparator)
    QLocale.setDefault(locale)
    try:
        from PySide6.QtWidgets import QAbstractSpinBox, QApplication

        if isinstance(QCoreApplication.instance(), QApplication):
            for widget in QApplication.allWidgets():
                if isinstance(widget, QAbstractSpinBox):
                    widget.setLocale(locale)
    except RuntimeError:  # a widget being deleted
        pass
    return locale

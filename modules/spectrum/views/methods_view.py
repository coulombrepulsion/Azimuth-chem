"""«Методика расчёта…»: the paragraph of the computational details of a calculation and the archive of its inputs.

§1 PURPOSE
    The window over modules/spectrum/analysis/methods_text.py: the paragraph for the report — read from the files of
    the calculation, free to be reworded here before it is copied — and a button that packs the input files of the
    calculation folder into a zip with that paragraph (the appendix of the report).
§4 SPECIFICATION
    MethodsDialog(owner, folder=None, details=None) — set_folder(folder, details=None) -> Details | None (the reason
    in the note), text (QPlainTextEdit), files (the label of what the archive will hold), copy() -> text,
    save_archive(path=None) -> path | None, choose_folder().
§7 TESTS
    tests/gui/test_gui_spectrum.py::test_methods_dialog.
"""

from pathlib import Path

from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout

from azimuth.i18n import tr
from azimuth.ui import button, label
from modules.spectrum.analysis import methods_text


class MethodsDialog(QDialog):
    def __init__(self, owner, folder=None, details=None):
        super().__init__(owner)
        self.setWindowTitle(tr('Методика расчёта'))
        self.folder, self.details = None, None
        lay = QVBoxLayout(self)
        hint = label(tr('Абзац для раздела «Методика расчёта» отчёта — собран из файлов расчёта. В нём только то, что '
                        'записано в файлах: проверьте его и допишите своё (зачем выбран метод, как проверена сходимость). '
                        'Текст можно править прямо здесь.'), 'subtitle')
        hint.setWordWrap(True)
        lay.addWidget(hint)
        self.text = QPlainTextEdit()
        lay.addWidget(self.text, 1)
        self.files = label('', 'subtitle')
        self.files.setWordWrap(True)
        lay.addWidget(self.files)
        bottom = QHBoxLayout()
        bottom.addWidget(button(tr('Выбрать папку расчёта…'), lambda: self.choose_folder()))
        self.copy_button = button(tr('Копировать текст'), lambda: self.copy())
        bottom.addWidget(self.copy_button)
        self.archive_button = button(tr('Сохранить архив входных файлов…'), lambda: self.save_archive())
        bottom.addWidget(self.archive_button)
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))
        lay.addLayout(bottom)
        self.resize(760, 420)
        self.set_folder(folder, details)

    def set_folder(self, folder, details=None):
        self.folder = Path(folder) if folder else None
        self.details = None
        reason = ''
        if self.folder is None:
            reason = tr('Откройте результат расчёта или выберите папку расчёта.')
        else:
            try:
                self.details = details or methods_text.of_folder(self.folder)
            except ValueError as exc:
                reason = str(exc)
            if self.details is None and not reason:
                reason = tr('В папке {} не нашлось расчёта ORCA или Quantum ESPRESSO.').format(self.folder.name)
        self.text.setPlainText(methods_text.paragraph(self.details) if self.details is not None else '')
        names = [p.name for p in methods_text.inputs_of(self.folder)] if self.folder is not None and self.folder.is_dir() else []
        shown = ', '.join(names[:12]) + (' …' if len(names) > 12 else '')
        self.files.setText(reason or tr('В архив войдут входные файлы папки {} ({}): {}').format(self.folder.name, len(names), shown))
        self.copy_button.setEnabled(self.details is not None)
        self.archive_button.setEnabled(bool(names))
        return self.details

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, tr('Папка расчёта'), str(self.folder or Path.home()))
        if folder:
            self.set_folder(folder)
        return folder

    def copy(self):
        text = self.text.toPlainText()
        QApplication.clipboard().setText(text)
        return text

    def save_archive(self, path=None):
        if self.folder is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr('Архив входных файлов'), str(self.folder.parent / (self.folder.name + '_inputs.zip')),
                                                  'ZIP (*.zip)')
            if not path:
                return None
        try:
            methods_text.archive(self.folder, path, self.text.toPlainText())
        except (ValueError, OSError) as exc:
            self.files.setText(str(exc))
            return None
        self.files.setText(tr('Архив сохранён: {}').format(path))
        return path

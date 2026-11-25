"""HistoryTool: «Расчёт → История расчётов…» — the row of a calculation remembered at its start, the window of the
history, «Открыть результат», «Папка», «Убрать из списка», «Очистить список». RunTool keeps the same methods, which hand
the call over here; «Проверить на сервере» (resume_history) stays in RunTool — it starts the watching of a calculation.
"""

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices

from azimuth.i18n import tr
from modules.sextant.inputs import NAMES
from modules.sextant.job_window import subscript


class HistoryTool:
    PORT = (
        'coordinate_tool',
        'notify',
        'opening_tool',
        'preferences',
        'running_jobs',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)

    def remember_job(self, job, calc, kind, place=None):
        from azimuth.runtime import lifecycle

        try:
            title = f'{subscript(self.w.coordinate_tool.table_molecule().formula)} · {NAMES[kind]}'
        except Exception:  # noqa: BLE001 — the history is a help, never a failure of the calculation
            return
        attempt = getattr(job, '_attempt', None) or lifecycle.Attempt(job.spec.folder, job.spec.output, kind, place or '')
        lifecycle.Lifecycle(self.w.preferences).remember(attempt, job, calc, title)

    def show_history(self):
        from modules.sextant.history_dialog import HistoryDialog

        dialog = HistoryDialog(self.w.widget)
        self._history_dialog = dialog
        dialog.show()
        return dialog

    def open_history_result(self, rec):
        output = Path(rec.get('output', ''))
        if not output.is_file() or output.stat().st_size == 0:
            self.w.notify(tr('Вывода расчёта нет: ') + str(output), 8000)
            return False
        self.w.opening_tool.open_path(str(output))
        return True

    def open_history_folder(self, rec):
        folder = Path(rec.get('folder', ''))
        if folder.is_dir():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            return True
        return False

    def forget_history(self, rec):
        from modules.sextant import history

        history.save(self.w.preferences, [d for d in history.load(self.w.preferences) if d.get('folder') != rec.get('folder')])
        return True

    def clear_history(self):
        """«Очистить список» of «История расчётов» — the list only (the folders of the calculations stay);
        a calculation going on now stays in it. Returns the number of entries taken away."""
        from modules.sextant import history

        items = history.load(self.w.preferences)
        going = {str(j.spec.folder) for j in (self.w.running_jobs() if self.w.has('running_jobs') else [])}
        kept = [d for d in items if d.get('folder') in going]
        history.save(self.w.preferences, kept)
        return len(items) - len(kept)

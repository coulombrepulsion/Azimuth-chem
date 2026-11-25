"""«Расчёт → Быстрый расчёт xtb» of «Компас · Кристалл».
§1 PURPOSE
    As the quick xtb of a molecule (calculation_tools.quick_xtb): the crystal of the tab computed at once, without the
    page of Sextant — GFN1-xTB of CP2K (periodic, Γ; the program xtb itself has no GFN2 with a cell), the energy, the
    optimization of the atoms or of the atoms and the cell. Its settings are those of GFN1-xTB from the start, not
    those of the page of Sextant (they stay as they are); the run is a run of the project like any other (Результаты
    расчётов), its progress on the pill over the model, Esc stops it; at the end a line of how it went and, after an
    optimization, the steps in the tab (QePanel.open_relaxed).
§2 ALGORITHM A hidden QePanel of the crystal (compact: its controls inside it): program 'cp2k', functional 'GFN1-XTB',
    the task, this computer; its start() (the Γ supercell of a small cell, the folder, the job); its listeners give
    'progress' and 'end'.
§4 SPECIFICATION
    TASKS — (key of cp2k_inputs.TASKS, title of the menu, tooltip); run(studio, task) -> QePanel | None;
    running(studio) -> bool.
§7 TESTS
    tests/gui/test_gui_files.py::test_the_quick_xtb_of_a_crystal."""

from azimuth.i18n import tr

TASKS = (
    ('Энергия', 'Энергия (GFN1-xTB)', 'Энергия ячейки полуэмпирикой GFN1-xTB в CP2K — сразу, без Секстанта'),
    ('Оптимизация атомов', 'Оптимизация атомов (GFN1-xTB)', 'Атомы сдвигаются, ячейка из файла остаётся'),
    ('Оптимизация с ячейкой', 'Оптимизация с ячейкой (GFN1-xTB)',
     'Атомы и ячейка вместе: быстрая предварительная оптимизация большой ячейки перед DFT'),
)


def running(studio):
    panel = getattr(studio, '_quick_crystal', None)
    try:
        return panel is not None and panel.job is not None and panel.job.running
    except RuntimeError:
        return False


def run(studio, task):
    """The quick GFN1-xTB of the crystal of the tab: task a key of cp2k_inputs.TASKS. → its QePanel, or None (said)."""
    from modules.compass.actions.qe_window import QePanel

    built = getattr(studio, 'crystal', None)
    if not built:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    if running(studio):
        studio.notify(tr('Быстрый расчёт кристалла уже идёт: дождитесь его конца или нажмите Esc.'), 6000)
        return None
    data = built[0]
    tool = getattr(studio, 'crystal_tool', None)
    name = getattr(tool, 'crystal_name', '') or data.title or 'CIF'
    old = getattr(studio, '_quick_crystal', None)
    if old is not None:
        try:
            old.deleteLater()
        except RuntimeError:
            pass
    panel = QePanel(studio, data, name, studio)  # compact: its controls laid out inside it (hidden), none a window
    panel.hide()
    studio._quick_crystal = panel
    panel.set_program('cp2k')
    panel.cp2k_functional.setCurrentIndex(max(0, panel.cp2k_functional.findData('GFN1-XTB')))
    panel.task.setCurrentIndex(max(0, panel.task.findData(task)))
    panel.where.setCurrentIndex(max(0, panel.where.findData('local')))
    panel.title_text = f'{name}-xtb'
    job = panel.start()
    if job is None:
        studio.notify(tr('Быстрый расчёт не запущен: ') + (panel.status.text() or tr('входной файл не собран')), 10000)
        return None
    follow(studio, panel, tr(task))
    return panel


def here(studio):
    """The user is in «Компас · Кристалл» now: its page in the Studio, the Studio shown in the hub."""
    viewer = getattr(studio, 'viewer', None)
    stack = getattr(studio, 'stack', None)
    try:
        return (viewer is not None and viewer.isVisibleTo(viewer.window())
                and (stack is None or stack.currentIndex() == 0) and getattr(studio, 'compass_mode', '') == 'crystal')
    except RuntimeError:
        return False


def follow(studio, panel, what):
    """The run on the pill over the model (as the quick xtb of a molecule): what, the time, «Esc — остановить»; at the
    end a line of how it went, after an optimization its steps in the tab."""
    import time

    from PySide6.QtCore import QEvent, QObject, Qt
    from PySide6.QtWidgets import QApplication

    from azimuth import tasks

    started = time.monotonic()
    hint = tr('Esc — остановить')
    app = QApplication.instance()

    class Esc(QObject):
        def eventFilter(self, obj, event):
            try:
                if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape \
                        and QApplication.activePopupWidget() is None and QApplication.activeModalWidget() is None \
                        and running(studio) and here(studio):
                    panel.stop()
                    return True
            except RuntimeError:
                app.removeEventFilter(self)
            return False

    esc = Esc(studio)
    app.installEventFilter(esc)
    # as the quick xtb of a molecule — in another section the pill goes and
    # the sign of «Компас · Кристалл» turns in the left panel (studio.activities), a click on it comes back; ended
    # away — the sign stays with its end until it is opened
    board = getattr(studio, 'activities', None)
    key = 'quick-crystal'
    if board is not None:
        board.start(key, tr('GFN1-xTB · {}').format(what), None, parked=not here(studio))
        item = board.get(key)
        if item is not None:
            item.section = 'crystal'

    def told(event, _panel):
        at_home = here(studio)
        if event in ('start', 'progress'):
            if board is not None and board.get(key) is not None:
                board.park(key, not at_home)
            spent = int(time.monotonic() - started)
            if at_home:
                tasks.pill_busy(studio, f'GFN1-xTB · {what} · {spent // 60}:{spent % 60:02d} · {hint}')
            else:
                tasks.pill_busy(studio, '', on=False)
            return
        app.removeEventFilter(esc)
        tasks.pill_busy(studio, '', on=False)
        result = panel.result
        ok = result is not None and result.done and not result.error and result.energy is not None
        if board is not None and board.get(key) is not None:
            if at_home:
                board.remove(key)
            else:
                board.park(key, True)
                board.finish(key, 'done' if ok else ('stopped' if panel.job is not None and panel.job.stopped else 'failed'))
        if not ok:
            studio.notify(tr('Быстрый расчёт кристалла не закончен: ') + panel.status.text(), 12000)
            return
        line = tr('Быстрый расчёт кристалла закончен: E = {} Eh').format(f'{result.energy_hartree:.6f}')
        if result.steps:
            line += tr(', шагов оптимизации: {}{}').format(result.steps, '' if result.converged else tr(' (не сошлась)'))
            # the steps go to the tab only while the user is in «Компас · Кристалл» — another section
            # chosen meanwhile is not left (they are in «Результаты расчётов»)
            if at_home and panel.open_relaxed():
                line += tr(' — шаги во вкладке')
            elif not at_home:
                line += tr(' — шаги в «Расчёт → Результаты расчётов»')
        studio.notify(line, 12000)

    panel.listeners.append(told)
    told('start', panel)

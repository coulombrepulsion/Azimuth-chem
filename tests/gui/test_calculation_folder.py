"""The folder button of the
panel of steps opens the folder of the calculation shown — of the result of the tab, or of the run of a crystal — and
is off for steps made in the program."""

import shutil
import sys

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers

ROOT = Path(__file__).resolve().parents[2]


def test_the_button_opens_the_folder_of_the_calculation(window, app, tmp_path, monkeypatch):
    import subprocess

    from PySide6.QtGui import QDesktopServices

    opened = []
    monkeypatch.setattr(subprocess, 'Popen', lambda args, *a, **k: opened.append(list(args)))
    monkeypatch.setattr(QDesktopServices, 'openUrl', staticmethod(lambda url: opened.append(url.toLocalFile()) or True))
    drawer, tool = window.drawer, window.trajectory_tool
    assert drawer.open_button.toolTip() == 'Открыть папку расчёта' and 'ORCA' not in drawer.open_button.toolTip()
    # a result read from its file: the folder of that file
    output = tmp_path / 'run-1' / 'optimization-demo.out'
    output.parent.mkdir()
    shutil.copy(ROOT / 'examples' / 'optimization-demo.out', output)
    window.display_output(output.read_text(encoding='utf-8'), output.name, False, path=str(output))
    app.processEvents()
    assert drawer.steps and tool.calculation_folder() == output.parent
    assert drawer.open_button.isEnabled()
    drawer.open_button.click()
    assert opened and (opened[-1] == ['open', '-R', str(output)] if sys.platform == 'darwin'
                       else str(output.parent) in ' '.join(map(str, opened[-1])))  # [explorer, /select, path] on Windows
    # steps made in the program (a path between structures): no folder — the button is off, a press says why
    from types import SimpleNamespace

    window.new_document()
    tool.load_trajectory(SimpleNamespace(steps=tuple(drawer.steps), scan=None, initial_geometry=None), 'путь')
    assert tool.calculation_folder() is None and not drawer.open_button.isEnabled()
    before = len(opened)
    assert tool.open_calculation_folder() is None and len(opened) == before
    # the steps of a crystal optimized by its run: the folder of the run
    run = tmp_path / 'cp2k-run'
    run.mkdir()
    tool.load_crystal_steps(tuple(drawer.steps), 'оптимизация CP2K', run)
    assert tool.calculation_folder() == run and drawer.open_button.isEnabled()
    tool.open_calculation_folder()
    assert Path(opened[-1]) == run  # «C:/…» from Qt on Windows
    drawer.load((), '')  # another load forgets that folder
    assert drawer.folder is None

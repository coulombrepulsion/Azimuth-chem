"""The number of steps goes to the line that says the geometry converged."""

from types import SimpleNamespace

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def test_round_ticks_and_steps_that_fit():
    from modules.spectrum.views.convergence_view import nice_ticks, step_ticks

    assert nice_ticks(-6.2, -0.4) == [-6, -4, -2]
    assert nice_ticks(-6.2, -0.4, 6) == [-6, -5, -4, -3, -2, -1]
    assert nice_ticks(0, 1, 4) == [0, 0.25, 0.5, 0.75, 1]
    assert step_ticks(14, 20) == list(range(1, 15))
    assert step_ticks(120, 15) == [1] + list(range(10, 121, 10))


def test_the_steps_of_an_optimization_follow_its_status():
    from modules.spectrum.workspace import SpectrumWorkspace as W

    steps = lambda n: SimpleNamespace(steps=[0] * n)  # noqa: E731
    assert W.steps_text(steps(1)) == ''
    assert W.steps_text(steps(21)) == ' за 21 шаг'
    assert W.steps_text(steps(3)) == ' за 3 шага'
    assert W.steps_text(steps(12)) == ' за 12 шагов'


def test_both_build_buttons_are_primary_and_the_atoms_are_centred(window):
    from PySide6.QtCore import Qt
    from modules.spectrum.views.field_view import AtomBox

    panel = window.field_panel
    assert panel.map_button.objectName() == panel.line_button.objectName() == 'primary'
    boxes = panel.findChildren(AtomBox)
    assert boxes and all(box.alignment() & Qt.AlignmentFlag.AlignHCenter for box in boxes)


def test_the_tabs_start_past_the_rounded_corner(window):
    margins = window.result_top_row.layout().contentsMargins()
    assert margins.left() == 12  # as the row of Compass (documents.build_view_row)


def test_the_status_is_a_pill_that_goes(window, app):
    data = Path(__file__).parents[1] / 'data'
    assert window.status_pill.isHidden()
    window.open_output_path(str(data / 'psi4' / 'water_ccsdt_psi4-1.7.out'), show=False)
    assert not window.status_pill.isHidden() and window.status_timer.isActive()
    assert window.output_source.parentWidget() is window.status_pill
    window.status_timer.timeout.emit()
    assert window.status_pill.isHidden()
    assert 'CCSD(T)' in window.result_summary.text()  # the text stays for the tests and a later flash
    window.clear_result()
    window.flash_status()
    assert window.status_pill.isHidden()  # no result — nothing to flash


def test_the_status_lies_over_the_foot_of_the_panel(window, app):
    data = Path(__file__).parents[1] / 'data'
    panel = window.result_panel
    layout = panel.layout()
    assert layout.indexOf(window.assessment) < 0 and layout.indexOf(window.status_pill) < 0  # no rows of their own
    window.open_output_path(str(data / 'psi4' / 'water_ccsdt_psi4-1.7.out'), show=False)
    assert window.status_pill.parentWidget() is panel and window.assessment.parentWidget() is window.status_pill
    panel.resize(900, 600)
    window.place_status()
    pill = window.status_pill.geometry()
    assert pill.left() >= 16 and pill.bottom() == panel.height() - 17 and pill.width() <= panel.width() - 32
    if not window.calc_pulse.isVisible():
        assert abs(pill.center().x() - panel.width() / 2) <= 1


def test_the_titles_of_the_axes_stand_by_their_values(app):
    from PySide6.QtGui import QImage, QPainter

    from modules.spectrum.views.convergence_view import ConvergencePlot

    plot = ConvergencePlot()
    image = QImage(10, 10, QImage.Format.Format_ARGB32)
    p = QPainter(image)
    near = plot.LEFT - 7 - 14 - 8 - p.fontMetrics().height() / 2
    p.end()
    assert near > 14  # with labels «−4» the title stands right by them, not at the edge of the plot


def test_a_message_in_spectrum_is_a_pill_not_a_status_line(window, app):
    # a message of the status line goes to a pill over the foot of the page; the line stays hidden
    window.navigate(2)
    window.resize(1200, 800)
    window.statusBar().showMessage('Таблицы в папке расчёта: a.csv', 5000)
    assert window.statusBar().isHidden() and not window.statusBar().currentMessage()
    toast = window._page_toast
    assert toast.text() == 'Таблицы в папке расчёта: a.csv' and not toast.isHidden()
    assert toast.parentWidget() is window.stack
    window.notify('Ещё одно', 3000)
    assert toast.text() == 'Ещё одно'
    window._page_toast_timer.timeout.emit()
    assert toast.isHidden()


def test_a_message_joins_the_pill_of_the_status(window, app):
    # while the status is shown a message is its last line; a long wait replaces it
    window.navigate(2)
    window.resize(1200, 800)
    toast = getattr(window, '_page_toast', None)
    if toast is not None:
        toast.hide()
    window.status_pill.show()
    window.notify('Найдено критических точек: 37.', 5000)
    assert window.status_message.text() == 'Найдено критических точек: 37.' and not window.status_message.isHidden()
    assert window.status_message.parentWidget() is window.status_pill
    assert window._page_toast is None or window._page_toast.isHidden()
    assert window.status_timer.remainingTime() >= 4000
    window.status_message_timer.timeout.emit()
    assert window.status_message.isHidden() and not window.status_message.text()
    window.notify('Считаю · 0:01 · Esc — отменить', 3_600_000)
    assert window.status_pill.isHidden() and window._page_toast.text().startswith('Считаю')


def test_the_sign_of_a_calculation_stands_in_the_column_of_the_icons():
    # the icon of 40 px with its padding less
    # by half of what it is wider than the 22 px icons at 12 px
    from hub.job_indicator import PAD, SIZE

    assert PAD + SIZE / 2 == 12 + 22 / 2


def test_the_pill_of_a_page_goes_with_the_page(window, app):
    # the message of Spectrum is not left behind in Sextant
    window.navigate(2)
    window.resize(1200, 800)
    window.status_pill.hide()
    window.notify('В результате есть свойства атомов', 5000)
    assert not window._page_toast.isHidden()
    window.navigate(1)
    assert window._page_toast.isHidden() and not window._page_toast_timer.isActive()


def test_a_dialog_opens_in_the_middle(window, app):
    from PySide6.QtWidgets import QDialog

    from azimuth.ui import DialogCentre

    DialogCentre.install()
    dialog = QDialog()
    dialog.resize(320, 200)
    dialog.move(0, 0)
    try:
        dialog.show()
        app.processEvents()
        room = dialog.screen().availableGeometry()
        assert abs(dialog.frameGeometry().center().x() - room.center().x()) <= 40
        assert dialog.property('azimuthCentred')
    finally:
        dialog.close()


def test_the_map_and_the_profile_zoom_and_move(app):
    import numpy as np
    from PySide6.QtCore import QPointF

    from modules.spectrum.views.field_view import LineView, MapView
    from modules.spectrum.views.plot_zoom import MIN

    line = LineView()
    line.resize(600, 400)
    assert line.pad.isHidden()
    x = np.linspace(0.0, 2.0, 201)
    line.set({'x': x, 'values': np.exp(-((x - 1.0) ** 2) * 8) + 0.01}, 'rho', [(0.0, 'C1'), (2.0, 'C2')], [], False)
    assert not line.pad.isHidden() and not line.zoomed()
    line.step('right')
    assert line.window == [0.0, 1.0, 0.0, 1.0]  # the whole is shown: nowhere to go
    line.step('in')
    assert line.zoomed() and line.window[1] - line.window[0] == pytest.approx(0.8)
    line.step('all')
    line.zoom(5.0, 0.5, 0.0, axes='y')  # the small values: the bottom of the graph stays, it grows upward
    x0, x1, y0, y1 = line.window
    assert y0 == pytest.approx(0.0) and y1 == pytest.approx(0.2) and (x0, x1) == (0.0, 1.0)
    line.step('up')
    assert line.window[2] > 0.0
    for _ in range(40):
        line.step('in')
    assert line.window[1] - line.window[0] >= MIN - 1e-9
    line.picture()
    assert not line.pad.isHidden()  # back after the picture
    line.step('all')
    assert not line.zoomed()
    plane = {'u': np.linspace(-2, 2, 30), 'v': np.linspace(-2, 2, 30), 'values': np.random.default_rng(1).random((30, 30))}
    view = MapView()
    view.resize(500, 500)
    view.set(plane, 'elf', [(0.0, 0.0, 'C1')], [])
    view.zoom(2.0)
    assert view.window == pytest.approx([0.25, 0.75, 0.25, 0.75])
    view.step('left')
    assert view.window[0] < 0.25
    rect = view.plot_rect()
    assert rect.width() > 0 and view._share(QPointF(rect.left(), rect.top())) == (0.0, 0.0)
    view.grab()
    view.set(plane, 'elf', [], [])  # a new map — the whole of it
    assert not view.zoomed()


def test_a_map_keeps_its_proportions_in_the_middle(app):
    import numpy as np

    from modules.spectrum.views.field_view import MapView

    plane = {'u': np.linspace(0.0, 9.3, 40), 'v': np.linspace(0.0, 6.8, 40),
             'values': np.random.default_rng(2).random((40, 40))}
    view = MapView()
    view.resize(900, 900)  # a square field: the map across its width, in the middle of the height
    view.set(plane, 'elf', [], [])
    rect = view.plot_rect()
    assert rect.width() / rect.height() == pytest.approx(9.3 / 6.8, rel=1e-6)
    assert rect.width() == pytest.approx(900 - 2 * view.SIDE) and rect.center().x() == pytest.approx(450, abs=1)
    assert rect.center().y() == pytest.approx(view.TOP + (900 - view.TOP - view.BOTTOM) / 2, abs=1)
    view.resize(1400, 500)  # a wide one: as high as it can be, in the middle of the width
    rect = view.plot_rect()
    assert rect.height() == pytest.approx(500 - view.TOP - view.BOTTOM) and rect.center().x() == pytest.approx(700, abs=1)
    view.zoom(2.0)
    view.grab()


def test_the_profile_gets_the_room_the_map_buttons_leave(app):
    # shown first, the map has the width of its rows of buttons, the profile the rest
    from modules.spectrum.views.field_view import FieldPanel

    panel = FieldPanel()
    panel.resize(2000, 700)
    panel.show()
    app.processEvents()
    first, second = panel.views.sizes()
    assert first == pytest.approx(panel.views.widget(0).minimumSizeHint().width(), abs=5) and second > first
    panel.close()


def test_the_arrows_and_the_scale_stand_by_the_build_buttons(app):
    from modules.spectrum.views.field_view import FieldPanel

    panel = FieldPanel()
    for view, button in ((panel.map_view, panel.map_button), (panel.line_view, panel.line_button)):
        assert view.pad.docked and view.pad.parentWidget() is button.parentWidget()
        assert view.pad.isHidden()  # nothing built yet


def test_the_profile_has_round_marks_on_both_axes(app):
    # about one mark per 50 px of the values, per 80 px along
    import numpy as np

    from modules.spectrum.views.convergence_view import nice_ticks
    from modules.spectrum.views.field_view import LineView

    view = LineView()
    view.resize(600, 420)
    x = np.linspace(0.0, 2.6, 261)
    view.set({'x': x, 'values': np.exp(-((x - 1.3) ** 2) * 6) * 100 + 0.1}, 'rho', [], [], True)
    view.grab()
    assert len(nice_ticks(-1.02, 2.05, (420 - 14 - 44) // 50)) >= 5
    assert len(nice_ticks(0.0, 2.6, (600 - 64 - 18) // 80)) >= 5
    view.zoom(8.0, 0.5, 0.0)
    view.grab()  # the marks of the part shown


def test_a_message_pill_is_as_wide_as_its_text(window, app):
    window.navigate(0)
    window.resize(1400, 900)
    window.notify('На модели ничего не наложено.', 3000)
    short = window.notice.width(), window.notice.height()
    assert short[0] < 400
    window.notify('Длинное сообщение о том, что сделано, где лежат таблицы и что можно сделать дальше. ' * 3, 3000)
    long = window.notice.width(), window.notice.height()
    assert long[0] > short[0] and long[1] > short[1]  # as wide as there is room, wrapped
    # the words wrapped keep their air from the edges
    margins = window.notice.contentsMargins()
    assert margins.left() >= 20 and margins.right() >= 20 and margins.top() >= 10
    assert window.notice.contentsRect().width() <= long[0] - 40
    window.hide_notice()
    window.navigate(2)
    window.notify('Готово', 3000)
    assert window._page_toast.width() < 300


def test_the_properties_of_a_result_are_told_once(window, app, monkeypatch, tmp_path):
    from types import SimpleNamespace

    said = []
    monkeypatch.setattr(window, 'notify', lambda text, ms=0: said.append(text))
    tool = window.property_tool
    kept = dict(window.overlay_choice)
    for key in window.overlay_choice:
        window.overlay_choice[key] = None if key == 'atom' else False
    props = SimpleNamespace()
    result = tmp_path / 'a.out'
    result.write_text('FINAL SINGLE POINT ENERGY -1.0\n', encoding='utf-8')
    try:
        tool.set_result_properties(props, str(result), announce=True)  # opened
        tool.set_result_properties(props, str(result), announce=True)  # its tab shown again
        tool.set_result_properties(SimpleNamespace(), str(result))  # charges computed for it later
        # the molecule chosen again
        # reads the same file anew — not told again
        tool.set_result_properties(SimpleNamespace(), str(result), announce=True)
        assert len(said) == 1 and 'свойства атомов и связей' in said[0] and 'справа от модели' in said[0]
        # 2026-11-19 named where they stand
        monkeypatch.setattr(window.custom_bar, 'where', lambda key, groups=None: 'top' if key.endswith('atoms') else 'rail')
        hint = tool.properties_hint()
        assert 'кнопка «Атомы» над моделью' in hint and 'кнопки «Связи», «Диполь и силы» справа от модели' in hint
        monkeypatch.setattr(window.custom_bar, 'where', lambda key, groups=None: None)
        assert 'кнопк' not in tool.properties_hint() and 'Свойства из расчёта' in tool.properties_hint()
        result.write_text('FINAL SINGLE POINT ENERGY -1.0\nFINAL SINGLE POINT ENERGY -2.0\n', encoding='utf-8')
        tool.set_result_properties(SimpleNamespace(), str(result), announce=True)  # calculated again: another file
        assert len(said) == 2
    finally:
        tool.set_result_properties(None)
        window.overlay_choice.update(kept)


def test_a_tooltip_comes_back_from_chinese_whole(app):
    from PySide6.QtWidgets import QPushButton

    from azimuth import i18n

    tip = 'Снимок · PNG, высокое разрешение, прозрачный фон, GIF вращения или шагов оптимизации'
    button = QPushButton('Снимки')
    button.setToolTip(tip)
    try:
        for code in ('zh', 'en', 'zh', 'ru'):
            i18n.set_language(code)
            i18n.retranslate(button)
        assert button.toolTip() == tip and button.text() == 'Снимки'
        assert i18n.retranslate_text('Настройки задачи · Оптимизация + частоты') == 'Настройки задачи · Оптимизация + частоты'
    finally:
        i18n.set_language('ru')


def test_the_pills_of_the_dark_theme_are_dark(app):
    import azimuth.app as styles

    assert 'QLabel#toast {background: rgba(46, 54, 68, 240)' in styles.DARK_STYLE
    assert 'QTreeWidget#surfacesTree::item:hover' in styles.STYLE

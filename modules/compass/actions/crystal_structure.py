"""«Анализ структуры» of a crystal in Compass: the window of crystal_energetics.

§1 PURPOSE The ionic picture of the crystal shown: the Madelung energy (formal charges or the CM5 / Hirshfeld charges of
    the last CP2K run of the project), the bond valence sums, Shannon radii and Pauling's rules, the density and the
    packing, the cell of the last optimization against the cell of the file. One window, a tab each; the items of the
    menu «Кристалл → Анализ структуры» open it on their tab.
§4 SPECIFICATION
    show(studio, tab) -> StructureWindow | None (tab: TABS); StructureWindow(parent, crystal, project, run).
§7 TESTS tests/gui/test_gui_files.py::test_crystal_structure_window*.
"""

from pathlib import Path

from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
                               QTabWidget, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import crystal_energetics as ce

TABS = ('madelung', 'valence', 'radii', 'packing', 'compare')


def _number(x, digits=3):
    if x is None:
        return '—'
    return f'{x:.{digits}f}'.replace('-', '−')


class Page(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        self.top = QHBoxLayout()
        layout.addLayout(self.top)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table, 1)
        self.note = QLabel()
        self.note.setWordWrap(True)
        layout.addWidget(self.note)

    def fill(self, heads, rows, summary='', lines=()):
        self.table.clear()
        self.table.setColumnCount(len(heads))
        self.table.setRowCount(len(rows))
        self.table.setHorizontalHeaderLabels(heads)
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                self.table.setItem(r, c, QTableWidgetItem(str(value)))
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)
        self.table.resizeRowsToContents()
        self.table.setVisible(bool(heads))
        self.summary.setText(summary)
        self.summary.setVisible(bool(summary))
        self.note.setText('<br>'.join(lines))

    def fail(self, exc):
        self.fill([], [], str(exc))


def _element_charges(symbols, values):
    """{symbol: mean charge} of the atoms of a calculation, the mean shifted so that the formula is neutral."""
    sums, counts = {}, {}
    for s, q in zip(symbols, values):
        sums[s] = sums.get(s, 0.0) + q
        counts[s] = counts.get(s, 0) + 1
    shift = sum(sums.values()) / len(symbols) if symbols else 0.0
    return {s: sums[s] / counts[s] - shift for s in sums}


class StructureWindow(QDialog):
    def __init__(self, parent, crystal, project=None, run=None, title=''):
        super().__init__(parent)
        self.crystal, self.project, self.run = crystal, project, run
        self.setWindowTitle(tr('Анализ структуры · ') + (title or crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)
        self.pages = {}
        for key, name in zip(TABS, (tr('Энергия Маделунга'), tr('Валентности связей'), tr('Радиусы и Полинг'),
                                    tr('Плотность и упаковка'), tr('Расчёт и эксперимент'))):
            self.pages[key] = Page()
            self.tabs.addTab(self.pages[key], name)
        self.charges = QComboBox()
        self.charges.addItem(tr('Формальные степени окисления'), None)
        kept = self._kept_charges()
        if kept is not None:
            self.charges.addItem(tr('Заряды CM5 (расчёт CP2K)'), 'cm5')
            self.charges.addItem(tr('Заряды Хиршфельда (расчёт CP2K)'), 'hirshfeld')
        self._kept = kept
        self.charges.currentIndexChanged.connect(self.fill_madelung)
        page = self.pages['madelung']
        page.top.addWidget(QLabel(tr('Заряды ионов:')))
        page.top.addWidget(self.charges, 1)
        try:
            self.states = ce.oxidation_states(crystal)
            self.problem = None
        except ValueError as exc:
            self.states, self.problem = None, exc
        self.fill_madelung()
        self.fill_valence()
        self.fill_radii()
        self.fill_packing()
        self.fill_compare()
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(820, 520)
        # the tabs of the ionic model are grey when it does
        # not apply (the energy of Madelung stays with the charges of a CP2K run)
        if self.problem is not None:
            for key in ('valence', 'radii') + (() if kept is not None else ('madelung',)):
                index = TABS.index(key)
                self.tabs.setTabEnabled(index, False)
                self.tabs.setTabToolTip(index, str(self.problem))
            if kept is not None:
                self.charges.setCurrentIndex(1)  # the formal states mean nothing here — the charges of the run

    def show_tab(self, key):
        index = TABS.index(key)
        if not self.tabs.isTabEnabled(index):
            index = next(i for i in range(self.tabs.count()) if self.tabs.isTabEnabled(i))
        self.tabs.setCurrentIndex(index)

    def _kept_charges(self):
        if self.run is None:
            return None
        from modules.compass.chemistry import crystal_results

        try:
            return crystal_results.read_charges(self.run.folder)
        except OSError:
            return None

    def _states_text(self):
        return ', '.join(ce.ion_name(s, q) for s, q in sorted(self.states.items(), key=lambda x: -x[1]))

    def fill_madelung(self):
        page = self.pages['madelung']
        key = self.charges.currentData()
        try:
            if key:
                charges = _element_charges(self._kept[0], self._kept[1][key])
                how = self.charges.currentText()
                result = ce.madelung(self.crystal, charges, how)
            else:
                if self.problem:
                    raise self.problem
                result = ce.madelung(self.crystal, self.states)
        except ValueError as exc:
            page.fail(exc)
            return
        summary = tr('{}: E = {} эВ на формульную единицу ({} кДж/моль), {} на ячейку (Z = {}).').format(
            result.formula, _number(result.energy_unit), _number(result.energy_unit * ce.EV_KJ, 0),
            _number(result.energy_cell), result.units)
        if result.constant is not None:
            summary += ' ' + tr('Постоянная Маделунга M = {} (r₀ = {} Å).').format(
                _number(result.constant, 6), _number(result.shortest))
        rows = [(label, symbol, _number(q, 3 if key else 0), _number(phi)) for label, symbol, q, phi in result.sites]
        lines = [tr('Электростатическая энергия точечных зарядов решётки, сумма по Эвальду (E = ½ Σ qᵢφᵢ). Для бинарной '
                    'соли M = −E r₀ / (kₑ |z₊z₋|), kₑ = 14,40 эВ·Å: NaCl 1,7476, CsCl 1,7627, CaF₂ 2,5194 (Киттель, '
                    'гл. 3).'),
                 tr('Потенциал φ — на ионе от всех остальных ионов кристалла: у катиона отрицательный, у аниона '
                    'положительный — ион удерживается решёткой. Энергия решётки опыта меньше по модулю: здесь нет '
                    'отталкивания оболочек (Борн — Майер, ≈ 10 %).')]
        if key:
            lines.append(tr('Заряды расчёта — средние по атомам элемента, сдвинутые так, чтобы ячейка была '
                            'нейтральна; ионы с зарядом меньше формального держатся слабее.'))
        page.fill([tr('Позиция'), tr('Элемент'), tr('Заряд, e'), tr('Потенциал φ, В')], rows, summary, lines)

    def fill_valence(self):
        page = self.pages['valence']
        try:
            if self.problem:
                raise self.problem
            result = ce.bond_valences(self.crystal, self.states)
        except ValueError as exc:
            page.fail(exc)
            return
        rows = []
        for label, ion, expected, total, bonds in result.sites:
            near = {}
            for other, d, s in bonds:
                near.setdefault((other, round(d, 3)), []).append(s)
            text = '; '.join(f'{len(v)} × {other} {_number(d)} Å ({_number(v[0])})' for (other, d), v in near.items())
            rows.append((label, ion, _number(total), str(expected), _number(total - expected, 2), text))
        quality = (tr('ненапряжённая структура') if result.gii < 0.1 else tr('заметные напряжения')
                   if result.gii < 0.2 else tr('сильно напряжена или ошибочна'))
        summary = tr('Степени окисления: {}. Глобальный индекс неустойчивости GII = {} в.е. — {}.').format(
            self._states_text(), _number(result.gii), quality)
        lines = [tr('Валентность связи s = exp((R₀ − R)/b), сумма по противоионам V = Σs должна равняться степени '
                    'окисления (Браун — Альтерматт, 1985). R₀ и b — таблица IUCr bvparm2020 (I. D. Brown). '
                    'V больше нормы — ион сжат (связи короче), меньше — ему просторно.'),
                 tr('GII = √(среднее (V − |q|)²): меньше 0,1 — норма, больше 0,2 — структура напряжена или неверна.')]
        if result.missing:
            lines.append(tr('Нет параметров для пар: {} — их связи не учтены.').format(', '.join(result.missing)))
        page.fill([tr('Позиция'), tr('Ион'), 'V', '|q|', 'V − |q|', tr('Связи (длина, валентность)')], rows, summary,
                  lines)

    def fill_radii(self):
        page = self.pages['radii']
        try:
            if self.problem:
                raise self.problem
            result = ce.radii(self.crystal, self.states)
        except ValueError as exc:
            page.fail(exc)
            return
        rows = []
        for cation, anion, ratio, predicted, observed, total, shortest in result.pairs:
            verdict = tr('да') if predicted == observed else tr('нет')
            rows.append((f'{cation} / {anion}', _number(ratio), str(predicted), str(observed), verdict,
                         _number(total), _number(shortest)))
        ions = '; '.join(f'{ion}: КЧ {cn}, r = {_number(r)} Å' + (tr(' (в таблице КЧ {})').format(table)
                                                                   if table is not None and table != cn else '')
                         for ion, cn, r, table in result.ions)
        rule2 = '; '.join(f'{label}: Σ z₊/КЧ₊ = {_number(total, 2)} ({tr("должно быть")} {expected})'
                          for label, total, expected in result.electrostatic[:6])
        summary = tr('Радиусы Шеннона: {}.').format(ions) + '<br>' + result.tolerance_text
        lines = [tr('Первое правило Полинга: отношение радиусов r₊/r₋ задаёт координационное число катиона — до 0,155: '
                    '2; до 0,225: 3; до 0,414: 4; до 0,732: 6; до 1: 8; больше — 12. Радиусы — эффективные ионные '
                    'радиусы Шеннона (1976) при наблюдаемом КЧ.'),
                 tr('Второе правило (электростатической валентности): сумма z₊/КЧ₊ катионов вокруг аниона равна его '
                    'заряду. ') + rule2,
                 tr('Сумма радиусов r₊ + r₋ сравнивается с кратчайшим расстоянием катион — анион в кристалле.')]
        page.fill([tr('Пара'), 'r₊/r₋', tr('КЧ по Полингу'), tr('КЧ в кристалле'), tr('Совпадает'), 'r₊ + r₋, Å',
                   tr('Расстояние, Å')], rows, summary, lines)

    def fill_packing(self):
        page = self.pages['packing']
        try:
            result = ce.packing(self.crystal, self.states)
        except ValueError as exc:
            page.fail(exc)
            return
        rows = [(tr('Плотность'), _number(result.density), tr('г/см³')),
                (tr('Объём ячейки'), _number(result.volume, 2), 'Å³'),
                (tr('Объём на формульную единицу'), _number(result.volume_unit, 2), 'Å³'),
                (tr('Доля объёма ионов (радиусы Шеннона)'), _number(result.ionic), ''),
                (tr('Коэффициент упаковки Китайгородского (ван-дер-ваальсовы радиусы)'), _number(result.vdw), '')]
        lines = [tr('Доля объёма ионов — сумма 4/3 πr³ ионов ячейки по радиусам Шеннона, делённая на объём ячейки: '
                    'для сравнения плотнейшая упаковка равных шаров 0,740, объёмно-центрированная 0,680.'),
                 tr('Коэффициент Китайгородского — для молекулярных кристаллов (обычно 0,65–0,77); для ионных и '
                    'ковалентных кристаллов ван-дер-ваальсовы сферы перекрываются, и он теряет смысл.')]
        page.fill([tr('Величина'), tr('Значение'), tr('Единица')], rows, '', lines)

    def fill_compare(self):
        page = self.pages['compare']
        computed, folder = self._optimized()
        if computed is None:
            page.fill([], [], tr('В проекте нет оптимизации ячейки — посчитайте кристалл в Секстанте (CP2K или '
                                 'Quantum ESPRESSO, оптимизация с ячейкой).'))
            return
        try:
            rows = ce.compare(self.crystal, computed)
        except ValueError as exc:
            page.fail(exc)
            return
        shown = [(name, _number(x, 4), _number(y, 4), (_number(d, 2) + (' %' if unit != '°' else '°')), unit)
                 for name, x, y, d, unit in rows]
        summary = tr('Последний шаг оптимизации: {}.').format(Path(folder).name)
        lines = [tr('Файл — структура опыта (рентгеноструктурный анализ, обычно при комнатной температуре); расчёт — '
                    'последний шаг оптимизации проекта. Функционалы GGA (PBE) обычно завышают постоянные решётки на '
                    '1–2 %, LDA занижает; учёт дисперсии (D3) сближает с опытом молекулярные и слоистые кристаллы.')]
        page.fill([tr('Параметр'), tr('Файл (опыт)'), tr('Расчёт'), tr('Разница'), tr('Единица')], shown, summary, lines)

    def _optimized(self):
        if not self.project:
            return None, None
        from azimuth import crystal_projects
        from modules.compass.chemistry import crystal_steps

        try:
            steps, folder = crystal_steps.project_steps(self.project, self.crystal, crystal_projects.title(self.project))
        except (OSError, ValueError, KeyError):
            return None, None
        if not steps:
            return None, None
        last = steps[-1]
        return (last.adopted or last.crystal), folder


def show(studio, tab='madelung'):
    """The window of the crystal shown in Compass on its tab; None (said why) without a crystal."""
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    project = studio.research_path() if hasattr(studio, 'research_path') else None
    from azimuth import crystal_projects

    if project and not crystal_projects.is_crystal(project):
        project = None
    run = studio.property_tool.crystal_run() if hasattr(studio, 'property_tool') else None
    window = StructureWindow(studio if isinstance(studio, QWidget) else None, crystal, project, run)
    window.show_tab(tab)
    studio._structure_window = window
    window.show()
    return window

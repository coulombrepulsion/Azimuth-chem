"""Measuring and moving a structure in Compass: «Сдвинуть и повернуть…», the planes of groups of atoms, vectors
and planes (guides), the internal coordinates, the size, the statistics, the masses, the inertia, the pinned
distances and angles. Methods of StructureTool (self is the tool; the window only through its port self.w), kept here
to make structure_actions.py shorter.

Split off modules/compass/actions/structure_actions.py (0.222.29).
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QVBoxLayout
from azimuth.i18n import tr
from modules.compass.chemistry import structure_tools as st


ANGLE_LIMIT = 60


def pin_distances(self):
    chosen = self._chosen(2, tr('атомы, расстояния между которыми показать'))
    if chosen is None:
        return
    found = st.pairs(chosen)
    if len(found) > ANGLE_LIMIT:
        self.w.notify(tr(f'Слишком много расстояний ({len(found)}) — выделите меньше атомов.'))
        return
    self._pin(found)


def pin_angles(self):
    found = st.bond_angles(self.w.molecule, self.w.viewer.selected or None)
    if not found:
        self.w.notify(tr('Валентных углов нет.'))
        return
    if len(found) > ANGLE_LIMIT:
        self.w.notify(tr(f'Углов {len(found)} — выделите часть молекулы, иначе числа закроют её.'))
        return
    self._pin(found)


def _pin(self, items):
    pinned = list(self.w.viewer.pinned)
    for item in items:
        if item not in pinned and tuple(reversed(item)) not in pinned:
            pinned.append(tuple(item))
    self.w.viewer.pinned = pinned
    self.w.viewer.update()


def clear_pins(self):
    self.w.viewer.pinned = []
    self.w.viewer.update()


# -- data of the structure --------------------------------------------------------------------------------------------
def show_inertia(self):
    if not self.w.molecule.atoms:
        return
    try:
        d = st.inertia(self.w.molecule)
    except ValueError as exc:
        self.w.error(exc)
        return
    kinds = {'atom': tr('атом'), 'linear': tr('линейный ротатор'), 'spherical': tr('сферический волчок'),
             'symmetric': tr('симметричный волчок'), 'asymmetric': tr('асимметричный волчок')}
    fmt = lambda x: '—' if x is None else f'{x:.6g}'
    lines = [tr('Главные моменты инерции, а. е. м.·Å²'), '']
    for name, value, cm, mhz in zip('ABC', d['moments'], d['B_cm'], d['B_mhz']):
        lines.append(f'I_{name} = {value:.4f}    {name} = {fmt(cm)} ' + tr('см⁻¹') + f' = {fmt(mhz)} ' + tr('МГц'))
    lines += ['', tr('Тип: ') + kinds[d['kind']],
              tr('Центр масс, Å: ') + ', '.join(f'{c:.4f}' for c in d['centre']),
              '', tr('Массы — самых распространённых изотопов.')]
    self._report(tr('Моменты инерции'), '\n'.join(lines))


def transform_atoms(self, values=None):
    """«Сдвинуть и повернуть…»: values {'shift', 'angle', 'axis'} (the tests) or a dialog."""
    if not self.w.molecule.atoms or self.w.browsing:
        return False
    chosen = list(self.w.viewer.selected)
    if values is None:
        from PySide6.QtWidgets import QComboBox, QDoubleSpinBox

        box = QDialog(self.w.widget)
        box.setWindowTitle(tr('Сдвинуть и повернуть'))
        form = QFormLayout(box)
        form.addRow(QLabel(tr('Выделенные атомы: ') + str(len(chosen)) if chosen else tr('Все атомы')))
        angle = QDoubleSpinBox()
        angle.setRange(-360, 360)
        angle.setDecimals(2)
        angle.setSuffix(' °')
        axis = QComboBox()
        for key, title in (('x', 'X'), ('y', 'Y'), ('z', 'Z')):
            axis.addItem(tr('Ось ') + title + tr(' через их центр'), key)
        if len(chosen) >= 2:
            axis.addItem(tr('Ось через атомы ') + f'{chosen[0] + 1}–{chosen[1] + 1}', 'atoms')
        form.addRow(tr('Повернуть на'), angle)
        form.addRow(tr('Вокруг'), axis)
        shifts = []
        for name in 'XYZ':
            field = QDoubleSpinBox()
            field.setRange(-1000, 1000)
            field.setDecimals(4)
            field.setSuffix(' Å')
            form.addRow(tr('Сдвиг по ') + name, field)
            shifts.append(field)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.rejected.connect(box.reject)

        def accept():
            box.accept()
            self.transform_atoms({'shift': tuple(f.value() for f in shifts), 'angle': angle.value(),
                                  'axis': axis.currentData()})

        buttons.accepted.connect(accept)
        self._transform_dialog = box
        from azimuth.ui import open_window

        open_window(box)  # a window with its title, not a sheet
        return None
    axis = values.get('axis', 'z')
    through = (chosen[0], chosen[1]) if axis == 'atoms' and len(chosen) >= 2 else None
    return self._change(lambda m: st.transformed(m, chosen, values.get('shift', (0.0, 0.0, 0.0)),
                                                 values.get('angle', 0.0), 'z' if through else axis, through),
                        tr('Атомы сдвинуты и повёрнуты.'), selection=chosen or None)


def planes_text(self, first, second=None):
    """The text of «Плоскости групп атомов…»: each plane (its atoms off it), and the angle and distances between
    two."""
    m = self.w.molecule
    symbols = [a.symbol for a in m.atoms]

    def name(i):
        return f'{symbols[i]}{i + 1}'

    def describe(title, p):
        worst = dict(p['deviations'])[p['largest']]
        return [title + ': ' + st.numbers_text(sorted(i for i, _ in p['deviations']), symbols),
                tr('  среднеквадратичное отклонение атомов: ') + f'{p["rms"]:.3f} Å',
                tr('  дальше всех: ') + f'{name(p["largest"])} ({worst:+.3f} Å)']

    if second:
        r = st.planes(m, first, second)
        lines = describe(tr('Плоскость 1'), r['first']) + [''] + describe(tr('Плоскость 2'), r['second'])
        lines += ['', tr('Угол между плоскостями: ') + f'{r["angle"]:.2f}°',
                  tr('Расстояние между центрами: ') + f'{r["centres"]:.3f} Å',
                  tr('Центр 2 над плоскостью 1: ') + f'{r["b_from_a"]:.3f} Å',
                  tr('Центр 1 над плоскостью 2: ') + f'{r["a_from_b"]:.3f} Å',
                  tr('Сдвиг центров вдоль плоскости 1: ') + f'{r["offset"]:.3f} Å']
        return '\n'.join(lines)
    p = st.plane(m, first)
    lines = describe(tr('Плоскость'), p) + ['', tr('Отклонения от плоскости, Å:')]
    lines += [f'  {name(i)}  {d:+.3f}' for i, d in p['deviations']]
    return '\n'.join(lines)


def show_planes(self, first=None, second=None):
    """«Плоскости групп атомов…»: two fields of atoms (numbers or C1–C6); the first is the selection."""
    if not self.w.molecule.atoms:
        return None
    symbols = [a.symbol for a in self.w.molecule.atoms]
    if first is not None:
        try:
            text = self.planes_text(first, second)
        except ValueError as exc:
            self.w.error(exc)
            return None
        self._report(tr('Плоскости групп атомов'), text)
        return text
    box = QDialog(self.w.widget)
    box.setWindowTitle(tr('Плоскости групп атомов'))
    form = QFormLayout(box)
    hint = QLabel(tr('Номера атомов: «1-6» или «C1–C6, N7». Одна группа — её плоскость и отклонения атомов; две — '
                     'ещё угол между плоскостями и расстояния между центрами.'))
    hint.setWordWrap(True)
    form.addRow(hint)
    one, two = QLineEdit(st.numbers_text(sorted(self.w.viewer.selected), symbols)), QLineEdit()
    form.addRow(tr('Группа 1'), one)
    form.addRow(tr('Группа 2'), two)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    form.addRow(buttons)
    buttons.rejected.connect(box.reject)

    def accept():
        try:
            a = st.parse_numbers(one.text(), len(symbols), symbols)
            b = st.parse_numbers(two.text(), len(symbols), symbols) if two.text().strip() else None
        except ValueError as exc:
            self.w.notify(str(exc))
            return
        box.accept()
        self.show_planes(a, b)

    buttons.accepted.connect(accept)
    self._planes_dialog = box
    from azimuth.ui import open_window

    open_window(box)  # a window with its title, not a sheet
    return None


# -- vectors and planes on the model ----------------------------------------------------------------------
def add_guide(self, kind):
    """A vector (two atoms, from the first selected to the second), a normal or a plane (three atoms or more)."""
    from modules.compass.chemistry import guides

    need = 2 if kind == 'vector' else 3
    what = tr('два атома: начало и конец вектора') if kind == 'vector' else tr('три атома или больше')
    chosen = self._chosen(need, what)
    if chosen is None:
        return None
    guide = ({'kind': 'vector', 'atoms': (chosen[0], chosen[1])} if kind == 'vector'
             else {'kind': kind, 'atoms': tuple(chosen)})
    try:
        guides.direction(guide, self.w.molecule)
    except ValueError as exc:
        self.w.error(exc)
        return None
    self.w.viewer.guides = list(self.w.viewer.guides) + [guide]
    self.w.viewer.update()
    symbols = [a.symbol for a in self.w.molecule.atoms]
    self.w.notify(str(len(self.w.viewer.guides)) + ': ' + guides.describe(guide, symbols), 6000)
    return guide


def guide_style(self, values=None):
    """«Стиль векторов и плоскостей…»: for vectors, normals and planes — shown or not, the colour (or that of the
    theme); the width of the lines, the fill and the edge of a plane, the numbers, the length of a normal, the
    margin of a plane around its atoms. values {key: value} of azimuth.defaults keeps them without the window. The
    colour in a circle, ↺ for the colour of the theme (it was «Как тема»), the picker of Qt."""
    if values is not None:
        return self._keep_styles({k: v for k, v in values.items() if k in self.GUIDE_STYLE})
    inks = self.w.viewer.GUIDE_INKS
    tip = '↺ — цвет по умолчанию (свой у светлой и тёмной темы)'
    return self._styles_window(tr('Стиль векторов и плоскостей'), [
        ('shown', 'Векторы', 'guide_vector_show', 'guide_vector_color', self._theme_ink(*inks['vector']), tip),
        ('shown', 'Нормали', 'guide_normal_show', 'guide_normal_color', self._theme_ink(*inks['normal']), tip),
        ('shown', 'Плоскости', 'guide_plane_show', 'guide_plane_color', self._theme_ink(*inks['plane']), tip),
        ('number', 'Толщина линий', 'guide_width', 0.5, 8.0, 0.2, 1, ' px'),
        ('number', 'Заливка плоскостей', 'guide_plane_opacity', 0, 100, 5, 0, ' %'),
        ('check', '', 'guide_plane_edge', 'рисовать край плоскости'),
        ('number', 'Длина нормали', 'guide_normal_length', 0.3, 10.0, 0.1, 2, ' Å'),
        ('number', 'Поля плоскости вокруг атомов', 'guide_plane_margin', 0.0, 5.0, 0.1, 2, ' Å'),
        ('check', '', 'guide_numbers', 'номера рядом с векторами и плоскостями'),
    ], '_guide_style_box')


def clear_guides(self):
    self.w.viewer.guides = []
    self.w.viewer.update()


def guide_angles_text(self):
    """Every guide with its number, then the angle of every pair."""
    from modules.compass.chemistry import guides

    symbols = [a.symbol for a in self.w.molecule.atoms]
    shown = [(k, g) for k, g in enumerate(self.w.viewer.guides, start=1)
             if guides.geometry(g, self.w.molecule) is not None]
    lines = [f'{k}. ' + guides.describe(g, symbols) for k, g in shown]
    if len(shown) > 1:
        lines.append('')
        for x in range(len(shown)):
            for y in range(x + 1, len(shown)):
                (ka, a), (kb, b) = shown[x], shown[y]
                lines.append(tr('Угол ') + f'{ka}–{kb}: {guides.angle(a, b, self.w.molecule):.2f}°')
    return '\n'.join(lines)


def show_guide_angles(self):
    if not self.w.viewer.guides:
        self.w.notify(tr('На модели нет векторов и плоскостей: «Правка → Векторы и плоскости».'), 6000)
        return None
    text = self.guide_angles_text()
    self._report(tr('Углы между векторами и плоскостями'), text)
    return text


def edit_guides_text(self, text=None):
    """The guides as text, edited and read back (text: without the window, the tests)."""
    from modules.compass.chemistry import guides

    symbols = [a.symbol for a in self.w.molecule.atoms]
    if text is not None:
        try:
            self.w.viewer.guides = guides.parse(text, len(symbols), symbols)
        except ValueError as exc:
            self.w.error(exc)
            return None
        self.w.viewer.update()
        return self.w.viewer.guides
    from PySide6.QtWidgets import QPlainTextEdit

    box = QDialog(self.w.widget)
    box.setWindowTitle(tr('Векторы и плоскости'))
    lay = QVBoxLayout(box)
    hint = QLabel(tr('Строка на объект: «вектор 1 2» (от атома 1 к атому 2), «вектор 0 0 0 1 0 0» (начало и конец, Å), '
                     '«нормаль 1-6», «плоскость C1–C6». После «#» — комментарий.'))
    hint.setWordWrap(True)
    lay.addWidget(hint)
    edit = QPlainTextEdit(guides.text(self.w.viewer.guides))
    edit.setMinimumSize(420, 180)
    lay.addWidget(edit)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    lay.addWidget(buttons)
    buttons.rejected.connect(box.reject)

    def accept():
        if self.edit_guides_text(edit.toPlainText()) is not None:
            box.accept()

    buttons.accepted.connect(accept)
    self._guides_dialog = box
    from azimuth.ui import open_window

    open_window(box)  # a window with its title, not a sheet
    return None


# -- «Инструменты» -------------------------------------------------------------------------------------
def internal_rows(self):
    """[(kind, atoms, value)] of the internal coordinates, the atoms as C1–O2–H3."""
    found = st.internal_coordinates(self.w.molecule)
    symbols = [a.symbol for a in self.w.molecule.atoms]
    name = lambda *ix: '–'.join(f'{symbols[i]}{i + 1}' for i in ix)  # noqa: E731
    rows = [(tr('Связь'), name(i, j), f'{d:.4f}') for i, j, d in found['bonds']]
    rows += [(tr('Угол'), name(i, j, k), f'{a:.2f}') for i, j, k, a in found['angles']]
    rows += [(tr('Двугранный'), name(i, j, k, m), f'{f:.2f}') for i, j, k, m, f in found['dihedrals']]
    return rows


def save_internal_csv(self, path=None):
    from modules.spectrum.wavefunction import field_tables

    if path is None:
        from PySide6.QtWidgets import QFileDialog

        path, _ = QFileDialog.getSaveFileName(self.w.widget, tr('Сохранить таблицу'), 'internal_coordinates.csv', 'CSV (*.csv)')
        if not path:
            return None
    return field_tables.write_csv(path, [tr('Тип'), tr('Атомы'), tr('Значение (Å или °)')], self.internal_rows())


def show_internal_coordinates(self):
    if not self.w.molecule.atoms:
        return None
    rows = self.internal_rows()
    counts = {kind: sum(1 for k, _, _ in rows if k == kind) for kind in (tr('Связь'), tr('Угол'), tr('Двугранный'))}
    head = tr('Связей: ') + str(counts[tr('Связь')]) + tr(', углов: ') + str(counts[tr('Угол')]) + \
        tr(', двугранных: ') + str(counts[tr('Двугранный')])
    text = head + '\n\n' + '\n'.join(f'{k:<11} {a:<20} {v:>10}' for k, a, v in rows)
    self._report(tr('Таблица внутренних координат'), text, [(tr('Сохранить CSV…'), self.save_internal_csv)])
    return text


def molecular_size_text(self):
    from modules.compass.chemistry import molecular_size as ms

    s = ms.size(self.w.molecule)
    return '\n'.join([
        tr('Ван-дер-ваальсов объём: ') + f'{s["volume"]:.1f} Å³',
        tr('Площадь ван-дер-ваальсовой поверхности: ') + f'{s["area"]:.1f} Å²',
        tr('Площадь, доступная растворителю (зонд 1,4 Å): ') + f'{s["sasa"]:.1f} Å²',
        tr('Эффективный диаметр (шар того же объёма): ') + f'{s["diameter"]:.2f} Å', '',
        tr('Радиусы Ван-дер-Ваальса — Бонди (1964); объём — по сетке 0,1 Å, площади — 960 точек на атом '
           '(Шрейк — Рапли).')])


def show_molecular_size(self):
    if not self.w.molecule.atoms:
        return None
    text = self.molecular_size_text()
    self._report(tr('Объём и площадь поверхности'), text)
    return text


def show_statistics(self):
    if not self.w.molecule.atoms:
        return
    s = st.statistics(self.w.molecule)
    lines = [tr(f'Атомов: {s["count"]}')] + [f'  {k}: {n}' for k, n in s['atoms'].items()]
    lines += ['', tr(f'Связей: {s["bond_count"]}')] + [f'  {k}: {n}' for k, n in s['bonds'].items()]
    parts = st.fragments(self.w.molecule)
    if len(parts) > 1:
        lines += ['', tr(f'Отдельных фрагментов: {len(parts)}')]
    self._report(tr('Статистика атомов и связей'), '\n'.join(lines))


def show_masses(self):
    if not self.w.molecule.atoms:
        return
    m = st.masses(self.w.molecule)
    lines = [tr('Формула: ') + m['formula'], '',
             tr('Точная (моноизотопная) масса: ') + f'{m["exact"]:.5f} ' + tr('а. е. м.'),
             tr('Средняя молекулярная масса: ') + f'{m["average"]:.3f} ' + tr('г/моль')]
    if m['missing']:
        lines += ['', tr('Нет данных для элементов: ') + ', '.join(m['missing'])]
    self._report(tr('Масса молекулы'), '\n'.join(lines))

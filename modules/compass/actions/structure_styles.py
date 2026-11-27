"""The styles of the model of Compass: the window of styles, the bonds, the labels, the measurements, the numbers
of the camera. Methods of StructureTool (self is the tool; the window only through its port self.w), kept here to make
structure_actions.py shorter.

Split off modules/compass/actions/structure_actions.py (0.222.29).
"""

from PySide6.QtWidgets import QDialog, QDialogButtonBox, QFormLayout
from azimuth.i18n import tr


def _styles_window(self, title, rows, name, live=(), first=''):
    """A window of the styles of the model (modules/compass/actions/style_form.py) — rows of
    ('number', title, key, low, high, step, decimals, suffix), ('check', title, key, text), ('font', title, key),
    ('choice', title, key, ((value, text), …)), ('colour', title, key, standard, tip), ('shown', title, show key,
    colour key, standard, tip) of azimuth.defaults; «OK» keeps them (and the settings of the program), «По
    умолчанию» puts back those of the installation. The window is self.<name>."""
    from PySide6.QtWidgets import QCheckBox, QComboBox, QGroupBox, QVBoxLayout, QWidget

    from azimuth import defaults
    from modules.compass.actions import style_form as sf

    box = QDialog(self.w.widget)
    box.setWindowTitle(title)
    outer = QVBoxLayout(box)
    outer.setSpacing(4)

    def section(heading=''):
        """A group of rows with a heading — a group box (rounded, its heading semibold, the
        style sheet of azimuth/app.py); rows without a heading — on the window itself."""
        holder = QGroupBox(tr(heading)) if heading else QWidget()
        outer.addWidget(holder)
        return sf.styled_form(holder)

    # the first group has its heading too
    form = section(first)
    read, reset = {}, []
    applied = []
    for label, make_field in live:  # rows of the view itself (not of azimuth.defaults): (field, read,
        field, get, put_back, apply = make_field()  # reset, apply)
        sf.add(form, label, field)
        reset.append(put_back)
        applied.append((get, apply))
    for kind, label, key, *more in rows:
        if kind == 'heading':  # a heading of a group of rows; a group in its frame
            form = section(label)
            continue
        if kind == 'number':
            low, high, step, decimals, suffix = more
            field = sf.number(low, high, step, decimals, suffix, defaults.get(key))
            read[key] = field.value
            reset.append(lambda f=field, k=key: f.setValue(defaults.KEYS[k][1]))
        elif kind == 'check':
            field = QCheckBox(tr(more[0]))
            field.setChecked(defaults.get(key))
            read[key] = field.isChecked
            reset.append(lambda f=field, k=key: f.setChecked(defaults.KEYS[k][1]))
        elif kind == 'font':
            field = sf.font_box(defaults.get(key))
            read[key] = lambda f=field: sf.family_of(f)
            reset.append(lambda f=field: f.setCurrentIndex(0))
        elif kind == 'choice':
            field = QComboBox()
            for value, text in more[0]:
                field.addItem(tr(text), value)
            field.setCurrentIndex(max(0, field.findData(defaults.get(key))))
            read[key] = field.currentData
            reset.append(lambda f=field, k=key: f.setCurrentIndex(max(0, f.findData(defaults.KEYS[k][1]))))
        elif kind == 'colour':
            standard, tip = more
            dot = sf.ColourDot(defaults.get(key), standard, tr(tip), tr(label))
            field = sf.row(dot)
            read[key] = lambda d=dot: d.value
            reset.append(lambda d=dot: d.set(''))
        else:  # 'shown': shown or not, and its colour, on one line
            colour_key, standard, tip = more
            show = QCheckBox(tr('показывать'))
            show.setChecked(defaults.get(key))
            dot = sf.ColourDot(defaults.get(colour_key), standard, tr(tip), tr(label))
            field = sf.row(show, dot)
            read[key], read[colour_key] = show.isChecked, (lambda d=dot: d.value)
            reset += [lambda s=show: s.setChecked(True), lambda d=dot: d.set('')]
        sf.add(form, label, field)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
                               | QDialogButtonBox.StandardButton.RestoreDefaults)
    outer.addSpacing(8)
    outer.addWidget(buttons)
    buttons.rejected.connect(box.reject)

    def keep():
        for get, apply in applied:
            apply(get())
        self._keep_styles({key: get() for key, get in read.items()})
        box.accept()

    buttons.accepted.connect(keep)
    buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(lambda: [r() for r in reset])
    setattr(self, name, box)
    from azimuth.ui import open_window

    open_window(box)  # a window with its title, not a sheet
    return box


def _theme_ink(self, light, dark):
    return lambda: dark if self.w.viewer.dark else light


def _keep_styles(self, values):
    from azimuth import defaults

    for key, value in values.items():
        defaults.put(key, value, getattr(self.w, 'preferences', None))
    self.w.viewer.update()
    return {key: defaults.get(key) for key in values}


def set_view_option(self, name, value):
    """An option of the bonds of the view (as «Вид → Отображение связей»: its colouring, width, multiple
    bonds), kept in the preferences, the checks of the menu following."""
    setattr(self.w.viewer, name, value)
    preferences = getattr(self.w, 'preferences', None)
    if preferences is not None:
        preferences.setValue(name, value)
    menus = {'bond_color': getattr(self.w, 'bond_color_actions', {}),
             'bond_width': getattr(self.w, 'bond_width_actions', {})}
    for key, item in menus.get(name, {}).items():
        item.setChecked(key == value)
    option = getattr(self.w, 'bond_option_actions', {}).get(name)
    if option is not None:
        option.setChecked(bool(value))
    self.w.viewer.update()
    return value


def bond_style(self, values=None):
    """«Стиль связей…» — the colouring of the bonds (by the atoms, smoothly or in halves, or one colour of
    one's own), their width, the multiple bonds as several rods; the aromatic ones (marked in the menu of a bond):
    a line and dashes, two lines or one; the dashed ones (partial, coordination, long) and their colour; the long
    bonds dashed from a length; the hydrogen bonds — their colour, width and line."""
    if values is not None:
        for name in ('bond_color', 'bond_width', 'multiple_bonds'):
            if name in values:
                self.set_view_option(name, values[name])
        return self._keep_styles({k: v for k, v in values.items() if k in self.BOND_STYLE})
    from PySide6.QtWidgets import QCheckBox, QComboBox

    from modules.compass.actions import style_form as sf

    viewer = self.w.viewer

    def colouring():
        box = QComboBox()
        for key, text in (('smooth', 'по атомам · плавный переход'), ('split', 'по атомам · чёткая граница'),
                          ('uniform', 'одним цветом')):
            box.addItem(tr(text), key)
        box.setCurrentIndex(max(0, box.findData(viewer.bond_color)))
        return (box, box.currentData, lambda: box.setCurrentIndex(0),
                lambda v: self.set_view_option('bond_color', v))

    def width():
        field = sf.number(0.3, 3.0, 0.1, 1, ' ×', float(viewer.bond_width))
        return field, field.value, lambda: field.setValue(1.0), lambda v: self.set_view_option('bond_width', v)

    def multiple():
        field = QCheckBox(tr('двойные и тройные — несколькими цилиндрами'))
        field.setChecked(bool(viewer.multiple_bonds))
        return (field, field.isChecked, lambda: field.setChecked(True),
                lambda v: self.set_view_option('multiple_bonds', v))

    from modules.compass.view.bond_depth import UNIFORM

    return self._styles_window(tr('Стиль связей'), [
        ('colour', 'Один цвет', 'bond_uniform_color', lambda: UNIFORM[bool(viewer.dark)],
         '↺ — цвет по умолчанию; им связи рисуются, когда выбрано «одним цветом»'),
        ('heading', 'Типы связей', ''),
        ('choice', 'Ароматические', 'bond_aromatic_style',
         (('dashed', 'линия и пунктир'), ('double', 'две линии'), ('single', 'одна линия'))),
        ('colour', 'Цвет пунктирных', 'bond_partial_color', lambda: UNIFORM[bool(viewer.dark)],
         '↺ — цвета их атомов; пунктиром рисуются частичные и координационные связи (меню связи) и длинные'),
        ('check', '', 'bond_long_dashed', 'длинные связи — пунктиром'),
        ('number', 'Длинная — длиннее', 'bond_long_factor', 1.02, 1.6, 0.02, 2, ' × (r₁ + r₂)'),
        ('heading', 'Водородные связи', ''),
        ('colour', 'Цвет', 'hbond_color', self._theme_ink('#3d7dd8', '#7fb2ff'), '↺ — цвет по умолчанию'),
        ('number', 'Толщина', 'hbond_width', 0.5, 6.0, 0.1, 1, ' px'),
        ('choice', 'Линия', 'hbond_style', (('dotted', 'точки'), ('dashed', 'штрихи'), ('solid', 'сплошная'))),
    ], '_bond_style_box', live=[(tr('Цвет связей'), colouring), (tr('Толщина'), width), ('', multiple)],
       first='Все связи')


def label_style(self, values=None):
    """«Стиль подписей…»: the size of the letters of the labels of atoms (× the size that fits the atom);
    the font, bold, italic, the colour
    (by default the one that reads on its atom: white on a coloured atom, dark on hydrogen), an outline, the place
    (on the atom or beside it)."""
    if values is not None:
        return self._keep_styles({k: v for k, v in values.items() if k in self.LABEL_STYLE})
    return self._styles_window(tr('Стиль подписей'), [
        ('font', 'Шрифт', 'label_font'),
        ('number', 'Размер', 'label_scale', 0.6, 2.0, 0.1, 1, ' ×'),
        ('check', '', 'label_bold', 'жирный'),
        ('check', '', 'label_italic', 'курсив'),
        ('colour', 'Цвет', 'label_color', lambda: ('#ffffff', '#344354'),
         '↺ — цвет по умолчанию: белый на цветном атоме, тёмный на водороде'),
        ('check', '', 'label_outline', 'обводка букв (читается на любом фоне)'),
        ('choice', 'Где', 'label_place', (('centre', 'на атоме'), ('beside', 'рядом с атомом'))),
    ], '_label_style_box')


def measure_style(self, values=None):
    """«Стиль измерений…»: the size of the text of lengths and angles on the model, the decimals of a length;
    the font, bold, italic, the colour of the numbers and of the lines, the plate behind the numbers."""
    if values is not None:
        return self._keep_styles({k: v for k, v in values.items() if k in self.MEASURE_STYLE})
    return self._styles_window(tr('Стиль измерений'), [
        ('font', 'Шрифт', 'measure_font'),
        ('number', 'Размер текста', 'measure_size', 8, 24, 1, 0, ' px'),
        ('check', '', 'measure_bold', 'жирный'),
        ('check', '', 'measure_italic', 'курсив'),
        ('colour', 'Цвет чисел', 'measure_color', self._theme_ink('#1b2230', '#e7eaf0'),
         '↺ — цвет по умолчанию (свой у светлой и тёмной темы)'),
        ('colour', 'Цвет линий', 'measure_line_color', self._theme_ink('#2a62b8', '#6ea2f0'),
         '↺ — цвет по умолчанию (свой у светлой и тёмной темы)'),
        ('check', '', 'measure_plate', 'подложка под числами'),
        ('number', 'Знаков после запятой у длин', 'measure_decimals', 1, 5, 1, 0, ''),
    ], '_measure_style_box')


def set_camera_numbers(self, values=None):
    """«Положение камеры…»: the turns about the axes of the screen (°: yaw — about the vertical, pitch — about the
    horizontal, roll — about the line of sight) and the zoom; with «от осей модели» the turns count from X, Y, Z of
    the model (else from the view chosen last: the best view, a standard view)."""
    from math import degrees, radians

    v = self.w.viewer
    if values is not None:
        if values.get('model_axes'):
            v.basis = None
        v.yaw, v.pitch, v.roll = (radians(values.get(k, 0.0)) for k in ('yaw', 'pitch', 'roll'))
        v.zoom = min(6.0, max(0.15, values.get('zoom', v.zoom)))
        v.update()
        return v.yaw, v.pitch, v.roll, v.zoom
    from PySide6.QtWidgets import QCheckBox, QDoubleSpinBox

    box = QDialog(self.w.widget)
    box.setWindowTitle(tr('Положение камеры'))
    form = QFormLayout(box)
    fields = {}
    for key, title, value in (('yaw', 'Поворот вокруг вертикали', degrees(v.yaw)),
                              ('pitch', 'Поворот вокруг горизонтали', degrees(v.pitch)),
                              ('roll', 'Поворот в плоскости экрана', degrees(v.roll))):
        field = QDoubleSpinBox()
        field.setRange(-720, 720)
        field.setDecimals(2)
        field.setSuffix(' °')
        field.setValue(value)
        form.addRow(tr(title), field)
        fields[key] = field
    zoom = QDoubleSpinBox()
    zoom.setRange(0.15, 6.0)
    zoom.setDecimals(2)
    zoom.setSingleStep(0.1)
    zoom.setValue(v.zoom)
    form.addRow(tr('Масштаб'), zoom)
    model_axes = QCheckBox(tr('Углы — от осей X, Y, Z модели'))
    model_axes.setChecked(v.basis is None)
    model_axes.setToolTip(tr('Иначе — от ракурса, выбранного последним («Лучший ракурс», стандартный вид)'))
    form.addRow(model_axes)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    form.addRow(buttons)
    buttons.rejected.connect(box.reject)

    def accept():
        box.accept()
        self.set_camera_numbers({**{k: f.value() for k, f in fields.items()}, 'zoom': zoom.value(),
                                 'model_axes': model_axes.isChecked()})

    buttons.accepted.connect(accept)
    self._camera_box = box
    from azimuth.ui import open_window

    open_window(box)  # a window with its title, not a sheet
    return None

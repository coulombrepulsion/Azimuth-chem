"""Defaults of the whole program chosen in «Файл → Настройки»: bonds, the steps of an optimization,
pictures, spectra.

§1 PURPOSE Chemcraft keeps such choices in Tools → Preferences: how bonds are found (the bond-order threshold of GAMESS,
    0.25 there), a common orientation of all the geometries of an optimization or a scan, the image saved. Here the
    choices that were fixed in the code (1.22 × the covalent radii, half a bond of Mayer, ×3 pictures, 20 cm⁻¹ of the IR
    curve) become values of the settings; every default is the old fixed value, so nothing changes until the user
    changes it.
§2 ALGORITHM
    KEYS {key: (kind, default, choices)}: kind float or int — choices (low, high); bool; str — the allowed values.
    valid(key, value) converts a value of QSettings (an INI file gives text: 'true', '1.3') and returns the default
    for anything wrong. load(store) reads every key (a missing one — the default); put(key, value, store) checks,
    keeps and writes it. get(key) — the current value.
§4 SPECIFICATION KEYS; get(key); put(key, value, store=None) -> the value kept; load(store=None) -> dict; reset() — the
    defaults. Users: modules/compass/chemistry/builder.connections (bond_factor), result_overlay.mayer_structure
    (bond_order_min), trajectory_actions.show_trajectory_step (common_orientation), pictures / viewer (picture_scale,
    picture_transparent, picture_crop), spectrum.vibrations (ir_style, ir_width, ir_scale_on), spectrum.spectra_view
    (uv_fwhm); compass.layout (coordinate_unit), compass.trajectory_drawer and spectrum.reaction_view (energy_unit;
    energy_factor(), energy_name()), compass.bond_depth.draw_model (quick_atoms); compass.viewer (label_scale,
    measure_size, measure_decimals).
§7 TESTS
    tests/core/test_defaults.py; tests/test_gui.py::test_settings_window.
"""

import re

COLOR = 'color'  # the choices of a colour: '' or #rrggbb (valid)
FONT = 'font'  # the choices of a font: '' (that of the program) or the name of a family (printable, ≤ 80 letters)
KEYS = {
    'bond_factor': (float, 1.22, (1.05, 1.50)),  # bond if d <= factor × (r1 + r2), covalent radii
    'bond_order_min': (float, 0.5, (0.1, 1.0)),  # «Связи по порядкам Майера»: a bond where B >= this
    'common_orientation': (bool, False, None),  # the steps of an optimization or a scan turned onto the first
    'picture_scale': (int, 3, (2, 6)),  # «Снимок высокого разрешения (×N)»
    'picture_transparent': (bool, False, None),
    'picture_crop': (bool, True, None),  # a PNG cut to the molecule (else the whole field)
    'ir_style': (str, 'sticks', ('sticks', 'gauss')),
    'ir_width': (float, 20.0, (2.0, 200.0)),  # FWHM of the IR bands, cm⁻¹
    'ir_scale_on': (bool, False, None),  # the frequency factor of NIST CCCBDB switched on when a result opens
    'uv_fwhm': (float, 0.3, (0.05, 2.0)),  # FWHM of UV-Vis and ECD bands, eV
    # units, the quick drawing of large models
    'coordinate_unit': (str, 'angstrom', ('angstrom', 'bohr')),  # the table of coordinates of Compass on opening
    'energy_unit': (str, 'kcal', ('kcal', 'kj', 'ev')),  # ΔE of the steps, scans, conformers; the reaction diagram
    'quick_atoms': (int, 0, (0, 5000)),  # from this many atoms every frame is a fast one (0 — never)
    # «Вид → Стиль подписей…» and «Стиль измерений…»
    'label_scale': (float, 1.0, (0.6, 2.0)),  # the letters of the labels of atoms × this
    'measure_size': (int, 11, (8, 24)),  # px of the text of lengths and angles on the model
    'measure_decimals': (int, 3, (1, 5)),  # decimals of a length; an angle one less, a dihedral two less
    # the font, its weight and slant, the colour ('' — that of the program:
    # for a label the one that reads on its atom), an outline, the place of a label; the lines and the plate of a
    # measurement
    'label_font': (str, '', FONT),
    'label_bold': (bool, True, None),
    'label_italic': (bool, False, None),
    'label_color': (str, '', COLOR),
    'label_outline': (bool, False, None),  # a thin outline of the other colour round the letters
    'label_place': (str, 'centre', ('centre', 'beside')),  # on the atom, or beside it (up to the right)
    'measure_font': (str, '', FONT),
    'measure_bold': (bool, False, None),
    'measure_italic': (bool, False, None),
    'measure_color': (str, '', COLOR),  # of the numbers
    'measure_line_color': (str, '', COLOR),  # of the dashed lines of a measurement
    'measure_plate': (bool, True, None),  # the plate behind the numbers
    # «Настройки → Расчёты» — the best conformer of every structure of a queue before its calculation
    'batch_conformers': (bool, False, None),
    'batch_conformer_method': (str, 'auto', ('auto', 'rdkit', 'scan', 'abc', 'crest')),
    # «Правка → Векторы и плоскости → Стиль…»; a colour is '' (the colour of the theme) or #rrggbb (COLOR: any such
    # text)
    'guide_vector_color': (str, '', COLOR),
    'guide_normal_color': (str, '', COLOR),
    'guide_plane_color': (str, '', COLOR),
    'guide_vector_show': (bool, True, None),
    'guide_normal_show': (bool, True, None),
    'guide_plane_show': (bool, True, None),
    'guide_width': (float, 2.4, (0.5, 8.0)),  # px of the arrows and of the edge of a plane
    'guide_plane_opacity': (int, 18, (0, 100)),  # % of the fill of a plane
    'guide_plane_edge': (bool, True, None),  # the edge of a plane drawn
    'guide_numbers': (bool, True, None),  # the number of each guide beside it
    'guide_normal_length': (float, 1.5, (0.3, 10.0)),  # Å
    'guide_plane_margin': (float, 0.8, (0.0, 5.0)),  # Å around the atoms of a plane
    # «Вид → Отображение связей → Стиль связей…»
    'bond_uniform_color': (str, '', COLOR),  # the one colour of «Одноцветные» ('' — that of the theme)
    'bond_aromatic_style': (str, 'dashed', ('dashed', 'double', 'single')),  # a bond marked aromatic: a line + dashes
    'bond_partial_color': (str, '', COLOR),  # the dashed bonds (partial, coordination, long) — '' their atoms' colours
    'bond_long_dashed': (bool, False, None),  # a bond much longer than usual for its atoms — dashed
    'bond_long_factor': (float, 1.12, (1.02, 1.6)),  # «much longer»: d > this × (r1 + r2), covalent radii
    'hbond_color': (str, '', COLOR),  # the hydrogen bonds on the model ('' — the blue of the theme)
    'hbond_width': (float, 1.6, (0.5, 6.0)),  # px
    'hbond_style': (str, 'dotted', ('dotted', 'dashed', 'solid')),
}
# hartree -> the unit (CODATA 2018: 627.509474 kcal/mol, 2625.499639 kJ/mol, 27.211386246 eV); the names are tr keys
ENERGY_UNITS = {'kcal': (627.509474, 'ккал/моль'), 'kj': (2625.499639, 'кДж/моль'), 'ev': (27.211386246, 'эВ')}
_values = {}


def valid(key, value):
    kind, default, choices = KEYS[key]
    try:
        if kind is bool:
            if isinstance(value, str):
                text = value.strip().lower()
                if text not in ('true', 'false', '1', '0'):
                    return default
                return text in ('true', '1')
            return bool(value) if isinstance(value, (bool, int)) else default
        if kind is str and choices == FONT:
            text = str(value).strip()
            return text if len(text) <= 80 and text.isprintable() else default
        if kind is str and choices == COLOR:
            text = str(value).strip()
            return text.lower() if text == '' or re.fullmatch(r'#[0-9a-fA-F]{6}', text) else default
        if kind is str:
            return value if value in choices else default
        number = kind(float(value)) if kind is int else float(value)
    except (TypeError, ValueError):
        return default
    if number != number or not choices[0] <= number <= choices[1]:  # NaN or out of range
        return default
    return number


def get(key):
    return _values.get(key, KEYS[key][1])


def put(key, value, store=None):
    kept = valid(key, value)
    _values[key] = kept
    if store is not None:
        store.setValue(key, kept)
    return kept


def load(store=None):
    for key, (_, default, _) in KEYS.items():
        raw = store.value(key, default) if store is not None else default
        _values[key] = valid(key, raw)
    return dict(_values)


def reset():
    _values.clear()


def energy_factor():
    """Hartree -> the energy unit of «Настройки → Единицы»."""
    return ENERGY_UNITS[get('energy_unit')][0]


def energy_name():
    """The name of the energy unit (Russian, the key of tr)."""
    return ENERGY_UNITS[get('energy_unit')][1]

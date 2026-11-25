"""Display schemes of the Compass model: ready looks and the user's own.

§1 THEORY
    A scheme is a named set of the settings that decide how the model looks, as Chemcraft's display
    schemes: the model (balls and sticks, sticks, space filling), the bonds (colouring, width, shown,
    multiple), the labels, the projection, the axes, the size of the atoms, the element colours (a
    palette and individual colours), the background and the dot grid. Applying a scheme sets all of
    them at once; the current look can be saved under a name.
§2 ALGORITHM
    normalize(data): every key of FIELDS must be present with an allowed value (sets of names, ranges
    of numbers, booleans; colours '#rrggbb' for element symbols), unknown keys are refused. palette(s):
    the base palette ('azimuth': the colours of the program, other elements the neutral fallback;
    'jmol': the Jmol colours of elements 1-109; 'mono': grey levels of the Jmol colours with the
    luminance 0.2126 R + 0.7152 G + 0.0722 B of Rec. 709, kept in the same order), then the individual
    colours. same(a, b): equal after normalize, the numbers to 1e-9.
§3 APPLICATIONS
    modules/compass/actions/scheme_actions.py («Вид → Схема отображения», «Цвет элемента…»), the viewer.
§4 SPECIFICATION
    FIELDS, DEFAULT, BUILTIN {name (ru): scheme}; normalize(dict) -> dict; palette(scheme) -> {symbol:
    '#rrggbb'} for every symbol of azimuth.core.SYMBOLS; parse(text) -> {name: scheme};
    dump({name: scheme}) -> text; same(a, b) -> bool. ValueError for every refused input.
§5 PROCEDURES - below.
§6 NOTES
    The Jmol colours (JMOL) were checked on 2026-10-24 against the table «CPK-Jmol periodic table» of
    sciencenotes.org (its layout shifts groups 15-17 and the f-block by one cell; the values were read
    in atomic-number order); elements above 109 have none there and use the neutral colour. The
    default scheme reproduces the look exactly (AZIMUTH is viewer.COLORS).
§7 TESTS
    tests/compass/test_schemes.py.
§8' ROBUSTNESS / ERRORS
    A damaged user scheme is refused with its name; the built-in ones are checked at import.
"""

import json
from math import isfinite

from azimuth.core import SYMBOLS
from azimuth.i18n import tr

NEUTRAL = '#9c80b7'  # the colour of elements the program has none for (as before)
# The colours of the program (modules/compass/view/viewer.COLORS is this dict; moved here 2026-10-24 so the
# schemes need no Qt)
AZIMUTH = {
    'H': '#e2e8ec',
    'C': '#45566a',
    'N': '#5278d6',
    'O': '#df645b',
    'F': '#74b887',
    'Cl': '#74b887',
    'S': '#e9b64b',
    'P': '#d28a4d',
}

JMOL = dict(
    zip(
        SYMBOLS[:109],
        (
            'FFFFFF D9FFFF CC80FF C2FF00 FFB5B5 909090 3050F8 FF0D0D 90E050 B3E3F5 AB5CF2 8AFF00 BFA6A6 F0C8A0 FF8000 '
            'FFFF30 1FF01F 80D1E3 8F40D4 3DFF00 E6E6E6 BFC2C7 A6A6AB 8A99C7 9C7AC7 E06633 F090A0 50D050 C88033 7D80B0 '
            'C28F8F 668F8F BD80E3 FFA100 A62929 5CB8D1 702EB0 00FF00 94FFFF 94E0E0 73C2C9 54B5B5 3B9E9E 248F8F 0A7D8C '
            '006985 C0C0C0 FFD98F A67573 668080 9E63B5 D47A00 940094 429EB0 57178F 00C900 70D4FF FFFFC7 D9FFC7 C7FFC7 '
            'A3FFC7 8FFFC7 61FFC7 45FFC7 30FFC7 1FFFC7 00FF9C 00E675 00D452 00BF38 00AB24 4DC2FF 4DA6FF 2194D6 267DAB '
            '266696 175487 D0D0E0 FFD123 B8B8D0 A6544D 575961 9E4FB5 AB5C00 754F45 428296 420066 007D00 70ABFA 00BAFF '
            '00A1FF 008FFF 0080FF 006BFF 545CF2 785CE3 8A4FE3 A136D4 B31FD4 B31FBA B30DA6 BD0D87 C70066 CC0059 D1004F '
            'D90045 E00038 E6002E EB0026'
        ).split(),
    )
)
if len(JMOL) != 109:
    raise ValueError('schemes.JMOL: 109 colours expected')

FIELDS = {
    'display_mode': ('ball-stick', 'sticks', 'spacefill'),
    'bond_color': ('smooth', 'split', 'uniform'),
    'bond_width': (0.3, 3.0),
    'show_bonds': bool,
    'multiple_bonds': bool,
    'label_mode': ('none', 'number', 'element', 'both', 'group'),  # 'group' — C1, H1 within the element
    'perspective': bool,
    'show_axes': bool,
    'atom_scale': (0.4, 2.5),
    'palette': ('azimuth', 'jmol', 'mono'),
    'colors': dict,
    'background': ('theme', 'white', 'black'),
    'grid': bool,
}

DEFAULT = {
    'display_mode': 'ball-stick',
    'bond_color': 'smooth',
    'bond_width': 1.0,
    'show_bonds': True,
    'multiple_bonds': True,
    'label_mode': 'element',
    'perspective': False,
    'show_axes': False,
    'atom_scale': 1.0,
    'palette': 'azimuth',
    'colors': {},
    'background': 'theme',
    'grid': True,
}


def normalize(data):
    """A complete, checked scheme (see §2)."""
    if not isinstance(data, dict):
        raise ValueError(tr('Схема отображения повреждена.'))
    unknown = set(data) - set(FIELDS)
    if unknown:
        raise ValueError(tr('Неизвестные параметры схемы: ') + ', '.join(sorted(unknown)))
    out = {}
    for key, rule in FIELDS.items():
        if key not in data:
            raise ValueError(tr('В схеме нет параметра ') + key)
        value = data[key]
        if rule is bool:
            if not isinstance(value, bool):
                raise ValueError(tr('Неверное значение параметра ') + key)
        elif rule is dict:
            if not isinstance(value, dict):
                raise ValueError(tr('Неверное значение параметра ') + key)
            colors = {}
            for symbol, color in value.items():
                if symbol not in SYMBOLS or not _is_color(color):
                    raise ValueError(tr('Неверный цвет элемента: ') + str(symbol))
                colors[symbol] = color.lower()
            value = colors
        elif isinstance(rule[0], str):
            if value not in rule:
                raise ValueError(tr('Неверное значение параметра ') + key)
        else:
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
                raise ValueError(tr('Неверное значение параметра ') + key)
            if not rule[0] <= value <= rule[1]:
                raise ValueError(tr('Неверное значение параметра ') + key)
            value = float(value)
        out[key] = value
    return out


def _is_color(text):
    return (
        isinstance(text, str)
        and len(text) == 7
        and text[0] == '#'
        and all(c in '0123456789abcdefABCDEF' for c in text[1:])
    )


def _grey(hex6):
    r, g, b = (int(hex6[k : k + 2], 16) for k in (0, 2, 4))
    y = round(0.2126 * r + 0.7152 * g + 0.0722 * b)
    return f'#{y:02x}{y:02x}{y:02x}'


def palette(scheme):
    """{symbol: '#rrggbb'} for every element (see §2)."""
    s = normalize(scheme)
    if s['palette'] == 'azimuth':
        base = {sym: AZIMUTH.get(sym, NEUTRAL) for sym in SYMBOLS}
    elif s['palette'] == 'jmol':
        base = {sym: ('#' + JMOL[sym].lower()) if sym in JMOL else NEUTRAL for sym in SYMBOLS}
    else:
        base = {sym: _grey(JMOL[sym]) if sym in JMOL else _grey(NEUTRAL[1:]) for sym in SYMBOLS}
    base.update(s['colors'])
    return base


def _scheme(**changes):
    s = dict(DEFAULT)
    s['colors'] = {}
    s.update(changes)
    return normalize(s)


BUILTIN = {
    'Азимут (по умолчанию)': _scheme(),
    'Публикация · белый фон': _scheme(palette='jmol', background='white', grid=False, label_mode='none'),
    'Чёрно-белая': _scheme(palette='mono', background='white', grid=False, bond_color='uniform', label_mode='element'),
    'Цвета Jmol': _scheme(palette='jmol'),
    'Стержни': _scheme(display_mode='sticks', label_mode='none', bond_width=1.6),
    'Объёмная модель': _scheme(display_mode='spacefill', label_mode='none', palette='jmol'),
    'Презентация': _scheme(atom_scale=1.3, bond_width=1.6, label_mode='both', background='black', grid=False),
}


def same(a, b):
    a, b = normalize(a), normalize(b)
    for key in FIELDS:
        x, y = a[key], b[key]
        if isinstance(x, float):
            if abs(x - y) > 1e-9:
                return False
        elif x != y:
            return False
    return True


def parse(text):
    try:
        data = json.loads(text)
    except (TypeError, ValueError) as exc:
        raise ValueError(tr('Файл схем повреждён.')) from exc
    if not isinstance(data, dict) or data.get('version') != 1 or not isinstance(data.get('schemes'), dict):
        raise ValueError(tr('Это не файл схем отображения «Азимута».'))
    out = {}
    for name, scheme in data['schemes'].items():
        if not isinstance(name, str) or not name.strip() or len(name) > 60:
            raise ValueError(tr('Неверное название схемы.'))
        try:
            out[' '.join(name.split())] = normalize(scheme)
        except ValueError as exc:
            raise ValueError(tr('Схема «') + name + '»: ' + str(exc)) from exc
    return out


def dump(schemes):
    return json.dumps({'version': 1, 'schemes': {k: normalize(v) for k, v in schemes.items()}}, ensure_ascii=False, indent=1)

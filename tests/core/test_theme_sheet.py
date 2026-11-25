"""One style sheet for both themes (azimuth/theme_sheet.py).

Oracles, written here by hand: the light sheet stays as it is at the start; every selector of the dark sheet comes
twice — inside a dark window (`*[azimuthDark="true"] S`) and, for one compound, with the attribute before the
pseudo-states and subcontrols (QComboBox::down-arrow:on → QComboBox[azimuthDark="true"]::down-arrow:on; an attribute
already there stays first); a descendant selector only in the first form.
"""

from azimuth import theme_sheet as ts

LIGHT = 'QWidget {color: #111;}\nQPushButton:hover {background: #eee;}\n'
DARK = ('QWidget {color: #eee;}\nQPushButton:hover {background: #222;}\nQComboBox::down-arrow:on {top: 1px;}\n'
        'QLabel#toast[busy="true"] {padding-left: 36px;}\nQFrame#a QTableWidget, QMenu {border: none;}\n')


def test_self_form():
    assert ts.self_form('QWidget') == 'QWidget[azimuthDark="true"]'
    assert ts.self_form('QComboBox::down-arrow:on') == 'QComboBox[azimuthDark="true"]::down-arrow:on'
    assert ts.self_form('QPushButton[iconic="true"]:hover') == 'QPushButton[iconic="true"][azimuthDark="true"]:hover'
    assert ts.self_form('QLabel#toast[busy="true"]') == 'QLabel#toast[busy="true"][azimuthDark="true"]'


def test_both():
    text = ts.both(LIGHT, DARK)
    assert text.startswith(LIGHT)
    rules = ts.rules(text[len(LIGHT):])
    assert [body for _, body in rules] == [body for _, body in ts.rules(DARK)]
    assert rules[0][0] == '*[azimuthDark="true"] QWidget, QWidget[azimuthDark="true"]'
    assert rules[1][0] == '*[azimuthDark="true"] QPushButton:hover, QPushButton[azimuthDark="true"]:hover'
    assert rules[4][0] == '*[azimuthDark="true"] QFrame#a QTableWidget, *[azimuthDark="true"] QMenu, QMenu[azimuthDark="true"]'

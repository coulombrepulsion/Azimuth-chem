"""The typeface carried by the program (azimuth/fonts.py): Inter from assets/fonts — the files are there and load, the
weights of the style sheet are found, Cyrillic and Greek are drawn with it, the style sheet names it first, the files
are in the manifest of the assets."""

import hashlib
import json
import re

from PySide6.QtGui import QFont, QFontInfo, QFontMetrics
from PySide6.QtWidgets import QApplication

from azimuth import fonts
from azimuth.app_style import STYLE
from azimuth.paths import ROOT


def app():
    return QApplication.instance() or QApplication([])


def test_the_files_are_there_with_their_license():
    for name in fonts.FILES + ('LICENSE-inter.txt',):
        assert (fonts.FOLDER / name).is_file(), name
    assert 'SIL OPEN FONT LICENSE' in (fonts.FOLDER / 'LICENSE-inter.txt').read_text(encoding='utf-8')


def test_the_weights_of_the_style_sheet_are_found():
    app()
    assert fonts.install() == fonts.FAMILY == fonts.install()  # once
    for weight in (400, 500, 600, 700):
        font = QFont(fonts.FAMILY)
        font.setPixelSize(13)
        font.setWeight(QFont.Weight(weight))
        info = QFontInfo(font)
        assert info.family() == fonts.FAMILY and info.weight() == weight, (weight, info.family(), info.weight())
    italic = QFont(fonts.FAMILY)
    italic.setItalic(True)
    assert QFontInfo(italic).italic() and QFontInfo(italic).family() == fonts.FAMILY


def test_russian_and_greek_letters_are_its_own():
    app()
    fonts.install()
    font = QFont(fonts.FAMILY)
    font.setPixelSize(13)
    metrics = QFontMetrics(font)
    for text in ('Азимут', 'Секстант ЁЖЩЫЭЮЯ', 'αβγδεσπψΔΣΩ', '→ ± ≈ ≤ × · ² ₂ Å'):
        assert all(metrics.inFontUcs4(ord(c)) for c in text if not c.isspace()), text


def test_the_windows_keep_the_font_of_the_system():
    # the owner, 2026-11-27: Inter looked too sharp on Windows («раньше он был мягче») — the windows are drawn with the
    # font of the system again; the files stay in assets/fonts, loaded by nothing but install()
    family = re.search(r'QWidget \{font-family: ([^;]+);', STYLE).group(1)
    names = [name.strip(" '") for name in family.split(',')]
    assert names == ['Segoe UI', 'Helvetica Neue', 'sans-serif'] and fonts.FAMILY not in names
    assert 'fonts.install' not in (ROOT / 'azimuth' / 'app.py').read_text(encoding='utf-8')


def test_the_files_are_in_the_manifest():
    manifest = json.loads((ROOT / 'assets-manifest.json').read_text(encoding='utf-8'))
    for name in fonts.FILES + ('LICENSE-inter.txt',):
        path = fonts.FOLDER / name
        assert manifest[f'assets/fonts/{name}'] == hashlib.sha256(path.read_bytes()).hexdigest(), name

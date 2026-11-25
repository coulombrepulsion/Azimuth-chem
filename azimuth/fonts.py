"""The typeface of the program: Inter (SIL Open Font License 1.1), carried in assets/fonts.

§1 PURPOSE
    The windows were drawn with the font of the system — Helvetica Neue on macOS, Segoe UI on Windows — and the same
    window had other widths and heights on each: a task of Sextant fitted the window of 1133 × 730 on a Mac and not on
    Windows (2026-11-25), and the tests measured another font on every system. The owner, 2026-11-25: the fonts of the
    program go with it, «чтобы он не искал их в других компьютерах». Nothing is downloaded: the files lie in the folder
    of the program.
§2 RULES
    1. install() registers every file of FILES with QFontDatabase once per process and returns FAMILY, or '' when none
       could be loaded (the style sheet then falls back to the system fonts it names after it).
    2. The weights of the style sheet — 400, 500, 600, 700 — have a file each, and an italic of 400. The files keep
       Latin with its first extension, Greek, Russian and Ukrainian Cyrillic, punctuation, super- and subscripts,
       arrows and the mathematical operators (fontTools subset of Inter 4.0); other letters — Chinese among them — come
       from the fonts of the system, as before.
    3. The menus keep the font of the system (azimuth.ui.menu_font_family), the code and the input files a monospace
       one of the system (Menlo, Consolas); the sidebar keeps Golos Text (hub.branding).
§3 INTERFACE
    FAMILY, FILES, FOLDER; install() -> str.
§4 TESTS
    tests/core/test_fonts.py — every file is there and loads, the four weights and the italic are found, Cyrillic and
    Greek are drawn with it, the style sheet names it first.
"""

from pathlib import Path

FAMILY = 'Inter'
FOLDER = Path(__file__).resolve().parent.parent / 'assets' / 'fonts'
FILES = ('Inter-Regular.otf', 'Inter-Italic.otf', 'Inter-Medium.otf', 'Inter-SemiBold.otf', 'Inter-Bold.otf')
_done = []


def install():
    """Register the files of the typeface (once); FAMILY, or '' when nothing could be loaded."""
    if _done:
        return _done[0]
    from PySide6.QtGui import QFontDatabase

    loaded = [QFontDatabase.addApplicationFont(str(FOLDER / name)) for name in FILES if (FOLDER / name).is_file()]
    _done.append(FAMILY if any(i >= 0 for i in loaded) else '')
    return _done[0]

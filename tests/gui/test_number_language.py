"""The screenshots of the site in English and Chinese showed «298,15 K», «1,000 atm» (read as a thousand)
and the Russian name of the folder of calculations in the hint of Sextant. The fields follow the language of the
program (azimuth/qt_language.numbers), not the system of the computer; the hints name no folder."""

import json
from pathlib import Path

from PySide6.QtWidgets import QDoubleSpinBox

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers

ROOT = Path(__file__).resolve().parents[2]


def test_the_fields_write_numbers_in_the_language_of_the_program(app):
    from azimuth import qt_language

    before = QDoubleSpinBox()  # made before the language changes: told too
    before.setDecimals(3)
    before.setRange(0, 10000)
    before.setValue(1)
    try:
        for language, one, kelvin in (('en', '1.000', '298.15'), ('zh', '1.000', '298.15'), ('ru', '1,000', '298,15')):
            qt_language.numbers(language)
            after = QDoubleSpinBox()
            after.setRange(0, 10000)
            after.setValue(298.15)
            assert before.text() == one, language
            assert after.text() == kelvin, language
            before.setValue(1500)
            assert before.text() == ('1500.000' if language != 'ru' else '1500,000')  # no separator of thousands
            before.setValue(1)
    finally:
        qt_language.numbers('ru')


def test_the_hints_of_sextant_name_no_folder():
    for path in ('modules/sextant/workspace.py', 'modules/sextant/calculation_page.py', 'modules/sextant/crystal_mode.py'):
        assert 'Документы/Azimuth/Расчёты)' not in (ROOT / path).read_text(encoding='utf-8'), path
    for language in ('en', 'zh'):
        table = json.loads((ROOT / 'azimuth' / 'locale' / f'{language}.json').read_text(encoding='utf-8'))
        hints = [v for k, v in table.items() if 'показывает кнопка с папкой' in k]
        assert len(hints) == 2 and not any('Расчёты' in v for v in hints), language

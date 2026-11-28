"""0.249.14 (the owner, 2026-11-28: the explanation under the input file «можно перенести под вопросительный знак.
Тогда больше места будет»): a long explanation lies behind «?» (azimuth.ui.help_button), not on the page — no label of
a constant text of LONG characters or more, but the few that tell how to fill in the field under them."""

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LONG = 200
# what to type (the format of the field), a warning before an action, a reference table — kept on the page
KEPT = {
    'azimuth/handbook_window.py',
    'modules/sextant/batch_retry.py',
    'modules/spectrum/views/nmr_compare_view.py',
    'modules/spectrum/views/nmr_conformers_view.py',
}


def long_labels(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, 'attr', '')
        if name not in ('label', 'QLabel', 'WrappedNote'):
            continue
        text = node.args[0]
        if isinstance(text, ast.Call) and getattr(text.func, 'id', '') == 'tr' and text.args:
            text = text.args[0]
        if isinstance(text, ast.Constant) and isinstance(text.value, str) and len(text.value) >= LONG:
            yield node.lineno, text.value[:60]


def test_long_explanations_are_behind_a_question_mark():
    found = []
    for folder in ('azimuth', 'modules', 'hub'):
        for path in sorted((ROOT / folder).rglob('*.py')):
            rel = path.relative_to(ROOT).as_posix()
            if rel in KEPT:
                continue
            found += [f'{rel}:{line} {text}' for line, text in long_labels(path)]
    assert not found, found

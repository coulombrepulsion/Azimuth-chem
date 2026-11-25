"""Text from other programs and files is read as UTF-8, never in the locale code page.

Contract. On Windows with the Russian locale Python decodes `subprocess.run(..., text=True)` and
`Path.read_text()` in cp1251 unless an encoding is given; a byte that cp1251 does not define (0x98)
then stops the program with UnicodeDecodeError. The program's own code therefore names the encoding
at every such call, and the output of other programs is decoded with errors='replace': an unknown byte
becomes U+FFFD, the rest of the text stays readable.

Oracles: a real child process that writes known bytes (independent of the decoding code under test);
the Python grammar (ast) for the source check.
"""

import ast
import sys
from pathlib import Path

from modules.sextant import advice, vpn

from tests.program_files import python_files

ROOT = Path(__file__).resolve().parents[2]
SKIP = {'.venv', '.git', '_to_delete', 'tests', '__pycache__', 'build', 'dist'}

# 0x98 is undefined in cp1251 and is not a valid start byte in UTF-8; then «Тест» in UTF-8.
CHILD = "import sys; sys.stdout.buffer.write(b'ok \\x98 ' + 'Тест'.encode('utf-8')); sys.stdout.flush()"


def test_output_with_an_unknown_byte_is_read_not_raised():
    text = advice._run([sys.executable, '-c', CHILD])
    assert text == 'ok � Тест'


def test_vpn_reply_with_an_unknown_byte_is_read_not_raised():
    text = vpn._run(sys.executable, ['-c', CHILD], 30)
    assert text == 'ok � Тест'


def program_sources():
    for path in python_files(skip=SKIP):  # not walking the environment (tests/program_files.py)
        parts = set(path.relative_to(ROOT).parts[:-1])
        if not parts & SKIP and not any(p.startswith('.') for p in parts):
            yield path


def calls_without_encoding(path):
    tree = ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else getattr(func, 'id', '')
        keywords = {k.arg for k in node.keywords}
        if 'encoding' in keywords:
            continue
        as_text = any(k.arg in ('text', 'universal_newlines') and isinstance(k.value, ast.Constant) and k.value.value
                      for k in node.keywords)
        if name in ('run', 'Popen', 'check_output') and as_text:
            yield node.lineno, f'subprocess.{name}(text=True)'
        elif name == 'read_text' and not node.args or name == 'write_text' and len(node.args) < 2:
            yield node.lineno, name
        elif name == 'open' and isinstance(func, ast.Name):
            mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == 'mode'), None)
            mode = mode.value if isinstance(mode, ast.Constant) else 'r'
            if 'b' not in str(mode):
                yield node.lineno, f'open({mode!r})'


def test_program_code_names_the_encoding():
    sources = list(program_sources())
    assert len(sources) > 100  # the walk found the program, not an empty folder
    found = [f'{path.relative_to(ROOT)}:{line} {what}' for path in sources for line, what in calls_without_encoding(path)]
    assert found == []

"""Atoms named by their element and number — «H1», «C3–C8» — wherever the user types or reads atom numbers.

§1 PURPOSE
    Wherever atom numbers are typed (maps, fragments), the fields show the atoms as «H1»
    and take both forms: «1-4, 7», «N1, H2-H4», «C3–C8», a bare element «H» for all its atoms; a symbol that is not the
    element of that atom is refused (the number was mistyped). What goes to Multiwfn stays numbers.
§4 SPECIFICATION
    label(symbols, k) -> «H1» (k 0-based); parse(text, count, symbols=None) -> sorted 1-based numbers (ValueError with
    what is wrong); text(numbers (1-based), symbols=None) -> «N1, H2–H4» (ranges of three and more; without symbols —
    «1, 2–4»).
§7 TESTS tests/core/test_atom_labels.py."""

import re

from azimuth.i18n import tr

_ATOM = r'([A-Z][a-z]?)?\s*(\d+)'
_PART = re.compile(_ATOM + r'(?:\s*[-–—]\s*' + _ATOM + r')?')
_ELEMENT = re.compile(r'[A-Z][a-z]?')


def label(symbols, k):
    return f'{symbols[k]}{k + 1}' if symbols is not None and 0 <= k < len(symbols) else str(k + 1)


def _check(symbols, number, symbol):
    if symbol and symbols is not None and symbols[number - 1] != symbol:
        raise ValueError(tr(f'Атом {number} — {symbols[number - 1]}, а не {symbol}: проверьте номер.'))


def parse(text, count, symbols=None):
    """«1-4, 7», «N1, H2-H4», «C3–C8», «H» (every H) → sorted 1-based numbers; commas, semicolons or spaces between."""
    numbers = set()
    for part in re.split(r'[,;\s]+(?![-–—])(?<![-–—][,;\s])', (text or '').strip()):
        part = part.strip()
        if not part:
            continue
        if _ELEMENT.fullmatch(part) and symbols is not None:
            found = [k + 1 for k, s in enumerate(symbols) if s == part]
            if not found:
                raise ValueError(tr(f'Атомов {part} в молекуле нет.'))
            numbers.update(found)
            continue
        m = _PART.fullmatch(part)
        if not m:
            raise ValueError(tr(f'Не понимаю «{part}»: атомы — номерами или с символом (1-4, 7 или N1, H2-H4), через '
                                'запятую, диапазоны через дефис.'))
        first = int(m.group(2))
        last = int(m.group(4)) if m.group(4) else first
        for number in (first, last):
            if not 1 <= number <= count:
                raise ValueError(tr(f'Атомов {count}: номер {number} вне их.'))
        _check(symbols, first, m.group(1))
        _check(symbols, last, m.group(3))
        if first > last:
            first, last = last, first
        numbers.update(range(first, last + 1))
    return sorted(numbers)


def text(numbers, symbols=None):
    """1-based numbers as «N1, H2–H4» (with symbols) or «1, 2–4»; ranges from three atoms in a row on."""
    numbers = sorted(set(numbers))
    name = (lambda n: label(symbols, n - 1)) if symbols is not None else str
    parts, k = [], 0
    while k < len(numbers):
        j = k
        while j + 1 < len(numbers) and numbers[j + 1] == numbers[j] + 1:
            j += 1
        if j - k >= 2:
            parts.append(f'{name(numbers[k])}–{name(numbers[j])}')
        else:
            parts.extend(name(n) for n in numbers[k:j + 1])
        k = j + 1
    return ', '.join(parts)

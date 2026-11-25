"""«Правка → Вставить блок» of Sextant (2026-11-21
the blocks of an input written by hand most often, put where the program expects them).

§1 PURPOSE
    The blocks a user adds to an input of ORCA or Gaussian by hand — the processes and the memory, the convergence of
    the SCF, the constraints of an optimisation, the excited states, the solvent, the printing of the orbitals, the
    numerical frequencies, the orbitals of a previous run — ready, with the usual values, at their place in the file.
§2 RULES
    ORCA: a block goes before the line of the coordinates («* xyz …», «*xyzfile …»), after the keywords («!» lines)
    and the other blocks; a keyword it needs («! MORead») goes after the last «!» line. Gaussian: the lines of Link 0
    («%nprocshared», «%mem», «%chk») go at the very top, before the route («#»). Without such a line — at the end.
§4 SPECIFICATION
    BLOCKS = {kind: ((title, text, keyword or ''), …)}; place(text, kind) -> int (the position of the block);
    keyword_place(text) -> int (after the last «!» line); inserted(text, kind, block, keyword='') -> str.
§7 TESTS
    tests/sextant/test_input_blocks.py.
"""

import re

BLOCKS = {
    'orca': (
        ('Параллельный расчёт (%pal)', '%pal\n  nprocs 4\nend', ''),
        ('Память на процесс, МБ (%maxcore)', '%maxcore 2000', ''),
        ('Сходимость SCF (%scf)', '%scf\n  maxiter 300\nend', ''),
        ('Ограничения оптимизации (%geom)', '%geom\n  Constraints\n    { B 0 1 C }  # длина связи атомов 0–1\n  end\nend', ''),
        ('Возбуждённые состояния (%tddft)', '%tddft\n  nroots 10\nend', ''),
        ('Растворитель SMD (%cpcm)', '%cpcm\n  smd true\n  SMDsolvent "water"\nend', 'CPCM'),
        ('Печать орбиталей (%output)', '%output\n  print[p_mos] 1\nend', ''),
        ('Численные частоты (%freq)', '%freq\n  numfreq true\nend', ''),
        ('Орбитали прошлого расчёта (%moinp)', '%moinp "previous.gbw"', 'MORead'),
    ),
    'gaussian': (
        ('Процессоры (%nprocshared)', '%nprocshared=4', ''),
        ('Память (%mem)', '%mem=4GB', ''),
        ('Файл контрольной точки (%chk)', '%chk=job.chk', ''),
    ),
}


def _lines(text):
    return text.split('\n')


def _offset(lines, index):
    return sum(len(line) + 1 for line in lines[:index])


def place(text, kind):
    """The position (a character of text) where a block of the program goes."""
    lines = _lines(text)
    if kind == 'orca':
        for k, line in enumerate(lines):
            if re.match(r'\s*\*\s*(xyz|xyzfile|int|gzmt|pdbfile)\b', line, re.I):
                return _offset(lines, k)
    elif kind == 'gaussian':
        return 0
    return len(text)


def keyword_place(text):
    """After the last line of keywords («!») of ORCA, or the start."""
    lines = _lines(text)
    last = max((k for k, line in enumerate(lines) if line.lstrip().startswith('!')), default=-1)
    return _offset(lines, last + 1)


def inserted(text, kind, block, keyword=''):
    """The text with the block (and the keyword it needs, when absent) at its place."""
    if keyword and kind == 'orca' and not re.search(r'^\s*!.*\b' + re.escape(keyword) + r'\b', text, re.M | re.I):
        at = keyword_place(text)
        text = text[:at] + f'! {keyword}\n' + text[at:]
    at = place(text, kind)
    before = text[:at]
    lead = '' if not before or before.endswith('\n') else '\n'
    return before + lead + block + '\n' + text[at:]

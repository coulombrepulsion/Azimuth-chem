"""The colours of the editor of input files: the language of a text guessed (guess_language), the highlighter of its
keywords, numbers and comments (Highlighter), the column of line numbers (_Numbers).

Split off azimuth/text_editor.py (0.222.30); text_editor still names them.
"""

import re
from PySide6.QtCore import QSize
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import QWidget


# the parts of an input of each program: the lines of the
# keywords, the blocks (and their end), the coordinates, the comments; numbers everywhere
_NUMBER = r'(?<![\w.])[-+]?(?:\d+\.?\d*|\.\d+)(?:[eEdD][-+]?\d+)?(?![\w.])'


LANGUAGES = {
    'orca': {'comment': '#', 'keyword': r'^\s*!.*$', 'block': r'^\s*%\w+|^\s*end\b', 'geometry': r'^\s*\*.*$'},
    'gaussian': {'comment': '!', 'keyword': r'^\s*#.*$', 'block': r'^\s*%\w+\s*=?.*$|^\s*--link1--',
                 'geometry': r'^\s*-?\d+\s+\d+\s*$'},
    'qe': {'comment': '!', 'keyword': r'^\s*(ATOMIC_SPECIES|ATOMIC_POSITIONS|K_POINTS|CELL_PARAMETERS|OCCUPATIONS|'
                                      r'CONSTRAINTS|ATOMIC_FORCES|HUBBARD|ADDITIONAL_K_POINTS)\b.*$',
           'block': r'^\s*&\w+|^\s*/\s*$', 'geometry': None},
    'cp2k': {'comment': '#', 'keyword': r'^\s*@\w+.*$', 'block': r'^\s*&\w+|^\s*&END\b.*$', 'geometry': None},
    'psi4': {'comment': '#', 'keyword': r'^\s*(set|energy|optimize|frequency|frequencies|properties|memory)\b.*$',
             'block': r'^\s*molecule\b.*\{|^\s*\}', 'geometry': None},
    'nwchem': {'comment': '#', 'keyword': r'^\s*(task|start|title|charge|memory|echo)\b.*$',
               'block': r'^\s*(geometry|basis|dft|scf|tddft|mp2|ccsd|driver|freq|cosmo)\b|^\s*end\b',
               'geometry': None},
    'gamess': {'comment': '!', 'keyword': None, 'block': r'^\s*\$\w+|\$end\b', 'geometry': None},
    'mopac': {'comment': '*', 'keyword': r'\A.*$', 'block': None, 'geometry': None},
    'xtb': {'comment': '#', 'keyword': None, 'block': r'^\s*\$\w+|^\s*\$end\b', 'geometry': None},
}


def guess_language(name='', text=''):
    """The language of a file by its name and its first lines (the editor of «Файлы на сервере»), or None."""
    name = (name or '').lower()
    head = (text or '')[:4000]
    if name.endswith(('.gjf', '.com')) or re.search(r'^\s*#[pnt]?\s', head, re.M) and '%chk' in head.lower():
        return 'gaussian'
    if re.search(r'^\s*&control\b', head, re.M | re.I):
        return 'qe'
    if re.search(r'^\s*&(global|force_eval)\b', head, re.M | re.I):
        return 'cp2k'
    if name.endswith('.inp') and re.search(r'^\s*!', head, re.M):
        return 'orca'
    if name.endswith('.nw'):
        return 'nwchem'
    if re.search(r'^\s*\$contrl\b', head, re.M | re.I):
        return 'gamess'
    if name.endswith(('.in', '.pwi')) and re.search(r'^\s*&', head, re.M):
        return 'qe'
    return None


class Highlighter(QSyntaxHighlighter):
    """The colours of an input (LANGUAGES): the keywords blue and bold, the blocks violet, the coordinates green, the
    numbers teal, the comments grey italic — lighter in the dark theme (the lightness of the base of the editor)."""

    def __init__(self, edit, language=None):
        super().__init__(edit.document())
        self.edit = edit
        self.language = None
        self.rules = []
        self.set_language(language)

    def _style(self, light, dark, bold=False, italic=False):
        base = self.edit.palette().base().color()
        style = QTextCharFormat()
        style.setForeground(QColor(dark if base.lightness() < 128 else light))
        if bold:
            style.setFontWeight(QFont.Weight.Bold)
        style.setFontItalic(italic)
        return style

    def set_language(self, language):
        from PySide6.QtCore import QRegularExpression

        self.language = language if language in LANGUAGES else None
        spec = LANGUAGES.get(self.language) or {}
        self.rules = []
        if self.language:
            self.rules.append((QRegularExpression(_NUMBER), self._style('#0e7c86', '#5fd0d8')))
            for key, light, dark, bold in (('geometry', '#2e7d32', '#7fd08a', True), ('block', '#7b3fb0', '#c79bf0', True),
                                           ('keyword', '#1f4f99', '#8ab4f8', True)):
                if spec.get(key):
                    self.rules.append((QRegularExpression(spec[key],
                                                          QRegularExpression.PatternOption.CaseInsensitiveOption),
                                       self._style(light, dark, bold)))
            sign = spec.get('comment')
            self.comment_style = self._style('#7a8494', '#8d97a8', italic=True)
            self.comment_sign = sign
        else:
            self.comment_sign = None
        self.rehighlight()

    def highlightBlock(self, text):
        if not self.language:
            return
        if self.language == 'mopac' and self.currentBlock().blockNumber() > 0:
            rules = self.rules[:1]  # MOPAC: the keywords are the first line only, then the title and the atoms
        else:
            rules = self.rules
        for expression, style in rules:
            found = expression.globalMatch(text)
            while found.hasNext():
                match = found.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), style)
        sign = self.comment_sign
        if sign:
            at = text.find(sign)
            if self.language == 'mopac':
                at = 0 if text.startswith('*') else -1
            if self.language == 'gaussian' and text.lstrip().startswith('#'):
                at = text.find('!')  # the route starts with #, a comment of Gaussian is «!»
            if at >= 0:
                self.setFormat(at, len(text) - at, self.comment_style)


class _Numbers(QWidget):
    def __init__(self, edit):
        super().__init__(edit)
        self.edit = edit

    def sizeHint(self):
        return QSize(self.edit.numbers_width(), 0)

    def paintEvent(self, event):
        self.edit.paint_numbers(self, event)

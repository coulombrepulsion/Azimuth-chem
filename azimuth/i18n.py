"""Languages of Compass, Sextant and Spectrum.

The source language of the code is Russian: every user-visible Russian literal goes through
tr(text). Translations live in azimuth/locale/<lang>.json as {russian: translation}; a key with
"{}" is a pattern for texts built at run time (f-strings: tr(f'Атомов: {n}') finds 'Атомов: {}').

Switching the language at run time: set_language(code) and retranslate(root) walk the widgets and
re-translate every text that is a known source (or a known translation in any language), so
static texts built once in Russian follow the language; dynamic texts are produced by tr() in the
current language when they are made. Combo boxes whose texts are data keys (tasks, fragments,
examples) keep the Russian key in item data: combo_key(combo) / set_combo_key(combo, key).
"""

import json
import re
from pathlib import Path

LANGUAGES = ('ru', 'en', 'zh')
LANG = 'ru'
KEY_ROLE = 0x0100 + 77  # Qt.UserRole + 77: the Russian key of a combo item
TEXT_ROLE = 0x0100 + 79  # the Russian text of an item whose key is not its text (a chain in «Задача»)
_DIR = Path(__file__).with_name('locale')
_TABLES = {}
_PATTERNS = {}
_REVERSE = {}


class _Pattern:
    """A text with «{}» of a table; its regular expression is made only when a text has its fixed start and
    end. _load compiled all of them at once — about 1800 regular expressions, a quarter of a second at every start
    of the program, though most are never used."""

    __slots__ = ('template', 'other', 'head', 'tail', '_rx')

    def __init__(self, template, other):
        self.template, self.other = template, other  # the text matched and the text it gives
        parts = template.split('{}')
        self.head, self.tail = parts[0], parts[-1]
        self._rx = None

    def match(self, text):
        if len(text) < len(self.head) + len(self.tail) or not text.startswith(self.head) or not text.endswith(self.tail):
            return None
        if self._rx is None:
            self._rx = re.compile('^' + '(.*?)'.join(re.escape(part) for part in self.template.split('{}')) + '$', re.S)
        return self._rx.match(text)


def _load():
    if _TABLES:
        return
    for code in LANGUAGES[1:]:
        try:
            table = json.loads((_DIR / f'{code}.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            table = {}
        _TABLES[code] = table
        pairs = [(src, dst) for src, dst in table.items() if '{}' in src and src.count('{}') == dst.count('{}')]
        # the most specific pattern first
        _PATTERNS[code] = sorted((_Pattern(src, dst) for src, dst in pairs), key=lambda p: -len(p.template))
        _REVERSE[code] = {dst: src for src, dst in table.items()}
        _REVERSE[code + '#p'] = sorted((_Pattern(dst, src) for src, dst in pairs), key=lambda p: -len(p.template))


def set_language(code):
    global LANG
    if code not in LANGUAGES:
        raise ValueError(f'Unknown language {code!r}')
    _load()
    LANG = code


def tr(text, lang=None):
    """The text in the current (or given) language; unknown texts are returned unchanged."""
    lang = lang or LANG
    if lang == 'ru' or not isinstance(text, str) or not text:
        return text
    _load()
    table = _TABLES.get(lang, {})
    if text in table:
        return table[text]
    for pattern in _PATTERNS.get(lang, ()):
        m = pattern.match(text)
        if m:
            return _fill(pattern.other, m.groups())
    return text


def _fill(pattern, groups):
    parts = pattern.split('{}')
    out = parts[0]
    for g, p in zip(groups, parts[1:]):
        out += g + p
    return out


def to_source(text):
    """The Russian source of a text shown in any language (itself if it is not a translation)."""
    if not isinstance(text, str) or not text:
        return text
    _load()
    for code in LANGUAGES[1:]:
        if text in _REVERSE[code]:
            return _REVERSE[code][text]
    if any(text in t for t in _TABLES.values()):
        return text
    for code in LANGUAGES[1:]:
        for pattern in _REVERSE[code + '#p']:
            m = pattern.match(text)
            if m:
                return _fill(pattern.other, m.groups())
    return text


def _sources(text):
    """[Russian source] of the parts of text: the whole when it is a known text, else («Настройки задачи ·
    Оптимизация + частоты») its parts joined by « · », the longest known run first (otherwise «Снимок · PNG, …» would
    come back from Chinese as «Снимки · <Chinese>»: the first part alone is a known word)."""
    source = to_source(text)
    if source != text or not isinstance(text, str) or ' · ' not in text or tr(source) != source:
        return [source]
    parts, out, k = text.split(' · '), [], 0
    while k < len(parts):
        for end in range(len(parts), k, -1):
            piece = ' · '.join(parts[k:end])
            known = to_source(piece)
            if known != piece or end == k + 1:
                out.append(known)
                k = end
                break
    return out


def retranslate_text(text):
    """The text in the current language (its parts, see _sources)."""
    return ' · '.join(tr(part) for part in _sources(text))


def _retranslated(widget, key, text):
    """The text in the current
    language from its Russian source kept on the widget (property key) the last time — the way back does not depend
    on reading a translation; a text the program changed since is read anew."""
    kept = widget.property(key)
    if isinstance(kept, (list, tuple)) and len(kept) == 2 and kept[1] == text:
        sources = list(kept[0])
    else:
        sources = _sources(text)
    new = ' · '.join(tr(part) for part in sources)
    widget.setProperty(key, (sources, new))
    return new


def combo_key(combo):
    """The data key of the current item (the Russian text it was created with)."""
    i = combo.currentIndex()
    key = combo.itemData(i, KEY_ROLE) if i >= 0 else None
    return key if isinstance(key, str) else to_source(combo.currentText())


def set_combo_key(combo, key):
    for i in range(combo.count()):
        if combo.itemData(i, KEY_ROLE) == key or to_source(combo.itemText(i)) == key:
            combo.setCurrentIndex(i)
            return True
    return False


def retranslate(root):
    """Re-translate the static texts of root and its children into the current language."""
    from PySide6.QtWidgets import (
        QAbstractButton,
        QAbstractSpinBox,
        QComboBox,
        QGroupBox,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMenu,
        QPlainTextEdit,
        QTabBar,
        QTabWidget,
        QTableWidget,
        QWidget,
    )
    from PySide6.QtGui import QAction

    widgets = [root] + root.findChildren(QWidget)
    for w in widgets:
        tip = w.toolTip()
        if tip:
            new = _retranslated(w, 'trTip', tip)
            if new != tip:
                w.setToolTip(new)
        if isinstance(w, QLabel):
            t = w.text()
            if t:
                new = retranslate_text(t)
                if new != t:
                    w.setText(new)
        elif isinstance(w, QAbstractButton):
            t = w.text()
            if t:
                new = _retranslated(w, 'trText', t)
                if new != t:
                    w.setText(new)
        elif isinstance(w, QGroupBox):
            t = w.title()
            if t:
                w.setTitle(retranslate_text(t))
        elif isinstance(w, QComboBox):
            for i in range(w.count()):
                t = w.itemText(i)
                if w.itemData(i, KEY_ROLE) is None:
                    w.setItemData(i, to_source(t), KEY_ROLE)
                new = tr(w.itemData(i, TEXT_ROLE) or w.itemData(i, KEY_ROLE))
                if new != t:
                    w.setItemText(i, new)
        elif isinstance(w, QTabWidget):
            for i in range(w.count()):
                t = w.tabText(i)
                new = retranslate_text(t)
                if new != t:
                    w.setTabText(i, new)
                tt = w.tabToolTip(i)
                if tt:
                    w.setTabToolTip(i, retranslate_text(tt))
        elif isinstance(w, QTabBar):  # the bars of the project tabs («Новый проект» stayed Russian)
            for i in range(w.count()):
                t = w.tabText(i)
                new = retranslate_text(t)
                if new != t:
                    w.setTabText(i, new)
                tt = w.tabToolTip(i)
                if tt:
                    w.setTabToolTip(i, retranslate_text(tt))
        elif isinstance(w, QAbstractSpinBox) and hasattr(w, 'suffix'):  # « проц.», « МБ», « циклов»
            for get, put in ((w.prefix, w.setPrefix), (w.suffix, w.setSuffix)):
                t = get()
                if t:
                    new = retranslate_text(t)
                    if new != t:
                        put(new)
        elif isinstance(w, QTableWidget):
            for get, n in ((w.horizontalHeaderItem, w.columnCount()), (w.verticalHeaderItem, w.rowCount())):
                for i in range(n):
                    item = get(i)
                    if item is not None and item.text():
                        item.setText(retranslate_text(item.text()))
        if isinstance(w, (QLineEdit, QPlainTextEdit)):
            ph = w.placeholderText()
            if ph:
                w.setPlaceholderText(retranslate_text(ph))
        if isinstance(w, QMenu):
            t = w.title()
            if t:
                w.setTitle(retranslate_text(t))
        if isinstance(w, QMainWindow) or w.isWindow():
            t = w.windowTitle()
            if t:
                w.setWindowTitle(retranslate_text(t))
    for a in root.findChildren(QAction):
        t = a.text()
        if t:
            a.setText(retranslate_text(t))
        tip = a.toolTip()
        if tip:
            a.setToolTip(retranslate_text(tip))
        st = a.statusTip()
        if st:
            a.setStatusTip(retranslate_text(st))

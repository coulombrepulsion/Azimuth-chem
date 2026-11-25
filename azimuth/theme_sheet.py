"""One style sheet for both themes; the theme is switched by a property of the windows.

§1 PURPOSE
    Switching the theme by QApplication.setStyleSheet takes every widget of the program (≈1500, the hidden sections
    and windows too) through a new style: ≈1.1–1.2 s for the window of the sections alone, whatever the text. Taking
    all the widgets through polish again costs ≈0.16 s, so both themes live in one sheet and a property switches them.
§2 ALGORITHM
    both(light, dark): the light sheet as it is, then every rule of the dark sheet with each selector S written twice —
    `*[azimuthDark="true"] S` (a widget inside a dark window) and, for a selector of one compound, S with the attribute
    put before its pseudo-states and subcontrols (the window itself, a menu). A dark rule has one attribute more than
    its light twin, so in a dark window it wins whatever the light rules are, and the dark rules among themselves
    keep the order and the weights of the dark sheet: a dark window looks as under the dark sheet alone (checked
    pixel by pixel on the pages of Compass, Sextant and Spectrum).
    mark(app, dark): the property on every top-level window whose value differs, off on every widget that is not a
    window (any more), then unpolish + polish of the widgets of those windows; the bars of tabs among them are then
    told that the style changed (QEvent.StyleChange) — they keep the sizes of their tabs otherwise.
    A window shown later (a dialog without a parent) gets it from watch(app): QGuiApplication.focusWindowChanged — a
    signal, not an event filter of the application (a Python filter of the whole application crashed Qt).
    Widgets made later inside a marked window match by the descendant form at their first polish.
§3 APPLICATIONS
    azimuth/app.py Studio._apply_theme.
§4 SPECIFICATION
    PROPERTY; both(light, dark) -> str; mark(app, dark) -> number of windows changed; watch(app) (once).
§7 TESTS
    tests/core/test_theme_sheet.py; the GUI tests of the theme.
§8' ROBUSTNESS / ERRORS
    Rules are split at '}' — the sheets of the program have no braces inside values or comments.
"""

PROPERTY = 'azimuthDark'
_STATE = {'dark': None, 'watched': False}


def rules(text):
    out = []
    for chunk in text.split('}'):
        if '{' not in chunk:
            continue
        selectors, body = chunk.split('{', 1)
        selectors = selectors.strip()
        if selectors:
            out.append((selectors, body.strip()))
    return out


def self_form(selector):
    """The attribute put into a selector of one compound before its pseudo-states and subcontrols."""
    depth = 0
    for i, ch in enumerate(selector):
        if ch == '[':
            depth += 1
        elif ch == ']':
            depth -= 1
        elif ch == ':' and depth == 0:
            return selector[:i] + f'[{PROPERTY}="true"]' + selector[i:]
    return selector + f'[{PROPERTY}="true"]'


def both(light, dark):
    parts = [light]
    for selectors, body in rules(dark):
        forms = []
        for s in (x.strip() for x in selectors.split(',')):
            forms.append(f'*[{PROPERTY}="true"] {s}')
            if ' ' not in s and '>' not in s:
                forms.append(self_form(s))
        parts.append(', '.join(forms) + ' {' + body + '}')
    return '\n'.join(parts) + '\n'


def _repolish(widgets):
    from PySide6.QtCore import QCoreApplication, QEvent
    from PySide6.QtWidgets import QTabBar, QWidget

    style = None
    bars = []
    for w in widgets:
        try:
            style = style or w.style()
            style.unpolish(w)
            style.polish(w)
            QWidget.update(w)  # item views overload update(index)
            if isinstance(w, QTabBar):
                bars.append(w)
        except RuntimeError:  # deleted meanwhile
            pass
    # a bar of tabs keeps the sizes of its tabs and does not count them again after polish — it stayed narrower than its
    # tabs, the last name cut and the scroll buttons shown. QApplication.setStyleSheet sends this event to every widget;
    # here only to the bars.
    for bar in bars:
        try:
            QCoreApplication.sendEvent(bar, QEvent(QEvent.Type.StyleChange))
            bar.updateGeometry()
        except RuntimeError:
            pass


def mark(app, dark):
    """The property on every window (top-level widget) whose value differs, and off on every widget that is no longer a
    window: the window of the sections is made on its own and then put into the hub (HubWindow) — marked dark at its
    start, it kept the mark inside the hub, and its pages stayed dark in the light theme."""
    from PySide6.QtWidgets import QWidget

    _STATE['dark'] = bool(dark)
    changed = []
    for widget in app.allWidgets():
        try:
            want = bool(dark) if widget.isWindow() else False
            if bool(widget.property(PROPERTY)) != want:
                widget.setProperty(PROPERTY, want)
                changed.append(widget.window())
        except RuntimeError:
            pass
    if changed:
        tops = list(dict.fromkeys(changed))
        widgets = []
        for top in tops:
            widgets.append(top)
            widgets.extend(top.findChildren(QWidget))
        _repolish(widgets)
    return len(changed)


def watch(app):
    """Windows shown after a switch (a dialog without a parent) get the property when they take the focus."""
    if _STATE['watched']:
        return
    _STATE['watched'] = True

    def follow(*_):
        if _STATE['dark'] is not None:
            from PySide6.QtWidgets import QApplication

            instance = QApplication.instance()
            if instance is not None:
                mark(instance, _STATE['dark'])

    app.focusWindowChanged.connect(follow)

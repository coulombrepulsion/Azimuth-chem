"""Turn a mixin of the window into a tool with a declared port (the second version — what was done
by hand in 0.108.24 is done here; the roadmap of 2026-11-09, stage 5).

Usage: python tools/mixin_to_tool.py <version> <module path> <Mixin> <Tool> <attribute of the window> [...more
quadruples]

For each mixin:
  * its methods stay methods of the tool; an attribute it sets that nothing else reads (by `.name` or by the string
    'name') is the state of the tool; every other name of the window goes through the port (self.w.<name>, a method
    moved to another tool of the same run — self.w.<attribute>.<name>); the names are written into the tool as PORT;
  * getattr / hasattr / setattr of the window by a string — getattr(self.w, …), self.w.has(…);
  * `self` as an argument (the Qt parent, the owner of a dialog) — self.w.widget.
Then the callers, by the syntax tree:
  * in a class of the window (Studio and its mixins, found from the bases) `self.<method>` →
  `self.<attribute>.<method>`;
  * in a tool with a PORT `self.w.<method>` → `self.w.<attribute>.<method>`, the attribute added to its PORT;
  * anywhere, the receivers that are the window by name (window, studio, owner, self.window, self.studio,
    self.owner, w, win) `.<method>` → `.<attribute>.<method>`, and hasattr(<receiver>, '<method>') →
    hasattr(<receiver>, '<attribute>');
  * a moved name that is also a method of another class is left alone for the receivers by name, and printed: those
    places are to be looked at by hand.
Also getattr / setattr(<receiver>, '<method>' (monkeypatch of the tests); not found by it — a getattr by a
name in a variable (history_dialog._do) and self.w.has('<method>') of a tool converted earlier: search for them.
The diff is to be read — this is a help, not a proof; the GUI tests run it.
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WINDOW_ROOTS = (('azimuth/app.py', 'Studio'),)
RECEIVERS = ('window', 'studio', 'owner', 'self.window', 'self.studio', 'self.owner', 'w', 'win', 'hub.studio',
             'self.hub.studio', 'another')


_FILES = None


def python_files():
    global _FILES
    if _FILES is None:
        skip = {'__pycache__', '.git', '.venv', 'venv', 'build', 'dist', 'site-packages', '.tools'}
        _FILES = [p for p in sorted(ROOT.rglob('*.py')) if not skip & set(p.relative_to(ROOT).parts)]
    return _FILES


_TEXT = {}


def text_of(p):
    if p not in _TEXT:
        _TEXT[p] = p.read_text(encoding='utf-8', errors='ignore')
    return _TEXT[p]


def class_index():
    """{class name: (path, ClassDef)} of the program (the first of a name)."""
    found = {}
    for p in python_files():
        try:
            tree = ast.parse(p.read_text(encoding='utf-8'))
        except (SyntaxError, UnicodeDecodeError):
            continue
        for n in tree.body:
            if isinstance(n, ast.ClassDef):
                found.setdefault(n.name, (p, n))
    return found


def window_classes(index):
    names, todo = set(), [name for _, name in WINDOW_ROOTS]
    while todo:
        name = todo.pop()
        if name in names or name not in index:
            continue
        names.add(name)
        todo.extend(b.id for b in index[name][1].bases if isinstance(b, ast.Name))
    return names


def methods_of_file(p):
    try:
        tree = ast.parse(p.read_text(encoding='utf-8', errors='ignore'))
    except SyntaxError:
        return set()
    return {n.name for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def methods_of(cls):
    return {n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}


def read_elsewhere(name, path):
    pattern = re.compile(r'\.' + re.escape(name) + r'\b|[\'"]' + re.escape(name) + r'[\'"]')
    for p in python_files():
        if p.resolve() == path.resolve():
            continue
        if pattern.search(text_of(p)):
            return True
    return False


def port_names(body):
    """The names of the window a tool body uses: self.w.<name>, getattr / setattr(self.w, '<name>'), self.w.has('<name>')."""
    return (set(re.findall(r'\bself\.w\.(\w+)', body)) | set(re.findall(r"\b(?:getattr|setattr)\(self\.w, '(\w+)'", body))
            | set(re.findall(r"self\.w\.has\('(\w+)'\)", body))) - {'widget', 'has'}


def convert_body(body, methods, own, constants, moved, version, mixin, tool):
    used = set(re.findall(r'\bself\.(\w+)', body))
    for name in sorted(used - methods - own - constants - {'w'}):
        target = f'{moved[name]}.{name}' if name in moved else name
        body = re.sub(r'\bself\.' + re.escape(name) + r'\b', 'self.w.' + target, body)

    def by_string(m):
        fn, name = m.group(1), m.group(2)
        if name in own or name in methods or name in constants:
            return m.group(0)
        if fn == 'hasattr':
            return f"self.w.has('{name}')"
        return f"{fn}(self.w, '{name}'"

    body = re.sub(r"\b(getattr|setattr)\(self, '(\w+)'", by_string, body)
    body = re.sub(r"\b(hasattr)\(self, '(\w+)'\)", by_string, body)
    lines = []
    for line in body.splitlines(keepends=True):
        if not line.lstrip().startswith(('def ', 'async def ')):
            line = re.sub(r'(?<![\w.])(?<!getattr\()(?<!hasattr\()(?<!setattr\()self(?=\s*[,)])', 'self.w.widget', line)
        lines.append(line)
    body = ''.join(lines)
    names = sorted(port_names(body))
    first = body.index('\n') + 1
    rest = body[first:]
    if ast.get_docstring(ast.parse(body).body[0]):
        rest = re.sub(r'^\s*(?:"""|\'\'\')[\s\S]*?(?:"""|\'\'\')\n', '', rest, count=1)
    header = (f'class {tool}:\n    """{version}: was the mixin {mixin} of the window; a part of its own — it reaches the '
              'window only through\n    the names of PORT (azimuth/window_port.WindowPort)."""\n\n    PORT = (\n'
              + ''.join(f'        {n!r},\n' for n in names) + '    )\n\n'
              '    def __init__(self, window):\n'
              '        from azimuth.window_port import WindowPort\n\n'
              '        self.w = WindowPort(window, self.PORT)\n\n')
    return header + rest, names


def rewrite_callers(moved, windows, tools_files, colliding):
    changed = []
    for p in python_files():
        if p.name == 'mixin_to_tool.py':
            continue
        text = p.read_text(encoding='utf-8', errors='ignore')
        present = {m: a for m, a in moved.items() if m in text}
        if not present:
            continue
        try:
            tree = ast.parse(text)
        except SyntaxError:
            continue
        lines = text.splitlines(keepends=True)
        edits = []  # (line index, old, new) applied per line of a class
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            mine = (p.resolve(), cls.name) in tools_files
            port = any(isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == 'PORT' for t in n.targets)
                       for n in cls.body)
            edits.append((cls.lineno - 1, cls.end_lineno, cls.name in windows, port and not mine, mine))
        new_lines = list(lines)
        for start, end, is_window, is_tool, mine in edits:
            for i in range(start, end):
                line = new_lines[i]
                for method, attr in present.items():
                    if method not in line:
                        continue
                    q = re.escape(method)
                    if is_window:
                        line = re.sub(r'(?<![\w.])self\.' + q + r'\b', f'self.{attr}.{method}', line)
                        line = re.sub(r"(?<![\w.])getattr\(self, '" + q + "'", f"getattr(self.{attr}, '{method}'", line)
                        line = re.sub(r"(?<![\w.])hasattr\(self, '" + q + r"'\)", f"hasattr(self, '{attr}')", line)
                    if is_tool:
                        line = re.sub(r'\bself\.w\.' + q + r'\b', f'self.w.{attr}.{method}', line)
                    if is_tool or mine:
                        line = re.sub(r"\bself\.w\.has\('" + q + r"'\)", f"self.w.has('{attr}')", line)
                        line = re.sub(r"\bgetattr\(self\.w, '" + q + "'", f"getattr(self.w.{attr}, '{method}'", line)
                new_lines[i] = line
        text2 = ''.join(new_lines)
        for method, attr in present.items():
            if method in colliding:
                continue
            for r in RECEIVERS:
                text2 = re.sub(r'(?<![\w.])' + re.escape(r) + r'\.' + re.escape(method) + r'\b', f'{r}.{attr}.{method}',
                               text2)
                text2 = re.sub(r'hasattr\(' + re.escape(r) + r", '" + re.escape(method) + r"'\)",
                               f"hasattr({r}, '{attr}')", text2)
                # getattr(window, 'name', …) and monkeypatch.setattr(window, 'name', …) of the tests
                text2 = re.sub(r'(?<![\w.])(getattr|setattr)\(' + re.escape(r) + r", '" + re.escape(method) + "'",
                               lambda m, r=r, a=attr, n=method: f"{m.group(1)}({r}.{a}, '{n}'", text2)
            text2 = re.sub(r"(?<![\w.])hasattr\(self, '" + re.escape(method) + r"'\)", f"hasattr(self, '{attr}')", text2) \
                if any(e[2] for e in edits) else text2
        if text2 != text:
            p.write_text(text2, encoding='utf-8')
            changed.append(p)
    # every tool touched (and the new ones) declares exactly the names it uses
    for p in sorted(set(changed) | {path for path, _ in tools_files}):
        text = p.read_text(encoding='utf-8')
        tree = ast.parse(text)
        for cls in [n for n in tree.body if isinstance(n, ast.ClassDef)]:
            seg = ''.join(text.splitlines(keepends=True)[cls.lineno - 1:cls.end_lineno])
            m = re.search(r'    PORT = \(\n((?:        .*\n)*?)    \)\n', seg)
            if not m:
                continue
            names = set(re.findall(r"'(\w+)'", m.group(1)))
            used = port_names(seg)
            if used != names:
                names = sorted(used)
                seg2 = seg.replace(m.group(0), '    PORT = (\n' + ''.join(f'        {n!r},\n' for n in names) + '    )\n')
                text = text.replace(seg, seg2)
        p.write_text(text, encoding='utf-8')
    return changed


def main(args):
    version, args = args[0], args[1:]
    jobs = [args[i:i + 4] for i in range(0, len(args), 4)]
    index = class_index()
    windows = window_classes(index)
    moved, plans = {}, []
    for rel, mixin, tool, attr in jobs:
        path = ROOT / rel
        tree = ast.parse(path.read_text(encoding='utf-8'))
        (cls,) = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == mixin]
        methods = methods_of(cls)
        constants = {t.id for n in cls.body if isinstance(n, ast.Assign) for t in n.targets if isinstance(t, ast.Name)}
        assigned = {n.attr for n in ast.walk(cls) if isinstance(n, ast.Attribute) and isinstance(n.value, ast.Name)
                    and n.value.id == 'self' and isinstance(n.ctx, ast.Store)}
        on_window = {t.id for w in windows if w != mixin for n in index[w][1].body if isinstance(n, ast.Assign)
                     for t in n.targets if isinstance(t, ast.Name)} | {m for w in windows if w != mixin
                                                                       for m in methods_of(index[w][1])}
        # a field of the window class (a _PerPlace of Sextant, a property) is the window's, never the tool's
        own = {a for a in assigned - methods - on_window if not read_elsewhere(a, path)}
        plans.append((path, mixin, tool, attr, methods, constants, own))
        for m in methods:
            if not m.startswith('__'):
                moved[m] = attr
    others = {}
    for name, (p, c) in index.items():
        if name in windows or name in {plan[1] for plan in plans}:
            continue
        for m in methods_of(c):
            if m in moved:
                others.setdefault(m, []).append(f'{p.relative_to(ROOT)}:{name}')
    for path, mixin, tool, attr, methods, constants, own in plans:
        text = path.read_text(encoding='utf-8')
        tree = ast.parse(text)
        (cls,) = [n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == mixin]
        lines = text.splitlines(keepends=True)
        body = ''.join(lines[cls.lineno - 1:cls.end_lineno])
        new, names = convert_body(body, methods, own, constants, moved, version, mixin, tool)
        lines[cls.lineno - 1:cls.end_lineno] = [new]
        path.write_text(''.join(lines), encoding='utf-8')
        print(f'{path.relative_to(ROOT)}: {mixin} -> {tool}; own state {sorted(own)}; port {len(names)} names')
        windows.discard(mixin)
    for path, mixin, tool, *_ in plans:
        for p in python_files():
            text = p.read_text(encoding='utf-8', errors='ignore')
            if re.search(r'\b' + mixin + r'\.', text):
                p.write_text(re.sub(r'\b' + mixin + r'\.', tool + '.', text), encoding='utf-8')
                print(f'LOOK: {mixin}. → {tool}. in {p.relative_to(ROOT)} (imported there?)')
    for p in python_files():
        for i, line in enumerate(p.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
            for found in re.finditer(r'\b(\w+)\.(\w+)\(', line):
                if found.group(1) in windows | {'CompassWorkspace', 'Studio'} and found.group(2) in moved:
                    print(f'LOOK: a moved method on the class of the window — {p.relative_to(ROOT)}:{i}: {line.strip()[:90]}')
    tools_files = {(path.resolve(), tool) for path, _, tool, *_ in plans}
    changed = rewrite_callers(moved, windows, tools_files, set(others))
    for p in changed:
        print('callers:', p.relative_to(ROOT))
    for m, where in sorted(others.items()):
        print(f'LOOK: {m} is also a method of {", ".join(where)} — the receivers by name were left alone:')
        pattern = re.compile(r'([\w.()\[\]]*)\.' + re.escape(m) + r'\b|[\'"]' + re.escape(m) + r'[\'"]')
        for p in python_files():
            for i, line in enumerate(p.read_text(encoding='utf-8', errors='ignore').splitlines(), 1):
                for found in pattern.finditer(line):
                    receiver = found.group(1) or ''
                    if receiver.endswith('_tool') or (receiver == 'self' and m in methods_of_file(p)):
                        continue
                    print(f'    {p.relative_to(ROOT)}:{i}: {line.strip()[:100]}')
                    break
    for name in sorted({c for *_, constants, _ in plans for c in constants}):
        print(f'LOOK: the constant {name} of a mixin — read on the window elsewhere?')


if __name__ == '__main__':
    main(sys.argv[1:])

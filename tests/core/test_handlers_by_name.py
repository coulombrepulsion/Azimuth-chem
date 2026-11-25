"""A method of a part of the window is never looked up on the window by its name.
0.108.28 moved the queues and the running of Sextant into parts (azimuth/window_port.py); three buttons kept
getattr(owner, 'batch_qtaim', lambda: None) — the window had no such method any more, the stand-in did nothing and no
test failed. Here every getattr / hasattr / setattr with a constant name and every port.has('name') in the program is
checked: a name that is a method of a part (a class with a PORT) must be looked up on that part
(<window>.<part>, getattr(owner, '<part>') or the part itself), never on the window. The oracle is the syntax tree of
the program, not the list of moved names: a part added later is checked as well."""

import ast
from pathlib import Path

from tests.program_files import moved_methods

ROOT = Path(__file__).resolve().parents[2]
SKIP = ('tests', 'tools', 'atlas_v2', '__pycache__')


PROGRAM = ('azimuth', 'modules', 'hub')  # only the code of the program — never .venv, build or dist


def program():
    paths = [p for folder in PROGRAM for p in sorted((ROOT / folder).rglob('*.py'))] + sorted(ROOT.glob('*.py'))
    for path in paths:
        if any(part in SKIP for part in path.relative_to(ROOT).parts):
            continue
        yield path, ast.parse(path.read_text(encoding='utf-8'))


def is_part(cls):
    return any(isinstance(n, ast.Assign) and any(getattr(t, 'id', '') == 'PORT' for t in n.targets) for n in cls.body)


def methods(cls):
    """The methods of the class — its own defs and those it takes from another file (`name = _part.name`, 0.222.29)."""
    own = {n.name for n in cls.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    taken = {t.id for n in cls.body if isinstance(n, ast.Assign) and isinstance(n.value, ast.Attribute)
             and isinstance(n.value.value, ast.Name) for t in n.targets if isinstance(t, ast.Name)}
    return {name for name in own | taken if not name.startswith('__')}


def window_classes():
    """Studio and the classes it is made of (its bases, followed): `self` there is the window."""
    index = {}
    for _, tree in program():
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            index.setdefault(cls.name, cls)
    found, todo = set(), ['Studio']
    while todo:
        name = todo.pop()
        if name in found or name not in index:
            continue
        found.add(name)
        todo.extend(b.id for b in index[name].bases if isinstance(b, ast.Name))
    return found


def names_of_parts():
    of_parts, elsewhere = set(), set()
    for _, tree in program():
        for cls in (n for n in tree.body if isinstance(n, ast.ClassDef)):
            (of_parts if is_part(cls) else elsewhere).update(methods(cls))
    return of_parts - elsewhere  # a name also of another class may be that class's own


def on_a_part(receiver):
    """The receiver is a part: <…>.<x>_tool / _tools, or getattr(<…>, '<x>_tool', …)."""
    if isinstance(receiver, ast.Attribute):
        return receiver.attr.endswith(('_tool', '_tools'))
    if isinstance(receiver, ast.Call) and getattr(receiver.func, 'id', '') == 'getattr' and len(receiver.args) >= 2:
        name = receiver.args[1]
        return isinstance(name, ast.Constant) and str(name.value).endswith(('_tool', '_tools'))
    return False


def test_no_method_of_a_part_is_looked_up_on_the_window():
    names = names_of_parts()
    windows = window_classes()
    assert len(names) > 300 and {'Studio', 'CompassWorkspace', 'SextantWorkspace'} <= windows  # found
    wrong = []
    for path, tree in program():
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            own = is_part(cls) or cls.name not in windows  # `self` of a part or of a dialog is not the window
            for node in [n for body in [cls, *moved_methods(tree, cls)] for n in ast.walk(body)]:
                if not isinstance(node, ast.Call):
                    continue
                func = node.func
                if getattr(func, 'id', '') in ('getattr', 'hasattr', 'setattr') and len(node.args) >= 2:
                    receiver, name = node.args[0], node.args[1]
                elif isinstance(func, ast.Attribute) and func.attr == 'has' and node.args:
                    receiver, name = func.value, node.args[0]  # port.has('name') asks the window
                    if not (isinstance(receiver, ast.Attribute) and receiver.attr == 'w'):
                        continue
                else:
                    continue
                if not isinstance(name, ast.Constant) or name.value not in names:
                    continue
                if on_a_part(receiver) or (own and isinstance(receiver, ast.Name) and receiver.id == 'self'):
                    continue
                wrong.append(f'{path.relative_to(ROOT)}:{node.lineno}: {ast.unparse(node)[:90]}')
    assert not wrong, 'a method of a part looked up on the window:\n' + '\n'.join(wrong)


def test_the_check_finds_the_mistake_of_0_108_28():
    # the oracle of the check itself: the line of 0.108.28 is found
    tree = ast.parse("class W:\n    def f(self, owner):\n        return getattr(owner, 'batch_qtaim', lambda: None)\n")
    call = next(n for n in ast.walk(tree) if isinstance(n, ast.Call))
    assert call.args[1].value in names_of_parts() and not on_a_part(call.args[0])
    tree = ast.parse("getattr(owner.batch_tool, 'batch_qtaim', None)")
    assert on_a_part(next(n for n in ast.walk(tree) if isinstance(n, ast.Call)).args[0])

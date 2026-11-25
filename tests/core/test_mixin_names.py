"""No two parts of the window define the same method by chance.

Studio (azimuth/app.py) is CompassWorkspace + SextantWorkspace + SpectrumWorkspace, each made of mixins; a method
defined in two of them silently hides one (a window that does not start, a menu item that opens another window).
The method names of every class of the window are read from the
code (ast); a name in two classes fails, except the overrides made on purpose (ALLOWED)."""

import ast
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).parents[2]


def classes():
    found = {}
    for path in list((ROOT / 'modules').rglob('*.py')) + list((ROOT / 'azimuth').glob('*.py')):
        if 'atlas_v2' in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                found.setdefault(node.name, (path, node))
    return found


def window_classes():
    found, order, seen = classes(), [], set()

    def walk(name):
        if name in seen or name not in found:
            return
        seen.add(name)
        order.append(name)
        for base in found[name][1].bases:
            if isinstance(base, ast.Name):
                walk(base.id)

    walk('Studio')
    return found, order


def test_no_method_hides_another():
    found, order = window_classes()
    owners = defaultdict(list)
    for name in order:
        methods = {item.name for item in found[name][1].body
                   if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and not item.name.startswith('__')}
        for method in methods:  # a property and its setter are one
            owners[method].append(name)
    twice = {m: o for m, o in owners.items() if len(o) > 1}
    assert len(order) > 5  # the mixins were found (fewer — the parts of their own are not mixins)
    new = {m: o for m, o in twice.items() if m not in ALLOWED}
    assert not new, new


ALLOWED = set()

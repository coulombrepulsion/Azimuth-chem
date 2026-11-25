"""A chain of calculations.
§1 PURPOSE
    The calculations made one after another on one molecule by hand — an optimization with frequencies, then the UV-Vis
    spectrum, the NMR or the energy with a larger basis at the geometry it gave — started by one command and run as a
    queue of Sextant (modules/sextant/batch.py, purpose 'chain'): each step on the geometry of the step before it.
§2 RULES
    1. PRESETS: (title, [(task, overrides of the calculation)]); the first step is an optimization with frequencies (a
       minimum confirmed before the properties at it). The settings of Sextant (method, basis, solvent, charge…) are
       those of every step but what a step overrides; a step of a task the program has not (inputs.tasks_for) makes the
       preset unavailable for it (available()).
    2. prepare(queue, item): a step after the first takes the final geometry of the step before it; the step before
       it not done — ValueError (the step is not calculated, the queue goes on to say the same of the rest).
    3. larger_basis(basis): def2-SVP → def2-TZVP → def2-QZVP, 6-31G(d) → 6-311+G(2d,p), cc-pVXZ → cc-pV(X+1)Z,
       aug-cc-pVXZ the same; anything else → def2-TZVP.
§4 SPECIFICATION
    PRESETS = {key: (title, steps)}; available(key, kind) -> bool; steps(key, calc) -> [(name, task, overrides)];
    items(key, molecule, calc, custom=None) -> [BatchItem] (custom: the method and basis of every step); prepare(queue,
    item) -> bool (changed); larger_basis(basis) -> str.
§7 TESTS
    tests/sextant/test_chain.py."""

import re

from azimuth.i18n import tr

OPT_FREQ = 'Оптимизация + частоты'
PRESETS = {
    'uv': ('Оптимизация + частоты → УФ-спектр (TD-DFT)', ((OPT_FREQ, {}), ('Спектр UV-Vis (TD-DFT)', {}))),
    'nmr': ('Оптимизация + частоты → ЯМР', ((OPT_FREQ, {}), ('ЯМР (экранирование)', {}))),
    'big': ('Оптимизация + частоты → энергия в большем базисе', ((OPT_FREQ, {}), ('Энергия', {'basis': '+'}))),
    'uv_nmr': ('Оптимизация + частоты → УФ-спектр → ЯМР',
               ((OPT_FREQ, {}), ('Спектр UV-Vis (TD-DFT)', {}), ('ЯМР (экранирование)', {}))),
}


def larger_basis(basis):
    text = (basis or '').strip()
    low = text.lower()
    if low in ('def2-svp', 'def2-sv(p)'):
        return 'def2-TZVP'
    if low.startswith('def2-tzvp'):
        return 'def2-QZVP' + text[len('def2-tzvp'):]
    found = re.fullmatch(r'(aug-)?cc-pv([dtq5])z', low)
    if found:
        bigger = {'d': 'T', 't': 'Q', 'q': '5', '5': '5'}[found.group(2)]
        return f'{"aug-" if found.group(1) else ""}cc-pV{bigger}Z'
    if low.startswith('6-31'):
        return '6-311+G(2d,p)'
    return 'def2-TZVP'


def available(key, kind):
    from modules.sextant import inputs

    tasks = set(inputs.tasks_for(kind))
    return key in PRESETS and all(task in tasks for task, _ in PRESETS[key][1])


def steps(key, calc):
    """[(name, task, overrides)] of a preset for the settings calc («+» of a basis: larger_basis)."""
    out = []
    for task, changes in PRESETS[key][1]:
        changes = dict(changes)
        if changes.get('basis') == '+':
            changes['basis'] = larger_basis(calc.basis)
        name = tr(task) + (f' · {changes["basis"]}' if 'basis' in changes else '')
        out.append((name, task, changes))
    return out


def items(key, molecule, calc, custom=None):
    """The steps as items of a queue; custom — [{'method', 'basis'}] of every step (chain_steps.ChainSteps.overrides,
    2026-11-21): what differs from the settings of the form goes into the step and its name."""
    from modules.sextant import batch

    out = []
    for k, (name, task, changes) in enumerate(steps(key, calc), start=1):
        own = dict(custom[k - 1]) if custom and k - 1 < len(custom) else {}
        own = {field: value for field, value in own.items() if value and value != getattr(calc, field, None)}
        if own:
            changes = {**changes, **own}
            name = tr(task) + ' · ' + '/'.join(changes.get(f, getattr(calc, f)) for f in ('method', 'basis'))
        out.append(batch.BatchItem(f'{k}. {name}', molecule, calc.charge, calc.multiplicity,
                                   props={'task': task, 'calc': changes, 'chain': k}))
    return out


def prepare(queue, item):
    """§2.2: the geometry of the step before; True when the item changed (the queue is saved by the caller)."""
    k = queue.items.index(item)
    if k == 0:
        return False
    before = queue.items[k - 1]
    if before.state != 'done':
        raise ValueError(tr('Предыдущий шаг цепочки не дал результата — этот шаг не считается.'))
    if before.geometry is not None and before.geometry is not item.molecule:
        item.molecule = before.geometry
        return True
    return False

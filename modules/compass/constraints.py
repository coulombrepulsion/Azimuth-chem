"""Optimization constraints on atoms, bonds, angles and dihedrals — the rules, without Qt (split from
modules/compass/actions/constraint_actions.py, the roadmap of 2026-11-09, stage 5: the first part of Compass that is
no longer a mixin of the window).

A constraint is (kind, atoms): 'C' an atom, 'B' a length, 'A' an angle, 'D' a dihedral angle; the atoms are indices
from 0. One constraint on the same atoms, in either direction.
"""

from azimuth.i18n import tr

KINDS = {1: 'C', 2: 'B', 3: 'A', 4: 'D'}


def find(items, atoms):
    atoms = tuple(atoms)
    return next((item for item in items if item[1] == atoms or item[1] == atoms[::-1]), None)


def toggled(items, atoms):
    """The constraints with the one on atoms added, or removed when it is there; ValueError for 0 or more than 4."""
    atoms = tuple(atoms)
    if not 1 <= len(atoms) <= 4:
        raise ValueError(tr('Выделите от одного до четырёх атомов: атом, связь, угол или двугранный угол.'))
    found = find(items, atoms)
    if found:
        return [item for item in items if item is not found]
    return list(items) + [(KINDS[len(atoms)], atoms)]


def names(molecule, atoms):
    return '–'.join(f'{molecule.atoms[i].symbol}{i + 1}' for i in atoms if i < len(molecule.atoms))


def text(item, molecule):
    kind, atoms = item
    return {'C': tr('Атом'), 'B': tr('Длина'), 'A': tr('Угол'), 'D': tr('Двугранный угол')}[kind] + ' ' + names(molecule, atoms)


def toggle_title(items, selected, molecule):
    """«Закрепить длину O1–H2» / «Освободить …» for the selection, or None when it is not 1–4 atoms."""
    if not 1 <= len(selected) <= 4:
        return None
    what = {1: tr('атом'), 2: tr('длину'), 3: tr('угол'), 4: tr('двугранный угол')}[len(selected)]
    return (tr('Освободить ') if find(items, selected) else tr('Закрепить ')) + what + ' ' + names(molecule, selected)

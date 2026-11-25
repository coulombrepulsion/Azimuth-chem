"""What the readers of structure files share: the numbers of their text, the element of a symbol or a number,
the molecule made of atoms, whether a file can be read.

Split off modules/compass/chemistry/formats.py (0.222.30).
"""

import re
from azimuth.core import Molecule, SYMBOLS, read_xyz
from azimuth.i18n import tr


def _f(text):
    try:
        return float(text.replace('D', 'E').replace('d', 'e'))
    except ValueError:  # said in the words of the program (was «could not convert string to float»)
        if not text.strip():
            raise ValueError(tr('пустое место там, где должно быть число (строка обрезана?).')) from None
        raise ValueError(tr(f'«{text.strip()}» — не число.')) from None


def readable(kind):
    """A reader of a damaged file says which format and line; an IndexError, a KeyError or a missing number
    becomes a ValueError with that text (was «list index out of range»)."""
    def wrap(function):
        def reader(text, *args, **kwargs):
            try:
                return function(text, *args, **kwargs)
            except (IndexError, KeyError, TypeError, ZeroDivisionError, AttributeError):
                raise ValueError(tr(f'{tr(kind)}: файл повреждён или записан в непривычном виде.')) from None
            except ValueError as exc:
                if str(exc).startswith(('invalid literal', 'could not convert', 'not enough values', 'too many values')):  # Python's own
                    raise ValueError(tr(f'{tr(kind)}: файл повреждён или записан в непривычном виде.')) from None
                raise
        reader.__name__, reader.__doc__ = function.__name__, function.__doc__
        return reader
    return wrap


def _symbol(text):
    text = re.sub(r'[^A-Za-z]', '', text)[:2]
    for cand in (text[:2].capitalize(), text[:1].upper()):
        if cand in SYMBOLS:
            return cand
    raise ValueError(tr(f'Неизвестный элемент: {text}'))


def _element(text):
    """An element by its symbol or by its atomic number (ORCA and Gaussian accept «6» for C in their
    inputs)."""
    name = text.split('(')[0]
    if name.isdigit() and 1 <= int(name) <= len(SYMBOLS):
        return SYMBOLS[int(name) - 1]
    return _symbol(text)


def _molecule(title, atoms, bonds):
    if not atoms:
        raise ValueError(tr('В файле нет атомов.'))
    body = f'{len(atoms)}\n{title}\n' + '\n'.join(f'{s} {x} {y} {z}' for s, x, y, z in atoms)
    mol = read_xyz(body)  # the usual checks: element names, counts, finite numbers
    # with the elements — O and S of furan, thiophene and the NH of pyrrole take no double bond (the rule of
    # kekule was given only to SMILES before), and a file without H gets its double bonds between carbons first
    symbols = [a.symbol for a in mol.atoms]
    return Molecule(title, mol.atoms, kekule(len(atoms), bonds, symbols) if bonds is not None else None)


# valences used to see which aromatic atoms can take a double bond
KEKULE_VALENCE = {'B': 3, 'C': 4, 'N': 3, 'P': 3, 'O': 2, 'S': 2, 'Se': 2}


def kekule(count, bonds, symbols=None):
    """Aromatic bonds (order 1.5 or 4) → alternating 1 and 2 (a perfect matching found by search; the fewest
    atoms left without a double bond).

    With the element symbols (and all bonds, hydrogens included) an aromatic atom whose usual
    valence is already used by its neighbours — O and S of furan and thiophene, the NH of pyrrole —
    takes no double bond (before, the search could put C=O, C=S or C=N there)."""
    bonds = [list(b) for b in bonds]
    arom = [k for k, b in enumerate(bonds) if b[2] in (1.5, 4)]
    if not arom:
        return tuple((i, j, int(o)) for i, j, o in bonds)
    full = set()
    if symbols is not None:
        degree = [0] * count
        for i, j, _ in bonds:
            degree[i] += 1
            degree[j] += 1
        full = {a for a in range(count) if symbols[a] in KEKULE_VALENCE and KEKULE_VALENCE[symbols[a]] - degree[a] < 1}
        arom_full = [k for k in arom if full & set(bonds[k][:2])]
        for k in arom_full:
            bonds[k][2] = 1
        arom = [k for k in arom if k not in arom_full]
        if not arom:
            return tuple((i, j, int(o)) for i, j, o in bonds)
    atoms = sorted({x for k in arom for x in bonds[k][:2]})
    tried = arom
    # a file of the heavy atoms only (no H to tell the NH of pyrrole) — the double bonds go between carbons
    # first, and the atom an odd ring leaves without one is a heteroatom (pyrrole, imidazole: N–H, not CH₂)
    if symbols is not None and 'H' not in symbols:
        hetero = {a for a in atoms if symbols[a] != 'C'}
        atoms.sort(key=lambda a: (a in hetero, a))
        tried = sorted(arom, key=lambda k: sum(x in hetero for x in bonds[k][:2]))
    for k in arom:
        bonds[k][2] = 1
    taken = set()

    def solve(rest, skips):
        if not rest:
            return True
        a = rest[0]
        if a in taken:
            return solve(rest[1:], skips)
        for k in tried:
            i, j = bonds[k][:2]
            if a in (i, j):
                b = j if i == a else i
                if b not in taken:
                    taken.update((a, b))
                    bonds[k][2] = 2
                    if solve(rest[1:], skips):
                        return True
                    taken.difference_update((a, b))
                    bonds[k][2] = 1
        return skips > 0 and solve(rest[1:], skips - 1)  # an atom may stay without (pyrrole N)

    # the fewest atoms without a double bond — every atom paired when it can be (before, any atom but the
    # last could be left out, so an odd ring could not leave its last atom, and a pairing could stop short)
    for skips in range(len(atoms) + 1):
        if solve(atoms, skips):
            break
    return tuple((i, j, int(o)) for i, j, o in bonds)

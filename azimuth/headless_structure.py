"""Structures without the window: a molecule or a crystal built and edited by commands — for a language model through
tools/azimuth_mcp.py (the owner, 2026-11-27: «можно ли как-то сделать, чтоб можно было через языковую модель делать
структуры в Компасе?»), by the same code Compass uses when one builds by hand.

§1 PURPOSE
    The model says what to build (a SMILES, a name, a molecule of the library, a file; a CIF, a number of COD) and a list
    of operations on it; the result is a file Compass opens (XYZ or MOL for a molecule, CIF for a crystal) and a
    description of it: the formula, every atom with its number, the bonds — so that the next command can name atoms by
    their numbers. Nothing here imports Qt (tests/core/test_architecture_boundaries.py).
§2 RULES
    1. Atoms and sites are numbered from 1, as in the table of coordinates of Compass. Every operation is checked by
       the code of Compass (editing, transforms, uff, crystal, surface, layer); its ValueError is the answer, nothing is
       written then.
    2. A molecule: {'smiles'} | {'name'} (PubChem: its 3D record, else its SMILES; needs the network) | {'library'} (a
       molecule of «Библиотека молекул»: its title or its beginning, or a key of azimuth.links.MOLECULES such as
       «water») | {'xyz'} | {'path'}; 'title' names it. Operations (MOLECULE_OPERATIONS):
         {'op': 'element', 'atom': n, 'symbol': 'N'} — the atom becomes another element (a terminal one moves to the
             new bond length);
         {'op': 'substitute', 'atom': n, 'fragment': 'methyl'} — a terminal atom (usually H) replaced by a fragment
             of Compass (FRAGMENT_NAMES or a key of builder.FRAGMENTS, or a unique part of one);
         {'op': 'delete', 'atoms': [n, …]}; {'op': 'add_hydrogens', 'atoms': [n, …] (all when left out)};
         {'op': 'set', 'atoms': [a, b] | [a, b, c] | [a, b, c, d], 'value': Å or degrees, 'move': 'fragment' |
             'atom'} — a distance, an angle or a dihedral, as «Изменить» of the measurement in Compass;
         {'op': 'optimize'} — UFF (uff.optimize), the energy in kcal/mol in the answer;
         {'op': 'conformers', 'step': 120, 'count': 5} — torsions turned (conformers.candidates, no energies: the
             score of the contacts); the best is the structure from here on, the others are written beside it.
    3. A crystal: {'cif'} | {'path'} | {'cod': number} (Crystallography Open Database, needs the network). Operations
       (CRYSTAL_OPERATIONS): {'op': 'primitive'}; {'op': 'supercell', 'n': [n1, n2, n3]}; {'op': 'surface', 'hkl': [h,
       k, l], 'layers': 1, 'vacuum': 15}; {'op': 'monolayer', 'vacuum': 15}; {'op': 'vacuum', 'value': Å};
       {'op': 'substitute', 'sites': [n, …], 'symbol': 'Fe'}; {'op': 'vacancy', 'sites': [n, …]}. Substitution and
       vacancy act on the atoms of one cell (group P 1, as a supercell) — the numbers of the description.
    4. The file goes where 'out' says (its suffix: .xyz or .mol for a molecule, .cif for a crystal), or to ROOT_DIR —
       ~/Documents/Azimuth/Структуры — under the title and the time; a file that exists is never overwritten (a
       number is added). The description lists at most LIST_LIMIT atoms (the file has all).
§3 INTERFACE
    molecule(spec) -> Molecule; build_molecule(spec, operations=(), out=None, root=None) -> dict;
    crystal(spec) -> Crystal; build_crystal(spec, operations=(), out=None, root=None) -> dict;
    catalogue() -> {'fragments', 'library', 'molecule_operations', 'crystal_operations'}.
§7 TESTS tests/core/test_headless_structure.py.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from pathlib import Path

ROOT_DIR = Path.home() / 'Documents' / 'Azimuth' / 'Структуры'
LIST_LIMIT = 300
MOLECULE_OPERATIONS = ('element', 'substitute', 'delete', 'add_hydrogens', 'set', 'optimize', 'conformers')
CRYSTAL_OPERATIONS = ('primitive', 'supercell', 'surface', 'monolayer', 'vacuum', 'substitute', 'vacancy')
FRAGMENT_NAMES = {'methyl': 'Метил · —CH₃', 'hydroxyl': 'Гидроксил · —OH', 'amino': 'Амино · —NH₂',
                  'carbonyl': 'Карбонил · >C=O', 'phenyl': 'Фенил · —C₆H₅'}


# -- molecules -------------------------------------------------------------------------------------------------------
def _library_key(text):
    from azimuth import links
    from modules.compass.chemistry import library

    text = str(text).strip()
    if text.lower() in links.MOLECULES:
        return links.MOLECULES[text.lower()]
    keys = library.keys()
    if text in keys:
        return text
    low = text.lower()
    found = [k for k in keys if k.lower().split(' · ')[0] == low] or [k for k in keys if k.lower().startswith(low)]
    if len(found) != 1:
        raise ValueError(f'no single molecule {text!r} in the library'
                         + (f' (it may be: {", ".join(found[:8])})' if found else ''))
    return found[0]


def molecule(spec):
    """The Molecule of spec (§2.2); its bonds perceived when the source has none."""
    from azimuth import headless
    from modules.compass.chemistry import formats, library

    if isinstance(spec, dict) and spec.get('library'):
        made = library.molecule(_library_key(spec['library']))
    elif isinstance(spec, dict) and spec.get('name'):
        from modules.compass.chemistry import pubchem

        try:
            found = pubchem.by_name(str(spec['name']))
        except OSError as exc:
            raise ValueError(f'PubChem cannot be reached: {exc}') from None
        if found is None:
            raise ValueError(f'PubChem does not know {spec["name"]!r}')
        kind, text = found
        made = formats.read_sdf_records(text)[0] if kind == 'sdf' else formats.from_smiles(text)
        if isinstance(made, tuple):
            made = made[0]
        made = replace(made, title=str(spec['name']))
    else:
        if not isinstance(spec, dict) or not any(spec.get(k) for k in ('smiles', 'xyz', 'path')):
            raise ValueError('a molecule is {"smiles"}, {"name"}, {"library"}, {"xyz"} or {"path"}')
        made = headless.molecule(spec)[0]
    if isinstance(spec, dict) and spec.get('title'):
        made = replace(made, title=str(spec['title']))
    if not made.atoms:
        raise ValueError('no atoms')
    return _bonded(made)


def _bonded(made):
    from modules.compass.chemistry.builder import connections

    return made if made.bonds else replace(made, bonds=tuple(connections(made)))


def _index(made, number, what='atom'):
    try:
        n = int(number)
    except (TypeError, ValueError):
        raise ValueError(f'{what} numbers are whole numbers from 1') from None
    if not 1 <= n <= len(made.atoms):
        raise ValueError(f'no {what} {n}: they are numbered 1…{len(made.atoms)}')
    return n - 1


def _fragment(name):
    from modules.compass.chemistry.builder import FRAGMENTS

    text = str(name or '').strip()
    if text.lower() in FRAGMENT_NAMES:
        return FRAGMENT_NAMES[text.lower()]
    if text in FRAGMENTS:
        return text
    found = [k for k in FRAGMENTS if text and text.lower() in k.lower()]
    if len(found) != 1:
        raise ValueError(f'no single fragment {text!r}' + (f' (it may be: {", ".join(found[:8])})' if found else '')
                         + ' — the list: azimuth_structure_catalogue')
    return found[0]


def _molecule_step(made, step, notes, extra):
    from modules.compass.chemistry import builder, editing, transforms

    if not isinstance(step, dict) or step.get('op') not in MOLECULE_OPERATIONS:
        raise ValueError(f'an operation is {{"op": one of {", ".join(MOLECULE_OPERATIONS)}, …}}: {step!r}')
    op = step['op']
    if op == 'element':
        symbol = str(step.get('symbol', '')).strip().capitalize()
        from azimuth.core import Z

        if symbol not in Z:
            raise ValueError(f'no element {symbol!r}')
        return editing.change_element(made, _index(made, step.get('atom')), symbol)
    if op == 'substitute':
        return editing.substitute(made, _index(made, step.get('atom')), _fragment(step.get('fragment')))
    if op == 'delete':
        atoms = sorted({_index(made, n) for n in step.get('atoms') or ()})
        if not atoms:
            raise ValueError('delete: "atoms": [numbers]')
        if len(atoms) == len(made.atoms):
            raise ValueError('delete: not every atom')
        return builder.delete_atoms(made, atoms)
    if op == 'add_hydrogens':
        atoms = step.get('atoms')
        return editing.add_hydrogens(made, None if not atoms else [_index(made, n) for n in atoms])
    if op == 'set':
        atoms = [_index(made, n) for n in step.get('atoms') or ()]
        try:
            value = float(step.get('value'))
        except (TypeError, ValueError):
            raise ValueError('set: "value" — Å for two atoms, degrees for three or four') from None
        moved = transforms.set_measurement(made, atoms, value, move_fragment=step.get('move', 'fragment') != 'atom')
        return moved
    if op == 'optimize':
        from modules.compass.chemistry import uff

        found = uff.optimize(made)
        extra['uff_energy_kcal_mol'] = round(found.energy, 3)
        notes.append(f'UFF: {found.start:.2f} → {found.energy:.2f} kcal/mol in {found.steps} steps')
        return replace(found.molecule, title=made.title, bonds=made.bonds)
    # conformers
    from modules.compass.chemistry import conformers

    step_angle = int(step.get('step', 120))
    count = max(1, min(int(step.get('count', 5)), 20))
    found = conformers.candidates(made, step=step_angle, limit=int(step.get('limit', 500)))
    if not found:
        raise ValueError('conformers: no turn of the torsions keeps the atoms apart')
    extra['conformers'] = [replace(m, title=f'{made.title} conformer {k + 1}', bonds=made.bonds)
                           for k, (m, _) in enumerate(found[:count])]
    notes.append(f'conformers: {len(found)} distinct, the best {len(extra["conformers"])} kept (no energies: '
                 'compute them, e.g. xtb)')
    return extra['conformers'][0]


def describe_molecule(made, limit=LIST_LIMIT):
    from modules.compass.chemistry.builder import connections

    bonds = connections(made)
    return {
        'title': made.title, 'formula': made.formula, 'atoms': len(made.atoms),
        'list': [[k + 1, a.symbol, round(a.x, 4), round(a.y, 4), round(a.z, 4)] for k, a in enumerate(made.atoms[:limit])],
        'bonds': [[i + 1, j + 1, o] for i, j, o in bonds[:limit * 2]],
        'listed_in_full': len(made.atoms) <= limit,
    }


def _target(out, root, title, suffix, allowed):
    if out:
        path = Path(str(out)).expanduser()
        if path.suffix.lower() not in allowed:
            raise ValueError(f'"out" ends with {" or ".join(allowed)}')
    else:
        name = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in (title or 'structure'))[:60] or 'structure'
        path = Path(root or ROOT_DIR) / f'{name}-{datetime.now():%Y%m%d-%H%M%S}{suffix}'
    path.parent.mkdir(parents=True, exist_ok=True)
    stem, k = path, 2
    while path.exists():  # never over a file there
        path = stem.with_name(f'{stem.stem}-{k}{stem.suffix}')
        k += 1
    return path


def _molecule_text(made, path):
    from modules.compass.chemistry import formats

    if path.suffix.lower() == '.mol':
        return formats.write_mol(made, made.bonds or ())
    return made.xyz()


def build_molecule(spec, operations=(), out=None, root=None):
    """§2.2, §2.4: the molecule built, edited in turn, written; its description and the path."""
    made = molecule(spec)
    notes, extra = [], {}
    for k, step in enumerate(operations or ()):
        try:
            made = _bonded(_molecule_step(made, step, notes, extra))
        except ValueError as exc:
            raise ValueError(f'operation {k + 1} ({(step or {}).get("op") if isinstance(step, dict) else step}): {exc}') from None
    path = _target(out, root, made.title, '.xyz', ('.xyz', '.mol'))
    path.write_text(_molecule_text(made, path), encoding='utf-8')
    answer = describe_molecule(made)
    answer['file'] = str(path)
    others = []
    for m in extra.get('conformers', [])[1:]:
        other = _target(None, path.parent, f'{path.stem}-conformer', path.suffix, ())
        other.write_text(_molecule_text(m, other), encoding='utf-8')
        others.append(str(other))
    if others:
        answer['other_conformers'] = others
    if 'uff_energy_kcal_mol' in extra:
        answer['uff_energy_kcal_mol'] = extra['uff_energy_kcal_mol']
    answer['notes'] = notes + ['Open the file in Compass: «Файл → Открыть…».']
    return answer


# -- crystals --------------------------------------------------------------------------------------------------------
def crystal(spec):
    from azimuth import headless_crystal

    if isinstance(spec, dict) and spec.get('cod'):
        from modules.compass.chemistry import cod, crystal as cr

        try:
            text = cod.fetch(int(spec['cod']))
        except OSError as exc:
            raise ValueError(f'COD cannot be reached: {exc}') from None
        made = cr.parse_cif(text)
        return replace(made, title=str(spec.get('title') or made.title or f'COD {spec["cod"]}'))
    made, title = headless_crystal.crystal(spec)
    return replace(made, title=title)


def p1(made):
    """The crystal with the atoms of one cell as its sites (group P 1)."""
    from modules.compass.chemistry import crystal as cr

    if made.space_group == 'P 1' and len(made.operations) == 1:
        return made
    sites = tuple(cr.Site(label, symbol, fx, fy, fz) for symbol, fx, fy, fz, label in cr.unit_cell(made))
    return replace(made, sites=sites, operations=(cr.operation('x, y, z'),), space_group='P 1', number=1)


def _sites(made, step):
    numbers = step.get('sites')
    if numbers is None and step.get('site') is not None:
        numbers = [step['site']]
    if not numbers:
        raise ValueError('"sites": [numbers of the atoms of the cell]')
    return sorted({_index(_Sized(made.sites), n, 'site') for n in numbers})


class _Sized:  # _index asks for .atoms
    def __init__(self, sites):
        self.atoms = sites


def _crystal_step(made, step):
    from modules.compass.chemistry import crystal as cr, layer, surface

    if not isinstance(step, dict) or step.get('op') not in CRYSTAL_OPERATIONS:
        raise ValueError(f'an operation is {{"op": one of {", ".join(CRYSTAL_OPERATIONS)}, …}}: {step!r}')
    op = step['op']
    if op == 'primitive':
        return cr.primitive(made)
    if op == 'supercell':
        n = step.get('n') or ()
        if len(n) != 3:
            raise ValueError('supercell: "n": [n1, n2, n3]')
        return cr.supercell(made, n)
    if op == 'surface':
        hkl = step.get('hkl') or ()
        if len(hkl) != 3:
            raise ValueError('surface: "hkl": [h, k, l]')
        return surface.slab(made, hkl, int(step.get('layers', 1)), float(step.get('vacuum', 15.0)))
    if op == 'monolayer':
        return layer.monolayer(made, float(step.get('vacuum', 15.0)))
    if op == 'vacuum':
        return layer.with_vacuum(made, float(step.get('value', 15.0)))
    made = p1(made)
    chosen = _sites(made, step)
    if op == 'vacancy':
        if len(chosen) == len(made.sites):
            raise ValueError('vacancy: not every atom')
        return replace(made, sites=tuple(s for k, s in enumerate(made.sites) if k not in chosen),
                       formula_sum='', formula_z=0)
    from azimuth.core import Z

    symbol = str(step.get('symbol', '')).strip().capitalize()
    if symbol not in Z:
        raise ValueError(f'no element {symbol!r}')
    sites = list(made.sites)
    for k in chosen:
        sites[k] = replace(sites[k], symbol=symbol, label=f'{symbol}{k + 1}')
    return replace(made, sites=tuple(sites), formula_sum='', formula_z=0)


def describe_crystal(made, limit=LIST_LIMIT):
    from modules.compass.chemistry import crystal as cr

    cell = cr.unit_cell(made)
    counts = {}
    for symbol, *_ in cell:
        counts[symbol] = counts.get(symbol, 0) + 1
    c = made.cell
    listed = p1(made).sites
    return {
        'title': made.title, 'space_group': made.space_group,
        'cell': {'a': round(c.a, 5), 'b': round(c.b, 5), 'c': round(c.c, 5), 'alpha': round(c.alpha, 4),
                 'beta': round(c.beta, 4), 'gamma': round(c.gamma, 4), 'volume': round(c.volume(), 3)},
        'atoms_in_cell': len(cell), 'composition': counts,
        'sites': [[k + 1, s.label, s.symbol, round(s.x, 5), round(s.y, 5), round(s.z, 5)]
                  for k, s in enumerate(listed[:limit])],
        'listed_in_full': len(listed) <= limit,
    }


def build_crystal(spec, operations=(), out=None, root=None):
    """§2.3, §2.4: the crystal made, changed in turn, written as CIF; its description and the path."""
    from modules.compass.chemistry import surface

    made = crystal(spec)
    title = made.title
    for k, step in enumerate(operations or ()):
        try:
            made = _crystal_step(made, step)
        except ValueError as exc:
            raise ValueError(f'operation {k + 1} ({(step or {}).get("op") if isinstance(step, dict) else step}): {exc}') from None
    made = replace(made, title=made.title or title)
    path = _target(out, root, made.title, '.cif', ('.cif',))
    path.write_text(surface.write_cif(made), encoding='utf-8')
    answer = describe_crystal(made)
    answer['file'] = str(path)
    answer['notes'] = ['Open the file in Compass: «Файл → Открыть…» (Компас · Кристалл); the calculation — '
                       'azimuth_crystal_preview / azimuth_crystal_run with {"path": this file}.']
    return answer


def catalogue():
    from modules.compass.chemistry import builder, library

    return {'fragments': {'short names': FRAGMENT_NAMES, 'all': list(builder.FRAGMENTS)},
            'library': library.keys(), 'molecule_operations': list(MOLECULE_OPERATIONS),
            'crystal_operations': list(CRYSTAL_OPERATIONS)}

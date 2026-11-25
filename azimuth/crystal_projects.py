"""A crystal as a project of its own.

§1 PURPOSE
    A CIF opened in «Компас · Кристалл» gets a project tab as a molecule file does: a folder of its own
    among the projects («Документы/Azimuth/Проекты/<name>»), the file of the crystal in it, the calculations of Quantum
    ESPRESSO in its «calculations», a record of each run.
§2 ALGORITHM
    A project of a crystal is an ordinary project (azimuth/projects.py: project.qcc, project.sqlite, calculations/) with
    no molecules and one more key of its document, KEY: {'cif': the file name, 'title', 'formula', 'runs': [...]}. The
    projects of molecules have no such key and are read and written as before; an older Azimuth opens a crystal project
    as an empty project (the key is kept in the document, nothing is lost). The tabs (project_navigation.py) tell a
    crystal project by is_crystal and show «Компас · Кристалл» for it. The first crystal stays where it was (KEY: cif,
    title, formula, runs — an older Azimuth sees it), the others are in KEY['more'] — {'id', 'cif'
    (crystal-<id>.cif), 'title', 'formula', 'runs'} each; KEY['active'] — the id of the crystal shown ('crystal' for
    the first). info, cif_text, title and record_run speak of the active crystal unless an id is given, so the runs
    and steps of a crystal stay its own.
§4 SPECIFICATION
    KEY = 'crystal'; CIF = 'crystal.cif'; create(root, name, cif_text) -> path of project.qcc; is_crystal(path) -> bool;
    info(path) -> dict; cif_text(path) -> str; title(path) -> str; record_run(path, run) — run: dict (folder,
    task, time, energy …) appended to the runs of the active crystal. Crystals(path) -> [info of each,
    'id' in it]; add(path, cif_text, name) -> id (the crystal added becomes the active one); set_active(path, id).
§7 TESTS
    tests/core/test_crystal_projects.py; tests/gui/test_gui_files.py::test_a_crystal_is_a_project."""

from pathlib import Path

KEY = 'crystal'
CIF = 'crystal.cif'
FIRST = 'crystal'  # the id of the first crystal of a project
_OWN = ('cif', 'title', 'formula', 'atoms', 'result', 'runs')  # what each crystal has of its own


def _manifest(path):
    from azimuth import projects

    path = Path(path)
    return path / projects.MANIFEST if path.is_dir() else path


def _formula(cif_text):
    return composition(cif_text)[0]


def composition(cif_text):
    """(the formula, the number of atoms) of a cell — the formula of the CIF (_chemical_formula_sum) or, without it (a
    CIF written from an output of CRYSTAL), that of the atoms of the cell; ('', None) when it cannot be read."""
    try:
        from azimuth.core import Atom, Molecule
        from modules.compass.chemistry import crystal as cr

        data = cr.parse_cif(cif_text)
        cell = cr.unit_cell(data)
    except (ValueError, ImportError, KeyError, IndexError):
        return '', None
    given = (data.formula_sum or '').replace(' ', '')
    if not given:  # the formula unit (C6Cl6 of hexachlorobenzene, not C12Cl12 of its cell)
        try:
            from modules.compass.chemistry import crystal_symmetry

            given = crystal_symmetry.empirical_formula(data)
        except (ValueError, IndexError, KeyError):
            given = ''
    return given or Molecule('', tuple(Atom(a[0], 0, 0, 0) for a in cell)).formula, len(cell)


def create(root, name, cif_text):
    from azimuth import projects
    from azimuth.project_folders import new_project_folder

    folder = new_project_folder(Path(root), name)
    project = projects.Project.create(folder)
    formula, atoms = composition(cif_text)
    (folder / CIF).write_text(cif_text, encoding='utf-8')
    project.data.update(name=name, named=True, draft=False)
    project.data[KEY] = {'cif': CIF, 'title': name, 'formula': formula, 'atoms': atoms, 'runs': []}
    project.save()
    return project.path


def is_crystal(path):
    if not path:
        return False
    try:
        from azimuth import projects

        manifest = _manifest(path)
        return manifest.is_file() and isinstance(projects.Project.view(manifest).data.get(KEY), dict)
    except (OSError, ValueError, KeyError):
        return False


def _all(entry):
    """[(id, the dict of the crystal in the document)] — the first one is the key itself."""
    return [(FIRST, entry)] + [(str(c.get('id')), c) for c in entry.get('more') or [] if isinstance(c, dict)]


def _pick(entry, ident=None):
    ident = ident or entry.get('active') or FIRST
    found = dict(_all(entry)).get(str(ident))
    return (FIRST, entry) if found is None else (str(ident), found)


def _data(path):
    from azimuth import projects

    return projects.Project.view(_manifest(path)).data


def _view(ident, own):
    out = {k: own[k] for k in _OWN if k in own}
    out['id'] = ident
    return out


def crystals(path):
    """The crystals of the project, the first first — {'id', 'cif', 'title', 'formula', 'runs'}."""
    return [_view(ident, own) for ident, own in _all(_data(path).get(KEY) or {})]


def active(path):
    return _pick(_data(path).get(KEY) or {})[0]


def info(path, ident=None):
    """The active crystal (or the crystal ident): cif, title, formula, runs, id."""
    entry = _data(path).get(KEY) or {}
    return _view(*_pick(entry, ident))


def cif_text(path, ident=None):
    manifest = _manifest(path)
    return (manifest.parent / (info(manifest, ident).get('cif') or CIF)).read_text(encoding='utf-8')


def title(path, ident=None):
    data = _data(path)
    return info(path, ident).get('title') or data.get('name') or 'CIF'


def record_run(path, run, ident=None):
    from azimuth import projects

    with projects.edit(_manifest(path)) as project:
        entry = project.data.setdefault(KEY, {})
        _pick(entry, ident)[1].setdefault('runs', []).append(dict(run))


def add(path, cif_text, name):
    """One more crystal in the project (its own file crystal-<n>.cif beside crystal.cif); it becomes the
    active one. Returns its id."""
    from azimuth import projects

    manifest = _manifest(path)
    with projects.edit(manifest) as project:
        entry = project.data.setdefault(KEY, {})
        taken = {ident for ident, _ in _all(entry)}
        n = 2
        while str(n) in taken or (manifest.parent / f'crystal-{n}.cif').exists():
            n += 1
        ident = str(n)
        (manifest.parent / f'crystal-{n}.cif').write_text(cif_text, encoding='utf-8')
        formula, atoms = composition(cif_text)
        entry.setdefault('more', []).append({'id': ident, 'cif': f'crystal-{n}.cif', 'title': name,
                                             'formula': formula, 'atoms': atoms, 'runs': []})
        entry['active'] = ident
    return ident


def set_result(path, method, energy, ident=None, pressure=None):
    """What the file the crystal was read from gave — an output
    of CRYSTAL: its method and its energy (Eh) — shown in the list of the project until a run of the project has one."""
    from azimuth import projects

    with projects.edit(_manifest(path)) as project:
        entry = project.data.setdefault(KEY, {})
        _pick(entry, ident)[1]['result'] = {'method': str(method or ''), 'energy': energy,
                                            'pressure': pressure}  # GPa: the external pressure of the output


def pressure(info):
    """The external pressure of the file the crystal was read from (an output of CRYSTAL), GPa, or None."""
    value = (info.get('result') or {}).get('pressure')
    return float(value) if isinstance(value, (int, float)) else None


def batch_ids(path):
    """The crystals with a
    tick in the batch of the project, in the order of its list."""
    entry = _data(path).get(KEY) or {}
    out = set(entry.get('batch_excluded') or [])
    return [ident for ident, _ in _all(entry) if ident not in out]


def set_in_batch(path, ident, on):
    from azimuth import projects

    with projects.edit(_manifest(path)) as project:
        entry = project.data.setdefault(KEY, {})
        out = [i for i in entry.get('batch_excluded') or [] if i != ident]
        entry['batch_excluded'] = out if on else out + [ident]


def cells(path, info):
    """The texts of the columns of the list of a project after «Формула» (project_widgets.COLUMNS[3:]:
    method, energy (Eh), atoms, charge, runs, last run) for a crystal of the project (one of crystals(path)). The method
    and the energy — of its last run that has an energy, else of the file it was read from (set_result)."""
    runs = info.get('runs') or []
    method, energy = '', ''
    for run in reversed(runs):
        value = run.get('energy_eh')
        if value is None and isinstance(run.get('energy_ry'), (int, float)):
            value = run['energy_ry'] / 2
        if isinstance(value, (int, float)):
            program = 'CP2K' if run.get('program') == 'cp2k' else 'Quantum ESPRESSO'
            method = program + (' · ' + str(run['task']) if run.get('task') else '')
            energy = f'{value:.6f}'
            break
    else:
        result = info.get('result') or {}
        method = result.get('method') or ''
        if isinstance(result.get('energy'), (int, float)):
            energy = f"{result['energy']:.6f}"
    atoms = info.get('atoms')
    if atoms is None:
        try:
            atoms = composition(cif_text(path, info.get('id')))[1]
        except OSError:
            atoms = None
    last = runs[-1] if runs else {}
    return (method, energy, '' if atoms is None else str(atoms), '', str(len(runs)) if runs else '',
            str(last.get('task') or '') if last else '')


def set_active(path, ident):
    from azimuth import projects

    with projects.edit(_manifest(path)) as project:
        entry = project.data.setdefault(KEY, {})
        entry['active'] = _pick(entry, ident)[0]

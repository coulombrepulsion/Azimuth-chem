"""Azimuth without its window: a calculation of a crystal in Quantum ESPRESSO or CP2K on this computer.

§1 PURPOSE
    azimuth/headless.py runs the molecular programs; this module does the same for a crystal — for a language model
    through tools/azimuth_mcp.py (the owner, 2026-11-27: the calculation of crystals, «и на cp2k тоже»). The code is
    that of the panel of the crystal calculation (modules/compass/actions/qe_window.py, qe_run.py): the cell computed
    (primitive, supercell), qe_inputs.steps / cp2k_inputs.cp2k_input, the pseudopotentials of «Установить программы»,
    modules/sextant/qe_local.py for the command, runner.Job, the readers of modules/spectrum/readers. No Qt here.
§2 RULES
    1. The crystal: {'cif': text} or {'path': a .cif file}; an optional 'title'.
    2. The settings are those of the panel by the names of qe_inputs.Options / cp2k_inputs.Options (ecutwfc, cutoff,
       functional, vdw, spin, charge …) and: task, primitive (True: the primitive cell when the lattice is centred),
       supercell [n1, n2, n3], spacing (Å⁻¹, Quantum ESPRESSO), processes, hubbard ('Ni 6'), order ('afm' — the
       antiferromagnetic order of magnetism.afm_signs). A name not known is refused with the names that are.
    3. What the panel chooses is chosen here too: CP2K computes at the Γ point, so without a supercell asked the cell
       is repeated until its edges reach GAMMA_LENGTH; its CUTOFF is cp2k_inputs.cutoff_for of the elements.
    4. Nothing is downloaded here: pseudopotentials not installed are refused with what to do.
§3 INTERFACE
    PROGRAMS; crystal(spec) -> (Crystal, title); options(program) -> dict; prepare(program, spec, settings=None,
    root=None) -> Prepared(program, task, steps, computed, processes, title, library, atoms);
    preview(program, spec, settings=None) -> {file: text}; job(prepared, jobs_root=None, tools_root=None) ->
    runner.JobSpec (the folder is made, the files are written); result(path) -> dict.
§7 TESTS tests/core/test_headless_crystal.py.
"""

from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path

PROGRAMS = ('qe', 'cp2k')
NAMES = {'qe': 'Quantum ESPRESSO', 'cp2k': 'CP2K'}
GAMMA_LENGTH = 10.0  # Å — as the panel (QePanel.GAMMA_LENGTH)
OWN = ('task', 'primitive', 'supercell', 'spacing', 'processes', 'hubbard', 'order')
RY_EV, HARTREE_EV = 13.605693122994, 27.211386245988


@dataclass(frozen=True)
class Prepared:
    program: str
    task: str
    steps: tuple
    computed: object
    processes: int
    title: str
    library: object = None
    atoms: int = 0  # in the cell computed


def _known(program):
    if program not in PROGRAMS:
        raise ValueError(f'unknown program {program!r}; crystals are computed by: {", ".join(PROGRAMS)}')


def crystal(spec):
    """(Crystal, its title) of {'cif': …} or {'path': …}."""
    from modules.compass.chemistry import crystal as cr

    if not isinstance(spec, dict) or not any(spec.get(k) for k in ('cif', 'path')):
        raise ValueError('a crystal is {"cif": "<text of a CIF file>"} or {"path": "<a .cif file>"}')
    title = str(spec.get('title') or '')
    if spec.get('cif'):
        text = str(spec['cif'])
    else:
        path = Path(str(spec['path'])).expanduser()
        if not path.is_file():
            raise ValueError(f'no file {path}')
        if path.suffix.lower() != '.cif':
            raise ValueError(f'not a CIF file: {path.name}')
        text = path.read_text(encoding='utf-8', errors='replace')
        title = title or path.stem
    try:
        made = cr.parse_cif(text)
    except (ValueError, KeyError, IndexError) as exc:
        raise ValueError(f'the CIF is not read: {exc}') from exc
    return made, title or 'crystal'


def tasks(program):
    from modules.sextant import cp2k_inputs, qe_inputs

    _known(program)
    return list(cp2k_inputs.TASKS) if program == 'cp2k' else list(qe_inputs.TASKS) + list(qe_inputs.STEPS)


def _options_class(program):
    from modules.sextant import cp2k_inputs, qe_inputs

    return cp2k_inputs.Options if program == 'cp2k' else qe_inputs.Options


def options(program):
    """What can be asked of a program: its tasks and the names of the settings with what they are by default."""
    from modules.sextant import cp2k_inputs, qe_inputs

    _known(program)
    made = _options_class(program)()
    settings = {f.name: getattr(made, f.name) for f in fields(made) if f.name not in ('hubbard', 'magnetic')}
    found = {'program': NAMES[program], 'tasks': tasks(program), 'settings': settings,
             'functionals': list(cp2k_inputs.FUNCTIONALS if program == 'cp2k' else qe_inputs.FUNCTIONALS),
             'also': {'primitive': True, 'supercell': 'CP2K: until the edges reach 10 Å; else [1, 1, 1]', 'processes': 2,
                      'hubbard': "'' or e.g. 'Ni 6' (U in eV)", 'order': "'' or 'afm' (needs a cell that holds it)"}}
    if program == 'qe':
        found['also']['spacing'] = qe_inputs.SPACING
        found['settings']['ecutwfc'] = found['settings']['ecutrho'] = 'from the pseudopotentials'
    else:
        found['settings']['cutoff'] = 'by the elements (cp2k_inputs.cutoff_for): 400 Ry and more'
        found['note'] = 'CP2K computes at the Γ point: the cell is repeated to a supercell.'
    return found


def _typed(name, value, default):
    try:
        if isinstance(default, bool):
            return value if isinstance(value, bool) else str(value).lower() in ('1', 'true', 'yes', 'да')
        if isinstance(default, int):
            return int(value)
        if isinstance(default, float) or default is None:
            return None if value is None else float(value)
        if isinstance(default, str):
            return str(value)
    except (TypeError, ValueError):
        raise ValueError(f'{name}: {value!r} is not understood') from None
    return value


def _computed(base, primitive, supercell):
    """(the cell computed, its rows in the fractions of the cell of the file) — QePanel.computed."""
    import numpy as np

    from modules.compass.chemistry import crystal as cr

    small = cr.primitive(base) if primitive else base
    reduced = primitive and len(cr.unit_cell(small)) < len(cr.unit_cell(base))
    start = small if reduced else base
    basis = cr.primitive_basis(base) if reduced else None
    if tuple(supercell) != (1, 1, 1):
        basis = np.diag(supercell).astype(float) @ (basis if basis is not None else np.eye(3))
    return cr.supercell(start, tuple(supercell)), basis, start


def prepare(program, spec, settings=None, root=None):
    """The steps of a calculation as the panel writes them; ValueError names what is wrong or missing."""
    from dataclasses import replace
    from math import ceil

    from modules.compass.chemistry import crystal as cr
    from modules.sextant import cp2k_inputs, hubbard, install_tools, magnetism, qe_inputs, qe_pseudo

    _known(program)
    base, title = crystal(spec)
    settings = dict(settings or {})
    cls = _options_class(program)
    defaults = cls()
    names = {f.name for f in fields(cls)} - {'hubbard', 'magnetic'}
    wrong = [k for k in settings if k not in names and k not in OWN]
    if wrong:
        raise ValueError(f'unknown setting {", ".join(map(repr, wrong))}; known: {", ".join(sorted(names | set(OWN)))}')
    task = str(settings.get('task') or 'Энергия')
    if task not in tasks(program):
        raise ValueError(f'{NAMES[program]} has no task {task!r}; its tasks: {", ".join(tasks(program))}')
    primitive = _typed('primitive', settings.get('primitive', True), True)
    processes = max(1, _typed('processes', settings.get('processes', 2), 2))
    asked = settings.get('supercell')
    if asked is not None:
        try:
            supercell = tuple(int(n) for n in asked)
        except (TypeError, ValueError):
            raise ValueError('supercell: three whole numbers, e.g. [2, 2, 2]') from None
        if len(supercell) != 3 or min(supercell) < 1:
            raise ValueError('supercell: three whole numbers from 1, e.g. [2, 2, 2]')
    elif program == 'cp2k':  # the Γ point alone: edges of GAMMA_LENGTH at least
        start = _computed(base, primitive, (1, 1, 1))[2]
        supercell = tuple(max(1, ceil(GAMMA_LENGTH / x - 1e-9)) for x in (start.cell.a, start.cell.b, start.cell.c))
    else:
        supercell = (1, 1, 1)
    computed, basis, _ = _computed(base, primitive, supercell)
    changes = {k: _typed(k, v, getattr(defaults, k)) for k, v in settings.items() if k in names and k != 'grid'}
    if settings.get('grid') is not None:  # the grid of k-points itself instead of the spacing
        try:
            changes['grid'] = tuple(int(n) for n in settings['grid'])
        except (TypeError, ValueError):
            raise ValueError('grid: three whole numbers, e.g. [6, 6, 6]') from None
        if len(changes['grid']) != 3 or min(changes['grid']) < 1:
            raise ValueError('grid: three whole numbers from 1, e.g. [6, 6, 6]')
    if settings.get('hubbard'):
        changes['hubbard'] = hubbard.parse(str(settings['hubbard']))
    order = str(settings.get('order') or '')
    if order not in ('', 'afm'):
        raise ValueError("order: '' or 'afm'")
    if order == 'afm':
        whole = _computed(base, primitive, (1, 1, 1))[0]
        changes['magnetic'] = magnetism.afm_signs(whole, supercell)
        changes['spin'] = program != 'cp2k'  # CP2K: the two kinds carry the moments (QePanel.options)
    if program == 'cp2k':
        if 'cutoff' not in changes:
            changes['cutoff'] = cp2k_inputs.cutoff_for({a[0] for a in cr.unit_cell(computed)})
        made = replace(defaults, **changes)
        steps = ((cp2k_inputs.INPUT, 'cp2k', cp2k_inputs.cp2k_input(computed, task, made)),)
        return Prepared(program, task, steps, computed, processes, title, None, len(cr.unit_cell(computed)))
    made = replace(defaults, **changes)
    root = Path(root) if root else install_tools.default_root()
    library = qe_pseudo.LIBRARIES[qe_inputs.library_of(made.functional or '')]
    if library.get('kind') == 'pslibrary':
        library = qe_pseudo.for_elements(library, [site.symbol for site in base.sites if site.symbol != 'X'])
    if not qe_pseudo.installed(root, library):
        raise ValueError(f'the pseudopotentials {library["name"]} are not installed: in Azimuth — «Расчёт → Установить '
                         'программы для расчёта…» → Quantum ESPRESSO, or «Скачать псевдопотенциалы» of the panel')
    spacing = _typed('spacing', settings.get('spacing', qe_inputs.SPACING), qe_inputs.SPACING)
    steps = qe_inputs.steps(computed, task, qe_pseudo.table(root, library), str(qe_pseudo.folder(root, library)), 'azimuth',
                            spacing, basis, base, made)
    return Prepared(program, task, tuple(steps), computed, processes, title, library, len(cr.unit_cell(computed)))


def preview(program, spec, settings=None, root=None):
    """The input files the panel would write, by their names."""
    made = prepare(program, spec, settings, root)
    return {name: text for name, _, text in made.steps}


def job(prepared, jobs_root=None, tools_root=None, now=None):
    """The folder of the job with its files written; what runner.Job starts. ValueError: the program is not found."""
    import os
    import shutil

    from modules.sextant import cp2k_inputs, install_tools, qe_local, qe_pseudo, runner

    tools_root = Path(tools_root) if tools_root else install_tools.default_root()
    cp2k = prepared.program == 'cp2k'
    program = install_tools.cp2k_program(tools_root) if cp2k else install_tools.qe_program(tools_root)
    if program is None:
        raise ValueError(f'{NAMES[prepared.program]} is not found on this computer: in Azimuth — «Расчёт → Установить '
                         'программы для расчёта…»')
    stamp = (now or datetime.now()).strftime('%Y%m%d-%H%M%S')
    safe = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in prepared.title)[:40] or 'crystal'
    folder = Path(jobs_root) if jobs_root else runner.default_jobs_root()
    folder = folder / f'{prepared.program}-{safe}-{stamp}'
    folder.mkdir(parents=True, exist_ok=True)
    steps = list(prepared.steps)
    beside = os.name == 'nt' and not cp2k
    if beside:
        steps = [(n, t, qe_local.beside(x)) for n, t, x in steps]
    for name, _, text in steps:
        (folder / name).write_text(text, encoding='utf-8', newline='\n')
    if cp2k:
        env = install_tools.cp2k_environment(program, prepared.processes)
        mpirun = Path(program).with_name('mpirun')
        mpi = prepared.processes > 1 and mpirun.is_file() and 'psmp' in Path(program).name
        command = [*([str(mpirun), '-np', str(prepared.processes)] if mpi else []), str(program), '-i', cp2k_inputs.INPUT]
        return runner.JobSpec('cp2k', folder, tuple(command), folder / cp2k_inputs.OUTPUT, env)
    if beside:
        pseudo = folder / 'pseudo'
        pseudo.mkdir(exist_ok=True)
        source = qe_pseudo.folder(tools_root, prepared.library)
        for file in qe_local.pseudo_files(steps):
            if not (source / file).is_file():
                raise ValueError(f'no pseudopotential {file} in {source}: in Azimuth — the panel of Quantum ESPRESSO, '
                                 '«Установить псевдопотенциалы»')
            shutil.copy2(source / file, pseudo / file)
    command, scripts, changes = qe_local.command(steps, program, prepared.processes, install_tools.qe_prefix(tools_root))
    for name, body in scripts.items():
        (folder / name).write_bytes(body)
    return runner.JobSpec('qe', folder, tuple(command), folder / 'pw.out', {**os.environ, **changes})


def _cell(rows):
    import numpy as np

    m = np.array(rows, dtype=float)
    lengths = [float(np.linalg.norm(v)) for v in m]

    def angle(u, v):
        return float(np.degrees(np.arccos(np.clip(np.dot(u, v) / (np.linalg.norm(u) * np.linalg.norm(v)), -1, 1))))

    return {'a': round(lengths[0], 5), 'b': round(lengths[1], 5), 'c': round(lengths[2], 5),
            'alpha': round(angle(m[1], m[2]), 3), 'beta': round(angle(m[0], m[2]), 3), 'gamma': round(angle(m[0], m[1]), 3),
            'volume_A3': round(abs(float(np.linalg.det(m))), 4)}


def result(path):
    """What a calculation of a crystal gave: path — its folder or its output (pw.out, cp2k.out)."""
    from modules.sextant import cp2k_inputs, runner

    path = Path(str(path)).expanduser()
    folder = path if path.is_dir() else path.parent
    if path.is_dir():
        found = [folder / name for name in ('pw.out', cp2k_inputs.OUTPUT) if (folder / name).is_file()]
        if not found:
            raise ValueError(f'no pw.out or {cp2k_inputs.OUTPUT} in {folder}')
        path = found[0]
    if not path.is_file():
        raise ValueError(f'no file {path}')
    text = path.read_text(encoding='utf-8', errors='replace')
    if path.name == cp2k_inputs.OUTPUT or 'CP2K|' in text[:20000]:
        from modules.spectrum.readers import cp2k

        r = cp2k.read(text, folder)
        out = {'file': str(path), 'program': r.version or 'CP2K', 'normal_exit': runner.finished_normally('cp2k', text, 0),
               'done': bool(r.done), 'converged': bool(r.converged), 'steps': r.steps, 'atoms': r.nat,
               'energy_hartree': r.energy_hartree,
               'energy_ev': None if r.energy_hartree is None else r.energy_hartree * HARTREE_EV}
        if r.cell is not None:
            out['cell'] = _cell(r.cell)
        return out
    from modules.spectrum.readers import qe

    if not qe.is_qe(text):
        raise ValueError(f'{path.name} is not an output of Quantum ESPRESSO or CP2K')
    runs = qe.runs(text)
    every = [qe.read(run) for run in runs] if len(runs) > 1 else []
    # the steps of the bands or of the density of states end with a run that has no total energy: the energy is that
    # of the last run with one (the scf); a series ends with its last point
    r = next((one for one in reversed(every) if one.energy is not None), None) or qe.read(runs[-1] if runs else text)
    out = {'file': str(path), 'program': f'Quantum ESPRESSO {r.version}'.strip(), 'calculation': r.calculation,
           'normal_exit': runner.finished_normally('qe', text, 0), 'done': bool(r.done), 'converged': bool(r.converged),
           'steps': r.steps, 'atoms': r.nat, 'energy_ry': r.energy, 'energy_hartree': r.energy_hartree,
           'energy_ev': None if r.energy is None else r.energy * RY_EV}
    if r.error:
        out['error'] = r.error
    if r.pressures:
        out['pressure_kbar'] = r.pressures[-1]
    if r.fermi is not None:
        out['fermi_ev'] = r.fermi
    if r.highest is not None and r.lowest is not None:
        out['highest_occupied_ev'], out['lowest_unoccupied_ev'] = r.highest, r.lowest
        out['gap_of_the_grid_ev'] = round(r.lowest - r.highest, 4)
    if r.magnetization is not None:
        out['magnetization_bohr'] = r.magnetization
        out['moments'] = [list(m) for m in r.moments]
    if r.cell is not None:
        out['cell'] = _cell(r.cell)
    if every:  # a series, or the steps of the bands: the energy of every run of pw.x
        out['runs'] = [{'calculation': one.calculation, 'energy_ry': one.energy, 'done': bool(one.done),
                        'pressure_kbar': one.pressures[-1] if one.pressures else None} for one in every]
    return out

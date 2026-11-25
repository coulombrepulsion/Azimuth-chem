"""Multiwfn on the wave function of a CP2K run of a crystal — for the panel of the calculation, for «Компас · Кристалл»
and for Spectrum alike (was in the panel only, qe_window.QePanel.show_aim / show_charges of 0.141–0.142).

§2 ALGORITHM multiwfn_program(owner) — Multiwfn of the settings («multiwfn_program») or found (multiwfn.find).
    compute_aim(parent, run, program, cores) — the critical points (multiwfn.run_topology, the answers of a molecule)
    gathered into the kinds of bonds (crystal_aim.bond_kinds), kept as aim-bonds.csv and aim-bonds.json in the folder of
    the run; compute_charges(...) — CM5 and Hirshfeld (crystal_aim.run_charges), kept as charges.csv. Both in
    run_waiting (the window keeps painting, Esc stops). aim_window / charges_window — the tables (qe_window.AimWindow,
    ChargesWindow).
§4 SPECIFICATION
    NOT_FOUND — the words when Multiwfn is not there; compute_aim -> (rows, meta); compute_charges -> (symbols, charges,
    version); ValueError for the user, InterruptedError after Esc.
"""

from pathlib import Path

from azimuth.i18n import tr

NOT_FOUND = ('Multiwfn не найден — установите его (macOS: brew install multiwfn; Windows: архив с sobereva.com/multiwfn) '
             'или укажите файл в «Компас → Поверхности → Программа Multiwfn…».')


def multiwfn_program(owner):
    from modules.spectrum.wavefunction import multiwfn

    settings = getattr(owner, 'preferences', None) or getattr(getattr(owner, 'w', None), 'preferences', None)
    try:
        configured = settings.value('multiwfn_program', '') if settings is not None else ''
    except Exception:  # a settings object of another kind
        configured = ''
    return multiwfn.find(configured or None)


def _ready(run, program, path=None):
    from modules.compass.chemistry import crystal_results

    if program is None:
        raise ValueError(tr(NOT_FOUND))
    path = path or crystal_results.multiwfn_file(run)
    if path is None:
        raise ValueError(tr('Нет волновой функции расчёта CP2K для Multiwfn.'))
    return path


def compute_aim(parent, run, program, cores=1, path=None):
    from azimuth.tasks import run_waiting
    from modules.compass.chemistry import crystal_results
    from modules.spectrum.wavefunction import crystal_aim, multiwfn

    path = _ready(run, program, path)
    cell, atoms = crystal_aim.geometry(Path(path).read_text(encoding='utf-8', errors='replace'))
    cps, _text, version, _ = run_waiting(parent, tr('Связи по AIM в Multiwfn…'), lambda step: multiwfn.run_topology(
        program, path, cores, step, timeout=7200))
    kinds = crystal_aim.bond_kinds(cps, atoms, cell)
    if not kinds:
        raise ValueError(tr('Multiwfn не нашёл связевых критических точек.'))
    rows = crystal_aim.table_rows(kinds)
    meta = {'census': crystal_aim.census(cps, cell), 'atoms': len(atoms), 'version': version or ''}
    try:
        crystal_results.write_aim(run.folder, rows, meta)
        crystal_results.write_aim_points(run.folder, crystal_aim.unique_points(cps, atoms, cell), cell)
    except OSError:
        pass
    return rows, meta


def compute_charges(parent, run, program, cores=1, path=None):
    from azimuth.tasks import run_waiting
    from modules.compass.chemistry import crystal_results
    from modules.spectrum.wavefunction import crystal_aim

    path = _ready(run, program, path)
    _cell, atoms = crystal_aim.geometry(Path(path).read_text(encoding='utf-8', errors='replace'))
    charges, _text, version = run_waiting(parent, tr('Заряды атомов в Multiwfn…'), lambda step: crystal_aim.run_charges(
        program, path, cores, step))
    if len(charges['cm5']) != len(atoms):
        raise ValueError(tr('Другое число атомов, чем у результата — заряды не взяты.'))
    try:
        crystal_results.write_charges(run.folder, atoms, charges)
    except OSError:
        pass
    return tuple(s for s, _ in atoms), charges, version


def aim_window(parent, name, rows, meta):
    from modules.compass.actions.qe_results import AimWindow

    census = meta.get('census') or {'poincare_hopf': 0}
    return AimWindow(parent, name, rows, census, meta.get('atoms', 0), meta.get('version'))


def charges_window(parent, name, symbols, charges, version=None):
    from modules.compass.actions.qe_results import ChargesWindow
    from modules.spectrum.wavefunction import crystal_aim

    return ChargesWindow(parent, name, crystal_aim.charge_rows([(s, None) for s in symbols], charges), version)

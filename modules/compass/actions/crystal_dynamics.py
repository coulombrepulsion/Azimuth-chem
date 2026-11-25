"""The frequencies at Γ and the critical points of a crystal on its model.

§1 PURPOSE
    The vibrations and the critical points of a crystal, shown as for a molecule. The modes of the last run
    «Частоты (точка Γ)» — of CP2K (cp2k_inputs, &VIBRATIONAL_ANALYSIS) or of Quantum ESPRESSO (ph.x and dynmat.x,
    qe_inputs.PHONON_TASK; with IR intensities for an insulator) — go to the page «Частоты» of
    the drawer of the result — the same table and animation as for a molecule, every atom of the block moving as its
    atom of the cell computed (crystal_model_map). The critical points of the density of the last run «Связи по AIM»
    (aim-points.json, crystal_analysis.compute_aim) go on the model as those of a molecule (viewer.aim): in every cell
    of the block, the bond points joined to their two atoms by straight paths.
§4 SPECIFICATION
    show_modes(studio, quiet=False) -> number of modes | None (quiet: at the opening of a project); show_points(studio)
    -> number of points | None (each says why not).
§7 TESTS tests/gui/test_gui_files.py::test_the_modes_and_the_critical_points_of_a_crystal.
"""

from types import SimpleNamespace

import numpy as np

from azimuth.i18n import tr


def _project(studio):
    from azimuth import crystal_projects

    path = studio.research_path() if hasattr(studio, 'research_path') else None
    return path if path and crystal_projects.is_crystal(path) else None


def _mapping(original, computed_rows, computed_count):
    from modules.compass.chemistry import crystal as cr
    from modules.compass.chemistry import crystal_field

    mapping = crystal_field.mapping_of(original, computed_rows)
    if mapping is None and computed_count == len(cr.unit_cell(original)):
        mapping = np.eye(3)  # the cell of the file itself, changed by an optimization
    return mapping


def modes_run(project):
    """The last run of the project with modes at Γ: CP2K (its *VIBRATIONS*.mol) or Quantum ESPRESSO (the Molden
    file of dynmat.x), or None."""
    from modules.compass.chemistry import crystal_results
    from modules.sextant.qe_inputs import PHONON_FILE

    for run in reversed(crystal_results.runs(project) if project else []):
        if (run.program == 'cp2k' and any(run.folder.glob('*VIBRATIONS*.mol'))) or (
                run.program == 'qe' and (run.folder / PHONON_FILE).is_file()):
            return run
    return None


def read_modes(run):
    """(atoms, modes, rows of the cell computed) of a run of modes_run."""
    from modules.spectrum.readers import cp2k, qe

    if run.program == 'qe':
        found = qe.phonons(run.folder)
        if found is None:
            raise ValueError(tr('Нет файла мод dynmat.x в папке расчёта.'))
        return found.atoms, found.modes, np.array(qe.input_cell(run.folder), float)
    atoms, modes = cp2k.vibrations(run.folder)
    return atoms, modes, np.array(cp2k._input_cell(run.folder / 'azimuth.inp'), float)


def _block(studio):
    shown = getattr(studio, 'crystal', None)
    if not shown:
        return None, None
    n = tuple(int(k) for k in shown[1]) if len(shown) > 1 and len(shown[1]) == 3 else (1, 1, 1)
    return shown[0], n


def show_modes(studio, quiet=False, project=None):
    """quiet — at the opening of a project: the modes loaded into the drawer without a word, the drawer not opened."""
    from modules.compass.chemistry import crystal_model_map

    original, _ = _block(studio)
    project = project or _project(studio)
    run = modes_run(project)
    if original is None or run is None:
        if quiet:
            return None
        studio.notify(tr('Нет расчёта частот этого кристалла — в Секстанте: CP2K или Quantum ESPRESSO, задача '
                         '«Частоты (точка Γ)» (лучше после оптимизации).'), 9000)
        return None
    try:
        atoms, modes, computed_rows = read_modes(run)
    except (OSError, ValueError, TypeError) as exc:
        if not quiet:
            studio.error(exc)
        return None
    mapping = _mapping(original, computed_rows, len(atoms))
    if mapping is None:
        if not quiet:
            studio.error(ValueError(tr('Ячейка расчёта не составлена из ячеек файла — частоты на модель не '
                                       'перенести.')))
        return None
    model = studio.molecule
    mapped = crystal_model_map.model_modes(modes, atoms, model, np.array(original.cell.vectors(), float), mapping,
                                           computed_rows)
    studio.trajectory_tool.load_result_modes(SimpleNamespace(modes=tuple(mapped), vibration_geometry=model))
    if quiet:
        return len(mapped)
    studio.trajectory_tool.set_trajectory_open(True, page='modes')
    studio.notify(tr('Частоты точки Γ ({}, {} мод) — в левой панели «Частоты»: выберите моду, атомы блока движутся '
                     'как атомы ячейки расчёта.').format(run.folder.name, len(mapped)), 9000)
    return len(mapped)


def show_points(studio, kinds=('bond',)):
    """kinds — the bond points only by default (a crystal is dense: its ring and cage points hide the model)."""
    from modules.compass.chemistry import crystal_model_map, crystal_results

    original, n = _block(studio)
    project = _project(studio)
    run = crystal_results.last(project, 'cp2k', having='aim-points.json') if project else None
    kept = crystal_results.read_aim_points(run.folder) if run is not None else None
    if original is None or kept is None:
        studio.notify(tr('Критических точек ещё нет: «Расчёт → Связи по AIM (Multiwfn)…» (для расчётов до 0.159.0 — '
                         '«Посчитать связи заново»).'), 9000)
        return None
    cell, points = kept
    points = [p for p in points if p[0] in kinds]
    computed_rows = np.array(cell, float)
    from modules.spectrum.wavefunction import crystal_aim

    path = crystal_results.multiwfn_file(run)
    count = len(crystal_aim.geometry(path.read_text(encoding='utf-8', errors='replace'))[1]) if path else 0
    mapping = _mapping(original, computed_rows, count)
    if mapping is None:
        studio.error(ValueError(tr('Ячейка расчёта не составлена из ячеек файла — точки на модель не перенести.')))
        return None
    model = studio.molecule
    placed = crystal_model_map.model_points(points, np.array(original.cell.vectors(), float), mapping, computed_rows, n)
    studio.viewer.aim = {
        'atoms': model.atoms,
        'points': [(kind, np.array(xyz)) for kind, xyz, _ in placed],
        'paths': crystal_model_map.bond_paths(placed, model),
        'selected': None,
        'labels': [],
    }
    studio.viewer.update()
    studio.surface_tool.sync_aim_buttons(True)
    kinds = {}
    for kind, _, _ in placed:
        kinds[kind] = kinds.get(kind, 0) + 1
    studio.notify(tr('Критические точки на модели: связевых {}, кольцевых {}, клеточных {}.').format(
        kinds.get('bond', 0), kinds.get('ring', 0), kinds.get('cage', 0)), 9000)
    return len(placed)

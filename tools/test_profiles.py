"""What each profile of tools/test.py runs (internal; TEST_FEEDBACK_PLAN.md §3, §7): one place for the composition.

QUICK — an explicit list (not «everything but the slow»: a new test does not grow it by itself, and nothing important
leaves the checks unseen): the reading and writing of data, the inputs of the programs, the outputs read, the store of
a project, the records of the runs, the translations — each under a second — and a few scenarios of the window.
Measured on about 25 s. It is a first signal, never «the tests passed».
AREAS — the tests of an area, of what it uses and of its window. An entry is a path (a folder, a file, a node id) or
(path, -k expression) — then only the tests of that file the expression selects. Every file of tests/ belongs to at
least one area (tools/test.py list says which do not).
NOT_IN_QUICK — what quick leaves out, printed with its result."""

QUICK = (
    'tests/core/test_core.py',
    'tests/core/test_i18n_patterns.py',
    'tests/compass/test_formats.py',
    'tests/compass/test_file_reading.py',
    'tests/sextant/test_inputs.py',
    'tests/sextant/test_qe_inputs.py',
    'tests/sextant/test_cp2k_inputs.py',
    'tests/spectrum/test_outputs.py',
    'tests/spectrum/test_orca601.py',
    'tests/spectrum/test_qe_reader.py',
    'tests/spectrum/test_cp2k_reader.py',
    'tests/projects/test_project_store.py',
    'tests/runtime/test_runtime_records.py',
    'tests/runtime/test_runtime_contracts.py',
    # the window: the default inputs, a broken edit, the spin, a Unicode file, a draft kept at the exit, a crystal tab
    'tests/gui/test_gui_sextant.py::test_default_workflow',
    'tests/gui/test_gui_sextant.py::test_invalid_edit_disables_export',
    'tests/gui/test_gui_sextant.py::test_spin_validation_in_ui',
    'tests/gui/test_gui_settings.py::test_atomic_unicode_save',
    'tests/projects/test_scenarios_t01_t04.py::test_t03_the_first_molecule_drawn_survives_the_exit_as_a_draft',
    'tests/gui/test_gui_files.py::test_a_crystal_is_a_project',
)

NOT_IN_QUICK = ('большинство сценариев окна', 'восстановление после сбоя (test_recovery)',
                'архитектурные границы', 'сервер и очереди', 'Multiwfn', 'Атлас и общее окно')

AREAS = {
    'compass': ('tests/compass', 'tests/gui/test_gui_compass.py', 'tests/gui/test_drop_overlay.py'),
    'crystal': ('tests/compass/test_crystal.py', 'tests/compass/test_crystal_steps.py', 'tests/spectrum/test_crystal_aim.py', 'tests/compass/test_crystal_results.py', 'tests/compass/test_crystal_adp.py', 'tests/compass/test_crystal_contacts.py',
                'tests/compass/test_crystal_examples.py', 'tests/compass/test_crystal_graphsets.py',
                'tests/compass/test_crystal_packing.py', 'tests/compass/test_crystal_rings.py',
                'tests/compass/test_crystal_symmetry.py', 'tests/compass/test_space_groups.py',
                'tests/compass/test_coordination.py', 'tests/compass/test_powder.py',
                'tests/sextant/test_qe_inputs.py', 'tests/sextant/test_qe_paths.py', 'tests/sextant/test_cp2k_inputs.py',
                'tests/spectrum/test_qe_reader.py', 'tests/spectrum/test_cp2k_reader.py', 'tests/spectrum/test_contacts.py',
                'tests/core/test_crystal_projects.py',
                ('tests/sextant/test_remote_job.py', 'quantum or cp2k'),
                ('tests/gui/test_gui_files.py', 'crystal or cif or quantum or cp2k or molecules_after or follows_the_kind '
                                                'or loose_molecule or no_kind')),
    'sextant': ('tests/sextant', 'tests/runtime', 'tests/gui/test_gui_sextant.py'),
    'server': ('tests/sextant/test_cluster.py', 'tests/sextant/test_remote.py', 'tests/sextant/test_remote_job.py',
               'tests/sextant/test_remote_submission.py', 'tests/sextant/test_server_access.py',
               'tests/sextant/test_server_files.py', 'tests/sextant/test_ssh.py', 'tests/sextant/test_transfer_t16.py',
               'tests/sextant/test_vpn.py', 'tests/sextant/test_unfinished.py', 'tests/runtime'),
    'spectrum': ('tests/spectrum', 'tests/gui/test_gui_spectrum.py', 'tests/gui/test_gui_multiwfn.py'),
    'projects': ('tests/projects', 'tests/runtime', 'tests/core/test_recovery.py', 'tests/core/test_crystal_projects.py',
                 'tests/gui/test_gui_files.py'),
    'runtime': ('tests/runtime',),
    'core': ('tests/core', 'tests/gui/test_gui_settings.py', 'tests/gui/test_theme_switch.py',
             'tests/gui/test_link_channel.py'),
    'hub': ('tests/hub', 'tests/atlas', 'tests/gui/test_link_channel.py'),
    'atlas': ('tests/atlas',),
    'gui': ('tests/gui',),
}

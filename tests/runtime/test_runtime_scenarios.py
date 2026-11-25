"""The acceptance scenarios T01–T24 of docs/architecture/PROJECT_RUNTIME_GUIDE.md §13 — at which stage each is
due and which tests cover it today (fully or a part of it). The table is checked against the files: a test named here
must exist. The status says honestly what is done: 'covered', 'partial' (a part of the behaviour is checked by older
tests, not the scenario as written), 'open'."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SCENARIOS = {
    'T01': ('B', 'covered', ['tests/projects/test_scenarios_t01_t04.py::test_t01_one_file_of_44_structures_opens_as_one_project_with_its_name_order_and_ids',
                             'tests/projects/test_scenarios_t01_t04.py::test_t01_a_trajectory_stays_the_steps_of_the_drawer',
                             'tests/runtime/test_runtime_session.py::test_t01_one_file_of_many_structures_is_one_project_with_its_name_order_and_ids']),
    'T02': ('B', 'covered', ['tests/projects/test_scenarios_t01_t04.py::test_t02_files_added_to_the_tab_keep_its_molecules_and_their_history',
                             'tests/runtime/test_runtime_session.py::test_t02_molecules_added_keep_the_others_and_name_the_project']),
    'T03': ('B', 'covered', ['tests/projects/test_scenarios_t01_t04.py::test_t03_the_first_molecule_drawn_survives_the_exit_as_a_draft',
                             'tests/projects/test_scenarios_t01_t04.py::test_t03_a_molecule_saved_to_a_file_or_unchanged_is_not_a_draft',
                             'tests/projects/test_scenarios_t01_t04.py::test_t03_the_exit_of_a_window_browsing_steps_asks_nothing',
                             'tests/projects/test_project_file_actions.py::test_preserves_drawn_molecule_when_new_project_is_closed',
                             'tests/runtime/test_runtime_session.py::test_t03_the_first_molecule_drawn_and_its_edit_survive_the_closing']),
    'T04': ('B', 'covered', ['tests/projects/test_scenarios_t01_t04.py::test_t04_an_edit_not_saved_is_what_the_calculation_gets_and_another_project_is_not',
                             'tests/projects/test_project_file_actions.py::test_exports_latest_coordinates_when_project_has_unsaved_edits',
                             'tests/runtime/test_runtime_session.py::test_t04_an_edit_not_saved_is_exported_and_another_project_is_not']),
    'T05': ('C', 'covered', ['tests/runtime/test_runtime_session.py::test_t05_a_finished_run_of_a_goes_to_its_attempt_while_b_is_edited',
                             'tests/runtime/test_runtime_delivery.py::test_t05_the_result_of_a_goes_to_the_tab_of_a_whichever_is_current',
                             'tests/projects/test_project_navigation.py::test_t05_the_result_goes_to_the_tab_of_its_attempt']),
    'T06': ('C', 'covered', ['tests/sextant/test_remote_submission.py::test_t06_closed_after_the_intent_before_the_sending']),
    'T07': ('C', 'covered', ['tests/runtime/test_runtime_states.py::test_a_lost_answer_of_sbatch_is_settled_only_with_a_reason',
                             'tests/sextant/test_remote_submission.py::test_t07_the_answer_lost_after_the_server_accepted',
                             'tests/sextant/test_remote_submission.py::test_t07_one_job_of_the_token_restores_the_link',
                             'tests/sextant/test_remote_submission.py::test_t07_several_jobs_of_the_token_stop_for_clarification',
                             'tests/sextant/test_remote_submission.py::test_t07_no_job_found_proves_nothing',
                             'tests/sextant/test_remote_submission.py::test_t07_the_answer_to_a_queue_lost_and_the_server_gone']),
    'T08': ('C', 'covered', ['tests/sextant/test_remote_submission.py::test_t08_a_full_disk_after_the_acceptance']),
    'T09': ('C', 'covered', ['tests/runtime/test_runtime_t09_t11.py::test_t09_a_server_out_of_reach_at_the_start_says_what_was_known_and_when',
                             'tests/runtime/test_runtime_t09_t11.py::test_t09_a_server_that_does_not_answer_is_opened_for_watching',
                             'tests/sextant/test_remote_job.py::test_a_lost_connection_does_not_end_the_job',
                             'tests/runtime/test_runtime_states.py::test_no_network_is_not_a_failure']),
    'T10': ('C', 'covered', ['tests/runtime/test_runtime_t09_t11.py::test_t10_an_output_that_comes_after_the_job_left_the_queue_is_a_success',
                             'tests/runtime/test_runtime_t09_t11.py::test_t10_a_job_gone_without_the_mark_fails_only_after_enough_evidence_never_succeeds',
                             'tests/runtime/test_runtime_t09_t11.py::test_t10_a_job_back_in_the_queue_is_watched_again',
                             'tests/runtime/test_runtime_t09_t11.py::test_t10_ended_states_of_slurm_are_not_running',
                             'tests/sextant/test_remote_job.py::test_a_queue_ended_before_its_calculation',
                             'tests/runtime/test_runtime_states.py::test_observations_of_an_old_watcher_twice_or_late_are_dropped']),
    'T11': ('C', 'covered', ['tests/runtime/test_runtime_t09_t11.py::test_t11_the_end_of_a_calculation_delivered_twice_is_one_record_and_no_analysis_again',
                             'tests/runtime/test_runtime_t09_t11.py::test_t11_the_end_of_a_row_delivered_twice_records_and_follows_nothing_again',
                             'tests/runtime/test_runtime_contracts.py::test_an_event_is_applied_once_and_never_older']),
    'T12': ('D', 'covered', ['tests/sextant/test_remote_job.py::test_a_queue_sent_at_once_runs_in_one_job',
                             'tests/sextant/test_remote_submission.py::test_the_group_has_a_manifest_and_markers_name_their_attempts',
                             'tests/sextant/test_remote_submission.py::test_t12_a_marker_of_another_attempt_is_not_this_one',
                             'tests/sextant/test_unfinished.py::test_a_server_queue_is_sent_at_once']),
    'T13': ('D', 'covered', ['tests/sextant/test_remote_job.py::test_a_queue_sent_at_once_runs_in_one_job']),
    'T14': ('D', 'covered', ['tests/runtime/test_scenario_t14.py::test_t14_five_failed_of_44_repeated_get_new_attempts_and_the_history_stays',
                             'tests/sextant/test_batch_retry.py::test_only_selected_rows_become_fresh_waiting_jobs']),
    'T15': ('E', 'covered', ['tests/spectrum/test_batch_qtaim.py::test_t15_one_molecule_ready_is_analysed_before_the_others']),
    'T16': ('C', 'covered', ['tests/sextant/test_transfer_t16.py::test_t16_a_cut_transfer_is_taken_again_and_only_the_whole_file_is_ready',
                             'tests/sextant/test_transfer_t16.py::test_t16_a_short_copy_scp_did_not_notice_is_found_by_its_size',
                             'tests/sextant/test_transfer_t16.py::test_t16_a_file_that_never_comes_whole_is_not_declared_ready',
                             'tests/sextant/test_remote_job.py::test_a_lost_moment_at_the_download_does_not_fail_a_finished_job']),
    'T17': ('E', 'covered', ['tests/spectrum/test_batch_qtaim.py::test_t17_a_failed_multiwfn_is_the_analysis_failure_not_the_calculation']),
    'T18': ('E', 'covered', ['tests/spectrum/test_batch_qtaim.py::test_t18_the_molecule_calculated_again_during_its_qtaim']),
    'T19': ('F', 'covered', ['tests/runtime/test_runtime_writer_lock.py::test_t19_a_second_process_reads_and_never_writes']),
    'T20': ('F', 'covered', ['tests/projects/test_project_store.py::test_t20_a_migration_cut_at_any_step_leaves_one_whole_project',
                             'tests/projects/test_project_store.py::test_t20_a_write_cut_inside_the_transaction_is_rolled_back']),
    'T21': ('F', 'covered', ['tests/runtime/test_runtime_writer_lock.py::test_t21_a_moved_project_keeps_its_id_and_a_copy_gets_its_own']),
    'T22': ('A', 'covered', ['tests/sextant/test_batch_purpose.py::test_one_formula_is_not_enough']),
    'T23': ('C', 'covered', ['tests/runtime/test_result_mismatch.py::test_each_change_is_named_and_the_result_stays_its_own',
                             'tests/runtime/test_result_mismatch.py::test_t23_a_new_charge_keeps_the_old_result_and_its_analysis_until_its_own_result',
                             'tests/projects/test_project_navigation.py::test_t23_a_result_of_other_data_is_marked_in_the_list_and_said']),
    'T24': ('G', 'open', []),  # on a real server — not an automatic test
}


def test_all_24_scenarios_have_a_stage_and_a_status():
    assert sorted(SCENARIOS) == [f'T{k:02d}' for k in range(1, 25)]
    for key, (stage, status, tests) in SCENARIOS.items():
        assert stage in 'ABCDEFG' and len(stage) == 1, key
        assert status in ('covered', 'partial', 'open'), key
        assert (status == 'open') == (not tests), key


def test_the_tests_named_exist():
    for key, (_, _, tests) in SCENARIOS.items():
        for node in tests:
            path, name = node.split('::')
            text = (ROOT / path).read_text(encoding='utf-8')
            assert re.search(rf'^\s*def {re.escape(name)}\(', text, re.M), f'{key}: {node}'


def test_the_registry_is_the_one_of_the_document():
    text = (ROOT / 'docs' / 'architecture' / 'RUNTIME_CONTRACTS.md').read_text(encoding='utf-8')
    for key, (stage, status, _) in SCENARIOS.items():
        assert re.search(rf'\|\s*{key}\s*\|\s*{stage}\s*\|\s*{status}\s*\|', text), key

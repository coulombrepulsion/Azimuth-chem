"""The tab of a result found by the ids of its attempt (azimuth/runtime/delivery.py; T05).

Oracle: the rules of §2 of the module, on plain objects standing for the tabs (no Qt)."""

from types import SimpleNamespace as Tab

from azimuth.runtime.delivery import result_tab


def test_t05_the_result_of_a_goes_to_the_tab_of_a_whichever_is_current():
    a = Tab(research_project_id='p', research_molecule_id='A')
    b = Tab(research_project_id='p', research_molecule_id='B')
    # A was started from its tab, which was closed and opened again (another object); B is the tab on screen
    again = Tab(research_project_id='p', research_molecule_id='A')
    assert result_tab([b, again], 'p', 'A', started=a, active_project_id='p') == (again, 'found')
    assert result_tab([a, b], 'p', 'A', started=b, active_project_id='p') == (a, 'found')  # not the tab it started in


def test_a_closed_tab_of_the_molecule_is_opened_again_or_a_new_tab_is_made():
    b = Tab(research_project_id='p', research_molecule_id='B')
    assert result_tab([b], 'p', 'A', active_project_id='p') == (None, 'open')
    assert result_tab([b], 'p', 'A', active_project_id='other') == (None, 'new')


def test_a_molecule_of_another_project_with_the_same_id_is_not_taken():
    other = Tab(research_project_id='q', research_molecule_id='A')
    assert result_tab([other], 'p', 'A', active_project_id='p') == (None, 'open')


def test_outside_a_project_the_tab_it_started_from_while_it_is_open():
    start = Tab(research_project_id=None, research_molecule_id='')
    twin = Tab(research_project_id=None, research_molecule_id='')  # equal, but another tab
    assert result_tab([twin, start], None, None, started=start) == (start, 'started')
    assert result_tab([twin], None, None, started=start) == (None, 'new')
    assert result_tab([], None, None) == (None, 'new')

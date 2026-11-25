"""Where the result of a calculation goes: found by the ids of its attempt at the end, not by the tab it was started
from (docs/architecture/PROJECT_RUNTIME_GUIDE.md §3, RUNTIME_CONTRACTS.md §4; scenario T05).

§1 PURPOSE
    The result of a calculation opened in job_document — the Python object of the tab current at the start. A tab
    closed meanwhile, or the molecule of a project shown in another tab, or a tab of the same molecule opened again,
    sent the result to the wrong place or to a fresh tab without its molecule.
§2 RULES
    1. A calculation of a project (its link: the manifest and the molecule id, project_actions.register_project_job):
       the tab whose (project id, molecule id) are those of the attempt — whichever tab it is now; none → 'open' (the
       molecule is opened in its own tab, then the result goes there) when its project is the active one, else 'new'
       (a tab of its own; the attempt in the project is recorded by its id all the same).
    2. A calculation outside a project: the tab it was started from while it is still open, else 'new'.
    3. Identity is `is`, never ==.
§3 INTERFACE result_tab(documents, project_id, molecule_id, started, active_project_id) -> (document | None, how)
    with how ∈ 'found' | 'started' | 'open' | 'new'.
§4 TESTS tests/runtime/test_runtime_delivery.py.
"""


def result_tab(documents, project_id, molecule_id, started=None, active_project_id=None):
    documents = list(documents)
    if project_id and molecule_id:
        for document in documents:
            if (getattr(document, 'research_project_id', None) == project_id
                    and getattr(document, 'research_molecule_id', None) == molecule_id):
                return document, 'found'
        return None, ('open' if active_project_id == project_id else 'new')
    if started is not None and any(d is started for d in documents):
        return started, 'started'
    return None, 'new'

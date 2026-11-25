"""Identity, commands and events of the runtime; who owns which data (PROJECT_RUNTIME_GUIDE.md §3, §4, §11).

§1 PURPOSE
    A result of a calculation, an answer of the server or of a worker thread must find its molecule and attempt by their
    ids — not by the tab on screen, the row of a table, a title, a path or id() of a Python object. These are the forms
    such messages take from stage B on, and the rules a receiver keeps.
§2 RULES Ids: new_id() — 32 hex digits, made before any outside action (sending, writing a file). Command: command_id
    (the same one delivered again returns the operation already made), expected_revision (a change against an older
    revision is refused, CommandError 'stale_revision'). Event: project_id, entity_id, project_revision, event_id, kind,
    payload — published after the change is written. Delivery (the receiving side): an event_id seen before is dropped
    ('duplicate'); an event of a project revision older than the last applied one is dropped ('stale'); the rest is
    applied — also for a project whose tab is closed (the receiver is the model of the project, not the window). OWNERS
    — the table of §3 of the guide: the data, its owner, what the interface sees.
§3 INTERFACE
    new_id(); Command(name, command_id, expected_revision=None, arguments={}); CommandError(code, message);
    Event(project_id, entity_id, project_revision, kind, payload={}, event_id=new_id()); Delivery(); .offer(event) ->
    'applied' | 'duplicate' | 'stale'; .revision(project_id) -> int; OWNERS: ((data, owner, seen by the interface), …).
§4 TESTS
    tests/runtime/test_runtime_contracts.py.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def new_id():
    return uuid.uuid4().hex


@dataclass(frozen=True)
class Command:
    name: str
    command_id: str
    expected_revision: int | None = None
    arguments: dict = field(default_factory=dict, hash=False, compare=False)


class CommandError(Exception):
    CODES = ('stale_revision', 'not_found', 'invalid', 'busy', 'uncertain_submission', 'backend')

    def __init__(self, code, message=''):
        if code not in self.CODES:
            raise ValueError(f'unknown error code {code!r}')
        super().__init__(f'{code}: {message}' if message else code)
        self.code, self.message = code, message


@dataclass(frozen=True)
class Event:
    project_id: str
    entity_id: str
    project_revision: int
    kind: str
    payload: dict = field(default_factory=dict, hash=False, compare=False)
    event_id: str = field(default_factory=new_id)


class Delivery:
    """The receiving side of events: each applied once, never older than what is applied."""

    def __init__(self):
        self._seen = set()
        self._revision = {}

    def revision(self, project_id):
        return self._revision.get(project_id, -1)

    def offer(self, event):
        if event.event_id in self._seen:
            return 'duplicate'
        if event.project_revision < self.revision(event.project_id):
            self._seen.add(event.event_id)
            return 'stale'
        self._seen.add(event.event_id)
        self._revision[event.project_id] = event.project_revision
        return 'applied'


# the guide, §3: the data, its owner, what the interface sees
OWNERS = (
    ('the list of molecules, their order and names', 'ProjectSession / ProjectRepository',
     'a snapshot of the list and the id of the chosen molecule'),
    ('coordinates and settings not saved yet', 'WorkingMolecule of ProjectSession',
     'an editable projection with its revision number'),
    ('what an attempt was sent with', 'InputSnapshot (never changed)', 'a view of the input of the attempt'),
    ('the state of a remote run', 'RunCoordinator, kept by ProjectRepository',
     'the last confirmed state and how old it is'),
    ('files and results', 'ArtifactStore / ResultRecord', 'the properties available and why the others are not'),
    ('camera, open panels, scrolling', 'WorkspaceState', 'only the view — never a source of scientific data'),
)

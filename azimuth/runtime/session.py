"""The open project: one ProjectSession per project_id over the JSON project (stage B of
docs/architecture/PROJECT_RUNTIME_GUIDE.md).

§1 PURPOSE
    A molecule of a project lived in two places that every command chose between by itself: project.qcc (saved) and
    the document of its tab (edits not saved yet, or the model on screen). Export took the model on screen for one
    molecule and the file for the others, saving wrote whatever documents were found — 0.105.18 mended the
    consequences (molecules of another project in an export, old coordinates). The session is the one owner of the
    working state of the molecules of a project: the editors push their edits into it (edit_molecule), the commands
    read from it (structure, export_snapshot, snapshot), save() writes it. Its answers never depend on the tab in front.
§2 RULES
    Identity: project_id from the file; one session per project_id (SessionRegistry: the same path — the same session;
    another path with the same id — ProjectConflict, a copy must get its own id). Revisions: the project revision is
    kept in the project ('revision', 0 for older files; in project.sqlite) and grows with every change the session
    writes; a molecule has
    working_revision (its last edit) and saved_revision (written). A command may give the revision it expects:
    another one — CommandError('stale_revision'). Writing: through projects.edit (it re-reads the file, so changes
    of others — the attempts a queue records — are kept); only the structure, the program, the formal charges and
    the flatness of the molecules edited are written. Adding molecules is written at once (a draft is kept for
    recovery, PROJECT_RUNTIME_GUIDE.md §1). The name: a project opened from one file is named after it; molecules added
    to a project of one molecule whose name was not chosen by the user make it «Новый проект» (§1).
§3 INTERFACE MoleculeRecord(molecule, calc, kind='orca', name='', constraints=(), labels=None, formal=(), flat=False,
    props={}, source='', skeleton=''); WorkingState(molecule, calc, kind, constraints, labels, formal, flat).
    ProjectSession(path): .project_id, .path, .revision, .name, .snapshot() -> ProjectSnapshot(project_id, revision,
    name, molecules=(MoleculeView(id, name, molecule, calc, kind, formal, flat, working_revision, saved_revision), …)),
    .ids(), .structure(id) -> WorkingState, .add_molecules(records, expected_revision=None, source_name=None,
    naming=True) -> [id], .edit_molecule(id, expected_revision=None, **changes) -> working revision, .dirty() -> [id],
    .export_snapshot(ids=None) -> ((id, name, Molecule), …) — the molecules the user added, in project order,
    .queue_view() -> ((id, name, WorkingState, props, flat), …) and .working_key(), .save(expected_revision=None) ->
    [ids written], .rename(name), .discard(id); .remove_molecules(ids, expected_revision=None) -> [(position, entry)],
    .restore_molecules(removed) -> [id]. SessionRegistry(): .open(path) -> ProjectSession, .get(project_id),
    .close(project_id, save=True) -> [ids written], .sessions()..open takes the writer lock of the project
    (azimuth/runtime/writer_lock.py); held by another process → session.read_only = who holds it (writing raises
    projects.ProjectLocked), else None; .close lets it go.
§4 TESTS
    tests/runtime/test_runtime_session.py — T01–T04 of the guide at the level of the session (no Qt).
"""

from __future__ import annotations

import threading
from dataclasses import dataclass, field, replace
from pathlib import Path

from azimuth import projects
from azimuth.i18n import tr
from azimuth.runtime.contracts import CommandError


@dataclass(frozen=True)
class MoleculeRecord:
    molecule: object
    calc: object
    kind: str = 'orca'
    name: str = ''
    constraints: tuple = ()
    labels: object = None
    formal: tuple = ()
    flat: bool = False
    props: dict = field(default_factory=dict, hash=False, compare=False)
    source: str = ''
    skeleton: str = ''


@dataclass(frozen=True)
class WorkingState:
    molecule: object
    calc: object
    kind: str
    constraints: tuple = ()
    labels: object = None
    formal: tuple = ()
    flat: bool = False


@dataclass(frozen=True)
class MoleculeView:
    id: str
    name: str
    molecule: object
    calc: object
    kind: str
    formal: tuple
    flat: bool
    working_revision: int
    saved_revision: int


@dataclass(frozen=True)
class ProjectSnapshot:
    project_id: str
    revision: int
    name: str
    molecules: tuple


class ProjectConflict(ValueError):
    pass


class ProjectSession:
    def __init__(self, path):
        project = projects.Project.view(path)
        self.path = project.path
        self.project_id = project.data['id']
        self._lock = threading.RLock()
        self._working = {}  # id: WorkingState — edits not written yet
        self.read_only = None  # who else writes the project (SessionRegistry.open), or None
        self._revisions = {}  # id: [working, saved]

    # -- reading ------------------------------------------------------------------------------------------------
    def held(self):
        """Within `with session.held():` the project is looked at once; for reads only (the edits of the tabs given
        before a save), never around a write."""
        from contextlib import contextmanager

        @contextmanager
        def block():
            with self._lock:
                outer = self.__dict__.get('_held')
                if outer is None:
                    self._held = self._project()
                try:
                    yield self
                finally:
                    if outer is None:
                        self._held = None

        return block()

    def _project(self):
        held = self.__dict__.get('_held')
        if held is not None:
            return held
        project = projects.Project.view(self.path)
        if project.data['id'] != self.project_id:
            raise ProjectConflict(tr('В папке проекта теперь другой проект.'))
        return project

    @property
    def revision(self):
        return int(self._project().data.get('revision', 0))

    @property
    def name(self):
        return self._project().data.get('name', '')

    def ids(self):
        return [entry['id'] for entry in self._project().molecules]

    def _saved_state(self, project, entry):
        """The molecule as the project keeps it. Read once — the structure by the project's
        own cache, the constraints and labels from the same record — and kept by its text for the next time."""
        import json

        key = (json.dumps(entry['structure'], sort_keys=True), entry.get('kind', 'orca'),
               tuple(entry.get('formal', ())), bool(entry.get('flat')))
        cache = self.__dict__.setdefault('_saved', {})
        found = cache.get(key)
        if found is not None:
            return replace(found, labels=dict(found.labels))  # a window may change the labels it was given
        from azimuth.core import validate_constraints

        molecule, calc = project.read_structure(entry['structure'])
        data = entry['structure']
        try:
            constraints = tuple(validate_constraints(data.get('constraints') or (), len(molecule.atoms)))
            raw = data.get('labels') or {}
            if not isinstance(raw, dict):
                raise TypeError
            labels = {int(k): str(v)[:40] for k, v in raw.items() if 0 <= int(k) < len(molecule.atoms) and str(v)}
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(tr('Повреждённый файл проекта «Азимута».')) from exc
        state = WorkingState(molecule, calc, key[1], constraints, labels, key[2], key[3])
        if len(cache) > 2000:
            cache.clear()
        cache[key] = state
        return replace(state, labels=dict(labels))

    def structure(self, ident):
        """The working state of the molecule: its edit not written yet, else what the project keeps."""
        with self._lock:
            if ident in self._working:
                return self._working[ident]
            project = self._project()
            return self._saved_state(project, project.entry(ident))

    def _revision_of(self, ident):
        return self._revisions.setdefault(ident, [0, 0])

    def snapshot(self):
        with self._lock:
            project = self._project()
            views = []
            for entry in project.molecules:
                state = self._working.get(entry['id']) or self._saved_state(project, entry)
                working, saved = self._revision_of(entry['id'])
                views.append(MoleculeView(entry['id'], entry['name'], state.molecule, state.calc, state.kind,
                                          tuple(state.formal), state.flat, working, saved))
            return ProjectSnapshot(self.project_id, int(project.data.get('revision', 0)),
                                   project.data.get('name', ''), tuple(views))

    def queue_view(self):
        """The molecules a queue of the project takes (projects.queueable — not the ion and the complexes of a
        binding queue), in project order, with their working state: ((id, name, WorkingState, props, flat), …). A
        molecule not edited keeps the same Molecule object while project.qcc is unchanged (Project.view and its parsed
        structures), so the rows chosen for a queue keep their identity."""
        with self._lock:
            project = self._project()
            found = []
            for entry in projects.queueable(project):
                state = self._working.get(entry['id']) or self._saved_state(project, entry)
                found.append((entry['id'], entry['name'], state, dict(entry.get('props', {})), bool(state.flat)))
            return tuple(found)

    def working_key(self):
        """What changes when an edit not saved changes — the working revisions of the molecules edited."""
        with self._lock:
            return tuple(sorted((i, self._revision_of(i)[0]) for i in self._working))

    def dirty(self):
        with self._lock:
            return [i for i in self.ids() if i in self._working]

    def export_snapshot(self, ids=None):
        """The molecules the user added (not the ion and complexes of a binding queue), in project order, with their
        working coordinates — of this project only, whatever tab is on screen."""
        with self._lock:
            project = self._project()
            chosen = None if ids is None else set(ids)
            found = []
            for entry in projects.queueable(project):
                if chosen is not None and entry['id'] not in chosen:
                    continue
                state = self._working.get(entry['id']) or self._saved_state(project, entry)
                if state.molecule is not None and state.molecule.atoms:
                    found.append((entry['id'], entry['name'] or state.molecule.title or state.molecule.formula,
                                  state.molecule))
            return tuple(found)

    # -- changing -----------------------------------------------------------------------------------------------
    def _expect(self, expected):
        if expected is not None and expected != self.revision:
            raise CommandError('stale_revision', f'expected {expected}, project is at {self.revision}')

    def add_molecules(self, records, expected_revision=None, source_name=None, naming=True):
        """Records written into the project at once; their ids in order. source_name — the project was opened from
        this one file: it is named after it (§2); naming=False — the name is left as it is (a molecule of the tab put
        into its project before a calculation)."""
        with self._lock:
            self._expect(expected_revision)
            added = []
            with projects.edit(self.path) as project:
                before = len(projects.queueable(project))
                for record in records:
                    entry = project.add(record.molecule, record.calc, record.kind, record.name or None,
                                        record.constraints, record.labels)
                    entry.update(formal=list(record.formal), flat=bool(record.flat), props=dict(record.props))
                    if record.source:
                        entry['source'] = record.source
                    if record.skeleton:
                        entry['skeleton'] = record.skeleton
                    added.append(entry['id'])
                    self._revisions[entry['id']] = [0, 0]
                if not naming:
                    pass
                elif source_name is not None and before == 0:
                    project.data['name'] = source_name
                elif added and before == 1 and not project.data.get('named'):
                    project.data['name'] = tr('Новый проект')
                if added:
                    project.data['revision'] = int(project.data.get('revision', 0)) + 1
            return added

    def edit_molecule(self, ident, expected_revision=None, **changes):
        """An edit of the molecule kept in the session (written by save()); the working revision of the molecule.
        changes: molecule, calc, kind, constraints, labels, formal, flat. The same state again is not a new revision."""
        with self._lock:
            if expected_revision is not None and expected_revision != self._revision_of(ident)[0]:
                raise CommandError('stale_revision', f'molecule {ident[:8]}: expected {expected_revision}, '
                                                     f'is at {self._revision_of(ident)[0]}')
            current = self.structure(ident)
            unknown = set(changes) - set(WorkingState.__dataclass_fields__)
            if unknown:
                raise CommandError('invalid', f'unknown fields {sorted(unknown)}')
            if 'formal' in changes:
                changes['formal'] = tuple(changes['formal'] or ())
            if 'constraints' in changes:
                changes['constraints'] = tuple(changes['constraints'] or ())
            new = replace(current, **changes)
            revision = self._revision_of(ident)
            if new != current:
                self._working[ident] = new
                revision[0] += 1
            return revision[0]

    def discard(self, ident):
        with self._lock:
            self._working.pop(ident, None)
            revision = self._revision_of(ident)
            revision[0] = revision[1]

    def remove_molecules(self, ids, expected_revision=None):
        """The molecules taken out of the project (projects.remove_molecules: with what a binding queue made
        for them; refused while one is calculated), their edits not written forgotten; [(position, entry)] for
        restore_molecules."""
        with self._lock:
            self._expect(expected_revision)
            with projects.edit(self.path) as project:
                removed = projects.remove_molecules(project, ids)
                project.data['revision'] = int(project.data.get('revision', 0)) + 1
            for _, entry in removed:
                self._working.pop(entry['id'], None)
                self._revisions.pop(entry['id'], None)
            return removed

    def restore_molecules(self, removed):
        """The molecules removed put back at their places; their ids."""
        with self._lock, projects.edit(self.path) as project:
            ids = projects.restore_molecules(project, removed)
            project.data['revision'] = int(project.data.get('revision', 0)) + 1
            for ident in ids:
                self._revisions[ident] = [0, 0]
            return ids

    def rename(self, name):
        with self._lock, projects.edit(self.path) as project:
            project.data.update(name=name, named=True)
            project.data['revision'] = int(project.data.get('revision', 0)) + 1

    def save(self, expected_revision=None):
        """The edits written; the ids written (an unchanged molecule is not rewritten)."""
        with self._lock:
            self._expect(expected_revision)
            if not self._working:
                return []
            written = []
            with projects.edit(self.path) as project:
                for ident, state in list(self._working.items()):
                    try:
                        entry = project.entry(ident)
                    except ValueError:  # taken out of the project meanwhile
                        self._working.pop(ident)
                        continue
                    if state.molecule is None or not state.molecule.atoms:
                        continue
                    entry['structure'] = project.structure(state.molecule, state.calc, state.constraints, state.labels)
                    entry['kind'] = state.kind
                    entry['formal'] = list(state.formal) if len(state.formal) == len(state.molecule.atoms) else []
                    entry['flat'] = bool(state.flat)
                    written.append(ident)
                if written:
                    project.data['revision'] = int(project.data.get('revision', 0)) + 1
            for ident in written:
                self._working.pop(ident, None)
                revision = self._revision_of(ident)
                revision[1] = revision[0]
            return written


class SessionRegistry:
    """One session per project_id — whatever tab, section or window asks."""

    def __init__(self):
        self._by_id = {}
        self._lock = threading.Lock()

    def open(self, path):
        path = Path(path)
        if path.is_dir():
            path /= projects.MANIFEST
        project = projects.Project.view(path)
        ident = project.data['id']
        with self._lock:
            session = self._by_id.get(ident)
            if session is not None:
                if session.path != project.path:
                    raise ProjectConflict(tr('Этот проект уже открыт из другой папки: {}. Копии нужен свой '
                                             'идентификатор («Сохранить как…»).').format(session.path.parent))
                return session
            session = ProjectSession(project.path)
            # the writer of the project across processes; another one holds it → read only
            from azimuth.runtime import writer_lock

            session.read_only = None if writer_lock.acquire(project.path.parent) else (
                writer_lock.holder(project.path.parent) or {'host': '?', 'pid': '?'})
            self._by_id[ident] = session
            return session

    def get(self, project_id):
        with self._lock:
            return self._by_id.get(project_id)

    def sessions(self):
        with self._lock:
            return list(self._by_id.values())

    def close(self, project_id, save=True):
        with self._lock:
            session = self._by_id.pop(project_id, None)
        if session is None:
            return []
        try:
            return session.save() if save and not session.read_only else []
        finally:
            if not session.read_only:
                from azimuth.runtime import writer_lock

                writer_lock.release(session.path.parent)

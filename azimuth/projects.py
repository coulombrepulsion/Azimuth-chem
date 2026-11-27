"""Portable research projects: molecules, immutable calculation attempts and current usable results.

Contract (0.100): project.qcc plus calculations/ form one movable folder. Paths inside the manifest are relative
and cannot escape that folder. Each molecule has a stable UUID; attempts have their own IDs and input/settings
snapshots. The latest registered successful attempt with a readable geometry is current. A failed or unfinished
attempt never replaces it; energies of different methods are not ranked together. Existing folders are copied on
import, never moved. Batch and single-job links are relative to their own folders. All metadata writes are atomic;
edit() serializes threads and re-reads the file before mutation. Reading never starts calculations or contacts servers.
Legacy structure .qcc data is reused within each molecule record; scientific readers/formulas are unchanged.
"""

from contextlib import contextmanager
import copy
import re
from dataclasses import replace
import json
import hashlib
import os
from pathlib import Path
import shutil
import tempfile
import threading
from uuid import uuid4

from azimuth import project_store
from azimuth.core import project_text, read_project, read_xyz
from modules.sextant import batch

FORMAT = 'azimuth-research-project'
MANIFEST = 'project.qcc'
_locks = {}
_guard = threading.Lock()
_views = {}  # str(path) -> ((mtime_ns, size, inode), Project) — read-only views, see Project.view


def atomic_json(path, data):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix='.project-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as file:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


class ProjectLocked(ValueError):
    """Another process of Azimuth writes this project (azimuth/runtime/writer_lock.py) — here it is read only."""


def locked_by(path):
    """Who else writes the project of path (host, pid, since), or None."""
    from azimuth.runtime import writer_lock

    return writer_lock.holder(Path(path).resolve().parent)


def stamp(path):
    """What tells that the project changed on disk: the descriptor (time, size, inode) and, for a project in
    SQLite, the generation of its database (it grows with every write)."""
    path = Path(path)
    if path.is_dir():
        path /= MANIFEST
    stat = path.stat()
    key = (stat.st_mtime_ns, stat.st_size, stat.st_ino)
    database = path.parent / project_store.DATABASE
    return key + ((project_store.generation(database),) if database.is_file() else (None,))


@contextmanager
def edit(path):
    key = str(Path(path).resolve())
    other = locked_by(path)  # one writer across processes
    if other is not None:
        from azimuth.i18n import tr

        raise ProjectLocked(tr('Проект открыт для записи в другом окне Азимута ({}, процесс {}). Здесь — только '
                               'просмотр: закройте его там, чтобы менять здесь.').format(other.get('host', '?'),
                                                                                      other.get('pid', '?')))
    with _guard:
        lock = _locks.setdefault(key, threading.RLock())
    with lock:
        # from the checked view (no second parse of every structure) and written only when something changed —
        # the choice of a molecule, the mode or a tick rewrote project.qcc each time, even unchanged
        base = Project.view(path)
        project = Project(base.path, copy.deepcopy(base.data), base.storage, base.generation)
        project._parsed = dict(base._parsed)
        project._stored = base.data  # what the database holds — save() writes only what differs
        yield project
        if project.data != base.data:
            project.save()


class Project:
    def __init__(self, path, data, storage='sqlite', generation=0):
        self.path, self.data = Path(path).resolve(), data
        self._parsed = {}  # the structures read, by their JSON (the Molecule objects are immutable)
        # 'sqlite' — the metadata in project.sqlite (azimuth/project_store.py); 'json' — a project of
        # version 1 not written since (it moves into SQLite at its first write)
        self.storage = storage
        self.generation = generation

    @property
    def database(self):
        return self.root / project_store.DATABASE

    @property
    def root(self):
        return self.path.parent

    @property
    def molecules(self):
        return self.data['molecules']

    @classmethod
    def create(cls, folder):
        folder = Path(folder).resolve()
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / MANIFEST
        if path.exists():
            raise ValueError('В этой папке уже есть проект.')
        project = cls(path, {'format': FORMAT, 'version': 1, 'id': uuid4().hex,
                             'name': folder.name, 'molecules': [], 'batches': [], 'imports': {}}, storage='new')
        (folder / 'calculations').mkdir(exist_ok=True)
        project.save()
        return project

    @classmethod
    def view(cls, path):
        """The project for reading, kept until project.qcc changes on disk (its time, size and inode — a write
        replaces the file atomically). Selecting a molecule, the mode, the list, the queue read it many times a second;
        Project.load parsed every structure each time (44 ligands with their complexes: tens of parses per click). The
        object is shared: never change it — edit() and load() give a fresh one to change."""
        path = Path(path)
        if path.is_dir():
            path /= MANIFEST
        key = stamp(path)
        name = str(path.resolve())
        with _guard:
            hit = _views.get(name)
        if hit is not None and hit[0] == key:
            return hit[1]
        project = cls.load(path, parsed=hit[1]._parsed if hit is not None else None)
        with _guard:
            _views[name] = (stamp(path) if project.storage == 'json' else key[:3] + (project.generation,), project)
        return project

    @classmethod
    def load(cls, path, parsed=None):
        """parsed: the structures already read by an earlier view (by their JSON; the molecules are
        immutable) — an unchanged structure is not parsed again after a write of the project."""
        path = Path(path)
        if path.is_dir():
            path /= MANIFEST
        data = json.loads(path.read_text(encoding='utf-8-sig'))
        storage, generation = 'json', 0
        if isinstance(data, dict) and data.get('format') == FORMAT and project_store.is_descriptor(data):
            data, generation = project_store.read(path.parent / project_store.DATABASE)
            storage = 'sqlite'
        if not isinstance(data, dict) or data.get('format') != FORMAT or data.get('version') != 1:
            raise ValueError('Неизвестный формат проекта с расчётами.')
        if not isinstance(data.get('molecules'), list) or not isinstance(data.get('batches'), list):
            raise ValueError('Повреждён список молекул или расчётов проекта.')
        project = cls(path, data, storage, generation)
        if parsed:
            project._parsed = dict(parsed)
        ids = [entry['id'] for entry in project.molecules]
        if len(ids) != len(set(ids)):
            raise ValueError('Повторяющиеся идентификаторы молекул проекта.')
        for entry in project.molecules:
            molecule, _ = project.read_structure(entry['structure'])
            formal = entry.get('formal', [])
            if formal and (len(formal) != len(molecule.atoms) or any(type(q) is not int for q in formal)):
                raise ValueError('Повреждены формальные заряды молекулы.')
            if entry.get('source'):
                project.absolute(entry['source'])
            attempts = entry['attempts']
            if not isinstance(attempts, list) or len({a['id'] for a in attempts}) != len(attempts):
                raise ValueError('Повреждена история попыток.')
            for attempt in attempts:
                for field in ('folder', 'output', 'batch'):
                    if attempt.get(field):
                        project.absolute(attempt[field])
        for folder in data['batches']:
            project.absolute(folder)
        return project

    def save(self):
        """Into project.sqlite in one transaction; a project of version 1 is moved into it first
        (project_store.migrate: the old project.qcc stays in force until the database is whole)."""
        if self.storage == 'sqlite':
            stored, self._stored = getattr(self, '_stored', None), None
            self.generation = project_store.write(self.database, self.data, stored, self.generation if stored else None)
            return
        project_store.migrate(self.path, self.data, atomic_json, FORMAT)
        self.storage = 'sqlite'
        self.generation = project_store.generation(self.database)

    def relative(self, path):
        return Path(path).resolve().relative_to(self.root).as_posix() if path else ''

    def absolute(self, path):
        raw = Path(path)
        if raw.is_absolute():
            raise ValueError('Путь внутри проекта должен быть относительным.')
        result = (self.root / raw).resolve()
        result.relative_to(self.root)
        return result

    def entry(self, ident):
        entry = next((e for e in self.molecules if e['id'] == ident), None)
        if entry is None:
            raise ValueError('Молекула не найдена в проекте.')
        return entry

    def structure(self, molecule, calc, constraints=(), labels=None):
        """Archive the optional starting wavefunction; persisted settings have project-relative paths."""
        if calc.guess:
            source = Path(calc.guess)
            if not source.is_absolute():
                source = self.absolute(calc.guess)
            source = source.resolve()
            try:
                relative = self.relative(source)
            except ValueError:
                digest = hashlib.sha256(source.read_bytes()).hexdigest()
                target = self.root / 'assets' / digest / source.name
                target.parent.mkdir(parents=True, exist_ok=True)
                if not target.is_file():
                    shutil.copy2(source, target)
                relative = self.relative(target)
            calc = replace(calc, guess=relative)
        return json.loads(project_text(molecule, calc, constraints, labels))

    def read_structure(self, data):
        text = json.dumps(data, sort_keys=True)
        found = self._parsed.get(text)
        if found is not None:
            return found
        molecule, calc = read_project(json.dumps(data))
        if calc.guess:
            calc = replace(calc, guess=str(self.absolute(calc.guess)))
        self._parsed[text] = (molecule, calc)
        return molecule, calc

    def add(self, molecule, calc, kind='orca', name=None, constraints=(), labels=None):
        entry = {'id': uuid4().hex, 'name': name or molecule.title or molecule.formula,
                 'structure': self.structure(molecule, calc, constraints, labels),
                 'kind': kind, 'attempts': [], 'current': None}
        self.molecules.append(entry)
        return entry

    def current(self, entry):
        return next((a for a in entry['attempts'] if a['id'] == entry.get('current')), None)

    def record(self, ident, attempt_id, molecule, calc, kind, state, folder='', output='', batch_path='', note=''):
        entry = self.entry(ident)
        attempt = next((a for a in entry['attempts'] if a['id'] == attempt_id), None)
        if attempt is None:
            snapshot = self.structure(molecule, calc)
            attempt = {'id': attempt_id, 'input': snapshot, 'requested_input': snapshot,
                       'kind': kind, 'calculation': snapshot['calculation']}
            entry['attempts'].append(attempt)
        if not attempt.get('submitted', bool(attempt.get('folder'))):
            attempt['input'] = self.structure(molecule, calc)
            attempt['calculation'] = attempt['input']['calculation']
            attempt['submitted'] = bool(folder)
        attempt.update(state=state, folder=self.relative(folder), output=self.relative(output),
                       batch=self.relative(batch_path), note=note)
        stamp = None
        if state == 'done' and output and Path(output).is_file():
            stat = Path(output).stat()
            stamp = [stat.st_size, stat.st_mtime_ns]
        # an output read before is not read again — unless it gave nothing then: an older version may not have read it
        # (the feedback of 2026-11-18: an xtb run of methane stayed «геометрия не прочитана» for good, Spectrum empty)
        cached = stamp is not None and attempt.get('stamp') == stamp and bool(attempt.get('usable'))
        if not cached:
            attempt['usable'] = False
        if stamp is not None and not cached:
            text = Path(output).read_text(encoding='utf-8', errors='replace')
            energy, geometry, gibbs, heat = batch.result_of(kind, text, output)
            if geometry is not None:
                try:
                    read_xyz(geometry.xyz())
                except ValueError as exc:
                    attempt['note'] = str(exc)
                    geometry = None
            if geometry is not None:
                attempt.update(usable=True, geometry=batch._molecule_dict(geometry), energy=energy, gibbs=gibbs, heat=heat)
                self.adopt_geometry(entry, attempt, geometry, kind, text)
        attempt['stamp'] = stamp
        entry['current'] = current_of(entry)
        return attempt

    def choose(self, ident, attempt_id):
        """This usable calculation of the molecule is its current one — until a newer one gives a result
        (current_of). False when it gave none."""
        entry = self.entry(ident)
        attempt = next((a for a in entry['attempts'] if a['id'] == attempt_id), None)
        if attempt is None or not attempt.get('usable'):
            return False
        entry['chosen'] = attempt_id
        entry['chosen_among'] = [a['id'] for a in entry['attempts'] if a.get('usable')]
        entry['current'] = current_of(entry)
        return entry['current'] == attempt_id

    def forget_attempt(self, ident, attempt_id):
        """The calculation taken out of the history of the molecule — its record only, the files of its folder
        stay; the current one is found again (current_of: the one chosen, else the last that gave a result). ValueError
        while it runs (or its fate on the server is not known). Returns the record taken out."""
        entry = self.entry(ident)
        attempt = next((a for a in entry['attempts'] if a['id'] == attempt_id), None)
        if attempt is None:
            raise ValueError('Расчёт не найден в истории молекулы.')
        if attempt.get('state') in BUSY:
            raise ValueError('Этот расчёт ещё идёт (или ждёт в очереди): дождитесь конца или остановите его.')
        entry['attempts'] = [a for a in entry['attempts'] if a['id'] != attempt_id]
        if entry.get('chosen_among'):
            entry['chosen_among'] = [i for i in entry['chosen_among'] if i != attempt_id]
        entry['current'] = current_of(entry)
        return attempt

    def adopt_geometry(self, entry, attempt, geometry, kind, text):
        """An optimization (or a transition state)
        that converged gives the molecule its geometry — the next calculation of the molecule, single or of a queue,
        starts from it. The structure before it stays in the attempt (its input) and in Undo of the tab. Not taken: an
        optimization that did not converge, another task (energy, frequencies), atoms of another order, and a structure
        edited after the calculation started (the edit of the user wins). Returns whether it was taken."""
        task = (attempt.get('calculation') or {}).get('task', '')
        if task not in OPTIMIZING or not optimization_converged(kind, text):
            return False
        try:
            molecule, _ = self.read_structure(entry['structure'])
            started, _ = self.read_structure(attempt['input'])
        except (KeyError, ValueError):
            return False
        symbols = [a.symbol for a in molecule.atoms]
        if symbols != [a.symbol for a in geometry.atoms] or symbols != [a.symbol for a in started.atoms]:
            return False
        if any(abs(p - q) > 1e-4 for a, b in zip(molecule.atoms, started.atoms) for p, q in zip(a.position, b.position)):
            return False  # edited after the start
        adopted = replace(molecule, atoms=tuple(replace(a, x=b.x, y=b.y, z=b.z)
                                                for a, b in zip(molecule.atoms, geometry.atoms)))
        entry['structure'] = dict(entry['structure'], xyz=adopted.xyz())
        entry['flat'] = False
        entry['adopted'] = attempt['id']
        return True

    def result_items(self, selected=None):
        """Current results only, for transfer/QTAIM. No ranking or cross-method Boltzmann weights."""
        found = []
        from collections import Counter

        names = Counter(e['name'] for e in self.molecules)
        for entry in self.molecules:
            if str(entry.get('props', {}).get('role', '')).startswith('bsse_'):
                continue  # auxiliary ghost-atom calculations are not full molecular wavefunctions for QTAIM
            if selected is not None and entry['id'] not in selected:
                continue
            attempt = self.current(entry)
            if attempt is None:
                continue
            molecule, calc = self.read_structure(attempt['input'])
            name = entry['name'] + (' · ' + entry['id'][:8] if names[entry['name']] > 1 else '')
            item = batch.BatchItem(name, molecule, calc.charge, calc.multiplicity, state='done',
                                   folder=str(self.absolute(attempt['folder'])), output=str(self.absolute(attempt['output'])),
                                   energy=attempt.get('energy'), gibbs=attempt.get('gibbs'), heat=attempt.get('heat'),
                                   geometry=batch._molecule(attempt.get('geometry')),
                                   props=dict(attempt.get('props', entry.get('props', {}))),
                                   formal=tuple(entry.get('formal', ())))
            found.append((entry, attempt, item))
        return found

    def import_batch(self, folder):
        """Copy a completed package and attach its attempts. Source files are never rewritten."""
        source = Path(folder).resolve()
        if source == self.root or source in self.root.parents:
            raise ValueError('Исходная очередь не должна содержать папку проекта.')
        key = str(source)
        if key in self.data['imports']:
            return self.absolute(self.data['imports'][key]['folder'])
        queue = batch.Batch.load(source, recover=False)
        if project_of_queue(queue) == self.path:
            return source
        if not queue.done():
            raise ValueError('Сначала завершите или остановите исходную очередь; затем добавьте её в проект.')
        if any(p.is_symlink() for p in source.rglob('*')):
            raise ValueError('Папка расчёта содержит ссылки на другие файлы. Для переноса нужны обычные файлы.')
        for item in queue.items:
            for value in (item.folder, item.output):
                if value:
                    Path(value).resolve().relative_to(source)
        target = self.root / 'calculations' / ('import_' + uuid4().hex[:12])
        shutil.copytree(source, target)
        queue.folder = target
        if queue.calc.guess:
            guess = Path(queue.calc.guess)
            try:
                copied_guess = target / guess.resolve().relative_to(source)
            except ValueError:
                from azimuth.core import GUESS_FILE

                copied_guess = next(target.rglob(GUESS_FILE), guess)
            queue.calc = replace(queue.calc, guess=str(copied_guess))
            _, queue.calc = self.read_structure(self.structure(queue.items[0].molecule, queue.calc))
        for item in queue.items:
            for field in ('folder', 'output'):
                value = getattr(item, field)
                if value:
                    setattr(item, field, str(target / Path(value).resolve().relative_to(source)))
        original = self.data['imports'].get(str(Path(queue.extra.get('retry_of', '')).resolve()))
        ids = []
        for k, item in enumerate(queue.items):
            previous = queue.extra.get('retry_items', [])
            if original and k < len(previous) and 1 <= previous[k]['index'] <= len(original['ids']):
                ident = original['ids'][previous[k]['index'] - 1]
            else:
                calc = replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity)
                ident = self.add(item.molecule, calc, queue.kind, item.name)['id']
            self.entry(ident).update(props=dict(item.props), formal=list(item.formal))
            ids.append(ident)
        queue.extra.pop('project', None)
        queue.extra['project'] = {'manifest': os.path.relpath(self.path, target), 'ids': ids,
                                  'attempts': [uuid4().hex for _ in ids]}
        self.data['batches'].append(self.relative(target))
        self.data['imports'][key] = {'folder': self.relative(target), 'ids': ids}
        self.sync_queue(queue)
        self.save()
        queue.save()
        return target

    def sync_queue(self, queue):
        link = queue.extra['project']
        if len(link['ids']) != len(queue.items) or len(link['attempts']) != len(queue.items):
            raise ValueError('Повреждена связь очереди с проектом.')
        folder = self.relative(queue.folder)
        if folder not in self.data['batches']:
            self.data['batches'].append(folder)
        present = {e['id'] for e in self.molecules}
        for item, ident, attempt in zip(queue.items, link['ids'], link['attempts']):
            if ident not in present:  # the molecule was removed from the project — its row is not recorded
                continue
            calc = replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity,
                           task=item.props.get('task', queue.calc.task))
            record = self.record(ident, attempt, item.molecule, calc, queue.kind, item.state,
                                 item.folder, item.output, queue.folder, item.note)
            record['props'] = dict(item.props)


BUSY = ('waiting', 'running', 'sent', 'searching', 'submitting', 'uncertain')  # not removed while so


def busy(entry):
    """An attempt of the molecule is still under way (or its fate on the server is not known)."""
    return any(a.get('state') in BUSY for a in entry.get('attempts', ()))


def removal(project, ids):
    """The entries taken out with the molecules ids —
    those ids and the molecules a binding queue made for them (auxiliary 'of'), in project order; ValueError when
    one of them is still calculated (a queue would record into a molecule that is gone) or an id is unknown."""
    chosen = set(ids)
    known = {e['id'] for e in project.molecules}
    if not chosen or not chosen <= known:
        raise ValueError('Молекула не найдена в проекте.')
    taken = [e for e in project.molecules
             if e['id'] in chosen or (e.get('auxiliary') or {}).get('of') in chosen
             or e.get('conformer_of') in chosen]  # a molecule goes with its conformers
    running = [e['name'] for e in taken if busy(e)]
    if running:
        raise ValueError('Эти молекулы ещё считаются (или ждут в очереди): ' + ', '.join(running[:5])
                         + ('…' if len(running) > 5 else '') + '. Дождитесь конца или остановите расчёт.')
    return taken


def remove_molecules(project, ids):
    """The molecules ids (and those made for them, removal) taken out of the project, with their attempts; the ticks
    of the batch forget them. Returns [(position, entry)] — what restore_molecules puts back. Files are not touched."""
    taken = removal(project, ids)
    gone = {e['id'] for e in taken}
    removed = [(k, copy.deepcopy(e)) for k, e in enumerate(project.molecules) if e['id'] in gone]
    project.data['molecules'] = [e for e in project.molecules if e['id'] not in gone]
    if project.data.get('excluded'):
        project.data['excluded'] = [i for i in project.data['excluded'] if i not in gone]
    return removed


def restore_molecules(project, removed):
    """What remove_molecules returned, back at its places (an id present again is not doubled)."""
    present = {e['id'] for e in project.molecules}
    for position, entry in sorted(removed, key=lambda pair: pair[0]):
        if entry['id'] not in present:
            project.molecules.insert(min(position, len(project.molecules)), copy.deepcopy(entry))
            present.add(entry['id'])
    return [entry['id'] for _, entry in removed]


# -- the conformers of a molecule — a group under it in the list of the project ---------------------------
# All the conformers in the energy window form a group under their molecule; checking the molecule for a queue checks
# its conformers too, and the group unfolds to uncheck some. A conformer is a molecule of the project of its own (its
# calculations, its folder) with conformer_of — the id of the
# molecule searched — and conformer = {rank, energy, delta, share}; it stands right after that molecule.

def conformers_of(project, ident):
    """The conformers of the molecule ident, in their order."""
    return [e for e in project.molecules if e.get('conformer_of') == ident]


def conformer_root(project, ident):
    """The molecule whose conformers ident belongs to (ident itself when it is no conformer)."""
    entry = next((e for e in project.molecules if e['id'] == ident), None)
    return (entry or {}).get('conformer_of') or ident


def set_conformers(project, ident, found):
    """The conformers found for the molecule ident (or for the molecule a conformer ident belongs to): found —
    [(molecule, energy | None, delta | None, share | None)], the lowest first. Those of an earlier search that were not
    calculated are replaced; those with calculations stay (their results are kept). The new ones stand after the
    molecule and its conformers kept, with its settings, charges and kind; they are in the batch (no tick taken off).
    Returns the new entries."""
    root = conformer_root(project, ident)
    parent = project.entry(root)
    old = conformers_of(project, root)
    dropped = {e['id'] for e in old if not e.get('attempts')}
    project.data['molecules'] = [e for e in project.molecules if e['id'] not in dropped]
    if project.data.get('excluded'):
        project.data['excluded'] = [i for i in project.data['excluded'] if i not in dropped]
    _, calc = project.read_structure(parent['structure'])
    kept = len(old) - len(dropped)
    added = []
    for k, (molecule, energy, delta, share) in enumerate(found, 1):
        entry = {'id': uuid4().hex, 'name': f"{parent['name']} · {kept + k}",
                 'structure': project.structure(replace(molecule, title=parent['name']), calc),
                 'kind': parent.get('kind', 'orca'), 'attempts': [], 'current': None, 'conformer_of': root,
                 'conformer': {'rank': kept + k, 'energy': energy, 'delta': delta, 'share': share}}
        for key in ('formal', 'props'):
            if parent.get(key):
                entry[key] = copy.deepcopy(parent[key])
        added.append(entry)
    place = max(k for k, e in enumerate(project.molecules) if e['id'] == root or e.get('conformer_of') == root) + 1
    project.molecules[place:place] = added
    return added


def mark_conformers(project, ident, ids, deltas=()):
    """Entries ids made by a queue of the drawer conformers of the molecule ident become its conformers —
    conformer_of, the rank and ΔE kept, the default names «Конформер k» turned into «<molecule> · k», and they move
    under the molecule (after its conformers already there). Entries that are conformers already stay as they are."""
    root = conformer_root(project, ident)
    parent = next((e for e in project.molecules if e['id'] == root), None)
    if parent is None:
        return []
    chosen = [e for i in ids for e in project.molecules if e['id'] == i and e['id'] != root and not e.get('conformer_of')]
    if not chosen:
        return []
    kept = len(conformers_of(project, root))
    deltas = list(deltas) + [None] * len(chosen)
    for k, entry in enumerate(chosen, 1):
        entry['conformer_of'] = root
        entry['conformer'] = {'rank': kept + k, 'energy': None, 'delta': deltas[k - 1], 'share': None}
        if re.fullmatch(r'(Конформер|Conformer|构象)\s*\d+', entry.get('name', '')):
            entry['name'] = f"{parent['name']} · {kept + k}"
    moved = {e['id'] for e in chosen}
    project.data['molecules'] = [e for e in project.molecules if e['id'] not in moved]
    place = max(k for k, e in enumerate(project.molecules) if e['id'] == root or e.get('conformer_of') == root) + 1
    project.molecules[place:place] = chosen
    return chosen


def adopt_conformer_queue(queue):
    """A queue of drawer conformers bound to the project (purpose 'conformers', its origin molecule in the
    project) — its entries shown as the conformers of that molecule; also for projects made."""
    link, origin = queue.extra.get('project'), (queue.extra.get('origin') or {}).get('molecule')
    if queue.purpose != 'conformers' or not link or not origin:
        return
    path = project_of_queue(queue)
    with edit(path) as project:
        if any(e['id'] == origin for e in project.molecules):
            mark_conformers(project, origin, link['ids'], [item.start_delta for item in queue.items])


def ordered(project):
    """listed(project) with every molecule followed by its conformers (as the list of the project shows them)."""
    shown = listed(project)
    ids = {e['id'] for e in shown}
    out = []
    for entry in shown:
        if entry.get('conformer_of') in ids:
            continue
        out.append(entry)
        out.extend(e for e in shown if e.get('conformer_of') == entry['id'])
    return out


def calculation_folder(project, entry):
    """The folder of the calculation of the molecule — of its current result, else of its newest attempt whose
    folder exists; None when it has none."""
    attempts = list(entry.get('attempts', ()))
    current = project.current(entry)
    for attempt in ([current] if current else []) + attempts[::-1]:
        relative = attempt.get('folder') if attempt else None
        if not relative:
            continue
        try:
            folder = project.absolute(relative)
        except ValueError:
            continue
        if folder.is_dir():
            return folder
    return None


def attempt_folder(project, attempt):
    """The folder of this calculation that may
    be deleted with it — by the rules of calculation_folders (inside the project, existing, not the project, not
    «calculations», not the folder of a whole queue) and used by no other calculation of the project; else None."""
    relative = attempt.get('folder')
    if not relative:
        return None
    for entry in project.molecules:
        if any(a.get('folder') == relative and a.get('id') != attempt.get('id') for a in entry.get('attempts', ())):
            return None
    try:
        folder = project.absolute(relative)
        whole = project.absolute(attempt['batch']) if attempt.get('batch') else None
    except ValueError:
        return None
    if folder in {project.root, project.root / 'calculations'} or folder == whole or not folder.is_dir():
        return None
    try:
        folder.resolve().relative_to(project.root.resolve())
    except ValueError:
        return None  # outside the project: not ours to delete
    return folder


def calculation_folders(project, entries):
    """The folders of the calculations of these molecules that may be deleted with them — inside the project,
    existing, never the project itself, «calculations» or the folder of a whole queue (its batch.json and «Анализ»
    belong to all its rows), and not used by an attempt of a molecule that stays."""
    gone = {e['id'] for e in entries}
    kept = set()
    for entry in project.molecules:
        if entry['id'] not in gone:
            kept |= {a.get('folder') for a in entry.get('attempts', ()) if a.get('folder')}
    found = []
    forbidden = {project.root, project.root / 'calculations'}
    for entry in entries:
        for attempt in entry.get('attempts', ()):
            relative = attempt.get('folder')
            if not relative or relative in kept:
                continue
            try:
                folder = project.absolute(relative)
                whole = project.absolute(attempt['batch']) if attempt.get('batch') else None
            except ValueError:
                continue
            if folder in forbidden or folder == whole or not folder.is_dir() or folder in found:
                continue
            found.append(folder)
    return found


AUXILIARY = ('ion', 'complex', 'bsse_l', 'bsse_lg', 'bsse_mg')  # made by a binding queue (binding.py)


def is_auxiliary(entry):
    """A molecule a binding queue made (the ion, a complex, a BSSE part), not one the user added."""
    return (entry.get('auxiliary') or {}).get('role') in AUXILIARY or \
        str((entry.get('props') or {}).get('role', '')) in AUXILIARY


def listed(project):
    """The molecules shown in the list of the tab and queued by «Пакетный расчёт»: those the user added and the
    complexes (their results are wanted); the ion and the BSSE parts stay out of sight."""
    return [e for e in project.molecules
            if not is_auxiliary(e) or (e.get('auxiliary') or {}).get('role', (e.get('props') or {}).get('role')) == 'complex']


def queueable(project):
    """The molecules a new queue of the project takes: only those the user added."""
    return [e for e in project.molecules if not is_auxiliary(e)]


def auxiliary_entry(project, item, calc, kind, key):
    """The entry of a molecule a binding queue makes — found again by key (role, the entry it belongs to, the
    ion) when the queue is run again, so the project does not fill with copies; a new attempt goes under it."""
    for entry in project.molecules:
        if entry.get('auxiliary') == key:
            return entry
    entry = project.add(item.molecule, calc, kind, item.name)
    entry.update(props=dict(item.props), formal=list(item.formal), auxiliary=key)
    return entry


def display_name(path):
    """What a list shows for a file — the name of the project for its manifest (project.qcc is the name of
    every project), the folder when the project cannot be read; the file name for any other file."""
    path = Path(path)
    if path.name != MANIFEST:
        return path.name
    try:
        data = Project.view(path).data
        name = str(data.get('name') or '').strip()
        draft = bool(data.get('draft'))
    except Exception:  # noqa: BLE001 — a list must show something: a damaged or locked project is named by its folder
        name, draft = '', False
    if draft:  # T03: a draft is marked as such
        from azimuth.i18n import tr

        return (name or path.parent.name) + ' · ' + tr('черновик')
    return name or path.parent.name


OPTIMIZING = ('Оптимизация', 'Оптимизация + частоты', 'Переходное состояние + частоты')  # tasks that move atoms


def optimization_converged(kind, text):
    """The program says its optimization converged (the marks of runner.MILESTONES 'opt')."""
    from modules.sextant.runner import MILESTONES

    marks = next((by_kind for key, _, by_kind in MILESTONES if key == 'opt'), {}).get(kind, ())
    return any(mark in text for mark in marks)


# T23 (docs/architecture/PROJECT_RUNTIME_GUIDE.md §13): results and analyses are not rebound after a change of the
# method, charge or geometry; the mismatch is shown. What of the molecule may differ from the input of its
# current result, in the order they are named. The level of theory: the fields that change the energy of a structure.
MISMATCHES = ('geometry', 'charge', 'multiplicity', 'theory', 'program')
MISMATCH_NAMES = {'geometry': 'геометрия', 'charge': 'заряд', 'multiplicity': 'мультиплетность',
                  'theory': 'метод, базис или среда', 'program': 'программа'}
THEORY = ('method', 'basis', 'dispersion', 'solvent', 'solvent_model', 'relativistic')
SAME_POSITION = 1e-3  # Å: a structure written and read again, not an edit
SAME_RESULT = 0.02  # Å: the geometry a calculation gave, as kept (0.006 Å apart was «changed»)


def _same_geometry(a, b, within=None):
    if a is None or b is None or len(a.atoms) != len(b.atoms):
        return False
    within = SAME_POSITION if within is None else within
    return all(p.symbol == q.symbol and all(abs(u - v) <= within for u, v in zip(p.position, q.position))
               for p, q in zip(a.atoms, b.atoms))


def result_mismatch(project, entry, molecule=None, calc=None, kind=None):
    """T23: what of the molecule now differs from the input of its current result — a tuple of MISMATCHES
    (empty: the result is of these data, or there is no result). molecule, calc, kind: the state of an open tab (its
    edits not saved yet); by default the saved structure of the molecule.
    The geometry is the result's own when it equals either the input of the attempt or the geometry the calculation
    gave (an optimization adopted, Project.adopt_geometry, or taken from the result by the user). Only states, never
    changes anything: the result stays bound to its attempt, the analyses to their artifact (§3d)."""
    attempt = project.current(entry)
    if attempt is None:
        return ()
    try:
        saved, saved_calc = project.read_structure(entry['structure'])
        then, then_calc = project.read_structure(attempt['input'])
    except (KeyError, TypeError, ValueError):
        return ()
    molecule = molecule if molecule is not None else saved
    calc = calc if calc is not None else saved_calc
    kind = kind or entry.get('kind')
    found = set()
    if not _same_geometry(molecule, then):
        try:
            final = batch._molecule(attempt.get('geometry'))
        except (KeyError, TypeError, ValueError):
            final = None
        # the geometry the calculation gave
        # differed from the one kept by 0.006 Å — the same structure written with another precision; it is the
        # result's own within SAME_RESULT
        if not _same_geometry(molecule, final, SAME_RESULT):
            found.add('geometry')
    if int(calc.charge) != int(then_calc.charge):
        found.add('charge')
    if int(calc.multiplicity) != int(then_calc.multiplicity):
        found.add('multiplicity')
    if any(str(getattr(calc, f, '') or '').strip().lower() != str(getattr(then_calc, f, '') or '').strip().lower()
           for f in THEORY):
        found.add('theory')
    if kind and attempt.get('kind') and kind != attempt['kind']:
        found.add('program')
    return tuple(code for code in MISMATCHES if code in found)


def mismatch_text(codes):
    """«геометрия, заряд» — the names of result_mismatch, in the language of the program."""
    from azimuth.i18n import tr

    return ', '.join(tr(MISMATCH_NAMES[code]) for code in codes)


def server_attempts(project, skip=()):
    """The single calculations of the project on a server whose end was not seen (sent, running or
    waiting there; a queue takes itself up — batch_actions), newest first, as records of the history of calculations
    (run_actions.resume_history); folders in skip are left out, and those without what the server said
    (job.json or the record of the sending)."""
    from modules.sextant import history

    found = []
    for entry in project.molecules:
        for attempt in entry['attempts']:
            if (attempt.get('batch') or not attempt.get('place') or not attempt.get('folder')
                    or attempt.get('state') not in ('running', 'sent', 'waiting')):
                continue
            folder = str(project.absolute(attempt['folder']))
            if folder in skip:
                continue
            rec = dict(attempt.get('calculation') or {}, kind=attempt.get('kind', 'orca'), place=attempt['place'],
                       title=entry['name'], folder=folder,
                       output=str(project.absolute(attempt['output'])) if attempt.get('output') else '')
            try:
                if history.remote_info(rec) is None:
                    continue
            except Exception:  # noqa: BLE001 — a record that cannot be read: not watched, the project still opens
                continue
            found.append(rec)
    return found[::-1]


def current_of(entry):
    """The current calculation of a molecule: the one chosen by the user (Project.choose) while no other calculation
    has given a result since the choice, else the last one that gave a result; None without any."""
    attempts = entry.get('attempts', [])
    usable = [a['id'] for a in attempts if a.get('usable')]
    chosen = entry.get('chosen')
    if chosen:
        known = set(entry.get('chosen_among', ()))
        if chosen in usable and set(usable) <= known:
            return chosen
        entry.pop('chosen', None)  # a newer result came (or the chosen one is gone): the choice is over
        entry.pop('chosen_among', None)
    return usable[-1] if usable else None


def attempt_of_file(path, limit=4):
    """(the path of the
    project, the id of the molecule, the attempt) whose output is this file — looked for in the project.qcc of the
    folders above it (a calculation lies in <project>/calculations/<run>/…); None when it is no output of a project."""
    file = Path(path).resolve()
    folder = file.parent
    for _ in range(limit):
        manifest = folder / MANIFEST
        if manifest.is_file():
            try:
                project = Project.view(manifest)
            except (OSError, ValueError, KeyError):
                return None
            for entry in project.molecules:
                for attempt in entry.get('attempts', ()):
                    if attempt.get('output') and project.absolute(attempt['output']).resolve() == file:
                        return project.path, entry['id'], attempt
            return None
        if folder.parent == folder:
            break
        folder = folder.parent
    return None


def looked_at_draft(path):
    """A draft whose molecules were only taken from files (named «formula · file», no calculation) — a file opened to
    look at, kept at the exit; not a molecule drawn (that one is kept to be found again)."""
    try:
        target = Path(path)
        project = Project.view(target / MANIFEST if target.is_dir() else target)
    except (OSError, ValueError, KeyError):
        return False
    molecules = project.molecules
    return bool(project.data.get('draft')) and bool(molecules) and all(
        ' · ' in str(entry.get('name') or '') and not entry.get('attempts') for entry in molecules)


def project_of_queue(queue):
    link = queue.extra.get('project')
    return (Path(queue.folder) / link['manifest']).resolve() if link else None


def attach(queue, path, ids):
    """Bind a new queue to existing project molecules; register all attempts before execution.
    A queue whose folder lies outside the project (another jobs folder chosen in Settings) is not bound —
    the project keeps only paths inside itself; returns whether the queue was bound."""
    root = Path(path).resolve().parent
    folder = Path(queue.folder).resolve()
    if folder != root and root not in folder.parents:
        return False
    if len(ids) != len(queue.items) or len(ids) != len(set(ids)):
        raise ValueError('Каждая строка очереди должна соответствовать одной молекуле проекта.')
    queue.extra['project'] = {'manifest': os.path.relpath(path, queue.folder), 'ids': list(ids),
                              'attempts': [uuid4().hex for _ in ids]}
    with edit(path) as project:
        if queue.calc.guess and queue.items:
            _, queue.calc = project.read_structure(project.structure(queue.items[0].molecule, queue.calc))
        project.sync_queue(queue)
    queue.save()
    return True


def sync(queue):
    path = project_of_queue(queue)
    if path is not None:
        with edit(path) as project:
            project.sync_queue(queue)


def refresh(path):
    """Refresh completed/pending queue records after reopening. No server contact or task submission.
    A queue that is unreadable or linked to another project is skipped (its folder is named in .skipped) — one bad
    queue must not keep the whole project closed."""
    project = Project.load(path)
    skipped = []
    for folder in project.data['batches']:
        candidate = project.absolute(folder)
        if (candidate / batch.FILE).is_file():
            try:
                queue = batch.Batch.load(candidate, recover=False)
            except (OSError, ValueError, KeyError, TypeError):
                skipped.append(folder)
                continue
            if project_of_queue(queue) != project.path:
                skipped.append(folder)
                continue
            sync(queue)
            adopt_conformer_queue(queue)
    # A single job may have written its final output before the application closed.
    # Inspect local files only; never infer success from a partial geometry or contact the server here.
    from modules.sextant import runner

    with edit(path) as project:
        for entry in project.molecules:
            for attempt in entry['attempts']:
                if attempt.get('batch') or not attempt.get('output'):
                    continue
                state = attempt['state']
                output = project.absolute(attempt['output'])
                if state in ('running', 'sent', 'waiting') and output.is_file():
                    text = output.read_text(encoding='utf-8', errors='replace')
                    if runner.finished_normally(attempt['kind'], text, 0):
                        state = 'done'
                molecule, calc = project.read_structure(attempt['input'])
                project.record(entry['id'], attempt['id'], molecule, calc, attempt['kind'], state,
                               project.absolute(attempt['folder']), output, note=attempt.get('note', ''))
    project = Project.load(path)
    project.skipped = skipped
    return project


def extend_queue(queue):
    """Register the explicit BSSE follow-ups appended by binding.follow_ups, without changing earlier IDs."""
    link = queue.extra.get('project')
    if not link:
        return
    start = len(link['ids'])
    added = queue.items[start:]
    if not added or any(item.props.get('role') not in ('bsse_l', 'bsse_lg', 'bsse_mg') for item in added):
        raise ValueError('Неизвестные дополнительные расчёты очереди.')
    with edit(project_of_queue(queue)) as project:
        for item in added:
            calc = replace(queue.calc, charge=item.charge, multiplicity=item.multiplicity,
                           task=item.props.get('task', queue.calc.task))
            owner = link['ids'][item.props['of']] if isinstance(item.props.get('of'), int) else ''
            entry = auxiliary_entry(project, item, calc, queue.kind, {'role': item.props['role'], 'of': owner})
            if entry['id'] in link['ids']:
                raise ValueError('Дополнительный расчёт уже связан с этой очередью.')
            link['ids'].append(entry['id'])
            link['attempts'].append(uuid4().hex)
        project.sync_queue(queue)


def copy_project(path, target):
    """An independent copy of the project of path in the folder target (new or empty) — the whole
    folder (calculations too: the relative paths stay valid) without the writer lock, with a new project id and
    «copied_from» the id of the original; the ids of the molecules and attempts stay (their history). The
    database copied with the SQLite Backup API (consistent even while open). Returns the manifest of the copy."""
    from azimuth.runtime import writer_lock

    source = Path(path).resolve().parent
    target = Path(target).resolve()
    if target == source or source in target.parents or (target.exists() and any(target.iterdir())):
        raise ValueError('Choose an empty folder outside the project.')
    if target.exists():
        target.rmdir()
    database = project_store.DATABASE
    shutil.copytree(source, target, ignore=shutil.ignore_patterns(
        writer_lock.LOCK, writer_lock.INFO, writer_lock.INFO + '.tmp', '.project-*', database, database + '-journal',
        project_store.MIGRATING + '*'))
    if (source / database).is_file() and Project.load(Path(path).resolve()).storage == 'sqlite':
        project_store.backup(source / database, target / database)
    manifest = target / MANIFEST
    project = Project.load(manifest)
    project.data['copied_from'] = project.data.get('id')
    project.data['id'] = uuid4().hex
    project.save()
    return manifest

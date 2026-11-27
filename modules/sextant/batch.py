"""A queue of calculations for a set of structures: the conformers or the structures of the drawer of Compass
with the same settings of Sextant, one after another on this computer.

§1 PURPOSE
    After a search of conformers (xtb, CREST, ABC) the low ones are calculated again with a better method — one input
    file each, the same settings, run one after another; at the end their energies at the new level, ΔE and the
    Boltzmann shares, and the conformers sorted again (the order often changes after DFT).
§2 ALGORITHM Batch(kind, calc, items, folder): items — BatchItem (name, molecule, charge, multiplicity; state 'waiting'
    | 'running' | 'done' | 'failed' | 'stopped' | 'skipped' | 'sent' (sent to the server before the exit, in its SLURM
    queue, watched later; next_sent()) | 'uncertain' (the sending of it may have reached SLURM — not known; the queue
    goes on, the row is not repeated until the server is asked, «Проверить на сервере»); note — why it failed; the
    folder and the output of its job; energy, gibbs; heat — ΔHf of MOPAC, kcal/mol). The folder of the queue
    «<date>_<formula>_batch_<program>» holds the folder of every job and batch.json (the settings and the states — a
    queue left by closing the program is taken up again: resume). next_waiting() — the next item to start;
    finished(item, state, energy, gibbs, geometry). default_count(deltas, window=WINDOW): how many of the lowest are
    within WINDOW kcal/mol (3 by default; those without ΔE count). summary(): the items done, sorted by G when every one
    of them has it (a calculation with frequencies), else by E, for MOPAC (no total energy) by the heat of formation
    ΔHf; ΔE in kcal/mol from the lowest; shares exp(−ΔE/RT) / Σ at T. result_of(kind, text) — the final energy
    (hartree), the final geometry and G (hartree, the thermochemistry of modules/spectrum/analysis/thermo.py at 298.15 K
    and 1 atm from the frequencies, σ of the point group — as the tab «Термохимия» of Spectrum, without qRRHO) of an
    output.
§4 SPECIFICATION
    WINDOW = 3.0 kcal/mol; HARTREE_KCAL; R_KCAL; default_count(deltas, window=WINDOW) -> int; batch_folder(root,
    molecule, kind, now=None) -> Path;
    BatchItem; Batch(kind, calc, items, folder, place='local', source='', created, purpose='' | 'fukui' — 0.91.34 |
    'cda' — 0.91.40, extra={} — 0.91.40);
    .save(), Batch.load(folder) -> Batch (an item running on a server — job.json in its folder — stays 'running');
    .next_waiting() -> BatchItem | None; .counts() -> {state: n}; .done() -> bool; .summary(T=298.15) -> [dict name,
    energy, gibbs, delta (kcal/mol), share, item]; .table() -> (header, rows); result_of(kind, text, path=None) -> (energy |
    None, Molecule | None, gibbs | None).
§7 TESTS tests/sextant/test_batch.py.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass, field, replace
from datetime import datetime
from pathlib import Path

from azimuth.i18n import tr

WINDOW = 3.0  # kcal/mol: the conformers taken by default
HARTREE_KCAL = 627.5094740631
R_KCAL = 1.987204259e-3  # kcal/(mol·K)
FILE = 'batch.json'
STATES = ('waiting', 'running', 'done', 'failed', 'stopped', 'skipped', 'sent', 'searching', 'uncertain')  # 'sent' —
# in SLURM, not watched yet; 'searching' — its best conformer is searched before the calculation
# (batch_conformers.py); 'uncertain' — the answer of the server to the sending was lost, it is not known whether
# the job is in SLURM (azimuth/runtime/runs.py): never repeated before the server is asked (check_uncertain_item)
OPEN_KEY = 'open_batch'  # the preference: the folder of a queue not finished (batch_actions, unfinished.py)


def default_count(deltas, window=WINDOW):
    """How many of the lowest (deltas sorted from the lowest, None — unknown) are taken by default: those within
    window kcal/mol; all when no ΔE is known; at least one."""
    known = [d for d in deltas if d is not None]
    if not known:
        return len(deltas)
    return max(1, sum(1 for d in deltas if d is None or d <= window + 1e-9))


@dataclass
class BatchItem:
    name: str
    molecule: object
    charge: int = 0
    multiplicity: int = 1
    state: str = 'waiting'
    folder: str = ''
    output: str = ''
    energy: float | None = None
    gibbs: float | None = None
    geometry: object = None  # the final geometry (Molecule) when done
    start_delta: float | None = None  # ΔE of the search (kcal/mol), for the table
    heat: float | None = None  # MOPAC — the heat of formation ΔHf, kcal/mol (MOPAC prints no total energy)
    note: str = ''  # why it failed (the message of the job), kept in batch.json
    props: dict = field(default_factory=dict)  # the data items of its SDF record (logK …); its role
    formal: tuple = ()  # the formal charges per atom of its file (RDKit needs them for the ions)


def _molecule_dict(molecule):
    if molecule is None:
        return None
    return {'title': molecule.title, 'atoms': [[a.symbol, a.x, a.y, a.z] for a in molecule.atoms],
            # bonds None: not given (an XYZ) — kept as None, Compass finds them by distances
            'bonds': None if molecule.bonds is None else [list(b) for b in molecule.bonds]}


def _molecule(data):
    from azimuth.core import Atom, Molecule

    if not data:
        return None
    return Molecule(data.get('title', ''), tuple(Atom(s, float(x), float(y), float(z)) for s, x, y, z in data['atoms']),
                    None if data.get('bonds') is None else tuple(tuple(b) for b in data['bonds']))


@dataclass
class Batch:
    kind: str
    calc: object
    items: list
    folder: Path
    place: str = 'local'
    source: str = ''
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec='seconds'))
    purpose: str = ''  # 'fukui' — the three charge states of modules/spectrum/analysis/fukui.py; 'cda', 'binding';
    # 'conformers' (the drawer) or 'structures' (the molecules of a project) — '' only in older batch.json 'cda' — the
    # complex and its two fragments (modules/spectrum/wavefunction/multiwfn_cda.plan); extra: {'fragments': [[…], […]],
    # 'order': […]} — the atoms of the fragments in the numbering of the molecule of the tab (0-based)
    extra: dict = field(default_factory=dict)

    def next_waiting(self):
        return next((item for item in self.items if item.state == 'waiting'), None)

    def current(self):
        return next((item for item in self.items if item.state == 'running'), None)

    def next_sent(self):
        """The first item sent to the server before the program closed (in its SLURM queue), not watched yet."""
        return next((item for item in self.items if item.state == 'sent'), None)

    def counts(self):
        out = {state: 0 for state in STATES}
        for item in self.items:
            out[item.state] = out.get(item.state, 0) + 1
        return out

    def done(self):
        return all(item.state not in ('waiting', 'running', 'sent', 'searching') for item in self.items)

    def position(self, item):
        return self.items.index(item) + 1

    def finished(self, item, state, energy=None, gibbs=None, geometry=None, heat=None):
        item.state = state
        item.energy, item.gibbs, item.geometry, item.heat = energy, gibbs, geometry, heat
        self.save()

    def stop_rest(self):
        """«Остановить всё»: what has not started is skipped."""
        for item in self.items:
            if item.state == 'waiting':
                item.state = 'skipped'
        self.save()

    # -- the result ----------------------------------------------------------------------------------------------
    def summary(self, temperature=298.15):
        done = [item for item in self.items if item.state == 'done' and (item.energy is not None or item.heat is not None)]
        if not done:
            return []
        # G when every one has it (frequencies), else E; MOPAC — ΔHf (kcal/mol): its differences are the relative
        # energies of the method; an item without the quantity chosen is left out of the ranking
        if all(item.gibbs is not None for item in done):
            by = 'gibbs'
        elif any(item.energy is not None for item in done):
            by = 'energy'
        else:
            by = 'heat'
        scale = 1.0 if by == 'heat' else HARTREE_KCAL
        done = [item for item in done if getattr(item, by) is not None]
        done.sort(key=lambda item: getattr(item, by))
        low = getattr(done[0], by)
        deltas = [(getattr(item, by) - low) * scale for item in done]
        weights = [math.exp(-d / (R_KCAL * temperature)) for d in deltas]
        total = sum(weights)
        return [{'name': item.name, 'energy': item.energy, 'gibbs': item.gibbs, 'heat': item.heat, 'delta': d,
                 'share': w / total, 'by': by, 'by_gibbs': by == 'gibbs', 'item': item}
                for item, d, w in zip(done, deltas, weights)]

    def table(self, temperature=298.15):
        rows = []
        summary = self.summary(temperature)
        by = summary[0]['by'] if summary else 'energy'
        delta = {'gibbs': tr('ΔG, ккал/моль'), 'energy': tr('ΔE, ккал/моль'), 'heat': tr('ΔΔHf, ккал/моль')}[by]
        header = [tr('№'), tr('Структура'), tr('E, Eh'), tr('G, Eh'), tr('ΔHf, ккал/моль'), delta, tr('Доля, %'),
                  tr('ΔE поиска, ккал/моль'), tr('Папка')]

        def number(value, digits):
            return '' if value is None else f'{value:.{digits}f}'

        ranked = set()
        for n, row in enumerate(summary, 1):
            item = row['item']
            ranked.add(id(item))
            rows.append([n, row['name'], number(row['energy'], 8), number(row['gibbs'], 8), number(row['heat'], 3),
                         f"{row['delta']:.2f}", f"{100 * row['share']:.1f}", number(item.start_delta, 2),
                         Path(item.folder).name])
        for item in self.items:  # what did not give an energy, at the end
            if id(item) not in ranked:
                rows.append(['', item.name, '', '', '', '', '', number(item.start_delta, 2),
                             tr(STATE_NAMES.get(item.state, item.state))])
        return header, rows

    # -- batch.json ------------------------------------------------------------------------------------------------
    def save(self):
        data = {
            'version': 1, 'kind': self.kind, 'place': self.place, 'source': self.source, 'created': self.created,
            'purpose': self.purpose, 'extra': self.extra,
            'calc': asdict(self.calc),
            'items': [{**{k: v for k, v in asdict(replace(item, molecule=None, geometry=None)).items()
                          if k not in ('molecule', 'geometry')},
                       'molecule': _molecule_dict(item.molecule), 'geometry': _molecule_dict(item.geometry)}
                      for item in self.items],
        }
        if self.extra.get('project'):
            import os

            if data['calc'].get('guess'):
                try:  # Windows — another drive has no relative path; then it stays absolute
                    data['calc']['guess'] = os.path.relpath(self.calc.guess, self.folder)
                except ValueError:
                    pass
            for raw in data['items']:
                for key in ('folder', 'output'):
                    if raw.get(key):
                        try:  # a path outside the queue folder stays absolute: the state of the queue is saved anyway
                            raw[key] = Path(raw[key]).resolve().relative_to(Path(self.folder).resolve()).as_posix()
                        except ValueError:
                            pass
        path = Path(self.folder) / FILE
        # in a project — a row of its database, and batch.json after it as a derived view
        _records().write(self.folder, FILE, data, mirror=True)
        if self.extra.get('project'):
            try:
                from azimuth.projects import sync

                sync(self)
                self.project_warning = ''
            except (OSError, ValueError, KeyError, StopIteration) as exc:
                # Calculation state is already persisted. Never re-submit a job because its project update failed.
                self.project_warning = str(exc)
        return path

    @classmethod
    def load(cls, folder, recover=True):
        from azimuth.core import Calculation

        data = _records().read(folder, FILE)  # the row of the project, else batch.json
        if not isinstance(data, dict):
            data = json.loads((Path(folder) / FILE).read_text(encoding='utf-8'))  # the error of the file, as before
        known = set(Calculation.__dataclass_fields__)
        calc = Calculation(**{k: (tuple(v) if isinstance(v, list) else v) for k, v in data['calc'].items() if k in known})
        if data.get('extra', {}).get('project') and calc.guess and not Path(calc.guess).is_absolute():
            calc = replace(calc, guess=str((Path(folder) / calc.guess).resolve()))
        items = []
        for raw in data['items']:
            for key in ('folder', 'output'):
                if raw.get(key) and not Path(raw[key]).is_absolute():
                    raw[key] = str((Path(folder) / raw[key]).resolve())
            item = BatchItem(raw['name'], _molecule(raw['molecule']), raw.get('charge', 0), raw.get('multiplicity', 1),
                             raw.get('state', 'waiting'), raw.get('folder', ''), raw.get('output', ''), raw.get('energy'),
                             raw.get('gibbs'), _molecule(raw.get('geometry')), raw.get('start_delta'), raw.get('heat'),
                             raw.get('note', ''), dict(raw.get('props') or {}), tuple(raw.get('formal') or ()))
            # the program was closed while it ran: started again — but one sent to a server (job.json in its
            # folder) stays 'running': it goes on there, its watching is taken up (batch_actions.start_next_batch_item)
            sent = data.get('place') == 'server' and item.folder and _records().exists(item.folder, 'job.json')
            if recover and item.state in ('running', 'searching') and not sent:  # a search — again
                item.state = 'waiting'
            items.append(item)
        return cls(data['kind'], calc, items, Path(folder), data.get('place', 'local'), data.get('source', ''),
                   data.get('created', ''), data.get('purpose', ''), data.get('extra') or {})


# the rows a new attempt must not be prepared for: they run, or may run, on the server ('uncertain')
NOT_REPEATABLE = ('running', 'sent', 'searching', 'uncertain')
STATE_NAMES = {'waiting': 'ждёт', 'running': 'идёт', 'done': 'готово', 'failed': 'ошибка', 'stopped': 'остановлен',
               'skipped': 'пропущен', 'sent': 'отправлен на сервер', 'searching': 'поиск конформера',
               'uncertain': 'неизвестно, принят ли сервером'}


def batch_folder(root, molecule, kind, now=None):
    from modules.sextant.runner import _safe

    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    # Latin letters only: ORCA on Windows does not find its parts under a path with other letters
    base = f'{(now or datetime.now()):%Y-%m-%d_%H-%M-%S}_{_safe(molecule.formula)}_batch_{kind}'
    folder, n = root / base, 1
    while folder.exists():
        n += 1
        folder = root / f'{base}-{n}'
    folder.mkdir()
    return folder


def result_of(kind, text, path=None):
    """(final energy hartree | None, final geometry | None, G hartree | None, ΔHf kcal/mol | None — MOPAC) of an
    output of the program kind. path — the output file: xtb writes its final geometry beside it (xtbopt.xyz), not into
    the output; without the path an xtb run gave no geometry and its project never took the result (0.249.1)."""
    from modules.spectrum.readers.outputs import read_any

    try:
        output = read_any(text, str(path) if path else None)
    except Exception:  # noqa: BLE001 — an output that cannot be read gives no energy
        return None, None, None, None
    energy = None
    if getattr(output, 'final_energy', None):
        energy = output.final_energy[1]
    elif output.energies:
        energy = output.energies[-1]
    geometry = output.geometry
    gibbs = None
    if energy is not None and geometry is not None and output.frequencies:
        try:
            from modules.spectrum.analysis import thermo

            sigma = 1
            try:  # the rotational symmetry number from the point group, as the tab «Термохимия» proposes it
                from modules.compass.chemistry.symmetry import analyze

                point = analyze(geometry)
                sigma = thermo.symmetry_number(point.get('name', '') if 'err' not in point else '')
            except Exception:  # noqa: BLE001 — no point group: σ = 1
                sigma = 1
            found = thermo.thermochemistry(geometry, output.frequencies, energy, multiplicity=thermo.multiplicity(text),
                                           sigma=sigma)
            gibbs = found.total(found.gibbs)
        except (ValueError, ZeroDivisionError):
            gibbs = None
    return energy, geometry, gibbs, getattr(output, 'heat_of_formation', None)


def _records():
    from azimuth.runtime import records  # job.json in the database of the project, else the file

    return records

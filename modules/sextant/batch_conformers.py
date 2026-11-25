"""The best conformer of every structure of a queue before its calculation — the methods of the program, chosen in
«Настройки → Расчёты».

HEADER
    A set of 2D records made 3D, or drawn by hand, is one conformer of many. When the switch of the settings is on (the
    method of the search is chosen there too), each structure of a queue is searched first (its
    own folder of the queue, «conformers/<n>»), the lowest conformer replaces it, and the calculation goes on with it.
    Wilkinson convention, sections 1-8.

§1 THEORY The methods are those of «Поиск конформеров» (modules/compass/actions/conformer_actions.py): RDKit ETKDG v3 +
    MMFF94 (UFF without parameters), the lowest of 20 (modules/compass/chemistry/rdkit_embed.py); the turns of the
    rotatable bonds with a step of 120° (at most SCAN_LIMIT combinations) each optimized in GFN2-xTB; the artificial bee
    colony over the turns with GFN2-xTB energies (abc_search.py); CREST iMTD-GC with GFN2-xTB. The lowest is the lowest
    energy of the method (MMFF or GFN2-xTB, gas phase), among the conformers whose bonds are those of the structure (a
    proton moved by xtb is not a conformer). «Авто» takes the turns for up to 4 rotatable bonds, the bee colony for
    5–10, CREST beyond, and CREST for a structure without rotatable bonds but with a ring of 8 atoms or more (a crown, a
    cryptand: rotors() leaves out the bonds of rings); a small rigid structure keeps its geometry.

§2 ALGORITHM method_for(method, molecule) -> the method to run, or None (nothing to search). best(method, molecule,
    charge, multiplicity, root, programs, cancel, step, formal, cores) -> (Molecule | None, note): runs the method,
    every program waited for in this thread (polled every POLL s; cancel — a threading.Event: the program is stopped and
    InterruptedError raised), step(k, n) — the progress. The caller (batch_actions.start_conformer_stage) runs it in a
    worker thread and replaces the structure of the item; the note (method, how many conformers, ΔE of the start when
    known) is kept in its props «conformer», so a queue taken up again does not search again.

§3 APPLICATIONS
    modules/sextant/batch_actions.py (the stage 'searching' of an item); azimuth/settings_dialog.py (the switch and the
    method, defaults KEYS 'batch_conformers', 'batch_conformer_method').

§4 SPECIFICATION METHODS ((key, title, note) …); SCAN_LIMIT; method_for(method, molecule) -> str | None;
    largest_ring(molecule) -> int; Programs(xtb, crest, python); best(…) -> (Molecule | None, str); same_bonds(a, b) ->
    bool.

§6 NOTES
    ASSUMPTION: the search is done in the gas phase with GFN2-xTB / MMFF whatever the method of the queue; for a series
    of ligands this ranks the conformers well enough to start the DFT optimization from the lowest. The search runs on
    this computer also for a queue on a server (xtb, CREST and RDKit are local programs). The ion of a binding queue and
    its complexes are not searched (the complex is built on the optimized ligand).

§7 TEST CASES (tests/compass/test_batch_conformers.py)
    «Авто»: butane — the turns, a model crown without rotors — CREST, water — nothing; the ring size of cyclohexane 6; a
    stub xtb that gives energies by the order of the candidates — the lowest taken, a conformer with a changed bond
    left out; cancel stops it.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, replace
from pathlib import Path

from azimuth.i18n import tr

METHODS = (
    ('auto', 'Авто (по числу вращаемых связей)',
     'До 4 вращаемых связей — перебор поворотов, 5–10 — пчелиный поиск, больше или большой цикл — CREST.'),
    ('rdkit', 'RDKit: ETKDG + MMFF', 'Быстро: 20 конформеров RDKit, самый низкий по MMFF94. Нужен Python с RDKit.'),
    ('scan', 'Перебор поворотов + xtb', 'Повороты связей по 120°, каждый кандидат — оптимизация GFN2-xTB.'),
    ('abc', 'Пчелиный поиск (ABC) + xtb', 'Искусственная пчелиная колония по поворотам с энергиями GFN2-xTB.'),
    ('crest', 'CREST (iMTD-GC)', 'Самый полный поиск: метадинамика CREST, GFN2-xTB. Дольше всех.'),
)
KEYS = tuple(key for key, *_ in METHODS)
SCAN_LIMIT = 60  # combinations of the turns per structure in a queue (Compass offers 200 for one structure)
ABC_CONFORMERS = 6
ABC_ITERATIONS = 8
RING = 8  # atoms: a ring this large is flexible (crown ethers, cryptands) — CREST in «Авто»
POLL = 0.3  # s


@dataclass
class Programs:
    xtb: object = None
    crest: object = None
    python: object = None


def largest_ring(molecule):
    """The size of the largest of the smallest rings through every bond (0 without rings)."""
    from collections import deque

    from modules.compass.chemistry.builder import connections

    bonds = [(b[0], b[1]) for b in (molecule.bonds if molecule.bonds is not None else connections(molecule))]
    near = {k: set() for k in range(len(molecule.atoms))}
    for i, j in bonds:
        near[i].add(j)
        near[j].add(i)
    largest = 0
    for i, j in bonds:  # the shortest path i → j without the bond i–j closes the smallest ring through it
        seen, queue = {i: 0}, deque([i])
        while queue:
            a = queue.popleft()
            for b in near[a]:
                if (a, b) in ((i, j), (j, i)) or b in seen:
                    continue
                seen[b] = seen[a] + 1
                queue.append(b)
        if j in seen:
            largest = max(largest, seen[j] + 1)
    return largest


def method_for(method, molecule):
    from modules.compass.chemistry import conformers as cf

    if molecule is None or len(molecule.atoms) < 4:
        return None
    if method != 'auto':
        return method if method in KEYS else None
    rotors = len(cf.rotors(molecule))
    if rotors == 0:
        return 'crest' if largest_ring(molecule) >= RING else None
    return 'scan' if rotors <= 4 else 'abc' if rotors <= 10 else 'crest'


def same_bonds(a, b):
    from modules.compass.chemistry.builder import connections

    def key(m):
        return {tuple(sorted(bond[:2])) for bond in connections(replace(m, bonds=None))}

    return len(a.atoms) == len(b.atoms) and key(a) == key(b)


def _wait(job, cancel):
    while job.poll() is None:
        if cancel is not None and cancel.is_set():
            job.stop()
            raise InterruptedError()
        time.sleep(POLL)
    return job


def _xtb(program, molecule, calc, root, cancel, short=False):
    """(energy, Molecule) of an xtb optimization (a short one may stop before convergence: its last step), or None."""
    from azimuth.core import read_xyz
    from modules.compass.chemistry.formats import read_xyz_frames
    from modules.sextant import runner

    spec = runner.prepare('xtb', program, molecule, calc, (), root)
    job = _wait(runner.Job(spec).start(), cancel)
    text = job.text()
    if not short and not runner.finished_normally('xtb', text, job.code):
        return None
    _, energy = runner.progress('xtb', text, spec.folder)
    for name in ('xtbopt.log', 'xtbopt.xyz', 'xtblast.xyz'):
        path = spec.folder / name
        if path.is_file():
            try:
                content = path.read_text(encoding='utf-8', errors='replace')
                geometry = read_xyz_frames(content)[-1] if name == 'xtbopt.log' else read_xyz(content)
            except (ValueError, IndexError):
                continue
            return None if energy is None else (energy, geometry)
    return None


def _lowest(found, molecule):
    found = sorted(((e, m) for e, m in found if e is not None and m is not None), key=lambda row: row[0])
    for e, m in found:
        if same_bonds(m, molecule):
            return e, m, len(found)
    return None, None, len(found)


def best(method, molecule, charge, multiplicity, root, programs, cancel=None, step=None, formal=(), cores=1):
    """(the lowest conformer | None, a note). Every program is waited for here — call it from a worker thread."""
    from azimuth.core import Calculation
    from modules.compass.chemistry import conformers as cf

    chosen = method_for(method, molecule)
    if chosen is None:
        return None, tr('жёсткая или маленькая структура — поиск не нужен')
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    calc = Calculation(task='Оптимизация', charge=int(charge), multiplicity=int(multiplicity), cores=max(1, int(cores)))
    tell = step or (lambda done, total: True)
    if chosen == 'rdkit':
        from modules.compass.chemistry import embed3d

        if programs.python is None:
            raise ValueError(tr('Python с RDKit не найден — укажите его («Геометрия → Сделать 3D (RDKit)…»).'))
        made = embed3d.run(programs.python, [molecule], [tuple(formal)] if formal else None,
                           step=lambda d, t: (not (cancel is not None and cancel.is_set())) and tell(d, t) is not False)
        new, ok, note = made[0]
        if not ok:
            raise ValueError(tr('RDKit: ') + note)
        return new, tr('RDKit ETKDG + MMFF: самый низкий из 20') + (f' ({note})' if note else '')
    if chosen in ('scan', 'abc') and programs.xtb is None:
        raise ValueError(tr('xtb не найдена: укажите её в Секстанте («Программа: xtb» → «Указать…»).'))
    if chosen == 'crest':
        from modules.sextant import runner

        if programs.crest is None:
            raise ValueError(tr('CREST не найдена (conda install -c conda-forge crest; рядом нужна и xtb).'))
        tell(0, 1)
        spec = runner.prepare('crest', programs.crest, molecule, calc, (), root, crest={'ewin': cf.EWIN})
        job = _wait(runner.Job(spec).start(), cancel)
        ensemble = spec.folder / 'crest_conformers.xyz'
        if not runner.finished_normally('crest', job.text(), job.code) or not ensemble.is_file():
            raise ValueError(tr('CREST не закончил поиск: см. crest.out в папке ') + str(spec.folder))
        found = [(e, m) for m, e in cf.read_ensemble(ensemble.read_text(encoding='utf-8', errors='replace'))]
        energy, lowest, n = _lowest(found, molecule)
        tell(1, 1)
        return lowest, tr(f'CREST: конформеров {n}, взят самый низкий') + ('' if lowest is not None else tr(' — не найден'))
    if chosen == 'scan':
        candidates = [m for m, _ in cf.candidates(molecule, 120, SCAN_LIMIT)]
        found = []
        for k, candidate in enumerate(candidates):
            if tell(k, len(candidates)) is False or (cancel is not None and cancel.is_set()):
                raise InterruptedError()
            answer = _xtb(programs.xtb, candidate, calc, root, cancel)
            if answer is not None:
                found.append(answer)
        tell(len(candidates), len(candidates))
        energy, lowest, n = _lowest(found, molecule)
        return lowest, tr(f'перебор поворотов + xtb: кандидатов {len(candidates)}, оптимизировано {n}')
    from modules.compass.chemistry import abc_search

    search = abc_search.search(molecule, n_confs=ABC_CONFORMERS, global_iterations=ABC_ITERATIONS,
                               local_iterations=max(1, ABC_ITERATIONS // 2), ewin=cf.EWIN)
    count = 0
    try:
        request = next(search)
        while True:
            if tell(count, 0) is False or (cancel is not None and cancel.is_set()):
                search.close()
                raise InterruptedError()
            candidate, cycles = request
            answer = _xtb(programs.xtb, candidate, replace(calc, max_cycles=cycles or 200), root, cancel, short=bool(cycles))
            count += 1
            request = search.send(None if answer is None else answer)
    except StopIteration as stop:
        ensemble = list(stop.value or [])
    found = [(e, m) for m, e in ensemble]
    energy, lowest, n = _lowest(found, molecule)
    return lowest, tr(f'пчелиный поиск + xtb: оптимизаций {count}, конформеров {n}')

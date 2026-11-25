"""QTAIM of every calculation of a finished queue at once: the critical points of the density by Multiwfn, the weak
interactions named, tables for all the molecules.

HEADER
    After a queue (modules/sextant/batch.py) of conformers or of a set of structures, the critical points of each one
    were found by hand, one result after another. Here they are found for all the calculations done, one Multiwfn run
    each, as the button «Найти критические точки» does for one (modules/spectrum/views/density_view.py): the topology
    (density.topology_from), the interactions (contacts.classify), the tables of the points of every molecule in its own
    folder, and three tables of the whole queue in «Анализ» of the folder of the queue. Wilkinson convention, sections
    1-8.

§1 THEORY As density.py §1 (QTAIM) and contacts.py §1 (the kinds of the weak interactions).

§2 ALGORITHM
    wavefunction_of(item): the file of orbitals next to the output of the calculation — «<base>.molden.input» (ORCA,
    orca_2mkl), else the first *.molden.input, *.molden, *.fchk, *.fch of its folder; None when there is none.
    analyse(program, items, cores, step, run): for every item done (state 'done') in turn: run(program, wavefunction,
    cores, inner_step) (multiwfn.run_topology), the orbitals read (orbital_files.read_orbitals) for the bond paths and
    the atoms, the topology, the interactions with the charge of the item; its output «<stem>_topology» and its tables
    «<stem>_qtaim_*.csv» in «Анализ» of its folder (as one search writes them). A failure of one (no file of orbitals,
    Multiwfn found nothing) is its row of the summary, the others go on. step(k, n) between the molecules and inside
    Multiwfn; False from it — InterruptedError.
    tables(results): «summary» — one row per calculation (the counts n, b, r, c, n − b + r − c, the BCPs of chemical
    bonds, the hydrogen, halogen, chalcogen, pnictogen, tetrel bonds and the van der Waals contacts with a BCP, the
    named interactions without one, the strongest hydrogen bond E ≈ (Emamian 2019) and its atoms, the note); «bonds» —
    every BCP of every molecule (molecule, b1 …, atoms, interaction, ρ, ∇²ρ, ε, G, V, H, |V|/G, E ≈); «contacts» —
    every weak interaction, with and without a BCP (contacts.table with the molecule first).

§3 APPLICATIONS
    modules/sextant/batch_actions.py: batch_qtaim — «QTAIM для всех» in the window of a finished queue and «Расчёт →
    QTAIM для очереди…» (a queue chosen by its folder); the tables «batch_qtaim_summary.csv», «…_bonds.csv»,
    «…_contacts.csv».

§4 SPECIFICATION
    Result(name, item, wavefunction Path | None, topology | None, contacts tuple, symbols list, error str, notes tuple,
    artifact — azimuth.runtime.analysis.Artifact | None).
    wavefunction_of(item) -> Path | None; analyse(program, items, cores=1, step=None, run=None, ledger=None) -> [Result]
    (Multiwfn reads a copy taken at the start of each analysis; ledger — the folder of analyses.json);
    tables(results) -> {'summary' | 'bonds' | 'contacts': (header, rows)}; KINDS — the queues it is offered for.

§5 PROCEDURES -- below.

§6 IMPLEMENTATION NOTES
    The point numbers b1, b2 … are those of the tables of one search (density_view.point_labels: the bonds in the order
    of the topology). MOPAC writes no file of orbitals Multiwfn reads: its queues are not offered. ASSUMPTION: an xtb
    queue has a Molden file only when xtb was asked for one; its topology misses nuclei (multiwfn.run_topology warns).

§7 TEST CASES (tests/spectrum/test_batch_qtaim.py)
    Two calculations done with the recorded Multiwfn topology of water (2026.7.15) and one without a file of orbitals:
    two summaries of 3 nuclei, 2 bonds, n − b + r − c = 1, two O–H chemical bonds each in «bonds»; the third — «нет
    файла орбиталей»; items not done are not run; the cancel stops; the tables in the per-molecule «Анализ».

§8 ERROR ANALYSIS As density.py and contacts.py: the numbers are those of Multiwfn at the level of the queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from azimuth.i18n import tr
from modules.spectrum.analysis import contacts, density
from modules.spectrum.wavefunction import field_tables

KINDS = ('orca', 'gaussian', 'psi4', 'xtb')  # the programs whose queues leave a file of orbitals
PATTERNS = ('*.molden.input', '*.molden', '*.fchk', '*.fch')
NAMED = ('hydrogen', 'halogen', 'chalcogen', 'pnictogen', 'tetrel', 'vdw')


@dataclass
class Result:
    name: str
    item: object
    wavefunction: Path | None = None
    topology: object = None
    contacts: tuple = ()
    symbols: list = field(default_factory=list)
    error: str = ''
    notes: tuple = ()
    artifact: object = None  # the copy analysed — attempt id, name, SHA-256


def wavefunction_of(item):
    if not getattr(item, 'output', ''):
        return None
    output = Path(item.output)
    exact = output.with_name(output.name.split('.')[0] + '.molden.input')
    if exact.is_file():
        return exact
    for pattern in PATTERNS:
        found = sorted(p for p in output.parent.glob(pattern) if p.is_file())
        if found:
            return found[0]
    return None


def analyse(program, items, cores=1, step=None, run=None, ledger=None):
    import shutil

    from azimuth.runtime import analysis
    from modules.spectrum.wavefunction import multiwfn
    from modules.spectrum.readers.orbital_files import read_orbitals

    run = run or multiwfn.run_topology
    book = analysis.Ledger(ledger) if ledger is not None else None
    done = [item for item in items if item.state == 'done']
    results = []
    for k, item in enumerate(done):
        if step is not None and step(k, len(done)) is False:
            raise InterruptedError()
        result = Result(item.name, item)
        results.append(result)
        path = wavefunction_of(item)
        result.wavefunction = path
        if path is None:
            result.error = tr('нет файла орбиталей')
            continue

        def inner(_done, _total, k=k):
            return True if step is None else step(k, len(done))

        # the analysis reads a copy of the file taken now — a calculation repeated meanwhile does not
        # change it (T18); its record in the ledger of the queue; a failure is the analysis's, never the calculation's
        staged = path.parent / field_tables.ANALYSIS / f'.az-input-{k}'
        record = None
        try:
            artifact = analysis.snapshot(path, analysis.attempt_of(item.folder), staged)
            result.artifact = artifact
            if book is not None:
                record = book.begin('qtaim', artifact)
            copy = Path(artifact.path)
            cps, text, _number, warnings = run(program, copy, cores, inner)
            orbital_set = read_orbitals(copy.read_text(encoding='utf-8-sig', errors='replace'))
            topology = density.topology_from(cps, orbital_set, warnings)
        except InterruptedError:
            if record is not None:
                book.finish(record, tr('прервано'))
            shutil.rmtree(staged, ignore_errors=True)
            raise
        except (OSError, ValueError, KeyError, IndexError) as exc:
            result.error = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
            if record is not None:
                book.finish(record, result.error)
            shutil.rmtree(staged, ignore_errors=True)
            continue
        shutil.rmtree(staged, ignore_errors=True)
        if record is not None:
            book.finish(record)
        symbols = [a.symbol for a in orbital_set.molecule.atoms]
        found = contacts.classify(orbital_set.molecule, topology, getattr(item, 'charge', 0))
        result.topology, result.contacts, result.symbols, result.notes = topology, found, symbols, tuple(topology.notes)
        stem = path.name.split('.')[0]
        try:  # as one search writes them (density_view.find_points_multiwfn)
            field_tables.save_output(path, 'topology', text)
            tables_ = field_tables.cp_tables(topology, symbols)
            header, rows = contacts.table(found, symbols)
            if rows:
                tables_['qtaim_contacts'] = (header, rows)
            field_tables.write_tables(path.parent, stem, tables_, family=field_tables.QTAIM_TABLES)
            write_bcp_json(path.parent, stem, topology)  # for «Дескрипторы и logK»
            field_tables.save_topology(path, topology)  # shown again when the result is opened
        except OSError:
            pass
    if step is not None:
        step(len(done), len(done))
    return results


def write_bcp_json(folder, stem, topology):
    """The bond critical points of one molecule as numbers (atoms from 0, ρ, ∇²ρ, G, V, H in atomic units) —
    «<stem>_qtaim_bcp.json» in «Анализ», read by modules/spectrum/analysis/descriptors.py."""
    import json

    rows = [{'atoms': [int(k) for k in p.atoms], 'rho': float(p.rho), 'laplacian': float(p.laplacian),
             'G': float(p.kinetic), 'V': float(p.potential), 'H': float(p.energy)}
            for p in topology.points if p.kind == 'bond']
    target = Path(folder) / field_tables.ANALYSIS
    target.mkdir(parents=True, exist_ok=True)
    path = target / f'{stem}_qtaim_bcp.json'
    path.write_text(json.dumps({'version': 1, 'bcp': rows}, indent=1), encoding='utf-8')
    return path


def _ratio(point):
    return abs(point.potential) / point.kinetic if point.kinetic and point.kinetic > 1e-12 else None


def _num(value, digits):
    return '' if value is None else f'{value:.{digits}f}'


def tables(results):
    summary_header = [tr('Молекула'), 'n', 'b', 'r', 'c', 'n − b + r − c', tr('химические связи'), tr('водородные'),
                      tr('галогенные'), tr('халькогенные'), tr('пниктогенные'), tr('тетрельные'), tr('вдВ-контакты'),
                      tr('связи без BCP'), tr('сильнейшая водородная'), tr('E ≈, ккал/моль'), tr('Примечание')]
    bond_header = [tr('Молекула'), '№', tr('Атомы'), tr('Взаимодействие'), 'ρ', '∇²ρ', 'ε', 'G', 'V', 'H', '|V|/G',
                   tr('E ≈, ккал/моль')]
    contact_header = None
    summary, bonds, weak = [], [], []
    for result in results:
        if result.topology is None:
            summary.append([result.name] + [''] * (len(summary_header) - 2) + [result.error])
            continue
        top, symbols = result.topology, result.symbols
        counts = top.counts
        by_point = contacts.by_point(result.contacts)
        tally = {kind: 0 for kind in ('covalent',) + NAMED}
        for c in result.contacts:
            if c.point is not None:
                tally[c.kind] += 1
        unseen = sum(1 for c in result.contacts if c.point is None and c.kind in contacts.ORDER)
        hbs = [c for c in result.contacts if c.kind == 'hydrogen' and c.energy is not None]
        strongest = min(hbs, key=lambda c: c.energy) if hbs else None
        summary.append([result.name, counts['n'], counts['b'], counts['r'], counts['c'], top.poincare_hopf,
                        tally['covalent'], tally['hydrogen'], tally['halogen'], tally['chalcogen'], tally['pnictogen'],
                        tally['tetrel'], tally['vdw'], unseen,
                        contacts.chain(strongest, symbols) if strongest else '',
                        _num(strongest.energy if strongest else None, 2), '; '.join(result.notes)])
        number = 0
        for point in top.points:
            if point.kind != 'bond':
                continue
            number += 1
            contact = by_point.get(id(point))
            atoms = '–'.join(f'{symbols[k]}{k + 1}' for k in point.atoms if 0 <= k < len(symbols))
            bonds.append([result.name, f'b{number}', atoms, contacts.label(contact, symbols) if contact else '',
                          f'{point.rho:.6f}', f'{point.laplacian:+.6f}',
                          '' if point.ellipticity is None else f'{point.ellipticity:.4f}', f'{point.kinetic:.6f}',
                          f'{point.potential:+.6f}', f'{point.energy:+.6f}', _num(_ratio(point), 3),
                          _num(contact.energy if contact else None, 2)])
        header, rows = contacts.table(result.contacts, symbols)
        contact_header = contact_header or header
        weak += [[result.name] + row for row in rows]
    if contact_header is None:
        contact_header = contacts.table((), [])[0]
    return {'summary': (summary_header, summary), 'bonds': (bond_header, bonds),
            'contacts': ([tr('Молекула')] + contact_header, weak)}

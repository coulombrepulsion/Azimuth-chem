"""The interaction energy of two molecules with the counterpoise correction of the basis set superposition error,
in one step.

HEADER
    The interaction energy of a pair with BSSE in one step: a pair of molecules cut out of a crystal (or any dimer) goes
    to Sextant, the task
    «Энергия взаимодействия с BSSE (две молекулы)» makes the five single points as a queue and the table gives ΔE,
    BSSE and ΔE(CP).

§1 THEORY
    At the geometry of the pair AB: ΔE = E_AB(AB) − E_A(A) − E_B(B); the counterpoise correction of Boys & Bernardi
    (Mol. Phys. 19, 553, 1970): ΔE(CP) = E_AB(AB) − E_A(AB) − E_B(AB), where E_A(AB) is A with the basis functions of B
    on ghost atoms (no nuclei, no electrons — ORCA «Sym : x y z», as in binding.py); BSSE = ΔE(CP) − ΔE =
    [E_A(A) − E_A(AB)] + [E_B(B) − E_B(AB)] ≥ 0. Both are the interaction at the frozen geometry (no deformation
    energy): the energy of a pair of a crystal, as in CrystalExplorer and PIXEL tables.
§2 ALGORITHM fragments(molecule): the parts of the structure by its bonds (builder.connections); exactly two — A (the
    one with the first atom) and B. plan(molecule, calc): the items AB, A in the basis of AB (ghosts B), B in the basis
    of AB (ghosts A), A alone, B alone — all «Энергия» (props role 'ab' / 'a_ab' / 'b_ab' / 'a' / 'b', ghosts); the
    charges: the pair neutral and closed-shell (each part validated: an even number of electrons). energies(queue) ->
    dict in kcal/mol.
§3 APPLICATIONS
    modules/sextant/batch_actions.py start_interaction (the task in run_actions.run_calculation), batch_item_input (the
    ghosts), batch_complete (the table «interaction.csv», the message).
§4 SPECIFICATION
    TASK; fragments(molecule) -> [[indices]]; plan(molecule, calc) -> [BatchItem]; energies(queue) -> {'dE', 'bsse',
    'dE_cp'} (None where missing); table(queue) -> (header, rows); note(molecule, calc) -> str.
§6 NOTES
    ORCA only (the ghost atoms). A charged pair or open shells — not here (the charges of the parts are not known from
    the structure): an error says so.
§7 TEST CASES (tests/sextant/test_interaction.py)
"""

from __future__ import annotations

from azimuth.i18n import tr

HARTREE_KCAL = 627.5094740631


def fragments(molecule):
    from modules.compass.chemistry.builder import connections

    n = len(molecule.atoms)
    neighbours = [[] for _ in range(n)]
    for i, j, _ in connections(molecule):
        neighbours[i].append(j)
        neighbours[j].append(i)
    seen, parts = set(), []
    for start in range(n):
        if start in seen:
            continue
        part, stack = [], [start]
        seen.add(start)
        while stack:
            k = stack.pop()
            part.append(k)
            for m in neighbours[k]:
                if m not in seen:
                    seen.add(m)
                    stack.append(m)
        parts.append(sorted(part))
    return parts


def _parts(molecule, calc):
    from azimuth.core import Molecule

    parts = fragments(molecule)
    if len(parts) != 2:
        raise ValueError(tr('Энергия взаимодействия: нужны ровно две молекулы (части структуры без связей между ними), '
                            'а их {}. В кристалле выделите две молекулы и перенесите их в «Компас · Молекула».').format(len(parts)))
    if calc.charge != 0 or calc.multiplicity != 1:
        raise ValueError(tr('Энергия взаимодействия считается здесь для нейтральной пары с закрытыми оболочками '
                            '(заряд 0, мультиплетность 1).'))
    out = []
    for part in parts:
        fragment = Molecule(molecule.title, tuple(molecule.atoms[k] for k in part), None)
        fragment.validate_state(0, 1)
        out.append((part, fragment))
    return out


def plan(molecule, calc):
    from modules.sextant.batch import BatchItem

    (a, mol_a), (b, mol_b) = _parts(molecule, calc)
    title = molecule.title or molecule.formula
    common = {'task': 'Энергия'}
    return [
        BatchItem(f'{title} · AB', molecule, 0, 1, props={**common, 'role': 'ab'}),
        BatchItem(tr('{} · A ({}) в базисе пары').format(title, mol_a.formula), molecule, 0, 1,
                  props={**common, 'role': 'a_ab', 'ghosts': list(b)}),
        BatchItem(tr('{} · B ({}) в базисе пары').format(title, mol_b.formula), molecule, 0, 1,
                  props={**common, 'role': 'b_ab', 'ghosts': list(a)}),
        BatchItem(tr('{} · A ({})').format(title, mol_a.formula), mol_a, 0, 1, props={**common, 'role': 'a'}),
        BatchItem(tr('{} · B ({})').format(title, mol_b.formula), mol_b, 0, 1, props={**common, 'role': 'b'}),
    ]


def note(molecule, calc):
    try:
        (_, a), (_, b) = _parts(molecule, calc)
    except ValueError as exc:
        return str(exc)
    return tr('Пять расчётов одной геометрии очередью: пара, A ({}) и B ({}) в базисе пары (атомы другой молекулы — '
              'призраки), A и B отдельно; затем ΔE, BSSE и ΔE(CP) по Бойсу — Бернарди. Только ORCA.').format(a.formula, b.formula)


def energies(queue):
    found = {item.props.get('role'): item.energy for item in queue.items if item.state == 'done'}
    out = {'dE': None, 'bsse': None, 'dE_cp': None}
    if all(found.get(k) is not None for k in ('ab', 'a', 'b')):
        out['dE'] = (found['ab'] - found['a'] - found['b']) * HARTREE_KCAL
    if all(found.get(k) is not None for k in ('ab', 'a_ab', 'b_ab')):
        out['dE_cp'] = (found['ab'] - found['a_ab'] - found['b_ab']) * HARTREE_KCAL
    if out['dE'] is not None and out['dE_cp'] is not None:
        out['bsse'] = out['dE_cp'] - out['dE']
    return out


def table(queue):
    found = energies(queue)

    def number(value):
        return '' if value is None else f'{value:.2f}'

    header = [tr('ΔE, ккал/моль'), tr('BSSE, ккал/моль'), tr('ΔE(CP), ккал/моль')]
    return header, [[number(found['dE']), number(found['bsse']), number(found['dE_cp'])]]

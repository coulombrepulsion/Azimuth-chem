"""Binding of a metal ion by a set of ligands: the ion, every ligand and its complex in one queue, the binding energies
and, for ORCA, the counterpoise correction of the basis set superposition error.

HEADER
    The user's series (Cs_full.sdf, Sr.sdf: 44 ligands with logK of Cs⁺ and Sr²⁺) needs ΔE of M⁺ + L → ML for each one.
    Before: the complexes were built by hand, three calculations per ligand were started and subtracted in a table.
    Here a queue does it: «Комплексы с ионом…» puts the ion into each ligand (place_ion), the queue computes the ion,
    each ligand and each complex (the complex built again on the optimized ligand when it is ready), with BSSE three
    single points more per complex, and the table gives ΔE, ΔE(CP), ΔG. Wilkinson convention, sections 1-8.

§1 THEORY
    ΔE_bind = E(ML) − E(L) − E(M) (hartree → kcal/mol, 627.5094740631), with the ligand and the complex optimized: it
    includes the deformation of the ligand. Counterpoise (Boys & Bernardi, Mol. Phys. 19, 553 (1970)): at the geometry
    of the complex, BSSE = [E_L(L basis) − E_L(ML basis)] + [E_M(M basis) − E_M(ML basis)] ≥ 0; ΔE_CP = ΔE_bind + BSSE.
    The functions of the partner stay on «ghost» atoms without nucleus and electrons — ORCA: «Cs : x y z» (the colon
    after the symbol; ORCA 6.1 manual, 2.11 «Counterpoise Corrections»). ΔG_bind = G(ML) − G(L) − G(M) when the queue
    computes frequencies; G of the atomic ion — E plus the translational and electronic terms (thermo.thermochemistry of
    one atom: 5/2 RT and the Sackur–Tetrode entropy at 1 atm, 298.15 K). MOPAC: ΔHf(ML) − ΔHf(L) − ΔHf(M).
    The starting place of the ion (place_ion): the minimum of
        U(p) = Σ_donors w(r) + Σ_others k·max(0, r_min − r)², w(r) = (r − d₀)² − 1.44 for r < d₀ + 1.2, else 0,
    over p; d₀ — a typical M–O distance of the ion (IONS; + DONORS[symbol] for N, S …), r_min — H_GAP = 2.8 Å from H
    and d₀ + HEAVY_GAP from the other atoms. Every donor in its well lowers U by up to 1.44, so the minimum is the site
    that holds the most
    donors at d₀ without running into the ligand: the cavity of a crown, between the two O of a carboxylate, the N,O
    chelate of an amino acid. It is a start: the optimization of the complex finds the real place.

§2 ALGORITHM place_ion(ligand, symbol): seeds — the position along the lone pair of each donor at d₀, the centres of the
    pairs and triples of donors that can share the ion, the centre of all donors; from each the gradient descent of U
    (Barzilai –Borwein steps, 200 at most); the lowest. The ion is the last atom of the complex (the ligand keeps its
    numbering). plan(ligands, symbol, charge, bsse, kind): [BatchItem] — the ion (task «Энергия»: one atom is not
    optimized), then per ligand L and ML (props role 'ion' / 'ligand' / 'complex', ligand_name, complex_of — the index
    of L). prepare(queue, item): before a complex runs — rebuilt on the geometry of its ligand when that is done.
    follow_ups(queue, item): after a complex is done with bsse — three single points: L at the geometry of ML (role
    'bsse_l'), L with the ion a ghost ('bsse_lg'), the ion with the ligand ghosts ('bsse_mg'). input_text(kind,
    molecule, calc, ghosts): the ORCA input with the ghost atoms (generated for a charge of the same parity of electrons
    as the fragment, then the charge of the fragment written back). energies(queue) -> rows per ligand; table(queue) ->
    (header, rows); descriptor_rows(queue) — for «Дескрипторы».

§3 APPLICATIONS
    batch_actions.start_binding (the dialog BindingDialog of binding_view.py), start_next_batch_item (prepare,
    input_text), batch_job_finished (follow_ups), batch_complete (the table «binding_energies.csv»).

§4 SPECIFICATION
    IONS {symbol: (charge, d₀ Å)}; place_ion(ligand, symbol) -> Molecule; plan(…) -> (items, extra);
    prepare(queue, item) -> bool (rebuilt); follow_ups(queue, item) -> [BatchItem] (appended); input_text(…) -> str;
    energies(queue) -> [dict]; table(queue) -> (header, rows); descriptor_rows(queue) -> {ligand name: {column: value}}.

§6 NOTES
    ASSUMPTION: one ion per complex; closed shells (multiplicity of the complex — that of the ligand, the ions of IONS
    have none unpaired). The ion is placed on the ligand as given or as optimized alone; a ligand that must change its
    conformation to wrap the ion (a podand) is found only as far as the optimization of the complex goes.

§7 TEST CASES (tests/sextant/test_binding.py) The ion in a model 18-crown-6 goes into the cavity (six O at d₀ ± 0.3 Å);
    between the O of a formate; the plan of two ligands — 5 items with their charges; the ghost input marks the ion «Cs
    :» and keeps the charge of the fragment; the follow-ups of a complex — 3 items; ΔE and ΔE(CP) of recorded energies.
"""

from __future__ import annotations

import math
from dataclasses import replace

import numpy as np

from azimuth.i18n import tr

HARTREE_KCAL = 627.5094740631
# charge, a typical distance M–O in complexes (Å; Shannon radii + 1.35 Å of O²⁻ for CN 6–8, rounded)
IONS = {'Li': (1, 1.98), 'Na': (1, 2.38), 'K': (1, 2.78), 'Rb': (1, 2.92), 'Cs': (1, 3.10), 'Ag': (1, 2.42),
        'Mg': (2, 2.08), 'Ca': (2, 2.40), 'Sr': (2, 2.58), 'Ba': (2, 2.78), 'Zn': (2, 2.10), 'Cd': (2, 2.32),
        'Pb': (2, 2.55)}
DONORS = {'O': 0.0, 'N': 0.08, 'S': 0.40, 'P': 0.40, 'F': -0.05, 'Cl': 0.45, 'Br': 0.6, 'I': 0.8, 'Se': 0.5}
WELL = 1.2  # Å above d₀ where a donor still pulls
DEPTH = WELL ** 2
PUSH = 10.0
H_GAP = 2.8  # Å: the ion keeps this far from H (M…H of complexes ≥ 2.8 Å)
HEAVY_GAP = 0.25  # Å above d₀: from C and the other atoms that do not coordinate
ROLES = ('ion', 'ligand', 'complex', 'bsse_l', 'bsse_lg', 'bsse_mg')


def ion_name(symbol, charge):
    return f'{symbol}{"" if charge == 1 else charge}+'


def _neighbours(molecule):
    from modules.compass.chemistry.builder import connections

    bonds = molecule.bonds if molecule.bonds is not None else connections(molecule)
    near = {k: [] for k in range(len(molecule.atoms))}
    for bond in bonds:
        i, j = bond[0], bond[1]
        near[i].append(j)
        near[j].append(i)
    return near


def _energy_and_gradient(p, donors, others):
    e, g = 0.0, np.zeros(3)
    for x, d0 in donors:
        v = p - x
        r = float(np.linalg.norm(v)) or 1e-9
        if r < d0 + WELL:
            e += (r - d0) ** 2 - DEPTH
            g += 2.0 * (r - d0) * v / r
    for x, rmin in others:
        v = p - x
        r = float(np.linalg.norm(v)) or 1e-9
        if r < rmin:
            e += PUSH * (rmin - r) ** 2
            g -= 2.0 * PUSH * (rmin - r) * v / r
    return e, g


def _descend(p, donors, others, steps=200):
    e, g = _energy_and_gradient(p, donors, others)
    step = 0.05
    for _ in range(steps):
        if float(np.linalg.norm(g)) < 1e-5:
            break
        q = p - step * g
        e2, g2 = _energy_and_gradient(q, donors, others)
        s, y = q - p, g2 - g
        sy = float(s @ y)
        step = min(0.5, max(1e-3, float(s @ s) / sy)) if sy > 1e-12 else 0.05
        if e2 > e + 1e-9:  # no progress: a smaller step from the same place
            step = 0.25 * float(np.linalg.norm(s)) / max(float(np.linalg.norm(g)), 1e-9)
            continue
        p, e, g = q, e2, g2
    return p, e


def place_ion(ligand, symbol):
    """The ligand with the ion appended (the last atom) at the minimum of U (§1)."""
    from azimuth.core import Atom, Molecule

    if symbol not in IONS:
        raise ValueError(tr(f'Ион {symbol}: нет в списке ионов.'))
    d0 = IONS[symbol][1]
    atoms = ligand.atoms
    if not atoms:
        raise ValueError(tr('Пустой лиганд.'))
    xyz = np.array([a.position for a in atoms], dtype=float)
    donors_idx = [k for k, a in enumerate(atoms) if a.symbol in DONORS]
    donors = [(xyz[k], d0 + DONORS[atoms[k].symbol]) for k in donors_idx]
    others = [(xyz[k], H_GAP if a.symbol == 'H' else d0 + HEAVY_GAP) for k, a in enumerate(atoms) if k not in donors_idx]
    seeds = []
    near = _neighbours(ligand)
    for k in donors_idx:
        bonded = near.get(k, [])
        away = xyz[k] - (xyz[bonded].mean(axis=0) if bonded else xyz.mean(axis=0))
        if float(np.linalg.norm(away)) < 1e-6:
            away = np.array([0.0, 0.0, 1.0])
        seeds.append(xyz[k] + d0 * away / np.linalg.norm(away))
    reach = 2 * d0 + 0.8
    pairs = [(i, j) for n, i in enumerate(donors_idx) for j in donors_idx[n + 1:]
             if np.linalg.norm(xyz[i] - xyz[j]) < reach]
    seeds += [(xyz[i] + xyz[j]) / 2 for i, j in pairs]
    triples = [(i, j, k) for i, j in pairs for k in donors_idx if k > j
               and np.linalg.norm(xyz[i] - xyz[k]) < reach and np.linalg.norm(xyz[j] - xyz[k]) < reach]
    rng = np.random.default_rng(7)
    if len(triples) > 300:
        triples = [triples[t] for t in rng.choice(len(triples), 300, replace=False)]
    seeds += [(xyz[i] + xyz[j] + xyz[k]) / 3 for i, j, k in triples]
    if donors_idx:
        seeds.append(xyz[donors_idx].mean(axis=0))
    else:  # no donor at all: beside the ligand, along its thinnest direction
        centre = xyz.mean(axis=0)
        spread = np.linalg.eigh(np.cov((xyz - centre).T) if len(xyz) > 2 else np.eye(3))[1][:, 0]
        seeds.append(centre + (d0 + 1.5) * spread)
    best, low = None, math.inf
    for seed in seeds:
        p, e = _descend(np.array(seed, dtype=float), donors, others)
        if e < low - 1e-9:
            best, low = p, e
    return Molecule(ligand.title, tuple(atoms) + (Atom(symbol, *map(float, best)),), None)


def ligand_part(complex_molecule):
    from azimuth.core import Molecule

    return Molecule(complex_molecule.title, tuple(complex_molecule.atoms[:-1]), None)


def plan(ligands, symbol, charge=None, bsse=False, kind='orca'):
    """ligands: [(name, Molecule, charge, multiplicity, props, formal)] -> ([BatchItem], extra)."""
    from azimuth.core import Atom, Molecule
    from modules.sextant.batch import BatchItem

    charge = IONS[symbol][0] if charge is None else int(charge)
    ion = Molecule(ion_name(symbol, charge), (Atom(symbol, 0.0, 0.0, 0.0),), None)
    items = [BatchItem(ion_name(symbol, charge), ion, charge, 1, props={'role': 'ion', 'task': 'Энергия'})]
    for name, molecule, q, multiplicity, props, formal in ligands:
        records = {k: v for k, v in (props or {}).items()}
        items.append(BatchItem(name, molecule, int(q), int(multiplicity), formal=tuple(formal or ()),
                               props={**records, 'role': 'ligand', 'ligand_name': name}))
        items.append(BatchItem(f'{name} · {ion_name(symbol, charge)}', place_ion(molecule, symbol), int(q) + charge,
                               int(multiplicity), props={**records, 'role': 'complex', 'ligand_name': name,
                                                         'complex_of': len(items) - 1}))
    extra = {'binding': {'ion': symbol, 'charge': charge, 'bsse': bool(bsse and kind == 'orca')}}
    return items, extra


def prepare(queue, item):
    """Before a complex runs: rebuilt on the optimized geometry of its ligand (when that one is done)."""
    if item.props.get('role') != 'complex':
        return False
    k = item.props.get('complex_of')
    if not isinstance(k, int) or not 0 <= k < len(queue.items):
        return False
    ligand = queue.items[k]
    if ligand.state != 'done' or ligand.geometry is None or len(ligand.geometry.atoms) != len(item.molecule.atoms) - 1:
        return False
    symbol = item.molecule.atoms[-1].symbol
    if symbol not in IONS:
        return False
    item.molecule = replace(place_ion(replace(ligand.geometry, bonds=None), symbol), title=item.name)
    return True


def follow_ups(queue, item):
    """The three single points of the counterpoise correction of a complex just done (appended to the queue)."""
    from modules.sextant.batch import BatchItem

    info = (queue.extra or {}).get('binding') or {}
    if not info.get('bsse') or item.props.get('role') != 'complex' or item.state != 'done' or item.geometry is None:
        return []
    k = queue.items.index(item)
    if any(other.props.get('of') == k for other in queue.items):
        return []  # already there (the queue taken up again)
    geometry = item.geometry
    n = len(geometry.atoms) - 1
    q_ion = int(info.get('charge', 1))
    q_ligand = item.charge - q_ion
    base = item.props.get('ligand_name', item.name)
    common = {'ligand_name': base, 'of': k, 'task': 'Энергия'}
    added = [
        BatchItem(base + tr(' · L при геометрии комплекса'), ligand_part(geometry), q_ligand, item.multiplicity,
                  props={**common, 'role': 'bsse_l'}),
        BatchItem(base + tr(' · L в базисе комплекса'), geometry, q_ligand, item.multiplicity,
                  props={**common, 'role': 'bsse_lg', 'ghosts': [n]}),
        BatchItem(base + tr(' · ион в базисе комплекса'), geometry, q_ion, 1,
                  props={**common, 'role': 'bsse_mg', 'ghosts': list(range(n))}),
    ]
    queue.items.extend(added)
    return added


def input_text(kind, molecule, calc, ghosts):
    """The input of ORCA with the atoms ghosts as «Sym : x y z», for the charge of calc (the charge written into it)."""
    from azimuth.core import Z
    from modules.sextant.inputs import input_files

    if kind != 'orca':
        raise ValueError(tr('Поправка BSSE (атомы-призраки) — только для ORCA.'))
    ghosts = sorted(set(int(k) for k in ghosts))
    # the input is checked for the electrons of all the atoms: a charge of the same parity as the fragment's electrons
    # passes the check (the charge is limited to ±20, the nuclei of the ghosts are not), then the real one is written
    nuclear = sum(Z[molecule.atoms[k].symbol] for k in ghosts)
    files = input_files(kind, molecule, replace(calc, charge=calc.charge + nuclear % 2), ())
    text = next(iter(files.values()))
    lines = text.split('\n')
    start = next(k for k, line in enumerate(lines) if line.lstrip().lower().startswith('* xyz'))
    head = lines[start].split()
    lines[start] = f'* xyz {calc.charge} {head[-1]}'
    for n, k in enumerate(ghosts):
        row = start + 1 + k
        parts = lines[row].split()
        if parts[0] != molecule.atoms[k].symbol:
            raise ValueError(tr('Строки координат входного файла не совпали с атомами.'))
        lines[row] = f'{parts[0]} : ' + ' '.join(parts[1:])
    return '\n'.join(lines)


def _ion_gibbs(item):
    if item.energy is None or item.geometry is None and item.molecule is None:
        return None
    from modules.spectrum.analysis import thermo

    try:
        found = thermo.thermochemistry(item.geometry or item.molecule, (), item.energy, multiplicity=item.multiplicity)
    except (ValueError, ZeroDivisionError):
        return None
    return found.total(found.gibbs)


def energies(queue):
    """[{ligand, ΔE, ΔE_CP, BSSE, ΔG, ΔH (MOPAC), complex item}] — kcal/mol, None where something is missing."""
    items = queue.items
    ion = next((item for item in items if item.props.get('role') == 'ion'), None)
    with_freq = 'Freq' in _task_keyword(queue.calc)
    rows = []
    for k, complex_ in enumerate(items):
        if complex_.props.get('role') != 'complex':
            continue
        j = complex_.props.get('complex_of')
        ligand = items[j] if isinstance(j, int) and 0 <= j < len(items) else None
        row = {'ligand': complex_.props.get('ligand_name', complex_.name), 'complex': complex_, 'dE': None,
               'dE_cp': None, 'bsse': None, 'dG': None, 'dH': None}
        ready = all(x is not None and x.state == 'done' for x in (ion, ligand, complex_))
        if ready and None not in (complex_.energy, ligand.energy, ion.energy):
            row['dE'] = (complex_.energy - ligand.energy - ion.energy) * HARTREE_KCAL
            parts = {other.props.get('role'): other for other in items if other.props.get('of') == k}
            l_own, l_ghost, m_ghost = parts.get('bsse_l'), parts.get('bsse_lg'), parts.get('bsse_mg')
            if all(x is not None and x.state == 'done' and x.energy is not None for x in (l_own, l_ghost, m_ghost)):
                row['bsse'] = ((l_own.energy - l_ghost.energy) + (ion.energy - m_ghost.energy)) * HARTREE_KCAL
                row['dE_cp'] = row['dE'] + row['bsse']
            if with_freq and None not in (complex_.gibbs, ligand.gibbs):
                ion_g = ion.gibbs if ion.gibbs is not None else _ion_gibbs(ion)
                if ion_g is not None:
                    row['dG'] = (complex_.gibbs - ligand.gibbs - ion_g) * HARTREE_KCAL
        if ready and None not in (complex_.heat, ligand.heat, ion.heat):
            row['dH'] = complex_.heat - ligand.heat - ion.heat
        rows.append(row)
    return rows


def _task_keyword(calc):
    from azimuth.core import TASKS

    return TASKS.get(getattr(calc, 'task', ''), '') if calc is not None else ''


def table(queue):
    header = [tr('Лиганд'), tr('ΔE связывания, ккал/моль'), tr('BSSE, ккал/моль'), tr('ΔE(CP), ккал/моль'),
              tr('ΔG связывания, ккал/моль'), tr('ΔΔHf связывания, ккал/моль')]

    def number(value):
        return '' if value is None else f'{value:.2f}'

    rows = [[row['ligand'], number(row['dE']), number(row['bsse']), number(row['dE_cp']), number(row['dG']),
             number(row['dH'])] for row in energies(queue)]
    return header, rows


def descriptor_rows(queue):
    out = {}
    for row in energies(queue):
        values = {tr('ΔE связывания, ккал/моль'): row['dE'], tr('BSSE, ккал/моль'): row['bsse'],
                  tr('ΔE(CP), ккал/моль'): row['dE_cp'], tr('ΔG связывания, ккал/моль'): row['dG'],
                  tr('ΔΔHf связывания, ккал/моль'): row['dH']}
        out[row['ligand']] = {k: v for k, v in values.items() if v is not None}
    return out

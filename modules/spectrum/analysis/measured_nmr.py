"""The measured ¹H and ¹³C shifts of the molecules of the course — filled into «Сравнить с экспериментом…» of the NMR
tab when the structure of the result is one of them (analysis/measured.py tells the molecule).

§1 PURPOSE
    A calculation of the NMR of acetone or pyridine is judged against the spectrum measured, and the student should
    not have to look the numbers up and number the atoms by hand: the window opens with the shifts of the table, each
    signal already on the atoms of the calculation that it belongs to.
§2 DATA (data/measured_nmr.json)
    Fulmer et al., Organometallics 29, 2176 (2010), Tables S1 and S2 — the shifts of common solvents and gases as trace
    impurities in twelve deuterated solvents (298 K): 14 of the 30 molecules (methane, ethane, ethylene, CO₂, methanol,
    ethanol, acetic acid, acetone, acetonitrile, benzene, cyclohexane, furan, pyridine, toluene; water left out). The
    data are published facts with their source named; no database license applies (nmrshiftdb2 was not used: its
    license asks an OSI license of the program that relies on it). OH and NH are left out: their shift moves with the
    concentration and the water of the sample. A signal is given on heavy atoms of the SMILES of the molecule in
    data/measured_molecules.json (0-based): ¹³C — the carbon atoms themselves, ¹H — the hydrogens on them.
§3 THE ATOMS OF THE CALCULATION
    The atoms equivalent by the graph (the classes of a Weisfeiler–Lehman refinement of the bonded graph with explicit
    hydrogens, run on the SMILES graph and the computed structure together, so the classes are shared) are the atoms a
    signal of the table belongs to: the two ortho carbons of toluene are one class, its methyl hydrogens another.
    The calculation is in the gas or a continuum model and the table in solution: ¹H differ by about 0.1–0.3 ppm, ¹³C by
    1–2 ppm from that alone (benzene-d6 and toluene-d8 shift the protons by more: the ring current of the solvent).
§4 SPECIFICATION
    entry(molecule) -> [signal] | None; solvents(molecule, element) -> [str] (those where at least one signal of the
    element has a value, in the order of the table, CDCl3 first); atoms(molecule, signal) -> [0-based atoms of the calculation];
    text(molecule, element, solvent=DEFAULT) -> str — lines «C2 C6 149.90  # CH(2,6)» for nmr_compare.parse, the source
    on the first line ('' when there is nothing); SOURCE, DEFAULT.
§7 TESTS tests/spectrum/test_measured_nmr.py.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

DATA = Path(__file__).resolve().parent / 'data' / 'measured_nmr.json'
SOURCE = 'Fulmer et al., Organometallics 29, 2176 (2010)'
DEFAULT = 'CDCl3'


@lru_cache(maxsize=1)
def _data():
    return json.loads(DATA.read_text(encoding='utf-8'))


def _key(molecule):
    from modules.spectrum.analysis import measured

    found = measured.identify(molecule)
    return found['key'] if found else None


def entry(molecule):
    key = _key(molecule)
    return _data()['molecules'].get(key) if key else None


def _classes(symbols, links):
    """The class of each atom after the refinement: equal for atoms the bonded graph cannot tell apart."""
    near = [[] for _ in symbols]
    for i, j in links:
        near[i].append(j)
        near[j].append(i)
    labels = list(symbols)
    for _ in range(len(symbols)):
        keys = [(labels[i], tuple(sorted(labels[j] for j in near[i]))) for i in range(len(symbols))]
        ranks = {k: str(n) for n, k in enumerate(sorted(set(keys)))}
        new = [ranks[k] for k in keys]
        if len(set(new)) == len(set(labels)):
            labels = new
            break
        labels = new
    return labels, near


def atoms(molecule, signal):
    """The 0-based atoms of the calculation that the signal of the table is on."""
    from modules.compass.chemistry.builder import connections
    from modules.compass.chemistry.names import smiles_graph
    from modules.spectrum.analysis import measured

    known = measured.identify(molecule)
    if known is None:
        return []
    symbols, links, _orders = smiles_graph(known['smiles'])
    mine = [a.symbol for a in molecule.atoms]
    shift = len(symbols)
    together = list(symbols) + mine
    bonds = [(i, j) for i, j in links] + [(i + shift, j + shift) for i, j, *_ in connections(molecule)]
    labels, near = _classes(together, bonds)
    if signal['nucleus'] == 'C':
        wanted = {labels[i] for i in signal['atoms']}
    else:
        wanted = {labels[j] for i in signal['atoms'] for j in near[i] if together[j] == signal['nucleus']}
    return [k - shift for k in range(shift, len(together))
            if labels[k] in wanted and together[k] == signal['nucleus']]


def solvents(molecule, element):
    signals = [s for s in (entry(molecule) or []) if s['nucleus'] == element]
    order = _data()['solvents']
    found = [name for name in order if any(name in s['shifts'] for s in signals)]
    return sorted(found, key=lambda name: name != DEFAULT)


def text(molecule, element, solvent=DEFAULT):
    signals = [s for s in (entry(molecule) or []) if s['nucleus'] == element and solvent in s['shifts']]
    lines = []
    for signal in signals:
        where = atoms(molecule, signal)
        if where:
            names = ' '.join(f'{element}{k + 1}' for k in where)
            lines.append(f"{names} {signal['shifts'][solvent]:.2f}  # {signal['label']}")
    if not lines:
        return ''
    return '\n'.join([f'# {SOURCE}, {solvent}'] + lines)

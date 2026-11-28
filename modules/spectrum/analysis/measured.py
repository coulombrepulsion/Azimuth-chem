"""The measured values of the molecules of the course next to a result: frequencies, bonds, dipole moment, ionization
energy, enthalpy of formation.

§1 PURPOSE
    A student computes water, benzene or acetone and sees at once how far the method is from experiment: the
    harmonic frequencies against the observed fundamentals (and the factor that brings them together), the bond
    lengths, the dipole moment; the ionization energy and the enthalpy of formation of the gas are given for the
    calculations that compute them (ΔSCF, a thermochemical recipe). The data — data/measured_molecules.json (30
    molecules of the course, NIST CCCBDB; the source of each value in the file).
§2 ALGORITHM
    Recognition: the graph of the structure (builder.connections — the bonds of Compass) as a multiset of atom
    environments, each atom with the sorted symbols of its neighbours; the same of the SMILES of an entry
    (names.smiles_graph, explicit hydrogens). Equal multisets — the same molecule; for the 30 molecules of the file
    every multiset is distinct (tests). Conformers are not told apart: the values are those of the conformer the
    note of the entry names.
    Frequencies: a degenerate fundamental counts as many modes as its degeneracy (E, Π — 2; T, F — 3). When the
    measured modes are as many as the computed real ones, both are sorted and paired in order — a pairing by
    position, not by symmetry: two close modes can be swapped, which changes little in the statistics (said). The
    mean absolute deviation, the mean ratio, the factor of least squares c = Σ ν·ω / Σ ω² (ν measured, ω computed)
    and the deviation after it. Otherwise — no pairing, with the reason.
    Bonds: for each pair of elements of the entry, every computed bond of that pair goes to the measured value of the
    pair nearest to it; per measured value — the mean of its computed bonds and the difference.
§4 SPECIFICATION
    molecules() -> [dict]; SOURCE; identify(molecule) -> dict | None; name(entry, lang=None) -> str;
    modes(entry) -> [(label, cm⁻¹)] expanded by degeneracy; vibrations(entry, computed) -> Vibrations;
    bonds(entry, molecule) -> [BondRow]; compare(entry, output) -> Comparison; url(entry).
§7 TESTS tests/spectrum/test_measured.py.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from azimuth.i18n import tr

DATA = Path(__file__).resolve().parent / 'data' / 'measured_molecules.json'
SOURCE = 'NIST CCCBDB, Release 22 (2022), cccbdb.nist.gov'
ZERO = 1.0  # cm⁻¹: |ω| below it — a translation or a rotation


@lru_cache(maxsize=1)
def _data():
    return json.loads(DATA.read_text(encoding='utf-8'))


def molecules():
    return _data()['molecules']


def url(entry):
    return _data()['url'].format(entry['cas'].replace('-', ''))


def name(entry, lang=None):
    from azimuth import i18n

    return entry['name'].get(lang or i18n.LANG) or entry['name']['en']


def _environments(symbols, links):
    neighbours = [[] for _ in symbols]
    for i, j in links:
        neighbours[i].append(symbols[j])
        neighbours[j].append(symbols[i])
    return Counter((s, tuple(sorted(n))) for s, n in zip(symbols, neighbours))


def smiles_signature(smiles):
    """The signature of the graph of a SMILES (explicit hydrogens); None when it is not read."""
    from modules.compass.chemistry.names import smiles_graph

    try:
        symbols, links, _orders = smiles_graph(smiles)
    except (ValueError, KeyError, IndexError):
        return None
    return frozenset(_environments(symbols, [(i, j) for i, j in links]).items())


@lru_cache(maxsize=1)
def _signatures():
    return tuple((smiles_signature(entry['smiles']), entry) for entry in molecules())


def signature(molecule):
    from modules.compass.chemistry.builder import connections

    symbols = [a.symbol for a in molecule.atoms]
    return frozenset(_environments(symbols, [(i, j) for i, j, *_ in connections(molecule)]).items())


LARGEST = 40  # atoms: a larger structure is not looked for (neither here nor in CCCBDB)


def identify(molecule):
    """The entry of the molecule, or None (another molecule, or no structure)."""
    if not searchable(molecule):
        return None
    mine = signature(molecule)
    return next((entry for key, entry in _signatures() if key == mine), None)


def searchable(molecule):
    """A structure small enough to be looked for among the molecules of experiment."""
    return molecule is not None and bool(getattr(molecule, 'atoms', None)) and len(molecule.atoms) <= LARGEST


def degeneracy(label):
    first = (label or 'A')[0]
    return 3 if first in 'TF' else 2 if first in 'EΠ' else 1


def modes(entry, key='fundamentals'):
    """The measured fundamentals (key 'harmonic' — the harmonic frequencies of the entry, where CCCBDB has them),
    each as often as its degeneracy, ascending."""
    return sorted(((label, float(value)) for label, value in entry.get(key) or ()
                   for _ in range(degeneracy(label))), key=lambda p: p[1])


@dataclass(frozen=True)
class Vibrations:
    pairs: tuple = ()  # (computed ω, measured ν, label)
    reason: str = ''  # why there is no pairing
    mean_abs: float | None = None  # cm⁻¹, ω − ν
    mean_ratio: float | None = None  # mean ν/ω
    factor: float | None = None  # least squares: ν ≈ c·ω
    mean_abs_scaled: float | None = None  # cm⁻¹, c·ω − ν


def vibrations(entry, computed, key='fundamentals'):
    """computed — the frequencies of the result (cm⁻¹; the imaginary ones negative)."""
    measured = modes(entry, key)
    if not measured:
        return Vibrations(reason=tr('В CCCBDB для этой молекулы нет опытных частот.'))
    # the translations and rotations some programs print as 0.00 are not vibrations
    real = sorted(float(w) for w in computed if w > ZERO)
    if any(w < -ZERO for w in computed):
        return Vibrations(reason=tr('В результате есть мнимые частоты: это не минимум, сравнивать с опытом рано.'))
    if len(real) != len(measured):
        return Vibrations(reason=tr('Частот в расчёте {}, в опыте {}: пары по порядку не составить.').format(
            len(real), len(measured)))
    pairs = tuple((w, nu, label) for w, (label, nu) in zip(real, measured))
    deltas = [w - nu for w, nu, _ in pairs]
    factor = sum(w * nu for w, nu, _ in pairs) / sum(w * w for w, _, _ in pairs)
    return Vibrations(pairs, '', sum(abs(d) for d in deltas) / len(deltas),
                      sum(nu / w for w, nu, _ in pairs) / len(pairs), factor,
                      sum(abs(factor * w - nu) for w, nu, _ in pairs) / len(pairs))


@dataclass(frozen=True)
class BondRow:
    pair: str  # 'C–H'
    measured: float  # Å
    computed: float | None  # the mean of the computed bonds nearest to this value, Å
    count: int  # how many computed bonds

    @property
    def delta(self):
        return None if self.computed is None else self.computed - self.measured


def bonds(entry, molecule):
    from math import dist

    from modules.compass.chemistry.builder import connections

    atoms = molecule.atoms
    lengths = {}
    for i, j, *_ in connections(molecule):
        key = tuple(sorted((atoms[i].symbol, atoms[j].symbol)))
        lengths.setdefault(key, []).append(dist(atoms[i].position, atoms[j].position))
    rows = []
    for a, b in dict.fromkeys(tuple(sorted((x, y))) for x, y, *_ in entry['bonds']):
        values = [r for x, y, r, *_ in entry['bonds'] if tuple(sorted((x, y))) == (a, b)]
        taken = {k: [] for k in range(len(values))}
        for length in lengths.get((a, b), []):
            taken[min(range(len(values)), key=lambda k: abs(values[k] - length))].append(length)
        for k, value in enumerate(values):
            got = taken[k]
            rows.append(BondRow(f'{a}–{b}', value, sum(got) / len(got) if got else None, len(got)))
    return rows


@dataclass(frozen=True)
class Comparison:
    entry: dict
    vibrations: Vibrations | None
    bonds: tuple = ()
    harmonic: Vibrations | None = None  # against the harmonic frequencies of experiment (CCCBDB has some)
    dipole: tuple | None = None  # (computed | None, measured) D
    notes: tuple = field(default_factory=tuple)


def compare(entry, output):
    """What the result output (modules/spectrum/readers/results.Output) has to compare with the entry."""
    geometry = getattr(output, 'geometry', None) or getattr(output, 'vibration_geometry', None)
    frequencies = [w for _, w in getattr(output, 'frequencies', ()) or ()]
    vib = vibrations(entry, frequencies) if frequencies else None
    harmonic = vibrations(entry, frequencies, 'harmonic') if frequencies and entry.get('harmonic') else None
    if harmonic is not None and not harmonic.pairs:
        harmonic = None  # not all the harmonic frequencies are on the page
    props = getattr(output, 'properties', None)
    computed_dipole = getattr(props, 'dipole_debye', None) if props is not None else None
    measured = entry.get('dipole_debye')
    notes = []
    if entry.get('note'):
        notes.append(entry['note'])
    return Comparison(entry, vib, tuple(bonds(entry, geometry)) if geometry is not None else (), harmonic,
                      None if measured is None else (computed_dipole, measured), tuple(notes))

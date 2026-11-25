"""Descriptors of the calculations of a queue against the constants of its structures — logK and the like.

HEADER The user's database of ligands (Cs_full.sdf, Sr.sdf: 2D records with «logK_Cs_z=1.0_T=25_I=0.1» … as data items)
    goes into a queue; after it the energies, the geometry around the metal, the charges and the QTAIM numbers of every
    calculation are put next to the constants of its record, and one descriptor is fitted against one constant. Before,
    that table was assembled by hand. Wilkinson convention, sections 1-8.

§1 THEORY
    A linear free-energy relation: logK = a + b·x for a descriptor x of the complexes of a series (the binding energy,
    the charge carried to the metal, Σρ or ΣV at the bond critical points M–D). The fit is ordinary least squares;
    R² = 1 − SS_res/SS_tot; RMSE = √(SS_res/n); the leave-one-out Q² = 1 − PRESS/SS_tot, PRESS = Σ (y_i − ŷ_(−i))²
    computed with the hat values h_ii (y_i − ŷ_(−i) = e_i / (1 − h_ii)); a point with |e_i| > 2·RMSE is an outlier.
    The coordination sphere: donors D ∈ DONORS with d(M–D) ≤ r_cov(M) + r_cov(D) + SHELL (Cordero 2008 radii; SHELL =
    0.5 Å takes Cs–O up to 3.6 Å, Sr–O up to 3.1 Å — the first sphere of both, not the second).

§2 ALGORITHM
    metal_index(molecule): the heaviest atom of METALS (None without one). sphere(molecule, i): the donors around it.
    of_item(item, qtaim): the descriptors of one calculation — E, G (hartree), ΔHf (MOPAC), the atoms; with a metal:
    CN, the shortest and mean M–D, the mean M–O and M–N, its Mulliken / Löwdin / Hirshfeld charge and z − q (the charge
    carried to it) from the output (orca_properties), and from the BCP table of «QTAIM для всех» (<stem>_qtaim_bcp.json,
    written by batch_qtaim) the number of M–D bond points, Σρ, Σ∇²ρ, ΣV, ΣH over them. table(queue, extra=None): one
    row per calculation done — the name, the descriptors, then every data item of its record (props); extra — rows of
    another table by name (the binding energies of 0.102.0) merged in. numbers(column) — the values as floats (the
    decimal comma of a Russian table too), None where empty. fit(x, y).

§3 APPLICATIONS
    modules/sextant/descriptor_view.py — «Дескрипторы и logK…» of the window of a finished queue and «Расчёт →
    Дескрипторы и logK очереди…».

§4 SPECIFICATION METALS, DONORS, SHELL; metal_index(molecule) -> int | None; sphere(molecule, i) -> [(j, symbol,
    distance)]; of_item(item, qtaim=None, text=None) -> {column: value}; table(queue, extra=None) -> (columns, rows:
    [[…]]); number(value) -> float | None; constant_columns(columns, rows) -> the columns of the records whose values
    are numbers; fit(x, y) -> Fit (n, slope, intercept, r, r2, rmse, q2, predicted, residuals, outliers) — ValueError
    with fewer than three pairs or one x for all.

§6 NOTES
    ASSUMPTION: the metal of a complex is its heaviest metal atom (a complex of one metal ion). The constants are taken
    as written in the record; their units and conditions (T, I) are the names of the items. The QTAIM columns are
    empty until «QTAIM для всех» has run for the queue.

§7 TEST CASES (tests/sextant/test_descriptors.py)
    An exact line gives R² = 1, Q² = 1, RMSE = 0; a known noisy set gives the R² of numpy.polyfit; the sphere of Cs⁺ in
    a model crown (6 O at 3.0 Å, C farther) is CN 6; a table of two items keeps the logK of their records.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path

from azimuth.i18n import tr

METALS = frozenset(
    'Li Na K Rb Cs Fr Be Mg Ca Sr Ba Ra Al Ga In Tl Sn Pb Bi Sc Ti V Cr Mn Fe Co Ni Cu Zn Y Zr Nb Mo Tc Ru Rh Pd Ag Cd '
    'La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu Hf Ta W Re Os Ir Pt Au Hg Ac Th Pa U Np Pu Am Cm'.split())
DONORS = frozenset({'O', 'N', 'S', 'P', 'F', 'Cl', 'Br', 'I', 'Se'})
SHELL = 0.5  # Å above the sum of the covalent radii
# Cordero et al., Dalton Trans. 2008, 2832 (contacts.COVALENT has the lighter ones; these are the heavy metals asked)
EXTRA_RADII = {'Rb': 2.20, 'Cs': 2.44, 'Sr': 1.95, 'Ba': 2.15, 'Y': 1.90, 'La': 2.07, 'Ce': 2.04, 'Nd': 2.01,
               'Eu': 1.98, 'Gd': 1.96, 'Lu': 1.87, 'Th': 2.06, 'U': 1.96, 'Pu': 1.87, 'Am': 1.80, 'Fr': 2.60, 'Ra': 2.21,
               'Sc': 1.70, 'Ti': 1.60, 'V': 1.53, 'Cr': 1.39, 'Mn': 1.39, 'Zr': 1.75, 'Mo': 1.54, 'Hf': 1.75}
OUTLIER = 2.0  # × RMSE


def radius(symbol):
    from modules.spectrum.analysis.contacts import COVALENT

    return COVALENT.get(symbol, EXTRA_RADII.get(symbol, 1.5))


def metal_index(molecule):
    from modules.spectrum.analysis.thermo import MASSES

    found = [k for k, a in enumerate(molecule.atoms) if a.symbol in METALS]
    return max(found, key=lambda k: MASSES.get(molecule.atoms[k].symbol, 0.0)) if found else None


def sphere(molecule, i):
    centre = molecule.atoms[i]
    out = []
    for j, a in enumerate(molecule.atoms):
        if j == i or a.symbol not in DONORS:
            continue
        d = math.dist(a.position, centre.position)
        if d <= radius(centre.symbol) + radius(a.symbol) + SHELL:
            out.append((j, a.symbol, d))
    return sorted(out, key=lambda row: row[2])


def number(value):
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return None if isinstance(value, bool) or not math.isfinite(value) else float(value)
    text = str(value).strip().replace('−', '-').replace(',', '.')
    try:
        found = float(text)
    except ValueError:
        return None
    return found if math.isfinite(found) else None


def bcp_file(item):
    """The BCP list «QTAIM для всех» wrote next to the orbitals of the item (batch_qtaim.write_bcp_json)."""
    from modules.spectrum.wavefunction import batch_qtaim, field_tables

    path = batch_qtaim.wavefunction_of(item)
    if path is None:
        return None
    candidate = path.parent / field_tables.ANALYSIS / (path.name.split('.')[0] + '_qtaim_bcp.json')
    return candidate if candidate.is_file() else None


def read_bcp(item):
    path = bcp_file(item)
    if path is None:
        return None
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return None


def _output_text(item):
    try:
        return Path(item.output).read_text(encoding='utf-8', errors='replace') if item.output else ''
    except OSError:
        return ''


def of_item(item, qtaim=None, text=None):
    """The descriptors of one calculation done ({column: float | str})."""
    out = {tr('E, Eh'): item.energy, tr('G, Eh'): item.gibbs, tr('ΔHf, ккал/моль'): item.heat}
    molecule = item.geometry or item.molecule
    if molecule is None or not molecule.atoms:
        return out
    out[tr('Атомов')] = len(molecule.atoms)
    i = metal_index(molecule)
    if i is None:
        return out
    metal = molecule.atoms[i].symbol
    shell = sphere(molecule, i)
    out[tr('Металл')] = metal
    out['CN'] = len(shell)
    if shell:
        out[tr('r(M–D) мин., Å')] = shell[0][2]
        out[tr('r(M–D) ср., Å')] = sum(d for *_, d in shell) / len(shell)
        for symbol in ('O', 'N'):
            ds = [d for _, s, d in shell if s == symbol]
            if ds:
                out[tr(f'r(M–{symbol}) ср., Å')] = sum(ds) / len(ds)
    text = _output_text(item) if text is None else text
    if text:
        try:
            from modules.spectrum.readers.orca_properties import read_properties

            props = read_properties(text)
        except Exception:  # noqa: BLE001 — another program, or no population analysis: no charges
            props = None
        if props is not None and props.geometry is not None and len(props.geometry.atoms) == len(molecule.atoms):
            for key, name in (('mulliken', 'q(M) Малликен'), ('loewdin', 'q(M) Лёвдин'), ('hirshfeld', 'q(M) Хиршфельд')):
                charges = props.charges.get(key)
                if charges and len(charges) > i:
                    out[tr(name)] = charges[i]
                    if key == 'loewdin' or (key == 'mulliken' and tr('z − q(M)') not in out):  # Löwdin first
                        out[tr('z − q(M)')] = _formal_ion_charge(metal) - charges[i]
    qtaim = read_bcp(item) if qtaim is None else qtaim
    if qtaim:
        rows = [p for p in qtaim.get('bcp', ()) if i in p.get('atoms', ()) and
                any(molecule.atoms[k].symbol in DONORS for k in p['atoms'] if k != i and k < len(molecule.atoms))]
        out[tr('BCP M–D')] = len(rows)
        if rows:
            out['Σρ(M–D)'] = sum(p['rho'] for p in rows)
            out['Σ∇²ρ(M–D)'] = sum(p['laplacian'] for p in rows)
            out['ΣV(M–D)'] = sum(p['V'] for p in rows)
            out['ΣH(M–D)'] = sum(p['H'] for p in rows)
    return out


def _formal_ion_charge(symbol):
    """The charge of the free ion the metal comes from: 1 for the alkali metals, 2 for the alkaline earths, else 0
    (z − q(M) is then −q)."""
    if symbol in ('Li', 'Na', 'K', 'Rb', 'Cs', 'Fr', 'Ag', 'Tl'):
        return 1
    if symbol in ('Be', 'Mg', 'Ca', 'Sr', 'Ba', 'Ra', 'Zn', 'Cd', 'Hg', 'Pb', 'Sn'):
        return 2
    return 0


def table(queue, extra=None):
    """(columns, rows) — one row per calculation done of the queue; extra: {name: {column: value}} merged in by the
    name (the binding energies of a binding queue); rows of a binding queue are its complexes."""
    columns = [tr('Структура')]
    rows = []
    roles = any(item.props.get('role') for item in queue.items)
    for item in queue.items:
        if item.state != 'done':
            continue
        if roles and item.props.get('role') not in ('complex', None):
            continue
        values = {tr('Структура'): item.name, **of_item(item)}
        key = item.props.get('ligand_name', item.name)
        if extra and key in extra:
            values.update(extra[key])
        values.update({k: v for k, v in item.props.items() if not k.startswith('_') and k not in ROLE_KEYS})
        for column in values:
            if column not in columns:
                columns.append(column)
        rows.append(values)
    return columns, [['' if row.get(c) is None else row.get(c) for c in columns] for row in rows]


ROLE_KEYS = ('role', 'ligand', 'ligand_name', 'task', 'ghosts', 'of', 'complex_of', 'conformer')


def constant_columns(columns, rows, start=1):
    """The columns whose values are numbers in at least three rows (the constants and the descriptors)."""
    out = []
    for k, column in enumerate(columns[start:], start):
        if sum(number(row[k]) is not None for row in rows) >= 3:
            out.append(column)
    return out


@dataclass
class Fit:
    n: int
    slope: float
    intercept: float
    r: float
    r2: float
    rmse: float
    q2: float | None
    predicted: list
    residuals: list
    outliers: list  # indices into the pairs


def fit(x, y):
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3:
        raise ValueError(tr('Для прямой нужно хотя бы три пары значений.'))
    xs, ys = [a for a, _ in pairs], [b for _, b in pairs]
    mx, my = sum(xs) / n, sum(ys) / n
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 1e-300:
        raise ValueError(tr('У всех точек одно значение дескриптора — прямую не провести.'))
    sxy = sum((a - mx) * (b - my) for a, b in pairs)
    slope = sxy / sxx
    intercept = my - slope * mx
    predicted = [intercept + slope * a for a in xs]
    residuals = [b - p for b, p in zip(ys, predicted)]
    ss_res = sum(e * e for e in residuals)
    r2 = 1.0 - ss_res / syy if syy > 1e-300 else 1.0
    r = sxy / math.sqrt(sxx * syy) if syy > 1e-300 else 1.0
    rmse = math.sqrt(ss_res / n)
    press = sum((e / (1.0 - (1.0 / n + (a - mx) ** 2 / sxx))) ** 2 for a, e in zip(xs, residuals))
    q2 = 1.0 - press / syy if syy > 1e-300 else None
    outliers = [k for k, e in enumerate(residuals) if rmse > 1e-12 and abs(e) > OUTLIER * rmse]
    return Fit(n, slope, intercept, r, r2, rmse, q2, predicted, residuals, outliers)

"""The results of the calculations of a project of a crystal, read from their folders — for «Компас · Кристалл» (the
charges on the atoms of the model), for Spectrum (the plots of an optimization, the bands, the density of states, the
tables of Multiwfn) and for the panel of the calculation.

§1 PURPOSE
    The results of a crystal as for a molecule: the charges as labels on the model, Spectrum with the plots of the
    optimization, the bands and the DOS, the charges and
    the bonds. A run of a crystal is a folder (crystal_projects.record_run: folder, program, task); what it gave is
    read from its files whenever it is shown, and what Multiwfn computed is kept beside them (charges.csv,
    aim-bonds.csv) so it is shown again without computing anew.
§2 ALGORITHM
    runs(manifest) — the runs recorded whose folder is there, in the order made. result(run) — cp2k.read / qe.read (the
    scf of the steps). steps(run) — the raw steps (cp2k.steps / qe.steps): energy, cell, atoms. steps_table — a row per
    step: energy (hartree), a, b, c (Å), the volume (Å³). bands(run), dos(run) — what the panel of Quantum ESPRESSO
    plots (path.json of the run and pw.out; azimuth.dos), E0 the top of the valence band or the Fermi level.
    multiwfn_file(run) — the file for Multiwfn of a CP2K run (cp2k.for_multiwfn). The charges of a supercell on the
    model (model_charges): the atoms of the file for Multiwfn as fractions of its cell times the supercell (the edges
    over those of the cell of the file) modulo 1, the atoms of the model as fractions of the cell of the file modulo 1;
    an atom of the model takes the mean charge of the atoms of its element nearer than MATCH (Å, by the metric of the
    cell of the file) — the atoms equal by translation have one charge; an atom with none stays without a label.
§4 SPECIFICATION
    Run(folder, program, task, time); runs(manifest) -> [Run]; last(manifest, program=None, having=None) -> Run | None;
    result(run); steps(run) -> raw; steps_table(raw) -> [dict]; bands(run) -> (Bands, path, E0) | None; dos(run) ->
    (Dos, E0) | None; multiwfn_file(run) -> Path | None; write_charges / read_charges, write_aim / read_aim (the CSV of
    the folder); model_charges(molden_text, charges, file_cell, points) -> [value | None per point].
§7 TESTS
    tests/compass/test_crystal_results.py — the real CELL_OPT of CsCl (CP2K 2026.2) and its charges (Multiwfn).
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

CHARGES_CSV, AIM_CSV = 'charges.csv', 'aim-bonds.csv'
AIM_HEADER = ['bond', 'length, A', 'bonds per atom', 'rho, au', 'laplacian, au', 'H, au', '|V|/G', 'nature']
MATCH = 0.6  # Å: an atom of the model and its atom of the supercell (the optimized cell moves the atoms a little)


@dataclass(frozen=True)
class Run:
    folder: Path
    program: str  # 'cp2k' | 'qe'
    task: str = ''
    time: str = ''

    @property
    def output(self):
        return self.folder / ('cp2k.out' if self.program == 'cp2k' else 'pw.out')

    @property
    def title(self):
        return ('CP2K' if self.program == 'cp2k' else 'Quantum ESPRESSO') + (' · ' + self.task if self.task else '')


def runs(manifest):
    from azimuth import crystal_projects

    manifest = Path(manifest)
    found = []
    for run in crystal_projects.info(manifest).get('runs') or []:
        folder = manifest.parent / str(run.get('folder', ''))
        if folder.is_dir() and run.get('folder'):
            found.append(Run(folder, 'cp2k' if run.get('program') == 'cp2k' else 'qe', str(run.get('task') or ''),
                             str(run.get('time') or '')))
    return found


def last(manifest, program=None, having=None):
    """The last run (of the program; with a file having in its folder)."""
    for run in reversed(runs(manifest)):
        if (program is None or run.program == program) and (having is None or any(run.folder.glob(having))):
            return run
    return None


def _text(path):
    return Path(path).read_text(encoding='utf-8', errors='replace') if Path(path).is_file() else ''


def result(run):
    from modules.spectrum.readers import cp2k, qe

    text = _text(run.output)
    if not text:
        return None
    if run.program == 'cp2k':
        return cp2k.read(text, run.folder)
    return qe.read((qe.runs(text) or [text])[0])


def steps(run):
    from modules.spectrum.readers import cp2k, qe

    if run.program == 'cp2k':
        return cp2k.steps(run.folder)
    text = _text(run.output)
    return qe.steps((qe.runs(text) or [text])[0]) if text else []


def steps_table(raw):
    import numpy as np

    rows = []
    for k, (energy, cell, _atoms) in enumerate(raw):
        m = np.array(cell, dtype=float)
        rows.append({'step': k, 'energy': energy, 'a': float(np.linalg.norm(m[0])), 'b': float(np.linalg.norm(m[1])),
                     'c': float(np.linalg.norm(m[2])), 'volume': float(abs(np.linalg.det(m)))})
    return rows


def _reference(r):
    return r.highest if r.highest is not None else r.fermi


def bands(run):
    from modules.spectrum.readers import qe

    if run.program != 'qe' or not (run.folder / 'path.json').is_file():
        return None
    r = result(run)
    if r is None:
        return None
    found = qe.bands(_text(run.output))
    path = json.loads((run.folder / 'path.json').read_text(encoding='utf-8'))
    if not found.energies or len(found.energies) != len(path['x']):
        return None
    return found, path, _reference(r)


def dos(run):
    from modules.spectrum.readers import qe

    if run.program != 'qe' or not (run.folder / 'azimuth.dos').is_file():
        return None
    r = result(run)
    found = qe.read_dos(_text(run.folder / 'azimuth.dos'))
    e0 = _reference(r) if r is not None else None
    if e0 is None:
        e0 = found.fermi
    return (found, e0) if found.energies else None


def pdos(run, compute=False, progress=None, fwhm=0.3):
    """The DOS and the PDOS of a run (crystal_pdos.Curves, energies from E₀) or None: Quantum ESPRESSO — the
    files of projwfc.x; CP2K — its .pdos files, else the shares of its Molden file (kept in pdos-levels.csv; worked out
    with compute). CP2K: per formula unit of its cell."""
    from math import gcd

    from modules.compass.chemistry import crystal_pdos

    if run.program == 'qe':
        found = crystal_pdos.qe_curves(run.folder)
        if found is None:
            return None
        r = result(run)
        e0 = _reference(r) if r is not None else None
        if e0 is None and (run.folder / 'azimuth.dos').is_file():
            from modules.spectrum.readers import qe

            e0 = qe.read_dos(_text(run.folder / 'azimuth.dos')).fermi
        found.x = found.x - (e0 or 0.0)
        found.e0 = e0 or 0.0
        return found
    from modules.spectrum.readers import cp2k

    levels = crystal_pdos.cp2k_levels(run.folder, compute, progress)
    if levels is None:
        return None
    units = 1
    cell = cp2k.last_cell(run.folder)
    if cell is not None and (run.folder / 'azimuth.inp').is_file():
        counts = {}
        for symbol, _ in cp2k._input_atoms(run.folder / 'azimuth.inp', cell):
            counts[symbol] = counts.get(symbol, 0) + 1
        g = 0
        for n in counts.values():
            g = gcd(g, n)
        units = max(1, g)
    found = crystal_pdos.curves(levels, fwhm, units)
    found.extra['units'] = units
    if not levels.complete:
        found.note = ('В файле Molden только занятые орбитали (расчёт с OT): PDOS кончается на вершине валентной зоны. '
                      'Новые расчёты CP2K печатают PDOS и с пустыми уровнями.')
    return found


def multiwfn_file(run):
    from modules.spectrum.readers import cp2k

    if run is None or run.program != 'cp2k':
        return None
    path, _why = cp2k.for_multiwfn(run.folder)
    return path


# -- what Multiwfn computed, kept beside the run ------------------------------------------------------------------------
def write_charges(folder, atoms, charges):
    with open(Path(folder) / CHARGES_CSV, 'w', newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(['atom', 'element', 'Hirshfeld', 'CM5'])
        for k, (symbol, _) in enumerate(atoms):
            writer.writerow([k + 1, symbol, f"{charges['hirshfeld'][k]:.6f}", f"{charges['cm5'][k]:.6f}"])


def read_charges(folder):
    """(symbols, {'hirshfeld': (…), 'cm5': (…)}) of charges.csv, or None."""
    path = Path(folder) / CHARGES_CSV
    if not path.is_file():
        return None
    try:
        rows = list(csv.DictReader(path.read_text(encoding='utf-8').splitlines()))
        return (tuple(r['element'] for r in rows), {'hirshfeld': tuple(float(r['Hirshfeld']) for r in rows),
                                                   'cm5': tuple(float(r['CM5']) for r in rows)})
    except (KeyError, ValueError):
        return None


AIM_META = 'aim-bonds.json'  # the count of the points (Poincaré–Hopf), the atoms, the version of Multiwfn
AIM_POINTS = 'aim-points.json'  # the critical points of the cell computed (Å) and its cell


def write_aim_points(folder, points, cell_bohr):
    data = {'cell': [[float(x) * 0.529177210903 for x in row] for row in cell_bohr], 'points': points}
    (Path(folder) / AIM_POINTS).write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')


def read_aim_points(folder):
    """(the cell of the run Å, [(kind, (x, y, z) Å, elements)]) or None."""
    path = Path(folder) / AIM_POINTS
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding='utf-8'))
        return data['cell'], [(p['kind'], tuple(p['xyz']), tuple(p.get('elements') or ())) for p in data['points']]
    except (OSError, ValueError, KeyError, TypeError):
        return None


def write_aim(folder, rows, meta=None):
    with open(Path(folder) / AIM_CSV, 'w', newline='', encoding='utf-8') as out:
        writer = csv.writer(out)
        writer.writerow(AIM_HEADER)
        writer.writerows(rows)
    if meta is not None:
        (Path(folder) / AIM_META).write_text(json.dumps(meta, ensure_ascii=False), encoding='utf-8')


def read_aim(folder):
    """(rows of aim-bonds.csv — crystal_aim.table_rows, meta {census, atoms, version}) or None."""
    path = Path(folder) / AIM_CSV
    if not path.is_file():
        return None
    rows = [tuple(r) for r in list(csv.reader(path.read_text(encoding='utf-8').splitlines()))[1:]
            if len(r) == len(AIM_HEADER)]
    try:
        meta = json.loads((Path(folder) / AIM_META).read_text(encoding='utf-8'))
    except (OSError, ValueError):
        meta = {}
    return (rows, meta) if rows else None


# -- the charges of a supercell on the atoms of the model ---------------------------------------------------------------
def model_charges(molden_text, values, file_cell, points):
    """The values of the atoms of the file for Multiwfn (one per atom, in its order) on the atoms of the model:
    points — [(symbol, (x, y, z) in Å)]; file_cell — the 3 vectors of the cell of the file (Å). None where no atom of
    the supercell is near."""
    import numpy as np

    from modules.spectrum.wavefunction import crystal_aim

    cell, atoms = crystal_aim.geometry(molden_text)
    cell = np.asarray(cell) * crystal_aim.BOHR
    small = np.asarray(file_cell, dtype=float)
    repeat = np.maximum(1, np.round(np.linalg.norm(cell, axis=1) / np.linalg.norm(small, axis=1)))
    inverse = np.linalg.inv(cell)
    super_fractions = np.array([(np.asarray(p) * crystal_aim.BOHR) @ inverse for _, p in atoms]) * repeat % 1.0
    model_inverse = np.linalg.inv(small)
    shown = []
    for symbol, position in points:
        f = (np.asarray(position, dtype=float) @ model_inverse) % 1.0
        d = super_fractions - f
        d -= np.round(d)
        lengths = np.linalg.norm(d @ small, axis=1)
        near = [values[k] for k in range(len(atoms)) if atoms[k][0] == symbol and lengths[k] < MATCH]
        shown.append(float(np.mean(near)) if near else None)
    return shown

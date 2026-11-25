"""A project made of calculations done outside Azimuth.

§1 PURPOSE
    Calculations done outside Azimuth (usually a folder per calculation) become a full project: the optimization
    results, the wave function and further analysis. The files of a calculation are found by a common name.
§2 ALGORITHM
    1. find(paths): every output of ORCA or Gaussian (.out, .log) in the folders chosen and below (depth ≤ 4; the
       folders of Azimuth projects skipped). The files of one calculation are those of its folder whose names begin
       with the name of its output and a dot or «_» (mol.inp, mol.gbw, mol.hess, mol_trj.xyz, mol.densities …); a
       file that begins with the longer name of another output of the folder is that one's (mol_freq.out takes
       mol_freq.*). Temporary files (*.tmp*) are left. An output that is a copy of another one (the same bytes) is
       taken once. The SCF of a free atom ORCA writes for its guess («mol_atom38.out» beside «mol.out») is a file of
       mol, not a calculation.
    2. read(output): the program (outputs.program), the input echoed in the output (ORCA: the lines «| n> …»; Gaussian:
       the route «#»), the settings Sextant knows (inputs.read_settings: method, basis, task, dispersion, solvent), the
       charge and the multiplicity (the «* xyz q m» of the input, else what the output says), the starting geometry
       (the input echoed, else the first geometry of the output) and the final one, the energy. The keywords as written
       («! PBE0 D3BJ def2-TZVP Opt Freq») stay as the method of the record — the history shows what was run, not the
       nearest of the lists of Sextant.
    3. groups: the calculations of one molecule, in the order of their outputs' times — the start of one is the start
       or the end of another (within 0.001 Å: an optimization, then the frequencies from its geometry, then TD-DFT …);
       or the same molecule computed otherwise (same_molecule) — the same formula, the same graph of bonds (by distance,
       the elements of the neighbours refined
       three times, as Weisfeiler–Lehman), and nearly the same shape: the final geometries (else the starting ones)
       within RMSD 0.25 Å after the best rotation when the atoms are in the same order, else their sorted distances
       within 0.03 Å on average and 0.3 Å at most; compared with the first calculation of the group. Conformers (another
       shape of the same graph) stay molecules of their own.
    4. build(root, name, found): a new project (projects.Project.create in a new folder of the projects of
       molecules); for each group a molecule (the name of its first output, its start geometry, its settings); for
       each calculation its files copied into calculations/import-<name>-<6 hex>/ (the originals untouched) and a record
       done (Project.record: the energy, the final geometry, «usable»); the last one with a result is the current one —
       Spectrum, the orbitals (the .gbw beside the output) and Multiwfn work on it.
§3 INTERFACE
    find(paths) -> [Found(output, files, program)]; read(found) -> Read | None; groups(reads) -> [[Read]];
    build(root, name, paths) -> (manifest, report [(output, outcome)]).
§7 TESTS
    tests/projects/test_project_import.py."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from pathlib import Path
import re
import shutil
from uuid import uuid4

from azimuth.i18n import tr

OUTPUTS = ('.out', '.log', '.dat', '.nwout', '.qcout', '.gamout')  # .dat: Psi4 (output.dat); a punch file of GAMESS is
# no output every program Spectrum reads
KINDS = {'ORCA': 'orca', 'Gaussian': 'gaussian', 'Psi4': 'psi4', 'xtb': 'xtb', 'MOPAC': 'mopac', 'GAMESS': 'gamess',
         'NWChem': 'nwchem', 'Q-Chem': 'qchem'}
# the files of xtb have fixed names, whatever the name of its output (it writes into the folder it runs in)
XTB_FILES = ('xtbopt.xyz', 'xtbopt.log', 'xtbopt.coord', 'xtbopt.sdf', 'xtbopt.pdb', 'charges', 'wbo', 'xtbrestart',
             'gradient', 'hessian', 'vibspectrum', 'g98.out', 'xtbtopo.mol', '.xtboptok', 'xtbout.json', 'xtbhess.xyz',
             'molden.input', 'xtbscreen.xyz', 'energy', 'coord', 'xtblast.xyz', 'xtbmdok', 'xtb.trj')
# the files of the orbitals Spectrum looks for beside an output (SpectrumWorkspace.find_molden: <stem>.molden.input,
# .molden, .molf, .fchk; the .gbw of ORCA; the .aux of MOPAC); a checkpoint of Gaussian is kept too (formchk makes the .fchk)
ORBITALS = ('.molden.input', '.molden', '.molf', '.fchk', '.fch', '.gbw', '.chk', '.movecs', '.aux')
DEPTH = 4
CLOSE = 1e-3  # Å


@dataclass
class Found:
    output: Path
    files: list = field(default_factory=list)
    program: str = ''
    renamed: dict = field(default_factory=dict)  # {a name given in the copy: the file} — the orbitals under the name
    note: str = ''                               # of the output, where Spectrum looks for them


@dataclass
class Read:
    found: Found
    kind: str
    name: str
    start: object
    final: object
    calc: object
    keywords: str
    energy: float | None
    time: float = 0.0


def _program(path):
    from modules.spectrum.readers.outputs import program

    try:
        with open(path, encoding='utf-8', errors='replace') as handle:
            head = handle.read(200000)
    except OSError:
        return ''
    found = program(head)
    # outputs.program says «ORCA» for any text it does not know (a punch file, a log of anything) — ORCA by its banner
    if found == 'ORCA' and not re.search(r'O\s+R\s+C\s+A|ORCA TERMINATED|Program Version \d', head):
        return ''
    if path.suffix.lower() == '.dat' and found != 'Psi4':
        return ''
    return found if found in KINDS else ''


def _outputs(paths):
    seen, out = set(), []

    def walk(folder, depth):
        if depth > DEPTH or (folder / 'project.qcc').exists():
            return
        try:
            entries = sorted(folder.iterdir())
        except OSError:
            return
        for entry in entries:
            if entry.is_dir():
                walk(entry, depth + 1)
            elif entry.suffix.lower() in OUTPUTS and entry.resolve() not in seen:
                seen.add(entry.resolve())
                out.append(entry)

    for path in paths:
        path = Path(path)
        if path.is_dir():
            walk(path, 0)
        elif path.is_file() and path.resolve() not in seen:
            seen.add(path.resolve())
            out.append(path)
    return out


def find(paths):
    """The calculations in the files and folders chosen: each output of ORCA or Gaussian with the files of its name."""
    found = []
    outputs = [(p, _program(p)) for p in _outputs(paths)]
    outputs = [(p, k) for p, k in outputs if k]
    by_folder = {}
    # ORCA writes the SCF of a free atom of the guess beside its
    # output — «<name>_atom38.out» (the atomic number): a file of that calculation, not a calculation of its own
    stems = {(p.parent, p.stem) for p, _ in outputs}
    outputs = [(p, k) for p, k in outputs
               if not (k == 'ORCA' and re.search(r'_atom\d+$', p.stem)
                       and (p.parent, re.sub(r'_atom\d+$', '', p.stem)) in stems)]
    for path, kind in outputs:
        by_folder.setdefault(path.parent, []).append((path, kind))
    for folder, items in by_folder.items():
        if any(k == 'xtb' for _, k in items):  # g98.out, xtbopt.log of xtb are its files, not outputs of their own
            items = [(p, k) for p, k in items if p.name not in XTB_FILES]
        stems = sorted({p.stem for p, _ in items}, key=len, reverse=True)
        try:
            names = [f for f in folder.iterdir() if f.is_file()]
        except OSError:
            names = []
        for path, kind in items:
            mine = []
            for f in names:
                if '.tmp' in f.name.lower():
                    continue
                owner = next((s for s in stems if f.name == s or f.name.startswith((s + '.', s + '_'))), None)
                if owner == path.stem:
                    mine.append(f)
            one = Found(path, sorted(mine), kind)
            _extras(one, names, alone=len(items) == 1)
            found.append(one)
    return found


def _extras(found, names, alone):
    """The files a program
    writes under other names than that of its output.
    xtb — its files of fixed names (XTB_FILES) and the coordinate file of its call («coordinate file : mol.xyz»).
    Gaussian — the checkpoint of «%chk=name.chk» and its formatted twin (name.fchk, name.fch).
    NWChem — the files of its prefix («prefix = dvb.»: dvb.movecs, dvb.db, dvb.hess …).
    Psi4, Q-Chem, GAMESS, any program alone in its folder — the files of orbitals there (ORBITALS).
    A file of orbitals of another name (the checkpoint of Gaussian, the Molden of Psi4) is copied also under the name
    of the output — <output>.fchk, <output>.molden — where Spectrum finds it; a .chk alone is said: formchk makes its
    .fchk."""
    path, program = found.output, found.program
    by_name = {f.name: f for f in names}
    taken = {f.name for f in found.files}

    def take(f):
        if f is not None and f.name not in taken and '.tmp' not in f.name.lower():
            found.files.append(f)
            taken.add(f.name)

    try:
        head = path.read_text(encoding='utf-8', errors='replace')[:400000]
    except OSError:
        head = ''
    if program == 'xtb':
        for name in XTB_FILES:
            take(by_name.get(name))
        call = re.search(r'coordinate file\s*:\s*(\S+)', head)
        if call:
            take(by_name.get(Path(call.group(1)).name))
    elif program == 'Gaussian':
        chk = re.search(r'^\s*%chk\s*=\s*(\S+)', head, re.M | re.I)
        if chk:
            stem = Path(chk.group(1).replace('\\', '/')).stem
            for ext in ('.chk', '.fchk', '.fch', '.Fchk', '.FChk'):
                take(by_name.get(stem + ext))
    elif program == 'NWChem':
        prefix = re.search(r'^\s*prefix\s*=\s*(\S+?)\.?\s*$', head, re.M)
        if prefix:
            for f in names:
                if f.name.startswith(prefix.group(1) + '.'):
                    take(f)
    if alone or program in ('Psi4', 'Q-Chem', 'GAMESS'):
        for f in names:
            if f.name.lower().endswith(ORBITALS) and (alone or f.stem == path.stem):
                take(f)
    found.files.sort()
    # the orbitals under the name of the output (Spectrum looks for <stem>.molden.input, .molden, .molf, .fchk)
    own = {f.name for f in found.files}
    if not any(path.stem + ext in own for ext in ('.molden.input', '.molden', '.molf', '.fchk')):
        for ext, as_ in (('.fchk', '.fchk'), ('.fch', '.fchk'), ('.molden.input', '.molden.input'),
                         ('.molden', '.molden'), ('.molf', '.molf')):
            others = [f for f in found.files if f.name.lower().endswith(ext) and f.name != path.stem + as_]
            if len(others) == 1:
                found.renamed[path.stem + as_] = others[0]
                break
    if not found.renamed and not any(path.stem + e in own for e in ('.fchk', '.molden', '.molden.input')) and \
            any(f.suffix.lower() == '.chk' for f in found.files):
        found.note = tr('орбитали только в .chk — сделайте formchk, чтобы получить .fchk')


def _echo(text, kind):
    if kind == 'ORCA':
        return '\n'.join(m.group(1) for m in re.finditer(r'^\|\s*\d+>\s?(.*)$', text, re.M))
    if kind != 'Gaussian':  # the others — no echo read here (their level: _keywords from the output)
        return ''
    lines = text.splitlines()
    start = next((k for k, l in enumerate(lines) if l.strip().startswith('#')), None)
    if start is None:
        return ''
    route = []
    for line in lines[start:start + 12]:
        if line.strip().startswith('---'):
            break
        route.append(line.strip())
    return ' '.join(route)


def _state(text, echo, kind):
    found = re.search(r'^\s*\*\s*(?:xyz|xyzfile|gzmt|int|internal|gzmtfile)\s+([+-]?\d+)\s+(\d+)', echo, re.M | re.I)
    if found:
        return int(found.group(1)), int(found.group(2))
    if kind == 'ORCA':
        charge = re.search(r'Total Charge\s+Charge\s+\.+\s+([+-]?\d+)', text)
        mult = re.search(r'Multiplicity\s+Mult\s+\.+\s+(\d+)', text)
    else:
        both = re.search(r'Charge\s*=\s*([+-]?\d+)\s+Multiplicity\s*=\s*(\d+)', text)
        charge, mult = (both, both) if both else (None, None)
        if both:
            return int(both.group(1)), int(both.group(2))
    return (int(charge.group(1)) if charge else 0), (int(mult.group(1)) if mult else 1)


def _keywords(echo, kind):
    if kind == 'ORCA':
        return ' '.join(l.strip()[1:].strip() for l in echo.splitlines() if l.strip().startswith('!'))
    return echo.lstrip('#').strip()


def read(found):
    """What the output says of its calculation; None when it has no geometry."""
    from azimuth.core import Calculation
    from modules.sextant import inputs
    from modules.spectrum.readers.outputs import read_any

    try:
        text = found.output.read_text(encoding='utf-8', errors='replace')
        output = read_any(text, found.output)
    except Exception:  # noqa: BLE001 — an output not read is reported, not raised
        return None
    kind = KINDS[found.program]
    echo = _echo(text, found.program)
    final = output.geometry
    start = getattr(output, 'initial_geometry', None)
    if start is None and getattr(output, 'steps', ()):
        start = output.steps[0].geometry
    start = start or final
    if start is None:
        return None
    charge, multiplicity = _state(text, echo, found.program)
    settings = inputs.read_settings(kind, echo) if echo and found.program in ('ORCA', 'Gaussian') else {}
    calc = Calculation(charge=charge, multiplicity=multiplicity)
    for key in ('method', 'basis', 'task', 'dispersion', 'solvent', 'couplings'):
        if key in settings:
            try:
                trial = replace(calc, **{key: settings[key]})
                trial.validate_settings()
                calc = trial
            except (ValueError, TypeError):
                pass
    energy = None
    if getattr(output, 'final_energy', None):
        energy = output.final_energy[1]
    elif getattr(output, 'energies', None):
        energy = output.energies[-1]
    name = found.output.stem
    calc = replace(calc, title=name)
    try:
        time = found.output.stat().st_mtime
    except OSError:
        time = 0.0
    keywords = _keywords(echo, found.program)
    if not keywords:  # Psi4, xtb, MOPAC, GAMESS, NWChem, Q-Chem — the level as Spectrum reads it
        try:
            from modules.spectrum.analysis.reaction import level_of_theory

            keywords = level_of_theory(text, found.program)
        except Exception:  # noqa: BLE001 — a name only
            keywords = ''
        keywords = f'{found.program} · {keywords}' if keywords and keywords != 'XTB' else (
            'GFN2-xTB' if found.program == 'xtb' else found.program)
    return Read(found, kind, name, start, final, calc, keywords, energy, time)


def _close(a, b):
    from azimuth.projects import _same_geometry

    return _same_geometry(a, b, CLOSE)


RMSD_SAME = 0.25  # Å: one molecule optimized by two methods; conformers differ more
DISTANCES_SAME = (0.03, 0.3)  # Å: the mean and the largest difference of the sorted interatomic distances (the atoms
# in another order); a mean of 0.1 Å would take conformers for one molecule


def _graph(molecule):
    """The invariant of the graph of bonds: the labels of the atoms refined three times (Weisfeiler–Lehman)."""
    from dataclasses import replace as _replace

    from modules.compass.chemistry.builder import connections

    bonds = connections(_replace(molecule, bonds=None))
    near = [[] for _ in molecule.atoms]
    for i, j, *_ in bonds:
        near[i].append(j)
        near[j].append(i)
    labels = [a.symbol for a in molecule.atoms]
    for _ in range(3):
        labels = [labels[k] + '(' + ','.join(sorted(labels[n] for n in near[k])) + ')' for k in range(len(labels))]
        index = {label: str(n) for n, label in enumerate(sorted(set(labels)))}
        labels = [a.symbol + index[label] for a, label in zip(molecule.atoms, labels)]
    return tuple(sorted(labels)), len(bonds)


def same_molecule(a, b):
    """Two geometries of one molecule (computed by other methods or from other starts), not two conformers."""
    import numpy as np

    if a is None or b is None or a.formula != b.formula or len(a.atoms) != len(b.atoms):
        return False
    if _graph(a) != _graph(b):
        return False
    if [x.symbol for x in a.atoms] == [x.symbol for x in b.atoms]:
        from modules.spectrum.analysis.comparison import align

        try:
            return align(a, b)[1] <= RMSD_SAME
        except ValueError:
            return False

    def distances(m):
        p = np.array([x.position for x in m.atoms], dtype=float)
        d = np.linalg.norm(p[:, None, :] - p[None, :, :], axis=2)
        return np.sort(d[np.triu_indices(len(p), 1)])

    gap = np.abs(distances(a) - distances(b))
    return float(np.mean(gap)) <= DISTANCES_SAME[0] and float(np.max(gap)) <= DISTANCES_SAME[1]


def _shown(r):
    return r.final if r.final is not None else r.start


def groups(reads):
    """The calculations of one molecule together, each group in the order of the times of its outputs."""
    out = []
    for r in sorted(reads, key=lambda r: r.time):
        home = next((g for g in out if any(_close(r.start, x.start) or _close(r.start, x.final) for x in g)), None)
        if home is None:  # the same molecule computed otherwise — like the first of the group (not any
            # of it: a chain of «nearly the same» would join conformers into one molecule)
            home = next((g for g in out if same_molecule(_shown(r), _shown(g[0]))), None)
        if home is None:
            out.append([r])
        else:
            home.append(r)
    return out


def build(root, name, paths):
    """A new project of the calculations in paths. Returns (the path of project.qcc, [(output, outcome)])."""
    from azimuth import projects
    from azimuth.project_folders import new_project_folder

    found = find(paths)
    if not found:
        raise ValueError(tr('Не нашлось выходов ORCA или Gaussian (.out, .log) в выбранных файлах и папках.'))
    report, reads, seen = [], [], {}
    import hashlib

    for f in found:
        try:  # a copy of an output already taken — not twice
            digest = hashlib.sha1(f.output.read_bytes()).hexdigest()
        except OSError:
            digest = None
        if digest is not None and digest in seen:
            report.append((f.output, tr('не взят: копия {}').format(seen[digest])))
            continue
        if digest is not None:
            seen[digest] = f.output
        r = read(f)
        if r is None:
            report.append((f.output, tr('не прочитан: в выходе нет геометрии (расчёт прервался с ошибкой?)')))
        else:
            reads.append(r)
    if not reads:
        raise ValueError(tr('Ни один выход не прочитан: в них нет геометрии.'))
    folder = new_project_folder(Path(root), name)
    project = projects.Project.create(folder)
    project.data.update(name=name, named=True, draft=False)
    calculations = folder / 'calculations'
    calculations.mkdir(exist_ok=True)
    for group in groups(reads):
        first = group[0]
        entry = project.add(first.start, first.calc, first.kind, first.name)
        for r in group:
            safe = ''.join(ch if ch.isalnum() or ch in '-_' else '_' for ch in r.name)[:40] or 'calc'
            target = calculations / f'import-{safe}-{uuid4().hex[:6]}'
            target.mkdir(parents=True)
            for f in r.found.files:
                shutil.copy2(f, target / f.name)
            for name, f in r.found.renamed.items():  # the orbitals under the name of the output (Spectrum)
                if not (target / name).exists():
                    shutil.copy2(f, target / name)
            attempt = project.record(entry['id'], uuid4().hex, r.start, r.calc, r.kind, 'done', folder=target,
                                     output=target / r.found.output.name,
                                     note=tr('импортирован из {}').format(r.found.output.parent))
            if not attempt.get('usable') and r.final is not None and r.energy is not None:
                # xtb and MOPAC keep their geometry beside the output (xtbopt.xyz, .aux) — Project.record
                # reads the text alone; what the output and its files gave (read with its path) is the result
                from modules.sextant import batch

                attempt.update(usable=True, geometry=batch._molecule_dict(r.final), energy=r.energy)
                entry['current'] = projects.current_of(entry)
            if r.keywords:
                attempt['keywords'] = r.keywords
            attempt['imported'] = str(r.found.output)
            if attempt.get('usable') and isinstance(attempt.get('energy'), (int, float)):
                outcome = tr('готово, E = {} Eh').format(f'{attempt["energy"]:.6f}')
            elif attempt.get('usable') and isinstance(attempt.get('heat'), (int, float)):  # MOPAC: ΔHf
                outcome = tr('готово, ΔHf = {} ккал/моль').format(f'{attempt["heat"]:.3f}')
            else:
                outcome = tr('добавлен без результата')
            report.append((r.found.output, outcome + (' · ' + r.found.note if r.found.note else '')))
    project.save()
    return project.path, report

"""Flat (2D) structures of a file and their 3D coordinates by RDKit.

HEADER
    An SDF of a database (RDKit «2D», PubChem 2D) has every z = 0 and often no hydrogens: Azimuth added the hydrogens,
    the structures stayed flat, and a queue of MOPAC optimized 44 molecules of the user — crown ethers, cryptands, EDTA
    — from planar starts. «Выровнять геометрию» (cleanup.py) cannot lift them: its gradient keeps a planar molecule in
    its plane. Here a flat structure is told (is_flat) and, on «Геометрия → Сделать 3D (RDKit)…», made three-dimensional
    by RDKit — not a dependency of Azimuth, a Python that has it is found on the computer (or chosen) and runs
    rdkit_embed.py on an SDF of the structures. Wilkinson convention, sections 1-8.

§1 THEORY ETKDGv3 (Riniker, Landrum, J. Chem. Inf. Model. 2015, 55, 2562: distance geometry with torsion preferences
            from crystal structures), then MMFF94 (or UFF), the lowest of N conformers — a start for a calculation, not
            a conformer search (CREST or xtb do that).
§2 ALGORITHM is_flat(molecule, completed=None): the atoms of the file (all of them, hydrogens too), three or more, not
    all on a line, every z the same within FLAT Å, and an atom of three neighbours or more whose VSEPR shape is
    tetrahedral — a planar molecule is not asked. On opening such a file Quill asks «Сделать объёмными?» (offer_3d),
    «Да» runs make_3d. make_3d (Compass) embeds the flat structures of a set (all of them when none is flat) or the
    structure of the tab. sdf_of(molecules, formal): V2000 records with the bonds of the molecule (aromatic 1.5 as 4),
    its explicit hydrogens and «M CHG» of the formal charges (formats.mol_charges of the file, hydrogens added after
    them get 0) — RDKit needs them for N⁺, O⁻. find_python(settings, candidates): the Python of the setting KEY, this
    Python, then the conda bases and their environments (anaconda3, miniconda3, miniforge3, mambaforge in the home
    folder, /opt, Homebrew) whose `python -c "import rdkit"` succeeds (the first one is kept in KEY). run(python,
    molecules, formal, count, timeout): the SDF to a temporary folder, `python -I rdkit_embed.py in out N`, the records
    read back in order (the same atoms; the data item «Azimuth3D» says ok or why it failed — then the structure comes
    back unchanged).
§4 SPECIFICATION FLAT, KEY, CONFORMERS; is_flat(molecule) -> bool; flat_count(molecules) -> int; sdf_of(molecules,
    formal=None) -> str; candidates(home=None) -> [Path]; has_rdkit(python) -> bool; find_python(settings=None,
    candidates=None) -> Path | None; run(python, molecules, formal=None, count=CONFORMERS, timeout=600, step=None) ->
    [(Molecule, ok: bool, note)] (step(done, total) from the lines of rdkit_embed.py; False from it stops RDKit —
    InterruptedError).
§6 NOTES The atom order is kept (Azimuth's labels, charges and the rows of a queue stay valid). In the .exe
rdkit_embed.py
            is beside this module as a data file (packaging/azimuth.spec names it: PyInstaller does not ship .py).
§7 TESTS tests/compass/test_embed3d.py (a fake «Python» that moves every atom out of the plane: the order, the charges
written,
            a failed record kept; is_flat; the search of a Python).
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path

from azimuth.i18n import tr

FLAT = 1e-3  # Å
KEY = 'rdkit_python'
CONFORMERS = 20
SCRIPT = Path(__file__).with_name('rdkit_embed.py')
BASES = ('anaconda3', 'miniconda3', 'miniforge3', 'mambaforge', 'opt/anaconda3', 'opt/miniconda3')
SYSTEM = ('/opt/anaconda3', '/opt/miniconda3', '/opt/miniforge3', '/opt/homebrew/Caskroom/miniforge/base',
          '/opt/homebrew/Caskroom/miniconda/base', '/usr/local/anaconda3', '/usr/local/miniconda3')


def is_flat(molecule, completed=None):
    """A 2D drawing that cannot be the real shape: the heavy atoms (all atoms when fewer than three are heavy) in one
    plane z = const, not on a line — the hydrogens Azimuth adds to a flat skeleton stand out of its plane — and some
    atom with three neighbours or more that is not planar by VSEPR (editing.shape 'tetrahedral': sp³ C, the N of an
    amine, the Cl of ClO₃⁻). A molecule that is planar in reality (benzene, NO₃⁻, water, a 3D file of them) is not
    flat in this sense (it was told for every planar structure). Molecule — as in the file, every atom
    counts (the 3D anti-butane of examples/9-torsion has its carbons in one plane, its hydrogens out of it — not flat;
    it was told); completed — the same with the hydrogens Azimuth added, for the shapes of its atoms."""
    atoms = getattr(molecule, 'atoms', ())
    if not _coplanar(atoms):
        return False
    molecule = completed if completed is not None else molecule
    atoms = molecule.atoms
    from modules.compass.chemistry.editing import shape

    orders = {}
    for i, j, o in _bonds(molecule):
        orders.setdefault(i, []).append(o)
        orders.setdefault(j, []).append(o)
    return any(len(found) >= 3 and shape(atoms[k].symbol, found) == 'tetrahedral' for k, found in orders.items()
               if 0 <= k < len(atoms))


def _coplanar(atoms):
    if len(atoms) < 3:
        return False
    zs = [a.z for a in atoms]
    if max(zs) - min(zs) > FLAT:
        return False
    first = atoms[0]
    for a in atoms[1:]:
        for b in atoms[1:]:
            u = (a.x - first.x, a.y - first.y)
            v = (b.x - first.x, b.y - first.y)
            if abs(u[0] * v[1] - u[1] * v[0]) > 1e-4:
                return True  # not all on a line
    return False


def flat_count(molecules):
    return sum(1 for m in molecules if is_flat(m))


def _bonds(molecule):
    if molecule.bonds is not None:
        return list(molecule.bonds)
    from modules.compass.chemistry.builder import connections

    return list(connections(molecule))


def sdf_of(molecules, formal=None):
    out = []
    for k, molecule in enumerate(molecules):
        bonds = _bonds(molecule)
        charges = list((formal or [()] * len(molecules))[k] or ())
        charges += [0] * (len(molecule.atoms) - len(charges))
        lines = [molecule.title[:80] or 'Azimuth', '  Azimuth', '',
                 f'{len(molecule.atoms):3d}{len(bonds):3d}  0  0  0  0  0  0  0  0999 V2000']
        lines += [f'{a.x:10.4f}{a.y:10.4f}{a.z:10.4f} {a.symbol:<3} 0  0  0  0  0  0  0  0  0  0  0  0'
                  for a in molecule.atoms]
        lines += [f'{i + 1:3d}{j + 1:3d}{4 if abs(o - 1.5) < 1e-6 else int(round(o)):3d}  0' for i, j, o in bonds]
        listed = [(n + 1, q) for n, q in enumerate(charges[:len(molecule.atoms)]) if q]
        for start in range(0, len(listed), 8):
            part = listed[start:start + 8]
            lines.append(f'M  CHG{len(part):3d}' + ''.join(f'{n:4d}{q:4d}' for n, q in part))
        lines += ['M  END', '$$$$']
        out.append('\n'.join(lines))
    return '\n'.join(out) + '\n'


def candidates(home=None):
    home = Path(home or Path.home())
    names = ('python.exe',) if os.name == 'nt' else ('bin/python3', 'bin/python')
    bases = [home / b for b in BASES] + [Path(p) for p in SYSTEM]
    found = []
    for base in bases:
        for root in [base] + (sorted((base / 'envs').glob('*')) if (base / 'envs').is_dir() else []):
            for name in names:
                path = root / name
                if path.is_file() and path not in found:
                    found.append(path)
                    break
    return found


def has_rdkit(python):
    try:
        done = subprocess.run([str(python), '-c', 'import rdkit'], capture_output=True, timeout=30)
        return done.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def find_python(settings=None, candidates_=None):
    saved = settings.value(KEY, '') if settings is not None else ''
    order = ([Path(saved)] if saved else []) + [Path(sys.executable)] + list(
        candidates() if candidates_ is None else candidates_)
    seen = set()
    for python in order:
        if str(python) in seen or not Path(python).is_file():
            continue
        seen.add(str(python))
        if has_rdkit(python):
            if settings is not None:
                settings.setValue(KEY, str(python))
            return Path(python)
    return None


def run(python, molecules, formal=None, count=CONFORMERS, timeout=600, step=None):
    from modules.compass.chemistry import formats

    if not SCRIPT.is_file():
        raise ValueError(tr('Нет файла rdkit_embed.py рядом с программой — переустановите Азимут.'))
    with tempfile.TemporaryDirectory(prefix='azimuth-3d-') as folder:
        source, target = Path(folder) / 'in.sdf', Path(folder) / 'out.sdf'
        source.write_text(sdf_of(molecules, formal), encoding='utf-8')
        # its «k n» lines are the progress (step); step() False — the process is stopped (InterruptedError)
        import time

        log = Path(folder) / 'rdkit.err'  # a file, not a pipe: the warnings of RDKit would fill it and stop the process
        try:
            with open(log, 'w', encoding='utf-8') as err:
                process = subprocess.Popen([str(python), '-I', str(SCRIPT), str(source), str(target), str(int(count))],
                                           stdout=subprocess.PIPE, stderr=err, text=True, encoding='utf-8',
                                           errors='replace')
        except OSError as exc:
            raise ValueError(tr('RDKit не запустился: ') + str(exc)) from None
        start, said = time.monotonic(), []
        try:
            for line in process.stdout:
                said.append(line)
                parts = line.split()
                if step is not None and len(parts) == 2 and all(p.isdigit() for p in parts):
                    if step(int(parts[0]), int(parts[1])) is False:
                        raise InterruptedError()
                if time.monotonic() - start > timeout:
                    raise TimeoutError()
            process.wait(timeout=max(1.0, timeout - (time.monotonic() - start)))
        except (InterruptedError, TimeoutError, subprocess.TimeoutExpired) as exc:
            process.kill()
            process.wait()
            if isinstance(exc, InterruptedError):
                raise
            raise ValueError(tr(f'RDKit не успел за {timeout} с.')) from None
        try:
            error = log.read_text(encoding='utf-8', errors='replace')
        except OSError:
            error = ''
        if process.returncode != 0 or not target.is_file():
            tail = ' '.join((error or ''.join(said)).split())[-300:]
            raise ValueError(tr('RDKit завершился с ошибкой: ') + tail)
        if step is not None:
            step(len(molecules), len(molecules))
        text = target.read_text(encoding='utf-8')
    records = [r for r in text.split('$$$$\n') if r.strip()]
    if len(records) != len(molecules):
        raise ValueError(tr(f'RDKit вернул {len(records)} структур вместо {len(molecules)}.'))
    out = []
    for molecule, record in zip(molecules, records):
        status = formats.sdf_items(record).get('Azimuth3D', '')
        try:
            made = formats.read_mol(record)
        except ValueError as exc:
            out.append((molecule, False, str(exc)))
            continue
        same = [a.symbol for a in made.atoms] == [a.symbol for a in molecule.atoms]
        if not status.startswith('ok') or not same:
            out.append((molecule, False, status or tr('атомы не совпали')))
            continue
        from dataclasses import replace

        out.append((replace(molecule, atoms=made.atoms), True, status[3:].strip()))
    return out

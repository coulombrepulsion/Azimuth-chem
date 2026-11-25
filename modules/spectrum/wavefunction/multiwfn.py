"""Multiwfn (Tian Lu) run in the background on the wavefunction of a result: atomic charges ADCH and CM5;
weak interactions NCI (RDG) and IRI on grids; the topology of the electron density (QTAIM critical points)
and the electrostatic potential on the molecular surface; ELF and LOL on grids; bond orders, the atom composition of the
orbitals, the orbitals and the
density on grids; more functions on grids and on the molecular surface, a function along a line and in a
plane; the analysis of excited states of TD-DFT — the hole and the electron, Δr.

§1 THEORY
    Hirshfeld charges share the density among atoms by their free-atom densities; they are small, and the dipole of
    the molecule made from them is too small. ADCH (Lu & Chen, J. Theor. Comput. Chem. 11, 163 (2012)) adds to each
    atom the charges that reproduce the dipole of its Hirshfeld basin, so the charges give the molecular dipole. CM5
    (Marenich, Jerome, Cramer, Truhlar, J. Chem. Theory Comput. 8, 527 (2012)) corrects Hirshfeld charges by pair
    terms of the bond lengths, fitted to reproduce dipoles; both hardly depend on the basis set, unlike Mulliken.
    NCI (Johnson et al., J. Am. Chem. Soc. 132, 6498 (2010)): the reduced density gradient
        s = |∇ρ| / (2 (3π²)^(1/3) ρ^(4/3))
    is small where the density is nearly flat between atoms; the sign of the second eigenvalue λ₂ of the Hessian of ρ
    tells attraction (λ₂ < 0: hydrogen bonds, ρ ≈ 0.02–0.04) from steric repulsion (λ₂ > 0, rings and cages) and
    weak van der Waals contacts (ρ ≈ 0). The surface s = 0.5 coloured by sign(λ₂)ρ shows them. «Promolecular»: ρ is
    the sum of free-atom densities — only the geometry is needed (rougher, but fine for intermolecular contacts). IRI
    (Lu & Chen, Chemistry–Methods 1, 231 (2021)) = |∇ρ| / ρ^a, a = 1.1: one surface (1.0) shows both chemical bonds
    and weak interactions.
    ELF (Becke & Edgecombe, J. Chem. Phys. 92, 5397 (1990)) compares the kinetic energy density of the electrons with
    that of a uniform electron gas of the same density: near 1 where electrons are paired and localized (cores, bonds,
    lone pairs), 0.5 in an electron gas. LOL (Schmider & Becke, J. Mol. Struct. THEOCHEM 527, 51 (2000)) shows the same
    from the localized orbitals, with sharper boundaries. Their isosurfaces (ELF 0.8, LOL 0.5) draw the bonds and the
    lone pairs as the Lewis picture.
§2 ALGORITHM
    Multiwfn has no programming interface — only text menus; the numbers of the items are given on its input
    (`Multiwfn input.fchk -nt N < answers`), as its manual describes for scripts. The recipe CHARGES (checked on
    Multiwfn 2026.7.15, outputs in tests/data/multiwfn/): 7 (population analysis and atomic charges) → 11 (ADCH) →
    1 (the built-in sphericalized free-atom densities) → n (no .chg file) → 16 (CM5) → 1 → n → 0 → q. The file is
    copied under an ASCII name into a temporary folder (a Fortran program and paths with Cyrillic letters or
    spaces), the type is told by the extension (.fchk, .molden, .wfn …). parse_charges: the block «Final atomic
    charges:» after «Atomic dipole moment corrected (ADC) charges» is ADCH, the one after «CM5 charges» is CM5
    («Atom 1(O ): -0.58474246»; the sum is normalized to the number of electrons by Multiwfn).
    NCI — 20 (weak interactions) → 1 (NCI) | 2 (promolecular NCI) | 4 (IRI) → grid 1 | 2 | 3 (low, medium,
    high: about 125 000, 512 000, 1 728 000 points over the whole system) → 3 (func1.cub = sign(λ₂)ρ, func2.cub = RDG
    or IRI) → 0 → 0 → q. Multiwfn sets RDG to 100 where ρ > 0.05 (its default), so covalent regions have no surface.
    The promolecular one reads the structure from an XYZ file written here (no wavefunction).
    Topology — 2 (topology analysis of ρ) → 2, 3, 4, 5 (Newton searches from the nuclei, the midpoints of all
    atom pairs, the centres of all triangles and tetrahedra of atoms: the search of the Multiwfn manual, it finds the
    critical points of bonds that Compass does not draw, rings and cages) → 8 (the bond paths; without them
    CPprop.txt names no atoms of the bonds) → 7 → 0 (CPprop.txt: every CP with its
    type, position, the atoms of a bond or the nucleus of a maximum, ρ, G, V, H, ∇²ρ, the eigenvalues and eigenvectors
    of the Hessian, the ellipticity) → −10 → q; parse_cps reads it. ESP — 12 (quantitative molecular surface
    analysis: the surface ρ = 0.001 e/bohr³ by marching tetrahedra, the ESP of the wavefunction at its vertices, the
    extrema and the statistics of Murray and Politzer) → 0 → 1 (surfanalysis.txt) → 7 (vtx.txt: the vertices, Å, with
    the ESP in a.u., eV, kcal/mol) → −2 (surf.cub: the grid of ρ of the surface) → −1 → −1 → q; parse_surface reads the
    extrema and the summary of the output.
    ELF and LOL — 5 (a property on a grid) → 9 (ELF) | 10 (LOL) → grid 1 | 2 | 3 → 2 (ELF.cub or LOL.cub) → 0 →
    q; run_function.
    Bond orders — 9 → 1 (Mayer) → n → 3 (Wiberg in the Löwdin orthogonalized basis) → n → 7 (fuzzy) → n → 8
    (Laplacian) → n → 0 → q: every table «# k: i(A) j(B) order» ends before «If outputting bond order matrix», so the
    blocks come in the order asked (parse_bond_orders); the Mayer valences follow the Mayer table. The composition of
    the orbitals — 8 → 8 (Hirshfeld) → 1 (built-in atomic densities) → 1, 2, … N (every orbital) → 0 → −10 → q: each
    «Orbital: k Energy(a.u.): e …» with «Contributions after normalization: Atom i(A) : p %» (parse_composition). The
    orbitals and the density on a grid — 5 → 4 (an orbital) → its index | 1 (ρ) → grid 1 | 2 | 3 → 2 → 0 → q
    (MOvalue.cub, density.cub). The index of Multiwfn counts the alpha orbitals first, then the beta ones.
    Along a line — 3 → the function → 1 (two atoms) → «i,j» → 2 (line.txt: x, y, z Å, the position along the
    line Å, the value; 3000 points, the line runs 1.5 bohr past both atoms) → 0 → q. In a plane — 4 → the function → 1
    (a colour map) → «N,N» → 4 (three atoms) → «i,j,k» → −6 (plane.txt: x, y, z Å, the two coordinates in the plane
    Å, the value; the second coordinate runs fastest) → −5 → q. On the molecular surface other functions than the ESP:
    12 → 2 → 2 (ALIE) | 4 (LEA) | −4 (LEAE) → 0 …
§3 APPLICATIONS Compass, «±» → «Заряды ADCH и CM5 (Multiwfn)…» (modules/compass/actions/property_actions.py): the
    charges are added to the Properties of the result and shown on the model like those of ORCA.
§4 SPECIFICATION
    find(configured=None, path_env=None, home=None, search=None) -> Path | None; version(text) -> str | None;
    wavefunction_name(path) -> 'input.<ext>' (ValueError: a file Multiwfn does not read);
    parse_charges(text) -> {'adch': tuple, 'cm5': tuple} (keys present only when found);
    run_charges(program, path, cores=1, step=None, timeout=600) -> (charges, output text, version);
    CITATION, CITATIONS (the papers Multiwfn asks to cite, and those of the methods).
    run_nci(program, path, kind='nci'|'promolecular'|'iri', grid='low'|'medium'|'high', cores=1, step=None,
            timeout=1800, molecule=None) -> (sign_cube, field_cube, output text, version) — cubes of
            modules/spectrum/readers/cube.py; for 'promolecular' molecule (a Molecule) is written as XYZ, path is
            ignored.
    scatter(sign, field, x=(low, high), top, limit=60000, seed=0, floor=0.0) -> (xs, ys): the points of the plot RDG
    (IRI;
            δg_inter of IGMH above floor) — sign(λ₂)ρ inside the window, at most limit of them (a random choice
            when there are more).
    parse_cps(text) -> [dict kind ('nucleus' | 'bond' | 'ring' | 'cage'), position (Å), bohr, atoms (0-based), rho,
            kinetic G, potential V, energy H, laplacian, eigenvalues (3), vectors (3, 3; columns), ellipticity].
    run_topology(program, path, cores=1, step=None, timeout=1800) -> (cps, output text, version, warnings).
    parse_surface(text) -> {'minima': [(kcal/mol, (x, y, z) Å, global)], 'maxima': [...], 'summary': {key: value}};
    read_vertices(text) -> (points (n, 3) Å, esp (n) a.u.).
    run_esp(program, path, cores=1, step=None, timeout=1800, mapped='esp') -> dict: minima, maxima (and their
            '_units': (a.u., eV)), summary, points, esp (the mapped function at the vertices, a.u.), density (Cube of
            the grid of ρ), text, version, mapped.
    run_function(program, path, name (a key of FUNCTIONS: rho, gradient, laplacian, spin, k, g, elf, lol, entropy,
            esp, rdg, alie), grid='low', cores=1, step=None, timeout=1800) -> (Cube, text, version).
    parse_bond_orders(text) -> {'mayer' | 'wiberg' | 'fuzzy' | 'laplacian': [(i, j, order)] (0-based)}, plus
            'valence': (Mayer valences) when printed; run_bond_orders(program, path, cores, step) -> (orders, text,
            version).
    parse_composition(text) -> {orbital index (1-based): (energy hartree, {atom (0-based): percent})};
            run_composition(program, path, count, cores, step) -> (composition, text, version).
    run_grid(program, path, what ('orbital' | 'density' | 'spin'), index=None (1-based), grid='medium', cores, step) ->
    Cube;
            field_cube(quiet, orbital_set, what, index, step, spin, progress) -> Cube (Multiwfn when given).
    The cache of the runs (_cache, clear_cache()); version_tuple(number), is_old(number) (before OLD_VERSION
            3.8); on_version(number, old) — called once for every version met.
            grid_for_step(step Å) -> 'low' | 'medium' | 'high' (0.10 Å of the panels).
    LINE_FUNCTIONS — the functions of the line and the plane; run_line(program, path, name, atoms (i, j) 0-based, cores,
            step) -> {'points' (n, 3) Å, 'x' (n) Å, 'values' (n), 'text', 'version'}; read_line(text);
    run_plane(program, path, name, atoms (i, j, k), size=100, …) -> {'points' (n1, n2, 3), 'u' (n1), 'v' (n2), 'values'
            (n1, n2), …}; read_plane(text).
    PLOT_WINDOWS = {'nci': ((−0.05), 2.0), 'iri': ((−0.4), 2.5)} (Multiwfn's IRI window; for NCI the
            range of the papers, narrower than Multiwfn's −0.1 … 0.1).
    ValueError: no file, no program, Multiwfn failed or printed no charges, cancelled.
§6 NOTES
    Multiwfn is free for teaching and commercial use (its licence; sobereva.com/multiwfn); Azimuth does not ship
    it, it finds the installed one: Homebrew on macOS (/opt/homebrew/bin), the official noGUI builds elsewhere.
    The old 3.7 build is looked for last; when it is the one that runs, the window says so once (on_version).
    OMP_STACKSIZE=200M as its manual asks.
§7 TESTS
    tests/spectrum/test_multiwfn.py: the recorded outputs of water (Gaussian fchk) and methane (ORCA Molden), a fake
    Multiwfn that prints a recorded output, the search order.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from azimuth.i18n import tr

NAMES = ('Multiwfn', 'multiwfn', 'Multiwfn_noGUI')
CHARGES = ('7', '11', '1', 'n', '16', '1', 'n', '0', 'q', 'q')
CITATION = 'T. Lu, F. Chen, J. Comput. Chem. 33, 580 (2012); T. Lu, J. Chem. Phys. 161, 082503 (2024)'
CITATIONS = {
    'adch': 'T. Lu, F. Chen, J. Theor. Comput. Chem. 11, 163 (2012)',
    'cm5': 'A. V. Marenich, S. V. Jerome, C. J. Cramer, D. G. Truhlar, J. Chem. Theory Comput. 8, 527 (2012)',
    'nci': 'E. R. Johnson, S. Keinan, P. Mori-Sánchez, J. Contreras-García, A. J. Cohen, W. Yang, '
           'J. Am. Chem. Soc. 132, 6498 (2010)',
    'iri': 'T. Lu, Q. Chen, Chemistry–Methods 1, 231 (2021)',
    'surface': 'T. Lu, F. Chen, J. Mol. Graph. Model. 38, 314 (2012)',
    'elf': 'A. D. Becke, K. E. Edgecombe, J. Chem. Phys. 92, 5397 (1990)',
    'lol': 'H. L. Schmider, A. D. Becke, J. Mol. Struct. THEOCHEM 527, 51 (2000)',
}
FUNCTIONS = {  # the real space functions of 5 (a property on a grid) offered as surfaces
    'rho': '1', 'gradient': '2', 'laplacian': '3', 'spin': '5', 'k': '6', 'g': '7', 'elf': '9', 'lol': '10',
    'entropy': '11', 'esp': '12', 'rdg': '13', 'alie': '18',
}
NCI = {'nci': '1', 'promolecular': '2', 'iri': '4'}
GRIDS = {'low': '1', 'medium': '2', 'high': '3'}
EXTENSIONS = {'.fchk': '.fchk', '.fch': '.fch', '.molden': '.molden', '.input': '.molden', '.molf': '.molden',
              '.mold': '.molden', '.wfn': '.wfn', '.wfx': '.wfx', '.mwfn': '.mwfn'}
_ROW = re.compile(r'^\s*Atom\s+(\d+)\(\s*([A-Za-z]{1,3})\s*\)\s*:\s*(-?\d+\.\d+)\s*$')


def _runnable(path):
    return path.is_file() and os.access(path, os.X_OK)


def windows_dirs(home, drives=None):
    """Where Multiwfn lies on Windows — it is a zip unpacked anywhere: the folders «Multiwfn*» in the home
    folder, on the Desktop, in Downloads and Documents, at the root of the drives and in Program Files. Also
    the Desktop and Documents of OneDrive (Windows 11 keeps them there), and one level deeper — «Извлечь всё» of
    Explorer puts the archive into a folder of its name: C:\\Multiwfn_…_Win64\\Multiwfn_…_Win64\\Multiwfn.exe."""
    roots = [home, home / 'Desktop', home / 'Downloads', home / 'Documents', home / 'OneDrive' / 'Desktop',
             home / 'OneDrive' / 'Documents', home / 'OneDrive' / 'Рабочий стол']
    for drive in drives if drives is not None else ('C:', 'D:', 'E:'):
        roots += [Path(drive + '\\'), Path(drive + '\\') / 'Program Files', Path(drive + '\\') / 'Program Files (x86)']
    found = []
    for root in roots:
        try:
            for d in sorted((d for d in root.glob('Multiwfn*') if d.is_dir()), reverse=True):
                found.append(d)
                found += sorted((s for s in d.glob('Multiwfn*') if s.is_dir()), reverse=True)
        except OSError:
            continue
    return found


def find(configured=None, path_env=None, home=None, search=None):
    """The configured file, PATH, Multiwfnpath, Homebrew and the usual folders; the old 3.7 build in /Applications
    last. Search=False (or the environment AZIMUTH_MULTIWFN_SEARCH=0, set by the window tests) — only the
    configured file."""
    if configured and _runnable(Path(configured)):
        return Path(configured)
    if search is None:
        search = os.environ.get('AZIMUTH_MULTIWFN_SEARCH', '1') != '0'
    if not search:
        return None
    path_env = os.environ.get('PATH', '') if path_env is None else path_env
    home = Path(home or Path.home())
    dirs = [Path(d) for d in path_env.split(os.pathsep) if d]
    if os.environ.get('Multiwfnpath'):
        dirs.append(Path(os.environ['Multiwfnpath']))
    dirs += [Path('/opt/homebrew/bin'), Path('/usr/local/bin'), home / 'Multiwfn', home / 'Multiwfn_noGUI']
    dirs += sorted(home.glob('Multiwfn*'), reverse=True) + sorted(Path('/Applications').glob('Multiwfn*'), reverse=True)
    if os.name == 'nt':
        dirs += windows_dirs(home)
    names = tuple(n + '.exe' for n in NAMES) + NAMES if os.name == 'nt' else NAMES
    for d in dirs:
        for name in names:
            if _runnable(d / name):
                return d / name
    return None


def version(text):
    match = re.search(r'Version\s+([0-9][0-9.]*(?:\s*\(dev\))?)', text)
    return match.group(1).strip() if match else None


def wavefunction_name(path):
    """The ASCII name of the copy; Multiwfn tells the format by the extension («.molden.input» of ORCA → .molden)."""
    suffix = Path(path).suffix.lower()
    if suffix not in EXTENSIONS:
        raise ValueError(tr('Multiwfn читает волновую функцию из файлов fchk, Molden, wfn, wfx и mwfn — '
                            'у этого результата такого файла нет.'))
    return 'input' + EXTENSIONS[suffix]


def _final(lines, start):
    """The rows of the first «Final atomic charges:» block after line start."""
    for k in range(start, len(lines)):
        if lines[k].strip().startswith('Final atomic charges'):
            values = []
            for line in lines[k + 1:]:
                match = _ROW.match(line)
                if not match:
                    break
                values.append(float(match.group(3)))
            return tuple(values), k
    return None, len(lines)


def parse_charges(text):
    lines = text.replace('\r', '').split('\n')
    found = {}
    for key, marker in (('adch', 'Atomic dipole moment corrected (ADC) charges'), ('cm5', 'CM5 charges ---')):
        for k, line in enumerate(lines):
            if marker in line:
                values, _ = _final(lines, k)
                if values:
                    found[key] = values
                break
    return found


# the runs already made in this session — the same program, the same file (its content), the same
# answers give the same output; a second request of a surface, a table or an excited state is instant
CACHE_SIZE = 12
CACHE_BYTES = 400_000_000
_cache = {}  # key -> (text, kept); the newest last
OLD_VERSION = (3, 8)  # the builds before 3.8 (the old 3.7 of /Applications) lack items of the recipes used here
on_version = None  # (version string, old: bool) -> None — set by the window: a notice once for an old Multiwfn
_versions_said = set()


def version_tuple(number):
    """«3.7» -> (3, 7); «2026.7.15» -> (2026, 7, 15); None for no version."""
    if not number:
        return None
    parts = re.findall(r'\d+', number)
    return tuple(int(x) for x in parts) if parts else None


def is_old(number):
    found = version_tuple(number)
    return found is not None and found < OLD_VERSION


def _stamp(path):
    """The content of the file (SHA-256 and size, azimuth/runtime/provenance.py), not its path and time — a
    file replaced by another of the same size and time is a new key, a project moved keeps its keys."""
    from azimuth.runtime.provenance import fingerprint

    return fingerprint(path)


def _cache_key(program, path, answers, name, keep):
    if callable(path):
        source = getattr(path, 'key', None)
        if source is None:
            return None
    else:
        source = _stamp(path)
        if source is None:
            return None
    return str(program), source, tuple(answers), name, tuple(keep)


def clear_cache():
    _cache.clear()


def _remember(key, text, kept):
    if key is None:
        return
    _cache.pop(key, None)
    _cache[key] = (text, dict(kept))
    total = sum(len(t) + sum(len(v) for v in k.values()) for t, k in _cache.values())
    while _cache and (len(_cache) > CACHE_SIZE or total > CACHE_BYTES):
        oldest = next(iter(_cache))
        t, k = _cache.pop(oldest)
        total -= len(t) + sum(len(v) for v in k.values())


def _said(text):
    number = version(text)
    if number and number not in _versions_said and on_version is not None:
        _versions_said.add(number)
        try:
            on_version(number, is_old(number))
        except Exception:  # a notice must never break a calculation
            pass


def command(program, name, cores=1, windows=None):
    """The command line. On Windows the build is the one with the graphical window, which opens its pictures and
    waits for them to be closed — «-silent» keeps it in the text mode, as a script needs (the noGUI builds of macOS and
    Linux have no window)."""
    windows = os.name == 'nt' if windows is None else windows
    args = [str(program), name, '-nt', str(max(1, int(cores)))]
    return args + ['-silent'] if windows else args


def windows_answers(program, folder, answers, windows=None, environ=None):
    """The answers as the build for Windows reads them. Without «settings.ini» in the current folder or in
    the folder of the variable Multiwfnpath it says so and waits — «Press ENTER button to continue» — and takes the
    first answer for that ENTER: every answer moves by one and Multiwfn falls at the end of them («forrtl: severe (24):
    end-of-file during read», Multiwfn 2026.10.18; the builds of macOS only warn).
    So the settings.ini of its package (next to Multiwfn.exe) or of Multiwfnpath is copied into the folder of the run —
    the settings of the user are kept —, and when there is none an empty line is the first answer."""
    windows = os.name == 'nt' if windows is None else windows
    if not windows:
        return tuple(answers)
    environ = os.environ if environ is None else environ
    places = [Path(program).parent] + ([Path(environ['Multiwfnpath'])] if environ.get('Multiwfnpath') else [])
    for place in places:
        settings = place / 'settings.ini'
        if settings.is_file():
            try:
                shutil.copyfile(settings, Path(folder) / 'settings.ini')
                return tuple(answers)
            except OSError:
                break
    return ('',) + tuple(answers)


def work_folder(windows=None, base=None):
    """The temporary folder of a run. Multiwfn (Fortran) opens files by names in the current folder; on Windows
    the temporary folder is inside the user's profile, and a Cyrillic user name («C:\\Users\\Сергей\\AppData…») breaks
    that — then a folder with an ASCII path is used (C:\\Users\\Public, or the root of the drive)."""
    windows = os.name == 'nt' if windows is None else windows
    folder = Path(tempfile.mkdtemp(prefix='azimuth-multiwfn-', dir=base))
    if not windows or str(folder).isascii():
        return folder
    shutil.rmtree(folder, ignore_errors=True)
    for root in (os.environ.get('PUBLIC', ''), os.environ.get('SystemDrive', 'C:') + '\\'):
        if root and root.isascii():
            try:
                target = Path(root) / 'AzimuthTemp'
                target.mkdir(exist_ok=True)
                return Path(tempfile.mkdtemp(prefix='azimuth-multiwfn-', dir=target))
            except OSError:
                continue
    return Path(tempfile.mkdtemp(prefix='azimuth-multiwfn-', dir=base))


def _run(program, path, answers, cores=1, step=None, timeout=600, name=None, keep=()):
    """Multiwfn on a copy of path (or, when path is a function of the folder, on the file it writes there) in a
    temporary folder;
    returns (output text, {kept file: text}). step() returning False cancels (the process is killed). The
    result of the same run is taken from the cache (_cache; a function path gives its .key)."""
    if program is None:
        raise ValueError(tr('Multiwfn не найден — установите его (macOS: brew install multiwfn; Windows: архив с '
                            'sobereva.com/multiwfn, файл Multiwfn.exe) или укажите файл программы.'))
    key = _cache_key(program, path, answers, name, keep)
    if key is not None and key in _cache:
        text, kept = _cache.pop(key)
        _cache[key] = (text, kept)
        return text, dict(kept)
    folder = work_folder()
    try:
        if callable(path):  # it writes the input itself
            name = path(folder)
        else:
            path = Path(path)
            if not path.is_file():
                raise ValueError(tr('Файл волновой функции не найден: ') + str(path))
            name = name or wavefunction_name(path)
            shutil.copyfile(path, folder / name)
        env = dict(os.environ, OMP_STACKSIZE=os.environ.get('OMP_STACKSIZE', '200M'))
        with open(folder / 'output.txt', 'w', encoding='utf-8', errors='replace') as out:
            try:
                flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if os.name == 'nt' else 0  # no black console
                process = subprocess.Popen(command(program, name, cores), cwd=folder, env=env, stdin=subprocess.PIPE,
                                           stdout=out, stderr=subprocess.STDOUT, text=True, creationflags=flags,
                                           encoding='utf-8', errors='replace')  # the answers
            except OSError as exc:  # a moved or broken program
                raise ValueError(tr('Multiwfn не запускается: ') + str(exc)) from None
            try:
                process.stdin.write('\n'.join(windows_answers(program, folder, answers)) + '\n')
                process.stdin.close()
            except OSError:
                pass
            start = time.monotonic()
            while process.poll() is None:
                if (step is not None and step(0, 0) is False) or time.monotonic() - start > timeout:
                    process.kill()
                    process.wait()
                    raise InterruptedError(tr('Расчёт в Multiwfn остановлен.'))  # not a failure
                time.sleep(0.1)
        text = (folder / 'output.txt').read_text(encoding='utf-8', errors='replace')
        if process.returncode not in (0, None) and not version(text):  # it did not even start its menus
            raise ValueError(tr(f'Multiwfn завершился с кодом {process.returncode} и ничего не посчитал: ')
                             + str(program) + ('\n' + _tail(text) if text.strip() else ''))
        kept = {}
        for item in keep:  # a name or a pattern ('*.cub')
            for found in sorted(folder.glob(item)) if any(c in item for c in '*?[') else [folder / item]:
                if found.is_file() and found.name != name:
                    kept[found.name] = found.read_text(encoding='utf-8', errors='replace')
        _said(text)
        _remember(key, text, kept)
        return text, kept
    finally:
        shutil.rmtree(folder, ignore_errors=True)


def _tail(text):
    return '\n'.join(text.strip().split('\n')[-6:])


def run_charges(program, path, cores=1, step=None, timeout=600):
    text, _ = _run(program, path, CHARGES, cores, step, timeout)
    charges = parse_charges(text)
    if not charges:
        raise ValueError(tr('Multiwfn не напечатал зарядов. Конец его вывода:') + '\n' + _tail(text))
    return charges, text, version(text)


def xyz_text(molecule):
    rows = [f'{a.symbol} {a.x:.8f} {a.y:.8f} {a.z:.8f}' for a in molecule.atoms]
    return f'{len(rows)}\n{molecule.title or "Azimuth"}\n' + '\n'.join(rows) + '\n'


def run_nci(program, path, kind='nci', grid='low', cores=1, step=None, timeout=1800, molecule=None):
    """The grids of sign(λ₂)ρ and of RDG (or IRI) as Cubes (Å), with the output and the version of Multiwfn."""
    from modules.spectrum.readers.cube import read_cube

    if kind not in NCI or grid not in GRIDS:
        raise ValueError(kind if kind not in NCI else grid)
    answers = ('20', NCI[kind], GRIDS[grid], '3', '0', '0', 'q', 'q')
    if kind == 'promolecular':
        if molecule is None or not molecule.atoms:
            raise ValueError(tr('Для промолекулярной плотности нужна структура.'))

        xyz = xyz_text(molecule)

        def path(folder):
            (folder / 'input.xyz').write_text(xyz, encoding='utf-8')
            return 'input.xyz'

        path.key = ('xyz', xyz)

    text, kept = _run(program, path, answers, cores, step, timeout, keep=('func1.cub', 'func2.cub'))
    if set(kept) != {'func1.cub', 'func2.cub'}:
        raise ValueError(tr('Multiwfn не записал сетки NCI. Конец его вывода:') + '\n' + _tail(text))
    sign, field = read_cube(kept['func1.cub']), read_cube(kept['func2.cub'])
    if sign.values.shape != field.values.shape:
        raise ValueError(tr('Сетки разного размера.'))
    return sign, field, text, version(text)


PLOT_WINDOWS = {'nci': ((-0.05, 0.05), 2.0), 'iri': ((-0.4, 0.1), 2.5), 'igmh': ((-0.05, 0.05), 0.05)}  # δg_inter


def scatter(sign, field, x=(-0.05, 0.05), top=2.0, limit=60000, seed=0, floor=0.0):
    """floor: only the points above it — δg_inter of IGMH is zero almost everywhere."""
    import numpy as np

    xs = np.asarray(sign.values[..., 0], float).ravel()
    ys = np.asarray(field.values[..., 0], float).ravel()
    inside = (xs >= x[0]) & (xs <= x[1]) & (ys >= floor) & (ys <= top)
    xs, ys = xs[inside], ys[inside]
    if len(xs) > limit:
        keep = np.random.default_rng(seed).choice(len(xs), limit, replace=False)
        xs, ys = xs[keep], ys[keep]
    return xs, ys


# -- topology ---------------------------------------------------------------------------------------------------
TOPOLOGY = ('2', '2', '3', '4', '5', '8', '7', '0', '-10', 'q', 'q')  # 8 — the bond paths: then CPprop.txt
# names the «Connected atoms» of every bond point (without them it does not)
CP_KINDS = {'(3,-3)': 'nucleus', '(3,-1)': 'bond', '(3,+1)': 'ring', '(3,+3)': 'cage'}
_CP_HEAD = re.compile(r'CP\s+(\d+),\s+Type\s+(\(3,[-+]\d\))')
_ATOM = re.compile(r'(\d+)\(\s*[A-Za-z]{1,3}\s*\)?')


def _numbers(line):
    return [float(v.replace('D', 'E')) for v in re.findall(r'-?\d+\.\d*(?:[EeDd][-+]?\d+)?', line.split(':', 1)[1])]


def parse_cps(text):
    import numpy as np

    found = []
    blocks = re.split(r'^\s*-{6,}\s+(?=CP\s+\d+,)', text.replace('\r', ''), flags=re.M)
    for block in blocks:
        head = _CP_HEAD.match(block.strip())
        if not head:
            continue
        lines = block.split('\n')
        cp = {'index': int(head.group(1)), 'kind': CP_KINDS.get(head.group(2), 'unknown'), 'atoms': (),
              'ellipticity': None}
        for k, line in enumerate(lines):
            name = line.strip()
            if name.startswith('Connected atoms:') or name.startswith('Corresponding nucleus:'):
                cp['atoms'] = tuple(int(n) - 1 for n in _ATOM.findall(name.split(':', 1)[1]))
            elif name.startswith('Position (Angstrom):'):
                cp['position'] = np.array(_numbers(name))
            elif name.startswith('Position (Bohr):'):
                cp['bohr'] = np.array(_numbers(name))
            elif name.startswith('Density of all electrons:'):
                cp['rho'] = _numbers(name)[0]
            elif name.startswith('Lagrangian kinetic energy G(r):'):
                cp['kinetic'] = _numbers(name)[0]
            elif name.startswith('Potential energy density V(r):'):
                cp['potential'] = _numbers(name)[0]
            elif name.startswith('Energy density E(r) or H(r):'):
                cp['energy'] = _numbers(name)[0]
            elif name.startswith('Laplacian of electron density:'):
                cp['laplacian'] = _numbers(name)[0]
            elif name.startswith('Eigenvalues of Hessian:'):
                cp['eigenvalues'] = np.array(_numbers(name))
            elif name.startswith('Eigenvectors (columns) of Hessian:'):
                cp['vectors'] = np.array([[float(v) for v in lines[k + r].split()] for r in (1, 2, 3)])
            elif name.startswith('Ellipticity of electron density:'):
                cp['ellipticity'] = _numbers(name)[0]
        if all(key in cp for key in ('position', 'rho', 'laplacian', 'eigenvalues')):
            if cp['kind'] != 'bond':
                cp['ellipticity'] = None
            found.append(cp)
    return found


def run_topology(program, path, cores=1, step=None, timeout=1800):
    text, kept = _run(program, path, TOPOLOGY, cores, step, timeout, keep=('CPprop.txt',))
    cps = parse_cps(kept.get('CPprop.txt', ''))
    if not cps:
        raise ValueError(tr('Multiwfn не нашёл критических точек. Конец его вывода:') + '\n' + _tail(text))
    warnings = []
    if 'Some (3,-3) may missing' in text:
        warnings.append(tr('Найдены не все максимумы плотности (ядра). Так бывает с волновой функцией xtb (минимальный '
                           'базис, остов приближённо) — для QTAIM нужна DFT или HF.'))
    return cps, text, version(text), warnings


# -- the ESP on the molecular surface ----------------------------------------------------------------------------
ESP_SURFACE = ('12', '0', '1', '7', '-2', '-1', '-1', 'q', 'q')
MAPPED = {'esp': '1', 'alie': '2', 'lea': '4', 'leae': '-4'}  # 12 → 2 → the function mapped on the surface
SUMMARY = (  # (key, the start of the line, which number after its first «:») — Å³, Å², kcal/mol as Multiwfn prints
    ('volume', 'Volume:', 1), ('area', 'Overall surface area:', 1), ('positive_area', 'Positive surface area:', 1),
    ('negative_area', 'Negative surface area:', 1), ('minimum', 'Minimal value:', 0), ('maximum', 'Minimal value:', 1),
    ('average', 'Overall average value:', 1), ('positive_average', 'Positive average value:', 1),
    ('negative_average', 'Negative average value:', 1), ('variance', 'Overall variance (sigma^2_tot):', 1),
    ('balance', 'Balance of charges (nu):', 0), ('product', 'Product of sigma^2_tot and nu:', 1),
    ('separation', 'Internal charge separation (Pi):', 1), ('mpi', 'Molecular polarity index (MPI):', 1),
    ('nonpolar_area', 'Nonpolar surface area', 0), ('nonpolar_share', 'Nonpolar surface area', 1),
    ('polar_area', 'Polar surface area', 0), ('polar_share', 'Polar surface area', 1),
    ('average_ev', 'Average value:', 1), ('variance_ev', 'Variance:', 1),  # ALIE, LEA… (eV, eV²)
)


def parse_surface(text):
    """The extrema (kcal/mol, Å, the global one) and the summary of the last surface analysis in the output."""
    lines = text.replace('\r', '').split('\n')
    start = max((k for k, line in enumerate(lines) if 'Summary of surface analysis' in line), default=0)
    head = max((k for k, line in enumerate(lines[:start]) if 'Global surface minimum' in line), default=0)
    out = {'minima': [], 'maxima': [], 'summary': {}}
    for k in range(head, len(lines)):
        name = lines[k].strip()
        target = 'minima' if name.startswith('The number of surface minima') else (
            'maxima' if name.startswith('The number of surface maxima') else None)
        if not target:
            continue
        for row in lines[k + 2:]:
            fields = row.replace('*', ' ').split()
            if len(fields) != 7:
                break
            try:
                values = [float(v) for v in fields[1:]]
            except ValueError:
                break
            out[target].append((values[2], tuple(values[3:6]), row.lstrip().startswith('*')))
            out.setdefault(target + '_units', []).append((values[0], values[1]))  # a.u., eV
    for key, begin, index in SUMMARY:
        for line in lines[start:]:
            name = line.strip()
            if name.startswith(begin) and ':' in name:
                numbers = re.findall(r'-?\d+\.\d+', name.split(':', 1)[1])
                if len(numbers) > index:
                    out['summary'][key] = float(numbers[index])
                break
    return out


def read_vertices(text):
    import numpy as np

    rows = text.split('\n')
    count = int(rows[0].split()[0])
    data = np.array([[float(v) for v in row.split()[:4]] for row in rows[1:1 + count] if row.strip()])
    if data.shape != (count, 4):
        raise ValueError(tr('Неполный файл вершин поверхности.'))
    return data[:, :3], data[:, 3]


def run_esp(program, path, cores=1, step=None, timeout=1800, mapped='esp'):
    """Mapped — the function on the surface: 'esp', 'alie', 'lea', 'leae' (MAPPED)."""
    from modules.spectrum.readers.cube import read_cube

    if mapped not in MAPPED:
        raise ValueError(mapped)
    answers = ESP_SURFACE if mapped == 'esp' else ('12', '2', MAPPED[mapped], '0', '1', '7', '-2', '-1', '-1', 'q', 'q')
    text, kept = _run(program, path, answers, cores, step, timeout, keep=('vtx.txt', 'surf.cub'))
    if set(kept) != {'vtx.txt', 'surf.cub'}:
        raise ValueError(tr('Multiwfn не закончил анализ поверхности. Конец его вывода:') + '\n' + _tail(text))
    found = parse_surface(text)
    points, esp = read_vertices(kept['vtx.txt'])
    found.update(points=points, esp=esp, density=read_cube(kept['surf.cub']), text=text, version=version(text),
                 mapped=mapped)
    return found


# -- ELF and LOL ------------------------------------------------------------------------------------------------
def run_function(program, path, name='elf', grid='low', cores=1, step=None, timeout=1800):
    from modules.spectrum.readers.cube import read_cube

    if name not in FUNCTIONS or grid not in GRIDS:
        raise ValueError(name if name not in FUNCTIONS else grid)
    text, kept = _run(program, path, ('5', FUNCTIONS[name], GRIDS[grid], '2', '0', 'q', 'q'), cores, step, timeout,
                      keep=('*.cub',))
    if not kept:
        raise ValueError(tr('Multiwfn не записал сетку. Конец его вывода:') + '\n' + _tail(text))
    return read_cube(next(iter(kept.values()))), text, version(text)


# -- bond orders, the composition of the orbitals, grids of orbitals and density ----------------------------------
BOND_ORDERS = ('9', '1', 'n', '3', 'n', '7', 'n', '8', 'n', '0', 'q', 'q')
BOND_KINDS = ('mayer', 'wiberg', 'fuzzy', 'laplacian')
_BOND = re.compile(r'#\s*\d+:\s*(\d+)\(\s*[A-Za-z]{1,3}\s*\)\s*(\d+)\(\s*[A-Za-z]{1,3}\s*\)\s*:?\s*(-?\d+\.\d+)')
_VALENCE = re.compile(r'^\s*Atom\s+(\d+)\(\s*[A-Za-z]{1,3}\s*\)\s*:\s*(-?\d+\.\d+)\s+(-?\d+\.\d+)')


def parse_bond_orders(text):
    blocks = text.replace('\r', '').split('If outputting bond order matrix')
    found = {}
    for kind, block in zip(BOND_KINDS, blocks):
        last = max(block.rfind('Bond orders with absolute value'), block.rfind('The total bond order'),
                   block.rfind('The bond orders >='))
        if last < 0:
            continue
        rows = [(int(m.group(1)) - 1, int(m.group(2)) - 1, float(m.group(3))) for m in _BOND.finditer(block[last:])]
        found[kind] = [(min(i, j), max(i, j), order) for i, j, order in rows]
        if kind == 'mayer' and 'Total valences' in block:
            part = block[block.index('Total valences'):]
            values = [float(m.group(2)) for m in (_VALENCE.match(line) for line in part.split('\n')) if m]
            if values:
                found['valence'] = tuple(values)
    return found


def run_bond_orders(program, path, cores=1, step=None, timeout=1800):
    text, _ = _run(program, path, BOND_ORDERS, cores, step, timeout)
    orders = parse_bond_orders(text)
    if not any(kind in orders for kind in BOND_KINDS):
        raise ValueError(tr('Порядки связей не напечатаны. Конец вывода Multiwfn:') + '\n' + _tail(text))
    return orders, text, version(text)


_ORBITAL = re.compile(r'Orbital:\s*(\d+)\s+Energy\(a\.u\.\):\s*(-?\d+\.\d+)')
_SHARE = re.compile(r'^\s*Atom\s+(\d+)\(\s*[A-Za-z]{1,3}\s*\)\s*:\s*(-?\d+\.\d+)\s*%')


def parse_composition(text):
    lines = text.replace('\r', '').split('\n')
    found = {}
    current = None
    for k, line in enumerate(lines):
        head = _ORBITAL.search(line)
        if head:
            current = (int(head.group(1)), float(head.group(2)))
            continue
        if current is not None and line.strip().startswith('Contributions after normalization'):
            shares = {}
            for row in lines[k + 1:]:
                match = _SHARE.match(row)
                if not match:
                    break
                shares[int(match.group(1)) - 1] = float(match.group(2))
            found[current[0]] = (current[1], shares)
            current = None
    return found


def run_composition(program, path, count, cores=1, step=None, timeout=3600):
    answers = ('8', '8', '1', *(str(k) for k in range(1, int(count) + 1)), '0', '-10', 'q', 'q')
    text, _ = _run(program, path, answers, cores, step, timeout)
    found = parse_composition(text)
    if not found:
        raise ValueError(tr('Состав орбиталей не напечатан. Конец вывода Multiwfn:') + '\n' + _tail(text))
    return found, text, version(text)


def grid_for_step(step):
    return 'high' if step <= 0.11 else ('medium' if step <= 0.2 else 'low')


def run_grid(program, path, what='orbital', index=None, grid='medium', cores=1, step=None, timeout=1800):
    from modules.spectrum.readers.cube import read_cube

    if what == 'orbital':
        if not index or int(index) < 1:
            raise ValueError('index')
        answers = ('5', '4', str(int(index)), GRIDS[grid], '2', '0', 'q', 'q')
    elif what == 'density':
        answers = ('5', '1', GRIDS[grid], '2', '0', 'q', 'q')
    elif what == 'spin':  # the spin density ρα − ρβ (function 5 of Multiwfn)
        answers = ('5', '5', GRIDS[grid], '2', '0', 'q', 'q')
    else:
        raise ValueError(what)
    text, kept = _run(program, path, answers, cores, step, timeout, keep=('*.cub',))
    if not kept:
        raise ValueError(tr('Multiwfn не записал сетку. Конец его вывода:') + '\n' + _tail(text))
    return read_cube(next(iter(kept.values())))


def orbital_number(orbital_set, k):
    """The index of Multiwfn (1-based: the alpha orbitals, then the beta ones) of the orbital k of orbital_set."""
    orbitals = orbital_set.orbitals
    spin = orbitals[k].spin
    same = sum(1 for o in orbitals[:k] if o.spin == spin)
    alphas = sum(1 for o in orbitals if o.spin != 'beta')
    return same + 1 + (alphas if spin == 'beta' else 0)


def composition_of(orbital_set, found, tolerance=2e-3):
    """{orbital k of orbital_set: {atom: percent}} from parse_composition, every orbital checked by its energy."""
    out = {}
    for k, o in enumerate(orbital_set.orbitals):
        item = found.get(orbital_number(orbital_set, k))
        if item is not None and abs(item[0] - o.energy) < tolerance:
            out[k] = item[1]
    return out


def field_cube(quiet, orbital_set, what='orbital', index=None, step=0.15, spin=False, progress=None):
    """The grid of an orbital, of ρ or of the spin density: from Multiwfn when quiet = (program, file, cores)
    is given — its errors are said, not hidden —, from our own code only without Multiwfn or without a file it reads
    (Multiwfn replaces our calculation wherever it can do it); a cancel goes through as InterruptedError."""
    from modules.spectrum.analysis.orbitals import density_cube, orbital_cube

    if quiet is not None:
        program, path, cores = quiet
        kind = 'orbital' if what == 'orbital' else ('spin' if spin else 'density')
        number = orbital_number(orbital_set, index) if kind == 'orbital' else None
        return run_grid(program, path, kind, number, grid_for_step(step), cores, progress)
    if what == 'orbital':
        return orbital_cube(orbital_set, index, step=step)
    return density_cube(orbital_set, spin, step=step, progress=progress)


# -- a function along a line and in a plane -----------------------------------------------------------------
LINE_FUNCTIONS = dict(FUNCTIONS, sign='15')  # + sign(λ₂)ρ; the orbitals (4) need an index — not offered here


def read_line(text):
    import numpy as np

    rows = [line.split() for line in text.split('\n') if len(line.split()) == 5]
    try:
        data = np.array([[float(v) for v in row] for row in rows])
    except ValueError:
        raise ValueError(tr('Неполный файл профиля.')) from None
    if data.shape[0] < 2:
        raise ValueError(tr('Неполный файл профиля.'))
    return {'points': data[:, :3], 'x': data[:, 3], 'values': data[:, 4]}


def read_plane(text):
    import numpy as np

    rows = [line.split() for line in text.split('\n') if len(line.split()) == 6]
    try:
        data = np.array([[float(v) for v in row] for row in rows])
    except ValueError:
        raise ValueError(tr('Неполный файл карты.')) from None
    if len(data) < 4:
        raise ValueError(tr('Неполный файл карты.'))
    v = np.unique(np.round(data[:, 4], 6))
    n2 = len(v)
    n1 = len(data) // n2
    if n1 * n2 != len(data):
        raise ValueError(tr('Неполный файл карты.'))
    grid = data.reshape(n1, n2, 6)
    return {'points': grid[:, :, :3], 'u': grid[:, 0, 3], 'v': grid[0, :, 4], 'values': grid[:, :, 5]}


def run_line(program, path, name, atoms, cores=1, step=None, timeout=600):
    if name not in LINE_FUNCTIONS or len(atoms) != 2:
        raise ValueError(name)
    i, j = (int(a) + 1 for a in atoms)
    text, kept = _run(program, path, ('3', LINE_FUNCTIONS[name], '1', f'{i},{j}', '2', '0', 'q', 'q'), cores, step,
                      timeout, keep=('line.txt',))
    if 'line.txt' not in kept:
        raise ValueError(tr('Multiwfn не записал профиль. Конец его вывода:') + '\n' + _tail(text))
    found = read_line(kept['line.txt'])
    found.update(text=text, version=version(text), raw=kept['line.txt'])
    return found


def run_plane(program, path, name, atoms, size=100, cores=1, step=None, timeout=900):
    if name not in LINE_FUNCTIONS or len(atoms) != 3:
        raise ValueError(name)
    i, j, k = (int(a) + 1 for a in atoms)
    n = max(20, min(400, int(size)))
    answers = ('4', LINE_FUNCTIONS[name], '1', f'{n},{n}', '4', f'{i},{j},{k}', '-6', '-5', 'q', 'q')
    text, kept = _run(program, path, answers, cores, step, timeout, keep=('plane.txt',))
    if 'plane.txt' not in kept:
        raise ValueError(tr('Multiwfn не записал карту. Конец его вывода:') + '\n' + _tail(text))
    found = read_plane(kept['plane.txt'])
    found.update(text=text, version=version(text))
    return found


# -- excited states -----------------------------------------------------------------------------------------
# 18 (electron excitation analysis) → 1 (hole and electron) → the output with the excitations (ORCA, Gaussian) → the
# state → 1 (analyse) → grid: the indices; 18 → 4 (Δr) → the output → «» (all states)
_INDEX = {
    'sr': r'Sr index \(integral of Sr function\):\s*(-?\d+\.\d+)',
    'sm': r'Sm index \(integral of Sm function\):\s*(-?\d+\.\d+)',
    'd': r'D index:\s*(-?\d+\.\d+)\s*Angstrom',
    'h': r'H index:\s*(-?\d+\.\d+)\s*Angstrom',
    't': r't index:\s*(-?\d+\.\d+)\s*Angstrom',
    'hdi': r'Hole delocalization index \(HDI\):\s*(-?\d+\.\d+)',
    'edi': r'Electron delocalization index \(EDI\):\s*(-?\d+\.\d+)',
    'energy': r'Excitation energy of this state:\s*(-?\d+\.\d+)\s*eV',
    'hole': r'Integral of hole:\s*(-?\d+\.\d+)',
    'electron': r'Integral of electron:\s*(-?\d+\.\d+)',
}


def parse_hole_electron(text):
    """{'sr', 'sm', 'd' Å, 'h' Å, 't' Å, 'hdi', 'edi', 'energy' eV, 'hole', 'electron'} of the last analysis printed."""
    found = {}
    for key, pattern in _INDEX.items():
        matches = re.findall(pattern, text)
        if matches:
            found[key] = float(matches[-1])
    return found


def parse_delta_r(text):
    """{state: Δr Å} of «Excited state k: Delta_r = … Bohr, … Angstrom»."""
    return {int(m.group(1)): float(m.group(2)) for m in
            re.finditer(r'Excited state\s+(\d+):\s*Delta_r\s*=\s*-?\d+\.\d+\s*Bohr,\s*(-?\d+\.\d+)\s*Angstrom', text)}


def _with_output(path, output):
    """The input of an excitation analysis: the wavefunction and the output with the excitations, under ASCII names."""
    name = wavefunction_name(path)

    def write(folder):
        shutil.copyfile(path, folder / name)
        shutil.copyfile(output, folder / ('excited' + (Path(output).suffix.lower() or '.out')))
        return name

    stamps = (_stamp(path), _stamp(output))
    write.key = stamps if None not in stamps else None
    return write, 'excited' + (Path(output).suffix.lower() or '.out')


# an ORCA output of singlets and triplets (%tddft triplets true) makes Multiwfn 3.8 ask «Load which kind of excited
# states? 1: Singlet 3: Triplet» once it has read it, and number the states within that kind (as ORCA does) — kind
# '1' or '3' answers it; None — an output of one kind, no question
def run_hole_electron(program, path, output, state, grid='low', cores=1, step=None, timeout=1800, kind=None):
    """The indices of the hole and the electron of one excited state (its number in the output, within its kind)."""
    write, excited = _with_output(path, output)
    answers = ('18', '1', excited, *((kind,) if kind else ()), str(int(state)), '1', GRIDS[grid], '0', '0', '0', 'q', 'q')
    text, _ = _run(program, write, answers, cores, step, timeout)
    found = parse_hole_electron(text)
    if 'd' not in found:
        raise ValueError(tr('Анализ возбуждения не напечатан. Конец вывода Multiwfn:') + '\n' + _tail(text))
    return found, text, version(text)


def run_delta_r(program, path, output, cores=1, step=None, timeout=1800, states=None, kind=None):
    """Δr (Å) of every excited state of the output: {state: Δr}. «» (Enter) — all the states; Multiwfn asks about the
    orbital pairs (y/n) only when there is a single state (states=1)."""
    write, excited = _with_output(path, output)
    answers = ('18', '4', excited, *((kind,) if kind else ()), '', *(('n',) if states == 1 else ()), '0', 'q', 'q')
    text, _ = _run(program, write, answers, cores, step, timeout)
    found = parse_delta_r(text)
    if not found:
        raise ValueError(tr('Δr не напечатан. Конец вывода Multiwfn:') + '\n' + _tail(text))
    return found, text


HOLE_ELECTRON_CUBES = ('10', '1', '11', '1')  # the hole and the electron to hole.cub, electron.cub; both ask the kind
# of the distribution — 1, «local + cross term» (checked on Multiwfn 2026.7.15)


def run_hole_electron_cubes(program, path, output, state, grid='low', cores=1, step=None, timeout=1800, kind=None):
    """(hole Cube, electron Cube, indices) of one excited state."""
    from modules.spectrum.readers.cube import read_cube

    write, excited = _with_output(path, output)
    answers = ('18', '1', excited, *((kind,) if kind else ()), str(int(state)), '1', GRIDS[grid], *HOLE_ELECTRON_CUBES,
               '0', '0', '0', 'q', 'q')
    text, kept = _run(program, write, answers, cores, step, timeout, keep=('hole.cub', 'electron.cub'))
    if set(kept) != {'hole.cub', 'electron.cub'}:
        raise ValueError(tr('Multiwfn не записал сетки дырки и электрона. Конец его вывода:') + '\n' + _tail(text))
    return read_cube(kept['hole.cub']), read_cube(kept['electron.cub']), parse_hole_electron(text)

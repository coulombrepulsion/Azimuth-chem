"""Record the answers of Multiwfn on the wave function of a crystal from CP2K:
the Molden file of the end of the run with [Cell] and [Nval] (readers.cp2k.for_multiwfn) — how Multiwfn reads it (the
cell, the electrons, the effective charges), its menus of populations and of the topology, and the answers the program
gives for a molecule (multiwfn.CHARGES, multiwfn.TOPOLOGY) — whether they lead through for a periodic system too. The
outputs become the oracles of the next step (tests/data/multiwfn/crystal_*.txt).

Run from the folder of the program: .venv/bin/python tools/record_multiwfn_crystal.py [the folder of a CP2K run]
[--round2 | --round3] Without a folder — the CELL_OPT of CsCl of the tests (tests/data/cp2k/cscl_cellopt). Multiwfn is
found as in the program. Each run is a separate Multiwfn with a time limit; a run whose answers do not lead out of the
menus stops at the limit — its output still shows where it went wrong.
"""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.spectrum.readers import cp2k  # noqa: E402
from modules.spectrum.wavefunction import multiwfn, multiwfn_populations  # noqa: E402

OUT = ROOT / 'tests' / 'data' / 'multiwfn'
LIMIT = 400_000


KEPT = ('CP ', 'Connected atoms', 'Corresponding nucleus', 'Position (', 'Density of all electrons',
        'Lagrangian kinetic energy G(r):', 'Potential energy density', 'Energy density E(r)', 'Laplacian of electron density:',
        'Eigenvalues of Hessian', 'Ellipticity')


def kept_text(path):
    """A file of Multiwfn as the oracle keeps it: CPprop.txt whole (all the points — the first round cut it at 400 000
    characters, 122 points of 739), but only the lines that multiwfn.parse_cps reads; the others cut at LIMIT."""
    text = path.read_text(encoding='utf-8', errors='replace')
    if path.name == 'CPprop.txt':
        return '\n'.join(line for line in text.splitlines() if line.strip().startswith(KEPT) or line.lstrip().startswith('---'))
    return text[:LIMIT]


def run(program, source, answers, name, timeout=300):
    work = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-'))
    target = work / 'input.molden'
    shutil.copyfile(source, target)
    text = '\n'.join(multiwfn.windows_answers(program, work, answers)) + '\n'
    try:
        done = subprocess.run(multiwfn.command(program, target.name, 4), input=text, capture_output=True, text=True,
                              encoding='utf-8', errors='replace', cwd=work, timeout=timeout)
        output = done.stdout + ('\n--- stderr ---\n' + done.stderr if done.stderr.strip() else '')
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\n--- timeout: the answers did not lead out of the menus ---'
    if len(output) > LIMIT:
        output = output[:LIMIT // 2] + '\n\n--- … cut … ---\n\n' + output[-LIMIT // 2:]
    (work / 'settings.ini').unlink(missing_ok=True)
    extra = {p.name: kept_text(p) for p in work.iterdir()
             if p.is_file() and p.suffix.lower() in ('.txt', '.chg') and p.name != target.name}
    shutil.rmtree(work, ignore_errors=True)
    path = OUT / f'crystal_{name}.txt'
    path.write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    for file, content in extra.items():
        (OUT / f'crystal_{name}__{file}').write_text(content, encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-6:])
    print(f'\n=== {name}: {path.relative_to(ROOT)} ({len(output)} знаков)\n{tail}', flush=True)


def main():
    program = multiwfn.find()
    if program is None:
        sys.exit('Multiwfn не найден')
    print('Multiwfn:', program)
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    given = Path(args[0]).expanduser() if args else ROOT / 'tests' / 'data' / 'cp2k' / 'cscl_cellopt'
    work = Path(tempfile.mkdtemp(prefix='azimuth-cp2k-'))
    for item in given.iterdir():  # the folder of the run is not written into
        if item.is_file() and (item.suffix in ('.molden', '.cell', '.inp', '.out')):
            shutil.copyfile(item, work / item.name)
    source, why = cp2k.for_multiwfn(work)
    if source is None:
        sys.exit('Файл для Multiwfn не подготовлен: ' + (why or 'нет файлов .molden'))
    print('Волновая функция:', cp2k.molden_files(work)[-1].name, '→', source.name)
    tag = '' if not args else '_' + given.name.replace(' ', '_')[:40]
    run(program, source, ['q'], 'load' + tag, timeout=120)  # what it says on loading: the cell, the electrons
    run(program, source, ['7', '0', 'q'], 'menu7' + tag, timeout=120)
    run(program, source, ['2', '-10', 'q'], 'menu2' + tag, timeout=120)
    if '--round3' in sys.argv:  # the topology whole; Hirshfeld and CM5 of a periodic wave function: 7 → 1 (16) → the
        # integration «1» (even grids, the one for valence electrons) → the grid spacing, bohr; then what it asks next
        run(program, source, list(multiwfn.TOPOLOGY), 'topology' + tag, timeout=3600)
        for name, menu in (('hirshfeld', '1'), ('cm5', '16')):
            run(program, source, ['7', menu, '1', '0.4', 'n', '0', 'q'], f'{name}_a' + tag, timeout=1800)
            run(program, source, ['7', menu, '1', '0.4', '1', 'n', '0', 'q'], f'{name}_b' + tag, timeout=1800)
        run(program, source, ['17', '1', '1', '11'], 'basins_menu' + tag, timeout=120)
        shutil.rmtree(work, ignore_errors=True)
        print('\nГотово: tests/data/multiwfn/crystal_*.txt')
        return None
    if '--round2' not in sys.argv:
        run(program, source, list(multiwfn.CHARGES), 'charges' + tag, timeout=900)  # ADCH: «does not support periodic»
        run(program, source, list(multiwfn.TOPOLOGY), 'topology' + tag, timeout=1800)  # QTAIM critical points
    # the second round (the first one, the topology leads through, ADCH (7 → 11) is not for a periodic
    # wave function): Hirshfeld and CM5 with the built-in free atoms, the AIM basins, the menu and the grid of NCI
    run(program, source, ['7', '1', '1', 'n', '0', 'q'], 'hirshfeld' + tag, timeout=1800)
    run(program, source, ['7', '16', '1', 'n', '0', 'q'], 'cm5' + tag, timeout=1800)
    run(program, source, list(multiwfn_populations.basin_answers(False)), 'basins' + tag, timeout=3600)
    run(program, source, ['20', '1', 'q'], 'menu20' + tag, timeout=120)
    run(program, source, ['20', '1', '1', '3', '0', '0', 'q', 'q'], 'nci' + tag, timeout=3600)
    shutil.rmtree(work, ignore_errors=True)
    print('\nГотово: tests/data/multiwfn/crystal_*.txt')


if __name__ == '__main__':
    main()

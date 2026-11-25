"""Record the answers of Multiwfn for IGMH: the independent gradient model based on the Hirshfeld partition
(Lu & Chen, J. Comput. Chem. 43, 539 (2022)) — main menu 20 → 11, the fragments, the grid, «3» (the cubes sl2r.cub and
dg_inter.cub), «6» (the atomic and atom-pair δG indices, atmdg.txt) with its integration grid and «n» (no atmdg.pdb).
The recipe follows the source of Multiwfn (visweak.f90, subroutine IGM); this run checks it on the installed version.

ORCA computes the S22 water dimer and benzene···methane (a C–H pointing at the ring) with B3LYP-D3(BJ)/def2-SVP at the
given geometries; orca_2mkl writes their Molden files. The outputs, atmdg.txt and the cubes (gzip) go to
tests/data/multiwfn/igmh_<system>_*, the oracles of modules/spectrum/wavefunction/multiwfn_igmh.py.

Run from the folder of the program: .venv/bin/python tools/record_multiwfn_igmh.py [--orca /path/to/orca]
A run that does not leave the menus is cut at the time limit and recorded as it is («--- timeout …»).
"""

import argparse
import gzip
import math
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.sextant import runner  # noqa: E402
from modules.spectrum.wavefunction import multiwfn  # noqa: E402

OUT = ROOT / 'tests' / 'data' / 'multiwfn'
METHOD = '! B3LYP D3BJ def2-SVP TightSCF'
DIMER = [('O', -1.551007, -0.114520, 0.0), ('H', -1.934259, 0.762503, 0.0), ('H', -0.599677, 0.040712, 0.0),
         ('O', 1.350625, 0.111469, 0.0), ('H', 1.680398, -0.373741, -0.758561), ('H', 1.680398, -0.373741, 0.758561)]


def benzene_methane():
    ring = [('C', 1.39 * math.cos(math.radians(a)), 1.39 * math.sin(math.radians(a)), 0.0) for a in range(0, 360, 60)]
    ring += [('H', 2.47 * math.cos(math.radians(a)), 2.47 * math.sin(math.radians(a)), 0.0) for a in range(0, 360, 60)]
    methane = [('C', 0.0, 0.0, 3.59), ('H', 0.0, 0.0, 2.50)]
    methane += [('H', 1.028 * math.cos(math.radians(a)), 1.028 * math.sin(math.radians(a)), 3.953) for a in (0, 120, 240)]
    return ring + methane


def systems():
    """(name, atoms, fragments as Multiwfn reads them)."""
    return [('dimer', DIMER, ('1-3', '4-6')), ('benzene_methane', benzene_methane(), ('1-12', '13-17'))]


def orca_job(orca, folder, name, atoms):
    folder.mkdir(parents=True, exist_ok=True)
    rows = '\n'.join(f'{s:2s} {x:12.6f} {y:12.6f} {z:12.6f}' for s, x, y, z in atoms)
    (folder / f'{name}.inp').write_text(f'{METHOD}\n* xyz 0 1\n{rows}\n*\n', encoding='utf-8')
    env = runner.environment(orca, 'orca', 1)
    with open(folder / f'{name}.out', 'w', encoding='utf-8') as out:
        subprocess.run([str(orca), f'{name}.inp'], cwd=folder, stdout=out, stderr=subprocess.STDOUT, env=env, check=False)
    tool = Path(orca).with_name('orca_2mkl' + ('.exe' if os.name == 'nt' else ''))
    subprocess.run([str(tool), name, '-molden'], cwd=folder, capture_output=True, env=env, check=False)
    molden = folder / f'{name}.molden.input'
    text = (folder / f'{name}.out').read_text(encoding='utf-8', errors='replace')
    if not molden.is_file() or 'ORCA TERMINATED NORMALLY' not in text:
        sys.exit(f'ORCA не досчитала {name}: см. {folder / (name + ".out")}')
    return molden


def run(program, work, answers, name, timeout=900):
    text = '\n'.join(multiwfn.windows_answers(program, work, answers)) + '\n'
    try:
        done = subprocess.run([str(program), 'input.molden'], input=text, capture_output=True, text=True,
                              encoding='utf-8', cwd=work, timeout=timeout, errors='replace',
                              env=dict(os.environ, OMP_STACKSIZE='200M'))
        output = done.stdout + ('\n--- stderr ---\n' + done.stderr if done.stderr.strip() else '')
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\n--- timeout: the answers did not lead out of the menus ---'
    (OUT / f'igmh_{name}_output.txt').write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    for kept in ('atmdg.txt', 'IBSIW.txt'):
        if (work / kept).is_file():
            shutil.copyfile(work / kept, OUT / f'igmh_{name}_{kept}')
    for cube in ('sl2r.cub', 'dg_inter.cub'):
        if (work / cube).is_file():
            (OUT / f'igmh_{name}_{cube}.gz').write_bytes(gzip.compress((work / cube).read_bytes()))
    tail = '\n'.join(output.strip().splitlines()[-12:])
    print(f'\n=== {name}: {len(output)} знаков; atmdg.txt: {(work / "atmdg.txt").is_file()}\n{tail}', flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--orca', help='файл программы orca (по умолчанию — найденная, как в Секстанте)')
    args = parser.parse_args()
    program = multiwfn.find()
    if program is None:
        sys.exit('Multiwfn не найден')
    orca = runner.find_program('orca', args.orca)
    if orca is None:
        sys.exit('ORCA не найдена: укажите --orca /путь/к/orca')
    print('Multiwfn:', program, '\nORCA:', orca, flush=True)
    for name, atoms, (one, two) in systems():
        work = Path(tempfile.mkdtemp(prefix=f'azimuth-igmh-{name}-'))
        molden = orca_job(orca, work / 'orca', name, atoms)
        shutil.copyfile(molden, work / 'input.molden')
        (OUT / f'igmh_{name}.molden.gz').write_bytes(gzip.compress(molden.read_bytes()))
        # 20 → 11 (IGMH) → 2 fragments → their atoms → grid 1 (low) → 3 (cubes) → 6 (δG indices) → 2 (high quality
        # integration) → n (no atmdg.pdb) → 0 (the post-processing menu) → 0 (menu 20) → q
        run(program, work, ['20', '11', '2', one, two, '1', '3', '6', '2', 'n', '0', '0', 'q'], name)
        shutil.rmtree(work, ignore_errors=True)
    print('\nГотово: tests/data/multiwfn/igmh_*')


if __name__ == '__main__':
    main()

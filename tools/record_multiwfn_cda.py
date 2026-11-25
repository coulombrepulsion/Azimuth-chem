"""Record the answers of Multiwfn for the charge decomposition analysis CDA of Dapprich and Frenking (docs/plans/ROADMAP.md,
beta item 9): ORCA computes a donor–acceptor complex and its two fragments at the geometry of the complex (the atoms of
fragment 1 first, then those of fragment 2 — the order Multiwfn expects), orca_2mkl writes their Molden files, and
Multiwfn reads the complex, then main menu 16 (CDA) → the number of fragments → the file of each fragment → its menu.
The outputs become the oracles of the parser (tests/data/multiwfn/cda_*.txt) and the Molden files the data of the tests
(tests/data/multiwfn/cda_<system>_<part>.molden.gz).

Run from the folder of the program:  .venv/bin/python tools/record_multiwfn_cda.py [--orca /path/to/orca]
Each run of Multiwfn has its own answers and a time limit; a run that does not leave the menus is cut at the limit and
recorded as it is («--- timeout …»), so the next round knows where it stopped. The ORCA jobs take a minute or two.
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
LIMIT = 400_000
METHOD = '! B3LYP def2-SVP TightSCF'


def pyramid(centre, axis_sign, bond, angle, symbol):
    """Three atoms symbol at bond Å from centre (x, y, z), at angle° to the +z axis (or −z), staggered by 60° steps."""
    x0, y0, z0 = centre
    theta = math.radians(angle)
    out = []
    for k in range(3):
        phi = math.radians(120 * k + (60 if axis_sign < 0 else 0))
        out.append((symbol, x0 + bond * math.sin(theta) * math.cos(phi), y0 + bond * math.sin(theta) * math.sin(phi),
                    z0 + axis_sign * bond * math.cos(theta)))
    return out


def systems():
    """(name, fragment 1 (donor) atoms, fragment 2 (acceptor) atoms): ammonia borane (B–N 1.66 Å) and borane carbonyl
    (B–C 1.53 Å, C–O 1.13 Å) — textbook donor–acceptor pairs; the geometries are rounded literature values, not optimized
    (CDA needs only one geometry for all three)."""
    nh3 = [('N', 0.0, 0.0, 0.0)] + pyramid((0, 0, 0), -1, 1.02, 180 - 110.5, 'H')
    bh3_n = [('B', 0.0, 0.0, 1.66)] + pyramid((0, 0, 1.66), +1, 1.21, 180 - 104.7, 'H')
    co = [('C', 0.0, 0.0, 0.0), ('O', 0.0, 0.0, -1.13)]
    bh3_c = [('B', 0.0, 0.0, 1.53)] + pyramid((0, 0, 1.53), +1, 1.20, 180 - 104.0, 'H')
    return [('nh3bh3', nh3, bh3_n), ('cobh3', co, bh3_c)]


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


def run(program, work, answers, name, timeout=600):
    # the build for Windows waits for ENTER without settings.ini — multiwfn.windows_answers
    text = '\n'.join(multiwfn.windows_answers(program, work, answers)) + '\n'
    try:
        done = subprocess.run([str(program), 'complex.molden'], input=text, capture_output=True, text=True,
                              encoding='utf-8', cwd=work, timeout=timeout, errors='replace')
        output = done.stdout + ('\n--- stderr ---\n' + done.stderr if done.stderr.strip() else '')
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\n--- timeout: the answers did not lead out of the menus ---'
    if len(output) > LIMIT:
        output = output[:LIMIT // 2] + '\n\n--- … cut … ---\n\n' + output[-LIMIT // 2:]
    path = OUT / f'cda_{name}.txt'
    path.write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-10:])
    print(f'\n=== {name}: {path.relative_to(ROOT)} ({len(output)} знаков)\n{tail}', flush=True)


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
    for system, donor, acceptor in systems():
        work = Path(tempfile.mkdtemp(prefix=f'azimuth-cda-{system}-'))
        files = {}
        for part, atoms in (('complex', donor + acceptor), ('frag1', donor), ('frag2', acceptor)):
            molden = orca_job(orca, work / part, part, atoms)
            files[part] = work / f'{part}.molden'
            shutil.copyfile(molden, files[part])
            (OUT / f'cda_{system}_{part}.molden.gz').write_bytes(gzip.compress(molden.read_bytes()))
            out = (work / part / f'{part}.out').read_text(encoding='utf-8', errors='replace')
            energy = [line for line in out.splitlines() if 'FINAL SINGLE POINT ENERGY' in line]
            print(f'{system} {part}: {energy[-1].strip() if energy else "?"}', flush=True)
        f1, f2 = str(files['frag1']), str(files['frag2'])
        # the way found by the first round: Multiwfn prints the result as soon as the fragments
        # are read, then its menu — «-1» back to the main menu, «q» (a «0» there prints the result again, and the
        # first records ended with a Fortran error on the «q» that followed it)
        run(program, work, ['16', '2', f1, f2, '-1', 'q'], f'{system}_cda')
        shutil.rmtree(work, ignore_errors=True)
    print('\nГотово: tests/data/multiwfn/cda_*')


if __name__ == '__main__':
    main()

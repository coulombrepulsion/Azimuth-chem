"""Record the answers of Multiwfn for the fuzzy atomic space analysis: localization and delocalization indices
(LI, DI) and the aromaticity indices PDI, FLU, MCI — the outputs become the oracles of the parsers
(tests/data/multiwfn).

Run from the folder of the program: .venv/bin/python tools/record_multiwfn_fuzzy.py [--rings] [--rings2] [--homa]
[--homa2] Multiwfn is found as in the program. Each run is a separate Multiwfn with its own answers and a 5-minute
limit; the outputs are written to tests/data/multiwfn/fuzzy_*.txt (the menus as Multiwfn printed them, for checking the
answers).
"""

import subprocess
import sys
import tempfile
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.spectrum.wavefunction import multiwfn  # noqa: E402
from modules.spectrum.readers.orbital_files import read_orbitals  # noqa: E402

DATA = ROOT / 'tests' / 'data'
OUT = DATA / 'multiwfn'


def six_ring(molecule):
    """The first six-membered carbon ring (1-based indices in ring order) by distances 1.2–1.6 Å."""
    import math

    carbons = [k for k, a in enumerate(molecule.atoms) if a.symbol == 'C']
    near = {k: [j for j in carbons if j != k and 1.2 < math.dist(molecule.atoms[k].position, molecule.atoms[j].position) < 1.6]
            for k in carbons}

    def walk(path):
        if len(path) == 6:
            return path if path[0] in near[path[-1]] else None
        for j in near[path[-1]]:
            if j not in path:
                found = walk(path + [j])
                if found:
                    return found
        return None

    for start in carbons:
        ring = walk([start])
        if ring:
            return [k + 1 for k in ring]
    return None


def run(program, source, answers, name):
    work = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-'))
    target = work / ('input' + source.suffix.lower())
    shutil.copyfile(source, target)
    # the build for Windows waits for ENTER without settings.ini — multiwfn.windows_answers
    text = '\n'.join(multiwfn.windows_answers(program, work, answers)) + '\n'
    try:
        done = subprocess.run([str(program), target.name], input=text, capture_output=True, text=True,
                              encoding='utf-8', cwd=work,
                              timeout=300, errors='replace')
        output = done.stdout + ('\n--- stderr ---\n' + done.stderr if done.stderr.strip() else '')
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\n--- timeout: the answers did not lead out of the menus ---'
    (work / 'settings.ini').unlink(missing_ok=True)  # copied by windows_answers, not written by Multiwfn
    extra = {p.name: p.read_text(encoding='utf-8', errors='replace') for p in work.iterdir()
             if p.is_file() and p.suffix.lower() == '.txt'}
    shutil.rmtree(work, ignore_errors=True)
    path = OUT / f'fuzzy_{name}.txt'
    path.write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    for file, content in extra.items():
        (OUT / f'fuzzy_{name}__{file}').write_text(content, encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-6:])
    print(f'\n=== {name}: {path.relative_to(ROOT)} ({len(output)} знаков)\n{tail}', flush=True)


def main():
    program = multiwfn.find()
    if program is None:
        sys.exit('Multiwfn не найден')
    print('Multiwfn:', program)
    water = DATA / 'orbitals' / 'water_mp2_g16.fchk'
    metal = DATA / 'orbitals' / 'Mo4OCl4-sp_g16.fchk'
    ring_file = DATA / 'orbitals' / 'molden5.7_dvb_un_sp.molden'
    ring = six_ring(read_orbitals(ring_file.read_text(encoding='utf-8', errors='replace')).molecule)
    ring_text = ','.join(map(str, ring))
    print('кольцо дивинилбензола (с 1):', ring_text)
    # the main menu 15 (fuzzy atomic space), its item 4 (LI and DI); 'n' — no file; then out of the menus
    if not {'--rings', '--rings2', '--homa', '--homa2'} & set(sys.argv):  # «--rings»: only the aromaticity of benzaldehyde (the rest was recorded first)
        run(program, water, ['15', '4', 'n', '0', 'q'], 'water_lidi')
        run(program, metal, ['15', '4', 'n', '0', 'q'], 'MoOCl4_lidi')
        run(program, ring_file, ['15', '4', 'n', '0', 'q'], 'dvb_lidi')  # open shell: α, β and the total
    # the aromaticity of the six-membered ring: PDI (5), FLU (6), MCI (11) — the ring atoms asked for after the item
    # PDI, FLU and MCI are for closed shells only (Multiwfn refused the cation of divinylbenzene): benzaldehyde
    # CAM-B3LYP/def2-SVPD of the user (ORCA, orca_2mkl), the ring C3–C8 in its order
    import gzip

    closed = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-')) / 'benzaldehyde.molden'
    closed.write_bytes(gzip.decompress((OUT / 'benzaldehyde_cam-b3lyp_def2-svpd.molden.gz').read_bytes()))
    benzene = six_ring(read_orbitals(closed.read_text(encoding='utf-8', errors='replace')).molecule)
    benzene_text = ','.join(map(str, benzene))
    print('кольцо бензальдегида (с 1):', benzene_text)
    if not {'--rings2', '--homa', '--homa2'} & set(sys.argv):
        run(program, closed, ['15', '4', 'n', '0', 'q'], 'benzaldehyde_lidi')
        run(program, closed, ['15', '5', benzene_text, '0', '0', '0', 'q'], 'benzaldehyde_pdi')
        run(program, closed, ['15', '6', benzene_text, '0', '0', '0', 'q'], 'benzaldehyde_flu')
        run(program, closed, ['15', '11', benzene_text, '0', '0', '0', 'q'], 'benzaldehyde_mci')
    # the recipe of the program: PDI, FLU and MCI in one run — each item asks for rings until «q» (the first records:
    # a «0» there was taken as a ring and Multiwfn fell); the menu 25 (delocalization and aromaticity) for HOMA
    if not {'--homa', '--homa2'} & set(sys.argv):
        run(program, closed, ['15', '5', benzene_text, 'q', '6', benzene_text, 'q', '11', benzene_text, 'q', '0', 'q'],
            'benzaldehyde_rings')
        run(program, closed, ['25', '0', 'q'], 'menu25')
    # HOMA and Bird of Multiwfn (menu 25 → 6) for the check of our HOMA: the ring, then «q»
    if '--homa2' not in sys.argv:
        run(program, closed, ['25', '6', benzene_text, 'q', '0', 'q'], 'benzaldehyde_homa')  # printed the parameters
    # 0 — «Start calculation for HOMA!», the ring, «q» back, «-1» out of HOMA / Bird, «0» out of menu 25
    run(program, closed, ['25', '6', '0', benzene_text, 'q', '-1', '0', 'q'], 'benzaldehyde_homa_value')
    print('\nГотово: tests/data/multiwfn/fuzzy_*.txt')


if __name__ == '__main__':
    main()

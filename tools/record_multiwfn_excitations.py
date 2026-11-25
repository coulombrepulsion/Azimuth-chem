"""Record the answers of Multiwfn for the charge transfer of the excited states (docs/plans/ROADMAP.md, beta item 6):
main menu 18 → 8 (IFCT, interfragment charge transfer) and 18 → 2 (the atom / fragment transition matrix as a heat map)
on the TD-DFT of benzaldehyde of the user (ORCA 6, CAM-B3LYP/def2-SVPD, the Molden of orca_2mkl and the output) — the
outputs and the files written become the oracles of the parsers (tests/data/multiwfn/exc_*.txt, exc_*__<file>).

Run from the folder of the program: .venv/bin/python tools/record_multiwfn_excitations.py [--round2]
The fragments: the formyl group CHO (O1, C2, H9) and the ring (C3–C8, H10–H14).
"""

import gzip
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from modules.spectrum.wavefunction import multiwfn  # noqa: E402

OUT = ROOT / 'tests' / 'data' / 'multiwfn'
LIMIT = 400_000
CHO, RING = '1,2,9', '3-8,10-14'


def run(program, wavefunction, excited, answers, name, timeout=600):
    work = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-'))
    shutil.copyfile(wavefunction, work / 'input.molden')
    shutil.copyfile(excited, work / 'excited.out')
    # the build for Windows waits for ENTER without settings.ini — multiwfn.windows_answers
    text = '\n'.join(multiwfn.windows_answers(program, work, answers)) + '\n'
    try:
        done = subprocess.run([str(program), 'input.molden'], input=text, capture_output=True, text=True,
                              encoding='utf-8', cwd=work, timeout=timeout, errors='replace')
        output = done.stdout + ('\n--- stderr ---\n' + done.stderr if done.stderr.strip() else '')
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\n--- timeout: the answers did not lead out of the menus ---'
    if len(output) > LIMIT:
        output = output[:LIMIT // 2] + '\n\n--- … cut … ---\n\n' + output[-LIMIT // 2:]
    (work / 'settings.ini').unlink(missing_ok=True)  # copied by windows_answers, not written by Multiwfn
    written = sorted(p for p in work.iterdir() if p.is_file() and p.name not in ('input.molden', 'excited.out'))
    output += '\n--- files written: ' + ', '.join(f'{p.name} ({p.stat().st_size} bytes)' for p in written) + '\n'
    for p in written:
        if p.stat().st_size < 5_000_000 and p.suffix.lower() in ('.txt', '.dat', '.csv'):
            (OUT / f'exc_{name}__{p.name}').write_text(p.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    shutil.rmtree(work, ignore_errors=True)
    path = OUT / f'exc_{name}.txt'
    path.write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-6:])
    print(f'\n=== {name}: {path.relative_to(ROOT)} ({len(output)} знаков)\n{tail}', flush=True)


def main():
    program = multiwfn.find()
    if program is None:
        sys.exit('Multiwfn не найден')
    print('Multiwfn:', program)
    molden = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-')) / 'benzaldehyde.molden'
    molden.write_bytes(gzip.decompress((OUT / 'benzaldehyde_cam-b3lyp_def2-svpd.molden.gz').read_bytes()))
    excited = OUT / 'benzaldehyde_cam-b3lyp_orca.out'
    if '--round2' in sys.argv:  # the answers corrected by the first record
        # IFCT asks first the partition of the hole and the electron: 2 — Hirshfeld (def2-SVPD has diffuse functions)
        run(program, molden, excited, ['18', '8', '2', 'excited.out', '1', '2', CHO, RING, '0', '0', 'q'], 'ifct2_s1')
        run(program, molden, excited, ['18', '8', '2', 'excited.out', '3', '2', CHO, RING, '0', '0', 'q'], 'ifct2_s3')
        # the heat map: no symmetrization (0), way 1 (the sum of the squares of the TDM elements), 4 — with the hydrogens,
        # 3 — the matrix to tmat.txt; then −1 — two fragments, 3 again
        run(program, molden, excited, ['18', '2', 'excited.out', '1', '0', '1', '4', '3', '0', '0', 'q'], 'heatmap2_atoms')
        run(program, molden, excited, ['18', '2', 'excited.out', '1', '0', '1', '-1', '2', CHO, RING, '3', '0', '0', 'q'],
            'heatmap2_fragments')
        print('\nГотово (второй круг): tests/data/multiwfn/exc_*')
        return None
    # IFCT (18 → 8): the file of the excitations, the state (S1), then — as the record will show — the number of
    # fragments and the atoms of each; out of the menus with 0 and q
    run(program, molden, excited, ['18', '8', 'excited.out', '1', '2', CHO, RING, '0', '0', 'q'], 'ifct_s1')
    run(program, molden, excited, ['18', '8', 'excited.out', '3', '2', CHO, RING, '0', '0', 'q'], 'ifct_s3')
    # the heat map (18 → 2): the file, the state, then its own menu (the kind of the matrix) — «0» to see the menu
    run(program, molden, excited, ['18', '2', 'excited.out', '1', '0', '0', '0', 'q'], 'heatmap_menu')
    print('\nГотово: tests/data/multiwfn/exc_*')


if __name__ == '__main__':
    main()

"""Record the answers of Multiwfn for the RESP charges (docs/plans/ROADMAP.md, beta item 7): main menu 7 (population
analysis and atomic charges) → 18 (RESP) — its menu, the standard two-stage fitting and what it asks after it; the
outputs and the files written become the oracles of the parser (tests/data/multiwfn/resp_*.txt, resp_*__<file>).

Run from the folder of the program:  .venv/bin/python tools/record_multiwfn_resp.py
Each run is a separate Multiwfn with its own answers and a time limit; a run that does not leave the menus is cut at
the limit and recorded as it is («--- timeout …»), so the next round knows where it stopped.
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

DATA = ROOT / 'tests' / 'data'
OUT = DATA / 'multiwfn'
LIMIT = 400_000


def run(program, source, answers, name, timeout=600):
    work = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-'))
    target = work / ('input' + ''.join(source.suffixes[-1:]).lower())
    shutil.copyfile(source, target)
    # the build for Windows waits for ENTER without settings.ini — multiwfn.windows_answers
    text = '\n'.join(multiwfn.windows_answers(program, work, answers)) + '\n'
    try:
        done = subprocess.run([str(program), target.name], input=text, capture_output=True, text=True,
                              encoding='utf-8', cwd=work, timeout=timeout, errors='replace')
        output = done.stdout + ('\n--- stderr ---\n' + done.stderr if done.stderr.strip() else '')
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\n--- timeout: the answers did not lead out of the menus ---'
    if len(output) > LIMIT:
        output = output[:LIMIT // 2] + '\n\n--- … cut … ---\n\n' + output[-LIMIT // 2:]
    (work / 'settings.ini').unlink(missing_ok=True)  # copied by windows_answers, not written by Multiwfn
    written = sorted(p for p in work.iterdir() if p.is_file() and p.name != target.name)
    output += '\n--- files written: ' + ', '.join(f'{p.name} ({p.stat().st_size} bytes)' for p in written) + '\n'
    for p in written:  # the charges files (.chg) and other small text files
        if p.stat().st_size < 2_000_000:
            (OUT / f'resp_{name}__{p.name}').write_text(p.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
    shutil.rmtree(work, ignore_errors=True)
    path = OUT / f'resp_{name}.txt'
    path.write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-8:])
    print(f'\n=== {name}: {path.relative_to(ROOT)} ({len(output)} знаков)\n{tail}', flush=True)


def main():
    program = multiwfn.find()
    if program is None:
        sys.exit('Multiwfn не найден')
    print('Multiwfn:', program)
    water = DATA / 'orbitals' / 'water_mp2_g16.fchk'  # Gaussian 16 fchk
    benzaldehyde = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-')) / 'benzaldehyde.molden'  # ORCA Molden, def2-SVPD
    benzaldehyde.write_bytes(gzip.decompress((OUT / 'benzaldehyde_cam-b3lyp_def2-svpd.molden.gz').read_bytes()))

    # the menu of RESP: 7 → 18 shows it; «0» back (if 0 is not the way back, the record shows the list and stops)
    run(program, water, ['7', '18', '0', '0', 'q'], 'menu', timeout=120)
    # the standard two-stage fitting (as the manual names item 1 of that menu); after it — whatever it asks, seen in
    # the record: «n» for a question y/n (a .chg file), then back and out
    run(program, water, ['7', '18', '1', 'n', '0', '0', 'q'], 'water_standard')
    run(program, water, ['7', '18', '1', 'y', '0', '0', 'q'], 'water_standard_chg')
    run(program, benzaldehyde, ['7', '18', '1', 'n', '0', '0', 'q'], 'benzaldehyde_standard', timeout=1800)
    print('\nГотово: tests/data/multiwfn/resp_*')


if __name__ == '__main__':
    main()

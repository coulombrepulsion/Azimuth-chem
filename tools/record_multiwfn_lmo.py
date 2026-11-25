"""Record the answers of Multiwfn for the localized orbitals (docs/plans/ROADMAP.md, beta item 5): main menu 19 (orbital
localization) — the list of methods (−6), the localization of the occupied orbitals (1) with its summary of one- and
two-center LMOs, and the file of the new orbitals it writes; the outputs and the names (and small copies) of the files
written become the oracles of the parser (tests/data/multiwfn/lmo_*.txt, lmo_*__<file>).

Run from the folder of the program: .venv/bin/python tools/record_multiwfn_lmo.py
Multiwfn is found as in the program; each run is a separate Multiwfn with its own answers and a time limit.
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


def run(program, source, answers, name, timeout=300):
    work = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-'))
    target = work / ('input' + source.suffix.lower())
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
    for p in written:  # the new orbitals (gzip) and the small text files, for the parser and the reader of orbitals
        if p.stat().st_size < 20_000_000:
            (OUT / f'lmo_{name}__{p.name}.gz').write_bytes(gzip.compress(p.read_bytes()))
    shutil.rmtree(work, ignore_errors=True)
    path = OUT / f'lmo_{name}.txt'
    path.write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-6:])
    print(f'\n=== {name}: {path.relative_to(ROOT)} ({len(output)} знаков)\n{tail}', flush=True)


def main():
    program = multiwfn.find()
    if program is None:
        sys.exit('Multiwfn не найден')
    print('Multiwfn:', program)
    water = DATA / 'orbitals' / 'water_mp2_g16.fchk'  # Gaussian 16 fchk
    cation = DATA / 'orbitals' / 'molden5.7_dvb_un_sp.molden'  # open shell, ORCA Molden
    closed = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-')) / 'benzaldehyde.molden'  # closed shell, ORCA Molden
    closed.write_bytes(gzip.decompress((OUT / 'benzaldehyde_cam-b3lyp_def2-svpd.molden.gz').read_bytes()))

    if '--more' in sys.argv:  # the other methods by the numbers of the list, and the open shell again
        run(program, water, ['19', '-6', '10', '1', '0', 'q'], 'water_boys')
        run(program, closed, ['19', '-6', '3', '1', '0', 'q'], 'benzaldehyde_pm_becke', timeout=900)
        run(program, closed, ['19', '-6', '10', '1', '0', 'q'], 'benzaldehyde_boys', timeout=900)
        # the composition of the LMOs by Mulliken (−9, its list recorded) instead of Hirshfeld: did Multiwfn fall there?
        run(program, cation, ['19', '-9', '1', '1', '0', 'q'], 'cation_pm_mulliken', timeout=600)
        print('\nГотово (ещё): tests/data/multiwfn/lmo_*')
        return None
    # the list of methods: −6 shows it; «1» — probably the first (the default Pipek–Mezey), then out
    run(program, water, ['19', '-6', '1', '0', 'q'], 'methods', timeout=60)
    # the occupied orbitals localized by the default (Pipek–Mezey, Mulliken): the summary and the new file; then
    # whatever it asks next is seen in the record («0» back, «q»)
    run(program, water, ['19', '1', '0', 'q'], 'water_pm')
    run(program, closed, ['19', '1', '0', 'q'], 'benzaldehyde_pm', timeout=600)
    run(program, cation, ['19', '1', '0', 'q'], 'cation_pm', timeout=600)
    print('\nГотово: tests/data/multiwfn/lmo_*')


if __name__ == '__main__':
    main()

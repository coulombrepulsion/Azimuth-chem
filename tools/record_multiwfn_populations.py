"""Record the answers of Multiwfn for the populations of the beta: Hirshfeld charges and spin populations
(main menu 7) and the charges of the AIM basins (main menu 17); and the menus of the next items of docs/plans/ROADMAP.md
(localized orbitals 19, excitations 18, RESP in 7, conceptual DFT 22, CDA 16) — the outputs become the oracles of the
parsers and the source of the numbers of the menus (tests/data/multiwfn/pop_*.txt).

Run from the folder of the program: .venv/bin/python tools/record_multiwfn_populations.py
Multiwfn is found as in the program. Each run is a separate Multiwfn with its own answers and a time limit; the outputs
are written with the answers on top (the menus as Multiwfn printed them, for checking the answers). A run whose answers
do not lead out of the menus stops at the limit — its output still shows where it went wrong.
"""

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
LIMIT = 400_000  # characters kept of one output (a wrong answer can make Multiwfn repeat its menu forever)


def run(program, source, answers, name, timeout=300):
    work = Path(tempfile.mkdtemp(prefix='azimuth-mwfn-'))
    target = work / ('input' + source.suffix.lower())
    shutil.copyfile(source, target)
    # the build for Windows waits for ENTER without settings.ini — multiwfn.windows_answers
    text = '\n'.join(multiwfn.windows_answers(program, work, answers)) + '\n'
    try:
        done = subprocess.run([str(program), target.name], input=text, capture_output=True, text=True,
                              encoding='utf-8', cwd=work,
                              timeout=timeout, errors='replace')
        output = done.stdout + ('\n--- stderr ---\n' + done.stderr if done.stderr.strip() else '')
    except subprocess.TimeoutExpired as exc:
        output = (exc.stdout or b'').decode('utf-8', 'replace') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
        output += '\n--- timeout: the answers did not lead out of the menus ---'
    if len(output) > LIMIT:
        output = output[:LIMIT // 2] + '\n\n--- … cut … ---\n\n' + output[-LIMIT // 2:]
    (work / 'settings.ini').unlink(missing_ok=True)  # copied by windows_answers, not written by Multiwfn
    extra = {p.name: p.read_text(encoding='utf-8', errors='replace')[:LIMIT] for p in work.iterdir()
             if p.is_file() and p.suffix.lower() in ('.txt', '.chg')}
    shutil.rmtree(work, ignore_errors=True)
    path = OUT / f'pop_{name}.txt'
    path.write_text('answers: ' + ' | '.join(answers) + '\n\n' + output, encoding='utf-8')
    for file, content in extra.items():
        (OUT / f'pop_{name}__{file}').write_text(content, encoding='utf-8')
    tail = '\n'.join(output.strip().splitlines()[-6:])
    print(f'\n=== {name}: {path.relative_to(ROOT)} ({len(output)} знаков)\n{tail}', flush=True)


def main():
    program = multiwfn.find()
    if program is None:
        sys.exit('Multiwfn не найден')
    print('Multiwfn:', program)
    water = DATA / 'orbitals' / 'water_mp2_g16.fchk'  # closed shell (Gaussian 16, MP2)
    cation = DATA / 'orbitals' / 'molden5.7_dvb_un_sp.molden'  # open shell: the UKS cation of divinylbenzene (ORCA)
    metal = DATA / 'orbitals' / 'Mo4OCl4-sp_g16.fchk'  # a complex with an ECP

    if '--round3' in sys.argv:  # 15 → −1 → 3: the Hirshfeld partition of the built-in atomic densities (2 needs .wfn files)
        run(program, cation, ['15', '-1', '3', '1', '5', '0', 'q'], 'cation_hirshfeld3_spin', timeout=600)
        run(program, water, ['15', '-1', '3', '1', '1', '0', 'q'], 'water_hirshfeld3_rho', timeout=600)
        print('\nГотово (третий круг): tests/data/multiwfn/pop_*.txt')
        return None
    if '--round2' in sys.argv:
        return round2(program, water, cation, metal)
    # the menus: 7 (populations and charges), 17 (basins), 15 (fuzzy atomic space), and the next items of the roadmap
    for menu in ('7', '17', '15', '19', '18', '22', '16'):
        run(program, water, [menu, '0', 'q'], f'menu{menu}', timeout=60)

    # Hirshfeld (7 → 1): «1» — the built-in free-atom densities; «n» — no .chg file; then out of the menus
    run(program, water, ['7', '1', '1', 'n', '0', 'q'], 'water_hirshfeld')
    run(program, cation, ['7', '1', '1', 'n', '0', 'q'], 'cation_hirshfeld')  # the spin populations of an open shell?
    run(program, metal, ['7', '1', '1', 'n', '0', 'q'], 'MoOCl4_hirshfeld')

    # the spin density integrated in the Hirshfeld atoms of the fuzzy space (15): the partition chosen first (8 → 2),
    # then 1 — the integral of a function, 5 — the spin density
    run(program, cation, ['15', '8', '2', '1', '5', '0', 'q'], 'cation_fuzzy_spin')

    # AIM basins (17): 1 — generate the basins of 1 (ρ) on 2 (the medium grid); 2 — integrate 1 (ρ) in them
    # (the populations and the charges); then 7 — the same with the mixed grids (more exact), if it is that item
    run(program, water, ['17', '1', '1', '2', '2', '1', '0', 'q'], 'water_basins', timeout=600)
    run(program, water, ['17', '1', '1', '2', '7', '1', '0', 'q'], 'water_basins_mixed', timeout=600)
    run(program, cation, ['17', '1', '1', '2', '2', '1', '0', 'q'], 'cation_basins', timeout=900)
    print('\nГотово: tests/data/multiwfn/pop_*.txt')


def round2(program, water, cation, metal):
    """The answers corrected by the first records: 7 → 14 (AIM charges of the menu of charges, its questions unknown —
    «2» for a grid, «n» for a file); 17 is left by −10 (a «q» there made Multiwfn fall); 17 → 7 asks the kind of grids
    (2 — the exact refinement of the boundary) before the integrand (1 — ρ, 5 — the spin density); 15 → −1 chooses the
    partition (its menu unknown: «2» tried, the record shows the list)."""
    run(program, water, ['7', '14', '2', 'n', '0', 'q'], 'water_aim_charges', timeout=600)
    run(program, metal, ['7', '14', '2', 'n', '0', 'q'], 'MoOCl4_aim_charges', timeout=900)
    run(program, water, ['17', '1', '1', '2', '7', '2', '1', '-10', 'q'], 'water_basins_exact', timeout=600)
    run(program, cation, ['17', '1', '1', '2', '7', '2', '1', '7', '2', '5', '-10', 'q'], 'cation_basins_spin',
        timeout=1200)
    run(program, metal, ['17', '1', '1', '2', '7', '2', '1', '-10', 'q'], 'MoOCl4_basins_exact', timeout=1200)
    run(program, cation, ['15', '-1', '2', '1', '5', '0', 'q'], 'cation_hirshfeld_spin', timeout=600)
    run(program, water, ['15', '-1', '2', '1', '1', '0', 'q'], 'water_hirshfeld_rho', timeout=600)
    print('\nГотово (второй круг): tests/data/multiwfn/pop_*.txt')


if __name__ == '__main__':
    main()

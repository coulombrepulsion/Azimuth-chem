"""The crystals computed through the CP2K inputs of Azimuth and compared with the literature and with Quantum ESPRESSO.

For the owner of the program: the check behind the mark «не проверено» of the CP2K calculations of crystals
(docs/plans/CRYSTAL_VALIDATION.md). Each crystal goes the way a student's goes — the CIF data, the supercell the panel
proposes for a calculation at the Γ point (edges of about 10 Å), the input of modules/sextant/cp2k_inputs.py, CP2K of
«Установить программы», the reader modules/spectrum/readers/cp2k.py — and the lattice parameter of «Оптимизация с
ячейкой» is written to artifacts/cp2k_validation/<name>/result.json.

    .venv/bin/python tools/validate_cp2k.py                 # all
    .venv/bin/python tools/validate_cp2k.py --only Si MgO --processes 4

SPECIFICATION
    SYSTEMS {name: {'cif', 'supercell' (n1, n2, n3) of the conventional cell}}; run(folder, text, processes) -> the
    output; relaxed(name, processes) -> {'a', 'lengths', 'steps', 'converged', 'energy_hartree', 'atoms', 'seconds'}.
"""

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tools'))
OUT = ROOT / 'artifacts' / 'cp2k_validation'


def systems():
    from validate_crystals import _cif

    return {
        'Si': {'cif': _cif('Si', 5.431, 5.431, 5.431, 90, 'F d -3 m :2', [('Si1', 0.125, 0.125, 0.125)]), 'supercell': (2, 2, 2)},
        'MgO': {'cif': _cif('MgO', 4.212, 4.212, 4.212, 90, 'F m -3 m', [('Mg1', 0, 0, 0), ('O1', 0.5, 0.5, 0.5)]),
                'supercell': (2, 2, 2)},
        'NaCl': {'cif': _cif('NaCl', 5.640, 5.640, 5.640, 90, 'F m -3 m', [('Na1', 0, 0, 0), ('Cl1', 0.5, 0.5, 0.5)]),
                 'supercell': (2, 2, 2)},
        'diamond': {'cif': _cif('C', 3.567, 3.567, 3.567, 90, 'F d -3 m :2', [('C1', 0.125, 0.125, 0.125)]),
                    'supercell': (3, 3, 3)},
    }


def run(folder, text, processes=4):
    from modules.sextant import cp2k_inputs, install_tools

    program = install_tools.cp2k_program()
    if program is None:
        raise RuntimeError('CP2K is not found')
    folder.mkdir(parents=True, exist_ok=True)
    (folder / cp2k_inputs.INPUT).write_text(text, encoding='utf-8')
    env = dict(os.environ)
    env['OMP_NUM_THREADS'] = '1'
    env['PATH'] = os.pathsep.join([str(Path(program).parent), env.get('PATH', '')])
    mpirun = Path(program).with_name('mpirun')
    command = [str(program), '-i', cp2k_inputs.INPUT]
    if processes > 1 and mpirun.is_file():
        command = [str(mpirun), '-np', str(processes)] + command
    with open(folder / cp2k_inputs.OUTPUT, 'w', encoding='utf-8') as out:
        done = subprocess.run(command, cwd=folder, env=env, stdout=out, stderr=subprocess.STDOUT)
    if done.returncode:
        raise RuntimeError(f'cp2k: code {done.returncode}')
    return (folder / cp2k_inputs.OUTPUT).read_text(encoding='utf-8', errors='replace')


def relaxed(name, processes=4):
    import numpy as np

    from modules.compass.chemistry import crystal as cr
    from modules.sextant import cp2k_inputs
    from modules.spectrum.readers import cp2k

    system = systems()[name]
    cell = cr.supercell(cr.parse_cif(system['cif']), system['supercell'])
    options = cp2k_inputs.Options(vdw='')  # plain PBE, as the numbers of the literature
    started = time.time()
    folder = OUT / name / 'cellopt'
    text = run(folder, cp2k_inputs.cp2k_input(cell, 'Оптимизация с ячейкой', options), processes)
    r = cp2k.read(text, folder)
    lengths = [float(np.linalg.norm(v)) for v in r.cell] if r.cell is not None else []
    return {'a': lengths[0] / system['supercell'][0] if lengths else None,
            'lengths': [length / n for length, n in zip(lengths, system['supercell'])], 'steps': r.steps,
            'converged': bool(r.converged and r.done), 'energy_hartree': r.energy_hartree, 'atoms': r.nat,
            'version': r.version, 'seconds': round(time.time() - started)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--processes', type=int, default=4)
    args = parser.parse_args(argv)
    for name in args.only or list(systems()):
        target = OUT / name / 'result.json'
        try:
            result = relaxed(name, args.processes)
        except Exception as error:  # noqa: BLE001 — the other crystals go on; the reason is kept
            result = {'error': f'{type(error).__name__}: {error}'}
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
        print(name, json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

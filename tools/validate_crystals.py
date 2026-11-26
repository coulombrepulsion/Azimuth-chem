"""The crystals of the course computed through the inputs of Azimuth and compared with the literature.

For the owner of the program: the check behind the mark «не проверено» of the crystal calculations
(docs/plans/ROADMAP.md, «Проекты студентов курса», item 2). Each crystal goes the way a student's goes — the CIF data,
the primitive cell, the inputs of modules/sextant/qe_inputs.py, pw.x of «Установить программы», the readers of
modules/spectrum/readers/qe.py — and what comes out (the lattice parameters of a vc-relax, the gap of the bands, the
magnetic moments) is written beside the values of the literature in docs/plans/CRYSTAL_VALIDATION.md by hand.

    .venv/bin/python tools/validate_crystals.py                 # all six
    .venv/bin/python tools/validate_crystals.py --only MgO NiO  # some
    .venv/bin/python tools/validate_crystals.py --processes 4

Every crystal writes artifacts/crystal_validation/<name>/ (the inputs, pw.out of every step) and result.json there.

SPECIFICATION
    SYSTEMS {name: {'cif', 'cells' — primitive cells in the conventional one, 'relax' — the cell_dofree of the vc-relax
    ('' — all), 'afm' — the supercell of the antiferromagnetic order or None, 'hubbard' — «Ni 6» or ''}}.
    crystal_of(name) -> (the crystal of the CIF, the cell computed, the rows of its basis); run_steps(folder, steps,
    processes) -> the text of the outputs; relaxed(name, …), gap(name, …), magnetic(name, …) -> dict.
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / 'artifacts' / 'crystal_validation'
SPACING = 0.20  # Å⁻¹, denser than the 0.25 of the panel


def _cif(name, a, b, c, gamma, group, sites):
    rows = '\n'.join(f'{label} {x} {y} {z}' for label, x, y, z in sites)
    return (f'data_{name}\n_cell_length_a {a}\n_cell_length_b {b}\n_cell_length_c {c}\n_cell_angle_alpha 90\n'
            f'_cell_angle_beta 90\n_cell_angle_gamma {gamma}\n_space_group_name_H-M_alt \'{group}\'\nloop_\n'
            '_atom_site_label\n_atom_site_fract_x\n_atom_site_fract_y\n_atom_site_fract_z\n' + rows + '\n')


# the measured cells the series start from (the lattice parameters of the handbooks, room temperature)
SYSTEMS = {
    'Si': {'cif': _cif('Si', 5.431, 5.431, 5.431, 90, 'F d -3 m :2', [('Si1', 0.125, 0.125, 0.125)]), 'cells': 4},
    'MgO': {'cif': _cif('MgO', 4.212, 4.212, 4.212, 90, 'F m -3 m', [('Mg1', 0, 0, 0), ('O1', 0.5, 0.5, 0.5)]), 'cells': 4},
    'SrTiO3': {'cif': _cif('SrTiO3', 3.905, 3.905, 3.905, 90, 'P m -3 m',
                           [('Sr1', 0.5, 0.5, 0.5), ('Ti1', 0, 0, 0), ('O1', 0.5, 0, 0)]), 'cells': 1},
    'TiO2': {'cif': _cif('TiO2', 4.594, 4.594, 2.959, 90, 'P 42/m n m', [('Ti1', 0, 0, 0), ('O1', 0.305, 0.305, 0)]),
             'cells': 1},
    'graphene': {'cif': _cif('graphene', 2.46, 2.46, 15.0, 120, 'P 6/m m m', [('C1', 0.333333333, 0.666666667, 0.5)]),
                 'cells': 1, 'relax': '2Dxy'},
    'NiO': {'cif': _cif('NiO', 4.177, 4.177, 4.177, 90, 'F m -3 m', [('Ni1', 0, 0, 0), ('O1', 0.5, 0.5, 0.5)]), 'cells': 4,
            'afm': (2, 1, 1), 'hubbard': 'Ni 6'},
}


def crystal_of(name):
    from modules.compass.chemistry import crystal as cr

    conventional = cr.parse_cif(SYSTEMS[name]['cif'])
    primitive = cr.primitive(conventional)
    basis = cr.primitive_basis(conventional)
    return conventional, primitive, basis


def environment():
    from modules.sextant import install_tools

    prefix = install_tools.qe_prefix(ROOT)
    env = dict(os.environ)
    env['OMP_NUM_THREADS'] = '1'
    env['PATH'] = os.pathsep.join([str(prefix / 'bin'), env.get('PATH', '')])
    env['OPAL_PREFIX'] = str(prefix)
    return prefix, env


def run_steps(folder, steps, processes=1):
    """Each step of [(file, program, text)] by its program, the outputs one after another in pw.out."""
    prefix, env = environment()
    folder.mkdir(parents=True, exist_ok=True)
    mpirun = prefix / 'bin' / 'mpirun'
    text = ''
    for name, tool, body in steps:
        (folder / name).write_text(body, encoding='utf-8')
        command = [str(prefix / 'bin' / tool), '-in', name]
        if processes > 1 and mpirun.is_file() and tool == 'pw.x':
            command = [str(mpirun), '-np', str(processes)] + command
        done = subprocess.run(command, cwd=folder, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
        text += done.stdout
        if done.returncode:
            (folder / 'pw.out').write_text(text + '\nSTDERR\n' + done.stderr[-3000:], encoding='utf-8')
            raise RuntimeError(f'{tool} {name}: code {done.returncode}')
    (folder / 'pw.out').write_text(text, encoding='utf-8')
    return text


def _pseudo():
    from modules.sextant import qe_pseudo

    return qe_pseudo.table(ROOT), str(qe_pseudo.folder(ROOT))


def _lengths(cell):
    import numpy as np

    return [float(np.linalg.norm(v)) for v in cell]


def relaxed(name, processes, options):
    """The cell after «Оптимизация с ячейкой»: the lengths of the cell computed and the conventional lattice parameter."""
    import numpy as np

    from modules.sextant import qe_inputs
    from modules.spectrum.readers import qe

    conventional, primitive, _ = crystal_of(name)
    table, folder = _pseudo()
    from dataclasses import replace

    # a layer: the cell changes in its plane only (Options.dofree)
    options = replace(options, dofree=SYSTEMS[name].get('relax', ''))
    text = qe_inputs.pw_input(primitive, 'vc-relax', table, folder, spacing=SPACING, options=options)
    out = run_steps(OUT / name / 'vc-relax', [('pw.in', 'pw.x', text)], processes)
    r = qe.read(out)
    volume = abs(float(np.linalg.det(np.array(r.cell, dtype=float))))
    found = {'converged': bool(r.converged and r.done), 'steps': r.steps, 'lengths': _lengths(r.cell), 'volume': volume,
             'pressure_kbar': r.pressures[-1] if r.pressures else None}
    cells = SYSTEMS[name]['cells']
    if conventional.cell.a == conventional.cell.c and conventional.cell.gamma == 90:  # cubic: a of the conventional cell
        found['a'] = (cells * volume) ** (1 / 3)
    else:
        found['a'], found['c'] = found['lengths'][0], found['lengths'][2]
    return found


def gap(name, processes, options):
    """The gap of «Зонная структура» at the measured cell: its kind, its size and where its edges are."""
    from modules.compass.chemistry import band_gap
    from modules.sextant import qe_inputs, qe_paths
    from modules.spectrum.readers import qe

    conventional, primitive, basis = crystal_of(name)
    table, folder = _pseudo()
    steps = qe_inputs.steps(primitive, qe_inputs.BANDS_TASK, table, folder, spacing=SPACING, basis=basis,
                            conventional=conventional, options=options)
    out = run_steps(OUT / name / 'bands', steps, processes)
    path = qe_paths.path(conventional, basis)
    bands = qe.bands(out)
    found = band_gap.gap(bands.energies, band_gap.occupied_bands(out), path.x, path.ticks)
    if found is None:
        return {'kind': None}
    return {'kind': found.kind, 'gap': found.gap, 'direct': found.direct, 'vbm': found.vbm.where, 'cbm': found.cbm.where,
            'direct_at': found.direct_where, 'text': band_gap.text(found)}


def magnetic(name, processes, hubbard_text):
    """The antiferromagnetic state at the measured cell: the gap of the levels of the scf run and the moments."""
    from modules.compass.chemistry import crystal as cr
    from modules.sextant import hubbard, magnetism, qe_inputs

    _, primitive, _ = crystal_of(name)
    cell = cr.supercell(primitive, SYSTEMS[name]['afm'])
    signs = magnetism.afm_signs(cell, SYSTEMS[name]['afm'])
    table, folder = _pseudo()
    options = qe_inputs.Options(magnetic=signs, magnetization=0.5, hubbard=hubbard.parse(hubbard_text) if hubbard_text else ())
    nbnd = qe_inputs.bands_count(cell, table, folder)
    text = qe_inputs.pw_input(cell, 'scf', table, folder, spacing=SPACING, nbnd=nbnd, options=options)
    out = run_steps(OUT / name / ('afm_u' if hubbard_text else 'afm'), [('pw.in', 'pw.x', text)], processes)
    levels = re.findall(r'highest occupied, lowest unoccupied level \(ev\):\s*(-?[\d.]+)\s+(-?[\d.]+)', out)
    moments = re.findall(r'atom\s+(\d+)\s+\(R=[\d.]+\)\s+charge=\s*[\d.]+\s+magn=\s*(-?[\d.]+)', out)
    count = len(cr.unit_cell(cell))
    energy = re.findall(r'^!\s+total energy\s+=\s+(-?[\d.]+) Ry', out, re.M)
    return {'gap': float(levels[-1][1]) - float(levels[-1][0]) if levels else None,
            'moments': [float(m) for _, m in moments[-count:]],
            'total': [float(v) for v in re.findall(r'total magnetization\s+=\s+(-?[\d.]+)', out)[-1:]],
            'absolute': [float(v) for v in re.findall(r'absolute magnetization\s+=\s+(-?[\d.]+)', out)[-1:]],
            'energy_ry': float(energy[-1]) if energy else None, 'atoms': count}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--only', nargs='*')
    parser.add_argument('--processes', type=int, default=4)
    parser.add_argument('--skip', nargs='*', default=[], help='relax, gap, magnetic')
    args = parser.parse_args(argv)
    from modules.sextant import qe_inputs

    for name in args.only or list(SYSTEMS):
        started = time.time()
        folder = OUT / name
        folder.mkdir(parents=True, exist_ok=True)
        target = folder / 'result.json'
        result = json.loads(target.read_text(encoding='utf-8')) if target.is_file() else {}
        afm = SYSTEMS[name].get('afm')
        parts = [] if afm else ['relax', 'gap']
        for part in parts:
            if part in args.skip:
                continue
            try:
                result[part] = (relaxed if part == 'relax' else gap)(name, args.processes, qe_inputs.Options())
            except Exception as error:  # noqa: BLE001 — the other parts and crystals go on; the reason is kept
                result[part] = {'error': f'{type(error).__name__}: {error}'}
            target.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
        if afm and 'magnetic' not in args.skip:
            for key, u in (('afm', ''), ('afm_u', SYSTEMS[name].get('hubbard', ''))):
                try:
                    result[key] = magnetic(name, args.processes, u)
                except Exception as error:  # noqa: BLE001
                    result[key] = {'error': f'{type(error).__name__}: {error}'}
                target.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
        result['seconds'] = round(time.time() - started)
        target.write_text(json.dumps(result, ensure_ascii=False, indent=1), encoding='utf-8')
        print(name, json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())

"""xtb runs (modules/spectrum/readers/xtb.py).

Oracles, independent of the parser: the same quantity printed twice by xtb — the 8-digit «charges» file
against the q column of the output (3 decimals: 5e-4), the «wbo» file against the Wiberg table (3
decimals), the frequencies and IR intensities of g98.out against «vibspectrum» (2 and 5 decimals), the
final energy of xtbopt.log against the TOTAL ENERGY box of the output (convergence of the last step:
the two are printed from different evaluations, 1e-9 Eh), the last frame of xtbopt.log against
xtbopt.xyz; the charges of the neutral molecule sum to 0. Data: cclib test data (BSD-3-Clause),
tests/data/xtb/README.md.
"""

from pathlib import Path
import re

import pytest

from modules.spectrum.readers.xtb import is_xtb, read_xtb

DATA = Path(__file__).parents[1] / 'data' / 'xtb'


def run(name):
    path = DATA / name / f'{name}.out'
    return read_xtb(path.read_text(encoding='utf-8'), path), path.read_text(encoding='utf-8')


def test_single_point_charges_and_wiberg_orders():
    out, text = run('dvb_sp')
    assert is_xtb(text) and out.program == 'xtb 6.6.1' and out.normal_exit and not out.optimization_converged
    assert out.energies == (-26.425939358406,)
    props = out.properties
    assert props.bond_kind == 'Wiberg' and len(props.geometry.atoms) == 20
    charges = props.charges['xtb']
    assert abs(sum(charges)) < 20 * 5e-9
    table = re.search(r'#\s+Z\s+covCN\s+q\s+C6AA.*\n((?:\s+\d+\s+\d+\s+\w+.*\n)+)', text)[1].splitlines()
    for value, line in zip(charges, table):
        assert value == pytest.approx(float(line.split()[4]), abs=5e-4)
    from modules.spectrum.readers.xtb import _wiberg_table

    printed = {(i, j): v for i, j, v in _wiberg_table(text, 20)}  # the 3-decimal table of the output
    assert len(printed) >= 21  # every C-C and C-H bond and the weak 1,3 orders above 0.10
    orders = {(i, j): v for i, j, v in props.mayer_bonds}
    assert set(orders) == set(printed)  # the wbo file lists the same pairs as the table
    for key, value in printed.items():
        assert orders[key] == pytest.approx(value, abs=5e-4)


def test_optimization_steps_and_final_geometry():
    out, text = run('dvb_opt')
    assert out.optimization_converged and len(out.steps) == 6
    assert out.steps[-1].energy == pytest.approx(out.energies[-1], abs=1e-9)
    final = (DATA / 'dvb_opt' / 'xtbopt.xyz').read_text(encoding='utf-8').splitlines()
    first_atom = [float(v) for v in final[2].split()[1:]]
    assert list(out.geometry.atoms[0].position) == pytest.approx(first_atom, abs=1e-12)
    assert out.steps[-1].geometry.atoms[0].position == pytest.approx(out.geometry.atoms[0].position, abs=1e-12)
    assert out.initial_geometry is not None and out.initial_geometry.atoms[0].position != out.geometry.atoms[0].position


def test_frequencies_from_g98_against_vibspectrum():
    out, text = run('dvb_ir')
    assert len(out.frequencies) == 54 and len(out.modes) == 54 and all(m.vectors for m in out.modes)
    rows = []
    for line in (DATA / 'dvb_ir' / 'vibspectrum').read_text(encoding='utf-8').splitlines():
        f = line.split()
        if len(f) == 6 and f[0].isdigit() and f[1] == 'a':  # the rows with a symmetry label: real modes
            rows.append((float(f[2]), float(f[3])))
    assert len(rows) == 54
    for mode, (frequency, intensity) in zip(out.modes, rows):
        assert mode.frequency == pytest.approx(frequency, abs=0.005 + 5e-5)
        assert mode.intensity == pytest.approx(intensity, abs=5e-5 + 5e-6)
    # without the neighbour files the projected frequencies of the output itself are used
    alone = read_xtb(text)
    assert len(alone.frequencies) == 54
    assert all(abs(f - m.frequency) <= 0.005 + 5e-5 for (_, f), m in zip(alone.frequencies, out.modes))
    assert alone.geometry is None and alone.modes == ()


def test_not_xtb():
    with pytest.raises(ValueError):
        read_xtb('nothing here')


def test_relaxed_scan_of_xtb(tmp_path):
    # the scan of xtb is read from xtbscan.log (the frames, «energy:» in the comments) and xcontrol (the
    # coordinate: the first row of $constrain with $scan); the value of each point — from its geometry (the oracle:
    # the O–H distances written into the frames)
    import shutil

    from modules.sextant import inputs

    source = DATA / 'dvb_opt' / 'dvb_opt.out'
    out = tmp_path / 'job.out'
    shutil.copy(source, out)
    frames = ''
    for k, (r, e) in enumerate(((0.90, -5.07), (1.00, -5.08), (1.10, -5.075))):
        frames += f'3\n energy: {e:.12f} gnorm: 0.000500000000 xtb: 6.6.1 (scan)\nO 0 0 0\nH {r} 0 0\nH -0.24 0.93 0\n'
    (tmp_path / 'xtbscan.log').write_text(frames, encoding='utf-8')
    (tmp_path / 'xcontrol').write_text(inputs.xcontrol((), ('B', (0, 1), 0.9, 1.1, 3)), encoding='utf-8')
    found = read_xtb(out.read_text(encoding='utf-8'), out).scan
    assert found is not None and found.kind == 'relaxed' and found.coordinates[0].label.endswith('(1–2)')
    assert [round(p.values[0], 6) for p in found.points] == [0.9, 1.0, 1.1]
    assert [p.energy for p in found.points] == [-5.07, -5.08, -5.075] and found.reference == 1
    (tmp_path / 'xcontrol').write_text(inputs.xcontrol([('C', (2,))]), encoding='utf-8')  # no $scan: no scan
    assert read_xtb(out.read_text(encoding='utf-8'), out).scan is None

"""The course of an optimization (modules/spectrum/analysis/convergence.py), the gradients of ORCA cycles, the TD-DFT
table of Psi4.

Oracles: the numbers printed in the cclib outputs (ORCA 6.0 «RMS gradient / MAX gradient» after each
Cartesian gradient; the CARTESIAN GRADIENT rows; xtb 6.6.1 «gnorm» in xtbopt.log; the SCF energies of the
Gaussian and Psi4 steps), the four «Geometry convergence» tables of an ORCA 6.0.1 optimization of water, and hand-written tables in the
layout of Gaussian «Converged?» and Psi4 tdscf (ASSUMPTION: these layouts are not in the test data).
"""

from pathlib import Path
from types import SimpleNamespace

import pytest

from modules.spectrum.analysis.convergence import history, relative_kcal
from modules.spectrum.readers.orca import read_output
from modules.spectrum.readers.outputs import read_any
from modules.spectrum.readers.psi4 import _excitations

DATA = Path(__file__).parents[1] / 'data'


def orca_with_cycles():
    """The cclib excerpt with the three cycle headers put back before the three cycle geometries."""
    lines, out, n = (DATA / 'orca_cclib' / 'dvb_gopt_orca6.0.out').read_text(encoding='utf-8').split('\n'), [], 0
    for i, line in enumerate(lines):
        if line.startswith('CARTESIAN COORDINATES (ANGSTROEM)') and n < 3:  # the 4th block is the final geometry
            n += 1
            out.append(f'*                GEOMETRY OPTIMIZATION CYCLE {n}            *')
        out.append(line)
    return '\n'.join(out)


def test_orca_gradients_per_cycle():
    text = orca_with_cycles()
    output = read_output(text)
    assert len(output.steps) == 3
    assert output.steps[0].gradient[0] == (0.000763548, 0.000179736, 0.000000092)  # the first printed row
    assert all(len(s.gradient) == 20 for s in output.steps)
    h = history(output, text)
    assert h.criteria == {
        'RMS gradient': [0.0004293185, 0.0002154754, 0.0000607002],
        'MAX gradient': [0.0012287748, 0.0004967553, 0.0001772920],
    }
    for step in output.steps:  # the printed RMS is the RMS of the printed components
        values = [c for row in step.gradient for c in row]
        rms = (sum(c * c for c in values) / len(values)) ** 0.5
        assert rms == pytest.approx(h.criteria['RMS gradient'][step.cycle - 1], rel=1e-5)


def test_orca_table_of_a_real_optimization():
    # ORCA 6.0.1, water: the values of «Geometry convergence», not the Cartesian «RMS gradient ... v» summaries
    # printed above each table (0.0070777728 against 0.0085579430 in the first cycle) — the tolerances are for these
    path = DATA / 'orca601' / 'h2o_opt.out'
    text = path.read_text(encoding='utf-8')
    h = history(read_any(text), text, path)
    assert h.criteria['RMS gradient'] == [0.0085579430, 0.0016561347, 0.0008093303, 0.0000371328]
    assert h.criteria['MAX gradient'] == [0.0102273604, 0.0028685087, 0.0013250493, 0.0000454446]
    assert h.criteria['Energy change'] == [None, 0.0002263574, 0.0000206104, 0.0000052113]
    assert h.thresholds == {'Energy change': 5e-06, 'RMS gradient': 0.0001, 'MAX gradient': 0.0003,
                            'RMS step': 0.002, 'MAX step': 0.004}
    assert not h.converged['Energy change'] and h.converged['RMS gradient'] and h.converged['MAX step']


def test_orca_and_gaussian_tables():
    orca = (
        '*  GEOMETRY OPTIMIZATION CYCLE 1  *\n'
        '          Item                value                   Tolerance       Converged\n'
        '          Energy change      -0.0012345678            0.0000050000      NO\n'
        '          RMS gradient        0.0004000000            0.0001000000      NO\n'
        '          MAX gradient        0.0012000000            0.0003000000      NO\n'
        '          RMS step            0.0050000000            0.0020000000      NO\n'
        '          MAX step            0.0150000000            0.0040000000      NO\n'
        '*  GEOMETRY OPTIMIZATION CYCLE 2  *\n'
        '          Energy change      -0.0000012000            0.0000050000      YES\n'
        '          RMS gradient        0.0000500000            0.0001000000      YES\n'
        '          MAX gradient        0.0001500000            0.0003000000      YES\n'
        '          RMS step            0.0010000000            0.0020000000      YES\n'
        '          MAX step            0.0030000000            0.0040000000      YES\n'
    )
    h = history(SimpleNamespace(program='ORCA', steps=()), orca)
    assert h.criteria['Energy change'] == [0.0012345678, 0.0000012] and h.criteria['MAX step'] == [0.015, 0.003]
    assert h.thresholds['RMS gradient'] == 0.0001 and all(h.converged.values()) and len(h.converged) == 5
    gaussian_text = (DATA / 'gaussian' / 'dvb_gopt_g16.log').read_text(encoding='utf-8')
    table = (
        '         Item               Value     Threshold  Converged?\n'
        ' Maximum Force            {0}     0.000450     {1}\n'
        ' RMS     Force            0.000100     0.000300     YES\n'
        ' Maximum Displacement     0.002000     0.001800     NO \n'
        ' RMS     Displacement     0.000700     0.001200     YES\n'
    )
    text = gaussian_text + table.format('0.001000', 'NO') + table.format('0.000200', 'YES')
    h = history(read_any(text), text)
    assert h.program.startswith('Gaussian') and len(h.energies) == 5
    assert h.criteria['Maximum Force'] == [0.001, 0.0002] and h.criteria['RMS Force'] == [0.0001, 0.0001]
    assert h.thresholds == {'Maximum Force': 0.00045, 'RMS Force': 0.0003, 'Maximum Displacement': 0.0018, 'RMS Displacement': 0.0012}
    assert h.converged['Maximum Force'] and not h.converged['Maximum Displacement']


def test_xtb_psi4_and_energies():
    path = DATA / 'xtb' / 'dvb_opt' / 'dvb_opt.out'
    text = path.read_text(encoding='utf-8')
    h = history(read_any(text, path), text, path)
    assert h.criteria['gnorm'][0] == 0.088050967149 and len(h.criteria['gnorm']) == h.steps == 6
    path = DATA / 'psi4' / 'dvb_gopt_rhf_psi4-1.7.out'
    text = path.read_text(encoding='utf-8')
    h = history(read_any(text, path), text, path)
    assert h.criteria == {} and len(h.energies) == 5
    rel = relative_kcal(h)
    assert rel[-1][1] == 0.0 and rel[0][1] == pytest.approx((-379.77011151867043 + 379.77910359515636) * 627.5094740631, rel=1e-9)
    sp = DATA / 'psi4' / 'dvb_sp_rhf_psi4-1.7.out'
    assert history(read_any(sp.read_text(encoding='utf-8')), sp.read_text(encoding='utf-8')) is None  # one point


def test_psi4_tdscf_table():
    sample = (
        '                                 Excitation Energy         Total Energy        Oscillator Strength             Rotatory Strength\n'
        '     #   Sym: GS->ES (Trans)        au              eV              au           au (length)    au (velocity)    au (length)    au (velocity)\n'
        '    ---- -------------------- --------------- --------------- --------------- --------------- --------------- --------------- ---------------\n'
        '     1        A1->B2 (1 B2)         0.30562         8.31637      -76.12345678          0.0193          0.0161          0.0000          0.0000\n'
        '     2        A1->A2 (1 A2)         0.36001         9.79630      -76.06906678          0.0000          0.0000          0.0000          0.0000\n'
        '\n'
    )
    states = _excitations(sample)
    assert [s.state for s in states] == [1, 2] and states[0].label == 'A1→B2 (1 B2)'
    assert states[0].wavelength == pytest.approx(1239.841984 / 8.31637, rel=1e-6)  # hc/e in eV·nm
    assert states[0].fosc == 0.0193 and states[1].fosc == 0.0
    assert _excitations('no table') == ()

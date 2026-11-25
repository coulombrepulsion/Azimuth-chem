"""NMR spin-spin couplings and multiplets: orca_spectra.read_couplings, analysis/nmr_multiplets.py.

Oracles: ORCA 6.0.1 outputs of the user (tests/data/nmr_j: ethanol and chloroethene, PBE0/pcJ-1, %eprnmr { shift,
ssall }) — the numbers of their «SUMMARY OF ISOTROPIC COUPLING CONSTANTS J (Hz)» tables, which also agree with the
«J[i,j](Total) … iso=» lines; Pascal's triangle for the first-order patterns; the textbook ³J ≈ 7 Hz of an ethyl group
and the trans > cis > |gem| order of the vinyl couplings (experiment: 14.6, 7.3, −1.4 Hz).
"""

import re
from pathlib import Path

import pytest

from modules.spectrum.analysis import nmr_multiplets as nm
from modules.spectrum.readers.orca_spectra import equivalent_groups, read_couplings
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).parents[1] / 'data' / 'nmr_j'


def output(name):
    return (DATA / f'{name}_ssall_orca.out').read_text(encoding='utf-8')


def test_couplings_of_the_summary_table():
    text = output('c2h3cl')
    couplings = {(i, j): v for i, j, v in read_couplings(text)}
    assert len(couplings) == 10  # C0, C1, H3, H4, H5: every pair once
    assert couplings[(3, 4)] == pytest.approx(16.018) and couplings[(3, 5)] == pytest.approx(8.406)
    assert couplings[(4, 5)] == pytest.approx(-3.488) and couplings[(0, 3)] == pytest.approx(194.208)
    for i, j, iso in re.findall(r'J\[(\d+),(\d+)\]\(Total\).*iso=\s*(\S+)', text):  # the same as the detailed blocks
        assert couplings[(int(i), int(j))] == pytest.approx(float(iso), abs=1e-3)
    ethanol = read_couplings(output('ethanol'))
    assert len(ethanol) == 28  # eight nuclei, the table in two blocks of columns
    assert dict(((i, j), v) for i, j, v in ethanol)[(7, 8)] == pytest.approx(-13.553)
    assert read_any(text).couplings == read_couplings(text)
    assert read_couplings('no table here') == ()


def test_patterns_follow_pascals_triangle():
    lines = nm.lines(1.0, [(3, 7.0)], 400.0)  # a quartet
    assert [round((p - 1.0) * 400, 6) for p, _ in lines] == [-10.5, -3.5, 3.5, 10.5]
    assert [w * 8 for _, w in lines] == pytest.approx([1, 3, 3, 1])
    dd = nm.lines(0.0, [(1, 16.0), (1, 8.0)], 100.0)
    assert [round(p * 100, 6) for p, _ in dd] == [-12.0, -4.0, 4.0, 12.0] and sum(w for _, w in dd) == pytest.approx(1)
    assert nm.name([]) == 'с' and nm.name([(3, 7.0), (1, 1.2)]) == 'кд' and nm.name([(1, 1)] * 4) == 'м'
    assert nm.frequency('C', 400) == pytest.approx(100.58, abs=0.01)


def test_multiplets_of_ethanol_and_chloroethene():
    text = output('ethanol')
    result = read_any(text)
    groups = equivalent_groups(result.geometry)
    elements = [result.geometry.atoms[g[0]].symbol for g in groups]
    by_atoms = {g: nm.partners(k, groups, elements, result.couplings) for k, g in enumerate(groups)}
    ch2, ch3 = by_atoms[(4, 5)], by_atoms[(6, 7, 8)]
    # the three H of the rotating CH3 averaged: 2.11, 5.28, 14.26 Hz to H4 → 7.2 Hz, a textbook ethyl group
    assert ch2[0][0] == 3 and ch2[0][1] == pytest.approx(7.22, abs=0.01) and nm.name(ch2)[0] == 'к'
    assert ch3[0][0] == 2 and ch3[0][1] == pytest.approx(7.22, abs=0.01) and nm.name(ch3)[0] == 'т'
    assert by_atoms[(0,)] == [] and by_atoms[(1,)] == []  # ¹³C{¹H}: decoupled singlets
    assert [n for n, _ in nm.partners(groups.index((1,)), groups, elements, result.couplings, decoupled=False)] == \
        [2, 3, 1]  # the CH2 carbon coupled: ¹J 134.7 Hz to its H, ²J −4.5 to the CH3 (averaged), ²J −2.4 to the OH
    vinyl = read_any(output('c2h3cl'))
    groups = equivalent_groups(vinyl.geometry)
    elements = [vinyl.geometry.atoms[g[0]].symbol for g in groups]
    split = {g: nm.partners(k, groups, elements, vinyl.couplings) for k, g in enumerate(groups)}
    assert [abs(j) for _, j in split[(3,)]] == pytest.approx([16.018, 8.406])  # trans, cis
    assert all(nm.name(split[(h,)]) == 'дд' for h in (3, 4, 5))
    assert abs(split[(4,)][1][1]) < abs(split[(3,)][1][1]) < abs(split[(3,)][0][1])  # |gem| < cis < trans


def test_curve_is_lorentzian():
    x, y = nm.curve([(nm.lines(2.0, [], 400.0), 1)], 400.0, width_hz=1.0, lo=1.99, hi=2.01, points=2001)
    assert y.max() == pytest.approx(1.0, abs=1e-3) and x[y.argmax()] == pytest.approx(2.0, abs=1e-5)
    half = x[y >= 0.5]
    assert (half.max() - half.min()) * 400 == pytest.approx(1.0, abs=0.02)  # full width at half height = 1 Hz


def test_sextant_writes_the_verified_input_of_couplings():
    # «КССВ» under the NMR task of ORCA — the input of tests/data/nmr_j/inputs (no «NMR» keyword, %eprnmr after
    # the coordinates: ORCA 6.0.1 stopped with the block before them, «no coordinates have been read»)
    from azimuth.core import Calculation, orca_input, read_xyz
    from modules.sextant import inputs

    water = read_xyz('3\nwater\nO 0 0 0.1173\nH 0 0.7572 -0.4692\nH 0 -0.7572 -0.4692')
    calc = Calculation(method='PBE0', basis='def2-SVP', task=inputs.NMR_TASK, couplings=True)
    text = orca_input(water, calc)
    assert text.index('* xyz') < text.index('%eprnmr') and 'Nuclei = all H { shift, ssall }' in text
    assert 'all C' not in text and ' NMR' not in text.split('\n')[1]
    assert ' NMR' in orca_input(water, Calculation(task=inputs.NMR_TASK)).split('\n')[1]  # without J: as before
    found = inputs.read_settings('orca', text)
    assert found['task'] == inputs.NMR_TASK and found['couplings'] is True
    reference = (DATA / 'inputs' / 'ethanol_ssall_orca.inp').read_text(encoding='utf-8')
    assert inputs.read_settings('orca', reference)['task'] == inputs.NMR_TASK
    assert 'couplings' in inputs.task_options('orca', inputs.NMR_TASK)
    assert 'couplings' not in inputs.task_options('gaussian', inputs.NMR_TASK)

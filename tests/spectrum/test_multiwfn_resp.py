"""The RESP charges of Multiwfn (modules/spectrum/wavefunction/multiwfn_resp.py).

Oracles: the outputs of Multiwfn 2026.7.15 recorded on the Mac of the user by tools/record_multiwfn_resp.py
(tests/data/multiwfn/resp_*): the menu 7 → 18, the water of Gaussian 16 and the benzaldehyde of ORCA (def2-SVPD).
"""

import re
from pathlib import Path

import pytest

from modules.spectrum.wavefunction import multiwfn
from modules.spectrum.wavefunction import multiwfn_resp as mr

MWFN = Path(__file__).parents[1] / 'data' / 'multiwfn'


def text(name):
    return (MWFN / name).read_text(encoding='utf-8', errors='replace')


def test_answers_are_the_items_of_the_record():
    menu = text('resp_menu.txt')
    assert re.search(r'^\s*18 Restrained ElectroStatic Potential \(RESP\)', menu, re.M)
    assert re.search(r'^\s*1 Start standard two-stage RESP fitting', menu, re.M)
    assert text('resp_water_standard_chg.txt').startswith('answers: ' + ' | '.join(mr.ANSWERS) + '\n')


def test_charges_of_water():
    charges, rmse, rrmse = mr.parse_resp(text('resp_water_standard_chg.txt'))
    assert charges == (-0.5891260132, 0.2945630066, 0.2945630066)
    assert (rmse, rrmse) == (0.00076, 0.045093) and sum(charges) == pytest.approx(0, abs=1e-9)
    chg = text('resp_water_standard_chg__input.chg').split()
    assert chg[0] == 'O' and float(chg[4]) == charges[0]


def test_charges_of_benzaldehyde():
    charges, _, rrmse = mr.parse_resp(text('resp_benzaldehyde_standard.txt'))
    assert len(charges) == 14 and sum(charges) == pytest.approx(0, abs=1e-9)
    assert charges[0] == -0.4698435342 and charges[1] == 0.3970988577  # O and the C of C=O
    assert all(c > 0 for c in charges[8:]) and rrmse == 0.115615  # the hydrogens


def test_no_table_no_charges(monkeypatch, tmp_path):
    assert mr.parse_resp('nothing') is None
    monkeypatch.setattr(multiwfn, '_run', lambda *a, **k: (text('resp_water_standard_chg.txt'),
                                                           {'input.chg': text('resp_water_standard_chg__input.chg')}))
    charges, _, rrmse, chg, _ = mr.run_resp('mwfn', tmp_path / 'w.fchk')
    assert charges[0] == -0.5891260132 and chg.startswith('O')
    monkeypatch.setattr(multiwfn, '_run', lambda *a, **k: ('no RESP', {}))
    with pytest.raises(ValueError):
        mr.run_resp('mwfn', tmp_path / 'w.fchk')

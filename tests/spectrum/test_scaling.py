"""Scaling factors of frequencies (modules/spectrum/analysis/scaling.py) — the values of NIST CCCBDB."""

from modules.spectrum.analysis import scaling


def test_values_of_cccbdb_and_the_levels_of_the_programs():
    found = scaling.recommended('B3LYP/6-31G(d)')  # the Gaussian archive
    assert (found.factor, found.uncertainty, found.exact) == (0.960, 0.022, True)
    assert scaling.recommended('MP2 STO-3G').factor == 0.872  # the ORCA input echo
    assert scaling.recommended(method='PBE0', basis='cc-pVTZ').factor == 0.961
    assert scaling.recommended('WB97XD/aug-cc-pVTZ').method == 'ωB97X-D'
    near = scaling.recommended(method='B3LYP', basis='def2-SVP')  # no def2-SVP in CCCBDB: cc-pVDZ
    assert near.factor == 0.970 and not near.exact and 'cc-pVDZ' in near.note
    assert scaling.recommended(method='B3LYP', basis='def2-TZVPP').uncertainty is None
    assert scaling.recommended(method='CAM-B3LYP', basis='def2-SVP') is None  # not in CCCBDB: nothing invented
    assert scaling.recommended('') is None and scaling.recommended('XTB') is None
    for method, table in scaling.FACTORS.items():
        for basis, (factor, unc) in table.items():
            assert 0.8 < factor < 1.01 and (unc is None or 0 < unc < 0.1), (method, basis)

"""Multiwfn: the RESP charges.

§1 PURPOSE
    The beta of docs/plans/ROADMAP.md, item 7: the charges fitted to the electrostatic potential with restraints (RESP,
    Bayly — Cieplak — Cornell — Kollman 1993) — the charges of the force fields AMBER / GAFF for molecular dynamics —
    in «±» of Compass next to ADCH and CM5, for any file of orbitals.
§2 ALGORITHM
    Main menu 7 (atomic charges) → 18 (RESP) → 1 (the standard two-stage fitting: the ESP at the MK points — the
    Merz — Kollman layers at 1.4–2.0 vdW radii —, stage 1 under the weak hyperbolic restraint a = 0.0005, stage 2 under
    the strong one a = 0.001 for the H of CH2 and CH3 made equivalent; skipped when there are none) → «y» (the atoms
    with their charges to input.chg: x y z q, Å) → 0, 0 (back to the main menu), q. The charges — the last table
    «Center Charge» («1(O ) -0.5891260132»), its quality — «RMSE: … RRMSE: …» (a.u.; RRMSE relative to the ESP).
    Recorded on Multiwfn 2026.7.15 (tools/record_multiwfn_resp.py, tests/data/multiwfn/resp_*): the menu, the water of
    Gaussian 16 (2913 points, O −0.589) and the benzaldehyde of ORCA def2-SVPD (10301 points, 7 s).
§4 SPECIFICATION
    ANSWERS; parse_resp(text) -> (charges tuple, rmse | None, rrmse | None) | None;
    run_resp(program, path, cores=1, step=None, timeout=1800) -> (charges, rmse, rrmse, chg text | None, output).
§7 TESTS tests/spectrum/test_multiwfn_resp.py.
"""

import re

from azimuth.i18n import tr
from modules.spectrum.wavefunction import multiwfn

ANSWERS = ('7', '18', '1', 'y', '0', '0', 'q')
_HEAD = re.compile(r'^\s*Center\s+Charge\s*$')
_ROW = re.compile(r'^\s*(\d+)\(\s*[A-Za-z]{1,3}\s*\)\s+(-?\d+\.\d+)\s*$')
_QUALITY = re.compile(r'RMSE:\s*(-?\d+\.\d+)\s+RRMSE:\s*(-?\d+\.\d+)')


def parse_resp(text):
    lines = text.replace('\r', '').split('\n')
    starts = [k for k, line in enumerate(lines) if _HEAD.match(line)]
    if not starts:
        return None
    charges, rest = [], starts[-1] + 1
    for k in range(starts[-1] + 1, len(lines)):
        row = _ROW.match(lines[k])
        if not row:
            rest = k
            break
        charges.append(float(row.group(2)))
    if not charges:
        return None
    quality = _QUALITY.search('\n'.join(lines[rest:rest + 4]))
    return tuple(charges), (float(quality.group(1)) if quality else None), (float(quality.group(2)) if quality else None)


def run_resp(program, path, cores=1, step=None, timeout=1800):
    text, kept = multiwfn._run(program, path, ANSWERS, cores, step, timeout, keep=('input.chg',))
    found = parse_resp(text)
    if not found:
        raise ValueError(tr('Multiwfn не напечатал заряды RESP. Конец его вывода:') + '\n' + multiwfn._tail(text))
    charges, rmse, rrmse = found
    return charges, rmse, rrmse, kept.get('input.chg'), text

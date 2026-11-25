"""The VCD of the vibrations — ORCA «VCD SPECTRUM CALCULATION»
(%freq DoVCD true end) and Gaussian «Rot. str.» (Freq=VCD); the signed spectrum."""

import re
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis.ir_spectrum import broaden, lines
from modules.spectrum.readers.outputs import read_any

DATA = Path(__file__).resolve().parents[1] / 'data'
# the table as in the ORCA 6.0 tutorial «Vibrational Circular Dichroism (VCD)» (faccts.de), for the modes of water
ORCA_VCD = """
------------------------
VCD SPECTRUM CALCULATION
------------------------

Calculating the atomic axial tensor (analytic) ... done ( 0.151 sec)

---------------------------------
 Mode   Freq    VCD-Intensity
       (1/cm) (1E-44*esu^2*cm^2)
---------------------------------
    6  1637.6         -3.66
    7  3786.9          3.09
    8  3881.9         13.12
"""


def test_orca_vcd_table():
    text = (DATA / 'orca601' / 'h2o_optfreq.out').read_text(encoding='utf-8')
    at = text.index('IR SPECTRUM')
    text = text[:at] + ORCA_VCD + '\n' + text[at:]
    output = read_any(text, 'h2o_vcd.out')
    vcd = {m.index: m.vcd for m in output.modes if m.vcd is not None}
    assert vcd == {6: -3.66, 7: 3.09, 8: 13.12}
    assert {m.index: m.intensity for m in output.modes if m.intensity}[6] == 55.30  # IR still read


def test_gaussian_rot_str():
    text = (DATA / 'gaussian' / 'dvb_ir_g16.log').read_text(encoding='utf-8')
    count = [0]

    def rot(m):
        count[0] += 1
        values = '  '.join(f'{(-1) ** (count[0] + k) * (k + 1) * 1.5:9.4f}' for k in range(len(m[1].split())))
        return m[0] + f'\n           Rot. str.  ---  {values}'

    text = re.sub(r'^\s+IR Intensities ---([^\n]*)', rot, text, flags=re.M)
    output = read_any(text, 'dvb_vcd.log')
    signed = [m.vcd for m in output.modes if m.vcd is not None]
    assert len(signed) == len(output.modes) and min(signed) < 0 < max(signed)


def test_a_signed_spectrum():
    from modules.spectrum.readers.vibration_data import Vibration

    modes = (Vibration(1, 1000.0, intensity=-5.0), Vibration(2, 1500.0, intensity=8.0))
    with pytest.raises(ValueError):
        lines(modes)  # an IR intensity is never negative
    x, y = broaden(modes, 20, signed=True)
    assert y[np.argmin(np.abs(x - 1000))] < 0 < y[np.argmin(np.abs(x - 1500))]

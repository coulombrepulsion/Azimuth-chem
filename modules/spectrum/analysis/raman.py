"""Raman spectra from the activities of a frequency calculation.

§1 THEORY
    A frequency calculation with the polarizability derivatives gives for every mode i the Raman activity
        S_i = 45 a_i'^2 + 7 g_i'^2 (A^4/amu; a' — the isotropic, g' — the anisotropic part of d alpha / d Q_i)
    and the depolarization ratio of linearly polarized light rho_i = 3 g'^2 / (45 a'^2 + 4 g'^2), 0..3/4. A mode that
    is not totally symmetric has a' = 0 and rho = 3/4 exactly; a totally symmetric one has rho < 3/4 (a polarized band).
    The activity does not depend on the laser; the measured scattered intensity does (Polavarapu, J. Phys. Chem. 94,
    8106 (1990); Keresztury et al., Spectrochim. Acta A 49, 2007 (1993)):
        I_i ~ (nu_0 - nu_i)^4 S_i / (nu_i (1 - exp(-c_2 nu_i / T)))
    with nu_0 the wavenumber of the laser, nu_i of the mode (cm^-1), c_2 = h c / k_B = 1.438776877 cm K (CODATA 2018)
    and T the temperature: the fourth power of the scattered frequency and the Boltzmann population of the levels. Only
    ratios are meaningful (the constant in front is dropped): the strongest line is 100.
§2 ALGORITHM
    raman_modes(modes, kind, laser_nm, temperature): copies of the modes whose «intensity» is the activity ('activity')
    or the relative intensity ('intensity'), so that the IR plot (ir_spectrum.py: sticks, Gaussian bands, the scaling
    factor, the comparison) draws them as they are; modes without an activity get intensity None (not drawn).
§3 APPLICATIONS
    modules/spectrum/views/vibrations.py (the switch «ИК / Раман» of the plot, the columns of the table).
§4 SPECIFICATION
    KINDS = ('activity', 'intensity'); LASER_NM = 532.0 (a design choice: the usual green laser), TEMPERATURE = 298.15.
    has_raman(modes) -> bool; seen(modes) -> {mode index} with an activity above ZERO of the largest (the others
    are forbidden or too weak: their printed depolarization is 0/0 noise and is not shown); intensities(modes, laser_nm,
    temperature) -> {mode index: relative intensity, max 100};
    raman_modes(modes, kind='activity', laser_nm=LASER_NM, temperature=TEMPERATURE) -> tuple of Vibration.
    ZERO = 1e-3 (a design choice: the forbidden bands of ethylene with NumFreq print 0.0000 next to 182; the weakest
    allowed one of the test molecules is 0.60, i.e. 3e-3 of the largest).
    ValueError: an unknown kind, laser outside 200..2000 nm, temperature outside 1..5000 K, a mode with a frequency at
    or above the laser line.
§5 PROCEDURES - below.
§6 NOTES
    ORCA 6.0.1 prints «RAMAN SPECTRUM» only with numerical frequencies (NumFreq): with analytic ones it writes
    «Analytical Hessian not available for calculation of RAMAN spectra» and computes the polarizability only
    (tests/data/raman). Gaussian (Freq=Raman) — after a reference output.
§7 TESTS
    tests/spectrum/test_raman.py.
"""

from dataclasses import replace
from math import exp, isfinite

KINDS = ('activity', 'intensity')
LASER_NM = 532.0
TEMPERATURE = 298.15
C2 = 1.438776877  # cm K, second radiation constant h c / k_B (CODATA 2018)
ZERO = 1e-3  # of the largest activity: below it a mode is not seen in Raman (§4)


def has_raman(modes):
    return any(m.raman_activity is not None for m in modes)


def seen(modes):
    values = [m.raman_activity for m in modes if m.raman_activity is not None and m.frequency > 0]
    top = max(values, default=0.0)
    return {m.index for m in modes if m.raman_activity is not None and m.frequency > 0 and top > 0
            and m.raman_activity > ZERO * top}


def intensities(modes, laser_nm=LASER_NM, temperature=TEMPERATURE):
    if not isfinite(laser_nm) or not 200 <= laser_nm <= 2000:
        raise ValueError('laser wavelength must be 200-2000 nm')
    if not isfinite(temperature) or not 1 <= temperature <= 5000:
        raise ValueError('temperature must be 1-5000 K')
    nu0 = 1e7 / laser_nm
    raw = {}
    for m in modes:
        if m.raman_activity is None or m.frequency <= 0:
            continue
        if m.frequency >= nu0:
            raise ValueError('a mode at or above the laser line')
        raw[m.index] = (nu0 - m.frequency) ** 4 * m.raman_activity / (m.frequency * (1 - exp(-C2 * m.frequency / temperature)))
    top = max(raw.values(), default=0.0)
    return {k: (100.0 * v / top if top > 0 else 0.0) for k, v in raw.items()}


def raman_modes(modes, kind='activity', laser_nm=LASER_NM, temperature=TEMPERATURE):
    if kind not in KINDS:
        raise ValueError(f'unknown kind {kind!r}')
    values = ({m.index: m.raman_activity for m in modes if m.raman_activity is not None} if kind == 'activity'
              else intensities(modes, laser_nm, temperature))
    return tuple(replace(m, intensity=values.get(m.index)) for m in modes)

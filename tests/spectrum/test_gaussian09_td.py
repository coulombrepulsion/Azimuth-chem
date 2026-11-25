"""TD-DFT of Gaussian 09 — a real output of the user (G09 A.02, Windows, CRLF) and the energy of the
excited state that Gaussian follows (single point: apart; with Opt or Freq: the energy of the result)."""

from pathlib import Path


from modules.spectrum.readers.gaussian import _route
from modules.spectrum.readers.orca_spectra import uv_curve
from modules.spectrum.readers.outputs import read_any
from modules.spectrum.analysis.reaction import level_of_theory

LOG = Path(__file__).parents[1] / 'data' / 'gaussian09' / 'ind_acid_td_g09.out'
TOTAL = (' This state for optimization and/or second-order correction.\r\n'
         ' Total Energy, E(TD-HF/TD-KS) =  -1258.22895555    \r\n')


def text():
    return LOG.read_bytes().decode('ascii')


def test_forty_states_of_gaussian_09():
    t = text()
    assert '\r\n' in t
    out = read_any(t, str(LOG))
    assert out.program == 'Gaussian 09' and out.normal_exit and out.energies == (-1258.3060999,)
    assert out.excited_energy is None  # G09 A.02 printed no «Total Energy, E(TD-HF/TD-KS)» for this single point
    assert level_of_theory(t, out.program) == 'B3LYP/6-311+G(2D,P)' and _route(t) == '# B3LYP/6-311+G(2d,p) TD(NStates=40)'
    a = out.absorption
    assert len(a) == 40 and [e.state for e in a] == list(range(1, 41))
    # «Excited State 1: Singlet-A 2.0992 eV 590.62 nm f=0.1531», «Excited State 40: … 6.2341 eV 198.88 nm f=0.0027»
    assert (a[0].label, a[0].multiplicity, a[0].energy_ev, a[0].wavelength, a[0].fosc) == ('A', 1, 2.0992, 590.62, 0.1531)
    assert (a[-1].energy_ev, a[-1].wavelength, a[-1].fosc) == (6.2341, 198.88, 0.0027)
    nm, eps = uv_curve(a, 0.3)
    assert len(nm) == len(eps) and max(eps) > 0


def test_the_excited_state_of_a_single_point_is_kept_apart():
    t = text().replace(' This state for optimization and/or second-order correction.\r\n', TOTAL, 1)
    out = read_any(t, str(LOG))
    assert out.energies == (-1258.3060999,) and out.excited_energy == (1, -1258.22895555)


def test_with_opt_or_freq_the_energy_of_the_result_is_the_excited_state():
    t = text().replace(' This state for optimization and/or second-order correction.\r\n', TOTAL, 1)
    for job in ('Opt', 'Freq', 'opt=tight'):
        out = read_any(t.replace(' # B3LYP/6-311+G(2d,p) TD(NStates=40)', ' # B3LYP/6-311+G(2d,p) TD(NStates=40) ' + job), str(LOG))
        assert out.energies == (-1258.22895555,) and out.excited_energy is None, job


def test_symmetry_not_determined():
    t = text().replace('Excited State   1:      Singlet-A    ', 'Excited State   1:      Singlet-?Sym ', 1)
    assert read_any(t).absorption[0].label == '?'

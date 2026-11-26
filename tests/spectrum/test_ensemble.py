"""The spectrum of conformers averaged by their Boltzmann shares (modules/spectrum/analysis/ensemble.py)."""

import shutil
from pathlib import Path

import numpy as np
import pytest

from modules.spectrum.analysis import ensemble
from modules.spectrum.analysis.ir_spectrum import broaden
from modules.spectrum.readers.orca_spectra import Excitation, cd_curve, uv_curve

DATA = Path(__file__).resolve().parents[1] / 'data'


def test_two_equal_conformers_give_the_spectrum_of_one(tmp_path):
    source = DATA / 'orca601' / 'h2o_optfreq.out'
    paths = [shutil.copy(source, tmp_path / name) for name in ('a.out', 'b.out')]
    found = ensemble.conformers(paths, 298.15)
    assert found['shares'] == pytest.approx([0.5, 0.5]) and len(found['outputs']) == 2
    modes = found['outputs'][0].modes
    mixed = ensemble.weighted_modes([o.modes for o in found['outputs']], found['shares'])
    x, y = broaden(modes, 20)
    mx, my = broaden(mixed, 20)
    assert np.allclose(x, mx) and np.allclose(y, my)
    with pytest.raises(ValueError):
        ensemble.conformers(paths[:1], 298.15)


def test_excitations_are_weighted_with_their_signs():
    a = Excitation(1, '1', 4.0, 32262.0, 309.96, 0.2, r_length=10.0)
    b = Excitation(1, '1', 4.5, 36295.0, 275.52, 0.1, r_velocity=-20.0)
    mixed = ensemble.weighted_excitations([[a], [b]], [0.75, 0.25])
    assert [e.fosc for e in mixed] == pytest.approx([0.15, 0.025])
    assert mixed[0].rotatory == pytest.approx(7.5) and mixed[1].rotatory == pytest.approx(-5.0)
    x, y = uv_curve(mixed)
    assert np.isfinite(y).all() and cd_curve(mixed)[1].min() < 0 < cd_curve(mixed)[1].max()
    assert ensemble.missing(['a', 'b'], [[a], []]) == ('b',)


# two rotamers of ethanol, ORCA 6.0.1 B3LYP-D3BJ/def2-SVP NMR (tests/data/orca601/README.md): copied from the outputs —
# FINAL SINGLE POINT ENERGY and the column «Isotropic» of CHEMICAL SHIELDING SUMMARY (C, C, O, 6 H)
ROTAMER_E = (-154.830083571198, -154.830440126007)
ROTAMER_SIGMA = ((173.115, 135.832, 287.499, 31.418, 31.022, 31.729, 28.840, 28.674, 32.402),
                 (177.918, 135.562, 306.682, 31.596, 31.118, 31.117, 28.623, 28.623, 31.679))


def test_the_shieldings_of_two_real_rotamers_averaged():
    from math import exp

    from modules.spectrum.analysis import boltzmann
    from modules.spectrum.readers.outputs import read_any

    outputs = []
    for name in ('ethanol_a.out', 'ethanol_b.out'):
        path = DATA / 'orca601' / 'nmr_conformers' / name
        outputs.append(read_any(path.read_text(encoding='utf-8', errors='replace'), str(path)))
    assert tuple(o.energies[-1] for o in outputs) == ROTAMER_E
    for output, sigma in zip(outputs, ROTAMER_SIGMA):
        assert [round(s.isotropic, 3) for s in output.shieldings] == list(sigma)
    # by hand: w = exp(−ΔE / kT), k = 3.166811563e-6 Eh/K — the higher rotamer has 41 %
    weight = exp(-(ROTAMER_E[0] - ROTAMER_E[1]) / (3.166811563e-6 * 298.15))
    shares = [weight / (1 + weight), 1 / (1 + weight)]
    assert shares[0] == pytest.approx(0.4067, abs=5e-4)
    assert boltzmann.shares(ROTAMER_E, 298.15) == pytest.approx(shares, rel=1e-9)
    mixed = ensemble.weighted_shieldings([o.shieldings for o in outputs], shares)
    assert [(s.atom, s.element) for s in mixed] == [(s.atom, s.element) for s in outputs[0].shieldings]
    assert [s.isotropic for s in mixed] == pytest.approx(
        [shares[0] * a + shares[1] * b for a, b in zip(*ROTAMER_SIGMA)], abs=6e-4)
    assert mixed[0].isotropic == pytest.approx(175.96, abs=0.01) and mixed[0].anisotropy is None
    assert [s.isotropic for s in ensemble.weighted_shieldings([outputs[0].shieldings] * 2, [0.3, 0.7])] == pytest.approx(
        [s.isotropic for s in outputs[0].shieldings])
    with pytest.raises(ValueError, match='порядком атомов'):
        ensemble.weighted_shieldings([outputs[0].shieldings, outputs[1].shieldings[::-1]], shares)
    with pytest.raises(ValueError):
        ensemble.weighted_shieldings([], [])

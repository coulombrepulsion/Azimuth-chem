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

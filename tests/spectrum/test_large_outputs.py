"""Spectrum reads outputs up to 256 MB (was 32 MB)."""

from pathlib import Path

import pytest

from modules.spectrum.readers import orca, outputs

DATA = Path(__file__).parents[1] / 'data' / 'orca601'
FILLER = '   0.1425E-03   -    I 133 YY,   SHELL 735,   AO 1762\n'  # a long table of a real output, read by nothing


def padded(name, megabytes):
    text = (DATA / f'{name}.out').read_text(encoding='utf-8')
    cut = text.index('****END OF INPUT****') + len('****END OF INPUT****\n')
    return text[:cut] + FILLER * (megabytes * 1_000_000 // len(FILLER)) + text[cut:], text


def test_an_output_bigger_than_32_mb_is_read_as_the_small_one():
    big, small = padded('h2o_optfreq', 40)
    assert len(big) > 32_000_000
    a, b = outputs.read_any(big), outputs.read_any(small)
    assert a.energies == b.energies and a.frequencies == b.frequencies and len(a.steps) == len(b.steps) == 4
    assert a.normal_exit and a.optimization_converged


def test_the_limit_is_said(monkeypatch):
    monkeypatch.setattr(orca, 'MAX_BYTES', 1000)
    monkeypatch.setattr(outputs, 'MAX_BYTES', 1000)
    with pytest.raises(ValueError, match='256 МБ'):
        outputs.read_any((DATA / 'h2o_energy.out').read_text(encoding='utf-8'))
    assert orca.MAX_BYTES == 1000 and 'МБ' in str(orca.too_large())

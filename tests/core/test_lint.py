"""ruff with the rules of ruff.toml (pyflakes F, bugbear B, syntax errors E9) finds nothing — run with the tests, as
the plan to the beta asks (docs/plans/BETA_PLAN.md, stage 0). Skipped where ruff is not installed
(requirements-dev.txt)."""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def _ruff():
    beside = Path(sys.executable).with_name('ruff')
    return str(beside) if beside.exists() else shutil.which('ruff')


@pytest.mark.skipif(_ruff() is None, reason='ruff is not installed: pip install -r requirements-dev.txt')
def test_ruff_finds_nothing():
    found = subprocess.run([_ruff(), 'check', '--output-format', 'concise', '.'], cwd=ROOT, capture_output=True,
                           text=True, timeout=300)
    assert found.returncode == 0, found.stdout[-4000:] + found.stderr[-1000:]

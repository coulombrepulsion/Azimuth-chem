"""The general model of a result (modules/spectrum/readers/results.py) — the audit of 2026-11-04, R6."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[2]


def test_the_model_needs_no_reader():
    code = ('import sys; import modules.spectrum.readers.results as r; '
            "assert 'modules.spectrum.readers.orca' not in sys.modules, sorted(m for m in sys.modules if 'spectrum' in m); "
            'print(r.Output.__module__)')
    found = subprocess.run([sys.executable, '-c', code], cwd=ROOT, capture_output=True, text=True, timeout=120)
    assert found.returncode == 0 and found.stdout.strip() == 'modules.spectrum.readers.results', found.stderr


def test_old_imports_give_the_same_classes():
    from modules.spectrum.readers import gaussian, orca, results

    assert orca.Output is results.Output and orca.OptimizationStep is results.OptimizationStep
    assert gaussian.Output is results.Output and orca.MAX_BYTES == results.MAX_BYTES

"""The symmetry engine of Compass and Spectrum (azimuth/symmetry_engine) is the Atlas's own, unchanged — the
program and the page «Симметрия» of the Atlas on the site agree. And the program reads it without the Atlas."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
ENGINE = ROOT / 'azimuth' / 'symmetry_engine'
ATLAS = ROOT / 'modules' / 'atlas' / 'atlas_v2' / 'quas_atlas' / 'core'
FILES = ('symfind.py', 'symmetry.py', 'jsmath.py', 'libm_glibc.py', '_sincostab.py', 'data/symmetry_ct.json')


@pytest.mark.parametrize('name', FILES)
def test_the_copies_are_the_atlas_own(name):
    if not (ATLAS / name).is_file():
        pytest.skip('no Atlas in the repository')
    assert (ENGINE / name).read_bytes() == (ATLAS / name).read_bytes(), f'{name}: changed in one place only'


def test_compass_and_spectrum_read_it_without_the_atlas():
    """In a process of its own: the Atlas's package is not importable there and not asked for."""
    script = (
        'import sys, builtins\n'
        'real = builtins.__import__\n'
        'def guard(name, *a, **k):\n'
        '    assert not name.startswith(("quas_atlas", "modules.atlas")), name\n'
        '    return real(name, *a, **k)\n'
        'builtins.__import__ = guard\n'
        'from modules.compass.chemistry import symmetry\n'
        'from modules.spectrum.analysis import thermo\n'
        'from azimuth.core import Atom, Molecule\n'
        'water = Molecule("water", [Atom("O", 0, 0, 0.1173), Atom("H", 0, 0.7572, -0.4692), Atom("H", 0, -0.7572, -0.4692)])\n'
        'print(symmetry.analyze(water)["name"], thermo._mass("U", []))  # U: no isotope in MASSES, the mean weight\n'
    )
    done = subprocess.run([sys.executable, '-c', script], cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert done.returncode == 0, done.stderr
    group, mass = done.stdout.split()
    assert group == 'C2v' and float(mass) == 238.0  # the table of symfind (_w)

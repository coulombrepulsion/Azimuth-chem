"""Installation diagnostics.

§1: Detect missing runtime dependencies and corrupted bundled teaching files.
§2: Run independent checks; collect every failure; exit nonzero on any failure.
§3: Support setup and user troubleshooting without opening a GUI window.
§4: --quick skips VTK contour smoke; paths resolved from this file, no mutation.
§5: Check runners below import packages, hash assets, find a point group (no Atlas server), build a scalar surface.
§6: All output is ASCII; exceptions are escaped; no graphical context is needed.
§7: Integrity oracle is assets-manifest.json; dependency oracle is requirements.txt.
§8: Missing files, failed imports and mismatched versions fail explicitly.
"""

import argparse
from dataclasses import dataclass
import hashlib
import importlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
LINES = []


@dataclass
class Check:
    name: str
    fn: object

    def run(self):
        try:
            ok, message = self.fn()
        except Exception as exc:
            ok, message = False, f'{type(exc).__name__}: {exc}'
        text = f'[{"OK" if ok else "FAIL"}] {self.name}: {message}'.encode('ascii', 'backslashreplace').decode('ascii')
        print(text, flush=True)
        LINES.append(text)
        return bool(ok)


def dependencies():
    lock = ('requirements-lock-win-amd64.txt' if sys.platform == 'win32' else
            'requirements-lock-linux-x86_64.txt' if sys.platform.startswith('linux') else
            'requirements-lock-macos-arm64.txt')
    for line in (ROOT / lock).read_text(encoding='utf-8').splitlines():
        if not line.strip() or line.startswith('#'):
            continue
        name, expected = line.split()[0].split('==')
        if version(name) != expected:
            return False, f'{name}: expected {expected}, installed {version(name)}'
    for module in (
        'PySide6.QtWidgets',
        'PySide6.QtSvg',
        'numpy',
        'vtk',
        'vtkmodules.qt.QVTKRenderWindowInteractor',
    ):
        importlib.import_module(module)
    return True, 'pinned versions and runtime imports'


def assets():
    """Every missing or changed file is named (the Windows run of 2026-10-29 stopped on two missing pictures
    with a bare FileNotFoundError, and the launcher advised to reinstall Python)."""
    manifest = json.loads((ROOT / 'assets-manifest.json').read_text(encoding='utf-8'))
    missing, changed = [], []
    for name, expected in manifest.items():
        path = ROOT / name
        if not path.is_file():
            missing.append(name)
        elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            changed.append(name)
    if missing or changed:
        parts = []
        if missing:
            parts.append(f'{len(missing)} missing: ' + ', '.join(missing[:5]) + (' ...' if len(missing) > 5 else ''))
        if changed:
            parts.append(f'{len(changed)} checksum mismatch: ' + ', '.join(changed[:5]) + (' ...' if len(changed) > 5 else ''))
        # a changed file is not an incomplete download (a student's report: the stale hashes of en.json and
        # zh.json, the same archive again did not help)
        advice = []
        if missing:
            advice.append('missing files: unpack the whole archive again (Extract All), into an empty folder')
        if changed:
            advice.append('changed files: an edited file, or a manifest of the release not updated -- tell the author')
        return False, '; '.join(parts) + ' -- ' + '; '.join(advice)
    return True, f'{len(manifest)} bundled files verified'


def symmetry():
    """The symmetry engine of Compass and Spectrum
    (azimuth/symmetry_engine) — the point group of water."""
    from azimuth.core import Atom, Molecule
    from modules.compass.chemistry import symmetry as point_group

    water = Molecule('water', [Atom('O', 0, 0, 0.1173), Atom('H', 0, 0.7572, -0.4692), Atom('H', 0, -0.7572, -0.4692)])
    group = point_group.analyze(water).get('name')
    return group == 'C2v', f'point group of water: {group}'


def smoke():
    from modules.spectrum.readers.cube import demo_cube
    from modules.spectrum.views.cube_view import surface

    data = surface(demo_cube(), 0, 0.05)
    return data.GetNumberOfPoints() > 0, 'VTK contour generation (no window)'


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--quick', action='store_true')
    args = parser.parse_args()
    checks = [
        # 3.12 or 3.13 (NumPy 2.5 needs 3.12+; 3.13 is the tested one)
        Check('Python', lambda: ((3, 12) <= sys.version_info[:2] <= (3, 13), sys.version.split()[0])),
        Check('Dependencies', dependencies),
        Check('Assets', assets),
        Check('Symmetry', symmetry),
    ]
    if not args.quick:
        checks.append(Check('Surface', smoke))
    results = [check.run() for check in checks]
    LINES.append(f'{sum(results)}/{len(results)} checks passed')
    print(LINES[-1])
    # the lines also go to verify-log.txt (Windows PowerShell 5 did not put them into setup-log.txt; setup.ps1
    # prints this file on a failure)
    try:
        (ROOT / 'verify-log.txt').write_text('\n'.join(LINES) + '\n', encoding='ascii', errors='backslashreplace')
    except OSError:
        pass
    return 0 if all(results) else 1


if __name__ == '__main__':
    raise SystemExit(main())

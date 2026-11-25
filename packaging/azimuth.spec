# PyInstaller: «Азимут» for Windows as a folder (0.91.57) — the installer of packaging/azimuth.iss is made from it;
# 0.166.0: on macOS the application Azimuth.app (BUNDLE), the disk image of packaging/build_macos.sh is made from it.
#
# Run from the folder of the program:  pyinstaller --noconfirm packaging/azimuth.spec
# macOS, signing (0.166.0; nothing of it is needed for an unsigned build): AZIMUTH_CODESIGN_IDENTITY — the name of the
# certificate «Developer ID Application: …» in the keychain; then PyInstaller signs every library and the bundle with
# the hardened runtime and packaging/entitlements.plist. Without it PyInstaller signs ad hoc (Apple silicon requires a
# signature of some kind to run at all).
# The folder dist/Azimuth holds Azimuth.exe and _internal/ — the code and, at the same relative paths as in the
# repository, the files the program reads next to its code (azimuth.paths.ROOT is _internal there): assets, examples,
# docs, the translations. Not taken: the tests, tools, the macOS bundle, and since 0.160.0 the Atlas (modules/atlas:
# it lives on the site, azimuth-chem.com, and is the source of the site in the repository; the symmetry engine that
# Compass and Spectrum took from it is azimuth/symmetry_engine).

import os
import sys
from pathlib import Path

from PyInstaller.utils.hooks import collect_submodules

ROOT = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(ROOT))
SKIP_DIRS = {'__pycache__', '.pytest_cache', '_to_delete', '_X'}


ATLAS = ROOT / 'modules' / 'atlas'  # 0.160.0: not in the program


def tree(folder, *, code=False):
    """(source, target folder) of every file under folder (its .py too when code=True), the same relative paths;
    nothing of the Atlas."""
    pairs = []
    for path in sorted((ROOT / folder).rglob('*')):
        if not path.is_file() or SKIP_DIRS & set(path.parts):
            continue
        if path.is_relative_to(ATLAS):
            continue
        if not code and path.suffix in ('.py', '.pyc'):
            continue
        pairs.append((str(path), str(path.parent.relative_to(ROOT))))
    return pairs


datas = (
    tree('assets') + tree('examples') + tree('docs') + tree('azimuth') + tree('hub') + tree('modules')
    # 0.98.0: run as a script by a Python with RDKit (modules/compass/chemistry/embed3d.py), not imported — its source is needed
    + [(str(ROOT / 'modules' / 'compass' / 'chemistry' / 'rdkit_embed.py'), 'modules/compass/chemistry')]
    + [(str(ROOT / name), '.') for name in ('CHANGELOG.md', 'README.md', 'THIRD_PARTY.md', 'PROVENANCE.md',
                                            'assets-manifest.json') if (ROOT / name).is_file()]
)
hiddenimports = [name for name in collect_submodules('azimuth') + collect_submodules('hub') + collect_submodules('modules')
                 if not name.startswith('modules.atlas')]  # 0.160.0: the Atlas is on the site

a = Analysis(
    [str(ROOT / 'gui_launcher.py')],
    pathex=[str(ROOT)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=['tkinter', 'pytest', 'IPython', 'matplotlib.tests', 'numpy.tests', 'modules.atlas', 'quas_atlas',
              'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets', 'PySide6.QtWebEngineQuick'],  # 0.161.0
    noarchive=False,
)
MACOS = sys.platform == 'darwin'
IDENTITY = os.environ.get('AZIMUTH_CODESIGN_IDENTITY') or None  # 0.166.0: None — ad hoc
ENTITLEMENTS = str(ROOT / 'packaging' / 'entitlements.plist') if MACOS and IDENTITY else None

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Azimuth',
    console=False,  # a window program: no console of its own (the programs it starts are hidden too: consoles.py)
    icon=str(ROOT / 'assets' / 'app-icon' / ('Azimuth.icns' if MACOS else 'Azimuth.ico')),
    argv_emulation=False,  # macOS: the links azimuth:// arrive as QEvent.FileOpen (azimuth/link_channel.py)
    codesign_identity=IDENTITY,
    entitlements_file=ENTITLEMENTS,
)
coll = COLLECT(exe, a.binaries, a.datas, name='Azimuth')

if MACOS:  # 0.166.0
    from azimuth import __version__

    app = BUNDLE(
        coll,
        name='Azimuth.app',
        icon=str(ROOT / 'assets' / 'app-icon' / 'Azimuth.icns'),
        bundle_identifier='org.quail.qccstudio',  # the same as the Azimuth.app of the folder of the program
        version=__version__,
        info_plist={
            'CFBundleDisplayName': 'Азимут',
            'CFBundleName': 'Azimuth',
            'CFBundleShortVersionString': __version__,
            'CFBundleVersion': __version__,
            'NSHighResolutionCapable': True,
            'LSMinimumSystemVersion': '12.0',
            'NSHumanReadableCopyright': '© 2026 С. А. Собалев',
            'CFBundleURLTypes': [{  # 0.131.0: the links azimuth:// of the site (azimuth/links.py)
                'CFBundleURLName': 'org.quail.qccstudio.link',
                'CFBundleTypeRole': 'Viewer',
                'CFBundleURLSchemes': ['azimuth'],
            }],
        },
    )

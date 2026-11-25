"""The files of the built program (packaging/) agree with the program and with each other.

The build itself runs on macOS and Windows (packaging/build_macos.sh, .github/workflows/build-*.yml) — not here; these
checks catch a spec that does not compile, an Azimuth.app of the image that would not answer the links azimuth://
the way the Azimuth.app of the folder does, and entitlements that macOS could not read.
"""

import plistlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGING = ROOT / 'packaging'


def test_the_spec_compiles_and_describes_the_bundle():
    text = (PACKAGING / 'azimuth.spec').read_text(encoding='utf-8')
    compile(text, 'azimuth.spec', 'exec')
    folder = plistlib.loads((ROOT / 'Azimuth.app' / 'Contents' / 'Info.plist').read_bytes())
    assert f"bundle_identifier='{folder['CFBundleIdentifier']}'" in text
    scheme = folder['CFBundleURLTypes'][0]
    assert f"'CFBundleURLName': '{scheme['CFBundleURLName']}'" in text
    assert "'CFBundleURLSchemes': ['azimuth']" in text and scheme['CFBundleURLSchemes'] == ['azimuth']
    assert "'CFBundleDisplayName': '" + folder['CFBundleDisplayName'] + "'" in text


def test_the_entitlements_and_the_build_script():
    keys = plistlib.loads((PACKAGING / 'entitlements.plist').read_bytes())
    assert keys == {'com.apple.security.cs.allow-jit': True,
                    'com.apple.security.cs.allow-unsigned-executable-memory': True,
                    'com.apple.security.cs.disable-library-validation': True}
    script = (PACKAGING / 'build_macos.sh').read_text(encoding='utf-8')
    assert '--check' in script and 'hdiutil create' in script and 'shasum -a 256' in script
    # the same PyInstaller in the script and in both workflows
    versions = set(re.findall(r'pyinstaller==([\d.]+)', script + ''.join(
        p.read_text(encoding='utf-8') for p in (ROOT / '.github' / 'workflows').glob('build-*.yml')), re.I))
    assert len(versions) == 1

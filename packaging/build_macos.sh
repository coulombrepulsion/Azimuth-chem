#!/bin/zsh
# 0.166.0: «Азимут» for macOS — Azimuth.app (PyInstaller, packaging/azimuth.spec) and the disk image
# dist/installer/Azimuth-<version>-macOS-<arch>.dmg with its SHA-256.
#
# Run from the folder of the program:   zsh packaging/build_macos.sh
# Needs: .venv with requirements.txt (setup.sh) and PyInstaller — the script installs PyInstaller into .venv if absent.
#
# Unsigned by default (ad hoc: Apple silicon runs nothing without a signature of some kind). A downloaded unsigned
# application is opened the first time through «Системные настройки → Конфиденциальность и безопасность → Всё равно
# открыть». Signing and notarization, when there is an Apple Developer account:
#   AZIMUTH_CODESIGN_IDENTITY="Developer ID Application: Имя (TEAMID)"   — the certificate in the keychain;
#   AZIMUTH_NOTARY_PROFILE=azimuth   — a profile saved once by
#       xcrun notarytool store-credentials azimuth --apple-id <почта> --team-id <TEAMID> --password <пароль приложения>
# With both set the script signs the application and the image, sends the image to Apple and staples the ticket.
set -eu
cd "$(dirname "$0")/.."
PY=.venv/bin/python
[[ -x $PY ]] || { echo "Нет .venv: сначала zsh setup.sh"; exit 1; }
if ! $PY -c 'import PyInstaller' 2>/dev/null; then
    # the index of pip.conf first (a mirror), then PyPI itself — a mirror that does not answer stops nothing
    $PY -m pip install --timeout 30 'pyinstaller==6.16.0' \
        || $PY -m pip install --timeout 30 --index-url https://pypi.org/simple 'pyinstaller==6.16.0'
fi

VERSION=$($PY -c 'import azimuth; print(azimuth.__version__)')
ARCH=$(uname -m)
IDENTITY=${AZIMUTH_CODESIGN_IDENTITY:-}
PROFILE=${AZIMUTH_NOTARY_PROFILE:-}
APP=dist/Azimuth.app
OUT=dist/installer
DMG=$OUT/Azimuth-$VERSION-macOS-$ARCH.dmg
echo "Азимут $VERSION, $ARCH, подпись: ${IDENTITY:-нет (ad hoc)}"

$PY -m PyInstaller --noconfirm --clean packaging/azimuth.spec

# the same check as the build for Windows: the hub and every section start (without VTK, off screen)
LOGS=$(mktemp -d)
if ! QT_QPA_PLATFORM=offscreen AZIMUTH_NO_VTK=1 AZIMUTH_LOG_DIR=$LOGS "$APP/Contents/MacOS/Azimuth" --check; then
    cat "$LOGS"/*.log 2>/dev/null || true
    echo "Собранная программа не запустилась — образ не сделан."
    exit 1
fi
grep -h 'startup verified' "$LOGS"/startup.log || { cat "$LOGS"/*.log; echo "Нет записи о проверке запуска."; exit 1; }

if [[ -n $IDENTITY ]]; then
    codesign --verify --deep --strict --verbose=2 "$APP"
fi

mkdir -p "$OUT"
STAGE=$(mktemp -d)
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
rm -f "$DMG"
hdiutil create -volname "Азимут $VERSION" -srcfolder "$STAGE" -fs HFS+ -format UDZO -ov "$DMG"
rm -rf "$STAGE"

if [[ -n $IDENTITY ]]; then
    codesign --sign "$IDENTITY" --timestamp "$DMG"
    if [[ -n $PROFILE ]]; then
        xcrun notarytool submit "$DMG" --keychain-profile "$PROFILE" --wait
        xcrun stapler staple "$DMG"
        spctl --assess --type open --context context:primary-signature --verbose=2 "$DMG"
    else
        echo "AZIMUTH_NOTARY_PROFILE не задан: образ подписан, но не нотаризован."
    fi
fi

(cd "$OUT" && shasum -a 256 "$(basename "$DMG")" > "$(basename "$DMG").sha256")
echo "Готово: $DMG"
cat "$DMG.sha256"

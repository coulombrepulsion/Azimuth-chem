#!/usr/bin/env bash
# Installation contract: docs/setup/INSTALLATION.md (sections 1-8).
set -u
set -o pipefail
cd "$(dirname "$0")" || exit 1
python_bin=''
skip=0
no_download=0
bundle=''
die() { echo "[setup] ERROR: $*; see docs/setup/TROUBLESHOOTING.md; retry --debug" >&2; exit 1; }
while (( $# )); do
  case "$1" in
    --python) (( $# >= 2 )) || die 'Missing Python path'; python_bin=$2; shift 2 ;;
    --skip-venv) skip=1; shift ;;
    --no-download) no_download=1; shift ;;
    --offline-bundle) (( $# >= 2 )) || die 'Missing wheel directory'; bundle=$2; shift 2 ;;
    --debug) set -x; shift ;;
    *) die "Unknown option: $1" ;;
  esac
done
# 0.91.58: any 64-bit Python 3.12 or 3.13 (NumPy 2.5 needs 3.12+; 3.13 is tested); a Conda Python is fine for .venv
check='import struct,sys; sys.exit(0 if (3,12) <= sys.version_info[:2] <= (3,13) and struct.calcsize("P") == 8 else 1)'
if [[ -z "$python_bin" ]]; then
  for candidate in python3.13 python3.12 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "$check" 2>/dev/null; then python_bin=$candidate; break; fi
  done
fi
echo '[setup] 1/6 Python checks (Python 3.12 or 3.13, 64-bit; 3.13 tested)'
# 0.222.14: macOS has no Python 3.12+ of its own, and this script does not install one (setup.ps1 does on Windows) — the
# message says where to get it instead of only «not found»
[[ -n "$python_bin" ]] && "$python_bin" -c "$check" || die 'No Python 3.12 or 3.13 found. Install Python 3.13 (macOS: the installer of https://www.python.org/downloads/macos/ ; Linux: the package python3.13 with venv), then start again; or name one with --python'
echo '[setup] 2/6 Environment'
if (( ! skip )); then
  [[ -d .venv ]] || "$python_bin" -m venv .venv || die 'Cannot create .venv'
  python_bin="$PWD/.venv/bin/python"
fi
echo '[setup] 3/6 Platform lock'
platform=$("$python_bin" -c 'import platform; print(platform.system()+"-"+platform.machine())') || die 'Cannot detect platform'
lock=''
if "$python_bin" -c 'import sys; sys.exit(0 if sys.version_info[:2] == (3,13) else 1)'; then
  case "$platform" in
    Darwin-arm64) lock=requirements-lock-macos-arm64.txt ;;
    Linux-x86_64) lock=requirements-lock-linux-x86_64.txt ;;  # 0.194.0
  esac
fi
# 0.91.58: another Python or platform: requirements.txt (the same versions, without the hashes of the lock)
[[ -n "$lock" ]] || echo '[setup] no hashed lock for this Python/platform: requirements.txt'
echo '[setup] 4/6 Dependencies'
if (( no_download )); then
  [[ -n "$bundle" ]] || die '--no-download requires --offline-bundle DIRECTORY'
  "$python_bin" -m pip install --no-index --find-links "$bundle" --require-hashes -r "$lock" || die 'Offline install failed'
else
  if [[ -n "$bundle" ]]; then
    "$python_bin" -m pip download --only-binary=:all: --require-hashes -r "$lock" -d "$bundle" || die 'Wheel download failed'
  fi
  if [[ -n "$lock" ]]; then
    "$python_bin" -m pip install --require-hashes -r "$lock" || die 'Dependency installation failed'
  else
    "$python_bin" -m pip install --only-binary=:all: -r requirements.txt || die 'Dependency installation failed'
  fi
fi
echo '[setup] 5/6 Teaching assets are bundled; no external models needed'
echo '[setup] 6/6 Verification'
"$python_bin" verify_install.py || die 'Verification failed'
"$python_bin" -m pip freeze > requirements-frozen.txt || die 'Cannot save environment snapshot'
if [[ "$(uname -s)" == Linux ]]; then
  echo '[setup] Ready. Start ./Launch-Linux.sh; to add Azimuth to the menu: ./Launch-Linux.sh --install-desktop'
else
  echo '[setup] Ready. Open Azimuth.app to start.'
fi

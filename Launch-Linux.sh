#!/usr/bin/env bash
# Azimuth on Linux (x86_64, glibc 2.34+: Ubuntu 22.04+, Debian 12+, Fedora 35+).
#   ./Launch-Linux.sh                    first run: installs .venv (setup.sh), then starts the program
#   ./Launch-Linux.sh --install-desktop  adds Azimuth to the menu of applications (and the links azimuth:// of the site)
#   ./Launch-Linux.sh --remove-desktop   takes it away again
# Run it from a terminal the first time: the installation writes its steps there.
set -u
cd "$(dirname "$(readlink -f "$0")")" || exit 1
root="$PWD"
apps="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
icons="${XDG_DATA_HOME:-$HOME/.local/share}/icons/hicolor"

pause() { if [[ -t 0 ]]; then read -r -p 'Press Enter to exit.' _; fi; }

desktop_entry() {
  # Exec runs the GUI launcher of the virtual environment directly (no terminal); %u — a link azimuth:// of the site
  cat <<ENTRY
[Desktop Entry]
Type=Application
Version=1.5
Name=Azimuth
Name[ru]=Азимут
Name[zh]=方位
GenericName=Quantum chemistry
GenericName[ru]=Квантовая химия
Comment=Theory, building molecules and crystals, calculations and their results
Comment[ru]=Теория, построение молекул и кристаллов, расчёты и их результаты
Exec="$root/.venv/bin/python" -B "$root/gui_launcher.py" %u
Path=$root
Icon=azimuth
Terminal=false
Categories=Education;Science;Chemistry;
MimeType=x-scheme-handler/azimuth;
StartupWMClass=azimuth
ENTRY
}

case "${1:-}" in
  --install-desktop)
    [[ -x .venv/bin/python ]] || { echo 'Run ./Launch-Linux.sh once first: it installs the program.'; exit 1; }
    mkdir -p "$apps"
    for size in 16 32 48 128 256 512; do
      mkdir -p "$icons/${size}x${size}/apps"
      cp "assets/app-icon/azimuth-$size.png" "$icons/${size}x${size}/apps/azimuth.png"
    done
    desktop_entry > "$apps/azimuth.desktop"
    command -v update-desktop-database >/dev/null && update-desktop-database "$apps" >/dev/null 2>&1
    command -v xdg-mime >/dev/null && xdg-mime default azimuth.desktop x-scheme-handler/azimuth
    command -v gtk-update-icon-cache >/dev/null && gtk-update-icon-cache -q -t "$icons" >/dev/null 2>&1
    echo "Azimuth is in the menu of applications ($apps/azimuth.desktop)."
    exit 0 ;;
  --remove-desktop)
    rm -f "$apps/azimuth.desktop"
    for size in 16 32 48 128 256 512; do rm -f "$icons/${size}x${size}/apps/azimuth.png"; done
    command -v update-desktop-database >/dev/null && update-desktop-database "$apps" >/dev/null 2>&1
    echo 'Azimuth is no longer in the menu of applications.'
    exit 0 ;;
esac

# Qt 6.5+ on X11 needs libxcb-cursor (not installed by default on some systems): say so before Qt fails with
# «could not load the Qt platform plugin "xcb"»
if [[ -z "${WAYLAND_DISPLAY:-}" ]] && command -v ldconfig >/dev/null && ! ldconfig -p 2>/dev/null | grep -q 'libxcb-cursor\.so\.0'; then
  echo 'Note: libxcb-cursor0 is not installed; Qt may not start on X11.'
  echo '  Ubuntu/Debian: sudo apt install libxcb-cursor0    Fedora: sudo dnf install xcb-util-cursor'
fi

if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -c 'from PySide6 import QtWidgets; import vtk, numpy' >/dev/null 2>&1; then
  if ! bash setup.sh; then
    echo 'Installation failed. See docs/setup/TROUBLESHOOTING.md.'
    pause
    exit 1
  fi
  echo 'To start Azimuth from the menu of applications: ./Launch-Linux.sh --install-desktop'
fi
if ! .venv/bin/python -B main.py "$@"; then
  echo 'Azimuth stopped with an error. Keep the message above.'
  pause
  exit 1
fi

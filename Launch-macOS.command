#!/bin/zsh
cd "$(dirname "$0")" || exit 1
if [[ ! -x .venv/bin/python ]] || ! .venv/bin/python -c 'from PySide6 import QtWidgets; import vtk, numpy' >/dev/null 2>&1; then
  if ! bash setup.sh; then
    echo 'Installation failed. See docs/setup/TROUBLESHOOTING.md.'
    read '?Press Enter to exit.'
    exit 1
  fi
fi
if ! .venv/bin/python main.py; then
  echo 'Azimuth stopped with an error. Keep the message above.'
  read '?Press Enter to exit.'
  exit 1
fi

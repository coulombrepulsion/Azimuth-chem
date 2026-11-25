@echo off
setlocal
cd /d "%~dp0"
rem 0.91.59: a .bat started inside the zip in Explorer sees no other file
if not exist "%~dp0setup.ps1" (
  echo Azimuth: the archive is not unpacked. Close this window, right-click the zip, choose "Extract All...",
  echo then run windows_first_run.bat from the unpacked folder.
  pause
  exit /b 1
)
rem 0.91.52: an installed program starts with this window minimized (the check of the libraries takes some seconds
rem and its black window stood on the screen); the first run, with the installation, keeps the window in sight
if exist ".venv\Scripts\pythonw.exe" if /i not "%~1"=="--min" if /i not "%~1"=="--show" (
  start "Azimuth" /min "%ComSpec%" /c ""%~f0" --min"
  exit /b 0
)
if not exist ".venv\Scripts\python.exe" goto setup
rem 0.222.35: the check imports what the program needs (verify_install.py: Qt, VTK, NumPy). QtWebEngine has not been
rem used since the Atlas moved to the site; its import failed on a Windows with a sound installation, and every start
rem ran setup.ps1 again (Windows check 2026-11-24). What failed is kept in launch-check.txt
".venv\Scripts\python.exe" -c "from PySide6 import QtWidgets; import vtk, numpy; import vtkmodules.qt.QVTKRenderWindowInteractor" >launch-check.txt 2>&1
if not errorlevel 1 goto launch
rem the libraries are broken: the repair is shown in a window in sight
if /i "%~1"=="--min" (
  start "Azimuth" "%ComSpec%" /c ""%~f0" --show"
  exit /b 0
)
:setup
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 goto failure
:launch
start "" ".venv\Scripts\pythonw.exe" gui_launcher.py
if errorlevel 1 goto failure
exit /b 0
:failure
if /i "%~1"=="--min" (
  start "Azimuth" "%ComSpec%" /k "echo Azimuth could not start: run windows_first_run.bat to repair the installation. See docs\TROUBLESHOOTING.md."
  exit /b 1
)
echo Azimuth could not start. The line "[setup] FAIL" above says which step stopped
echo (the whole log: setup-log.txt in this folder). See docs/setup/TROUBLESHOOTING.md.
pause
exit /b 1

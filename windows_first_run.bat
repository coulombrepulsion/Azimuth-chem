@echo off
setlocal
rem 0.91.59: a .bat started inside the zip in Explorer sees no other file
if not exist "%~dp0setup.ps1" (
  echo Azimuth: the archive is not unpacked. Close this window, right-click the zip, choose "Extract All...",
  echo then run windows_first_run.bat from the unpacked folder.
  pause
  exit /b 1
)
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
set result=%errorlevel%
pause
exit /b %result%

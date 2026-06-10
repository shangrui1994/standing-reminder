@echo off
setlocal

pushd "%~dp0"

set PYTHON=python

"%PYTHON%" create_icon.py

"%PYTHON%" -m PyInstaller ^
  --noconsole ^
  --onefile ^
  --name StandingReminder ^
  --icon "assets\app_icon.ico" ^
  --add-data "assets;assets" ^
  main.py

echo.
echo Build finished. EXE path: dist\StandingReminder.exe
popd
pause

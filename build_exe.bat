@echo off
setlocal

pushd "%~dp0"

set PYTHON=python

"%PYTHON%" create_icon.py
if errorlevel 1 goto :failed

if not exist "assets\standing_mascot.png" (
  echo Missing required asset: assets\standing_mascot.png
  goto :failed
)

"%PYTHON%" -m PyInstaller --noconfirm --clean StandingReminder.spec
if errorlevel 1 goto :failed

echo.
echo Build finished. EXE path: dist\StandingReminder.exe
popd
pause
exit /b 0

:failed
echo.
echo Build failed.
popd
pause
exit /b 1

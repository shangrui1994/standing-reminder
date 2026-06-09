@echo off
setlocal

set PYTHON=C:\Users\Chen\AppData\Local\Programs\Python\Python314\python.exe

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
pause
